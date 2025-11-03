# LangGraph Checkpointer DB Schema

**작성일**: 2025-01-03
**LangGraph 버전**: 1.0+
**langgraph-checkpoint-postgres**: 3.0.0

---

## 개요

LangGraph의 PostgreSQL Checkpointer는 **자동으로 4개의 테이블을 생성**합니다.
이 스키마는 **하드코딩되어 있으며 불변**입니다. 사용자가 직접 수정할 수 없습니다.

### 주요 특징

- ✅ **자동 생성**: `.setup()` 메서드 호출 시 자동으로 테이블 생성
- ✅ **버전 관리**: `checkpoint_migrations` 테이블로 마이그레이션 추적
- ✅ **최적화**: 채널별 versioning으로 변경된 값만 저장
- ✅ **에러 복구**: pending writes 저장으로 실패한 노드 재실행 방지

---

## DB Diagram (dbdiagram.io)

아래 코드를 [dbdiagram.io](https://dbdiagram.io)에 붙여넣으면 ER Diagram을 볼 수 있습니다.

```dbml
Table checkpoint_migrations {
  v INTEGER [pk]
}

Table checkpoints {
  thread_id TEXT [not null]
  checkpoint_ns TEXT [not null]
  checkpoint_id TEXT [not null]
  parent_checkpoint_id TEXT
  type TEXT
  checkpoint JSONB [not null]
  metadata JSONB [not null]

  indexes {
    (thread_id, checkpoint_ns, checkpoint_id) [pk]
  }
}

Table checkpoint_blobs {
  thread_id TEXT [not null]
  checkpoint_ns TEXT [not null]
  channel TEXT [not null]
  version TEXT [not null]
  type TEXT [not null]
  blob BYTEA

  indexes {
    (thread_id, checkpoint_ns, channel, version) [pk]
  }
}

Table checkpoint_writes {
  thread_id TEXT [not null]
  checkpoint_ns TEXT [not null]
  checkpoint_id TEXT [not null]
  task_id TEXT [not null]
  idx INTEGER [not null]
  channel TEXT [not null]
  type TEXT
  blob BYTEA [not null]
  task_path TEXT [not null]

  indexes {
    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) [pk]
  }
}

Ref: checkpoint_blobs.(thread_id, checkpoint_ns) > checkpoints.(thread_id, checkpoint_ns)

Ref: checkpoint_writes.(thread_id, checkpoint_ns, checkpoint_id) > checkpoints.(thread_id, checkpoint_ns, checkpoint_id)

Ref: checkpoints.parent_checkpoint_id - checkpoints.checkpoint_id
```

**dbdiagram.io 사용법**:
1. [https://dbdiagram.io](https://dbdiagram.io) 접속
2. 왼쪽 에디터에 위 코드 붙여넣기
3. 자동으로 ER Diagram 생성됨
4. Export → PNG/PDF/SQL 가능

---

## 테이블 구조

### 1. checkpoint_migrations

마이그레이션 버전 추적 테이블

```sql
CREATE TABLE IF NOT EXISTS checkpoint_migrations (
  v INTEGER PRIMARY KEY
);
```

**용도**: 어떤 DB 마이그레이션이 적용되었는지 추적

---

### 2. checkpoints

메인 체크포인트 테이블 - Graph 실행 상태 저장

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
  thread_id TEXT NOT NULL,
  checkpoint_ns TEXT NOT NULL DEFAULT '',
  checkpoint_id TEXT NOT NULL,
  parent_checkpoint_id TEXT,
  type TEXT,
  checkpoint JSONB NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
```

**컬럼 설명**:
- `thread_id`: 대화 스레드 ID (세션 구분)
- `checkpoint_ns`: Checkpoint 네임스페이스 (서브그래프용)
- `checkpoint_id`: 고유 체크포인트 ID
- `parent_checkpoint_id`: 부모 체크포인트 (타임트래블용)
- `type`: 체크포인트 타입
- `checkpoint`: 실제 State 데이터 (JSONB)
- `metadata`: 메타데이터 (JSONB)

**Primary Key**: `(thread_id, checkpoint_ns, checkpoint_id)`

---

### 3. checkpoint_blobs

채널별 값 저장 테이블 (최적화용)

```sql
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
  thread_id TEXT NOT NULL,
  checkpoint_ns TEXT NOT NULL DEFAULT '',
  channel TEXT NOT NULL,
  version TEXT NOT NULL,
  type TEXT NOT NULL,
  blob BYTEA,
  PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
```

**컬럼 설명**:
- `channel`: State의 채널명 (예: `messages`)
- `version`: 버전 번호
- `type`: 데이터 타입
- `blob`: 실제 데이터 (바이너리)

**최적화 원리**:
- 각 채널 값을 개별적으로 versioning
- 변경된 값만 저장 (전체 State 저장 X)
- 읽기/쓰기 성능 향상

**Primary Key**: `(thread_id, checkpoint_ns, channel, version)`

---

### 4. checkpoint_writes

Pending writes 저장 테이블 (에러 복구용)

```sql
CREATE TABLE IF NOT EXISTS checkpoint_writes (
  thread_id TEXT NOT NULL,
  checkpoint_ns TEXT NOT NULL DEFAULT '',
  checkpoint_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  idx INTEGER NOT NULL,
  channel TEXT NOT NULL,
  type TEXT,
  blob BYTEA NOT NULL,
  task_path TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

**컬럼 설명**:
- `task_id`: 태스크 ID
- `idx`: Write 순서
- `channel`: 채널명
- `blob`: Write 데이터
- `task_path`: 태스크 경로 (ordering용)

**에러 복구 원리**:
- 노드가 실패하면 성공한 노드의 pending writes 저장
- Graph 재실행 시 성공한 노드는 재실행 안 함
- Superstep별로 write 관리

**Primary Key**: `(thread_id, checkpoint_ns, checkpoint_id, task_id, idx)`

---

## 설치 및 사용

### 1. 패키지 설치

```bash
# pyproject.toml에 추가
langgraph-checkpoint-postgres = "^3.0.0"
psycopg = {extras = ["binary"], version = "^3.0.0"}
```

### 2. DB 초기화

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import psycopg

# DB 연결 (autocommit=True 필수!)
conn = await psycopg.AsyncConnection.connect(
    config.postgres_url,
    autocommit=True,
    row_factory=psycopg.rows.dict_row
)

# Checkpointer 생성 및 테이블 자동 생성
checkpointer = AsyncPostgresSaver(conn)
await checkpointer.setup()  # 4개 테이블 자동 생성
```

**주의사항**:
- ⚠️ `autocommit=True` 필수 (테이블 생성 커밋용)
- ⚠️ `row_factory=dict_row` 권장 (딕셔너리 반환)

### 3. Graph에 Checkpointer 연결

```python
from langgraph.graph import StateGraph

workflow = StateGraph(SupervisorState)
# ... 노드 추가 ...

# Checkpointer와 함께 컴파일
graph = workflow.compile(checkpointer=checkpointer)
```

### 4. Thread ID로 대화 관리

```python
# 대화 시작
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123-session-1"}}
)

# 이어서 대화 (같은 thread_id)
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="What's my name?")]},
    config={"configurable": {"thread_id": "user-123-session-1"}}
)
# State가 자동으로 복원됨
```

---

## 핵심 기능

### 1. Session Memory
- `thread_id`로 대화 세션 구분
- 자동으로 이전 State 복원
- 멀티턴 대화 지원

### 2. Error Recovery
- 노드 실패 시 성공한 노드의 writes 저장
- 재실행 시 성공한 노드 건너뛰기
- Superstep 단위로 복구

### 3. Time Travel
- `parent_checkpoint_id`로 체크포인트 체인 생성
- 과거 시점으로 되돌아가기 가능
- Graph 실행 히스토리 탐색

### 4. Human-in-the-Loop
- Checkpointer와 결합하여 사람 승인 대기
- 승인 후 이어서 실행
- Interrupt 지점에서 State 저장

---

## 데이터 관리

### 자동 정리 (없음)
- ⚠️ LangGraph는 자동으로 오래된 체크포인트를 삭제하지 않음
- ⚠️ 운영 환경에서는 주기적인 정리 필요

### 수동 정리 예시
```sql
-- 30일 이상 된 체크포인트 삭제
DELETE FROM checkpoints
WHERE metadata->>'created_at' < (NOW() - INTERVAL '30 days')::text;

DELETE FROM checkpoint_blobs
WHERE (thread_id, checkpoint_ns, version) NOT IN (
    SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints
);

DELETE FROM checkpoint_writes
WHERE (thread_id, checkpoint_ns, checkpoint_id) NOT IN (
    SELECT thread_id, checkpoint_ns, checkpoint_id FROM checkpoints
);
```

---

## Phase 5 구현 계획

### 1. 의존성 추가
```toml
[project]
dependencies = [
    "langgraph-checkpoint-postgres>=3.0.0",
    "psycopg[binary]>=3.0.0"
]
```

### 2. Checkpointer 초기화 코드
```python
# backend/app/db/checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import psycopg
from backend.app.config.system import config

async def get_checkpointer():
    conn = await psycopg.AsyncConnection.connect(
        config.postgres_url,
        autocommit=True,
        row_factory=psycopg.rows.dict_row
    )
    checkpointer = AsyncPostgresSaver(conn)
    await checkpointer.setup()
    return checkpointer
```

### 3. FastAPI 엔드포인트 수정
```python
# backend/app/main.py
from backend.app.db.checkpointer import get_checkpointer

# 앱 시작 시 Checkpointer 초기화
@app.on_event("startup")
async def startup():
    global checkpointer
    checkpointer = await get_checkpointer()
    global supervisor_graph
    supervisor_graph = build_supervisor_graph().compile(checkpointer=checkpointer)

# Chat 엔드포인트에 thread_id 추가
@app.post("/chat")
async def chat(request: ChatRequest, thread_id: str):
    result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": thread_id}}
    )
    return {"response": result["messages"][-1].content}
```

---

## 참고 자료

- [LangGraph Checkpointer 공식 문서](https://langchain-ai.github.io/langgraph/reference/checkpoints/)
- [PostgreSQL Checkpointer PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/)
- [GitHub 소스코드](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-postgres)

---

## 결론

LangGraph Checkpointer는 **하드코딩된 불변 스키마**로, 사용자가 수정할 수 없습니다.

**Phase 5에서 할 일**:
1. ✅ 의존성 추가 (`langgraph-checkpoint-postgres`, `psycopg`)
2. ✅ `.setup()` 호출로 자동 테이블 생성
3. ✅ Graph 컴파일 시 checkpointer 연결
4. ✅ API에 `thread_id` 파라미터 추가

**별도 스키마 설계 불필요** - LangGraph가 모든 것을 자동으로 처리합니다.
