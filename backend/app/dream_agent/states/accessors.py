"""State Accessors - AgentState 접근 유틸리티 (P0-3.1)

state.get() 직접 호출을 대체하는 타입 안전한 accessor 함수들.
일관된 기본값 처리와 타입 힌트 제공.

사용 예:
    # Before
    todos = state.get("todos", [])

    # After
    from backend.app.dream_agent.states.accessors import get_todos
    todos = get_todos(state)
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import AgentState
    from .todo import TodoItem


# ============================================================
# 기본 Accessors (7개)
# ============================================================

def get_todos(state: "AgentState") -> List["TodoItem"]:
    """todos 리스트 반환

    Args:
        state: AgentState

    Returns:
        TodoItem 리스트 (없으면 빈 리스트)
    """
    return state.get("todos", [])


def get_user_input(state: "AgentState") -> str:
    """사용자 입력 반환

    Args:
        state: AgentState

    Returns:
        user_input 문자열 (없으면 빈 문자열)
    """
    return state.get("user_input", "")


def get_intent(state: "AgentState") -> Dict[str, Any]:
    """Cognitive layer의 intent 결과 반환

    Args:
        state: AgentState

    Returns:
        intent 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("intent", {})


def get_current_context(state: "AgentState") -> str:
    """현재 컨텍스트 반환

    Args:
        state: AgentState

    Returns:
        current_context 문자열 (없으면 빈 문자열)
    """
    return state.get("current_context", "")


def get_session_id(state: "AgentState") -> str:
    """세션 ID 반환

    Args:
        state: AgentState

    Returns:
        session_id 문자열 (없으면 "default")
    """
    return state.get("session_id", "default")


def get_language(state: "AgentState") -> str:
    """언어 설정 반환

    Args:
        state: AgentState

    Returns:
        language 문자열 (없으면 "KOR")
    """
    return state.get("language", "KOR")


def get_requires_hitl(state: "AgentState") -> bool:
    """HITL 필요 여부 반환

    Args:
        state: AgentState

    Returns:
        requires_hitl 불리언 (없으면 False)
    """
    return state.get("requires_hitl", False)


# ============================================================
# ML Accessors (4개)
# ============================================================

def get_current_ml_todo_id(state: "AgentState") -> Optional[str]:
    """현재 실행 중인 ML todo ID 반환

    Args:
        state: AgentState

    Returns:
        current_ml_todo_id 또는 None
    """
    return state.get("current_ml_todo_id")


def get_intermediate_results(state: "AgentState") -> Dict[str, Any]:
    """ML Stage 간 중간 결과 반환

    Args:
        state: AgentState

    Returns:
        intermediate_results 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("intermediate_results", {})


def get_ml_result(state: "AgentState") -> Dict[str, Any]:
    """ML Execution 결과 반환

    Args:
        state: AgentState

    Returns:
        ml_result 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("ml_result", {})


def get_next_ml_tool(state: "AgentState") -> Optional[str]:
    """다음 ML 도구 이름 반환

    Args:
        state: AgentState

    Returns:
        next_ml_tool 문자열 또는 None
    """
    return state.get("next_ml_tool")


# ============================================================
# Biz Accessors (12개)
# ============================================================

def get_current_biz_todo_id(state: "AgentState") -> Optional[str]:
    """현재 실행 중인 Biz todo ID 반환

    Args:
        state: AgentState

    Returns:
        current_biz_todo_id 또는 None
    """
    return state.get("current_biz_todo_id")


def get_biz_result(state: "AgentState") -> Dict[str, Any]:
    """Biz Execution 결과 반환

    Args:
        state: AgentState

    Returns:
        biz_result 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("biz_result", {})


def get_storyboard(state: "AgentState") -> Optional[Any]:
    """비디오 스토리보드 반환

    Args:
        state: AgentState

    Returns:
        storyboard 또는 None
    """
    return state.get("storyboard")


def get_validation_result(state: "AgentState") -> Dict[str, Any]:
    """검증 결과 반환

    Args:
        state: AgentState

    Returns:
        validation_result 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("validation_result", {})


def get_resolution(state: "AgentState") -> str:
    """비디오 해상도 반환

    Args:
        state: AgentState

    Returns:
        resolution 문자열 (없으면 "1080p")
    """
    return state.get("resolution", "1080p")


def get_fps(state: "AgentState") -> int:
    """비디오 FPS 반환

    Args:
        state: AgentState

    Returns:
        fps 정수 (없으면 30)
    """
    return state.get("fps", 30)


def get_scene_prompts(state: "AgentState") -> List[Any]:
    """씬 프롬프트 리스트 반환

    Args:
        state: AgentState

    Returns:
        scene_prompts 리스트 (없으면 빈 리스트)
    """
    return state.get("scene_prompts", [])


def get_comfyui_result(state: "AgentState") -> Optional[Any]:
    """ComfyUI 결과 반환

    Args:
        state: AgentState

    Returns:
        comfyui_result 또는 None
    """
    return state.get("comfyui_result")


def get_insights(state: "AgentState") -> Dict[str, Any]:
    """분석 인사이트 반환

    Args:
        state: AgentState

    Returns:
        insights 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("insights", {})


def get_report_structure(state: "AgentState") -> Dict[str, Any]:
    """보고서 구조 반환

    Args:
        state: AgentState

    Returns:
        report_structure 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("report_structure", {})


def get_output_format(state: "AgentState") -> str:
    """출력 포맷 반환

    Args:
        state: AgentState

    Returns:
        output_format 문자열 (없으면 "json")
    """
    return state.get("output_format", "json")


def get_error(state: "AgentState") -> Optional[str]:
    """에러 메시지 반환

    Args:
        state: AgentState

    Returns:
        error 문자열 또는 None
    """
    return state.get("error")


# ============================================================
# 기타 Accessors (2개)
# ============================================================

def get_plan(state: "AgentState") -> Dict[str, Any]:
    """Planning layer 결과 반환

    Args:
        state: AgentState

    Returns:
        plan 딕셔너리 (없으면 빈 딕셔너리)
    """
    return state.get("plan", {})


def get_dialogue_context(state: "AgentState") -> Optional[Any]:
    """대화 컨텍스트 반환

    Args:
        state: AgentState

    Returns:
        dialogue_context 또는 None
    """
    return state.get("dialogue_context")


# ============================================================
# 추가 Accessors (실제 코드에서 사용되는 패턴)
# ============================================================

def get_next_layer(state: "AgentState") -> Optional[str]:
    """다음 라우팅 대상 레이어 반환

    Args:
        state: AgentState

    Returns:
        next_layer 문자열 또는 None
    """
    return state.get("next_layer")


def get_plan_obj(state: "AgentState") -> Optional[Any]:
    """Plan 객체 반환 (SSOT)

    Args:
        state: AgentState

    Returns:
        plan_obj 또는 None
    """
    return state.get("plan_obj")


def get_workflow(state: "AgentState") -> Optional[Any]:
    """ComfyUI 워크플로우 반환

    Args:
        state: AgentState

    Returns:
        workflow 또는 None
    """
    return state.get("workflow")


def get_use_mock(state: "AgentState") -> bool:
    """Mock 모드 사용 여부 반환

    Args:
        state: AgentState

    Returns:
        use_mock 불리언 (없으면 True)
    """
    return state.get("use_mock", True)


def get_response(state: "AgentState") -> str:
    """Response layer 결과 반환

    Args:
        state: AgentState

    Returns:
        response 문자열 (없으면 빈 문자열)
    """
    return state.get("response", "")


def get_target_context(state: "AgentState") -> str:
    """목표 컨텍스트 반환

    Args:
        state: AgentState

    Returns:
        target_context 문자열 (없으면 빈 문자열)
    """
    return state.get("target_context", "")


# ============================================================
# Convenience Functions
# ============================================================

def get_completed_todo_count(state: "AgentState") -> int:
    """완료된 todo 개수 반환

    Args:
        state: AgentState

    Returns:
        완료된 todo 개수
    """
    todos = get_todos(state)
    return len([t for t in todos if t.status == "completed"])


def get_pending_todo_count(state: "AgentState") -> int:
    """대기 중인 todo 개수 반환

    Args:
        state: AgentState

    Returns:
        대기 중인 todo 개수
    """
    todos = get_todos(state)
    return len([t for t in todos if t.status == "pending"])


def get_todos_by_layer(state: "AgentState", layer: str) -> List["TodoItem"]:
    """레이어별 todos 반환

    Args:
        state: AgentState
        layer: 레이어 이름 ("ml_execution", "biz_execution" 등)

    Returns:
        해당 레이어의 TodoItem 리스트
    """
    todos = get_todos(state)
    return [t for t in todos if t.layer == layer]


def get_todo_by_id(state: "AgentState", todo_id: str) -> Optional["TodoItem"]:
    """ID로 todo 조회

    Args:
        state: AgentState
        todo_id: 조회할 todo ID

    Returns:
        TodoItem 또는 None
    """
    todos = get_todos(state)
    for todo in todos:
        if todo.id == todo_id:
            return todo
    return None


__all__ = [
    # 기본 Accessors
    "get_todos",
    "get_user_input",
    "get_intent",
    "get_current_context",
    "get_session_id",
    "get_language",
    "get_requires_hitl",
    # ML Accessors
    "get_current_ml_todo_id",
    "get_intermediate_results",
    "get_ml_result",
    "get_next_ml_tool",
    # Biz Accessors
    "get_current_biz_todo_id",
    "get_biz_result",
    "get_storyboard",
    "get_validation_result",
    "get_resolution",
    "get_fps",
    "get_scene_prompts",
    "get_comfyui_result",
    "get_insights",
    "get_report_structure",
    "get_output_format",
    "get_error",
    # 기타 Accessors
    "get_plan",
    "get_dialogue_context",
    # 추가 Accessors
    "get_next_layer",
    "get_plan_obj",
    "get_workflow",
    "get_use_mock",
    "get_response",
    "get_target_context",
    # Convenience Functions
    "get_completed_todo_count",
    "get_pending_todo_count",
    "get_todos_by_layer",
    "get_todo_by_id",
]
