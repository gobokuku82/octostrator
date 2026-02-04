"""YAML Tool Loader - YAML 파일에서 Tool 정의 로드

YAML 파일로 정의된 Tool을 ToolSpec으로 변환합니다.
Phase 0: Tool Discovery 시스템의 일부.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging

from ..models.tool import (
    ToolSpec,
    ToolType,
    ToolParameter,
    ToolParameterType,
)

logger = logging.getLogger(__name__)

# 기본 YAML 디렉토리
DEFAULT_YAML_DIR = Path(__file__).parent / "definitions"


class YAMLToolLoader:
    """YAML Tool 정의 로더"""

    def __init__(self, yaml_dir: Optional[Path] = None):
        self.yaml_dir = yaml_dir or DEFAULT_YAML_DIR

    def load_tool(self, file_path: Path) -> ToolSpec:
        """
        단일 YAML 파일에서 ToolSpec 로드

        Args:
            file_path: YAML 파일 경로

        Returns:
            ToolSpec 인스턴스
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 파라미터 변환
        parameters = []
        for p in data.get('parameters', []):
            param = ToolParameter(
                name=p['name'],
                type=ToolParameterType(p.get('type', 'string')),
                required=p.get('required', False),
                default=p.get('default'),
                description=p.get('description', '')
            )
            parameters.append(param)

        return ToolSpec(
            name=data['name'],
            description=data.get('description', ''),
            tool_type=ToolType(data.get('tool_type', 'data')),
            version=data.get('version', '1.0.0'),
            parameters=parameters,
            executor=data.get('executor', ''),
            timeout_sec=data.get('timeout_sec', 300),
            max_retries=data.get('max_retries', 3),
            dependencies=data.get('dependencies', []),
            produces=data.get('produces', []),
            layer=data.get('layer', 'execution'),
            tags=data.get('tags', []),
            examples=data.get('examples', []),
            has_cost=data.get('has_cost', False),
            estimated_cost=data.get('estimated_cost', 0.0),
        )

    def load_all(self) -> Dict[str, ToolSpec]:
        """
        모든 YAML 파일에서 ToolSpec 로드

        Returns:
            Dict[tool_name, ToolSpec]
        """
        tools = {}

        if not self.yaml_dir.exists():
            logger.warning(f"YAML directory not found: {self.yaml_dir}")
            return tools

        for yaml_file in self.yaml_dir.rglob("*.yaml"):
            try:
                spec = self.load_tool(yaml_file)
                tools[spec.name] = spec
                logger.debug(f"Loaded tool: {spec.name} from {yaml_file}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")

        for yaml_file in self.yaml_dir.rglob("*.yml"):
            try:
                spec = self.load_tool(yaml_file)
                tools[spec.name] = spec
                logger.debug(f"Loaded tool: {spec.name} from {yaml_file}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")

        logger.info(f"Loaded {len(tools)} tools from {self.yaml_dir}")
        return tools


def load_tools_from_yaml(yaml_dir: Optional[Path] = None) -> Dict[str, ToolSpec]:
    """
    YAML에서 Tool 로드 헬퍼 함수

    Args:
        yaml_dir: YAML 디렉토리 (None이면 기본 경로)

    Returns:
        Dict[tool_name, ToolSpec]
    """
    from .discovery import get_tool_discovery

    loader = YAMLToolLoader(yaml_dir)
    tools = loader.load_all()

    # Discovery에 등록
    discovery = get_tool_discovery()
    for spec in tools.values():
        discovery.register(spec)

    return tools
