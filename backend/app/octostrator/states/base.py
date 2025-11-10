"""
Base State Classes for the 3-Layer Architecture

This module contains the base state classes that all other states inherit from.
Provides common functionality and fields used across the system.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from pydantic import BaseModel, Field


class BaseState(TypedDict, total=False):
    """
    Base state for all components in the system.
    TypedDict allows for LangGraph compatibility.
    """
    # Session management
    session_id: str
    thread_id: Optional[str]
    user_id: Optional[str]

    # Message tracking
    messages: List[Dict[str, Any]]
    user_message: str

    # Execution context
    context: Dict[str, Any]
    metadata: Dict[str, Any]

    # Timing
    created_at: datetime
    updated_at: datetime

    # Error handling
    error: Optional[str]
    errors: List[str]

    # Status tracking
    status: str  # "pending", "processing", "completed", "failed"


class BaseAgentState(BaseState):
    """
    Base state specifically for agents.
    All agent states should inherit from this.
    """
    # Agent specific fields
    agent_id: Optional[str]
    agent_name: Optional[str]

    # Task management
    task: Optional[Dict[str, Any]]
    task_id: Optional[str]
    task_status: Optional[str]

    # Results
    result: Optional[Dict[str, Any]]
    results: List[Dict[str, Any]]

    # Capabilities
    capabilities: List[str]
    required_capabilities: List[str]

    # Execution tracking
    execution_history: List[Dict[str, Any]]
    retry_count: int
    max_retries: int

    # Dependencies
    dependencies: List[str]
    depends_on: List[str]


class BaseModel(BaseModel):
    """
    Pydantic base model for validation when needed.
    Use this for request/response validation, not for LangGraph states.
    """
    class Config:
        # Allow extra fields
        extra = "allow"
        # Use enum values
        use_enum_values = True
        # Allow mutation
        allow_mutation = True
        # JSON encoders
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# Common type definitions
TaskDict = Dict[str, Any]
ResultDict = Dict[str, Any]
ContextDict = Dict[str, Any]
MessageDict = Dict[str, Any]