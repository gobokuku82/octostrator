"""
Response Layer Graph Builder

Builds the workflow graph for response generation.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from langgraph.graph import StateGraph, START, END
from .response_nodes import (
    hitl_handler_node,
    output_router_node,
    chat_generator_node,
    graph_generator_node,
    report_generator_node
)


def build_response_graph(state_class=None):
    """
    Build the response layer workflow graph.

    Flow:
    1. HITL check (if needed)
    2. Route to output format
    3. Generate response
    """
    # Use default dict if no state class provided
    if state_class is None:
        state_class = dict

    # Create graph
    graph = StateGraph(state_class)

    # Add nodes
    graph.add_node("hitl", hitl_handler_node)
    graph.add_node("router", output_router_node)
    graph.add_node("chat_gen", chat_generator_node)
    graph.add_node("graph_gen", graph_generator_node)
    graph.add_node("report_gen", report_generator_node)

    # Add edges
    graph.add_edge(START, "hitl")
    graph.add_edge("hitl", "router")

    # Route based on output format
    graph.add_conditional_edges(
        "router",
        lambda x: x.get("selected_format", "chat"),
        {
            "chat": "chat_gen",
            "graph": "graph_gen",
            "report": "report_gen"
        }
    )

    # All generators lead to END
    graph.add_edge("chat_gen", END)
    graph.add_edge("graph_gen", END)
    graph.add_edge("report_gen", END)

    return graph.compile()