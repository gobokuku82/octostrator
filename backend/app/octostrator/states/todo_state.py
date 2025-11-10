"""
TodoAgent State Definition

Individual state definition for TodoAgent.
Manages TODO list and HITL (Human-in-the-Loop) interactions.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from .base import BaseAgentState


class TodoItem(TypedDict):
    """Single TODO item structure"""
    id: str
    title: str
    description: Optional[str]
    agent_id: str
    agent_name: str
    priority: int  # 1-5, 1 being highest
    dependencies: List[str]  # IDs of other todos
    status: str  # "pending", "in_progress", "completed", "failed", "skipped"

    # Execution details
    assigned_to: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration: Optional[float]

    # Results
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    retry_count: int

    # HITL
    requires_approval: bool
    approved: bool
    approved_by: Optional[str]
    approval_timestamp: Optional[datetime]

    # Metadata
    metadata: Dict[str, Any]
    tags: List[str]


class TodoAgentState(BaseAgentState):
    """
    State for TodoAgent (Layer 2)
    Manages TODO list creation, HITL, and task distribution.
    """
    # Plan input
    plan: Optional[Dict[str, Any]]
    plan_version: int

    # TODO Management
    todos: List[TodoItem]
    todo_count: int
    next_todo_id: int

    # Categorized TODOs
    pending_todos: List[TodoItem]
    active_todos: List[TodoItem]
    completed_todos: List[TodoItem]
    failed_todos: List[TodoItem]
    skipped_todos: List[TodoItem]

    # HITL Management
    hitl_enabled: bool
    auto_approve: bool
    approval_pending: bool
    approval_request_sent: bool
    approval_timeout: Optional[datetime]

    # User modifications
    user_modifications: List[Dict[str, Any]]
    modification_history: List[Dict[str, Any]]

    # Execution planning
    execution_groups: List[List[str]]  # Groups of TODO IDs that can run in parallel
    dependency_graph: Dict[str, List[str]]  # TODO ID -> List of dependent TODO IDs
    execution_order: List[str]  # Ordered list of TODO IDs

    # Progress tracking
    total_todos: int
    completed_count: int
    failed_count: int
    skipped_count: int
    progress_percentage: float
    estimated_completion_time: Optional[datetime]

    # Performance metrics
    average_todo_duration: float
    total_execution_time: float
    success_rate: float

    # Agent assignment
    agent_assignments: Dict[str, List[str]]  # agent_id -> List of TODO IDs
    agent_workload: Dict[str, int]  # agent_id -> number of assigned todos

    # Validation
    todos_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]

    # Recovery and rollback
    checkpoint_todos: List[TodoItem]  # Backup for rollback
    recovery_mode: bool
    recovery_point: Optional[str]

    # Additional context
    todo_context: Dict[str, Any]
    global_parameters: Dict[str, Any]
    shared_resources: Dict[str, Any]

    # Notifications
    notifications_enabled: bool
    notification_events: List[Dict[str, Any]]

    # Advanced features
    dynamic_todo_creation: bool  # Allow creating todos during execution
    conditional_todos: Dict[str, Dict[str, Any]]  # TODOs that depend on conditions
    template_todos: Dict[str, TodoItem]  # Reusable TODO templates


class TodoBatch(TypedDict):
    """Batch of TODOs for bulk operations"""
    batch_id: str
    todos: List[TodoItem]
    batch_status: str
    created_at: datetime
    processed_at: Optional[datetime]


class TodoFilter(TypedDict):
    """Filter criteria for TODO queries"""
    status: Optional[List[str]]
    agent_id: Optional[str]
    priority: Optional[int]
    tags: Optional[List[str]]
    date_range: Optional[Dict[str, datetime]]