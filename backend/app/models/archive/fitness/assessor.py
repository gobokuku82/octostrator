"""Assessor Agent models - InBodyData, PostureAnalysis"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from datetime import datetime
from .base import Base


class InBodyData(Base):
    """InBody 측정 데이터 테이블 (Assessor Agent)"""
    __tablename__ = "inbody_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    measurement_date = Column(DateTime, nullable=False)
    weight = Column(Float)
    muscle_mass = Column(Float)
    body_fat_mass = Column(Float)
    body_fat_percentage = Column(Float)
    bmr = Column(Integer)  # Basal Metabolic Rate
    visceral_fat_level = Column(Integer)
    body_water = Column(Float)
    protein = Column(Float)
    mineral = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostureAnalysis(Base):
    """자세 분석 테이블 (Assessor Agent)"""
    __tablename__ = "posture_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    analysis_date = Column(DateTime, nullable=False)
    front_image_url = Column(String(500))
    side_image_url = Column(String(500))
    back_image_url = Column(String(500))
    shoulder_alignment = Column(String(50))  # balanced, left_high, right_high
    hip_alignment = Column(String(50))  # balanced, left_high, right_high
    spine_curvature = Column(String(50))  # normal, kyphosis, lordosis, scoliosis
    issues = Column(Text)  # JSON: [{"area": "shoulder", "issue": "rounded", "severity": "moderate"}]
    recommendations = Column(Text)  # JSON: [{"exercise": "wall_angels", "sets": 3, "reps": 10}]
    created_at = Column(DateTime, default=datetime.utcnow)
