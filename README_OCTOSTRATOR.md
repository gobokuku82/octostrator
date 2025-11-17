# 🚀 Octostrator - LangGraph 1.0 기반 코딩 어시스턴트

## 📋 프로젝트 개요

Octostrator는 LangGraph 1.0을 활용한 지능형 코딩 어시스턴트로, TODO 자동 관리, HITL(Human-in-the-Loop), 그리고 멀티 에이전트 시스템을 제공합니다.

### 핵심 기능
- 🎯 **자동 TODO 관리**: 사용자 요청을 TODO로 변환 및 관리
- 🔄 **HITL 메커니즘**: ESC 개입 + interrupt() 기능
- 🌐 **멀티 에이전트**: Supervisor-Swarm 아키텍처
- 💾 **듀얼 메모리**: Short-term (PostgreSQL) + Long-term (Redis)
- ⚡ **실시간 통신**: WebSocket 기반 스트리밍

## 🛠️ 기술 스택

- **Python**: 3.12.7
- **LangGraph**: 1.0.2
- **FastAPI**: 0.115.0
- **PostgreSQL**: 15+ (AsyncPostgreSaver)
- **Redis**: 7+
- **Package Manager**: UV

## 📁 프로젝트 구조

```
octostrator/
├── backend/
│   ├── app/
│   │   ├── octostrator/      # 핵심 에이전트 시스템
│   │   │   ├── agents/        # 에이전트 정의
│   │   │   ├── graphs/        # LangGraph 그래프
│   │   │   ├── tools/         # 에이전트 도구
│   │   │   ├── managers/      # 관리자 클래스
│   │   │   └── services/      # 내부 서비스
│   │   ├── api/              # API 엔드포인트
│   │   └── main.py           # FastAPI 앱
│   ├── core/                 # 핵심 설정
│   ├── db/                   # 데이터베이스
│   └── schema/               # Pydantic 스키마
├── frontend/                 # Next.js (추후 구현)
├── data/                     # Mock 데이터
├── scripts/                  # 유틸리티 스크립트
└── docker-compose.yml        # Docker 설정
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 OPENAI_API_KEY 추가
```

### 2. Docker 실행

```bash
# PostgreSQL과 Redis 실행
docker-compose up -d

# 데이터베이스 초기화
docker exec -i octostrator_postgres psql -U octostrator -d octostrator < scripts/init_db.sql
```

### 3. Python 환경 설정

```bash
# UV 사용
uv venv
uv pip sync

# 또는 pip 사용
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 애플리케이션 실행

```bash
# Backend 실행
uv run python -m backend.app.main

# 또는
python -m backend.app.main
```

### 5. 테스트

```bash
# 기본 테스트
uv run python scripts/init_app.py

# API 테스트 (다른 터미널)
curl http://localhost:8000/health

# Chat API 테스트
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "API 엔드포인트 3개를 구현해주세요"}'
```

## 📡 API 엔드포인트

### REST API

- `GET /health` - 헬스 체크
- `POST /api/v1/chat` - 채팅 메시지 처리
- `GET /api/v1/todos` - TODO 목록 조회
- `POST /api/v1/todos` - TODO 생성
- `PUT /api/v1/todos/{todo_id}` - TODO 수정
- `DELETE /api/v1/todos/{todo_id}` - TODO 삭제
- `POST /api/v1/sessions` - 세션 생성

### WebSocket

- `WS /ws/{session_id}` - 실시간 통신

## 🔧 개발 가이드

### 그래프 상태 구조

```python
class MainGraphState:
    messages: List[BaseMessage]      # 대화 히스토리
    todos: List[TodoItem]            # TODO 목록
    detected_intent: IntentInfo      # 감지된 의도
    requires_confirmation: bool      # 사용자 확인 필요
    execution_results: Dict          # 실행 결과
```

### 에이전트 추가

```python
# backend/app/octostrator/agents/executors/custom_agent.py
class CustomExecutorAgent:
    async def execute(self, todo: TodoItem, state: GraphState):
        # 실행 로직 구현
        return {"status": "success", "result": ...}
```

### HITL 구현

```python
# interrupt() 사용
user_response = interrupt({
    "type": "confirmation",
    "message": "계속 진행할까요?",
    "actions": ["yes", "no"]
})
```

## 🐛 문제 해결

### PostgreSQL 연결 오류
```bash
# PostgreSQL 상태 확인
docker ps
docker logs octostrator_postgres

# 재시작
docker-compose restart postgres
```

### Redis 연결 오류
```bash
# Redis 상태 확인
docker exec octostrator_redis redis-cli ping

# 재시작
docker-compose restart redis
```

### OpenAI API 오류
- `.env` 파일에 `OPENAI_API_KEY` 확인
- API 키 유효성 확인

## 📊 현재 구현 상태

### ✅ Phase 1: Core Architecture
- [x] 프로젝트 구조 생성
- [x] Docker Compose 설정
- [x] LangGraph Core 구현
- [x] 기본 에이전트 체인

### 🚧 Phase 2: TODO Management (진행 예정)
- [ ] TODO CRUD 완성
- [ ] 의존성 관리
- [ ] 자연어 수정

### 🔄 Phase 3: HITL (진행 예정)
- [ ] ESC 개입 완성
- [ ] interrupt() 구현
- [ ] Resume 로직

### 📝 Phase 4: Mock Agents (진행 예정)
- [ ] Search Agent
- [ ] Analysis Agent
- [ ] Document Agent
- [ ] API Agent

## 📚 참고 자료

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Project Implementation Plan](reports/octostrator/Octostrator_Implementation_Plan_v1.0.md)
- [Final Implementation Report](reports/octostrator/Octostrator_Final_Implementation_Report.md)

## 🤝 기여 방법

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 라이센스

MIT License

## 👨‍💻 개발자

- Claude AI Assistant & Human Developer

---

**Last Updated**: 2024-11-17
**Version**: 1.0.0-alpha