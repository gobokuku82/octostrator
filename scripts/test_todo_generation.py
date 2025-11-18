"""Test TODO auto-generation functionality"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.octostrator.graphs.todo_graph import TodoGraph
from loguru import logger


async def test_todo_generation():
    """Test TODO generation with various queries"""

    todo_graph = TodoGraph()
    todo_graph.build_graph()

    test_cases = [
        {
            "query": "데이터 분석 프로젝트를 시작하려고 합니다. 먼저 데이터를 수집하고, 정제한 다음, 분석하고 보고서를 작성해야 합니다.",
            "description": "Simple sequential tasks"
        },
        {
            "query": "웹 애플리케이션을 만들어주세요. 프론트엔드는 React, 백엔드는 FastAPI를 사용하고, 데이터베이스는 PostgreSQL로 해주세요.",
            "description": "Multi-component project"
        },
        {
            "query": "머신러닝 모델을 학습시켜주세요",
            "description": "Complex task requiring breakdown"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test Case {i}: {test_case['description']}")
        print(f"Query: {test_case['query']}")
        print(f"{'=' * 60}\n")

        try:
            result = await todo_graph.invoke(
                user_query=test_case["query"],
                thread_id=f"test_thread_{i}",
                session_id=f"test_session_{i}"
            )

            todos = result.get("todos", [])
            validation_passed = result.get("validation_passed", False)
            validation_errors = result.get("validation_errors", [])

            print(f"✓ Validation: {'PASSED' if validation_passed else 'FAILED'}")
            if validation_errors:
                print(f"  Errors: {validation_errors}")

            print(f"\n📝 Generated {len(todos)} TODOs:\n")

            for j, todo in enumerate(todos, 1):
                print(f"{j}. {todo.title}")
                print(f"   Description: {todo.description}")
                print(f"   Priority: {todo.priority}")
                print(f"   Est. Time: {todo.estimated_time_minutes} min")
                if todo.dependencies:
                    dep_titles = [
                        next((t.title for t in todos if t.id == dep_id), str(dep_id))
                        for dep_id in todo.dependencies
                    ]
                    print(f"   Dependencies: {', '.join(dep_titles)}")
                print()

        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception("Test failed")

        print("\n" + "-" * 60)


if __name__ == "__main__":
    print("🚀 Testing TODO Auto-Generation\n")
    asyncio.run(test_todo_generation())
    print("\n✅ Tests completed")
