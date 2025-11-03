# ScrollArea 무한 루프 해결 및 시스템 아키텍처 분석

**날짜**: 2025-10-16
**작성자**: Claude Code
**상태**: 진행 중 🔄
**문서 버전**: 1.0

---

## 📋 목차

1. [ScrollArea 무한 루프 문제](#1-scrollarea-무한-루프-문제)
2. [Frontend 아키텍처 분석](#2-frontend-아키텍처-분석)
3. [Backend 아키텍처 분석](#3-backend-아키텍처-분석)
4. [수정 계획](#4-수정-계획)
5. [실행 가이드](#5-실행-가이드)

---

## 1. ScrollArea 무한 루프 문제

### 1.1 문제 요약

**증상**:
```
Error: Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside componentWillUpdate or componentDidUpdate.
setScrollArea ..\src\scroll-area.tsx (85:66)
```

**발생 시점**:
- 지도 검색 페이지 → 채팅 페이지 전환 시
- 채팅 페이지가 완전히 언마운트되었다가 다시 마운트될 때
- F5 새로고침으로 일시적 해결 가능 (컴포넌트 완전 재초기화)

**근본 원인**:
1. **Radix UI ScrollArea의 내부 상태 관리 문제**
   - ScrollArea 컴포넌트는 내부적으로 스크롤 상태를 추적
   - 상태 업데이트가 부모 컴포넌트의 재렌더링을 유발
   - 부모 재렌더링 → ScrollArea 리마운트 → 상태 업데이트 → 무한 루프

2. **chat-interface.tsx의 높은 렌더링 빈도**
   - WebSocket 메시지 수신마다 messages 상태 업데이트
   - 실시간 ExecutionProgress 업데이트
   - ScrollArea가 매번 스크롤 위치 재계산 시도

### 1.2 영향 범위 분석

| 파일 | ScrollArea 사용 | 문제 여부 | 이유 |
|------|---------------|---------|------|
| **chat-interface.tsx** | ✅ 사용 (Line 460) | ⚠️ **문제 발생** | 전체 화면 크기, 높은 렌더링 빈도, 페이지 마운트/언마운트 |
| **memory-history.tsx** | ✅ 사용 (Line 119) | ✅ 정상 | 고정 높이 200px, 낮은 업데이트 빈도, Collapsible 내부 |

**결론**: chat-interface.tsx만 수정 필요

### 1.3 ScrollArea 사용 현황

#### chat-interface.tsx (문제 발생)
```typescript
// Line 7: Import
import { ScrollArea } from "@/components/ui/scroll-area"

// Line 460: 사용
<ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
  <div className="space-y-4 max-w-3xl mx-auto">
    {messages.map((message) => (...))}
  </div>
</ScrollArea>

// Line 318-326: 스크롤 자동 이동 (Radix UI 내부 구조 접근)
useEffect(() => {
  if (scrollAreaRef.current) {
    const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight
    }
  }
}, [messages])
```

#### memory-history.tsx (정상 작동)
```typescript
// Line 119: 사용
<ScrollArea className="h-[200px]">
  <div className="space-y-3">
    {memories.map((memory) => (...))}
  </div>
</ScrollArea>
```

---

## 2. Frontend 아키텍처 분석

### 2.1 디렉토리 구조

```
frontend/
├── app/
│   ├── layout.tsx              # Root Layout (Theme Provider)
│   └── page.tsx                # Main Page (라우팅, 페이지 전환)
├── components/
│   ├── chat-interface.tsx      # 채팅 인터페이스 (WebSocket, 메시지 관리)
│   ├── map-interface.tsx       # 지도 검색 인터페이스
│   ├── sidebar.tsx             # 사이드바 (메뉴, Memory History)
│   ├── memory-history.tsx      # 최근 대화 목록
│   ├── session-list.tsx        # 세션 리스트 (미사용)
│   ├── answer-display.tsx      # 구조화된 답변 표시
│   ├── execution-plan-page.tsx # 실행 계획 표시
│   ├── execution-progress-page.tsx # 실행 진행 상황
│   ├── step-item.tsx           # 실행 단계 아이템
│   ├── agents/                 # Agent 별 UI 컴포넌트
│   │   ├── analysis-agent.tsx
│   │   ├── verification-agent.tsx
│   │   └── consultation-agent.tsx
│   └── ui/                     # shadcn/ui 컴포넌트
│       ├── scroll-area.tsx     # ⚠️ Radix UI ScrollArea 래퍼
│       └── ...                 # 50+ UI 컴포넌트
├── hooks/
│   ├── use-session.ts          # 세션 관리 (sessionStorage, API 호출)
│   ├── use-chat-sessions.ts    # 채팅 세션 목록 관리 (미사용)
│   ├── use-toast.ts            # Toast 알림
│   └── use-mobile.ts           # 모바일 감지
├── lib/
│   ├── ws.ts                   # WebSocket 클라이언트 (ChatWSClient)
│   ├── api.ts                  # REST API 클라이언트
│   ├── types.ts                # 타입 정의 (ExecutionStepState 등)
│   ├── utils.ts                # 유틸리티 (cn 함수 등)
│   └── ...                     # 지도 관련 유틸
└── types/
    ├── chat.ts                 # 채팅 관련 타입
    ├── process.ts              # 프로세스 상태 타입
    └── execution.ts            # 실행 계획/단계 타입
```

### 2.2 핵심 아키텍처 패턴

#### 2.2.1 Next.js App Router 구조
```typescript
// app/page.tsx - 단일 페이지 애플리케이션
export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<PageType>("chat")
  const [isSplitView, setIsSplitView] = useState(false)

  // 페이지 타입: "chat" | "map" | "analysis" | "verification" | "consultation"
  const renderMainContent = () => {
    switch (currentPage) {
      case "chat": return <ChatInterface />
      case "map": return <MapInterface />
      // ...
    }
  }
}
```

**특징**:
- Single Page Application (SPA) 방식
- 클라이언트 사이드 라우팅 (useState로 페이지 전환)
- Split View 지원 (채팅 + Agent 동시 표시)

#### 2.2.2 State Management
**React Hooks 기반 로컬 상태 관리**:
- `useState`: 컴포넌트 로컬 상태
- `useEffect`: 사이드 이펙트 (API 호출, WebSocket 연결)
- `useCallback`: 함수 메모이제이션
- `useRef`: DOM 참조, WebSocket 인스턴스 보관

**전역 상태 없음**: Redux, Zustand 등 사용 안 함

#### 2.2.3 세션 관리 (use-session.ts)
```typescript
export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)

  useEffect(() => {
    // 1. sessionStorage에서 기존 세션 확인
    const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY)

    if (storedSessionId) {
      // ✅ 그냥 바로 사용 (검증 제거)
      setSessionId(storedSessionId)
      return
    }

    // 2. 새 세션 생성 (POST /api/v1/chat/start)
    const response = await chatAPI.startSession(...)
    setSessionId(response.session_id)
    sessionStorage.setItem(SESSION_STORAGE_KEY, response.session_id)
  }, [])
}
```

**흐름**:
1. 컴포넌트 마운트 시 useSession() 호출
2. sessionStorage 확인 → 있으면 바로 사용
3. 없으면 POST /start → session_id 생성 → sessionStorage 저장
4. sessionId 변경 → ChatInterface에서 WebSocket 연결

#### 2.2.4 WebSocket 통신 (lib/ws.ts)
```typescript
export class ChatWSClient {
  constructor(config: WSClientConfig) {
    this.config = { reconnectInterval: 2000, maxReconnectAttempts: 5, ...config }
  }

  connect(): void {
    const wsUrl = `${baseUrl}/api/v1/chat/ws/${sessionId}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onmessage = (event) => {
      const message: WSMessage = JSON.parse(event.data)
      this.config.onMessage(message)  // → handleWSMessage()
    }
  }

  send(message: WSClientMessage): void {
    if (this.state === 'connected') {
      this.ws.send(JSON.stringify(message))
    } else {
      this.messageQueue.push(message)  // 연결 전 큐잉
    }
  }
}
```

**특징**:
- Singleton 패턴 (createWSClient)
- 자동 재연결 (Exponential backoff)
- 메시지 큐잉 (연결 전 메시지 보관)

#### 2.2.5 메시지 처리 흐름 (chat-interface.tsx)
```
사용자 입력 → handleSendMessage()
  ├─ 1. UserMessage 추가 (즉시 UI 표시)
  ├─ 2. ExecutionPlanPage 추가 (로딩 상태)
  └─ 3. WebSocket 전송: { type: "query", query: "..." }

Backend 처리 → WebSocket 메시지 수신
  ├─ "plan_ready" → ExecutionPlanPage 업데이트
  ├─ "execution_start" → ExecutionProgressPage 생성
  ├─ "todo_updated" → ExecutionProgressPage 업데이트
  └─ "final_response" → BotMessage 추가 (structured_data 포함)
```

**handleWSMessage()**: WebSocket 메시지 타입별 분기 처리

#### 2.2.6 DB 메시지 로드 (chat-interface.tsx)
```typescript
// WebSocket 연결 후 DB에서 메시지 로드
useEffect(() => {
  if (!sessionId || !wsConnected) return

  const loadMessagesFromDB = async () => {
    const response = await fetch(
      `${apiUrl}/api/v1/chat/sessions/${sessionId}/messages?limit=100`
    )
    const dbMessages = await response.json()

    if (dbMessages.length > 0) {
      // ✅ DB 메시지로 환영 메시지 교체
      setMessages(formattedMessages)
    } else {
      // ✅ DB가 비어있으면 환영 메시지 유지
    }
  }

  loadMessagesFromDB()
}, [sessionId, wsConnected])
```

**F5 새로고침 흐름**:
1. sessionStorage에서 session_id 복원
2. WebSocket 재연결
3. DB에서 메시지 로드
4. 대화 내역 복원 ✅

### 2.3 데이터 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  app/page.tsx (Main Router)                                │
│    ↓                                                        │
│  components/chat-interface.tsx                             │
│    ├─ hooks/use-session.ts (sessionStorage, POST /start)  │
│    ├─ lib/ws.ts (WebSocket Client)                        │
│    └─ handleWSMessage() (메시지 타입별 처리)                │
│                                                             │
│  components/answer-display.tsx                             │
│    └─ structured_data.sections[] 렌더링                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP / WebSocket
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                         Backend                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FastAPI Router: app/api/chat_api.py                       │
│    ├─ POST /api/v1/chat/start                             │
│    │   → PostgreSQLSessionManager.create_session()        │
│    │   → ChatSession INSERT (DB 영속성)                    │
│    │                                                        │
│    ├─ WebSocket /api/v1/chat/ws/{session_id}              │
│    │   → _process_query_async()                           │
│    │   → _save_message_to_db() (user 메시지)              │
│    │   → TeamBasedSupervisor.process_query_streaming()    │
│    │   → _save_message_to_db() (assistant 메시지)         │
│    │                                                        │
│    └─ GET /api/v1/chat/sessions/{session_id}/messages     │
│        → ChatMessage SELECT (structured_data 포함)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  chat_sessions                                             │
│    ├─ session_id (PK, VARCHAR(100))                       │
│    ├─ user_id, title, created_at, updated_at              │
│    └─ message_count, is_active, metadata (JSONB)          │
│                                                             │
│  chat_messages                                             │
│    ├─ id (PK, SERIAL)                                     │
│    ├─ session_id (FK → chat_sessions)                     │
│    ├─ role (user/assistant/system)                        │
│    ├─ content (TEXT)                                      │
│    ├─ structured_data (JSONB) ✅ 구조화된 답변            │
│    └─ created_at                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Backend 아키텍처 분석

### 3.1 디렉토리 구조

```
backend/
├── app/
│   ├── api/                                # API 라우터
│   │   ├── chat_api.py                    # 채팅 WebSocket + REST API
│   │   ├── postgres_session_manager.py    # PostgreSQL 세션 관리
│   │   ├── ws_manager.py                  # WebSocket 연결 관리
│   │   ├── schemas.py                     # Pydantic 스키마
│   │   └── error_handlers.py              # 에러 핸들러
│   ├── models/                             # SQLAlchemy 모델
│   │   ├── chat.py                        # ChatSession, ChatMessage
│   │   ├── users.py                       # User
│   │   └── real_estate.py                 # 부동산 데이터
│   ├── service_agent/                      # Agent 시스템
│   │   ├── supervisor/                    # Supervisor (LangGraph)
│   │   │   └── team_supervisor.py         # TeamBasedSupervisor
│   │   ├── foundation/                    # 기반 서비스
│   │   │   ├── simple_memory_service.py   # Long-term Memory
│   │   │   └── context.py                 # LLM Context
│   │   └── teams/                         # Agent Teams
│   │       ├── analysis_team/
│   │       ├── verification_team/
│   │       └── consultation_team/
│   ├── db/
│   │   └── postgre_db.py                  # DB 연결, Base 클래스
│   └── reports/
│       └── long_term_memory/              # 장기 보고서 (이 파일)
├── main.py                                 # FastAPI 앱 초기화
└── requirements.txt
```

### 3.2 핵심 아키텍처 패턴

#### 3.2.1 FastAPI + SQLAlchemy Async
```python
# app/api/chat_api.py
from fastapi import APIRouter, WebSocket, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    session_id, expires_at = await session_mgr.create_session(...)
    # ...
```

**특징**:
- 완전 비동기 (async/await)
- Dependency Injection (Depends)
- Pydantic 스키마 (자동 검증)

#### 3.2.2 Database 모델 (SQLAlchemy)
```python
# app/models/chat.py
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), default="새 대화")
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
    message_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    session_metadata = Column("metadata", JSONB)

    messages = relationship("ChatMessage", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.session_id"))
    role = Column(String(20))  # user/assistant/system
    content = Column(Text)
    structured_data = Column(JSONB)  # ✅ 구조화된 답변
    created_at = Column(TIMESTAMP(timezone=True))
```

**관계**:
- ChatSession (1) ↔ (N) ChatMessage
- ChatSession (N) ↔ (1) User
- CASCADE DELETE: 세션 삭제 시 메시지 자동 삭제

#### 3.2.3 세션 관리 (PostgreSQLSessionManager)
```python
# app/api/postgres_session_manager.py
class PostgreSQLSessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}  # 메모리 캐시
        self.lock = asyncio.Lock()

    async def create_session(self, user_id: int, metadata: dict) -> Tuple[str, datetime]:
        session_id = f"session-{uuid.uuid4()}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        # 메모리에 저장 (임시, 24시간 TTL)
        self.sessions[session_id] = SessionData(...)

        return session_id, expires_at

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        # 메모리 캐시에서 조회 (만료 체크)
        session = self.sessions.get(session_id)
        if session and session.expires_at > datetime.now(timezone.utc):
            return session
        return None
```

**특징**:
- 메모리 기반 세션 저장 (Redis 대신)
- 24시간 TTL
- 서버 재시작 시 세션 초기화됨

**문제점** (이전 이슈):
- GET /{session_id}가 메모리에서만 조회 → 만료되면 404
- **해결**: chat_sessions 테이블에도 저장 (DB 영속성)

#### 3.2.4 WebSocket 연결 관리 (ConnectionManager)
```python
# app/api/ws_manager.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    async def send_message(self, session_id: str, message: dict):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json(message)

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
```

**특징**:
- 세션 ID별 WebSocket 연결 관리
- 동일 세션에 여러 연결 불가 (Dict 사용)

#### 3.2.5 메시지 저장 (chat_api.py)
```python
async def _save_message_to_db(
    session_id: str,
    role: str,
    content: str,
    structured_data: dict = None
) -> bool:
    async for db in get_async_db():
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                structured_data=structured_data  # ✅ JSONB 저장
            )
            db.add(message)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            return False
```

**호출 시점**:
1. 사용자 메시지 수신 직후 (`_process_query_async` Line 419)
2. AI 응답 생성 직후 (`_process_query_async` Line 457)

#### 3.2.6 Agent 시스템 (TeamBasedSupervisor)
```python
# app/service_agent/supervisor/team_supervisor.py
class TeamBasedSupervisor:
    async def process_query_streaming(
        self,
        query: str,
        session_id: str,
        user_id: int,
        progress_callback
    ) -> dict:
        # 1. Planning (의도 분석)
        await progress_callback("plan_ready", {
            "intent": "...",
            "execution_steps": [...],
            "estimated_total_time": 10
        })

        # 2. Execution (Agent 실행)
        await progress_callback("execution_start", {...})

        for step in execution_steps:
            await progress_callback("todo_updated", {...})
            result = await self._execute_step(step)

        # 3. Final Response
        return {
            "final_response": {
                "answer": "...",
                "structured_data": {
                    "sections": [...],
                    "metadata": {...}
                }
            }
        }
```

**특징**:
- LangGraph 기반 워크플로우
- 실시간 진행 상황 콜백
- Checkpointing (상태 저장/복원)

### 3.3 API 엔드포인트 전체 목록

#### 세션 관리
- `POST /api/v1/chat/start` - 새 세션 생성
- `GET /api/v1/chat/{session_id}` - 세션 정보 조회
- `DELETE /api/v1/chat/{session_id}` - 세션 삭제

#### WebSocket
- `WS /api/v1/chat/ws/{session_id}` - 실시간 채팅

#### 채팅 세션 (GPT 스타일)
- `GET /api/v1/chat/sessions` - 세션 목록 조회
- `POST /api/v1/chat/sessions` - 새 채팅 세션 생성
- `GET /api/v1/chat/sessions/{session_id}/messages` - 메시지 조회
- `PATCH /api/v1/chat/sessions/{session_id}` - 세션 제목 업데이트
- `DELETE /api/v1/chat/sessions/{session_id}` - 세션 삭제

#### Memory
- `GET /api/v1/chat/memory/history` - Long-term Memory 조회

#### 통계
- `GET /api/v1/chat/stats/sessions` - 세션 통계
- `GET /api/v1/chat/stats/websockets` - WebSocket 통계
- `POST /api/v1/chat/cleanup/sessions` - 만료 세션 정리

### 3.4 데이터베이스 스키마

```sql
-- chat_sessions 테이블
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at);

-- chat_messages 테이블
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL
        REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    structured_data JSONB,  -- ✅ 구조화된 답변 (sections, metadata)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
```

---

## 4. 수정 계획

### 4.1 ScrollArea 제거 계획

#### Phase 1: chat-interface.tsx 수정

**목표**: ScrollArea를 일반 div로 교체하여 무한 루프 해결

**수정 내용**:

1. **Import 제거** (Line 7)
```typescript
// 제거
import { ScrollArea } from "@/components/ui/scroll-area"
```

2. **JSX 수정** (Line 460)
```typescript
// 변경 전
<ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
  <div className="space-y-4 max-w-3xl mx-auto">
    {messages.map((message) => (...))}
  </div>
</ScrollArea>

// 변경 후
<div ref={scrollAreaRef} className="flex-1 p-4 overflow-y-auto">
  <div className="space-y-4 max-w-3xl mx-auto">
    {messages.map((message) => (...))}
  </div>
</div>
```

**CSS 변경**:
- `overflow-y-auto`: 세로 스크롤 활성화
- `flex-1`: 부모의 남은 공간 채우기
- 스크롤바 스타일은 브라우저 기본값 사용

3. **스크롤 자동 이동 수정** (Line 318-326)
```typescript
// 변경 전: Radix UI 내부 구조 접근
useEffect(() => {
  if (scrollAreaRef.current) {
    const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight
    }
  }
}, [messages])

// 변경 후: 직접 DOM 조작
useEffect(() => {
  if (scrollAreaRef.current) {
    scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
  }
}, [messages])
```

#### Phase 2: 테스트

**테스트 시나리오**:

1. **페이지 전환 테스트**
   ```
   1. 지도 페이지 클릭
   2. 채팅 페이지 클릭
   3. 무한 루프 발생하지 않는지 확인
   4. 반복 10회
   ```

2. **메시지 전송 테스트**
   ```
   1. 채팅 페이지에서 메시지 전송
   2. 응답 수신 확인
   3. 스크롤 자동 이동 확인
   4. 반복 5회
   ```

3. **F5 새로고침 테스트**
   ```
   1. 채팅 중 F5 새로고침
   2. 대화 내역 유지 확인
   3. 스크롤 위치 확인 (맨 아래)
   ```

4. **브라우저 호환성 테스트**
   ```
   - Chrome
   - Edge
   - Firefox
   ```

#### Phase 3: memory-history.tsx는 유지

**이유**:
- 현재 문제 없음
- 작은 영역 (200px)
- 낮은 업데이트 빈도
- 불필요한 변경 방지

### 4.2 예상 효과

**긍정적 효과**:
- ✅ 무한 루프 완전 해결
- ✅ 페이지 전환 속도 향상 (렌더링 부담 감소)
- ✅ 코드 단순화 (Radix UI 의존성 제거)
- ✅ 스크롤 자동 이동 안정화

**단점 (미미함)**:
- 스크롤바 디자인이 브라우저 기본값으로 변경
- Radix UI의 부드러운 스크롤 애니메이션 없음

### 4.3 롤백 계획

**만약 문제 발생 시**:
```bash
# Git으로 원복
git checkout -- frontend/components/chat-interface.tsx
```

**또는 수동 원복**:
1. Import 재추가
2. `<div>` → `<ScrollArea>` 변경
3. useEffect 스크롤 로직 원복

---

## 5. 실행 가이드

### 5.1 현재 상태 확인

**Git 상태**:
```bash
git status
```

**기대 결과**:
```
M .claude/settings.local.json
M backend/data/storage/legal_info/chroma_db/chroma.sqlite3
M backend/logs/app.log
?? backend/nul
?? nul
```

**확인**: frontend 파일은 수정되지 않은 상태 (이전 rollback 완료)

### 5.2 수정 실행 순서

1. **보고서 저장 완료** ✅ (이 파일)
2. **chat-interface.tsx 수정**
   - Import 제거
   - ScrollArea → div 변경
   - useEffect 수정
3. **테스트 실행**
   - 페이지 전환
   - 메시지 전송
   - F5 새로고침
4. **문제 없으면 Git Commit**
   ```bash
   git add frontend/components/chat-interface.tsx
   git commit -m "Fix: Replace ScrollArea with plain div to resolve infinite loop

   - Remove Radix UI ScrollArea from chat-interface.tsx
   - Replace with overflow-y-auto div
   - Simplify scroll-to-bottom logic
   - Fixes infinite re-render on page navigation (Map → Chat)
   "
   ```

### 5.3 다음 작업 (세션 관리 구현)

**ScrollArea 문제 해결 후 진행**:
1. GET /api/v1/chat/sessions API 테스트
2. useChatSessions 훅 활성화
3. SessionList 컴포넌트 활성화
4. "New Chat" 버튼 연결
5. 세션 전환 테스트

**예상 소요 시간**: 70분 (기존 계획서 참조)

---

## 6. 아키텍처 요약

### 6.1 Frontend 핵심 특징
- **프레임워크**: Next.js 14 App Router
- **상태 관리**: React Hooks (useState, useEffect, useCallback)
- **통신**: WebSocket (실시간) + REST API (세션/메시지 조회)
- **스타일링**: Tailwind CSS + shadcn/ui
- **세션 저장**: sessionStorage (24시간 유지)

### 6.2 Backend 핵심 특징
- **프레임워크**: FastAPI (Async)
- **ORM**: SQLAlchemy 2.0 (Async)
- **DB**: PostgreSQL (chat_sessions, chat_messages)
- **Agent**: LangGraph (TeamBasedSupervisor)
- **WebSocket**: Starlette WebSocket
- **세션 관리**: 메모리 + DB (Hybrid)

### 6.3 데이터 흐름 요약
```
Frontend → POST /start → Backend
  → SessionManager (메모리)
  → ChatSession INSERT (DB)
  → session_id 반환

Frontend → WebSocket /ws/{session_id} → Backend
  → Supervisor.process_query_streaming()
  → _save_message_to_db() (user, assistant)
  → 실시간 진행 상황 전송 (plan_ready, todo_updated, final_response)

Frontend → GET /sessions/{session_id}/messages → Backend
  → ChatMessage SELECT (structured_data 포함)
  → F5 새로고침 시 대화 복원
```

---

## 7. 참고 문서

### 관련 보고서
1. `CHAT_SYSTEM_STRUCTURE_AND_PLAN_251016.md` - 채팅 시스템 전체 계획
2. `PHASE0_STRUCTURE_ANALYSIS_251016.md` - Phase 0 분석 결과
3. `Fix_Plan_Chat_Message_Persistence_251016.md` - 메시지 저장 수정 계획

### 핵심 파일 위치
**Frontend**:
- `frontend/components/chat-interface.tsx:460` - ScrollArea 사용 위치
- `frontend/hooks/use-session.ts` - 세션 관리
- `frontend/lib/ws.ts` - WebSocket 클라이언트

**Backend**:
- `backend/app/api/chat_api.py:243` - WebSocket 엔드포인트
- `backend/app/api/chat_api.py:30` - _save_message_to_db()
- `backend/app/models/chat.py` - DB 모델

---

**문서 끝**

**다음 단계**: chat-interface.tsx 수정 실행
