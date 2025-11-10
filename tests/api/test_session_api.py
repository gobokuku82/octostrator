"""Session API 테스트

Phase 2 Session API 엔드포인트 테스트 (4개)
- GET /{thread_id}/summary
- GET /{thread_id}/action/{step}
- PUT /{thread_id}/state
- POST /{thread_id}/interrupt

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
    with patch('backend.app.api.sessions.create_checkpointer') as mock:
        mock_cp = AsyncMock()
        mock.return_value = mock_cp
        yield mock_cp


@pytest.fixture
def mock_graph():
    """Mock graph fixture"""
    with patch('backend.app.api.sessions.build_supervisor_graph') as mock:
        mock_g = MagicMock()

        # Mock state
        mock_state = MagicMock()
        mock_state.values = {
            "session_id": "test-session",
            "created_at": "2025-11-06T10:00:00",
            "updated_at": "2025-11-06T10:05:00",
            "total_steps": 3,
            "plan_history": [{"version": 1}],
            "user_interactions": [{"type": "interrupt"}],
            "action_history": [
                {
                    "step": 1,
                    "action": "cognitive_layer_node",
                    "result": {"plan": {"goal": "test"}},
                    "duration_ms": 100,
                    "timestamp": "2025-11-06T10:00:00"
                }
            ],
            "todos": [
                {"id": "1", "task": "Task 1", "status": "completed"},
                {"id": "2", "task": "Task 2", "status": "pending"}
            ]
        }

        # Mock aget_state
        mock_g.aget_state = AsyncMock(return_value=mock_state)

        # Mock aupdate_state
        mock_g.aupdate_state = AsyncMock()

        mock.return_value = mock_g
        yield mock_g


# === Test GET /{thread_id}/summary ===

@pytest.mark.asyncio
async def test_get_session_summary_success(mock_checkpointer, mock_graph):
    """세션 요약 조회 성공 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sessions/test-session/summary")

    assert response.status_code == 200
    data = response.json()

    # 기본 필드 검증
    assert data["session_id"] == "test-session"
    assert "created_at" in data
    assert "total_steps" in data
    assert "todo_status" in data
    assert "actions_summary" in data

    # Mock 호출 검증
    mock_checkpointer.assert_called_once()
    mock_graph.aget_state.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_summary_not_found(mock_checkpointer):
    """세션을 찾을 수 없는 경우 테스트"""
    with patch('backend.app.api.sessions.build_supervisor_graph') as mock:
        mock_g = MagicMock()
        mock_state = MagicMock()
        mock_state.values = None  # 세션 없음
        mock_g.aget_state = AsyncMock(return_value=mock_state)
        mock.return_value = mock_g

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/sessions/nonexistent/summary")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# === Test GET /{thread_id}/action/{step} ===

@pytest.mark.asyncio
async def test_get_action_at_step_success(mock_checkpointer, mock_graph):
    """특정 step 조회 성공 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sessions/test-session/action/1")

    assert response.status_code == 200
    data = response.json()

    # 응답 구조 검증
    assert data["step"] == 1
    assert "action" in data
    assert data["action"]["action"] == "cognitive_layer_node"


@pytest.mark.asyncio
async def test_get_action_at_step_not_found(mock_checkpointer, mock_graph):
    """존재하지 않는 step 조회 테스트"""
    # StateHelpers.get_action_at_step이 None 반환하도록 mock
    with patch('backend.app.api.sessions.StateHelpers') as mock_helpers:
        mock_helpers.get_action_at_step.return_value = None

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/sessions/test-session/action/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# === Test PUT /{thread_id}/state ===

@pytest.mark.asyncio
async def test_update_session_state_success(mock_checkpointer, mock_graph):
    """State 업데이트 성공 테스트"""
    update_data = {
        "updates": {
            "plan_requires_todos": True,
            "need_todo_update": False
        }
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/sessions/test-session/state",
            json=update_data
        )

    assert response.status_code == 200
    data = response.json()

    # 응답 검증
    assert data["success"] is True
    assert "updated successfully" in data["message"].lower()
    assert data["updates"] == update_data["updates"]

    # aupdate_state가 2번 호출되어야 함 (state update + user_interaction)
    assert mock_graph.aupdate_state.call_count == 2


@pytest.mark.asyncio
async def test_update_session_state_not_found(mock_checkpointer):
    """존재하지 않는 세션 업데이트 테스트"""
    with patch('backend.app.api.sessions.build_supervisor_graph') as mock:
        mock_g = MagicMock()
        mock_state = MagicMock()
        mock_state.values = None
        mock_g.aget_state = AsyncMock(return_value=mock_state)
        mock.return_value = mock_g

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                "/api/sessions/nonexistent/state",
                json={"updates": {"test": "value"}}
            )

        assert response.status_code == 404


# === Test POST /{thread_id}/interrupt ===

@pytest.mark.asyncio
async def test_interrupt_session_success(mock_checkpointer, mock_graph):
    """세션 중단 성공 테스트"""
    interrupt_data = {
        "reason": "user_requested",
        "message": "Need to modify plan"
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/interrupt",
            json=interrupt_data
        )

    assert response.status_code == 200
    data = response.json()

    # 응답 검증
    assert data["success"] is True
    assert "interrupted successfully" in data["message"].lower()
    assert data["reason"] == "user_requested"
    assert "progress" in data

    # Progress 정보 검증
    assert "completed" in data["progress"]
    assert "total" in data["progress"]

    # aupdate_state 호출 검증 (user_interaction + requires_approval)
    mock_graph.aupdate_state.assert_called_once()


@pytest.mark.asyncio
async def test_interrupt_session_default_reason(mock_checkpointer, mock_graph):
    """기본 reason으로 중단 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/test-session/interrupt",
            json={}  # reason 없음
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reason"] == "user_requested"  # 기본값


# === Integration Tests ===

@pytest.mark.asyncio
async def test_full_session_workflow(mock_checkpointer, mock_graph):
    """전체 세션 워크플로우 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Summary 조회
        summary_resp = await client.get("/api/sessions/test-session/summary")
        assert summary_resp.status_code == 200

        # 2. 특정 action 조회
        action_resp = await client.get("/api/sessions/test-session/action/1")
        assert action_resp.status_code == 200

        # 3. State 업데이트
        update_resp = await client.put(
            "/api/sessions/test-session/state",
            json={"updates": {"test": "value"}}
        )
        assert update_resp.status_code == 200

        # 4. 세션 중단
        interrupt_resp = await client.post(
            "/api/sessions/test-session/interrupt",
            json={"reason": "test"}
        )
        assert interrupt_resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
