# 작업 1: Tools 수동 병합 상세 가이드

**작성일**: 2025-10-30
**작성자**: Claude Code
**프로젝트**: beta_v001 (chatbot_improve)
**소스**: tests/backend/ (chatbot_execute 파일)
**우선순위**: **Tools는 tests/backend 우선** ⭐

---

## 🎯 작업 목표

### 총 5개 Tool 파일 병합

#### ✅ 신규 파일 (3개) - 단순 복사
- `building_registry_tool.py` (459줄)
- `legal_search_tool.py` (693줄)
- `realestate_terminology.py` (402줄)

#### 🔀 중복 파일 (2개) - Best-of-Both 병합
- `infrastructure_tool.py` (Backend 438줄 vs Tests 530줄)
- `real_estate_search_tool.py` (Backend 352줄 vs Tests 411줄)

#### 📝 설정 파일 업데이트
- `__init__.py` - 신규 tool exports 추가

---

## 📊 작업 전 상태 확인

### Backend (chatbot_improve) 현재 Tools
```
backend/app/service_agent/tools/
├── __init__.py
├── analysis_tools.py
├── contract_analysis_tool.py
├── hybrid_legal_search.py          ← 이름 다름 (HybridLegalSearch)
├── infrastructure_tool.py          ← 중복 (438줄, 16:28)
├── lease_contract_generator_tool.py
├── loan_data_tool.py
├── loan_simulator_tool.py
├── market_analysis_tool.py
├── market_data_tool.py
├── policy_matcher_tool.py
├── real_estate_search_tool.py      ← 중복 (352줄, 16:28)
└── roi_calculator_tool.py
```

### Tests (chatbot_execute) Tools
```
tests/backend/app/service_agent/tools/
├── building_registry_tool.py       ← 신규 (459줄)
├── infrastructure_tool.py          ← 중복 (530줄, 11:26)
├── legal_search_tool.py            ← 신규 (693줄)
├── real_estate_search_tool.py      ← 중복 (411줄, 11:26)
└── realestate_terminology.py       ← 신규 (402줄)
```

---

## 🔍 Phase 1: 신규 Tools 복사 (30분)

### 1.1 building_registry_tool.py 복사

**파일 정보:**
- 용량: 459줄
- 기능: 건축물대장 API 연동
- 충돌: 없음 (신규)

**실행 명령:**
```bash
cp tests/backend/app/service_agent/tools/building_registry_tool.py \
   backend/app/service_agent/tools/building_registry_tool.py
```

**검증:**
```bash
# 파일 존재 확인
ls -l backend/app/service_agent/tools/building_registry_tool.py

# 줄 수 확인
wc -l backend/app/service_agent/tools/building_registry_tool.py
# 예상 출력: 459 backend/app/service_agent/tools/building_registry_tool.py
```

**클래스 이름 확인:**
```bash
grep "^class " backend/app/service_agent/tools/building_registry_tool.py
# 예상 출력: class BuildingRegistryTool:
```

---

### 1.2 legal_search_tool.py 복사

**파일 정보:**
- 용량: 693줄
- 기능: SQLite + FAISS 하이브리드 법률 검색
- 충돌: 없음 (기존 hybrid_legal_search.py와 다른 이름)

**실행 명령:**
```bash
cp tests/backend/app/service_agent/tools/legal_search_tool.py \
   backend/app/service_agent/tools/legal_search_tool.py
```

**검증:**
```bash
ls -l backend/app/service_agent/tools/legal_search_tool.py
wc -l backend/app/service_agent/tools/legal_search_tool.py
# 예상 출력: 693 backend/app/service_agent/tools/legal_search_tool.py
```

**클래스 이름 확인:**
```bash
grep "^class " backend/app/service_agent/tools/legal_search_tool.py
# 예상 출력: class LegalSearch:
```

**⚠️ 주의:**
- 기존 `hybrid_legal_search.py` (HybridLegalSearch)와 **공존**
- 나중에 search_executor.py에서 LegalSearch 우선 사용
- HybridLegalSearch는 Fallback으로 유지

---

### 1.3 realestate_terminology.py 복사

**파일 정보:**
- 용량: 402줄
- 기능: 부동산 용어 사전
- 충돌: 없음 (신규)

**실행 명령:**
```bash
cp tests/backend/app/service_agent/tools/realestate_terminology.py \
   backend/app/service_agent/tools/realestate_terminology.py
```

**검증:**
```bash
ls -l backend/app/service_agent/tools/realestate_terminology.py
wc -l backend/app/service_agent/tools/realestate_terminology.py
# 예상 출력: 402 backend/app/service_agent/tools/realestate_terminology.py
```

**클래스 이름 확인:**
```bash
grep "^class " backend/app/service_agent/tools/realestate_terminology.py
# 예상 출력: class RealEstateTerminology: (예상)
```

---

### ✅ Phase 1 완료 체크리스트

- [ ] building_registry_tool.py 복사 완료
- [ ] legal_search_tool.py 복사 완료
- [ ] realestate_terminology.py 복사 완료
- [ ] 3개 파일 모두 459, 693, 402줄 확인
- [ ] 클래스 이름 확인 완료

---

## 🔀 Phase 2: infrastructure_tool.py 병합 (45분)

### 2.1 파일 비교 분석

**Backend (438줄, 10월 29 16:28):**
```python
CATEGORY_MAP = {
    "subway": "SW8",
    "kindergarten": "PS3",
    "elementary_school": "SC4",
    # ... 기존 카테고리
    "convenience_store": "CS2",  # ✅ 활성화
    "hospital": "HP8",           # ✅ 활성화
    "pharmacy": "PM9",           # ✅ 활성화
    "cafe": "CE7",               # ✅ 활성화
    "bank": "BK9",               # ✅ 활성화
}

# 메서드 8개
def __init__(...)
def search(...)
def search_subway_stations(...)
def search_schools(...)
def search_convenience_facilities(...)
def get_comprehensive_infrastructure(...)
def _search_by_category(...)
def _search_all_categories(...)
```

**Tests (530줄, +92줄, 10월 29 11:26):**
```python
CATEGORY_MAP = {
    "subway": "SW8",
    "kindergarten": "PS3",
    "elementary_school": "SC4",
    # ... 기존 카테고리
    # "convenience_store": "CS2",  # ❌ 주석 처리
    # "hospital": "HP8",           # ❌ 주석 처리
    # "pharmacy": "PM9",           # ❌ 주석 처리
    # "cafe": "CE7",               # ❌ 주석 처리
    # "bank": "BK9",               # ❌ 주석 처리
}

# 메서드 10개 (+2개)
def __init__(...)
def geocode_address(...)          # ✅ 신규!
def _geocode_by_keyword(...)      # ✅ 신규!
def search(...)
def search_subway_stations(...)
def search_schools(...)
def search_convenience_facilities(...)
def get_comprehensive_infrastructure(...)
def _search_by_category(...)
def _search_all_categories(...)
```

### 2.2 병합 전략

**원칙: Tests 파일 우선 (사용자 지시) ⭐**

**병합 결과:**
- ✅ Tests 파일 채택 (530줄, geocode 기능 포함)
- ✅ Tests의 CATEGORY_MAP 유지 (일부 카테고리 주석 처리 상태)
- ⚠️ Backend의 활성화된 카테고리는 **선택 사항** (필요 시 주석 제거)

**이유:**
- Tests가 더 많은 기능 (geocode_address, _geocode_by_keyword)
- 일부 카테고리 주석 처리는 **execute팀의 의도적 결정**
- 성능/API 쿼터 관리를 위한 선택일 가능성

### 2.3 실행 명령

**옵션 A: Tests 파일 그대로 채택 (권장)**
```bash
# 백업 (선택 사항)
cp backend/app/service_agent/tools/infrastructure_tool.py \
   backend/app/service_agent/tools/infrastructure_tool.py.backup

# Tests 버전으로 교체
cp tests/backend/app/service_agent/tools/infrastructure_tool.py \
   backend/app/service_agent/tools/infrastructure_tool.py
```

**검증:**
```bash
wc -l backend/app/service_agent/tools/infrastructure_tool.py
# 예상 출력: 530

# geocode_address 메서드 존재 확인
grep "def geocode_address" backend/app/service_agent/tools/infrastructure_tool.py
# 예상 출력: def geocode_address(self, address: str) -> Optional[Dict[str, float]]:
```

**옵션 B: 카테고리 활성화 원하는 경우**
```bash
# Tests 파일 복사 후 수동 편집
cp tests/backend/app/service_agent/tools/infrastructure_tool.py \
   backend/app/service_agent/tools/infrastructure_tool.py

# 편집기로 열어서 42-52줄 주석 제거
# "convenience_store": "CS2",
# "hospital": "HP8",
# "pharmacy": "PM9",
# "cafe": "CE7",
# "bank": "BK9",
```

**⚠️ 주의:**
- 카테고리 활성화 시 카카오 API 호출량 증가
- API 쿼터 확인 필요

### 2.4 Diff 확인 (참고용)

```bash
# 두 파일 차이점 확인
diff -u backend/app/service_agent/tools/infrastructure_tool.py.backup \
        backend/app/service_agent/tools/infrastructure_tool.py | head -100
```

---

## 🔀 Phase 3: real_estate_search_tool.py 병합 (30분)

### 3.1 파일 비교 분석

**Backend (352줄):**
```python
async def search(self, query: str, params: Dict[str, Any] = None):
    params = params or {}

    # 파라미터 추출
    region = params.get('region') or self._extract_region(query)
    property_type = params.get('property_type')
    # ... 나머지 파라미터
```

**Tests (411줄, +59줄):**
```python
async def search(self, query: str, params: Dict[str, Any] = None):
    params = params or {}

    # 파라미터 추출
    property_name = params.get('property_name')  # ✅ 신규 파라미터!
    region = params.get('region') or self._extract_region(query)
    property_type = params.get('property_type')
    # ... 나머지 파라미터

    logger.info(
        f"Real estate search - name: {property_name}, region: {region}, ..."
    )
```

**주요 차이점:**
- Tests: **property_name 파라미터 추가** ✅
- 부동산 이름으로 직접 검색 가능 (예: "래미안아파트")
- 로그 메시지에 property_name 추가

### 3.2 병합 전략

**원칙: Tests 파일 우선 (사용자 지시) ⭐**

**병합 결과:**
- ✅ Tests 파일 채택 (411줄, property_name 기능 포함)
- ✅ 부동산 이름 직접 검색 기능 추가

### 3.3 실행 명령

```bash
# 백업 (선택 사항)
cp backend/app/service_agent/tools/real_estate_search_tool.py \
   backend/app/service_agent/tools/real_estate_search_tool.py.backup

# Tests 버전으로 교체
cp tests/backend/app/service_agent/tools/real_estate_search_tool.py \
   backend/app/service_agent/tools/real_estate_search_tool.py
```

**검증:**
```bash
wc -l backend/app/service_agent/tools/real_estate_search_tool.py
# 예상 출력: 411

# property_name 파라미터 존재 확인
grep "property_name = params.get" backend/app/service_agent/tools/real_estate_search_tool.py
# 예상 출력: property_name = params.get('property_name')
```

---

## 📝 Phase 4: __init__.py 업데이트 (30분)

### 4.1 현재 __init__.py 분석

**Backend 현재 상태:**
```python
# backend/app/service_agent/tools/__init__.py

from .market_data_tool import MarketDataTool
from .loan_data_tool import LoanDataTool

# Placeholder classes (곧 제거 예정)
class LegalSearchTool:
    """Placeholder for LegalSearchTool"""
    pass

class LoanProductTool:
    """Placeholder for LoanProductTool"""
    pass

# 분석 도구들
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool, PolicyType

__all__ = [
    "LegalSearchTool",  # Placeholder
    "LoanProductTool",  # Placeholder
    "MarketDataTool",
    "ContractAnalysisTool",
    "MarketAnalysisTool",
    "ROICalculatorTool",
    "LoanSimulatorTool",
    "PolicyMatcherTool",
    "PolicyType"
]
```

### 4.2 업데이트 후 __init__.py

**새로운 버전:**
```python
# backend/app/service_agent/tools/__init__.py

"""
Tools Package
에이전트가 사용하는 도구 모음
"""

# =========================================================================
# 기존 Tools
# =========================================================================

from .market_data_tool import MarketDataTool
from .loan_data_tool import LoanDataTool

# 분석 도구들
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool, PolicyType

# =========================================================================
# 신규 Tools (chatbot_execute 병합)
# =========================================================================

# Legal Search (SQLite + FAISS)
from .legal_search_tool import LegalSearch

# 공공데이터 API Tools
from .building_registry_tool import BuildingRegistryTool

# Infrastructure Tool (카카오 API)
from .infrastructure_tool import InfrastructureTool

# 부동산 용어 사전
from .realestate_terminology import RealEstateTerminology

# Real Estate Search (PostgreSQL)
from .real_estate_search_tool import RealEstateSearchTool

# =========================================================================
# Backward Compatibility Aliases
# =========================================================================

# LegalSearch 기본 이름
LegalSearchTool = LegalSearch

# 기존 HybridLegalSearch도 import 가능하게 유지
try:
    from .hybrid_legal_search import HybridLegalSearch
except ImportError:
    HybridLegalSearch = None

# =========================================================================
# Exports
# =========================================================================

__all__ = [
    # 기존 도구
    "MarketDataTool",
    "LoanDataTool",

    # 분석 도구
    "ContractAnalysisTool",
    "MarketAnalysisTool",
    "ROICalculatorTool",
    "LoanSimulatorTool",
    "PolicyMatcherTool",
    "PolicyType",

    # 신규 도구 (chatbot_execute)
    "LegalSearch",
    "LegalSearchTool",  # Alias
    "BuildingRegistryTool",
    "InfrastructureTool",
    "RealEstateTerminology",
    "RealEstateSearchTool",

    # Backward compatibility
    "HybridLegalSearch",
]
```

### 4.3 주요 변경 사항

**1. 신규 Imports 추가:**
- `LegalSearch` (legal_search_tool.py)
- `BuildingRegistryTool` (building_registry_tool.py)
- `InfrastructureTool` (infrastructure_tool.py)
- `RealEstateTerminology` (realestate_terminology.py)
- `RealEstateSearchTool` (real_estate_search_tool.py)

**2. Alias 생성:**
```python
LegalSearchTool = LegalSearch  # 이름 통일
```

**3. Backward Compatibility:**
```python
# 기존 HybridLegalSearch도 import 가능
from .hybrid_legal_search import HybridLegalSearch
```

**4. Placeholder 제거:**
```python
# ❌ 제거됨
class LegalSearchTool:
    """Placeholder for LegalSearchTool"""
    pass
```

### 4.4 실행 방법

**방법 1: 직접 편집 (권장)**
```bash
# 편집기로 열기
code backend/app/service_agent/tools/__init__.py
# 또는
vim backend/app/service_agent/tools/__init__.py

# 위 "업데이트 후 __init__.py" 내용으로 교체
```

**방법 2: 스크립트로 생성**
```bash
# 새로운 __init__.py 생성
cat > backend/app/service_agent/tools/__init__.py << 'EOF'
# (위 "업데이트 후 __init__.py" 내용 붙여넣기)
EOF
```

### 4.5 검증

**Import 테스트:**
```bash
cd backend
python -c "
from app.service_agent.tools import (
    LegalSearch,
    LegalSearchTool,
    BuildingRegistryTool,
    InfrastructureTool,
    RealEstateTerminology,
    RealEstateSearchTool,
    HybridLegalSearch
)
print('✅ All imports successful')
print(f'LegalSearch: {LegalSearch}')
print(f'LegalSearchTool == LegalSearch: {LegalSearchTool == LegalSearch}')
print(f'BuildingRegistryTool: {BuildingRegistryTool}')
print(f'InfrastructureTool: {InfrastructureTool}')
print(f'RealEstateTerminology: {RealEstateTerminology}')
print(f'HybridLegalSearch: {HybridLegalSearch}')
"
```

**예상 출력:**
```
✅ All imports successful
LegalSearch: <class 'app.service_agent.tools.legal_search_tool.LegalSearch'>
LegalSearchTool == LegalSearch: True
BuildingRegistryTool: <class 'app.service_agent.tools.building_registry_tool.BuildingRegistryTool'>
InfrastructureTool: <class 'app.service_agent.tools.infrastructure_tool.InfrastructureTool'>
RealEstateTerminology: <class 'app.service_agent.tools.realestate_terminology.RealEstateTerminology'>
HybridLegalSearch: <class 'app.service_agent.tools.hybrid_legal_search.HybridLegalSearch'>
```

---

## ✅ 작업 1 완료 체크리스트

### Phase 1: 신규 Tools 복사
- [ ] building_registry_tool.py 복사 완료 (459줄)
- [ ] legal_search_tool.py 복사 완료 (693줄)
- [ ] realestate_terminology.py 복사 완료 (402줄)

### Phase 2: infrastructure_tool.py 병합
- [ ] Tests 버전으로 교체 완료 (530줄)
- [ ] geocode_address 메서드 존재 확인
- [ ] (선택) 카테고리 활성화 검토

### Phase 3: real_estate_search_tool.py 병합
- [ ] Tests 버전으로 교체 완료 (411줄)
- [ ] property_name 파라미터 존재 확인

### Phase 4: __init__.py 업데이트
- [ ] 신규 imports 추가
- [ ] Alias 생성 (LegalSearchTool)
- [ ] Backward compatibility 확인
- [ ] Import 테스트 성공

### 최종 검증
- [ ] 5개 파일 모두 backend/에 존재
- [ ] __init__.py import 테스트 통과
- [ ] 에러 없음

---

## 🎯 다음 단계

작업 1 완료 후:
→ **작업 2: Agents & Foundation 병합** 진행

---

## 📊 예상 소요 시간

| Phase | 작업 | 시간 |
|-------|------|------|
| Phase 1 | 신규 Tools 복사 | 30분 |
| Phase 2 | infrastructure_tool.py 병합 | 45분 |
| Phase 3 | real_estate_search_tool.py 병합 | 30분 |
| Phase 4 | __init__.py 업데이트 | 30분 |
| **총계** | | **2시간 15분** |

---

## 🔧 문제 해결

### 문제 1: Import 실패

**증상:**
```python
ImportError: cannot import name 'LegalSearch' from 'app.service_agent.tools'
```

**해결:**
1. __init__.py에 import 문 확인
2. legal_search_tool.py 파일 존재 확인
3. 클래스 이름 확인 (LegalSearch)

### 문제 2: Circular Import

**증상:**
```python
ImportError: cannot import name 'X' from partially initialized module
```

**해결:**
1. __init__.py의 import 순서 변경
2. Lazy import 사용 검토

### 문제 3: 파일 권한 오류

**증상:**
```bash
cp: cannot create regular file: Permission denied
```

**해결:**
```bash
# 관리자 권한으로 실행 (Windows)
# 또는 파일 권한 확인
ls -l backend/app/service_agent/tools/
```

---

**문서 버전**: 1.0
**작성 완료일**: 2025-10-30
**다음 단계**: 작업 2 - Agents & Foundation 병합
