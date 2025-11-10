"""Dependency Resolver

Agent 간 의존성 관리 및 실행 순서 결정
Topological Sort를 사용하여 순환 의존성을 감지하고 최적 실행 순서를 계산합니다.
"""

import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, deque
from enum import Enum

logger = logging.getLogger(__name__)


class DependencyStatus(Enum):
    """의존성 검증 상태"""
    VALID = "valid"  # 정상
    CIRCULAR = "circular"  # 순환 의존성
    MISSING = "missing"  # 누락된 의존성
    READY = "ready"  # 실행 가능


class ExecutionPlan:
    """Agent 실행 계획"""

    def __init__(self, agent_order: List[str], parallel_groups: List[List[str]]):
        """ExecutionPlan 초기화

        Args:
            agent_order: 순차 실행 순서
            parallel_groups: 병렬 실행 가능 그룹
        """
        self.agent_order = agent_order
        self.parallel_groups = parallel_groups
        self.executed_agents: Set[str] = set()
        self.failed_agents: Set[str] = set()

    def get_next_agents(self) -> List[str]:
        """다음 실행할 Agent 목록

        Returns:
            병렬 실행 가능한 Agent 목록
        """
        for group in self.parallel_groups:
            # 그룹 내 모든 Agent가 아직 실행 안 됐으면 반환
            if not any(agent in self.executed_agents for agent in group):
                return group
        return []

    def mark_completed(self, agent_id: str):
        """Agent 완료 표시

        Args:
            agent_id: 완료된 Agent ID
        """
        self.executed_agents.add(agent_id)

    def mark_failed(self, agent_id: str):
        """Agent 실패 표시

        Args:
            agent_id: 실패한 Agent ID
        """
        self.failed_agents.add(agent_id)
        self.executed_agents.add(agent_id)  # 실행은 됐으므로 추가

    def is_complete(self) -> bool:
        """모든 Agent 실행 완료 여부

        Returns:
            완료 여부
        """
        all_agents = set()
        for group in self.parallel_groups:
            all_agents.update(group)
        return all_agents == self.executed_agents

    def get_progress(self) -> Dict[str, Any]:
        """실행 진행 상황

        Returns:
            진행 상황 정보
        """
        total = len(self.agent_order)
        completed = len(self.executed_agents)
        failed = len(self.failed_agents)

        return {
            "total": total,
            "completed": completed - failed,
            "failed": failed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
            "is_complete": self.is_complete(),
        }


class DependencyResolver:
    """Agent 의존성 해결 및 실행 순서 관리"""

    def __init__(self):
        """DependencyResolver 초기화"""
        # Agent ID -> 의존하는 Agent ID 리스트
        self.dependencies: Dict[str, List[str]] = {}
        # Agent ID -> 이 Agent를 의존하는 Agent ID 리스트 (역방향)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)
        # 검증 캐시
        self._validation_cache: Optional[Dict[str, Any]] = None

        logger.info("[DependencyResolver] Initialized")

    def add_agent(self, agent_id: str, dependencies: Optional[List[str]] = None):
        """Agent 및 의존성 추가

        Args:
            agent_id: Agent ID
            dependencies: 의존하는 Agent ID 목록
        """
        self.dependencies[agent_id] = dependencies or []

        # 역방향 의존성 업데이트
        for dep in self.dependencies[agent_id]:
            self.dependents[dep].add(agent_id)

        # 캐시 무효화
        self._validation_cache = None

        logger.debug(f"[DependencyResolver] Added {agent_id} with dependencies: {dependencies}")

    def remove_agent(self, agent_id: str):
        """Agent 제거

        Args:
            agent_id: 제거할 Agent ID
        """
        if agent_id not in self.dependencies:
            return

        # 의존성 제거
        deps = self.dependencies.pop(agent_id, [])

        # 역방향 의존성 제거
        for dep in deps:
            self.dependents[dep].discard(agent_id)

        # 이 Agent를 의존하는 다른 Agent들의 의존성에서 제거
        for other_agent, other_deps in self.dependencies.items():
            if agent_id in other_deps:
                other_deps.remove(agent_id)

        # 역방향 의존성 딕셔너리에서 제거
        self.dependents.pop(agent_id, None)

        # 캐시 무효화
        self._validation_cache = None

        logger.debug(f"[DependencyResolver] Removed {agent_id}")

    def validate(self) -> Tuple[DependencyStatus, Optional[Dict[str, Any]]]:
        """모든 의존성 검증

        Returns:
            (상태, 세부 정보) 튜플
        """
        # 캐시된 결과가 있으면 반환
        if self._validation_cache is not None:
            return self._validation_cache["status"], self._validation_cache["details"]

        all_agents = set(self.dependencies.keys())
        issues = {
            "missing": {},
            "circular": []
        }

        # 1. 누락된 의존성 검사
        for agent_id, deps in self.dependencies.items():
            missing = [dep for dep in deps if dep not in all_agents]
            if missing:
                issues["missing"][agent_id] = missing

        if issues["missing"]:
            result = (DependencyStatus.MISSING, issues)
            self._validation_cache = {"status": result[0], "details": result[1]}
            return result

        # 2. 순환 의존성 검사 (DFS 사용)
        visited = set()
        rec_stack = set()

        def has_cycle(agent: str, path: List[str]) -> Optional[List[str]]:
            visited.add(agent)
            rec_stack.add(agent)
            path.append(agent)

            for neighbor in self.dependencies.get(agent, []):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # 순환 발견
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(agent)
            return None

        for agent_id in all_agents:
            if agent_id not in visited:
                cycle = has_cycle(agent_id, [])
                if cycle:
                    issues["circular"].append(cycle)

        if issues["circular"]:
            result = (DependencyStatus.CIRCULAR, issues)
            self._validation_cache = {"status": result[0], "details": result[1]}
            return result

        # 모든 검증 통과
        result = (DependencyStatus.VALID, None)
        self._validation_cache = {"status": result[0], "details": result[1]}
        return result

    def topological_sort(self) -> Optional[List[str]]:
        """위상 정렬로 실행 순서 계산

        Returns:
            Agent 실행 순서 또는 None (순환 의존성이 있는 경우)
        """
        # 의존성 검증
        status, _ = self.validate()
        if status != DependencyStatus.VALID:
            return None

        # Kahn's Algorithm 사용
        in_degree = {agent: 0 for agent in self.dependencies}

        # In-degree 계산
        for agent, deps in self.dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # In-degree가 0인 노드로 시작
        queue = deque([agent for agent, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # 현재 노드를 의존하는 노드들의 in-degree 감소
            for dependent in self.dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # 모든 노드를 방문했는지 확인
        if len(result) != len(self.dependencies):
            return None  # 순환 의존성 존재

        return result

    def get_parallel_groups(self) -> Optional[List[List[str]]]:
        """병렬 실행 가능한 Agent 그룹 계산

        Returns:
            병렬 실행 그룹 리스트 또는 None
        """
        # 의존성 검증
        status, _ = self.validate()
        if status != DependencyStatus.VALID:
            return None

        # Level-based grouping
        levels = {}
        in_degree = {agent: len(self.dependencies[agent]) for agent in self.dependencies}

        # Level 0: 의존성이 없는 Agent들
        current_level = 0
        queue = deque([agent for agent, degree in in_degree.items() if degree == 0])

        for agent in queue:
            levels[agent] = current_level

        processed = set(queue)

        while queue:
            next_queue = deque()

            for current in queue:
                # 이 Agent를 의존하는 Agent들 확인
                for dependent in self.dependents[current]:
                    if dependent not in processed:
                        # 모든 의존성이 처리되었는지 확인
                        deps_satisfied = all(dep in processed for dep in self.dependencies[dependent])

                        if deps_satisfied:
                            next_queue.append(dependent)
                            processed.add(dependent)
                            # Level은 의존성 중 최대 level + 1
                            dep_levels = [levels[dep] for dep in self.dependencies[dependent]]
                            levels[dependent] = max(dep_levels) + 1 if dep_levels else 0

            queue = next_queue

        # Level별로 그룹핑
        groups = defaultdict(list)
        for agent, level in levels.items():
            groups[level].append(agent)

        # Level 순서대로 반환
        return [groups[level] for level in sorted(groups.keys())]

    def create_execution_plan(self, selected_agents: Optional[List[str]] = None) -> Optional[ExecutionPlan]:
        """실행 계획 생성

        Args:
            selected_agents: 실행할 Agent ID 목록 (None이면 전체)

        Returns:
            ExecutionPlan 또는 None
        """
        # 선택된 Agent만 포함하는 부분 그래프 생성
        if selected_agents:
            sub_resolver = DependencyResolver()
            for agent in selected_agents:
                if agent in self.dependencies:
                    # 선택된 Agent 내에서만 유효한 의존성
                    valid_deps = [
                        dep for dep in self.dependencies[agent]
                        if dep in selected_agents
                    ]
                    sub_resolver.add_agent(agent, valid_deps)

            order = sub_resolver.topological_sort()
            groups = sub_resolver.get_parallel_groups()
        else:
            order = self.topological_sort()
            groups = self.get_parallel_groups()

        if order is None or groups is None:
            return None

        return ExecutionPlan(agent_order=order, parallel_groups=groups)

    def can_execute(self, agent_id: str, completed_agents: Set[str]) -> bool:
        """Agent 실행 가능 여부 확인

        Args:
            agent_id: 확인할 Agent ID
            completed_agents: 완료된 Agent ID 집합

        Returns:
            실행 가능 여부
        """
        if agent_id not in self.dependencies:
            return False

        # 모든 의존성이 완료되었는지 확인
        for dep in self.dependencies[agent_id]:
            if dep not in completed_agents:
                return False

        return True

    def get_blocked_agents(self, completed_agents: Set[str]) -> Dict[str, List[str]]:
        """블록된 Agent와 원인 조회

        Args:
            completed_agents: 완료된 Agent ID 집합

        Returns:
            블록된 Agent와 대기 중인 의존성
        """
        blocked = {}

        for agent_id in self.dependencies:
            if agent_id not in completed_agents:
                waiting_for = [
                    dep for dep in self.dependencies[agent_id]
                    if dep not in completed_agents
                ]
                if waiting_for:
                    blocked[agent_id] = waiting_for

        return blocked

    def visualize(self) -> str:
        """의존성 그래프 시각화 (텍스트)

        Returns:
            ASCII 아트 형태의 그래프
        """
        lines = ["=== Agent Dependency Graph ===\n"]

        # 병렬 그룹 표시
        groups = self.get_parallel_groups()
        if groups:
            for i, group in enumerate(groups):
                lines.append(f"Level {i}: [{', '.join(group)}]")

                # 다음 레벨과의 연결 표시
                if i < len(groups) - 1:
                    lines.append("    ↓")

        lines.append("\n=== Dependency Details ===")

        # 각 Agent의 의존성 표시
        for agent_id in sorted(self.dependencies.keys()):
            deps = self.dependencies[agent_id]
            if deps:
                lines.append(f"{agent_id} depends on: {', '.join(deps)}")
            else:
                lines.append(f"{agent_id} (no dependencies)")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """의존성 통계

        Returns:
            통계 정보
        """
        total_agents = len(self.dependencies)
        total_dependencies = sum(len(deps) for deps in self.dependencies.values())

        # 의존성 없는 Agent (진입점)
        entry_points = [
            agent for agent, deps in self.dependencies.items()
            if not deps
        ]

        # 가장 많은 의존성을 가진 Agent
        max_deps_agent = None
        max_deps_count = 0
        for agent, deps in self.dependencies.items():
            if len(deps) > max_deps_count:
                max_deps_count = len(deps)
                max_deps_agent = agent

        # 가장 많이 의존되는 Agent
        most_depended = None
        most_depended_count = 0
        for agent, dependents in self.dependents.items():
            if len(dependents) > most_depended_count:
                most_depended_count = len(dependents)
                most_depended = agent

        return {
            "total_agents": total_agents,
            "total_dependencies": total_dependencies,
            "average_dependencies": total_dependencies / total_agents if total_agents > 0 else 0,
            "entry_points": entry_points,
            "max_dependencies": {
                "agent": max_deps_agent,
                "count": max_deps_count
            } if max_deps_agent else None,
            "most_depended": {
                "agent": most_depended,
                "count": most_depended_count
            } if most_depended else None,
            "parallel_groups": len(self.get_parallel_groups()) if self.get_parallel_groups() else 0
        }


# 전역 DependencyResolver 인스턴스
_dependency_resolver: Optional[DependencyResolver] = None


def get_dependency_resolver() -> DependencyResolver:
    """DependencyResolver 싱글톤 인스턴스 가져오기

    Returns:
        DependencyResolver 인스턴스
    """
    global _dependency_resolver

    if _dependency_resolver is None:
        _dependency_resolver = DependencyResolver()

    return _dependency_resolver