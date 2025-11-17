"""Agent related schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


class AgentType(str, Enum):
    """에이전트 타입"""
    PLANNER = "planner"
    ROUTER = "router"
    EXECUTOR = "executor"
    VALIDATOR = "validator"
    SUPERVISOR = "supervisor"


class ExecutorSubtype(str, Enum):
    """실행 에이전트 서브타입"""
    SEARCH = "search"
    ANALYSIS = "analysis"
    DOCUMENT = "document"
    API = "api"


class AgentStatus(str, Enum):
    """에이전트 상태"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class AgentBase(BaseModel):
    """에이전트 기본 모델"""
    agent_name: str
    agent_type: AgentType
    executor_subtype: Optional[ExecutorSubtype] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    configuration: Dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    """에이전트 생성 모델"""
    pass


class Agent(AgentBase):
    """에이전트 모델"""
    id: UUID
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentExecution(BaseModel):
    """에이전트 실행 기록"""
    id: UUID
    agent_id: UUID
    thread_id: str
    todo_id: Optional[UUID] = None
    status: AgentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

    class Config:
        from_attributes = True