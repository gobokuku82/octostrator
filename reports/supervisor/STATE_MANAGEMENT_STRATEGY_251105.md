# State/Checkpointer/Session Management Strategy

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Agent를 LangGraph로 변경 시 State, Checkpointer, Session 관리 전략 정의

---

## 1. 현재 시스템 분석

### 1.1 현재 State 관리 구조

```
┌─────────────────────────────────────┐
│         SupervisorState             │
│  - messages: BaseMessage[]          │
│  - plan: List[dict]                 │
│  - current_step: int                │
│  - is_waiting_human: bool           │
│  - aggregated_data: dict            │
│  - final_result: str                │
└─────────────────────────────────────┘
            ↓ PostgreSQL
┌─────────────────────────────────────┐
│    AsyncPostgresSaver (Checkpoint)  │
│  - thread_id = session_id           │
│  - checkpoint 테이블에 저장          │
└─────────────────────────────────────┘
```

**특징**:
- 단일 State 구조 (SupervisorState)
- Agent는 State를 받아서 처리하고 반환
- 모든 State 변경이 PostgreSQL에 저장됨

### 1.2 현재 Checkpointer 관리

```python
# CheckpointerManager (싱글톤)
- AsyncPostgresSaver 인스턴스 캐싱
- 연결 생명주기 관리
- thread_id 기반 checkpoint 저장

# 사용 패턴
checkpointer = await create_checkpointer()
graph = build_supervisor_graph(checkpointer=checkpointer)
result = await graph.ainvoke(input, config={"configurable": {"thread_id": session_id}})
```

### 1.3 현재 Session 관리

```python
# SessionManager (싱글톤, 메모리)
- session_id = session_${Date.now()} (Frontend)
- thread_id = session_id (Backend)
- 메모리에 세션 메타데이터 저장

# WebSocket 연결
ws://localhost:8000/ws/chat/{session_id}
→ thread_id로 변환
→ Checkpointer에서 사용
```

---

## 2. Agent LangGraph 변환 시 발생할 복잡성

### 2.1 State 관리 복잡성

#### 문제점 1: 이중 State 구조

```
┌──────────────────┐     ┌──────────────────┐
│ SupervisorState  │────▶│   AgentState     │
│                  │     │ - task: dict     │
│ - plan[i]        │     │ - tool_plan: []  │
│ - messages       │     │ - tool_results   │
└──────────────────┘     └──────────────────┘
        ↓                        ↓
    PostgreSQL              PostgreSQL???
```

**이슈**:
- SupervisorState와 AgentState 간 데이터 전달
- State 크기 증가 (중복 데이터)
- State 동기화 문제

#### 문제점 2: State 중첩

```
SupervisorState {
  messages: [...],
  plan: [{
    agent: "diet",
    agent_state: {  // Agent 내부 State 저장?
      task: {...},
      tool_results: {...}
    }
  }]
}
```

**이슈**:
- Agent 내부 State를 Supervisor State에 저장?
- State 크기 폭발적 증가
- 직렬화 복잡성

### 2.2 Checkpointer 관리 복잡성

#### 문제점 1: 중첩된 Checkpointing

```
Supervisor Checkpointer
  └─ thread_id: "session_123"
      └─ Agent Checkpointer???
          └─ thread_id: "session_123_diet_001"???
```

**이슈**:
- Agent Graph에도 Checkpointer 필요한가?
- 중첩된 checkpoint 관리
- 복구 시 어느 checkpoint 사용?

#### 문제점 2: 성능 이슈

```
Supervisor checkpoint 저장 → 1회
+ Agent1 checkpoint 저장 → N회 (노드 수)
+ Agent2 checkpoint 저장 → N회
+ Agent3 checkpoint 저장 → N회
= 총 저장 횟수 폭발적 증가
```

### 2.3 Session 관리 복잡성

#### 문제점 1: Session 분기

```
session_123 (Supervisor)
  ├─ session_123_diet_001 (DietAgent)
  ├─ session_123_workout_002 (WorkoutAgent)
  └─ session_123_schedule_003 (ScheduleAgent)
```

**이슈**:
- Session 트리 구조 관리
- Session 간 데이터 공유
- Session 정리 (cleanup)

---

## 3. 해결 전략

### 3.1 State 관리 전략

#### 전략 1: Agent State를 Supervisor State의 일부로 관리 ❌

```python
class SupervisorState(TypedDict):
    messages: Sequence[BaseMessage]
    plan: List[dict]
    current_step: int

    # Agent States (NEW)
    agent_states: Dict[str, dict]  # {"diet": {...}, "workout": {...}}
```

**장점**: 단일 State, 단일 Checkpoint
**단점**: State 크기 증가, 복잡성 증가

#### 전략 2: Agent는 Stateless로 유지 ✅ (권장)

```python
async def diet_agent_graph(input: dict) -> dict:
    """Agent Graph는 Stateless 함수처럼 동작"""
    # 입력 받고
    agent_state = {
        "task": input["task"],
        "user_context": input["user_context"],
        ...
    }

    # Graph 실행 (Checkpointer 없이)
    result = await diet_graph.ainvoke(agent_state)

    # 결과만 반환
    return {"result": result["final_response"]}
```

**장점**:
- 단순함
- State 크기 최소화
- Checkpointing 복잡성 제거

**단점**:
- Agent 내부 중단/재개 불가능

#### 전략 3: Agent State를 임시로만 사용 ✅✅ (최적)

```python
class AgentState(TypedDict):
    """Agent 내부 State (휘발성)"""
    # Agent 실행 중에만 존재
    # Checkpoint 저장 안 함

async def diet_agent_node_v2(state: SupervisorState) -> dict:
    # 1. SupervisorState에서 필요한 데이터 추출
    task = state["plan"][state["current_step"]]

    # 2. Agent State 생성 (임시)
    agent_state = {
        "task": task,
        "tool_plan": [],
        "tool_results": {},
        ...
    }

    # 3. Agent Graph 실행 (Checkpointer 없이)
    diet_graph = build_diet_agent_graph(llm)  # Checkpointer 없음
    result = await diet_graph.ainvoke(agent_state)

    # 4. 결과만 SupervisorState에 반영
    return {
        "plan": update_plan_with_result(state["plan"], result),
        "messages": state["messages"] + [AIMessage(content=result["final_response"])]
    }
```

### 3.2 Checkpointer 관리 전략

#### 전략 1: Supervisor만 Checkpointing ✅✅ (권장)

```python
# Supervisor Graph (Checkpointer 있음)
supervisor_graph = workflow.compile(checkpointer=checkpointer)

# Agent Graphs (Checkpointer 없음)
diet_graph = diet_workflow.compile()  # No checkpointer
workout_graph = workout_workflow.compile()  # No checkpointer
```

**장점**:
- 단순함
- 성능 최적
- Checkpoint 관리 용이

**단점**:
- Agent 내부 중단/재개 불가능

#### 전략 2: 선택적 Checkpointing

```python
# 복잡한 Agent만 Checkpointing
coaching_graph = coaching_workflow.compile(checkpointer=checkpointer)

# 단순한 Agent는 Checkpointing 없음
diet_graph = diet_workflow.compile()
```

### 3.3 Session 관리 전략

#### 전략 1: 단일 Session 유지 ✅✅ (권장)

```python
# Session은 Supervisor 레벨에서만 관리
session_id = "session_123"
thread_id = session_id

# Agent는 Session 개념 없음
# Agent는 단순 함수처럼 동작
```

**장점**:
- 단순함
- Session 관리 용이
- 기존 시스템과 호환

#### 전략 2: Agent 실행 추적용 메타데이터

```python
# Agent 실행을 추적하기 위한 메타데이터만 사용
execution_metadata = {
    "session_id": "session_123",
    "agent_name": "diet",
    "execution_id": uuid.uuid4(),  # 실행마다 새로 생성
    "started_at": datetime.now(),
    "completed_at": None
}

# 로깅/모니터링용으로만 사용
# Session 관리와는 분리
```

---

## 4. 권장 아키텍처

### 4.1 최종 권장 구조

```
┌─────────────────────────────────────────┐
│         Supervisor (LangGraph)          │
│  - SupervisorState                      │
│  - Checkpointer: AsyncPostgresSaver     │
│  - thread_id: session_id                │
└─────────────────────────────────────────┘
                    ↓
    ┌───────────────┴───────────────┐
    ↓                               ↓
┌──────────────────┐    ┌──────────────────┐
│  DietAgent       │    │  WorkoutAgent    │
│  (LangGraph)     │    │  (LangGraph)     │
│  - AgentState    │    │  - AgentState    │
│  - No Checkpoint │    │  - No Checkpoint │
│  - Stateless     │    │  - Stateless     │
└──────────────────┘    └──────────────────┘
```

### 4.2 구현 가이드라인

#### 1. State 관리
```python
# SupervisorState는 유지
# AgentState는 임시 (Agent 실행 중에만)
# Agent 결과는 SupervisorState에 병합
```

#### 2. Checkpointer 관리
```python
# Supervisor만 Checkpointer 사용
supervisor_graph = workflow.compile(checkpointer=checkpointer)

# Agent는 Checkpointer 없음
agent_graph = agent_workflow.compile()  # No checkpointer
```

#### 3. Session 관리
```python
# 단일 session_id = thread_id 유지
# Agent는 session 개념 없음
# Agent 실행 추적은 로깅으로
```

### 4.3 Agent Graph 구현 패턴

```python
# backend/app/octostrator/agents/diet/graph.py
def build_diet_agent_graph(llm):
    """Diet Agent Graph (Stateless, No Checkpointer)"""
    workflow = StateGraph(DietAgentState)

    # 노드 추가
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("format", format_node)

    # 엣지 정의
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "execute_tools")
    workflow.add_edge("execute_tools", "format")
    workflow.add_edge("format", END)

    # Checkpointer 없이 컴파일
    return workflow.compile()  # ← No checkpointer

# backend/app/octostrator/supervisor/main_graph.py
async def diet_agent_node_v2(state: SupervisorState) -> dict:
    """Diet Agent 실행 (Stateless)"""
    # 1. 입력 준비
    task = state["plan"][state["current_step"]]

    # 2. Agent Graph 실행 (Checkpointer 없이)
    diet_graph = build_diet_agent_graph(llm)
    result = await diet_graph.ainvoke({
        "task": task,
        "user_context": {"user_id": state.get("user_id", 1)}
    })

    # 3. 결과 반영
    state["plan"][state["current_step"]]["result"] = result["final_response"]
    state["plan"][state["current_step"]]["status"] = "completed"

    return {
        "plan": state["plan"],
        "current_step": state["current_step"] + 1,
        "messages": state["messages"] + [AIMessage(content=result["final_response"])]
    }
```

---

## 5. 구현 시 주의사항

### 5.1 절대 하지 말아야 할 것

1. **Agent Graph에 Checkpointer 추가 ❌**
   ```python
   # BAD
   agent_graph = workflow.compile(checkpointer=checkpointer)
   ```

2. **Agent State를 SupervisorState에 저장 ❌**
   ```python
   # BAD
   state["agent_states"]["diet"] = agent_state
   ```

3. **Agent별 Session 생성 ❌**
   ```python
   # BAD
   agent_session_id = f"{session_id}_diet_{uuid}"
   ```

### 5.2 반드시 해야 할 것

1. **Agent를 Stateless로 설계 ✅**
   ```python
   # GOOD
   async def agent_graph(input: dict) -> dict:
       # 입력 받고, 처리하고, 결과 반환
   ```

2. **Agent 실행 로깅 ✅**
   ```python
   # GOOD
   logger.info(f"Agent {agent_name} started", extra={
       "session_id": session_id,
       "execution_id": str(uuid.uuid4())
   })
   ```

3. **Agent Graph 캐싱 ✅**
   ```python
   # GOOD
   @lru_cache(maxsize=5)
   def get_agent_graph(agent_name: str):
       return build_agent_graph(agent_name, llm)
   ```

---

## 6. 마이그레이션 체크리스트

### Phase 1: DietAgent 파일럿

- [ ] DietAgentState 정의 (임시 State)
- [ ] build_diet_agent_graph() 구현 (Checkpointer 없이)
- [ ] diet_agent_node_v2() 구현 (Stateless 패턴)
- [ ] 테스트: State 크기 확인
- [ ] 테스트: 성능 측정
- [ ] 테스트: 기존 기능 호환성

### Phase 2: 검증

- [ ] Checkpoint 저장 횟수 확인
- [ ] State 크기 비교 (전/후)
- [ ] 실행 시간 비교 (전/후)
- [ ] 메모리 사용량 비교

### Phase 3: 나머지 Agent 적용

- [ ] 모든 Agent를 Stateless 패턴으로
- [ ] Checkpointer는 Supervisor만
- [ ] Session은 단일 유지

---

## 7. 예상 결과

### 7.1 장점

1. **단순함 유지**: 복잡한 State/Session 관리 회피
2. **성능 최적화**: Checkpoint 저장 최소화
3. **디버깅 용이**: Agent별 독립 실행 가능
4. **확장성**: 새 Agent 추가 용이

### 7.2 단점

1. **Agent 내부 중단/재개 불가능**: Supervisor 레벨에서만 가능
2. **Agent 내부 State 추적 어려움**: 로깅으로 대체

### 7.3 Trade-off

**복잡성 vs 기능**:
- Agent 내부 Checkpointing 포기
- 대신 단순함과 성능 확보

**권장**: 대부분의 경우 Agent는 빠르게 실행되므로 내부 Checkpointing 불필요

---

## 8. 결론

### 핵심 전략

1. **State**: Agent State는 임시, SupervisorState만 영구 저장
2. **Checkpointer**: Supervisor만 사용, Agent는 사용 안 함
3. **Session**: 단일 session_id 유지, Agent는 session 개념 없음

### 구현 원칙

```
Keep It Simple, Stateless
- Agent는 함수처럼
- State는 최소화
- Checkpoint는 Supervisor만
```

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 관리**: `C:\kdy\Projects\AI_PTmanager\beta_v001\reports\supervisor\STATE_MANAGEMENT_STRATEGY_251105.md`