"""Frontdesk Agent Tools

신규 문의 처리, 리드 관리, 상담 예약 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.database.relation_db.models import Lead, Inquiry, Appointment
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== Lead Management Tools ====================

async def create_lead(
    name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    source: str = "website",
    interest: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """새로운 리드 생성

    Args:
        name: 리드 이름
        phone: 전화번호
        email: 이메일
        source: 유입 경로 (website, phone, walk_in, referral)
        interest: 관심사 (weight_loss, muscle_gain, fitness)
        notes: 추가 메모

    Returns:
        생성된 리드 정보
    """
    try:
        with get_db() as db:
            lead = Lead(
                name=name,
                phone=phone,
                email=email,
                source=source,
                interest=interest,
                status="new",
                notes=notes
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

            logger.info(f"[Frontdesk] Lead created: {lead.name} (ID: {lead.id})")

            return {
                "success": True,
                "lead_id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "email": lead.email,
                "source": lead.source,
                "status": lead.status
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to create lead: {e}")
        return {"success": False, "error": str(e)}


async def get_lead(lead_id: int) -> Dict[str, Any]:
    """리드 정보 조회

    Args:
        lead_id: 리드 ID

    Returns:
        리드 정보
    """
    try:
        with get_db() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()

            if not lead:
                return {"success": False, "error": "Lead not found"}

            return {
                "success": True,
                "lead": {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "email": lead.email,
                    "source": lead.source,
                    "interest": lead.interest,
                    "score": lead.score,
                    "status": lead.status,
                    "notes": lead.notes,
                    "created_at": lead.created_at.isoformat()
                }
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to get lead: {e}")
        return {"success": False, "error": str(e)}


async def get_all_leads(status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """모든 리드 조회

    Args:
        status: 상태 필터 (new, contacted, scheduled, converted, lost)
        limit: 조회 개수 제한

    Returns:
        리드 목록
    """
    try:
        with get_db() as db:
            query = db.query(Lead)

            if status:
                query = query.filter(Lead.status == status)

            leads = query.order_by(Lead.created_at.desc()).limit(limit).all()

            return {
                "success": True,
                "count": len(leads),
                "leads": [
                    {
                        "id": lead.id,
                        "name": lead.name,
                        "phone": lead.phone,
                        "email": lead.email,
                        "source": lead.source,
                        "interest": lead.interest,
                        "score": lead.score,
                        "status": lead.status,
                        "created_at": lead.created_at.isoformat()
                    }
                    for lead in leads
                ]
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to get leads: {e}")
        return {"success": False, "error": str(e)}


async def update_lead_status(lead_id: int, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """리드 상태 업데이트

    Args:
        lead_id: 리드 ID
        status: 새로운 상태 (new, contacted, scheduled, converted, lost)
        notes: 추가 메모

    Returns:
        업데이트 결과
    """
    try:
        with get_db() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()

            if not lead:
                return {"success": False, "error": "Lead not found"}

            lead.status = status
            if notes:
                lead.notes = f"{lead.notes}\n{notes}" if lead.notes else notes

            db.commit()

            logger.info(f"[Frontdesk] Lead {lead_id} status updated to: {status}")

            return {
                "success": True,
                "lead_id": lead_id,
                "status": status
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to update lead status: {e}")
        return {"success": False, "error": str(e)}


async def calculate_lead_score(lead_id: int, factors: Dict[str, float]) -> Dict[str, Any]:
    """리드 스코어 계산

    Args:
        lead_id: 리드 ID
        factors: 스코어링 요소 {"urgency": 0.8, "budget_fit": 0.9, "engagement": 0.7}

    Returns:
        계산된 리드 스코어
    """
    try:
        # 스코어 계산 로직 (간단한 weighted average)
        weights = {
            "urgency": 0.3,
            "budget_fit": 0.3,
            "engagement": 0.2,
            "fit": 0.2
        }

        total_score = 0
        for factor, value in factors.items():
            if factor in weights:
                total_score += value * weights[factor]

        # 0-100 스케일로 변환
        score = int(total_score * 100)

        # DB 업데이트
        with get_db() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()

            if not lead:
                return {"success": False, "error": "Lead not found"}

            lead.score = score
            db.commit()

            logger.info(f"[Frontdesk] Lead {lead_id} score updated to: {score}")

            return {
                "success": True,
                "lead_id": lead_id,
                "score": score,
                "factors": factors
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to calculate lead score: {e}")
        return {"success": False, "error": str(e)}


# ==================== Inquiry Management Tools ====================

async def create_inquiry(
    lead_id: int,
    inquiry_text: str,
    inquiry_type: str = "general",
    response_text: Optional[str] = None
) -> Dict[str, Any]:
    """문의 생성

    Args:
        lead_id: 리드 ID
        inquiry_text: 문의 내용
        inquiry_type: 문의 유형 (pricing, schedule, program, facility)
        response_text: 응답 내용

    Returns:
        생성된 문의 정보
    """
    try:
        with get_db() as db:
            inquiry = Inquiry(
                lead_id=lead_id,
                inquiry_text=inquiry_text,
                response_text=response_text,
                inquiry_type=inquiry_type,
                handled_by="AI Agent"
            )
            db.add(inquiry)
            db.commit()
            db.refresh(inquiry)

            logger.info(f"[Frontdesk] Inquiry created for lead {lead_id}")

            return {
                "success": True,
                "inquiry_id": inquiry.id,
                "lead_id": lead_id,
                "inquiry_type": inquiry_type
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to create inquiry: {e}")
        return {"success": False, "error": str(e)}


async def get_inquiries(lead_id: int) -> Dict[str, Any]:
    """리드의 모든 문의 조회

    Args:
        lead_id: 리드 ID

    Returns:
        문의 목록
    """
    try:
        with get_db() as db:
            inquiries = db.query(Inquiry).filter(Inquiry.lead_id == lead_id).all()

            return {
                "success": True,
                "count": len(inquiries),
                "inquiries": [
                    {
                        "id": inquiry.id,
                        "inquiry_text": inquiry.inquiry_text,
                        "response_text": inquiry.response_text,
                        "inquiry_type": inquiry.inquiry_type,
                        "handled_by": inquiry.handled_by,
                        "created_at": inquiry.created_at.isoformat()
                    }
                    for inquiry in inquiries
                ]
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to get inquiries: {e}")
        return {"success": False, "error": str(e)}


# ==================== Appointment Management Tools ====================

async def get_available_slots(
    start_date: Optional[datetime] = None,
    days: int = 7
) -> Dict[str, Any]:
    """예약 가능한 시간 슬롯 조회

    Args:
        start_date: 시작 날짜 (None이면 오늘)
        days: 조회할 일수

    Returns:
        예약 가능한 시간 슬롯 목록
    """
    try:
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Mock 데이터: 오전 10시~오후 8시, 1시간 단위
        available_slots = []

        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)

            # 주말 제외 (간단화)
            if current_date.weekday() >= 5:
                continue

            for hour in range(10, 20):  # 10am - 8pm
                slot_time = current_date.replace(hour=hour, minute=0)

                # 이미 예약된 시간 체크
                with get_db() as db:
                    existing = db.query(Appointment).filter(
                        Appointment.appointment_date == slot_time,
                        Appointment.status == "scheduled"
                    ).first()

                    if not existing:
                        available_slots.append({
                            "datetime": slot_time.isoformat(),
                            "display": slot_time.strftime("%Y-%m-%d %H:%M"),
                            "available": True
                        })

        return {
            "success": True,
            "count": len(available_slots),
            "slots": available_slots
        }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to get available slots: {e}")
        return {"success": False, "error": str(e)}


async def create_appointment(
    lead_id: int,
    appointment_date: datetime,
    appointment_type: str = "consultation",
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """상담 예약 생성

    Args:
        lead_id: 리드 ID
        appointment_date: 예약 날짜/시간
        appointment_type: 예약 유형 (consultation, trial, assessment)
        notes: 추가 메모

    Returns:
        생성된 예약 정보
    """
    try:
        with get_db() as db:
            appointment = Appointment(
                lead_id=lead_id,
                appointment_date=appointment_date,
                appointment_type=appointment_type,
                status="scheduled",
                notes=notes
            )
            db.add(appointment)
            db.commit()
            db.refresh(appointment)

            # 리드 상태를 "scheduled"로 업데이트
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.status = "scheduled"
                db.commit()

            logger.info(f"[Frontdesk] Appointment created for lead {lead_id}")

            return {
                "success": True,
                "appointment_id": appointment.id,
                "lead_id": lead_id,
                "appointment_date": appointment_date.isoformat(),
                "appointment_type": appointment_type,
                "status": "scheduled"
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to create appointment: {e}")
        return {"success": False, "error": str(e)}


async def update_appointment_status(
    appointment_id: int,
    status: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """예약 상태 업데이트

    Args:
        appointment_id: 예약 ID
        status: 새로운 상태 (scheduled, completed, cancelled, no_show)
        notes: 추가 메모

    Returns:
        업데이트 결과
    """
    try:
        with get_db() as db:
            appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

            if not appointment:
                return {"success": False, "error": "Appointment not found"}

            appointment.status = status
            if notes:
                appointment.notes = f"{appointment.notes}\n{notes}" if appointment.notes else notes

            db.commit()

            logger.info(f"[Frontdesk] Appointment {appointment_id} status updated to: {status}")

            return {
                "success": True,
                "appointment_id": appointment_id,
                "status": status
            }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to update appointment status: {e}")
        return {"success": False, "error": str(e)}


# ==================== Notification Tools ====================

async def send_notification(
    lead_id: int,
    notification_type: str,
    message: str,
    channel: str = "sms"
) -> Dict[str, Any]:
    """알림 전송 (Mock)

    Args:
        lead_id: 리드 ID
        notification_type: 알림 유형 (appointment_confirm, follow_up, reminder)
        message: 알림 메시지
        channel: 전송 채널 (sms, email, kakao)

    Returns:
        전송 결과
    """
    try:
        # Mock implementation - 실제로는 SMS/Email 서비스 연동
        logger.info(f"[Frontdesk] Notification sent to lead {lead_id} via {channel}")
        logger.info(f"[Frontdesk] Message: {message}")

        return {
            "success": True,
            "lead_id": lead_id,
            "notification_type": notification_type,
            "channel": channel,
            "sent_at": datetime.now().isoformat(),
            "message": message
        }
    except Exception as e:
        logger.error(f"[Frontdesk] Failed to send notification: {e}")
        return {"success": False, "error": str(e)}


# ==================== Utility Tools ====================

async def classify_inquiry_intent(inquiry_text: str) -> Dict[str, Any]:
    """문의 내용 분류 (간단한 키워드 기반)

    Args:
        inquiry_text: 문의 내용

    Returns:
        분류된 의도
    """
    inquiry_lower = inquiry_text.lower()

    # 간단한 키워드 매칭
    if any(keyword in inquiry_lower for keyword in ["가격", "비용", "얼마", "price", "cost"]):
        intent = "pricing"
    elif any(keyword in inquiry_lower for keyword in ["시간", "스케줄", "언제", "schedule", "time"]):
        intent = "schedule"
    elif any(keyword in inquiry_lower for keyword in ["프로그램", "운동", "다이어트", "program", "workout"]):
        intent = "program"
    elif any(keyword in inquiry_lower for keyword in ["시설", "장비", "샤워", "facility", "equipment"]):
        intent = "facility"
    else:
        intent = "general"

    return {
        "success": True,
        "intent": intent,
        "confidence": 0.8  # Mock confidence score
    }


__all__ = [
    "create_lead",
    "get_lead",
    "get_all_leads",
    "update_lead_status",
    "calculate_lead_score",
    "create_inquiry",
    "get_inquiries",
    "get_available_slots",
    "create_appointment",
    "update_appointment_status",
    "send_notification",
    "classify_inquiry_intent",
]
