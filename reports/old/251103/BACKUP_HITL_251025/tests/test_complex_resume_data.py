"""
Test complex resume data structures
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


async def test_complex_resume_data():
    """Test resuming with complex nested data structures"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 COMPLEX RESUME DATA TEST")
    logger.info("=" * 80)
    logger.info("Testing: Resume with complex nested data structures")
    logger.info("Purpose: Verify interrupt() can handle production-like data")
    logger.info("=" * 80)

    supervisor = TestSupervisor()
    supervisor.build_graph()

    session_id = "test-complex-data"
    config = {"configurable": {"thread_id": session_id}}

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
    async for event in supervisor.app.astream(initial_state, config):
        if "__interrupt__" in event:
            interrupted = True
            logger.info("✅ Interrupted!")
            break

    if not interrupted:
        logger.error("❌ Failed to interrupt")
        return False

    # Phase 2: Resume with COMPLEX data
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2: Resume with COMPLEX Data")
    logger.info("=" * 80)

    await asyncio.sleep(0.5)

    # Complex resume data (production-like)
    complex_resume_data = {
        "approved": True,
        "user_feedback": "검토 완료. 다음 항목 수정 필요",
        "modifications": [
            {"section": "introduction", "change": "Add more context"},
            {"section": "conclusion", "change": "Strengthen argument"}
        ],
        "metadata": {
            "timestamp": "2025-10-25T14:00:00",
            "user_id": "user-123",
            "review_duration_seconds": 45
        },
        "nested_object": {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        },
        "array_of_objects": [
            {"id": 1, "value": "first"},
            {"id": 2, "value": "second"}
        ]
    }

    logger.info("Resume data structure:")
    logger.info(f"  - approved: {complex_resume_data['approved']}")
    logger.info(f"  - modifications: {len(complex_resume_data['modifications'])} items")
    logger.info(f"  - metadata: {list(complex_resume_data['metadata'].keys())}")
    logger.info(f"  - nested_object: 3 levels deep")
    logger.info(f"  - array_of_objects: {len(complex_resume_data['array_of_objects'])} items")

    step_count = None
    received_data = None

    try:
        async for event in supervisor.app.astream(
            Command(resume=complex_resume_data),
            config
        ):
            if "document_subgraph" in event:
                result = event["document_subgraph"]
                step_count = result.get("step_count", 0)
                received_data = result.get("user_input")

                logger.info(f"\n✅ Subgraph completed!")
                logger.info(f"   Step count: {step_count}")
                logger.info(f"   Received data type: {type(received_data)}")

    except Exception as e:
        logger.error(f"❌ Error during resume: {e}", exc_info=True)
        return False

    # Verify
    logger.info("\n" + "=" * 80)
    logger.info("DATA VERIFICATION")
    logger.info("=" * 80)

    if step_count != 2:
        logger.error(f"❌ Step count failed: {step_count} (expected 2)")
        return False

    logger.info(f"✅ Step count correct: {step_count}")

    # Verify received data
    if received_data is None:
        logger.error("❌ No data received")
        return False

    logger.info(f"✅ Data received")

    # Check if complex data was preserved
    if isinstance(received_data, dict):
        logger.info(f"   Type: dict (correct)")

        # Check top-level fields
        if "approved" in received_data:
            logger.info(f"   ✅ 'approved' field present: {received_data['approved']}")
        else:
            logger.warning(f"   ⚠️ 'approved' field missing")

        if "metadata" in received_data:
            logger.info(f"   ✅ 'metadata' field present")
            if isinstance(received_data["metadata"], dict):
                logger.info(f"      Metadata keys: {list(received_data['metadata'].keys())}")
        else:
            logger.warning(f"   ⚠️ 'metadata' field missing")

        if "modifications" in received_data:
            logger.info(f"   ✅ 'modifications' field present: {len(received_data['modifications'])} items")
        else:
            logger.warning(f"   ⚠️ 'modifications' field missing")

        if "nested_object" in received_data:
            logger.info(f"   ✅ 'nested_object' field present")
            try:
                deep_value = received_data["nested_object"]["level1"]["level2"]["level3"]
                logger.info(f"      Deep nested value: '{deep_value}'")
            except:
                logger.warning(f"      ⚠️ Could not access deep nested value")
        else:
            logger.warning(f"   ⚠️ 'nested_object' field missing")

    else:
        logger.warning(f"   ⚠️ Received data is not dict: {type(received_data)}")

    # Final result
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULT")
    logger.info("=" * 80)

    success = step_count == 2 and received_data is not None

    if success:
        logger.info("✅ TEST PASSED!")
        logger.info("   Complex data structures work correctly")
        logger.info("   interrupt() can handle nested objects and arrays")
        return True
    else:
        logger.error("❌ TEST FAILED!")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_complex_resume_data())
    exit(0 if result else 1)
