# 📝 API 사용 예시 및 쿼리 패턴

> AI 에이전트가 데이터베이스를 효과적으로 활용하기 위한 실전 예시 모음

---

## 📋 목차

1. [기본 CRUD 예시](#기본-crud-예시)
2. [검색 쿼리 패턴](#검색-쿼리-패턴)
3. [AI 에이전트용 쿼리](#ai-에이전트용-쿼리)
4. [복잡한 쿼리](#복잡한-쿼리)
5. [성능 최적화 예시](#성능-최적화-예시)
6. [실전 시나리오](#실전-시나리오)

---

## 기본 CRUD 예시

### 데이터베이스 연결

```python
from app.db.postgre_db import SessionLocal, get_db
from app.models.real_estate import RealEstate, Transaction, Region, PropertyType, TransactionType
from app.models.users import User
from app.models.chat import ChatSession, ChatMessage

# 세션 생성
db = SessionLocal()

try:
    # 쿼리 실행
    result = db.query(RealEstate).first()
    db.commit()  # 변경사항이 있을 경우
finally:
    db.close()  # 항상 종료

# FastAPI에서 Dependency Injection 사용
from fastapi import Depends

def some_endpoint(db: Session = Depends(get_db)):
    # db 자동으로 생성 및 종료
    result = db.query(RealEstate).all()
    return result
```

### Create (생성)

```python
# 새 부동산 등록
new_estate = RealEstate(
    property_type=PropertyType.APARTMENT,
    code="APT001",
    name="래미안강남",
    region_id=1,
    address="서울시 강남구 역삼동 123",
    latitude=37.123456,
    longitude=127.123456
)
db.add(new_estate)
db.commit()
db.refresh(new_estate)  # ID 등 자동 생성 값 가져오기
print(f"생성된 매물 ID: {new_estate.id}")
```

### Read (조회)

```python
# 단일 조회 - ID로
estate = db.query(RealEstate).filter(RealEstate.id == 1).first()
# 또는
estate = db.query(RealEstate).get(1)

# 단일 조회 - 코드로
estate = db.query(RealEstate).filter(RealEstate.code == "APT001").first()

# 다중 조회
estates = db.query(RealEstate).limit(10).all()

# 조건부 조회
apartments = db.query(RealEstate).filter(
    RealEstate.property_type == PropertyType.APARTMENT
).all()

# 여러 조건 (AND)
results = db.query(RealEstate).filter(
    RealEstate.property_type == PropertyType.APARTMENT,
    RealEstate.total_households > 100
).all()

# OR 조건
from sqlalchemy import or_

results = db.query(RealEstate).filter(
    or_(
        RealEstate.property_type == PropertyType.APARTMENT,
        RealEstate.property_type == PropertyType.OFFICETEL
    )
).all()

# IN 조건
results = db.query(RealEstate).filter(
    RealEstate.property_type.in_([PropertyType.APARTMENT, PropertyType.VILLA])
).all()
```

### Update (수정)

```python
# 단일 수정
estate = db.query(RealEstate).filter(RealEstate.id == 1).first()
if estate:
    estate.name = "새로운 이름"
    estate.total_households = 150
    db.commit()

# 일괄 수정
db.query(RealEstate).filter(
    RealEstate.property_type == PropertyType.APARTMENT
).update({"deal_count": 0})
db.commit()
```

### Delete (삭제)

```python
# 단일 삭제
estate = db.query(RealEstate).filter(RealEstate.id == 1).first()
if estate:
    db.delete(estate)
    db.commit()

# 일괄 삭제
db.query(Transaction).filter(
    Transaction.transaction_date < "2020-01-01"
).delete()
db.commit()
```

---

## 검색 쿼리 패턴

### 1. 지역 기반 검색

```python
# 특정 지역의 부동산
region_name = "강남구"
estates = db.query(RealEstate).join(Region).filter(
    Region.name.contains(region_name)
).all()

# 여러 지역
region_names = ["강남구", "서초구", "송파구"]
estates = db.query(RealEstate).join(Region).filter(
    or_(*[Region.name.contains(name) for name in region_names])
).all()
```

### 2. 가격 기반 검색

```python
# 매매가 5억 이하
cheap_estates = db.query(RealEstate).join(Transaction).filter(
    Transaction.transaction_type == TransactionType.SALE,
    Transaction.sale_price <= 50000  # 만원 단위
).distinct().all()

# 가격 범위
estates = db.query(RealEstate).join(Transaction).filter(
    Transaction.sale_price.between(30000, 50000)
).distinct().all()

# 최저가 조회
from sqlalchemy import func

min_price = db.query(func.min(Transaction.sale_price)).scalar()
print(f"최저가: {min_price}만원")
```

### 3. 타입 기반 검색

```python
# 아파트만
apartments = db.query(RealEstate).filter(
    RealEstate.property_type == PropertyType.APARTMENT
).all()

# 아파트 또는 오피스텔
results = db.query(RealEstate).filter(
    RealEstate.property_type.in_([PropertyType.APARTMENT, PropertyType.OFFICETEL])
).all()
```

### 4. 면적 기반 검색

```python
# 전용면적 60㎡ 이상
large_estates = db.query(RealEstate).filter(
    RealEstate.min_exclusive_area >= 60
).all()

# 전용면적 범위
estates = db.query(RealEstate).filter(
    RealEstate.representative_area.between(60, 100)
).all()
```

### 5. 위치 기반 검색 (좌표)

```python
from sqlalchemy import func

# 특정 좌표 근처 (간단한 방법)
center_lat = 37.497942
center_lon = 127.027621
radius = 0.01  # 약 1km

nearby = db.query(RealEstate).filter(
    func.abs(RealEstate.latitude - center_lat) < radius,
    func.abs(RealEstate.longitude - center_lon) < radius
).all()

# 거리 계산 포함 (Haversine formula)
# PostGIS 확장이 없다면 Python에서 후처리
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 지구 반지름 (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

estates = db.query(RealEstate).filter(
    RealEstate.latitude.isnot(None),
    RealEstate.longitude.isnot(None)
).all()

nearby_estates = [
    e for e in estates
    if calculate_distance(center_lat, center_lon, float(e.latitude), float(e.longitude)) < 1.0
]
```

### 6. 텍스트 검색

```python
# 부동산 이름으로 검색
estates = db.query(RealEstate).filter(
    RealEstate.name.contains("래미안")
).all()

# 대소문자 무시
estates = db.query(RealEstate).filter(
    RealEstate.name.ilike("%래미안%")
).all()

# 주소로 검색
estates = db.query(RealEstate).filter(
    RealEstate.address.contains("역삼동")
).all()
```

---

## AI 에이전트용 쿼리

### 1. 자연어 질문 → SQL 변환 예시

**사용자 질문**: "강남구에 있는 아파트 알려줘"

```python
def search_by_natural_language(region: str = None, property_type: str = None):
    query = db.query(RealEstate)

    if region:
        query = query.join(Region).filter(Region.name.contains(region))

    if property_type:
        type_map = {
            "아파트": PropertyType.APARTMENT,
            "오피스텔": PropertyType.OFFICETEL,
            "빌라": PropertyType.VILLA,
            "원룸": PropertyType.ONEROOM
        }
        query = query.filter(RealEstate.property_type == type_map.get(property_type))

    return query.limit(10).all()

# 사용
results = search_by_natural_language(region="강남구", property_type="아파트")
```

**사용자 질문**: "5억 이하 전세 매물 보여줘"

```python
def search_by_price_and_type(
    max_price: int = None,
    transaction_type: str = "jeonse"
):
    query = db.query(RealEstate).join(Transaction).filter(
        Transaction.transaction_type == TransactionType.JEONSE
    )

    if max_price:
        query = query.filter(Transaction.deposit <= max_price)

    return query.distinct().limit(10).all()

results = search_by_price_and_type(max_price=50000)
```

### 2. AI 에이전트 응답 포맷팅

```python
def format_estate_for_ai(estate: RealEstate) -> dict:
    """AI 에이전트가 읽기 쉬운 형식으로 변환"""
    return {
        "이름": estate.name,
        "주소": estate.address,
        "타입": {
            PropertyType.APARTMENT: "아파트",
            PropertyType.OFFICETEL: "오피스텔",
            PropertyType.VILLA: "빌라",
            PropertyType.ONEROOM: "원룸"
        }.get(estate.property_type, "기타"),
        "지역": estate.region.name if estate.region else "미상",
        "전용면적": f"{estate.representative_area}㎡" if estate.representative_area else "미상",
        "준공년도": estate.completion_date[:4] if estate.completion_date else "미상",
        "세대수": f"{estate.total_households}세대" if estate.total_households else "미상",
        "가격정보": {
            "매매": f"{t.sale_price}만원" if (t := estate.transactions[0] if estate.transactions else None) and t.sale_price else "정보없음",
        }
    }

# 사용
estate = db.query(RealEstate).first()
formatted = format_estate_for_ai(estate)
print(formatted)
```

### 3. 컨텍스트 기반 검색 (대화 히스토리 고려)

```python
class ConversationContext:
    def __init__(self):
        self.last_region = None
        self.last_property_type = None
        self.last_price_range = None

    def search(self, **kwargs):
        # 명시되지 않은 조건은 이전 대화에서 가져오기
        region = kwargs.get('region', self.last_region)
        property_type = kwargs.get('property_type', self.last_property_type)

        query = db.query(RealEstate)

        if region:
            query = query.join(Region).filter(Region.name.contains(region))
            self.last_region = region

        if property_type:
            query = query.filter(RealEstate.property_type == property_type)
            self.last_property_type = property_type

        return query.limit(10).all()

# 사용 (대화 예시)
ctx = ConversationContext()

# 사용자: "강남구 아파트 보여줘"
results1 = ctx.search(region="강남구", property_type=PropertyType.APARTMENT)

# 사용자: "그 중에서 100세대 이상인 곳은?"  (강남구, 아파트 유지)
results2 = ctx.search()  # last_region, last_property_type 자동 사용
results2 = [r for r in results2 if r.total_households and r.total_households >= 100]
```

---

## 복잡한 쿼리

### 1. 다중 조인

```python
# 부동산 + 지역 + 거래 + 주변시설
from sqlalchemy.orm import joinedload

estates = db.query(RealEstate).options(
    joinedload(RealEstate.region),
    joinedload(RealEstate.transactions),
    joinedload(RealEstate.nearby_facility)
).filter(
    RealEstate.property_type == PropertyType.APARTMENT
).limit(10).all()

for estate in estates:
    print(f"{estate.name} ({estate.region.name})")
    print(f"  거래 {len(estate.transactions)}건")
    if estate.nearby_facility:
        print(f"  지하철: {estate.nearby_facility.subway_line}")
```

### 2. 집계 쿼리

```python
from sqlalchemy import func

# 지역별 평균 가격
avg_prices = db.query(
    Region.name,
    func.avg(Transaction.sale_price).label('avg_price')
).join(RealEstate).join(Transaction).filter(
    Transaction.sale_price > 0
).group_by(Region.name).order_by(func.avg(Transaction.sale_price).desc()).all()

for region, avg_price in avg_prices:
    print(f"{region}: 평균 {avg_price:,.0f}만원")

# 타입별 매물 수
type_counts = db.query(
    RealEstate.property_type,
    func.count(RealEstate.id).label('count')
).group_by(RealEstate.property_type).all()

for ptype, count in type_counts:
    print(f"{ptype.value}: {count}개")
```

### 3. 서브쿼리

```python
from sqlalchemy import select

# 평균 가격 이하 매물
avg_price_subq = db.query(func.avg(Transaction.sale_price)).filter(
    Transaction.sale_price > 0
).scalar_subquery()

cheap_estates = db.query(RealEstate).join(Transaction).filter(
    Transaction.sale_price <= avg_price_subq
).distinct().all()
```

### 4. 랭킹 쿼리

```python
from sqlalchemy import func, desc

# 가장 비싼 매물 Top 10
expensive = db.query(
    RealEstate,
    func.max(Transaction.sale_price).label('max_price')
).join(Transaction).group_by(RealEstate.id).order_by(
    desc('max_price')
).limit(10).all()

for estate, price in expensive:
    print(f"{estate.name}: {price:,}만원")
```

---

## 성능 최적화 예시

### 1. Eager Loading vs Lazy Loading

```python
# 나쁨: N+1 문제 (10개 부동산 조회 시 1 + 10 = 11번 쿼리)
estates = db.query(RealEstate).limit(10).all()
for estate in estates:
    print(estate.region.name)  # 각 반복마다 DB 쿼리

# 좋음: Eager Loading (2번 쿼리)
from sqlalchemy.orm import joinedload

estates = db.query(RealEstate).options(
    joinedload(RealEstate.region)
).limit(10).all()
for estate in estates:
    print(estate.region.name)  # 추가 쿼리 없음
```

### 2. 필요한 컬럼만 조회

```python
# 나쁨: 모든 컬럼 조회
estates = db.query(RealEstate).all()

# 좋음: 필요한 컬럼만
names = db.query(RealEstate.id, RealEstate.name).all()
```

### 3. Pagination

```python
def get_paginated_estates(page: int = 1, page_size: int = 10):
    offset = (page - 1) * page_size
    estates = db.query(RealEstate).offset(offset).limit(page_size).all()
    total = db.query(func.count(RealEstate.id)).scalar()

    return {
        "data": estates,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
```

### 4. 인덱스 활용

```python
# 좋음: 인덱스 사용 (code에 UNIQUE INDEX)
estate = db.query(RealEstate).filter(RealEstate.code == "APT001").first()

# 나쁨: Full table scan
estate = db.query(RealEstate).filter(RealEstate.building_description.contains("좋은")).first()
```

---

## 실전 시나리오

### 시나리오 1: "강남구에서 지하철역 가까운 아파트 찾아줘"

```python
def find_subway_near_apartments(region_name: str, max_walking_time: int = 10):
    """지하철 가까운 아파트 검색"""
    estates = db.query(RealEstate).join(Region).join(NearbyFacility).filter(
        Region.name.contains(region_name),
        RealEstate.property_type == PropertyType.APARTMENT,
        NearbyFacility.subway_walking_time <= max_walking_time
    ).options(
        joinedload(RealEstate.region),
        joinedload(RealEstate.nearby_facility)
    ).limit(10).all()

    results = []
    for estate in estates:
        results.append({
            "이름": estate.name,
            "주소": estate.address,
            "지하철": estate.nearby_facility.subway_line if estate.nearby_facility else None,
            "도보시간": f"{estate.nearby_facility.subway_walking_time}분" if estate.nearby_facility else None
        })

    return results
```

### 시나리오 2: "서초구에서 최근 거래된 3억 이하 아파트"

```python
from datetime import datetime, timedelta

def find_recent_cheap_apartments(region_name: str, max_price: int, days: int = 90):
    """최근 거래된 저가 아파트"""
    recent_date = datetime.now() - timedelta(days=days)

    estates = db.query(RealEstate).join(Region).join(Transaction).filter(
        Region.name.contains(region_name),
        RealEstate.property_type == PropertyType.APARTMENT,
        Transaction.transaction_type == TransactionType.SALE,
        Transaction.sale_price <= max_price,
        Transaction.transaction_date >= recent_date
    ).distinct().options(
        joinedload(RealEstate.transactions)
    ).all()

    results = []
    for estate in estates:
        recent_tx = sorted(estate.transactions, key=lambda x: x.transaction_date, reverse=True)[0]
        results.append({
            "이름": estate.name,
            "가격": f"{recent_tx.sale_price:,}만원",
            "거래일": recent_tx.transaction_date.strftime("%Y-%m-%d")
        })

    return results
```

### 시나리오 3: "학군 좋은 지역의 아파트 추천해줘"

```python
def find_apartments_with_good_schools(min_schools: int = 3):
    """학교 많은 지역의 아파트"""
    from sqlalchemy import func

    estates = db.query(RealEstate).join(NearbyFacility).filter(
        RealEstate.property_type == PropertyType.APARTMENT,
        or_(
            NearbyFacility.elementary_schools.isnot(None),
            NearbyFacility.middle_schools.isnot(None),
            NearbyFacility.high_schools.isnot(None)
        )
    ).options(
        joinedload(RealEstate.nearby_facility)
    ).all()

    # Python에서 학교 수 계산 (TEXT 컬럼이므로)
    results = []
    for estate in estates:
        facility = estate.nearby_facility
        if not facility:
            continue

        school_count = 0
        if facility.elementary_schools:
            school_count += len(facility.elementary_schools.split(','))
        if facility.middle_schools:
            school_count += len(facility.middle_schools.split(','))
        if facility.high_schools:
            school_count += len(facility.high_schools.split(','))

        if school_count >= min_schools:
            results.append({
                "이름": estate.name,
                "학교수": school_count,
                "초등학교": facility.elementary_schools,
                "중학교": facility.middle_schools,
                "고등학교": facility.high_schools
            })

    return sorted(results, key=lambda x: x['학교수'], reverse=True)
```

### 시나리오 4: "신축 아파트 중에서 평수 큰 곳"

```python
def find_new_large_apartments(years: int = 5, min_area: float = 100):
    """신축 대형 아파트"""
    current_year = datetime.now().year
    min_completion = f"{current_year - years}01"  # YYYYMM 형식

    estates = db.query(RealEstate).filter(
        RealEstate.property_type == PropertyType.APARTMENT,
        RealEstate.completion_date >= min_completion,
        RealEstate.representative_area >= min_area
    ).options(
        joinedload(RealEstate.region)
    ).order_by(RealEstate.completion_date.desc()).all()

    results = []
    for estate in estates:
        results.append({
            "이름": estate.name,
            "지역": estate.region.name if estate.region else "미상",
            "준공": f"{estate.completion_date[:4]}년 {estate.completion_date[4:6]}월",
            "면적": f"{estate.representative_area}㎡ ({estate.representative_area * 0.3025:.1f}평)"
        })

    return results
```

### 시나리오 5: "사용자가 찜한 매물과 비슷한 매물 추천"

```python
def recommend_similar_estates(user_id: int, limit: int = 5):
    """사용자 찜 기반 추천"""
    # 사용자가 찜한 매물
    favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == user_id
    ).options(joinedload(UserFavorite.real_estate)).all()

    if not favorites:
        return []

    # 찜한 매물의 특성 분석
    fav_estates = [f.real_estate for f in favorites]
    common_type = max(set(e.property_type for e in fav_estates), key=lambda x: sum(e.property_type == x for e in fav_estates))
    avg_area = sum(e.representative_area or 0 for e in fav_estates) / len(fav_estates)

    # 비슷한 매물 찾기
    similar = db.query(RealEstate).filter(
        RealEstate.property_type == common_type,
        RealEstate.representative_area.between(avg_area * 0.8, avg_area * 1.2),
        RealEstate.id.notin_([e.id for e in fav_estates])  # 이미 찜한 것 제외
    ).limit(limit).all()

    return [{
        "이름": estate.name,
        "주소": estate.address,
        "면적": f"{estate.representative_area}㎡"
    } for estate in similar]
```

---

## 에러 처리 예시

```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

def safe_create_estate(estate_data: dict):
    """안전한 부동산 생성"""
    try:
        estate = RealEstate(**estate_data)
        db.add(estate)
        db.commit()
        db.refresh(estate)
        return {"success": True, "data": estate}
    except IntegrityError as e:
        db.rollback()
        return {"success": False, "error": "중복된 매물 코드입니다"}
    except SQLAlchemyError as e:
        db.rollback()
        return {"success": False, "error": f"데이터베이스 오류: {str(e)}"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"알 수 없는 오류: {str(e)}"}
```

---

## 트랜잭션 관리

```python
from contextlib import contextmanager

@contextmanager
def db_transaction():
    """트랜잭션 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# 사용
with db_transaction() as db:
    estate = RealEstate(...)
    db.add(estate)
    # 자동 commit/rollback/close
```

---

## 테스트용 쿼리

```python
# 데이터베이스 연결 확인
def test_connection():
    try:
        db = SessionLocal()
        db.query(RealEstate).first()
        db.close()
        return True
    except Exception as e:
        print(f"연결 실패: {e}")
        return False

# 데이터 통계
def get_statistics():
    db = SessionLocal()
    stats = {
        "regions": db.query(Region).count(),
        "real_estates": db.query(RealEstate).count(),
        "transactions": db.query(Transaction).count(),
        "users": db.query(User).count(),
        "by_type": {
            ptype.value: db.query(RealEstate).filter(
                RealEstate.property_type == ptype
            ).count()
            for ptype in PropertyType
        }
    }
    db.close()
    return stats
```

---

**마지막 업데이트**: 2025-10-13
**버전**: 1.0.0
