"""Sales Tool - 영업 실행 지원

인사이트 기반 영업 전략 및 실행 계획 생성 도구를 제공합니다.

Phase 0: Stub 구현 (ImportError 방지)
Phase 2: LLM 통합 완전 구현 예정

(기존 biz_execution/tools/sales.py에서 이전)
"""

import logging
from typing import Dict, Any, List

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def generate_sales_plan(
    insights: Dict[str, Any],
    target_segment: str = "b2c",
    plan_type: str = "strategy"
) -> Dict[str, Any]:
    """
    인사이트 기반 영업 전략/실행 계획 생성

    Phase 0: Stub 모드 - 최소 기능 구현
    Phase 2: Full 모드 - LLM 통합 완전 구현 예정

    Args:
        insights: ML 분석 인사이트
        target_segment: 타겟 세그먼트 (b2c, b2b, enterprise)
        plan_type: 계획 유형 (strategy, action, pitch)

    Returns:
        영업 계획 생성 결과:
        {
            "target_analysis": str,    # 타겟 고객 분석
            "approach": str,           # 접근 방식
            "key_messages": List[str], # 핵심 메시지
            "differentiation": str,    # 차별화 포인트
            "action_items": List[str], # 실행 계획
            "stub": bool,              # Stub 모드 여부
            "summary": str             # 요약 메시지
        }
    """
    logger.info(f"[Sales] Generating {plan_type} plan for {target_segment}")

    # Stub 모드 확인
    is_stub = _is_stub_mode()

    if is_stub:
        return _generate_stub_plan(target_segment, plan_type)
    else:
        return _generate_full_plan(insights, target_segment, plan_type)


@tool
def generate_pitch_deck(
    insights: Dict[str, Any],
    audience: str = "investor"
) -> Dict[str, Any]:
    """
    인사이트 기반 피치덱 생성

    Args:
        insights: ML 분석 인사이트
        audience: 타겟 청중 (investor, client, partner)

    Returns:
        피치덱 슬라이드 정보
    """
    logger.info(f"[Sales] Generating pitch deck for {audience}")

    if _is_stub_mode():
        return {
            "slides": [
                {"title": "표지", "content": "[Stub] K-Beauty 분석 리포트"},
                {"title": "문제 정의", "content": "[Stub] Phase 2에서 자동 생성"},
                {"title": "솔루션", "content": "[Stub] Phase 2에서 자동 생성"},
                {"title": "시장 기회", "content": "[Stub] Phase 2에서 자동 생성"},
                {"title": "결론", "content": "[Stub] Phase 2에서 자동 생성"}
            ],
            "audience": audience,
            "stub": True,
            "summary": "[Phase 0 Stub] 피치덱 생성 기능은 Phase 2에서 구현 예정입니다."
        }
    else:
        raise NotImplementedError("Full implementation planned for Phase 2")


def _is_stub_mode() -> bool:
    """Stub 모드 여부 확인"""
    try:
        from backend.app.dream_agent.llm_manager import agent_config
        return agent_config.get_tool_config("biz_execution", {}).get("stub_mode", True)
    except Exception:
        return True


def _generate_stub_plan(target_segment: str, plan_type: str) -> Dict[str, Any]:
    """Phase 0: Stub 영업 계획 생성"""
    return {
        "target_analysis": "[Phase 0 Stub] 타겟 고객 분석이 여기에 들어갑니다",
        "approach": "[Phase 0 Stub] 접근 방식이 여기에 들어갑니다",
        "key_messages": [
            "[Stub] 핵심 메시지 1",
            "[Stub] 핵심 메시지 2",
            "[Stub] 핵심 메시지 3"
        ],
        "differentiation": "[Phase 0 Stub] 차별화 포인트가 여기에 들어갑니다",
        "action_items": [
            "[Stub] 실행 항목 1",
            "[Stub] 실행 항목 2",
            "[Stub] 실행 항목 3"
        ],
        "target_segment": target_segment,
        "plan_type": plan_type,
        "stub": True,
        "requires_approval": True,
        "summary": "[Phase 0 Stub] 영업 실행 지원 기능은 Phase 2에서 구현 예정입니다."
    }


def _generate_full_plan(
    insights: Dict[str, Any],
    target_segment: str,
    plan_type: str
) -> Dict[str, Any]:
    """Phase 2: 완전 구현 (LLM 통합)"""
    raise NotImplementedError(
        "Full implementation is planned for Phase 2. "
        "Set stub_mode=false in tool_settings.yaml when Phase 2 is complete."
    )


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("sales")
class SalesTool(BaseTool):
    """영업 실행 지원 도구

    BaseTool 패턴으로 구현된 Sales Planner.
    인사이트 기반 영업 전략 및 실행 계획을 생성합니다.

    Phase 0: Stub 구현
    Phase 2: LLM 통합 완전 구현 예정
    """

    name: str = "sales"
    description: str = "인사이트 기반 영업 전략 및 실행 계획 생성"
    category: str = "business"
    version: str = "0.1.0"  # Phase 0: Stub

    # 타겟 세그먼트
    SEGMENTS = ["b2c", "b2b", "enterprise"]

    # 계획 유형
    PLAN_TYPES = ["strategy", "action", "pitch"]

    def execute(
        self,
        insights: Dict[str, Any],
        target_segment: str = "b2c",
        plan_type: str = "strategy",
        **kwargs
    ) -> Dict[str, Any]:
        """영업 계획 생성 실행

        Args:
            insights: ML 분석 인사이트
            target_segment: 타겟 세그먼트
            plan_type: 계획 유형

        Returns:
            영업 계획 생성 결과
        """
        return generate_sales_plan.invoke({
            "insights": insights,
            "target_segment": target_segment,
            "plan_type": plan_type
        })

    async def aexecute(
        self,
        insights: Dict[str, Any],
        target_segment: str = "b2c",
        plan_type: str = "strategy",
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 영업 계획 생성 실행"""
        return await generate_sales_plan.ainvoke({
            "insights": insights,
            "target_segment": target_segment,
            "plan_type": plan_type
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def generate_sales_plan_direct(
    insights: Dict[str, Any],
    target_segment: str = "b2c"
) -> Dict[str, Any]:
    """Agent 없이 직접 영업 계획 생성"""
    logger.info(f"[Sales] Direct plan generation for {target_segment}")
    return generate_sales_plan.invoke({
        "insights": insights,
        "target_segment": target_segment,
        "plan_type": "strategy"
    })


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

SALES_TOOLS = [
    generate_sales_plan,
    generate_pitch_deck,
]
