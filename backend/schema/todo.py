"""TODO related schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4


class TodoStatus(str, Enum):
    """TODO 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TodoPriority(str, Enum):
    """TODO 우선순위"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TodoBase(BaseModel):
    """TODO 기본 모델"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    priority: TodoPriority = TodoPriority.MEDIUM
    assigned_agent: Optional[str] = None
    estimated_time_minutes: Optional[int] = Field(None, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TodoCreate(TodoBase):
    """TODO 생성 모델"""
    parent_todo_id: Optional[UUID] = None
    dependencies: List[UUID] = Field(default_factory=list)


class TodoUpdate(BaseModel):
    """TODO 업데이트 모델"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    assigned_agent: Optional[str] = None
    estimated_time_minutes: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None


class TodoItem(TodoBase):
    """TODO 아이템 모델 (완전한 TODO 정보)"""
    id: UUID = Field(default_factory=uuid4)
    status: TodoStatus = TodoStatus.PENDING
    parent_todo_id: Optional[UUID] = None
    dependencies: List[UUID] = Field(default_factory=list)
    thread_id: Optional[str] = None
    order_index: int = 0
    actual_time_minutes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        from_attributes=True
    )

    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary with proper datetime serialization"""
        data = super().model_dump(**kwargs)
        # Convert datetime objects to ISO format strings
        for key in ['created_at', 'started_at', 'completed_at', 'updated_at']:
            if key in data and data[key]:
                if isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
        # Convert UUID to string
        for key in ['id', 'parent_todo_id']:
            if key in data and data[key]:
                data[key] = str(data[key])
        if 'dependencies' in data:
            data['dependencies'] = [str(dep) for dep in data['dependencies']]
        return data


class TodoResponse(BaseModel):
    """TODO 응답 모델"""
    todo: TodoItem
    children: List[TodoItem] = Field(default_factory=list)
    dependencies: List[TodoItem] = Field(default_factory=list)


class TodoListResponse(BaseModel):
    """TODO 리스트 응답 모델"""
    todos: List[TodoItem]
    total: int
    page: int = 1
    page_size: int = 20