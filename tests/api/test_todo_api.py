"""Todo API 테스트

Phase 2 Todo 관리 API 엔드포인트 테스트 (6개)
- POST /{thread_id}/todos
- DELETE /{thread_id}/todos/{todo_id}
- PUT /{thread_id}/todos/{todo_id}
- PUT /{thread_id}/todos/reorder
- POST /{thread_id}/retry/{todo_id}
- PUT /{thread_id}/todos/{todo_id}/agent

Author: AI PT Manager Development Team
Date: 2025-11-06
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.main import app


@pytest.fixture
def mock_checkpointer():
    """Mock checkpointer fixture"""
    with patch('backend.app.api.todos.create_checkpointer') as mock:
        mock_cp = AsyncMock()
        mock.return_value = mock_cp
        yield mock_cp


@pytest.fixture
def mock_graph_with_todos():
    """Mock graph with todos fixture"""
    with patch('backend.app.api.todos.build_supervisor_graph') as mock:
        mock_g = MagicMock()

        # Mock state with todos
        mock_state = MagicMock()
        mock_state.values = {
            "session_id": "test-session",
            "todos": [
                {
                    "id": "todo-1",
                    "step": 1,
                    "task": "Task 1",
                    "status": "completed",
                    "agent": "DietAgent"
                },
                {
                    "id": "todo-2",
                    "step": 2,
                    "task": "Task 2",
                    "status": "failed",
                    "agent": "WorkoutAgent",
                    "error": "Some error",
                    "retry_count": 0
                },
                {
                    "id": "todo-3",
                    "step": 3,
                    "task": "Task 3",
                    "status": "pending",
                    "agent": "ReportAgent"
                }
            ]
        }

        mock_g.aget_state = AsyncMock(return_value=mock_state)
        mock_g.aupdate_state = AsyncMock()

        mock.return_value = mock_g
        yield mock_g


# === Test POST /{thread_id}/todos ===

@pytest.mark.asyncio
async def test_add_todo_success(mock_checkpointer, mock_graph_with_todos):
    """Todo 추가 성공 테스트"""
    new_todo = {
        "task": "New Task",
        "agent": "DietAgent",
        "priority": 1
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/todos",
            json=new_todo
        )

    assert response.status_code == 200
    data = response.json()

    # 응답 검증
    assert data["success"] is True
    assert "added successfully" in data["message"].lower()
    assert data["todo"]["task"] == "New Task"
    assert data["todo"]["agent"] == "DietAgent"
    assert data["todo"]["status"] == "pending"

    # aupdate_state가 2번 호출되어야 함 (todo add + user_interaction)
    assert mock_graph_with_todos.aupdate_state.call_count == 2


@pytest.mark.asyncio
async def test_add_todo_minimal(mock_checkpointer, mock_graph_with_todos):
    """최소 정보로 Todo 추가 테스트"""
    new_todo = {
        "task": "Minimal Task"
        # agent, priority 없음
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/todos",
            json=new_todo
        )

    assert response.status_code == 200
    data = response.json()
    assert data["todo"]["task"] == "Minimal Task"
    assert data["todo"]["status"] == "pending"


# === Test DELETE /{thread_id}/todos/{todo_id} ===

@pytest.mark.asyncio
async def test_delete_todo_success(mock_checkpointer, mock_graph_with_todos):
    """Todo 삭제 성공 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            "/api/sessions/test-session/todos/todo-2"
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "deleted successfully" in data["message"].lower()
    assert data["deleted_id"] == "todo-2"

    # aupdate_state가 2번 호출 (delete + user_interaction)
    assert mock_graph_with_todos.aupdate_state.call_count == 2


@pytest.mark.asyncio
async def test_delete_todo_not_found(mock_checkpointer, mock_graph_with_todos):
    """존재하지 않는 Todo 삭제 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(
            "/api/sessions/test-session/todos/nonexistent-id"
        )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# === Test PUT /{thread_id}/todos/{todo_id} ===

@pytest.mark.asyncio
async def test_update_todo_success(mock_checkpointer, mock_graph_with_todos):
    """Todo 수정 성공 테스트"""
    update_data = {
        "task": "Updated Task",
        "status": "in_progress"
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/todo-3",
            json=update_data
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "updated successfully" in data["message"].lower()
    assert "old_todo" in data
    assert "new_todo" in data

    # aupdate_state가 2번 호출
    assert mock_graph_with_todos.aupdate_state.call_count == 2


@pytest.mark.asyncio
async def test_update_todo_partial(mock_checkpointer, mock_graph_with_todos):
    """일부 필드만 수정 테스트"""
    update_data = {
        "status": "completed"
        # task는 수정하지 않음
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/todo-3",
            json=update_data
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_todo_not_found(mock_checkpointer, mock_graph_with_todos):
    """존재하지 않는 Todo 수정 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/nonexistent",
            json={"task": "Updated"}
        )

    assert response.status_code == 404


# === Test PUT /{thread_id}/todos/reorder ===

@pytest.mark.asyncio
async def test_reorder_todos_success(mock_checkpointer, mock_graph_with_todos):
    """Todo 순서 변경 성공 테스트"""
    reorder_data = {
        "todo_ids": ["todo-3", "todo-1", "todo-2"]
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/reorder",
            json=reorder_data
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "reordered successfully" in data["message"].lower()
    assert len(data["new_order"]) == 3

    # Step 번호 검증
    assert data["new_order"][0]["id"] == "todo-3"
    assert data["new_order"][0]["step"] == 1
    assert data["new_order"][1]["id"] == "todo-1"
    assert data["new_order"][1]["step"] == 2


@pytest.mark.asyncio
async def test_reorder_todos_invalid_id(mock_checkpointer, mock_graph_with_todos):
    """잘못된 Todo ID로 순서 변경 테스트"""
    reorder_data = {
        "todo_ids": ["todo-1", "nonexistent-id"]
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/reorder",
            json=reorder_data
        )

    assert response.status_code == 400


# === Test POST /{thread_id}/retry/{todo_id} ===

@pytest.mark.asyncio
async def test_retry_todo_success(mock_checkpointer, mock_graph_with_todos):
    """실패한 Todo 재시도 성공 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/retry/todo-2"
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "retry queued" in data["message"].lower()
    assert data["todo"]["id"] == "todo-2"
    assert data["todo"]["status"] == "pending"
    assert data["todo"]["retry_count"] == 1

    # aupdate_state가 2번 호출
    assert mock_graph_with_todos.aupdate_state.call_count == 2


@pytest.mark.asyncio
async def test_retry_todo_not_failed(mock_checkpointer, mock_graph_with_todos):
    """실패하지 않은 Todo 재시도 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/retry/todo-1"  # completed 상태
        )

    assert response.status_code == 400
    assert "cannot retry" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_retry_todo_not_found(mock_checkpointer, mock_graph_with_todos):
    """존재하지 않는 Todo 재시도 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/retry/nonexistent"
        )

    assert response.status_code == 404


# === Test PUT /{thread_id}/todos/{todo_id}/agent ===

@pytest.mark.asyncio
async def test_change_todo_agent_success(mock_checkpointer, mock_graph_with_todos):
    """Todo Agent 변경 성공 테스트"""
    agent_data = {
        "new_agent": "HealthAssessmentAgent"
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/todo-3/agent",
            json=agent_data
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "agent changed" in data["message"].lower()
    assert data["old_agent"] == "ReportAgent"
    assert data["new_agent"] == "HealthAssessmentAgent"

    # aupdate_state가 2번 호출
    assert mock_graph_with_todos.aupdate_state.call_count == 2


@pytest.mark.asyncio
async def test_change_todo_agent_not_found(mock_checkpointer, mock_graph_with_todos):
    """존재하지 않는 Todo의 Agent 변경 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/todos/nonexistent/agent",
            json={"new_agent": "DietAgent"}
        )

    assert response.status_code == 404


# === Integration Tests ===

@pytest.mark.asyncio
async def test_full_todo_management_workflow(mock_checkpointer, mock_graph_with_todos):
    """전체 Todo 관리 워크플로우 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Todo 추가
        add_resp = await client.post(
            "/api/sessions/test-session/todos",
            json={"task": "New Task", "agent": "DietAgent"}
        )
        assert add_resp.status_code == 200

        # 2. Todo 수정
        update_resp = await client.put(
            "/api/sessions/test-session/todos/todo-3",
            json={"task": "Modified Task"}
        )
        assert update_resp.status_code == 200

        # 3. Agent 변경
        agent_resp = await client.put(
            "/api/sessions/test-session/todos/todo-3/agent",
            json={"new_agent": "WorkoutAgent"}
        )
        assert agent_resp.status_code == 200

        # 4. 순서 변경
        reorder_resp = await client.put(
            "/api/sessions/test-session/todos/reorder",
            json={"todo_ids": ["todo-2", "todo-1", "todo-3"]}
        )
        assert reorder_resp.status_code == 200

        # 5. 재시도
        retry_resp = await client.post(
            "/api/sessions/test-session/retry/todo-2"
        )
        assert retry_resp.status_code == 200

        # 6. Todo 삭제
        delete_resp = await client.delete(
            "/api/sessions/test-session/todos/todo-1"
        )
        assert delete_resp.status_code == 200


@pytest.mark.asyncio
async def test_todo_lifecycle(mock_checkpointer, mock_graph_with_todos):
    """Todo 생명주기 테스트: pending → in_progress → failed → retry → completed"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 새 Todo 추가 (pending)
        add_resp = await client.post(
            "/api/sessions/test-session/todos",
            json={"task": "Lifecycle Test"}
        )
        assert add_resp.json()["todo"]["status"] == "pending"

        # 2. 상태를 in_progress로 변경
        progress_resp = await client.put(
            "/api/sessions/test-session/todos/todo-3",
            json={"status": "in_progress"}
        )
        assert progress_resp.status_code == 200

        # 3. 상태를 failed로 변경
        failed_resp = await client.put(
            "/api/sessions/test-session/todos/todo-3",
            json={"status": "failed"}
        )
        assert failed_resp.status_code == 200

        # 4. 재시도 (pending으로 복귀)
        # Note: todo-2가 이미 failed 상태이므로 이를 사용
        retry_resp = await client.post(
            "/api/sessions/test-session/retry/todo-2"
        )
        assert retry_resp.json()["todo"]["status"] == "pending"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
