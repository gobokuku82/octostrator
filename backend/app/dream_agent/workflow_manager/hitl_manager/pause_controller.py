"""Pause Controller - Agent 실행 일시정지/재개 관리

상태 머신 기반 HITL 일시정지 제어
"""

from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class PauseReason(str, Enum):
    """일시정지 사유"""
    USER_REQUEST = "user_request"
    INPUT_REQUIRED = "input_required"
    APPROVAL_REQUIRED = "approval_required"
    ERROR_RECOVERY = "error_recovery"


class HITLMode(str, Enum):
    """HITL 모드"""
    RUNNING = "running"
    PAUSED = "paused"
    PLAN_EDIT = "plan_edit"
    INPUT_REQUEST = "input_request"
    APPROVAL_WAIT = "approval_wait"


class PauseController:
    """
    Pause 상태 관리 (상태 머신)

    상태 전이:
        RUNNING → PAUSED (user pause)
        RUNNING → INPUT_REQUEST (input required)
        RUNNING → APPROVAL_WAIT (approval required)
        PAUSED → PLAN_EDIT (edit plan)
        PAUSED → RUNNING (resume)
        PLAN_EDIT → PAUSED (cancel edit)
        PLAN_EDIT → RUNNING (save & resume)
        INPUT_REQUEST → RUNNING (input received)
        APPROVAL_WAIT → RUNNING (approved/rejected)
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._mode = HITLMode.RUNNING
        self._pause_reason: Optional[PauseReason] = None
        self._paused_at: Optional[datetime] = None
        self._message: Optional[str] = None
        self._resume_event = asyncio.Event()
        self._resume_event.set()  # 초기 상태: running
        self._callbacks: List[Callable] = []
        self._state_history: List[Dict[str, Any]] = []

    @property
    def mode(self) -> HITLMode:
        """현재 모드"""
        return self._mode

    @property
    def is_paused(self) -> bool:
        """일시정지 여부"""
        return self._mode != HITLMode.RUNNING

    @property
    def pause_reason(self) -> Optional[PauseReason]:
        """일시정지 사유"""
        return self._pause_reason

    async def request_pause(
        self,
        reason: PauseReason = PauseReason.USER_REQUEST,
        message: str = None
    ) -> bool:
        """
        일시정지 요청

        Args:
            reason: 일시정지 사유
            message: 사용자에게 표시할 메시지

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.RUNNING:
            logger.warning(f"Already paused: {self._mode}")
            return False

        previous_mode = self._mode
        self._mode = HITLMode.PAUSED
        self._pause_reason = reason
        self._paused_at = datetime.now()
        self._message = message
        self._resume_event.clear()

        self._record_state_change(previous_mode, self._mode, reason.value)

        await self._notify_callbacks("pause", {
            "reason": reason.value,
            "message": message,
            "timestamp": self._paused_at.isoformat()
        })

        logger.info(f"Session {self.session_id} paused: {reason.value}")
        return True

    async def enter_plan_edit(self) -> bool:
        """
        계획 편집 모드 진입

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.PAUSED:
            logger.warning(f"Cannot enter plan edit from {self._mode}")
            return False

        previous_mode = self._mode
        self._mode = HITLMode.PLAN_EDIT

        self._record_state_change(previous_mode, self._mode, "plan_edit_start")

        await self._notify_callbacks("plan_edit_start", {
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Session {self.session_id} entered plan edit mode")
        return True

    async def exit_plan_edit(self, save: bool = True) -> bool:
        """
        계획 편집 모드 종료

        Args:
            save: 저장 후 재개 여부 (False면 취소하고 PAUSED로)

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.PLAN_EDIT:
            logger.warning(f"Not in plan edit mode: {self._mode}")
            return False

        previous_mode = self._mode

        if save:
            # 저장 후 재개
            self._mode = HITLMode.RUNNING
            self._pause_reason = None
            self._paused_at = None
            self._message = None
            self._resume_event.set()

            self._record_state_change(previous_mode, self._mode, "plan_edit_save")

            await self._notify_callbacks("plan_edit_end", {
                "saved": True,
                "timestamp": datetime.now().isoformat()
            })
        else:
            # 취소하고 PAUSED로
            self._mode = HITLMode.PAUSED

            self._record_state_change(previous_mode, self._mode, "plan_edit_cancel")

            await self._notify_callbacks("plan_edit_end", {
                "saved": False,
                "timestamp": datetime.now().isoformat()
            })

        return True

    async def enter_input_request(
        self,
        field: str,
        message: str = None,
        options: List[Dict[str, Any]] = None
    ) -> bool:
        """
        입력 요청 모드 진입

        Args:
            field: 요청할 입력 필드명
            message: 사용자에게 표시할 메시지
            options: 선택 옵션 (있는 경우)

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.RUNNING:
            logger.warning(f"Cannot request input from {self._mode}")
            return False

        previous_mode = self._mode
        self._mode = HITLMode.INPUT_REQUEST
        self._pause_reason = PauseReason.INPUT_REQUIRED
        self._paused_at = datetime.now()
        self._message = message
        self._resume_event.clear()

        self._record_state_change(previous_mode, self._mode, f"input_request:{field}")

        await self._notify_callbacks("input_request", {
            "field": field,
            "message": message,
            "options": options,
            "timestamp": self._paused_at.isoformat()
        })

        logger.info(f"Session {self.session_id} requesting input: {field}")
        return True

    async def submit_input(self, field: str, value: Any) -> bool:
        """
        입력 제출 및 재개

        Args:
            field: 입력 필드명
            value: 입력 값

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.INPUT_REQUEST:
            logger.warning(f"Not waiting for input: {self._mode}")
            return False

        previous_mode = self._mode
        self._mode = HITLMode.RUNNING
        self._pause_reason = None
        self._paused_at = None
        self._message = None
        self._resume_event.set()

        self._record_state_change(previous_mode, self._mode, f"input_received:{field}")

        await self._notify_callbacks("input_received", {
            "field": field,
            "value": value,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Session {self.session_id} received input: {field}")
        return True

    async def enter_approval_wait(
        self,
        approval_type: str,
        message: str = None,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        승인 대기 모드 진입

        Args:
            approval_type: 승인 유형 (plan, cost, action 등)
            message: 사용자에게 표시할 메시지
            details: 승인 요청 상세 정보

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.RUNNING:
            logger.warning(f"Cannot wait for approval from {self._mode}")
            return False

        previous_mode = self._mode
        self._mode = HITLMode.APPROVAL_WAIT
        self._pause_reason = PauseReason.APPROVAL_REQUIRED
        self._paused_at = datetime.now()
        self._message = message
        self._resume_event.clear()

        self._record_state_change(previous_mode, self._mode, f"approval_request:{approval_type}")

        await self._notify_callbacks("approval_request", {
            "type": approval_type,
            "message": message,
            "details": details,
            "timestamp": self._paused_at.isoformat()
        })

        logger.info(f"Session {self.session_id} waiting for approval: {approval_type}")
        return True

    async def submit_approval(self, approved: bool, reason: str = None) -> bool:
        """
        승인/거부 제출 및 재개

        Args:
            approved: 승인 여부
            reason: 승인/거부 사유

        Returns:
            성공 여부
        """
        if self._mode != HITLMode.APPROVAL_WAIT:
            logger.warning(f"Not waiting for approval: {self._mode}")
            return False

        previous_mode = self._mode
        self._mode = HITLMode.RUNNING
        self._pause_reason = None
        self._paused_at = None
        self._message = None
        self._resume_event.set()

        self._record_state_change(previous_mode, self._mode, f"approval_{'approved' if approved else 'rejected'}")

        await self._notify_callbacks("approval_result", {
            "approved": approved,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Session {self.session_id} approval: {'approved' if approved else 'rejected'}")
        return True

    async def resume(self) -> bool:
        """
        실행 재개

        Returns:
            성공 여부
        """
        if self._mode == HITLMode.RUNNING:
            return False

        if self._mode == HITLMode.PLAN_EDIT:
            return await self.exit_plan_edit(save=True)

        previous_mode = self._mode
        pause_duration = None

        if self._paused_at:
            pause_duration = (datetime.now() - self._paused_at).total_seconds()

        self._mode = HITLMode.RUNNING
        self._pause_reason = None
        self._paused_at = None
        self._message = None
        self._resume_event.set()

        self._record_state_change(previous_mode, self._mode, "resume")

        await self._notify_callbacks("resume", {
            "previous_mode": previous_mode.value,
            "pause_duration": pause_duration,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Session {self.session_id} resumed")
        return True

    async def wait_for_resume(self, timeout: float = None) -> bool:
        """
        재개 대기

        Args:
            timeout: 타임아웃 (초)

        Returns:
            재개 여부 (타임아웃 시 False)
        """
        try:
            if timeout:
                await asyncio.wait_for(
                    self._resume_event.wait(),
                    timeout=timeout
                )
            else:
                await self._resume_event.wait()
            return True
        except asyncio.TimeoutError:
            return False

    def add_callback(self, callback: Callable) -> None:
        """
        이벤트 콜백 등록

        Args:
            callback: 콜백 함수 (async 지원)
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """콜백 제거"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify_callbacks(self, event_type: str, data: Dict[str, Any]) -> None:
        """콜백 알림"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _record_state_change(
        self,
        from_mode: HITLMode,
        to_mode: HITLMode,
        trigger: str
    ) -> None:
        """상태 변경 기록"""
        self._state_history.append({
            "from": from_mode.value,
            "to": to_mode.value,
            "trigger": trigger,
            "timestamp": datetime.now().isoformat()
        })

    def get_state(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            "session_id": self.session_id,
            "mode": self._mode.value,
            "is_paused": self.is_paused,
            "pause_reason": self._pause_reason.value if self._pause_reason else None,
            "paused_at": self._paused_at.isoformat() if self._paused_at else None,
            "message": self._message,
        }

    def get_state_history(self) -> List[Dict[str, Any]]:
        """상태 변경 이력 반환"""
        return self._state_history.copy()

    def to_agent_state_update(self) -> Dict[str, Any]:
        """AgentState 업데이트용 dict 반환"""
        return {
            "hitl_mode": self._mode.value,
            "hitl_pause_reason": self._pause_reason.value if self._pause_reason else None,
            "hitl_message": self._message,
            "hitl_timestamp": self._paused_at.isoformat() if self._paused_at else None,
        }


# ============================================================
# Session별 Controller 관리
# ============================================================

_controllers: Dict[str, PauseController] = {}


def get_pause_controller(session_id: str) -> PauseController:
    """
    Session별 PauseController 반환

    Args:
        session_id: 세션 ID

    Returns:
        PauseController 인스턴스
    """
    if session_id not in _controllers:
        _controllers[session_id] = PauseController(session_id)
    return _controllers[session_id]


def remove_pause_controller(session_id: str) -> bool:
    """
    PauseController 제거

    Args:
        session_id: 세션 ID

    Returns:
        제거 여부
    """
    if session_id in _controllers:
        del _controllers[session_id]
        return True
    return False


def get_all_paused_sessions() -> List[Dict[str, Any]]:
    """모든 일시정지된 세션 조회"""
    return [
        controller.get_state()
        for controller in _controllers.values()
        if controller.is_paused
    ]
