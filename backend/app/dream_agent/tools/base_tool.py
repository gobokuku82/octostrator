"""BaseTool - 모든 도구의 추상 기본 클래스

LangGraph @tool 데코레이터와 호환되면서도
통합 관리가 가능한 도구 인터페이스를 제공합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, Callable
from functools import wraps
from langchain_core.tools import tool as langchain_tool
import logging

logger = logging.getLogger(__name__)

# Type variable for tool classes
T = TypeVar("T", bound="BaseTool")

# Global registry for tool classes (populated by register_tool decorator)
_TOOL_CLASSES: Dict[str, Type["BaseTool"]] = {}


class BaseTool(ABC):
    """모든 도구의 추상 기본 클래스

    Attributes:
        name: 도구 고유 이름 (예: "collector", "sentiment")
        description: 도구 설명
        category: 도구 카테고리 (data, analysis, content, business)
        version: 도구 버전

    Example:
        ```python
        @register_tool("collector")
        class CollectorTool(BaseTool):
            name = "collector"
            description = "멀티 플랫폼 리뷰 수집"
            category = "data"

            def execute(self, keyword: str, platforms: list = None) -> Dict:
                # 수집 로직
                return {"reviews": [...]}
        ```
    """

    # 클래스 속성 (서브클래스에서 오버라이드)
    name: str = "base_tool"
    description: str = "기본 도구"
    category: str = "general"
    version: str = "1.0.0"

    def __init__(self, **kwargs):
        """도구 초기화

        Args:
            **kwargs: 도구별 설정 파라미터
        """
        self._config = kwargs
        self._initialized = False

    def initialize(self) -> None:
        """도구 초기화 (lazy loading 지원)

        무거운 리소스 로딩이 필요한 경우 오버라이드합니다.
        """
        self._initialized = True

    def ensure_initialized(self) -> None:
        """초기화 보장"""
        if not self._initialized:
            self.initialize()

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """도구 실행 (동기)

        Args:
            **kwargs: 도구별 입력 파라미터

        Returns:
            실행 결과 딕셔너리
        """
        pass

    async def aexecute(self, **kwargs) -> Dict[str, Any]:
        """도구 실행 (비동기)

        기본적으로 동기 execute를 호출합니다.
        비동기 로직이 필요한 경우 오버라이드합니다.

        Args:
            **kwargs: 도구별 입력 파라미터

        Returns:
            실행 결과 딕셔너리
        """
        return self.execute(**kwargs)

    def validate_input(self, **kwargs) -> bool:
        """입력 검증

        Args:
            **kwargs: 검증할 입력

        Returns:
            검증 통과 여부
        """
        return True

    def __call__(self, **kwargs) -> Dict[str, Any]:
        """도구를 함수처럼 호출"""
        self.ensure_initialized()

        if not self.validate_input(**kwargs):
            raise ValueError(f"Invalid input for tool '{self.name}'")

        try:
            result = self.execute(**kwargs)
            logger.debug(f"Tool '{self.name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool '{self.name}' failed: {e}")
            raise

    def to_langchain_tool(self) -> Callable:
        """LangGraph @tool 호환 함수로 변환

        Returns:
            LangGraph tool 데코레이터가 적용된 함수
        """
        @langchain_tool
        def tool_func(**kwargs) -> Dict[str, Any]:
            return self(**kwargs)

        tool_func.__name__ = self.name
        tool_func.__doc__ = self.description
        return tool_func

    def get_metadata(self) -> Dict[str, Any]:
        """도구 메타데이터 반환"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', category='{self.category}')>"


def register_tool(name: str) -> Callable[[Type[T]], Type[T]]:
    """도구 클래스 등록 데코레이터

    Args:
        name: 도구 등록 이름

    Returns:
        데코레이터 함수

    Example:
        ```python
        @register_tool("collector")
        class CollectorTool(BaseTool):
            ...
        ```
    """
    def decorator(cls: Type[T]) -> Type[T]:
        if not issubclass(cls, BaseTool):
            raise TypeError(f"{cls.__name__} must inherit from BaseTool")

        _TOOL_CLASSES[name] = cls
        logger.debug(f"Registered tool: {name} -> {cls.__name__}")
        return cls

    return decorator


def get_registered_tools() -> Dict[str, Type[BaseTool]]:
    """등록된 모든 도구 클래스 반환"""
    return _TOOL_CLASSES.copy()


def create_tool(name: str, **kwargs) -> BaseTool:
    """등록된 도구 인스턴스 생성

    Args:
        name: 도구 이름
        **kwargs: 도구 초기화 파라미터

    Returns:
        도구 인스턴스

    Raises:
        KeyError: 등록되지 않은 도구
    """
    if name not in _TOOL_CLASSES:
        raise KeyError(f"Tool '{name}' not registered. Available: {list(_TOOL_CLASSES.keys())}")

    return _TOOL_CLASSES[name](**kwargs)
