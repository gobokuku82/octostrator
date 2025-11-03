"""
Minimal Supervisor for HITL Testing
3 nodes: start → execute_subgraph → end

Purpose: Test if we can resume subgraph from parent graph context
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MainState(TypedDict):
    # Shared fields with SubgraphState
    query: str
    status: str
    subgraph_result: Dict[str, Any]
    # Subgraph fields (must be included for state sharing)
    message: str
    step_count: int
    user_input: str


class TestSupervisor:
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.app = None
        self._subgraph_apps = {}  # NEW: Store subgraph references for resume

    def build_graph(self):
        """Build minimal supervisor graph using OFFICIAL PATTERN"""
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] Building main graph with OFFICIAL PATTERN...")
        logger.info("=" * 60)

        workflow = StateGraph(MainState)

        # Add nodes
        workflow.add_node("start", self.start_node)

        # OFFICIAL PATTERN: Add compiled subgraph DIRECTLY as node
        from app.hitl_test_agent.test_subgraph import build_document_subgraph
        logger.info("[SUPERVISOR] Building document subgraph...")
        subgraph = build_document_subgraph()

        # Compile subgraph WITHOUT checkpointer (parent will provide)
        logger.info("[SUPERVISOR] Compiling subgraph WITHOUT checkpointer...")
        compiled_subgraph = subgraph.compile()
        logger.info("✅ [SUPERVISOR] Subgraph compiled (checkpointer will be auto-propagated)")

        # Add compiled subgraph DIRECTLY as node (NO WRAPPER!)
        # This allows LangGraph to handle interrupts properly
        workflow.add_node("document_subgraph", compiled_subgraph)
        logger.info("✅ [SUPERVISOR] Subgraph added DIRECTLY as node (OFFICIAL PATTERN)")

        workflow.add_node("end", self.end_node)

        # Add edges
        workflow.add_edge(START, "start")
        workflow.add_edge("start", "document_subgraph")  # Direct to subgraph node
        workflow.add_edge("document_subgraph", "end")
        workflow.add_edge("end", END)

        # Compile with checkpointer (will auto-propagate to subgraph)
        self.app = workflow.compile(checkpointer=self.checkpointer)
        logger.info("✅ [SUPERVISOR] Main graph compiled with checkpointer")
        logger.info("   Checkpointer will be auto-propagated to subgraph")

        return self.app

    def start_node(self, state: MainState) -> MainState:
        """Initialize workflow"""
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] start_node executing")
        logger.info(f"   Query: {state['query']}")
        logger.info("=" * 60)
        state["status"] = "started"
        return state

    async def execute_subgraph_node_OLD_PATTERN_NOT_USED(self, state: MainState) -> MainState:
        """
        Execute document subgraph

        This is the CRITICAL test point:
        - Does subgraph interrupt properly?
        - Can we resume it later?
        """
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] execute_subgraph_node executing")
        logger.info("=" * 60)

        # Import subgraph builder
        from app.hitl_test_agent.test_subgraph import build_document_subgraph

        # Build subgraph
        logger.info("[SUPERVISOR] Building document subgraph...")
        subgraph = build_document_subgraph()

        # Compile with supervisor's checkpointer (shared checkpoint)
        subgraph_app = subgraph.compile(checkpointer=self.checkpointer)
        logger.info("✅ [SUPERVISOR] Subgraph compiled with shared checkpointer")

        # Store reference for later resume (CRITICAL for Test 4!)
        session_id = "test-session-123"
        self._subgraph_apps[session_id] = subgraph_app
        logger.info(f"✅ [SUPERVISOR] Subgraph app stored for session: {session_id}")

        # Config: session_id = thread_id (same value)
        config = {"configurable": {"thread_id": session_id}}
        logger.info(f"📌 [SUPERVISOR] thread_id: {session_id}")

        # Execute subgraph
        logger.info("🚀 [SUPERVISOR] Executing subgraph...")

        subgraph_state = {
            "message": "",
            "step_count": 0,
            "user_input": ""
        }

        try:
            async for event in subgraph_app.astream(subgraph_state, config):
                logger.info(f"   [SUPERVISOR] Subgraph event: {list(event.keys())}")

                # Check for __interrupt__ event
                if "__interrupt__" in event:
                    logger.info("   ⚠️ [SUPERVISOR] Interrupt detected in subgraph!")

                    # Extract interrupt object
                    interrupt_value = event["__interrupt__"]
                    if isinstance(interrupt_value, tuple):
                        interrupt_obj = interrupt_value[0]
                    else:
                        interrupt_obj = interrupt_value

                    # Get interrupt data
                    interrupt_data = interrupt_obj.value if hasattr(interrupt_obj, 'value') else {}

                    logger.info(f"   [SUPERVISOR] Interrupt type: {interrupt_data.get('type')}")
                    logger.info(f"   [SUPERVISOR] Interrupt message: {interrupt_data.get('message')}")

                    # Return interrupted status to parent
                    state["status"] = "interrupted"
                    state["subgraph_result"] = {
                        "status": "interrupted",
                        "interrupt_data": interrupt_data
                    }

                    logger.info("   [SUPERVISOR] Returning interrupted status to main graph")
                    return state

            # If we reach here, subgraph completed without interrupt
            logger.info("   ✅ [SUPERVISOR] Subgraph completed normally (no interrupt)")
            state["status"] = "completed"
            state["subgraph_result"] = {"status": "completed"}
            return state

        except Exception as e:
            logger.error(f"   ❌ [SUPERVISOR] Subgraph execution error: {e}", exc_info=True)
            state["status"] = "failed"
            state["subgraph_result"] = {"status": "failed", "error": str(e)}
            return state

    def end_node(self, state: MainState) -> MainState:
        """Finalize workflow"""
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] end_node executing")
        logger.info(f"   Final status: {state['status']}")
        logger.info(f"   Subgraph result: {state.get('subgraph_result', {})}")
        logger.info("=" * 60)
        return state

    async def resume_workflow(self, session_id: str, user_input: str = "confirmed"):
        """
        Resume workflow using OFFICIAL PATTERN

        With official pattern:
        - Subgraph is added as direct node
        - Resume MAIN graph (not subgraph directly)
        - LangGraph handles subgraph resume automatically
        """
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] resume_workflow called (OFFICIAL PATTERN)")
        logger.info(f"   Session ID: {session_id}")
        logger.info(f"   User input: {user_input}")
        logger.info("=" * 60)

        # Config: session_id = thread_id
        config = {"configurable": {"thread_id": session_id}}

        # CHECKPOINT VERIFICATION
        logger.info("🔍 [SUPERVISOR] Checking checkpoints...")
        try:
            # Check main graph state with subgraphs=True
            main_snapshot = self.app.get_state(config, subgraphs=True)
            logger.info(f"   ✅ Main graph checkpoint:")
            logger.info(f"      Next node: {main_snapshot.next}")
            logger.info(f"      Values: {list(main_snapshot.values.keys()) if main_snapshot.values else 'EMPTY'}")

            # Check if subgraph tasks exist
            if hasattr(main_snapshot, 'tasks') and main_snapshot.tasks:
                logger.info(f"   ✅ Subgraph tasks found: {len(main_snapshot.tasks)}")
                for i, task in enumerate(main_snapshot.tasks):
                    logger.info(f"      Task {i}: {task}")
                    if hasattr(task, 'state'):
                        logger.info(f"         State: {task.state}")
            else:
                logger.info(f"   ⚠️ No subgraph tasks found")
        except Exception as e:
            logger.error(f"   ❌ Failed to get checkpoint: {e}")

        # OFFICIAL PATTERN: Resume MAIN graph with Command
        from langgraph.types import Command

        logger.info("🔄 [SUPERVISOR] Resuming MAIN graph with Command(resume=...)...")
        logger.info("   Pattern: main_graph.astream(Command(resume=...), config)")
        logger.info("   LangGraph will automatically resume subgraph")

        result = None
        step_count_at_finish = None

        try:
            async for event in self.app.astream(
                Command(resume={"user_input": user_input}),
                config
            ):
                logger.info(f"   [SUPERVISOR] Resume event: {list(event.keys())}")
                result = event

                # Check if we got to finish_node (in subgraph)
                if "document_subgraph" in event:
                    subgraph_result = event["document_subgraph"]
                    logger.info(f"   [SUPERVISOR] Subgraph completed!")
                    logger.info(f"   Subgraph result keys: {list(subgraph_result.keys())}")
                    logger.info(f"   Subgraph result: {subgraph_result}")
                    # Subgraph returns full state, get step_count from it
                    step_count_at_finish = subgraph_result.get("step_count", 0)
                    logger.info(f"   Step count from subgraph: {step_count_at_finish}")

                # Check end node
                if "end" in event:
                    logger.info(f"   [SUPERVISOR] End node reached!")

            # Analysis
            logger.info("\n" + "=" * 60)
            logger.info("[SUPERVISOR] RESUME RESULT ANALYSIS")
            logger.info("=" * 60)

            if step_count_at_finish == 2:
                logger.info("✅ SUCCESS: Subgraph continued from interrupt_node")
                logger.info("   Step count = 2 (work=1, finish=1)")
                logger.info("   interrupt_node did NOT re-execute")
                logger.info("   → OFFICIAL PATTERN WORKS!")
                return {"status": "success", "step_count": step_count_at_finish, "result": result}
            elif step_count_at_finish is None:
                logger.error("❌ FAILURE: finish_node never executed")
                logger.error("   Subgraph might not have resumed")
                return {"status": "failed", "error": "finish_node not executed"}
            else:
                logger.error(f"❌ FAILURE: Subgraph RESTARTED")
                logger.error(f"   Step count = {step_count_at_finish} (expected 2)")
                return {"status": "failed", "step_count": step_count_at_finish}

        except Exception as e:
            logger.error(f"❌ [SUPERVISOR] Resume error: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
