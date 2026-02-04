"""Analysis Tools - 분석 도구

감성 분석, 키워드 추출, 해시태그 분석 등 ML 기반 분석 도구를 제공합니다.

모듈:
- sentiment.py: 감성 분석, ABSA
- keyword.py: 키워드 추출, 바이그램
- hashtag.py: 해시태그 분석
- problem.py: 문제점 분류
- competitor.py: 경쟁사 분석
"""

# Sentiment Tools
from .sentiment import (
    # @tool 함수
    analyze_sentiment,
    SENTIMENT_TOOLS,
    # BaseTool 클래스
    SentimentTool,
    # Direct 함수
    analyze_sentiment_direct,
)

# Keyword Tools
from .keyword import (
    # @tool 함수
    extract_keywords,
    KEYWORD_TOOLS,
    # BaseTool 클래스
    KeywordTool,
    # Direct 함수
    extract_keywords_direct,
)

# Hashtag Tools
from .hashtag import (
    # @tool 함수
    extract_hashtags,
    compare_hashtags,
    get_trending_hashtags,
    analyze_hashtag_engagement,
    HASHTAG_TOOLS,
    # BaseTool 클래스
    HashtagTool,
    # Direct 함수
    extract_hashtags_direct,
    get_trending_direct,
    analyze_engagement_direct,
)

# Problem Tools
from .problem import (
    # @tool 함수
    classify_problems,
    PROBLEM_TOOLS,
    # BaseTool 클래스
    ProblemTool,
    # Direct 함수
    classify_problems_direct,
)

# Competitor Tools
from .competitor import (
    # @tool 함수
    compare_brands,
    analyze_competitive_position,
    generate_competitive_report,
    get_brand_strengths_weaknesses,
    COMPETITOR_TOOLS,
    # BaseTool 클래스
    CompetitorTool,
    # Direct 함수
    compare_brands_direct,
    analyze_position_direct,
    get_strengths_weaknesses_direct,
)

__all__ = [
    # Sentiment
    "analyze_sentiment",
    "SENTIMENT_TOOLS",
    "SentimentTool",
    "analyze_sentiment_direct",
    # Keyword
    "extract_keywords",
    "KEYWORD_TOOLS",
    "KeywordTool",
    "extract_keywords_direct",
    # Hashtag
    "extract_hashtags",
    "compare_hashtags",
    "get_trending_hashtags",
    "analyze_hashtag_engagement",
    "HASHTAG_TOOLS",
    "HashtagTool",
    "extract_hashtags_direct",
    "get_trending_direct",
    "analyze_engagement_direct",
    # Problem
    "classify_problems",
    "PROBLEM_TOOLS",
    "ProblemTool",
    "classify_problems_direct",
    # Competitor
    "compare_brands",
    "analyze_competitive_position",
    "generate_competitive_report",
    "get_brand_strengths_weaknesses",
    "COMPETITOR_TOOLS",
    "CompetitorTool",
    "compare_brands_direct",
    "analyze_position_direct",
    "get_strengths_weaknesses_direct",
]
