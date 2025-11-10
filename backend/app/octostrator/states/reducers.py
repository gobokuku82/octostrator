"""
Custom Reducer Functions for State Management

이 파일은 LangGraph State의 Reducer 함수들을 정의합니다.
각 Reducer는 State 업데이트 시 어떻게 병합할지 결정합니다.

Author: Specialist Agent Development Team
Date: 2025-11-06
Version: 1.0
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


def add_with_timestamp_and_step(
    existing: Optional[List[Dict]],
    new: List[Dict]
) -> List[Dict]:
    """
    작업 내역에 타임스탬프와 step 번호 자동 추가

    Args:
        existing: 기존 action_history
        new: 새로 추가할 작업들

    Returns:
        병합된 작업 내역

    Example:
        >>> existing = [{"action": "A", "step": 1, "timestamp": "..."}]
        >>> new = [{"action": "B"}]
        >>> result = add_with_timestamp_and_step(existing, new)
        >>> result
        [
            {"action": "A", "step": 1, "timestamp": "..."},
            {"action": "B", "step": 2, "timestamp": "2025-11-06T..."}
        ]
    """
    if existing is None:
        existing = []

    if new is None or not new:
        return existing

    # 다음 step 번호 계산
    next_step = len(existing) + 1

    # 새 항목에 메타데이터 추가
    enriched = []
    for item in new:
        if isinstance(item, dict):
            # 타임스탬프 (없는 경우만)
            if "timestamp" not in item:
                item["timestamp"] = datetime.now().isoformat()

            # Step 번호
            if "step" not in item:
                item["step"] = next_step
                next_step += 1

        enriched.append(item)

    return existing + enriched


def merge_todos_smart(
    existing: Optional[List[Dict]],
    new: List[Dict]
) -> List[Dict]:
    """
    Todo를 ID 기준으로 스마트하게 병합

    Features:
        - ID 기준 중복 제거
        - ID 없으면 자동 생성 (UUID)
        - created_at, updated_at 자동 관리
        - step 순서 유지

    Args:
        existing: 기존 todos
        new: 새로운 todos

    Returns:
        병합된 todos (step 순서로 정렬)

    Example:
        >>> existing = [{"id": "1", "task": "A", "step": 1}]
        >>> new = [{"id": "1", "task": "A_modified"}, {"task": "B"}]
        >>> result = merge_todos_smart(existing, new)
        >>> result
        [
            {"id": "1", "task": "A_modified", "step": 1, "updated_at": "..."},
            {"id": "<uuid>", "task": "B", "step": 2, "created_at": "..."}
        ]
    """
    if existing is None:
        existing = []

    if new is None or not new:
        return existing

    # ID를 key로 하는 dict 생성
    todo_dict = {}
    for todo in existing:
        todo_id = todo.get("id")
        if todo_id:
            todo_dict[todo_id] = todo.copy()  # 원본 보호

    # 현재 최대 step
    max_step = max([t.get("step", 0) for t in existing], default=0)

    # 새 Todo 처리
    now = datetime.now().isoformat()
    for todo in new:
        # ID 생성 (없는 경우)
        if "id" not in todo:
            todo["id"] = str(uuid.uuid4())

        todo_id = todo["id"]

        # 신규 vs 업데이트 판단
        if todo_id in todo_dict:
            # 기존 항목 업데이트
            existing_todo = todo_dict[todo_id]

            # 기존 값 유지 (새로 제공되지 않은 필드)
            merged = existing_todo.copy()
            merged.update(todo)  # 새 값으로 덮어쓰기

            # step은 기존 값 유지
            merged["step"] = existing_todo.get("step", max_step + 1)

            # created_at 유지
            merged["created_at"] = existing_todo.get("created_at", now)

            # updated_at 갱신
            merged["updated_at"] = now

            todo_dict[todo_id] = merged
        else:
            # 신규 항목
            max_step += 1
            todo["step"] = max_step
            todo["created_at"] = now
            todo["updated_at"] = now

            # 기본 status
            if "status" not in todo:
                todo["status"] = "pending"

            todo_dict[todo_id] = todo

    # 리스트로 변환 및 정렬
    result = list(todo_dict.values())
    result.sort(key=lambda x: x.get("step", 999))

    return result


def track_plan_changes(
    existing: Optional[List[Dict]],
    new: List[Dict]
) -> List[Dict]:
    """
    Plan 변경을 버전별로 추적

    Args:
        existing: 기존 plan_history
        new: 새로운 plan (리스트 형태, 보통 1개)

    Returns:
        버전 관리되는 plan_history

    Example:
        >>> existing = [{"version": 1, "plan": {...}}]
        >>> new = [{"plan": {...}, "reason": "user_modification"}]
        >>> result = track_plan_changes(existing, new)
        >>> result
        [
            {"version": 1, "plan": {...}},
            {"version": 2, "plan": {...}, "reason": "user_modification", "timestamp": "..."}
        ]
    """
    if existing is None:
        existing = []

    if new is None or not new:
        return existing

    # 다음 버전 번호
    next_version = len(existing) + 1

    # 새 Plan 처리
    enriched = []
    for plan_entry in new:
        if isinstance(plan_entry, dict):
            # 버전 번호
            plan_entry["version"] = next_version
            next_version += 1

            # 타임스탬프
            if "timestamp" not in plan_entry:
                plan_entry["timestamp"] = datetime.now().isoformat()

            # 기본값
            if "reason" not in plan_entry:
                plan_entry["reason"] = "unknown"
            if "modified_by" not in plan_entry:
                plan_entry["modified_by"] = "system"

        enriched.append(plan_entry)

    return existing + enriched


def track_user_interactions(
    existing: Optional[List[Dict]],
    new: List[Dict]
) -> List[Dict]:
    """
    사용자 개입 내역 추적

    Interaction Types:
        - interrupt: 실행 중단
        - modify_todo: Todo 수정
        - modify_plan: Plan 수정
        - resume: 실행 재개
        - retry: Todo 재시도
        - change_agent: Agent 변경

    Args:
        existing: 기존 user_interactions
        new: 새로운 개입 기록

    Returns:
        누적된 개입 내역

    Example:
        >>> existing = []
        >>> new = [{"type": "interrupt", "reason": "user_requested"}]
        >>> result = track_user_interactions(existing, new)
        >>> result
        [{"type": "interrupt", "reason": "user_requested", "timestamp": "..."}]
    """
    if existing is None:
        existing = []

    if new is None or not new:
        return existing

    # 타임스탬프 추가
    enriched = []
    for interaction in new:
        if isinstance(interaction, dict):
            if "timestamp" not in interaction:
                interaction["timestamp"] = datetime.now().isoformat()

            # type 필수
            if "type" not in interaction:
                interaction["type"] = "unknown"

        enriched.append(interaction)

    return existing + enriched
