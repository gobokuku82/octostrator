# 채팅 히스토리 기반 분석 직접 실행 가능성 분석 보고서

**작성일**: 2025-10-22
**버전**: 1.0
**분석 대상**: LangGraph 0.6 기반 Multi-Agent 챗봇 시스템
**핵심 질문**: 채팅 히스토리에 정보가 있다면 정보검색 없이 바로 분석 에이전트를 실행할 수 있는가?

---

## 📋 목차

1. [Executive Summary](#executive-summary)
2. [시스템 아키텍처 개요](#시스템-아키텍처-개요)
3. [현재 워크플로우 분석](#현재-워크플로우-분석)
4. [채팅 히스토리 관리 메커니즘](#채팅-히스토리-관리-메커니즘)
5. [정보검색 에이전트 조건 분석](#정보검색-에이전트-조건-분석)
6. [분석 에이전트 실행 조건 분석](#분석-에이전트-실행-조건-분석)
7. [직접 분석 가능성 판단](#직접-분석-가능성-판단)
8. [구현 시나리오 및 제약사항](#구현-시나리오-및-제약사항)
9. [권장사항 및 구현 가이드](#권장사항-및-구현-가이드)
10. [결론](#결론)

---

## 1. Executive Summary

### 핵심 발견사항

**✅ 현재 시스템 상태**: **직접 분석 실행 가능 (부분적)**

채팅 히스토리에 충분한 정보가 있을 경우, 정보검색 에이전트를 건너뛰고 분석 에이전트를 직접 실행하는 것이 **기술적으로 가능**합니다. 다만 현재 구현은 항상 순차적으로 실행되므로, 이를 활성화하려면 **라우팅 로직 개선**이 필요합니다.

### 주요 결과

| 항목 | 현재 상태 | 직접 분석 가능 여부 | 필요 작업 |
|------|-----------|-------------------|----------|
| **채팅 히스토리 로드** | ✅ 구현됨 | ✅ 가능 | 없음 (이미 동작 중) |
| **Intent 분석 시 히스토리 활용** | ✅ 구현됨 | ✅ 가능 | 없음 (context 전달 중) |
| **SearchTeam 건너뛰기** | ❌ 미구현 | ✅ 가능 | 라우팅 로직 추가 필요 |
| **AnalysisTeam 직접 실행** | ⚠️ 제한적 | ✅ 가능 | input_data 검증 로직 필요 |
| **충분성 판단 로직** | ❌ 미구현 | ⚠️ 어려움 | LLM 기반 판단 필요 |

### 권장사항 요약

1. **Phase 1 (기초)**: 명시적 키워드 기반 건너뛰기 ("방금 검색한 데이터로 분석해줘")
2. **Phase 2 (고급)**: LLM 기반 자동 판단 (대화 컨텍스트 분석)
3. **Phase 3 (최적)**: Hybrid 방식 (키워드 + LLM + 사용자 확인)

---

## 2. 시스템 아키텍처 개요

### 2.1 LangGraph 0.6 기반 Multi-Agent 구조

```
TeamBasedSupervisor (LangGraph StateGraph)
    ├── initialize_node
    ├── planning_node (PlanningAgent)
    │   ├── analyze_intent (LLM #1)
    │   ├── suggest_agents (LLM #2)
    │   └── create_execution_plan
    ├── route_after_planning (조건부 라우팅)
    ├── execute_teams_node
    │   ├── SearchExecutor (정보 수집)
    │   │   ├── LegalSearchTool
    │   │   ├── MarketDataTool
    │   │   └── LoanDataTool
    │   └── AnalysisExecutor (데이터 분석)
    │       ├── ContractAnalysisTool
    │       ├── MarketAnalysisTool
    │       └── ROICalculatorTool
    ├── aggregate_results_node
    └── generate_response_node (LLM #10)
```

**파일 위치**:
- Supervisor: [`team_supervisor.py`](../../backend/app/service_agent/supervisor/team_supervisor.py)
- Planning: [`planning_agent.py`](../../backend/app/service_agent/cognitive_agents/planning_agent.py)
- SearchExecutor: [`search_executor.py`](../../backend/app/service_agent/execution_agents/search_executor.py)
- AnalysisExecutor: [`analysis_executor.py`](../../backend/app/service_agent/execution_agents/analysis_executor.py)

### 2.2 핵심 State 관리

```python
MainSupervisorState (TypedDict)
    ├── query: str                              # 사용자 쿼리
    ├── session_id: str                         # WebSocket 세션 ID
    ├── chat_session_id: str                    # 채팅 세션 ID (히스토리용)
    ├── user_id: Optional[int]                  # 사용자 ID (Long-term Memory)
    ├── planning_state: PlanningState           # 계획 수립 결과
    ├── active_teams: List[str]                 # 실행할 팀 목록
    ├── team_results: Dict[str, Any]            # 팀별 실행 결과
    ├── loaded_memories: List[Dict]             # 로드된 대화 기록
    └── tiered_memories: Dict                   # 3-Tier Hybrid Memory
```

**참조 문서**: [STATE_MANAGEMENT_GUIDE.md](../../Manual/STATE_MANAGEMENT_GUIDE.md)

---

## 3. 현재 워크플로우 분석

### 3.1 전체 실행 흐름

**코드 위치**: [`team_supervisor.py:1231-1348`](../../backend/app/service_agent/supervisor/team_supervisor.py#L1231-L1348)

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str = "default",
    chat_session_id: Optional[str] = None,
    user_id: Optional[int] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
```

**실행 단계**:

1. **초기화** (`initialize_node`) - [L157-172](../../backend/app/service_agent/supervisor/team_supervisor.py#L157-L172)
   ```python
   state["start_time"] = datetime.now()
   state["status"] = "initialized"
   state["active_teams"] = []
   state["team_results"] = {}
   ```

2. **계획 수립** (`planning_node`) - [L174-417](../../backend/app/service_agent/supervisor/team_supervisor.py#L174-L417)
   - **Long-term Memory 로드** - [L235-271](../../backend/app/service_agent/supervisor/team_supervisor.py#L235-L271)
   - **Chat History 조회** - [L200-207](../../backend/app/service_agent/supervisor/team_supervisor.py#L200-L207)
   - **Intent 분석** - [L210](../../backend/app/service_agent/supervisor/team_supervisor.py#L210)
   - **Agent 선택** - [L317](../../backend/app/service_agent/supervisor/team_supervisor.py#L317)
   - **Execution Plan 생성** - [L320-363](../../backend/app/service_agent/supervisor/team_supervisor.py#L320-L363)

3. **라우팅** (`route_after_planning`) - [L130-155](../../backend/app/service_agent/supervisor/team_supervisor.py#L130-L155)
   ```python
   def _route_after_planning(self, state: MainSupervisorState) -> str:
       # IRRELEVANT/UNCLEAR → "respond"
       # execution_steps 있음 → "execute"
       # 없음 → "respond"
   ```

4. **팀 실행** (`execute_teams_node`) - [L567-618](../../backend/app/service_agent/supervisor/team_supervisor.py#L567-L618)
   - **순차 실행** (`_execute_teams_sequential`) - [L716-818](../../backend/app/service_agent/supervisor/team_supervisor.py#L716-L818)
   - **병렬 실행** (`_execute_teams_parallel`) - [L620-714](../../backend/app/service_agent/supervisor/team_supervisor.py#L620-L714)

5. **결과 집계** (`aggregate_results_node`) - [L883-912](../../backend/app/service_agent/supervisor/team_supervisor.py#L883-L912)

6. **응답 생성** (`generate_response_node`) - [L914-1000](../../backend/app/service_agent/supervisor/team_supervisor.py#L914-L1000)
   - **Long-term Memory 저장** - [L959-997](../../backend/app/service_agent/supervisor/team_supervisor.py#L959-L997)

### 3.2 현재 팀 실행 로직

**코드 위치**: [`team_supervisor.py:716-818`](../../backend/app/service_agent/supervisor/team_supervisor.py#L716-L818)

```python
async def _execute_teams_sequential(
    self,
    teams: List[str],
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """팀 순차 실행"""
    results = {}

    for team_name in teams:
        # ✅ 현재: 모든 팀을 순서대로 실행
        result = await self._execute_single_team(team_name, shared_state, main_state)
        results[team_name] = result

        # ✅ SearchTeam → AnalysisTeam 데이터 전달
        if team_name == "search" and "analysis" in teams:
            main_state["team_results"][team_name] = self._extract_team_data(result, team_name)

    return results
```

**핵심 발견**:
- 현재는 `active_teams`에 있는 모든 팀을 **무조건 순차 실행**
- SearchTeam 결과를 `team_results`에 저장 → AnalysisTeam이 `input_data`로 사용
- **건너뛰기 로직 없음** → 채팅 히스토리에 데이터가 있어도 SearchTeam 실행

---

## 4. 채팅 히스토리 관리 메커니즘

### 4.1 Chat History 로드 (단기 메모리)

**코드 위치**: [`team_supervisor.py:1105-1162`](../../backend/app/service_agent/supervisor/team_supervisor.py#L1105-L1162)

```python
async def _get_chat_history(
    self,
    session_id: Optional[str],
    limit: int = 3  # 최근 3개 대화 쌍 (6개 메시지)
) -> List[Dict[str, str]]:
    """
    Chat history 조회 (최근 N개 대화 쌍)

    Returns:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
    """
```

**동작 방식**:
1. `chat_messages` 테이블에서 최근 메시지 조회
2. `created_at` 기준 시간순 정렬
3. 각 메시지 500자로 제한 (컨텍스트 윈도우 관리)

**사용 지점**:
```python
# planning_node에서 호출 (L200-207)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3
)

# Intent 분석 시 context로 전달 (L208-210)
context = {"chat_history": chat_history} if chat_history else None
intent_result = await self.planning_agent.analyze_intent(query, context)
```

### 4.2 Long-term Memory 로드 (장기 메모리)

**코드 위치**: [`team_supervisor.py:235-271`](../../backend/app/service_agent/supervisor/team_supervisor.py#L235-L271)

```python
# ✅ 3-Tier Hybrid Memory 로드
tiered_memories = await memory_service.load_tiered_memories(
    user_id=user_id,
    current_session_id=chat_session_id
)

state["tiered_memories"] = tiered_memories
state["loaded_memories"] = (
    tiered_memories.get("shortterm", []) +
    tiered_memories.get("midterm", []) +
    tiered_memories.get("longterm", [])
)
```

**3-Tier 구조**:

| Tier | 범위 | 데이터 형식 | 토큰 제한 |
|------|------|-----------|---------|
| **Short-term** | 1-5 세션 | 전체 메시지 | 최대 16K |
| **Mid-term** | 6-10 세션 | LLM 요약 | 최대 16K |
| **Long-term** | 11-20 세션 | LLM 요약 | 최대 16K |

**코드 위치**: [`simple_memory_service.py:393-536`](../../backend/app/service_agent/foundation/simple_memory_service.py#L393-L536)

### 4.3 Intent 분석 시 히스토리 활용

**코드 위치**: [`planning_agent.py:183-248`](../../backend/app/service_agent/cognitive_agents/planning_agent.py#L183-L248)

```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    # Context에서 chat_history 추출
    chat_history = context.get("chat_history", []) if context else []

    # Chat history를 문자열로 포맷팅
    chat_history_text = ""
    if chat_history:
        formatted_history = []
        for msg in chat_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(f"사용자: {content}")
            elif role == "assistant":
                formatted_history.append(f"AI: {content}")

        if formatted_history:
            chat_history_text = "\n".join(formatted_history)

    # LLM에 전달
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={
            "query": query,
            "chat_history": chat_history_text  # ✅ 히스토리 전달
        },
        temperature=0.0,
        max_tokens=500
    )
```

**프롬프트 위치**: [`backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`](../../backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt)

**핵심 발견**:
- Intent 분석 시 채팅 히스토리가 **이미 활용**되고 있음
- 그러나 **데이터 충분성 판단 로직은 없음**
- Intent만 분석하고, "이전 대화에 필요한 데이터가 있는지" 판단하지 않음

---

## 5. 정보검색 에이전트 조건 분석

### 5.1 SearchExecutor 실행 조건

**코드 위치**: [`search_executor.py:859-908`](../../backend/app/service_agent/execution_agents/search_executor.py#L859-L908)

```python
async def execute(
    self,
    shared_state: SharedState,
    search_scope: Optional[List[str]] = None,
    keywords: Optional[Dict] = None
) -> SearchTeamState:
    """
    SearchTeam 실행

    Args:
        shared_state: 공유 상태 (필수)
        search_scope: 검색 범위 (선택적)
        keywords: 검색 키워드 (선택적)
    """
```

**실행 조건**:
1. **필수**: `shared_state` (query, session_id 포함)
2. **선택적**: `search_scope` (없으면 자동 결정)
3. **선택적**: `keywords` (없으면 자동 추출)

**자동 결정 로직**:
```python
# prepare_search_node (L150-173)
if not state.get("keywords"):
    query = state.get("shared_context", {}).get("query", "")
    state["keywords"] = self._extract_keywords(query)

if not state.get("search_scope"):
    state["search_scope"] = self._determine_search_scope(state["keywords"])
```

### 5.2 SearchExecutor 내부 워크플로우

**서브그래프 구조** - [L112-142](../../backend/app/service_agent/execution_agents/search_executor.py#L112-L142):

```
prepare → route → [search → aggregate] → finalize
                   ↓ (skip 가능)
                finalize
```

**라우팅 조건** - [L144-148](../../backend/app/service_agent/execution_agents/search_executor.py#L144-L148):
```python
def _route_decision(self, state: SearchTeamState) -> str:
    if not state.get("search_scope"):
        return "skip"  # ✅ search_scope가 없으면 건너뛰기
    return "search"
```

**핵심 발견**:
- SearchExecutor 내부에는 **건너뛰기 로직 존재** (`route_decision`)
- 그러나 Supervisor에서 SearchExecutor를 **무조건 호출**하므로 의미 없음
- 건너뛰려면 **Supervisor 레벨에서 active_teams 조정 필요**

### 5.3 SearchExecutor 출력 데이터

**코드 위치**: [`search_executor.py:789-833`](../../backend/app/service_agent/execution_agents/search_executor.py#L789-L833)

```python
async def aggregate_results_node(self, state: SearchTeamState) -> SearchTeamState:
    state["aggregated_results"] = {
        "total_count": total_results,
        "by_type": {
            "legal": len(state.get("legal_results", [])),
            "real_estate": len(state.get("real_estate_results", [])),
            "loan": len(state.get("loan_results", [])),
            "property_search": len(state.get("property_search_results", []))
        },
        "sources": sources,
        "keywords_used": state.get("keywords", {})
    }
```

**Supervisor로 전달되는 데이터** - [`team_supervisor.py:863-881`](../../backend/app/service_agent/supervisor/team_supervisor.py#L863-L881):

```python
def _extract_team_data(self, team_state: Any, team_name: str) -> Dict:
    if team_name == "search":
        return {
            "legal_search": team_state.get("legal_results", []),
            "real_estate_search": team_state.get("real_estate_results", []),
            "loan_search": team_state.get("loan_results", [])
        }
```

**핵심 구조**:
- `legal_results`: List[Dict] - 법률 검색 결과
- `real_estate_results`: List[Dict] - 시세 검색 결과
- `loan_results`: List[Dict] - 대출 검색 결과
- `property_search_results`: List[Dict] - 개별 매물 검색 결과

---

## 6. 분석 에이전트 실행 조건 분석

### 6.1 AnalysisExecutor 실행 조건

**코드 위치**: [`analysis_executor.py:927-973`](../../backend/app/service_agent/execution_agents/analysis_executor.py#L927-L973)

```python
async def execute(
    self,
    shared_state: SharedState,
    analysis_type: str = "comprehensive",
    input_data: Optional[Dict] = None  # ✅ 핵심: input_data
) -> AnalysisTeamState:
    """
    AnalysisTeam 실행

    Args:
        shared_state: 공유 상태 (필수)
        analysis_type: 분석 타입 (선택적, 기본값: comprehensive)
        input_data: 입력 데이터 (선택적, SearchTeam 결과)
    """
```

**실행 조건**:
1. **필수**: `shared_state` (query, session_id 포함)
2. **선택적**: `analysis_type`
3. **선택적**: `input_data` (SearchTeam 결과 또는 채팅 히스토리 데이터)

**핵심 발견**:
- `input_data`가 **선택적 (Optional)** → None이어도 실행 가능!
- 내부에서 데이터 유무에 따라 다른 분석 수행

### 6.2 AnalysisExecutor input_data 처리

**코드 위치**: [`analysis_executor.py:934-963`](../../backend/app/service_agent/execution_agents/analysis_executor.py#L934-L963)

```python
# 입력 데이터 준비
analysis_inputs = []
if input_data:
    for source, data in input_data.items():
        analysis_inputs.append(AnalysisInput(
            data_source=source,  # "legal_search", "real_estate_search", etc.
            data=data,
            metadata={}
        ))

# 초기 상태 생성
initial_state = AnalysisTeamState(
    team_name=self.team_name,
    status="pending",
    shared_context=shared_state,
    analysis_type=analysis_type,
    input_data=analysis_inputs,  # ✅ 빈 리스트 가능
    ...
)
```

**전처리 노드** - [L308-324](../../backend/app/service_agent/execution_agents/analysis_executor.py#L308-L324):

```python
async def preprocess_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    preprocessed = {}
    for input_item in state.get("input_data", []):  # ✅ 빈 리스트도 처리
        preprocessed[input_item["data_source"]] = input_item.get("data", {})

    state["preprocessed_data"] = preprocessed  # ✅ 빈 dict도 가능
    return state
```

**분석 노드** - [L326-524](../../backend/app/service_agent/execution_agents/analysis_executor.py#L326-L524):

```python
async def analyze_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
    preprocessed_data = state.get("preprocessed_data", {})

    # LLM 기반 도구 선택
    collected_data_summary = {
        "has_legal_data": bool(preprocessed_data.get("legal_search")),
        "has_market_data": bool(preprocessed_data.get("real_estate_search")),
        "has_loan_data": bool(preprocessed_data.get("loan_search")),
        "has_contract": bool(preprocessed_data.get("contract")),
        "data_types": list(preprocessed_data.keys())
    }

    # ✅ 데이터 유무에 따라 선택적 도구 실행
    if "market_analysis" in selected_tools:
        property_data = self._extract_property_data(preprocessed_data, query)
        market_data = preprocessed_data.get("real_estate_search", {})
        results["market"] = await self.market_tool.execute(...)
```

**핵심 발견**:
- AnalysisExecutor는 **input_data 없이도 실행 가능**
- `preprocessed_data`가 비어있으면 일부 도구만 실행 (에러 없음)
- Query에서 직접 데이터 추출 시도 (`_extract_price`, `_extract_rent` 등)

### 6.3 채팅 히스토리 데이터 활용 가능성

**현재 코드**:
```python
# team_supervisor.py:841-847 - AnalysisTeam 호출
elif team_name == "analysis":
    # 이전 팀 결과 전달
    input_data = main_state.get("team_results", {})
    return await team.execute(
        shared_state,
        analysis_type="comprehensive",
        input_data=input_data  # ✅ SearchTeam 결과만 전달
    )
```

**가능한 개선**:
```python
elif team_name == "analysis":
    # ✅ 채팅 히스토리 데이터 추출
    input_data = self._extract_input_data_from_history_or_search(main_state)
    return await team.execute(
        shared_state,
        analysis_type="comprehensive",
        input_data=input_data
    )

def _extract_input_data_from_history_or_search(self, state: MainSupervisorState) -> Dict:
    """채팅 히스토리 또는 SearchTeam 결과에서 input_data 추출"""
    input_data = {}

    # 1차: SearchTeam 결과 확인
    team_results = state.get("team_results", {})
    if "search" in team_results:
        input_data.update(team_results["search"])

    # 2차: 채팅 히스토리에서 추출 (SearchTeam 결과 없을 때)
    if not input_data:
        loaded_memories = state.get("loaded_memories", [])
        # TODO: 메모리에서 legal_search, real_estate_search 등 추출

    return input_data
```

---

## 7. 직접 분석 가능성 판단

### 7.1 기술적 가능성 평가

| 요구사항 | 현재 구현 | 직접 분석 가능 여부 | 비고 |
|---------|---------|-------------------|------|
| **채팅 히스토리 로드** | ✅ 완료 | ✅ 가능 | `_get_chat_history`, `load_tiered_memories` 동작 중 |
| **Intent 분석 시 히스토리 활용** | ✅ 완료 | ✅ 가능 | `planning_agent.py` context 전달 중 |
| **데이터 충분성 판단** | ❌ 미구현 | ⚠️ 어려움 | LLM 기반 판단 또는 규칙 기반 필요 |
| **SearchTeam 건너뛰기** | ❌ 미구현 | ✅ 가능 | `active_teams` 조정 필요 |
| **AnalysisTeam 직접 실행** | ⚠️ 제한적 | ✅ 가능 | input_data 없어도 실행 가능 |
| **히스토리 데이터 추출** | ❌ 미구현 | ⚠️ 어려움 | 데이터 파싱 로직 필요 |
| **데이터 형식 표준화** | ⚠️ 부분적 | ⚠️ 어려움 | SearchTeam 형식과 호환 필요 |

### 7.2 시나리오별 실현 가능성

#### 시나리오 1: 명시적 키워드 기반

**사용자 요청 예시**:
```
사용자: "강남구 전세 시세 알려줘"
AI: [SearchTeam 실행] "강남구 전세 시세는 5억~7억입니다..."
사용자: "방금 검색한 데이터로 위험도 분석해줘"
```

**구현 난이도**: ⭐ (매우 쉬움)

**필요 작업**:
1. Intent 분석 시 "방금", "이전", "아까" 등 키워드 감지
2. `planning_node`에서 `active_teams`에 "search" 제외
3. 마지막 응답의 `team_results["search"]`를 재사용

**코드 예시**:
```python
# planning_agent.py - Intent 분석
if any(kw in query for kw in ["방금", "이전", "아까", "위에서"]):
    intent_result.use_previous_data = True

# team_supervisor.py - Planning Node
if intent_result.use_previous_data and state.get("team_results", {}).get("search"):
    # SearchTeam 건너뛰기
    active_teams = ["analysis"]
    state["using_cached_search"] = True
else:
    active_teams = ["search", "analysis"]
```

**제약사항**:
- 동일 세션 내에서만 동작 (session_id 기반)
- `team_results`가 State에 유지되는 경우만 가능
- 현재 State는 각 요청마다 초기화되므로 **Checkpointing 필요**

#### 시나리오 2: LLM 기반 자동 판단

**사용자 요청 예시**:
```
사용자: "강남구 전세 시세 알려줘"
AI: "강남구 전세 시세는 5억~7억입니다..."
사용자: "투자 수익률 계산해줘"
[LLM 판단: 이전 대화에 시세 정보 있음 → SearchTeam 건너뛰기]
```

**구현 난이도**: ⭐⭐⭐ (어려움)

**필요 작업**:
1. Intent 분석 시 채팅 히스토리 분석
2. LLM에게 "이전 대화에 필요한 데이터가 있는지" 판단 요청
3. 데이터 위치 추출 (몇 번째 대화, 어떤 정보)
4. 히스토리에서 데이터 파싱 및 표준화

**프롬프트 예시**:
```
# intent_analysis.txt 확장

## 이전 대화 분석

대화 히스토리:
{chat_history}

현재 쿼리: {query}

다음을 판단하세요:
1. 현재 쿼리 처리에 필요한 데이터 타입 (legal_data, market_data, loan_data)
2. 이전 대화에 해당 데이터가 있는지 여부
3. 있다면 어느 대화에서 어떤 정보인지 (JSON 형식)

출력 형식:
{
  "needs_data": ["market_data", "legal_data"],
  "available_in_history": {
    "market_data": {
      "found": true,
      "conversation_index": 1,
      "data_summary": "강남구 전세 시세 5억~7억"
    },
    "legal_data": {
      "found": false
    }
  },
  "needs_new_search": ["legal_data"],
  "can_skip_search": ["market_data"]
}
```

**제약사항**:
- LLM 호출 비용 증가 (Intent 분석 복잡도 증가)
- 데이터 파싱 정확도 문제 (LLM이 잘못 판단 가능)
- 히스토리 길이 제한 (최근 3개 대화만 → 오래된 데이터 찾기 어려움)

#### 시나리오 3: Hybrid 방식 (권장)

**동작 방식**:
1. **1차**: 명시적 키워드 감지 ("방금", "이전")
2. **2차**: LLM 자동 판단 (Intent 분석 시)
3. **3차**: 사용자 확인 (불확실한 경우)

**예시**:
```
사용자: "투자 수익률 계산해줘"
AI: [LLM 판단: 이전 대화에 시세 정보 있음, 확신도 80%]
    "이전 대화의 강남구 시세 정보(5억~7억)를 사용하여 분석하시겠습니까?
     또는 최신 정보를 다시 검색하시겠습니까?"
사용자: "이전 정보 사용해"
AI: [AnalysisTeam만 실행]
```

**구현 난이도**: ⭐⭐⭐⭐ (매우 어려움)

**필요 작업**:
- 시나리오 1 + 시나리오 2 + Human-in-the-Loop 구현
- WebSocket을 통한 사용자 확인 UI
- State 관리 복잡도 증가

### 7.3 State 관리 이슈

#### 문제점: State 초기화

**현재 코드** - [`team_supervisor.py:1268-1295`](../../backend/app/service_agent/supervisor/team_supervisor.py#L1268-L1295):

```python
# 초기 상태 생성 (매 요청마다 새로 생성)
initial_state = MainSupervisorState(
    query=query,
    session_id=session_id,
    chat_session_id=chat_session_id,
    request_id=f"req_{datetime.now().timestamp()}",
    user_id=user_id,
    planning_state=None,
    execution_plan=None,
    search_team_state=None,  # ✅ 항상 None
    document_team_state=None,
    analysis_team_state=None,
    current_phase="",
    active_teams=[],
    completed_teams=[],
    failed_teams=[],
    team_results={},  # ✅ 항상 빈 dict
    ...
)
```

**이슈**:
- `team_results`가 매 요청마다 초기화됨
- 이전 요청의 SearchTeam 결과가 사라짐
- 명시적 키워드 방식도 작동 불가

#### 해결 방법: Checkpointing 활용

**현재 구현** - [L1164-1198](../../backend/app/service_agent/supervisor/team_supervisor.py#L1164-L1198):

```python
async def _ensure_checkpointer(self):
    """Checkpointer 초기화"""
    if not self._checkpointer_initialized:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
        self.checkpointer = await self._checkpoint_cm.__aenter__()
        await self.checkpointer.setup()

        self._checkpointer_initialized = True
```

**사용 방법** - [L1299-1314](../../backend/app/service_agent/supervisor/team_supervisor.py#L1299-L1314):

```python
if self.checkpointer:
    thread_id = chat_session_id if chat_session_id else session_id
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    final_state = await self.app.ainvoke(initial_state, config=config)
```

**활용 방안**:
1. Checkpointing 활성화 (이미 구현됨)
2. 동일 `thread_id` (chat_session_id) 사용 시 State 복원
3. 이전 요청의 `team_results` 접근 가능

**코드 예시**:
```python
# Checkpointing에서 이전 State 로드
if self.checkpointer and chat_session_id:
    previous_state = await self.checkpointer.aget(
        config={"configurable": {"thread_id": chat_session_id}}
    )

    if previous_state and previous_state.get("team_results"):
        # 이전 검색 결과 재사용
        initial_state["cached_team_results"] = previous_state["team_results"]
```

---

## 8. 구현 시나리오 및 제약사항

### 8.1 Phase 1: 명시적 키워드 기반 (단기)

**목표**: 사용자가 명시적으로 요청 시 이전 데이터 재사용

**구현 단계**:

1. **Intent 분석 확장** - `planning_agent.py` 수정
   ```python
   # 키워드 리스트
   REUSE_KEYWORDS = ["방금", "이전", "아까", "위에서", "앞에서", "직전"]

   # Intent 분석 후
   if any(kw in query for kw in REUSE_KEYWORDS):
       intent_result.reuse_previous_data = True
   ```

2. **Planning Node 수정** - `team_supervisor.py:174-417`
   ```python
   # Checkpointing에서 이전 State 로드
   previous_search_results = None
   if self.checkpointer and chat_session_id:
       prev_state = await self._get_previous_state(chat_session_id)
       if prev_state:
           previous_search_results = prev_state.get("team_results", {}).get("search")

   # Intent에 reuse 플래그 있고, 이전 데이터 있으면 SearchTeam 제외
   if intent_result.reuse_previous_data and previous_search_results:
       # SearchTeam 제외, AnalysisTeam만 포함
       selected_agents = [a for a in intent_result.suggested_agents if a != "search_team"]
       state["cached_search_results"] = previous_search_results
   ```

3. **AnalysisTeam 호출 수정** - `team_supervisor.py:840-847`
   ```python
   elif team_name == "analysis":
       # 캐시된 데이터 또는 SearchTeam 결과 사용
       if state.get("cached_search_results"):
           input_data = state["cached_search_results"]
       else:
           input_data = main_state.get("team_results", {})

       return await team.execute(
           shared_state,
           analysis_type="comprehensive",
           input_data=input_data
       )
   ```

**예상 효과**:
- ✅ SearchTeam 건너뛰기 → 3~5초 단축
- ✅ 사용자 제어 가능 (명시적 요청)
- ✅ 오류 위험 낮음

**제약사항**:
- ❌ 사용자가 매번 "방금"이라고 말해야 함
- ❌ 자동 판단 불가

### 8.2 Phase 2: LLM 기반 자동 판단 (중기)

**목표**: LLM이 자동으로 이전 대화 분석 및 데이터 충분성 판단

**구현 단계**:

1. **Intent 분석 프롬프트 확장** - `intent_analysis.txt` 수정
   ```
   ## 추가 분석: 이전 대화 활용 가능성

   대화 히스토리:
   {chat_history}

   현재 쿼리: {query}

   다음을 판단하세요:
   1. 현재 쿼리가 이전 대화의 연속인지? (yes/no)
   2. 필요한 데이터가 이전 대화에 있는지? (yes/no)
   3. 새로운 검색이 필요한지? (yes/no)
   4. 재사용 가능한 데이터 타입: (legal_data, market_data, loan_data 중 선택)

   출력 JSON:
   {
     "is_continuation": true,
     "previous_data_sufficient": true,
     "needs_new_search": false,
     "reusable_data_types": ["market_data"],
     "confidence": 0.85
   }
   ```

2. **Planning Node 수정**
   ```python
   # Intent 분석 결과 확인
   if intent_result.previous_data_sufficient:
       # Checkpointing에서 이전 데이터 추출
       reusable_data = await self._extract_reusable_data(
           chat_session_id,
           intent_result.reusable_data_types
       )

       if reusable_data:
           # SearchTeam 제외
           selected_agents = self._filter_search_team(intent_result.suggested_agents)
           state["reused_data"] = reusable_data
   ```

3. **데이터 추출 로직**
   ```python
   async def _extract_reusable_data(
       self,
       chat_session_id: str,
       data_types: List[str]
   ) -> Dict:
       """Checkpointing에서 특정 타입의 데이터 추출"""
       prev_state = await self._get_previous_state(chat_session_id)
       if not prev_state:
           return {}

       team_results = prev_state.get("team_results", {}).get("search", {})
       reusable = {}

       for data_type in data_types:
           key_map = {
               "legal_data": "legal_search",
               "market_data": "real_estate_search",
               "loan_data": "loan_search"
           }
           key = key_map.get(data_type)
           if key and key in team_results:
               reusable[key] = team_results[key]

       return reusable
   ```

**예상 효과**:
- ✅ 사용자가 명시하지 않아도 자동 판단
- ✅ 자연스러운 대화 흐름
- ✅ 불필요한 검색 최소화

**제약사항**:
- ❌ LLM 호출 비용 증가 (Intent 분석 복잡도 증가)
- ❌ 잘못된 판단 가능성 (정확도 문제)
- ❌ 채팅 히스토리 길이 제한 (최근 3개 대화)

### 8.3 Phase 3: Hybrid + Human-in-the-Loop (장기)

**목표**: LLM 자동 판단 + 불확실 시 사용자 확인

**구현 단계**:

1. **Intent 분석에 confidence 추가**
   ```python
   {
     "previous_data_sufficient": true,
     "confidence": 0.65,  # ✅ 낮은 확신도
     "uncertainty_reason": "시세 데이터가 1주일 전 것임"
   }
   ```

2. **Planning Node에서 사용자 확인 요청**
   ```python
   if intent_result.previous_data_sufficient:
       if intent_result.confidence < 0.8:
           # 사용자 확인 요청 (WebSocket)
           await progress_callback("user_confirmation_required", {
               "message": f"이전 대화의 데이터를 사용하시겠습니까? ({intent_result.uncertainty_reason})",
               "options": ["예, 이전 데이터 사용", "아니요, 최신 정보 검색"]
           })

           # 응답 대기 (Human-in-the-Loop)
           user_choice = await self._wait_for_user_response(session_id)

           if user_choice == "use_previous":
               # SearchTeam 건너뛰기
               ...
   ```

3. **WebSocket 메시지 프로토콜 확장**
   ```typescript
   // frontend/lib/types.ts
   type WebSocketMessage =
     | { type: "plan_ready"; ... }
     | { type: "user_confirmation_required"; message: string; options: string[] }
     | { type: "user_response"; choice: string }
   ```

**예상 효과**:
- ✅ 최고의 정확도 (사용자 최종 결정)
- ✅ 투명성 (왜 이전 데이터인지 설명)
- ✅ 사용자 신뢰도 향상

**제약사항**:
- ❌ 구현 복잡도 매우 높음
- ❌ WebSocket 양방향 통신 필요
- ❌ 사용자 대기 시간 증가

### 8.4 데이터 형식 표준화 이슈

**문제점**: 채팅 히스토리 데이터 vs SearchTeam 출력 형식

**SearchTeam 출력 형식** - [`search_executor.py:863-881`](../../backend/app/service_agent/execution_agents/search_executor.py#L863-L881):
```python
{
    "legal_search": [
        {
            "law_title": "주택임대차보호법",
            "article_number": "제7조의2",
            "content": "...",
            "relevance_score": 0.95
        }
    ],
    "real_estate_search": [
        {
            "region": "강남구",
            "avg_deposit": 50000000,
            "transaction_count": 100
        }
    ]
}
```

**채팅 히스토리 데이터 (AI 응답)** - [`team_supervisor.py:914-1000`](../../backend/app/service_agent/supervisor/team_supervisor.py#L914-L1000):
```
"강남구 전세 시세는 평균 5억~7억 사이입니다. 최근 3개월 거래량은 100건입니다..."
```

**문제**:
- AI 응답은 **자연어 문자열**
- SearchTeam 출력은 **구조화된 JSON**
- AnalysisTeam은 구조화된 데이터 기대

**해결 방안 1**: Long-term Memory에 SearchTeam 결과 저장

```python
# generate_response_node에서 Long-term Memory 저장 시
await memory_service.save_conversation(
    user_id=user_id,
    session_id=chat_session_id,
    messages=[],
    summary=response_summary,
    structured_data=state.get("team_results", {})  # ✅ 추가
)
```

**해결 방안 2**: LLM으로 자연어 → JSON 변환

```python
# 채팅 히스토리에서 데이터 추출
conversation = "강남구 전세 시세는 평균 5억~7억 사이입니다..."
structured_data = await llm_service.complete_json_async(
    prompt_name="extract_structured_data",
    variables={"conversation": conversation}
)
# 출력: {"region": "강남구", "avg_deposit": 600000000, ...}
```

---

## 9. 권장사항 및 구현 가이드

### 9.1 단기 권장사항 (1주 이내)

**Phase 1 구현: 명시적 키워드 기반**

1. **파일 수정 목록**:
   - [`planning_agent.py`](../../backend/app/service_agent/cognitive_agents/planning_agent.py) - Intent 분석 확장
   - [`team_supervisor.py`](../../backend/app/service_agent/supervisor/team_supervisor.py) - Planning Node 수정
   - [`separated_states.py`](../../backend/app/service_agent/foundation/separated_states.py) - State 필드 추가

2. **코드 변경**:

   **1) `planning_agent.py` - IntentResult에 필드 추가** (L54-64):
   ```python
   @dataclass
   class IntentResult:
       intent_type: IntentType
       confidence: float
       keywords: List[str] = field(default_factory=list)
       reasoning: str = ""
       entities: Dict[str, Any] = field(default_factory=dict)
       suggested_agents: List[str] = field(default_factory=list)
       fallback: bool = False
       reuse_previous_data: bool = False  # ✅ 추가
   ```

   **2) `planning_agent.py` - Intent 분석 후 키워드 체크** (L210 이후):
   ```python
   intent_result = await self.planning_agent.analyze_intent(query, context)

   # ✅ 키워드 기반 이전 데이터 재사용 감지
   REUSE_KEYWORDS = ["방금", "이전", "아까", "위에서", "앞에서", "직전", "그거", "그걸"]
   if any(kw in query for kw in REUSE_KEYWORDS):
       intent_result.reuse_previous_data = True
       logger.info(f"Detected reuse keyword in query: {query}")
   ```

   **3) `team_supervisor.py` - Planning Node 수정** (L317 이전):
   ```python
   # ✅ 이전 검색 결과 로드 (Checkpointing)
   previous_search_results = None
   if self.checkpointer and chat_session_id:
       try:
           prev_config = {"configurable": {"thread_id": chat_session_id}}
           prev_checkpoint = await self.checkpointer.aget(prev_config)

           if prev_checkpoint and prev_checkpoint.values:
               prev_state = prev_checkpoint.values
               previous_search_results = prev_state.get("team_results", {}).get("search")

               if previous_search_results:
                   logger.info(f"Found previous search results in checkpoint: {list(previous_search_results.keys())}")
       except Exception as e:
           logger.warning(f"Failed to load previous checkpoint: {e}")

   # ✅ 재사용 플래그 있고 이전 데이터 있으면 SearchTeam 제외
   if intent_result.reuse_previous_data and previous_search_results:
       logger.info("Reusing previous search results, skipping SearchTeam")

       # SearchTeam 제외
       selected_agents = [a for a in intent_result.suggested_agents if a != "search_team"]

       # 캐시된 데이터 저장
       state["cached_search_results"] = previous_search_results
       state["search_skipped"] = True
   else:
       selected_agents = intent_result.suggested_agents
   ```

   **4) `team_supervisor.py` - _execute_single_team 수정** (L840-847):
   ```python
   elif team_name == "analysis":
       # ✅ 캐시된 검색 결과 또는 새 검색 결과 사용
       if main_state.get("cached_search_results"):
           input_data = main_state["cached_search_results"]
           logger.info("Using cached search results for AnalysisTeam")
       else:
           input_data = main_state.get("team_results", {})

       return await team.execute(
           shared_state,
           analysis_type="comprehensive",
           input_data=input_data
       )
   ```

3. **테스트 시나리오**:
   ```
   # 1차 쿼리
   사용자: "강남구 아파트 전세 시세 알려줘"
   AI: [SearchTeam 실행] "강남구 전세 시세는 5억~7억입니다..."

   # 2차 쿼리 (재사용)
   사용자: "방금 검색한 데이터로 위험도 분석해줘"
   AI: [SearchTeam 건너뛰기, AnalysisTeam만 실행] "시세 데이터 기반 위험도는..."

   # 3차 쿼리 (새 검색)
   사용자: "서초구는 어때?"
   AI: [SearchTeam + AnalysisTeam 실행]
   ```

4. **주의사항**:
   - Checkpointing이 **활성화**되어야 함 (`enable_checkpointing=True`)
   - 동일 `chat_session_id` 사용해야 이전 State 접근 가능
   - WebSocket 연결 유지 필요

### 9.2 중기 권장사항 (1개월 이내)

**Phase 2 구현: LLM 기반 자동 판단**

1. **프롬프트 파일 수정**:
   - [`intent_analysis.txt`](../../backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt) 확장

2. **프롬프트 예시**:
   ```
   ## 대화 연속성 분석

   대화 히스토리:
   {chat_history}

   현재 쿼리: {query}

   ### 판단 기준

   1. **대화 연속성**: 현재 쿼리가 이전 대화의 후속 질문인가?
      - "그거 분석해줘", "위험도는?", "수익률 계산해줘" → 연속성 있음
      - "서초구 시세 알려줘" → 새로운 질문

   2. **데이터 충분성**: 이전 대화에 필요한 데이터가 있는가?
      - 필요 데이터: legal_data (법률), market_data (시세), loan_data (대출)
      - 이전 대화에서 제공된 데이터 확인

   3. **신선도**: 이전 데이터가 여전히 유효한가?
      - 시세 데이터: 1주일 이내 → 유효
      - 법률 데이터: 변경 없음 → 유효

   ### 출력 JSON

   {
     "is_continuation": true/false,
     "previous_data_sufficient": true/false,
     "needs_new_search": true/false,
     "reusable_data_types": ["market_data", "legal_data"],
     "confidence": 0.0~1.0,
     "reasoning": "이전 대화에서 강남구 시세 정보 제공됨, 분석 가능"
   }
   ```

3. **Intent 분석 확장**:
   ```python
   # planning_agent.py
   result = await self.llm_service.complete_json_async(
       prompt_name="intent_analysis",
       variables={
           "query": query,
           "chat_history": chat_history_text
       },
       temperature=0.0,
       max_tokens=800  # ✅ 증가 (기존 500)
   )

   # ✅ 추가 필드 파싱
   intent_result.is_continuation = result.get("is_continuation", False)
   intent_result.previous_data_sufficient = result.get("previous_data_sufficient", False)
   intent_result.reusable_data_types = result.get("reusable_data_types", [])
   intent_result.confidence = result.get("confidence", 0.0)
   ```

### 9.3 장기 권장사항 (3개월 이내)

**Phase 3 구현: Hybrid + Human-in-the-Loop**

1. **WebSocket 메시지 프로토콜 확장**:
   ```typescript
   // frontend/lib/types.ts

   interface UserConfirmationMessage {
     type: "user_confirmation_required";
     confirmation_id: string;
     message: string;
     context: {
       previous_data_summary: string;
       data_age: string;  // "3분 전", "1일 전"
       uncertainty_reason: string;
     };
     options: Array<{
       value: string;
       label: string;
       description: string;
     }>;
   }

   // 사용 예시
   {
     type: "user_confirmation_required",
     confirmation_id: "conf_12345",
     message: "이전 대화의 데이터를 사용하시겠습니까?",
     context: {
       previous_data_summary: "강남구 전세 시세 (5억~7억)",
       data_age: "3분 전",
       uncertainty_reason: "최신 데이터 확인 필요"
     },
     options: [
       {
         value: "use_previous",
         label: "예, 이전 데이터 사용",
         description: "검색 시간 3초 단축"
       },
       {
         value: "search_new",
         label: "아니요, 최신 정보 검색",
         description: "최신 시세로 분석"
       }
     ]
   }
   ```

2. **Backend 구현**:
   ```python
   # team_supervisor.py

   async def _wait_for_user_confirmation(
       self,
       session_id: str,
       confirmation_data: Dict
   ) -> str:
       """
       사용자 확인 대기 (Human-in-the-Loop)

       Returns:
           "use_previous" | "search_new"
       """
       # 확인 요청 전송
       progress_callback = self._progress_callbacks.get(session_id)
       if progress_callback:
           await progress_callback("user_confirmation_required", confirmation_data)

       # 응답 대기 (타임아웃 30초)
       response = await asyncio.wait_for(
           self._wait_for_response_event(session_id),
           timeout=30.0
       )

       return response.get("choice", "search_new")  # 기본값: 새 검색
   ```

### 9.4 성능 영향 평가

| 시나리오 | SearchTeam 실행 시간 | AnalysisTeam 실행 시간 | 총 절감 시간 | 절감률 |
|---------|-------------------|---------------------|------------|--------|
| **현재 (항상 검색)** | 3~5초 | 2~3초 | - | - |
| **Phase 1 (키워드)** | 0초 (건너뛰기) | 2~3초 | 3~5초 | 60% |
| **Phase 2 (LLM 판단)** | 0초 | 2~3초 | 3~5초 | 60% |
| **Phase 3 (Hybrid)** | 0~5초 (조건부) | 2~3초 | 0~5초 | 0~60% |

**비용 영향**:
- Phase 1: ✅ LLM 호출 비용 변화 없음
- Phase 2: ⚠️ Intent 분석 복잡도 증가 → 약 20% 비용 증가
- Phase 3: ⚠️ WebSocket 유지 비용 증가

---

## 10. 결론

### 10.1 핵심 답변

**질문**: 채팅 히스토리에 정보가 있다면 바로 분석 에이전트(팀)이 실행될 수 있는가?

**답변**: **✅ 가능하지만, 현재 시스템에서는 활성화되어 있지 않습니다.**

**현재 상태**:
1. ✅ 채팅 히스토리 로드 기능 **구현됨**
2. ✅ Intent 분석 시 히스토리 활용 **구현됨**
3. ❌ 데이터 충분성 판단 **미구현**
4. ❌ SearchTeam 건너뛰기 로직 **미구현**
5. ⚠️ AnalysisTeam 직접 실행 **가능하지만 input_data 필요**

**구현 가능성**:
- **Phase 1 (명시적 키워드)**: ⭐ 매우 쉬움, 1주 이내 구현 가능
- **Phase 2 (LLM 자동 판단)**: ⭐⭐⭐ 어려움, 1개월 소요
- **Phase 3 (Hybrid)**: ⭐⭐⭐⭐ 매우 어려움, 3개월 소요

### 10.2 권장 구현 순서

1. **즉시 (1주 이내)**: Phase 1 구현
   - 명시적 키워드 기반 재사용
   - Checkpointing 활용
   - 사용자 제어 가능

2. **단기 (1개월 이내)**: Phase 2 테스트
   - LLM 자동 판단 추가
   - 정확도 평가
   - A/B 테스트

3. **중기 (3개월 이내)**: Phase 3 고려
   - Hybrid 방식 도입
   - 사용자 피드백 수집
   - UI/UX 개선

### 10.3 주요 기술적 제약사항

1. **State 초기화 문제**
   - 해결: Checkpointing 활용 (이미 구현됨)

2. **데이터 형식 불일치**
   - 해결: Long-term Memory에 구조화 데이터 저장
   - 또는: LLM으로 자연어 → JSON 변환

3. **히스토리 길이 제한**
   - 현재: 최근 3개 대화만 (6개 메시지)
   - 해결: Long-term Memory (3-Tier) 활용

4. **정확도 문제**
   - LLM 판단 오류 가능성
   - 해결: 낮은 confidence 시 사용자 확인

### 10.4 최종 권장사항

**추천 방안**: **Phase 1 + Phase 2 Hybrid**

1. **Phase 1 (즉시 구현)**:
   - 명시적 키워드 감지
   - 빠르고 안전한 구현
   - 사용자 학습 곡선 낮음

2. **Phase 2 (점진적 추가)**:
   - LLM 자동 판단 (confidence > 0.8)
   - 낮은 confidence 시 Phase 1로 폴백
   - 사용자 경험 개선

3. **Phase 3 (선택적)**:
   - 사용자 피드백에 따라 결정
   - 복잡도 대비 효과 검증 필요

---

## 참고 문서

- [SYSTEM_FLOW_DIAGRAM.md](../../Manual/SYSTEM_FLOW_DIAGRAM.md) - 전체 시스템 흐름도
- [STATE_MANAGEMENT_GUIDE.md](../../Manual/STATE_MANAGEMENT_GUIDE.md) - State 관리 가이드
- [MEMORY_CONFIGURATION_GUIDE.md](../../Manual/MEMORY_CONFIGURATION_GUIDE.md) - Long-term Memory 설정
- [team_supervisor.py](../../backend/app/service_agent/supervisor/team_supervisor.py) - Supervisor 구현
- [planning_agent.py](../../backend/app/service_agent/cognitive_agents/planning_agent.py) - Planning Agent 구현
- [search_executor.py](../../backend/app/service_agent/execution_agents/search_executor.py) - SearchExecutor 구현
- [analysis_executor.py](../../backend/app/service_agent/execution_agents/analysis_executor.py) - AnalysisExecutor 구현

---

**보고서 작성 완료**
**작성자**: Claude Code
**작성일**: 2025-10-22
**버전**: 1.0
