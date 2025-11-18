"""Test TODO natural language editing"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.octostrator.graphs.todo_graph import TodoGraph
from backend.app.octostrator.graphs.todo_editor import TodoEditor
from loguru import logger


async def test_todo_editing():
    """Test TODO editing with natural language commands"""

    # 1. 먼저 TODO 생성
    print("=" * 60)
    print("Step 1: TODO 생성")
    print("=" * 60)

    todo_graph = TodoGraph()
    todo_graph.build_graph()

    result = await todo_graph.invoke(
        user_query="데이터 분석 프로젝트: 데이터 수집, 정제, 분석, 보고서 작성",
        thread_id="test_edit",
        session_id="test_edit"
    )

    todos = result.get("todos", [])
    print(f"\n생성된 TODO {len(todos)}개:\n")
    for i, todo in enumerate(todos):
        print(f"{i}. [{todo.priority.value}] {todo.title} ({todo.estimated_time_minutes}분)")

    # 2. TODO 편집 테스트
    print("\n" + "=" * 60)
    print("Step 2: TODO 편집 테스트")
    print("=" * 60)

    editor = TodoEditor()

    test_commands = [
        "첫 번째 TODO의 우선순위를 높여줘",
        "데이터 분석 작업의 예상 시간을 3시간으로 변경해줘",
        "보고서 작성의 상태를 진행중으로 바꿔줘",
        "데이터 정제 작업을 삭제해줘"
    ]

    for i, command in enumerate(test_commands, 1):
        print(f"\n--- 편집 명령 {i}: {command} ---")

        edit_result = await editor.edit_todos(todos, command)

        if edit_result["success"]:
            print(f"✓ 편집 성공: {edit_result['action']}")
            print(f"  변경된 TODO: {edit_result['changes_count']}개")
            if edit_result.get('reason'):
                print(f"  사유: {edit_result['reason']}")

            # 업데이트된 TODO로 교체
            todos = edit_result["todos"]

            print(f"\n현재 TODO {len(todos)}개:")
            for j, todo in enumerate(todos):
                print(f"  {j}. [{todo.priority.value}] {todo.title} "
                      f"({todo.estimated_time_minutes}분, {todo.status.value})")
        else:
            print(f"✗ 편집 실패: {edit_result.get('error')}")

        print("-" * 60)

    # 3. 최종 결과
    print("\n" + "=" * 60)
    print("최종 TODO 리스트")
    print("=" * 60)
    for i, todo in enumerate(todos):
        print(f"\n{i}. {todo.title}")
        print(f"   우선순위: {todo.priority.value}")
        print(f"   예상 시간: {todo.estimated_time_minutes}분")
        print(f"   상태: {todo.status.value}")
        print(f"   설명: {todo.description}")


if __name__ == "__main__":
    print("🚀 Testing TODO Natural Language Editing\n")
    asyncio.run(test_todo_editing())
    print("\n✅ Tests completed")
