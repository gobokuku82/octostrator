# Octostrator 매뉴얼

**버전**: 0.2.0 (Phase 1 완료)
**LangGraph**: 1.0.2 | **LangChain**: 1.0.3

---

## 빠른 시작

### 설치 및 실행
```bash
# 의존성 설치
uv sync

# 환경 변수 설정 (.env 파일에 OPENAI_API_KEY 추가)
cp .env.example .env

# 서버 실행
uv run uvicorn backend.app.main:app --reload

# 테스트
uv run pytest tests/ -v
```

### API 사용
```bash
# 채팅
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
```

---

## 프로젝트 구조

```
backend/app/
├── config/system.py          # 환경 변수 관리 (SystemConfig)
├── main.py                   # FastAPI 엔트리포인트
└── octostrator/              # 🐙 메인 시스템
    ├── states/               # State 관리 (변경 가능)
    ├── supervisor/           # Supervisor 에이전트
    ├── contexts/             # Context 관리 (불변) - Phase 1.5
    ├── agents/               # Worker 에이전트 - Phase 2+
    ├── sub_agents/           # 공유 하위 에이전트 - Phase 7
    └── tools/                # 공유 툴 - Phase 2+
```

---

## 핵심 개념

### State vs Context
| 항목 | State | Context |
|------|-------|---------|
| 변경 | ✅ 가능 | ❌ 불변 |
| 저장 | Checkpoint | 저장 안 됨 |
| 용도 | messages, 중간 결과 | user_id, db_conn |

### Supervisor Graph
- **목적**: 사용자 요청 처리 (현재: 직접 LLM 호출)
- **위치**: `octostrator/supervisor/graph.py`
- **실행**: `build_supervisor_graph()` → `ainvoke({"messages": [...]})`

---

## 현재 구현 (Phase 1)

### 1. SupervisorState
```python
# octostrator/states/supervisor_state.py
class SupervisorState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

### 2. Supervisor Graph
```python
# octostrator/supervisor/graph.py
def build_supervisor_graph():
    workflow = StateGraph(SupervisorState)
    workflow.add_node("supervisor", supervisor_node)  # LLM 호출
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", END)
    return workflow.compile()
```

### 3. FastAPI
```python
# main.py
@app.post("/chat")
async def chat(request: ChatRequest):
    result = await supervisor_graph.ainvoke({
        "messages": [HumanMessage(content=request.message)]
    })
    return {"response": result["messages"][-1].content}
```

---

## 다음 단계

**Phase 1.5**: Context 도입 (user_id, session_id)
**Phase 2**: Search Agent 추가 (조건부 라우팅)
**Phase 5**: Checkpointer (대화 히스토리 저장)

---

## 참고

- [STRUCTURE.md](../STRUCTURE.md) - 상세 구조
- [Context 보고서](../reports/context_management/langgraph_context_analysis.md)
- [구현 계획](../reports/base_agent/implementation_plan_251103.md)
