"""
Test AsyncPostgresSaver with HITL Pattern
Production 환경과 동일한 AsyncPostgresSaver를 사용한 interrupt/resume 테스트
"""

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
import logging
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestState(TypedDict):
    """테스트용 State"""
    query: str
    step_count: int
    user_input: str
    message: str
    status: str


def build_test_subgraph():
    """간단한 3-node subgraph with interrupt"""

    def work_node(state: TestState) -> TestState:
        """Step 1: Initial work"""
        logger.info("[Subgraph] work_node executing")
        state["message"] = "Work done"
        state["step_count"] = 1
        return state

    def interrupt_node(state: TestState) -> TestState:
        """Step 2: HITL interrupt point"""
        logger.info("[Subgraph] interrupt_node - triggering HITL")

        # interrupt() 함수 사용 (공식 패턴)
        user_input = interrupt({
            "type": "user_confirmation_required",
            "message": "Please confirm to continue",
            "step_count": state.get("step_count", 0)
        })

        logger.info(f"[Subgraph] User input received: {user_input}")
        state["user_input"] = user_input
        return state

    def finish_node(state: TestState) -> TestState:
        """Step 3: Final work"""
        logger.info("[Subgraph] finish_node executing")
        state["step_count"] = state.get("step_count", 0) + 1
        state["status"] = "completed"
        return state

    # Build workflow
    workflow = StateGraph(TestState)

    workflow.add_node("work", work_node)
    workflow.add_node("interrupt", interrupt_node)
    workflow.add_node("finish", finish_node)

    workflow.add_edge(START, "work")
    workflow.add_edge("work", "interrupt")
    workflow.add_edge("interrupt", "finish")
    workflow.add_edge("finish", END)

    # Compile WITHOUT checkpointer (parent will provide)
    return workflow.compile()


def build_test_supervisor(checkpointer):
    """Main supervisor with AsyncPostgresSaver"""

    def start_node(state: TestState) -> TestState:
        logger.info("[Supervisor] start_node")
        state["status"] = "started"
        return state

    def end_node(state: TestState) -> TestState:
        logger.info("[Supervisor] end_node")
        state["status"] = "finished"
        return state

    # Build main workflow
    workflow = StateGraph(TestState)

    workflow.add_node("start", start_node)

    # OFFICIAL PATTERN: Add compiled subgraph as direct node
    subgraph = build_test_subgraph()
    workflow.add_node("document_subgraph", subgraph)

    workflow.add_node("end", end_node)

    workflow.add_edge(START, "start")
    workflow.add_edge("start", "document_subgraph")
    workflow.add_edge("document_subgraph", "end")
    workflow.add_edge("end", END)

    # Compile WITH AsyncPostgresSaver
    return workflow.compile(checkpointer=checkpointer)


async def test_asyncpostgres_checkpointer():
    """
    Test AsyncPostgresSaver with HITL pattern

    Verifies:
    1. AsyncPostgresSaver initialization
    2. Checkpoint creation on interrupt
    3. Resume from checkpoint with Command API
    4. Final state verification
    """
    logger.info("=" * 80)
    logger.info("TEST: AsyncPostgresSaver with HITL Pattern")
    logger.info("=" * 80)

    # Get database URL from settings
    from app.core.config import settings

    # PostgreSQL connection string
    db_url = settings.DATABASE_URL

    # Convert SQLAlchemy URL format if needed
    if 'postgresql+psycopg://' in db_url:
        conn_string = db_url.replace('postgresql+psycopg://', 'postgresql://')
    else:
        conn_string = db_url

    logger.info(f"Database connection string configured")

    # Create AsyncPostgresSaver
    logger.info("\n1. Creating AsyncPostgresSaver...")
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        # Setup PostgreSQL tables
        await checkpointer.setup()
        logger.info("✅ AsyncPostgresSaver initialized and tables created")

        # Build supervisor with checkpointer
        app = build_test_supervisor(checkpointer)

        # Test session ID
        session_id = "test-asyncpg-001"

        # Config
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        # Initial state
        initial_state = {
            "query": "test query",
            "step_count": 0,
            "user_input": "",
            "message": "",
            "status": "init"
        }

        # ============================================================================
        # PHASE 1: Run until interrupt
        # ============================================================================
        logger.info("\n2. Running workflow until interrupt...")

        events = []
        interrupted = False

        async for event in app.astream(initial_state, config):
            logger.info(f"   Event: {list(event.keys())}")
            events.append(event)

            if "__interrupt__" in event:
                logger.info("   🛑 Interrupt detected!")
                interrupted = True

                # Verify interrupt data
                interrupt_list = event["__interrupt__"]
                logger.info(f"   Interrupt data: {interrupt_list}")

        if not interrupted:
            logger.error("❌ FAILED: No interrupt occurred!")
            return False

        logger.info("✅ Phase 1 complete: Workflow interrupted as expected")

        # ============================================================================
        # PHASE 2: Check checkpoint in database
        # ============================================================================
        logger.info("\n3. Verifying checkpoint in PostgreSQL...")

        state_snapshot = await app.aget_state(config)

        logger.info(f"   Checkpoint values: {list(state_snapshot.values.keys())}")
        logger.info(f"   Next node: {state_snapshot.next}")
        logger.info(f"   Step count: {state_snapshot.values.get('step_count')}")

        if not state_snapshot.next:
            logger.error("❌ FAILED: Checkpoint has no next node!")
            return False

        if state_snapshot.values.get('step_count') != 1:
            logger.error(f"❌ FAILED: Expected step_count=1, got {state_snapshot.values.get('step_count')}")
            return False

        logger.info("✅ Checkpoint verified in PostgreSQL")

        # ============================================================================
        # PHASE 3: Resume with Command API
        # ============================================================================
        logger.info("\n4. Resuming with Command(resume=...)...")

        resume_value = "user approved"
        events = []

        async for event in app.astream(Command(resume=resume_value), config):
            logger.info(f"   Event: {list(event.keys())}")
            events.append(event)

        # ============================================================================
        # PHASE 4: Verify final state
        # ============================================================================
        logger.info("\n5. Verifying final state...")

        final_state = await app.aget_state(config)

        logger.info(f"   Final step_count: {final_state.values.get('step_count')}")
        logger.info(f"   Final status: {final_state.values.get('status')}")
        logger.info(f"   User input: {final_state.values.get('user_input')}")
        logger.info(f"   Next node: {final_state.next}")

        # Assertions
        if final_state.values.get('step_count') != 2:
            logger.error(f"❌ FAILED: Expected step_count=2, got {final_state.values.get('step_count')}")
            return False

        if final_state.values.get('status') != 'finished':
            logger.error(f"❌ FAILED: Expected status='finished', got {final_state.values.get('status')}")
            return False

        if final_state.values.get('user_input') != resume_value:
            logger.error(f"❌ FAILED: Expected user_input='{resume_value}', got {final_state.values.get('user_input')}")
            return False

        if final_state.next:
            logger.error(f"❌ FAILED: Workflow should be complete (next={final_state.next})")
            return False

        logger.info("✅ All verifications passed!")

        # ============================================================================
        # SUMMARY
        # ============================================================================
        logger.info("\n" + "=" * 80)
        logger.info("TEST PASSED! ✅")
        logger.info("=" * 80)
        logger.info("Summary:")
        logger.info("  ✅ AsyncPostgresSaver initialized successfully")
        logger.info("  ✅ Interrupt triggered and checkpoint saved to PostgreSQL")
        logger.info("  ✅ Resume from checkpoint worked correctly")
        logger.info("  ✅ User input propagated to finish_node")
        logger.info("  ✅ Final state verification passed")
        logger.info("=" * 80)

        return True


async def main():
    """Run the test"""
    try:
        success = await test_asyncpostgres_checkpointer()
        if success:
            logger.info("\n✅ AsyncPostgresSaver + HITL Pattern: ALL TESTS PASSED")
        else:
            logger.error("\n❌ AsyncPostgresSaver + HITL Pattern: TEST FAILED")
    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {e}", exc_info=True)


if __name__ == "__main__":
    # IMPORTANT: Windows compatibility for psycopg async
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("✅ Windows EventLoop policy set (WindowsSelectorEventLoopPolicy)")

    asyncio.run(main())
