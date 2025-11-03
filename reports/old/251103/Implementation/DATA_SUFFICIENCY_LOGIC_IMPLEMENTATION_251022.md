# 데이터 충분성 판단 로직 구현 방안 분석 보고서

**작성일**: 2025-10-22
**버전**: 1.0
**분석 대상**: LangGraph 0.6 Multi-Agent 시스템 데이터 충분성 판단 로직
**핵심 질문**: Supervisor 레벨 vs Execute Node 레벨 중 어디에 구현하는 것이 최적인가?

---

## 📋 목차

1. [Executive Summary](#executive-summary)
2. [현재 시스템 구조 분석](#현재-시스템-구조-분석)
3. [접근 방식 1: Supervisor 레벨 구현](#접근-방식-1-supervisor-레벨-구현)
4. [접근 방식 2: Execute Node 고도화](#접근-방식-2-execute-node-고도화)
5. [비교 분석 및 권장사항](#비교-분석-및-권장사항)
6. [단계별 구현 가이드](#단계별-구현-가이드)
7. [결론](#결론)

---

## 1. Executive Summary

### 핵심 발견사항

**✅ 최적 해답: Hybrid 접근 (Supervisor + Execute Node 분담)**

데이터 충분성 판단 로직을 **단일 지점에 집중**시키는 것보다, **Supervisor와 Execute Node 양쪽에 분담**하는 것이 가장 효과적입니다.

### 권장 아키텍처

```
Planning Node (Supervisor)
    ├── Intent 분석
    ├── Chat History 로드
    └── 🆕 데이터 충분성 1차 판단 (LLM)
        ├── "이전 데이터로 충분" → SearchTeam 제외
        ├── "새 검색 필요" → SearchTeam 포함
        └── "불확실" → SearchTeam 포함 (안전)

Execute Teams Node (Supervisor)
    └── 🆕 SearchExecutor 실행 전 2차 검증
        ├── Checkpointing에서 이전 데이터 로드
        ├── 데이터 품질 검사 (신선도, 완전성)
        └── 조건 충족 시 SearchTeam 건너뛰기

SearchExecutor (Execute Node)
    └── 🆕 prepare_search_node 내부 3차 검증
        ├── input_data 확인
        ├── search_scope 재평가
        └── 실제 검색 건너뛰기 결정
```

### 비교 표

| 항목 | Supervisor 레벨 | Execute Node 레벨 | **Hybrid (권장)** |
|------|----------------|------------------|------------------|
| **구현 위치** | `planning_node` | `prepare_search_node` | 양쪽 모두 |
| **판단 시점** | 계획 수립 시 | 실행 직전 | 계획 + 실행 |
| **접근 가능 데이터** | Chat History, Long-term Memory | Checkpointing, 이전 팀 결과 | 모든 데이터 |
| **복잡도** | ⭐⭐⭐ 중간 | ⭐⭐ 낮음 | ⭐⭐⭐⭐ 높음 |
| **정확도** | ⭐⭐⭐ 중간 | ⭐⭐ 낮음 | ⭐⭐⭐⭐⭐ 매우 높음 |
| **유연성** | ⭐⭐ 낮음 | ⭐⭐⭐⭐ 높음 | ⭐⭐⭐⭐⭐ 매우 높음 |
| **성능 영향** | ✅ 조기 종료 가능 | ⚠️ 늦은 종료 | ✅ 최적 |
| **유지보수성** | ⭐⭐⭐ 중간 | ⭐⭐⭐⭐ 높음 | ⭐⭐⭐ 중간 |

### 권장사항 요약

1. **Phase 1 (1주)**: Supervisor 레벨 구현 (1차 판단)
   - Planning Node에서 LLM 기반 충분성 판단
   - 명확한 경우 SearchTeam 제외
   - 불확실한 경우 Execute Node로 위임

2. **Phase 2 (2주)**: Execute Node 고도화 (2차 검증)
   - SearchExecutor에서 데이터 품질 검사
   - 조건 충족 시 실제 검색 건너뛰기
   - Fallback 로직 강화

3. **Phase 3 (3주)**: Hybrid 통합 (최적화)
   - 양쪽 로직 통합 및 조율
   - A/B 테스트 및 정확도 검증
   - Human-in-the-Loop 추가

---

## 2. 현재 시스템 구조 분석

### 2.1 LangGraph 워크플로우

```python
# team_supervisor.py - _build_graph()
workflow = StateGraph(MainSupervisorState)

# 노드 추가
workflow.add_node("initialize", self.initialize_node)
workflow.add_node("planning", self.planning_node)              # ← Supervisor 레벨
workflow.add_node("execute_teams", self.execute_teams_node)    # ← Execute Node 레벨
workflow.add_node("aggregate", self.aggregate_results_node)
workflow.add_node("generate_response", self.generate_response_node)

# 엣지 구성
workflow.add_edge(START, "initialize")
workflow.add_edge("initialize", "planning")

# ✅ 계획 후 라우팅 (현재 데이터 충분성 판단 없음)
workflow.add_conditional_edges(
    "planning",
    self._route_after_planning,
    {
        "execute": "execute_teams",
        "respond": "generate_response"
    }
)

workflow.add_edge("execute_teams", "aggregate")
```

### 2.2 데이터 흐름

```
┌─────────────────────────────────────────────────┐
│ Planning Node (Supervisor)                      │
├─────────────────────────────────────────────────┤
│ 1. Chat History 로드 (최근 3개 대화)              │
│ 2. Long-term Memory 로드 (3-Tier)               │
│ 3. Intent 분석 (LLM #1)                          │
│ 4. Agent 선택 (LLM #2)                           │
│ 5. Execution Plan 생성                           │
│    └─> active_teams: ["search", "analysis"]     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Execute Teams Node (Supervisor)                 │
├─────────────────────────────────────────────────┤
│ for team in active_teams:                       │
│     └─> _execute_single_team(team)              │
│         ├─> SearchExecutor.execute()            │
│         └─> AnalysisExecutor.execute()          │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ SearchExecutor (Execute Node)                   │
├─────────────────────────────────────────────────┤
│ 1. prepare_search_node                          │
│    ├─> keywords 추출                             │
│    └─> search_scope 결정                         │
│ 2. route_search_node                             │
│    └─> search_scope 없으면 skip                  │
│ 3. execute_search_node                           │
│    └─> 실제 검색 수행                             │
└─────────────────────────────────────────────────┘
```

### 2.3 현재 판단 지점 부재 문제

**문제점**:
1. **Planning Node**: Intent만 분석, 데이터 충분성 판단 없음
2. **Execute Teams Node**: active_teams를 **무조건 실행**
3. **SearchExecutor**: search_scope 없으면 skip (하지만 이미 SearchTeam 호출됨)

**결과**:
- 채팅 히스토리에 충분한 데이터가 있어도 SearchTeam 항상 실행
- 불필요한 LLM 호출 및 검색 도구 실행
- 3~5초 낭비

---

## 3. 접근 방식 1: Supervisor 레벨 구현

### 3.1 아키텍처 개요

**핵심 아이디어**: Planning Node에서 데이터 충분성을 판단하고, `active_teams`에서 SearchTeam 제외

```python
# team_supervisor.py - planning_node()

async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    # 1. Intent 분석
    intent_result = await self.planning_agent.analyze_intent(query, context)

    # 🆕 2. 데이터 충분성 판단 (LLM 기반)
    sufficiency_result = await self._check_data_sufficiency(
        query=query,
        intent=intent_result,
        chat_history=chat_history,
        tiered_memories=state.get("tiered_memories", {})
    )

    # 🆕 3. Execution Plan 수정
    if sufficiency_result["is_sufficient"]:
        # SearchTeam 제외
        execution_plan = await self.planning_agent.create_execution_plan(
            intent_result,
            skip_teams=["search_team"]
        )
        state["data_reused"] = True
        state["reused_data_source"] = sufficiency_result["data_source"]
    else:
        # 정상 계획
        execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # 4. active_teams 결정
    # ...
```

### 3.2 데이터 충분성 판단 로직

**코드 위치**: `team_supervisor.py` - 새 메서드 추가

```python
async def _check_data_sufficiency(
    self,
    query: str,
    intent: IntentResult,
    chat_history: List[Dict],
    tiered_memories: Dict
) -> Dict[str, Any]:
    """
    데이터 충분성 판단 (LLM 기반)

    Returns:
        {
            "is_sufficient": bool,           # 충분한가?
            "confidence": float,             # 확신도 (0~1)
            "data_source": str,              # "chat_history" | "long_term_memory" | "none"
            "missing_data_types": List[str], # 부족한 데이터 타입
            "reasoning": str                 # 판단 근거
        }
    """
    if not self.planning_agent.llm_service:
        return {"is_sufficient": False, "confidence": 0.0, "data_source": "none"}

    try:
        # 필요한 데이터 타입 결정
        required_data_types = self._get_required_data_types(intent)

        # Chat History 분석
        available_in_chat = await self._extract_available_data_from_history(
            chat_history,
            required_data_types
        )

        # Long-term Memory 분석 (필요 시)
        available_in_memory = {}
        if not available_in_chat:
            available_in_memory = await self._extract_available_data_from_memory(
                tiered_memories,
                required_data_types
            )

        # LLM에게 충분성 판단 요청
        result = await self.planning_agent.llm_service.complete_json_async(
            prompt_name="data_sufficiency_check",
            variables={
                "query": query,
                "intent_type": intent.intent_type.value,
                "required_data_types": required_data_types,
                "available_in_chat": available_in_chat,
                "available_in_memory": available_in_memory,
                "chat_history": self._format_chat_history(chat_history)
            },
            temperature=0.1
        )

        return {
            "is_sufficient": result.get("is_sufficient", False),
            "confidence": result.get("confidence", 0.0),
            "data_source": result.get("data_source", "none"),
            "missing_data_types": result.get("missing_data_types", []),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        logger.error(f"Data sufficiency check failed: {e}")
        # 안전을 위해 충분하지 않다고 판단
        return {"is_sufficient": False, "confidence": 0.0, "data_source": "none"}
```

### 3.3 필요한 데이터 타입 결정

```python
def _get_required_data_types(self, intent: IntentResult) -> List[str]:
    """
    Intent에 따라 필요한 데이터 타입 결정

    Returns:
        ["legal_data", "market_data", "loan_data", "contract_data"]
    """
    intent_to_data = {
        IntentType.LEGAL_CONSULT: ["legal_data"],
        IntentType.MARKET_INQUIRY: ["market_data"],
        IntentType.LOAN_CONSULT: ["loan_data"],
        IntentType.CONTRACT_REVIEW: ["legal_data", "contract_data"],
        IntentType.COMPREHENSIVE: ["legal_data", "market_data"],
        IntentType.RISK_ANALYSIS: ["legal_data", "market_data"],
    }

    return intent_to_data.get(intent.intent_type, ["legal_data", "market_data"])
```

### 3.4 Chat History에서 데이터 추출

```python
async def _extract_available_data_from_history(
    self,
    chat_history: List[Dict],
    required_data_types: List[str]
) -> Dict[str, Any]:
    """
    Chat History에서 필요한 데이터 추출

    Returns:
        {
            "legal_data": {"found": True, "content": "...", "recency": "3분 전"},
            "market_data": {"found": False}
        }
    """
    if not chat_history:
        return {}

    available = {}

    # 각 데이터 타입별로 검색
    for data_type in required_data_types:
        # 키워드 패턴
        patterns = {
            "legal_data": ["법", "전세", "임대차", "계약", "보증금"],
            "market_data": ["시세", "가격", "매매가", "전세가"],
            "loan_data": ["대출", "금리", "한도", "LTV"],
            "contract_data": ["계약서", "특약", "조항"]
        }

        keywords = patterns.get(data_type, [])

        # Chat History에서 검색
        for i, msg in enumerate(reversed(chat_history)):
            if msg["role"] == "assistant":
                content = msg["content"]
                if any(kw in content for kw in keywords):
                    available[data_type] = {
                        "found": True,
                        "content": content[:200],  # 샘플
                        "message_index": len(chat_history) - i - 1,
                        "recency": f"{(len(chat_history) - i) // 2}개 대화 전"
                    }
                    break

        # 찾지 못한 경우
        if data_type not in available:
            available[data_type] = {"found": False}

    return available
```

### 3.5 프롬프트 설계

**파일 위치**: `backend/app/service_agent/llm_manager/prompts/cognitive/data_sufficiency_check.txt`

```
# 데이터 충분성 판단

## 현재 상황

사용자 쿼리: {query}
의도 타입: {intent_type}

## 필요한 데이터

다음 데이터 타입이 필요합니다:
{required_data_types}

## 이전 대화에서 발견된 데이터

### Chat History (최근 대화)
{available_in_chat}

### Long-term Memory (과거 대화)
{available_in_memory}

## 대화 히스토리

{chat_history}

---

## 판단 기준

1. **완전성**: 필요한 모든 데이터 타입이 있는가?
2. **신선도**: 데이터가 여전히 유효한가?
   - 법률 데이터: 항상 유효 (법령 변경 제외)
   - 시세 데이터: 1주일 이내 유효
   - 대출 데이터: 1일 이내 유효
3. **관련성**: 현재 쿼리와 일치하는가?
   - 지역, 금액, 조건 등이 동일한가?

## 출력 JSON

{
  "is_sufficient": true/false,
  "confidence": 0.0~1.0,
  "data_source": "chat_history" | "long_term_memory" | "none",
  "missing_data_types": ["market_data"],
  "reasoning": "이전 대화(3개 대화 전)에서 강남구 시세 정보(5억~7억) 제공됨. 신선도 양호 (3분 전). 현재 쿼리와 지역 일치. 법률 데이터만 추가 검색 필요."
}

## 주의사항

- 불확실한 경우 `is_sufficient: false` 반환 (안전 우선)
- confidence < 0.8인 경우 `is_sufficient: false` 권장
- 데이터가 부분적으로만 있어도 유용하면 `is_sufficient: true` 가능
  (예: 시세 데이터만 있어도 대략적 분석 가능)
```

### 3.6 장점 및 단점

**장점**:
1. ✅ **조기 최적화**: Planning 단계에서 불필요한 팀 제외
2. ✅ **중앙 집중**: 모든 판단 로직이 한 곳에 집중
3. ✅ **명확한 계획**: active_teams가 명확하게 결정됨
4. ✅ **WebSocket 알림**: 사용자에게 "이전 데이터 재사용" 알림 가능

**단점**:
1. ❌ **Planning Node 복잡도 증가**: 이미 복잡한 로직이 더 복잡해짐
2. ❌ **Checkpointing 데이터 접근 어려움**: Planning Node에서 이전 SearchTeam 결과 접근 어려움
3. ❌ **유연성 부족**: 계획 후 변경 불가
4. ❌ **테스트 어려움**: Planning 로직과 강하게 결합

### 3.7 구현 복잡도

**파일 수정 목록**:
1. `team_supervisor.py` - `planning_node()` 수정
2. `team_supervisor.py` - `_check_data_sufficiency()` 추가
3. `team_supervisor.py` - `_extract_available_data_from_history()` 추가
4. `team_supervisor.py` - `_extract_available_data_from_memory()` 추가
5. `planning_agent.py` - `create_execution_plan()` 수정 (skip_teams 파라미터 추가)
6. `prompts/cognitive/data_sufficiency_check.txt` - 새 프롬프트 추가

**예상 구현 시간**: 3~5일

---

## 4. 접근 방식 2: Execute Node 고도화

### 4.1 아키텍처 개요

**핵심 아이디어**: SearchExecutor 내부에서 실행 전 데이터 확인 후 건너뛰기

```python
# search_executor.py - prepare_search_node()

async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
    logger.info("[SearchTeam] Preparing search")

    # 🆕 1. 이전 검색 결과 확인 (Checkpointing 또는 주입된 데이터)
    previous_data = state.get("injected_previous_data") or await self._load_previous_search_data(state)

    # 🆕 2. 데이터 충분성 검증
    if previous_data:
        sufficiency = self._check_data_quality(previous_data, state)

        if sufficiency["is_sufficient"]:
            # 검색 건너뛰기
            state["search_scope"] = []  # ← route_decision에서 "skip" 반환
            state["using_cached_data"] = True
            state["cached_data_source"] = sufficiency["source"]

            # 이전 데이터를 결과로 사용
            state["legal_results"] = previous_data.get("legal_search", [])
            state["real_estate_results"] = previous_data.get("real_estate_search", [])
            state["loan_results"] = previous_data.get("loan_search", [])

            logger.info(f"[SearchTeam] Using cached data from {sufficiency['source']}")
            return state

    # 🆕 3. 새 검색 필요 (기존 로직 계속)
    if not state.get("keywords"):
        query = state.get("shared_context", {}).get("query", "")
        state["keywords"] = self._extract_keywords(query)

    if not state.get("search_scope"):
        state["search_scope"] = self._determine_search_scope(state["keywords"])

    return state
```

### 4.2 이전 검색 데이터 로드

```python
async def _load_previous_search_data(self, state: SearchTeamState) -> Optional[Dict]:
    """
    Checkpointing 또는 Long-term Memory에서 이전 검색 데이터 로드

    Returns:
        {
            "legal_search": [...],
            "real_estate_search": [...],
            "loan_search": [...]
        }
    """
    # 방법 1: Checkpointing (가장 최근)
    # Note: SearchExecutor는 checkpointer 접근 불가
    # → Supervisor에서 주입해야 함

    # 방법 2: Long-term Memory
    # Note: SearchExecutor는 DB 접근 불가
    # → Supervisor에서 주입해야 함

    # 방법 3: shared_context에서 추출
    shared_context = state.get("shared_context", {})
    previous_data = shared_context.get("previous_search_results")

    return previous_data
```

### 4.3 데이터 품질 검증

```python
def _check_data_quality(
    self,
    previous_data: Dict,
    state: SearchTeamState
) -> Dict[str, Any]:
    """
    이전 데이터의 품질 검증

    Returns:
        {
            "is_sufficient": bool,
            "confidence": float,
            "source": str,
            "issues": List[str]  # 품질 이슈
        }
    """
    issues = []
    confidence = 1.0

    # 1. 완전성 검사
    query = state.get("shared_context", {}).get("query", "")
    required_types = self._determine_required_data_types(query)

    available_types = []
    if previous_data.get("legal_search"):
        available_types.append("legal")
    if previous_data.get("real_estate_search"):
        available_types.append("market")
    if previous_data.get("loan_search"):
        available_types.append("loan")

    missing = set(required_types) - set(available_types)
    if missing:
        issues.append(f"Missing data types: {missing}")
        confidence -= 0.3

    # 2. 데이터 양 검사
    for data_type, results in previous_data.items():
        if isinstance(results, list) and len(results) < 3:
            issues.append(f"{data_type} has insufficient results ({len(results)})")
            confidence -= 0.2

    # 3. 신선도 검사 (타임스탬프 필요)
    # Note: 현재 데이터에 타임스탬프 없음
    # → Supervisor에서 metadata 전달 필요

    # 4. 관련성 검사 (간단한 키워드 매칭)
    keywords = state.get("keywords", {})
    # TODO: 이전 데이터의 키워드와 비교

    # 최종 판단
    is_sufficient = confidence > 0.7 and not missing

    return {
        "is_sufficient": is_sufficient,
        "confidence": max(confidence, 0.0),
        "source": "previous_search",
        "issues": issues
    }
```

### 4.4 Supervisor에서 데이터 주입

**코드 위치**: `team_supervisor.py` - `_execute_single_team()`

```python
async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 팀 실행"""
    team = self.teams[team_name]

    if team_name == "search":
        # 🆕 이전 검색 결과 로드 (Checkpointing)
        previous_search_data = None
        if self.checkpointer and main_state.get("chat_session_id"):
            previous_search_data = await self._get_previous_search_results(
                main_state["chat_session_id"]
            )

        # 🆕 shared_state에 주입
        if previous_search_data:
            shared_state["previous_search_results"] = previous_search_data
            shared_state["previous_search_metadata"] = {
                "timestamp": previous_search_data.get("timestamp"),
                "query": previous_search_data.get("query")
            }

        return await team.execute(shared_state)

    # ...
```

```python
async def _get_previous_search_results(
    self,
    chat_session_id: str
) -> Optional[Dict]:
    """
    Checkpointing에서 이전 SearchTeam 결과 로드

    Returns:
        {
            "legal_search": [...],
            "real_estate_search": [...],
            "loan_search": [...],
            "timestamp": "2025-10-22T10:30:00",
            "query": "강남구 아파트 시세"
        }
    """
    if not self.checkpointer:
        return None

    try:
        config = {"configurable": {"thread_id": chat_session_id}}
        prev_checkpoint = await self.checkpointer.aget(config)

        if prev_checkpoint and prev_checkpoint.values:
            prev_state = prev_checkpoint.values
            team_results = prev_state.get("team_results", {})

            if "search" in team_results:
                return {
                    **team_results["search"],
                    "timestamp": prev_state.get("end_time"),
                    "query": prev_state.get("query")
                }

    except Exception as e:
        logger.warning(f"Failed to load previous search results: {e}")

    return None
```

### 4.5 장점 및 단점

**장점**:
1. ✅ **높은 유연성**: 실행 직전 최종 판단 가능
2. ✅ **Checkpointing 활용**: 이전 결과 쉽게 접근
3. ✅ **관심사 분리**: Planning과 Execution 분리
4. ✅ **테스트 용이**: SearchExecutor 독립적으로 테스트 가능

**단점**:
1. ❌ **늦은 최적화**: Planning 단계에서 이미 active_teams에 포함됨
2. ❌ **중복 로직**: SearchExecutor 내부 복잡도 증가
3. ❌ **데이터 주입 필요**: Supervisor에서 데이터 주입 로직 필요
4. ❌ **WebSocket 알림 어려움**: Planning 시점에 알림 불가

### 4.6 구현 복잡도

**파일 수정 목록**:
1. `search_executor.py` - `prepare_search_node()` 수정
2. `search_executor.py` - `_load_previous_search_data()` 추가
3. `search_executor.py` - `_check_data_quality()` 추가
4. `team_supervisor.py` - `_execute_single_team()` 수정
5. `team_supervisor.py` - `_get_previous_search_results()` 추가
6. `separated_states.py` - SharedState에 `previous_search_results` 필드 추가

**예상 구현 시간**: 2~3일

---

## 5. 비교 분석 및 권장사항

### 5.1 상세 비교표

| 평가 항목 | Supervisor 레벨 | Execute Node 레벨 | **Hybrid (권장)** |
|----------|----------------|------------------|------------------|
| **1. 성능 최적화** |
| 조기 종료 | ✅ Planning 단계 | ❌ Execute 단계 (늦음) | ✅ Planning 단계 |
| SearchTeam 호출 회피 | ✅ 완전 회피 | ⚠️ 호출은 하지만 빠르게 종료 | ✅ 완전 회피 |
| 불필요한 LLM 호출 감소 | ✅ 최대 | ⚠️ 중간 | ✅ 최대 |
| **2. 정확도** |
| 데이터 접근 범위 | ⭐⭐⭐ Chat History, Long-term Memory | ⭐⭐⭐⭐ Checkpointing 추가 | ⭐⭐⭐⭐⭐ 모든 소스 |
| 품질 검증 | ⭐⭐ LLM 판단만 | ⭐⭐⭐⭐ 규칙 기반 검증 | ⭐⭐⭐⭐⭐ LLM + 규칙 |
| 오판단 리스크 | ⭐⭐ 중간 | ⭐⭐⭐ 낮음 (Fallback) | ⭐⭐⭐⭐ 매우 낮음 |
| **3. 구현 복잡도** |
| 코드 변경 범위 | ⭐⭐⭐ 중간 (6개 파일) | ⭐⭐ 낮음 (6개 파일) | ⭐⭐⭐⭐ 높음 (8개 파일) |
| 프롬프트 설계 | ⭐⭐⭐⭐ 복잡 | ⭐⭐ 단순 | ⭐⭐⭐⭐ 복잡 |
| 테스트 복잡도 | ⭐⭐⭐ 중간 | ⭐⭐ 낮음 | ⭐⭐⭐⭐ 높음 |
| **4. 유지보수성** |
| 코드 응집도 | ⭐⭐ 낮음 (Planning 비대화) | ⭐⭐⭐⭐ 높음 (관심사 분리) | ⭐⭐⭐ 중간 |
| 디버깅 용이성 | ⭐⭐⭐ 중간 | ⭐⭐⭐⭐ 높음 | ⭐⭐⭐ 중간 |
| 확장성 | ⭐⭐ 낮음 | ⭐⭐⭐⭐ 높음 | ⭐⭐⭐⭐ 높음 |
| **5. 사용자 경험** |
| 사전 알림 가능 | ✅ "이전 데이터 사용 예정" | ❌ 알림 불가 | ✅ 명확한 알림 |
| 투명성 | ⭐⭐⭐⭐ 높음 | ⭐⭐ 낮음 | ⭐⭐⭐⭐⭐ 매우 높음 |
| Human-in-the-Loop | ✅ 가능 | ⚠️ 어려움 | ✅ 최적 |

### 5.2 Hybrid 접근의 우수성

**Hybrid = Supervisor (1차 판단) + Execute Node (2차 검증)**

```
┌──────────────────────────────────────────────────┐
│ Planning Node (Supervisor)                       │
├──────────────────────────────────────────────────┤
│ 1차 판단: 데이터 충분성 LLM 분석                    │
│                                                  │
│ IF confidence > 0.9:                             │
│   └─> active_teams = ["analysis"]               │
│   └─> state["skip_search_reason"] = "충분함"     │
│                                                  │
│ ELIF confidence > 0.6:                           │
│   └─> active_teams = ["search", "analysis"]     │
│   └─> state["search_verify_data"] = True        │
│                                                  │
│ ELSE:                                            │
│   └─> active_teams = ["search", "analysis"]     │
│   └─> state["search_verify_data"] = False       │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ Execute Teams Node (Supervisor)                  │
├──────────────────────────────────────────────────┤
│ IF "search" in active_teams:                     │
│   ├─> 이전 데이터 로드 (Checkpointing)             │
│   ├─> shared_state에 주입                         │
│   └─> SearchExecutor.execute(shared_state)       │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ SearchExecutor (Execute Node)                    │
├──────────────────────────────────────────────────┤
│ 2차 검증: 데이터 품질 규칙 기반 검사                 │
│                                                  │
│ IF state["search_verify_data"] == True:          │
│   ├─> previous_data = state.get("previous_...")  │
│   ├─> quality = _check_data_quality(...)         │
│   │                                              │
│   └─> IF quality["is_sufficient"]:               │
│       └─> search_scope = []  (skip)              │
│   └─> ELSE:                                      │
│       └─> 새 검색 수행                            │
│                                                  │
│ ELSE:                                            │
│   └─> 새 검색 수행 (기존 로직)                     │
└──────────────────────────────────────────────────┘
```

**장점**:
1. ✅ **이중 안전망**: LLM 오판단 시 규칙 기반 검증으로 보완
2. ✅ **최적 성능**: 명확한 경우(confidence > 0.9) 조기 종료
3. ✅ **최고 정확도**: 모든 데이터 소스 활용
4. ✅ **사용자 신뢰**: Planning 시점 알림 + Execute 시점 재확인

**단점**:
1. ❌ **높은 복잡도**: 양쪽 모두 구현 필요
2. ❌ **유지보수 부담**: 두 곳에서 로직 관리
3. ❌ **구현 시간**: 4~6일 소요

### 5.3 최종 권장사항

**단계별 구현 전략**:

#### Phase 1 (1주): Supervisor 레벨 구현 (1차 판단)

**목표**: 명확한 경우 SearchTeam 제외

**구현**:
1. `planning_node()`에 `_check_data_sufficiency()` 추가
2. confidence > 0.9인 경우 active_teams에서 "search" 제외
3. WebSocket 알림: "이전 데이터 재사용 중..."

**기대 효과**:
- 명확한 경우 (예: "방금 검색한 데이터로 분석해줘") 3~5초 단축
- 전체 쿼리의 약 30% 해당

#### Phase 2 (2주): Execute Node 고도화 (2차 검증)

**목표**: 불확실한 경우 2차 검증

**구현**:
1. `_execute_single_team()`에서 이전 데이터 로드 및 주입
2. `prepare_search_node()`에 `_check_data_quality()` 추가
3. 조건 충족 시 search_scope = [] 설정

**기대 효과**:
- Phase 1에서 놓친 경우 추가 최적화 (약 20%)
- 총 50% 쿼리에서 SearchTeam 건너뛰기

#### Phase 3 (3주): Hybrid 통합 및 최적화

**목표**: 양쪽 로직 조율 및 Human-in-the-Loop 추가

**구현**:
1. Supervisor와 Execute Node 간 State 공유 최적화
2. confidence 임계값 조정 (A/B 테스트)
3. 불확실 시 사용자 확인 요청 (WebSocket)

**기대 효과**:
- 최고 정확도 및 사용자 신뢰도
- 총 60~70% 쿼리 최적화

---

## 6. 단계별 구현 가이드

### 6.1 Phase 1: Supervisor 레벨 구현

#### Step 1: 프롬프트 작성

**파일 생성**: `backend/app/service_agent/llm_manager/prompts/cognitive/data_sufficiency_check.txt`

```
# 데이터 충분성 판단 프롬프트

## 목적
사용자의 현재 질문을 처리하기 위해 이전 대화(Chat History 또는 Long-term Memory)에 저장된 데이터로 충분한지 판단합니다.

## 입력 정보

### 1. 현재 쿼리
{query}

### 2. 의도 타입
{intent_type}

### 3. 필요한 데이터 타입
{required_data_types}

### 4. Chat History에서 발견된 데이터
{available_in_chat}

### 5. Long-term Memory에서 발견된 데이터
{available_in_memory}

### 6. 대화 전체 히스토리
{chat_history}

---

## 판단 기준

### 1. 완전성 (Completeness)
- 필요한 모든 데이터 타입이 있는가?
- 예: "시세 분석"이면 market_data 필수

### 2. 신선도 (Freshness)
- **법률 데이터**: 항상 유효 (법령 개정 제외)
- **시세 데이터**: 1주일 이내 유효
- **대출 데이터**: 1일 이내 유효
- **계약 데이터**: 항상 유효 (특정 계약서)

### 3. 관련성 (Relevance)
- 지역이 동일한가? (예: 강남구 → 강남구)
- 금액 범위가 유사한가?
- 조건이 일치하는가?

### 4. 품질 (Quality)
- 데이터 양이 충분한가? (최소 3개 이상)
- 구체적인 정보인가? (막연한 설명 X)

---

## 출력 형식 (JSON)

{
  "is_sufficient": true/false,
  "confidence": 0.0~1.0,
  "data_source": "chat_history" | "long_term_memory" | "none",
  "missing_data_types": ["market_data"],
  "reasoning": "이전 대화(3개 대화 전)에서 강남구 시세 정보(5억~7억) 제공됨. 신선도 양호 (3분 전). 현재 쿼리와 지역 일치. 충분함."
}

---

## 예시

### 예시 1: 충분함

**쿼리**: "방금 검색한 시세로 투자 수익률 계산해줘"
**Chat History**: "강남구 아파트 전세 시세는 5억~7억입니다. (2분 전)"
**필요 데이터**: ["market_data"]

**출력**:
{
  "is_sufficient": true,
  "confidence": 0.95,
  "data_source": "chat_history",
  "missing_data_types": [],
  "reasoning": "2분 전 대화에서 강남구 시세 정보 제공됨. 신선도 우수. 투자 분석에 충분."
}

### 예시 2: 불충분함

**쿼리**: "서초구 시세 분석해줘"
**Chat History**: "강남구 아파트 전세 시세는 5억~7억입니다. (2분 전)"
**필요 데이터**: ["market_data"]

**출력**:
{
  "is_sufficient": false,
  "confidence": 0.3,
  "data_source": "none",
  "missing_data_types": ["market_data"],
  "reasoning": "지역 불일치 (강남구 ≠ 서초구). 새로운 검색 필요."
}

### 예시 3: 불확실함 (안전하게 false 반환)

**쿼리**: "위험도 분석해줘"
**Chat History**: "강남구 아파트 전세 시세는 5억~7억입니다. (1주일 전)"
**필요 데이터**: ["market_data", "legal_data"]

**출력**:
{
  "is_sufficient": false,
  "confidence": 0.6,
  "data_source": "chat_history",
  "missing_data_types": ["legal_data"],
  "reasoning": "시세 데이터는 있으나 1주일 경과로 신선도 의심. 법률 데이터 없음. 재검색 권장."
}

---

## 주의사항

1. **안전 우선**: 불확실하면 `is_sufficient: false` 반환
2. **Confidence 기준**: < 0.8이면 false 권장
3. **부분 충족**: 일부 데이터만 있어도 유용하면 true 가능
4. **시간 표현 이해**: "방금", "아까", "조금 전" → 신선함
```

#### Step 2: 데이터 충분성 판단 메서드 추가

**파일 수정**: `backend/app/service_agent/supervisor/team_supervisor.py`

```python
# team_supervisor.py - 새 메서드 추가 (planning_node 이전)

async def _check_data_sufficiency(
    self,
    query: str,
    intent: IntentResult,
    chat_history: List[Dict],
    tiered_memories: Dict
) -> Dict[str, Any]:
    """
    데이터 충분성 판단 (LLM 기반)

    Args:
        query: 사용자 쿼리
        intent: Intent 분석 결과
        chat_history: 최근 대화 히스토리
        tiered_memories: 3-Tier Long-term Memory

    Returns:
        {
            "is_sufficient": bool,
            "confidence": float,
            "data_source": str,
            "missing_data_types": List[str],
            "reasoning": str
        }
    """
    # LLM 서비스 없으면 건너뛰기
    if not self.planning_agent.llm_service:
        logger.warning("LLM service not available, skipping sufficiency check")
        return {
            "is_sufficient": False,
            "confidence": 0.0,
            "data_source": "none",
            "missing_data_types": [],
            "reasoning": "LLM not available"
        }

    try:
        # 1. 필요한 데이터 타입 결정
        required_data_types = self._get_required_data_types(intent)

        # 2. Chat History에서 이용 가능한 데이터 추출
        available_in_chat = self._extract_available_data_from_history(
            chat_history,
            required_data_types
        )

        # 3. Long-term Memory에서 이용 가능한 데이터 추출
        available_in_memory = self._extract_available_data_from_memory(
            tiered_memories,
            required_data_types
        )

        # 4. Chat History 포맷팅
        chat_history_text = self._format_chat_history(chat_history)

        # 5. LLM에게 충분성 판단 요청
        result = await self.planning_agent.llm_service.complete_json_async(
            prompt_name="data_sufficiency_check",
            variables={
                "query": query,
                "intent_type": intent.intent_type.value,
                "required_data_types": json.dumps(required_data_types, ensure_ascii=False),
                "available_in_chat": json.dumps(available_in_chat, ensure_ascii=False, indent=2),
                "available_in_memory": json.dumps(available_in_memory, ensure_ascii=False, indent=2),
                "chat_history": chat_history_text
            },
            temperature=0.1,
            max_tokens=500
        )

        logger.info(f"[Sufficiency Check] Result: {result}")

        return {
            "is_sufficient": result.get("is_sufficient", False),
            "confidence": result.get("confidence", 0.0),
            "data_source": result.get("data_source", "none"),
            "missing_data_types": result.get("missing_data_types", []),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as e:
        logger.error(f"Data sufficiency check failed: {e}", exc_info=True)
        # 안전을 위해 불충분하다고 판단
        return {
            "is_sufficient": False,
            "confidence": 0.0,
            "data_source": "none",
            "missing_data_types": required_data_types,
            "reasoning": f"Error: {str(e)}"
        }

def _get_required_data_types(self, intent: IntentResult) -> List[str]:
    """Intent에 따라 필요한 데이터 타입 결정"""
    intent_to_data = {
        IntentType.LEGAL_CONSULT: ["legal_data"],
        IntentType.MARKET_INQUIRY: ["market_data"],
        IntentType.LOAN_CONSULT: ["loan_data"],
        IntentType.CONTRACT_CREATION: [],  # 새로 작성하므로 이전 데이터 불필요
        IntentType.CONTRACT_REVIEW: ["legal_data", "contract_data"],
        IntentType.COMPREHENSIVE: ["legal_data", "market_data"],
        IntentType.RISK_ANALYSIS: ["legal_data", "market_data"],
    }

    return intent_to_data.get(intent.intent_type, ["legal_data", "market_data"])

def _extract_available_data_from_history(
    self,
    chat_history: List[Dict],
    required_data_types: List[str]
) -> Dict[str, Any]:
    """Chat History에서 필요한 데이터 추출"""
    if not chat_history:
        return {}

    available = {}

    # 데이터 타입별 키워드 패턴
    patterns = {
        "legal_data": ["법", "전세", "임대차", "계약", "보증금", "권리", "의무", "갱신"],
        "market_data": ["시세", "가격", "매매가", "전세가", "평균", "거래"],
        "loan_data": ["대출", "금리", "한도", "LTV", "DTI", "DSR"],
        "contract_data": ["계약서", "특약", "조항", "서명"]
    }

    # 각 데이터 타입별로 검색
    for data_type in required_data_types:
        keywords = patterns.get(data_type, [])

        # Chat History를 역순으로 탐색 (최신부터)
        for i, msg in enumerate(reversed(chat_history)):
            if msg["role"] == "assistant":
                content = msg["content"]

                # 키워드 매칭
                if any(kw in content for kw in keywords):
                    # 데이터 발견
                    conversation_index = len(chat_history) - i - 1
                    conversations_ago = (len(chat_history) - conversation_index) // 2

                    available[data_type] = {
                        "found": True,
                        "content": content[:300],  # 샘플 (최대 300자)
                        "conversation_index": conversation_index,
                        "recency": f"{conversations_ago}개 대화 전"
                    }
                    break  # 가장 최근 것만

        # 찾지 못한 경우
        if data_type not in available:
            available[data_type] = {"found": False}

    return available

def _extract_available_data_from_memory(
    self,
    tiered_memories: Dict,
    required_data_types: List[str]
) -> Dict[str, Any]:
    """Long-term Memory에서 필요한 데이터 추출"""
    if not tiered_memories:
        return {}

    available = {}

    # Short-term, Mid-term, Long-term 순으로 검색
    for tier in ["shortterm", "midterm", "longterm"]:
        memories = tiered_memories.get(tier, [])

        for data_type in required_data_types:
            if data_type in available:
                continue  # 이미 찾음

            # 메모리에서 키워드 검색 (간단한 버전)
            for memory in memories:
                summary = memory.get("summary", "")
                # TODO: 더 정교한 매칭 로직
                if data_type.replace("_data", "") in summary.lower():
                    available[data_type] = {
                        "found": True,
                        "content": summary[:300],
                        "tier": tier,
                        "session_id": memory.get("session_id")
                    }
                    break

    # 찾지 못한 경우
    for data_type in required_data_types:
        if data_type not in available:
            available[data_type] = {"found": False}

    return available

def _format_chat_history(self, chat_history: List[Dict]) -> str:
    """Chat History를 LLM이 읽기 쉬운 형식으로 변환"""
    if not chat_history:
        return "No chat history available."

    lines = []
    for i, msg in enumerate(chat_history):
        role = "사용자" if msg["role"] == "user" else "AI"
        content = msg["content"][:500]  # 제한
        lines.append(f"[{i+1}] {role}: {content}")

    return "\n".join(lines)
```

#### Step 3: Planning Node 수정

**파일 수정**: `backend/app/service_agent/supervisor/team_supervisor.py` - `planning_node()`

```python
async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    # ... (기존 코드: Intent 분석, Long-term Memory 로드 등)

    # IRRELEVANT/UNCLEAR 조기 종료 (기존 코드)
    if intent_result.intent_type == IntentType.IRRELEVANT:
        # ...
        return state

    # 🆕 데이터 충분성 판단 (새 코드)
    sufficiency_result = await self._check_data_sufficiency(
        query=query,
        intent=intent_result,
        chat_history=chat_history,
        tiered_memories=state.get("tiered_memories", {})
    )

    logger.info(
        f"[Sufficiency Check] is_sufficient={sufficiency_result['is_sufficient']}, "
        f"confidence={sufficiency_result['confidence']:.2f}, "
        f"source={sufficiency_result['data_source']}"
    )

    # 🆕 충분성 결과에 따라 Agent 선택 수정
    skip_search = False

    if sufficiency_result["is_sufficient"] and sufficiency_result["confidence"] > 0.9:
        # 매우 확실한 경우: SearchTeam 완전 제외
        logger.info("[Sufficiency Check] Very high confidence, skipping SearchTeam completely")
        skip_search = True

        # State에 기록
        state["data_reused"] = True
        state["reused_data_source"] = sufficiency_result["data_source"]
        state["sufficiency_reasoning"] = sufficiency_result["reasoning"]

        # WebSocket 알림
        session_id = state.get("session_id")
        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
        if progress_callback:
            try:
                await progress_callback("data_reuse_decision", {
                    "message": "이전 대화의 데이터를 재사용합니다.",
                    "source": sufficiency_result["data_source"],
                    "reasoning": sufficiency_result["reasoning"],
                    "confidence": sufficiency_result["confidence"]
                })
            except Exception as e:
                logger.error(f"Failed to send data_reuse_decision: {e}")

    elif sufficiency_result["is_sufficient"] and sufficiency_result["confidence"] > 0.6:
        # 중간 확신: Execute Node에서 2차 검증
        logger.info("[Sufficiency Check] Medium confidence, deferring to Execute Node")
        state["verify_search_data"] = True
        state["sufficiency_result"] = sufficiency_result

    else:
        # 불충분 또는 낮은 확신: 새 검색 필요
        logger.info("[Sufficiency Check] Insufficient or low confidence, new search required")
        state["verify_search_data"] = False

    # 실행 계획 생성 (기존 코드 수정)
    if skip_search:
        # 🆕 SearchTeam 제외한 Agent만 선택
        filtered_agents = [a for a in intent_result.suggested_agents if a != "search_team"]

        # 강제로 Agent 목록 교체
        intent_result.suggested_agents = filtered_agents if filtered_agents else ["analysis_team"]

    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # ... (나머지 기존 코드: Planning State 생성, active_teams 결정 등)

    return state
```

### 6.2 Phase 2: Execute Node 고도화

#### Step 1: Supervisor에서 이전 데이터 로드 및 주입

**파일 수정**: `backend/app/service_agent/supervisor/team_supervisor.py` - `_execute_single_team()`

```python
async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 팀 실행"""
    team = self.teams[team_name]

    if team_name == "search":
        # 🆕 Phase 2: 이전 검색 결과 로드 및 주입
        if main_state.get("verify_search_data"):
            previous_data = await self._get_previous_search_results(
                main_state.get("chat_session_id")
            )

            if previous_data:
                # shared_state에 주입
                shared_state["previous_search_results"] = previous_data
                shared_state["previous_search_metadata"] = {
                    "timestamp": previous_data.get("timestamp"),
                    "query": previous_data.get("query")
                }
                shared_state["sufficiency_result"] = main_state.get("sufficiency_result")

                logger.info(f"[Execute] Injected previous search data from {previous_data.get('timestamp')}")

        return await team.execute(shared_state)

    elif team_name == "document":
        # ...
        return await team.execute(shared_state, document_type=doc_type)

    elif team_name == "analysis":
        # ...
        return await team.execute(shared_state, analysis_type="comprehensive", input_data=input_data)

    return {"status": "skipped"}

async def _get_previous_search_results(
    self,
    chat_session_id: Optional[str]
) -> Optional[Dict]:
    """
    Checkpointing에서 이전 SearchTeam 결과 로드

    Returns:
        {
            "legal_search": [...],
            "real_estate_search": [...],
            "loan_search": [...],
            "timestamp": "2025-10-22T10:30:00",
            "query": "강남구 아파트 시세"
        }
    """
    if not self.checkpointer or not chat_session_id:
        return None

    try:
        config = {"configurable": {"thread_id": chat_session_id}}
        prev_checkpoint = await self.checkpointer.aget(config)

        if prev_checkpoint and prev_checkpoint.values:
            prev_state = prev_checkpoint.values
            team_results = prev_state.get("team_results", {})

            if "search" in team_results:
                # 타임스탬프 및 쿼리 추가
                return {
                    **team_results["search"],
                    "timestamp": prev_state.get("end_time", datetime.now()).isoformat() if prev_state.get("end_time") else None,
                    "query": prev_state.get("query", "")
                }

        logger.info("[Checkpoint] No previous search results found")
        return None

    except Exception as e:
        logger.warning(f"Failed to load previous search results from checkpoint: {e}")
        return None
```

#### Step 2: SearchExecutor prepare_search_node 수정

**파일 수정**: `backend/app/service_agent/execution_agents/search_executor.py`

```python
async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
    """
    검색 준비 노드
    키워드 추출 및 검색 범위 설정
    🆕 Phase 2: 이전 데이터 재사용 검증
    """
    logger.info("[SearchTeam] Preparing search")

    # 초기화
    state["team_name"] = self.team_name
    state["status"] = "in_progress"
    state["start_time"] = datetime.now()
    state["search_progress"] = {}

    # 🆕 Phase 2: 이전 검색 데이터 확인
    shared_context = state.get("shared_context", {})
    previous_data = shared_context.get("previous_search_results")
    sufficiency_result = shared_context.get("sufficiency_result")

    if previous_data and sufficiency_result:
        # 🆕 데이터 품질 검증
        quality = self._check_data_quality(
            previous_data=previous_data,
            state=state,
            sufficiency_result=sufficiency_result
        )

        if quality["is_sufficient"]:
            # 🆕 검색 건너뛰기
            logger.info(
                f"[SearchTeam] Using cached data (quality: {quality['confidence']:.2f}, "
                f"source: {quality['source']})"
            )

            # search_scope를 빈 리스트로 설정 → route_decision에서 "skip" 반환
            state["search_scope"] = []
            state["using_cached_data"] = True
            state["cached_data_source"] = quality["source"]
            state["cached_data_quality"] = quality

            # 🆕 이전 데이터를 결과로 사용
            state["legal_results"] = previous_data.get("legal_search", [])
            state["real_estate_results"] = previous_data.get("real_estate_search", [])
            state["loan_results"] = previous_data.get("loan_search", [])

            return state
        else:
            # 품질 불충분, 새 검색 필요
            logger.info(
                f"[SearchTeam] Cached data quality insufficient (confidence: {quality['confidence']:.2f}), "
                f"performing new search. Issues: {quality['issues']}"
            )

    # 🆕 키워드가 없으면 쿼리에서 추출 (기존 로직)
    if not state.get("keywords"):
        query = shared_context.get("query", "")
        state["keywords"] = self._extract_keywords(query)

    # 검색 범위가 없으면 키워드 기반으로 결정 (기존 로직)
    if not state.get("search_scope"):
        state["search_scope"] = self._determine_search_scope(state["keywords"])

    logger.info(f"[SearchTeam] Search scope: {state['search_scope']}")
    return state
```

#### Step 3: 데이터 품질 검증 메서드 추가

**파일 수정**: `backend/app/service_agent/execution_agents/search_executor.py`

```python
def _check_data_quality(
    self,
    previous_data: Dict,
    state: SearchTeamState,
    sufficiency_result: Dict
) -> Dict[str, Any]:
    """
    이전 검색 데이터의 품질 검증 (규칙 기반)

    Args:
        previous_data: 이전 검색 결과
        state: 현재 State
        sufficiency_result: Supervisor의 충분성 판단 결과

    Returns:
        {
            "is_sufficient": bool,
            "confidence": float,
            "source": str,
            "issues": List[str]
        }
    """
    issues = []
    confidence = sufficiency_result.get("confidence", 0.5)

    # 1. 완전성 검사: 필요한 데이터 타입이 모두 있는가?
    query = state.get("shared_context", {}).get("query", "")
    required_types = self._determine_required_data_types_from_query(query)

    available_types = []
    if previous_data.get("legal_search"):
        available_types.append("legal")
    if previous_data.get("real_estate_search"):
        available_types.append("market")
    if previous_data.get("loan_search"):
        available_types.append("loan")

    missing = set(required_types) - set(available_types)
    if missing:
        issues.append(f"Missing data types: {missing}")
        confidence -= 0.3

    # 2. 데이터 양 검사: 각 타입별로 충분한 결과가 있는가?
    for data_type, results in previous_data.items():
        if data_type in ["legal_search", "real_estate_search", "loan_search"]:
            if isinstance(results, list):
                if len(results) == 0:
                    issues.append(f"{data_type} has no results")
                    confidence -= 0.4
                elif len(results) < 3:
                    issues.append(f"{data_type} has insufficient results ({len(results)} < 3)")
                    confidence -= 0.2

    # 3. 신선도 검사 (타임스탬프 기반)
    metadata = state.get("shared_context", {}).get("previous_search_metadata", {})
    timestamp_str = metadata.get("timestamp")

    if timestamp_str:
        try:
            from datetime import datetime, timedelta

            # ISO 형식 파싱
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = timestamp_str

            age = datetime.now() - timestamp

            # 신선도 기준 (데이터 타입별)
            if "market" in required_types:
                # 시세 데이터: 1주일 이내
                if age > timedelta(days=7):
                    issues.append(f"Market data is {age.days} days old (> 7 days)")
                    confidence -= 0.3
                elif age > timedelta(days=3):
                    issues.append(f"Market data is {age.days} days old (> 3 days, warning)")
                    confidence -= 0.1

            if "loan" in required_types:
                # 대출 데이터: 1일 이내
                if age > timedelta(days=1):
                    issues.append(f"Loan data is {age.days} days old (> 1 day)")
                    confidence -= 0.4

            # 법률 데이터는 신선도 검사 생략 (항상 유효)

        except Exception as e:
            logger.warning(f"Failed to parse timestamp: {e}")
            issues.append("Timestamp parsing failed, cannot verify freshness")
            confidence -= 0.1

    # 4. 관련성 검사 (간단한 키워드 매칭)
    previous_query = metadata.get("query", "")
    if previous_query:
        # 지역 비교
        current_regions = self._extract_regions(query)
        previous_regions = self._extract_regions(previous_query)

        if current_regions and previous_regions:
            if not any(r in previous_regions for r in current_regions):
                issues.append(f"Region mismatch: {current_regions} vs {previous_regions}")
                confidence -= 0.4

    # 최종 판단
    confidence = max(confidence, 0.0)  # 음수 방지
    is_sufficient = confidence > 0.7 and len(missing) == 0

    return {
        "is_sufficient": is_sufficient,
        "confidence": confidence,
        "source": sufficiency_result.get("data_source", "previous_search"),
        "issues": issues
    }

def _determine_required_data_types_from_query(self, query: str) -> List[str]:
    """쿼리에서 필요한 데이터 타입 추론 (간단한 키워드 매칭)"""
    types = []

    if any(kw in query for kw in ["법", "전세", "임대", "계약", "보증금"]):
        types.append("legal")

    if any(kw in query for kw in ["시세", "가격", "매매", "거래"]):
        types.append("market")

    if any(kw in query for kw in ["대출", "금리", "한도"]):
        types.append("loan")

    # 기본값
    if not types:
        types = ["legal", "market"]

    return types

def _extract_regions(self, text: str) -> List[str]:
    """텍스트에서 지역 추출"""
    regions = ["강남구", "강북구", "강동구", "강서구", "관악구", "광진구", "구로구",
              "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구",
              "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구",
              "은평구", "종로구", "중구", "중랑구"]

    found = []
    for region in regions:
        if region in text:
            found.append(region)

    return found
```

### 6.3 Phase 3: Hybrid 통합 및 최적화

#### Step 1: State 공유 최적화

**파일 수정**: `backend/app/service_agent/foundation/separated_states.py`

```python
# separated_states.py - SharedState 확장

class SharedState(TypedDict, total=False):
    # ... (기존 필드)

    # 🆕 Phase 3: 데이터 재사용 관련 필드
    previous_search_results: Optional[Dict]           # 이전 검색 결과
    previous_search_metadata: Optional[Dict]          # 타임스탬프, 쿼리 등
    sufficiency_result: Optional[Dict]                # Supervisor 충분성 판단
    verify_search_data: bool                          # 2차 검증 필요 여부
```

#### Step 2: A/B 테스트 프레임워크

**파일 생성**: `backend/app/service_agent/evaluation/ab_test.py`

```python
"""
A/B 테스트: 데이터 충분성 판단 정확도 평가
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ABTestTracker:
    """
    A/B 테스트 결과 추적

    Variant A: Supervisor 레벨만
    Variant B: Hybrid (Supervisor + Execute Node)
    """

    def __init__(self):
        self.results = {
            "variant_a": [],  # Supervisor only
            "variant_b": []   # Hybrid
        }

    def log_decision(
        self,
        variant: str,
        query: str,
        supervisor_decision: Dict,
        execute_node_decision: Optional[Dict],
        actual_result: str,  # "correct_skip" | "incorrect_skip" | "correct_search" | "incorrect_search"
        execution_time: float
    ):
        """A/B 테스트 결과 로깅"""
        self.results[variant].append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "supervisor_decision": supervisor_decision,
            "execute_node_decision": execute_node_decision,
            "actual_result": actual_result,
            "execution_time": execution_time
        })

    def get_metrics(self, variant: str) -> Dict:
        """지표 계산"""
        results = self.results[variant]

        if not results:
            return {}

        total = len(results)
        correct_skips = sum(1 for r in results if r["actual_result"] == "correct_skip")
        incorrect_skips = sum(1 for r in results if r["actual_result"] == "incorrect_skip")
        correct_searches = sum(1 for r in results if r["actual_result"] == "correct_search")
        incorrect_searches = sum(1 for r in results if r["actual_result"] == "incorrect_search")

        accuracy = (correct_skips + correct_searches) / total if total > 0 else 0.0
        avg_time = sum(r["execution_time"] for r in results) / total if total > 0 else 0.0

        return {
            "total_requests": total,
            "correct_skips": correct_skips,
            "incorrect_skips": incorrect_skips,
            "correct_searches": correct_searches,
            "incorrect_searches": incorrect_searches,
            "accuracy": accuracy,
            "avg_execution_time": avg_time,
            "skip_rate": (correct_skips + incorrect_skips) / total if total > 0 else 0.0
        }
```

#### Step 3: Human-in-the-Loop 통합

**파일 수정**: `backend/app/service_agent/supervisor/team_supervisor.py`

```python
# planning_node() 내부 - 충분성 판단 후

if sufficiency_result["is_sufficient"] and 0.6 < sufficiency_result["confidence"] <= 0.9:
    # 🆕 Phase 3: 중간 확신도 → 사용자 확인 요청
    logger.info("[Sufficiency Check] Medium confidence, requesting user confirmation")

    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id) if session_id else None

    if progress_callback:
        try:
            # 사용자 확인 요청
            await progress_callback("user_confirmation_required", {
                "confirmation_id": f"conf_{datetime.now().timestamp()}",
                "message": "이전 대화의 데이터를 사용하시겠습니까?",
                "context": {
                    "previous_data_summary": self._summarize_previous_data(sufficiency_result),
                    "data_age": self._calculate_data_age(sufficiency_result),
                    "uncertainty_reason": sufficiency_result.get("reasoning", "")
                },
                "options": [
                    {
                        "value": "use_previous",
                        "label": "예, 이전 데이터 사용",
                        "description": "검색 시간 3~5초 단축"
                    },
                    {
                        "value": "search_new",
                        "label": "아니요, 최신 정보 검색",
                        "description": "최신 데이터로 분석"
                    }
                ]
            })

            # 사용자 응답 대기 (타임아웃 30초)
            user_choice = await self._wait_for_user_confirmation(session_id, timeout=30.0)

            if user_choice == "use_previous":
                # SearchTeam 제외
                skip_search = True
                state["data_reused"] = True
                state["user_confirmed"] = True
            else:
                # 새 검색
                skip_search = False
                state["user_confirmed"] = False

        except asyncio.TimeoutError:
            # 타임아웃 → 안전하게 새 검색
            logger.warning("[Sufficiency Check] User confirmation timeout, performing new search")
            skip_search = False
        except Exception as e:
            logger.error(f"User confirmation failed: {e}")
            skip_search = False
```

---

## 7. 결론

### 7.1 최종 권장사항

**✅ Hybrid 접근 방식이 최적**

1. **Supervisor 레벨 (1차 판단)**:
   - LLM 기반 데이터 충분성 판단
   - 명확한 경우 (confidence > 0.9) SearchTeam 제외
   - 사용자에게 사전 알림 가능

2. **Execute Node 레벨 (2차 검증)**:
   - 규칙 기반 데이터 품질 검사
   - 불확실한 경우 안전망 역할
   - Checkpointing 활용한 이전 데이터 로드

3. **Human-in-the-Loop (3차 확인)**:
   - 중간 확신도 시 사용자 확인
   - 투명성 및 신뢰도 향상

### 7.2 구현 우선순위

| Phase | 구현 내용 | 소요 시간 | 예상 효과 |
|-------|---------|---------|---------|
| **Phase 1** | Supervisor 레벨 구현 | 1주 (3~5일) | 30% 쿼리 최적화 |
| **Phase 2** | Execute Node 고도화 | 2주 (추가 3~5일) | 50% 쿼리 최적화 |
| **Phase 3** | Hybrid 통합 + HIL | 3주 (추가 5~7일) | 60~70% 쿼리 최적화 |

### 7.3 기대 효과

**성능**:
- SearchTeam 건너뛰기: **3~5초 단축**
- 전체 응답 시간: **60% 감소** (최적 케이스)

**비용**:
- LLM 호출 감소: **40~50% 절감**
- 검색 도구 호출 감소: **60~70% 절감**

**사용자 경험**:
- 반응 속도 향상
- 투명한 의사결정
- 신뢰도 향상

### 7.4 리스크 및 대응

| 리스크 | 확률 | 영향도 | 대응 방안 |
|--------|------|--------|----------|
| LLM 오판단 | 중간 | 높음 | Execute Node 2차 검증 |
| Checkpointing 실패 | 낮음 | 중간 | Fallback to 새 검색 |
| 사용자 혼란 | 낮음 | 낮음 | 명확한 알림 메시지 |
| 구현 복잡도 | 높음 | 중간 | 단계별 구현 |

---

**보고서 작성 완료**
**작성자**: Claude Code
**작성일**: 2025-10-22
**버전**: 1.0
