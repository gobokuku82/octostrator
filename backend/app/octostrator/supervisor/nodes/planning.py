"""Planning Agent Node

사용자 의도를 TaskStep 리스트로 분해하는 Planning Agent
Phase 2: Planning-Based Execution with Structured Output
"""
from typing import Dict, List
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState, TaskStep


class Plan(BaseModel):
    """전체 계획 (Structured Output)

    Planning Agent가 생성하는 계획 구조
    LLM의 with_structured_output()으로 강제

    Attributes:
        steps: TaskStep 리스트
        reasoning: 왜 이렇게 계획했는지 설명
    """
    steps: List[TaskStep]
    reasoning: str


async def planning_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """전체 작업을 Task로 분해

    사용자 의도를 분석하여 순차적인 Task 리스트를 생성합니다.
    같은 Agent를 여러 번 사용할 수 있으며, HITL 지점을 자동으로 결정합니다.

    Args:
        state: 현재 SupervisorState
        llm: ChatOpenAI 인스턴스

    Returns:
        Dict: 업데이트할 state
            - plan: TaskStep 리스트 (dict로 변환)
            - current_step: 0 (첫 단계부터 시작)
            - is_planning: False (Planning 완료)
            - is_executing: True (Execution 시작)
            - messages: Planning 결과 메시지
    """
    user_intent = state.get("user_intent", "")

    # Planning 프롬프트
    planning_prompt = SystemMessage(content="""
    You are a planning agent. Break down the user's request into sequential tasks.

    Available agents:
    - search: 데이터 검색 (벡터DB, SQL, 웹 검색 등)
    - validation: 데이터 검증 (완전성, 정확성 확인)
    - analysis: 데이터 분석 (트렌드, 패턴 등)
    - comparison: 비교 분석 (전년 대비, 기간별 비교 등)
    - document: 문서 생성 (보고서, 요약 등)
    - hitl: 사용자 승인 필요 (중요한 결정 전)

    Rules:
    1. 같은 Agent를 여러 번 사용 가능 (예: search → analysis → hitl → analysis → document)
    2. HITL은 중요한 결정 전에 배치 (데이터 검증 후, 분석 결과 확인, 최종 승인 등)
    3. 각 Task는 명확한 description 필요
    4. step_id는 1부터 시작
    5. HITL Task에는 hitl_question 필드 반드시 포함

    Complexity Guidelines:
    - Simple (1-2 steps): 단순 검색/질문
      Example: "날씨 알려줘" → [search]

    - Medium (3-5 steps): 분석 필요
      Example: "매출 분석해줘" → [search, validation, analysis]

    - Complex (6+ steps): 멀티 스텝 + HITL
      Example: "매출 분석 후 보고서 작성" → [search, validation, analysis, hitl, document]

    Example Plans:

    1. Simple Request: "최근 매출 데이터 검색해줘"
    Plan:
    [
      {"step_id": 1, "agent": "search", "description": "최근 매출 데이터 검색"}
    ]

    2. Medium Request: "지난 분기 매출 분석해줘"
    Plan:
    [
      {"step_id": 1, "agent": "search", "description": "지난 분기 매출 데이터 검색"},
      {"step_id": 2, "agent": "validation", "description": "데이터 완전성 검증"},
      {"step_id": 3, "agent": "analysis", "description": "매출 트렌드 분석"}
    ]

    3. Complex Request: "지난 분기 매출 분석 후 전년 동기 대비 비교하고 보고서 작성해줘. 각 단계마다 확인할게."
    Plan:
    [
      {"step_id": 1, "agent": "search", "description": "지난 분기 매출 데이터 검색"},
      {"step_id": 2, "agent": "search", "description": "전년 동기 매출 데이터 검색"},
      {"step_id": 3, "agent": "validation", "description": "두 데이터셋의 완전성 검증"},
      {"step_id": 4, "agent": "hitl", "description": "데이터 검증 결과 확인", "hitl_question": "검색된 데이터가 맞나요?"},
      {"step_id": 5, "agent": "analysis", "description": "지난 분기 트렌드 분석"},
      {"step_id": 6, "agent": "comparison", "description": "전년 동기 대비 비교 분석"},
      {"step_id": 7, "agent": "hitl", "description": "분석 결과 확인", "hitl_question": "분석 결과를 확인해주세요"},
      {"step_id": 8, "agent": "document", "description": "분석 보고서 생성"},
      {"step_id": 9, "agent": "hitl", "description": "최종 승인", "hitl_question": "보고서를 승인하시겠습니까?"}
    ]

    Now create a plan for the given user intent.
    """)

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
