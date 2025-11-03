# 설정 가이드

## 환경 변수 (.env)

```bash
# OpenAI API
OPENAI_API_KEY=your_key_here

# PostgreSQL (Phase 5에서 사용)
POSTGRES_URL=postgresql://user:password@localhost:5432/octo_chatbot

# System
SYSTEM_DEBUG=False
SYSTEM_API_HOST=0.0.0.0
SYSTEM_API_PORT=8000

# CORS
SYSTEM_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## SystemConfig

**위치**: `backend/app/config/system.py`

```python
from backend.app.config.system import config

# 사용
config.openai_api_key
config.system_api_port
```

## 의존성 (pyproject.toml)

### 핵심 패키지
- **LangChain**: 1.0.3
- **LangGraph**: 1.0.2
- **LangChain OpenAI**: 1.0.1
- **FastAPI**: 0.115.0

### 버전 관리
```toml
[project]
dependencies = [
    "langchain==1.0.3",
    "langgraph==1.0.2",
    "pydantic>=2.9.0,<3.0.0",  # 범위 지정
]
```

## LLM 설정

**현재**: `gpt-4o-mini` (temperature=0.7)

변경 방법:
```python
# octostrator/supervisor/graph.py
llm = ChatOpenAI(
    model="gpt-4o",  # 변경
    temperature=0.5,  # 변경
    api_key=config.openai_api_key
)
```
