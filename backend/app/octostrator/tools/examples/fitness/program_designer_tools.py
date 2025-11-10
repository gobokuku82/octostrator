"""Program Designer Agent Tools

운동 및 식단 프로그램 생성, 관리 및 커스터마이징 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.database.relation_db.models import Program, ExerciseDB, User
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== Program Creation Tools ====================

async def create_program(
    user_id: int,
    program_type: str,
    goal: str,
    duration_weeks: int,
    workout_plan: Dict[str, Any],
    diet_plan: Dict[str, Any],
    template_id: str,
    customizations: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """새로운 운동/식단 프로그램 생성

    Args:
        user_id: 사용자 ID
        program_type: 프로그램 유형 (workout, diet, combined)
        goal: 목표 (weight_loss, muscle_gain, strength, endurance)
        duration_weeks: 프로그램 기간 (주)
        workout_plan: 운동 계획 (Dict)
        diet_plan: 식단 계획 (Dict)
        template_id: 사용된 템플릿 ID
        customizations: 커스터마이징 옵션

    Returns:
        생성된 프로그램 정보
    """
    try:
        with get_db() as db:
            # 사용자 확인
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            program = Program(
                user_id=user_id,
                program_type=program_type,
                goal=goal,
                duration_weeks=duration_weeks,
                workout_plan=json.dumps(workout_plan),
                diet_plan=json.dumps(diet_plan),
                template_id=template_id,
                customizations=json.dumps(customizations) if customizations else None,
                status="active"
            )
            db.add(program)
            db.commit()
            db.refresh(program)

            logger.info(f"[Program Designer] Program created for user {user_id} (ID: {program.id})")

            return {
                "success": True,
                "program_id": program.id,
                "user_id": user_id,
                "program_type": program_type,
                "goal": goal,
                "duration_weeks": duration_weeks,
                "template_id": template_id,
                "status": program.status,
                "created_at": program.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to create program: {e}")
        return {"success": False, "error": str(e)}


async def get_program(program_id: int) -> Dict[str, Any]:
    """프로그램 정보 조회

    Args:
        program_id: 프로그램 ID

    Returns:
        프로그램 정보
    """
    try:
        with get_db() as db:
            program = db.query(Program).filter(Program.id == program_id).first()

            if not program:
                return {"success": False, "error": "Program not found"}

            return {
                "success": True,
                "program": {
                    "id": program.id,
                    "user_id": program.user_id,
                    "program_type": program.program_type,
                    "goal": program.goal,
                    "duration_weeks": program.duration_weeks,
                    "workout_plan": json.loads(program.workout_plan) if program.workout_plan else {},
                    "diet_plan": json.loads(program.diet_plan) if program.diet_plan else {},
                    "template_id": program.template_id,
                    "customizations": json.loads(program.customizations) if program.customizations else {},
                    "status": program.status,
                    "created_at": program.created_at.isoformat()
                }
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to get program: {e}")
        return {"success": False, "error": str(e)}


async def get_user_programs(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """사용자의 모든 프로그램 조회

    Args:
        user_id: 사용자 ID
        status: 상태 필터 (active, completed, paused)
        limit: 조회 개수 제한

    Returns:
        프로그램 목록
    """
    try:
        with get_db() as db:
            query = db.query(Program).filter(Program.user_id == user_id)

            if status:
                query = query.filter(Program.status == status)

            programs = query.order_by(Program.created_at.desc()).limit(limit).all()

            return {
                "success": True,
                "count": len(programs),
                "programs": [
                    {
                        "id": program.id,
                        "program_type": program.program_type,
                        "goal": program.goal,
                        "duration_weeks": program.duration_weeks,
                        "template_id": program.template_id,
                        "status": program.status,
                        "created_at": program.created_at.isoformat()
                    }
                    for program in programs
                ]
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to get user programs: {e}")
        return {"success": False, "error": str(e)}


async def update_program_status(program_id: int, status: str) -> Dict[str, Any]:
    """프로그램 상태 업데이트

    Args:
        program_id: 프로그램 ID
        status: 새로운 상태 (active, completed, paused)

    Returns:
        업데이트 결과
    """
    try:
        with get_db() as db:
            program = db.query(Program).filter(Program.id == program_id).first()

            if not program:
                return {"success": False, "error": "Program not found"}

            program.status = status
            db.commit()

            logger.info(f"[Program Designer] Program {program_id} status updated to: {status}")

            return {
                "success": True,
                "program_id": program_id,
                "status": status
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to update program status: {e}")
        return {"success": False, "error": str(e)}


# ==================== Template Tools ====================

async def get_workout_templates() -> Dict[str, Any]:
    """사용 가능한 운동 템플릿 조회 (Mock Data)

    Returns:
        운동 템플릿 목록
    """
    try:
        templates = [
            {
                "template_id": "strength_gain_beginner",
                "name": "강력한 기초 구축 (초급)",
                "goal": "muscle_gain",
                "level": "beginner",
                "duration_weeks": 12,
                "description": "초급자를 위한 기초 근력 강화 프로그램",
                "workout_frequency": 4,  # 주당 운동 일수
                "focus_areas": ["compound_movements", "form_mastery", "strength_base"],
                "sample_schedule": {
                    "monday": "chest_triceps",
                    "wednesday": "back_biceps",
                    "thursday": "legs",
                    "saturday": "shoulders_core"
                }
            },
            {
                "template_id": "weight_loss_intermediate",
                "name": "지방 감소 및 체형 개선 (중급)",
                "goal": "weight_loss",
                "level": "intermediate",
                "duration_weeks": 16,
                "description": "중급자를 위한 체지방 감소 및 체형 개선 프로그램",
                "workout_frequency": 5,
                "focus_areas": ["calorie_deficit", "cardio_strength", "metabolic_conditioning"],
                "sample_schedule": {
                    "monday": "upper_body_strength",
                    "tuesday": "cardio_hiit",
                    "wednesday": "lower_body_strength",
                    "thursday": "active_recovery",
                    "friday": "full_body_circuit"
                }
            },
            {
                "template_id": "endurance_athlete",
                "name": "체력 및 지구력 향상 (고급)",
                "goal": "endurance",
                "level": "advanced",
                "duration_weeks": 20,
                "description": "고급자를 위한 지구력 및 체력 극대화 프로그램",
                "workout_frequency": 6,
                "focus_areas": ["aerobic_capacity", "VO2_max", "muscular_endurance"],
                "sample_schedule": {
                    "monday": "tempo_run_strength",
                    "tuesday": "interval_training",
                    "wednesday": "strength_conditioning",
                    "thursday": "long_endurance",
                    "friday": "speed_work",
                    "saturday": "circuit_training"
                }
            },
            {
                "template_id": "functional_strength",
                "name": "기능성 운동 및 안정성 (중급)",
                "goal": "strength",
                "level": "intermediate",
                "duration_weeks": 12,
                "description": "일상 활동 성능 향상 및 부상 예방 프로그램",
                "workout_frequency": 4,
                "focus_areas": ["functional_patterns", "core_stability", "mobility"],
                "sample_schedule": {
                    "monday": "lower_body_patterns",
                    "wednesday": "upper_body_patterns",
                    "thursday": "core_stability",
                    "saturday": "full_body_integration"
                }
            },
            {
                "template_id": "hypertrophy_muscle_gain",
                "name": "근육량 증가 프로그램 (중급-고급)",
                "goal": "muscle_gain",
                "level": "intermediate",
                "duration_weeks": 16,
                "description": "근육 비대 및 근력 증가를 위한 맞춤형 프로그램",
                "workout_frequency": 5,
                "focus_areas": ["progressive_overload", "hypertrophy_rep_ranges", "volume_training"],
                "sample_schedule": {
                    "monday": "chest_triceps_hypertrophy",
                    "tuesday": "back_biceps_hypertrophy",
                    "wednesday": "rest_or_mobility",
                    "thursday": "legs_hypertrophy",
                    "friday": "shoulders_arms_hypertrophy",
                    "saturday": "accessory_work"
                }
            }
        ]

        logger.info(f"[Program Designer] Retrieved {len(templates)} workout templates")

        return {
            "success": True,
            "count": len(templates),
            "templates": templates
        }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to get workout templates: {e}")
        return {"success": False, "error": str(e)}


async def get_diet_templates() -> Dict[str, Any]:
    """사용 가능한 식단 템플릿 조회 (Mock Data)

    Returns:
        식단 템플릿 목록
    """
    try:
        templates = [
            {
                "template_id": "calorie_deficit_balanced",
                "name": "균형 잡힌 칼로리 감소 식단",
                "goal": "weight_loss",
                "level": "beginner",
                "duration_weeks": 12,
                "description": "안전하고 지속 가능한 체중 감소를 위한 균형 식단",
                "daily_calories": 2000,
                "macros": {
                    "protein_percent": 40,
                    "carbs_percent": 40,
                    "fat_percent": 20
                },
                "meal_frequency": 4,
                "features": ["balanced_nutrients", "sustainable", "flexible"]
            },
            {
                "template_id": "high_protein_muscle_gain",
                "name": "고단백 근육 성장 식단",
                "goal": "muscle_gain",
                "level": "intermediate",
                "duration_weeks": 16,
                "description": "근육 성장과 복구를 위한 고단백 식단",
                "daily_calories": 2800,
                "macros": {
                    "protein_percent": 45,
                    "carbs_percent": 40,
                    "fat_percent": 15
                },
                "meal_frequency": 5,
                "protein_per_kg": 2.2,
                "features": ["high_protein", "muscle_support", "recovery_focused"]
            },
            {
                "template_id": "atkins_low_carb",
                "name": "저탄수화물 케토제닉 식단",
                "goal": "weight_loss",
                "level": "intermediate",
                "duration_weeks": 8,
                "description": "지방을 주 에너지원으로 하는 저탄수 식단",
                "daily_calories": 1800,
                "macros": {
                    "protein_percent": 35,
                    "carbs_percent": 10,
                    "fat_percent": 55
                },
                "meal_frequency": 3,
                "carb_limit_grams": 50,
                "features": ["ketogenic", "appetite_suppression", "rapid_fat_loss"]
            },
            {
                "template_id": "mediterranean_wellness",
                "name": "지중해식 건강 식단",
                "goal": "fitness",
                "level": "beginner",
                "duration_weeks": 12,
                "description": "장기 건강과 웰니스를 위한 지중해식 식단",
                "daily_calories": 2200,
                "macros": {
                    "protein_percent": 25,
                    "carbs_percent": 50,
                    "fat_percent": 25
                },
                "meal_frequency": 3,
                "features": ["heart_healthy", "sustainable", "longevity_focused"]
            },
            {
                "template_id": "intermittent_fasting",
                "name": "간헐적 단식 프로토콜",
                "goal": "weight_loss",
                "level": "intermediate",
                "duration_weeks": 12,
                "description": "시간 제한 식사 패턴을 통한 지방 감소",
                "eating_window": "8_hours",
                "fasting_window": "16_hours",
                "macros": {
                    "protein_percent": 35,
                    "carbs_percent": 45,
                    "fat_percent": 20
                },
                "meal_frequency": 2,
                "features": ["time_restricted", "metabolic_flexibility", "simple"]
            },
            {
                "template_id": "vegan_athlete",
                "name": "채식 운동 선수 식단",
                "goal": "muscle_gain",
                "level": "advanced",
                "duration_weeks": 16,
                "description": "식물 기반 식품만으로 근육 성장을 위한 식단",
                "daily_calories": 2700,
                "macros": {
                    "protein_percent": 40,
                    "carbs_percent": 45,
                    "fat_percent": 15
                },
                "meal_frequency": 4,
                "features": ["plant_based", "complete_amino_acids", "ethical"]
            }
        ]

        logger.info(f"[Program Designer] Retrieved {len(templates)} diet templates")

        return {
            "success": True,
            "count": len(templates),
            "templates": templates
        }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to get diet templates: {e}")
        return {"success": False, "error": str(e)}


# ==================== Customization Tools ====================

async def customize_program(
    program_id: int,
    customizations: Dict[str, Any]
) -> Dict[str, Any]:
    """프로그램에 커스터마이징 적용

    Args:
        program_id: 프로그램 ID
        customizations: 적용할 커스터마이징 옵션 (Dict)

    Returns:
        커스터마이징 적용 결과
    """
    try:
        with get_db() as db:
            program = db.query(Program).filter(Program.id == program_id).first()

            if not program:
                return {"success": False, "error": "Program not found"}

            # 기존 커스터마이징 가져오기
            existing_customizations = {}
            if program.customizations:
                existing_customizations = json.loads(program.customizations)

            # 새로운 커스터마이징과 병합
            existing_customizations.update(customizations)

            # 업데이트
            program.customizations = json.dumps(existing_customizations)
            db.commit()

            logger.info(f"[Program Designer] Customizations applied to program {program_id}")

            return {
                "success": True,
                "program_id": program_id,
                "customizations": existing_customizations,
                "updated_at": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to customize program: {e}")
        return {"success": False, "error": str(e)}


# ==================== Exercise Database Tools ====================

async def search_exercises(
    muscle_group: Optional[str] = None,
    difficulty: Optional[str] = None,
    equipment: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """운동 데이터베이스에서 운동 검색

    Args:
        muscle_group: 근육 그룹 필터 (legs, chest, back, shoulders, arms)
        difficulty: 난이도 필터 (beginner, intermediate, advanced)
        equipment: 장비 필터 (barbell, dumbbell, bodyweight, machine)
        limit: 조회 개수 제한

    Returns:
        검색된 운동 목록
    """
    try:
        with get_db() as db:
            query = db.query(ExerciseDB)

            if muscle_group:
                query = query.filter(ExerciseDB.muscle_group == muscle_group)

            if difficulty:
                query = query.filter(ExerciseDB.difficulty == difficulty)

            if equipment:
                query = query.filter(ExerciseDB.equipment == equipment)

            exercises = query.limit(limit).all()

            return {
                "success": True,
                "count": len(exercises),
                "exercises": [
                    {
                        "id": exercise.id,
                        "name": exercise.name,
                        "muscle_group": exercise.muscle_group,
                        "difficulty": exercise.difficulty,
                        "equipment": exercise.equipment,
                        "description": exercise.description,
                        "video_url": exercise.video_url
                    }
                    for exercise in exercises
                ]
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to search exercises: {e}")
        return {"success": False, "error": str(e)}


async def get_exercise(exercise_id: int) -> Dict[str, Any]:
    """특정 운동 정보 조회

    Args:
        exercise_id: 운동 ID

    Returns:
        운동 정보
    """
    try:
        with get_db() as db:
            exercise = db.query(ExerciseDB).filter(ExerciseDB.id == exercise_id).first()

            if not exercise:
                return {"success": False, "error": "Exercise not found"}

            return {
                "success": True,
                "exercise": {
                    "id": exercise.id,
                    "name": exercise.name,
                    "muscle_group": exercise.muscle_group,
                    "difficulty": exercise.difficulty,
                    "equipment": exercise.equipment,
                    "description": exercise.description,
                    "video_url": exercise.video_url,
                    "created_at": exercise.created_at.isoformat()
                }
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to get exercise: {e}")
        return {"success": False, "error": str(e)}


# ==================== Program Analysis Tools ====================

async def get_program_summary(program_id: int) -> Dict[str, Any]:
    """프로그램 요약 정보 조회

    Args:
        program_id: 프로그램 ID

    Returns:
        프로그램 요약
    """
    try:
        with get_db() as db:
            program = db.query(Program).filter(Program.id == program_id).first()

            if not program:
                return {"success": False, "error": "Program not found"}

            user = db.query(User).filter(User.id == program.user_id).first()

            workout_plan = json.loads(program.workout_plan) if program.workout_plan else {}
            diet_plan = json.loads(program.diet_plan) if program.diet_plan else {}
            customizations = json.loads(program.customizations) if program.customizations else {}

            return {
                "success": True,
                "summary": {
                    "program_id": program.id,
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "goal": user.goal,
                        "level": user.level
                    } if user else None,
                    "program_type": program.program_type,
                    "goal": program.goal,
                    "duration_weeks": program.duration_weeks,
                    "template_id": program.template_id,
                    "status": program.status,
                    "created_at": program.created_at.isoformat(),
                    "workout_plan_summary": {
                        "type": workout_plan.get("type"),
                        "frequency": workout_plan.get("frequency"),
                        "focus_areas": workout_plan.get("focus_areas", [])
                    },
                    "diet_plan_summary": {
                        "daily_calories": diet_plan.get("daily_calories"),
                        "macros": diet_plan.get("macros", {})
                    },
                    "customization_count": len(customizations)
                }
            }
    except Exception as e:
        logger.error(f"[Program Designer] Failed to get program summary: {e}")
        return {"success": False, "error": str(e)}


__all__ = [
    "create_program",
    "get_program",
    "get_user_programs",
    "update_program_status",
    "get_workout_templates",
    "get_diet_templates",
    "customize_program",
    "search_exercises",
    "get_exercise",
    "get_program_summary",
]
