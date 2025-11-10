"""Manager Agent Tools

회원 출석, 이탈 위험도, 회원 유지율 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.database.relation_db.models import Attendance, ChurnRisk, User, Schedule
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== Attendance Management Tools ====================

async def record_attendance(
    user_id: int,
    check_in_time: datetime,
    workout_type: str = "self_workout",
    trainer_id: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """회원 체크인 기록

    Args:
        user_id: 회원 ID
        check_in_time: 체크인 시간
        workout_type: 운동 유형 (pt_session, group_class, self_workout)
        trainer_id: 트레이너 ID (PT 세션의 경우)
        notes: 추가 메모

    Returns:
        기록된 출석 정보
    """
    try:
        with get_db() as db:
            # 이미 체크인한 기록이 있는지 확인
            existing = db.query(Attendance).filter(
                Attendance.user_id == user_id,
                Attendance.check_in_time >= check_in_time.replace(hour=0, minute=0, second=0, microsecond=0),
                Attendance.check_out_time == None
            ).first()

            if existing:
                return {
                    "success": False,
                    "error": "User already checked in today",
                    "attendance_id": existing.id
                }

            attendance = Attendance(
                user_id=user_id,
                check_in_time=check_in_time,
                workout_type=workout_type,
                trainer_id=trainer_id,
                notes=notes
            )
            db.add(attendance)
            db.commit()
            db.refresh(attendance)

            logger.info(f"[Manager] Attendance recorded for user {user_id}: {attendance.id}")

            return {
                "success": True,
                "attendance_id": attendance.id,
                "user_id": user_id,
                "check_in_time": check_in_time.isoformat(),
                "workout_type": workout_type,
                "trainer_id": trainer_id
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to record attendance: {e}")
        return {"success": False, "error": str(e)}


async def checkout_attendance(
    attendance_id: int,
    check_out_time: datetime
) -> Dict[str, Any]:
    """회원 체크아웃 기록

    Args:
        attendance_id: 출석 기록 ID
        check_out_time: 체크아웃 시간

    Returns:
        업데이트된 출석 정보
    """
    try:
        with get_db() as db:
            attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()

            if not attendance:
                return {"success": False, "error": "Attendance record not found"}

            if attendance.check_out_time:
                return {
                    "success": False,
                    "error": "Attendance already checked out",
                    "check_out_time": attendance.check_out_time.isoformat()
                }

            # 운동 시간 계산 (분 단위)
            duration_minutes = int((check_out_time - attendance.check_in_time).total_seconds() / 60)

            attendance.check_out_time = check_out_time
            db.commit()

            logger.info(f"[Manager] Attendance {attendance_id} checked out after {duration_minutes} minutes")

            return {
                "success": True,
                "attendance_id": attendance_id,
                "user_id": attendance.user_id,
                "check_in_time": attendance.check_in_time.isoformat(),
                "check_out_time": check_out_time.isoformat(),
                "duration_minutes": duration_minutes
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to checkout attendance: {e}")
        return {"success": False, "error": str(e)}


async def get_attendance_records(
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """회원 출석 기록 조회

    Args:
        user_id: 회원 ID
        start_date: 시작 날짜
        end_date: 종료 날짜
        limit: 조회 개수 제한

    Returns:
        출석 기록 목록
    """
    try:
        with get_db() as db:
            query = db.query(Attendance).filter(Attendance.user_id == user_id)

            if start_date:
                query = query.filter(Attendance.check_in_time >= start_date)
            if end_date:
                query = query.filter(Attendance.check_in_time <= end_date)

            records = query.order_by(Attendance.check_in_time.desc()).limit(limit).all()

            return {
                "success": True,
                "count": len(records),
                "records": [
                    {
                        "id": record.id,
                        "user_id": record.user_id,
                        "check_in_time": record.check_in_time.isoformat(),
                        "check_out_time": record.check_out_time.isoformat() if record.check_out_time else None,
                        "workout_type": record.workout_type,
                        "trainer_id": record.trainer_id,
                        "duration_minutes": int((record.check_out_time - record.check_in_time).total_seconds() / 60) if record.check_out_time else None,
                        "notes": record.notes
                    }
                    for record in records
                ]
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to get attendance records: {e}")
        return {"success": False, "error": str(e)}


async def calculate_attendance_rate(
    user_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """회원 출석률 계산

    Args:
        user_id: 회원 ID
        days: 기간 (일수)

    Returns:
        출석률 정보
    """
    try:
        with get_db() as db:
            start_date = datetime.now() - timedelta(days=days)

            # 해당 기간 내 출석 기록
            attendance_count = db.query(Attendance).filter(
                Attendance.user_id == user_id,
                Attendance.check_in_time >= start_date
            ).count()

            # 해당 기간 내 스케줄 (기대 출석 수)
            schedule_count = db.query(Schedule).filter(
                Schedule.user_id == user_id,
                Schedule.date >= start_date,
                Schedule.status == "confirmed"
            ).count()

            # 출석률 계산
            if schedule_count > 0:
                attendance_rate = (attendance_count / schedule_count) * 100
            else:
                # 스케줄이 없으면 전체 운영일 기준으로 계산 (30일 기준)
                operating_days = min(days, (datetime.now() - start_date).days)
                attendance_rate = (attendance_count / max(operating_days, 1)) * 100 if operating_days > 0 else 0

            # 최대값을 100으로 제한
            attendance_rate = min(attendance_rate, 100.0)

            logger.info(f"[Manager] Attendance rate for user {user_id}: {attendance_rate:.1f}%")

            return {
                "success": True,
                "user_id": user_id,
                "attendance_count": attendance_count,
                "schedule_count": schedule_count,
                "attendance_rate": round(attendance_rate, 2),
                "period_days": days
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to calculate attendance rate: {e}")
        return {"success": False, "error": str(e)}


# ==================== Churn Risk Management Tools ====================

async def calculate_churn_risk(
    user_id: int
) -> Dict[str, Any]:
    """회원 이탈 위험도 계산 및 저장

    Args:
        user_id: 회원 ID

    Returns:
        계산된 이탈 위험도 정보
    """
    try:
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                return {"success": False, "error": "User not found"}

            # 최근 방문일 조회
            latest_attendance = db.query(Attendance).filter(
                Attendance.user_id == user_id
            ).order_by(Attendance.check_in_time.desc()).first()

            now = datetime.now()
            days_since_visit = (now - latest_attendance.check_in_time).days if latest_attendance else 999

            # 출석률 계산 (최근 30일)
            attendance_rate_response = await calculate_attendance_rate(user_id, days=30)
            attendance_rate = attendance_rate_response.get("attendance_rate", 0) if attendance_rate_response.get("success") else 0

            # 멤버십 만료일 확인 (현재는 mock, 실제로는 User 테이블에 membership_end_date 필드 필요)
            membership_end_date = now + timedelta(days=30)  # Mock: 30일 후 만료
            days_until_expiry = (membership_end_date - now).days

            # 이탈 위험도 계산 로직
            factors = []
            risk_score = 0.0

            # Factor 1: 최근 방문 여부 (가중치 35%)
            if days_since_visit > 14:
                weight = 0.35
                factor_score = min(days_since_visit / 60, 1.0)  # 60일 이상이면 1.0
                risk_score += factor_score * weight
                factors.append({
                    "factor": "low_recent_activity",
                    "days_since_visit": days_since_visit,
                    "weight": weight,
                    "score": round(factor_score, 3)
                })

            # Factor 2: 출석률 (가중치 35%)
            if attendance_rate < 50:
                weight = 0.35
                factor_score = 1.0 - (attendance_rate / 100)
                risk_score += factor_score * weight
                factors.append({
                    "factor": "low_attendance_rate",
                    "attendance_rate": round(attendance_rate, 2),
                    "weight": weight,
                    "score": round(factor_score, 3)
                })

            # Factor 3: 멤버십 만료 임박 (가중치 20%)
            if days_until_expiry < 30 and days_until_expiry >= 0:
                weight = 0.20
                factor_score = 1.0 - (days_until_expiry / 30)
                risk_score += factor_score * weight
                factors.append({
                    "factor": "membership_expiry_soon",
                    "days_until_expiry": days_until_expiry,
                    "weight": weight,
                    "score": round(factor_score, 3)
                })
            elif days_until_expiry < 0:
                # 멤버십 이미 만료됨
                weight = 0.20
                risk_score += weight
                factors.append({
                    "factor": "membership_expired",
                    "days_overdue": abs(days_until_expiry),
                    "weight": weight,
                    "score": 1.0
                })

            # 최종 위험도 정규화
            risk_score = min(risk_score, 1.0)

            # 위험도 레벨 결정
            if risk_score >= 0.75:
                risk_level = "critical"
            elif risk_score >= 0.50:
                risk_level = "high"
            elif risk_score >= 0.25:
                risk_level = "medium"
            else:
                risk_level = "low"

            # 권장 조치 사항 생성
            recommended_actions = []

            if days_since_visit > 14:
                recommended_actions.append({
                    "action": "send_motivation_message",
                    "priority": "high",
                    "description": "회원에게 동기부여 메시지 발송"
                })

            if attendance_rate < 50:
                recommended_actions.append({
                    "action": "schedule_personal_coaching",
                    "priority": "high",
                    "description": "개인 코칭 상담 예약"
                })

            if risk_level in ["high", "critical"]:
                recommended_actions.append({
                    "action": "offer_discount_renewal",
                    "priority": "high",
                    "description": "갱신 할인 제안"
                })
                recommended_actions.append({
                    "action": "assign_retention_manager",
                    "priority": "high",
                    "description": "회원 유지 담당자 배정"
                })

            # 기존 레코드 확인
            existing_risk = db.query(ChurnRisk).filter(ChurnRisk.user_id == user_id).first()

            if existing_risk:
                # 기존 레코드 업데이트
                existing_risk.risk_score = risk_score
                existing_risk.risk_level = risk_level
                existing_risk.factors = json.dumps(factors)
                existing_risk.last_attendance = latest_attendance.check_in_time if latest_attendance else None
                existing_risk.days_since_visit = days_since_visit
                existing_risk.membership_end_date = membership_end_date
                existing_risk.recommended_actions = json.dumps(recommended_actions)
                db.commit()
                churn_risk_id = existing_risk.id
            else:
                # 새 레코드 생성
                churn_risk = ChurnRisk(
                    user_id=user_id,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    factors=json.dumps(factors),
                    last_attendance=latest_attendance.check_in_time if latest_attendance else None,
                    days_since_visit=days_since_visit,
                    membership_end_date=membership_end_date,
                    recommended_actions=json.dumps(recommended_actions)
                )
                db.add(churn_risk)
                db.commit()
                db.refresh(churn_risk)
                churn_risk_id = churn_risk.id

            logger.info(f"[Manager] Churn risk calculated for user {user_id}: {risk_level} ({risk_score:.2f})")

            return {
                "success": True,
                "churn_risk_id": churn_risk_id,
                "user_id": user_id,
                "risk_score": round(risk_score, 3),
                "risk_level": risk_level,
                "days_since_visit": days_since_visit,
                "attendance_rate": round(attendance_rate, 2),
                "factors_count": len(factors),
                "recommended_actions_count": len(recommended_actions)
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to calculate churn risk: {e}")
        return {"success": False, "error": str(e)}


async def get_churn_risks(
    risk_level: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """위험도별 회원 조회

    Args:
        risk_level: 위험도 레벨 (low, medium, high, critical)
        limit: 조회 개수 제한

    Returns:
        이탈 위험 회원 목록
    """
    try:
        with get_db() as db:
            query = db.query(ChurnRisk).order_by(ChurnRisk.risk_score.desc())

            if risk_level:
                query = query.filter(ChurnRisk.risk_level == risk_level)

            risks = query.limit(limit).all()

            return {
                "success": True,
                "count": len(risks),
                "risk_level": risk_level,
                "risks": [
                    {
                        "id": risk.id,
                        "user_id": risk.user_id,
                        "risk_score": risk.risk_score,
                        "risk_level": risk.risk_level,
                        "days_since_visit": risk.days_since_visit,
                        "last_attendance": risk.last_attendance.isoformat() if risk.last_attendance else None,
                        "membership_end_date": risk.membership_end_date.isoformat() if risk.membership_end_date else None,
                        "factors": json.loads(risk.factors) if risk.factors else [],
                        "recommended_actions": json.loads(risk.recommended_actions) if risk.recommended_actions else []
                    }
                    for risk in risks
                ]
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to get churn risks: {e}")
        return {"success": False, "error": str(e)}


# ==================== Retention Management Tools ====================

async def get_renewal_candidates(
    days_before_expiry: int = 7
) -> Dict[str, Any]:
    """멤버십 갱신 대상자 조회

    Args:
        days_before_expiry: 만료 전 일수

    Returns:
        갱신 대상 회원 목록
    """
    try:
        with get_db() as db:
            now = datetime.now()
            expiry_start = now
            expiry_end = now + timedelta(days=days_before_expiry)

            # ChurnRisk에서 membership_end_date가 범위 내인 레코드 조회
            candidates = db.query(ChurnRisk).filter(
                ChurnRisk.membership_end_date >= expiry_start,
                ChurnRisk.membership_end_date <= expiry_end
            ).order_by(ChurnRisk.membership_end_date.asc()).all()

            return {
                "success": True,
                "count": len(candidates),
                "days_before_expiry": days_before_expiry,
                "candidates": [
                    {
                        "id": candidate.id,
                        "user_id": candidate.user_id,
                        "membership_end_date": candidate.membership_end_date.isoformat() if candidate.membership_end_date else None,
                        "days_until_expiry": (candidate.membership_end_date - now).days if candidate.membership_end_date else None,
                        "risk_level": candidate.risk_level,
                        "risk_score": candidate.risk_score,
                        "last_attendance": candidate.last_attendance.isoformat() if candidate.last_attendance else None,
                        "recommended_actions": json.loads(candidate.recommended_actions) if candidate.recommended_actions else []
                    }
                    for candidate in candidates
                ]
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to get renewal candidates: {e}")
        return {"success": False, "error": str(e)}


async def update_churn_risk_actions(
    churn_risk_id: int,
    actions_taken: List[str]
) -> Dict[str, Any]:
    """이탈 위험 회원 대응 조치 업데이트

    Args:
        churn_risk_id: 이탈 위험도 레코드 ID
        actions_taken: 실시된 조치 목록

    Returns:
        업데이트 결과
    """
    try:
        with get_db() as db:
            churn_risk = db.query(ChurnRisk).filter(ChurnRisk.id == churn_risk_id).first()

            if not churn_risk:
                return {"success": False, "error": "Churn risk record not found"}

            # 기존 권장사항 조회
            existing_actions = json.loads(churn_risk.recommended_actions) if churn_risk.recommended_actions else []

            # 실시된 조치 기록
            updated_actions = []
            for action in existing_actions:
                action_copy = action.copy()
                if action.get("action") in actions_taken:
                    action_copy["status"] = "completed"
                    action_copy["completed_at"] = datetime.now().isoformat()
                else:
                    action_copy["status"] = "pending"
                updated_actions.append(action_copy)

            churn_risk.recommended_actions = json.dumps(updated_actions)
            db.commit()

            completed_count = len([a for a in updated_actions if a.get("status") == "completed"])

            logger.info(f"[Manager] Churn risk {churn_risk_id} actions updated: {completed_count}/{len(updated_actions)} completed")

            return {
                "success": True,
                "churn_risk_id": churn_risk_id,
                "user_id": churn_risk.user_id,
                "actions_taken": actions_taken,
                "completed_count": completed_count,
                "total_actions": len(updated_actions)
            }
    except Exception as e:
        logger.error(f"[Manager] Failed to update churn risk actions: {e}")
        return {"success": False, "error": str(e)}


__all__ = [
    "record_attendance",
    "checkout_attendance",
    "get_attendance_records",
    "calculate_attendance_rate",
    "calculate_churn_risk",
    "get_churn_risks",
    "get_renewal_candidates",
    "update_churn_risk_actions",
]
