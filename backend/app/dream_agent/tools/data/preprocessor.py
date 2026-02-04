"""Preprocessor Tool - 리뷰 텍스트 전처리

언어 감지, 정규화, 토큰화 기능을 제공합니다.

(기존 ml_execution/agents/preprocessor_agent.py에서 이전)
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
def preprocess_reviews(reviews: List[Dict], use_mock: bool = False) -> Dict[str, Any]:
    """
    리뷰 텍스트 전처리 (언어 감지, 정규화, 토큰화)

    Args:
        reviews: collect_reviews의 결과 리뷰 리스트
        use_mock: True면 data/mock에서 전처리된 결과 로드

    Returns:
        전처리된 리뷰 데이터:
        {
            "reviews": [...],           # 전처리된 리뷰 리스트
            "count": int,               # 전처리된 리뷰 수
            "filtered_count": int,      # 필터링된 리뷰 수
            "language_stats": {...}     # 언어별 통계
        }
    """
    from .mock_loader import is_mock_mode, get_mock_loader

    # Mock 모드: data/mock에서 전처리된 결과 로드
    if use_mock or is_mock_mode():
        logger.info(f"[Preprocessor] Using mock preprocessed data")
        loader = get_mock_loader()
        return loader.get_preprocessed_reviews()

    # 실제 전처리 로직
    try:
        from backend.app.services.ml.preprocessing.pipeline import get_preprocessing_pipeline
        pipeline = get_preprocessing_pipeline()
    except ImportError:
        logger.warning("[Preprocessor] Pipeline not available, using simple preprocessing")
        return _simple_preprocess(reviews)

    logger.info(f"[Preprocessor] Starting preprocessing for {len(reviews)} reviews")

    preprocessed = []
    lang_stats = {}

    for review in reviews:
        text = review.get("text", "")
        if not text:
            continue

        result = pipeline.process(text)

        # 품질 필터링 (0.3 이상만)
        if result.quality_score >= 0.3:
            preprocessed.append({
                **review,
                "cleaned_text": result.cleaned_text,
                "language": result.language,
                "tokens": result.tokens,
                "hashtags": result.hashtags + review.get("hashtags", []),
                "quality_score": result.quality_score
            })

            lang = result.language
            lang_stats[lang] = lang_stats.get(lang, 0) + 1

    logger.info(
        f"[Preprocessor] Complete: {len(preprocessed)} processed, "
        f"{len(reviews) - len(preprocessed)} filtered"
    )

    return {
        "reviews": preprocessed,
        "count": len(preprocessed),
        "filtered_count": len(reviews) - len(preprocessed),
        "language_stats": lang_stats
    }


def _simple_preprocess(reviews: List[Dict]) -> Dict[str, Any]:
    """간단한 전처리 (파이프라인 없이)"""
    import re

    preprocessed = []
    lang_stats = {}

    for review in reviews:
        text = review.get("text", "")
        if not text:
            continue

        # 간단한 정규화
        cleaned = re.sub(r'\s+', ' ', text).strip()
        tokens = cleaned.split()[:20]

        # 언어 감지 (간단한 휴리스틱)
        korean_chars = len(re.findall(r'[가-힣]', text))
        lang = "ko" if korean_chars > len(text) * 0.3 else "en"

        preprocessed.append({
            **review,
            "cleaned_text": cleaned,
            "language": lang,
            "tokens": tokens,
            "hashtags": review.get("hashtags", []),
            "quality_score": 0.7,
        })

        lang_stats[lang] = lang_stats.get(lang, 0) + 1

    return {
        "reviews": preprocessed,
        "count": len(preprocessed),
        "filtered_count": len(reviews) - len(preprocessed),
        "language_stats": lang_stats,
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("preprocessor")
class PreprocessorTool(BaseTool):
    """리뷰 텍스트 전처리 도구

    BaseTool 패턴으로 구현된 Preprocessor.
    언어 감지, 정규화, 토큰화 기능을 제공합니다.
    """

    name: str = "preprocessor"
    description: str = "리뷰 텍스트를 전처리합니다 (언어 감지, 정규화, 토큰화)"
    category: str = "data"
    version: str = "1.0.0"

    def execute(
        self,
        reviews: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """전처리 실행

        Args:
            reviews: 전처리할 리뷰 리스트

        Returns:
            전처리된 리뷰 데이터
        """
        return preprocess_reviews.invoke({"reviews": reviews})

    async def aexecute(
        self,
        reviews: List[Dict],
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 전처리 실행"""
        return await preprocess_reviews.ainvoke({"reviews": reviews})


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def preprocess_reviews_direct(reviews: List[Dict]) -> Dict[str, Any]:
    """Agent 없이 직접 전처리"""
    logger.info(f"[Preprocessor] Direct preprocessing: {len(reviews)} reviews")
    return preprocess_reviews.invoke({"reviews": reviews})


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

PREPROCESSOR_TOOLS = [
    preprocess_reviews,
]
