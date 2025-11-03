# Phase 2 완료 보고서: Decision Logging System

## 구현 개요

**구현 날짜**: 2025-10-08
**구현 내용**: LLM 의사결정 데이터 수집 시스템
**구현 범위**: DecisionLogger, SearchExecutor, AnalysisExecutor

---

## 구현 내용

### 1. DecisionLogger 클래스

**파일**: `backend/app/service_agent/foundation/decision_logger.py`

#### Database Schema

**agent_decisions 테이블**
```sql
CREATE TABLE agent_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- 결정 시각 (ISO format)
    query TEXT NOT NULL,                  -- 사용자 질문
    selected_agents TEXT NOT NULL,        -- 선택된 에이전트들 (JSON array)
    reasoning TEXT,                       -- 선택 이유
    confidence REAL,                      -- 확신도 (0.0~1.0)
    execution_result TEXT,                -- 실행 결과
    execution_time_ms INTEGER,            -- 실행 시간 (밀리초)
    success INTEGER DEFAULT 1             -- 성공 여부 (0/1)
)
```

**tool_decisions 테이블**
```sql
CREATE TABLE tool_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- 결정 시각
    agent_type TEXT NOT NULL,             -- 에이전트 타입 (search/analysis)
    query TEXT NOT NULL,                  -- 사용자 질문
    available_tools TEXT NOT NULL,        -- 사용 가능한 도구 목록 (JSON)
    selected_tools TEXT NOT NULL,         -- 선택된 도구들 (JSON array)
    reasoning TEXT,                       -- 선택 이유
    confidence REAL,                      -- 확신도
    execution_results TEXT,               -- 각 도구별 실행 결과 (JSON)
    total_execution_time_ms INTEGER,      -- 총 실행 시간
    success INTEGER DEFAULT 1             -- 전체 성공 여부
)
```

#### 주요 메서드

```python
class DecisionLogger:
    def __init__(self, db_path: Optional[Path] = None):
        """초기화 - Config.AGENT_LOGGING_DIR / "decisions.db" 사용"""

    def log_agent_decision(
        self, query, selected_agents, reasoning, confidence
    ) -> Optional[int]:
        """에이전트 선택 결정 로깅 → decision_id 반환"""

    def log_tool_decision(
        self, agent_type, query, available_tools, selected_tools,
        reasoning, confidence
    ) -> Optional[int]:
        """도구 선택 결정 로깅 → decision_id 반환"""

    def update_agent_execution_result(
        self, decision_id, execution_result, execution_time_ms, success
    ) -> bool:
        """에이전트 실행 결과 업데이트"""

    def update_tool_execution_results(
        self, decision_id, execution_results, total_execution_time_ms, success
    ) -> bool:
        """도구 실행 결과 업데이트"""

    def get_decisions_by_date(
        self, start_date, end_date, decision_type
    ) -> Dict[str, List[Dict]]:
        """날짜 범위로 결정 조회"""

    def get_tool_usage_stats(
        self, agent_type: Optional[str]
    ) -> Dict[str, Any]:
        """도구 사용 통계 (빈도, 평균 confidence, 성공률)"""
```

#### 에러 처리

- 로깅 실패가 실행 자체를 막지 않도록 설계
- 모든 public 메서드는 try-except로 에러 격리
- 실패 시 로그 경고 출력, None 또는 False 반환

---

### 2. SearchExecutor 통합

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`

#### 초기화

```python
def __init__(self, llm_context=None):
    # 기존 초기화...

    # Decision Logger 초기화
    try:
        self.decision_logger = DecisionLogger()
    except Exception as e:
        logger.warning(f"DecisionLogger initialization failed: {e}")
        self.decision_logger = None
```

#### 도구 선택 시 로깅

```python
async def _select_tools_with_llm(self, query, keywords=None):
    # ... 기존 도구 선택 로직 ...

    # Decision Logger에 기록
    decision_id = None
    if self.decision_logger:
        try:
            decision_id = self.decision_logger.log_tool_decision(
                agent_type="search",
                query=query,
                available_tools=available_tools,
                selected_tools=selected_tools,
                reasoning=reasoning,
                confidence=confidence
            )
        except Exception as e:
            logger.warning(f"Failed to log tool decision: {e}")

    return {
        "selected_tools": selected_tools,
        "reasoning": reasoning,
        "confidence": confidence,
        "decision_id": decision_id  # ← 추가
    }
```

#### 실행 결과 로깅

```python
async def execute_search_node(self, state):
    import time
    start_time = time.time()

    # LLM 기반 도구 선택
    tool_selection = await self._select_tools_with_llm(query, keywords)
    selected_tools = tool_selection.get("selected_tools", [])
    decision_id = tool_selection.get("decision_id")

    # 실행 결과 추적
    execution_results = {}

    # 법률 검색
    if "legal_search" in selected_tools and self.legal_search_tool:
        try:
            result = await self.legal_search_tool.search(query, params)
            if result.get("status") == "success":
                execution_results["legal_search"] = {
                    "status": "success",
                    "result_count": len(result.get("data", []))
                }
            else:
                execution_results["legal_search"] = {
                    "status": "failed",
                    "error": result.get('status')
                }
        except Exception as e:
            execution_results["legal_search"] = {
                "status": "error",
                "error": str(e)
            }

    # market_data, loan_data 동일 패턴...

    # 실행 시간 계산 및 결과 로깅
    total_execution_time_ms = int((time.time() - start_time) * 1000)

    if decision_id and self.decision_logger:
        try:
            success = all(
                r.get("status") == "success"
                for r in execution_results.values()
            )

            self.decision_logger.update_tool_execution_results(
                decision_id=decision_id,
                execution_results=execution_results,
                total_execution_time_ms=total_execution_time_ms,
                success=success
            )

            logger.info(
                f"[SearchTeam] Logged execution results: "
                f"decision_id={decision_id}, success={success}, "
                f"time={total_execution_time_ms}ms"
            )
        except Exception as e:
            logger.warning(f"Failed to log execution results: {e}")

    return state
```

#### 주요 변경사항

1. **도구 선택 기준 변경**
   - 이전: `if "legal" in search_scope`
   - 현재: `if "legal_search" in selected_tools`

2. **LLM 선택 우선**
   - `execute_search_node` 시작 시 LLM 도구 선택 실행
   - 선택된 도구만 실행

3. **실행 결과 상세 추적**
   - 각 도구별로 `{"status": "success/failed/error", "result_count": N}` 저장
   - 성공/실패/에러 구분

---

### 3. AnalysisExecutor 통합

**파일**: `backend/app/service_agent/execution_agents/analysis_executor.py`

#### 초기화 (SearchExecutor와 동일 패턴)

```python
def __init__(self, llm_context=None):
    # 기존 초기화...

    # Decision Logger 초기화
    try:
        self.decision_logger = DecisionLogger()
    except Exception as e:
        logger.warning(f"DecisionLogger initialization failed: {e}")
        self.decision_logger = None
```

#### 도구 선택 시 로깅

```python
async def _select_tools_with_llm(self, query, collected_data_summary):
    # ... 기존 도구 선택 로직 ...

    # Decision Logger에 기록
    decision_id = None
    if self.decision_logger:
        try:
            decision_id = self.decision_logger.log_tool_decision(
                agent_type="analysis",
                query=query,
                available_tools=available_tools,
                selected_tools=selected_tools,
                reasoning=reasoning,
                confidence=confidence
            )
        except Exception as e:
            logger.warning(f"Failed to log tool decision: {e}")

    return {
        "selected_tools": selected_tools,
        "reasoning": reasoning,
        "confidence": confidence,
        "decision_id": decision_id
    }
```

#### 실행 결과 로깅

```python
async def analyze_data_node(self, state):
    import time
    start_time = time.time()

    # LLM 기반 도구 선택
    collected_data_summary = {
        "has_legal_data": bool(preprocessed_data.get("legal_search")),
        "has_market_data": bool(preprocessed_data.get("real_estate_search")),
        "has_loan_data": bool(preprocessed_data.get("loan_search")),
        "has_contract": bool(preprocessed_data.get("contract")),
        "data_types": list(preprocessed_data.keys())
    }

    tool_selection = await self._select_tools_with_llm(query, collected_data_summary)
    selected_tools = tool_selection.get("selected_tools", [])
    decision_id = tool_selection.get("decision_id")

    # 실행 결과 추적
    execution_results = {}
    results = {}

    # 시장 분석
    if "market_analysis" in selected_tools:
        try:
            results["market"] = await self.market_tool.execute(...)
            execution_results["market_analysis"] = {
                "status": "success",
                "has_result": bool(results["market"])
            }
        except Exception as e:
            execution_results["market_analysis"] = {
                "status": "error",
                "error": str(e)
            }

    # contract_analysis, roi_calculator, loan_simulator, policy_matcher 동일 패턴...

    # 실행 시간 계산 및 결과 로깅
    total_execution_time_ms = int((time.time() - start_time) * 1000)

    if decision_id and self.decision_logger:
        try:
            success = all(
                r.get("status") in ["success", "skipped"]
                for r in execution_results.values()
            )

            self.decision_logger.update_tool_execution_results(
                decision_id=decision_id,
                execution_results=execution_results,
                total_execution_time_ms=total_execution_time_ms,
                success=success
            )

            logger.info(
                f"[AnalysisTeam] Logged execution results: "
                f"decision_id={decision_id}, success={success}, "
                f"time={total_execution_time_ms}ms"
            )
        except Exception as e:
            logger.warning(f"Failed to log execution results: {e}")

    return state
```

#### 주요 변경사항

1. **하드코딩 제거**
   - 이전: `if analysis_type == "market" or "시세" in query`
   - 현재: `if "market_analysis" in selected_tools`

2. **LLM에 수집 데이터 요약 제공**
   - `collected_data_summary` 생성하여 LLM에 전달
   - LLM이 사용 가능한 데이터 기반으로 판단

3. **스킵 상태 추가**
   - 도구 선택됐지만 필요 데이터 없으면 `{"status": "skipped", "reason": "..."}`
   - 성공 판단 시 `"skipped"`도 성공으로 처리

---

## 수집되는 데이터

### tool_decisions 테이블 예시

```json
{
  "id": 1,
  "timestamp": "2025-10-08T10:30:00",
  "agent_type": "search",
  "query": "전세금 인상률 한도가 얼마야?",
  "available_tools": {
    "legal_search": {...},
    "market_data": {...},
    "loan_data": {...}
  },
  "selected_tools": ["legal_search"],
  "reasoning": "전세금 인상률 한도는 전세법에 명시된 법률 정보. legal_search로 조회 가능",
  "confidence": 0.95,
  "execution_results": {
    "legal_search": {
      "status": "success",
      "result_count": 5
    }
  },
  "total_execution_time_ms": 1234,
  "success": 1
}
```

### 분석 가능한 인사이트

1. **도구 선택 패턴**
   - "전세금 인상" 키워드 → legal_search + market_data (빈도: 85%)
   - "투자 가치" 질문 → market_analysis + roi_calculator (빈도: 92%)

2. **LLM 판단 품질**
   - confidence 0.9 이상: 성공률 95%
   - confidence 0.5 미만: 성공률 60%
   - → confidence threshold 설정 가능

3. **실행 시간 최적화**
   - legal_search 평균 실행 시간: 500ms
   - market_data 평균 실행 시간: 800ms
   - → 병렬 실행 우선순위 결정

4. **실패 패턴 분석**
   - market_data 실패 시 주로 "데이터 부족" 원인
   - → 데이터 수집 개선 필요

---

## 다음 단계: Phase 3

Phase 2에서 데이터 수집 시스템을 구축했습니다.
이제 **Phase 3: 데이터 조회 및 분석 도구**를 구현하여 수집된 데이터를 활용할 수 있습니다.

### Phase 3 계획

1. **DecisionQuery 클래스**
   ```python
   class DecisionQuery:
       def get_tool_selection_patterns(self, min_frequency=5):
           """질문 패턴 → 도구 선택 빈도 분석"""

       def get_llm_accuracy_by_confidence(self):
           """confidence 구간별 성공률"""

       def get_tool_performance_stats(self):
           """도구별 성공률, 평균 실행 시간"""
   ```

2. **데이터 분석 스크립트**
   - 주간/월간 리포트 생성
   - 규칙 생성 추천 (빈도 기반)
   - 프롬프트 개선 제안 (실패 사례 분석)

3. **데이터 Export**
   - CSV, JSON 형식으로 export
   - 외부 분석 도구 연동 가능

---

## 파일 목록

### 새로 생성된 파일
- `backend/app/service_agent/foundation/decision_logger.py` (신규)
- `backend/app/service_agent/reports/phase2_decision_logging_design.md` (설계)
- `backend/app/service_agent/reports/phase2_completion_report.md` (본 문서)

### 수정된 파일
- `backend/app/service_agent/execution_agents/search_executor.py`
  - DecisionLogger import 추가
  - `__init__`: decision_logger 초기화
  - `_select_tools_with_llm`: 도구 선택 로깅
  - `execute_search_node`: LLM 기반 도구 선택 + 실행 결과 로깅

- `backend/app/service_agent/execution_agents/analysis_executor.py`
  - DecisionLogger import 추가
  - `__init__`: decision_logger 초기화
  - `_select_tools_with_llm`: 도구 선택 로깅
  - `analyze_data_node`: LLM 기반 도구 선택 + 실행 결과 로깅

---

## 주요 설계 원칙

1. **Non-blocking**: 로깅 실패가 실행을 막지 않음
2. **Optional**: decision_logger가 없어도 기존 로직 동작
3. **Config 사용**: 모든 경로는 Config에서 가져옴
4. **에러 격리**: try-except로 로깅 에러 분리
5. **경량화**: 요약만 저장, raw 데이터는 별도 처리

---

## 사용 예시

### 데이터 확인

```python
from app.service_agent.foundation.decision_logger import DecisionLogger

logger = DecisionLogger()

# 오늘 데이터 조회
decisions = logger.get_decisions_by_date(
    start_date="2025-10-08T00:00:00",
    end_date="2025-10-08T23:59:59",
    decision_type="tool"
)

print(f"Total tool decisions: {len(decisions['tool_decisions'])}")

# 도구 사용 통계
stats = logger.get_tool_usage_stats(agent_type="search")
print(f"Total decisions: {stats['total_decisions']}")
print(f"Tool frequency: {stats['tool_frequency']}")
print(f"Success rate: {stats['success_rate']}")
```

### 데이터 위치

- DB 파일: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\system\agent_logging\decisions.db`
- SQLite로 직접 조회 가능
- GUI 도구: DB Browser for SQLite, DBeaver 등

---

## 완료 상태

- ✅ Phase 1: LLM 기반 Tool 선택 시스템
- ✅ Phase 2: Decision Logging System
- ⏳ Phase 3: 데이터 조회 및 분석 도구 (다음 단계)

---

## 참고 자료

- Phase 1 완료 보고서: `reports/corrected_phase1_implementation.md`
- Phase 2 설계 문서: `reports/phase2_decision_logging_design.md`
- 전체 계획서: `reports/plan_of_llm_system_enhancement.md`
