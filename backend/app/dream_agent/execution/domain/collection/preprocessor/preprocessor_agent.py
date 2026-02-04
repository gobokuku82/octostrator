"""
Phase 2: Preprocessor Agent

리뷰 텍스트 전처리 - 언어 감지, 정규화, 토큰화
"""

from typing import List, Dict, Any
from langchain_core.tools import tool


@tool
def preprocess_reviews(reviews: List[Dict]) -> Dict[str, Any]:
    """
    리뷰 텍스트 전처리 (언어 감지, 정규화, 토큰화)

    Args:
        reviews: collect_reviews의 결과 리뷰 리스트

    Returns:
        전처리된 리뷰 데이터
    """
    from backend.app.services.ml.preprocessing.pipeline import get_preprocessing_pipeline

    pipeline = get_preprocessing_pipeline()
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

    return {
        "reviews": preprocessed,
        "count": len(preprocessed),
        "filtered_count": len(reviews) - len(preprocessed),
        "language_stats": lang_stats
    }


PREPROCESSOR_SYSTEM_PROMPT = """당신은 텍스트 전처리 전문가입니다.

사용 가능한 도구:
- preprocess_reviews: 리뷰 텍스트를 전처리합니다.

전처리 과정:
1. 언어 감지 (한국어/영어)
2. 텍스트 정규화 (URL, 이모지, 특수문자 처리)
3. 토큰화 (형태소 분석)
4. 품질 점수 계산 및 필터링

품질 점수 0.3 미만의 저품질 리뷰는 자동으로 필터링됩니다.
"""


def create_preprocessor_agent(model: str = "gpt-4o-mini"):
    """Preprocessor Agent 생성"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage
        from langgraph.prebuilt import create_react_agent

        llm = ChatOpenAI(model=model, temperature=0)

        agent = create_react_agent(
            model=llm,
            tools=[preprocess_reviews],
            state_modifier=SystemMessage(content=PREPROCESSOR_SYSTEM_PROMPT)
        )

        return agent
    except ImportError as e:
        print(f"[PreprocessorAgent] LangGraph not available: {e}")
        return None


_preprocessor_agent = None


def get_preprocessor_agent():
    """Preprocessor Agent 싱글톤 반환"""
    global _preprocessor_agent
    if _preprocessor_agent is None:
        _preprocessor_agent = create_preprocessor_agent()
    return _preprocessor_agent


# Direct function call (without Agent)
def preprocess_reviews_direct(reviews: List[Dict]) -> Dict[str, Any]:
    """Agent 없이 직접 전처리"""
    return preprocess_reviews.invoke({"reviews": reviews})
