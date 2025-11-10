"""Program Designer Agent models - Program, MealLog, WorkoutRoutine"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from .base import Base


class Program(Base):
    """운동/식단 프로그램 테이블 (Program Designer Agent)"""
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    program_type = Column(String(20))  # workout, diet, combined
    goal = Column(String(100))  # weight_loss, muscle_gain, strength, endurance
    duration_weeks = Column(Integer)
    workout_plan = Column(Text)  # JSON: workout routine details
    diet_plan = Column(Text)  # JSON: meal plan details
    template_id = Column(String(50))  # Reference to template used
    customizations = Column(Text)  # JSON: custom modifications
    status = Column(String(20), default="active")  # active, completed, paused
    created_at = Column(DateTime, default=datetime.utcnow)


class MealLog(Base):
    """식단 기록 테이블"""
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    meal_type = Column(String(20))  # breakfast, lunch, dinner, snack
    foods = Column(Text)  # JSON 문자열: [{"name": "계란", "quantity": 2, "unit": "개"}]
    nutrition = Column(Text)  # JSON 문자열: {"calories": 300, "protein": 24, ...}
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkoutRoutine(Base):
    """운동 루틴 테이블"""
    __tablename__ = "workout_routines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    muscle_group = Column(String(50))  # legs, chest, back, shoulders, arms
    exercises = Column(Text)  # JSON 문자열: [{"name": "스쿼트", "sets": 4, "reps": 10, ...}]
    created_at = Column(DateTime, default=datetime.utcnow)
