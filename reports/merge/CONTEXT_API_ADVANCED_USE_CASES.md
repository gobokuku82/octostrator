# Context API 고급 활용 방안

**작성일**: 2025-11-06
**버전**: 1.0
**상태**: 📋 RESEARCH

---

## 📋 개요

Phase 2에서 Context API를 **환경별 LLM 설정 전환** 용도로 구현했습니다. 하지만 LangGraph Context API는 훨씬 더 많은 활용 방안이 있습니다. 이 문서는 Context API의 추가 활용 가능한 패턴들을 정리합니다.

### 현재 사용 중 (Phase 2)
✅ **환경별 LLM 설정**
- Production: 비용 최적화 (낮은 temp, 적은 tokens)
- Development: 품질 우선 (높은 temp, 넉넉한 tokens)
- Testing: 재현성 (temp=0, 최소 tokens)

### 미사용 필드 (AppContext)
⚠️ **현재 정의되어 있지만 활용하지 않는 필드들**:
- `user_id`: 사용자 ID (정의만 됨)
- `session_id`: 세션 ID (정의만 됨)
- `db_conn`: DB 연결 (Phase 5 예정)
- `debug`: 디버그 모드 (정의만 됨)

---

## 🎯 Context API 활용 방안 카탈로그

### 1. 사용자별 맞춤 설정 (User-Specific Configuration)

**개념**: `user_id`를 활용하여 사용자별로 다른 LLM 설정 적용

**활용 사례**:
```python
@dataclass
class AppContext:
    user_id: str
    llm_settings: LLMSettings
    user_preferences: Optional[Dict] = None

def _create_llm_for_agents(runtime: Runtime) -> ChatOpenAI:
    context: AppContext = runtime.context

    # 사용자별 맞춤 설정 적용
    if context.user_id.startswith("premium_"):
        # 프리미엄 사용자: GPT-4 사용
        model = "gpt-4o"
        max_tokens = 8000
    elif context.user_id.startswith("trial_"):
        # 체험 사용자: 제한된 설정
        model = "gpt-4o-mini"
        max_tokens = 2000
    else:
        # 일반 사용자: 기본 설정
        model = context.llm_settings.agent_model
        max_tokens = context.llm_settings.agent_max_tokens

    return ChatOpenAI(model=model, max_tokens=max_tokens)
```

**효과**:
- ✅ 사용자 등급별 차별화 서비스
- ✅ 비용 최적화 (체험/일반/프리미엄)
- ✅ 개인화된 사용자 경험

---

### 2. 세션 관리 및 Rate Limiting

**개념**: `session_id`를 활용하여 세션별 요청 제한 및 추적

**활용 사례**:
```python
from collections import defaultdict
from datetime import datetime, timedelta

# 세션별 요청 카운터 (실제로는 Redis 등 사용)
session_request_count = defaultdict(int)
session_last_reset = {}

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    rate_limit: int = 100  # 세션당 최대 요청 수

def check_rate_limit(runtime: Runtime) -> bool:
    """세션별 Rate Limiting 체크"""
    context: AppContext = runtime.context
    session_id = context.session_id

    # 시간 기반 리셋 (1시간마다)
    now = datetime.now()
    if session_id in session_last_reset:
        if now - session_last_reset[session_id] > timedelta(hours=1):
            session_request_count[session_id] = 0
            session_last_reset[session_id] = now
    else:
        session_last_reset[session_id] = now

    # Rate limit 체크
    if session_request_count[session_id] >= context.rate_limit:
        return False  # 제한 초과

    session_request_count[session_id] += 1
    return True

def execute_node(state: dict, runtime: Runtime):
    """Execute 노드에서 Rate Limiting 적용"""
    if not check_rate_limit(runtime):
        raise Exception(f"Rate limit exceeded for session {runtime.context.session_id}")

    # 정상 처리
    # ...
```

**효과**:
- ✅ 남용 방지 (Abuse prevention)
- ✅ 세션별 요청 추적
- ✅ 비용 통제

---

### 3. DB 연결 공유 (Database Connection Pooling)

**개념**: `db_conn`을 활용하여 모든 노드에서 DB 연결 재사용

**활용 사례**:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    db_conn: Optional[str] = None
    db_session: Optional[Any] = None  # SQLAlchemy Session

def build_octostrator_graph(context: Optional[AppContext] = None):
    """Graph 빌드 시 DB 세션 생성"""
    if context is None:
        from backend.app.config.system import config

        # DB 연결 생성
        engine = create_engine(config.postgres_url)
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()

        context = AppContext(
            user_id="default",
            session_id="default",
            llm_settings=get_llm_settings_from_env(),
            db_conn=config.postgres_url,
            db_session=db_session  # 세션 공유!
        )

    graph = StateGraph(OctostratorState, context_schema=type(context))
    # ...
    return graph.compile(checkpointer=checkpointer)

def execute_node(state: dict, runtime: Runtime):
    """모든 노드에서 동일한 DB 세션 사용"""
    context: AppContext = runtime.context
    db_session = context.db_session

    # DB 쿼리 실행
    user = db_session.query(User).filter_by(id=context.user_id).first()

    # Agent 실행 결과 DB 저장
    result = execute_agent(...)
    db_session.add(AgentResult(result=result))
    db_session.commit()
```

**효과**:
- ✅ DB 연결 재사용 (connection pooling)
- ✅ 트랜잭션 관리 용이
- ✅ 성능 향상

---

### 4. 디버그 모드 및 상세 로깅

**개념**: `debug` 플래그를 활용하여 개발 환경에서 상세 로깅

**활용 사례**:
```python
import logging

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    debug: bool = False
    log_level: str = "INFO"

def _create_llm_for_agents(runtime: Runtime) -> ChatOpenAI:
    context: AppContext = runtime.context

    # 디버그 모드 활성화 시 상세 로깅
    if context.debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug(f"[DEBUG] Creating LLM for user={context.user_id}")
        logger.debug(f"[DEBUG] Settings: temp={context.llm_settings.agent_temperature}, "
                     f"tokens={context.llm_settings.agent_max_tokens}")

    llm = ChatOpenAI(
        model=context.llm_settings.agent_model,
        temperature=context.llm_settings.agent_temperature,
        max_tokens=context.llm_settings.agent_max_tokens,
        verbose=context.debug  # LangChain verbose 모드
    )

    return llm

# API 엔드포인트에서 디버그 모드 활성화
@app.post("/api/octo/invoke")
async def invoke_octostrator(request: Request):
    debug_mode = request.headers.get("X-Debug-Mode", "false") == "true"

    context = AppContext(
        user_id=request.user_id,
        session_id=request.session_id,
        llm_settings=get_llm_settings_from_env(),
        debug=debug_mode  # 헤더로 디버그 모드 제어
    )

    graph = build_octostrator_graph(context=context)
    result = await graph.ainvoke(...)
    return result
```

**효과**:
- ✅ 개발 환경에서 상세 디버깅
- ✅ Production 환경에서는 로깅 최소화
- ✅ 문제 발생 시 빠른 진단

---

### 5. A/B 테스트 및 실험 (Experimentation)

**개념**: Context에 실험 설정을 추가하여 A/B 테스트 수행

**활용 사례**:
```python
from enum import Enum

class ExperimentGroup(str, Enum):
    CONTROL = "control"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    experiment_group: ExperimentGroup = ExperimentGroup.CONTROL
    experiment_id: Optional[str] = None

def _create_llm_for_agents(runtime: Runtime) -> ChatOpenAI:
    context: AppContext = runtime.context

    # A/B 테스트: 그룹별로 다른 설정 적용
    if context.experiment_group == ExperimentGroup.VARIANT_A:
        # Variant A: 높은 temperature 테스트
        temperature = 0.8
        max_tokens = 6000
    elif context.experiment_group == ExperimentGroup.VARIANT_B:
        # Variant B: 낮은 temperature 테스트
        temperature = 0.3
        max_tokens = 3000
    else:
        # Control: 기본 설정
        temperature = context.llm_settings.agent_temperature
        max_tokens = context.llm_settings.agent_max_tokens

    logger.info(f"[Experiment] Group={context.experiment_group}, "
                f"ID={context.experiment_id}, temp={temperature}")

    return ChatOpenAI(
        model=context.llm_settings.agent_model,
        temperature=temperature,
        max_tokens=max_tokens
    )

# 실험 결과 추적
def response_layer_node(state: dict, runtime: Runtime):
    context: AppContext = runtime.context

    # 실험 메트릭 기록
    if context.experiment_id:
        log_experiment_metric(
            experiment_id=context.experiment_id,
            group=context.experiment_group,
            user_id=context.user_id,
            response_quality=calculate_quality(state["response"]),
            cost=estimate_cost(state)
        )

    return state
```

**효과**:
- ✅ 새로운 설정 안전하게 테스트
- ✅ 데이터 기반 최적화
- ✅ 점진적 롤아웃 가능

---

### 6. 권한 관리 (Authorization & Permissions)

**개념**: Context에 권한 정보를 추가하여 노드별 접근 제어

**활용 사례**:
```python
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    user_role: UserRole = UserRole.USER
    permissions: List[str] = None

def execute_node(state: dict, runtime: Runtime):
    """권한 체크 후 Agent 실행"""
    context: AppContext = runtime.context

    # 관리자만 특정 Agent 실행 가능
    if "AdminAgent" in state["todos"]:
        if context.user_role != UserRole.ADMIN:
            raise PermissionError(f"User {context.user_id} does not have admin access")

    # 정상 처리
    results = []
    for todo in state["todos"]:
        # 권한 체크
        if not has_permission(context, todo["agent_name"]):
            logger.warning(f"User {context.user_id} denied access to {todo['agent_name']}")
            continue

        result = execute_agent(todo, runtime)
        results.append(result)

    return {"results": results}

def has_permission(context: AppContext, agent_name: str) -> bool:
    """권한 체크 헬퍼 함수"""
    if context.user_role == UserRole.ADMIN:
        return True  # 관리자는 모든 권한

    # Guest는 제한된 Agent만
    if context.user_role == UserRole.GUEST:
        allowed_agents = ["FrontdeskAgent", "InfoAgent"]
        return agent_name in allowed_agents

    return True  # 일반 사용자는 대부분 허용
```

**효과**:
- ✅ 세밀한 접근 제어
- ✅ 보안 강화
- ✅ 역할 기반 기능 제공

---

### 7. 캐싱 전략 (Caching Strategy)

**개념**: Context에 캐싱 설정을 추가하여 중복 요청 최적화

**활용 사례**:
```python
from functools import lru_cache
import hashlib

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1시간

# 간단한 캐시 (실제로는 Redis 등 사용)
response_cache = {}

def cognitive_layer_node(state: dict, runtime: Runtime):
    """Cognitive 노드에서 캐싱 적용"""
    context: AppContext = runtime.context
    user_input = state.get("user_input", "")

    # 캐싱 활성화 시 캐시 체크
    if context.enable_cache:
        cache_key = hashlib.md5(
            f"{context.user_id}:{user_input}".encode()
        ).hexdigest()

        if cache_key in response_cache:
            logger.info(f"[Cache] Hit for user={context.user_id}")
            return response_cache[cache_key]

    # 캐시 미스: LLM 호출
    llm = _create_llm_for_cognitive(runtime)
    response = llm.invoke(user_input)

    # 캐시 저장
    if context.enable_cache:
        response_cache[cache_key] = response

    return {"intent": response}

# API 엔드포인트에서 캐싱 제어
@app.post("/api/octo/invoke")
async def invoke_octostrator(request: Request):
    enable_cache = request.query_params.get("cache", "true") == "true"

    context = AppContext(
        user_id=request.user_id,
        session_id=request.session_id,
        llm_settings=get_llm_settings_from_env(),
        enable_cache=enable_cache
    )

    graph = build_octostrator_graph(context=context)
    result = await graph.ainvoke(...)
    return result
```

**효과**:
- ✅ 중복 요청 제거
- ✅ 응답 속도 향상
- ✅ 비용 절감 (LLM 호출 감소)

---

### 8. 모니터링 및 추적 (Observability)

**개념**: Context에 추적 정보를 추가하여 분산 추적 (Distributed Tracing)

**활용 사례**:
```python
import time
from dataclasses import field
from typing import Dict, List

@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metrics: Dict[str, Any] = field(default_factory=dict)

def execute_node(state: dict, runtime: Runtime):
    """실행 메트릭 수집"""
    context: AppContext = runtime.context
    start_time = time.time()

    # Agent 실행
    results = []
    for todo in state["todos"]:
        agent_start = time.time()
        result = execute_agent(todo, runtime)
        agent_duration = time.time() - agent_start

        # 메트릭 기록
        context.metrics[f"agent_{todo['agent_name']}_duration"] = agent_duration
        results.append(result)

    total_duration = time.time() - start_time
    context.metrics["execute_total_duration"] = total_duration

    # 로깅 (분산 추적)
    logger.info(
        f"[Trace] ID={context.trace_id}, "
        f"User={context.user_id}, "
        f"Session={context.session_id}, "
        f"Duration={total_duration:.2f}s"
    )

    return {"results": results, "metrics": context.metrics}

def response_layer_node(state: dict, runtime: Runtime):
    """최종 메트릭 집계 및 전송"""
    context: AppContext = runtime.context

    # 메트릭 집계
    total_tokens = sum(
        result.get("tokens_used", 0)
        for result in state.get("results", [])
    )

    context.metrics["total_tokens"] = total_tokens
    context.metrics["total_cost"] = calculate_cost(total_tokens)

    # 외부 모니터링 시스템에 전송 (예: DataDog, Prometheus)
    send_metrics_to_monitoring(
        trace_id=context.trace_id,
        user_id=context.user_id,
        metrics=context.metrics
    )

    return state
```

**효과**:
- ✅ 성능 모니터링
- ✅ 병목 지점 파악
- ✅ 사용자별 사용 패턴 분석
- ✅ 비용 추적

---

### 9. Human-in-the-Loop (HITL)

**개념**: Context에 승인 설정을 추가하여 중요 작업 시 사람 검토

**활용 사례**:
```python
@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    require_approval: bool = False
    approval_webhook: Optional[str] = None

def execute_node(state: dict, runtime: Runtime):
    """중요 작업 시 승인 요청"""
    context: AppContext = runtime.context

    # 고비용 Agent 실행 전 승인 필요
    high_cost_agents = ["ReportGeneratorAgent", "AnalysisAgent"]

    for todo in state["todos"]:
        if todo["agent_name"] in high_cost_agents and context.require_approval:
            # 승인 요청
            approval_id = request_approval(
                context=context,
                todo=todo,
                webhook=context.approval_webhook
            )

            # LangGraph interrupt() 호출 (사람 검토 대기)
            from langgraph.runtime import interrupt
            approval = interrupt(
                f"Approval required for {todo['agent_name']}. "
                f"Approval ID: {approval_id}"
            )

            if not approval.get("approved", False):
                logger.info(f"Task {approval_id} rejected by user")
                continue

        # 승인됨 또는 승인 불필요: 실행
        result = execute_agent(todo, runtime)
        results.append(result)

    return {"results": results}
```

**효과**:
- ✅ 중요 결정에 사람 개입
- ✅ 위험 감소
- ✅ 품질 향상

---

### 10. Multi-Tenancy (다중 테넌트)

**개념**: Context에 조직 정보를 추가하여 멀티 테넌트 지원

**활용 사례**:
```python
@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    organization_id: str
    tenant_settings: Dict[str, Any] = None

def _create_llm_for_agents(runtime: Runtime) -> ChatOpenAI:
    context: AppContext = runtime.context

    # 조직별 API 키 사용
    api_key = get_org_api_key(context.organization_id)

    # 조직별 커스텀 설정
    tenant_settings = context.tenant_settings or {}
    model = tenant_settings.get("model", context.llm_settings.agent_model)

    return ChatOpenAI(
        model=model,
        api_key=api_key  # 조직별 API 키!
    )

def execute_node(state: dict, runtime: Runtime):
    """조직별 격리된 실행"""
    context: AppContext = runtime.context

    # 조직별 DB 스키마 사용
    db_schema = f"org_{context.organization_id}"

    # 조직별 데이터만 접근
    with db_session(schema=db_schema) as session:
        results = execute_agents(state["todos"], session, runtime)

    return {"results": results}
```

**효과**:
- ✅ 조직별 데이터 격리
- ✅ 조직별 커스텀 설정
- ✅ SaaS 비즈니스 모델 지원

---

## 📊 활용 방안 우선순위 매트릭스

### 구현 난이도 vs 비즈니스 가치

| 활용 방안 | 구현 난이도 | 비즈니스 가치 | 우선순위 | Phase |
|----------|-----------|-------------|---------|-------|
| ✅ 환경별 LLM 설정 | 낮음 | 높음 | P0 | Phase 2 (완료) |
| 디버그 모드 | 낮음 | 중간 | P1 | Phase 3 권장 |
| 사용자별 맞춤 설정 | 중간 | 높음 | P1 | Phase 3 권장 |
| DB 연결 공유 | 중간 | 높음 | P1 | Phase 5 예정 |
| 모니터링 및 추적 | 중간 | 높음 | P1 | Phase 4 권장 |
| Rate Limiting | 중간 | 중간 | P2 | Phase 6 선택 |
| 캐싱 전략 | 중간 | 중간 | P2 | Phase 6 선택 |
| 권한 관리 | 높음 | 중간 | P2 | Phase 7 선택 |
| A/B 테스트 | 높음 | 중간 | P3 | Phase 8 선택 |
| HITL | 높음 | 낮음 | P3 | Phase 9 선택 |
| Multi-Tenancy | 높음 | 높음* | P3 | Phase 10 선택 |

*Multi-Tenancy는 SaaS 비즈니스 모델 시 필수

---

## 🎯 권장 구현 순서

### Phase 3 (권장)
1. **디버그 모드** - 개발 생산성 향상
2. **사용자별 맞춤 설정** - 사용자 경험 개선
3. **모니터링 및 추적** - 운영 가시성 확보

### Phase 4 (선택)
4. **Rate Limiting** - 남용 방지
5. **캐싱 전략** - 성능 및 비용 최적화

### Phase 5 (DB 통합)
6. **DB 연결 공유** - 트랜잭션 관리

### Phase 6+ (고급)
7. **권한 관리** - 보안 강화
8. **A/B 테스트** - 데이터 기반 최적화
9. **HITL** - 중요 결정 검토
10. **Multi-Tenancy** - SaaS 대응

---

## 📝 구현 예시: Phase 3 Quick Start

### 디버그 모드 + 모니터링 통합

**1. AppContext 확장**:
```python
@dataclass
class AppContext:
    # 기존 (Phase 2)
    user_id: str
    session_id: str
    llm_settings: LLMSettings

    # 신규 (Phase 3)
    debug: bool = False
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metrics: Dict[str, Any] = field(default_factory=dict)
```

**2. execute_nodes.py 수정**:
```python
def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    if runtime is not None:
        context: AppContext = runtime.context

        # Phase 3: 디버그 모드 활성화
        if context.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(f"[DEBUG] Trace={context.trace_id}, User={context.user_id}")

        return ChatOpenAI(
            model=context.llm_settings.agent_model,
            temperature=context.llm_settings.agent_temperature,
            max_tokens=context.llm_settings.agent_max_tokens,
            verbose=context.debug  # LangChain verbose 모드
        )

    # Fallback: Phase 1 모드
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)
```

**3. API 엔드포인트**:
```python
@app.post("/api/octo/invoke")
async def invoke_octostrator(request: Request):
    debug_mode = request.headers.get("X-Debug-Mode", "false") == "true"

    context = AppContext(
        user_id=request.user_id,
        session_id=request.session_id,
        llm_settings=get_llm_settings_from_env(),
        debug=debug_mode,  # 헤더로 디버그 제어
        trace_id=request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    )

    graph = build_octostrator_graph(context=context)
    result = await graph.ainvoke(request.input)

    # 메트릭 반환
    return {
        "result": result,
        "trace_id": context.trace_id,
        "metrics": context.metrics
    }
```

**변경량**: ~30 lines (Phase 2와 유사하게 최소 수정)

---

## 🏆 요약

### 현재 상태 (Phase 2)
✅ Context API 인프라 구축 완료
✅ 환경별 LLM 설정 (45.9% 비용 절감)
✅ `user_id`, `session_id`, `debug` 필드 정의됨 (미사용)

### 추가 활용 가능 (10가지)
1. ✅ 환경별 LLM 설정 (Phase 2 완료)
2. ⏳ 디버그 모드 (Phase 3 권장)
3. ⏳ 사용자별 맞춤 설정 (Phase 3 권장)
4. ⏳ 모니터링 및 추적 (Phase 3 권장)
5. ⏳ Rate Limiting (Phase 4 선택)
6. ⏳ 캐싱 전략 (Phase 4 선택)
7. ⏳ DB 연결 공유 (Phase 5 예정)
8. ⏳ 권한 관리 (Phase 6+ 고급)
9. ⏳ A/B 테스트 (Phase 6+ 고급)
10. ⏳ Multi-Tenancy (Phase 10 선택)

### 권장 사항
- **Phase 3 우선 구현**: 디버그 모드 + 모니터링 (개발 생산성 & 운영 가시성)
- **Phase 4 선택 구현**: Rate Limiting + 캐싱 (비용 최적화)
- **Phase 5+ 고급 기능**: 필요시 점진적 추가

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Status**: 📋 RESEARCH
**Author**: AI PT Manager Development Team
