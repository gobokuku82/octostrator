# 빠른 참조

## 주요 Import

```python
# Supervisor
from backend.app.octostrator.supervisor import build_supervisor_graph

# State
from backend.app.octostrator.states.supervisor_state import SupervisorState

# Config
from backend.app.config.system import config

# Messages
from langchain_core.messages import HumanMessage, AIMessage
```

## 주요 명령어

```bash
# 의존성 설치
uv sync

# 서버 실행
uv run uvicorn backend.app.main:app --reload

# 테스트
uv run pytest tests/ -v
uv run pytest tests/test_supervisor_graph.py -v

# 특정 테스트
uv run pytest tests/test_api.py::test_chat_endpoint -v
```

## 파일 위치

| 항목 | 경로 |
|------|------|
| 환경 변수 | `.env` |
| 설정 | `backend/app/config/system.py` |
| State | `octostrator/states/supervisor_state.py` |
| Graph | `octostrator/supervisor/graph.py` |
| API | `backend/app/main.py` |
| 테스트 | `tests/` |

## 주요 함수

### build_supervisor_graph()
```python
graph = build_supervisor_graph()
result = await graph.ainvoke({"messages": [HumanMessage(content="Hi")]})
```

### FastAPI 엔드포인트
```python
@app.post("/chat")
async def chat(request: ChatRequest):
    result = await supervisor_graph.ainvoke({...})
    return {"response": result["messages"][-1].content}
```

## 디버깅

### 로그 확인
```python
# loguru 사용 (설치됨)
from loguru import logger
logger.info("Debug message")
```

### Graph 구조 확인
```python
graph = build_supervisor_graph()
print(graph.get_graph().nodes())
print(graph.get_graph().edges())
```

## Phase별 구현 상태

- ✅ **Phase 0**: 환경 설정
- ✅ **Phase 1**: Supervisor 기본 구조
- ⏸️ **Phase 1.5**: Context 도입
- ⏸️ **Phase 2**: Search Agent
- ⏸️ **Phase 5**: Checkpointer
- ⏸️ **Phase 6**: 나머지 Agent
- ⏸️ **Phase 7**: Sub-Agent
