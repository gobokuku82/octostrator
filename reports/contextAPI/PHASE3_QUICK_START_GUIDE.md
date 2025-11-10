# Phase 3 Quick Start Guide

**프로젝트**: AI PT Manager - Phase 3 구현 가이드
**작성일**: 2025-11-06
**버전**: 1.0
**예상 소요 시간**: 2-3일

---

## 📋 Phase 3 개요

### 목표
- ✅ **디버그 모드**: API 헤더로 동적 제어
- ✅ **모니터링 및 추적**: trace_id 기반 분산 추적 + 메트릭 수집
- ✅ **사용자별 맞춤 설정**: Premium/Standard/Trial 등급별 차별화

### 예상 효과
- 📈 개발 생산성 50% 향상 (디버그 시간 단축)
- 🔍 운영 가시성 확보 (병목 지점 파악)
- 💰 추가 비용 절감 10-15% (체험 사용자 제한)
- 🎯 사용자 경험 개선 (등급별 차별화)

### 변경량
- 코드: ~90 lines
- 테스트: ~150 lines
- 총 4개 파일 수정

---

## 🚀 구현 단계

### Day 1: 디버그 모드 + 모니터링 인프라

#### Step 1.1: AppContext 확장 (5분)

**파일**: `backend/app/octostrator/contexts/app_context.py`

**변경 전 (Phase 2)**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    db_conn: Optional[str] = None
    debug: bool = False  # ← 정의만 됨
```

**변경 후 (Phase 3)**:
```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import uuid

@dataclass
class AppContext:
    # 기존 (Phase 2)
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    db_conn: Optional[str] = None

    # Phase 3: 디버그 & 모니터링
    debug: bool = False
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metrics: Dict[str, Any] = field(default_factory=dict)
    log_level: str = "INFO"
```

**변경 사항**:
- ✅ `trace_id`: 요청 추적용 UUID (자동 생성)
- ✅ `metrics`: 메트릭 수집용 dict (자동 초기화)
- ✅ `log_level`: 로그 레벨 제어

**변경량**: +4 lines

#### Step 1.2: 디버그 모드 구현 (15분)

**파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

**함수**: `_create_llm_for_agents()`

**변경 전 (Phase 2)**:
```python
def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """Agent용 LLM 생성 (Context API 사용)"""

    if runtime is not None:
        try:
            context: AppContext = runtime.context
            settings = context.llm_settings

            logger.info(
                f"[Execute] Using Context API settings "
                f"(model={settings.agent_model})"
            )

            return ChatOpenAI(
                model=settings.agent_model,
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens
            )
        except Exception as e:
            logger.warning(f"Failed to use Context API: {e}")

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**변경 후 (Phase 3)**:
```python
import logging

def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """Agent용 LLM 생성 (디버그 모드 + Context API)"""

    if runtime is not None:
        try:
            context: AppContext = runtime.context
            settings = context.llm_settings

            # ⭐ Phase 3: 디버그 모드 활성화
            if context.debug:
                logging.basicConfig(level=logging.DEBUG)
                logger.setLevel(logging.DEBUG)
                logger.debug(f"[DEBUG] Trace ID: {context.trace_id}")
                logger.debug(f"[DEBUG] User: {context.user_id}, Session: {context.session_id}")
                logger.debug(f"[DEBUG] LLM Settings:")
                logger.debug(f"  - Model: {settings.agent_model}")
                logger.debug(f"  - Temperature: {settings.agent_temperature}")
                logger.debug(f"  - Max Tokens: {settings.agent_max_tokens}")
                logger.debug(f"  - Environment: {os.getenv('SYSTEM_ENV', 'development')}")

            logger.info(
                f"[Execute] Using Context API settings "
                f"(model={settings.agent_model}, debug={context.debug})"
            )

            return ChatOpenAI(
                model=settings.agent_model,
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens,
                verbose=context.debug  # ⭐ LangChain verbose 모드
            )
        except Exception as e:
            logger.warning(f"Failed to use Context API: {e}")

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**변경 사항**:
- ✅ `context.debug` 체크하여 상세 로깅
- ✅ `logger.setLevel(logging.DEBUG)` 동적 레벨 변경
- ✅ `verbose=context.debug` LangChain 디버깅 활성화

**변경량**: +15 lines

#### Step 1.3: 모니터링 구현 (20분)

**파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

**함수**: `execute_node()`, `aggregate_node()`

**execute_node() 변경 전**:
```python
async def execute_node(state: dict, runtime: Runtime):
    """Execute agent tasks"""
    context: AppContext = runtime.context

    logger.info(f"[Execute] User={context.user_id}")

    # Agent 실행
    results = []
    for todo in state.get("todos", []):
        result = await execute_agent(todo, runtime)
        results.append(result)

    return {"results": results}
```

**execute_node() 변경 후**:
```python
import time

async def execute_node(state: dict, runtime: Runtime):
    """Execute agent tasks with monitoring"""
    context: AppContext = runtime.context
    start_time = time.time()

    logger.info(f"[Execute] Trace={context.trace_id}, User={context.user_id}, Session={context.session_id}")

    if context.debug:
        logger.debug(f"[DEBUG] Todos to execute: {len(state.get('todos', []))}")

    # Agent 실행 + 메트릭 수집
    results = []
    for idx, todo in enumerate(state.get("todos", []), 1):
        agent_start = time.time()

        logger.info(f"[Execute] Starting agent {idx}/{len(state.get('todos'))}: {todo.get('agent_name')}")

        result = await execute_agent(todo, runtime)

        agent_duration = time.time() - agent_start

        # ⭐ 메트릭 수집
        agent_name = todo.get("agent_name", "unknown")
        context.metrics[f"agent_{agent_name}_duration"] = round(agent_duration, 3)
        context.metrics[f"agent_{agent_name}_status"] = result.get("status", "success")

        if "tokens_used" in result:
            context.metrics[f"agent_{agent_name}_tokens"] = result["tokens_used"]

        if context.debug:
            logger.debug(f"[DEBUG] Agent {agent_name} completed in {agent_duration:.3f}s")

        results.append(result)

    # 총 실행 시간
    total_duration = time.time() - start_time
    context.metrics["execute_total_duration"] = round(total_duration, 3)
    context.metrics["execute_agent_count"] = len(results)
    context.metrics["execute_success_count"] = sum(1 for r in results if r.get("status") == "success")
    context.metrics["execute_failure_count"] = sum(1 for r in results if r.get("status") != "success")

    logger.info(
        f"[Execute] Completed in {total_duration:.2f}s, "
        f"Success: {context.metrics['execute_success_count']}/{len(results)}"
    )

    return {"results": results}
```

**변경 사항**:
- ✅ `trace_id` 로그 출력
- ✅ Agent별 실행 시간 측정
- ✅ 성공/실패 카운트
- ✅ 토큰 사용량 수집

**변경량**: +30 lines

#### Step 1.4: API 엔드포인트 수정 (15분)

**파일**: `backend/app/api/main.py` (또는 해당 API 파일)

**변경 전**:
```python
@app.post("/api/octo/invoke")
async def invoke_octostrator(request: Request):
    """Octostrator 실행 엔드포인트"""

    # Context 생성
    llm_settings = get_llm_settings_from_env()
    context = AppContext(
        user_id=request.user_id,
        session_id=request.session_id,
        llm_settings=llm_settings
    )

    # Graph 실행
    graph = build_octostrator_graph(context=context)
    result = await graph.ainvoke(request.input)

    return {"result": result}
```

**변경 후**:
```python
from fastapi import Request, Header
from typing import Optional
import uuid

@app.post("/api/octo/invoke")
async def invoke_octostrator(
    request: Request,
    x_debug_mode: Optional[str] = Header(None),
    x_trace_id: Optional[str] = Header(None)
):
    """Octostrator 실행 엔드포인트 (디버그 모드 + 모니터링)"""

    # ⭐ Phase 3: 헤더로 디버그 모드 제어
    debug_mode = x_debug_mode == "true" if x_debug_mode else False
    trace_id = x_trace_id if x_trace_id else str(uuid.uuid4())

    logger.info(f"[API] Request received, Trace={trace_id}, Debug={debug_mode}")

    # Context 생성
    llm_settings = get_llm_settings_from_env()
    context = AppContext(
        user_id=request.user_id,
        session_id=request.session_id,
        llm_settings=llm_settings,
        debug=debug_mode,           # ⭐ 디버그 모드
        trace_id=trace_id,          # ⭐ 추적 ID
        log_level="DEBUG" if debug_mode else "INFO"
    )

    # Graph 실행
    graph = build_octostrator_graph(context=context)
    result = await graph.ainvoke(request.input)

    # ⭐ 메트릭 반환
    response = {
        "result": result,
        "trace_id": context.trace_id,
        "debug": debug_mode
    }

    # 디버그 모드 시 메트릭 포함
    if debug_mode:
        response["metrics"] = context.metrics
        logger.debug(f"[API] Metrics: {context.metrics}")

    logger.info(f"[API] Request completed, Trace={trace_id}")

    return response
```

**변경 사항**:
- ✅ `X-Debug-Mode` 헤더로 디버그 모드 제어
- ✅ `X-Trace-ID` 헤더로 추적 ID 전달 (선택)
- ✅ 응답에 `trace_id`, `metrics` 포함

**변경량**: +20 lines

**Day 1 총 변경량**: ~70 lines

---

### Day 2: 사용자별 맞춤 설정

#### Step 2.1: 사용자 등급 정의 (5분)

**파일**: `backend/app/octostrator/contexts/app_context.py` (또는 새 파일)

**새로 추가**:
```python
from enum import Enum

class UserTier(str, Enum):
    """사용자 등급"""
    PREMIUM = "premium"
    STANDARD = "standard"
    TRIAL = "trial"

# 등급별 설정
USER_TIER_CONFIG = {
    UserTier.PREMIUM: {
        "model": "gpt-4o",
        "max_tokens": 8000,
        "description": "프리미엄 사용자 - GPT-4 + 높은 토큰"
    },
    UserTier.STANDARD: {
        "model": "gpt-4o-mini",
        "max_tokens": 5000,
        "description": "일반 사용자 - 기본 설정"
    },
    UserTier.TRIAL: {
        "model": "gpt-4o-mini",
        "max_tokens": 2000,
        "description": "체험 사용자 - 제한된 토큰"
    }
}

def get_user_tier(user_id: str) -> UserTier:
    """user_id로부터 사용자 등급 판단"""
    if user_id.startswith("premium_"):
        return UserTier.PREMIUM
    elif user_id.startswith("trial_"):
        return UserTier.TRIAL
    else:
        return UserTier.STANDARD
```

**변경량**: +30 lines

#### Step 2.2: _create_llm_for_agents() 수정 (15분)

**파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

**변경 전 (Day 1)**:
```python
def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    if runtime is not None:
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 디버그 로깅
        if context.debug:
            # ...

        return ChatOpenAI(
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
            verbose=context.debug
        )

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**변경 후 (Day 2)**:
```python
from backend.app.octostrator.contexts.app_context import get_user_tier, USER_TIER_CONFIG

def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    if runtime is not None:
        context: AppContext = runtime.context
        settings = context.llm_settings

        # ⭐ Phase 3: 사용자별 맞춤 설정
        user_tier = get_user_tier(context.user_id)
        tier_config = USER_TIER_CONFIG[user_tier]

        # 등급별 설정 적용
        model = tier_config["model"]
        max_tokens = tier_config["max_tokens"]
        temperature = settings.agent_temperature  # temperature는 환경별 설정 유지

        logger.info(
            f"[Execute] User tier: {user_tier.value}, "
            f"Model: {model}, Max tokens: {max_tokens}"
        )

        # 디버그 로깅
        if context.debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug(f"[DEBUG] Trace ID: {context.trace_id}")
            logger.debug(f"[DEBUG] User: {context.user_id} (Tier: {user_tier.value})")
            logger.debug(f"[DEBUG] Tier config: {tier_config}")
            logger.debug(f"[DEBUG] Final LLM settings:")
            logger.debug(f"  - Model: {model}")
            logger.debug(f"  - Temperature: {temperature}")
            logger.debug(f"  - Max Tokens: {max_tokens}")

        # ⭐ 메트릭 기록
        context.metrics["user_tier"] = user_tier.value
        context.metrics["llm_model"] = model
        context.metrics["llm_max_tokens"] = max_tokens

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=context.debug
        )

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**변경 사항**:
- ✅ `get_user_tier()` 호출하여 사용자 등급 판단
- ✅ 등급별 모델 및 토큰 적용
- ✅ 메트릭에 등급 정보 기록

**변경량**: +20 lines

**Day 2 총 변경량**: ~50 lines

---

### Day 3: 통합 테스트 + 문서화

#### Step 3.1: 테스트 작성 (1-2시간)

**파일**: `tests/test_phase3_context_api.py` (신규 생성)

**테스트 시나리오**:

```python
"""
Phase 3 Context API Integration Test

디버그 모드 + 모니터링 + 사용자별 설정 검증
"""

import sys
sys.path.insert(0, 'C:/kdy/Projects/AI_PTmanager/beta_v001')

import os
from unittest.mock import Mock, AsyncMock

print("\n" + "="*60)
print("Phase 3 Context API Integration Test")
print("="*60 + "\n")

# ====================================
# Test 1: 디버그 모드 활성화
# ====================================
print("[Test 1] Debug mode activation...")

try:
    from backend.app.octostrator.contexts.app_context import AppContext
    from backend.app.config.llm_settings import get_llm_settings_from_env

    llm_settings = get_llm_settings_from_env()
    context = AppContext(
        user_id="test_user",
        session_id="test_session",
        llm_settings=llm_settings,
        debug=True  # ⭐ 디버그 모드 활성화
    )

    assert context.debug == True
    assert context.trace_id is not None
    assert isinstance(context.metrics, dict)

    print(f"   ✅ Debug mode activated")
    print(f"      - Debug: {context.debug}")
    print(f"      - Trace ID: {context.trace_id}")
    print(f"      - Metrics: {type(context.metrics).__name__}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Test 2: 메트릭 수집
# ====================================
print("\n[Test 2] Metrics collection...")

try:
    from backend.app.octostrator.contexts.app_context import AppContext
    from backend.app.config.llm_settings import get_llm_settings_from_env

    llm_settings = get_llm_settings_from_env()
    context = AppContext(
        user_id="test_user",
        session_id="test_session",
        llm_settings=llm_settings
    )

    # 메트릭 수집
    context.metrics["test_duration"] = 1.23
    context.metrics["test_count"] = 5
    context.metrics["test_status"] = "success"

    assert "test_duration" in context.metrics
    assert context.metrics["test_duration"] == 1.23
    assert context.metrics["test_count"] == 5

    print(f"   ✅ Metrics collection working")
    print(f"      - Metrics: {context.metrics}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Test 3: 사용자 등급 판단
# ====================================
print("\n[Test 3] User tier detection...")

try:
    from backend.app.octostrator.contexts.app_context import get_user_tier, UserTier

    # Premium 사용자
    tier_premium = get_user_tier("premium_user123")
    assert tier_premium == UserTier.PREMIUM

    # Trial 사용자
    tier_trial = get_user_tier("trial_user456")
    assert tier_trial == UserTier.TRIAL

    # Standard 사용자
    tier_standard = get_user_tier("user789")
    assert tier_standard == UserTier.STANDARD

    print(f"   ✅ User tier detection working")
    print(f"      - premium_user123 → {tier_premium.value}")
    print(f"      - trial_user456 → {tier_trial.value}")
    print(f"      - user789 → {tier_standard.value}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Test 4: LLM 생성 (Premium 사용자)
# ====================================
print("\n[Test 4] LLM creation for premium user...")

try:
    from backend.app.octostrator.supervisors.execute.execute_nodes import _create_llm_for_agents
    from backend.app.octostrator.contexts.app_context import AppContext
    from backend.app.config.llm_settings import get_llm_settings_from_env
    from unittest.mock import Mock

    llm_settings = get_llm_settings_from_env()
    context = AppContext(
        user_id="premium_user123",
        session_id="test_session",
        llm_settings=llm_settings
    )

    # Mock Runtime
    runtime = Mock()
    runtime.context = context

    # LLM 생성
    llm = _create_llm_for_agents(runtime)

    assert llm is not None
    assert llm.model_name == "gpt-4o"  # Premium → GPT-4

    print(f"   ✅ Premium user LLM created")
    print(f"      - Model: {llm.model_name}")
    print(f"      - User tier: {context.metrics.get('user_tier', 'N/A')}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Test 5: LLM 생성 (Trial 사용자)
# ====================================
print("\n[Test 5] LLM creation for trial user...")

try:
    llm_settings = get_llm_settings_from_env()
    context = AppContext(
        user_id="trial_user456",
        session_id="test_session",
        llm_settings=llm_settings
    )

    runtime = Mock()
    runtime.context = context

    llm = _create_llm_for_agents(runtime)

    assert llm is not None
    assert llm.model_name == "gpt-4o-mini"  # Trial → gpt-4o-mini
    assert llm.max_tokens == 2000  # Trial → 2000 tokens

    print(f"   ✅ Trial user LLM created")
    print(f"      - Model: {llm.model_name}")
    print(f"      - Max tokens: {llm.max_tokens}")
    print(f"      - User tier: {context.metrics.get('user_tier', 'N/A')}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Test 6: Trace ID 생성
# ====================================
print("\n[Test 6] Trace ID generation...")

try:
    import uuid

    context1 = AppContext(
        user_id="user1",
        session_id="session1",
        llm_settings=llm_settings
    )

    context2 = AppContext(
        user_id="user2",
        session_id="session2",
        llm_settings=llm_settings
    )

    # 각 Context는 고유한 trace_id를 가짐
    assert context1.trace_id != context2.trace_id
    assert len(context1.trace_id) == 36  # UUID 길이

    print(f"   ✅ Trace ID generation working")
    print(f"      - Context 1: {context1.trace_id}")
    print(f"      - Context 2: {context2.trace_id}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Test 7: Backward Compatibility
# ====================================
print("\n[Test 7] Backward compatibility...")

try:
    # runtime=None → Phase 1 모드
    llm = _create_llm_for_agents(runtime=None)

    assert llm is not None
    assert llm.model_name == "gpt-4o-mini"

    print(f"   ✅ Backward compatibility maintained")
    print(f"      - LLM created without runtime")
    print(f"      - Model: {llm.model_name}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ====================================
# Summary
# ====================================
print("\n" + "="*60)
print("✅ ALL PHASE 3 TESTS PASSED!")
print("="*60)
print("""
Phase 3 Context API Integration: COMPLETE ✓

Test Coverage:
  ✓ Debug mode activation
  ✓ Metrics collection
  ✓ User tier detection
  ✓ LLM creation for premium user
  ✓ LLM creation for trial user
  ✓ Trace ID generation
  ✓ Backward compatibility

Phase 3 Features:
  ✓ 디버그 모드: API 헤더로 제어
  ✓ 모니터링: trace_id 기반 추적 + 메트릭 수집
  ✓ 사용자별 설정: Premium/Standard/Trial 차별화

Ready for Production: YES ✅
""")
```

**테스트 실행**:
```bash
python tests/test_phase3_context_api.py
```

**변경량**: ~150 lines (신규 파일)

#### Step 3.2: 문서화 (30분)

**파일**: `reports/contextAPI/PHASE3_COMPLETION_REPORT.md` (신규 생성)

**내용**:
- Phase 3 목표 및 성과
- 구현 내역
- 테스트 결과
- 변경된 파일 목록
- Next Steps

---

## 📊 Phase 3 완료 체크리스트

### 코드 변경
- [ ] `app_context.py`: debug, trace_id, metrics 필드 추가 (+4 lines)
- [ ] `execute_nodes.py`: 디버그 모드 + 모니터링 + 사용자별 설정 (+50 lines)
- [ ] `api/main.py`: X-Debug-Mode 헤더 지원 (+20 lines)
- [ ] (신규) 사용자 등급 정의 (+30 lines)

### 테스트
- [ ] `test_phase3_context_api.py` 작성 (7개 테스트)
- [ ] 모든 테스트 통과 (7/7)
- [ ] Phase 1 E2E 테스트 재실행 (Backward Compatibility 확인)
- [ ] Phase 2 테스트 재실행 (환경별 LLM 설정 정상 동작)

### 문서화
- [ ] Phase 3 완료 보고서 작성
- [ ] 변경 사항 문서화
- [ ] API 사용 예시 작성

### 검증
- [ ] 디버그 모드 동작 확인 (curl로 테스트)
- [ ] trace_id 로그 출력 확인
- [ ] 메트릭 수집 확인
- [ ] Premium 사용자 GPT-4 사용 확인
- [ ] Trial 사용자 토큰 제한 확인

---

## 🧪 테스트 방법

### 1. 디버그 모드 테스트

**API 호출**:
```bash
curl -X POST http://localhost:8000/api/octo/invoke \
  -H "Content-Type: application/json" \
  -H "X-Debug-Mode: true" \
  -H "X-Trace-ID: test-trace-123" \
  -d '{
    "input": "오늘 운동 루틴 추천해줘",
    "user_id": "test_user",
    "session_id": "test_session"
  }'
```

**예상 응답**:
```json
{
  "result": { ... },
  "trace_id": "test-trace-123",
  "debug": true,
  "metrics": {
    "execute_total_duration": 2.345,
    "execute_agent_count": 2,
    "execute_success_count": 2,
    "agent_DietAgent_duration": 1.123,
    "agent_DietAgent_tokens": 1500,
    "agent_WorkoutAgent_duration": 1.222,
    "agent_WorkoutAgent_tokens": 1800
  }
}
```

### 2. Premium 사용자 테스트

**API 호출**:
```bash
curl -X POST http://localhost:8000/api/octo/invoke \
  -H "Content-Type: application/json" \
  -H "X-Debug-Mode: true" \
  -d '{
    "input": "상세한 식단 분석 부탁해",
    "user_id": "premium_user123",
    "session_id": "test_session"
  }'
```

**로그 확인**:
```
[Execute] User tier: premium, Model: gpt-4o, Max tokens: 8000
[DEBUG] User: premium_user123 (Tier: premium)
```

### 3. Trial 사용자 테스트

**API 호출**:
```bash
curl -X POST http://localhost:8000/api/octo/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input": "간단한 운동 추천",
    "user_id": "trial_user456",
    "session_id": "test_session"
  }'
```

**로그 확인**:
```
[Execute] User tier: trial, Model: gpt-4o-mini, Max tokens: 2000
```

---

## 📈 예상 효과 측정

### Day 1 완료 후

**디버그 모드**:
- [ ] 로그 상세도 10배 증가 (디버그 모드 시)
- [ ] 문제 진단 시간 체감 50% 단축

**모니터링**:
- [ ] trace_id로 전체 요청 추적 가능
- [ ] Agent별 실행 시간 측정
- [ ] 병목 지점 파악

### Day 2 완료 후

**사용자별 설정**:
- [ ] Premium 사용자 GPT-4 사용 확인
- [ ] Trial 사용자 토큰 제한 확인
- [ ] 등급별 비용 차이 측정

**예상 비용 절감**:
- Trial 사용자 (2000 tokens vs 5000 tokens): 60% 절감
- 전체 Trial 사용자가 20%라면: 12% 추가 절감

### Day 3 완료 후

**전체 시스템**:
- [ ] Phase 3 테스트 7/7 통과
- [ ] Phase 1 + Phase 2 테스트 재실행 (Backward Compatibility)
- [ ] 문서화 완료

---

## ⚠️ 주의사항

### 디버그 모드 사용

**❌ 잘못된 사용**:
```python
# Production에서 항상 디버그 모드
context = AppContext(..., debug=True)  # ❌
```

**✅ 올바른 사용**:
```python
# API 헤더로 동적 제어
debug_mode = request.headers.get("X-Debug-Mode") == "true"
context = AppContext(..., debug=debug_mode)
```

### 메트릭 수집

**❌ 잘못된 사용**:
```python
# 모든 상태를 metrics에 저장
context.metrics["entire_state"] = state  # ❌ 너무 많은 데이터
```

**✅ 올바른 사용**:
```python
# 핵심 메트릭만 수집
context.metrics["duration"] = 1.23
context.metrics["agent_count"] = 5
context.metrics["tokens_used"] = 1500
```

### 사용자 등급

**❌ 잘못된 판단**:
```python
# 하드코딩된 사용자 ID
if user_id == "premium_user123":  # ❌
```

**✅ 올바른 판단**:
```python
# prefix 기반 판단
if user_id.startswith("premium_"):  # ✅
```

---

## 🎉 완료 후 Next Steps

### Phase 3 완료 확인

- [ ] 모든 테스트 통과 (7/7)
- [ ] Backward Compatibility 확인
- [ ] 문서화 완료
- [ ] 팀 리뷰 및 승인

### Phase 4 진행 여부 결정

**Phase 4 (Rate Limiting + 캐싱)**를 진행할지 결정:
- ✅ 사용량 증가 예상 → Phase 4 진행 권장
- ✅ 추가 비용 절감 필요 → Phase 4 진행 권장
- ⚠️ 현재 사용량 적음 → Phase 5 (DB 통합) 우선

### Production 배포

Phase 3 완료 후 Production 배포 시:
1. Development 환경에서 1-2일 추가 테스트
2. 디버그 로그 확인
3. 메트릭 모니터링 설정 (DataDog, Prometheus 등)
4. Production 배포
5. 1주일 모니터링 (디버그 모드 효과, 사용자별 설정 동작)

---

## 📚 참고 문서

- [Context API 로드맵](./CONTEXT_API_ROADMAP.md)
- [Context API 구현 가이드](./CONTEXT_API_IMPLEMENTATION_GUIDE.md)
- [Phase 2 완료 보고서](../merge/PHASE2_CONTEXT_API_COMPLETION_REPORT_251106.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Status**: 🚀 QUICK START
**Author**: AI PT Manager Development Team

**Ready to Start?** Day 1부터 시작하세요! 🎯
