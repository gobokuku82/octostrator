"""execution_node.py - 메인 그래프 실행 노드

LangGraph와 통합되는 execution 노드를 제공합니다.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from langgraph.types import Command

from .supervisor import ExecutionSupervisor, get_execution_supervisor, TOOL_TO_EXECUTOR
from .core.base_executor import ExecutionResult

logger = logging.getLogger(__name__)


async def execution_node(state: Dict[str, Any]) -> Command:
    """통합 실행 노드

    Ready 상태의 Todo를 **한 개씩** 실행하고 결과를 State에 반영합니다.
    한 번에 하나의 Todo만 실행하여 각 완료 후 WebSocket 업데이트가 전송되도록 합니다.

    Args:
        state: AgentState (dict 형태)
            - todos: TodoItem 리스트
            - language: 언어 코드

    Returns:
        Command with updated state
    """
    logger.info("[execution_node] Starting execution")

    todos = state.get("todos", [])
    if not todos:
        logger.info("[execution_node] No todos to execute")
        return Command(
            update={"execution_result": {"status": "no_todos", "results": {}}},
            goto="response",
        )

    # Ready 상태의 Todo 필터링
    ready_todos = _get_ready_todos(todos)
    if not ready_todos:
        logger.info("[execution_node] No ready todos")
        return Command(
            update={"execution_result": {"status": "no_ready_todos", "results": {}}},
            goto="response",
        )

    # ExecutionSupervisor로 실행
    supervisor = get_execution_supervisor()

    # 이전 실행 결과를 컨텍스트로 전달
    context = _build_context_from_state(state)

    # **한 개의 Todo만 실행** (실시간 WebSocket 업데이트를 위해)
    # priority가 높은 것 먼저 실행 (10이 가장 높음)
    sorted_ready_todos = sorted(
        ready_todos,
        key=lambda t: getattr(t, "priority", 0) if hasattr(t, "priority") else t.get("priority", 0),
        reverse=True  # 높은 priority 먼저
    )
    current_todo = sorted_ready_todos[0]
    todo_id = getattr(current_todo, "id", None) or (current_todo.get("id") if hasattr(current_todo, "get") else None)
    todo_task = getattr(current_todo, "task", None) or (current_todo.get("task") if hasattr(current_todo, "get") else None)
    logger.info(f"[execution_node] Executing single todo: {todo_id} (task: {todo_task})")

    # 단일 Todo 실행
    result = await supervisor.execute_todo(current_todo, context)
    results = {todo_id or str(current_todo): result}

    # 결과 처리
    updated_todos = _update_todos_with_results(todos, results)
    execution_result = _build_execution_result(results, supervisor)

    # 다음 라우팅 결정
    next_node = _determine_next_node(updated_todos, results)

    logger.info(f"[execution_node] Single todo completed. Next: {next_node}")

    return Command(
        update={
            "todos": updated_todos,
            "execution_result": execution_result,
        },
        goto=next_node,
    )


async def data_execution_node(state: Dict[str, Any]) -> Command:
    """데이터 실행 노드 (Data Executor 전용)

    collector, preprocessor, google_trends 도구를 실행합니다.
    """
    return await _execute_by_category(state, "data_executor", ["collector", "preprocessor", "google_trends"])


async def insight_execution_node(state: Dict[str, Any]) -> Command:
    """인사이트 실행 노드 (Insight Executor 전용)

    sentiment, keyword, hashtag, problem, competitor, insight 도구를 실행합니다.
    """
    return await _execute_by_category(
        state,
        "insight_executor",
        ["sentiment", "keyword", "hashtag", "problem", "competitor", "insight"],
    )


async def content_execution_node(state: Dict[str, Any]) -> Command:
    """콘텐츠 실행 노드 (Content Executor 전용)

    report, video, ad_creative 도구를 실행합니다.
    """
    return await _execute_by_category(state, "content_executor", ["report", "video", "ad_creative"])


async def ops_execution_node(state: Dict[str, Any]) -> Command:
    """운영 실행 노드 (Ops Executor 전용)

    sales, inventory, dashboard 도구를 실행합니다.
    """
    return await _execute_by_category(state, "ops_executor", ["sales", "inventory", "dashboard"])


async def _execute_by_category(
    state: Dict[str, Any],
    executor_name: str,
    tools: List[str],
) -> Command:
    """카테고리별 실행 헬퍼

    Args:
        state: AgentState
        executor_name: Executor 이름
        tools: 해당 Executor가 처리할 도구 목록

    Returns:
        Command with updated state
    """
    logger.info(f"[{executor_name}] Starting execution")

    todos = state.get("todos", [])
    ready_todos = _get_ready_todos_by_tools(todos, tools)

    if not ready_todos:
        logger.info(f"[{executor_name}] No ready todos for tools: {tools}")
        return Command(
            update={f"{executor_name}_result": {"status": "no_todos", "results": {}}},
            goto=_get_next_node_after_executor(executor_name),
        )

    # ExecutionSupervisor로 실행
    supervisor = get_execution_supervisor()
    context = _build_context_from_state(state)
    results = await supervisor.execute_todos(ready_todos, context)

    # 결과 처리
    updated_todos = _update_todos_with_results(todos, results)
    execution_result = _build_execution_result(results, supervisor)

    # ML/Biz result 업데이트
    result_key = _get_result_key_for_executor(executor_name)

    logger.info(f"[{executor_name}] Completed")

    return Command(
        update={
            "todos": updated_todos,
            result_key: execution_result,
        },
        goto=_get_next_node_after_executor(executor_name),
    )


def _get_ready_todos(todos: List[Any]) -> List[Any]:
    """Ready 상태의 Todo 필터링

    Args:
        todos: 전체 Todo 리스트

    Returns:
        Ready 상태의 Todo 리스트
    """
    ready = []
    for todo in todos:
        status = getattr(todo, "status", None)
        if status is None and hasattr(todo, "get"):
            status = todo.get("status", "pending")

        if status == "pending":
            # 의존성 체크
            if not _has_unresolved_dependencies(todo, todos):
                ready.append(todo)

    return ready


def _get_ready_todos_by_tools(todos: List[Any], tools: List[str]) -> List[Any]:
    """특정 도구에 해당하는 Ready Todo 필터링

    Args:
        todos: 전체 Todo 리스트
        tools: 필터링할 도구 목록

    Returns:
        Ready 상태이고 해당 도구를 사용하는 Todo 리스트
    """
    ready = []
    for todo in todos:
        status = getattr(todo, "status", None)
        if status is None and hasattr(todo, "get"):
            status = todo.get("status", "pending")

        if status != "pending":
            continue

        # 도구 확인
        tool_name = _get_tool_name(todo)
        if tool_name and tool_name in tools:
            # 의존성 체크
            if not _has_unresolved_dependencies(todo, todos):
                ready.append(todo)

    return ready


def _has_unresolved_dependencies(todo: Any, all_todos: List[Any]) -> bool:
    """미해결 의존성 존재 여부 확인

    의존성 해석:
    - UUID 형식: todo ID로 직접 매칭
    - 문자열(tool name): 해당 tool을 사용하는 completed todo로 매칭

    Args:
        todo: 확인할 Todo
        all_todos: 전체 Todo 리스트

    Returns:
        미해결 의존성 존재 여부
    """
    depends_on = []

    if hasattr(todo, "metadata"):
        metadata = todo.metadata
        if hasattr(metadata, "dependency") and metadata.dependency:
            depends_on = metadata.dependency.depends_on or []

    if not depends_on:
        return False

    # 완료된 todo들의 ID와 tool name 수집
    completed_ids = set()
    completed_tools = set()

    for t in all_todos:
        t_id = getattr(t, "id", None) or (t.get("id") if hasattr(t, "get") else None)
        t_status = getattr(t, "status", None) or (t.get("status") if hasattr(t, "get") else None)

        if t_status == "completed" and t_id:
            completed_ids.add(t_id)

            # Tool name 추출
            t_metadata = getattr(t, "metadata", None)
            if t_metadata is None and hasattr(t, "get"):
                t_metadata = t.get("metadata")

            if t_metadata:
                t_execution = getattr(t_metadata, "execution", None)
                if t_execution is None and hasattr(t_metadata, "get"):
                    t_execution = t_metadata.get("execution")

                if t_execution:
                    tool_name = getattr(t_execution, "tool", None)
                    if tool_name is None and hasattr(t_execution, "get"):
                        tool_name = t_execution.get("tool")
                    if tool_name:
                        completed_tools.add(tool_name)

    # 의존성 체크: ID 또는 tool name으로 매칭
    for dep in depends_on:
        # UUID(todo ID)로 체크
        if dep in completed_ids:
            continue
        # Tool name으로 체크
        if dep in completed_tools:
            continue
        # 둘 다 아니면 미해결 의존성
        return True

    return False


def _get_tool_name(todo: Any) -> Optional[str]:
    """Todo에서 도구 이름 추출"""
    if hasattr(todo, "metadata"):
        metadata = todo.metadata
        if hasattr(metadata, "execution") and metadata.execution:
            return metadata.execution.tool

    if hasattr(todo, "tool"):
        return todo.tool

    if hasattr(todo, "get"):
        metadata = todo.get("metadata", {})
        if isinstance(metadata, dict):
            execution = metadata.get("execution", {})
            if isinstance(execution, dict):
                return execution.get("tool")

    return None


def _build_context_from_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """State에서 실행 컨텍스트 추출

    Args:
        state: AgentState

    Returns:
        실행 컨텍스트 딕셔너리
    """
    context = {}

    # 이전 실행 결과 포함
    if "ml_result" in state:
        context.update(state["ml_result"])
    if "biz_result" in state:
        context.update(state["biz_result"])
    if "execution_result" in state:
        prev_result = state["execution_result"]
        if isinstance(prev_result, dict) and "results" in prev_result:
            for result_data in prev_result["results"].values():
                if isinstance(result_data, dict):
                    context.update(result_data)

    # 사용자 입력 정보
    if "user_input" in state:
        context["user_input"] = state["user_input"]
    if "language" in state:
        context["language"] = state["language"]

    return context


def _update_todos_with_results(
    todos: List[Any],
    results: Dict[str, ExecutionResult],
) -> List[Any]:
    """실행 결과로 Todo 상태 업데이트

    Args:
        todos: Todo 리스트
        results: 실행 결과 딕셔너리

    Returns:
        업데이트된 Todo 리스트
    """
    updated = []

    for todo in todos:
        todo_id = getattr(todo, "id", None)
        if todo_id is None and hasattr(todo, "get"):
            todo_id = todo.get("id")

        if todo_id and todo_id in results:
            result = results[todo_id]

            # Todo 상태 업데이트
            if hasattr(todo, "status"):
                todo.status = "completed" if result.success else "failed"
            elif hasattr(todo, "__setitem__"):
                todo["status"] = "completed" if result.success else "failed"

            # 메타데이터 업데이트
            if hasattr(todo, "metadata"):
                metadata = todo.metadata
                if hasattr(metadata, "progress"):
                    if result.success:
                        metadata.progress.progress_percentage = 100
                        metadata.progress.completed_at = datetime.now()

        updated.append(todo)

    return updated


def _build_execution_result(
    results: Dict[str, ExecutionResult],
    supervisor: ExecutionSupervisor,
) -> Dict[str, Any]:
    """실행 결과 딕셔너리 생성

    Args:
        results: ExecutionResult 매핑
        supervisor: ExecutionSupervisor 인스턴스

    Returns:
        실행 결과 딕셔너리
    """
    result_data = {}
    errors = []

    for todo_id, result in results.items():
        if result.success:
            result_data[todo_id] = result.data
        else:
            errors.append({
                "todo_id": todo_id,
                "error": result.error,
            })

    return {
        "status": "completed" if not errors else "partial",
        "results": result_data,
        "errors": errors,
        "statistics": supervisor.get_statistics(),
    }


def _determine_next_node(
    todos: List[Any],
    results: Dict[str, ExecutionResult],
) -> str:
    """다음 노드 결정

    Args:
        todos: 업데이트된 Todo 리스트
        results: 실행 결과

    Returns:
        다음 노드 이름
    """
    # 남은 pending Todo 확인
    pending_todos = [
        t for t in todos
        if (getattr(t, "status", None) or (t.get("status") if hasattr(t, "get") else None)) == "pending"
    ]

    if not pending_todos:
        return "response"

    # 실행 가능한 Ready Todo가 있는지 확인
    ready_todos = _get_ready_todos(pending_todos)
    if ready_todos:
        # 도구 유형에 따라 적절한 노드로 라우팅
        first_tool = _get_tool_name(ready_todos[0])
        if first_tool:
            executor_name = TOOL_TO_EXECUTOR.get(first_tool)
            if executor_name:
                return _get_node_name_for_executor(executor_name)

        return "execution"  # 기본 execution 노드로

    return "response"


def _get_next_node_after_executor(executor_name: str) -> str:
    """Executor 실행 후 다음 노드 결정

    Args:
        executor_name: Executor 이름

    Returns:
        다음 노드 이름
    """
    # 실행 순서: data -> insight -> content -> ops -> response
    next_map = {
        "data_executor": "router",  # Router가 다음 실행 노드 결정
        "insight_executor": "router",
        "content_executor": "router",
        "ops_executor": "router",
    }
    return next_map.get(executor_name, "response")


def _get_result_key_for_executor(executor_name: str) -> str:
    """Executor별 결과 저장 키

    Args:
        executor_name: Executor 이름

    Returns:
        State 결과 키
    """
    key_map = {
        "data_executor": "ml_result",
        "insight_executor": "ml_result",
        "content_executor": "biz_result",
        "ops_executor": "biz_result",
    }
    return key_map.get(executor_name, "execution_result")


def _get_node_name_for_executor(executor_name: str) -> str:
    """Executor에 해당하는 노드 이름

    Args:
        executor_name: Executor 이름

    Returns:
        노드 이름
    """
    node_map = {
        "data_executor": "data_execution",
        "insight_executor": "insight_execution",
        "content_executor": "content_execution",
        "ops_executor": "ops_execution",
    }
    return node_map.get(executor_name, "execution")
