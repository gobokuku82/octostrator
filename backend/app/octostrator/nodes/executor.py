"""Executor Node

계획(plan)에 따라 Agent를 순차적으로 실행하는 실행 루프
Phase 3: Execution Loop
"""
from typing import Union
from langgraph.types import Command
from langgraph.graph import END
from backend.app.octostrator.states.supervisor_state import SupervisorState


def update_step_status(plan: list[dict], step_idx: int, status: str) -> list[dict]:
    """계획의 특정 단계 상태 업데이트

    Args:
        plan: 전체 계획 리스트
        step_idx: 업데이트할 단계 인덱스
        status: 새로운 상태

    Returns:
        업데이트된 계획 리스트
    """
    new_plan = [s.copy() for s in plan]
    new_plan[step_idx]["status"] = status
    return new_plan


async def executor_node(state: SupervisorState) -> Command:
    """계획에 따라 Agent를 순차적으로 실행

    Phase 3: Execution Loop의 핵심 노드
    - plan 배열을 순회하며 각 Task 실행
    - 각 Task 상태 업데이트
    - HITL 대기 처리
    - 에러 핸들링

    Args:
        state: 현재 SupervisorState

    Returns:
        Command: 다음 노드로의 라우팅 명령
            - goto: 다음에 실행할 노드 이름
            - update: State 업데이트 내용
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)

    # 모든 단계 완료 확인
    if current_step >= len(plan):
        # Phase 3.5: 모든 단계 완료 시 Aggregator로 이동
        # Aggregator가 최종 결과 생성 담당
        return Command(
            update={"is_executing": False},
            goto="aggregator"
        )

    # 현재 단계 가져오기
    step = plan[current_step]

    # HITL 체크
    if step["agent"] == "hitl":
        return Command(
            update={
                "is_waiting_human": True,
                "plan": update_step_status(plan, current_step, "waiting_human")
            },
            goto="hitl_handler"
        )

    # Agent 선택
    agent_name = step["agent"]

    # 현재 단계를 "running"으로 업데이트
    updated_plan = update_step_status(plan, current_step, "running")

    return Command(
        update={"plan": updated_plan},
        goto=agent_name  # "search", "validation", "analysis", "comparison", "document"
    )
