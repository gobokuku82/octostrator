# PolicyType Enum JSON 직렬화 오류 수정 계획서

**작성일:** 2025-10-18
**계획서 버전:** 1.0
**예상 완료일:** 2025-10-18 (즉시 수정 가능)

---

## 1. 개요

### 목표
PolicyType Enum의 JSON 직렬화 오류를 수정하여 정책 매칭 기능 정상화

### 접근 방식
**하이브리드 전략:** 즉각 복구 (Phase 1) + 근본 해결 (Phase 2)

### 예상 시간
- **Phase 1 (즉각 복구):** 10분
- **Phase 2 (근본 해결):** 15분
- **Phase 3 (검증):** 20분
- **총 소요 시간:** 45분

---

## 2. Phase 1: 즉각 복구 (P0 - Critical)

### 목표
서비스 즉시 복구 - JSON 직렬화 핸들러 추가

### 수정 대상
1. `llm_service.py` - LLM 응답 생성 복구
2. `ws_manager.py` - WebSocket 전송 복구

---

### 2.1. llm_service.py 수정

**파일:** `backend/app/service_agent/llm_manager/llm_service.py`
**위치:** Line 418-441 (_safe_json_dumps 메서드)

#### 수정 전

```python
def _safe_json_dumps(self, obj: Any) -> str:
    """
    객체를 안전하게 JSON 문자열로 변환 (datetime 처리 포함)
    """
    from datetime import datetime
    import json

    def json_serial(obj):
        """datetime 등 기본 JSON 직렬화 불가능한 객체 처리"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    try:
        return json.dumps(obj, default=json_serial, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to serialize object to JSON: {e}")
        return str(obj)
```

#### 수정 후

```python
def _safe_json_dumps(self, obj: Any) -> str:
    """
    객체를 안전하게 JSON 문자열로 변환 (datetime, Enum 처리 포함)
    """
    from datetime import datetime
    from enum import Enum
    import json

    def json_serial(obj):
        """datetime, Enum 등 기본 JSON 직렬화 불가능한 객체 처리"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value  # ← Enum 처리 추가
        raise TypeError(f"Type {type(obj)} not serializable")

    try:
        return json.dumps(obj, default=json_serial, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to serialize object to JSON: {e}")
        return str(obj)
```

#### 변경 사항
- `from enum import Enum` import 추가 (Line 2)
- `json_serial` 함수에 Enum 처리 로직 추가 (Line 10-11)
- Docstring 업데이트 (Line 3)

#### 검증 방법

```python
# 수정 후 테스트
from app.service_agent.llm_manager.llm_service import LLMService
from app.service_agent.tools.policy_matcher_tool import PolicyType

llm = LLMService()

test_data = {
    "policy": {
        "type": PolicyType.LOAN_SUPPORT,
        "name": "디딤돌대출"
    }
}

result = llm._safe_json_dumps(test_data)
print(result)

# 예상 출력:
# {
#   "policy": {
#     "type": "대출지원",
#     "name": "디딤돌대출"
#   }
# }
```

---

### 2.2. ws_manager.py 수정

**파일:** `backend/app/api/ws_manager.py`
**위치:** Line 61-80 (_serialize_datetimes 메서드)

#### 수정 전

```python
def _serialize_datetimes(self, obj: Any) -> Any:
    """
    재귀적으로 datetime 객체를 ISO 형식 문자열로 변환

    Args:
        obj: 변환할 객체

    Returns:
        변환된 객체 (datetime은 문자열로 변환됨)
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: self._serialize_datetimes(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [self._serialize_datetimes(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(self._serialize_datetimes(item) for item in obj)
    else:
        return obj
```

#### 수정 후

```python
def _serialize_datetimes(self, obj: Any) -> Any:
    """
    재귀적으로 datetime, Enum 객체를 직렬화 가능한 형태로 변환

    Args:
        obj: 변환할 객체

    Returns:
        변환된 객체 (datetime은 ISO 문자열, Enum은 value로 변환됨)
    """
    from datetime import datetime
    from enum import Enum

    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value  # ← Enum 처리 추가
    elif isinstance(obj, dict):
        return {key: self._serialize_datetimes(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [self._serialize_datetimes(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(self._serialize_datetimes(item) for item in obj)
    else:
        return obj
```

#### 변경 사항
- 메서드 최상단에 import 추가 (Line 10-11)
- Enum 타입 체크 및 `.value` 반환 추가 (Line 15-16)
- Docstring 업데이트 (Line 3, 8)

#### 검증 방법

```python
# 수정 후 테스트
from app.api.ws_manager import get_connection_manager
from app.service_agent.tools.policy_matcher_tool import PolicyType

manager = get_connection_manager()

test_message = {
    "type": "policy_result",
    "data": {
        "policy_type": PolicyType.LOAN_SUPPORT
    }
}

serialized = manager._serialize_datetimes(test_message)
print(serialized)

# 예상 출력:
# {
#   "type": "policy_result",
#   "data": {
#     "policy_type": "대출지원"
#   }
# }
```

---

## 3. Phase 2: 근본 해결 (P1 - High Priority)

### 목표
근본 원인 제거 - Enum을 애초에 `.value` 형태로 저장

### 수정 대상
`policy_matcher_tool.py` - 정책 데이터베이스 초기화

---

### 3.1. policy_matcher_tool.py 수정

**파일:** `backend/app/service_agent/tools/policy_matcher_tool.py`
**위치:** Line 44-292 (_initialize_policy_database 메서드)

#### 수정 전 (예시 - Line 48-73)

```python
{
    "id": "디딤돌대출",
    "name": "디딤돌대출",
    "type": PolicyType.LOAN_SUPPORT,  # ← Enum 객체
    "provider": "주택도시기금",
    "target": ["무주택자", "신혼부부", "청년"],
    ...
}
```

#### 수정 후

```python
{
    "id": "디딤돌대출",
    "name": "디딤돌대출",
    "type": PolicyType.LOAN_SUPPORT.value,  # ← .value로 문자열 변환
    "provider": "주택도시기금",
    "target": ["무주택자", "신혼부부", "청년"],
    ...
}
```

#### 전체 수정 위치

모든 정책 딕셔너리에서 `"type": PolicyType.XXX` → `"type": PolicyType.XXX.value` 변경:

- Line 51: `PolicyType.LOAN_SUPPORT` → `PolicyType.LOAN_SUPPORT.value`
- Line 78: `PolicyType.LOAN_SUPPORT` → `PolicyType.LOAN_SUPPORT.value`
- Line 102: `PolicyType.LOAN_SUPPORT` → `PolicyType.LOAN_SUPPORT.value`
- Line 129: `PolicyType.SUBSIDY` → `PolicyType.SUBSIDY.value`
- Line 150: `PolicyType.PUBLIC_HOUSING` → `PolicyType.PUBLIC_HOUSING.value`
- Line 172: `PolicyType.LOAN_SUPPORT` → `PolicyType.LOAN_SUPPORT.value`
- Line 195: `PolicyType.SPECIAL_SUPPLY` → `PolicyType.SPECIAL_SUPPLY.value`
- Line 218: `PolicyType.TAX_BENEFIT` → `PolicyType.TAX_BENEFIT.value`
- Line 237: `PolicyType.TAX_BENEFIT` → `PolicyType.TAX_BENEFIT.value`
- Line 257: `PolicyType.SPECIAL_SUPPLY` → `PolicyType.SPECIAL_SUPPLY.value`
- Line 276: `PolicyType.SPECIAL_SUPPLY` → `PolicyType.SPECIAL_SUPPLY.value`

**총 11개 위치**

#### 코드 사용처 수정

**Line 429 수정:**

```python
# 수정 전
if policy_types and policy["type"].value not in policy_types:
    continue

# 수정 후
if policy_types and policy["type"] not in policy_types:
    continue
```

**Line 647 수정:**

```python
# 수정 전
if policy["type"] == PolicyType.LOAN_SUPPORT:

# 수정 후
if policy["type"] == PolicyType.LOAN_SUPPORT.value:
```

**Line 655 수정:**

```python
# 수정 전
elif policy["type"] == PolicyType.SUBSIDY:

# 수정 후
elif policy["type"] == PolicyType.SUBSIDY.value:
```

**Line 663 수정:**

```python
# 수정 전
elif policy["type"] == PolicyType.SPECIAL_SUPPLY:

# 수정 후
elif policy["type"] == PolicyType.SPECIAL_SUPPLY.value:
```

**Line 703 수정:**

```python
# 수정 전
if policy["type"] == PolicyType.LOAN_SUPPORT:

# 수정 후
if policy["type"] == PolicyType.LOAN_SUPPORT.value:
```

**Line 750 수정:**

```python
# 수정 전
if policy["type"] == PolicyType.LOAN_SUPPORT:

# 수정 후
if policy["type"] == PolicyType.LOAN_SUPPORT.value:
```

**Line 752 수정:**

```python
# 수정 전
elif policy["type"] == PolicyType.SUBSIDY:

# 수정 후
elif policy["type"] == PolicyType.SUBSIDY.value:
```

**총 수정:** 11개 초기화 + 7개 비교 로직 = **18개 위치**

#### 검증 방법

```python
# 수정 후 테스트
from app.service_agent.tools.policy_matcher_tool import PolicyMatcherTool

matcher = PolicyMatcherTool()

# 초기화된 정책 확인
first_policy = matcher.policies[0]
print(f"Type: {type(first_policy['type'])}")  # <class 'str'>
print(f"Value: {first_policy['type']}")       # "대출지원"

# execute 실행
result = await matcher.execute({
    "age": 30,
    "annual_income": 50000000,
    "has_house": False
})

# 결과 확인
print(f"Matched type: {type(result['matched_policies'][0]['type'])}")  # <class 'str'>

# JSON 직렬화 확인
import json
json_str = json.dumps(result)
print("JSON serialization: SUCCESS")
```

---

## 4. Phase 3: 검증 및 테스트 (P2 - Medium Priority)

### 4.1. Unit Test 작성

**파일 생성:** `backend/tests/test_policy_enum_serialization.py`

```python
"""
PolicyType Enum JSON 직렬화 테스트
"""

import pytest
import json
from app.service_agent.tools.policy_matcher_tool import PolicyMatcherTool, PolicyType
from app.service_agent.llm_manager.llm_service import LLMService
from app.api.ws_manager import get_connection_manager


class TestPolicyEnumSerialization:
    """PolicyType Enum JSON 직렬화 테스트 모음"""

    def test_llm_service_enum_serialization(self):
        """LLMService가 Enum을 올바르게 직렬화하는지 테스트"""
        llm = LLMService()

        test_data = {
            "policy": {
                "type": PolicyType.LOAN_SUPPORT,
                "name": "테스트 정책"
            }
        }

        result = llm._safe_json_dumps(test_data)

        # 문자열로 변환되었는지 확인
        assert "대출지원" in result
        # Enum 타입명이 없는지 확인
        assert "PolicyType" not in result
        # 유효한 JSON인지 확인
        parsed = json.loads(result)
        assert parsed["policy"]["type"] == "대출지원"

    def test_ws_manager_enum_serialization(self):
        """WebSocket Manager가 Enum을 올바르게 직렬화하는지 테스트"""
        manager = get_connection_manager()

        test_message = {
            "type": "policy_result",
            "data": {
                "policy_type": PolicyType.SUBSIDY,
                "nested": {
                    "type": PolicyType.TAX_BENEFIT
                }
            }
        }

        serialized = manager._serialize_datetimes(test_message)

        # Enum이 문자열로 변환되었는지 확인
        assert isinstance(serialized["data"]["policy_type"], str)
        assert serialized["data"]["policy_type"] == "보조금"

        # 중첩된 Enum도 변환되었는지 확인
        assert isinstance(serialized["data"]["nested"]["type"], str)
        assert serialized["data"]["nested"]["type"] == "세제혜택"

    @pytest.mark.asyncio
    async def test_policy_matcher_tool_direct_string(self):
        """PolicyMatcherTool이 Enum.value를 직접 저장하는지 테스트"""
        matcher = PolicyMatcherTool()

        # 초기화된 정책 확인
        first_policy = matcher.policies[0]

        # type 필드가 문자열인지 확인
        assert isinstance(first_policy["type"], str)
        assert first_policy["type"] in [
            "대출지원", "세제혜택", "보조금", "공공주택", "특별공급"
        ]

    @pytest.mark.asyncio
    async def test_policy_matcher_e2e_json_serializable(self):
        """정책 매칭 전체 흐름에서 JSON 직렬화가 성공하는지 테스트"""
        matcher = PolicyMatcherTool()

        user_profile = {
            "age": 30,
            "annual_income": 50000000,
            "total_assets": 200000000,
            "has_house": False,
            "first_time_buyer": True,
        }

        result = await matcher.execute(user_profile)

        # 1. 매칭 결과가 있는지 확인
        assert result["status"] == "success"
        assert len(result["matched_policies"]) > 0

        # 2. 모든 policy의 type이 문자열인지 확인
        for policy in result["matched_policies"]:
            assert isinstance(policy["type"], str)

        # 3. JSON 직렬화가 성공하는지 확인
        json_str = json.dumps(result)
        assert len(json_str) > 0

        # 4. 역직렬화도 성공하는지 확인
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"

    def test_all_policy_types_serializable(self):
        """모든 PolicyType Enum 값이 직렬화 가능한지 테스트"""
        llm = LLMService()

        for policy_type in PolicyType:
            test_data = {"type": policy_type}

            result = llm._safe_json_dumps(test_data)

            # JSON 직렬화 성공 확인
            parsed = json.loads(result)
            assert isinstance(parsed["type"], str)
            assert parsed["type"] == policy_type.value
```

### 4.2. Integration Test

**파일 생성:** `backend/tests/test_policy_websocket_integration.py`

```python
"""
정책 매칭 → WebSocket 전송 통합 테스트
"""

import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.api.ws_manager import get_connection_manager
from app.service_agent.tools.policy_matcher_tool import PolicyMatcherTool


@pytest.mark.asyncio
async def test_policy_matcher_websocket_integration():
    """정책 매칭 결과가 WebSocket으로 정상 전송되는지 통합 테스트"""

    # 1. 정책 매칭 실행
    matcher = PolicyMatcherTool()

    user_profile = {
        "age": 32,
        "annual_income": 55000000,
        "has_house": False,
        "marriage_years": 2,
    }

    result = await matcher.execute(user_profile)

    # 2. WebSocket Manager로 직렬화
    manager = get_connection_manager()

    message = {
        "type": "policy_matching_result",
        "data": result
    }

    serialized = manager._serialize_datetimes(message)

    # 3. JSON 직렬화 성공 확인
    json_str = json.dumps(serialized)
    assert len(json_str) > 0

    # 4. 역직렬화하여 데이터 무결성 확인
    parsed = json.loads(json_str)
    assert parsed["type"] == "policy_matching_result"
    assert parsed["data"]["status"] == "success"
    assert len(parsed["data"]["matched_policies"]) > 0

    # 5. 모든 policy의 type이 문자열인지 확인
    for policy in parsed["data"]["matched_policies"]:
        assert isinstance(policy["type"], str)

    print("✅ Integration test passed: Policy → WebSocket serialization")
```

### 4.3. 테스트 실행 계획

```bash
# 1. Unit Test 실행
pytest backend/tests/test_policy_enum_serialization.py -v

# 2. Integration Test 실행
pytest backend/tests/test_policy_websocket_integration.py -v

# 3. 전체 테스트 실행
pytest backend/tests/ -v --cov=app.service_agent.tools.policy_matcher_tool

# 4. 특정 테스트만 실행
pytest backend/tests/test_policy_enum_serialization.py::TestPolicyEnumSerialization::test_llm_service_enum_serialization -v
```

---

## 5. 배포 계획

### 5.1. Phase 1 배포 (즉시)

**목표:** 서비스 즉시 복구

**체크리스트:**
- [ ] `llm_service.py` 수정
- [ ] `ws_manager.py` 수정
- [ ] 로컬 테스트 실행
- [ ] Git commit
- [ ] 서버 재시작
- [ ] 정책 매칭 기능 검증

**배포 커맨드:**
```bash
# 1. 수정 적용
git add backend/app/service_agent/llm_manager/llm_service.py
git add backend/app/api/ws_manager.py

# 2. Commit
git commit -m "Fix: Add Enum serialization handler for PolicyType

- Add Enum.value conversion in llm_service._safe_json_dumps
- Add Enum.value conversion in ws_manager._serialize_datetimes
- Fixes JSON serialization error for policy matching results
- Issue: PolicyType Enum was not JSON serializable

Severity: Critical
Priority: P0"

# 3. 서버 재시작
# (uvicorn 자동 재시작 또는 수동 재시작)

# 4. 검증
# - 정책 매칭 API 호출
# - WebSocket 메시지 수신 확인
```

---

### 5.2. Phase 2 배포 (1일 후)

**목표:** 근본 원인 제거

**체크리스트:**
- [ ] `policy_matcher_tool.py` 수정 (18개 위치)
- [ ] Unit Test 작성
- [ ] 로컬 테스트 실행
- [ ] Phase 1 수정과 호환성 확인
- [ ] Git commit
- [ ] 서버 재시작
- [ ] 전체 기능 검증

**배포 커맨드:**
```bash
# 1. 수정 적용
git add backend/app/service_agent/tools/policy_matcher_tool.py
git add backend/tests/test_policy_enum_serialization.py

# 2. Commit
git commit -m "Refactor: Store PolicyType as string instead of Enum

- Change all PolicyType.XXX to PolicyType.XXX.value in policy database
- Update policy type comparisons to use string values
- Add comprehensive unit tests for Enum serialization
- Removes root cause of JSON serialization error

Related: Previous commit (Enum serialization handler)
Priority: P1"

# 3. 테스트 실행
pytest backend/tests/test_policy_enum_serialization.py -v

# 4. 서버 재시작 및 검증
```

---

## 6. 롤백 계획

### Phase 1 롤백

만약 Phase 1 수정으로 문제가 발생한 경우:

```bash
# 1. 이전 commit으로 되돌리기
git revert HEAD

# 2. 또는 특정 파일만 되돌리기
git checkout HEAD~1 backend/app/service_agent/llm_manager/llm_service.py
git checkout HEAD~1 backend/app/api/ws_manager.py

# 3. 서버 재시작
```

### Phase 2 롤백

만약 Phase 2 수정으로 문제가 발생한 경우:

```bash
# 1. policy_matcher_tool.py만 되돌리기
git checkout HEAD~1 backend/app/service_agent/tools/policy_matcher_tool.py

# 2. 서버 재시작
```

**참고:** Phase 1과 Phase 2는 독립적이므로, Phase 2만 롤백해도 서비스는 정상 작동

---

## 7. 모니터링 계획

### 7.1. 즉시 확인 사항 (배포 후 5분 내)

```bash
# 1. 서버 로그 확인
tail -f backend/logs/app.log | grep -E "PolicyType|JSON|serialize"

# 2. 에러 로그 확인
tail -f backend/logs/app.log | grep -E "ERROR|Failed"

# 3. WebSocket 연결 확인
curl http://localhost:8000/api/health
```

### 7.2. 기능 검증 (배포 후 10분 내)

```bash
# 1. 정책 매칭 API 호출
curl -X POST http://localhost:8000/api/policy/match \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "annual_income": 50000000,
    "has_house": false
  }'

# 2. 응답 확인
# - status: "success"
# - matched_policies에 데이터 있음
# - type 필드가 문자열 ("대출지원" 등)

# 3. WebSocket 메시지 확인
# - 프론트엔드에서 정책 매칭 실행
# - 브라우저 개발자 도구 → Network → WS → Messages 확인
# - policy_matching_result 메시지 정상 수신 확인
```

### 7.3. 장기 모니터링 (배포 후 1주일)

**메트릭 수집:**
- 정책 매칭 요청 수
- JSON 직렬화 성공률
- WebSocket 전송 성공률
- 에러 발생 건수 (PolicyType 관련)

**알림 설정:**
- JSON 직렬화 실패 시 Slack 알림
- PolicyType 관련 에러 발생 시 이메일 알림

---

## 8. 체크리스트

### Phase 1: 즉각 복구

- [ ] `llm_service.py` 수정 완료
  - [ ] `from enum import Enum` import 추가
  - [ ] `json_serial` 함수에 Enum 처리 추가
  - [ ] Docstring 업데이트
- [ ] `ws_manager.py` 수정 완료
  - [ ] `from enum import Enum` import 추가
  - [ ] `_serialize_datetimes`에 Enum 처리 추가
  - [ ] Docstring 업데이트
- [ ] 로컬 테스트 성공
- [ ] Git commit 완료
- [ ] 서버 배포 완료
- [ ] 기능 검증 완료

### Phase 2: 근본 해결

- [ ] `policy_matcher_tool.py` 수정 완료
  - [ ] 11개 정책 초기화 위치 수정
  - [ ] 7개 비교 로직 수정
- [ ] Unit Test 작성 완료
  - [ ] `test_llm_service_enum_serialization`
  - [ ] `test_ws_manager_enum_serialization`
  - [ ] `test_policy_matcher_tool_direct_string`
  - [ ] `test_policy_matcher_e2e_json_serializable`
  - [ ] `test_all_policy_types_serializable`
- [ ] Integration Test 작성 완료
- [ ] 모든 테스트 통과
- [ ] Git commit 완료
- [ ] 서버 배포 완료
- [ ] 전체 기능 검증 완료

### Phase 3: 검증 및 모니터링

- [ ] 배포 후 즉시 확인 완료
- [ ] 기능 검증 완료
- [ ] 장기 모니터링 설정 완료
- [ ] 문서 업데이트 완료

---

## 9. 타임라인

| 시간 | Phase | 작업 | 담당 |
|-----|-------|------|------|
| T+0분 | Phase 1 | `llm_service.py` 수정 | 개발자 |
| T+5분 | Phase 1 | `ws_manager.py` 수정 | 개발자 |
| T+10분 | Phase 1 | 로컬 테스트 및 Commit | 개발자 |
| T+15분 | Phase 1 | 서버 배포 | DevOps |
| T+20분 | Phase 1 | 기능 검증 | QA |
| T+1일 | Phase 2 | `policy_matcher_tool.py` 수정 | 개발자 |
| T+1일 | Phase 2 | Unit/Integration Test 작성 | 개발자 |
| T+1일 | Phase 2 | 서버 배포 | DevOps |
| T+1주 | Phase 3 | 장기 모니터링 및 문서화 | Tech Lead |

---

## 10. 리스크 및 대응 방안

### 리스크 1: Phase 1 수정이 다른 Enum에 영향

**확률:** 낮음 (10%)
**영향:** 중간

**대응:**
- 현재 시스템에서 PolicyType 외 다른 Enum 사용 여부 확인
- 있다면 같은 방식으로 처리되므로 문제 없음
- 테스트 코드로 검증

### 리스크 2: Phase 2 수정 시 기존 코드 호환성 문제

**확률:** 중간 (30%)
**영향:** 높음

**대응:**
- Phase 1 수정이 이미 적용되어 있으므로 Enum/String 모두 처리 가능
- `.value` 비교 코드를 문자열 비교로 변경하여 일관성 유지
- 철저한 테스트로 검증

### 리스크 3: 성능 저하

**확률:** 매우 낮음 (5%)
**영향:** 낮음

**대응:**
- Enum `.value` 접근은 O(1) 연산
- JSON 직렬화 시 Enum 타입 체크도 O(1)
- 성능 영향 무시 가능
- 필요 시 프로파일링

---

## 11. 성공 기준

### Phase 1 성공 기준

✅ 다음 조건을 **모두** 만족해야 함:
1. 정책 매칭 API 호출 시 응답 성공
2. LLM 응답 생성 성공 (JSON 직렬화 오류 없음)
3. WebSocket 메시지 전송 성공
4. 프론트엔드에서 정책 매칭 결과 정상 표시
5. 서버 로그에 PolicyType 관련 에러 없음

### Phase 2 성공 기준

✅ 다음 조건을 **모두** 만족해야 함:
1. Phase 1 성공 기준 유지
2. 모든 Unit Test 통과
3. Integration Test 통과
4. `policy["type"]`이 문자열로 저장됨 (Enum 아님)
5. 코드 리뷰 승인

### 최종 성공 기준

✅ 다음 조건을 **모두** 만족해야 함:
1. Phase 1, Phase 2 성공 기준 모두 만족
2. 배포 후 1주일 동안 PolicyType 관련 에러 0건
3. 정책 매칭 기능 정상 작동률 99% 이상
4. 사용자 불편 신고 0건

---

## 12. 후속 조치

### 12.1. 문서 업데이트

- [ ] API 문서 업데이트 (정책 매칭 응답 스키마)
- [ ] 개발자 가이드 업데이트 (Enum 사용 가이드라인)
- [ ] 아키텍처 문서 업데이트 (JSON 직렬화 핸들러 설명)

### 12.2. 코드 개선

- [ ] 다른 Enum 타입도 같은 방식으로 처리 검토
- [ ] 공통 직렬화 유틸리티 함수 생성 고려
- [ ] Type Hint 강화 (Union[Enum, str] 등)

### 12.3. 프로세스 개선

- [ ] PR 체크리스트에 "Enum JSON 직렬화 확인" 항목 추가
- [ ] CI/CD에 JSON 직렬화 테스트 추가
- [ ] 코드 리뷰 가이드라인에 Enum 사용 규칙 추가

---

## 13. 연락처

**질문 및 문제 보고:**
- Tech Lead: [이름/이메일]
- Backend Developer: [이름/이메일]
- DevOps: [이름/이메일]

**긴급 상황:**
- Slack Channel: #backend-emergency
- On-call: [전화번호]

---

**계획서 작성:** Claude Code AI
**검토 필요:** Backend Team Lead
**승인 필요:** CTO
**예상 완료:** 2025-10-18 (당일)
