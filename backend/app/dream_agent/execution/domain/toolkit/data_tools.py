"""Data Tools - 데이터 변환/분석 Tools

ML 결과 데이터 처리 및 변환 기능 제공
"""

from typing import Dict, Any, List
from langchain_core.tools import tool


@tool
def extract_ml_insights(ml_result: Dict[str, Any]) -> List[str]:
    """
    ML 분석 결과에서 인사이트 추출

    Args:
        ml_result: ML 분석 결과

    Returns:
        인사이트 목록
    """
    insights = []

    # 기존 insights 필드가 있으면 사용
    if "insights" in ml_result:
        return ml_result["insights"]

    # 감성 분석 인사이트
    if "sentiment" in ml_result:
        sentiment = ml_result["sentiment"]
        positive = sentiment.get('positive', 0)
        negative = sentiment.get('negative', 0)
        neutral = sentiment.get('neutral', 0)

        insights.append(f"긍정 비율: {positive:.1%}")
        insights.append(f"부정 비율: {negative:.1%}")
        insights.append(f"중립 비율: {neutral:.1%}")

    # 키워드 인사이트
    if "keywords" in ml_result:
        top_keywords = ml_result["keywords"][:5]
        insights.append(f"주요 키워드: {', '.join(top_keywords)}")

    # 평점 인사이트
    if "avg_rating" in ml_result:
        avg_rating = ml_result["avg_rating"]
        insights.append(f"평균 평점: {avg_rating:.1f}/5.0")

    # 리뷰 수 인사이트
    if "total_reviews" in ml_result:
        total_reviews = ml_result["total_reviews"]
        insights.append(f"총 리뷰 수: {total_reviews:,}개")

    return insights


@tool
def format_metrics_for_dashboard(ml_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    ML 결과를 대시보드용 메트릭으로 변환

    Args:
        ml_result: ML 분석 결과

    Returns:
        대시보드용 메트릭
    """
    metrics = {
        "total_reviews": ml_result.get("total_reviews", 0),
        "avg_rating": ml_result.get("avg_rating", 0),
        "sentiment_score": ml_result.get("sentiment_score", 0)
    }

    # 감성 비율 추가
    if "sentiment" in ml_result:
        sentiment = ml_result["sentiment"]
        metrics["positive_ratio"] = sentiment.get("positive", 0)
        metrics["negative_ratio"] = sentiment.get("negative", 0)
        metrics["neutral_ratio"] = sentiment.get("neutral", 0)

    # 키워드 추가
    if "keywords" in ml_result:
        metrics["top_keywords"] = ml_result["keywords"][:10]

    return metrics


@tool
def calculate_sentiment_trend(ml_result: Dict[str, Any]) -> str:
    """
    감성 트렌드 분석

    Args:
        ml_result: ML 분석 결과

    Returns:
        트렌드 요약 (긍정적/부정적/중립적)
    """
    if "sentiment" not in ml_result:
        return "중립적"

    sentiment = ml_result["sentiment"]
    positive = sentiment.get("positive", 0)
    negative = sentiment.get("negative", 0)

    if positive > 0.6:
        return "긍정적"
    elif negative > 0.3:
        return "부정적"
    else:
        return "중립적"
