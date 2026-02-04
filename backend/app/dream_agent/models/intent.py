"""Intent Models - 의도 분류 관련 모델

Phase 0.5에서 신규 추가된 모델.
Cognitive Layer의 의도 분류 결과를 표현.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum


class IntentDomain(str, Enum):
    """의도 도메인"""
    ANALYSIS = "analysis"
    CONTENT = "content"
    OPERATION = "operation"
    INQUIRY = "inquiry"


class IntentCategory(str, Enum):
    """의도 카테고리"""
    # Analysis
    SENTIMENT = "sentiment"
    KEYWORD = "keyword"
    TREND = "trend"
    COMPETITOR = "competitor"
    # Content
    REPORT = "report"
    VIDEO = "video"
    AD = "ad"
    # Operation
    SALES = "sales"
    INVENTORY = "inventory"
    DASHBOARD = "dashboard"


class Entity(BaseModel):
    """추출된 엔티티"""
    type: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class Intent(BaseModel):
    """의도 분류 결과"""
    domain: IntentDomain
    category: Optional[IntentCategory] = None
    subcategory: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    requires_ml: bool = False
    requires_biz: bool = False
    entities: List[Entity] = Field(default_factory=list)
    summary: str = ""
    raw_input: str = ""
    language: str = "ko"


class IntentClassificationResult(BaseModel):
    """IntentClassifier 결과"""
    intent: Intent
    alternatives: List[Intent] = Field(default_factory=list)
    processing_time_ms: float = 0.0
