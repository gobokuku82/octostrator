"""Todo Dependency Manager - 의존성 해결 및 검증

P0-4.3: BaseManager 상속 및 Instance Method 리팩토링
- Static Method → Instance Method 변환
- BaseManager 상속으로 lifecycle 관리 통합
- 기존 인터페이스 호환성 유지
"""

from typing import List, Set, Dict, Tuple, Optional
from backend.app.core.logging import get_logger
from backend.app.dream_agent.models.todo import TodoItem
from backend.app.dream_agent.workflow_manager.base_manager import (
    BaseManager,
    ManagerStatus,
)

logger = get_logger(__name__)


class TodoDependencyManager(BaseManager):
    """
    Todo 의존성 관리자

    BaseManager를 상속하여 lifecycle 관리를 지원합니다.

    Features:
    - 의존성 기반 실행 순서 결정
    - 순환 의존성 검사
    - 위상 정렬 (Topological Sort)
    - 자동 unblock 처리
    """

    def __init__(self, name: str = "TodoDependencyManager"):
        """
        TodoDependencyManager 초기화

        Args:
            name: Manager 이름
        """
        super().__init__(name)
        self._cache: Dict[str, any] = {}

    def _do_initialize(self) -> None:
        """
        Manager 초기화 로직

        현재는 별도 초기화 작업 없음.
        향후 캐시 초기화 등에 활용 가능.
        """
        self._cache = {}
        logger.info(f"{self.name} initialized")

    def _do_shutdown(self) -> None:
        """
        Manager 종료 로직

        캐시 정리 등 cleanup 작업.
        """
        self._cache.clear()
        logger.info(f"{self.name} shutdown")

    def validate(self) -> Dict[str, any]:
        """
        Manager 상태 검증

        Returns:
            검증 결과 딕셔너리
        """
        return {
            "valid": True,
            "cache_size": len(self._cache),
        }

    @staticmethod
    def get_ready_todos(todos: List[TodoItem]) -> List[TodoItem]:
        """
        실행 가능한 (의존성이 충족된) todos 반환

        조건:
        - status == "pending"
        - 모든 의존성(depends_on)이 completed 상태

        의존성 해석:
        - UUID 형식: todo ID로 직접 매칭
        - 문자열(tool name): 해당 tool을 사용하는 completed todo로 매칭

        Args:
            todos: Todo 리스트

        Returns:
            실행 가능한 todos (우선순위 순)
        """
        # Completed todo IDs
        completed_ids = {
            t.id for t in todos
            if t.status == "completed"
        }

        # Completed todos의 tool name → todo ID 매핑
        # depends_on=["collector"] 형태의 의존성 해결용
        completed_tools: Set[str] = set()
        for t in todos:
            if t.status == "completed":
                # metadata.execution.tool에서 tool name 추출
                if hasattr(t, "metadata") and t.metadata:
                    if hasattr(t.metadata, "execution") and t.metadata.execution:
                        tool_name = t.metadata.execution.tool
                        if tool_name:
                            completed_tools.add(tool_name)

        def is_dependency_satisfied(dep: str) -> bool:
            """
            의존성이 충족되었는지 확인

            Args:
                dep: 의존성 (todo ID 또는 tool name)

            Returns:
                충족 여부
            """
            # 1. UUID 형식인지 확인 (todo ID)
            if dep in completed_ids:
                return True

            # 2. Tool name으로 확인
            if dep in completed_tools:
                return True

            return False

        ready = []
        for todo in todos:
            if todo.status != "pending":
                continue

            # 의존성 확인
            dependencies = todo.metadata.dependency.depends_on

            if all(is_dependency_satisfied(dep) for dep in dependencies):
                ready.append(todo)

        # 우선순위 순 정렬 (높은 것 먼저)
        return sorted(ready, key=lambda x: -x.priority)

    @staticmethod
    def _build_tool_to_id_map(todos: List[TodoItem]) -> Dict[str, str]:
        """
        Tool name → Todo ID 매핑 생성

        Args:
            todos: Todo 리스트

        Returns:
            {tool_name: todo_id} 매핑
        """
        tool_to_id: Dict[str, str] = {}
        for todo in todos:
            if hasattr(todo, "metadata") and todo.metadata:
                if hasattr(todo.metadata, "execution") and todo.metadata.execution:
                    tool_name = todo.metadata.execution.tool
                    if tool_name and tool_name not in tool_to_id:
                        # 같은 tool이 여러 개면 첫 번째 것만 사용
                        tool_to_id[tool_name] = todo.id
        return tool_to_id

    @staticmethod
    def _resolve_dependency(dep: str, todo_ids: Set[str], tool_to_id: Dict[str, str]) -> Optional[str]:
        """
        의존성을 todo ID로 해석

        Args:
            dep: 의존성 (todo ID 또는 tool name)
            todo_ids: 유효한 todo ID 집합
            tool_to_id: tool name → todo ID 매핑

        Returns:
            해석된 todo ID 또는 None
        """
        # UUID(todo ID)인 경우
        if dep in todo_ids:
            return dep
        # Tool name인 경우
        if dep in tool_to_id:
            return tool_to_id[dep]
        return None

    @staticmethod
    def check_circular_dependency(todos: List[TodoItem]) -> List[str]:
        """
        순환 의존성 검사 (DFS)

        Tool name 의존성도 지원합니다.

        Args:
            todos: Todo 리스트

        Returns:
            순환이 발견된 todo ID 목록
        """
        todo_ids = {t.id for t in todos}
        tool_to_id = TodoDependencyManager._build_tool_to_id_map(todos)

        # 의존성 그래프 구성 (tool name → todo ID 변환)
        graph: Dict[str, List[str]] = {}
        for todo in todos:
            resolved_deps = []
            for dep in todo.metadata.dependency.depends_on:
                resolved = TodoDependencyManager._resolve_dependency(dep, todo_ids, tool_to_id)
                if resolved:
                    resolved_deps.append(resolved)
            graph[todo.id] = resolved_deps

        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[str] = []

        def dfs(todo_id: str) -> bool:
            """DFS로 순환 검사"""
            visited.add(todo_id)
            rec_stack.add(todo_id)

            for neighbor in graph.get(todo_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # 순환 발견
                    cycles.append(todo_id)
                    return True

            rec_stack.remove(todo_id)
            return False

        # 모든 노드에 대해 DFS 실행
        for todo in todos:
            if todo.id not in visited:
                dfs(todo.id)

        if cycles:
            logger.warning(f"Circular dependency detected: {cycles}")

        return cycles

    def validate_same_layer_dependency(self, todos: List[TodoItem]) -> List[str]:
        """
        Cross-layer 의존성 검증

        **정책 변경 (2026-01-13):**
        - Cross-layer 의존성 **허용**
        - 복합적인 실행 흐름 지원: ml->biz, biz->ml, biz->biz->ml->biz 등
        - ML layer와 Biz layer 모두 Execution layer 하위 개념
        - 모든 실행 에이전트는 복합적으로 작동 가능

        Args:
            todos: Todo 리스트

        Returns:
            에러 메시지 리스트 (현재는 항상 빈 리스트)
        """
        # Cross-layer dependency 허용 - 검증하지 않음
        return []

    def get_dependent_todos(
        self,
        todos: List[TodoItem],
        todo_id: str
    ) -> List[TodoItem]:
        """
        특정 todo에 의존하는 todos 찾기

        해당 todo의 ID 또는 tool name에 의존하는 todos를 찾습니다.

        Args:
            todos: Todo 리스트
            todo_id: 대상 todo ID

        Returns:
            todo_id에 의존하는 todos
        """
        # 대상 todo 찾기
        target_todo = None
        for t in todos:
            if t.id == todo_id:
                target_todo = t
                break

        # 대상 todo의 tool name 추출
        target_tool = None
        if target_todo and hasattr(target_todo, "metadata") and target_todo.metadata:
            if hasattr(target_todo.metadata, "execution") and target_todo.metadata.execution:
                target_tool = target_todo.metadata.execution.tool

        dependent = []

        for todo in todos:
            deps = todo.metadata.dependency.depends_on
            # ID로 의존하는 경우
            if todo_id in deps:
                dependent.append(todo)
            # Tool name으로 의존하는 경우
            elif target_tool and target_tool in deps:
                dependent.append(todo)

        return dependent

    def build_dependency_graph(
        self,
        todos: List[TodoItem]
    ) -> Dict[str, List[str]]:
        """
        의존성 그래프 구축

        Tool name 의존성을 todo ID로 변환합니다.

        Args:
            todos: Todo 리스트

        Returns:
            {todo_id: [depends_on_ids]} 그래프 (모든 의존성이 todo ID로 해석됨)
        """
        todo_ids = {t.id for t in todos}
        tool_to_id = TodoDependencyManager._build_tool_to_id_map(todos)

        graph = {}
        for todo in todos:
            resolved_deps = []
            for dep in todo.metadata.dependency.depends_on:
                resolved = TodoDependencyManager._resolve_dependency(dep, todo_ids, tool_to_id)
                if resolved:
                    resolved_deps.append(resolved)
            graph[todo.id] = resolved_deps

        return graph

    def topological_sort(self, todos: List[TodoItem]) -> Tuple[List[TodoItem], bool]:
        """
        위상 정렬 (Topological Sort)

        의존성 순서대로 todos 정렬.
        Tool name 의존성도 지원합니다.

        Args:
            todos: Todo 리스트

        Returns:
            (정렬된 todos, 성공 여부)
            성공 여부가 False이면 순환 의존성 존재
        """
        # 의존성 그래프 (tool name → todo ID 변환됨)
        graph = self.build_dependency_graph(todos)

        # todo ID → todo 객체 매핑
        todo_by_id = {t.id: t for t in todos}

        # In-degree 계산 (그래프 기반)
        in_degree: Dict[str, int] = {}
        for todo in todos:
            # graph[todo.id]는 이미 해석된 todo ID 리스트
            in_degree[todo.id] = len(graph.get(todo.id, []))

        # In-degree 0인 노드로 시작
        queue = [t for t in todos if in_degree[t.id] == 0]
        sorted_todos = []

        while queue:
            # 우선순위 순 정렬
            queue.sort(key=lambda x: -x.priority)
            current = queue.pop(0)
            sorted_todos.append(current)

            # current에 의존하는 todos의 in-degree 감소
            for todo in todos:
                # graph에서 해석된 의존성 확인
                if current.id in graph.get(todo.id, []):
                    in_degree[todo.id] -= 1
                    if in_degree[todo.id] == 0:
                        queue.append(todo)

        # 모든 todos가 정렬되었는지 확인
        success = len(sorted_todos) == len(todos)

        if not success:
            logger.error("Topological sort failed - circular dependency detected")

        return (sorted_todos, success)

    def get_blocked_todos(self, todos: List[TodoItem]) -> List[TodoItem]:
        """
        Blocked 상태의 todos 조회

        Args:
            todos: Todo 리스트

        Returns:
            blocked 상태의 todos
        """
        return [t for t in todos if t.status == "blocked"]

    def auto_unblock_todos(
        self,
        todos: List[TodoItem]
    ) -> List[TodoItem]:
        """
        자동 unblock - 의존성이 충족되면 pending으로 변경

        의존성 해석:
        - UUID 형식: todo ID로 직접 매칭
        - 문자열(tool name): 해당 tool을 사용하는 completed todo로 매칭

        Args:
            todos: Todo 리스트

        Returns:
            unblock된 todos (상태 업데이트용)
        """
        completed_ids = {
            t.id for t in todos
            if t.status == "completed"
        }

        # Completed todos의 tool name 수집
        completed_tools: Set[str] = set()
        for t in todos:
            if t.status == "completed":
                if hasattr(t, "metadata") and t.metadata:
                    if hasattr(t.metadata, "execution") and t.metadata.execution:
                        tool_name = t.metadata.execution.tool
                        if tool_name:
                            completed_tools.add(tool_name)

        def is_dependency_satisfied(dep: str) -> bool:
            """의존성 충족 여부 확인"""
            return dep in completed_ids or dep in completed_tools

        unblocked = []

        for todo in todos:
            if todo.status == "blocked":
                # 의존성 확인
                dependencies = todo.metadata.dependency.depends_on

                if all(is_dependency_satisfied(dep) for dep in dependencies):
                    # Unblock
                    updated = todo.model_copy(update={
                        "status": "pending",
                        "version": todo.version + 1
                    })

                    updated.history.append({
                        "timestamp": updated.updated_at.isoformat(),
                        "action": "auto_unblock",
                        "reason": "Dependencies satisfied"
                    })

                    unblocked.append(updated)

        if unblocked:
            logger.info(f"Auto-unblocked {len(unblocked)} todos")

        return unblocked


# 글로벌 인스턴스 (싱글톤 패턴)
todo_dependency_manager = TodoDependencyManager()
