"""Execution Graph Builder - DAG 생성 및 병렬 실행 계획"""

from typing import List, Dict, Set, Optional, Tuple, Any
from collections import defaultdict, deque
from backend.app.core.logging import get_logger
from backend.app.dream_agent.models import TodoItem
from backend.app.dream_agent.models.execution_graph import (
    ExecutionNode, ExecutionGroup, ExecutionGraph,
    create_execution_node, create_execution_group, create_execution_graph
)
from backend.app.dream_agent.models.resource import ResourcePlan

logger = get_logger(__name__)


class ExecutionGraphBuilder:
    """
    실행 그래프 빌더

    기능:
    - DAG 생성
    - 병렬 실행 그룹 생성
    - Critical Path 계산
    - LangGraph Command 생성
    - Mermaid 다이어그램 생성
    """

    def __init__(self):
        """초기화"""
        logger.info("ExecutionGraphBuilder initialized")

    # ============================================================
    # Graph Building
    # ============================================================

    def build(
        self,
        plan_id: str,
        todos: List[TodoItem],
        resource_plan: Optional[ResourcePlan] = None
    ) -> ExecutionGraph:
        """
        실행 그래프 생성

        Args:
            plan_id: Plan ID
            todos: TodoItem 리스트
            resource_plan: ResourcePlan (optional)

        Returns:
            ExecutionGraph
        """
        graph = create_execution_graph(plan_id)

        # 1. 노드 생성
        nodes = self._create_nodes(todos, resource_plan)
        graph.nodes = nodes

        # 2. 의존성 그래프 구축
        self._build_dependency_graph(graph)

        # 3. 깊이 계산
        self._calculate_depths(graph)

        # 4. 병렬 실행 그룹 생성
        groups = self._create_parallel_groups(graph)
        graph.groups = groups

        # 5. Critical Path 계산
        self._calculate_critical_path(graph)

        # 6. 통계 계산
        self._calculate_statistics(graph)

        # 7. LangGraph Command 생성
        self._generate_langgraph_commands(graph)

        # 8. Mermaid 다이어그램 생성
        graph.mermaid_diagram = self._generate_mermaid_diagram(graph)

        logger.info(
            f"Execution graph built: {graph.graph_id}, "
            f"nodes={graph.total_nodes}, groups={graph.total_groups}, "
            f"parallel_duration={graph.estimated_parallel_duration}s"
        )

        return graph

    def _create_nodes(
        self,
        todos: List[TodoItem],
        resource_plan: Optional[ResourcePlan]
    ) -> List[ExecutionNode]:
        """노드 생성"""
        nodes = []
        todo_to_node = {}  # todo_id -> node_id 매핑

        for todo in todos:
            # Agent 이름 추출
            agent_name = todo.metadata.execution.tool

            # 예상 실행 시간
            estimated_duration = todo.metadata.execution.timeout or 60.0

            # Resource plan에서 추가 정보 가져오기
            if resource_plan:
                allocation = next(
                    (a for a in resource_plan.allocations if a.todo_id == todo.id),
                    None
                )
                if allocation:
                    estimated_duration = allocation.estimated_duration_sec

            # 노드 생성
            node = create_execution_node(
                todo_id=todo.id,
                task=todo.task,
                layer=todo.layer,
                dependencies=[],  # 나중에 설정
                agent_name=agent_name,
                estimated_duration_sec=estimated_duration
            )

            nodes.append(node)
            todo_to_node[todo.id] = node.node_id

        # 의존성 매핑
        for todo in todos:
            node = next(n for n in nodes if n.todo_id == todo.id)
            depends_on = todo.metadata.dependency.depends_on

            # depends_on의 todo_id를 node_id로 변환
            node.dependencies = [
                todo_to_node[dep_todo_id]
                for dep_todo_id in depends_on
                if dep_todo_id in todo_to_node
            ]

        return nodes

    def _build_dependency_graph(self, graph: ExecutionGraph):
        """의존성 그래프 구축 (dependents 설정)"""
        for node in graph.nodes:
            for dep_node_id in node.dependencies:
                dep_node = graph.get_node(dep_node_id)
                if dep_node:
                    dep_node.dependents.append(node.node_id)

    def _calculate_depths(self, graph: ExecutionGraph):
        """
        깊이 계산 (위상 정렬 기반)

        루트 노드의 depth = 0
        각 노드의 depth = max(의존하는 노드들의 depth) + 1
        """
        # 진입 차수 계산
        in_degree = {node.node_id: len(node.dependencies) for node in graph.nodes}

        # 큐 초기화 (진입 차수가 0인 노드)
        queue = deque([node for node in graph.nodes if in_degree[node.node_id] == 0])

        # 깊이 초기화
        depth_map = {node.node_id: 0 for node in graph.nodes}

        # BFS
        while queue:
            current = queue.popleft()

            for dependent_id in current.dependents:
                dependent = graph.get_node(dependent_id)
                if not dependent:
                    continue

                # 깊이 업데이트
                depth_map[dependent_id] = max(
                    depth_map[dependent_id],
                    depth_map[current.node_id] + 1
                )

                # 진입 차수 감소
                in_degree[dependent_id] -= 1

                # 진입 차수가 0이 되면 큐에 추가
                if in_degree[dependent_id] == 0:
                    queue.append(dependent)

        # 노드에 깊이 설정
        for node in graph.nodes:
            node.depth = depth_map[node.node_id]

        graph.max_depth = max(depth_map.values()) if depth_map else 0

    def _create_parallel_groups(self, graph: ExecutionGraph) -> List[ExecutionGroup]:
        """
        병렬 실행 그룹 생성

        같은 depth의 노드들을 하나의 그룹으로 묶음
        """
        # depth별로 노드 그룹화
        depth_to_nodes: Dict[int, List[ExecutionNode]] = defaultdict(list)

        for node in graph.nodes:
            depth_to_nodes[node.depth].append(node)

        # ExecutionGroup 생성
        groups = []
        for depth in sorted(depth_to_nodes.keys()):
            group = create_execution_group(group_id=depth)

            for node in depth_to_nodes[depth]:
                node.parallel_group = depth
                group.add_node(node)

            groups.append(group)

        return groups

    def _calculate_critical_path(self, graph: ExecutionGraph):
        """
        Critical Path 계산

        Critical Path: 루트에서 리프까지 가장 긴 경로
        """
        # 각 노드까지의 최장 경로 시간 계산
        longest_path = {}

        # 위상 정렬 순서로 처리
        sorted_nodes = sorted(graph.nodes, key=lambda n: n.depth)

        for node in sorted_nodes:
            if not node.dependencies:
                # 루트 노드
                longest_path[node.node_id] = node.estimated_duration_sec
            else:
                # 의존하는 노드들 중 최대값 + 자신의 시간
                max_dep_time = max(
                    longest_path.get(dep_id, 0)
                    for dep_id in node.dependencies
                )
                longest_path[node.node_id] = max_dep_time + node.estimated_duration_sec

        # Critical Path 역추적
        if longest_path:
            # 최장 시간을 가진 리프 노드 찾기
            leaf_nodes = graph.get_leaf_nodes()
            if leaf_nodes:
                critical_leaf = max(
                    leaf_nodes,
                    key=lambda n: longest_path.get(n.node_id, 0)
                )

                # 역추적
                critical_path = []
                current = critical_leaf

                while current:
                    critical_path.append(current.node_id)
                    current.is_critical = True

                    # 이전 노드 찾기 (최장 경로)
                    if current.dependencies:
                        prev_node_id = max(
                            current.dependencies,
                            key=lambda dep_id: longest_path.get(dep_id, 0)
                        )
                        current = graph.get_node(prev_node_id)
                    else:
                        current = None

                critical_path.reverse()
                graph.critical_path = critical_path
                graph.critical_path_duration = longest_path[critical_leaf.node_id]

    def _calculate_statistics(self, graph: ExecutionGraph):
        """통계 계산"""
        graph.total_nodes = len(graph.nodes)
        graph.total_groups = len(graph.groups)

        # 순차 실행 시간
        graph.estimated_sequential_duration = sum(
            node.estimated_duration_sec for node in graph.nodes
        )

        # 병렬 실행 시간 (각 그룹의 최대 시간의 합)
        graph.estimated_parallel_duration = sum(
            group.estimated_duration_sec for group in graph.groups
        )

        # 병렬화 효율
        if graph.estimated_parallel_duration > 0:
            graph.parallelization_factor = (
                graph.estimated_sequential_duration /
                graph.estimated_parallel_duration
            )

        # 병렬 실행 지원 여부
        graph.supports_parallel_execution = graph.total_groups > 1

    def _generate_langgraph_commands(self, graph: ExecutionGraph):
        """
        LangGraph Command 생성

        각 그룹을 LangGraph의 Command로 변환
        """
        commands = []

        for i, group in enumerate(graph.groups):
            if len(group.nodes) == 1:
                # 단일 노드: 일반 실행
                node = group.nodes[0]
                command = {
                    "type": "execute",
                    "group_id": group.group_id,
                    "node_id": node.node_id,
                    "todo_id": node.todo_id,
                    "agent": node.agent_name,
                    "next_group": group.group_id + 1 if i < len(graph.groups) - 1 else None
                }
            else:
                # 다중 노드: 병렬 실행 (Command with goto)
                goto_targets = [node.todo_id for node in group.nodes]

                command = {
                    "type": "parallel",
                    "group_id": group.group_id,
                    "goto_targets": goto_targets,
                    "nodes": [
                        {
                            "node_id": node.node_id,
                            "todo_id": node.todo_id,
                            "agent": node.agent_name
                        }
                        for node in group.nodes
                    ],
                    "next_group": group.group_id + 1 if i < len(graph.groups) - 1 else None
                }

            commands.append(command)

        graph.langgraph_commands = commands

    def _generate_mermaid_diagram(self, graph: ExecutionGraph) -> str:
        """
        Mermaid 다이어그램 생성

        Returns:
            Mermaid 문자열
        """
        lines = ["graph TD"]

        # 노드 정의
        for node in graph.nodes:
            node_label = f"{node.task[:20]}..."
            style = ""

            if node.is_critical:
                style = ":::critical"

            lines.append(f'    {node.node_id}["{node_label}"]{ style}')

        # 엣지 정의
        for node in graph.nodes:
            for dep_id in node.dependencies:
                lines.append(f"    {dep_id} --> {node.node_id}")

        # 스타일 정의
        lines.append("")
        lines.append("    classDef critical fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px")

        return "\n".join(lines)

    # ============================================================
    # Graph Analysis
    # ============================================================

    def analyze_parallelization(
        self,
        graph: ExecutionGraph
    ) -> Dict[str, any]:
        """
        병렬화 분석

        Args:
            graph: ExecutionGraph

        Returns:
            분석 결과 dict
        """
        return {
            "total_nodes": graph.total_nodes,
            "total_groups": graph.total_groups,
            "max_parallel_nodes": max(
                len(group.nodes) for group in graph.groups
            ) if graph.groups else 0,
            "sequential_duration_sec": graph.estimated_sequential_duration,
            "parallel_duration_sec": graph.estimated_parallel_duration,
            "time_saved_sec": (
                graph.estimated_sequential_duration -
                graph.estimated_parallel_duration
            ),
            "speedup_factor": graph.parallelization_factor,
            "efficiency": (
                graph.parallelization_factor / graph.total_nodes
                if graph.total_nodes > 0
                else 0
            )
        }

    def get_ready_nodes(
        self,
        graph: ExecutionGraph,
        completed_node_ids: Set[str]
    ) -> List[ExecutionNode]:
        """
        실행 가능한 노드 조회

        Args:
            graph: ExecutionGraph
            completed_node_ids: 완료된 node IDs

        Returns:
            실행 가능한 노드 리스트
        """
        ready = []

        for node in graph.nodes:
            # 이미 완료되었으면 스킵
            if node.node_id in completed_node_ids:
                continue

            # 모든 의존성이 완료되었는지 확인
            all_deps_completed = all(
                dep_id in completed_node_ids
                for dep_id in node.dependencies
            )

            if all_deps_completed:
                ready.append(node)

        return ready

    def validate_graph(self, graph: ExecutionGraph) -> Dict[str, Any]:
        """
        그래프 유효성 검사

        Args:
            graph: ExecutionGraph

        Returns:
            검사 결과 dict
        """
        errors = []
        warnings = []

        # 1. 순환 의존성 체크
        if self._has_cycle(graph):
            errors.append("Circular dependency detected")

        # 2. 고립된 노드 체크
        isolated_nodes = [
            node.node_id
            for node in graph.nodes
            if not node.dependencies and not node.dependents
        ]
        if isolated_nodes and len(isolated_nodes) < len(graph.nodes):
            warnings.append(f"Isolated nodes found: {len(isolated_nodes)}")

        # 3. 병렬화 효율 체크
        if graph.parallelization_factor < 1.5:
            warnings.append(
                f"Low parallelization factor: {graph.parallelization_factor:.2f}"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _has_cycle(self, graph: ExecutionGraph) -> bool:
        """순환 의존성 검사 (DFS)"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node.node_id: WHITE for node in graph.nodes}

        def dfs(node_id: str) -> bool:
            color[node_id] = GRAY
            node = graph.get_node(node_id)

            if node:
                for dep_id in node.dependencies:
                    if color[dep_id] == GRAY:
                        return True  # 순환 발견
                    if color[dep_id] == WHITE and dfs(dep_id):
                        return True

            color[node_id] = BLACK
            return False

        for node in graph.nodes:
            if color[node.node_id] == WHITE:
                if dfs(node.node_id):
                    return True

        return False


# ============================================================
# Global Instance (Singleton Pattern)
# ============================================================

_execution_graph_builder_instance: Optional[ExecutionGraphBuilder] = None


def get_execution_graph_builder() -> ExecutionGraphBuilder:
    """ExecutionGraphBuilder 싱글톤 인스턴스 반환"""
    global _execution_graph_builder_instance
    if _execution_graph_builder_instance is None:
        _execution_graph_builder_instance = ExecutionGraphBuilder()
    return _execution_graph_builder_instance


# 글로벌 인스턴스 (편의용)
execution_graph_builder = get_execution_graph_builder()
