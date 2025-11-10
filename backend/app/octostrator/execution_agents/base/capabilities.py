"""Agent Capabilities Definition

Agent가 제공할 수 있는 표준 능력들을 정의합니다.
역할 기반 라우팅과 동적 Agent 선택에 사용됩니다.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Capability(Enum):
    """시스템에서 사용하는 표준 능력"""

    # Health & Fitness
    MEAL_PLANNING = "meal_planning"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    EXERCISE_PLANNING = "exercise_planning"
    HEALTH_TRACKING = "health_tracking"
    FITNESS_ASSESSMENT = "fitness_assessment"

    # Schedule & Time Management
    SCHEDULING = "scheduling"
    CALENDAR_MANAGEMENT = "calendar_management"
    REMINDER = "reminder"
    TIME_OPTIMIZATION = "time_optimization"

    # TODO & Task Management
    TODO_MANAGEMENT = "todo_management"
    TASK_MANAGEMENT = "task_management"
    TASK_PRIORITIZATION = "task_prioritization"
    DEPENDENCY_RESOLUTION = "dependency_resolution"

    # Analysis & Reporting
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"
    PROGRESS_TRACKING = "progress_tracking"
    TREND_ANALYSIS = "trend_analysis"

    # Communication
    NOTIFICATION = "notification"
    EMAIL = "email"
    USER_INTERACTION = "user_interaction"
    MESSAGING = "messaging"

    # Coaching & Guidance
    COACHING = "coaching"
    MOTIVATION = "motivation"
    FEEDBACK = "feedback"
    RECOMMENDATION = "recommendation"

    # Member Care
    MEMBER_SUPPORT = "member_support"
    CONSULTATION = "consultation"
    ONBOARDING = "onboarding"

    # System & Meta
    PLANNING = "planning"
    ORCHESTRATION = "orchestration"
    MONITORING = "monitoring"
    ERROR_HANDLING = "error_handling"

    # Custom capabilities for extensibility
    CUSTOM = "custom"


class CapabilityBasedRouter:
    """능력 기반으로 Agent 선택하는 라우터"""

    def __init__(self, registry):
        """초기화

        Args:
            registry: AgentRegistry 인스턴스
        """
        self.registry = registry
        self._capability_cache: Dict[str, List[str]] = {}

    def find_agents_for_capability(self, capability: str) -> List[str]:
        """특정 능력을 가진 Agent 찾기

        Args:
            capability: 필요한 능력

        Returns:
            해당 능력을 가진 Agent ID 리스트
        """
        # 캐시 확인
        if capability in self._capability_cache:
            return self._capability_cache[capability]

        matching_agents = []

        for agent_id in self.registry.list_agents():
            agent = self.registry.get_agent_instance(agent_id)

            if agent and hasattr(agent, 'capabilities'):
                if capability in agent.capabilities:
                    matching_agents.append(agent_id)

        # 캐시 저장
        self._capability_cache[capability] = matching_agents

        logger.info(f"[CapabilityRouter] Found {len(matching_agents)} agents for {capability}")
        return matching_agents

    def find_best_agent(
        self,
        required_capability: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """특정 능력에 가장 적합한 Agent 찾기

        Args:
            required_capability: 필요한 능력
            context: 선택 컨텍스트 (우선순위, 부하 등 고려)

        Returns:
            가장 적합한 Agent ID 또는 None
        """
        candidates = self.find_agents_for_capability(required_capability)

        if not candidates:
            logger.warning(f"[CapabilityRouter] No agent found for {required_capability}")
            return None

        if len(candidates) == 1:
            return candidates[0]

        # 여러 후보가 있을 때 점수 기반 선택
        scored_candidates = []

        for agent_id in candidates:
            score = self._calculate_fitness_score(
                agent_id,
                required_capability,
                context
            )
            scored_candidates.append((agent_id, score))

        # 점수순 정렬
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        best_agent = scored_candidates[0][0]
        logger.info(
            f"[CapabilityRouter] Selected {best_agent} for {required_capability} "
            f"from {len(candidates)} candidates"
        )

        return best_agent

    def _calculate_fitness_score(
        self,
        agent_id: str,
        capability: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Agent 적합도 점수 계산

        Args:
            agent_id: Agent ID
            capability: 필요한 능력
            context: 평가 컨텍스트

        Returns:
            적합도 점수 (높을수록 좋음)
        """
        score = 0.0
        agent = self.registry.get_agent_instance(agent_id)

        if not agent:
            return 0.0

        # 주 능력인지 확인
        if hasattr(agent, 'primary_capabilities'):
            if capability in agent.primary_capabilities:
                score += 1.0  # 주 능력이면 보너스
            else:
                score += 0.5  # 보조 능력
        else:
            score += 0.5  # 기본 점수

        # 우선순위 고려
        if hasattr(agent, 'priority'):
            # 높은 우선순위일수록 높은 점수
            # (CRITICAL=1, HIGH=2, NORMAL=3, LOW=4)
            score += (5 - agent.priority.value) * 0.2

        # 컨텍스트 기반 추가 점수
        if context:
            # 특정 Agent 선호도
            if 'preferred_agent' in context:
                if agent_id == context['preferred_agent']:
                    score += 0.5

            # 이전 성공 이력
            if 'success_history' in context:
                success_rate = context['success_history'].get(agent_id, 0.5)
                score += success_rate * 0.3

        return score

    def find_alternative_agents(
        self,
        primary_agent: str,
        capability: str
    ) -> List[str]:
        """대체 가능한 Agent 찾기

        Args:
            primary_agent: 기본 Agent ID
            capability: 필요한 능력

        Returns:
            대체 가능한 Agent ID 리스트 (우선순위 순)
        """
        all_agents = self.find_agents_for_capability(capability)

        # Primary agent 제외
        alternatives = [a for a in all_agents if a != primary_agent]

        # 점수 기반 정렬
        scored = []
        for agent_id in alternatives:
            score = self._calculate_fitness_score(agent_id, capability, None)
            scored.append((agent_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [agent_id for agent_id, _ in scored]

    def get_capability_coverage(self) -> Dict[str, List[str]]:
        """모든 능력과 해당 Agent 매핑 조회

        Returns:
            능력별 Agent ID 리스트
        """
        coverage = {}

        # 모든 표준 능력 확인
        for capability in Capability:
            agents = self.find_agents_for_capability(capability.value)
            if agents:
                coverage[capability.value] = agents

        return coverage

    def validate_capability_coverage(self, required_capabilities: List[str]) -> Dict[str, bool]:
        """필요한 능력들의 커버리지 검증

        Args:
            required_capabilities: 필요한 능력 리스트

        Returns:
            각 능력의 사용 가능 여부
        """
        coverage = {}

        for capability in required_capabilities:
            agents = self.find_agents_for_capability(capability)
            coverage[capability] = len(agents) > 0

        return coverage

    def clear_cache(self):
        """능력 캐시 초기화"""
        self._capability_cache.clear()
        logger.info("[CapabilityRouter] Cache cleared")


def extend_capability(base_capability: Capability, extension: str) -> str:
    """기본 능력을 확장한 커스텀 능력 생성

    Args:
        base_capability: 기본 능력
        extension: 확장 이름

    Returns:
        확장된 능력 이름
    """
    return f"{base_capability.value}_{extension}"