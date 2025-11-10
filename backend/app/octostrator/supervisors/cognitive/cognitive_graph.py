"""
Cognitive Layer Graph Builder

Builds the workflow graph for cognitive processing.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from langgraph.graph import StateGraph, START, END
from .cognitive_nodes import (
    intent_understanding_node,
    planning_node,
    validator_node
)


def build_cognitive_graph(state_class=None):
    """
    Build the cognitive layer workflow graph.

    Flow:
    1. Intent Understanding
    2. Planning
    3. Validation
    """
    # Use default dict if no state class provided
    if state_class is None:
        state_class = dict

    # Create graph
    graph = StateGraph(state_class)

    # Add nodes
    graph.add_node("intent", intent_understanding_node)
    graph.add_node("planning", planning_node)
    graph.add_node("validator", validator_node)

    # Add edges
    graph.add_edge(START, "intent")
    graph.add_edge("intent", "planning")
    graph.add_edge("planning", "validator")
    graph.add_edge("validator", END)

    # TODO: Add conditional edges for validation failure
    # graph.add_conditional_edges(
    #     "validator",
    #     lambda x: "planning" if not x.get("plan_valid") else END
    # )

    return graph.compile()