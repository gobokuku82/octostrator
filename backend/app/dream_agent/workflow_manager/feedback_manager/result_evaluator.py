"""Result Evaluator - 실행 결과에 대한 평가 수집

실행 결과에 대한 사용자/시스템 평가를 수집하여
Agent 품질 개선에 활용합니다.

수집 데이터:
- user_rating (1-5)
- user_feedback (텍스트)
- result_quality_metrics
- execution_time
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import logging
import uuid

logger = logging.getLogger(__name__)


class EvaluationRating(int, Enum):
    """평가 등급"""
    EXCELLENT = 5
    GOOD = 4
    ACCEPTABLE = 3
    POOR = 2
    UNACCEPTABLE = 1


class EvaluationType(str, Enum):
    """평가 유형"""
    USER = "user"          # 사용자 평가
    SYSTEM = "system"      # 시스템 자동 평가
    AUTOMATED = "automated"  # 자동화 품질 체크


@dataclass
class ResultEvaluation:
    """결과 평가"""
    id: str
    session_id: str
    timestamp: datetime

    # 평가 대상
    todo_id: str
    agent_name: str
    result: Dict[str, Any]

    # 평가 내용
    rating: int  # 1-5
    evaluation_type: str = "user"
    feedback_text: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # 세부 평가 (선택적)
    aspects: Dict[str, int] = field(default_factory=dict)
    # e.g., {"accuracy": 5, "completeness": 4, "relevance": 5}

    # 자동 품질 지표
    execution_time_ms: int = 0
    retry_count: int = 0
    error_occurred: bool = False
    output_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "todo_id": self.todo_id,
            "agent_name": self.agent_name,
            "result": self.result,
            "rating": self.rating,
            "evaluation_type": self.evaluation_type,
            "feedback_text": self.feedback_text,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "aspects": self.aspects,
            "execution_time_ms": self.execution_time_ms,
            "retry_count": self.retry_count,
            "error_occurred": self.error_occurred,
            "output_size": self.output_size,
        }


class ResultEvaluator:
    """
    결과 평가기

    실행 결과에 대한 평가를 수집하여
    Agent 품질 개선 데이터로 활용합니다.
    """

    def __init__(self, storage_backend: str = "memory"):
        """
        Args:
            storage_backend: 저장 백엔드 ("memory", "file", "database")
        """
        self._storage = storage_backend
        self._evaluations: List[ResultEvaluation] = []
        self._created_at = datetime.now()

    async def submit_evaluation(
        self,
        session_id: str,
        todo_id: str,
        agent_name: str,
        result: Dict[str, Any],
        rating: int,
        evaluation_type: str = "user",
        feedback_text: Optional[str] = None,
        issues: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
        aspects: Optional[Dict[str, int]] = None,
        execution_time_ms: int = 0,
        retry_count: int = 0,
        error_occurred: bool = False,
        output_size: int = 0
    ) -> str:
        """
        평가 제출

        Args:
            session_id: 세션 ID
            todo_id: Todo ID
            agent_name: Agent 이름
            result: 실행 결과
            rating: 평가 등급 (1-5)
            evaluation_type: 평가 유형
            feedback_text: 피드백 텍스트
            issues: 발견된 이슈
            suggestions: 개선 제안
            aspects: 세부 평가
            execution_time_ms: 실행 시간 (ms)
            retry_count: 재시도 횟수
            error_occurred: 에러 발생 여부
            output_size: 출력 크기

        Returns:
            평가 ID
        """
        # 등급 범위 검증
        rating = max(1, min(5, rating))

        evaluation = ResultEvaluation(
            id=f"eval_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            timestamp=datetime.now(),
            todo_id=todo_id,
            agent_name=agent_name,
            result=result,
            rating=rating,
            evaluation_type=evaluation_type,
            feedback_text=feedback_text,
            issues=issues or [],
            suggestions=suggestions or [],
            aspects=aspects or {},
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            error_occurred=error_occurred,
            output_size=output_size,
        )

        await self._store(evaluation)
        logger.debug(f"[ResultEvaluator] Evaluation submitted: {evaluation.id}")

        return evaluation.id

    async def _store(self, evaluation: ResultEvaluation) -> None:
        """저장"""
        if self._storage == "memory":
            self._evaluations.append(evaluation)
        # TODO: file, database 백엔드 구현

    async def get_evaluations(
        self,
        agent_name: Optional[str] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        evaluation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[ResultEvaluation]:
        """
        평가 조회

        Args:
            agent_name: Agent 이름 필터
            min_rating: 최소 등급 필터
            max_rating: 최대 등급 필터
            evaluation_type: 평가 유형 필터
            limit: 최대 개수

        Returns:
            평가 목록
        """
        evaluations = self._evaluations

        if agent_name:
            evaluations = [e for e in evaluations if e.agent_name == agent_name]

        if min_rating:
            evaluations = [e for e in evaluations if e.rating >= min_rating]

        if max_rating:
            evaluations = [e for e in evaluations if e.rating <= max_rating]

        if evaluation_type:
            evaluations = [e for e in evaluations if e.evaluation_type == evaluation_type]

        return evaluations[-limit:]

    async def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """
        Agent별 통계

        Args:
            agent_name: Agent 이름

        Returns:
            통계 딕셔너리
        """
        agent_evals = [e for e in self._evaluations if e.agent_name == agent_name]

        if not agent_evals:
            return {"agent_name": agent_name, "evaluation_count": 0}

        ratings = [e.rating for e in agent_evals]
        error_count = sum(1 for e in agent_evals if e.error_occurred)
        avg_execution_time = sum(e.execution_time_ms for e in agent_evals) / len(agent_evals)

        return {
            "agent_name": agent_name,
            "evaluation_count": len(agent_evals),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "min_rating": min(ratings),
            "max_rating": max(ratings),
            "rating_distribution": self._get_rating_distribution(agent_evals),
            "error_rate": round(error_count / len(agent_evals), 3),
            "avg_execution_time_ms": round(avg_execution_time, 2),
            "common_issues": self._get_common_issues(agent_evals),
        }

    def _get_rating_distribution(
        self,
        evaluations: List[ResultEvaluation]
    ) -> Dict[int, int]:
        """등급 분포"""
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for e in evaluations:
            distribution[e.rating] = distribution.get(e.rating, 0) + 1
        return distribution

    def _get_common_issues(
        self,
        evaluations: List[ResultEvaluation],
        top_n: int = 5
    ) -> List[tuple]:
        """자주 발생하는 이슈"""
        issue_count: Dict[str, int] = {}
        for e in evaluations:
            for issue in e.issues:
                issue_count[issue] = issue_count.get(issue, 0) + 1

        return sorted(
            issue_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

    async def export_for_training(self) -> List[Dict[str, Any]]:
        """
        학습 데이터 형식으로 내보내기

        Returns:
            학습 데이터 목록

        Format:
            {
                "agent": agent_name,
                "input": result,
                "rating": rating,
                "feedback": feedback_text,
                "issues": issues,
            }
        """
        return [
            {
                "agent": e.agent_name,
                "todo_id": e.todo_id,
                "input": e.result,
                "rating": e.rating,
                "feedback": e.feedback_text,
                "issues": e.issues,
                "suggestions": e.suggestions,
                "aspects": e.aspects,
                "metrics": {
                    "execution_time_ms": e.execution_time_ms,
                    "retry_count": e.retry_count,
                    "error_occurred": e.error_occurred,
                },
            }
            for e in self._evaluations
        ]

    async def get_satisfaction_stats(self) -> Dict[str, Any]:
        """
        전체 만족도 통계

        Returns:
            만족도 통계 딕셔너리
        """
        if not self._evaluations:
            return {
                "total_evaluations": 0,
                "satisfaction_rate": 0.0,
            }

        ratings = [e.rating for e in self._evaluations]
        satisfied = sum(1 for r in ratings if r >= 4)  # 4-5를 만족으로 간주

        # Agent별 평균 평점
        agent_ratings: Dict[str, List[int]] = {}
        for e in self._evaluations:
            if e.agent_name not in agent_ratings:
                agent_ratings[e.agent_name] = []
            agent_ratings[e.agent_name].append(e.rating)

        agent_averages = {
            name: round(sum(r) / len(r), 2)
            for name, r in agent_ratings.items()
        }

        return {
            "total_evaluations": len(self._evaluations),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "satisfaction_rate": round(satisfied / len(self._evaluations), 3),
            "rating_distribution": self._get_rating_distribution(self._evaluations),
            "agent_averages": agent_averages,
        }

    async def get_low_rated_results(
        self,
        threshold: int = 2
    ) -> List[ResultEvaluation]:
        """
        낮은 평가 결과 조회 (재검토 필요)

        Args:
            threshold: 등급 임계값

        Returns:
            평가 목록
        """
        return [
            e for e in self._evaluations
            if e.rating <= threshold
        ]

    def get_summary(self) -> Dict[str, Any]:
        """
        평가기 요약 정보

        Returns:
            요약 딕셔너리
        """
        if not self._evaluations:
            return {
                "storage": self._storage,
                "created_at": self._created_at.isoformat(),
                "total_evaluations": 0,
            }

        ratings = [e.rating for e in self._evaluations]
        agents = set(e.agent_name for e in self._evaluations)

        return {
            "storage": self._storage,
            "created_at": self._created_at.isoformat(),
            "total_evaluations": len(self._evaluations),
            "unique_agents": len(agents),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "error_count": sum(1 for e in self._evaluations if e.error_occurred),
        }


# ============================================================
# Global Instance
# ============================================================

_result_evaluator: Optional[ResultEvaluator] = None


def get_result_evaluator(storage_backend: str = "memory") -> ResultEvaluator:
    """
    전역 ResultEvaluator 인스턴스 반환

    Args:
        storage_backend: 저장 백엔드

    Returns:
        ResultEvaluator 인스턴스
    """
    global _result_evaluator
    if _result_evaluator is None:
        _result_evaluator = ResultEvaluator(storage_backend)
    return _result_evaluator


def reset_result_evaluator() -> None:
    """ResultEvaluator 초기화 (테스트용)"""
    global _result_evaluator
    _result_evaluator = None
