"""
Octostrator Supervisor (Main Orchestrator)

Coordinates all supervisor layers into a complete workflow.

This is the main entry point that connects:
- Cognitive Layer: Intent understanding and planning
- Todo Layer: Task breakdown and HITL
- Execute Layer: Agent execution and aggregation
- Response Layer: Output generation and formatting

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from .octostrator_nodes import (
    cognitive_layer_node,
    todo_layer_node,
    execute_layer_node,
    response_layer_node
)
from .octostrator_helpers import (
    OctostratorSupervisor,
    create_octostrator
)
from .octostrator_graph import build_octostrator_graph

__all__ = [
    # Nodes
    "cognitive_layer_node",
    "todo_layer_node",
    "execute_layer_node",
    "response_layer_node",

    # Helpers
    "OctostratorSupervisor",
    "create_octostrator",

    # Graph
    "build_octostrator_graph"
]
