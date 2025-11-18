"""Agent Manager - Routes tasks to appropriate agents"""

from typing import Dict, Any, List, Optional
from loguru import logger

from .base_agent import BaseAgent
from .search_agent import SearchAgent
from .analysis_agent import AnalysisAgent
from .document_agent import DocumentAgent
from .code_agent import CodeAgent


class AgentManager:
    """에이전트 관리 및 라우팅"""

    def __init__(self):
        """Initialize agent manager with all available agents"""
        self.agents: List[BaseAgent] = [
            SearchAgent(),
            AnalysisAgent(),
            DocumentAgent(),
            CodeAgent(),
        ]

        self.agent_map = {agent.name: agent for agent in self.agents}

        logger.info(f"AgentManager initialized with {len(self.agents)} agents")

    def get_agent_for_task(self, task_type: str) -> Optional[BaseAgent]:
        """Get the best agent for a given task type

        Args:
            task_type: Type of task (e.g., "search", "analysis", etc.)

        Returns:
            Best matching agent or None
        """
        for agent in self.agents:
            if agent.can_handle(task_type):
                logger.info(f"Task type '{task_type}' matched to {agent.name}")
                return agent

        # Default to first agent if no match (fallback)
        logger.warning(f"No agent matched for task type '{task_type}', using default")
        return self.agents[0] if self.agents else None

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with the appropriate agent

        Args:
            task: Task dictionary with type and details

        Returns:
            Execution result
        """
        task_type = task.get("type", "general")

        # Get appropriate agent
        agent = self.get_agent_for_task(task_type)

        if not agent:
            return {
                "status": "failure",
                "error": "No agent available for this task",
                "task_id": task.get("id")
            }

        # Execute with selected agent
        try:
            result = await agent.execute(task)
            result["task_id"] = task.get("id")
            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "status": "failure",
                "error": str(e),
                "task_id": task.get("id"),
                "agent": agent.name
            }

    def get_all_capabilities(self) -> List[Dict[str, Any]]:
        """Get capabilities of all agents"""
        return [agent.get_capabilities() for agent in self.agents]

    def get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        return self.agent_map.get(name)

    def list_agents(self) -> List[str]:
        """List all available agent names"""
        return list(self.agent_map.keys())
