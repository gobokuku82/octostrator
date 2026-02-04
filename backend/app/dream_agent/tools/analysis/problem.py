"""Problem Classification Tool - 부정 리뷰 문제 분류

부정 리뷰를 8개 카테고리, 3단계 심각도로 분류합니다.

(기존 ml_execution/agents/problem_classifier_agent.py에서 이전)
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
def classify_problems(negative_reviews: List[Dict]) -> Dict[str, Any]:
    """
    부정 리뷰 문제 분류 (8개 카테고리, 3단계 심각도)

    카테고리: 피부트러블_자극, 효과미흡, 품질불량, 향불만, 용기불량, 가격불만, 용량불만, 배송문제
    심각도: critical, important, minor

    Args:
        negative_reviews: analyze_sentiment의 negative_reviews

    Returns:
        문제 분류 결과:
        {
            "classifications": [...],    # 모든 분류 결과
            "critical_issues": [...],    # 심각한 문제들
            "summary": {
                "total": int,
                "by_category": {...},
                "by_severity": {...}
            }
        }
    """
    from backend.app.services.ml.classification import get_problem_classifier

    logger.info(f"[Problem] Classifying {len(negative_reviews)} negative reviews")

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

    logger.info(
        f"[Problem] Classified {len(classifications)} issues "
        f"({by_severity['critical']} critical)"
    )

    return {
        "classifications": classifications,
        "critical_issues": critical_issues[:10],
        "summary": {
            "total": len(classifications),
            "by_category": by_category,
            "by_severity": by_severity
        }
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("problem")
class ProblemTool(BaseTool):
    """부정 리뷰 문제 분류 도구

    BaseTool 패턴으로 구현된 Problem Classifier.
    8개 카테고리, 3단계 심각도로 분류합니다.
    """

    name: str = "problem"
    description: str = "부정 리뷰 문제 분류 (8개 카테고리, 3단계 심각도)"
    category: str = "analysis"
    version: str = "1.0.0"

    # 문제 카테고리
    CATEGORIES = [
        "피부트러블_자극",
        "효과미흡",
        "품질불량",
        "향불만",
        "용기불량",
        "가격불만",
        "용량불만",
        "배송문제",
    ]

    # 심각도 레벨
    SEVERITIES = ["critical", "important", "minor"]

    def execute(
        self,
        negative_reviews: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """문제 분류 실행

        Args:
            negative_reviews: 분류할 부정 리뷰 리스트

        Returns:
            문제 분류 결과
        """
        return classify_problems.invoke({"negative_reviews": negative_reviews})

    async def aexecute(
        self,
        negative_reviews: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 문제 분류 실행"""
        return await classify_problems.ainvoke({"negative_reviews": negative_reviews})


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def classify_problems_direct(negative_reviews: List[Dict]) -> Dict[str, Any]:
    """Agent 없이 직접 문제 분류"""
    logger.info(f"[Problem] Direct classification of {len(negative_reviews)} reviews")
    return classify_problems.invoke({"negative_reviews": negative_reviews})


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

PROBLEM_TOOLS = [
    classify_problems,
]
