"""Insight Generator Tool I/O Schema

인사이트 도출 도구의 입출력 스키마.
Phase 2: Tool I/O 스키마 정의.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from .base import ToolInput, ToolOutput


class InsightInput(ToolInput):
    """인사이트 도출 입력 스키마"""
    analysis_results: Dict[str, Any] = Field(default_factory=dict, description="분석 결과 데이터")
    context: Dict[str, Any] = Field(default_factory=dict, description="추가 컨텍스트")
    insight_depth: str = Field(default="standard", description="인사이트 깊이 (basic, standard, detailed)")
    include_trends: bool = Field(default=False, description="트렌드 데이터 포함 여부")


class InsightItem(BaseModel):
    """인사이트 항목"""
    category: str = Field(description="인사이트 카테고리")
    insight: str = Field(description="인사이트 내용")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, description="근거 데이터")
    priority: int = Field(default=5, ge=1, le=10)


class RecommendationItem(BaseModel):
    """추천 액션 항목"""
    action: str = Field(description="추천 액션")
    rationale: str = Field(default="", description="근거")
    impact: str = Field(default="medium", description="예상 영향도")
    effort: str = Field(default="medium", description="필요 노력")


class InsightOutput(ToolOutput):
    """인사이트 도출 출력 스키마"""
    insights: List[InsightItem] = Field(default_factory=list)
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    summary: str = ""
    key_findings: List[str] = Field(default_factory=list)
