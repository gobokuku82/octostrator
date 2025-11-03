# Validation & Compliance Tools 구현 계획서

**작성일**: 2025-10-26
**대상**: DocumentExecutor 확장 - 임대차 계약서 검증 도구
**목적**: 계약서 생성 시 필수 정보 검증 및 법률 준수 확인

---

## 📋 목차

1. [개요](#개요)
2. [현재 상황 분석](#현재-상황-분석)
3. [요구사항 정의](#요구사항-정의)
4. [Tool 설계](#tool-설계)
5. [구현 계획](#구현-계획)
6. [DocumentExecutor 통합](#documentexecutor-통합)
7. [Frontend 연동](#frontend-연동)
8. [테스트 계획](#테스트-계획)
9. [참고 자료](#참고-자료)

---

## 개요

### 배경

현재 DocumentExecutor는 Mock 기반으로 동작하며, 계약서 생성 시 다음 문제가 있음:

1. **필수 정보 누락 가능성**: 사용자가 입력하지 않은 필수 필드 체크 없음
2. **법률 요구사항 미검증**: 임대차보호법, 전월세신고제 등 법적 요구사항 확인 없음
3. **위험 조항 미검토**: 불공정 조항, 임차인 보호 조항 누락 여부 확인 없음
4. **데이터 정확성 미보장**: 입력 데이터 포맷, 범위 검증 없음

### 목표

**LeaseContractValidationTool**과 **LeaseContractComplianceTool**을 구현하여:

- ✅ 계약서 필수 정보 완전성 보장
- ✅ 법률 준수 자동 확인
- ✅ 위험 조항 사전 경고
- ✅ 사용자 경험 개선 (HITL 시점에 검증 결과 제공)

### 적용 범위

- **Phase 1**: ValidationTool 구현 (Week 1-2)
- **Phase 2**: ComplianceTool 구현 (Week 3-4)
- **Phase 3**: Frontend 연동 (Week 5-6)
- **Phase 4**: LLM 통합 및 고도화 (Week 7-8)

---

## 현재 상황 분석

### DocumentExecutor 현재 워크플로우

```
Planning → Aggregate (HITL) → Generate
```

**문제점**:
1. Planning: Mock 키워드 추출만 수행
2. Aggregate: HITL 승인만 요청, 검증 없음
3. Generate: Mock 포맷팅만 수행, 완전성 체크 없음

### 기존 도구 확인

```bash
backend/app/service_agent/tools/
├── lease_contract_generator_tool.py  # ✅ 존재 (DOCX 생성)
├── hybrid_legal_search.py            # ✅ 존재 (법률 검색)
├── real_estate_search_tool.py        # ✅ 존재 (매물 검색)
└── market_data_tool.py               # ✅ 존재 (시장 데이터)
```

**LeaseContractGeneratorTool 분석**:
- DOCX 템플릿 기반 계약서 생성
- 현재 DocumentExecutor와 미연동 상태
- 필드 검증 로직 없음

### 법률 요구사항 조사

#### 1. 주택임대차보호법 (필수 정보)

**필수 포함 사항**:
- 임대인/임차인 정보 (이름, 주민등록번호, 주소, 연락처)
- 임대 목적물 (주소, 면적, 구조)
- 임대차 기간 (시작일, 종료일)
- 차임 (보증금, 월세)
- 특약사항 (관리비, 수선의무 등)

**제한 사항**:
- 최소 임대 기간: 2년 (단기임대 예외)
- 묵시적 갱신 고지 필요
- 계약갱신청구권 명시

#### 2. 전월세 신고제 (2021.6.1 시행)

**신고 대상**:
- 보증금 6천만원 초과 또는
- 월세 30만원 초과

**신고 정보**:
- 임대차 계약 체결일로부터 30일 이내
- 임대인과 임차인 공동 신고
- 신고 누락 시 과태료 (최대 100만원)

#### 3. 확정일자 안내

**필수 안내 사항**:
- 확정일자 필요성
- 취득 방법 (주민센터, 인터넷)
- 대항력 및 우선변제권 설명

#### 4. 불공정 조항 체크

**금지 조항**:
- 임차인에게 과도한 수선의무 부과
- 부당한 계약해지 조건
- 보증금 반환 지연 조항
- 일방적인 차임 증액 조항

---

## 요구사항 정의

### 기능 요구사항

#### FR1: 필수 정보 검증 (ValidationTool)

| ID | 검증 항목 | 우선순위 | 설명 |
|----|----------|---------|------|
| FR1.1 | 당사자 정보 검증 | P0 | 임대인/임차인 이름, 연락처, 주소 필수 |
| FR1.2 | 목적물 정보 검증 | P0 | 주소, 면적, 구조 필수 |
| FR1.3 | 계약 조건 검증 | P0 | 기간, 보증금, 월세 필수 |
| FR1.4 | 데이터 포맷 검증 | P1 | 전화번호, 주소, 날짜 형식 |
| FR1.5 | 데이터 범위 검증 | P1 | 금액 음수 체크, 날짜 순서 등 |

#### FR2: 법률 준수 확인 (ComplianceTool)

| ID | 검증 항목 | 우선순위 | 설명 |
|----|----------|---------|------|
| FR2.1 | 임대 기간 확인 | P0 | 2년 미만 계약 경고 |
| FR2.2 | 전월세 신고제 확인 | P0 | 신고 대상 여부 판단 및 안내 |
| FR2.3 | 확정일자 안내 | P1 | 확정일자 필요성 설명 |
| FR2.4 | 묵시적 갱신 안내 | P1 | 계약갱신청구권 설명 |
| FR2.5 | 불공정 조항 탐지 | P2 | LLM 기반 조항 분석 |

#### FR3: 검증 결과 제공

| ID | 기능 | 우선순위 | 설명 |
|----|------|---------|------|
| FR3.1 | 누락 필드 목록 | P0 | 입력 필요 필드 리스트 |
| FR3.2 | 경고 메시지 | P0 | 법률 위반 가능성 경고 |
| FR3.3 | 권장 사항 | P1 | 추가 안내사항 제공 |
| FR3.4 | 심각도 표시 | P1 | Error / Warning / Info 구분 |

### 비기능 요구사항

| ID | 요구사항 | 목표 |
|----|---------|------|
| NFR1 | 응답 시간 | < 2초 (검증 1회당) |
| NFR2 | 정확도 | 99% (필수 필드 검증) |
| NFR3 | 확장성 | 새로운 검증 규칙 쉽게 추가 가능 |
| NFR4 | 유지보수성 | 법률 변경 시 설정 파일만 수정 |
| NFR5 | 로깅 | 모든 검증 결과 로그 기록 |

---

## Tool 설계

### 1. LeaseContractValidationTool

#### 클래스 구조

```python
from typing import Dict, Any, List
from app.service_agent.tools.base_tool import BaseTool

class LeaseContractValidationTool(BaseTool):
    """
    임대차 계약서 필수 정보 검증 도구

    기능:
    - 필수 필드 누락 체크
    - 데이터 포맷 검증
    - 데이터 범위 검증
    - 논리적 일관성 검증
    """

    def __init__(self):
        super().__init__(
            name="lease_contract_validation",
            description="Validate lease contract required fields and data formats"
        )
        self.validation_rules = self._load_validation_rules()

    def validate(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        계약서 데이터 검증

        Args:
            contract_data: 계약서 데이터 딕셔너리

        Returns:
            {
                "is_valid": bool,
                "missing_fields": List[str],
                "format_errors": List[Dict],
                "range_errors": List[Dict],
                "warnings": List[str],
                "severity": "error" | "warning" | "ok"
            }
        """
        pass

    def _validate_required_fields(self, data: Dict) -> List[str]:
        """필수 필드 누락 체크"""
        pass

    def _validate_formats(self, data: Dict) -> List[Dict]:
        """데이터 포맷 검증 (전화번호, 주소, 날짜 등)"""
        pass

    def _validate_ranges(self, data: Dict) -> List[Dict]:
        """데이터 범위 검증 (금액, 날짜 순서 등)"""
        pass

    def _validate_consistency(self, data: Dict) -> List[Dict]:
        """논리적 일관성 검증"""
        pass

    def _load_validation_rules(self) -> Dict:
        """검증 규칙 로드 (JSON 파일에서)"""
        pass
```

#### 검증 규칙 설정 파일

```json
// backend/app/service_agent/tools/configs/lease_validation_rules.json
{
  "required_fields": {
    "lessor": {
      "name": {
        "required": true,
        "type": "string",
        "min_length": 2,
        "display_name": "임대인 이름"
      },
      "phone": {
        "required": true,
        "type": "phone",
        "pattern": "^01[0-9]-[0-9]{3,4}-[0-9]{4}$",
        "display_name": "임대인 연락처"
      },
      "address": {
        "required": true,
        "type": "string",
        "display_name": "임대인 주소"
      }
    },
    "lessee": {
      "name": {
        "required": true,
        "type": "string",
        "min_length": 2,
        "display_name": "임차인 이름"
      },
      "phone": {
        "required": true,
        "type": "phone",
        "display_name": "임차인 연락처"
      },
      "address": {
        "required": true,
        "type": "string",
        "display_name": "임차인 주소"
      }
    },
    "property": {
      "address": {
        "required": true,
        "type": "string",
        "display_name": "임대 목적물 주소"
      },
      "area": {
        "required": true,
        "type": "number",
        "min": 0,
        "display_name": "전용면적(㎡)"
      },
      "structure": {
        "required": false,
        "type": "string",
        "display_name": "건물 구조"
      }
    },
    "contract": {
      "start_date": {
        "required": true,
        "type": "date",
        "display_name": "계약 시작일"
      },
      "end_date": {
        "required": true,
        "type": "date",
        "display_name": "계약 종료일"
      },
      "deposit": {
        "required": true,
        "type": "number",
        "min": 0,
        "display_name": "보증금"
      },
      "monthly_rent": {
        "required": true,
        "type": "number",
        "min": 0,
        "display_name": "월세"
      }
    }
  },
  "business_rules": {
    "min_contract_period_days": 730,
    "max_deposit": 1000000000,
    "max_monthly_rent": 100000000
  }
}
```

#### 검증 결과 예시

```python
{
    "is_valid": False,
    "missing_fields": [
        {
            "field": "lessor.phone",
            "display_name": "임대인 연락처",
            "severity": "error"
        },
        {
            "field": "property.area",
            "display_name": "전용면적(㎡)",
            "severity": "error"
        }
    ],
    "format_errors": [
        {
            "field": "lessee.phone",
            "value": "01012345678",
            "expected": "010-1234-5678 형식",
            "severity": "warning"
        }
    ],
    "range_errors": [
        {
            "field": "contract.end_date",
            "issue": "계약 종료일이 시작일보다 빠름",
            "severity": "error"
        }
    ],
    "warnings": [
        "계약 기간이 2년 미만입니다. 임대차보호법에 따라 2년이 보장됩니다."
    ],
    "severity": "error",  # error | warning | ok
    "summary": {
        "total_errors": 3,
        "total_warnings": 2,
        "completion_rate": 0.78  # 78% 완성
    }
}
```

### 2. LeaseContractComplianceTool

#### 클래스 구조

```python
from typing import Dict, Any, List
from app.service_agent.tools.base_tool import BaseTool

class LeaseContractComplianceTool(BaseTool):
    """
    임대차 계약서 법률 준수 확인 도구

    기능:
    - 주택임대차보호법 준수 확인
    - 전월세 신고제 대상 판단
    - 확정일자 안내
    - 불공정 조항 탐지
    """

    def __init__(self, llm_context=None):
        super().__init__(
            name="lease_contract_compliance",
            description="Check lease contract compliance with Korean housing laws"
        )
        self.llm_context = llm_context
        self.compliance_rules = self._load_compliance_rules()

    def check_compliance(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        법률 준수 확인

        Args:
            contract_data: 계약서 데이터 딕셔너리

        Returns:
            {
                "compliant": bool,
                "lease_period_check": Dict,
                "reporting_requirement": Dict,
                "guaranteed_date_info": Dict,
                "unfair_terms": List[Dict],
                "recommendations": List[str]
            }
        """
        pass

    def _check_lease_period(self, data: Dict) -> Dict:
        """임대 기간 확인 (최소 2년)"""
        pass

    def _check_reporting_requirement(self, data: Dict) -> Dict:
        """전월세 신고제 대상 여부 확인"""
        pass

    def _generate_guaranteed_date_info(self, data: Dict) -> Dict:
        """확정일자 안내 생성"""
        pass

    def _detect_unfair_terms(self, contract_text: str) -> List[Dict]:
        """불공정 조항 탐지 (LLM 활용)"""
        pass

    def _load_compliance_rules(self) -> Dict:
        """준수 규칙 로드"""
        pass
```

#### 준수 규칙 설정 파일

```json
// backend/app/service_agent/tools/configs/lease_compliance_rules.json
{
  "housing_lease_protection_act": {
    "min_lease_period_days": 730,
    "min_lease_period_description": "주택임대차보호법에 따라 최소 2년 보장",
    "renewal_request_right": {
      "enabled": true,
      "max_times": 1,
      "description": "임차인은 1회에 한해 계약갱신청구권 보유"
    },
    "rent_increase_limit": {
      "max_percentage": 5,
      "description": "차임 증액 시 연 5% 이내"
    }
  },
  "reporting_requirement": {
    "deposit_threshold": 60000000,
    "monthly_rent_threshold": 300000,
    "deadline_days": 30,
    "penalty_max": 1000000,
    "description": "보증금 6천만원 초과 또는 월세 30만원 초과 시 신고 필요"
  },
  "guaranteed_date": {
    "required_for_priority": true,
    "where_to_get": [
      "주민센터 방문",
      "인터넷 등기소 (www.iros.go.kr)",
      "구청 민원실"
    ],
    "benefits": [
      "대항력 취득",
      "우선변제권 확보"
    ]
  },
  "unfair_terms_keywords": [
    "임차인 전체 수선의무",
    "일방적 계약해지",
    "보증금 반환 지연",
    "과도한 위약금",
    "부당한 차임 증액"
  ]
}
```

#### 준수 확인 결과 예시

```python
{
    "compliant": False,
    "lease_period_check": {
        "period_days": 365,
        "meets_requirement": False,
        "message": "계약 기간이 1년입니다. 주택임대차보호법에 따라 2년이 보장됩니다.",
        "severity": "warning",
        "legal_protection": "임차인이 원할 경우 2년 거주 가능"
    },
    "reporting_requirement": {
        "required": True,
        "reason": "보증금 7,000만원으로 신고 대상",
        "deadline": "계약일로부터 30일 이내",
        "how_to": "온라인: 부동산거래관리시스템 / 오프라인: 주민센터",
        "penalty": "미신고 시 최대 100만원 과태료",
        "severity": "error"
    },
    "guaranteed_date_info": {
        "recommended": True,
        "benefits": [
            "대항력: 집주인이 바뀌어도 계약 유지",
            "우선변제권: 경매 시 보증금 우선 변제"
        ],
        "how_to_get": [
            "주민센터 방문 신청",
            "인터넷 등기소 (www.iros.go.kr)",
            "구청 민원실"
        ],
        "severity": "info"
    },
    "unfair_terms": [
        {
            "term": "임차인이 모든 수선비용을 부담한다",
            "issue": "임대인의 수선의무를 과도하게 임차인에게 부과",
            "recommendation": "통상적인 관리는 임차인, 주요 수선은 임대인 부담으로 수정",
            "severity": "warning",
            "legal_basis": "주택임대차보호법 제20조"
        }
    ],
    "recommendations": [
        "계약 기간을 2년으로 연장하시는 것을 권장합니다.",
        "전월세 신고를 30일 이내에 완료하셔야 합니다.",
        "확정일자를 취득하여 우선변제권을 확보하시기 바랍니다.",
        "불공정 조항 1건이 발견되었습니다. 수정을 권장합니다."
    ],
    "summary": {
        "total_errors": 1,
        "total_warnings": 2,
        "total_info": 1
    }
}
```

---

## 구현 계획

### Phase 1: LeaseContractValidationTool 구현 (Week 1-2)

#### Week 1: 기본 구조 및 필수 필드 검증

**Task 1.1: 프로젝트 구조 생성** (3시간)
```
backend/app/service_agent/tools/
├── lease_contract_validation_tool.py       # 신규
├── configs/
│   └── lease_validation_rules.json         # 신규
└── tests/
    └── test_lease_validation_tool.py       # 신규
```

**Task 1.2: BaseTool 상속 및 초기화** (2시간)
- ValidationTool 클래스 정의
- 검증 규칙 JSON 로드
- Logger 설정

**Task 1.3: 필수 필드 검증 구현** (4시간)
```python
def _validate_required_fields(self, data: Dict) -> List[str]:
    """
    필수 필드 누락 체크

    Logic:
    1. validation_rules에서 required=true 필드 목록 추출
    2. data에서 각 필드 존재 여부 확인
    3. 누락된 필드 리스트 반환
    """
    missing = []
    rules = self.validation_rules["required_fields"]

    # Lessor 검증
    for field, rule in rules["lessor"].items():
        if rule["required"]:
            value = data.get("lessor", {}).get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                missing.append({
                    "field": f"lessor.{field}",
                    "display_name": rule["display_name"],
                    "severity": "error"
                })

    # Lessee 검증
    # Property 검증
    # Contract 검증

    return missing
```

**Task 1.4: 데이터 포맷 검증 구현** (4시간)
```python
def _validate_formats(self, data: Dict) -> List[Dict]:
    """
    데이터 포맷 검증

    검증 항목:
    - 전화번호: 010-1234-5678 형식
    - 날짜: YYYY-MM-DD 형식
    - 이메일: xxx@xxx.xxx 형식
    """
    import re
    from datetime import datetime

    errors = []

    # 전화번호 검증
    phone_pattern = r"^01[0-9]-[0-9]{3,4}-[0-9]{4}$"
    lessor_phone = data.get("lessor", {}).get("phone", "")
    if lessor_phone and not re.match(phone_pattern, lessor_phone):
        errors.append({
            "field": "lessor.phone",
            "value": lessor_phone,
            "expected": "010-1234-5678 형식",
            "severity": "warning"
        })

    # 날짜 검증
    start_date = data.get("contract", {}).get("start_date", "")
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        errors.append({
            "field": "contract.start_date",
            "value": start_date,
            "expected": "YYYY-MM-DD 형식",
            "severity": "error"
        })

    return errors
```

**Task 1.5: 단위 테스트 작성** (3시간)
```python
# tests/test_lease_validation_tool.py
import pytest
from app.service_agent.tools.lease_contract_validation_tool import LeaseContractValidationTool

def test_validate_missing_required_fields():
    tool = LeaseContractValidationTool()

    # 필수 필드 누락 케이스
    contract_data = {
        "lessor": {"name": "홍길동"},
        # phone, address 누락
        "lessee": {},
        "property": {},
        "contract": {}
    }

    result = tool.validate(contract_data)

    assert result["is_valid"] == False
    assert len(result["missing_fields"]) > 0
    assert any(f["field"] == "lessor.phone" for f in result["missing_fields"])

def test_validate_format_errors():
    tool = LeaseContractValidationTool()

    contract_data = {
        "lessor": {
            "name": "홍길동",
            "phone": "01012345678",  # 잘못된 형식
            "address": "서울시"
        }
    }

    result = tool.validate(contract_data)
    assert len(result["format_errors"]) > 0
```

#### Week 2: 범위 검증 및 통합

**Task 2.1: 데이터 범위 검증 구현** (4시간)
```python
def _validate_ranges(self, data: Dict) -> List[Dict]:
    """
    데이터 범위 검증

    검증 항목:
    - 금액: 음수 체크, 최대값 체크
    - 날짜 순서: 종료일 > 시작일
    - 면적: 0 이상
    """
    from datetime import datetime

    errors = []

    # 금액 검증
    deposit = data.get("contract", {}).get("deposit", 0)
    if deposit < 0:
        errors.append({
            "field": "contract.deposit",
            "issue": "보증금은 0 이상이어야 합니다",
            "severity": "error"
        })

    max_deposit = self.validation_rules["business_rules"]["max_deposit"]
    if deposit > max_deposit:
        errors.append({
            "field": "contract.deposit",
            "issue": f"보증금이 {max_deposit:,}원을 초과합니다",
            "severity": "warning"
        })

    # 날짜 순서 검증
    start_date_str = data.get("contract", {}).get("start_date")
    end_date_str = data.get("contract", {}).get("end_date")

    if start_date_str and end_date_str:
        try:
            start = datetime.strptime(start_date_str, "%Y-%m-%d")
            end = datetime.strptime(end_date_str, "%Y-%m-%d")

            if end <= start:
                errors.append({
                    "field": "contract.end_date",
                    "issue": "계약 종료일이 시작일보다 빠르거나 같습니다",
                    "severity": "error"
                })
        except ValueError:
            pass  # 포맷 검증에서 이미 처리

    return errors
```

**Task 2.2: 통합 validate() 메서드 완성** (3시간)
```python
def validate(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
    """전체 검증 실행"""
    logger.info("🔍 Starting contract validation")

    # 각 검증 실행
    missing_fields = self._validate_required_fields(contract_data)
    format_errors = self._validate_formats(contract_data)
    range_errors = self._validate_ranges(contract_data)

    # 심각도 결정
    has_errors = len(missing_fields) > 0 or \
                 any(e["severity"] == "error" for e in format_errors) or \
                 any(e["severity"] == "error" for e in range_errors)

    severity = "error" if has_errors else \
               ("warning" if len(format_errors) > 0 or len(range_errors) > 0 else "ok")

    # 완성도 계산
    total_required = self._count_required_fields()
    provided = total_required - len(missing_fields)
    completion_rate = provided / total_required if total_required > 0 else 0

    result = {
        "is_valid": not has_errors,
        "missing_fields": missing_fields,
        "format_errors": format_errors,
        "range_errors": range_errors,
        "severity": severity,
        "summary": {
            "total_errors": len([e for e in missing_fields + format_errors + range_errors
                                 if e.get("severity") == "error"]),
            "total_warnings": len([e for e in format_errors + range_errors
                                   if e.get("severity") == "warning"]),
            "completion_rate": round(completion_rate, 2)
        }
    }

    logger.info(f"✅ Validation complete: {result['severity']} "
                f"({result['summary']['total_errors']} errors, "
                f"{result['summary']['total_warnings']} warnings)")

    return result
```

**Task 2.3: 통합 테스트** (3시간)

**Task 2.4: 문서화** (2시간)
- Docstring 완성
- README 작성
- 사용 예시 추가

---

### Phase 2: LeaseContractComplianceTool 구현 (Week 3-4)

#### Week 3: 법률 규칙 기반 검증

**Task 3.1: 프로젝트 구조 생성** (2시간)
```
backend/app/service_agent/tools/
├── lease_contract_compliance_tool.py       # 신규
├── configs/
│   └── lease_compliance_rules.json         # 신규
└── tests/
    └── test_lease_compliance_tool.py       # 신규
```

**Task 3.2: 임대 기간 확인 구현** (3시간)
```python
def _check_lease_period(self, data: Dict) -> Dict:
    """
    임대 기간 확인 (최소 2년)
    """
    from datetime import datetime

    start_date_str = data.get("contract", {}).get("start_date")
    end_date_str = data.get("contract", {}).get("end_date")

    if not start_date_str or not end_date_str:
        return {
            "period_days": None,
            "meets_requirement": None,
            "message": "계약 기간 정보 없음",
            "severity": "info"
        }

    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
        period_days = (end - start).days

        min_days = self.compliance_rules["housing_lease_protection_act"]["min_lease_period_days"]
        meets = period_days >= min_days

        if meets:
            message = f"계약 기간 {period_days}일로 법적 요건 충족"
            severity = "ok"
        else:
            message = (f"계약 기간이 {period_days}일입니다. "
                      "주택임대차보호법에 따라 2년이 보장됩니다.")
            severity = "warning"

        return {
            "period_days": period_days,
            "meets_requirement": meets,
            "message": message,
            "severity": severity,
            "legal_protection": "임차인이 원할 경우 2년 거주 가능" if not meets else None
        }
    except ValueError:
        return {
            "period_days": None,
            "meets_requirement": None,
            "message": "날짜 형식 오류",
            "severity": "error"
        }
```

**Task 3.3: 전월세 신고제 확인 구현** (4시간)
```python
def _check_reporting_requirement(self, data: Dict) -> Dict:
    """
    전월세 신고제 대상 여부 확인
    """
    deposit = data.get("contract", {}).get("deposit", 0)
    monthly_rent = data.get("contract", {}).get("monthly_rent", 0)

    rules = self.compliance_rules["reporting_requirement"]
    deposit_threshold = rules["deposit_threshold"]
    rent_threshold = rules["monthly_rent_threshold"]

    is_required = (deposit > deposit_threshold) or (monthly_rent > rent_threshold)

    if not is_required:
        return {
            "required": False,
            "reason": "신고 대상 아님",
            "severity": "ok"
        }

    reasons = []
    if deposit > deposit_threshold:
        reasons.append(f"보증금 {deposit:,}원으로 신고 대상 (기준: {deposit_threshold:,}원)")
    if monthly_rent > rent_threshold:
        reasons.append(f"월세 {monthly_rent:,}원으로 신고 대상 (기준: {rent_threshold:,}원)")

    return {
        "required": True,
        "reason": ", ".join(reasons),
        "deadline": f"계약일로부터 {rules['deadline_days']}일 이내",
        "how_to": "온라인: 부동산거래관리시스템 (http://rtms.molit.go.kr) / 오프라인: 주민센터",
        "penalty": f"미신고 시 최대 {rules['penalty_max']:,}원 과태료",
        "severity": "error"
    }
```

**Task 3.4: 확정일자 안내 생성** (2시간)

**Task 3.5: 단위 테스트** (3시간)

#### Week 4: LLM 기반 불공정 조항 탐지

**Task 4.1: LLM 프롬프트 설계** (4시간)

```python
UNFAIR_TERMS_DETECTION_PROMPT = """
당신은 대한민국 주택임대차 계약서 전문가입니다.
다음 계약서 조항을 분석하여 불공정하거나 법률에 위배될 가능성이 있는 조항을 찾아주세요.

# 계약서 조항
{contract_text}

# 확인 사항
1. 임차인에게 과도한 수선의무를 부과하는 조항
2. 부당한 계약해지 조건
3. 보증금 반환을 부당하게 지연시키는 조항
4. 일방적인 차임 증액 조항
5. 기타 임차인에게 불리한 조항

# 출력 형식 (JSON)
{{
  "unfair_terms": [
    {{
      "term": "문제가 되는 조항 원문",
      "issue": "문제점 설명",
      "recommendation": "수정 권장 사항",
      "severity": "warning" 또는 "error",
      "legal_basis": "관련 법률 조항"
    }}
  ]
}}

불공정 조항이 없으면 빈 리스트를 반환하세요.
"""
```

**Task 4.2: 불공정 조항 탐지 구현** (5시간)
```python
def _detect_unfair_terms(self, contract_text: str) -> List[Dict]:
    """
    불공정 조항 탐지 (LLM 활용)
    """
    if not self.llm_context:
        logger.warning("LLM context not available, skipping unfair terms detection")
        return []

    try:
        from app.service_agent.llm_manager import LLMService
        llm_service = LLMService(llm_context=self.llm_context)

        prompt = UNFAIR_TERMS_DETECTION_PROMPT.format(contract_text=contract_text)

        response = llm_service.generate(
            prompt=prompt,
            temperature=0.3,  # 낮은 temperature로 일관성 확보
            max_tokens=2000
        )

        import json
        result = json.loads(response)
        unfair_terms = result.get("unfair_terms", [])

        logger.info(f"🔍 Detected {len(unfair_terms)} potential unfair terms")
        return unfair_terms

    except Exception as e:
        logger.error(f"Failed to detect unfair terms: {e}", exc_info=True)
        return []
```

**Task 4.3: 통합 check_compliance() 완성** (4시간)

**Task 4.4: 통합 테스트 및 문서화** (3시간)

---

## DocumentExecutor 통합

### 새로운 워크플로우

```
Planning
  → Validation (ValidationTool 실행)
    → Aggregate (HITL - 검증 결과 + 폼 입력)
      → Compliance (ComplianceTool 실행)
        → Generate (최종 문서 생성)
          → Final Review (HITL - 최종 승인)
```

### 통합 코드 예시

```python
# document_executor.py 수정

class DocumentExecutor:
    def __init__(self, llm_context=None, checkpointer=None):
        self.llm_context = llm_context
        self.checkpointer = checkpointer

        # ✅ Tools 초기화
        self._initialize_tools()

    def _initialize_tools(self):
        """Initialize validation and compliance tools"""
        try:
            from app.service_agent.tools.lease_contract_validation_tool import LeaseContractValidationTool
            from app.service_agent.tools.lease_contract_compliance_tool import LeaseContractComplianceTool

            self.validation_tool = LeaseContractValidationTool()
            self.compliance_tool = LeaseContractComplianceTool(llm_context=self.llm_context)

            logger.info("✅ Validation and Compliance tools initialized")
        except Exception as e:
            logger.error(f"Failed to initialize tools: {e}")
            self.validation_tool = None
            self.compliance_tool = None

    def build_workflow(self):
        """Build workflow with validation and compliance nodes"""
        workflow = StateGraph(MainSupervisorState)

        # Add nodes
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("validation", self.validation_node)      # ✅ NEW
        workflow.add_node("aggregate", self.aggregate_node)
        workflow.add_node("compliance", self.compliance_node)      # ✅ NEW
        workflow.add_node("generate", self.generate_node)
        workflow.add_node("final_review", self.final_review_node)  # ✅ NEW

        # Define edges
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "validation")               # ✅ NEW
        workflow.add_edge("validation", "aggregate")
        workflow.add_edge("aggregate", "compliance")              # ✅ NEW
        workflow.add_edge("compliance", "generate")
        workflow.add_edge("generate", "final_review")             # ✅ NEW
        workflow.add_edge("final_review", END)

        return workflow.compile(checkpointer=self.checkpointer)

    # ==================== New Nodes ====================

    def validation_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Validation Node: Check required fields and data formats
        """
        logger.info("🔍 Validation node: Checking contract data")

        if not self.validation_tool:
            logger.warning("ValidationTool not available, skipping validation")
            return {"workflow_status": "running"}

        # Extract contract data from state
        contract_data = self._extract_contract_data(state)

        # Run validation
        validation_result = self.validation_tool.validate(contract_data)

        logger.info(f"Validation complete: {validation_result['severity']}")

        return {
            "validation_result": validation_result,
            "workflow_status": "running"
        }

    def compliance_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Compliance Node: Check legal requirements
        """
        logger.info("⚖️ Compliance node: Checking legal requirements")

        if not self.compliance_tool:
            logger.warning("ComplianceTool not available, skipping compliance check")
            return {"workflow_status": "running"}

        contract_data = self._extract_contract_data(state)

        # Run compliance check
        compliance_result = self.compliance_tool.check_compliance(contract_data)

        logger.info(f"Compliance check complete")

        return {
            "compliance_result": compliance_result,
            "workflow_status": "running"
        }

    def final_review_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Final Review Node: HITL for final approval
        """
        logger.info("📋 Final Review: Requesting final approval")

        final_document = state.get("final_document", "")
        validation_result = state.get("validation_result", {})
        compliance_result = state.get("compliance_result", {})

        # Prepare interrupt value
        interrupt_value = {
            "final_document": final_document,
            "validation_summary": validation_result.get("summary", {}),
            "compliance_summary": compliance_result.get("summary", {}),
            "message": "최종 검토 후 승인해주세요.",
            "options": {
                "approve": "승인 및 계약서 생성",
                "modify": "수정 필요",
                "reject": "취소"
            },
            "_metadata": {
                "interrupted_by": "final_review",
                "interrupt_type": "final_approval"
            }
        }

        # HITL interrupt
        user_decision = interrupt(interrupt_value)

        return {
            "final_approval": user_decision,
            "workflow_status": "completed"
        }

    def _extract_contract_data(self, state: MainSupervisorState) -> Dict[str, Any]:
        """Extract contract data from state"""
        # TODO: Implement based on actual state structure
        return state.get("contract_data", {})
```

---

## Frontend 연동

### 검증 결과 UI 표시

#### 1. Aggregate HITL 화면 (validation_result 표시)

```typescript
// frontend/src/components/DocumentReview.tsx

interface ValidationResult {
  is_valid: boolean;
  missing_fields: Array<{
    field: string;
    display_name: string;
    severity: 'error' | 'warning';
  }>;
  format_errors: Array<any>;
  range_errors: Array<any>;
  summary: {
    total_errors: number;
    total_warnings: number;
    completion_rate: number;
  };
}

function DocumentReviewPanel({ validationResult }: { validationResult: ValidationResult }) {
  return (
    <div className="validation-panel">
      <h3>검증 결과</h3>

      {/* 완성도 표시 */}
      <ProgressBar
        value={validationResult.summary.completion_rate * 100}
        label={`${Math.round(validationResult.summary.completion_rate * 100)}% 완성`}
      />

      {/* 에러 목록 */}
      {validationResult.missing_fields.length > 0 && (
        <div className="error-section">
          <h4>❌ 필수 입력 항목 ({validationResult.missing_fields.length})</h4>
          <ul>
            {validationResult.missing_fields.map((field, idx) => (
              <li key={idx} className={`severity-${field.severity}`}>
                <strong>{field.display_name}</strong>을(를) 입력해주세요
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 경고 목록 */}
      {validationResult.format_errors.length > 0 && (
        <div className="warning-section">
          <h4>⚠️ 형식 확인 필요 ({validationResult.format_errors.length})</h4>
          {/* ... */}
        </div>
      )}
    </div>
  );
}
```

#### 2. Compliance 결과 표시

```typescript
interface ComplianceResult {
  compliant: boolean;
  reporting_requirement: {
    required: boolean;
    reason: string;
    deadline: string;
    how_to: string;
    penalty: string;
  };
  unfair_terms: Array<{
    term: string;
    issue: string;
    recommendation: string;
  }>;
}

function CompliancePanel({ complianceResult }: { complianceResult: ComplianceResult }) {
  return (
    <div className="compliance-panel">
      <h3>법률 준수 확인</h3>

      {/* 전월세 신고제 */}
      {complianceResult.reporting_requirement.required && (
        <Alert severity="error">
          <strong>전월세 신고 필요</strong>
          <p>{complianceResult.reporting_requirement.reason}</p>
          <p>기한: {complianceResult.reporting_requirement.deadline}</p>
          <p>방법: {complianceResult.reporting_requirement.how_to}</p>
        </Alert>
      )}

      {/* 불공정 조항 */}
      {complianceResult.unfair_terms.length > 0 && (
        <div className="unfair-terms">
          <h4>⚠️ 불공정 조항 검토 ({complianceResult.unfair_terms.length})</h4>
          {complianceResult.unfair_terms.map((term, idx) => (
            <Card key={idx}>
              <p><strong>조항:</strong> {term.term}</p>
              <p><strong>문제점:</strong> {term.issue}</p>
              <p><strong>권장:</strong> {term.recommendation}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 테스트 계획

### Unit Tests

```python
# tests/test_lease_validation_tool.py

class TestLeaseContractValidationTool:

    def test_all_fields_valid(self):
        """모든 필드가 올바른 경우"""
        tool = LeaseContractValidationTool()
        data = {
            "lessor": {
                "name": "홍길동",
                "phone": "010-1234-5678",
                "address": "서울시 강남구"
            },
            "lessee": {
                "name": "김철수",
                "phone": "010-9876-5432",
                "address": "서울시 서초구"
            },
            "property": {
                "address": "서울시 강남구 테헤란로 123",
                "area": 84.5
            },
            "contract": {
                "start_date": "2025-01-01",
                "end_date": "2027-01-01",
                "deposit": 50000000,
                "monthly_rent": 0
            }
        }

        result = tool.validate(data)
        assert result["is_valid"] == True
        assert result["severity"] == "ok"

    def test_missing_required_fields(self):
        """필수 필드 누락"""
        tool = LeaseContractValidationTool()
        data = {
            "lessor": {"name": "홍길동"},  # phone, address 누락
            "lessee": {},
            "property": {},
            "contract": {}
        }

        result = tool.validate(data)
        assert result["is_valid"] == False
        assert len(result["missing_fields"]) > 5

    def test_invalid_phone_format(self):
        """전화번호 형식 오류"""
        tool = LeaseContractValidationTool()
        data = {
            "lessor": {
                "name": "홍길동",
                "phone": "01012345678",  # 하이픈 없음
                "address": "서울"
            }
        }

        result = tool.validate(data)
        assert any(e["field"] == "lessor.phone" for e in result["format_errors"])

    def test_invalid_date_range(self):
        """날짜 순서 오류"""
        tool = LeaseContractValidationTool()
        data = {
            "contract": {
                "start_date": "2025-01-01",
                "end_date": "2024-12-31",  # 종료일이 시작일보다 빠름
                "deposit": 10000000,
                "monthly_rent": 0
            }
        }

        result = tool.validate(data)
        assert any(e["field"] == "contract.end_date" for e in result["range_errors"])
```

### Integration Tests

```python
# tests/test_document_executor_integration.py

class TestDocumentExecutorIntegration:

    @pytest.mark.asyncio
    async def test_validation_workflow(self):
        """Validation 노드 통합 테스트"""
        executor = DocumentExecutor()

        state = {
            "query": "임대차 계약서 작성",
            "contract_data": {
                "lessor": {"name": "홍길동"},
                # 필수 필드 일부 누락
            }
        }

        result = executor.validation_node(state)

        assert "validation_result" in result
        assert result["validation_result"]["is_valid"] == False

    @pytest.mark.asyncio
    async def test_compliance_workflow(self):
        """Compliance 노드 통합 테스트"""
        executor = DocumentExecutor(llm_context=mock_llm_context)

        state = {
            "contract_data": {
                "contract": {
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",  # 1년 (2년 미만)
                    "deposit": 70000000,       # 신고 대상
                    "monthly_rent": 0
                }
            }
        }

        result = executor.compliance_node(state)

        assert "compliance_result" in result
        assert result["compliance_result"]["reporting_requirement"]["required"] == True
        assert result["compliance_result"]["lease_period_check"]["meets_requirement"] == False
```

---

## 참고 자료

### 법률 문서

1. **주택임대차보호법**
   - 국가법령정보센터: https://www.law.go.kr/법령/주택임대차보호법
   - 주요 조항: 제4조(임대차기간), 제6조(계약갱신요구권), 제7조(차임증감청구권)

2. **민간임대주택에 관한 특별법**
   - 전월세 신고제 관련 조항

3. **부동산 거래신고 등에 관한 법률**
   - 전월세 신고 절차 및 벌칙

### 기술 문서

1. **LangGraph 0.6 Documentation**
   - interrupt() 패턴: https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/

2. **Pydantic Validation**
   - 데이터 검증 라이브러리: https://docs.pydantic.dev/

3. **Python-docx**
   - DOCX 생성 및 수정: https://python-docx.readthedocs.io/

### 개발 가이드

1. **DocumentExecutor 리팩토링 계획서**
   - `reports/docs_agent/DOCUMENT_EXECUTOR_REFACTORING_PLAN_251026.md`

2. **HITL 분석 및 솔루션**
   - `reports/docs_agent/LANGGRAPH_06_HITL_ANALYSIS_AND_SOLUTIONS_251025.md`

---

## 예상 일정 요약

| Phase | 작업 내용 | 기간 | 예상 시간 |
|-------|---------|------|----------|
| Phase 1 | ValidationTool 구현 | Week 1-2 | 28시간 |
| Phase 2 | ComplianceTool 구현 | Week 3-4 | 28시간 |
| Phase 3 | Frontend 연동 | Week 5-6 | 20시간 |
| Phase 4 | LLM 통합 및 고도화 | Week 7-8 | 24시간 |
| **Total** | | **8주** | **100시간** |

---

**작성자**: Holmes AI Team
**검토자**: N/A
**승인**: Pending
**관련 문서**: DOCUMENT_EXECUTOR_REFACTORING_PLAN_251026.md
