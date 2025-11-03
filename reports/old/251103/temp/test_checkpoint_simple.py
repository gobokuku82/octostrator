"""
간단한 Checkpoint 저장 테스트
LangGraph AsyncSqliteSaver가 실제로 데이터를 저장하는지 확인
"""

import asyncio
import sys
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Backend path 추가
backend_dir = Path(__file__).parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class SimpleState(TypedDict):
    """간단한 상태 정의"""
    message: str
    counter: int


async def node1(state: SimpleState) -> SimpleState:
    """첫 번째 노드"""
    print(f"[Node1] Current state: {state}")
    state["message"] = "After node1"
    state["counter"] = state.get("counter", 0) + 1
    return state


async def node2(state: SimpleState) -> SimpleState:
    """두 번째 노드"""
    print(f"[Node2] Current state: {state}")
    state["message"] = "After node2"
    state["counter"] = state.get("counter", 0) + 10
    return state


async def test_checkpoint_save():
    """Checkpoint 저장 테스트"""
    print("=" * 60)
    print("Simple Checkpoint Save Test")
    print("=" * 60)

    # 1. Checkpointer 생성
    db_path = "C:/kdy/Projects/holmesnyangz/beta_v001/backend/data/system/checkpoints/simple_test.db"
    print(f"\n1. Creating checkpointer: {db_path}")

    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        print("   [OK] Checkpointer created")

        # 2. Graph 구성
        print("\n2. Building graph...")
        workflow = StateGraph(SimpleState)
        workflow.add_node("node1", node1)
        workflow.add_node("node2", node2)
        workflow.add_edge(START, "node1")
        workflow.add_edge("node1", "node2")
        workflow.add_edge("node2", END)

        # Checkpointer와 함께 컴파일
        app = workflow.compile(checkpointer=checkpointer)
        print("   [OK] Graph compiled with checkpointer")

        # 3. 초기 상태로 실행
        print("\n3. Running workflow...")
        initial_state = SimpleState(message="Start", counter=0)
        config = {"configurable": {"thread_id": "test-session-123"}}

        final_state = await app.ainvoke(initial_state, config=config)
        print(f"   [OK] Workflow completed: {final_state}")

        # 4. Checkpoint 데이터 확인
        print("\n4. Checking checkpoint data...")
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Checkpoints 테이블 확인
        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        checkpoint_count = cursor.fetchone()[0]
        print(f"   Checkpoints count: {checkpoint_count}")

        if checkpoint_count > 0:
            cursor.execute("SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(f"     - thread_id={row[0]}, ns={row[1]}, id={row[2]}")

        # Writes 테이블 확인
        cursor.execute("SELECT COUNT(*) FROM writes")
        writes_count = cursor.fetchone()[0]
        print(f"   Writes count: {writes_count}")

        conn.close()

        # 5. 같은 thread로 이어서 실행 (재개 테스트)
        print("\n5. Resuming from checkpoint...")
        resume_state = SimpleState(message="Resume", counter=100)
        final_state2 = await app.ainvoke(resume_state, config=config)
        print(f"   [OK] Resumed workflow completed: {final_state2}")

        # 6. 최종 checkpoint 확인
        print("\n6. Final checkpoint count...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        final_checkpoint_count = cursor.fetchone()[0]
        print(f"   Final checkpoints count: {final_checkpoint_count}")
        cursor.execute("SELECT COUNT(*) FROM writes")
        final_writes_count = cursor.fetchone()[0]
        print(f"   Final writes count: {final_writes_count}")
        conn.close()

        print("\n" + "=" * 60)
        if final_checkpoint_count > 0:
            print("[SUCCESS] Checkpoints are being saved!")
        else:
            print("[FAILURE] No checkpoints saved")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_checkpoint_save())
