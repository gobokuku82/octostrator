"""WebSocket Message Schemas"""

from pydantic import BaseModel
from typing import Literal, Optional, Any


class WSMessage(BaseModel):
    """WebSocket 메시지 기본 스키마"""
    type: Literal[
        "status",        # 상태 업데이트
        "todo_update",   # Todo 상태 변경
        "result",        # 실행 결과
        "error",         # 에러
        "hitl_request",  # HITL 요청
        "complete",      # 완료
        "pong",          # 핑퐁 응답
    ]
    data: Any = None


class TodoUpdateMessage(BaseModel):
    """Todo 업데이트 메시지"""
    todo_id: str
    task: str
    status: str
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None


class HITLRequestMessage(BaseModel):
    """HITL 요청 메시지"""
    hitl_type: Literal["approval", "input", "edit"]
    message: str
    options: list = []
    required_field: Optional[str] = None
