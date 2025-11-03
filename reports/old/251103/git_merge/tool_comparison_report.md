# Tool 비교 분석 보고서
## 작성일: 2025-10-23

---

## 📊 Tool 파일 현황 비교

### 1. **현재 존재하는 Tool 파일** (실제 파일시스템)

#### 📁 위치: `backend\app\service_agent\tools\`

| No | 파일명 | 상태 | 용도 |
|----|--------|------|------|
| 1 | `analysis_tools.py` | ✅ 존재 | 분석 도구 모음 |
| 2 | `contract_analysis_tool.py` | ✅ 존재 | 계약서 분석 |
| 3 | `loan_simulator_tool.py` | ✅ 존재 | 대출 시뮬레이터 |
| 4 | `roi_calculator_tool.py` | ✅ 존재 | ROI 계산기 |
| 5 | `market_analysis_tool.py` | ✅ 존재 | 시장 분석 |
| 6 | `lease_contract_generator_tool.py` | ✅ 존재 | 임대차계약서 생성 |
| 7 | `market_data_tool.py` | ✅ 존재 | 시장 데이터 |
| 8 | `real_estate_search_tool.py` | ✅ 존재 | 부동산 검색 |
| 9 | `loan_data_tool.py` | ✅ 존재 | 대출 데이터 |
| 10 | `infrastructure_tool.py` | ✅ 존재 | 인프라 분석 |
| 11 | `policy_matcher_tool.py` | ✅ 존재 | 정책 매칭 |
| 12 | `hybrid_legal_search.py` | ✅ 존재 | 하이브리드 법률 검색 |

---

### 2. **LJM 파일에서 요구하는 Tool** (intent_analysis_LJM.txt)

| 카테고리 | 요구 Tool 파일 | 실제 존재 | 상태 |
|----------|---------------|----------|------|
| TERM_DEFINITION | `legal_search_tool.py` | ❌ | **없음** (hybrid_legal_search.py로 대체 가능) |
| LEGAL_INQUIRY | `legal_search_tool.py` | ❌ | **없음** (hybrid_legal_search.py로 대체 가능) |
| CONTRACT_PROCEDURE | `contract_step_tool.py` | ❌ | **없음** |
| LOAN_SEARCH | `loan_data_tool.py` | ✅ | 존재 |
| LOAN_COMPARISON | `loan_simulator_tool.py` | ✅ | 존재 |
| BUILDING_REGISTRY | `building_registry_tool.py` | ❌ | **없음** |
| INFRASTRUCTURE_ANALYSIS | `infrastructure_tool.py` | ✅ | 존재 |
| MARKET_INQUIRY | `market_analysis_tool.py` | ✅ | 존재 |
| PRICE_EVALUATION | `market_analysis_tool.py` | ✅ | 존재 (동일 툴 사용) |
| PROPERTY_SEARCH | `real_estate_search_tool.py` | ✅ | 존재 |
| PROPERTY_RECOMMENDATION | `real_estate_search_tool.py` | ✅ | 존재 (동일 툴 사용) |
| ROI_CALCULATION | `roi_calculator_tool.py` | ✅ | 존재 |
| CONTRACT_ANALYSIS | `contract_analysis_tool.py` | ✅ | 존재 |
| POLICY_INQUIRY | `policy_matcher_tool.py` | ✅ | 존재 |
| HOUSING_APPLICATION | `housing_application_tool.py` | ❌ | **없음** |
| CONTRACT_CREATION | `lease_contract_generator_tool.py` | ✅ | 존재 |

---

## 🔍 상세 분석 결과

### ✅ **일치하는 Tool** (11개)
1. `loan_data_tool.py` - LOAN_SEARCH
2. `loan_simulator_tool.py` - LOAN_COMPARISON
3. `infrastructure_tool.py` - INFRASTRUCTURE_ANALYSIS
4. `market_analysis_tool.py` - MARKET_INQUIRY, PRICE_EVALUATION
5. `real_estate_search_tool.py` - PROPERTY_SEARCH, PROPERTY_RECOMMENDATION
6. `roi_calculator_tool.py` - ROI_CALCULATION
7. `contract_analysis_tool.py` - CONTRACT_ANALYSIS
8. `policy_matcher_tool.py` - POLICY_INQUIRY
9. `lease_contract_generator_tool.py` - CONTRACT_CREATION

### ❌ **누락된 Tool** (5개)
1. **`legal_search_tool.py`**
   - 용도: TERM_DEFINITION, LEGAL_INQUIRY
   - 대체: `hybrid_legal_search.py` 존재 (이름 변경 또는 리팩토링 필요)

2. **`contract_step_tool.py`**
   - 용도: CONTRACT_PROCEDURE (계약 절차 안내)
   - 상태: 완전 누락, 신규 개발 필요

3. **`building_registry_tool.py`**
   - 용도: BUILDING_REGISTRY (건축물대장 조회)
   - 상태: 완전 누락, 신규 개발 필요

4. **`housing_application_tool.py`**
   - 용도: HOUSING_APPLICATION (청약 자격 확인)
   - 상태: 완전 누락, 신규 개발 필요

### 🔄 **이름 불일치 Tool** (1개)
- `hybrid_legal_search.py` → `legal_search_tool.py`로 이름 변경 고려

### 📌 **추가 존재 Tool** (2개)
- `analysis_tools.py` - 분석 도구 모음 (유틸리티)
- `market_data_tool.py` - 시장 데이터 (market_analysis_tool과 별개)

---

## 💡 해결 방안

### 1. **즉시 해결 가능** (이름 변경)
```python
# hybrid_legal_search.py → legal_search_tool.py 로 이름 변경
# 또는 import 시 alias 사용
from .hybrid_legal_search import HybridLegalSearch as LegalSearchTool
```

### 2. **Placeholder로 임시 해결**
```python
# 누락된 Tool들에 대한 Placeholder 클래스 생성
class ContractStepTool:
    """계약 절차 안내 Tool - 구현 예정"""
    def execute(self, **kwargs):
        return {"status": "not_implemented", "message": "계약 절차 안내 기능은 준비 중입니다."}

class BuildingRegistryTool:
    """건축물대장 조회 Tool - 구현 예정"""
    def execute(self, **kwargs):
        return {"status": "not_implemented", "message": "건축물대장 조회 기능은 준비 중입니다."}

class HousingApplicationTool:
    """청약 자격 확인 Tool - 구현 예정"""
    def execute(self, **kwargs):
        return {"status": "not_implemented", "message": "청약 자격 확인 기능은 준비 중입니다."}
```

### 3. **카테고리별 Tool 매핑 수정**
```python
# 실제 존재하는 Tool로 매핑 조정
TOOL_MAPPING = {
    "TERM_DEFINITION": "hybrid_legal_search",  # legal_search_tool 대신
    "LEGAL_INQUIRY": "hybrid_legal_search",     # legal_search_tool 대신
    "CONTRACT_PROCEDURE": None,  # 구현 필요
    "LOAN_SEARCH": "loan_data_tool",
    "LOAN_COMPARISON": "loan_simulator_tool",
    "BUILDING_REGISTRY": None,  # 구현 필요
    "INFRASTRUCTURE_ANALYSIS": "infrastructure_tool",
    "MARKET_INQUIRY": "market_analysis_tool",
    "PRICE_EVALUATION": "market_analysis_tool",
    "PROPERTY_SEARCH": "real_estate_search_tool",
    "PROPERTY_RECOMMENDATION": "real_estate_search_tool",
    "ROI_CALCULATION": "roi_calculator_tool",
    "CONTRACT_ANALYSIS": "contract_analysis_tool",
    "POLICY_INQUIRY": "policy_matcher_tool",
    "HOUSING_APPLICATION": None,  # 구현 필요
    "CONTRACT_CREATION": "lease_contract_generator_tool",
}
```

---

## 📋 권장 조치 사항

### 🚨 **우선순위 1: 필수 조치**
1. **legal_search_tool 문제 해결**
   - Option A: `hybrid_legal_search.py` → `legal_search_tool.py` 이름 변경
   - Option B: import alias 사용
   - Option C: intent_analysis_LJM.txt 수정 (hybrid_legal_search로 변경)

### ⚠️ **우선순위 2: 단기 조치**
1. **누락 Tool Placeholder 생성**
   - contract_step_tool.py
   - building_registry_tool.py
   - housing_application_tool.py

2. **__init__.py 업데이트**
   - 새로운 Tool들 import 추가
   - __all__ 리스트 업데이트

### 📝 **우선순위 3: 장기 계획**
1. **누락 Tool 실제 구현**
   - 계약 절차 안내 기능
   - 건축물대장 조회 API 연동
   - 청약 자격 확인 로직

---

## 🎯 결론

### 현재 상태 평가
- **11/16개 Tool 존재** (68.75% 준비)
- **5개 Tool 누락** (31.25% 미구현)
- **1개 Tool 이름 불일치**

### 병합 가능 여부
- ✅ **조건부 가능**
  - legal_search_tool 이름 문제 해결 후
  - 누락 Tool에 대한 Placeholder 생성 후
  - 또는 intent_analysis 파일에서 실제 존재하는 Tool명으로 수정

### 추천 방안
1. **즉시 실행**: `hybrid_legal_search.py`를 활용하도록 매핑 수정
2. **Placeholder 생성**: 누락된 3개 Tool에 대한 임시 클래스 생성
3. **점진적 구현**: 실제 기능은 추후 개발

---

**작성자**: Claude Assistant
**검토일**: 2025-10-23
**상태**: Tool 비교 완료 ⚠️