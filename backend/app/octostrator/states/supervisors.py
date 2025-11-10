"""
Supervisor State Definitions

This module contains state definitions for all supervisor components.
Centralized supervisor states for easier management and consistency.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from .base import BaseState


class CognitiveSupervisorState(BaseState):
    """
    State for Cognitive Supervisor (Layer 1)
    Handles planning and intent understanding.
    """
    # Planning
    intent: Optional[str]
    intent_confidence: Optional[float]
    plan: Optional[Dict[str, Any]]
    planning_iterations: int

    # Analysis
    user_context: Dict[str, Any]
    domain_analysis: Dict[str, Any]
    required_agents: List[str]
    required_capabilities: List[str]

    # Reasoning
    reasoning: Optional[str]
    alternative_plans: List[Dict[str, Any]]

    # Validation
    plan_valid: bool
    validation_errors: List[str]


class ExecuteSupervisorState(BaseState):
    """
    State for Execute Supervisor (Layer 3)
    Manages agent execution and coordination.
    """
    # Execution management
    todos: List[Dict[str, Any]]
    active_todos: List[Dict[str, Any]]
    completed_todos: List[Dict[str, Any]]
    failed_todos: List[Dict[str, Any]]

    # Agent tracking
    active_agents: List[str]
    agent_results: Dict[str, Any]
    agent_errors: Dict[str, List[str]]

    # Execution flow
    execution_order: List[str]
    dependency_graph: Dict[str, List[str]]
    parallel_groups: List[List[str]]

    # Progress tracking
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percentage: float

    # Timing
    execution_start: Optional[datetime]
    execution_end: Optional[datetime]
    agent_timings: Dict[str, Dict[str, Any]]


class MainOrchestratorState(BaseState):
    """
    State for Main Orchestrator
    Overall system coordination state.
    """
    # Workflow tracking
    current_layer: int  # 1, 2, or 3
    workflow_state: str  # "planning", "todo_management", "executing", "completed"

    # Layer results
    cognitive_result: Optional[Dict[str, Any]]
    todo_result: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]

    # HITL (Human-in-the-Loop)
    hitl_required: bool
    hitl_status: Optional[str]  # "pending", "approved", "modified", "rejected"
    hitl_feedback: Optional[Dict[str, Any]]
    hitl_timeout: Optional[datetime]

    # Final response
    final_response: Optional[Dict[str, Any]]
    response_generated: bool

    # Performance metrics
    total_processing_time: Optional[float]
    layer_timings: Dict[int, float]


class HumanInTheLoopState(BaseState):
    """
    State for Human-in-the-Loop interactions
    Manages user approval workflows.
    """
    # Approval workflow
    approval_required: bool
    approval_status: Optional[str]  # "pending", "approved", "rejected", "modified"
    approval_timeout: Optional[datetime]

    # User interaction
    prompt_sent: bool
    user_response: Optional[Dict[str, Any]]
    modifications: List[Dict[str, Any]]

    # Auto-approval
    auto_approve_enabled: bool
    auto_approved: bool
    auto_approval_reasons: List[str]

    # History
    interaction_history: List[Dict[str, Any]]
    modification_count: int


class MonitorState(BaseState):
    """
    State for monitoring and debugging
    Tracks system performance and health.
    """
    # System health
    system_status: str
    health_checks: Dict[str, bool]
    resource_usage: Dict[str, float]

    # Performance metrics
    request_count: int
    success_rate: float
    average_response_time: float
    peak_response_time: float

    # Agent metrics
    agent_performance: Dict[str, Dict[str, Any]]
    agent_availability: Dict[str, bool]
    agent_error_rates: Dict[str, float]

    # Alerts
    active_alerts: List[Dict[str, Any]]
    alert_history: List[Dict[str, Any]]

    # Debug info
    debug_mode: bool
    trace_logs: List[Dict[str, Any]]
    checkpoints: List[Dict[str, Any]]