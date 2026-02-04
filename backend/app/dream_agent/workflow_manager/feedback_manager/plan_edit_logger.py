"""Plan Edit Logger - 사용자의 계획 편집 내역 로깅

HITL 과정에서 사용자의 계획 편집 내역을 로깅하여
Planning 모델 학습에 활용합니다.

수집 데이터:
- original_todos (편집 전 todos)
- edited_todos (편집 후 todos)
- edit_operations (편집 작업 목록)
- user_instruction (자연어 지시)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class PlanEditLogEntry:
    """계획 편집 로그 엔트리"""
    id: str
    session_id: str
    plan_id: str
    timestamp: datetime

    # 편집 전후 상태
    before_todos: List[Dict[str, Any]]
    after_todos: List[Dict[str, Any]]

    # 편집 내용
    operations: List[Dict[str, Any]]  # add, update, delete, reorder, skip

    # 컨텍스트
    user_input: str = ""  # 자연어 지시 (있는 경우)
    intent: Dict[str, Any] = field(default_factory=dict)
    edit_source: str = "manual"  # "manual" | "natural_language" | "api"

    # 메타데이터
    edit_duration_seconds: float = 0.0
    plan_version_before: int = 0
    plan_version_after: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "timestamp": self.timestamp.isoformat(),
            "before_todos": self.before_todos,
            "after_todos": self.after_todos,
            "operations": self.operations,
            "user_input": self.user_input,
            "intent": self.intent,
            "edit_source": self.edit_source,
            "edit_duration_seconds": self.edit_duration_seconds,
            "plan_version_before": self.plan_version_before,
            "plan_version_after": self.plan_version_after,
        }


class PlanEditLogger:
    """
    계획 편집 로거

    사용자의 계획 편집 내역을 로깅하여
    Planning 모델 학습 데이터로 활용합니다.
    """

    def __init__(self, storage_backend: str = "memory"):
        """
        Args:
            storage_backend: 저장 백엔드 ("memory", "file", "database")
        """
        self._storage = storage_backend
        self._entries: List[PlanEditLogEntry] = []
        self._created_at = datetime.now()

    async def log(
        self,
        session_id: str,
        plan_id: str,
        before_todos: List[Dict[str, Any]],
        after_todos: List[Dict[str, Any]],
        operations: List[Dict[str, Any]],
        user_input: str = "",
        intent: Optional[Dict[str, Any]] = None,
        edit_source: str = "manual",
        edit_duration_seconds: float = 0.0,
        plan_version_before: int = 0,
        plan_version_after: int = 0
    ) -> str:
        """
        계획 편집 로깅

        Args:
            session_id: 세션 ID
            plan_id: 계획 ID
            before_todos: 편집 전 todos
            after_todos: 편집 후 todos
            operations: 편집 작업 목록
            user_input: 자연어 지시
            intent: 원본 의도 정보
            edit_source: 편집 소스
            edit_duration_seconds: 편집 소요 시간
            plan_version_before: 편집 전 버전
            plan_version_after: 편집 후 버전

        Returns:
            로그 엔트리 ID
        """
        entry = PlanEditLogEntry(
            id=f"plan_edit_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            plan_id=plan_id,
            timestamp=datetime.now(),
            before_todos=before_todos,
            after_todos=after_todos,
            operations=operations,
            user_input=user_input,
            intent=intent or {},
            edit_source=edit_source,
            edit_duration_seconds=edit_duration_seconds,
            plan_version_before=plan_version_before,
            plan_version_after=plan_version_after,
        )

        await self._store(entry)
        logger.debug(f"[PlanEditLogger] Plan edit logged: {entry.id}")

        return entry.id

    async def _store(self, entry: PlanEditLogEntry) -> None:
        """저장"""
        if self._storage == "memory":
            self._entries.append(entry)
        # TODO: file, database 백엔드 구현

    async def get_entries(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[PlanEditLogEntry]:
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
                "input": user_input + intent,
                "original_plan": before_todos,
                "corrected_plan": after_todos,
                "corrections": operations
            }
        """
        return [
            {
                "input": e.user_input,
                "intent": e.intent,
                "original_plan": e.before_todos,
                "corrected_plan": e.after_todos,
                "corrections": e.operations,
                "edit_source": e.edit_source,
            }
            for e in self._entries
        ]

    async def analyze_patterns(self) -> Dict[str, Any]:
        """
        편집 패턴 분석

        Returns:
            패턴 분석 결과:
            - 자주 추가되는 Todo 유형
            - 자주 삭제되는 Todo 유형
            - 자주 수정되는 필드
        """
        add_patterns = []
        delete_patterns = []
        skip_patterns = []
        update_fields: Dict[str, int] = {}
        reorder_count = 0

        for entry in self._entries:
            for op in entry.operations:
                operation = op.get("operation", "")

                if operation == "add":
                    add_patterns.append(op.get("data", {}))
                elif operation == "delete":
                    delete_patterns.append(op.get("todo_id"))
                elif operation == "skip":
                    skip_patterns.append(op.get("todo_id"))
                elif operation == "update":
                    for field_name in op.get("data", {}).keys():
                        update_fields[field_name] = update_fields.get(field_name, 0) + 1
                elif operation == "reorder":
                    reorder_count += 1

        return {
            "total_edits": len(self._entries),
            "operations": {
                "add_count": len(add_patterns),
                "delete_count": len(delete_patterns),
                "skip_count": len(skip_patterns),
                "update_count": sum(update_fields.values()),
                "reorder_count": reorder_count,
            },
            "most_updated_fields": sorted(
                update_fields.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "edit_sources": self._count_edit_sources(),
        }

    def _count_edit_sources(self) -> Dict[str, int]:
        """편집 소스별 집계"""
        sources: Dict[str, int] = {}
        for entry in self._entries:
            source = entry.edit_source
            sources[source] = sources.get(source, 0) + 1
        return sources

    async def get_by_operation_type(
        self,
        operation_type: str
    ) -> List[PlanEditLogEntry]:
        """
        특정 편집 작업 유형의 로그 조회

        Args:
            operation_type: 작업 유형 (add, update, delete, reorder, skip)

        Returns:
            로그 엔트리 목록
        """
        return [
            e for e in self._entries
            if any(op.get("operation") == operation_type for op in e.operations)
        ]

    async def get_natural_language_edits(self) -> List[PlanEditLogEntry]:
        """
        자연어 기반 편집 로그 조회

        Returns:
            로그 엔트리 목록
        """
        return [
            e for e in self._entries
            if e.edit_source == "natural_language" and e.user_input
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
                "total_edits": 0,
            }

        total_operations = sum(len(e.operations) for e in self._entries)
        avg_duration = sum(e.edit_duration_seconds for e in self._entries) / len(self._entries)

        return {
            "storage": self._storage,
            "created_at": self._created_at.isoformat(),
            "total_edits": len(self._entries),
            "total_operations": total_operations,
            "average_duration_seconds": round(avg_duration, 2),
            "edit_sources": self._count_edit_sources(),
        }


# ============================================================
# Global Instance
# ============================================================

_plan_edit_logger: Optional[PlanEditLogger] = None


def get_plan_edit_logger(storage_backend: str = "memory") -> PlanEditLogger:
    """
    전역 PlanEditLogger 인스턴스 반환

    Args:
        storage_backend: 저장 백엔드

    Returns:
        PlanEditLogger 인스턴스
    """
    global _plan_edit_logger
    if _plan_edit_logger is None:
        _plan_edit_logger = PlanEditLogger(storage_backend)
    return _plan_edit_logger


def reset_plan_edit_logger() -> None:
    """PlanEditLogger 초기화 (테스트용)"""
    global _plan_edit_logger
    _plan_edit_logger = None
