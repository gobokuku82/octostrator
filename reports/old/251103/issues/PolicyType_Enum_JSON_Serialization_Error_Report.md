# PolicyType Enum JSON 직렬화 오류 분석 보고서

**작성일:** 2025-10-18
**보고서 버전:** 1.0
**심각도:** 🔴 Critical (서비스 장애)

---

## 1. 요약 (Executive Summary)

### 문제
`PolicyType` Enum 객체가 JSON 직렬화되지 않아 다음 3가지 오류 발생:
1. `Object of type PolicyType is not JSON serializable`
2. `Failed to send message to session-...: Object of type PolicyType is not JSON serializable`
3. `Failed to serialize object to JSON: Type <enum 'PolicyType'> not serializable`

### 영향
- **LLM Service**: `aggregated_results`를 JSON으로 변환할 때 실패 → 최종 응답 생성 불가
- **WebSocket**: 정책 매칭 결과를 프론트엔드로 전송 시 실패 → 사용자 UI 업데이트 불가
- **전체 서비스**: 정책 매칭 기능 완전 중단

### 해결 방안
3가지 파일 수정 필요:
1. `policy_matcher_tool.py`: Enum → `.value` 변환 (근본 해결)
2. `llm_service.py`: Enum 직렬화 핸들러 추가 (방어적 처리)
3. `ws_manager.py`: Enum 직렬화 핸들러 추가 (방어적 처리)

---

## 2. 문제 발생 경로 (Error Flow)

```
[1] PolicyMatcherTool.execute()
    ↓
    policy["type"] = PolicyType.LOAN_SUPPORT (Enum 객체 그대로 저장)
    ↓
[2] LLMService.generate_final_response()
    ↓
    aggregated_results = {"policy_matcher": {..., "type": PolicyType.LOAN_SUPPORT}}
    ↓
[3] LLMService._safe_json_dumps(aggregated_results)
    ↓
    json.dumps(obj, default=json_serial, ...)
    ↓
    json_serial 함수: datetime만 처리, Enum은 TypeError 발생 ❌
    ↓
[4] WebSocket.send_message()
    ↓
    ws_manager._serialize_datetimes(message)
    ↓
    Enum 처리 로직 없음, JSON 직렬화 실패 ❌
```

---

## 3. 상세 분석

### 3.1. PolicyType Enum 정의

**파일:** `backend/app/service_agent/tools/policy_matcher_tool.py`
**위치:** Line 14-21

```python
class PolicyType(Enum):
    """정책 유형"""
    LOAN_SUPPORT = "대출지원"
    TAX_BENEFIT = "세제혜택"
    SUBSIDY = "보조금"
    PUBLIC_HOUSING = "공공주택"
    SPECIAL_SUPPLY = "특별공급"
```

**문제점:**
- Enum 객체는 Python 기본 JSON 직렬화 대상이 아님
- `json.dumps()`는 `str`, `int`, `float`, `bool`, `None`, `list`, `dict`만 지원
- Enum은 커스텀 핸들러 없이는 `TypeError` 발생

---

### 3.2. PolicyMatcherTool에서 Enum 사용

**파일:** `backend/app/service_agent/tools/policy_matcher_tool.py`
**위치:** Line 44-292 (_initialize_policy_database 메서드)

**Enum이 직접 저장되는 예시:**
```python
# Line 51
{
    "id": "디딤돌대출",
    "name": "디딤돌대출",
    "type": PolicyType.LOAN_SUPPORT,  # ← Enum 객체 그대로!
    ...
}
```

**코드에서는 `.value` 접근 시도:**
```python
# Line 429
if policy_types and policy["type"].value not in policy_types:
    continue

# Line 824 (테스트 코드)
print(f"유형: {policy['type'].value}")
```

**문제:**
- 내부적으로 `.value` 접근은 성공
- 하지만 JSON 직렬화 시점에는 **Enum 객체 자체**가 전달됨
- 결과: JSON 변환 불가

---

### 3.3. LLMService에서 JSON 직렬화 실패

**파일:** `backend/app/service_agent/llm_manager/llm_service.py`
**위치:** Line 418-441 (_safe_json_dumps 메서드)

**현재 구현:**
```python
def _safe_json_dumps(self, obj: Any) -> str:
    from datetime import datetime
    import json

    def json_serial(obj):
        """datetime 등 기본 JSON 직렬화 불가능한 객체 처리"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")  # ← Enum은 여기서 실패!

    try:
        return json.dumps(obj, default=json_serial, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to serialize object to JSON: {e}")
        return str(obj)
```

**문제:**
- `json_serial` 함수가 `datetime`만 처리
- `Enum` 객체가 들어오면 `TypeError` 발생
- `except` 블록으로 fallback되어 `str(obj)` 반환 → 데이터 손실

**영향:**
- Line 373: `aggregated_json = self._safe_json_dumps(aggregated_results)[:4000]`
- `aggregated_results`에 PolicyType Enum이 포함되어 있으면 직렬화 실패
- LLM에 전달되는 JSON이 손상됨
- 최종 응답 품질 저하 또는 생성 불가

---

### 3.4. WebSocket 전송 실패

**파일:** `backend/app/api/ws_manager.py`
**위치:** Line 61-80 (_serialize_datetimes 메서드)

**현재 구현:**
```python
def _serialize_datetimes(self, obj: Any) -> Any:
    """
    재귀적으로 datetime 객체를 ISO 형식 문자열로 변환
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
        return obj  # ← Enum은 그대로 반환됨!
```

**문제:**
- Enum 처리 로직 없음
- `else: return obj`에서 Enum 객체 그대로 반환
- Line 99: `await websocket.send_json(serialized_message)` 호출 시 JSON 직렬화 실패

**영향:**
- 정책 매칭 결과를 프론트엔드로 전송 불가
- 사용자 UI에 스피너만 계속 표시
- 실제 데이터는 백엔드에서 처리 완료했지만 화면 갱신 안됨

---

## 4. 오류 메시지 분석

### 오류 1: `Object of type PolicyType is not JSON serializable`
- **발생 위치:** `json.dumps()` 호출 시
- **원인:** Python 기본 JSON 인코더가 Enum을 처리할 수 없음
- **영향:** JSON 변환 실패

### 오류 2: `Failed to send message to session-...: Object of type PolicyType is not JSON serializable`
- **발생 위치:** `ws_manager.py:103` (Line 103: logger.error)
- **원인:** WebSocket `send_json()` 내부에서 JSON 직렬화 실패
- **영향:** 메시지 큐에 저장되지만, 재전송 시에도 동일 오류 반복

### 오류 3: `Failed to serialize object to JSON: Type <enum 'PolicyType'> not serializable`
- **발생 위치:** `llm_service.py:440` (Line 440: logger.warning)
- **원인:** `json_serial` 함수에서 Enum 처리 불가
- **영향:** `str(obj)` fallback으로 데이터 손상

---

## 5. 영향 범위

### 5.1. 기능적 영향

| 컴포넌트 | 영향 | 심각도 |
|---------|------|--------|
| PolicyMatcherTool | 실행은 성공하지만 결과 전달 실패 | 🔴 Critical |
| LLMService | 최종 응답 생성 실패 또는 품질 저하 | 🔴 Critical |
| WebSocket | 프론트엔드 업데이트 불가 | 🔴 Critical |
| 사용자 경험 | 정책 매칭 기능 완전 중단 | 🔴 Critical |

### 5.2. 데이터 흐름 영향

```
정책 매칭 실행 ✅
    ↓
결과 생성 (Enum 포함) ✅
    ↓
JSON 직렬화 ❌ ← 여기서 막힘
    ↓
LLM 전달 ❌
    ↓
WebSocket 전송 ❌
    ↓
프론트엔드 표시 ❌
```

**결과:** 백엔드에서는 정상 처리되었지만, 사용자는 결과를 볼 수 없음

---

## 6. 재현 방법

### 테스트 케이스

```python
import asyncio
from app.service_agent.tools.policy_matcher_tool import PolicyMatcherTool

async def reproduce_error():
    matcher = PolicyMatcherTool()

    user_profile = {
        "age": 32,
        "annual_income": 55000000,
        "total_assets": 200000000,
        "has_house": False,
        "first_time_buyer": True,
        "marriage_years": 2,
        "children": 1,
    }

    result = await matcher.execute(user_profile)

    # 이 시점에서 result["matched_policies"][0]["type"]은 Enum 객체
    print(type(result["matched_policies"][0]["type"]))  # <enum 'PolicyType'>

    # JSON 직렬화 시도
    import json
    try:
        json_str = json.dumps(result)  # ← 여기서 오류 발생!
    except TypeError as e:
        print(f"오류: {e}")  # Object of type PolicyType is not JSON serializable

asyncio.run(reproduce_error())
```

**예상 출력:**
```
<enum 'PolicyType'>
오류: Object of type PolicyType is not JSON serializable
```

---

## 7. 근본 원인 (Root Cause)

### 설계 문제
1. **Enum 사용 의도:**
   - 정책 유형을 타입 안전하게 관리하기 위해 Enum 사용
   - 코드 내에서는 `.value` 접근으로 문자열 추출 가능

2. **JSON 직렬화 고려 부족:**
   - Enum 객체가 외부 시스템(LLM, WebSocket)으로 전달될 것을 고려하지 않음
   - 직렬화 핸들러 구현 누락

3. **일관성 부족:**
   - `datetime`은 직렬화 핸들러 구현됨 (`_serialize_datetimes`, `json_serial`)
   - `Enum`은 누락됨

### 기술적 원인
- Python `json` 모듈의 기본 인코더는 Enum을 지원하지 않음
- 커스텀 `default` 함수에서 Enum 처리 로직 누락
- 재귀적 직렬화 함수에서 Enum 타입 체크 누락

---

## 8. 권장 해결 방안

### Option 1: Enum → String 변환 (근본 해결) ⭐ 추천

**장점:**
- 근본 원인 제거
- 추가 직렬화 로직 불필요
- 코드 단순화

**단점:**
- 기존 코드에서 `.value` 접근하는 부분 수정 필요 (이미 사용 중이므로 영향 적음)

**구현 위치:** `policy_matcher_tool.py`

```python
# 수정 전
{
    "type": PolicyType.LOAN_SUPPORT,
}

# 수정 후
{
    "type": PolicyType.LOAN_SUPPORT.value,  # "대출지원"
}
```

---

### Option 2: JSON 직렬화 핸들러 추가 (방어적 처리)

**장점:**
- 기존 코드 변경 최소화
- 다른 Enum 타입에도 적용 가능
- 호환성 유지

**단점:**
- 직렬화 오버헤드 약간 증가
- 근본 원인은 해결되지 않음

**구현 위치:** `llm_service.py`, `ws_manager.py`

```python
# llm_service.py의 json_serial 함수 수정
def json_serial(obj):
    from datetime import datetime
    from enum import Enum

    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value  # ← Enum 처리 추가
    raise TypeError(f"Type {type(obj)} not serializable")
```

```python
# ws_manager.py의 _serialize_datetimes 함수 수정
def _serialize_datetimes(self, obj: Any) -> Any:
    from datetime import datetime
    from enum import Enum

    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value  # ← Enum 처리 추가
    elif isinstance(obj, dict):
        return {key: self._serialize_datetimes(value) for key, value in obj.items()}
    # ... 나머지 동일
```

---

### Option 3: 하이브리드 접근 (최종 권장) ⭐⭐⭐

**전략:**
- Option 1 (근본 해결) + Option 2 (방어적 처리)
- 이중 안전망 구축

**장점:**
- 즉각적인 문제 해결 (Option 2)
- 장기적인 안정성 (Option 1)
- 향후 유사 문제 예방

**구현 계획:**
1. **즉시 (Phase 1):** Option 2 구현 → 서비스 복구
2. **단기 (Phase 2):** Option 1 구현 → 근본 원인 제거
3. **검증 (Phase 3):** 테스트 및 모니터링

---

## 9. 수정 우선순위

| 우선순위 | 파일 | 수정 내용 | 예상 시간 | 영향 범위 |
|---------|------|----------|----------|----------|
| 🔴 P0 | `llm_service.py` | Enum 직렬화 핸들러 추가 | 5분 | LLM 응답 생성 |
| 🔴 P0 | `ws_manager.py` | Enum 직렬화 핸들러 추가 | 5분 | WebSocket 전송 |
| 🟡 P1 | `policy_matcher_tool.py` | Enum → .value 변환 | 15분 | 정책 DB 초기화 |
| 🟢 P2 | 테스트 코드 | 수정 검증 테스트 작성 | 20분 | 품질 보증 |

**총 예상 시간:** 45분

---

## 10. 테스트 계획

### 10.1. Unit Test

```python
def test_enum_serialization():
    from app.service_agent.llm_manager.llm_service import LLMService
    from app.service_agent.tools.policy_matcher_tool import PolicyType

    llm = LLMService()

    test_data = {
        "policy": {
            "type": PolicyType.LOAN_SUPPORT,
            "name": "디딤돌대출"
        }
    }

    # JSON 직렬화 성공 검증
    result = llm._safe_json_dumps(test_data)
    assert "대출지원" in result
    assert "PolicyType" not in result
```

### 10.2. Integration Test

```python
async def test_policy_matcher_e2e():
    matcher = PolicyMatcherTool()

    result = await matcher.execute({
        "age": 30,
        "annual_income": 50000000,
        "has_house": False
    })

    # 1. Enum이 문자열로 변환되었는지 확인
    assert isinstance(result["matched_policies"][0]["type"], str)

    # 2. JSON 직렬화 성공 확인
    import json
    json_str = json.dumps(result)
    assert len(json_str) > 0

    # 3. WebSocket 전송 가능 확인
    from app.api.ws_manager import get_connection_manager
    manager = get_connection_manager()
    serialized = manager._serialize_datetimes(result)
    assert isinstance(serialized, dict)
```

---

## 11. 모니터링 및 알림

### 추가할 로그

```python
# policy_matcher_tool.py
logger.debug(f"Policy type: {type(policy['type'])} - Value: {policy['type']}")

# llm_service.py
logger.info(f"Serialized {len(aggregated_json)} chars, contains Enum: {bool('PolicyType' in str(obj))}")

# ws_manager.py
logger.debug(f"Serializing message type: {message.get('type')}, contains Enum: {self._contains_enum(message)}")
```

### 알림 설정

- **Critical:** JSON 직렬화 실패 시 Slack 알림
- **Warning:** `str(obj)` fallback 사용 시 로그 수집
- **Info:** 정책 매칭 성공/실패 통계 수집

---

## 12. 결론

### 핵심 요약

1. **문제:** PolicyType Enum이 JSON 직렬화되지 않아 LLM 응답 생성 및 WebSocket 전송 실패
2. **원인:** Enum 객체를 `.value` 변환 없이 그대로 저장, 직렬화 핸들러 누락
3. **해결:** 3개 파일 수정 (llm_service.py, ws_manager.py, policy_matcher_tool.py)
4. **시간:** 총 45분 예상
5. **우선순위:** P0 (Critical) - 즉시 수정 필요

### 다음 단계

1. **즉시:** P0 수정 적용 (llm_service.py, ws_manager.py)
2. **1주일 내:** P1 수정 적용 (policy_matcher_tool.py)
3. **2주일 내:** 테스트 코드 작성 및 모니터링 강화

---

**보고서 작성:** Claude Code AI
**검토 필요:** 개발팀 리드
**승인 필요:** CTO/Tech Lead
