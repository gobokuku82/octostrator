"""Trainer Education Agent Tools

트레이너 교육 및 스킬 개발 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.database.relation_db.models import TrainerSkill, User
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== Training Modules (Mock Data) ====================

def _get_training_modules() -> List[Dict[str, Any]]:
    """트레이너 교육 모듈 목록 (Mock 데이터)

    Returns:
        교육 모듈 목록
    """
    return [
        {
            "id": "TM001",
            "name": "Advanced Strength Training Techniques",
            "category": "technique",
            "duration_hours": 20,
            "description": "Advanced programming for strength development",
            "target_proficiency": 4,
            "difficulty": "advanced"
        },
        {
            "id": "TM002",
            "name": "Client Communication & Motivation",
            "category": "communication",
            "duration_hours": 15,
            "description": "Effective communication and behavioral coaching",
            "target_proficiency": 4,
            "difficulty": "intermediate"
        },
        {
            "id": "TM003",
            "name": "Functional Movement Assessment",
            "category": "technique",
            "duration_hours": 25,
            "description": "Comprehensive movement screening and analysis",
            "target_proficiency": 4,
            "difficulty": "advanced"
        },
        {
            "id": "TM004",
            "name": "Program Design Fundamentals",
            "category": "program_design",
            "duration_hours": 30,
            "description": "Creating periodized training programs",
            "target_proficiency": 4,
            "difficulty": "intermediate"
        },
        {
            "id": "TM005",
            "name": "Sales & Client Retention",
            "category": "sales",
            "duration_hours": 18,
            "description": "Sales techniques and member retention strategies",
            "target_proficiency": 4,
            "difficulty": "intermediate"
        },
        {
            "id": "TM006",
            "name": "Injury Prevention & Rehabilitation",
            "category": "technique",
            "duration_hours": 28,
            "description": "Common injuries and rehabilitation protocols",
            "target_proficiency": 4,
            "difficulty": "advanced"
        },
        {
            "id": "TM007",
            "name": "Nutrition Coaching for Trainers",
            "category": "program_design",
            "duration_hours": 16,
            "description": "Basic nutrition principles for client guidance",
            "target_proficiency": 4,
            "difficulty": "beginner"
        },
        {
            "id": "TM008",
            "name": "Business Development & Marketing",
            "category": "sales",
            "duration_hours": 20,
            "description": "Building your personal brand and client base",
            "target_proficiency": 4,
            "difficulty": "intermediate"
        },
        {
            "id": "TM009",
            "name": "Leadership & Team Management",
            "category": "communication",
            "duration_hours": 18,
            "description": "Leading sessions, mentoring, and team dynamics",
            "target_proficiency": 4,
            "difficulty": "advanced"
        },
        {
            "id": "TM010",
            "name": "Core Stability & Flexibility",
            "category": "technique",
            "duration_hours": 22,
            "description": "Advanced core training and mobility work",
            "target_proficiency": 4,
            "difficulty": "intermediate"
        }
    ]


# ==================== Trainer Skill Recording Tools ====================

async def record_trainer_skill(
    trainer_id: int,
    skill_category: str,
    skill_name: str,
    proficiency_level: int,
    assessor: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """트레이너 스킬 기록

    Args:
        trainer_id: 트레이너 ID
        skill_category: 스킬 카테고리 (technique, communication, program_design, sales)
        skill_name: 스킬 이름
        proficiency_level: 숙련도 (1-5)
        assessor: 평가자 이름
        notes: 추가 노트

    Returns:
        기록된 스킬 정보
    """
    try:
        # Validate inputs
        if proficiency_level < 1 or proficiency_level > 5:
            return {"success": False, "error": "Proficiency level must be between 1 and 5"}

        valid_categories = ["technique", "communication", "program_design", "sales"]
        if skill_category not in valid_categories:
            return {"success": False, "error": f"Invalid skill category. Must be one of: {valid_categories}"}

        with get_db() as db:
            # Check if trainer exists
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": "Trainer not found"}

            # Create new skill record
            trainer_skill = TrainerSkill(
                trainer_id=trainer_id,
                skill_category=skill_category,
                skill_name=skill_name,
                proficiency_level=proficiency_level,
                assessment_date=datetime.now(),
                assessor=assessor,
                notes=notes
            )
            db.add(trainer_skill)
            db.commit()
            db.refresh(trainer_skill)

            logger.info(f"[Trainer Education] Skill recorded for trainer {trainer_id}: {skill_name} (Level {proficiency_level})")

            return {
                "success": True,
                "skill_id": trainer_skill.id,
                "trainer_id": trainer_id,
                "skill_name": skill_name,
                "skill_category": skill_category,
                "proficiency_level": proficiency_level,
                "assessment_date": trainer_skill.assessment_date.isoformat(),
                "assessor": assessor
            }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to record trainer skill: {e}")
        return {"success": False, "error": str(e)}


async def get_trainer_skills(
    trainer_id: int,
    skill_category: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """트레이너의 스킬 조회

    Args:
        trainer_id: 트레이너 ID
        skill_category: 스킬 카테고리 필터 (선택)
        limit: 조회 개수 제한

    Returns:
        스킬 목록
    """
    try:
        with get_db() as db:
            # Check if trainer exists
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": "Trainer not found"}

            # Query skills
            query = db.query(TrainerSkill).filter(TrainerSkill.trainer_id == trainer_id)

            if skill_category:
                query = query.filter(TrainerSkill.skill_category == skill_category)

            skills = query.order_by(TrainerSkill.assessment_date.desc()).limit(limit).all()

            # Group by category
            skills_by_category = {}
            for skill in skills:
                cat = skill.skill_category
                if cat not in skills_by_category:
                    skills_by_category[cat] = []

                skills_by_category[cat].append({
                    "id": skill.id,
                    "skill_name": skill.skill_name,
                    "proficiency_level": skill.proficiency_level,
                    "assessment_date": skill.assessment_date.isoformat(),
                    "assessor": skill.assessor,
                    "notes": skill.notes
                })

            return {
                "success": True,
                "trainer_id": trainer_id,
                "trainer_name": trainer.name,
                "total_skills": len(skills),
                "skills_by_category": skills_by_category
            }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to get trainer skills: {e}")
        return {"success": False, "error": str(e)}


async def assess_skill_level(
    trainer_id: int,
    skill_name: str,
    proficiency_level: int,
    assessor: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """스킬 수준 평가 (신규 또는 업데이트)

    Args:
        trainer_id: 트레이너 ID
        skill_name: 스킬 이름
        proficiency_level: 숙련도 (1-5)
        assessor: 평가자 이름
        notes: 평가 노트

    Returns:
        평가 결과
    """
    try:
        # Validate proficiency level
        if proficiency_level < 1 or proficiency_level > 5:
            return {"success": False, "error": "Proficiency level must be between 1 and 5"}

        with get_db() as db:
            # Check if trainer exists
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": "Trainer not found"}

            # Find existing skill
            existing_skill = db.query(TrainerSkill).filter(
                TrainerSkill.trainer_id == trainer_id,
                TrainerSkill.skill_name == skill_name
            ).order_by(TrainerSkill.assessment_date.desc()).first()

            if existing_skill:
                # Update existing skill
                old_level = existing_skill.proficiency_level
                existing_skill.proficiency_level = proficiency_level
                existing_skill.assessment_date = datetime.now()
                existing_skill.assessor = assessor
                existing_skill.notes = notes
                db.commit()
                db.refresh(existing_skill)

                logger.info(f"[Trainer Education] Skill {skill_name} updated for trainer {trainer_id}: {old_level} -> {proficiency_level}")

                return {
                    "success": True,
                    "skill_id": existing_skill.id,
                    "trainer_id": trainer_id,
                    "skill_name": skill_name,
                    "proficiency_level": proficiency_level,
                    "previous_level": old_level,
                    "assessment_date": existing_skill.assessment_date.isoformat(),
                    "assessor": assessor,
                    "action": "updated"
                }
            else:
                # Create new skill - need to determine category
                category_map = {
                    "technique": ["strength training", "movement", "form", "exercise", "assessment", "functional"],
                    "communication": ["communication", "motivation", "coaching", "leadership", "team"],
                    "program_design": ["programming", "periodization", "nutrition", "design"],
                    "sales": ["sales", "retention", "marketing", "business", "client acquisition"]
                }

                skill_category = "technique"  # default
                for cat, keywords in category_map.items():
                    if any(keyword in skill_name.lower() for keyword in keywords):
                        skill_category = cat
                        break

                new_skill = TrainerSkill(
                    trainer_id=trainer_id,
                    skill_category=skill_category,
                    skill_name=skill_name,
                    proficiency_level=proficiency_level,
                    assessment_date=datetime.now(),
                    assessor=assessor,
                    notes=notes
                )
                db.add(new_skill)
                db.commit()
                db.refresh(new_skill)

                logger.info(f"[Trainer Education] New skill {skill_name} created for trainer {trainer_id}: Level {proficiency_level}")

                return {
                    "success": True,
                    "skill_id": new_skill.id,
                    "trainer_id": trainer_id,
                    "skill_name": skill_name,
                    "skill_category": skill_category,
                    "proficiency_level": proficiency_level,
                    "assessment_date": new_skill.assessment_date.isoformat(),
                    "assessor": assessor,
                    "action": "created"
                }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to assess skill level: {e}")
        return {"success": False, "error": str(e)}


# ==================== Skill Gap Analysis Tools ====================

async def get_skill_gap_analysis(trainer_id: int) -> Dict[str, Any]:
    """트레이너 스킬 갭 분석

    Args:
        trainer_id: 트레이너 ID

    Returns:
        스킬 갭 분석 결과
    """
    try:
        with get_db() as db:
            # Check if trainer exists
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": "Trainer not found"}

            # Get all trainer skills
            skills = db.query(TrainerSkill).filter(
                TrainerSkill.trainer_id == trainer_id
            ).order_by(TrainerSkill.assessment_date.desc()).all()

            if not skills:
                return {
                    "success": True,
                    "trainer_id": trainer_id,
                    "trainer_name": trainer.name,
                    "message": "No skills recorded yet",
                    "gaps": []
                }

            # Group by skill name and get latest assessment
            latest_skills = {}
            for skill in skills:
                if skill.skill_name not in latest_skills:
                    latest_skills[skill.skill_name] = skill

            # Target proficiency is 4 for all skills
            TARGET_PROFICIENCY = 4
            gaps = []
            total_gap = 0

            for skill_name, skill in latest_skills.items():
                gap = TARGET_PROFICIENCY - skill.proficiency_level
                if gap > 0:
                    gaps.append({
                        "skill_name": skill_name,
                        "skill_category": skill.skill_category,
                        "current_level": skill.proficiency_level,
                        "target_level": TARGET_PROFICIENCY,
                        "gap": gap,
                        "last_assessment": skill.assessment_date.isoformat()
                    })
                    total_gap += gap

            # Group gaps by category
            gaps_by_category = {}
            for gap in gaps:
                cat = gap["skill_category"]
                if cat not in gaps_by_category:
                    gaps_by_category[cat] = []
                gaps_by_category[cat].append(gap)

            return {
                "success": True,
                "trainer_id": trainer_id,
                "trainer_name": trainer.name,
                "total_skills_assessed": len(latest_skills),
                "skills_with_gaps": len(gaps),
                "total_gap_points": total_gap,
                "gap_analysis": {
                    "by_skill": sorted(gaps, key=lambda x: x["gap"], reverse=True),
                    "by_category": gaps_by_category
                }
            }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to get skill gap analysis: {e}")
        return {"success": False, "error": str(e)}


# ==================== Development Plan Tools ====================

async def create_development_plan(
    trainer_id: int,
    target_skills: Optional[List[str]] = None
) -> Dict[str, Any]:
    """트레이너 개발 계획 생성

    Args:
        trainer_id: 트레이너 ID
        target_skills: 대상 스킬 목록 (선택)

    Returns:
        개발 계획
    """
    try:
        with get_db() as db:
            # Check if trainer exists
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": "Trainer not found"}

            # Get skill gap analysis
            gap_result = await get_skill_gap_analysis(trainer_id)
            if not gap_result["success"]:
                return gap_result

            gaps = gap_result["gap_analysis"]["by_skill"]

            if not gaps:
                return {
                    "success": True,
                    "trainer_id": trainer_id,
                    "trainer_name": trainer.name,
                    "message": "No skill gaps detected",
                    "plan": []
                }

            # Get available training modules
            modules = _get_training_modules()

            # Create development plan by matching gaps to modules
            plan = []
            module_map = {m["name"].lower(): m for m in modules}

            for gap in gaps[:5]:  # Top 5 gaps
                skill_name = gap["skill_name"].lower()
                category = gap["skill_category"]
                gap_level = gap["gap"]

                # Find matching modules
                recommended_modules = [
                    m for m in modules
                    if m["category"] == category and m["target_proficiency"] >= (gap["current_level"] + gap_level)
                ]

                if not recommended_modules:
                    # Fall back to category-based recommendation
                    recommended_modules = [
                        m for m in modules
                        if m["category"] == category
                    ][:2]

                plan_item = {
                    "skill_name": gap["skill_name"],
                    "skill_category": category,
                    "current_level": gap["current_level"],
                    "target_level": gap["target_level"],
                    "priority": "high" if gap_level >= 3 else "medium" if gap_level >= 2 else "low",
                    "recommended_modules": [
                        {
                            "id": m["id"],
                            "name": m["name"],
                            "duration_hours": m["duration_hours"],
                            "difficulty": m["difficulty"],
                            "description": m["description"]
                        }
                        for m in recommended_modules[:3]
                    ]
                }
                plan.append(plan_item)

            # Store improvement plan
            if gaps:
                # Update the latest skill record with improvement plan (for the most critical gap)
                latest_skill = db.query(TrainerSkill).filter(
                    TrainerSkill.trainer_id == trainer_id
                ).order_by(TrainerSkill.assessment_date.desc()).first()

                if latest_skill:
                    latest_skill.improvement_plan = json.dumps({
                        "created_date": datetime.now().isoformat(),
                        "plan": plan
                    })
                    db.commit()

            logger.info(f"[Trainer Education] Development plan created for trainer {trainer_id}")

            return {
                "success": True,
                "trainer_id": trainer_id,
                "trainer_name": trainer.name,
                "total_gaps": len(gaps),
                "plan": plan
            }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to create development plan: {e}")
        return {"success": False, "error": str(e)}


# ==================== Training Modules Tools ====================

async def get_training_modules() -> Dict[str, Any]:
    """사용 가능한 트레이너 교육 모듈 조회

    Returns:
        교육 모듈 목록
    """
    try:
        modules = _get_training_modules()

        # Group by category
        modules_by_category = {}
        for module in modules:
            cat = module["category"]
            if cat not in modules_by_category:
                modules_by_category[cat] = []
            modules_by_category[cat].append(module)

        logger.info(f"[Trainer Education] Retrieved {len(modules)} training modules")

        return {
            "success": True,
            "total_modules": len(modules),
            "modules": modules,
            "modules_by_category": modules_by_category
        }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to get training modules: {e}")
        return {"success": False, "error": str(e)}


# ==================== Training Progress Tools ====================

async def track_training_progress(
    trainer_id: int,
    module_id: str,
    completion_percentage: int
) -> Dict[str, Any]:
    """트레이너 교육 모듈 진행 상황 추적 (Mock)

    Args:
        trainer_id: 트레이너 ID
        module_id: 모듈 ID
        completion_percentage: 완료율 (0-100)

    Returns:
        진행 상황 추적 결과
    """
    try:
        # Validate completion percentage
        if completion_percentage < 0 or completion_percentage > 100:
            return {"success": False, "error": "Completion percentage must be between 0 and 100"}

        with get_db() as db:
            # Check if trainer exists
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": "Trainer not found"}

        # Get module info
        modules = _get_training_modules()
        module = next((m for m in modules if m["id"] == module_id), None)

        if not module:
            return {"success": False, "error": "Module not found"}

        logger.info(f"[Trainer Education] Training progress tracked for trainer {trainer_id}: {module_id} - {completion_percentage}%")

        # Mock data - in production this would be stored in a TrainerProgress table
        completion_status = "completed" if completion_percentage == 100 else "in_progress" if completion_percentage > 0 else "not_started"

        return {
            "success": True,
            "trainer_id": trainer_id,
            "module_id": module_id,
            "module_name": module["name"],
            "completion_percentage": completion_percentage,
            "status": completion_status,
            "tracked_at": datetime.now().isoformat(),
            "estimated_hours_remaining": int(module["duration_hours"] * (100 - completion_percentage) / 100)
        }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to track training progress: {e}")
        return {"success": False, "error": str(e)}


# ==================== Overview Tools ====================

async def get_all_trainers_overview() -> Dict[str, Any]:
    """모든 트레이너의 스킬 개요 조회

    Returns:
        모든 트레이너의 스킬 개요
    """
    try:
        with get_db() as db:
            # Get all trainers with skills
            trainers_with_skills = db.query(User).filter(
                User.id.in_(
                    db.query(TrainerSkill.trainer_id).distinct()
                )
            ).all()

            if not trainers_with_skills:
                return {
                    "success": True,
                    "total_trainers": 0,
                    "trainers": []
                }

            trainers_overview = []

            for trainer in trainers_with_skills:
                # Get all skills for this trainer
                skills = db.query(TrainerSkill).filter(
                    TrainerSkill.trainer_id == trainer.id
                ).order_by(TrainerSkill.assessment_date.desc()).all()

                # Get latest assessment for each skill
                latest_skills = {}
                for skill in skills:
                    if skill.skill_name not in latest_skills:
                        latest_skills[skill.skill_name] = skill

                # Calculate average proficiency
                avg_proficiency = sum(s.proficiency_level for s in latest_skills.values()) / len(latest_skills) if latest_skills else 0

                # Group by category
                skills_by_category = {}
                for skill_name, skill in latest_skills.items():
                    cat = skill.skill_category
                    if cat not in skills_by_category:
                        skills_by_category[cat] = []
                    skills_by_category[cat].append({
                        "name": skill_name,
                        "level": skill.proficiency_level
                    })

                trainers_overview.append({
                    "trainer_id": trainer.id,
                    "trainer_name": trainer.name,
                    "total_skills": len(latest_skills),
                    "average_proficiency": round(avg_proficiency, 2),
                    "skills_by_category": skills_by_category
                })

            logger.info(f"[Trainer Education] Retrieved overview for {len(trainers_with_skills)} trainers")

            return {
                "success": True,
                "total_trainers": len(trainers_with_skills),
                "trainers": sorted(trainers_overview, key=lambda x: x["average_proficiency"], reverse=True)
            }
    except Exception as e:
        logger.error(f"[Trainer Education] Failed to get trainers overview: {e}")
        return {"success": False, "error": str(e)}


__all__ = [
    "record_trainer_skill",
    "get_trainer_skills",
    "assess_skill_level",
    "get_skill_gap_analysis",
    "create_development_plan",
    "get_training_modules",
    "track_training_progress",
    "get_all_trainers_overview"
]
