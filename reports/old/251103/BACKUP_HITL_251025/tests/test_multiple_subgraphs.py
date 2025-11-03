"""
Test multiple subgraphs (simulating document/search/analysis teams)
"""
import asyncio
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from typing import TypedDict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiTeamState(TypedDict):
    query: str
    teams_to_execute: List[str]
    document_result: str
    search_result: str
    analysis_result: str
    final_result: str


def build_document_subgraph():
    """Document team subgraph with interrupt"""
    class DocState(TypedDict):
        query: str
        teams_to_execute: List[str]
        document_result: str
        search_result: str
        analysis_result: str
        final_result: str

    def doc_work(state: DocState) -> DocState:
        logger.info("   [DOC TEAM] Processing...")
        return state

    def doc_review(state: DocState) -> DocState:
        logger.info("   [DOC TEAM] Requesting review...")
        approval = interrupt({"team": "document", "message": "Review document?"})
        state["document_result"] = f"doc_approved: {approval.get('approved', False)}"
        return state

    subgraph = StateGraph(DocState)
    subgraph.add_node("work", doc_work)
    subgraph.add_node("review", doc_review)
    subgraph.add_edge(START, "work")
    subgraph.add_edge("work", "review")
    subgraph.add_edge("review", END)

    return subgraph


def build_search_subgraph():
    """Search team subgraph (no interrupt)"""
    class SearchState(TypedDict):
        query: str
        teams_to_execute: List[str]
        document_result: str
        search_result: str
        analysis_result: str
        final_result: str

    def search_work(state: SearchState) -> SearchState:
        logger.info("   [SEARCH TEAM] Searching...")
        state["search_result"] = "search_completed"
        return state

    subgraph = StateGraph(SearchState)
    subgraph.add_node("work", search_work)
    subgraph.add_edge(START, "work")
    subgraph.add_edge("work", END)

    return subgraph


def build_analysis_subgraph():
    """Analysis team subgraph (no interrupt)"""
    class AnalysisState(TypedDict):
        query: str
        teams_to_execute: List[str]
        document_result: str
        search_result: str
        analysis_result: str
        final_result: str

    def analysis_work(state: AnalysisState) -> AnalysisState:
        logger.info("   [ANALYSIS TEAM] Analyzing...")
        state["analysis_result"] = "analysis_completed"
        return state

    subgraph = StateGraph(AnalysisState)
    subgraph.add_node("work", analysis_work)
    subgraph.add_edge(START, "work")
    subgraph.add_edge("work", END)

    return subgraph


async def test_multiple_subgraphs():
    """Test multiple subgraphs in same workflow"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 MULTIPLE SUBGRAPHS TEST")
    logger.info("=" * 80)
    logger.info("Testing: Multiple subgraphs (document/search/analysis)")
    logger.info("Purpose: Verify production architecture with 3 teams")
    logger.info("=" * 80)

    # Build main workflow
    workflow = StateGraph(MultiTeamState)

    def planning(state: MultiTeamState) -> MultiTeamState:
        logger.info("[MAIN] Planning which teams to execute...")
        # Execute all 3 teams
        state["teams_to_execute"] = ["document", "search", "analysis"]
        logger.info(f"   Teams: {state['teams_to_execute']}")
        return state

    def aggregate(state: MultiTeamState) -> MultiTeamState:
        logger.info("[MAIN] Aggregating results...")
        logger.info(f"   Document: {state.get('document_result', 'none')}")
        logger.info(f"   Search: {state.get('search_result', 'none')}")
        logger.info(f"   Analysis: {state.get('analysis_result', 'none')}")
        state["final_result"] = "aggregated"
        return state

    # Compile all subgraphs
    document_sg = build_document_subgraph().compile()
    search_sg = build_search_subgraph().compile()
    analysis_sg = build_analysis_subgraph().compile()

    # Add nodes
    workflow.add_node("planning", planning)
    workflow.add_node("document_team", document_sg)
    workflow.add_node("search_team", search_sg)
    workflow.add_node("analysis_team", analysis_sg)
    workflow.add_node("aggregate", aggregate)

    # Linear flow: planning → document → search → analysis → aggregate
    workflow.add_edge(START, "planning")
    workflow.add_edge("planning", "document_team")
    workflow.add_edge("document_team", "search_team")
    workflow.add_edge("search_team", "analysis_team")
    workflow.add_edge("analysis_team", "aggregate")
    workflow.add_edge("aggregate", END)

    # Compile
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("\n✅ Workflow compiled with 3 subgraphs")

    # Execute
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTION: All 3 Teams")
    logger.info("=" * 80)

    session_id = "test-multi-teams"
    config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "query": "Test query",
        "teams_to_execute": [],
        "document_result": "",
        "search_result": "",
        "analysis_result": "",
        "final_result": ""
    }

    # Phase 1: Execute until document team interrupts
    logger.info("\n[PHASE 1] Initial execution...")
    interrupted = False
    async for event in app.astream(initial_state, config):
        logger.info(f"[EVENT] {list(event.keys())}")
        if "__interrupt__" in event:
            logger.info("   ✅ Interrupted at document_team")
            interrupted = True
            break

    if not interrupted:
        logger.error("❌ Failed to interrupt")
        return False

    # Phase 2: Resume
    await asyncio.sleep(0.3)
    logger.info("\n[PHASE 2] Resume after document approval...")

    final_state = None
    async for event in app.astream(
        Command(resume={"approved": True}),
        config
    ):
        logger.info(f"[EVENT] {list(event.keys())}")
        if "aggregate" in event:
            final_state = event["aggregate"]

    # Verification
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)

    if not final_state:
        logger.error("❌ No final state")
        return False

    # Check all teams executed
    doc_ok = "doc_approved" in final_state.get("document_result", "")
    search_ok = final_state.get("search_result") == "search_completed"
    analysis_ok = final_state.get("analysis_result") == "analysis_completed"
    aggregated_ok = final_state.get("final_result") == "aggregated"

    logger.info(f"Document team: {'✅' if doc_ok else '❌'} - {final_state.get('document_result')}")
    logger.info(f"Search team: {'✅' if search_ok else '❌'} - {final_state.get('search_result')}")
    logger.info(f"Analysis team: {'✅' if analysis_ok else '❌'} - {final_state.get('analysis_result')}")
    logger.info(f"Aggregation: {'✅' if aggregated_ok else '❌'} - {final_state.get('final_result')}")

    all_ok = doc_ok and search_ok and analysis_ok and aggregated_ok

    logger.info("\n" + "=" * 80)
    if all_ok:
        logger.info("✅ MULTIPLE SUBGRAPHS TEST PASSED!")
        logger.info("\n   Key Findings:")
        logger.info("   - Multiple subgraphs work in sequence")
        logger.info("   - Each subgraph maintains its own state")
        logger.info("   - Interrupt in one subgraph doesn't affect others")
        logger.info("   - Resume continues from interrupted subgraph")
        logger.info("   - Remaining subgraphs execute after resume")
        return True
    else:
        logger.error("❌ MULTIPLE SUBGRAPHS TEST FAILED!")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_multiple_subgraphs())
    exit(0 if result else 1)
