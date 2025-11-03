"""Supervisor Graph 정의

LangGraph 1.0을 사용한 메인 그래프
Phase 3: Executor + Agents 추가 (완전한 Execution Loop)
"""
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.octostrator.nodes import (
    intent_understanding_node,
    planning_node,
    executor_node,
    hitl_handler_node,
)
from backend.app.octostrator.agents import (
    search_agent_node,
    validation_agent_node,
    analysis_agent_node,
    comparison_agent_node,
    document_agent_node,
)
from backend.app.config.system import config


def build_supervisor_graph(context: Optional[AppContext] = None):
    """Supervisor Graph 생성

    Phase 3: 완전한 Execution Loop 구현
    - Intent Understanding: 사용자 의도 파악
    - Planning: 작업을 Task 리스트로 분해
    - Executor: 계획에 따라 Agent 순차 실행 (Command 기반 동적 라우팅)
    - Agents: 실제 작업 수행 (search, validation, analysis, comparison, document)
    - HITL Handler: 사용자 승인 처리 (Phase 3: 자동 승인, Phase 4: 실제 대기)

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

    # === Phase 3: Executor Node (Command 기반 동적 라우팅) ===
    # Executor는 Command를 반환하므로 그대로 사용
    # executor_node는 이미 async 함수이므로 wrapper 불필요

    # === Phase 3: Agent Nodes ===
    # Agent 노드들도 이미 async 함수이므로 그대로 사용

    # === Phase 3: HITL Handler ===
    # HITL Handler도 이미 async 함수이므로 그대로 사용

    # === 노드 추가 ===

    # 1. Intent & Planning
    workflow.add_node("intent", intent_node)
    workflow.add_node("planning", planning_node_wrapper)

    # 2. Executor (Command 사용, ends 명시 필수)
    workflow.add_node("executor", executor_node, ends=[
        "search", "validation", "analysis", "comparison", "document", "hitl_handler", END
    ])

    # 3. Agents (교체 가능)
    workflow.add_node("search", search_agent_node)
    workflow.add_node("validation", validation_agent_node)
    workflow.add_node("analysis", analysis_agent_node)
    workflow.add_node("comparison", comparison_agent_node)
    workflow.add_node("document", document_agent_node)

    # 4. HITL Handler
    workflow.add_node("hitl_handler", hitl_handler_node)

    # === 엣지 정의 ===

    # 플로우: START → intent → planning → executor → (Agents | HITL | END)
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "planning")
    workflow.add_edge("planning", "executor")

    # 모든 Agent → executor로 복귀 (다음 Task 실행)
    workflow.add_edge("search", "executor")
    workflow.add_edge("validation", "executor")
    workflow.add_edge("analysis", "executor")
    workflow.add_edge("comparison", "executor")
    workflow.add_edge("document", "executor")

    # HITL → executor로 복귀 (Phase 3: 자동 승인 후 복귀)
    workflow.add_edge("hitl_handler", "executor")

    # 그래프 컴파일
    return workflow.compile()
