"""
Reducer 함수 Unit Tests

Author: AI PT Manager Development Team
Date: 2025-11-06
Version: 1.0
"""
import pytest
from datetime import datetime
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)


def test_add_with_timestamp_and_step():
    """타임스탬프와 step 자동 추가 테스트"""
    # None -> 빈 리스트
    result = add_with_timestamp_and_step(None, [{"action": "A"}])
    assert len(result) == 1
    assert result[0]["step"] == 1
    assert "timestamp" in result[0]

    # 기존 항목에 추가
    result = add_with_timestamp_and_step(result, [{"action": "B"}])
    assert len(result) == 2
    assert result[1]["step"] == 2


def test_merge_todos_smart():
    """Todo 스마트 병합 테스트"""
    # 신규 Todo (ID 자동 생성)
    result = merge_todos_smart(None, [{"task": "A"}])
    assert len(result) == 1
    assert "id" in result[0]
    assert result[0]["step"] == 1
    assert result[0]["status"] == "pending"

    # 기존 Todo 업데이트
    todo_id = result[0]["id"]
    result = merge_todos_smart(result, [{"id": todo_id, "task": "A_modified"}])
    assert len(result) == 1
    assert result[0]["task"] == "A_modified"
    assert result[0]["step"] == 1  # step 유지


def test_track_plan_changes():
    """Plan 버전 관리 테스트"""
    result = track_plan_changes(None, [{"plan": {"goal": "A"}}])
    assert len(result) == 1
    assert result[0]["version"] == 1

    result = track_plan_changes(result, [{"plan": {"goal": "B"}}])
    assert len(result) == 2
    assert result[1]["version"] == 2


def test_track_user_interactions():
    """사용자 개입 추적 테스트"""
    result = track_user_interactions(None, [{"type": "interrupt"}])
    assert len(result) == 1
    assert result[0]["type"] == "interrupt"
    assert "timestamp" in result[0]
