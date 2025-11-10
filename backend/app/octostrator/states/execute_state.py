"""
Execute Layer State Definition

State for Layer 3: Execution and orchestration.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from typing import Dict, List, Optional, Any, TypedDict, Set
from datetime import datetime
from .base import BaseState


class ExecuteState(BaseState):
    """
    State for Execute Layer (Layer 3)

    Handles agent execution, dependency resolution, and result aggregation.
    """
    # Execution Management
    todos: List[Dict[str, Any]]
    execution_order: List[List[str]]  # Groups of parallel executable tasks
    current_execution_group: int
    is_executing: bool

    # Task Status Tracking
    pending_tasks: List[str]
    running_tasks: List[str]
    completed_tasks: List[str]
    failed_tasks: List[str]
    skipped_tasks: List[str]

    # Execution Results
    execution_results: List[Dict[str, Any]]
    agent_results: Dict[str, Any]  # agent_id -> result
    partial_results: Dict[str, Any]

    # Error Handling
    execution_errors: List[Dict[str, Any]]
    error_recovery_attempts: Dict[str, int]  # task_id -> retry_count
    max_retries: int
    error_report: Optional[Dict[str, Any]]

    # Aggregation
    aggregated_data: Optional[Dict[str, Any]]
    aggregation_status: str  # "pending", "processing", "completed"
    insights: List[str]
    summary: Optional[str]

    # Performance Metrics
    execution_start_time: Optional[datetime]
    execution_end_time: Optional[datetime]
    task_timings: Dict[str, Dict[str, Any]]  # task_id -> {start, end, duration}
    total_execution_time: Optional[float]

    # Agent Management
    active_agents: List[str]
    agent_availability: Dict[str, bool]
    agent_workload: Dict[str, int]

    # Dependency Resolution
    dependency_graph: Dict[str, List[str]]
    resolved_dependencies: Set[str]
    blocked_tasks: List[str]

    # Resource Management
    resource_usage: Dict[str, float]
    resource_limits: Dict[str, float]
    resource_allocation: Dict[str, Dict[str, Any]]