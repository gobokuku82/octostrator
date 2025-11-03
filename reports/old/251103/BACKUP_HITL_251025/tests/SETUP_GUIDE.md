# HITL Test Agent - Setup Guide
**Purpose:** Isolated environment to test LangGraph 0.6 HITL patterns safely
**Location:** `backend/app/hitl_test_agent/`

---

## What We're Building

**Minimal Test Structure:**
```
hitl_test_agent/
  ├─ test_runner.py          # Main test execution script
  ├─ test_supervisor.py      # Simplified supervisor with 3 nodes
  ├─ test_subgraph.py        # Document subgraph (3 nodes)
  └─ foundation/
       ├─ separated_states.py  # State definitions (keep as-is)
       └─ checkpointer.py      # Checkpointer setup (keep as-is)
```

**Remove:**
- `cognitive_agents/` (planning not needed)
- `execution_agents/` (search, analysis not needed)
- `llm_manager/` (LLM not needed for pattern test)
- `tools/` (tools not needed)
- `supervisor/team_supervisor.py` (too complex)

**Keep:**
- `foundation/separated_states.py` (state definitions)
- `foundation/checkpointer.py` (checkpoint setup)

---

## Cleanup Steps

### Step 1: Remove Unnecessary Directories

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\hitl_test_agent

# Remove directories we don't need
rm -rf cognitive_agents
rm -rf execution_agents
rm -rf llm_manager
rm -rf tools
rm -rf supervisor
```

### Step 2: Clean Foundation Directory

```bash
cd foundation

# Keep only essential files
# Remove:
rm -f agent_adapter.py
rm -f agent_registry.py
rm -f config.py
rm -f context.py
rm -f decision_logger.py
rm -f simple_memory_service.py
rm -rf old/

# Keep:
# - separated_states.py
# - checkpointer.py
# - __init__.py
```

---

## Test Structure Design

### File 1: `test_supervisor.py`

**Purpose:** Minimal main graph (3 nodes)

```python
"""
Minimal Supervisor for HITL Testing
3 nodes: start → execute_subgraph → end
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MainState(TypedDict):
    query: str
    status: str
    subgraph_result: Dict[str, Any]


class TestSupervisor:
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.app = None
        self._subgraph_apps = {}  # Store subgraph references

    def build_graph(self):
        workflow = StateGraph(MainState)

        # Nodes
        workflow.add_node("start", self.start_node)
        workflow.add_node("execute_subgraph", self.execute_subgraph_node)
        workflow.add_node("end", self.end_node)

        # Edges
        workflow.add_edge(START, "start")
        workflow.add_edge("start", "execute_subgraph")
        workflow.add_edge("execute_subgraph", "end")
        workflow.add_edge("end", END)

        # Compile with checkpointer
        self.app = workflow.compile(checkpointer=self.checkpointer)
        logger.info("✅ Test supervisor graph compiled")

        return self.app

    def start_node(self, state: MainState) -> MainState:
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] start_node")
        logger.info(f"  Query: {state['query']}")
        logger.info("=" * 60)
        state["status"] = "started"
        return state

    async def execute_subgraph_node(self, state: MainState) -> MainState:
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] execute_subgraph_node")
        logger.info("=" * 60)

        # Import subgraph
        from test_subgraph import build_document_subgraph

        # Build and compile subgraph
        subgraph = build_document_subgraph()
        subgraph_app = subgraph.compile(checkpointer=self.checkpointer)

        # Store reference (for resume)
        session_id = "test-session-123"
        self._subgraph_apps[session_id] = subgraph_app

        # Config
        config = {"configurable": {"thread_id": session_id}}

        # Execute subgraph
        logger.info("🚀 [SUPERVISOR] Executing subgraph...")

        subgraph_state = {
            "message": "",
            "step_count": 0,
            "user_input": ""
        }

        async for event in subgraph_app.astream(subgraph_state, config):
            logger.info(f"  [SUPERVISOR] Subgraph event: {list(event.keys())}")

            # Check for interrupt
            if "__interrupt__" in event:
                logger.info("  ⚠️ [SUPERVISOR] Interrupt detected!")

                interrupt_value = event["__interrupt__"]
                if isinstance(interrupt_value, tuple):
                    interrupt_obj = interrupt_value[0]
                else:
                    interrupt_obj = interrupt_value

                interrupt_data = interrupt_obj.value if hasattr(interrupt_obj, 'value') else {}

                logger.info(f"  [SUPERVISOR] Interrupt data: {interrupt_data}")

                # Return interrupted status
                state["status"] = "interrupted"
                state["subgraph_result"] = {
                    "status": "interrupted",
                    "interrupt_data": interrupt_data
                }
                return state

        # Subgraph completed normally
        logger.info("  ✅ [SUPERVISOR] Subgraph completed")
        state["status"] = "completed"
        state["subgraph_result"] = {"status": "completed"}
        return state

    def end_node(self, state: MainState) -> MainState:
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] end_node")
        logger.info(f"  Status: {state['status']}")
        logger.info("=" * 60)
        return state

    async def resume_workflow(self, session_id: str):
        """Resume subgraph directly (Test 4 pattern)"""
        logger.info("=" * 60)
        logger.info("[SUPERVISOR] resume_workflow")
        logger.info(f"  Session: {session_id}")
        logger.info("=" * 60)

        # Get stored subgraph app
        subgraph_app = self._subgraph_apps.get(session_id)

        if not subgraph_app:
            logger.error("❌ No subgraph app found")
            return {"error": "Subgraph not found"}

        config = {"configurable": {"thread_id": session_id}}

        # Resume subgraph directly
        logger.info("🔄 [SUPERVISOR] Resuming subgraph directly...")

        result = None
        async for event in subgraph_app.astream(None, config):
            logger.info(f"  [SUPERVISOR] Resume event: {list(event.keys())}")
            result = event

            # Check step_count in finish_node
            if "finish" in event:
                step_count = event["finish"].get("step_count", 0)
                logger.info(f"  ✅ [SUPERVISOR] finish_node executed! Step count: {step_count}")

                if step_count == 2:
                    logger.info("  ✅ SUCCESS: Subgraph continued from interrupt (not restarted)")
                else:
                    logger.error(f"  ❌ FAILURE: Subgraph restarted (step_count={step_count}, expected 2)")

        return {"status": "resumed", "result": result}
```

---

### File 2: `test_subgraph.py`

**Purpose:** Minimal document subgraph (3 nodes)

```python
"""
Minimal Document Subgraph for HITL Testing
3 nodes: work → interrupt → finish
"""

from langgraph.graph import StateGraph, START, END
from langgraph.errors import NodeInterrupt
from typing import TypedDict
import logging

logger = logging.getLogger(__name__)


class SubgraphState(TypedDict):
    message: str
    step_count: int
    user_input: str


def work_node(state: SubgraphState) -> SubgraphState:
    """Step 1: Do some work"""
    logger.info("🔧 [SUBGRAPH] work_node")
    state["message"] = "Work done"
    state["step_count"] = state.get("step_count", 0) + 1
    logger.info(f"   Step count: {state['step_count']}")
    return state


def interrupt_node(state: SubgraphState) -> SubgraphState:
    """Step 2: HITL interrupt"""
    logger.info("🛑 [SUBGRAPH] interrupt_node")
    logger.info("   Raising NodeInterrupt...")

    # Note: step_count NOT incremented here (interrupt prevents it)
    raise NodeInterrupt({
        "type": "user_confirmation_required",
        "message": "Please confirm",
        "step_count": state.get("step_count", 0)
    })


def finish_node(state: SubgraphState) -> SubgraphState:
    """Step 3: Complete workflow"""
    logger.info("✅ [SUBGRAPH] finish_node")
    state["message"] = "Completed"
    state["step_count"] = state.get("step_count", 0) + 1
    logger.info(f"   Step count: {state['step_count']}")
    return state


def build_document_subgraph() -> StateGraph:
    """Build the document subgraph"""
    subgraph = StateGraph(SubgraphState)

    # Nodes
    subgraph.add_node("work", work_node)
    subgraph.add_node("interrupt", interrupt_node)
    subgraph.add_node("finish", finish_node)

    # Edges
    subgraph.add_edge(START, "work")
    subgraph.add_edge("work", "interrupt")
    subgraph.add_edge("interrupt", "finish")
    subgraph.add_edge("finish", END)

    logger.info("✅ [SUBGRAPH] Graph built")
    return subgraph
```

---

### File 3: `test_runner.py`

**Purpose:** Execute tests

```python
"""
HITL Test Runner
Run different test scenarios
"""

import asyncio
import logging
from test_supervisor import TestSupervisor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_direct_subgraph_resume():
    """
    Test Scenario 4: Direct Subgraph Resume

    Expected Result:
    ✅ SUCCESS: step_count = 2 (work=1, finish=1)
    ❌ FAILURE: step_count = 3+ (restart detected)
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Direct Subgraph Resume (Scenario 4)")
    logger.info("=" * 80)

    # Create supervisor
    supervisor = TestSupervisor()
    app = supervisor.build_graph()

    # Config
    session_id = "test-session-123"
    config = {"configurable": {"thread_id": session_id}}

    # Phase 1: Initial execution
    logger.info("\n--- PHASE 1: Initial Execution ---")

    initial_state = {
        "query": "Create document",
        "status": "initialized",
        "subgraph_result": {}
    }

    result = None
    async for event in app.astream(initial_state, config):
        logger.info(f"[TEST] Event: {list(event.keys())}")
        result = event

    # Check if interrupted
    final_state = result.get("end", {})
    if final_state.get("status") != "interrupted":
        logger.error("❌ TEST FAILED: Expected 'interrupted' status")
        return False

    logger.info("✅ Phase 1 complete: Workflow interrupted")

    # Phase 2: Resume
    logger.info("\n--- PHASE 2: Resume ---")
    logger.info("[TEST] Simulating user confirmation...")

    # Resume via supervisor method
    resume_result = await supervisor.resume_workflow(session_id)

    logger.info(f"\n[TEST] Resume result: {resume_result}")

    # Analysis
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULT ANALYSIS")
    logger.info("=" * 80)

    # Check logs manually for step_count
    # If step_count in finish_node == 2 → SUCCESS
    # If step_count in finish_node == 3+ → FAILURE (restart)

    return True


async def main():
    """Run all tests"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 HITL Test Suite - Direct Subgraph Resume")
    logger.info("=" * 80)

    success = await test_direct_subgraph_resume()

    logger.info("\n" + "=" * 80)
    logger.info("TESTS COMPLETE")
    logger.info("=" * 80)

    if success:
        logger.info("✅ Check logs above for step_count values")
        logger.info("   Expected: finish_node step_count = 2")
        logger.info("   If higher: Subgraph restarted (Issue #4796)")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Expected Test Results

### SUCCESS Case ✅

```
[SUBGRAPH] work_node
   Step count: 1

[SUBGRAPH] interrupt_node
   Raising NodeInterrupt...

[SUPERVISOR] Interrupt detected!

--- USER CONFIRMS ---

[SUPERVISOR] Resuming subgraph directly...

[SUBGRAPH] finish_node  ← Directly to finish!
   Step count: 2  ← SUCCESS! (work=1, finish=1)

✅ SUCCESS: Subgraph continued from interrupt (not restarted)
```

---

### FAILURE Case ❌ (Issue #4796)

```
[SUBGRAPH] work_node
   Step count: 1

[SUBGRAPH] interrupt_node
   Raising NodeInterrupt...

[SUPERVISOR] Interrupt detected!

--- USER CONFIRMS ---

[SUPERVISOR] Resuming subgraph directly...

[SUBGRAPH] work_node  ← RESTART detected!
   Step count: 2  ← work_node executed AGAIN

[SUBGRAPH] interrupt_node
   Step count: 3

[SUBGRAPH] finish_node
   Step count: 4  ← FAILURE! (expected 2)

❌ FAILURE: Subgraph restarted (step_count=4, expected 2)
```

---

## Next Steps After Test

### If Test Succeeds ✅

1. **Pattern confirmed working**
2. **Apply to production code:**
   - Add `_subgraph_apps` dict to TeamBasedSupervisor
   - Store document_app reference in `_execute_single_team()`
   - Resume subgraph directly in `resume_document_workflow()`
3. **Test integration**
4. **Done!** 🎉

---

### If Test Fails ❌

1. **Issue #4796 confirmed**
2. **Try alternative patterns:**
   - Test 2: `interrupt()` function
   - Test 3: `Command(resume=...)` API
3. **If all fail:**
   - Implement workaround
   - OR flatten architecture

---

## File Cleanup Commands

```bash
# Navigate to hitl_test_agent
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\hitl_test_agent

# Remove unnecessary directories
rm -rf cognitive_agents
rm -rf execution_agents
rm -rf llm_manager
rm -rf tools
rm -rf supervisor

# Clean foundation directory
cd foundation
rm -f agent_adapter.py agent_registry.py config.py context.py decision_logger.py simple_memory_service.py
rm -rf old

# Go back to hitl_test_agent root
cd ..

# Create test files (will be done in next step)
```

---

## Ready to Execute

**Status:** Setup guide complete
**Next:** Clean up files and create test structure
**Estimated Time:** 30 minutes setup + 30 minutes testing = 1 hour total

