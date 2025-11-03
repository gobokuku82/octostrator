# Chat Session Deletion Error Analysis

**Date:** 2025-10-21
**Issue:** Session deletion fails with SQLAlchemy ArgumentError
**Severity:** 🔴 Critical (User-facing functionality broken)
**Status:** ✅ Analyzed & Solution Identified

---

## Problem Summary

채팅 세션 삭제 버튼을 클릭하면 삭제가 실패하고 "세션 삭제에 실패했습니다" 에러 메시지가 표시됩니다.

---

## Error Details

### Frontend Error (Console)
```
DELETE http://localhost:8000/api/v1/chat/sessions/session-dcf06392-c551-4c1f-b23b-77e940756c8d?hard_delete=true 500 (Internal Server Error)

[useChatSessions] Failed to delete session: Error: Failed to delete session: Internal Server Error
```

### Backend Error (Logs)
```python
sqlalchemy.exc.ArgumentError: Textual SQL expression 'DELETE FROM checkpoints W...'
should be explicitly declared as text('DELETE FROM checkpoints W...')

File "C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\api\chat_api.py", line 482, in delete_chat_session
    await db.execute(
```

**Full Stack Trace:**
```
Traceback (most recent call last):
  File "chat_api.py", line 482, in delete_chat_session
    await db.execute(
  File "sqlalchemy/ext/asyncio/session.py", line 455, in execute
  File "sqlalchemy/orm/session.py", line 2088, in _execute_internal
    statement = coercions.expect(roles.StatementRole, statement)
  File "sqlalchemy/sql/coercions.py", line 601, in _no_text_coercion
    raise exc_cls(
sqlalchemy.exc.ArgumentError: Textual SQL expression 'DELETE FROM checkpoints W...'
should be explicitly declared as text('DELETE FROM checkpoints W...')
```

---

## Root Cause Analysis

### 1. SQLAlchemy 2.0 Breaking Change

**Issue:** SQLAlchemy 2.0부터 텍스트 SQL을 사용할 때 명시적으로 `text()` 함수로 선언해야 합니다.

**Before (SQLAlchemy 1.x - Works):**
```python
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

**After (SQLAlchemy 2.x - Required):**
```python
from sqlalchemy import text

await db.execute(
    text("DELETE FROM checkpoints WHERE session_id = :session_id"),
    {"session_id": session_id}
)
```

### 2. Affected Code Locations

#### Location 1: chat_api.py (Lines 482-489)

**File:** `backend/app/api/chat_api.py`

```python
# Line 482-485 ❌ BROKEN
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)

# Line 486-489 ❌ BROKEN
await db.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

#### Location 2: postgres_session_manager.py (Lines 216-223)

**File:** `backend/app/api/postgres_session_manager.py`

```python
# Line 217-219 ❌ BROKEN
await db_session.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)

# Line 222-223 ❌ BROKEN
await db_session.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

---

## Impact Analysis

### User Impact
- ✅ **Severity:** Critical
- ✅ **Frequency:** Every time user tries to delete a session
- ✅ **Workaround:** None (feature completely broken)
- ✅ **User Experience:** Frustrating (cannot clean up old sessions)

### System Impact
- ✅ **Database:** No corruption (deletion doesn't execute)
- ✅ **Data Integrity:** Maintained (CASCADE constraints not triggered)
- ✅ **Session Accumulation:** Old sessions pile up in database

### Technical Debt
- ✅ **SQLAlchemy Version:** Using 2.x syntax incorrectly
- ✅ **Code Consistency:** Multiple locations with same issue
- ✅ **Testing Gap:** No automated tests for session deletion

---

## Solution Design

### Approach 1: Add text() Wrapper (Recommended) ✅

**Pros:**
- Simple fix (just wrap strings with text())
- Minimal code change
- SQLAlchemy 2.0 compliant
- Fast to implement

**Cons:**
- Still uses raw SQL (not ORM)

**Implementation:**
```python
from sqlalchemy import text

# Fix chat_api.py
await db.execute(
    text("DELETE FROM checkpoints WHERE session_id = :session_id"),
    {"session_id": session_id}
)

# Fix postgres_session_manager.py
await db_session.execute(
    text("DELETE FROM checkpoints WHERE session_id = :session_id"),
    {"session_id": session_id}
)
```

### Approach 2: Use ORM Delete (Alternative)

**Pros:**
- Fully ORM-based
- Type-safe
- Better for future maintenance

**Cons:**
- Requires Checkpoint model definitions
- More code changes
- May break if models don't exist

**Implementation:**
```python
from sqlalchemy import delete
from app.models.checkpoint import Checkpoint, CheckpointWrite

# ORM-based delete
await db.execute(
    delete(Checkpoint).where(Checkpoint.session_id == session_id)
)
await db.execute(
    delete(CheckpointWrite).where(CheckpointWrite.session_id == session_id)
)
```

### Recommendation: **Approach 1** ✅

Use `text()` wrapper for immediate fix. Consider refactoring to ORM in Phase 2.

---

## Implementation Plan

### Phase 1: Immediate Fix (5 minutes)

1. ✅ Add `text` import to both files
2. ✅ Wrap all SQL strings with `text()`
3. ✅ Test session deletion
4. ✅ Verify no regression

### Phase 2: Testing (10 minutes)

1. ✅ Test hard delete
2. ✅ Test soft delete (if implemented)
3. ✅ Verify CASCADE works (messages deleted)
4. ✅ Check database cleanup

### Phase 3: Documentation (5 minutes)

1. ✅ Update API documentation
2. ✅ Add code comments
3. ✅ Create patch notes

---

## Code Changes Required

### File 1: chat_api.py

**Location:** Lines 482-489

**Before:**
```python
# checkpoints 관련 테이블도 정리
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

**After:**
```python
from sqlalchemy import text

# checkpoints 관련 테이블도 정리
await db.execute(
    text("DELETE FROM checkpoints WHERE session_id = :session_id"),
    {"session_id": session_id}
)
await db.execute(
    text("DELETE FROM checkpoint_writes WHERE session_id = :session_id"),
    {"session_id": session_id}
)
```

### File 2: postgres_session_manager.py

**Location:** Lines 216-223

**Before:**
```python
# checkpoints 테이블 정리
await db_session.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
# checkpoint_writes 테이블 정리
await db_session.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

**After:**
```python
from sqlalchemy import text

# checkpoints 테이블 정리
await db_session.execute(
    text("DELETE FROM checkpoints WHERE session_id = :session_id"),
    {"session_id": session_id}
)
# checkpoint_writes 테이블 정리
await db_session.execute(
    text("DELETE FROM checkpoint_writes WHERE session_id = :session_id"),
    {"session_id": session_id}
)
```

---

## Testing Checklist

### Functional Testing
- [ ] Hard delete removes session from `chat_sessions`
- [ ] Hard delete removes messages from `chat_messages` (CASCADE)
- [ ] Hard delete removes checkpoints from `checkpoints`
- [ ] Hard delete removes writes from `checkpoint_writes`
- [ ] Frontend shows success message after deletion
- [ ] Session list updates correctly after deletion
- [ ] Auto-select next session after current deleted

### Error Handling
- [ ] Non-existent session returns 404
- [ ] Invalid session_id returns 400
- [ ] Database error returns 500 with proper message

### Database Verification
```sql
-- Before deletion
SELECT COUNT(*) FROM chat_sessions WHERE session_id = 'session-xxx';  -- 1
SELECT COUNT(*) FROM chat_messages WHERE session_id = 'session-xxx';  -- N
SELECT COUNT(*) FROM checkpoints WHERE session_id = 'session-xxx';    -- N
SELECT COUNT(*) FROM checkpoint_writes WHERE session_id = 'session-xxx'; -- N

-- After deletion
SELECT COUNT(*) FROM chat_sessions WHERE session_id = 'session-xxx';  -- 0
SELECT COUNT(*) FROM chat_messages WHERE session_id = 'session-xxx';  -- 0
SELECT COUNT(*) FROM checkpoints WHERE session_id = 'session-xxx';    -- 0
SELECT COUNT(*) FROM checkpoint_writes WHERE session_id = 'session-xxx'; -- 0
```

---

## Related Files

| File | Purpose | Changes Required |
|------|---------|------------------|
| `backend/app/api/chat_api.py` | DELETE endpoint | Add text() wrapper |
| `backend/app/api/postgres_session_manager.py` | Session cleanup | Add text() wrapper |
| `frontend/src/hooks/use-chat-sessions.ts` | Delete handler | No changes needed |
| `frontend/src/components/session-list.tsx` | Delete button | No changes needed |

---

## Risk Assessment

### Low Risk ✅
- Simple fix (add text() wrapper)
- No logic changes
- No schema changes
- Backward compatible

### Mitigation
- Test in development first
- Verify CASCADE constraints work
- Check database cleanup
- Monitor error logs

---

## Rollback Plan

If fix causes issues:

1. Revert text() wrapper
2. Use ORM delete instead
3. Or temporarily disable delete feature
4. Investigate further

**Rollback Time:** < 2 minutes

---

## Prevention Measures

### Short-term
1. ✅ Fix all text SQL with text() wrapper
2. ✅ Add unit tests for delete endpoint
3. ✅ Add integration tests

### Long-term
1. ✅ Create SQLAlchemy 2.0 migration guide
2. ✅ Audit all raw SQL queries
3. ✅ Prefer ORM over raw SQL
4. ✅ Add pre-commit hook for SQL string detection

### Code Review Checklist
- [ ] All raw SQL uses `text()` wrapper
- [ ] All endpoints have error handling
- [ ] All database operations have tests
- [ ] All user-facing errors have friendly messages

---

## Conclusion

**Root Cause:** SQLAlchemy 2.0 requires explicit `text()` wrapper for raw SQL queries

**Solution:** Wrap SQL strings with `text()` in 2 files (4 occurrences total)

**Impact:** Critical user-facing bug (session deletion broken)

**Effort:** 5 minutes to fix, 10 minutes to test

**Status:** Ready to implement ✅

---

**Analyzed by:** Claude Code
**Date:** 2025-10-21
**Priority:** 🔴 P0 (Critical Bug Fix)
**Estimated Fix Time:** 15 minutes total
