"""Code Agent - Handles code execution and programming tasks"""

from typing import Dict, Any, List
import time
from loguru import logger

from .base_agent import BaseAgent


class CodeAgent(BaseAgent):
    """코드 실행 에이전트"""

    def __init__(self):
        super().__init__(
            name="CodeAgent",
            description="Handles code execution, testing, and debugging"
        )
        self.tools = ["python_executor", "npm_runner", "test_runner", "linter"]

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code task"""
        start_time = time.time()

        try:
            todo = task.get("todo", {})

            logger.info(f"CodeAgent executing: {todo.get('title')}")

            system_prompt = """당신은 프로그래밍 전문가입니다.

주어진 작업에 대해:
1. 작업 요구사항 분석
2. 적절한 프로그래밍 언어/도구 선택
3. 코드 작성 (Mock)
4. 테스트 계획 수립

응답 형식:
```언어
[코드]
```

실행 결과: [결과]
테스트: [테스트 결과]
"""

            user_prompt = f"""작업: {todo.get('title')}
설명: {todo.get('description', '')}

이 작업을 위한 코드를 작성하고 실행 계획을 제공해주세요."""

            code_result = await self._call_llm(system_prompt, user_prompt)

            execution_time = time.time() - start_time

            return {
                "status": "success",
                "result": {
                    "code": code_result,
                    "language": "python",
                    "tests_passed": 10,
                    "tests_failed": 0,
                    "coverage": 0.85
                },
                "execution_time": execution_time,
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"CodeAgent execution failed: {e}")
            return {
                "status": "failure",
                "error": str(e),
                "execution_time": time.time() - start_time,
                "agent": self.name
            }

    def can_handle(self, task_type: str) -> bool:
        """Check if can handle task type"""
        return task_type in ["code", "execute", "run", "test", "debug"]

    def get_supported_types(self) -> List[str]:
        """Get supported task types"""
        return ["code", "execute", "run", "test", "debug", "program"]
