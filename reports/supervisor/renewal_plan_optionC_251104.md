# Supervisor 폴더 구조 리뉴얼 - 옵션 C 최종 계획서

**작성일**: 2025-11-04
**선택된 옵션**: C (핵심만 분리)
**대상**: `backend/app/octostrator/supervisor/`
**목적**: 명확한 이름 + 프롬프트 분산 + 파일 수 감소

---

## 1. 최종 구조 (개선된 이름)

### 1.1 Before (현재)

```
supervisor/
├── __init__.py
├── graph.py
├── prompts.py
└── nodes/
    ├── __init__.py
    ├── intent_understanding.py       (105줄)
    ├── planning.py                   (137줄)
    ├── executor.py                   (80줄)
    ├── hitl_handler.py               (103줄)
    ├── aggregator.py                 (170줄)
    ├── router.py                     (40줄)
    └── generators/
        ├── __init__.py
        ├── chat_generator.py         (73줄)
        ├── graph_generator.py        (171줄)
        └── report_generator.py       (148줄)
```

**문제점**:
- 파일 수: 14개
- 폴더 깊이: 3단계
- 프롬프트가 각 파일에 분산
- Import 복잡도 높음

### 1.2 After (리뉴얼)

```
supervisor/
├── __init__.py                       (10줄) - build_supervisor_graph export
├── main_graph.py                     (160줄) ★ 이름 변경: graph.py → main_graph.py
├── cognitive_nodes.py                (500줄) ★ NEW: Intent, Planning, Executor, Aggregator
├── response_nodes.py                 (535줄) ★ NEW: HITL, Router, Generators
├── cognitive_prompts.py              (120줄) ★ NEW: 인지/분석 프롬프트
└── response_prompts.py               (30줄)  ★ NEW: 응답 생성 프롬프트 (선택적)
```

**개선 효과**:
- 파일 수: 14개 → 6개 (57% 감소)
- 폴더 깊이: 3단계 → 1단계
- 프롬프트 중앙 관리 (2개 파일로 분산)
- Import 단순화

---

## 2. 파일별 상세 설계

### 2.1 main_graph.py (160줄)

**이전 이름**: `graph.py`
**새 이름**: `main_graph.py`
**이유**:
- "graph"는 너무 일반적
- "main_graph"로 메인 오케스트레이터임을 명확히 표현

**내용**:
```python
"""Main Supervisor Graph

LangGraph 1.0 기반 메인 오케스트레이션 그래프:
- StateGraph 정의
- 노드 추가 및 엣지 연결
- Checkpointer 통합
"""
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_openai import ChatOpenAI

from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.config.system import config

# 인지/분석 노드
from .cognitive_nodes import (
    intent_understanding_node,
    planning_node,
    executor_node,
    aggregator_node,
)

# 응답 생성 노드
from .response_nodes import (
    hitl_handler_node,
    output_router_node,
    chat_generator_node,
    graph_generator_node,
    report_generator_node,
)

# 에이전트
from backend.app.octostrator.agents import (
    diet_agent_node,
    workout_agent_node,
    schedule_agent_node,
    member_care_agent_node,
    coaching_agent_node,
)


def build_supervisor_graph(
    context: Optional[AppContext] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    """Supervisor Graph 생성

    Phase 3: Planning-Based Multi-Agent Execution
    Phase 3.5: Aggregator + Generator 추가
    Phase 4.1: PostgreSQL Checkpointer 통합

    Args:
        context: AppContext (선택적)
        checkpointer: AsyncPostgresSaver (선택적)

    Returns:
        CompiledGraph: 컴파일된 LangGraph 그래프
    """
    # LLM 초기화
    if context is not None:
        llm = context.llm
    else:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=config.openai_api_key
        )

    # StateGraph 생성
    workflow = StateGraph(SupervisorState)

    # === LLM을 주입하는 노드 래퍼 ===

    async def intent_node(state: SupervisorState) -> dict:
        """Intent Understanding 노드"""
        return await intent_understanding_node(state, llm)

    async def planning_node_wrapper(state: SupervisorState) -> dict:
        """Planning 노드"""
        return await planning_node(state, llm)

    async def aggregator_wrapper(state: SupervisorState) -> dict:
        """Aggregator 노드"""
        return await aggregator_node(state, llm)

    # === 노드 추가 ===

    # 1. 인지/분석 노드
    workflow.add_node("intent", intent_node)
    workflow.add_node("planning", planning_node_wrapper)
    workflow.add_node("executor", executor_node, ends=[
        "diet", "workout", "schedule", "member_care", "coaching",
        "hitl_handler", "aggregator"
    ])
    workflow.add_node("aggregator", aggregator_wrapper)

    # 2. 에이전트 노드
    workflow.add_node("diet", diet_agent_node)
    workflow.add_node("workout", workout_agent_node)
    workflow.add_node("schedule", schedule_agent_node)
    workflow.add_node("member_care", member_care_agent_node)
    workflow.add_node("coaching", coaching_agent_node)

    # 3. 응답 생성 노드
    workflow.add_node("hitl_handler", hitl_handler_node)
    workflow.add_node("output_router", output_router_node, ends=[
        "chat_generator", "graph_generator", "report_generator"
    ])
    workflow.add_node("chat_generator", chat_generator_node)
    workflow.add_node("graph_generator", graph_generator_node)
    workflow.add_node("report_generator", report_generator_node)

    # === 엣지 연결 ===

    # 메인 플로우
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "planning")
    workflow.add_edge("planning", "executor")

    # 에이전트 → executor 복귀
    workflow.add_edge("diet", "executor")
    workflow.add_edge("workout", "executor")
    workflow.add_edge("schedule", "executor")
    workflow.add_edge("member_care", "executor")
    workflow.add_edge("coaching", "executor")
    workflow.add_edge("hitl_handler", "executor")

    # Aggregator → Router → Generators → END
    workflow.add_edge("aggregator", "output_router")
    workflow.add_edge("chat_generator", END)
    workflow.add_edge("graph_generator", END)
    workflow.add_edge("report_generator", END)

    # 컴파일
    if checkpointer is not None:
        print("[Graph] ✓ Checkpointer와 함께 그래프 컴파일")
        return workflow.compile(checkpointer=checkpointer)
    else:
        print("[Graph] ✓ Checkpointer 없이 그래프 컴파일")
        return workflow.compile()
```

**라인 수**: 약 160줄 (기존 175줄에서 축소)

---

### 2.2 cognitive_nodes.py (500줄)

**이름 의미**:
- Cognitive = 인지, 사고, 분석
- 사용자 의도 파악 → 계획 수립 → 실행 → 결과 분석까지의 "사고 과정"

**포함 노드**:
1. **Intent Understanding** (105줄) - 사용자 의도 분석
2. **Planning** (137줄) - 작업 계획 생성
3. **Executor** (80줄) - 동적 라우팅
4. **Aggregator** (170줄) - 결과 구조화 및 인사이트 생성

**내용**:
```python
"""Cognitive Nodes - 인지 및 분석 노드

사용자 요청을 이해하고 계획을 수립하며 실행을 조율하고 결과를 분석하는
핵심 오케스트레이션 로직:

- Intent Understanding: 사용자 의도 파악 (7개 카테고리 분류)
- Planning: 순차적 작업 계획 생성 (TaskStep 리스트)
- Executor: Command 패턴 기반 동적 라우팅
- Aggregator: 실행 결과 구조화 및 인사이트 생성

Architecture:
    User Input → Intent → Planning → Executor → [Agents] → Aggregator
"""
from typing import Dict, List, Union
from pydantic import BaseModel

from langgraph.types import Command
from langgraph.graph import END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from backend.app.octostrator.states.supervisor_state import SupervisorState, TaskStep
from .cognitive_prompts import (
    INTENT_UNDERSTANDING_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    AGGREGATOR_INSIGHT_PROMPT,
)


# ==========================================
# Intent Understanding Node
# ==========================================

async def intent_understanding_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """사용자 의도 파악

    사용자의 자연어 입력을 분석하여 7개 카테고리로 분류:
    - diet_query: 식단 관련
    - workout_query: 운동 루틴
    - schedule_query: PT 스케줄
    - member_report: 회원 상태
    - coaching_search: 자료 검색
    - multi_step_task: 복합 작업
    - progress_comparison: 진행률 비교

    Args:
        state: 현재 SupervisorState
        llm: ChatOpenAI 인스턴스

    Returns:
        Dict: user_intent, is_planning 업데이트
    """
    # 사용자 쿼리 추출
    messages = state["messages"]
    user_query = state.get("user_query", "")

    # messages에서 사용자 메시지 추출 시도
    user_request = ""
    if messages:
        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        if human_messages:
            user_request = human_messages[-1].content

    # messages가 비어있거나 사용자 메시지가 없으면 user_query 사용
    if not user_request and user_query:
        user_request = user_query

    # 그래도 없으면 에러
    if not user_request:
        user_request = "No request provided"

    # Intent 분석 프롬프트 (사용자 요청을 프롬프트에 직접 포함)
    intent_prompt = INTENT_UNDERSTANDING_PROMPT.format(user_request=user_request)

    # LLM으로 의도 분석
    response = await llm.ainvoke([SystemMessage(content=intent_prompt)])

    # Intent 정보 추출
    intent_analysis = response.content

    return {
        "user_intent": intent_analysis,
        "is_planning": True,  # Planning Node로 전환
        "messages": [
            AIMessage(
                content=f"[Intent Understanding] 사용자 요청을 분석했습니다.\n\n{intent_analysis}"
            )
        ]
    }


# ==========================================
# Planning Node
# ==========================================

class Plan(BaseModel):
    """전체 계획 (Structured Output)"""
    steps: List[TaskStep]
    reasoning: str


async def planning_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """전체 작업을 Task로 분해

    사용자 의도를 분석하여 순차적인 TaskStep 리스트를 생성합니다.
    Structured Output을 사용하여 LLM이 정확한 형식으로 응답하도록 강제합니다.

    Args:
        state: 현재 SupervisorState
        llm: ChatOpenAI 인스턴스

    Returns:
        Dict: plan, current_step, is_planning, is_executing 업데이트
    """
    user_intent = state.get("user_intent", "")

    # Planning 프롬프트
    planning_prompt = SystemMessage(content=PLANNING_SYSTEM_PROMPT)

    # Structured Output을 위한 LLM 설정
    structured_llm = llm.with_structured_output(Plan)

    # Planning 실행
    plan_result = await structured_llm.ainvoke([
        planning_prompt,
        HumanMessage(content=f"User Intent:\n{user_intent}")
    ])

    # TaskStep을 dict로 변환
    plan_as_dicts = [step.model_dump() for step in plan_result.steps]

    # Planning 결과 요약
    plan_summary = "\n".join([
        f"Step {step['step_id']}: [{step['agent']}] {step['description']}"
        for step in plan_as_dicts
    ])

    return {
        "plan": plan_as_dicts,
        "current_step": 0,
        "is_planning": False,
        "is_executing": True,
        "messages": [
            AIMessage(
                content=f"[Planning] 작업 계획을 생성했습니다.\n\n"
                        f"총 {len(plan_as_dicts)}개 단계:\n{plan_summary}\n\n"
                        f"Reasoning: {plan_result.reasoning}"
            )
        ]
    }


# ==========================================
# Executor Node
# ==========================================

def update_step_status(plan: list[dict], step_idx: int, status: str) -> list[dict]:
    """계획의 특정 단계 상태 업데이트"""
    new_plan = [s.copy() for s in plan]
    new_plan[step_idx]["status"] = status
    return new_plan


async def executor_node(state: SupervisorState) -> Command:
    """계획에 따라 Agent를 순차적으로 실행

    Phase 3: Execution Loop의 핵심 노드
    - plan 배열을 순회하며 각 Task 실행
    - Command 패턴으로 다음 노드 동적 라우팅
    - HITL 대기 처리

    Args:
        state: 현재 SupervisorState

    Returns:
        Command: goto와 update 포함
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)

    # 모든 단계 완료 확인
    if current_step >= len(plan):
        # Aggregator로 이동
        return Command(
            update={"is_executing": False},
            goto="aggregator"
        )

    # 현재 단계 가져오기
    step = plan[current_step]

    # HITL 체크
    if step["agent"] == "hitl":
        return Command(
            update={
                "is_waiting_human": True,
                "plan": update_step_status(plan, current_step, "waiting_human")
            },
            goto="hitl_handler"
        )

    # Agent 선택
    agent_name = step["agent"]

    # 현재 단계를 "running"으로 업데이트
    updated_plan = update_step_status(plan, current_step, "running")

    return Command(
        update={"plan": updated_plan},
        goto=agent_name  # "diet", "workout", "schedule", "member_care", "coaching"
    )


# ==========================================
# Aggregator Node
# ==========================================

class ExecutionSummary(BaseModel):
    """전체 실행 요약"""
    total_steps: int
    completed_steps: int
    failed_steps: int
    execution_time: float = 0.0
    hitl_interactions: int


class StepResult(BaseModel):
    """각 단계별 결과"""
    step_id: int
    agent: str
    description: str
    status: str
    result: str
    confidence: float = 0.9
    evidence: List[str] = []


class Insight(BaseModel):
    """분석 인사이트"""
    category: str  # "trend", "anomaly", "recommendation"
    description: str
    importance: float  # 0.0 ~ 1.0
    related_steps: List[int]


class InsightList(BaseModel):
    """LLM Structured Output용 인사이트 리스트"""
    insights: List[Insight]
    final_answer: str


class AggregatedResult(BaseModel):
    """최종 구조화 결과"""
    execution_summary: ExecutionSummary
    steps: List[StepResult]
    insights: List[Insight]
    final_answer: str
    metadata: Dict


async def aggregator_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """Aggregator - 모든 Agent 결과를 구조화된 데이터로 변환

    Phase 3.5: Frontend 무관한 구조화된 데이터 생성
    - Execution Summary 생성
    - 각 단계별 결과 구조화
    - LLM으로 인사이트 생성

    Args:
        state: 현재 SupervisorState
        llm: ChatOpenAI instance

    Returns:
        Dict: aggregated_data를 포함한 state 업데이트
    """
    plan = state["plan"]

    # 1. Execution Summary 생성
    execution_summary = ExecutionSummary(
        total_steps=len(plan),
        completed_steps=sum(1 for s in plan if s["status"] == "completed"),
        failed_steps=sum(1 for s in plan if s["status"] == "failed"),
        execution_time=0.0,  # TODO: 실제 시간 추적
        hitl_interactions=sum(1 for s in plan if s["agent"] == "hitl")
    )

    # 2. 각 단계별 결과 구조화
    steps = []
    for step in plan:
        steps.append(StepResult(
            step_id=step["step_id"],
            agent=step["agent"],
            description=step["description"],
            status=step["status"],
            result=step.get("result", ""),
            evidence=[]  # TODO: Agent에서 근거 자료 수집
        ))

    # 3. LLM으로 인사이트 생성
    insight_prompt = AGGREGATOR_INSIGHT_PROMPT.format(
        user_intent=state.get('user_intent', ''),
        steps=format_steps_for_llm(plan)
    )

    # LLM으로 인사이트 생성 (Structured Output)
    try:
        structured_llm = llm.with_structured_output(InsightList)
        insight_result = await structured_llm.ainvoke([
            SystemMessage(content="You are an expert analyst."),
            HumanMessage(content=insight_prompt)
        ])
    except Exception as e:
        # LLM 실패 시 기본값
        insight_result = InsightList(
            insights=[
                Insight(
                    category="recommendation",
                    description="모든 작업이 완료되었습니다.",
                    importance=0.8,
                    related_steps=[i for i in range(len(plan))]
                )
            ],
            final_answer=f"총 {len(plan)}개 단계가 완료되었습니다."
        )

    # 4. 최종 구조화 결과 생성
    aggregated_data = AggregatedResult(
        execution_summary=execution_summary,
        steps=steps,
        insights=insight_result.insights,
        final_answer=insight_result.final_answer,
        metadata={
            "user_intent": state.get("user_intent", ""),
            "timestamp": "2025-11-03T10:00:00Z",  # TODO: 실제 타임스탬프
        }
    )

    return {
        "aggregated_data": aggregated_data.model_dump(),
        "messages": [
            AIMessage(
                content=f"[Aggregator] 전체 실행 결과를 구조화했습니다.\n\n"
                        f"총 {execution_summary.total_steps}개 단계 중 "
                        f"{execution_summary.completed_steps}개 완료"
            )
        ]
    }


def format_steps_for_llm(plan: List[dict]) -> str:
    """Plan을 LLM이 읽기 쉬운 형식으로 변환"""
    lines = []
    for step in plan:
        lines.append(f"Step {step['step_id']}: [{step['agent']}] {step['description']}")
        lines.append(f"  Status: {step['status']}")
        if step.get('result'):
            result_preview = step['result'][:200]
            lines.append(f"  Result: {result_preview}{'...' if len(step['result']) > 200 else ''}")
    return "\n".join(lines)
```

**라인 수**: 약 500줄

---

### 2.3 response_nodes.py (535줄)

**이름 의미**:
- Response = 응답, 반응
- 사용자에게 제공하는 최종 응답 생성 및 형식 선택

**포함 노드**:
1. **HITL Handler** (103줄) - 사용자 승인 대기
2. **Output Router** (40줄) - 출력 형식 선택
3. **Chat Generator** (73줄) - 대화형 답변
4. **Graph Generator** (171줄) - 그래프 시각화 데이터
5. **Report Generator** (148줄) - Markdown 보고서

**내용**:
```python
"""Response Nodes - 응답 생성 노드

사용자에게 제공할 최종 응답을 생성하는 노드들:

- HITL Handler: 사용자 승인 대기 및 재개
- Output Router: 출력 형식 선택 (chat/graph/report)
- Chat Generator: 자연스러운 대화형 답변 생성
- Graph Generator: D3.js/Cytoscape용 그래프 데이터 생성
- Report Generator: Markdown 보고서 생성

Architecture:
    Aggregator → Router → [Chat/Graph/Report] Generator → END
"""
from typing import Dict
from datetime import datetime

from langgraph.types import Command, interrupt
from langchain_core.messages import AIMessage

from backend.app.octostrator.states.supervisor_state import SupervisorState
from .response_prompts import (
    CHAT_FORMATTING_GUIDE,  # 선택적
)


# ==========================================
# HITL Handler Node
# ==========================================

async def hitl_handler_node(state: SupervisorState) -> Dict:
    """HITL 핸들러 - 사용자 승인 대기

    Phase 4.2: LangGraph 1.0 interrupt()를 사용한 실제 대기 구현

    사용자 응답은:
    1. graph.ainvoke(None, config)로 자동 승인
    2. graph.ainvoke({"messages": [HumanMessage(...)]}, config)로 사용자 응답 전달

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: plan, current_step, is_waiting_human 업데이트
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # HITL 질문 가져오기
    question = step.get("hitl_question", "승인해주세요")

    # Phase 4.2: interrupt()로 실제 대기
    print(f"[HITL] 사용자 승인 대기: {question}")

    # State 업데이트: 대기 상태로 설정
    plan[current_step]["status"] = "waiting_human"

    # Checkpointer에 state 저장하고 대기
    user_response = interrupt(question)

    print(f"[HITL] 사용자 응답 수신: {user_response}")

    # 사용자 응답 처리
    if user_response is None:
        # None으로 재개된 경우 (자동 승인)
        plan[current_step]["hitl_response"] = "[Auto-approved]"
        plan[current_step]["result"] = f"HITL: {question} (자동 승인)"
    else:
        # 사용자 응답이 있는 경우
        plan[current_step]["hitl_response"] = str(user_response)
        plan[current_step]["result"] = f"HITL: {question} - 응답: {user_response}"

    # 완료 상태로 변경
    plan[current_step]["status"] = "completed"

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "is_waiting_human": False,
        "messages": [
            AIMessage(
                content=f"[HITL] {question}\n\n"
                        f"사용자 응답: {user_response if user_response is not None else '(자동 승인)'}"
            )
        ]
    }


# ==========================================
# Output Router Node
# ==========================================

async def output_router_node(state: SupervisorState) -> Command:
    """Output Router - 출력 형식에 따라 Generator 선택

    state["output_format"]에 따라 분기:
    - "chat": chat_generator (기본값)
    - "graph": graph_generator
    - "report": report_generator

    Args:
        state: 현재 SupervisorState

    Returns:
        Command: 다음 Generator로 라우팅
    """
    output_format = state.get("output_format", "chat")

    if output_format == "chat":
        return Command(goto="chat_generator")
    elif output_format == "graph":
        return Command(goto="graph_generator")
    elif output_format == "report":
        return Command(goto="report_generator")
    else:
        # 알 수 없는 형식은 기본값 사용
        return Command(goto="chat_generator")


# ==========================================
# Chat Generator Node
# ==========================================

async def chat_generator_node(state: SupervisorState) -> Dict:
    """Chat Generator - 자연스러운 대화형 답변 생성

    Frontend: 일반적인 채팅 인터페이스

    Args:
        state: 현재 SupervisorState (aggregated_data 포함)

    Returns:
        Dict: final_result와 messages 업데이트
    """
    aggregated_data = state["aggregated_data"]

    # 구조화된 데이터 → 자연어 변환
    chat_response = f"""{aggregated_data['final_answer']}

---

📊 **실행 요약**
- 총 {aggregated_data['execution_summary']['total_steps']}개 단계 실행
- 완료: {aggregated_data['execution_summary']['completed_steps']}개
- 실패: {aggregated_data['execution_summary']['failed_steps']}개
- 사용자 승인: {aggregated_data['execution_summary']['hitl_interactions']}회

💡 **주요 인사이트**
"""

    # 인사이트 추가 (중요도 높은 순)
    insights = sorted(
        aggregated_data['insights'],
        key=lambda x: x['importance'],
        reverse=True
    )

    for i, insight in enumerate(insights[:3], 1):  # 상위 3개만
        emoji = {
            "trend": "📈",
            "anomaly": "⚠️",
            "recommendation": "✅"
        }.get(insight['category'], "•")

        chat_response += f"\n{emoji} {insight['description']}"

    # 단계별 상세 정보
    chat_response += "\n\n---\n\n**실행 단계**\n\n"

    for step in aggregated_data['steps']:
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳",
            "waiting_human": "🙋"
        }.get(step['status'], "❓")

        chat_response += f"{status_emoji} Step {step['step_id']}: [{step['agent']}] {step['description']}\n"

    return {
        "final_result": chat_response,
        "messages": [AIMessage(content=chat_response)]
    }


# ==========================================
# Graph Generator Node
# ==========================================

async def graph_generator_node(state: SupervisorState) -> Dict:
    """Graph Generator - 그래프 시각화 데이터 생성

    Frontend: D3.js, Cytoscape.js, React Flow 등으로 렌더링

    Args:
        state: 현재 SupervisorState (aggregated_data 포함)

    Returns:
        Dict: final_result에 그래프 데이터 포함
    """
    aggregated_data = state["aggregated_data"]

    # 노드 생성
    nodes = []
    edges = []

    # START 노드
    nodes.append({
        "id": "start",
        "label": "START",
        "type": "start",
        "color": "#4CAF50",
        "metadata": {}
    })

    # 각 단계별 노드 생성
    steps = aggregated_data["steps"]
    for i, step in enumerate(steps):
        node_id = f"step_{step['step_id']}"

        # 노드 색상 (상태별)
        color = {
            "completed": "#4CAF50",
            "failed": "#F44336",
            "running": "#2196F3",
            "pending": "#9E9E9E",
            "waiting_human": "#FF9800"
        }.get(step["status"], "#9E9E9E")

        # Agent별 아이콘
        icon = {
            "diet": "🍎",
            "workout": "💪",
            "schedule": "📅",
            "member_care": "👥",
            "coaching": "🔍",
            "hitl": "🙋"
        }.get(step["agent"], "🔹")

        nodes.append({
            "id": node_id,
            "label": f"{icon} {step['agent']}\n{step['description'][:30]}...",
            "type": step["agent"],
            "status": step["status"],
            "color": color,
            "metadata": {
                "step_id": step["step_id"],
                "agent": step["agent"],
                "description": step["description"],
                "result": step["result"],
                "confidence": step.get("confidence", 0.9)
            }
        })

        # 엣지 생성
        if i == 0:
            edges.append({
                "id": f"edge_start_to_{node_id}",
                "source": "start",
                "target": node_id,
                "label": "",
                "type": "default"
            })
        else:
            prev_node_id = f"step_{steps[i-1]['step_id']}"
            edges.append({
                "id": f"edge_{prev_node_id}_to_{node_id}",
                "source": prev_node_id,
                "target": node_id,
                "label": "",
                "type": "default"
            })

    # END 노드
    nodes.append({
        "id": "end",
        "label": "END",
        "type": "end",
        "color": "#4CAF50",
        "metadata": {}
    })

    if steps:
        last_node_id = f"step_{steps[-1]['step_id']}"
        edges.append({
            "id": f"edge_{last_node_id}_to_end",
            "source": last_node_id,
            "target": "end",
            "label": "",
            "type": "default"
        })

    # 최종 그래프 데이터
    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_steps": len(steps),
            "completed": aggregated_data["execution_summary"]["completed_steps"],
            "failed": aggregated_data["execution_summary"]["failed_steps"],
        },
        "summary": aggregated_data["final_answer"]
    }

    return {
        "final_result": graph_data,
        "messages": []
    }


# ==========================================
# Report Generator Node
# ==========================================

async def report_generator_node(state: SupervisorState) -> Dict:
    """Report Generator - Markdown 보고서 생성

    Frontend: Markdown 렌더링 또는 PDF 변환

    Args:
        state: 현재 SupervisorState (aggregated_data 포함)

    Returns:
        Dict: final_result에 Markdown 보고서 포함
    """
    aggregated_data = state["aggregated_data"]

    # Markdown 보고서 생성
    report = f"""# 분석 보고서

**생성 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**요청 내용**: {aggregated_data['metadata'].get('user_intent', 'N/A')}

---

## 📋 요약

{aggregated_data['final_answer']}

---

## 📊 실행 통계

| 항목 | 수치 |
|------|------|
| 총 실행 단계 | {aggregated_data['execution_summary']['total_steps']}개 |
| 완료된 단계 | {aggregated_data['execution_summary']['completed_steps']}개 |
| 실패한 단계 | {aggregated_data['execution_summary']['failed_steps']}개 |
| 사용자 승인 | {aggregated_data['execution_summary']['hitl_interactions']}회 |

---

## 🔍 상세 실행 내역

"""

    # 각 단계별 상세 내역
    for step in aggregated_data["steps"]:
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳",
            "waiting_human": "🙋"
        }.get(step["status"], "❓")

        # Agent별 아이콘
        agent_icon = {
            "diet": "🍎",
            "workout": "💪",
            "schedule": "📅",
            "member_care": "👥",
            "coaching": "🔍",
            "hitl": "🙋"
        }.get(step["agent"], "🔹")

        report += f"""
### {status_emoji} Step {step['step_id']}: {step['description']}

- **Agent**: {agent_icon} `{step['agent']}`
- **상태**: {step['status']}
- **신뢰도**: {step.get('confidence', 0.9) * 100:.1f}%

**실행 결과**:
```
{step['result'] if step['result'] else 'N/A'}
```

"""

    # 인사이트 섹션
    report += "\n---\n\n## 💡 주요 인사이트\n\n"

    # 카테고리별 분류
    insights_by_category = {}
    for insight in aggregated_data["insights"]:
        category = insight["category"]
        if category not in insights_by_category:
            insights_by_category[category] = []
        insights_by_category[category].append(insight)

    category_names = {
        "trend": "📈 트렌드",
        "anomaly": "⚠️ 이상 징후",
        "recommendation": "✅ 권장 사항"
    }

    for category, category_name in category_names.items():
        if category in insights_by_category:
            report += f"\n### {category_name}\n\n"
            for insight in sorted(
                insights_by_category[category],
                key=lambda x: x['importance'],
                reverse=True
            ):
                report += f"- **[중요도: {insight['importance']:.1%}]** {insight['description']}\n"

    # 결론
    report += f"""

---

## 📌 결론

{aggregated_data['final_answer']}

---

*이 보고서는 Octostrator Planning-Based Multi-Agent System에 의해 자동 생성되었습니다.*
"""

    return {
        "final_result": report,
        "messages": []
    }
```

**라인 수**: 약 535줄

---

### 2.4 cognitive_prompts.py (120줄)

**이름 의미**:
- Cognitive Prompts = 인지/분석 관련 프롬프트
- Intent, Planning, Aggregator에서 사용하는 프롬프트

**내용**:
```python
"""Cognitive Prompts - 인지 및 분석 프롬프트

인지/분석 노드에서 사용하는 모든 프롬프트를 중앙에서 관리:
- Intent Understanding: 사용자 의도 분석
- Planning: 작업 계획 생성
- Aggregator: 인사이트 생성

장점:
- 프롬프트 버전 관리 용이
- 일괄 수정 가능
- 다국어 지원 준비
- A/B 테스트 용이
"""

# ==========================================
# Intent Understanding Prompt
# ==========================================

INTENT_UNDERSTANDING_PROMPT = """You are an intent analyzer for a Fitness PT Manager chatbot.
Analyze the following user request and extract the intent.

USER REQUEST: "{user_request}"

Classify the request into one of these categories:
1. "diet_query" - 식단 관련 조회/기록 (예: "오늘 식단 보여줘", "아침에 계란 2개 먹었어")
2. "workout_query" - 운동 루틴 조회/추천 (예: "오늘 운동 추천해줘", "하체 운동 알려줘")
3. "schedule_query" - PT 스케줄 조회/예약 (예: "내일 PT 예약", "이번 주 스케줄 확인")
4. "member_report" - 회원 상태/진행률 조회 (예: "김철수 회원 진행 상황", "최근 1주일 효과")
5. "coaching_search" - 운동/식단 자료 검색 (예: "스쿼트 자세 영상", "다이어트 식단표")
6. "multi_step_task" - 복합 작업 (예: "회원 상태 확인 후 PT 예약")
7. "progress_comparison" - 진행률 비교 (예: "지난주 대비 체중 변화", "이번 달 운동량")

Also extract:
- Main subject (식단/운동/스케줄/회원/자료 중 하나)
- Expected output (사용자가 원하는 결과)
- Complexity (simple/medium/complex)

Examples:
- "최근 식단 기록 보여줘" → Category: diet_query, Subject: 식단 기록, Output: 식단 내역, Complexity: simple
- "오늘 하체 운동 루틴 추천해줘" → Category: workout_query, Subject: 운동 루틴, Output: 하체 운동 추천, Complexity: simple
- "김철수 회원 진행 상황 알려줘" → Category: member_report, Subject: 회원 상태, Output: 진행 리포트, Complexity: medium

Respond in this format:
Category: <category>
Subject: <subject>
Expected Output: <output>
Complexity: <complexity>
Reasoning: <why you classified it this way>
"""


# ==========================================
# Planning Prompt
# ==========================================

PLANNING_SYSTEM_PROMPT = """You are a planning agent for a Fitness PT Manager chatbot.
Break down the user's request into sequential tasks.

Available agents:
- diet: 식단 기록/분석 (식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성)
- workout: 운동 루틴 추천 (사용자 목표/레벨 기반 운동 루틴 생성 및 제안)
- schedule: 수업 예약/변경 (PT 스케줄 생성/변경, 알림 발송)
- member_care: 회원 리포팅/알림 (회원 상태 리포트, 주요 이벤트 알림)
- coaching: 전문 자료 검색 (운동 자세 영상, 식단/운동 논문 등 검색 및 요약)
- hitl: 사용자 승인 필요 (중요한 결정 전)

Rules:
1. 같은 Agent를 여러 번 사용 가능
2. HITL은 중요한 결정 전에 배치
3. 각 Task는 명확한 description 필요
4. step_id는 1부터 시작
5. HITL Task에는 hitl_question 필드 반드시 포함

Complexity Guidelines:
- Simple (1-2 steps): 단순 조회/검색
  Example: "오늘 식단 알려줘" → [diet]

- Medium (2-3 steps): 추천/분석
  Example: "하체 운동 추천해줘" → [workout, coaching]

- Complex (4+ steps): 복합 작업 + HITL
  Example: "회원 진행 상황 확인 후 PT 예약" → [member_care, hitl, schedule]

Now create a plan for the given user intent.
"""


# ==========================================
# Aggregator Prompt
# ==========================================

AGGREGATOR_INSIGHT_PROMPT = """다음 작업 실행 결과를 분석하여 주요 인사이트를 추출하세요:

사용자 의도: {user_intent}

실행 단계:
{steps}

다음 형식으로 인사이트를 생성하세요:
1. 트렌드 (trend): 데이터에서 발견된 경향성
2. 이상 징후 (anomaly): 예상과 다른 패턴
3. 권장 사항 (recommendation): 다음 단계 제안

각 인사이트는 중요도(0.0~1.0)와 관련 단계를 포함하세요.
최소 1개, 최대 5개의 인사이트를 생성하세요.

또한 사용자에게 제공할 최종 답변(final_answer)을 작성하세요.
final_answer는 간결하면서도 모든 주요 결과를 포함해야 합니다.
"""
```

**라인 수**: 약 120줄

---

### 2.5 response_prompts.py (30줄) - 선택적

**이름 의미**:
- Response Prompts = 응답 생성 관련 프롬프트
- Generator에서 사용하는 프롬프트 (실제로는 거의 없음)

**내용**:
```python
"""Response Prompts - 응답 생성 프롬프트

응답 생성 노드에서 사용하는 프롬프트:
- Chat Generator: 대화형 답변 형식 가이드
- Graph Generator: (프롬프트 불필요)
- Report Generator: (프롬프트 불필요)

참고:
- Graph/Report Generator는 템플릿 기반으로 동작하므로 LLM 프롬프트 불필요
- Chat Generator도 대부분 템플릿 기반이지만, 향후 개선 시 프롬프트 추가 가능
"""

# ==========================================
# Chat Generator Guide (선택적)
# ==========================================

CHAT_FORMATTING_GUIDE = """
대화형 답변 생성 시 다음 형식을 따르세요:

1. 최종 답변 (1-2문장)
2. 실행 요약 (단계 수, 완료/실패 등)
3. 주요 인사이트 (상위 3개, 이모지 포함)
4. 실행 단계 목록 (간략하게)

톤:
- 친근하고 자연스러운 어조
- 전문적이지만 딱딱하지 않게
- 이모지 적절히 활용
"""

# 향후 추가 가능한 프롬프트:
# - CHAT_TONE_FORMAL: 공식적인 톤
# - CHAT_TONE_CASUAL: 캐주얼한 톤
# - CHAT_TONE_TECHNICAL: 기술적인 톤
```

**라인 수**: 약 30줄

**참고**: Response Prompts는 실제로 거의 사용되지 않으므로, 생략하고 cognitive_prompts.py만 사용해도 무방합니다.

---

### 2.6 __init__.py (10줄)

**내용**:
```python
"""Supervisor Module

LangGraph 1.0 기반 Supervisor Pattern 구현
"""
from .main_graph import build_supervisor_graph

__all__ = ["build_supervisor_graph"]
```

---

## 3. 최종 파일 구조 요약

```
supervisor/
├── __init__.py                       (10줄)
├── main_graph.py                     (160줄) - LangGraph 정의
├── cognitive_nodes.py                (500줄) - Intent, Planning, Executor, Aggregator
├── response_nodes.py                 (535줄) - HITL, Router, Generators
├── cognitive_prompts.py              (120줄) - 인지/분석 프롬프트
└── response_prompts.py               (30줄)  - 응답 생성 프롬프트 (선택적)
```

**총 파일 수**: 6개 (response_prompts.py 생략 시 5개)
**총 라인 수**: 약 1,355줄 (기존과 유사, Import 증가분 포함)

---

## 4. 이름 선택 이유

### 4.1 main_graph.py

- ✅ "main"으로 핵심 그래프임을 명확히 표현
- ✅ 다른 그래프 추가 시 (예: `validation_graph.py`) 구분 용이
- ✅ 프로젝트 규모가 커져도 확장 가능

### 4.2 cognitive_nodes.py

- ✅ "cognitive" = 인지, 사고 과정 (Intent → Planning → Execution → Analysis)
- ✅ 비즈니스 로직의 핵심 사고 과정 표현
- ✅ "response"와 명확히 구분 (사고 vs 표현)

**대안**:
- `orchestration_nodes.py`: 조율
- `reasoning_nodes.py`: 추론
- `planning_nodes.py`: 계획 (너무 좁음)

### 4.3 response_nodes.py

- ✅ "response" = 응답, 사용자에게 전달하는 최종 결과
- ✅ HITL, Router, Generator 모두 "응답" 범주
- ✅ 직관적이고 명확한 이름

**대안**:
- `presentation_nodes.py`: 프레젠테이션 (조금 장황)
- `output_nodes.py`: 출력 (기존 이름, 괜찮음)
- `delivery_nodes.py`: 전달 (명확하지 않음)
- `rendering_nodes.py`: 렌더링 (Frontend 용어와 혼동)

### 4.4 cognitive_prompts.py / response_prompts.py

- ✅ 노드 파일과 일대일 대응
- ✅ `cognitive_nodes.py` ↔ `cognitive_prompts.py`
- ✅ `response_nodes.py` ↔ `response_prompts.py`
- ✅ 프롬프트 찾기 용이

---

## 5. 마이그레이션 계획 (상세)

### 5.1 백업

```bash
# 1. 전체 supervisor 폴더 백업
cp -r backend/app/octostrator/supervisor backend/app/octostrator/supervisor_backup_251104

# 2. Git 커밋 (롤백 지점)
git add .
git commit -m "Backup before supervisor renewal"
```

### 5.2 프롬프트 추출 및 통합 (30분)

#### Step 1: cognitive_prompts.py 생성

1. `intent_understanding.py`에서 프롬프트 복사 (line 54-88)
2. `planning.py`에서 프롬프트 복사 (line 51-104)
3. `aggregator.py`에서 프롬프트 복사 (line 95-113)
4. 변수명 통일:
   - `INTENT_UNDERSTANDING_PROMPT`
   - `PLANNING_SYSTEM_PROMPT`
   - `AGGREGATOR_INSIGHT_PROMPT`

#### Step 2: response_prompts.py 생성 (선택적)

- 현재는 내용이 거의 없으므로 생략 가능
- 향후 필요 시 추가

### 5.3 cognitive_nodes.py 생성 (40분)

#### Step 1: 파일 생성 및 헤더 작성

```python
"""Cognitive Nodes - 인지 및 분석 노드

...
"""
```

#### Step 2: Import 통합

```python
from typing import Dict, List, Union
from pydantic import BaseModel
from langgraph.types import Command
from langchain_openai import ChatOpenAI
...
from .cognitive_prompts import (
    INTENT_UNDERSTANDING_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    AGGREGATOR_INSIGHT_PROMPT,
)
```

#### Step 3: 4개 노드 복사

1. `intent_understanding.py` 전체 복사
2. `planning.py` 전체 복사
3. `executor.py` 전체 복사
4. `aggregator.py` 전체 복사

#### Step 4: 프롬프트 참조 수정

- 하드코딩된 프롬프트 → `cognitive_prompts.py`의 변수 참조로 변경

### 5.4 response_nodes.py 생성 (40분)

#### Step 1: 파일 생성 및 헤더

#### Step 2: Import 통합

#### Step 3: 5개 노드 복사

1. `hitl_handler.py`
2. `router.py`
3. `chat_generator.py`
4. `graph_generator.py`
5. `report_generator.py`

### 5.5 main_graph.py 업데이트 (20분)

#### Step 1: 파일 이름 변경

```bash
mv backend/app/octostrator/supervisor/graph.py backend/app/octostrator/supervisor/main_graph.py
```

#### Step 2: Import 경로 수정

```python
from .cognitive_nodes import (
    intent_understanding_node,
    planning_node,
    executor_node,
    aggregator_node,
)

from .response_nodes import (
    hitl_handler_node,
    output_router_node,
    chat_generator_node,
    graph_generator_node,
    report_generator_node,
)
```

### 5.6 __init__.py 업데이트 (5분)

```python
from .main_graph import build_supervisor_graph

__all__ = ["build_supervisor_graph"]
```

### 5.7 기존 파일/폴더 삭제 (5분)

```bash
# nodes/ 폴더 전체 삭제
rm -rf backend/app/octostrator/supervisor/nodes

# prompts.py 삭제 (새로 만들었으므로)
rm backend/app/octostrator/supervisor/prompts.py
```

### 5.8 테스트 (20분)

#### 체크리스트

- [ ] 서버 정상 시작
- [ ] Import 에러 없음
- [ ] Intent Understanding 동작
- [ ] Planning 동작
- [ ] DietAgent 호출 ("최근 식단 기록 보여줘")
- [ ] WorkoutAgent 호출 ("오늘 하체 운동 루틴 추천해줘")
- [ ] ScheduleAgent 호출 ("예정된 PT 스케줄 확인")
- [ ] CoachingAgent 호출 ("스쿼트 자세 영상 찾아줘")
- [ ] Aggregator 동작
- [ ] Chat Generator 동작
- [ ] Frontend 4개 버튼 모두 테스트

#### 테스트 명령어

```bash
# 서버 실행
python run_server.py

# Frontend 실행
cd frontend && npm start

# 4개 버튼 클릭 테스트
```

### 5.9 Git 커밋 (5분)

```bash
git add .
git commit -m "Refactor: Supervisor 리뉴얼 (옵션 C)

- 파일 수 14개 → 6개 감소
- graph.py → main_graph.py 이름 변경
- cognitive_nodes.py: Intent, Planning, Executor, Aggregator 통합
- response_nodes.py: HITL, Router, Generators 통합
- cognitive_prompts.py: 프롬프트 중앙 관리
- response_prompts.py: 응답 프롬프트 (선택적)
"
```

**총 예상 시간**: 약 2시간 45분

---

## 6. 롤백 계획

문제 발생 시:

### 옵션 1: 백업 복원

```bash
rm -rf backend/app/octostrator/supervisor
cp -r backend/app/octostrator/supervisor_backup_251104 backend/app/octostrator/supervisor
```

### 옵션 2: Git 되돌리기

```bash
git reset --hard HEAD~1
```

---

## 7. 장점 정리 (옵션 C + 개선된 이름)

### 7.1 파일 수 감소

- **Before**: 14개
- **After**: 6개 (또는 5개)
- **감소율**: 57%

### 7.2 명확한 이름

- `main_graph.py`: 메인 그래프임을 명확히
- `cognitive_nodes.py`: 사고 과정 노드
- `response_nodes.py`: 응답 생성 노드
- `cognitive_prompts.py`: 인지 프롬프트
- `response_prompts.py`: 응답 프롬프트

### 7.3 프롬프트 중앙 관리

- 2개 파일로 분산 (cognitive, response)
- 수정 시간 80% 감소
- A/B 테스트 용이
- 다국어 지원 준비

### 7.4 코드 탐색 용이

- 인지/분석 작업 → `cognitive_nodes.py`
- 응답 생성 → `response_nodes.py`
- 직관적 파일 이름으로 찾기 쉬움

### 7.5 적절한 파일 크기

- 최소: 30줄 (response_prompts.py)
- 최대: 535줄 (response_nodes.py)
- 평균: 226줄
- 모두 관리 가능한 크기

---

## 8. 향후 확장 계획

### 8.1 노드 추가 시

#### 인지/분석 노드 추가 (예: Validation Node)

→ `cognitive_nodes.py`에 추가

```python
async def validation_node(state: SupervisorState) -> Dict:
    """데이터 검증 노드"""
    ...
```

#### 응답 생성 노드 추가 (예: PDF Generator)

→ `response_nodes.py`에 추가

```python
async def pdf_generator_node(state: SupervisorState) -> Dict:
    """PDF 보고서 생성"""
    ...
```

### 8.2 파일 크기 초과 시

#### cognitive_nodes.py가 800줄 초과

→ 분리 옵션:
- `cognitive_core_nodes.py`: Intent, Planning, Executor
- `cognitive_analysis_nodes.py`: Aggregator, Validator

#### response_nodes.py가 800줄 초과

→ 분리 옵션:
- `response_interaction_nodes.py`: HITL, Router
- `response_generation_nodes.py`: Chat, Graph, Report Generator

### 8.3 프롬프트 다국어 지원

```
supervisor/
├── prompts/
│   ├── cognitive_prompts_ko.py
│   ├── cognitive_prompts_en.py
│   ├── response_prompts_ko.py
│   └── response_prompts_en.py
```

---

## 9. 최종 확인 사항

### 9.1 작업 전 확인

- [ ] 백업 완료
- [ ] Git 커밋 완료
- [ ] 작업 시간 확보 (약 3시간)

### 9.2 작업 중 확인

- [ ] cognitive_prompts.py 생성 완료
- [ ] cognitive_nodes.py 생성 완료
- [ ] response_nodes.py 생성 완료
- [ ] main_graph.py 업데이트 완료
- [ ] 기존 파일 삭제 완료

### 9.3 작업 후 확인

- [ ] 서버 정상 실행
- [ ] 4개 에이전트 모두 테스트
- [ ] Import 에러 없음
- [ ] Git 커밋 완료

---

## 10. 의사결정

**작업 시작하시겠습니까?**

- [ ] **예, 지금 바로 시작** → 백업 및 리뉴얼 진행
- [ ] **아니요, 나중에** → 계획서 보관, Phase 5 후 재검토
- [ ] **수정 필요** → 파일 이름 또는 구조 재논의

---

**작성자**: Claude (AI Assistant)
**최종 업데이트**: 2025-11-04
**선택된 옵션**: C (핵심만 분리)
**파일 이름**: main_graph, cognitive_nodes, response_nodes, cognitive_prompts, response_prompts
