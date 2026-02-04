"""Feedback Manager - 사용자 피드백 수집 및 학습

Phase 3: Feedback 구조 구현
- QueryLogger: 질의 및 의도 분석 로깅
- PlanEditLogger: 계획 편집 내역 로깅
- ResultEvaluator: 실행 결과 평가 수집

기존 FeedbackManager: DB 기반 RLHF 피드백 관리
신규 Loggers: 경량 학습 데이터 수집용 (메모리/파일)
"""

# 기존 DB 기반 FeedbackManager
from .feedback_manager import FeedbackManager, feedback_manager

# Phase 3: 경량 학습 데이터 Loggers
from .query_logger import (
    QueryLogger,
    QueryLogEntry,
    get_query_logger,
    reset_query_logger,
)
from .plan_edit_logger import (
    PlanEditLogger,
    PlanEditLogEntry,
    get_plan_edit_logger,
    reset_plan_edit_logger,
)
from .result_evaluator import (
    ResultEvaluator,
    ResultEvaluation,
    EvaluationRating,
    EvaluationType,
    get_result_evaluator,
    reset_result_evaluator,
)

__all__ = [
    # 기존 DB 기반
    "FeedbackManager",
    "feedback_manager",
    # Phase 3: Query Logger
    "QueryLogger",
    "QueryLogEntry",
    "get_query_logger",
    "reset_query_logger",
    # Phase 3: Plan Edit Logger
    "PlanEditLogger",
    "PlanEditLogEntry",
    "get_plan_edit_logger",
    "reset_plan_edit_logger",
    # Phase 3: Result Evaluator
    "ResultEvaluator",
    "ResultEvaluation",
    "EvaluationRating",
    "EvaluationType",
    "get_result_evaluator",
    "reset_result_evaluator",
    # Phase 3: Unified Manager
    "LightweightFeedbackManager",
    "get_lightweight_feedback_manager",
]


class LightweightFeedbackManager:
    """
    경량 학습 데이터 수집용 통합 Feedback 관리자

    DB 연결 없이 메모리 기반으로 학습 데이터를 수집합니다.
    수집된 데이터는 export_all()로 내보내 학습에 활용할 수 있습니다.
    """

    def __init__(self, storage_backend: str = "memory"):
        """
        Args:
            storage_backend: 저장 백엔드 ("memory", "file", "database")
        """
        self.query_logger = QueryLogger(storage_backend)
        self.plan_edit_logger = PlanEditLogger(storage_backend)
        self.result_evaluator = ResultEvaluator(storage_backend)
        self._storage = storage_backend

    async def export_all(self) -> dict:
        """
        전체 학습 데이터 내보내기

        Returns:
            {
                "queries": [...],
                "plan_edits": [...],
                "evaluations": [...],
            }
        """
        return {
            "queries": await self.query_logger.export_for_training(),
            "plan_edits": await self.plan_edit_logger.export_for_training(),
            "evaluations": await self.result_evaluator.export_for_training(),
        }

    async def get_summary(self) -> dict:
        """
        수집 현황 요약

        Returns:
            각 로거의 요약 정보
        """
        return {
            "storage_backend": self._storage,
            "query_logger": self.query_logger.get_summary(),
            "plan_edit_logger": self.plan_edit_logger.get_summary(),
            "result_evaluator": self.result_evaluator.get_summary(),
        }

    async def get_training_stats(self) -> dict:
        """
        학습 데이터 통계

        Returns:
            수집 데이터 통계
        """
        query_summary = self.query_logger.get_summary()
        plan_edit_summary = self.plan_edit_logger.get_summary()
        evaluator_summary = self.result_evaluator.get_summary()

        return {
            "total_queries": query_summary.get("total_queries", 0),
            "total_plan_edits": plan_edit_summary.get("total_edits", 0),
            "total_evaluations": evaluator_summary.get("total_evaluations", 0),
            "ready_for_training": (
                query_summary.get("total_queries", 0) >= 100 or
                plan_edit_summary.get("total_edits", 0) >= 50 or
                evaluator_summary.get("total_evaluations", 0) >= 50
            ),
        }


# Global instance
_lightweight_manager: LightweightFeedbackManager = None


def get_lightweight_feedback_manager(
    storage_backend: str = "memory"
) -> LightweightFeedbackManager:
    """
    전역 LightweightFeedbackManager 인스턴스 반환

    Args:
        storage_backend: 저장 백엔드

    Returns:
        LightweightFeedbackManager 인스턴스
    """
    global _lightweight_manager
    if _lightweight_manager is None:
        _lightweight_manager = LightweightFeedbackManager(storage_backend)
    return _lightweight_manager
