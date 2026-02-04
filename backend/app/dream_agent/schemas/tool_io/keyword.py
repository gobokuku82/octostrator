"""Keyword Extractor Tool I/O Schema

키워드 추출 도구의 입출력 스키마.
Phase 2: Tool I/O 스키마 정의.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from .base import ToolInput, ToolOutput


class KeywordInput(ToolInput):
    """키워드 추출 입력 스키마"""
    texts: List[str] = Field(default_factory=list, description="키워드를 추출할 텍스트 목록")
    top_k: int = Field(default=10, ge=1, le=100, description="추출할 키워드 개수")
    algorithm: str = Field(default="tfidf", description="추출 알고리즘 (tfidf, textrank, yake)")
    min_freq: int = Field(default=1, ge=1, description="최소 출현 빈도")


class KeywordResult(BaseModel):
    """키워드 결과 항목"""
    keyword: str
    score: float = Field(default=0.0, description="키워드 중요도 점수")
    frequency: int = Field(default=0, description="출현 빈도")
    rank: int = Field(default=0, description="순위")


class KeywordOutput(ToolOutput):
    """키워드 추출 출력 스키마"""
    keywords: List[str] = Field(default_factory=list, description="추출된 키워드 목록")
    keyword_results: List[KeywordResult] = Field(default_factory=list, description="상세 키워드 결과")
    total_words: int = 0
    unique_keywords: int = 0
