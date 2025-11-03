# Session Management Analysis for Long-term Memory Implementation

**Version**: 1.0
**Date**: 2025-10-14
**Purpose**: Analyze existing session management infrastructure to guide Long-term Memory feature integration

---

## 1. Executive Summary

### Current State
- **Session Management**: PostgreSQL-based with SQLAlchemy ORM
- **User Management**: Complete user/auth system with User, UserProfile, LocalAuth, SocialAuth models
- **Chat Persistence**: ChatSession and ChatMessage models already exist
- **WebSocket Flow**: chat_api.py → SessionManager → TeamBasedSupervisor

### Key Finding
**The infrastructure for Long-term Memory already exists!** We have:
- ✅ User management (users table)
- ✅ Chat session tracking (chat_sessions table)
- ✅ Message persistence (chat_messages table)
- ✅ Session-to-user linking (session_id + user_id)

### What's Missing
1. **Long-term Memory Models**: ConversationMemory, UserPreference, EntityMemory tables
2. **Memory Service**: LongTermMemoryService to load/save memories
3. **Workflow Integration**: Connect memory loading to planning_node
4. **Frontend UI**: Display conversation history and memory context

---

## 2. Existing Database Schema

### 2.1 Session Model (`models/session.py`)

```python
class Session(Base):
    """WebSocket 세션 모델"""
    __tablename__ = "sessions"

    # Primary Key
    session_id = Column(String(100), primary_key=True, index=True)

    # User & Metadata
    user_id = Column(String(100), nullable=True)  # ← Critical: user_id exists!
    session_metadata = Column("metadata", Text, nullable=True)  # JSON string

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), nullable=False)

    # Statistics
    request_count = Column(Integer, default=0, nullable=False)
```

**Key Points**:
- `user_id` is **optional** (nullable=True) - supports anonymous sessions
- `session_metadata` stores JSON string - can include temporary context
- 24-hour TTL by default

### 2.2 User Model (`models/users.py`)

```python
class User(Base):
    """통합 사용자 테이블"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    type = Column(Enum(UserType), nullable=False, default=UserType.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    profile = relationship("UserProfile", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")  # ← Important!
```

**Key Points**:
- `id` is Integer (NOT String) - we'll use this as user_id
- Already has `chat_sessions` relationship defined
- Supports LocalAuth and SocialAuth (Google, Kakao, Naver, Apple)

### 2.3 ChatSession Model (`models/chat.py`)

```python
class ChatSession(Base):
    """채팅 세션 모델"""
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    """채팅 메시지 모델"""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    sender_type = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
```

**Key Points**:
- ChatSession already tracks user conversations
- ChatMessage stores individual messages
- **This is the foundation for ConversationMemory!**

---

## 3. Session Management Flow

### 3.1 Session Creation (`session_manager.py`)

```python
async def create_session(
    self,
    user_id: Optional[str] = None,  # ← Can be None for anonymous
    metadata: Optional[Dict] = None
) -> Tuple[str, datetime]:
    """새 세션 생성"""
    session_id = f"session-{uuid.uuid4()}"
    # ... stores in PostgreSQL sessions table
    return session_id, expires_at
```

**Flow**:
1. Frontend calls `POST /api/v1/chat/start` with optional `user_id`
2. SessionManager creates session in DB
3. Returns `session_id` to frontend
4. Frontend uses `session_id` for WebSocket connection

### 3.2 WebSocket Connection (`chat_api.py`)

```python
@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    # 1. 세션 검증
    if not await session_mgr.validate_session(session_id):
        await websocket.close(code=4004, reason="Session not found or expired")
        return

    # 2. WebSocket 연결
    await conn_mgr.connect(session_id, websocket)

    # 3. Supervisor 가져오기
    supervisor = await get_supervisor(enable_checkpointing=True)

    # 4. 쿼리 처리
    if message_type == "query":
        asyncio.create_task(
            _process_query_async(
                supervisor=supervisor,
                query=query,
                session_id=session_id,  # ← Passed to supervisor
                enable_checkpointing=enable_checkpointing,
                progress_callback=progress_callback,
                conn_mgr=conn_mgr
            )
        )
```

**Flow**:
1. Frontend connects via WebSocket: `ws://host/api/v1/chat/ws/{session_id}`
2. Backend validates session
3. `session_id` is passed to `TeamBasedSupervisor.process_query_streaming()`

### 3.3 Query Processing (`chat_api.py:318-368`)

```python
async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,  # ← Available here
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager
):
    # Streaming 방식으로 쿼리 처리
    result = await supervisor.process_query_streaming(
        query=query,
        session_id=session_id,  # ← Passed to supervisor
        progress_callback=progress_callback
    )
```

**Critical Point**: `session_id` is already passed to TeamBasedSupervisor!

---

## 4. Integration Points for Long-term Memory

### 4.1 Data Flow Chain

```
Frontend
    ↓
POST /chat/start (with user_id)
    ↓
SessionManager.create_session()
    ↓ stores in sessions table
session_id + user_id
    ↓
WebSocket /ws/{session_id}
    ↓
chat_api.websocket_chat()
    ↓ validates session
SessionManager.get_session(session_id) → returns user_id
    ↓
_process_query_async(supervisor, session_id)
    ↓
TeamBasedSupervisor.process_query_streaming(session_id)
    ↓
initialize_node → planning_node (MEMORY LOAD HERE)
    ↓
MainSupervisorState["user_id"] = user_id
MainSupervisorState["loaded_memories"] = [...]
```

### 4.2 Required Changes

#### Change 1: Extract user_id in chat_api.py

**Location**: `chat_api.py:websocket_chat()` (Line 175-316)

**Before**:
```python
# 4. Supervisor 인스턴스 가져오기
supervisor = await get_supervisor(enable_checkpointing=True)

# Query 처리
asyncio.create_task(
    _process_query_async(
        supervisor=supervisor,
        query=query,
        session_id=session_id,
        enable_checkpointing=enable_checkpointing,
        progress_callback=progress_callback,
        conn_mgr=conn_mgr
    )
)
```

**After**:
```python
# 4. Supervisor 인스턴스 가져오기
supervisor = await get_supervisor(enable_checkpointing=True)

# 5. Extract user_id from session
session_info = await session_mgr.get_session(session_id)
user_id = session_info.get("user_id") if session_info else None  # ← NEW

# Query 처리
asyncio.create_task(
    _process_query_async(
        supervisor=supervisor,
        query=query,
        session_id=session_id,
        user_id=user_id,  # ← NEW parameter
        enable_checkpointing=enable_checkpointing,
        progress_callback=progress_callback,
        conn_mgr=conn_mgr
    )
)
```

#### Change 2: Pass user_id to supervisor

**Location**: `chat_api.py:_process_query_async()` (Line 318-368)

**Before**:
```python
async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager
):
    result = await supervisor.process_query_streaming(
        query=query,
        session_id=session_id,
        progress_callback=progress_callback
    )
```

**After**:
```python
async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    user_id: Optional[int],  # ← NEW parameter
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager
):
    result = await supervisor.process_query_streaming(
        query=query,
        session_id=session_id,
        user_id=user_id,  # ← NEW parameter
        progress_callback=progress_callback
    )
```

#### Change 3: Update MainSupervisorState

**Location**: `separated_states.py:MainSupervisorState`

**Add**:
```python
class MainSupervisorState(TypedDict):
    # ... existing fields ...

    # Long-term Memory fields (NEW)
    user_id: Optional[int]  # User ID from session
    loaded_memories: Optional[List[Dict[str, Any]]]  # Loaded memories
    memory_load_time: Optional[str]  # When memories were loaded
```

#### Change 4: Update initialize_node

**Location**: `team_supervisor.py:initialize_node()` (Line 152-167)

**Add**:
```python
async def initialize_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """초기화 노드"""
    state["start_time"] = datetime.now()
    state["status"] = "initialized"
    state["active_teams"] = []
    state["completed_teams"] = []
    state["failed_teams"] = []
    state["team_results"] = {}
    state["error_log"] = []

    # Long-term Memory initialization (NEW)
    state["user_id"] = state.get("user_id")  # Preserve user_id
    state["loaded_memories"] = None  # Will be loaded in planning_node
    state["memory_load_time"] = None

    return state
```

**Note**: We do NOT load memories here! We load in planning_node.

#### Change 5: Load memories in planning_node

**Location**: `team_supervisor.py:planning_node()` (Line 169-284)

**Add** (at the beginning of planning_node):
```python
async def planning_node(self, state: MainSupervisorState):
    """계획 수립 노드"""
    # 1. Load Long-term Memory (NEW)
    user_id = state.get("user_id")
    if user_id:
        memory_service = LongTermMemoryService()
        loaded_memories = await memory_service.load_recent_memories(
            user_id=user_id,
            limit=5  # Load last 5 conversations
        )
        state["loaded_memories"] = loaded_memories
        state["memory_load_time"] = datetime.now().isoformat()

        logger.info(f"📚 Loaded {len(loaded_memories)} memories for user {user_id}")

    # 2. Progress callback for memory_loaded
    if self.progress_callback:
        await self.progress_callback("memory_loaded", {
            "user_id": user_id,
            "memory_count": len(loaded_memories) if loaded_memories else 0
        })

    # 3. Original planning logic
    query = state.get("user_query", "")
    # ... rest of existing code ...
```

---

## 5. Type Mismatch Issue: user_id

### Problem
- `Session.user_id`: String (nullable=True)
- `User.id`: Integer (primary key)
- `ChatSession.user_id`: Integer (ForeignKey to users.id)

### Analysis
Looking at the code:
- `session_manager.py:create_session(user_id: Optional[str])` accepts String
- `users.py:User.id` is Integer
- `chat.py:ChatSession.user_id` is Integer (ForeignKey to users.id)

**This is a TYPE MISMATCH!**

### Recommended Solution

**Option 1: Change Session.user_id to Integer (RECOMMENDED)**

```python
# models/session.py
class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Changed from String(100)
    # ... rest
```

**Why?**
- Consistent with User.id (Integer)
- Consistent with ChatSession.user_id (Integer)
- Better for foreign key relationships
- Smaller storage size

**Migration Required**:
```sql
-- PostgreSQL migration
ALTER TABLE sessions ALTER COLUMN user_id TYPE INTEGER USING user_id::integer;
```

**Option 2: Keep String, Cast when Needed**

If changing the schema is too risky:
```python
# When loading session
session_info = await session_mgr.get_session(session_id)
user_id = int(session_info["user_id"]) if session_info.get("user_id") else None
```

**Recommendation**: Use Option 1 for long-term maintainability.

---

## 6. Frontend Integration Points

### 6.1 Session Start with user_id

**Current**:
```typescript
// POST /api/v1/chat/start
{
  "user_id": "optional",  // Currently optional
  "metadata": {}
}
```

**After Login**:
```typescript
// When user logs in, store user info
const userInfo = await login(email, password);
localStorage.setItem('user_id', userInfo.id);

// Start session with user_id
const sessionResponse = await fetch('/api/v1/chat/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: userInfo.id,  // Pass user_id
    metadata: {}
  })
});
```

### 6.2 WebSocket Message: memory_loaded

**New Event** (sent by planning_node):
```json
{
  "type": "memory_loaded",
  "user_id": 123,
  "memory_count": 5,
  "timestamp": "2025-10-14T10:30:00Z"
}
```

**Frontend Handler**:
```typescript
case 'memory_loaded':
  console.log(`📚 Loaded ${data.memory_count} memories for user ${data.user_id}`);
  // Update UI to show memory context indicator
  break;
```

### 6.3 Conversation History API

**New Endpoints** (to be added):
```typescript
// Get user's conversation history
GET /api/v1/chat/conversations?user_id={user_id}&limit=10

// Response
{
  "conversations": [
    {
      "session_id": "session-uuid",
      "title": "부동산 투자 상담",
      "created_at": "2025-10-10T14:30:00Z",
      "last_message": "감사합니다",
      "message_count": 12
    }
  ]
}
```

---

## 7. Summary of Changes

### 7.1 Database Changes (Task 1)

**New Tables**:
1. `conversation_memories` - stores conversation summaries
2. `user_preferences` - stores user preferences
3. `entity_memories` - stores entity information

**Schema Fix**:
- Change `sessions.user_id` from String to Integer

### 7.2 Backend Changes (Tasks 2-4)

**New Files**:
1. `backend/app/models/memory.py` - Memory models
2. `backend/app/services/long_term_memory_service.py` - Memory service

**Modified Files**:
1. `backend/app/api/chat_api.py`
   - Extract user_id from session (Line ~225)
   - Pass user_id to _process_query_async (Line ~260)
   - Update _process_query_async signature (Line ~318)

2. `backend/app/service_agent/foundation/separated_states.py`
   - Add user_id, loaded_memories, memory_load_time fields

3. `backend/app/service_agent/supervisor/team_supervisor.py`
   - Update initialize_node to preserve user_id (Line ~152)
   - Add memory loading in planning_node (Line ~169)
   - Add memory saving in response_node (Line ~635)

### 7.3 Frontend Changes (Task 5)

**New Components**:
1. `ConversationHistory.tsx` - Show past conversations
2. `MemoryContextViewer.tsx` - Show loaded memory context
3. Update `PlanningIndicator.tsx` - Show memory_loaded status

**Modified Files**:
1. WebSocket handler - Handle memory_loaded event
2. Session start - Pass user_id when creating session

---

## 8. Implementation Checklist

### Phase 1: Database (Day 1)
- [ ] Create `backend/app/models/memory.py` with ConversationMemory, UserPreference, EntityMemory
- [ ] Write migration script to change sessions.user_id from String to Integer
- [ ] Run migration on development database
- [ ] Verify foreign key relationships

### Phase 2: Memory Service (Day 2)
- [ ] Create `backend/app/services/long_term_memory_service.py`
- [ ] Implement load_recent_memories() method
- [ ] Implement save_conversation_memory() method
- [ ] Write unit tests

### Phase 3: API Integration (Day 3)
- [ ] Modify chat_api.py to extract user_id from session
- [ ] Update _process_query_async to pass user_id
- [ ] Modify separated_states.py to add memory fields
- [ ] Test session flow with user_id

### Phase 4: Workflow Integration (Days 4-5)
- [ ] Update initialize_node to preserve user_id
- [ ] Add memory loading in planning_node
- [ ] Add memory saving in response_node
- [ ] Test end-to-end memory loading/saving
- [ ] Add progress_callback for memory_loaded event

### Phase 5: Frontend UI (Days 6-7)
- [ ] Create ConversationHistory component
- [ ] Create MemoryContextViewer component
- [ ] Update WebSocket handler for memory_loaded
- [ ] Update session start to pass user_id
- [ ] Add conversation history API endpoints
- [ ] Test UI with real conversations

### Phase 6: Testing (Day 8)
- [ ] Integration tests for memory loading
- [ ] Integration tests for memory saving
- [ ] Load testing with multiple users
- [ ] Test anonymous sessions (no user_id)
- [ ] Test memory count limits (3-5 conversations)

---

## 9. Critical Decisions

### Decision 1: user_id Type
- **Decision**: Change sessions.user_id from String to Integer
- **Rationale**: Consistency with User.id and ChatSession.user_id
- **Impact**: Requires database migration

### Decision 2: Memory Loading Location
- **Decision**: Load memories in planning_node, NOT initialize_node
- **Rationale**: Avoid unnecessary DB queries for IRRELEVANT queries
- **Impact**: Planning node becomes slightly more complex

### Decision 3: Memory Count
- **Decision**: Load 3-5 recent conversations (dynamic by intent)
- **Rationale**: Balance between context and performance
- **Impact**: Query performance depends on memory count

### Decision 4: Anonymous Sessions
- **Decision**: Support sessions without user_id
- **Rationale**: Allow anonymous usage without forcing login
- **Impact**: Memory loading is skipped when user_id is None

---

## 10. Next Steps

**Immediate Next Task**: Start Task 1 (Database Model Implementation)

**Specific Actions**:
1. Create `backend/app/models/memory.py`
2. Define ConversationMemory, UserPreference, EntityMemory models
3. Write migration script for sessions.user_id type change
4. Test migrations on development database

**Estimated Time**: 1 day (6-8 hours)

---

**Document End**
