"""Tool I/O Schemas - Tool별 입출력 스키마

각 Tool의 입출력 스키마를 정의합니다.
Phase 2: 도구별 표준화된 입출력 스키마.
"""

from .base import ToolInput, ToolOutput

# Sentiment Analysis
from .sentiment import (
    SentimentInput,
    SentimentOutput,
    SentimentResult,
    SentimentStats,
    AspectSentiment,
)

# Keyword Extraction
from .keyword import (
    KeywordInput,
    KeywordOutput,
    KeywordResult,
)

# Review Collection
from .collector import (
    CollectorInput,
    CollectorOutput,
    CollectorStats,
    ReviewItem,
)

# Insight Generation
from .insight import (
    InsightInput,
    InsightOutput,
    InsightItem,
    RecommendationItem,
)

__all__ = [
    # Base
    "ToolInput",
    "ToolOutput",
    # Sentiment
    "SentimentInput",
    "SentimentOutput",
    "SentimentResult",
    "SentimentStats",
    "AspectSentiment",
    # Keyword
    "KeywordInput",
    "KeywordOutput",
    "KeywordResult",
    # Collector
    "CollectorInput",
    "CollectorOutput",
    "CollectorStats",
    "ReviewItem",
    # Insight
    "InsightInput",
    "InsightOutput",
    "InsightItem",
    "RecommendationItem",
]
