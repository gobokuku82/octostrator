"""
Octostrator State Definition

전체 시스템의 State 구조를 정의합니다.
MainOrchestratorState를 확장하여 History Tracking 기능을 추가합니다.

Author: Specialist Agent Development Team
Date: 2025-11-06
Version: 1.0
"""
from typing import Annotated, TypedDict, Optional, Any, List, Dict
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)


class OctostratorState(TypedDict, total=False):
    """
    Octostrator의 전체 State

    기존 MainOrchestratorState 기능 + History Tracking 추가
    """
    # ===== User Input =====
    user_query: str
    session_id: str
    output_format: str  # "chat" | "graph" | "report"

    # ===== Resources (Phase 3: Removed - Use Context API Instead) =====
    # Phase 3 변경: llm, checkpointer, context는 State에서 제거되었습니다.
    # 이유:
    #   1. msgpack 직렬화 불가능 (AsyncPostgresSaver, ChatOpenAI 인스턴스)
    #   2. Context API를 통해 접근해야 함 (RuntimeValue.runtime.context)
    #   3. context는 LangGraph config의 configurable에 포함되어야 함
    #
    # 노드에서 사용 방법:
    #   - LLM: context.llm_settings를 사용하여 생성
    #   - Checkpointer: 필요시 노드에서 직접 생성
    #   - Context: RuntimeValue.runtime.context로 접근

    # ===== Current State =====
    plan: dict
    todos: Annotated[List[Dict], merge_todos_smart]  # Reducer 사용!
    execution_results: dict
    final_response: str

    # ===== Flags =====
    plan_valid: bool
    requires_approval: bool
    error: Optional[str]

    # ===== Todo Manager 제어 (신규) =====
    plan_requires_todos: bool           # Cognitive가 설정 (Todo Manager 호출 필요 시)
    need_todo_update: bool              # Execute가 설정 (실행 중 Todo 추가 필요 시)
    user_requested_todo_update: bool    # API가 설정 (사용자가 Todo 수정 시)

    # ===== History Tracking (신규) =====

    # 작업 내역
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]
    # Example: [
    #   {"step": 1, "action": "cognitive_layer_node", "timestamp": "...", "result": {...}, "duration_ms": 250},
    #   {"step": 2, "action": "todo_layer_node", ...},
    # ]

    # Plan 변경 히스토리
    plan_history: Annotated[List[Dict], track_plan_changes]
    # Example: [
    #   {"version": 1, "plan": {...}, "timestamp": "...", "reason": "initial", "modified_by": "system"},
    #   {"version": 2, "plan": {...}, "timestamp": "...", "reason": "user_modification", "modified_by": "api"},
    # ]

    # 사용자 개입 기록
    user_interactions: Annotated[List[Dict], track_user_interactions]
    # Example: [
    #   {"type": "interrupt", "timestamp": "...", "reason": "...", "details": {...}},
    #   {"type": "modify_todo", "timestamp": "...", "details": {...}},
    # ]

    # ===== Metadata =====
    created_at: str  # 세션 생성 시각
    updated_at: str  # 마지막 업데이트 시각
    total_steps: int  # 총 실행된 step 수
