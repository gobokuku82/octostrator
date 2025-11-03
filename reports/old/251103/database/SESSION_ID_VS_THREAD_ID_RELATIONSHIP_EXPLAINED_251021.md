# session_id와 thread_id의 관계 - 완전 이해

**Date:** 2025-10-21
**목적:** session_id와 thread_id, chat_* 와 checkpoint_* 테이블의 관계를 명확히 이해

---

## 🎯 핵심 개념: 같은 것을 다르게 부를 뿐!

### 가장 중요한 사실

```
session_id == thread_id
(값은 완전히 동일, 이름만 다름!)
```

---

## 📊 두 개의 세계

### 우리가 만든 세계 (Chat 시스템)

```
우리의 용어: "세션 (Session)"
우리의 ID:   session_id
테이블:      chat_sessions, chat_messages
```

### LangGraph의 세계 (Checkpoint 시스템)

```
LangGraph 용어: "스레드 (Thread)"
LangGraph ID:   thread_id
테이블:         checkpoints, checkpoint_writes, checkpoint_blobs
```

---

## 🔗 실제 데이터로 관계 이해하기

### 시나리오: 사용자가 "강남구 아파트 전세 시세 알려줘" 질문

### 1단계: 새 대화 시작

**Backend 코드:**
```python
# 새 세션 생성
session_id = "session-abc123"  # UUID로 생성

# chat_sessions 테이블에 저장
INSERT INTO chat_sessions (session_id, user_id, title)
VALUES ('session-abc123', 1, '새 대화');
```

**DB 상태:**
```
chat_sessions 테이블:
┌──────────────────┬─────────┬──────────┐
│ session_id       │ user_id │ title    │
├──────────────────┼─────────┼──────────┤
│ session-abc123   │ 1       │ 새 대화   │
└──────────────────┴─────────┴──────────┘
```

### 2단계: 사용자 메시지 저장

**Backend 코드:**
```python
# 사용자 메시지 저장
INSERT INTO chat_messages (session_id, role, content)
VALUES ('session-abc123', 'user', '강남구 아파트 전세 시세 알려줘');
```

**DB 상태:**
```
chat_messages 테이블:
┌────┬──────────────────┬──────────┬─────────────────────────┐
│ id │ session_id       │ role     │ content                 │
├────┼──────────────────┼──────────┼─────────────────────────┤
│ 1  │ session-abc123   │ user     │ 강남구 아파트 전세...    │
└────┴──────────────────┴──────────┴─────────────────────────┘
```

### 3단계: AI 처리 시작 (LangGraph 실행)

**Backend 코드:**
```python
# LangGraph에게 처리 요청
config = {
    "configurable": {
        "thread_id": session_id  # ← session_id 값을 thread_id로 전달!
    }
}

# LangGraph 실행
graph.invoke(state, config)
```

**중요!** 여기서 `thread_id`에 `session_id` 값을 넣습니다!
```python
thread_id = "session-abc123"  # session_id와 같은 값!
```

### 4단계: LangGraph가 상태 저장

**LangGraph 내부 동작:**
```python
# LangGraph가 자동으로 실행
INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint)
VALUES ('session-abc123', 'checkpoint-001', {...상태 데이터...});
```

**DB 상태:**
```
checkpoints 테이블:
┌──────────────────┬─────────────────┬──────────────┐
│ thread_id        │ checkpoint_id   │ checkpoint   │
├──────────────────┼─────────────────┼──────────────┤
│ session-abc123   │ checkpoint-001  │ {...JSON...} │
└──────────────────┴─────────────────┴──────────────┘
```

### 5단계: AI 응답 저장

**Backend 코드:**
```python
# AI 응답을 chat_messages에 저장
INSERT INTO chat_messages (session_id, role, content)
VALUES ('session-abc123', 'assistant', '강남구 아파트 전세 시세는...');
```

**DB 상태:**
```
chat_messages 테이블:
┌────┬──────────────────┬───────────┬────────────────────┐
│ id │ session_id       │ role      │ content            │
├────┼──────────────────┼───────────┼────────────────────┤
│ 1  │ session-abc123   │ user      │ 강남구 아파트...   │
│ 2  │ session-abc123   │ assistant │ 강남구 아파트 전세..│
└────┴──────────────────┴───────────┴────────────────────┘
```

---

## 🔍 전체 데이터 연결 보기

### 하나의 대화 세션 "session-abc123"의 데이터

```
┌─────────────────────────────────────────────────────────┐
│           하나의 대화 세션: session-abc123                │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓

┌─────────────┐  ┌──────────────┐  ┌───────────────┐
│chat_sessions│  │chat_messages │  │ checkpoints   │
├─────────────┤  ├──────────────┤  ├───────────────┤
│session_id:  │  │session_id:   │  │thread_id:     │
│abc123       │  │abc123        │  │abc123         │
│             │  │              │  │               │
│title:       │  │role: user    │  │checkpoint:    │
│새 대화       │  │content: 강남..│  │{...상태...}   │
│             │  │              │  │               │
│             │  │role: assistant│ │               │
│             │  │content: 시세는│ │               │
└─────────────┘  └──────────────┘  └───────────────┘
      ↑                 ↑                  ↑
      └─────────────────┴──────────────────┘
            같은 값: "session-abc123"
```

---

## 💡 왜 두 가지 이름을 사용하나?

### chat_* 테이블 (우리가 만든 것)

**목적:** 사용자에게 보여주기 위한 데이터
```
- 채팅 히스토리 표시
- 대화 목록 보기
- 메시지 검색
```

**저장 내용:**
```
chat_sessions:
  - 세션 제목
  - 생성 시간
  - 마지막 메시지 미리보기

chat_messages:
  - 사용자 메시지
  - AI 응답 메시지
  - 시간 순서
```

**컬럼명:** `session_id` (우리 설계)

### checkpoint_* 테이블 (LangGraph가 만든 것)

**목적:** AI 처리 상태 저장 (일시정지/재개)
```
- 대화 중간 상태 저장
- 에러 발생 시 복구
- 장시간 작업 일시정지/재개
```

**저장 내용:**
```
checkpoints:
  - AI 처리 중간 상태
  - 현재까지 수행한 작업
  - 다음에 할 일

checkpoint_writes:
  - 상태 업데이트 이력

checkpoint_blobs:
  - 큰 데이터 (파일, 이미지 등)
```

**컬럼명:** `thread_id` (LangGraph 표준)

---

## 🔄 두 시스템이 어떻게 연결되나?

### 코드에서의 연결

```python
# 1. 새 세션 생성 (우리 시스템)
session_id = "session-abc123"

# 2. chat_sessions에 저장 (우리 테이블)
INSERT INTO chat_sessions (session_id, ...)
VALUES ('session-abc123', ...);

# 3. LangGraph 설정 (thread_id = session_id)
config = {
    "configurable": {
        "thread_id": session_id  # ← 여기서 연결!
    }
}

# 4. LangGraph 실행
graph.invoke(state, config)

# 5. LangGraph가 checkpoints에 저장 (LangGraph 테이블)
INSERT INTO checkpoints (thread_id, ...)
VALUES ('session-abc123', ...);  # ← session_id 값 사용!
```

**핵심:**
```python
thread_id = session_id  # 값은 완전히 동일!
```

---

## 📝 실제 코드 예시

### team_supervisor.py에서 연결하는 부분

```python
# Line 1140-1160 (대략)
async def process_query(self, query: str, session_id: str, ...):
    """AI 처리"""

    # 1. session_id 받음 (우리 시스템)
    chat_session_id = session_id  # "session-abc123"

    # 2. LangGraph config 설정
    config = {
        "configurable": {
            "thread_id": chat_session_id  # ← session_id를 thread_id로 전달!
        }
    }

    # 3. LangGraph 실행
    async for event in self.graph.astream(state, config):
        # LangGraph가 checkpoints 테이블에
        # thread_id = "session-abc123"로 저장
        ...
```

---

## 🗑️ 세션 삭제 시 문제 발생!

### 현재 문제 코드

```python
# chat_api.py:483 (문제 발생!)
session_id = "session-abc123"

# chat_sessions 삭제 (정상 동작)
DELETE FROM chat_sessions WHERE session_id = :session_id

# chat_messages 삭제 (정상 동작 - CASCADE)
# 자동 삭제됨

# checkpoints 삭제 (❌ 에러 발생!)
DELETE FROM checkpoints WHERE session_id = :session_id
# ERROR: column "session_id" does not exist
```

### 왜 에러가 나는가?

```
checkpoints 테이블에는 session_id 컬럼이 없음!
thread_id 컬럼만 있음!
```

### 올바른 코드

```python
session_id = "session-abc123"

# chat_sessions 삭제
DELETE FROM chat_sessions WHERE session_id = :session_id

# checkpoints 삭제 (✅ 수정!)
DELETE FROM checkpoints WHERE thread_id = :thread_id
#                             ^^^^^^^^^ 컬럼명 변경!

# 파라미터 전달
{"thread_id": session_id}  # session_id 값을 thread_id 파라미터로!
```

---

## 🎓 비유로 이해하기

### 비유: 학생 관리 시스템

```
우리 학교 시스템:
  - 테이블: students, grades
  - 학생 ID: student_id
  - 예: student_id = "2024001"

외부 도서관 시스템 (LangGraph):
  - 테이블: library_loans
  - 회원 ID: member_id
  - 예: member_id = "2024001"  (같은 번호!)

연결:
  - 학교에서 도서관에 학생 등록 시
  - member_id = student_id 로 등록
  - 같은 학생, 다른 이름!
```

**학생 "홍길동":**
```
학교 시스템:
  students.student_id = "2024001"
  grades.student_id = "2024001"

도서관 시스템:
  library_loans.member_id = "2024001"  ← 같은 사람!
```

**책 대출 기록 삭제 시:**
```python
# ❌ 잘못된 코드
DELETE FROM library_loans WHERE student_id = '2024001'
# ERROR: column "student_id" does not exist

# ✅ 올바른 코드
DELETE FROM library_loans WHERE member_id = '2024001'
```

---

## 📋 관계 요약표

| 항목 | chat_* 테이블 | checkpoint_* 테이블 |
|------|--------------|-------------------|
| **소유자** | 우리가 만듦 | LangGraph가 만듦 |
| **ID 컬럼명** | session_id | thread_id |
| **ID 값** | "session-abc123" | "session-abc123" (동일!) |
| **목적** | 채팅 히스토리 표시 | AI 상태 저장 |
| **사용자 보임** | ✅ 예 | ❌ 아니오 (내부용) |
| **제어 가능** | ✅ 예 | ❌ 아니오 (LangGraph) |

---

## 🔧 실전 적용

### 세션 생성 시

```python
# 1. session_id 생성
session_id = f"session-{uuid4()}"  # "session-abc123"

# 2. chat_sessions에 저장
INSERT INTO chat_sessions (session_id, ...) VALUES (session_id, ...)
# session_id 컬럼 사용 ✅

# 3. LangGraph 실행 시
config = {"configurable": {"thread_id": session_id}}
# thread_id에 session_id 값 전달 ✅
```

### 메시지 저장 시

```python
# chat_messages에 저장
INSERT INTO chat_messages (session_id, role, content)
VALUES (session_id, 'user', '질문 내용')
# session_id 컬럼 사용 ✅

# LangGraph가 자동으로 checkpoints 저장
# thread_id = session_id 값으로 자동 저장됨 ✅
```

### 세션 삭제 시 (수정 필요!)

```python
session_id = "session-abc123"

# 1. chat_sessions 삭제
DELETE FROM chat_sessions WHERE session_id = :session_id  # ✅

# 2. chat_messages 삭제 (CASCADE 자동) # ✅

# 3. checkpoints 삭제 (컬럼명 변경 필요!)
DELETE FROM checkpoints WHERE thread_id = :thread_id  # ← 수정!
{"thread_id": session_id}  # 값은 session_id 사용!
```

---

## ✅ 최종 정리

### 핵심 사실

1. **session_id와 thread_id는 같은 값**
   ```python
   session_id = "session-abc123"
   thread_id = "session-abc123"  # 동일!
   ```

2. **chat_* 테이블은 session_id 컬럼 사용**
   ```sql
   chat_sessions.session_id
   chat_messages.session_id
   ```

3. **checkpoint_* 테이블은 thread_id 컬럼 사용**
   ```sql
   checkpoints.thread_id
   checkpoint_writes.thread_id
   checkpoint_blobs.thread_id
   ```

4. **두 시스템은 값으로 연결됨**
   ```
   chat_sessions.session_id = "session-abc123"
   checkpoints.thread_id    = "session-abc123"
   ↑ 같은 대화를 가리킴!
   ```

### 수정할 부분

```python
# ❌ Before
DELETE FROM checkpoints WHERE session_id = :session_id

# ✅ After
DELETE FROM checkpoints WHERE thread_id = :thread_id
{"thread_id": session_id}  # 값은 session_id 변수 사용!
```

### 수정하지 않는 부분

```python
# 이런 것들은 전부 그대로!
session_id = "session-abc123"              # ✅
chat_sessions.session_id                   # ✅
chat_messages.session_id                   # ✅
config = {"configurable": {"thread_id": session_id}}  # ✅
```

---

**이제 이해되셨나요?**

session_id와 thread_id는:
- 같은 값 (예: "session-abc123")
- 다른 테이블에서 다른 이름으로 사용
- chat_* = session_id (우리)
- checkpoint_* = thread_id (LangGraph)
- 값으로 연결됨!

---

**Status:** Relationship Fully Explained
**Created by:** Claude Code
**Date:** 2025-10-21
