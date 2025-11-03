"""Supervisor Graph 정의

LangGraph 1.0을 사용한 메인 그래프
단일 노드로 LLM을 호출하는 최소 버전
"""
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.config.system import config


def build_supervisor_graph():
    """Supervisor Graph 생성 (최소 버전)

    Returns:
        CompiledGraph: 컴파일된 LangGraph 그래프
    """
    # LLM 초기화
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=config.openai_api_key
    )

    # StateGraph 생성
    workflow = StateGraph(SupervisorState)

    # 노드 정의: LLM 호출만
    async def supervisor_node(state: SupervisorState) -> dict:
        """Supervisor 노드 - 단순 LLM 호출

        Args:
            state: SupervisorState 현재 상태

        Returns:
            dict: 업데이트할 상태 (messages 키 포함)
        """
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    # 노드 추가
    workflow.add_node("supervisor", supervisor_node)

    # 엣지 정의: 시작 -> supervisor -> 종료
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", END)

    # 그래프 컴파일
    return workflow.compile()
