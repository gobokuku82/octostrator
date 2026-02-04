"""ToolRegistry - 도구 인스턴스 관리 레지스트리

싱글톤 패턴으로 도구 인스턴스를 관리하며,
카테고리별 조회 및 lazy loading을 지원합니다.
"""

from typing import Dict, List, Optional, Type, Any
from threading import Lock
import logging

from .base_tool import BaseTool, get_registered_tools

logger = logging.getLogger(__name__)


class ToolRegistry:
    """도구 인스턴스 레지스트리 (싱글톤)

    등록된 도구 클래스를 기반으로 인스턴스를 생성하고 관리합니다.

    Example:
        ```python
        registry = get_tool_registry()

        # 도구 가져오기 (lazy loading)
        collector = registry.get("collector")
        result = collector(keyword="라네즈", limit=10)

        # 카테고리별 조회
        data_tools = registry.get_by_category("data")

        # 모든 도구 목록
        all_tools = registry.list_tools()
        ```
    """

    _instance: Optional["ToolRegistry"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> "ToolRegistry":
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

        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        self._initialized = True
        logger.info("ToolRegistry initialized")

    def register_class(self, name: str, tool_class: Type[BaseTool]) -> None:
        """도구 클래스 등록

        Args:
            name: 도구 이름
            tool_class: 도구 클래스
        """
        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"{tool_class.__name__} must inherit from BaseTool")

        self._tool_classes[name] = tool_class
        logger.debug(f"Registered tool class: {name}")

    def register_instance(self, name: str, tool: BaseTool) -> None:
        """도구 인스턴스 직접 등록

        Args:
            name: 도구 이름
            tool: 도구 인스턴스
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool instance, got {type(tool)}")

        self._tools[name] = tool
        logger.debug(f"Registered tool instance: {name}")

    def get(self, name: str, **kwargs) -> BaseTool:
        """도구 인스턴스 가져오기 (lazy loading)

        Args:
            name: 도구 이름
            **kwargs: 도구 초기화 파라미터

        Returns:
            도구 인스턴스

        Raises:
            KeyError: 등록되지 않은 도구
        """
        # 이미 인스턴스가 있으면 반환
        if name in self._tools:
            return self._tools[name]

        # 클래스가 있으면 인스턴스 생성
        if name in self._tool_classes:
            tool = self._tool_classes[name](**kwargs)
            self._tools[name] = tool
            logger.debug(f"Created tool instance: {name}")
            return tool

        # @register_tool로 등록된 클래스 확인
        registered = get_registered_tools()
        if name in registered:
            tool = registered[name](**kwargs)
            self._tools[name] = tool
            logger.debug(f"Created tool instance from registered class: {name}")
            return tool

        raise KeyError(f"Tool '{name}' not found. Available: {self.list_tool_names()}")

    def get_or_none(self, name: str, **kwargs) -> Optional[BaseTool]:
        """도구 인스턴스 가져오기 (없으면 None)

        Args:
            name: 도구 이름
            **kwargs: 도구 초기화 파라미터

        Returns:
            도구 인스턴스 또는 None
        """
        try:
            return self.get(name, **kwargs)
        except KeyError:
            return None

    def get_by_category(self, category: str) -> List[BaseTool]:
        """카테고리별 도구 목록

        Args:
            category: 카테고리 이름 (data, analysis, content, business)

        Returns:
            해당 카테고리의 도구 목록
        """
        result = []

        # 등록된 인스턴스 확인
        for tool in self._tools.values():
            if tool.category == category:
                result.append(tool)

        # 등록된 클래스 확인 (아직 인스턴스화되지 않은 것)
        for name, cls in self._tool_classes.items():
            if name not in self._tools and cls.category == category:
                tool = self.get(name)
                result.append(tool)

        # @register_tool로 등록된 클래스 확인
        registered = get_registered_tools()
        for name, cls in registered.items():
            if name not in self._tools and cls.category == category:
                tool = self.get(name)
                result.append(tool)

        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """모든 도구 메타데이터 목록

        Returns:
            도구 메타데이터 딕셔너리 목록
        """
        result = []

        # 등록된 인스턴스
        for tool in self._tools.values():
            result.append(tool.get_metadata())

        # 등록된 클래스 (아직 인스턴스화되지 않은 것)
        all_classes = {**self._tool_classes, **get_registered_tools()}
        for name, cls in all_classes.items():
            if name not in self._tools:
                result.append({
                    "name": cls.name,
                    "description": cls.description,
                    "category": cls.category,
                    "version": cls.version,
                })

        return result

    def list_tool_names(self) -> List[str]:
        """등록된 도구 이름 목록

        Returns:
            도구 이름 리스트
        """
        names = set(self._tools.keys())
        names.update(self._tool_classes.keys())
        names.update(get_registered_tools().keys())
        return sorted(list(names))

    def has(self, name: str) -> bool:
        """도구 등록 여부 확인

        Args:
            name: 도구 이름

        Returns:
            등록 여부
        """
        return (
            name in self._tools
            or name in self._tool_classes
            or name in get_registered_tools()
        )

    def clear(self) -> None:
        """모든 도구 인스턴스 제거 (테스트용)"""
        self._tools.clear()
        logger.debug("Cleared all tool instances")

    def reset(self) -> None:
        """레지스트리 초기화 (테스트용)"""
        self._tools.clear()
        self._tool_classes.clear()
        logger.debug("Reset tool registry")


# 싱글톤 인스턴스 접근 함수
_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """ToolRegistry 싱글톤 인스턴스 반환

    Returns:
        ToolRegistry 인스턴스
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance
