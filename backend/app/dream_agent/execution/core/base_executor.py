"""BaseExecutor - 모든 실행기의 추상 기본 클래스

BaseBizAgentGraph 패턴을 기반으로 하며,
HITL(Human-in-the-Loop) 연동점을 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

# Type variable for executor classes
E = TypeVar("E", bound="BaseExecutor")

# Global registry for executor classes (populated by register_executor decorator)
_EXECUTOR_CLASSES: Dict[str, Type["BaseExecutor"]] = {}


class ExecutionResult:
    """실행 결과 컨테이너

    Attributes:
        success: 성공 여부
        data: 결과 데이터
        error: 에러 메시지 (실패 시)
        todo_id: 실행된 Todo ID
        execution_time: 실행 시간 (초)
        metadata: 추가 메타데이터
    """

    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        todo_id: Optional[str] = None,
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.todo_id = todo_id
        self.execution_time = execution_time
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "todo_id": self.todo_id,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class BaseExecutor(ABC):
    """모든 실행기의 추상 기본 클래스

    BaseBizAgentGraph 패턴을 기반으로 하며,
    Todo 기반 실행 및 HITL 연동을 지원합니다.

    Attributes:
        name: 실행기 고유 이름 (예: "data_executor", "content_executor")
        category: 실행기 카테고리 (data, insight, content, ops)
        supported_tools: 지원하는 도구 이름 목록
        enable_hitl: HITL 활성화 여부

    Example:
        ```python
        @register_executor("data_executor")
        class DataExecutor(BaseExecutor):
            name = "data_executor"
            category = "data"
            supported_tools = ["collector", "preprocessor", "external_api"]

            async def _execute_impl(self, todo: TodoItem, context: Dict) -> Dict:
                tool_name = todo.metadata.execution.tool
                tool = self.get_tool(tool_name)
                return tool.execute(**context)
        ```
    """

    # 클래스 속성 (서브클래스에서 오버라이드)
    name: str = "base_executor"
    category: str = "general"
    supported_tools: List[str] = []
    version: str = "1.0.0"

    def __init__(self, enable_hitl: bool = True, **kwargs):
        """실행기 초기화

        Args:
            enable_hitl: HITL 활성화 여부
            **kwargs: 추가 설정
        """
        self.enable_hitl = enable_hitl
        self._config = kwargs
        self._initialized = False
        self._decision_manager = None
        self._tool_registry = None

    def initialize(self) -> None:
        """실행기 초기화 (lazy loading)

        무거운 리소스 로딩이 필요한 경우 오버라이드합니다.
        """
        self._initialized = True

    def ensure_initialized(self) -> None:
        """초기화 보장"""
        if not self._initialized:
            self.initialize()

    @property
    def decision_manager(self):
        """DecisionManager 인스턴스 (lazy loading)"""
        if self._decision_manager is None and self.enable_hitl:
            try:
                from ...workflow_manager.hitl_manager.decision_manager import (
                    get_decision_manager,
                )
                self._decision_manager = get_decision_manager()
            except ImportError:
                logger.warning("DecisionManager not available")
        return self._decision_manager

    @property
    def tool_registry(self):
        """ToolRegistry 인스턴스 (lazy loading)"""
        if self._tool_registry is None:
            from ...tools import get_tool_registry
            self._tool_registry = get_tool_registry()
        return self._tool_registry

    def get_tool(self, name: str):
        """도구 인스턴스 가져오기

        Args:
            name: 도구 이름

        Returns:
            도구 인스턴스

        Raises:
            ValueError: 지원하지 않는 도구
        """
        if self.supported_tools and name not in self.supported_tools:
            raise ValueError(
                f"Tool '{name}' not supported by {self.name}. "
                f"Supported: {self.supported_tools}"
            )

        return self.tool_registry.get(name)

    async def execute(self, todo: Any, context: Dict[str, Any]) -> ExecutionResult:
        """Todo 실행 (HITL 포함)

        Args:
            todo: TodoItem 인스턴스
            context: 실행 컨텍스트

        Returns:
            ExecutionResult 인스턴스
        """
        self.ensure_initialized()
        start_time = datetime.now()
        todo_id = getattr(todo, "id", None)

        try:
            logger.info(f"[{self.name}] Executing todo: {todo_id}")

            # 실제 실행
            result_data = await self._execute_impl(todo, context)

            execution_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=True,
                data=result_data,
                todo_id=todo_id,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Execution failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()

            # HITL 처리
            if self.enable_hitl and self.decision_manager:
                decision = await self._request_decision(todo, e)
                return await self._handle_decision(todo, decision, context)

            return ExecutionResult(
                success=False,
                error=str(e),
                todo_id=todo_id,
                execution_time=execution_time,
            )

    @abstractmethod
    async def _execute_impl(self, todo: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """실제 실행 로직 (서브클래스에서 구현)

        Args:
            todo: TodoItem 인스턴스
            context: 실행 컨텍스트

        Returns:
            실행 결과 딕셔너리
        """
        pass

    async def _request_decision(self, todo: Any, error: Exception) -> Dict[str, Any]:
        """HITL 결정 요청

        Args:
            todo: 실패한 TodoItem
            error: 발생한 예외

        Returns:
            결정 결과 딕셔너리
        """
        if not self.decision_manager:
            return {"action": "abort", "reason": "DecisionManager not available"}

        todo_id = getattr(todo, "id", None)
        todo_task = getattr(todo, "task", str(todo))
        session_id = self._get_session_id(todo)

        # 고유한 request_id 생성
        request_id = f"exec_{self.name}_{todo_id or 'unknown'}_{uuid.uuid4().hex[:8]}"

        result = await self.decision_manager.request_decision(
            request_id=request_id,
            session_id=session_id,
            context={
                "todo_id": todo_id,
                "error": str(error),
                "error_type": type(error).__name__,
                "todo_task": todo_task,
                "executor": self.name,
                "category": self.category,
            },
            options=[
                {"value": "retry", "label": "재시도", "description": "작업을 다시 시도합니다"},
                {"value": "skip", "label": "건너뛰기", "description": "이 작업을 건너뛰고 다음으로 진행합니다"},
                {"value": "abort", "label": "중단", "description": "전체 실행을 중단합니다"},
            ],
            message=f"작업 실패: {todo_task}\n오류: {str(error)}\n\n어떻게 처리할까요?",
            timeout=300,
        )

        # 타임아웃 시 기본 abort 반환
        if result is None:
            logger.warning(f"[{self.name}] Decision timeout for todo: {todo_id}")
            return {"action": "abort", "reason": "Decision timeout"}

        return result

    async def _handle_decision(
        self,
        todo: Any,
        decision: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """HITL 결정 처리

        Args:
            todo: TodoItem 인스턴스
            decision: 결정 결과
            context: 실행 컨텍스트

        Returns:
            ExecutionResult 인스턴스
        """
        action = decision.get("action", "abort")
        todo_id = getattr(todo, "id", None)
        reason = decision.get("reason") or decision.get("data", {}).get("reason", "No reason")

        if action == "retry":
            logger.info(f"[{self.name}] Retrying todo: {todo_id}")
            # 재시도 횟수 제한 (무한 루프 방지)
            retry_count = context.get("_retry_count", 0)
            max_retries = getattr(todo, "metadata", {})
            if hasattr(max_retries, "execution"):
                max_retries = getattr(max_retries.execution, "max_retries", 3)
            else:
                max_retries = 3

            if retry_count >= max_retries:
                logger.warning(f"[{self.name}] Max retries ({max_retries}) exceeded for todo: {todo_id}")
                return ExecutionResult(
                    success=False,
                    error=f"Max retries ({max_retries}) exceeded",
                    todo_id=todo_id,
                    metadata={"decision": "abort", "retry_count": retry_count},
                )

            context["_retry_count"] = retry_count + 1
            return await self.execute(todo, context)

        elif action == "skip":
            logger.info(f"[{self.name}] Skipping todo: {todo_id}")
            return ExecutionResult(
                success=True,
                data={"skipped": True, "reason": reason},
                todo_id=todo_id,
                metadata={"decision": "skip"},
            )

        elif action == "cancel":
            logger.info(f"[{self.name}] Cancelled todo: {todo_id}")
            return ExecutionResult(
                success=False,
                error=f"Cancelled: {reason}",
                todo_id=todo_id,
                metadata={"decision": "cancel"},
            )

        else:  # abort
            logger.info(f"[{self.name}] Aborting todo: {todo_id}")
            return ExecutionResult(
                success=False,
                error=f"Aborted by user: {reason}",
                todo_id=todo_id,
                metadata={"decision": "abort"},
            )

    def _get_session_id(self, todo: Any) -> str:
        """Todo에서 세션 ID 추출"""
        # TodoItem.metadata.context.session_id 확인
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "context") and metadata.context:
                return metadata.context.get("session_id", "unknown")
        return "unknown"

    def supports_tool(self, tool_name: str) -> bool:
        """도구 지원 여부 확인

        Args:
            tool_name: 도구 이름

        Returns:
            지원 여부
        """
        if not self.supported_tools:
            return True  # 빈 리스트면 모든 도구 지원
        return tool_name in self.supported_tools

    def get_metadata(self) -> Dict[str, Any]:
        """실행기 메타데이터 반환"""
        return {
            "name": self.name,
            "category": self.category,
            "supported_tools": self.supported_tools,
            "version": self.version,
            "enable_hitl": self.enable_hitl,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', category='{self.category}')>"


def register_executor(name: str):
    """실행기 클래스 등록 데코레이터

    Args:
        name: 실행기 등록 이름

    Returns:
        데코레이터 함수

    Example:
        ```python
        @register_executor("data_executor")
        class DataExecutor(BaseExecutor):
            ...
        ```
    """
    def decorator(cls: Type[E]) -> Type[E]:
        if not issubclass(cls, BaseExecutor):
            raise TypeError(f"{cls.__name__} must inherit from BaseExecutor")

        _EXECUTOR_CLASSES[name] = cls
        logger.debug(f"Registered executor: {name} -> {cls.__name__}")
        return cls

    return decorator


def get_registered_executors() -> Dict[str, Type[BaseExecutor]]:
    """등록된 모든 실행기 클래스 반환"""
    return _EXECUTOR_CLASSES.copy()


def create_executor(name: str, **kwargs) -> BaseExecutor:
    """등록된 실행기 인스턴스 생성

    Args:
        name: 실행기 이름
        **kwargs: 실행기 초기화 파라미터

    Returns:
        실행기 인스턴스

    Raises:
        KeyError: 등록되지 않은 실행기
    """
    if name not in _EXECUTOR_CLASSES:
        raise KeyError(
            f"Executor '{name}' not registered. Available: {list(_EXECUTOR_CLASSES.keys())}"
        )

    return _EXECUTOR_CLASSES[name](**kwargs)
