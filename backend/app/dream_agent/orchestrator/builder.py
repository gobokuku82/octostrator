"""Builder - LangGraph 그래프 조립

Phase 1.6 변경사항:
- build_unified_agent_graph(): 통합 실행 레이어 사용 (권장)
- build_agent_graph(): 레거시 (ml_execution + biz_execution 분리)
"""

import warnings
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.app.dream_agent.states import AgentState
from backend.app.dream_agent.cognitive import cognitive_node
from backend.app.dream_agent.planning import planning_node
from backend.app.dream_agent.response import response_node

# Phase 1.6: 통합 실행 레이어
from backend.app.dream_agent.execution import execution_node
from .router import (
    route_to_execution,
    route_after_execution,
)

# Legacy imports (deprecated) - removed as modules no longer exist
# from backend.app.dream_agent.ml_execution import ml_graph
# from backend.app.dream_agent.biz_execution import biz_graph
# from .router import (
#     route_after_planning,
#     route_after_ml_execution,
#     route_after_biz_execution,
# )


# ================================
# Phase 1.6 - 통합 실행 레이어 그래프
# ================================

def build_unified_agent_graph() -> StateGraph:
    """
    통합 실행 레이어를 사용하는 Agent 그래프 빌드 (Phase 1.6+)

    구조:
        START -> cognitive -> planning -> execution (loop) -> response -> END

    Returns:
        StateGraph 인스턴스
    """
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("cognitive", cognitive_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("execution", execution_node)  # 통합 실행 노드
    workflow.add_node("response", response_node)

    # 엣지 정의
    # START -> cognitive -> planning
    workflow.add_edge(START, "cognitive")
    workflow.add_edge("cognitive", "planning")

    # planning -> conditional routing
    workflow.add_conditional_edges(
        "planning",
        route_to_execution,
        {
            "execution": "execution",
            "response": "response",
            "END": END
        }
    )

    # execution -> conditional routing (루프)
    workflow.add_conditional_edges(
        "execution",
        route_after_execution,
        {
            "execution": "execution",  # 루프: 더 많은 todos
            "response": "response"
        }
    )

    # response -> END
    workflow.add_edge("response", END)

    return workflow


# ================================
# Legacy Graph Builder (Deprecated)
# ================================

def build_agent_graph() -> StateGraph:
    """
    Agent 그래프 빌드 (레거시)

    .. deprecated:: Phase 1.6
        Use :func:`build_unified_agent_graph` instead for unified execution layer.
        This function is no longer functional as ml_execution and biz_execution modules have been removed.

    Returns:
        StateGraph 인스턴스
    """
    warnings.warn(
        "build_agent_graph is deprecated and no longer functional. Use build_unified_agent_graph for unified execution layer.",
        DeprecationWarning,
        stacklevel=2
    )

    # Return the unified graph instead
    return build_unified_agent_graph()


def create_agent(
    checkpointer=None,
    interrupt_before: list[str] | None = None,
    use_legacy: bool = False
):
    """
    Agent 인스턴스 생성

    Args:
        checkpointer: 체크포인터 (기본값: MemorySaver)
        interrupt_before: HITL을 위해 중단할 노드 목록
                         (기본값: [] - 자동 중단 없음)
        use_legacy: True이면 레거시 그래프 사용 (ml_execution + biz_execution 분리)
                   False이면 통합 실행 레이어 사용 (기본값)

    Returns:
        컴파일된 그래프
    """
    if use_legacy:
        workflow = build_agent_graph()
    else:
        workflow = build_unified_agent_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    # HITL: 자동 중단 없음 (사용자가 Stop 클릭 시에만 중단)
    # interrupt_before를 빈 리스트로 설정하면 자동 중단 없이 끝까지 실행
    if interrupt_before is None:
        interrupt_before = []

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before
    )


def create_legacy_agent(checkpointer=None, interrupt_before: list[str] | None = None):
    """
    레거시 Agent 인스턴스 생성 (ml_execution + biz_execution 분리)

    .. deprecated:: Phase 1.6
        Use :func:`create_agent` instead.

    Args:
        checkpointer: 체크포인터 (기본값: MemorySaver)
        interrupt_before: HITL을 위해 중단할 노드 목록

    Returns:
        컴파일된 그래프
    """
    warnings.warn(
        "create_legacy_agent is deprecated. Use create_agent() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return create_agent(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
        use_legacy=True
    )
