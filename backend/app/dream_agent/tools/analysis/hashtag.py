"""Hashtag Analysis Tool - SNS 해시태그 분석

SNS 데이터(TikTok, YouTube)에서 해시태그를 분석하여
바이럴 마케팅 인사이트를 발굴합니다.

(기존 ml_execution/agents/hashtag_analyzer_agent.py에서 이전)
"""

import re
import logging
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def extract_hashtags(
    reviews: List[Dict],
    top_n: int = 20,
    min_count: int = 2,
) -> Dict[str, Any]:
    """
    SNS 리뷰에서 해시태그 추출 및 분석

    Args:
        reviews: 리뷰 데이터 리스트 (TikTok, YouTube 등 SNS 데이터 포함)
        top_n: 반환할 상위 해시태그 수
        min_count: 최소 등장 횟수

    Returns:
        해시태그 분석 결과:
        {
            "top_hashtags": [...],      # 빈도 기준 상위 해시태그
            "rising_hashtags": [...],   # engagement 기준 상승 해시태그
            "brand_hashtags": [...],    # 브랜드별 해시태그
            "category_breakdown": {},   # 카테고리별 분류
            "stats": {...}              # 통계 정보
        }
    """
    from backend.app.services.ml.analysis import get_hashtag_analyzer

    logger.info(f"[Hashtag] Analyzing hashtags from {len(reviews)} reviews (top_n={top_n})")

    analyzer = get_hashtag_analyzer()
    result = analyzer.analyze(reviews, top_n=top_n, min_count=min_count)

    logger.info(
        f"[Hashtag] Found {result.stats['unique_hashtags']} unique hashtags, "
        f"SNS reviews: {result.stats.get('sns_reviews_count', 0)}"
    )

    return {
        "top_hashtags": result.top_hashtags,
        "rising_hashtags": result.rising_hashtags,
        "brand_hashtags": result.brand_hashtags,
        "category_breakdown": result.category_breakdown,
        "stats": result.stats,
        "analyzed_at": result.analyzed_at,
    }


@tool
def compare_hashtags(
    brand_hashtags: Dict[str, List[str]],
    competitor_hashtags: Dict[str, List[str]],
) -> Dict[str, Any]:
    """
    브랜드와 경쟁사 해시태그 비교 분석

    Args:
        brand_hashtags: 브랜드별 해시태그 {"laneige": ["#kbeauty", "#skincare", ...]}
        competitor_hashtags: 경쟁사별 해시태그 {"sulwhasoo": ["#luxury", ...]}

    Returns:
        비교 분석 결과:
        {
            "brand_unique": {...},          # 브랜드만의 고유 해시태그
            "shared_with_competitors": {},   # 경쟁사와 공유하는 해시태그
            "competitor_only": {},           # 경쟁사만의 해시태그
            "overlap_analysis": [...]        # 겹침 분석
        }
    """
    from backend.app.services.ml.analysis import get_hashtag_analyzer

    logger.info(
        f"[Hashtag] Comparing hashtags - "
        f"brands: {list(brand_hashtags.keys())}, "
        f"competitors: {list(competitor_hashtags.keys())}"
    )

    analyzer = get_hashtag_analyzer()
    result = analyzer.compare_hashtags(brand_hashtags, competitor_hashtags)

    return result


@tool
def get_trending_hashtags(
    reviews: List[Dict],
    category: Optional[str] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    트렌딩 해시태그 추출

    Args:
        reviews: 리뷰 데이터
        category: 필터링할 카테고리 ("kbeauty", "skincare", "beauty", "viral", "review")
        top_n: 상위 N개 반환

    Returns:
        트렌딩 해시태그 리스트
    """
    from backend.app.services.ml.analysis import get_hashtag_analyzer

    logger.info(f"[Hashtag] Getting trending hashtags (category={category}, top_n={top_n})")

    analyzer = get_hashtag_analyzer()
    trending = analyzer.get_trending_hashtags(reviews, category=category, top_n=top_n)

    return {
        "trending_hashtags": trending,
        "category": category,
        "count": len(trending),
    }


@tool
def analyze_hashtag_engagement(
    reviews: List[Dict],
    hashtag: str,
) -> Dict[str, Any]:
    """
    특정 해시태그의 engagement 분석

    Args:
        reviews: 리뷰 데이터
        hashtag: 분석할 해시태그 (# 포함 또는 미포함)

    Returns:
        해시태그 engagement 분석 결과
    """
    hashtag_clean = hashtag.lstrip('#').lower()
    logger.info(f"[Hashtag] Analyzing engagement for #{hashtag_clean}")

    # 해당 해시태그가 포함된 리뷰 필터링
    matching_reviews = []
    sns_sources = {"tiktok", "youtube", "instagram"}

    for review in reviews:
        source = review.get("source", "").lower()
        if source not in sns_sources:
            continue

        text = review.get("text", "").lower()
        hashtags_field = review.get("hashtags", [])

        # 텍스트 또는 hashtags 필드에서 매칭
        text_match = f"#{hashtag_clean}" in text or re.search(rf'#{hashtag_clean}(?:\s|$|[^\w])', text)
        field_match = any(h.lower().lstrip('#') == hashtag_clean for h in hashtags_field)

        if text_match or field_match:
            matching_reviews.append(review)

    if not matching_reviews:
        return {
            "hashtag": f"#{hashtag_clean}",
            "found": False,
            "count": 0,
            "message": f"해시태그 #{hashtag_clean}을(를) 찾을 수 없습니다.",
        }

    # Engagement 계산
    total_likes = sum(r.get("likes", 0) for r in matching_reviews)
    total_views = sum(r.get("views", 0) for r in matching_reviews)
    total_shares = sum(r.get("shares", 0) for r in matching_reviews)
    total_comments = sum(r.get("comments_count", 0) for r in matching_reviews)

    count = len(matching_reviews)
    total_engagement = total_likes + total_views + total_shares

    return {
        "hashtag": f"#{hashtag_clean}",
        "found": True,
        "count": count,
        "engagement": {
            "total": total_engagement,
            "average": round(total_engagement / count, 2) if count else 0,
            "likes": total_likes,
            "views": total_views,
            "shares": total_shares,
            "comments": total_comments,
        },
        "sources": list(set(r.get("source", "unknown") for r in matching_reviews)),
        "sample_texts": [r.get("text", "")[:100] for r in matching_reviews[:3]],
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("hashtag")
class HashtagTool(BaseTool):
    """SNS 해시태그 분석 도구

    BaseTool 패턴으로 구현된 Hashtag Analyzer.
    TikTok, YouTube 등 SNS 데이터의 해시태그를 분석합니다.
    """

    name: str = "hashtag"
    description: str = "SNS 해시태그 분석 (TikTok, YouTube)"
    category: str = "analysis"
    version: str = "1.0.0"

    def execute(
        self,
        reviews: List[Dict],
        top_n: int = 20,
        min_count: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """해시태그 분석 실행

        Args:
            reviews: 분석할 리뷰 리스트
            top_n: 상위 해시태그 수
            min_count: 최소 등장 횟수

        Returns:
            해시태그 분석 결과
        """
        return extract_hashtags.invoke({
            "reviews": reviews,
            "top_n": top_n,
            "min_count": min_count
        })

    async def aexecute(
        self,
        reviews: List[Dict],
        top_n: int = 20,
        min_count: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 해시태그 분석 실행"""
        return await extract_hashtags.ainvoke({
            "reviews": reviews,
            "top_n": top_n,
            "min_count": min_count
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def extract_hashtags_direct(
    reviews: List[Dict],
    top_n: int = 20,
) -> Dict[str, Any]:
    """Agent 없이 직접 해시태그 추출"""
    logger.info(f"[Hashtag] Direct extraction from {len(reviews)} reviews")
    return extract_hashtags.invoke({
        "reviews": reviews,
        "top_n": top_n,
        "min_count": 2,
    })


def get_trending_direct(
    reviews: List[Dict],
    category: Optional[str] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """Agent 없이 직접 트렌딩 해시태그 추출"""
    return get_trending_hashtags.invoke({
        "reviews": reviews,
        "category": category,
        "top_n": top_n,
    })


def analyze_engagement_direct(
    reviews: List[Dict],
    hashtag: str,
) -> Dict[str, Any]:
    """Agent 없이 직접 해시태그 engagement 분석"""
    return analyze_hashtag_engagement.invoke({
        "reviews": reviews,
        "hashtag": hashtag,
    })


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

HASHTAG_TOOLS = [
    extract_hashtags,
    compare_hashtags,
    get_trending_hashtags,
    analyze_hashtag_engagement,
]
