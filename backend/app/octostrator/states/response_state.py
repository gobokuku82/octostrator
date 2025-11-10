"""
Response Layer State Definition

State for response generation and formatting.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from typing import Dict, List, Optional, Any, TypedDict, Literal
from datetime import datetime
from .base import BaseState


class ResponseState(BaseState):
    """
    State for Response Layer

    Handles HITL, output routing, and response generation.
    """
    # HITL (Human-in-the-Loop)
    requires_approval: bool
    hitl_approved: bool
    is_waiting_human: bool
    hitl_message: Optional[str]
    hitl_timeout: Optional[datetime]
    auto_approve: bool
    approval_status: Optional[str]  # "pending", "approved", "modified", "rejected"
    user_modifications: List[Dict[str, Any]]

    # Output Format
    output_format: Literal["chat", "graph", "report"]
    selected_format: Optional[str]
    ready_for_generation: bool
    format_preferences: Dict[str, Any]

    # Response Generation
    final_result: Optional[Any]  # Can be str, dict, or other format
    response_type: Optional[str]
    response_metadata: Dict[str, Any]

    # Chat Response
    chat_response: Optional[str]
    chat_tone: Optional[str]  # "professional", "friendly", "casual"
    chat_language: str  # "ko", "en"
    include_emojis: bool

    # Graph Response
    graph_data: Optional[Dict[str, Any]]
    graph_nodes: List[Dict[str, Any]]
    graph_edges: List[Dict[str, Any]]
    graph_layout: Optional[str]  # "horizontal", "vertical", "circular"
    graph_format: Optional[str]  # "d3js", "cytoscape", "mermaid"

    # Report Response
    report_content: Optional[str]
    report_format: Optional[str]  # "markdown", "html", "pdf"
    report_sections: List[Dict[str, Any]]
    report_include_charts: bool
    report_include_tables: bool

    # Response Enhancement
    insights_included: bool
    recommendations_included: bool
    next_steps_included: bool
    confidence_scores: Dict[str, float]

    # Delivery
    delivery_method: Optional[str]  # "inline", "email", "file"
    delivery_status: Optional[str]  # "pending", "sent", "delivered", "failed"
    delivery_timestamp: Optional[datetime]

    # User Feedback
    user_satisfaction: Optional[int]  # 1-5 rating
    user_feedback: Optional[str]
    feedback_processed: bool