"""ExecutorRegistry - 실행기 인스턴스 관리 레지스트리

싱글톤 패턴으로 실행기 인스턴스를 관리하며,
카테고리별 조회 및 도구 기반 라우팅을 지원합니다.
"""

from typing import Dict, List, Optional, Type, Any
from threading import Lock
import logging

from .base_executor import BaseExecutor, get_registered_executors

logger = logging.getLogger(__name__)


class ExecutorRegistry:
    """실행기 인스턴스 레지스트리 (싱글톤)

    등록된 실행기 클래스를 기반으로 인스턴스를 생성하고 관리합니다.

    Example:
        ```python
        registry = get_executor_registry()

        # 실행기 가져오기
        data_executor = registry.get("data_executor")

        # 도구 기반 라우팅
        executor = registry.get_by_tool("collector")

        # 카테고리별 조회
        data_executors = registry.get_by_category("data")
        ```
    """

    _instance: Optional["ExecutorRegistry"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> "ExecutorRegistry":
        """싱글톤 인스턴스 생성"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """레지스트리 초기화"""
        if self._initialized:
            return

        self._executors: Dict[str, BaseExecutor] = {}
        self._executor_classes: Dict[str, Type[BaseExecutor]] = {}
        self._tool_to_executor: Dict[str, str] = {}  # tool_name -> executor_name
        self._initialized = True
        logger.info("ExecutorRegistry initialized")

    def register_class(self, name: str, executor_class: Type[BaseExecutor]) -> None:
        """실행기 클래스 등록

        Args:
            name: 실행기 이름
            executor_class: 실행기 클래스
        """
        if not issubclass(executor_class, BaseExecutor):
            raise TypeError(f"{executor_class.__name__} must inherit from BaseExecutor")

        self._executor_classes[name] = executor_class

        # 지원 도구 매핑 등록
        for tool_name in executor_class.supported_tools:
            self._tool_to_executor[tool_name] = name

        logger.debug(f"Registered executor class: {name}")

    def register_instance(self, name: str, executor: BaseExecutor) -> None:
        """실행기 인스턴스 직접 등록

        Args:
            name: 실행기 이름
            executor: 실행기 인스턴스
        """
        if not isinstance(executor, BaseExecutor):
            raise TypeError(f"Expected BaseExecutor instance, got {type(executor)}")

        self._executors[name] = executor

        # 지원 도구 매핑 등록
        for tool_name in executor.supported_tools:
            self._tool_to_executor[tool_name] = name

        logger.debug(f"Registered executor instance: {name}")

    def get(self, name: str, **kwargs) -> BaseExecutor:
        """실행기 인스턴스 가져오기 (lazy loading)

        Args:
            name: 실행기 이름
            **kwargs: 실행기 초기화 파라미터

        Returns:
            실행기 인스턴스

        Raises:
            KeyError: 등록되지 않은 실행기
        """
        # 이미 인스턴스가 있으면 반환
        if name in self._executors:
            return self._executors[name]

        # 클래스가 있으면 인스턴스 생성
        if name in self._executor_classes:
            executor = self._executor_classes[name](**kwargs)
            self._executors[name] = executor
            logger.debug(f"Created executor instance: {name}")
            return executor

        # @register_executor로 등록된 클래스 확인
        registered = get_registered_executors()
        if name in registered:
            executor = registered[name](**kwargs)
            self._executors[name] = executor

            # 지원 도구 매핑 등록
            for tool_name in executor.supported_tools:
                self._tool_to_executor[tool_name] = name

            logger.debug(f"Created executor from registered class: {name}")
            return executor

        raise KeyError(f"Executor '{name}' not found. Available: {self.list_executor_names()}")

    def get_or_none(self, name: str, **kwargs) -> Optional[BaseExecutor]:
        """실행기 인스턴스 가져오기 (없으면 None)

        Args:
            name: 실행기 이름
            **kwargs: 실행기 초기화 파라미터

        Returns:
            실행기 인스턴스 또는 None
        """
        try:
            return self.get(name, **kwargs)
        except KeyError:
            return None

    def get_by_tool(self, tool_name: str, **kwargs) -> Optional[BaseExecutor]:
        """도구 이름으로 실행기 가져오기

        Args:
            tool_name: 도구 이름
            **kwargs: 실행기 초기화 파라미터

        Returns:
            실행기 인스턴스 또는 None
        """
        # 매핑된 실행기 확인
        if tool_name in self._tool_to_executor:
            executor_name = self._tool_to_executor[tool_name]
            return self.get(executor_name, **kwargs)

        # 등록된 클래스에서 검색
        registered = get_registered_executors()
        for executor_name, cls in registered.items():
            if tool_name in cls.supported_tools:
                return self.get(executor_name, **kwargs)

        # 모든 인스턴스에서 검색
        for executor in self._executors.values():
            if executor.supports_tool(tool_name):
                return executor

        logger.warning(f"No executor found for tool: {tool_name}")
        return None

    def get_by_category(self, category: str) -> List[BaseExecutor]:
        """카테고리별 실행기 목록

        Args:
            category: 카테고리 이름 (data, insight, content, ops)

        Returns:
            해당 카테고리의 실행기 목록
        """
        result = []

        # 등록된 인스턴스 확인
        for executor in self._executors.values():
            if executor.category == category:
                result.append(executor)

        # 등록된 클래스 확인 (아직 인스턴스화되지 않은 것)
        for name, cls in self._executor_classes.items():
            if name not in self._executors and cls.category == category:
                executor = self.get(name)
                result.append(executor)

        # @register_executor로 등록된 클래스 확인
        registered = get_registered_executors()
        for name, cls in registered.items():
            if name not in self._executors and cls.category == category:
                executor = self.get(name)
                result.append(executor)

        return result

    def list_executors(self) -> List[Dict[str, Any]]:
        """모든 실행기 메타데이터 목록

        Returns:
            실행기 메타데이터 딕셔너리 목록
        """
        result = []

        # 등록된 인스턴스
        for executor in self._executors.values():
            result.append(executor.get_metadata())

        # 등록된 클래스 (아직 인스턴스화되지 않은 것)
        all_classes = {**self._executor_classes, **get_registered_executors()}
        for name, cls in all_classes.items():
            if name not in self._executors:
                result.append({
                    "name": cls.name,
                    "category": cls.category,
                    "supported_tools": cls.supported_tools,
                    "version": cls.version,
                })

        return result

    def list_executor_names(self) -> List[str]:
        """등록된 실행기 이름 목록

        Returns:
            실행기 이름 리스트
        """
        names = set(self._executors.keys())
        names.update(self._executor_classes.keys())
        names.update(get_registered_executors().keys())
        return sorted(list(names))

    def get_tool_mapping(self) -> Dict[str, str]:
        """도구 -> 실행기 매핑 반환

        Returns:
            도구 이름 -> 실행기 이름 매핑
        """
        return self._tool_to_executor.copy()

    def has(self, name: str) -> bool:
        """실행기 등록 여부 확인

        Args:
            name: 실행기 이름

        Returns:
            등록 여부
        """
        return (
            name in self._executors
            or name in self._executor_classes
            or name in get_registered_executors()
        )

    def clear(self) -> None:
        """모든 실행기 인스턴스 제거 (테스트용)"""
        self._executors.clear()
        self._tool_to_executor.clear()
        logger.debug("Cleared all executor instances")

    def reset(self) -> None:
        """레지스트리 초기화 (테스트용)"""
        self._executors.clear()
        self._executor_classes.clear()
        self._tool_to_executor.clear()
        logger.debug("Reset executor registry")


# 싱글톤 인스턴스 접근 함수
_registry_instance: Optional[ExecutorRegistry] = None


def get_executor_registry() -> ExecutorRegistry:
    """ExecutorRegistry 싱글톤 인스턴스 반환

    Returns:
        ExecutorRegistry 인스턴스
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ExecutorRegistry()
    return _registry_instance
