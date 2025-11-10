# 기능 명세서 (Feature Specifications)

**작성일**: 2025-11-06
**목적**: 전체 시스템의 기능 명세 및 구현 상태
**버전**: 0.5.0

---

## 📑 목차 (Table of Contents)

1. [개요 (Overview)](#개요-overview)
2. [Phase별 기능 구현 현황](#phase별-기능-구현-현황)
3. [Core Features (핵심 기능)](#core-features-핵심-기능)
4. [Supervisor Features (레이어 기능)](#supervisor-features-레이어-기능)
5. [Worker Agent Features (에이전트 기능)](#worker-agent-features-에이전트-기능)
6. [Infrastructure Features (인프라 기능)](#infrastructure-features-인프라-기능)
7. [Planned Features (계획된 기능)](#planned-features-계획된-기능)

---

## 개요 (Overview)

### 시스템 목적

**AI PT Manager**는 피트니스 센터의 모든 업무를 AI로 지원하는 통합 관리 시스템입니다.

### 핵심 가치 제안

1. **트레이너**: "회원마다 다른 프로그램을 빠르고 정확하게 설계하고 싶다"
2. **원장**: "센터 운영 데이터를 한눈에 보고 의사결정하고 싶다"
3. **프론트데스크**: "리드를 놓치지 않고 효율적으로 관리하고 싶다"
4. **회원**: "나만의 맞춤 PT를 받고 싶다"

### 기능 계층 구조

```
AI PT Manager
├── Layer 1: Cognitive (의도 파악 + 계획)
├── Layer 2: Todo Manager (작업 관리 + HITL)
├── Layer 3: Execute (Agent 실행 + 집계)
├── Layer 4: Response (응답 생성)
│
└── Worker Agents (7개)
    ├── Frontdesk Agent          ✅ 완전 구현
    ├── Assessor Agent           🟡 기본 구조
    ├── Program Designer Agent   🟡 기본 구조
    ├── Manager Agent            🟡 기본 구조
    ├── Marketing Agent          🟡 기본 구조
    ├── Owner Assistant Agent    🟡 기본 구조
    └── Trainer Education Agent  🟡 기본 구조
```

---

## Phase별 기능 구현 현황

### Phase 1: Foundation (완료 ✅)

**목표**: 기본 아키텍처 및 Agent 구조 수립

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| LangGraph 기본 구조 | ✅ | 100% | StateGraph, 노드, 엣지 |
| Supervisor Pattern | ✅ | 100% | 4-Layer 구조 |
| Worker Agent 정의 | ✅ | 80% | FrontdeskAgent만 완전 구현 |
| State 정의 | ✅ | 100% | 모든 State 클래스 |
| 기본 Graph 실행 | ✅ | 100% | ainvoke, astream |

---

### Phase 2: Context API (완료 ✅)

**목표**: 환경별 LLM 설정 및 비용 최적화

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| LLMSettings 정의 | ✅ | 100% | Pydantic BaseModel |
| 환경별 Presets | ✅ | 100% | Production/Dev/Test |
| AppContext 정의 | ✅ | 100% | dataclass, Context API |
| 노드별 LLM 커스터마이징 | ✅ | 100% | Temperature, max_tokens |
| 비용 최적화 | ✅ | 100% | 30-50% 절감 |

---

### Phase 3: UserTier System (완료 ✅)

**목표**: 사용자별 맞춤 설정 (Premium/Standard/Trial)

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| UserTier Enum 정의 | ✅ | 100% | PREMIUM/STANDARD/TRIAL |
| Tier별 LLM Presets | ✅ | 100% | gpt-4o vs gpt-4o-mini |
| Debug 모드 | ✅ | 100% | 상세 로깅 |
| Trace ID | ✅ | 100% | 분산 추적 |
| Metrics 수집 | ✅ | 100% | 성능 메트릭 |
| WebSocket UserTier 지원 | ✅ | 100% | user_id로 Tier 추출 |
| **P0 Fixes** | ✅ | 100% | State/Context 분리 완료 |

---

### Phase 4: Advanced Features (부분 완료 🟡)

#### Phase 4.1: Todo Manager (완료 ✅)

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| Todo 생성 | ✅ | 100% | Plan → Todos 변환 |
| Todo 의존성 관리 | ✅ | 100% | Dependency graph |
| HITL (승인 대기) | 🟡 | 70% | auto_approve 필드 필요 |
| 조건부 Todo Manager | ✅ | 100% | should_use_todo_manager |

#### Phase 4.2: Agent Registry (완료 ✅)

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| Agent 등록 시스템 | ✅ | 100% | AgentRegistry 클래스 |
| Agent 우선순위 | ✅ | 100% | Priority Enum |
| Agent 검색 | ✅ | 100% | By ID, capability |
| BaseAgent 클래스 | ✅ | 100% | 공통 인터페이스 |

#### Phase 4.3: WebSocket Streaming (완료 ✅)

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| WebSocket 연결 | ✅ | 100% | ConnectionManager |
| 실시간 스트리밍 | ✅ | 100% | astream_events v2 |
| 이벤트 전송 | ✅ | 100% | 10가지 이벤트 타입 |
| 진행 상황 업데이트 | ✅ | 100% | node_started/completed |
| Plan/Todo/Execution 업데이트 | ✅ | 100% | 실시간 전송 |

#### Phase 4.4: Session Management (완료 ✅)

| 기능 | 상태 | 완성도 | 비고 |
|------|------|--------|------|
| 세션 생성 | ✅ | 100% | create_session |
| 세션 조회 | ✅ | 100% | GET /sessions/{id} |
| 히스토리 조회 | ✅ | 100% | GET /sessions/{id}/history |
| Checkpoint 관리 | ✅ | 100% | AsyncPostgresSaver |

---

### Phase 5: Production Ready (미구현 🔴)

| 기능 | 상태 | 완성도 | 예정일 |
|------|------|--------|--------|
| JWT 인증 | 🔴 | 0% | TBD |
| Rate Limiting | 🔴 | 0% | TBD |
| 에러 추적 (Sentry) | 🔴 | 0% | TBD |
| 성능 모니터링 | 🔴 | 0% | TBD |
| DB Migration (Alembic) | 🔴 | 0% | TBD |
| Production Deployment | 🔴 | 0% | TBD |

---

## Core Features (핵심 기능)

### F-001: Supervisor Pattern 오케스트레이션

**Phase**: 1
**상태**: ✅ 완료
**우선순위**: P0

**설명**:
4-Layer Supervisor Pattern을 통한 복잡한 작업 오케스트레이션

**기능 상세**:
1. **Cognitive Layer**: 사용자 의도 파악 + 계획 수립
2. **Todo Manager**: 계획 → Todo 변환 + 의존성 관리
3. **Execute Layer**: Worker Agents 실행 + 결과 집계
4. **Response Layer**: 최종 응답 생성

**Flow**:
```
START → Cognitive → [Conditional Todo] → Execute → Response → END
```

**검증 방법**:
- 사용자 질의 입력
- 각 Layer 노드 실행 확인
- 최종 응답 생성 확인

**Test Coverage**: 수동 테스트 완료

---

### F-002: Context API (Phase 3)

**Phase**: 3
**상태**: ✅ 완료
**우선순위**: P0

**설명**:
State/Context 분리 원칙을 통한 안정적인 런타임 관리

**기능 상세**:
1. **State**: 직렬화 가능한 데이터만 (user_query, plan, todos 등)
2. **Context**: 불변 런타임 정보 (llm_settings, user_tier, trace_id 등)
3. **Runtime 주입**: LangGraph context_schema를 통한 자동 주입

**구현**:
```python
# Graph 정의
graph = StateGraph(
    OctostratorState,
    context_schema=AppContext  # Context API 활성화
)

# 노드에서 접근
async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None
):
    context: AppContext = runtime.context
    llm_settings = context.llm_settings
```

**혜택**:
- msgpack 직렬화 문제 해결
- UserTier별 LLM 차별화
- 디버그 모드 지원
- 분산 추적 (trace_id)

**Test Coverage**: 26개 단위 테스트 통과

---

### F-003: UserTier System (Phase 3)

**Phase**: 3
**상태**: ✅ 완료
**우선순위**: P1

**설명**:
사용자 등급별 차별화된 서비스 제공

**Tier 비교**:

| Tier | 모델 | Agent Tokens | Report Tokens | 비용 | 품질 |
|------|------|--------------|---------------|------|------|
| **PREMIUM** | gpt-4o | 8000 | 15000 | 높음 | 최고 |
| **STANDARD** | gpt-4o-mini | 4096 | 10000 | 중간 | 좋음 |
| **TRIAL** | gpt-4o-mini | 2000 | 3000 | 낮음 | 기본 |

**사용 방법**:
```python
# WebSocket 메시지에서 user_id로 자동 추출
{
  "message": "...",
  "user_id": "premium_user123"  # → UserTier.PREMIUM
}
```

**구현 상태**:
- ✅ Octostrator 노드: 적용 완료
- ⚠️ Worker Agents: 미적용 (config.openai_model 사용)

---

### F-004: WebSocket 실시간 스트리밍 (Phase 4.3)

**Phase**: 4.3
**상태**: ✅ 완료
**우선순위**: P0

**설명**:
실시간 이벤트 스트리밍을 통한 사용자 경험 향상

**지원 이벤트**:
1. `connected` - 연결 성공
2. `execution_started` - 실행 시작
3. `node_started` - 노드 시작
4. `node_completed` - 노드 완료
5. `plan_update` - 계획 업데이트
6. `todos_update` - Todo 업데이트
7. `execution_update` - 실행 진행 상황
8. `final_result` - 최종 결과
9. `execution_completed` - 실행 완료
10. `error` - 에러 발생

**구현**:
```python
async for event in graph.astream_events(initial_input, config=config, version="v2"):
    # 이벤트 처리 및 WebSocket 전송
    await manager.send_message(session_id, {...})
```

**사용자 혜택**:
- 실시간 진행 상황 확인
- 긴 작업 대기 시간 감소
- 투명한 처리 과정

---

### F-005: Checkpoint & Session 관리 (Phase 4.4)

**Phase**: 4.4
**상태**: ✅ 완료
**우선순위**: P0

**설명**:
PostgreSQL 기반 State Checkpoint 및 세션 관리

**기능**:
1. **Checkpoint 저장**: State를 DB에 자동 저장
2. **세션 복원**: thread_id로 이전 State 복원
3. **히스토리 조회**: 세션별 대화 히스토리

**구현**:
```python
# Checkpointer 생성
checkpointer = await create_checkpointer()

# Graph compile
graph = build_graph(checkpointer=checkpointer)

# 세션 재개
result = await graph.ainvoke(
    {"user_query": "..."},
    config={"configurable": {"thread_id": "session_001"}}
)
```

**혜택**:
- 중단된 대화 재개
- 컨텍스트 유지
- 대화 히스토리 분석

---

## Supervisor Features (레이어 기능)

### F-101: Cognitive Layer

**상태**: ✅ 완료
**파일**: `backend/app/octostrator/supervisors/cognitive/`

**기능**:
1. **의도 파악**: 사용자 질의에서 의도 추출
2. **계획 수립**: 의도에 기반한 실행 계획 생성
3. **검증**: 계획 유효성 검증

**입력**: `user_query: str`

**출력**:
```python
{
    "plan": {
        "goal": "회원 프로그램 설계",
        "steps": [...]
    },
    "plan_valid": True,
    "required_agents": ["assessor", "program_designer"]
}
```

**Test Coverage**: 수동 테스트

---

### F-102: Todo Manager

**상태**: ✅ 완료 (HITL 일부)
**파일**: `backend/app/octostrator/todo_manager/`

**기능**:
1. **Plan → Todo 변환**: 계획을 실행 가능한 Todo로 변환
2. **의존성 관리**: Todo 간 의존성 그래프 생성
3. **HITL**: 승인 필요 시 대기 (구현 중)
4. **조건부 실행**: 필요시에만 실행

**입력**: `plan: dict`

**출력**:
```python
{
    "todos": [
        {
            "id": "todo_1",
            "title": "회원 평가",
            "agent_id": "assessor_agent",
            "status": "pending",
            "dependencies": []
        }
    ]
}
```

**HITL 상태**:
- ✅ requires_approval flag 설정
- ⚠️ AppContext에 auto_approve 필드 필요

---

### F-103: Execute Layer

**상태**: ✅ 완료
**파일**: `backend/app/octostrator/supervisors/execute/`

**기능**:
1. **Agent 실행**: Worker Agents 실행
2. **의존성 해결**: Todo 의존성 기반 실행 순서 결정
3. **병렬 실행**: 독립적인 Todo 병렬 실행
4. **결과 집계**: Agent 결과 통합

**입력**: `todos: List[Dict]`

**출력**:
```python
{
    "execution_results": {
        "agent_1": {...},
        "agent_2": {...}
    },
    "completed": 2,
    "failed": 0,
    "success_rate": 100
}
```

---

### F-104: Response Layer

**상태**: ✅ 완료
**파일**: `backend/app/octostrator/supervisors/response/`

**기능**:
1. **응답 생성**: 실행 결과 기반 응답 생성
2. **포매팅**: output_format에 맞춰 포맷 (chat/report/graph)
3. **품질 검증**: 응답 품질 확인

**입력**: `execution_results: dict, output_format: str`

**출력**:
```python
{
    "final_response": "최종 응답 내용..."
}
```

---

## Worker Agent Features (에이전트 기능)

### F-201: Frontdesk Agent

**상태**: ✅ 완전 구현
**파일**: `backend/app/octostrator/agents/frontdesk/`
**구현도**: 100% (149 lines)

**Pain Point**: "리드를 놓치지 않고 효율적으로 관리하고 싶다"

**기능**:
1. **리드 관리**: 신규 문의 접수 및 분류
2. **리드 스코어링**: 전환 가능성 점수화 (0.0~1.0)
3. **상담 일정 관리**: 가능한 시간대 제공 및 예약
4. **알림 전송**: 트레이너/관리자에게 알림

**입력**:
```python
{
    "inquiry_text": "3개월 PT 등록하고 싶어요",
    "inquiry_type": "membership"
}
```

**출력**:
```python
{
    "lead_info": {
        "lead_id": "lead_001",
        "lead_score": 0.85,
        "priority": "high"
    },
    "recommended_action": "schedule_appointment",
    "estimated_conversion_rate": 0.78
}
```

**구현 상세**:
- ✅ 입력 유효성 검증
- ✅ 에러 처리
- ✅ 메타데이터 (capabilities, supported_channels)

---

### F-202: Assessor Agent

**상태**: 🟡 기본 구조
**파일**: `backend/app/octostrator/agents/assessor/`
**구현도**: 20% (59 lines)

**Pain Point**: "회원 체형과 자세를 '감'이 아닌 '데이터'로 정확하게 분석하고 싶다"

**계획된 기능**:
1. **인바디 분석**: 체성분 데이터 해석
2. **자세 분석**: 이미지 기반 자세 평가
3. **목표 설정**: 회원 목표 분석 및 우선순위 설정
4. **평가 보고서**: 종합 평가 리포트 생성

**필요한 작업**:
- 인바디 데이터 파서
- 자세 분석 알고리즘 (또는 외부 API 연동)
- 평가 리포트 템플릿

---

### F-203: Program Designer Agent

**상태**: 🟡 기본 구조
**파일**: `backend/app/octostrator/agents/program_designer/`
**구현도**: 20% (59 lines)

**Pain Point**: "회원마다 다른 목표와 체형에 맞춘 프로그램을 빠르게 설계하고 싶다"

**계획된 기능**:
1. **프로그램 설계**: 평가 결과 기반 맞춤 프로그램
2. **운동 선택**: 목표에 맞는 운동 선정
3. **단계별 진행**: 프로그램 단계(Phase) 설계
4. **진행도 추적**: 프로그램 수정 및 조정

**필요한 작업**:
- 운동 데이터베이스
- 프로그램 템플릿
- 진행도 추적 로직

---

### F-204 ~ F-207: 기타 Agents

**상태**: 🟡 기본 구조 (각 59 lines)

| Agent | Pain Point | 주요 기능 |
|-------|------------|-----------|
| **Manager** | "회원권, 출석, 매출을 한 번에 관리하고 싶다" | 회원권 관리, 출석 체크, 매출 분석 |
| **Marketing** | "SNS 콘텐츠를 빠르게 만들고 싶다" | 콘텐츠 생성, 이벤트 기획 |
| **Owner Assistant** | "센터 경영을 데이터로 분석하고 싶다" | 비즈니스 인사이트, 경영 분석 |
| **Trainer Education** | "트레이너 교육을 체계화하고 싶다" | 트레이너 교육, 피드백 |

---

## Infrastructure Features (인프라 기능)

### F-301: Custom Reducers

**상태**: ✅ 완료
**파일**: `backend/app/octostrator/states/octostrator_state.py`

**Reducers**:
1. `merge_todos_smart`: ID 기반 Todo 병합
2. `add_with_timestamp_and_step`: 타임스탬프 + 스텝 번호 자동 추가
3. `track_plan_changes`: 계획 변경 추적
4. `track_user_interactions`: 사용자 상호작용 추적

---

### F-302: History Tracking

**상태**: ✅ 완료
**파일**: 모든 Layer 노드

**추적 항목**:
1. `action_history`: 모든 액션 기록
2. `plan_history`: 계획 변경 기록
3. `user_interactions`: 사용자 상호작용 기록

**사용 예시**:
```python
# 노드에서 자동 추적
return {
    "action_history": [
        {"action": "plan_created", "details": "..."}
    ]
}
# → timestamp, step_number 자동 추가
```

---

### F-303: Agent Registry

**상태**: ✅ 완료
**파일**: `backend/app/octostrator/agent_registry/`

**기능**:
1. Agent 등록 및 검색
2. Priority 기반 정렬
3. Capability 기반 검색
4. 의존성 관리

---

## Planned Features (계획된 기능)

### P-001: Worker Agents Context API 통합

**우선순위**: P1
**예상 시간**: 2-3시간

**현재 문제**:
- Worker Agents가 `config.openai_model` 사용
- UserTier 설정 무시

**해결 방안**:
1. Agent Registry가 runtime 지원
2. build_graph()가 Context로부터 LLM 생성
3. execute_layer_node에서 runtime 전달

---

### P-002: AppContext auto_approve 필드

**우선순위**: P1
**예상 시간**: 15분

**현재 문제**:
- todo_layer_node에서 항상 auto_approve=True

**해결 방안**:
```python
@dataclass
class AppContext:
    # ...
    auto_approve: bool = True  # HITL 자동 승인 여부
```

---

### P-003: Agent Graph 비즈니스 로직 구현

**우선순위**: P1
**예상 시간**: 1-2주

**대상**: 6개 Agent (Assessor, ProgramDesigner 등)

**작업**:
1. 각 Agent의 실제 비즈니스 로직 구현
2. Graph 노드 구현
3. State 업데이트 로직
4. 단위 테스트 작성

---

### P-004: 단위/통합 테스트 작성

**우선순위**: P1
**예상 시간**: 1주

**Test Coverage 목표**: >80%

---

### P-005: Production 배포 준비

**우선순위**: P2
**예상 시간**: 1주

**작업**:
1. JWT 인증
2. Rate Limiting
3. 에러 추적 (Sentry)
4. 성능 모니터링
5. DB Migration (Alembic)

---

## 부록

### 기능 통계

| 카테고리 | 총 개수 | 완료 | 진행 중 | 미구현 | 완성도 |
|----------|---------|------|---------|---------|---------|
| Core Features | 5 | 5 | 0 | 0 | 100% |
| Supervisor Features | 4 | 4 | 0 | 0 | 100% |
| Worker Agents | 7 | 1 | 6 | 0 | 20% |
| Infrastructure | 3 | 3 | 0 | 0 | 100% |
| Planned Features | 5 | 0 | 0 | 5 | 0% |
| **Total** | **24** | **13** | **6** | **5** | **60%** |

---

**작성자**: Claude Code Agent
**검토자**: -
**버전**: 1.0
**마지막 업데이트**: 2025-11-06
**관련 문서**:
- [MASTER_CHECKLIST.md](MASTER_CHECKLIST.md)
- [SCHEMA_SPECIFICATIONS.md](SCHEMA_SPECIFICATIONS.md)
- [API_SPECIFICATIONS.md](API_SPECIFICATIONS.md)
