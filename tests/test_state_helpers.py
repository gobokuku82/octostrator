"""
StateHelper Unit Tests

Author: AI PT Manager Development Team
Date: 2025-11-06
Version: 1.0
"""
import pytest
from .state_helpers import StateHelpers


def test_get_action_at_step():
    """특정 step 조회 테스트"""
    state = {
        "action_history": [
            {"step": 1, "action": "A"},
            {"step": 2, "action": "B"}
        ]
    }

    result = StateHelpers.get_action_at_step(state, 1)
    assert result["action"] == "A"

    result = StateHelpers.get_action_at_step(state, 999)
    assert result is None


def test_get_todo_status():
    """Todo 상태 통계 테스트"""
    state = {
        "todos": [
            {"status": "completed"},
            {"status": "completed"},
            {"status": "pending"},
            {"status": "failed"}
        ]
    }

    status = StateHelpers.get_todo_status(state)
    assert status["total"] == 4
    assert status["completed"] == 2
    assert status["failed"] == 1
    assert status["pending"] == 1
    assert status["progress"] == 0.5


def test_get_execution_summary():
    """전체 요약 테스트"""
    from datetime import datetime

    state = {
        "session_id": "test_session",
        "created_at": datetime.now().isoformat(),
        "action_history": [{"step": 1}, {"step": 2}],
        "todos": [
            {"status": "completed"},
            {"status": "pending"}
        ],
        "plan_history": [{"version": 1}],
        "user_interactions": [],
        "error": None,
        "requires_approval": False
    }

    summary = StateHelpers.get_execution_summary(state)
    assert summary["session_id"] == "test_session"
    assert summary["total_steps"] == 2
    assert summary["status"] == "in_progress"
