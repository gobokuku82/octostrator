"""HITL Manager - Human-in-the-Loop 상호작용"""

from .replan_manager import ReplanManager, ReplanResult, replan_manager
from .decision_manager import DecisionManager, DecisionRequest, decision_manager
from .pause_controller import (
    PauseController,
    PauseReason,
    HITLMode,
    get_pause_controller,
    remove_pause_controller,
    get_all_paused_sessions,
)
from .plan_editor import (
    PlanEditor,
    PlanEdit,
    EditOperation,
    EditResult,
    get_plan_editor,
    remove_plan_editor,
)
from .nl_plan_modifier import (
    NLPlanModifier,
    ModificationDecision,
    ModificationAnalysis,
    ModificationResult,
    get_nl_plan_modifier,
    remove_nl_plan_modifier,
)
from .input_requester import (
    InputRequester,
    InputRequest,
    InputResponse,
    InputType,
    RequestStatus,
    get_input_requester,
    remove_input_requester,
    get_all_pending_requests,
)

__all__ = [
    # Replan
    "ReplanManager",
    "ReplanResult",
    "replan_manager",
    # Decision
    "DecisionManager",
    "DecisionRequest",
    "decision_manager",
    # Pause Controller (Phase 2)
    "PauseController",
    "PauseReason",
    "HITLMode",
    "get_pause_controller",
    "remove_pause_controller",
    "get_all_paused_sessions",
    # Plan Editor (Phase 2)
    "PlanEditor",
    "PlanEdit",
    "EditOperation",
    "EditResult",
    "get_plan_editor",
    "remove_plan_editor",
    # NL Plan Modifier (Phase 2)
    "NLPlanModifier",
    "ModificationDecision",
    "ModificationAnalysis",
    "ModificationResult",
    "get_nl_plan_modifier",
    "remove_nl_plan_modifier",
    # Input Requester (Phase 2)
    "InputRequester",
    "InputRequest",
    "InputResponse",
    "InputType",
    "RequestStatus",
    "get_input_requester",
    "remove_input_requester",
    "get_all_pending_requests",
]
