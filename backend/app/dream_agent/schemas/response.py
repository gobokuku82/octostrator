"""Response Layer I/O Schema

Response Layer의 입출력 스키마를 정의합니다.
Phase 3: field_validator 기반 검증 추가.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from ..models.results import MLResult, BizResult


class ResponseInput(BaseModel):
    """Response Layer 입력"""
    user_input: str
    language: str = "ko"
    intent_summary: str = ""
    ml_result: Optional[MLResult] = None
    biz_result: Optional[BizResult] = None
    execution_results: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        supported_languages = {'ko', 'en', 'ja', 'zh'}
        if v not in supported_languages:
            raise ValueError(f"Unsupported language: {v}. Supported: {supported_languages}")
        return v


class ResponseOutput(BaseModel):
    """Response Layer 출력"""
    response_text: str
    summary: str = ""
    attachments: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('response_text')
    @classmethod
    def validate_response_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Response text cannot be empty")
        return v.strip()
