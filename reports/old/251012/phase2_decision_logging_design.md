# Phase 2 설계: Decision Logging System

## 목표

LLM의 의사결정 데이터를 수집하여 향후 규칙 생성 및 프롬프트 개선에 활용

---

## Database Schema

### 1. agent_decisions 테이블

에이전트 선택 결정 로깅 (PlanningAgent에서 사용)

```sql
CREATE TABLE agent_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- 결정 시각 (ISO format)
    query TEXT NOT NULL,                  -- 사용자 질문
    selected_agents TEXT NOT NULL,        -- 선택된 에이전트들 (JSON array)
    reasoning TEXT,                       -- 선택 이유
    confidence REAL,                      -- 확신도 (0.0~1.0)
    execution_result TEXT,                -- 실행 결과 (나중에 업데이트)
    execution_time_ms INTEGER,            -- 실행 시간 (밀리초)
    success INTEGER DEFAULT 1             -- 성공 여부 (0/1)
)
```

### 2. tool_decisions 테이블

도구 선택 결정 로깅 (SearchExecutor, AnalysisExecutor에서 사용)

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

---

## DecisionLogger 클래스 설계

### 위치

`backend/app/service_agent/foundation/decision_logger.py`

### 주요 메서드

```python
class DecisionLogger:
    """LLM 의사결정 로깅 시스템"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        초기화
        Args:
            db_path: SQLite DB 경로 (기본값: Config.AGENT_LOGGING_DIR / "decisions.db")
        """

    def log_agent_decision(
        self,
        query: str,
        selected_agents: List[str],
        reasoning: str = "",
        confidence: float = 0.0
    ) -> int:
        """
        에이전트 선택 결정 로깅
        Returns:
            decision_id: 로깅된 레코드 ID
        """

    def log_tool_decision(
        self,
        agent_type: str,
        query: str,
        available_tools: Dict[str, Any],
        selected_tools: List[str],
        reasoning: str = "",
        confidence: float = 0.0
    ) -> int:
        """
        도구 선택 결정 로깅
        Returns:
            decision_id: 로깅된 레코드 ID
        """

    def update_agent_execution_result(
        self,
        decision_id: int,
        execution_result: str,
        execution_time_ms: int,
        success: bool = True
    ):
        """에이전트 실행 결과 업데이트"""

    def update_tool_execution_results(
        self,
        decision_id: int,
        execution_results: Dict[str, Any],
        total_execution_time_ms: int,
        success: bool = True
    ):
        """도구 실행 결과 업데이트"""

    def get_decisions_by_date(
        self,
        start_date: str,
        end_date: str,
        decision_type: str = "both"  # "agent", "tool", "both"
    ) -> Dict[str, List[Dict]]:
        """날짜 범위로 결정 조회"""

    def get_tool_usage_stats(
        self,
        agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """도구 사용 통계"""
```

---

## 통합 계획

### 1. SearchExecutor 통합

**수정 위치**: `execution_agents/search_executor.py`

```python
class SearchExecutor:
    def __init__(self, llm_context=None):
        # 기존 초기화
        self.decision_logger = DecisionLogger()  # 추가

    async def _select_tools_with_llm(self, query: str, keywords=None) -> Dict[str, Any]:
        available_tools = self._get_available_tools()

        # LLM 도구 선택
        result = await self.llm_service.complete_json_async(...)

        # 결정 로깅
        decision_id = self.decision_logger.log_tool_decision(
            agent_type="search",
            query=query,
            available_tools=available_tools,
            selected_tools=result.get("selected_tools", []),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.0)
        )

        # decision_id를 결과에 포함하여 나중에 업데이트 가능하도록
        result["decision_id"] = decision_id
        return result

    async def execute_search(self, state: SearchTeamState) -> SearchTeamState:
        # 도구 선택
        selection = await self._select_tools_with_llm(...)
        decision_id = selection.get("decision_id")

        # 도구 실행
        start_time = time.time()
        results = {}
        for tool_name in selection["selected_tools"]:
            try:
                results[tool_name] = await self._execute_tool(tool_name, ...)
            except Exception as e:
                results[tool_name] = {"error": str(e)}

        execution_time_ms = int((time.time() - start_time) * 1000)

        # 실행 결과 로깅
        if decision_id:
            self.decision_logger.update_tool_execution_results(
                decision_id=decision_id,
                execution_results=results,
                total_execution_time_ms=execution_time_ms,
                success=all("error" not in r for r in results.values())
            )

        return state
```

### 2. AnalysisExecutor 통합

동일한 패턴으로 적용

```python
class AnalysisExecutor:
    def __init__(self, llm_context=None):
        # 기존 초기화
        self.decision_logger = DecisionLogger()  # 추가

    async def _select_tools_with_llm(self, query, collected_data_summary) -> Dict:
        # 도구 선택 + 로깅
        decision_id = self.decision_logger.log_tool_decision(
            agent_type="analysis",
            query=query,
            available_tools=available_tools,
            selected_tools=result.get("selected_tools", []),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.0)
        )
        result["decision_id"] = decision_id
        return result

    # 실행 결과 업데이트는 SearchExecutor와 동일 패턴
```

---

## 데이터 활용 계획

### 수집할 데이터

1. **질문 패턴 분석**
   - 어떤 질문에 어떤 도구가 선택되었는가?
   - 복합 질문에서 도구 조합 패턴

2. **성공률 분석**
   - 도구별 성공률
   - 도구 조합별 성공률

3. **실행 시간 분석**
   - 도구별 평균 실행 시간
   - 병렬 실행 효과 측정

4. **LLM 판단 품질**
   - confidence와 실제 성공률 상관관계
   - reasoning 패턴 분석

### 향후 활용

1. **규칙 생성**
   - 빈도 높은 질문-도구 패턴 → 규칙화
   - 예: "전세금 인상" 포함 → legal_search + market_data (신뢰도 95%)

2. **프롬프트 개선**
   - 실패 사례 분석 → 프롬프트 예시 추가
   - 헷갈리는 패턴 → Chain-of-Thought 강화

3. **성능 최적화**
   - 자주 사용되는 도구 조합 → 병렬 실행 우선
   - 불필요한 도구 선택 패턴 발견 → 프롬프트 수정

---

## 구현 순서

1. ✅ Phase 1: LLM 기반 도구 선택 (완료)
2. 🔄 Phase 2: Decision Logging
   - Step 1: DecisionLogger 클래스 구현
   - Step 2: SearchExecutor 통합
   - Step 3: AnalysisExecutor 통합
   - Step 4: 간단한 테스트로 로깅 동작 확인
3. Phase 3: 데이터 조회 및 분석 도구 (다음 단계)

---

## 주의사항

1. **경로는 Config 사용**
   ```python
   from app.service_agent.foundation.config import Config
   db_path = Config.AGENT_LOGGING_DIR / "decisions.db"
   ```

2. **비동기 안전성**
   - SQLite 작업은 동기 방식
   - 필요시 asyncio.to_thread 사용

3. **에러 처리**
   - 로깅 실패가 실행 자체를 막으면 안 됨
   - try-except로 로깅 에러 격리

4. **데이터 크기 관리**
   - execution_result는 요약만 저장 (전체 raw 데이터 X)
   - 필요시 별도 파일로 저장

5. **하위 호환성**
   - decision_logger가 없어도 기존 로직 동작
   - Optional로 처리
