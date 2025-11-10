"""
Octostrator Main Graph Builder

새로운 구조 (2025-11-06):
Cognitive → [Conditional Todo Manager] → Execute → Response

Todo Manager는 필요시에만 조건부로 실행됩니다.

Phase 2 Updates:
- Context API 통합 (context_schema 추가)
- 환경별 LLM 설정 자동 적용
- 노드별 LLM 파라미터 최적화

Author: Specialist Agent Development Team
Date: 2025-11-06 (Created)
Updated: 2025-11-06 (Phase 2 Context API)
Version: 2.0
"""

from typing import Optional
from langgraph.graph import StateGraph, START, END
from backend.app.octostrator.states import OctostratorState
from .octostrator_nodes import (
    cognitive_layer_node,
    todo_layer_node,
    execute_layer_node,
    response_layer_node
)


def should_use_todo_manager(state: OctostratorState) -> str:
    """
    Conditional Edge: Todo Manager 실행 여부 판단

    Todo Manager는 다음 경우에만 실행됩니다:
    1. Cognitive가 복잡한 계획을 생성하여 Todo 관리가 필요한 경우
    2. 사용자가 API를 통해 Todo 수정을 요청한 경우
    3. Execute 중 새로운 Todo가 필요한 경우

    Args:
        state: 현재 OctostratorState

    Returns:
        "todo" (Todo Manager 실행) 또는 "execute" (건너뛰기)
    """
    # 1. Cognitive가 Todo 생성 요청
    if state.get("plan_requires_todos", False):
        return "todo"

    # 2. 사용자가 API로 Todo 수정 요청
    if state.get("user_requested_todo_update", False):
        return "todo"

    # 3. Execute에서 Todo 업데이트 요청
    if state.get("need_todo_update", False):
        return "todo"

    # 기본: Todo Manager 건너뛰기
    return "execute"


def build_octostrator_graph(
    checkpointer=None,
    context: Optional["AppContext"] = None
):
    """
    Build the main orchestrator graph with conditional Todo Manager.

    새로운 Flow (2025-11-06):
    START
      → Cognitive Layer (intent understanding, planning)
      → [Conditional] Todo Manager (필요시에만 실행)
      → Execute Layer (agent execution, aggregation)
      → Response Layer (response generation)
      → END

    Phase 2 Updates:
    - Context API 지원: context_schema 파라미터로 runtime 자동 주입
    - 환경별 LLM 설정 자동 적용 (SYSTEM_ENV 환경 변수)
    - 노드별 LLM 파라미터 최적화 (비용 절감)

    Args:
        checkpointer: LangGraph checkpointer (e.g., AsyncPostgresSaver)
        context: AppContext instance (optional, Phase 2)
                 None이면 환경 변수에서 자동 생성

    Returns:
        Compiled LangGraph workflow with OctostratorState

    Phase 2 Features:
    - Runtime이 자동으로 주입되어 모든 노드에서 Context API 사용 가능
    - SYSTEM_ENV=production → 비용 최적화 설정
    - SYSTEM_ENV=development → 품질 우선 설정
    - SYSTEM_ENV=testing → 재현성 확보 (temp=0)
    """
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
        OctostratorState,
        context_schema=type(context)  # AppContext 클래스
    )

    # Add layer nodes
    graph.add_node("cognitive", cognitive_layer_node)
    graph.add_node("todo", todo_layer_node)          # 조건부 실행!
    graph.add_node("execute", execute_layer_node)
    graph.add_node("response", response_layer_node)

    # Connect layers
    graph.add_edge(START, "cognitive")

    # ===== Conditional Edge: Todo Manager 호출 여부 결정 =====
    graph.add_conditional_edges(
        "cognitive",
        should_use_todo_manager,  # 조건 함수
        {
            "todo": "todo",        # Todo Manager 실행
            "execute": "execute"   # Todo Manager 건너뛰기
        }
    )

    # Todo Manager → Execute
    graph.add_edge("todo", "execute")

    # Execute → Response → END
    graph.add_edge("execute", "response")
    graph.add_edge("response", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=checkpointer)
