"""BaseDomainAgent - 도메인 에이전트 표준화 기본 클래스

Phase 2: 모든 Domain Agent의 기본 인터페이스 정의.
ToolSpec과 연동하여 YAML 기반 도구 정의와 통합.
"""

from abc import ABC, abstractmethod
from typing import Type, Any, Dict, List, Optional, Callable
from pydantic import BaseModel
import logging

from ...schemas.tool_io.base import ToolInput, ToolOutput
from ...tools.discovery import get_tool_discovery
from ...models.tool import ToolSpec

logger = logging.getLogger(__name__)


class BaseDomainAgent(ABC):
    """Domain Agent 기본 클래스

    모든 도메인 에이전트가 상속해야 하는 추상 기본 클래스입니다.
    ToolSpec과 연동하여 YAML 기반 설정을 지원합니다.

    Example:
        ```python
        class SentimentAgent(BaseDomainAgent):
            @property
            def name(self) -> str:
                return "sentiment_analyzer"

            @property
            def description(self) -> str:
                return "리뷰 감성 분석"

            @property
            def input_schema(self) -> Type[BaseModel]:
                return SentimentInput

            @property
            def output_schema(self) -> Type[BaseModel]:
                return SentimentOutput

            async def execute(self, input: ToolInput) -> ToolOutput:
                # 실행 로직
                ...
        ```
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """에이전트 초기화

        Args:
            config: 에이전트 설정 (optional)
        """
        self._config = config or {}
        self._spec: Optional[ToolSpec] = None
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """에이전트 이름 (ToolSpec name과 일치해야 함)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """에이전트 설명"""
        pass

    @property
    def input_schema(self) -> Type[BaseModel]:
        """입력 스키마 (기본: ToolInput)"""
        return ToolInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        """출력 스키마 (기본: ToolOutput)"""
        return ToolOutput

    @property
    def spec(self) -> Optional[ToolSpec]:
        """연결된 ToolSpec"""
        if self._spec is None:
            discovery = get_tool_discovery()
            self._spec = discovery.get(self.name)
        return self._spec

    @property
    def layer(self) -> Optional[str]:
        """실행 레이어"""
        return self.spec.layer if self.spec else None

    @property
    def dependencies(self) -> List[str]:
        """의존하는 도구 목록"""
        return self.spec.dependencies if self.spec else []

    def initialize(self) -> None:
        """에이전트 초기화 (lazy loading)

        무거운 리소스 로딩이 필요한 경우 오버라이드합니다.
        """
        self._initialized = True

    def ensure_initialized(self) -> None:
        """초기화 보장"""
        if not self._initialized:
            self.initialize()

    @abstractmethod
    async def execute(self, input: ToolInput) -> ToolOutput:
        """에이전트 실행

        Args:
            input: 입력 데이터 (ToolInput 또는 서브클래스)

        Returns:
            출력 데이터 (ToolOutput 또는 서브클래스)
        """
        pass

    def execute_sync(self, input: ToolInput) -> ToolOutput:
        """동기 실행 (async wrapper)

        Args:
            input: 입력 데이터

        Returns:
            출력 데이터
        """
        import asyncio
        return asyncio.run(self.execute(input))

    def validate_input(self, input_data: Dict[str, Any]) -> ToolInput:
        """입력 검증

        Args:
            input_data: 입력 딕셔너리

        Returns:
            검증된 ToolInput 인스턴스

        Raises:
            ValidationError: 검증 실패 시
        """
        return self.input_schema(**input_data)

    def validate_output(self, output_data: Dict[str, Any]) -> ToolOutput:
        """출력 검증

        Args:
            output_data: 출력 딕셔너리

        Returns:
            검증된 ToolOutput 인스턴스

        Raises:
            ValidationError: 검증 실패 시
        """
        return self.output_schema(**output_data)

    async def run(self, **kwargs) -> Dict[str, Any]:
        """편의 메서드: dict 입력 → dict 출력

        Args:
            **kwargs: 입력 파라미터

        Returns:
            출력 딕셔너리
        """
        self.ensure_initialized()

        # 입력 검증
        validated_input = self.validate_input(kwargs)

        # 실행
        logger.debug(f"[{self.name}] Executing with input: {validated_input}")
        output = await self.execute(validated_input)

        # 출력 검증 및 변환
        if isinstance(output, BaseModel):
            return output.model_dump()
        return dict(output)

    def to_langchain_tool(self) -> Callable:
        """LangChain @tool 호환 함수 생성

        Returns:
            @tool 데코레이터가 적용된 함수
        """
        from langchain_core.tools import tool as langchain_tool

        agent = self

        @langchain_tool
        def tool_func(**kwargs) -> Dict[str, Any]:
            return agent.execute_sync(agent.validate_input(kwargs))

        tool_func.__name__ = self.name
        tool_func.__doc__ = self.description
        return tool_func

    def get_metadata(self) -> Dict[str, Any]:
        """에이전트 메타데이터"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
            "layer": self.layer,
            "dependencies": self.dependencies,
            "has_spec": self.spec is not None,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"


class DomainAgentRegistry:
    """Domain Agent 레지스트리

    모든 도메인 에이전트를 중앙에서 관리합니다.

    Example:
        ```python
        registry = get_domain_agent_registry()

        # 에이전트 등록
        registry.register(SentimentAgent())

        # 에이전트 조회
        agent = registry.get("sentiment_analyzer")
        result = await agent.run(texts=["좋아요!"])
        ```
    """

    _instance: Optional["DomainAgentRegistry"] = None

    def __new__(cls) -> "DomainAgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, BaseDomainAgent] = {}
        return cls._instance

    def register(self, agent: BaseDomainAgent) -> None:
        """에이전트 등록

        Args:
            agent: BaseDomainAgent 인스턴스
        """
        self._agents[agent.name] = agent
        logger.debug(f"Registered domain agent: {agent.name}")

    def unregister(self, name: str) -> bool:
        """에이전트 등록 해제

        Args:
            name: 에이전트 이름

        Returns:
            성공 여부
        """
        if name in self._agents:
            del self._agents[name]
            logger.debug(f"Unregistered domain agent: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseDomainAgent]:
        """에이전트 조회

        Args:
            name: 에이전트 이름

        Returns:
            BaseDomainAgent 인스턴스 또는 None
        """
        return self._agents.get(name)

    def list_all(self) -> List[BaseDomainAgent]:
        """모든 에이전트 목록"""
        return list(self._agents.values())

    def list_names(self) -> List[str]:
        """모든 에이전트 이름 목록"""
        return list(self._agents.keys())

    def has(self, name: str) -> bool:
        """에이전트 존재 여부"""
        return name in self._agents

    def clear(self) -> None:
        """모든 에이전트 제거"""
        self._agents.clear()

    @classmethod
    def reset(cls) -> None:
        """레지스트리 리셋 (테스트용)"""
        cls._instance = None


# 싱글톤 접근 함수
_registry_instance: Optional[DomainAgentRegistry] = None


def get_domain_agent_registry() -> DomainAgentRegistry:
    """DomainAgentRegistry 싱글톤 인스턴스 반환"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DomainAgentRegistry()
    return _registry_instance


def register_domain_agent(agent: BaseDomainAgent) -> None:
    """도메인 에이전트 등록 (헬퍼 함수)"""
    get_domain_agent_registry().register(agent)


def get_domain_agent(name: str) -> Optional[BaseDomainAgent]:
    """도메인 에이전트 조회 (헬퍼 함수)"""
    return get_domain_agent_registry().get(name)
