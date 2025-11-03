# Session Manager vs Long-term Memory 아키텍처 설계서 v1.0

**작성일**: 2025-10-13
**버전**: v1.0
**작성자**: Claude Code
**목적**: SessionManager와 Long-term Memory의 역할 구분 및 PostgreSQL 통합 아키텍처 설계

**관련 문서**:
- [State/Context 설계 계획서 v2.0](./plan_of_state_context_design_v2.md)

---

## 📋 목차

1. [개요](#개요)
2. [SessionManager 상세 설계](#sessionmanager-상세-설계)
3. [Long-term Memory 상세 설계](#long-term-memory-상세-설계)
4. [두 시스템의 상호작용](#두-시스템의-상호작용)
5. [PostgreSQL 통합 계획](#postgresql-통합-계획)
6. [구현 로드맵](#구현-로드맵)
7. [API 설계](#api-설계)

---

## 1. 개요

### 1.1 배경

현재 시스템은 세 가지 저장소를 사용합니다:

1. **SessionManager** (SQLite) - WebSocket 세션 관리
2. **Checkpointer** (SQLite) - LangGraph State 저장
3. **Long-term Memory** (미구현) - 대화 이력 및 학습 데이터

**문제점**:
- SQLite 3개 사용 → 관리 복잡도 증가
- Long-term Memory 미구현 → 개인화 불가능
- SessionManager와 Memory의 역할 혼동

**해결 방안**:
- 모든 저장소를 PostgreSQL로 통합
- SessionManager와 Memory의 역할 명확히 구분
- 통합 아키텍처 설계

---

### 1.2 핵심 개념 비교

| 구분 | SessionManager | Long-term Memory |
|------|----------------|------------------|
| **역할** | 🔐 WebSocket 연결 세션 관리 | 🧠 대화 내용 및 학습 데이터 저장 |
| **목적** | 인증 및 세션 추적 (인프라) | 개인화 및 문맥 이해 (비즈니스) |
| **데이터** | session_id, user_id, 만료시간 | 대화 이력, 선호도, 엔티티 추적 |
| **생명주기** | 단기 (24시간 TTL) | 장기 (영구 저장) |
| **삭제 시점** | 세션 만료 시 자동 삭제 | 사용자 계정 삭제 시까지 보관 |
| **비유** | 출입증, 번호표 | 단골 카드, 주문 이력 |
| **현재 상태** | ✅ 구현됨 (SQLite) | ⏳ 미구현 |
| **DB** | PostgreSQL 전환 예정 | PostgreSQL 신규 구축 |

---

### 1.3 사용 시나리오 예시

#### 시나리오 1: 첫 방문 사용자 (비로그인)

```
1. 사용자가 웹사이트 접속
   ↓
SessionManager.create_session(user_id=None)
   → session_id: "session-xyz-789" 생성
   → 24시간 유효
   ↓
2. 질문: "강남구 아파트 찾아줘"
   ↓
TeamSupervisor 처리
   SharedState {
       session_id: "session-xyz-789",
       user_id: None,  # 로그인 안함
       query: "강남구 아파트 찾아줘"
   }
   ↓
3. 응답: "강남구 아파트 10건 찾았습니다"
   ↓
Memory 저장 ❌ (user_id 없으므로 저장 안함)
   → 일회성 대화만 처리
   ↓
4. 24시간 후 session 자동 만료
```

---

#### 시나리오 2: 로그인 사용자 (단골)

```
1. 로그인 후 접속
   ↓
SessionManager.create_session(user_id=42)
   → session_id: "session-abc-123"
   → user_id: 42 연결
   ↓
2. 질문: "아파트 찾아줘" (지역 미지정)
   ↓
Planning Agent
   ↓ Memory 조회
Memory.get_user_preferences(user_id=42)
   → preferred_regions: ["강남구", "서초구"]
   → 자주 검색하는 지역 확인
   ↓
Planning Agent: "이 사용자는 주로 강남구를 검색하니까 강남구로 검색하자"
   ↓
3. 응답: "강남구 아파트 10건 찾았습니다"
   ↓
Memory 저장 ✅
   ConversationMemory: 대화 내역 저장
   UserPreference: 강남구 검색 카운트 +1
   EntityMemory: "강남구" 엔티티 업데이트
```

---

#### 시나리오 3: 문맥 참조 (과거 대화 기억)

```
1. 첫 번째 질문
user: "강남구 5억 이하 아파트 찾아줘"
   ↓
assistant: "강남 아파트 A, B, C 3건 찾았습니다"
   ↓
Memory.store_conversation(
    session_id="session-abc-123",
    user_id=42,
    query="강남구 5억 이하 아파트 찾아줘",
    response="강남 아파트 A, B, C 3건...",
    entities=["강남구", "5억", "아파트"]
)
   ↓
2. 10분 후, 두 번째 질문
user: "첫 번째 매물 상세히 보여줘"
   ↓
Planning Agent
   ↓ Memory 조회
Memory.load_recent_context(user_id=42, limit=1)
   → 이전 대화: "강남 아파트 A, B, C"
   → "첫 번째 매물" = 강남 아파트 A
   ↓
assistant: "강남 아파트 A 상세 정보입니다..."
```

---

## 2. SessionManager 상세 설계

### 2.1 현재 구조 (SQLite)

**파일**: `backend/app/api/session_manager.py`
**DB**: `backend/data/system/sessions/sessions.db`

**테이블 스키마**:
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,          -- "session-{uuid}"
    user_id TEXT,                         -- 사용자 ID (로그인 시)
    metadata TEXT,                        -- JSON 메타데이터
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,        -- 24시간 후 자동 만료
    last_activity TIMESTAMP NOT NULL,
    request_count INTEGER DEFAULT 0
);

CREATE INDEX idx_expires_at ON sessions(expires_at);
```

**주요 메서드**:
```python
class SessionManager:
    def create_session(user_id: Optional[str], metadata: Optional[Dict]) -> Tuple[str, datetime]
    def get_session(session_id: str) -> Optional[Dict]
    def update_activity(session_id: str) -> bool
    def delete_session(session_id: str) -> bool
    def cleanup_expired_sessions() -> int  # 만료된 세션 정리
    def get_user_sessions(user_id: str) -> List[Dict]
```

---

### 2.2 PostgreSQL 전환 설계

**목표**: SQLite → PostgreSQL 마이그레이션

#### 2.2.1 DB 모델 설계

**파일**: `backend/app/models/session.py` (신규)

```python
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.postgre_db import Base
import uuid

class WebSocketSession(Base):
    """WebSocket 세션 관리 (기존 SessionManager)"""
    __tablename__ = "websocket_sessions"

    # Primary Key
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User 연결
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # nullable=True: 비로그인 사용자도 접속 가능

    # 메타데이터
    metadata = Column(JSON, default={})

    # 타임스탬프
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)  # created_at + 24h
    last_activity = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 통계
    request_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="websocket_sessions")

    # Indexes
    __table_args__ = (
        Index('idx_expires_at', 'expires_at'),  # 만료 세션 정리용
        Index('idx_user_sessions', 'user_id', 'created_at'),  # 사용자별 세션 조회
    )
```

**Pydantic Schema**:

**파일**: `backend/app/schemas/session.py` (신규)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class WebSocketSessionCreate(BaseModel):
    user_id: Optional[int] = None
    metadata: Optional[dict] = {}

class WebSocketSessionResponse(BaseModel):
    session_id: UUID
    user_id: Optional[int]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    request_count: int

    class Config:
        from_attributes = True
```

---

#### 2.2.2 SessionManager 리팩토링

**파일**: `backend/app/api/session_manager.py` (수정)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgre_db import SessionLocal
from app.models.session import WebSocketSession
from datetime import datetime, timedelta
import uuid

class SessionManager:
    """PostgreSQL 기반 세션 관리"""

    def __init__(self, session_ttl_hours: int = 24):
        self.session_ttl = timedelta(hours=session_ttl_hours)

    async def create_session(
        self,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """
        새 세션 생성 (PostgreSQL)

        Returns:
            (session_id, expires_at)
        """
        async with SessionLocal() as db:
            session_id = uuid.uuid4()
            created_at = datetime.now()
            expires_at = created_at + self.session_ttl

            ws_session = WebSocketSession(
                session_id=session_id,
                user_id=user_id,
                metadata=metadata or {},
                created_at=created_at,
                expires_at=expires_at,
                last_activity=created_at,
                request_count=0
            )

            db.add(ws_session)
            await db.commit()
            await db.refresh(ws_session)

            logger.info(f"Session created: {session_id}, user_id: {user_id}")
            return str(session_id), expires_at

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 조회"""
        async with SessionLocal() as db:
            result = await db.execute(
                select(WebSocketSession).where(
                    WebSocketSession.session_id == uuid.UUID(session_id)
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                return None

            # 만료 체크
            if session.expires_at < datetime.now():
                logger.info(f"Session expired: {session_id}")
                await self.delete_session(session_id)
                return None

            return {
                "session_id": str(session.session_id),
                "user_id": session.user_id,
                "metadata": session.metadata,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
                "last_activity": session.last_activity,
                "request_count": session.request_count
            }

    async def update_activity(self, session_id: str) -> bool:
        """세션 활동 업데이트"""
        async with SessionLocal() as db:
            result = await db.execute(
                update(WebSocketSession)
                .where(WebSocketSession.session_id == uuid.UUID(session_id))
                .values(
                    last_activity=datetime.now(),
                    request_count=WebSocketSession.request_count + 1
                )
            )
            await db.commit()
            return result.rowcount > 0

    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        async with SessionLocal() as db:
            result = await db.execute(
                delete(WebSocketSession)
                .where(WebSocketSession.session_id == uuid.UUID(session_id))
            )
            await db.commit()
            return result.rowcount > 0

    async def cleanup_expired_sessions(self) -> int:
        """만료된 세션 정리 (Cron job)"""
        async with SessionLocal() as db:
            result = await db.execute(
                delete(WebSocketSession)
                .where(WebSocketSession.expires_at < datetime.now())
            )
            await db.commit()
            count = result.rowcount
            logger.info(f"Cleaned up {count} expired sessions")
            return count

    async def get_user_sessions(self, user_id: int) -> List[Dict]:
        """사용자의 모든 활성 세션 조회"""
        async with SessionLocal() as db:
            result = await db.execute(
                select(WebSocketSession)
                .where(
                    WebSocketSession.user_id == user_id,
                    WebSocketSession.expires_at > datetime.now()
                )
                .order_by(WebSocketSession.created_at.desc())
            )
            sessions = result.scalars().all()

            return [
                {
                    "session_id": str(s.session_id),
                    "created_at": s.created_at,
                    "expires_at": s.expires_at,
                    "last_activity": s.last_activity,
                    "request_count": s.request_count
                }
                for s in sessions
            ]
```

---

#### 2.2.3 마이그레이션 계획

**단계 1: DB 모델 생성**
```bash
# Alembic migration 생성
alembic revision --autogenerate -m "Add WebSocketSession model"
alembic upgrade head
```

**단계 2: SessionManager 교체**
```python
# 기존 SQLite SessionManager 사용 코드
session_manager = SessionManager(db_path="sessions.db")

# PostgreSQL SessionManager로 교체
session_manager = SessionManager(session_ttl_hours=24)
# DB 경로 불필요 (PostgreSQL 연결은 app.db.postgre_db에서 관리)
```

**단계 3: 기존 SQLite 데이터 마이그레이션 (선택)**
```python
# 기존 sessions.db에서 활성 세션 추출
import sqlite3
conn = sqlite3.connect("backend/data/system/sessions/sessions.db")
active_sessions = conn.execute(
    "SELECT * FROM sessions WHERE expires_at > datetime('now')"
).fetchall()

# PostgreSQL로 삽입
for session in active_sessions:
    await session_manager.create_session(
        user_id=session["user_id"],
        metadata=json.loads(session["metadata"])
    )
```

**단계 4: 테스트 및 배포**
- [ ] Unit Test: SessionManager 메서드 테스트
- [ ] Integration Test: WebSocket 연결 시나리오
- [ ] Load Test: 동시 세션 1000개 처리
- [ ] 배포 후 모니터링

---

## 3. Long-term Memory 상세 설계

### 3.1 개요

**목적**: 대화 이력, 사용자 선호도, 학습된 패턴을 영구 저장하여 개인화된 서비스 제공

**주요 기능**:
1. **대화 이력 저장**: 모든 대화 턴 기록
2. **사용자 선호도 학습**: 자주 검색하는 지역, 가격대, 매물 타입
3. **엔티티 추적**: 사용자가 자주 언급하는 엔티티 (지역, 매물 등)
4. **문맥 이해**: 과거 대화를 참조하여 "그 매물" 같은 대명사 해석

---

### 3.2 DB 모델 설계

#### 3.2.1 ConversationMemory (대화 이력)

**파일**: `backend/app/models/memory.py` (신규)

```python
from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base

class ConversationMemory(Base):
    """대화 이력 메모리"""
    __tablename__ = "conversation_memories"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Session & User 연결
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 대화 턴 정보
    turn_number = Column(Integer, nullable=False)  # 세션 내 몇 번째 대화인지
    user_query = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)

    # 의도 분석 결과
    intent_type = Column(String(50))  # "legal_consult", "market_inquiry", "property_search" 등
    intent_confidence = Column(Float)  # 0.0 ~ 1.0

    # 실행 메타데이터
    teams_used = Column(ARRAY(String))  # ["search", "analysis"]
    tools_used = Column(ARRAY(String))  # ["legal_search", "market_data"]
    execution_time_ms = Column(Integer)  # 실행 시간 (밀리초)

    # 추출된 엔티티
    entities = Column(JSON)  # {"location": ["강남구"], "price": ["5억"], "property_type": ["아파트"]}

    # 타임스탬프
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="conversation_memories")
    user = relationship("User", back_populates="conversation_memories")

    # Indexes
    __table_args__ = (
        Index('idx_session_turn', 'session_id', 'turn_number'),  # 세션별 대화 순서 조회
        Index('idx_user_recent', 'user_id', 'created_at'),       # 사용자별 최근 대화 조회
        Index('idx_intent_type', 'intent_type'),                 # 의도별 대화 통계
    )
```

---

#### 3.2.2 UserPreference (사용자 선호도)

```python
class UserPreference(Base):
    """사용자 선호도 메모리 (학습된 패턴)"""
    __tablename__ = "user_preferences"

    # Primary Key
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # 지역 선호도
    preferred_regions = Column(ARRAY(String))  # ["강남구", "서초구"]
    region_search_counts = Column(JSON)  # {"강남구": 25, "서초구": 10}

    # 가격 선호도
    preferred_price_range = Column(JSON)  # {"min": 40000, "max": 60000} (만원)
    avg_searched_price = Column(Integer)  # 평균 검색 가격

    # 매물 타입 선호도
    preferred_property_types = Column(ARRAY(String))  # ["APARTMENT", "OFFICETEL"]
    property_type_counts = Column(JSON)  # {"APARTMENT": 30, "OFFICETEL": 5}

    # 검색 패턴
    frequent_queries = Column(JSON)  # [{"query": "강남구 아파트", "count": 15, "last_searched": "2025-10-13"}]
    search_keywords = Column(ARRAY(String))  # ["지하철", "학교", "신축"]

    # 매물 상호작용
    viewed_properties = Column(ARRAY(Integer))  # 조회한 매물 ID 목록 (최근 100개)
    favorited_properties = Column(ARRAY(Integer))  # 찜한 매물 ID 목록

    # 시간대 패턴
    active_hours = Column(JSON)  # {"morning": 5, "afternoon": 10, "evening": 20, "night": 3}

    # 최종 업데이트
    last_search_context = Column(JSON)  # 마지막 검색 컨텍스트 (문맥 유지용)

    # 타임스탬프
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preference")
```

---

#### 3.2.3 EntityMemory (엔티티 추적)

```python
class EntityMemory(Base):
    """엔티티 추출 및 추적 메모리"""
    __tablename__ = "entity_memories"

    # Primary Key
    id = Column(Integer, primary_key=True)

    # User 연결
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 엔티티 정보
    entity_type = Column(String(50), nullable=False)  # "location", "price", "property_id", "date" 등
    entity_value = Column(String(255), nullable=False)  # "강남구", "5억", "123456"
    entity_normalized = Column(String(255))  # 정규화된 값 ("5억" → "500000000")

    # 문맥 정보
    entity_context = Column(Text)  # 엔티티가 언급된 문맥 (최근 3개)
    related_entities = Column(JSON)  # 함께 언급된 다른 엔티티 {"price": ["5억"], "property_type": ["아파트"]}

    # 빈도 및 중요도
    mention_count = Column(Integer, default=1)  # 언급 횟수
    importance_score = Column(Float, default=1.0)  # 중요도 점수 (빈도 기반)

    # 타임스탬프
    first_mentioned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_mentioned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="entity_memories")

    # Indexes
    __table_args__ = (
        Index('idx_entity_lookup', 'user_id', 'entity_type', 'entity_value'),  # 빠른 엔티티 조회
        Index('idx_importance', 'user_id', 'importance_score'),                 # 중요 엔티티 정렬
    )
```

---

### 3.3 Memory Service 구현

**파일**: `backend/app/service_agent/memory/memory_service.py` (신규)

```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func
from app.db.postgre_db import SessionLocal
from app.models.memory import ConversationMemory, UserPreference, EntityMemory

class LongTermMemoryService:
    """Long-term Memory 관리 서비스"""

    # ============================================================================
    # 1. 대화 이력 관리
    # ============================================================================

    async def store_conversation(
        self,
        session_id: str,
        user_id: int,
        turn_number: int,
        user_query: str,
        assistant_response: str,
        intent_type: str,
        intent_confidence: float,
        teams_used: List[str],
        tools_used: List[str],
        execution_time_ms: int,
        entities: Dict[str, List[str]]
    ) -> int:
        """
        대화 턴 저장

        Returns:
            conversation_id
        """
        async with SessionLocal() as db:
            conversation = ConversationMemory(
                session_id=session_id,
                user_id=user_id,
                turn_number=turn_number,
                user_query=user_query,
                assistant_response=assistant_response,
                intent_type=intent_type,
                intent_confidence=intent_confidence,
                teams_used=teams_used,
                tools_used=tools_used,
                execution_time_ms=execution_time_ms,
                entities=entities,
                created_at=datetime.now()
            )

            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

            logger.info(f"Conversation stored: user={user_id}, turn={turn_number}")
            return conversation.id

    async def load_recent_context(
        self,
        user_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 컨텍스트 로드

        Args:
            user_id: 사용자 ID
            limit: 최근 N개 대화

        Returns:
            대화 이력 리스트 (최신순)
        """
        async with SessionLocal() as db:
            result = await db.execute(
                select(ConversationMemory)
                .where(ConversationMemory.user_id == user_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(limit)
            )
            conversations = result.scalars().all()

            return [
                {
                    "turn_number": c.turn_number,
                    "user_query": c.user_query,
                    "assistant_response": c.assistant_response,
                    "intent_type": c.intent_type,
                    "entities": c.entities,
                    "created_at": c.created_at.isoformat()
                }
                for c in reversed(conversations)  # 오래된 것부터 정렬
            ]

    async def get_session_conversations(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """특정 세션의 전체 대화 이력 조회"""
        async with SessionLocal() as db:
            result = await db.execute(
                select(ConversationMemory)
                .where(ConversationMemory.session_id == session_id)
                .order_by(ConversationMemory.turn_number)
            )
            conversations = result.scalars().all()

            return [
                {
                    "turn_number": c.turn_number,
                    "user_query": c.user_query,
                    "assistant_response": c.assistant_response,
                    "created_at": c.created_at.isoformat()
                }
                for c in conversations
            ]

    # ============================================================================
    # 2. 사용자 선호도 관리
    # ============================================================================

    async def get_user_preferences(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """사용자 선호도 조회"""
        async with SessionLocal() as db:
            result = await db.execute(
                select(UserPreference)
                .where(UserPreference.user_id == user_id)
            )
            pref = result.scalar_one_or_none()

            if not pref:
                return None

            return {
                "preferred_regions": pref.preferred_regions,
                "preferred_price_range": pref.preferred_price_range,
                "preferred_property_types": pref.preferred_property_types,
                "frequent_queries": pref.frequent_queries,
                "search_keywords": pref.search_keywords
            }

    async def update_region_preference(
        self,
        user_id: int,
        region: str
    ):
        """지역 검색 카운트 업데이트"""
        async with SessionLocal() as db:
            # 기존 선호도 조회
            result = await db.execute(
                select(UserPreference)
                .where(UserPreference.user_id == user_id)
            )
            pref = result.scalar_one_or_none()

            if not pref:
                # 첫 선호도 생성
                pref = UserPreference(
                    user_id=user_id,
                    preferred_regions=[region],
                    region_search_counts={region: 1}
                )
                db.add(pref)
            else:
                # 카운트 업데이트
                counts = pref.region_search_counts or {}
                counts[region] = counts.get(region, 0) + 1

                # 상위 3개 지역 추출
                top_regions = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:3]

                await db.execute(
                    update(UserPreference)
                    .where(UserPreference.user_id == user_id)
                    .values(
                        preferred_regions=[r[0] for r in top_regions],
                        region_search_counts=counts,
                        updated_at=datetime.now()
                    )
                )

            await db.commit()

    async def update_price_preference(
        self,
        user_id: int,
        min_price: Optional[int],
        max_price: Optional[int]
    ):
        """가격 범위 선호도 업데이트"""
        async with SessionLocal() as db:
            result = await db.execute(
                select(UserPreference)
                .where(UserPreference.user_id == user_id)
            )
            pref = result.scalar_one_or_none()

            price_range = {}
            if min_price:
                price_range["min"] = min_price
            if max_price:
                price_range["max"] = max_price

            if not pref:
                pref = UserPreference(
                    user_id=user_id,
                    preferred_price_range=price_range
                )
                db.add(pref)
            else:
                await db.execute(
                    update(UserPreference)
                    .where(UserPreference.user_id == user_id)
                    .values(
                        preferred_price_range=price_range,
                        updated_at=datetime.now()
                    )
                )

            await db.commit()

    async def add_viewed_property(
        self,
        user_id: int,
        property_id: int
    ):
        """조회한 매물 추가 (최근 100개 유지)"""
        async with SessionLocal() as db:
            result = await db.execute(
                select(UserPreference)
                .where(UserPreference.user_id == user_id)
            )
            pref = result.scalar_one_or_none()

            if not pref:
                pref = UserPreference(
                    user_id=user_id,
                    viewed_properties=[property_id]
                )
                db.add(pref)
            else:
                viewed = pref.viewed_properties or []
                viewed.append(property_id)
                viewed = viewed[-100:]  # 최근 100개만 유지

                await db.execute(
                    update(UserPreference)
                    .where(UserPreference.user_id == user_id)
                    .values(
                        viewed_properties=viewed,
                        updated_at=datetime.now()
                    )
                )

            await db.commit()

    # ============================================================================
    # 3. 엔티티 추적 관리
    # ============================================================================

    async def update_entity_mentions(
        self,
        user_id: int,
        entities: Dict[str, List[str]],
        context: str
    ):
        """
        엔티티 언급 업데이트

        Args:
            user_id: 사용자 ID
            entities: {"location": ["강남구"], "price": ["5억"], ...}
            context: 엔티티가 언급된 문맥
        """
        async with SessionLocal() as db:
            for entity_type, values in entities.items():
                for value in values:
                    # 기존 엔티티 조회
                    result = await db.execute(
                        select(EntityMemory)
                        .where(
                            EntityMemory.user_id == user_id,
                            EntityMemory.entity_type == entity_type,
                            EntityMemory.entity_value == value
                        )
                    )
                    entity = result.scalar_one_or_none()

                    if not entity:
                        # 새 엔티티 생성
                        entity = EntityMemory(
                            user_id=user_id,
                            entity_type=entity_type,
                            entity_value=value,
                            entity_context=context,
                            mention_count=1,
                            importance_score=1.0,
                            first_mentioned_at=datetime.now(),
                            last_mentioned_at=datetime.now()
                        )
                        db.add(entity)
                    else:
                        # 기존 엔티티 업데이트
                        new_count = entity.mention_count + 1
                        await db.execute(
                            update(EntityMemory)
                            .where(EntityMemory.id == entity.id)
                            .values(
                                mention_count=new_count,
                                importance_score=float(new_count),  # 간단한 중요도 계산
                                entity_context=context,
                                last_mentioned_at=datetime.now()
                            )
                        )

            await db.commit()

    async def get_important_entities(
        self,
        user_id: int,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        중요 엔티티 조회 (빈도 기반)

        Args:
            user_id: 사용자 ID
            entity_type: 엔티티 타입 필터 (None이면 전체)
            limit: 최대 개수

        Returns:
            엔티티 리스트 (중요도 순)
        """
        async with SessionLocal() as db:
            query = select(EntityMemory).where(EntityMemory.user_id == user_id)

            if entity_type:
                query = query.where(EntityMemory.entity_type == entity_type)

            query = query.order_by(EntityMemory.importance_score.desc()).limit(limit)

            result = await db.execute(query)
            entities = result.scalars().all()

            return [
                {
                    "entity_type": e.entity_type,
                    "entity_value": e.entity_value,
                    "mention_count": e.mention_count,
                    "importance_score": e.importance_score,
                    "last_mentioned_at": e.last_mentioned_at.isoformat()
                }
                for e in entities
            ]

    # ============================================================================
    # 4. 통계 및 분석
    # ============================================================================

    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """사용자 활동 통계"""
        async with SessionLocal() as db:
            # 총 대화 수
            total_conversations = await db.scalar(
                select(func.count(ConversationMemory.id))
                .where(ConversationMemory.user_id == user_id)
            )

            # 의도별 통계
            intent_stats = await db.execute(
                select(
                    ConversationMemory.intent_type,
                    func.count(ConversationMemory.id).label('count')
                )
                .where(ConversationMemory.user_id == user_id)
                .group_by(ConversationMemory.intent_type)
            )
            intent_distribution = {row.intent_type: row.count for row in intent_stats}

            # 최근 활동
            last_conversation = await db.execute(
                select(ConversationMemory)
                .where(ConversationMemory.user_id == user_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(1)
            )
            last = last_conversation.scalar_one_or_none()

            return {
                "total_conversations": total_conversations,
                "intent_distribution": intent_distribution,
                "last_activity": last.created_at.isoformat() if last else None
            }
```

---

### 3.4 Planning Agent 통합

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py` (수정)

```python
class PlanningAgent:
    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context
        self.llm_service = LLMService(llm_context=llm_context)
        self.memory_service = LongTermMemoryService()  # ✅ 추가

    async def analyze_intent_with_memory(
        self,
        query: str,
        user_id: Optional[int],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Memory를 활용한 의도 분석

        1. 최근 대화 컨텍스트 로드
        2. 사용자 선호도 로드
        3. 엔티티 추적
        4. 개인화된 의도 분석
        """

        # 1. 과거 대화 컨텍스트 (user_id 있을 때만)
        recent_context = []
        user_preferences = {}

        if user_id:
            recent_context = await self.memory_service.load_recent_context(
                user_id=user_id,
                limit=3  # 최근 3개 대화
            )

            user_preferences = await self.memory_service.get_user_preferences(user_id)

        # 2. LLM에게 컨텍스트 전달
        enhanced_prompt = f"""
        사용자 질문: {query}

        과거 대화 컨텍스트:
        {self._format_context(recent_context)}

        사용자 선호도:
        - 자주 검색하는 지역: {user_preferences.get('preferred_regions', [])}
        - 선호 가격대: {user_preferences.get('preferred_price_range', {})}
        - 선호 매물 타입: {user_preferences.get('preferred_property_types', [])}

        위 정보를 참고하여 사용자의 의도를 분석하세요.
        지역이 명시되지 않았다면 선호 지역을 제안하세요.
        """

        # 3. 의도 분석
        intent_result = await self.llm_service.analyze_intent(enhanced_prompt)

        # 4. 엔티티 추출 및 추적
        if user_id:
            entities = self._extract_entities(query)
            await self.memory_service.update_entity_mentions(
                user_id=user_id,
                entities=entities,
                context=query
            )

        return intent_result

    def _format_context(self, conversations: List[Dict]) -> str:
        """대화 컨텍스트 포맷팅"""
        if not conversations:
            return "없음"

        formatted = []
        for conv in conversations:
            formatted.append(f"- User: {conv['user_query']}")
            formatted.append(f"  Assistant: {conv['assistant_response'][:100]}...")

        return "\n".join(formatted)

    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """간단한 엔티티 추출 (정규식 기반)"""
        import re

        entities = {
            "location": [],
            "price": [],
            "property_type": [],
            "area": []
        }

        # 지역 추출
        regions = ["강남구", "서초구", "송파구", "강동구", "마포구", "용산구", "중구"]
        for region in regions:
            if region in query:
                entities["location"].append(region)

        # 가격 추출
        price_match = re.findall(r'(\d+)억', query)
        entities["price"] = [f"{p}억" for p in price_match]

        # 매물 타입 추출
        if "아파트" in query:
            entities["property_type"].append("아파트")
        if "오피스텔" in query:
            entities["property_type"].append("오피스텔")

        return entities
```

---

## 4. 두 시스템의 상호작용

### 4.1 데이터 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                        User 접속                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  SessionManager: WebSocket 세션 생성                          │
│  → session_id: "session-abc-123" (24h TTL)                   │
│  → user_id: 42 (로그인 사용자)                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  User Query: "아파트 찾아줘" (지역 미지정)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Planning Agent                                               │
│  ├─ Memory.load_recent_context(user_id=42)                   │
│  │  → 최근 3개 대화 로드                                      │
│  ├─ Memory.get_user_preferences(user_id=42)                  │
│  │  → preferred_regions: ["강남구", "서초구"]                 │
│  └─ LLM: "이 사용자는 주로 강남구를 검색함"                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Search Execution                                             │
│  → "강남구 아파트" 검색 (지역 자동 추가)                      │
│  → 10건 발견                                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Response Generation                                          │
│  → "강남구에서 아파트 10건을 찾았습니다"                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Memory: 대화 저장                                            │
│  ├─ ConversationMemory.store(...)                            │
│  │  → query: "아파트 찾아줘"                                  │
│  │  → response: "강남구 아파트 10건..."                       │
│  ├─ UserPreference.update_region("강남구")                   │
│  │  → 강남구 카운트 +1                                        │
│  └─ EntityMemory.update(entity_type="location", value="강남구")│
│     → 강남구 언급 +1                                          │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.2 실제 코드 통합 예시

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py` (수정)

```python
class TeamBasedSupervisor:
    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        # ... 기존 코드 ...

        # Memory Service 추가
        self.memory_service = LongTermMemoryService()  # ✅ 추가

    async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        Planning 노드 - Memory 통합
        """
        query = state["query"]
        session_id = state["session_id"]
        user_id = state.get("user_id")  # v2.0에서 추가한 필드

        # 1. Memory를 활용한 의도 분석
        intent_result = await self.planning_agent.analyze_intent_with_memory(
            query=query,
            user_id=user_id,
            session_id=session_id
        )

        # 2. 계획 수립
        plan = await self.planning_agent.create_execution_plan(intent_result)

        state["planning_state"] = {
            "analyzed_intent": intent_result,
            "execution_steps": plan["execution_steps"]
        }

        return state

    async def generate_response_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        Response 생성 노드 - Memory 저장
        """
        # ... 기존 응답 생성 로직 ...

        response = await self._generate_llm_response(state)
        state["final_response"] = response

        # Memory 저장 (user_id 있을 때만)
        user_id = state.get("user_id")
        if user_id:
            session_id = state["session_id"]
            query = state["query"]

            # 현재 세션의 턴 번호 계산
            turn_number = await self._get_turn_number(session_id)

            # 대화 저장
            await self.memory_service.store_conversation(
                session_id=session_id,
                user_id=user_id,
                turn_number=turn_number,
                user_query=query,
                assistant_response=response["content"],
                intent_type=state["planning_state"]["analyzed_intent"]["intent"],
                intent_confidence=state["planning_state"]["analyzed_intent"]["confidence"],
                teams_used=state.get("active_teams", []),
                tools_used=self._extract_tools_used(state),
                execution_time_ms=int(state.get("total_execution_time", 0) * 1000),
                entities=self._extract_entities(query)
            )

            # 선호도 업데이트
            await self._update_preferences(user_id, query, state)

        return state

    async def _update_preferences(self, user_id: int, query: str, state: MainSupervisorState):
        """사용자 선호도 업데이트"""
        # 지역 추출
        regions = self._extract_regions(query)
        for region in regions:
            await self.memory_service.update_region_preference(user_id, region)

        # 가격 추출
        price_range = self._extract_price_range(query)
        if price_range:
            await self.memory_service.update_price_preference(
                user_id,
                price_range.get("min"),
                price_range.get("max")
            )

        # 조회한 매물 추가
        property_ids = self._extract_property_ids(state)
        for prop_id in property_ids:
            await self.memory_service.add_viewed_property(user_id, prop_id)
```

---

## 5. PostgreSQL 통합 계획

### 5.1 통합 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   User 관련       │  │  Real Estate      │                 │
│  ├──────────────────┤  ├──────────────────┤                 │
│  │ users            │  │ real_estates     │                 │
│  │ user_profiles    │  │ transactions     │                 │
│  │ local_auths      │  │ regions          │                 │
│  │ social_auths     │  │ trust_scores     │                 │
│  │ user_favorites   │  │ nearby_facilities│                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   Chat 관련       │  │  Memory 관련      │                 │
│  ├──────────────────┤  ├──────────────────┤                 │
│  │ chat_sessions    │  │ conversation_    │                 │
│  │ chat_messages    │  │   memories       │                 │
│  │                  │  │ user_preferences │                 │
│  │                  │  │ entity_memories  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Session 관련      │  │ Checkpoint 관련   │                 │
│  ├──────────────────┤  ├──────────────────┤                 │
│  │ websocket_       │  │ langgraph_       │                 │
│  │   sessions       │  │   checkpoints    │                 │
│  │                  │  │ (LangGraph 관리)  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

### 5.2 마이그레이션 단계

#### Phase 4-1: Checkpointer 전환 (1주일)

**목표**: SQLite AsyncSqliteSaver → PostgreSQL AsyncPostgresSaver

**작업 목록**:
1. **패키지 설치**
   ```bash
   pip install "langgraph[postgres]"
   ```

2. **checkpointer.py 수정**
   ```python
   # 변경 전
   from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

   # 변경 후
   from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
   ```

3. **연결 문자열 변경**
   ```python
   # 변경 전
   db_path = "backend/data/system/checkpoints/default_checkpoint.db"
   checkpointer = AsyncSqliteSaver.from_conn_string(str(db_path))

   # 변경 후
   from app.db.postgre_db import DATABASE_URL
   checkpointer = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
   ```

4. **테스트**
   - [ ] Checkpoint 저장/로드 정상 동작
   - [ ] 멀티 세션 동시 처리
   - [ ] 성능 비교 (SQLite vs PostgreSQL)

**예상 소요 시간**: 3일 (개발 1일, 테스트 2일)

---

#### Phase 4-2: SessionManager 전환 (1주일)

**목표**: SQLite SessionManager → PostgreSQL WebSocketSession

**작업 목록**:
1. **DB 모델 생성** (`models/session.py`)
2. **Alembic migration**
   ```bash
   alembic revision --autogenerate -m "Add WebSocketSession"
   alembic upgrade head
   ```

3. **SessionManager 리팩토링** (`api/session_manager.py`)
4. **기존 SQLite 데이터 마이그레이션** (선택)
5. **테스트**
   - [ ] 세션 생성/조회/삭제
   - [ ] WebSocket 연결 시나리오
   - [ ] 만료 세션 정리 Cron job

**예상 소요 시간**: 4일 (개발 2일, 테스트 2일)

---

#### Phase 5: Long-term Memory 구현 (2주일)

**목표**: Long-term Memory 시스템 구축

**작업 목록**:

**Week 1: DB 모델 및 Service 구현**
1. **DB 모델 생성** (`models/memory.py`)
   - ConversationMemory
   - UserPreference
   - EntityMemory

2. **Alembic migration**
   ```bash
   alembic revision --autogenerate -m "Add Long-term Memory models"
   alembic upgrade head
   ```

3. **Memory Service 구현** (`service_agent/memory/memory_service.py`)
   - 대화 저장/조회
   - 선호도 관리
   - 엔티티 추적

4. **Unit Test 작성**

**Week 2: Planning Agent 통합 및 테스트**
5. **Planning Agent 수정** (`cognitive_agents/planning_agent.py`)
   - Memory 조회 로직 추가
   - 개인화된 의도 분석

6. **Supervisor 통합** (`supervisor/team_supervisor.py`)
   - 대화 저장 로직 추가
   - 선호도 업데이트

7. **Integration Test**
   - 과거 대화 참조 시나리오
   - 선호도 기반 추천 시나리오

8. **E2E Test 및 배포**

**예상 소요 시간**: 10일 (개발 7일, 테스트 3일)

---

## 6. 구현 로드맵

### 6.1 전체 타임라인

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1-3: property_search_results 버그 수정 (1일)          │
│  → State/Context 설계 v2.0 실행                              │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4-1: Checkpointer PostgreSQL 전환 (1주일)             │
│  → AsyncSqliteSaver → AsyncPostgresSaver                     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4-2: SessionManager PostgreSQL 전환 (1주일)           │
│  → SQLite sessions.db → PostgreSQL websocket_sessions        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: Long-term Memory 구현 (2주일)                      │
│  → ConversationMemory, UserPreference, EntityMemory         │
│  → Planning Agent 통합                                        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: 개인화 기능 고도화 (향후)                          │
│  → 추천 시스템, 자동 필터링, 문맥 이해 고도화                │
└─────────────────────────────────────────────────────────────┘
```

**총 예상 기간**: 약 4-5주

---

### 6.2 우선순위별 작업

| Priority | Phase | 작업 | 소요 시간 | 의존성 |
|----------|-------|------|----------|--------|
| P0 | 1-3 | property_search_results 버그 수정 | 1일 | 없음 |
| P1 | 4-1 | Checkpointer PostgreSQL 전환 | 1주일 | P0 완료 |
| P1 | 4-2 | SessionManager PostgreSQL 전환 | 1주일 | P0 완료 |
| P2 | 5 | Long-term Memory 구현 | 2주일 | P1 완료 |
| P3 | 6 | 개인화 기능 고도화 | 추후 | P2 완료 |

---

## 7. API 설계

### 7.1 Memory Service API

#### 7.1.1 대화 이력 조회

**Endpoint**: `GET /api/memory/conversations`

**Request**:
```json
{
    "user_id": 42,
    "limit": 5,
    "session_id": "optional"
}
```

**Response**:
```json
{
    "conversations": [
        {
            "turn_number": 1,
            "user_query": "강남구 5억 이하 아파트 찾아줘",
            "assistant_response": "강남구에서 10건을 찾았습니다...",
            "intent_type": "property_search",
            "created_at": "2025-10-13T18:00:00Z"
        },
        {
            "turn_number": 2,
            "user_query": "첫 번째 매물 상세히 보여줘",
            "assistant_response": "강남 아파트 A 상세 정보입니다...",
            "intent_type": "property_detail",
            "created_at": "2025-10-13T18:05:00Z"
        }
    ]
}
```

---

#### 7.1.2 사용자 선호도 조회

**Endpoint**: `GET /api/memory/preferences/{user_id}`

**Response**:
```json
{
    "user_id": 42,
    "preferred_regions": ["강남구", "서초구"],
    "preferred_price_range": {
        "min": 40000,
        "max": 60000
    },
    "preferred_property_types": ["APARTMENT"],
    "frequent_queries": [
        {
            "query": "강남구 아파트",
            "count": 15,
            "last_searched": "2025-10-13T18:00:00Z"
        }
    ],
    "search_keywords": ["지하철", "학교", "신축"]
}
```

---

#### 7.1.3 중요 엔티티 조회

**Endpoint**: `GET /api/memory/entities/{user_id}`

**Request**:
```json
{
    "entity_type": "location",  // optional
    "limit": 10
}
```

**Response**:
```json
{
    "entities": [
        {
            "entity_type": "location",
            "entity_value": "강남구",
            "mention_count": 25,
            "importance_score": 25.0,
            "last_mentioned_at": "2025-10-13T18:00:00Z"
        },
        {
            "entity_type": "location",
            "entity_value": "서초구",
            "mention_count": 10,
            "importance_score": 10.0,
            "last_mentioned_at": "2025-10-12T15:30:00Z"
        }
    ]
}
```

---

#### 7.1.4 사용자 활동 통계

**Endpoint**: `GET /api/memory/statistics/{user_id}`

**Response**:
```json
{
    "user_id": 42,
    "total_conversations": 50,
    "intent_distribution": {
        "property_search": 30,
        "market_inquiry": 15,
        "legal_consult": 5
    },
    "last_activity": "2025-10-13T18:00:00Z",
    "active_days": 15,
    "avg_daily_queries": 3.3
}
```

---

### 7.2 SessionManager API

#### 7.2.1 세션 생성

**Endpoint**: `POST /api/sessions`

**Request**:
```json
{
    "user_id": 42,  // optional, null for non-logged-in users
    "metadata": {}  // optional
}
```

**Response**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "expires_at": "2025-10-14T18:00:00Z",
    "created_at": "2025-10-13T18:00:00Z"
}
```

---

#### 7.2.2 세션 조회

**Endpoint**: `GET /api/sessions/{session_id}`

**Response**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 42,
    "metadata": {},
    "created_at": "2025-10-13T18:00:00Z",
    "expires_at": "2025-10-14T18:00:00Z",
    "last_activity": "2025-10-13T18:05:00Z",
    "request_count": 5
}
```

---

## 8. 참고 자료

### 8.1 관련 문서

- [State/Context 설계 계획서 v2.0](./plan_of_state_context_design_v2.md)
- [LangGraph Checkpointer 문서](https://langchain-ai.github.io/langgraph/reference/checkpoints/)
- [PostgreSQL AsyncPostgresSaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres.PostgresSaver)

### 8.2 DB 마이그레이션 가이드

- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [SQLite to PostgreSQL 마이그레이션](https://pgloader.io/)

---

## 9. 체크리스트

### Phase 4-1: Checkpointer 전환
- [ ] langgraph[postgres] 패키지 설치
- [ ] checkpointer.py AsyncPostgresSaver로 변경
- [ ] team_supervisor.py 초기화 코드 수정
- [ ] Unit Test 작성
- [ ] Integration Test 실행
- [ ] 성능 비교 (SQLite vs PostgreSQL)
- [ ] 배포 및 모니터링

### Phase 4-2: SessionManager 전환
- [ ] models/session.py 작성 (WebSocketSession)
- [ ] schemas/session.py 작성
- [ ] Alembic migration 생성 및 실행
- [ ] api/session_manager.py 리팩토링
- [ ] 기존 SQLite 데이터 마이그레이션 (선택)
- [ ] Unit Test 작성
- [ ] WebSocket 연결 테스트
- [ ] 만료 세션 정리 Cron job 테스트
- [ ] 배포 및 모니터링

### Phase 5: Long-term Memory 구현
- [ ] models/memory.py 작성 (3개 모델)
- [ ] Alembic migration 생성 및 실행
- [ ] service_agent/memory/memory_service.py 구현
- [ ] Planning Agent 통합
- [ ] Supervisor 통합 (대화 저장)
- [ ] Unit Test 작성
- [ ] Integration Test (시나리오별)
- [ ] E2E Test
- [ ] 성능 최적화 (인덱스, 쿼리)
- [ ] 배포 및 모니터링

---

**승인자**: _______________
**승인일**: 2025-10-13
**다음 검토일**: Phase 4-1 완료 후

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0 | 2025-10-13 | 초안 작성 - SessionManager vs Memory 아키텍처 설계 | Claude Code |
