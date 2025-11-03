# Chat Session Deletion Fix Plan

**Date:** 2025-10-21
**Issue:** Session deletion fails with column name error
**Severity:** 🔴 Critical (User-facing functionality broken)
**Status:** 📋 Analysis Complete - Ready for Implementation

---

## Problem Summary

채팅 세션 삭제 버튼 클릭 시 500 Internal Server Error 발생

**User Impact:**
- ✅ 채팅 세션 삭제 불가
- ✅ 오래된 세션들이 계속 누적
- ✅ 사용자 경험 저하

---

## Root Cause Analysis

### Error Message (Backend Log)

```python
sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedColumn)
"session_id" 이름의 칼럼은 없습니다
LINE 1: DELETE FROM checkpoints WHERE session_id = $1
                                      ^
[SQL: DELETE FROM checkpoints WHERE session_id = %(session_id)s]
```

### Real Problem: Incorrect Column Name ❌

**코드에서 사용:** `session_id`
**실제 DB 컬럼:** `thread_id`

### Database Schema Analysis

#### Table 1: checkpoints
```sql
\d checkpoints

필드명                  | 형태
-----------------------|-------
thread_id              | text   (not null) ✅
checkpoint_ns          | text
checkpoint_id          | text
parent_checkpoint_id   | text
type                   | text
checkpoint             | jsonb
metadata               | jsonb
```

**Key:** `thread_id` (NOT session_id!)

#### Table 2: checkpoint_writes
```sql
\d checkpoint_writes

필드명         | 형태
--------------|----------
thread_id     | text   (not null) ✅
checkpoint_ns | text
checkpoint_id | text
task_id       | text
idx           | integer
channel       | text
type          | text
blob          | bytea
task_path     | text
```

**Key:** `thread_id` (NOT session_id!)

#### Table 3: checkpoint_blobs
```sql
\d checkpoint_blobs

필드명         | 형태
--------------|-------
thread_id     | text   (not null) ✅
checkpoint_ns | text
channel       | text
version       | text
type          | text
blob          | bytea
```

**Key:** `thread_id` (NOT session_id!)

### Data Verification

```sql
SELECT thread_id FROM checkpoints LIMIT 5;

thread_id
-------------------------------------------
session-ad7e7fe3-dccf-4c56-b87f-628dda96485f
session-ad7e7fe3-dccf-4c56-b87f-628dda96485f
...
```

**결론:** `thread_id` 값이 `session-xxx` 형식으로 저장됨
→ **session_id == thread_id** (값은 동일, 컬럼명만 다름)

---

## Affected Code

### Location 1: chat_api.py (Lines 482-493)

**File:** `backend/app/api/chat_api.py`

```python
# ❌ WRONG - Uses session_id (column doesn't exist)
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db.execute(
    "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

**Should be:**
```python
# ✅ CORRECT - Uses thread_id (actual column name)
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

### Location 2: postgres_session_manager.py (Lines 216-228)

**File:** `backend/app/api/postgres_session_manager.py`

```python
# ❌ WRONG - Uses session_id
await db_session.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db_session.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db_session.execute(
    "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
    {"session_id": session_id}
)
```

**Should be:**
```python
# ✅ CORRECT - Uses thread_id
await db_session.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db_session.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db_session.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

---

## Two Issues to Fix

### Issue 1: Wrong Column Name ❌
- **Current:** `session_id`
- **Correct:** `thread_id`

### Issue 2: Missing text() Wrapper (SQLAlchemy 2.0) ❌
- **Current:** Raw string `"DELETE FROM..."`
- **Correct:** `text("DELETE FROM...")`

---

## Implementation Plan

### Step 1: Add text Import (2 files)

#### File: chat_api.py
```python
from sqlalchemy import func, text  # Add text
```

#### File: postgres_session_manager.py
```python
from sqlalchemy import select, delete, update, func, text  # Add text
```

### Step 2: Fix DELETE Queries (6 occurrences total)

#### chat_api.py (3 occurrences)

**Line 482-485:**
```python
# Before
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

**Line 486-489:**
```python
# Before
await db.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

**Line 490-493:**
```python
# Before
await db.execute(
    "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

#### postgres_session_manager.py (3 occurrences)

**Line 217-219:**
```python
# Before
await db_session.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db_session.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

**Line 222-224:**
```python
# Before
await db_session.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db_session.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

**Line 226-228:**
```python
# Before
await db_session.execute(
    "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db_session.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

---

## Changes Summary

| File | Line | Change Type | Before | After |
|------|------|-------------|--------|-------|
| chat_api.py | 12 | Import | `from sqlalchemy import func` | `from sqlalchemy import func, text` |
| chat_api.py | 483 | Column + text() | `session_id = :session_id` | `text("...thread_id = :thread_id")` |
| chat_api.py | 487 | Column + text() | `session_id = :session_id` | `text("...thread_id = :thread_id")` |
| chat_api.py | 491 | Column + text() | `session_id = :session_id` | `text("...thread_id = :thread_id")` |
| postgres_session_manager.py | 9 | Import | `from sqlalchemy import ...func` | `from sqlalchemy import ...func, text` |
| postgres_session_manager.py | 217 | Column + text() | `session_id = :session_id` | `text("...thread_id = :thread_id")` |
| postgres_session_manager.py | 222 | Column + text() | `session_id = :session_id` | `text("...thread_id = :thread_id")` |
| postgres_session_manager.py | 227 | Column + text() | `session_id = :session_id` | `text("...thread_id = :thread_id")` |

**Total:** 8 changes across 2 files

---

## Testing Plan

### Pre-Test Verification

```sql
-- Check current checkpoint data
SELECT thread_id, COUNT(*)
FROM checkpoints
GROUP BY thread_id
LIMIT 5;

-- Verify session exists
SELECT session_id FROM chat_sessions
WHERE session_id = 'session-xxx';
```

### Test Scenario 1: Delete Session with Checkpoints

1. ✅ Select a session with checkpoint data
2. ✅ Click delete button
3. ✅ Verify 200 OK response (not 500)
4. ✅ Check session removed from UI
5. ✅ Verify DB cleanup

### Test Scenario 2: Delete Session without Checkpoints

1. ✅ Select a fresh session (no checkpoints)
2. ✅ Click delete button
3. ✅ Verify 200 OK response
4. ✅ Check session removed

### Database Verification Queries

```sql
-- Before deletion
SELECT COUNT(*) FROM chat_sessions WHERE session_id = 'session-xxx';     -- 1
SELECT COUNT(*) FROM chat_messages WHERE session_id = 'session-xxx';     -- N
SELECT COUNT(*) FROM checkpoints WHERE thread_id = 'session-xxx';        -- N
SELECT COUNT(*) FROM checkpoint_writes WHERE thread_id = 'session-xxx';  -- N
SELECT COUNT(*) FROM checkpoint_blobs WHERE thread_id = 'session-xxx';   -- N

-- After deletion
SELECT COUNT(*) FROM chat_sessions WHERE session_id = 'session-xxx';     -- 0
SELECT COUNT(*) FROM chat_messages WHERE session_id = 'session-xxx';     -- 0 (CASCADE)
SELECT COUNT(*) FROM checkpoints WHERE thread_id = 'session-xxx';        -- 0
SELECT COUNT(*) FROM checkpoint_writes WHERE thread_id = 'session-xxx';  -- 0
SELECT COUNT(*) FROM checkpoint_blobs WHERE thread_id = 'session-xxx';   -- 0
```

### Expected Frontend Behavior

**Before Fix:**
```
DELETE .../sessions/session-xxx?hard_delete=true 500 (Internal Server Error)
[useChatSessions] Failed to delete session: Error: Failed to delete session: Internal Server Error
```

**After Fix:**
```
DELETE .../sessions/session-xxx?hard_delete=true 200 (OK)
[useChatSessions] Session deleted successfully: session-xxx
```

---

## Risk Assessment

### Low Risk ✅
- Simple column name fix
- text() wrapper required by SQLAlchemy 2.0
- No schema changes
- No logic changes
- Backward compatible

### Mitigation
- Test with multiple sessions
- Verify CASCADE works
- Check all 3 checkpoint tables cleaned
- Monitor backend logs for errors

---

## Rollback Plan

If issues occur:

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001
git restore backend/app/api/chat_api.py
git restore backend/app/api/postgres_session_manager.py
# Restart backend
```

**Rollback Time:** < 1 minute

---

## Implementation Checklist

### Phase 1: Code Changes (5 minutes)
- [ ] Add `text` import to chat_api.py
- [ ] Fix 3 DELETE queries in chat_api.py (session_id → thread_id + text())
- [ ] Add `text` import to postgres_session_manager.py
- [ ] Fix 3 DELETE queries in postgres_session_manager.py (session_id → thread_id + text())

### Phase 2: Testing (10 minutes)
- [ ] Restart backend server
- [ ] Test delete session with checkpoints
- [ ] Test delete session without checkpoints
- [ ] Verify DB cleanup (all 5 tables)
- [ ] Check frontend UI updates correctly
- [ ] Verify no errors in backend logs

### Phase 3: Documentation (5 minutes)
- [ ] Update this report with test results
- [ ] Create patch notes
- [ ] Document column name mapping (session_id ↔ thread_id)

---

## Key Insights

### Why thread_id instead of session_id?

LangGraph checkpoint tables use **`thread_id`** as the primary key:
- LangGraph concept: "thread" = conversation thread
- Our concept: "session" = chat session
- Mapping: **session_id == thread_id** (same value, different terminology)

### Why both fixes needed?

1. **Column name:** Database has `thread_id`, not `session_id`
2. **text() wrapper:** SQLAlchemy 2.0 requires explicit `text()` for raw SQL

---

## Success Criteria

✅ Session delete returns 200 OK
✅ Session removed from chat_sessions table
✅ Messages removed via CASCADE
✅ Checkpoints removed from all 3 tables
✅ Frontend shows success message
✅ Session list updates correctly
✅ No errors in backend logs

---

**Created by:** Claude Code
**Date:** 2025-10-21
**Status:** 📋 Ready for Implementation
**Estimated Fix Time:** 20 minutes total
**Priority:** 🔴 P0 (Critical Bug Fix)
