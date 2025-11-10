"""
Execute Layer Helper Classes

Helper classes and utilities for execution processing.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

import logging
import asyncio
from typing import Dict, Any, List, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class DependencyResolver:
    """
    의존성 해결기

    TODO 간 의존성을 분석하고 실행 순서를 결정합니다.
    """

    def resolve(self, tasks: List[Dict[str, Any]]) -> List[List[str]]:
        """
        의존성을 해결하고 병렬 실행 가능한 그룹을 반환합니다.

        Returns:
            List[List[str]]: 각 리스트는 병렬 실행 가능한 task ID들
        """
        # Build dependency graph
        graph = defaultdict(set)
        in_degree = defaultdict(int)
        all_tasks = set()

        for task in tasks:
            task_id = task.get("id") or task.get("step_id")
            all_tasks.add(task_id)

            for dep in task.get("dependencies", []):
                graph[dep].add(task_id)
                in_degree[task_id] += 1

        # Topological sort with level grouping
        levels = []
        current_level = [task for task in all_tasks if in_degree[task] == 0]

        while current_level:
            levels.append(current_level[:])
            next_level = []

            for task in current_level:
                for dependent in graph[task]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_level.append(dependent)

            current_level = next_level

        return levels


class AgentExecutor:
    """
    Agent 실행기

    Agent Registry와 연동하여 Agent들을 실행합니다.
    """

    def __init__(self, agent_registry=None):
        self.agent_registry = agent_registry

    async def execute(self, agent_id: str, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 Agent를 실행합니다.
        """
        try:
            # TODO: Get agent from registry and execute
            # For now, simulate execution
            logger.info(f"[AgentExecutor] Executing {agent_id} with task {task.get('action')}")

            await asyncio.sleep(0.1)  # Simulate work

            return {
                "status": "completed",
                "result": f"Agent {agent_id} completed task",
                "agent": agent_id
            }

        except Exception as e:
            logger.error(f"[AgentExecutor] Error executing {agent_id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "agent": agent_id
            }

    async def execute_parallel(self, tasks: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        여러 Agent를 병렬로 실행합니다.
        """
        coroutines = [
            self.execute(task.get("agent"), task, context)
            for task in tasks
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "failed",
                    "error": str(result),
                    "agent": tasks[i].get("agent")
                })
            else:
                processed_results.append(result)

        return processed_results


class ExecuteSupervisor:
    """
    Execute Supervisor 클래스

    실행 레이어의 메인 클래스입니다.
    """

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer
        self.resolver = DependencyResolver()
        self.executor = AgentExecutor()

    async def execute(self, todos: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        TODO 리스트를 받아 실행합니다.
        """
        # 1. Resolve dependencies
        execution_levels = self.resolver.resolve(todos)

        # 2. Execute level by level
        all_results = []
        for level in execution_levels:
            level_tasks = [t for t in todos if t.get("id") in level or t.get("step_id") in level]

            # Execute parallel within level
            level_results = await self.executor.execute_parallel(level_tasks, context or {})
            all_results.extend(level_results)

        # 3. Aggregate results
        return {
            "execution_results": all_results,
            "total_executed": len(all_results),
            "successful": sum(1 for r in all_results if r.get("status") == "completed"),
            "failed": sum(1 for r in all_results if r.get("status") == "failed")
        }