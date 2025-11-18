"""Document Agent - Handles document creation and writing tasks"""

from typing import Dict, Any, List
import time
from loguru import logger

from .base_agent import BaseAgent


class DocumentAgent(BaseAgent):
    """문서 작성 에이전트"""

    def __init__(self):
        super().__init__(
            name="DocumentAgent",
            description="Handles document creation, writing, and formatting"
        )
        self.tools = ["markdown_writer", "pdf_generator", "template_engine", "formatter"]

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute document creation task"""
        start_time = time.time()

        try:
            todo = task.get("todo", {})

            logger.info(f"DocumentAgent executing: {todo.get('title')}")

            system_prompt = """당신은 전문 문서 작성가입니다.

주어진 작업에 대해:
1. 문서 유형 파악 (보고서, 제안서, 문서 등)
2. 적절한 구조 설계
3. 내용 작성 (Mock)
4. 형식 지정

응답 형식 (Markdown):
# 제목

## 개요
[내용]

## 주요 내용
[상세 내용]

## 결론
[결론]
"""

            user_prompt = f"""작업: {todo.get('title')}
설명: {todo.get('description', '')}

이 주제에 대한 문서를 작성해주세요."""

            document_content = await self._call_llm(system_prompt, user_prompt)

            execution_time = time.time() - start_time

            return {
                "status": "success",
                "result": {
                    "document": document_content,
                    "format": "markdown",
                    "word_count": len(document_content.split()),
                    "sections": 3
                },
                "execution_time": execution_time,
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"DocumentAgent execution failed: {e}")
            return {
                "status": "failure",
                "error": str(e),
                "execution_time": time.time() - start_time,
                "agent": self.name
            }

    def can_handle(self, task_type: str) -> bool:
        """Check if can handle task type"""
        return task_type in ["document", "write", "report", "create_doc"]

    def get_supported_types(self) -> List[str]:
        """Get supported task types"""
        return ["document", "write", "report", "create_doc", "generate_doc"]
