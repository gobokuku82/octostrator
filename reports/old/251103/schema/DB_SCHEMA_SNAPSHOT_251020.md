# DB Schema Snapshot - Phase 0.1

**추출일**: 2025-10-20
**데이터베이스**: real_estate (PostgreSQL)
**목적**: 단일 진실 공급원(Single Source of Truth) 확립

---

## 1. chat_sessions 테이블

```sql
                      "public.chat_sessions" 테이블
    필드명     |           형태           | 정렬규칙 | NULL허용 | 초기값
---------------+--------------------------+----------+----------+--------
 session_id    | character varying(100)   |          | not null |
 user_id       | integer                  |          | not null |
 title         | character varying(200)   |          | not null |
 last_message  | text                     |          |          |
 message_count | integer                  |          |          |
 created_at    | timestamp with time zone |          | not null | now()
 updated_at    | timestamp with time zone |          | not null | now()
 is_active     | boolean                  |          |          |
 metadata      | jsonb                    |          |          |
```

### 인덱스
- `chat_sessions_pkey` PRIMARY KEY, btree (session_id)
- `idx_chat_sessions_updated_at` btree (updated_at)
- `idx_chat_sessions_user_id` btree (user_id)
- `idx_chat_sessions_user_updated` btree (user_id, updated_at)
- `ix_chat_sessions_user_id` btree (user_id)

### 외래 키 제약
- `chat_sessions_user_id_fkey` FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

### 참조 키
- TABLE "chat_messages" CONSTRAINT "chat_messages_session_id_fkey" FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE

### ✅ Memory Service 관련 핵심 정보

**metadata 컬럼** (JSONB):
- Python 코드에서는 `session_metadata`로 사용
- Phase 1에서 메모리 저장에 활용
- 구조:
  ```json
  {
    "memories": [
      {
        "query": "...",
        "response_summary": "...",
        "relevance": "RELEVANT",
        "timestamp": "...",
        ...
      }
    ]
  }
  ```

---

## 2. chat_messages 테이블

```sql
                      "public.chat_messages" 테이블
     필드명      |           형태           | 정렬규칙 | NULL허용 |                  초기값
-----------------+--------------------------+----------+----------+------------------------------------------
 id              | integer                  |          | not null | nextval('chat_messages_id_seq'::regclass)
 session_id      | character varying(100)   |          | not null |
 role            | character varying(20)    |          | not null |
 content         | text                     |          | not null |
 structured_data | jsonb                    |          |          |
 created_at      | timestamp with time zone |          |          | now()
```

### 인덱스
- `chat_messages_pkey` PRIMARY KEY, btree (id)
- `ix_chat_messages_session_id` btree (session_id)

### 외래 키 제약
- `chat_messages_session_id_fkey` FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE

### ✅ Memory Service 관련 핵심 정보

**structured_data 컬럼** (JSONB):
- 메시지별 추가 데이터 저장 가능
- Phase 1에서 활용 가능 (선택적)

---

## 3. users 테이블

```sql
                                      "public.users" 테이블
   필드명   |           형태           | 정렬규칙 | NULL허용 |              초기값
------------+--------------------------+----------+----------+------------------------------------
 id         | integer                  |          | not null | nextval('users_id_seq'::regclass)
 email      | character varying(200)   |          | not null |
 type       | usertype                 |          | not null |
 is_active  | boolean                  |          |          |
 created_at | timestamp with time zone |          |          | now()
 updated_at | timestamp with time zone |          |          |
```

### 인덱스
- `users_pkey` PRIMARY KEY, btree (id)
- `ix_users_email` UNIQUE, btree (email)
- `ix_users_id` btree (id)

### 참조 키
- TABLE "chat_sessions" CONSTRAINT "chat_sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
- TABLE "local_auths" CONSTRAINT "local_auths_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id)
- TABLE "social_auths" CONSTRAINT "social_auths_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id)
- TABLE "user_favorites" CONSTRAINT "user_favorites_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id)
- TABLE "user_profiles" CONSTRAINT "user_profiles_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id)

---

## 🎯 Phase 0.1 Step 1 검증 결과

### ✅ 확인 사항

1. **chat_sessions.metadata (JSONB)** - ✅ 존재
   - DB 컬럼명: `metadata`
   - Python 속성명: `session_metadata`
   - Nullable: YES
   - Phase 1에서 메모리 저장에 사용 예정

2. **chat_messages.structured_data (JSONB)** - ✅ 존재
   - Nullable: YES
   - Phase 1에서 선택적 사용 가능

3. **Foreign Key 관계** - ✅ 완벽
   - chat_sessions.user_id → users.id (CASCADE DELETE)
   - chat_messages.session_id → chat_sessions.session_id (CASCADE DELETE)

4. **Memory 전용 테이블** - ❌ 없음 (예상대로)
   - conversation_memories: 없음 → Phase 2에서 생성
   - entity_memories: 없음 → Phase 2에서 생성
   - user_preferences: 없음 → Phase 2에서 생성

---

## 📋 다음 단계

- [x] Step 1: Memory 관련 핵심 테이블 스키마 추출
- [ ] Step 2: 전체 테이블 목록 추출
- [ ] Step 3: Memory 테이블 존재 여부 확인
- [ ] Step 4: JSONB 컬럼 상세 확인
- [ ] Step 5: Foreign Key 관계 확인

**다음**: Step 2 진행 (전체 테이블 목록)

