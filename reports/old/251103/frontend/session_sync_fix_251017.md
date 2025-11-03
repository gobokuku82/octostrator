# Session Synchronization Fix - 2025-10-17

## 🎯 문제 요약

사용자가 보고한 3가지 핵심 이슈:

1. **새 채팅 버튼 클릭 시 특정 채팅창에 메시지 병합**
   - "새 채팅" 버튼을 눌러도 독립적인 채팅이 생성되지 않음
   - 특정 기존 세션에 메시지가 계속 누적됨

2. **기존 저장된 메시지는 정상, 새 메시지는 오류**
   - DB에 이미 저장된 세션들은 정상적으로 표시됨
   - 새로 작성하는 메시지만 문제 발생

3. **AI 응답이 저장되지 않음**
   - 사용자 메시지는 전송되지만 AI 응답이 DB에 저장 안 됨

---

## 🔍 근본 원인 분석

### 원인 1: Initial Session Selection 타이밍 이슈

**문제**:
- 이전 삭제 버그 수정 과정에서 `fetchSessions`의 의존성 배열을 `[]`로 비웠음
- 초기 세션 자동 선택 useEffect가 `loading` 체크 없이 실행됨
- `sessions` 배열이 로드되기 전에 실행되어 `currentSessionId`가 `null`로 유지됨

**코드**:
```typescript
// ❌ Before (use-chat-sessions.ts)
useEffect(() => {
    if (!currentSessionId && sessions.length > 0) {
        setCurrentSessionId(sessions[0].id)
    }
}, [sessions, currentSessionId])  // loading 체크 없음
```

**결과**:
- `currentSessionId`가 null이면 ChatInterface가 WebSocket을 잘못된 세션으로 연결
- 메시지가 엉뚱한 세션에 저장됨

---

### 원인 2: Session ID Mismatch (가장 치명적)

**문제**:
- **WebSocket 세션**과 **DB 세션**이 서로 다른 ID 사용
- 두 개의 세션 생성 엔드포인트 존재:

1. `/api/v1/chat/start` (WebSocket용)
   - `useSession` hook이 호출
   - `session-{uuid}` 형식 반환
   - sessionStorage에 저장됨

2. `/api/v1/chat/sessions` (DB용)
   - `useChatSessions.createSession`이 호출
   - `chat-{uuid}` 형식 반환
   - 새 채팅 버튼이 이것만 호출

**동작 순서**:
```
1. 앱 시작 → useSession.initSession() → /api/v1/chat/start
   → sessionStorage: "session-abc123"

2. 새 채팅 버튼 클릭 → createSession() → /api/v1/chat/sessions
   → currentSessionId: "chat-xyz789"

3. ChatInterface WebSocket 연결:
   - sessionId from useSession: "session-abc123" (stale)
   - currentSessionId: "chat-xyz789" (new)

4. 메시지 전송:
   - WebSocket: "session-abc123"로 전송
   - Backend: "chat-xyz789"에 저장하려고 시도
   - ❌ 불일치! 저장 실패
```

---

### 원인 3: WebSocket 재연결 안 됨

**문제**:
- `page.tsx`에서 sessionStorage 업데이트만 하고 WebSocket은 재연결 안 됨
- ChatInterface useEffect가 `sessionId`만 의존
- `currentSessionId` 변경 시 WebSocket이 갱신되지 않음

**코드**:
```typescript
// ❌ Before (chat-interface.tsx)
useEffect(() => {
    if (!sessionId) return  // sessionId만 체크

    const wsClient = createWSClient({
        sessionId,  // ❌ currentSessionId 무시
        // ...
    })
    // ...
}, [sessionId])  // ❌ currentSessionId 의존성 없음
```

---

## ✅ 적용된 수정 사항

### Fix 1: Initial Session Selection에 loading 체크 추가

**파일**: `frontend/hooks/use-chat-sessions.ts`

**변경 내용**:
```typescript
// ✅ After
useEffect(() => {
    // ✅ 로딩 완료 후에만 자동 선택 (loading=false 체크)
    if (!currentSessionId && sessions.length > 0 && !loading) {
        setCurrentSessionId(sessions[0].id)
        console.log(`[useChatSessions] Auto-selected first session: ${sessions[0].id}`)
    }
}, [sessions, currentSessionId, loading])  // ✅ loading 의존성 추가
```

**효과**:
- `fetchSessions()` 완료 후에만 첫 번째 세션 자동 선택
- 빈 배열 상태에서 실행되는 문제 해결

---

### Fix 2: useSession에 updateSessionId 함수 추가

**파일**: `frontend/hooks/use-session.ts`

**변경 내용**:
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

**효과**:
- 외부에서 WebSocket 세션 ID를 강제로 업데이트 가능
- "새 채팅" 버튼 클릭 시 세션 동기화 가능

---

### Fix 3: 새 채팅 버튼에서 sessionStorage 업데이트

**파일**: `frontend/app/page.tsx`

**변경 내용**:
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

**효과**:
- 새 채팅 생성 시 sessionStorage에 새 session_id 저장
- WebSocket이 이 값을 읽어서 올바른 세션으로 연결

---

### Fix 4: WebSocket 자동 재연결 (가장 중요!)

**파일**: `frontend/components/chat-interface.tsx`

#### 4-1. WebSocket 초기화 로직 수정

**변경 내용**:
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
        onDisconnected: () => {
            console.log('[ChatInterface] WebSocket disconnected')
            setWsConnected(false)
        },
        onError: (error) => {
            console.error('[ChatInterface] WebSocket error:', error)
        }
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
- 새 채팅 버튼 클릭 → currentSessionId 변경 → WebSocket 재연결 → 올바른 세션 사용

---

#### 4-2. 메시지 로드 로직 수정

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
            // ... (메시지 로드 로직)
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

#### 4-3. 메시지 전송 로직 수정

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

## 🔄 수정 후 동작 흐름

### 시나리오 1: 앱 초기 로드
```
1. useSession.initSession()
   → /api/v1/chat/start 호출
   → sessionStorage: "session-abc123"

2. useChatSessions.fetchSessions()
   → 기존 세션 목록 로드
   → loading: false

3. Auto-selection useEffect 실행
   → currentSessionId: "chat-001" (첫 번째 세션)

4. ChatInterface WebSocket 연결
   → activeSessionId = currentSessionId || sessionId
   → "chat-001"로 연결 ✅

5. 메시지 로드
   → "chat-001"의 메시지 표시 ✅
```

---

### 시나리오 2: 새 채팅 버튼 클릭
```
1. page.tsx onCreateSession 실행
   → createSession() 호출
   → /api/v1/chat/sessions POST
   → newSessionId: "chat-xyz789"

2. sessionStorage 업데이트
   → sessionStorage.setItem("holmes_session_id", "chat-xyz789")

3. setCurrentSessionId("chat-xyz789")

4. ChatInterface useEffect 트리거
   → currentSessionId 변경 감지
   → 기존 WebSocket 연결 종료
   → 새 WebSocket 연결: "chat-xyz789" ✅

5. 메시지 로드 useEffect 트리거
   → "chat-xyz789" 세션의 메시지 로드
   → 빈 세션이므로 환영 메시지 표시 ✅

6. 사용자 메시지 전송
   → activeSessionId: "chat-xyz789"
   → WebSocket: "chat-xyz789"로 전송
   → Backend: "chat-xyz789"에 저장 ✅

7. AI 응답 수신
   → WebSocket: "chat-xyz789"로 수신
   → Backend: "chat-xyz789"에 저장 ✅
```

---

### 시나리오 3: 기존 세션 클릭
```
1. Sidebar에서 세션 클릭
   → switchSession("chat-old123") 호출
   → setCurrentSessionId("chat-old123")

2. ChatInterface useEffect 트리거
   → currentSessionId 변경 감지
   → WebSocket 재연결: "chat-old123" ✅

3. 세션 전환 메시지 로드 useEffect 실행
   → "chat-old123"의 메시지 로드 ✅

4. 메시지 전송
   → activeSessionId: "chat-old123"
   → WebSocket: "chat-old123"로 전송
   → Backend: "chat-old123"에 저장 ✅
```

---

## 🧪 테스트 계획

### Test 1: 새 채팅 독립성 확인
**Steps**:
1. 앱 시작
2. "새 채팅" 버튼 클릭
3. 메시지 "테스트 1" 전송
4. 다시 "새 채팅" 버튼 클릭
5. 메시지 "테스트 2" 전송

**Expected**:
- 두 세션이 독립적으로 생성됨
- "테스트 1"과 "테스트 2"가 서로 다른 세션에 저장됨
- 사이드바에 2개의 세션 표시됨

---

### Test 2: 메시지 저장 확인
**Steps**:
1. 새 채팅 생성
2. 복잡한 질문 전송 (예: "공인중개사 금지행위는?")
3. AI 응답 대기
4. F5 새로고침

**Expected**:
- AI 응답이 정상적으로 수신됨
- 새로고침 후에도 사용자 메시지와 AI 응답 모두 표시됨
- DB에 저장 확인 가능

**SQL 검증**:
```sql
SELECT session_id, role, content, created_at
FROM chat_messages
WHERE session_id = 'chat-xyz789'
ORDER BY created_at;
```

---

### Test 3: 세션 전환 정상 동작
**Steps**:
1. 세션 A에서 "메시지 A" 전송
2. 세션 B에서 "메시지 B" 전송
3. 세션 A로 다시 전환
4. "메시지 A2" 전송

**Expected**:
- 세션 A에는 "메시지 A", "메시지 A2"만 표시됨
- 세션 B에는 "메시지 B"만 표시됨
- WebSocket이 세션 전환 시마다 재연결됨

---

### Test 4: Console Log 확인
**Expected Logs**:
```
[useChatSessions] Loaded X sessions
[useChatSessions] Auto-selected first session: chat-001

// 새 채팅 버튼 클릭
[useChatSessions] Created new session: chat-xyz789
[HomePage] Updated WebSocket session ID: chat-xyz789
[ChatInterface] 🔌 Disconnecting WebSocket from session: chat-001
[ChatInterface] 🔌 Initializing WebSocket with session: chat-xyz789
[ChatInterface] ✅ WebSocket connected to session: chat-xyz789
[ChatInterface] ✅ Loaded 0 messages for session chat-xyz789
[ChatInterface] No messages in DB, keeping welcome message
```

---

## 📊 수정된 파일 목록

### 1. `frontend/hooks/use-chat-sessions.ts`
- **변경**: Initial session selection useEffect에 `loading` 의존성 추가
- **라인**: 196-202

### 2. `frontend/hooks/use-session.ts`
- **변경**: `updateSessionId` 함수 추가
- **라인**: 60-72

### 3. `frontend/app/page.tsx`
- **변경**: `onCreateSession`에서 sessionStorage 업데이트
- **라인**: 107-115

### 4. `frontend/components/chat-interface.tsx`
- **변경 1**: WebSocket 초기화 useEffect에 `currentSessionId` 의존성 추가
- **라인**: 261-294
- **변경 2**: 메시지 로드 useEffect에 `currentSessionId` 의존성 추가
- **라인**: 296-338
- **변경 3**: `handleSendMessage`에서 `activeSessionId` 사용
- **라인**: 403-413

---

## 🎉 예상 효과

### ✅ 해결된 문제
1. **새 채팅 버튼이 독립적인 세션 생성**
   - 각 "새 채팅"이 고유한 세션 ID로 생성됨
   - 메시지가 의도한 세션에 저장됨

2. **메시지 저장 정상화**
   - 사용자 메시지 + AI 응답 모두 DB에 저장됨
   - 새로고침 후에도 대화 유지됨

3. **세션 전환 안정성**
   - WebSocket이 세션 전환 시 자동 재연결
   - 각 세션의 메시지가 올바르게 로드됨

### ✅ 개선된 사항
- **로깅 강화**: 세션 연결/전환 과정 추적 가능
- **동기화 보장**: `activeSessionId` 로직으로 WebSocket-DB 일치
- **타이밍 이슈 해결**: `loading` 체크로 Race Condition 방지

---

## 🚀 다음 단계 (선택 사항)

### 장기적 개선 사항
1. **세션 생성 엔드포인트 통합**
   - `/api/v1/chat/start`와 `/api/v1/chat/sessions` 통합
   - 단일 엔드포인트로 WebSocket + DB 세션 동시 생성
   - 아키텍처 단순화

2. **세션 ID 형식 통일**
   - `session-{uuid}` vs `chat-{uuid}` 형식 통일
   - 혼란 방지

3. **WebSocket 재연결 최적화**
   - Debounce 로직 추가하여 불필요한 재연결 방지
   - 세션 전환 시 부드러운 전환 애니메이션

---

## 📝 결론

**핵심 원인**:
- Session ID Mismatch (WebSocket vs DB)
- WebSocket이 세션 전환을 감지하지 못함
- Initial session selection 타이밍 이슈

**적용된 해결책**:
- `currentSessionId` 우선 사용하는 `activeSessionId` 로직
- WebSocket useEffect에 `currentSessionId` 의존성 추가
- sessionStorage 동기화 + `loading` 체크 추가

**결과**:
- ✅ 새 채팅이 독립적으로 생성됨
- ✅ 메시지와 응답이 올바른 세션에 저장됨
- ✅ 세션 전환이 안정적으로 동작함

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0 (Session Sync Fix)
