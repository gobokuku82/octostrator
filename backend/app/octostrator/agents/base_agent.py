"""Base Agent Interface"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from backend.schema.todo import TodoItem


class BaseAgent(ABC):
    """기본 에이전트 인터페이스"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
        )
        self.tools: List[str] = []

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task

        Args:
            task: Task dictionary containing:
                - id: Task ID
                - type: Task type
                - todo: TodoItem dict
                - priority: Priority level

        Returns:
            Result dictionary with:
                - status: "success" | "failure"
                - result: Result data
                - execution_time: Time taken
                - error: Error message if failed
        """
        pass

    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle the given task type"""
        pass

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM with prompts"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return {
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
            "supported_types": self.get_supported_types()
        }

    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get list of supported task types"""
        pass
