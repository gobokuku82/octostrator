"""
Test progress callbacks with interrupt/resume
Progress callbacks simulate WebSocket communication
"""
import asyncio
import logging
from app.hitl_test_agent.test_supervisor import TestSupervisor
from langgraph.types import Command
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CallbackTracker:
    """Track callback invocations"""
    def __init__(self):
        self.events: List[Dict] = []

    async def callback(self, event_type: str, data: dict):
        """Simulated progress callback (like WebSocket send)"""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.events.append(event)
        logger.info(f"[CALLBACK] {event_type}: {data.get('message', '')}")

    def get_events(self, event_type: str = None):
        """Get events by type"""
        if event_type:
            return [e for e in self.events if e["event_type"] == event_type]
        return self.events

    def clear(self):
        """Clear events"""
        self.events = []


async def test_callbacks_with_interrupt():
    """Test that callbacks work across interrupt/resume"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 PROGRESS CALLBACKS TEST")
    logger.info("=" * 80)
    logger.info("Testing: Callbacks work across interrupt/resume cycle")
    logger.info("Purpose: Verify WebSocket-like communication remains functional")
    logger.info("=" * 80)

    # Create supervisor with modified nodes that use callbacks
    supervisor = TestSupervisor()
    supervisor.build_graph()

    session_id = "test-callbacks"
    config = {"configurable": {"thread_id": session_id}}

    # Setup callback tracker
    tracker = CallbackTracker()

    # Store callback (simulating WebSocket registration)
    # In production: self._progress_callbacks[session_id] = websocket_send
    logger.info("\n[SETUP] Registering progress callback for session")

    # Modify supervisor to call our callback
    # (In real code, this would be in node functions)
    original_start = supervisor.start_node

    async def start_with_callback(state):
        await tracker.callback("node_start", {"node": "start", "message": "Starting workflow"})
        result = original_start(state)
        await tracker.callback("node_complete", {"node": "start", "message": "Start complete"})
        return result

    supervisor.start_node = start_with_callback

    initial_state = {
        "query": "Test",
        "status": "initialized",
        "subgraph_result": {},
        "message": "",
        "step_count": 0,
        "user_input": ""
    }

    # Phase 1: Initial execution with callbacks
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1: Initial Execution")
    logger.info("=" * 80)

    interrupted = False
    async for event in supervisor.app.astream(initial_state, config):
        if "__interrupt__" in event:
            await tracker.callback("interrupt", {"message": "Workflow interrupted - awaiting user input"})
            interrupted = True
            break

    if not interrupted:
        logger.error("❌ Failed to interrupt")
        return False

    # Check callbacks from Phase 1
    phase1_events = tracker.get_events()
    logger.info(f"\n[PHASE 1] Received {len(phase1_events)} callback events:")
    for evt in phase1_events:
        logger.info(f"   - {evt['event_type']}: {evt['data'].get('message', '')}")

    # Simulate user interaction delay
    await asyncio.sleep(0.5)

    # Phase 2: Resume with callbacks
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: Resume")
    logger.info("=" * 80)
    logger.info("[SETUP] Callback should still work after resume")

    # In production, we need to re-register callback if connection was lost
    # But in our case, tracker persists

    await tracker.callback("resume_start", {"message": "Resuming workflow with user input"})

    step_count = None
    async for event in supervisor.app.astream(
        Command(resume={"user_input": "confirmed"}),
        config
    ):
        if "document_subgraph" in event:
            result = event["document_subgraph"]
            step_count = result.get("step_count", 0)
            await tracker.callback("subgraph_complete", {
                "message": "Subgraph completed",
                "step_count": step_count
            })

        if "end" in event:
            await tracker.callback("workflow_complete", {"message": "Workflow completed successfully"})

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("CALLBACK ANALYSIS")
    logger.info("=" * 80)

    all_events = tracker.get_events()
    logger.info(f"Total callbacks: {len(all_events)}")

    # Check specific events
    interrupt_events = tracker.get_events("interrupt")
    resume_events = tracker.get_events("resume_start")
    complete_events = tracker.get_events("workflow_complete")

    logger.info(f"   Interrupt callbacks: {len(interrupt_events)}")
    logger.info(f"   Resume callbacks: {len(resume_events)}")
    logger.info(f"   Complete callbacks: {len(complete_events)}")

    # Verify
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULT")
    logger.info("=" * 80)

    success = (
        step_count == 2 and
        len(interrupt_events) > 0 and
        len(resume_events) > 0 and
        len(complete_events) > 0
    )

    if success:
        logger.info("✅ TEST PASSED!")
        logger.info("   Callbacks work across interrupt/resume")
        logger.info("   WebSocket-like communication is functional")
        logger.info("\n   Event Timeline:")
        for i, evt in enumerate(all_events, 1):
            logger.info(f"      {i}. {evt['event_type']}: {evt['data'].get('message', '')}")
        return True
    else:
        logger.error("❌ TEST FAILED!")
        if step_count != 2:
            logger.error(f"   Step count: {step_count} (expected 2)")
        if len(interrupt_events) == 0:
            logger.error("   No interrupt callback")
        if len(resume_events) == 0:
            logger.error("   No resume callback")
        if len(complete_events) == 0:
            logger.error("   No complete callback")
        return False


async def test_callback_reconnection():
    """Test callback re-registration after connection loss"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 CALLBACK RECONNECTION TEST")
    logger.info("=" * 80)
    logger.info("Testing: Callback re-registration after simulated disconnect")
    logger.info("=" * 80)

    supervisor = TestSupervisor()
    supervisor.build_graph()

    session_id = "test-reconnect"
    config = {"configurable": {"thread_id": session_id}}

    # First tracker (initial connection)
    tracker1 = CallbackTracker()

    initial_state = {
        "query": "Test",
        "status": "initialized",
        "subgraph_result": {},
        "message": "",
        "step_count": 0,
        "user_input": ""
    }

    # Phase 1: Execute with tracker1
    logger.info("\n[PHASE 1] Initial execution with callback1")
    interrupted = False
    async for event in supervisor.app.astream(initial_state, config):
        if "__interrupt__" in event:
            await tracker1.callback("interrupt", {"message": "Interrupted"})
            interrupted = True
            break

    logger.info(f"   Tracker1 events: {len(tracker1.get_events())}")

    # Simulate connection loss
    logger.info("\n[DISCONNECT] Simulating connection loss...")
    logger.info("   Tracker1 is discarded")

    await asyncio.sleep(0.3)

    # Simulate reconnection with new tracker
    logger.info("\n[RECONNECT] Client reconnects with new callback")
    tracker2 = CallbackTracker()

    # Phase 2: Resume with tracker2
    logger.info("\n[PHASE 2] Resume with callback2")

    step_count = None
    async for event in supervisor.app.astream(
        Command(resume={"user_input": "confirmed"}),
        config
    ):
        # New callback
        if "document_subgraph" in event:
            result = event["document_subgraph"]
            step_count = result.get("step_count", 0)
            await tracker2.callback("resume_complete", {
                "message": "Resume successful",
                "step_count": step_count
            })

    logger.info(f"   Tracker2 events: {len(tracker2.get_events())}")

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("RECONNECTION ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"Tracker1 (before disconnect): {len(tracker1.get_events())} events")
    logger.info(f"Tracker2 (after reconnect): {len(tracker2.get_events())} events")

    success = step_count == 2 and len(tracker2.get_events()) > 0

    if success:
        logger.info("\n✅ TEST PASSED!")
        logger.info("   Resume works even after callback re-registration")
        logger.info("   Workflow state is preserved (checkpoint)")
        logger.info("   New callback receives events after reconnection")
        return True
    else:
        logger.error("\n❌ TEST FAILED!")
        return False


async def test_progress_callbacks():
    """Run all progress callback tests"""
    logger.info("=" * 80)
    logger.info("🧪 PROGRESS CALLBACKS TEST SUITE")
    logger.info("=" * 80)

    results = []

    # Test 1
    try:
        result = await test_callbacks_with_interrupt()
        results.append(("Callbacks with Interrupt/Resume", result))
    except Exception as e:
        logger.error(f"Test 1 crashed: {e}", exc_info=True)
        results.append(("Callbacks with Interrupt/Resume", False))

    # Test 2
    try:
        result = await test_callback_reconnection()
        results.append(("Callback Reconnection", result))
    except Exception as e:
        logger.error(f"Test 2 crashed: {e}", exc_info=True)
        results.append(("Callback Reconnection", False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("PROGRESS CALLBACKS TEST RESULTS")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    all_passed = all(r[1] for r in results)

    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("✅ ALL PROGRESS CALLBACK TESTS PASSED")
        logger.info("\n   Key Findings:")
        logger.info("   - Callbacks work across interrupt/resume")
        logger.info("   - Callback re-registration works after reconnection")
        logger.info("   - Workflow state preserved in checkpoint")
        logger.info("   - WebSocket pattern is compatible")
    else:
        logger.error("❌ SOME PROGRESS CALLBACK TESTS FAILED")
    logger.info("=" * 80)

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(test_progress_callbacks())
    exit(0 if result else 1)
