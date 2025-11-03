"""
Minimal Document Subgraph for HITL Testing
3 nodes: work → interrupt → finish

Purpose: Test if subgraph resumes correctly after NodeInterrupt
"""

from langgraph.graph import StateGraph, START, END
from langgraph.errors import NodeInterrupt
from typing import TypedDict
import logging

logger = logging.getLogger(__name__)


class SubgraphState(TypedDict):
    # Make compatible with MainState by including all fields
    query: str  # From MainState
    status: str  # From MainState
    subgraph_result: dict  # From MainState
    # Subgraph-specific fields
    message: str
    step_count: int
    user_input: str


def work_node(state: SubgraphState) -> SubgraphState:
    """Step 1: Do some work"""
    logger.info("🔧 [SUBGRAPH] work_node executing")
    state["message"] = "Work done"
    state["step_count"] = state.get("step_count", 0) + 1
    logger.info(f"   Step count: {state['step_count']}")
    return state


def interrupt_node(state: SubgraphState) -> SubgraphState:
    """Step 2: HITL interrupt point using interrupt() function"""
    logger.info("🛑 [SUBGRAPH] interrupt_node executing")
    logger.info("   Current step count: {}".format(state.get("step_count", 0)))

    # Use interrupt() function instead of NodeInterrupt
    # This allows Command(resume=...) to work properly
    from langgraph.types import interrupt

    logger.info("   Calling interrupt() - waiting for user input...")

    # interrupt() will pause execution and return the resume value
    user_input = interrupt({
        "type": "user_confirmation_required",
        "message": "Please confirm to continue",
        "step_count": state.get("step_count", 0)
    })

    logger.info(f"   ✅ User input received: '{user_input}'")

    # Store user_input in state
    state["user_input"] = user_input
    return state


def finish_node(state: SubgraphState) -> SubgraphState:
    """Step 3: Complete workflow"""
    logger.info("✅ [SUBGRAPH] finish_node executing")
    state["message"] = "Completed successfully"
    state["step_count"] = state.get("step_count", 0) + 1
    logger.info(f"   Final step count: {state['step_count']}")

    # CRITICAL CHECK: step_count should be 2
    # work_node (1) → interrupt → finish_node (+1 = 2)
    # If step_count > 2, it means work_node executed again (restart!)
    if state["step_count"] == 2:
        logger.info("   ✅ CORRECT: Subgraph continued from interrupt point")
    else:
        logger.error(f"   ❌ ERROR: Subgraph restarted! Expected step_count=2, got {state['step_count']}")

    return state


def build_document_subgraph() -> StateGraph:
    """Build the minimal document subgraph"""
    logger.info("=" * 60)
    logger.info("[SUBGRAPH] Building subgraph...")
    logger.info("=" * 60)

    subgraph = StateGraph(SubgraphState)

    # Add nodes
    subgraph.add_node("work", work_node)
    subgraph.add_node("interrupt", interrupt_node)
    subgraph.add_node("finish", finish_node)

    # Add edges (linear flow)
    subgraph.add_edge(START, "work")
    subgraph.add_edge("work", "interrupt")
    subgraph.add_edge("interrupt", "finish")
    subgraph.add_edge("finish", END)

    logger.info("✅ [SUBGRAPH] Graph built successfully")
    logger.info("   Nodes: work → interrupt → finish")
    return subgraph
