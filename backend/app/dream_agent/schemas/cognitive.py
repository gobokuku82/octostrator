"""Cognitive Layer I/O Schema

Cognitive Layer의 입출력 스키마를 정의합니다.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from ..models.intent import Intent, Entity


class CognitiveInput(BaseModel):
    """Cognitive Layer 입력"""
    user_input: str
    language: str = "ko"
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('user_input')
    @classmethod
    def validate_user_input(cls, v):
        if not v or not v.strip():
            raise ValueError("User input cannot be empty")
        return v.strip()


class CognitiveOutput(BaseModel):
    """Cognitive Layer 출력"""
    intent: Intent
    entities: List[Entity] = Field(default_factory=list)
    requires_clarification: bool = False
    clarification_message: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    @field_validator('intent')
    @classmethod
    def validate_intent(cls, v):
        if v.confidence < 0.3:
            raise ValueError("Intent confidence too low")
        return v
