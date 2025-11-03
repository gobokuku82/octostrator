# Chat DB, State, Context 통합 가이드

## 목차
1. [Chat DB와 State의 관계](#chat-db와-state의-관계)
2. [Context/Config 통합](#contextconfig-통합)
3. [전체 아키텍처](#전체-아키텍처)
4. [구현 예시](#구현-예시)
5. [체크포인팅 전략](#체크포인팅-전략)

---

## Chat DB와 State의 관계

### ❌ 오해: "Chat DB와 State는 별개다"
### ✅ 진실: "Chat DB는 State의 영속성 계층이다"

```
chat_sessions, chat_messages (DB)
           ↕️
    State (메모리)
           ↕️
   LangGraph 실행
```

### 1. chat_sessions와 State 매핑

```python
# ============================================
# DB 스키마
# ============================================
Table chat_sessions {
    id uuid [primary key]              # LangGraph의 session_id
    user_id integer                    # 사용자 식별
    title varchar(100)                 # 세션 제목 ("전세 계약 상담", "강남 아파트 문의")
    created_at timestamp
    updated_at timestamp
}

# ============================================
# LangGraph State (현재)
# ============================================
class SharedState(TypedDict):
    user_query: str
    session_id: str          # ← chat_sessions.id 참조
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]

# ============================================
# Context (현재)
# ============================================
class AgentContext(TypedDict):
    chat_session_id: str     # ← chat_sessions.id와 동일
    chat_user_ref: str       # ← users.id 또는 외부 참조
    db_user_id: Optional[int]     # ← users.id (DB)
    db_session_id: Optional[int]  # ← 사용 안함 (UUID 사용)
```

### 핵심: State와 DB의 관계

```python
# State의 session_id = DB의 chat_sessions.id
state["session_id"] == chat_sessions.id

# Context의 chat_session_id = DB의 chat_sessions.id
context["chat_session_id"] == chat_sessions.id

# 셋 다 같은 값!
state["session_id"] == context["chat_session_id"] == chat_sessions.id
```

### 2. chat_messages와 State 매핑

```python
# ============================================
# DB 스키마
# ============================================
Table chat_messages {
    id uuid [primary key]
    session_id uuid [ref: > chat_sessions.id]
    sender_type varchar(20)  # "user" | "assistant"
    content text             # 메시지 내용
    created_at timestamp
}

# ============================================
# State에서의 표현 (변환 필요)
# ============================================
class MainSupervisorState(TypedDict):
    session_id: str  # chat_sessions.id
    user_query: str  # 최신 chat_messages.content (sender_type="user")

    # 대화 이력 (chat_messages 테이블에서 조회)
    conversation_history: List[Dict[str, str]]
    # [
    #   {"role": "user", "content": "...", "timestamp": "..."},
    #   {"role": "assistant", "content": "...", "timestamp": "..."}
    # ]

    # 최종 답변 (chat_messages로 저장될 예정)
    final_answer: str  # → chat_messages.content (sender_type="assistant")
```

### 3. 데이터 흐름

```python
User: "강남구 전세 5억 적정한가요?"
    ↓
┌─────────────────────────────────────────┐
│ 1. DB: chat_messages 저장                │
│    INSERT INTO chat_messages (           │
│      id: uuid,                           │
│      session_id: "abc-123",              │
│      sender_type: "user",                │
│      content: "강남구 전세..."            │
│    )                                     │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. State 생성                            │
│    state = {                             │
│      "session_id": "abc-123",            │ ← chat_sessions.id
│      "user_query": "강남구 전세...",      │ ← chat_messages.content
│      "conversation_history": [           │ ← chat_messages 조회
│        {"role": "user", "content": ""}   │
│      ],                                  │
│      "final_answer": ""  # 초기 빈값     │
│    }                                     │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. Context 생성                          │
│    context = {                           │
│      "chat_session_id": "abc-123",       │ ← chat_sessions.id
│      "chat_user_ref": "user_xyz",        │ ← users.id
│      "db_user_id": 123,                  │ ← users.id (integer)
│      "timestamp": "2025-10-06...",       │
│      "language": "ko"                    │
│    }                                     │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 4. LangGraph 실행                        │
│    result = await supervisor.invoke(     │
│      state,                              │
│      config={"configurable": context}    │
│    )                                     │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 5. DB: chat_messages 저장                │
│    INSERT INTO chat_messages (           │
│      id: uuid,                           │
│      session_id: "abc-123",              │
│      sender_type: "assistant",           │
│      content: result["final_answer"]     │ ← State에서 추출
│    )                                     │
└─────────────────────────────────────────┘
```

---

## Context/Config 통합

### 현재 Context 구조

```python
# backend/app/service_agent/foundation/context.py

class AgentContext(TypedDict):
    # LangGraph 식별자
    chat_user_ref: str              # "user_abc123"
    chat_session_id: str            # "session_xyz789" ← chat_sessions.id
    chat_thread_id: Optional[str]   # 체크포인팅용

    # DB 참조
    db_user_id: Optional[int]       # users.id
    db_session_id: Optional[int]    # 사용 안함 (UUID)

    # 런타임 정보
    request_id: Optional[str]
    timestamp: Optional[str]
    original_query: Optional[str]

    # 설정
    language: Optional[str]
    debug_mode: Optional[bool]

    # LLM 설정
    llm_context: Optional[LLMContext]
```

### DB 스키마와 통합

```python
# ============================================
# 통합된 Context (수정 필요)
# ============================================

class AgentContext(TypedDict):
    # ========== DB 직접 매핑 ==========
    # chat_sessions 테이블
    session_id: str  # chat_sessions.id (UUID)
    user_id: int     # users.id (integer)
    session_title: Optional[str]  # chat_sessions.title

    # ========== LangGraph 전용 ==========
    thread_id: Optional[str]  # 체크포인팅용 (chat_sessions.id와 다를 수 있음)

    # ========== 런타임 ==========
    request_id: str  # 요청 추적용
    timestamp: str
    language: str  # "ko" | "en"

    # ========== LLM 설정 ==========
    llm_context: Optional[LLMContext]

    # ========== 디버그 ==========
    debug_mode: bool
    trace_enabled: bool
```

### State + Context 함께 사용

```python
# Service Layer에서 State와 Context 모두 생성

async def process_message(
    db: Session,
    session_id: str,
    user_message: str
) -> Dict[str, Any]:
    """메시지 처리"""

    # ============================================
    # 1. DB에서 세션 정보 조회
    # ============================================
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # ============================================
    # 2. State 생성 (작업 데이터)
    # ============================================
    # 대화 이력 조회
    messages = db.query(ChatMessage).filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()

    state = MainSupervisorState(
        # DB에서 가져온 데이터
        session_id=session_id,
        user_id=session.user_id,
        user_query=user_message,
        conversation_history=[
            {"role": msg.sender_type, "content": msg.content}
            for msg in reversed(messages)
        ],

        # 작업 필드 (초기값)
        current_team="",
        team_results={},
        processing_steps=[],

        # 결과 필드 (초기값)
        final_answer="",
        confidence_score=None,

        # 메타
        timestamp=datetime.now().isoformat(),
        status="pending"
    )

    # ============================================
    # 3. Context 생성 (설정 정보)
    # ============================================
    context = AgentContext(
        # DB 매핑
        session_id=session_id,
        user_id=session.user_id,
        session_title=session.title,

        # LangGraph
        thread_id=f"thread_{session_id}",  # 체크포인팅용

        # 런타임
        request_id=str(uuid4()),
        timestamp=datetime.now().isoformat(),
        language="ko",

        # LLM 설정
        llm_context=LLMContext(
            provider="openai",
            temperature=0.7,
            user_id=str(session.user_id),
            session_id=session_id
        ),

        # 디버그
        debug_mode=False,
        trace_enabled=True
    )

    # ============================================
    # 4. LangGraph 실행 (State + Context)
    # ============================================
    config = {
        "configurable": context,
        "recursion_limit": 50
    }

    result = await supervisor.invoke(state, config=config)

    # ============================================
    # 5. 결과 DB 저장
    # ============================================
    assistant_msg = ChatMessage(
        id=str(uuid4()),
        session_id=session_id,
        sender_type="assistant",
        content=result["final_answer"],
        created_at=datetime.now()
    )
    db.add(assistant_msg)
    db.commit()

    return result
```

---

## 전체 아키텍처

### 계층 구조

```
┌─────────────────────────────────────────────────┐
│  API Layer (FastAPI)                            │
│  - ChatRequest/ChatResponse (Pydantic)          │
│  - Session 관리                                  │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│  Service Layer                                  │
│  - ChatService                                  │
│  - DB ↔ State ↔ Context 변환                    │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
┌──────────────────┐    ┌──────────────────┐
│  Database        │    │  LangGraph       │
│                  │    │                  │
│  chat_sessions   │←───│  State           │
│  chat_messages   │    │  + Context       │
│  users           │    │  + Config        │
│  real_estates    │    │                  │
└──────────────────┘    └──────────────────┘
```

### State, Context, Config의 역할

| 구분 | 타입 | 역할 | 예시 |
|------|------|------|------|
| **State** | TypedDict | 작업 데이터 전달 | user_query, search_results, final_answer |
| **Context** | TypedDict | 런타임 설정 (read-only) | session_id, user_id, language, llm_config |
| **Config** | Dict | LangGraph 실행 옵션 | recursion_limit, checkpointer, callbacks |

```python
# 실행 예시
result = await supervisor.invoke(
    state,  # ← 작업 데이터 (변경됨)
    config={
        "configurable": context,  # ← 런타임 설정 (불변)
        "recursion_limit": 50,    # ← 실행 옵션
        "callbacks": [logger]
    }
)
```

---

## 구현 예시

### 1. 통합된 Service Layer

```python
# backend/app/service_agent/services/chat_service.py

from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any

from app.models import ChatSession, ChatMessage, User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.service_agent.supervisor.team_supervisor import TeamSupervisor
from app.service_agent.foundation.separated_states import MainSupervisorState
from app.service_agent.foundation.context import AgentContext, LLMContext


class ChatService:
    """채팅 서비스 - DB, State, Context 통합"""

    def __init__(self, db: Session):
        self.db = db
        self.supervisor = TeamSupervisor(db=db)

    async def create_session(self, user_id: int, title: str = "새 대화") -> ChatSession:
        """새 채팅 세션 생성"""
        session = ChatSession(
            id=str(uuid4()),
            user_id=user_id,
            title=title,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    async def send_message(
        self,
        session_id: str,
        user_message: str,
        language: str = "ko",
        debug_mode: bool = False
    ) -> ChatMessageResponse:
        """메시지 전송 및 처리"""

        # ============================================
        # 1. 세션 검증
        # ============================================
        session = self.db.query(ChatSession).filter_by(
            id=session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # ============================================
        # 2. 사용자 메시지 DB 저장
        # ============================================
        user_msg = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            sender_type="user",
            content=user_message,
            created_at=datetime.now()
        )
        self.db.add(user_msg)
        self.db.commit()

        # ============================================
        # 3. State 생성 (DB 데이터 기반)
        # ============================================
        state = await self._create_state_from_db(
            session_id=session_id,
            user_message=user_message
        )

        # ============================================
        # 4. Context 생성 (설정 정보)
        # ============================================
        context = self._create_context(
            session=session,
            language=language,
            debug_mode=debug_mode
        )

        # ============================================
        # 5. LangGraph 실행
        # ============================================
        config = {
            "configurable": context,
            "recursion_limit": 50,
            "callbacks": []  # 필요시 콜백 추가
        }

        try:
            result_state = await self.supervisor.invoke(state, config=config)

        except Exception as e:
            # 에러 처리
            result_state = state.copy()
            result_state["status"] = "error"
            result_state["error_message"] = str(e)
            result_state["final_answer"] = "처리 중 오류가 발생했습니다."

        # ============================================
        # 6. 응답 메시지 DB 저장
        # ============================================
        assistant_msg = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            sender_type="assistant",
            content=result_state["final_answer"],
            created_at=datetime.now()
        )
        self.db.add(assistant_msg)

        # 세션 업데이트
        session.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(assistant_msg)

        # ============================================
        # 7. 응답 생성
        # ============================================
        return ChatMessageResponse(
            id=assistant_msg.id,
            session_id=session_id,
            sender_type="assistant",
            content=assistant_msg.content,
            created_at=assistant_msg.created_at,
            metadata={
                "confidence_score": result_state.get("confidence_score"),
                "sources": result_state.get("sources_used", []),
                "processing_time": result_state.get("processing_time")
            }
        )

    async def _create_state_from_db(
        self,
        session_id: str,
        user_message: str
    ) -> MainSupervisorState:
        """DB에서 State 생성"""

        # 세션 정보
        session = self.db.query(ChatSession).filter_by(
            id=session_id
        ).first()

        # 대화 이력 (최근 10개)
        messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()

        conversation_history = [
            {
                "role": msg.sender_type,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]

        # State 생성
        return {
            # DB 데이터
            "session_id": session_id,
            "user_id": session.user_id,
            "user_query": user_message,
            "conversation_history": conversation_history,

            # 작업 필드
            "current_team": "",
            "next_team": None,
            "team_results": {},
            "team_status": {},
            "processing_steps": [],
            "error_logs": [],

            # 결과 필드
            "final_answer": "",
            "confidence_score": None,
            "sources_used": [],

            # 메타데이터
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "error_message": None
        }

    def _create_context(
        self,
        session: ChatSession,
        language: str,
        debug_mode: bool
    ) -> AgentContext:
        """Context 생성"""

        return {
            # DB 매핑
            "session_id": session.id,
            "user_id": session.user_id,
            "session_title": session.title,

            # LangGraph
            "thread_id": f"thread_{session.id}",

            # 런타임
            "request_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "language": language,

            # LLM 설정
            "llm_context": {
                "provider": "openai",
                "temperature": 0.7,
                "user_id": str(session.user_id),
                "session_id": session.id
            },

            # 디버그
            "debug_mode": debug_mode,
            "trace_enabled": debug_mode
        }

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """세션 대화 이력 조회"""

        return self.db.query(ChatMessage).filter_by(
            session_id=session_id
        ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
```

### 2. API Endpoint

```python
# backend/app/api/endpoints/chat.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.service_agent.services.chat_service import ChatService
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageRequest,
    ChatMessageResponse
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    """새 채팅 세션 생성"""
    service = ChatService(db)
    session = await service.create_session(
        user_id=request.user_id,
        title=request.title or "새 대화"
    )
    return ChatSessionResponse.from_orm(session)


@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """메시지 전송"""
    service = ChatService(db)

    try:
        response = await service.send_message(
            session_id=request.session_id,
            user_message=request.content,
            language=request.language or "ko",
            debug_mode=request.debug_mode or False
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """세션 메시지 이력 조회"""
    service = ChatService(db)
    messages = await service.get_session_history(session_id, limit)
    return [ChatMessageResponse.from_orm(msg) for msg in messages]
```

---

## 체크포인팅 전략

### LangGraph 체크포인팅과 chat_messages의 관계

```python
# 두 가지 저장 방식

1. chat_messages (DB)
   - 최종 사용자 대화만 저장
   - user_msg, assistant_msg

2. LangGraph Checkpointer (별도)
   - 전체 State 스냅샷
   - 중간 상태 복구용
```

### 통합 패턴

```python
# backend/app/service_agent/supervisor/team_supervisor.py

from langgraph.checkpoint.sqlite import SqliteSaver

class TeamSupervisor:
    def __init__(self, db: Session):
        self.db = db

        # LangGraph 체크포인터 (별도 SQLite)
        self.checkpointer = SqliteSaver.from_conn_string(
            "checkpoints.db"
        )

        # 또는 동일 DB 사용 (권장)
        # self.checkpointer = PostgresSaver(db_connection)

    async def invoke(self, state, config):
        # thread_id로 체크포인팅
        thread_id = config["configurable"].get("thread_id")

        config_with_checkpoint = {
            **config,
            "thread_id": thread_id  # 체크포인트 식별자
        }

        # State 실행 (자동 체크포인팅)
        return await self.app.ainvoke(state, config_with_checkpoint)

    async def resume_from_checkpoint(self, thread_id: str):
        """체크포인트에서 재개"""
        # 마지막 State 복구
        state = self.checkpointer.get(thread_id)

        # 계속 실행
        return await self.app.ainvoke(state, {"thread_id": thread_id})
```

---

## 요약

### 1. chat_sessions/chat_messages와 State 관계

| DB | State | 관계 |
|----|-------|------|
| `chat_sessions.id` | `state["session_id"]` | 동일 값 |
| `chat_messages.content` (user) | `state["user_query"]` | 최신 메시지 |
| `chat_messages` (전체) | `state["conversation_history"]` | 조회 후 변환 |
| `chat_messages.content` (assistant) | `state["final_answer"]` | 결과 저장 |

### 2. Context/Config 통합

```python
# Context (설정)
context = {
    "session_id": chat_sessions.id,
    "user_id": users.id,
    "language": "ko",
    "llm_context": {...}
}

# State (작업 데이터)
state = {
    "session_id": chat_sessions.id,  # Context와 동일
    "user_query": "...",
    "final_answer": ""
}

# 실행
result = await supervisor.invoke(
    state,
    config={"configurable": context}
)
```

### 3. 전체 흐름

```
1. 사용자 메시지 → chat_messages (DB)
2. DB 조회 → State + Context 생성
3. LangGraph 실행 (State + Context)
4. 결과 → chat_messages (DB)
```

### 4. 핵심 원칙

✅ `chat_sessions.id` = State의 `session_id` = Context의 `session_id`
✅ `chat_messages`는 대화 이력의 영속 계층
✅ State는 작업 데이터 (임시)
✅ Context는 설정 정보 (불변)
✅ 최종 답변만 `chat_messages`로 저장

---

*작성일: 2025-10-06*
*버전: 1.0*
