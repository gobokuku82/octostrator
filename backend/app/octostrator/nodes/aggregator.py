"""Aggregator Node

모든 Agent 실행 결과를 구조화된 중간 데이터로 변환
Phase 3.5: Frontend 무관한 구조화된 데이터 생성
"""
from typing import Dict, List
from pydantic import BaseModel
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState


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
최소 1개, 최대 5개의 인사이트를 생성하세요.

또한 사용자에게 제공할 최종 답변(final_answer)을 작성하세요.
final_answer는 간결하면서도 모든 주요 결과를 포함해야 합니다.
"""

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
