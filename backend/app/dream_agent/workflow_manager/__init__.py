"""Workflow Manager - 5개 Manager 통합 관리

필요한 Managers:
- Todo Manager: Todo 생성, 검증, 의존성 관리
- HITL Manager: Human-in-the-Loop 상호작용
- Feedback Manager: 사용자 피드백 수집 및 학습
- Todo Failure Recovery: LLM 에러 복구 폴백 (Phase 3.5)
- Memory Manager: 세션 상태 및 히스토리 관리 (Phase 4)
"""

# Base Manager (P0-4.1)
from .base_manager import (
    ManagerStatus,
    ManagerHealth,
    BaseManager,
    AsyncBaseManager,
    StatefulManager,
    require_manager_ready,
    get_manager_status_summary,
)

# Manager Registry (P0-4.2)
from .manager_registry import (
    RegistryStatus,
    RegistryHealth,
    ManagerRegistry,
    manager_registry,
    get_manager_registry,
    get_manager,
    require_manager,
)

# Todo Manager
from .todo_manager import (
    TodoDependencyManager,
    todo_dependency_manager,
    TodoValidator,
)

# HITL Manager
from .hitl_manager import (
    ReplanManager,
    ReplanResult,
    replan_manager,
    DecisionManager,
    DecisionRequest,
    decision_manager,
)

# Feedback Manager (Phase 3 강화)
# TODO: DB 설정 후 활성화 - sLLM 학습 데이터 수집용
# from .feedback_manager import (
#     FeedbackManager,
#     feedback_manager,
#     # Phase 3 추가
#     QueryLogger,
#     get_query_logger,
#     PlanEditLogger,
#     get_plan_edit_logger,
#     ResultEvaluator,
#     get_result_evaluator,
#     LightweightFeedbackManager,
#     get_lightweight_feedback_manager,
# )
FeedbackManager = None
feedback_manager = None
QueryLogger = None
get_query_logger = None
PlanEditLogger = None
get_plan_edit_logger = None
ResultEvaluator = None
get_result_evaluator = None
LightweightFeedbackManager = None
get_lightweight_feedback_manager = None

# Todo Failure Recovery (Phase 3.5)
from .todo_failure_recovery import (
    TodoFailureRecovery,
    RecoveryStrategy,
    RecoveryResult,
    get_failure_recovery,
    reset_failure_recovery,
)

# Planning Manager (Phase 2)
from .planning_manager import (
    PlanManager,
    plan_manager,
    get_plan_manager,
    ResourcePlanner,
    resource_planner,
    get_resource_planner,
    ExecutionGraphBuilder,
    execution_graph_builder,
    get_execution_graph_builder,
)

# Memory Manager (Phase 4 - placeholder)
# from .memory_manager import MemoryManager, memory_manager

__all__ = [
    # Base Manager (P0-4.1)
    "ManagerStatus",
    "ManagerHealth",
    "BaseManager",
    "AsyncBaseManager",
    "StatefulManager",
    "require_manager_ready",
    "get_manager_status_summary",

    # Manager Registry (P0-4.2)
    "RegistryStatus",
    "RegistryHealth",
    "ManagerRegistry",
    "manager_registry",
    "get_manager_registry",
    "get_manager",
    "require_manager",

    # Todo Manager
    "TodoDependencyManager",
    "todo_dependency_manager",
    "TodoValidator",

    # HITL Manager
    "ReplanManager",
    "ReplanResult",
    "replan_manager",
    "DecisionManager",
    "DecisionRequest",
    "decision_manager",

    # Feedback Manager
    "FeedbackManager",
    "feedback_manager",
    # Phase 3 추가
    "QueryLogger",
    "get_query_logger",
    "PlanEditLogger",
    "get_plan_edit_logger",
    "ResultEvaluator",
    "get_result_evaluator",
    "LightweightFeedbackManager",
    "get_lightweight_feedback_manager",

    # Todo Failure Recovery (Phase 3.5)
    "TodoFailureRecovery",
    "RecoveryStrategy",
    "RecoveryResult",
    "get_failure_recovery",
    "reset_failure_recovery",

    # Planning Manager (Phase 2)
    "PlanManager",
    "plan_manager",
    "get_plan_manager",
    "ResourcePlanner",
    "resource_planner",
    "get_resource_planner",
    "ExecutionGraphBuilder",
    "execution_graph_builder",
    "get_execution_graph_builder",
]
