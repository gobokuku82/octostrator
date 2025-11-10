# 단계별 구현 가이드

**작성일:** 2025-11-06
**버전:** 1.0

---

## 📋 목차

1. [구현 순서 개요](#구현-순서-개요)
2. [Phase 1: State 구조 개선](#phase-1-state-구조-개선)
3. [Phase 2: API 확장](#phase-2-api-확장)
4. [Phase 3: 통합 테스트](#phase-3-통합-테스트)
5. [체크리스트](#체크리스트)

---

## 🎯 구현 순서 개요

### 전체 로드맵

```
Phase 1: State 구조 개선 (예상: 1일)
  ├── Step 1.1: Reducer 함수 작성
  ├── Step 1.2: OctostratorState 정의
  ├── Step 1.3: StateHelper 클래스 작성
  └── Step 1.4: Graph 및 Node 업데이트

Phase 2: API 확장 (예상: 2일)
  ├── Step 2.1: Session API 확장
  ├── Step 2.2: Todo 관리 API 생성
  ├── Step 2.3: Agent 관리 API 생성
  └── Step 2.4: main.py 라우터 등록

Phase 3: 통합 테스트 (예상: 1일)
  ├── Step 3.1: Unit Tests
  ├── Step 3.2: Integration Tests
  └── Step 3.3: 성능 테스트

Total: 4일
```

### 의존성 그래프

```
Step 1.1 (Reducer 작성)
  ↓
Step 1.2 (State 정의) ← Step 1.1 완료 필요
  ↓
Step 1.3 (StateHelper) ← Step 1.2 완료 필요
  ↓
Step 1.4 (Graph 업데이트) ← Step 1.2, 1.3 완료 필요
  ↓
Step 2.1-2.4 (API) ← Step 1.3, 1.4 완료 필요
  ↓
Step 3.1-3.3 (테스트) ← 모든 구현 완료 필요
```

---

## 📦 Phase 1: State 구조 개선

### Step 1.1: Reducer 함수 작성

**예상 소요**: 2시간

**목표**: 4개 커스텀 Reducer 함수 구현

#### 파일 생성

**경로**: `backend/app/octostrator/states/reducers.py`

#### 구현 코드

```python
"""
Custom Reducer Functions for State Management

이 파일은 LangGraph State의 Reducer 함수들을 정의합니다.
각 Reducer는 State 업데이트 시 어떻게 병합할지 결정합니다.
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
```

#### 테스트 코드

**경로**: `backend/app/octostrator/states/test_reducers.py`

```python
"""
Reducer 함수 Unit Tests
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
```

#### 검증

```bash
# 테스트 실행
cd c:\kdy\Projects\AI_PTmanager\beta_v001
pytest backend/app/octostrator/states/test_reducers.py -v
```

**체크리스트**:
- [ ] reducers.py 파일 생성
- [ ] 4개 Reducer 함수 구현
- [ ] test_reducers.py 작성
- [ ] 모든 테스트 통과

---

### Step 1.2: OctostratorState 정의

**예상 소요**: 1시간

**목표**: 새로운 State 구조 정의

#### 파일 생성

**경로**: `backend/app/octostrator/states/octostrator_state.py`

#### 구현 코드

```python
"""
Octostrator State Definition

전체 시스템의 State 구조를 정의합니다.
"""
from typing import Annotated, TypedDict, Optional, Any, List, Dict
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)


class OctostratorState(TypedDict):
    """
    Octostrator의 전체 State

    기존 필드 + History Tracking 추가
    """
    # ===== User Input =====
    user_query: str
    session_id: str
    output_format: str  # "chat" | "graph" | "report"

    # ===== Resources =====
    llm: Any  # ChatOpenAI instance
    checkpointer: Any  # AsyncPostgresSaver instance
    context: dict  # {"auto_approve": bool, ...}

    # ===== Current State =====
    plan: dict
    todos: Annotated[List[Dict], merge_todos_smart]  # Reducer 사용!
    execution_results: dict
    final_response: str

    # ===== Flags =====
    plan_valid: bool
    requires_approval: bool
    error: Optional[str]

    # ===== Todo Manager 제어 (신규) =====
    plan_requires_todos: bool           # Cognitive가 설정 (Todo Manager 호출 필요 시)
    need_todo_update: bool              # Execute가 설정 (실행 중 Todo 추가 필요 시)
    user_requested_todo_update: bool    # API가 설정 (사용자가 Todo 수정 시)

    # ===== History Tracking (신규) =====

    # 작업 내역
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]
    # Example: [
    #   {"step": 1, "action": "cognitive_layer_node", "timestamp": "...", "result": {...}, "duration_ms": 250},
    #   {"step": 2, "action": "todo_layer_node", ...},
    # ]

    # Plan 변경 히스토리
    plan_history: Annotated[List[Dict], track_plan_changes]
    # Example: [
    #   {"version": 1, "plan": {...}, "timestamp": "...", "reason": "initial", "modified_by": "system"},
    #   {"version": 2, "plan": {...}, "timestamp": "...", "reason": "user_modification", "modified_by": "api"},
    # ]

    # 사용자 개입 기록
    user_interactions: Annotated[List[Dict], track_user_interactions]
    # Example: [
    #   {"type": "interrupt", "timestamp": "...", "reason": "...", "details": {...}},
    #   {"type": "modify_todo", "timestamp": "...", "details": {...}},
    # ]

    # ===== Metadata =====
    created_at: str  # 세션 생성 시각
    updated_at: str  # 마지막 업데이트 시각
    total_steps: int  # 총 실행된 step 수
```

#### __init__.py 업데이트

**경로**: `backend/app/octostrator/states/__init__.py`

```python
"""
States module exports
"""
from .octostrator_state import OctostratorState
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)

__all__ = [
    "OctostratorState",
    "add_with_timestamp_and_step",
    "merge_todos_smart",
    "track_plan_changes",
    "track_user_interactions",
]
```

**체크리스트**:
- [ ] octostrator_state.py 파일 생성
- [ ] OctostratorState 정의
- [ ] __init__.py 업데이트
- [ ] import 에러 없는지 확인

---

### Step 1.3: StateHelper 클래스 작성

**예상 소요**: 2시간

**목표**: State 조회/분석 헬퍼 함수 구현

#### 파일 생성

**경로**: `backend/app/octostrator/states/state_helpers.py`

#### 구현 코드

```python
"""
StateHelper: State 조회 및 분석 유틸리티

State를 쉽게 조회하고 분석할 수 있는 헬퍼 함수 모음
"""
from typing import Dict, List, Optional, Any
from datetime import datetime


class StateHelpers:
    """State 조회 및 분석 헬퍼 클래스"""

    @staticmethod
    def get_action_at_step(state: Dict, step: int) -> Optional[Dict]:
        """특정 step의 작업 조회"""
        history = state.get("action_history", [])
        for action in history:
            if action.get("step") == step:
                return action
        return None

    @staticmethod
    def get_all_actions_summary(state: Dict) -> str:
        """모든 작업 내역 요약"""
        history = state.get("action_history", [])
        if not history:
            return "작업 내역이 없습니다."

        lines = ["=== 작업 내역 ==="]
        for action in history:
            step = action.get("step", "?")
            action_name = action.get("action", "unknown")
            timestamp = action.get("timestamp", "")
            duration = action.get("duration_ms", 0)

            # 시간 포맷 (HH:MM:SS)
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp

            lines.append(
                f"Step {step:2d} [{time_str}] {action_name:30s} ({duration}ms)"
            )

        return "\n".join(lines)

    @staticmethod
    def get_todo_status(state: Dict) -> Dict[str, Any]:
        """Todo 상태 통계"""
        todos = state.get("todos", [])

        total = len(todos)
        completed = sum(1 for t in todos if t.get("status") == "completed")
        failed = sum(1 for t in todos if t.get("status") == "failed")
        pending = sum(1 for t in todos if t.get("status") == "pending")
        in_progress = sum(1 for t in todos if t.get("status") == "in_progress")

        progress = completed / total if total > 0 else 0.0

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "in_progress": in_progress,
            "progress": progress
        }

    @staticmethod
    def get_plan_version(state: Dict, version: int) -> Optional[Dict]:
        """특정 버전의 Plan 조회"""
        plan_history = state.get("plan_history", [])
        for plan_entry in plan_history:
            if plan_entry.get("version") == version:
                return plan_entry
        return None

    @staticmethod
    def get_latest_plan(state: Dict) -> Optional[Dict]:
        """최신 Plan 조회"""
        plan_history = state.get("plan_history", [])
        if not plan_history:
            return None
        return plan_history[-1]

    @staticmethod
    def get_user_interaction_summary(state: Dict) -> List[str]:
        """사용자 개입 내역 요약"""
        interactions = state.get("user_interactions", [])
        if not interactions:
            return ["사용자 개입 내역이 없습니다."]

        summary = []
        for interaction in interactions:
            itype = interaction.get("type", "unknown")
            timestamp = interaction.get("timestamp", "")
            details = interaction.get("details", {})

            # 시간 포맷
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp

            if itype == "interrupt":
                summary.append(f"[{time_str}] 중단: {details.get('message', '')}")
            elif itype == "modify_todo":
                action = details.get("action", "")
                summary.append(f"[{time_str}] Todo {action}")
            elif itype == "resume":
                summary.append(f"[{time_str}] 재개")
            else:
                summary.append(f"[{time_str}] {itype}")

        return summary

    @staticmethod
    def get_execution_summary(state: Dict) -> Dict[str, Any]:
        """실행 상황 전체 요약"""
        # 세션 정보
        session_id = state.get("session_id", "unknown")
        created_at = state.get("created_at", "")
        total_steps = state.get("total_steps", len(state.get("action_history", [])))

        # 소요 시간 계산
        try:
            start = datetime.fromisoformat(created_at)
            now = datetime.now()
            duration = str(now - start).split('.')[0]  # HH:MM:SS
        except:
            duration = "unknown"

        # Todo 상태
        todo_status = StateHelpers.get_todo_status(state)

        # Plan 버전
        plan_history = state.get("plan_history", [])
        plan_version = len(plan_history)

        # 사용자 개입 횟수
        user_interactions = len(state.get("user_interactions", []))

        # 전체 상태 판단
        if state.get("error"):
            status = "error"
        elif state.get("requires_approval"):
            status = "waiting_human"
        elif todo_status["progress"] == 1.0:
            status = "completed"
        else:
            status = "in_progress"

        return {
            "session_id": session_id,
            "created_at": created_at,
            "duration": duration,
            "total_steps": total_steps,
            "todo_status": todo_status,
            "plan_version": plan_version,
            "user_interactions": user_interactions,
            "status": status
        }
```

#### __init__.py 업데이트

**경로**: `backend/app/octostrator/states/__init__.py`

```python
from .state_helpers import StateHelpers

__all__ = [
    # ... 기존
    "StateHelpers",
]
```

#### 테스트 코드

**경로**: `backend/app/octostrator/states/test_state_helpers.py`

```python
"""
StateHelper Unit Tests
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
```

**체크리스트**:
- [ ] state_helpers.py 파일 생성
- [ ] StateHelpers 클래스 구현
- [ ] test_state_helpers.py 작성
- [ ] 모든 테스트 통과

---

### Step 1.4: Graph 및 Node 업데이트

**예상 소요**: 2시간

**목표**: OctostratorState 적용, Node에서 History 기록

#### octostrator_graph.py 수정

**경로**: `backend/app/octostrator/supervisors/octostrator/octostrator_graph.py`

**중요 변경**: Todo Manager를 조건부로만 실행하도록 그래프 구조 변경

```python
# 기존 코드에서 수정
from backend.app.octostrator.states import OctostratorState
from langgraph.graph import StateGraph, START, END

def build_octostrator_graph(checkpointer=None):
    """Build the main orchestrator graph

    새로운 구조:
        START → Supervisor → Cognitive → [Conditional] → Execute → Response → END
                                              ↓ (필요시만)
                                          Todo Manager
    """
    # StateGraph에 OctostratorState 적용
    graph = StateGraph(OctostratorState)  # ← 변경!

    # 노드 추가 (기존과 동일)
    graph.add_node("cognitive", cognitive_layer_node)
    graph.add_node("todo", todo_layer_node)          # 조건부 실행!
    graph.add_node("execute", execute_layer_node)
    graph.add_node("response", response_layer_node)

    # 엣지 추가 (신규 구조)
    graph.add_edge(START, "cognitive")

    # ===== Conditional Edge: Todo Manager 호출 여부 결정 =====
    graph.add_conditional_edges(
        "cognitive",
        should_use_todo_manager,  # 새로운 함수!
        {
            "todo": "todo",        # Todo Manager 실행
            "execute": "execute"   # Todo Manager 건너뛰기
        }
    )

    # Todo Manager → Execute
    graph.add_edge("todo", "execute")

    # Execute → Response → END
    graph.add_edge("execute", "response")
    graph.add_edge("response", END)

    # Compile
    compiled_graph = graph.compile(checkpointer=checkpointer)
    return compiled_graph


def should_use_todo_manager(state: OctostratorState) -> str:
    """
    Conditional Edge: Todo Manager 실행 여부 판단

    Args:
        state: 현재 State

    Returns:
        "todo" 또는 "execute"
    """
    # 1. Cognitive가 Todo 생성 요청
    if state.get("plan_requires_todos", False):
        return "todo"

    # 2. 사용자가 API로 Todo 수정 요청
    if state.get("user_requested_todo_update", False):
        return "todo"

    # 3. Execute에서 Todo 업데이트 요청
    if state.get("need_todo_update", False):
        return "todo"

    # 기본: Todo Manager 건너뛰기
    return "execute"
```

#### octostrator_nodes.py 수정

**경로**: `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py`

각 노드에서 action_history 기록 추가:

```python
from datetime import datetime
from backend.app.octostrator.states import OctostratorState

async def cognitive_layer_node(state: OctostratorState) -> OctostratorState:
    """Execute Cognitive Layer"""
    start_time = datetime.now()

    # 기존 로직
    from ..cognitive.cognitive_helpers import CognitiveSupervisor
    supervisor = CognitiveSupervisor(
        llm=state.get("llm"),
        checkpointer=state.get("checkpointer")
    )
    plan = await supervisor.plan(
        user_message=state.get("user_query", ""),
        session_id=state.get("session_id", "default"),
        context=state.get("context", {})
    )

    # State 업데이트
    state["plan"] = plan
    state["plan_valid"] = plan is not None

    # ===== Todo Manager 호출 여부 결정 (신규) =====
    # 예시: 복잡한 계획이면 Todo Manager 호출
    if plan and len(plan.get("steps", [])) > 1:
        state["plan_requires_todos"] = True
    else:
        state["plan_requires_todos"] = False

    # ===== History 기록 (신규) =====
    end_time = datetime.now()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    # Action history 기록
    state["action_history"] = [{
        "action": "cognitive_layer_node",
        "result": {"plan": plan},
        "duration_ms": duration_ms
    }]

    # Plan history 기록
    if plan:
        state["plan_history"] = [{
            "plan": plan,
            "reason": "initial_creation",
            "modified_by": "system"
        }]

    # Metadata 업데이트
    if "created_at" not in state or not state["created_at"]:
        state["created_at"] = start_time.isoformat()
    state["updated_at"] = end_time.isoformat()

    return state


# 다른 노드들도 유사하게 수정...
```

**체크리스트**:
- [ ] octostrator_graph.py 수정
- [ ] octostrator_nodes.py 수정 (4개 노드 모두)
- [ ] import 에러 확인
- [ ] 간단한 실행 테스트

---

## 🌐 Phase 2: API 확장

### Step 2.1: Session API 확장

**예상 소요**: 2시간

**파일**: `backend/app/api/sessions.py` (수정)

#### 추가할 엔드포인트

1. `GET /{thread_id}/summary`
2. `GET /{thread_id}/action/{step}`
3. `PUT /{thread_id}/state`
4. `POST /{thread_id}/interrupt`

**상세 코드는 API_DESIGN_251106.md 참조**

**체크리스트**:
- [ ] GET /summary 구현
- [ ] GET /action/{step} 구현
- [ ] PUT /state 구현
- [ ] POST /interrupt 구현
- [ ] Postman으로 테스트

---

### Step 2.2: Todo 관리 API 생성

**예상 소요**: 3시간

#### 파일 생성

**경로**: `backend/app/api/todos.py`

#### 구현할 엔드포인트

1. `POST /{thread_id}/todos` - Todo 추가
2. `DELETE /{thread_id}/todos/{todo_id}` - Todo 삭제
3. `PUT /{thread_id}/todos/{todo_id}` - Todo 수정
4. `PUT /{thread_id}/todos/reorder` - 순서 변경
5. `POST /{thread_id}/retry/{todo_id}` - 재시도
6. `PUT /{thread_id}/todos/{todo_id}/agent` - Agent 변경

**상세 코드는 API_DESIGN_251106.md 참조**

**체크리스트**:
- [ ] todos.py 파일 생성
- [ ] 6개 엔드포인트 구현
- [ ] Pydantic 모델 정의
- [ ] Postman으로 테스트

---

### Step 2.3: Agent 관리 API 생성

**예상 소요**: 1시간

#### 파일 생성

**경로**: `backend/app/api/agents.py`

#### 구현할 엔드포인트

1. `GET /agents` - Agent 목록 조회

**체크리스트**:
- [ ] agents.py 파일 생성
- [ ] GET /agents 구현
- [ ] Postman으로 테스트

---

### Step 2.4: main.py 라우터 등록

**예상 소요**: 30분

**파일**: `backend/app/main.py` (수정)

```python
# 기존 코드에 추가
from backend.app.api.todos import router as todos_router
from backend.app.api.agents import router as agents_router

# Router 등록
app.include_router(todos_router)
app.include_router(agents_router)
```

**체크리스트**:
- [ ] todos_router 등록
- [ ] agents_router 등록
- [ ] 서버 재시작 후 Swagger 확인 (http://localhost:8000/docs)

---

## 🧪 Phase 3: 통합 테스트

### Step 3.1: Unit Tests

**예상 소요**: 2시간

**테스트 파일들**:
- `backend/app/octostrator/states/test_reducers.py` (이미 작성)
- `backend/app/octostrator/states/test_state_helpers.py` (이미 작성)

**체크리스트**:
- [ ] 모든 Unit Test 작성
- [ ] pytest 실행 성공
- [ ] 커버리지 > 80%

---

### Step 3.2: Integration Tests

**예상 소요**: 2시간

#### 파일 생성

**경로**: `backend/tests/test_api_integration.py`

```python
"""
API Integration Tests
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_full_workflow():
    """전체 워크플로우 테스트"""
    # 1. 세션 시작 (WebSocket 대신 REST로 간단히)
    response = client.post("/chat", json={"message": "점심 추천해줘"})
    assert response.status_code == 200

    # 2. 요약 조회
    response = client.get("/api/sessions/default/summary")
    assert response.status_code == 200
    summary = response.json()
    assert "total_steps" in summary

    # 3. Todo 추가
    response = client.post(
        "/api/sessions/default/todos",
        json={"task": "알레르기 체크", "agent": "DietAgent"}
    )
    assert response.status_code == 200
    todo = response.json()["todo"]
    assert "id" in todo

    # 4. Todo 수정
    response = client.put(
        f"/api/sessions/default/todos/{todo['id']}",
        json={"status": "completed"}
    )
    assert response.status_code == 200

    # 5. Todo 삭제
    response = client.delete(f"/api/sessions/default/todos/{todo['id']}")
    assert response.status_code == 200
```

**체크리스트**:
- [ ] test_api_integration.py 작성
- [ ] 전체 시나리오 테스트 통과

---

### Step 3.3: 성능 테스트

**예상 소요**: 1시간

#### 테스트 항목

1. State 조회 성능 (< 1초)
2. Todo 수정 반영 (< 200ms)
3. History 조회 (100개, < 2초)

**체크리스트**:
- [ ] 성능 테스트 스크립트 작성
- [ ] 모든 NFR 충족 확인

---

## ✅ 전체 체크리스트

### Phase 1 완료 확인
- [ ] Step 1.1: Reducer 함수 작성 완료
- [ ] Step 1.2: OctostratorState 정의 완료
- [ ] Step 1.3: StateHelper 클래스 작성 완료
- [ ] Step 1.4: Graph 및 Node 업데이트 완료

### Phase 2 완료 확인
- [ ] Step 2.1: Session API 확장 완료
- [ ] Step 2.2: Todo 관리 API 생성 완료
- [ ] Step 2.3: Agent 관리 API 생성 완료
- [ ] Step 2.4: main.py 라우터 등록 완료

### Phase 3 완료 확인
- [ ] Step 3.1: Unit Tests 완료
- [ ] Step 3.2: Integration Tests 완료
- [ ] Step 3.3: 성능 테스트 완료

### 최종 확인
- [ ] 모든 테스트 통과
- [ ] Swagger 문서 생성 확인
- [ ] README 업데이트
- [ ] Git commit

---

**다음 단계**: QUESTIONS_251106.md의 모든 항목 확인 후 구현 시작
