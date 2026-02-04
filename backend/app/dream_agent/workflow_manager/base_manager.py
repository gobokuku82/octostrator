"""
BaseManager - Manager 추상 클래스

목적:
- 모든 Manager 클래스의 공통 인터페이스 정의
- 초기화/종료 라이프사이클 표준화
- 상태 모니터링 및 헬스체크 기능 제공
- 동기/비동기 Manager 모두 지원

사용법:
    class MyManager(BaseManager):
        name = "my_manager"
        version = "1.0.0"

        def _do_initialize(self) -> None:
            # 초기화 로직
            pass

        def validate(self) -> Dict[str, Any]:
            return {"valid": True}

비동기 Manager:
    class MyAsyncManager(AsyncBaseManager):
        name = "my_async_manager"

        async def _do_initialize_async(self) -> None:
            # 비동기 초기화 로직
            pass
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypeVar, Generic
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class ManagerStatus(Enum):
    """Manager 상태"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"
    DEGRADED = "degraded"  # 일부 기능만 동작


@dataclass
class ManagerHealth:
    """Manager 헬스체크 결과"""
    name: str
    status: ManagerStatus
    version: str
    initialized_at: Optional[str] = None
    last_health_check: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "version": self.version,
            "initialized_at": self.initialized_at,
            "last_health_check": self.last_health_check,
            "error": self.error,
            "details": self.details,
        }


class BaseManager(ABC):
    """
    동기 Manager 베이스 클래스

    모든 동기 Manager는 이 클래스를 상속해야 합니다.

    Attributes:
        name: Manager 이름 (로깅/디버깅용)
        version: Manager 버전

    Methods to Override:
        _do_initialize(): 초기화 로직 구현
        _do_shutdown(): 종료 로직 구현 (선택)
        validate(): 상태 검증 로직 구현 (필수)
    """

    name: str = "base_manager"
    version: str = "1.0.0"

    def __init__(self, name: Optional[str] = None):
        if name:
            self.name = name
        self._status = ManagerStatus.UNINITIALIZED
        self._error: Optional[str] = None
        self._initialized_at: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None
        self._health_details: Dict[str, Any] = {}

    @property
    def status(self) -> ManagerStatus:
        """현재 Manager 상태"""
        return self._status

    @property
    def is_ready(self) -> bool:
        """Manager가 사용 가능한 상태인지"""
        return self._status in (ManagerStatus.READY, ManagerStatus.DEGRADED)

    @property
    def is_healthy(self) -> bool:
        """Manager가 정상 상태인지"""
        return self._status == ManagerStatus.READY

    def initialize(self) -> None:
        """
        Manager 초기화

        서브클래스에서 _do_initialize()를 구현하여 사용합니다.

        Raises:
            Exception: 초기화 실패 시
        """
        if self._status == ManagerStatus.READY:
            logger.debug(f"{self.name} already initialized")
            return

        self._status = ManagerStatus.INITIALIZING
        logger.info(f"Initializing {self.name}...")

        try:
            self._do_initialize()
            self._status = ManagerStatus.READY
            self._initialized_at = datetime.now()
            logger.info(f"{self.name} initialized successfully")
        except Exception as e:
            self._status = ManagerStatus.ERROR
            self._error = str(e)
            logger.error(f"{self.name} initialization failed: {e}", exc_info=True)
            raise

    def _do_initialize(self) -> None:
        """
        실제 초기화 로직 (서브클래스에서 구현)

        기본 구현은 아무것도 하지 않습니다.
        """
        pass

    def shutdown(self) -> None:
        """
        Manager 종료

        서브클래스에서 _do_shutdown()을 구현하여 리소스를 정리합니다.
        """
        if self._status == ManagerStatus.SHUTDOWN:
            logger.debug(f"{self.name} already shutdown")
            return

        logger.info(f"Shutting down {self.name}...")

        try:
            self._do_shutdown()
            self._status = ManagerStatus.SHUTDOWN
            logger.info(f"{self.name} shutdown completed")
        except Exception as e:
            logger.error(f"{self.name} shutdown failed: {e}", exc_info=True)
            self._error = str(e)
            raise

    def _do_shutdown(self) -> None:
        """
        실제 종료 로직 (서브클래스에서 구현)

        기본 구현은 아무것도 하지 않습니다.
        """
        pass

    def health_check(self) -> ManagerHealth:
        """
        Manager 상태 확인

        Returns:
            ManagerHealth: 헬스체크 결과
        """
        self._last_health_check = datetime.now()

        # 서브클래스의 validate() 결과 반영
        try:
            validation = self.validate()
            if not validation.get("valid", True):
                self._health_details["validation_errors"] = validation.get("errors", [])
        except Exception as e:
            self._health_details["validation_error"] = str(e)

        return ManagerHealth(
            name=self.name,
            status=self._status,
            version=self.version,
            initialized_at=self._initialized_at.isoformat() if self._initialized_at else None,
            last_health_check=self._last_health_check.isoformat() if self._last_health_check else None,
            error=self._error,
            details=self._health_details.copy(),
        )

    @abstractmethod
    def validate(self) -> Dict[str, Any]:
        """
        Manager 상태 검증 (서브클래스에서 구현 필수)

        Returns:
            Dict with at least:
                - valid: bool - 유효한 상태인지
                - errors: List[str] - 에러 목록 (선택)
                - warnings: List[str] - 경고 목록 (선택)
        """
        raise NotImplementedError("Subclass must implement validate()")

    def require_ready(self) -> None:
        """
        Manager가 준비 상태인지 확인하고, 아니면 예외 발생

        Raises:
            RuntimeError: Manager가 준비되지 않은 경우
        """
        if not self.is_ready:
            raise RuntimeError(
                f"{self.name} is not ready (status: {self._status.value}). "
                f"Call initialize() first."
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} status={self._status.value}>"


class AsyncBaseManager(BaseManager):
    """
    비동기 Manager 베이스 클래스

    비동기 초기화/종료가 필요한 Manager는 이 클래스를 상속합니다.

    Methods to Override:
        _do_initialize_async(): 비동기 초기화 로직 구현
        _do_shutdown_async(): 비동기 종료 로직 구현 (선택)
        validate(): 상태 검증 로직 구현 (필수)

    Example:
        class MyAsyncManager(AsyncBaseManager):
            name = "my_async_manager"

            async def _do_initialize_async(self) -> None:
                await self._connect_to_database()

            async def _do_shutdown_async(self) -> None:
                await self._disconnect_from_database()

            def validate(self) -> Dict[str, Any]:
                return {"valid": self._db_connected}
    """

    async def initialize_async(self) -> None:
        """
        비동기 Manager 초기화

        Raises:
            Exception: 초기화 실패 시
        """
        if self._status == ManagerStatus.READY:
            logger.debug(f"{self.name} already initialized")
            return

        self._status = ManagerStatus.INITIALIZING
        logger.info(f"Initializing {self.name} (async)...")

        try:
            await self._do_initialize_async()
            self._status = ManagerStatus.READY
            self._initialized_at = datetime.now()
            logger.info(f"{self.name} initialized successfully (async)")
        except Exception as e:
            self._status = ManagerStatus.ERROR
            self._error = str(e)
            logger.error(f"{self.name} async initialization failed: {e}", exc_info=True)
            raise

    async def _do_initialize_async(self) -> None:
        """
        비동기 초기화 로직 (서브클래스에서 구현)

        기본 구현은 동기 버전을 호출합니다.
        """
        self._do_initialize()

    async def shutdown_async(self) -> None:
        """
        비동기 Manager 종료
        """
        if self._status == ManagerStatus.SHUTDOWN:
            logger.debug(f"{self.name} already shutdown")
            return

        logger.info(f"Shutting down {self.name} (async)...")

        try:
            await self._do_shutdown_async()
            self._status = ManagerStatus.SHUTDOWN
            logger.info(f"{self.name} shutdown completed (async)")
        except Exception as e:
            logger.error(f"{self.name} async shutdown failed: {e}", exc_info=True)
            self._error = str(e)
            raise

    async def _do_shutdown_async(self) -> None:
        """
        비동기 종료 로직 (서브클래스에서 구현)

        기본 구현은 동기 버전을 호출합니다.
        """
        self._do_shutdown()


# Type variable for Generic Manager
T = TypeVar('T')


class StatefulManager(BaseManager, Generic[T]):
    """
    상태를 가지는 Manager 베이스 클래스

    내부 상태를 관리하고 직렬화/역직렬화를 지원합니다.

    Example:
        class SessionManager(StatefulManager[Dict[str, Session]]):
            name = "session_manager"

            def _get_initial_state(self) -> Dict[str, Session]:
                return {}

            def _serialize_state(self, state: Dict[str, Session]) -> Dict[str, Any]:
                return {k: v.to_dict() for k, v in state.items()}

            def _deserialize_state(self, data: Dict[str, Any]) -> Dict[str, Session]:
                return {k: Session.from_dict(v) for k, v in data.items()}
    """

    def __init__(self):
        super().__init__()
        self._state: Optional[T] = None

    @property
    def state(self) -> T:
        """현재 상태"""
        if self._state is None:
            self._state = self._get_initial_state()
        return self._state

    def _get_initial_state(self) -> T:
        """
        초기 상태 반환 (서브클래스에서 구현)
        """
        raise NotImplementedError("Subclass must implement _get_initial_state()")

    def _serialize_state(self, state: T) -> Dict[str, Any]:
        """
        상태 직렬화 (서브클래스에서 구현)
        """
        raise NotImplementedError("Subclass must implement _serialize_state()")

    def _deserialize_state(self, data: Dict[str, Any]) -> T:
        """
        상태 역직렬화 (서브클래스에서 구현)
        """
        raise NotImplementedError("Subclass must implement _deserialize_state()")

    def export_state(self) -> Dict[str, Any]:
        """상태 내보내기"""
        return self._serialize_state(self.state)

    def import_state(self, data: Dict[str, Any]) -> None:
        """상태 가져오기"""
        self._state = self._deserialize_state(data)

    def reset_state(self) -> None:
        """상태 초기화"""
        self._state = self._get_initial_state()


# Convenience functions

def require_manager_ready(manager: BaseManager) -> None:
    """
    Manager가 준비 상태인지 확인하는 유틸리티 함수

    Args:
        manager: 확인할 Manager

    Raises:
        RuntimeError: Manager가 준비되지 않은 경우
    """
    manager.require_ready()


def get_manager_status_summary(managers: List[BaseManager]) -> Dict[str, Any]:
    """
    여러 Manager의 상태 요약

    Args:
        managers: Manager 리스트

    Returns:
        상태 요약 딕셔너리
    """
    summary = {
        "total": len(managers),
        "ready": 0,
        "error": 0,
        "uninitialized": 0,
        "managers": {}
    }

    for manager in managers:
        status = manager.status.value
        if manager.is_ready:
            summary["ready"] += 1
        elif manager.status == ManagerStatus.ERROR:
            summary["error"] += 1
        elif manager.status == ManagerStatus.UNINITIALIZED:
            summary["uninitialized"] += 1

        summary["managers"][manager.name] = status

    summary["healthy"] = summary["ready"] == summary["total"]

    return summary
