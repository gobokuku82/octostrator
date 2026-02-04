"""States - LangGraph 상태 정의

이 패키지는 LangGraph 상태 관련 코드를 포함합니다:
- base.py: AgentState (TypedDict)
- reducers.py: LangGraph Reducers
- accessors.py: State Accessor 함수들

Pydantic 모델은 models/ 패키지로 이동되었으며,
하위 호환성을 위해 여기서 re-export됩니다.

권장 import:
    # 새로운 방식 (권장)
    from backend.app.dream_agent.models import TodoItem, Plan

    # 기존 방식 (하위 호환성 유지, 점진적 deprecated 예정)
    from backend.app.dream_agent.states import TodoItem, Plan
"""

# =============================================================================
# Re-export from models/ (하위 호환성)
# =============================================================================

# Todo Models (from models/)
from ..models.todo import (
    TodoItem,
    TodoMetadata,
    TodoExecutionConfig,
    TodoDataConfig,
    TodoDependencyConfig,
    TodoProgress,
    TodoApproval,
)

# Plan Models (from models/)
from ..models.plan import (
    Plan,
    PlanVersion,
    PlanChange,
    create_plan,
    create_plan_change,
    create_plan_version,
)

# Resource Models (from models/)
from ..models.resource import (
    AgentResource,
    ResourceAllocation,
    ResourceConstraints,
    ResourcePlan,
    create_agent_resource,
    create_resource_allocation,
    create_resource_constraints,
)

# Execution Graph Models (from models/)
from ..models.execution_graph import (
    ExecutionNode,
    ExecutionGroup,
    ExecutionGraph,
    create_execution_node,
    create_execution_group,
    create_execution_graph,
)

# Results (from models/)
from ..models.results import IntentResult, PlanResult, MLResult, BizResult, FinalResponse

# =============================================================================
# LangGraph State (states/ 고유)
# =============================================================================

# Base State
from .base import AgentState, create_initial_state

# Reducers
from .reducers import todo_reducer, ml_result_reducer, biz_result_reducer

# State Accessors
from .accessors import (
    # 기본 Accessors
    get_todos,
    get_user_input,
    get_intent,
    get_current_context,
    get_session_id,
    get_language,
    get_requires_hitl,
    # ML Accessors
    get_current_ml_todo_id,
    get_intermediate_results,
    get_ml_result,
    get_next_ml_tool,
    # Biz Accessors
    get_current_biz_todo_id,
    get_biz_result,
    get_storyboard,
    get_validation_result,
    get_resolution,
    get_fps,
    get_scene_prompts,
    get_comfyui_result,
    get_insights,
    get_report_structure,
    get_output_format,
    get_error,
    # 기타 Accessors
    get_plan,
    get_dialogue_context,
    # 추가 Accessors
    get_next_layer,
    get_plan_obj,
    get_workflow,
    get_use_mock,
    get_response,
    get_target_context,
    # Convenience Functions
    get_completed_todo_count,
    get_pending_todo_count,
    get_todos_by_layer,
    get_todo_by_id,
)

__all__ = [
    # =============================================================================
    # Re-exported from models/ (하위 호환성)
    # =============================================================================
    # Todo Models
    "TodoItem",
    "TodoMetadata",
    "TodoExecutionConfig",
    "TodoDataConfig",
    "TodoDependencyConfig",
    "TodoProgress",
    "TodoApproval",
    # Plan Models
    "Plan",
    "PlanVersion",
    "PlanChange",
    # Plan Helpers
    "create_plan",
    "create_plan_change",
    "create_plan_version",
    # Resource Models
    "AgentResource",
    "ResourceAllocation",
    "ResourceConstraints",
    "ResourcePlan",
    # Resource Helpers
    "create_agent_resource",
    "create_resource_allocation",
    "create_resource_constraints",
    # Execution Graph Models
    "ExecutionNode",
    "ExecutionGroup",
    "ExecutionGraph",
    # Execution Graph Helpers
    "create_execution_node",
    "create_execution_group",
    "create_execution_graph",
    # Results
    "IntentResult",
    "PlanResult",
    "MLResult",
    "BizResult",
    "FinalResponse",
    # =============================================================================
    # LangGraph State (states/ 고유)
    # =============================================================================
    # Base State
    "AgentState",
    "create_initial_state",
    # Reducers
    "todo_reducer",
    "ml_result_reducer",
    "biz_result_reducer",
    # State Accessors
    "get_todos",
    "get_user_input",
    "get_intent",
    "get_current_context",
    "get_session_id",
    "get_language",
    "get_requires_hitl",
    "get_current_ml_todo_id",
    "get_intermediate_results",
    "get_ml_result",
    "get_next_ml_tool",
    "get_current_biz_todo_id",
    "get_biz_result",
    "get_storyboard",
    "get_validation_result",
    "get_resolution",
    "get_fps",
    "get_scene_prompts",
    "get_comfyui_result",
    "get_insights",
    "get_report_structure",
    "get_output_format",
    "get_error",
    "get_plan",
    "get_dialogue_context",
    "get_next_layer",
    "get_plan_obj",
    "get_workflow",
    "get_use_mock",
    "get_response",
    "get_target_context",
    "get_completed_todo_count",
    "get_pending_todo_count",
    "get_todos_by_layer",
    "get_todo_by_id",
]
