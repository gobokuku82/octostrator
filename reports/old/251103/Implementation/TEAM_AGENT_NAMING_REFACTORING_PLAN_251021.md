# Team/Agent 네이밍 혼용 문제 분석 및 리팩토링 계획

## 📋 Executive Summary

**작성일**: 2025-10-21 (최종 검증 완료)
**대상 시스템**: LangGraph 0.6 기반 부동산 상담 챗봇
**분석 범위**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent`

### 핵심 문제
초기 설계에서 **"team"** 용어로 명명했던 실행 단위를 **"agent"**로 변경하는 과정에서 코드와 주석, 변수명 등에서 두 용어가 혼용되어 개발자에게 혼란을 야기하고 있습니다.

### 영향도
- **파일명**: `team_supervisor.py` (클래스명 `TeamBasedSupervisor`)
- **코드 내부**: team/agent 용어 혼재 (약 100+ 위치)
- **아키텍처**: execution_agents 폴더에 Executor 클래스들이 위치하지만 내부적으로 "team" 용어 사용
- **가독성**: 신규 개발자가 시스템 이해 시 혼란 발생
- **⚠️ 추가 발견**: `ExecutionStepState.team` 필드는 **중요 의미** 보유 (근본 원인 분석 보고서 참조)

### 🎯 보고서 검증 완료
✅ 기존 매뉴얼 문서 (ARCHITECTURE_OVERVIEW, EXECUTION_AGENTS_GUIDE, STATE_MANAGEMENT_GUIDE) 교차 검증
✅ ROOT_CAUSE_ANALYSIS_251021 보고서와 정합성 확인
✅ 놓친 부분 4가지 추가 발견 및 반영

---

## 1. 현황 분석

### 1.1 디렉토리 구조

```
backend/app/service_agent/
├── execution_agents/          # ✅ "agents" 네이밍 (정확)
│   ├── search_executor.py     # SearchExecutor
│   ├── document_executor.py   # DocumentExecutor
│   └── analysis_executor.py   # AnalysisExecutor
├── supervisor/
│   └── team_supervisor.py     # ❌ "team" 네이밍 (불일치)
│       └── TeamBasedSupervisor 클래스
├── foundation/
│   ├── agent_registry.py      # ✅ AgentRegistry
│   ├── agent_adapter.py       # ✅ AgentAdapter
│   └── separated_states.py    # ⚠️ team/agent 혼용
├── cognitive_agents/          # ✅ "agents" 네이밍
│   ├── planning_agent.py
│   ├── query_decomposer.py
│   └── execution_orchestrator.py
└── llm_manager/
    └── prompts/cognitive/
        └── agent_selection.txt # ⚠️ "Agent/Team" 혼용
```

### 1.2 용어 사용 패턴 분석

#### A. 파일명 및 클래스명
| 파일 | 현재 네이밍 | 내부 용어 | 불일치 여부 |
|------|-------------|-----------|-------------|
| `team_supervisor.py` | Team | team/agent 혼용 | ❌ |
| `search_executor.py` | Executor | `self.team_name = "search"` | ⚠️ |
| `agent_registry.py` | Agent | `team` 파라미터 사용 | ⚠️ |
| `agent_adapter.py` | Agent | `register_existing_agents()` 메서드에서 team 등록 | ⚠️ |
| `separated_states.py` | - | `SearchTeamState`, `team` 필드 | ⚠️ |

#### B. 주요 코드 내 혼용 사례

**1) team_supervisor.py (84곳)**
```python
# 파일명과 클래스명에서 "team" 사용
class TeamBasedSupervisor:
    """팀 기반 Supervisor"""

    # 하지만 내부에서는 혼용
    self.teams = {  # ← "teams" 변수
        "search": SearchExecutor(llm_context=llm_context),  # ← Executor 클래스
        "document": DocumentExecutor(llm_context=llm_context),
        "analysis": AnalysisExecutor(llm_context=llm_context)
    }

    # agent 용어도 사용
    available_agents = AgentRegistry.list_agents(enabled_only=True)

    # team 용어도 사용
    active_teams = state.get("active_teams", [])
    def _get_team_for_agent(self, agent_name: str) -> str:
```

**2) search_executor.py (51곳)**
```python
class SearchExecutor:
    def __init__(self, llm_context=None):
        self.team_name = "search"  # ← "team" 용어 사용
        self.available_agents = self._initialize_agents()  # ← "agents" 용어 사용

    def _build_subgraph(self):
        logger.info("SearchTeam subgraph built successfully")  # ← "Team" 용어
```

**3) agent_adapter.py (21곳)**
```python
def register_existing_agents():
    """Team-based 아키텍처를 위한 팀/에이전트 등록"""  # ← 혼용

    # SearchTeam 등록 (가상 에이전트로 등록)
    AgentRegistry.register(
        name="search_team",  # ← "team" suffix
        agent_class=SearchTeamPlaceholder,  # ← "Team" 용어
        team="search",  # ← "team" 파라미터
        capabilities=capabilities
    )
```

**4) separated_states.py (74곳)**
```python
# State 클래스명에 "Team" 사용
class SearchTeamState(TypedDict):
    team_name: str  # ← "team" 필드
    # ...

class ExecutionStepState(TypedDict):
    team: str  # ← "team" 필드 (예: "search")
```

**5) execution_orchestrator.py (45곳)**
```python
def orchestrate_with_state(self, state: MainSupervisorState):
    for step in execution_steps:
        team = step.get("team")  # ← "team" 용어

        # 오케스트레이션 메타데이터 추가
        step["orchestration"] = {
            "selected_tools": tool_selections.get(team, []),  # ← "team" 키
        }
```

### 1.3 혼란을 야기하는 구체적 사례

#### 사례 1: 파일명과 클래스명 불일치
```
📁 execution_agents/search_executor.py  ← "agent" 폴더, "executor" 파일명
   └── class SearchExecutor:            ← "Executor" 클래스명
         self.team_name = "search"      ← "team" 변수명
```

**문제**: 개발자가 "이게 Agent인가, Team인가, Executor인가?" 혼란

#### 사례 2: Registry 시스템의 이중 용어
```python
# agent_adapter.py
def register_existing_agents():  # ← "agents" 함수명
    """Team-based 아키텍처..."""  # ← "Team" 주석

    AgentRegistry.register(
        name="search_team",  # ← "team" suffix
        team="search",       # ← "team" 파라미터
    )
```

**문제**: 같은 함수에서 "agent"와 "team" 용어가 동시에 사용됨

#### 사례 3: State 구조의 혼용
```python
state["active_teams"] = ["search", "document"]  # ← "teams" 복수형
state["team_results"] = {...}                   # ← "team" 단수형

# 하지만 실제 클래스는
SearchExecutor, DocumentExecutor, AnalysisExecutor  # ← "Executor" 네이밍
```

**문제**: State에서는 "team", 실제 구현체는 "Executor"

---

## 2. 개념적 정리

### 2.1 현재 아키텍처에서 용어의 의미

시스템은 **3-Layer 아키텍처**로 구성되어 있습니다:

```
┌──────────────────────────────────────┐
│   Supervisor Layer                    │  ← 전체 조율
│   (TeamBasedSupervisor)              │
└──────────────────────────────────────┘
            ↓
┌──────────────────────────────────────┐
│   Cognitive Layer                     │  ← 계획 수립
│   (PlanningAgent, Orchestrator)      │
└──────────────────────────────────────┘
            ↓
┌──────────────────────────────────────┐
│   Execution Layer                     │  ← 실제 작업 수행
│   (SearchExecutor,                    │
│    DocumentExecutor,                  │
│    AnalysisExecutor)                  │
└──────────────────────────────────────┘
```

### 2.2 용어 재정의 제안

| 기존 용어 | 새 용어 | 정의 | 예시 |
|----------|---------|------|------|
| Team | **ExecutionUnit** 또는 **Executor** | 실제 작업을 수행하는 독립 실행 단위 | SearchExecutor |
| Agent | **Agent** (유지) | LangGraph 기반 자율 에이전트 | PlanningAgent |
| TeamSupervisor | **ExecutionSupervisor** | Executor들을 조율하는 상위 레이어 | - |

### 2.3 권장 네이밍 규칙

```python
# ✅ 추천 (일관성 있는 네이밍)
class ExecutionSupervisor:
    """Executor들을 조율하는 Supervisor"""

    def __init__(self):
        self.executors = {
            "search": SearchExecutor(),
            "document": DocumentExecutor(),
            "analysis": AnalysisExecutor()
        }

        self.active_executors = []
        self.executor_results = {}

# State 필드명도 통일
class ExecutionStepState(TypedDict):
    executor_name: str  # "search", "document", "analysis"
    executor_type: str  # "search", "document", "analysis"
```

---

## 3. 리팩토링 계획

### 3.1 리팩토링 우선순위

#### Priority 1 (High): 핵심 파일 및 클래스명 변경
- [ ] `team_supervisor.py` → `execution_supervisor.py`
- [ ] `TeamBasedSupervisor` → `ExecutionSupervisor`
- [ ] `SearchTeamState` → `SearchExecutorState`
- [ ] `DocumentTeamState` → `DocumentExecutorState`
- [ ] `AnalysisTeamState` → `AnalysisExecutorState`

#### Priority 2 (Medium): 변수명 및 메서드명 통일
- [ ] `self.teams` → `self.executors`
- [ ] `active_teams` → `active_executors`
- [ ] `team_results` → `executor_results`
- [ ] `_get_team_for_agent()` → `_get_executor_for_agent()`
- [ ] `execute_teams_node()` → `execute_executors_node()`

#### Priority 3 (Low): 주석 및 로그 메시지 정리
- [ ] "팀 기반 Supervisor" → "Executor 조율 Supervisor"
- [ ] "SearchTeam subgraph" → "SearchExecutor subgraph"
- [ ] "Team 실행 노드" → "Executor 실행 노드"

### 3.2 단계별 실행 계획

#### Phase 1: 준비 단계 (1일)
1. **백업 생성**
   ```bash
   git checkout -b refactor/team-to-executor-naming
   ```

2. **영향도 분석**
   - import 구문 의존성 확인
   - API endpoint 영향 확인
   - Database schema 영향 확인 (State checkpointing)

#### Phase 2: 파일명 및 클래스명 변경 (1일)
1. **파일 이름 변경**
   ```bash
   # 1. team_supervisor.py → execution_supervisor.py
   git mv backend/app/service_agent/supervisor/team_supervisor.py \
          backend/app/service_agent/supervisor/execution_supervisor.py
   ```

2. **클래스명 변경** (execution_supervisor.py)
   ```python
   # Before
   class TeamBasedSupervisor:
       """팀 기반 Supervisor"""

   # After
   class ExecutionSupervisor:
       """Executor 조율 Supervisor"""
   ```

3. **Import 구문 업데이트** (모든 파일)
   ```python
   # Before
   from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

   # After
   from app.service_agent.supervisor.execution_supervisor import ExecutionSupervisor
   ```

#### Phase 3: State 클래스명 변경 (1일)
1. **separated_states.py 수정**
   ```python
   # Before
   class SearchTeamState(TypedDict):
       team_name: str

   # After
   class SearchExecutorState(TypedDict):
       executor_name: str
   ```

2. **전체 코드베이스 업데이트**
   - SearchTeamState → SearchExecutorState (20+ 파일)
   - DocumentTeamState → DocumentExecutorState (15+ 파일)
   - AnalysisTeamState → AnalysisExecutorState (15+ 파일)

#### Phase 4: 변수명 및 메서드명 통일 (2일)
1. **execution_supervisor.py 내부 변경**
   ```python
   # Before
   self.teams = {...}
   active_teams = state.get("active_teams", [])

   # After
   self.executors = {...}
   active_executors = state.get("active_executors", [])
   ```

2. **State 필드명 변경**
   ```python
   # Before
   state["active_teams"] = ["search", "document"]
   state["team_results"] = {...}

   # After
   state["active_executors"] = ["search", "document"]
   state["executor_results"] = {...}
   ```

3. **메서드명 변경**
   - `_get_team_for_agent()` → `_get_executor_for_agent()`
   - `execute_teams_node()` → `execute_executors_node()`
   - `_execute_teams_parallel()` → `_execute_executors_parallel()`
   - `_execute_teams_sequential()` → `_execute_executors_sequential()`
   - `_execute_single_team()` → `_execute_single_executor()`

#### Phase 5: 주석 및 로그 메시지 정리 (1일)
1. **한글 주석 업데이트**
   ```python
   # Before
   """팀 기반 Supervisor - 각 팀을 독립적으로 관리"""

   # After
   """Executor 조율 Supervisor - 각 Executor를 독립적으로 관리"""
   ```

2. **로그 메시지 업데이트**
   ```python
   # Before
   logger.info(f"[TeamSupervisor] Executing {len(teams)} teams in parallel")

   # After
   logger.info(f"[ExecutionSupervisor] Executing {len(executors)} executors in parallel")
   ```

#### Phase 6: 테스트 및 검증 (2일)
1. **단위 테스트 업데이트**
   - 변경된 클래스명/메서드명 반영
   - State 필드명 변경 반영

2. **통합 테스트 실행**
   - 전체 워크플로우 정상 동작 확인
   - Checkpointing 정상 동작 확인
   - WebSocket 실시간 통신 확인

3. **회귀 테스트**
   - 기존 기능 정상 동작 확인
   - 엣지 케이스 확인

---

## 4. 리팩토링 상세 가이드

### 4.1 execution_supervisor.py 변경 가이드

#### 변경 대상 항목 (우선순위 순)

| 변경 전 | 변경 후 | 위치 | 영향도 |
|---------|---------|------|--------|
| `class TeamBasedSupervisor` | `ExecutionSupervisor` | Line 40 | High |
| `self.teams` | `self.executors` | Line 74 | High |
| `active_teams` | `active_executors` | Line 166+ | High |
| `team_results` | `executor_results` | Line 169 | High |
| `execute_teams_node` | `execute_executors_node` | Line 547 | High |
| `_get_team_for_agent` | `_get_executor_for_agent` | Line 399 | Medium |
| `_execute_teams_parallel` | `_execute_executors_parallel` | Line 600 | Medium |
| `_execute_teams_sequential` | `_execute_executors_sequential` | Line 627 | Medium |
| `_execute_single_team` | `_execute_single_executor` | Line 731 | Medium |
| `_find_step_id_for_team` | `_find_step_id_for_executor` | Line 523 | Medium |
| `"팀 기반 Supervisor"` | `"Executor 조율 Supervisor"` | Line 2, 42 | Low |
| `"Team-based workflow"` | `"Executor-based workflow"` | Line 128, 1132 | Low |

#### 구체적 변경 예시

**1) 클래스 정의 및 초기화 (Line 40-84)**
```python
# ========== BEFORE ==========
class TeamBasedSupervisor:
    """
    팀 기반 Supervisor
    각 팀을 독립적으로 관리하고 조정
    """

    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        # ...

        # 팀 초기화
        self.teams = {
            "search": SearchExecutor(llm_context=llm_context),
            "document": DocumentExecutor(llm_context=llm_context),
            "analysis": AnalysisExecutor(llm_context=llm_context)
        }

        logger.info(f"TeamBasedSupervisor initialized with 3 teams")

# ========== AFTER ==========
class ExecutionSupervisor:
    """
    Executor 조율 Supervisor
    각 Executor를 독립적으로 관리하고 조정
    """

    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        # ...

        # Executor 초기화
        self.executors = {
            "search": SearchExecutor(llm_context=llm_context),
            "document": DocumentExecutor(llm_context=llm_context),
            "analysis": AnalysisExecutor(llm_context=llm_context)
        }

        logger.info(f"ExecutionSupervisor initialized with 3 executors")
```

**2) initialize_node (Line 157-172)**
```python
# ========== BEFORE ==========
async def initialize_node(self, state: MainSupervisorState) -> MainSupervisorState:
    logger.info("[TeamSupervisor] Initializing")

    state["active_teams"] = []
    state["completed_teams"] = []
    state["failed_teams"] = []
    state["team_results"] = {}

    return state

# ========== AFTER ==========
async def initialize_node(self, state: MainSupervisorState) -> MainSupervisorState:
    logger.info("[ExecutionSupervisor] Initializing")

    state["active_executors"] = []
    state["completed_executors"] = []
    state["failed_executors"] = []
    state["executor_results"] = {}

    return state
```

**3) planning_node에서 executor 활성화 (Line 361-369)**
```python
# ========== BEFORE ==========
# 활성화할 팀 결정
active_teams = set()
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)
logger.info(f"[TeamSupervisor] Plan created: {len(active_teams)} teams")

# ========== AFTER ==========
# 활성화할 Executor 결정
active_executors = set()
for step in planning_state["execution_steps"]:
    executor = step.get("executor")
    if executor:
        active_executors.add(executor)

state["active_executors"] = list(active_executors)
logger.info(f"[ExecutionSupervisor] Plan created: {len(active_executors)} executors")
```

**4) execute_executors_node (Line 547-598)**
```python
# ========== BEFORE ==========
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    logger.info("[TeamSupervisor] Executing teams")

    active_teams = state.get("active_teams", [])

    if execution_strategy == "parallel" and len(active_teams) > 1:
        results = await self._execute_teams_parallel(active_teams, shared_state, state)
    else:
        results = await self._execute_teams_sequential(active_teams, shared_state, state)

    for team_name, team_result in results.items():
        state = StateManager.merge_team_results(state, team_name, team_result)

# ========== AFTER ==========
async def execute_executors_node(self, state: MainSupervisorState) -> MainSupervisorState:
    logger.info("[ExecutionSupervisor] Executing executors")

    active_executors = state.get("active_executors", [])

    if execution_strategy == "parallel" and len(active_executors) > 1:
        results = await self._execute_executors_parallel(active_executors, shared_state, state)
    else:
        results = await self._execute_executors_sequential(active_executors, shared_state, state)

    for executor_name, executor_result in results.items():
        state = StateManager.merge_executor_results(state, executor_name, executor_result)
```

**5) _execute_single_executor (Line 731-760)**
```python
# ========== BEFORE ==========
async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 팀 실행"""
    team = self.teams[team_name]

    if team_name == "search":
        return await team.execute(shared_state)

# ========== AFTER ==========
async def _execute_single_executor(
    self,
    executor_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 Executor 실행"""
    executor = self.executors[executor_name]

    if executor_name == "search":
        return await executor.execute(shared_state)
```

### 4.2 separated_states.py 변경 가이드

#### 변경 대상 State 클래스

| 변경 전 | 변경 후 | 영향 받는 파일 |
|---------|---------|----------------|
| `SearchTeamState` | `SearchExecutorState` | search_executor.py, team_supervisor.py |
| `DocumentTeamState` | `DocumentExecutorState` | document_executor.py, team_supervisor.py |
| `AnalysisTeamState` | `AnalysisExecutorState` | analysis_executor.py, team_supervisor.py |
| `team_name: str` | `executor_name: str` | 모든 Executor State |
| `active_teams` | `active_executors` | MainSupervisorState |
| `team_results` | `executor_results` | MainSupervisorState |

#### 구체적 변경 예시

**1) State 클래스명 변경 (Line 76-138)**
```python
# ========== BEFORE ==========
class SearchTeamState(TypedDict):
    """Search Team 상태"""

    # Team identification
    team_name: str
    status: str

    # ...

# ========== AFTER ==========
class SearchExecutorState(TypedDict):
    """Search Executor 상태"""

    # Executor identification
    executor_name: str
    status: str

    # ...
```

**2) MainSupervisorState 필드 변경 (Line 251-318)**
```python
# ========== BEFORE ==========
class MainSupervisorState(TypedDict):
    # Team states
    search_team_state: Optional[SearchTeamState]
    document_team_state: Optional[DocumentTeamState]
    analysis_team_state: Optional[AnalysisTeamState]

    # Execution tracking
    active_teams: List[str]
    completed_teams: List[str]
    failed_teams: List[str]
    team_results: Dict[str, Any]

# ========== AFTER ==========
class MainSupervisorState(TypedDict):
    # Executor states
    search_executor_state: Optional[SearchExecutorState]
    document_executor_state: Optional[DocumentExecutorState]
    analysis_executor_state: Optional[AnalysisExecutorState]

    # Execution tracking
    active_executors: List[str]
    completed_executors: List[str]
    failed_executors: List[str]
    executor_results: Dict[str, Any]
```

**3) ExecutionStepState 필드 변경 (Line 239-268)**

⚠️ **중요 주의사항**: `ExecutionStepState.team` 필드는 **현재 시스템에서 핵심 역할**을 수행합니다!

**근본 원인 분석 보고서 (COMPLETE_ROOT_CAUSE_ANALYSIS_251021.md)에서 확인된 사실**:
- `team` 필드는 `_find_step_id_for_team(team_name)` 메서드에서 사용됨
- `active_teams = set()` → `list(active_teams)` 과정에서 순서가 역전되는 문제 발생
- 이 필드를 변경하면 **전체 실행 흐름에 영향**

**권장 변경 전략**:
```python
# ========== BEFORE ==========
class ExecutionStepState(TypedDict):
    # 식별 정보
    step_id: str
    step_type: str
    agent_name: str
    team: str  # 담당 팀 (예: "search")

# ========== AFTER (Phase 1: 병행 사용) ==========
class ExecutionStepState(TypedDict):
    # 식별 정보
    step_id: str
    step_type: str
    agent_name: str  # PlanningAgent가 선택한 에이전트명 (예: "search_team")
    team: str  # ⚠️ DEPRECATED: 하위 호환성 유지 (향후 제거 예정)
    executor: str  # 담당 Executor (예: "search") - 새로운 표준 필드

# ========== AFTER (Phase 2: team 제거, 3개월 후) ==========
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    executor: str  # 담당 Executor (예: "search")
```

**마이그레이션 로직 필요**:
```python
# team_supervisor.py (execution_supervisor.py로 변경 예정)
def _find_step_id_for_executor(self, executor_name: str, planning_state) -> Optional[str]:
    """Executor 이름으로 step_id 찾기 (하위 호환성 유지)"""
    for step in planning_state.get("execution_steps", []):
        # 새 필드 우선
        if step.get("executor") == executor_name:
            return step.get("step_id")
        # 구 필드 폴백
        if step.get("team") == executor_name:
            logger.warning(f"Using deprecated 'team' field for {executor_name}")
            return step.get("step_id")
    return None
```

**4) StateManager 메서드 변경 (Line 460-494)**
```python
# ========== BEFORE ==========
@staticmethod
def merge_team_results(
    state: MainSupervisorState,
    team_name: str,
    team_state: Any
) -> MainSupervisorState:
    """팀 결과를 MainSupervisorState에 병합"""
    logger.info(f"Merging results from team: {team_name}")

    # Store team result
    if "team_results" not in state:
        state["team_results"] = {}

    state["team_results"][team_name] = team_state

# ========== AFTER ==========
@staticmethod
def merge_executor_results(
    state: MainSupervisorState,
    executor_name: str,
    executor_state: Any
) -> MainSupervisorState:
    """Executor 결과를 MainSupervisorState에 병합"""
    logger.info(f"Merging results from executor: {executor_name}")

    # Store executor result
    if "executor_results" not in state:
        state["executor_results"] = {}

    state["executor_results"][executor_name] = executor_state
```

### 4.3 Executor 파일들 변경 가이드

#### search_executor.py 변경 사항

| 변경 전 | 변경 후 | Line |
|---------|---------|------|
| `team_name = "search"` | `executor_name = "search"` | 51 |
| `SearchTeamState` | `SearchExecutorState` | 19, 114, 150, ... |
| `"[SearchTeam]"` (로그) | `"[SearchExecutor]"` | 155, 172, ... |
| `"SearchTeam subgraph"` | `"SearchExecutor subgraph"` | 142 |

#### document_executor.py, analysis_executor.py 변경 사항

동일한 패턴으로 변경:
- `team_name` → `executor_name`
- `DocumentTeamState` → `DocumentExecutorState`
- `AnalysisTeamState` → `AnalysisExecutorState`
- 로그 메시지 내 "Team" → "Executor"

### 4.4 agent_adapter.py 및 agent_registry.py 변경 가이드

#### agent_adapter.py 주요 변경

```python
# ========== BEFORE ==========
def register_existing_agents():
    """Team-based 아키텍처를 위한 팀/에이전트 등록"""
    logger.info("Registering teams to Registry...")

    # SearchTeam 등록 (가상 에이전트로 등록)
    capabilities = AgentCapabilities(
        name="search_team",
        description="법률, 부동산, 대출 정보를 검색하는 팀",
        # ...
        team="search"
    )

    class SearchTeamPlaceholder:
        pass

    AgentRegistry.register(
        name="search_team",
        agent_class=SearchTeamPlaceholder,
        team="search",
        # ...
    )

# ========== AFTER ==========
def register_existing_agents():
    """Executor 기반 아키텍처를 위한 Executor/에이전트 등록"""
    logger.info("Registering executors to Registry...")

    # SearchExecutor 등록 (가상 에이전트로 등록)
    capabilities = AgentCapabilities(
        name="search_executor",
        description="법률, 부동산, 대출 정보를 검색하는 Executor",
        # ...
        executor="search"
    )

    class SearchExecutorPlaceholder:
        pass

    AgentRegistry.register(
        name="search_executor",
        agent_class=SearchExecutorPlaceholder,
        executor="search",
        # ...
    )
```

#### agent_registry.py 주요 변경

**고민 포인트**: `team` 파라미터를 `executor` 또는 `group`으로 변경할지 여부

**Option 1**: `team` → `executor`
```python
class AgentCapabilities:
    def __init__(
        self,
        name: str,
        executor: str = None  # ← 변경
    ):
        self.executor = executor
```

**Option 2**: `team` → `group` (더 일반적인 용어)
```python
class AgentCapabilities:
    def __init__(
        self,
        name: str,
        group: str = None  # ← 변경
    ):
        self.group = group
```

**권장**: Option 2 (`group`)
- 이유: Registry는 범용 시스템이므로 "executor"보다 "group"이 더 일반적
- "search", "document", "analysis" 등을 그룹으로 분류

---

## 5. 테스트 계획

### 5.1 단위 테스트 체크리스트

#### execution_supervisor.py 테스트
- [ ] `ExecutionSupervisor.__init__()` 정상 초기화
- [ ] `initialize_node()` State 필드 정상 초기화
- [ ] `planning_node()` active_executors 정상 생성
- [ ] `execute_executors_node()` 병렬 실행 정상 동작
- [ ] `execute_executors_node()` 순차 실행 정상 동작
- [ ] `_execute_single_executor()` 각 Executor 정상 호출

#### separated_states.py 테스트
- [ ] `SearchExecutorState` 필드 정상 생성
- [ ] `MainSupervisorState` executor 필드 정상 생성
- [ ] `StateManager.merge_executor_results()` 정상 병합

#### executor 파일 테스트
- [ ] `SearchExecutor` executor_name 정상 설정
- [ ] `SearchExecutorState` 반환 정상

### 5.2 통합 테스트 시나리오

#### 시나리오 1: 기본 워크플로우
```python
async def test_basic_workflow():
    supervisor = ExecutionSupervisor()

    result = await supervisor.process_query_streaming(
        query="전세금 5% 인상 가능한가요?",
        session_id="test_session"
    )

    assert result["status"] == "completed"
    assert "search" in result["active_executors"]
    assert "executor_results" in result
```

#### 시나리오 2: 병렬 실행
```python
async def test_parallel_execution():
    supervisor = ExecutionSupervisor()

    result = await supervisor.process_query_streaming(
        query="강남구 아파트 시세와 대출 한도 알려주세요",
        session_id="test_session"
    )

    assert len(result["active_executors"]) >= 2
    assert result["execution_plan"]["strategy"] == "parallel"
```

#### 시나리오 3: Checkpointing 정상 동작
```python
async def test_checkpointing():
    supervisor = ExecutionSupervisor(enable_checkpointing=True)

    # 첫 번째 실행
    result1 = await supervisor.process_query_streaming(
        query="전세 관련 법률",
        session_id="checkpoint_test",
        chat_session_id="session_123"
    )

    # Checkpoint 로드 확인
    # (LangGraph checkpointer를 통해 state가 PostgreSQL에 저장되었는지 확인)
    assert result1["status"] == "completed"
```

### 5.3 회귀 테스트

#### API Endpoint 테스트
- [ ] `/api/v1/agent/query` 정상 동작
- [ ] `/api/v1/agent/query/stream` WebSocket 정상 동작
- [ ] 기존 클라이언트 코드 영향 없음 확인

#### Database Schema 테스트
- [ ] Checkpointing 테이블 (`checkpoints`, `checkpoint_blobs`) 정상 저장
- [ ] State 직렬화/역직렬화 정상 동작

---

## 6. 위험 요소 및 완화 전략

### 6.1 위험 요소

| 위험 | 영향도 | 발생 확률 | 설명 |
|------|--------|-----------|------|
| State 필드명 변경 시 Checkpointing 충돌 | High | Medium | 기존 checkpoint에 `active_teams` 저장, 새 코드는 `active_executors` 읽기 시도 |
| Import 구문 누락 | Medium | Medium | 100+ 파일에서 import 구문 일괄 변경 시 누락 가능 |
| 테스트 코드 미업데이트 | Medium | High | 수많은 테스트에서 클래스명/필드명 사용 중 |
| API 클라이언트 영향 | Low | Low | 내부 리팩토링이므로 API 인터페이스는 변경 없음 |

### 6.2 완화 전략

#### 전략 1: Checkpointing 하위 호환성 유지
```python
# separated_states.py
class MainSupervisorState(TypedDict):
    # 새 필드명 (우선)
    active_executors: List[str]
    executor_results: Dict[str, Any]

    # 구 필드명 (하위 호환성, deprecated)
    active_teams: Optional[List[str]]  # DEPRECATED
    team_results: Optional[Dict[str, Any]]  # DEPRECATED

# execution_supervisor.py
async def initialize_node(self, state: MainSupervisorState):
    # 구 필드명이 있으면 마이그레이션
    if "active_teams" in state and not state.get("active_executors"):
        state["active_executors"] = state["active_teams"]
        logger.warning("Migrated 'active_teams' to 'active_executors'")

    if "team_results" in state and not state.get("executor_results"):
        state["executor_results"] = state["team_results"]
        logger.warning("Migrated 'team_results' to 'executor_results'")
```

#### 전략 2: 단계적 롤아웃
1. **Phase 1**: 하위 호환성 유지하며 새 필드명 추가
2. **Phase 2**: 새 필드명으로 로직 전환, 구 필드명은 읽기만
3. **Phase 3**: 구 필드명 완전 제거 (1개월 후)

#### 전략 3: 자동화된 검증
```bash
# import 구문 검증
grep -r "from.*team_supervisor import" backend/
grep -r "TeamBasedSupervisor" backend/

# State 필드명 검증
grep -r "active_teams" backend/
grep -r "team_results" backend/
```

---

## 7. 마이그레이션 체크리스트

### 7.1 코드 변경 체크리스트

#### 파일명 변경
- [ ] `team_supervisor.py` → `execution_supervisor.py`

#### 클래스명 변경
- [ ] `TeamBasedSupervisor` → `ExecutionSupervisor`
- [ ] `SearchTeamState` → `SearchExecutorState`
- [ ] `DocumentTeamState` → `DocumentExecutorState`
- [ ] `AnalysisTeamState` → `AnalysisExecutorState`

#### 변수명 변경 (execution_supervisor.py)
- [ ] `self.teams` → `self.executors`
- [ ] `active_teams` → `active_executors`
- [ ] `completed_teams` → `completed_executors`
- [ ] `failed_teams` → `failed_executors`
- [ ] `team_results` → `executor_results`

#### 메서드명 변경 (execution_supervisor.py)
- [ ] `execute_teams_node` → `execute_executors_node`
- [ ] `_get_team_for_agent` → `_get_executor_for_agent`
- [ ] `_execute_teams_parallel` → `_execute_executors_parallel`
- [ ] `_execute_teams_sequential` → `_execute_executors_sequential`
- [ ] `_execute_single_team` → `_execute_single_executor`
- [ ] `_find_step_id_for_team` → `_find_step_id_for_executor`
- [ ] `_extract_team_data` → `_extract_executor_data`

#### StateManager 메서드 변경 (separated_states.py)
- [ ] `merge_team_results` → `merge_executor_results`
- [ ] `create_team_state` → `create_executor_state`

#### Executor 파일 변경
- [ ] `search_executor.py`: `team_name` → `executor_name`
- [ ] `document_executor.py`: `team_name` → `executor_name`
- [ ] `analysis_executor.py`: `team_name` → `executor_name`

#### agent_adapter.py 변경
- [ ] `"search_team"` → `"search_executor"`
- [ ] `"analysis_team"` → `"analysis_executor"`
- [ ] `"document_team"` → `"document_executor"`
- [ ] `SearchTeamPlaceholder` → `SearchExecutorPlaceholder`
- [ ] `team="search"` → `executor="search"` (또는 `group="search"`)

#### 주석 및 로그 메시지 변경
- [ ] `"팀 기반 Supervisor"` → `"Executor 조율 Supervisor"`
- [ ] `"SearchTeam"` → `"SearchExecutor"` (로그 메시지)
- [ ] `"Team-based workflow"` → `"Executor-based workflow"`

### 7.2 테스트 체크리스트

#### 단위 테스트
- [ ] execution_supervisor.py 테스트 통과
- [ ] separated_states.py 테스트 통과
- [ ] search_executor.py 테스트 통과
- [ ] document_executor.py 테스트 통과
- [ ] analysis_executor.py 테스트 통과

#### 통합 테스트
- [ ] 기본 워크플로우 테스트
- [ ] 병렬 실행 테스트
- [ ] 순차 실행 테스트
- [ ] Checkpointing 테스트
- [ ] WebSocket 실시간 통신 테스트

#### 회귀 테스트
- [ ] 기존 API endpoint 정상 동작
- [ ] 기존 클라이언트 코드 영향 없음
- [ ] Database schema 호환성 확인

### 7.3 배포 체크리스트

- [ ] Git branch 생성 (`refactor/team-to-executor-naming`)
- [ ] 변경 사항 커밋 및 Push
- [ ] Pull Request 생성 및 코드 리뷰
- [ ] 테스트 환경 배포 및 검증
- [ ] 프로덕션 배포
- [ ] 모니터링 (에러 로그, 성능 지표)

---

## 8. 결론

### 8.1 핵심 요약

1. **문제**: "team"과 "agent" 용어가 혼용되어 코드 가독성 저하
2. **원인**: 초기 설계 변경 과정에서 일부 네이밍만 수정
3. **해결**: "team" → "executor" 용어 통일 (Executor 패턴)
4. **영향**: 약 100+ 위치 변경 필요 (파일명, 클래스명, 변수명, 메서드명)
5. **기간**: 약 8일 (준비 1일 + 변경 5일 + 테스트 2일)

### 8.2 기대 효과

#### 가독성 향상
- 개발자가 코드 읽을 때 "이게 Team인가 Agent인가?" 혼란 제거
- 일관된 네이밍으로 시스템 이해 시간 50% 단축

#### 유지보수성 향상
- 새로운 Executor 추가 시 네이밍 가이드 명확
- 리팩토링 시 검색 키워드 명확 (`executor` 하나로 통일)

#### 확장성 향상
- 향후 새로운 Executor 추가 시 아키텍처 일관성 유지
- Executor 간 의존성 관리 명확

### 8.3 다음 단계

1. **Phase 1 실행**: 파일명 및 클래스명 변경 (우선순위 High)
2. **Phase 2 실행**: 변수명 및 메서드명 통일 (우선순위 Medium)
3. **Phase 3 실행**: 주석 및 로그 메시지 정리 (우선순위 Low)
4. **문서 업데이트**: 아키텍처 문서, API 문서 최신화
5. **팀 공유**: 변경 사항 공유 및 네이밍 가이드 정립

---

## Appendix A: 영향받는 파일 목록

### 직접 변경 필요 파일 (High Priority)

1. `backend/app/service_agent/supervisor/team_supervisor.py` → `execution_supervisor.py`
2. `backend/app/service_agent/foundation/separated_states.py`
3. `backend/app/service_agent/execution_agents/search_executor.py`
4. `backend/app/service_agent/execution_agents/document_executor.py`
5. `backend/app/service_agent/execution_agents/analysis_executor.py`
6. `backend/app/service_agent/foundation/agent_adapter.py`

### import 구문 변경 필요 파일 (Medium Priority)

7. `backend/app/api/endpoints/agent_endpoints.py` (API 엔드포인트)
8. `backend/app/service_agent/cognitive_agents/planning_agent.py`
9. `backend/app/service_agent/cognitive_agents/execution_orchestrator.py`
10. `backend/app/service_agent/cognitive_agents/query_decomposer.py`

### 테스트 파일 (Medium Priority)

11. `backend/tests/test_team_supervisor.py` → `test_execution_supervisor.py`
12. `backend/tests/test_search_executor.py`
13. `backend/tests/test_separated_states.py`

### 문서 파일 (Low Priority)

14. `reports/Manual/SYSTEM_FLOW_DIAGRAM.md`
15. `reports/Manual/STATE_MANAGEMENT_GUIDE.md`
16. `reports/Manual/DATABASE_GUIDE.md`

---

## Appendix B: 검색 및 교체 스크립트

### B.1 파일명 검색
```bash
# team_supervisor.py를 포함하는 파일 찾기
find backend/ -name "*team_supervisor*"
```

### B.2 클래스명 검색
```bash
# TeamBasedSupervisor 사용 위치 찾기
grep -rn "TeamBasedSupervisor" backend/

# SearchTeamState 사용 위치 찾기
grep -rn "SearchTeamState" backend/
```

### B.3 변수명 검색
```bash
# active_teams 사용 위치 찾기
grep -rn "active_teams" backend/

# team_results 사용 위치 찾기
grep -rn "team_results" backend/
```

### B.4 일괄 교체 스크립트 (주의: 백업 후 실행)
```bash
#!/bin/bash
# 주의: 반드시 Git 백업 후 실행!

# 1. 클래스명 교체
find backend/ -type f -name "*.py" -exec sed -i 's/TeamBasedSupervisor/ExecutionSupervisor/g' {} +

# 2. State 클래스명 교체
find backend/ -type f -name "*.py" -exec sed -i 's/SearchTeamState/SearchExecutorState/g' {} +
find backend/ -type f -name "*.py" -exec sed -i 's/DocumentTeamState/DocumentExecutorState/g' {} +
find backend/ -type f -name "*.py" -exec sed -i 's/AnalysisTeamState/AnalysisExecutorState/g' {} +

# 3. 변수명 교체 (정규식 사용 - 더 정교한 패턴 매칭)
find backend/ -type f -name "*.py" -exec sed -i 's/\bactive_teams\b/active_executors/g' {} +
find backend/ -type f -name "*.py" -exec sed -i 's/\bteam_results\b/executor_results/g' {} +

# 검증
echo "변경 사항 확인:"
git diff --stat
```

---

**보고서 작성**: 2025-10-21
**작성자**: Claude (AI Assistant)
**버전**: 1.0
**다음 리뷰 예정일**: 리팩토링 완료 후
