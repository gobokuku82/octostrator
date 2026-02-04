"""Dream Agent Tools - 공용 도구 모듈

모든 실행 도구의 기본 클래스와 레지스트리를 제공합니다.

구조:
- tools/base_tool.py: BaseTool 추상 클래스
- tools/tool_registry.py: 도구 인스턴스 등록 및 조회
- tools/discovery.py: YAML 기반 Tool Discovery (Phase 0)
- tools/loader.py: YAML Tool Loader (Phase 0)
- tools/compat.py: ToolSpec ↔ BaseTool 호환 레이어 (Phase 1)
- tools/hot_reload.py: YAML 변경 감지 및 자동 리로드 (Phase 2)
- tools/definitions/: YAML Tool 정의 파일
- tools/data/: 데이터 수집/처리 도구
- tools/analysis/: 분석 도구
- tools/content/: 콘텐츠 생성 도구
- tools/business/: 비즈니스 도구
- tools/utils/: 유틸리티 함수
"""

from .base_tool import BaseTool, register_tool
from .tool_registry import ToolRegistry, get_tool_registry

# Phase 0: Tool Discovery
from .discovery import ToolDiscovery, get_tool_discovery
from .loader import YAMLToolLoader, load_tools_from_yaml

# Phase 1: Compatibility Layer
from .compat import (
    ToolSpecAdapter,
    spec_to_base_tool,
    base_tool_to_spec,
    sync_registries,
    get_unified_tool_access,
    UnifiedToolAccess,
    get_tool_for_layer,
    get_tool_dependencies,
    get_tool_produces,
    LAYER_TO_EXECUTOR,
)

# Phase 2: Hot Reload
from .hot_reload import (
    YAMLWatcher,
    ToolHotReloader,
    get_tool_hot_reloader,
    start_hot_reload,
    stop_hot_reload,
)

# Phase 3: Validator
from .validator import (
    ToolValidator,
    ValidationResult,
    get_tool_validator,
    validate_tool_spec,
    validate_all_tools,
)

__all__ = [
    # 기존
    "BaseTool",
    "register_tool",
    "ToolRegistry",
    "get_tool_registry",
    # Phase 0: Tool Discovery
    "ToolDiscovery",
    "get_tool_discovery",
    "YAMLToolLoader",
    "load_tools_from_yaml",
    # Phase 1: Compatibility Layer
    "ToolSpecAdapter",
    "spec_to_base_tool",
    "base_tool_to_spec",
    "sync_registries",
    "get_unified_tool_access",
    "UnifiedToolAccess",
    "get_tool_for_layer",
    "get_tool_dependencies",
    "get_tool_produces",
    "LAYER_TO_EXECUTOR",
    # Phase 2: Hot Reload
    "YAMLWatcher",
    "ToolHotReloader",
    "get_tool_hot_reloader",
    "start_hot_reload",
    "stop_hot_reload",
    # Phase 3: Validator
    "ToolValidator",
    "ValidationResult",
    "get_tool_validator",
    "validate_tool_spec",
    "validate_all_tools",
]
