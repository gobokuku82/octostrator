"""Decision Manager - 사용자 결정 대기 및 관리"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class DecisionRequest:
    """사용자 결정 요청 데이터"""

    def __init__(
        self,
        request_id: str,
        session_id: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        message: str,
        timeout: int = 300
    ):
        """
        Args:
            request_id: 요청 고유 ID
            session_id: Session ID
            context: 요청 컨텍스트 (todo_id, error 등)
            options: 선택 옵션 리스트
            message: 사용자에게 표시할 메시지
            timeout: 타임아웃 (초)
        """
        self.request_id = request_id
        self.session_id = session_id
        self.context = context
        self.options = options
        self.message = message
        self.timeout = timeout
        self.created_at = datetime.now()
        self.decision: Optional[Dict[str, Any]] = None
        self.event = asyncio.Event()

    def to_dict(self) -> Dict[str, Any]:
        """WebSocket 전송용 dict 변환"""
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "context": self.context,
            "options": self.options,
            "message": self.message,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat()
        }


class DecisionManager:
    """사용자 결정 대기 및 관리 시스템"""

    def __init__(self):
        """
        초기화

        pending_requests: {request_id: DecisionRequest}
        """
        self.pending_requests: Dict[str, DecisionRequest] = {}

    async def request_decision(
        self,
        request_id: str,
        session_id: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        message: str,
        timeout: int = 300,
        websocket_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 결정 요청 및 대기

        Args:
            request_id: 요청 고유 ID
            session_id: Session ID
            context: 요청 컨텍스트
            options: 선택 옵션 리스트
                [
                    {"value": "retry", "label": "재시도", "description": "..."},
                    {"value": "skip", "label": "건너뛰기", "description": "..."}
                ]
            message: 사용자에게 표시할 메시지
            timeout: 타임아웃 (초)
            websocket_callback: WebSocket 알림 콜백

        Returns:
            사용자 결정 dict 또는 None (타임아웃)
            {
                "action": "retry",
                "data": {...}  # 추가 데이터
            }
        """
        # DecisionRequest 생성
        request = DecisionRequest(
            request_id=request_id,
            session_id=session_id,
            context=context,
            options=options,
            message=message,
            timeout=timeout
        )

        self.pending_requests[request_id] = request

        try:
            # WebSocket으로 사용자에게 알림
            if websocket_callback:
                await self._send_decision_request(request, websocket_callback)

            # 사용자 결정 대기 (타임아웃 포함)
            try:
                await asyncio.wait_for(request.event.wait(), timeout=timeout)
                logger.info(
                    f"Decision received: request_id={request_id}, "
                    f"decision={request.decision}"
                )
                return request.decision

            except asyncio.TimeoutError:
                logger.warning(
                    f"Decision request timed out: request_id={request_id}, "
                    f"timeout={timeout}s"
                )
                return None

        finally:
            # Cleanup
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

    async def _send_decision_request(
        self,
        request: DecisionRequest,
        websocket_callback: Callable
    ):
        """WebSocket으로 결정 요청 전송"""
        try:
            await websocket_callback({
                "type": "decision_request",
                "data": request.to_dict()
            })
            logger.info(f"Decision request sent: {request.request_id}")

        except Exception as e:
            logger.error(f"Failed to send decision request: {e}", exc_info=True)

    def submit_decision(
        self,
        request_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        사용자 결정 제출 (API 엔드포인트에서 호출)

        Args:
            request_id: 요청 ID
            action: 선택한 액션
            data: 추가 데이터

        Returns:
            성공 여부
        """
        if request_id not in self.pending_requests:
            logger.warning(f"Decision request not found: {request_id}")
            return False

        request = self.pending_requests[request_id]

        # 결정 저장
        request.decision = {
            "action": action,
            "data": data or {},
            "submitted_at": datetime.now().isoformat()
        }

        # Event 설정 (대기 중인 코루틴 깨우기)
        request.event.set()

        logger.info(
            f"Decision submitted: request_id={request_id}, "
            f"action={action}"
        )
        return True

    def cancel_decision(self, request_id: str) -> bool:
        """
        결정 요청 취소

        Args:
            request_id: 요청 ID

        Returns:
            성공 여부
        """
        if request_id not in self.pending_requests:
            logger.warning(f"Decision request not found: {request_id}")
            return False

        request = self.pending_requests[request_id]

        # 기본 결정 설정 (취소)
        request.decision = {
            "action": "cancel",
            "data": {},
            "submitted_at": datetime.now().isoformat()
        }

        # Event 설정
        request.event.set()

        logger.info(f"Decision cancelled: {request_id}")
        return True

    def get_pending_requests(
        self,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        대기 중인 결정 요청 조회

        Args:
            session_id: Session ID (None이면 전체)

        Returns:
            결정 요청 리스트
        """
        requests = []

        for request in self.pending_requests.values():
            if session_id is None or request.session_id == session_id:
                requests.append(request.to_dict())

        return requests

    def has_pending_request(self, request_id: str) -> bool:
        """
        결정 요청이 대기 중인지 확인

        Args:
            request_id: 요청 ID

        Returns:
            대기 중이면 True
        """
        return request_id in self.pending_requests

    def cleanup_session(self, session_id: str) -> int:
        """
        Session의 모든 결정 요청 정리

        Args:
            session_id: Session ID

        Returns:
            정리된 요청 개수
        """
        to_remove = []

        for request_id, request in self.pending_requests.items():
            if request.session_id == session_id:
                to_remove.append(request_id)
                # 취소 처리
                request.decision = {
                    "action": "cancel",
                    "data": {"reason": "session_cleanup"},
                    "submitted_at": datetime.now().isoformat()
                }
                request.event.set()

        for request_id in to_remove:
            del self.pending_requests[request_id]

        if to_remove:
            logger.info(
                f"Cleaned up {len(to_remove)} decision requests "
                f"for session {session_id}"
            )

        return len(to_remove)


# ============================================================
# Global Instance
# ============================================================

_decision_manager: Optional[DecisionManager] = None


def get_decision_manager() -> DecisionManager:
    """전역 DecisionManager 인스턴스 반환"""
    global _decision_manager
    if _decision_manager is None:
        _decision_manager = DecisionManager()
    return _decision_manager


# 편의를 위한 전역 인스턴스
decision_manager = get_decision_manager()
