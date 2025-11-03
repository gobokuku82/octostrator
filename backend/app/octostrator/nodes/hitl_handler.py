"""HITL (Human-in-the-Loop) Handler

사용자 승인 대기 및 재개
Phase 3: 기본 구조 구현
Phase 4: Checkpointer와 통합
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def hitl_handler_node(state: SupervisorState) -> Dict:
    """HITL 핸들러 - 사용자 승인 대기

    Phase 3: 기본 구조 (대기 메시지만 출력)
    Phase 4: Checkpointer와 통합하여 실제 대기/재개 구현

    사용자 응답은 별도 FastAPI 엔드포인트(/hitl/resume)로 받아서 처리

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
            - messages: HITL 질문 메시지
            - (Phase 4에서 Checkpointer로 State 저장)
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # HITL 질문 가져오기
    question = step.get("hitl_question", "승인해주세요")

    # Phase 3: 일단 자동 승인 (Phase 4에서 실제 대기 구현)
    # TODO Phase 4: Checkpointer로 State 저장하고 대기
    # 현재는 테스트를 위해 자동 승인

    # State 업데이트: 자동 승인
    plan[current_step]["status"] = "completed"
    plan[current_step]["hitl_response"] = "[Auto-approved in Phase 3]"
    plan[current_step]["result"] = f"HITL: {question} (자동 승인)"

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "is_waiting_human": False,  # Phase 4에서는 True로 설정하고 대기
        "messages": [
            AIMessage(
                content=f"[HITL] {question}\n\n"
                        f"(Phase 3: 자동 승인됨. Phase 4에서 실제 사용자 승인 기능 추가 예정)"
            )
        ]
    }


# Phase 4에서 구현 예정
async def hitl_resume(state: SupervisorState, user_response: str) -> Dict:
    """HITL에서 재개 (Phase 4 구현 예정)

    사용자 응답을 받아서 그래프를 재개합니다.

    Args:
        state: Checkpointer에서 복원된 State
        user_response: 사용자 응답

    Returns:
        Dict: 업데이트할 state
    """
    plan = state["plan"]
    current_step = state["current_step"]

    # 사용자 응답 저장
    plan[current_step]["hitl_response"] = user_response
    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = f"HITL: 사용자 응답 - {user_response}"

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "is_waiting_human": False
    }
