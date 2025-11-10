# Agent Migration Guide to LangGraph Architecture

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: 기존 Simple Agent를 새로운 LangGraph 기반 아키텍처로 마이그레이션 가이드

---

## 1. 아키텍처 변경 요약

### 기존 구조 (Simple Function)
```python
async def diet_agent_node(state: SupervisorState) -> dict:
    # 단순 함수 기반
    # State는 SupervisorState에 의존
    # Checkpoint 없음
    # 재사용성 낮음
```

### 새로운 구조 (LangGraph + BaseAgent)
```python
@register_agent("diet_agent")
class DietAgent(BaseAgent):
    # LangGraph StateGraph 기반
    # 독립적인 State 관리
    # 선택적 Checkpoint
    # 높은 재사용성과 확장성
```

---

## 2. 핵심 구성 요소

### 2.1 BaseAgent 추상 클래스
```python
backend/app/octostrator/agents/base/base_agent.py
```
- 모든 Agent의 기반 클래스
- LangGraph 통합
- 선택적 Checkpoint 지원
- 의존성 관리

### 2.2 AgentRegistry
```python
backend/app/octostrator/agents/base/agent_registry.py
```
- 동적 Agent 발견 및 등록
- 10+ Agent 관리
- 런타임 Agent 생성

### 2.3 CheckpointStrategy
```python
backend/app/octostrator/agents/base/checkpoint_strategy.py
```
- Agent별 Checkpoint 전략
- NONE, AUTO, PERIODIC, MANUAL, ON_COMPLETE
- 성능 최적화

### 2.4 DependencyResolver
```python
backend/app/octostrator/agents/base/dependency_resolver.py
```
- Agent 간 의존성 관리
- 실행 순서 결정 (Topological Sort)
- 병렬 실행 그룹 계산

---

## 3. 마이그레이션 단계별 가이드

### Step 1: 기존 Agent 분석

#### 1.1 현재 코드 검토
```python
# backend/app/octostrator/agents/diet/agent.py (기존)
async def diet_agent_node(state: SupervisorState) -> dict:
    task = state["plan"][state["current_step"]]
    user_id = state.get("user_id", 1)

    # 작업 처리
    result = await process_diet_task(task, user_id)

    # State 업데이트
    return {
        "plan": update_plan(state["plan"], result),
        "messages": state["messages"] + [AIMessage(content=result)]
    }
```

#### 1.2 필요 기능 식별
- [ ] State 요구사항
- [ ] Tool 사용 여부
- [ ] Checkpoint 필요성
- [ ] 의존성 관계

### Step 2: 새로운 Agent 클래스 생성

#### 2.1 BaseAgent 상속
```python
from ..base import BaseAgent, AgentPriority, register_agent

@register_agent("diet_agent")
class DietAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="diet_agent",
            agent_name="Diet Planning Agent",
            enable_checkpoint=True,  # 복잡한 작업
            priority=AgentPriority.HIGH,
            dependencies=[],  # 독립 실행
            **kwargs
        )
```

#### 2.2 State 정의
```python
from typing import TypedDict

class DietAgentState(TypedDict):
    # 기본 State (BaseAgentState)
    agent_id: str
    task: Dict[str, Any]
    user_context: Dict[str, Any]
    messages: List[BaseMessage]

    # Agent 전용 State
    user_profile: Dict[str, Any]
    dietary_goals: Dict[str, Any]
    meal_plan: Dict[str, Any]
```

### Step 3: LangGraph Workflow 구현

#### 3.1 Graph 구축
```python
def build_graph(self, llm=None) -> StateGraph:
    workflow = StateGraph(DietAgentState)

    # 노드 추가
    workflow.add_node("analyze", self._analyze_node)
    workflow.add_node("plan", self._plan_node)
    workflow.add_node("output", self._output_node)

    # 엣지 정의
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "plan")
    workflow.add_edge("plan", "output")
    workflow.add_edge("output", END)

    return workflow
```

#### 3.2 노드 구현
```python
async def _analyze_node(self, state: DietAgentState) -> Dict:
    # 사용자 분석 로직
    user_profile = analyze_user(state["user_context"])
    return {"user_profile": user_profile}

async def _plan_node(self, state: DietAgentState) -> Dict:
    # 식단 계획 로직
    meal_plan = create_meal_plan(state["user_profile"])
    return {"meal_plan": meal_plan}
```

### Step 4: Supervisor 통합

#### 4.1 기존 Node 대체
```python
# backend/app/octostrator/supervisor/main_graph.py

# 기존 코드 (제거)
# from ..agents.diet.agent import diet_agent_node
# workflow.add_node("diet_agent", diet_agent_node)

# 새로운 코드
from ..agents.diet import DietAgent

async def diet_agent_wrapper(state: SupervisorState) -> dict:
    """새로운 DietAgent를 기존 Supervisor와 연결"""

    # Agent 인스턴스 생성 또는 가져오기
    agent = agent_registry.get_agent_instance("diet_agent")
    if not agent:
        agent = agent_registry.create_agent("diet_agent")
        await agent.initialize(llm, checkpointer)

    # 작업 실행
    task = state["plan"][state["current_step"]]
    context = {"user_id": state.get("user_id", 1)}

    # Thread ID 생성 (Checkpoint용)
    thread_id = state.get("thread_id", "default")

    # Agent 실행
    result = await agent.execute(task, context, thread_id)

    # SupervisorState 업데이트
    return {
        "plan": update_plan_with_result(state["plan"], result),
        "messages": state["messages"] + [
            AIMessage(content=result["result"].get("summary", ""))
        ]
    }

# Workflow에 추가
workflow.add_node("diet_agent", diet_agent_wrapper)
```

### Step 5: 테스트 및 검증

#### 5.1 단위 테스트
```python
# tests/test_diet_agent.py
import pytest
from app.octostrator.agents.diet import DietAgent

@pytest.mark.asyncio
async def test_diet_agent_initialization():
    agent = DietAgent()
    assert agent.agent_id == "diet_agent"
    assert agent.enable_checkpoint == True

@pytest.mark.asyncio
async def test_diet_agent_execution():
    agent = DietAgent()
    await agent.initialize()

    task = {"type": "create_meal_plan", "duration": "week"}
    context = {"user_id": 1, "goal": "weight_loss"}

    result = await agent.execute(task, context)
    assert result["status"] == "completed"
    assert "meal_plan" in result["result"]
```

#### 5.2 통합 테스트
```python
@pytest.mark.asyncio
async def test_supervisor_with_new_diet_agent():
    # Supervisor Graph 생성
    supervisor = build_supervisor_graph(checkpointer)

    # 실행
    result = await supervisor.ainvoke(
        {"messages": [HumanMessage(content="Create diet plan")]},
        config={"configurable": {"thread_id": "test"}}
    )

    assert "diet_agent" in result["completed_agents"]
```

---

## 4. 실제 마이그레이션 예시

### 예시 1: WorkoutAgent 마이그레이션

#### Before (Simple Function):
```python
async def workout_agent_node(state: SupervisorState) -> dict:
    task = state["plan"][state["current_step"]]

    # 간단한 운동 계획 생성
    workout_plan = {
        "monday": ["Push-ups", "Squats"],
        "wednesday": ["Pull-ups", "Lunges"],
        "friday": ["Deadlifts", "Bench Press"]
    }

    return {
        "plan": update_plan(state["plan"], workout_plan),
        "messages": state["messages"] + [
            AIMessage(content="Workout plan created")
        ]
    }
```

#### After (LangGraph Agent):
```python
@register_agent("workout_agent")
class WorkoutAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="workout_agent",
            agent_name="Workout Planning Agent",
            enable_checkpoint=True,
            priority=AgentPriority.NORMAL,
            dependencies=["diet_agent"],  # Diet 후 실행
            **kwargs
        )

    def build_graph(self, llm=None) -> StateGraph:
        workflow = StateGraph(WorkoutAgentState)

        # 복잡한 workflow
        workflow.add_node("assess_fitness", self._assess_fitness_node)
        workflow.add_node("plan_exercises", self._plan_exercises_node)
        workflow.add_node("schedule_workouts", self._schedule_workouts_node)
        workflow.add_node("generate_videos", self._generate_videos_node)

        # 조건부 엣지
        workflow.add_edge(START, "assess_fitness")
        workflow.add_conditional_edges(
            "assess_fitness",
            self._route_by_fitness_level,
            {
                "beginner": "plan_exercises",
                "advanced": "schedule_workouts"
            }
        )

        return workflow
```

### 예시 2: NotificationAgent 마이그레이션

#### Before:
```python
async def notification_agent_node(state: SupervisorState) -> dict:
    # 단순 알림 전송
    send_notification(state["user_id"], state["message"])
    return state
```

#### After (Stateless):
```python
@register_agent("notification_agent")
class NotificationAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="notification_agent",
            agent_name="Notification Agent",
            enable_checkpoint=False,  # Stateless
            priority=AgentPriority.LOW,
            dependencies=[],
            **kwargs
        )

    def build_graph(self, llm=None) -> StateGraph:
        workflow = StateGraph(NotificationState)

        # 단순 workflow
        workflow.add_node("send", self._send_notification_node)
        workflow.add_edge(START, "send")
        workflow.add_edge("send", END)

        return workflow
```

---

## 5. Checkpoint 전략 가이드

### 5.1 Checkpoint가 필요한 경우
```python
# 복잡한 다단계 작업
enable_checkpoint=True

# 예시:
- DietAgent: 사용자 분석 → 식단 계획 → 영양 계산
- WorkoutAgent: 체력 평가 → 운동 계획 → 일정 조정
- PaymentAgent: 결제 처리 → 검증 → 확인
```

### 5.2 Checkpoint가 불필요한 경우
```python
# 단순 단일 작업
enable_checkpoint=False

# 예시:
- NotificationAgent: 알림 전송만
- ReportingAgent: 리포트 생성만
- SummaryAgent: 요약만
```

### 5.3 Checkpoint 모드 설정
```python
from app.octostrator.agents.base import get_checkpoint_strategy, CheckpointMode

checkpoint_strategy = get_checkpoint_strategy()

# Agent별 전략 설정
checkpoint_strategy.set_strategy("diet_agent", CheckpointMode.AUTO)
checkpoint_strategy.set_strategy("workout_agent", CheckpointMode.PERIODIC)
checkpoint_strategy.set_strategy("notification_agent", CheckpointMode.NONE)
```

---

## 6. Agent 등록 및 검색

### 6.1 자동 등록 (데코레이터)
```python
@register_agent("custom_agent")
class CustomAgent(BaseAgent):
    pass
```

### 6.2 수동 등록
```python
from app.octostrator.agents.base import agent_registry

agent_registry.register(CustomAgent, "custom_agent")
```

### 6.3 동적 검색
```python
# 모든 Agent 검색
agent_registry.discover_agents("backend/app/octostrator/agents")

# 특정 Agent 가져오기
diet_agent = agent_registry.create_agent("diet_agent")

# Checkpoint 사용 Agent 목록
checkpoint_agents = agent_registry.get_agents_with_checkpoint()
```

---

## 7. 의존성 관리

### 7.1 의존성 정의
```python
class ScheduleAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(
            dependencies=["diet_agent", "workout_agent"],
            **kwargs
        )
```

### 7.2 실행 계획 생성
```python
from app.octostrator.agents.base import get_dependency_resolver

resolver = get_dependency_resolver()

# Agent 추가
resolver.add_agent("diet_agent", [])
resolver.add_agent("workout_agent", ["diet_agent"])
resolver.add_agent("schedule_agent", ["diet_agent", "workout_agent"])

# 실행 계획
plan = resolver.create_execution_plan()
print(plan.parallel_groups)
# [[diet_agent], [workout_agent], [schedule_agent]]
```

---

## 8. 문제 해결 가이드

### Issue 1: Import Error
```python
# 문제
ModuleNotFoundError: No module named 'app.octostrator.agents.base'

# 해결
# PYTHONPATH 확인
export PYTHONPATH=$PYTHONPATH:/path/to/backend
```

### Issue 2: Checkpoint 연결 실패
```python
# 문제
ValueError: POSTGRES_URL not configured

# 해결
# .env 파일 확인
POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname
```

### Issue 3: 순환 의존성
```python
# 문제
DependencyStatus.CIRCULAR: [['agent_a', 'agent_b', 'agent_a']]

# 해결
# 의존성 재설계
agent_a.dependencies = []
agent_b.dependencies = ["agent_a"]
```

---

## 9. 성능 최적화

### 9.1 Agent Graph 캐싱
```python
from functools import lru_cache

@lru_cache(maxsize=10)
def get_cached_agent(agent_id: str) -> BaseAgent:
    agent = agent_registry.create_agent(agent_id)
    agent.initialize()
    return agent
```

### 9.2 병렬 실행
```python
import asyncio

async def execute_parallel_agents(agents: List[BaseAgent]):
    tasks = [
        agent.execute(task, context)
        for agent in agents
    ]
    results = await asyncio.gather(*tasks)
    return results
```

---

## 10. 마이그레이션 체크리스트

### Phase 1: 준비 (Day 1-2)
- [ ] BaseAgent 구현 완료
- [ ] AgentRegistry 구현 완료
- [ ] CheckpointStrategy 구현 완료
- [ ] DependencyResolver 구현 완료

### Phase 2: 파일럿 (Day 3-5)
- [ ] DietAgent 마이그레이션
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 수행
- [ ] 성능 측정

### Phase 3: 전체 마이그레이션 (Day 6-12)
- [ ] WorkoutAgent 마이그레이션
- [ ] ScheduleAgent 마이그레이션
- [ ] CoachingAgent 마이그레이션
- [ ] NotificationAgent 마이그레이션
- [ ] 나머지 Agent 마이그레이션

### Phase 4: 최적화 (Day 13-15)
- [ ] Checkpoint 전략 튜닝
- [ ] 의존성 최적화
- [ ] 병렬 실행 구현
- [ ] 모니터링 추가

### Phase 5: 배포 (Day 15+)
- [ ] 문서화 완료
- [ ] 코드 리뷰
- [ ] 스테이징 배포
- [ ] 프로덕션 배포

---

## 11. 참고 자료

### 문서
- `reports/supervisor/SCALABLE_AGENT_ARCHITECTURE_251105.md`
- `reports/supervisor/STATE_MANAGEMENT_STRATEGY_251105.md`
- `reports/reference/service_agent/`

### 코드
- `backend/app/octostrator/agents/base/` - 기반 모듈
- `backend/app/octostrator/agents/diet/` - 예시 구현
- `backend/app/service_agent/` - 참조 구현

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**다음 단계**: Phase 2 파일럿 시작 - DietAgent 실제 마이그레이션 및 테스트