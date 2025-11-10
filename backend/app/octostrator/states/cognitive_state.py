"""
Cognitive Layer State Definition

State for Layer 1: Planning and decision making.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from .base import BaseState


class CognitiveState(BaseState):
    """
    State for Cognitive Layer (Layer 1)

    Handles planning, intent understanding, and validation.
    """
    # Intent Understanding
    user_query: str
    user_intent: Optional[str]
    intent_confidence: Optional[float]
    intent_keywords: List[str]

    # Planning
    plan: Optional[Dict[str, Any]]
    plan_goal: Optional[str]
    plan_steps: List[Dict[str, Any]]
    plan_version: int
    is_planning: bool

    # Validation
    plan_valid: bool
    validation_result: Optional[Dict[str, Any]]
    validation_errors: List[str]
    validation_warnings: List[str]

    # Context and Memory
    user_context: Dict[str, Any]
    historical_context: Optional[Dict[str, Any]]
    domain_context: Dict[str, Any]

    # Analysis
    required_agents: List[str]
    required_capabilities: List[str]
    estimated_duration: Optional[float]
    complexity_score: Optional[float]

    # Alternative Plans
    alternative_plans: List[Dict[str, Any]]
    selected_plan_index: int
    plan_selection_reason: Optional[str]