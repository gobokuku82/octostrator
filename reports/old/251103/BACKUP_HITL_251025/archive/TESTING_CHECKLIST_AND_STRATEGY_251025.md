# HITL Testing Strategy & Checklist
**Date:** 2025-10-25
**Purpose:** Systematic testing before any git reset or major refactoring
**Approach:** PoC first, then apply to production code

---

## Testing Philosophy

### 원칙 1: Isolate and Verify
**Before touching production code:**
1. Create minimal PoC
2. Test pattern in isolation
3. Verify it works 100%
4. Then apply to real code

**Why:**
- 실패해도 안전
- 문제 원인 명확히 파악
- 시간 절약 (역설적이지만 사실)

---

### 원칙 2: One Variable at a Time
**각 테스트는 하나의 변수만 변경:**
- Test 1: `interrupt()` vs `NodeInterrupt`
- Test 2: `Command(resume=...)` vs `astream(None)`
- Test 3: Parent resume vs Direct subgraph resume
- Test 4: Same thread_id vs Separate thread_id

**Why:**
- 어떤 변경이 효과있는지 정확히 파악
- 복합 변경 시 원인 불명확

---

### 원칙 3: Document Everything
**모든 테스트 결과 기록:**
- 예상 결과
- 실제 결과
- 로그 스크린샷
- 결론

**Why:**
- 나중에 참고
- 다른 사람과 공유
- 의사결정 근거

---

## PoC Test Plan

### File: `test_langgraph_subgraph_hitl_poc.py`

**목적:** LangGraph 패턴 자체가 작동하는지 검증

**구조:**
```
Main Graph (3 nodes)
  ├─ start
  ├─ execute_subgraph  ← 여기서 subgraph 실행
  └─ end

Subgraph (3 nodes)
  ├─ work  ← Step 1
  ├─ interrupt  ← HITL 발생
  └─ finish  ← Step 2
```

---

### Test Scenario 4: Direct Subgraph Resume ⭐ **최우선**

**왜 먼저?**
- 가장 성공 가능성 높음
- 우리 코드에 적용 쉬움
- 빠른 검증 (30분)

**Test Steps:**
```python
# 1. Execute subgraph
async for event in subgraph_app.astream(initial_state, config):
    if "__interrupt__" in event:
        break  # Interrupt detected

# 2. Resume subgraph directly
async for event in subgraph_app.astream(None, config):
    # Check: Does finish_node execute?
    if "finish" in event:
        step_count = event["finish"]["step_count"]
```

**Success Criteria:**
- ✅ `step_count == 2` (work=1, finish=1)
- ✅ `interrupt_node` 재실행 안 됨
- ✅ `finish_node` 실행됨

**Failure Criteria:**
- ❌ `step_count == 3` (work=1, interrupt=1, finish=1)
- ❌ Subgraph가 처음부터 재시작
- ❌ LangGraph Issue #4796 확정

---

### Test Scenario 1: Parent Resume (Issue #4796 재현)

**왜 테스트?**
- 현재 우리가 하는 방식
- 실패 확인 (Issue #4796)
- 문제 재현

**Test Steps:**
```python
# 1. Execute main graph
async for event in main_app.astream(initial_state, config):
    pass  # Subgraph interrupts

# 2. Resume main graph
async for event in main_app.astream(None, config):
    # Check: Does it restart from planning?
```

**Expected Result:**
- ❌ Main graph restarts from `start_node`
- ❌ Subgraph 재실행
- ❌ Issue #4796 재현됨

---

### Test Scenario 2: `interrupt()` Function

**왜 테스트?**
- Official docs 권장 방법
- `NodeInterrupt`과 다른 API
- 자동 resume 가능성

**Requirements:**
- LangGraph 버전 확인 필요
- `from langgraph.types import interrupt`

**Test Steps:**
```python
def interrupt_node(state):
    user_input = interrupt("Please confirm")
    # Execution continues here after user provides input!
    state["user_input"] = user_input
    return state
```

**Success Criteria:**
- ✅ `interrupt()` 호출 시 일시정지
- ✅ User input 제공 후 자동 재개
- ✅ 다음 줄 실행됨

**Challenge:**
- WebSocket 통합 방법 확인 필요
- User input을 어떻게 전달?

---

### Test Scenario 3: `Command(resume=...)`

**왜 테스트?**
- Official docs에서 사용
- User input 전달 메커니즘

**Test Steps:**
```python
# Resume with Command
from langgraph.types import Command

async for event in graph.astream(
    Command(resume="user confirmed"),
    config
):
    pass
```

**Success Criteria:**
- ✅ Resume 시 user input 전달됨
- ✅ Subgraph가 올바른 위치에서 계속됨

---

## Production Code Test Plan

**Only proceed if PoC shows working pattern!**

### Phase 1: Minimal Change Test (1 hour)

**If Scenario 4 (Direct Subgraph Resume) works:**

**Change 1: Keep Subgraph Reference**
```python
# team_supervisor.py
class TeamBasedSupervisor:
    def __init__(self):
        self._subgraph_apps = {}  # NEW: Store compiled subgraphs

    async def _execute_single_team(self, team_name, ...):
        if team_name == "document":
            # Compile subgraph
            document_app = subgraph.compile(checkpointer=self.checkpointer)

            # Store reference
            session_id = main_state.get("session_id")
            self._subgraph_apps[session_id] = document_app  # ← NEW

            # Execute
            async for event in document_app.astream(...):
                if "__interrupt__" in event:
                    return {"status": "interrupted", ...}
```

**Change 2: Resume Subgraph Directly**
```python
# team_supervisor.py
async def resume_document_workflow(self, session_id):
    # Get stored subgraph app
    document_app = self._subgraph_apps.get(session_id)

    if not document_app:
        logger.error("No subgraph app found for session")
        return {"error": "Subgraph not found"}

    config = {"configurable": {"thread_id": session_id}}

    # Resume subgraph directly
    async for event in document_app.astream(None, config):
        logger.info(f"Resume event: {list(event.keys())}")
        # ... handle events
```

**Test:**
1. "임대차계약서 작성"
2. Dialog opens
3. Click confirm
4. ✅ Check logs: `finish_node` executes
5. ✅ Check logs: No restart from `work_node`

---

### Phase 2: Integration Test (1 hour)

**Test Full Flow:**
1. Planning → Execute → Document subgraph
2. Subgraph interrupts at collaborate_node
3. User edits document
4. User confirms
5. Subgraph continues to finalize_node
6. Final response generated
7. Frontend displays result

**Success Criteria:**
- ✅ No errors in backend logs
- ✅ No errors in frontend logs
- ✅ Document generated correctly
- ✅ All WebSocket messages sent

---

### Phase 3: Edge Case Testing (1 hour)

**Test Cases:**

1. **Multiple Interrupts**
   - collaborate_node → user_confirm_node
   - Both should work

2. **Session Cleanup**
   - Verify subgraph_app removed after completion
   - No memory leaks

3. **Concurrent Sessions**
   - Multiple users creating documents
   - No cross-session interference

4. **Error Handling**
   - Network disconnect during HITL
   - Graceful recovery

---

## Critical Considerations Checklist

### 🔍 Before Each Test

- [ ] Git branch created for test
- [ ] Backup current code
- [ ] Checkpointer configured correctly
- [ ] Logging enabled (DEBUG level)
- [ ] Test data prepared

---

### 🎯 During Test

**1. State Management**
- [ ] Verify thread_id consistency
- [ ] Check state fields preserved
- [ ] Validate TypedDict fields present
- [ ] Monitor checkpoint writes (PostgreSQL)

**2. Event Tracking**
- [ ] Log all graph events
- [ ] Track `__interrupt__` events
- [ ] Monitor node execution order
- [ ] Record step counts / timestamps

**3. Error Monitoring**
- [ ] Watch for KeyError
- [ ] Check for AttributeError
- [ ] Verify no silent failures
- [ ] Capture full stack traces

---

### ✅ After Test

**1. Result Documentation**
- [ ] Screenshot backend logs
- [ ] Screenshot frontend logs
- [ ] Record success/failure
- [ ] Note unexpected behavior

**2. Code Review**
- [ ] Check for memory leaks
- [ ] Verify resource cleanup
- [ ] Review error handling
- [ ] Validate logging messages

**3. Decision Point**
- [ ] Pattern works → Apply to production
- [ ] Pattern fails → Try next test
- [ ] All tests fail → Consider workaround/flatten

---

## Important Variables to Monitor

### 1. Step Count (Critical!)

**Purpose:** Detect if node re-executes

```python
# In each node
state["step_count"] = state.get("step_count", 0) + 1
logger.info(f"Step count: {state['step_count']}")
```

**Expected Values:**
```
Initial execution:
  work_node: step_count = 1
  interrupt_node: step_count = 2 (but raises interrupt)

After resume (SUCCESS):
  finish_node: step_count = 3  ← Only finish adds 1

After resume (FAILURE - restart):
  work_node: step_count = 4  ← work executed again!
  interrupt_node: step_count = 5
  finish_node: step_count = 6
```

**Red Flag:** Step count > 3 after resume = restart detected!

---

### 2. Thread ID Consistency

**Check in logs:**
```
Initial: thread_id = "session-123"
Resume: thread_id = "session-123"  ← Must match!
```

**Red Flag:** Different thread_id = new execution, not resume!

---

### 3. Checkpoint Data

**Query PostgreSQL:**
```sql
SELECT thread_id, checkpoint_ns, checkpoint
FROM checkpoints
WHERE thread_id = 'session-123'
ORDER BY checkpoint_id DESC
LIMIT 5;
```

**Verify:**
- [ ] Checkpoint saved after interrupt
- [ ] `next` field shows correct node
- [ ] State data preserved

---

### 4. Event Sequence

**Expected Order:**
```
Initial Execution:
1. start_node
2. execute_subgraph_node
   3. work_node
   4. interrupt_node → __interrupt__ event
5. end_node (with interrupted status)

Resume Execution (SUCCESS):
1. finish_node  ← Directly to finish!
2. (no other nodes)

Resume Execution (FAILURE):
1. start_node  ← Restart from beginning!
2. execute_subgraph_node
   3. work_node
   4. interrupt_node
   5. finish_node
```

**Red Flag:** Any node before `finish_node` = restart!

---

## Debugging Tips

### If Test Fails

**1. Check LangGraph Version**
```bash
pip show langgraph
# Verify >= 0.6.0
```

**2. Enable Verbose Logging**
```python
import logging
logging.getLogger("langgraph").setLevel(logging.DEBUG)
```

**3. Inspect Checkpoint**
```python
# Get checkpoint data
state_snapshot = await checkpointer.aget_tuple(config)
print(f"Next nodes: {state_snapshot.next}")
print(f"State: {state_snapshot.values}")
```

**4. Add Breakpoints**
```python
import pdb; pdb.set_trace()
# Step through resume logic
```

---

## Decision Matrix

### If Direct Subgraph Resume Works ✅

**Action:**
1. Apply pattern to production code
2. Test with full integration
3. Keep current architecture
4. No git reset needed!

**Effort:** 2-3 hours
**Risk:** Low
**Confidence:** High

---

### If Direct Subgraph Resume Fails ❌

**Check:**
- Is it Issue #4796?
- Do other scenarios work?

**If NO scenarios work:**

**Option A: Implement Workaround**
- Save subgraph state manually
- Restore and re-execute from correct node
- Effort: 1 day
- Risk: Medium

**Option B: Flatten Architecture**
- Follow previous plan
- Remove subgraph structure
- Effort: 3-4 days
- Risk: Low (proven pattern)

---

## Success Metrics

### PoC Success
- [ ] At least one test scenario passes
- [ ] Resume doesn't restart from beginning
- [ ] Step count matches expected value
- [ ] Logs show correct node execution order

### Production Success
- [ ] Full HITL flow works end-to-end
- [ ] No errors in logs
- [ ] Frontend displays correctly
- [ ] User can edit and confirm
- [ ] Document generates successfully

### Quality Metrics
- [ ] Code is clean and understandable
- [ ] Proper error handling
- [ ] Comprehensive logging
- [ ] No memory leaks
- [ ] Thread-safe (multiple sessions)

---

## Timeline Estimates

### PoC Testing
- Scenario 4 (Direct resume): 30 min
- Scenario 1 (Parent resume): 30 min
- Scenario 2 (interrupt()): 1 hour
- Scenario 3 (Command): 30 min
- **Total:** 2.5 hours

### Production Application
- Code changes: 1 hour
- Integration testing: 1 hour
- Edge case testing: 1 hour
- **Total:** 3 hours

### Grand Total: 5.5 hours

**vs. Flatten Architecture: 3-4 days (24-32 hours)**

---

## Risk Assessment

### Low Risk ✅
- PoC testing (separate file)
- Small code changes (if pattern works)
- Easy rollback

### Medium Risk ⚠️
- Production integration
- Multiple concurrent sessions
- State synchronization

### High Risk 🔴
- Flatten architecture (if all tests fail)
- Major refactoring
- Breaking changes

---

## Next Steps

**Immediate:**
1. Run PoC Test Scenario 4
2. Analyze results
3. Document findings
4. Present to user

**If Test Passes:**
1. Apply to production code
2. Test integration
3. Deploy

**If Test Fails:**
1. Try other scenarios
2. Analyze logs
3. Consult with user
4. Decide: Workaround vs Flatten

---

## 최종 체크리스트

### Before Starting
- [ ] Read this entire document
- [ ] Understand each test scenario
- [ ] Prepare test environment
- [ ] Backup current code

### During Testing
- [ ] Follow test steps exactly
- [ ] Log everything
- [ ] Monitor all variables
- [ ] Take screenshots

### After Testing
- [ ] Document results
- [ ] Analyze logs
- [ ] Draw conclusions
- [ ] Plan next steps

### Before Production
- [ ] All tests pass
- [ ] Code reviewed
- [ ] Edge cases covered
- [ ] User approved

---

**Created:** 2025-10-25
**Status:** Ready for Execution
**Confidence:** High (systematic approach)

