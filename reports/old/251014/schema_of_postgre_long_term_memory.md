# PostgreSQL Schema: Long-term Memory 시스템

**작성일**: 2025-10-14
**버전**: v1.0
**DB**: PostgreSQL 14+ (real_estate 데이터베이스)
**목적**: Long-term Memory 시스템 스키마 정의 및 구현 가이드

**관련 문서**:
- [Session Memory 아키텍처 v1.1](./plan_of_architecture_session_memory_v1.1.md)
- [PostgreSQL 스키마 분석 보고서](./database_schema_analysis_report.md)

---

## 📋 목차

1. [스키마 개요](#스키마-개요)
2. [테이블 정의](#테이블-정의)
3. [인덱스 및 제약조건](#인덱스-및-제약조건)
4. [Relationships](#relationships)
5. [Migration SQL](#migration-sql)
6. [사용 예시](#사용-예시)

---

## 1. 스키마 개요

### 1.1 추가될 테이블 (3개)

```
PostgreSQL Database: real_estate

기존 테이블 (13개):
├── regions, real_estates, transactions, trust_scores
├── real_estate_agents, nearby_facilities, user_favorites
├── users, user_profiles, local_auths, social_auths
└── chat_sessions, chat_messages

신규 테이블 (3개): ✅ 추가 예정
├── conversation_memories  (대화 이력 메모리)
├── user_preferences       (사용자 선호도 메모리)
└── entity_memories        (엔티티 추적 메모리)
```

### 1.2 설계 원칙

1. **user_id 필수**: 로그인 사용자만 Long-term Memory 저장 (GDPR 준수)
2. **PostgreSQL 네이티브 타입 활용**: ARRAY, JSON, UUID
3. **인덱스 최적화**: 자주 조회하는 조건에 복합 인덱스
4. **Cascade 정책**: User 삭제 시 Memory도 함께 삭제

---

## 2. 테이블 정의

### 2.1 conversation_memories (대화 이력 메모리)

#### 용도
- 모든 대화 턴 기록 (사용자 질문 + AI 응답)
- 의도 분석 결과 및 실행 메타데이터 저장
- 과거 대화 컨텍스트 로드 → Planning Agent 개인화

#### 기존 chat_messages와 차이점

| 항목 | chat_messages | conversation_memories |
|------|---------------|----------------------|
| **목적** | UI 표시용 단순 메시지 | 개인화 학습용 메타데이터 |
| **user_id** | ❌ 없음 (session_id만) | ✅ 필수 (로그인 사용자만) |
| **의도 분석** | ❌ 없음 | ✅ intent_type, confidence |
| **실행 메타** | ❌ 없음 | ✅ teams_used, tools_used, execution_time |
| **엔티티** | ❌ 없음 | ✅ entities (JSON) |
| **저장 대상** | 모든 사용자 | 로그인 사용자만 |

#### DDL

```sql
CREATE TABLE conversation_memories (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 대화 턴 정보
    turn_number INTEGER NOT NULL,
    user_query TEXT NOT NULL,
    assistant_response TEXT NOT NULL,

    -- 의도 분석 결과 (Planning Agent)
    intent_type VARCHAR(50),  -- 'legal_consult', 'market_inquiry', 'property_search'
    intent_confidence REAL CHECK (intent_confidence >= 0.0 AND intent_confidence <= 1.0),

    -- 실행 메타데이터 (Supervisor)
    teams_used TEXT[],  -- ARRAY: ['search', 'analysis']
    tools_used TEXT[],  -- ARRAY: ['legal_search', 'market_data', 'real_estate_search']
    execution_time_ms INTEGER,  -- 밀리초

    -- 추출된 엔티티 (NER)
    entities JSONB,  -- {"location": ["강남구"], "price": ["5억"], "property_type": ["아파트"]}

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT chk_turn_number CHECK (turn_number > 0),
    CONSTRAINT chk_execution_time CHECK (execution_time_ms >= 0)
);

-- Indexes
CREATE INDEX idx_conversation_session_turn ON conversation_memories(session_id, turn_number);
CREATE INDEX idx_conversation_user_recent ON conversation_memories(user_id, created_at DESC);
CREATE INDEX idx_conversation_intent_type ON conversation_memories(intent_type) WHERE intent_type IS NOT NULL;
CREATE INDEX idx_conversation_entities ON conversation_memories USING GIN(entities) WHERE entities IS NOT NULL;

-- Comments
COMMENT ON TABLE conversation_memories IS '대화 이력 메모리 - 로그인 사용자의 모든 대화 턴 기록 (의도 분석 + 실행 메타데이터)';
COMMENT ON COLUMN conversation_memories.user_id IS '사용자 ID (필수, 로그인 사용자만 저장)';
COMMENT ON COLUMN conversation_memories.turn_number IS '세션 내 턴 번호 (1부터 시작)';
COMMENT ON COLUMN conversation_memories.intent_type IS 'Planning Agent가 분석한 의도 타입';
COMMENT ON COLUMN conversation_memories.entities IS 'NER로 추출한 엔티티 (JSONB)';
```

#### 데이터 예시

```sql
INSERT INTO conversation_memories (
    session_id, user_id, turn_number,
    user_query, assistant_response,
    intent_type, intent_confidence,
    teams_used, tools_used, execution_time_ms,
    entities
) VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    42,
    1,
    '강남구 5억 이하 아파트 찾아줘',
    '강남구에서 5억 이하 아파트 10건을 찾았습니다...',
    'property_search',
    0.95,
    ARRAY['search'],
    ARRAY['real_estate_search', 'market_data'],
    2345,
    '{"location": ["강남구"], "price": ["5억"], "property_type": ["아파트"]}'::jsonb
);
```

---

### 2.2 user_preferences (사용자 선호도 메모리)

#### 용도
- 사용자의 검색 패턴 학습 (지역, 가격대, 매물 타입)
- 개인화된 추천 및 의도 분석
- 문맥 유지: "지난번 검색 이어서" 가능

#### DDL

```sql
CREATE TABLE user_preferences (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 지역 선호도
    preferred_regions TEXT[],  -- ['강남구', '서초구'] - 상위 3개
    region_search_counts JSONB,  -- {"강남구": 25, "서초구": 10, "송파구": 5}

    -- 가격 선호도
    preferred_price_range JSONB,  -- {"min": 40000, "max": 60000} (만원)
    avg_searched_price INTEGER,  -- 평균 검색 가격 (만원)

    -- 매물 타입 선호도
    preferred_property_types TEXT[],  -- ['APARTMENT', 'OFFICETEL']
    property_type_counts JSONB,  -- {"APARTMENT": 30, "OFFICETEL": 5}

    -- 검색 패턴
    frequent_queries JSONB,  -- [{"query": "강남구 아파트", "count": 15}, ...]
    search_keywords TEXT[],  -- ['지하철', '학교', '신축']

    -- 매물 상호작용
    viewed_properties INTEGER[],  -- 최근 조회한 매물 ID (최대 100개)
    favorited_properties INTEGER[],  -- 찜한 매물 ID

    -- 시간대 패턴
    active_hours JSONB,  -- {"morning": 5, "afternoon": 10, "evening": 20, "night": 3}

    -- 마지막 검색 컨텍스트 (문맥 유지)
    last_search_context JSONB,  -- {"region": "강남구", "price_max": 50000, "property_type": "APARTMENT"}

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_viewed_properties_length CHECK (array_length(viewed_properties, 1) <= 100)
);

-- Indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_regions ON user_preferences USING GIN(preferred_regions) WHERE preferred_regions IS NOT NULL;

-- Comments
COMMENT ON TABLE user_preferences IS '사용자 선호도 메모리 - 검색 패턴 학습 및 개인화';
COMMENT ON COLUMN user_preferences.preferred_regions IS '자주 검색하는 지역 (상위 3개)';
COMMENT ON COLUMN user_preferences.viewed_properties IS '최근 조회한 매물 ID (FIFO, 최대 100개)';
COMMENT ON COLUMN user_preferences.last_search_context IS '마지막 검색 컨텍스트 (문맥 유지용)';
```

#### 데이터 예시

```sql
INSERT INTO user_preferences (
    user_id,
    preferred_regions, region_search_counts,
    preferred_price_range, avg_searched_price,
    preferred_property_types, property_type_counts,
    frequent_queries, search_keywords,
    viewed_properties,
    last_search_context
) VALUES (
    42,
    ARRAY['강남구', '서초구', '송파구'],
    '{"강남구": 25, "서초구": 10, "송파구": 5}'::jsonb,
    '{"min": 40000, "max": 60000}'::jsonb,
    50000,
    ARRAY['APARTMENT', 'OFFICETEL'],
    '{"APARTMENT": 30, "OFFICETEL": 5}'::jsonb,
    '[{"query": "강남구 아파트", "count": 15}, {"query": "서초구 오피스텔", "count": 8}]'::jsonb,
    ARRAY['지하철', '학교', '신축'],
    ARRAY[123, 456, 789],
    '{"region": "강남구", "price_max": 50000, "property_type": "APARTMENT"}'::jsonb
);
```

---

### 2.3 entity_memories (엔티티 추적 메모리)

#### 용도
- 사용자가 자주 언급하는 엔티티 추적
- 문맥 참조: "그 매물", "지난번 그 지역"
- 중요도 기반 랭킹

#### DDL

```sql
CREATE TABLE entity_memories (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Key
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 엔티티 정보
    entity_type VARCHAR(50) NOT NULL,  -- 'location', 'price', 'property_id', 'property_type'
    entity_value VARCHAR(255) NOT NULL,  -- '강남구', '5억', '123'
    entity_normalized VARCHAR(255),  -- '5억' → '500000000', '강남구' → 'GANGNAM'

    -- 문맥 정보
    entity_context TEXT,  -- 엔티티가 언급된 문맥
    related_entities JSONB,  -- 함께 언급된 다른 엔티티

    -- 빈도 및 중요도
    mention_count INTEGER NOT NULL DEFAULT 1,
    importance_score REAL NOT NULL DEFAULT 1.0,

    -- Timestamps
    first_mentioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_mentioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT chk_mention_count CHECK (mention_count > 0),
    CONSTRAINT chk_importance_score CHECK (importance_score >= 0.0)
);

-- Indexes
CREATE INDEX idx_entity_lookup ON entity_memories(user_id, entity_type, entity_value);
CREATE INDEX idx_entity_importance ON entity_memories(user_id, importance_score DESC);
CREATE INDEX idx_entity_recent ON entity_memories(user_id, last_mentioned_at DESC);

-- Unique Constraint
CREATE UNIQUE INDEX idx_entity_unique ON entity_memories(user_id, entity_type, entity_value);

-- Comments
COMMENT ON TABLE entity_memories IS '엔티티 추적 메모리 - 사용자가 자주 언급하는 엔티티 추적 (문맥 참조용)';
COMMENT ON COLUMN entity_memories.entity_type IS '엔티티 타입 (location, price, property_id, property_type)';
COMMENT ON COLUMN entity_memories.mention_count IS '언급 횟수';
COMMENT ON COLUMN entity_memories.importance_score IS '중요도 점수 (mention_count 기반)';
```

#### 데이터 예시

```sql
INSERT INTO entity_memories (
    user_id, entity_type, entity_value, entity_normalized,
    entity_context, related_entities,
    mention_count, importance_score,
    first_mentioned_at, last_mentioned_at
) VALUES (
    42,
    'location',
    '강남구',
    'GANGNAM',
    '강남구 5억 이하 아파트 찾아줘',
    '{"price": ["5억"], "property_type": ["아파트"]}'::jsonb,
    25,
    25.0,
    '2025-10-01 10:00:00+09',
    '2025-10-14 15:30:00+09'
);
```

---

## 3. 인덱스 및 제약조건

### 3.1 인덱스 전략

#### conversation_memories

| 인덱스 | 타입 | 컬럼 | 용도 |
|--------|------|------|------|
| `idx_conversation_session_turn` | B-Tree | (session_id, turn_number) | 세션별 대화 순서 조회 |
| `idx_conversation_user_recent` | B-Tree | (user_id, created_at DESC) | 최근 대화 컨텍스트 로드 |
| `idx_conversation_intent_type` | B-Tree | (intent_type) | 의도별 통계 |
| `idx_conversation_entities` | GIN | (entities) | 엔티티 검색 (JSONB) |

**쿼리 최적화 예시**:
```sql
-- 최근 3개 대화 로드 (idx_conversation_user_recent 사용)
SELECT * FROM conversation_memories
WHERE user_id = 42
ORDER BY created_at DESC
LIMIT 3;

-- 특정 의도 타입 통계 (idx_conversation_intent_type 사용)
SELECT intent_type, COUNT(*) FROM conversation_memories
WHERE user_id = 42 AND intent_type IS NOT NULL
GROUP BY intent_type;

-- 엔티티 검색 (idx_conversation_entities 사용)
SELECT * FROM conversation_memories
WHERE user_id = 42
  AND entities @> '{"location": ["강남구"]}'::jsonb;
```

---

#### user_preferences

| 인덱스 | 타입 | 컬럼 | 용도 |
|--------|------|------|------|
| `idx_user_preferences_user_id` | B-Tree | (user_id) | 사용자별 선호도 조회 |
| `idx_user_preferences_regions` | GIN | (preferred_regions) | 지역 배열 검색 |

**쿼리 최적화 예시**:
```sql
-- 사용자 선호도 조회 (Primary Key 사용)
SELECT * FROM user_preferences WHERE user_id = 42;

-- 특정 지역을 선호하는 사용자 검색 (idx_user_preferences_regions 사용)
SELECT user_id FROM user_preferences
WHERE '강남구' = ANY(preferred_regions);
```

---

#### entity_memories

| 인덱스 | 타입 | 컬럼 | 용도 |
|--------|------|------|------|
| `idx_entity_lookup` | B-Tree | (user_id, entity_type, entity_value) | 엔티티 검색 |
| `idx_entity_importance` | B-Tree | (user_id, importance_score DESC) | 중요 엔티티 랭킹 |
| `idx_entity_recent` | B-Tree | (user_id, last_mentioned_at DESC) | 최근 언급 엔티티 |
| `idx_entity_unique` | Unique | (user_id, entity_type, entity_value) | 중복 방지 |

**쿼리 최적화 예시**:
```sql
-- 특정 엔티티 조회 (idx_entity_lookup 사용)
SELECT * FROM entity_memories
WHERE user_id = 42
  AND entity_type = 'location'
  AND entity_value = '강남구';

-- 중요 엔티티 Top 10 (idx_entity_importance 사용)
SELECT * FROM entity_memories
WHERE user_id = 42 AND entity_type = 'location'
ORDER BY importance_score DESC
LIMIT 10;
```

---

### 3.2 제약조건 (Constraints)

#### Foreign Key Constraints

```sql
-- conversation_memories
ALTER TABLE conversation_memories
    ADD CONSTRAINT fk_conversation_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_conversation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- user_preferences
ALTER TABLE user_preferences
    ADD CONSTRAINT fk_preference_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- entity_memories
ALTER TABLE entity_memories
    ADD CONSTRAINT fk_entity_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

**ON DELETE CASCADE 정책**:
- User 삭제 시 → 모든 Memory 데이터도 함께 삭제 (GDPR 준수)
- ChatSession 삭제 시 → 해당 세션의 ConversationMemory 삭제

---

#### Check Constraints

```sql
-- conversation_memories
ALTER TABLE conversation_memories
    ADD CONSTRAINT chk_turn_number CHECK (turn_number > 0),
    ADD CONSTRAINT chk_intent_confidence CHECK (intent_confidence >= 0.0 AND intent_confidence <= 1.0),
    ADD CONSTRAINT chk_execution_time CHECK (execution_time_ms >= 0);

-- user_preferences
ALTER TABLE user_preferences
    ADD CONSTRAINT chk_viewed_properties_length CHECK (array_length(viewed_properties, 1) <= 100);

-- entity_memories
ALTER TABLE entity_memories
    ADD CONSTRAINT chk_mention_count CHECK (mention_count > 0),
    ADD CONSTRAINT chk_importance_score CHECK (importance_score >= 0.0);
```

---

## 4. Relationships

### 4.1 ERD (Entity Relationship Diagram)

```
┌──────────────────┐
│     users        │
│ (기존)           │
│  id (PK)         │
│  email           │
│  type            │
└──────────────────┘
        │ 1
        │
        │ N
        ├──────────────────────────────────┐
        │                                  │
        │ N                                │ 1
┌──────────────────┐              ┌──────────────────┐
│ conversation_    │              │ user_            │
│ memories         │              │ preferences      │
│ (신규)           │              │ (신규)           │
│  id (PK)         │              │  id (PK)         │
│  user_id (FK) ───┤              │  user_id (FK) ───┤
│  session_id (FK) │              │                  │
│  turn_number     │              │                  │
│  user_query      │              │                  │
│  intent_type     │              │                  │
│  entities (JSON) │              │                  │
└──────────────────┘              └──────────────────┘
        │ N
        │
        │ 1
┌──────────────────┐
│ chat_sessions    │
│ (기존)           │
│  id (PK)         │
│  user_id (FK)    │
└──────────────────┘


┌──────────────────┐
│ entity_memories  │
│ (신규)           │
│  id (PK)         │
│  user_id (FK) ───┼──────→ users.id
│  entity_type     │
│  entity_value    │
│  mention_count   │
└──────────────────┘
```

---

### 4.2 SQLAlchemy Relationships 추가

#### User 모델 수정

**파일**: `backend/app/models/users.py`

```python
class User(Base):
    # ... 기존 필드 ...

    # Relationships (추가)
    conversation_memories = relationship(
        "ConversationMemory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    preference = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    entity_memories = relationship(
        "EntityMemory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

---

#### ChatSession 모델 수정

**파일**: `backend/app/models/chat.py`

```python
class ChatSession(Base):
    # ... 기존 필드 ...

    # Relationships (추가)
    conversation_memories = relationship(
        "ConversationMemory",
        back_populates="session",
        cascade="all, delete-orphan"
    )
```

---

#### Memory 모델 정의

**파일**: `backend/app/models/memory.py` (신규)

```python
from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base

class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # ... 기타 필드 ...

    # Relationships
    session = relationship("ChatSession", back_populates="conversation_memories")
    user = relationship("User", back_populates="conversation_memories")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    # ... 기타 필드 ...

    # Relationships
    user = relationship("User", back_populates="preference")

class EntityMemory(Base):
    __tablename__ = "entity_memories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # ... 기타 필드 ...

    # Relationships
    user = relationship("User", back_populates="entity_memories")
```

---

## 5. Migration SQL

### 5.1 Alembic Migration 생성

```bash
# 1. models/__init__.py에 import 추가
# backend/app/models/__init__.py

from app.models.memory import ConversationMemory, UserPreference, EntityMemory

__all__ = [
    # ... 기존 모델들 ...
    "ConversationMemory",
    "UserPreference",
    "EntityMemory",
]

# 2. Alembic migration 생성
alembic revision --autogenerate -m "Add Long-term Memory models (ConversationMemory, UserPreference, EntityMemory)"

# 3. Migration 실행
alembic upgrade head

# 4. 확인
psql -U postgres -d real_estate -c "\dt *memories*"
```

---

### 5.2 수동 Migration SQL (Alembic 없이)

```sql
-- ============================================================================
-- 1. conversation_memories 테이블 생성
-- ============================================================================

CREATE TABLE conversation_memories (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL CHECK (turn_number > 0),
    user_query TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    intent_type VARCHAR(50),
    intent_confidence REAL CHECK (intent_confidence >= 0.0 AND intent_confidence <= 1.0),
    teams_used TEXT[],
    tools_used TEXT[],
    execution_time_ms INTEGER CHECK (execution_time_ms >= 0),
    entities JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversation_session_turn ON conversation_memories(session_id, turn_number);
CREATE INDEX idx_conversation_user_recent ON conversation_memories(user_id, created_at DESC);
CREATE INDEX idx_conversation_intent_type ON conversation_memories(intent_type) WHERE intent_type IS NOT NULL;
CREATE INDEX idx_conversation_entities ON conversation_memories USING GIN(entities) WHERE entities IS NOT NULL;

COMMENT ON TABLE conversation_memories IS '대화 이력 메모리 - 로그인 사용자의 모든 대화 턴 기록 (의도 분석 + 실행 메타데이터)';

-- ============================================================================
-- 2. user_preferences 테이블 생성
-- ============================================================================

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferred_regions TEXT[],
    region_search_counts JSONB,
    preferred_price_range JSONB,
    avg_searched_price INTEGER,
    preferred_property_types TEXT[],
    property_type_counts JSONB,
    frequent_queries JSONB,
    search_keywords TEXT[],
    viewed_properties INTEGER[] CHECK (array_length(viewed_properties, 1) <= 100),
    favorited_properties INTEGER[],
    active_hours JSONB,
    last_search_context JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_regions ON user_preferences USING GIN(preferred_regions) WHERE preferred_regions IS NOT NULL;

COMMENT ON TABLE user_preferences IS '사용자 선호도 메모리 - 검색 패턴 학습 및 개인화';

-- ============================================================================
-- 3. entity_memories 테이블 생성
-- ============================================================================

CREATE TABLE entity_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_value VARCHAR(255) NOT NULL,
    entity_normalized VARCHAR(255),
    entity_context TEXT,
    related_entities JSONB,
    mention_count INTEGER NOT NULL DEFAULT 1 CHECK (mention_count > 0),
    importance_score REAL NOT NULL DEFAULT 1.0 CHECK (importance_score >= 0.0),
    first_mentioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_mentioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_entity_lookup ON entity_memories(user_id, entity_type, entity_value);
CREATE INDEX idx_entity_importance ON entity_memories(user_id, importance_score DESC);
CREATE INDEX idx_entity_recent ON entity_memories(user_id, last_mentioned_at DESC);
CREATE UNIQUE INDEX idx_entity_unique ON entity_memories(user_id, entity_type, entity_value);

COMMENT ON TABLE entity_memories IS '엔티티 추적 메모리 - 사용자가 자주 언급하는 엔티티 추적 (문맥 참조용)';

-- ============================================================================
-- 4. 생성 확인
-- ============================================================================

SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename LIKE '%memories%' OR tablename LIKE '%preferences%'
ORDER BY tablename;
```

---

### 5.3 Rollback SQL

```sql
-- 역순으로 삭제 (FK 제약조건 때문)

DROP TABLE IF EXISTS entity_memories CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS conversation_memories CASCADE;
```

---

## 6. 사용 예시

### 6.1 대화 저장 (Supervisor)

```sql
-- Turn 1: 사용자가 "강남구 5억 이하 아파트" 검색
INSERT INTO conversation_memories (
    session_id, user_id, turn_number,
    user_query, assistant_response,
    intent_type, intent_confidence,
    teams_used, tools_used, execution_time_ms,
    entities
) VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
    42,
    1,
    '강남구 5억 이하 아파트 찾아줘',
    '강남구에서 5억 이하 아파트 10건을 찾았습니다. 1. 강남 아파트 A...',
    'property_search',
    0.95,
    ARRAY['search'],
    ARRAY['real_estate_search', 'market_data'],
    2345,
    '{"location": ["강남구"], "price": ["5억"], "property_type": ["아파트"]}'::jsonb
);

-- 선호도 업데이트
INSERT INTO user_preferences (user_id, preferred_regions, region_search_counts)
VALUES (42, ARRAY['강남구'], '{"강남구": 1}'::jsonb)
ON CONFLICT (user_id) DO UPDATE SET
    region_search_counts = jsonb_set(
        COALESCE(user_preferences.region_search_counts, '{}'::jsonb),
        '{강남구}',
        to_jsonb(COALESCE((user_preferences.region_search_counts->>'강남구')::int, 0) + 1)
    ),
    updated_at = now();
```

---

### 6.2 과거 대화 컨텍스트 로드 (Planning Agent)

```sql
-- 최근 3개 대화 로드
SELECT
    turn_number,
    user_query,
    assistant_response,
    intent_type,
    entities,
    created_at
FROM conversation_memories
WHERE user_id = 42
ORDER BY created_at DESC
LIMIT 3;

-- 결과:
-- turn_number | user_query | assistant_response | intent_type | entities | created_at
-- 3 | "첫 번째 매물 상세" | "강남 아파트 A..." | property_detail | {...} | 2025-10-14 15:35
-- 2 | "지하철 근처만" | "지하철 역세권..." | property_search | {...} | 2025-10-14 15:32
-- 1 | "강남구 5억 아파트" | "10건 찾음..." | property_search | {...} | 2025-10-14 15:30
```

---

### 6.3 사용자 선호도 조회

```sql
-- 사용자 42의 선호도
SELECT
    preferred_regions,
    region_search_counts,
    preferred_price_range,
    preferred_property_types
FROM user_preferences
WHERE user_id = 42;

-- 결과:
-- preferred_regions: ['강남구', '서초구', '송파구']
-- region_search_counts: {"강남구": 25, "서초구": 10, "송파구": 5}
-- preferred_price_range: {"min": 40000, "max": 60000}
-- preferred_property_types: ['APARTMENT']
```

---

### 6.4 엔티티 추적

```sql
-- "강남구" 엔티티 업데이트 (또는 생성)
INSERT INTO entity_memories (
    user_id, entity_type, entity_value,
    entity_context, mention_count, importance_score,
    first_mentioned_at, last_mentioned_at
) VALUES (
    42, 'location', '강남구',
    '강남구 5억 이하 아파트 찾아줘',
    1, 1.0,
    now(), now()
)
ON CONFLICT (user_id, entity_type, entity_value) DO UPDATE SET
    mention_count = entity_memories.mention_count + 1,
    importance_score = entity_memories.mention_count + 1.0,
    entity_context = EXCLUDED.entity_context,
    last_mentioned_at = now();

-- 중요 엔티티 Top 10
SELECT
    entity_type,
    entity_value,
    mention_count,
    importance_score,
    last_mentioned_at
FROM entity_memories
WHERE user_id = 42 AND entity_type = 'location'
ORDER BY importance_score DESC
LIMIT 10;
```

---

### 6.5 통계 쿼리

```sql
-- 사용자의 의도별 통계
SELECT
    intent_type,
    COUNT(*) as count,
    AVG(execution_time_ms) as avg_time_ms
FROM conversation_memories
WHERE user_id = 42 AND intent_type IS NOT NULL
GROUP BY intent_type
ORDER BY count DESC;

-- 결과:
-- intent_type | count | avg_time_ms
-- property_search | 35 | 2300
-- legal_consult | 10 | 1800
-- market_inquiry | 5 | 1500
```

---

## 7. 성능 최적화

### 7.1 쿼리 최적화 팁

#### JSONB 인덱스 활용

```sql
-- GIN 인덱스로 JSONB 검색 최적화
CREATE INDEX idx_conversation_entities ON conversation_memories USING GIN(entities);

-- 엔티티 검색 (인덱스 사용)
SELECT * FROM conversation_memories
WHERE entities @> '{"location": ["강남구"]}'::jsonb;

-- 특정 key 존재 여부
SELECT * FROM conversation_memories
WHERE entities ? 'location';
```

---

#### ARRAY 인덱스 활용

```sql
-- GIN 인덱스로 ARRAY 검색 최적화
CREATE INDEX idx_user_preferences_regions ON user_preferences USING GIN(preferred_regions);

-- '강남구'를 선호하는 사용자 검색
SELECT user_id FROM user_preferences
WHERE '강남구' = ANY(preferred_regions);
```

---

### 7.2 파티셔닝 (대규모 데이터)

```sql
-- conversation_memories를 월별로 파티셔닝 (수백만 건 이상 시)
CREATE TABLE conversation_memories (
    -- 기존 필드들 ...
) PARTITION BY RANGE (created_at);

CREATE TABLE conversation_memories_2025_10 PARTITION OF conversation_memories
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE conversation_memories_2025_11 PARTITION OF conversation_memories
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

---

### 7.3 데이터 정리

```sql
-- 6개월 이상 된 대화 삭제 (GDPR 준수)
DELETE FROM conversation_memories
WHERE created_at < now() - INTERVAL '6 months';

-- 또는 Soft Delete
ALTER TABLE conversation_memories ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX idx_conversation_deleted ON conversation_memories(deleted_at) WHERE deleted_at IS NULL;

UPDATE conversation_memories SET deleted_at = now()
WHERE created_at < now() - INTERVAL '6 months';
```

---

## 8. 참고 자료

### 8.1 PostgreSQL 공식 문서
- [JSONB 타입](https://www.postgresql.org/docs/14/datatype-json.html)
- [ARRAY 타입](https://www.postgresql.org/docs/14/arrays.html)
- [GIN 인덱스](https://www.postgresql.org/docs/14/gin.html)
- [파티셔닝](https://www.postgresql.org/docs/14/ddl-partitioning.html)

### 8.2 관련 내부 문서
- [Session Memory 아키텍처 v1.1](./plan_of_architecture_session_memory_v1.1.md)
- [PostgreSQL 스키마 분석 보고서](./database_schema_analysis_report.md)
- [Phase 1-2 완료 보고서](./phase_1_2_completion_report_v3.md)

---

## 9. 체크리스트

### Migration 실행 전
- [ ] PostgreSQL 14+ 버전 확인
- [ ] 백업 생성: `pg_dump -U postgres real_estate > backup_$(date +%Y%m%d).sql`
- [ ] models/memory.py 작성 완료
- [ ] models/__init__.py에 import 추가
- [ ] Alembic revision 생성

### Migration 실행
- [ ] `alembic upgrade head` 실행
- [ ] 테이블 생성 확인: `\dt *memories*`
- [ ] 인덱스 생성 확인: `\di *memories*`
- [ ] Foreign Key 확인: `\d conversation_memories`

### 코드 통합
- [ ] LongTermMemoryService 구현
- [ ] Planning Agent 통합
- [ ] Supervisor 통합
- [ ] Unit Test 작성
- [ ] Integration Test 작성

---

**문서 버전**: v1.0
**최종 업데이트**: 2025-10-14
**검증 상태**: ⏳ Migration 실행 대기 중

---

**승인자**: _______________
**승인일**: 2025-10-14
**다음 검토일**: Migration 실행 후
