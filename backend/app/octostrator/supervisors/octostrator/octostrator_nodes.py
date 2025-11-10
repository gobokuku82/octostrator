"""
Octostrator Layer Nodes

Each node executes a complete supervisor layer.
Updated to use OctostratorState with history tracking.

Author: Specialist Agent Development Team
Date: 2025-11-06
Version: 2.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.octostrator.states import OctostratorState
from langchain_openai import ChatOpenAI

# Phase 3: Runtime import for Context API
try:
    from langgraph.types import Runtime
except ImportError:
    Runtime = type(None)

logger = logging.getLogger(__name__)


# ====================================
# Phase 3: Context API 헬퍼 함수
# ====================================

def _create_llm_from_context(runtime: Optional[Runtime] = None) -> Optional[ChatOpenAI]:
    """
    Context API를 사용하여 LLM 생성

    Args:
        runtime: LangGraph Runtime (Context API)

    Returns:
        ChatOpenAI instance or None
    """
    from backend.app.config.system import config as system_config

    if runtime is not None:
        try:
            from backend.app.octostrator.contexts.app_context import AppContext
            context: AppContext = runtime.context
            settings = context.llm_settings

            logger.info(
                f"[Octostrator] Using Context API settings "
                f"(model={settings.agent_model}, temp={settings.agent_temperature}, "
                f"max_tokens={settings.agent_max_tokens})"
            )

            return ChatOpenAI(
                model=settings.agent_model,
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens,
                api_key=system_config.openai_api_key
            )
        except Exception as e:
            logger.warning(f"[Octostrator] Failed to use Context API: {e}")

    return None


async def cognitive_layer_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None  # Phase 3: Context API 지원
) -> OctostratorState:
    """
    Execute Cognitive Layer (Updated 2025-11-06)

    Tasks:
    - Intent understanding
    - Plan generation
    - Plan validation
    - History tracking
    - Todo Manager 호출 여부 결정

    Args:
        state: Current OctostratorState
        runtime: LangGraph Runtime (Phase 3: Context API)

    Returns:
        Updated state with plan and history
    """
    start_time = datetime.now()
    logger.info("[Octostrator] Executing Cognitive Layer")

    try:
        from ..cognitive.cognitive_helpers import CognitiveSupervisor

        # Phase 3: Context API를 사용하여 LLM 생성
        llm = _create_llm_from_context(runtime)

        supervisor = CognitiveSupervisor(
            llm=llm,  # Phase 3: Context API에서 생성됨
            checkpointer=None  # 현재 사용하지 않음
        )

        # Execute planning
        # Phase 3: session_id 파라미터 제거 (plan() 메서드에 없음)
        # session_id가 필요하면 context에 포함시킬 수 있음
        context_data = {
            "session_id": state.get("session_id", "default"),
            "auto_approve": True
        }

        plan = await supervisor.plan(
            user_message=state.get("user_query", ""),
            context=context_data
        )

        # Update state
        state["plan"] = plan
        state["plan_valid"] = plan is not None

        # ===== Todo Manager 호출 여부 결정 (신규) =====
        # 예시: 복잡한 계획이면 Todo Manager 호출
        if plan and len(plan.get("steps", [])) > 1:
            state["plan_requires_todos"] = True
        else:
            state["plan_requires_todos"] = False

        # ===== History 기록 (신규) =====
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Action history 기록
        state["action_history"] = [{
            "action": "cognitive_layer_node",
            "result": {"plan": plan},
            "duration_ms": duration_ms
        }]

        # Plan history 기록
        if plan:
            state["plan_history"] = [{
                "plan": plan,
                "reason": "initial_creation",
                "modified_by": "system"
            }]

        # Metadata 업데이트
        if "created_at" not in state or not state.get("created_at"):
            state["created_at"] = start_time.isoformat()
        state["updated_at"] = end_time.isoformat()
        state["total_steps"] = len(state.get("action_history", []))

        logger.info(f"[Octostrator] Cognitive Layer complete. Plan: {plan.get('goal', 'N/A') if plan else 'None'}")

        return state

    except Exception as e:
        logger.error(f"[Octostrator] Cognitive Layer failed: {e}")
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        state["error"] = str(e)
        state["plan_valid"] = False

        # 에러도 history에 기록
        state["action_history"] = [{
            "action": "cognitive_layer_node",
            "result": {"error": str(e)},
            "duration_ms": duration_ms
        }]

        state["updated_at"] = end_time.isoformat()

        return state


async def todo_layer_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None  # Phase 3: Context API 지원
) -> OctostratorState:
    """
    Execute Todo Layer (Updated 2025-11-06)

    Tasks:
    - Convert plan to TODOs
    - HITL approval (if needed)
    - Batch preparation
    - History tracking

    Args:
        state: Current OctostratorState with plan
        runtime: LangGraph Runtime (Phase 3: Context API)

    Returns:
        Updated state with todos and history
    """
    start_time = datetime.now()
    logger.info("[Octostrator] Executing Todo Layer")

    try:
        from ..todo.todo_manager import TodoAgent

        # Get plan from state
        plan = state.get("plan", {})
        if not plan:
            logger.warning("[Octostrator] No plan found in state")
            state["todos"] = []
            return state

        # Get or create TodoAgent
        todo_agent = TodoAgent()

        # Initialize if needed
        # Phase 3: Context API를 사용하여 LLM 생성
        if not hasattr(todo_agent, '_initialized'):
            llm = _create_llm_from_context(runtime)
            await todo_agent.initialize(
                llm=llm,  # Phase 3: Context API에서 생성됨
                checkpointer=None  # 현재 사용하지 않음
            )

        # Convert plan to todos
        # Phase 3: context를 빈 dict로 전달 (State에서 제거됨)
        result = await todo_agent.execute(
            task={"type": "convert_plan", "plan": plan},
            context={},  # Phase 3: Context API로 대체
            thread_id=state.get("session_id", "default")
        )

        # Extract todos
        todos = result.get("result", {}).get("todos", [])

        # HITL handling
        # Phase 3: Runtime에서 auto_approve 확인
        auto_approve = True  # 기본값: 자동 승인
        if runtime is not None:
            try:
                from backend.app.octostrator.contexts.app_context import AppContext
                context: AppContext = runtime.context
                # TODO: AppContext에 auto_approve 필드 추가 필요
                # 현재는 기본값 사용
                auto_approve = True  # 임시: 항상 자동 승인
            except Exception as e:
                logger.warning(f"[Octostrator] Failed to get auto_approve from context: {e}")
                auto_approve = True

        if not auto_approve and todos:
            logger.info("[Octostrator] TODO approval required (HITL)")
            state["requires_approval"] = True
            state["approval_data"] = {
                "todos": todos,
                "plan_goal": plan.get("goal", "")
            }

        # Update state (merge_todos_smart reducer will be applied)
        state["todos"] = todos
        state["total_todos"] = len(todos)

        # ===== History 기록 (신규) =====
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        state["action_history"] = [{
            "action": "todo_layer_node",
            "result": {"todos_count": len(todos)},
            "duration_ms": duration_ms
        }]

        state["updated_at"] = end_time.isoformat()
        state["total_steps"] = len(state.get("action_history", []))

        logger.info(f"[Octostrator] Todo Layer complete. Todos: {len(todos)}")

        return state

    except Exception as e:
        logger.error(f"[Octostrator] Todo Layer failed: {e}")
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        state["error"] = str(e)
        state["todos"] = []

        # 에러도 history에 기록
        state["action_history"] = [{
            "action": "todo_layer_node",
            "result": {"error": str(e)},
            "duration_ms": duration_ms
        }]

        state["updated_at"] = end_time.isoformat()

        return state


async def execute_layer_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None  # Phase 3: Context API 지원
) -> OctostratorState:
    """
    Execute Layer Wrapper - Octostrator → Execute Layer
    (Phase 1 Integration: Updated 2025-11-06)

    Tasks:
    - Delegate to new execute_layer_node from execute_nodes.py
    - 7 Agent 통합 실행
    - Result aggregation
    - Error handling
    - History tracking

    Args:
        state: Current OctostratorState with todos
        runtime: LangGraph Runtime (Phase 3: Context API)

    Returns:
        Updated state with execution results and history
    """
    start_time = datetime.now()
    logger.info("[Octostrator] Delegating to Execute Layer (Phase 1)")

    try:
        # ⭐ Phase 1: 새로운 Execute Layer 호출
        from ..execute.execute_nodes import execute_layer_node as execute_impl

        # Get todos from state
        todos = state.get("todos", [])
        if not todos:
            logger.warning("[Octostrator] No todos found in state")
            state["execution_results"] = {}
            state["completed"] = 0
            state["failed"] = 0
            state["success_rate"] = 0.0
            return state

        # Execute Layer 호출 (Phase 3: runtime 전달)
        result = await execute_impl(state, runtime=runtime)  # Dict[str, Any] → Dict[str, Any]

        # ===== Result를 OctostratorState에 매핑 =====
        state["execution_results"] = result.get("execution_results", {})
        state["completed"] = result.get("completed", 0)
        state["failed"] = result.get("failed", 0)
        state["success_rate"] = result.get("success_rate", 0.0)

        # Todos 업데이트 (execute_impl이 반환한 업데이트된 todos)
        if "todos" in result:
            state["todos"] = result["todos"]

        # ===== History 기록 =====
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Execute Layer의 action_history 가져오기 (있으면)
        execute_history = result.get("action_history", [])

        # Octostrator의 action_history에 추가
        state["action_history"] = [{
            "action": "execute_layer_node_wrapper",
            "result": {
                "completed": state["completed"],
                "failed": state["failed"],
                "success_rate": state["success_rate"]
            },
            "duration_ms": duration_ms,
            "sub_actions": execute_history  # Execute Layer의 상세 history
        }]

        state["updated_at"] = end_time.isoformat()
        state["total_steps"] = len(state.get("action_history", []))

        logger.info(
            f"[Octostrator] Execute Layer complete (Phase 1). "
            f"Success: {state['completed']}/{len(todos)} "
            f"({state['success_rate']:.1%})"
        )

        return state

    except Exception as e:
        logger.error(f"[Octostrator] Execute Layer failed: {e}", exc_info=True)
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        state["error"] = str(e)
        state["execution_results"] = {}
        state["completed"] = 0
        state["failed"] = 0
        state["success_rate"] = 0.0

        # 에러도 history에 기록
        state["action_history"] = [{
            "action": "execute_layer_node_wrapper",
            "result": {"error": str(e)},
            "duration_ms": duration_ms
        }]

        state["updated_at"] = end_time.isoformat()

        return state


async def response_layer_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None  # Phase 3: Context API 지원
) -> OctostratorState:
    """
    Execute Response Layer (Updated 2025-11-06)

    Tasks:
    - HITL for final approval (if needed)
    - Output format routing
    - Response generation (chat/graph/report)
    - History tracking

    Args:
        state: Current OctostratorState with execution results
        runtime: LangGraph Runtime (Phase 3: Context API)

    Returns:
        Updated state with final response and history
    """
    start_time = datetime.now()
    logger.info("[Octostrator] Executing Response Layer")

    try:
        from ..response.response_graph import build_response_graph

        # Build response graph
        response_graph = build_response_graph()

        # Prepare response state
        response_state = {
            "execution_results": state.get("execution_results", {}),
            "plan": state.get("plan", {}),
            "output_format": state.get("output_format", "chat"),
            "requires_approval": state.get("requires_approval", False)
        }

        # Execute response generation
        result = await response_graph.ainvoke(response_state)

        # Update state with final response
        state["final_response"] = result.get("final_response", "")
        state["response_format"] = result.get("selected_format", "chat")

        # ===== History 기록 (신규) =====
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        state["action_history"] = [{
            "action": "response_layer_node",
            "result": {"format": state["response_format"]},
            "duration_ms": duration_ms
        }]

        state["updated_at"] = end_time.isoformat()
        state["total_steps"] = len(state.get("action_history", []))

        logger.info(
            f"[Octostrator] Response Layer complete. "
            f"Format: {state['response_format']}"
        )

        return state

    except Exception as e:
        logger.error(f"[Octostrator] Response Layer failed: {e}")
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        state["error"] = str(e)
        state["final_response"] = f"Error generating response: {e}"

        # 에러도 history에 기록
        state["action_history"] = [{
            "action": "response_layer_node",
            "result": {"error": str(e)},
            "duration_ms": duration_ms
        }]

        state["updated_at"] = end_time.isoformat()

        return state
