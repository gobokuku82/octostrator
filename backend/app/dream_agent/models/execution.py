"""Execution Models - 실행 관련 모델

Phase 0.5에서 신규 추가된 모델.
Execution Layer의 실행 결과 및 컨텍스트를 표현.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionResult(BaseModel):
    """실행 결과 (표준)"""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    todo_id: Optional[str] = None
    tool_name: Optional[str] = None
    executor_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class ExecutionContext(BaseModel):
    """실행 컨텍스트"""
    session_id: str
    language: str = "ko"
    previous_results: Dict[str, Any] = Field(default_factory=dict)
    reviews: List[Dict] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
