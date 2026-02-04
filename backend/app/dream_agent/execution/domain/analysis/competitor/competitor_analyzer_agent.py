"""
Competitor Analyzer Agent

브랜드별 리뷰 데이터를 비교 분석하여 경쟁 인사이트 도출
전략적 의사결정 지원을 위한 SWOT 분석 및 포지셔닝 분석 제공
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# 로거 설정
logger = logging.getLogger(__name__)


@tool
def compare_brands(
    brand_reviews: Dict[str, List[Dict]],
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    여러 브랜드의 리뷰를 비교 분석

    Args:
        brand_reviews: 브랜드별 리뷰 데이터
            예: {"laneige": [리뷰1, 리뷰2, ...], "sulwhasoo": [리뷰1, ...]}
        metrics: 비교할 메트릭스 ["sentiment", "keywords", "problems"]
            - sentiment: 긍정/부정 비율 비교
            - keywords: 핵심 키워드 비교 (공통/고유)
            - problems: 문제점 비교

    Returns:
        브랜드 비교 분석 결과:
        {
            "brand_metrics": {...},   # 브랜드별 상세 메트릭스
            "comparison": {...},      # 비교 분석
            "ranking": [...],         # 종합 랭킹
            "insights": [...],        # 자동 생성 인사이트
            "swot": {...}             # SWOT 분석
        }
    """
    from backend.app.services.ml.analysis import get_competitor_analyzer

    logger.info(
        f"[CompetitorAgent] Comparing {len(brand_reviews)} brands: "
        f"{list(brand_reviews.keys())}"
    )

    analyzer = get_competitor_analyzer()
    result = analyzer.compare_brands(brand_reviews, metrics=metrics)

    logger.info(f"[CompetitorAgent] Ranking: {[r['brand'] for r in result.ranking]}")

    return {
        "brand_metrics": result.brand_metrics,
        "comparison": result.comparison,
        "ranking": result.ranking,
        "insights": result.insights,
        "swot": result.swot,
        "analyzed_at": result.analyzed_at,
    }


@tool
def analyze_competitive_position(
    primary_brand: str,
    competitor_brands: List[str],
    reviews: List[Dict],
) -> Dict[str, Any]:
    """
    특정 브랜드의 경쟁 포지션 분석

    Args:
        primary_brand: 주요 분석 대상 브랜드
        competitor_brands: 비교 대상 경쟁 브랜드 리스트
        reviews: 전체 리뷰 데이터 (brand/product_name 필드 포함)

    Returns:
        경쟁 포지션 분석 결과
    """
    from backend.app.services.ml.analysis import get_competitor_analyzer

    logger.info(
        f"[CompetitorAgent] Analyzing position of '{primary_brand}' "
        f"vs {competitor_brands}"
    )

    # 브랜드별 리뷰 분류
    brand_reviews: Dict[str, List[Dict]] = {primary_brand: []}
    for comp in competitor_brands:
        brand_reviews[comp] = []

    for review in reviews:
        text = (review.get("text", "") + " " + review.get("product_name", "")).lower()

        # 주요 브랜드 매칭
        if primary_brand.lower() in text:
            brand_reviews[primary_brand].append(review)
            continue

        # 경쟁 브랜드 매칭
        for comp in competitor_brands:
            if comp.lower() in text:
                brand_reviews[comp].append(review)
                break

    # 빈 브랜드 제거
    brand_reviews = {b: r for b, r in brand_reviews.items() if r}

    if not brand_reviews:
        return {
            "error": "No reviews found for the specified brands",
            "primary_brand": primary_brand,
            "competitor_brands": competitor_brands,
        }

    analyzer = get_competitor_analyzer()
    result = analyzer.compare_brands(brand_reviews)

    # 주요 브랜드 포지션 추출
    position = None
    for r in result.ranking:
        if r["brand"] == primary_brand:
            position = r
            break

    return {
        "primary_brand": primary_brand,
        "position": position,
        "ranking": result.ranking,
        "swot": result.swot,
        "insights": result.insights,
        "brand_metrics": result.brand_metrics,
    }


@tool
def generate_competitive_report(
    brand_reviews: Dict[str, List[Dict]],
    report_type: str = "summary",
) -> Dict[str, Any]:
    """
    경쟁사 분석 리포트 생성

    Args:
        brand_reviews: 브랜드별 리뷰 데이터
        report_type: 리포트 유형
            - "summary": 요약 리포트 (기본)
            - "detailed": 상세 리포트
            - "executive": 임원용 요약

    Returns:
        리포트 데이터
    """
    from backend.app.services.ml.analysis import get_competitor_analyzer

    logger.info(f"[CompetitorAgent] Generating {report_type} report")

    analyzer = get_competitor_analyzer()
    result = analyzer.compare_brands(brand_reviews)

    # 리포트 타입별 구성
    if report_type == "executive":
        return {
            "type": "executive",
            "title": "경쟁사 분석 Executive Summary",
            "key_findings": result.insights[:3],
            "top_brand": result.ranking[0] if result.ranking else None,
            "recommendation": _generate_recommendation(result),
        }

    elif report_type == "detailed":
        return {
            "type": "detailed",
            "title": "경쟁사 상세 분석 리포트",
            "brand_metrics": result.brand_metrics,
            "comparison": result.comparison,
            "ranking": result.ranking,
            "insights": result.insights,
            "swot": result.swot,
            "analyzed_at": result.analyzed_at,
        }

    else:  # summary
        return {
            "type": "summary",
            "title": "경쟁사 분석 요약",
            "brands_analyzed": list(brand_reviews.keys()),
            "ranking": result.ranking,
            "key_insights": result.insights,
            "swot_summary": {
                "strengths": result.swot.get("strengths", [])[:2],
                "opportunities": result.swot.get("opportunities", [])[:2],
            },
        }


def _generate_recommendation(result) -> str:
    """분석 결과 기반 추천 생성"""
    if not result.ranking:
        return "분석할 데이터가 부족합니다."

    top_brand = result.ranking[0]
    opportunities = result.swot.get("opportunities", [])

    if opportunities:
        return (
            f"'{top_brand['brand']}'이(가) 현재 1위입니다. "
            f"다음 기회 영역에 집중하세요: {opportunities[0]}"
        )
    return f"'{top_brand['brand']}'의 긍정적인 포지션을 유지하세요."


@tool
def get_brand_strengths_weaknesses(
    brand: str,
    reviews: List[Dict],
) -> Dict[str, Any]:
    """
    특정 브랜드의 강점/약점 분석

    Args:
        brand: 분석할 브랜드명
        reviews: 리뷰 데이터

    Returns:
        강점/약점 분석 결과
    """
    from backend.app.services.ml.analysis import get_competitor_analyzer

    logger.info(f"[CompetitorAgent] Analyzing strengths/weaknesses for '{brand}'")

    # 브랜드 리뷰 필터링
    brand_reviews = []
    brand_lower = brand.lower()

    for review in reviews:
        text = (review.get("text", "") + " " + review.get("product_name", "")).lower()
        if brand_lower in text:
            brand_reviews.append(review)

    if not brand_reviews:
        return {
            "brand": brand,
            "error": f"No reviews found for brand '{brand}'",
        }

    analyzer = get_competitor_analyzer()
    metrics = analyzer.analyze_brand(brand, brand_reviews)

    return {
        "brand": brand,
        "review_count": metrics.review_count,
        "strengths": {
            "positive_ratio": metrics.positive_ratio,
            "avg_rating": metrics.avg_rating,
            "top_keywords": metrics.top_keywords,
            "total_engagement": metrics.total_engagement,
        },
        "weaknesses": {
            "negative_ratio": metrics.negative_ratio,
            "top_problems": metrics.top_problems,
        },
        "sentiment_breakdown": {
            "positive": metrics.positive_count,
            "negative": metrics.negative_count,
            "neutral": metrics.neutral_count,
        },
    }


# ============================================================
# Agent System Prompt
# ============================================================

COMPETITOR_ANALYZER_SYSTEM_PROMPT = """당신은 K-Beauty 경쟁사 분석 전문가입니다.

사용 가능한 도구:
1. compare_brands: 여러 브랜드를 비교 분석합니다.
   - brand_metrics: 브랜드별 긍정률, 평점, 키워드, 문제점
   - comparison: 메트릭스별 비교 (sentiment, keywords, problems)
   - ranking: 종합 점수 기반 순위
   - insights: 자동 생성 인사이트
   - swot: SWOT 분석

2. analyze_competitive_position: 특정 브랜드의 경쟁 포지션을 분석합니다.
   - 주요 브랜드와 경쟁사들의 상대적 위치 파악

3. generate_competitive_report: 경쟁사 분석 리포트를 생성합니다.
   - summary: 요약 리포트
   - detailed: 상세 리포트
   - executive: 임원용 요약

4. get_brand_strengths_weaknesses: 특정 브랜드의 강점/약점을 분석합니다.

분석 메트릭스:
- sentiment: 긍정/부정 비율, 평균 평점
- keywords: 핵심 키워드 (공통 vs 고유)
- problems: 주요 문제점 (자극, 건조, 끈적임, 효과없음, 가격, 트러블)

SWOT 분석:
- Strengths: 높은 긍정률, 우수한 평점, 핵심 강점 키워드
- Weaknesses: 부정 평가율, 주요 개선 필요 영역
- Opportunities: 경쟁사 약점에서의 차별화 기회
- Threats: 경쟁사의 높은 긍정 평가율

사용 예시:
- "라네즈와 설화수 비교해줘" → compare_brands({"laneige": [...], "sulwhasoo": [...]})
- "라네즈의 경쟁 포지션 분석" → analyze_competitive_position("laneige", ["sulwhasoo", "innisfree"], reviews)
- "경쟁사 분석 리포트 생성" → generate_competitive_report(brand_reviews, "summary")
"""


# ============================================================
# Agent Creation
# ============================================================

def create_competitor_analyzer_agent(model: str = "gpt-4o-mini"):
    """Competitor Analyzer Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[
                compare_brands,
                analyze_competitive_position,
                generate_competitive_report,
                get_brand_strengths_weaknesses,
            ],
            state_modifier=SystemMessage(content=COMPETITOR_ANALYZER_SYSTEM_PROMPT)
        )

        logger.info("[CompetitorAgent] Agent created successfully")
        return agent

    except ImportError as e:
        logger.error(f"[CompetitorAgent] LangGraph not available: {e}")
        return None


_competitor_analyzer_agent = None


def get_competitor_analyzer_agent():
    """Competitor Analyzer Agent 싱글톤 반환"""
    global _competitor_analyzer_agent
    if _competitor_analyzer_agent is None:
        _competitor_analyzer_agent = create_competitor_analyzer_agent()
    return _competitor_analyzer_agent


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def compare_brands_direct(
    brand_reviews: Dict[str, List[Dict]],
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Agent 없이 직접 브랜드 비교"""
    logger.info(f"[CompetitorAgent] Direct comparison of {len(brand_reviews)} brands")

    return compare_brands.invoke({
        "brand_reviews": brand_reviews,
        "metrics": metrics or ["sentiment", "keywords", "problems"],
    })


def analyze_position_direct(
    primary_brand: str,
    competitor_brands: List[str],
    reviews: List[Dict],
) -> Dict[str, Any]:
    """Agent 없이 직접 포지션 분석"""
    return analyze_competitive_position.invoke({
        "primary_brand": primary_brand,
        "competitor_brands": competitor_brands,
        "reviews": reviews,
    })


def get_strengths_weaknesses_direct(
    brand: str,
    reviews: List[Dict],
) -> Dict[str, Any]:
    """Agent 없이 직접 강점/약점 분석"""
    return get_brand_strengths_weaknesses.invoke({
        "brand": brand,
        "reviews": reviews,
    })
