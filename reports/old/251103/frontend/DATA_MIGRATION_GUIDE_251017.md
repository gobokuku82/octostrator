# 📋 기존 데이터 처리 가이드 (2025-10-17)

## 질문: 기존에 저장되어있는 자료는 다 지워야 하는가?

### 답변: 아니오, 3가지 옵션이 있습니다

---

## 🎯 옵션 비교

| 옵션 | 장점 | 단점 | 추천 대상 |
|------|------|------|----------|
| **1. 마이그레이션** | • 기존 데이터 보존<br>• 대화 히스토리 유지 | • 마이그레이션 실행 필요<br>• 테스트 시간 필요 | **프로덕션 환경** |
| **2. 전체 삭제** | • 깔끔한 시작<br>• 빠른 적용 | • 모든 데이터 손실 | **개발/테스트 환경** |
| **3. 혼용 (권장 안 함)** | • 즉시 사용 가능 | • 일관성 문제<br>• 버그 가능성 | ❌ 비추천 |

---

## 📊 Step 1: 기존 데이터 확인

### 1-1. DB 접속
```bash
# PostgreSQL 접속
psql -U postgres -d holmesnyangz_db
```

### 1-2. 확인 스크립트 실행
```bash
# 프로젝트 루트에서 실행
psql -U postgres -d holmesnyangz_db -f backend/check_existing_sessions.sql
```

또는 SQL 직접 실행:
```sql
-- session_id 형식별 개수 확인
SELECT
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
        ELSE '⚠️ 기타'
    END AS format_type,
    COUNT(*) as count
FROM chat_sessions
GROUP BY format_type;
```

### 1-3. 결과 해석

#### Case A: `chat-{uuid}` 형식만 존재
```
format_type        | count
-------------------+-------
❌ chat-{uuid}     |    15
```
→ **옵션 1 (마이그레이션) 또는 옵션 2 (삭제) 선택**

#### Case B: `session-{uuid}` 형식만 존재
```
format_type        | count
-------------------+-------
✅ session-{uuid}  |    10
```
→ **조치 불필요! 이미 표준 형식 사용 중**

#### Case C: 혼합 존재
```
format_type        | count
-------------------+-------
✅ session-{uuid}  |     8
❌ chat-{uuid}     |     7
```
→ **옵션 1 (마이그레이션) 필수**

#### Case D: 데이터 없음
```
format_type        | count
-------------------+-------
(0 rows)
```
→ **조치 불필요! 바로 사용 가능**

---

## 🔧 옵션 1: 마이그레이션 (권장 - 프로덕션)

### 장점
- ✅ 기존 대화 히스토리 보존
- ✅ 사용자 경험 연속성 유지
- ✅ 데이터 손실 없음

### 단점
- ⏱️ 마이그레이션 실행 시간 필요 (데이터 양에 따라)
- 🧪 사전 테스트 권장

### 실행 방법

#### Step 1: 백업 생성
```bash
# PostgreSQL 전체 백업
pg_dump -U postgres holmesnyangz_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 또는 특정 테이블만 백업
pg_dump -U postgres -t chat_sessions -t chat_messages holmesnyangz_db > sessions_backup.sql
```

#### Step 2: 마이그레이션 실행
```bash
# 마이그레이션 스크립트 실행
psql -U postgres -d holmesnyangz_db -f backend/migrate_chat_to_session.sql
```

#### Step 3: 검증
```sql
-- 변환 결과 확인
SELECT
    COUNT(*) as total_sessions,
    SUM(CASE WHEN session_id LIKE 'session-%' THEN 1 ELSE 0 END) as standard_format,
    SUM(CASE WHEN session_id LIKE 'chat-%' THEN 1 ELSE 0 END) as old_format
FROM chat_sessions;

-- 기대 결과:
-- total_sessions | standard_format | old_format
-- --------------+-----------------+-----------
--            15 |              15 |          0
```

#### Step 4: COMMIT 또는 ROLLBACK
```sql
-- 검증 성공 시
COMMIT;

-- 문제 발생 시
ROLLBACK;
```

### 마이그레이션 상세 설명

스크립트는 다음 작업을 수행합니다:

1. **백업 테이블 생성**: `chat_sessions_backup`, `chat_messages_backup`
2. **매핑 테이블 생성**: `old_session_id` → `new_session_id`
3. **순차적 업데이트**:
   ```
   chat-abc123 → session-abc123
   chat-xyz789 → session-xyz789
   ```
4. **관련 테이블 동기화**:
   - `chat_messages.session_id` 업데이트
   - `checkpoints.session_id` 업데이트
   - `checkpoint_writes.session_id` 업데이트
   - `checkpoint_blobs.session_id` 업데이트
   - `chat_sessions.session_id` 업데이트 (PK이므로 마지막)

### 롤백 방법 (문제 발생 시)

```sql
BEGIN;

-- 백업에서 복원
DELETE FROM chat_sessions WHERE session_id LIKE 'session-%';
DELETE FROM chat_messages WHERE session_id LIKE 'session-%';

INSERT INTO chat_sessions SELECT * FROM chat_sessions_backup;
INSERT INTO chat_messages SELECT * FROM chat_messages_backup;

DROP TABLE chat_sessions_backup;
DROP TABLE chat_messages_backup;

COMMIT;
```

---

## 🗑️ 옵션 2: 전체 삭제 (권장 - 개발/테스트)

### 장점
- ✅ 빠르고 간단
- ✅ 깔끔한 시작
- ✅ 복잡한 마이그레이션 불필요

### 단점
- ❌ 모든 대화 히스토리 손실
- ❌ 사용자 데이터 복구 불가

### 실행 방법

#### Step 1: 백업 (선택 사항)
```bash
# 혹시 모르니 백업
pg_dump -U postgres -t chat_sessions -t chat_messages holmesnyangz_db > backup_before_delete.sql
```

#### Step 2: 데이터 삭제
```sql
BEGIN;

-- 1. chat_messages 먼저 삭제 (FK 제약 때문)
DELETE FROM chat_messages;

-- 2. checkpoint 관련 테이블 정리
DELETE FROM checkpoint_writes;
DELETE FROM checkpoint_blobs;
DELETE FROM checkpoints;

-- 3. chat_sessions 삭제
DELETE FROM chat_sessions;

-- 검증
SELECT COUNT(*) FROM chat_sessions;  -- 0이어야 함
SELECT COUNT(*) FROM chat_messages;  -- 0이어야 함

COMMIT;
```

#### Step 3: 시퀀스 리셋 (선택 사항)
```sql
-- chat_messages ID 시퀀스 리셋
ALTER SEQUENCE chat_messages_id_seq RESTART WITH 1;
```

---

## ⚠️ 옵션 3: 혼용 (권장 안 함)

### 설명
`chat-{uuid}`와 `session-{uuid}` 형식을 동시에 유지

### 문제점
1. **WebSocket 연결 실패**: `chat-{uuid}` 세션은 검증 실패
2. **메시지 저장 실패**: session_id 불일치
3. **UI 혼란**: 일부 세션만 작동
4. **유지보수 어려움**: 두 가지 형식 관리

### 결론
❌ **절대 권장하지 않음**

---

## 📋 의사결정 플로우차트

```
┌─────────────────────────────┐
│ 기존 데이터가 중요한가?      │
└─────────────┬───────────────┘
              │
        ┌─────┴─────┐
        │           │
       YES         NO
        │           │
        ▼           ▼
┌───────────────┐  ┌──────────────┐
│ 옵션 1        │  │ 옵션 2       │
│ 마이그레이션   │  │ 전체 삭제     │
│               │  │              │
│ 1. 백업       │  │ 1. 백업(선택)│
│ 2. 마이그레이션│  │ 2. DELETE    │
│ 3. 검증       │  │ 3. 시작      │
│ 4. COMMIT     │  │              │
└───────────────┘  └──────────────┘
```

---

## 🎯 환경별 추천

### 개발 환경 (로컬)
→ **옵션 2 (전체 삭제)** 추천
- 테스트 데이터이므로 삭제해도 무방
- 빠르고 간단

### 스테이징 환경
→ **옵션 1 (마이그레이션)** 추천
- 프로덕션 환경 시뮬레이션
- 마이그레이션 스크립트 테스트

### 프로덕션 환경
→ **옵션 1 (마이그레이션)** 필수
- 사용자 데이터 보존 필수
- 철저한 백업 + 검증

---

## ✅ 실행 체크리스트

### 마이그레이션 실행 전
- [ ] 현재 session_id 형식 확인 (`check_existing_sessions.sql`)
- [ ] 전체 DB 백업 완료
- [ ] 마이그레이션 스크립트 검토
- [ ] 테스트 환경에서 먼저 실행
- [ ] 백엔드 서버 중지 (선택 사항)

### 마이그레이션 실행 중
- [ ] 트랜잭션 시작 (`BEGIN`)
- [ ] 마이그레이션 스크립트 실행
- [ ] 결과 검증 (모든 session_id가 `session-{uuid}` 형식인지)
- [ ] 메시지 개수 일치 확인

### 마이그레이션 실행 후
- [ ] `COMMIT` 또는 `ROLLBACK` 실행
- [ ] 백엔드 서버 재시작
- [ ] Frontend에서 테스트
  - [ ] 기존 세션 목록 표시 확인
  - [ ] 기존 대화 내용 표시 확인
  - [ ] 새 채팅 생성 확인
  - [ ] 메시지 저장 확인

---

## 🧪 테스트 시나리오

### 테스트 1: 기존 세션 로드
1. Frontend 접속
2. 사이드바에 기존 세션 표시되는지 확인
3. 세션 클릭 → 대화 내용 표시 확인

### 테스트 2: 새 채팅 생성
1. "새 채팅" 버튼 클릭
2. 메시지 전송
3. AI 응답 수신 확인
4. DB에서 `session-{uuid}` 형식 확인

### 테스트 3: 세션 전환
1. 세션 A 선택 → 메시지 전송
2. 세션 B 선택 → 메시지 전송
3. 각 세션의 메시지가 올바르게 저장되었는지 확인

---

## 🆘 문제 해결

### Q1: 마이그레이션 실패 시 어떻게 하나요?
**A**: `ROLLBACK` 실행 → 백업에서 복원
```sql
ROLLBACK;
-- 그 후 백업에서 복원
psql -U postgres holmesnyangz_db < backup_YYYYMMDD_HHMMSS.sql
```

### Q2: 일부 세션만 마이그레이션하고 싶어요
**A**: WHERE 조건 추가
```sql
-- 특정 날짜 이후 세션만 마이그레이션
UPDATE chat_sessions cs
SET session_id = 'session-' || SUBSTRING(cs.session_id FROM 6)
WHERE cs.session_id LIKE 'chat-%'
  AND cs.created_at >= '2025-10-01';
```

### Q3: 마이그레이션 중 서버를 중지해야 하나요?
**A**: 권장하지만 필수는 아닙니다
- **중지 권장**: 데이터 정합성 보장
- **중지 불가 시**: READ COMMITTED isolation level 확인

### Q4: 마이그레이션 시간이 얼마나 걸리나요?
**A**: 데이터 양에 따라 다름
- 100개 세션: ~1초
- 1,000개 세션: ~5초
- 10,000개 세션: ~30초

---

## 📝 최종 권장사항

### 개발/테스트 환경
```bash
# 간단하게 전체 삭제
psql -U postgres -d holmesnyangz_db -c "
BEGIN;
DELETE FROM chat_messages;
DELETE FROM checkpoint_writes;
DELETE FROM checkpoint_blobs;
DELETE FROM checkpoints;
DELETE FROM chat_sessions;
COMMIT;
"
```

### 프로덕션 환경
```bash
# 1. 백업
pg_dump -U postgres holmesnyangz_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 현황 확인
psql -U postgres -d holmesnyangz_db -f backend/check_existing_sessions.sql

# 3. 마이그레이션 실행 (트랜잭션 모드)
psql -U postgres -d holmesnyangz_db -f backend/migrate_chat_to_session.sql

# 4. 검증 후 COMMIT 또는 ROLLBACK
```

---

## 🎉 결론

### 기존 데이터를 삭제해야 하는가?

**답변**: ❌ **아니요, 필수가 아닙니다.**

**하지만**:
- `chat-{uuid}` 형식 세션이 있다면 → **마이그레이션 또는 삭제 필요**
- `session-{uuid}` 형식만 있다면 → **조치 불필요**
- 데이터가 없다면 → **바로 사용 가능**

### 어떤 옵션을 선택해야 하나?

| 상황 | 권장 옵션 |
|------|----------|
| 개발 중 (테스트 데이터) | **옵션 2 (삭제)** |
| 중요한 대화 있음 | **옵션 1 (마이그레이션)** |
| 프로덕션 환경 | **옵션 1 (마이그레이션)** |
| 깨끗하게 시작하고 싶음 | **옵션 2 (삭제)** |

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**관련 파일**:
- `backend/check_existing_sessions.sql` - 현황 확인 스크립트
- `backend/migrate_chat_to_session.sql` - 마이그레이션 스크립트
