# 아키텍처

## Octostrator 시스템

**개념**: Octopus (문어) + Orchestrator
여러 에이전트를 동시에 제어하는 중앙 집중식 시스템

## 폴더별 역할

### `octostrator/states/`
노드 간 전달되는 **변경 가능한** 상태
- 예: `messages`, `next`, `intermediate_results`
- Checkpoint에 저장됨

### `octostrator/supervisor/`
메인 오케스트레이터
- `graph.py`: Graph 생성
- `nodes.py`: 노드 함수 (향후 분리)
- `prompts.py`: 프롬프트 템플릿 (Phase 2)

### `octostrator/contexts/` (Phase 1.5)
런타임 **불변** 정보
- 예: `user_id`, `session_id`, `db_conn`
- Checkpoint에 저장 안 됨

### `octostrator/agents/` (Phase 2+)
전문 Worker 에이전트
- `search/`: 웹 검색
- `rag/`: 문서 검색
- `base/`: 일반 대화

### `octostrator/sub_agents/` (Phase 7)
공유 하위 에이전트 (평면 구조)
- 모든 에이전트가 사용 가능

### `octostrator/tools/` (Phase 2+)
공유 툴 (평면 구조)
- 모든 에이전트가 사용 가능

## 데이터 흐름

```
User Request
    ↓
FastAPI (/chat)
    ↓
Supervisor Graph
    ↓
supervisor_node (LLM 호출)
    ↓
Response
```

**Phase 2 이후**:
```
User Request → Supervisor → 라우팅 결정
                    ↓
        ┌───────────┼───────────┐
    Search      RAG          Base
        └───────────┼───────────┘
                    ↓
                Response
```

## LangGraph 1.0 핵심

### State 정의
```python
class SupervisorState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
```
- `add_messages`: LangGraph가 자동으로 메시지 누적

### Graph 생성
```python
workflow = StateGraph(SupervisorState)
workflow.add_node("node_name", node_function)
workflow.set_entry_point("node_name")
workflow.add_edge("node_name", END)
graph = workflow.compile()
```

### 실행
```python
result = await graph.ainvoke({"messages": [...]})
```
