"""Manager Agent models - Attendance, ChurnRisk, Schedule"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from datetime import datetime
from .base import Base


class Attendance(Base):
    """출석 기록 테이블 (Manager Agent)"""
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    check_in_time = Column(DateTime, nullable=False)
    check_out_time = Column(DateTime)
    workout_type = Column(String(50))  # pt_session, group_class, self_workout
    trainer_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class ChurnRisk(Base):
    """이탈 위험도 테이블 (Manager Agent)"""
    __tablename__ = "churn_risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    risk_score = Column(Float)  # 0.0 - 1.0
    risk_level = Column(String(20))  # low, medium, high, critical
    factors = Column(Text)  # JSON: [{"factor": "low_attendance", "weight": 0.3}]
    last_attendance = Column(DateTime)
    days_since_visit = Column(Integer)
    membership_end_date = Column(DateTime)
    recommended_actions = Column(Text)  # JSON: suggested retention strategies
    created_at = Column(DateTime, default=datetime.utcnow)


class Schedule(Base):
    """PT 스케줄 테이블"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trainer_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(String(20))  # confirmed, cancelled, completed
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
