"""
Frontdesk Agent Nodes Integration Tests

각 노드를 개별적으로 테스트합니다.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.octostrator.agents.frontdesk.frontdesk_nodes import (
    inquiry_handler_node,
    lead_scorer_node,
    appointment_scheduler_node,
    notification_sender_node
)


async def test_inquiry_handler_node():
    """Test 1: inquiry_handler_node"""
    print("\n" + "=" * 60)
    print("Test 1: inquiry_handler_node")
    print("=" * 60)

    # Mock state
    state = {
        "inquiry_text": "PT 가격과 프로그램이 궁금합니다. 체중 감량 목적입니다.",
        "conversation_history": []
    }

    try:
        result = await inquiry_handler_node(state)

        print(f"\n✓ Node executed successfully!")
        print(f"  Status: {result.get('status')}")
        print(f"  Intent: {result.get('intent_classification')}")
        print(f"  Recommended Action: {result.get('recommended_action')}")
        print(f"  Urgency: {result.get('urgency_level')}")
        print(f"  Response Preview: {result.get('response_text', '')[:100]}...")

        return True, result

    except Exception as e:
        print(f"\n✗ Node execution failed!")
        print(f"  Error: {e}")
        return False, None


async def test_lead_scorer_node():
    """Test 2: lead_scorer_node (DB Integration)"""
    print("\n" + "=" * 60)
    print("Test 2: lead_scorer_node (DB Integration)")
    print("=" * 60)

    # Mock state with task data
    state = {
        "intent_classification": "pricing_inquiry",
        "inquiry_text": "PT 가격과 프로그램이 궁금합니다.",
        "task": {
            "name": "김철수",
            "phone": "010-9876-5432",
            "email": "kim@example.com",
            "source": "website"
        }
    }

    try:
        result = await lead_scorer_node(state)

        print(f"\n✓ Node executed successfully!")
        print(f"  Status: {result.get('status')}")

        lead_info = result.get('lead_info')
        if lead_info:
            print(f"  Lead ID: {lead_info.get('lead_id')} (type: {type(lead_info.get('lead_id')).__name__})")
            print(f"  Lead Name: {lead_info.get('name')}")
            print(f"  Lead Score: {lead_info.get('score')}")
            print(f"  Priority: {lead_info.get('priority')}")

        print(f"  Estimated Conversion Rate: {result.get('estimated_conversion_rate')}")
        print(f"  Recommended Action: {result.get('recommended_action')}")

        # Verify lead_id is integer
        if lead_info and isinstance(lead_info.get('lead_id'), int):
            print(f"\n  ✓ lead_id is integer (PostgreSQL ID)")
        else:
            print(f"\n  ✗ lead_id type mismatch: expected int, got {type(lead_info.get('lead_id'))}")

        return True, result

    except Exception as e:
        print(f"\n✗ Node execution failed!")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_appointment_scheduler_node():
    """Test 3: appointment_scheduler_node (DB Integration)"""
    print("\n" + "=" * 60)
    print("Test 3: appointment_scheduler_node (DB Integration)")
    print("=" * 60)

    # Mock state with lead_info (integer ID)
    state = {
        "lead_info": {
            "lead_id": 1,  # Integer ID from database
            "name": "김철수",
            "phone": "010-9876-5432",
            "priority": "high"
        }
    }

    try:
        result = await appointment_scheduler_node(state)

        print(f"\n✓ Node executed successfully!")
        print(f"  Status: {result.get('status')}")

        available_slots = result.get('available_slots', [])
        print(f"  Available Slots: {len(available_slots)} found")

        if available_slots:
            print(f"  First 3 slots:")
            for i, slot in enumerate(available_slots[:3], 1):
                print(f"    {i}. {slot.get('date')} at {slot.get('time')}")

        print(f"  Scheduling Message Preview: {result.get('scheduling_message', '')[:100]}...")

        return True, result

    except Exception as e:
        print(f"\n✗ Node execution failed!")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_notification_sender_node():
    """Test 4: notification_sender_node"""
    print("\n" + "=" * 60)
    print("Test 4: notification_sender_node")
    print("=" * 60)

    # Mock state with lead_info (integer ID)
    state = {
        "lead_info": {
            "lead_id": 1,
            "name": "김철수",
            "phone": "010-9876-5432",
            "priority": "high",
            "score": 0.85
        },
        "appointment_info": None
    }

    try:
        result = await notification_sender_node(state)

        print(f"\n✓ Node executed successfully!")
        print(f"  Status: {result.get('status')}")
        print(f"  Notification Sent: {result.get('notification_sent')}")
        print(f"  Recipients: {result.get('notification_recipients')}")

        return True, result

    except Exception as e:
        print(f"\n✗ Node execution failed!")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def run_all_tests():
    """Run all node tests"""
    print("\n" + "=" * 60)
    print("FRONTDESK AGENT NODES INTEGRATION TESTS")
    print("=" * 60)

    results = {}

    # Test 1: inquiry_handler_node
    success, result = await test_inquiry_handler_node()
    results['inquiry_handler'] = success

    # Test 2: lead_scorer_node (DB Integration)
    success, result = await test_lead_scorer_node()
    results['lead_scorer'] = success

    if success and result:
        # Save lead_info for next tests
        lead_info = result.get('lead_info')
    else:
        lead_info = None

    # Test 3: appointment_scheduler_node (DB Integration)
    if lead_info:
        success, result = await test_appointment_scheduler_node()
        results['appointment_scheduler'] = success
    else:
        print("\n⚠ Skipping appointment_scheduler_node test (no lead_info)")
        results['appointment_scheduler'] = None

    # Test 4: notification_sender_node
    if lead_info:
        success, result = await test_notification_sender_node()
        results['notification_sender'] = success
    else:
        print("\n⚠ Skipping notification_sender_node test (no lead_info)")
        results['notification_sender'] = None

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, success in results.items():
        if success is True:
            status = "✓ PASSED"
        elif success is False:
            status = "✗ FAILED"
        else:
            status = "⚠ SKIPPED"

        print(f"  {test_name}: {status}")

    total = len([s for s in results.values() if s is not None])
    passed = len([s for s in results.values() if s is True])

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
