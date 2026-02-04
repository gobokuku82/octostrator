"""Router - 라우팅 로직

Phase 1.6 변경사항:
- 통합 실행 레이어를 위한 route_to_execution, route_after_execution 추가
- 기존 route_after_ml_execution, route_after_biz_execution은 deprecated

Phase 3.5 변경사항:
- FAILURE_THRESHOLD 상수 추가
- calculate_failure_rate 함수 추가
- route_after_execution에 실패율 체크 로직 추가
"""

import warnings
from typing import Literal, Dict, Any
from backend.app.dream_agent.states import AgentState
from backend.app.dream_agent.states.accessors import (
    get_todos,
    get_intent,
    get_requires_hitl,
)
from backend.app.dream_agent.workflow_manager import TodoDependencyManager
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Phase 3.5 - 실패율 임계값
# ============================================================

FAILURE_THRESHOLD = 0.5  # 50% 이상 실패 시 기본 임계값

FAILURE_THRESHOLDS = {
    "warning": 0.3,     # 30% 이상: 경고 로깅
    "critical": 0.5,    # 50% 이상: 사용자 알림 권고
    "abort": 0.8,       # 80% 이상: 실행 중단 권고
}


def calculate_failure_rate(state: AgentState) -> Dict[str, Any]:
    """
    실행 레이어의 실패율 계산

    Args:
        state: 현재 상태

    Returns:
        {
            "rate": float,      # 실패율 (0.0 ~ 1.0)
            "failed": int,      # 실패한 Todo 수
            "total": int,       # 전체 실행 Todo 수
            "level": str,       # "normal" | "warning" | "critical" | "abort"
        }
    """
    all_todos = get_todos(state)

    # execution layer의 Todo만 대상 (ml_execution, biz_execution 포함)
    execution_todos = [
        t for t in all_todos
        if t.layer in ["execution", "ml_execution", "biz_execution"]
    ]

    if not execution_todos:
        return {
            "rate": 0.0,
            "failed": 0,
            "total": 0,
            "level": "normal"
        }

    failed = sum(1 for t in execution_todos if t.status == "failed")
    total = len(execution_todos)
    rate = failed / total

    # 레벨 결정
    if rate >= FAILURE_THRESHOLDS["abort"]:
        level = "abort"
    elif rate >= FAILURE_THRESHOLDS["critical"]:
        level = "critical"
    elif rate >= FAILURE_THRESHOLDS["warning"]:
        level = "warning"
    else:
        level = "normal"

    return {
        "rate": rate,
        "failed": failed,
        "total": total,
        "level": level
    }


def get_execution_health(state: AgentState) -> Dict[str, Any]:
    """
    실행 상태 건강도 요약 (Frontend 표시용)

    Args:
        state: 현재 상태

    Returns:
        {
            "status": "healthy" | "degraded" | "critical",
            "failure_rate": float,
            "completed": int,
            "failed": int,
            "pending": int,
            "message": str
        }
    """
    all_todos = get_todos(state)
    execution_todos = [
        t for t in all_todos
        if t.layer in ["execution", "ml_execution", "biz_execution"]
    ]

    if not execution_todos:
        return {
            "status": "healthy",
            "failure_rate": 0.0,
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "message": "No execution todos"
        }

    completed = sum(1 for t in execution_todos if t.status == "completed")
    failed = sum(1 for t in execution_todos if t.status == "failed")
    pending = sum(1 for t in execution_todos if t.status in ["pending", "in_progress"])
    total = len(execution_todos)

    failure_rate = failed / total if total > 0 else 0

    if failure_rate >= FAILURE_THRESHOLDS["critical"]:
        status = "critical"
        message = f"{failure_rate:.0%} 실패율: 실행 중단 권고"
    elif failure_rate >= FAILURE_THRESHOLDS["warning"]:
        status = "degraded"
        message = f"{failure_rate:.0%} 실패율: 주의 필요"
    else:
        status = "healthy"
        message = f"{completed}/{total} 완료"

    return {
        "status": status,
        "failure_rate": failure_rate,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "message": message
    }


# ============================================================
# Phase 1.6 - 통합 실행 레이어 라우팅
# ============================================================

def route_to_execution(
    state: AgentState,
) -> Literal["execution", "response", "END"]:
    """
    Planning 이후 통합 실행 노드로 라우팅 (Phase 1.6+)

    동작:
    - 실행 가능한(ready) todos가 있으면 execution으로
    - 없으면 response로

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    try:
        logger.info("[router] route_to_execution called")

        todos = get_todos(state)
        logger.info(f"[router] Total todos in state: {len(todos)}")

        for t in todos:
            deps = "N/A"
            if hasattr(t, 'metadata') and hasattr(t.metadata, 'dependency'):
                deps = t.metadata.dependency.depends_on
            logger.info(f"[router] Todo: task={t.task}, layer={t.layer}, status={t.status}, depends_on={deps}")

        ready_todos = TodoDependencyManager.get_ready_todos(todos)
        logger.info(f"[router] Ready todos (pending + deps met): {len(ready_todos)}")

        if ready_todos:
            logger.info("[router] Routing to execution")
            return "execution"

        # Fallback: intent 플래그 확인
        intent = get_intent(state)
        requires_ml = intent.get("requires_ml", False)
        requires_biz = intent.get("requires_biz", False)
        logger.info(f"[router] Intent fallback: requires_ml={requires_ml}, requires_biz={requires_biz}")

        if requires_ml or requires_biz:
            logger.info("[router] Routing to execution via intent fallback")
            return "execution"

        logger.info("[router] No ready todos - routing to response")
        return "response"

    except Exception as e:
        logger.error(f"[router] route_to_execution error: {e}", exc_info=True)
        # 에러 시 response로 fallback
        return "response"


def route_after_execution(
    state: AgentState,
) -> Literal["execution", "response"]:
    """
    통합 실행 노드 이후 라우팅 (Phase 1.6+)

    Phase 3.5 추가:
    - 실패율 체크 및 로깅

    동작:
    - 실행 가능한(ready) todos가 더 있으면 execution (루프)
    - 없으면 response로

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    todos = get_todos(state)
    ready_todos = TodoDependencyManager.get_ready_todos(todos)

    # =========================================================================
    # Phase 3.5: 실패율 체크
    # =========================================================================
    failure_stats = calculate_failure_rate(state)

    if failure_stats["level"] == "abort":
        logger.error(
            f"[router] 실행 실패율 {failure_stats['rate']:.0%} "
            f"({failure_stats['failed']}/{failure_stats['total']}) - ABORT 권고"
        )
        # 심각한 상황이지만 response로 이동하여 사용자에게 알림
        # TODO: HITL로 전환하여 사용자에게 중단 여부 확인

    elif failure_stats["level"] == "critical":
        logger.warning(
            f"[router] 실행 실패율 {failure_stats['rate']:.0%} "
            f"({failure_stats['failed']}/{failure_stats['total']}) - CRITICAL"
        )

    elif failure_stats["level"] == "warning":
        logger.warning(
            f"[router] 실행 실패율 {failure_stats['rate']:.0%} "
            f"({failure_stats['failed']}/{failure_stats['total']}) - WARNING"
        )

    # =========================================================================
    # 기존 라우팅 로직
    # =========================================================================
    logger.info(f"[router] After execution - Ready todos: {len(ready_todos)}")

    if ready_todos:
        return "execution"

    return "response"


# ============================================================
# Legacy - Phase 1.5 이전 (Deprecated)
# ============================================================


def route_after_planning(
    state: AgentState,
) -> Literal["ml_execution", "biz_execution", "response", "END"]:
    """
    Planning 이후 라우팅

    .. deprecated:: Phase 1.6
        Use :func:`route_to_execution` instead for unified execution layer.

    동작:
    - 우선: Planning이 생성한 todos 확인 (실제 계획)
    - 차선: intent의 requires_ml/requires_biz 플래그 확인
    - ML todos 있으면 ml_execution으로
    - Biz만 있으면 biz_execution으로
    - 둘 다 없으면 response로

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    warnings.warn(
        "route_after_planning is deprecated. Use route_to_execution for unified execution layer.",
        DeprecationWarning,
        stacklevel=2
    )
    # 1. 먼저 Planning이 생성한 todos 확인 (가장 정확함)
    # 의존성이 충족된 실행 가능한 todos만 확인
    todos = get_todos(state)

    # DEBUG: todos 상태 로깅
    logger.info(f"[router] Total todos in state: {len(todos)}")
    for t in todos:
        logger.info(f"[router] Todo: {t.task}, layer={t.layer}, status={t.status}")

    ready_todos = TodoDependencyManager.get_ready_todos(todos)
    logger.info(f"[router] Ready todos (pending + deps met): {len(ready_todos)}")

    # 레이어별로 필터링
    ml_ready = [t for t in ready_todos if t.layer == "ml_execution"]
    biz_ready = [t for t in ready_todos if t.layer == "biz_execution"]

    logger.info(f"[router] ML ready: {len(ml_ready)}, Biz ready: {len(biz_ready)}")

    # ML todos가 있으면 ML 실행
    if ml_ready:
        logger.info("[router] Routing to ml_execution")
        return "ml_execution"

    # Biz todos가 있으면 Biz 실행 (ML 없이)
    if biz_ready:
        return "biz_execution"

    # 2. Todos가 없으면 intent 플래그 확인 (fallback)
    intent = get_intent(state)
    requires_ml = intent.get("requires_ml", False)
    requires_biz = intent.get("requires_biz", False)

    if requires_ml:
        return "ml_execution"

    if requires_biz:
        return "biz_execution"

    # 둘 다 필요 없으면 바로 응답
    logger.info("[router] No ready todos and no intent flags - routing to response")
    return "response"


def route_after_ml_execution(
    state: AgentState,
) -> Literal["ml_execution", "biz_execution", "response"]:
    """
    ML Execution 이후 라우팅

    .. deprecated:: Phase 1.6
        Use :func:`route_after_execution` instead for unified execution layer.

    동작:
    - ML 레이어의 pending todos가 있으면 계속 ml_execution
    - ML 완료 후 Biz todos 있거나 requires_biz이면 biz_execution
    - 모두 완료면 response

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    warnings.warn(
        "route_after_ml_execution is deprecated. Use route_after_execution for unified execution layer.",
        DeprecationWarning,
        stacklevel=2
    )
    todos = get_todos(state)
    ready_todos = TodoDependencyManager.get_ready_todos(todos)

    # 레이어별로 필터링
    ml_ready = [t for t in ready_todos if t.layer == "ml_execution"]
    biz_ready = [t for t in ready_todos if t.layer == "biz_execution"]

    # ML 레이어에 실행 가능한 작업이 있으면 계속 실행
    if ml_ready:
        return "ml_execution"

    # ML 완료 후 Biz 필요 여부 확인
    # 1. Biz todos 확인 (우선)
    if biz_ready:
        return "biz_execution"

    # 2. intent 플래그 확인 (fallback)
    intent = get_intent(state)
    requires_biz = intent.get("requires_biz", False)
    if requires_biz:
        return "biz_execution"

    # 모두 완료
    return "response"


def route_after_biz_execution(
    state: AgentState,
) -> Literal["biz_execution", "response"]:
    """
    Biz Execution 이후 라우팅

    .. deprecated:: Phase 1.6
        Use :func:`route_after_execution` instead for unified execution layer.

    동작:
    - Biz 레이어의 pending todos가 있으면 계속 biz_execution
    - 완료되면 response

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    warnings.warn(
        "route_after_biz_execution is deprecated. Use route_after_execution for unified execution layer.",
        DeprecationWarning,
        stacklevel=2
    )
    todos = get_todos(state)
    ready_todos = TodoDependencyManager.get_ready_todos(todos)

    # 레이어별로 필터링
    biz_ready = [t for t in ready_todos if t.layer == "biz_execution"]

    # Biz 레이어에 실행 가능한 작업이 있으면 계속 실행
    if biz_ready:
        return "biz_execution"

    # 모두 완료
    return "response"


def route_after_response(
    state: AgentState,
) -> Literal["END"]:
    """
    Response 이후 라우팅

    항상 END로 종료

    Args:
        state: 현재 상태

    Returns:
        "END"
    """
    return "END"


def should_continue_hitl(
    state: AgentState,
) -> Literal["human_review", "continue"]:
    """
    HITL(Human-In-The-Loop) 필요 여부 판단

    Args:
        state: 현재 상태

    Returns:
        "human_review" 또는 "continue"
    """
    if get_requires_hitl(state):
        return "human_review"

    return "continue"
