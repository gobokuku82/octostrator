"""Tool Compatibility Layer - ToolSpec과 BaseTool 간 호환성 브릿지

YAML 기반 ToolSpec과 클래스 기반 BaseTool 시스템을 통합합니다.
"""

from typing import Dict, Any, Optional, Type, List, Callable
from functools import wraps
import logging

from .base_tool import BaseTool, register_tool, _TOOL_CLASSES
from .discovery import ToolDiscovery, get_tool_discovery
from ..models.tool import ToolSpec, ToolType, ToolParameter, ToolParameterType

logger = logging.getLogger(__name__)


# ToolType ↔ category 매핑
TOOL_TYPE_TO_CATEGORY: Dict[ToolType, str] = {
    ToolType.DATA: "data",
    ToolType.ANALYSIS: "analysis",
    ToolType.CONTENT: "content",
    ToolType.BUSINESS: "business",
}

CATEGORY_TO_TOOL_TYPE: Dict[str, ToolType] = {
    v: k for k, v in TOOL_TYPE_TO_CATEGORY.items()
}


# Layer ↔ Executor 매핑
LAYER_TO_EXECUTOR: Dict[str, str] = {
    "ml_execution": "ml",
    "biz_execution": "biz",
    "data_collection": "data",
}


class ToolSpecAdapter(BaseTool):
    """ToolSpec을 BaseTool 인터페이스로 감싸는 어댑터

    YAML에서 로드된 ToolSpec을 BaseTool처럼 사용할 수 있게 합니다.

    Example:
        ```python
        spec = get_tool_discovery().get("sentiment_analyzer")
        adapter = ToolSpecAdapter(spec)
        result = adapter(reviews=["좋아요!", "별로예요"])
        ```
    """

    def __init__(self, spec: ToolSpec, executor_func: Optional[Callable] = None):
        """어댑터 초기화

        Args:
            spec: ToolSpec 인스턴스
            executor_func: 실제 실행 함수 (optional, 없으면 executor 경로에서 동적 로드)
        """
        super().__init__()
        self._spec = spec
        self._executor_func = executor_func

        # BaseTool 속성 매핑
        self.name = spec.name
        self.description = spec.description
        self.category = TOOL_TYPE_TO_CATEGORY.get(spec.tool_type, "general")
        self.version = spec.version

    @property
    def spec(self) -> ToolSpec:
        """원본 ToolSpec 반환"""
        return self._spec

    def execute(self, **kwargs) -> Dict[str, Any]:
        """도구 실행

        Args:
            **kwargs: 도구 파라미터

        Returns:
            실행 결과

        Raises:
            NotImplementedError: executor_func가 설정되지 않은 경우
        """
        if self._executor_func:
            return self._executor_func(**kwargs)

        # executor 경로에서 동적 로드 시도
        executor_path = self._spec.executor
        if executor_path:
            func = self._resolve_executor(executor_path)
            if func:
                return func(**kwargs)

        raise NotImplementedError(
            f"No executor implementation for tool: {self.name}. "
            f"Expected executor at: {executor_path}"
        )

    def _resolve_executor(self, path: str) -> Optional[Callable]:
        """executor 경로에서 함수 동적 로드

        Args:
            path: 'module.submodule.function' 형식의 경로

        Returns:
            Callable 또는 None
        """
        try:
            parts = path.rsplit(".", 1)
            if len(parts) != 2:
                return None

            module_path, func_name = parts
            module = __import__(module_path, fromlist=[func_name])
            return getattr(module, func_name, None)
        except (ImportError, AttributeError) as e:
            logger.debug(f"Failed to resolve executor {path}: {e}")
            return None

    def validate_input(self, **kwargs) -> bool:
        """입력 검증

        ToolSpec의 파라미터 정의를 기반으로 검증합니다.
        """
        required_params = self._spec.get_required_params()
        for param in required_params:
            if param.name not in kwargs:
                logger.warning(f"Missing required parameter: {param.name}")
                return False
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """도구 메타데이터 반환"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "tool_type": self._spec.tool_type.value,
            "layer": self._spec.layer,
            "tags": self._spec.tags,
            "dependencies": self._spec.dependencies,
            "produces": self._spec.produces,
            "has_cost": self._spec.has_cost,
            "estimated_cost": self._spec.estimated_cost,
        }


def spec_to_base_tool(spec: ToolSpec, executor_func: Optional[Callable] = None) -> BaseTool:
    """ToolSpec을 BaseTool 인스턴스로 변환

    Args:
        spec: ToolSpec 인스턴스
        executor_func: 실행 함수 (optional)

    Returns:
        BaseTool 호환 인스턴스
    """
    return ToolSpecAdapter(spec, executor_func)


def base_tool_to_spec(tool: BaseTool) -> ToolSpec:
    """BaseTool을 ToolSpec으로 변환

    Args:
        tool: BaseTool 인스턴스

    Returns:
        ToolSpec 인스턴스
    """
    tool_type = CATEGORY_TO_TOOL_TYPE.get(tool.category, ToolType.DATA)

    return ToolSpec(
        name=tool.name,
        description=tool.description,
        tool_type=tool_type,
        version=tool.version,
        executor=f"{tool.__class__.__module__}.{tool.__class__.__name__}.execute",
        parameters=[],  # BaseTool은 명시적 파라미터 정의가 없음
    )


def register_spec_tools_to_registry():
    """ToolDiscovery의 모든 ToolSpec을 BaseTool 레지스트리에 등록

    기존 ToolRegistry와의 호환성을 위해 YAML 도구들을 등록합니다.

    Example:
        ```python
        # 초기화 시 호출
        from backend.app.dream_agent.tools.compat import register_spec_tools_to_registry
        register_spec_tools_to_registry()

        # 이후 기존 방식으로 사용 가능
        from backend.app.dream_agent.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("sentiment_analyzer")
        ```
    """
    from .tool_registry import get_tool_registry

    discovery = get_tool_discovery()
    registry = get_tool_registry()

    specs = discovery.list_all_specs()
    for spec in specs:
        if not registry.has(spec.name):
            adapter = ToolSpecAdapter(spec)
            registry.register_instance(spec.name, adapter)
            logger.debug(f"Registered ToolSpec as BaseTool: {spec.name}")

    logger.info(f"Registered {len(specs)} YAML tools to ToolRegistry")


def register_base_tools_to_discovery():
    """@register_tool로 등록된 모든 BaseTool을 ToolDiscovery에 등록

    클래스 기반 도구들을 ToolDiscovery에서도 조회 가능하게 합니다.

    Example:
        ```python
        from backend.app.dream_agent.tools.compat import register_base_tools_to_discovery
        register_base_tools_to_discovery()

        # 이후 Discovery로 조회 가능
        discovery = get_tool_discovery()
        spec = discovery.get("legacy_tool")
        ```
    """
    discovery = get_tool_discovery()

    for name, tool_cls in _TOOL_CLASSES.items():
        if not discovery.get(name):
            # 임시 인스턴스 생성하여 메타데이터 추출
            try:
                instance = tool_cls()
                spec = base_tool_to_spec(instance)
                discovery.register(spec)
                logger.debug(f"Registered BaseTool as ToolSpec: {name}")
            except Exception as e:
                logger.warning(f"Failed to register {name} to discovery: {e}")

    logger.info(f"Registered {len(_TOOL_CLASSES)} class tools to ToolDiscovery")


def sync_registries():
    """ToolRegistry와 ToolDiscovery 양방향 동기화

    두 시스템에서 도구를 상호 조회할 수 있도록 동기화합니다.
    """
    register_spec_tools_to_registry()
    register_base_tools_to_discovery()
    logger.info("Tool registries synchronized")


class UnifiedToolAccess:
    """통합 도구 접근 인터페이스

    ToolRegistry와 ToolDiscovery를 통합하여 단일 인터페이스로 접근합니다.

    Example:
        ```python
        access = get_unified_tool_access()

        # 이름으로 조회 (YAML 또는 클래스 기반 모두)
        tool = access.get("sentiment_analyzer")

        # 타입별 조회
        data_tools = access.get_by_type(ToolType.DATA)

        # 태그별 조회
        nlp_tools = access.get_by_tag("nlp")

        # Executor 정보 조회
        executor = access.get_executor_name("sentiment_analyzer")
        ```
    """

    _instance: Optional["UnifiedToolAccess"] = None

    def __new__(cls) -> "UnifiedToolAccess":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._discovery = get_tool_discovery()
        self._initialized = True

    def get(self, name: str) -> Optional[BaseTool]:
        """이름으로 도구 조회

        Args:
            name: 도구 이름

        Returns:
            BaseTool 인스턴스 또는 None
        """
        # Discovery에서 먼저 조회
        spec = self._discovery.get(name)
        if spec:
            return ToolSpecAdapter(spec)

        # 클래스 기반 도구 조회
        if name in _TOOL_CLASSES:
            return _TOOL_CLASSES[name]()

        return None

    def get_spec(self, name: str) -> Optional[ToolSpec]:
        """이름으로 ToolSpec 조회

        Args:
            name: 도구 이름

        Returns:
            ToolSpec 인스턴스 또는 None
        """
        spec = self._discovery.get(name)
        if spec:
            return spec

        # 클래스 기반 도구를 ToolSpec으로 변환
        if name in _TOOL_CLASSES:
            instance = _TOOL_CLASSES[name]()
            return base_tool_to_spec(instance)

        return None

    def get_by_type(self, tool_type: ToolType) -> List[BaseTool]:
        """타입별 도구 목록

        Args:
            tool_type: 도구 타입

        Returns:
            BaseTool 인스턴스 리스트
        """
        specs = self._discovery.get_by_type(tool_type)
        return [ToolSpecAdapter(spec) for spec in specs]

    def get_by_tag(self, tag: str) -> List[BaseTool]:
        """태그별 도구 목록

        Args:
            tag: 태그

        Returns:
            BaseTool 인스턴스 리스트
        """
        specs = self._discovery.get_by_tag(tag)
        return [ToolSpecAdapter(spec) for spec in specs]

    def get_by_layer(self, layer: str) -> List[BaseTool]:
        """레이어별 도구 목록

        Args:
            layer: 실행 레이어 (ml_execution, biz_execution 등)

        Returns:
            BaseTool 인스턴스 리스트
        """
        specs = self._discovery.get_by_layer(layer)
        return [ToolSpecAdapter(spec) for spec in specs]

    def get_executor_name(self, tool_name: str) -> Optional[str]:
        """도구의 Executor 이름 조회

        Args:
            tool_name: 도구 이름

        Returns:
            Executor 이름 또는 None
        """
        spec = self._discovery.get(tool_name)
        if spec and spec.layer:
            return LAYER_TO_EXECUTOR.get(spec.layer)
        return None

    def get_execution_order(self, tool_names: List[str]) -> List[str]:
        """의존성 기반 실행 순서

        Args:
            tool_names: 도구 이름 리스트

        Returns:
            정렬된 도구 이름 리스트
        """
        return self._discovery.get_execution_order(tool_names)

    def list_all(self) -> List[Dict[str, Any]]:
        """모든 도구 메타데이터 목록"""
        result = []

        # Discovery 도구들
        specs = self._discovery.list_all_specs()
        for spec in specs:
            result.append({
                "name": spec.name,
                "description": spec.description,
                "tool_type": spec.tool_type.value,
                "layer": spec.layer,
                "source": "yaml",
            })

        # 클래스 기반 도구들 (중복 제외)
        registered_names = {spec.name for spec in specs}
        for name, tool_cls in _TOOL_CLASSES.items():
            if name not in registered_names:
                result.append({
                    "name": tool_cls.name,
                    "description": tool_cls.description,
                    "category": tool_cls.category,
                    "version": tool_cls.version,
                    "source": "class",
                })

        return result


# 싱글톤 접근 함수
_unified_access: Optional[UnifiedToolAccess] = None


def get_unified_tool_access() -> UnifiedToolAccess:
    """UnifiedToolAccess 싱글톤 인스턴스 반환"""
    global _unified_access
    if _unified_access is None:
        _unified_access = UnifiedToolAccess()
    return _unified_access


def get_tool_for_layer(layer: str) -> List[ToolSpec]:
    """레이어별 도구 목록 (헬퍼 함수)

    Args:
        layer: 실행 레이어

    Returns:
        해당 레이어의 ToolSpec 리스트
    """
    return get_tool_discovery().get_by_layer(layer)


def get_tool_dependencies(tool_name: str) -> List[str]:
    """도구의 의존성 목록 (헬퍼 함수)

    Args:
        tool_name: 도구 이름

    Returns:
        의존하는 도구 이름 리스트
    """
    spec = get_tool_discovery().get(tool_name)
    return spec.dependencies if spec else []


def get_tool_produces(tool_name: str) -> List[str]:
    """도구의 출력 목록 (헬퍼 함수)

    Args:
        tool_name: 도구 이름

    Returns:
        생성하는 데이터 키 리스트
    """
    spec = get_tool_discovery().get(tool_name)
    return spec.produces if spec else []
