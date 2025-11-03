# 데이터베이스 구축 가이드

**프로젝트**: HolmesNyangz Beta v0.01
**작성일**: 2025-10-14
**목적**: 다른 개발자가 동일한 데이터베이스를 구축할 수 있도록 전체 프로세스 문서화

---

## 📋 목차

1. [전체 프로세스 개요](#전체-프로세스-개요)
2. [필수 파일 목록](#필수-파일-목록)
3. [Step-by-Step 가이드](#step-by-step-가이드)
4. [데이터 검증](#데이터-검증)
5. [트러블슈팅](#트러블슈팅)

---

## 전체 프로세스 개요

```
원본 CSV 데이터 (3개 파일)
    ↓
1. init_db.py (테이블 생성)
    ↓
2. import_*.py (데이터 삽입 - 4개 스크립트)
    ↓
3. generate_trust_scores.py (신뢰도 점수 계산)
    ↓
PostgreSQL 데이터베이스 완성 (9,738개 매물)
```

**소요 시간**: 약 10-15분

---

## 필수 파일 목록

### 1. 원본 데이터 파일 (CSV)

**위치**: `backend/data/real_estate/`

| 파일명 | 크기 | 내용 | 매물 수 |
|--------|------|------|---------|
| `realestate_apt_ofst_20251008.csv` | ~2MB | 아파트 + 오피스텔 | ~7,000개 |
| `real_estate_vila_20251008.csv` | ~500KB | 빌라 | ~1,500개 |
| `realestate_oneroom_20251008csv.csv` | ~300KB | 원룸 + 단독/다가구 | ~1,200개 |

**참고**: 이 파일들은 "데이터베이스 담당자"가 제공한 실제 매물 데이터입니다.

### 2. 데이터베이스 스크립트

**위치**: `backend/scripts/`

| 스크립트 | 목적 | 실행 순서 |
|---------|------|----------|
| `init_db.py` | PostgreSQL 테이블 생성 | 1 |
| `import_apt_ofst.py` | 아파트/오피스텔 데이터 삽입 | 2 |
| `import_villa_house_oneroom.py` | 빌라/원룸/단독 데이터 삽입 | 3 |
| `import_transaction_data.py` | 거래 데이터 삽입 | 4 |
| `import_mongo_data.py` | MongoDB 데이터 마이그레이션 (선택) | 5 |
| `generate_trust_scores.py` | 신뢰도 점수 생성 | 6 |

### 3. 모델 정의 파일

**위치**: `backend/app/models/`

| 파일 | 내용 |
|-----|------|
| `real_estate.py` | RealEstate, Region, Transaction, RealEstateAgent 모델 |
| `trust.py` | TrustScore 모델 |
| `users.py` | User, UserProfile, UserFavorite 모델 |
| `chat.py` | ChatSession, ChatMessage 모델 |
| `__init__.py` | 모든 모델 등록 (순환 참조 방지) |

---

## Step-by-Step 가이드

### 사전 준비

#### 1. PostgreSQL 설치 및 실행

```bash
# PostgreSQL 설치 확인
psql --version

# PostgreSQL 서비스 실행 (Windows)
# Services.msc에서 "PostgreSQL" 시작

# PostgreSQL 서비스 실행 (Linux/Mac)
sudo systemctl start postgresql
```

#### 2. 데이터베이스 생성

```sql
-- PostgreSQL 접속
psql -U postgres

-- 데이터베이스 생성
CREATE DATABASE holmesnyangz_db;

-- 사용자 생성 (선택)
CREATE USER holmesnyangz_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE holmesnyangz_db TO holmesnyangz_user;
```

#### 3. 환경변수 설정

**파일**: `backend/.env`

```env
# PostgreSQL 연결 정보
DATABASE_URL=postgresql://postgres:password@localhost:5432/holmesnyangz_db

# 또는 사용자 계정 사용
DATABASE_URL=postgresql://holmesnyangz_user:your_password@localhost:5432/holmesnyangz_db
```

#### 4. Python 패키지 설치

```bash
cd backend
pip install -r requirements.txt
```

**주요 패키지**:
- `sqlalchemy` (ORM)
- `psycopg2-binary` 또는 `psycopg3` (PostgreSQL 드라이버)
- `python-dotenv` (환경변수)

---

### Step 1: 테이블 생성

```bash
cd backend
python scripts/init_db.py
```

**생성되는 테이블** (13개):
1. `regions` - 지역 정보
2. `real_estates` - 매물 정보
3. `transactions` - 거래 내역
4. `nearby_facilities` - 주변 시설
5. `real_estate_agents` - 중개사 정보
6. `trust_scores` - 신뢰도 점수
7. `users` - 사용자 정보
8. `user_profiles` - 사용자 프로필
9. `local_auths` - 로컬 인증
10. `social_auths` - 소셜 인증
11. `user_favorites` - 찜 목록
12. `chat_sessions` - 채팅 세션
13. `chat_messages` - 채팅 메시지

**확인**:
```sql
-- PostgreSQL 접속
psql -U postgres -d holmesnyangz_db

-- 테이블 목록 확인
\dt

-- 예상 출력:
--  Schema |       Name        | Type  |  Owner
-- --------+-------------------+-------+----------
--  public | regions           | table | postgres
--  public | real_estates      | table | postgres
--  ...
```

---

### Step 2: 아파트/오피스텔 데이터 삽입

```bash
cd backend
python scripts/import_apt_ofst.py
```

**처리 내용**:
- CSV 파일: `data/real_estate/realestate_apt_ofst_20251008.csv`
- 매물 수: ~7,000개
- 거래 데이터: Transaction 테이블에 자동 삽입
- 중개사 데이터: RealEstateAgent 테이블에 자동 삽입

**예상 출력**:
```
Processing apartment and officetel data...
Imported 7,123 properties
Imported 8,456 transactions
Imported 5,234 agents
Success!
```

---

### Step 3: 빌라/원룸/단독 데이터 삽입

```bash
cd backend
python scripts/import_villa_house_oneroom.py
```

**처리 내용**:
- CSV 파일 2개:
  - `data/real_estate/real_estate_vila_20251008.csv`
  - `data/real_estate/realestate_oneroom_20251008csv.csv`
- 매물 수: ~2,700개

**예상 출력**:
```
Processing villa, house, and oneroom data...
Imported 2,615 properties
Imported 2,316 transactions
Imported 2,400 agents
Success!
```

---

### Step 4: 추가 거래 데이터 삽입 (선택)

```bash
cd backend
python scripts/import_transaction_data.py
```

**참고**: 이 스크립트는 추가 거래 데이터가 있을 경우에만 실행합니다.

---

### Step 5: MongoDB 데이터 마이그레이션 (선택)

```bash
cd backend
python scripts/import_mongo_data.py
```

**참고**: 기존 MongoDB에 데이터가 있는 경우에만 실행합니다.

---

### Step 6: 신뢰도 점수 생성 ⭐ **중요**

```bash
cd backend
python scripts/generate_trust_scores.py
```

**처리 내용**:
- 전체 매물: 9,738개
- 계산 기준: 4가지 (거래 이력, 가격 적정성, 정보 완전성, 중개사 등록)
- 소요 시간: ~2분

**예상 출력**:
```
============================================================
TrustScore Generation Script
============================================================
Total properties to process: 9738

Processing batch 1 (offset: 0)
  Processed: 50/9738 | Created: 50 | Updated: 0 | Errors: 0
  Processed: 100/9738 | Created: 100 | Updated: 0 | Errors: 0

...

Processing batch 98 (offset: 9700)

============================================================
Generation completed!
Total processed: 9738
Created: 9738
Updated: 0
Errors: 0
============================================================

Script execution completed.
```

---

## 데이터 검증

### 1. 데이터 개수 확인

```bash
cd backend
python scripts/check_db_data.py
```

**예상 출력**:
```
=== PostgreSQL 데이터 확인 ===
RealEstate: 9,738개
Region: 150개
Transaction: 10,772개
RealEstateAgent: 7,634개
TrustScore: 9,738개
User: 0개 (정상 - 사용자 인증 미구현)
ChatSession: 0개 (정상 - 아직 채팅 없음)
```

### 2. SQL 직접 확인

```sql
-- PostgreSQL 접속
psql -U postgres -d holmesnyangz_db

-- 매물 수 확인
SELECT COUNT(*) FROM real_estates;
-- 예상: 9738

-- 신뢰도 점수 통계
SELECT
    COUNT(*) as total,
    AVG(score) as avg_score,
    MIN(score) as min_score,
    MAX(score) as max_score
FROM trust_scores;
-- 예상: 9738, 64.56, 42.86, 81.43

-- 샘플 데이터 확인
SELECT
    re.id,
    re.name,
    re.address,
    ts.score,
    ts.verification_notes
FROM real_estates re
LEFT JOIN trust_scores ts ON re.id = ts.real_estate_id
LIMIT 5;
```

### 3. Python 스크립트로 검증

```bash
cd backend
python scripts/verify_trust_scores.py
```

**예상 출력**:
```
Sample TrustScore Records:
====================================================================================================
ID: 8605 | RealEstate ID: 8605 | Score: 81.43
Notes: 거래 이력: 1건 (10.0점) | 가격 적정성: 25.0점 | 정보 완전성: 21.4점 (86%) | 중개사 등록: 있음 (25.0점)
Calculated At: 2025-10-14 02:11:24.189422+09:00
----------------------------------------------------------------------------------------------------
...
```

---

## 트러블슈팅

### 문제 1: "DATABASE_URL not found"

**증상**:
```
KeyError: 'DATABASE_URL'
```

**해결**:
1. `.env` 파일이 `backend/` 디렉토리에 있는지 확인
2. `.env` 파일에 `DATABASE_URL=postgresql://...` 설정 확인
3. `python-dotenv` 패키지 설치 확인

### 문제 2: "psycopg2.OperationalError: could not connect"

**증상**:
```
psycopg2.OperationalError: could not connect to server
```

**해결**:
1. PostgreSQL 서비스 실행 확인
2. 데이터베이스 이름, 포트 확인
3. 방화벽 설정 확인

### 문제 3: "Table already exists"

**증상**:
```
sqlalchemy.exc.ProgrammingError: relation "real_estates" already exists
```

**해결**:
```sql
-- 모든 테이블 삭제 후 재생성
psql -U postgres -d holmesnyangz_db

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- 다시 init_db.py 실행
```

### 문제 4: CSV 파일 인코딩 에러

**증상**:
```
UnicodeDecodeError: 'utf-8' codec can't decode
```

**해결**:
CSV 파일을 UTF-8 인코딩으로 변환:
```bash
iconv -f EUC-KR -t UTF-8 input.csv > output.csv
```

### 문제 5: TrustScore 생성 중 "no attribute 'price'"

**증상**:
```
AttributeError: type object 'RealEstate' has no attribute 'price'
```

**해결**:
- 이미 수정된 버전의 `generate_trust_scores.py` 사용
- Transaction 테이블에서 가격을 가져오도록 구현됨

---

## 추가 리소스

### 관련 문서

- **Phase 1-2-3 완료 보고서**: `backend/app/reports/complete_phase_1_2_completion_report_v3.md`
- **데이터베이스 스키마 분석**: `backend/app/reports/database_schema_analysis_report.md`
- **TrustScore 생성 보고서**: `backend/app/reports/trust_score_generation_completion_report.md`

### 스크립트 위치

```
backend/
├── scripts/
│   ├── init_db.py                      # 테이블 생성
│   ├── import_apt_ofst.py              # 아파트/오피스텔 import
│   ├── import_villa_house_oneroom.py   # 빌라/원룸/단독 import
│   ├── import_transaction_data.py      # 거래 데이터 import
│   ├── import_mongo_data.py            # MongoDB 마이그레이션
│   ├── generate_trust_scores.py        # 신뢰도 점수 생성 ⭐
│   ├── verify_trust_scores.py          # 데이터 검증
│   └── check_db_data.py                # 전체 데이터 확인
└── data/
    └── real_estate/
        ├── realestate_apt_ofst_20251008.csv
        ├── real_estate_vila_20251008.csv
        └── realestate_oneroom_20251008csv.csv
```

---

## 빠른 시작 (전체 프로세스)

**전체를 한 번에 실행**:

```bash
# 1. 환경변수 설정
echo "DATABASE_URL=postgresql://postgres:password@localhost:5432/holmesnyangz_db" > backend/.env

# 2. 데이터베이스 생성
psql -U postgres -c "CREATE DATABASE holmesnyangz_db;"

# 3. 패키지 설치
cd backend
pip install -r requirements.txt

# 4. 테이블 생성
python scripts/init_db.py

# 5. 데이터 삽입
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py

# 6. 신뢰도 점수 생성 ⭐
python scripts/generate_trust_scores.py

# 7. 검증
python scripts/check_db_data.py
python scripts/verify_trust_scores.py

# 완료!
```

**예상 소요 시간**: 10-15분

---

## 결론

이 가이드를 따라하면 다른 개발자가 **동일한 데이터베이스를 완전히 재현**할 수 있습니다.

**최종 데이터베이스 상태**:
- ✅ 9,738개 매물 (RealEstate)
- ✅ 10,772건 거래 내역 (Transaction)
- ✅ 7,634개 중개사 정보 (RealEstateAgent)
- ✅ 9,738개 신뢰도 점수 (TrustScore, 평균 64.56/100)

**다음 단계**:
- 서버 실행 및 API 테스트
- 10개 테스트 쿼리 실행
- 프론트엔드 연동

---

**작성자**: Claude Code
**최종 업데이트**: 2025-10-14
**문의**: 프로젝트 담당자
