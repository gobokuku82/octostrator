"""
Phase 7: Insight Generator Agent

모든 ML 분석 결과를 종합하여 비즈니스 인사이트 생성
+ K-Beauty 트렌드 RAG 연동 (Hwahae 리포트 기반)
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)


def _extract_review_keywords_from_ml_result(ml_result: Dict[str, Any]) -> Optional["ReviewKeywords"]:
    """
    ML 분석 결과에서 ReviewKeywords 추출

    Args:
        ml_result: ML 파이프라인 결과
            - extractor: {top_keywords, unigrams, bigrams, ...}
            - absa_analyzer: {stats, ...}

    Returns:
        ReviewKeywords or None
    """
    try:
        from backend.app.services.rag import ReviewKeywords

        extractor_result = ml_result.get("extractor", {})
        absa_result = ml_result.get("absa_analyzer", {})

        # 키워드 추출
        top_keywords = extractor_result.get("top_keywords", [])
        unigrams = extractor_result.get("unigrams", [])

        # Primary keywords: 상위 키워드에서 추출
        primary_keywords = [kw["keyword"] for kw in top_keywords[:10]]

        # Ingredient keywords: 성분 관련 키워드 필터링 (간단한 휴리스틱)
        ingredient_hints = ["산", "추출물", "오일", "워터", "acid", "extract", "oil", "water"]
        ingredient_keywords = [
            kw["keyword"] for kw in unigrams
            if any(hint in kw["keyword"].lower() for hint in ingredient_hints)
        ][:5]

        # Sentiment keywords: ABSA 결과에서 추출
        aspect_stats = absa_result.get("stats", {}).get("aspect_stats", {})
        sentiment_keywords = list(aspect_stats.keys())[:5]

        # Brand keywords: 브랜드명 추출 (대문자로 시작하는 단어)
        brand_keywords = [
            kw["keyword"] for kw in unigrams
            if kw["keyword"][0].isupper() and len(kw["keyword"]) > 2
        ][:3]

        return ReviewKeywords(
            primary_keywords=primary_keywords,
            ingredient_keywords=ingredient_keywords,
            sentiment_keywords=sentiment_keywords,
            brand_keywords=brand_keywords,
            category=ml_result.get("category")
        )
    except Exception as e:
        logger.warning(f"Failed to extract ReviewKeywords: {e}")
        return None


@tool
def generate_insights(ml_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    ML 분석 결과를 종합하여 비즈니스 인사이트 생성

    Args:
        ml_result: 모든 ML 분석 결과
            - absa_analyzer: 감성 분석 결과
            - problem_classifier: 문제 분류 결과
            - extractor: 키워드 추출 결과
            - google_trends: 트렌드 분석 결과

    Returns:
        InsightReport (딕셔너리 형태)
    """
    from backend.app.services.ml.insight import get_insight_generator

    generator = get_insight_generator()
    report = generator.generate(ml_result)

    return {
        "report_id": report.report_id,
        "created_at": report.created_at,
        "summary": report.summary,
        "insights": [
            {
                "type": insight.insight_type.value,
                "priority": insight.priority.value,
                "title": insight.title,
                "description": insight.description,
                "recommendations": insight.recommendations,
                "data": insight.data
            }
            for insight in report.insights
        ],
        "key_metrics": report.key_metrics,
        "next_steps": report.next_steps
    }


@tool
def generate_insights_with_kbeauty_trends(
    ml_result: Dict[str, Any],
    brand: str = "Amorepacific"
) -> Dict[str, Any]:
    """
    ML 분석 결과 + K-Beauty 트렌드(Hwahae 리포트)를 결합하여 마케팅 인사이트 생성

    글로벌 고객 리뷰(올리브영, Amazon, SNS) 분석 결과와
    K-Beauty 트렌드 리포트를 결합하여 새로운 마케팅 인사이트를 도출합니다.

    Args:
        ml_result: ML 분석 결과 (extractor, absa_analyzer 등)
        brand: 타겟 브랜드명 (기본: Amorepacific)

    Returns:
        K-Beauty 트렌드가 결합된 인사이트 리포트
    """
    from backend.app.services.ml.insight import get_insight_generator
    from backend.app.services.rag import (
        TrendContextProvider,
        ReviewKeywords,
        create_insight_prompt,
    )

    result = {
        "report_id": None,
        "insights": [],
        "trend_context": None,
        "kbeauty_insights": None,
        "llm_prompt": None,
        "error": None,
    }

    # 1. 기본 인사이트 생성
    try:
        generator = get_insight_generator()
        report = generator.generate(ml_result)
        result["report_id"] = report.report_id
        result["insights"] = [
            {
                "type": insight.insight_type.value,
                "priority": insight.priority.value,
                "title": insight.title,
                "description": insight.description,
                "recommendations": insight.recommendations,
                "data": insight.data
            }
            for insight in report.insights
        ]
        result["key_metrics"] = report.key_metrics
        result["summary"] = report.summary
    except Exception as e:
        logger.error(f"Failed to generate base insights: {e}")
        result["error"] = f"Base insight generation failed: {str(e)}"

    # 2. K-Beauty 트렌드 컨텍스트 검색
    try:
        # ML 결과에서 키워드 추출
        review_keywords = _extract_review_keywords_from_ml_result(ml_result)

        if review_keywords and review_keywords.primary_keywords:
            provider = TrendContextProvider()
            trend_context = provider.get_context_for_keywords(review_keywords)

            result["trend_context"] = {
                "keywords_searched": trend_context.keywords,
                "snippets_found": trend_context.summary_stats.get("total_snippets", 0),
                "unique_articles": trend_context.summary_stats.get("unique_articles", 0),
                "avg_relevance": trend_context.summary_stats.get("avg_relevance", 0),
                "top_snippets": [
                    {
                        "keyword": s["keyword"],
                        "score": s["score"],
                        "title": s["title"][:60],
                        "text_preview": s["text"][:200]
                    }
                    for s in trend_context.trend_snippets[:5]
                ]
            }

            # 3. LLM 프롬프트 생성 (리뷰 분석 + 트렌드 컨텍스트)
            review_analysis = {
                "keywords": [kw["keyword"] for kw in ml_result.get("extractor", {}).get("top_keywords", [])[:10]],
                "sentiment": ml_result.get("absa_analyzer", {}).get("stats", {}).get("sentiment_distribution", {}),
                "concerns": [
                    cat for cat, count in
                    ml_result.get("problem_classifier", {}).get("summary", {}).get("by_category", {}).items()
                ][:5],
                "ingredients": review_keywords.ingredient_keywords,
            }

            llm_prompt = create_insight_prompt(review_analysis, trend_context, brand)
            result["llm_prompt"] = llm_prompt

            # 4. K-Beauty 트렌드 기반 인사이트 추가
            result["kbeauty_insights"] = {
                "trend_alignment": _analyze_trend_alignment(review_keywords, trend_context),
                "opportunity_areas": _identify_opportunities(review_keywords, trend_context),
                "recommended_focus": _get_recommended_focus(trend_context),
            }

        else:
            result["trend_context"] = {"error": "No keywords extracted from ML result"}

    except FileNotFoundError as e:
        logger.warning(f"FAISS index not found: {e}")
        result["trend_context"] = {"error": "K-Beauty trend index not available"}
    except Exception as e:
        logger.error(f"Failed to get K-Beauty trend context: {e}")
        result["trend_context"] = {"error": str(e)}

    return result


def _analyze_trend_alignment(review_keywords, trend_context) -> List[Dict[str, Any]]:
    """리뷰 키워드와 K-Beauty 트렌드의 정렬 분석"""
    alignments = []
    for snippet in trend_context.trend_snippets[:5]:
        if snippet["score"] > 0.5:
            alignments.append({
                "keyword": snippet["keyword"],
                "trend_title": snippet["title"][:50],
                "relevance": round(snippet["score"], 3),
                "insight": f"'{snippet['keyword']}' 키워드가 K-Beauty 트렌드와 높은 연관성"
            })
    return alignments


def _identify_opportunities(review_keywords, trend_context) -> List[str]:
    """트렌드 기반 기회 영역 식별"""
    opportunities = []

    # 트렌드에 있지만 리뷰에 적게 언급된 키워드 찾기
    review_kw_set = set(review_keywords.primary_keywords + review_keywords.ingredient_keywords)
    trend_keywords = set(s["keyword"] for s in trend_context.trend_snippets if s["score"] > 0.4)

    trending_gaps = trend_keywords - review_kw_set
    for gap in list(trending_gaps)[:3]:
        opportunities.append(f"트렌드 키워드 '{gap}'를 마케팅에 활용 고려")

    return opportunities


def _get_recommended_focus(trend_context) -> List[str]:
    """트렌드 기반 추천 포커스 영역"""
    if not trend_context.trend_snippets:
        return ["데이터 부족으로 추천 불가"]

    # 가장 관련성 높은 트렌드 추출
    top_trends = trend_context.trend_snippets[:3]
    return [
        f"{t['title'][:40]}... (관련도: {t['score']:.2f})"
        for t in top_trends
    ]


INSIGHT_GENERATOR_SYSTEM_PROMPT = """당신은 K-Beauty 비즈니스 인사이트 전문가입니다.

사용 가능한 도구:
1. generate_insights: 기본 ML 분석 결과를 종합하여 비즈니스 인사이트를 생성합니다.
2. generate_insights_with_kbeauty_trends: ML 분석 결과 + K-Beauty 트렌드(Hwahae 리포트)를 결합하여
   글로벌 마케팅 인사이트를 생성합니다. (권장)

K-Beauty 트렌드 연동 기능:
- 글로벌 고객 리뷰(올리브영, Amazon, SNS) 분석 결과와 Hwahae 트렌드 리포트를 결합
- 고객 기대 포인트 분석: 글로벌 고객이 K-beauty 브랜드에 기대하는 포인트 도출
- 트렌드 정렬 분석: 리뷰 키워드와 K-Beauty 트렌드의 연관성 분석
- 기회 영역 식별: 트렌드에 있지만 리뷰에 적게 언급된 성장 기회 포착

생성하는 인사이트 유형:
1. SENTIMENT_ALERT: 감성 분석 기반 경고
2. PROBLEM_CRITICAL: 심각한 문제 발견
3. TREND_OPPORTUNITY: 트렌드 기회 포착
4. TREND_RISING: 상승 트렌드
5. TREND_FALLING: 하락 트렌드
6. KEYWORD_HIGHLIGHT: 핵심 키워드 하이라이트
7. RECOMMENDATION: 추천 사항

우선순위 (HIGH > MEDIUM > LOW)에 따라 정렬된 인사이트를 제공합니다.
K-Beauty 트렌드 데이터가 필요한 경우 generate_insights_with_kbeauty_trends를 사용하세요.
"""


def create_insight_generator_agent(model: str = "gpt-4o-mini", with_kbeauty_trends: bool = True):
    """
    Insight Generator Agent 생성

    Args:
        model: LLM 모델 (기본: gpt-4o-mini)
        with_kbeauty_trends: K-Beauty 트렌드 RAG 도구 포함 여부 (기본: True)

    Returns:
        LangGraph ReAct Agent
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        # 도구 목록 구성
        tools = [generate_insights]
        if with_kbeauty_trends:
            tools.append(generate_insights_with_kbeauty_trends)

        agent = create_react_agent(
            model=llm,
            tools=tools,
            state_modifier=SystemMessage(content=INSIGHT_GENERATOR_SYSTEM_PROMPT)
        )

        return agent
    except ImportError as e:
        print(f"[InsightGeneratorAgent] LangGraph not available: {e}")
        return None


_insight_generator_agent = None


def get_insight_generator_agent():
    """Insight Generator Agent 싱글톤 반환"""
    global _insight_generator_agent
    if _insight_generator_agent is None:
        _insight_generator_agent = create_insight_generator_agent()
    return _insight_generator_agent


# Direct function calls (without Agent)
def generate_insights_direct(ml_result: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 없이 직접 인사이트 생성"""
    return generate_insights.invoke({"ml_result": ml_result})


def generate_insights_with_trends_direct(
    ml_result: Dict[str, Any],
    brand: str = "Amorepacific"
) -> Dict[str, Any]:
    """
    Agent 없이 직접 K-Beauty 트렌드 결합 인사이트 생성

    Args:
        ml_result: ML 분석 결과
        brand: 타겟 브랜드명

    Returns:
        K-Beauty 트렌드가 결합된 인사이트 리포트
    """
    return generate_insights_with_kbeauty_trends.invoke({
        "ml_result": ml_result,
        "brand": brand
    })
