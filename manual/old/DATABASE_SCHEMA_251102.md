# Database Schema Documentation

**작성일**: 2025-11-02
**프로젝트**: HolmesNyangz beta_v001
**데이터베이스**: PostgreSQL (real_estate)
**작성자**: Claude Code

---

## 📋 목차

1. [개요](#개요)
2. [ERD (Entity Relationship Diagram)](#erd-entity-relationship-diagram)
3. [테이블 상세 스키마](#테이블-상세-스키마)
4. [인덱스 및 제약조건](#인덱스-및-제약조건)
5. [JSONB 필드 구조](#jsonb-필드-구조)
6. [관계 (Relationships)](#관계-relationships)
7. [Enum 타입](#enum-타입)

---

## 개요

### 데이터베이스 정보

- **DBMS**: PostgreSQL 15+
- **데이터베이스명**: `real_estate`
- **문자 인코딩**: UTF-8
- **연결 URL**: `postgresql://postgres:root1234@localhost:5432/real_estate`

### 테이블 그룹

| 그룹 | 테이블 | 설명 |
|-----|-------|------|
| **사용자 관리** | users, user_profiles, local_auths, social_auths, user_favorites | 사용자 계정 및 인증 |
| **채팅 시스템** | chat_sessions, chat_messages | 채팅 세션 및 메시지 |
| **부동산 정보** | regions, real_estates, transactions | 부동산 매물 및 거래 |
| **부가 정보** | nearby_facilities, real_estate_agents, trust_scores | 편의시설, 중개사, 신뢰도 |
| **LangGraph** | checkpoints, checkpoint_blobs, checkpoint_writes | LangGraph 상태 관리 |

---

## ERD (Entity Relationship Diagram)

```mermaid
erDiagram
    %% ===== 사용자 관리 =====
    users ||--o| user_profiles : "1:1"
    users ||--o| local_auths : "1:1"
    users ||--o{ social_auths : "1:N"
    users ||--o{ user_favorites : "1:N"
    users ||--o{ chat_sessions : "1:N"

    %% ===== 채팅 시스템 =====
    chat_sessions ||--o{ chat_messages : "1:N"

    %% ===== 부동산 정보 =====
    regions ||--o{ real_estates : "1:N"
    regions ||--o{ transactions : "1:N"
    real_estates ||--o{ transactions : "1:N"
    real_estates ||--o{ user_favorites : "1:N"
    real_estates ||--o| nearby_facilities : "1:1"
    real_estates ||--o{ real_estate_agents : "1:N"
    real_estates ||--o| trust_scores : "1:1"

    %% ===== 사용자 =====
    users {
        int id PK
        string email UK
        enum type
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    user_profiles {
        int id PK
        int user_id FK,UK
        string nickname UK
        text bio
        enum gender
        string birth_date
        string image_url
        timestamp created_at
        timestamp updated_at
    }

    local_auths {
        int user_id PK,FK
        string hashed_password
        timestamp created_at
        timestamp updated_at
    }

    social_auths {
        int id PK
        int user_id FK
        enum provider
        string provider_user_id
        timestamp created_at
        timestamp updated_at
    }

    user_favorites {
        int id PK
        int user_id FK
        int real_estate_id FK
        timestamp created_at
    }

    %% ===== 채팅 시스템 =====
    chat_sessions {
        string session_id PK
        int user_id FK
        string title
        text last_message
        int message_count
        timestamp created_at
        timestamp updated_at
        boolean is_active
        jsonb metadata
    }

    chat_messages {
        int id PK
        string session_id FK
        string role
        text content
        jsonb structured_data
        timestamp created_at
    }

    %% ===== 부동산 =====
    regions {
        int id PK
        string code UK
        string name
        timestamp created_at
        timestamp updated_at
    }

    real_estates {
        int id PK
        enum property_type
        string code UK
        string name
        int region_id FK
        string address
        string address_detail
        decimal latitude
        decimal longitude
        int total_households
        int total_buildings
        string completion_date
        float min_exclusive_area
        float max_exclusive_area
        float representative_area
        float floor_area_ratio
        float exclusive_area
        float supply_area
        float exclusive_area_pyeong
        float supply_area_pyeong
        string direction
        string floor_info
        text building_description
        array tag_list
        int deal_count
        int lease_count
        int rent_count
        int short_term_rent_count
        timestamp created_at
        timestamp updated_at
    }

    transactions {
        int id PK
        int real_estate_id FK
        int region_id FK
        enum transaction_type
        timestamp transaction_date
        int sale_price
        int deposit
        int monthly_rent
        int min_sale_price
        int max_sale_price
        int min_deposit
        int max_deposit
        int min_monthly_rent
        int max_monthly_rent
        string article_no UK
        string article_confirm_ymd
        timestamp created_at
        timestamp updated_at
    }

    nearby_facilities {
        int id PK
        int real_estate_id FK
        string subway_line
        int subway_distance
        int subway_walking_time
        text elementary_schools
        text middle_schools
        text high_schools
    }

    real_estate_agents {
        int id PK
        int real_estate_id FK
        string agent_name
        string company_name
        boolean is_direct_trade
        timestamp created_at
        timestamp updated_at
    }

    trust_scores {
        int id PK
        int real_estate_id FK
        decimal score
        text verification_notes
        timestamp calculated_at
        timestamp updated_at
    }
```

### DBML (dbdiagram.io)

**사용 방법**: 아래 코드를 복사하여 [dbdiagram.io](https://dbdiagram.io) 에디터에 붙여넣기

```dbml
// ===== 프로젝트 정보 =====
Project HolmesNyangz {
  database_type: 'PostgreSQL'
  Note: '''
    # HolmesNyangz 부동산 AI 챗봇 데이터베이스
    - 사용자 관리 및 인증
    - 채팅 시스템 (3-Tier Memory)
    - 부동산 매물 및 거래 정보
    - LangGraph 워크플로우 상태 관리
  '''
}

// ===== Enum 정의 =====
Enum user_type {
  admin
  user
  agent
}

Enum gender {
  male
  female
  other
}

Enum social_provider {
  google
  kakao
  naver
  apple
}

Enum property_type {
  apartment
  officetel
  oneroom
  villa
  house
}

Enum transaction_type {
  sale
  jeonse
  rent
}

// ===== 사용자 관리 테이블 =====
Table users {
  id integer [pk, increment]
  email varchar(200) [not null, unique]
  type user_type [not null, default: 'user']
  is_active boolean [default: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    email [name: 'idx_users_email']
  }

  Note: '사용자 계정 정보'
}

Table user_profiles {
  id integer [pk, increment]
  user_id integer [unique, not null, ref: - users.id]
  nickname varchar(20) [unique, not null]
  bio text
  gender gender [not null]
  birth_date varchar(8) [not null, note: 'YYYYMMDD']
  image_url varchar(500)
  created_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    user_id [name: 'idx_user_profiles_user_id']
    nickname [unique, name: 'idx_user_profiles_nickname']
  }

  Note: '사용자 프로필 상세 정보'
}

Table local_auths {
  user_id integer [pk, ref: - users.id]
  hashed_password varchar(255) [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp

  Note: '로컬 로그인 인증 정보'
}

Table social_auths {
  id integer [pk, increment]
  user_id integer [not null, ref: > users.id]
  provider social_provider [not null]
  provider_user_id varchar(100) [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    (provider, provider_user_id) [unique, name: 'idx_provider_user']
  }

  Note: '소셜 로그인 인증 정보'
}

Table user_favorites {
  id integer [pk, increment]
  user_id integer [not null, ref: > users.id]
  real_estate_id integer [not null, ref: > real_estates.id]
  created_at timestamp [default: `now()`]

  indexes {
    (user_id, real_estate_id) [unique, name: 'idx_user_real_estate']
  }

  Note: '사용자 찜 목록'
}

// ===== 채팅 시스템 테이블 =====
Table chat_sessions {
  session_id varchar(100) [pk]
  user_id integer [not null, ref: > users.id]
  title varchar(200) [not null, default: '새 대화']
  last_message text
  message_count integer [default: 0]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  is_active boolean [default: true]
  metadata jsonb [note: '3-Tier Memory 저장: conversation_summary']

  indexes {
    user_id [name: 'idx_chat_sessions_user_id']
    updated_at [name: 'idx_chat_sessions_updated_at']
    (user_id, updated_at) [name: 'idx_chat_sessions_user_updated']
  }

  Note: '''
    채팅 세션
    - metadata.conversation_summary: LLM 생성 요약
    - 3-Tier Memory 시스템의 핵심
  '''
}

Table chat_messages {
  id integer [pk, increment]
  session_id varchar(100) [not null, ref: > chat_sessions.session_id]
  role varchar(20) [not null, note: 'user/assistant/system']
  content text [not null]
  structured_data jsonb [note: 'sections, metadata']
  created_at timestamp [default: `now()`]

  indexes {
    session_id [name: 'idx_chat_messages_session_id']
  }

  Note: '채팅 메시지 (user/assistant)'
}

// ===== 부동산 정보 테이블 =====
Table regions {
  id integer [pk, increment]
  code varchar(20) [unique, not null, note: '법정동코드']
  name varchar(50) [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    code [unique, name: 'idx_regions_code']
  }

  Note: '지역 정보 (법정동 기준)'
}

Table real_estates {
  id integer [pk, increment]
  property_type property_type [not null]
  code varchar(30) [unique, not null, note: '단지코드/매물코드']
  name varchar(100) [not null]
  region_id integer [not null, ref: > regions.id]
  address varchar(255) [not null]
  address_detail varchar(255)
  latitude decimal(10,7)
  longitude decimal(10,7)

  // 건물 스펙
  total_households integer
  total_buildings integer
  completion_date varchar(6) [note: 'YYYYMM']
  min_exclusive_area float
  max_exclusive_area float
  representative_area float
  floor_area_ratio float

  // 개별 매물 상세
  exclusive_area float [note: '전용면적(㎡)']
  supply_area float [note: '공급면적(㎡)']
  exclusive_area_pyeong float [note: '전용면적(평)']
  supply_area_pyeong float [note: '공급면적(평)']
  direction varchar(20)
  floor_info varchar(50)

  // 설명
  building_description text
  tag_list "varchar[]" [note: 'Array']

  // 매물 통계
  deal_count integer [default: 0]
  lease_count integer [default: 0]
  rent_count integer [default: 0]
  short_term_rent_count integer [default: 0]

  created_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    code [unique, name: 'idx_real_estates_code']
    region_id [name: 'idx_real_estates_region_id']
  }

  Note: '부동산 매물 기본 정보'
}

Table transactions {
  id integer [pk, increment]
  real_estate_id integer [not null, ref: > real_estates.id]
  region_id integer [not null, ref: > regions.id]
  transaction_type transaction_type
  transaction_date timestamp

  // 가격 정보 (개별 거래)
  sale_price integer [default: 0, note: '매매가(만원)']
  deposit integer [default: 0, note: '보증금(만원)']
  monthly_rent integer [default: 0, note: '월세(만원)']

  // 가격 범위 (단지 통계)
  min_sale_price integer [default: 0]
  max_sale_price integer [default: 0]
  min_deposit integer [default: 0]
  max_deposit integer [default: 0]
  min_monthly_rent integer [default: 0]
  max_monthly_rent integer [default: 0]

  article_no varchar(50) [unique, note: '매물번호']
  article_confirm_ymd varchar(10)

  created_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    (transaction_date, transaction_type) [name: 'idx_transaction_date_type']
    (real_estate_id, transaction_date) [name: 'idx_real_estate_date']
    article_no [unique, name: 'idx_article_no']
  }

  Note: '실거래 내역 및 시세 정보'
}

// ===== 부가 정보 테이블 =====
Table nearby_facilities {
  id integer [pk, increment]
  real_estate_id integer [ref: - real_estates.id]

  // 지하철
  subway_line varchar(50)
  subway_distance integer
  subway_walking_time integer

  // 학교
  elementary_schools text
  middle_schools text
  high_schools text

  Note: '주변 편의시설 정보'
}

Table real_estate_agents {
  id integer [pk, increment]
  real_estate_id integer [ref: > real_estates.id]
  agent_name varchar(100)
  company_name varchar(100)
  is_direct_trade boolean [default: false]
  created_at timestamp [default: `now()`]
  updated_at timestamp

  Note: '부동산 중개사 정보'
}

Table trust_scores {
  id integer [pk, increment]
  real_estate_id integer [not null, ref: - real_estates.id]
  score decimal(5,2) [not null, note: '0-100']
  verification_notes text
  calculated_at timestamp [default: `now()`]
  updated_at timestamp

  indexes {
    real_estate_id [name: 'idx_trust_scores_real_estate_id']
  }

  Note: '매물 신뢰도 점수'
}

// ===== LangGraph 테이블 (자동 생성) =====
Table checkpoints {
  thread_id text [not null]
  checkpoint_ns text [not null, default: '']
  checkpoint_id text [not null]
  parent_checkpoint_id text
  type text
  checkpoint jsonb [not null]
  metadata jsonb [not null, default: '{}']

  indexes {
    (thread_id, checkpoint_ns, checkpoint_id) [pk]
  }

  Note: 'LangGraph 워크플로우 체크포인트'
}

Table checkpoint_blobs {
  thread_id text [not null]
  checkpoint_ns text [not null, default: '']
  channel text [not null]
  version text [not null]
  type text [not null]
  blob bytea

  indexes {
    (thread_id, checkpoint_ns, channel, version) [pk]
  }

  Note: 'LangGraph 바이너리 데이터'
}

Table checkpoint_writes {
  thread_id text [not null]
  checkpoint_ns text [not null, default: '']
  checkpoint_id text [not null]
  task_id text [not null]
  idx integer [not null]
  channel text [not null]
  type text
  blob bytea

  indexes {
    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) [pk]
  }

  Note: 'LangGraph 쓰기 작업 추적'
}

// ===== 관계 정의 요약 =====
// 1:1 관계
// - users → user_profiles
// - users → local_auths
// - real_estates → nearby_facilities
// - real_estates → trust_scores

// 1:N 관계
// - users → social_auths
// - users → user_favorites
// - users → chat_sessions
// - chat_sessions → chat_messages
// - regions → real_estates
// - regions → transactions
// - real_estates → transactions
// - real_estates → user_favorites
// - real_estates → real_estate_agents

// Cascade 삭제
// - users 삭제 시: profiles, auths, sessions, messages 모두 삭제
// - real_estates 삭제 시: transactions, facilities, agents, scores 모두 삭제
```

**dbdiagram.io 사용 팁**:
1. [dbdiagram.io](https://dbdiagram.io) 접속
2. 왼쪽 에디터에 위 DBML 코드 붙여넣기
3. 자동으로 ERD 생성됨
4. Export: PNG, PDF, SQL 등으로 내보내기 가능
5. Share: 링크로 공유 가능

---

## 테이블 상세 스키마

### 1. 사용자 관리

#### 1.1 users (사용자 계정)

**모델 파일**: [app/models/users.py:34-49](backend/app/models/users.py#L34-L49)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL UNIQUE,
    type VARCHAR(20) NOT NULL DEFAULT 'user',  -- UserType enum
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| id | INTEGER | PK | 사용자 고유 ID |
| email | VARCHAR(200) | NOT NULL, UNIQUE | 이메일 주소 |
| type | VARCHAR(20) | NOT NULL | 사용자 유형 (admin/user/agent) |
| is_active | BOOLEAN | DEFAULT TRUE | 계정 활성 상태 |
| created_at | TIMESTAMP | DEFAULT NOW() | 계정 생성일 |
| updated_at | TIMESTAMP | | 마지막 수정일 |

#### 1.2 user_profiles (사용자 프로필)

**모델 파일**: [app/models/users.py:64-78](backend/app/models/users.py#L64-L78)

```sql
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    nickname VARCHAR(20) NOT NULL UNIQUE,
    bio TEXT,
    gender VARCHAR(20) NOT NULL,  -- Gender enum
    birth_date VARCHAR(8) NOT NULL,  -- YYYYMMDD
    image_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE UNIQUE INDEX idx_user_profiles_nickname ON user_profiles(nickname);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| id | INTEGER | PK | 프로필 고유 ID |
| user_id | INTEGER | FK, UNIQUE | 사용자 ID (users.id) |
| nickname | VARCHAR(20) | NOT NULL, UNIQUE | 닉네임 |
| bio | TEXT | | 소개글 |
| gender | VARCHAR(20) | NOT NULL | 성별 (male/female/other) |
| birth_date | VARCHAR(8) | NOT NULL | 생년월일 (YYYYMMDD) |
| image_url | VARCHAR(500) | | 프로필 사진 URL |
| created_at | TIMESTAMP | DEFAULT NOW() | 생성일 |
| updated_at | TIMESTAMP | | 수정일 |

#### 1.3 local_auths (로컬 인증)

**모델 파일**: [app/models/users.py:52-61](backend/app/models/users.py#L52-L61)

```sql
CREATE TABLE local_auths (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| user_id | INTEGER | PK, FK | 사용자 ID (users.id) |
| hashed_password | VARCHAR(255) | NOT NULL | 암호화된 비밀번호 |
| created_at | TIMESTAMP | DEFAULT NOW() | 생성일 |
| updated_at | TIMESTAMP | | 수정일 |

#### 1.4 social_auths (소셜 로그인)

**모델 파일**: [app/models/users.py:80-96](backend/app/models/users.py#L80-L96)

```sql
CREATE TABLE social_auths (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,  -- SocialProvider enum
    provider_user_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE UNIQUE INDEX idx_provider_user ON social_auths(provider, provider_user_id);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| id | INTEGER | PK | 소셜 인증 고유 ID |
| user_id | INTEGER | FK | 사용자 ID (users.id) |
| provider | VARCHAR(20) | NOT NULL | 소셜 제공자 (google/kakao/naver/apple) |
| provider_user_id | VARCHAR(100) | NOT NULL | 제공자의 사용자 ID |
| created_at | TIMESTAMP | DEFAULT NOW() | 연동일 |
| updated_at | TIMESTAMP | | 수정일 |

#### 1.5 user_favorites (찜 목록)

**모델 파일**: [app/models/users.py:99-114](backend/app/models/users.py#L99-L114)

```sql
CREATE TABLE user_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    real_estate_id INTEGER NOT NULL REFERENCES real_estates(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_user_real_estate ON user_favorites(user_id, real_estate_id);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| id | INTEGER | PK | 찜 고유 ID |
| user_id | INTEGER | FK | 사용자 ID (users.id) |
| real_estate_id | INTEGER | FK | 부동산 ID (real_estates.id) |
| created_at | TIMESTAMP | DEFAULT NOW() | 찜한 날짜 |

---

### 2. 채팅 시스템

#### 2.1 chat_sessions (채팅 세션)

**모델 파일**: [app/models/chat.py:22-109](backend/app/models/chat.py#L22-L109)

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB  -- 메모리 저장 위치
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| session_id | VARCHAR(100) | PK | 세션 고유 식별자 |
| user_id | INTEGER | FK, NOT NULL | 사용자 ID (users.id) |
| title | VARCHAR(200) | NOT NULL | 세션 제목 |
| last_message | TEXT | | 마지막 메시지 미리보기 |
| message_count | INTEGER | DEFAULT 0 | 메시지 개수 |
| created_at | TIMESTAMP | DEFAULT NOW() | 생성일 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 마지막 활동일 |
| is_active | BOOLEAN | DEFAULT TRUE | 세션 활성 상태 |
| metadata | JSONB | | **3-Tier Memory 저장** (conversation_summary) |

**metadata JSONB 구조** ([상세 설명](#jsonb-필드-구조)):
```json
{
    "conversation_summary": "강남구 아파트 전세 시세 문의",
    "last_updated": "2025-10-20T14:30:15",
    "message_count": 12,
    "summary_method": "llm",
    "summary_updated_at": "2025-10-20T14:35:00"
}
```

#### 2.2 chat_messages (채팅 메시지)

**모델 파일**: [app/models/chat.py:112-154](backend/app/models/chat.py#L112-L154)

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    structured_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| id | INTEGER | PK | 메시지 고유 ID |
| session_id | VARCHAR(100) | FK, NOT NULL | 세션 ID (chat_sessions.session_id) |
| role | VARCHAR(20) | NOT NULL | 역할 (user/assistant/system) |
| content | TEXT | NOT NULL | 메시지 내용 |
| structured_data | JSONB | | 구조화된 답변 데이터 (sections, metadata) |
| created_at | TIMESTAMP | DEFAULT NOW() | 생성일 |

---

### 3. 부동산 정보

#### 3.1 regions (지역)

**모델 파일**: [app/models/real_estate.py:35-45](backend/app/models/real_estate.py#L35-L45)

```sql
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE UNIQUE INDEX idx_regions_code ON regions(code);
```

**컬럼 설명**:

| 컬럼 | 타입 | 제약 | 설명 |
|-----|------|-----|------|
| id | INTEGER | PK | 지역 고유 ID |
| code | VARCHAR(20) | NOT NULL, UNIQUE | 법정동코드 |
| name | VARCHAR(50) | NOT NULL | 지역명 |
| created_at | TIMESTAMP | DEFAULT NOW() | 생성일 |
| updated_at | TIMESTAMP | | 수정일 |

#### 3.2 real_estates (부동산 매물)

**모델 파일**: [app/models/real_estate.py:47-98](backend/app/models/real_estate.py#L47-L98)

```sql
CREATE TABLE real_estates (
    id SERIAL PRIMARY KEY,
    property_type VARCHAR(20) NOT NULL,  -- PropertyType enum
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    address VARCHAR(255) NOT NULL,
    address_detail VARCHAR(255),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),

    -- 건물 스펙
    total_households INTEGER,
    total_buildings INTEGER,
    completion_date VARCHAR(6),  -- YYYYMM
    min_exclusive_area FLOAT,
    max_exclusive_area FLOAT,
    representative_area FLOAT,
    floor_area_ratio FLOAT,

    -- 개별 매물 상세
    exclusive_area FLOAT,
    supply_area FLOAT,
    exclusive_area_pyeong FLOAT,
    supply_area_pyeong FLOAT,
    direction VARCHAR(20),
    floor_info VARCHAR(50),

    -- 설명
    building_description TEXT,
    tag_list VARCHAR[],  -- ARRAY

    -- 매물 통계
    deal_count INTEGER DEFAULT 0,
    lease_count INTEGER DEFAULT 0,
    rent_count INTEGER DEFAULT 0,
    short_term_rent_count INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE UNIQUE INDEX idx_real_estates_code ON real_estates(code);
CREATE INDEX idx_real_estates_region_id ON real_estates(region_id);
```

**주요 컬럼 설명**:

| 컬럼 | 타입 | 설명 |
|-----|------|------|
| property_type | VARCHAR(20) | 부동산 종류 (apartment/officetel/oneroom/villa/house) |
| code | VARCHAR(30) | 단지코드/매물코드 (고유) |
| name | VARCHAR(100) | 단지명/건물명 |
| region_id | INTEGER | 지역 ID (FK) |
| latitude/longitude | DECIMAL(10, 7) | 위도/경도 |
| exclusive_area | FLOAT | 전용면적 (㎡) |
| tag_list | VARCHAR[] | 태그 배열 |

#### 3.3 transactions (거래 내역)

**모델 파일**: [app/models/real_estate.py:100-143](backend/app/models/real_estate.py#L100-L143)

```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER NOT NULL REFERENCES real_estates(id) ON DELETE CASCADE,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20),  -- TransactionType enum
    transaction_date TIMESTAMP WITH TIME ZONE,

    -- 가격 정보 (개별 거래)
    sale_price INTEGER DEFAULT 0,
    deposit INTEGER DEFAULT 0,
    monthly_rent INTEGER DEFAULT 0,

    -- 가격 범위 (단지/건물 단위 통계)
    min_sale_price INTEGER DEFAULT 0,
    max_sale_price INTEGER DEFAULT 0,
    min_deposit INTEGER DEFAULT 0,
    max_deposit INTEGER DEFAULT 0,
    min_monthly_rent INTEGER DEFAULT 0,
    max_monthly_rent INTEGER DEFAULT 0,

    -- 매물 정보
    article_no VARCHAR(50) UNIQUE,
    article_confirm_ymd VARCHAR(10),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_transaction_date_type ON transactions(transaction_date, transaction_type);
CREATE INDEX idx_real_estate_date ON transactions(real_estate_id, transaction_date);
CREATE UNIQUE INDEX idx_article_no ON transactions(article_no);
```

**주요 컬럼 설명**:

| 컬럼 | 타입 | 설명 |
|-----|------|------|
| transaction_type | VARCHAR(20) | 거래 유형 (sale/jeonse/rent) |
| sale_price | INTEGER | 매매가 (만원) |
| deposit | INTEGER | 보증금 (만원) |
| monthly_rent | INTEGER | 월세 (만원) |
| article_no | VARCHAR(50) | 매물번호 (고유) |

---

### 4. 부가 정보

#### 4.1 nearby_facilities (주변 편의시설)

**모델 파일**: [app/models/real_estate.py:145-159](backend/app/models/real_estate.py#L145-L159)

```sql
CREATE TABLE nearby_facilities (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER REFERENCES real_estates(id) ON DELETE CASCADE,

    -- 지하철
    subway_line VARCHAR(50),
    subway_distance INTEGER,
    subway_walking_time INTEGER,

    -- 학교
    elementary_schools TEXT,
    middle_schools TEXT,
    high_schools TEXT
);
```

#### 4.2 real_estate_agents (중개사 정보)

**모델 파일**: [app/models/real_estate.py:161-175](backend/app/models/real_estate.py#L161-L175)

```sql
CREATE TABLE real_estate_agents (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER REFERENCES real_estates(id) ON DELETE CASCADE,
    agent_name VARCHAR(100),
    company_name VARCHAR(100),
    is_direct_trade BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### 4.3 trust_scores (신뢰도 점수)

**모델 파일**: [app/models/trust.py:6-17](backend/app/models/trust.py#L6-L17)

```sql
CREATE TABLE trust_scores (
    id SERIAL PRIMARY KEY,
    real_estate_id INTEGER NOT NULL REFERENCES real_estates(id) ON DELETE CASCADE,
    score DECIMAL(5, 2) NOT NULL,  -- 0-100
    verification_notes TEXT,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_trust_scores_real_estate_id ON trust_scores(real_estate_id);
```

---

### 5. LangGraph 시스템 (자동 생성)

#### 5.1 checkpoints

**용도**: LangGraph 워크플로우 상태 체크포인트 저장

```sql
CREATE TABLE checkpoints (
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

| 컬럼 | 타입 | 설명 |
|-----|------|------|
| thread_id | TEXT | 스레드 ID (chat_session_id) |
| checkpoint_ns | TEXT | 네임스페이스 |
| checkpoint_id | TEXT | 체크포인트 ID |
| parent_checkpoint_id | TEXT | 부모 체크포인트 ID |
| checkpoint | JSONB | 상태 스냅샷 |
| metadata | JSONB | 메타데이터 |

#### 5.2 checkpoint_blobs

**용도**: 큰 바이너리 데이터 저장

```sql
CREATE TABLE checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
```

#### 5.3 checkpoint_writes

**용도**: 체크포인트 쓰기 작업 추적

```sql
CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

---

## 인덱스 및 제약조건

### Primary Keys

| 테이블 | PK 컬럼 | 타입 |
|-------|---------|-----|
| users | id | SERIAL |
| user_profiles | id | SERIAL |
| local_auths | user_id | INTEGER |
| social_auths | id | SERIAL |
| user_favorites | id | SERIAL |
| **chat_sessions** | **session_id** | **VARCHAR(100)** |
| chat_messages | id | SERIAL |
| regions | id | SERIAL |
| real_estates | id | SERIAL |
| transactions | id | SERIAL |
| nearby_facilities | id | SERIAL |
| real_estate_agents | id | SERIAL |
| trust_scores | id | SERIAL |

### Unique Constraints

| 테이블 | 컬럼 | 설명 |
|-------|------|------|
| users | email | 이메일 중복 방지 |
| user_profiles | nickname | 닉네임 중복 방지 |
| user_profiles | user_id | 1:1 관계 보장 |
| regions | code | 법정동코드 고유 |
| real_estates | code | 단지코드 고유 |
| transactions | article_no | 매물번호 고유 |
| social_auths | (provider, provider_user_id) | 소셜 계정 중복 방지 |
| user_favorites | (user_id, real_estate_id) | 중복 찜 방지 |

### Foreign Keys

| 자식 테이블 | FK 컬럼 | 부모 테이블 | 삭제 규칙 |
|----------|---------|-----------|---------|
| user_profiles | user_id | users.id | CASCADE |
| local_auths | user_id | users.id | CASCADE |
| social_auths | user_id | users.id | CASCADE |
| user_favorites | user_id | users.id | CASCADE |
| user_favorites | real_estate_id | real_estates.id | CASCADE |
| chat_sessions | user_id | users.id | CASCADE |
| chat_messages | session_id | chat_sessions.session_id | CASCADE |
| real_estates | region_id | regions.id | CASCADE |
| transactions | real_estate_id | real_estates.id | CASCADE |
| transactions | region_id | regions.id | CASCADE |
| nearby_facilities | real_estate_id | real_estates.id | CASCADE |
| real_estate_agents | real_estate_id | real_estates.id | CASCADE |
| trust_scores | real_estate_id | real_estates.id | CASCADE |

### Indexes

#### chat_sessions 인덱스

```sql
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at);
```

**용도**:
- `user_id`: 사용자별 세션 조회
- `updated_at`: 최근 세션 정렬
- `(user_id, updated_at)`: **3-Tier Memory 로드** 최적화

#### transactions 인덱스

```sql
CREATE INDEX idx_transaction_date_type ON transactions(transaction_date, transaction_type);
CREATE INDEX idx_real_estate_date ON transactions(real_estate_id, transaction_date);
```

**용도**:
- 거래 날짜 및 타입별 검색
- 매물별 거래 이력 조회

---

## JSONB 필드 구조

### chat_sessions.metadata

**용도**: 3-Tier Hybrid Memory 저장

**저장 위치**: [simple_memory_service.py:335-390](backend/app/service_agent/foundation/simple_memory_service.py#L335-L390)

```json
{
    "conversation_summary": "강남구 아파트 전세 시세 문의 (5억~7억). 역삼동 위주로 조회.",
    "last_updated": "2025-10-20T14:30:15.123456",
    "message_count": 12,
    "summary_method": "llm",
    "summary_updated_at": "2025-10-20T14:35:00.789012"
}
```

**필드 설명**:

| 필드 | 타입 | 설명 |
|-----|------|------|
| conversation_summary | string | LLM 생성 대화 요약 (최대 200자) |
| last_updated | string (ISO 8601) | 마지막 업데이트 시간 |
| message_count | integer | 세션 내 메시지 개수 |
| summary_method | string | 요약 생성 방법 ("llm" or "manual") |
| summary_updated_at | string (ISO 8601) | 요약 생성 시간 |

**조회 쿼리 예시**:

```sql
-- conversation_summary 추출
SELECT
    session_id,
    metadata->>'conversation_summary' as summary
FROM chat_sessions
WHERE user_id = 1
ORDER BY updated_at DESC
LIMIT 5;

-- summary 존재 여부 확인
SELECT COUNT(*)
FROM chat_sessions
WHERE metadata ? 'conversation_summary';

-- summary가 특정 키워드 포함
SELECT session_id
FROM chat_sessions
WHERE metadata->>'conversation_summary' LIKE '%전세%';
```

### chat_messages.structured_data

**용도**: 구조화된 답변 데이터 저장

```json
{
    "sections": [
        {
            "title": "검색 결과",
            "content": "강남구 아파트 전세 시세는...",
            "type": "search_result"
        },
        {
            "title": "분석 결과",
            "content": "평균 가격은...",
            "type": "analysis"
        }
    ],
    "metadata": {
        "execution_time": 2.5,
        "teams_executed": ["search", "analysis"]
    }
}
```

---

## 관계 (Relationships)

### 1:1 관계

| 부모 | 자식 | 설명 |
|-----|------|------|
| users | user_profiles | 사용자 - 프로필 |
| users | local_auths | 사용자 - 로컬 인증 |
| real_estates | nearby_facilities | 부동산 - 편의시설 |
| real_estates | trust_scores | 부동산 - 신뢰도 |

### 1:N 관계

| 1 (부모) | N (자식) | 설명 |
|---------|---------|------|
| users | social_auths | 사용자 - 소셜 계정 (여러 개 가능) |
| users | user_favorites | 사용자 - 찜 목록 |
| users | chat_sessions | 사용자 - 채팅 세션 |
| chat_sessions | chat_messages | 세션 - 메시지 |
| regions | real_estates | 지역 - 부동산 |
| regions | transactions | 지역 - 거래 |
| real_estates | transactions | 부동산 - 거래 |
| real_estates | user_favorites | 부동산 - 찜 (여러 사용자) |
| real_estates | real_estate_agents | 부동산 - 중개사 |

### Cascade 삭제 흐름

```
users 삭제
  ├─→ user_profiles 삭제
  ├─→ local_auths 삭제
  ├─→ social_auths 삭제 (모든 연동 계정)
  ├─→ user_favorites 삭제 (모든 찜)
  └─→ chat_sessions 삭제
       └─→ chat_messages 삭제 (모든 메시지)

real_estates 삭제
  ├─→ transactions 삭제
  ├─→ user_favorites 삭제
  ├─→ nearby_facilities 삭제
  ├─→ real_estate_agents 삭제
  └─→ trust_scores 삭제
```

---

## Enum 타입

### UserType

**파일**: [app/models/users.py:18-21](backend/app/models/users.py#L18-L21)

```python
class UserType(enum.Enum):
    ADMIN = "admin"    # 관리자
    USER = "user"      # 일반 사용자
    AGENT = "agent"    # 중개사
```

### Gender

**파일**: [app/models/users.py:23-26](backend/app/models/users.py#L23-L26)

```python
class Gender(enum.Enum):
    MALE = "male"      # 남성
    FEMALE = "female"  # 여성
    OTHER = "other"    # 기타
```

### SocialProvider

**파일**: [app/models/users.py:28-32](backend/app/models/users.py#L28-L32)

```python
class SocialProvider(enum.Enum):
    GOOGLE = "google"  # 구글
    KAKAO = "kakao"    # 카카오
    NAVER = "naver"    # 네이버
    APPLE = "apple"    # 애플
```

### PropertyType

**파일**: [app/models/real_estate.py:22-27](backend/app/models/real_estate.py#L22-L27)

```python
class PropertyType(enum.Enum):
    APARTMENT = "apartment"  # 아파트
    OFFICETEL = "officetel"  # 오피스텔
    ONEROOM = "oneroom"      # 원룸
    VILLA = "villa"          # 빌라
    HOUSE = "house"          # 단독/다가구
```

### TransactionType

**파일**: [app/models/real_estate.py:29-33](backend/app/models/real_estate.py#L29-L33)

```python
class TransactionType(enum.Enum):
    SALE = "sale"        # 매매
    JEONSE = "jeonse"    # 전세
    RENT = "rent"        # 월세
```

---

## 데이터베이스 생성 스크립트

### 전체 스키마 생성

```sql
-- 1. Enum 타입 생성 (PostgreSQL)
CREATE TYPE user_type AS ENUM ('admin', 'user', 'agent');
CREATE TYPE gender AS ENUM ('male', 'female', 'other');
CREATE TYPE social_provider AS ENUM ('google', 'kakao', 'naver', 'apple');
CREATE TYPE property_type AS ENUM ('apartment', 'officetel', 'oneroom', 'villa', 'house');
CREATE TYPE transaction_type AS ENUM ('sale', 'jeonse', 'rent');

-- 2. 사용자 테이블
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL UNIQUE,
    type user_type NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 3. 나머지 테이블들...
-- (상세 스키마는 위 섹션 참조)
```

### SQLAlchemy로 자동 생성

```python
from app.db.postgre_db import Base, engine
from app.models import users, chat, real_estate, trust

# 모든 테이블 생성
Base.metadata.create_all(bind=engine)
```

---

## 마이그레이션

### Alembic 마이그레이션 (권장)

```bash
# 마이그레이션 초기화
alembic init alembic

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial schema"

# 마이그레이션 적용
alembic upgrade head
```

---

## 보안 고려사항

### 1. 비밀번호 저장

- **절대 평문 저장 금지**
- bcrypt/argon2 등 암호화 알고리즘 사용
- `local_auths.hashed_password`: 해시 저장

### 2. JSONB 필드

- 민감 정보 저장 금지 (비밀번호, 카드번호 등)
- 사용자 입력 검증 필수
- SQL Injection 방지

### 3. Cascade 삭제

- `ON DELETE CASCADE` 신중히 사용
- 데이터 손실 위험 인지
- 백업 정책 수립

---

## 쿼리 예시

### 사용자별 최근 채팅 세션 조회

```sql
SELECT
    cs.session_id,
    cs.title,
    cs.message_count,
    cs.metadata->>'conversation_summary' as summary,
    cs.updated_at
FROM chat_sessions cs
WHERE cs.user_id = 1
ORDER BY cs.updated_at DESC
LIMIT 10;
```

### 3-Tier Memory 로드 쿼리

```sql
-- Short-term (1-5 세션): 전체 메시지 포함
SELECT
    cs.session_id,
    cs.updated_at,
    cs.metadata,
    json_agg(
        json_build_object(
            'role', cm.role,
            'content', cm.content,
            'timestamp', cm.created_at
        ) ORDER BY cm.created_at
    ) as messages
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
WHERE cs.user_id = 1
  AND cs.session_id != 'current-session-id'  -- 현재 세션 제외
GROUP BY cs.session_id, cs.updated_at, cs.metadata
ORDER BY cs.updated_at DESC
LIMIT 5;
```

### 부동산 검색 (지역 + 가격 범위)

```sql
SELECT
    re.id,
    re.name,
    re.address,
    r.name as region_name,
    t.deposit,
    t.monthly_rent
FROM real_estates re
JOIN regions r ON re.region_id = r.id
JOIN transactions t ON re.id = t.real_estate_id
WHERE r.name LIKE '%강남%'
  AND t.transaction_type = 'jeonse'
  AND t.deposit BETWEEN 50000 AND 70000  -- 5억~7억
ORDER BY t.transaction_date DESC;
```

---

## 참고 자료

- **모델 파일 위치**: `backend/app/models/`
- **메모리 서비스**: [simple_memory_service.py](backend/app/service_agent/foundation/simple_memory_service.py)
- **데이터베이스 연결**: [postgre_db.py](backend/app/db/postgre_db.py)
- **환경변수**: [.env](backend/.env)

---

**문서 작성 완료**
**작성일**: 2025-11-02
**작성자**: Claude Code
