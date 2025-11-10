"""
Execute Layer (Layer 2)

실행과 오케스트레이션을 담당하는 레이어
- Agent Execution
- Dependency Resolution
- Result Aggregation
- Error Handling

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from .execute_nodes import (
    execute_layer_node,  # Phase 1: 새 함수명
    aggregator_node,
    error_handler_node
)
from .execute_helpers import (
    AgentExecutor,
    DependencyResolver,
    ExecuteSupervisor
)
from .execute_graph import build_execute_graph

# Backward compatibility (구 함수명도 지원)
executor_node = execute_layer_node

__all__ = [
    # Nodes (Phase 1)
    "execute_layer_node",
    "executor_node",  # Backward compatibility
    "aggregator_node",
    "error_handler_node",

    # Helpers
    "AgentExecutor",
    "DependencyResolver",
    "ExecuteSupervisor",

    # Graph
    "build_execute_graph"
]