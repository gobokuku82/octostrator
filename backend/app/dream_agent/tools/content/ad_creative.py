"""Ad Creative Tool - 광고 크리에이티브 생성

인사이트 기반 광고 문구/이미지 프롬프트 생성 도구를 제공합니다.

Phase 0: Stub 구현 (ImportError 방지)
Phase 2: LLM 통합 완전 구현 예정

(기존 biz_execution/tools/ad_creative.py에서 이전)
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
def generate_ad_creative(
    insights: Dict[str, Any],
    platform: str = "instagram",
    creative_type: str = "image"
) -> Dict[str, Any]:
    """
    인사이트 기반 광고 크리에이티브 생성

    Phase 0: Stub 모드 - 최소 기능 구현
    Phase 2: Full 모드 - LLM 통합 완전 구현 예정

    Args:
        insights: ML 분석 인사이트
        platform: 타겟 플랫폼 (instagram, facebook, youtube, tiktok)
        creative_type: 크리에이티브 유형 (image, video, carousel)

    Returns:
        광고 크리에이티브 생성 결과:
        {
            "headline": str,         # 헤드라인
            "body": str,             # 바디 카피
            "cta": str,              # Call-to-Action
            "image_prompt": str,     # 이미지 생성 프롬프트
            "target_audience": str,  # 타겟 오디언스
            "stub": bool,            # Stub 모드 여부
            "summary": str           # 요약 메시지
        }
    """
    logger.info(f"[AdCreative] Generating creative for {platform} ({creative_type})")

    # Stub 모드 확인
    is_stub = _is_stub_mode()

    if is_stub:
        return _generate_stub_creative(platform, creative_type)
    else:
        return _generate_full_creative(insights, platform, creative_type)


@tool
def generate_ad_copy_variants(
    base_copy: Dict[str, Any],
    variant_count: int = 3
) -> List[Dict[str, Any]]:
    """
    광고 카피 변형 생성

    Args:
        base_copy: 기본 광고 카피 (headline, body, cta)
        variant_count: 생성할 변형 수

    Returns:
        광고 카피 변형 리스트
    """
    logger.info(f"[AdCreative] Generating {variant_count} copy variants")

    if _is_stub_mode():
        return [
            {
                "variant_id": i + 1,
                "headline": f"[Stub 변형 {i+1}] 헤드라인",
                "body": f"[Stub 변형 {i+1}] 바디 카피",
                "cta": "자세히 보기",
                "stub": True
            }
            for i in range(variant_count)
        ]
    else:
        raise NotImplementedError("Full implementation planned for Phase 2")


def _is_stub_mode() -> bool:
    """Stub 모드 여부 확인"""
    try:
        from backend.app.dream_agent.llm_manager import agent_config
        return agent_config.get_tool_config("biz_execution", {}).get("stub_mode", True)
    except Exception:
        return True


def _generate_stub_creative(platform: str, creative_type: str) -> Dict[str, Any]:
    """Phase 0: Stub 크리에이티브 생성"""
    return {
        "headline": "[Phase 0 Stub] 헤드라인이 여기에 들어갑니다",
        "body": "[Phase 0 Stub] 광고 바디 카피가 여기에 들어갑니다. Phase 2에서 완전한 크리에이티브가 생성됩니다.",
        "cta": "자세히 보기",
        "image_prompt": "[Phase 0 Stub] 이미지 프롬프트: K-Beauty 제품 광고 이미지",
        "target_audience": "[Phase 0 Stub] 20-35세 여성, 스킨케어 관심",
        "platform": platform,
        "creative_type": creative_type,
        "stub": True,
        "requires_approval": True,
        "summary": "[Phase 0 Stub] 광고 크리에이티브 생성 기능은 Phase 2에서 구현 예정입니다."
    }


def _generate_full_creative(
    insights: Dict[str, Any],
    platform: str,
    creative_type: str
) -> Dict[str, Any]:
    """Phase 2: 완전 구현 (LLM 통합)"""
    raise NotImplementedError(
        "Full implementation is planned for Phase 2. "
        "Set stub_mode=false in tool_settings.yaml when Phase 2 is complete."
    )


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("ad_creative")
class AdCreativeTool(BaseTool):
    """광고 크리에이티브 생성 도구

    BaseTool 패턴으로 구현된 Ad Creative Generator.
    인사이트 기반 광고 문구/이미지 프롬프트를 생성합니다.

    Phase 0: Stub 구현
    Phase 2: LLM 통합 완전 구현 예정
    """

    name: str = "ad_creative"
    description: str = "인사이트 기반 광고 문구/이미지 프롬프트 생성"
    category: str = "content"
    version: str = "0.1.0"  # Phase 0: Stub

    # 지원 플랫폼
    PLATFORMS = ["instagram", "facebook", "youtube", "tiktok", "naver"]

    # 크리에이티브 유형
    CREATIVE_TYPES = ["image", "video", "carousel", "story"]

    def execute(
        self,
        insights: Dict[str, Any],
        platform: str = "instagram",
        creative_type: str = "image",
        **kwargs
    ) -> Dict[str, Any]:
        """광고 크리에이티브 생성 실행

        Args:
            insights: ML 분석 인사이트
            platform: 타겟 플랫폼
            creative_type: 크리에이티브 유형

        Returns:
            광고 크리에이티브 생성 결과
        """
        return generate_ad_creative.invoke({
            "insights": insights,
            "platform": platform,
            "creative_type": creative_type
        })

    async def aexecute(
        self,
        insights: Dict[str, Any],
        platform: str = "instagram",
        creative_type: str = "image",
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 광고 크리에이티브 생성 실행"""
        return await generate_ad_creative.ainvoke({
            "insights": insights,
            "platform": platform,
            "creative_type": creative_type
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def generate_ad_creative_direct(
    product_info: Dict[str, Any] = None,
    insights: Dict[str, Any] = None,
    platform: str = "instagram",
    target_audience: str = "general",
    style: str = "modern",
    creative_type: str = "image"
) -> Dict[str, Any]:
    """Agent 없이 직접 광고 크리에이티브 생성

    Args:
        product_info: 제품 정보 (insights 대신 사용 가능)
        insights: ML 분석 인사이트
        platform: 타겟 플랫폼
        target_audience: 타겟 오디언스
        style: 크리에이티브 스타일
        creative_type: 크리에이티브 유형

    Returns:
        광고 크리에이티브 생성 결과
    """
    # product_info와 insights 병합 (호환성 유지)
    merged_insights = insights or {}
    if product_info:
        merged_insights = {
            **merged_insights,
            "product": product_info,
            "target_audience": target_audience,
            "style": style,
        }

    logger.info(f"[AdCreative] Direct generation for {platform} (style={style})")
    return generate_ad_creative.invoke({
        "insights": merged_insights,
        "platform": platform,
        "creative_type": creative_type
    })


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

AD_CREATIVE_TOOLS = [
    generate_ad_creative,
    generate_ad_copy_variants,
]
