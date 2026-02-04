"""Query Logger - 사용자 질의 및 의도 분석 결과 로깅

사용자 질의를 로깅하여 Intent 모델 학습에 활용합니다.

수집 데이터:
- user_input (원본)
- typo_corrected (오타 수정본)
- detected_intent
- detected_nuances
- processing_time_ms
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class QueryLogEntry:
    """질의 로그 엔트리"""
    id: str
    session_id: str
    timestamp: datetime

    # 입력
    user_input: str
    language: str
    typo_corrected: Optional[str] = None

    # 분석 결과
    intent: Dict[str, Any] = field(default_factory=dict)
    intent_confidence: float = 0.0
    nuances: List[str] = field(default_factory=list)

    # 메타데이터
    processing_time_ms: int = 0
    model_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "language": self.language,
            "typo_corrected": self.typo_corrected,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "nuances": self.nuances,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
        }


class QueryLogger:
    """
    질의 로거

    사용자 질의와 의도 분석 결과를 로깅하여
    Intent 모델 학습 데이터로 활용합니다.
    """

    def __init__(self, storage_backend: str = "memory"):
        """
        Args:
            storage_backend: 저장 백엔드 ("memory", "file", "database")
        """
        self._storage = storage_backend
        self._entries: List[QueryLogEntry] = []
        self._created_at = datetime.now()

    async def log(
        self,
        session_id: str,
        user_input: str,
        language: str,
        intent: Dict[str, Any],
        typo_corrected: Optional[str] = None,
        intent_confidence: float = 0.0,
        nuances: Optional[List[str]] = None,
        processing_time_ms: int = 0,
        model_used: str = ""
    ) -> str:
        """
        질의 로깅

        Args:
            session_id: 세션 ID
            user_input: 사용자 입력
            language: 언어 코드
            intent: 의도 분석 결과
            typo_corrected: 오타 수정된 입력
            intent_confidence: 의도 신뢰도
            nuances: 감지된 뉘앙스
            processing_time_ms: 처리 시간 (ms)
            model_used: 사용된 모델명

        Returns:
            로그 엔트리 ID
        """
        entry = QueryLogEntry(
            id=f"query_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            timestamp=datetime.now(),
            user_input=user_input,
            language=language,
            typo_corrected=typo_corrected,
            intent=intent,
            intent_confidence=intent_confidence,
            nuances=nuances or [],
            processing_time_ms=processing_time_ms,
            model_used=model_used,
        )

        await self._store(entry)
        logger.debug(f"[QueryLogger] Query logged: {entry.id}")

        return entry.id

    async def _store(self, entry: QueryLogEntry) -> None:
        """저장"""
        if self._storage == "memory":
            self._entries.append(entry)
        # TODO: file, database 백엔드 구현

    async def get_entries(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[QueryLogEntry]:
        """
        로그 조회

        Args:
            session_id: 세션 ID (없으면 전체)
            limit: 최대 개수

        Returns:
            로그 엔트리 목록
        """
        entries = self._entries
        if session_id:
            entries = [e for e in entries if e.session_id == session_id]
        return entries[-limit:]

    async def export_for_training(self) -> List[Dict[str, Any]]:
        """
        학습 데이터 형식으로 내보내기

        Returns:
            학습 데이터 목록

        Format:
            {
                "input": user_input,
                "output": intent,
                "confidence": intent_confidence,
                "nuances": nuances,
            }
        """
        return [
            {
                "input": e.user_input,
                "typo_corrected": e.typo_corrected,
                "output": e.intent,
                "confidence": e.intent_confidence,
                "nuances": e.nuances,
                "language": e.language,
            }
            for e in self._entries
        ]

    async def get_by_intent_type(self, intent_type: str) -> List[QueryLogEntry]:
        """
        특정 의도 유형의 로그 조회

        Args:
            intent_type: 의도 유형

        Returns:
            로그 엔트리 목록
        """
        return [
            e for e in self._entries
            if e.intent.get("type") == intent_type
        ]

    async def get_low_confidence_queries(
        self,
        threshold: float = 0.7
    ) -> List[QueryLogEntry]:
        """
        낮은 신뢰도 질의 조회 (재검토 필요)

        Args:
            threshold: 신뢰도 임계값

        Returns:
            로그 엔트리 목록
        """
        return [
            e for e in self._entries
            if e.intent_confidence < threshold
        ]

    def get_summary(self) -> Dict[str, Any]:
        """
        로거 요약 정보

        Returns:
            요약 딕셔너리
        """
        if not self._entries:
            return {
                "storage": self._storage,
                "created_at": self._created_at.isoformat(),
                "total_queries": 0,
            }

        intent_types = {}
        languages = {}
        avg_confidence = 0.0

        for entry in self._entries:
            # 의도 유형 집계
            intent_type = entry.intent.get("type", "unknown")
            intent_types[intent_type] = intent_types.get(intent_type, 0) + 1

            # 언어 집계
            languages[entry.language] = languages.get(entry.language, 0) + 1

            # 신뢰도 합산
            avg_confidence += entry.intent_confidence

        avg_confidence /= len(self._entries)

        return {
            "storage": self._storage,
            "created_at": self._created_at.isoformat(),
            "total_queries": len(self._entries),
            "intent_distribution": intent_types,
            "language_distribution": languages,
            "average_confidence": round(avg_confidence, 3),
        }


# ============================================================
# Global Instance
# ============================================================

_query_logger: Optional[QueryLogger] = None


def get_query_logger(storage_backend: str = "memory") -> QueryLogger:
    """
    전역 QueryLogger 인스턴스 반환

    Args:
        storage_backend: 저장 백엔드

    Returns:
        QueryLogger 인스턴스
    """
    global _query_logger
    if _query_logger is None:
        _query_logger = QueryLogger(storage_backend)
    return _query_logger


def reset_query_logger() -> None:
    """QueryLogger 초기화 (테스트용)"""
    global _query_logger
    _query_logger = None
