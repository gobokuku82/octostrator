# 데이터베이스 스키마 문서

**작성일**: 2025-11-03
**버전**: 0.4.0
**데이터베이스**: PostgreSQL 13+

---

## dbdiagram.io로 시각화하기

### 방법 1: 웹 사이트에서 직접 열기

1. https://dbdiagram.io/d 접속
2. 좌측 에디터에 `DB_스키마_251103.dbml` 파일 내용을 복사하여 붙여넣기
3. 자동으로 다이어그램이 생성됩니다

### 방법 2: 파일 가져오기

1. https://dbdiagram.io/ 접속
2. 상단 메뉴에서 "Import" 클릭
3. "From file" 선택
4. `DB_스키마_251103.dbml` 파일 업로드

---

## 스키마 구조

### 핵심 테이블 (구현 완료)

#### 1. checkpoints
LangGraph의 StateGraph 상태를 저장하는 메인 테이블

**주요 컬럼**:
- `thread_id`: 세션 식별자 (session_id와 동일)
- `checkpoint_id`: 체크포인트 고유 ID (UUID)
- `checkpoint`: 직렬화된 상태 데이터 (bytea)
- `metadata`: 메타데이터

**용도**:
- 각 노드 실행 후 상태 저장
- 세션 복원 (타임 트래블)
- 에러 발생 시 롤백

#### 2. checkpoint_writes
체크포인트의 변경 사항을 추적하는 로그 테이블

**주요 컬럼**:
- `thread_id`, `checkpoint_id`: 관련 체크포인트
- `channel`: 상태 키 (messages, user_intent, plan 등)
- `value`: 변경된 값
- `idx`: 쓰기 순서

**용도**:
- 상태 변경 추적
- 디버깅
- 성능 분석

---

### 확장 테이블 (향후 구현)

#### 3. sessions
세션 메타데이터 관리

**현재 상태**: 메모리 기반 (SessionManager)
**향후 계획**: PostgreSQL로 영구 저장

**주요 컬럼**:
- `thread_id`: 세션 ID
- `user_id`: 사용자 ID
- `status`: active, waiting_human, completed 등
- `is_waiting_human`: HITL 대기 플래그

**용도**:
- 세션 상태 추적
- 사용자별 세션 조회
- HITL 대기 세션 찾기

#### 4. session_messages
메시지 히스토리 (옵션)

**현재**: checkpoint에 포함되어 저장
**향후**: 빠른 조회를 위해 분리 가능

#### 5. agent_executions
에이전트 실행 로그 (모니터링용)

**용도**:
- 성능 분석
- 에러 추적
- 에이전트별 실행 통계

#### 6. hitl_approvals
HITL 승인 이력

**용도**:
- 승인/거부 추적
- 컴플라이언스 감사 로그
- 사용자 응답 패턴 분석

#### 7. users
사용자 관리 (인증/권한)

**향후 기능**:
- API 키 기반 인증
- 역할 기반 접근 제어 (RBAC)
- 사용자별 할당량 관리

---

## 데이터 흐름

```
1. 사용자 요청
   ↓
2. sessions 생성/업데이트 (메모리 or DB)
   ↓
3. Supervisor Graph 실행
   ↓
4. 각 노드 실행마다
   ├── checkpoints 테이블에 상태 저장
   ├── checkpoint_writes에 변경 사항 기록
   └── agent_executions에 실행 로그 (옵션)
   ↓
5. HITL 발생 시
   ├── sessions.is_waiting_human = true
   └── hitl_approvals에 요청 기록 (옵션)
   ↓
6. 사용자 승인/거부
   ↓
7. Graph 재개 및 최종 상태 저장
```

---

## 인덱스 전략

### 자주 사용되는 쿼리

1. **세션 조회**: `thread_id`로 최신 체크포인트 조회
2. **HITL 대기 세션**: `is_waiting_human = true`인 세션 조회
3. **사용자별 세션**: `user_id`로 모든 세션 조회
4. **시간 범위 조회**: `created_at` 기반 쿼리

### 최적화된 인덱스

```sql
-- checkpoints 테이블
CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at);

-- sessions 테이블
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_waiting_human ON sessions(is_waiting_human)
  WHERE is_waiting_human = true;  -- Partial index

-- agent_executions 테이블
CREATE INDEX idx_executions_thread_started ON agent_executions(thread_id, started_at);
CREATE INDEX idx_executions_agent_name ON agent_executions(agent_name);
```

---

## SQL 예제

### 1. 최신 체크포인트 조회

```sql
SELECT
  thread_id,
  checkpoint_id,
  created_at,
  metadata
FROM checkpoints
WHERE thread_id = 'session_001'
ORDER BY created_at DESC
LIMIT 1;
```

### 2. HITL 대기 중인 세션 조회

```sql
SELECT
  thread_id,
  user_id,
  status,
  updated_at
FROM sessions
WHERE is_waiting_human = true
AND status = 'waiting_human'
ORDER BY updated_at ASC;
```

### 3. 사용자별 세션 통계

```sql
SELECT
  user_id,
  COUNT(*) as total_sessions,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_sessions,
  AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_seconds
FROM sessions
GROUP BY user_id;
```

### 4. 에이전트 성능 분석

```sql
SELECT
  agent_name,
  COUNT(*) as execution_count,
  AVG(execution_time_ms) as avg_execution_time,
  MAX(execution_time_ms) as max_execution_time,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failure_count
FROM agent_executions
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY agent_name
ORDER BY avg_execution_time DESC;
```

### 5. 체크포인트 정리 (오래된 데이터 삭제)

```sql
-- 30일 이상 된 체크포인트 삭제
DELETE FROM checkpoint_writes
WHERE checkpoint_id IN (
  SELECT checkpoint_id
  FROM checkpoints
  WHERE created_at < NOW() - INTERVAL '30 days'
);

DELETE FROM checkpoints
WHERE created_at < NOW() - INTERVAL '30 days';
```

---

## 마이그레이션

### 초기 테이블 생성

LangGraph의 AsyncPostgresSaver가 자동으로 `checkpoints`와 `checkpoint_writes` 테이블을 생성합니다.

```python
# backend/app/octostrator/checkpointer/postgres_checkpointer.py
checkpointer = AsyncPostgresSaver.from_conn_string(conn_string)
await checkpointer.setup()  # 테이블 자동 생성
```

### 확장 테이블 생성 (수동)

`manual/migrations/001_create_sessions.sql`:

```sql
-- sessions 테이블
CREATE TABLE IF NOT EXISTS sessions (
  thread_id VARCHAR(255) PRIMARY KEY,
  user_id VARCHAR(255),
  status VARCHAR(50) NOT NULL DEFAULT 'active',
  is_waiting_human BOOLEAN DEFAULT false,
  last_checkpoint_id VARCHAR(255),
  session_metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_waiting_human ON sessions(is_waiting_human)
  WHERE is_waiting_human = true;

-- session_messages 테이블
CREATE TABLE IF NOT EXISTS session_messages (
  id BIGSERIAL PRIMARY KEY,
  thread_id VARCHAR(255) NOT NULL REFERENCES sessions(thread_id) ON DELETE CASCADE,
  message_type VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  message_metadata JSONB,
  sequence_number INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_thread_id ON session_messages(thread_id);
CREATE INDEX idx_messages_thread_seq ON session_messages(thread_id, sequence_number);

-- agent_executions 테이블
CREATE TABLE IF NOT EXISTS agent_executions (
  id BIGSERIAL PRIMARY KEY,
  thread_id VARCHAR(255) NOT NULL REFERENCES sessions(thread_id) ON DELETE CASCADE,
  checkpoint_id VARCHAR(255),
  agent_name VARCHAR(100) NOT NULL,
  node_name VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL,
  input_data JSONB,
  output_data JSONB,
  error_message TEXT,
  execution_time_ms INTEGER,
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP
);

CREATE INDEX idx_executions_thread_id ON agent_executions(thread_id);
CREATE INDEX idx_executions_agent_name ON agent_executions(agent_name);
CREATE INDEX idx_executions_started_at ON agent_executions(started_at);

-- hitl_approvals 테이블
CREATE TABLE IF NOT EXISTS hitl_approvals (
  id BIGSERIAL PRIMARY KEY,
  thread_id VARCHAR(255) NOT NULL REFERENCES sessions(thread_id) ON DELETE CASCADE,
  checkpoint_id VARCHAR(255) NOT NULL,
  agent_name VARCHAR(100),
  approval_type VARCHAR(50) NOT NULL,
  request_message TEXT NOT NULL,
  request_context JSONB,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  response_message TEXT,
  requested_at TIMESTAMP DEFAULT NOW(),
  responded_at TIMESTAMP
);

CREATE INDEX idx_approvals_thread_id ON hitl_approvals(thread_id);
CREATE INDEX idx_approvals_status ON hitl_approvals(status);
```

---

## 성능 고려사항

### 1. 파티셔닝

대용량 데이터 처리를 위해 시간 기반 파티셔닝:

```sql
-- checkpoints 테이블을 월별로 파티셔닝
CREATE TABLE checkpoints_partitioned (
  LIKE checkpoints INCLUDING ALL
) PARTITION BY RANGE (created_at);

CREATE TABLE checkpoints_2025_11 PARTITION OF checkpoints_partitioned
  FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE checkpoints_2025_12 PARTITION OF checkpoints_partitioned
  FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

### 2. 연결 풀링

```python
# PostgreSQL 연결 풀 설정
checkpointer = AsyncPostgresSaver.from_conn_string(
    conn_string,
    pool_size=10,        # 기본 연결 수
    max_overflow=20      # 최대 추가 연결 수
)
```

### 3. 백업 전략

```bash
# 일일 백업
pg_dump -h localhost -U postgres -d octo_chatbot > backup_$(date +%Y%m%d).sql

# 압축 백업
pg_dump -h localhost -U postgres -d octo_chatbot | gzip > backup_$(date +%Y%m%d).sql.gz

# 복원
psql -h localhost -U postgres -d octo_chatbot < backup_20251103.sql
```

---

## 참조

- [시스템 아키텍처 명세서](./시스템_아키텍처_명세서_251103.md)
- [개발자 가이드](./개발자_가이드_251103.md)
- [dbdiagram.io 문서](https://dbdiagram.io/docs)
- [LangGraph Checkpointer 문서](https://python.langchain.com/docs/langgraph)
