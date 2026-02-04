"""Review Collector Tool I/O Schema

리뷰 수집 도구의 입출력 스키마.
Phase 2: Tool I/O 스키마 정의.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import ToolInput, ToolOutput


class CollectorInput(ToolInput):
    """리뷰 수집 입력 스키마"""
    keyword: str = Field(description="검색 키워드 (브랜드명 또는 제품명)")
    platform: str = Field(default="all", description="수집 플랫폼 (naver, coupang, oliveyoung, all)")
    limit: int = Field(default=100, ge=1, le=1000, description="수집할 리뷰 개수")
    start_date: Optional[str] = Field(default=None, description="수집 시작일 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="수집 종료일 (YYYY-MM-DD)")


class ReviewItem(BaseModel):
    """수집된 리뷰 항목"""
    text: str
    rating: Optional[float] = None
    date: Optional[str] = None
    platform: Optional[str] = None
    product_name: Optional[str] = None
    author: Optional[str] = None
    helpful_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CollectorStats(BaseModel):
    """수집 통계"""
    total_collected: int = 0
    by_platform: Dict[str, int] = Field(default_factory=dict)
    avg_rating: Optional[float] = None
    date_range: Optional[Dict[str, str]] = None


class CollectorOutput(ToolOutput):
    """리뷰 수집 출력 스키마"""
    reviews: List[ReviewItem] = Field(default_factory=list)
    stats: CollectorStats = Field(default_factory=CollectorStats)
    keyword: str = ""
    platform: str = ""
