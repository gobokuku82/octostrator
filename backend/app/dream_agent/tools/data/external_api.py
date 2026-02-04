"""External API Tool - 외부 API 연동

Google Trends 등 외부 API 연동 기능을 제공합니다.

(기존 ml_execution/agents/google_trends_agent.py에서 이전)
"""

import os
import logging
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def analyze_trends(
    keyword: str,
    related_keywords: Optional[List[str]] = None,
    timeframe: str = "today 3-m",
    geo: str = ""
) -> Dict[str, Any]:
    """
    Google Trends 분석 수행

    Args:
        keyword: 메인 검색 키워드 (예: "laneige", "설화수")
        related_keywords: 함께 비교할 키워드 목록 (최대 4개)
        timeframe: 분석 기간 ("today 3-m", "today 12-m", "today 5-y")
        geo: 지역 코드 ("KR", "US", "" = 전세계)

    Returns:
        트렌드 분석 결과:
        {
            "success": bool,
            "is_mock": bool,
            "data": {
                "keyword": str,
                "timeframe": str,
                "geo": str,
                "interest_over_time": [...],
                "rising_queries": [...],
                "top_queries": [...],
                "top_regions": [...],
                "trend_direction": str,
                "change_percent": float,
            }
        }
    """
    from .mock_loader import is_mock_mode, get_mock_loader

    logger.info(f"[ExternalAPI] Analyzing trends for '{keyword}'")

    # Mock 모드: data/mock에서 트렌드 데이터 로드
    if is_mock_mode():
        logger.info(f"[ExternalAPI] Using mock trends data from data/mock")
        loader = get_mock_loader()
        return loader.get_trends_result(keyword, timeframe, geo or "KR")

    # 실제 API 사용
    try:
        from backend.app.services.ml.trends import get_google_trends_analyzer

        # 환경 변수로 서비스 내 mock 여부 결정
        use_service_mock = os.environ.get("USE_MOCK_TRENDS", "false").lower() == "true"
        analyzer = get_google_trends_analyzer(use_mock=use_service_mock)
        result = analyzer.analyze(keyword, related_keywords, timeframe, geo)

        logger.info(f"[ExternalAPI] Trends analysis complete (is_mock={result.is_mock})")

        return {
            "success": True,
            "is_mock": result.is_mock,
            "data": {
                "keyword": result.keyword,
                "timeframe": result.timeframe,
                "geo": result.geo,
                "interest_over_time": result.interest_over_time,
                "rising_queries": result.rising_queries,
                "top_queries": result.top_queries,
                "top_regions": result.top_regions,
                "trend_direction": result.trend_direction,
                "change_percent": result.change_percent,
            }
        }
    except ImportError:
        logger.warning("[ExternalAPI] Trends analyzer not available, using mock data")
        loader = get_mock_loader()
        return loader.get_trends_result(keyword, timeframe, geo or "KR")


@tool
def compare_brand_trends(
    brands: List[str],
    timeframe: str = "today 12-m",
    geo: str = "KR"
) -> Dict[str, Any]:
    """
    브랜드 간 트렌드 비교 분석

    Args:
        brands: 비교할 브랜드 목록 (예: ["laneige", "sulwhasoo", "innisfree"])
        timeframe: 분석 기간
        geo: 지역 코드

    Returns:
        브랜드 비교 결과
    """
    from backend.app.services.ml.trends import get_google_trends_analyzer

    logger.info(f"[ExternalAPI] Comparing brand trends: {brands}")

    # 환경 변수로 mock 여부 결정 (기본: 실제 API 사용)
    use_mock = os.environ.get("USE_MOCK_TRENDS", "false").lower() == "true"
    analyzer = get_google_trends_analyzer(use_mock=use_mock)
    result = analyzer.compare_brands(brands, timeframe, geo)

    logger.info(f"[ExternalAPI] Brand comparison complete")

    return result


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("google_trends")
class GoogleTrendsTool(BaseTool):
    """Google Trends 분석 도구

    BaseTool 패턴으로 구현된 Google Trends 분석기.
    트렌드 분석 및 브랜드 비교 기능을 제공합니다.
    """

    name: str = "google_trends"
    description: str = "Google Trends를 사용한 키워드/브랜드 트렌드 분석"
    category: str = "data"
    version: str = "1.0.0"

    def execute(
        self,
        keyword: str,
        related_keywords: Optional[List[str]] = None,
        timeframe: str = "today 3-m",
        geo: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """트렌드 분석 실행

        Args:
            keyword: 검색 키워드
            related_keywords: 관련 키워드 목록
            timeframe: 분석 기간
            geo: 지역 코드

        Returns:
            트렌드 분석 결과
        """
        return analyze_trends.invoke({
            "keyword": keyword,
            "related_keywords": related_keywords,
            "timeframe": timeframe,
            "geo": geo,
        })

    async def aexecute(
        self,
        keyword: str,
        related_keywords: Optional[List[str]] = None,
        timeframe: str = "today 3-m",
        geo: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 트렌드 분석 실행"""
        return await analyze_trends.ainvoke({
            "keyword": keyword,
            "related_keywords": related_keywords,
            "timeframe": timeframe,
            "geo": geo,
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def analyze_trends_direct(
    keyword: str,
    related_keywords: List[str] = None,
    timeframe: str = "today 3-m",
    geo: str = ""
) -> Dict[str, Any]:
    """Agent 없이 직접 트렌드 분석"""
    logger.info(f"[ExternalAPI] Direct trends analysis: keyword='{keyword}'")
    return analyze_trends.invoke({
        "keyword": keyword,
        "related_keywords": related_keywords,
        "timeframe": timeframe,
        "geo": geo
    })


def compare_brand_trends_direct(
    brands: List[str],
    timeframe: str = "today 12-m",
    geo: str = "KR"
) -> Dict[str, Any]:
    """Agent 없이 직접 브랜드 비교"""
    logger.info(f"[ExternalAPI] Direct brand comparison: brands={brands}")
    return compare_brand_trends.invoke({
        "brands": brands,
        "timeframe": timeframe,
        "geo": geo,
    })


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

EXTERNAL_API_TOOLS = [
    analyze_trends,
    compare_brand_trends,
]
