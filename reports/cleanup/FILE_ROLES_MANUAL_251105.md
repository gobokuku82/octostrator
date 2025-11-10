# 📚 Octostrator File Roles Manual

**작성일**: 2025-11-05
**버전**: 1.0
**목적**: 각 파일의 역할과 목적 설명

---

## 📁 디렉토리 구조

```
backend/app/octostrator/
├── agents/               # Agent 구현체들
│   ├── base/            # Agent 프레임워크 (핵심)
│   ├── todo/            # TODO 관리 Agent
│   ├── diet/            # 식단 관리 Agent
│   ├── workout/         # 운동 관리 Agent
│   └── ...              # 기타 도메인 Agent들
├── supervisor/          # Supervisor 레이어
├── states/              # 상태 정의 (중앙집중)
├── tools/               # 도메인별 도구들
├── session/             # 세션 관리
├── checkpointer/        # 상태 영속성
├── contexts/            # 애플리케이션 컨텍스트
└── manual/              # 문서화

```

---

## 🏗️ Core Framework (agents/base/)

### 1. `base_agent.py` (256 lines)
**역할**: 모든 Agent의 추상 베이스 클래스
**핵심 기능**:
- Agent 생명주기 관리
- LangGraph 통합
- Checkpoint 지원
- 표준 인터페이스 정의

**주요 클래스**:
```python
class BaseAgent(ABC):
    - build_graph() # LangGraph workflow 구축
    - execute()     # Agent 실행
    - process_task() # 작업 처리
```

### 2. `agent_registry.py` (347 lines)
**역할**: Agent 동적 등록 및 관리
**핵심 기능**:
- Singleton 패턴으로 전역 Registry
- 런타임 Agent 등록/해제
- Agent 자동 발견
- Capability 기반 라우팅

**사용 예**:
```python
@register_agent("my_agent")
class MyAgent(BaseAgent):
    pass
```

### 3. `capabilities.py` (458 lines)
**역할**: Agent 능력 정의 및 라우팅
**핵심 기능**:
- Capability Enum 정의
- Capability 기반 Agent 선택
- 작업-능력 매칭

### 4. `checkpoint_strategy.py` (310 lines)
**역할**: 상태 저장 전략
**핵심 기능**:
- 선택적 checkpoint 지원
- PostgreSQL 통합
- 상태 복원 메커니즘

### 5. `dependency_resolver.py` (334 lines)
**역할**: Agent 간 의존성 관리
**핵심 기능**:
- 토폴로지 정렬
- 순환 의존성 감지
- 병렬 실행 그룹 계산

---

## 🎯 Supervisor Layer (supervisor/)

### 1. `cognitive_supervisor.py` (456 lines)
**역할**: Layer 1 - 계획 수립
**핵심 기능**:
- 사용자 의도 파악
- 실행 계획 생성
- 도메인 분석
- 필요 Agent 결정

### 2. `execute_supervisor.py` (520 lines)
**역할**: Layer 3 - 실행 관리
**핵심 기능**:
- Agent 오케스트레이션
- 병렬 실행 관리
- 결과 집계
- 에러 처리

### 3. `cognitive_nodes.py` (381 lines)
**역할**: Cognitive 워크플로우 노드
**핵심 노드**:
- `intent_understanding_node` - 의도 파악
- `planning_node` - 계획 생성
- `validator_node` - 계획 검증

### 4. `response_nodes.py` (492 lines)
**역할**: 응답 생성 노드
**핵심 노드**:
- `aggregator_node` - 결과 집계
- `generator_node` - 최종 응답 생성
- `hitl_handler_node` - 사용자 상호작용

### 5. `cognitive_prompts.py` (135 lines)
**역할**: LLM 프롬프트 템플릿
**내용**:
- 의도 분석 프롬프트
- 계획 생성 프롬프트
- 응답 생성 프롬프트

### 6. `main_graph.py` (276 lines)
**역할**: 전체 워크플로우 정의
**핵심 기능**:
- StateGraph 구성
- 노드 연결
- 조건부 라우팅
- 레거시 호환성 유지

---

## 📦 State Management (states/)

### 1. `base.py` (97 lines)
**역할**: 기본 상태 클래스
**주요 클래스**:
- `BaseState` - 모든 상태의 기본
- `BaseAgentState` - Agent 상태 기본
- Type aliases (TaskDict, ResultDict 등)

### 2. `supervisors.py` (191 lines)
**역할**: Supervisor 상태 정의
**주요 상태**:
- `CognitiveSupervisorState` - 계획 레이어
- `ExecuteSupervisorState` - 실행 레이어
- `MainOrchestratorState` - 전체 조율
- `HumanInTheLoopState` - HITL 관리

### 3. `todo_agent_state.py` (130 lines)
**역할**: TodoAgent 전용 상태
**주요 구조**:
- `TodoItem` - 개별 TODO
- `TodoBatch` - TODO 묶음
- HITL 관련 필드

### 4. `diet_agent_state.py` (268 lines)
**역할**: DietAgent 전용 상태
**주요 구조**:
- `NutritionInfo` - 영양 정보
- `MealItem` - 식사 항목
- `DietPlan` - 식단 계획

### 5. `workout_agent_state.py` (207 lines)
**역할**: WorkoutAgent 전용 상태
**주요 구조**:
- `Exercise` - 운동 정보
- `WorkoutSession` - 운동 세션
- `WorkoutPlan` - 운동 계획

---

## 🤖 Agent Implementations (agents/)

### 1. `todo/todo_agent.py` (553 lines)
**역할**: Layer 2 - TODO 관리
**핵심 기능**:
- Plan → TODO 변환
- HITL 처리
- 의존성 분석
- 실행 순서 결정

### 2. `diet/diet_agent_v2.py` (414 lines) ✅
**역할**: 식단 관리 Agent
**핵심 기능**:
- 칼로리 계산
- 영양 분석
- 식단 생성
- 건강 데이터 처리

### 3. `workout/agent.py` (80 lines) ⚠️ Legacy
**역할**: 운동 관리 (구버전)
**상태**: BaseAgent로 마이그레이션 필요

### 4. `schedule/agent.py` (77 lines) ⚠️ Legacy
**역할**: 일정 관리 (구버전)
**상태**: BaseAgent로 마이그레이션 필요

---

## 🔧 Tools (tools/)

### 1. `diet_tools.py` (331 lines)
**역할**: 식단 관련 도구
**주요 함수**:
- `calculate_bmr()` - 기초대사율
- `calculate_tdee()` - 일일 칼로리
- `analyze_nutrition()` - 영양 분석

### 2. `workout_tools.py` (329 lines)
**역할**: 운동 관련 도구
**주요 함수**:
- `generate_workout()` - 운동 생성
- `calculate_1rm()` - 1RM 계산
- `analyze_form()` - 자세 분석

### 3. `schedule_tools.py` (286 lines)
**역할**: 일정 관련 도구
**주요 함수**:
- `check_conflicts()` - 충돌 검사
- `optimize_schedule()` - 일정 최적화

### 4. `coaching_tools.py` (299 lines)
**역할**: 코칭 관련 도구
**주요 함수**:
- `generate_feedback()` - 피드백 생성
- `analyze_progress()` - 진행도 분석

### 5. `member_care_tools.py` (262 lines)
**역할**: 회원 관리 도구
**주요 함수**:
- `send_reminders()` - 알림 발송
- `track_engagement()` - 참여도 추적

---

## 🏢 Infrastructure

### 1. `main_orchestrator.py` (312 lines)
**역할**: 3-Layer 아키텍처 메인 조율자
**핵심 기능**:
- Layer 간 조율
- 전체 워크플로우 관리
- 세션 관리
- HITL 처리

### 2. `session/session_manager.py` (29 lines)
**역할**: 세션 영속성
**핵심 기능**:
- 세션 상태 저장/로드
- 세션 생명주기 관리

### 3. `checkpointer/postgres_checkpointer.py` (27 lines)
**역할**: PostgreSQL checkpoint
**핵심 기능**:
- AsyncPostgresSaver 래퍼
- 상태 영속성

### 4. `contexts/app_context.py` (61 lines)
**역할**: 애플리케이션 컨텍스트
**핵심 기능**:
- 전역 설정 관리
- 의존성 주입

---

## 📝 Documentation (manual/)

### 1. `SYSTEM_ARCHITECTURE_MANUAL_251105.md`
**목적**: 전체 시스템 아키텍처 설명

### 2. `AGENT_DEVELOPMENT_GUIDE_251105.md`
**목적**: Agent 개발 가이드

### 3. `API_REFERENCE_251105.md`
**목적**: API 문서

### 4. `MIGRATION_GUIDE_251105.md`
**목적**: 마이그레이션 가이드

### 5. `QUICK_START_251105.md`
**목적**: 빠른 시작 가이드

### 6. `CLEANUP_PLAN_251105.md`
**목적**: 코드 정리 계획

### 7. `FILE_ROLES_MANUAL_251105.md`
**목적**: 파일별 역할 설명 (이 문서)

---

## 🔄 파일 간 관계

### 1. 핵심 흐름
```
main_orchestrator.py
    ├─> cognitive_supervisor.py (계획)
    ├─> todo_agent.py (TODO 변환)
    └─> execute_supervisor.py (실행)
            └─> 각 도메인 Agent들
```

### 2. 상태 흐름
```
BaseState (base.py)
    ├─> CognitiveSupervisorState (supervisors.py)
    ├─> TodoAgentState (todo_agent_state.py)
    └─> 각 Agent State (diet_agent_state.py 등)
```

### 3. Agent 생성
```
BaseAgent (base_agent.py)
    └─> @register_agent (agent_registry.py)
            └─> Agent 구현체 (diet_agent_v2.py 등)
```

---

## ⚡ 빠른 참조

### 새 Agent 추가 시
1. `states/{agent}_agent_state.py` - State 정의
2. `agents/{agent}/{agent}_agent.py` - Agent 구현
3. `tools/{agent}_tools.py` - 도구 구현 (선택)
4. `agents/base/capabilities.py` - Capability 추가

### 수정이 자주 필요한 파일
- `cognitive_prompts.py` - 프롬프트 조정
- `capabilities.py` - 새 능력 추가
- `main_graph.py` - 워크플로우 변경

### 디버깅 시 확인 파일
- `main_orchestrator.py` - 전체 흐름
- `execute_supervisor.py` - 실행 로직
- 해당 Agent 파일

---

## 🚀 Best Practices

1. **State는 states/ 폴더에**: 중앙 관리
2. **Agent는 BaseAgent 상속**: 표준화
3. **Tool은 순수 함수로**: 테스트 용이
4. **Registry 활용**: 동적 Agent 관리
5. **Capability 기반 설계**: 확장성

---

**마지막 업데이트**: 2025-11-05
**다음 업데이트 예정**: Agent 추가 시