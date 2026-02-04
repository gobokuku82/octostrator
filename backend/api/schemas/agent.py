"""Agent API Schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any


class AgentRequest(BaseModel):
    """Agent 실행 요청"""
    user_input: str = Field(..., description="사용자 입력 텍스트")
    language: str = Field(default="KOR", description="언어 코드 (KOR, EN, JP)")
    session_id: Optional[str] = Field(default=None, description="세션 ID (미제공 시 자동 생성)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "라네즈 리뷰를 분석해서 인사이트 뽑아줘",
                "language": "KOR",
            }
        }


class AgentResponse(BaseModel):
    """Agent 실행 응답"""
    session_id: str = Field(..., description="세션 ID")
    status: str = Field(..., description="상태 (running, completed, failed, stopped)")
    response: Optional[str] = Field(default=None, description="Agent 응답 텍스트")
    todos: List[Any] = Field(default=[], description="Todo 리스트")
    error: Optional[str] = Field(default=None, description="에러 메시지")


class AgentStatus(BaseModel):
    """Agent 상태 조회 응답"""
    session_id: str
    status: str
    response: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[dict] = None
