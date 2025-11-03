"""
HITL Test Runner
Execute LangGraph 0.6 Subgraph + HITL pattern tests

Run this to verify if direct subgraph resume works!
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hitl_test_agent.test_supervisor import TestSupervisor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_direct_subgraph_resume():
    """
    Test Scenario 4: Direct Subgraph Resume

    This tests if we can resume a subgraph by:
    1. Storing reference to compiled subgraph_app
    2. Calling subgraph_app.astream(None, config) after interrupt

    Expected Results:
    ✅ SUCCESS: finish_node executes with step_count = 2
                (work=1, interrupt pauses, finish=1)
    ❌ FAILURE: finish_node executes with step_count > 2
                (indicates work_node executed again = restart)
                This would confirm LangGraph Issue #4796
    """
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TEST SCENARIO 4: Direct Subgraph Resume")
    logger.info("=" * 80)
    logger.info("Purpose: Verify if subgraph.astream(None) resumes from interrupt point")
    logger.info("Reference: LangGraph Issue #4796")
    logger.info("=" * 80)

    # Create supervisor
    logger.info("\n[TEST] Creating TestSupervisor...")
    supervisor = TestSupervisor()
    app = supervisor.build_graph()

    # Config
    session_id = "test-session-123"
    config = {"configurable": {"thread_id": session_id}}

    # ====================
    # PHASE 1: Initial Execution
    # ====================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: Initial Execution")
    logger.info("=" * 80)
    logger.info("[TEST] Executing main graph...")
    logger.info("   Expected: Subgraph will interrupt at interrupt_node")

    initial_state = {
        "query": "Create document",
        "status": "initialized",
        "subgraph_result": {},
        "message": "",
        "step_count": 0,
        "user_input": ""
    }

    result = None
    interrupted = False
    async for event in app.astream(initial_state, config):
        logger.info(f"[TEST] Main graph event: {list(event.keys())}")
        result = event
        # Check for interrupt
        if "__interrupt__" in event:
            interrupted = True
            logger.info(f"   ✅ Interrupt detected!")

    logger.info(f"\n[TEST] Phase 1 complete")
    logger.info(f"   Interrupted: {interrupted}")

    if not interrupted:
        logger.error("\n❌ TEST FAILED: Expected interrupt")
        logger.error("   The workflow should have paused at interrupt_node")
        return False

    logger.info("\n✅ Phase 1 SUCCESS: Workflow interrupted as expected")

    # ====================
    # PHASE 2: User Confirmation (Simulated)
    # ====================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: User Confirmation")
    logger.info("=" * 80)
    logger.info("[TEST] Simulating user clicking 'Confirm' button...")
    logger.info("   (In real system, this would come from WebSocket message)")

    # Wait a moment to make logs clearer
    await asyncio.sleep(1)

    # ====================
    # PHASE 3: Resume Workflow
    # ====================
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: Resume Workflow")
    logger.info("=" * 80)
    logger.info("[TEST] Calling supervisor.resume_workflow()...")
    logger.info("   This will execute: subgraph_app.astream(None, config)")
    logger.info("   CRITICAL: Check if workflow continues from interrupt_node")

    resume_result = await supervisor.resume_workflow(session_id)

    logger.info(f"\n[TEST] Resume completed")
    logger.info(f"   Result: {resume_result}")

    # ====================
    # RESULT ANALYSIS
    # ====================
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULT ANALYSIS")
    logger.info("=" * 80)

    status = resume_result.get("status")
    step_count = resume_result.get("step_count")

    if status == "success" and step_count == 2:
        logger.info("✅ TEST PASSED!")
        logger.info("=" * 80)
        logger.info("CONCLUSION: Direct Subgraph Resume WORKS")
        logger.info("=" * 80)
        logger.info("Details:")
        logger.info("  - Subgraph resumed from interrupt_node")
        logger.info("  - finish_node executed with step_count = 2")
        logger.info("  - work_node did NOT re-execute")
        logger.info("\nNext Steps:")
        logger.info("  1. Apply this pattern to production code")
        logger.info("  2. In TeamBasedSupervisor:")
        logger.info("     - Add self._subgraph_apps = {}")
        logger.info("     - Store document_app in _execute_single_team()")
        logger.info("     - Resume via document_app.astream(None) in resume_document_workflow()")
        logger.info("  3. Test integration")
        logger.info("  4. Done! 🎉")
        return True

    elif status == "failed":
        logger.error("❌ TEST FAILED!")
        logger.error("=" * 80)
        logger.error("CONCLUSION: Direct Subgraph Resume DOES NOT WORK")
        logger.error("=" * 80)
        logger.error("Details:")
        if step_count:
            logger.error(f"  - finish_node step_count = {step_count} (expected 2)")
            logger.error("  - Subgraph RESTARTED from beginning")
            logger.error("  - work_node executed again")
        else:
            logger.error("  - finish_node never executed")
            logger.error("  - Subgraph might not have resumed at all")
        logger.error("\nThis confirms: LangGraph Issue #4796")
        logger.error("GitHub: https://github.com/langchain-ai/langgraph/issues/4796")
        logger.error("\nNext Steps:")
        logger.error("  Option A: Try Test 2 (interrupt() function)")
        logger.error("  Option B: Try Test 3 (Command API)")
        logger.error("  Option C: Implement workaround")
        logger.error("  Option D: Flatten architecture (remove subgraphs)")
        return False

    else:
        logger.error("❌ TEST ERROR!")
        logger.error(f"   Unexpected result: {resume_result}")
        return False


async def main():
    """Main test execution"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 LangGraph 0.6 HITL Test Suite")
    logger.info("=" * 80)
    logger.info("Testing: Subgraph + NodeInterrupt + Resume Pattern")
    logger.info("=" * 80)

    # Run Test Scenario 4
    success = await test_direct_subgraph_resume()

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUITE COMPLETE")
    logger.info("=" * 80)

    if success:
        logger.info("Result: ✅ PASSED")
        logger.info("\nPattern verified: Direct subgraph resume works!")
        logger.info("Safe to apply to production code.")
    else:
        logger.info("Result: ❌ FAILED")
        logger.info("\nPattern does NOT work in current LangGraph version.")
        logger.info("Need to try alternative approaches or workarounds.")

    logger.info("\n" + "=" * 80)

    return success


if __name__ == "__main__":
    # Run tests
    result = asyncio.run(main())

    # Exit code
    sys.exit(0 if result else 1)
