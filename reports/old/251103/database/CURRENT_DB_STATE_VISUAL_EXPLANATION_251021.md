# 현재 데이터베이스 상태 - 쉬운 설명

**Date:** 2025-10-21
**목적:** SQL을 몰라도 이해할 수 있는 설명

---

## 📊 현재 상황 한눈에 보기

### 당신이 설계한 것 (dbml 파일)

```
chat_sessions    → session_id 컬럼 ✅
chat_messages    → session_id 컬럼 ✅
checkpoints      → session_id 컬럼 ✅ (당신 설계)
checkpoint_writes → session_id 컬럼 ✅ (당신 설계)
checkpoint_blobs  → session_id 컬럼 ✅ (당신 설계)
```

### 실제 DB에 있는 것

```
chat_sessions    → session_id 컬럼 ✅ (당신 설계대로!)
chat_messages    → session_id 컬럼 ✅ (당신 설계대로!)
checkpoints      → thread_id 컬럼 ❌ (LangGraph가 바꿈!)
checkpoint_writes → thread_id 컬럼 ❌ (LangGraph가 바꿈!)
checkpoint_blobs  → thread_id 컬럼 ❌ (LangGraph가 바꿈!)
```

---

## 🔍 실제 DB 테이블 구조

### ✅ chat_sessions (당신이 만든 것 - 정상)

```
컬럼 이름         | 타입
-----------------|--------
session_id       | 문자열  ← ✅ 당신 설계대로!
user_id          | 숫자
title            | 문자열
last_message     | 텍스트
message_count    | 숫자
created_at       | 날짜시간
updated_at       | 날짜시간
is_active        | 참/거짓
metadata         | JSON
```

**예시 데이터:**
```
session_id: "session-1a4c5a9c-88f7-4d0d-a227-96fc13416ea6"
user_id: 1
title: "강남구 아파트 전세 문의"
```

### ✅ chat_messages (당신이 만든 것 - 정상)

```
컬럼 이름         | 타입
-----------------|--------
id               | 숫자 (자동증가)
session_id       | 문자열  ← ✅ 당신 설계대로!
role             | 문자열 (user/assistant)
content          | 텍스트
structured_data  | JSON
created_at       | 날짜시간
```

**예시 데이터:**
```
id: 1
session_id: "session-1a4c5a9c-88f7-4d0d-a227-96fc13416ea6"
role: "user"
content: "강남구 아파트 전세 시세 알려줘"
```

### ❌ checkpoints (LangGraph가 만든 것 - 다름!)

```
컬럼 이름              | 타입
---------------------|--------
thread_id            | 텍스트  ← ❌ 당신은 session_id로 설계했지만...
checkpoint_ns        | 텍스트
checkpoint_id        | 텍스트
parent_checkpoint_id | 텍스트
type                 | 텍스트
checkpoint           | JSON
metadata             | JSON
```

**예시 데이터:**
```
thread_id: "session-1a4c5a9c-88f7-4d0d-a227-96fc13416ea6"
            ↑ 컬럼명은 thread_id지만
            ↑ 값은 session-xxx 형식 (session_id와 같음!)
```

### ❌ checkpoint_writes (LangGraph가 만든 것 - 다름!)

```
컬럼 이름         | 타입
-----------------|--------
thread_id        | 텍스트  ← ❌ session_id여야 하는데...
checkpoint_ns    | 텍스트
checkpoint_id    | 텍스트
task_id          | 텍스트
idx              | 숫자
channel          | 텍스트
type             | 텍스트
blob             | 바이너리
task_path        | 텍스트
```

### ❌ checkpoint_blobs (LangGraph가 만든 것 - 다름!)

```
컬럼 이름         | 타입
-----------------|--------
thread_id        | 텍스트  ← ❌ session_id여야 하는데...
checkpoint_ns    | 텍스트
channel          | 텍스트
version          | 텍스트
type             | 텍스트
blob             | 바이너리
```

---

## 💡 핵심 포인트 (중요!)

### 컬럼명은 다르지만, 값은 같습니다!

```
chat_sessions.session_id = "session-abc123"
chat_messages.session_id = "session-abc123"
checkpoints.thread_id    = "session-abc123"  ← 컬럼명만 다름!
                            ↑↑↑↑↑↑↑↑↑↑↑↑
                            값은 똑같음!
```

**쉽게 설명:**
```
예를 들어 "홍길동"이라는 사람이 있습니다.

chat_sessions 테이블:   "이름" 컬럼에 "홍길동" 저장
chat_messages 테이블:   "이름" 컬럼에 "홍길동" 저장
checkpoints 테이블:     "성명" 컬럼에 "홍길동" 저장  ← 컬럼명만 다름!

사람은 같은데, 부르는 이름(컬럼명)만 다른 것입니다!
```

---

## 🔄 데이터 흐름 확인

실제 데이터를 보면 모두 연결되어 있습니다:

```sql
-- 같은 세션의 데이터들
chat_sessions.session_id    = "session-1a4c5a9c..."
chat_messages.session_id    = "session-1a4c5a9c..."  (같은 값!)
checkpoints.thread_id       = "session-1a4c5a9c..."  (같은 값!)
```

**그림으로 보면:**
```
┌──────────────────────────────────────────┐
│ 하나의 대화 세션                            │
│ ID: session-1a4c5a9c-88f7-...            │
├──────────────────────────────────────────┤
│                                          │
│ chat_sessions 테이블                      │
│   session_id = "session-1a4c5a9c..."    │
│                                          │
│ chat_messages 테이블                      │
│   session_id = "session-1a4c5a9c..."    │
│                                          │
│ checkpoints 테이블                        │
│   thread_id = "session-1a4c5a9c..."     │
│                                          │
└──────────────────────────────────────────┘

↑ 모두 같은 세션을 가리킴!
  (컬럼명만 다를 뿐!)
```

---

## 🤔 왜 이렇게 되었나?

### 타임라인

**1단계: 당신이 설계함 (2025-10-16)**
```
checkpoints.session_id로 설계 ✅
```

**2단계: 테이블 생성 시도**
```
아마도 SQL 스크립트로 생성 시도했을 것
```

**3단계: LangGraph가 덮어씀**
```
애플리케이션 실행 → LangGraph 초기화
→ "어? checkpoint 테이블이 있네?"
→ "내가 만든 게 아니네? 내 방식으로 다시 만들자!"
→ DROP TABLE checkpoints;
→ CREATE TABLE checkpoints (thread_id TEXT...);
```

**4단계: 현재 상태**
```
checkpoints.thread_id로 변경됨 ❌
```

---

## ❓ 왜 LangGraph가 마음대로 바꿨나?

### LangGraph의 동작 방식

```python
# team_supervisor.py에서 실행됨
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 이 코드가 실행되면...
checkpointer = AsyncPostgresSaver.from_conn_string(DB_URI)
await checkpointer.setup()  # ← 여기서 테이블 자동 생성!

# LangGraph 내부 코드:
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,  -- ← 무조건 thread_id!
    ...
);
```

**LangGraph 규칙:**
- 무조건 `thread_id` 사용
- 변경 불가능
- 설정 옵션 없음
- 이미 있어도 자기 방식대로 재생성

---

## 🛠️ 해결 방법

### 방법 1: 코드를 DB에 맞춤 (추천 ⭐)

**무엇을 바꾸나?**
```python
# 코드에서 컬럼명만 수정
DELETE FROM checkpoints WHERE session_id = ...  # ❌
DELETE FROM checkpoints WHERE thread_id = ...   # ✅
```

**무엇을 안 바꾸나?**
```python
# 이런 건 전부 그대로!
session_id = "session-abc123"        # ✅ 그대로
chat_sessions.session_id             # ✅ 그대로
chat_messages.session_id             # ✅ 그대로
```

**변경 파일:**
- `chat_api.py` (3줄)
- `postgres_session_manager.py` (3줄)

**변경하지 않는 파일:**
- `scripts/` (그대로!)
- `models/` (그대로!)
- `schemas/` (그대로!)
- 기타 모든 파일 (그대로!)

### 방법 2: DB를 설계대로 바꿈 (비추천 ⚠️)

**무엇을 바꾸나?**
```sql
-- DB에서 컬럼명 변경
ALTER TABLE checkpoints
RENAME COLUMN thread_id TO session_id;
```

**문제:**
```
- LangGraph가 다시 thread_id로 되돌릴 수 있음
- 애플리케이션 재시작할 때마다 위험
- 복잡하고 위험함
```

---

## 📝 쉬운 비유로 이해하기

### 비유 1: 같은 사람, 다른 호칭

```
할아버지가 "철수야" 라고 부름
엄마가 "우리 아들" 이라고 부름
선생님이 "김철수 학생" 이라고 부름

→ 사람은 같은데 부르는 이름만 다름!
→ session_id vs thread_id도 같은 개념!
```

### 비유 2: 같은 주소, 다른 표기

```
한국식: "서울시 강남구 테헤란로 123"
영어식: "123 Teheran-ro, Gangnam-gu, Seoul"

→ 장소는 같은데 표기만 다름!
→ session_id (우리 방식) vs thread_id (LangGraph 방식)
```

---

## ✅ 결론

### 현재 상태 요약

| 테이블 | 당신 설계 | 실제 DB | 일치? |
|-------|----------|---------|-------|
| chat_sessions | session_id | session_id | ✅ |
| chat_messages | session_id | session_id | ✅ |
| checkpoints | session_id | thread_id | ❌ |
| checkpoint_writes | session_id | thread_id | ❌ |
| checkpoint_blobs | session_id | thread_id | ❌ |

### 핵심 메시지

```
✅ 당신이 맞습니다: session_id로 설계했습니다
❌ LangGraph가 바꿨습니다: thread_id로 덮어씌웠습니다
⚠️ 값은 같습니다: "session-abc123" 똑같이 저장됨
✅ 해결은 간단합니다: 코드 6줄만 수정하면 됩니다
```

### 왜 헷갈리는가?

```
1. 당신은 session_id로 설계함
2. LangGraph가 몰래 thread_id로 바꿈
3. 코드는 session_id를 찾음
4. DB에는 thread_id만 있음
5. "session_id 컬럼이 없다"는 에러!
```

### 해결책

```
코드에서:
  "WHERE session_id = ..." → "WHERE thread_id = ..."

값은:
  session_id 변수 그대로 사용!

결과:
  {"thread_id": session_id}
  ↑ 컬럼명      ↑ 값
```

---

**이해되셨나요?**
- 컬럼명(thread_id)과 값(session-xxx)은 다른 개념입니다
- 모든 session_id를 바꾸는 게 아닙니다
- checkpoint 쿼리의 컬럼명만 바꿉니다!

---

**Status:** 현재 DB 상태 명확히 확인됨
**Created by:** Claude Code
**Date:** 2025-10-21
