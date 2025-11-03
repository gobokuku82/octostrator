"""Placeholder Agents

교체 가능한 Agent 구조 - 사용자가 실제 로직으로 교체
Phase 3: Execution Loop
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def search_agent_node(state: SupervisorState) -> Dict:
    """Search Agent - 사용자가 실제 검색 로직으로 교체

    TODO: 사용자가 다음 중 하나로 교체
    - 벡터DB 검색 (Pinecone, Chroma, Qdrant 등)
    - SQL 쿼리 실행
    - 웹 검색 (Tavily, SerpAPI 등)
    - 문서 검색

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
            - plan: 현재 단계를 "completed"로 업데이트
            - current_step: 다음 단계로 이동
            - messages: 결과 메시지 추가
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # TODO: 사용자가 실제 검색 로직으로 교체
    result = f"[Placeholder] Search Agent executed: {step['description']}"

    # State 업데이트
    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }


async def validation_agent_node(state: SupervisorState) -> Dict:
    """Validation Agent - 사용자가 실제 검증 로직으로 교체

    TODO: 사용자가 다음 중 하나로 교체
    - 데이터 완전성 검증
    - 스키마 검증
    - 비즈니스 룰 검증
    - 데이터 품질 검증

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # TODO: 사용자가 실제 검증 로직으로 교체
    result = f"[Placeholder] Validation Agent: {step['description']}"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }


async def analysis_agent_node(state: SupervisorState) -> Dict:
    """Analysis Agent - 여러 번 호출 가능!

    TODO: 사용자가 다음 중 하나로 교체
    - 데이터 분석 (트렌드, 패턴)
    - 통계 분석
    - ML/AI 모델 실행
    - 비즈니스 인텔리전스

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # 몇 번째 Analysis 호출인지 확인
    analysis_count = sum(
        1 for s in plan[:current_step]
        if s["agent"] == "analysis" and s["status"] == "completed"
    )

    # TODO: 사용자가 실제 분석 로직으로 교체
    result = f"[Placeholder] Analysis #{analysis_count + 1}: {step['description']}"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }


async def comparison_agent_node(state: SupervisorState) -> Dict:
    """Comparison Agent - 비교 분석

    TODO: 사용자가 다음 중 하나로 교체
    - 전년 대비 비교
    - A/B 테스트 결과 비교
    - 기간별 비교
    - 벤치마크 비교

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # TODO: 사용자가 실제 비교 로직으로 교체
    result = f"[Placeholder] Comparison Agent: {step['description']}"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }


async def document_agent_node(state: SupervisorState) -> Dict:
    """Document Agent - 문서 생성

    TODO: 사용자가 다음 중 하나로 교체
    - 보고서 생성
    - 요약문 생성
    - Markdown/PDF 생성
    - 이메일 작성

    Args:
        state: 현재 SupervisorState

    Returns:
        Dict: 업데이트할 state
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # TODO: 사용자가 실제 문서 생성 로직으로 교체
    result = f"[Placeholder] Document Agent: {step['description']}"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
