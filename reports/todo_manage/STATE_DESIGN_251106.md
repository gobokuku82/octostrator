# State 구조 상세 설계

**작성일:** 2025-11-06
**버전:** 1.0

---

## 📋 목차

1. [현재 State 구조](#현재-state-구조)
2. [개선된 State 구조](#개선된-state-구조)
3. [Reducer 함수 명세](#reducer-함수-명세)
4. [StateHelper 클래스](#statehelper-클래스)
5. [마이그레이션 계획](#마이그레이션-계획)

---

## 📊 현재 State 구조

### 기존 OctostratorState

```python
# 위치: backend/app/octostrator/states/ (여러 파일에 분산)

# 현재는 간단한 dict 형태
{
    # User input
    "user_query": str,
    "session_id": str,
    "output_format": str,

    # Resources
    "llm": Any,
    "checkpointer": Any,
    "context": dict,

    # State tracking
    "plan": dict,
    "todos": list,
    "execution_results": dict,
    "final_response": str,

    # Flags
    "plan_valid": bool,
    "requires_approval": bool,
    "error": Optional[str]
}
```

### 문제점

1. **History 없음**
   - `plan`이 변경되면 이전 plan은 사라짐
   - `todos`가 수정되면 원본을 알 수 없음

2. **타임스탬프 없음**
   - 언제 어떤 작업이 수행되었는지 알 수 없음

3. **사용자 개입 추적 안 됨**
   - 사용자가 언제 무엇을 수정했는지 기록 없음

4. **Step 정보 없음**
   - "4번 작업이 뭐였지?" 같은 질문에 답변 불가

---

## 🆕 개선된 State 구조

### 새로운 OctostratorState

```python
from typing import Annotated, TypedDict, Optional, Any, List, Dict
from datetime import datetime

# 커스텀 Reducer들 (reducers.py에서 import)
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)

class OctostratorState(TypedDict):
    # ===== 기존 필드 (변경 없음) =====

    # User input
    user_query: str
    session_id: str
    output_format: str  # "chat" | "graph" | "report"

    # Resources
    llm: Any
    checkpointer: Any
    context: dict  # {"auto_approve": bool, ...}

    # Current state (최신 상태만)
    plan: dict
    todos: Annotated[list, merge_todos_smart]  # ← Reducer 추가!
    execution_results: dict
    final_response: str

    # Flags
    plan_valid: bool
    requires_approval: bool
    error: Optional[str]

    # ===== 신규 필드 (History Tracking) =====

    # 작업 내역 (모든 노드 실행 기록)
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]
    # 예시: [
    #   {
    #     "step": 1,
    #     "action": "cognitive_layer_node",
    #     "timestamp": "2025-11-06T09:30:15.123456",
    #     "result": {"plan": {...}},
    #     "duration_ms": 250
    #   },
    #   {
    #     "step": 2,
    #     "action": "todo_layer_node",
    #     "timestamp": "2025-11-06T09:30:16.456789",
    #     "result": {"todos": [...]},
    #     "duration_ms": 180
    #   },
    #   ...
    # ]

    # Plan 변경 히스토리
    plan_history: Annotated[List[Dict], track_plan_changes]
    # 예시: [
    #   {
    #     "version": 1,
    #     "plan": {"goal": "점심 추천", "steps": [...]},
    #     "timestamp": "2025-11-06T09:30:15.123456",
    #     "reason": "initial_creation",
    #     "modified_by": "system"
    #   },
    #   {
    #     "version": 2,
    #     "plan": {"goal": "점심 + 운동 추천", "steps": [...]},
    #     "timestamp": "2025-11-06T09:35:20.000000",
    #     "reason": "user_modification",
    #     "modified_by": "user_abc123"
    #   },
    #   ...
    # ]

    # 사용자 개입 기록
    user_interactions: Annotated[List[Dict], track_user_interactions]
    # 예시: [
    #   {
    #     "type": "interrupt",
    #     "timestamp": "2025-11-06T09:32:00.000000",
    #     "reason": "user_requested",
    #     "details": {"message": "잠깐 멈춰"}
    #   },
    #   {
    #     "type": "modify_todo",
    #     "timestamp": "2025-11-06T09:33:15.000000",
    #     "details": {
    #       "action": "delete",
    #       "todo_id": "uuid-123",
    #       "todo": {"task": "칼로리 계산"}
    #     }
    #   },
    #   {
    #     "type": "resume",
    #     "timestamp": "2025-11-06T09:34:00.000000",
    #     "details": {"approved": true}
    #   },
    #   ...
    # ]

    # 메타데이터
    created_at: str  # 세션 생성 시각
    updated_at: str  # 마지막 업데이트 시각
    total_steps: int  # 총 실행된 step 수
```

### State 크기 추정

```python
# 평균 세션 추정:
# - action_history: 약 20개 항목 (노드 실행)
# - plan_history: 약 3개 항목 (초기 + 수정 1-2회)
# - user_interactions: 약 5개 항목
# - todos: 약 10개 항목

# 각 항목 크기:
# - action: ~500 bytes (JSON)
# - plan: ~1KB
# - interaction: ~300 bytes
# - todo: ~200 bytes

# 총 크기 = 20*500 + 3*1000 + 5*300 + 10*200
#         = 10,000 + 3,000 + 1,500 + 2,000
#         = 16,500 bytes ≈ 16 KB

# ✅ PostgreSQL에 저장하기에 적절한 크기
```

---

## ⚙️ Reducer 함수 명세

### 1. add_with_timestamp_and_step

**목적**: 작업 내역에 타임스탬프와 step 번호 자동 추가

```python
def add_with_timestamp_and_step(
    existing: Optional[List[Dict]],
    new: List[Dict]
) -> List[Dict]:
    """
    작업 내역에 메타데이터 추가

    Args:
        existing: 기존 action_history
        new: 새로 추가할 작업들

    Returns:
        병합된 작업 내역

    추가되는 메타데이터:
        - timestamp: ISO 8601 형식
        - step: 1부터 시작하는 순차 번호
    """
    from datetime import datetime

    if existing is None:
        existing = []

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


# 사용 예시
class State(TypedDict):
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]

# Node에서 사용
def some_node(state):
    # 작업 기록 추가 (타임스탬프/step은 자동)
    state["action_history"] = [{
        "action": "cognitive_layer_node",
        "result": {"plan": state["plan"]},
        "duration_ms": 250
    }]
    return state
```

### 2. merge_todos_smart

**목적**: Todo를 ID 기준으로 병합, 중복 제거, 메타데이터 자동 추가

```python
def merge_todos_smart(
    existing: Optional[List[Dict]],
    new: List[Dict]
) -> List[Dict]:
    """
    Todo를 스마트하게 병합

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
    """
    import uuid
    from datetime import datetime

    if existing is None:
        existing = []

    # ID를 key로 하는 dict 생성
    todo_dict = {}
    for todo in existing:
        todo_id = todo.get("id")
        if todo_id:
            todo_dict[todo_id] = todo

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
            # step은 기존 값 유지
            todo["step"] = existing_todo.get("step", max_step + 1)
            # created_at 유지
            todo["created_at"] = existing_todo.get("created_at", now)
            # updated_at 갱신
            todo["updated_at"] = now
        else:
            # 신규 항목
            max_step += 1
            todo["step"] = max_step
            todo["created_at"] = now
            todo["updated_at"] = now
            # 기본 status
            if "status" not in todo:
                todo["status"] = "pending"

        # dict에 저장
        todo_dict[todo_id] = todo

    # 리스트로 변환 및 정렬
    result = list(todo_dict.values())
    result.sort(key=lambda x: x.get("step", 999))

    return result


# 사용 예시
class State(TypedDict):
    todos: Annotated[List[Dict], merge_todos_smart]

# Node에서 사용
def todo_layer_node(state):
    # ID 없이 추가 가능 (자동 생성됨)
    state["todos"] = [
        {"task": "준비운동", "agent": "WorkoutAgent"},
        {"task": "본운동", "agent": "WorkoutAgent"}
    ]
    return state

# 나중에 수정
def modify_todo(state, todo_id, updates):
    # 같은 ID로 업데이트하면 병합됨
    state["todos"] = [
        {"id": todo_id, **updates}
    ]
    return state
```

### 3. track_plan_changes

**목적**: Plan 변경 사항을 버전 관리하며 추적

```python
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
    """
    from datetime import datetime

    if existing is None:
        existing = []

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


# 사용 예시
class State(TypedDict):
    plan: dict  # 현재 plan
    plan_history: Annotated[List[Dict], track_plan_changes]

# Node에서 사용
def cognitive_layer_node(state):
    new_plan = {"goal": "점심 추천", "steps": [...]}

    # 현재 plan 업데이트
    state["plan"] = new_plan

    # History에 기록
    state["plan_history"] = [{
        "plan": new_plan,
        "reason": "initial_creation"
    }]

    return state

# 사용자가 수정
def user_modify_plan(state, modified_plan, user_id):
    state["plan"] = modified_plan
    state["plan_history"] = [{
        "plan": modified_plan,
        "reason": "user_modification",
        "modified_by": user_id
    }]
    return state
```

### 4. track_user_interactions

**목적**: 사용자 개입 내역 기록

```python
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

    Args:
        existing: 기존 user_interactions
        new: 새로운 개입 기록

    Returns:
        누적된 개입 내역
    """
    from datetime import datetime

    if existing is None:
        existing = []

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


# 사용 예시
class State(TypedDict):
    user_interactions: Annotated[List[Dict], track_user_interactions]

# 사용자가 중단
def interrupt_execution(state, reason):
    state["requires_approval"] = True
    state["user_interactions"] = [{
        "type": "interrupt",
        "reason": reason,
        "details": {"message": "사용자 요청으로 중단"}
    }]
    return state

# 사용자가 Todo 수정
def user_modify_todo(state, todo_id, action, details):
    state["user_interactions"] = [{
        "type": "modify_todo",
        "details": {
            "action": action,  # "add" | "delete" | "update"
            "todo_id": todo_id,
            **details
        }
    }]
    return state
```

---

## 🛠️ StateHelper 클래스

### 목적

State를 쉽게 조회/분석할 수 있는 헬퍼 함수 모음

### 위치

`backend/app/octostrator/states/state_helpers.py`

### 구현

```python
from typing import Dict, List, Optional, Any
from datetime import datetime


class StateHelpers:
    """State 조회 및 분석 헬퍼 클래스"""

    @staticmethod
    def get_action_at_step(state: Dict, step: int) -> Optional[Dict]:
        """
        특정 step의 작업 조회

        Args:
            state: OctostratorState
            step: step 번호 (1부터 시작)

        Returns:
            해당 step의 작업 정보, 없으면 None
        """
        history = state.get("action_history", [])
        for action in history:
            if action.get("step") == step:
                return action
        return None

    @staticmethod
    def get_all_actions_summary(state: Dict) -> str:
        """
        모든 작업 내역 요약

        Returns:
            읽기 쉬운 형태의 요약 문자열
        """
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
        """
        Todo 상태 통계

        Returns:
            {
                "total": 전체 개수,
                "completed": 완료 개수,
                "failed": 실패 개수,
                "pending": 대기 개수,
                "in_progress": 진행 중 개수,
                "progress": 진행률 (0.0 ~ 1.0)
            }
        """
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
        """
        특정 버전의 Plan 조회

        Args:
            state: OctostratorState
            version: Plan 버전 (1부터 시작)

        Returns:
            해당 버전의 Plan, 없으면 None
        """
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
        """
        사용자 개입 내역 요약

        Returns:
            개입 내역 리스트 (읽기 쉬운 형태)
        """
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
    def get_session_timeline(state: Dict) -> List[Dict]:
        """
        전체 세션의 타임라인 생성

        Returns:
            시간순으로 정렬된 모든 이벤트
            [
                {"time": "09:30:15", "type": "action", "content": "..."},
                {"time": "09:30:20", "type": "user", "content": "..."},
                ...
            ]
        """
        events = []

        # Action history
        for action in state.get("action_history", []):
            events.append({
                "time": action.get("timestamp", ""),
                "type": "action",
                "content": action.get("action", ""),
                "step": action.get("step", 0)
            })

        # Plan history
        for plan in state.get("plan_history", []):
            events.append({
                "time": plan.get("timestamp", ""),
                "type": "plan",
                "content": f"Plan v{plan.get('version', '')} - {plan.get('reason', '')}",
                "step": None
            })

        # User interactions
        for interaction in state.get("user_interactions", []):
            events.append({
                "time": interaction.get("timestamp", ""),
                "type": "user",
                "content": interaction.get("type", ""),
                "step": None
            })

        # 시간순 정렬
        events.sort(key=lambda x: x["time"])

        return events

    @staticmethod
    def get_execution_summary(state: Dict) -> Dict[str, Any]:
        """
        실행 상황 전체 요약

        Returns:
            {
                "session_id": "...",
                "created_at": "...",
                "duration": "...",
                "total_steps": 10,
                "todo_status": {...},
                "plan_version": 2,
                "user_interactions": 3,
                "status": "in_progress" | "completed" | "error"
            }
        """
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

---

## 🔄 마이그레이션 계획

### Step 1: Reducer 함수 작성

**파일**: `backend/app/octostrator/states/reducers.py` (신규 생성)

```python
# 4개 함수 구현:
# - add_with_timestamp_and_step
# - merge_todos_smart
# - track_plan_changes
# - track_user_interactions
```

### Step 2: State 정의 파일 생성

**파일**: `backend/app/octostrator/states/octostrator_state.py` (신규 생성)

```python
from typing import Annotated, TypedDict, Optional, Any, List, Dict
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)

class OctostratorState(TypedDict):
    # ... 전체 정의
```

### Step 3: StateHelper 클래스 생성

**파일**: `backend/app/octostrator/states/state_helpers.py` (신규 생성)

```python
class StateHelpers:
    # ... 모든 헬퍼 메서드
```

### Step 4: Octostrator Graph 업데이트

**파일**: `backend/app/octostrator/supervisors/octostrator/octostrator_graph.py` (수정)

```python
from backend.app.octostrator.states.octostrator_state import OctostratorState

def build_octostrator_graph(checkpointer=None):
    # StateGraph에 OctostratorState 적용
    graph = StateGraph(OctostratorState)
    # ...
```

### Step 5: 각 Layer Node에서 History 기록

**파일**: `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py` (수정)

```python
from datetime import datetime

async def cognitive_layer_node(state: OctostratorState) -> OctostratorState:
    start_time = datetime.now()

    # 기존 로직
    # ...

    # History 기록
    end_time = datetime.now()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    state["action_history"] = [{
        "action": "cognitive_layer_node",
        "result": {"plan": state["plan"]},
        "duration_ms": duration_ms
    }]

    # Plan history 기록
    state["plan_history"] = [{
        "plan": state["plan"],
        "reason": "initial_creation"
    }]

    return state
```

### Step 6: API 업데이트

**파일**: `backend/app/api/sessions.py` (수정)

```python
from backend.app.octostrator.states.state_helpers import StateHelpers

@router.get("/{thread_id}/summary")
async def get_summary(thread_id: str):
    state = await graph.aget_state(config)
    return StateHelpers.get_execution_summary(state.values)
```

---

## ✅ 체크리스트

구현 전 확인 사항:

- [ ] Reducer 함수 4개 이해함
- [ ] StateHelper 클래스 메서드 확인함
- [ ] 마이그레이션 순서 이해함
- [ ] 기존 코드와의 호환성 확인함
- [ ] 테스트 계획 수립함

---

**다음 단계**: `API_DESIGN_251106.md`에서 API 상세 명세 확인
