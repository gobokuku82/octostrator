"""Frontdesk Agent models - Lead, Inquiry, Appointment"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from .base import Base


class Lead(Base):
    """리드 정보 테이블 (Frontdesk Agent)"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    source = Column(String(50))  # website, phone, walk_in, referral
    interest = Column(String(100))  # weight_loss, muscle_gain, fitness
    score = Column(Integer, default=0)  # Lead scoring: 0-100
    status = Column(String(20), default="new")  # new, contacted, scheduled, converted, lost
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Inquiry(Base):
    """문의 내역 테이블 (Frontdesk Agent)"""
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    inquiry_text = Column(Text, nullable=False)
    response_text = Column(Text)
    inquiry_type = Column(String(50))  # pricing, schedule, program, facility
    handled_by = Column(String(100))  # staff name or "AI Agent"
    created_at = Column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    """상담 예약 테이블 (Frontdesk Agent)"""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    appointment_date = Column(DateTime, nullable=False)
    appointment_type = Column(String(50))  # consultation, trial, assessment
    status = Column(String(20), default="scheduled")  # scheduled, completed, cancelled, no_show
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
