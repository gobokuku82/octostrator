"""Sentiment Analysis Tool I/O Schema

감성 분석 도구의 입출력 스키마.
Phase 2: Tool I/O 스키마 정의.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import ToolInput, ToolOutput


class SentimentInput(ToolInput):
    """감성 분석 입력 스키마"""
    texts: List[str] = Field(default_factory=list, description="분석할 텍스트 목록")
    reviews: List[Dict[str, Any]] = Field(default_factory=list, description="분석할 리뷰 데이터")
    analysis_mode: str = Field(default="standard", description="분석 모드 (standard, absa)")
    language: str = Field(default="ko", description="텍스트 언어")


class AspectSentiment(BaseModel):
    """Aspect별 감성 결과"""
    aspect: str = Field(description="분석된 속성 (예: 보습, 향, 가격)")
    sentiment: str = Field(description="감성 (positive, negative, neutral)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    keywords: List[str] = Field(default_factory=list)


class SentimentResult(BaseModel):
    """개별 텍스트 감성 분석 결과"""
    text: str
    sentiment: str = Field(description="전체 감성 (positive, negative, neutral)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_negative: bool = False
    aspects: List[AspectSentiment] = Field(default_factory=list)


class SentimentStats(BaseModel):
    """감성 분석 통계"""
    total: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    positive_rate: float = 0.0
    negative_rate: float = 0.0
    aspect_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class SentimentOutput(ToolOutput):
    """감성 분석 출력 스키마"""
    results: List[SentimentResult] = Field(default_factory=list)
    positive_reviews: List[Dict[str, Any]] = Field(default_factory=list)
    negative_reviews: List[Dict[str, Any]] = Field(default_factory=list)
    stats: SentimentStats = Field(default_factory=SentimentStats)
