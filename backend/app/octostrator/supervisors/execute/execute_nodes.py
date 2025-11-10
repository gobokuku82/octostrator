"""
Execute Layer Nodes

Execution and aggregation nodes for Layer 2.
Phase 1: 7개 에이전트 통합 (Context API 확장 포인트 포함)

Author: Specialist Agent Development Team
Date: 2025-11-06
Version: 2.0 (Option A+ - 확장 가능)
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI

# Phase 2: Runtime import (optional for Phase 1)
try:
    from langgraph.types import Runtime
except ImportError:
    # Phase 1: Runtime not available in older LangGraph versions
    Runtime = type(None)  # Placeholder type

logger = logging.getLogger(__name__)


# ====================================
# 확장 포인트: LLM 생성 헬퍼 함수
# ====================================

def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """
    Agent용 LLM 생성 (Context API 확장 포인트)

    [Phase 1] runtime=None: 기본 설정 사용
    [Phase 2] runtime 있음: Context API 설정 사용

    Args:
        runtime: LangGraph Runtime (Context API)

    Returns:
        ChatOpenAI instance
    """
    from backend.app.config.system import config as system_config

    # Phase 2: Context API 사용 (runtime이 있을 때)
    if runtime is not None:
        try:
            from backend.app.octostrator.contexts.app_context import AppContext
            context: AppContext = runtime.context
            settings = context.llm_settings

            logger.info(
                f"[Execute] Using Context API settings "
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
            logger.warning(
                f"[Execute] Failed to use Context API, falling back to default: {e}"
            )

    # Phase 1: 기본 설정
    default_model = "gpt-4o-mini"  # Phase 1 기본 모델
    logger.info(
        f"[Execute] Using default LLM settings "
        f"(model={default_model})"
    )

    return ChatOpenAI(
        model=default_model,
        api_key=system_config.openai_api_key,
        temperature=0.7,
        max_tokens=4096
    )


# ====================================
# EXECUTION NODE
# ====================================

async def execute_layer_node(
    state: Dict[str, Any],
    runtime: Optional[Runtime] = None  # ⭐ Phase 2 확장 포인트
) -> Dict[str, Any]:
    """
    Execute Layer Node - 7개 에이전트 실행 및 결과 수집

    [Phase 1] runtime=None으로 동작 (Context API 없이)
    [Phase 2] runtime 자동 주입됨 (Graph에 context_schema 등록 시)

    Features:
    - Todo별 동적 Agent 라우팅
    - Agent 독립 실행 및 결과 수집
    - 에러 처리 및 graceful degradation
    - Context API 확장 포인트 포함

    Args:
        state: Octostrator State
        runtime: LangGraph Runtime (optional, Phase 2)

    Returns:
        Updated state with execution results
    """
    from backend.app.octostrator.execution_agents import agent_registry

    try:
        # 1. State에서 필요한 데이터 가져오기
        todos = state.get("todos", [])
        # Phase 3: checkpointer는 State에서 제거됨
        # TODO (Step 4): Context API를 사용하여 필요시 생성
        checkpointer = None  # Phase 3: 필요시 노드에서 직접 생성
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id", "default")

        if not todos:
            logger.warning("[Execute] No todos to execute")
            return {
                "execution_results": {},
                "completed": 0,
                "failed": 0,
                "success_rate": 0.0
            }

        logger.info(f"[Execute] Starting execution for {len(todos)} todos")

        # 2. LLM 초기화 (확장 포인트 사용)
        llm = _create_llm_for_agents(runtime)

        # 3. 결과 수집 변수
        execution_results = {}
        completed = 0
        failed = 0

        # 4. Todo별 Agent 실행
        for todo in todos:
            # Skip non-pending todos
            if todo.get("status") != "pending":
                logger.debug(f"[Execute] Skipping todo {todo.get('id')} (status: {todo.get('status')})")
                continue

            agent_name = todo.get("agent")  # 예: "frontdesk_agent"
            task_description = todo.get("task")
            todo_id = todo.get("id")

            if not agent_name:
                logger.warning(f"[Execute] Todo {todo_id} has no agent assigned, skipping")
                continue

            try:
                # 4.1 Agent 가져오기 (Registry에서)
                agent_class = agent_registry.get(agent_name)
                if not agent_class:
                    raise ValueError(f"Agent '{agent_name}' not found in registry")

                logger.info(f"[Execute] Running {agent_name} for todo {todo_id}")

                # 4.2 Agent 인스턴스 생성
                agent = agent_class()

                # 4.3 Agent 초기화 (LLM + Checkpointer)
                await agent.initialize(llm=llm, checkpointer=checkpointer)

                # 4.4 Task 준비
                task = {
                    "task_id": todo_id,
                    "task_type": "todo_execution",
                    "description": task_description,
                    "todo_data": todo  # 전체 Todo 전달
                }

                context = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "parent_state": "octostrator"
                }

                # 4.5 Agent 실행
                result = await agent.execute(
                    task=task,
                    context=context,
                    thread_id=session_id  # Checkpoint용 (format: {session_id}_{agent_id})
                )

                # 4.6 결과 저장
                execution_results[todo_id] = {
                    "todo_id": todo_id,
                    "agent": agent_name,
                    "status": result.get("status", "unknown"),
                    "result": result.get("result", {}),
                    "started_at": result.get("started_at"),
                    "completed_at": result.get("completed_at"),
                    "error": result.get("error")
                }

                # 4.7 Todo 상태 업데이트
                if result.get("status") == "completed":
                    todo["status"] = "completed"
                    todo["completed_at"] = result.get("completed_at")
                    completed += 1
                    logger.info(f"[Execute] {agent_name} completed successfully for todo {todo_id}")
                else:
                    todo["status"] = "failed"
                    todo["error"] = result.get("error")
                    failed += 1
                    logger.error(f"[Execute] {agent_name} failed for todo {todo_id}: {result.get('error')}")

            except Exception as e:
                # 에러 처리: graceful degradation
                logger.error(f"[Execute] Exception while executing {agent_name}: {e}", exc_info=True)

                execution_results[todo_id] = {
                    "todo_id": todo_id,
                    "agent": agent_name,
                    "status": "failed",
                    "error": str(e),
                    "result": {}
                }

                todo["status"] = "failed"
                todo["error"] = str(e)
                failed += 1

        # 5. 실행 통계
        total_todos = len([t for t in todos if t.get("agent")])
        success_rate = completed / total_todos if total_todos > 0 else 0.0

        logger.info(
            f"[Execute] Execution completed: {completed} succeeded, {failed} failed "
            f"(success rate: {success_rate:.1%})"
        )

        # 6. State 업데이트
        return {
            "execution_results": execution_results,
            "completed": completed,
            "failed": failed,
            "success_rate": success_rate,
            "todos": todos,  # merge_todos_smart가 자동 병합
            "action_history": [{
                "action": "execute_layer_node",
                "result": {
                    "total_todos": total_todos,
                    "completed": completed,
                    "failed": failed,
                    "success_rate": success_rate
                }
            }]
        }

    except Exception as e:
        logger.error(f"[Execute] Critical error in execute_layer_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "execution_results": {},
            "completed": 0,
            "failed": 0
        }


# ====================================
# AGGREGATOR NODE
# ====================================

async def aggregator_node(
    state: Dict[str, Any],
    runtime: Optional[Runtime] = None  # ⭐ Phase 2 확장 포인트
) -> Dict[str, Any]:
    """
    Aggregator Node - 실행 결과 집계

    [Phase 1] 간단한 집계
    [Phase 2] LLM으로 인사이트 생성 (Context API 사용)

    Args:
        state: Octostrator State
        runtime: LangGraph Runtime (optional, Phase 2)

    Returns:
        Aggregated data
    """
    try:
        execution_results = state.get("execution_results", {})

        if not execution_results:
            logger.warning("[Aggregator] No execution results to aggregate")
            return {"aggregated_data": {}}

        # Phase 1: 간단한 집계
        completed_count = sum(
            1 for r in execution_results.values() if r.get("status") == "completed"
        )
        failed_count = sum(
            1 for r in execution_results.values() if r.get("status") == "failed"
        )

        aggregated = {
            "total_steps": len(execution_results),
            "completed_steps": completed_count,
            "failed_steps": failed_count,
            "results": execution_results,
            "summary": (
                f"Execution completed: {completed_count} succeeded, "
                f"{failed_count} failed"
            )
        }

        logger.info(f"[Aggregator] Aggregated {aggregated['total_steps']} results")

        # TODO Phase 2: LLM으로 인사이트 생성
        # if runtime is not None:
        #     llm = _create_llm_for_aggregator(runtime)
        #     insights = await generate_insights(llm, execution_results)
        #     aggregated["insights"] = insights

        return {"aggregated_data": aggregated}

    except Exception as e:
        logger.error(f"[Aggregator] Error: {e}")
        return {"error": str(e)}


# ====================================
# ERROR HANDLER NODE
# ====================================

async def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Error Handler Node - 실행 중 발생한 에러 처리

    Features:
    - Error categorization
    - Error reporting
    - Recovery suggestions
    """
    try:
        error = state.get("error")
        failed_steps = [
            r for r in state.get("execution_results", {}).values()
            if r.get("status") == "failed"
        ]

        if not error and not failed_steps:
            return {}  # No errors to handle

        # 에러 리포트 생성
        error_report = {
            "has_errors": True,
            "error_count": len(failed_steps),
            "errors": failed_steps,
            "recovery_action": "manual_intervention_required"
        }

        if error:
            error_report["critical_error"] = error

        logger.warning(
            f"[ErrorHandler] Handling {error_report['error_count']} errors"
        )

        return {"error_report": error_report}

    except Exception as e:
        logger.error(f"[ErrorHandler] Error in error handler: {e}")
        return {"critical_error": str(e)}
