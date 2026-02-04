"""Todo Models V2.0 - Todo 아이템 Pydantic 모델

이 파일은 states/todo.py에서 models/로 이동됨.
Pydantic 모델만 포함하며, LangGraph 상태와 분리.
"""

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ============================================================
# Hierarchical Metadata Components
# ============================================================

class TodoExecutionConfig(BaseModel):
    """실행 관련 설정"""
    tool: Optional[str] = None
    tool_params: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None  # 초
    max_retries: int = 3
    retry_count: int = 0


class TodoDataConfig(BaseModel):
    """데이터 관련 설정"""
    input_data: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    expected_result: Optional[Dict[str, Any]] = None


class TodoDependencyConfig(BaseModel):
    """의존성 관련 설정"""
    depends_on: List[str] = Field(default_factory=list)  # 이 todo가 의존하는 todo IDs
    blocks: List[str] = Field(default_factory=list)      # 이 todo가 블록하는 todo IDs


class TodoProgress(BaseModel):
    """진행 상황 추적"""
    progress_percentage: int = Field(default=0, ge=0, le=100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TodoApproval(BaseModel):
    """승인 관련"""
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    user_notes: Optional[str] = None


class TodoMetadata(BaseModel):
    """Todo 메타데이터 - 계층적 구조"""
    execution: TodoExecutionConfig = Field(default_factory=TodoExecutionConfig)
    data: TodoDataConfig = Field(default_factory=TodoDataConfig)
    dependency: TodoDependencyConfig = Field(default_factory=TodoDependencyConfig)
    progress: TodoProgress = Field(default_factory=TodoProgress)
    approval: TodoApproval = Field(default_factory=TodoApproval)
    context: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# ============================================================
# TodoItem V2.0
# ============================================================

class TodoItem(BaseModel):
    """Todo 아이템 V2.0"""

    # 기본 정보
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    task_type: str = "general"  # 작업 타입 (collect, analyze, report 등)

    # 실행 정보
    layer: Literal["cognitive", "planning", "ml_execution", "biz_execution", "response"]
    status: Literal["pending", "in_progress", "completed", "failed", "blocked", "skipped", "needs_approval", "cancelled"] = "pending"
    priority: int = Field(default=5, ge=0, le=10)

    # 계층 구조
    parent_id: Optional[str] = None

    # 메타데이터 (계층적)
    metadata: TodoMetadata = Field(default_factory=TodoMetadata)

    # 생성 정보
    created_by: str = "system"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 버전 관리
    version: int = 1
    history: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
