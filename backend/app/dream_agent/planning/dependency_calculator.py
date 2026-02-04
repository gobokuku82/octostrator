"""Dependency Calculator - 자동 의존성 계산

Todo 간의 의존성을 자동으로 계산하고 실행 순서를 결정합니다.
"""

from typing import List, Dict, Set, Optional, Any, Tuple
from collections import defaultdict

from backend.app.dream_agent.models.todo import TodoItem
from backend.app.dream_agent.planning.tool_catalog import (
    get_catalog,
    ToolCatalogLoader,
    ToolMetadata,
    ToolPhase
)


# ============================================================
# Dependency Rules
# ============================================================

class DependencyRules:
    """의존성 규칙 정의"""

    # 출력 타입 -> 입력 타입 매핑 (자동 연결)
    OUTPUT_TO_INPUT: Dict[str, List[str]] = {
        "raw_data": ["preprocessed_data"],
        "preprocessed_data": ["analysis_result"],
        "analysis_result": ["insights", "report", "dashboard"],
        "insights": ["report", "storyboard", "ad_creative"],
        "storyboard": ["video"],
    }

    # 레이어 순서 (실행 우선순위)
    LAYER_ORDER: Dict[str, int] = {
        "cognitive": 5,
        "planning": 4,
        "ml_execution": 3,
        "biz_execution": 2,
        "response": 1
    }

    # 단계 순서
    PHASE_ORDER: Dict[str, int] = {
        "collection": 5,
        "preprocessing": 4,
        "analysis": 3,
        "insight": 2,
        "output": 1
    }


# ============================================================
# Dependency Graph
# ============================================================

class DependencyGraph:
    """의존성 그래프"""

    def __init__(self):
        self.nodes: Dict[str, TodoItem] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)  # node -> depends_on
        self.reverse_edges: Dict[str, Set[str]] = defaultdict(set)  # node -> blocked_by

    def add_node(self, todo: TodoItem) -> None:
        """노드 추가"""
        self.nodes[todo.id] = todo

    def add_edge(self, from_id: str, to_id: str) -> None:
        """
        의존성 엣지 추가

        Args:
            from_id: 의존하는 Todo ID
            to_id: 의존 대상 Todo ID (먼저 실행되어야 함)
        """
        self.edges[from_id].add(to_id)
        self.reverse_edges[to_id].add(from_id)

    def get_dependencies(self, todo_id: str) -> Set[str]:
        """특정 Todo의 의존성 목록"""
        return self.edges.get(todo_id, set())

    def get_dependents(self, todo_id: str) -> Set[str]:
        """특정 Todo에 의존하는 Todo 목록"""
        return self.reverse_edges.get(todo_id, set())

    def has_cycle(self) -> Tuple[bool, Optional[List[str]]]:
        """
        순환 의존성 감지

        Returns:
            (has_cycle, cycle_path)
        """
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> Tuple[bool, List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.edges.get(node, set()):
                if neighbor not in visited:
                    has_cycle, cycle_path = dfs(neighbor)
                    if has_cycle:
                        return True, cycle_path
                elif neighbor in rec_stack:
                    # 순환 발견
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return False, []

        for node in self.nodes:
            if node not in visited:
                has_cycle, cycle_path = dfs(node)
                if has_cycle:
                    return True, cycle_path

        return False, None

    def topological_sort(self) -> List[str]:
        """
        위상 정렬 (실행 순서)

        Returns:
            List[str]: Todo ID 리스트 (실행 순서)
        """
        # Kahn's algorithm
        in_degree = defaultdict(int)

        for node in self.nodes:
            in_degree[node] = 0

        for node, deps in self.edges.items():
            for dep in deps:
                in_degree[node] += 1

        # 의존성 없는 노드부터 시작
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []

        while queue:
            # 우선순위 정렬 (레이어, 단계 순)
            queue.sort(key=lambda x: self._get_node_priority(x), reverse=True)
            node = queue.pop(0)
            result.append(node)

            for dependent in self.reverse_edges.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def _get_node_priority(self, todo_id: str) -> Tuple[int, int]:
        """노드 우선순위 계산"""
        todo = self.nodes.get(todo_id)
        if not todo:
            return (0, 0)

        layer_priority = DependencyRules.LAYER_ORDER.get(todo.layer, 0)
        todo_priority = todo.priority

        return (layer_priority, todo_priority)

    def get_ready_nodes(self, completed: Set[str]) -> List[str]:
        """
        실행 가능한 노드 목록 (모든 의존성 완료)

        Args:
            completed: 완료된 Todo ID 집합

        Returns:
            List[str]: 실행 가능한 Todo ID 리스트
        """
        ready = []
        for node in self.nodes:
            if node in completed:
                continue
            deps = self.get_dependencies(node)
            if deps.issubset(completed):
                ready.append(node)
        return ready


# ============================================================
# Dependency Calculator
# ============================================================

class DependencyCalculator:
    """
    자동 의존성 계산기

    Todo 리스트의 의존성을 자동으로 분석하고 실행 순서를 결정합니다.
    """

    def __init__(self, catalog: Optional[ToolCatalogLoader] = None):
        self.catalog = catalog or get_catalog()
        self.rules = DependencyRules()

    def calculate_dependencies(self, todos: List[TodoItem]) -> DependencyGraph:
        """
        Todo 리스트의 의존성 계산

        Args:
            todos: TodoItem 리스트

        Returns:
            DependencyGraph
        """
        graph = DependencyGraph()

        # 노드 추가
        for todo in todos:
            graph.add_node(todo)

        # 명시적 의존성 추가
        for todo in todos:
            for dep_id in todo.metadata.dependency.depends_on:
                if dep_id in graph.nodes:
                    graph.add_edge(todo.id, dep_id)

        # 암묵적 의존성 추가 (출력/입력 타입 기반)
        self._add_implicit_dependencies(graph, todos)

        # 레이어 기반 의존성 추가
        self._add_layer_dependencies(graph, todos)

        return graph

    def _add_implicit_dependencies(
        self,
        graph: DependencyGraph,
        todos: List[TodoItem]
    ) -> None:
        """출력/입력 타입 기반 암묵적 의존성 추가"""
        # 도구별 출력 타입 매핑
        output_producers: Dict[str, List[str]] = defaultdict(list)

        for todo in todos:
            tool_name = todo.metadata.execution.tool
            if tool_name:
                tool_meta = self.catalog.get_tool(tool_name)
                if tool_meta:
                    output_producers[tool_meta.output_type].append(todo.id)

        # 입력 타입 기반 의존성 추가
        for todo in todos:
            tool_name = todo.metadata.execution.tool
            if tool_name:
                tool_meta = self.catalog.get_tool(tool_name)
                if tool_meta:
                    for input_type in tool_meta.input_types:
                        # 해당 입력 타입을 생성하는 도구 찾기
                        for output_type, output_mapping in self.rules.OUTPUT_TO_INPUT.items():
                            if input_type in output_mapping:
                                # 해당 출력 타입을 생성하는 Todo 찾기
                                for producer_id in output_producers.get(output_type, []):
                                    if producer_id != todo.id:
                                        graph.add_edge(todo.id, producer_id)

    def _add_layer_dependencies(
        self,
        graph: DependencyGraph,
        todos: List[TodoItem]
    ) -> None:
        """레이어 기반 의존성 추가"""
        # 같은 parent 내에서 레이어 순서 보장
        parent_groups: Dict[Optional[str], List[TodoItem]] = defaultdict(list)

        for todo in todos:
            parent_groups[todo.parent_id].append(todo)

        for parent_id, group in parent_groups.items():
            if not parent_id:
                continue

            # 레이어별 정렬
            sorted_group = sorted(
                group,
                key=lambda x: self.rules.LAYER_ORDER.get(x.layer, 0),
                reverse=True
            )

            # 연속된 레이어 간 의존성 추가
            for i in range(1, len(sorted_group)):
                current = sorted_group[i]
                previous = sorted_group[i - 1]

                current_order = self.rules.LAYER_ORDER.get(current.layer, 0)
                previous_order = self.rules.LAYER_ORDER.get(previous.layer, 0)

                if current_order < previous_order:
                    # 이미 명시적 의존성이 없으면 추가
                    if previous.id not in graph.get_dependencies(current.id):
                        graph.add_edge(current.id, previous.id)

    def validate_dependencies(self, todos: List[TodoItem]) -> Dict[str, Any]:
        """
        의존성 유효성 검증

        Returns:
            {
                "is_valid": bool,
                "has_cycle": bool,
                "cycle_path": Optional[List[str]],
                "missing_dependencies": List[Dict],
                "warnings": List[str]
            }
        """
        graph = self.calculate_dependencies(todos)
        errors = []
        warnings = []
        missing_deps = []

        # 순환 의존성 검사
        has_cycle, cycle_path = graph.has_cycle()
        if has_cycle:
            errors.append(f"Circular dependency detected: {' -> '.join(cycle_path)}")

        # 누락된 의존성 검사
        for todo in todos:
            for dep_id in todo.metadata.dependency.depends_on:
                if dep_id not in graph.nodes:
                    missing_deps.append({
                        "todo_id": todo.id,
                        "todo_task": todo.task,
                        "missing_dep_id": dep_id
                    })

        # 도구 체인 검증
        tool_chain = [
            todo.metadata.execution.tool
            for todo in todos
            if todo.metadata.execution.tool
        ]
        chain_validation = self.catalog.validate_tool_chain(tool_chain)
        if not chain_validation["is_valid"]:
            errors.extend(chain_validation["errors"])
        warnings.extend(chain_validation["warnings"])

        return {
            "is_valid": len(errors) == 0 and not has_cycle,
            "has_cycle": has_cycle,
            "cycle_path": cycle_path,
            "missing_dependencies": missing_deps,
            "errors": errors,
            "warnings": warnings
        }

    def get_execution_order(self, todos: List[TodoItem]) -> List[TodoItem]:
        """
        실행 순서대로 정렬된 Todo 리스트

        Returns:
            List[TodoItem]: 실행 순서대로 정렬된 Todo
        """
        graph = self.calculate_dependencies(todos)

        # 순환 검사
        has_cycle, _ = graph.has_cycle()
        if has_cycle:
            raise ValueError("Cannot determine execution order: circular dependency detected")

        # 위상 정렬
        sorted_ids = graph.topological_sort()

        # ID -> Todo 매핑
        todo_map = {todo.id: todo for todo in todos}
        return [todo_map[todo_id] for todo_id in sorted_ids if todo_id in todo_map]

    def get_parallelizable_groups(self, todos: List[TodoItem]) -> List[List[TodoItem]]:
        """
        병렬 실행 가능한 그룹 반환

        Returns:
            List[List[TodoItem]]: 각 그룹은 병렬 실행 가능
        """
        graph = self.calculate_dependencies(todos)
        todo_map = {todo.id: todo for todo in todos}
        completed: Set[str] = set()
        groups: List[List[TodoItem]] = []

        while len(completed) < len(todos):
            ready_ids = graph.get_ready_nodes(completed)
            if not ready_ids:
                break

            group = [todo_map[tid] for tid in ready_ids if tid in todo_map]
            groups.append(group)
            completed.update(ready_ids)

        return groups

    def update_todo_dependencies(self, todos: List[TodoItem]) -> List[TodoItem]:
        """
        Todo의 의존성 정보 업데이트

        자동 계산된 의존성을 Todo 메타데이터에 반영합니다.

        Returns:
            List[TodoItem]: 업데이트된 Todo 리스트
        """
        graph = self.calculate_dependencies(todos)
        updated_todos = []

        for todo in todos:
            # 의존성 업데이트
            deps = list(graph.get_dependencies(todo.id))
            blocks = list(graph.get_dependents(todo.id))

            updated = todo.model_copy()
            updated.metadata.dependency.depends_on = deps
            updated.metadata.dependency.blocks = blocks
            updated_todos.append(updated)

        return updated_todos

    def get_critical_path(self, todos: List[TodoItem]) -> List[TodoItem]:
        """
        크리티컬 패스 (최장 경로) 계산

        Returns:
            List[TodoItem]: 크리티컬 패스의 Todo 리스트
        """
        graph = self.calculate_dependencies(todos)
        todo_map = {todo.id: todo for todo in todos}

        # 각 노드까지의 최장 거리 계산
        distances: Dict[str, int] = {}
        predecessors: Dict[str, Optional[str]] = {}

        sorted_ids = graph.topological_sort()

        for node_id in sorted_ids:
            todo = todo_map.get(node_id)
            if not todo:
                continue

            tool_name = todo.metadata.execution.tool
            tool_meta = self.catalog.get_tool(tool_name) if tool_name else None
            duration = tool_meta.estimated_duration_sec if tool_meta else 60

            deps = graph.get_dependencies(node_id)
            if not deps:
                distances[node_id] = duration
                predecessors[node_id] = None
            else:
                max_dist = 0
                max_pred = None
                for dep_id in deps:
                    if dep_id in distances and distances[dep_id] > max_dist:
                        max_dist = distances[dep_id]
                        max_pred = dep_id
                distances[node_id] = max_dist + duration
                predecessors[node_id] = max_pred

        # 최장 경로 역추적
        if not distances:
            return []

        end_node = max(distances.keys(), key=lambda x: distances[x])
        path = []
        current = end_node

        while current is not None:
            path.append(todo_map[current])
            current = predecessors.get(current)

        return list(reversed(path))


# ============================================================
# Global Instance
# ============================================================

_calculator: Optional[DependencyCalculator] = None


def get_calculator() -> DependencyCalculator:
    """전역 Calculator 인스턴스 반환"""
    global _calculator
    if _calculator is None:
        _calculator = DependencyCalculator()
    return _calculator
