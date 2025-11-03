# Chat Session Deletion - Root Cause Analysis

**Date:** 2025-10-21
**Issue:** Session deletion fails - Column name mismatch
**Status:** 🔍 Deep Analysis - User Review Required

---

## 사용자 피드백

> "난 db만들때 thread_id를 다 session_id로 만들었어. 어디에서 오류났는지 찾아야해."

**중요 발견:**
- 사용자가 의도적으로 `session_id` 컬럼으로 생성했다고 주장
- 하지만 현재 DB에는 `thread_id` 컬럼이 존재
- **어디선가 테이블이 다시 생성되었거나 덮어씌워졌을 가능성**

---

## 현재 Database 상태

### Checkpoint 테이블 목록
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE '%checkpoint%';

table_name
-----------------------
checkpoint_blobs
checkpoint_migrations  ⭐ (LangGraph 자동 마이그레이션 테이블)
checkpoint_writes
checkpoints
```

### Checkpoint Migrations 내용
```sql
SELECT * FROM checkpoint_migrations;

v
---
0
1
2
3
4
5
6
7
8
9
(10 migrations executed)
```

**분석:** LangGraph가 자동으로 **10개의 마이그레이션을 실행**했습니다!

---

## 테이블 스키마 현황

### Table 1: checkpoints
```
필드명                  | 형태
-----------------------|-------
thread_id              | text   ⚠️ (LangGraph 기본값)
checkpoint_ns          | text
checkpoint_id          | text
parent_checkpoint_id   | text
type                   | text
checkpoint             | jsonb
metadata               | jsonb
```

### Table 2: checkpoint_writes
```
필드명         | 형태
--------------|----------
thread_id     | text   ⚠️ (LangGraph 기본값)
checkpoint_ns | text
checkpoint_id | text
task_id       | text
idx           | integer
channel       | text
type          | text
blob          | bytea
task_path     | text
```

### Table 3: checkpoint_blobs
```
필드명         | 형태
--------------|-------
thread_id     | text   ⚠️ (LangGraph 기본값)
checkpoint_ns | text
channel       | text
version       | text
type          | text
blob          | bytea
```

---

## Root Cause 가설

### 가설 1: LangGraph가 자동으로 테이블 생성 (가능성 높음 ✅)

**증거:**
1. `checkpoint_migrations` 테이블 존재 (LangGraph 전용)
2. 10개의 마이그레이션 실행됨 (v0-v9)
3. LangGraph 기본 스키마는 `thread_id` 사용

**시나리오:**
```
1. 사용자가 처음에 session_id로 테이블 생성
2. 애플리케이션 실행 시 LangGraph 초기화
3. LangGraph가 기존 테이블 DROP 후 재생성 (thread_id 사용)
4. 또는 LangGraph가 처음부터 테이블 생성 (사용자 테이블 무시)
```

### 가설 2: 사용자가 잘못 생성했거나 덮어씌워짐

**가능성:**
- 사용자가 `session_id`로 생성했다고 생각했지만 실제로는 `thread_id`로 생성
- 또는 이후에 다른 스크립트가 테이블을 재생성

### 가설 3: 두 가지 테이블 세트가 공존

**가능성:**
- 다른 스키마에 `session_id` 버전이 있을 수도 있음
- 현재는 `public` 스키마만 확인함

---

## 조사 필요 사항

### 1. 사용자가 만든 원본 스크립트 확인

**질문:**
- 테이블 생성 SQL 스크립트 파일이 있나요?
- 언제, 어떻게 checkpoint 테이블을 생성했나요?
- `.sql` 파일 또는 Python migration 스크립트가 있나요?

**찾을 위치:**
```
backend/database/
backend/migrations/
backend/scripts/
backend/sql/
backend/init_db.py
```

### 2. LangGraph 설정 확인

**찾을 파일:**
- LangGraph checkpoint 설정 코드
- PostgresSaver 초기화 부분
- `create_tables=True` 옵션이 있는지 확인

**검색할 패턴:**
```python
from langgraph.checkpoint.postgres import PostgresSaver
PostgresSaver(..., create_tables=True)  # 이게 있으면 자동 생성
```

### 3. 애플리케이션 시작 로그 확인

**확인할 내용:**
```
backend/logs/app.log (첫 실행 시)
- "Creating checkpoint tables..."
- "Running migrations..."
- "Checkpoint tables initialized"
```

### 4. DB 생성 히스토리 확인

```sql
-- PostgreSQL 로그 확인 (가능하다면)
-- pg_log 디렉토리에서 CREATE TABLE 검색
```

---

## 두 가지 해결 방안

### 방안 A: 코드를 DB에 맞춤 (thread_id 사용) ⚠️

**장점:**
- LangGraph 기본 스키마와 일치
- 미래 업그레이드 시 호환성 좋음

**단점:**
- 사용자 의도와 다름
- 코드 전체에서 session_id를 thread_id로 변경 필요

**구현:**
```python
# chat_api.py & postgres_session_manager.py
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 session-xxx 형식으로 동일
)
```

### 방안 B: DB를 코드에 맞춤 (session_id로 변경) ⭐ 추천

**장점:**
- 사용자 의도대로 복원
- 코드 변경 최소화
- 직관적 (session_id가 맞음)

**단점:**
- DB 마이그레이션 필요
- 기존 데이터 백업 필요
- LangGraph 자동 마이그레이션 비활성화 필요

**구현:**
```sql
-- Step 1: 컬럼 이름 변경
ALTER TABLE checkpoints RENAME COLUMN thread_id TO session_id;
ALTER TABLE checkpoint_writes RENAME COLUMN thread_id TO session_id;
ALTER TABLE checkpoint_blobs RENAME COLUMN thread_id TO session_id;

-- Step 2: 인덱스 재생성 (필요시)
DROP INDEX checkpoints_thread_id_idx;
CREATE INDEX checkpoints_session_id_idx ON checkpoints(session_id);

DROP INDEX checkpoint_writes_thread_id_idx;
CREATE INDEX checkpoint_writes_session_id_idx ON checkpoint_writes(session_id);

DROP INDEX checkpoint_blobs_thread_id_idx;
CREATE INDEX checkpoint_blobs_session_id_idx ON checkpoint_blobs(session_id);
```

---

## 추가 조사 계획

### Step 1: LangGraph 초기화 코드 찾기

```bash
# 검색 패턴
cd backend
grep -r "PostgresSaver" --include="*.py"
grep -r "checkpoint" --include="*.py" | grep "create"
grep -r "thread_id" --include="*.py"
```

### Step 2: 사용자가 만든 스크립트 찾기

```bash
# SQL 파일 찾기
find . -name "*.sql" -type f

# Python init 스크립트 찾기
find . -name "*init*.py" -type f
find . -name "*migration*.py" -type f
```

### Step 3: 데이터 확인

```sql
-- 현재 checkpoint 데이터 샘플
SELECT thread_id, checkpoint_ns, checkpoint_id
FROM checkpoints
LIMIT 5;

-- session_id 형식 확인
SELECT DISTINCT thread_id
FROM checkpoints
WHERE thread_id LIKE 'session-%'
LIMIT 10;
```

---

## 질문 (사용자 답변 필요)

### 🔴 중요 질문

1. **checkpoint 테이블을 언제, 어떻게 생성했나요?**
   - [ ] SQL 스크립트로 직접 생성
   - [ ] Python 코드로 생성
   - [ ] LangGraph가 자동 생성 (모름)
   - [ ] 다른 방법

2. **원본 테이블 생성 스크립트가 있나요?**
   - [ ] 있음 (파일 경로: ____________)
   - [ ] 없음

3. **LangGraph PostgresSaver 설정 어디에 있나요?**
   - [ ] 알고 있음 (파일: ____________)
   - [ ] 모름 (찾아야 함)

4. **선호하는 해결 방법:**
   - [ ] 방안 A: 코드 수정 (thread_id 사용)
   - [ ] 방안 B: DB 수정 (session_id로 변경) ⭐ 추천
   - [ ] 기타 의견: ____________

---

## 다음 단계

### 사용자가 방안 A 선택 시 (thread_id 사용)

1. ✅ 코드에서 session_id → thread_id 변경
2. ✅ text() wrapper 추가
3. ✅ 테스트

**예상 시간:** 10분

### 사용자가 방안 B 선택 시 (session_id로 DB 변경) ⭐

1. ✅ 기존 데이터 백업
2. ✅ ALTER TABLE 실행 (3개 테이블)
3. ✅ 인덱스 재생성
4. ✅ LangGraph 자동 마이그레이션 비활성화
5. ✅ 코드에서 text() wrapper만 추가
6. ✅ 테스트

**예상 시간:** 20분

---

## 임시 해결책 (긴급)

**지금 당장 삭제 기능이 필요하다면:**

```python
# chat_api.py (임시)
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

**단점:**
- 근본 원인 해결 안 됨
- 나중에 혼란 가능

---

## 요약

**문제:**
- 코드는 `session_id` 사용
- DB는 `thread_id` 존재
- 사용자는 `session_id`로 만들었다고 주장

**원인 추정:**
- LangGraph가 자동으로 테이블 생성/재생성 (가능성 90%)
- checkpoint_migrations 테이블 존재가 증거

**해결 필요:**
1. 사용자 원본 스크립트 확인
2. LangGraph 설정 확인
3. 방안 A vs B 결정
4. 실행

**다음 보고서:**
- 사용자 답변 후 상세 실행 계획서 작성

---

**Status:** ⏸️ Waiting for User Input
**Created by:** Claude Code
**Date:** 2025-10-21
