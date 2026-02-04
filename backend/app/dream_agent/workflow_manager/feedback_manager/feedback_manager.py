"""Feedback Manager - RLHF 훈련 데이터 수집 관리자"""

import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.postgre_db import AsyncSessionLocal
from backend.app.models.feedback import (
    UserInteractionLog,
    PlanFeedback,
    RLHFFeedback,
    RLHFTrainingExport
)
from backend.app.schemas.feedback import (
    UserInteractionLogCreate,
    UserInteractionLogUpdate,
    PlanFeedbackCreate,
    RLHFFeedbackCreate,
    RLHFTrainingExportCreate,
    PlanAction,
    RLHFRating,
    FeedbackAnalytics,
    TrainingDataRecord
)
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class FeedbackManager:
    """
    사용자 피드백 및 상호작용 데이터 수집 관리자

    RLHF 훈련 데이터 수집을 위한 핵심 매니저:
    - 사용자 입력 쿼리 자동 로깅
    - 계획서 피드백 (approve/modify/reject) 저장
    - RLHF 피드백 (thumbs up/down) 저장
    - 훈련 데이터 내보내기
    """

    def __init__(self):
        """초기화"""
        # In-memory cache for active sessions
        self._active_logs: Dict[str, uuid.UUID] = {}  # session_id -> log_id

    # ============================================================
    # User Interaction Logging
    # ============================================================

    async def log_user_interaction(
        self,
        session_id: str,
        user_id: int,
        user_input: str,
        language: str = "KOR",
        input_tokens: Optional[int] = None,
        client_info: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        """
        사용자 입력 쿼리 로깅

        Args:
            session_id: Session ID
            user_id: User ID
            user_input: 사용자 입력 텍스트
            language: 언어 코드 (KOR, EN, JP)
            input_tokens: 입력 토큰 수
            client_info: 클라이언트 정보

        Returns:
            log_id: 생성된 로그 ID
        """
        async with AsyncSessionLocal() as session:
            try:
                log = UserInteractionLog(
                    session_id=uuid.UUID(session_id),
                    user_id=user_id,
                    user_input=user_input,
                    language=language,
                    input_tokens=input_tokens,
                    client_info=client_info
                )

                session.add(log)
                await session.commit()
                await session.refresh(log)

                # Cache for later context updates
                self._active_logs[session_id] = log.log_id

                logger.info(
                    f"User interaction logged: session={session_id}, "
                    f"log_id={log.log_id}, input_length={len(user_input)}"
                )

                return log.log_id

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to log user interaction: {e}", exc_info=True)
                raise

    async def update_interaction_context(
        self,
        log_id: uuid.UUID,
        intent_detected: Optional[Dict[str, Any]] = None,
        plan_generated: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Interaction 로그에 컨텍스트 업데이트

        Cognitive/Planning 레이어 완료 후 호출

        Args:
            log_id: 로그 ID
            intent_detected: 인텐트 분석 결과
            plan_generated: 생성된 계획서

        Returns:
            성공 여부
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(UserInteractionLog).where(
                        UserInteractionLog.log_id == log_id
                    )
                )
                log = result.scalar_one_or_none()

                if not log:
                    logger.warning(f"Interaction log not found: {log_id}")
                    return False

                if intent_detected is not None:
                    log.intent_detected = intent_detected
                if plan_generated is not None:
                    log.plan_generated = plan_generated

                await session.commit()

                logger.debug(
                    f"Interaction context updated: log_id={log_id}, "
                    f"has_intent={intent_detected is not None}, "
                    f"has_plan={plan_generated is not None}"
                )

                return True

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update interaction context: {e}", exc_info=True)
                return False

    async def get_current_log_id(self, session_id: str) -> Optional[uuid.UUID]:
        """현재 세션의 활성 로그 ID 조회"""
        return self._active_logs.get(session_id)

    # ============================================================
    # Plan Feedback
    # ============================================================

    async def record_plan_feedback(
        self,
        session_id: str,
        user_id: int,
        plan_id: str,
        plan_snapshot: Dict[str, Any],
        action: str,
        reason: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None,
        original_todos: Optional[List[Dict[str, Any]]] = None,
        modified_todos: Optional[List[Dict[str, Any]]] = None,
        time_to_decision: Optional[int] = None
    ) -> uuid.UUID:
        """
        계획서 피드백 저장

        Args:
            session_id: Session ID
            user_id: User ID
            plan_id: Plan ID
            plan_snapshot: 계획서 스냅샷
            action: "approved" | "modified" | "rejected"
            reason: 피드백 사유
            modifications: 수정 내용
            original_todos: 원본 todos
            modified_todos: 수정된 todos
            time_to_decision: 결정까지 소요 시간(초)

        Returns:
            feedback_id: 생성된 피드백 ID
        """
        async with AsyncSessionLocal() as session:
            try:
                # 연결된 interaction log 찾기
                log_id = self._active_logs.get(session_id)

                if not log_id:
                    # 가장 최근 로그 조회
                    result = await session.execute(
                        select(UserInteractionLog)
                        .where(UserInteractionLog.session_id == uuid.UUID(session_id))
                        .order_by(UserInteractionLog.timestamp.desc())
                        .limit(1)
                    )
                    log = result.scalar_one_or_none()
                    log_id = log.log_id if log else None

                if not log_id:
                    logger.warning(
                        f"No interaction log found for session {session_id}, "
                        "creating orphan feedback"
                    )
                    log_id = uuid.uuid4()

                feedback = PlanFeedback(
                    log_id=log_id,
                    session_id=uuid.UUID(session_id),
                    user_id=user_id,
                    plan_id=plan_id,
                    plan_snapshot=plan_snapshot,
                    action=action,
                    reason=reason,
                    modifications=modifications,
                    original_todos=original_todos,
                    modified_todos=modified_todos,
                    time_to_decision=time_to_decision
                )

                session.add(feedback)
                await session.commit()
                await session.refresh(feedback)

                logger.info(
                    f"Plan feedback recorded: session={session_id}, "
                    f"plan={plan_id}, action={action}"
                )

                return feedback.feedback_id

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to record plan feedback: {e}", exc_info=True)
                raise

    # ============================================================
    # RLHF Feedback
    # ============================================================

    async def record_rlhf_feedback(
        self,
        session_id: str,
        user_id: int,
        response_id: str,
        response_type: str,
        response_snapshot: Dict[str, Any],
        rating: str,
        reason: Optional[str] = None,
        aspects: Optional[Dict[str, int]] = None,
        selected_improvements: Optional[List[str]] = None
    ) -> uuid.UUID:
        """
        RLHF 피드백 저장

        Args:
            session_id: Session ID
            user_id: User ID
            response_id: Response ID
            response_type: "plan" | "ml_result" | "biz_result" | "final_response"
            response_snapshot: 응답 스냅샷
            rating: "thumbs_up" | "thumbs_down" | "neutral"
            reason: 피드백 사유
            aspects: 세부 평가 {"accuracy": 5, "helpfulness": 4, ...}
            selected_improvements: ["more_detail", "faster", ...]

        Returns:
            feedback_id: 생성된 피드백 ID
        """
        async with AsyncSessionLocal() as session:
            try:
                # 연결된 interaction log 찾기
                log_id = self._active_logs.get(session_id)

                if not log_id:
                    result = await session.execute(
                        select(UserInteractionLog)
                        .where(UserInteractionLog.session_id == uuid.UUID(session_id))
                        .order_by(UserInteractionLog.timestamp.desc())
                        .limit(1)
                    )
                    log = result.scalar_one_or_none()
                    log_id = log.log_id if log else None

                if not log_id:
                    logger.warning(
                        f"No interaction log found for session {session_id}, "
                        "creating orphan feedback"
                    )
                    log_id = uuid.uuid4()

                feedback = RLHFFeedback(
                    log_id=log_id,
                    session_id=uuid.UUID(session_id),
                    user_id=user_id,
                    response_id=response_id,
                    response_type=response_type,
                    response_snapshot=response_snapshot,
                    rating=rating,
                    reason=reason,
                    aspects=aspects,
                    selected_improvements=selected_improvements
                )

                session.add(feedback)
                await session.commit()
                await session.refresh(feedback)

                logger.info(
                    f"RLHF feedback recorded: session={session_id}, "
                    f"response={response_id}, rating={rating}"
                )

                return feedback.feedback_id

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to record RLHF feedback: {e}", exc_info=True)
                raise

    # ============================================================
    # Analytics & Export
    # ============================================================

    async def get_analytics(
        self,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None
    ) -> FeedbackAnalytics:
        """
        피드백 통계 조회

        Args:
            date_start: 시작일
            date_end: 종료일

        Returns:
            FeedbackAnalytics 객체
        """
        async with AsyncSessionLocal() as session:
            try:
                # Base filters
                interaction_filters = []
                plan_filters = []
                rlhf_filters = []

                if date_start:
                    interaction_filters.append(UserInteractionLog.timestamp >= date_start)
                    plan_filters.append(PlanFeedback.created_at >= date_start)
                    rlhf_filters.append(RLHFFeedback.created_at >= date_start)

                if date_end:
                    interaction_filters.append(UserInteractionLog.timestamp <= date_end)
                    plan_filters.append(PlanFeedback.created_at <= date_end)
                    rlhf_filters.append(RLHFFeedback.created_at <= date_end)

                # Total counts
                interaction_count = await session.execute(
                    select(func.count(UserInteractionLog.log_id))
                    .where(and_(*interaction_filters) if interaction_filters else True)
                )
                total_interactions = interaction_count.scalar() or 0

                plan_count = await session.execute(
                    select(func.count(PlanFeedback.feedback_id))
                    .where(and_(*plan_filters) if plan_filters else True)
                )
                total_plan_feedbacks = plan_count.scalar() or 0

                rlhf_count = await session.execute(
                    select(func.count(RLHFFeedback.feedback_id))
                    .where(and_(*rlhf_filters) if rlhf_filters else True)
                )
                total_rlhf_feedbacks = rlhf_count.scalar() or 0

                # Plan action distribution
                plan_dist = await session.execute(
                    select(PlanFeedback.action, func.count(PlanFeedback.feedback_id))
                    .where(and_(*plan_filters) if plan_filters else True)
                    .group_by(PlanFeedback.action)
                )
                plan_action_distribution = {row[0]: row[1] for row in plan_dist.all()}

                # RLHF rating distribution
                rlhf_dist = await session.execute(
                    select(RLHFFeedback.rating, func.count(RLHFFeedback.feedback_id))
                    .where(and_(*rlhf_filters) if rlhf_filters else True)
                    .group_by(RLHFFeedback.rating)
                )
                rlhf_rating_distribution = {row[0]: row[1] for row in rlhf_dist.all()}

                # Average time to decision
                avg_time = await session.execute(
                    select(func.avg(PlanFeedback.time_to_decision))
                    .where(
                        and_(
                            PlanFeedback.time_to_decision.isnot(None),
                            *plan_filters
                        ) if plan_filters else PlanFeedback.time_to_decision.isnot(None)
                    )
                )
                avg_time_to_decision = avg_time.scalar()

                return FeedbackAnalytics(
                    total_interactions=total_interactions,
                    total_plan_feedbacks=total_plan_feedbacks,
                    total_rlhf_feedbacks=total_rlhf_feedbacks,
                    plan_action_distribution=plan_action_distribution,
                    rlhf_rating_distribution=rlhf_rating_distribution,
                    avg_time_to_decision=float(avg_time_to_decision) if avg_time_to_decision else None,
                    date_range={
                        "start": date_start,
                        "end": date_end
                    } if date_start or date_end else None
                )

            except Exception as e:
                logger.error(f"Failed to get analytics: {e}", exc_info=True)
                raise

    async def export_training_data(
        self,
        export_name: str,
        export_type: str = "full",
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
        created_by: Optional[int] = None,
        output_path: Optional[str] = None
    ) -> uuid.UUID:
        """
        RLHF 훈련 데이터 내보내기

        Args:
            export_name: 내보내기 이름
            export_type: "full" | "plan_only" | "rlhf_only"
            date_start: 시작일
            date_end: 종료일
            created_by: 생성자 ID
            output_path: 출력 경로 (없으면 자동 생성)

        Returns:
            export_id: 내보내기 ID
        """
        async with AsyncSessionLocal() as session:
            try:
                # Create export record
                export = RLHFTrainingExport(
                    export_name=export_name,
                    export_type=export_type,
                    date_range_start=date_start,
                    date_range_end=date_end,
                    created_by=created_by,
                    status="processing"
                )

                session.add(export)
                await session.commit()
                await session.refresh(export)

                export_id = export.export_id

                # Build filters
                filters = []
                if date_start:
                    filters.append(UserInteractionLog.timestamp >= date_start)
                if date_end:
                    filters.append(UserInteractionLog.timestamp <= date_end)

                # Query interactions with feedbacks
                result = await session.execute(
                    select(UserInteractionLog)
                    .where(and_(*filters) if filters else True)
                    .order_by(UserInteractionLog.timestamp)
                )
                interactions = result.scalars().all()

                # Prepare output
                if not output_path:
                    output_dir = Path(__file__).parent.parent.parent.parent.parent / "data/exports"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = str(output_dir / f"training_data_{timestamp}.jsonl")

                records = []
                for interaction in interactions:
                    # Get related feedbacks
                    plan_feedbacks = await session.execute(
                        select(PlanFeedback)
                        .where(PlanFeedback.log_id == interaction.log_id)
                    )
                    rlhf_feedbacks = await session.execute(
                        select(RLHFFeedback)
                        .where(RLHFFeedback.log_id == interaction.log_id)
                    )

                    plan_fb_list = plan_feedbacks.scalars().all()
                    rlhf_fb_list = rlhf_feedbacks.scalars().all()

                    # Skip based on export_type
                    if export_type == "plan_only" and not plan_fb_list:
                        continue
                    if export_type == "rlhf_only" and not rlhf_fb_list:
                        continue

                    # Create training record
                    for rlhf_fb in rlhf_fb_list:
                        record = TrainingDataRecord(
                            user_input=interaction.user_input,
                            language=interaction.language,
                            intent=interaction.intent_detected,
                            plan=interaction.plan_generated,
                            response=rlhf_fb.response_snapshot,
                            rating=rlhf_fb.rating,
                            reason=rlhf_fb.reason,
                            aspects=rlhf_fb.aspects,
                            timestamp=interaction.timestamp
                        )
                        records.append(record)

                    # Include plan feedback if no RLHF feedback
                    if not rlhf_fb_list and plan_fb_list:
                        for plan_fb in plan_fb_list:
                            record = TrainingDataRecord(
                                user_input=interaction.user_input,
                                language=interaction.language,
                                intent=interaction.intent_detected,
                                plan=interaction.plan_generated,
                                response=plan_fb.plan_snapshot,
                                plan_action=plan_fb.action,
                                plan_modifications=plan_fb.modifications,
                                timestamp=interaction.timestamp
                            )
                            records.append(record)

                # Write JSONL
                with open(output_path, 'w', encoding='utf-8') as f:
                    for record in records:
                        f.write(record.model_dump_json() + '\n')

                # Update export record
                export.total_records = len(records)
                export.export_path = output_path
                export.status = "completed"
                export.stats = {
                    "total_interactions": len(interactions),
                    "total_records": len(records),
                    "export_type": export_type
                }

                await session.commit()

                logger.info(
                    f"Training data exported: export_id={export_id}, "
                    f"records={len(records)}, path={output_path}"
                )

                return export_id

            except Exception as e:
                # Mark as failed
                if 'export' in locals():
                    export.status = "failed"
                    await session.commit()

                await session.rollback()
                logger.error(f"Failed to export training data: {e}", exc_info=True)
                raise

    # ============================================================
    # Session Cleanup
    # ============================================================

    def cleanup_session(self, session_id: str):
        """세션 정리 (메모리 캐시만)"""
        if session_id in self._active_logs:
            del self._active_logs[session_id]
            logger.debug(f"Feedback session cache cleaned: {session_id}")


# Global instance (Singleton)
feedback_manager = FeedbackManager()
