"""
Test conditional edges/routing with subgraph as node
"""
import asyncio
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from typing import TypedDict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestState(TypedDict):
    query: str
    route_decision: str
    subgraph_result: str
    step_count: int


def build_simple_subgraph():
    """Build a simple subgraph with interrupt"""
    from langgraph.graph import StateGraph, START, END

    class SubState(TypedDict):
        query: str
        route_decision: str
        subgraph_result: str
        step_count: int

    def work(state: SubState) -> SubState:
        logger.info("   [SUBGRAPH] work_node")
        state["step_count"] = state.get("step_count", 0) + 1
        return state

    def check_approval(state: SubState) -> SubState:
        logger.info("   [SUBGRAPH] check_approval_node")
        user_decision = interrupt({"message": "Approve?"})
        state["subgraph_result"] = f"approved: {user_decision}"
        return state

    subgraph = StateGraph(SubState)
    subgraph.add_node("work", work)
    subgraph.add_node("check_approval", check_approval)
    subgraph.add_edge(START, "work")
    subgraph.add_edge("work", "check_approval")
    subgraph.add_edge("check_approval", END)

    return subgraph


async def test_routing_with_subgraph():
    """Test conditional routing before/after subgraph node"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 CONDITIONAL ROUTING TEST")
    logger.info("=" * 80)
    logger.info("Testing: Conditional edges work with subgraph as node")
    logger.info("=" * 80)

    # Build main graph with conditional routing
    workflow = StateGraph(TestState)

    # Planning node
    def planning_node(state: TestState) -> TestState:
        logger.info("[MAIN] planning_node")
        # Decision: execute subgraph or skip
        if "skip" in state["query"].lower():
            state["route_decision"] = "skip"
        else:
            state["route_decision"] = "execute"
        logger.info(f"   Decision: {state['route_decision']}")
        return state

    # Skip node
    def skip_node(state: TestState) -> TestState:
        logger.info("[MAIN] skip_node")
        state["subgraph_result"] = "skipped"
        return state

    # Aggregate node
    def aggregate_node(state: TestState) -> TestState:
        logger.info("[MAIN] aggregate_node")
        logger.info(f"   Subgraph result: {state.get('subgraph_result', 'none')}")
        return state

    # Add subgraph as node
    subgraph = build_simple_subgraph()
    compiled_subgraph = subgraph.compile()

    workflow.add_node("planning", planning_node)
    workflow.add_node("subgraph_node", compiled_subgraph)
    workflow.add_node("skip", skip_node)
    workflow.add_node("aggregate", aggregate_node)

    # Conditional routing BEFORE subgraph
    def route_after_planning(state: TestState) -> str:
        decision = state.get("route_decision", "execute")
        logger.info(f"[ROUTING] After planning → {decision}")
        if decision == "skip":
            return "skip"
        return "execute"

    workflow.add_edge(START, "planning")
    workflow.add_conditional_edges(
        "planning",
        route_after_planning,
        {
            "execute": "subgraph_node",
            "skip": "skip"
        }
    )

    # Both paths lead to aggregate
    workflow.add_edge("subgraph_node", "aggregate")
    workflow.add_edge("skip", "aggregate")
    workflow.add_edge("aggregate", END)

    # Compile
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("\n✅ Graph compiled with conditional routing")

    # Test 1: Execute path (with interrupt)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Execute Path (with subgraph)")
    logger.info("=" * 80)

    session1 = "test-execute"
    config1 = {"configurable": {"thread_id": session1}}

    state1 = {
        "query": "execute this",
        "route_decision": "",
        "subgraph_result": "",
        "step_count": 0
    }

    # Initial execution
    interrupted = False
    async for event in app.astream(state1, config1):
        logger.info(f"[EVENT] {list(event.keys())}")
        if "__interrupt__" in event:
            logger.info("   ✅ Interrupted in subgraph")
            interrupted = True
            break

    if not interrupted:
        logger.error("❌ Failed to interrupt")
        return False

    # Resume
    await asyncio.sleep(0.3)
    logger.info("\n[RESUME] Continuing execution...")

    final_result1 = None
    async for event in app.astream(Command(resume={"approved": True}), config1):
        logger.info(f"[EVENT] {list(event.keys())}")
        if "aggregate" in event:
            final_result1 = event["aggregate"]

    # Test 2: Skip path (no subgraph, no interrupt)
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Skip Path (bypass subgraph)")
    logger.info("=" * 80)

    session2 = "test-skip"
    config2 = {"configurable": {"thread_id": session2}}

    state2 = {
        "query": "skip this",
        "route_decision": "",
        "subgraph_result": "",
        "step_count": 0
    }

    final_result2 = None
    async for event in app.astream(state2, config2):
        logger.info(f"[EVENT] {list(event.keys())}")
        if "aggregate" in event:
            final_result2 = event["aggregate"]

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)

    # Test 1 verification
    test1_pass = (
        final_result1 is not None and
        "approved" in final_result1.get("subgraph_result", "")
    )

    logger.info(f"Test 1 (Execute): {'✅ PASS' if test1_pass else '❌ FAIL'}")
    if final_result1:
        logger.info(f"   Subgraph result: {final_result1.get('subgraph_result')}")

    # Test 2 verification
    test2_pass = (
        final_result2 is not None and
        final_result2.get("subgraph_result") == "skipped"
    )

    logger.info(f"Test 2 (Skip): {'✅ PASS' if test2_pass else '❌ FAIL'}")
    if final_result2:
        logger.info(f"   Subgraph result: {final_result2.get('subgraph_result')}")

    logger.info("\n" + "=" * 80)
    if test1_pass and test2_pass:
        logger.info("✅ CONDITIONAL ROUTING TEST PASSED!")
        logger.info("\n   Key Findings:")
        logger.info("   - Conditional edges work with subgraph as node")
        logger.info("   - Can route TO subgraph based on condition")
        logger.info("   - Can bypass subgraph with alternate path")
        logger.info("   - Interrupt works within conditional flow")
        return True
    else:
        logger.error("❌ CONDITIONAL ROUTING TEST FAILED!")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_routing_with_subgraph())
    exit(0 if result else 1)
