# API 레퍼런스

## 엔드포인트

### `GET /`
루트 엔드포인트
```json
{"message": "LangGraph Chatbot API", "version": "0.2.0", "status": "running"}
```

### `GET /health`
헬스 체크
```json
{"status": "healthy"}
```

### `POST /chat`
채팅 요청

**Request**:
```json
{
  "message": "안녕하세요"
}
```

**Response**:
```json
{
  "response": "안녕하세요! 무엇을 도와드릴까요?"
}
```

## Python 사용

```python
from backend.app.octostrator.supervisor import build_supervisor_graph
from langchain_core.messages import HumanMessage

graph = build_supervisor_graph()
result = await graph.ainvoke({
    "messages": [HumanMessage(content="Hello")]
})
print(result["messages"][-1].content)
```
