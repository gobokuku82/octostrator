# Memory, Checkpointer, TodoList 아키텍처 가이드

## 목차
1. [개념 정리](#개념-정리)
2. [Short-term Memory vs Checkpointer](#short-term-memory-vs-checkpointer)
3. [Long-term Memory와 DB Schema](#long-term-memory와-db-schema)
4. [TodoList 관리 전략](#todolist-관리-전략)
5. [구현 계획](#구현-계획)

---

## 개념 정리

### 핵심 구분

```
┌─────────────────────────────────────────────────┐
│ 1. State (작업 공간)                             │
│    - TypedDict                                  │
│    - 노드 간 데이터 전달                          │
│    - 휘발성 (실행 중에만 존재)                     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 2. Short-term Memory (세션 메모리)                │
│    - Checkpointer가 담당                         │
│    - State 스냅샷 저장                           │
│    - 세션 내 복구용                               │
│    - DB Schema 불필요 (별도 저장소)                │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 3. Long-term Memory (지식 베이스)                 │
│    - 세션 간 공유되는 지식                         │
│    - 사용자 선호도, 과거 상담 이력                  │
│    - DB Schema 필요 ✅                           │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 4. Context (설정)                                │
│    - DB Schema와 매핑 ✅                         │
│    - session_id, user_id 등                     │
└─────────────────────────────────────────────────┘
```

---

## Short-term Memory vs Checkpointer

### ❌ 오해: "Short-term Memory와 Checkpointer는 다르다"
### ✅ 진실: "Short-term Memory = Checkpointer 구현"

```python
Short-term Memory (개념)
         ↓
    Checkpointer (LangGraph 구현체)
         ↓
   AsyncSqliteSaver, MemorySaver 등 (구체적 저장소)
```

### 1. Checkpointer란?

LangGraph에서 **State 스냅샷을 저장/복구**하는 메커니즘입니다.

```python
# LangGraph Checkpointer 계층

┌─────────────────────────────────────┐
│  BaseCheckpointSaver (추상 인터페이스) │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┬──────────────────┬─────────────┐
    ↓                     ↓                  ↓             ↓
MemorySaver      AsyncSqliteSaver    PostgresSaver   RedisSaver
(메모리)         (SQLite)            (PostgreSQL)    (Redis)
```

### 2. Short-term Memory = Checkpointer

```python
# Short-term Memory는 Checkpointer로 구현됩니다

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

class TeamSupervisor:
    def __init__(self):
        # Short-term Memory 구현
        self.checkpointer = AsyncSqliteSaver.from_conn_string(
            "short_term_memory.db"  # 세션별 State 저장
        )

        self.app = workflow.compile(checkpointer=self.checkpointer)

# 사용 시
result = await supervisor.invoke(
    state,
    config={
        "configurable": {
            "thread_id": f"session_{session_id}"  # 세션별 메모리
        }
    }
)

# 자동으로 State가 저장됨
# - 각 노드 실행 후 스냅샷
# - 에러 발생 시 복구 가능
# - 중단 후 재개 가능
```

### 3. Checkpointer의 역할

```python
# ============================================
# Checkpointer가 저장하는 것
# ============================================

{
    "thread_id": "session_abc-123",
    "checkpoint_id": "checkpoint_001",
    "state": {
        # 전체 State 스냅샷
        "session_id": "abc-123",
        "user_query": "전세 5억 적정해?",
        "search_results": [...],  # 중간 결과도 포함
        "current_team": "analysis_team",
        "team_results": {...}
    },
    "next_node": "analyze_data",  # 다음 실행 노드
    "metadata": {
        "timestamp": "2025-10-06T...",
        "step": 5
    }
}
```

### 4. DB Schema 불필요!

```python
# ❌ 이런 테이블 만들 필요 없음
Table short_term_memory {
    session_id uuid
    state_snapshot json
    checkpoint_id varchar
}

# ✅ Checkpointer가 알아서 저장
# - MemorySaver: 메모리에만 (재시작 시 소실)
# - AsyncSqliteSaver: SQLite 파일 (영속)
# - PostgresSaver: PostgreSQL (영속)
```

---

## Long-term Memory와 DB Schema

### Long-term Memory는 **DB Schema 필요** ✅

```python
# Long-term Memory = 세션을 넘어서는 지식

1. 사용자 선호도
   - "이 사용자는 강남 선호"
   - "투자 목적 위주 상담"

2. 과거 상담 이력
   - "3개월 전 강남 아파트 문의"
   - "전세금 5억 예산"

3. 학습된 패턴
   - "이 사용자는 법률 설명 상세히 원함"
   - "숫자보다 그래프 선호"
```

### DB Schema 설계

```sql
-- ============================================
-- Long-term Memory 테이블
-- ============================================

-- 1. 사용자 선호도
Table user_preferences {
    id integer [primary key, increment]
    user_id integer [not null, ref: > users.id]
    preference_key varchar(50) [not null, note: 'preferred_region, investment_style']
    preference_value text [not null, note: 'JSON 형태']
    confidence float [default: 1.0, note: '신뢰도 (0.0-1.0)']
    created_at timestamp [default: `now()`]
    updated_at timestamp

    indexes {
        (user_id, preference_key) [unique]
    }
}

-- 2. 대화 요약 (장기 기억)
Table conversation_summaries {
    id integer [primary key, increment]
    user_id integer [not null, ref: > users.id]
    session_id uuid [not null, ref: > chat_sessions.id]
    summary text [not null, note: '대화 요약']
    key_topics text[] [note: '주요 토픽 배열']
    entities_mentioned text[] [note: '언급된 엔티티 (지역, 부동산 등)']
    created_at timestamp [default: `now()`]

    indexes {
        user_id
        (user_id, created_at)
    }
}

-- 3. 사용자 인사이트
Table user_insights {
    id integer [primary key, increment]
    user_id integer [not null, ref: > users.id]
    insight_type varchar(50) [not null, note: 'budget, region_preference, urgency']
    insight_value text [not null]
    source varchar(50) [note: '출처: conversation, explicit, inferred']
    confidence float [default: 0.5]
    valid_until timestamp [note: '유효기간']
    created_at timestamp [default: `now()`]

    indexes {
        user_id
        (user_id, insight_type)
    }
}

-- 4. 실체 기록 (사용자가 관심있는 부동산 등)
Table user_entity_history {
    id integer [primary key, increment]
    user_id integer [not null, ref: > users.id]
    entity_type varchar(50) [not null, note: 'real_estate, region, contract']
    entity_id integer [note: '참조 ID (예: real_estates.id)']
    interaction_type varchar(20) [not null, note: 'viewed, searched, favorited']
    interaction_count integer [default: 1]
    last_interaction_at timestamp [default: `now()`]
    created_at timestamp [default: `now()`]

    indexes {
        (user_id, entity_type)
        (user_id, last_interaction_at)
    }
}
```

### Long-term Memory 사용 패턴

```python
# ============================================
# Long-term Memory 활용
# ============================================

async def create_state_with_long_term_memory(
    db: Session,
    session_id: str,
    user_id: int,
    user_message: str
) -> MainSupervisorState:
    """Long-term Memory를 포함한 State 생성"""

    # 1. 사용자 선호도 조회 (Long-term Memory)
    preferences = db.query(UserPreference).filter_by(
        user_id=user_id
    ).all()

    user_prefs = {
        pref.preference_key: json.loads(pref.preference_value)
        for pref in preferences
    }

    # 2. 과거 대화 요약 조회 (최근 5개 세션)
    past_summaries = db.query(ConversationSummary).filter_by(
        user_id=user_id
    ).order_by(
        ConversationSummary.created_at.desc()
    ).limit(5).all()

    # 3. 사용자 인사이트 조회
    insights = db.query(UserInsight).filter_by(
        user_id=user_id
    ).filter(
        or_(
            UserInsight.valid_until.is_(None),
            UserInsight.valid_until > datetime.now()
        )
    ).all()

    user_insights = {
        insight.insight_type: {
            "value": insight.insight_value,
            "confidence": insight.confidence
        }
        for insight in insights
    }

    # 4. State 생성 (Long-term Memory 포함)
    state = {
        # 기본 정보
        "session_id": session_id,
        "user_id": user_id,
        "user_query": user_message,

        # Short-term (현재 세션)
        "conversation_history": [...],  # 현재 세션 대화

        # Long-term Memory (DB에서 조회)
        "user_preferences": user_prefs,  # {"preferred_region": "강남", ...}
        "past_contexts": [
            {
                "summary": s.summary,
                "topics": s.key_topics,
                "date": s.created_at.isoformat()
            }
            for s in past_summaries
        ],
        "user_insights": user_insights,  # {"budget": {"value": "5-10억", ...}}

        # 작업 필드
        "search_results": [],
        "final_answer": ""
    }

    return state
```

---

## TodoList 관리 전략

### 현재 상황 분석

```python
# 현재: State에서 실행 계획만 선언

class MainSupervisorState(TypedDict):
    execution_plan: List[Dict[str, Any]]  # 계획만 있음
    # [
    #   {"team": "search_team", "priority": 1},
    #   {"team": "analysis_team", "priority": 2}
    # ]
```

### 목표: Checkpointer + TodoList 통합

```python
# 목표: 실행 계획 + 진행 상황 추적

class MainSupervisorState(TypedDict):
    # 계획
    execution_plan: List[TodoItem]

    # 진행 상황 (Checkpointer가 추적)
    todo_status: Dict[str, TodoStatus]

    # 현재 작업
    current_todo: Optional[str]
    completed_todos: List[str]
```

### TodoList 타입 정의

```python
# backend/app/service_agent/foundation/todo_types.py

from typing import TypedDict, Literal, Optional, List
from datetime import datetime

class TodoItem(TypedDict):
    """단일 Todo 아이템"""
    id: str  # "todo_001"
    team: str  # "search_team"
    action: str  # "법률 검색"
    description: str  # "임대차보호법 관련 조항 검색"
    priority: int  # 1, 2, 3
    dependencies: List[str]  # ["todo_001", "todo_002"]
    estimated_time: Optional[float]  # 예상 소요 시간 (초)

class TodoStatus(TypedDict):
    """Todo 실행 상태"""
    todo_id: str
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    result_summary: Optional[str]

class TodoProgress(TypedDict):
    """전체 진행 상황"""
    total: int
    pending: int
    in_progress: int
    completed: int
    failed: int
    progress_percentage: float
```

### State 통합

```python
# backend/app/service_agent/foundation/separated_states.py

from app.service_agent.foundation.todo_types import TodoItem, TodoStatus, TodoProgress

class MainSupervisorState(TypedDict):
    """메인 슈퍼바이저 상태 (TodoList 통합)"""

    # 기본 정보
    session_id: str
    user_id: int
    user_query: str

    # ============================================
    # TodoList 관리
    # ============================================
    # 실행 계획 (PlanningAgent가 생성)
    execution_plan: List[TodoItem]

    # Todo 상태 추적
    todo_status: Dict[str, TodoStatus]  # {"todo_001": {...}, ...}

    # 현재 실행 중
    current_todo_id: Optional[str]

    # 진행 상황
    todo_progress: TodoProgress

    # ============================================
    # 팀 결과
    # ============================================
    team_results: Dict[str, Any]

    # ============================================
    # 최종 결과
    # ============================================
    final_answer: str
    confidence_score: Optional[float]
```

### TodoList 워크플로우

```python
# ============================================
# 1. PlanningAgent: Todo 생성
# ============================================

async def create_execution_plan_node(state: MainSupervisorState):
    """실행 계획 수립 (Todo 생성)"""

    # LLM으로 계획 수립
    plan = await llm.generate_plan(state["user_query"])

    # TodoItem 생성
    todos = [
        TodoItem(
            id=f"todo_{i:03d}",
            team="search_team",
            action="법률 검색",
            description="임대차보호법 조항 검색",
            priority=1,
            dependencies=[],
            estimated_time=5.0
        )
        for i, task in enumerate(plan["tasks"])
    ]

    # State 업데이트
    state["execution_plan"] = todos
    state["todo_status"] = {
        todo["id"]: TodoStatus(
            todo_id=todo["id"],
            status="pending",
            started_at=None,
            completed_at=None,
            error=None,
            result_summary=None
        )
        for todo in todos
    }
    state["todo_progress"] = TodoProgress(
        total=len(todos),
        pending=len(todos),
        in_progress=0,
        completed=0,
        failed=0,
        progress_percentage=0.0
    )

    return state


# ============================================
# 2. Supervisor: Todo 실행 관리
# ============================================

async def execute_next_todo_node(state: MainSupervisorState):
    """다음 Todo 실행"""

    # 실행 가능한 Todo 찾기
    next_todo = find_next_executable_todo(
        state["execution_plan"],
        state["todo_status"]
    )

    if not next_todo:
        # 모든 Todo 완료
        state["status"] = "all_todos_completed"
        return state

    # Todo 시작
    todo_id = next_todo["id"]
    state["current_todo_id"] = todo_id
    state["todo_status"][todo_id]["status"] = "in_progress"
    state["todo_status"][todo_id]["started_at"] = datetime.now().isoformat()

    # 진행 상황 업데이트
    update_progress(state)

    return state


def find_next_executable_todo(
    plan: List[TodoItem],
    status: Dict[str, TodoStatus]
) -> Optional[TodoItem]:
    """실행 가능한 다음 Todo 찾기"""

    for todo in sorted(plan, key=lambda t: t["priority"]):
        # 이미 완료/실행 중이면 스킵
        if status[todo["id"]]["status"] in ["completed", "in_progress"]:
            continue

        # 의존성 확인
        dependencies_met = all(
            status[dep_id]["status"] == "completed"
            for dep_id in todo["dependencies"]
        )

        if dependencies_met:
            return todo

    return None


# ============================================
# 3. ExecutionAgent: Todo 완료 처리
# ============================================

async def search_team_wrapper(state: MainSupervisorState):
    """SearchTeam 실행 및 Todo 업데이트"""

    current_todo_id = state["current_todo_id"]

    try:
        # 실제 작업 수행
        result = await search_executor.execute(state)

        # Todo 완료 처리
        state["todo_status"][current_todo_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result_summary": f"검색 완료: {result.get('total_results')}건"
        })

        # 진행 상황 업데이트
        update_progress(state)

    except Exception as e:
        # Todo 실패 처리
        state["todo_status"][current_todo_id].update({
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "error": str(e)
        })

    state["current_todo_id"] = None
    return state


def update_progress(state: MainSupervisorState):
    """진행 상황 업데이트"""
    statuses = state["todo_status"].values()

    state["todo_progress"] = TodoProgress(
        total=len(statuses),
        pending=sum(1 for s in statuses if s["status"] == "pending"),
        in_progress=sum(1 for s in statuses if s["status"] == "in_progress"),
        completed=sum(1 for s in statuses if s["status"] == "completed"),
        failed=sum(1 for s in statuses if s["status"] == "failed"),
        progress_percentage=sum(
            1 for s in statuses if s["status"] == "completed"
        ) / len(statuses) * 100
    )
```

### Checkpointer와 TodoList 통합

```python
# ============================================
# Checkpointer가 TodoList 상태 자동 저장
# ============================================

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

class TeamSupervisor:
    def __init__(self):
        self.checkpointer = AsyncSqliteSaver.from_conn_string(
            "checkpoints.db"
        )

        self.app = workflow.compile(checkpointer=self.checkpointer)

    async def invoke(self, state, config):
        """실행 (자동 체크포인팅)"""

        # 각 노드 실행 후 State가 자동 저장됨
        # - execution_plan
        # - todo_status
        # - todo_progress
        # 모두 Checkpointer에 저장!

        result = await self.app.ainvoke(state, config)
        return result

    async def resume_from_checkpoint(self, thread_id: str):
        """중단된 작업 재개"""

        # Checkpointer에서 마지막 State 복구
        # - 어느 Todo까지 완료했는지
        # - 다음 실행할 Todo는 무엇인지
        # 모두 복구됨!

        state = await self.checkpointer.aget(thread_id)
        return await self.app.ainvoke(state, {"thread_id": thread_id})
```

---

## 구현 계획

### Phase 1: Checkpointer 구현 (Short-term Memory)

```python
# 1. AsyncSqliteSaver 설정
# backend/app/service_agent/supervisor/team_supervisor.py

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

class TeamSupervisor:
    def __init__(self, db: Session = None):
        self.db = db

        # Checkpointer 초기화
        self.checkpointer = AsyncSqliteSaver.from_conn_string(
            "checkpoints/short_term_memory.db"
        )

        # Workflow 컴파일 (checkpointer 연결)
        self.app = self._build_workflow().compile(
            checkpointer=self.checkpointer
        )

# 2. 실행 시 thread_id 지정
result = await supervisor.invoke(
    state,
    config={
        "configurable": {
            "thread_id": f"session_{session_id}"
        }
    }
)

# 3. 자동으로 State 스냅샷 저장됨!
```

### Phase 2: Long-term Memory DB Schema 추가

```sql
-- migrations/add_long_term_memory.sql

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    preference_key VARCHAR(50) NOT NULL,
    preference_value TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE(user_id, preference_key)
);

CREATE TABLE conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL REFERENCES chat_sessions(id),
    summary TEXT NOT NULL,
    key_topics TEXT[],
    entities_mentioned TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_insights (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    insight_type VARCHAR(50) NOT NULL,
    insight_value TEXT NOT NULL,
    source VARCHAR(50),
    confidence FLOAT DEFAULT 0.5,
    valid_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_conversation_summaries_user_id ON conversation_summaries(user_id);
CREATE INDEX idx_user_insights_user_id ON user_insights(user_id);
```

### Phase 3: TodoList 통합

```python
# 1. todo_types.py 생성 (위 코드 참조)

# 2. separated_states.py 업데이트
class MainSupervisorState(TypedDict):
    execution_plan: List[TodoItem]
    todo_status: Dict[str, TodoStatus]
    todo_progress: TodoProgress
    current_todo_id: Optional[str]
    # ... 나머지 필드

# 3. Supervisor에 Todo 관리 로직 추가
# - create_execution_plan_node
# - execute_next_todo_node
# - update_progress

# 4. Checkpointer가 자동으로 Todo 상태 저장
```

---

## 요약

### 1. Short-term Memory

```python
Short-term Memory = Checkpointer (AsyncSqliteSaver)
- DB Schema 불필요 ❌
- State 스냅샷 자동 저장
- 세션 내 복구용
- thread_id로 관리
```

### 2. Long-term Memory

```python
Long-term Memory = DB 테이블 ✅
- user_preferences
- conversation_summaries
- user_insights
- user_entity_history

세션을 넘어서는 지식 저장
```

### 3. TodoList 관리

```python
TodoList = State + Checkpointer
- State에 execution_plan, todo_status 추가
- Checkpointer가 진행 상황 자동 저장
- 중단 후 재개 가능
- DB Schema 불필요 (Checkpointer가 처리)
```

### 4. 전체 구조

```
┌─────────────────────────────────────┐
│ State (작업 공간)                    │
│ - TodoList 포함                     │
│ - 실행 중 데이터                     │
└────────┬────────────────────────────┘
         │
         ↓ (저장)
┌─────────────────────────────────────┐
│ Short-term Memory (Checkpointer)    │
│ - AsyncSqliteSaver                  │
│ - State 스냅샷                      │
│ - DB Schema 불필요 ❌                │
└─────────────────────────────────────┘

         +

┌─────────────────────────────────────┐
│ Long-term Memory (DB)               │
│ - user_preferences                  │
│ - conversation_summaries            │
│ - DB Schema 필요 ✅                  │
└─────────────────────────────────────┘

         +

┌─────────────────────────────────────┐
│ Context (설정)                       │
│ - session_id, user_id               │
│ - DB Schema와 매핑 ✅                │
└─────────────────────────────────────┘
```

---

*작성일: 2025-10-06*
*버전: 1.0*
