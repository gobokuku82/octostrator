"""
Test config with both thread_id and session_id
"""
import asyncio
import logging
from app.hitl_test_agent.test_supervisor import TestSupervisor
from langgraph.types import Command

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_config_with_session_id():
    """Test config with both thread_id and session_id fields"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 CONFIG WITH SESSION_ID TEST")
    logger.info("=" * 80)
    logger.info("Testing: config with both thread_id and session_id")
    logger.info("Purpose: Verify session_id doesn't break checkpoint behavior")
    logger.info("=" * 80)

    supervisor = TestSupervisor()
    supervisor.build_graph()

    session_id = "test-session-123"

    # Config with BOTH thread_id and session_id
    config = {
        "configurable": {
            "thread_id": session_id,   # checkpoint 저장용
            "session_id": session_id    # chat/application 저장용
        }
    }

    logger.info(f"\n✅ Config created:")
    logger.info(f"   thread_id: {session_id}")
    logger.info(f"   session_id: {session_id}")

    initial_state = {
        "query": "Test query",
        "status": "initialized",
        "subgraph_result": {},
        "message": "",
        "step_count": 0,
        "user_input": ""
    }

    # Phase 1: Initial execution
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: Initial Execution")
    logger.info("=" * 80)

    interrupted = False
    try:
        async for event in supervisor.app.astream(initial_state, config):
            logger.info(f"Event: {list(event.keys())}")
            if "__interrupt__" in event:
                interrupted = True
                logger.info("✅ Interrupted!")
                break
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return False

    if not interrupted:
        logger.error("❌ Failed to interrupt")
        return False

    logger.info("✅ Phase 1 SUCCESS: Workflow interrupted")

    # Check checkpoint
    logger.info("\n" + "=" * 80)
    logger.info("CHECKPOINT VERIFICATION")
    logger.info("=" * 80)

    try:
        state_snapshot = supervisor.app.get_state(config, subgraphs=True)
        logger.info(f"✅ Checkpoint retrieved successfully")
        logger.info(f"   Next: {state_snapshot.next}")
        logger.info(f"   Config used: thread_id={config['configurable']['thread_id']}, session_id={config['configurable'].get('session_id', 'N/A')}")

        if state_snapshot.tasks:
            logger.info(f"   Tasks: {len(state_snapshot.tasks)} found")
            for task in state_snapshot.tasks:
                logger.info(f"      - {task.name}")
    except Exception as e:
        logger.error(f"❌ Failed to get checkpoint: {e}")
        return False

    # Phase 2: Resume
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: Resume")
    logger.info("=" * 80)

    await asyncio.sleep(0.5)

    step_count = None
    try:
        async for event in supervisor.app.astream(
            Command(resume={"user_input": "confirmed"}),
            config  # Same config with thread_id + session_id
        ):
            logger.info(f"Resume event: {list(event.keys())}")

            if "document_subgraph" in event:
                result = event["document_subgraph"]
                step_count = result.get("step_count", 0)
                logger.info(f"✅ Subgraph completed with step_count={step_count}")

    except Exception as e:
        logger.error(f"❌ Error during resume: {e}", exc_info=True)
        return False

    # Verify
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULT")
    logger.info("=" * 80)

    if step_count == 2:
        logger.info("✅ TEST PASSED!")
        logger.info(f"   Step count: {step_count} (correct)")
        logger.info("   Config with session_id works correctly!")
        logger.info("   session_id field does NOT interfere with checkpoint")
        return True
    else:
        logger.error("❌ TEST FAILED!")
        logger.error(f"   Step count: {step_count} (expected 2)")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_config_with_session_id())
    exit(0 if result else 1)
