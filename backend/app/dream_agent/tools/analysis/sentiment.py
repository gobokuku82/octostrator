"""Sentiment Analysis Tool - ABSA 감성 분석

ABSA(Aspect-Based Sentiment Analysis)를 통한 감성 분석 기능을 제공합니다.

(기존 ml_execution/agents/sentiment_analyzer_agent.py에서 이전)
"""

import logging
from typing import List, Dict, Any

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def analyze_sentiment(reviews: List[Dict]) -> Dict[str, Any]:
    """
    ABSA 감성 분석 (긍정/부정 분류 + Aspect별 분석)

    Args:
        reviews: preprocess_reviews의 결과

    Returns:
        감성 분석 결과:
        {
            "positive_reviews": [...],  # 긍정 리뷰 리스트
            "negative_reviews": [...],  # 부정 리뷰 리스트
            "stats": {
                "total": int,
                "positive": int,
                "negative": int,
                "negative_ratio": float,
                "aspect_stats": {...}
            }
        }
    """
    from backend.app.services.ml.analysis import get_absa_analyzer

    logger.info(f"[Sentiment] Analyzing sentiment for {len(reviews)} reviews")

    analyzer = get_absa_analyzer()

    positive_reviews = []
    negative_reviews = []
    aspect_stats: Dict[str, Dict[str, int]] = {}

    for review in reviews:
        text = review.get("cleaned_text", review.get("text", ""))
        tokens = review.get("tokens", [])

        result = analyzer.analyze(text, tokens)

        analyzed = {
            **review,
            "sentiment": result.overall_sentiment.value,
            "confidence": float(round(result.overall_confidence, 4)),
            "is_negative": result.is_negative,
            "aspects": [
                {
                    "aspect": a.aspect,
                    "sentiment": a.sentiment.value,
                    "confidence": float(a.confidence),
                    "keywords": a.keywords
                }
                for a in result.aspects
            ]
        }

        if result.is_negative:
            negative_reviews.append(analyzed)
        else:
            positive_reviews.append(analyzed)

        # Aspect 통계
        for asp in result.aspects:
            name = asp.aspect
            sent = asp.sentiment.value
            if name not in aspect_stats:
                aspect_stats[name] = {"positive": 0, "negative": 0, "neutral": 0}
            aspect_stats[name][sent] += 1

    total = len(positive_reviews) + len(negative_reviews)

    logger.info(
        f"[Sentiment] Analysis complete: "
        f"{len(positive_reviews)} positive, {len(negative_reviews)} negative"
    )

    return {
        "positive_reviews": positive_reviews,
        "negative_reviews": negative_reviews,
        "stats": {
            "total": total,
            "positive": len(positive_reviews),
            "negative": len(negative_reviews),
            "negative_ratio": round(len(negative_reviews) / max(total, 1) * 100, 1),
            "aspect_stats": aspect_stats
        }
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("sentiment")
class SentimentTool(BaseTool):
    """ABSA 감성 분석 도구

    BaseTool 패턴으로 구현된 Sentiment Analyzer.
    Aspect-Based Sentiment Analysis를 수행합니다.
    """

    name: str = "sentiment"
    description: str = "ABSA 감성 분석 (긍정/부정 분류 + Aspect별 분석)"
    category: str = "analysis"
    version: str = "1.0.0"

    def execute(
        self,
        reviews: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """감성 분석 실행

        Args:
            reviews: 분석할 리뷰 리스트

        Returns:
            감성 분석 결과
        """
        return analyze_sentiment.invoke({"reviews": reviews})

    async def aexecute(
        self,
        reviews: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 감성 분석 실행"""
        return await analyze_sentiment.ainvoke({"reviews": reviews})


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def analyze_sentiment_direct(reviews: List[Dict]) -> Dict[str, Any]:
    """Agent 없이 직접 감성 분석"""
    logger.info(f"[Sentiment] Direct analysis: {len(reviews)} reviews")
    return analyze_sentiment.invoke({"reviews": reviews})


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

SENTIMENT_TOOLS = [
    analyze_sentiment,
]
