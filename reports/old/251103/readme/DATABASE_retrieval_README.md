# 부동산 데이터 Import 스크립트 가이드

## 📋 개요

CSV 데이터를 PostgreSQL 데이터베이스로 import하는 스크립트 모음입니다.

## 🗂️ 스크립트 목록

### 0. `init_db.py` - 데이터베이스 초기화 ⭐
- **기능**: 모든 DB 연결 종료 후 테이블 삭제 및 재생성
- **사용**: 데이터를 처음부터 다시 import할 때

```bash
# 기존 데이터 모두 삭제하고 테이블 재생성
uv run python scripts/init_db.py

# 테이블 생성만 (삭제 안 함)
uv run python scripts/init_db.py --no-drop
```

---

### 1. `import_apt_ofst.py` - 아파트/오피스텔 데이터
- **파일**: `data/real_estate/realestate_apt_ofst_20251008.csv`
- **데이터**: 아파트, 오피스텔 단지 정보 (약 2,104개)
- **실행 시간**: 약 1-2분

```bash
uv run python scripts/import_apt_ofst.py
```

### 2. `import_villa_house_oneroom.py` - 빌라/원룸/다가구 데이터
- **파일**:
  - `data/real_estate/real_estate_vila_20251008.csv` (빌라 6,631개)
  - `data/real_estate/realestate_oneroom_20251008csv.csv` (원룸 1,010개)
- **데이터**: 개별 매물 정보
- **실행 시간**: 빌라 5-10분, 원룸 1-2분

```bash
# 원룸만 (자동)
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom

# 빌라만 (자동)
uv run python scripts/import_villa_house_oneroom.py --auto --type villa

# 둘 다 (자동)
uv run python scripts/import_villa_house_oneroom.py --auto --type all

# 대화형 선택
uv run python scripts/import_villa_house_oneroom.py
```

### 3. `import_transaction_data.py` - 거래 가격 데이터 (선택)
- **파일**: `frontend/public/data/real_estate_with_coordinates_kakao.csv`
- **데이터**: 단지별 거래 가격 범위
- **실행 시간**: 약 1-2분
- **참고**: 아파트/오피스텔 import 시 가격 정보도 함께 들어가므로 선택사항

```bash
uv run python scripts/import_transaction_data.py
```

### 4. `import_mongo_data.py` - MongoDB 은행 데이터 (선택)
- **기능**: MongoDB에 은행 데이터 import
- **데이터**: 7개 은행 데이터

```bash
uv run python scripts/import_mongo_data.py
```

---

## 🚀 추천 실행 순서

```bash
# Step 1: 데이터베이스 초기화 (기존 데이터 삭제)
uv run python scripts/init_db.py

# Step 2: 아파트/오피스텔 import
uv run python scripts/import_apt_ofst.py

# Step 3: 원룸 import
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom

# Step 4: 빌라 import
uv run python scripts/import_villa_house_oneroom.py --auto --type villa

# (선택) MongoDB 은행 데이터
uv run python scripts/import_mongo_data.py
```

---

## 📊 Import되는 테이블

- **regions**: 지역 정보 (구, 동)
- **real_estates**: 부동산 기본 정보
- **transactions**: 거래 내역 및 가격 정보
- **nearby_facilities**: 주변 편의시설 (지하철, 학교)
- **real_estate_agents**: 부동산 중개사 정보 (빌라/원룸만)

---

## ✅ 주요 기능

### 중복 방지
- 모든 스크립트는 `code` 필드로 중복 체크
- 이미 존재하는 데이터는 자동 건너뛰기
- 안전하게 여러 번 실행 가능

### 에러 처리
- 개별 레코드 에러 시 해당 레코드만 건너뛰고 계속 진행
- 최대 5개까지 에러 메시지 출력
- 전체 프로세스는 중단되지 않음

### 진행 상황 표시
- 100개(또는 200개)마다 진행 상황 출력
- 성공/실패 카운트 제공
- 최종 통계 출력

---

## 🔧 유틸리티 (`import_utils.py`)

공통 유틸리티 함수 제공:
- `safe_int()`, `safe_float()`, `safe_decimal()`, `safe_str()`: 안전한 타입 변환
- `get_or_create_region()`: 지역 생성/조회
- `parse_region_from_name()`: 구/동 이름으로 지역 파싱
- `parse_completion_date()`: 준공년월 파싱
- `parse_tag_list()`: 태그 리스트 파싱
- `clean_school_list()`: 학교 목록 정리

---

## 📈 데이터 확인

import 후 데이터 확인:

```bash
uv run python -c "
from app.db.postgre_db import SessionLocal
from app.models.real_estate import RealEstate, PropertyType, Transaction, Region

db = SessionLocal()
print('📊 현재 데이터베이스 상태:\n')
print(f'  Regions:       {db.query(Region).count():5,}개')
print(f'  RealEstates:   {db.query(RealEstate).count():5,}개')
print(f'  Transactions:  {db.query(Transaction).count():5,}개')
print(f'\n부동산 타입별:')
print(f'  아파트:        {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.APARTMENT).count():5,}개')
print(f'  오피스텔:      {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.OFFICETEL).count():5,}개')
print(f'  빌라:          {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.VILLA).count():5,}개')
print(f'  원룸:          {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.ONEROOM).count():5,}개')
db.close()
"
```

---

## ⚠️ 주의사항

1. **PostgreSQL 연결**: `.env` 파일에 `DATABASE_URL` 설정 필요
2. **실행 환경**: `uv` 사용 (프로젝트 의존성 관리)
3. **실행 디렉토리**: 반드시 `backend` 디렉토리에서 실행
4. **DB 락 문제**: `init_db.py`가 모든 연결을 종료하고 초기화

---

## 🐛 트러블슈팅

### DB 연결 확인
```bash
uv run python -c "from app.db.postgre_db import SessionLocal; db = SessionLocal(); print('✅ 연결 성공'); db.close()"
```

### CSV 파일 확인
```bash
ls -lh data/real_estate/
```

### DB 락 문제 발생 시
```bash
# init_db.py가 자동으로 모든 연결 종료
uv run python scripts/init_db.py
```

---

## 📝 실행 예시

```bash
$ uv run python scripts/init_db.py
============================================================
🚀 데이터베이스 초기화
============================================================
🗑️  기존 테이블 삭제 중...
🔨 모든 데이터베이스 연결 종료 중...
✅ 모든 연결 종료 완료
   삭제할 테이블: 13개
   ✓ regions
   ✓ real_estates
   ...
✅ 모든 테이블 삭제 완료
📦 테이블 생성 중...
✅ 데이터베이스 초기화 완료!

$ uv run python scripts/import_apt_ofst.py
============================================================
🏢 아파트/오피스텔 데이터 Import
============================================================
[아파트/오피스텔] 총 2895개 레코드
  📈 진행: 100/2895
  📈 진행: 200/2895
  ...
✅ 아파트/오피스텔: 성공 2,104개, 실패 0개
============================================================
📈 데이터베이스 전체 통계:
============================================================
  Regions:          31개
  RealEstates:   2,104개
  Transactions:  3,138개
============================================================
✅ Import 완료!
```
