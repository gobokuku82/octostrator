"""Owner Assistant Agent Tools

매출 분석, 사업 성과, 재무 데이터 관련 도구들
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.database.relation_db.models import Revenue, User, Schedule, Attendance
from backend.database.relation_db.session import get_db
import logging
import json

logger = logging.getLogger(__name__)


# ==================== Revenue Recording Tools ====================

async def record_revenue(
    date: datetime,
    revenue_type: str,
    amount: float,
    user_id: int,
    trainer_id: Optional[int] = None,
    description: Optional[str] = None,
    payment_method: str = "card"
) -> Dict[str, Any]:
    """매출 거래 기록

    Args:
        date: 거래 날짜
        revenue_type: 매출 유형 (membership, pt_session, product, event)
        amount: 거래 금액
        user_id: 회원 ID
        trainer_id: 트레이너 ID (선택사항)
        description: 거래 설명
        payment_method: 결제 방법 (card, cash, transfer)

    Returns:
        기록된 매출 정보
    """
    try:
        # 입력값 검증
        valid_types = ["membership", "pt_session", "product", "event"]
        valid_methods = ["card", "cash", "transfer"]

        if revenue_type not in valid_types:
            return {"success": False, "error": f"Invalid revenue_type. Must be one of {valid_types}"}

        if payment_method not in valid_methods:
            return {"success": False, "error": f"Invalid payment_method. Must be one of {valid_methods}"}

        if amount <= 0:
            return {"success": False, "error": "Amount must be greater than 0"}

        with get_db() as db:
            # 해당 회원 존재 여부 확인
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": f"User with id {user_id} not found"}

            # 트레이너 ID가 제공된 경우 확인
            if trainer_id:
                trainer = db.query(User).filter(User.id == trainer_id).first()
                if not trainer:
                    return {"success": False, "error": f"Trainer with id {trainer_id} not found"}

            revenue = Revenue(
                date=date,
                revenue_type=revenue_type,
                amount=amount,
                user_id=user_id,
                trainer_id=trainer_id,
                description=description,
                payment_method=payment_method
            )
            db.add(revenue)
            db.commit()
            db.refresh(revenue)

            logger.info(f"[Owner] Revenue recorded: {revenue_type} - ${amount} from user {user_id}")

            return {
                "success": True,
                "revenue_id": revenue.id,
                "date": date.isoformat(),
                "revenue_type": revenue_type,
                "amount": amount,
                "user_id": user_id,
                "trainer_id": trainer_id,
                "payment_method": payment_method
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to record revenue: {e}")
        return {"success": False, "error": str(e)}


# ==================== Revenue Retrieval Tools ====================

async def get_revenue_records(
    start_date: datetime,
    end_date: datetime,
    revenue_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """매출 기록 조회

    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        revenue_type: 매출 유형 필터 (선택사항)
        limit: 조회 개수 제한

    Returns:
        매출 기록 목록
    """
    try:
        with get_db() as db:
            query = db.query(Revenue).filter(
                Revenue.date >= start_date,
                Revenue.date <= end_date
            )

            if revenue_type:
                query = query.filter(Revenue.revenue_type == revenue_type)

            records = query.order_by(Revenue.date.desc()).limit(limit).all()

            # 통계 계산
            total_records = len(records)
            total_amount = sum(record.amount for record in records)
            avg_amount = total_amount / total_records if total_records > 0 else 0

            # 수익 유형별 집계
            type_breakdown = {}
            for record in records:
                if record.revenue_type not in type_breakdown:
                    type_breakdown[record.revenue_type] = {
                        "count": 0,
                        "total": 0,
                        "avg": 0
                    }
                type_breakdown[record.revenue_type]["count"] += 1
                type_breakdown[record.revenue_type]["total"] += record.amount

            # 평균값 계산
            for type_key in type_breakdown:
                count = type_breakdown[type_key]["count"]
                type_breakdown[type_key]["avg"] = round(
                    type_breakdown[type_key]["total"] / count, 2
                ) if count > 0 else 0

            logger.info(f"[Owner] Retrieved {total_records} revenue records")

            return {
                "success": True,
                "count": total_records,
                "total_amount": round(total_amount, 2),
                "average_amount": round(avg_amount, 2),
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "type_breakdown": type_breakdown,
                "records": [
                    {
                        "id": record.id,
                        "date": record.date.isoformat(),
                        "revenue_type": record.revenue_type,
                        "amount": record.amount,
                        "user_id": record.user_id,
                        "trainer_id": record.trainer_id,
                        "payment_method": record.payment_method,
                        "description": record.description
                    }
                    for record in records
                ]
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to get revenue records: {e}")
        return {"success": False, "error": str(e)}


# ==================== Revenue Analysis Tools ====================

async def get_revenue_analysis(
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """매출 분석

    수익 유형, 트레이너, 결제 방법별 분석 제공

    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        상세 분석 데이터
    """
    try:
        with get_db() as db:
            records = db.query(Revenue).filter(
                Revenue.date >= start_date,
                Revenue.date <= end_date
            ).all()

            if not records:
                return {
                    "success": True,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "total_revenue": 0,
                    "record_count": 0,
                    "analysis_by_type": {},
                    "analysis_by_trainer": {},
                    "analysis_by_payment": {}
                }

            # 기본 통계
            total_revenue = sum(record.amount for record in records)
            record_count = len(records)

            # 수익 유형별 분석
            analysis_by_type = {}
            for record in records:
                rtype = record.revenue_type
                if rtype not in analysis_by_type:
                    analysis_by_type[rtype] = {
                        "count": 0,
                        "total": 0,
                        "percentage": 0,
                        "avg_amount": 0
                    }
                analysis_by_type[rtype]["count"] += 1
                analysis_by_type[rtype]["total"] += record.amount

            # 백분율 계산
            for rtype in analysis_by_type:
                analysis_by_type[rtype]["percentage"] = round(
                    (analysis_by_type[rtype]["total"] / total_revenue * 100) if total_revenue > 0 else 0, 2
                )
                analysis_by_type[rtype]["avg_amount"] = round(
                    analysis_by_type[rtype]["total"] / analysis_by_type[rtype]["count"], 2
                )

            # 트레이너별 분석
            analysis_by_trainer = {}
            trainer_records = [r for r in records if r.trainer_id is not None]

            for record in trainer_records:
                trainer_id = record.trainer_id
                if trainer_id not in analysis_by_trainer:
                    analysis_by_trainer[trainer_id] = {
                        "count": 0,
                        "total": 0,
                        "percentage": 0,
                        "avg_amount": 0
                    }
                analysis_by_trainer[trainer_id]["count"] += 1
                analysis_by_trainer[trainer_id]["total"] += record.amount

            # 트레이너별 백분율 계산
            for trainer_id in analysis_by_trainer:
                total_trainer_revenue = sum(r.amount for r in trainer_records)
                analysis_by_trainer[trainer_id]["percentage"] = round(
                    (analysis_by_trainer[trainer_id]["total"] / total_trainer_revenue * 100) if total_trainer_revenue > 0 else 0, 2
                )
                analysis_by_trainer[trainer_id]["avg_amount"] = round(
                    analysis_by_trainer[trainer_id]["total"] / analysis_by_trainer[trainer_id]["count"], 2
                )

            # 결제 방법별 분석
            analysis_by_payment = {}
            for record in records:
                method = record.payment_method
                if method not in analysis_by_payment:
                    analysis_by_payment[method] = {
                        "count": 0,
                        "total": 0,
                        "percentage": 0
                    }
                analysis_by_payment[method]["count"] += 1
                analysis_by_payment[method]["total"] += record.amount

            # 결제 방법별 백분율 계산
            for method in analysis_by_payment:
                analysis_by_payment[method]["percentage"] = round(
                    (analysis_by_payment[method]["total"] / total_revenue * 100) if total_revenue > 0 else 0, 2
                )

            logger.info(f"[Owner] Revenue analysis completed: ${total_revenue} over {record_count} records")

            return {
                "success": True,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_revenue": round(total_revenue, 2),
                "record_count": record_count,
                "average_transaction": round(total_revenue / record_count, 2) if record_count > 0 else 0,
                "analysis_by_type": analysis_by_type,
                "analysis_by_trainer": analysis_by_trainer,
                "analysis_by_payment": analysis_by_payment
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to get revenue analysis: {e}")
        return {"success": False, "error": str(e)}


# ==================== Monthly Revenue Tools ====================

async def calculate_monthly_revenue(
    year: int,
    month: int
) -> Dict[str, Any]:
    """월별 매출 계산

    Args:
        year: 연도
        month: 월 (1-12)

    Returns:
        월별 매출 정보
    """
    try:
        # 월의 첫날과 마지막날 계산
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

        start_date = datetime(year, month, 1)
        end_date = end_date.replace(hour=23, minute=59, second=59)

        # 수익 분석 함수 호출
        analysis_result = await get_revenue_analysis(start_date, end_date)

        if not analysis_result.get("success"):
            return analysis_result

        # 월간 통계 추가 정보
        with get_db() as db:
            records = db.query(Revenue).filter(
                Revenue.date >= start_date,
                Revenue.date <= end_date
            ).all()

            # 일별 매출
            daily_revenue = {}
            for record in records:
                day = record.date.date()
                day_str = day.isoformat()
                if day_str not in daily_revenue:
                    daily_revenue[day_str] = {
                        "total": 0,
                        "count": 0
                    }
                daily_revenue[day_str]["total"] += record.amount
                daily_revenue[day_str]["count"] += 1

            # 평균값 계산
            for day in daily_revenue:
                daily_revenue[day]["total"] = round(daily_revenue[day]["total"], 2)

        logger.info(f"[Owner] Monthly revenue calculated: {year}-{month:02d} = ${analysis_result['total_revenue']}")

        return {
            "success": True,
            "year": year,
            "month": month,
            "total_revenue": analysis_result["total_revenue"],
            "record_count": analysis_result["record_count"],
            "average_transaction": analysis_result["average_transaction"],
            "daily_breakdown": daily_revenue,
            "type_breakdown": analysis_result["analysis_by_type"],
            "payment_breakdown": analysis_result["analysis_by_payment"]
        }
    except Exception as e:
        logger.error(f"[Owner] Failed to calculate monthly revenue: {e}")
        return {"success": False, "error": str(e)}


# ==================== Trainer Performance Tools ====================

async def get_trainer_performance(
    trainer_id: int,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """트레이너 성과 분석

    수익, 세션 수, 평균 수익 포함

    Args:
        trainer_id: 트레이너 ID
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        트레이너 성과 정보
    """
    try:
        with get_db() as db:
            # 트레이너 정보 조회
            trainer = db.query(User).filter(User.id == trainer_id).first()
            if not trainer:
                return {"success": False, "error": f"Trainer with id {trainer_id} not found"}

            # 트레이너가 생성한 수익 기록
            revenue_records = db.query(Revenue).filter(
                Revenue.trainer_id == trainer_id,
                Revenue.date >= start_date,
                Revenue.date <= end_date
            ).all()

            # 트레이너가 진행한 세션 기록
            session_records = db.query(Attendance).filter(
                Attendance.trainer_id == trainer_id,
                Attendance.check_in_time >= start_date,
                Attendance.check_in_time <= end_date,
                Attendance.check_out_time != None
            ).all()

            # 수익 계산
            total_revenue = sum(record.amount for record in revenue_records)
            revenue_count = len(revenue_records)
            avg_revenue_per_session = 0

            # 세션 통계
            session_count = len(session_records)
            total_session_minutes = sum(
                int((session.check_out_time - session.check_in_time).total_seconds() / 60)
                for session in session_records
            )
            avg_session_minutes = total_session_minutes / session_count if session_count > 0 else 0

            # 세션당 평균 수익
            if session_count > 0:
                avg_revenue_per_session = total_revenue / session_count

            # 수익 유형별 분석
            revenue_by_type = {}
            for record in revenue_records:
                rtype = record.revenue_type
                if rtype not in revenue_by_type:
                    revenue_by_type[rtype] = {
                        "count": 0,
                        "total": 0
                    }
                revenue_by_type[rtype]["count"] += 1
                revenue_by_type[rtype]["total"] += record.amount

            # 성능 점수 계산 (Mock intelligent calculation)
            # 점수 = (수익 / 세션) × (세션 시간 / 60) × 100
            performance_score = 0
            if session_count > 0:
                revenue_per_session_factor = min(avg_revenue_per_session / 100, 1.0)  # 세션당 $100을 기준
                session_quality_factor = min(avg_session_minutes / 60, 1.0)  # 60분을 기준
                performance_score = (revenue_per_session_factor + session_quality_factor) / 2 * 100

            logger.info(f"[Owner] Trainer {trainer_id} performance analyzed: ${total_revenue} from {session_count} sessions")

            return {
                "success": True,
                "trainer_id": trainer_id,
                "trainer_name": trainer.name,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_revenue": round(total_revenue, 2),
                "revenue_count": revenue_count,
                "session_count": session_count,
                "total_session_minutes": total_session_minutes,
                "average_session_minutes": round(avg_session_minutes, 1),
                "avg_revenue_per_session": round(avg_revenue_per_session, 2),
                "revenue_by_type": revenue_by_type,
                "performance_score": round(performance_score, 1)
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to get trainer performance: {e}")
        return {"success": False, "error": str(e)}


async def get_all_trainers_performance(
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """모든 트레이너 성과 비교

    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        모든 트레이너의 비교 성과 데이터
    """
    try:
        with get_db() as db:
            # 해당 기간에 수익을 생성한 모든 트레이너 ID 조회
            trainer_ids = db.query(Revenue.trainer_id).filter(
                Revenue.trainer_id != None,
                Revenue.date >= start_date,
                Revenue.date <= end_date
            ).distinct().all()

            trainer_ids = [t[0] for t in trainer_ids]

            if not trainer_ids:
                return {
                    "success": True,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "trainers_count": 0,
                    "trainers": []
                }

            # 각 트레이너의 성과 데이터 수집
            trainers_data = []
            for trainer_id in trainer_ids:
                perf = await get_trainer_performance(trainer_id, start_date, end_date)
                if perf.get("success"):
                    trainers_data.append(perf)

            # 수익 기준 정렬
            trainers_data.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)

            # 총계 계산
            total_revenue_all = sum(t.get("total_revenue", 0) for t in trainers_data)
            total_sessions_all = sum(t.get("session_count", 0) for t in trainers_data)
            avg_performance_score = sum(t.get("performance_score", 0) for t in trainers_data) / len(trainers_data) if trainers_data else 0

            logger.info(f"[Owner] All trainers performance analyzed: {len(trainers_data)} trainers")

            return {
                "success": True,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "trainers_count": len(trainers_data),
                "total_revenue": round(total_revenue_all, 2),
                "total_sessions": total_sessions_all,
                "average_performance_score": round(avg_performance_score, 1),
                "trainers": trainers_data
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to get all trainers performance: {e}")
        return {"success": False, "error": str(e)}


# ==================== Program ROI Tools ====================

async def calculate_program_roi(
    program_type: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """프로그램별 ROI 계산

    수익 vs 예상 비용 기반 계산

    Args:
        program_type: 프로그램 유형 (membership, pt_session, product, event)
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        ROI 분석 데이터
    """
    try:
        with get_db() as db:
            # 해당 프로그램의 수익 기록
            revenue_records = db.query(Revenue).filter(
                Revenue.revenue_type == program_type,
                Revenue.date >= start_date,
                Revenue.date <= end_date
            ).all()

            total_revenue = sum(record.amount for record in revenue_records)
            transaction_count = len(revenue_records)

            # Mock 비용 추정 (실제 구현에서는 별도의 비용 테이블 필요)
            # 프로그램 유형별 예상 비용 계산
            estimated_cost_per_transaction = {
                "membership": 5,  # 관리 비용: $5
                "pt_session": 15,  # 트레이너 비용: 수익의 약 30-50%
                "product": 25,  # 제품 원가: 수익의 약 40%
                "event": 50  # 이벤트 운영 비용: $50
            }

            cost_per_unit = estimated_cost_per_transaction.get(program_type, 0)
            total_estimated_cost = cost_per_unit * transaction_count

            # ROI 계산
            net_profit = total_revenue - total_estimated_cost
            roi_percentage = 0
            if total_estimated_cost > 0:
                roi_percentage = (net_profit / total_estimated_cost) * 100

            # 평균값
            avg_revenue = total_revenue / transaction_count if transaction_count > 0 else 0
            avg_profit = net_profit / transaction_count if transaction_count > 0 else 0

            # ROI 레벨 판정
            if roi_percentage >= 100:
                roi_level = "excellent"
            elif roi_percentage >= 50:
                roi_level = "good"
            elif roi_percentage >= 0:
                roi_level = "positive"
            elif roi_percentage >= -20:
                roi_level = "concerning"
            else:
                roi_level = "critical"

            logger.info(f"[Owner] Program ROI calculated: {program_type} = {roi_percentage:.1f}%")

            return {
                "success": True,
                "program_type": program_type,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_revenue": round(total_revenue, 2),
                "total_estimated_cost": round(total_estimated_cost, 2),
                "net_profit": round(net_profit, 2),
                "roi_percentage": round(roi_percentage, 2),
                "roi_level": roi_level,
                "transaction_count": transaction_count,
                "average_revenue": round(avg_revenue, 2),
                "average_profit": round(avg_profit, 2),
                "cost_per_unit": cost_per_unit
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to calculate program ROI: {e}")
        return {"success": False, "error": str(e)}


# ==================== Key Business Metrics Tools ====================

async def get_key_business_metrics(days: int = 30) -> Dict[str, Any]:
    """핵심 비즈니스 지표 조회

    KPI 데이터 (총 수익, 평균 거래액, 주요 수익원) 집계

    Args:
        days: 기간 (일수)

    Returns:
        KPI 대시보드 데이터
    """
    try:
        with get_db() as db:
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()

            # 기본 수익 통계
            revenue_records = db.query(Revenue).filter(
                Revenue.date >= start_date,
                Revenue.date <= end_date
            ).all()

            total_revenue = sum(record.amount for record in revenue_records)
            transaction_count = len(revenue_records)
            avg_transaction = total_revenue / transaction_count if transaction_count > 0 else 0

            # 수익 유형별 상위 3개
            revenue_by_type = {}
            for record in revenue_records:
                rtype = record.revenue_type
                if rtype not in revenue_by_type:
                    revenue_by_type[rtype] = 0
                revenue_by_type[rtype] += record.amount

            top_revenue_sources = sorted(
                [{"type": k, "amount": v} for k, v in revenue_by_type.items()],
                key=lambda x: x["amount"],
                reverse=True
            )[:3]

            # 결제 방법별 통계
            payment_by_method = {}
            for record in revenue_records:
                method = record.payment_method
                if method not in payment_by_method:
                    payment_by_method[method] = {
                        "count": 0,
                        "total": 0
                    }
                payment_by_method[method]["count"] += 1
                payment_by_method[method]["total"] += record.amount

            # 상위 트레이너 (수익 기준)
            top_trainers_by_revenue = {}
            for record in revenue_records:
                if record.trainer_id:
                    if record.trainer_id not in top_trainers_by_revenue:
                        top_trainers_by_revenue[record.trainer_id] = 0
                    top_trainers_by_revenue[record.trainer_id] += record.amount

            top_trainers = sorted(
                [{"trainer_id": k, "total_revenue": v} for k, v in top_trainers_by_revenue.items()],
                key=lambda x: x["total_revenue"],
                reverse=True
            )[:3]

            # 일일 평균 수익
            daily_revenue = {}
            for record in revenue_records:
                day = record.date.date()
                day_str = day.isoformat()
                if day_str not in daily_revenue:
                    daily_revenue[day_str] = 0
                daily_revenue[day_str] += record.amount

            operating_days = len([d for d in daily_revenue if daily_revenue[d] > 0])
            daily_avg = total_revenue / operating_days if operating_days > 0 else 0

            # 활성 회원 수 (수익 기록이 있는 회원)
            active_members = len(set(record.user_id for record in revenue_records))

            # 성장도 계산 (지난 반기간과 비교)
            mid_date = start_date + timedelta(days=days // 2)
            first_half = sum(r.amount for r in revenue_records if r.date < mid_date)
            second_half = total_revenue - first_half

            growth_percentage = 0
            if first_half > 0:
                growth_percentage = ((second_half - first_half) / first_half) * 100

            logger.info(f"[Owner] Key business metrics calculated: ${total_revenue} over {days} days")

            return {
                "success": True,
                "period_days": days,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_revenue": round(total_revenue, 2),
                "transaction_count": transaction_count,
                "average_transaction": round(avg_transaction, 2),
                "daily_average_revenue": round(daily_avg, 2),
                "operating_days": operating_days,
                "active_members": active_members,
                "growth_percentage": round(growth_percentage, 2),
                "top_revenue_sources": [
                    {
                        "type": item["type"],
                        "amount": round(item["amount"], 2),
                        "percentage": round((item["amount"] / total_revenue * 100) if total_revenue > 0 else 0, 2)
                    }
                    for item in top_revenue_sources
                ],
                "payment_methods": {
                    method: {
                        "count": payment_by_method[method]["count"],
                        "total": round(payment_by_method[method]["total"], 2),
                        "percentage": round((payment_by_method[method]["total"] / total_revenue * 100) if total_revenue > 0 else 0, 2)
                    }
                    for method in payment_by_method
                },
                "top_trainers": [
                    {
                        "trainer_id": trainer["trainer_id"],
                        "total_revenue": round(trainer["total_revenue"], 2)
                    }
                    for trainer in top_trainers
                ]
            }
    except Exception as e:
        logger.error(f"[Owner] Failed to get key business metrics: {e}")
        return {"success": False, "error": str(e)}


__all__ = [
    "record_revenue",
    "get_revenue_records",
    "get_revenue_analysis",
    "calculate_monthly_revenue",
    "get_trainer_performance",
    "get_all_trainers_performance",
    "calculate_program_roi",
    "get_key_business_metrics",
]
