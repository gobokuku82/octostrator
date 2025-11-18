"""Test Mock Agents"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.octostrator.agents import (
    AgentManager,
    SearchAgent,
    AnalysisAgent,
    DocumentAgent,
    CodeAgent
)
from loguru import logger


async def test_individual_agents():
    """Test each agent individually"""

    print("=" * 60)
    print("Testing Individual Agents")
    print("=" * 60)

    agents = [
        SearchAgent(),
        AnalysisAgent(),
        DocumentAgent(),
        CodeAgent()
    ]

    test_tasks = [
        {
            "id": "task_1",
            "type": "search",
            "todo": {
                "title": "웹에서 AI 관련 최신 뉴스 검색",
                "description": "최근 1주일간의 AI 관련 주요 뉴스를 수집하세요"
            },
            "priority": "high"
        },
        {
            "id": "task_2",
            "type": "analysis",
            "todo": {
                "title": "사용자 데이터 분석",
                "description": "사용자 행동 패턴을 분석하여 인사이트를 도출하세요"
            },
            "priority": "medium"
        },
        {
            "id": "task_3",
            "type": "document",
            "todo": {
                "title": "프로젝트 보고서 작성",
                "description": "Q1 프로젝트 진행 상황 보고서를 작성하세요"
            },
            "priority": "high"
        },
        {
            "id": "task_4",
            "type": "code",
            "todo": {
                "title": "데이터 처리 스크립트 작성",
                "description": "CSV 파일을 읽어 JSON으로 변환하는 스크립트를 작성하세요"
            },
            "priority": "low"
        }
    ]

    for i, (agent, task) in enumerate(zip(agents, test_tasks), 1):
        print(f"\n--- Test {i}: {agent.name} ---")
        print(f"Task: {task['todo']['title']}")

        result = await agent.execute(task)

        print(f"Status: {result['status']}")
        print(f"Execution Time: {result['execution_time']:.3f}s")

        if result['status'] == 'success':
            print(f"Result Preview: {str(result['result'])[:200]}...")
        else:
            print(f"Error: {result.get('error')}")

        print("-" * 60)


async def test_agent_manager():
    """Test AgentManager routing"""

    print("\n" + "=" * 60)
    print("Testing AgentManager")
    print("=" * 60)

    manager = AgentManager()

    print(f"\nAvailable Agents: {manager.list_agents()}")

    # Test routing
    test_cases = [
        ("search", "Should route to SearchAgent"),
        ("analysis", "Should route to AnalysisAgent"),
        ("document", "Should route to DocumentAgent"),
        ("code", "Should route to CodeAgent"),
        ("unknown", "Should use fallback agent")
    ]

    print("\n--- Testing Agent Routing ---")
    for task_type, expected in test_cases:
        agent = manager.get_agent_for_task(task_type)
        print(f"Task type '{task_type}': {agent.name if agent else 'None'} - {expected}")

    # Test full execution through manager
    print("\n--- Testing Full Execution ---")

    task = {
        "id": "manager_test_1",
        "type": "analysis",
        "todo": {
            "title": "매출 데이터 분석",
            "description": "최근 3개월 매출 트렌드를 분석하고 예측하세요"
        },
        "priority": "high"
    }

    print(f"\nExecuting task: {task['todo']['title']}")
    result = await manager.execute_task(task)

    print(f"Status: {result['status']}")
    print(f"Agent Used: {result.get('agent')}")
    print(f"Task ID: {result.get('task_id')}")
    print(f"Execution Time: {result.get('execution_time', 0):.3f}s")

    if result['status'] == 'success':
        print(f"\nResult Summary:")
        for key, value in result.get('result', {}).items():
            if isinstance(value, str):
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")


async def test_capabilities():
    """Test agent capabilities reporting"""

    print("\n" + "=" * 60)
    print("Testing Agent Capabilities")
    print("=" * 60)

    manager = AgentManager()
    capabilities = manager.get_all_capabilities()

    for cap in capabilities:
        print(f"\n{cap['name']}:")
        print(f"  Description: {cap['description']}")
        print(f"  Tools: {', '.join(cap['tools'])}")
        print(f"  Supported Types: {', '.join(cap['supported_types'])}")


if __name__ == "__main__":
    print("🤖 Testing Octostrator Mock Agents\n")

    asyncio.run(test_individual_agents())
    asyncio.run(test_agent_manager())
    asyncio.run(test_capabilities())

    print("\n✅ All agent tests completed")
