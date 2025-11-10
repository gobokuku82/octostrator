"""
Execute Layer Graph Builder

Builds the workflow graph for execution processing.

Phase 2 Updates:
- Context API 통합 (context_schema 추가)
- 환경별 LLM 설정 자동 적용
- 노드별 LLM 파라미터 최적화

Author: Specialist Agent Development Team
Date: 2025-11-05 (Created)
Updated: 2025-11-06 (Phase 2 Context API)
Version: 2.0
"""

from typing import Optional
from langgraph.graph import StateGraph, START, END
from .execute_nodes import (
    execute_layer_node,  # Phase 1: 새 함수명
    aggregator_node,
    error_handler_node
)

# Backward compatibility
executor_node = execute_layer_node


def build_execute_graph(
    state_class=None,
    context: Optional["AppContext"] = None
):
    """
    Build the execute layer workflow graph.

    Phase 2 Updates:
    - Context API 지원: context_schema 파라미터로 runtime 자동 주입
    - 환경별 LLM 설정 자동 적용 (SYSTEM_ENV 환경 변수)
    - 노드별 LLM 파라미터 최적화 (비용 절감)

    Args:
        state_class: State class (default: dict)
        context: AppContext instance (optional, Phase 2)
                 None이면 환경 변수에서 자동 생성

    Flow:
    1. Execute agents
    2. Handle errors (if any)
    3. Aggregate results

    Phase 2 Features:
    - Runtime이 자동으로 주입되어 _create_llm_for_agents()가 Context API 사용
    - SYSTEM_ENV=production → 비용 최적화 설정
    - SYSTEM_ENV=development → 품질 우선 설정
    - SYSTEM_ENV=testing → 재현성 확보 (temp=0)
    """
    # State 기본값
    if state_class is None:
        state_class = dict

    # ⭐ Phase 2: Context 자동 생성 (환경 변수 기반)
    if context is None:
        from backend.app.octostrator.contexts.app_context import AppContext
        from backend.app.config.llm_settings import get_llm_settings_from_env

        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=llm_settings
        )

    # ⭐ Phase 2: Context API 활성화 (context_schema 추가)
    # 이것만 추가하면 runtime이 자동 주입됨!
    graph = StateGraph(
        state_class,
        context_schema=type(context)  # AppContext 클래스
    )

    # Add nodes
    graph.add_node("executor", executor_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("aggregator", aggregator_node)

    # Add edges
    graph.add_edge(START, "executor")

    # Conditional: Check for errors
    graph.add_conditional_edges(
        "executor",
        lambda x: "error_handler" if x.get("error") or any(
            r.get("status") == "failed" for r in x.get("execution_results", [])
        ) else "aggregator",
        {
            "error_handler": "error_handler",
            "aggregator": "aggregator"
        }
    )

    graph.add_edge("error_handler", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()
