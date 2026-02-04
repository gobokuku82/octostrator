"""Approval Manager - 계획 승인 관리 (Phase 1.7 재설계)

변경사항:
- 타임아웃 시 자동 거부 (기존: 자동 승인)
- 감사 로그 추가
- 거부 사유 처리 개선
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class ApprovalStatus(str, Enum):
    """승인 상태"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ApprovalRecord:
    """승인 기록"""

    def __init__(
        self,
        session_id: str,
        plan_summary: str,
        todos_count: int,
        status: ApprovalStatus,
        reason: Optional[str] = None,
        modified_todos: Optional[list] = None,
        actor: str = "user"
    ):
        self.session_id = session_id
        self.plan_summary = plan_summary
        self.todos_count = todos_count
        self.status = status
        self.reason = reason
        self.modified_todos = modified_todos
        self.actor = actor
        self.created_at = datetime.now()
        self.resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "plan_summary": self.plan_summary,
            "todos_count": self.todos_count,
            "status": self.status.value,
            "reason": self.reason,
            "actor": self.actor,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class ApprovalResult:
    """승인 결과"""

    def __init__(
        self,
        approved: bool,
        status: ApprovalStatus,
        modified_todos: Optional[list] = None,
        reason: Optional[str] = None,
        auto_decision: bool = False
    ):
        self.approved = approved
        self.status = status
        self.modified_todos = modified_todos
        self.reason = reason
        self.auto_decision = auto_decision
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "status": self.status.value,
            "modified_todos": self.modified_todos,
            "reason": self.reason,
            "auto_decision": self.auto_decision,
            "timestamp": self.timestamp.isoformat()
        }


class ApprovalManager:
    """계획 승인 관리자 (Phase 1.7 재설계)"""

    def __init__(self):
        self._pending_approvals: Dict[str, asyncio.Event] = {}
        self._approval_results: Dict[str, ApprovalResult] = {}
        self._approval_history: List[ApprovalRecord] = []
        self._pending_records: Dict[str, ApprovalRecord] = {}

    async def request_approval(
        self,
        session_id: str,
        plan: Dict[str, Any],
        todos: list,
        timeout: float = 300.0,
        auto_reject_on_timeout: bool = True
    ) -> ApprovalResult:
        """
        계획 승인 요청

        Args:
            session_id: 세션 ID
            plan: 생성된 계획
            todos: 생성된 todos
            timeout: 승인 대기 시간 (초)
            auto_reject_on_timeout: 타임아웃 시 자동 거부 여부 (기본값: True)

        Returns:
            ApprovalResult: 승인 결과
        """
        logger.info(f"Requesting approval for session {session_id}, {len(todos)} todos")

        # 승인 이벤트 생성
        event = asyncio.Event()
        self._pending_approvals[session_id] = event

        # 기록 생성
        record = ApprovalRecord(
            session_id=session_id,
            plan_summary=plan.get("plan_description", "No description"),
            todos_count=len(todos),
            status=ApprovalStatus.PENDING
        )
        self._pending_records[session_id] = record

        try:
            # 승인 대기 (timeout까지)
            await asyncio.wait_for(event.wait(), timeout=timeout)

            # 승인 결과 반환
            result = self._approval_results.get(session_id)
            if result:
                record.status = result.status
                record.reason = result.reason
                record.resolved_at = datetime.now()
                self._approval_history.append(record)
                logger.info(f"Approval result for {session_id}: {result.status.value}")
                return result

            # 결과 없음 (예외 상황)
            record.status = ApprovalStatus.REJECTED
            record.reason = "No result found"
            record.resolved_at = datetime.now()
            self._approval_history.append(record)
            return ApprovalResult(
                approved=False,
                status=ApprovalStatus.REJECTED,
                reason="No result found"
            )

        except asyncio.TimeoutError:
            record.resolved_at = datetime.now()

            if auto_reject_on_timeout:
                # 타임아웃 시 자동 거부 (보안상 안전)
                record.status = ApprovalStatus.TIMEOUT
                record.reason = f"Timeout after {timeout}s - auto rejected"
                self._approval_history.append(record)

                logger.warning(f"Approval timeout for {session_id} - auto rejected")
                return ApprovalResult(
                    approved=False,
                    status=ApprovalStatus.TIMEOUT,
                    reason=f"Timeout after {timeout}s - auto rejected",
                    auto_decision=True
                )
            else:
                # 타임아웃 시 자동 승인 (기존 동작, 비권장)
                record.status = ApprovalStatus.APPROVED
                record.reason = f"Timeout after {timeout}s - auto approved"
                self._approval_history.append(record)

                logger.warning(f"Approval timeout for {session_id} - auto approved (not recommended)")
                return ApprovalResult(
                    approved=True,
                    status=ApprovalStatus.APPROVED,
                    reason=f"Timeout after {timeout}s - auto approved",
                    auto_decision=True
                )

        finally:
            # 정리
            self._pending_approvals.pop(session_id, None)
            self._approval_results.pop(session_id, None)
            self._pending_records.pop(session_id, None)

    def submit_approval(
        self,
        session_id: str,
        approved: bool,
        modified_todos: Optional[list] = None,
        reason: Optional[str] = None,
        actor: str = "user"
    ) -> bool:
        """
        승인 제출 (사용자 응답)

        Args:
            session_id: 세션 ID
            approved: 승인 여부
            modified_todos: 수정된 todos (optional)
            reason: 승인/거부 사유 (optional)
            actor: 작업자

        Returns:
            성공 여부
        """
        if session_id not in self._pending_approvals:
            logger.warning(f"No pending approval for session {session_id}")
            return False

        # 승인 결과 저장
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        result = ApprovalResult(
            approved=approved,
            status=status,
            modified_todos=modified_todos,
            reason=reason
        )
        self._approval_results[session_id] = result

        # 기록 업데이트
        if session_id in self._pending_records:
            self._pending_records[session_id].actor = actor

        # 이벤트 발동
        self._pending_approvals[session_id].set()

        logger.info(f"Approval submitted for {session_id}: {status.value}")
        return True

    def cancel_approval(self, session_id: str, reason: str = "User cancelled") -> bool:
        """
        승인 요청 취소

        Args:
            session_id: 세션 ID
            reason: 취소 사유

        Returns:
            성공 여부
        """
        if session_id not in self._pending_approvals:
            logger.warning(f"No pending approval for session {session_id}")
            return False

        # 취소 결과 저장
        result = ApprovalResult(
            approved=False,
            status=ApprovalStatus.CANCELLED,
            reason=reason
        )
        self._approval_results[session_id] = result

        # 이벤트 발동
        self._pending_approvals[session_id].set()

        logger.info(f"Approval cancelled for {session_id}: {reason}")
        return True

    def has_pending_approval(self, session_id: str) -> bool:
        """승인 대기 중인지 확인"""
        return session_id in self._pending_approvals

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """모든 대기 중인 승인 요청 조회"""
        return [
            record.to_dict()
            for record in self._pending_records.values()
        ]

    def get_approval_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        승인 이력 조회

        Args:
            session_id: 세션 ID (None이면 전체)
            limit: 최대 개수

        Returns:
            승인 기록 리스트
        """
        records = self._approval_history

        if session_id:
            records = [r for r in records if r.session_id == session_id]

        # 최근 순 정렬
        records = sorted(records, key=lambda r: r.created_at, reverse=True)

        return [r.to_dict() for r in records[:limit]]

    def cleanup_session(self, session_id: str) -> bool:
        """
        세션의 승인 요청 정리

        Args:
            session_id: 세션 ID

        Returns:
            정리 수행 여부
        """
        if session_id in self._pending_approvals:
            self.cancel_approval(session_id, "Session cleanup")
            return True
        return False


# ============================================================
# Global Instance
# ============================================================

_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """전역 ApprovalManager 인스턴스 반환"""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


# 편의를 위한 전역 인스턴스
approval_manager = get_approval_manager()
