"""
Phase 5: Problem Classifier Agent

부정 리뷰 문제 분류 (8개 카테고리, 3단계 심각도)
"""

from typing import List, Dict, Any
from langchain_core.tools import tool


@tool
def classify_problems(negative_reviews: List[Dict]) -> Dict[str, Any]:
    """
    부정 리뷰 문제 분류 (8개 카테고리, 3단계 심각도)

    카테고리: 피부트러블_자극, 효과미흡, 품질불량, 향불만, 용기불량, 가격불만, 용량불만, 배송문제
    심각도: critical, important, minor

    Args:
        negative_reviews: analyze_sentiment의 negative_reviews

    Returns:
        문제 분류 결과
    """
    from backend.app.services.ml.classification import get_problem_classifier

    if not negative_reviews:
        return {
            "classifications": [],
            "critical_issues": [],
            "summary": {
                "total": 0,
                "by_category": {},
                "by_severity": {"critical": 0, "important": 0, "minor": 0}
            }
        }

    classifier = get_problem_classifier()

    classifications = []
    by_category: Dict[str, int] = {}
    by_severity = {"critical": 0, "important": 0, "minor": 0}
    critical_issues = []

    for review in negative_reviews:
        text = review.get("cleaned_text", review.get("text", ""))
        tokens = review.get("tokens", [])

        results = classifier.classify(text, tokens=tokens)

        for p in results:
            item = {
                "category": p.category,
                "severity": p.severity,
                "confidence": p.confidence,
                "keywords": p.keywords_found,
                "snippet": p.original_snippet[:150],
                "product": review.get("product_name"),
                "source": review.get("source"),
            }
            classifications.append(item)

            by_category[p.category] = by_category.get(p.category, 0) + 1
            by_severity[p.severity] += 1

            if p.severity == "critical":
                critical_issues.append(item)

    return {
        "classifications": classifications,
        "critical_issues": critical_issues[:10],
        "summary": {
            "total": len(classifications),
            "by_category": by_category,
            "by_severity": by_severity
        }
    }


PROBLEM_CLASSIFIER_SYSTEM_PROMPT = """당신은 제품 문제 분류 전문가입니다.

사용 가능한 도구:
- classify_problems: 부정 리뷰를 8개 카테고리로 분류합니다.

문제 카테고리:
1. 피부트러블_자극: 알레르기, 발진, 자극 등
2. 효과미흡: 효과 없음, 기대 미달
3. 품질불량: 제품 변질, 불량
4. 향불만: 향 관련 불만
5. 용기불량: 패키징, 펌프 문제
6. 가격불만: 가성비 불만
7. 용량불만: 양 부족
8. 배송문제: 배송 지연, 파손

심각도 (critical > important > minor)에 따라 우선순위를 결정합니다.
"""


def create_problem_classifier_agent(model: str = "gpt-4o-mini"):
    """Problem Classifier Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[classify_problems],
            state_modifier=SystemMessage(content=PROBLEM_CLASSIFIER_SYSTEM_PROMPT)
        )

        return agent
    except ImportError as e:
        print(f"[ProblemClassifierAgent] LangGraph not available: {e}")
        return None


_problem_classifier_agent = None


def get_problem_classifier_agent():
    """Problem Classifier Agent 싱글톤 반환"""
    global _problem_classifier_agent
    if _problem_classifier_agent is None:
        _problem_classifier_agent = create_problem_classifier_agent()
    return _problem_classifier_agent


# Direct function call (without Agent)
def classify_problems_direct(negative_reviews: List[Dict]) -> Dict[str, Any]:
    """Agent 없이 직접 문제 분류"""
    return classify_problems.invoke({"negative_reviews": negative_reviews})
