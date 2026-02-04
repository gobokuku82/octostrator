"""
Hashtag Analyzer Agent

SNS 데이터(TikTok, YouTube)에서 해시태그를 분석하는 Agent
바이럴 마케팅 인사이트 발굴을 위한 트렌드 분석 제공
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# 로거 설정
logger = logging.getLogger(__name__)


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

    logger.info(f"[HashtagAgent] Analyzing hashtags from {len(reviews)} reviews (top_n={top_n})")

    analyzer = get_hashtag_analyzer()
    result = analyzer.analyze(reviews, top_n=top_n, min_count=min_count)

    logger.info(
        f"[HashtagAgent] Found {result.stats['unique_hashtags']} unique hashtags, "
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
        f"[HashtagAgent] Comparing hashtags - "
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

    logger.info(f"[HashtagAgent] Getting trending hashtags (category={category}, top_n={top_n})")

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
    import re
    from backend.app.services.ml.analysis import get_hashtag_analyzer

    hashtag_clean = hashtag.lstrip('#').lower()
    logger.info(f"[HashtagAgent] Analyzing engagement for #{hashtag_clean}")

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
# Agent System Prompt
# ============================================================

HASHTAG_ANALYZER_SYSTEM_PROMPT = """당신은 SNS 해시태그 분석 전문가입니다.

사용 가능한 도구:
1. extract_hashtags: 리뷰에서 해시태그를 추출하고 분석합니다.
   - top_hashtags: 빈도 기준 상위 해시태그
   - rising_hashtags: engagement 기준 상승 해시태그
   - brand_hashtags: 브랜드별 해시태그 현황
   - category_breakdown: kbeauty, skincare, beauty, viral, review 카테고리별 분류

2. compare_hashtags: 브랜드와 경쟁사의 해시태그를 비교합니다.
   - 브랜드만의 고유 해시태그 식별
   - 경쟁사와 공유하는 해시태그 분석

3. get_trending_hashtags: 트렌딩 해시태그를 추출합니다.
   - category 파라미터로 특정 카테고리만 필터링 가능

4. analyze_hashtag_engagement: 특정 해시태그의 engagement를 분석합니다.
   - likes, views, shares 등 상세 지표 제공

지원 카테고리:
- kbeauty: #kbeauty, #koreanbeauty, #koreanskincare 등
- skincare: #skincare, #glowingskin, #피부관리 등
- beauty: #beauty, #beautytips, #뷰티 등
- viral: #fyp, #foryou, #trending, #추천 등
- review: #review, #리뷰, #후기, #언박싱 등

분석 인사이트:
- 상승 해시태그는 바이럴 콘텐츠 기획에 활용
- 브랜드 해시태그는 마케팅 캠페인 효과 측정에 활용
- 경쟁사 비교로 차별화 포인트 발굴

주의: SNS 데이터(TikTok, YouTube)가 없으면 해시태그 분석이 제한됩니다.
"""


# ============================================================
# Agent Creation
# ============================================================

def create_hashtag_analyzer_agent(model: str = "gpt-4o-mini"):
    """Hashtag Analyzer Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[
                extract_hashtags,
                compare_hashtags,
                get_trending_hashtags,
                analyze_hashtag_engagement,
            ],
            state_modifier=SystemMessage(content=HASHTAG_ANALYZER_SYSTEM_PROMPT)
        )

        logger.info("[HashtagAgent] Agent created successfully")
        return agent

    except ImportError as e:
        logger.error(f"[HashtagAgent] LangGraph not available: {e}")
        return None


_hashtag_analyzer_agent = None


def get_hashtag_analyzer_agent():
    """Hashtag Analyzer Agent 싱글톤 반환"""
    global _hashtag_analyzer_agent
    if _hashtag_analyzer_agent is None:
        _hashtag_analyzer_agent = create_hashtag_analyzer_agent()
    return _hashtag_analyzer_agent


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def extract_hashtags_direct(
    reviews: List[Dict],
    top_n: int = 20,
) -> Dict[str, Any]:
    """Agent 없이 직접 해시태그 추출"""
    logger.info(f"[HashtagAgent] Direct extraction from {len(reviews)} reviews")

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
