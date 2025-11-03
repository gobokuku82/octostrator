# LangGraph Command API 사용법 조사 및 코드 분석
**작성일**: 2025-10-26
**버전**: LangGraph 0.6.x
**목적**: HITL (Human-in-the-Loop) resume 기능 구현 검증

---

## 1. 공식 문서 조사 결과

### 1.1 Command API 개요

LangGraph의 **`Command`** 프리미티브는 interrupt된 워크플로우를 재개할 때 사용자 입력을 전달하는 공식 방법입니다.

**출처**:
- https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/
- https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/add-human-in-the-loop/

### 1.2 기본 사용 패턴

#### **Node에서 interrupt() 호출**
```python
from langgraph.types import interrupt

def aggregate_node(state):
    # 작업 수행
    aggregated_content = aggregate_results(state["search_results"])

    # ⏸️ Interrupt - 사용자 입력 대기
    user_feedback = interrupt({
        "content": aggregated_content,
        "message": "Please review and approve"
    })

    # 🔄 여기서 재개됨 - user_feedback에 사용자 입력 포함
    if user_feedback.get("action") == "approve":
        return {"final_content": aggregated_content}
```

#### **Resume with Command - Synchronous**
```python
from langgraph.types import Command

# 첫 실행 - interrupt까지 진행
config = {"configurable": {"thread_id": "123"}}
result = graph.invoke(initial_input, config=config)

# 재개 - Command로 사용자 입력 전달
result = graph.invoke(
    Command(resume="user_response_here"),  # ✅ 첫 번째 positional parameter
    config=config
)
```

#### **Resume with Command - Asynchronous**
```python
# 첫 실행
config = {"configurable": {"thread_id": "123"}}
result = await graph.ainvoke(initial_input, config=config)

# 재개
result = await graph.ainvoke(
    Command(resume=user_feedback_dict),  # ✅ 첫 번째 positional parameter
    config=config
)
```

### 1.3 공식 문서의 핵심 포인트

#### ✅ **Command는 첫 번째 positional parameter**
공식 문서의 모든 예제:
```python
graph.invoke(Command(resume="Edited text"), config=config)
graph.invoke(Command(resume=True), config=thread_config)
graph.stream(Command(resume={"type": "accept"}), config)
```

#### ✅ **Checkpointer 필수**
```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# In-memory checkpointer
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# PostgreSQL checkpointer (production)
async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
```

#### ✅ **Thread ID로 세션 추적**
```python
config = {
    "configurable": {
        "thread_id": "unique_session_id"
    }
}
```

#### ⚠️ **Node 재시작 동작**
> "When you resume execution after an interrupt, graph execution **starts from the beginning of the graph node** where the last interrupt was triggered."

즉, resume 시 노드의 처음부터 다시 실행되지만, **interrupt()를 만나면** 이전에 저장된 resume 값을 반환하고 계속 진행합니다.

#### ⚠️ **Multiple Interrupts 주의사항**
> "When a node contains multiple interrupt calls, LangGraph keeps a list of resume values, and whenever execution resumes, matching is **strictly index-based**"

같은 노드에 여러 interrupt가 있으면 순서가 중요합니다.

---

## 2. 현재 코드 분석

### 2.1 Interrupt 구현 (aggregate.py)

**파일**: `backend/app/service_agent/teams/document_team/aggregate.py`

```python
def aggregate_node(state: MainSupervisorState) -> Dict[str, Any]:
    search_results = state.get("search_results", [])
    aggregated_content = aggregate_results(search_results)

    # Prepare interrupt value
    interrupt_value = {
        "aggregated_content": aggregated_content,
        "search_results_count": len(search_results),
        "message": "Please review the aggregated content...",
        "options": {...},
        "_metadata": {
            "interrupted_by": "aggregate",
            "interrupt_type": "approval"
        }
    }

    # Update state
    state["aggregated_content"] = aggregated_content
    state["workflow_status"] = "interrupted"

    # ✅ LangGraph 0.6 Official Pattern
    user_feedback = interrupt(interrupt_value)

    # 🔄 Execution resumes here
    logger.info("▶️  Workflow resumed with user feedback")
    logger.info(f"User feedback: {user_feedback}")

    # Process user feedback
    if user_feedback and user_feedback.get("action") == "modify":
        modified_content = apply_user_feedback(aggregated_content, user_feedback)
        aggregated_content = modified_content

    return {
        "aggregated_content": aggregated_content,
        "collaboration_result": user_feedback,
        "workflow_status": "running"
    }
```

**분석**:
- ✅ `interrupt()` 함수 사용 (올바름)
- ✅ interrupt 값에 메타데이터 포함
- ✅ resume 후 user_feedback 처리
- ✅ 단일 interrupt만 사용 (index 문제 없음)

### 2.2 Resume 구현 (chat_api.py) - 수정 전

**파일**: `backend/app/api/chat_api.py`

```python
# ❌ 잘못된 구현 (수정 전)
result = await supervisor.app.ainvoke(
    None,  # ❌ 첫 번째 parameter가 None
    config=config,
    command=Command(resume=user_feedback)  # ❌ keyword argument로 전달
)
```

**문제점**:
1. `Command`를 keyword argument (`command=`)로 전달
2. 첫 번째 parameter에 `None` 전달
3. 공식 문서의 패턴과 불일치

**증상**:
- aggregate_node가 두 번 실행됨 (로그 확인됨)
- "▶️ Workflow resumed with user feedback" 로그 출력 안됨
- `user_feedback`가 interrupt()로 전달되지 않음

### 2.3 Resume 구현 (chat_api.py) - 수정 후

```python
# ✅ 올바른 구현 (수정 후)
from langgraph.types import Command

result = await supervisor.app.ainvoke(
    Command(resume=user_feedback),  # ✅ 첫 번째 positional parameter
    config=config
)
```

**개선점**:
1. ✅ `Command`를 첫 번째 positional parameter로 전달
2. ✅ 공식 문서 패턴과 일치
3. ✅ resume 값이 interrupt()로 정상 전달될 것으로 예상

### 2.4 Workflow 구조 (workflow.py)

**파일**: `backend/app/service_agent/teams/document_team/workflow.py`

```python
def build_document_workflow(checkpointer: AsyncPostgresSaver) -> Any:
    workflow = StateGraph(MainSupervisorState)

    # Add nodes
    workflow.add_node("planning", planning_node)
    workflow.add_node("search", search_node)
    workflow.add_node("aggregate", aggregate_node)  # Contains interrupt()
    workflow.add_node("generate", generate_node)

    # Define edges
    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "search")
    workflow.add_edge("search", "aggregate")
    workflow.add_edge("aggregate", "generate")  # ✅ Resume 후 generate로 진행
    workflow.add_edge("generate", END)

    # Compile with checkpointer
    compiled = workflow.compile(checkpointer=checkpointer)
    return compiled
```

**분석**:
- ✅ Checkpointer 전달됨
- ✅ Linear flow: planning → search → aggregate → generate → END
- ✅ aggregate 이후 generate로 edge 연결됨
- ⚠️ Resume 시 aggregate 노드 처음부터 재실행 예상 (공식 문서 동작)

---

## 3. 예상 동작 흐름

### 3.1 첫 실행 (Interrupt까지)

```
1. User: "임대차 계약서 작성해줘"
2. Graph: planning_node → search_node → aggregate_node
3. aggregate_node:
   - aggregated_content 생성
   - interrupt(interrupt_value) 호출 ⏸️
   - **여기서 멈춤**
4. Backend: get_state()로 interrupt 감지
5. Frontend: workflow_interrupted 메시지 수신
6. User: lease_contract_page 표시됨
```

### 3.2 Resume 실행 (승인 버튼)

```
1. User: "승인" 버튼 클릭
2. Frontend: interrupt_response 전송
   {
     "type": "interrupt_response",
     "action": "approve",
     "feedback": null
   }
3. Backend: _resume_workflow_async() 실행
4. ainvoke(Command(resume=user_feedback), config)
5. Graph: aggregate_node 재시작 🔄
   - 노드 처음부터 재실행
   - aggregated_content 재생성
   - interrupt(interrupt_value) 도달
   - ✅ 이번엔 resume 값 반환: user_feedback = {"action": "approve", ...}
   - "▶️ Workflow resumed" 로그 출력
   - user_feedback 처리 (action != "modify"이므로 skip)
   - return {...}
6. Graph: aggregate → generate edge 따라 generate_node 실행
7. generate_node:
   - collaboration_result에서 user_feedback 확인
   - 최종 문서 생성
   - return {"final_document": ..., "workflow_status": "completed"}
8. Graph: generate → END
9. Backend: final_response 전송
10. Frontend: 최종 응답 표시
```

### 3.3 Resume 실행 (수정 버튼)

```
1. User: "수정" 버튼 클릭 → Textarea 입력 → "수정 제출"
2. Frontend: interrupt_response 전송
   {
     "type": "interrupt_response",
     "action": "modify",
     "feedback": "임대료를 월 100만원으로 조정해주세요",
     "modifications": "임대료를 월 100만원으로 조정해주세요"
   }
3. Backend: _resume_workflow_async() 실행
4. ainvoke(Command(resume=user_feedback), config)
5. Graph: aggregate_node 재시작
   - interrupt() 도달
   - user_feedback = {"action": "modify", "modifications": "..."}
   - ✅ action == "modify" → apply_user_feedback() 호출
   - aggregated_content에 수정사항 추가
   - return {"aggregated_content": modified_content, ...}
6. Graph: generate_node 실행
   - 수정된 aggregated_content 사용
   - collaboration_result.action == "modify" 확인
   - 최종 문서에 수정사항 반영
7. 완료
```

---

## 4. 현재 구현의 잠재적 문제점

### 4.1 Node 재실행 이슈

**공식 문서**:
> "Graph execution starts from the **beginning of the graph node** where the last interrupt was triggered."

**영향**:
- `aggregate_node`가 처음부터 다시 실행됨
- `aggregate_results(search_results)` 재호출됨
- 로그에서 "📊 Aggregate node: Consolidating search results" 두 번 출력될 것

**해결**:
- ✅ 현재 구현은 idempotent (같은 입력 → 같은 출력)
- ✅ 추가 비용 발생하지만 기능상 문제 없음
- ⚠️ 나중에 최적화 필요시 state에 캐시 추가 고려

### 4.2 final_response None 이슈

**증상** (로그 확인):
```
ERROR: 'NoneType' object has no attribute 'get'
File "chat_api.py", line 844
    final_response.get("answer") or
```

**원인**:
- Resume 후 `result`에 `final_response` 키가 없음
- Document Team 워크플로우가 `final_response`를 생성하지 않음

**해결책 (이미 적용됨)**:
```python
final_response = result.get("final_response") if result else None

if final_response is None:
    logger.warning(f"Workflow resumed but final_response is None")
    final_response = {}

response_content = (
    final_response.get("answer", "") or
    final_response.get("content", "") or
    final_response.get("message", "") or
    ""
)
```

**근본 원인**:
- Document Team은 subgraph이므로 `final_document`를 반환하지만
- Parent graph (TeamSupervisor)가 `final_response`를 생성해야 함
- Resume 시 parent graph가 아닌 subgraph만 실행되어 `final_response` 없음

### 4.3 올바른 Response 생성 방법

**Option A**: Document Team에서 final_response 생성
```python
# generate_node에서
return {
    "final_document": final_document,
    "final_response": {
        "answer": final_document,
        "document_type": planning_result.get("document_type"),
        "collaboration_result": collaboration_result
    },
    "workflow_status": "completed"
}
```

**Option B**: Parent graph에서 후처리
```python
# team_supervisor.py - generate_response_node에서
if state.get("final_document"):
    return {
        "final_response": {
            "answer": state["final_document"],
            "type": "document",
            "metadata": {...}
        }
    }
```

**권장**: Option A (Document Team이 자체 응답 생성)

---

## 5. 테스트 체크리스트

### 5.1 기본 기능

- [ ] Interrupt 발생 확인
  - [ ] Backend 로그: "⏸️ Requesting human approval via interrupt()"
  - [ ] Frontend: lease_contract_page 표시
  - [ ] interrupt_data 올바르게 전달됨

### 5.2 승인 (Approve)

- [ ] "승인" 버튼 클릭
  - [ ] Backend 로그: "📥 Interrupt response received: approve"
  - [ ] Backend 로그: "🔄 Resuming workflow for session..."
  - [ ] **Backend 로그: "▶️ Workflow resumed with user feedback"** ← 핵심!
  - [ ] Backend 로그: "User feedback: {'action': 'approve', ...}"
  - [ ] Backend 로그: "📝 Generate node: Creating final document"
  - [ ] Frontend: final_response 수신
  - [ ] 최종 문서 표시

### 5.3 수정 (Modify)

- [ ] "수정" 버튼 클릭 → Textarea 표시
- [ ] 수정사항 입력 → "수정 제출" 클릭
  - [ ] Backend 로그: "📥 Interrupt response received: modify"
  - [ ] Backend 로그: "User feedback: {'action': 'modify', 'modifications': '...'}"
  - [ ] Backend 로그: "Content modified based on user feedback"
  - [ ] 최종 문서에 수정사항 반영됨

### 5.4 거부 (Reject)

- [ ] "거부" 버튼 클릭
  - [ ] Backend 로그: "📥 Interrupt response received: reject"
  - [ ] Workflow 종료
  - [ ] 적절한 응답 메시지

### 5.5 예상 로그 시퀀스 (승인 시)

```
1. ⏸️  Requesting human approval via interrupt()
2. 📥 Interrupt response received: approve
3. 🔄 Resuming workflow for session-xxx
4. 📊 Aggregate node: Consolidating search results  ← 노드 재시작
5. Aggregation complete: 128 characters
6. ⏸️  Requesting human approval via interrupt()  ← interrupt 재도달
7. ▶️  Workflow resumed with user feedback  ← resume 값 받음! 핵심!
8. User feedback: {'action': 'approve', ...}
9. 📝 Generate node: Creating final document
10. Document generation complete: XXX characters
11. ✅ Workflow resumed successfully
```

---

## 6. 결론 및 권장사항

### 6.1 현재 구현 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| interrupt() 사용 | ✅ 올바름 | LangGraph 0.6 패턴 준수 |
| Command 전달 방식 | ✅ 수정됨 | 첫 번째 positional parameter |
| Checkpointer | ✅ 올바름 | AsyncPostgresSaver 사용 |
| Thread ID | ✅ 올바름 | session_id로 추적 |
| None 처리 | ✅ 추가됨 | final_response None 안전 처리 |
| Node 재실행 | ⚠️ 예상됨 | 공식 동작, 최적화 가능 |
| final_response | ❌ 미생성 | Document Team에서 생성 필요 |

### 6.2 즉시 조치 필요

1. **백엔드 재시작 후 테스트**
   - Command 수정 적용 확인
   - "▶️ Workflow resumed" 로그 확인

2. **final_response 생성 추가**
   - `generate_node`에서 `final_response` 필드 추가
   - 또는 parent graph에서 후처리

3. **로그 기반 디버깅**
   - aggregate_node 재실행 횟수 확인
   - user_feedback 전달 여부 확인

### 6.3 향후 최적화

1. **Node 재실행 최적화**
   ```python
   # aggregate_node에서 캐시 활용
   if state.get("_aggregated_cache"):
       aggregated_content = state["_aggregated_cache"]
   else:
       aggregated_content = aggregate_results(search_results)
       state["_aggregated_cache"] = aggregated_content
   ```

2. **Multiple Interrupts 지원**
   - 현재는 단일 interrupt만 사용
   - 나중에 여러 단계 승인 필요시 index 순서 관리 필요

3. **Error Handling 강화**
   - Resume timeout 처리
   - Invalid feedback 처리
   - Session 만료 처리

---

## 7. 참고 자료

### 7.1 공식 문서

- [LangGraph HITL Overview](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [Wait for User Input](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
- [Add Human Intervention](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/add-human-in-the-loop/)
- [Interrupts Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts)

### 7.2 관련 파일

- `backend/app/service_agent/teams/document_team/aggregate.py` (interrupt 호출)
- `backend/app/service_agent/teams/document_team/workflow.py` (workflow 구조)
- `backend/app/api/chat_api.py` (resume 구현)
- `frontend/components/lease_contract/lease_contract_page.tsx` (UI)
- `frontend/components/chat-interface.tsx` (WebSocket 통신)

### 7.3 핵심 개념

- **interrupt()**: 노드 내에서 호출, 실행 중단 및 사용자 입력 대기
- **Command(resume=...)**: resume 값을 interrupt()로 전달
- **Checkpointer**: 상태 저장 및 복원 (AsyncPostgresSaver)
- **Thread ID**: 세션별 워크플로우 추적
- **Node Restart**: Resume 시 interrupt가 발생한 노드의 처음부터 재실행

---

**작성자**: Claude Code Agent
**검토 필요**: Backend 재시작 후 테스트 로그 확인
**다음 단계**: final_response 생성 로직 추가
