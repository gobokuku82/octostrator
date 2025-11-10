# Agent to LangGraph Migration Plan

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: 현재 단순 함수 기반 Agent를 LangGraph(StateGraph)로 변경하여 Agent 내부 플로우를 시각화/추적 가능하게 만들기

---

## 1. 현재 구조 분석 (AS-IS)

### 1.1 Supervisor 아키텍처

```
Supervisor (LangGraph StateGraph)
  ├─ Intent Understanding Node
  ├─ Planning Node
  ├─ Executor Node (동적 라우팅)
  ├─ Agent Nodes (5개, 단순 async 함수)
  │   ├─ diet_agent_node()
  │   ├─ workout_agent_node()
  │   ├─ schedule_agent_node()
  │   ├─ member_care_agent_node()
  │   └─ coaching_agent_node()
  ├─ Aggregator Node
  ├─ Output Router Node
  └─ Generator Nodes (Chat, Graph, Report)
```

### 1.2 현재 Agent 구조 (단순 함수)

**파일 위치**:
```
backend/app/octostrator/agents/
  ├─ diet/agent.py          → diet_agent_node()
  ├─ workout/agent.py       → workout_agent_node()
  ├─ schedule/agent.py      → schedule_agent_node()
  ├─ member_care/agent.py   → member_care_agent_node()
  └─ coaching/agent.py      → coaching_agent_node()
```

**현재 Agent 로직 (예: diet_agent_node)**:
```python
async def diet_agent_node(state: SupervisorState) -> Dict:
    """단순 async 함수"""
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # 1. Tool 호출
    meal_logs = get_meal_logs(user_id=user_id, limit=3)
    daily_summary = get_daily_nutrition_summary(user_id=user_id)

    # 2. 결과 포맷팅
    result_text = format_meal_logs(meal_logs, daily_summary)

    # 3. State 업데이트
    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result_text

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result_text)]
    }
```

### 1.3 현재 구조의 문제점

1. **Agent 내부 플로우 비가시화**: Agent 내부에서 어떤 Tool을 호출하는지, 어떤 순서로 실행되는지 추적 불가
2. **복잡한 로직 관리 어려움**: Agent 내부가 복잡해지면 함수 하나로는 유지보수 어려움
3. **Checkpointing 불가**: Agent 내부에서 중단/재개 불가능
4. **오류 처리 어려움**: Agent 내부 특정 단계에서 실패 시 전체 Agent가 실패
5. **디버깅 어려움**: Agent 실행 중 어디서 시간이 걸리는지, 어떤 Tool이 실패했는지 추적 어려움

### 1.4 현재 사용하는 Tools

각 Agent는 다음 Tools를 사용합니다:

| Agent | Tools |
|-------|-------|
| **diet** | `get_meal_logs`, `get_daily_nutrition_summary` |
| **workout** | `get_workout_history`, `search_exercises` |
| **schedule** | `get_schedules`, `get_member_info` |
| **member_care** | `get_all_members`, `get_member_progress`, `get_progress_comparison` |
| **coaching** | `search_materials` (FAISS), `get_bookmarks` |

---

## 2. 목표 아키텍처 (TO-BE)

### 2.1 각 Agent를 LangGraph로 변경

```
Agent (LangGraph StateGraph)
  ├─ Analyze Request Node     → 사용자 요청 분석
  ├─ Plan Actions Node        → 필요한 Tool 선택
  ├─ Execute Tools Node       → Tool 순차 실행 (동적 라우팅)
  ├─ Tool Nodes (여러 개)     → 각 Tool을 별도 노드로
  ├─ Aggregate Results Node   → Tool 결과 종합
  └─ Format Response Node     → 최종 응답 포맷팅
```

### 2.2 새로운 파일 구조

```
backend/app/octostrator/agents/
  ├─ diet/
  │   ├─ agent.py              (기존 유지, 호환성)
  │   ├─ graph.py              (NEW: LangGraph 정의)
  │   ├─ nodes.py              (NEW: Agent 내부 노드들)
  │   └─ state.py              (NEW: AgentState 정의)
  ├─ workout/
  │   ├─ agent.py
  │   ├─ graph.py              (NEW)
  │   ├─ nodes.py              (NEW)
  │   └─ state.py              (NEW)
  ├─ schedule/
  │   ├─ agent.py
  │   ├─ graph.py              (NEW)
  │   ├─ nodes.py              (NEW)
  │   └─ state.py              (NEW)
  ├─ member_care/
  │   ├─ agent.py
  │   ├─ graph.py              (NEW)
  │   ├─ nodes.py              (NEW)
  │   └─ state.py              (NEW)
  └─ coaching/
      ├─ agent.py
      ├─ graph.py              (NEW)
      ├─ nodes.py              (NEW)
      └─ state.py              (NEW)
```

### 2.3 AgentState 정의 (공통)

```python
# backend/app/octostrator/states/agent_state.py
from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """Agent 내부 State (Agent Graph용)

    ⚠️ 중요: 임시 State로만 사용 (Checkpoint 저장 안 함)
    Agent 실행 중에만 메모리에 존재
    """
    # 입력
    task: Dict[str, Any]              # Supervisor에서 전달받은 Task
    user_context: Dict[str, Any]      # 사용자 컨텍스트 (user_id, query 등)

    # 분석 결과
    analysis: Optional[Dict]          # 요청 분석 결과
    tool_plan: List[str]              # 실행할 Tool 목록

    # Tool 실행 결과
    tool_results: Dict[str, Any]      # Tool별 실행 결과

    # 최종 결과
    final_response: str               # 포맷팅된 최종 응답
    status: str                       # 'running', 'completed', 'failed'
    error: Optional[str]              # 에러 메시지
```

### 2.3.1 State 관리 전략 ⚠️

**핵심 원칙**: Agent State는 임시, SupervisorState만 영구 저장

```python
# ✅ GOOD: Agent는 Stateless 패턴
async def diet_agent_node_v2(state: SupervisorState) -> dict:
    # 1. 임시 Agent State 생성
    agent_state = {"task": state["plan"][state["current_step"]]}

    # 2. Agent Graph 실행 (Checkpointer 없이)
    result = await diet_graph.ainvoke(agent_state)

    # 3. 결과만 SupervisorState에 반영
    return {"plan": updated_plan, "messages": updated_messages}

# ❌ BAD: Agent State를 SupervisorState에 저장
state["agent_states"]["diet"] = agent_state  # 하지 말 것!
```

### 2.4 Agent Graph 예시 (DietAgent)

```python
# backend/app/octostrator/agents/diet/graph.py
from langgraph.graph import StateGraph, START, END
from .state import DietAgentState
from .nodes import (
    analyze_request_node,
    plan_tools_node,
    get_meal_logs_node,
    get_nutrition_summary_node,
    aggregate_results_node,
    format_response_node
)

def build_diet_agent_graph(llm):
    """Diet Agent Graph 생성

    ⚠️ 중요: Checkpointer 없이 컴파일 (Stateless)
    """
    workflow = StateGraph(DietAgentState)

    # 노드 추가
    workflow.add_node("analyze_request", analyze_request_node)
    workflow.add_node("plan_tools", plan_tools_node)
    workflow.add_node("get_meal_logs", get_meal_logs_node)
    workflow.add_node("get_nutrition_summary", get_nutrition_summary_node)
    workflow.add_node("aggregate_results", aggregate_results_node)
    workflow.add_node("format_response", format_response_node)

    # 엣지 정의
    workflow.add_edge(START, "analyze_request")
    workflow.add_edge("analyze_request", "plan_tools")

    # 동적 라우팅: 필요한 Tool만 실행
    def route_tools(state):
        tools = state["tool_plan"]
        if "get_meal_logs" in tools:
            return "get_meal_logs"
        elif "get_nutrition_summary" in tools:
            return "get_nutrition_summary"
        else:
            return "aggregate_results"

    workflow.add_conditional_edges("plan_tools", route_tools, {
        "get_meal_logs": "get_meal_logs",
        "get_nutrition_summary": "get_nutrition_summary",
        "aggregate_results": "aggregate_results"
    })

    # Tool → Tool 또는 종합
    workflow.add_edge("get_meal_logs", "get_nutrition_summary")
    workflow.add_edge("get_nutrition_summary", "aggregate_results")
    workflow.add_edge("aggregate_results", "format_response")
    workflow.add_edge("format_response", END)

    # ⚠️ Checkpointer 없이 컴파일 (중요!)
    return workflow.compile()  # No checkpointer
```

### 2.4.1 Checkpointer 관리 전략 ⚠️

**핵심 원칙**: Supervisor만 Checkpointer 사용, Agent는 사용 안 함

```python
# ✅ GOOD: Supervisor만 Checkpointer
supervisor_graph = workflow.compile(checkpointer=checkpointer)

# ✅ GOOD: Agent는 Checkpointer 없음
diet_graph = diet_workflow.compile()  # No checkpointer

# ❌ BAD: Agent에 Checkpointer 추가
agent_graph = workflow.compile(checkpointer=checkpointer)  # 하지 말 것!
```

### 2.5 Supervisor에서 Agent Graph 호출

```python
# backend/app/octostrator/supervisor/main_graph.py
from functools import lru_cache
from backend.app.octostrator.agents.diet.graph import build_diet_agent_graph

# Agent Graph 캐싱 (매번 빌드 방지)
@lru_cache(maxsize=5)
def get_cached_agent_graph(agent_name: str, llm):
    """Agent Graph를 캐싱하여 반환"""
    if agent_name == "diet":
        return build_diet_agent_graph(llm)
    elif agent_name == "workout":
        return build_workout_agent_graph(llm)
    # ... 나머지 Agent들

# Supervisor 노드에서 Agent Graph 호출
async def diet_agent_node_v2(state: SupervisorState) -> dict:
    """Diet Agent Graph를 호출하는 Supervisor 노드

    ⚠️ 중요:
    - Agent Graph는 Stateless (Checkpointer 없음)
    - Session 개념 없음 (thread_id 전달 안 함)
    - 결과만 SupervisorState에 반영
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # Agent Graph 입력 생성 (임시 State)
    agent_input = {
        "task": step,
        "user_context": {
            "user_id": state.get("user_id", 1),
            "query": state.get("user_query", "")
        },
        "analysis": None,
        "tool_plan": [],
        "tool_results": {},
        "final_response": "",
        "status": "running",
        "error": None
    }

    # Agent Graph 실행 (Stateless, No Session)
    diet_graph = get_cached_agent_graph("diet", llm)
    result = await diet_graph.ainvoke(agent_input)  # No config/thread_id

    # Supervisor State 업데이트 (결과만 반영)
    plan[current_step]["status"] = result["status"]
    plan[current_step]["result"] = result["final_response"]

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result["final_response"])]
    }

# Supervisor에 노드 추가
workflow.add_node("diet", diet_agent_node_v2)
```

### 2.5.1 Session 관리 전략 ⚠️

**핵심 원칙**: 단일 Session 유지 (Supervisor 레벨에서만)

```python
# ✅ GOOD: Supervisor만 session_id 사용
config = {"configurable": {"thread_id": session_id}}
supervisor_result = await supervisor_graph.ainvoke(input, config=config)

# ✅ GOOD: Agent는 session 개념 없음
agent_result = await agent_graph.ainvoke(agent_input)  # No config

# ❌ BAD: Agent별 session 생성
agent_session_id = f"{session_id}_diet_{uuid}"  # 하지 말 것!
```

---

## 3. 단계별 구현 계획

### Phase 1: 공통 인프라 구축 (1일)

#### Task 1.1: AgentState 정의
- **파일**: `backend/app/octostrator/states/agent_state.py` (NEW)
- **내용**: 공통 AgentState TypedDict 정의
- **예상 시간**: 1시간

#### Task 1.2: Agent별 State 정의
- **파일**: 각 Agent의 `state.py` (NEW)
  - `backend/app/octostrator/agents/diet/state.py`
  - `backend/app/octostrator/agents/workout/state.py`
  - `backend/app/octostrator/agents/schedule/state.py`
  - `backend/app/octostrator/agents/member_care/state.py`
  - `backend/app/octostrator/agents/coaching/state.py`
- **내용**: Agent별 특화 State 정의 (AgentState 확장)
- **예상 시간**: 2시간

#### Task 1.3: Agent Graph Template 작성
- **파일**: `backend/app/octostrator/agents/_template/graph_template.py` (NEW)
- **내용**: 재사용 가능한 Agent Graph Template
- **예상 시간**: 2시간

---

### Phase 2: DietAgent LangGraph 변환 (파일럿, 2일)

#### Task 2.1: DietAgent Nodes 작성
- **파일**: `backend/app/octostrator/agents/diet/nodes.py` (NEW)
- **내용**:
  ```python
  async def analyze_request_node(state: DietAgentState) -> dict:
      """요청 분석 노드"""
      pass

  async def plan_tools_node(state: DietAgentState) -> dict:
      """Tool 계획 노드"""
      pass

  async def get_meal_logs_node(state: DietAgentState) -> dict:
      """식단 기록 조회 노드"""
      pass

  async def get_nutrition_summary_node(state: DietAgentState) -> dict:
      """영양소 집계 노드"""
      pass

  async def aggregate_results_node(state: DietAgentState) -> dict:
      """결과 종합 노드"""
      pass

  async def format_response_node(state: DietAgentState) -> dict:
      """응답 포맷팅 노드"""
      pass
  ```
- **예상 시간**: 4시간

#### Task 2.2: DietAgent Graph 작성
- **파일**: `backend/app/octostrator/agents/diet/graph.py` (NEW)
- **내용**: StateGraph 정의, 노드/엣지 추가
- **예상 시간**: 2시간

#### Task 2.3: DietAgent 통합
- **파일**: `backend/app/octostrator/agents/diet/agent.py` (수정)
- **내용**: 기존 `diet_agent_node()` 유지, 새로운 `diet_agent_node_v2()` 추가
- **예상 시간**: 1시간

#### Task 2.4: Supervisor 연동
- **파일**: `backend/app/octostrator/supervisor/main_graph.py` (수정)
- **내용**: DietAgent Graph 빌드 및 호출
- **예상 시간**: 2시간

#### Task 2.5: 테스트 및 검증
- **테스트 항목**:
  - [ ] DietAgent Graph 단독 실행 테스트
  - [ ] Supervisor에서 DietAgent Graph 호출 테스트
  - [ ] Dashboard에서 Agent 내부 노드 추적 확인
  - [ ] 기존 기능 regression 테스트
- **예상 시간**: 3시간

---

### Phase 3: 나머지 Agent 변환 (4일)

#### Task 3.1: WorkoutAgent LangGraph 변환
- **파일**:
  - `backend/app/octostrator/agents/workout/nodes.py` (NEW)
  - `backend/app/octostrator/agents/workout/graph.py` (NEW)
  - `backend/app/octostrator/agents/workout/agent.py` (수정)
- **예상 시간**: 1일

#### Task 3.2: ScheduleAgent LangGraph 변환
- **파일**:
  - `backend/app/octostrator/agents/schedule/nodes.py` (NEW)
  - `backend/app/octostrator/agents/schedule/graph.py` (NEW)
  - `backend/app/octostrator/agents/schedule/agent.py` (수정)
- **예상 시간**: 1일

#### Task 3.3: MemberCareAgent LangGraph 변환
- **파일**:
  - `backend/app/octostrator/agents/member_care/nodes.py` (NEW)
  - `backend/app/octostrator/agents/member_care/graph.py` (NEW)
  - `backend/app/octostrator/agents/member_care/agent.py` (수정)
- **예상 시간**: 1일

#### Task 3.4: CoachingAgent LangGraph 변환
- **파일**:
  - `backend/app/octostrator/agents/coaching/nodes.py` (NEW)
  - `backend/app/octostrator/agents/coaching/graph.py` (NEW)
  - `backend/app/octostrator/agents/coaching/agent.py` (수정)
- **예상 시간**: 1일

---

### Phase 4: Supervisor 최적화 (1일)

#### Task 4.1: Supervisor에서 모든 Agent Graph 통합
- **파일**: `backend/app/octostrator/supervisor/main_graph.py` (수정)
- **내용**:
  - 모든 Agent를 Graph 버전으로 교체
  - 기존 함수 버전은 deprecated 표시
- **예상 시간**: 2시간

#### Task 4.2: 동적 라우팅 최적화
- **파일**: `backend/app/octostrator/supervisor/cognitive_nodes.py` (수정)
- **내용**: Executor가 Agent Graph를 호출하도록 수정
- **예상 시간**: 2시간

#### Task 4.3: Dashboard 이벤트 확장
- **파일**:
  - `backend/app/api/websocket.py` (수정)
  - `frontend/src/App.tsx` (수정)
- **내용**: Agent 내부 노드 이벤트를 Dashboard에 표시
- **예상 시간**: 3시간

---

### Phase 5: 테스트 및 문서화 (1일)

#### Task 5.1: End-to-End 테스트
- **테스트 시나리오**:
  1. "최근 식단 기록 보여줘" → DietAgent Graph 실행
  2. "오늘 하체 운동 루틴 추천해줘" → WorkoutAgent Graph 실행
  3. "예정된 PT 스케줄 확인" → ScheduleAgent Graph 실행
  4. "회원 진행률 확인" → MemberCareAgent Graph 실행
  5. "스쿼트 자세 영상 찾아줘" → CoachingAgent Graph 실행
- **예상 시간**: 3시간

#### Task 5.2: 문서 업데이트
- **파일**:
  - `reports/supervisor/ARCHITECTURE_OVERVIEW_251105.md` (NEW)
  - `reports/supervisor/AGENT_GRAPH_GUIDE_251105.md` (NEW)
- **내용**: 새로운 아키텍처 설명, Agent Graph 작성 가이드
- **예상 시간**: 2시간

#### Task 5.3: 마이그레이션 가이드 작성
- **파일**: `reports/supervisor/MIGRATION_GUIDE_251105.md` (NEW)
- **내용**: 기존 Agent를 Graph로 변환하는 방법
- **예상 시간**: 1시간

---

## 4. 파일 변경 목록

### 4.1 신규 파일 (총 26개)

| 파일 경로 | 설명 |
|----------|------|
| `backend/app/octostrator/states/agent_state.py` | 공통 AgentState 정의 |
| `backend/app/octostrator/agents/_template/graph_template.py` | Agent Graph Template |
| **DietAgent** | |
| `backend/app/octostrator/agents/diet/state.py` | DietAgentState |
| `backend/app/octostrator/agents/diet/nodes.py` | DietAgent 노드들 |
| `backend/app/octostrator/agents/diet/graph.py` | DietAgent Graph |
| **WorkoutAgent** | |
| `backend/app/octostrator/agents/workout/state.py` | WorkoutAgentState |
| `backend/app/octostrator/agents/workout/nodes.py` | WorkoutAgent 노드들 |
| `backend/app/octostrator/agents/workout/graph.py` | WorkoutAgent Graph |
| **ScheduleAgent** | |
| `backend/app/octostrator/agents/schedule/state.py` | ScheduleAgentState |
| `backend/app/octostrator/agents/schedule/nodes.py` | ScheduleAgent 노드들 |
| `backend/app/octostrator/agents/schedule/graph.py` | ScheduleAgent Graph |
| **MemberCareAgent** | |
| `backend/app/octostrator/agents/member_care/state.py` | MemberCareAgentState |
| `backend/app/octostrator/agents/member_care/nodes.py` | MemberCareAgent 노드들 |
| `backend/app/octostrator/agents/member_care/graph.py` | MemberCareAgent Graph |
| **CoachingAgent** | |
| `backend/app/octostrator/agents/coaching/state.py` | CoachingAgentState |
| `backend/app/octostrator/agents/coaching/nodes.py` | CoachingAgent 노드들 |
| `backend/app/octostrator/agents/coaching/graph.py` | CoachingAgent Graph |
| **문서** | |
| `reports/supervisor/ARCHITECTURE_OVERVIEW_251105.md` | 아키텍처 개요 |
| `reports/supervisor/AGENT_GRAPH_GUIDE_251105.md` | Agent Graph 작성 가이드 |
| `reports/supervisor/MIGRATION_GUIDE_251105.md` | 마이그레이션 가이드 |

### 4.2 수정 파일 (총 9개)

| 파일 경로 | 변경 내용 |
|----------|----------|
| `backend/app/octostrator/supervisor/main_graph.py` | Agent Graph 통합 |
| `backend/app/octostrator/supervisor/cognitive_nodes.py` | Executor 수정 |
| `backend/app/api/websocket.py` | Agent 내부 노드 이벤트 추가 |
| `frontend/src/App.tsx` | Agent 내부 노드 표시 |
| `backend/app/octostrator/agents/diet/agent.py` | v2 함수 추가 |
| `backend/app/octostrator/agents/workout/agent.py` | v2 함수 추가 |
| `backend/app/octostrator/agents/schedule/agent.py` | v2 함수 추가 |
| `backend/app/octostrator/agents/member_care/agent.py` | v2 함수 추가 |
| `backend/app/octostrator/agents/coaching/agent.py` | v2 함수 추가 |

---

## 5. 예상 일정 및 리스크

### 5.1 예상 일정

| Phase | 작업 내용 | 예상 시간 |
|-------|----------|----------|
| **Phase 1** | 공통 인프라 구축 | 1일 (5시간) |
| **Phase 2** | DietAgent 파일럿 | 2일 (12시간) |
| **Phase 3** | 나머지 4개 Agent 변환 | 4일 (32시간) |
| **Phase 4** | Supervisor 최적화 | 1일 (7시간) |
| **Phase 5** | 테스트 및 문서화 | 1일 (6시간) |
| **Total** | | **9일 (62시간)** |

### 5.2 주요 리스크 및 대응 방안

| 리스크 | 영향도 | 확률 | 대응 방안 |
|--------|--------|------|----------|
| **Agent Graph 복잡도 증가로 인한 성능 저하** | 높음 | 중간 | - Agent 내부 노드를 최소화<br>- 불필요한 LLM 호출 제거<br>- Agent Graph 캐싱 (@lru_cache) |
| **State 관리 복잡성 증가** ⚠️ | 매우 높음 | 높음 | - **Agent State는 임시로만 사용**<br>- **SupervisorState에 Agent State 저장 금지**<br>- **Agent는 Stateless 패턴으로 구현** |
| **Checkpointer 중첩 문제** ⚠️ | 매우 높음 | 높음 | - **Agent Graph는 Checkpointer 없이 컴파일**<br>- **Supervisor만 Checkpointer 사용**<br>- **Agent 내부 중단/재개 포기** |
| **Session 분기 관리 복잡성** ⚠️ | 높음 | 중간 | - **단일 session_id 유지**<br>- **Agent는 session 개념 없음**<br>- **Agent 실행 추적은 로깅으로** |
| **기존 기능 호환성 문제** | 높음 | 낮음 | - 기존 함수 버전 유지 (deprecated)<br>- 단계적 전환 (v2 함수 추가) |
| **Dashboard 이벤트 과다로 인한 UI 성능 저하** | 중간 | 중간 | - Agent 내부 노드는 토글로 숨김<br>- 디바운싱 적용 |
| **State 크기 폭발적 증가** ⚠️ | 높음 | 높음 | - Agent State를 SupervisorState에 저장 금지<br>- Agent 결과만 저장<br>- State 크기 모니터링 |
| **일정 지연** | 중간 | 높음 | - Phase 2에서 검증 후 Phase 3 진행<br>- 문서화는 후순위 |

---

## 6. 기대 효과

### 6.1 가시성 향상

- **Dashboard에서 Agent 내부 플로우 추적 가능**
  - 예: DietAgent 실행 시
    ```
    ▶️ DietAgent 시작
      ├─ analyze_request (0.2s)
      ├─ plan_tools (0.1s)
      ├─ get_meal_logs (0.5s)
      ├─ get_nutrition_summary (0.3s)
      ├─ aggregate_results (0.2s)
      └─ format_response (0.1s)
    ✅ DietAgent 완료 (총 1.4s)
    ```

### 6.2 유지보수성 향상

- Agent 내부 로직을 노드 단위로 분리 → 코드 가독성 향상
- 각 노드를 독립적으로 테스트 가능
- Agent 확장 시 노드만 추가하면 됨

### 6.3 디버깅 용이성

- Agent 실행 중 어느 노드에서 시간이 걸리는지 확인 가능
- 특정 노드에서 실패 시 재시도 로직 추가 가능
- LangSmith/LangFuse로 Agent 내부 추적 가능

### 6.4 Checkpointing 지원

- Agent 내부에서도 Checkpointing 적용 가능 (선택적)
- Agent 실행 중 중단 후 재개 가능

### 6.5 복잡한 Agent 구현 가능

- Multi-step Agent (예: ReACT 패턴)
- Parallel Tool Execution
- Conditional Branching (if-else 로직)

---

## 7. 결론

이 계획서는 현재 단순 함수 기반 Agent를 LangGraph로 변경하는 세부 로드맵을 제시합니다.

### 7.1 핵심 원칙

1. **기존 기능 보존**: 기존 함수 버전 유지 (deprecated)
2. **단계적 전환**: DietAgent 파일럿 → 나머지 Agent
3. **검증 우선**: Phase 2에서 충분히 검증 후 Phase 3 진행
4. **문서화**: 아키텍처 변경사항을 명확히 문서화

### 7.2 ⚠️ State/Checkpointer/Session 관리 원칙

**절대 원칙 (MUST)**:
1. **Agent State는 임시로만 사용** - Checkpoint 저장 금지
2. **Agent Graph는 Checkpointer 없이 컴파일** - Stateless 유지
3. **단일 session_id 유지** - Agent별 session 생성 금지
4. **Agent는 함수처럼 동작** - 입력 받고 결과 반환

**권장 사항 (SHOULD)**:
1. Agent Graph를 `@lru_cache`로 캐싱
2. Agent 실행 추적은 로깅으로
3. State 크기 모니터링
4. Agent 결과만 SupervisorState에 저장

### 7.3 Next Steps

1. **이 계획서 및 State 관리 전략 검토**
2. **Phase 1 시작**: AgentState 정의 (임시 State)
3. **Phase 2 파일럿**: DietAgent LangGraph 변환 (Stateless)
4. **State/Checkpointer/Session 검증**
5. **검증 후 Phase 3-5 진행**

---

**작성 완료일**: 2025-11-05
**버전**: 2.0 (State/Checkpointer/Session 관리 전략 추가)
**관련 문서**:
- `STATE_MANAGEMENT_STRATEGY_251105.md` - State/Checkpointer/Session 상세 전략
**문서 관리**: `C:\kdy\Projects\AI_PTmanager\beta_v001\reports\supervisor\AGENT_TO_LANGGRAPH_MIGRATION_PLAN_251105.md`
