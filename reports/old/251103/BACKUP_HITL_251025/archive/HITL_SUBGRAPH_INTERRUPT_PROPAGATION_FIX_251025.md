# HITL Subgraph Interrupt Propagation Fix Plan
**Date:** 2025-10-25
**Status:** Planning
**Priority:** Critical
**Related Reports:**
- LANGGRAPH_06_HITL_ANALYSIS_AND_SOLUTIONS_251025.md
- IMMEDIATE_FIX_PLAN_251025.md

---

## Executive Summary

### Current Status
✅ **HITL Interrupt Detection Working**
- NodeInterrupt raised in Document Subgraph collaborate_node
- Interrupt properly detected in Main Supervisor
- State fields (workflow_status, interrupt_type, interrupt_data) correctly stored
- Main Supervisor routes to END successfully

❌ **Workflow Resume Not Working**
- After user confirmation, workflow does not continue
- Frontend stuck on "문서 편집 모드가 시작되었습니다" message
- No response generated after resume attempt

---

## Root Cause Analysis

### Problem: Subgraph Interrupt ≠ Parent Graph Interrupt

**Current Architecture:**
```
MainSupervisor Graph
  └─> execute_teams_node()
        └─> Document Subgraph.ainvoke()
              └─> collaborate_node → raise NodeInterrupt ❌
        ← Returns: state with workflow_status="interrupted"
  └─> _route_after_execution()
        → Detects workflow_status="interrupted"
        → Routes to "end"
        → Main Graph TERMINATES ❌
```

**What Happens:**
1. Document Subgraph raises NodeInterrupt in collaborate_node
2. `_execute_single_team()` catches interrupt, sets workflow_status="interrupted"
3. `execute_teams_node()` returns state to Main Supervisor
4. `_route_after_execution()` sees workflow_status="interrupted"
5. **Main Supervisor routes to END and TERMINATES**

**Result:** Main Supervisor graph is COMPLETED, not PAUSED.

**When Resume is Attempted:**
```python
# team_supervisor.py:1879
async for event in self.app.astream(None, config=config):
    # ❌ Main graph already completed (no checkpoint to resume from)
    # ❌ Nothing to stream - loop never executes
```

---

## LangGraph 0.6 HITL Correct Pattern

### How Interrupts Must Work with Subgraphs

**LangGraph 0.6 Rule:**
> When a subgraph raises NodeInterrupt, the parent graph must ALSO raise NodeInterrupt to preserve the execution state for resumption.

**Correct Flow:**
```
MainSupervisor Graph
  └─> execute_teams_node()
        └─> Document Subgraph.ainvoke()
              └─> collaborate_node → raise NodeInterrupt
        ← Detects interrupt in subgraph
        → PROPAGATES NodeInterrupt to parent graph ✅
  → Main Graph PAUSES (checkpoint saved) ✅
  → User provides input
  → resume_document_workflow() calls astream(None)
  → Main Graph RESUMES from checkpoint ✅
  → execute_teams_node() continues
  → Document Subgraph RESUMES from collaborate_node ✅
  → Workflow completes successfully ✅
```

---

## Key Insight: Why Current Design Fails

### Issue 1: Return State Instead of Raise Interrupt

**Current Code (execute_teams_node:806-817):**
```python
for team_name, team_result in results.items():
    if team_result.get("status") == "interrupted":
        logger.info(f"Workflow interrupted by team '{team_name}'")
        state = StateManager.merge_team_results(state, team_name, team_result)

        # ✅ Store interrupt info in state
        state["workflow_status"] = "interrupted"
        state["interrupted_by"] = team_name
        state["interrupt_type"] = team_result.get("interrupt_type", "unknown")
        state["interrupt_data"] = team_result.get("interrupt_data", {})

        return state  # ❌ Returns state - graph continues to routing
```

**Problem:** Returning state causes the graph to continue to the next node (_route_after_execution), which routes to END, **terminating the graph**.

**Solution:** Must **raise NodeInterrupt** instead of returning state.

---

### Issue 2: Routing to END Terminates Graph

**Current Code (_route_after_execution:148-170):**
```python
def _route_after_execution(self, state: MainSupervisorState) -> str:
    workflow_status = state.get("workflow_status", "")
    if workflow_status == "interrupted":
        logger.info(f"Workflow interrupted (HITL) - routing to END")
        return "end"  # ❌ Terminates graph - no checkpoint to resume from
```

**Problem:** Routing to END completes the graph execution, making it impossible to resume.

**Solution:** Don't route - raise NodeInterrupt directly in execute_teams_node() before any routing occurs.

---

## Solution Design

### Option A: Propagate Interrupt in execute_teams_node (RECOMMENDED)

**Modification Location:** `team_supervisor.py:806-817`

**Current Code:**
```python
for team_name, team_result in results.items():
    if team_result.get("status") == "interrupted":
        logger.info(f"Workflow interrupted by team '{team_name}'")
        state = StateManager.merge_team_results(state, team_name, team_result)

        state["workflow_status"] = "interrupted"
        state["interrupted_by"] = team_name
        state["interrupt_type"] = team_result.get("interrupt_type", "unknown")
        state["interrupt_data"] = team_result.get("interrupt_data", {})

        return state  # ❌ Problem: continues to routing
```

**New Code:**
```python
from langgraph.errors import NodeInterrupt

for team_name, team_result in results.items():
    if team_result.get("status") == "interrupted":
        logger.info(f"[TeamSupervisor] Subgraph interrupt detected - propagating to parent graph")

        # ✅ Store interrupt info in state
        state = StateManager.merge_team_results(state, team_name, team_result)
        state["workflow_status"] = "interrupted"
        state["interrupted_by"] = team_name

        # Extract interrupt details
        interrupt_type = team_result.get("interrupt_type", "unknown")
        interrupt_data = team_result.get("interrupt_data", {})

        state["interrupt_type"] = interrupt_type
        state["interrupt_data"] = interrupt_data

        logger.info(f"   Interrupted by: {team_name}")
        logger.info(f"   Interrupt type: {interrupt_type}")
        logger.info(f"   Raising NodeInterrupt to pause Main Supervisor graph")

        # ✅ CRITICAL: Raise NodeInterrupt to pause parent graph
        # This creates a checkpoint that can be resumed later
        raise NodeInterrupt(interrupt_data)
```

**Why This Works:**
1. NodeInterrupt pauses Main Supervisor graph (doesn't terminate it)
2. LangGraph saves checkpoint with current state
3. `resume_document_workflow()` can call `astream(None)` to resume
4. Main graph continues from execute_teams_node
5. Document subgraph resumes from collaborate_node

---

### Option B: Remove Routing Logic (ALTERNATIVE)

**Modification Location:** `team_supervisor.py:148-170`

**Current Code:**
```python
def _route_after_execution(self, state: MainSupervisorState) -> str:
    workflow_status = state.get("workflow_status", "")
    if workflow_status == "interrupted":
        logger.info(f"Workflow interrupted (HITL) - routing to END")
        return "end"  # ❌ Terminates graph

    logger.info("Execution completed - routing to aggregate")
    return "aggregate"
```

**New Code:**
```python
def _route_after_execution(self, state: MainSupervisorState) -> str:
    # ✅ Interrupt handling now done via NodeInterrupt in execute_teams_node
    # No need to check workflow_status here

    logger.info("[TeamSupervisor] Execution completed - routing to aggregate")
    return "aggregate"
```

**Rationale:**
- With Option A, NodeInterrupt is raised BEFORE routing occurs
- Therefore, _route_after_execution() never sees interrupted state
- Simplify routing logic by removing interrupt check

---

## Implementation Plan

### Phase 1: Modify execute_teams_node() to Propagate Interrupt

**File:** `backend/app/service_agent/supervisor/team_supervisor.py`

**Line:** 806-817

**Changes:**
1. Add `from langgraph.errors import NodeInterrupt` import
2. Replace `return state` with `raise NodeInterrupt(interrupt_data)`
3. Add detailed logging for interrupt propagation

**Expected Behavior:**
- Main Supervisor graph pauses when Document subgraph interrupts
- Checkpoint saved with complete state
- Graph can be resumed via `astream(None)`

---

### Phase 2: Simplify Routing Logic

**File:** `backend/app/service_agent/supervisor/team_supervisor.py`

**Line:** 148-170

**Changes:**
1. Remove workflow_status check from _route_after_execution()
2. Always route to "aggregate" (if execution completes without interrupt)
3. Update logging to reflect new behavior

**Expected Behavior:**
- Cleaner routing logic
- No need for interrupt detection in routing (handled by NodeInterrupt)

---

### Phase 3: Verify Resume Logic

**File:** `backend/app/service_agent/supervisor/team_supervisor.py`

**Line:** 1852-1910 (`resume_document_workflow`)

**Current Code (Should Work After Phase 1):**
```python
async def resume_document_workflow(self, session_id: str) -> Dict:
    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    logger.info(f"🚀 Resuming workflow via Command API for session {session_id}")

    async for event in self.app.astream(None, config=config):
        logger.info(f"   Resume event: {list(event.keys())}")
        # ... handle events ...
```

**Why This Will Work:**
- After Phase 1, Main graph is PAUSED (not terminated)
- Checkpoint exists with state at execute_teams_node
- `astream(None)` resumes from checkpoint
- Document subgraph continues from collaborate_node

**No Changes Required** - existing code should work correctly.

---

### Phase 4: Update chat_api.py (Already Done)

**File:** `backend/app/api/chat_api.py`

**Line:** 907

**Status:** ✅ Already Fixed

**Code:**
```python
if result is None or result.get("workflow_status") == "interrupted":
    logger.info(f"[ChatAPI] Workflow interrupted (HITL) for {session_id}")
    return
```

**Note:** After Phase 1, the first query will still return a result with workflow_status="interrupted" (because NodeInterrupt pauses the graph but returns state). This check will still work correctly.

---

## Expected Test Flow

### Before Fix
1. User: "임대차계약서 작성"
2. Backend: Document subgraph raises NodeInterrupt
3. Backend: Main graph routes to END and terminates ❌
4. Backend: `[ChatAPI] Workflow interrupted (HITL)` - returns early ✅
5. User: Clicks confirm in dialog
6. Backend: `resume_document_workflow()` calls `astream(None)`
7. Backend: No events (graph already terminated) ❌
8. Frontend: Stuck on "문서 편집 모드가 시작되었습니다" ❌

---

### After Fix
1. User: "임대차계약서 작성"
2. Backend: Document subgraph raises NodeInterrupt
3. Backend: Main graph raises NodeInterrupt in execute_teams_node ✅
4. Backend: Main graph PAUSES (checkpoint saved) ✅
5. Backend: Returns state with workflow_status="interrupted"
6. Backend: `[ChatAPI] Workflow interrupted (HITL)` - returns early ✅
7. User: Clicks confirm in dialog
8. Backend: `resume_document_workflow()` calls `astream(None)` ✅
9. Backend: Main graph resumes from execute_teams_node ✅
10. Backend: Document subgraph resumes from collaborate_node ✅
11. Backend: Continues to finalize_node → generate_response_node ✅
12. Backend: Returns final document ✅
13. Frontend: Displays completed document ✅

---

## Risk Assessment

### Low Risk ✅
- **Scope:** Only 2 functions modified (execute_teams_node, _route_after_execution)
- **Pattern:** Standard LangGraph 0.6 interrupt propagation pattern
- **Reversibility:** Easy to revert if issues occur

### Potential Issues
1. **Multiple Interrupts:** If Document subgraph has multiple interrupt points, all must be handled
2. **State Consistency:** Ensure interrupt_data structure matches expectations
3. **Logging Clarity:** Distinguish between subgraph interrupt and parent interrupt

### Mitigation
- Add detailed logging at each step
- Test with single interrupt point first (collaborate_node)
- Verify checkpoint state after interrupt

---

## Success Criteria

### Functional Requirements
✅ User can request document creation
✅ Dialog opens with editable fields
✅ User can confirm/edit and click confirm button
✅ Workflow resumes from collaborate_node
✅ Document generation completes
✅ Final response sent to frontend
✅ No error messages

### Technical Requirements
✅ Main Supervisor graph pauses (not terminates) on subgraph interrupt
✅ Checkpoint saved with complete state
✅ `astream(None)` successfully resumes workflow
✅ Document subgraph continues from collaborate_node
✅ All progress messages sent via WebSocket

### Logging Requirements
✅ Clear distinction between subgraph and parent interrupts
✅ Checkpoint save/load events logged
✅ Resume events logged with node names

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review LangGraph 0.6 interrupt propagation documentation
- [ ] Backup current team_supervisor.py
- [ ] Review Document subgraph structure (collaborate_node routing)

### Phase 1: Propagate Interrupt
- [ ] Add NodeInterrupt import to team_supervisor.py
- [ ] Modify execute_teams_node() to raise NodeInterrupt
- [ ] Add detailed logging for interrupt propagation
- [ ] Test: Verify Main graph pauses (not terminates)

### Phase 2: Simplify Routing
- [ ] Remove workflow_status check from _route_after_execution()
- [ ] Update logging messages
- [ ] Test: Verify normal (non-interrupt) flow still works

### Phase 3: Integration Test
- [ ] Test full HITL flow: request → interrupt → confirm → resume → complete
- [ ] Verify all WebSocket messages sent correctly
- [ ] Verify no error messages in frontend
- [ ] Check PostgreSQL checkpoints table for saved state

### Post-Implementation
- [ ] Update HITL implementation documentation
- [ ] Create test cases for HITL flow
- [ ] Monitor production logs for any issues

---

## Related Code Locations

### Files to Modify
1. **team_supervisor.py**
   - Line 806-817: execute_teams_node() - Add NodeInterrupt propagation
   - Line 148-170: _route_after_execution() - Remove interrupt check

### Files Already Fixed
1. **chat_api.py**
   - Line 907: HITL detection logic - ✅ Working

### Files to Verify (No Changes Expected)
1. **team_supervisor.py**
   - Line 1852-1910: resume_document_workflow() - Should work after fix

2. **document_executor.py**
   - collaborate_node: NodeInterrupt raising - ✅ Working correctly

---

## Conclusion

This fix addresses the **fundamental LangGraph 0.6 pattern** for handling interrupts in subgraphs:

**Core Principle:** When a subgraph raises NodeInterrupt, the parent graph must propagate it by also raising NodeInterrupt, not by routing to END.

**Impact:** Minimal code changes (2 functions) with maximum effect (enables complete HITL workflow).

**Confidence:** High - follows official LangGraph 0.6 patterns for interrupt handling.

---

## Next Steps

1. Review this plan with user for approval
2. Implement Phase 1 (interrupt propagation)
3. Test interrupt behavior
4. Implement Phase 2 (routing cleanup)
5. Test complete HITL flow
6. Update documentation

---

**End of Plan**
