# Nested Graph + HITL 완전 가이드

**작성일**: 2025-11-03
**대상**: Octostrator 3-Level Graph 구조 (Main → Sub → Sub-Sub)
**목적**: Nested Graph 환경에서 HITL (Human-in-the-Loop) 구현 방법 완전 정리

---

## 1. 개요

### 1.1 Octostrator의 3-Level Graph 구조

```
Main Graph (Supervisor)
  └─ Sub Graph (Domain Agent, e.g., Analysis Agent)
       └─ Sub-Sub Graph (Specialized Tool, e.g., SQL Query Agent)
```

**각 레벨의 역할**:

| 레벨 | 그래프 이름 | 역할 | HITL 사용 사례 |
|------|------------|------|----------------|
| **Level 1** | Main Graph | 전체 워크플로우 관리 (Intent → Planning → Execution) | 전체 계획 승인, 최종 결과 확인 |
| **Level 2** | Sub Graph | 도메인별 Agent (분석, 비교, 문서 생성 등) | 중간 분석 결과 확인, 데이터 검증 |
| **Level 3** | Sub-Sub Graph | 세부 도구 (SQL 쿼리, API 호출, 파일 처리 등) | 위험한 작업 승인 (DELETE 쿼리, 파일 삭제) |

### 1.2 HITL의 핵심 과제

Nested Graph 환경에서 HITL을 구현할 때 해결해야 할 과제:

1. **State 전파**: Sub/Sub-Sub Graph의 HITL 상태를 Main Graph까지 전달
2. **Checkpointer 통합**: 어느 레벨에서 State를 저장할 것인가?
3. **Resume 메커니즘**: 사용자 응답 후 어느 지점에서 재개할 것인가?
4. **Thread 관리**: 각 레벨의 thread_id를 어떻게 관리할 것인가?

### 1.3 권장 아키텍처

**Main Graph에서만 Checkpointer 사용**:
- Sub/Sub-Sub Graph는 단순 함수로 실행
- HITL 발생 시 State를 Main Graph로 전파
- Main Graph에서 Checkpointer로 저장하고 대기
- 사용자 응답 후 Main Graph에서 재개 → Sub/Sub-Sub Graph로 전달

**장점**:
- Checkpointer 관리 단순화 (Main Graph 하나만)
- State 일관성 보장
- Resume 로직 중앙화

---

## 2. Level 1: Main Graph HITL

### 2.1 개념

Main Graph에서 직접 HITL을 호출하는 경우입니다.

**사용 사례**:
- 전체 계획(Plan) 승인 요청
- 최종 결과 확인
- 위험한 전체 작업 승인 (예: 모든 데이터 삭제)

### 2.2 구현

```python
# backend/app/octostrator/nodes/hitl_handler.py

from typing import Dict
from langchain_core.messages import AIMessage
from langgraph.types import Command, interrupt
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def hitl_handler_node(state: SupervisorState) -> Dict:
    """Main Graph HITL Handler

    Phase 4: Checkpointer와 통합하여 실제 대기/재개 구현
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # HITL 질문 가져오기
    question = step.get("hitl_question", "승인해주세요")

    # Phase 4: interrupt()로 실행 중단
    # Checkpointer가 현재 State를 저장하고 대기
    user_response = interrupt({
        "type": "hitl_request",
        "question": question,
        "step_id": step["step_id"],
        "context": {
            "agent": step["agent"],
            "description": step["description"]
        }
    })

    # 사용자 응답 받은 후 재개됨
    plan[current_step]["status"] = "completed"
    plan[current_step]["hitl_response"] = user_response
    plan[current_step]["result"] = f"HITL: {question} - 사용자 응답: {user_response}"

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "is_waiting_human": False,
        "messages": [
            AIMessage(content=f"[HITL] 사용자 응답 받음: {user_response}")
        ]
    }
```

### 2.3 FastAPI 엔드포인트

```python
# backend/app/api/endpoints/hitl.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.octostrator.supervisor.graph import graph, checkpointer

router = APIRouter(prefix="/hitl", tags=["HITL"])


class HITLResumeRequest(BaseModel):
    thread_id: str
    user_response: str


@router.post("/resume")
async def resume_hitl(request: HITLResumeRequest):
    """HITL 재개 - 사용자 응답을 받아서 그래프 실행 재개

    Args:
        thread_id: 중단된 세션의 thread_id
        user_response: 사용자 응답 (승인/거부/수정 요청 등)

    Returns:
        재개된 그래프의 실행 결과
    """
    try:
        # Checkpointer에서 State 복원
        config = {"configurable": {"thread_id": request.thread_id}}

        # 그래프 재개 (user_response를 Command로 전달)
        result = await graph.ainvoke(
            Command(resume=request.user_response),
            config=config
        )

        return {
            "status": "resumed",
            "result": result.get("final_result"),
            "is_waiting_human": result.get("is_waiting_human", False)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HITL resume failed: {str(e)}")


@router.get("/status/{thread_id}")
async def get_hitl_status(thread_id: str):
    """HITL 상태 확인 - 현재 어떤 질문으로 대기 중인지 확인"""
    try:
        config = {"configurable": {"thread_id": thread_id}}

        # Checkpointer에서 현재 State 조회
        state = await graph.aget_state(config)

        if not state:
            raise HTTPException(status_code=404, detail="Thread not found")

        # HITL 대기 중인지 확인
        if state.values.get("is_waiting_human"):
            plan = state.values.get("plan", [])
            current_step = state.values.get("current_step", 0)

            if current_step < len(plan):
                step = plan[current_step]
                return {
                    "is_waiting": True,
                    "question": step.get("hitl_question", "승인해주세요"),
                    "step_id": step["step_id"],
                    "context": {
                        "agent": step["agent"],
                        "description": step["description"]
                    }
                }

        return {"is_waiting": False}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
```

### 2.4 사용 예시

**Step 1: 그래프 실행**

```python
# 클라이언트에서 요청
result = await graph.ainvoke(
    {
        "messages": [HumanMessage(content="지난 분기 매출 분석해줘")],
        "output_format": "chat"
    },
    config={"configurable": {"thread_id": "session-123"}}
)

# HITL에서 중단됨
# result에는 중단 정보 포함
```

**Step 2: Frontend에서 사용자에게 질문 표시**

```javascript
// Frontend (React/Vue)
const response = await fetch('/api/hitl/status/session-123')
const data = await response.json()

if (data.is_waiting) {
    // 사용자에게 질문 표시
    showConfirmDialog(data.question, data.context)
}
```

**Step 3: 사용자 응답 후 재개**

```javascript
// 사용자가 "승인" 버튼 클릭
const resumeResponse = await fetch('/api/hitl/resume', {
    method: 'POST',
    body: JSON.stringify({
        thread_id: 'session-123',
        user_response: '승인합니다'
    })
})

const result = await resumeResponse.json()
// 그래프 실행 계속됨
```

---

## 3. Level 2: Sub Graph HITL

### 3.1 개념

Sub Graph (Domain Agent)에서 HITL을 호출하는 경우입니다.

**사용 사례**:
- 분석 Agent에서 중간 결과 확인
- 비교 Agent에서 비교 기준 승인
- 문서 Agent에서 초안 검토

### 3.2 구조

```
Main Graph
  └─ Executor
       └─ Analysis Agent (Sub Graph)
            ├─ Data Collection
            ├─ Analysis
            ├─ HITL (중간 결과 확인) ← 여기서 중단
            └─ Final Report
```

### 3.3 구현

**Sub Graph 정의**:

```python
# backend/app/octostrator/agents/analysis_agent/graph.py

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from typing import TypedDict


class AnalysisAgentState(TypedDict):
    """Analysis Agent의 State"""
    input_data: str
    analysis_result: dict
    user_confirmation: str
    final_report: str


async def collect_data_node(state: AnalysisAgentState) -> dict:
    """데이터 수집"""
    # 데이터 수집 로직
    return {"input_data": "수집된 데이터..."}


async def analyze_node(state: AnalysisAgentState) -> dict:
    """데이터 분석"""
    # 분석 로직
    return {"analysis_result": {"trend": "증가", "percentage": 15}}


async def hitl_node(state: AnalysisAgentState) -> dict:
    """HITL - 중간 결과 확인

    Sub Graph에서 interrupt() 호출 → Main Graph로 전파
    """
    analysis_result = state["analysis_result"]

    # interrupt() 호출
    # Main Graph의 Checkpointer가 저장함
    user_confirmation = interrupt({
        "type": "sub_graph_hitl",
        "sub_graph": "analysis_agent",
        "question": f"분석 결과를 확인해주세요: {analysis_result}",
        "data": analysis_result
    })

    return {"user_confirmation": user_confirmation}


async def generate_report_node(state: AnalysisAgentState) -> dict:
    """최종 보고서 생성"""
    return {"final_report": "최종 분석 보고서..."}


def build_analysis_agent_graph():
    """Analysis Agent Sub Graph 생성"""
    workflow = StateGraph(AnalysisAgentState)

    workflow.add_node("collect_data", collect_data_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("hitl", hitl_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.add_edge(START, "collect_data")
    workflow.add_edge("collect_data", "analyze")
    workflow.add_edge("analyze", "hitl")
    workflow.add_edge("hitl", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()
```

**Main Graph와 통합**:

```python
# backend/app/octostrator/agents/analysis_agent_node.py

from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.agents.analysis_agent.graph import build_analysis_agent_graph


async def analysis_agent_node(state: SupervisorState) -> dict:
    """Analysis Agent - Sub Graph 실행

    Sub Graph에서 HITL 발생 시 Main Graph로 전파됨
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # Sub Graph 생성
    sub_graph = build_analysis_agent_graph()

    # Sub Graph 실행
    # interrupt()가 호출되면 Main Graph로 전파됨
    sub_result = await sub_graph.ainvoke({
        "input_data": step["description"]
    })

    # Sub Graph 완료 후 결과 저장
    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = sub_result["final_report"]

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=f"[Analysis Agent] {sub_result['final_report']}")]
    }
```

### 3.4 핵심 원리

**interrupt() 전파**:
- Sub Graph에서 `interrupt()` 호출
- LangGraph는 자동으로 이를 Parent Graph (Main Graph)로 전파
- Main Graph의 Checkpointer가 현재 State 저장
- Frontend는 Main Graph의 thread_id로 상태 조회 및 재개

**State 관리**:
- Sub Graph의 State는 독립적
- HITL 응답은 `interrupt()`의 반환값으로 받음
- Main Graph는 Sub Graph의 State를 알 필요 없음

---

## 4. Level 3: Sub-Sub Graph HITL

### 4.1 개념

Sub-Sub Graph (Specialized Tool)에서 HITL을 호출하는 경우입니다.

**사용 사례**:
- SQL Query Agent에서 DELETE 쿼리 승인
- File Agent에서 파일 삭제 승인
- API Agent에서 외부 API 호출 승인

### 4.2 구조

```
Main Graph
  └─ Executor
       └─ Analysis Agent (Sub Graph)
            └─ SQL Query Agent (Sub-Sub Graph)
                 ├─ Query Validation
                 ├─ HITL (위험한 쿼리 승인) ← 여기서 중단
                 └─ Query Execution
```

### 4.3 구현

**Sub-Sub Graph 정의**:

```python
# backend/app/octostrator/agents/analysis_agent/tools/sql_agent.py

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from typing import TypedDict


class SQLAgentState(TypedDict):
    """SQL Agent의 State"""
    query: str
    is_dangerous: bool
    user_approval: str
    result: dict


async def validate_query_node(state: SQLAgentState) -> dict:
    """쿼리 검증"""
    query = state["query"]

    # 위험한 쿼리 감지
    is_dangerous = any(keyword in query.upper() for keyword in ["DELETE", "DROP", "TRUNCATE"])

    return {"is_dangerous": is_dangerous}


async def hitl_approval_node(state: SQLAgentState) -> dict:
    """HITL - 위험한 쿼리 승인

    Sub-Sub Graph → Sub Graph → Main Graph로 전파
    """
    query = state["query"]

    # interrupt() 호출
    user_approval = interrupt({
        "type": "sub_sub_graph_hitl",
        "sub_graph": "analysis_agent",
        "sub_sub_graph": "sql_agent",
        "question": f"⚠️ 위험한 쿼리입니다. 실행하시겠습니까?\n\n{query}",
        "data": {"query": query, "risk_level": "high"}
    })

    return {"user_approval": user_approval}


async def execute_query_node(state: SQLAgentState) -> dict:
    """쿼리 실행"""
    # 실제 쿼리 실행 로직
    return {"result": {"rows_affected": 100}}


def should_ask_approval(state: SQLAgentState) -> str:
    """위험한 쿼리인 경우 HITL로 분기"""
    if state["is_dangerous"]:
        return "hitl_approval"
    else:
        return "execute_query"


def build_sql_agent_graph():
    """SQL Agent Sub-Sub Graph 생성"""
    workflow = StateGraph(SQLAgentState)

    workflow.add_node("validate_query", validate_query_node)
    workflow.add_node("hitl_approval", hitl_approval_node)
    workflow.add_node("execute_query", execute_query_node)

    workflow.add_edge(START, "validate_query")

    # Conditional Edge: 위험한 쿼리면 HITL, 아니면 바로 실행
    workflow.add_conditional_edges(
        "validate_query",
        should_ask_approval,
        {
            "hitl_approval": "hitl_approval",
            "execute_query": "execute_query"
        }
    )

    workflow.add_edge("hitl_approval", "execute_query")
    workflow.add_edge("execute_query", END)

    return workflow.compile()
```

**Sub Graph와 통합**:

```python
# backend/app/octostrator/agents/analysis_agent/graph.py (수정)

from backend.app.octostrator.agents.analysis_agent.tools.sql_agent import build_sql_agent_graph


async def analyze_node(state: AnalysisAgentState) -> dict:
    """데이터 분석 - SQL Agent 호출"""

    # Sub-Sub Graph 실행
    sql_agent = build_sql_agent_graph()

    sql_result = await sql_agent.ainvoke({
        "query": "DELETE FROM old_data WHERE date < '2024-01-01'"
    })

    # SQL 실행 결과로 분석 수행
    return {
        "analysis_result": {
            "sql_result": sql_result["result"],
            "trend": "증가",
            "percentage": 15
        }
    }
```

### 4.4 HITL 전파 흐름

```
1. Sub-Sub Graph (SQL Agent)에서 interrupt() 호출
   ↓
2. Sub Graph (Analysis Agent)로 전파
   ↓
3. Main Graph (Supervisor)로 전파
   ↓
4. Main Graph의 Checkpointer가 State 저장
   ↓
5. Frontend는 Main Graph의 thread_id로 상태 조회
   ↓
6. 사용자 응답 후 Main Graph에서 재개
   ↓
7. Sub Graph로 재개 신호 전달
   ↓
8. Sub-Sub Graph로 재개 신호 전달
   ↓
9. SQL 쿼리 실행
```

**핵심**: 모든 레벨의 interrupt()가 **Main Graph의 Checkpointer**로 수렴됩니다.

---

## 5. Checkpointer 통합

### 5.1 AsyncPostgresSaver 설정

```python
# backend/app/octostrator/supervisor/graph.py

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from backend.app.config.system import config


async def get_checkpointer():
    """Checkpointer 생성"""
    connection_string = f"postgresql://{config.postgres_user}:{config.postgres_password}@{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"

    # AsyncPostgresSaver 생성
    async with await AsyncConnection.connect(connection_string) as conn:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()  # 테이블 생성
        return checkpointer


def build_supervisor_graph(context: Optional[AppContext] = None):
    """Supervisor Graph 생성 - Checkpointer 통합"""

    # ... 기존 코드 ...

    # Checkpointer 설정
    checkpointer = await get_checkpointer()

    # 그래프 컴파일 (Checkpointer 포함)
    return workflow.compile(checkpointer=checkpointer)
```

### 5.2 Thread 관리

**Thread ID 생성 규칙**:

```python
# backend/app/utils/thread_manager.py

import uuid
from datetime import datetime


def generate_thread_id(user_id: str, session_type: str = "main") -> str:
    """Thread ID 생성

    Args:
        user_id: 사용자 ID
        session_type: 세션 타입 ("main", "analysis", etc.)

    Returns:
        thread_id: "{user_id}_{session_type}_{timestamp}_{uuid}"
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]

    return f"{user_id}_{session_type}_{timestamp}_{unique_id}"


# 사용 예시
thread_id = generate_thread_id("user123", "main")
# "user123_main_20251103143000_a1b2c3d4"
```

### 5.3 State 저장 및 복원

**저장** (자동):

```python
# interrupt() 호출 시 자동 저장
user_response = interrupt({"question": "승인하시겠습니까?"})
# Checkpointer가 자동으로 현재 State를 PostgreSQL에 저장
```

**복원** (수동):

```python
# FastAPI 엔드포인트에서 복원
config = {"configurable": {"thread_id": "user123_main_20251103143000_a1b2c3d4"}}

# State 조회
state = await graph.aget_state(config)

# 그래프 재개
result = await graph.ainvoke(
    Command(resume="승인합니다"),
    config=config
)
```

---

## 6. 실전 예제: 3-Level HITL 완전 시나리오

### 6.1 시나리오

사용자 요청: **"지난 분기 매출 데이터를 분석하되, 2024년 이전 데이터는 삭제해줘"**

**실행 흐름**:

```
1. Main Graph: Planning
   → Plan 생성: [search, analysis, cleanup]

2. Main Graph: HITL (Level 1)
   → 질문: "3단계 계획을 승인하시겠습니까?"
   → 사용자: "승인"

3. Sub Graph (Analysis Agent): 실행
   → Sub-Sub Graph (SQL Agent) 호출

4. Sub-Sub Graph (SQL Agent): HITL (Level 3)
   → 질문: "⚠️ DELETE 쿼리를 실행하시겠습니까?"
   → 사용자: "승인"

5. Sub-Sub Graph: DELETE 실행

6. Sub Graph: 분석 완료, HITL (Level 2)
   → 질문: "분석 결과를 확인해주세요"
   → 사용자: "확인"

7. Main Graph: 최종 결과 생성
```

### 6.2 코드 구현

**Step 1: Main Graph Planning + HITL**

```python
# Planning Node가 자동으로 Plan 생성
plan = [
    {"step_id": 0, "agent": "hitl", "description": "전체 계획 승인", "hitl_question": "3단계 계획을 승인하시겠습니까?"},
    {"step_id": 1, "agent": "search", "description": "매출 데이터 검색"},
    {"step_id": 2, "agent": "analysis", "description": "데이터 분석 (Sub Graph)"},
    {"step_id": 3, "agent": "cleanup", "description": "이전 데이터 정리"},
]

# Executor → HITL Handler (Level 1)
# interrupt() 호출, Main Graph 중단
```

**Step 2: Analysis Agent 실행**

```python
# Executor → analysis_agent_node
async def analysis_agent_node(state: SupervisorState) -> dict:
    sub_graph = build_analysis_agent_graph()

    # Sub Graph 실행
    sub_result = await sub_graph.ainvoke({
        "input_data": "매출 데이터 분석 + 이전 데이터 삭제"
    })

    # Sub Graph 내부에서 SQL Agent 호출
    # → HITL (Level 3) 발생
    # → Main Graph로 전파
```

**Step 3: SQL Agent HITL**

```python
# Sub-Sub Graph: SQL Agent
async def hitl_approval_node(state: SQLAgentState) -> dict:
    query = "DELETE FROM sales WHERE date < '2024-01-01'"

    # interrupt() 호출 (Level 3)
    user_approval = interrupt({
        "type": "sub_sub_graph_hitl",
        "sub_graph": "analysis_agent",
        "sub_sub_graph": "sql_agent",
        "question": f"⚠️ 위험한 쿼리입니다. 실행하시겠습니까?\n\n{query}",
        "data": {"query": query, "risk_level": "high"}
    })

    # Main Graph로 전파 → Checkpointer 저장
```

**Step 4: Frontend 처리**

```javascript
// Frontend: HITL 상태 폴링
const checkHITL = async () => {
    const response = await fetch(`/api/hitl/status/${threadId}`)
    const data = await response.json()

    if (data.is_waiting) {
        if (data.type === "sub_sub_graph_hitl") {
            // 위험한 작업 경고 표시
            showDangerAlert(data.question, data.data)
        } else {
            showConfirmDialog(data.question)
        }
    }
}

// 사용자 승인 후
const approve = async () => {
    await fetch('/api/hitl/resume', {
        method: 'POST',
        body: JSON.stringify({
            thread_id: threadId,
            user_response: '승인합니다'
        })
    })

    // 그래프 재개 → SQL 실행
}
```

### 6.3 전체 메시지 흐름

```
[Client] POST /api/chat
         {"message": "지난 분기 매출 데이터 분석하고 이전 데이터 삭제해줘"}

[Main Graph] Planning → Plan 생성 (4 steps)
[Main Graph] Executor → Step 0 (HITL)
[Main Graph] HITL Handler → interrupt() 호출
             Checkpointer: State 저장 (중단)

[Client] GET /api/hitl/status/thread-123
         Response: {"is_waiting": true, "question": "3단계 계획 승인?"}

[Client] 사용자 승인 클릭

[Client] POST /api/hitl/resume
         {"thread_id": "thread-123", "user_response": "승인"}

[Main Graph] 재개 → Step 1 (Search)
[Main Graph] Executor → Step 2 (Analysis Agent)
[Sub Graph] Analysis Agent 시작
[Sub Graph] SQL Agent 호출
[Sub-Sub Graph] SQL Agent → Validate Query
[Sub-Sub Graph] is_dangerous = True → HITL
[Sub-Sub Graph] interrupt() 호출
                Main Graph로 전파
                Checkpointer: State 저장 (중단)

[Client] GET /api/hitl/status/thread-123
         Response: {"is_waiting": true, "type": "sub_sub_graph_hitl", "question": "⚠️ DELETE 쿼리 실행?"}

[Client] 사용자 승인 클릭

[Client] POST /api/hitl/resume
         {"thread_id": "thread-123", "user_response": "승인"}

[Sub-Sub Graph] 재개 → DELETE 실행
[Sub-Sub Graph] 완료
[Sub Graph] 분석 완료 → HITL (Level 2)
[Sub Graph] interrupt() 호출
            Main Graph로 전파
            Checkpointer: State 저장 (중단)

[Client] GET /api/hitl/status/thread-123
         Response: {"is_waiting": true, "question": "분석 결과 확인?"}

[Client] 사용자 확인 클릭

[Client] POST /api/hitl/resume
         {"thread_id": "thread-123", "user_response": "확인"}

[Sub Graph] 재개 → 최종 보고서 생성
[Sub Graph] 완료
[Main Graph] Executor → Step 3 (Cleanup)
[Main Graph] Executor → 모든 단계 완료
[Main Graph] Aggregator → 결과 구조화
[Main Graph] Chat Generator → 최종 답변 생성
[Main Graph] 완료

[Client] GET /api/chat/result/thread-123
         Response: {"final_result": "분석 완료. 총 100건 삭제됨"}
```

---

## 7. 모범 사례 및 주의사항

### 7.1 모범 사례

1. **Main Graph에만 Checkpointer 설정**
   - Sub/Sub-Sub Graph는 Checkpointer 없이 실행
   - interrupt()가 자동으로 Main Graph로 전파됨

2. **interrupt()에 충분한 컨텍스트 포함**
   ```python
   interrupt({
       "type": "sub_sub_graph_hitl",
       "sub_graph": "analysis_agent",
       "sub_sub_graph": "sql_agent",
       "question": "질문 내용",
       "data": {"query": "...", "risk_level": "high"},
       "metadata": {"timestamp": "..."}
   })
   ```

3. **Thread ID 규칙 준수**
   - 사용자별로 고유한 thread_id 사용
   - 동일 세션에서 일관된 thread_id 유지

4. **State 크기 최소화**
   - Checkpointer는 전체 State를 저장하므로 불필요한 데이터 제거
   - 큰 파일은 S3에 저장하고 State에는 URL만 포함

5. **에러 처리**
   ```python
   try:
       user_response = interrupt({"question": "..."})
   except Exception as e:
       # interrupt() 실패 시 기본값 사용 또는 에러 처리
       user_response = "auto_approved"
   ```

### 7.2 주의사항

1. **Sub Graph에서 Checkpointer 중복 설정 금지**
   - Sub Graph에 Checkpointer를 설정하면 State가 두 번 저장됨
   - Main Graph의 Checkpointer만 사용

2. **interrupt() 반환값 타입 확인**
   - interrupt()는 사용자 응답 문자열을 반환
   - 타입 검증 필수

3. **HITL 타임아웃 처리**
   - 사용자가 응답하지 않을 경우 타임아웃 설정
   - 타임아웃 시 자동 거부 또는 알림

4. **동시 HITL 요청 처리**
   - 한 세션에서 여러 HITL이 동시 발생 가능
   - Frontend에서 순차 처리 또는 큐 관리

---

## 8. 테스트 전략

### 8.1 Level 1 HITL 테스트

```python
# test_level1_hitl.py

import asyncio
from langchain_core.messages import HumanMessage


async def test_level1_hitl():
    """Main Graph HITL 테스트"""

    # 그래프 실행
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="매출 분석해줘")],
            "output_format": "chat"
        },
        config={"configurable": {"thread_id": "test-level1"}}
    )

    # HITL 상태 확인
    state = await graph.aget_state({"configurable": {"thread_id": "test-level1"}})

    assert state.values["is_waiting_human"] == True
    assert "승인" in state.values["plan"][0]["hitl_question"]

    # 재개
    result = await graph.ainvoke(
        Command(resume="승인합니다"),
        config={"configurable": {"thread_id": "test-level1"}}
    )

    assert result["final_result"] is not None


if __name__ == "__main__":
    asyncio.run(test_level1_hitl())
```

### 8.2 Level 3 HITL 테스트

```python
# test_level3_hitl.py

async def test_level3_hitl():
    """Sub-Sub Graph HITL 테스트 (SQL Agent)"""

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="이전 데이터 삭제해줘")],
        },
        config={"configurable": {"thread_id": "test-level3"}}
    )

    # SQL Agent의 HITL 상태 확인
    state = await graph.aget_state({"configurable": {"thread_id": "test-level3"}})

    # interrupt() 메타데이터 확인
    assert state.next == ()  # 중단됨
    assert "DELETE" in state.tasks[0].interrupts[0]["value"]["question"]

    # 재개
    result = await graph.ainvoke(
        Command(resume="승인합니다"),
        config={"configurable": {"thread_id": "test-level3"}}
    )

    assert "삭제 완료" in result["final_result"]
```

---

## 9. 결론

### 9.1 핵심 원칙

1. **Main Graph에만 Checkpointer 설정**
2. **interrupt()는 자동으로 상위 Graph로 전파**
3. **Thread ID는 Main Graph 레벨에서 관리**
4. **모든 HITL은 동일한 FastAPI 엔드포인트로 처리**

### 9.2 장점

- **단순성**: Checkpointer 관리가 중앙화됨
- **일관성**: 모든 레벨의 HITL이 동일한 방식으로 처리됨
- **확장성**: 새로운 Sub-Sub-Sub Graph 추가 시에도 코드 변경 불필요

### 9.3 다음 단계

**Phase 4 구현 계획**:
1. AsyncPostgresSaver 설정 완료
2. Level 1 HITL 구현 및 테스트
3. Level 2 HITL 구현 (Analysis Agent)
4. Level 3 HITL 구현 (SQL Agent)
5. FastAPI 엔드포인트 완성
6. Frontend 통합 테스트

---

**참고 자료**:
- LangGraph Checkpointer: https://langchain-ai.github.io/langgraph/concepts/persistence/
- LangGraph interrupt(): https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/
- AsyncPostgresSaver: https://langchain-ai.github.io/langgraph/reference/checkpoints/
