"""Base State - 에이전트 공유 상태"""

from __future__ import annotations

from typing import Annotated, Optional, Any
from typing_extensions import TypedDict

from ..models.todo import TodoItem
from ..models.plan import Plan
from ..models.resource import ResourcePlan
from ..models.execution_graph import ExecutionGraph
from .reducers import todo_reducer, ml_result_reducer, biz_result_reducer


class AgentState(TypedDict, total=False):
    """
    에이전트 공유 상태

    모든 레이어에서 공유하는 단일 상태.
    Router가 이 상태를 기반으로 라우팅 결정.
    """
    # 사용자 입력
    user_input: str
    language: str  # "KOR", "EN", "JP" (기본값: "KOR")

    # 컨텍스트
    current_context: str  # 현재 상황/데이터
    target_context: str   # 목표/의도

    # Todo 관리 (ID 기반 병합)
    todos: Annotated[list[TodoItem], todo_reducer]

    # 레이어별 결과
    intent: dict          # Cognitive 레이어 결과
    plan: dict            # Planning 레이어 결과
    ml_result: Annotated[dict, ml_result_reducer]  # ML Execution 레이어 결과
    biz_result: Annotated[dict, biz_result_reducer]  # Biz Execution 레이어 결과
    response: str         # Response 레이어 결과

    # 워크플로우 제어
    next_layer: Optional[str]  # 다음 라우팅 대상
    requires_hitl: bool        # HITL 필요 여부
    error: Optional[str]       # 에러 메시지

    # Subgraph 실행 제어 (Phase 0에서 추가, Phase 1에서 사용)
    current_ml_todo_id: Optional[str]   # ML Subgraph에서 현재 실행 중인 todo ID
    current_biz_todo_id: Optional[str]  # Biz Subgraph에서 현재 실행 중인 todo ID
    next_ml_tool: Optional[str]         # ML Router가 선택한 다음 tool 이름
    next_biz_tool: Optional[str]        # Biz Router가 선택한 다음 tool 이름

    # Phase 2: Planning Layer 고도화 필드
    session_id: Optional[str]                      # 세션 ID (Plan 추적용)
    plan_obj: Optional["Plan"]                     # Plan 객체 (SSOT for todos)
    plan_id: Optional[str]                         # Plan ID
    resource_plan: Optional["ResourcePlan"]        # ResourcePlan 객체
    execution_graph: Optional["ExecutionGraph"]    # ExecutionGraph 객체
    cost_estimate: Optional[dict]                  # 비용 예상 정보
    langgraph_commands: Optional[list]             # LangGraph 실행 명령어 리스트
    mermaid_diagram: Optional[str]                 # Mermaid 다이어그램 문자열

    # Phase 3: ML Executor 세분화 필드
    intermediate_results: Optional[dict]  # Stage 간 중간 결과 저장 (collected_reviews, preprocessed_reviews, etc.)

    # Phase 2 HITL 강화 필드
    hitl_mode: Optional[str]              # "running" | "paused" | "plan_edit" | "input_request" | "approval_wait"
    hitl_requested_field: Optional[str]   # 입력 요청 필드명
    hitl_message: Optional[str]           # HITL 메시지 (사용자에게 표시)
    hitl_timestamp: Optional[str]         # HITL 상태 변경 시점
    hitl_pause_reason: Optional[str]      # "user_request" | "input_required" | "approval_required" | "error_recovery"
    hitl_pending_input: Optional[dict]    # 대기 중인 입력 요청 정보


def create_initial_state(user_input: str, language: str = "KOR", session_id: str = None) -> AgentState:
    """초기 상태 생성"""
    return AgentState(
        user_input=user_input,
        language=language,
        current_context="",
        target_context="",
        todos=[],
        intent={},
        plan={},
        ml_result={},
        biz_result={},
        response="",
        next_layer=None,
        requires_hitl=False,
        error=None,
        intermediate_results={},  # Phase 3: Stage 간 중간 결과 저장
        # Phase 2 HITL 강화 필드
        session_id=session_id,
        hitl_mode="running",
        hitl_requested_field=None,
        hitl_message=None,
        hitl_timestamp=None,
        hitl_pause_reason=None,
        hitl_pending_input=None,
    )
