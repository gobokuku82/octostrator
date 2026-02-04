"""
Phase 6: Google Trends Agent

Google Trends 분석 (목업 지원)
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool


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
        트렌드 분석 결과
    """
    from backend.app.services.ml.trends import get_google_trends_analyzer
    import os

    # 환경 변수로 mock 여부 결정 (기본: 실제 API 사용)
    use_mock = os.environ.get("USE_MOCK_TRENDS", "false").lower() == "true"
    analyzer = get_google_trends_analyzer(use_mock=use_mock)
    result = analyzer.analyze(keyword, related_keywords, timeframe, geo)

    return {
        "success": True,
        "is_mock": result.is_mock,  # True if mock data, False if real Google Trends data
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
    import os

    # 환경 변수로 mock 여부 결정 (기본: 실제 API 사용)
    use_mock = os.environ.get("USE_MOCK_TRENDS", "false").lower() == "true"
    analyzer = get_google_trends_analyzer(use_mock=use_mock)
    return analyzer.compare_brands(brands, timeframe, geo)


GOOGLE_TRENDS_SYSTEM_PROMPT = """당신은 Google Trends 분석 전문가입니다.

사용 가능한 도구:
1. analyze_trends: 특정 키워드의 Google Trends 분석
   - 시간별 관심도 추이
   - 관련 검색어 (상승/인기)
   - 지역별 관심도

2. compare_brand_trends: 브랜드 간 트렌드 비교
   - 브랜드별 평균 관심도
   - 순위 비교
   - 최근 트렌드 방향

분석 시 고려사항:
- 트렌드 상승/하락 패턴 파악
- 계절성 분석
- 경쟁사 대비 포지션
- 관련 검색어를 통한 소비자 관심사 파악
"""


def create_google_trends_agent(model: str = "gpt-4o-mini"):
    """Google Trends Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[analyze_trends, compare_brand_trends],
            state_modifier=SystemMessage(content=GOOGLE_TRENDS_SYSTEM_PROMPT)
        )

        return agent
    except ImportError as e:
        print(f"[GoogleTrendsAgent] LangGraph not available: {e}")
        return None


_google_trends_agent = None


def get_google_trends_agent():
    """Google Trends Agent 싱글톤 반환"""
    global _google_trends_agent
    if _google_trends_agent is None:
        _google_trends_agent = create_google_trends_agent()
    return _google_trends_agent


# Direct function call (without Agent)
def analyze_trends_direct(
    keyword: str,
    related_keywords: List[str] = None,
    timeframe: str = "today 3-m",
    geo: str = ""
) -> Dict[str, Any]:
    """Agent 없이 직접 트렌드 분석"""
    return analyze_trends.invoke({
        "keyword": keyword,
        "related_keywords": related_keywords,
        "timeframe": timeframe,
        "geo": geo
    })
