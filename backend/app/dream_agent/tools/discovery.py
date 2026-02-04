"""Tool Discovery - YAML 기반 Tool 검색 및 관리 시스템

싱글톤 패턴으로 ToolSpec을 중앙 관리합니다.
Phase 0: Tool Discovery 시스템의 핵심.
"""

from typing import Dict, List, Optional, Set
from ..models.tool import ToolSpec, ToolType
import logging

logger = logging.getLogger(__name__)


class ToolDiscovery:
    """Tool Discovery 시스템 (싱글톤)

    YAML 파일에서 로드한 ToolSpec을 관리하고,
    다양한 조건으로 검색할 수 있게 합니다.
    """

    _instance: Optional["ToolDiscovery"] = None

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._by_type: Dict[ToolType, Set[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}
        self._by_layer: Dict[str, Set[str]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

    @classmethod
    def get_instance(cls) -> "ToolDiscovery":
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """인스턴스 리셋 (테스트용)"""
        cls._instance = None

    def register(self, spec: ToolSpec) -> None:
        """
        Tool 등록

        Args:
            spec: ToolSpec 인스턴스
        """
        self._tools[spec.name] = spec

        # 타입별 인덱스
        if spec.tool_type not in self._by_type:
            self._by_type[spec.tool_type] = set()
        self._by_type[spec.tool_type].add(spec.name)

        # 태그별 인덱스
        for tag in spec.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(spec.name)

        # 레이어별 인덱스
        if spec.layer not in self._by_layer:
            self._by_layer[spec.layer] = set()
        self._by_layer[spec.layer].add(spec.name)

        # 의존성 그래프
        self._dependency_graph[spec.name] = set(spec.dependencies)

        logger.debug(f"Registered tool: {spec.name} (type={spec.tool_type.value})")

    def unregister(self, name: str) -> bool:
        """
        Tool 등록 해제

        Args:
            name: Tool 이름

        Returns:
            성공 여부
        """
        if name not in self._tools:
            return False

        spec = self._tools[name]

        # 인덱스에서 제거
        if spec.tool_type in self._by_type:
            self._by_type[spec.tool_type].discard(name)

        for tag in spec.tags:
            if tag in self._by_tag:
                self._by_tag[tag].discard(name)

        if spec.layer in self._by_layer:
            self._by_layer[spec.layer].discard(name)

        if name in self._dependency_graph:
            del self._dependency_graph[name]

        del self._tools[name]
        logger.debug(f"Unregistered tool: {name}")
        return True

    def get(self, name: str) -> Optional[ToolSpec]:
        """이름으로 Tool 조회"""
        return self._tools.get(name)

    def get_by_type(self, tool_type: ToolType) -> List[ToolSpec]:
        """타입별 Tool 조회"""
        names = self._by_type.get(tool_type, set())
        return [self._tools[n] for n in names if n in self._tools]

    def get_by_tag(self, tag: str) -> List[ToolSpec]:
        """태그별 Tool 조회"""
        names = self._by_tag.get(tag, set())
        return [self._tools[n] for n in names if n in self._tools]

    def get_by_layer(self, layer: str) -> List[ToolSpec]:
        """레이어별 Tool 조회"""
        names = self._by_layer.get(layer, set())
        return [self._tools[n] for n in names if n in self._tools]

    def list_all(self) -> List[str]:
        """모든 Tool 이름 목록"""
        return list(self._tools.keys())

    def list_all_specs(self) -> List[ToolSpec]:
        """모든 ToolSpec 목록"""
        return list(self._tools.values())

    def get_dependencies(self, name: str) -> List[str]:
        """Tool의 의존성 목록"""
        return list(self._dependency_graph.get(name, set()))

    def get_dependents(self, name: str) -> List[str]:
        """해당 Tool에 의존하는 Tool 목록"""
        dependents = []
        for tool_name, deps in self._dependency_graph.items():
            if name in deps:
                dependents.append(tool_name)
        return dependents

    def get_execution_order(self, tool_names: List[str]) -> List[str]:
        """
        의존성을 고려한 실행 순서 반환 (위상 정렬)

        Args:
            tool_names: 실행할 Tool 이름 목록

        Returns:
            정렬된 Tool 이름 목록
        """
        # 대상 Tool과 의존성만 고려
        relevant_tools = set(tool_names)
        for name in tool_names:
            relevant_tools.update(self._dependency_graph.get(name, set()))

        # 진입 차수 계산
        in_degree = {name: 0 for name in relevant_tools}
        for name in relevant_tools:
            for dep in self._dependency_graph.get(name, set()):
                if dep in relevant_tools:
                    in_degree[name] += 1

        # 위상 정렬
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for name in relevant_tools:
                if current in self._dependency_graph.get(name, set()):
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        # 요청된 Tool만 필터링
        return [name for name in result if name in tool_names]

    def to_langchain_tools(self) -> List[Dict]:
        """LangChain Tool 형식으로 변환"""
        return [spec.to_langchain_schema() for spec in self._tools.values()]

    def get_stats(self) -> Dict:
        """통계 정보"""
        return {
            "total_tools": len(self._tools),
            "by_type": {t.value: len(names) for t, names in self._by_type.items()},
            "by_layer": {l: len(names) for l, names in self._by_layer.items()},
            "tags": list(self._by_tag.keys()),
        }


# 싱글톤 헬퍼 함수
def get_tool_discovery() -> ToolDiscovery:
    """ToolDiscovery 싱글톤 인스턴스 반환"""
    return ToolDiscovery.get_instance()
