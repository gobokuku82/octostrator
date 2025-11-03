# Human-in-the-Loop (HITL) Implementation Plan

**Project:** HolmesNyangz Real Estate Chatbot
**Date:** 2025-10-21
**Version:** 1.0.0
**LangGraph Version:** 0.6+ (Command & interrupt support)
**Priority:** 🔴 P0 Critical

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [LangGraph 0.6+ Features](#langgraph-06-features)
3. [Architecture Design](#architecture-design)
4. [Implementation Details](#implementation-details)
5. [Backend Implementation](#backend-implementation)
6. [Frontend Implementation](#frontend-implementation)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Plan](#deployment-plan)
9. [Timeline & Milestones](#timeline--milestones)

---

## 🎯 Executive Summary

### Problem Statement

현재 홈즈냥즈 시스템은 **사용자 승인 없이 중요한 작업을 자동 실행**합니다:
- 계약서 작성/수정
- 법률 검토 결과 제시
- 고액 매물 추천 (10억 이상)
- 투자 의사결정 조언

이는 다음과 같은 리스크를 초래합니다:
- 법률 책임 문제
- 사용자 신뢰도 저하
- 잘못된 결정으로 인한 금전적 손실

### Solution: Human-in-the-Loop

**LangGraph 0.6+의 `interrupt()` 및 `Command` 기능**을 활용하여:
1. 중요 작업 전 사용자 승인 요청
2. 워크플로우 일시 중단
3. 사용자 입력 대기
4. 승인/거부에 따른 분기 처리

### Expected Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| 사용자 신뢰도 | 60% | 95%+ | +58% |
| 법률 리스크 | High | Low | -80% |
| 잘못된 결정 방지 | 0% | 95%+ | +95% |
| 사용자 제어권 | 낮음 | 높음 | +100% |

### Key Deliverables

1. ✅ LangGraph interrupt 기반 승인 메커니즘
2. ✅ Command를 통한 워크플로우 재개
3. ✅ Frontend 승인 UI/UX
4. ✅ WebSocket 실시간 알림
5. ✅ 승인 이력 추적 및 감사

---

## 🔧 LangGraph 0.6+ Features

### 1. interrupt() Function

**개념:**
```python
from langgraph.types import interrupt

def approval_node(state):
    # 워크플로우 일시 중단, 사용자에게 데이터 전달
    user_response = interrupt({
        "action": "계약서 작성",
        "details": {...},
        "risk_level": "high"
    })

    # user_response는 Command(resume=...)로 전달된 값
    return {"approval_status": user_response}
```

**핵심 특징:**
- 그래프 실행을 특정 지점에서 **일시 중단**
- Checkpointer를 통해 **상태 영구 저장**
- `interrupt()` 호출 시 페이로드를 사용자에게 전달
- 재개 시 `Command(resume=...)`로 전달된 값을 반환

**중요 동작 방식:**
> ⚠️ **Critical:** interrupt()를 포함한 **전체 노드가 재실행**됩니다.
> - 노드 시작부터 다시 실행
> - Side effect (API 호출 등)는 interrupt() **이후**에 배치
> - 또는 별도 노드로 분리

### 2. Command Primitive

**기본 사용법:**
```python
from langgraph.types import Command

# 1. 그래프 실행 (interrupt까지)
config = {"configurable": {"thread_id": "session-123"}}
result = graph.invoke({"query": "계약서 작성해줘"}, config=config)

# 2. Interrupt 확인
if "__interrupt__" in result:
    interrupt_data = result["__interrupt__"][0]
    print(interrupt_data.value)  # 사용자에게 보여줄 데이터

# 3. 사용자 승인 후 재개
approved_result = graph.invoke(
    Command(resume="approved"),  # 사용자 입력
    config=config
)
```

**고급 기능:**

**A. 여러 interrupt 동시 처리 (Parallel Interrupts)**
```python
# 여러 노드에서 동시에 interrupt 발생 시
interrupts = result["__interrupt__"]
resume_map = {
    interrupts[0].id: "approved",
    interrupts[1].id: "rejected",
}
graph.invoke(Command(resume=resume_map), config=config)
```

**B. State 업데이트와 함께 재개**
```python
# 사용자가 데이터를 수정한 경우
graph.invoke(
    Command(
        resume="approved",
        update={"modified_price": 500_000_000}  # State 업데이트
    ),
    config=config
)
```

### 3. Checkpointer (필수)

**종류:**

**A. 개발용 (InMemorySaver)**
```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

**B. 프로덕션용 (PostgresSaver)**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def create_checkpointer():
    return await AsyncPostgresSaver.from_conn_string(
        "postgresql://user:pass@localhost/db"
    )

checkpointer = await create_checkpointer()
graph = builder.compile(checkpointer=checkpointer)
```

**홈즈냥즈는 이미 AsyncPostgresSaver 사용 중** ✅
- 위치: `backend/app/service_agent/foundation/checkpointer.py`
- 별도 설정 불필요

---

## 🏗️ Architecture Design

### Overall Flow

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant WS as WebSocket
    participant API as Chat API
    participant S as TeamSupervisor
    participant A as ApprovalNode
    participant CP as Checkpointer (PostgreSQL)
    participant DB as Database

    U->>WS: 질문 ("계약서 작성해줘")
    WS->>API: process_query()
    API->>S: invoke(query, config)

    S->>S: planning_node()
    Note over S: next_action = "계약서 작성"

    S->>A: approval_node(state)
    A->>A: Check if approval needed
    Note over A: requires_approval() = True

    A->>CP: interrupt(approval_payload)
    Note over CP: Save state to PostgreSQL
    A-->>S: Interrupt raised
    S-->>API: Return with __interrupt__

    API->>DB: Save pending approval
    API->>WS: Send approval_required event
    WS->>U: Show Approval Modal

    U->>U: Review action details
    U->>WS: User clicks "승인"
    WS->>API: approve_action(session_id)

    API->>S: invoke(Command(resume="approved"), config)
    S->>CP: Load state from PostgreSQL
    CP-->>S: Restored state

    S->>A: approval_node() re-executes
    Note over A: interrupt() returns "approved"
    A->>A: Process approval
    A-->>S: {"approval_status": "approved"}

    S->>S: execute_node()
    Note over S: Execute approved action
    S-->>API: Final result

    API->>WS: Send response
    WS->>U: Show result
```

### State Structure

```python
# backend/app/service_agent/foundation/separated_states.py

class MainSupervisorState(TypedDict):
    # Existing fields
    user_id: int
    query: str
    chat_session_id: str
    current_agent: Optional[str]
    next_action: Optional[str]
    messages: List[BaseMessage]

    # NEW: HITL Fields
    pending_approval: Optional[Dict[str, Any]]  # 승인 대기 중인 액션
    approval_status: Optional[str]              # "pending" | "approved" | "rejected" | None
    approval_timeout: Optional[datetime]        # 승인 타임아웃 시간
    approval_metadata: Optional[Dict[str, Any]] # 승인 관련 메타데이터
```

### Approval Types

```python
# backend/app/core/approval_types.py

from enum import Enum
from typing import Dict, Callable, Any

class ApprovalType(Enum):
    """승인이 필요한 액션 타입"""

    # 계약 관련
    CONTRACT_CREATE = "contract_create"           # 계약서 작성
    CONTRACT_MODIFY = "contract_modify"           # 계약서 수정
    CONTRACT_SIGN = "contract_sign"               # 계약 체결

    # 법률 관련
    LEGAL_REVIEW = "legal_review"                 # 법률 검토
    LEGAL_ADVICE = "legal_advice"                 # 법률 조언
    RISK_ASSESSMENT = "risk_assessment"           # 리스크 평가

    # 매물 관련
    HIGH_VALUE_PROPERTY = "high_value_property"   # 고액 매물 추천 (10억+)
    PROPERTY_PURCHASE = "property_purchase"       # 매물 구매 제안
    PROPERTY_INVEST = "property_invest"           # 투자 제안

    # 금융 관련
    LOAN_APPLICATION = "loan_application"         # 대출 신청
    INVESTMENT_DECISION = "investment_decision"   # 투자 결정
    HIGH_AMOUNT_TRANSACTION = "high_amount"       # 고액 거래 (5억+)

class ApprovalConfig:
    """승인 규칙 정의"""

    @staticmethod
    def requires_approval(action: Dict[str, Any]) -> bool:
        """액션이 승인을 필요로 하는지 판단"""

        action_type = action.get("type", "")

        # 1. 계약 관련 - 항상 승인 필요
        if any(keyword in action_type.lower() for keyword in ["contract", "계약"]):
            return True

        # 2. 법률 관련 - 항상 승인 필요
        if any(keyword in action_type.lower() for keyword in ["legal", "법률", "리스크"]):
            return True

        # 3. 고액 매물 - 10억 이상
        price = action.get("price", 0)
        if price >= 1_000_000_000:
            return True

        # 4. 투자/대출 - 5억 이상
        amount = action.get("amount", 0)
        if any(keyword in action_type.lower() for keyword in ["investment", "loan", "투자", "대출"]):
            if amount >= 500_000_000:
                return True

        return False

    @staticmethod
    def get_approval_metadata(action: Dict[str, Any]) -> Dict[str, Any]:
        """승인 요청에 필요한 메타데이터 생성"""

        action_type = action.get("type", "")

        metadata = {
            "action_type": action_type,
            "risk_level": "medium",
            "estimated_time": "즉시",
            "reversible": False,
        }

        # 리스크 레벨 결정
        if any(keyword in action_type.lower() for keyword in ["contract", "legal", "계약", "법률"]):
            metadata["risk_level"] = "high"
            metadata["reversible"] = False

        price = action.get("price", 0)
        if price >= 1_000_000_000:
            metadata["risk_level"] = "critical"
            metadata["estimated_time"] = "1-3 영업일"

        # 상세 정보 추가
        metadata["details"] = {
            "description": action.get("description", ""),
            "price": action.get("price"),
            "amount": action.get("amount"),
            "location": action.get("location"),
            "property_type": action.get("property_type"),
        }

        return metadata
```

---

## 💻 Backend Implementation

### Phase 1: Core Approval Node

**파일:** `backend/app/service_agent/supervisor/approval_node.py` (신규)

```python
"""
Human-in-the-Loop Approval Node

LangGraph interrupt()를 사용하여 사용자 승인 대기
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from langgraph.types import interrupt

from app.service_agent.foundation.separated_states import MainSupervisorState
from app.core.approval_types import ApprovalConfig

logger = logging.getLogger(__name__)


class ApprovalNode:
    """사용자 승인 처리 노드"""

    def __init__(self, timeout_minutes: int = 30):
        """
        Args:
            timeout_minutes: 승인 타임아웃 시간 (분)
        """
        self.timeout_minutes = timeout_minutes

    async def __call__(
        self,
        state: MainSupervisorState
    ) -> MainSupervisorState:
        """
        승인이 필요한 액션 처리

        1. 승인 필요 여부 확인
        2. 필요 시 interrupt()로 워크플로우 중단
        3. 사용자 입력 대기
        4. 승인/거부 처리
        """

        next_action = state.get("next_action")

        if not next_action:
            logger.info("[ApprovalNode] No action to approve")
            return state

        # 승인 필요 여부 확인
        if not ApprovalConfig.requires_approval(next_action):
            logger.info(f"[ApprovalNode] Action does not require approval: {next_action.get('type')}")
            state["approval_status"] = "auto_approved"
            return state

        logger.info(f"[ApprovalNode] Approval required for action: {next_action.get('type')}")

        # 승인 메타데이터 생성
        approval_metadata = ApprovalConfig.get_approval_metadata(next_action)

        # 타임아웃 설정
        timeout = datetime.now() + timedelta(minutes=self.timeout_minutes)

        # Pending approval 저장
        state["pending_approval"] = {
            "action": next_action,
            "metadata": approval_metadata,
            "requested_at": datetime.now().isoformat(),
            "timeout_at": timeout.isoformat(),
        }
        state["approval_timeout"] = timeout

        # LangGraph interrupt - 워크플로우 중단
        logger.info("[ApprovalNode] Interrupting workflow for user approval...")

        user_decision = interrupt({
            "type": "approval_required",
            "action": next_action,
            "metadata": approval_metadata,
            "timeout_at": timeout.isoformat(),
            "message": self._generate_approval_message(next_action, approval_metadata)
        })

        # ============================================
        # 이 지점에서 워크플로우가 중단됩니다.
        # Command(resume=...)로 재개될 때까지 대기
        # ============================================

        # user_decision은 Command(resume=...)로 전달된 값
        logger.info(f"[ApprovalNode] User decision received: {user_decision}")

        # 승인 상태 업데이트
        if user_decision == "approved":
            state["approval_status"] = "approved"
            logger.info(f"[ApprovalNode] ✅ Action approved: {next_action.get('type')}")

        elif user_decision == "rejected":
            state["approval_status"] = "rejected"
            state["next_action"] = None  # 액션 취소
            logger.info(f"[ApprovalNode] ❌ Action rejected: {next_action.get('type')}")

        elif user_decision == "timeout":
            state["approval_status"] = "timeout"
            state["next_action"] = None  # 액션 취소
            logger.warning(f"[ApprovalNode] ⏰ Approval timeout: {next_action.get('type')}")

        else:
            # Unknown decision (fallback)
            state["approval_status"] = "rejected"
            state["next_action"] = None
            logger.error(f"[ApprovalNode] Unknown decision: {user_decision}")

        # Pending approval 제거
        state["pending_approval"] = None

        return state

    def _generate_approval_message(
        self,
        action: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """승인 요청 메시지 생성"""

        action_type = action.get("type", "")
        risk_level = metadata.get("risk_level", "medium")

        # 리스크 레벨에 따른 메시지
        risk_messages = {
            "low": "이 작업은 낮은 리스크를 가집니다.",
            "medium": "이 작업은 중간 리스크를 가집니다. 신중하게 검토해주세요.",
            "high": "⚠️ 이 작업은 높은 리스크를 가집니다. 반드시 확인 후 승인하세요.",
            "critical": "🔴 매우 중요한 작업입니다. 법률 또는 금융 전문가와 상담 후 승인을 권장합니다."
        }

        message = f"""
다음 작업을 실행하려면 승인이 필요합니다:

📋 작업: {action.get('description', action_type)}
⚠️ 리스크: {risk_level.upper()}
⏱️ 예상 소요 시간: {metadata.get('estimated_time', '즉시')}

{risk_messages.get(risk_level, '')}

승인하시겠습니까?
"""
        return message.strip()


# 노드 인스턴스 생성
approval_node = ApprovalNode(timeout_minutes=30)
```

### Phase 2: TeamSupervisor Integration

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py` (수정)

```python
# 기존 imports
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END

# NEW: Approval node import
from app.service_agent.supervisor.approval_node import approval_node

class TeamSupervisor:
    def __init__(self, ...):
        # ... existing code ...

        # Build graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        LangGraph 워크플로우 구성

        NEW: approval_node 추가
        """

        builder = StateGraph(MainSupervisorState)

        # Existing nodes
        builder.add_node("planning_node", self.planning_node)
        builder.add_node("real_estate_search_node", self.real_estate_search_node)
        builder.add_node("legal_node", self.legal_node)
        builder.add_node("transaction_node", self.transaction_node)
        builder.add_node("analysis_node", self.analysis_node)
        builder.add_node("execute_node", self.execute_node)
        builder.add_node("generate_response_node", self.generate_response_node)

        # NEW: Approval node
        builder.add_node("approval_node", approval_node)

        # Edges
        builder.add_edge(START, "planning_node")

        # planning → approval (승인 체크)
        builder.add_edge("planning_node", "approval_node")

        # approval → conditional routing
        builder.add_conditional_edges(
            "approval_node",
            self._route_after_approval,
            {
                "approved": "execute_node",      # 승인됨 → 실행
                "rejected": "generate_response_node",  # 거부됨 → 거부 메시지
                "timeout": "generate_response_node",   # 타임아웃 → 타임아웃 메시지
                "auto_approved": "execute_node", # 승인 불필요 → 바로 실행
            }
        )

        # 나머지 기존 edges
        builder.add_edge("execute_node", "generate_response_node")
        builder.add_edge("generate_response_node", END)

        # Existing conditional edges for agent routing
        # ... (keep existing code)

        return builder.compile(checkpointer=self.checkpointer)

    def _route_after_approval(self, state: MainSupervisorState) -> str:
        """
        승인 노드 이후 라우팅

        Returns:
            "approved" | "rejected" | "timeout" | "auto_approved"
        """
        approval_status = state.get("approval_status")

        if approval_status == "approved":
            return "approved"
        elif approval_status == "rejected":
            return "rejected"
        elif approval_status == "timeout":
            return "timeout"
        elif approval_status == "auto_approved":
            return "auto_approved"
        else:
            # Fallback: 승인 상태 없으면 거부 처리
            logger.warning(f"[TeamSupervisor] Unknown approval status: {approval_status}")
            return "rejected"

    async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        계획 수립 노드 (기존 코드)

        NEW: approval_status 초기화
        """
        # ... existing planning logic ...

        # NEW: 승인 상태 초기화
        state["approval_status"] = None
        state["pending_approval"] = None

        return state

    async def generate_response_node(
        self,
        state: MainSupervisorState
    ) -> MainSupervisorState:
        """
        최종 응답 생성 노드

        NEW: 승인 거부/타임아웃 처리
        """
        approval_status = state.get("approval_status")

        # 승인 거부된 경우
        if approval_status == "rejected":
            rejected_action = state.get("next_action", {})
            response = f"""
죄송합니다. 다음 작업이 거부되었습니다:

📋 작업: {rejected_action.get('description', '알 수 없음')}

다른 도움이 필요하시면 말씀해주세요.
"""
            state["messages"].append(AIMessage(content=response.strip()))
            return state

        # 타임아웃된 경우
        if approval_status == "timeout":
            timeout_action = state.get("next_action", {})
            response = f"""
⏰ 승인 요청이 시간 초과되었습니다.

📋 작업: {timeout_action.get('description', '알 수 없음')}
⏱️ 제한 시간: 30분

작업이 자동으로 취소되었습니다. 다시 시도하시려면 요청을 다시 보내주세요.
"""
            state["messages"].append(AIMessage(content=response.strip()))
            return state

        # ... existing response generation logic ...

        return state
```

### Phase 3: Chat API Integration

**파일:** `backend/app/api/chat_api.py` (수정)

```python
from langgraph.types import Command
from fastapi import HTTPException

# NEW: Approval endpoints

@router.post("/chat/{session_id}/approve")
async def approve_action(
    session_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    사용자가 액션을 승인

    LangGraph Command(resume="approved")로 워크플로우 재개
    """
    try:
        # Config 생성 (thread_id = session_id)
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "",
            }
        }

        # TeamSupervisor graph 가져오기
        supervisor = get_supervisor()

        # Command로 워크플로우 재개
        logger.info(f"[ChatAPI] Resuming workflow with approval: {session_id}")

        result = await supervisor.graph.ainvoke(
            Command(resume="approved"),
            config=config
        )

        logger.info(f"[ChatAPI] Workflow resumed successfully: {session_id}")

        return {
            "status": "approved",
            "session_id": session_id,
            "message": "작업이 승인되어 실행되었습니다."
        }

    except Exception as e:
        logger.error(f"[ChatAPI] Approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/{session_id}/reject")
async def reject_action(
    session_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    사용자가 액션을 거부

    LangGraph Command(resume="rejected")로 워크플로우 재개
    """
    try:
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "",
            }
        }

        supervisor = get_supervisor()

        logger.info(f"[ChatAPI] Rejecting action: {session_id}, reason: {reason}")

        result = await supervisor.graph.ainvoke(
            Command(resume="rejected"),
            config=config
        )

        logger.info(f"[ChatAPI] Action rejected: {session_id}")

        return {
            "status": "rejected",
            "session_id": session_id,
            "message": "작업이 거부되었습니다.",
            "reason": reason
        }

    except Exception as e:
        logger.error(f"[ChatAPI] Rejection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/pending-approval")
async def get_pending_approval(
    session_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    대기 중인 승인 요청 조회

    LangGraph state에서 pending_approval 가져오기
    """
    try:
        config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "",
            }
        }

        supervisor = get_supervisor()

        # 현재 state 가져오기
        state = await supervisor.graph.aget_state(config)

        # Interrupt 확인
        if state.tasks:
            # Interrupt가 있는 경우
            for task in state.tasks:
                if task.interrupts:
                    interrupt = task.interrupts[0]
                    return {
                        "status": "pending",
                        "approval_data": interrupt.value,
                        "interrupt_id": interrupt.id,
                    }

        return {
            "status": "none",
            "message": "대기 중인 승인 요청이 없습니다."
        }

    except Exception as e:
        logger.error(f"[ChatAPI] Failed to get pending approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Phase 4: WebSocket Event Handling

**파일:** `backend/app/api/ws_manager.py` (수정)

```python
class ConnectionManager:
    # ... existing code ...

    async def send_approval_request(
        self,
        session_id: str,
        approval_data: Dict[str, Any]
    ):
        """
        승인 요청을 WebSocket으로 전송

        Frontend에서 approval modal 표시
        """
        message = {
            "type": "approval_required",
            "data": approval_data,
            "timestamp": datetime.now().isoformat()
        }

        await self.send_to_session(session_id, message)
        logger.info(f"[WSManager] Approval request sent to session: {session_id}")

    async def send_approval_result(
        self,
        session_id: str,
        status: str,
        result: Dict[str, Any]
    ):
        """
        승인 결과를 WebSocket으로 전송
        """
        message = {
            "type": "approval_result",
            "status": status,  # "approved" | "rejected"
            "data": result,
            "timestamp": datetime.now().isoformat()
        }

        await self.send_to_session(session_id, message)
        logger.info(f"[WSManager] Approval result sent: {session_id} - {status}")


# WebSocket endpoint 수정
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    await manager.connect(session_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "query":
                query = data.get("query")

                # Supervisor 실행
                result = await supervisor.ainvoke({"query": query, ...})

                # Interrupt 확인
                if "__interrupt__" in result:
                    interrupt_data = result["__interrupt__"][0]

                    # 승인 요청 전송
                    await manager.send_approval_request(
                        session_id,
                        interrupt_data.value
                    )

                else:
                    # 정상 응답 전송
                    await manager.send_message(session_id, result)

            elif message_type == "approve":
                # 승인 처리
                result = await approve_action(session_id, db)
                await manager.send_approval_result(session_id, "approved", result)

            elif message_type == "reject":
                # 거부 처리
                reason = data.get("reason")
                result = await reject_action(session_id, reason, db)
                await manager.send_approval_result(session_id, "rejected", result)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

---

## 🎨 Frontend Implementation

### Phase 1: Approval Modal Component

**파일:** `frontend/src/components/chat/ApprovalModal.tsx` (신규)

```typescript
import React, { useState } from 'react';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Card,
  CardBody,
  Alert,
  Chip,
} from '@nextui-org/react';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

interface ApprovalData {
  type: string;
  action: {
    type: string;
    description: string;
    price?: number;
    amount?: number;
    location?: string;
    property_type?: string;
  };
  metadata: {
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    estimated_time: string;
    reversible: boolean;
    details: Record<string, any>;
  };
  message: string;
  timeout_at: string;
}

interface ApprovalModalProps {
  isOpen: boolean;
  approvalData: ApprovalData | null;
  onApprove: () => void;
  onReject: (reason?: string) => void;
  onClose: () => void;
}

const ApprovalModal: React.FC<ApprovalModalProps> = ({
  isOpen,
  approvalData,
  onApprove,
  onReject,
  onClose,
}) => {
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!approvalData) return null;

  const { action, metadata, message } = approvalData;

  // 리스크 레벨에 따른 색상
  const riskColors = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  };

  const riskIcons = {
    low: <CheckCircle className="w-5 h-5" />,
    medium: <AlertTriangle className="w-5 h-5" />,
    high: <AlertTriangle className="w-5 h-5" />,
    critical: <XCircle className="w-5 h-5" />,
  };

  const handleApprove = async () => {
    setIsSubmitting(true);
    await onApprove();
    setIsSubmitting(false);
    onClose();
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    await onReject(rejectReason);
    setIsSubmitting(false);
    setRejectReason('');
    onClose();
  };

  // 타임아웃 시간 계산
  const timeoutAt = new Date(metadata.timeout_at);
  const timeRemaining = Math.max(
    0,
    Math.floor((timeoutAt.getTime() - Date.now()) / 1000 / 60)
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="2xl"
      backdrop="blur"
      isDismissable={false}
      hideCloseButton
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            {riskIcons[metadata.risk_level]}
            <span>승인 요청</span>
          </div>
        </ModalHeader>

        <ModalBody>
          {/* 리스크 레벨 알림 */}
          <Alert
            color={riskColors[metadata.risk_level]}
            title={`리스크 레벨: ${metadata.risk_level.toUpperCase()}`}
            description={message}
          />

          {/* 작업 상세 정보 */}
          <Card>
            <CardBody>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-2">작업 정보</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">작업 유형</p>
                      <p className="font-medium">{action.type}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">예상 소요 시간</p>
                      <p className="font-medium">{metadata.estimated_time}</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">작업 내용</h4>
                  <p className="text-gray-700">{action.description}</p>
                </div>

                {/* 가격 정보 */}
                {action.price && (
                  <div>
                    <p className="text-sm text-gray-500">금액</p>
                    <p className="text-lg font-bold text-blue-600">
                      {action.price.toLocaleString()}원
                    </p>
                  </div>
                )}

                {/* 위치 정보 */}
                {action.location && (
                  <div>
                    <p className="text-sm text-gray-500">위치</p>
                    <p className="font-medium">{action.location}</p>
                  </div>
                )}

                {/* 속성 태그 */}
                <div className="flex flex-wrap gap-2">
                  <Chip size="sm" color={riskColors[metadata.risk_level]}>
                    {metadata.risk_level} risk
                  </Chip>
                  {!metadata.reversible && (
                    <Chip size="sm" color="danger">
                      되돌릴 수 없음
                    </Chip>
                  )}
                  {action.property_type && (
                    <Chip size="sm" variant="flat">
                      {action.property_type}
                    </Chip>
                  )}
                </div>

                {/* 타임아웃 경고 */}
                {timeRemaining < 10 && (
                  <Alert color="warning" title="시간이 얼마 남지 않았습니다">
                    {timeRemaining}분 후 자동으로 취소됩니다.
                  </Alert>
                )}
              </div>
            </CardBody>
          </Card>

          {/* 거부 사유 입력 (선택사항) */}
          <div>
            <label className="text-sm text-gray-500 mb-1 block">
              거부 사유 (선택사항)
            </label>
            <textarea
              className="w-full border rounded-lg p-2"
              rows={3}
              placeholder="거부하는 이유를 입력하세요..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
          </div>
        </ModalBody>

        <ModalFooter>
          <Button
            color="danger"
            variant="light"
            onPress={handleReject}
            isDisabled={isSubmitting}
          >
            거부하기
          </Button>
          <Button
            color="primary"
            onPress={handleApprove}
            isLoading={isSubmitting}
            startContent={<CheckCircle className="w-4 h-4" />}
          >
            승인하기
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ApprovalModal;
```

### Phase 2: Approval Hook

**파일:** `frontend/src/hooks/use-approval.ts` (신규)

```typescript
import { useState, useCallback } from 'react';
import { useWebSocket } from './use-websocket';

interface ApprovalData {
  type: string;
  action: any;
  metadata: any;
  message: string;
  timeout_at: string;
}

export const useApproval = (sessionId: string) => {
  const [pendingApproval, setPendingApproval] = useState<ApprovalData | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { sendMessage } = useWebSocket(sessionId);

  // WebSocket 메시지 핸들러
  const handleApprovalRequest = useCallback((data: ApprovalData) => {
    console.log('[useApproval] Approval request received:', data);
    setPendingApproval(data);
    setIsModalOpen(true);
  }, []);

  // 승인 처리
  const approve = useCallback(async () => {
    if (!pendingApproval) return;

    console.log('[useApproval] Approving action...');

    // WebSocket으로 승인 전송
    sendMessage({
      type: 'approve',
      session_id: sessionId,
    });

    // 또는 REST API 호출
    try {
      const response = await fetch(`/api/v1/chat/${sessionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error('Approval failed');
      }

      console.log('[useApproval] Action approved');
      setPendingApproval(null);
      setIsModalOpen(false);
    } catch (error) {
      console.error('[useApproval] Approval error:', error);
      throw error;
    }
  }, [pendingApproval, sessionId, sendMessage]);

  // 거부 처리
  const reject = useCallback(
    async (reason?: string) => {
      if (!pendingApproval) return;

      console.log('[useApproval] Rejecting action:', reason);

      // WebSocket으로 거부 전송
      sendMessage({
        type: 'reject',
        session_id: sessionId,
        reason,
      });

      // 또는 REST API 호출
      try {
        const response = await fetch(`/api/v1/chat/${sessionId}/reject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason }),
        });

        if (!response.ok) {
          throw new Error('Rejection failed');
        }

        console.log('[useApproval] Action rejected');
        setPendingApproval(null);
        setIsModalOpen(false);
      } catch (error) {
        console.error('[useApproval] Rejection error:', error);
        throw error;
      }
    },
    [pendingApproval, sessionId, sendMessage]
  );

  return {
    pendingApproval,
    isModalOpen,
    setIsModalOpen,
    handleApprovalRequest,
    approve,
    reject,
  };
};
```

### Phase 3: ChatInterface Integration

**파일:** `frontend/src/components/chat/ChatInterface.tsx` (수정)

```typescript
import { useApproval } from '@/hooks/use-approval';
import ApprovalModal from './ApprovalModal';

const ChatInterface: React.FC = () => {
  const { currentSession } = useChatSessions();
  const sessionId = currentSession?.session_id || '';

  // NEW: Approval hook
  const {
    pendingApproval,
    isModalOpen,
    setIsModalOpen,
    handleApprovalRequest,
    approve,
    reject,
  } = useApproval(sessionId);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback(
    (message: any) => {
      console.log('[ChatInterface] Received WS message:', message.type);

      if (message.type === 'approval_required') {
        // 승인 요청 수신
        handleApprovalRequest(message.data);
      } else if (message.type === 'approval_result') {
        // 승인 결과 수신
        console.log('[ChatInterface] Approval result:', message.status);
        // UI 업데이트 등...
      } else {
        // 기존 메시지 처리
        // ...
      }
    },
    [handleApprovalRequest]
  );

  return (
    <div className="chat-interface">
      {/* 기존 UI */}
      <MessageList messages={messages} />
      <InputBox onSend={sendMessage} />

      {/* NEW: Approval Modal */}
      <ApprovalModal
        isOpen={isModalOpen}
        approvalData={pendingApproval}
        onApprove={approve}
        onReject={reject}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};
```

---

## 🧪 Testing Strategy

### Unit Tests

**Backend:**

```python
# tests/test_approval_node.py

import pytest
from app.service_agent.supervisor.approval_node import ApprovalNode
from app.core.approval_types import ApprovalConfig

@pytest.mark.asyncio
async def test_approval_required_for_contract():
    """계약 관련 액션은 항상 승인 필요"""
    action = {
        "type": "contract_create",
        "description": "매매 계약서 작성"
    }

    assert ApprovalConfig.requires_approval(action) == True

@pytest.mark.asyncio
async def test_approval_required_for_high_value():
    """10억 이상 매물은 승인 필요"""
    action = {
        "type": "property_recommendation",
        "price": 1_500_000_000
    }

    assert ApprovalConfig.requires_approval(action) == True

@pytest.mark.asyncio
async def test_approval_not_required_for_low_value():
    """5억 이하 매물은 승인 불필요"""
    action = {
        "type": "property_recommendation",
        "price": 300_000_000
    }

    assert ApprovalConfig.requires_approval(action) == False

@pytest.mark.asyncio
async def test_approval_node_interrupt():
    """Approval node가 interrupt를 정상적으로 발생시키는지 확인"""
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import StateGraph, START

    # Setup
    approval_node = ApprovalNode()
    checkpointer = InMemorySaver()

    builder = StateGraph(MainSupervisorState)
    builder.add_node("approval", approval_node)
    builder.add_edge(START, "approval")

    graph = builder.compile(checkpointer=checkpointer)

    # Execute
    config = {"configurable": {"thread_id": "test-123"}}
    state = {
        "next_action": {
            "type": "contract_create",
            "description": "Test contract"
        }
    }

    result = graph.invoke(state, config=config)

    # Assert
    assert "__interrupt__" in result
    assert len(result["__interrupt__"]) > 0
    assert result["__interrupt__"][0].value["type"] == "approval_required"
```

**Frontend:**

```typescript
// tests/ApprovalModal.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import ApprovalModal from '@/components/chat/ApprovalModal';

describe('ApprovalModal', () => {
  const mockApprovalData = {
    type: 'approval_required',
    action: {
      type: 'contract_create',
      description: '매매 계약서 작성',
      price: 500000000,
    },
    metadata: {
      risk_level: 'high',
      estimated_time: '즉시',
      reversible: false,
      details: {},
    },
    message: '계약서 작성 승인이 필요합니다.',
    timeout_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
  };

  it('renders approval modal correctly', () => {
    render(
      <ApprovalModal
        isOpen={true}
        approvalData={mockApprovalData}
        onApprove={jest.fn()}
        onReject={jest.fn()}
        onClose={jest.fn()}
      />
    );

    expect(screen.getByText('승인 요청')).toBeInTheDocument();
    expect(screen.getByText('매매 계약서 작성')).toBeInTheDocument();
  });

  it('calls onApprove when approve button clicked', () => {
    const onApprove = jest.fn();

    render(
      <ApprovalModal
        isOpen={true}
        approvalData={mockApprovalData}
        onApprove={onApprove}
        onReject={jest.fn()}
        onClose={jest.fn()}
      />
    );

    fireEvent.click(screen.getByText('승인하기'));
    expect(onApprove).toHaveBeenCalled();
  });
});
```

### Integration Tests

```python
# tests/integration/test_hitl_workflow.py

import pytest
from langgraph.types import Command

@pytest.mark.asyncio
async def test_complete_hitl_workflow():
    """전체 HITL 워크플로우 통합 테스트"""

    # 1. TeamSupervisor 초기화
    supervisor = TeamSupervisor(...)

    # 2. 승인이 필요한 쿼리 실행
    config = {"configurable": {"thread_id": "integration-test"}}
    query = "10억짜리 강남 아파트 계약서 작성해줘"

    result = await supervisor.ainvoke({"query": query}, config=config)

    # 3. Interrupt 확인
    assert "__interrupt__" in result
    interrupt = result["__interrupt__"][0]
    assert interrupt.value["type"] == "approval_required"
    assert "계약" in interrupt.value["action"]["description"]

    # 4. 승인으로 재개
    approved_result = await supervisor.ainvoke(
        Command(resume="approved"),
        config=config
    )

    # 5. 최종 결과 확인
    assert approved_result["approval_status"] == "approved"
    assert "계약서" in approved_result["messages"][-1].content

@pytest.mark.asyncio
async def test_hitl_rejection():
    """승인 거부 시나리오 테스트"""

    supervisor = TeamSupervisor(...)
    config = {"configurable": {"thread_id": "rejection-test"}}

    # 승인 필요한 작업 요청
    result = await supervisor.ainvoke(
        {"query": "계약서 작성해줘"},
        config=config
    )

    assert "__interrupt__" in result

    # 거부로 재개
    rejected_result = await supervisor.ainvoke(
        Command(resume="rejected"),
        config=config
    )

    # 거부 메시지 확인
    assert rejected_result["approval_status"] == "rejected"
    assert "거부" in rejected_result["messages"][-1].content
```

### E2E Tests (Playwright)

```typescript
// e2e/approval-workflow.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Human-in-the-Loop Workflow', () => {
  test('should show approval modal for high-value property', async ({ page }) => {
    // 1. 채팅 페이지 이동
    await page.goto('http://localhost:3000');

    // 2. 고액 매물 질문
    await page.fill('[data-testid="chat-input"]', '강남구 15억 아파트 추천해줘');
    await page.click('[data-testid="send-button"]');

    // 3. Approval Modal 표시 확인
    await expect(page.locator('[data-testid="approval-modal"]')).toBeVisible();
    await expect(page.locator('text=승인 요청')).toBeVisible();
    await expect(page.locator('text=15억')).toBeVisible();

    // 4. 승인 버튼 클릭
    await page.click('[data-testid="approve-button"]');

    // 5. Modal 닫힘 확인
    await expect(page.locator('[data-testid="approval-modal"]')).not.toBeVisible();

    // 6. 결과 메시지 확인
    await expect(page.locator('text=추천합니다')).toBeVisible({ timeout: 10000 });
  });

  test('should cancel action on rejection', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // 계약서 작성 요청
    await page.fill('[data-testid="chat-input"]', '매매 계약서 작성해줘');
    await page.click('[data-testid="send-button"]');

    // Modal 대기
    await expect(page.locator('[data-testid="approval-modal"]')).toBeVisible();

    // 거부 버튼 클릭
    await page.click('[data-testid="reject-button"]');

    // 거부 메시지 확인
    await expect(page.locator('text=거부되었습니다')).toBeVisible();
  });
});
```

---

## 🚀 Deployment Plan

### Prerequisites

1. **LangGraph Version**
   ```bash
   pip install langgraph>=0.6.0
   ```

2. **Database Migration**
   ```sql
   -- approval_history 테이블 추가 (선택사항)
   CREATE TABLE approval_history (
       id SERIAL PRIMARY KEY,
       session_id VARCHAR(100) NOT NULL,
       action_type VARCHAR(100) NOT NULL,
       action_description TEXT,
       approval_status VARCHAR(20) NOT NULL,
       requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       responded_at TIMESTAMP WITH TIME ZONE,
       response_reason TEXT,
       FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
   );

   CREATE INDEX idx_approval_history_session ON approval_history(session_id);
   ```

3. **Environment Variables**
   ```env
   # .env
   APPROVAL_TIMEOUT_MINUTES=30  # 승인 타임아웃 (분)
   APPROVAL_AUTO_REJECT_ON_TIMEOUT=true  # 타임아웃 시 자동 거부
   ```

### Deployment Steps

**Step 1: Code Deployment**
```bash
# Backend
cd backend
git pull origin main
pip install -r requirements.txt
alembic upgrade head  # DB migration

# Frontend
cd frontend
git pull origin main
npm install
npm run build
```

**Step 2: Configuration**
```bash
# Backend .env 확인
cat backend/.env | grep APPROVAL

# Frontend .env 확인
cat frontend/.env.local
```

**Step 3: Service Restart**
```bash
# Backend
pm2 restart holmesnyangz-backend

# Frontend
pm2 restart holmesnyangz-frontend
```

**Step 4: Health Check**
```bash
# Backend health check
curl http://localhost:8000/health

# Approval endpoint test
curl -X GET http://localhost:8000/api/v1/chat/test-session/pending-approval
```

### Rollback Plan

**If issues occur:**

```bash
# 1. Rollback code
git revert HEAD

# 2. Restart services
pm2 restart all

# 3. Database rollback (if needed)
alembic downgrade -1
```

---

## 📅 Timeline & Milestones

### Week 1: Backend Core (Days 1-5)

**Day 1-2: LangGraph Integration**
- [ ] ApprovalNode 구현
- [ ] interrupt() 테스트
- [ ] Command resumption 테스트
- [ ] Unit tests

**Day 3-4: API Endpoints**
- [ ] `/approve` endpoint
- [ ] `/reject` endpoint
- [ ] `/pending-approval` endpoint
- [ ] WebSocket integration

**Day 5: Backend Testing**
- [ ] Integration tests
- [ ] Error handling
- [ ] Logging

**Deliverable:** ✅ Working backend HITL system

---

### Week 2: Frontend & E2E (Days 6-10)

**Day 6-7: UI Components**
- [ ] ApprovalModal component
- [ ] Approval hook
- [ ] ChatInterface integration

**Day 8: WebSocket Integration**
- [ ] Real-time approval requests
- [ ] Real-time approval results
- [ ] Connection handling

**Day 9: Testing**
- [ ] Unit tests (Jest)
- [ ] Component tests (React Testing Library)
- [ ] E2E tests (Playwright)

**Day 10: Polish & Deploy**
- [ ] UI/UX refinement
- [ ] Error messages
- [ ] Loading states
- [ ] Deployment to staging

**Deliverable:** ✅ Complete HITL system in staging

---

### Week 3: Production & Monitoring (Days 11-15)

**Day 11-12: Production Deployment**
- [ ] Deploy to production
- [ ] Smoke tests
- [ ] User acceptance testing

**Day 13-14: Monitoring**
- [ ] Metrics dashboard
- [ ] Approval rate tracking
- [ ] Timeout monitoring

**Day 15: Documentation**
- [ ] User guide
- [ ] API documentation
- [ ] Troubleshooting guide

**Deliverable:** ✅ Production-ready HITL system

---

## 📊 Success Metrics

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Approval request accuracy | > 95% | Actions requiring approval correctly identified |
| False positives | < 5% | Non-critical actions incorrectly flagged |
| Modal display time | < 1s | Time from interrupt to modal display |
| Resumption time | < 2s | Time from approval to workflow resume |
| Timeout rate | < 10% | Approvals expiring before user action |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User approval rate | > 80% | % of approval requests approved |
| User satisfaction | > 4.5/5.0 | Post-approval survey |
| Legal risk reduction | -80% | Reduction in auto-executed critical actions |
| User trust | +60% | Survey: "I trust the system with important decisions" |

---

## 🔍 Monitoring & Observability

### Prometheus Metrics

```python
# backend/app/core/metrics.py

from prometheus_client import Counter, Histogram

# Approval metrics
approval_requests = Counter(
    'approval_requests_total',
    'Total approval requests',
    ['action_type', 'risk_level']
)

approval_responses = Counter(
    'approval_responses_total',
    'Total approval responses',
    ['action_type', 'status']  # approved, rejected, timeout
)

approval_latency = Histogram(
    'approval_latency_seconds',
    'Time from request to response',
    ['action_type']
)
```

### Grafana Dashboard

**Panels:**
1. Approval Request Rate (requests/hour)
2. Approval Status Distribution (pie chart)
3. Average Response Time (line chart)
4. Timeout Rate (gauge)
5. Top Approval Types (bar chart)

**Alerts:**
- Timeout rate > 15%: Warning
- Approval latency > 300s (5분): Warning
- Rejection rate > 50%: Critical

---

## 📚 References

### LangGraph Documentation
- [Human-in-the-Loop Concepts](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [Add Human Intervention](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/add-human-in-the-loop/)
- [Wait for User Input](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
- [Command API Reference](https://langchain-ai.github.io/langgraph/reference/types/)

### Code Examples
- [LangGraph interrupt() examples](https://github.com/langchain-ai/langgraph/tree/main/examples/human-in-the-loop)
- [Command primitive usage](https://python.langchain.com/docs/langgraph/how-tos/human_in_the_loop)

### Related Files
- `backend/app/service_agent/supervisor/team_supervisor.py`
- `backend/app/service_agent/foundation/checkpointer.py`
- `backend/app/service_agent/foundation/separated_states.py`

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-21 | Initial HITL implementation plan |

---

**Last Updated:** 2025-10-21
**Author:** HolmesNyangz Development Team
**Status:** 📋 Ready for Implementation
**Priority:** 🔴 P0 Critical
**Estimated Effort:** 15 days (3 weeks)

---

**End of Document**
