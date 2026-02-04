"""Keyword Extraction Tool - 키워드 추출

TF-IDF + TextRank 앙상블 기반 키워드 추출
N-gram (Unigram, Bigram, Trigram) 지원

(기존 ml_execution/agents/keyword_extractor_agent.py에서 이전)
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
def extract_keywords(reviews: List[Dict], top_n: int = 20) -> Dict[str, Any]:
    """
    리뷰에서 핵심 키워드 추출 (TF-IDF + TextRank 앙상블, N-gram 지원)

    Args:
        reviews: preprocess_reviews의 결과 (tokens 포함)
        top_n: 추출할 상위 키워드 수

    Returns:
        키워드 추출 결과:
        {
            "top_keywords": [...],    # 상위 키워드 (혼합)
            "unigrams": [...],        # 단일 단어
            "bigrams": [...],         # 2단어 구문
            "trigrams": [...],        # 3단어 구문
            "stats": {...}            # 통계 정보
        }
    """
    from backend.app.services.ml.extraction import get_ensemble_extractor

    logger.info(f"[Keyword] Extracting keywords from {len(reviews)} reviews")

    extractor = get_ensemble_extractor()

    # 전체 토큰 수집
    all_tokens_list = []
    for review in reviews:
        tokens = review.get("tokens", [])
        if tokens:
            all_tokens_list.append(tokens)

    if not all_tokens_list:
        logger.warning("[Keyword] No tokens found in reviews")
        return {
            "top_keywords": [],
            "unigrams": [],
            "bigrams": [],
            "trigrams": [],
            "unique_count": 0,
            "total_tokens": 0
        }

    # IDF 학습
    extractor.fit(all_tokens_list)

    # 리뷰별 키워드 추출 및 글로벌 점수 집계
    global_keywords: Dict[str, Dict[str, Any]] = {}

    for tokens in all_tokens_list:
        keywords = extractor.extract(tokens, top_n=15)
        for kw in keywords:
            key = kw.keyword
            if key not in global_keywords:
                # Determine ngram type by word count
                word_count = len(key.split())
                if word_count == 1:
                    ngram_type = "unigram"
                elif word_count == 2:
                    ngram_type = "bigram"
                else:
                    ngram_type = "trigram"

                global_keywords[key] = {
                    "score": 0.0,
                    "ngram_type": ngram_type,
                    "count": 0  # Number of documents containing this keyword
                }
            global_keywords[key]["score"] += kw.score
            global_keywords[key]["count"] += 1

    # 상위 키워드 정렬
    sorted_keywords = sorted(
        global_keywords.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    # 결과 분류
    top_keywords = []
    unigrams = []
    bigrams = []
    trigrams = []

    for keyword, data in sorted_keywords[:top_n * 2]:  # 더 많은 후보 확보
        result = {
            "keyword": keyword,
            "score": round(data["score"], 4),
            "ngram_type": data["ngram_type"],
            "count": data["count"]
        }

        # 타입별 분류
        if data["ngram_type"] == "unigram":
            if len(unigrams) < top_n:
                unigrams.append(result)
        elif data["ngram_type"] == "bigram":
            if len(bigrams) < top_n // 2:
                bigrams.append(result)
        elif data["ngram_type"] == "trigram":
            if len(trigrams) < top_n // 3:
                trigrams.append(result)

        # 전체 상위 키워드 (혼합)
        if len(top_keywords) < top_n:
            top_keywords.append(result)

    # 전체 토큰 수 계산
    total_tokens = sum(len(tokens) for tokens in all_tokens_list)

    logger.info(
        f"[Keyword] Extracted {len(top_keywords)} keywords "
        f"({len(unigrams)} unigrams, {len(bigrams)} bigrams, {len(trigrams)} trigrams)"
    )

    return {
        "top_keywords": top_keywords,
        "unigrams": unigrams,
        "bigrams": bigrams,
        "trigrams": trigrams,
        "stats": {
            "unique_keywords": len(global_keywords),
            "total_tokens": total_tokens,
            "reviews_analyzed": len(all_tokens_list),
            "unigram_count": len(unigrams),
            "bigram_count": len(bigrams),
            "trigram_count": len(trigrams)
        }
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("keyword")
class KeywordTool(BaseTool):
    """키워드 추출 도구

    BaseTool 패턴으로 구현된 Keyword Extractor.
    TF-IDF + TextRank 앙상블 방식을 사용합니다.
    """

    name: str = "keyword"
    description: str = "리뷰에서 핵심 키워드 추출 (TF-IDF + TextRank 앙상블)"
    category: str = "analysis"
    version: str = "1.0.0"

    def execute(
        self,
        reviews: List[Dict],
        top_n: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """키워드 추출 실행

        Args:
            reviews: 분석할 리뷰 리스트
            top_n: 추출할 키워드 수

        Returns:
            키워드 추출 결과
        """
        return extract_keywords.invoke({"reviews": reviews, "top_n": top_n})

    async def aexecute(
        self,
        reviews: List[Dict],
        top_n: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 키워드 추출 실행"""
        return await extract_keywords.ainvoke({"reviews": reviews, "top_n": top_n})


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def extract_keywords_direct(reviews: List[Dict], top_n: int = 20) -> Dict[str, Any]:
    """Agent 없이 직접 키워드 추출"""
    logger.info(f"[Keyword] Direct extraction from {len(reviews)} reviews")
    return extract_keywords.invoke({"reviews": reviews, "top_n": top_n})


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

KEYWORD_TOOLS = [
    extract_keywords,
]
