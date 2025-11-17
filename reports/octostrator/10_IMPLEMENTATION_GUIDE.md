# 10. 구현 가이드 및 우선순위

**문서 버전**: 1.0.0  
**작성일**: 2025-11-17  
**관련 문서**: 전체 문서 참조

---

## 📋 목차

1. [구현 로드맵](#1-구현-로드맵)
2. [우선순위 매트릭스](#2-우선순위-매트릭스)
3. [Phase별 구현 가이드](#3-phase별-구현-가이드)
4. [기술 스택 상세](#4-기술-스택-상세)
5. [개발 환경 설정](#5-개발-환경-설정)
6. [테스트 전략](#6-테스트-전략)
7. [배포 전략](#7-배포-전략)
8. [모니터링 및 로깅](#8-모니터링-및-로깅)

---

## 1. 구현 로드맵

### 1.1 전체 타임라인

```
Week 1-2: MVP (필수 기능)
  ├─ Backend 기본 구조
  ├─ Intent Analysis
  ├─ Planning Agent
  └─ 1개 Worker

Week 3-4: 확장 (병렬 처리)
  ├─ Supervisor Agent
  ├─ Send API
  ├─ 추가 Workers
  └─ Frontend 고도화

Week 5-6: 고도화 (최적화)
  ├─ Context API
  ├─ Store API
  ├─ Node Caching
  └─ 프로덕션 준비
```

### 1.2 마일스톤

| 주차 | 마일스톤 | 주요 기능 | 완료 기준 |
|-----|---------|---------|----------|
| W1 | MVP Alpha | Intent + Planning + 1 Worker | 단순 TODO 실행 가능 |
| W2 | MVP Beta | Supervisor + Interrupt | ESC 중단 및 수정 가능 |
| W3 | 확장 v1 | 병렬 처리 + 4 Workers | 복잡한 TODO 병렬 실행 |
| W4 | 확장 v2 | Frontend 완성 | 실시간 UI 업데이트 |
| W5 | 최적화 v1 | Context + Store API | 사용자 히스토리 저장 |
| W6 | 프로덕션 | 배포 준비 | 프로덕션 환경 배포 |

---

## 2. 우선순위 매트릭스

### 2.1 LangGraph API 우선순위

| 순위 | API | 사용 목적 | 필수/선택 | 구현 시점 |
|-----|-----|----------|---------|----------|
| 1 | **interrupt()** | ESC 중단, 승인 요청 | ✅ 필수 | W1 |
| 2 | **Command API** | 라우팅, Subgraph 복귀 | ✅ 필수 | W1 |
| 3 | **Streaming (updates)** | 실시간 TODO 표시 | ✅ 필수 | W2 |
| 4 | **AsyncPostgresSaver** | 상태 영속성 | ✅ 필수 | W2 |
| 5 | **Send API** | 병렬 TODO 실행 | ✅ 필수 | W3 |
| 6 | **Context API** | user_id, session_id | 🔄 권장 | W5 |
| 7 | **Middleware** | 로깅, 검증 | 🔄 권장 | W5 |
| 8 | **Store API** | 사용자 히스토리 | ⭐ 선택 | W5 |
| 9 | **Node Caching** | 개발 속도 향상 | ⭐ 선택 | W6 |
| 10 | **Multiple Interrupt** | 병렬 승인 | ⭐ 선택 | W6 |

### 2.2 기능별 우선순위

#### Phase 1: MVP (W1-W2)

| 순위 | 기능 | 설명 | 예상 시간 |
|-----|------|------|----------|
| 1 | **Intent Analysis** | 의도 분류 (4가지) | 2일 |
| 2 | **Planning Agent** | TODO 생성 + interrupt() | 3일 |
| 3 | **Research Worker** | 웹 검색 기본 구현 | 2일 |
| 4 | **FastAPI 기본** | /api/stream 엔드포인트 | 2일 |
| 5 | **Frontend 기본** | TODO 대시보드 | 3일 |
| 6 | **Checkpointer** | AsyncPostgresSaver 연동 | 2일 |

**총 예상**: 14일 (W1-W2)

#### Phase 2: 확장 (W3-W4)

| 순위 | 기능 | 설명 | 예상 시간 |
|-----|------|------|----------|
| 7 | **Supervisor Agent** | TODO 실행 관리 | 3일 |
| 8 | **Send API** | 병렬 처리 구현 | 2일 |
| 9 | **추가 Workers** | Analysis, Coding, Writing | 4일 |
| 10 | **도구 승인** | 도구 실행 시 interrupt() | 2일 |
| 11 | **UI 개선** | 모달, 알림, 진행률 | 3일 |

**총 예상**: 14일 (W3-W4)

#### Phase 3: 고도화 (W5-W6)

| 순위 | 기능 | 설명 | 예상 시간 |
|-----|------|------|----------|
| 12 | **Context API** | Runtime 마이그레이션 | 2일 |
| 13 | **Middleware** | 로깅, 검증 | 2일 |
| 14 | **Store API** | 사용자 히스토리 저장 | 3일 |
| 15 | **Node Caching** | 캐싱 적용 | 2일 |
| 16 | **프로덕션 배포** | Docker, CI/CD | 5일 |

**총 예상**: 14일 (W5-W6)

---

## 3. Phase별 구현 가이드

### 3.1 Phase 1: MVP (W1-W2)

#### W1: Backend 핵심

**Day 1-2: 프로젝트 설정 및 Intent Analysis**
```bash
# 1. 프로젝트 초기화
poetry init
poetry add langgraph langchain langchain-openai fastapi uvicorn

# 2. 디렉토리 구조
backend/
├── app/
│   ├── agents/
│   │   └── intent_analysis.py
│   ├── models/
│   │   └── state.py
│   └── main.py
├── tests/
└── pyproject.toml

# 3. State 정의
# models/state.py 작성

# 4. Intent Analysis Agent 구현
# agents/intent_analysis.py 작성

# 5. 테스트
pytest tests/test_intent_analysis.py
```

**Day 3-5: Planning Agent + interrupt()**
```python
# agents/planning.py 작성

def planning_agent(state: MainState) -> Command:
    # TODO 생성
    proposed_todos = generate_new_todos(state)
    
    # interrupt() 구현
    user_response = interrupt({...})
    
    # 응답 처리
    if user_response["action"] == "approve":
        return Command(update={...}, goto="supervisor_agent")
```

**Day 6-7: Research Worker (기본)**
```python
# agents/workers/research.py 작성

def research_worker(state: WorkerState) -> Command:
    # 웹 검색 도구 실행
    results = web_search(state["current_todo"]["description"])
    
    # 결과 반환
    return Command(
        update={"final_result": results},
        goto="finalize"
    )
```

#### W2: Backend 통합 + Frontend 시작

**Day 1-2: FastAPI 스트리밍**
```python
# api/routes.py

@app.post("/api/stream")
async def stream_agent(request: StreamRequest):
    async def event_generator():
        async for chunk in graph.astream(...):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Day 3-5: Frontend TODO Dashboard**
```typescript
// components/TodoDashboard.tsx

function TodoDashboard({ todos }: Props) {
  return (
    <div>
      {todos.map(todo => (
        <TodoItem key={todo.id} todo={todo} />
      ))}
    </div>
  );
}
```

**Day 6-7: Checkpointer 연동**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(
    "postgresql://..."
)

compiled_graph = graph.compile(checkpointer=checkpointer)
```

---

### 3.2 Phase 2: 확장 (W3-W4)

**핵심 구현**:
1. Supervisor Agent (의존성 + 병렬 처리)
2. Send API 활용
3. 추가 Workers (Analysis, Coding, Writing)
4. Frontend Interrupt Modal

**상세 구현은 각 Phase 문서 참조**

---

### 3.3 Phase 3: 고도화 (W5-W6)

**핵심 구현**:
1. Context API 마이그레이션
2. Store API (Redis/MongoDB)
3. Node Caching
4. 프로덕션 배포

---

## 4. 기술 스택 상세

### 4.1 Backend

| 항목 | 선택 | 버전 | 이유 |
|------|------|------|------|
| **언어** | Python | 3.10+ | LangGraph/LangChain 지원 |
| **프레임워크** | FastAPI | 0.100+ | 비동기, 빠른 개발 |
| **LangGraph** | langgraph | 1.0+ | 최신 안정 버전 |
| **LangChain** | langchain | 1.0+ | LangGraph와 통합 |
| **LLM** | OpenAI GPT-4 | - | 높은 정확도 |
| **Checkpointer** | PostgreSQL | 14+ | 프로덕션 준비 |
| **Store** | Redis | 7+ | 빠른 벡터 검색 |
| **도구** | Tavily, Brave | - | 웹 검색 |

### 4.2 Frontend

| 항목 | 선택 | 버전 | 이유 |
|------|------|------|------|
| **프레임워크** | Next.js | 14+ | React + SSR |
| **언어** | TypeScript | 5+ | 타입 안전성 |
| **스타일링** | Tailwind CSS | 3+ | 빠른 개발 |
| **상태 관리** | React Hooks | - | 간단한 상태 |
| **스트리밍** | SSE | - | 실시간 업데이트 |

### 4.3 DevOps

| 항목 | 선택 | 이유 |
|------|------|------|
| **컨테이너** | Docker | 일관된 환경 |
| **오케스트레이션** | Docker Compose | 로컬 개발 |
| **CI/CD** | GitHub Actions | 자동화 |
| **모니터링** | Prometheus + Grafana | 메트릭 수집 |
| **로깅** | ELK Stack | 로그 분석 |

---

## 5. 개발 환경 설정

### 5.1 Backend 설정

```bash
# 1. Python 환경
pyenv install 3.10
pyenv local 3.10

# 2. Poetry 설치
curl -sSL https://install.python-poetry.org | python3 -

# 3. 프로젝트 초기화
poetry init
poetry add langgraph langchain langchain-openai
poetry add fastapi uvicorn psycopg2-binary redis
poetry add --group dev pytest pytest-asyncio

# 4. 환경 변수
cp .env.example .env
# OPENAI_API_KEY=...
# DATABASE_URL=postgresql://...
# REDIS_URL=redis://...

# 5. 데이터베이스 초기화
docker-compose up -d postgres redis
poetry run python scripts/init_db.py

# 6. 실행
poetry run uvicorn app.main:app --reload
```

### 5.2 Frontend 설정

```bash
# 1. Node.js 환경
nvm install 18
nvm use 18

# 2. 프로젝트 초기화
npx create-next-app@latest frontend --typescript --tailwind --app

# 3. 의존성 설치
cd frontend
npm install

# 4. 환경 변수
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000

# 5. 실행
npm run dev
```

### 5.3 Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: langgraph
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@postgres/langgraph
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000

volumes:
  postgres_data:
  redis_data:
```

---

## 6. 테스트 전략

### 6.1 Backend 테스트

**단위 테스트**:
```python
# tests/test_intent_analysis.py

@pytest.mark.asyncio
async def test_intent_analysis_new_task():
    state = create_test_state(...)
    result = intent_analysis_agent(state)
    
    assert result.update["current_intent"] == "new_task"
    assert result.update["intent_confidence"] > 0.8
```

**통합 테스트**:
```python
# tests/test_graph.py

@pytest.mark.asyncio
async def test_full_graph_execution():
    graph = create_compiled_graph()
    
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="보고서 만들어줘")]},
        config={"configurable": {"thread_id": "test"}}
    )
    
    assert len(result["todos"]) > 0
```

### 6.2 Frontend 테스트

**컴포넌트 테스트**:
```typescript
// __tests__/TodoDashboard.test.tsx

import { render, screen } from '@testing-library/react';
import TodoDashboard from '@/components/TodoDashboard';

test('renders TODO items', () => {
  const todos = [
    { id: '1', title: 'Test TODO', status: 'pending' }
  ];
  
  render(<TodoDashboard todos={todos} />);
  
  expect(screen.getByText('Test TODO')).toBeInTheDocument();
});
```

### 6.3 E2E 테스트

```python
# tests/e2e/test_workflow.py

@pytest.mark.e2e
async def test_complete_workflow():
    # 1. 새 작업 시작
    response = await client.post("/api/stream", json={
        "query": "AI 보고서 만들어줘"
    })
    
    # 2. Interrupt 감지
    assert "__interrupt__" in response.events
    
    # 3. 승인
    await client.post("/api/resume/thread_123", json={
        "action": "approve"
    })
    
    # 4. 완료 확인
    state = await client.get("/api/state/thread_123")
    assert state["conversation_mode"] == "completed"
```

---

## 7. 배포 전략

### 7.1 환경별 설정

| 환경 | 용도 | 배포 방식 |
|------|------|----------|
| **Development** | 로컬 개발 | docker-compose |
| **Staging** | 테스트 | Kubernetes |
| **Production** | 실서비스 | Kubernetes + Load Balancer |

### 7.2 CI/CD 파이프라인

```yaml
# .github/workflows/deploy.yml

name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          poetry install
          poetry run pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker images
        run: |
          docker build -t backend:latest ./backend
          docker build -t frontend:latest ./frontend

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: kubectl apply -f k8s/
```

---

## 8. 모니터링 및 로깅

### 8.1 메트릭 수집

```python
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
todo_created = Counter('todo_created_total', 'Total TODOs created')
todo_completed = Counter('todo_completed_total', 'Total TODOs completed')
interrupt_occurred = Counter('interrupt_occurred_total', 'Total interrupts')
execution_time = Histogram('execution_time_seconds', 'Execution time')
active_todos = Gauge('active_todos', 'Currently active TODOs')

# 사용
@execution_time.time()
async def execute_todo(todo):
    todo_created.inc()
    # ...
    todo_completed.inc()
```

### 8.2 로깅 전략

```python
import logging
import structlog

# Structured logging
logger = structlog.get_logger()

logger.info(
    "todo_execution_started",
    todo_id=todo["id"],
    worker=todo["assigned_worker"],
    user_id=user_id
)
```

### 8.3 대시보드

**Grafana 대시보드**:
- TODO 생성/완료 추세
- Interrupt 발생 빈도
- 실행 시간 분포
- 에러율
- 활성 사용자 수

---

## 9. 체크리스트

### 9.1 MVP 완료 체크리스트

- [ ] Intent Analysis 구현 및 테스트
- [ ] Planning Agent + interrupt() 구현
- [ ] 1개 Worker 구현 (Research)
- [ ] FastAPI 스트리밍 엔드포인트
- [ ] Frontend TODO 대시보드
- [ ] AsyncPostgresSaver 연동
- [ ] ESC 중단 기능
- [ ] 기본 에러 처리

### 9.2 확장 완료 체크리스트

- [ ] Supervisor Agent 구현
- [ ] Send API 병렬 처리
- [ ] 4개 Workers 구현
- [ ] 도구 승인 interrupt()
- [ ] Frontend Interrupt Modal
- [ ] 의존성 그래프 시각화

### 9.3 프로덕션 준비 체크리스트

- [ ] Context API 마이그레이션
- [ ] Store API 구현
- [ ] Node Caching 적용
- [ ] Middleware (로깅, 검증)
- [ ] 단위 테스트 커버리지 80%+
- [ ] E2E 테스트 통과
- [ ] Docker 이미지 빌드
- [ ] CI/CD 파이프라인
- [ ] 모니터링 대시보드
- [ ] 문서화 완료

---

**이전 문서**: [09_BACKEND_API.md](./09_BACKEND_API.md)  
**관련 문서**: 전체 문서 참조
