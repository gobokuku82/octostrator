# 🎯 AI PT Manager - Final Master Plan

**작성일**: 2025-11-05
**작성자**: AI Assistant
**버전**: FINAL v1.0
**목적**: LangGraph 기반 차세대 AI PT Manager 시스템 최종 마스터 플랜

---

## Executive Summary

### 📌 핵심 변화

| 구분 | AS-IS (현재) | TO-BE (목표) |
|------|-------------|--------------|
| **Architecture** | 단일 Supervisor + Simple Functions | Dual Supervisor + LangGraph Agents |
| **Agents** | 5개 단순 함수 | 10+ 복잡한 LangGraph Workflows |
| **State Management** | SupervisorState only | Multi-layer States + TODO Management |
| **Intent** | 없음 | Intent Classification System |
| **Memory** | 없음 | Long-term Memory + Context |
| **Checkpoint** | Supervisor만 | Agent별 선택적 Checkpoint |
| **Modification** | 불가능 | 실시간 수정 가능 |

### 🚀 목표
- **확장성**: 10개 이상의 복잡한 Agent 관리
- **지능화**: Intent 분류와 Memory 기반 개인화
- **유연성**: 실행 중 계획 수정 가능
- **성능**: 병렬 실행과 선택적 Checkpoint

---

## 1. 전체 아키텍처

### 1.1 System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│                 (React + WebSocket)                      │
└─────────────────────────────────────────────────────────┘
                            │
                        WebSocket
                            │
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                        │
└─────────────────────────────────────────────────────────┘
                            │
                ┌──────────┴───────────┐
                ▼                      ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│   INTENT CLASSIFIER     │  │    MEMORY MANAGER       │
│  - Pattern Matching     │  │  - User Profile         │
│  - Context Resolution   │  │  - Conversation History │
│  - Reference Handling   │  │  - Task History         │
└─────────────────────────┘  └─────────────────────────┘
                ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│              COGNITIVE SUPERVISOR                        │
│  - Intent Analysis                                       │
│  - Plan Generation                                       │
│  - TODO Creation                                         │
│  - Modification Handling                                 │
└─────────────────────────────────────────────────────────┘
                            │
                     TODO Management
                            │
┌─────────────────────────────────────────────────────────┐
│               EXECUTE SUPERVISOR                         │
│  - TODO Execution                                        │
│  - Agent Orchestration                                   │
│  - Progress Tracking                                     │
│  - Error Handling                                        │
└─────────────────────────────────────────────────────────┘
                            │
        ┌──────────────┬────┴────┬──────────────┐
        ▼              ▼         ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  DietAgent   │ │ WorkoutAgent │ │ScheduleAgent │ ...10+
│ (LangGraph)  │ │ (LangGraph)  │ │ (LangGraph)  │ Agents
│ +Checkpoint  │ │ +Checkpoint  │ │ -Checkpoint  │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │               │
        ▼              ▼               ▼
┌─────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                     │
│  - Checkpoints (LangGraph States)                        │
│  - User Profiles & Preferences                           │
│  - Task History & Results                                │
│  - Vector Embeddings (pgvector)                          │
└─────────────────────────────────────────────────────────┘
```

### 1.2 핵심 Design Decisions

#### ✅ Decision 1: Dual Supervisor Architecture
- **Cognitive Supervisor**: 계획과 의사결정
- **Execute Supervisor**: 실행과 모니터링
- **이유**: 명확한 책임 분리, 독립적 확장

#### ✅ Decision 2: Individual Agent Architecture (No Teams)
- 팀 단위 X, 개별 Agent 기반
- BaseAgent 추상 클래스 상속
- **이유**: 10+ Agent 확장성, 유연한 관리

#### ✅ Decision 3: TODO Management State
- 실행 계획을 TODO로 관리
- 실시간 수정 가능
- 버전 관리와 이력 추적
- **이유**: 유연한 실행 흐름, 사용자 제어

#### ✅ Decision 4: Intent + Memory Integration
- Intent Classification으로 의도 파악
- Memory Manager로 컨텍스트 유지
- **이유**: 자연스러운 대화, 개인화

---

## 2. 핵심 컴포넌트

### 2.1 Base Infrastructure

```python
backend/app/octostrator/
├── agents/
│   └── base/
│       ├── base_agent.py          # BaseAgent 추상 클래스
│       ├── agent_registry.py      # Agent 동적 관리
│       ├── checkpoint_strategy.py # 선택적 Checkpoint
│       └── dependency_resolver.py # 의존성 해결
```

**BaseAgent Pattern**
```python
class BaseAgent(ABC):
    - agent_id: str
    - enable_checkpoint: bool
    - dependencies: List[str]

    @abstractmethod
    def build_graph() -> StateGraph

    @abstractmethod
    async def process_task() -> Dict
```

### 2.2 Supervisor System

```python
backend/app/octostrator/supervisor/
├── cognitive_supervisor.py   # 계획/수정
├── execute_supervisor.py     # 실행/추적
├── states/
│   ├── todo_state.py        # TODO Management
│   └── cognitive_state.py   # 인지 State
└── managers/
    └── todo_manager.py       # TODO CRUD
```

**Dual Supervisor Flow**
```
User Message → Cognitive → TODOs → Execute → Results
                  ↑                    ↓
                  └── Modifications ────┘
```

### 2.3 Intelligence Layer

```python
backend/app/octostrator/
├── intent/
│   ├── classifier.py         # Intent 분류
│   ├── patterns.py          # 패턴 정의
│   └── resolver.py          # 참조 해결
└── memory/
    ├── manager.py           # Memory 관리
    ├── embeddings.py        # 벡터 임베딩
    └── schemas.py           # DB 스키마
```

**Intent Categories**
- CREATE: 새로 생성
- MODIFY: 수정
- QUERY: 조회
- EXECUTE: 실행
- MANAGE: 관리

### 2.4 Agent Implementation

```python
backend/app/octostrator/agents/
├── diet/
│   ├── diet_agent.py       # LangGraph Agent
│   └── agent.py            # Legacy 호환
├── workout/
├── schedule/
├── coaching/
├── payment/
├── notification/
└── ... (10+ agents)
```

**Agent Types**
- **Complex (w/ Checkpoint)**: Diet, Workout, Payment
- **Simple (Stateless)**: Notification, Reporting
- **Scheduled**: Reminder, Monitoring

---

## 3. State Management Strategy

### 3.1 State Hierarchy

```
Global Session State
├── Cognitive State
│   ├── Intent
│   ├── Context
│   └── TODO Management
├── Execute State
│   ├── Current Execution
│   ├── Progress
│   └── Results
└── Agent States
    ├── DietAgentState
    ├── WorkoutAgentState
    └── ...
```

### 3.2 TODO Management

```python
class TodoItem:
    id: str                   # todo_abc123
    title: str               # "Create meal plan"
    agent: str               # "diet_agent"
    status: TodoStatus       # PENDING|IN_PROGRESS|COMPLETED
    dependencies: List[str]  # ["todo_xyz789"]
    version: int            # 수정 버전
    modifications: List     # 수정 이력
```

**TODO Lifecycle**
```
PENDING → IN_PROGRESS → COMPLETED
    ↓          ↓           ↑
MODIFIED → RETRY → FAILED → SKIPPED
```

---

## 4. 구현 로드맵

### Phase 0: Foundation (Day 1-3) ✅ [완료]
- [x] BaseAgent 클래스 구현
- [x] AgentRegistry 구현
- [x] CheckpointStrategy 구현
- [x] DependencyResolver 구현
- [x] 계획서 작성

### Phase 1: Core Infrastructure (Day 4-6)
- [ ] TODO Management State 구현
- [ ] TodoManager 클래스 구현
- [ ] Cognitive Supervisor 구현
- [ ] Execute Supervisor 구현

### Phase 2: Intelligence Layer (Day 7-9)
- [ ] Intent Classifier 구현
- [ ] Memory Manager 구현
- [ ] Context Resolver 구현
- [ ] PostgreSQL Schema 설정

### Phase 3: Agent Migration (Day 10-14)
- [ ] DietAgent to LangGraph
- [ ] WorkoutAgent to LangGraph
- [ ] ScheduleAgent to LangGraph
- [ ] CoachingAgent to LangGraph
- [ ] PaymentAgent to LangGraph

### Phase 4: Integration (Day 15-17)
- [ ] Supervisor 통합
- [ ] WebSocket Handler 수정
- [ ] Frontend 연동
- [ ] End-to-end 테스트

### Phase 5: Optimization (Day 18-20)
- [ ] 병렬 실행 최적화
- [ ] Checkpoint 전략 튜닝
- [ ] 캐싱 구현
- [ ] 성능 테스트

### Phase 6: Deployment (Day 21)
- [ ] 문서화 완성
- [ ] 배포 준비
- [ ] 모니터링 설정
- [ ] Production 배포

---

## 5. 마이그레이션 전략

### 5.1 단계적 마이그레이션

```
Week 1: Infrastructure
- Dual Supervisor 구현
- TODO Management 구현

Week 2: Intelligence
- Intent Classification
- Memory Integration

Week 3: Agents
- 5 Core Agents 마이그레이션
- 5 Additional Agents 추가
```

### 5.2 하위 호환성 유지

```python
# 기존 코드 호환
from app.octostrator.agents.diet import diet_agent_node  # Legacy

# 새로운 코드
from app.octostrator.agents.diet import DietAgent  # New
```

### 5.3 점진적 롤아웃

1. **Alpha**: 내부 테스트 (5 Agents)
2. **Beta**: 제한된 사용자 (10 Agents)
3. **Production**: 전체 배포 (15+ Agents)

---

## 6. 기술 스택

### 6.1 Backend
- **Framework**: FastAPI
- **LangGraph**: Agent Workflows
- **LangChain**: LLM Integration
- **Database**: PostgreSQL + pgvector
- **WebSocket**: Real-time Communication

### 6.2 Frontend
- **Framework**: React + TypeScript
- **State**: Redux/Zustand
- **UI**: Material-UI/Tailwind
- **WebSocket**: socket.io-client

### 6.3 Infrastructure
- **Container**: Docker
- **Orchestration**: Docker Compose
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack

---

## 7. 예상 결과

### 7.1 기능적 개선

| 항목 | 현재 | 목표 | 개선율 |
|------|------|------|-------|
| Agent 수 | 5 | 15+ | 300% |
| 복잡도 처리 | 단순 | 복잡 워크플로우 | - |
| 응답 정확도 | 70% | 95% | 35% |
| 개인화 | 없음 | Memory 기반 | - |
| 수정 가능성 | 불가 | 실시간 수정 | - |

### 7.2 성능 지표

- **응답 시간**: < 2초 (계획 수립)
- **실행 시간**: Agent당 평균 1-3초
- **동시 사용자**: 100+
- **Checkpoint 크기**: < 10MB/session

### 7.3 사용자 경험

- ✅ 자연스러운 대화 (Intent + Memory)
- ✅ 실시간 진행률 표시
- ✅ 실행 중 수정 가능
- ✅ 개인화된 추천
- ✅ 이전 대화 참조

---

## 8. 리스크 및 대응

### 8.1 기술적 리스크

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| State 크기 증가 | High | Selective Checkpoint |
| Graph 복잡도 | Medium | Dual Supervisor 분리 |
| 의존성 충돌 | Low | Dependency Resolver |
| 성능 저하 | Medium | 병렬 실행, 캐싱 |

### 8.2 운영 리스크

- **마이그레이션 실패**: 단계적 롤백 계획
- **하위 호환성**: Legacy 코드 유지
- **모니터링**: 실시간 메트릭 수집

---

## 9. 성공 기준

### 9.1 필수 요구사항 ✅
- [ ] 10+ Agent 지원
- [ ] LangGraph 기반 Agent
- [ ] TODO Management
- [ ] 실시간 수정
- [ ] Intent Classification
- [ ] Memory Integration

### 9.2 성능 요구사항 📊
- [ ] 응답 시간 < 2초
- [ ] 동시 사용자 100+
- [ ] 가용성 99.9%

### 9.3 품질 요구사항 🎯
- [ ] 테스트 커버리지 80%
- [ ] 문서화 100%
- [ ] 코드 리뷰 완료

---

## 10. 다음 단계

### 🚀 즉시 시작 (Today)
1. TODO Management State 구현
2. Cognitive Supervisor 개발 시작
3. Execute Supervisor 개발 시작

### 📅 이번 주 (Week 1)
1. Dual Supervisor 완성
2. Intent Classifier 기본 구현
3. DietAgent 마이그레이션

### 🎯 이번 달 (Month 1)
1. 전체 시스템 통합
2. 10개 Agent 마이그레이션
3. Beta 테스트 시작

---

## 부록

### A. 관련 문서
1. [SCALABLE_AGENT_ARCHITECTURE_251105.md](./SCALABLE_AGENT_ARCHITECTURE_251105.md)
2. [COGNITIVE_EXECUTE_SEPARATION_251105.md](./COGNITIVE_EXECUTE_SEPARATION_251105.md)
3. [INTENT_MEMORY_ARCHITECTURE_251105.md](./INTENT_MEMORY_ARCHITECTURE_251105.md)
4. [TODO_MANAGEMENT_IMPLEMENTATION_GUIDE_251105.md](./TODO_MANAGEMENT_IMPLEMENTATION_GUIDE_251105.md)

### B. 코드 템플릿
- BaseAgent Template
- Supervisor Template
- TODO Manager Template
- Intent Classifier Template

### C. 테스트 시나리오
1. 신규 사용자 시나리오
2. 복잡한 대화 시나리오
3. 실행 중 수정 시나리오
4. 에러 복구 시나리오

---

## 승인 및 결정

### 최종 결정 사항

✅ **Architecture**: Dual Supervisor (Cognitive + Execute)
✅ **Agent Pattern**: Individual BaseAgent (No Teams)
✅ **State Management**: TODO Management with Modifications
✅ **Intelligence**: Intent + Memory Integration
✅ **Checkpoint**: Selective per Agent

### Sign-off

| 역할 | 담당자 | 승인 | 날짜 |
|------|--------|------|------|
| Architect | AI Assistant | ✅ | 2025-11-05 |
| Developer | - | ⬜ | - |
| Product Owner | - | ⬜ | - |

---

**🎉 Ready to Execute!**

이 계획서를 기반으로 차세대 AI PT Manager 시스템을 구축합니다.
모든 아키텍처 결정이 완료되었으며, 구현을 시작할 준비가 되었습니다.

---

**작성 완료일**: 2025-11-05
**최종 버전**: FINAL v1.0
**문서 위치**: `reports/supervisor/FINAL_MASTER_PLAN_251105.md`