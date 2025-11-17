# LangGraph 1.0 기반 TODO 관리 에이전트 프로젝트

**프로젝트명**: Octostrator (가칭)  
**버전**: 1.0.0  
**작성일**: 2025-11-17  
**LangGraph 버전**: 1.0  
**LangChain 버전**: 1.0  

---

## 📋 문서 구조

본 프로젝트는 다음과 같이 문서가 구성되어 있습니다:

### 핵심 문서
1. **00_PROJECT_OVERVIEW.md** (본 문서)
   - 프로젝트 개요 및 목표
   - 문서 구조 안내
   - 핵심 개념 요약

2. **01_ARCHITECTURE_DESIGN.md**
   - 전체 시스템 아키텍처
   - 컴포넌트 다이어그램
   - 데이터 플로우

3. **02_STATE_SCHEMA.md**
   - State 설계
   - TypedDict 정의
   - 데이터 모델

4. **03_PHASE1_INTENT_ANALYSIS.md**
   - Phase 1: Intent Analysis Agent
   - 의도 분류 로직
   - 라우팅 전략

5. **04_PHASE2_PLANNING.md**
   - Phase 2: Planning Agent
   - TODO 생성 로직
   - interrupt() 구현

6. **05_PHASE3_SUPERVISOR.md**
   - Phase 3: Supervisor Agent
   - TODO 실행 관리
   - 병렬 처리 전략

7. **06_PHASE4_WORKERS.md**
   - Phase 4: Worker Subgraph
   - Worker 종류별 구현
   - 도구 실행 로직

8. **07_INTERRUPT_SCENARIOS.md**
   - Interrupt 발생 시나리오
   - ESC 중단 처리
   - 승인 프로세스

9. **08_FRONTEND_DESIGN.md**
   - Frontend 설계 (Next.js)
   - 컴포넌트 구조
   - 스트리밍 클라이언트

10. **09_BACKEND_API.md**
    - Backend API 설계 (FastAPI)
    - 엔드포인트 상세
    - 스트리밍 구현

11. **10_IMPLEMENTATION_GUIDE.md**
    - 구현 단계별 가이드
    - 우선순위 매트릭스
    - 기술 스택

---

## 🎯 프로젝트 목표

### 핵심 목표
사용자가 복잡한 작업을 요청하면, AI 에이전트가 자동으로 작업을 **TODO로 분해**하고, **단계별로 실행**하며, 사용자는 **언제든지 중단/수정**할 수 있는 대화형 에이전트 시스템 구축

### 주요 기능
1. ✅ **자동 TODO 생성**: 사용자 쿼리 → AI가 작업 계획 수립
2. ✅ **실시간 TODO 표시**: Frontend에서 진행 상황 실시간 확인
3. ✅ **ESC 중단**: 사용자가 언제든지 작업 중단 및 수정
4. ✅ **Human-in-the-Loop**: 에이전트가 필요 시 사용자 승인 요청
5. ✅ **멀티턴 대화**: 이전 대화 컨텍스트 유지
6. ✅ **영속성**: PostgreSQL Checkpointer로 상태 저장/복구

---

## 🏗️ 시스템 아키텍처 개요

```
┌─────────────────────────────────────────┐
│          Frontend (Next.js)             │
│  - 실시간 TODO 표시                      │
│  - ESC 버튼으로 interrupt 발생           │
│  - SSE로 스트리밍 수신                   │
└─────────────┬───────────────────────────┘
              ↓ HTTP/SSE
┌─────────────────────────────────────────┐
│       FastAPI Backend                   │
│  - /api/stream: 비동기 스트리밍          │
│  - /api/interrupt: 중단 요청             │
│  - /api/resume: 재개 + 수정 반영         │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│       LangGraph Main Graph              │
│                                         │
│  Phase 1: Intent Analysis               │
│  Phase 2: Planning Agent                │
│  Phase 3: Supervisor Agent              │
│  Phase 4: Worker Subgraph               │
│                                         │
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│    AsyncPostgresSaver (Checkpointer)    │
└─────────────────────────────────────────┘
```

---

## 🎨 핵심 설계 철학

### 1. **Interrupt 중심 설계**
모든 사용자 상호작용은 `interrupt()` 함수를 통해 처리합니다.

**사용자 주도 Interrupt**:
- ESC 키로 작업 중단
- 수정 요청

**에이전트 주도 Interrupt**:
- TODO 계획 승인 요청
- 도구 실행 승인 요청
- 사용자 의견 질문

### 2. **TODO는 실시간 추적 상태**
TODO는 단순한 계획이 아닌, **실시간으로 업데이트되는 작업 상태**입니다.

- Planning에서 생성
- Supervisor에서 관리
- Worker에서 실행
- 언제든지 수정 가능

### 3. **멀티턴 대화 지원**
각 쿼리의 의도를 분석하여 적절히 처리합니다.

- 새 작업: TODO 생성
- 기존 작업 수정: TODO 업데이트
- 작업 계속: 실행 재개
- 단순 질문: 즉시 답변

### 4. **Checkpointer로 완전한 복구**
모든 상태는 PostgreSQL에 저장되어 안전합니다.

- 중단 시점 저장
- 재개 시 이어서 실행
- 에러 발생 시 이전 체크포인트로 복구

---

## 🔑 핵심 기술 선택 이유

### LangGraph 1.0 선택 이유
1. **Production Ready**: Uber, LinkedIn 등 대기업 검증
2. **Breaking Changes 없음**: 안정적인 API
3. **Durable Execution**: 체크포인팅으로 내구성 보장
4. **Built-in HITL**: interrupt() 네이티브 지원

### 주요 API 활용
| API | 사용 목적 | 필수/선택 |
|-----|----------|---------|
| **interrupt()** | ESC 중단, 승인 요청 | ✅ 필수 |
| **Command API** | 라우팅, Subgraph 복귀 | ✅ 필수 |
| **Send API** | 병렬 TODO 실행 | ✅ 필수 |
| **Streaming (updates)** | 실시간 TODO 표시 | ✅ 필수 |
| **AsyncPostgresSaver** | 상태 영속성 | ✅ 필수 |
| **Context API** | user_id, session_id | 🔄 권장 |
| **Store API** | 사용자 히스토리 | ⭐ 선택 |

---

## 📊 우선순위 매트릭스

### Phase 1: MVP (필수 기능)
**목표**: 기본적인 TODO 관리 및 interrupt 구현

| 순위 | 기능 | 구현 범위 |
|-----|------|----------|
| 1 | Intent Analysis | 의도 분류 (4가지) |
| 2 | Planning Agent | TODO 생성 + interrupt() |
| 3 | Supervisor Agent | TODO 실행 관리 |
| 4 | 1개 Worker | Research Worker |
| 5 | FastAPI 스트리밍 | /api/stream 엔드포인트 |
| 6 | Frontend 기본 UI | TODO 대시보드 + ESC |
| 7 | Checkpointer | AsyncPostgresSaver |

**예상 기간**: 2-3주

### Phase 2: 확장 (병렬 처리 + 도구)
**목표**: 병렬 실행 및 다양한 Worker 추가

| 순위 | 기능 | 구현 범위 |
|-----|------|----------|
| 8 | Send API | 병렬 TODO 실행 |
| 9 | 추가 Workers | Analysis, Coding, Writing |
| 10 | 도구 승인 | 도구 실행 시 interrupt() |
| 11 | UI 개선 | 모달, 알림, 진행률 바 |

**예상 기간**: 2주

### Phase 3: 고도화 (최적화 + 추가 기능)
**목표**: 성능 최적화 및 사용자 경험 개선

| 순위 | 기능 | 구현 범위 |
|-----|------|----------|
| 12 | Context API | Runtime 마이그레이션 |
| 13 | Middleware | 로깅, 검증 |
| 14 | Store API | 사용자별 히스토리 |
| 15 | Node Caching | 개발 속도 향상 |

**예상 기간**: 1-2주

---

## 🎬 사용자 시나리오 예시

### 시나리오 1: 새 작업 요청
```
[User] "2025년 AI 트렌드 보고서 만들어줘"
  ↓
[System] TODO 3개 생성
  - TODO 1: 데이터 수집 (웹 검색)
  - TODO 2: 데이터 분석
  - TODO 3: 보고서 작성
  ↓
[System] 📍 interrupt() - "이 계획으로 진행할까요?"
  ↓
[User] "승인"
  ↓
[System] TODO 1 실행 시작...
```

### 시나리오 2: 실행 중 ESC 중단
```
[System] TODO 1 실행 중... (진행률 45%)
  ↓
[User] ESC 키 누름
  ↓
[System] 📍 interrupt() - "어떻게 하시겠습니까?"
  - 수정: TODO 변경
  - 계속: 그대로 실행
  - 중단: 종료
  ↓
[User] "수정" 선택
  ↓
[System] TODO 수정 모드로 전환
[User] "한국 시장 분석도 추가해줘"
  ↓
[System] TODO 4 추가됨
  ↓
[User] "승인"
  ↓
[System] TODO 1 계속 실행...
```

### 시나리오 3: 멀티턴 대화
```
[Turn 1]
User: "AI 트렌드 보고서 만들어줘"
System: TODO 생성 → 실행

[Turn 2] (실행 중)
User: "GPT-5는 언제 나와?"
System: 단순 질문 감지 → 즉시 답변 (TODO는 백그라운드 유지)

[Turn 3]
User: "보고서에 그 내용도 넣어줘"
System: 기존 작업 수정 → TODO 업데이트
```

---

## 🛠️ 기술 스택

### Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **LangGraph**: 1.0
- **LangChain**: 1.0
- **Checkpointer**: AsyncPostgresSaver
- **Database**: PostgreSQL 14+
- **LLM**: OpenAI GPT-4 / Anthropic Claude

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Hooks
- **Streaming**: Server-Sent Events (SSE)

### DevOps
- **Container**: Docker
- **Orchestration**: Docker Compose
- **CI/CD**: GitHub Actions (선택)

---

## 📁 프로젝트 구조 (예상)

```
project-root/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── intent_analysis.py
│   │   │   ├── planning.py
│   │   │   ├── supervisor.py
│   │   │   └── workers/
│   │   │       ├── research.py
│   │   │       ├── analysis.py
│   │   │       ├── coding.py
│   │   │       └── writing.py
│   │   ├── graphs/
│   │   │   ├── main_graph.py
│   │   │   └── worker_subgraph.py
│   │   ├── models/
│   │   │   └── state.py
│   │   ├── api/
│   │   │   └── routes.py
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   ├── TodoDashboard.tsx
│   │   │   ├── InterruptModal.tsx
│   │   │   └── StreamingClient.tsx
│   │   ├── page.tsx
│   │   └── layout.tsx
│   ├── package.json
│   └── Dockerfile
│
├── docs/
│   ├── 00_PROJECT_OVERVIEW.md
│   ├── 01_ARCHITECTURE_DESIGN.md
│   ├── 02_STATE_SCHEMA.md
│   ├── ... (나머지 문서들)
│   └── 10_IMPLEMENTATION_GUIDE.md
│
├── docker-compose.yml
└── README.md
```

---

## 🚀 시작하기

### 전제 조건
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Docker & Docker Compose (선택)

### 빠른 시작
1. 문서 읽기 순서:
   - 00_PROJECT_OVERVIEW.md (본 문서)
   - 01_ARCHITECTURE_DESIGN.md
   - 02_STATE_SCHEMA.md
   - 03-06: 각 Phase별 문서
   - 10_IMPLEMENTATION_GUIDE.md

2. 구현 시작:
   - Phase 1부터 순차적으로 구현
   - 각 Phase별 테스트 진행
   - MVP 완성 후 Phase 2, 3 진행

---

## 📚 참고 자료

### 공식 문서
- [LangGraph 1.0 Docs](https://docs.langchain.com/oss/python/langgraph)
- [LangChain 1.0 Docs](https://docs.langchain.com/oss/python/langchain)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)

### 관련 문서
- `LANGGRAPH_NEW_APIS_251116.md`: LangGraph 1.0 API 정리
- `LangGraph_LangChain_New_Features_Report.md`: 종합 보고서

---

## 📝 버전 히스토리

### v1.0.0 (2025-11-17)
- 초기 문서 작성
- 전체 아키텍처 설계
- Phase별 상세 계획 수립

---

## 📧 문의 및 지원

프로젝트 관련 문의사항은 이슈 트래커를 통해 제출해주세요.

---

**다음 문서**: [01_ARCHITECTURE_DESIGN.md](./01_ARCHITECTURE_DESIGN.md)
