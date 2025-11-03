"""Supervisor Graph 정의

LangGraph 1.0을 사용한 메인 그래프
Phase 3: Executor + Agents 추가 (완전한 Execution Loop)
Phase 3.5: Aggregator + Generator 추가 (Answer Generation)
Phase 3.6: Graph & Report Generator 추가
Phase 4.1: PostgreSQL Checkpointer 통합
"""
from typing import Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.octostrator.supervisor.nodes import (
    intent_understanding_node,
    planning_node,
    executor_node,
    hitl_handler_node,
)
from backend.app.octostrator.supervisor.nodes.aggregator import aggregator_node
from backend.app.octostrator.supervisor.nodes.router import output_router_node
from backend.app.octostrator.supervisor.nodes.generators import (
    chat_generator_node,
    graph_generator_node,
    report_generator_node,
)
from backend.app.octostrator.agents import (
    search_agent_node,
    validation_agent_node,
    analysis_agent_node,
    comparison_agent_node,
    document_agent_node,
)
from backend.app.config.system import config


def build_supervisor_graph(
    context: Optional[AppContext] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    """Supervisor Graph 생성

    Phase 3: 완전한 Execution Loop 구현
    - Intent Understanding: 사용자 의도 파악
    - Planning: 작업을 Task 리스트로 분해
    - Executor: 계획에 따라 Agent 순차 실행 (Command 기반 동적 라우팅)
    - Agents: 실제 작업 수행 (search, validation, analysis, comparison, document)
    - HITL Handler: 사용자 승인 처리 (Phase 3: 자동 승인, Phase 4: 실제 대기)

    Phase 3.5: Aggregator + Generator 추가
    - Aggregator: 모든 Agent 결과를 구조화된 데이터로 변환
    - Output Router: 출력 형식에 따라 적절한 Generator 선택
    - Chat Generator: 자연스러운 대화형 답변 생성

    Phase 3.6: Graph & Report Generator 추가
    - Graph Generator: 시각화 데이터 생성 (D3.js, Cytoscape.js 등)
    - Report Generator: Markdown 보고서 생성

    Phase 4.1: PostgreSQL Checkpointer 통합
    - AsyncPostgresSaver를 통한 State 영속화
    - thread_id 기반 세션 관리

    Args:
        context: AppContext (선택적)
        checkpointer: AsyncPostgresSaver (선택적, Phase 4.1+)

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

    # === Phase 3.5: Aggregator + Generator ===

    async def aggregator_wrapper(state: SupervisorState) -> dict:
        """Aggregator 노드"""
        return await aggregator_node(state, llm)

    # output_router_node와 chat_generator_node는 async 함수이므로 그대로 사용

    # === 노드 추가 ===

    # 1. Intent & Planning
    workflow.add_node("intent", intent_node)
    workflow.add_node("planning", planning_node_wrapper)

    # 2. Executor (Command 사용, ends 명시 필수)
    # Phase 3.5: END 대신 "aggregator" 추가
    workflow.add_node("executor", executor_node, ends=[
        "search", "validation", "analysis", "comparison", "document", "hitl_handler", "aggregator"
    ])

    # 3. Agents (교체 가능)
    workflow.add_node("search", search_agent_node)
    workflow.add_node("validation", validation_agent_node)
    workflow.add_node("analysis", analysis_agent_node)
    workflow.add_node("comparison", comparison_agent_node)
    workflow.add_node("document", document_agent_node)

    # 4. HITL Handler
    workflow.add_node("hitl_handler", hitl_handler_node)

    # 5. Phase 3.5: Aggregator + Generator
    workflow.add_node("aggregator", aggregator_wrapper)
    workflow.add_node("output_router", output_router_node, ends=["chat_generator", "graph_generator", "report_generator"])
    workflow.add_node("chat_generator", chat_generator_node)

    # 6. Phase 3.6: Graph & Report Generator
    workflow.add_node("graph_generator", graph_generator_node)
    workflow.add_node("report_generator", report_generator_node)

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

    # Phase 3.5/3.6: Aggregator + Generator 플로우
    # Aggregator → Output Router → (Chat | Graph | Report) Generator → END
    workflow.add_edge("aggregator", "output_router")
    workflow.add_edge("chat_generator", END)
    workflow.add_edge("graph_generator", END)
    workflow.add_edge("report_generator", END)

    # 그래프 컴파일
    # Phase 4.1: Checkpointer 통합
    if checkpointer is not None:
        print("[Graph] ✓ Checkpointer와 함께 그래프 컴파일")
        return workflow.compile(checkpointer=checkpointer)
    else:
        print("[Graph] ✓ Checkpointer 없이 그래프 컴파일 (Phase 3.6 모드)")
        return workflow.compile()
