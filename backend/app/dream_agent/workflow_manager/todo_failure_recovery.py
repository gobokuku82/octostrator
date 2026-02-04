"""Todo Failure Recovery - LLM 에러 복구 폴백 로직

Todo 실행 실패 시 자동 복구를 시도합니다.

복구 전략:
1. RETRY: 단순 재시도 (일시적 오류)
2. ADJUST_PARAMS: LLM으로 파라미터 수정 후 재시도
3. FALLBACK: 폴백 방식 사용 (캐시 등)
4. HITL: 사용자 개입 요청
"""

import re
import json
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

if TYPE_CHECKING:
    from ..models.todo import TodoItem

logger = logging.getLogger(__name__)


class RecoveryStrategy(str, Enum):
    """복구 전략"""
    RETRY = "retry"                    # 단순 재시도
    ADJUST_PARAMS = "adjust_params"    # 파라미터 조정 후 재시도
    FALLBACK = "fallback"              # 폴백 방식 사용
    HITL = "hitl"                      # 사용자 개입 요청
    SKIP = "skip"                      # 건너뛰기


class ErrorCategory(str, Enum):
    """에러 카테고리"""
    TRANSIENT = "transient"            # 일시적 오류 (timeout, rate limit)
    PARAMETER = "parameter"            # 파라미터 오류
    CONNECTION = "connection"          # 연결 오류
    RESOURCE = "resource"              # 리소스 부족
    PERMISSION = "permission"          # 권한 오류
    LOGIC = "logic"                    # 로직 오류
    UNKNOWN = "unknown"                # 알 수 없는 오류


@dataclass
class RecoveryResult:
    """복구 결과"""
    success: bool
    strategy: RecoveryStrategy
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy.value,
            "data": self.data,
            "error": self.error,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RecoveryHistory:
    """복구 이력"""
    todo_id: str
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    def add_attempt(self, result: RecoveryResult) -> None:
        self.attempts.append(result.to_dict())

    def get_total_attempts(self) -> int:
        return len(self.attempts)


class TodoFailureRecovery:
    """
    Todo 실패 복구 관리자

    Todo 실행 실패 시 자동 복구를 시도합니다.
    - 일시적 오류: 단순 재시도
    - 파라미터 오류: LLM으로 수정 시도
    - 기타 오류: HITL로 전환
    """

    # 에러 키워드 → 카테고리 매핑
    ERROR_KEYWORDS = {
        ErrorCategory.TRANSIENT: [
            "timeout", "rate limit", "503", "429", "temporarily",
            "unavailable", "overloaded", "retry later"
        ],
        ErrorCategory.PARAMETER: [
            "invalid", "parameter", "argument", "missing", "format",
            "validation", "required", "type error"
        ],
        ErrorCategory.CONNECTION: [
            "connection", "network", "dns", "socket", "refused",
            "unreachable", "reset"
        ],
        ErrorCategory.RESOURCE: [
            "memory", "disk", "quota", "limit exceeded", "out of"
        ],
        ErrorCategory.PERMISSION: [
            "permission", "denied", "unauthorized", "forbidden", "401", "403"
        ],
        ErrorCategory.LOGIC: [
            "assertion", "value error", "key error", "index error"
        ],
    }

    # 카테고리 → 전략 매핑
    CATEGORY_STRATEGIES = {
        ErrorCategory.TRANSIENT: RecoveryStrategy.RETRY,
        ErrorCategory.PARAMETER: RecoveryStrategy.ADJUST_PARAMS,
        ErrorCategory.CONNECTION: RecoveryStrategy.FALLBACK,
        ErrorCategory.RESOURCE: RecoveryStrategy.HITL,
        ErrorCategory.PERMISSION: RecoveryStrategy.HITL,
        ErrorCategory.LOGIC: RecoveryStrategy.HITL,
        ErrorCategory.UNKNOWN: RecoveryStrategy.HITL,
    }

    def __init__(self, llm_client=None, max_retries: int = 3):
        """
        Args:
            llm_client: LLM 클라이언트 (파라미터 수정용)
            max_retries: 최대 재시도 횟수
        """
        self.llm_client = llm_client
        self.max_retries = max_retries
        self._retry_counts: Dict[str, int] = {}
        self._histories: Dict[str, RecoveryHistory] = {}

    async def attempt_recovery(
        self,
        todo: "TodoItem",
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """
        실패한 Todo 복구 시도

        Args:
            todo: 실패한 TodoItem
            error: 발생한 에러
            context: 추가 컨텍스트

        Returns:
            RecoveryResult
        """
        todo_id = todo.id
        self._retry_counts[todo_id] = self._retry_counts.get(todo_id, 0) + 1
        current_retry = self._retry_counts[todo_id]

        # 이력 초기화
        if todo_id not in self._histories:
            self._histories[todo_id] = RecoveryHistory(todo_id=todo_id)

        logger.info(
            f"[Recovery] Attempt {current_retry}/{self.max_retries} "
            f"for todo {todo_id}: {error}"
        )

        # 재시도 횟수 초과
        if current_retry > self.max_retries:
            logger.warning(f"[Recovery] Max retries exceeded for {todo_id}")
            result = RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.HITL,
                error=f"Max retries ({self.max_retries}) exceeded",
                retry_count=current_retry
            )
            self._histories[todo_id].add_attempt(result)
            return result

        # 에러 분류
        category = self._categorize_error(error)
        logger.debug(f"[Recovery] Error category: {category.value}")

        # 전략 선택 및 실행
        strategy = self.CATEGORY_STRATEGIES.get(category, RecoveryStrategy.HITL)
        result = await self._execute_strategy(todo, error, strategy, context)
        result.retry_count = current_retry

        # 이력 기록
        self._histories[todo_id].add_attempt(result)

        return result

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """에러 유형 분류"""
        error_str = str(error).lower()

        for category, keywords in self.ERROR_KEYWORDS.items():
            if any(kw in error_str for kw in keywords):
                return category

        return ErrorCategory.UNKNOWN

    async def _execute_strategy(
        self,
        todo: "TodoItem",
        error: Exception,
        strategy: RecoveryStrategy,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """전략 실행"""

        if strategy == RecoveryStrategy.RETRY:
            return RecoveryResult(
                success=True,
                strategy=strategy,
                data={"action": "retry_same"}
            )

        elif strategy == RecoveryStrategy.ADJUST_PARAMS:
            adjusted_params = await self._auto_correct_with_llm(todo, error)
            if adjusted_params:
                return RecoveryResult(
                    success=True,
                    strategy=strategy,
                    data={"adjusted_params": adjusted_params}
                )
            else:
                # LLM 수정 실패 → HITL로 전환
                return RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.HITL,
                    error="Auto-correction failed"
                )

        elif strategy == RecoveryStrategy.FALLBACK:
            fallback_result = await self._try_fallback(todo, error, context)
            return fallback_result

        elif strategy == RecoveryStrategy.SKIP:
            return RecoveryResult(
                success=True,
                strategy=strategy,
                data={"action": "skip", "reason": str(error)}
            )

        else:  # HITL
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.HITL,
                error=str(error)
            )

    async def _auto_correct_with_llm(
        self,
        todo: "TodoItem",
        error: Exception
    ) -> Optional[Dict[str, Any]]:
        """
        LLM으로 파라미터 자동 수정 시도 (다단계 폴백)

        Returns:
            수정된 파라미터 dict, 실패 시 None
        """
        if self.llm_client is None:
            logger.warning("[Recovery] LLM client not available for auto-correction")
            return None

        # 현재 파라미터 추출
        current_params = {}
        tool_name = None
        if todo.metadata and todo.metadata.execution:
            current_params = todo.metadata.execution.tool_params or {}
            tool_name = todo.metadata.execution.tool

        prompt = f"""다음 에러를 해결하기 위해 파라미터를 수정해주세요.

에러: {error}

현재 Todo:
- 내용: {todo.content if hasattr(todo, 'content') else todo.task}
- Tool: {tool_name or 'None'}
- 파라미터: {json.dumps(current_params, ensure_ascii=False, indent=2)}

수정된 파라미터를 JSON 형식으로만 반환해주세요.
"""

        # 1차: JSON 모드로 LLM 호출
        try:
            if hasattr(self.llm_client, 'chat_json'):
                response = await self.llm_client.chat_json(prompt)
                if isinstance(response, dict):
                    logger.info("[Recovery] Auto-correction successful (JSON mode)")
                    return response
        except Exception as e:
            logger.warning(f"[Recovery] LLM JSON mode failed: {e}")

        # 2차: 일반 호출 후 JSON 추출
        try:
            if hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat(prompt)
                extracted = self._extract_json_from_response(response)
                if extracted:
                    logger.info("[Recovery] Auto-correction successful (text extraction)")
                    return extracted

        except Exception as e:
            logger.warning(f"[Recovery] JSON extraction failed: {e}")

        # 3차: 실패 → None 반환 (호출부에서 HITL로 전환)
        logger.error("[Recovery] Auto-correction failed")
        return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON 추출"""
        try:
            # JSON 블록 추출 시도
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 중괄호 추출 시도
            brace_match = re.search(r'\{[^{}]*\}', response)
            if brace_match:
                return json.loads(brace_match.group())

        except json.JSONDecodeError:
            pass

        return None

    async def _try_fallback(
        self,
        todo: "TodoItem",
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """폴백 방식 시도"""
        # 캐시에서 이전 결과 조회
        if context:
            cached_result = context.get("execution_cache", {})
            tool_name = None
            if todo.metadata and todo.metadata.execution:
                tool_name = todo.metadata.execution.tool

            if tool_name and tool_name in cached_result:
                logger.info(f"[Recovery] Using cached result for {tool_name}")
                return RecoveryResult(
                    success=True,
                    strategy=RecoveryStrategy.FALLBACK,
                    data={
                        "action": "use_cache",
                        "cached_result": cached_result[tool_name]
                    }
                )

        # 폴백 불가
        logger.warning(f"[Recovery] Fallback not available for todo {todo.id}")
        return RecoveryResult(
            success=False,
            strategy=RecoveryStrategy.FALLBACK,
            error="No fallback available"
        )

    def reset_retry_count(self, todo_id: str) -> None:
        """재시도 횟수 리셋"""
        if todo_id in self._retry_counts:
            del self._retry_counts[todo_id]
        logger.debug(f"[Recovery] Retry count reset for {todo_id}")

    def get_retry_count(self, todo_id: str) -> int:
        """현재 재시도 횟수 반환"""
        return self._retry_counts.get(todo_id, 0)

    def get_history(self, todo_id: str) -> Optional[RecoveryHistory]:
        """복구 이력 반환"""
        return self._histories.get(todo_id)

    def get_all_histories(self) -> Dict[str, RecoveryHistory]:
        """모든 복구 이력 반환"""
        return self._histories.copy()

    def get_summary(self) -> Dict[str, Any]:
        """복구 요약 정보"""
        total_attempts = sum(
            h.get_total_attempts()
            for h in self._histories.values()
        )
        unique_todos = len(self._histories)

        strategy_counts: Dict[str, int] = {}
        success_count = 0
        for history in self._histories.values():
            for attempt in history.attempts:
                strategy = attempt.get("strategy", "unknown")
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                if attempt.get("success"):
                    success_count += 1

        return {
            "unique_todos_with_failures": unique_todos,
            "total_recovery_attempts": total_attempts,
            "successful_recoveries": success_count,
            "success_rate": success_count / total_attempts if total_attempts > 0 else 0.0,
            "strategy_distribution": strategy_counts,
        }


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

_recovery_manager: Optional[TodoFailureRecovery] = None


def get_failure_recovery(llm_client=None) -> TodoFailureRecovery:
    """
    TodoFailureRecovery 인스턴스 반환

    Args:
        llm_client: LLM 클라이언트 (최초 생성 시에만 사용)

    Returns:
        TodoFailureRecovery 인스턴스
    """
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = TodoFailureRecovery(llm_client)
    elif llm_client and _recovery_manager.llm_client is None:
        _recovery_manager.llm_client = llm_client
    return _recovery_manager


def reset_failure_recovery() -> None:
    """TodoFailureRecovery 초기화 (테스트용)"""
    global _recovery_manager
    _recovery_manager = None
