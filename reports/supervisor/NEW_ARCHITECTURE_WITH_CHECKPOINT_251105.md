# 새로운 아키텍처: 팀 기반 독립 State & Checkpoint 전략

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: service_agent 구조를 참고한 새로운 아키텍처 제안

---

## 1. 핵심 변경 사항

### 1.1 기존 접근법의 문제점

**원래 계획 (문제있음)**:
```
Supervisor (Checkpoint ✓)
    ↓
Agent (No Checkpoint ✗) → Agent 중단/재개 불가능!
```

**service_agent에서 발견한 해결책**:
```
MainSupervisor (Checkpoint ✓)
    ├─ SearchTeam (독립 State + Checkpoint ✓)
    ├─ DocumentTeam (독립 State + Checkpoint ✓)
    └─ AnalysisTeam (독립 State + Checkpoint ✓)
```

### 1.2 새로운 원칙

1. **팀 기반 아키텍처**: Agent를 팀으로 그룹화
2. **독립적인 State**: 각 팀은 자체 State 보유
3. **독립적인 Checkpoint**: 각 팀은 자체 Checkpoint 보유
4. **State 격리**: State pollution 방지

---

## 2. 새로운 아키텍처 설계

### 2.1 State 구조

```python
# backend/app/octostrator/states/separated_states.py

# 1. 공유 State (최소한의 공통 정보)
class SharedState(TypedDict):
    """모든 팀이 공유하는 최소한의 상태"""
    user_query: str
    session_id: str
    user_id: Optional[int]
    timestamp: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]

# 2. 팀별 독립 State
class FitnessTeamState(TypedDict):
    """피트니스 팀 전용 State (Diet + Workout)"""
    team_name: str
    shared_context: Dict[str, Any]  # SharedState 복사본

    # Diet 관련
    meal_logs: List[Dict[str, Any]]
    nutrition_summary: Dict[str, Any]

    # Workout 관련
    workout_history: List[Dict[str, Any]]
    exercise_recommendations: List[Dict[str, Any]]

    # 공통
    status: str
    error: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]

class ScheduleTeamState(TypedDict):
    """스케줄 팀 전용 State (Schedule + MemberCare)"""
    team_name: str
    shared_context: Dict[str, Any]

    # Schedule 관련
    pt_schedules: List[Dict[str, Any]]

    # MemberCare 관련
    member_progress: Dict[str, Any]
    alerts: List[Dict[str, Any]]

    status: str
    error: Optional[str]

class CoachingTeamState(TypedDict):
    """코칭 팀 전용 State"""
    team_name: str
    shared_context: Dict[str, Any]

    # Coaching 관련
    search_results: List[Dict[str, Any]]
    bookmarks: List[Dict[str, Any]]

    status: str
    error: Optional[str]

# 3. 메인 Supervisor State
class MainSupervisorState(TypedDict):
    """메인 Supervisor State"""
    # 핵심 필드
    query: str
    session_id: str
    request_id: str

    # Planning
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]

    # 팀 States (독립적)
    fitness_team_state: Optional[Dict[str, Any]]
    schedule_team_state: Optional[Dict[str, Any]]
    coaching_team_state: Optional[Dict[str, Any]]

    # 실행 추적
    current_phase: str
    active_teams: List[str]
    completed_teams: List[str]

    # 결과
    team_results: Dict[str, Any]
    aggregated_results: Dict[str, Any]
    final_response: Optional[str]
```

### 2.2 팀 구조

```python
# backend/app/octostrator/teams/

teams/
  ├─ __init__.py
  ├─ fitness_team.py       # Diet + Workout 통합
  ├─ schedule_team.py      # Schedule + MemberCare 통합
  └─ coaching_team.py      # Coaching 독립

# fitness_team.py
class FitnessTeam:
    """피트니스 팀 (Diet + Workout)"""

    def __init__(self, llm_context, enable_checkpointing=True):
        self.llm_context = llm_context
        self.enable_checkpointing = enable_checkpointing
        self.checkpointer = None  # 팀별 독립 Checkpointer

    async def build_workflow(self):
        """팀 워크플로우 구성"""
        workflow = StateGraph(FitnessTeamState)

        # 노드 추가
        workflow.add_node("analyze_request", self.analyze_request)
        workflow.add_node("get_diet_data", self.get_diet_data)
        workflow.add_node("get_workout_data", self.get_workout_data)
        workflow.add_node("generate_response", self.generate_response)

        # 엣지 정의
        workflow.add_edge(START, "analyze_request")
        workflow.add_edge("analyze_request", "get_diet_data")
        workflow.add_edge("get_diet_data", "get_workout_data")
        workflow.add_edge("get_workout_data", "generate_response")
        workflow.add_edge("generate_response", END)

        # 팀별 Checkpointer 적용
        if self.enable_checkpointing:
            self.checkpointer = await create_checkpointer()
            return workflow.compile(checkpointer=self.checkpointer)
        else:
            return workflow.compile()
```

### 2.3 Checkpoint 전략

```python
# backend/app/octostrator/checkpointer/team_checkpointer.py

class TeamCheckpointerManager:
    """팀별 독립 Checkpointer 관리"""

    def __init__(self):
        self._team_checkpointers: Dict[str, AsyncPostgresSaver] = {}
        self._context_managers: Dict[str, object] = {}

    async def get_team_checkpointer(self, team_name: str) -> AsyncPostgresSaver:
        """팀별 Checkpointer 가져오기"""

        # 캐시 확인
        if team_name in self._team_checkpointers:
            return self._team_checkpointers[team_name]

        # 새로 생성
        conn_string = os.getenv("POSTGRES_URL")

        # 팀별 네임스페이스 사용
        # checkpoints 테이블의 checkpoint_ns 필드 활용
        context_manager = AsyncPostgresSaver.from_conn_string(
            conn_string,
            checkpoint_ns=f"team_{team_name}"  # 팀별 네임스페이스
        )

        checkpointer = await context_manager.__aenter__()
        await checkpointer.setup()

        # 캐싱
        self._team_checkpointers[team_name] = checkpointer
        self._context_managers[team_name] = context_manager

        return checkpointer
```

### 2.4 Session 관리

```python
# Session은 계층 구조로 관리
session_structure = {
    "main_session": "session_123",  # 메인 Supervisor
    "team_sessions": {
        "fitness": "session_123_fitness",    # 팀별 세션
        "schedule": "session_123_schedule",
        "coaching": "session_123_coaching"
    }
}

# 각 팀은 독립적인 thread_id 사용
fitness_config = {"configurable": {"thread_id": "session_123_fitness"}}
schedule_config = {"configurable": {"thread_id": "session_123_schedule"}}
```

---

## 3. 새로운 Supervisor 구조

### 3.1 MainSupervisor

```python
# backend/app/octostrator/supervisor/main_supervisor.py

class MainSupervisor:
    """메인 Supervisor - 팀 조정"""

    def __init__(self, enable_checkpointing=True):
        self.enable_checkpointing = enable_checkpointing
        self.main_checkpointer = None

        # 팀 초기화
        self.teams = {
            "fitness": FitnessTeam(enable_checkpointing=True),
            "schedule": ScheduleTeam(enable_checkpointing=True),
            "coaching": CoachingTeam(enable_checkpointing=True)
        }

    async def build_workflow(self):
        """메인 워크플로우 구성"""
        workflow = StateGraph(MainSupervisorState)

        # Planning
        workflow.add_node("planning", self.planning_node)

        # Team Execution (병렬 가능)
        workflow.add_node("fitness_team", self.execute_fitness_team)
        workflow.add_node("schedule_team", self.execute_schedule_team)
        workflow.add_node("coaching_team", self.execute_coaching_team)

        # Aggregation
        workflow.add_node("aggregator", self.aggregator_node)

        # 조건부 라우팅
        workflow.add_conditional_edges(
            "planning",
            self.route_to_teams,
            {
                "fitness": "fitness_team",
                "schedule": "schedule_team",
                "coaching": "coaching_team",
                "all": ["fitness_team", "schedule_team", "coaching_team"]
            }
        )

        # 메인 Checkpointer
        if self.enable_checkpointing:
            self.main_checkpointer = await create_checkpointer()
            return workflow.compile(checkpointer=self.main_checkpointer)
        else:
            return workflow.compile()

    async def execute_fitness_team(self, state: MainSupervisorState) -> dict:
        """피트니스 팀 실행"""
        # 1. 팀 State 생성
        team_state = FitnessTeamState(
            team_name="fitness",
            shared_context=self.extract_shared_state(state),
            # ... 초기화
        )

        # 2. 팀 워크플로우 실행 (독립 Checkpoint)
        fitness_workflow = await self.teams["fitness"].build_workflow()
        team_config = {"configurable": {"thread_id": f"{state['session_id']}_fitness"}}
        result = await fitness_workflow.ainvoke(team_state, config=team_config)

        # 3. 결과를 메인 State에 병합
        return {
            "fitness_team_state": result,
            "team_results": {**state.get("team_results", {}), "fitness": result}
        }
```

### 3.2 실행 흐름

```
1. 사용자 요청
    ↓
2. MainSupervisor (main checkpoint)
    ├─ Planning: 어떤 팀이 필요한지 결정
    ↓
3. 팀 실행 (병렬 가능)
    ├─ FitnessTeam (독립 state + checkpoint)
    ├─ ScheduleTeam (독립 state + checkpoint)
    └─ CoachingTeam (독립 state + checkpoint)
    ↓
4. Aggregator: 팀 결과 통합
    ↓
5. 최종 응답
```

---

## 4. TODO 관리 개선

### 4.1 ExecutionStepState (service_agent 참고)

```python
class ExecutionStepState(TypedDict):
    """TODO 아이템 + 실행 추적"""
    # 식별
    step_id: str                    # "step_0", "step_1"
    step_type: str                  # 'planning'|'fitness'|'schedule'|'coaching'
    team: str                       # 담당 팀

    # 작업
    priority: int                   # 실행 우선순위
    task: str                       # 작업명
    description: str                # 설명

    # 상태
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    progress_percentage: int        # 0-100

    # 타이밍
    started_at: Optional[str]
    completed_at: Optional[str]

    # 결과
    result: Optional[Dict[str, Any]]
    error: Optional[str]
```

### 4.2 PlanningState

```python
class PlanningState(TypedDict):
    """계획 수립 State"""
    raw_query: str
    analyzed_intent: Dict[str, Any]

    # 실행 계획 (TODO 리스트)
    execution_steps: List[ExecutionStepState]

    # 팀 할당
    team_assignments: Dict[str, List[str]]  # {"fitness": ["step_0", "step_1"]}

    # 병렬 실행 그룹
    parallel_groups: List[List[str]]
```

---

## 5. 장단점 분석

### 5.1 장점

✅ **Agent 중단/재개 가능**: 각 팀이 독립 checkpoint
✅ **State 격리**: State pollution 방지
✅ **병렬 실행**: 독립적인 팀은 병렬 실행 가능
✅ **확장성**: 새로운 팀 추가 용이
✅ **디버깅**: 팀별 독립 추적 가능

### 5.2 단점

❌ **복잡성 증가**: 관리할 State/Checkpoint 증가
❌ **메모리 사용량**: 여러 checkpoint 유지
❌ **동기화 문제**: 팀 간 데이터 공유 시 주의 필요

### 5.3 Trade-off

| 요소 | 단순 함수 방식 | 팀 기반 Checkpoint |
|------|---------------|-------------------|
| 구현 복잡도 | 낮음 | 높음 |
| 중단/재개 | 불가능 | 가능 |
| State 관리 | 단순 | 복잡 |
| 확장성 | 낮음 | 높음 |
| 디버깅 | 어려움 | 용이 |

---

## 6. 마이그레이션 계획

### Phase 1: 인프라 구축 (2일)
- [ ] separated_states.py 작성
- [ ] TeamCheckpointerManager 구현
- [ ] 팀 base 클래스 작성

### Phase 2: 팀 구현 (3일)
- [ ] FitnessTeam 구현 (Diet + Workout)
- [ ] ScheduleTeam 구현 (Schedule + MemberCare)
- [ ] CoachingTeam 구현

### Phase 3: Supervisor 재구성 (2일)
- [ ] MainSupervisor 구현
- [ ] Planning 로직 수정
- [ ] Aggregator 구현

### Phase 4: 테스트 (2일)
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 성능 테스트

### Phase 5: 전환 (1일)
- [ ] 기존 코드 deprecated 처리
- [ ] 문서 업데이트
- [ ] 배포

**총 예상 시간**: 10일

---

## 7. 결론

### 7.1 권장사항

**현재 상황**:
- 단순 함수 방식은 Agent 중단/재개 불가능
- service_agent는 팀별 독립 State + Checkpoint 사용

**권장 아키텍처**:
1. **팀 기반 구조**: Agent를 논리적 팀으로 그룹화
2. **독립 State**: 팀별 독립 State로 격리
3. **독립 Checkpoint**: 팀별 checkpoint로 중단/재개 지원
4. **계층적 Session**: 메인 + 팀별 session 관리

### 7.2 결정 필요 사항

1. **전면 개편 vs 점진적 전환**
   - 전면 개편: 깔끔하지만 시간 소요
   - 점진적: 빠르지만 코드 복잡

2. **팀 구성**
   - Option A: 3개 팀 (Fitness / Schedule / Coaching)
   - Option B: 5개 독립 Agent 유지
   - Option C: 2개 팀 (Core / Support)

3. **Checkpoint 범위**
   - 모든 팀 checkpoint (권장)
   - 중요 팀만 checkpoint
   - 선택적 checkpoint

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 관리**: `C:\kdy\Projects\AI_PTmanager\beta_v001\reports\supervisor\NEW_ARCHITECTURE_WITH_CHECKPOINT_251105.md`