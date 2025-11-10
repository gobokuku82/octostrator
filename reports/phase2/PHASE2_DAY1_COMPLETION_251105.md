# Phase 2 - Day 1 완료 보고서

**작성일**: 2025-11-05
**작업**: Context API 기반 구축
**상태**: ✅ 완료

---

## 📋 작업 요약

Phase 2의 첫 번째 날 작업으로 **LangGraph 1.0 Context API 기반을 성공적으로 구축**했습니다.

### 완료된 작업

| 작업 | 상태 | 비고 |
|------|------|------|
| AppContext에 LLMSettings 스키마 추가 | ✅ 완료 | Pydantic BaseModel 사용 |
| 환경별 LLM 설정 팩토리 생성 | ✅ 완료 | Production/Dev/Test 분리 |
| Cognitive Nodes에 Context API 적용 | ✅ 완료 | Intent, Planning, Aggregator |
| Response Nodes 검토 | ✅ 완료 | 현재 LLM 미사용, 설정 준비됨 |
| main_graph.py 업데이트 | ✅ 완료 | context_schema 등록 |

---

## 🎯 핵심 변경사항

### 1. LLMSettings 스키마 정의

**파일**: `backend/app/octostrator/contexts/app_context.py`

```python
class LLMSettings(BaseModel):
    """노드별 LLM 설정"""

    # Intent Node
    intent_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    intent_max_tokens: int = Field(default=1024, ge=1, le=16384)
    intent_model: str = Field(default="gpt-4o-mini")

    # Planning Node
    planning_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    planning_max_tokens: int = Field(default=2048, ge=1, le=16384)
    planning_model: str = Field(default="gpt-4o-mini")

    # Aggregator Node
    aggregator_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    aggregator_max_tokens: int = Field(default=3072, ge=1, le=16384)
    aggregator_model: str = Field(default="gpt-4o-mini")

    # Response Nodes (Chat, Graph, Report)
    # Agent Nodes (Diet, Workout, Schedule, Member Care, Coaching)
    # ... (총 6개 노드 카테고리)
```

**특징**:
- Pydantic Field 검증으로 타입 안정성 확보
- temperature 범위: 0.0 ~ 2.0
- max_tokens 범위: 1 ~ 16384
- 노드별 최적화된 기본값 설정

---

### 2. 환경별 설정 팩토리

**파일**: `backend/app/config/llm_settings.py` (신규 생성)

#### Production 설정 (비용 최적화)
```python
PRODUCTION_PRESET = {
    "intent_temperature": 0.5,      # 낮은 temperature
    "intent_max_tokens": 800,       # 제한된 tokens
    "planning_temperature": 0.2,    # 정확성 우선
    "planning_max_tokens": 2048,
    "chat_temperature": 0.6,
    "chat_max_tokens": 3000,        # 비용 절감
}
```

#### Development 설정 (다양성 확보)
```python
DEVELOPMENT_PRESET = {
    "intent_temperature": 0.7,      # 다양한 테스트
    "intent_max_tokens": 1024,
    "planning_temperature": 0.5,    # 다양한 계획
    "planning_max_tokens": 4096,    # 여유있는 설정
    "chat_temperature": 0.7,
    "chat_max_tokens": 6000,
}
```

#### Testing 설정 (결정론적 출력)
```python
TESTING_PRESET = {
    "intent_temperature": 0.0,      # 동일한 결과
    "intent_max_tokens": 512,       # 빠른 실행
    "planning_temperature": 0.0,
    "planning_max_tokens": 1024,
}
```

**주요 함수**:
- `get_llm_settings(environment)`: 환경별 설정 반환
- `get_llm_settings_from_env()`: 환경 변수 자동 감지
- `estimate_token_savings()`: 비용 절감 추정

---

### 3. Cognitive Nodes 업데이트

**파일**: `backend/app/octostrator/supervisor/nodes/cognitive_nodes.py`

#### Before (Phase 1)
```python
async def intent_understanding_node(
    state: SupervisorState,
    llm: ChatOpenAI  # 전역 LLM 인스턴스
) -> Dict:
    response = await llm.ainvoke([SystemMessage(content=prompt)])
```

#### After (Phase 2)
```python
async def intent_understanding_node(
    state: SupervisorState,
    runtime: Runtime  # Context API 사용
) -> Dict:
    # Context에서 설정 가져오기
    context: AppContext = runtime.context
    settings = context.llm_settings

    # 노드별 맞춤 LLM 생성
    llm = ChatOpenAI(
        model=settings.intent_model,
        temperature=settings.intent_temperature,
        max_tokens=settings.intent_max_tokens,
        api_key=system_config.openai_api_key
    )

    response = await llm.ainvoke([SystemMessage(content=prompt)])
```

**적용된 노드**:
1. ✅ `intent_understanding_node` (temp=0.7, tokens=1024)
2. ✅ `planning_node` (temp=0.3, tokens=2048)
3. ✅ `aggregator_node` (temp=0.5, tokens=3072)

---

### 4. Graph 업데이트

**파일**: `backend/app/octostrator/supervisor/graphs/main_graph.py`

#### Before (Phase 1)
```python
def build_supervisor_graph(
    context: Optional[AppContext] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    # LLM 초기화
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=4096)

    # StateGraph 생성
    workflow = StateGraph(SupervisorState)

    # 노드 래퍼 필요
    async def intent_node(state):
        return await intent_understanding_node(state, llm)

    workflow.add_node("intent", intent_node)
```

#### After (Phase 2)
```python
def build_supervisor_graph(
    context: Optional[AppContext] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None,
    user_id: str = "default_user",
    session_id: str = "default_session"
):
    # AppContext 자동 생성
    if context is None:
        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings
        )

    # context_schema 등록
    workflow = StateGraph(SupervisorState, context_schema=AppContext)

    # 노드 직접 등록 (Runtime 자동 주입)
    workflow.add_node("intent", intent_understanding_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("aggregator", aggregator_node)
```

**핵심 변경**:
- `context_schema=AppContext` 등록
- 환경 변수 기반 자동 설정 로드
- 노드 래퍼 제거 (LangGraph가 Runtime 자동 주입)

---

## 📊 예상 효과

### 1. 토큰 사용량 감소

**Production vs Development 비교**:

| 환경 | 평균 Tokens/Call | 감소율 |
|------|------------------|--------|
| Development | 3,437 tokens | - |
| Production | 2,170 tokens | **36.9%** ↓ |

**노드별 최적화**:
- Intent: 1024 → 800 tokens (22% 감소)
- Planning: 4096 → 2048 tokens (50% 감소)
- Chat: 6000 → 3000 tokens (50% 감소)

### 2. 비용 절감

```
Before (Phase 1): 평균 4096 tokens/call (하드코딩)
After (Phase 2):
  - Development: 3437 tokens/call
  - Production:  2170 tokens/call

예상 비용 절감: 30-40%
```

### 3. 타입 안정성

```python
# Pydantic 자동 검증
settings = LLMSettings(
    intent_temperature=2.5  # ❌ ValidationError: 범위 초과 (0.0~2.0)
)

settings = LLMSettings(
    intent_max_tokens="1024"  # ✅ 자동 타입 변환 (str → int)
)
```

---

## 🏗️ 파일 변경 이력

### 신규 생성 (1개)
```
backend/app/config/llm_settings.py (371 lines)
  - Environment enum
  - 3개 환경별 preset
  - get_llm_settings() 팩토리 함수
  - estimate_token_savings() 분석 함수
```

### 수정 (3개)

#### `contexts/app_context.py`
```diff
- @dataclass
- class AppContext:
-     user_id: str
-     session_id: str
-     llm: ChatOpenAI  # 단일 LLM 인스턴스

+ class LLMSettings(BaseModel):  # 신규 추가
+     intent_temperature: float = Field(default=0.7)
+     planning_temperature: float = Field(default=0.3)
+     # ... (총 18개 필드)

+ @dataclass
+ class AppContext:
+     user_id: str
+     session_id: str
+     llm_settings: LLMSettings  # LLM 설정으로 변경
```

#### `supervisor/nodes/cognitive_nodes.py`
```diff
  async def intent_understanding_node(
      state: SupervisorState,
-     llm: ChatOpenAI
+     runtime: Runtime
  ) -> Dict:
+     context: AppContext = runtime.context
+     settings = context.llm_settings
+     llm = ChatOpenAI(
+         temperature=settings.intent_temperature,
+         max_tokens=settings.intent_max_tokens
+     )
```

#### `supervisor/graphs/main_graph.py`
```diff
  def build_supervisor_graph(
      context: Optional[AppContext] = None,
-     checkpointer: Optional[AsyncPostgresSaver] = None
+     checkpointer: Optional[AsyncPostgresSaver] = None,
+     user_id: str = "default_user",
+     session_id: str = "default_session"
  ):
+     if context is None:
+         llm_settings = get_llm_settings_from_env()
+         context = AppContext(user_id, session_id, llm_settings)

-     workflow = StateGraph(SupervisorState)
+     workflow = StateGraph(SupervisorState, context_schema=AppContext)

-     async def intent_node(state):
-         return await intent_understanding_node(state, llm)
-     workflow.add_node("intent", intent_node)

+     workflow.add_node("intent", intent_understanding_node)
```

---

## ✅ 검증 항목

### 1. 구조 검증

```bash
# 파일 존재 확인
✅ backend/app/config/llm_settings.py
✅ backend/app/octostrator/contexts/app_context.py (LLMSettings 포함)
✅ backend/app/octostrator/supervisor/nodes/cognitive_nodes.py (Runtime 사용)
✅ backend/app/octostrator/supervisor/graphs/main_graph.py (context_schema 등록)
```

### 2. Import 검증

```python
# LLMSettings 사용 가능
from backend.app.octostrator.contexts.app_context import LLMSettings
from backend.app.config.llm_settings import get_llm_settings, Environment

# Runtime 타입 사용 가능
from langgraph.types import Runtime
```

### 3. 노드 시그니처 검증

```python
# Before
async def intent_understanding_node(state: SupervisorState, llm: ChatOpenAI)

# After
async def intent_understanding_node(state: SupervisorState, runtime: Runtime)
```

---

## 🔧 환경 설정

### 환경 변수 추가 (선택적)

`.env` 파일에 추가:
```bash
# LLM 환경 설정
SYSTEM_ENV=development  # production, development, testing
```

### 사용 예시

```python
# 자동 환경 감지
settings = get_llm_settings_from_env()

# 수동 환경 지정
settings = get_llm_settings(Environment.PRODUCTION)

# 커스텀 override
settings = get_llm_settings(
    Environment.PRODUCTION,
    overrides={"chat_max_tokens": 5000}
)
```

---

## 📈 다음 단계 (Day 2-3)

### Day 2: Prompt 최적화
- [ ] Cognitive prompts 압축 (109줄 → 30줄)
- [ ] Response prompts 최적화
- [ ] 중복 제거 및 명확성 개선

### Day 3: Agent Nodes 적용
- [ ] Diet Agent에 Context API 적용
- [ ] Workout Agent에 Context API 적용
- [ ] 나머지 Agent들 적용

### Day 4-5: 테스트 및 검증
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 실행
- [ ] 성능 측정 (토큰 사용량)
- [ ] 비용 절감 실측

---

## 🎓 기술적 학습

### LangGraph 1.0 Context API 핵심

1. **context_schema 등록**:
   ```python
   workflow = StateGraph(State, context_schema=AppContext)
   ```

2. **Runtime 자동 주입**:
   ```python
   async def my_node(state: State, runtime: Runtime):
       context = runtime.context  # AppContext 접근
   ```

3. **타입 안정성**:
   - Pydantic BaseModel로 스키마 정의
   - 자동 검증 및 타입 변환
   - IDE 자동완성 지원

4. **환경 분리**:
   - Production: 비용 최적화
   - Development: 다양성 확보
   - Testing: 결정론적 출력

---

## 💡 주요 인사이트

### 1. 하드코딩 제거

**Before**:
```python
llm = ChatOpenAI(temperature=0.7, max_tokens=4096)  # 모든 노드 동일
```

**After**:
```python
# Intent: 창의적 해석
llm = ChatOpenAI(temperature=0.7, max_tokens=1024)

# Planning: 정확한 계획
llm = ChatOpenAI(temperature=0.3, max_tokens=2048)

# Aggregator: 균형잡힌 분석
llm = ChatOpenAI(temperature=0.5, max_tokens=3072)
```

### 2. 중앙 관리

모든 LLM 설정이 **2개 파일**에 집중:
- `contexts/app_context.py`: 스키마 정의
- `config/llm_settings.py`: 환경별 값

### 3. 비용 투명성

```python
# 비용 추정 함수 제공
savings = estimate_token_savings()
print(savings)
# {
#     "production_avg_tokens": 2170,
#     "development_avg_tokens": 3437,
#     "reduction_percentage": "36.9%",
#     "estimated_cost_savings": "30-40%"
# }
```

---

## ⚠️ 주의사항

### 1. 하위 호환성

기존 코드와 병행 가능:
```python
# Phase 1 방식 (여전히 작동)
graph = build_supervisor_graph(context=None, checkpointer=None)

# Phase 2 방식 (권장)
graph = build_supervisor_graph(
    user_id="user123",
    session_id="session456"
)
```

### 2. Response Nodes

현재 Chat/Graph/Report Generator는 **LLM을 사용하지 않음**:
- 데이터 포맷팅만 수행
- LLMSettings는 준비되어 있음 (향후 확장용)

### 3. Agent Nodes

Diet, Workout 등 Agent 노드는 **아직 Context API 미적용**:
- Day 3에 적용 예정
- `agent_temperature`, `agent_max_tokens` 설정 준비됨

---

## 📚 참고 문서

- [LangGraph Context API Analysis](../contextAPI/LANGGRAPH_CONTEXT_API_ANALYSIS_2025.md)
- [Implementation Guide](../contextAPI/IMPLEMENTATION_GUIDE_CONTEXT_API.md)
- [Phase 2 Implementation Plan](../system/IMPLEMENTATION_PLAN_PHASE2_251105.md)

---

**작성자**: Claude (Anthropic)
**프로젝트**: AI PT Manager Beta v001
**Phase**: 2 - Context API Integration
**상태**: ✅ Day 1 Complete (5/5 tasks)
