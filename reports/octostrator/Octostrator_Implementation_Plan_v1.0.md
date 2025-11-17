# 📋 Octostrator 구현 계획서 v1.0

**프로젝트명**: Octostrator - LangGraph 기반 지능형 코딩 어시스턴트
**작성일**: 2024-11-17
**버전**: 1.0
**목적**: LangGraph 1.0을 활용한 TODO 기반 자율 에이전트 시스템 구현

---

## 📌 Executive Summary

Octostrator는 Cursor나 VS Code의 Claude Desktop과 유사한 코딩 어시스턴트로, 사용자의 질문을 내부적으로 TODO로 변환하여 관리하며, 두 가지 HITL(Human-in-the-Loop) 메커니즘을 통해 사용자가 언제든 개입할 수 있는 지능형 에이전트 시스템입니다.

### 핵심 특징
- **자동 TODO 관리**: 사용자 요청을 자동으로 작업 단위로 분해
- **실시간 개입**: ESC 키로 언제든 작업 중단 및 수정 가능
- **지능형 Interrupt**: 에이전트가 필요시 사용자 의견 요청
- **확장 가능한 아키텍처**: 도메인별 실행 에이전트 플러그인 구조

---

## 🎯 프로젝트 목표

### 1차 목표 (MVP)
1. LangGraph 1.0 기반 멀티 에이전트 시스템 구축
2. TODO 자동 생성 및 관리 시스템
3. HITL 메커니즘 구현 (ESC 개입, Interrupt)
4. Mock 실행 에이전트로 전체 워크플로우 검증

### 2차 목표 (확장)
1. 실제 도메인별 실행 에이전트 추가
2. 고급 메모리 관리 (장기 학습)
3. 협업 기능 (멀티 유저)
4. IDE 플러그인 개발

---

## 🛠️ 기술 스택

### Backend
- **Python**: 3.12.7
- **Framework**: FastAPI 0.115.0
- **LangGraph**: 1.0.2 (LangChain 1.0.3)
- **LLM**: OpenAI GPT-4o-mini
- **Database**:
  - PostgreSQL (AsyncPostgreSaver - Checkpointer)
  - Redis (Store API - Long-term Memory)
- **Package Manager**: UV

### Frontend
- **Framework**: Next.js 14+ (React 18+)
- **State Management**: Zustand
- **Styling**: Tailwind CSS
- **WebSocket**: Native WebSocket API
- **Build Tool**: Turbo

### Infrastructure
- **Container**: Docker & Docker Compose
- **Process Manager**: PM2 (Production)
- **Reverse Proxy**: Nginx

---

## 🏗️ 시스템 아키텍처

### 컴포넌트 다이어그램
```
┌─────────────────────────────────────────────────┐
│                  Frontend (Next.js)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   Chat   │  │   TODO   │  │  Debug   │     │
│  │Interface │  │  Panel   │  │ Console  │     │
│  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────┬───────────────────────────────┘
                  │ WebSocket / REST API
┌─────────────────▼───────────────────────────────┐
│              FastAPI Backend                    │
│  ┌────────────────────────────────────────┐   │
│  │          Octostrator Core              │   │
│  │  ┌──────────┐  ┌──────────┐           │   │
│  │  │ LangGraph│  │   TODO   │           │   │
│  │  │  Engine  │◄─┤ Manager  │           │   │
│  │  └──────────┘  └──────────┘           │   │
│  │       ▲              ▲                 │   │
│  │       │              │                 │   │
│  │  ┌────▼────┐   ┌────▼────┐           │   │
│  │  │ Planner │   │ Router  │           │   │
│  │  │  Agent  │   │  Agent  │           │   │
│  │  └─────────┘   └─────────┘           │   │
│  │       │              │                 │   │
│  │  ┌────▼──────────────▼────┐           │   │
│  │  │   Execution Agents      │           │   │
│  │  │ (Search/Analysis/Doc)   │           │   │
│  │  └─────────────────────────┘           │   │
│  └────────────────────────────────────────┘   │
└─────────────────┬───────────┬───────────────────┘
                  │           │
        ┌─────────▼───┐   ┌──▼──────┐
        │ PostgreSQL  │   │  Redis   │
        │(Checkpoint) │   │ (Store)  │
        └─────────────┘   └──────────┘
```

### 데이터 플로우
```
User Input
    ↓
Planner Agent (TODO 생성)
    ↓
Router Agent (작업 분배)
    ↓
Execution Agents (병렬 실행)
    ↓
Validator Agent (검증)
    ↓
Response to User
```

---

## 📁 프로젝트 구조

```
octostrator/
├── backend/
│   ├── app/
│   │   ├── octostrator/           # 핵심 에이전트 시스템
│   │   │   ├── agents/            # 에이전트 정의
│   │   │   ├── graphs/            # LangGraph 그래프
│   │   │   ├── tools/             # 에이전트 도구
│   │   │   ├── managers/          # 관리자 클래스
│   │   │   ├── services/          # 내부 서비스
│   │   │   └── config.py          # Octostrator 설정
│   │   ├── api/                   # API 엔드포인트
│   │   └── main.py                # FastAPI 앱
│   ├── core/                      # 핵심 설정
│   ├── db/                        # 데이터베이스
│   ├── schema/                    # Pydantic 스키마
│   ├── models/                    # 도메인 모델
│   └── utils/                     # 유틸리티
├── frontend/
│   ├── app/                       # Next.js 앱
│   ├── components/                # React 컴포넌트
│   ├── hooks/                     # 커스텀 훅
│   ├── services/                  # API 서비스
│   ├── store/                     # Zustand 스토어
│   └── types/                     # TypeScript 타입
├── data/                          # Mock 데이터
├── tests/                         # 테스트
├── scripts/                       # 유틸리티 스크립트
└── docker/                        # Docker 설정
```

---

## 🔑 핵심 기능 상세

### 1. TODO 관리 시스템

#### TODO 구조
```python
class TodoItem:
    id: str                    # 고유 식별자
    title: str                 # 작업 제목
    description: str           # 상세 설명
    status: TodoStatus         # pending/in_progress/completed/cancelled
    priority: Priority         # high/medium/low
    dependencies: List[str]    # 의존 TODO ID
    agent: str                # 담당 에이전트
    parent_id: Optional[str]   # 부모 TODO (계층 구조)
    metadata: Dict            # 추가 메타데이터
    created_at: datetime
    updated_at: datetime
```

#### TODO 생명주기
1. **생성**: 사용자 입력 → Planner Agent가 TODO 생성
2. **분배**: Router Agent가 적절한 실행 에이전트에 할당
3. **실행**: 할당된 에이전트가 작업 수행
4. **검증**: Validator Agent가 결과 확인
5. **완료**: 상태 업데이트 및 다음 작업 진행

### 2. HITL (Human-in-the-Loop)

#### ESC 개입 메커니즘
```python
# WebSocket 이벤트 핸들러
async def handle_esc_interrupt(websocket, path):
    # 1. ESC 신호 수신
    # 2. 현재 실행중인 그래프 중단
    await graph.interrupt()
    # 3. 체크포인트 저장
    checkpoint = await checkpointer.save(state)
    # 4. 사용자 입력 대기
    user_input = await websocket.recv()
    # 5. Command로 재개
    await graph.resume(Command(resume=user_input))
```

#### Interrupt 시나리오
```python
# 에이전트 내부에서 Interrupt 발생
def execution_agent(state):
    if ambiguous_requirement:
        # 사용자 의견 필요
        user_feedback = interrupt("이 요구사항을 명확히 해주세요")
        state.update(clarification=user_feedback)

    if risky_operation:
        # 승인 필요
        approval = interrupt("이 작업을 진행할까요?")
        if not approval:
            return Command(goto="alternative_path")
```

### 3. 멀티 에이전트 협업

#### Parent-Subgraph 통신
```python
# Command API 활용
def parent_graph(state):
    # Subgraph로 작업 전달
    return Command(goto="subgraph", update={"task": task})

def subgraph(state):
    # 작업 완료 후 Parent로 복귀
    return Command.PARENT
```

#### Send API로 병렬 처리
```python
def distribute_todos(state):
    # TODO별로 병렬 실행
    return [
        Send("process_todo", {"todo": todo})
        for todo in state["todos"]
    ]
```

### 4. 메모리 관리

#### Short-term Memory (Checkpointer)
- PostgreSQL 기반
- Thread별 대화 히스토리
- 현재 세션 상태

#### Long-term Memory (Store API)
- Redis 기반
- 사용자 프로필/선호도
- 학습된 패턴
- 크로스 세션 인사이트

```python
# Store API 사용
async def save_to_memory(runtime, key, value):
    await runtime.store.put(
        namespace=(user_id, "preferences"),
        key=key,
        value=value
    )

async def retrieve_from_memory(runtime, key):
    return await runtime.store.get(
        namespace=(user_id, "preferences"),
        key=key
    )
```

---

## 📊 개발 Phase 계획

### Phase 1: Core Architecture (3일)
**목표**: 기본 인프라 및 LangGraph 코어 구현

#### Day 1: 프로젝트 초기 설정
- [ ] 프로젝트 구조 생성
- [ ] UV 기반 패키지 설정
- [ ] Docker Compose 구성 (PostgreSQL, Redis)
- [ ] 환경 변수 설정 (.env)

#### Day 2: LangGraph Core 구현
- [ ] State/Graph 정의
- [ ] Parent-Subgraph 구조 구현
- [ ] AsyncPostgreSaver 설정
- [ ] Redis Store 연동

#### Day 3: 기본 에이전트 체인
- [ ] PlannerAgent 구현
- [ ] RouterAgent 구현
- [ ] ValidatorAgent 구현
- [ ] Command/Send API 통합

### Phase 2: TODO Management System (3일)
**목표**: TODO 관리 로직 및 API 구현

#### Day 4: TODO 모델 및 API
- [ ] TODO 데이터 모델 정의
- [ ] CRUD API 구현
- [ ] 의존성 관리 로직
- [ ] 상태 전이 로직

#### Day 5: Graph-TODO 통합
- [ ] TODO를 Graph State로 변환
- [ ] 병렬/직렬 실행 로직
- [ ] Context API로 TODO 공유
- [ ] Subgraph TODO 관리

#### Day 6: 자연어 TODO 수정
- [ ] LLM 기반 TODO 해석
- [ ] 수정 명령 파싱
- [ ] 충돌 해결 로직
- [ ] 변경 이력 관리

### Phase 3: HITL Implementation (3일)
**목표**: Human-in-the-Loop 메커니즘 구현

#### Day 7: Interrupt 시스템
- [ ] interrupt() 함수 구현
- [ ] 다중 interrupt 관리
- [ ] Resume 로직
- [ ] Timeout 처리

#### Day 8: ESC 개입 시스템
- [ ] WebSocket 서버 구현
- [ ] 실시간 상태 전송
- [ ] 개입 신호 처리
- [ ] 상태 복구 메커니즘

#### Day 9: 사용자 피드백 루프
- [ ] 승인 요청 UI
- [ ] 수정 제안 처리
- [ ] 롤백 메커니즘
- [ ] 이력 관리

### Phase 4: Mock Agents & Tools (2일)
**목표**: Mock 실행 에이전트 및 도구 구현

#### Day 10: Mock 실행 에이전트
- [ ] DataSearchAgent 구현
- [ ] AnalysisAgent 구현
- [ ] DocumentAgent 구현
- [ ] APIAgent 구현

#### Day 11: Mock Tools
- [ ] SearchTool (샘플 데이터)
- [ ] AnalysisTool (더미 분석)
- [ ] DocumentTool (템플릿 생성)
- [ ] APITool (Mock 응답)

### Phase 5: Frontend Development (4일)
**목표**: Next.js 기반 UI 구현

#### Day 12: Next.js 프로젝트 설정
- [ ] 프로젝트 구조 생성
- [ ] 컴포넌트 폴더 구조
- [ ] Zustand 스토어 설정
- [ ] API 클라이언트 설정

#### Day 13: Core UI 컴포넌트
- [ ] ChatInterface 구현
- [ ] TodoPanel 구현
- [ ] StatusBar 구현
- [ ] DebugConsole 구현

#### Day 14: WebSocket 통합
- [ ] 실시간 메시지 스트리밍
- [ ] TODO 업데이트 구독
- [ ] ESC 키 핸들링
- [ ] 상태 동기화

#### Day 15: 고급 기능
- [ ] 로그 뷰어
- [ ] 디버그 모드
- [ ] 테마 전환
- [ ] 반응형 디자인

### Phase 6: Integration & Testing (2일)
**목표**: 통합 테스트 및 최적화

#### Day 16: 통합 테스트
- [ ] E2E 테스트 시나리오
- [ ] 성능 테스트
- [ ] 에러 처리 테스트
- [ ] 멀티 사용자 테스트

#### Day 17: 최적화 및 문서화
- [ ] 성능 최적화
- [ ] 보안 점검
- [ ] API 문서 생성
- [ ] 배포 가이드 작성

---

## 🚀 구현 전략

### 1. 점진적 개발
- 각 Phase별 독립적 테스트
- 작동 가능한 MVP 우선 구축
- 피드백 기반 반복 개선

### 2. Mock First 접근
- Mock 도구로 전체 플로우 검증
- 실제 구현은 인터페이스 유지하며 교체
- 테스트 용이성 확보

### 3. 확장 가능한 설계
- 플러그인 아키텍처로 에이전트 추가 용이
- 도메인별 독립적 구현
- 느슨한 결합 유지

---

## 📝 위험 요소 및 대응 방안

### 기술적 위험
1. **LangGraph 1.0 신규 기능 안정성**
   - 대응: 핵심 기능 위주 사용, 점진적 적용

2. **실시간 WebSocket 연결 관리**
   - 대응: 재연결 로직, 하트비트 구현

3. **LLM API 비용 및 속도**
   - 대응: 캐싱, 스트리밍, 적절한 모델 선택

### 운영적 위험
1. **복잡한 TODO 의존성 관리**
   - 대응: DAG 검증, 순환 참조 방지

2. **동시 사용자 처리**
   - 대응: 세션 격리, 리소스 관리

---

## 📈 성공 지표

### 기능적 지표
- [ ] 사용자 요청 → TODO 변환 정확도 > 90%
- [ ] ESC 개입 응답 시간 < 100ms
- [ ] Interrupt 처리 성공률 > 95%

### 성능 지표
- [ ] 첫 응답 시간 < 2초
- [ ] 동시 세션 지원 > 100개
- [ ] 메모리 사용량 < 1GB/세션

### 사용성 지표
- [ ] 사용자 만족도 > 4/5
- [ ] 평균 세션 시간 > 10분
- [ ] 재사용률 > 60%

---

## 🔄 향후 로드맵

### v1.1 (1개월)
- 실제 코드 실행 에이전트 추가
- Git 통합
- 파일 시스템 접근

### v1.2 (2개월)
- VS Code Extension 개발
- 협업 기능 (멀티 유저)
- 고급 메모리 관리

### v2.0 (3개월)
- 자체 학습 능력
- 커스텀 에이전트 빌더
- 엔터프라이즈 기능

---

## 📚 참고 자료

- [LangGraph 1.0 Documentation](https://docs.langchain.com/langgraph)
- [LangChain 1.0 Documentation](https://docs.langchain.com)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Next.js Documentation](https://nextjs.org/docs)

---

## 🤝 팀 구성 및 역할

- **아키텍트**: 시스템 설계 및 기술 결정
- **백엔드 개발**: LangGraph, FastAPI 구현
- **프론트엔드 개발**: Next.js UI 구현
- **DevOps**: 인프라 및 배포 관리

---

**문서 버전**: 1.0
**최종 수정**: 2024-11-17
**다음 리뷰**: Phase 1 완료 후

---