# Agent 재설계 계획서
**작성일**: 2025-11-10
**목표**: 오류 없이 깔끔하게 Agent 시스템 재구축

---

## 🎯 재설계 방침

### 핵심 원칙
1. **기존 우수한 부분은 유지** (Database, Architecture)
2. **Agent는 전체 삭제 후 재설계**
3. **사전 규칙 정의 → Template 생성 → 복제** 방식
4. **Reference Agent 1개 완벽 구현 → 나머지 복제**

---

## 📦 유지 vs 삭제 구분

### ✅ 유지할 컴포넌트 (건드리지 않음)

#### 1. Database 레이어 (100% 완성)
```
backend/database/
├── session.py              ✅ 완벽 (타입 힌트만 수정)
├── utils.py                ✅ 완벽
├── assessor_crud.py        ✅ 완벽
├── frontdesk_crud.py       ✅ 완벽
└── relation_db/
    └── models.py           ✅ 완벽 (23개 테이블)
```

#### 2. ORM Models (100% 완성)
```
backend/app/models/
├── core.py                 ✅ User
├── frontdesk.py            ✅ Lead, Inquiry, Appointment
├── assessor.py             ✅ InBodyData, PostureAnalysis
├── nutrition.py            ✅ NutritionGoal, FoodDatabase, etc.
└── ... (총 23개 테이블)
```

#### 3. Alembic Migrations (100% 완성)
```
backend/alembic/
├── versions/
│   ├── c8dd4d782b94_initial_migration.py  ✅
│   └── d9e84f691c25_add_nutrition_tables.py  ✅
└── alembic.ini             ✅
```

#### 4. Architecture Core (95% 완성)
```
backend/app/octostrator/
├── supervisors/
│   ├── octostrator/
│   │   └── octostrator_graph.py  ✅ 완벽
│   ├── execute/
│   │   ├── execute_graph.py      ✅ 완벽
│   │   └── execute_nodes.py      ✅ 완벽 (agent_registry만 수정)
│   └── response/
│       └── response_*.py         ✅ 완벽
├── states/
│   ├── octostrator_state.py      ✅ 완벽 (Annotated Reducers)
│   ├── reducers.py               ✅ 완벽
│   └── base.py                   ✅ 완벽
└── contexts/
    └── app_context.py            ✅ 완벽 (Context API)
```

**유지 이유**: LangGraph 1.0 최신 패턴, Context API, Reducers 완벽 구현

---

### ❌ 삭제할 컴포넌트 (재설계 대상)

#### 1. Agent 구현 파일 (전체 삭제)
```
backend/app/octostrator/agents/
├── frontdesk/
│   ├── frontdesk_agent.py        ❌ 삭제
│   ├── frontdesk_graph.py        ❌ 삭제
│   ├── frontdesk_nodes.py        ❌ 삭제 (버그 多)
│   ├── frontdesk_tools.py        ❌ 삭제 (버그 多)
│   └── frontdesk_prompts.py      ❌ 삭제
├── assessor/
│   └── assessor_nodes.py         ❌ 삭제 (TODO만)
├── nutrition/
│   └── nutrition_nodes.py        ❌ 삭제 (TODO만)
└── ... (나머지 5개 에이전트 전부)
```

**삭제 이유**:
- 통합 실패
- 버그 多
- 컨벤션 불일치
- TODO만 있거나 구현 불완전

#### 2. Agent State 파일 (재설계)
```
backend/app/octostrator/states/
├── frontdesk_state.py            ⚠️ 재설계 (구조는 유지, 정리)
├── assessor_state.py             ⚠️ 재설계
└── ... (나머지 State 파일들)
```

**재설계 이유**: State 구조는 좋지만 Agent 재설계와 동기화 필요

#### 3. Cognitive/Todo Layer (재구현)
```
backend/app/octostrator/supervisors/
├── cognitive/
│   └── cognitive_nodes.py        ❌ 삭제 (TODO만)
└── todo/
    └── todo_manager.py           ❌ 삭제 (TODO만)
```

**삭제 이유**: 구현 안 됨 (TODO만)

---

## 📋 사전 결정 사항 (재설계 전 필수)

### 1. 프로젝트 컨벤션 정의

#### 📁 파일 구조 규칙
```
backend/app/octostrator/agents/{agent_name}/
├── {agent_name}_agent.py       # Agent 클래스 (BaseAgent 상속)
├── {agent_name}_graph.py       # LangGraph 빌드
├── {agent_name}_nodes.py       # 노드 함수들
├── {agent_name}_tools.py       # DB/API 호출 함수
├── {agent_name}_prompts.py     # 프롬프트 템플릿
└── __init__.py                 # Export
```

#### 📝 코딩 컨벤션
```python
# 1. Import 규칙
# ✅ 절대 경로만 사용
from backend.database import frontdesk_crud
from backend.database.session import get_db_session
from backend.app.octostrator.states.frontdesk_state import FrontdeskState

# ❌ 상대 경로 금지
from database import frontdesk_crud  # ❌
from ..states import FrontdeskState   # ❌

# 2. 타입 힌트 필수
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

async def create_lead_record(
    session: AsyncSession,
    lead_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:  # 반환 타입 명시
    ...

# 3. Docstring 필수 (Google 스타일)
async def create_lead_record(
    session: AsyncSession,
    lead_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Create a new lead record in database.

    Args:
        session: Async database session
        lead_data: Lead information with keys:
            - name (str): Customer name
            - phone (str): Phone number
            - email (str): Email address

    Returns:
        Dict with created lead info or None if failed

    Raises:
        ValidationError: If lead_data is invalid
    """
    ...

# 4. 로깅 규칙
import logging
logger = logging.getLogger(__name__)

logger.info(f"[{AgentName}] Action started: {action_id}")
logger.warning(f"[{AgentName}] Unexpected condition: {details}")
logger.error(f"[{AgentName}] Operation failed: {error}", exc_info=True)
```

---

### 2. Database 세션 사용 규칙

```python
# ✅ 규칙 1: Context Manager 사용 (권장)
from backend.database.session import get_db_session

async def some_tool_function():
    async with get_db_session() as session:
        result = await crud.create_lead(session, data)
        # session.commit()은 자동 (context manager가 처리)
    return result

# ✅ 규칙 2: 수동 관리 (특수한 경우만)
from backend.database.session import get_db

async def some_special_function():
    session = await get_db()
    try:
        result = await crud.create_lead(session, data)
        await session.commit()
        return result
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()

# ❌ 금지: 잘못된 사용
async with await get_db() as session:  # ❌ TypeError
    ...
```

---

### 3. LLM 호출 규칙

#### OpenAI Structured Output 사용 (권장)
```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List

# 1. Response Schema 정의
class InquiryResponse(BaseModel):
    """Inquiry handler response schema"""
    intent: str = Field(..., description="Customer intent category")
    customer_needs: List[str] = Field(default_factory=list)
    response: str = Field(..., description="Response to customer")
    next_action: str = Field(..., description="Recommended next action")
    urgency: str = Field(..., description="Urgency level: high/medium/low")

# 2. LLM 생성 (Context API 사용)
from langgraph.types import RuntimeValue

async def inquiry_handler_node(state: Dict[str, Any], *, config) -> Dict[str, Any]:
    # Context API에서 설정 가져오기
    context = RuntimeValue.runtime.context

    llm = ChatOpenAI(
        model=context.llm_settings.intent_model,
        temperature=context.llm_settings.intent_temperature,
        api_key=system_config.openai_api_key
    ).with_structured_output(InquiryResponse)  # ⭐ Structured Output

    # 3. 호출 (자동으로 Pydantic 객체 반환)
    response: InquiryResponse = await llm.ainvoke([
        SystemMessage(content=prompt)
    ])

    # 4. 안전한 사용 (타입 보장)
    return {
        "intent_classification": response.intent,
        "response_text": response.response,
        "urgency_level": response.urgency,
        ...
    }
```

---

### 4. 에러 처리 규칙

```python
# 1. Custom Exception 정의
class AgentError(Exception):
    """Base exception for all agent errors"""
    pass

class DatabaseOperationError(AgentError):
    """Database operation failed"""
    pass

class LLMCallError(AgentError):
    """LLM call failed"""
    pass

# 2. Try-Except 패턴
async def some_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # 주요 로직
        result = await process_data(state)

        logger.info(f"[AgentName] Node completed successfully")
        return {
            "status": "completed",
            "result": result
        }

    except DatabaseOperationError as e:
        logger.error(f"[AgentName] Database error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "error_type": "database"
        }

    except LLMCallError as e:
        logger.error(f"[AgentName] LLM error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "error_type": "llm"
        }

    except Exception as e:
        logger.error(f"[AgentName] Unexpected error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "error_type": "unknown"
        }
```

---

### 5. State 업데이트 규칙

```python
# ✅ 규칙: 노드는 Dict를 반환 (State 자동 병합)
async def some_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    반환된 Dict는 자동으로 State에 병합됩니다.
    Annotated Reducers가 있는 필드는 자동으로 리스트에 추가됩니다.
    """
    return {
        # 일반 필드: 덮어쓰기
        "status": "completed",
        "result": {...},

        # Annotated Reducer 필드: 자동 병합
        "action_history": {  # add_with_timestamp_and_step 자동 적용
            "action": "inquiry_handler_node",
            "result": "success"
        },

        "todos": {  # merge_todos_smart 자동 적용
            "id": "todo_1",
            "status": "completed"
        }
    }
```

---

## 🏗️ Agent Template 구조

### BaseAgent 표준 구현
```python
# backend/app/octostrator/agents/base/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        description: str = "",
        enable_checkpoint: bool = True,
        priority: str = "NORMAL"
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.enable_checkpoint = enable_checkpoint
        self.priority = priority
        self.graph = None

    @abstractmethod
    async def build_graph(self, llm: Optional[ChatOpenAI] = None) -> StateGraph:
        """Build LangGraph workflow (must implement)"""
        pass

    @abstractmethod
    async def process_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process task (must implement)"""
        pass

    async def initialize(
        self,
        llm: Optional[ChatOpenAI] = None,
        checkpointer = None
    ):
        """Initialize agent (graph compile)"""
        state_graph = await self.build_graph(llm)
        self.graph = state_graph.compile(checkpointer=checkpointer)

    async def execute(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        thread_id: str = "default"
    ) -> Dict[str, Any]:
        """Execute task"""
        if not self.graph:
            raise RuntimeError(f"{self.agent_name} not initialized")

        # LangGraph 실행
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.graph.ainvoke(task, config=config)

        return {
            "status": "completed",
            "result": result,
            "agent_id": self.agent_id
        }
```

---

### Agent 구현 Template (복사해서 사용)

#### 1. {agent_name}_agent.py
```python
"""
{AgentName} Agent

{Agent 설명}
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from backend.app.octostrator.agents.base.base_agent import BaseAgent
from backend.app.octostrator.states.{agent_name}_state import {AgentName}State
from .{agent_name}_nodes import (
    node1_function,
    node2_function,
    # ... 노드 import
)

class {AgentName}Agent(BaseAgent):
    """
    {AgentName} Agent Implementation

    Workflow:
    START → node1 → node2 → ... → END
    """

    def __init__(self):
        super().__init__(
            agent_id="{agent_name}_agent",
            agent_name="{AgentName} Agent",
            description="{Agent 설명}",
            enable_checkpoint=True,
            priority="HIGH"  # or MEDIUM, NORMAL
        )

    async def build_graph(
        self,
        llm: Optional[ChatOpenAI] = None
    ) -> StateGraph:
        """Build LangGraph workflow"""
        graph = StateGraph({AgentName}State)

        # Add nodes
        graph.add_node("node1", node1_function)
        graph.add_node("node2", node2_function)
        # ...

        # Add edges
        graph.add_edge(START, "node1")
        graph.add_edge("node1", "node2")
        # ...
        graph.add_edge("final_node", END)

        return graph

    async def process_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process task (called by execute layer)"""
        # Task 초기 State로 변환
        initial_state = {
            "task_id": task.get("task_id"),
            "agent_id": self.agent_id,
            # ... task 데이터를 State로 변환
        }

        # Graph 실행
        thread_id = context.get("session_id", "default")
        result = await self.execute(
            task=initial_state,
            context=context,
            thread_id=thread_id
        )

        return result
```

#### 2. {agent_name}_nodes.py
```python
"""
{AgentName} Agent Workflow Nodes
"""
from typing import Dict, Any
import logging
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from backend.database.session import get_db_session
from backend.database import {agent_name}_crud
from .{agent_name}_prompts import create_prompt_template
from .{agent_name}_tools import tool_function_1, tool_function_2

logger = logging.getLogger(__name__)


# Response Schema 정의
class Node1Response(BaseModel):
    """Node 1 response schema"""
    field1: str
    field2: int
    # ...


async def node1_function(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 1: {설명}

    Args:
        state: Current state

    Returns:
        Updated state dict
    """
    try:
        logger.info(f"[{AgentName}] Node 1 executing")

        # 1. Input 추출
        input_data = state.get("input_field")

        # 2. LLM 호출 (Structured Output)
        llm = ChatOpenAI(...).with_structured_output(Node1Response)
        prompt = create_prompt_template(input_data)
        response = await llm.ainvoke([SystemMessage(content=prompt)])

        # 3. Tool 함수 호출 (DB 접근 등)
        result = await tool_function_1(response.field1)

        # 4. State 업데이트
        logger.info(f"[{AgentName}] Node 1 completed")
        return {
            "status": "completed",
            "node1_result": result,
            "action_history": {
                "action": "node1_function",
                "result": "success"
            }
        }

    except Exception as e:
        logger.error(f"[{AgentName}] Node 1 failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


async def node2_function(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 2: {설명}"""
    # 동일한 패턴으로 구현
    ...
```

#### 3. {agent_name}_tools.py
```python
"""
{AgentName} Agent Tools

Database 및 외부 API 호출 함수들
"""
from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db_session
from backend.database import {agent_name}_crud

logger = logging.getLogger(__name__)


async def tool_function_1(param1: str) -> Dict[str, Any]:
    """Tool function 1: {설명}

    Args:
        param1: Parameter description

    Returns:
        Result dict
    """
    try:
        async with get_db_session() as session:
            # CRUD 호출
            result = await {agent_name}_crud.create_something(
                session,
                data={"param": param1}
            )

            if not result:
                raise DatabaseOperationError("Failed to create")

            # Dict로 변환
            result_dict = {agent_name}_crud.model_to_dict(result)

            logger.info(f"[{AgentName}Tools] Tool 1 success")
            return {
                "status": "success",
                "data": result_dict
            }

    except Exception as e:
        logger.error(f"[{AgentName}Tools] Tool 1 failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }
```

#### 4. {agent_name}_prompts.py
```python
"""
{AgentName} Agent Prompts
"""

def create_prompt_template(data: str) -> str:
    """Create prompt for node 1"""
    return f"""
You are a {agent description}.

Task: {task description}

Input Data:
{data}

Please analyze and respond in JSON format:
{{
    "field1": "...",
    "field2": 123,
    ...
}}
"""
```

#### 5. {agent_name}_state.py
```python
"""
{AgentName} Agent State
"""
from typing import TypedDict, Optional, List, Dict, Any
from backend.app.octostrator.states.base import BaseAgentState


class {AgentName}State(BaseAgentState):
    """
    {AgentName} Agent State Schema

    {State 설명}
    """
    # Agent-specific fields
    field1: Optional[str]
    field2: Optional[int]
    result_data: Optional[Dict[str, Any]]
    # ...
```

---

## 🚀 재설계 실행 계획

### Phase 1: 준비 및 정리 (1일)

#### Step 1: 기존 Agent 파일 백업 후 삭제
```bash
# 백업
mkdir -p backup/agents_backup_251110
cp -r backend/app/octostrator/agents/* backup/agents_backup_251110/

# Agent 구현 파일 삭제 (base는 유지)
rm -rf backend/app/octostrator/agents/frontdesk/*.py
rm -rf backend/app/octostrator/agents/assessor/*.py
rm -rf backend/app/octostrator/agents/nutrition/*.py
# ... (나머지 에이전트들)

# base, __init__.py만 유지
# backend/app/octostrator/agents/base/ (유지)
# backend/app/octostrator/agents/__init__.py (재작성)
```

#### Step 2: 컨벤션 문서 작성
```bash
# 파일 생성: docs/CODING_CONVENTIONS.md
# 위에서 정의한 규칙 문서화
```

#### Step 3: Database session.py 타입 힌트 수정
```python
# backend/database/session.py
from typing import AsyncGenerator

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

---

### Phase 2: Reference Agent 구현 (1-2일)

#### Step 1: Frontdesk Agent를 Reference로 선택
**선택 이유**:
- Database CRUD 완성 ✅
- 워크플로우 명확 (inquiry → scoring → appointment → notification)
- 복잡도 적당

#### Step 2: Template 기반 완벽 구현
```bash
# 1. State 정의 (깔끔하게 재작성)
backend/app/octostrator/states/frontdesk_state.py

# 2. Agent 파일 생성 (Template 사용)
backend/app/octostrator/agents/frontdesk/
├── frontdesk_agent.py       # ✅ Template 적용
├── frontdesk_nodes.py       # ✅ Structured Output 사용
├── frontdesk_tools.py       # ✅ 올바른 세션 사용
├── frontdesk_prompts.py     # ✅ 프롬프트 분리
└── __init__.py              # ✅ Export
```

#### Step 3: 통합 테스트 작성
```python
# backend/tests/test_frontdesk_e2e.py
async def test_frontdesk_full_workflow():
    """Frontdesk Agent E2E 테스트"""
    # 1. Agent 초기화
    agent = FrontdeskAgent()
    await agent.initialize(llm=llm, checkpointer=checkpointer)

    # 2. Task 실행
    task = {
        "task_id": "task_001",
        "inquiry_text": "PT 회원권 문의드립니다",
        "name": "홍길동",
        "phone": "01012345678",
        "email": "hong@example.com"
    }

    result = await agent.process_task(task, context={})

    # 3. 검증
    assert result["status"] == "completed"
    assert "lead_info" in result["result"]
    assert "appointment_info" in result["result"]

    # 4. DB 확인
    async with get_db_session() as session:
        lead = await frontdesk_crud.get_lead_by_id(
            session,
            result["result"]["lead_info"]["lead_id"]
        )
        assert lead is not None
        assert lead.name == "홍길동"
```

#### Step 4: Reference Agent 완성 확인
- [ ] 모든 노드 구현 완료
- [ ] LLM Structured Output 사용
- [ ] Database CRUD 연결
- [ ] 에러 처리 완벽
- [ ] 타입 힌트 완벽
- [ ] Docstring 완벽
- [ ] 통합 테스트 통과
- [ ] 실제 실행 확인

---

### Phase 3: 나머지 Agent 복제 (2-3일)

#### Agent 우선순위
1. **Assessor Agent** (HIGH) - Database CRUD 완성되어 있음
2. **Nutrition Agent** (MEDIUM) - Database CRUD 일부 완성
3. **Program Designer** (NORMAL)
4. **Manager Agent** (NORMAL)
5. **Marketing Agent** (NORMAL)
6. **Owner Assistant** (NORMAL)

#### 복제 프로세스 (각 Agent당 2-3시간)
```bash
# 1. Reference Agent 복제
cp -r backend/app/octostrator/agents/frontdesk \
      backend/app/octostrator/agents/assessor

# 2. 파일 이름 변경
mv assessor/frontdesk_agent.py assessor/assessor_agent.py
mv assessor/frontdesk_nodes.py assessor/assessor_nodes.py
# ...

# 3. 내용 수정 (검색/치환)
# "Frontdesk" → "Assessor"
# "frontdesk" → "assessor"

# 4. 노드 로직 구현 (Agent별 다름)
# - Assessor: InBody/Posture 분석
# - Nutrition: 식단 기록/분석
# ...

# 5. 통합 테스트 작성 및 실행

# 6. agent_registry 등록
```

---

### Phase 4: Cognitive/Todo Layer 구현 (1일)

#### Cognitive Layer Nodes
```python
# cognitive_nodes.py

class IntentResponse(BaseModel):
    """Intent understanding response"""
    user_intent: str  # diet_query, workout_query, member_report, etc.
    confidence: float
    required_agents: List[str]

async def intent_understanding_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Understand user intent with LLM"""
    llm = ChatOpenAI(...).with_structured_output(IntentResponse)
    response = await llm.ainvoke([...])

    return {
        "user_intent": response.user_intent,
        "intent_confidence": response.confidence,
        "required_agents": response.required_agents
    }


class PlanResponse(BaseModel):
    """Planning response"""
    goal: str
    steps: List[Dict[str, Any]]
    requires_todos: bool

async def planning_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create execution plan with LLM"""
    llm = ChatOpenAI(...).with_structured_output(PlanResponse)
    response = await llm.ainvoke([...])

    return {
        "plan": {
            "goal": response.goal,
            "steps": response.steps
        },
        "plan_requires_todos": response.requires_todos
    }
```

---

### Phase 5: 통합 및 테스트 (1-2일)

#### agent_registry 완성
```python
# backend/app/octostrator/agents/__init__.py
from .frontdesk.frontdesk_agent import FrontdeskAgent
from .assessor.assessor_agent import AssessorAgent
from .nutrition.nutrition_agent import NutritionAgent
from .program_designer.program_designer_agent import ProgramDesignerAgent
from .manager.manager_agent import ManagerAgent
from .marketing.marketing_agent import MarketingAgent
from .owner_assistant.owner_assistant_agent import OwnerAssistantAgent

agent_registry = {
    "frontdesk_agent": FrontdeskAgent,
    "assessor_agent": AssessorAgent,
    "nutrition_agent": NutritionAgent,
    "program_designer_agent": ProgramDesignerAgent,
    "manager_agent": ManagerAgent,
    "marketing_agent": MarketingAgent,
    "owner_assistant_agent": OwnerAssistantAgent,
}

__all__ = ["agent_registry"]
```

#### 전체 시스템 E2E 테스트
```python
# backend/tests/test_octostrator_e2e.py
async def test_full_system_workflow():
    """전체 시스템 E2E 테스트"""
    # START → Cognitive → Execute (Frontdesk + Assessor) → Response → END
    ...
```

---

## 📊 예상 일정

| Phase | 작업 | 예상 시간 | 담당자 |
|-------|------|-----------|--------|
| **Phase 1** | 준비 및 정리 | 4시간 | 전체 |
| **Phase 2** | Reference Agent (Frontdesk) | 12시간 (1.5일) | 1명 |
| **Phase 3** | Agent 복제 (6개) | 18시간 (2-3일) | 2-3명 병렬 |
| **Phase 4** | Cognitive/Todo Layer | 8시간 (1일) | 1명 |
| **Phase 5** | 통합 테스트 | 8시간 (1일) | 전체 |
| **총계** | | **50시간 (6-7일)** | |

---

## ✅ 성공 기준

### 코드 품질
- [ ] 모든 파일에 타입 힌트 100%
- [ ] 모든 함수에 Docstring
- [ ] Import 경로 일관성 (절대 경로만)
- [ ] 에러 처리 완벽
- [ ] 로깅 일관성

### 기능 완성도
- [ ] 7개 Agent 모두 구현 완료
- [ ] 각 Agent별 E2E 테스트 통과
- [ ] 전체 시스템 E2E 테스트 통과
- [ ] Database 연동 정상 작동
- [ ] LLM 호출 정상 작동

### 통합
- [ ] agent_registry 완성
- [ ] Cognitive Layer 구현 완료
- [ ] 실제 사용자 쿼리 처리 가능
- [ ] 버그 0개

---

## 🎯 장점 요약

### 기존 방식 (버그 수정)
- ❌ 버그 수정 시간: 3-4일
- ❌ 통합 문제 재발 가능
- ❌ 코드 품질 불균일
- ❌ 유지보수 어려움

### 재설계 방식 (권장)
- ✅ 처음부터 깔끔하게
- ✅ Template 기반 → 일관성 보장
- ✅ 컨벤션 정의 → 통합 문제 원천 차단
- ✅ Reference Agent → 복제 빠름
- ✅ 장기적 유지보수 용이

---

## 📝 다음 단계

1. **의사결정**: 재설계 방식 채택 여부
2. **준비**: 컨벤션 문서 확정
3. **실행**: Phase 1부터 시작

재설계 진행하시겠습니까?

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-10
