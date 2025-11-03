"""Supervisor Graph 정의

LangGraph 1.0을 사용한 메인 그래프
Phase 2: Intent Understanding + Planning Agent 추가
"""
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.octostrator.nodes import intent_understanding_node, planning_node
from backend.app.config.system import config


def build_supervisor_graph(context: Optional[AppContext] = None):
    """Supervisor Graph 생성

    Phase 2: Intent Understanding + Planning Agent 추가
    - Intent Understanding: 사용자 의도 파악
    - Planning: 작업을 Task 리스트로 분해
    - Supervisor: 계획 실행 (Phase 3에서 Executor로 변경 예정)

    Args:
        context: AppContext (선택적)

    Returns:
        CompiledGraph: 컴파일된 LangGraph 그래프
    """
    # LLM 초기화 (Context 우선, 없으면 기본값)
    if context is not None:
        llm = context.llm
    else:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=config.openai_api_key
        )

    # StateGraph 생성
    workflow = StateGraph(SupervisorState)

    # === Phase 2: Intent & Planning Nodes ===

    async def intent_node(state: SupervisorState) -> dict:
        """Intent Understanding 노드"""
        return await intent_understanding_node(state, llm)

    async def planning_node_wrapper(state: SupervisorState) -> dict:
        """Planning 노드"""
        return await planning_node(state, llm)

    # === Phase 1 Supervisor Node (Phase 3에서 Executor로 변경 예정) ===

    async def supervisor_node(state: SupervisorState) -> dict:
        """Supervisor 노드 - Phase 3에서 Executor로 변경 예정

        현재는 계획 결과를 출력하고 종료

        Args:
            state: SupervisorState 현재 상태

        Returns:
            dict: 업데이트할 상태 (messages 키 포함)
        """
        # Phase 2: 계획이 있으면 출력
        plan = state.get("plan", [])
        if plan:
            plan_summary = "\n".join([
                f"Step {step['step_id']}: [{step['agent']}] {step['description']}"
                for step in plan
            ])
            from langchain_core.messages import AIMessage
            return {
                "messages": [
                    AIMessage(
                        content=f"[Supervisor] 계획 실행 준비 완료\n\n"
                                f"다음 단계에서 실행될 계획:\n{plan_summary}\n\n"
                                f"(Phase 3에서 실제 Executor 구현 예정)"
                    )
                ]
            }

        # Fallback: 계획이 없으면 기본 LLM 호출
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    # === 노드 추가 ===
    workflow.add_node("intent", intent_node)
    workflow.add_node("planning", planning_node_wrapper)
    workflow.add_node("supervisor", supervisor_node)

    # === 엣지 정의: START → intent → planning → supervisor → END ===
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "planning")
    workflow.add_edge("planning", "supervisor")
    workflow.add_edge("supervisor", END)

    # 그래프 컴파일
    return workflow.compile()
