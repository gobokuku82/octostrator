"""HITL (Human-in-the-Loop) Handler

사용자 승인 대기 및 재개
Phase 3: 기본 구조 구현
Phase 4.2: interrupt()를 사용한 실제 대기 구현
"""
from typing import Dict
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def hitl_handler_node(state: SupervisorState) -> Dict:
    """HITL 핸들러 - 사용자 승인 대기

    Phase 4.2: LangGraph 1.0 interrupt()를 사용한 실제 대기 구현

    사용자 응답은:
    1. graph.ainvoke(None, config)로 자동 승인 (None 입력)
    2. graph.ainvoke({"messages": [HumanMessage(...)]}, config)로 사용자 응답 전달

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
            - messages: HITL 질문 메시지
            - is_waiting_human: True (대기 상태)
            - (Checkpointer가 자동으로 State 저장)
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # HITL 질문 가져오기
    question = step.get("hitl_question", "승인해주세요")

    # Phase 4.2: interrupt()로 실제 대기
    print(f"[HITL] 사용자 승인 대기: {question}")

    # State 업데이트: 대기 상태로 설정
    plan[current_step]["status"] = "waiting_human"

    # Checkpointer에 state 저장하고 대기
    # interrupt()는 사용자 입력을 기다립니다
    # graph.ainvoke(None, config) 또는 사용자 응답과 함께 재개 가능
    user_response = interrupt(question)

    print(f"[HITL] 사용자 응답 수신: {user_response}")

    # 사용자 응답 처리
    if user_response is None:
        # None으로 재개된 경우 (자동 승인)
        plan[current_step]["hitl_response"] = "[Auto-approved]"
        plan[current_step]["result"] = f"HITL: {question} (자동 승인)"
    else:
        # 사용자 응답이 있는 경우
        plan[current_step]["hitl_response"] = str(user_response)
        plan[current_step]["result"] = f"HITL: {question} - 응답: {user_response}"

    # 완료 상태로 변경
    plan[current_step]["status"] = "completed"

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "is_waiting_human": False,  # 재개 후에는 False
        "messages": [
            AIMessage(
                content=f"[HITL] {question}\n\n"
                        f"사용자 응답: {user_response if user_response is not None else '(자동 승인)'}"
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
