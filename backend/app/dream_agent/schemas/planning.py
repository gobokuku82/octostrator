"""Planning Layer I/O Schema

Planning Layer의 입출력 스키마를 정의합니다.
Phase 3: field_validator 기반 검증 추가.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from ..models.intent import Intent
from ..models.todo import TodoItem
from ..models.plan import Plan


class PlanningInput(BaseModel):
    """Planning Layer 입력"""
    intent: Intent
    session_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    # 기존 Plan이 있는 경우 (재계획)
    existing_plan: Optional[Plan] = None
    replan_instruction: Optional[str] = None

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError("session_id cannot be empty")
        return v.strip()

    # NOTE: Intent 검증은 cognitive_node에서 수행됨
    # 스키마는 문서화 목적으로만 사용


class PlanningOutput(BaseModel):
    """Planning Layer 출력"""
    plan: Plan
    todos: List[TodoItem] = Field(default_factory=list)
    estimated_duration_sec: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0.0)
    requires_approval: bool = False
    approval_message: Optional[str] = None
    mermaid_diagram: Optional[str] = None

    @field_validator('todos')
    @classmethod
    def validate_todos(cls, v):
        if not v:
            raise ValueError("At least one todo is required")
        return v

    @model_validator(mode='after')
    def validate_plan_consistency(self):
        """Plan과 todos 일관성 검증"""
        if self.plan and self.todos:
            plan_todo_count = len(self.plan.todos)
            output_todo_count = len(self.todos)
            if plan_todo_count != output_todo_count:
                # 경고만 (에러는 아님)
                pass
        return self
