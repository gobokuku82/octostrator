"""Owner Assistant models - Revenue, MemberProgress"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from datetime import datetime
from .base import Base


class Revenue(Base):
    """매출 데이터 테이블 (Owner Assistant Agent)"""
    __tablename__ = "revenue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    revenue_type = Column(String(50))  # membership, pt_session, product, event
    amount = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    trainer_id = Column(Integer, ForeignKey("users.id"))
    description = Column(String(500))
    payment_method = Column(String(50))  # card, cash, transfer
    created_at = Column(DateTime, default=datetime.utcnow)


class MemberProgress(Base):
    """회원 진행률 테이블"""
    __tablename__ = "member_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    weight = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass = Column(Float)
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
