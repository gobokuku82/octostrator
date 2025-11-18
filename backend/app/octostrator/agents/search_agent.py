"""Search Agent - Handles search and information retrieval tasks"""

from typing import Dict, Any, List
import time
from loguru import logger

from .base_agent import BaseAgent


class SearchAgent(BaseAgent):
    """검색 및 정보 수집 에이전트"""

    def __init__(self):
        super().__init__(
            name="SearchAgent",
            description="Handles web search, database queries, and information retrieval"
        )
        self.tools = ["web_search", "database_query", "api_call", "file_search"]

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search task"""
        start_time = time.time()

        try:
            todo = task.get("todo", {})
            task_type = task.get("type", "general")

            logger.info(f"SearchAgent executing: {todo.get('title')}")

            # System prompt for search tasks
            system_prompt = """당신은 정보 검색 전문가입니다.

주어진 작업에 대해:
1. 어떤 정보가 필요한지 파악
2. 검색 전략 수립
3. 가상의 검색 결과 생성 (Mock)

응답 형식:
- 검색 쿼리: [쿼리]
- 검색 결과: [요약]
- 관련 링크: [링크들]
- 신뢰도: [0-100]
"""

            user_prompt = f"""작업: {todo.get('title')}
설명: {todo.get('description', '')}

이 작업을 위한 검색을 수행하고 결과를 제공해주세요."""

            # Call LLM for mock search
            search_result = await self._call_llm(system_prompt, user_prompt)

            execution_time = time.time() - start_time

            return {
                "status": "success",
                "result": {
                    "search_output": search_result,
                    "queries_executed": ["mock_query_1", "mock_query_2"],
                    "sources_found": 5
                },
                "execution_time": execution_time,
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"SearchAgent execution failed: {e}")
            return {
                "status": "failure",
                "error": str(e),
                "execution_time": time.time() - start_time,
                "agent": self.name
            }

    def can_handle(self, task_type: str) -> bool:
        """Check if can handle task type"""
        return task_type in ["search", "query", "lookup", "find"]

    def get_supported_types(self) -> List[str]:
        """Get supported task types"""
        return ["search", "query", "lookup", "find", "retrieve"]
