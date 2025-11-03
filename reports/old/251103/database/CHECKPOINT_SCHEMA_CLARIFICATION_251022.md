# Checkpoint Schema 명확화 보고서

**작성일:** 2025-10-22
**작성자:** Claude Code
**목적:** checkpoint_id 존재 여부 및 session_id vs thread_id 혼란 해소

---

## 🎯 핵심 결론

### ✅ checkpoint_id는 이미 존재합니다!
- 테이블을 다시 만들 필요 **전혀 없음**
- LangGraph가 자동 생성한 스키마가 정상 작동 중

---

## 📊 Schema 비교

### 1. DBML 문서 스키마 (설계 의도)

```dbml
Table checkpoints {
  session_id text [not null]           ← 통일된 이름 사용 의도
  checkpoint_ns text [not null, default: '']
  checkpoint_id text [not null]        ✅ 존재
  parent_checkpoint_id text            ✅ 존재
  type text
  checkpoint jsonb [not null]
  metadata jsonb [not null, default: `{}`]

  indexes {
    session_id
    (session_id, checkpoint_ns, checkpoint_id) [pk]
  }
}
```

**출처:** `backend/migrations/unified_schema.dbml` (Line 72-87)

---

### 2. 실제 데이터베이스 스키마 (LangGraph 자동 생성)

```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,             ← LangGraph 강제 사용
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,         ✅ 존재
    parent_checkpoint_id TEXT,           ✅ 존재
    type TEXT,
    checkpoint BLOB,                     -- SQLite는 BLOB
    metadata BLOB,                       -- PostgreSQL은 JSONB
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
```

**출처:** `backend/logs/app.log` (LangGraph 자동 생성 로그)

---

## 🔄 session_id vs thread_id 차이점

### 혼란의 원인

| 항목 | session_id | thread_id |
|------|------------|-----------|
| **사용처** | DBML 문서, chat_sessions 테이블 | LangGraph checkpoint 테이블 |
| **값** | `"session-{uuid}"` | `"session-{uuid}"` (동일한 값) |
| **의도** | 통일된 컬럼명으로 혼동 방지 | LangGraph 내부 표준 |
| **변경 가능** | ✅ 우리가 정의 | ❌ LangGraph 강제 |

### 왜 두 이름이 존재하나?

1. **우리의 설계 의도 (DBML):**
   ```
   chat_sessions.session_id      = "session-{uuid}"
   chat_messages.session_id      = "session-{uuid}"
   checkpoints.session_id        = "session-{uuid}"  ← 통일하고 싶었음
   ```

2. **LangGraph의 강제 사항:**
   ```python
   # LangGraph 내부 코드 (변경 불가)
   CREATE TABLE checkpoints (
       thread_id TEXT NOT NULL,  ← 하드코딩됨
       ...
   )
   ```

3. **우리의 해결책 (코드):**
   ```python
   # session_id 값을 thread_id 컬럼에 저장
   config = {
       "configurable": {
           "thread_id": session_id  # 값은 session_id, 컬럼은 thread_id
       }
   }
   ```

---

## 🧩 전체 Checkpoint 테이블 구조

### checkpoints (메인 상태 저장)

| 컬럼명 | 타입 | 필수 | 기본값 | 설명 |
|--------|------|------|--------|------|
| `thread_id` | TEXT | ✅ | - | 세션 식별자 (값: session-{uuid}) |
| `checkpoint_ns` | TEXT | ✅ | `''` | 네임스페이스 (보통 빈 문자열) |
| `checkpoint_id` | TEXT | ✅ | - | **체크포인트 고유 ID** (LangGraph 생성) |
| `parent_checkpoint_id` | TEXT | ❌ | `NULL` | 이전 체크포인트 참조 (Time Travel용) |
| `type` | TEXT | ❌ | - | 직렬화 타입 (`msgpack`, `json` 등) |
| `checkpoint` | BLOB/JSONB | ✅ | - | 상태 스냅샷 (전체 그래프 상태) |
| `metadata` | BLOB/JSONB | ✅ | `{}` | 메타데이터 (step, source, parents 등) |

**Primary Key:** `(thread_id, checkpoint_ns, checkpoint_id)`

---

### checkpoint_writes (증분 업데이트)

| 컬럼명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| `thread_id` | TEXT | ✅ | 세션 식별자 |
| `checkpoint_ns` | TEXT | ✅ | 네임스페이스 |
| `checkpoint_id` | TEXT | ✅ | **체크포인트 ID** |
| `task_id` | TEXT | ✅ | 병렬 실행 태스크 ID |
| `idx` | INTEGER | ✅ | Write 순서 번호 |
| `channel` | TEXT | ✅ | 채널명 (상태의 어느 부분) |
| `type` | TEXT | ❌ | Write 타입 |
| `blob` | BYTEA | ✅ | 업데이트 데이터 |

**Primary Key:** `(thread_id, checkpoint_ns, checkpoint_id, task_id, idx)`

---

### checkpoint_blobs (대용량 데이터)

| 컬럼명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| `thread_id` | TEXT | ✅ | 세션 식별자 |
| `checkpoint_ns` | TEXT | ✅ | 네임스페이스 |
| `channel` | TEXT | ✅ | 채널명 |
| `version` | TEXT | ✅ | Blob 버전 |
| `type` | TEXT | ✅ | Blob 타입 |
| `blob` | BYTEA | ❌ | 바이너리 데이터 (이미지, 파일 등) |

**Primary Key:** `(thread_id, checkpoint_ns, channel, version)`

---

### checkpoint_migrations (스키마 버전)

| 컬럼명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| `v` | INTEGER | ✅ | 마이그레이션 버전 번호 |

**Primary Key:** `v`

---

## 🔍 checkpoint_id 사용 예시

### 1. Checkpoint 저장 시

```python
# LangGraph가 자동 생성
checkpoint_id = "1f0a80f2-0aed-69a0-bfff-ebe5215362bc"

# INSERT 쿼리
INSERT INTO checkpoints (
    thread_id,
    checkpoint_ns,
    checkpoint_id,           ← 자동 생성된 UUID
    parent_checkpoint_id,
    type,
    checkpoint,
    metadata
) VALUES (
    'session-bfdb29ca-76fe-447d-af3e-e83c4c160920',
    '',
    '1f0a80f2-0aed-69a0-bfff-ebe5215362bc',  ← 여기
    NULL,
    'msgpack',
    <binary_data>,
    '{"source": "input", "step": -1}'
)
```

---

### 2. Checkpoint 조회 시

```python
# 최신 체크포인트 조회
SELECT thread_id, checkpoint_id, parent_checkpoint_id, checkpoint, metadata
FROM checkpoints
WHERE thread_id = 'session-xxx'
  AND checkpoint_ns = ''
ORDER BY checkpoint_id DESC
LIMIT 1;
```

**결과:**
```
thread_id: session-bfdb29ca-76fe-447d-af3e-e83c4c160920
checkpoint_id: 1f0a80f2-0aed-69a0-bfff-ebe5215362bc  ← 존재!
parent_checkpoint_id: NULL
```

---

### 3. Time Travel 시 (checkpoint_id 활용)

```python
# 1단계: 체크포인트 히스토리 조회
states = list(graph.get_state_history(config))

# 결과:
# states[0].config['configurable']['checkpoint_id'] = "1f0a80f2-0aed-69a0-..."
# states[1].config['configurable']['checkpoint_id'] = "1f0a80e1-9bcd-68a1-..."
# states[2].config['configurable']['checkpoint_id'] = "1f0a80d0-8abc-67a0-..."

# 2단계: 특정 체크포인트로 되돌아가기
old_checkpoint_config = states[2].config  # checkpoint_id 포함

# 3단계: 상태 수정
new_config = graph.update_state(
    old_checkpoint_config,  # checkpoint_id로 식별
    values={"query": "modified query"}
)

# 4단계: 그 지점부터 다시 실행
result = graph.invoke(None, new_config)
```

**내부 동작:**
```sql
-- checkpoint_id로 특정 체크포인트 로드
SELECT checkpoint, metadata
FROM checkpoints
WHERE thread_id = 'session-xxx'
  AND checkpoint_id = '1f0a80d0-8abc-67a0-...'  ← checkpoint_id 사용
```

---

## 🐛 이전 버그와의 관계

### Session Delete Bug (2025-10-21 수정)

**문제:**
```python
# 잘못된 코드 (수정 전)
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",  ← 컬럼명 오류
    {"session_id": session_id}
)
# ❌ Error: column "session_id" does not exist
```

**해결:**
```python
# 올바른 코드 (수정 후)
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),  ← 컬럼명 수정
    {"thread_id": session_id}  # 값은 session_id, 컬럼은 thread_id
)
# ✅ Success: 4 sessions deleted
```

**참고:** [SESSION_DELETE_FIX_RESULT_251021.md](SESSION_DELETE_FIX_RESULT_251021.md)

---

## 📝 DBML 수정 권장사항

### 현재 DBML (혼란 야기)

```dbml
Table checkpoints {
  session_id text [not null]  ← 실제 DB와 불일치
  ...
}
```

### 권장 DBML (실제 DB 반영)

```dbml
Table checkpoints {
  thread_id text [not null, note: 'LangGraph session identifier (값: session-{uuid})']
  checkpoint_ns text [not null, default: '', note: 'Checkpoint 네임스페이스']
  checkpoint_id text [not null, note: 'Checkpoint 고유 ID (LangGraph 자동 생성)']
  parent_checkpoint_id text [note: 'Parent checkpoint (Time Travel용)']
  type text [note: 'Serialization type (msgpack, json)']
  checkpoint blob [not null, note: 'State snapshot (BLOB in SQLite, JSONB in PostgreSQL)']
  metadata blob [not null, default: `{}`, note: 'Metadata (step, source, parents)']

  indexes {
    thread_id
    (thread_id, checkpoint_ns, checkpoint_id) [pk]
  }

  Note: '''
  LangGraph Checkpoint Storage
  - thread_id: LangGraph 내부 표준 (변경 불가)
  - 값은 우리의 session_id를 사용: "session-{uuid}"
  - checkpoint_id: LangGraph가 자동 생성 (UUID 형식)
  - parent_checkpoint_id: Time Travel 시 이전 체크포인트 추적
  '''
}
```

---

## 🎯 최종 정리

### 질문: checkpoint_id가 없는가?
**답변:** ✅ **아닙니다! checkpoint_id는 이미 존재합니다.**

### 질문: 테이블을 다시 만들어야 하나?
**답변:** ❌ **전혀 필요 없습니다. 현재 스키마가 정상입니다.**

### 혼란의 원인
1. **DBML 문서**가 `session_id`를 사용 (설계 의도)
2. **실제 DB**는 `thread_id`를 사용 (LangGraph 강제)
3. **코드**에서 `session_id` 값을 `thread_id` 컬럼에 저장
4. `checkpoint_id`는 **양쪽 모두 존재**

### 해야 할 일
- [ ] DBML 문서를 실제 DB에 맞게 수정 (선택 사항)
- [ ] 문서에 "thread_id vs session_id" 설명 추가
- [x] checkpoint_id가 존재함을 확인 ✅

### 하지 말아야 할 일
- [ ] ❌ 테이블 다시 만들기
- [ ] ❌ checkpoint_id 컬럼 추가
- [ ] ❌ 스키마 구조 변경

---

## 🔗 관련 문서

- **Session Delete Fix:** [SESSION_DELETE_FIX_RESULT_251021.md](SESSION_DELETE_FIX_RESULT_251021.md)
- **Checkpointer Guide:** [../human_in_the_loop/CHECKPOINTER_COMPLETE_GUIDE.md](../human_in_the_loop/CHECKPOINTER_COMPLETE_GUIDE.md)
- **LangGraph History:** [../human_in_the_loop/LANGGRAPH_CHECKPOINTER_HISTORY.md](../human_in_the_loop/LANGGRAPH_CHECKPOINTER_HISTORY.md)
- **DBML Schema:** [../../backend/migrations/unified_schema.dbml](../../backend/migrations/unified_schema.dbml)

---

## 📊 Checkpoint 테이블 현황

### 테이블 존재 여부

| 테이블명 | 존재 여부 | 자동 생성 | 용도 |
|----------|-----------|-----------|------|
| `checkpoints` | ✅ | LangGraph | 상태 스냅샷 |
| `checkpoint_writes` | ✅ | LangGraph | 증분 업데이트 |
| `checkpoint_blobs` | ✅ | LangGraph | 대용량 데이터 |
| `checkpoint_migrations` | ✅ | LangGraph | 스키마 버전 |

### 주요 컬럼 존재 여부

| 컬럼명 | checkpoints | checkpoint_writes | checkpoint_blobs |
|--------|-------------|-------------------|------------------|
| `thread_id` | ✅ PK | ✅ PK | ✅ PK |
| `checkpoint_ns` | ✅ PK | ✅ PK | ✅ PK |
| `checkpoint_id` | ✅ PK | ✅ PK | ❌ |
| `parent_checkpoint_id` | ✅ | ❌ | ❌ |

**모든 테이블에 필요한 컬럼이 존재합니다!**

---

**결론:** 스키마는 완벽하게 정상이며, 추가 작업이 필요 없습니다. DBML 문서만 실제 DB에 맞게 업데이트하면 더 명확해집니다.
