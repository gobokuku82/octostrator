# Supervisor Aggregator + Generator 설계

**작성일**: 2025-11-03
**Phase**: Phase 3.5 (Answer Generation)
**목적**: 다양한 Frontend 요구사항을 지원하는 답변 생성 시스템 설계

---

## 1. 개요

### 1.1 왜 Aggregator + Generator 구조인가?

Octostrator는 일반적인 LLM 챗봇(ChatGPT, Gemini)과의 차별화를 목표로 합니다:

| 구분 | 일반 LLM 챗봇 | Octostrator |
|------|--------------|-------------|
| **답변 형식** | 텍스트만 | 텍스트 + 그래프 + 보고서 |
| **투명성** | 낮음 (블랙박스) | 높음 (모든 단계 추적) |
| **신뢰성** | 설명 없음 | 각 단계별 근거 제공 |
| **전문성** | 일반적 답변 | 도메인별 Agent 기반 |
| **Frontend** | 단일 채팅창 | 그래프 페이지, 대시보드, 보고서 등 다양 |

### 1.2 아키텍처 개요

```
Executor → All Agents → Aggregator → [Conditional Router] → Generators → Final Result
                                              ↓
                                      ┌───────┼───────┐
                                      ↓       ↓       ↓
                               Chat  Graph  Report
                             Generator Generator Generator
```

**핵심 원칙**:
- **Aggregator**: Frontend 무관하게 구조화된 데이터 생성 (재사용 가능)
- **Generator**: Frontend 형식에 맞게 변환 (교체 가능)
- **Conditional Router**: 사용자 요청/설정에 따라 적절한 Generator 선택

---

## 2. Aggregator Node 설계

### 2.1 역할

모든 Agent 실행 결과를 **구조화된 중간 데이터**로 변환합니다.

**입력**:
- `state["plan"]`: 모든 TaskStep의 실행 결과
- `state["messages"]`: 전체 메시지 흐름
- `state["user_intent"]`: 사용자 의도

**출력**:
- `aggregated_data`: Frontend 무관한 구조화된 JSON

### 2.2 구현

```python
# backend/app/octostrator/nodes/aggregator.py

from typing import Dict, List
from pydantic import BaseModel
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState


class ExecutionSummary(BaseModel):
    """전체 실행 요약"""
    total_steps: int
    completed_steps: int
    failed_steps: int
    execution_time: float  # seconds
    hitl_interactions: int


class StepResult(BaseModel):
    """각 단계별 결과"""
    step_id: int
    agent: str
    description: str
    status: str
    result: str
    confidence: float = 0.9  # Agent별로 설정 가능
    evidence: List[str] = []  # 근거 자료


class Insight(BaseModel):
    """분석 인사이트"""
    category: str  # "trend", "anomaly", "recommendation"
    description: str
    importance: float  # 0.0 ~ 1.0
    related_steps: List[int]


class AggregatedResult(BaseModel):
    """최종 구조화 결과"""
    execution_summary: ExecutionSummary
    steps: List[StepResult]
    insights: List[Insight]
    final_answer: str  # 간단한 요약 (모든 Generator가 사용)
    metadata: Dict  # 추가 정보


async def aggregator_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """Aggregator - 모든 Agent 결과를 구조화된 데이터로 변환

    Phase 3.5: Frontend 무관한 구조화된 데이터 생성

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
    insight_prompt = f"""
    다음 작업 실행 결과를 분석하여 주요 인사이트를 추출하세요:

    사용자 의도: {state.get('user_intent', '')}

    실행 단계:
    {format_steps_for_llm(plan)}

    다음 형식으로 인사이트를 생성하세요:
    1. 트렌드 (trend): 데이터에서 발견된 경향성
    2. 이상 징후 (anomaly): 예상과 다른 패턴
    3. 권장 사항 (recommendation): 다음 단계 제안

    각 인사이트는 중요도(0.0~1.0)와 관련 단계를 포함하세요.
    """

    # LLM으로 인사이트 생성 (Structured Output)
    from pydantic import BaseModel

    class InsightList(BaseModel):
        insights: List[Insight]
        final_answer: str

    structured_llm = llm.with_structured_output(InsightList)
    insight_result = await structured_llm.ainvoke([
        {"role": "system", "content": "You are an expert analyst."},
        {"role": "user", "content": insight_prompt}
    ])

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
            AIMessage(content=f"[Aggregator] 전체 실행 결과를 구조화했습니다.\n\n"
                             f"총 {execution_summary.total_steps}개 단계 중 "
                             f"{execution_summary.completed_steps}개 완료")
        ]
    }


def format_steps_for_llm(plan: List[dict]) -> str:
    """Plan을 LLM이 읽기 쉬운 형식으로 변환"""
    lines = []
    for step in plan:
        lines.append(f"Step {step['step_id']}: [{step['agent']}] {step['description']}")
        lines.append(f"  Status: {step['status']}")
        if step.get('result'):
            lines.append(f"  Result: {step['result'][:200]}")
    return "\n".join(lines)
```

### 2.3 SupervisorState 확장

```python
# backend/app/octostrator/states/supervisor_state.py

class SupervisorState(TypedDict, total=False):
    """Supervisor State with Plan Management"""
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Planning
    user_intent: Optional[str]
    plan: List[dict]
    current_step: int

    # Execution Flags
    is_planning: bool
    is_executing: bool
    is_waiting_human: bool

    # NEW: Aggregation & Generation
    aggregated_data: Optional[dict]  # Aggregator 결과
    output_format: str  # "chat", "graph", "report"

    # Results
    final_result: Optional[str]
```

---

## 3. Generator Nodes 설계

### 3.1 Chat Generator (대화형 챗봇)

**목적**: 자연스러운 대화 형식으로 답변 생성 (기존 LLM과 유사하지만 더 구조적)

```python
# backend/app/octostrator/nodes/generators/chat_generator.py

from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def chat_generator_node(state: SupervisorState) -> dict:
    """Chat Generator - 자연스러운 대화형 답변 생성

    Frontend: 일반적인 채팅 인터페이스
    """
    aggregated_data = state["aggregated_data"]

    # 구조화된 데이터 → 자연어 변환
    chat_response = f"""
{aggregated_data['final_answer']}

---

📊 **실행 요약**
- 총 {aggregated_data['execution_summary']['total_steps']}개 단계 실행
- 완료: {aggregated_data['execution_summary']['completed_steps']}개
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

    chat_response += "\n\n---\n\n"
    chat_response += "더 자세한 내용은 각 단계별 결과를 확인하세요. (그래프 보기 버튼 클릭)"

    return {
        "final_result": chat_response,
        "messages": [AIMessage(content=chat_response)]
    }
```

**Frontend 예시**:
```
사용자 질문: "지난 분기 매출 분석해줘"

답변:
지난 분기 매출은 전년 대비 15% 증가했으며, 특히 온라인 채널에서
큰 성장이 있었습니다. 다만 오프라인 매장은 5% 감소했습니다.

---

📊 실행 요약
- 총 9개 단계 실행
- 완료: 9개
- 사용자 승인: 3회

💡 주요 인사이트
📈 온라인 매출이 전년 대비 35% 증가
⚠️ 오프라인 매장 3곳에서 매출 급감
✅ 온라인 마케팅 예산 확대 권장

---

더 자세한 내용은 각 단계별 결과를 확인하세요. (그래프 보기 버튼 클릭)
```

---

### 3.2 Graph Generator (시각화 페이지)

**목적**: 실행 흐름을 그래프로 시각화 (투명성 극대화)

```python
# backend/app/octostrator/nodes/generators/graph_generator.py

from typing import List, Dict
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def graph_generator_node(state: SupervisorState) -> dict:
    """Graph Generator - 그래프 시각화 데이터 생성

    Frontend: D3.js, Cytoscape.js 등으로 렌더링
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
        "color": "#4CAF50"
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
            "pending": "#9E9E9E"
        }.get(step["status"], "#9E9E9E")

        nodes.append({
            "id": node_id,
            "label": f"{step['agent']}\n{step['description'][:30]}...",
            "type": step["agent"],
            "status": step["status"],
            "color": color,
            "metadata": {
                "result": step["result"],
                "confidence": step["confidence"]
            }
        })

        # 엣지 생성 (이전 단계 → 현재 단계)
        if i == 0:
            edges.append({
                "source": "start",
                "target": node_id,
                "label": ""
            })
        else:
            edges.append({
                "source": f"step_{steps[i-1]['step_id']}",
                "target": node_id,
                "label": ""
            })

    # END 노드
    nodes.append({
        "id": "end",
        "label": "END",
        "type": "end",
        "color": "#4CAF50"
    })

    if steps:
        edges.append({
            "source": f"step_{steps[-1]['step_id']}",
            "target": "end",
            "label": ""
        })

    # 인사이트를 주석 노드로 추가
    for insight in aggregated_data["insights"]:
        if insight["importance"] > 0.7:  # 중요한 인사이트만
            # 관련 단계에 주석 노드 연결
            for step_id in insight["related_steps"]:
                annotation_id = f"insight_{step_id}_{insight['category']}"
                nodes.append({
                    "id": annotation_id,
                    "label": insight["description"][:50] + "...",
                    "type": "insight",
                    "color": "#FF9800"
                })
                edges.append({
                    "source": f"step_{step_id}",
                    "target": annotation_id,
                    "label": "insight",
                    "style": "dashed"
                })

    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_steps": len(steps),
            "completed": aggregated_data["execution_summary"]["completed_steps"],
            "failed": aggregated_data["execution_summary"]["failed_steps"]
        }
    }

    return {
        "final_result": graph_data,
        "messages": []  # 그래프는 메시지 불필요
    }
```

**Frontend 예시** (JSON 응답):
```json
{
  "nodes": [
    {"id": "start", "label": "START", "type": "start", "color": "#4CAF50"},
    {"id": "step_0", "label": "search\n지난 분기 매출 데이터 검색", "type": "search", "status": "completed", "color": "#4CAF50"},
    {"id": "step_1", "label": "validation\n데이터 유효성 검증", "type": "validation", "status": "completed", "color": "#4CAF50"},
    {"id": "step_2", "label": "hitl\n데이터 확인 승인 요청", "type": "hitl", "status": "completed", "color": "#4CAF50"},
    {"id": "insight_0_trend", "label": "온라인 매출 35% 증가...", "type": "insight", "color": "#FF9800"},
    {"id": "end", "label": "END", "type": "end", "color": "#4CAF50"}
  ],
  "edges": [
    {"source": "start", "target": "step_0"},
    {"source": "step_0", "target": "step_1"},
    {"source": "step_1", "target": "step_2"},
    {"source": "step_0", "target": "insight_0_trend", "style": "dashed"},
    {"source": "step_2", "target": "end"}
  ]
}
```

---

### 3.3 Report Generator (문서 생성)

**목적**: Markdown/PDF 보고서 생성 (전문성 극대화)

```python
# backend/app/octostrator/nodes/generators/report_generator.py

from datetime import datetime
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def report_generator_node(state: SupervisorState) -> dict:
    """Report Generator - Markdown 보고서 생성

    Frontend: Markdown 렌더링 또는 PDF 변환
    """
    aggregated_data = state["aggregated_data"]

    # Markdown 보고서 생성
    report = f"""# 분석 보고서

**생성 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**요청 내용**: {aggregated_data['metadata']['user_intent']}

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
| 총 실행 시간 | {aggregated_data['execution_summary']['execution_time']:.2f}초 |

---

## 🔍 상세 실행 내역

"""

    # 각 단계별 상세 내역
    for step in aggregated_data["steps"]:
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳"
        }.get(step["status"], "❓")

        report += f"""
### {status_emoji} Step {step['step_id']}: {step['description']}

- **Agent**: `{step['agent']}`
- **상태**: {step['status']}
- **신뢰도**: {step['confidence'] * 100:.1f}%

**실행 결과**:
```
{step['result']}
```

"""

        # 근거 자료가 있으면 추가
        if step.get('evidence'):
            report += "**근거 자료**:\n"
            for evidence in step['evidence']:
                report += f"- {evidence}\n"
            report += "\n"

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
            for insight in sorted(insights_by_category[category], key=lambda x: x['importance'], reverse=True):
                report += f"- **[중요도: {insight['importance']:.1%}]** {insight['description']}\n"
                if insight['related_steps']:
                    report += f"  - 관련 단계: {', '.join(f'Step {s}' for s in insight['related_steps'])}\n"
            report += "\n"

    # 결론
    report += """
---

## 📌 결론

"""
    report += aggregated_data['final_answer']

    report += """

---

*이 보고서는 Octostrator Planning-Based Multi-Agent System에 의해 자동 생성되었습니다.*
"""

    return {
        "final_result": report,
        "messages": []
    }
```

**Frontend 예시** (Markdown 렌더링):

```
# 분석 보고서

생성 일시: 2025-11-03 14:30:45
요청 내용: 지난 분기 매출 분석 후 전년 동기 대비 비교하고 보고서 작성해줘

---

## 📋 요약

지난 분기 매출은 전년 대비 15% 증가했으며...

---

## 📊 실행 통계

| 항목 | 수치 |
|------|------|
| 총 실행 단계 | 9개 |
| 완료된 단계 | 9개 |
...
```

---

## 4. Conditional Router 설계

**목적**: 사용자 요청/설정에 따라 적절한 Generator 선택

```python
# backend/app/octostrator/nodes/router.py

from langgraph.types import Command
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def output_router_node(state: SupervisorState) -> Command:
    """Output Router - 출력 형식에 따라 적절한 Generator로 라우팅

    state["output_format"]에 따라 분기:
    - "chat": chat_generator
    - "graph": graph_generator
    - "report": report_generator
    - "all": 모든 Generator 실행 (병렬)
    """
    output_format = state.get("output_format", "chat")  # 기본값: chat

    if output_format == "chat":
        return Command(goto="chat_generator")
    elif output_format == "graph":
        return Command(goto="graph_generator")
    elif output_format == "report":
        return Command(goto="report_generator")
    elif output_format == "all":
        # TODO Phase 4: 병렬 실행 지원
        # 현재는 순차 실행
        return Command(goto="chat_generator")
    else:
        # 기본값
        return Command(goto="chat_generator")
```

---

## 5. Graph 통합

```python
# backend/app/octostrator/supervisor/graph.py

from backend.app.octostrator.nodes.aggregator import aggregator_node
from backend.app.octostrator.nodes.router import output_router_node
from backend.app.octostrator.nodes.generators.chat_generator import chat_generator_node
from backend.app.octostrator.nodes.generators.graph_generator import graph_generator_node
from backend.app.octostrator.nodes.generators.report_generator import report_generator_node


def build_supervisor_graph(context: Optional[AppContext] = None):
    """Supervisor Graph 생성 - Phase 3.5: Aggregator + Generators 추가"""

    # ... 기존 코드 ...

    # === Phase 3.5: Aggregator + Generators ===

    async def aggregator_wrapper(state: SupervisorState) -> dict:
        return await aggregator_node(state, llm)

    workflow.add_node("aggregator", aggregator_wrapper)
    workflow.add_node("output_router", output_router_node, ends=["chat_generator", "graph_generator", "report_generator"])
    workflow.add_node("chat_generator", chat_generator_node)
    workflow.add_node("graph_generator", graph_generator_node)
    workflow.add_node("report_generator", report_generator_node)

    # === 엣지 수정 ===

    # Executor가 모든 단계 완료 시 → Aggregator로 이동
    # executor_node의 END 조건을 Aggregator로 변경
    # (executor_node 내부 수정 필요)

    workflow.add_edge("aggregator", "output_router")
    workflow.add_edge("chat_generator", END)
    workflow.add_edge("graph_generator", END)
    workflow.add_edge("report_generator", END)

    return workflow.compile()
```

**Executor Node 수정** (executor.py):

```python
# 기존:
# return Command(update={"final_result": final_result, "is_executing": False}, goto=END)

# 변경:
return Command(
    update={"is_executing": False},
    goto="aggregator"  # END 대신 Aggregator로
)
```

---

## 6. FastAPI 엔드포인트 예시

### 6.1 채팅 인터페이스

```python
# backend/app/api/endpoints/chat.py

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """일반 채팅 인터페이스"""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content=request.message)],
        "output_format": "chat"  # Chat Generator 사용
    })

    return {
        "response": result["final_result"],
        "steps_count": len(result["plan"])
    }
```

### 6.2 그래프 시각화

```python
# backend/app/api/endpoints/graph_view.py

@router.post("/analyze/graph")
async def graph_view_endpoint(request: AnalysisRequest):
    """그래프 시각화 페이지용"""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content=request.query)],
        "output_format": "graph"  # Graph Generator 사용
    })

    # final_result에 graph_data (nodes, edges) 포함
    return result["final_result"]
```

### 6.3 보고서 생성

```python
# backend/app/api/endpoints/report.py

@router.post("/report/generate")
async def generate_report(request: ReportRequest):
    """보고서 생성"""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content=request.query)],
        "output_format": "report"  # Report Generator 사용
    })

    # Markdown을 PDF로 변환 (선택사항)
    if request.format == "pdf":
        pdf_bytes = markdown_to_pdf(result["final_result"])
        return Response(content=pdf_bytes, media_type="application/pdf")
    else:
        return {"markdown": result["final_result"]}
```

---

## 7. ChatGPT/Gemini와의 차별화

| 측면 | ChatGPT/Gemini | Octostrator |
|------|----------------|-------------|
| **투명성** | 답변만 제공 (과정 숨김) | 모든 단계 시각화 (그래프 보기) |
| **신뢰성** | 근거 불명확 | 각 단계별 근거 자료 제공 |
| **다양성** | 텍스트 답변만 | 채팅 + 그래프 + 보고서 |
| **전문성** | 일반적 답변 | Agent별 전문 영역 (분석/비교/검증) |
| **협업** | 없음 | HITL로 중간 승인 가능 |
| **확장성** | 고정된 모델 | Agent/Tool 교체 가능 |

**사용자 경험 시나리오**:

1. **일반 사용자**: 채팅 인터페이스 사용 (ChatGPT와 유사)
2. **분석가**: 그래프 페이지에서 실행 흐름 확인 (투명성)
3. **경영진**: 보고서 다운로드 (PDF) → 공유 및 보관

---

## 8. 구현 우선순위

### Phase 3.5 (현재)
1. ✅ Aggregator Node 구현
2. ✅ Chat Generator 구현 (기본)
3. ✅ Conditional Router 구현
4. ✅ Graph 통합

### Phase 3.6 (다음)
1. Graph Generator 구현
2. Report Generator 구현
3. FastAPI 엔드포인트 추가
4. Frontend 연동 테스트

### Phase 4 (미래)
1. 병렬 Generator 실행 (all 옵션)
2. PDF 변환 기능
3. Real-time 그래프 업데이트 (WebSocket)
4. 커스텀 Generator 플러그인 시스템

---

## 9. 결론

**Aggregator + Generator 구조의 장점**:

1. **재사용성**: Aggregator는 한 번만 실행, 여러 Generator가 재사용
2. **확장성**: 새로운 Frontend 형식 추가 시 Generator만 추가
3. **테스트**: 각 Generator를 독립적으로 테스트 가능
4. **성능**: Aggregator 결과를 캐싱하여 여러 형식 동시 제공
5. **차별화**: 다양한 출력 형식으로 ChatGPT/Gemini와 명확히 구분

**다음 단계**: `nested_graph_hitl_guide.md` 작성
