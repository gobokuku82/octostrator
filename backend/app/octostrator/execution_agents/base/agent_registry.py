"""Agent Registry

동적 Agent 관리를 위한 Registry 패턴 구현
10+ Agent를 효율적으로 관리하고 검색합니다.
"""

import logging
from typing import Dict, List, Optional, Type, Any
from pathlib import Path
import importlib
import inspect

from .base_agent import BaseAgent, AgentStatus, AgentPriority

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent Registry for Dynamic Agent Management

    Agent를 동적으로 등록, 검색, 관리하는 싱글톤 클래스
    """

    _instance: Optional["AgentRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "AgentRegistry":
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Registry 초기화"""
        if not self._initialized:
            self._agents: Dict[str, Type[BaseAgent]] = {}
            self._instances: Dict[str, BaseAgent] = {}
            self._metadata: Dict[str, Dict[str, Any]] = {}
            self._initialized = True
            logger.info("[AgentRegistry] Initialized")

    def register(
        self,
        agent_class: Type[BaseAgent],
        agent_id: Optional[str] = None,
        override: bool = False
    ) -> bool:
        """Agent 클래스 등록

        Args:
            agent_class: BaseAgent를 상속한 Agent 클래스
            agent_id: Agent ID (None이면 클래스명에서 추출)
            override: 기존 Agent 덮어쓰기 여부

        Returns:
            등록 성공 여부
        """
        # Agent ID 결정
        if agent_id is None:
            # 클래스명에서 자동 생성 (예: DietAgent -> diet_agent)
            class_name = agent_class.__name__
            if class_name.endswith("Agent"):
                class_name = class_name[:-5]  # Remove "Agent" suffix
            agent_id = self._camel_to_snake(class_name) + "_agent"

        # 중복 검사
        if agent_id in self._agents and not override:
            logger.warning(f"[AgentRegistry] Agent {agent_id} already registered")
            return False

        # 등록
        self._agents[agent_id] = agent_class
        logger.info(f"[AgentRegistry] Registered agent: {agent_id} -> {agent_class.__name__}")

        return True

    def register_decorator(self, agent_id: Optional[str] = None):
        """데코레이터를 통한 Agent 등록

        Usage:
            @agent_registry.register_decorator("diet_agent")
            class DietAgent(BaseAgent):
                ...
        """
        def decorator(agent_class: Type[BaseAgent]):
            self.register(agent_class, agent_id)
            return agent_class
        return decorator

    def discover_agents(self, path: str = "backend/app/octostrator/execution_agents") -> int:
        """지정된 경로에서 Agent 자동 검색 및 등록

        Args:
            path: Agent 모듈이 있는 경로

        Returns:
            발견된 Agent 수
        """
        discovered = 0
        agents_path = Path(path)

        if not agents_path.exists():
            logger.warning(f"[AgentRegistry] Path does not exist: {path}")
            return 0

        # 모든 Python 파일 검색
        for py_file in agents_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip private modules

            try:
                # 모듈 경로 구성
                relative_path = py_file.relative_to(Path.cwd())
                module_path = str(relative_path).replace("/", ".").replace("\\", ".")[:-3]

                # 모듈 임포트
                module = importlib.import_module(module_path)

                # BaseAgent 서브클래스 찾기
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseAgent) and obj != BaseAgent:
                        if self.register(obj):
                            discovered += 1

            except Exception as e:
                logger.debug(f"[AgentRegistry] Failed to import {py_file}: {e}")

        logger.info(f"[AgentRegistry] Discovered {discovered} agents from {path}")
        return discovered

    def get_agent_class(self, agent_id: str) -> Optional[Type[BaseAgent]]:
        """등록된 Agent 클래스 가져오기

        Args:
            agent_id: Agent ID

        Returns:
            Agent 클래스 또는 None
        """
        return self._agents.get(agent_id)

    def create_agent(
        self,
        agent_id: str,
        agent_name: Optional[str] = None,
        **kwargs
    ) -> Optional[BaseAgent]:
        """Agent 인스턴스 생성

        Args:
            agent_id: Agent ID
            agent_name: Agent 이름 (옵션)
            **kwargs: Agent 초기화 인자

        Returns:
            생성된 Agent 인스턴스 또는 None
        """
        agent_class = self.get_agent_class(agent_id)
        if not agent_class:
            logger.error(f"[AgentRegistry] Agent not found: {agent_id}")
            return None

        try:
            # Agent 인스턴스 생성
            if agent_name is None:
                agent_name = agent_id.replace("_", " ").title()

            agent = agent_class(
                agent_id=agent_id,
                agent_name=agent_name,
                **kwargs
            )

            # 인스턴스 캐싱
            self._instances[agent_id] = agent

            logger.info(f"[AgentRegistry] Created agent instance: {agent_id}")
            return agent

        except Exception as e:
            logger.error(f"[AgentRegistry] Failed to create agent {agent_id}: {e}")
            return None

    def get_agent_instance(self, agent_id: str) -> Optional[BaseAgent]:
        """캐시된 Agent 인스턴스 가져오기

        Args:
            agent_id: Agent ID

        Returns:
            Agent 인스턴스 또는 None
        """
        return self._instances.get(agent_id)

    def list_agents(self, filter_by: Optional[Dict[str, Any]] = None) -> List[str]:
        """등록된 Agent 목록 조회

        Args:
            filter_by: 필터 조건 (예: {"enable_checkpoint": True})

        Returns:
            Agent ID 목록
        """
        agent_ids = list(self._agents.keys())

        if filter_by:
            filtered = []
            for agent_id in agent_ids:
                agent_instance = self.get_agent_instance(agent_id)
                if agent_instance:
                    match = True
                    for key, value in filter_by.items():
                        if not hasattr(agent_instance, key) or getattr(agent_instance, key) != value:
                            match = False
                            break
                    if match:
                        filtered.append(agent_id)
            return filtered

        return agent_ids

    def get_agents_by_priority(self, priority: AgentPriority) -> List[str]:
        """우선순위별 Agent 목록 조회

        Args:
            priority: 우선순위

        Returns:
            해당 우선순위의 Agent ID 목록
        """
        agents = []
        for agent_id in self._agents.keys():
            instance = self.get_agent_instance(agent_id)
            if instance and instance.priority == priority:
                agents.append(agent_id)
        return agents

    def get_agents_with_checkpoint(self) -> List[str]:
        """Checkpoint를 사용하는 Agent 목록 조회

        Returns:
            Checkpoint 사용 Agent ID 목록
        """
        return self.list_agents(filter_by={"enable_checkpoint": True})

    def get_agent_dependencies(self, agent_id: str) -> List[str]:
        """Agent의 의존성 목록 조회

        Args:
            agent_id: Agent ID

        Returns:
            의존하는 Agent ID 목록
        """
        agent = self.get_agent_instance(agent_id)
        if agent:
            return agent.dependencies
        return []

    def validate_all_dependencies(self) -> Dict[str, List[str]]:
        """모든 Agent의 의존성 검증

        Returns:
            문제가 있는 의존성 정보
        """
        issues = {}
        all_agents = set(self._agents.keys())

        for agent_id in all_agents:
            agent = self.get_agent_instance(agent_id)
            if agent:
                for dep in agent.dependencies:
                    if dep not in all_agents:
                        if agent_id not in issues:
                            issues[agent_id] = []
                        issues[agent_id].append(f"Missing dependency: {dep}")

        return issues

    def clear(self):
        """Registry 초기화"""
        self._agents.clear()
        self._instances.clear()
        self._metadata.clear()
        logger.info("[AgentRegistry] Cleared all agents")

    def get_stats(self) -> Dict[str, Any]:
        """Registry 통계 정보

        Returns:
            통계 정보 딕셔너리
        """
        total_agents = len(self._agents)
        instantiated = len(self._instances)
        with_checkpoint = len(self.get_agents_with_checkpoint())

        priority_counts = {}
        for priority in AgentPriority:
            count = len(self.get_agents_by_priority(priority))
            if count > 0:
                priority_counts[priority.name] = count

        return {
            "total_registered": total_agents,
            "instantiated": instantiated,
            "with_checkpoint": with_checkpoint,
            "without_checkpoint": total_agents - with_checkpoint,
            "by_priority": priority_counts
        }

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """CamelCase를 snake_case로 변환

        Args:
            name: CamelCase 문자열

        Returns:
            snake_case 문자열
        """
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"AgentRegistry("
            f"total={stats['total_registered']}, "
            f"instantiated={stats['instantiated']}, "
            f"checkpoint={stats['with_checkpoint']})"
        )


# 전역 Registry 인스턴스
agent_registry = AgentRegistry()


def register_agent(agent_id: Optional[str] = None):
    """Agent 등록 데코레이터 (편의 함수)

    Usage:
        @register_agent("diet_agent")
        class DietAgent(BaseAgent):
            ...
    """
    return agent_registry.register_decorator(agent_id)