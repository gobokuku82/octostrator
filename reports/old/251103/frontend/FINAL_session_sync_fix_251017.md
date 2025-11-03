# 🔧 Session Synchronization Fix - Final Report (2025-10-17)

## 📌 Executive Summary

사용자가 보고한 **세션 관리 버그**의 근본 원인을 파악하고 수정 완료:

### 🚨 발견된 Critical Bug
**Session ID 형식 불일치** - 두 개의 세션 생성 엔드포인트가 서로 다른 형식 사용:
- `/api/v1/chat/start` → `session-{uuid}` ✅ (표준)
- `/api/v1/chat/sessions` → `chat-{uuid}` ❌ (비표준)

이로 인해:
1. 새 채팅 버튼 클릭 시 `chat-{uuid}` 생성
2. WebSocket은 `session-{uuid}` 사용
3. 메시지가 잘못된 세션에 저장되거나 저장 실패
4. AI 응답이 저장되지 않음

---

## 🔍 Root Cause Analysis

### 1. Schema 표준 확인

**DB Schema** (`complete_schema_251016.dbml`):
```dbml
Table chat_sessions {
  session_id varchar(100) [pk, note: 'Session ID (WebSocket 연결 식별자)']
  ...
  Note: '''
  session_id: Backend가 생성 ("session-{uuid}" 형식)  ← 표준!
  '''
}
```

**통합 세션 ID 개념**:
```
모든 테이블이 동일한 session_id 사용:
- chat_sessions.session_id      = "session-{uuid}"
- chat_messages.session_id       = "session-{uuid}"
- checkpoints.session_id         = "session-{uuid}"
- checkpoint_blobs.session_id    = "session-{uuid}"
- checkpoint_writes.session_id   = "session-{uuid}"
```

### 2. Backend 코드 분석

#### ✅ 정상: `/api/v1/chat/start` 엔드포인트
**파일**: `backend/app/api/postgres_session_manager.py:52`
```python
session_id = f"session-{uuid.uuid4()}"  # ✅ 표준 형식
```

#### ❌ 문제: `/api/v1/chat/sessions` 엔드포인트
**파일**: `backend/app/api/chat_api.py:300` (수정 전)
```python
session_id = f"chat-{uuid.uuid4()}"  # ❌ 비표준 형식!
```

### 3. Frontend 동작 흐름 (버그 발생 시나리오)

```
1. 앱 시작
   → useSession.initSession()
   → /api/v1/chat/start 호출
   → sessionStorage: "session-abc123" ✅

2. "새 채팅" 버튼 클릭
   → useChatSessions.createSession()
   → /api/v1/chat/sessions POST
   → currentSessionId: "chat-xyz789" ❌

3. ChatInterface WebSocket 연결
   → currentSessionId가 우선이므로 "chat-xyz789"로 연결 시도
   → WebSocket validation 실패 (DB에 없는 session_id)
   → 또는 fallback으로 "session-abc123" 사용
   → 메시지가 엉뚱한 세션에 저장 ❌

4. 메시지 전송
   → WebSocket: "session-abc123"로 전송
   → Backend: "chat-xyz789"에 저장 시도
   → session_id 불일치로 저장 실패 ❌
```

---

## ✅ Applied Fixes

### Fix 1: 세션 ID 형식 통일 (CRITICAL)

**파일**: `backend/app/api/chat_api.py:300`

**변경 전**:
```python
session_id = f"chat-{uuid.uuid4()}"  # ❌
```

**변경 후**:
```python
session_id = f"session-{uuid.uuid4()}"  # ✅ 스키마 표준 형식으로 수정
```

**효과**:
- 두 엔드포인트 모두 `session-{uuid}` 형식 사용
- WebSocket과 DB가 동일한 session_id 사용
- 메시지 저장 정상화

---

### Fix 2: Initial Session Selection 타이밍 수정

**파일**: `frontend/hooks/use-chat-sessions.ts:196-202`

**변경 전**:
```typescript
useEffect(() => {
    if (!currentSessionId && sessions.length > 0) {
        setCurrentSessionId(sessions[0].id)
    }
}, [sessions, currentSessionId])  // loading 체크 없음
```

**변경 후**:
```typescript
useEffect(() => {
    // ✅ 로딩 완료 후에만 자동 선택
    if (!currentSessionId && sessions.length > 0 && !loading) {
        setCurrentSessionId(sessions[0].id)
        console.log(`[useChatSessions] Auto-selected first session: ${sessions[0].id}`)
    }
}, [sessions, currentSessionId, loading])  // ✅ loading 의존성 추가
```

**효과**:
- `fetchSessions()` 완료 후에만 첫 번째 세션 자동 선택
- Race condition 해결

---

### Fix 3: WebSocket 세션 전환 자동 재연결

**파일**: `frontend/components/chat-interface.tsx:261-294`

**변경 전**:
```typescript
useEffect(() => {
    if (!sessionId) return

    const wsClient = createWSClient({
        sessionId,  // ❌ currentSessionId 무시
        // ...
    })
    // ...
}, [sessionId])  // ❌ currentSessionId 의존성 없음
```

**변경 후**:
```typescript
// WebSocket 초기화 및 세션 전환 시 재연결
useEffect(() => {
    // ✅ currentSessionId 우선 사용 (새 채팅 버튼으로 생성된 세션)
    const activeSessionId = currentSessionId || sessionId
    if (!activeSessionId) return

    console.log('[ChatInterface] 🔌 Initializing WebSocket with session:', activeSessionId)

    const wsClient = createWSClient({
        baseUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
        sessionId: activeSessionId,  // ✅ currentSessionId 또는 sessionId 사용
        onMessage: handleWSMessage,
        onConnected: () => {
            console.log('[ChatInterface] ✅ WebSocket connected to session:', activeSessionId)
            setWsConnected(true)
        },
        // ...
    })

    wsClient.connect()
    wsClientRef.current = wsClient

    return () => {
        console.log('[ChatInterface] 🔌 Disconnecting WebSocket from session:', activeSessionId)
        wsClient.disconnect()
        wsClientRef.current = null
    }
}, [currentSessionId, sessionId, handleWSMessage])  // ✅ currentSessionId 추가
```

**효과**:
- `currentSessionId` 변경 시 WebSocket 자동 재연결
- 새 채팅 생성 시 올바른 세션으로 연결
- 세션 전환 시 안정적 재연결

---

### Fix 4: 메시지 로드 로직 수정

**파일**: `frontend/components/chat-interface.tsx:296-338`

**변경 내용**:
```typescript
// DB에서 메시지 로드 (WebSocket 연결 후) - 초기 로드용
useEffect(() => {
    // ✅ currentSessionId 우선 사용
    const activeSessionId = currentSessionId || sessionId
    if (!activeSessionId || !wsConnected) return

    const loadMessagesFromDB = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
            const response = await fetch(
                `${apiUrl}/api/v1/chat/sessions/${activeSessionId}/messages?limit=100`
            )
            // ... (메시지 로드)
            console.log(`[ChatInterface] ✅ Loaded messages for session ${activeSessionId}`)
        } catch (error) {
            console.error('[ChatInterface] Failed to load messages from DB:', error)
        }
    }

    loadMessagesFromDB()
}, [currentSessionId, sessionId, wsConnected])  // ✅ currentSessionId 추가
```

**효과**:
- 새 세션으로 전환 시 해당 세션의 메시지 자동 로드
- 빈 세션이면 환영 메시지 표시

---

### Fix 5: 메시지 전송 로직 수정

**파일**: `frontend/components/chat-interface.tsx:403-413`

**변경 내용**:
```typescript
const handleSendMessage = async (content: string) => {
    // ✅ currentSessionId 우선 사용
    const activeSessionId = currentSessionId || sessionId
    if (!content.trim() || !activeSessionId || !wsClientRef.current) return

    const userMessage: Message = {
        id: Date.now().toString(),
        type: "user",
        content,
        timestamp: new Date(),
    }
    // ... (메시지 전송)
}
```

**효과**:
- 메시지 전송 시 올바른 세션 ID 사용
- WebSocket과 DB가 동일한 세션에 메시지 저장

---

### Fix 6: 불필요한 코드 제거

#### 6-1. page.tsx sessionStorage 업데이트 제거

**파일**: `frontend/app/page.tsx:107`

**변경 전**:
```typescript
onCreateSession={async () => {
    const newSessionId = await createSession()
    if (newSessionId) {
        // ✅ WebSocket session_id 업데이트 (sessionStorage)
        sessionStorage.setItem("holmes_session_id", newSessionId)
        console.log(`[HomePage] Updated WebSocket session ID: ${newSessionId}`)
    }
    return newSessionId
}}
```

**변경 후**:
```typescript
onCreateSession={createSession}
```

**이유**:
- 두 엔드포인트 모두 `session-{uuid}` 형식 사용
- `currentSessionId`가 이미 올바른 값을 받음
- sessionStorage 업데이트 불필요

#### 6-2. useSession updateSessionId 함수 제거

**파일**: `frontend/hooks/use-session.ts:59-71`

**변경 전**:
```typescript
// ✅ 외부에서 세션 ID 업데이트 가능 (새 채팅 버튼용)
const updateSessionId = (newSessionId: string) => {
    setSessionId(newSessionId)
    sessionStorage.setItem(SESSION_STORAGE_KEY, newSessionId)
    console.log(`[useSession] Updated session ID: ${newSessionId}`)
}

return {
    sessionId,
    isLoading,
    error,
    resetSession,
    updateSessionId,  // ✅ 추가
}
```

**변경 후**:
```typescript
return {
    sessionId,
    isLoading,
    error,
    resetSession,
}
```

**이유**:
- 세션 ID 형식 통일로 더 이상 필요 없음
- ChatInterface가 `currentSessionId`로 자동 전환

---

## 🎯 Final Architecture

### Session ID Flow (수정 후)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 앱 시작                                                   │
│    → useSession.initSession()                               │
│    → /api/v1/chat/start                                     │
│    → sessionStorage: "session-abc123" ✅                    │
│    → DB chat_sessions: "session-abc123" ✅                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. "새 채팅" 버튼 클릭                                        │
│    → useChatSessions.createSession()                        │
│    → /api/v1/chat/sessions POST                             │
│    → currentSessionId: "session-xyz789" ✅                  │
│    → DB chat_sessions: "session-xyz789" ✅                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 3. ChatInterface WebSocket 연결                             │
│    → activeSessionId = currentSessionId || sessionId        │
│    → activeSessionId: "session-xyz789" ✅                   │
│    → WebSocket 연결: "session-xyz789" ✅                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 4. 메시지 전송                                               │
│    → WebSocket: "session-xyz789"로 전송 ✅                  │
│    → Backend: "session-xyz789"에 저장 ✅                    │
│    → AI 응답: "session-xyz789"에 저장 ✅                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 5. F5 새로고침                                               │
│    → useChatSessions.fetchSessions()                        │
│    → 세션 목록 로드 (session-xyz789 포함) ✅                │
│    → Auto-selection: currentSessionId = "session-xyz789" ✅ │
│    → 메시지 로드: session-xyz789의 메시지 표시 ✅           │
└─────────────────────────────────────────────────────────────┘
```

### activeSessionId Pattern

모든 WebSocket 및 DB 연결에 `activeSessionId` 사용:

```typescript
const activeSessionId = currentSessionId || sessionId

// WebSocket 연결
sessionId: activeSessionId

// 메시지 로드
`/api/v1/chat/sessions/${activeSessionId}/messages`

// 메시지 전송
if (!activeSessionId || !wsClientRef.current) return
```

**장점**:
1. `currentSessionId` 우선 (새 채팅, 세션 전환)
2. Fallback: `sessionId` (초기 로드)
3. 단일 진실 공급원 (Single Source of Truth)

---

## 📊 수정된 파일 목록

### Backend (1개 파일)

1. **`backend/app/api/chat_api.py`** (Line 300)
   - ❌ `session_id = f"chat-{uuid.uuid4()}"`
   - ✅ `session_id = f"session-{uuid.uuid4()}"`

### Frontend (4개 파일)

1. **`frontend/hooks/use-chat-sessions.ts`** (Line 196-202)
   - ✅ `loading` 의존성 추가
   - Initial session selection 타이밍 수정

2. **`frontend/hooks/use-session.ts`** (Line 59-71)
   - ❌ `updateSessionId` 함수 제거 (불필요)

3. **`frontend/app/page.tsx`** (Line 107)
   - ❌ sessionStorage 업데이트 코드 제거 (불필요)

4. **`frontend/components/chat-interface.tsx`** (3곳 수정)
   - Line 261-294: WebSocket useEffect에 `currentSessionId` 의존성 추가
   - Line 296-338: 메시지 로드 useEffect에 `activeSessionId` 적용
   - Line 403-413: `handleSendMessage`에 `activeSessionId` 적용

---

## 🧪 테스트 시나리오

### Test 1: 새 채팅 독립성 확인 ✅

**Steps**:
1. 앱 시작
2. "새 채팅" 버튼 클릭
3. 메시지 "테스트 1" 전송
4. 다시 "새 채팅" 버튼 클릭
5. 메시지 "테스트 2" 전송

**Expected**:
- 두 세션 모두 `session-{uuid}` 형식 ✅
- "테스트 1"과 "테스트 2"가 서로 다른 세션에 저장됨 ✅
- 사이드바에 2개의 세션 표시됨 ✅

**DB 검증**:
```sql
SELECT session_id, title, message_count
FROM chat_sessions
WHERE user_id = 1
ORDER BY updated_at DESC;

-- Expected:
-- session-xyz789 | 테스트 2 | 2
-- session-abc123 | 테스트 1 | 2
```

---

### Test 2: 메시지 저장 확인 ✅

**Steps**:
1. 새 채팅 생성
2. 복잡한 질문 전송 (예: "공인중개사 금지행위는?")
3. AI 응답 대기
4. F5 새로고침

**Expected**:
- AI 응답이 정상적으로 수신됨 ✅
- 새로고침 후에도 사용자 메시지와 AI 응답 모두 표시됨 ✅

**DB 검증**:
```sql
SELECT session_id, role, content, created_at
FROM chat_messages
WHERE session_id = 'session-xyz789'
ORDER BY created_at;

-- Expected:
-- session-xyz789 | user      | 공인중개사 금지행위는? | 2025-10-17 10:00:00
-- session-xyz789 | assistant | [AI 응답]             | 2025-10-17 10:00:05
```

---

### Test 3: 세션 전환 정상 동작 ✅

**Steps**:
1. 세션 A에서 "메시지 A" 전송
2. 세션 B에서 "메시지 B" 전송
3. 세션 A로 다시 전환
4. "메시지 A2" 전송

**Expected**:
- 세션 A에는 "메시지 A", "메시지 A2"만 표시됨 ✅
- 세션 B에는 "메시지 B"만 표시됨 ✅
- WebSocket이 세션 전환 시마다 재연결됨 ✅

**Console Logs**:
```
[ChatInterface] 🔌 Disconnecting WebSocket from session: session-abc123
[ChatInterface] 🔌 Initializing WebSocket with session: session-xyz789
[ChatInterface] ✅ WebSocket connected to session: session-xyz789
[ChatInterface] ✅ Loaded 1 messages for session session-xyz789
```

---

### Test 4: Console Log 확인 ✅

**새 채팅 버튼 클릭 시 Expected Logs**:
```
[useChatSessions] Creating new session...
[useChatSessions] Created new session: session-xyz789
[useChatSessions] Setting current session: session-xyz789
[ChatInterface] 🔌 Disconnecting WebSocket from session: session-abc123
[ChatInterface] 🔌 Initializing WebSocket with session: session-xyz789
[ChatInterface] ✅ WebSocket connected to session: session-xyz789
[ChatInterface] ✅ Loaded 0 messages for session session-xyz789
[ChatInterface] No messages in DB, keeping welcome message
```

---

## 🎉 수정 결과

### ✅ 해결된 문제

1. **새 채팅 버튼이 독립적인 세션 생성**
   - 각 "새 채팅"이 고유한 `session-{uuid}` 생성
   - 메시지가 의도한 세션에 저장됨

2. **메시지 저장 정상화**
   - 사용자 메시지 + AI 응답 모두 DB에 저장됨
   - 새로고침 후에도 대화 유지됨
   - `structured_data`도 정상 저장 (답변 UI 표시용)

3. **세션 전환 안정성**
   - WebSocket이 세션 전환 시 자동 재연결
   - 각 세션의 메시지가 올바르게 로드됨
   - `activeSessionId` 패턴으로 단일 진실 공급원 보장

### ✅ 개선된 사항

- **세션 ID 형식 통일**: `session-{uuid}` 표준화
- **로깅 강화**: 세션 연결/전환 과정 추적 가능
- **동기화 보장**: `activeSessionId` 로직으로 WebSocket-DB 일치
- **타이밍 이슈 해결**: `loading` 체크로 Race Condition 방지
- **코드 단순화**: 불필요한 sessionStorage 업데이트 제거

---

## 🚀 다음 단계 (권장 사항)

### 1. 장기적 아키텍처 개선

#### Option 1: 세션 생성 엔드포인트 통합
현재:
- `/api/v1/chat/start` - WebSocket용 세션 생성
- `/api/v1/chat/sessions` - DB 세션 생성 (Chat History용)

제안:
```python
@router.post("/sessions")
async def create_unified_session(
    request: ChatSessionCreate,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """
    통합 세션 생성 (WebSocket + DB)

    Returns:
        - session_id: "session-{uuid}"
        - WebSocket 연결 가능
        - chat_sessions 테이블에 저장됨
    """
    session_id, expires_at = await session_mgr.create_session(
        user_id=request.user_id or 1,
        metadata=request.metadata
    )

    return {
        "id": session_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at.isoformat()
    }
```

장점:
- 단일 엔드포인트로 모든 세션 생성
- `/start` 엔드포인트 제거 가능
- Frontend 코드 단순화

#### Option 2: Frontend 세션 관리 단순화
현재:
- `useSession` (WebSocket 세션)
- `useChatSessions` (Chat History 세션)

제안:
```typescript
// 단일 hook으로 통합
export function useUnifiedSession() {
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [sessions, setSessions] = useState<ChatSessionType[]>([])

    // 세션 생성 (WebSocket + DB 동시)
    const createSession = async () => {
        const response = await fetch('/api/v1/chat/sessions', { method: 'POST' })
        const data = await response.json()
        setSessionId(data.id)
        return data.id
    }

    // ...
}
```

### 2. 모니터링 및 디버깅 강화

#### Session Health Check Endpoint
```python
@router.get("/sessions/{session_id}/health")
async def check_session_health(session_id: str, db: AsyncSession = Depends(get_async_db)):
    """
    세션 상태 진단

    Returns:
        - session_exists: chat_sessions 테이블 존재 여부
        - message_count: 메시지 개수
        - checkpoint_count: 체크포인트 개수
        - websocket_active: WebSocket 연결 상태
    """
    # ...
```

#### Frontend Debug Panel
```typescript
// 개발 모드에서 세션 상태 표시
<DebugPanel>
    <div>Session ID: {activeSessionId}</div>
    <div>WebSocket: {wsConnected ? '✅' : '❌'}</div>
    <div>Messages: {messages.length}</div>
    <div>Current Session: {currentSessionId}</div>
    <div>Fallback Session: {sessionId}</div>
</DebugPanel>
```

### 3. 성능 최적화

#### WebSocket 재연결 Debounce
```typescript
// 빠른 세션 전환 시 불필요한 재연결 방지
const debouncedReconnect = useMemo(
    () => debounce((sessionId: string) => {
        // WebSocket 재연결 로직
    }, 300),
    []
)
```

#### 세션 전환 애니메이션
```typescript
// 세션 전환 시 부드러운 전환
const [isTransitioning, setIsTransitioning] = useState(false)

const switchSession = async (sessionId: string) => {
    setIsTransitioning(true)
    await new Promise(resolve => setTimeout(resolve, 200))  // Fade out
    setCurrentSessionId(sessionId)
    await new Promise(resolve => setTimeout(resolve, 200))  // Fade in
    setIsTransitioning(false)
}
```

---

## 📝 결론

### 핵심 원인
**Session ID 형식 불일치** (`chat-{uuid}` vs `session-{uuid}`)로 인한 WebSocket-DB 동기화 실패

### 적용된 해결책
1. ✅ Backend 세션 ID 형식 통일 (`session-{uuid}`)
2. ✅ Frontend `activeSessionId` 패턴 도입
3. ✅ WebSocket 자동 재연결 로직 추가
4. ✅ Initial session selection 타이밍 수정
5. ✅ 불필요한 sessionStorage 동기화 코드 제거

### 최종 결과
- ✅ 새 채팅이 독립적으로 생성됨
- ✅ 메시지와 응답이 올바른 세션에 저장됨
- ✅ 세션 전환이 안정적으로 동작함
- ✅ 스키마 표준 준수 (`session-{uuid}`)

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 2.0 (Final - Schema Fix Included)
**관련 이슈**: 새 채팅 병합 문제, 메시지 저장 실패, AI 응답 누락
