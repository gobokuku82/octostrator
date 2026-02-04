"""
Phase 3: Keyword Extractor Agent

TF-IDF + TextRank 앙상블 기반 키워드 추출
N-gram (Unigram, Bigram, Trigram) 지원

v2.0: 다중 단어 키워드 추출 지원
"""

from typing import List, Dict, Any
from langchain_core.tools import tool


@tool
def extract_keywords(reviews: List[Dict], top_n: int = 20) -> Dict[str, Any]:
    """
    리뷰에서 핵심 키워드 추출 (TF-IDF + TextRank 앙상블, N-gram 지원)

    Args:
        reviews: preprocess_reviews의 결과 (tokens 포함)
        top_n: 추출할 상위 키워드 수

    Returns:
        키워드 추출 결과 (단일 단어 + 복합 구문)
    """
    from backend.app.services.ml.extraction import get_ensemble_extractor

    extractor = get_ensemble_extractor()

    # 전체 토큰 수집
    all_tokens_list = []
    for review in reviews:
        tokens = review.get("tokens", [])
        if tokens:
            all_tokens_list.append(tokens)

    if not all_tokens_list:
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


KEYWORD_EXTRACTOR_SYSTEM_PROMPT = """당신은 K-Beauty 키워드 추출 전문가입니다.

사용 가능한 도구:
- extract_keywords: 리뷰에서 핵심 키워드를 추출합니다.

추출 방식:
- TF-IDF: 문서 내 중요 단어 추출 (통계 기반)
- TextRank: 그래프 기반 핵심 단어 추출 (PageRank 응용)
- 앙상블: 두 방식의 결과를 가중 결합

N-gram 지원:
- Unigram: 단일 단어 (예: "보습", "자극")
- Bigram: 2단어 구문 (예: "피부 자극", "수분 공급")
- Trigram: 3단어 구문 (예: "피부 장벽 강화")

상위 키워드는 제품 분석 및 트렌드 파악에 활용됩니다.
"""


def create_keyword_extractor_agent(model: str = "gpt-4o-mini"):
    """Keyword Extractor Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[extract_keywords],
            state_modifier=SystemMessage(content=KEYWORD_EXTRACTOR_SYSTEM_PROMPT)
        )

        return agent
    except ImportError as e:
        print(f"[KeywordExtractorAgent] LangGraph not available: {e}")
        return None


_keyword_extractor_agent = None


def get_keyword_extractor_agent():
    """Keyword Extractor Agent 싱글톤 반환"""
    global _keyword_extractor_agent
    if _keyword_extractor_agent is None:
        _keyword_extractor_agent = create_keyword_extractor_agent()
    return _keyword_extractor_agent


# Direct function call (without Agent)
def extract_keywords_direct(reviews: List[Dict], top_n: int = 20) -> Dict[str, Any]:
    """Agent 없이 직접 키워드 추출"""
    return extract_keywords.invoke({"reviews": reviews, "top_n": top_n})
