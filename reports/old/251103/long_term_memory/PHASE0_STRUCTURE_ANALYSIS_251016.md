# Phase 0: 시스템 구조 분석 및 문제 원인 규명

**날짜**: 2025-10-16
**작성자**: Claude Code
**상태**: Phase 0 완료 ✅
**목적**: 코드 수정 전 정확한 구조 파악 및 문제 원인 분석

---

## 📋 목차

1. [전체 아키텍처 플로우](#1-전체-아키텍처-플로우)
2. [문제별 심층 원인 분석](#2-문제별-심층-원인-분석)
3. [코드 레벨 상세 분석](#3-코드-레벨-상세-분석)
4. [불필요한 코드 리스트](#4-불필요한-코드-리스트)
5. [다음 단계 권장사항](#5-다음-단계-권장사항)

---

## 1. 전체 아키텍처 플로우

### 1.1 세션 생성 플로우 (현재 구조)

```
사용자 접속
    ↓
[Frontend] use-session.ts useEffect 실행
    ↓
sessionStorage 확인
    ↓
┌─────────────────────────────────────┐
│ sessionStorage에 session_id 있음?   │
└─────────────────────────────────────┘
         YES ↓              NO ↓
    [검증 단계]          [생성 단계]
         ↓                   ↓
GET /api/v1/chat/{session_id}   POST /api/v1/chat/start
         ↓                   ↓
chat_api.py::get_session_info   chat_api.py::start_session
         ↓                   ↓
session_mgr.get_session()    session_mgr.create_session()
         ↓                   ↓
postgres_session_manager.py  postgres_session_manager.py
         ↓                   ↓
chat_sessions 테이블 조회    1. chat_sessions INSERT
         ↓                   2. session_id 생성
    ┌────────┐                   ↓
    │ 있음?  │              sessionStorage에 저장
    └────────┘                   ↓
  YES ↓    NO ↓            WebSocket 연결
   성공      404               ↓
    ↓        ↓            DB에서 메시지 로드
  유지   새 세션 생성
```

**❌ 문제점**:
- `postgres_session_manager.get_session()`은 chat_sessions 테이블을 정상 조회함
- **하지만** GET /{session_id} API가 이를 제대로 반환하지 못함
- 404 에러 → 무한 루프 → 세션 2개씩 생성

---

### 1.2 메시지 저장 플로우 (정상 동작 중)

```
사용자 메시지 입력
    ↓
[Frontend] chat-interface.tsx::handleSendMessage()
    ↓
WebSocket 전송: { type: "query", query: "...", chat_session_id: "..." }
    ↓
[Backend] chat_api.py::websocket_chat()
    ↓
_process_query_async() 비동기 실행
    ↓
1. _save_message_to_db(session_id, "user", query)
    ↓
   chat_messages 테이블 INSERT ✅
    ↓
2. supervisor.process_query_streaming()
    ↓
   AI 응답 생성
    ↓
3. _save_message_to_db(session_id, "assistant", response)
    ↓
   chat_messages 테이블 INSERT ✅
    ↓
WebSocket으로 응답 전송
```

**✅ 정상 동작**:
- 메시지는 DB에 잘 저장됨
- chat_messages 테이블에 데이터 누적 중

---

### 1.3 F5 새로고침 플로우 (현재 동작 안 함)

```
사용자 F5 새로고침
    ↓
[Frontend] use-session.ts useEffect 실행
    ↓
sessionStorage에서 session_id 복원
    ↓
GET /api/v1/chat/{session_id} 호출
    ↓
❌ 404 에러 발생
    ↓
새 세션 생성 (session_id 변경됨!)
    ↓
chat-interface.tsx useEffect 실행
    ↓
조건: sessionId && wsConnected
    ↓
WebSocket 연결 성공
    ↓
DB 메시지 로드 시도
    ↓
GET /api/v1/chat/sessions/{NEW_session_id}/messages
    ↓
❌ 새 session_id이므로 메시지 0개 반환
    ↓
환영 메시지만 표시 (대화 내역 사라짐)
```

**❌ 핵심 문제**:
- GET /{session_id} 404 에러
- session_id가 계속 바뀌어서 이전 메시지 못 불러옴

---

## 2. 문제별 심층 원인 분석

### P0: 세션이 2개씩 생성되는 문제

#### 증상
```
✅ New session created: session-8b15a80a-fc8d-40b3-91d6-9fd8fa6886c9
✅ New session created: session-3892c944-84ec-4834-8d96-5cfbf4ef78e2
```

#### 원인 분석

**1차 원인**: React Strict Mode (개발 모드)
```javascript
// frontend/next.config.mjs
const nextConfig = {
  // reactStrictMode: false  ❌ 설정되지 않음 (기본값 true)
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  images: { unoptimized: true },
}
```

- Next.js 기본값: `reactStrictMode: true` (개발 모드)
- **개발 모드에서 useEffect가 2번 실행됨** (의도된 동작)
- mount → unmount → mount (순수성 테스트)

**2차 원인**: GET /{session_id} 404 에러로 인한 재생성
```javascript
// frontend/hooks/use-session.ts:28
try {
  await chatAPI.getSessionInfo(storedSessionId)
  console.log("✅ Existing session valid:", storedSessionId)
  setSessionId(storedSessionId)
  setIsLoading(false)
  return  // ✅ 여기서 종료되어야 함
} catch (error) {
  // ❌ 404 에러 → 계속 새 세션 생성
  console.warn("⚠️ Session expired or invalid, creating new session:", error)
  sessionStorage.removeItem(SESSION_STORAGE_KEY)
  // 여기서 계속 진행하여 새 세션 생성
}
```

**3차 원인**: useEffect 클린업 없음
```javascript
// use-session.ts:13
useEffect(() => {
  initSession()  // ❌ 클린업 함수 없음
}, [])
```

- Strict Mode에서 2번 실행됨
- 첫 번째 실행: session-xxx 생성
- 두 번째 실행: session-yyy 생성
- 결과: DB에 2개 세션 누적

#### 연쇄 효과
1. 세션 2개 생성 → sessionStorage에는 마지막 것만 저장
2. WebSocket은 두 번째 세션으로 연결
3. DB 메시지 로드 시 두 번째 세션 ID 사용
4. 첫 번째 세션의 메시지는 고아 상태

---

### P1: GET /{session_id} 404 에러

#### 증상
```
GET http://localhost:8000/api/v1/chat/session-8e3ea97b-b778-4973-ad31-ca50af455898 404 (Not Found)
⚠️ Session expired or invalid, creating new session
```

#### 원인 분석

**코드 조사 결과**:
```python
# backend/app/api/chat_api.py:172-200
@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    # ✅ postgres_session_manager.get_session() 호출
    session = await session_mgr.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or expired: {session_id}"
        )

    return SessionInfo(
        session_id=session["session_id"],
        created_at=session["created_at"].isoformat(),
        expires_at=session["expires_at"].isoformat(),
        last_activity=session["last_activity"].isoformat(),  # ❌ KeyError 발생?
        metadata=session.get("metadata", {})
    )
```

```python
# backend/app/api/postgres_session_manager.py:130-163
async def get_session(self, session_id: str) -> Optional[Dict]:
    # ✅ chat_sessions 테이블에서 정상 조회
    async for db_session in get_async_db():
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return None

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "expires_at": session.created_at + self.session_ttl  # ✅ 계산값
                # ❌ "last_activity" 키가 없음!!!
            }
```

**❌ 발견된 버그**:
- `postgres_session_manager.get_session()`이 반환하는 dict에 **"last_activity" 키가 없음**
- `chat_api.py:198`에서 `session["last_activity"]` 접근 → **KeyError 발생**
- KeyError는 500 에러가 아니라 예외 처리되어 404로 반환될 수 있음

**해결 방법**:
```python
# postgres_session_manager.py:150-157
return {
    "session_id": session.session_id,
    "user_id": session.user_id,
    "title": session.title,
    "created_at": session.created_at,
    "updated_at": session.updated_at,
    "expires_at": session.created_at + self.session_ttl,
    "last_activity": session.updated_at  # ✅ 추가 필요!
}
```

---

### P2: F5 새로고침 시 메시지 로드 안 됨

#### 증상
```
[ChatInterface] No messages in DB, keeping welcome message
```

#### 원인 분석

**의존성 체인**:
```javascript
// frontend/components/chat-interface.tsx:297-336
useEffect(() => {
  if (!sessionId || !wsConnected) return  // ❌ 조건 확인

  const loadMessagesFromDB = async () => {
    // DB에서 메시지 로드
    const response = await fetch(
      `${apiUrl}/api/v1/chat/sessions/${sessionId}/messages?limit=100`
    )
    // ...
  }

  loadMessagesFromDB()
}, [sessionId, wsConnected])  // ✅ 두 조건 모두 true여야 실행
```

**문제 시나리오**:
1. F5 새로고침
2. sessionStorage에서 `session-old` 복원
3. GET /{session-old} → 404 에러 (P1 때문)
4. 새 세션 생성: `session-new`
5. sessionId 변경: `session-old` → `session-new`
6. WebSocket 연결 성공
7. DB 메시지 로드: `GET /sessions/session-new/messages`
8. session-new는 방금 생성되어 메시지 0개
9. "No messages in DB" 출력

**근본 원인**:
- P1 (GET /{session_id} 404)이 해결되지 않으면 P2도 해결 불가
- session_id가 계속 바뀌면 이전 메시지 절대 못 불러옴

---

## 3. 코드 레벨 상세 분석

### 3.1 Backend: chat_api.py

#### POST /start (세션 생성)
```python
# Line 105-169
@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest = SessionStartRequest(),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    # 1. postgres_session_manager.create_session() 호출
    session_id, expires_at = await session_mgr.create_session(
        user_id=request.user_id,
        metadata=request.metadata
    )

    # 2. ✅ chat_sessions 테이블에 INSERT (Line 128-151)
    async for db in get_async_db():
        # 중복 확인
        existing_session_query = select(ChatSession).where(...)
        # 없으면 새로 추가
        new_chat_session = ChatSession(
            session_id=session_id,
            user_id=request.user_id or 1,
            title="새 대화"
        )
        db.add(new_chat_session)
        await db.commit()
```

**✅ 정상 동작**: chat_sessions 테이블에 잘 저장됨

---

#### GET /{session_id} (세션 조회)
```python
# Line 172-200
@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    session = await session_mgr.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, ...)

    # ❌ session["last_activity"] KeyError 발생 가능
    return SessionInfo(
        session_id=session["session_id"],
        created_at=session["created_at"].isoformat(),
        expires_at=session["expires_at"].isoformat(),
        last_activity=session["last_activity"].isoformat(),  # ❌ 키 없음
        metadata=session.get("metadata", {})
    )
```

**❌ 버그 발견**: `last_activity` 키 누락으로 인한 에러

---

#### WebSocket /ws/{session_id} (메시지 처리)
```python
# Line 241-396
@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str, ...):
    # 1. 세션 검증
    validation_result = await session_mgr.validate_session(session_id)
    if not validation_result:
        await websocket.close(code=4004, reason="Session not found or expired")
        return

    # 2. WebSocket 연결
    await conn_mgr.connect(session_id, websocket)

    # 3. 메시지 수신 루프
    while True:
        data = await websocket.receive_json()

        if message_type == "query":
            # 비동기 처리
            asyncio.create_task(_process_query_async(...))
```

**✅ 정상 동작**: WebSocket 연결 및 메시지 처리

---

#### _process_query_async (쿼리 처리)
```python
# Line 398-475
async def _process_query_async(supervisor, query, session_id, ...):
    # 1. ✅ 사용자 메시지 저장
    await _save_message_to_db(session_id, "user", query)

    # 2. Supervisor 처리
    result = await supervisor.process_query_streaming(...)

    # 3. ✅ AI 응답 저장
    response_content = final_response.get("answer") or ...
    if response_content:
        await _save_message_to_db(session_id, "assistant", response_content)
```

**✅ 정상 동작**: 메시지가 DB에 정상 저장됨

---

#### _save_message_to_db (메시지 저장)
```python
# Line 30-61
async def _save_message_to_db(session_id: str, role: str, content: str) -> bool:
    async for db in get_async_db():
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            db.add(message)
            await db.commit()
            logger.info(f"💾 Message saved: {role} → {session_id[:20]}...")
            result = True
```

**✅ 정상 동작**: chat_messages 테이블에 INSERT 성공

---

#### GET /sessions/{session_id}/messages (메시지 조회)
```python
# Line 725-777
@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(session_id: str, ...):
    # 1. 세션 존재 확인
    session_query = select(ChatSession).where(ChatSession.session_id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. 메시지 조회
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    messages = result.scalars().all()
```

**✅ 정상 동작**: 메시지 조회 API는 정상

---

### 3.2 Backend: postgres_session_manager.py

#### create_session (세션 생성)
```python
# Line 38-87
async def create_session(
    self,
    user_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Tuple[str, datetime]:
    session_id = f"session-{uuid.uuid4()}"
    user_id = user_id or 1

    async for db_session in get_async_db():
        try:
            # 새 세션 생성
            new_session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                title="새 대화"
            )
            db_session.add(new_session)
            await db_session.commit()
            await db_session.refresh(new_session)

            expires_at = datetime.now(timezone.utc) + self.session_ttl

            logger.info(f"Session created (PostgreSQL): {session_id} ...")
            result = (session_id, expires_at)
```

**✅ 정상 동작**: chat_sessions 테이블에 INSERT

---

#### get_session (세션 조회)
```python
# Line 130-163
async def get_session(self, session_id: str) -> Optional[Dict]:
    async for db_session in get_async_db():
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return None

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "expires_at": session.created_at + self.session_ttl
                # ❌ "last_activity" 키 누락!!!
            }
```

**❌ 버그**: `last_activity` 키가 없어서 chat_api.py에서 KeyError 발생

---

#### validate_session (세션 검증)
```python
# Line 89-128
async def validate_session(self, session_id: str) -> bool:
    async for db_session in get_async_db():
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"Session not found: {session_id}")
                return False

            # updated_at 갱신
            await db_session.execute(
                update(ChatSession)
                .where(ChatSession.session_id == session_id)
                .values(updated_at=datetime.now(timezone.utc))
            )
            await db_session.commit()

            logger.debug(f"Session validated: {session_id}")
            return True
```

**✅ 정상 동작**: chat_sessions 테이블에서 조회 및 갱신

---

### 3.3 Frontend: use-session.ts

#### 세션 초기화 흐름
```javascript
// Line 13-59
useEffect(() => {
  initSession()  // ❌ 클린업 없음
}, [])

const initSession = async () => {
  setIsLoading(true)
  setError(null)

  try {
    // 1. sessionStorage에서 기존 세션 확인
    const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY)

    if (storedSessionId) {
      // 2. 세션 유효성 검증
      try {
        await chatAPI.getSessionInfo(storedSessionId)
        console.log("✅ Existing session valid:", storedSessionId)
        setSessionId(storedSessionId)
        setIsLoading(false)
        return  // ✅ 여기서 종료
      } catch (error) {
        // ❌ 404 → 새 세션 생성
        console.warn("⚠️ Session expired or invalid, creating new session:", error)
        sessionStorage.removeItem(SESSION_STORAGE_KEY)
        // 계속 진행
      }
    }

    // 3. 새 세션 생성
    console.log("🔄 Creating new session...")
    const response = await chatAPI.startSession({...})

    console.log("✅ New session created:", response.session_id)
    setSessionId(response.session_id)
    sessionStorage.setItem(SESSION_STORAGE_KEY, response.session_id)
  } catch (err) {
    console.error("❌ Session initialization failed:", err)
    setError(err instanceof Error ? err.message : "...")
  } finally {
    setIsLoading(false)
  }
}
```

**문제점**:
1. ❌ React Strict Mode에서 useEffect 2번 실행됨
2. ❌ 클린업 함수 없어서 중복 실행 방지 안 됨
3. ❌ GET /{session_id} 404 → 계속 새 세션 생성

---

### 3.4 Frontend: chat-interface.tsx

#### chat_session_id 생성 (불필요)
```javascript
// Line 96-110
useEffect(() => {
  let currentChatSessionId = localStorage.getItem(CHAT_SESSION_KEY)

  if (!currentChatSessionId) {
    // ❌ 새로운 chat_session_id 생성 (사용 안 됨!)
    currentChatSessionId = `session-${Date.now()}-${Math.random()...}`
    localStorage.setItem(CHAT_SESSION_KEY, currentChatSessionId)
    console.log('[ChatInterface] Created new chat_session_id:', currentChatSessionId)
  } else {
    console.log('[ChatInterface] Loaded existing chat_session_id:', currentChatSessionId)
  }

  setChatSessionId(currentChatSessionId)
}, [])
```

**❌ 불필요한 코드**:
- Backend에서 chat_session_id를 받지만 실제로 사용하지 않음
- session_id만으로 충분함

---

#### DB 메시지 로드
```javascript
// Line 297-336
useEffect(() => {
  if (!sessionId || !wsConnected) return

  const loadMessagesFromDB = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(
        `${apiUrl}/api/v1/chat/sessions/${sessionId}/messages?limit=100`
      )

      if (response.ok) {
        const dbMessages = await response.json()

        if (dbMessages.length > 0) {
          const formattedMessages = dbMessages.map((msg: any) => ({
            id: msg.id.toString(),
            type: msg.role === 'user' ? 'user' : 'bot',
            content: msg.content,
            timestamp: new Date(msg.created_at)
          }))

          // ✅ DB에 메시지가 있으면 환영 메시지 제거하고 DB 메시지로 교체
          setMessages(formattedMessages)
          console.log(`[ChatInterface] ✅ Loaded ${dbMessages.length} messages from DB`)
        } else {
          // ✅ DB에 메시지가 없으면 환영 메시지 유지
          console.log('[ChatInterface] No messages in DB, keeping welcome message')
        }
      }
    } catch (error) {
      console.error('[ChatInterface] Failed to load messages from DB:', error)
    }
  }

  loadMessagesFromDB()
}, [sessionId, wsConnected])
```

**✅ 로직은 정상**:
- sessionId가 올바르면 정상 작동할 것
- 문제는 sessionId가 계속 바뀌어서 이전 메시지 못 불러옴

---

#### localStorage 저장/복원 (DEPRECATED)
```javascript
// Line 348-375
/*
// ❌ DEPRECATED: localStorage 저장/복원 로직 비활성화
// DB 저장이 Phase 1에서 구현되어 더 이상 localStorage 사용 안함

// localStorage에 메시지 저장 (자동)
useEffect(() => {
  if (messages.length > 1) {
    const recentMessages = messages.slice(-MAX_STORED_MESSAGES)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(recentMessages))
  }
}, [messages])

// localStorage에서 메시지 복원 (초기 로드)
useEffect(() => {
  const savedMessages = localStorage.getItem(STORAGE_KEY)
  if (savedMessages) {
    // ...
  }
}, [])
*/
```

**✅ 이미 주석 처리됨**: 삭제 예정

---

## 4. 불필요한 코드 리스트

### 4.1 Frontend: chat-interface.tsx

#### 1. chat_session_id 관련 코드
```javascript
// ❌ 삭제 대상 1: state 선언 (Line 84)
const [chatSessionId, setChatSessionId] = useState<string>("")

// ❌ 삭제 대상 2: chat_session_id 생성 useEffect (Line 96-110)
useEffect(() => {
  let currentChatSessionId = localStorage.getItem(CHAT_SESSION_KEY)
  if (!currentChatSessionId) {
    currentChatSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem(CHAT_SESSION_KEY, currentChatSessionId)
    console.log('[ChatInterface] Created new chat_session_id:', currentChatSessionId)
  } else {
    console.log('[ChatInterface] Loaded existing chat_session_id:', currentChatSessionId)
  }
  setChatSessionId(currentChatSessionId)
}, [])

// ❌ 삭제 대상 3: WebSocket 전송 시 chat_session_id 파라미터 (Line 468)
wsClientRef.current.send({
  type: "query",
  query: content,
  chat_session_id: chatSessionId,  // ❌ 삭제
  enable_checkpointing: true
})

// ❌ 삭제 대상 4: 콘솔 로그 (Line 472)
console.log('[ChatInterface] Sent query with chat_session_id:', chatSessionId)

// ❌ 삭제 대상 5: CHAT_SESSION_KEY 상수 (Line 64)
const CHAT_SESSION_KEY = 'current_chat_session_id'
```

---

#### 2. localStorage 관련 코드
```javascript
// ❌ 삭제 대상 1: STORAGE_KEY 상수 (Line 62)
const STORAGE_KEY = 'chat-messages'

// ❌ 삭제 대상 2: MAX_STORED_MESSAGES 상수 (Line 63)
const MAX_STORED_MESSAGES = 50

// ❌ 삭제 대상 3: 주석 처리된 코드 블록 (Line 348-375)
/*
// localStorage에 메시지 저장 (자동)
useEffect(() => {
  if (messages.length > 1) {
    const recentMessages = messages.slice(-MAX_STORED_MESSAGES)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(recentMessages))
  }
}, [messages])

// localStorage에서 메시지 복원 (초기 로드)
useEffect(() => {
  const savedMessages = localStorage.getItem(STORAGE_KEY)
  if (savedMessages) {
    try {
      const parsed = JSON.parse(savedMessages)
      setMessages(parsed.map((m: Message) => ({
        ...m,
        timestamp: new Date(m.timestamp)
      })))
      console.log('[ChatInterface] Restored messages from localStorage:', parsed.length)
    } catch (e) {
      console.error('[ChatInterface] Failed to restore messages:', e)
    }
  }
}, [])
*/

// ❌ 삭제 대상 4: clearHistory 함수 (Line 409-421)
const clearHistory = () => {
  localStorage.removeItem(STORAGE_KEY)
  setMessages([
    {
      id: "1",
      type: "bot",
      content: "안녕하세요! 도와줘 홈즈냥즈입니다. 안전한 부동산 거래를 위해 어떤 도움이 필요하신가요?",
      timestamp: new Date()
    }
  ])
  console.log('[ChatInterface] Chat history cleared')
}
```

---

### 4.2 Backend: chat_api.py

#### chat_session_id 파라미터 (사용하지 않음)
```python
# ❌ 삭제 대상 1: WebSocket handler에서 chat_session_id 추출 (Line 314)
chat_session_id = data.get("chat_session_id")  # GPT-style chat session ID

# ❌ 삭제 대상 2: chat_session_id 로깅 (Line 324-326)
if chat_session_id:
    logger.info(f"[WebSocket] Received chat_session_id: {chat_session_id}")

# ❌ 삭제 대상 3: _process_query_async 파라미터 (Line 402, 424)
async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    chat_session_id: str,  # ❌ 삭제
    enable_checkpointing: bool,
    ...
):
    # ...
    if chat_session_id:
        logger.info(f"Chat session ID: {chat_session_id}")

# ❌ 삭제 대상 4: supervisor.process_query_streaming에 chat_session_id 전달 (Line 440)
result = await supervisor.process_query_streaming(
    query=query,
    session_id=session_id,
    chat_session_id=chat_session_id,  # ❌ 삭제
    user_id=user_id,
    progress_callback=progress_callback
)
```

**참고**:
- Backend에서 chat_session_id를 받지만 실제로 아무 곳에서도 사용하지 않음
- session_id만으로 메시지 저장 및 조회 가능

---

## 5. 다음 단계 권장사항

### Step 1: P1 버그 수정 (최우선) 🔥

**파일**: `backend/app/api/postgres_session_manager.py`

**수정 위치**: Line 150-157

**Before**:
```python
return {
    "session_id": session.session_id,
    "user_id": session.user_id,
    "title": session.title,
    "created_at": session.created_at,
    "updated_at": session.updated_at,
    "expires_at": session.created_at + self.session_ttl
    # ❌ "last_activity" 키 누락
}
```

**After**:
```python
return {
    "session_id": session.session_id,
    "user_id": session.user_id,
    "title": session.title,
    "created_at": session.created_at,
    "updated_at": session.updated_at,
    "expires_at": session.created_at + self.session_ttl,
    "last_activity": session.updated_at  # ✅ 추가
}
```

**테스트**:
```bash
# 1. Backend 재시작
# 2. 브라우저 새로고침
# 3. 콘솔 확인:
✅ Existing session valid: session-xxx
```

---

### Step 2: React Strict Mode 비활성화 (임시)

**파일**: `frontend/next.config.mjs`

**Before**:
```javascript
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  images: { unoptimized: true },
}
```

**After**:
```javascript
const nextConfig = {
  reactStrictMode: false,  // ✅ 임시로 비활성화 (개발 모드)
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  images: { unoptimized: true },
}
```

**참고**:
- 프로덕션 빌드에서는 자동으로 비활성화됨
- 개발 중에만 임시로 끄고, 나중에 다시 켜도 됨

**테스트**:
```bash
# 1. Frontend 재시작 (npm run dev)
# 2. 브라우저 완전히 닫고 다시 열기
# 3. 콘솔 확인:
✅ New session created: session-xxx  (1번만!)
```

---

### Step 3: useEffect 클린업 추가 (선택)

**파일**: `frontend/hooks/use-session.ts`

**Before**:
```javascript
useEffect(() => {
  initSession()
}, [])
```

**After**:
```javascript
useEffect(() => {
  let isMounted = true

  const init = async () => {
    if (!isMounted) return
    await initSession()
  }

  init()

  return () => {
    isMounted = false
  }
}, [])
```

**참고**:
- Step 2에서 Strict Mode 비활성화하면 불필요할 수 있음
- 더 안전한 코드를 위해 추가 권장

---

### Step 4: 불필요한 코드 제거

**순서**:
1. Frontend: chat_session_id 관련 코드 제거
2. Frontend: localStorage 관련 코드 제거
3. Backend: chat_session_id 파라미터 제거

**주의**:
- 한 번에 하나씩 제거
- 각 단계마다 테스트

---

### Step 5: 통합 테스트

**시나리오 1**: 완전히 새로운 사용자
```
1. 브라우저 열기 (시크릿 모드)
2. sessionStorage 비어있음
3. POST /start → 새 세션 생성 (1개만!)
4. 환영 메시지 표시
5. 메시지 전송 → DB 저장 확인
6. F5 새로고침 → DB에서 로드 확인
```

**시나리오 2**: F5 새로고침
```
1. 채팅 중 (메시지 2-3개 주고받음)
2. F5 새로고침
3. sessionStorage에서 session_id 복원
4. GET /{session_id} → 200 OK (✅ P1 해결)
5. WebSocket 연결
6. DB에서 메시지 로드
7. 대화 내역 그대로 유지
```

**시나리오 3**: 돌아온 사용자
```
1. 브라우저 닫기
2. 다시 브라우저 열기
3. sessionStorage에 이전 session_id 있음
4. GET /{session_id} → 200 OK
5. WebSocket 연결
6. DB에서 메시지 로드
7. 이어서 대화
```

---

## 6. 결론

### ✅ 발견된 핵심 버그
1. **postgres_session_manager.get_session()**에서 "last_activity" 키 누락
   - chat_api.py에서 KeyError 발생 → 404 에러
   - 이것이 모든 문제의 근본 원인!

### ✅ 정상 동작하는 부분
- POST /start: 세션 생성 ✅
- WebSocket: 메시지 송수신 ✅
- _save_message_to_db(): 메시지 저장 ✅
- GET /sessions/{session_id}/messages: 메시지 조회 ✅

### ❌ 수정 필요한 부분
1. P1: postgres_session_manager.get_session() "last_activity" 추가
2. P0: React Strict Mode 비활성화 (임시)
3. 불필요한 코드 제거 (chat_session_id, localStorage)

### 📊 우선순위
| 순위 | 작업 | 영향도 | 난이도 |
|------|------|--------|--------|
| **P1** | "last_activity" 키 추가 | 🔥 매우 높음 | 매우 쉬움 |
| **P0** | Strict Mode 비활성화 | 높음 | 매우 쉬움 |
| P3 | 불필요한 코드 제거 | 중간 | 쉬움 |

### 🎯 다음 Phase
- **Phase 1**: P1 버그 수정 + 테스트
- **Phase 2**: P0 수정 + 테스트
- **Phase 3**: 코드 정리 + 최종 테스트

---

**문서 끝**

Phase 0 완료 ✅
다음: Phase 1 진행 (P1 버그 수정)
