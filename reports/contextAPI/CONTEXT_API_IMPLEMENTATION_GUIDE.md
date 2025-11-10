# Context API 구현 매뉴얼

**프로젝트**: AI PT Manager - Context API 개발자 가이드
**작성일**: 2025-11-06
**버전**: 1.0
**대상**: 백엔드 개발자

---

## 📋 목차

1. [Context API 개요](#1-context-api-개요)
2. [기본 구조](#2-기본-구조)
3. [Phase별 구현 가이드](#3-phase별-구현-가이드)
4. [API 레퍼런스](#4-api-레퍼런스)
5. [Best Practices](#5-best-practices)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Context API 개요

### 1.1 Context API란?

Context API는 LangGraph 1.0+에서 제공하는 기능으로, **State와 별도로 관리되는 불변 런타임 정보**를 노드에 전달합니다.

**주요 특징**:
- ✅ **불변성**: Context는 변경되지 않음
- ✅ **Checkpoint 비저장**: Checkpoint에 저장되지 않아 가벼움
- ✅ **모든 노드 접근**: Runtime을 통해 모든 노드에서 접근 가능
- ✅ **타입 안전**: Dataclass + Pydantic으로 타입 검증

### 1.2 State vs Context

| 항목 | State | Context |
|-----|-------|---------|
| 용도 | 그래프 실행 중 변경되는 데이터 | 실행 전 설정된 불변 정보 |
| 변경 가능 | ✅ Yes | ❌ No |
| Checkpoint 저장 | ✅ Yes | ❌ No |
| 예시 | todos, results, messages | user_id, llm_settings, debug |

### 1.3 왜 Context API를 사용하는가?

**문제 (Phase 1)**:
```python
# 모든 노드에서 동일한 하드코딩된 설정 사용
def _create_llm_for_agents():
    return ChatOpenAI(
        model="gpt-4o-mini",  # ← 하드코딩
        temperature=0.7,
        max_tokens=4096
    )
```

**해결 (Phase 2+)**:
```python
# Context API를 통한 동적 설정
def _create_llm_for_agents(runtime: Runtime):
    context: AppContext = runtime.context
    return ChatOpenAI(
        model=context.llm_settings.agent_model,  # ← 환경별 자동 적용
        temperature=context.llm_settings.agent_temperature,
        max_tokens=context.llm_settings.agent_max_tokens
    )
```

**효과**:
- ✅ 환경별 설정 분리 (Prod/Dev/Test)
- ✅ 사용자별 맞춤 설정
- ✅ 디버그 모드 동적 제어
- ✅ 중앙화된 설정 관리

---

## 2. 기본 구조

### 2.1 파일 구조

```
backend/app/
├── octostrator/
│   ├── contexts/
│   │   └── app_context.py          # ← Context 스키마 정의
│   ├── supervisors/
│   │   ├── execute/
│   │   │   ├── execute_nodes.py    # ← Context 사용
│   │   │   └── execute_graph.py    # ← Context 주입
│   │   └── octostrator/
│   │       └── octostrator_graph.py # ← Context 주입
├── config/
│   └── llm_settings.py             # ← 설정 로직 (Factory)
└── api/
    └── main.py                     # ← Context 생성

.env                                 # ← 환경 제어
```

### 2.2 핵심 컴포넌트

#### 2.2.1 AppContext (Dataclass)
**파일**: `backend/app/octostrator/contexts/app_context.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppContext:
    """Application 런타임 Context

    불변 정보만 포함:
    - user_id: 사용자 ID
    - session_id: 세션 ID
    - llm_settings: 노드별 LLM 설정
    - db_conn: DB 연결 (Phase 5)
    - debug: 디버그 모드 (Phase 3)
    """

    # 필수 필드
    user_id: str
    session_id: str
    llm_settings: LLMSettings

    # 선택 필드
    db_conn: Optional[str] = None
    debug: bool = False
```

**주의사항**:
- ⚠️ **Dataclass 필수**: LangGraph Context API는 dataclass 요구
- ⚠️ **불변 정보만**: 변경 가능한 정보는 State에 저장

#### 2.2.2 LLMSettings (Pydantic)
**파일**: `backend/app/octostrator/contexts/app_context.py`

```python
from pydantic import BaseModel, Field

class LLMSettings(BaseModel):
    """노드별 LLM 설정

    Pydantic 검증으로 타입 안정성 확보
    """

    # Model Selection
    default_model: str = Field(default="gpt-4o-mini")

    # Intent Node
    intent_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    intent_max_tokens: int = Field(default=1024, ge=1, le=16384)
    intent_model: str = Field(default="gpt-4o-mini")

    # Planning Node
    planning_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    planning_max_tokens: int = Field(default=2048, ge=1, le=16384)
    planning_model: str = Field(default="gpt-4o-mini")

    # Agent Nodes
    agent_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    agent_max_tokens: int = Field(default=4096, ge=1, le=16384)
    agent_model: str = Field(default="gpt-4o-mini")

    # ... 더 많은 노드별 설정
```

**장점**:
- ✅ **타입 검증**: Pydantic이 자동으로 타입 검증
- ✅ **범위 검증**: `ge`, `le`로 값 범위 제한
- ✅ **기본값**: 설정 누락 시 기본값 사용

#### 2.2.3 LLM Settings Factory
**파일**: `backend/app/config/llm_settings.py`

```python
from enum import Enum
from typing import Optional, Dict, Any

class Environment(str, Enum):
    """환경 타입"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"

# 환경별 Preset
PRODUCTION_PRESET = {
    "agent_temperature": 0.4,
    "agent_max_tokens": 3500,
    # ...
}

DEVELOPMENT_PRESET = {
    "agent_temperature": 0.5,
    "agent_max_tokens": 5000,
    # ...
}

def get_llm_settings(
    environment: Environment = Environment.DEVELOPMENT
) -> LLMSettings:
    """환경별 LLM 설정 생성"""
    if environment == Environment.PRODUCTION:
        preset = PRODUCTION_PRESET.copy()
    else:
        preset = DEVELOPMENT_PRESET.copy()

    return LLMSettings(**preset)

def get_llm_settings_from_env() -> LLMSettings:
    """환경 변수로부터 LLM 설정 가져오기"""
    env_name = os.getenv("SYSTEM_ENV", "development").lower()

    if env_name == "production":
        environment = Environment.PRODUCTION
    elif env_name == "testing":
        environment = Environment.TESTING
    else:
        environment = Environment.DEVELOPMENT

    return get_llm_settings(environment)
```

### 2.3 Context API 활성화

#### 2.3.1 Graph Builder 수정

**파일**: `backend/app/octostrator/supervisors/execute/execute_graph.py`

```python
from typing import Optional
from backend.app.octostrator.contexts.app_context import AppContext

def build_execute_graph(
    state_class=None,
    context: Optional[AppContext] = None  # ← Context 파라미터 추가
):
    """Build execute graph with Context API"""

    # State 기본값
    if state_class is None:
        state_class = dict

    # ⭐ Context 자동 생성 (환경 변수 기반)
    if context is None:
        from backend.app.config.llm_settings import get_llm_settings_from_env

        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=llm_settings
        )

    # ⭐ Context API 활성화!
    graph = StateGraph(
        state_class,
        context_schema=type(context)  # ← 이것만 추가하면 됨!
    )

    # 노드 추가
    graph.add_node("execute", execute_node)
    graph.add_node("aggregate", aggregate_node)
    # ...

    return graph.compile(checkpointer=checkpointer)
```

**핵심 포인트**:
- ⭐ `context_schema=type(context)` 추가만으로 Context API 활성화!
- ⭐ LangGraph가 자동으로 runtime을 모든 노드에 주입
- ⭐ `context=None`이면 환경 변수 기반 자동 생성

#### 2.3.2 Node에서 Context 사용

**파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

```python
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext

def execute_node(state: dict, runtime: Runtime):
    """Execute node with Context API

    Args:
        state: 그래프 상태
        runtime: LangGraph Runtime (자동 주입됨!)
    """

    # ⭐ Context 가져오기
    context: AppContext = runtime.context

    # Context 사용
    logger.info(f"[Execute] User={context.user_id}, Session={context.session_id}")

    # LLM 생성 (Context 설정 사용)
    llm = _create_llm_for_agents(runtime)

    # Agent 실행
    results = []
    for todo in state.get("todos", []):
        result = execute_agent(todo, llm)
        results.append(result)

    return {"results": results}

def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """Agent용 LLM 생성 (Context API 사용)"""

    # Phase 2: Context API 사용
    if runtime is not None:
        try:
            context: AppContext = runtime.context
            settings = context.llm_settings

            logger.info(
                f"[Execute] Using Context API settings "
                f"(model={settings.agent_model}, temp={settings.agent_temperature})"
            )

            return ChatOpenAI(
                model=settings.agent_model,
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens
            )
        except Exception as e:
            logger.warning(f"Failed to use Context API: {e}")

    # Phase 1: Fallback (Backward Compatibility)
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=4096
    )
```

**핵심 포인트**:
- ⭐ `runtime` 파라미터는 자동으로 주입됨
- ⭐ `runtime.context`로 Context 접근
- ⭐ `runtime=None`이면 Phase 1 모드 (Backward Compatibility)

---

## 3. Phase별 구현 가이드

### 3.1 Phase 2: 환경별 LLM 설정 (완료)

**목표**: `.env` 파일 1줄로 환경 전환

**구현 완료**:
- ✅ `app_context.py`: LLMSettings + AppContext 정의
- ✅ `llm_settings.py`: 환경별 preset + Factory 함수
- ✅ `execute_graph.py`: context_schema 추가
- ✅ `octostrator_graph.py`: context_schema 추가
- ✅ `execute_nodes.py`: runtime 파라미터 사용
- ✅ `.env`: SYSTEM_ENV 환경 변수

**사용 방법**:
```bash
# .env 파일
SYSTEM_ENV=development  # or production, testing
```

**결과**: 45.9% 비용 절감

### 3.2 Phase 3: 디버그 모드 + 모니터링 + 사용자별 설정

**목표**: 개발 생산성 향상 + 운영 가시성 확보

#### 3.2.1 AppContext 확장

**수정 파일**: `backend/app/octostrator/contexts/app_context.py`

```python
from dataclasses import dataclass, field
from typing import Dict, Any
import uuid

@dataclass
class AppContext:
    # 기존 (Phase 2)
    user_id: str
    session_id: str
    llm_settings: LLMSettings

    # 신규 (Phase 3)
    debug: bool = False                                              # 디버그 모드
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())) # 추적 ID
    metrics: Dict[str, Any] = field(default_factory=dict)           # 메트릭 수집
    log_level: str = "INFO"                                          # 로그 레벨
```

**변경량**: +4 lines

#### 3.2.2 디버그 모드 구현

**수정 파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

```python
import logging

def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """Agent용 LLM 생성 (디버그 모드 지원)"""

    if runtime is not None:
        context: AppContext = runtime.context

        # ⭐ Phase 3: 디버그 모드 활성화
        if context.debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug(f"[DEBUG] Trace={context.trace_id}")
            logger.debug(f"[DEBUG] User={context.user_id}, Session={context.session_id}")
            logger.debug(f"[DEBUG] LLM Settings: temp={context.llm_settings.agent_temperature}, "
                        f"tokens={context.llm_settings.agent_max_tokens}")

        return ChatOpenAI(
            model=context.llm_settings.agent_model,
            temperature=context.llm_settings.agent_temperature,
            max_tokens=context.llm_settings.agent_max_tokens,
            verbose=context.debug  # ⭐ LangChain verbose 모드
        )

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**변경량**: +10 lines

#### 3.2.3 모니터링 구현

**수정 파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

```python
import time

def execute_node(state: dict, runtime: Runtime):
    """Execute node with monitoring"""
    context: AppContext = runtime.context
    start_time = time.time()

    logger.info(f"[Execute] Trace={context.trace_id}, User={context.user_id}")

    # Agent 실행 + 메트릭 수집
    results = []
    for todo in state.get("todos", []):
        agent_start = time.time()
        result = execute_agent(todo, runtime)
        agent_duration = time.time() - agent_start

        # ⭐ 메트릭 기록
        context.metrics[f"agent_{todo['agent_name']}_duration"] = agent_duration
        context.metrics[f"agent_{todo['agent_name']}_tokens"] = result.get("tokens_used", 0)

        results.append(result)

    # 총 실행 시간
    total_duration = time.time() - start_time
    context.metrics["execute_total_duration"] = total_duration
    context.metrics["execute_agent_count"] = len(results)

    logger.info(f"[Execute] Completed in {total_duration:.2f}s, Agents={len(results)}")

    return {"results": results}
```

**변경량**: +15 lines

#### 3.2.4 사용자별 맞춤 설정

**수정 파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

```python
def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """Agent용 LLM 생성 (사용자별 맞춤 설정)"""

    if runtime is not None:
        context: AppContext = runtime.context
        settings = context.llm_settings

        # ⭐ Phase 3: 사용자별 맞춤 설정
        model = settings.agent_model
        temperature = settings.agent_temperature
        max_tokens = settings.agent_max_tokens

        if context.user_id.startswith("premium_"):
            # Premium 사용자: GPT-4 + 높은 토큰
            model = "gpt-4o"
            max_tokens = 8000
            logger.info(f"[Execute] Premium user detected: {context.user_id}")

        elif context.user_id.startswith("trial_"):
            # Trial 사용자: 제한된 토큰
            max_tokens = 2000
            logger.info(f"[Execute] Trial user detected: {context.user_id}")

        if context.debug:
            logger.debug(f"[DEBUG] User={context.user_id}, Model={model}, Tokens={max_tokens}")

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=context.debug
        )

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**변경량**: +15 lines

#### 3.2.5 API 엔드포인트 수정

**수정 파일**: `backend/app/api/main.py`

```python
from fastapi import Request, Header
from typing import Optional

@app.post("/api/octo/invoke")
async def invoke_octostrator(
    request: Request,
    x_debug_mode: Optional[str] = Header(None),
    x_trace_id: Optional[str] = Header(None)
):
    """Octostrator 실행 엔드포인트"""

    # ⭐ Phase 3: 헤더로 디버그 모드 제어
    debug_mode = x_debug_mode == "true" if x_debug_mode else False
    trace_id = x_trace_id if x_trace_id else str(uuid.uuid4())

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
    return {
        "result": result,
        "trace_id": context.trace_id,
        "metrics": context.metrics,
        "debug": debug_mode
    }
```

**변경량**: +20 lines

**사용 예시**:
```bash
# 디버그 모드 활성화
curl -X POST http://localhost:8000/api/octo/invoke \
  -H "X-Debug-Mode: true" \
  -H "X-Trace-ID: custom-trace-123" \
  -d '{"input": "오늘 운동 루틴 추천해줘"}'
```

**Phase 3 총 변경량**: ~90 lines

### 3.3 Phase 4: Rate Limiting + 캐싱

#### 3.3.1 AppContext 확장

```python
@dataclass
class AppContext:
    # ... 기존 필드

    # Phase 4
    rate_limit: int = 100                    # 세션당 최대 요청 수/시간
    enable_cache: bool = True                # 캐싱 활성화
    cache_ttl: int = 3600                    # 캐시 TTL (1시간)
```

#### 3.3.2 Rate Limiting 구현

```python
from collections import defaultdict
from datetime import datetime, timedelta
import redis

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def check_rate_limit(runtime: Runtime) -> bool:
    """세션별 Rate Limiting 체크"""
    context: AppContext = runtime.context
    session_id = context.session_id

    # Redis에서 현재 카운트 가져오기
    key = f"rate_limit:{session_id}"
    count = redis_client.get(key)

    if count is None:
        # 처음 요청: 카운터 초기화
        redis_client.setex(key, 3600, 1)  # 1시간 TTL
        return True

    count = int(count)
    if count >= context.rate_limit:
        logger.warning(f"[RateLimit] Session {session_id} exceeded limit ({count}/{context.rate_limit})")
        return False

    # 카운터 증가
    redis_client.incr(key)
    return True

def execute_node(state: dict, runtime: Runtime):
    """Execute node with Rate Limiting"""

    # ⭐ Rate Limit 체크
    if not check_rate_limit(runtime):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {runtime.context.rate_limit} requests per hour."
        )

    # 정상 처리
    # ...
```

#### 3.3.3 캐싱 구현

```python
import hashlib

def cognitive_layer_node(state: dict, runtime: Runtime):
    """Cognitive node with caching"""
    context: AppContext = runtime.context
    user_input = state.get("user_input", "")

    # ⭐ 캐싱 활성화 시 캐시 체크
    if context.enable_cache:
        cache_key = f"cognitive:{hashlib.md5(f'{context.user_id}:{user_input}'.encode()).hexdigest()}"

        # Redis에서 캐시 확인
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"[Cache] Hit for user={context.user_id}")
            return json.loads(cached)

    # 캐시 미스: LLM 호출
    llm = _create_llm_for_cognitive(runtime)
    response = llm.invoke(user_input)

    # 캐시 저장
    if context.enable_cache:
        redis_client.setex(
            cache_key,
            context.cache_ttl,
            json.dumps(response)
        )

    return {"intent": response}
```

### 3.4 Phase 5: DB 연결 공유

#### 3.4.1 AppContext 확장

```python
from sqlalchemy.orm import Session

@dataclass
class AppContext:
    # ... 기존 필드

    # Phase 5
    db_conn: Optional[str] = None            # DB 연결 URL
    db_session: Optional[Session] = None     # SQLAlchemy Session
```

#### 3.4.2 Graph Builder 수정

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def build_octostrator_graph(context: Optional[AppContext] = None):
    """Graph 빌드 시 DB 세션 생성"""

    if context is None:
        from backend.app.config.system import config

        # ⭐ DB 연결 생성
        engine = create_engine(config.postgres_url)
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()

        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=llm_settings,
            db_conn=config.postgres_url,
            db_session=db_session  # ⭐ 세션 공유!
        )

    graph = StateGraph(OctostratorState, context_schema=type(context))
    # ...
    return graph.compile(checkpointer=checkpointer)
```

#### 3.4.3 Node에서 DB 사용

```python
def execute_node(state: dict, runtime: Runtime):
    """Execute node with DB access"""
    context: AppContext = runtime.context
    db_session = context.db_session

    # ⭐ DB 쿼리 실행
    user = db_session.query(User).filter_by(id=context.user_id).first()

    # Agent 실행
    results = []
    for todo in state.get("todos", []):
        result = execute_agent(todo, runtime)

        # ⭐ 결과 DB 저장
        agent_result = AgentResult(
            user_id=context.user_id,
            session_id=context.session_id,
            agent_name=todo["agent_name"],
            result=result
        )
        db_session.add(agent_result)
        results.append(result)

    # ⭐ 커밋
    db_session.commit()

    return {"results": results}
```

---

## 4. API 레퍼런스

### 4.1 AppContext

**위치**: `backend/app/octostrator/contexts/app_context.py`

```python
@dataclass
class AppContext:
    """Application 런타임 Context"""

    # 필수 필드
    user_id: str                             # 사용자 ID
    session_id: str                          # 세션 ID
    llm_settings: LLMSettings               # LLM 설정

    # Phase 3
    debug: bool = False                      # 디버그 모드
    trace_id: str = ...                      # 추적 ID
    metrics: Dict[str, Any] = ...           # 메트릭
    log_level: str = "INFO"                  # 로그 레벨

    # Phase 4
    rate_limit: int = 100                    # Rate Limit
    enable_cache: bool = True                # 캐싱 활성화
    cache_ttl: int = 3600                    # 캐시 TTL

    # Phase 5
    db_conn: Optional[str] = None            # DB 연결
    db_session: Optional[Session] = None     # DB 세션
```

### 4.2 LLMSettings

**위치**: `backend/app/octostrator/contexts/app_context.py`

```python
class LLMSettings(BaseModel):
    """노드별 LLM 설정"""

    # Model
    default_model: str = "gpt-4o-mini"

    # Intent
    intent_temperature: float = 0.7
    intent_max_tokens: int = 1024
    intent_model: str = "gpt-4o-mini"

    # Planning
    planning_temperature: float = 0.3
    planning_max_tokens: int = 2048
    planning_model: str = "gpt-4o-mini"

    # Agent
    agent_temperature: float = 0.5
    agent_max_tokens: int = 4096
    agent_model: str = "gpt-4o-mini"

    # ... 더 많은 노드
```

### 4.3 Factory 함수

**위치**: `backend/app/config/llm_settings.py`

```python
def get_llm_settings(
    environment: Environment = Environment.DEVELOPMENT,
    overrides: Optional[Dict[str, Any]] = None
) -> LLMSettings:
    """환경별 LLM 설정 생성

    Args:
        environment: 환경 (production/development/testing)
        overrides: 커스텀 오버라이드 (optional)

    Returns:
        LLMSettings 인스턴스
    """

def get_llm_settings_from_env() -> LLMSettings:
    """환경 변수로부터 LLM 설정 가져오기

    SYSTEM_ENV 환경 변수 읽어서 적절한 설정 반환

    Returns:
        LLMSettings 인스턴스
    """
```

### 4.4 Graph Builder

**위치**: `backend/app/octostrator/supervisors/*/execute_graph.py`

```python
def build_execute_graph(
    state_class=None,
    context: Optional[AppContext] = None
) -> CompiledStateGraph:
    """Execute Graph 빌드

    Args:
        state_class: State 클래스 (optional)
        context: AppContext (optional, 자동 생성됨)

    Returns:
        Compiled LangGraph
    """
```

### 4.5 Node 함수 시그니처

```python
def node_function(state: dict, runtime: Runtime) -> dict:
    """Node 함수

    Args:
        state: 그래프 상태
        runtime: LangGraph Runtime (자동 주입)

    Returns:
        업데이트된 상태
    """
    context: AppContext = runtime.context
    # ...
    return updated_state
```

---

## 5. Best Practices

### 5.1 Context는 불변으로 유지

**❌ 잘못된 예시**:
```python
def execute_node(state: dict, runtime: Runtime):
    context = runtime.context
    context.user_id = "new_user"  # ❌ 변경하지 마세요!
```

**✅ 올바른 예시**:
```python
def execute_node(state: dict, runtime: Runtime):
    context = runtime.context
    # Context는 읽기 전용으로 사용
    logger.info(f"User={context.user_id}")
```

### 5.2 metrics는 수집만 (변경 가능)

**✅ 올바른 예시**:
```python
def execute_node(state: dict, runtime: Runtime):
    context = runtime.context
    # metrics는 수집 용도로 변경 가능
    context.metrics["execution_time"] = 1.23
    context.metrics["agent_count"] = 5
```

### 5.3 runtime=None 체크 (Backward Compatibility)

**✅ 올바른 예시**:
```python
def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """Agent용 LLM 생성"""

    # Phase 2+: Context API 사용
    if runtime is not None:
        try:
            context = runtime.context
            return ChatOpenAI(
                model=context.llm_settings.agent_model,
                temperature=context.llm_settings.agent_temperature,
                max_tokens=context.llm_settings.agent_max_tokens
            )
        except Exception as e:
            logger.warning(f"Failed to use Context API: {e}")

    # Phase 1: Fallback
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

### 5.4 디버그 로그는 debug=True 시에만

**✅ 올바른 예시**:
```python
def execute_node(state: dict, runtime: Runtime):
    context = runtime.context

    # 항상 출력
    logger.info(f"[Execute] User={context.user_id}")

    # 디버그 모드에만 출력
    if context.debug:
        logger.debug(f"[DEBUG] Full state: {state}")
        logger.debug(f"[DEBUG] Todos: {state.get('todos')}")
```

### 5.5 메트릭은 일관된 키 사용

**✅ 올바른 예시**:
```python
# 일관된 네이밍: {node}_{metric}
context.metrics["execute_duration"] = 1.23
context.metrics["execute_agent_count"] = 5
context.metrics["cognitive_duration"] = 0.45
context.metrics["agent_DietAgent_duration"] = 0.67
context.metrics["agent_DietAgent_tokens"] = 1500
```

---

## 6. Troubleshooting

### 6.1 Context API가 동작하지 않음

**증상**: runtime이 None이거나 context가 없음

**원인**: `context_schema` 누락

**해결**:
```python
# ❌ 잘못된 코드
graph = StateGraph(OctostratorState)

# ✅ 올바른 코드
graph = StateGraph(OctostratorState, context_schema=type(context))
```

### 6.2 Pydantic ValidationError

**증상**: `ValidationError: temperature must be <= 2.0`

**원인**: 설정 값이 범위를 벗어남

**해결**:
```python
# llm_settings.py에서 preset 수정
PRODUCTION_PRESET = {
    "agent_temperature": 0.4,  # ✅ 0.0 ~ 2.0 범위
    "agent_max_tokens": 3500,  # ✅ 1 ~ 16384 범위
}
```

### 6.3 환경 변수가 반영되지 않음

**증상**: SYSTEM_ENV=production인데 development 설정 사용

**원인**: 서비스 재시작 안 함

**해결**:
```bash
# 서비스 재시작
docker-compose restart  # 또는
pm2 restart all
```

### 6.4 메트릭이 반환되지 않음

**증상**: API 응답에 metrics 필드 없음

**원인**: API 엔드포인트에서 metrics 반환 안 함

**해결**:
```python
@app.post("/api/octo/invoke")
async def invoke_octostrator(request: Request):
    # ...
    result = await graph.ainvoke(request.input)

    # ✅ 메트릭 반환
    return {
        "result": result,
        "trace_id": context.trace_id,
        "metrics": context.metrics  # ← 추가!
    }
```

### 6.5 디버그 모드가 적용되지 않음

**증상**: X-Debug-Mode: true인데 디버그 로그 안 나옴

**원인**: logging 설정 문제

**해결**:
```python
if context.debug:
    # ✅ 로거 레벨 변경
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
```

---

## 📚 참고 문서

- [Context API 로드맵](./CONTEXT_API_ROADMAP.md)
- [Phase 3 Quick Start](./PHASE3_QUICK_START_GUIDE.md)
- [Phase 2 완료 보고서](../merge/PHASE2_CONTEXT_API_COMPLETION_REPORT_251106.md)
- [LangGraph Context API 공식 문서](https://langchain-ai.github.io/langgraph/)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Status**: 📖 MANUAL
**Author**: AI PT Manager Development Team
