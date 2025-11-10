"""
Simple test script to verify Frontdesk DB integration
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from database.session import get_db
from database import frontdesk_crud


async def test_frontdesk_crud():
    """Test Frontdesk CRUD operations"""

    print("=" * 60)
    print("Testing Frontdesk Database Integration")
    print("=" * 60)

    async with await get_db() as session:

        # Test 1: Create Lead
        print("\n[Test 1] Creating lead...")
        lead_data = {
            "name": "홍길동",
            "phone": "010-1234-5678",
            "email": "hong@example.com",
            "source": "website",
            "inquiry_type": "weight_loss",
            "inquiry_content": "체중 감량 프로그램 문의",
            "lead_score": 0.85,
            "status": "new"
        }

        lead = await frontdesk_crud.create_lead(session, lead_data)

        if lead:
            print(f"✓ Lead created successfully!")
            print(f"  - ID: {lead.id}")
            print(f"  - Name: {lead.name}")
            print(f"  - Score: {lead.score}")
            print(f"  - Status: {lead.status}")
        else:
            print("✗ Failed to create lead")
            return

        # Test 2: Get Lead by ID
        print("\n[Test 2] Retrieving lead by ID...")
        retrieved_lead = await frontdesk_crud.get_lead_by_id(session, lead.id)

        if retrieved_lead:
            print(f"✓ Lead retrieved successfully!")
            print(f"  - Name: {retrieved_lead.name}")
            print(f"  - Email: {retrieved_lead.email}")
        else:
            print("✗ Failed to retrieve lead")

        # Test 3: Create Inquiry
        print("\n[Test 3] Creating inquiry...")
        inquiry_data = {
            "lead_id": lead.id,
            "inquiry_content": "PT 가격과 프로그램 문의드립니다.",
            "inquiry_type": "pricing",
            "handled_by": "AI Agent"
        }

        inquiry = await frontdesk_crud.create_inquiry(session, inquiry_data)

        if inquiry:
            print(f"✓ Inquiry created successfully!")
            print(f"  - ID: {inquiry.id}")
            print(f"  - Type: {inquiry.inquiry_type}")
            print(f"  - Handled by: {inquiry.handled_by}")
        else:
            print("✗ Failed to create inquiry")

        # Test 4: Create Appointment
        print("\n[Test 4] Creating appointment...")
        appointment_data = {
            "lead_id": lead.id,
            "scheduled_date": "2025-02-15",
            "scheduled_time": "14:00",
            "appointment_type": "consultation",
            "status": "scheduled",
            "notes": "초기 상담"
        }

        appointment = await frontdesk_crud.create_appointment(session, appointment_data)

        if appointment:
            print(f"✓ Appointment created successfully!")
            print(f"  - ID: {appointment.id}")
            print(f"  - Type: {appointment.appointment_type}")
            print(f"  - Date: {appointment.appointment_date}")
            print(f"  - Status: {appointment.status}")
        else:
            print("✗ Failed to create appointment")

        # Test 5: Get Inquiries by Lead
        print("\n[Test 5] Getting inquiries by lead...")
        inquiries = await frontdesk_crud.get_inquiries_by_lead(session, lead.id)

        print(f"✓ Retrieved {len(inquiries)} inquiries")
        for inq in inquiries:
            print(f"  - Type: {inq.inquiry_type}, Handled by: {inq.handled_by}")

        # Test 5b: Get Appointments by Lead
        print("\n[Test 5b] Getting appointments by lead...")
        appointments = await frontdesk_crud.get_appointments_by_lead(session, lead.id)

        print(f"✓ Retrieved {len(appointments)} appointments")
        for apt in appointments:
            print(f"  - Type: {apt.appointment_type}, Date: {apt.appointment_date}")

        # Test 6: Get Available Slots
        print("\n[Test 6] Getting available appointment slots...")
        slots = await frontdesk_crud.get_available_appointment_slots(
            session,
            "2025-02-10",
            "2025-02-14"
        )

        print(f"✓ Found {len(slots)} available slots")
        if slots:
            for i, slot in enumerate(slots[:3], 1):  # Show first 3
                print(f"  {i}. {slot['date']} at {slot['time']}")
            if len(slots) > 3:
                print(f"  ... and {len(slots) - 3} more slots")

        # Test 7: Update Lead Status
        print("\n[Test 7] Updating lead status...")
        success = await frontdesk_crud.update_lead_status(
            session,
            lead.id,
            "contacted",
            "고객에게 전화 연락 완료"
        )

        if success:
            updated_lead = await frontdesk_crud.get_lead_by_id(session, lead.id)
            print(f"✓ Lead status updated!")
            print(f"  - New status: {updated_lead.status}")
        else:
            print("✗ Failed to update lead status")

        # Test 8: Convert to Dict
        print("\n[Test 8] Converting models to dict...")
        lead_dict = frontdesk_crud.lead_to_dict(lead)
        print(f"✓ Lead dict keys: {list(lead_dict.keys())}")

        inquiry_dict = frontdesk_crud.inquiry_to_dict(inquiry)
        print(f"✓ Inquiry dict keys: {list(inquiry_dict.keys())}")

        appointment_dict = frontdesk_crud.appointment_to_dict(appointment)
        print(f"✓ Appointment dict keys: {list(appointment_dict.keys())}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_frontdesk_crud())
