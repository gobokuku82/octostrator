"""
Phase 4: Sentiment Analyzer Agent

ABSA(Aspect-Based Sentiment Analysis) 감성 분석
"""

from typing import List, Dict, Any
from langchain_core.tools import tool


@tool
def analyze_sentiment(reviews: List[Dict]) -> Dict[str, Any]:
    """
    ABSA 감성 분석 (긍정/부정 분류 + Aspect별 분석)

    Args:
        reviews: preprocess_reviews의 결과

    Returns:
        감성 분석 결과 (긍정/부정 리뷰 분리)
    """
    from backend.app.services.ml.analysis import get_absa_analyzer

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


SENTIMENT_ANALYZER_SYSTEM_PROMPT = """당신은 ABSA 감성 분석 전문가입니다.

사용 가능한 도구:
- analyze_sentiment: ABSA(Aspect-Based Sentiment Analysis) 감성 분석 수행

분석 내용:
1. 전체 감성 분류 (긍정/부정/중립)
2. Aspect별 감성 분석 (효과, 보습, 향, 질감, 가격, 자극, 패키지)
3. 신뢰도 점수 계산

부정 리뷰는 이후 문제 분류 단계에서 상세 분석됩니다.
"""


def create_sentiment_analyzer_agent(model: str = "gpt-4o-mini"):
    """Sentiment Analyzer Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[analyze_sentiment],
            state_modifier=SystemMessage(content=SENTIMENT_ANALYZER_SYSTEM_PROMPT)
        )

        return agent
    except ImportError as e:
        print(f"[SentimentAnalyzerAgent] LangGraph not available: {e}")
        return None


_sentiment_analyzer_agent = None


def get_sentiment_analyzer_agent():
    """Sentiment Analyzer Agent 싱글톤 반환"""
    global _sentiment_analyzer_agent
    if _sentiment_analyzer_agent is None:
        _sentiment_analyzer_agent = create_sentiment_analyzer_agent()
    return _sentiment_analyzer_agent


# Direct function call (without Agent)
def analyze_sentiment_direct(reviews: List[Dict]) -> Dict[str, Any]:
    """Agent 없이 직접 감성 분석"""
    return analyze_sentiment.invoke({"reviews": reviews})
