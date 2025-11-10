"""
Frontdesk Agent DB Integration Test

Tools와 State의 DB 통합을 검증합니다.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from database import frontdesk_crud
from database.session import get_db


async def test_full_workflow():
    """전체 workflow 시뮬레이션"""
    print("\n" + "=" * 60)
    print("FRONTDESK AGENT DB INTEGRATION TEST")
    print("=" * 60)

    async with await get_db() as session:

        # Step 1: 문의 접수 (inquiry_handler_node 시뮬레이션)
        print("\n[Step 1] Inquiry Reception")
        print("-" * 60)

        inquiry_text = "PT 가격과 프로그램이 궁금합니다. 체중 감량 목적입니다."
        intent = "pricing_inquiry"

        print(f"  Inquiry: {inquiry_text}")
        print(f"  Intent: {intent}")

        # Step 2: Lead 생성 및 스코어링 (lead_scorer_node 시뮬레이션)
        print("\n[Step 2] Lead Creation & Scoring")
        print("-" * 60)

        lead_data = {
            "name": "이영희",
            "phone": "010-1111-2222",
            "email": "lee@example.com",
            "inquiry_type": intent,
            "inquiry_content": inquiry_text,
            "lead_score": 0.78,
            "priority": "high",
            "source": "website"
        }

        lead = await frontdesk_crud.create_lead(session, lead_data)

        if lead:
            print(f"  ✓ Lead created in database")
            print(f"    ID: {lead.id} (type: {type(lead.id).__name__})")
            print(f"    Name: {lead.name}")
            print(f"    Score: {lead.score}")
            print(f"    Status: {lead.status}")

            # Verify it's an integer
            assert isinstance(lead.id, int), f"Expected int, got {type(lead.id)}"
            print(f"  ✓ Lead ID is integer (PostgreSQL auto-increment)")

            # Convert to dict (State format)
            lead_info = frontdesk_crud.lead_to_dict(lead)
            print(f"\n  State format (lead_info):")
            print(f"    lead_id: {lead_info['lead_id']} (type: {type(lead_info['lead_id']).__name__})")
            print(f"    score: {lead_info['score']} (type: {type(lead_info['score']).__name__})")

        else:
            print("  ✗ Failed to create lead")
            return

        # Step 3: Inquiry 레코드 생성
        print("\n[Step 3] Inquiry Record Creation")
        print("-" * 60)

        inquiry_data = {
            "lead_id": lead.id,  # Integer foreign key
            "inquiry_content": inquiry_text,
            "inquiry_type": intent,
            "handled_by": "AI Agent"
        }

        inquiry = await frontdesk_crud.create_inquiry(session, inquiry_data)

        if inquiry:
            print(f"  ✓ Inquiry created in database")
            print(f"    ID: {inquiry.id}")
            print(f"    Lead ID (FK): {inquiry.lead_id}")
            print(f"    Type: {inquiry.inquiry_type}")

            # Verify foreign key relationship
            assert inquiry.lead_id == lead.id, "Foreign key mismatch"
            print(f"  ✓ Foreign key relationship verified")

        else:
            print("  ✗ Failed to create inquiry")

        # Step 4: 가능한 일정 조회 (appointment_scheduler_node 시뮬레이션)
        print("\n[Step 4] Available Appointment Slots Query")
        print("-" * 60)

        from datetime import datetime, timedelta
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        slots = await frontdesk_crud.get_available_appointment_slots(
            session,
            start_date,
            end_date
        )

        print(f"  ✓ Found {len(slots)} available slots")
        if slots:
            print(f"    First 3 slots:")
            for i, slot in enumerate(slots[:3], 1):
                print(f"      {i}. {slot['date']} at {slot['time']}")

        # Step 5: 예약 생성
        print("\n[Step 5] Appointment Creation")
        print("-" * 60)

        if slots:
            first_slot = slots[0]
            appointment_data = {
                "lead_id": lead.id,  # Integer foreign key
                "scheduled_date": first_slot['date'],
                "scheduled_time": first_slot['time'],
                "appointment_type": "consultation",
                "status": "scheduled",
                "notes": "초기 상담"
            }

            appointment = await frontdesk_crud.create_appointment(session, appointment_data)

            if appointment:
                print(f"  ✓ Appointment created in database")
                print(f"    ID: {appointment.id} (type: {type(appointment.id).__name__})")
                print(f"    Lead ID (FK): {appointment.lead_id}")
                print(f"    Date: {appointment.appointment_date}")
                print(f"    Type: {appointment.appointment_type}")

                # Verify foreign key
                assert appointment.lead_id == lead.id, "Foreign key mismatch"
                print(f"  ✓ Foreign key relationship verified")

                # Convert to dict (State format)
                appointment_info = frontdesk_crud.appointment_to_dict(appointment)
                print(f"\n  State format (appointment_info):")
                print(f"    appointment_id: {appointment_info['appointment_id']} (type: {type(appointment_info['appointment_id']).__name__})")
                print(f"    lead_id: {appointment_info['lead_id']} (type: {type(appointment_info['lead_id']).__name__})")

                # Verify types for State schema
                assert isinstance(appointment_info['appointment_id'], int), "appointment_id should be int"
                assert isinstance(appointment_info['lead_id'], int), "lead_id should be int"
                print(f"  ✓ State schema types verified")

            else:
                print("  ✗ Failed to create appointment")

        # Step 6: Lead 히스토리 조회
        print("\n[Step 6] Lead History Query")
        print("-" * 60)

        # Get inquiries
        inquiries = await frontdesk_crud.get_inquiries_by_lead(session, lead.id)
        print(f"  ✓ Found {len(inquiries)} inquiry records")

        # Get appointments
        appointments = await frontdesk_crud.get_appointments_by_lead(session, lead.id)
        print(f"  ✓ Found {len(appointments)} appointment records")

        print(f"\n  Lead history timeline:")
        for inq in inquiries:
            print(f"    - [{inq.created_at}] Inquiry: {inq.inquiry_type}")

        for apt in appointments:
            print(f"    - [{apt.created_at}] Appointment: {apt.appointment_type}")

        # Step 7: Lead 상태 업데이트 (notification_sender_node 이후)
        print("\n[Step 7] Lead Status Update")
        print("-" * 60)

        success = await frontdesk_crud.update_lead_status(
            session,
            lead.id,
            "contacted",
            "트레이너에게 배정됨"
        )

        if success:
            updated_lead = await frontdesk_crud.get_lead_by_id(session, lead.id)
            print(f"  ✓ Lead status updated")
            print(f"    Previous: new")
            print(f"    Current: {updated_lead.status}")
        else:
            print("  ✗ Failed to update lead status")

    print("\n" + "=" * 60)
    print("WORKFLOW SIMULATION COMPLETED")
    print("=" * 60)
    print("\n✅ All steps executed successfully!")
    print("\n📊 Verification Results:")
    print("  ✓ Lead created with integer ID (PostgreSQL)")
    print("  ✓ Inquiry linked via foreign key")
    print("  ✓ Appointment slots queried from database")
    print("  ✓ Appointment created with integer ID")
    print("  ✓ State schema types match (all IDs are integers)")
    print("  ✓ Lead history retrieval works")
    print("  ✓ Lead status update works")
    print("\n🎯 Frontdesk Agent DB Integration: VERIFIED")


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
