"""
Manager Registry - Manager 중앙 등록 및 관리

목적:
- 모든 Manager의 중앙 등록/관리
- 의존성 기반 초기화 순서 제어 (위상 정렬)
- 상태 모니터링 및 헬스체크
- 동기/비동기 Manager 통합 지원

사용법:
    from backend.app.dream_agent.workflow_manager import (
        manager_registry, get_manager
    )

    # Manager 등록
    manager_registry.register(
        "todo_manager",
        TodoManager(),
        depends_on=["config_manager"]
    )

    # 모든 Manager 초기화
    await manager_registry.initialize_all()

    # Manager 조회
    todo_mgr = get_manager("todo_manager")

    # 헬스체크
    health = await manager_registry.health_check_all()
"""

from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
import logging
import asyncio

from .base_manager import (
    BaseManager,
    AsyncBaseManager,
    ManagerStatus,
    ManagerHealth,
)

logger = logging.getLogger(__name__)


class RegistryStatus(Enum):
    """Registry 상태"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    PARTIAL = "partial"  # 일부 Manager만 초기화됨
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class RegistryHealth:
    """Registry 헬스체크 결과"""
    status: RegistryStatus
    total_managers: int
    initialized_managers: int
    failed_managers: int
    manager_health: Dict[str, ManagerHealth] = field(default_factory=dict)
    last_check: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "total_managers": self.total_managers,
            "initialized_managers": self.initialized_managers,
            "failed_managers": self.failed_managers,
            "manager_health": {
                name: health.to_dict()
                for name, health in self.manager_health.items()
            },
            "last_check": self.last_check,
            "errors": self.errors,
        }


class ManagerRegistry:
    """
    Manager 중앙 레지스트리 (싱글톤)

    모든 Manager의 등록, 초기화, 종료, 상태 관리를 담당합니다.

    Features:
    - 의존성 기반 초기화 순서 (위상 정렬)
    - 동기/비동기 Manager 통합 지원
    - 상태 모니터링 및 헬스체크
    - 싱글톤 패턴으로 전역 접근
    """

    _instance: Optional["ManagerRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._managers: Dict[str, BaseManager] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._initialization_order: List[str] = []
        self._status = RegistryStatus.UNINITIALIZED
        self._errors: List[str] = []
        self._initialized = True

        logger.debug("ManagerRegistry initialized")

    @property
    def status(self) -> RegistryStatus:
        """현재 Registry 상태"""
        return self._status

    @property
    def is_ready(self) -> bool:
        """Registry가 사용 가능한 상태인지"""
        return self._status in (RegistryStatus.READY, RegistryStatus.PARTIAL)

    def register(
        self,
        name: str,
        manager: BaseManager,
        depends_on: Optional[List[str]] = None
    ) -> None:
        """
        Manager 인스턴스 등록

        Args:
            name: Manager 식별자
            manager: Manager 인스턴스
            depends_on: 의존하는 Manager 이름 목록

        Raises:
            ValueError: 이미 등록된 이름이거나 유효하지 않은 의존성
        """
        if name in self._managers:
            raise ValueError(f"Manager '{name}' is already registered")

        self._managers[name] = manager
        self._dependencies[name] = depends_on or []

        # 초기화 순서 재계산 필요
        self._initialization_order = []

        logger.info(f"Registered manager: {name} (depends_on: {depends_on or 'none'})")

    def unregister(self, name: str) -> Optional[BaseManager]:
        """
        Manager 등록 해제

        Args:
            name: Manager 식별자

        Returns:
            제거된 Manager 인스턴스 (없으면 None)
        """
        manager = self._managers.pop(name, None)
        self._dependencies.pop(name, None)

        if manager:
            self._initialization_order = []
            logger.info(f"Unregistered manager: {name}")

        return manager

    def get(self, name: str) -> Optional[BaseManager]:
        """
        Manager 인스턴스 조회

        Args:
            name: Manager 식별자

        Returns:
            Manager 인스턴스 (없으면 None)
        """
        return self._managers.get(name)

    def get_or_raise(self, name: str) -> BaseManager:
        """
        Manager 인스턴스 조회 (없으면 예외)

        Args:
            name: Manager 식별자

        Returns:
            Manager 인스턴스

        Raises:
            KeyError: Manager가 등록되지 않음
        """
        manager = self._managers.get(name)
        if manager is None:
            raise KeyError(f"Manager '{name}' is not registered")
        return manager

    def list_managers(self) -> List[str]:
        """등록된 Manager 목록"""
        return list(self._managers.keys())

    def get_dependencies(self, name: str) -> List[str]:
        """특정 Manager의 의존성 목록"""
        return self._dependencies.get(name, [])

    def _compute_initialization_order(self) -> List[str]:
        """
        의존성 기반 초기화 순서 계산 (위상 정렬)

        Returns:
            초기화 순서대로 정렬된 Manager 이름 목록

        Raises:
            ValueError: 순환 의존성 발견
        """
        if self._initialization_order:
            return self._initialization_order

        visited: Set[str] = set()
        temp_visited: Set[str] = set()  # 순환 감지용
        result: List[str] = []

        def visit(name: str) -> None:
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected involving '{name}'")
            if name in visited:
                return

            temp_visited.add(name)

            for dep in self._dependencies.get(name, []):
                if dep in self._managers:
                    visit(dep)
                else:
                    logger.warning(f"Dependency '{dep}' for '{name}' is not registered")

            temp_visited.remove(name)
            visited.add(name)
            result.append(name)

        for name in self._managers:
            if name not in visited:
                visit(name)

        self._initialization_order = result
        return result

    async def initialize_all(self) -> Dict[str, Any]:
        """
        모든 Manager 초기화 (의존성 순서)

        Returns:
            초기화 결과 딕셔너리:
            - initialized: 성공한 Manager 목록
            - failed: 실패한 Manager 정보 목록
            - order: 초기화 순서
        """
        self._status = RegistryStatus.INITIALIZING
        self._errors = []

        result = {
            "initialized": [],
            "failed": [],
            "order": [],
        }

        try:
            order = self._compute_initialization_order()
            result["order"] = order
        except ValueError as e:
            self._status = RegistryStatus.ERROR
            self._errors.append(str(e))
            result["failed"].append({"name": "registry", "error": str(e)})
            return result

        logger.info(f"Initializing {len(order)} managers in order: {order}")

        for name in order:
            manager = self._managers.get(name)
            if not manager:
                continue

            try:
                if isinstance(manager, AsyncBaseManager):
                    await manager.initialize_async()
                else:
                    manager.initialize()

                result["initialized"].append(name)
                logger.info(f"Manager '{name}' initialized successfully")

            except Exception as e:
                error_msg = f"Failed to initialize '{name}': {e}"
                self._errors.append(error_msg)
                result["failed"].append({"name": name, "error": str(e)})
                logger.error(error_msg, exc_info=True)

        # 최종 상태 결정
        if not result["failed"]:
            self._status = RegistryStatus.READY
        elif result["initialized"]:
            self._status = RegistryStatus.PARTIAL
        else:
            self._status = RegistryStatus.ERROR

        logger.info(
            f"Registry initialization complete: "
            f"{len(result['initialized'])} succeeded, {len(result['failed'])} failed"
        )

        return result

    def initialize_all_sync(self) -> Dict[str, Any]:
        """
        모든 Manager 동기 초기화 (동기 Manager만)

        비동기 Manager는 건너뜁니다.

        Returns:
            초기화 결과 딕셔너리
        """
        self._status = RegistryStatus.INITIALIZING
        self._errors = []

        result = {
            "initialized": [],
            "failed": [],
            "skipped": [],
            "order": [],
        }

        try:
            order = self._compute_initialization_order()
            result["order"] = order
        except ValueError as e:
            self._status = RegistryStatus.ERROR
            self._errors.append(str(e))
            result["failed"].append({"name": "registry", "error": str(e)})
            return result

        for name in order:
            manager = self._managers.get(name)
            if not manager:
                continue

            # 비동기 Manager는 건너뛰기
            if isinstance(manager, AsyncBaseManager) and not hasattr(manager, '_do_initialize'):
                result["skipped"].append(name)
                continue

            try:
                manager.initialize()
                result["initialized"].append(name)
            except Exception as e:
                error_msg = f"Failed to initialize '{name}': {e}"
                self._errors.append(error_msg)
                result["failed"].append({"name": name, "error": str(e)})

        # 최종 상태 결정
        if not result["failed"]:
            self._status = RegistryStatus.READY if not result["skipped"] else RegistryStatus.PARTIAL
        elif result["initialized"]:
            self._status = RegistryStatus.PARTIAL
        else:
            self._status = RegistryStatus.ERROR

        return result

    async def shutdown_all(self) -> Dict[str, Any]:
        """
        모든 Manager 종료 (역순)

        Returns:
            종료 결과 딕셔너리
        """
        result = {
            "shutdown": [],
            "failed": [],
        }

        # 초기화 역순으로 종료
        order = list(reversed(self._compute_initialization_order()))

        logger.info(f"Shutting down {len(order)} managers in reverse order")

        for name in order:
            manager = self._managers.get(name)
            if not manager:
                continue

            try:
                if isinstance(manager, AsyncBaseManager):
                    await manager.shutdown_async()
                else:
                    manager.shutdown()

                result["shutdown"].append(name)

            except Exception as e:
                result["failed"].append({"name": name, "error": str(e)})
                logger.error(f"Failed to shutdown '{name}': {e}")

        self._status = RegistryStatus.SHUTDOWN
        logger.info(f"Registry shutdown complete")

        return result

    def shutdown_all_sync(self) -> Dict[str, Any]:
        """모든 Manager 동기 종료"""
        result = {
            "shutdown": [],
            "failed": [],
        }

        order = list(reversed(self._compute_initialization_order()))

        for name in order:
            manager = self._managers.get(name)
            if not manager:
                continue

            try:
                manager.shutdown()
                result["shutdown"].append(name)
            except Exception as e:
                result["failed"].append({"name": name, "error": str(e)})

        self._status = RegistryStatus.SHUTDOWN
        return result

    async def health_check_all(self) -> RegistryHealth:
        """
        모든 Manager 헬스체크

        Returns:
            RegistryHealth 결과
        """
        manager_health: Dict[str, ManagerHealth] = {}
        initialized_count = 0
        failed_count = 0

        for name, manager in self._managers.items():
            health = manager.health_check()
            manager_health[name] = health

            if health.status == ManagerStatus.READY:
                initialized_count += 1
            elif health.status == ManagerStatus.ERROR:
                failed_count += 1

        return RegistryHealth(
            status=self._status,
            total_managers=len(self._managers),
            initialized_managers=initialized_count,
            failed_managers=failed_count,
            manager_health=manager_health,
            last_check=datetime.now().isoformat(),
            errors=self._errors.copy(),
        )

    def health_check_all_sync(self) -> RegistryHealth:
        """모든 Manager 동기 헬스체크"""
        manager_health: Dict[str, ManagerHealth] = {}
        initialized_count = 0
        failed_count = 0

        for name, manager in self._managers.items():
            health = manager.health_check()
            manager_health[name] = health

            if health.status == ManagerStatus.READY:
                initialized_count += 1
            elif health.status == ManagerStatus.ERROR:
                failed_count += 1

        return RegistryHealth(
            status=self._status,
            total_managers=len(self._managers),
            initialized_managers=initialized_count,
            failed_managers=failed_count,
            manager_health=manager_health,
            last_check=datetime.now().isoformat(),
            errors=self._errors.copy(),
        )

    def reset(self) -> None:
        """
        Registry 초기화 (테스트용)

        모든 Manager 등록을 해제하고 상태를 초기화합니다.
        """
        self._managers.clear()
        self._dependencies.clear()
        self._initialization_order = []
        self._status = RegistryStatus.UNINITIALIZED
        self._errors = []
        logger.debug("ManagerRegistry reset")

    def __repr__(self) -> str:
        return (
            f"<ManagerRegistry status={self._status.value} "
            f"managers={len(self._managers)}>"
        )


# 글로벌 싱글톤 인스턴스
manager_registry = ManagerRegistry()


def get_manager_registry() -> ManagerRegistry:
    """Registry 인스턴스 반환"""
    return manager_registry


def get_manager(name: str) -> Optional[BaseManager]:
    """Manager 인스턴스 조회 (편의 함수)"""
    return manager_registry.get(name)


def require_manager(name: str) -> BaseManager:
    """Manager 인스턴스 조회 - 없으면 예외 (편의 함수)"""
    return manager_registry.get_or_raise(name)
