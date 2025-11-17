# 🚀 Docker 없이 Octostrator 실행하기

## 📋 개발 환경 설정 (Docker 없음)

### 1. 환경 변수 설정

```bash
# 개발용 환경 파일 사용
cp .env.dev .env

# .env 파일 편집하여 OpenAI API 키 추가
# OPENAI_API_KEY=your_actual_api_key_here
```

### 2. Python 패키지 설치

```bash
# UV 사용 (권장)
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

### 3. 애플리케이션 실행

```bash
# 개발 모드로 실행 (SQLite + In-Memory Store 사용)
uv run python -m backend.app.main

# 또는 uvicorn으로 직접 실행
uv run uvicorn backend.app.main:app --reload --port 8000

# pip을 사용하는 경우
python -m backend.app.main
```

### 4. 테스트

```bash
# 기본 테스트 실행
uv run python scripts/init_app.py

# Health Check
curl http://localhost:8000/health

# Chat API 테스트
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "테스트 작업을 만들어주세요"}'
```

## 🔧 개발 모드 특징

### SQLite 사용
- PostgreSQL 대신 SQLite 사용
- 파일: `octostrator.db` (자동 생성)
- Checkpoints: `octostrator_checkpoints.db` (자동 생성)

### In-Memory Store
- Redis 대신 메모리 기반 스토어 사용
- 재시작 시 데이터 초기화됨
- 개발/테스트용으로만 권장

### 개발 환경 변수
```bash
USE_DEV_MODE=true         # 개발 모드 활성화
APP_DEBUG=true           # 디버그 모드
LOG_LEVEL=DEBUG         # 디버그 로깅
```

## 📡 API 접속

- **API 문서**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **WebSocket Test**: `ws://localhost:8000/ws/test_session`

## 🧪 WebSocket 테스트 (JavaScript Console)

```javascript
// 브라우저 콘솔에서 실행
const ws = new WebSocket('ws://localhost:8000/ws/test_session');

ws.onopen = () => {
    console.log('Connected');
    ws.send(JSON.stringify({
        type: 'query',
        content: '데이터 분석 작업을 만들어주세요'
    }));
};

ws.onmessage = (event) => {
    console.log('Message:', JSON.parse(event.data));
};
```

## 🐛 문제 해결

### 포트 충돌
```bash
# 8000 포트가 사용 중인 경우
uv run uvicorn backend.app.main:app --reload --port 8001
```

### SQLite 권한 오류
```bash
# Windows에서 SQLite 파일 삭제
del octostrator.db
del octostrator_checkpoints.db

# Linux/Mac에서 SQLite 파일 삭제
rm octostrator.db
rm octostrator_checkpoints.db
```

### 패키지 누락
```bash
# 필수 패키지 수동 설치
uv pip install langgraph langchain langchain-openai
uv pip install fastapi uvicorn websockets
uv pip install aiosqlite
```

## 📝 개발 팁

### 1. 로그 확인
```python
# backend/app/main.py에서 로그 레벨 조정
from loguru import logger
logger.add("debug.log", rotation="10 MB", level="DEBUG")
```

### 2. 데이터베이스 초기화
```bash
# SQLite 데이터베이스 파일 삭제
rm *.db

# 앱 재시작하면 자동으로 새로 생성됨
```

### 3. Mock 데이터로 테스트
```python
# scripts/test_mock.py 생성
import asyncio
from backend.app.octostrator.graphs import MainGraph

async def test():
    graph = MainGraph()
    await graph.initialize()

    # 테스트 실행
    result = await graph.invoke({
        "messages": [HumanMessage(content="테스트")],
        "session_id": "test",
        "thread_id": "test"
    })

    print(result)

asyncio.run(test())
```

## ✅ 체크리스트

- [ ] Python 3.12.7 설치됨
- [ ] UV 또는 pip 설치됨
- [ ] .env 파일에 OpenAI API 키 설정됨
- [ ] `uv sync` 또는 `pip install` 완료
- [ ] `python -m backend.app.main` 실행 성공
- [ ] http://localhost:8000/health 접속 성공

## 🚦 빠른 실행 (One-liner)

```bash
# UV 사용
cp .env.dev .env && uv sync && uv run python -m backend.app.main

# Pip 사용
cp .env.dev .env && pip install -r requirements.txt && python -m backend.app.main
```

---

**Docker 없이도 간단하게 개발 환경을 구성할 수 있습니다!** 🎉