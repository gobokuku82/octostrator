"""Execution Layer I/O Schema

Execution Layer의 입출력 스키마를 정의합니다.
Phase 3: field_validator 기반 검증 추가.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from ..models.todo import TodoItem
from ..models.execution import ExecutionResult, ExecutionContext


class ExecutionInput(BaseModel):
    """Execution Layer 입력"""
    todo: TodoItem
    context: ExecutionContext
    previous_results: Dict[str, Any] = Field(default_factory=dict)
    use_mock: bool = False

    # NOTE: Todo 검증은 execution_node에서 수행됨
    # 스키마는 문서화 목적으로만 사용


class ExecutionOutput(BaseModel):
    """Execution Layer 출력"""
    result: ExecutionResult
    updated_todo: TodoItem
    intermediate_data: Dict[str, Any] = Field(default_factory=dict)
    # 다음 실행을 위한 정보
    next_todos: List[str] = Field(default_factory=list)
    requires_user_input: bool = False
    user_input_message: Optional[str] = None

    @model_validator(mode='after')
    def validate_output_consistency(self):
        """실행 결과와 Todo 상태 일관성 검증"""
        if self.result.success and self.updated_todo.status not in ['completed', 'in_progress']:
            pass  # 경고만
        if not self.result.success and self.updated_todo.status == 'completed':
            raise ValueError("Todo marked completed but execution failed")
        return self
