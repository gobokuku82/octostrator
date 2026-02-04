"""Resource Planner - 자원 관리 및 할당 시스템"""

from typing import Dict, List, Optional, Tuple, Any
from backend.app.core.logging import get_logger
from backend.app.dream_agent.models import TodoItem
from backend.app.dream_agent.models.resource import (
    AgentResource, ResourceAllocation, ResourceConstraints, ResourcePlan,
    create_agent_resource, create_resource_allocation, create_resource_constraints
)

logger = get_logger(__name__)


class ResourcePlanner:
    """
    자원 관리 및 할당 시스템

    기능:
    - 에이전트 자원 등록 및 관리
    - Todo에 대한 최적 에이전트 할당
    - 병렬 실행 계획 수립
    - 비용 최적화
    - 가용성 추적
    """

    def __init__(self):
        """초기화"""
        self.agents: Dict[str, AgentResource] = {}  # agent_id -> AgentResource
        self.agent_by_name: Dict[str, str] = {}  # agent_name -> agent_id
        self.resource_plans: Dict[str, ResourcePlan] = {}  # resource_plan_id -> ResourcePlan

        # 기본 에이전트 등록
        self._register_default_agents()

        logger.info("ResourcePlanner initialized")

    # ============================================================
    # Agent Registry
    # ============================================================

    def _register_default_agents(self):
        """기본 에이전트 등록"""

        # ML Agents (9개 전체 등록)
        ml_agents = [
            # 기본 파이프라인 Agent (7개)
            ("collector", 1, False, 0.0, 30.0),  # (name, concurrent, has_cost, cost, avg_time)
            ("preprocessor", 2, False, 0.0, 20.0),
            ("keyword_extractor", 1, False, 0.0, 15.0),  # 키워드 추출
            ("extractor", 1, False, 0.0, 15.0),  # keyword_extractor 별칭
            ("sentiment_analyzer", 1, True, 0.05, 45.0),  # ABSA 감성 분석
            ("absa_analyzer", 1, True, 0.05, 45.0),  # sentiment_analyzer 별칭
            ("problem_classifier", 1, True, 0.03, 30.0),  # 문제 분류
            ("google_trends", 1, False, 0.0, 40.0),  # 트렌드 분석 (API 비용 없음)
            ("insight", 1, True, 0.08, 45.0),  # 인사이트 생성
            ("insight_generator", 1, True, 0.08, 45.0),  # insight 별칭
            # 추가 분석 Agent (2개)
            ("hashtag_analyzer", 1, False, 0.0, 20.0),  # SNS 해시태그 분석
            ("competitor_analyzer", 1, True, 0.10, 60.0),  # 경쟁사 비교 분석
            # 레거시 별칭 (하위 호환성)
            ("analyzer", 1, True, 0.05, 60.0),  # 레거시: sentiment_analyzer로 라우팅
        ]

        for name, concurrent, has_cost, cost, avg_time in ml_agents:
            self.register_agent(
                agent_name=name,
                agent_type="ml",
                max_concurrent_tasks=concurrent,
                has_cost=has_cost,
                cost_per_execution=cost,
                average_execution_time_sec=avg_time
            )

        # Biz Agents
        biz_agents = [
            ("report_agent", 1, True, 0.10, 40.0),
            ("dashboard_agent", 1, True, 0.12, 50.0),
            ("storyboard_agent", 1, True, 0.15, 60.0),
            ("video_agent", 1, True, 0.30, 120.0),
            ("ad_creative_agent", 1, True, 0.20, 80.0),
        ]

        for name, concurrent, has_cost, cost, avg_time in biz_agents:
            self.register_agent(
                agent_name=name,
                agent_type="biz",
                max_concurrent_tasks=concurrent,
                has_cost=has_cost,
                cost_per_execution=cost,
                average_execution_time_sec=avg_time
            )

        logger.info(
            f"Registered {len(ml_agents)} ML agents and {len(biz_agents)} Biz agents"
        )

    def register_agent(
        self,
        agent_name: str,
        agent_type: str,
        max_concurrent_tasks: int = 1,
        has_cost: bool = False,
        cost_per_execution: float = 0.0,
        average_execution_time_sec: float = 60.0
    ) -> AgentResource:
        """
        에이전트 등록

        Args:
            agent_name: 에이전트 이름
            agent_type: 에이전트 타입 (ml, biz, utility)
            max_concurrent_tasks: 최대 동시 처리 수
            has_cost: 비용 여부
            cost_per_execution: 실행당 비용
            average_execution_time_sec: 평균 실행 시간

        Returns:
            등록된 AgentResource
        """
        agent = create_agent_resource(
            agent_name=agent_name,
            agent_type=agent_type,
            max_concurrent_tasks=max_concurrent_tasks,
            has_cost=has_cost,
            cost_per_execution=cost_per_execution,
            average_execution_time_sec=average_execution_time_sec
        )

        self.agents[agent.agent_id] = agent
        self.agent_by_name[agent_name] = agent.agent_id

        logger.debug(f"Registered agent: {agent_name} (id={agent.agent_id})")

        return agent

    def get_agent_by_name(self, agent_name: str) -> Optional[AgentResource]:
        """이름으로 에이전트 조회"""
        agent_id = self.agent_by_name.get(agent_name)
        if not agent_id:
            return None
        return self.agents.get(agent_id)

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentResource]:
        """ID로 에이전트 조회"""
        return self.agents.get(agent_id)

    def list_available_agents(
        self,
        agent_type: Optional[str] = None
    ) -> List[AgentResource]:
        """
        사용 가능한 에이전트 조회

        Args:
            agent_type: 필터링할 타입 (None이면 전체)

        Returns:
            사용 가능한 AgentResource 리스트
        """
        agents = [
            agent for agent in self.agents.values()
            if agent.is_available()
        ]

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]

        return agents

    # ============================================================
    # Resource Allocation
    # ============================================================

    def allocate_resources(
        self,
        plan_id: str,
        todos: List[TodoItem],
        constraints: Optional[ResourceConstraints] = None
    ) -> ResourcePlan:
        """
        자원 할당

        Args:
            plan_id: Plan ID
            todos: 할당할 TodoItem 리스트
            constraints: 자원 제약 조건

        Returns:
            ResourcePlan
        """
        if constraints is None:
            constraints = create_resource_constraints()

        resource_plan = ResourcePlan(
            plan_id=plan_id,
            constraints=constraints
        )

        # 각 todo에 대해 agent 할당
        allocations = []
        for todo in todos:
            allocation = self._allocate_todo(todo, constraints)
            if allocation:
                allocations.append(allocation)
            else:
                logger.warning(f"Failed to allocate agent for todo: {todo.id}")

        resource_plan.allocations = allocations

        # 예상 정보 계산
        self._calculate_estimates(resource_plan)

        # 최적화 점수 계산
        self._calculate_optimization_score(resource_plan)

        # 저장
        self.resource_plans[resource_plan.resource_plan_id] = resource_plan

        logger.info(
            f"Resource plan created: {resource_plan.resource_plan_id}, "
            f"allocations={len(allocations)}, "
            f"estimated_cost=${resource_plan.estimated_total_cost:.2f}, "
            f"estimated_duration={resource_plan.estimated_total_duration_sec}s"
        )

        return resource_plan

    def _allocate_todo(
        self,
        todo: TodoItem,
        constraints: ResourceConstraints
    ) -> Optional[ResourceAllocation]:
        """
        단일 todo에 대한 agent 할당

        Args:
            todo: TodoItem
            constraints: 제약 조건

        Returns:
            ResourceAllocation 또는 None
        """
        # Tool 정보에서 agent 이름 추출
        agent_name = todo.metadata.execution.tool
        if not agent_name:
            logger.warning(f"Todo {todo.id} has no tool specified")
            return None

        # Agent 찾기
        agent = self.get_agent_by_name(agent_name)
        if not agent:
            logger.warning(f"Agent not found: {agent_name}")
            return None

        # Timeout 설정
        timeout = todo.metadata.execution.timeout
        estimated_duration = timeout if timeout else agent.average_execution_time_sec

        # Allocation 생성
        allocation = create_resource_allocation(
            todo_id=todo.id,
            agent=agent,
            estimated_duration_sec=estimated_duration
        )

        return allocation

    def _calculate_estimates(self, resource_plan: ResourcePlan):
        """예상 정보 계산 (총 시간, 총 비용, 병렬 그룹 수)"""

        # 총 비용
        resource_plan.estimated_total_cost = sum(
            alloc.estimated_cost for alloc in resource_plan.allocations
        )

        # 총 시간 (순차 실행 기준)
        resource_plan.estimated_total_duration_sec = sum(
            alloc.estimated_duration_sec for alloc in resource_plan.allocations
        )

        # 병렬 그룹 수 (간단한 추정 - 실제는 dependency graph 필요)
        # 여기서는 max_total_parallel로 나눈 값으로 추정
        max_parallel = resource_plan.constraints.max_total_parallel
        total_tasks = len(resource_plan.allocations)
        resource_plan.estimated_parallel_groups = (total_tasks + max_parallel - 1) // max_parallel

    def _calculate_optimization_score(self, resource_plan: ResourcePlan):
        """최적화 점수 계산 (0.0 ~ 1.0)"""

        score = 1.0
        notes = []

        # 비용 제약 체크
        if resource_plan.constraints.max_total_cost:
            cost_ratio = resource_plan.estimated_total_cost / resource_plan.constraints.max_total_cost
            if cost_ratio > 1.0:
                score *= 0.5
                notes.append(f"Cost exceeds limit: ${resource_plan.estimated_total_cost:.2f} > ${resource_plan.constraints.max_total_cost:.2f}")
            elif cost_ratio > 0.9:
                score *= 0.8
                notes.append("Cost near limit")

        # 시간 제약 체크
        if resource_plan.constraints.max_total_duration_sec:
            duration_ratio = resource_plan.estimated_total_duration_sec / resource_plan.constraints.max_total_duration_sec
            if duration_ratio > 1.0:
                score *= 0.5
                notes.append(f"Duration exceeds limit: {resource_plan.estimated_total_duration_sec}s > {resource_plan.constraints.max_total_duration_sec}s")

        # 최적화 목표에 따른 점수 조정
        optimize_for = resource_plan.constraints.optimize_for
        if optimize_for == "cost":
            # 비용이 낮을수록 점수 높음
            avg_cost_per_task = resource_plan.estimated_total_cost / max(len(resource_plan.allocations), 1)
            if avg_cost_per_task < 0.05:
                score *= 1.2
                notes.append("Low cost per task")
        elif optimize_for == "speed":
            # 병렬화 가능성이 높을수록 점수 높음
            if resource_plan.estimated_parallel_groups <= 3:
                score *= 1.2
                notes.append("High parallelization potential")

        # 최종 점수는 1.0 초과 불가
        resource_plan.optimization_score = min(score, 1.0)
        resource_plan.optimization_notes = notes

    # ============================================================
    # Agent Status Management
    # ============================================================

    def assign_task_to_agent(
        self,
        agent_id: str,
        todo_id: str
    ) -> bool:
        """
        에이전트에 task 할당

        Args:
            agent_id: Agent ID
            todo_id: Todo ID

        Returns:
            성공 여부
        """
        agent = self.agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return False

        if not agent.can_accept_task():
            logger.warning(f"Agent {agent.agent_name} cannot accept more tasks")
            return False

        agent.assign_task(todo_id)
        logger.debug(f"Task {todo_id} assigned to agent {agent.agent_name}")

        return True

    def release_task_from_agent(
        self,
        agent_id: str,
        todo_id: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> bool:
        """
        에이전트에서 task 해제

        Args:
            agent_id: Agent ID
            todo_id: Todo ID
            success: 성공 여부
            error: 에러 메시지

        Returns:
            성공 여부
        """
        agent = self.agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return False

        agent.release_task(todo_id, success=success)

        if error:
            agent.last_error = error

        logger.debug(
            f"Task {todo_id} released from agent {agent.agent_name} "
            f"(success={success})"
        )

        return True

    def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        에이전트 상태 조회

        Args:
            agent_name: Agent 이름

        Returns:
            상태 정보 dict
        """
        agent = self.get_agent_by_name(agent_name)
        if not agent:
            return None

        return {
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "status": agent.status,
            "is_available": agent.is_available(),
            "current_tasks": len(agent.current_tasks),
            "max_concurrent_tasks": agent.max_concurrent_tasks,
            "success_rate": agent.success_rate,
            "total_executions": agent.total_executions,
            "last_execution_at": agent.last_execution_at,
            "last_error": agent.last_error
        }

    # ============================================================
    # Cost Optimization
    # ============================================================

    def estimate_cost(
        self,
        todos: List[TodoItem],
        constraints: Optional[ResourceConstraints] = None
    ) -> Dict[str, Any]:
        """
        비용 예상

        Args:
            todos: TodoItem 리스트
            constraints: 제약 조건

        Returns:
            비용 정보 dict
        """
        if constraints is None:
            constraints = create_resource_constraints()

        total_cost = 0.0
        total_duration = 0.0
        cost_breakdown = {}

        for todo in todos:
            agent_name = todo.metadata.execution.tool
            if not agent_name:
                continue

            agent = self.get_agent_by_name(agent_name)
            if not agent:
                continue

            # 예상 시간
            timeout = todo.metadata.execution.timeout
            duration = timeout if timeout else agent.average_execution_time_sec

            # 예상 비용
            cost = 0.0
            if agent.has_cost:
                if agent.cost_per_execution > 0:
                    cost = agent.cost_per_execution
                elif agent.cost_per_second > 0:
                    cost = agent.cost_per_second * duration

            total_cost += cost
            total_duration += duration

            if agent_name not in cost_breakdown:
                cost_breakdown[agent_name] = {"count": 0, "cost": 0.0, "duration": 0.0}

            cost_breakdown[agent_name]["count"] += 1
            cost_breakdown[agent_name]["cost"] += cost
            cost_breakdown[agent_name]["duration"] += duration

        # 병렬 실행 시 예상 시간
        max_parallel = constraints.max_total_parallel
        estimated_parallel_duration = total_duration / max_parallel

        return {
            "total_cost": total_cost,
            "total_duration_sequential": total_duration,
            "estimated_duration_parallel": estimated_parallel_duration,
            "max_parallel": max_parallel,
            "cost_breakdown": cost_breakdown,
            "within_budget": (
                total_cost <= constraints.max_total_cost
                if constraints.max_total_cost
                else True
            )
        }

    def optimize_allocation(
        self,
        resource_plan: ResourcePlan,
        optimize_for: str = "balanced"
    ) -> ResourcePlan:
        """
        자원 할당 최적화

        Args:
            resource_plan: 최적화할 ResourcePlan
            optimize_for: 최적화 목표 (speed, cost, balanced)

        Returns:
            최적화된 ResourcePlan
        """
        # 현재는 간단한 최적화만 수행
        # 향후 더 복잡한 최적화 알고리즘 적용 가능

        resource_plan.constraints.optimize_for = optimize_for

        # 최적화 점수 재계산
        self._calculate_optimization_score(resource_plan)

        logger.info(
            f"Resource plan optimized for '{optimize_for}': "
            f"score={resource_plan.optimization_score:.2f}"
        )

        return resource_plan

    # ============================================================
    # Resource Plan Management
    # ============================================================

    def get_resource_plan(self, resource_plan_id: str) -> Optional[ResourcePlan]:
        """자원 계획 조회"""
        return self.resource_plans.get(resource_plan_id)

    def update_allocation_status(
        self,
        allocation_id: str,
        status: str,
        actual_duration_sec: Optional[float] = None,
        actual_cost: Optional[float] = None,
        success: bool = False,
        error: Optional[str] = None
    ) -> bool:
        """
        할당 상태 업데이트

        Args:
            allocation_id: Allocation ID
            status: 새 상태
            actual_duration_sec: 실제 실행 시간
            actual_cost: 실제 비용
            success: 성공 여부
            error: 에러 메시지

        Returns:
            성공 여부
        """
        # 모든 resource plan에서 allocation 찾기
        for resource_plan in self.resource_plans.values():
            for allocation in resource_plan.allocations:
                if allocation.allocation_id == allocation_id:
                    allocation.status = status

                    if actual_duration_sec is not None:
                        allocation.actual_duration_sec = actual_duration_sec

                    if actual_cost is not None:
                        allocation.actual_cost = actual_cost

                    allocation.success = success

                    if error:
                        allocation.error = error

                    if status == "completed":
                        from datetime import datetime
                        allocation.completed_at = datetime.now()

                    logger.debug(
                        f"Allocation {allocation_id} updated: status={status}"
                    )

                    return True

        logger.warning(f"Allocation not found: {allocation_id}")
        return False


# ============================================================
# Global Instance (Singleton Pattern)
# ============================================================

_resource_planner_instance: Optional[ResourcePlanner] = None


def get_resource_planner() -> ResourcePlanner:
    """ResourcePlanner 싱글톤 인스턴스 반환"""
    global _resource_planner_instance
    if _resource_planner_instance is None:
        _resource_planner_instance = ResourcePlanner()
    return _resource_planner_instance


# 글로벌 인스턴스 (편의용)
resource_planner = get_resource_planner()
