"""Intent Understanding Node

사용자 요청을 분석하여 의도를 파악하는 노드
Phase 2: Planning-Based Execution
"""
from typing import Dict
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def intent_understanding_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """사용자 의도 파악

    사용자의 최근 메시지를 분석하여 의도를 추출합니다.
    단순 질문인지, 복잡한 멀티 스텝 작업인지 판단합니다.

    Args:
        state: 현재 SupervisorState
        llm: ChatOpenAI 인스턴스

    Returns:
        Dict: 업데이트할 state
            - user_intent: 파악된 사용자 의도
            - is_planning: True (Planning Node로 전환)
            - messages: Intent 분석 결과 메시지
    """
    messages = state["messages"]

    # Intent 분석 프롬프트
    intent_prompt = SystemMessage(content="""
    Analyze the user's request and extract the intent.

    Classify the request into one of these categories:
    1. "simple_search" - 단순 정보 검색 (예: "날씨 알려줘")
    2. "data_analysis" - 데이터 분석 필요 (예: "매출 분석해줘")
    3. "multi_step_task" - 여러 단계 작업 (예: "데이터 검색 후 분석하고 보고서 작성")
    4. "document_generation" - 문서 생성 (예: "보고서 작성해줘")
    5. "comparison" - 비교 분석 (예: "전년 대비 비교")

    Also extract:
    - Main subject (무엇에 관한 요청인지)
    - Expected output (사용자가 원하는 결과)
    - Complexity (simple/medium/complex)

    Examples:
    - "지난 분기 매출 분석 후 보고서 작성" → Category: multi_step_task, Subject: 매출 데이터, Output: 보고서, Complexity: complex
    - "데이터 검색해줘" → Category: simple_search, Subject: 일반 데이터, Output: 검색 결과, Complexity: simple
    - "전년 동기 대비 매출 비교" → Category: comparison, Subject: 매출 데이터, Output: 비교 분석 결과, Complexity: medium

    Respond in this format:
    Category: <category>
    Subject: <subject>
    Expected Output: <output>
    Complexity: <complexity>
    Reasoning: <why you classified it this way>
    """)

    # LLM으로 의도 분석
    response = await llm.ainvoke([intent_prompt, *messages])

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
