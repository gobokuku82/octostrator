"""Message related schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


class MessageRole(str, Enum):
    """메시지 역할"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ContentBlock(BaseModel):
    """Content Block for LangChain 1.0 compatibility"""
    type: str
    content: Dict[str, Any]


class MessageBase(BaseModel):
    """메시지 기본 모델"""
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageCreate(MessageBase):
    """메시지 생성 모델"""
    thread_id: Optional[str] = None
    content_blocks: Optional[List[ContentBlock]] = None


class Message(MessageBase):
    """메시지 모델"""
    id: UUID
    thread_id: str
    content_blocks: Optional[List[ContentBlock]] = None
    created_at: datetime

    class Config:
        from_attributes = True