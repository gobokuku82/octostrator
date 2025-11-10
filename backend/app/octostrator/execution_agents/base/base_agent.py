"""Base Agent Abstract Class

Phase 1: 확장 가능한 Agent 아키텍처를 위한 BaseAgent 구현
각 Agent는 이 클래스를 상속받아 구현됩니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypedDict
from datetime import datetime
import logging
from enum import Enum

from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent 상태 정의"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    WAITING_DEPENDENCY = "waiting_dependency"


class AgentPriority(Enum):
    """Agent 실행 우선순위"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


# Import BaseAgentState from centralized state management
from backend.app.octostrator.states.base import BaseAgentState


class BaseAgent(ABC):
    """모든 Agent가 상속받는 추상 베이스 클래스

    각 Agent는 이 클래스를 상속받아 자신만의 LangGraph workflow를 구현합니다.
    Checkpoint 사용 여부는 선택적으로 결정할 수 있습니다.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        description: str = "",
        enable_checkpoint: bool = False,
        priority: AgentPriority = AgentPriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """BaseAgent 초기화

        Args:
            agent_id: Agent 고유 식별자 (예: "diet_agent", "workout_agent")
            agent_name: Agent 표시명 (예: "Diet Planning Agent")
            description: Agent 설명
            enable_checkpoint: Checkpoint 사용 여부
            priority: 실행 우선순위
            dependencies: 의존하는 다른 Agent ID 목록
            metadata: 추가 메타데이터
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.enable_checkpoint = enable_checkpoint
        self.priority = priority
        self.dependencies = dependencies or []
        self.metadata = metadata or {}

        # Runtime properties
        self.status = AgentStatus.IDLE
        self.graph: Optional[CompiledStateGraph] = None
        self.checkpointer: Optional[AsyncPostgresSaver] = None

        logger.info(
            f"[BaseAgent] Initialized {self.agent_name} "
            f"(ID: {self.agent_id}, Checkpoint: {self.enable_checkpoint})"
        )

    @abstractmethod
    def build_graph(self, llm=None) -> StateGraph:
        """Agent의 LangGraph workflow 구축 (추상 메서드)

        각 Agent는 이 메서드를 구현하여 자신만의 workflow를 정의합니다.

        Args:
            llm: Language Model 인스턴스

        Returns:
            StateGraph: 구축된 workflow graph
        """
        pass

    @abstractmethod
    async def process_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Agent의 주요 작업 처리 로직 (추상 메서드)

        각 Agent는 이 메서드를 구현하여 작업을 처리합니다.

        Args:
            task: 처리할 작업 정보
            context: 실행 컨텍스트 (user_id, session_id 등)

        Returns:
            처리 결과
        """
        pass

    async def initialize(self, llm=None, checkpointer: Optional[AsyncPostgresSaver] = None):
        """Agent 초기화 및 Graph 컴파일

        Args:
            llm: Language Model 인스턴스
            checkpointer: Checkpoint 저장소 (enable_checkpoint=True일 때만 필요)
        """
        try:
            # Graph 구축
            state_graph = self.build_graph(llm)

            # Checkpoint 설정
            if self.enable_checkpoint:
                if not checkpointer:
                    raise ValueError(f"{self.agent_name} requires checkpointer but none provided")
                self.checkpointer = checkpointer
                self.graph = state_graph.compile(checkpointer=checkpointer)
                logger.info(f"[BaseAgent] {self.agent_name} compiled with checkpointer")
            else:
                self.graph = state_graph.compile()
                logger.info(f"[BaseAgent] {self.agent_name} compiled without checkpointer (stateless)")

            self.status = AgentStatus.IDLE

        except Exception as e:
            logger.error(f"[BaseAgent] Failed to initialize {self.agent_name}: {e}")
            self.status = AgentStatus.FAILED
            raise

    async def execute(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Agent 실행

        Args:
            task: 실행할 작업
            context: 실행 컨텍스트
            thread_id: Checkpoint용 thread ID (enable_checkpoint=True일 때 필요)

        Returns:
            실행 결과
        """
        if not self.graph:
            raise RuntimeError(f"{self.agent_name} not initialized. Call initialize() first.")

        try:
            self.status = AgentStatus.RUNNING
            started_at = datetime.now().isoformat()

            logger.info(f"[BaseAgent] {self.agent_name} execution started")

            # Input 준비
            agent_input = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "task": task,
                "user_context": context,
                "messages": [],
                "status": "running",
                "started_at": started_at,
                "completed_at": None,
                "error": None,
                "result": None
            }

            # Graph 실행
            if self.enable_checkpoint and thread_id:
                # Checkpoint 있는 실행
                config = {"configurable": {"thread_id": f"{thread_id}_{self.agent_id}"}}
                result = await self.graph.ainvoke(agent_input, config=config)
            else:
                # Stateless 실행
                result = await self.graph.ainvoke(agent_input)

            # 상태 업데이트
            self.status = AgentStatus.COMPLETED
            completed_at = datetime.now().isoformat()

            logger.info(f"[BaseAgent] {self.agent_name} execution completed")

            return {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "status": "completed",
                "started_at": started_at,
                "completed_at": completed_at,
                "result": result.get("result", {})
            }

        except Exception as e:
            logger.error(f"[BaseAgent] {self.agent_name} execution failed: {e}")
            self.status = AgentStatus.FAILED

            return {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "status": "failed",
                "error": str(e),
                "started_at": started_at,
                "completed_at": datetime.now().isoformat()
            }

    def get_info(self) -> Dict[str, Any]:
        """Agent 정보 반환

        Returns:
            Agent 정보 딕셔너리
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "description": self.description,
            "enable_checkpoint": self.enable_checkpoint,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "metadata": self.metadata
        }

    def validate_dependencies(self, completed_agents: List[str]) -> bool:
        """의존성 검증

        Args:
            completed_agents: 완료된 Agent ID 목록

        Returns:
            모든 의존성이 만족되면 True
        """
        for dep in self.dependencies:
            if dep not in completed_agents:
                logger.debug(f"[BaseAgent] {self.agent_name} waiting for dependency: {dep}")
                return False
        return True

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id='{self.agent_id}', "
            f"name='{self.agent_name}', "
            f"checkpoint={self.enable_checkpoint}, "
            f"status={self.status.value})"
        )