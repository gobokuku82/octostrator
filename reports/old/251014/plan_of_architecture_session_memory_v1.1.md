# Session Manager vs Long-term Memory 아키텍처 설계서 v1.1

**작성일**: 2025-10-14
**버전**: v1.2 (실행 계획 구체화)
**작성자**: Claude Code
**목적**: Long-term Memory 구현을 위한 구체적인 5단계 작업 계획 수립

**관련 문서**:
- [Session Memory 설계 v1.0](./plan_of_architecture_session_memory_v1.md)
- [State/Context 설계 계획서 v2.0](./plan_of_state_context_design_v2.md)

---

## 📋 목차

1. [현황 분석 요약](#현황-분석-요약)
2. [수정된 구현 로드맵](#수정된-구현-로드맵)
3. [Phase 5: Long-term Memory 우선 구현](#phase-5-long-term-memory-우선-구현)
4. [ChatMessage 확장 vs 신규 ConversationMemory](#chatmessage-확장-vs-신규-conversationmemory)
5. [PostgreSQL 마이그레이션 재평가](#postgresql-마이그레이션-재평가)
6. [구현 우선순위](#구현-우선순위)

---

## 1. 현황 분석 요약

### ✅ **중요 업데이트 (2025-10-14)**

**✅ Checkpointer PostgreSQL 마이그레이션 완료!**
- ✅ **상태**: SQLite → PostgreSQL 전환 완료 (2025-10-14, 소요시간 7분)
- ✅ **파일**: [checkpointer.py](backend/app/service_agent/foundation/checkpointer.py)
- ✅ **변경**: AsyncSqliteSaver → AsyncPostgresSaver
- ✅ **테이블**: checkpoints, checkpoint_blobs, checkpoint_writes (자동 생성)
- ✅ **보고서**: [migration_analysis_sqlite_to_postgres_checkpointer.md](./migration_analysis_sqlite_to_postgres_checkpointer.md)
- 🗑️ **정리**: `backend/data/system/checkpoints/` → 백업 완료 (35MB)

**✅ SessionManager PostgreSQL 마이그레이션 완료!**
- ✅ **상태**: SQLite → PostgreSQL 전환 완료 (2025-10-14, 소요시간 90분)
- ✅ **파일**: [session_manager.py](backend/app/api/session_manager.py) - 완전 리팩토링 (동기 → 비동기)
- ✅ **변경**: `sqlite3` → SQLAlchemy AsyncSessionLocal (AsyncPG 드라이버)
- ✅ **신규**: [models/session.py](backend/app/models/session.py) - Session ORM 모델
- ✅ **테이블**: sessions (PostgreSQL, 인덱스 포함)
- ✅ **보고서**: [migration_analysis_sessionmanager_sqlite_to_postgres.md](./migration_analysis_sessionmanager_sqlite_to_postgres.md)
- ✅ **Async DB**: [postgre_db.py](backend/app/db/postgre_db.py) - AsyncEngine + AsyncSessionLocal 추가
- ✅ **API 업데이트**: [chat_api.py](backend/app/api/chat_api.py) - 7개 메서드 await 추가
- 🗑️ **정리**: `backend/data/system/sessions/sessions.db` → 백업 완료 (24KB)

### 1.1 구현 완료된 시스템

| 시스템 | 상태 | 파일 | 비고 |
|--------|------|------|------|
| **SessionManager** | ✅ 완료 (**PostgreSQL**) | `backend/app/api/session_manager.py` | **AsyncSessionLocal 사용 (2025-10-14 전환, 비동기)** |
| **Checkpointer** | ✅ 완료 (**PostgreSQL**) | `backend/app/service_agent/foundation/checkpointer.py` | **AsyncPostgresSaver 사용 (2025-10-14 전환)** |
| **User 인증** | ✅ 완료 | `backend/app/models/users.py` | Local/Social 로그인 |
| **ChatSession/Message** | ✅ 부분 완료 | `backend/app/models/chat.py` | 단순 메시지 저장만 |
| **PlanningAgent** | ✅ 완료 | `backend/app/service_agent/cognitive_agents/planning_agent.py` | 의도 분석 패턴 매칭 |

### 1.2 미구현된 핵심 시스템 (Gap)

| 시스템 | 진행도 | 영향 | 우선순위 |
|--------|--------|------|----------|
| **ConversationMemory** | ❌ 0% | 대화 학습 불가 | 🔴 **P0** |
| **UserPreference** | ❌ 0% | 개인화 불가 | 🔴 **P0** |
| **EntityMemory** | ❌ 0% | 엔티티 추적 불가 | 🟡 P1 |
| **LongTermMemoryService** | ❌ 0% | Memory 시스템 없음 | 🔴 **P0** |
| **Planning Agent Memory 통합** | ❌ 0% | 과거 대화 참조 불가 | 🔴 **P0** |
| **Supervisor Memory 통합** | ❌ 0% | 대화 저장 안됨 | 🔴 **P0** |

### 1.3 핵심 문제점

**현재 시스템은 "일회성 대화만 처리 가능"합니다:**

```
❌ 불가능한 시나리오:
- "지난번에 찾아본 강남구 아파트 중에서..." (과거 대화 기억 없음)
- "내가 자주 검색하는 지역은?" (선호도 학습 없음)
- "그 매물 상세 정보 보여줘" (문맥 참조 불가)
- 로그인 사용자 개인화 추천 (선호도 데이터 없음)
```

**✅ 가능한 시나리오:**
- 단일 세션 내 질의응답 (State 저장됨)
- 비로그인 사용자 일회성 검색
- 세션별 메시지 기록 (단순 저장만)

---

## 2. 수정된 구현 로드맵

### 2.1 기존 v1.0 로드맵 문제점

```
Phase 4-1: Checkpointer PostgreSQL 전환 (1주일)
Phase 4-2: SessionManager PostgreSQL 전환 (1주일)
Phase 5: Long-term Memory 구현 (2주일)
```

**문제:**
1. ❌ PostgreSQL 전환이 먼저 필요하지 않음 (SQLite로도 충분히 동작)
2. ❌ Long-term Memory가 가장 시급한데 마지막 순서
3. ❌ 인프라 마이그레이션에 2주 소비 후 핵심 기능 구현

### 2.2 수정된 로드맵 (v1.1)

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 5-1: ConversationMemory + UserPreference 구현 (1주)  │
│  → 대화 이력 저장 및 선호도 학습 (SQLite/PostgreSQL 병행)   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 5-2: Planning Agent & Supervisor Memory 통합 (3일)   │
│  → 과거 대화 참조 및 개인화된 의도 분석                      │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 5-3: EntityMemory 구현 (선택, 3일)                    │
│  → 엔티티 추적 고도화                                        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: PostgreSQL 마이그레이션 (선택, 필요시)             │
│  → 다중 서버 환경 필요 시에만 진행                            │
└─────────────────────────────────────────────────────────────┘
```

**총 예상 기간**: 약 2-3주 (PostgreSQL 마이그레이션 제외 시 10일)

**우선순위 변경 근거:**
1. Long-term Memory가 **비즈니스 핵심 가치**
2. SQLite도 단일 서버 환경에서는 충분히 고성능
3. PostgreSQL 마이그레이션은 스케일 아웃 필요 시 진행

---

## 3. Phase 5: Long-term Memory 우선 구현

### 📋 작업 개요 (5가지 핵심 작업)

Long-term Memory 구현은 다음 **5가지 주요 작업**으로 구성됩니다:

| 작업 | 위치 | 예상 시간 | 우선순위 | 의존성 |
|------|------|----------|---------|--------|
| **1. DB 모델** | `models/memory.py` | 1일 | P0 | 없음 |
| **2. Memory Service** | `service_agent/memory/memory_service.py` | 2-3일 | P0 | 1번 완료 |
| **3. Planning Node 통합** | `supervisor/team_supervisor.py` (planning_node) | 1일 | P0 | 2번 완료 |
| **4. Response Node 통합** | `supervisor/team_supervisor.py` (generate_response_node) | 1일 | P0 | 2번 완료 |
| **5. Frontend UI** | Frontend (Next.js) | 2-3일 | P0 | 3-4번 완료 |

**총 예상 기간**: 7-8일

---

### ✅ **중요 결정 사항**

#### 1. Memory 로드 위치: `planning_node`
- ❌ `initialize_node`에서 로드 **안 함**
- ✅ `planning_node`에서 로드
- **이유**: IRRELEVANT/UNCLEAR 쿼리는 조기 종료하므로 불필요한 DB 쿼리 방지

#### 2. Memory 로드 개수: **3-5개 (동적 조정)**
- 기본값: 3개
- 의도 타입별 조정:
  - `legal_consult`: 5개 (문맥 중요)
  - `market_inquiry`: 3개 (최근만 중요)
  - `simple_question`: 1개 (최소)

#### 3. `initialize_node` 수정 여부: **수정 불필요**
- 현재 그대로 유지
- 각 워크플로우 실행마다 State 초기화만 담당
- Memory 로드는 `planning_node`에서 처리

---

### 3.1 Phase 5-1: 핵심 Memory 모델 구현 (1주)

#### 3.1.1 DB 모델 설계 (1일)

**파일**: `backend/app/models/memory.py` (신규)

```python
from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgre_db import Base
import uuid

# ============================================================================
# 1. ConversationMemory - 대화 이력 메모리 (P0)
# ============================================================================

class ConversationMemory(Base):
    """
    대화 이력 메모리 - 모든 대화 턴 기록

    기존 ChatMessage와 차이:
    - ChatMessage: 단순 메시지 저장 (content만)
    - ConversationMemory: 실행 메타데이터 포함 (intent, teams, entities)
    """
    __tablename__ = "conversation_memories"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Session & User 연결
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 대화 턴 정보
    turn_number = Column(Integer, nullable=False)
    user_query = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)

    # 의도 분석 결과 (Planning Agent)
    intent_type = Column(String(50))  # "legal_consult", "market_inquiry", etc.
    intent_confidence = Column(Float)  # 0.0 ~ 1.0

    # 실행 메타데이터 (Supervisor)
    teams_used = Column(ARRAY(String))  # ["search", "analysis"]
    tools_used = Column(ARRAY(String))  # ["legal_search", "market_data"]
    execution_time_ms = Column(Integer)  # 실행 시간 (밀리초)

    # 추출된 엔티티 (NER)
    entities = Column(JSON)  # {"location": ["강남구"], "price": ["5억"]}

    # 타임스탬프
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="conversation_memories")
    user = relationship("User", back_populates="conversation_memories")

    # Indexes
    __table_args__ = (
        Index('idx_session_turn', 'session_id', 'turn_number'),
        Index('idx_user_recent', 'user_id', 'created_at'),
        Index('idx_intent_type', 'intent_type'),
    )


# ============================================================================
# 2. UserPreference - 사용자 선호도 메모리 (P0)
# ============================================================================

class UserPreference(Base):
    """
    사용자 선호도 메모리 - 학습된 패턴

    사용자의 검색 패턴, 선호 지역/가격대 등을 학습하여
    개인화된 서비스 제공
    """
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
    frequent_queries = Column(JSON)  # [{"query": "강남구 아파트", "count": 15}]
    search_keywords = Column(ARRAY(String))  # ["지하철", "학교", "신축"]

    # 매물 상호작용
    viewed_properties = Column(ARRAY(Integer))  # 최근 조회한 매물 ID (100개)
    favorited_properties = Column(ARRAY(Integer))  # 찜한 매물 ID

    # 시간대 패턴
    active_hours = Column(JSON)  # {"morning": 5, "afternoon": 10, "evening": 20}

    # 마지막 검색 컨텍스트 (문맥 유지)
    last_search_context = Column(JSON)

    # 타임스탬프
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preference")


# ============================================================================
# 3. EntityMemory - 엔티티 추적 메모리 (P1, 선택)
# ============================================================================

class EntityMemory(Base):
    """
    엔티티 추출 및 추적 메모리

    사용자가 자주 언급하는 엔티티(지역, 가격 등)를 추적하여
    "그 매물", "지난번 그 지역" 같은 문맥 참조 가능
    """
    __tablename__ = "entity_memories"

    # Primary Key
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 엔티티 정보
    entity_type = Column(String(50), nullable=False)  # "location", "price", "property_id"
    entity_value = Column(String(255), nullable=False)  # "강남구", "5억"
    entity_normalized = Column(String(255))  # "5억" → "500000000"

    # 문맥 정보
    entity_context = Column(Text)  # 엔티티가 언급된 문맥
    related_entities = Column(JSON)  # 함께 언급된 다른 엔티티

    # 빈도 및 중요도
    mention_count = Column(Integer, default=1)
    importance_score = Column(Float, default=1.0)

    # 타임스탬프
    first_mentioned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_mentioned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="entity_memories")

    # Indexes
    __table_args__ = (
        Index('idx_entity_lookup', 'user_id', 'entity_type', 'entity_value'),
        Index('idx_importance', 'user_id', 'importance_score'),
    )
```

#### 3.1.2 User 모델 Relationships 추가

**파일**: `backend/app/models/users.py` (수정)

```python
class User(Base):
    # ... 기존 필드 ...

    # Relationships (추가)
    conversation_memories = relationship("ConversationMemory", back_populates="user", cascade="all, delete-orphan")
    preference = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    entity_memories = relationship("EntityMemory", back_populates="user", cascade="all, delete-orphan")
```

#### 3.1.3 ChatSession Relationships 추가

**파일**: `backend/app/models/chat.py` (수정)

```python
class ChatSession(Base):
    # ... 기존 필드 ...

    # Relationships (추가)
    conversation_memories = relationship("ConversationMemory", back_populates="session", cascade="all, delete-orphan")
```

#### 3.1.4 Alembic Migration

```bash
# 1. Migration 생성
alembic revision --autogenerate -m "Add Long-term Memory models (ConversationMemory, UserPreference, EntityMemory)"

# 2. Migration 실행
alembic upgrade head
```

---

#### 3.1.5 LongTermMemoryService 구현 (3일)

**파일**: `backend/app/service_agent/memory/memory_service.py` (신규)

```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgre_db import SessionLocal
from app.models.memory import ConversationMemory, UserPreference, EntityMemory
import logging

logger = logging.getLogger(__name__)


class LongTermMemoryService:
    """
    Long-term Memory 관리 서비스

    대화 이력, 사용자 선호도, 엔티티 추적을 통합 관리
    """

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

        Args:
            session_id: 세션 ID (UUID)
            user_id: 사용자 ID
            turn_number: 턴 번호 (세션 내 몇 번째 대화)
            user_query: 사용자 질문
            assistant_response: AI 응답
            intent_type: 의도 타입 ("legal_consult", "market_inquiry", etc.)
            intent_confidence: 의도 신뢰도 (0.0 ~ 1.0)
            teams_used: 사용된 팀 목록 ["search", "analysis"]
            tools_used: 사용된 도구 목록 ["legal_search", "market_data"]
            execution_time_ms: 실행 시간 (밀리초)
            entities: 추출된 엔티티 {"location": ["강남구"], "price": ["5억"]}

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

            logger.info(f"💾 Conversation stored: user={user_id}, turn={turn_number}, intent={intent_type}")
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
            대화 이력 리스트 (시간순)
        """
        async with SessionLocal() as db:
            result = await db.execute(
                select(ConversationMemory)
                .where(ConversationMemory.user_id == user_id)
                .order_by(ConversationMemory.created_at.desc())
                .limit(limit)
            )
            conversations = result.scalars().all()

            context = [
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

            logger.debug(f"📖 Loaded {len(context)} recent conversations for user {user_id}")
            return context

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
                logger.debug(f"No preferences found for user {user_id}")
                return None

            return {
                "preferred_regions": pref.preferred_regions or [],
                "preferred_price_range": pref.preferred_price_range or {},
                "preferred_property_types": pref.preferred_property_types or [],
                "frequent_queries": pref.frequent_queries or [],
                "search_keywords": pref.search_keywords or []
            }

    async def update_region_preference(
        self,
        user_id: int,
        region: str
    ):
        """지역 검색 카운트 업데이트"""
        async with SessionLocal() as db:
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
            logger.debug(f"🎯 Updated region preference for user {user_id}: {region}")

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
                if property_id not in viewed:
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
    # 3. 엔티티 추적 관리 (선택)
    # ============================================================================

    async def update_entity_mentions(
        self,
        user_id: int,
        entities: Dict[str, List[str]],
        context: str
    ):
        """엔티티 언급 업데이트"""
        async with SessionLocal() as db:
            for entity_type, values in entities.items():
                for value in values:
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
                                importance_score=float(new_count),
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
        """중요 엔티티 조회 (빈도 기반)"""
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
                "total_conversations": total_conversations or 0,
                "intent_distribution": intent_distribution,
                "last_activity": last.created_at.isoformat() if last else None
            }


# Module-level singleton
_memory_service = None


def get_memory_service() -> LongTermMemoryService:
    """
    Get the singleton LongTermMemoryService instance

    Returns:
        LongTermMemoryService singleton instance
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = LongTermMemoryService()
    return _memory_service
```

---

### 3.2 Phase 5-2: Planning Agent & Supervisor Memory 통합 (3일)

#### 3.2.1 Planning Agent Memory 통합

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py` (수정)

```python
class PlanningAgent:
    def __init__(self, llm_context=None):
        self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
        self.intent_patterns = self._initialize_intent_patterns()
        self.agent_capabilities = self._load_agent_capabilities()
        self.query_decomposer = QueryDecomposer(self.llm_service)

        # ✅ Memory Service 추가
        from app.service_agent.memory.memory_service import get_memory_service
        self.memory_service = get_memory_service()

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
        3. 개인화된 의도 분석

        Args:
            query: 사용자 질문
            user_id: 사용자 ID (None이면 메모리 미사용)
            session_id: 세션 ID

        Returns:
            의도 분석 결과
        """

        # 1. 과거 대화 컨텍스트 (user_id 있을 때만)
        recent_context = []
        user_preferences = {}

        if user_id:
            try:
                recent_context = await self.memory_service.load_recent_context(
                    user_id=user_id,
                    limit=3  # 최근 3개 대화
                )

                user_preferences = await self.memory_service.get_user_preferences(user_id) or {}

                logger.info(f"🧠 Loaded memory: {len(recent_context)} conversations, preferences: {bool(user_preferences)}")
            except Exception as e:
                logger.warning(f"Failed to load memory for user {user_id}: {e}")

        # 2. LLM에게 컨텍스트 전달
        enhanced_prompt = self._build_enhanced_prompt(query, recent_context, user_preferences)

        # 3. 의도 분석
        intent_result = await self.llm_service.analyze_intent(enhanced_prompt)

        # 4. 엔티티 추출 및 추적 (선택)
        if user_id:
            try:
                entities = self._extract_entities(query)
                if entities:
                    await self.memory_service.update_entity_mentions(
                        user_id=user_id,
                        entities=entities,
                        context=query
                    )
            except Exception as e:
                logger.warning(f"Failed to update entity mentions: {e}")

        return intent_result

    def _build_enhanced_prompt(
        self,
        query: str,
        recent_context: List[Dict],
        user_preferences: Dict
    ) -> str:
        """컨텍스트를 포함한 프롬프트 생성"""

        prompt_parts = [f"사용자 질문: {query}"]

        # 과거 대화 컨텍스트
        if recent_context:
            context_str = "\n".join([
                f"- User: {c['user_query']}\n  Assistant: {c['assistant_response'][:100]}..."
                for c in recent_context
            ])
            prompt_parts.append(f"\n과거 대화 컨텍스트:\n{context_str}")

        # 사용자 선호도
        if user_preferences:
            pref_lines = []
            if user_preferences.get('preferred_regions'):
                pref_lines.append(f"- 자주 검색하는 지역: {', '.join(user_preferences['preferred_regions'])}")
            if user_preferences.get('preferred_price_range'):
                price_range = user_preferences['preferred_price_range']
                pref_lines.append(f"- 선호 가격대: {price_range.get('min', '?')}만원 ~ {price_range.get('max', '?')}만원")
            if user_preferences.get('preferred_property_types'):
                pref_lines.append(f"- 선호 매물 타입: {', '.join(user_preferences['preferred_property_types'])}")

            if pref_lines:
                prompt_parts.append(f"\n사용자 선호도:\n" + "\n".join(pref_lines))

        prompt_parts.append("\n위 정보를 참고하여 사용자의 의도를 분석하세요.")
        prompt_parts.append("지역이 명시되지 않았다면 선호 지역을 제안하세요.")

        return "\n".join(prompt_parts)

    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """간단한 엔티티 추출 (정규식 기반)"""
        import re

        entities = {
            "location": [],
            "price": [],
            "property_type": [],
        }

        # 지역 추출
        regions = ["강남구", "서초구", "송파구", "강동구", "마포구", "용산구", "중구", "종로구"]
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

        # 빈 리스트 제거
        return {k: v for k, v in entities.items() if v}
```

#### 3.2.2 TeamSupervisor Memory 통합

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py` (수정)

```python
class TeamBasedSupervisor:
    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        # ... 기존 코드 ...

        # ✅ Memory Service 추가
        from app.service_agent.memory.memory_service import get_memory_service
        self.memory_service = get_memory_service()

        logger.info(f"TeamBasedSupervisor initialized with Memory support")

    async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        Planning 노드 - Memory 통합
        """
        logger.info("[TeamSupervisor] Planning phase with Memory")

        state["current_phase"] = "planning"

        query = state.get("query", "")
        session_id = state.get("session_id")
        user_id = state.get("user_id")  # ✅ user_id 추가 필요

        # ✅ Memory를 활용한 의도 분석
        intent_result = await self.planning_agent.analyze_intent_with_memory(
            query=query,
            user_id=user_id,
            session_id=session_id
        )

        # 계획 수립
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

        # ✅ Memory 저장 (user_id 있을 때만)
        user_id = state.get("user_id")
        if user_id:
            await self._store_conversation_to_memory(state, response)
            await self._update_user_preferences(state)

        return state

    async def _store_conversation_to_memory(
        self,
        state: MainSupervisorState,
        response: Dict[str, Any]
    ):
        """대화 이력을 Memory에 저장"""
        try:
            session_id = state.get("session_id")
            user_id = state.get("user_id")
            query = state.get("query")
            planning_state = state.get("planning_state", {})

            # 턴 번호 계산 (세션 내 몇 번째 대화인지)
            turn_number = await self._get_turn_number(session_id)

            # 의도 분석 결과
            analyzed_intent = planning_state.get("analyzed_intent", {})
            intent_type = analyzed_intent.get("intent_type", "unknown")
            intent_confidence = analyzed_intent.get("confidence", 0.0)

            # 실행 메타데이터
            teams_used = state.get("active_teams", [])
            tools_used = self._extract_tools_used(state)
            execution_time_ms = int(state.get("total_execution_time", 0) * 1000)

            # 엔티티
            entities = analyzed_intent.get("entities", {})

            # Memory 저장
            conversation_id = await self.memory_service.store_conversation(
                session_id=session_id,
                user_id=user_id,
                turn_number=turn_number,
                user_query=query,
                assistant_response=response.get("content", ""),
                intent_type=intent_type,
                intent_confidence=intent_confidence,
                teams_used=teams_used,
                tools_used=tools_used,
                execution_time_ms=execution_time_ms,
                entities=entities
            )

            logger.info(f"✅ Conversation saved to Memory: conversation_id={conversation_id}")

        except Exception as e:
            logger.error(f"Failed to store conversation to memory: {e}", exc_info=True)

    async def _update_user_preferences(self, state: MainSupervisorState):
        """사용자 선호도 업데이트"""
        try:
            user_id = state.get("user_id")
            query = state.get("query")
            planning_state = state.get("planning_state", {})

            # 지역 선호도 업데이트
            entities = planning_state.get("analyzed_intent", {}).get("entities", {})
            locations = entities.get("location", [])
            for location in locations:
                await self.memory_service.update_region_preference(user_id, location)

            # 가격 선호도 업데이트
            price_range = self._extract_price_range_from_entities(entities)
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

            logger.debug(f"✅ User preferences updated for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}", exc_info=True)

    async def _get_turn_number(self, session_id: str) -> int:
        """세션 내 턴 번호 계산"""
        try:
            conversations = await self.memory_service.get_session_conversations(session_id)
            return len(conversations) + 1
        except:
            return 1

    def _extract_tools_used(self, state: MainSupervisorState) -> List[str]:
        """사용된 도구 추출"""
        tools = []
        team_results = state.get("team_results", {})
        for team_name, result in team_results.items():
            if isinstance(result, dict) and result.get("tools"):
                tools.extend(result["tools"])
        return list(set(tools))

    def _extract_price_range_from_entities(self, entities: Dict) -> Optional[Dict[str, int]]:
        """엔티티에서 가격 범위 추출"""
        import re

        prices = entities.get("price", [])
        if not prices:
            return None

        price_values = []
        for price_str in prices:
            match = re.search(r'(\d+)억', price_str)
            if match:
                price_values.append(int(match.group(1)) * 10000)  # 만원 단위

        if price_values:
            return {
                "min": min(price_values),
                "max": max(price_values)
            }
        return None

    def _extract_property_ids(self, state: MainSupervisorState) -> List[int]:
        """응답에서 매물 ID 추출"""
        property_ids = []
        team_results = state.get("team_results", {})

        # Search Team 결과에서 매물 ID 추출
        if "search" in team_results:
            search_result = team_results["search"]
            if isinstance(search_result, dict) and "properties" in search_result:
                properties = search_result["properties"]
                property_ids.extend([p.get("id") for p in properties if p.get("id")])

        return property_ids
```

---

### 3.3 Phase 5-3: EntityMemory 구현 (선택, 3일)

**우선순위**: P1 (선택 사항)

EntityMemory는 고급 문맥 참조 기능을 위한 것으로, Phase 5-1, 5-2가 완료된 후 필요 시 구현합니다.

**사용 사례:**
- "그 매물" → 가장 최근에 언급한 매물 ID 참조
- "지난번 그 지역" → 가장 자주 언급한 지역 참조

**구현 시점**: 기본 Memory 시스템 동작 확인 후

---

### 3.4 Phase 5-4: Frontend UI 구현 (2-3일)

**우선순위**: P0 (필수)

#### 3.4.1 대화 이력 UI (1일)

**파일**: `frontend/components/chat/ConversationHistory.tsx` (신규)

```typescript
import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';

interface Conversation {
  session_id: string;
  first_query: string;
  last_activity: string;
  message_count: number;
}

interface ConversationHistoryProps {
  userId: number;
  onSelectConversation: (sessionId: string) => void;
}

export default function ConversationHistory({ userId, onSelectConversation }: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConversations();
  }, [userId]);

  const loadConversations = async () => {
    try {
      const response = await fetch(`/api/v1/memory/conversations?user_id=${userId}&limit=10`);
      const data = await response.json();
      setConversations(data.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="conversation-history">
      <h3>대화 이력</h3>
      {loading ? (
        <div>로딩 중...</div>
      ) : (
        <ul>
          {conversations.map((conv) => (
            <li key={conv.session_id} onClick={() => onSelectConversation(conv.session_id)}>
              <div className="query">{conv.first_query}</div>
              <div className="meta">
                {format(new Date(conv.last_activity), 'yyyy-MM-dd HH:mm')} · {conv.message_count}개 메시지
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

#### 3.4.2 Memory 로드 표시 (1일)

**파일**: `frontend/components/chat/PlanningIndicator.tsx` (수정)

```typescript
// WebSocket 메시지 처리 추가
interface PlanningIndicatorProps {
  status: 'idle' | 'planning' | 'memory_loaded' | 'plan_ready';
  memoryContext?: {
    conversationCount: number;
    hasPreferences: boolean;
  };
}

export default function PlanningIndicator({ status, memoryContext }: PlanningIndicatorProps) {
  return (
    <div className="planning-indicator">
      {status === 'planning' && <Spinner text="계획 수립 중..." />}
      {status === 'memory_loaded' && memoryContext && (
        <div className="memory-loaded">
          ✅ 과거 대화 {memoryContext.conversationCount}개 참조 중
          {memoryContext.hasPreferences && ' · 선호도 적용'}
        </div>
      )}
      {status === 'plan_ready' && <div>계획 완료!</div>}
    </div>
  );
}
```

#### 3.4.3 Memory 컨텍스트 상세 보기 (Optional, 1일)

**파일**: `frontend/components/chat/MemoryContextViewer.tsx` (신규)

```typescript
interface MemoryContext {
  conversations: Array<{
    user_query: string;
    assistant_response: string;
    created_at: string;
  }>;
  preferences: {
    preferred_regions?: string[];
    price_range?: { min: number; max: number };
  };
}

export default function MemoryContextViewer({ context }: { context: MemoryContext }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="memory-context-viewer">
      <button onClick={() => setExpanded(!expanded)}>
        📝 참조한 과거 대화 {context.conversations.length}개 {expanded ? '▲' : '▼'}
      </button>
      {expanded && (
        <div className="context-details">
          <h4>과거 대화:</h4>
          <ul>
            {context.conversations.map((conv, idx) => (
              <li key={idx}>
                <div className="date">{format(new Date(conv.created_at), 'MM/dd HH:mm')}</div>
                <div className="query">Q: {conv.user_query}</div>
                <div className="response">A: {conv.assistant_response.slice(0, 100)}...</div>
              </li>
            ))}
          </ul>
          {context.preferences.preferred_regions && (
            <div className="preferences">
              <h4>선호도:</h4>
              <p>자주 검색하는 지역: {context.preferences.preferred_regions.join(', ')}</p>
              {context.preferences.price_range && (
                <p>
                  선호 가격대: {context.preferences.price_range.min}만원 ~{' '}
                  {context.preferences.price_range.max}만원
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

#### 3.4.4 WebSocket 메시지 추가

**파일**: Backend `team_supervisor.py` - planning_node 수정

```python
async def planning_node(self, state: MainSupervisorState):
    # ... 기존 코드 ...

    # Memory 로드 후 WebSocket 알림 ✅ 추가
    if user_id and callback:
        await callback("memory_loaded", {
            "conversation_count": len(recent_context),
            "has_preferences": bool(user_preferences)
        })
```

#### 3.4.5 API 엔드포인트 추가

**파일**: `backend/app/api/memory_api.py` (신규)

```python
from fastapi import APIRouter, Depends, HTTPException
from app.service_agent.memory.memory_service import get_memory_service
from typing import List, Dict, Any

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

@router.get("/conversations")
async def get_user_conversations(
    user_id: int,
    limit: int = 10
) -> Dict[str, Any]:
    """사용자의 최근 대화 세션 목록 조회"""
    memory_service = get_memory_service()

    # 세션별로 그룹화된 대화 목록
    conversations = await memory_service.get_user_conversation_sessions(user_id, limit)

    return {
        "conversations": conversations,
        "total": len(conversations)
    }

@router.get("/statistics")
async def get_user_statistics(user_id: int) -> Dict[str, Any]:
    """사용자 활동 통계"""
    memory_service = get_memory_service()
    stats = await memory_service.get_user_statistics(user_id)
    return stats

@router.get("/preferences")
async def get_user_preferences(user_id: int) -> Dict[str, Any]:
    """사용자 선호도 조회"""
    memory_service = get_memory_service()
    preferences = await memory_service.get_user_preferences(user_id)
    return preferences or {}
```

**파일**: `backend/main.py` - Router 추가

```python
from app.api import memory_api

app.include_router(memory_api.router)
```

---

## 4. ChatMessage 확장 vs 신규 ConversationMemory

### 4.1 두 가지 접근 방식

#### Option A: 기존 ChatMessage 확장
```python
class ChatMessage(Base):
    # 기존
    id, session_id, sender_type, content, created_at

    # 추가
    intent_type = Column(String(50))
    intent_confidence = Column(Float)
    teams_used = Column(ARRAY(String))
    entities = Column(JSON)
    execution_time_ms = Column(Integer)
```

**장점:**
- 기존 코드와 호환
- 마이그레이션 간단

**단점:**
- 비로그인 사용자 메시지와 혼재
- user_id 없음 (세션만 있음)
- 분석/학습에 비효율적

#### Option B: 신규 ConversationMemory 모델 (✅ 권장)
```python
class ConversationMemory(Base):
    # session_id, user_id 모두 필수
    # 실행 메타데이터 포함
    # 분석/학습 최적화
```

**장점:**
- user_id 기반 개인화
- 로그인 사용자만 저장 (GDPR 준수)
- 분석/학습에 최적화된 구조

**단점:**
- 신규 테이블 추가

### 4.2 권장 사항: Hybrid 접근

```
┌─────────────────────────────────────────────────────────────┐
│  ChatMessage                                                  │
│  - 모든 메시지 저장 (로그인 여부 무관)                        │
│  - UI 표시용                                                  │
│  - 단순 content만                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  ConversationMemory                                           │
│  - 로그인 사용자만 (user_id 필수)                             │
│  - 실행 메타데이터 포함                                       │
│  - 개인화 및 학습용                                           │
└─────────────────────────────────────────────────────────────┘
```

**구현:**
- ChatMessage: 그대로 유지 (UI 표시용)
- ConversationMemory: 신규 추가 (학습용)
- Supervisor에서 두 곳 모두 저장

---

## 5. PostgreSQL 마이그레이션 재평가

### 5.1 기존 계획 (v1.0)

```
Phase 4-1: Checkpointer PostgreSQL 전환 (1주)
Phase 4-2: SessionManager PostgreSQL 전환 (1주)
```

### 5.2 재평가 결과

#### 현재 SQLite 성능
- ✅ 단일 서버 환경에서 충분히 고성능
- ✅ 동시 접속 100명 이하: 문제 없음
- ✅ 백업 및 복구 간편

#### PostgreSQL 전환이 필요한 경우
1. **다중 서버 환경** (스케일 아웃)
   - 로드 밸런서 + 여러 백엔드 서버
   - 세션/State를 공유해야 함

2. **고급 쿼리 필요**
   - 복잡한 JOIN, 집계
   - Full-text Search

3. **대규모 데이터**
   - 수백만 건 이상의 대화 이력
   - SQLite 파일 크기 한계 (수 GB)

### 5.3 권장 사항

**Phase 6으로 연기 (선택 사항):**

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 5 완료 후 운영 중 필요 시 마이그레이션                 │
│  - 단일 서버 → SQLite 유지                                   │
│  - 다중 서버 필요 → PostgreSQL 전환                          │
└─────────────────────────────────────────────────────────────┘
```

**마이그레이션 용이성:**
- SQLAlchemy 사용 중이므로 DB 변경 간단
- 연결 문자열만 변경하면 됨
- Alembic migration으로 스키마 자동 전환

---

## 6. 구현 우선순위

### 6.1 우선순위 정리

| Phase | 작업 | 소요 시간 | 우선순위 | 비즈니스 가치 |
|-------|------|----------|---------|--------------|
| **Phase 5-1** | ConversationMemory + UserPreference 모델 및 Service | 1주 | 🔴 **P0** | ⭐⭐⭐⭐⭐ |
| **Phase 5-2** | Planning Agent & Supervisor Memory 통합 | 3일 | 🔴 **P0** | ⭐⭐⭐⭐⭐ |
| **Phase 5-3** | EntityMemory 구현 | 3일 | 🟡 P1 | ⭐⭐⭐ |
| **Phase 6** | PostgreSQL 마이그레이션 | 1주 | ⚪ P2 | ⭐⭐ |

### 6.2 즉시 시작 가능한 작업 (P0)

```bash
# 1. 모델 파일 생성
touch backend/app/models/memory.py

# 2. Service 파일 생성
mkdir -p backend/app/service_agent/memory
touch backend/app/service_agent/memory/__init__.py
touch backend/app/service_agent/memory/memory_service.py

# 3. models/__init__.py에 import 추가
# from .memory import ConversationMemory, UserPreference, EntityMemory

# 4. Alembic migration
alembic revision --autogenerate -m "Add Long-term Memory models"
alembic upgrade head

# 5. Planning Agent 수정
# backend/app/service_agent/cognitive_agents/planning_agent.py

# 6. Supervisor 수정
# backend/app/service_agent/supervisor/team_supervisor.py
```

### 6.3 테스트 시나리오

#### 시나리오 1: 과거 대화 참조
```
Turn 1:
User: "강남구 5억 이하 아파트 찾아줘"
AI: "강남구에서 10건 찾았습니다..."
→ Memory 저장: location=["강남구"], price=["5억"]

Turn 2 (10분 후):
User: "첫 번째 매물 상세 정보 보여줘"
AI: (Memory 조회) "강남 아파트 A의 상세 정보입니다..."
```

#### 시나리오 2: 선호도 기반 개인화
```
User (로그인, 강남구 검색 25회):
"아파트 추천해줘" (지역 미지정)

AI (Memory 조회):
→ preferred_regions: ["강남구"]
→ "강남구를 자주 검색하셨는데, 강남구 아파트를 추천해드릴까요?"
```

---

## 7. 체크리스트 (5가지 핵심 작업)

### ✅ 작업 1: DB 모델 구현 (1일)
- [ ] `backend/app/models/memory.py` 작성
  - [ ] ConversationMemory 모델 (session_id, user_id, turn_number, user_query, assistant_response, intent_type, teams_used, entities)
  - [ ] UserPreference 모델 (user_id, preferred_regions, preferred_price_range, viewed_properties)
  - [ ] EntityMemory 모델 (선택, P1)
- [ ] `backend/app/models/users.py` Relationships 추가
  ```python
  conversation_memories = relationship("ConversationMemory", ...)
  preference = relationship("UserPreference", uselist=False, ...)
  ```
- [ ] `backend/app/models/chat.py` Relationships 추가
  ```python
  conversation_memories = relationship("ConversationMemory", ...)
  ```
- [ ] `backend/app/models/__init__.py` import 추가
- [ ] Alembic migration 생성 및 실행
  ```bash
  alembic revision --autogenerate -m "Add Long-term Memory models"
  alembic upgrade head
  ```

### ✅ 작업 2: LongTermMemoryService 구현 (2-3일)
- [ ] 디렉토리 생성
  ```bash
  mkdir -p backend/app/service_agent/memory
  touch backend/app/service_agent/memory/__init__.py
  touch backend/app/service_agent/memory/memory_service.py
  ```
- [ ] `memory_service.py` 구현
  - [ ] 대화 이력 관리
    - [ ] `store_conversation()` - 대화 저장
    - [ ] `load_recent_context(user_id, limit=3)` - 최근 N개 대화 로드
    - [ ] `get_session_conversations(session_id)` - 세션 대화 조회
  - [ ] 사용자 선호도 관리
    - [ ] `get_user_preferences(user_id)` - 선호도 조회
    - [ ] `update_region_preference(user_id, region)` - 지역 선호도 업데이트
    - [ ] `update_price_preference(user_id, min, max)` - 가격 선호도 업데이트
    - [ ] `add_viewed_property(user_id, property_id)` - 조회 매물 추가
  - [ ] 엔티티 추적 (선택, P1)
    - [ ] `update_entity_mentions(user_id, entities, context)` - 엔티티 업데이트
    - [ ] `get_important_entities(user_id, limit=10)` - 중요 엔티티 조회
  - [ ] 통계 및 분석
    - [ ] `get_user_statistics(user_id)` - 사용자 활동 통계
  - [ ] `get_memory_service()` - Singleton 패턴
- [ ] Unit Test 작성

### ✅ 작업 3: Planning Node 통합 (1일)
- [ ] `planning_agent.py` 수정
  - [ ] `memory_service` import 및 초기화
    ```python
    from app.service_agent.memory.memory_service import get_memory_service
    self.memory_service = get_memory_service()
    ```
  - [ ] `analyze_intent_with_memory(query, user_id, session_id)` 메서드 추가
  - [ ] `_build_enhanced_prompt(query, recent_context, preferences)` 메서드 추가
  - [ ] `_extract_entities(query)` 메서드 추가 (정규식 기반)
- [ ] `team_supervisor.py` - `planning_node` 수정
  - [ ] `memory_service` import 및 초기화
  - [ ] `user_id = state.get("user_id")` 추가
  - [ ] `analyze_intent_with_memory()` 호출로 변경
  - [ ] WebSocket 알림 추가: `memory_loaded` 메시지
- [ ] `MainSupervisorState`에 `user_id` 필드 추가
  ```python
  user_id: Optional[int]
  ```

### ✅ 작업 4: Response Node 통합 (1일)
- [ ] `team_supervisor.py` - `generate_response_node` 수정
  - [ ] `_store_conversation_to_memory(state, response)` 메서드 추가
  - [ ] `_update_user_preferences(state)` 메서드 추가
  - [ ] `_get_turn_number(session_id)` 메서드 추가
  - [ ] `_extract_tools_used(state)` 메서드 추가
  - [ ] `_extract_price_range_from_entities(entities)` 메서드 추가
  - [ ] `_extract_property_ids(state)` 메서드 추가
  - [ ] `user_id` 있을 때만 Memory 저장 로직 추가
- [ ] `process_query_streaming()`에 `user_id` 파라미터 추가
- [ ] `chat_api.py` - WebSocket에서 `user_id` 전달
- [ ] Integration Test
  - [ ] 시나리오 1: 과거 대화 참조
  - [ ] 시나리오 2: 선호도 기반 개인화

### ✅ 작업 5: Frontend UI 구현 (2-3일)
- [ ] **대화 이력 UI** (1일)
  - [ ] `components/chat/ConversationHistory.tsx` 생성
  - [ ] 최근 10개 대화 세션 목록 표시
  - [ ] 날짜별 그룹화
  - [ ] 클릭 시 대화 로드
- [ ] **Memory 로드 표시** (1일)
  - [ ] `components/chat/PlanningIndicator.tsx` 수정
  - [ ] WebSocket `memory_loaded` 메시지 처리
  - [ ] "✅ 과거 대화 N개 참조 중" 표시
- [ ] **Memory 컨텍스트 상세** (Optional, 1일)
  - [ ] `components/chat/MemoryContextViewer.tsx` 생성
  - [ ] 참조한 대화 상세 보기 (접기/펼치기)
  - [ ] 선호도 정보 표시
- [ ] **Backend API 추가**
  - [ ] `backend/app/api/memory_api.py` 생성
    - [ ] `GET /api/v1/memory/conversations?user_id={}&limit=10`
    - [ ] `GET /api/v1/memory/statistics?user_id={}`
    - [ ] `GET /api/v1/memory/preferences?user_id={}`
  - [ ] `backend/main.py`에 router 추가
- [ ] E2E Test

### Phase 5-3: EntityMemory (선택, P1)
- [ ] update_entity_mentions 구현
- [ ] get_important_entities 구현
- [ ] Planning Agent 통합
- [ ] Test

### Phase 6: PostgreSQL 마이그레이션 (선택, P2)
- [ ] 필요성 재평가
- [ ] DATABASE_URL 변경
- [ ] Alembic migration
- [ ] 데이터 마이그레이션
- [ ] 성능 테스트

---

## 8. 참고 자료

### 8.1 관련 문서
- [Session Memory 설계 v1.0](./plan_of_architecture_session_memory_v1.md)
- [State/Context 설계 계획서 v2.0](./plan_of_state_context_design_v2.md)
- [SQLAlchemy Async 공식 문서](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

### 8.2 유사 구현 사례
- LangChain Memory: https://python.langchain.com/docs/modules/memory/
- Rasa Tracker Store: https://rasa.com/docs/rasa/tracker-stores

---

## 9. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0 | 2025-10-13 | 초안 작성 - SessionManager vs Memory 아키텍처 설계 | Claude Code |
| v1.1 | 2025-10-14 | 현황 분석 반영 - Long-term Memory 우선순위 재조정 | Claude Code |
| v1.2 | 2025-10-14 | 실행 계획 구체화 - 5단계 작업 상세 정의 | Claude Code |

**주요 변경사항 (v1.2):**
1. ✅ **5가지 핵심 작업 명확화**: DB 모델 → Memory Service → Planning Node → Response Node → Frontend UI
2. ✅ **중요 결정 사항 문서화**:
   - Memory 로드 위치: `planning_node` (not `initialize_node`)
   - Memory 로드 개수: 3-5개 (동적 조정)
   - `initialize_node` 수정 불필요
3. ✅ **Frontend UI 구현 계획 추가** (Phase 5-4):
   - ConversationHistory 컴포넌트
   - PlanningIndicator 수정 (memory_loaded 메시지)
   - MemoryContextViewer (선택)
   - Backend API 엔드포인트 (/api/v1/memory/*)
4. ✅ **체크리스트 재구성**: 5가지 작업별로 세분화
5. ✅ **즉시 실행 가능한 구현 가이드**

---

**승인자**: _______________
**승인일**: 2025-10-14
**다음 검토일**: 작업 1 (DB 모델) 완료 후
**예상 완료일**: 2025-10-22 (7-8일 후)

---

## 부록: 빠른 시작 가이드

### A. 10일 구현 계획

```
Day 1-2: DB 모델 생성 + Migration
Day 3-5: LongTermMemoryService 구현
Day 6-7: Planning Agent 통합
Day 8-9: Supervisor 통합
Day 10: 통합 테스트
```

### B. 최소 구현 (MVP, 5일)

Phase 5-3 (EntityMemory) 제외하고 핵심만 구현:
- ConversationMemory: 대화 저장
- UserPreference: 지역 선호도만
- Planning Agent: 과거 대화 참조만
- Supervisor: 대화 저장만

---

**이 문서는 실제 구현 상태를 반영하여 작성되었으며, 즉시 실행 가능한 계획입니다.**
