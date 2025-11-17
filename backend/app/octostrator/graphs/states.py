"""Graph state definitions for Octostrator"""

from typing import TypedDict, List, Optional, Dict, Any, Annotated, Literal
from langchain_core.messages import BaseMessage, add_messages
from datetime import datetime
from uuid import UUID

from backend.schema.todo import TodoItem, TodoStatus, TodoPriority


class IntentInfo(TypedDict):
    """의도 정보"""
    primary: str
    secondary: Optional[str]
    confidence: float
    entities: Dict[str, Any]
    requires_context: bool
    suggested_action: str


class BaseGraphState(TypedDict):
    """기본 그래프 상태"""
    # Message history
    messages: Annotated[List[BaseMessage], add_messages]

    # Session info
    session_id: str
    thread_id: str
    user_id: Optional[str]

    # Error handling
    error: Optional[str]

    # Metadata
    created_at: datetime
    updated_at: datetime


class SupervisorState(BaseGraphState):
    """Supervisor 그래프 상태"""
    # Intent management
    detected_intent: Optional[IntentInfo]
    previous_intent: Optional[str]
    intent_history: List[str]
    intent_confidence: float

    # Task management
    pending_tasks: List[Dict[str, Any]]
    completed_tasks: List[Dict[str, Any]]

    # Subgraph management
    target_subgraph: Optional[str]
    subgraph_input: Optional[Dict[str, Any]]
    parent_state: Optional[Dict[str, Any]]

    # Routing
    next_node: Optional[str]


class TodoState(BaseGraphState):
    """TODO 그래프 상태"""
    # User input
    user_query: str

    # TODO management
    todos: List[TodoItem]
    current_todo: Optional[TodoItem]
    todo_dependencies: Dict[str, List[str]]  # todo_id -> [dependency_ids]

    # Validation
    validation_passed: bool
    validation_errors: List[str]

    # User interaction
    requires_confirmation: bool
    user_feedback: Optional[str]


class ExecutionState(BaseGraphState):
    """실행 그래프 상태"""
    # Tasks
    scheduled_tasks: List[Dict[str, Any]]
    active_executions: List[Dict[str, Any]]
    execution_results: Dict[str, Any]

    # Agent management
    assigned_agents: Dict[str, str]  # task_id -> agent_id
    agent_statuses: Dict[str, str]  # agent_id -> status

    # Performance
    execution_metrics: Dict[str, float]


class ConversationState(BaseGraphState):
    """대화 그래프 상태"""
    # Multi-turn context
    conversation_turns: int
    conversation_mode: Literal["new", "continuation", "clarification", "modification"]
    conversation_context: Dict[str, Any]

    # Context switches
    context_switches: int
    requires_clarification: bool
    clarification_attempts: int

    # Active context
    active_task_context: Optional[Dict[str, Any]]
    suspended_tasks: List[Dict[str, Any]]


class HITLState(BaseGraphState):
    """Human-in-the-Loop 그래프 상태"""
    # Interrupt info
    interrupt_type: Optional[str]
    interrupt_reason: Optional[str]
    interrupt_data: Optional[Dict[str, Any]]

    # User interaction
    awaiting_user_input: bool
    user_response: Optional[Dict[str, Any]]

    # Resume info
    resume_from: Optional[str]
    resume_data: Optional[Dict[str, Any]]


class MainGraphState(
    SupervisorState,
    TodoState,
    ExecutionState,
    ConversationState,
    HITLState
):
    """통합 메인 그래프 상태 (모든 상태 포함)"""
    pass


# Type aliases for convenience
GraphState = MainGraphState  # Main alias