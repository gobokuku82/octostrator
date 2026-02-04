"""Tool I/O Base Schema

Tool의 기본 입출력 스키마를 정의합니다.
모든 Tool I/O 스키마는 이 기본 클래스를 상속합니다.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class ToolInput(BaseModel):
    """Tool 입력 기본 스키마"""
    context: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    todo_id: Optional[str] = None


class ToolOutput(BaseModel):
    """Tool 출력 기본 스키마"""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
