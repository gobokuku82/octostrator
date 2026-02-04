"""Reducers - 상태 병합 함수"""

from typing import Any, List
from datetime import datetime


def ml_result_reducer(current: dict, update: dict) -> dict:
    """
    ML 결과 리듀서 - 딕셔너리 병합

    동작:
    - 기존 결과와 새 결과를 병합
    - result_type이 다르면 히스토리에 추가
    - 같은 result_type이면 업데이트

    Args:
        current: 현재 ML 결과
        update: 업데이트할 ML 결과

    Returns:
        병합된 ML 결과
    """
    if not current:
        return update

    # 히스토리 관리
    history = current.get("history", [])

    # 현재 result_type과 다르면 히스토리에 추가
    if current.get("result_type") and current.get("result_type") != update.get("result_type"):
        history.append({
            "result_type": current.get("result_type"),
            "summary": current.get("summary", {}),
            "timestamp": current.get("timestamp")
        })

    # 업데이트 적용
    result = {**current, **update}
    result["history"] = history

    return result


def biz_result_reducer(current: dict, update: dict) -> dict:
    """
    Biz 결과 리듀서 - 딕셔너리 병합

    동작:
    - ML 결과 리듀서와 동일한 로직
    - result_type별 히스토리 관리

    Args:
        current: 현재 Biz 결과
        update: 업데이트할 Biz 결과

    Returns:
        병합된 Biz 결과
    """
    if not current:
        return update

    # 히스토리 관리
    history = current.get("history", [])

    # 현재 result_type과 다르면 히스토리에 추가
    if current.get("result_type") and current.get("result_type") != update.get("result_type"):
        history.append({
            "result_type": current.get("result_type"),
            "preview": current.get("preview", ""),
            "timestamp": current.get("timestamp")
        })

    # 업데이트 적용
    result = {**current, **update}
    result["history"] = history

    return result


def merge_dict_recursive(base: dict, update: dict) -> dict:
    """
    재귀적 딕셔너리 병합 헬퍼 함수

    Args:
        base: 기본 딕셔너리
        update: 업데이트할 딕셔너리

    Returns:
        병합된 딕셔너리
    """
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dict_recursive(result[key], value)
        else:
            result[key] = value

    return result


def todo_reducer(current: List[Any], updates: List[Any]) -> List[Any]:
    """
    Todo 리듀서 V2.0 - ID 기반 병합 with history/version 관리

    동작:
    - 같은 ID가 있으면 업데이트 (history 병합, version 증가)
    - 새로운 ID면 추가
    - completed/failed/skipped 상태인 항목은 유지 (히스토리)

    Args:
        current: 현재 Todo 리스트
        updates: 업데이트할 Todo 리스트

    Returns:
        병합된 Todo 리스트
    """
    # Import from models/ package
    from ..models.todo import TodoItem

    # ID -> TodoItem 매핑
    todo_map = {todo.id: todo for todo in current}

    # 업데이트 적용
    for update in updates:
        if update.id in todo_map:
            existing = todo_map[update.id]

            # History 병합 (중복 제거)
            # Pydantic model_copy는 list를 shallow copy하므로
            # existing.history와 update.history가 같은 객체일 수 있음
            # Deep copy 필요
            import copy
            existing_hist = copy.deepcopy(existing.history)
            update_hist = copy.deepcopy(update.history)
            combined_history = existing_hist + update_hist

            # 중복 제거 (timestamp + action 기준)
            # 같은 timestamp에 다른 action이 있을 수 있으므로
            # timestamp만으로 중복 제거하면 안됨
            seen_entries = set()
            unique_history = []
            for hist in combined_history:
                # timestamp + action으로 unique key 생성
                ts = hist.get("timestamp")
                action = hist.get("action")
                key = (ts, action)
                if key not in seen_entries:
                    seen_entries.add(key)
                    unique_history.append(hist)

            # Version은 더 큰 값 사용
            max_version = max(existing.version, update.version)

            # model_copy로 새 인스턴스 생성 (shallow copy 문제 방지)
            update = update.model_copy(update={
                "history": unique_history,
                "version": max_version,
                "updated_at": datetime.now()
            })

        todo_map[update.id] = update

    return list(todo_map.values())
