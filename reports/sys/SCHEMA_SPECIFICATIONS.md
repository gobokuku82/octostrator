# Schema 명세서 (Schema Specifications)

**작성일**: 2025-11-06
**목적**: 전체 시스템의 Schema 및 State 구조 명세
**상태**: Living Document (지속 업데이트)

---

## 📑 목차 (Table of Contents)

1. [개요 (Overview)](#개요-overview)
2. [아키텍처 원칙 (Architecture Principles)](#아키텍처-원칙-architecture-principles)
3. [Core Schemas](#core-schemas)
   - [OctostratorState](#octostratorstate)
   - [AppContext](#appcontext)
   - [LLMSettings](#llmsettings)
   - [UserTier](#usertier)
4. [Supervisor States](#supervisor-states)
   - [CognitiveState](#cognitivestate)
   - [TodoState](#todostate)
   - [ExecuteState](#executestate)
   - [ResponseState](#responsestate)
5. [Worker Agent States](#worker-agent-states)
   - [FrontdeskState](#frontdeskstate)
   - [AssessorState](#assessorstate)
   - [ProgramDesignerState](#programdesignerstate)
   - [ManagerState](#managerstate)
   - [MarketingState](#marketingstate)
   - [OwnerAssistantState](#ownerassistantstate)
   - [TrainerEducationState](#trainereducationstate)
6. [Base Schemas](#base-schemas)
   - [BaseState](#basestate)
   - [BaseAgentState](#baseagentstate)
7. [Type Definitions](#type-definitions)
8. [Serialization Rules](#serialization-rules)
9. [Validation Rules](#validation-rules)
10. [Change History](#change-history)

---

## 개요 (Overview)

### 문서 목적

이 문서는 AI PT Manager 시스템의 모든 Schema 및 State 구조를 정의합니다. 각 Schema의 필드, 타입, 제약조건, 사용 목적을 명확히 기술하여 일관성 있는 개발을 보장합니다.

### Schema 분류

```
Schemas
├── Core Schemas              # 시스템 핵심 구조
│   ├── OctostratorState      # 메인 오케스트레이터 상태
│   ├── AppContext            # 런타임 컨텍스트 (Phase 3)
│   └── LLMSettings           # LLM 설정 (Phase 2/3)
│
├── Supervisor States         # 각 Layer의 Supervisor 상태
│   ├── CognitiveState        # Layer 1: Planning
│   ├── TodoState             # Layer 2: Todo Management
│   ├── ExecuteState          # Layer 3: Execution
│   └── ResponseState         # Layer 4: Response Generation
│
├── Worker Agent States       # 비즈니스 로직 Agent 상태
│   ├── FrontdeskState        # 프론트데스크 응대
│   ├── AssessorState         # 회원 평가
│   ├── ProgramDesignerState  # 프로그램 설계
│   ├── ManagerState          # 센터 관리
│   ├── MarketingState        # 마케팅
│   ├── OwnerAssistantState   # 원장 보조
│   └── TrainerEducationState # 트레이너 교육
│
└── Base Schemas              # 공통 베이스 클래스
    ├── BaseState             # Supervisor용 베이스
    └── BaseAgentState        # Agent용 베이스
```

---

## 아키텍처 원칙 (Architecture Principles)

### Phase 3 핵심 원칙: State/Context/Config 분리

```
┌─────────────────────────────────────────────────────────────┐
│                 Phase 3 Architecture                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  State (TypedDict)          Context (dataclass)            │
│  ━━━━━━━━━━━━━━━            ━━━━━━━━━━━━━━━━━              │
│  • 직렬화 가능한 데이터       • 불변 런타임 정보             │
│  • msgpack 저장             • LangGraph Runtime            │
│  • Checkpoint 대상          • Checkpoint 제외               │
│  • 변경 가능 (mutable)       • 요청별 생성                  │
│                                                             │
│  예시:                      예시:                           │
│  - user_query: str          - llm_settings: LLMSettings    │
│  - plan: dict               - user_tier: UserTier          │
│  - todos: List[Dict]        - trace_id: str                │
│  - final_response: str      - debug: bool                  │
│                                                             │
│  Config (.env)                                             │
│  ━━━━━━━━━━━━━━━                                           │
│  • 환경별 설정                                              │
│  • openai_api_key                                          │
│  • postgres_url                                            │
│  • system_debug                                            │
└─────────────────────────────────────────────────────────────┘
```

### 직렬화 규칙 (Serialization Rules)

**State에 포함 가능** ✅:
- 기본 타입: str, int, float, bool, None
- 컬렉션: list, dict, tuple, set (직렬화 가능한 항목만)
- Optional 타입
- TypedDict, dataclass (직렬화 가능한 필드만)

**State에 포함 불가** ❌:
- LLM 인스턴스 (ChatOpenAI 등)
- Checkpointer 인스턴스 (AsyncPostgresSaver)
- Runtime 객체
- 함수, 람다
- 파일 핸들
- 데이터베이스 연결

### LangGraph 1.0+ Context API

```python
# ✅ Correct Usage (Phase 3)

from langraph.graph import StateGraph

# 1. Context schema 정의
graph = StateGraph(
    OctostratorState,
    context_schema=AppContext  # Context API 활성화
)

# 2. 노드에서 runtime 접근
async def my_node(state: OctostratorState, runtime: Optional[Runtime] = None):
    if runtime is not None:
        context: AppContext = runtime.context
        llm_settings = context.llm_settings
        # ...
```

---

## Core Schemas

### OctostratorState

**파일**: `backend/app/octostrator/states/octostrator_state.py`

**설명**: 메인 오케스트레이터의 State. 전체 대화 흐름의 상태를 관리합니다.

**Phase 3 업데이트**: llm, checkpointer, context 필드 제거 (직렬화 문제 해결)

#### Schema Definition

```python
class OctostratorState(TypedDict, total=False):
    """
    Main Octostrator State

    Phase 3: State에서 비직렬화 객체 제거
    - llm, checkpointer, context → Runtime을 통해 접근
    """

    # ===== User Input =====
    user_query: str                 # 사용자 질의 (필수)
    session_id: str                 # 세션 ID (필수)
    output_format: str              # 출력 형식 ("chat", "report", "graph")

    # ===== Current State =====
    plan: dict                      # Cognitive Layer에서 생성한 계획
    todos: Annotated[List[Dict], merge_todos_smart]  # Todo 목록 (Smart reducer)
    execution_results: dict         # Execute Layer 실행 결과
    final_response: str             # Response Layer 최종 응답

    # ===== Flags =====
    plan_valid: bool                # 계획 유효성
    requires_approval: bool         # HITL 승인 필요 여부
    error: Optional[str]            # 에러 메시지

    # ===== Conditional Flow Flags (Phase 2) =====
    plan_requires_todos: bool       # Todo Manager 필요 여부
    user_requested_todo_update: bool  # 사용자가 Todo 수정 요청
    need_todo_update: bool          # Execute에서 Todo 업데이트 필요

    # ===== History Tracking =====
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]
    plan_history: Annotated[List[Dict], track_plan_changes]
    user_interactions: Annotated[List[Dict], track_user_interactions]

    # ===== Metadata =====
    created_at: str                 # 생성 시각 (ISO 8601)
    updated_at: str                 # 최종 업데이트 시각
    total_steps: int                # 총 실행 스텝 수
```

#### Field Specifications

| 필드 | 타입 | 필수 | 기본값 | 설명 | Reducer |
|------|------|------|--------|------|---------|
| `user_query` | str | ✅ | - | 사용자 질의 | - |
| `session_id` | str | ✅ | - | 세션 ID | - |
| `output_format` | str | ❌ | "chat" | 출력 형식 | - |
| `plan` | dict | ❌ | {} | Cognitive 계획 | - |
| `todos` | List[Dict] | ❌ | [] | Todo 목록 | merge_todos_smart |
| `execution_results` | dict | ❌ | {} | 실행 결과 | - |
| `final_response` | str | ❌ | "" | 최종 응답 | - |
| `plan_valid` | bool | ❌ | False | 계획 유효성 | - |
| `requires_approval` | bool | ❌ | False | HITL 필요 | - |
| `error` | Optional[str] | ❌ | None | 에러 메시지 | - |
| `plan_requires_todos` | bool | ❌ | False | Todo Manager 실행 | - |
| `user_requested_todo_update` | bool | ❌ | False | 사용자 Todo 수정 | - |
| `need_todo_update` | bool | ❌ | False | Execute Todo 업데이트 | - |
| `action_history` | List[Dict] | ❌ | [] | 액션 히스토리 | add_with_timestamp_and_step |
| `plan_history` | List[Dict] | ❌ | [] | 계획 변경 히스토리 | track_plan_changes |
| `user_interactions` | List[Dict] | ❌ | [] | 사용자 상호작용 | track_user_interactions |
| `created_at` | str | ❌ | (auto) | 생성 시각 | - |
| `updated_at` | str | ❌ | (auto) | 업데이트 시각 | - |
| `total_steps` | int | ❌ | 0 | 총 스텝 수 | - |

#### Custom Reducers

**1. merge_todos_smart**

```python
def merge_todos_smart(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Smart Todo 병합
    - ID 기반 업데이트
    - 새 Todo 추가
    - 중복 제거
    """
```

**2. add_with_timestamp_and_step**

```python
def add_with_timestamp_and_step(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    타임스탬프 및 스텝 추가
    - 각 액션에 timestamp, step_number 자동 추가
    """
```

**3. track_plan_changes**

```python
def track_plan_changes(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    계획 변경 추적
    - 계획 수정 시 변경 내역 기록
    """
```

**4. track_user_interactions**

```python
def track_user_interactions(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    사용자 상호작용 추적
    - 사용자 입력, 승인, 거부 등 기록
    """
```

#### Validation Rules

1. **user_query**: 빈 문자열 불가
2. **session_id**: UUID 형식 권장
3. **output_format**: "chat", "report", "graph" 중 하나
4. **todos**: 각 Todo는 id, title, status 필드 필수
5. **plan_valid**: plan이 있으면 True여야 함

#### Usage Example

```python
from backend.app.octostrator.states import OctostratorState

# 초기 State 생성
state: OctostratorState = {
    "user_query": "회원 홍길동의 운동 프로그램 설계해줘",
    "session_id": "session_001",
    "output_format": "chat",
    "plan": {},
    "todos": [],
    "execution_results": {},
    "final_response": "",
    "plan_valid": False,
    "requires_approval": False,
    "error": None,
    "action_history": [],
    "plan_history": [],
    "user_interactions": [],
    "created_at": "2025-11-06T10:00:00Z",
    "updated_at": "2025-11-06T10:00:00Z",
    "total_steps": 0
}
```

---

### AppContext

**파일**: `backend/app/octostrator/contexts/app_context.py`

**설명**: 런타임 불변 정보를 담는 Context. LangGraph 1.0+ Context API를 사용하여 모든 노드에서 접근 가능합니다.

**Phase 2 업데이트**: LLMSettings 추가
**Phase 3 업데이트**: debug, trace_id, metrics, user_tier 추가

#### Schema Definition

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class AppContext:
    """
    Application Runtime Context

    Phase 3: Debug, Tracing, Metrics, UserTier 추가

    불변 정보만 포함:
    - Checkpoint에 저장되지 않음
    - 모든 노드에서 runtime을 통해 접근
    """

    # ===== User Information =====
    user_id: str                    # 사용자 ID
    session_id: str                 # 세션 ID

    # ===== LLM Settings (Phase 2) =====
    llm_settings: LLMSettings       # 노드별 LLM 설정

    # ===== Debug & Monitoring (Phase 3) =====
    debug: bool = False             # 디버그 모드
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 추적 ID
    metrics: Dict[str, Any] = field(default_factory=dict)  # 성능 메트릭
    log_level: str = "INFO"         # 로그 레벨

    # ===== User Tier (Phase 3) =====
    user_tier: UserTier = UserTier.STANDARD  # 사용자 등급

    # ===== Database (Phase 5) =====
    db_conn: Optional[str] = None   # DB 연결 문자열
```

#### Field Specifications

| 필드 | 타입 | 필수 | 기본값 | 설명 | Phase |
|------|------|------|--------|------|-------|
| `user_id` | str | ✅ | - | 사용자 ID | Phase 1 |
| `session_id` | str | ✅ | - | 세션 ID | Phase 1 |
| `llm_settings` | LLMSettings | ✅ | - | LLM 설정 | Phase 2 |
| `debug` | bool | ❌ | False | 디버그 모드 | Phase 3 |
| `trace_id` | str | ❌ | (UUID) | 분산 추적 ID | Phase 3 |
| `metrics` | Dict[str, Any] | ❌ | {} | 성능 메트릭 | Phase 3 |
| `log_level` | str | ❌ | "INFO" | 로그 레벨 | Phase 3 |
| `user_tier` | UserTier | ❌ | STANDARD | 사용자 등급 | Phase 3 |
| `db_conn` | Optional[str] | ❌ | None | DB 연결 | Phase 5 |

#### Usage Example

```python
from backend.app.octostrator.contexts.app_context import AppContext, create_app_context
from backend.app.config.llm_settings import get_llm_settings_for_user, UserTier

# Factory 함수 사용 (권장)
context = create_app_context(
    user_id="premium_user123",
    session_id="session_001",
    llm_settings=get_llm_settings_for_user(UserTier.PREMIUM),
    debug=True
)

# 자동 설정 확인
assert context.user_tier == UserTier.PREMIUM
assert context.log_level == "DEBUG"
assert context.trace_id is not None
```

#### Factory Functions

**1. get_user_tier(user_id: str) -> UserTier**

사용자 ID로부터 Tier 추출:
- `premium_*` → PREMIUM
- `trial_*` → TRIAL
- 그 외 → STANDARD

**2. create_app_context(...) -> AppContext**

AppContext 생성 Factory 함수:
- user_tier 자동 추출
- trace_id 자동 생성
- log_level 자동 설정

---

### LLMSettings

**파일**: `backend/app/octostrator/contexts/app_context.py`

**설명**: 노드별 LLM 파라미터 설정. Pydantic BaseModel을 사용하여 타입 안정성을 확보합니다.

**Phase 2**: 환경별 설정 (Production/Development/Testing)
**Phase 3**: UserTier별 설정 (Premium/Standard/Trial)

#### Schema Definition

```python
from pydantic import BaseModel, Field

class LLMSettings(BaseModel):
    """
    Node-Specific LLM Settings

    각 노드의 특성에 맞는 temperature/max_tokens 설정
    """

    # ===== Model Selection =====
    default_model: str = Field(default="gpt-4o-mini", description="기본 LLM 모델")

    # ===== Intent Understanding Node =====
    intent_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Intent 노드 temperature")
    intent_max_tokens: int = Field(default=1024, ge=1, le=16384, description="Intent 노드 max tokens")
    intent_model: str = Field(default="gpt-4o-mini", description="Intent 노드 모델")

    # ===== Planning Node =====
    planning_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    planning_max_tokens: int = Field(default=2048, ge=1, le=16384)
    planning_model: str = Field(default="gpt-4o-mini")

    # ===== Aggregator Node =====
    aggregator_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    aggregator_max_tokens: int = Field(default=3072, ge=1, le=16384)
    aggregator_model: str = Field(default="gpt-4o-mini")

    # ===== Chat Generator Node =====
    chat_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    chat_max_tokens: int = Field(default=4096, ge=1, le=16384)
    chat_model: str = Field(default="gpt-4o-mini")

    # ===== Graph Generator Node =====
    graph_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    graph_max_tokens: int = Field(default=2048, ge=1, le=16384)
    graph_model: str = Field(default="gpt-4o-mini")

    # ===== Report Generator Node =====
    report_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    report_max_tokens: int = Field(default=8192, ge=1, le=16384)
    report_model: str = Field(default="gpt-4o-mini")

    # ===== Agent Nodes =====
    agent_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    agent_max_tokens: int = Field(default=4096, ge=1, le=16384)
    agent_model: str = Field(default="gpt-4o-mini")
```

#### Node Configuration Guidelines

| 노드 타입 | Temperature | Max Tokens | 설명 |
|-----------|-------------|------------|------|
| **Intent** | 0.7 (높음) | 1024 | 창의적 의도 파악 |
| **Planning** | 0.3 (낮음) | 2048 | 정확한 계획 수립 |
| **Aggregator** | 0.5 (중간) | 3072 | 균형잡힌 분석 |
| **Chat** | 0.7 (높음) | 4096 | 자연스러운 대화 |
| **Graph** | 0.2 (낮음) | 2048 | JSON 정확성 |
| **Report** | 0.5 (중간) | 8192 | 긴 보고서 생성 |
| **Agent** | 0.5 (중간) | 4096 | 균형잡힌 처리 |

#### Presets

**Environment Presets (Phase 2)**:
- **PRODUCTION_PRESET**: 비용 최적화
- **DEVELOPMENT_PRESET**: 품질 우선
- **TESTING_PRESET**: 재현성 확보 (temp=0)

**User Tier Presets (Phase 3)**:
- **PREMIUM_PRESET**: gpt-4o, 높은 토큰
- **STANDARD_PRESET**: gpt-4o-mini, 중간 토큰
- **TRIAL_PRESET**: gpt-4o-mini, 낮은 토큰

#### Factory Functions

```python
from backend.app.config.llm_settings import (
    get_llm_settings,           # 환경별
    get_llm_settings_from_env,  # 환경 변수 읽기
    get_llm_settings_for_user   # UserTier별
)

# 환경별
settings = get_llm_settings(Environment.PRODUCTION)

# 사용자 Tier별
settings = get_llm_settings_for_user(UserTier.PREMIUM)

# Custom overrides
settings = get_llm_settings(
    Environment.PRODUCTION,
    overrides={"chat_max_tokens": 5000}
)
```

---

### UserTier

**파일**: `backend/app/octostrator/contexts/app_context.py`

**설명**: 사용자 등급 Enum (Phase 3)

#### Schema Definition

```python
from enum import Enum

class UserTier(str, Enum):
    """
    User Tier System (Phase 3)

    사용자별 맞춤 설정을 위한 Tier 시스템
    """
    PREMIUM = "premium"      # 프리미엄 사용자 (gpt-4o, 높은 토큰)
    STANDARD = "standard"    # 일반 사용자 (균형잡힌 설정)
    TRIAL = "trial"          # 체험 사용자 (최소 비용)
```

#### Tier Comparison

| 항목 | PREMIUM | STANDARD | TRIAL |
|------|---------|----------|-------|
| **모델** | gpt-4o | gpt-4o-mini | gpt-4o-mini |
| **Agent Tokens** | 8000 | 4096 | 2000 |
| **Report Tokens** | 15000 | 10000 | 3000 |
| **Temperature** | 0.5-0.7 | 0.5-0.7 | 0.3-0.6 |
| **비용** | 높음 | 중간 | 낮음 |
| **품질** | 최고 | 좋음 | 기본 |

#### Usage Example

```python
from backend.app.octostrator.contexts.app_context import UserTier, get_user_tier

# User ID로부터 자동 추출
tier = get_user_tier("premium_user123")
assert tier == UserTier.PREMIUM

tier = get_user_tier("trial_user456")
assert tier == UserTier.TRIAL

tier = get_user_tier("regular_user789")
assert tier == UserTier.STANDARD
```

---

## Supervisor States

### CognitiveState

**파일**: `backend/app/octostrator/states/cognitive_state.py`

**설명**: Cognitive Layer (Layer 1) 상태. 사용자 의도 파악, 계획 수립, 검증을 담당합니다.

#### Schema Definition

```python
from typing import Dict, List, Optional, Any
from .base import BaseState

class CognitiveState(BaseState):
    """
    State for Cognitive Layer (Layer 1)

    Handles planning, intent understanding, and validation.
    """

    # ===== Intent Understanding =====
    user_query: str                         # 사용자 질의
    user_intent: Optional[str]              # 파악된 의도
    intent_confidence: Optional[float]      # 의도 신뢰도 (0.0~1.0)
    intent_keywords: List[str]              # 핵심 키워드

    # ===== Planning =====
    plan: Optional[Dict[str, Any]]          # 생성된 계획
    plan_goal: Optional[str]                # 계획 목표
    plan_steps: List[Dict[str, Any]]        # 계획 스텝들
    plan_version: int                       # 계획 버전
    is_planning: bool                       # 계획 진행 중

    # ===== Validation =====
    plan_valid: bool                        # 계획 유효성
    validation_result: Optional[Dict[str, Any]]  # 검증 결과
    validation_errors: List[str]            # 검증 에러
    validation_warnings: List[str]          # 검증 경고

    # ===== Context and Memory =====
    user_context: Dict[str, Any]            # 사용자 컨텍스트
    historical_context: Optional[Dict[str, Any]]  # 이전 대화 기록
    domain_context: Dict[str, Any]          # 도메인 컨텍스트

    # ===== Analysis =====
    required_agents: List[str]              # 필요한 Agent 목록
    required_capabilities: List[str]        # 필요한 기능 목록
    estimated_duration: Optional[float]     # 예상 소요 시간 (초)
    complexity_score: Optional[float]       # 복잡도 점수 (0.0~1.0)

    # ===== Alternative Plans =====
    alternative_plans: List[Dict[str, Any]] # 대안 계획들
    selected_plan_index: int                # 선택된 계획 인덱스
    plan_selection_reason: Optional[str]    # 선택 이유
```

#### Key Fields

| 필드 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `user_intent` | str | 의도 분류 | "member_assessment", "program_design" |
| `intent_confidence` | float | 의도 신뢰도 | 0.85 |
| `plan_steps` | List[Dict] | 실행 단계 | [{"agent": "assessor", "task": "..."}] |
| `required_agents` | List[str] | 필요 Agent | ["assessor", "program_designer"] |
| `complexity_score` | float | 복잡도 | 0.7 (높음) |

---

### TodoState

**파일**: `backend/app/octostrator/states/todo_state.py`

**설명**: Todo Manager (Layer 2) 상태. Todo 생성, 수정, 의존성 관리를 담당합니다.

#### Schema Definition

```python
from typing import Dict, List, Optional, Any
from .base import BaseState

class TodoState(BaseState):
    """
    State for Todo Manager (Layer 2)

    Handles todo creation, updates, and dependency management.
    """

    # ===== Todo Management =====
    todos: List[Dict[str, Any]]             # Todo 목록
    active_todos: List[str]                 # 활성 Todo ID들
    completed_todos: List[str]              # 완료된 Todo ID들
    failed_todos: List[str]                 # 실패한 Todo ID들

    # ===== Dependencies =====
    todo_dependencies: Dict[str, List[str]]  # Todo 의존성 그래프
    blocked_todos: List[str]                # 블로킹된 Todo ID들

    # ===== HITL (Human-in-the-Loop) =====
    requires_approval: bool                 # 승인 필요 여부
    approval_status: Optional[str]          # 승인 상태
    approval_feedback: Optional[str]        # 승인 피드백

    # ===== Metadata =====
    last_todo_update: Optional[str]         # 마지막 업데이트 시각
    total_todos: int                        # 총 Todo 수
    progress_percentage: float              # 진행률 (0.0~100.0)
```

#### Todo Item Structure

```python
{
    "id": "todo_001",
    "title": "회원 초기 평가 실시",
    "description": "인바디 측정 및 자세 분석",
    "agent_id": "assessor_agent",
    "status": "pending",  # pending, running, completed, failed
    "priority": "high",   # high, medium, low
    "dependencies": ["todo_000"],  # 의존하는 Todo ID들
    "result": None,       # 실행 결과 (완료 시)
    "error": None,        # 에러 메시지 (실패 시)
    "created_at": "2025-11-06T10:00:00Z",
    "updated_at": "2025-11-06T10:00:00Z"
}
```

---

### ExecuteState

**파일**: `backend/app/octostrator/states/execute_state.py`

**설명**: Execute Layer (Layer 3) 상태. Agent 실행, 의존성 해결, 결과 집계를 담당합니다.

#### Schema Definition (Excerpt)

```python
class ExecuteState(BaseState):
    """
    State for Execute Layer (Layer 3)

    Handles agent execution, dependency resolution, and result aggregation.
    """

    # ===== Execution Management =====
    todos: List[Dict[str, Any]]             # 실행할 Todo 목록
    execution_order: List[List[str]]        # 병렬 실행 그룹
    current_execution_group: int            # 현재 그룹 인덱스
    is_executing: bool                      # 실행 중 여부

    # ===== Task Status Tracking =====
    pending_tasks: List[str]                # 대기 중
    running_tasks: List[str]                # 실행 중
    completed_tasks: List[str]              # 완료
    failed_tasks: List[str]                 # 실패
    skipped_tasks: List[str]                # 건너뜀

    # ===== Execution Results =====
    execution_results: List[Dict[str, Any]]  # 전체 결과
    agent_results: Dict[str, Any]           # Agent별 결과
    partial_results: Dict[str, Any]         # 중간 결과

    # ===== Error Handling =====
    execution_errors: List[Dict[str, Any]]  # 에러 목록
    error_recovery_attempts: Dict[str, int]  # 재시도 횟수
    max_retries: int                        # 최대 재시도
    error_report: Optional[Dict[str, Any]]  # 에러 리포트

    # ===== Aggregation =====
    aggregated_data: Optional[Dict[str, Any]]  # 집계 데이터
    aggregation_status: str                 # pending, processing, completed
    insights: List[str]                     # 인사이트
    summary: Optional[str]                  # 요약

    # ===== Performance Metrics =====
    execution_start_time: Optional[datetime]
    execution_end_time: Optional[datetime]
    task_timings: Dict[str, Dict[str, Any]]  # Task별 시간
    total_execution_time: Optional[float]   # 총 실행 시간(초)

    # ===== Agent Management =====
    active_agents: List[str]                # 활성 Agent 목록
    agent_availability: Dict[str, bool]     # Agent 가용성
    agent_workload: Dict[str, int]          # Agent 작업 부하

    # ===== Dependency Resolution =====
    dependency_graph: Dict[str, List[str]]  # 의존성 그래프
    resolved_dependencies: Set[str]         # 해결된 의존성
    blocked_tasks: List[str]                # 블로킹된 Task

    # ===== Resource Management =====
    resource_usage: Dict[str, float]        # 리소스 사용률
    resource_limits: Dict[str, float]       # 리소스 제한
    resource_allocation: Dict[str, Dict[str, Any]]  # 할당
```

#### Key Concepts

**Execution Order**: 의존성을 고려한 병렬 실행 그룹
```python
execution_order = [
    ["task_1", "task_2"],      # Group 0: 병렬 실행
    ["task_3"],                # Group 1: task_1, task_2 완료 후 실행
    ["task_4", "task_5"]       # Group 2: task_3 완료 후 병렬 실행
]
```

---

### ResponseState

**파일**: `backend/app/octostrator/states/response_state.py`

**설명**: Response Layer (Layer 4) 상태. 최종 응답 생성을 담당합니다.

#### Schema Definition (Summary)

```python
class ResponseState(BaseState):
    """
    State for Response Layer (Layer 4)

    Handles response generation based on execution results.
    """

    # ===== Input Data =====
    execution_results: Dict[str, Any]       # Execute Layer 결과
    user_query: str                         # 원래 사용자 질의
    output_format: str                      # chat, report, graph

    # ===== Response Generation =====
    generated_response: Optional[str]       # 생성된 응답
    response_sections: List[Dict[str, Any]]  # 응답 섹션들
    response_metadata: Dict[str, Any]       # 메타데이터

    # ===== Formatting =====
    is_formatting: bool                     # 포매팅 진행 중
    format_options: Dict[str, Any]          # 포맷 옵션

    # ===== Quality Control =====
    response_quality_score: Optional[float]  # 품질 점수
    quality_issues: List[str]               # 품질 이슈

    # ===== Final Output =====
    final_response: str                     # 최종 응답
```

---

## Worker Agent States

### FrontdeskState

**파일**: `backend/app/octostrator/states/frontdesk_state.py`

**설명**: AI 프론트데스크 에이전트 상태. 신규 회원 응대 및 리드 관리를 담당합니다.

**구현 상태**: ✅ 완전 구현 (149 lines)

#### Schema Definition

```python
from typing import TypedDict, Optional, List, Dict, Any
from .base import BaseAgentState

class LeadInfo(TypedDict):
    """리드 정보"""
    lead_id: str                            # 리드 ID
    name: Optional[str]                     # 이름
    phone: Optional[str]                    # 전화번호
    email: Optional[str]                    # 이메일
    inquiry_type: Optional[str]             # membership, trial, question
    inquiry_content: str                    # 문의 내용
    lead_score: Optional[float]             # 리드 점수 (0.0~1.0)
    priority: Optional[str]                 # high, medium, low
    source: Optional[str]                   # web, phone, sns

class AppointmentInfo(TypedDict):
    """상담 일정 정보"""
    appointment_id: str
    lead_id: str
    scheduled_date: str
    scheduled_time: str
    trainer_id: Optional[str]
    appointment_type: str                   # consultation, trial, assessment
    status: str                             # scheduled, confirmed, cancelled, completed
    notes: Optional[str]

class FrontdeskState(BaseAgentState):
    """Frontdesk Agent State Schema"""

    # ===== 리드 관리 =====
    lead_info: Optional[LeadInfo]           # 현재 리드 정보
    lead_list: Optional[List[LeadInfo]]     # 리드 목록

    # ===== 응대 내용 =====
    inquiry_text: Optional[str]             # 문의 내용
    response_text: Optional[str]            # 응답 내용
    conversation_history: Optional[List[Dict[str, str]]]  # 대화 기록

    # ===== 스코어링 =====
    lead_scoring_factors: Optional[Dict[str, Any]]  # 스코어링 요소
    recommended_action: Optional[str]       # schedule_appointment, send_info, follow_up

    # ===== 일정 관리 =====
    appointment_info: Optional[AppointmentInfo]  # 일정 정보
    available_slots: Optional[List[Dict[str, str]]]  # 가능한 시간대

    # ===== 알림 =====
    notification_sent: Optional[bool]       # 알림 전송 여부
    notification_recipients: Optional[List[str]]  # 수신자 목록

    # ===== 분석 결과 =====
    intent_classification: Optional[str]    # 문의 의도 분류
    urgency_level: Optional[str]            # high, medium, low
    estimated_conversion_rate: Optional[float]  # 예상 전환율
```

#### Usage Example

```python
state: FrontdeskState = {
    "lead_info": {
        "lead_id": "lead_001",
        "name": "홍길동",
        "phone": "010-1234-5678",
        "email": "hong@example.com",
        "inquiry_type": "membership",
        "inquiry_content": "PT 등록 문의드립니다",
        "lead_score": 0.85,
        "priority": "high",
        "source": "web"
    },
    "inquiry_text": "3개월 PT 등록하고 싶어요",
    "recommended_action": "schedule_appointment",
    "intent_classification": "membership_inquiry",
    "urgency_level": "high",
    "estimated_conversion_rate": 0.78
}
```

---

### AssessorState

**파일**: `backend/app/octostrator/states/assessor_state.py`

**설명**: AI 어시션 에이전트 상태. 회원 초기 평가 및 자세 분석을 담당합니다.

**구현 상태**: 🟡 기본 구조 (59 lines)

#### Schema Definition (Summary)

```python
class AssessorState(BaseAgentState):
    """
    Assessor Agent State

    핵심 역할: 회원 초기 평가 및 자세 분석
    Pain Point: "회원 체형과 자세를 '감'이 아닌 '데이터'로 정확하게 분석하고 싶다."
    """

    # ===== 회원 정보 =====
    member_id: Optional[str]
    member_name: Optional[str]
    assessment_date: Optional[str]

    # ===== 인바디 데이터 =====
    inbody_data: Optional[Dict[str, Any]]   # 인바디 측정 결과
    body_composition: Optional[Dict[str, float]]  # 체성분 분석

    # ===== 자세 분석 =====
    posture_images: Optional[List[str]]     # 자세 이미지 URL
    posture_analysis: Optional[Dict[str, Any]]  # 자세 분석 결과
    asymmetry_score: Optional[float]        # 비대칭 점수

    # ===== 목표 설정 =====
    member_goals: Optional[List[str]]       # 회원 목표
    priority_goals: Optional[List[str]]     # 우선 목표

    # ===== 평가 결과 =====
    assessment_report: Optional[Dict[str, Any]]  # 평가 보고서
    risk_factors: Optional[List[str]]       # 위험 요소
    recommendations: Optional[List[str]]     # 권장 사항
```

---

### ProgramDesignerState

**파일**: `backend/app/octostrator/states/program_designer_state.py`

**설명**: AI 프로그램 설계 에이전트 상태. 맞춤형 운동 프로그램 설계를 담당합니다.

**구현 상태**: 🟡 기본 구조 (59 lines)

#### Schema Definition (Summary)

```python
class ProgramDesignerState(BaseAgentState):
    """
    Program Designer Agent State

    핵심 역할: 맞춤형 운동 프로그램 설계
    Pain Point: "회원마다 다른 목표와 체형에 맞춘 프로그램을 빠르게 설계하고 싶다."
    """

    # ===== 입력 데이터 =====
    member_id: Optional[str]
    assessment_results: Optional[Dict[str, Any]]  # Assessor 결과
    goals: Optional[List[str]]

    # ===== 프로그램 설계 =====
    program_id: Optional[str]
    program_type: Optional[str]             # strength, cardio, flexibility, mixed
    duration_weeks: Optional[int]           # 프로그램 기간
    sessions_per_week: Optional[int]        # 주당 세션 수

    # ===== 운동 구성 =====
    exercises: Optional[List[Dict[str, Any]]]  # 운동 목록
    workout_phases: Optional[List[Dict[str, Any]]]  # 단계별 구성
    progression_plan: Optional[Dict[str, Any]]  # 진행 계획

    # ===== 프로그램 결과 =====
    program_document: Optional[Dict[str, Any]]  # 프로그램 문서
    trainer_notes: Optional[str]            # 트레이너 노트
```

---

### ManagerState

**파일**: `backend/app/octostrator/states/manager_state.py`

**설명**: AI 센터 관리 에이전트 상태. 회원권 관리, 출석 체크, 매출 분석을 담당합니다.

**구현 상태**: 🟡 기본 구조 (59 lines)

---

### MarketingState

**파일**: `backend/app/octostrator/states/marketing_state.py`

**설명**: AI 마케팅 에이전트 상태. SNS 콘텐츠 생성, 이벤트 기획을 담당합니다.

**구현 상태**: 🟡 기본 구조 (59 lines)

---

### OwnerAssistantState

**파일**: `backend/app/octostrator/states/owner_assistant_state.py`

**설명**: AI 원장 보조 에이전트 상태. 비즈니스 인사이트, 경영 분석을 담당합니다.

**구현 상태**: 🟡 기본 구조 (59 lines)

---

### TrainerEducationState

**파일**: `backend/app/octostrator/states/trainer_education_state.py`

**설명**: AI 트레이너 교육 에이전트 상태. 트레이너 교육 및 피드백을 담당합니다.

**구현 상태**: 🟡 기본 구조 (59 lines)

---

## Base Schemas

### BaseState

**파일**: `backend/app/octostrator/states/base.py`

**설명**: Supervisor State의 공통 베이스 클래스

```python
from typing import TypedDict, Optional

class BaseState(TypedDict, total=False):
    """
    Base State for all Supervisor States

    공통 필드:
    - session_id: 세션 ID
    - timestamp: 타임스탬프
    - error: 에러 메시지
    """

    session_id: str                         # 세션 ID (필수)
    timestamp: Optional[str]                # ISO 8601 타임스탬프
    error: Optional[str]                    # 에러 메시지
```

---

### BaseAgentState

**파일**: `backend/app/octostrator/states/base.py`

**설명**: Worker Agent State의 공통 베이스 클래스

```python
class BaseAgentState(TypedDict, total=False):
    """
    Base State for all Worker Agent States

    공통 필드:
    - agent_id: Agent ID
    - status: 실행 상태
    - result: 실행 결과
    - error: 에러 메시지
    """

    agent_id: str                           # Agent ID (필수)
    status: Optional[str]                   # pending, running, completed, failed
    result: Optional[Dict[str, Any]]        # 실행 결과
    error: Optional[str]                    # 에러 메시지

    # Metadata
    started_at: Optional[str]               # 시작 시각
    completed_at: Optional[str]             # 완료 시각
    duration_seconds: Optional[float]       # 실행 시간
```

---

## Type Definitions

### Common Types

```python
from typing import TypedDict, Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum

# ===== Task Status =====
TaskStatus = Literal["pending", "running", "completed", "failed", "skipped"]

# ===== Priority =====
Priority = Literal["high", "medium", "low"]

# ===== Agent Type =====
AgentType = Literal[
    "frontdesk",
    "assessor",
    "program_designer",
    "manager",
    "marketing",
    "owner_assistant",
    "trainer_education"
]

# ===== Output Format =====
OutputFormat = Literal["chat", "report", "graph"]

# ===== Approval Status =====
ApprovalStatus = Literal["pending", "approved", "rejected"]
```

---

## Serialization Rules

### msgpack 직렬화 가능 여부

#### ✅ 직렬화 가능 (State에 포함 가능)

```python
# 기본 타입
user_query: str = "안녕하세요"
count: int = 42
score: float = 3.14
is_valid: bool = True
nothing: None = None

# 컬렉션
items: list = [1, 2, 3]
data: dict = {"key": "value"}
unique: set = {1, 2, 3}  # → list로 변환됨
coords: tuple = (10, 20)  # → list로 변환됨

# 중첩 구조
nested: dict = {
    "user": {"name": "홍길동", "age": 30},
    "todos": [
        {"id": 1, "title": "Task 1"},
        {"id": 2, "title": "Task 2"}
    ]
}

# TypedDict
class PersonDict(TypedDict):
    name: str
    age: int

person: PersonDict = {"name": "홍길동", "age": 30}  # ✅ OK

# Optional
maybe_text: Optional[str] = None  # ✅ OK
maybe_text: Optional[str] = "value"  # ✅ OK
```

#### ❌ 직렬화 불가 (State에 포함 불가)

```python
# LLM 인스턴스
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini")  # ❌ NOT SERIALIZABLE

# Checkpointer
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
checkpointer = AsyncPostgresSaver()  # ❌ NOT SERIALIZABLE

# Context (dataclass with non-serializable)
from backend.app.octostrator.contexts.app_context import AppContext
context = AppContext(...)  # ❌ NOT SERIALIZABLE

# 함수
def my_function(): pass
fn = my_function  # ❌ NOT SERIALIZABLE

# 람다
lambda_fn = lambda x: x + 1  # ❌ NOT SERIALIZABLE

# 파일 핸들
file = open("data.txt")  # ❌ NOT SERIALIZABLE

# 데이터베이스 연결
import psycopg2
conn = psycopg2.connect(...)  # ❌ NOT SERIALIZABLE
```

### Phase 3 Migration Guide

**Before (Phase 2)** ❌:
```python
class OctostratorState(TypedDict, total=False):
    llm: Any                    # ❌ ChatOpenAI 인스턴스
    checkpointer: Any           # ❌ AsyncPostgresSaver 인스턴스
    context: Dict[str, Any]     # ❌ 불필요한 중복
```

**After (Phase 3)** ✅:
```python
class OctostratorState(TypedDict, total=False):
    # llm, checkpointer, context 제거!
    # Runtime을 통해 접근
    pass

# 사용법
async def my_node(state: OctostratorState, runtime: Optional[Runtime] = None):
    if runtime is not None:
        context: AppContext = runtime.context
        llm_settings = context.llm_settings
        # ...
```

---

## Validation Rules

### 1. OctostratorState Validation

```python
def validate_octostrator_state(state: OctostratorState) -> List[str]:
    """OctostratorState 검증"""
    errors = []

    # user_query: 필수, 비어있지 않음
    if not state.get("user_query"):
        errors.append("user_query is required and cannot be empty")

    # session_id: 필수
    if not state.get("session_id"):
        errors.append("session_id is required")

    # output_format: 허용된 값만
    valid_formats = ["chat", "report", "graph"]
    if state.get("output_format") not in valid_formats:
        errors.append(f"output_format must be one of {valid_formats}")

    # plan_valid: plan이 있으면 True여야 함
    if state.get("plan") and not state.get("plan_valid"):
        errors.append("plan exists but plan_valid is False")

    # todos: 각 Todo는 id, title, status 필수
    for todo in state.get("todos", []):
        if "id" not in todo:
            errors.append(f"Todo missing 'id': {todo}")
        if "title" not in todo:
            errors.append(f"Todo missing 'title': {todo}")
        if "status" not in todo:
            errors.append(f"Todo missing 'status': {todo}")

    return errors
```

### 2. AppContext Validation

```python
def validate_app_context(context: AppContext) -> List[str]:
    """AppContext 검증"""
    errors = []

    # user_id: 필수, 비어있지 않음
    if not context.user_id:
        errors.append("user_id is required")

    # session_id: 필수
    if not context.session_id:
        errors.append("session_id is required")

    # llm_settings: Pydantic이 자동 검증
    # (temperature 범위, max_tokens 범위 등)

    # log_level: 허용된 값만
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    if context.log_level not in valid_levels:
        errors.append(f"log_level must be one of {valid_levels}")

    # user_tier: Enum 검증
    if not isinstance(context.user_tier, UserTier):
        errors.append("user_tier must be a UserTier enum")

    return errors
```

### 3. LLMSettings Validation

```python
# Pydantic이 자동으로 검증함

from pydantic import ValidationError

try:
    settings = LLMSettings(
        intent_temperature=2.5,  # ❌ 2.0 초과
        intent_max_tokens=20000  # ❌ 16384 초과
    )
except ValidationError as e:
    print(e.errors())
    # [
    #   {
    #     'loc': ('intent_temperature',),
    #     'msg': 'ensure this value is less than or equal to 2.0',
    #     'type': 'value_error'
    #   },
    #   ...
    # ]
```

---

## Change History

### 2025-11-06: P0 Fixes (Phase 3 완료)

**변경 사항**:
1. ✅ **OctostratorState**: llm, checkpointer, context 필드 제거
2. ✅ **AppContext**: debug, trace_id, metrics, user_tier 추가
3. ✅ **LLMSettings**: UserTier별 presets 추가
4. ✅ **SystemConfig**: openai_model 필드 추가

**이유**:
- msgpack 직렬화 오류 해결
- Phase 3 원칙 준수 (State/Context 분리)
- Context API 정상 동작

**영향**:
- 모든 노드는 runtime 파라미터로 Context 접근
- UserTier별 LLM 차별화 가능
- State 직렬화/역직렬화 안정화

---

### 2025-11-05: Phase 2 Context API

**변경 사항**:
1. AppContext에 LLMSettings 추가
2. 환경별 LLM 설정 (Production/Dev/Test)
3. 노드별 LLM 파라미터 커스터마이징

---

### 2025-11-04: Phase 1 Foundation

**변경 사항**:
1. OctostratorState 정의
2. Supervisor States 정의 (Cognitive/Todo/Execute/Response)
3. Worker Agent States 정의 (7개)
4. BaseState, BaseAgentState 정의

---

## 부록 (Appendix)

### A. 전체 State 목록

| State 이름 | 타입 | 파일 | 구현 상태 |
|-----------|------|------|----------|
| OctostratorState | Supervisor | octostrator_state.py | ✅ 완료 |
| AppContext | Context | app_context.py | ✅ 완료 |
| LLMSettings | Config | app_context.py | ✅ 완료 |
| CognitiveState | Supervisor | cognitive_state.py | ✅ 완료 |
| TodoState | Supervisor | todo_state.py | ✅ 완료 |
| ExecuteState | Supervisor | execute_state.py | ✅ 완료 |
| ResponseState | Supervisor | response_state.py | ✅ 완료 |
| FrontdeskState | Agent | frontdesk_state.py | ✅ 완료 |
| AssessorState | Agent | assessor_state.py | 🟡 기본 |
| ProgramDesignerState | Agent | program_designer_state.py | 🟡 기본 |
| ManagerState | Agent | manager_state.py | 🟡 기본 |
| MarketingState | Agent | marketing_state.py | 🟡 기본 |
| OwnerAssistantState | Agent | owner_assistant_state.py | 🟡 기본 |
| TrainerEducationState | Agent | trainer_education_state.py | 🟡 기본 |

### B. 관련 문서

- [Master Checklist](MASTER_CHECKLIST.md)
- [State Management Guide](STATE_MANAGEMENT_GUIDE.md)
- [API Specifications](API_SPECIFICATIONS.md)
- [Phase 3 Quick Start](PHASE3_QUICK_START_GUIDE.md)
- [Context API Implementation Guide](CONTEXT_API_IMPLEMENTATION_GUIDE.md)

---

**작성자**: Claude Code Agent
**검토자**: -
**버전**: 1.0
**마지막 업데이트**: 2025-11-06
**다음 리뷰**: TBD
