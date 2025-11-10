# API Reference

**작성일**: 2025-11-05
**버전**: 2.0
**시스템**: AI PT Manager API

---

## 목차

1. [Main Orchestrator API](#1-main-orchestrator-api)
2. [Cognitive Supervisor API](#2-cognitive-supervisor-api)
3. [TodoAgent API](#3-todoagent-api)
4. [Execute Supervisor API](#4-execute-supervisor-api)
5. [Agent Registry API](#5-agent-registry-api)
6. [BaseAgent API](#6-baseagent-api)
7. [Capability Router API](#7-capability-router-api)
8. [WebSocket API](#8-websocket-api)

---

## 1. Main Orchestrator API

### 1.1 MainOrchestrator Class

```python
from backend.app.octostrator.main_orchestrator import MainOrchestrator
```

#### Constructor

```python
MainOrchestrator(
    llm=None,
    checkpointer: Optional[AsyncPostgresSaver] = None,
    memory_manager=None,
    auto_approve_todos: bool = False
)
```

**Parameters:**
- `llm`: Language Model 인스턴스
- `checkpointer`: PostgreSQL checkpoint 저장소
- `memory_manager`: 메모리 관리자
- `auto_approve_todos`: TODO 자동 승인 여부

#### Methods

##### process_request()

```python
async def process_request(
    user_message: str,
    session_id: str,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**사용자 요청 처리**

**Parameters:**
- `user_message`: 사용자 입력 메시지
- `session_id`: 세션 식별자
- `user_id`: 사용자 식별자 (선택)
- `context`: 추가 컨텍스트 정보

**Returns:**
```python
{
    "success": bool,
    "session_id": str,
    "plan_goal": str,
    "total_todos": int,
    "completed": int,
    "failed": int,
    "skipped": int,
    "success_rate": float,
    "results": Dict[str, Any],
    "execution_time": str,
    "timestamp": str
}
```

**Example:**
```python
orchestrator = MainOrchestrator()
result = await orchestrator.process_request(
    user_message="다이어트 계획 만들어줘",
    session_id="session_123",
    user_id="user_456",
    context={"age": 30, "weight": 70}
)
```

##### handle_human_feedback()

```python
async def handle_human_feedback(
    session_id: str,
    feedback: Dict[str, Any]
) -> Dict[str, Any]
```

**Human feedback 처리**

**Parameters:**
- `session_id`: 세션 식별자
- `feedback`: 사용자 피드백

**Feedback Structure:**
```python
{
    "action": "modified",  # "approved" | "modified" | "rejected"
    "modifications": [
        {
            "todo_id": str,
            "changes": Dict[str, Any]
        }
    ]
}
```

##### get_agent_status()

```python
async def get_agent_status() -> Dict[str, Any]
```

**시스템 상태 조회**

**Returns:**
```python
{
    "stats": {
        "total_registered": int,
        "instantiated": int,
        "with_checkpoint": int
    },
    "agents": [
        {
            "id": str,
            "name": str,
            "status": str,
            "checkpoint": bool
        }
    ],
    "timestamp": str
}
```

### 1.2 Factory Functions

#### create_orchestrator()

```python
async def create_orchestrator(
    db_url: Optional[str] = None,
    llm_model: str = "gpt-4o-mini",
    auto_approve: bool = False
) -> MainOrchestrator
```

**Orchestrator 생성 팩토리**

**Example:**
```python
orchestrator = await create_orchestrator(
    db_url="postgresql://user:pass@localhost/db",
    llm_model="gpt-4o-mini",
    auto_approve=False
)
```

---

## 2. Cognitive Supervisor API

### 2.1 CognitiveSupervisor Class

```python
from backend.app.octostrator.supervisor.cognitive_supervisor import CognitiveSupervisor
```

#### Constructor

```python
CognitiveSupervisor(
    llm=None,
    checkpointer: Optional[AsyncPostgresSaver] = None,
    memory_manager=None
)
```

#### Methods

##### plan()

```python
async def plan(
    user_message: str,
    session_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**실행 계획 생성**

**Returns:**
```python
{
    "goal": str,
    "priority": "high" | "normal" | "low",
    "steps": [
        {
            "step_id": str,
            "action": str,
            "agent": str,
            "capability": str,
            "params": Dict,
            "dependencies": List[str],
            "estimated_time": str
        }
    ],
    "expected_outcome": str
}
```

### 2.2 IntentClassifier

```python
from backend.app.octostrator.supervisor.cognitive_supervisor import IntentClassifier
```

#### classify()

```python
@classmethod
def classify(cls, user_message: str) -> str
```

**사용자 의도 분류**

**Intent Types:**
- `CREATE_DIET_PLAN`
- `CREATE_WORKOUT_PLAN`
- `SCHEDULE_MANAGEMENT`
- `HEALTH_ANALYSIS`
- `PROGRESS_TRACKING`
- `GENERAL_CONSULTATION`
- `GENERAL_REQUEST`

---

## 3. TodoAgent API

### 3.1 TodoAgent Class

```python
from backend.app.octostrator.agents.todo.todo_agent import TodoAgent
```

#### Constructor

```python
TodoAgent()
```

자동으로 다음 설정으로 초기화:
- `agent_id`: "todo_agent"
- `enable_checkpoint`: True
- `capabilities`: TODO_MANAGEMENT, TASK_PRIORITIZATION, etc.

#### State Definition

```python
class TodoAgentState(BaseAgentState):
    plan: Optional[Dict[str, Any]]
    todos: List[Dict[str, Any]]
    human_feedback: Optional[Dict[str, Any]]
    requires_approval: bool
    approval_status: Optional[str]
    modifications: List[Dict[str, Any]]
    execution_plan: Optional[Dict[str, Any]]
```

#### TodoItem Structure

```python
{
    "id": str,
    "agent": str,
    "task": str,
    "capability": str,
    "params": Dict[str, Any],
    "dependencies": List[str],
    "priority": str,
    "estimated_time": str,
    "description": str,
    "status": "pending",
    "created_at": str
}
```

---

## 4. Execute Supervisor API

### 4.1 ExecuteSupervisor Class

```python
from backend.app.octostrator.supervisor.execute_supervisor import ExecuteSupervisor
```

#### Constructor

```python
ExecuteSupervisor(
    checkpointer: Optional[AsyncPostgresSaver] = None,
    agent_executor=None
)
```

#### Methods

##### execute()

```python
async def execute(
    todos: List[Dict[str, Any]],
    session_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**TODO 리스트 실행**

**Returns:**
```python
{
    "session_id": str,
    "total_todos": int,
    "completed": int,
    "failed": int,
    "skipped": int,
    "success_rate": float,
    "results": Dict[str, Dict[str, Any]],
    "execution_time": str
}
```

### 4.2 AgentExecutor

```python
from backend.app.octostrator.supervisor.execute_supervisor import AgentExecutor
```

#### execute_single_agent()

```python
async def execute_single_agent(
    todo: TodoItem,
    context: Dict[str, Any],
    dependencies_results: Dict[str, Any] = None
) -> Dict[str, Any]
```

**단일 Agent 실행**

#### execute_parallel_group()

```python
async def execute_parallel_group(
    todos: List[TodoItem],
    context: Dict[str, Any],
    dependencies_results: Dict[str, Any] = None
) -> Dict[str, Dict[str, Any]]
```

**병렬 Agent 그룹 실행**

---

## 5. Agent Registry API

### 5.1 AgentRegistry Class

```python
from backend.app.octostrator.agents.base.agent_registry import agent_registry
```

싱글톤 인스턴스: `agent_registry`

#### Methods

##### register()

```python
def register(
    agent_class: Type[BaseAgent],
    agent_id: Optional[str] = None,
    override: bool = False
) -> bool
```

**Agent 클래스 등록**

**Example:**
```python
agent_registry.register(DietAgent, "diet_agent")
```

##### discover_agents()

```python
def discover_agents(path: str = "backend/app/octostrator/agents") -> int
```

**Agent 자동 검색 및 등록**

**Returns:** 발견된 Agent 수

##### create_agent()

```python
def create_agent(
    agent_id: str,
    agent_name: Optional[str] = None,
    **kwargs
) -> Optional[BaseAgent]
```

**Agent 인스턴스 생성**

##### get_agent_instance()

```python
def get_agent_instance(agent_id: str) -> Optional[BaseAgent]
```

**캐시된 Agent 인스턴스 반환**

##### list_agents()

```python
def list_agents(filter_by: Optional[Dict[str, Any]] = None) -> List[str]
```

**등록된 Agent 목록 조회**

**Example:**
```python
# 모든 Agent
all_agents = agent_registry.list_agents()

# Checkpoint 사용 Agent만
checkpoint_agents = agent_registry.list_agents(
    filter_by={"enable_checkpoint": True}
)
```

##### get_stats()

```python
def get_stats() -> Dict[str, Any]
```

**Registry 통계 정보**

### 5.2 Decorator

```python
from backend.app.octostrator.agents.base.agent_registry import register_agent

@register_agent("my_agent")
class MyAgent(BaseAgent):
    pass
```

---

## 6. BaseAgent API

### 6.1 BaseAgent Class

```python
from backend.app.octostrator.agents.base.base_agent import BaseAgent
```

#### Constructor

```python
BaseAgent(
    agent_id: str,
    agent_name: str,
    description: str = "",
    enable_checkpoint: bool = False,
    priority: AgentPriority = AgentPriority.NORMAL,
    dependencies: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
)
```

#### Abstract Methods (Must Implement)

##### build_graph()

```python
@abstractmethod
def build_graph(self, llm=None) -> StateGraph
```

**LangGraph workflow 구축**

##### process_task()

```python
@abstractmethod
async def process_task(
    self,
    task: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]
```

**작업 처리 로직**

#### Public Methods

##### initialize()

```python
async def initialize(
    llm=None,
    checkpointer: Optional[AsyncPostgresSaver] = None
)
```

**Agent 초기화 및 그래프 컴파일**

##### execute()

```python
async def execute(
    task: Dict[str, Any],
    context: Dict[str, Any],
    thread_id: Optional[str] = None
) -> Dict[str, Any]
```

**Agent 실행**

**Returns:**
```python
{
    "agent_id": str,
    "agent_name": str,
    "status": "completed" | "failed",
    "started_at": str,
    "completed_at": str,
    "result": Dict[str, Any] | None,
    "error": str | None
}
```

##### get_info()

```python
def get_info() -> Dict[str, Any]
```

**Agent 정보 반환**

##### validate_dependencies()

```python
def validate_dependencies(completed_agents: List[str]) -> bool
```

**의존성 검증**

### 6.2 Enums

#### AgentStatus

```python
from backend.app.octostrator.agents.base.base_agent import AgentStatus

AgentStatus.IDLE
AgentStatus.RUNNING
AgentStatus.COMPLETED
AgentStatus.FAILED
AgentStatus.PAUSED
AgentStatus.WAITING_DEPENDENCY
```

#### AgentPriority

```python
from backend.app.octostrator.agents.base.base_agent import AgentPriority

AgentPriority.CRITICAL  # 1
AgentPriority.HIGH      # 2
AgentPriority.NORMAL    # 3
AgentPriority.LOW       # 4
```

---

## 7. Capability Router API

### 7.1 CapabilityBasedRouter

```python
from backend.app.octostrator.agents.base.capabilities import CapabilityBasedRouter
```

#### Constructor

```python
CapabilityBasedRouter(registry)
```

#### Methods

##### find_agents_for_capability()

```python
def find_agents_for_capability(capability: str) -> List[str]
```

**특정 능력을 가진 Agent 찾기**

##### find_best_agent()

```python
def find_best_agent(
    required_capability: str,
    context: Optional[Dict[str, Any]] = None
) -> Optional[str]
```

**최적 Agent 선택**

**Context Options:**
```python
{
    "preferred_agent": str,      # 선호 Agent
    "success_history": Dict,     # 성공 이력
}
```

##### find_alternative_agents()

```python
def find_alternative_agents(
    primary_agent: str,
    capability: str
) -> List[str]
```

**대체 가능 Agent 목록**

### 7.2 Capability Enum

```python
from backend.app.octostrator.agents.base.capabilities import Capability

# Health & Fitness
Capability.MEAL_PLANNING
Capability.NUTRITION_ANALYSIS
Capability.EXERCISE_PLANNING
Capability.HEALTH_TRACKING

# Schedule & Time
Capability.SCHEDULING
Capability.CALENDAR_MANAGEMENT

# TODO & Task
Capability.TODO_MANAGEMENT
Capability.TASK_MANAGEMENT

# Analysis & Reporting
Capability.DATA_ANALYSIS
Capability.REPORT_GENERATION

# Communication
Capability.NOTIFICATION
Capability.EMAIL

# Coaching
Capability.COACHING
Capability.MOTIVATION

# Custom
Capability.CUSTOM
```

---

## 8. WebSocket API

### 8.1 WebSocket Events

#### Client → Server

##### todo_approval

```json
{
    "type": "todo_approval",
    "session_id": "session_123",
    "action": "approved" | "modified" | "rejected",
    "modifications": [
        {
            "todo_id": "todo_001",
            "changes": {}
        }
    ]
}
```

##### request_status

```json
{
    "type": "request_status",
    "session_id": "session_123"
}
```

#### Server → Client

##### todo_approval_request

```json
{
    "type": "todo_approval_request",
    "session_id": "session_123",
    "todos": [...],
    "plan_goal": "다이어트 계획",
    "total_todos": 5,
    "estimated_time": "10 minutes",
    "request_time": "2025-11-05T10:00:00"
}
```

##### progress_update

```json
{
    "type": "progress_update",
    "data": {
        "total_todos": 5,
        "completed": 3,
        "current": "todo_004",
        "percentage": 60.0
    }
}
```

##### execution_complete

```json
{
    "type": "execution_complete",
    "success": true,
    "completed": 4,
    "failed": 1,
    "success_rate": 80.0,
    "results": {}
}
```

### 8.2 WebSocket Handler

```python
def set_websocket_handler(handler):
    """웹소켓 핸들러 설정"""
    orchestrator.set_websocket_handler(handler)
```

**Handler Interface:**
```python
class WebSocketHandler:
    async def send_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ):
        pass

    async def receive_message(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        pass
```

---

## Usage Examples

### Complete Flow Example

```python
import asyncio
from backend.app.octostrator.main_orchestrator import create_orchestrator

async def main():
    # 1. Orchestrator 생성
    orchestrator = await create_orchestrator(
        db_url="postgresql://localhost/ptmanager",
        auto_approve=False
    )

    # 2. 요청 처리
    result = await orchestrator.process_request(
        user_message="다이어트와 운동 계획을 만들어주세요",
        session_id="session_123",
        user_id="user_456",
        context={
            "age": 30,
            "weight": 70,
            "height": 175,
            "goal": "lose_weight"
        }
    )

    # 3. 결과 확인
    print(f"Success: {result['success']}")
    print(f"Completed: {result['completed']}/{result['total_todos']}")
    print(f"Success Rate: {result['success_rate']}%")

    # 4. Human feedback 처리 (HITL)
    feedback_result = await orchestrator.handle_human_feedback(
        session_id="session_123",
        feedback={
            "action": "modified",
            "modifications": [
                {
                    "todo_id": "todo_001",
                    "changes": {"params": {"calories": 1800}}
                }
            ]
        }
    )

    # 5. 시스템 상태 확인
    status = await orchestrator.get_agent_status()
    print(f"Total Agents: {status['stats']['total_registered']}")

asyncio.run(main())
```

### Direct Agent Usage

```python
from backend.app.octostrator.agents.base.agent_registry import agent_registry

# Agent 등록
agent_registry.discover_agents()

# Agent 생성
diet_agent = agent_registry.create_agent("diet_agent")
await diet_agent.initialize()

# 직접 실행
result = await diet_agent.execute(
    task={
        "type": "create_meal_plan",
        "params": {"calories": 2000}
    },
    context={"session_id": "test_123"}
)
```

---

**작성 완료일**: 2025-11-05
**다음 문서**: [Migration Guide](./MIGRATION_GUIDE_251105.md)