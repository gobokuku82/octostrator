# 📊 데이터베이스 스키마 상세 문서

> PostgreSQL 데이터베이스의 모든 테이블, 관계, 인덱스, 제약조건에 대한 완전한 문서

---

## 📋 목차

1. [개요](#개요)
2. [ERD (Entity Relationship Diagram)](#erd-entity-relationship-diagram)
3. [테이블 상세](#테이블-상세)
4. [관계 (Relationships)](#관계-relationships)
5. [인덱스 (Indexes)](#인덱스-indexes)
6. [Enum 타입](#enum-타입)
7. [제약조건 (Constraints)](#제약조건-constraints)
8. [사용 예시](#사용-예시)

---

## 개요

### 데이터베이스 정보
- **이름**: `real_estate`
- **DBMS**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.0+
- **드라이버**: pg8000 (Pure Python)

### 통계 (2025-10-13 기준)
- **총 테이블**: 9개
- **총 매물**: 9,738개
- **총 거래**: 10,772개
- **총 지역**: 46개

### 테이블 목록
1. `regions` - 지역 정보
2. `real_estates` - 부동산 매물
3. `transactions` - 거래/가격 정보
4. `nearby_facilities` - 주변 편의시설
5. `real_estate_agents` - 중개사 정보
6. `trust_scores` - 신뢰도 점수
7. `users` - 사용자
8. `user_profiles` - 사용자 프로필
9. `local_auths` - 로컬 인증
10. `social_auths` - 소셜 인증
11. `user_favorites` - 사용자 찜
12. `chat_sessions` - 채팅 세션
13. `chat_messages` - 채팅 메시지

---

## ERD (Entity Relationship Diagram)

### 텍스트 기반 ERD

```
┌─────────────────┐
│    regions      │
│─────────────────│
│ id (PK)         │
│ code (UQ)       │◀───┐
│ name            │    │
└─────────────────┘    │
                       │ 1
                       │
                       │ N
┌──────────────────────┴────────────────────────────┐
│             real_estates                          │
│───────────────────────────────────────────────────│
│ id (PK)                                           │
│ property_type (Enum)                              │
│ code (UQ)                                         │
│ name                                              │
│ region_id (FK) ───────────────────────────────────┘
│ address, latitude, longitude                      │
│ total_households, completion_date                 │
│ exclusive_area, supply_area                       │
│ building_description, tag_list                    │
└───────────────────────────────────────────────────┘
         │                    │                │
         │ 1                  │ 1              │ 1
         │                    │                │
         │ N                  │ 1              │ 1
         ▼                    ▼                ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  transactions   │  │nearby_facilities │  │real_estate_     │
│─────────────────│  │──────────────────│  │   agents        │
│ id (PK)         │  │ id (PK)          │  │─────────────────│
│ real_estate_id  │  │ real_estate_id   │  │ id (PK)         │
│ region_id (FK)  │  │ subway_line      │  │ real_estate_id  │
│ transaction_type│  │ subway_distance  │  │ agent_name      │
│ sale_price      │  │ schools          │  │ company_name    │
│ deposit         │  └──────────────────┘  └─────────────────┘
│ monthly_rent    │
└─────────────────┘
         │ 1
         │
         │ N
         ▼
┌─────────────────┐
│  trust_scores   │
│─────────────────│
│ id (PK)         │
│ real_estate_id  │
│ score           │
│ verification_   │
│   notes         │
└─────────────────┘


┌─────────────────────────────────────────────────┐
│                   users                         │
│─────────────────────────────────────────────────│
│ id (PK)                                         │
│ email (UQ)                                      │
│ type (Enum: admin/user/agent)                   │
│ is_active                                       │
└─────────────────────────────────────────────────┘
    │              │               │              │
    │ 1            │ 1             │ 1            │ 1
    │              │               │              │
    │ 1            │ N             │ N            │ N
    ▼              ▼               ▼              ▼
┌────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│user_       │ │social_auths │ │user_        │ │chat_        │
│ profiles   │ │─────────────│ │ favorites   │ │ sessions    │
│────────────│ │ id (PK)     │ │─────────────│ │─────────────│
│ user_id    │ │ user_id     │ │ user_id     │ │ id (PK,UUID)│
│ nickname   │ │ provider    │ │ real_estate │ │ user_id     │
│ gender     │ │ provider_   │ │   _id       │ │ title       │
│ birth_date │ │   user_id   │ └─────────────┘ └─────────────┘
└────────────┘ └─────────────┘                          │
    │ 1                                                 │ 1
    │                                                   │
    │ 1                                                 │ N
    ▼                                                   ▼
┌────────────┐                              ┌──────────────────┐
│local_auths │                              │  chat_messages   │
│────────────│                              │──────────────────│
│ user_id(PK)│                              │ id (PK, UUID)    │
│ hashed_    │                              │ session_id (FK)  │
│  password  │                              │ sender_type      │
└────────────┘                              │ content          │
                                            └──────────────────┘
```

---

## 테이블 상세

### 1. regions (지역)

**용도**: 법정동 기준 지역 정보 저장

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 지역 ID |
| code | VARCHAR(20) | UNIQUE, NOT NULL, INDEX | 법정동코드 |
| name | VARCHAR(50) | NOT NULL | 지역명 (예: "강남구", "서초구") |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**코드 위치**: `app/models/real_estate.py:35-45`

**사용 예시**:
```python
from app.models.real_estate import Region

# 강남구 조회
gangnam = db.query(Region).filter(Region.name.contains("강남구")).first()
print(f"지역코드: {gangnam.code}, 매물 수: {len(gangnam.real_estates)}")
```

---

### 2. real_estates (부동산 매물)

**용도**: 모든 부동산 매물의 물리적 정보 저장 (핵심 테이블)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 매물 ID |
| property_type | ENUM | NOT NULL | 부동산 종류 (apartment/officetel/villa/oneroom/house) |
| code | VARCHAR(30) | UNIQUE, NOT NULL, INDEX | 단지코드/매물코드 |
| name | VARCHAR(100) | NOT NULL | 단지명/건물명 |
| region_id | INTEGER | FOREIGN KEY → regions.id, NOT NULL | 지역 ID |
| address | VARCHAR(255) | NOT NULL | 도로명주소 |
| address_detail | VARCHAR(255) | NULL | 상세주소 |
| latitude | DECIMAL(10,7) | NULL | 위도 |
| longitude | DECIMAL(10,7) | NULL | 경도 |
| total_households | INTEGER | NULL | 총 세대수 |
| total_buildings | INTEGER | NULL | 총 동수 |
| completion_date | VARCHAR(6) | NULL | 준공년월 (YYYYMM) |
| min_exclusive_area | FLOAT | NULL | 최소 전용면적(㎡) |
| max_exclusive_area | FLOAT | NULL | 최대 전용면적(㎡) |
| representative_area | FLOAT | NULL | 대표 전용면적(㎡) |
| floor_area_ratio | FLOAT | NULL | 용적률(%) |
| exclusive_area | FLOAT | NULL | 개별 매물 전용면적(㎡) |
| supply_area | FLOAT | NULL | 개별 매물 공급면적(㎡) |
| exclusive_area_pyeong | FLOAT | NULL | 전용면적(평) |
| supply_area_pyeong | FLOAT | NULL | 공급면적(평) |
| direction | VARCHAR(20) | NULL | 방향 (남향, 동남향 등) |
| floor_info | VARCHAR(50) | NULL | 층 정보 |
| building_description | TEXT | NULL | 건물 설명 |
| tag_list | ARRAY(VARCHAR) | NULL | 태그 리스트 |
| deal_count | INTEGER | DEFAULT 0 | 매매 매물 수 |
| lease_count | INTEGER | DEFAULT 0 | 전세 매물 수 |
| rent_count | INTEGER | DEFAULT 0 | 월세 매물 수 |
| short_term_rent_count | INTEGER | DEFAULT 0 | 단기임대 매물 수 |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**코드 위치**: `app/models/real_estate.py:47-98`

**사용 예시**:
```python
from app.models.real_estate import RealEstate, PropertyType

# 강남구 아파트 조회
apartments = db.query(RealEstate).join(Region).filter(
    Region.name.contains("강남구"),
    RealEstate.property_type == PropertyType.APARTMENT
).limit(10).all()

for apt in apartments:
    print(f"{apt.name} - {apt.address}")
    print(f"  전용면적: {apt.min_exclusive_area}~{apt.max_exclusive_area}㎡")
    print(f"  준공: {apt.completion_date}")
```

---

### 3. transactions (거래/가격 정보)

**용도**: 실거래 내역 및 가격 정보 저장

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 거래 ID |
| real_estate_id | INTEGER | FOREIGN KEY → real_estates.id, NOT NULL | 부동산 ID |
| region_id | INTEGER | FOREIGN KEY → regions.id, NOT NULL | 지역 ID |
| transaction_type | ENUM | NULL | 거래 유형 (sale/jeonse/rent) |
| transaction_date | TIMESTAMP | INDEX | 거래일 |
| sale_price | INTEGER | DEFAULT 0 | 매매가(만원) |
| deposit | INTEGER | DEFAULT 0 | 보증금(만원) |
| monthly_rent | INTEGER | DEFAULT 0 | 월세(만원) |
| min_sale_price | INTEGER | DEFAULT 0 | 최소 매매가(만원) |
| max_sale_price | INTEGER | DEFAULT 0 | 최대 매매가(만원) |
| min_deposit | INTEGER | DEFAULT 0 | 최소 보증금(만원) |
| max_deposit | INTEGER | DEFAULT 0 | 최대 보증금(만원) |
| min_monthly_rent | INTEGER | DEFAULT 0 | 최소 월세(만원) |
| max_monthly_rent | INTEGER | DEFAULT 0 | 최대 월세(만원) |
| article_no | VARCHAR(50) | UNIQUE, INDEX | 매물번호 |
| article_confirm_ymd | VARCHAR(10) | NULL | 매물확인일자 |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**복합 인덱스**:
- `idx_transaction_date_type` (transaction_date, transaction_type)
- `idx_real_estate_date` (real_estate_id, transaction_date)

**코드 위치**: `app/models/real_estate.py:100-143`

**사용 예시**:
```python
from app.models.real_estate import Transaction, TransactionType

# 1억 이하 매매 거래
cheap_sales = db.query(Transaction).filter(
    Transaction.transaction_type == TransactionType.SALE,
    Transaction.sale_price <= 10000
).all()

# 특정 아파트의 거래 내역
apt_transactions = db.query(Transaction).filter(
    Transaction.real_estate_id == 1
).order_by(Transaction.transaction_date.desc()).all()
```

---

### 4. nearby_facilities (주변 편의시설)

**용도**: 부동산 주변의 교통, 교육 시설 정보

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 시설 ID |
| real_estate_id | INTEGER | FOREIGN KEY → real_estates.id | 부동산 ID |
| subway_line | VARCHAR(50) | NULL | 지하철 노선 |
| subway_distance | INTEGER | NULL | 지하철까지 거리(m) |
| subway_walking_time | INTEGER | NULL | 지하철 도보 시간(분) |
| elementary_schools | TEXT | NULL | 초등학교 목록 (콤마 구분) |
| middle_schools | TEXT | NULL | 중학교 목록 (콤마 구분) |
| high_schools | TEXT | NULL | 고등학교 목록 (콤마 구분) |

**코드 위치**: `app/models/real_estate.py:145-159`

**사용 예시**:
```python
# 지하철역 가까운 매물
near_subway = db.query(RealEstate).join(NearbyFacility).filter(
    NearbyFacility.subway_walking_time <= 5
).all()
```

---

### 5. real_estate_agents (중개사 정보)

**용도**: 부동산 중개사/담당자 정보

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 중개사 ID |
| real_estate_id | INTEGER | FOREIGN KEY → real_estates.id | 부동산 ID |
| agent_name | VARCHAR(100) | NULL | 중개사명 |
| company_name | VARCHAR(100) | NULL | 메인 중개사명 |
| is_direct_trade | BOOLEAN | DEFAULT FALSE | 직거래 유무 |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**코드 위치**: `app/models/real_estate.py:161-174`

---

### 6. trust_scores (신뢰도 점수)

**용도**: 부동산 매물의 신뢰도 평가

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 점수 ID |
| real_estate_id | INTEGER | FOREIGN KEY → real_estates.id, NOT NULL, INDEX | 부동산 ID |
| score | DECIMAL(5,2) | NOT NULL | 신뢰점수 (0-100) |
| verification_notes | TEXT | NULL | 검증 내용 |
| calculated_at | TIMESTAMP | DEFAULT now() | 계산일자 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**코드 위치**: `app/models/trust.py:6-17`

---

### 7. users (사용자)

**용도**: 통합 사용자 정보

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 사용자 ID |
| email | VARCHAR(200) | UNIQUE, NOT NULL, INDEX | 이메일 |
| type | ENUM | NOT NULL, DEFAULT 'user' | 유저 타입 (admin/user/agent) |
| is_active | BOOLEAN | DEFAULT TRUE | 계정 활성화 여부 |
| created_at | TIMESTAMP | DEFAULT now() | 계정 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 계정 수정일 |

**코드 위치**: `app/models/users.py:34-49`

---

### 8. user_profiles (사용자 프로필)

**용도**: 사용자 상세 프로필 정보

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 프로필 ID |
| user_id | INTEGER | FOREIGN KEY → users.id, UNIQUE, NOT NULL | 사용자 ID |
| nickname | VARCHAR(20) | UNIQUE, NOT NULL | 닉네임 |
| bio | TEXT | NULL | 소개글 |
| gender | ENUM | NOT NULL | 성별 (male/female/other) |
| birth_date | VARCHAR(8) | NOT NULL | 생년월일 (YYYYMMDD) |
| image_url | VARCHAR(500) | NULL | 프로필 사진 URL |
| created_at | TIMESTAMP | DEFAULT now() | 프로필 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 프로필 수정일 |

**코드 위치**: `app/models/users.py:64-78`

---

### 9. local_auths (로컬 인증)

**용도**: 이메일/비밀번호 기반 인증 정보

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| user_id | INTEGER | PRIMARY KEY, FOREIGN KEY → users.id | 사용자 ID |
| hashed_password | VARCHAR(255) | NOT NULL | 암호화된 비밀번호 |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**코드 위치**: `app/models/users.py:52-61`

---

### 10. social_auths (소셜 인증)

**용도**: 소셜 로그인 연동 정보 (한 유저가 여러 소셜 계정 연동 가능)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 인증 ID |
| user_id | INTEGER | FOREIGN KEY → users.id, NOT NULL | 사용자 ID |
| provider | ENUM | NOT NULL | 소셜 제공자 (google/kakao/naver/apple) |
| provider_user_id | VARCHAR(100) | NOT NULL | 소셜 제공자의 사용자 ID |
| created_at | TIMESTAMP | DEFAULT now() | 연동일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**복합 인덱스**:
- `idx_provider_user` (provider, provider_user_id) - UNIQUE

**코드 위치**: `app/models/users.py:80-96`

---

### 11. user_favorites (사용자 찜)

**용도**: 사용자가 찜한 부동산 목록

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PRIMARY KEY, AUTO INCREMENT | 찜 ID |
| user_id | INTEGER | FOREIGN KEY → users.id, NOT NULL | 사용자 ID |
| real_estate_id | INTEGER | FOREIGN KEY → real_estates.id, NOT NULL | 부동산 ID |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |

**복합 인덱스**:
- `idx_user_real_estate` (user_id, real_estate_id) - UNIQUE

**코드 위치**: `app/models/users.py:99-114`

---

### 12. chat_sessions (채팅 세션)

**용도**: 사용자별 채팅 세션

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | UUID | PRIMARY KEY | 세션 ID |
| user_id | INTEGER | FOREIGN KEY → users.id, NOT NULL, INDEX | 사용자 ID |
| title | VARCHAR(20) | NOT NULL | 채팅 세션 제목 |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |
| updated_at | TIMESTAMP | ON UPDATE now() | 수정일 |

**코드 위치**: `app/models/chat.py:16-27`

---

### 13. chat_messages (채팅 메시지)

**용도**: 채팅 세션별 메시지 저장

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | UUID | PRIMARY KEY | 메시지 ID |
| session_id | UUID | FOREIGN KEY → chat_sessions.id (CASCADE), NOT NULL, INDEX | 세션 ID |
| sender_type | VARCHAR(20) | NOT NULL | 발신자 타입 (user/assistant) |
| content | TEXT | NOT NULL | 메시지 내용 |
| created_at | TIMESTAMP | DEFAULT now() | 생성일 |

**코드 위치**: `app/models/chat.py:29-39`

---

## 관계 (Relationships)

### 1:N 관계

| 부모 (1) | 자식 (N) | 설명 |
|----------|----------|------|
| Region | RealEstate | 한 지역에 여러 부동산 |
| Region | Transaction | 한 지역에 여러 거래 |
| RealEstate | Transaction | 한 부동산에 여러 거래 |
| User | UserFavorite | 한 유저가 여러 부동산 찜 |
| User | SocialAuth | 한 유저가 여러 소셜 계정 연동 |
| User | ChatSession | 한 유저가 여러 채팅 세션 |
| ChatSession | ChatMessage | 한 세션에 여러 메시지 |

### 1:1 관계

| 테이블 A | 테이블 B | 설명 |
|----------|----------|------|
| User | UserProfile | 유저-프로필 (1:1) |
| User | LocalAuth | 유저-로컬인증 (1:1) |
| RealEstate | NearbyFacility | 부동산-주변시설 (1:1) |
| RealEstate | RealEstateAgent | 부동산-중개사 (1:1) |
| RealEstate | TrustScore | 부동산-신뢰점수 (1:1) |

### N:M 관계 (중간 테이블 사용)

| 테이블 A | 중간 테이블 | 테이블 B | 설명 |
|----------|-------------|----------|------|
| User | UserFavorite | RealEstate | 유저 ↔ 부동산 찜 (N:M) |

### SQLAlchemy Relationship 예시

```python
# 1:N 관계 (Region → RealEstate)
class Region(Base):
    real_estates = relationship("RealEstate", back_populates="region")

class RealEstate(Base):
    region_id = Column(Integer, ForeignKey("regions.id"))
    region = relationship("Region", back_populates="real_estates")

# 사용
region = db.query(Region).first()
for re in region.real_estates:  # 이 지역의 모든 부동산
    print(re.name)

# 1:1 관계 (User → UserProfile)
class User(Base):
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    user = relationship("User", back_populates="profile")

# 사용
user = db.query(User).first()
print(user.profile.nickname)  # uselist=False라서 단일 객체

# N:M 관계 (User ↔ RealEstate via UserFavorite)
class User(Base):
    favorites = relationship("UserFavorite", back_populates="user")

class UserFavorite(Base):
    user_id = Column(Integer, ForeignKey("users.id"))
    real_estate_id = Column(Integer, ForeignKey("real_estates.id"))
    user = relationship("User", back_populates="favorites")
    real_estate = relationship("RealEstate", back_populates="favorites")

# 사용
user = db.query(User).first()
for fav in user.favorites:
    print(fav.real_estate.name)  # 찜한 부동산 목록
```

---

## 인덱스 (Indexes)

### 단일 컬럼 인덱스

| 테이블 | 컬럼 | 타입 | 목적 |
|--------|------|------|------|
| regions | id | PRIMARY KEY | 기본키 |
| regions | code | UNIQUE | 법정동코드 중복 방지 + 빠른 검색 |
| real_estates | id | PRIMARY KEY | 기본키 |
| real_estates | code | UNIQUE | 매물코드 중복 방지 + 빠른 검색 |
| real_estates | region_id | FOREIGN KEY | JOIN 최적화 |
| transactions | id | PRIMARY KEY | 기본키 |
| transactions | article_no | UNIQUE | 매물번호 중복 방지 |
| transactions | transaction_date | INDEX | 날짜 기반 검색 최적화 |
| users | id | PRIMARY KEY | 기본키 |
| users | email | UNIQUE | 이메일 중복 방지 + 로그인 빠름 |
| user_profiles | nickname | UNIQUE | 닉네임 중복 방지 |
| chat_sessions | user_id | INDEX | 유저별 채팅 조회 최적화 |

### 복합 인덱스

| 테이블 | 인덱스명 | 컬럼들 | 타입 | 목적 |
|--------|----------|--------|------|------|
| transactions | idx_transaction_date_type | (transaction_date, transaction_type) | INDEX | "최근 매매 거래" 같은 쿼리 최적화 |
| transactions | idx_real_estate_date | (real_estate_id, transaction_date) | INDEX | 특정 부동산의 거래 히스토리 조회 |
| social_auths | idx_provider_user | (provider, provider_user_id) | UNIQUE | 소셜 로그인 중복 방지 (카카오+123 같은) |
| user_favorites | idx_user_real_estate | (user_id, real_estate_id) | UNIQUE | 찜 중복 방지 |

### 인덱스 확인 쿼리

```sql
-- PostgreSQL에서 인덱스 확인
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

---

## Enum 타입

### PropertyType (부동산 종류)
```python
class PropertyType(enum.Enum):
    APARTMENT = "apartment"   # 아파트
    OFFICETEL = "officetel"   # 오피스텔
    ONEROOM = "oneroom"       # 원룸
    VILLA = "villa"           # 빌라
    HOUSE = "house"           # 단독/다가구
```

### TransactionType (거래 유형)
```python
class TransactionType(enum.Enum):
    SALE = "sale"       # 매매
    JEONSE = "jeonse"   # 전세
    RENT = "rent"       # 월세
```

### UserType (사용자 타입)
```python
class UserType(enum.Enum):
    ADMIN = "admin"   # 관리자
    USER = "user"     # 일반 사용자
    AGENT = "agent"   # 중개사
```

### Gender (성별)
```python
class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
```

### SocialProvider (소셜 로그인 제공자)
```python
class SocialProvider(enum.Enum):
    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"
    APPLE = "apple"
```

---

## 제약조건 (Constraints)

### PRIMARY KEY
모든 테이블의 `id` 컬럼 (chat_sessions, chat_messages는 UUID)

### FOREIGN KEY
- `real_estates.region_id` → `regions.id`
- `transactions.real_estate_id` → `real_estates.id`
- `transactions.region_id` → `regions.id`
- `nearby_facilities.real_estate_id` → `real_estates.id`
- `real_estate_agents.real_estate_id` → `real_estates.id`
- `trust_scores.real_estate_id` → `real_estates.id`
- `user_profiles.user_id` → `users.id`
- `local_auths.user_id` → `users.id`
- `social_auths.user_id` → `users.id`
- `user_favorites.user_id` → `users.id`
- `user_favorites.real_estate_id` → `real_estates.id`
- `chat_sessions.user_id` → `users.id`
- `chat_messages.session_id` → `chat_sessions.id` (ON DELETE CASCADE)

### UNIQUE
- `regions.code`
- `real_estates.code`
- `transactions.article_no`
- `users.email`
- `user_profiles.user_id`
- `user_profiles.nickname`
- `(social_auths.provider, social_auths.provider_user_id)` - 복합
- `(user_favorites.user_id, user_favorites.real_estate_id)` - 복합

### NOT NULL (주요 필드)
- `real_estates.name`
- `real_estates.address`
- `real_estates.region_id`
- `users.email`
- `user_profiles.nickname`
- `chat_messages.content`

### DEFAULT 값
- 모든 `created_at`: `now()`
- `users.type`: `'user'`
- `users.is_active`: `true`
- `real_estate_agents.is_direct_trade`: `false`
- 가격 관련 필드: `0`

### CHECK 제약조건 (Pydantic 스키마에서)
- `user_profiles.birth_date`: YYYYMMDD 형식
- `real_estates.completion_date`: YYYYMM 형식
- `chat_messages.sender_type`: 'user' 또는 'assistant'

---

## 사용 예시

### 1. 기본 조회

```python
from app.db.postgre_db import SessionLocal
from app.models.real_estate import RealEstate, Region

db = SessionLocal()

# 모든 아파트
apartments = db.query(RealEstate).filter(
    RealEstate.property_type == PropertyType.APARTMENT
).all()

# 특정 지역의 부동산
gangnam_estates = db.query(RealEstate).join(Region).filter(
    Region.name.contains("강남구")
).all()

db.close()
```

### 2. 복잡한 검색

```python
# 강남구, 3억 이하, 아파트
results = db.query(RealEstate).join(Region).join(Transaction).filter(
    Region.name.contains("강남구"),
    RealEstate.property_type == PropertyType.APARTMENT,
    Transaction.sale_price <= 30000
).distinct().all()
```

### 3. 관계 활용

```python
# 지역 → 부동산 → 거래
region = db.query(Region).filter(Region.name == "강남구").first()
for estate in region.real_estates:
    print(f"{estate.name}: {len(estate.transactions)}개 거래")

# 부동산 → 주변시설
estate = db.query(RealEstate).first()
if estate.nearby_facility:
    print(f"지하철: {estate.nearby_facility.subway_line}")
```

### 4. Eager Loading (N+1 문제 방지)

```python
from sqlalchemy.orm import joinedload

# 한 번에 관련 데이터 모두 로드
estates = db.query(RealEstate).options(
    joinedload(RealEstate.region),
    joinedload(RealEstate.transactions),
    joinedload(RealEstate.nearby_facility)
).limit(10).all()

# 추가 쿼리 없이 접근 가능
for estate in estates:
    print(estate.region.name)  # 추가 쿼리 없음
    print(len(estate.transactions))  # 추가 쿼리 없음
```

### 5. 집계 쿼리

```python
from sqlalchemy import func

# 지역별 부동산 수
region_counts = db.query(
    Region.name,
    func.count(RealEstate.id).label('count')
).join(RealEstate).group_by(Region.name).all()

for region, count in region_counts:
    print(f"{region}: {count}개")
```

---

## 성능 최적화 팁

### 1. 인덱스 활용
```python
# 좋음: 인덱스 사용 (code)
estate = db.query(RealEstate).filter(RealEstate.code == "A001").first()

# 나쁨: Full table scan
estate = db.query(RealEstate).filter(RealEstate.building_description.contains("좋은")).first()
```

### 2. 조인 최소화
```python
# 좋음: 필요한 컬럼만
names = db.query(RealEstate.name).filter(...).all()

# 나쁨: 모든 컬럼
estates = db.query(RealEstate).filter(...).all()
```

### 3. Pagination
```python
# 항상 limit 사용
results = db.query(RealEstate).limit(10).offset(0).all()
```

---

**마지막 업데이트**: 2025-10-13
**버전**: 1.0.0
