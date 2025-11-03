# DocumentExecutor 상세 분석 보고서

**분석일**: 2025-11-02
**분석 대상**: `document_executor.py` (DocumentExecutor 클래스)
**분석 범위**: 에이전트 구조, 워크플로우, HITL 패턴, 툴 통합, 작동 메커니즘
**작성자**: Claude Code

---

## 📋 목차

1. [개요](#1-개요)
2. [DocumentExecutor 클래스 구조](#2-documentexecutor-클래스-구조)
3. [워크플로우 상세 분석](#3-워크플로우-상세-분석)
4. [노드별 작동 메커니즘](#4-노드별-작동-메커니즘)
5. [HITL 패턴 심층 분석](#5-hitl-패턴-심층-분석)
6. [State 관리 메커니즘](#6-state-관리-메커니즘)
7. [Progress Tracking 시스템](#7-progress-tracking-시스템)
8. [툴 통합 구조](#8-툴-통합-구조)
9. [다른 실행 에이전트와의 비교](#9-다른-실행-에이전트와의-비교)
10. [현재 구현 상태 및 개선 제안](#10-현재-구현-상태-및-개선-제안)

---

## 1. 개요

### 1.1 DocumentExecutor란?

**DocumentExecutor**는 beta_v001 시스템의 **문서 생성 전문 에이전트**로, 주택임대차 계약서, 법률 문서, 계약서 검토 등의 **문서 생성 및 검토** 작업을 담당합니다.

**핵심 특징:**
- **Human-in-the-Loop (HITL) 패턴 구현**: LangGraph 0.6의 `interrupt()` 함수를 사용한 사용자 승인 워크플로우
- **LangGraph 서브그래프 구조**: MainSupervisorState를 사용하여 상위 Supervisor와 통합
- **6단계 Progress Tracking**: 실시간 WebSocket 업데이트 지원
- **Mock 구현 + Future-ready 설계**: 현재는 테스트용 Mock, LLM 및 툴 통합 준비 완료

### 1.2 파일 정보

```
위치: backend/app/service_agent/execution_agents/document_executor.py
라인 수: 539줄
작성일: 2025-10-26
LangGraph 버전: 0.6
```

### 1.3 시스템 내 위치

```
TeamBasedSupervisor (team_supervisor.py)
  └─ execute_teams_node
      └─ _execute_single_team("document")
          └─ DocumentExecutor.execute() ⬅️ 이 파일
              └─ build_workflow() → Compiled Graph
                  ├─ planning_node
                  ├─ aggregate_node (HITL)
                  └─ generate_node
```

### 1.4 의존성

**직접 의존:**
- `langgraph.graph`: StateGraph, START, END
- `langgraph.types`: interrupt (HITL 핵심)
- `app.service_agent.foundation.separated_states`: MainSupervisorState

**미래 통합 예정:**
- `app.service_agent.llm_manager.llm_service`: LLMService
- `app.service_agent.tools.lease_contract_generator_tool`: LeaseContractGeneratorTool
- `app.service_agent.tools`: ValidationTool, ComplianceTool (TODO)

---

## 2. DocumentExecutor 클래스 구조

### 2.1 클래스 정의

```python
class DocumentExecutor:
    """
    Document generation executor with HITL workflow.

    Workflow:
    1. Planning: Analyze query and determine document requirements
    2. Aggregate: Consolidate information and request HITL approval
    3. Generate: Create final document based on approved content
    """
```

**설계 철학:**
- **단일 책임**: 문서 생성에만 집중
- **확장 가능성**: 미래 툴 통합을 위한 인터페이스 준비
- **HITL 중심**: 사용자 승인 없이는 최종 문서 생성 불가

### 2.2 초기화 메서드

#### 2.2.1 `__init__` 메서드 (44-56줄)

```python
def __init__(self, llm_context=None, checkpointer=None, progress_callback=None):
    """
    Initialize DocumentExecutor.

    Args:
        llm_context: Optional LLM context for future integration
        checkpointer: AsyncPostgresSaver for state checkpointing
        progress_callback: Optional callback for real-time progress updates
    """
    self.llm_context = llm_context
    self.checkpointer = checkpointer
    self.progress_callback = progress_callback  # 🆕 Store parent's WebSocket callback
    logger.info("📄 DocumentExecutor initialized")
```

**주요 속성:**

| 속성 | 타입 | 역할 |
|------|------|------|
| `llm_context` | Any | LLM 컨텍스트 (현재 미사용, 미래 통합용) |
| `checkpointer` | AsyncPostgresSaver | PostgreSQL 기반 State 체크포인팅 (HITL 필수) |
| `progress_callback` | Callable | WebSocket 실시간 진행 상황 전송 함수 |

**checkpointer의 역할:**
- HITL `interrupt()` 시점에서 State 저장
- 사용자 승인 후 `Command(resume=...)` 호출 시 State 복원
- PostgreSQL `checkpoints` 테이블에 저장 (참고: [checkpointer.py](../../backend/app/service_agent/foundation/checkpointer.py:46-90))

**progress_callback의 역할:**
- 상위 Supervisor의 WebSocket callback 함수
- 6단계 진행 상황을 실시간으로 프론트엔드에 전송
- `_update_step_progress()` 메서드에서 호출

### 2.3 워크플로우 구성

#### 2.3.1 `build_workflow` 메서드 (58-90줄)

```python
def build_workflow(self):
    """
    Build the document generation workflow graph.

    Workflow Structure:
        START → planning → aggregate (HITL) → generate → END

    Returns:
        Compiled StateGraph with interrupt support
    """
    logger.info("🔧 Building document generation workflow")

    workflow = StateGraph(MainSupervisorState)

    # Add nodes
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("aggregate", self.aggregate_node)
    workflow.add_node("generate", self.generate_node)

    # Define edges
    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "aggregate")
    workflow.add_edge("aggregate", "generate")
    workflow.add_edge("generate", END)

    # Compile with checkpointer for HITL support
    compiled_graph = workflow.compile(
        checkpointer=self.checkpointer,
        interrupt_before=[]  # interrupt() is called within aggregate_node
    )

    logger.info("✅ Document workflow compiled successfully")
    return compiled_graph
```

**워크플로우 구조:**

```
START
  ↓
planning_node (Step 1: 계획 수립)
  ↓
aggregate_node (Step 2-4: 정보 검증 → HITL 승인 → 법률 검토)
  ↓
  [interrupt() - 사용자 승인 대기]
  ↓
  [Command(resume=user_feedback) - 재개]
  ↓
generate_node (Step 5-6: 문서 생성 → 최종 검토)
  ↓
END
```

**LangGraph 0.6 컴파일 옵션:**

| 옵션 | 값 | 설명 |
|------|-----|------|
| `checkpointer` | AsyncPostgresSaver | State 저장/복원 (HITL 필수) |
| `interrupt_before` | `[]` | aggregate_node 내부에서 `interrupt()` 직접 호출 |

**중요**: `interrupt_before` 배열은 비어있음. LangGraph 0.6에서는 노드 내부에서 `interrupt()` 함수를 직접 호출하는 방식 사용.

---

## 3. 워크플로우 상세 분석

### 3.1 워크플로우 단계 개요

DocumentExecutor는 **3개 노드 + 6개 진행 단계**로 구성됩니다.

**노드 vs 진행 단계 비교:**

| 노드 (Node) | 포함된 진행 단계 (Progress Steps) | 설명 |
|-------------|-----------------------------------|------|
| `planning_node` | Step 1: 계획 수립 | 문서 타입 분석, 섹션 구성 |
| `aggregate_node` | Step 2: 정보 검증<br>Step 3: 정보 입력 (HITL)<br>Step 4: 법률 검토 | 검색 → 집계 → 사용자 승인 → 피드백 적용 |
| `generate_node` | Step 5: 문서 생성<br>Step 6: 최종 검토 | 최종 문서 생성 및 검증 |

### 3.2 State 전파 흐름

```python
# Input State (from Supervisor)
MainSupervisorState {
    "query": "전세 계약서 작성해줘",
    "session_id": "sess_abc123",
    "team_results": {},  # 다른 팀의 결과 (선택적)
    ...
}

# After planning_node
MainSupervisorState {
    "planning_result": {
        "document_type": "general",
        "sections": ["introduction", "main_content", "conclusion"],
        "search_keywords": ["전세", "계약서", "작성"]
    },
    "workflow_status": "running"
}

# After aggregate_node (interrupt 전)
MainSupervisorState {
    "aggregated_content": "Aggregated Content:\n- 전세: Mock...",
    "workflow_status": "interrupted",  # ⚠️ HITL 대기 상태
    "interrupted_by": "aggregate",
    "interrupt_type": "approval"
}

# After aggregate_node (resume 후)
MainSupervisorState {
    "aggregated_content": "...[User Feedback Applied]...",
    "collaboration_result": {
        "action": "modify",
        "modifications": "보증금 금액 수정"
    },
    "workflow_status": "running"  # 재개됨
}

# After generate_node (최종)
MainSupervisorState {
    "final_document": "# Document: GENERAL\n...",
    "final_response": {
        "answer": "...",
        "document_type": "general",
        "user_approved": true,
        "type": "document"
    },
    "team_results": {
        "document": {
            "status": "success",
            "data": {...}
        }
    },
    "workflow_status": "completed"
}
```

---

## 4. 노드별 작동 메커니즘

### 4.1 planning_node (계획 수립)

**위치**: 94-142줄
**역할**: 사용자 쿼리를 분석하여 문서 생성 계획 수립

#### 4.1.1 메서드 시그니처

```python
async def planning_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    """
    Planning Node: Analyze user query and create document generation plan.

    Current Implementation: Mock/TODO
    - Extracts simple keywords from query
    - Returns generic document structure

    Future Implementation:
    - Use LLM to analyze query intent
    - Determine specific document type (lease contract, legal notice, etc.)
    - Identify required information and sections
    - Plan validation and compliance requirements
    """
```

#### 4.1.2 실행 흐름

```python
# 1. Step Progress 시작
await self._update_step_progress(state, step_index=0, status="in_progress", progress=0)

# 2. 쿼리 추출
query = state.get("query", "")

# 3. 키워드 추출 (Mock)
planning_result = {
    "document_type": "general",
    "sections": ["introduction", "main_content", "conclusion"],
    "estimated_length": "medium",
    "requires_search": True,
    "search_keywords": self._extract_keywords(query),
    "timestamp": "2025-10-26T00:00:00"
}

# 4. Step Progress 완료
await self._update_step_progress(state, step_index=0, status="completed", progress=100)

# 5. State 업데이트
return {
    "planning_result": planning_result,
    "workflow_status": "running"
}
```

#### 4.1.3 `_extract_keywords` 헬퍼 메서드 (330-346줄)

**현재 구현 (Mock):**

```python
def _extract_keywords(self, query: str) -> List[str]:
    """
    Extract search keywords from user query.

    Current: Simple split (Mock)
    TODO: Use LLM for intelligent keyword extraction
    """
    # Simple extraction: take first 5 words
    keywords = query.split()[:5]
    logger.debug(f"Extracted keywords: {keywords}")
    return keywords
```

**미래 구현 (TODO):**

```python
# LLM 기반 키워드 추출
result = await self.llm_service.complete_json_async(
    prompt_name="document_keyword_extraction",
    variables={"query": query},
    temperature=0.1
)

return result.get("keywords", [])
```

#### 4.1.4 WebSocket 메시지

```json
{
    "type": "agent_step_progress",
    "agentName": "document",
    "agentType": "document",
    "stepId": "document_step_1",
    "stepIndex": 0,
    "status": "in_progress",
    "progress": 0,
    "timestamp": "..."
}

// ... 작업 완료 후 ...

{
    "type": "agent_step_progress",
    "agentName": "document",
    "agentType": "document",
    "stepId": "document_step_1",
    "stepIndex": 0,
    "status": "completed",
    "progress": 100,
    "timestamp": "..."
}
```

**프론트엔드 동작:**
- `ExecutionProgressPage`에서 "계획 수립" 단계 표시
- Progress bar: 0% → 100%
- 완료 시 체크마크 표시

---

### 4.2 aggregate_node (정보 집계 + HITL 승인)

**위치**: 144-245줄
**역할**: 검색 결과 집계 및 **사용자 승인 요청 (HITL 핵심)**

#### 4.2.1 메서드 시그니처

```python
async def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    """
    Aggregate Node: Consolidate information and request HITL approval.

    This is the CRITICAL HITL node using LangGraph 0.6 interrupt() pattern.

    Workflow:
    1. Perform mock search based on planning keywords
    2. Aggregate search results into coherent content
    3. Call interrupt() to pause execution and request user approval
    4. Resume when parent graph calls Command(resume=user_feedback)
    5. Apply user modifications if action == "modify"

    HITL Pattern (LangGraph 0.6):
    - Uses interrupt() function (NOT NodeInterrupt exception)
    - interrupt() stores value in checkpoint and waits
    - Parent graph retrieves via get_state().tasks[0].interrupts[0]
    - Resume with Command(resume=value)
    """
```

#### 4.2.2 실행 흐름 (Phase 1: 검색 및 집계)

```python
# 1. Step 2 시작 (정보 검증)
await self._update_step_progress(state, step_index=1, status="in_progress", progress=0)

# 2. Planning 결과 로드
planning_result = state.get("planning_result", {})
keywords = planning_result.get("search_keywords", [])

# 3. Mock 검색 실행
search_results = self._mock_search(keywords)
```

**`_mock_search` 헬퍼 메서드 (348-377줄):**

```python
def _mock_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Perform mock search for testing.

    Current: Returns fake search results
    TODO: Integrate with actual search tools:
    - Legal database search
    - Real estate database search
    - Document template search
    - Compliance guideline search
    """
    search_results = []
    for keyword in keywords:
        result = {
            "keyword": keyword,
            "source": "mock_database",
            "content": f"Mock search result for: {keyword}",
            "relevance_score": 0.85,
            "timestamp": "2025-10-26T00:00:00"
        }
        search_results.append(result)

    logger.debug(f"Mock search complete: {len(search_results)} results")
    return search_results
```

**미래 구현 (TODO):**

```python
# 실제 SearchExecutor 결과 활용
search_results = state.get("team_results", {}).get("search", {}).get("data", [])

# 또는 직접 Legal Search Tool 호출
from app.service_agent.tools import LegalSearch
legal_search = LegalSearch()
legal_results = await legal_search.search(query, {"limit": 10})
```

#### 4.2.3 실행 흐름 (Phase 2: 결과 집계)

```python
# 4. 결과 집계
aggregated_content = self._aggregate_results(search_results)

logger.info(f"Aggregation complete: {len(aggregated_content)} characters")

# 5. Step 2 완료 (정보 검증)
await self._update_step_progress(state, step_index=1, status="completed", progress=100)
```

**`_aggregate_results` 헬퍼 메서드 (379-405줄):**

```python
def _aggregate_results(self, search_results: List[Dict[str, Any]]) -> str:
    """
    Aggregate search results into coherent content.

    Current: Simple concatenation
    TODO: Use LLM to create intelligent aggregation with:
    - Semantic clustering
    - Relevance ranking
    - Duplicate removal
    - Coherent narrative structure
    """
    if not search_results:
        return "No search results to aggregate."

    # Simple aggregation
    aggregated = "\n\n".join([
        f"- {result.get('keyword', 'Unknown')}: {result.get('content', 'No content')}"
        for result in search_results
    ])

    return f"Aggregated Content:\n{aggregated}"
```

**미래 구현 (TODO):**

```python
# LLM 기반 지능형 집계
result = await self.llm_service.complete_async(
    prompt_name="document_aggregation",
    variables={
        "search_results": search_results,
        "document_type": planning_result["document_type"]
    }
)

return result
```

#### 4.2.4 실행 흐름 (Phase 3: HITL 승인 요청) ⭐ 핵심

```python
# 6. Step 3 시작 (정보 입력 HITL)
await self._update_step_progress(state, step_index=2, status="in_progress", progress=0)

logger.info("⏸️  Requesting human approval via interrupt()")

# 7. Interrupt value 준비
interrupt_value = {
    # User-facing data
    "aggregated_content": aggregated_content,
    "search_results_count": len(search_results),
    "message": "Please review the aggregated content before final document generation.",
    "options": {
        "approve": "Continue with document generation",
        "modify": "Provide feedback for modification",
        "reject": "Cancel document generation"
    },
    # Metadata for parent graph
    "_metadata": {
        "interrupted_by": "aggregate",
        "interrupt_type": "approval",
        "node_name": "document_team.aggregate"
    }
}

# 8. State 업데이트 (interrupt 전)
state["aggregated_content"] = aggregated_content
state["workflow_status"] = "interrupted"

# 9. ✅ LangGraph 0.6 HITL 패턴: interrupt() 호출
# 여기서 실행이 일시 중지되고 checkpointer에 State 저장
user_feedback = interrupt(interrupt_value)

# 🔄 이 아래 코드는 Command(resume=...) 호출 후에만 실행됨
logger.info("▶️  Workflow resumed with user feedback")
logger.info(f"User feedback: {user_feedback}")
```

**interrupt() 함수의 동작:**

1. **State Checkpointing**:
   ```python
   # PostgreSQL checkpoints 테이블에 저장
   checkpoint_data = {
       "state": current_state,
       "interrupt_value": interrupt_value,
       "node": "aggregate",
       "timestamp": datetime.now()
   }
   ```

2. **Parent Graph 알림**:
   ```python
   # Supervisor의 process_query_streaming이 감지
   result = await supervisor.app.ainvoke(...)

   if result.get("workflow_status") == "interrupted":
       # State snapshot 조회
       state_snapshot = await supervisor.app.aget_state(config)
       interrupt_data = state_snapshot.tasks[0].interrupts[0].value

       # WebSocket으로 클라이언트에 알림
       await conn_mgr.send_message(session_id, {
           "type": "workflow_interrupted",
           "interrupt_data": interrupt_data
       })
   ```

3. **Resume 대기**:
   ```python
   # 사용자가 프론트엔드에서 승인 버튼 클릭
   // Frontend
   websocket.send(JSON.stringify({
       type: "interrupt_response",
       action: "approve",
       feedback: {}
   }))

   # Backend에서 Command(resume=...) 호출
   await supervisor.app.ainvoke(
       Command(resume=user_feedback),
       config=config
   )
   ```

#### 4.2.5 실행 흐름 (Phase 4: 피드백 적용)

```python
# 10. Step 3 완료 (정보 입력 HITL)
await self._update_step_progress(state, step_index=2, status="completed", progress=100)

# 11. Step 4 시작 (법률 검토)
await self._update_step_progress(state, step_index=3, status="in_progress", progress=0)

# 12. 사용자 피드백 처리
if user_feedback and user_feedback.get("action") == "modify":
    logger.info("Applying user modifications")
    aggregated_content = self._apply_user_feedback(aggregated_content, user_feedback)

# 13. Step 4 완료 (법률 검토)
await self._update_step_progress(state, step_index=3, status="completed", progress=100)

# 14. State 반환
return {
    "aggregated_content": aggregated_content,
    "collaboration_result": user_feedback,
    "workflow_status": "running",
    "interrupted_by": "aggregate",
    "interrupt_type": "approval"
}
```

**`_apply_user_feedback` 헬퍼 메서드 (407-429줄):**

```python
def _apply_user_feedback(self, content: str, feedback: Dict[str, Any]) -> str:
    """
    Apply user feedback to modify content.

    Current: Simple append
    TODO: Use LLM to intelligently apply modifications:
    - Understand user intent
    - Merge changes coherently
    - Maintain document structure
    - Preserve important information
    """
    modifications = feedback.get("modifications", "")
    if modifications:
        # Simple append for now
        return f"{content}\n\n[User Feedback Applied]\n{modifications}"
    return content
```

**미래 구현 (TODO):**

```python
# LLM 기반 피드백 통합
result = await self.llm_service.complete_async(
    prompt_name="apply_user_feedback",
    variables={
        "original_content": content,
        "user_feedback": feedback.get("modifications", ""),
        "feedback_type": feedback.get("action", "")
    }
)

return result
```

#### 4.2.6 WebSocket 메시지 (HITL 승인 요청)

**Step 2 완료 → Step 3 시작:**

```json
{
    "type": "agent_step_progress",
    "stepId": "document_step_3",
    "stepIndex": 2,
    "status": "in_progress",
    "progress": 0
}
```

**Parent Graph → Client (workflow_interrupted):**

```json
{
    "type": "workflow_interrupted",
    "interrupted_by": "aggregate",
    "interrupt_type": "approval",
    "interrupt_data": {
        "aggregated_content": "Aggregated Content:\n- 전세: Mock...",
        "search_results_count": 5,
        "message": "Please review the aggregated content before final document generation.",
        "options": {
            "approve": "Continue with document generation",
            "modify": "Provide feedback for modification",
            "reject": "Cancel document generation"
        },
        "_metadata": {
            "interrupted_by": "aggregate",
            "interrupt_type": "approval",
            "node_name": "document_team.aggregate"
        }
    },
    "message": "워크플로우가 사용자 승인을 기다리고 있습니다.",
    "timestamp": "..."
}
```

**프론트엔드 렌더링:**

```jsx
// ExecutionProgressPage.tsx
if (message.type === "workflow_interrupted") {
    return (
        <InterruptCard>
            <h3>사용자 승인 필요</h3>
            <p>{message.interrupt_data.message}</p>

            <ContentPreview>
                {message.interrupt_data.aggregated_content}
            </ContentPreview>

            <ButtonGroup>
                <Button onClick={() => approve()}>
                    {message.interrupt_data.options.approve}
                </Button>
                <Button onClick={() => showModifyModal()}>
                    {message.interrupt_data.options.modify}
                </Button>
                <Button onClick={() => reject()}>
                    {message.interrupt_data.options.reject}
                </Button>
            </ButtonGroup>
        </InterruptCard>
    )
}
```

---

### 4.3 generate_node (문서 생성)

**위치**: 247-326줄
**역할**: 승인된 내용을 바탕으로 최종 문서 생성

#### 4.3.1 메서드 시그니처

```python
async def generate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    """
    Generate Node: Create final document from approved content.

    Current Implementation: Mock/TODO
    - Simple text formatting
    - Builds final_response for client
    - Adds team_results for parent graph

    Future Implementation:
    - Use LLM to create well-formatted document
    - Apply document templates (DOCX, PDF)
    - Use LeaseContractGeneratorTool for lease contracts
    - Run validation and compliance checks
    """
```

#### 4.3.2 실행 흐름

```python
# 1. Step 5 시작 (문서 생성)
await self._update_step_progress(state, step_index=4, status="in_progress", progress=0)

# 2. 데이터 로드
aggregated_content = state.get("aggregated_content", "")
planning_result = state.get("planning_result", {})
collaboration_result = state.get("collaboration_result", {})

# 3. 최종 문서 생성
final_document = self._format_document(
    content=aggregated_content,
    planning=planning_result,
    feedback=collaboration_result
)

logger.info(f"Document generation complete: {len(final_document)} characters")

# 4. Step 5 완료
await self._update_step_progress(state, step_index=4, status="completed", progress=100)

# 5. Step 6 시작 (최종 검토 - Mock, 실제 HITL 없음)
await self._update_step_progress(state, step_index=5, status="in_progress", progress=0)

# 6. final_response 구성
doc_type = planning_result.get("document_type", "general")
user_action = collaboration_result.get("action", "unknown") if collaboration_result else "unknown"

final_response = {
    "answer": final_document,
    "document_type": doc_type,
    "user_approved": user_action == "approve",
    "user_action": user_action,
    "modifications_applied": user_action == "modify",
    "type": "document"
}

# 7. team_results 추가 (Parent Graph 통합)
team_results = {
    "document": {
        "status": "success",
        "data": final_response
    }
}

# 8. Step 6 완료
await self._update_step_progress(state, step_index=5, status="completed", progress=100)

# 9. State 반환
return {
    "final_document": final_document,
    "final_response": final_response,
    "workflow_status": "completed",
    "team_results": team_results
}
```

#### 4.3.3 `_format_document` 헬퍼 메서드 (431-475줄)

**현재 구현 (Mock):**

```python
def _format_document(
    self,
    content: str,
    planning: Dict[str, Any],
    feedback: Dict[str, Any]
) -> str:
    """
    Format final document with proper structure.

    Current: Simple text template
    TODO: Use LLM and templates for professional formatting:
    - Document type-specific templates (lease contract, legal notice, etc.)
    - DOCX/PDF generation
    - Legal compliance formatting
    - Professional styling
    """
    doc_type = planning.get("document_type", "general")
    sections = planning.get("sections", [])

    document = f"""
# Document: {doc_type.upper()}

## Generated Content

{content}

## Metadata
- Document Type: {doc_type}
- Sections: {', '.join(sections)}
- User Approved: {feedback.get('action') == 'approve' if feedback else False}
- Generation Time: 2025-10-26

---
Generated by Holmes AI Document Team
"""

    return document.strip()
```

**미래 구현 (TODO):**

```python
# 문서 타입별 분기
if doc_type == "lease_contract":
    # LeaseContractGeneratorTool 사용
    from app.service_agent.tools import LeaseContractGeneratorTool

    tool = LeaseContractGeneratorTool()
    result = await tool.execute(
        address_road=extracted_params["address"],
        deposit=extracted_params["deposit"],
        # ...
    )

    return result["content"]

elif doc_type == "legal_notice":
    # LLM 기반 법률 문서 생성
    result = await self.llm_service.complete_async(
        prompt_name="legal_notice_generation",
        variables={
            "content": content,
            "user_feedback": feedback
        }
    )

    return result

else:
    # Generic LLM 기반 문서 생성
    result = await self.llm_service.complete_async(
        prompt_name="generic_document_generation",
        variables={"content": content}
    )

    return result
```

#### 4.3.4 WebSocket 메시지

**Step 5-6 진행:**

```json
{
    "type": "agent_step_progress",
    "stepId": "document_step_5",
    "status": "in_progress",
    "progress": 0
}

// ... 문서 생성 완료 ...

{
    "type": "agent_step_progress",
    "stepId": "document_step_5",
    "status": "completed",
    "progress": 100
}

{
    "type": "agent_step_progress",
    "stepId": "document_step_6",
    "status": "completed",
    "progress": 100
}
```

**Parent Graph → Client (final_response):**

```json
{
    "type": "final_response",
    "response": {
        "answer": "# Document: GENERAL\n\n## Generated Content\n...",
        "document_type": "general",
        "user_approved": true,
        "user_action": "approve",
        "modifications_applied": false,
        "type": "document"
    },
    "timestamp": "..."
}
```

---

## 5. HITL 패턴 심층 분석

### 5.1 LangGraph 0.6 interrupt() 패턴

DocumentExecutor는 **LangGraph 0.6의 `interrupt()` 함수**를 사용하여 HITL을 구현합니다.

**LangGraph 0.5 vs 0.6 비교:**

| 항목 | LangGraph 0.5 | LangGraph 0.6 (현재) |
|------|---------------|---------------------|
| HITL 메서드 | `NodeInterrupt` Exception | `interrupt()` 함수 |
| 사용법 | `raise NodeInterrupt(value)` | `result = interrupt(value)` |
| Resume 방법 | `ainvoke(input, config)` | `ainvoke(Command(resume=value), config)` |
| State 조회 | `get_state(config)` | `aget_state(config).tasks[0].interrupts[0]` |
| Checkpointer | 필수 | 필수 |

### 5.2 interrupt() 함수 상세 분석

#### 5.2.1 함수 시그니처

```python
from langgraph.types import interrupt

result = interrupt(value: Any) -> Any
```

**파라미터:**
- `value`: 사용자에게 전달할 데이터 (dict, str, 등)

**반환값:**
- `Command(resume=...)` 호출 시 전달된 값

#### 5.2.2 실행 흐름

```python
# 1. interrupt() 호출 전
state["aggregated_content"] = aggregated_content
state["workflow_status"] = "interrupted"

# 2. interrupt() 호출 (execution pauses here)
user_feedback = interrupt({
    "aggregated_content": aggregated_content,
    "message": "Please review...",
    "options": {...}
})

# 3. Checkpointer에 State 저장
# PostgreSQL checkpoints 테이블에 저장:
# - state: 현재 State
# - interrupt_value: interrupt()에 전달된 value
# - node: "aggregate"
# - timestamp: 현재 시간

# 4. Parent Graph에 반환
# Supervisor의 ainvoke()가 반환:
# {
#     "workflow_status": "interrupted",
#     "final_response": None
# }

# 5. Parent Graph가 State 조회
state_snapshot = await supervisor.app.aget_state(config)
interrupt_data = state_snapshot.tasks[0].interrupts[0].value

# 6. WebSocket으로 Client에 알림
await conn_mgr.send_message(session_id, {
    "type": "workflow_interrupted",
    "interrupt_data": interrupt_data
})

# 7. Client에서 승인/수정/거부 선택
// Frontend
websocket.send(JSON.stringify({
    type: "interrupt_response",
    action: "modify",
    feedback: {
        modifications: "보증금 금액 수정"
    }
}))

# 8. Backend에서 Command(resume=...) 호출
await supervisor.app.ainvoke(
    Command(resume={
        "action": "modify",
        "modifications": "보증금 금액 수정"
    }),
    config=config
)

# 9. interrupt() 함수가 반환 (execution resumes)
user_feedback = {
    "action": "modify",
    "modifications": "보증금 금액 수정"
}

# 10. 피드백 적용 후 계속 진행
if user_feedback.get("action") == "modify":
    aggregated_content = self._apply_user_feedback(aggregated_content, user_feedback)
```

### 5.3 Checkpointer의 역할

**파일**: [checkpointer.py](../../backend/app/service_agent/foundation/checkpointer.py)

#### 5.3.1 AsyncPostgresSaver 구조

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Checkpointer 생성
checkpointer = await AsyncPostgresSaver.from_conn_string(DATABASE_URL)
await checkpointer.setup()  # 테이블 생성

# 테이블 구조:
# - checkpoints: State 저장
# - checkpoint_blobs: 큰 데이터 저장
# - checkpoint_writes: Write 로그
```

#### 5.3.2 State 저장/복원

**저장 (interrupt() 호출 시):**

```sql
INSERT INTO checkpoints (
    thread_id,
    checkpoint_id,
    checkpoint_data,
    created_at
) VALUES (
    'sess_abc123',  -- session_id
    'checkpoint_1',
    {
        "state": {...},
        "interrupt_value": {...},
        "node": "aggregate"
    },
    NOW()
);
```

**복원 (Command(resume=...) 호출 시):**

```python
# LangGraph가 자동으로 복원
config = {"configurable": {"thread_id": "sess_abc123"}}
await supervisor.app.ainvoke(Command(resume=...), config=config)

# Checkpointer에서 최신 checkpoint 조회 후 State 복원
```

### 5.4 Parent Graph 통합

**파일**: [team_supervisor.py](../../backend/app/service_agent/supervisor/team_supervisor.py)

#### 5.4.1 Supervisor에서 DocumentExecutor 호출

```python
# _execute_single_team 메서드 (1251-1285줄)
async def _execute_single_team(self, team_name: str, shared_state, main_state):
    team = self.teams[team_name]

    # Progress Callback 설정
    progress_callback = self._progress_callbacks.get(session_id)
    if progress_callback:
        team.progress_callback = progress_callback

    # DocumentExecutor 실행
    if team_name == "document":
        doc_type = self._extract_document_type(main_state)
        return await team.execute(shared_state, document_type=doc_type)
```

#### 5.4.2 Interrupt 감지

```python
# process_query_streaming 메서드 (1763-1863줄)
result = await self.app.ainvoke(initial_state, config=config)

workflow_status = result.get("workflow_status")
final_response = result.get("final_response")

if workflow_status == "interrupted" or final_response is None:
    logger.info(f"⏸️  Workflow interrupted for session {session_id}")

    # LangGraph 0.6 API로 State 조회
    config = {"configurable": {"thread_id": session_id}}
    state_snapshot = await self.app.aget_state(config)

    # interrupt_value 추출
    if state_snapshot.tasks and len(state_snapshot.tasks) > 0:
        first_task = state_snapshot.tasks[0]
        if hasattr(first_task, 'interrupts') and first_task.interrupts:
            interrupt_value = first_task.interrupts[0].value
            # ...
```

#### 5.4.3 Resume 처리

```python
# chat_api.py의 WebSocket 엔드포인트
if message_type == "interrupt_response":
    action = data.get("action")
    feedback = data.get("feedback", {})

    # Interrupted session 조회
    session_data = _interrupted_sessions.get(session_id)
    if not session_data:
        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": "No interrupted session found"
        })
        continue

    config = session_data["config"]

    # Resume value 구성
    resume_value = {
        "action": action,
        "modifications": feedback.get("modifications", "")
    }

    # Command(resume=...) 호출
    from langgraph.types import Command

    result = await supervisor.app.ainvoke(
        Command(resume=resume_value),
        config=config
    )

    # Interrupted session 제거
    async with _interrupted_sessions_lock:
        _interrupted_sessions.pop(session_id, None)

    # Final response 전송
    if result.get("final_response"):
        await conn_mgr.send_message(session_id, {
            "type": "final_response",
            "response": result["final_response"]
        })
```

### 5.5 HITL 오류 처리

#### 5.5.1 Timeout 처리

**현재 상태**: 구현되지 않음 (TODO)

**제안:**

```python
# chat_api.py
INTERRUPT_TIMEOUT = 300  # 5분

_interrupted_sessions[session_id] = {
    "config": config,
    "interrupt_data": interrupt_data,
    "timestamp": datetime.now(),
    "timeout_task": asyncio.create_task(
        _handle_interrupt_timeout(session_id)
    )
}

async def _handle_interrupt_timeout(session_id: str):
    await asyncio.sleep(INTERRUPT_TIMEOUT)

    # Timeout 처리
    session_data = _interrupted_sessions.get(session_id)
    if session_data:
        # 자동 거부 처리
        await supervisor.app.ainvoke(
            Command(resume={"action": "reject", "reason": "timeout"}),
            config=session_data["config"]
        )

        # Session 제거
        _interrupted_sessions.pop(session_id, None)
```

#### 5.5.2 중복 Resume 방지

**현재 상태**: `_interrupted_sessions`에서 session 제거로 방지

```python
# Resume 후 즉시 제거
async with _interrupted_sessions_lock:
    _interrupted_sessions.pop(session_id, None)

# 이후 재시도 시
if session_id not in _interrupted_sessions:
    await conn_mgr.send_message(session_id, {
        "type": "error",
        "error": "No interrupted session found"
    })
```

---

## 6. State 관리 메커니즘

### 6.1 MainSupervisorState 구조

**파일**: [separated_states.py](../../backend/app/service_agent/foundation/separated_states.py:289-375)

```python
class MainSupervisorState(TypedDict, total=False):
    """
    메인 Supervisor의 State
    total=False로 설정하여 모든 필드를 선택적으로 만듦
    """
    # Core fields (required)
    query: str
    session_id: str
    chat_session_id: Optional[str]
    request_id: str

    # Document Team Fields (for HITL workflow)
    planning_result: Optional[Dict[str, Any]]  # Document planning result
    search_results: Optional[List[Dict[str, Any]]]  # Search results from document team
    aggregated_content: Optional[str]  # Aggregated content before HITL
    final_document: Optional[str]  # Final generated document
    collaboration_result: Optional[Dict[str, Any]]  # HITL resume value (user feedback)

    # HITL (Human-in-the-Loop) Fields
    workflow_status: Optional[str]  # "running" | "interrupted" | "completed" | "failed"
    interrupted_by: Optional[str]  # Node name that triggered interrupt
    interrupt_type: Optional[str]  # "approval" | "review" | "feedback"
    interrupt_data: Optional[Dict[str, Any]]  # Data to present to user during interrupt

    # Results
    team_results: Dict[str, Any]
    final_response: Optional[Dict[str, Any]]
```

### 6.2 DocumentExecutor에서 사용하는 State 필드

**Input (Supervisor → DocumentExecutor):**

```python
{
    "query": str,              # 사용자 쿼리
    "session_id": str,         # WebSocket session ID
    "team_results": {          # 다른 팀의 결과 (optional)
        "search": {...},       # SearchExecutor 결과
        "analysis": {...}      # AnalysisExecutor 결과
    }
}
```

**Output (DocumentExecutor → Supervisor):**

```python
{
    # Planning 결과
    "planning_result": {
        "document_type": "general",
        "sections": [...],
        "search_keywords": [...]
    },

    # Aggregation 결과
    "aggregated_content": str,

    # HITL 상태
    "workflow_status": "completed",  # or "interrupted"
    "interrupted_by": "aggregate",
    "interrupt_type": "approval",
    "collaboration_result": {
        "action": "approve",
        "modifications": ""
    },

    # 최종 결과
    "final_document": str,
    "final_response": {
        "answer": str,
        "document_type": str,
        "user_approved": bool,
        "type": "document"
    },

    # Parent Graph 통합
    "team_results": {
        "document": {
            "status": "success",
            "data": {...}
        }
    }
}
```

### 6.3 State 직렬화 및 Checkpointing

#### 6.3.1 msgpack 직렬화

**Checkpointer가 사용하는 형식**: msgpack

**지원되는 타입:**
- 기본 타입: str, int, float, bool, None
- 컬렉션: list, dict
- 날짜: datetime (ISO 형식 변환 필요)

**지원되지 않는 타입:**
- Callable (함수, 메서드)
- Custom 객체 (dataclass는 dict 변환 필요)

#### 6.3.2 progress_callback의 State 제외

**문제:**

```python
# ❌ 잘못된 예
state["progress_callback"] = progress_callback

# Checkpointer 직렬화 시도 시:
# Error: "Type is not msgpack serializable: function"
```

**해결책:**

```python
# ✅ 올바른 예
# DocumentExecutor 인스턴스 속성으로 저장
self.progress_callback = progress_callback

# State에는 포함하지 않음
# 각 노드에서 self.progress_callback으로 접근
```

**코드 위치:**

```python
# DocumentExecutor.__init__ (44-56줄)
def __init__(self, llm_context=None, checkpointer=None, progress_callback=None):
    self.progress_callback = progress_callback  # ✅ 인스턴스 속성

# aggregate_node (144-245줄)
async def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    # ✅ self로 접근
    await self._update_step_progress(state, step_index=1, status="in_progress", progress=0)
```

### 6.4 State Pollution 방지

DocumentExecutor는 **MainSupervisorState만 사용**하여 State pollution을 최소화합니다.

**SearchExecutor 비교:**

```python
# SearchExecutor는 별도의 SearchTeamState 사용
class SearchTeamState(TypedDict):
    team_name: str
    status: str
    shared_context: Dict[str, Any]
    keywords: Optional[SearchKeywords]
    legal_results: List[Dict[str, Any]]
    # ... 30+ fields
```

**DocumentExecutor는 MainSupervisorState 직접 사용:**

```python
# 별도의 DocumentTeamState 없음
# MainSupervisorState에 Document 관련 필드 추가
class MainSupervisorState(TypedDict, total=False):
    planning_result: Optional[Dict[str, Any]]
    aggregated_content: Optional[str]
    final_document: Optional[str]
    collaboration_result: Optional[Dict[str, Any]]
    # ...
```

**장점:**
- State 변환 오버헤드 없음
- Parent Graph와 직접 통합
- Checkpointing 단순화

**단점:**
- MainSupervisorState가 비대해질 수 있음
- 팀별 독립성 감소

---

## 7. Progress Tracking 시스템

### 7.1 6단계 Progress Steps

DocumentExecutor는 **6개의 진행 단계**를 정의합니다.

| Step Index | Step Name | Node | Status Updates |
|------------|-----------|------|----------------|
| 0 | 계획 수립 | planning_node | in_progress → completed |
| 1 | 정보 검증 | aggregate_node | in_progress → completed |
| 2 | 정보 입력 (HITL) | aggregate_node | in_progress → completed |
| 3 | 법률 검토 | aggregate_node | in_progress → completed |
| 4 | 문서 생성 | generate_node | in_progress → completed |
| 5 | 최종 검토 | generate_node | in_progress → completed |

### 7.2 `_update_step_progress` 메서드

**위치**: 477-520줄

```python
async def _update_step_progress(
    self,
    state: MainSupervisorState,
    step_index: int,
    status: str,
    progress: int = 0
) -> None:
    """
    🆕 Update agent step progress in state AND forward to WebSocket.

    This method writes step progress updates to the state and forwards
    them to the parent graph via WebSocket callback for real-time UI updates.

    Args:
        state: MainSupervisorState
        step_index: Step index (0-5 for document agent's 6 steps)
        status: Step status ("pending", "in_progress", "completed", "failed")
        progress: Progress percentage (0-100)
    """
    # Initialize document_step_progress if not exists
    if "document_step_progress" not in state:
        state["document_step_progress"] = {}

    # Update step progress in state
    state["document_step_progress"][f"step_{step_index}"] = {
        "index": step_index,
        "status": status,
        "progress": progress
    }

    logger.debug(f"[DocumentExecutor] Step {step_index} progress: {status} ({progress}%)")

    # 🆕 Forward to WebSocket via parent callback for real-time UI updates
    if self.progress_callback:
        await self.progress_callback("agent_step_progress", {
            "agentName": "document",
            "agentType": "document",
            "stepId": f"document_step_{step_index + 1}",  # 1-indexed for frontend
            "stepIndex": step_index,
            "status": status,
            "progress": progress
        })
        logger.debug(f"[DocumentExecutor] Forwarded step {step_index} progress to WebSocket")
```

### 7.3 WebSocket 메시지 형식

#### 7.3.1 agent_step_progress 메시지

```json
{
    "type": "agent_step_progress",
    "agentName": "document",
    "agentType": "document",
    "stepId": "document_step_1",
    "stepIndex": 0,
    "status": "in_progress",
    "progress": 0,
    "timestamp": "2025-11-02T14:30:00.123Z"
}
```

**필드 설명:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | string | "agent_step_progress" (고정) |
| `agentName` | string | "document" (에이전트 이름) |
| `agentType` | string | "document" (에이전트 타입) |
| `stepId` | string | "document_step_1" (프론트엔드용 1-indexed) |
| `stepIndex` | number | 0 (백엔드용 0-indexed) |
| `status` | string | "pending" \| "in_progress" \| "completed" \| "failed" |
| `progress` | number | 0-100 (진행률 퍼센트) |

#### 7.3.2 프론트엔드 렌더링

**ExecutionProgressPage.tsx:**

```tsx
// DocumentAgent 카드
<AgentCard agentName="document">
    <AgentHeader>
        <AgentIcon>📄</AgentIcon>
        <AgentTitle>문서 생성</AgentTitle>
    </AgentHeader>

    <StepsList>
        {documentSteps.map((step, index) => (
            <StepItem key={step.stepId}>
                <StepIcon status={step.status}>
                    {step.status === "completed" ? "✓" :
                     step.status === "in_progress" ? "⟳" : "○"}
                </StepIcon>
                <StepName>{getStepName(index)}</StepName>
                <ProgressBar value={step.progress} />
            </StepItem>
        ))}
    </StepsList>
</AgentCard>
```

**Step 이름 매핑:**

```tsx
const getStepName = (index: number) => {
    const stepNames = [
        "계획 수립",      // Step 0
        "정보 검증",      // Step 1
        "정보 입력",      // Step 2 (HITL)
        "법률 검토",      // Step 3
        "문서 생성",      // Step 4
        "최종 검토"       // Step 5
    ];
    return stepNames[index] || `Step ${index + 1}`;
};
```

### 7.4 SearchExecutor와의 비교

**SearchExecutor의 Progress Tracking:**

```python
# 4단계만 사용
# Step 0: 쿼리 생성
# Step 1: 데이터 검색
# Step 2: 결과 필터링
# Step 3: 결과 정리
```

**DocumentExecutor의 Progress Tracking:**

```python
# 6단계 사용 (HITL 포함)
# Step 0: 계획 수립
# Step 1: 정보 검증
# Step 2: 정보 입력 (HITL)
# Step 3: 법률 검토
# Step 4: 문서 생성
# Step 5: 최종 검토
```

**차이점:**
- DocumentExecutor는 HITL을 별도 단계로 추적
- 더 세분화된 진행 상황 제공
- 프론트엔드에서 사용자 승인 대기 상태 명확히 표시

---

## 8. 툴 통합 구조

### 8.1 현재 구현 상태

DocumentExecutor는 **Mock 구현**으로, 실제 툴 통합은 **TODO** 상태입니다.

**Mock 메서드:**
- `_extract_keywords()`: 단순 split
- `_mock_search()`: 가짜 검색 결과 반환
- `_aggregate_results()`: 단순 concatenation
- `_apply_user_feedback()`: 단순 append
- `_format_document()`: 텍스트 템플릿

### 8.2 미래 툴 통합 계획

#### 8.2.1 LeaseContractGeneratorTool 통합

**파일**: [lease_contract_generator_tool.py](../../backend/app/service_agent/tools/lease_contract_generator_tool.py)

**기능:**
- 주택임대차 표준계약서 DOCX 생성
- 플레이스홀더 기반 필드 채우기
- Markdown 변환 지원

**통합 예시:**

```python
# generate_node에서 사용
async def generate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    doc_type = planning_result.get("document_type")

    if doc_type == "lease_contract":
        # LeaseContractGeneratorTool 사용
        from app.service_agent.tools import LeaseContractGeneratorTool

        tool = LeaseContractGeneratorTool()

        # 파라미터 추출 (LLM 또는 규칙 기반)
        params = self._extract_lease_params(aggregated_content, collaboration_result)

        # 계약서 생성
        result = await tool.execute(**params)

        if result["status"] == "success":
            final_document = result["content"]
            docx_path = result["docx_path"]

            # final_response에 DOCX 경로 추가
            final_response = {
                "answer": final_document,
                "document_type": "lease_contract",
                "docx_path": docx_path,
                "sections": result["sections"],
                "type": "document"
            }
        else:
            # Fallback: LLM 기반 생성
            final_document = await self._format_document_with_llm(...)
    else:
        # 다른 문서 타입 처리
        ...
```

#### 8.2.2 LLM 통합

**파일**: [llm_service.py](../../backend/app/service_agent/llm_manager/llm_service.py)

**사용 시나리오:**

1. **키워드 추출 (planning_node):**

```python
result = await self.llm_service.complete_json_async(
    prompt_name="document_keyword_extraction",
    variables={"query": query},
    temperature=0.1
)

keywords = result.get("keywords", [])
```

2. **문서 타입 결정 (planning_node):**

```python
result = await self.llm_service.complete_json_async(
    prompt_name="document_type_determination",
    variables={
        "query": query,
        "available_types": ["lease_contract", "sales_contract", "legal_notice", ...]
    },
    temperature=0.0
)

doc_type = result.get("document_type")
```

3. **검색 결과 집계 (aggregate_node):**

```python
result = await self.llm_service.complete_async(
    prompt_name="document_aggregation",
    variables={
        "search_results": search_results,
        "document_type": doc_type
    },
    temperature=0.3
)

aggregated_content = result
```

4. **사용자 피드백 통합 (aggregate_node):**

```python
result = await self.llm_service.complete_async(
    prompt_name="apply_user_feedback",
    variables={
        "original_content": content,
        "user_feedback": feedback.get("modifications"),
        "feedback_type": feedback.get("action")
    }
)

modified_content = result
```

5. **문서 생성 (generate_node):**

```python
result = await self.llm_service.complete_async(
    prompt_name="generic_document_generation",
    variables={
        "content": aggregated_content,
        "document_type": doc_type,
        "user_approved": True
    },
    temperature=0.5
)

final_document = result
```

#### 8.2.3 Validation 툴 통합 (TODO)

**제안:**

```python
# generate_node에서 사용
from app.service_agent.tools import DocumentValidationTool

validation_tool = DocumentValidationTool()

validation_result = await validation_tool.validate(
    document=final_document,
    document_type=doc_type
)

if validation_result["has_errors"]:
    # 자동 수정 또는 사용자에게 알림
    final_document = await self._fix_validation_errors(
        final_document,
        validation_result["errors"]
    )
```

#### 8.2.4 Compliance 툴 통합 (TODO)

**제안:**

```python
# generate_node에서 사용
from app.service_agent.tools import ComplianceTool

compliance_tool = ComplianceTool()

compliance_result = await compliance_tool.check(
    document=final_document,
    document_type="lease_contract"
)

if not compliance_result["is_compliant"]:
    # 법률 준수 항목 추가
    final_document = await self._add_compliance_clauses(
        final_document,
        compliance_result["missing_clauses"]
    )
```

### 8.3 SearchExecutor와의 통합

DocumentExecutor는 **SearchExecutor의 결과**를 활용할 수 있습니다.

**시나리오:**

1. Supervisor가 SearchExecutor 먼저 실행
2. SearchExecutor의 결과가 `team_results["search"]`에 저장
3. DocumentExecutor가 해당 결과 활용

**코드 예시:**

```python
# aggregate_node에서 SearchExecutor 결과 활용
async def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    # SearchExecutor 결과 확인
    search_results = state.get("team_results", {}).get("search", {}).get("data", {})

    if search_results:
        # SearchExecutor의 법률 검색 결과 사용
        legal_results = search_results.get("legal_results", [])

        # 집계
        aggregated_content = self._aggregate_legal_results(legal_results)
    else:
        # 자체 검색 실행
        keywords = planning_result.get("search_keywords", [])
        search_results = self._mock_search(keywords)
        aggregated_content = self._aggregate_results(search_results)

    # ...
```

---

## 9. 다른 실행 에이전트와의 비교

### 9.1 SearchExecutor vs DocumentExecutor

| 항목 | SearchExecutor | DocumentExecutor |
|------|----------------|------------------|
| **파일** | search_executor.py | document_executor.py |
| **주요 역할** | 법률/부동산/대출 정보 검색 | 문서 생성 및 검토 |
| **노드 수** | 5개 | 3개 |
| **Progress Steps** | 4개 | 6개 |
| **HITL** | 없음 | 있음 (aggregate_node) |
| **State** | SearchTeamState (별도) | MainSupervisorState (직접) |
| **LLM 사용** | Tool 선택, 키워드 추출 | 전 과정 (TODO) |
| **Tools** | 7개 (Legal, Market, Loan, ...) | 1개 (LeaseContract, TODO) |
| **실행 전략** | Parallel/Sequential | Sequential only |
| **Mock 여부** | 일부 (Fallback) | 전체 (TODO) |

### 9.2 워크플로우 비교

**SearchExecutor 워크플로우:**

```
START
  ↓
prepare_node (키워드 추출, 범위 결정)
  ↓
route_node (병렬/순차 결정)
  ↓
search_node (실제 검색 실행)
  ↓
aggregate_node (결과 집계)
  ↓
finalize_node (상태 정리)
  ↓
END
```

**DocumentExecutor 워크플로우:**

```
START
  ↓
planning_node (문서 계획 수립)
  ↓
aggregate_node (검색 → 집계 → HITL 승인)
  ↓
  [interrupt() - 사용자 승인 대기]
  ↓
  [Command(resume=...) - 재개]
  ↓
generate_node (최종 문서 생성)
  ↓
END
```

### 9.3 코드 스타일 비교

**SearchExecutor:**

```python
# LLM 서비스 초기화 (에러 핸들링)
try:
    self.llm_service = LLMService(llm_context=llm_context)
    logger.info("✅ LLMService initialized successfully in SearchExecutor")
except Exception as e:
    logger.error(f"❌ LLMService initialization failed: {e}", exc_info=True)
    self.llm_service = None

# 툴 초기화 (Fallback)
try:
    from app.service_agent.tools.legal_search_tool import LegalSearch
    self.legal_search_tool = LegalSearch()
except Exception as e:
    logger.warning(f"LegalSearch initialization failed: {e}, trying HybridLegalSearch fallback")
    try:
        from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
        self.legal_search_tool = HybridLegalSearch()
    except Exception as e2:
        logger.warning(f"HybridLegalSearch fallback also failed: {e2}")
```

**DocumentExecutor:**

```python
# 단순 초기화 (Mock 구현)
self.llm_context = llm_context
self.checkpointer = checkpointer
self.progress_callback = progress_callback
logger.info("📄 DocumentExecutor initialized")

# 툴 초기화 없음 (TODO)
```

**차이점:**
- SearchExecutor: 프로덕션 준비, 에러 핸들링 철저
- DocumentExecutor: 테스트/개발 단계, Mock 구현

---

## 10. 현재 구현 상태 및 개선 제안

### 10.1 현재 구현 상태 요약

#### 10.1.1 ✅ 완성된 부분

1. **LangGraph 0.6 워크플로우 구조**
   - StateGraph 정의 및 컴파일
   - 3개 노드 연결 (planning → aggregate → generate)
   - Checkpointer 통합

2. **HITL 패턴 구현**
   - `interrupt()` 함수 사용
   - Checkpointing 지원
   - Parent Graph 통합

3. **Progress Tracking**
   - 6단계 진행 상황 추적
   - WebSocket 실시간 업데이트
   - `_update_step_progress()` 메서드

4. **State 관리**
   - MainSupervisorState 사용
   - HITL 관련 필드 정의
   - team_results 통합

#### 10.1.2 🚧 TODO 부분

1. **LLM 통합**
   - 키워드 추출
   - 문서 타입 결정
   - 검색 결과 집계
   - 사용자 피드백 통합
   - 문서 생성

2. **툴 통합**
   - LeaseContractGeneratorTool
   - ValidationTool
   - ComplianceTool
   - SearchExecutor 결과 활용

3. **Mock 메서드 교체**
   - `_extract_keywords()` → LLM 기반
   - `_mock_search()` → 실제 검색
   - `_aggregate_results()` → LLM 기반
   - `_apply_user_feedback()` → LLM 기반
   - `_format_document()` → LLM + 툴

4. **에러 처리**
   - Interrupt timeout
   - LLM 실패 fallback
   - 툴 실패 처리

### 10.2 개선 제안

#### 10.2.1 LLM 통합 우선순위

**Priority 1 (핵심 기능):**

1. **문서 타입 결정** (planning_node)
   ```python
   # Prompt: llm_manager/prompts/execution/document_type_determination.txt
   result = await self.llm_service.complete_json_async(
       prompt_name="document_type_determination",
       variables={"query": query}
   )
   ```

2. **문서 생성** (generate_node)
   ```python
   # Prompt: llm_manager/prompts/execution/document_generation.txt
   result = await self.llm_service.complete_async(
       prompt_name="document_generation",
       variables={
           "content": aggregated_content,
           "document_type": doc_type
       }
   )
   ```

**Priority 2 (품질 향상):**

3. **검색 결과 집계** (aggregate_node)
   ```python
   # Prompt: llm_manager/prompts/execution/document_aggregation.txt
   result = await self.llm_service.complete_async(
       prompt_name="document_aggregation",
       variables={"search_results": search_results}
   )
   ```

4. **사용자 피드백 통합** (aggregate_node)
   ```python
   # Prompt: llm_manager/prompts/execution/apply_user_feedback.txt
   result = await self.llm_service.complete_async(
       prompt_name="apply_user_feedback",
       variables={
           "original_content": content,
           "user_feedback": feedback
       }
   )
   ```

#### 10.2.2 툴 통합 로드맵

**Phase 1: LeaseContractGeneratorTool**

```python
# 1. Tool 가용성 확인
def __init__(self, ...):
    try:
        from app.service_agent.tools import LeaseContractGeneratorTool
        self.lease_tool = LeaseContractGeneratorTool()
        logger.info("LeaseContractGeneratorTool initialized")
    except Exception as e:
        logger.warning(f"LeaseContractGeneratorTool unavailable: {e}")
        self.lease_tool = None

# 2. generate_node에서 사용
if doc_type == "lease_contract" and self.lease_tool:
    params = self._extract_lease_params(aggregated_content)
    result = await self.lease_tool.execute(**params)
    final_document = result["content"]
else:
    # Fallback: LLM 기반
    final_document = await self._format_document_with_llm(...)
```

**Phase 2: SearchExecutor 결과 활용**

```python
# aggregate_node 수정
search_results = state.get("team_results", {}).get("search", {}).get("data", {})

if search_results:
    # SearchExecutor의 결과 사용
    legal_results = search_results.get("legal_results", [])
    aggregated_content = self._aggregate_legal_results(legal_results)
else:
    # 자체 검색 (현재 Mock)
    search_results = self._mock_search(keywords)
    aggregated_content = self._aggregate_results(search_results)
```

**Phase 3: ValidationTool 및 ComplianceTool**

```python
# generate_node에서 사용
from app.service_agent.tools import DocumentValidationTool, ComplianceTool

# 1. 검증
validation_result = await validation_tool.validate(final_document, doc_type)
if validation_result["has_errors"]:
    final_document = await self._fix_validation_errors(...)

# 2. 법률 준수 확인
compliance_result = await compliance_tool.check(final_document, doc_type)
if not compliance_result["is_compliant"]:
    final_document = await self._add_compliance_clauses(...)
```

#### 10.2.3 에러 처리 개선

**1. Interrupt Timeout 추가**

```python
# chat_api.py
INTERRUPT_TIMEOUT = 300  # 5분

_interrupted_sessions[session_id] = {
    "config": config,
    "timeout_task": asyncio.create_task(_handle_timeout(session_id))
}

async def _handle_timeout(session_id: str):
    await asyncio.sleep(INTERRUPT_TIMEOUT)
    session_data = _interrupted_sessions.get(session_id)
    if session_data:
        # 자동 거부
        await supervisor.app.ainvoke(
            Command(resume={"action": "reject", "reason": "timeout"}),
            config=session_data["config"]
        )
        _interrupted_sessions.pop(session_id, None)
```

**2. LLM 실패 Fallback**

```python
# aggregate_node
try:
    aggregated_content = await self._aggregate_with_llm(search_results)
except Exception as e:
    logger.warning(f"LLM aggregation failed: {e}, using fallback")
    aggregated_content = self._aggregate_results(search_results)  # Simple concat
```

**3. 툴 실패 처리**

```python
# generate_node
if doc_type == "lease_contract" and self.lease_tool:
    try:
        result = await self.lease_tool.execute(**params)
        if result["status"] == "success":
            final_document = result["content"]
        else:
            # Fallback
            final_document = await self._format_document_with_llm(...)
    except Exception as e:
        logger.error(f"LeaseContractGeneratorTool failed: {e}")
        final_document = await self._format_document_with_llm(...)
else:
    final_document = await self._format_document_with_llm(...)
```

#### 10.2.4 코드 구조 개선

**1. 헬퍼 메서드 분리**

```python
# 현재: 모든 헬퍼 메서드가 DocumentExecutor 클래스에 포함

# 제안: 별도 모듈로 분리
# document_helpers.py
class DocumentKeywordExtractor:
    def extract(self, query: str) -> List[str]:
        ...

class DocumentAggregator:
    def aggregate(self, search_results: List[Dict]) -> str:
        ...

# document_executor.py
from .document_helpers import DocumentKeywordExtractor, DocumentAggregator

class DocumentExecutor:
    def __init__(self, ...):
        self.keyword_extractor = DocumentKeywordExtractor(self.llm_service)
        self.aggregator = DocumentAggregator(self.llm_service)
```

**2. Prompt 관리 개선**

```python
# 현재: 하드코딩된 prompt_name

# 제안: Enum으로 관리
from enum import Enum

class DocumentPrompt(str, Enum):
    KEYWORD_EXTRACTION = "document_keyword_extraction"
    TYPE_DETERMINATION = "document_type_determination"
    AGGREGATION = "document_aggregation"
    FEEDBACK_APPLICATION = "apply_user_feedback"
    GENERATION = "document_generation"

# 사용
result = await self.llm_service.complete_json_async(
    prompt_name=DocumentPrompt.TYPE_DETERMINATION,
    variables={"query": query}
)
```

**3. Configuration 추가**

```python
# document_executor_config.py
from dataclasses import dataclass

@dataclass
class DocumentExecutorConfig:
    enable_llm: bool = True
    enable_validation: bool = True
    enable_compliance: bool = True
    interrupt_timeout: int = 300  # seconds
    max_search_results: int = 10
    default_document_type: str = "general"

# document_executor.py
class DocumentExecutor:
    def __init__(self, llm_context=None, checkpointer=None, progress_callback=None, config=None):
        self.config = config or DocumentExecutorConfig()
        # ...
```

#### 10.2.5 테스트 추가

**1. Unit Tests**

```python
# tests/test_document_executor.py
import pytest
from app.service_agent.execution_agents.document_executor import DocumentExecutor

@pytest.mark.asyncio
async def test_planning_node():
    executor = DocumentExecutor()

    state = {
        "query": "전세 계약서 작성해줘"
    }

    result = await executor.planning_node(state)

    assert "planning_result" in result
    assert result["planning_result"]["document_type"] == "general"
    assert len(result["planning_result"]["search_keywords"]) > 0

@pytest.mark.asyncio
async def test_aggregate_node_mock():
    executor = DocumentExecutor()

    state = {
        "planning_result": {
            "search_keywords": ["전세", "계약서"]
        }
    }

    # Mock interrupt (return immediately)
    # TODO: Mock langgraph.types.interrupt

    result = await executor.aggregate_node(state)

    assert "aggregated_content" in result
    assert "workflow_status" in result
```

**2. Integration Tests**

```python
# tests/test_document_executor_integration.py
@pytest.mark.asyncio
async def test_full_workflow():
    from app.service_agent.foundation.checkpointer import create_checkpointer

    checkpointer = await create_checkpointer()
    executor = DocumentExecutor(checkpointer=checkpointer)

    workflow = executor.build_workflow()

    initial_state = {
        "query": "전세 계약서 작성해줘",
        "session_id": "test_session"
    }

    # Run until interrupt
    config = {"configurable": {"thread_id": "test_session"}}

    # TODO: Mock interrupt handling
```

**3. HITL Tests**

```python
# tests/test_document_executor_hitl.py
@pytest.mark.asyncio
async def test_hitl_approval():
    # 1. Run until interrupt
    # 2. Get state snapshot
    # 3. Resume with approve
    # 4. Verify final_document generated
    ...

@pytest.mark.asyncio
async def test_hitl_modification():
    # 1. Run until interrupt
    # 2. Resume with modify + feedback
    # 3. Verify feedback applied
    ...

@pytest.mark.asyncio
async def test_hitl_rejection():
    # 1. Run until interrupt
    # 2. Resume with reject
    # 3. Verify workflow terminated
    ...
```

### 10.3 성능 최적화 제안

#### 10.3.1 SearchExecutor 결과 재사용

**현재**: DocumentExecutor가 독립적으로 검색 수행 (Mock)

**제안**: Supervisor가 SearchExecutor 먼저 실행, DocumentExecutor가 결과 재사용

```python
# team_supervisor.py
async def _execute_teams_sequential(self, teams, shared_state, main_state):
    for team_name in teams:
        if team_name == "search":
            # SearchExecutor 먼저 실행
            result = await self._execute_single_team("search", shared_state, main_state)
            main_state["team_results"]["search"] = result

        elif team_name == "document":
            # SearchExecutor 결과 활용
            # DocumentExecutor는 team_results["search"]에서 데이터 로드
            result = await self._execute_single_team("document", shared_state, main_state)
            main_state["team_results"]["document"] = result
```

**효과:**
- 중복 검색 제거
- 검색 시간 절약 (5-10초)
- 일관된 데이터 사용

#### 10.3.2 LLM 캐싱

```python
# llm_service.py에 캐싱 추가
class LLMService:
    def __init__(self, ...):
        self.cache = {}  # {prompt_hash: result}

    async def complete_json_async(self, prompt_name, variables, **kwargs):
        # Cache key 생성
        cache_key = self._generate_cache_key(prompt_name, variables)

        if cache_key in self.cache:
            logger.info(f"LLM cache hit: {prompt_name}")
            return self.cache[cache_key]

        # LLM 호출
        result = await self._call_llm(...)

        # 캐싱
        self.cache[cache_key] = result

        return result
```

#### 10.3.3 병렬 처리

**현재**: 모든 단계가 순차 실행

**제안**: 독립적인 작업 병렬 처리

```python
# aggregate_node에서 검색 + 검증 병렬 실행
import asyncio

# 병렬 실행
search_task = asyncio.create_task(self._search_legal_db(keywords))
validation_task = asyncio.create_task(self._validate_planning(planning_result))

search_results, validation_result = await asyncio.gather(search_task, validation_task)
```

---

## 📊 부록

### A. 파일 구조

```
document_executor.py (539줄)
│
├─ Imports (1-25)
│   ├─ logging
│   ├─ typing
│   ├─ langgraph.graph (StateGraph, START, END)
│   ├─ langgraph.types (interrupt)
│   └─ separated_states (MainSupervisorState)
│
├─ DocumentExecutor 클래스 (30-520)
│   │
│   ├─ __init__ (44-56)
│   │   ├─ llm_context
│   │   ├─ checkpointer
│   │   └─ progress_callback
│   │
│   ├─ build_workflow (58-90)
│   │   ├─ StateGraph 생성
│   │   ├─ 노드 추가
│   │   ├─ 엣지 정의
│   │   └─ compile (checkpointer 포함)
│   │
│   ├─ 노드 메서드 (94-326)
│   │   ├─ planning_node (94-142)
│   │   ├─ aggregate_node (144-245)
│   │   └─ generate_node (247-326)
│   │
│   ├─ 헬퍼 메서드 (330-475)
│   │   ├─ _extract_keywords (330-346)
│   │   ├─ _mock_search (348-377)
│   │   ├─ _aggregate_results (379-405)
│   │   ├─ _apply_user_feedback (407-429)
│   │   └─ _format_document (431-475)
│   │
│   └─ Progress Tracking (477-520)
│       └─ _update_step_progress (477-520)
│
└─ Public API (524-539)
    └─ build_document_workflow (524-539)
```

### B. State 필드 참조

**MainSupervisorState (Document 관련 필드):**

| 필드 | 타입 | 노드 | 설명 |
|------|------|------|------|
| `query` | str | Input | 사용자 쿼리 |
| `session_id` | str | Input | WebSocket session ID |
| `planning_result` | Dict | planning_node | 문서 계획 결과 |
| `aggregated_content` | str | aggregate_node | 집계된 내용 |
| `collaboration_result` | Dict | aggregate_node | HITL 사용자 피드백 |
| `workflow_status` | str | All | "running" \| "interrupted" \| "completed" |
| `interrupted_by` | str | aggregate_node | "aggregate" |
| `interrupt_type` | str | aggregate_node | "approval" |
| `final_document` | str | generate_node | 최종 문서 |
| `final_response` | Dict | generate_node | 최종 응답 |
| `team_results` | Dict | generate_node | Parent Graph 통합 |

### C. WebSocket 메시지 참조

**1. agent_step_progress**

```json
{
    "type": "agent_step_progress",
    "agentName": "document",
    "agentType": "document",
    "stepId": "document_step_1",
    "stepIndex": 0,
    "status": "in_progress",
    "progress": 0,
    "timestamp": "2025-11-02T14:30:00.123Z"
}
```

**2. workflow_interrupted**

```json
{
    "type": "workflow_interrupted",
    "interrupted_by": "aggregate",
    "interrupt_type": "approval",
    "interrupt_data": {
        "aggregated_content": "...",
        "search_results_count": 5,
        "message": "Please review the aggregated content before final document generation.",
        "options": {
            "approve": "Continue with document generation",
            "modify": "Provide feedback for modification",
            "reject": "Cancel document generation"
        },
        "_metadata": {
            "interrupted_by": "aggregate",
            "interrupt_type": "approval",
            "node_name": "document_team.aggregate"
        }
    },
    "message": "워크플로우가 사용자 승인을 기다리고 있습니다.",
    "timestamp": "2025-11-02T14:30:05.456Z"
}
```

**3. interrupt_response (Client → Server)**

```json
{
    "type": "interrupt_response",
    "action": "modify",
    "feedback": {
        "modifications": "보증금 금액을 5억으로 수정"
    }
}
```

**4. final_response**

```json
{
    "type": "final_response",
    "response": {
        "answer": "# Document: GENERAL\n\n...",
        "document_type": "general",
        "user_approved": true,
        "user_action": "modify",
        "modifications_applied": true,
        "type": "document"
    },
    "timestamp": "2025-11-02T14:30:15.789Z"
}
```

### D. 참조 파일 목록

| 파일 | 경로 | 역할 |
|------|------|------|
| document_executor.py | backend/app/service_agent/execution_agents/ | DocumentExecutor 클래스 |
| separated_states.py | backend/app/service_agent/foundation/ | State 정의 |
| checkpointer.py | backend/app/service_agent/foundation/ | Checkpointer 관리 |
| team_supervisor.py | backend/app/service_agent/supervisor/ | Supervisor 통합 |
| chat_api.py | backend/app/api/ | WebSocket API |
| lease_contract_generator_tool.py | backend/app/service_agent/tools/ | 계약서 생성 툴 |
| search_executor.py | backend/app/service_agent/execution_agents/ | SearchExecutor (비교용) |

---

**문서 작성 완료**

- **작성일**: 2025-11-02
- **분석 대상**: DocumentExecutor (document_executor.py)
- **분석 범위**: 전체 (구조, 워크플로우, HITL, State, Progress, Tools)
- **상태**: 100% 완료

---
