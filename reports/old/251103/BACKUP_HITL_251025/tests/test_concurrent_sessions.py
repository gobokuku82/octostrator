"""
Test concurrent sessions using same subgraph instance
"""
import asyncio
import logging
from app.hitl_test_agent.test_supervisor import TestSupervisor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_session(supervisor, session_id: str, delay: float = 0):
    """Run a single session workflow"""
    logger.info(f"=" * 80)
    logger.info(f"[{session_id}] Starting session")
    logger.info(f"=" * 80)

    config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "query": f"Query from {session_id}",
        "status": "initialized",
        "subgraph_result": {},
        "message": "",
        "step_count": 0,
        "user_input": ""
    }

    # Add artificial delay for session 2
    if delay > 0:
        await asyncio.sleep(delay)

    # Phase 1: Initial execution (should interrupt)
    logger.info(f"[{session_id}] Phase 1: Initial execution")
    interrupted = False

    try:
        async for event in supervisor.app.astream(initial_state, config):
            logger.info(f"[{session_id}] Event: {list(event.keys())}")
            if "__interrupt__" in event:
                interrupted = True
                logger.info(f"[{session_id}] ✅ Interrupted!")
                break
    except Exception as e:
        logger.error(f"[{session_id}] ❌ Error during initial execution: {e}")
        return {"session_id": session_id, "status": "error", "error": str(e)}

    if not interrupted:
        logger.error(f"[{session_id}] ❌ Failed to interrupt")
        return {"session_id": session_id, "status": "failed"}

    # Simulate user delay
    await asyncio.sleep(0.5)

    # Phase 2: Resume
    logger.info(f"[{session_id}] Phase 2: Resume")
    from langgraph.types import Command

    step_count = None
    try:
        async for event in supervisor.app.astream(
            Command(resume={"user_input": f"confirmed-{session_id}"}),
            config
        ):
            logger.info(f"[{session_id}] Resume event: {list(event.keys())}")

            if "document_subgraph" in event:
                result = event["document_subgraph"]
                step_count = result.get("step_count", 0)
                logger.info(f"[{session_id}] Completed with step_count={step_count}")

    except Exception as e:
        logger.error(f"[{session_id}] ❌ Error during resume: {e}")
        return {"session_id": session_id, "status": "error", "error": str(e)}

    # Verify
    if step_count == 2:
        logger.info(f"[{session_id}] ✅ SUCCESS")
        return {"session_id": session_id, "status": "success", "step_count": step_count}
    else:
        logger.error(f"[{session_id}] ❌ FAILED - step_count={step_count}")
        return {"session_id": session_id, "status": "failed", "step_count": step_count}


async def test_concurrent_sessions():
    """Test 2 concurrent sessions using same subgraph instance"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 CONCURRENT SESSIONS TEST")
    logger.info("=" * 80)
    logger.info("Testing: Same compiled subgraph instance with multiple sessions")
    logger.info("Expected: Both sessions should work independently")
    logger.info("=" * 80)

    # Create ONE supervisor (shared subgraph instance)
    supervisor = TestSupervisor()
    supervisor.build_graph()

    logger.info("\n✅ Supervisor created with shared subgraph instance")
    logger.info("   Now running 2 sessions concurrently...\n")

    # Run 2 sessions concurrently
    session1_task = asyncio.create_task(run_session(supervisor, "session-1"))
    session2_task = asyncio.create_task(run_session(supervisor, "session-2", delay=0.2))

    # Wait for both
    results = await asyncio.gather(session1_task, session2_task)

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)

    for result in results:
        session_id = result["session_id"]
        status = result["status"]
        step_count = result.get("step_count", "N/A")

        if status == "success":
            logger.info(f"✅ {session_id}: SUCCESS (step_count={step_count})")
        else:
            logger.error(f"❌ {session_id}: {status.upper()} (step_count={step_count})")

    # Overall result
    all_success = all(r["status"] == "success" for r in results)

    logger.info("\n" + "=" * 80)
    if all_success:
        logger.info("✅ CONCURRENT SESSIONS TEST PASSED!")
        logger.info("   Both sessions completed successfully")
        logger.info("   Shared subgraph instance is SAFE for concurrent use")
    else:
        logger.error("❌ CONCURRENT SESSIONS TEST FAILED!")
        logger.error("   One or more sessions failed")
        logger.error("   Shared subgraph instance may NOT be safe")
    logger.info("=" * 80)

    return all_success


if __name__ == "__main__":
    result = asyncio.run(test_concurrent_sessions())
    exit(0 if result else 1)
