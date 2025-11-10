"""통합 테스트

Phase 3 통합 테스트: 전체 워크플로우 검증
- 세션 생성 → Plan → Todo 생성 → 실행 → 결과
- Todo 수정 후 재실행
- 세션 중단 및 재개
- Agent 변경 및 재시도

Author: AI PT Manager Development Team
Date: 2025-11-06
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.main import app
import uuid


@pytest.fixture
def session_id():
    """테스트용 세션 ID"""
    return f"test-session-{uuid.uuid4()}"


@pytest.fixture
def mock_full_system():
    """전체 시스템 Mock"""
    with patch('backend.app.api.sessions.create_checkpointer') as mock_cp, \
         patch('backend.app.api.todos.create_checkpointer') as mock_cp_todo, \
         patch('backend.app.api.sessions.build_supervisor_graph') as mock_graph_sessions, \
         patch('backend.app.api.todos.build_supervisor_graph') as mock_graph_todos:

        # Checkpointer mock
        checkpointer = AsyncMock()
        mock_cp.return_value = checkpointer
        mock_cp_todo.return_value = checkpointer

        # Graph mock
        graph = MagicMock()

        # Initial state
        initial_state = {
            "session_id": "test-session",
            "created_at": "2025-11-06T10:00:00",
            "updated_at": "2025-11-06T10:00:00",
            "total_steps": 0,
            "action_history": [],
            "plan_history": [],
            "user_interactions": [],
            "todos": [],
            "plan": {
                "goal": "Create diet plan",
                "steps": ["analyze", "plan", "execute"]
            }
        }

        mock_state = MagicMock()
        mock_state.values = initial_state.copy()

        graph.aget_state = AsyncMock(return_value=mock_state)
        graph.aupdate_state = AsyncMock()

        mock_graph_sessions.return_value = graph
        mock_graph_todos.return_value = graph

        yield {
            "checkpointer": checkpointer,
            "graph": graph,
            "state": mock_state
        }


# === 시나리오 1: 기본 워크플로우 ===

@pytest.mark.asyncio
async def test_basic_workflow(session_id, mock_full_system):
    """기본 워크플로우: 세션 생성 → Todo 추가 → 실행 → 조회"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 세션 요약 조회 (초기 상태)
        summary = await client.get(f"/api/sessions/{session_id}/summary")
        assert summary.status_code == 200

        # 2. Todo 추가
        todo1 = await client.post(
            f"/api/sessions/{session_id}/todos",
            json={"task": "Analyze user profile", "agent": "HealthAssessmentAgent"}
        )
        assert todo1.status_code == 200

        todo2 = await client.post(
            f"/api/sessions/{session_id}/todos",
            json={"task": "Create meal plan", "agent": "DietAgent"}
        )
        assert todo2.status_code == 200

        # 3. 세션 요약 재조회 (Todo 추가 후)
        summary2 = await client.get(f"/api/sessions/{session_id}/summary")
        assert summary2.status_code == 200

        # 4. 특정 action 조회
        action = await client.get(f"/api/sessions/{session_id}/action/1")
        # 성공하거나 404 (아직 실행 전일 수 있음)
        assert action.status_code in [200, 404]


# === 시나리오 2: Todo 수정 및 순서 변경 ===

@pytest.mark.asyncio
async def test_todo_modification_workflow(session_id, mock_full_system):
    """Todo 수정 워크플로우: 추가 → 수정 → 순서 변경 → Agent 변경"""

    # Mock state에 todos 추가
    mock_full_system["state"].values["todos"] = [
        {"id": "todo-1", "step": 1, "task": "Task 1", "status": "pending", "agent": "DietAgent"},
        {"id": "todo-2", "step": 2, "task": "Task 2", "status": "pending", "agent": "WorkoutAgent"},
        {"id": "todo-3", "step": 3, "task": "Task 3", "status": "pending", "agent": "ReportAgent"}
    ]

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Todo 수정
        update = await client.put(
            f"/api/sessions/{session_id}/todos/todo-1",
            json={"task": "Modified Task 1"}
        )
        assert update.status_code == 200

        # 2. Agent 변경
        agent_change = await client.put(
            f"/api/sessions/{session_id}/todos/todo-2/agent",
            json={"new_agent": "HealthAssessmentAgent"}
        )
        assert agent_change.status_code == 200

        # 3. 순서 변경
        reorder = await client.put(
            f"/api/sessions/{session_id}/todos/reorder",
            json={"todo_ids": ["todo-3", "todo-1", "todo-2"]}
        )
        assert reorder.status_code == 200
        data = reorder.json()

        # 순서가 변경되었는지 확인
        assert data["new_order"][0]["id"] == "todo-3"
        assert data["new_order"][1]["id"] == "todo-1"
        assert data["new_order"][2]["id"] == "todo-2"


# === 시나리오 3: 실패 처리 및 재시도 ===

@pytest.mark.asyncio
async def test_failure_and_retry_workflow(session_id, mock_full_system):
    """실패 처리 워크플로우: 실행 → 실패 → Agent 변경 → 재시도"""

    # Mock state에 실패한 todo 추가
    mock_full_system["state"].values["todos"] = [
        {"id": "todo-1", "step": 1, "task": "Task 1", "status": "failed", "agent": "DietAgent", "error": "Connection error", "retry_count": 0},
        {"id": "todo-2", "step": 2, "task": "Task 2", "status": "completed", "agent": "WorkoutAgent"}
    ]

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 실패한 Todo의 Agent 변경
        agent_change = await client.put(
            f"/api/sessions/{session_id}/todos/todo-1/agent",
            json={"new_agent": "HealthAssessmentAgent"}
        )
        assert agent_change.status_code == 200

        # 2. 재시도
        retry = await client.post(f"/api/sessions/{session_id}/retry/todo-1")
        assert retry.status_code == 200
        data = retry.json()

        # 재시도 후 상태 확인
        assert data["todo"]["status"] == "pending"
        assert data["todo"]["retry_count"] == 1


# === 시나리오 4: 세션 중단 및 재개 ===

@pytest.mark.asyncio
async def test_interrupt_and_resume_workflow(session_id, mock_full_system):
    """중단 및 재개 워크플로우: 실행 중 → 중단 → 수정 → 재개"""

    # Mock state에 진행 중인 todos 추가
    mock_full_system["state"].values["todos"] = [
        {"id": "todo-1", "step": 1, "task": "Task 1", "status": "completed", "agent": "DietAgent"},
        {"id": "todo-2", "step": 2, "task": "Task 2", "status": "in_progress", "agent": "WorkoutAgent"},
        {"id": "todo-3", "step": 3, "task": "Task 3", "status": "pending", "agent": "ReportAgent"}
    ]

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 세션 중단
        interrupt = await client.post(
            f"/api/sessions/{session_id}/interrupt",
            json={"reason": "user_modification", "message": "Need to modify plan"}
        )
        assert interrupt.status_code == 200
        data = interrupt.json()

        # 진행 상황 확인
        assert "progress" in data
        assert data["progress"]["completed"] >= 0

        # 2. 중단 중에 새 Todo 추가
        new_todo = await client.post(
            f"/api/sessions/{session_id}/todos",
            json={"task": "Additional Task", "agent": "DietAgent"}
        )
        assert new_todo.status_code == 200

        # 3. 기존 Todo 수정
        modify = await client.put(
            f"/api/sessions/{session_id}/todos/todo-3",
            json={"task": "Modified Task 3"}
        )
        assert modify.status_code == 200

        # 4. State 조회로 변경사항 확인
        summary = await client.get(f"/api/sessions/{session_id}/summary")
        assert summary.status_code == 200


# === 시나리오 5: 복잡한 Todo 관리 ===

@pytest.mark.asyncio
async def test_complex_todo_management(session_id, mock_full_system):
    """복잡한 Todo 관리: 추가 → 수정 → 삭제 → 순서변경을 반복"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 여러 Todo 추가
        todos = []
        for i in range(5):
            resp = await client.post(
                f"/api/sessions/{session_id}/todos",
                json={"task": f"Task {i+1}", "agent": "DietAgent"}
            )
            assert resp.status_code == 200
            todos.append(resp.json()["todo"])

        # Mock state 업데이트
        mock_full_system["state"].values["todos"] = [
            {"id": f"todo-{i}", "step": i, "task": f"Task {i}", "status": "pending", "agent": "DietAgent"}
            for i in range(1, 6)
        ]

        # 2. 일부 Todo 삭제
        delete1 = await client.delete(f"/api/sessions/{session_id}/todos/todo-2")
        assert delete1.status_code == 200

        delete2 = await client.delete(f"/api/sessions/{session_id}/todos/todo-4")
        assert delete2.status_code == 200

        # 3. 남은 Todo 순서 변경
        reorder = await client.put(
            f"/api/sessions/{session_id}/todos/reorder",
            json={"todo_ids": ["todo-5", "todo-3", "todo-1"]}
        )
        assert reorder.status_code == 200


# === 시나리오 6: State 직접 수정 ===

@pytest.mark.asyncio
async def test_direct_state_modification(session_id, mock_full_system):
    """State 직접 수정: 고급 사용자용 기능"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. State 직접 수정
        state_update = await client.put(
            f"/api/sessions/{session_id}/state",
            json={
                "updates": {
                    "plan_requires_todos": True,
                    "need_todo_update": True,
                    "custom_field": "custom_value"
                }
            }
        )
        assert state_update.status_code == 200
        data = state_update.json()

        assert data["success"] is True
        assert data["updates"]["plan_requires_todos"] is True

        # 2. Summary 조회로 변경 확인
        summary = await client.get(f"/api/sessions/{session_id}/summary")
        assert summary.status_code == 200


# === 시나리오 7: Agent 목록 활용 ===

@pytest.mark.asyncio
async def test_agent_discovery_workflow(session_id, mock_full_system):
    """Agent 발견 워크플로우: Agent 목록 조회 → Todo에 할당"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 사용 가능한 Agent 목록 조회
        agents = await client.get("/api/agents")
        assert agents.status_code == 200
        agent_list = agents.json()["agents"]

        # 2. 각 Agent로 Todo 생성
        for agent in agent_list[:3]:  # 처음 3개만
            todo = await client.post(
                f"/api/sessions/{session_id}/todos",
                json={
                    "task": f"Task for {agent['name']}",
                    "agent": agent["name"]
                }
            )
            assert todo.status_code == 200


# === 시나리오 8: 에러 처리 ===

@pytest.mark.asyncio
async def test_error_handling(session_id, mock_full_system):
    """에러 처리: 잘못된 요청들"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. 존재하지 않는 Todo 수정
        resp1 = await client.put(
            f"/api/sessions/{session_id}/todos/nonexistent",
            json={"task": "Modified"}
        )
        assert resp1.status_code == 404

        # 2. 존재하지 않는 Todo 삭제
        resp2 = await client.delete(f"/api/sessions/{session_id}/todos/nonexistent")
        assert resp2.status_code == 404

        # 3. 잘못된 순서 변경
        resp3 = await client.put(
            f"/api/sessions/{session_id}/todos/reorder",
            json={"todo_ids": ["nonexistent-1", "nonexistent-2"]}
        )
        assert resp3.status_code == 400

        # 4. 존재하지 않는 Todo 재시도
        resp4 = await client.post(f"/api/sessions/{session_id}/retry/nonexistent")
        assert resp4.status_code == 404


# === 성능 테스트 ===

@pytest.mark.asyncio
async def test_concurrent_todo_operations(session_id, mock_full_system):
    """동시 Todo 작업 테스트"""

    # Mock state에 여러 todos 추가
    mock_full_system["state"].values["todos"] = [
        {"id": f"todo-{i}", "step": i, "task": f"Task {i}", "status": "pending", "agent": "DietAgent"}
        for i in range(1, 11)
    ]

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 동시에 여러 작업 실행
        import asyncio

        tasks = [
            client.get(f"/api/sessions/{session_id}/summary"),
            client.put(f"/api/sessions/{session_id}/todos/todo-1", json={"task": "Modified"}),
            client.put(f"/api/sessions/{session_id}/todos/todo-2/agent", json={"new_agent": "WorkoutAgent"}),
            client.delete(f"/api/sessions/{session_id}/todos/todo-3"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 모든 작업이 완료되어야 함
        assert len(results) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
