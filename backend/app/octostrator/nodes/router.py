"""Output Router

출력 형식에 따라 적절한 Generator로 라우팅
Phase 3.5: Conditional Router for Output Format
Phase 3.6: Graph & Report Generator 지원
"""
from langgraph.types import Command
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def output_router_node(state: SupervisorState) -> Command:
    """Output Router - 출력 형식에 따라 적절한 Generator로 라우팅

    state["output_format"]에 따라 분기:
    - "chat": chat_generator (기본값)
    - "graph": graph_generator (Phase 3.6)
    - "report": report_generator (Phase 3.6)
    - "all": 모든 Generator 실행 (Phase 4)

    Args:
        state: 현재 SupervisorState

    Returns:
        Command: 다음 노드로 라우팅
    """
    output_format = state.get("output_format", "chat")  # 기본값: chat

    if output_format == "chat":
        return Command(goto="chat_generator")
    elif output_format == "graph":
        return Command(goto="graph_generator")
    elif output_format == "report":
        return Command(goto="report_generator")
    elif output_format == "all":
        # Phase 4에서 병렬 실행 구현
        return Command(goto="chat_generator")  # 임시로 chat_generator 사용
    else:
        # 알 수 없는 형식은 기본값 사용
        return Command(goto="chat_generator")
