"""Input Requester - Agent가 사용자에게 입력을 요청하는 모듈

Agent 실행 중 필요한 정보를 사용자에게 요청하고 응답을 관리합니다.

사용 예시:
- 검색 키워드 요청
- 분석 옵션 선택
- 추가 파라미터 입력
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)


class InputType(str, Enum):
    """입력 유형"""
    TEXT = "text"              # 자유 텍스트 입력
    SELECT = "select"          # 단일 선택
    MULTI_SELECT = "multi_select"  # 다중 선택
    NUMBER = "number"          # 숫자 입력
    DATE = "date"              # 날짜 입력
    BOOLEAN = "boolean"        # 예/아니오
    FILE = "file"              # 파일 업로드


class RequestStatus(str, Enum):
    """요청 상태"""
    PENDING = "pending"        # 대기 중
    ANSWERED = "answered"      # 응답 완료
    CANCELLED = "cancelled"    # 취소됨
    TIMEOUT = "timeout"        # 타임아웃


@dataclass
class InputOption:
    """선택 옵션"""
    value: str
    label: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputRequest:
    """입력 요청"""
    request_id: str
    session_id: str
    field_name: str              # 요청하는 필드명
    input_type: InputType        # 입력 유형
    message: str                 # 사용자에게 표시할 메시지
    options: List[InputOption] = field(default_factory=list)  # 선택 옵션
    default_value: Any = None    # 기본값
    required: bool = True        # 필수 여부
    validation: Optional[Dict[str, Any]] = None  # 검증 규칙
    context: Dict[str, Any] = field(default_factory=dict)  # 추가 컨텍스트
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    answered_at: Optional[datetime] = None
    response_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "field_name": self.field_name,
            "input_type": self.input_type.value,
            "message": self.message,
            "options": [
                {
                    "value": opt.value,
                    "label": opt.label,
                    "description": opt.description,
                }
                for opt in self.options
            ],
            "default_value": self.default_value,
            "required": self.required,
            "validation": self.validation,
            "context": self.context,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
            "response_value": self.response_value,
        }


@dataclass
class InputResponse:
    """입력 응답"""
    request_id: str
    field_name: str
    value: Any
    answered_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class InputRequester:
    """
    입력 요청 관리자

    Agent가 사용자에게 입력을 요청하고 응답을 대기합니다.
    """

    def __init__(self, session_id: str):
        """
        Args:
            session_id: 세션 ID
        """
        self.session_id = session_id
        self._pending_requests: Dict[str, InputRequest] = {}
        self._response_events: Dict[str, asyncio.Event] = {}
        self._callbacks: List[Callable] = []
        self._history: List[Dict[str, Any]] = []
        self._created_at = datetime.now()

    async def request_input(
        self,
        field_name: str,
        input_type: InputType,
        message: str,
        options: Optional[List[Dict[str, Any]]] = None,
        default_value: Any = None,
        required: bool = True,
        validation: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 300.0
    ) -> Optional[Any]:
        """
        사용자에게 입력 요청

        Args:
            field_name: 요청하는 필드명
            input_type: 입력 유형
            message: 사용자에게 표시할 메시지
            options: 선택 옵션 (select/multi_select 시)
            default_value: 기본값
            required: 필수 여부
            validation: 검증 규칙
            context: 추가 컨텍스트
            timeout: 타임아웃 (초)

        Returns:
            사용자 응답 값 (타임아웃/취소 시 None)
        """
        request_id = str(uuid.uuid4())

        # 옵션 변환
        input_options = []
        if options:
            for opt in options:
                input_options.append(InputOption(
                    value=opt.get("value", ""),
                    label=opt.get("label", opt.get("value", "")),
                    description=opt.get("description"),
                    metadata=opt.get("metadata", {})
                ))

        # 요청 생성
        request = InputRequest(
            request_id=request_id,
            session_id=self.session_id,
            field_name=field_name,
            input_type=input_type,
            message=message,
            options=input_options,
            default_value=default_value,
            required=required,
            validation=validation,
            context=context or {},
        )

        # 저장 및 이벤트 생성
        self._pending_requests[request_id] = request
        self._response_events[request_id] = asyncio.Event()

        # 콜백 알림
        await self._notify_callbacks("input_request", request.to_dict())

        logger.info(
            f"[InputRequester] Request created: {request_id} - "
            f"field: {field_name}, type: {input_type.value}"
        )

        # 응답 대기
        try:
            await asyncio.wait_for(
                self._response_events[request_id].wait(),
                timeout=timeout
            )

            # 응답 반환
            return request.response_value

        except asyncio.TimeoutError:
            # 타임아웃 처리
            request.status = RequestStatus.TIMEOUT
            logger.warning(f"[InputRequester] Request timeout: {request_id}")

            await self._notify_callbacks("input_timeout", {
                "request_id": request_id,
                "field_name": field_name,
            })

            # 필수가 아니면 기본값 반환
            if not required:
                return default_value

            return None

        finally:
            # 정리
            self._cleanup_request(request_id)

    async def submit_response(
        self,
        request_id: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        입력 응답 제출

        Args:
            request_id: 요청 ID
            value: 응답 값
            metadata: 추가 메타데이터

        Returns:
            성공 여부
        """
        request = self._pending_requests.get(request_id)
        if not request:
            logger.warning(f"[InputRequester] Request not found: {request_id}")
            return False

        if request.status != RequestStatus.PENDING:
            logger.warning(
                f"[InputRequester] Request not pending: "
                f"{request_id} - {request.status}"
            )
            return False

        # 검증
        if request.validation:
            if not self._validate_value(value, request.validation, request.input_type):
                logger.warning(f"[InputRequester] Validation failed: {request_id}")
                return False

        # 응답 저장
        request.response_value = value
        request.answered_at = datetime.now()
        request.status = RequestStatus.ANSWERED

        # 히스토리 기록
        self._history.append({
            "request": request.to_dict(),
            "response": {
                "value": value,
                "metadata": metadata,
                "answered_at": request.answered_at.isoformat(),
            }
        })

        # 이벤트 트리거
        event = self._response_events.get(request_id)
        if event:
            event.set()

        # 콜백 알림
        await self._notify_callbacks("input_received", {
            "request_id": request_id,
            "field_name": request.field_name,
            "value": value,
        })

        logger.info(f"[InputRequester] Response received: {request_id} - {value}")

        return True

    async def cancel_request(self, request_id: str) -> bool:
        """
        요청 취소

        Args:
            request_id: 요청 ID

        Returns:
            성공 여부
        """
        request = self._pending_requests.get(request_id)
        if not request:
            return False

        if request.status != RequestStatus.PENDING:
            return False

        request.status = RequestStatus.CANCELLED

        # 이벤트 트리거 (대기 해제)
        event = self._response_events.get(request_id)
        if event:
            event.set()

        # 콜백 알림
        await self._notify_callbacks("input_cancelled", {
            "request_id": request_id,
            "field_name": request.field_name,
        })

        logger.info(f"[InputRequester] Request cancelled: {request_id}")

        return True

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """대기 중인 요청 조회"""
        return [
            req.to_dict()
            for req in self._pending_requests.values()
            if req.status == RequestStatus.PENDING
        ]

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """특정 요청 조회"""
        request = self._pending_requests.get(request_id)
        return request.to_dict() if request else None

    def add_callback(self, callback: Callable) -> None:
        """이벤트 콜백 등록"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """콜백 제거"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify_callbacks(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """콜백 알림"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"[InputRequester] Callback error: {e}")

    def _validate_value(
        self,
        value: Any,
        validation: Dict[str, Any],
        input_type: InputType
    ) -> bool:
        """값 검증"""
        try:
            # 필수 체크
            if validation.get("required", False) and value is None:
                return False

            # 타입별 검증
            if input_type == InputType.TEXT:
                if not isinstance(value, str):
                    return False
                min_len = validation.get("min_length", 0)
                max_len = validation.get("max_length", float('inf'))
                if not (min_len <= len(value) <= max_len):
                    return False

            elif input_type == InputType.NUMBER:
                if not isinstance(value, (int, float)):
                    return False
                min_val = validation.get("min", float('-inf'))
                max_val = validation.get("max", float('inf'))
                if not (min_val <= value <= max_val):
                    return False

            elif input_type == InputType.SELECT:
                allowed = validation.get("allowed_values", [])
                if allowed and value not in allowed:
                    return False

            elif input_type == InputType.MULTI_SELECT:
                if not isinstance(value, list):
                    return False
                allowed = validation.get("allowed_values", [])
                if allowed and not all(v in allowed for v in value):
                    return False

            return True

        except Exception as e:
            logger.error(f"[InputRequester] Validation error: {e}")
            return False

    def _cleanup_request(self, request_id: str) -> None:
        """요청 정리 (메모리 관리)"""
        # 이벤트 제거
        if request_id in self._response_events:
            del self._response_events[request_id]

        # 오래된 요청은 제거하지 않고 히스토리로 유지
        # (필요시 별도 정리 로직 추가)

    def get_history(self) -> List[Dict[str, Any]]:
        """요청/응답 히스토리 반환"""
        return self._history.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Requester 요약 정보"""
        statuses = {}
        for req in self._pending_requests.values():
            status = req.status.value
            statuses[status] = statuses.get(status, 0) + 1

        return {
            "session_id": self.session_id,
            "created_at": self._created_at.isoformat(),
            "total_requests": len(self._pending_requests),
            "status_summary": statuses,
            "history_count": len(self._history),
        }


# ============================================================
# Session별 Requester 관리
# ============================================================

_requesters: Dict[str, InputRequester] = {}


def get_input_requester(session_id: str) -> InputRequester:
    """
    Session별 InputRequester 반환

    Args:
        session_id: 세션 ID

    Returns:
        InputRequester 인스턴스
    """
    if session_id not in _requesters:
        _requesters[session_id] = InputRequester(session_id)
    return _requesters[session_id]


def remove_input_requester(session_id: str) -> bool:
    """
    InputRequester 제거

    Args:
        session_id: 세션 ID

    Returns:
        제거 여부
    """
    if session_id in _requesters:
        del _requesters[session_id]
        return True
    return False


def get_all_pending_requests() -> List[Dict[str, Any]]:
    """모든 세션의 대기 중인 요청 조회"""
    all_requests = []
    for requester in _requesters.values():
        all_requests.extend(requester.get_pending_requests())
    return all_requests
