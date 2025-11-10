"""Assessor Agent Tools

InBody 분석, 자세 평가, 체력 측정 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.database.relation_db.models import InBodyData, PostureAnalysis, User
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== InBody Analysis Tools ====================

async def save_inbody_data(
    user_id: int,
    weight: float,
    muscle_mass: float,
    body_fat_mass: float,
    body_fat_percentage: float,
    bmr: int,
    visceral_fat_level: int,
    body_water: Optional[float] = None,
    protein: Optional[float] = None,
    mineral: Optional[float] = None,
    measurement_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """InBody 측정 데이터 저장

    Args:
        user_id: 사용자 ID
        weight: 체중 (kg)
        muscle_mass: 근육량 (kg)
        body_fat_mass: 체지방량 (kg)
        body_fat_percentage: 체지방률 (%)
        bmr: 기초대사량 (kcal)
        visceral_fat_level: 내장지방 레벨
        body_water: 체수분 (kg)
        protein: 단백질 (kg)
        mineral: 무기질 (kg)
        measurement_date: 측정 날짜

    Returns:
        저장된 InBody 데이터 정보
    """
    try:
        if measurement_date is None:
            measurement_date = datetime.now()

        with get_db() as db:
            inbody = InBodyData(
                user_id=user_id,
                measurement_date=measurement_date,
                weight=weight,
                muscle_mass=muscle_mass,
                body_fat_mass=body_fat_mass,
                body_fat_percentage=body_fat_percentage,
                bmr=bmr,
                visceral_fat_level=visceral_fat_level,
                body_water=body_water,
                protein=protein,
                mineral=mineral
            )
            db.add(inbody)
            db.commit()
            db.refresh(inbody)

            logger.info(f"[Assessor] InBody data saved for user {user_id}")

            return {
                "success": True,
                "inbody_id": inbody.id,
                "user_id": user_id,
                "measurement_date": measurement_date.isoformat(),
                "weight": weight,
                "body_fat_percentage": body_fat_percentage,
                "muscle_mass": muscle_mass
            }
    except Exception as e:
        logger.error(f"[Assessor] Failed to save InBody data: {e}")
        return {"success": False, "error": str(e)}


async def get_inbody_data(user_id: int, limit: int = 10) -> Dict[str, Any]:
    """사용자의 InBody 측정 데이터 조회

    Args:
        user_id: 사용자 ID
        limit: 조회 개수 제한

    Returns:
        InBody 데이터 목록
    """
    try:
        with get_db() as db:
            inbody_list = db.query(InBodyData).filter(
                InBodyData.user_id == user_id
            ).order_by(InBodyData.measurement_date.desc()).limit(limit).all()

            return {
                "success": True,
                "count": len(inbody_list),
                "data": [
                    {
                        "id": inbody.id,
                        "measurement_date": inbody.measurement_date.isoformat(),
                        "weight": inbody.weight,
                        "muscle_mass": inbody.muscle_mass,
                        "body_fat_mass": inbody.body_fat_mass,
                        "body_fat_percentage": inbody.body_fat_percentage,
                        "bmr": inbody.bmr,
                        "visceral_fat_level": inbody.visceral_fat_level,
                        "body_water": inbody.body_water,
                        "protein": inbody.protein,
                        "mineral": inbody.mineral
                    }
                    for inbody in inbody_list
                ]
            }
    except Exception as e:
        logger.error(f"[Assessor] Failed to get InBody data: {e}")
        return {"success": False, "error": str(e)}


async def analyze_inbody_trend(user_id: int, days: int = 30) -> Dict[str, Any]:
    """InBody 데이터 트렌드 분석

    Args:
        user_id: 사용자 ID
        days: 분석 기간 (일)

    Returns:
        트렌드 분석 결과
    """
    try:
        with get_db() as db:
            cutoff_date = datetime.now() - timedelta(days=days)

            inbody_list = db.query(InBodyData).filter(
                InBodyData.user_id == user_id,
                InBodyData.measurement_date >= cutoff_date
            ).order_by(InBodyData.measurement_date.asc()).all()

            if len(inbody_list) < 2:
                return {
                    "success": False,
                    "error": "Not enough data for trend analysis"
                }

            # 첫 데이터와 마지막 데이터 비교
            first = inbody_list[0]
            last = inbody_list[-1]

            weight_change = last.weight - first.weight
            muscle_change = last.muscle_mass - first.muscle_mass
            fat_change = last.body_fat_percentage - first.body_fat_percentage

            return {
                "success": True,
                "period_days": days,
                "measurements_count": len(inbody_list),
                "trends": {
                    "weight": {
                        "start": first.weight,
                        "end": last.weight,
                        "change": round(weight_change, 2),
                        "change_percent": round((weight_change / first.weight) * 100, 2)
                    },
                    "muscle_mass": {
                        "start": first.muscle_mass,
                        "end": last.muscle_mass,
                        "change": round(muscle_change, 2),
                        "change_percent": round((muscle_change / first.muscle_mass) * 100, 2)
                    },
                    "body_fat_percentage": {
                        "start": first.body_fat_percentage,
                        "end": last.body_fat_percentage,
                        "change": round(fat_change, 2)
                    }
                }
            }
    except Exception as e:
        logger.error(f"[Assessor] Failed to analyze InBody trend: {e}")
        return {"success": False, "error": str(e)}


# ==================== Posture Analysis Tools ====================

async def save_posture_analysis(
    user_id: int,
    front_image_url: Optional[str] = None,
    side_image_url: Optional[str] = None,
    back_image_url: Optional[str] = None,
    shoulder_alignment: str = "balanced",
    hip_alignment: str = "balanced",
    spine_curvature: str = "normal",
    issues: Optional[List[Dict[str, Any]]] = None,
    recommendations: Optional[List[Dict[str, Any]]] = None,
    analysis_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """자세 분석 결과 저장

    Args:
        user_id: 사용자 ID
        front_image_url: 정면 사진 URL
        side_image_url: 측면 사진 URL
        back_image_url: 후면 사진 URL
        shoulder_alignment: 어깨 정렬 (balanced, left_high, right_high)
        hip_alignment: 골반 정렬 (balanced, left_high, right_high)
        spine_curvature: 척추 만곡 (normal, kyphosis, lordosis, scoliosis)
        issues: 발견된 문제점 목록
        recommendations: 권장 운동 목록
        analysis_date: 분석 날짜

    Returns:
        저장된 자세 분석 정보
    """
    try:
        if analysis_date is None:
            analysis_date = datetime.now()

        with get_db() as db:
            posture = PostureAnalysis(
                user_id=user_id,
                analysis_date=analysis_date,
                front_image_url=front_image_url,
                side_image_url=side_image_url,
                back_image_url=back_image_url,
                shoulder_alignment=shoulder_alignment,
                hip_alignment=hip_alignment,
                spine_curvature=spine_curvature,
                issues=json.dumps(issues) if issues else None,
                recommendations=json.dumps(recommendations) if recommendations else None
            )
            db.add(posture)
            db.commit()
            db.refresh(posture)

            logger.info(f"[Assessor] Posture analysis saved for user {user_id}")

            return {
                "success": True,
                "posture_id": posture.id,
                "user_id": user_id,
                "analysis_date": analysis_date.isoformat(),
                "shoulder_alignment": shoulder_alignment,
                "hip_alignment": hip_alignment,
                "spine_curvature": spine_curvature,
                "issues_count": len(issues) if issues else 0
            }
    except Exception as e:
        logger.error(f"[Assessor] Failed to save posture analysis: {e}")
        return {"success": False, "error": str(e)}


async def get_posture_analysis(user_id: int, limit: int = 5) -> Dict[str, Any]:
    """사용자의 자세 분석 데이터 조회

    Args:
        user_id: 사용자 ID
        limit: 조회 개수 제한

    Returns:
        자세 분석 목록
    """
    try:
        with get_db() as db:
            posture_list = db.query(PostureAnalysis).filter(
                PostureAnalysis.user_id == user_id
            ).order_by(PostureAnalysis.analysis_date.desc()).limit(limit).all()

            return {
                "success": True,
                "count": len(posture_list),
                "data": [
                    {
                        "id": posture.id,
                        "analysis_date": posture.analysis_date.isoformat(),
                        "shoulder_alignment": posture.shoulder_alignment,
                        "hip_alignment": posture.hip_alignment,
                        "spine_curvature": posture.spine_curvature,
                        "front_image_url": posture.front_image_url,
                        "side_image_url": posture.side_image_url,
                        "back_image_url": posture.back_image_url,
                        "issues": json.loads(posture.issues) if posture.issues else [],
                        "recommendations": json.loads(posture.recommendations) if posture.recommendations else []
                    }
                    for posture in posture_list
                ]
            }
    except Exception as e:
        logger.error(f"[Assessor] Failed to get posture analysis: {e}")
        return {"success": False, "error": str(e)}


# ==================== Assessment Tools ====================

async def get_member_assessment_summary(user_id: int) -> Dict[str, Any]:
    """회원 종합 평가 요약

    Args:
        user_id: 사용자 ID

    Returns:
        종합 평가 요약
    """
    try:
        with get_db() as db:
            # 사용자 정보
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 최신 InBody 데이터
            latest_inbody = db.query(InBodyData).filter(
                InBodyData.user_id == user_id
            ).order_by(InBodyData.measurement_date.desc()).first()

            # 최신 자세 분석
            latest_posture = db.query(PostureAnalysis).filter(
                PostureAnalysis.user_id == user_id
            ).order_by(PostureAnalysis.analysis_date.desc()).first()

            summary = {
                "success": True,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "goal": user.goal,
                    "level": user.level
                },
                "body_composition": None,
                "posture": None
            }

            if latest_inbody:
                summary["body_composition"] = {
                    "measurement_date": latest_inbody.measurement_date.isoformat(),
                    "weight": latest_inbody.weight,
                    "muscle_mass": latest_inbody.muscle_mass,
                    "body_fat_percentage": latest_inbody.body_fat_percentage,
                    "bmr": latest_inbody.bmr,
                    "visceral_fat_level": latest_inbody.visceral_fat_level
                }

            if latest_posture:
                summary["posture"] = {
                    "analysis_date": latest_posture.analysis_date.isoformat(),
                    "shoulder_alignment": latest_posture.shoulder_alignment,
                    "hip_alignment": latest_posture.hip_alignment,
                    "spine_curvature": latest_posture.spine_curvature,
                    "issues": json.loads(latest_posture.issues) if latest_posture.issues else []
                }

            return summary

    except Exception as e:
        logger.error(f"[Assessor] Failed to get assessment summary: {e}")
        return {"success": False, "error": str(e)}


async def calculate_fitness_score(user_id: int) -> Dict[str, Any]:
    """체력 점수 계산 (Mock)

    Args:
        user_id: 사용자 ID

    Returns:
        체력 점수
    """
    try:
        # Mock 구현 - 실제로는 체력 측정 데이터 기반
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 간단한 mock 점수
            base_score = 70
            level_bonus = {"beginner": 0, "intermediate": 10, "advanced": 20}
            score = base_score + level_bonus.get(user.level, 0)

            return {
                "success": True,
                "user_id": user_id,
                "fitness_score": score,
                "components": {
                    "strength": 75,
                    "endurance": 70,
                    "flexibility": 65,
                    "balance": 80
                }
            }
    except Exception as e:
        logger.error(f"[Assessor] Failed to calculate fitness score: {e}")
        return {"success": False, "error": str(e)}


from datetime import timedelta

__all__ = [
    "save_inbody_data",
    "get_inbody_data",
    "analyze_inbody_trend",
    "save_posture_analysis",
    "get_posture_analysis",
    "get_member_assessment_summary",
    "calculate_fitness_score",
]
