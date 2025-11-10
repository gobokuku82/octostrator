"""Trainer Education models - TrainerSkill"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from .base import Base


class TrainerSkill(Base):
    """트레이너 스킬 테이블 (Trainer Education Agent)"""
    __tablename__ = "trainer_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trainer_id = Column(Integer, ForeignKey("users.id"))
    skill_category = Column(String(50))  # technique, communication, program_design, sales
    skill_name = Column(String(100), nullable=False)
    proficiency_level = Column(Integer)  # 1-5
    assessment_date = Column(DateTime, nullable=False)
    assessor = Column(String(100))  # Who assessed the skill
    notes = Column(Text)
    improvement_plan = Column(Text)  # JSON: training recommendations
    created_at = Column(DateTime, default=datetime.utcnow)
