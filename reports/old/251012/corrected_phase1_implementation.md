# Phase 1 완료 보고서: LLM 기반 Tool 선택 시스템 (수정본)

## 구현 개요

**구현 날짜**: 2025-10-08
**구현 내용**: LLM 기반 동적 Tool 선택 시스템 (키워드 하드코딩 제거)
**구현 범위**: SearchExecutor, AnalysisExecutor

---

## 주요 문제점 및 해결

### 초기 구현의 문제점

1. **단일 프롬프트 문제**
   - 문제: 여러 에이전트가 있는데 `tool_selection.txt` 파일이 1개만 존재
   - 영향: 각 에이전트의 특성을 반영한 도구 선택 불가능

2. **키워드 하드코딩 문제**
   - 문제: `keywords` 파라미터로 미리 분류된 키워드를 LLM에 전달
   - 예시: `legal_keywords`, `real_estate_keywords`, `loan_keywords`
   - 영향: LLM이 실제로 판단하는 것이 아니라, 키워드 분류 규칙에 의존
   - 이는 여전히 하드코딩된 규칙 기반 시스템

### 해결 방법

1. **에이전트별 전용 프롬프트 생성**
   - `tool_selection_search.txt`: Search Team 전용
   - `tool_selection_analysis.txt`: Analysis Team 전용
   - 각 에이전트의 도구와 사용 사례에 맞춤화된 프롬프트

2. **키워드 의존성 완전 제거**
   - LLM에 전달하는 정보: **오직 사용자 질문 (query)만**
   - 키워드 파라미터 유지: 하위 호환성 위해 유지하되 사용 안 함
   - LLM이 질문을 직접 분석하여 도구 선택

3. **동적 도구 정보 수집**
   - `_get_available_tools()`: 런타임에 사용 가능한 도구 수집
   - `_get_available_analysis_tools()`: 분석 도구 동적 수집
   - 도구별 name, description, capabilities, available 상태 포함

---

## 구현 세부사항

### 1. Config 설정 (foundation/config.py)

```python
# Agent 로깅 디렉토리 추가
AGENT_LOGGING_DIR = BASE_DIR / "data" / "system" / "agent_logging"

# 디렉토리 생성
for directory in [CHECKPOINT_DIR, AGENT_LOGGING_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
```

### 2. Search Team 프롬프트 (llm_manager/prompts/execution/tool_selection_search.txt)

**특징**:
- Search Team의 3가지 도구 (legal_search, market_data, loan_data) 설명
- 4가지 선택 예시 (단순 법률, 시세, 복합 질문)
- 입력: `{query}`, `{available_tools}`
- 출력: JSON (`selected_tools`, `reasoning`, `confidence`)

**핵심 원칙**:
```
질문 분석 → 필요 정보 종류 식별 → 도구 선택
- 법률 정보 필요? → legal_search
- 시세 정보 필요? → market_data
- 대출 정보 필요? → loan_data
```

### 3. Analysis Team 프롬프트 (llm_manager/prompts/execution/tool_selection_analysis.txt)

**특징**:
- Analysis Team의 5가지 도구 설명
  - contract_analysis: 계약서 검토
  - market_analysis: 시장 분석
  - roi_calculator: 투자수익률 계산
  - loan_simulator: 대출 시뮬레이션
  - policy_matcher: 정부 지원 정책 매칭
- 6가지 상세 예시 (계약서, 투자, 대출, 종합, 정책, 복합)
- 입력: `{query}`, `{collected_data_summary}`, `{available_tools}`
- 출력: JSON (`selected_tools`, `reasoning`, `confidence`)

**핵심 원칙**:
```
질문 분석 → 수집된 데이터 확인 → 도구 선택
- 복합 분석 가능 (시장 분석 + ROI 계산)
- 우선순위: 핵심 의도 → 보조 도구 → 추가 인사이트
```

### 4. SearchExecutor 수정 (execution_agents/search_executor.py)

#### 4.1. 동적 도구 정보 수집

```python
def _get_available_tools(self) -> Dict[str, Any]:
    """현재 SearchExecutor에서 사용 가능한 tool 정보를 동적으로 수집"""
    tools = {}

    if self.legal_search_tool:
        tools["legal_search"] = {
            "name": "legal_search",
            "description": "법률 정보 검색 (전세법, 임대차보호법, 부동산 관련 법규)",
            "capabilities": [
                "법률 조항 검색",
                "법적 권리/의무 확인",
                "계약 조건 법적 타당성 검토"
            ],
            "available": True
        }

    if self.market_data_tool:
        tools["market_data"] = {
            "name": "market_data",
            "description": "부동산 시세 정보 검색 (실거래가, 전세가, 지역별 가격)",
            "capabilities": [
                "지역별 시세 조회",
                "실거래가 분석",
                "가격 적정성 평가"
            ],
            "available": True
        }

    if self.loan_data_tool:
        tools["loan_data"] = {
            "name": "loan_data",
            "description": "대출 정보 검색 (금리, LTV, DTI, 대출 상품)",
            "capabilities": [
                "대출 상품 비교",
                "금리 정보 조회",
                "LTV/DTI 계산"
            ],
            "available": True
        }

    return tools
```

#### 4.2. LLM 기반 도구 선택 (키워드 제거)

```python
async def _select_tools_with_llm(
    self,
    query: str,
    keywords: SearchKeywords = None  # 하위 호환성 유지, 미사용
) -> Dict[str, Any]:
    """LLM을 사용하여 도구 선택 (키워드 의존성 제거)"""

    available_tools = self._get_available_tools()

    result = await self.llm_service.complete_json_async(
        prompt_name="tool_selection_search",
        variables={
            "query": query,  # 오직 query만 전달
            "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
        },
        temperature=0.1
    )

    return {
        "selected_tools": result.get("selected_tools", []),
        "reasoning": result.get("reasoning", ""),
        "confidence": result.get("confidence", 0.0)
    }
```

#### 4.3. Fallback 방식 변경

```python
def _select_tools_with_fallback(self, keywords: SearchKeywords = None):
    """Fallback: 모든 가능한 도구 사용 (안전 우선)"""
    available_tools = self._get_available_tools()
    scope = list(available_tools.keys())

    return {
        "selected_tools": scope,
        "reasoning": "Fallback: using all available tools for safety",
        "confidence": 0.3
    }
```

**변경 사항**:
- 이전: 키워드 기반으로 일부 도구만 선택
- 현재: 안전을 위해 모든 도구 사용 (LLM 실패 시)

### 5. AnalysisExecutor 수정 (execution_agents/analysis_executor.py)

#### 5.1. 동적 분석 도구 정보 수집

```python
def _get_available_analysis_tools(self) -> Dict[str, Any]:
    """현재 AnalysisExecutor에서 사용 가능한 분석 도구 정보를 동적으로 수집"""
    tools = {}

    if self.contract_tool:
        tools["contract_analysis"] = {
            "name": "contract_analysis",
            "description": "계약서 내용 분석 및 위험 조항 탐지",
            "capabilities": [
                "계약서 조항 검토",
                "위험 조항 탐지",
                "법적 타당성 검토"
            ],
            "available": True
        }

    if self.market_tool:
        tools["market_analysis"] = {
            "name": "market_analysis",
            "description": "시장 동향 분석 및 가격 적정성 평가",
            "capabilities": [
                "시장 동향 분석",
                "가격 적정성 평가",
                "지역 분석"
            ],
            "available": True
        }

    if self.roi_tool:
        tools["roi_calculator"] = {
            "name": "roi_calculator",
            "description": "투자수익률 계산 및 현금흐름 분석",
            "capabilities": [
                "ROI 계산",
                "현금흐름 분석",
                "수익성 평가"
            ],
            "available": True
        }

    if self.loan_tool:
        tools["loan_simulator"] = {
            "name": "loan_simulator",
            "description": "대출 한도 계산 및 상환 계획 시뮬레이션",
            "capabilities": [
                "LTV/DTI 계산",
                "대출 한도 계산",
                "월 상환액 시뮬레이션"
            ],
            "available": True
        }

    if self.policy_tool:
        tools["policy_matcher"] = {
            "name": "policy_matcher",
            "description": "정부 지원 정책 매칭 및 자격 확인",
            "capabilities": [
                "정책 자격 확인",
                "혜택 분석",
                "지원 프로그램 매칭"
            ],
            "available": True
        }

    return tools
```

#### 5.2. LLM 기반 분석 도구 선택

```python
async def _select_tools_with_llm(
    self,
    query: str,
    collected_data_summary: Dict = None
) -> Dict[str, Any]:
    """LLM을 사용하여 분석 도구 선택"""

    available_tools = self._get_available_analysis_tools()

    if not collected_data_summary:
        collected_data_summary = {"status": "no data collected yet"}

    result = await self.llm_service.complete_json_async(
        prompt_name="tool_selection_analysis",
        variables={
            "query": query,
            "collected_data_summary": json.dumps(collected_data_summary, ensure_ascii=False),
            "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
        },
        temperature=0.1
    )

    return {
        "selected_tools": result.get("selected_tools", []),
        "reasoning": result.get("reasoning", ""),
        "confidence": result.get("confidence", 0.0)
    }
```

#### 5.3. Fallback 방식

```python
def _select_tools_with_fallback(self):
    """Fallback: 모든 가능한 분석 도구 사용 (안전 우선)"""
    available_tools = self._get_available_analysis_tools()
    scope = list(available_tools.keys())

    return {
        "selected_tools": scope,
        "reasoning": "Fallback: using all available analysis tools for safety",
        "confidence": 0.3
    }
```

---

## 구현 결과

### 변경 전 (키워드 하드코딩)

```python
# SearchExecutor._select_tools_with_llm
keywords = {
    "legal_keywords": ["전세금", "인상률", "법"],
    "real_estate_keywords": ["아파트", "시세"],
    "loan_keywords": ["대출", "금리"]
}
# LLM에 keywords 전달 → 여전히 규칙 기반
```

### 변경 후 (순수 LLM 판단)

```python
# SearchExecutor._select_tools_with_llm
variables = {
    "query": "집주인이 전세금 3억을 10억으로 올려달래. 가능해?",
    "available_tools": {...}  # 동적 수집
}
# LLM이 query만 보고 직접 판단
# → legal_search (인상률 한도 확인)
# → market_data (시세 비교)
```

### 주요 개선점

1. **완전한 탈 하드코딩**
   - 키워드 분류 제거
   - LLM이 질문 전문을 직접 분석
   - 맥락 기반 판단 가능

2. **에이전트별 최적화**
   - Search Team: 데이터 수집 관점의 프롬프트
   - Analysis Team: 수집된 데이터 활용 관점의 프롬프트

3. **동적 확장성**
   - 새 도구 추가 시 `_get_available_tools()`만 수정
   - 프롬프트는 자동으로 새 도구 정보 반영

4. **의사결정 투명성**
   - `reasoning`: 왜 이 도구를 선택했는지 설명
   - `confidence`: 판단의 확신도
   - 향후 로깅 시 이 정보 저장 → 패턴 분석 가능

---

## 다음 단계: Phase 2

Phase 1에서 LLM이 도구를 선택하는 시스템을 구축했습니다.
이제 **Phase 2: Decision Logging System**을 구현하여 LLM의 의사결정 데이터를 수집해야 합니다.

### Phase 2 목표

1. **DecisionLogger 클래스 생성**
   - SQLite 기반 로깅 시스템
   - agent_decisions, tool_decisions 테이블

2. **로깅 통합**
   - PlanningAgent: 에이전트 선택 로깅
   - SearchExecutor: 도구 선택 + 실행 결과 로깅
   - AnalysisExecutor: 도구 선택 + 실행 결과 로깅

3. **데이터 수집 시작**
   - 실제 사용자 질문
   - LLM 선택 (도구, 에이전트)
   - 실행 결과 (성공/실패, 결과 품질)
   - 시간 정보 (실행 시간)

이 데이터를 수집하면 나중에:
- 어떤 질문에 어떤 도구가 효과적인지 분석
- 실제 사용 패턴 기반 규칙 생성
- LLM 프롬프트 개선

---

## 참고 자료

- 수정 계획서: `reports/revised_plan_tool_selection.md`
- Search 프롬프트: `llm_manager/prompts/execution/tool_selection_search.txt`
- Analysis 프롬프트: `llm_manager/prompts/execution/tool_selection_analysis.txt`
- SearchExecutor: `execution_agents/search_executor.py`
- AnalysisExecutor: `execution_agents/analysis_executor.py`
