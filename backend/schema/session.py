"""Session related schemas"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class SessionBase(BaseModel):
    """세션 기본 모델"""
    user_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCreate(SessionBase):
    """세션 생성 모델"""
    pass


class SessionResponse(SessionBase):
    """세션 응답 모델"""
    id: UUID
    session_token: str
    thread_id: str
    is_active: bool
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True