# LangGraph 1.0 TODO 관리 에이전트 프로젝트

**프로젝트명**: Octostrator (가칭)  
**버전**: 1.0.0  
**작성일**: 2025-11-17  
**기술 스택**: LangGraph 1.0, LangChain 1.0, FastAPI, Next.js  

---

## 📖 프로젝트 개요

사용자가 복잡한 작업을 요청하면, AI 에이전트가 자동으로 작업을 **TODO로 분해**하고, **단계별로 실행**하며, 사용자는 **언제든지 중단/수정**할 수 있는 대화형 에이전트 시스템입니다.

### 🎯 핵심 기능

- ✅ **자동 TODO 생성**: AI가 사용자 쿼리를 분석하여 실행 가능한 작업 계획 수립
- ✅ **실시간 진행 표시**: Frontend에서 TODO 상태를 실시간으로 확인
- ✅ **ESC 중단**: 사용자가 언제든지 작업을 중단하고 수정
- ✅ **Human-in-the-Loop**: 에이전트가 필요 시 사용자 승인 요청
- ✅ **멀티턴 대화**: 이전 대화 컨텍스트 유지
- ✅ **영속성**: PostgreSQL Checkpointer로 상태 저장/복구

---

## 📁 문서 구조

본 프로젝트는 다음과 같은 문서로 구성되어 있습니다:

### 📚 필수 문서 (반드시 읽어야 할 순서)

1. **[00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)**
   - 프로젝트 전체 개요
   - 목표 및 핵심 개념
   - 기술 스택 요약

2. **[01_ARCHITECTURE_DESIGN.md](./01_ARCHITECTURE_DESIGN.md)**
   - 전체 시스템 아키텍처
   - 3-Tier 구조
   - 데이터 플로우

3. **[02_STATE_SCHEMA.md](./02_STATE_SCHEMA.md)**
   - State 설계 원칙
   - Main State & Worker State
   - Reducer 함수

4. **[10_IMPLEMENTATION_GUIDE.md](./10_IMPLEMENTATION_GUIDE.md)**
   - 구현 로드맵 (6주)
   - 우선순위 매트릭스
   - 개발 환경 설정

### 🔧 상세 구현 문서

5. **[03_PHASE1_INTENT_ANALYSIS.md](./03_PHASE1_INTENT_ANALYSIS.md)**
   - Intent Analysis Agent 구현
   - 의도 분류 (4가지)
   - LLM 프롬프트 설계

6. **[04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)**
   - Planning Agent 구현
   - TODO 생성 전략
   - interrupt() 구현

7. **[05_PHASE3_SUPERVISOR.md](./05_PHASE3_SUPERVISOR.md)**
   - Supervisor Agent 구현
   - TODO 실행 관리
   - Send API 병렬 처리

8. **[06_PHASE4_WORKERS.md](./06_PHASE4_WORKERS.md)** (미생성)
   - Worker Subgraph 구현
   - 4개 Worker 종류
   - 도구 실행

9. **[07_INTERRUPT_SCENARIOS.md](./07_INTERRUPT_SCENARIOS.md)** (미생성)
   - Interrupt 시나리오
   - ESC 중단 처리
   - 승인 프로세스

10. **[08_FRONTEND_DESIGN.md](./08_FRONTEND_DESIGN.md)** (미생성)
    - Frontend 설계 (Next.js)
    - 컴포넌트 구조
    - 스트리밍 클라이언트

11. **[09_BACKEND_API.md](./09_BACKEND_API.md)** (미생성)
    - Backend API 설계 (FastAPI)
    - 엔드포인트 상세
    - 스트리밍 구현

---

## 🚀 빠른 시작

### 전제 조건

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+ (선택)
- Docker & Docker Compose (권장)

### 1. 프로젝트 클론

```bash
git clone https://github.com/your-org/octostrator.git
cd octostrator
```

### 2. Backend 설정

```bash
cd backend

# Poetry로 의존성 설치
poetry install

# 환경 변수 설정
cp .env.example .env
# OPENAI_API_KEY=...
# DATABASE_URL=postgresql://...

# 데이터베이스 초기화
docker-compose up -d postgres
poetry run python scripts/init_db.py

# 서버 실행
poetry run uvicorn app.main:app --reload
```

### 3. Frontend 설정

```bash
cd frontend

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000

# 개발 서버 실행
npm run dev
```

### 4. 접속

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🏗️ 시스템 아키텍처

### 전체 구조

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
└─────────────┬───────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│    AsyncPostgresSaver (Checkpointer)    │
└─────────────────────────────────────────┘
```

### LangGraph Flow

```
사용자 쿼리
    ↓
┌────────────────────┐
│ Intent Analysis    │ → 의도 분류 (4가지)
└────────┬───────────┘
         ↓
┌────────────────────┐
│ Planning Agent     │ → TODO 생성
│                    │ → interrupt() 📍 (승인)
└────────┬───────────┘
         ↓
┌────────────────────┐
│ Supervisor Agent   │ → 실행 순서 관리
│                    │ → 병렬/순차 결정
└────────┬───────────┘
         ↓
┌────────────────────┐
│ Worker Subgraph    │ → 실제 작업 수행
│ (4 Workers)        │ → 도구 실행
└────────────────────┘
```

---

## 📊 기술 스택

### Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **LangGraph**: 1.0
- **LangChain**: 1.0
- **Checkpointer**: AsyncPostgresSaver (PostgreSQL)
- **Store**: RedisStore (선택)
- **LLM**: OpenAI GPT-4 / Anthropic Claude

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: React Hooks
- **Streaming**: Server-Sent Events (SSE)

### DevOps
- **Container**: Docker
- **Orchestration**: Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

---

## 🎯 핵심 LangGraph API

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

## 📖 사용 예시

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
```

---

## 🛠️ 개발 가이드

### 구현 순서

1. **Week 1-2: MVP (필수 기능)**
   - Intent Analysis
   - Planning Agent + interrupt()
   - 1개 Worker (Research)
   - FastAPI 스트리밍
   - Frontend 기본 UI

2. **Week 3-4: 확장 (병렬 처리)**
   - Supervisor Agent
   - Send API
   - 추가 Workers (Analysis, Coding, Writing)
   - UI 개선

3. **Week 5-6: 고도화 (최적화)**
   - Context API
   - Store API
   - Node Caching
   - 프로덕션 배포

### 테스트 실행

```bash
# Backend 테스트
cd backend
poetry run pytest

# Frontend 테스트
cd frontend
npm test

# E2E 테스트
poetry run pytest tests/e2e/
```

---

## 📚 참고 자료

### 공식 문서
- [LangGraph 1.0 Docs](https://docs.langchain.com/oss/python/langgraph)
- [LangChain 1.0 Docs](https://docs.langchain.com/oss/python/langchain)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)

### 프로젝트 문서
- [LangGraph 신규 API 정리](./LANGGRAPH_NEW_APIS_251116.md)
- [LangGraph/LangChain 종합 보고서](./LangGraph_LangChain_New_Features_Report.md)

---

## 🤝 기여 가이드

### 이슈 생성
- 버그 리포트
- 기능 요청
- 문서 개선

### Pull Request
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 버전 히스토리

### v1.0.0 (2025-11-17)
- 초기 문서 작성
- 전체 아키텍처 설계
- Phase별 상세 계획 수립

---

## 📧 문의

- 이슈 트래커: https://github.com/your-org/octostrator/issues
- 이메일: contact@example.com

---

## 📄 라이선스

MIT License

---

**시작하기**: [00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)를 먼저 읽어보세요!
