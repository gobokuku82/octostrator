# 시스템 전체 점검 마스터 플랜 (System Health Check Master Plan)

**날짜**: 2025-11-06
**목적**: 좀비 코드, 버그 코드, 불일치 방지를 위한 체계적 점검
**상태**: 🔍 분석 중

---

## 📋 목차

1. [현재 시스템 현황](#1-현재-시스템-현황)
2. [구현된 기능 목록](#2-구현된-기능-목록)
3. [핵심 아키텍처](#3-핵심-아키텍처)
4. [위험 영역 식별](#4-위험-영역-식별)
5. [체크리스트](#5-체크리스트)
6. [우선순위](#6-우선순위)
7. [실행 계획](#7-실행-계획)

---

## 1. 현재 시스템 현황

### 시스템 규모
- **총 Python 파일**: 108개
- **Graph 파일**: 11개
- **Nodes 파일**: 11개
- **API 엔드포인트**: 5개 라우터
- **Worker Agents**: 7개

### 레이어 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│  - websocket.py (WebSocket 실시간)                           │
│  - sessions.py (세션 관리)                                    │
│  - todos.py (Todo 관리)                                       │
│  - agents.py (Agent 관리)                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Octostrator Layer (최상위)                   │
│  - octostrator_graph.py                                      │
│  - octostrator_nodes.py                                      │
│  - OctostratorState (TypedDict)                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Supervisor Layer (3개)                      │
│  1. Cognitive (계획 수립)                                     │
│  2. Todo (Todo 생성, HITL)                                   │
│  3. Execute (에이전트 실행)                                   │
│  4. Response (응답 생성) - 현재 미사용?                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Worker Agents (7개)                        │
│  1. FrontdeskAgent (접수/상담)                               │
│  2. AssessorAgent (평가/측정)                                │
│  3. ProgramDesignerAgent (프로그램 설계)                     │
│  4. ManagerAgent (관리/운영)                                 │
│  5. MarketingAgent (마케팅)                                  │
│  6. OwnerAssistantAgent (원장 보조)                          │
│  7. TrainerEducationAgent (트레이너 교육)                    │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 컴포넌트

**State Management**:
- `OctostratorState` (TypedDict)
- History Tracking (action_history, plan_history, user_interactions)
- Smart Reducers (merge_todos_smart, track_plan_changes 등)

**Context API (Phase 3)**:
- `AppContext` (dataclass)
- `UserTier` (PREMIUM, STANDARD, TRIAL)
- `LLMSettings` (Tier별 차별화)

**Checkpointer**:
- PostgreSQL (AsyncPostgresSaver)
- Session Management

---

## 2. 구현된 기능 목록

### ✅ 완료된 기능 (Production Ready)

#### Phase 1: 기본 인프라
- [x] FastAPI 서버 구축
- [x] PostgreSQL Checkpointer
- [x] Session Management
- [x] 7개 Worker Agent 기본 구조
- [x] Agent Registry 시스템

#### Phase 2: LLM Settings 환경별 분리
- [x] DEVELOPMENT_PRESET
- [x] PRODUCTION_PRESET
- [x] 환경 변수 기반 설정 전환

#### Phase 3: Context API (2025-11-06 완료)
- [x] AppContext (dataclass)
- [x] UserTier 시스템 (PREMIUM/STANDARD/TRIAL)
- [x] LLM Settings Tier별 차별화
- [x] Debug & Monitoring (debug, trace_id, metrics)
- [x] WebSocket API 확장 (debug/trace_id/user_id 지원)
- [x] Context Factory Functions
- [x] 26개 Unit Tests (100% 통과)

#### Phase 3 Bug Fix (2025-11-06 완료)
- [x] OctostratorState 직렬화 불가능 필드 제거
- [x] Cognitive 노드 session_id 에러 수정
- [x] 모든 노드 Context API 통합
- [x] msgpack 직렬화 오류 해결

#### Phase 4.3: WebSocket 실시간 스트리밍
- [x] WebSocket 엔드포인트 (/ws/chat/{session_id})
- [x] 실시간 이벤트 스트리밍 (astream_events)
- [x] Frontend 연동

#### Phase 4.4: Session Management API
- [x] 세션 생성/조회/삭제
- [x] 세션 상태 관리

#### Phase 2: Todo & Agent Management API
- [x] Todo CRUD API
- [x] Agent 목록 조회 API

### 🚧 부분 구현 (Partially Implemented)

#### History Tracking
- [x] State 정의 (action_history, plan_history, user_interactions)
- [x] Reducers 구현 (add_with_timestamp_and_step 등)
- [ ] 실제 사용 여부 불명확
- [ ] Frontend 시각화 미구현

#### Response Supervisor
- [x] Graph 파일 존재 (response_graph.py)
- [x] Nodes 파일 존재 (response_nodes.py)
- [ ] Octostrator에 통합 여부 불명확
- [ ] 실제 사용 여부 미확인

#### Todo Manager
- [x] TodoAgent 클래스 존재
- [ ] Context API 통합 완료 (Step 4에서 수정)
- [ ] 실제 LLM 사용 여부 미확인

#### HITL (Human-in-the-Loop)
- [x] State에 requires_approval 플래그
- [x] auto_approve context 설정
- [ ] WebSocket interrupt 메커니즘 미구현
- [ ] Frontend HITL UI 미구현

### ❌ 미구현 (Not Implemented)

#### Phase 3.5: Todo/HITL Context API
- [ ] TodoSettings (Tier별 timeout, retry)
- [ ] HITLSettings (Tier별 승인 정책)

#### Phase 4: Frontend Dashboard 고도화
- [ ] ContextInfoPanel.tsx
- [ ] MetricsDashboard.tsx
- [ ] WebSocket context_update/metrics_update 이벤트

#### Worker Agent 실제 구현
- [ ] 7개 Agent의 실제 비즈니스 로직
- [ ] Agent별 LLM Prompt Engineering
- [ ] Agent별 Tools 구현

---

## 3. 핵심 아키텍처

### 3.1 State vs Context vs Config

#### ✅ 올바른 사용 (Phase 3 이후)

**State** (직렬화 가능, Checkpointer에 저장):
```python
class OctostratorState(TypedDict):
    # User Input
    user_query: str
    session_id: str
    output_format: str

    # State Tracking
    plan: dict
    todos: List[Dict]
    execution_results: dict
    final_response: str

    # Flags
    plan_valid: bool
    requires_approval: bool
    error: Optional[str]

    # History
    action_history: List[Dict]
    plan_history: List[Dict]
    user_interactions: List[Dict]

    # Metadata
    created_at: str
    updated_at: str
    total_steps: int
```

**Context** (런타임 정보, 직렬화 불가능):
```python
@dataclass
class AppContext:
    # User Info
    user_id: str
    session_id: str
    user_tier: UserTier  # PREMIUM/STANDARD/TRIAL

    # LLM Settings
    llm_settings: LLMSettings

    # Debug & Monitoring
    debug: bool
    trace_id: str
    metrics: Dict[str, Any]
    log_level: str

    # Optional
    db_conn: Optional[str]
```

**Config** (LangGraph 설정):
```python
config = {
    "configurable": {
        "thread_id": session_id,
        "context": app_context  # Phase 3: AppContext 인스턴스
    }
}
```

### 3.2 LLM 생성 패턴

#### ✅ 올바른 패턴 (Phase 3 이후)

```python
# 노드에서 LLM 생성
async def my_node(state: State, runtime: Optional[Runtime] = None) -> State:
    # Context API 사용
    if runtime is not None:
        context: AppContext = runtime.context
        settings = context.llm_settings

        llm = ChatOpenAI(
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
            api_key=system_config.openai_api_key
        )
    else:
        # Fallback
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=...)

    # Use llm...
```

#### ❌ 잘못된 패턴 (Phase 2 이전, 제거됨)

```python
# ❌ State에서 LLM 접근 (직렬화 불가능)
llm = state.get("llm")

# ❌ State에 LLM 저장
state["llm"] = ChatOpenAI(...)
```

### 3.3 데이터 흐름

```
1. Client (WebSocket) → API
   └─ message, debug, trace_id, user_id

2. API → AppContext 생성
   └─ UserTier 자동 감지
   └─ LLMSettings 선택 (PREMIUM/STANDARD/TRIAL)

3. API → LangGraph Config
   └─ thread_id (세션)
   └─ context (AppContext)

4. Graph → Nodes 실행
   └─ runtime.context로 AppContext 접근
   └─ LLM 생성 (Tier별 설정)

5. Nodes → State 업데이트
   └─ 직렬화 가능한 데이터만 저장

6. Checkpointer → PostgreSQL
   └─ State만 저장 (Context는 저장 안됨)
```

---

## 4. 위험 영역 식별 🚨

### 🔴 Critical (즉시 점검 필요)

#### 4.1 Response Supervisor 사용 여부 불명확
**위치**: `backend/app/octostrator/supervisors/response/`

**문제**:
- Graph와 Nodes 파일 존재
- Octostrator Graph에 포함 여부 미확인
- 사용하지 않으면 **좀비 코드**

**점검 필요**:
```python
# octostrator_graph.py에서 response_supervisor 사용하는지?
# response_layer_node가 호출되는지?
```

#### 4.2 History Tracking 실제 사용 여부
**위치**: `backend/app/octostrator/states/reducers.py`

**문제**:
- State에 history 필드 정의됨
- Reducers 구현됨
- 실제로 노드에서 업데이트하는지 미확인
- Frontend에서 표시하는지 미확인

**점검 필요**:
```python
# 노드에서 action_history 업데이트하는가?
# Frontend에서 history 표시하는가?
```

#### 4.3 Todo Manager LLM 사용 불명확
**위치**: `backend/app/octostrator/supervisors/todo/todo_manager.py`

**문제**:
- Phase 3에서 llm=None으로 초기화됨
- 실제 LLM 사용해야 하는지 불명확
- 현재 동작하는지 미확인

#### 4.4 Worker Agents 실제 구현 상태
**위치**: `backend/app/octostrator/agents/*/`

**문제**:
- 7개 Agent 파일 존재
- 실제 비즈니스 로직 구현 여부 미확인
- Placeholder 코드일 가능성

### 🟡 Medium (검토 권장)

#### 4.5 HITL 메커니즘 불완전
- State에 requires_approval 플래그만 존재
- WebSocket interrupt 미구현
- Frontend UI 미구현

#### 4.6 main.py의 /chat 엔드포인트
**위치**: `backend/app/main.py:91`

**문제**:
- POST /chat 엔드포인트 존재
- WebSocket 사용 시 필요한지 불명확
- auto_approve=True로 고정됨

#### 4.7 Config에 Context 전달 방식 불일치 가능성
**위치**: 여러 파일

**문제**:
- `session_manager.py`: context를 dict로 전달
- 실제로는 AppContext 인스턴스여야 함
- Type mismatch 가능성

### 🟢 Low (모니터링)

#### 4.8 Frontend plan 타입 불일치
- Backend: plan을 dict로 전송
- Frontend: array 기대
- 이미 수정했지만 재발 가능성

---

## 5. 체크리스트

### 5.1 아키텍처 일관성 체크리스트

- [ ] **State 직렬화 검증**
  - [ ] OctostratorState의 모든 필드가 직렬화 가능한가?
  - [ ] State에 llm/checkpointer/context 접근 시도 없는가?

- [ ] **Context API 통합 검증**
  - [ ] 모든 노드가 runtime 파라미터를 받는가?
  - [ ] 모든 노드가 Context로부터 LLM 생성하는가?
  - [ ] Fallback 로직이 있는가?

- [ ] **Config 전달 검증**
  - [ ] Config에 context가 AppContext 인스턴스로 전달되는가?
  - [ ] Type mismatch가 없는가?

### 5.2 기능 완성도 체크리스트

- [ ] **Octostrator Graph**
  - [ ] cognitive_layer_node 동작 확인
  - [ ] todo_layer_node 동작 확인
  - [ ] execute_layer_node 동작 확인
  - [ ] response_layer_node 사용 여부 확인 🔴

- [ ] **Supervisor Layers**
  - [ ] Cognitive: LLM 사용하는가?
  - [ ] Todo: LLM 사용하는가? 🔴
  - [ ] Execute: Agent 라우팅 동작하는가?
  - [ ] Response: 사용되는가? 🔴

- [ ] **Worker Agents**
  - [ ] 7개 Agent가 실제 구현되었는가? 🔴
  - [ ] Agent Registry 동작하는가?
  - [ ] Agent별 LLM 설정이 적용되는가?

- [ ] **History Tracking**
  - [ ] action_history 업데이트되는가? 🔴
  - [ ] plan_history 업데이트되는가? 🔴
  - [ ] user_interactions 업데이트되는가? 🔴

- [ ] **HITL**
  - [ ] requires_approval 동작하는가? 🔴
  - [ ] WebSocket interrupt 구현되었는가? ❌
  - [ ] Frontend HITL UI 있는가? ❌

### 5.3 코드 품질 체크리스트

- [ ] **좀비 코드 제거**
  - [ ] 사용하지 않는 Graph/Nodes 파일 식별
  - [ ] 사용하지 않는 함수/클래스 제거
  - [ ] Import되지 않는 모듈 제거

- [ ] **문서화**
  - [ ] 모든 주요 함수에 docstring 있는가?
  - [ ] Phase 표시가 명확한가?
  - [ ] TODO 주석이 명확한가?

- [ ] **테스트**
  - [ ] Phase 3 Unit Tests (26개) ✅
  - [ ] Integration Tests? ❌
  - [ ] E2E Tests? ❌

---

## 6. 우선순위

### 🔥 P0 (즉시 실행 - 시스템 안정성)

1. **Response Supervisor 사용 여부 확인**
   - Octostrator Graph 분석
   - 사용하지 않으면 제거 또는 문서화

2. **Todo Manager LLM 사용 확인**
   - TodoAgent 실제 동작 테스트
   - LLM 필요하면 Context API 적용

3. **Worker Agents 구현 상태 확인**
   - 7개 Agent 코드 검토
   - Placeholder이면 문서화

4. **Config Context 타입 검증**
   - AppContext vs dict 불일치 수정

### ⚡ P1 (주요 기능 완성도)

5. **History Tracking 사용 확인**
   - 노드에서 업데이트하는지 확인
   - 사용하지 않으면 제거 고려

6. **HITL 메커니즘 완성 여부 결정**
   - 구현 완료할지 Phase 4로 연기할지 결정

7. **main.py /chat 엔드포인트 정리**
   - WebSocket과 중복인지 확인
   - 필요 없으면 제거

### 📋 P2 (코드 품질 개선)

8. **좀비 코드 제거**
   - 사용하지 않는 파일/함수 제거

9. **문서화 개선**
   - README 업데이트
   - API 문서 생성

10. **Integration Tests 작성**
    - E2E 시나리오 테스트

---

## 7. 실행 계획

### Week 1: 핵심 검증 (P0)

**Day 1-2: Response Supervisor & Todo Manager**
1. Octostrator Graph 코드 읽기
2. Response Supervisor 사용 여부 확인
3. Todo Manager 테스트 시나리오 작성
4. 결과 문서화

**Day 3-4: Worker Agents & Config**
5. 7개 Agent 코드 리뷰
6. 각 Agent 구현 상태 문서화
7. Config Context 타입 검증
8. 필요시 수정

**Day 5: P0 통합 테스트**
9. 전체 시스템 E2E 테스트
10. 발견된 이슈 수정

### Week 2: 기능 완성도 (P1)

**Day 1-2: History Tracking**
11. History 업데이트 코드 추가 또는 제거 결정
12. Frontend 연동 여부 결정

**Day 3: HITL & /chat**
13. HITL 구현 범위 결정
14. /chat 엔드포인트 정리

**Day 4-5: 통합 및 문서화**
15. P0 + P1 통합 테스트
16. 시스템 문서 업데이트

### Week 3: 코드 품질 (P2)

**Day 1-2: 좀비 코드 제거**
17. 사용하지 않는 파일 삭제
18. Import 정리

**Day 3-5: 테스트 & 문서**
19. Integration Tests 작성
20. README 및 API 문서 업데이트

---

## 8. 체크리스트 템플릿

### 파일별 점검 템플릿

```markdown
## [파일명] 점검

**날짜**: YYYY-MM-DD
**담당**:
**상태**: ⬜ 미점검 / 🔍 점검 중 / ✅ 완료 / ❌ 이슈 발견

### 점검 항목
- [ ] 파일이 실제로 사용되는가?
- [ ] Import되는가?
- [ ] 최근 수정 날짜는?
- [ ] Phase 표시가 명확한가?
- [ ] Context API 통합되었는가?
- [ ] State 직렬화 문제 없는가?
- [ ] 테스트가 있는가?

### 발견된 이슈
1.
2.

### 조치 사항
1.
2.

### 결론
✅ 유지 / 🔄 수정 필요 / ❌ 제거
```

---

## 9. 다음 단계

### 즉시 시작 가능

1. **P0-1 실행**: Response Supervisor 사용 여부 확인
   ```bash
   # Octostrator Graph 읽기
   # response_layer_node 호출 여부 grep
   ```

2. **P0-2 실행**: Todo Manager 테스트
   ```bash
   # Todo Manager 실행 테스트 작성
   # LLM 사용 여부 확인
   ```

### 의사결정 필요

- History Tracking을 계속 사용할 것인가?
- HITL을 Phase 3.5로 완성할 것인가, Phase 4로 연기할 것인가?
- Worker Agents를 지금 구현할 것인가, 나중에 할 것인가?

---

**작성자**: Claude Code Agent
**검토자**: -
**승인자**: -

---

## 10. 요약

✅ **완료된 것**:
- Phase 3 Context API (100%)
- Phase 3 Bug Fix (100%)
- WebSocket 실시간 스트리밍
- Session Management

🚧 **부분 구현**:
- History Tracking (미사용 가능성)
- Response Supervisor (미사용 가능성)
- Todo Manager (LLM 미사용?)
- HITL (불완전)
- Worker Agents (Placeholder?)

❌ **미구현**:
- Phase 3.5 (Todo/HITL Settings)
- Phase 4 (Frontend Dashboard)
- Agent 실제 비즈니스 로직

🔥 **우선순위**:
1. 좀비 코드 식별 (Response, History, Agents)
2. Todo Manager 동작 확인
3. Config Context 타입 검증
4. 전체 E2E 테스트
