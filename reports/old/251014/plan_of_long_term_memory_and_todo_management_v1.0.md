# Long-term Memory & TODO Management 통합 구현 계획서

**Version**: 1.0
**Date**: 2025-10-14
**Purpose**: Long-term Memory + TODO 관리 시스템 통합 구현 가이드

---

## 📋 Executive Summary

### 프로젝트 개요

본 프로젝트는 두 가지 핵심 기능을 구현합니다:

1. **Long-term Memory**: 사용자별 대화 기록 영구 저장 및 맥락 제공
2. **TODO Management**: 실시간 작업 진행 상황 추적 및 사용자 개입

### 현재 구현 상태

| 기능 | 상태 | 구현률 |
|------|------|--------|
| **ExecutionStepState** (TODO 기본 구조) | ✅ 완료 | 100% |
| **StateManager.update_step_status()** | ✅ 완료 | 100% |
| **sessions 테이블** (user_id 저장) | ✅ 완료 | 100% |
| **User/ChatSession 모델** | ✅ 완료 | 100% |
| **Long-term Memory 모델** | ❌ 미구현 | 0% |
| **LongTermMemoryService** | ❌ 미구현 | 0% |
| **planning_node Memory 로딩** | ❌ 미구현 | 0% |
| **TODO API** (todo_api.py) | ❌ 미구현 | 0% |
| **사용자 개입 메커니즘** | ❌ 미구현 | 0% |

### 구현 우선순위

```
Phase 1: Long-term Memory (우선)
    ├── Task 1: sessions.user_id 타입 수정 (필수 선행)
    ├── Task 2: Memory 모델 생성
    ├── Task 3: LongTermMemoryService 구현
    ├── Task 4: planning_node 통합
    └── Task 5: Frontend UI

Phase 2: TODO Management (후속)
    ├── Task 6: 사용자 개입 메커니즘
    ├── Task 7: TODO API 구현
    ├── Task 8: Checkpoint 통합 강화
    └── Task 9: Frontend TODO UI
```

**총 예상 기간**: 12-14일

---

## Part A: Long-term Memory 구현

---

## A-1. sessions.user_id 타입 수정 (Task 1)

### 문제점

```sql
-- 현재 타입 불일치
sessions.user_id          VARCHAR(100)  ← 문자열
users.id                  INTEGER       ← 정수
chat_sessions.user_id     INTEGER       ← 정수
conversation_memories.user_id INTEGER   ← 정수 (예정)
```

### 해결 방법

#### Step 1-1: 모델 파일 수정

**파일**: `backend/app/models/session.py`

```python
# BEFORE (Line 26)
user_id = Column(String(100), nullable=True)

# AFTER
user_id = Column(Integer, nullable=True, index=True)
```

#### Step 1-2: Migration SQL 수정

**파일**: `backend/migrations/create_sessions_table.sql`

```sql
-- BEFORE (Line 8)
user_id VARCHAR(100),

-- AFTER
user_id INTEGER,
```

#### Step 1-3: 데이터베이스 적용

```bash
# 1. 기존 sessions 테이블 삭제 (데이터 백업 필요 시)
psql "postgresql://postgres:root1234@localhost:5432/real_estate" << EOF
DROP TABLE IF EXISTS sessions;
EOF

# 2. 수정된 SQL로 재생성
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -f backend/migrations/create_sessions_table.sql

# 3. 확인
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\d sessions"
```

**예상 출력**:
```
Column    | Type                     | Nullable
----------+--------------------------+----------
user_id   | integer                  |          ← INTEGER로 변경 확인!
```

#### Step 1-4: SessionManager 테스트

```bash
cd backend
python test_session_migration.py
```

**예상 시간**: 30분

---

## A-2. Long-term Memory 모델 생성 (Task 2)

### Step 2-1: 모델 파일 생성

**파일**: `backend/app/models/memory.py` (신규 생성)

```python
"""
Long-term Memory Models
사용자별 대화 기록 영구 저장
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    TIMESTAMP,
    ForeignKey,
    Index,
    Float
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgre_db import Base
import uuid


class ConversationMemory(Base):
    """
    대화 기록 영구 저장

    각 대화 세션의 요약과 주요 정보를 저장하여
    다음 대화 시 맥락을 제공
    """
    __tablename__ = "conversation_memories"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="사용자 ID"
    )
    session_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="원본 WebSocket 세션 ID (참조용)"
    )

    # 대화 내용
    user_query = Column(Text, nullable=False, comment="사용자 질문")
    assistant_response_summary = Column(
        Text,
        nullable=True,
        comment="AI 응답 요약 (전체 저장 시 용량 과다)"
    )
    conversation_summary = Column(
        Text,
        nullable=True,
        comment="대화 전체 요약 (LLM 생성)"
    )

    # 분류 정보
    intent_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="의도 분류 (search_real_estate, legal_consult, etc.)"
    )
    intent_confidence = Column(
        Float,
        nullable=True,
        comment="의도 분류 신뢰도 (0.0-1.0)"
    )

    # 실행 정보
    teams_used = Column(
        JSONB,
        nullable=True,
        comment="사용된 팀 목록 ['search', 'analysis']"
    )
    execution_time_ms = Column(
        Integer,
        nullable=True,
        comment="실행 시간 (밀리초)"
    )

    # 엔티티 추출
    entities_mentioned = Column(
        JSONB,
        nullable=True,
        comment="언급된 엔티티 {regions: [...], properties: [...], agents: [...]}"
    )

    # 타임스탬프
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="대화 발생 시각"
    )

    # Relationships
    user = relationship("User", back_populates="conversation_memories")

    # Indexes
    __table_args__ = (
        # 최근 대화 조회 최적화 (user_id + created_at DESC)
        Index('idx_user_created', 'user_id', 'created_at'),
        # 의도별 필터링
        Index('idx_user_intent', 'user_id', 'intent_type'),
    )


class UserPreference(Base):
    """
    사용자 선호도 추적

    반복되는 검색 패턴과 선호도를 학습하여
    개인화된 응답 제공
    """
    __tablename__ = "user_preferences"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key (Unique - 사용자당 1개)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="사용자 ID"
    )

    # 선호 지역
    preferred_regions = Column(
        JSONB,
        nullable=True,
        comment="선호 지역 ['강남구', '서초구']"
    )

    # 선호 매물 타입
    preferred_property_types = Column(
        JSONB,
        nullable=True,
        comment="선호 매물 타입 ['아파트', '오피스텔']"
    )

    # 가격 범위
    price_range = Column(
        JSONB,
        nullable=True,
        comment="선호 가격대 {min: 300000000, max: 500000000}"
    )

    # 면적 범위
    area_range = Column(
        JSONB,
        nullable=True,
        comment="선호 면적 {min: 60, max: 100} (평)"
    )

    # 검색 패턴
    search_history_summary = Column(
        JSONB,
        nullable=True,
        comment="검색 패턴 요약 {frequent_keywords: [...], peak_times: [...]}"
    )

    # 통계
    interaction_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="총 상호작용 횟수"
    )

    # 타임스탬프
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="생성 시각"
    )
    last_updated = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="마지막 업데이트 시각"
    )

    # Relationships
    user = relationship("User", back_populates="preferences")


class EntityMemory(Base):
    """
    엔티티 추적 (매물, 지역, 중개사 등)

    사용자가 관심을 보인 특정 엔티티를 추적하여
    재언급 시 빠른 조회 제공
    """
    __tablename__ = "entity_memories"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="사용자 ID"
    )

    # 엔티티 정보
    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="엔티티 타입 (real_estate, region, agent, contract)"
    )
    entity_id = Column(
        String(100),
        nullable=False,
        index=True,
        comment="엔티티 ID (예: real_estate_12345)"
    )
    entity_name = Column(
        String(200),
        nullable=True,
        comment="엔티티 이름 (표시용)"
    )

    # 추적 정보
    last_mentioned = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="마지막 언급 시각"
    )
    mention_count = Column(
        Integer,
        default=1,
        nullable=False,
        comment="언급 횟수"
    )

    # 맥락 정보
    context_summary = Column(
        Text,
        nullable=True,
        comment="언급 맥락 요약 (어떤 상황에서 언급되었는지)"
    )

    # 타임스탬프
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="첫 언급 시각"
    )

    # Relationships
    user = relationship("User", back_populates="entity_memories")

    # Indexes
    __table_args__ = (
        # 사용자별 엔티티 조회 최적화
        Index('idx_user_entity', 'user_id', 'entity_type', 'entity_id'),
        # 최근 언급 엔티티 조회
        Index('idx_user_last_mentioned', 'user_id', 'last_mentioned'),
    )
```

### Step 2-2: User 모델에 Relationship 추가

**파일**: `backend/app/models/users.py`

```python
class User(Base):
    """통합 사용자 테이블"""
    __tablename__ = "users"
    # ... 기존 필드들 ...

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    local_auth = relationship("LocalAuth", back_populates="user", uselist=False, cascade="all, delete-orphan")
    social_auths = relationship("SocialAuth", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    # ✨ NEW: Long-term Memory relationships
    conversation_memories = relationship("ConversationMemory", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    entity_memories = relationship("EntityMemory", back_populates="user", cascade="all, delete-orphan")
```

### Step 2-3: 테이블 생성

```bash
# FastAPI 서버 시작 시 자동 생성
cd backend
uvicorn app.main:app --reload

# 또는 수동으로 Python에서 실행
python << EOF
import asyncio
from app.db.postgre_db import Base, engine

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Memory tables created!")

asyncio.run(create_tables())
EOF
```

### Step 2-4: 확인

```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" << EOF
\dt conversation_memories
\dt user_preferences
\dt entity_memories

-- 인덱스 확인
\d conversation_memories
EOF
```

**예상 시간**: 2시간

---

## A-3. LongTermMemoryService 구현 (Task 3)

### Step 3-1: Service 파일 생성

**파일**: `backend/app/services/long_term_memory_service.py` (신규 생성)

```python
"""
Long-term Memory Service
사용자별 대화 기록 로드/저장 관리
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgre_db import AsyncSessionLocal
from app.models.memory import ConversationMemory, UserPreference, EntityMemory
from app.models.users import User

logger = logging.getLogger(__name__)


class LongTermMemoryService:
    """
    Long-term Memory 관리 서비스

    주요 기능:
    1. 최근 대화 기록 로드 (planning_node에서 사용)
    2. 대화 완료 후 저장 (response_node에서 사용)
    3. 사용자 선호도 업데이트
    4. 엔티티 추적
    """

    def __init__(self):
        pass

    # ============================================================================
    # 1. 대화 기록 로드 (Planning Node에서 사용)
    # ============================================================================

    async def load_recent_memories(
        self,
        user_id: int,
        limit: int = 5,
        intent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 기록 로드

        Args:
            user_id: 사용자 ID
            limit: 로드할 대화 수 (기본 5개)
            intent_filter: 특정 의도만 필터링 (선택)

        Returns:
            대화 기록 리스트
            [
                {
                    "id": uuid,
                    "user_query": str,
                    "conversation_summary": str,
                    "intent_type": str,
                    "teams_used": list,
                    "entities_mentioned": dict,
                    "created_at": str (ISO format)
                }
            ]
        """
        async with AsyncSessionLocal() as db:
            try:
                # Base query
                query = select(ConversationMemory).where(
                    ConversationMemory.user_id == user_id
                )

                # Intent filter (optional)
                if intent_filter:
                    query = query.where(ConversationMemory.intent_type == intent_filter)

                # Order by created_at DESC, limit
                query = query.order_by(desc(ConversationMemory.created_at)).limit(limit)

                result = await db.execute(query)
                memories = result.scalars().all()

                # Convert to dict
                memory_list = []
                for memory in memories:
                    memory_list.append({
                        "id": str(memory.id),
                        "user_query": memory.user_query,
                        "conversation_summary": memory.conversation_summary,
                        "intent_type": memory.intent_type,
                        "teams_used": memory.teams_used or [],
                        "entities_mentioned": memory.entities_mentioned or {},
                        "created_at": memory.created_at.isoformat()
                    })

                logger.info(
                    f"📚 Loaded {len(memory_list)} memories for user {user_id}"
                    f"{f' (intent: {intent_filter})' if intent_filter else ''}"
                )

                return memory_list

            except Exception as e:
                logger.error(f"Failed to load memories for user {user_id}: {e}")
                return []

    async def get_user_preferences(
        self,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 선호도 조회

        Args:
            user_id: 사용자 ID

        Returns:
            선호도 정보 또는 None
            {
                "preferred_regions": list,
                "preferred_property_types": list,
                "price_range": dict,
                "area_range": dict,
                "interaction_count": int
            }
        """
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(UserPreference).where(UserPreference.user_id == user_id)
                )
                preference = result.scalar_one_or_none()

                if not preference:
                    logger.info(f"No preferences found for user {user_id}")
                    return None

                return {
                    "preferred_regions": preference.preferred_regions or [],
                    "preferred_property_types": preference.preferred_property_types or [],
                    "price_range": preference.price_range or {},
                    "area_range": preference.area_range or {},
                    "interaction_count": preference.interaction_count,
                    "last_updated": preference.last_updated.isoformat()
                }

            except Exception as e:
                logger.error(f"Failed to get preferences for user {user_id}: {e}")
                return None

    async def get_recent_entities(
        self,
        user_id: int,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 언급된 엔티티 조회

        Args:
            user_id: 사용자 ID
            entity_type: 엔티티 타입 필터 (선택)
            limit: 조회 개수

        Returns:
            엔티티 리스트
        """
        async with AsyncSessionLocal() as db:
            try:
                query = select(EntityMemory).where(EntityMemory.user_id == user_id)

                if entity_type:
                    query = query.where(EntityMemory.entity_type == entity_type)

                query = query.order_by(desc(EntityMemory.last_mentioned)).limit(limit)

                result = await db.execute(query)
                entities = result.scalars().all()

                entity_list = []
                for entity in entities:
                    entity_list.append({
                        "entity_type": entity.entity_type,
                        "entity_id": entity.entity_id,
                        "entity_name": entity.entity_name,
                        "mention_count": entity.mention_count,
                        "last_mentioned": entity.last_mentioned.isoformat()
                    })

                return entity_list

            except Exception as e:
                logger.error(f"Failed to get entities for user {user_id}: {e}")
                return []

    # ============================================================================
    # 2. 대화 저장 (Response Node에서 사용)
    # ============================================================================

    async def save_conversation(
        self,
        user_id: int,
        session_id: str,
        user_query: str,
        assistant_response_summary: Optional[str],
        conversation_summary: Optional[str],
        intent_type: Optional[str],
        intent_confidence: Optional[float],
        teams_used: Optional[List[str]],
        entities_mentioned: Optional[Dict[str, Any]],
        execution_time_ms: Optional[int]
    ) -> bool:
        """
        대화 기록 저장

        Args:
            user_id: 사용자 ID
            session_id: WebSocket 세션 ID
            user_query: 사용자 질문
            assistant_response_summary: AI 응답 요약
            conversation_summary: 대화 전체 요약 (LLM 생성)
            intent_type: 의도 분류
            intent_confidence: 의도 신뢰도
            teams_used: 사용된 팀 목록
            entities_mentioned: 언급된 엔티티
            execution_time_ms: 실행 시간

        Returns:
            성공 여부
        """
        async with AsyncSessionLocal() as db:
            try:
                new_memory = ConversationMemory(
                    user_id=user_id,
                    session_id=session_id,
                    user_query=user_query,
                    assistant_response_summary=assistant_response_summary,
                    conversation_summary=conversation_summary,
                    intent_type=intent_type,
                    intent_confidence=intent_confidence,
                    teams_used=teams_used,
                    entities_mentioned=entities_mentioned,
                    execution_time_ms=execution_time_ms
                )

                db.add(new_memory)
                await db.commit()
                await db.refresh(new_memory)

                logger.info(
                    f"💾 Saved conversation memory for user {user_id} "
                    f"(session: {session_id}, intent: {intent_type})"
                )

                # 엔티티 추적 업데이트
                if entities_mentioned:
                    await self._update_entity_tracking(
                        db, user_id, entities_mentioned
                    )

                return True

            except Exception as e:
                logger.error(f"Failed to save conversation for user {user_id}: {e}")
                await db.rollback()
                return False

    async def _update_entity_tracking(
        self,
        db: AsyncSession,
        user_id: int,
        entities: Dict[str, Any]
    ):
        """
        엔티티 추적 업데이트 (내부 메서드)

        entities 예시:
        {
            "regions": ["강남구", "서초구"],
            "properties": ["real_estate_12345"],
            "agents": ["agent_789"]
        }
        """
        try:
            for entity_type, entity_ids in entities.items():
                if not entity_ids:
                    continue

                for entity_id in entity_ids:
                    # 기존 엔티티 조회
                    result = await db.execute(
                        select(EntityMemory).where(
                            EntityMemory.user_id == user_id,
                            EntityMemory.entity_type == entity_type,
                            EntityMemory.entity_id == str(entity_id)
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # 기존 엔티티 업데이트
                        existing.last_mentioned = datetime.now(timezone.utc)
                        existing.mention_count += 1
                    else:
                        # 새 엔티티 생성
                        new_entity = EntityMemory(
                            user_id=user_id,
                            entity_type=entity_type,
                            entity_id=str(entity_id),
                            entity_name=str(entity_id),  # TODO: 실제 이름 조회
                            mention_count=1
                        )
                        db.add(new_entity)

            await db.commit()
            logger.debug(f"Updated entity tracking for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update entity tracking: {e}")
            await db.rollback()

    # ============================================================================
    # 3. 선호도 업데이트 (점진적 학습)
    # ============================================================================

    async def update_user_preferences(
        self,
        user_id: int,
        regions: Optional[List[str]] = None,
        property_types: Optional[List[str]] = None,
        price_range: Optional[Dict[str, int]] = None,
        area_range: Optional[Dict[str, int]] = None
    ) -> bool:
        """
        사용자 선호도 업데이트 (점진적 축적)

        Args:
            user_id: 사용자 ID
            regions: 언급된 지역
            property_types: 언급된 매물 타입
            price_range: 언급된 가격대
            area_range: 언급된 면적

        Returns:
            성공 여부
        """
        async with AsyncSessionLocal() as db:
            try:
                # 기존 선호도 조회
                result = await db.execute(
                    select(UserPreference).where(UserPreference.user_id == user_id)
                )
                preference = result.scalar_one_or_none()

                if not preference:
                    # 새 선호도 생성
                    preference = UserPreference(
                        user_id=user_id,
                        preferred_regions=regions or [],
                        preferred_property_types=property_types or [],
                        price_range=price_range or {},
                        area_range=area_range or {},
                        interaction_count=1
                    )
                    db.add(preference)
                else:
                    # 기존 선호도 업데이트 (병합 로직)
                    if regions:
                        current_regions = set(preference.preferred_regions or [])
                        current_regions.update(regions)
                        preference.preferred_regions = list(current_regions)[:10]  # 최대 10개

                    if property_types:
                        current_types = set(preference.preferred_property_types or [])
                        current_types.update(property_types)
                        preference.preferred_property_types = list(current_types)

                    if price_range:
                        # 가격대 업데이트 (평균 또는 최신 값)
                        preference.price_range = price_range

                    if area_range:
                        preference.area_range = area_range

                    preference.interaction_count += 1

                await db.commit()
                logger.info(f"Updated preferences for user {user_id}")

                return True

            except Exception as e:
                logger.error(f"Failed to update preferences for user {user_id}: {e}")
                await db.rollback()
                return False

    # ============================================================================
    # 4. 통계 조회 (Frontend API용)
    # ============================================================================

    async def get_user_statistics(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        사용자 통계 조회

        Returns:
            {
                "total_conversations": int,
                "total_interactions": int,
                "most_used_intent": str,
                "recent_activity": str (ISO format)
            }
        """
        async with AsyncSessionLocal() as db:
            try:
                # 총 대화 수
                total_conv_result = await db.execute(
                    select(func.count(ConversationMemory.id)).where(
                        ConversationMemory.user_id == user_id
                    )
                )
                total_conversations = total_conv_result.scalar() or 0

                # 가장 많이 사용된 의도
                intent_result = await db.execute(
                    select(
                        ConversationMemory.intent_type,
                        func.count(ConversationMemory.id).label('count')
                    )
                    .where(ConversationMemory.user_id == user_id)
                    .group_by(ConversationMemory.intent_type)
                    .order_by(desc('count'))
                    .limit(1)
                )
                intent_row = intent_result.first()
                most_used_intent = intent_row[0] if intent_row else "N/A"

                # 최근 활동 시각
                recent_result = await db.execute(
                    select(ConversationMemory.created_at)
                    .where(ConversationMemory.user_id == user_id)
                    .order_by(desc(ConversationMemory.created_at))
                    .limit(1)
                )
                recent_row = recent_result.scalar_one_or_none()
                recent_activity = recent_row.isoformat() if recent_row else None

                # 선호도 interaction_count
                pref_result = await db.execute(
                    select(UserPreference.interaction_count).where(
                        UserPreference.user_id == user_id
                    )
                )
                interaction_count = pref_result.scalar_one_or_none() or 0

                return {
                    "total_conversations": total_conversations,
                    "total_interactions": interaction_count,
                    "most_used_intent": most_used_intent,
                    "recent_activity": recent_activity
                }

            except Exception as e:
                logger.error(f"Failed to get statistics for user {user_id}: {e}")
                return {
                    "total_conversations": 0,
                    "total_interactions": 0,
                    "most_used_intent": "N/A",
                    "recent_activity": None
                }
```

**예상 시간**: 4-5시간

---

## A-4. Planning Node 통합 (Task 4)

### Step 4-1: chat_api.py 수정 (user_id 추출)

**파일**: `backend/app/api/chat_api.py`

**수정 위치**: `websocket_chat()` 함수 (Line ~225)

```python
@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    # ... (기존 코드: 세션 검증, WebSocket 연결) ...

    # ✨ NEW: user_id 추출
    session_info = await session_mgr.get_session(session_id)
    user_id = session_info.get("user_id") if session_info else None

    if user_id:
        logger.info(f"User {user_id} connected to session {session_id}")
    else:
        logger.info(f"Anonymous user connected to session {session_id}")

    # ... (기존 코드: Supervisor 가져오기) ...

    # Query 처리
    if message_type == "query":
        asyncio.create_task(
            _process_query_async(
                supervisor=supervisor,
                query=query,
                session_id=session_id,
                user_id=user_id,  # ✨ NEW: user_id 전달
                enable_checkpointing=enable_checkpointing,
                progress_callback=progress_callback,
                conn_mgr=conn_mgr
            )
        )
```

### Step 4-2: _process_query_async 수정

**수정 위치**: `_process_query_async()` 함수 (Line ~318)

```python
async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    user_id: Optional[int],  # ✨ NEW parameter
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager
):
    """쿼리 비동기 처리"""
    try:
        # Streaming 방식으로 쿼리 처리
        result = await supervisor.process_query_streaming(
            query=query,
            session_id=session_id,
            user_id=user_id,  # ✨ NEW: user_id 전달
            progress_callback=progress_callback
        )

        # ... (기존 코드: 결과 전송) ...

    except Exception as e:
        logger.error(f"Query processing error: {e}")
        # ... (기존 에러 처리) ...
```

### Step 4-3: team_supervisor.py 수정 (process_query_streaming)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**수정 위치**: `process_query_streaming()` 함수

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str,
    user_id: Optional[int] = None,  # ✨ NEW parameter
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Query 처리 (Streaming 방식)

    Args:
        query: 사용자 질문
        session_id: Session ID
        user_id: User ID (Long-term Memory용)  # ✨ NEW
        progress_callback: Progress callback
    """
    # ... (기존 코드) ...

    # Initial state 생성
    initial_state = {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,  # ✨ NEW: user_id 포함
        # ... 기존 필드들 ...
    }

    # LangGraph 실행
    result = await self.workflow.ainvoke(
        initial_state,
        config=config
    )

    return result
```

### Step 4-4: planning_node 수정 (Memory 로드)

**수정 위치**: `planning_node()` 함수 (Line ~169)

```python
async def planning_node(self, state: MainSupervisorState):
    """계획 수립 노드"""
    logger.info("[TeamSupervisor] Planning phase")

    state["current_phase"] = "planning"
    query = state.get("query", "")
    user_id = state.get("user_id")  # ✨ NEW: user_id 추출

    # ============================================================================
    # ✨ NEW: Long-term Memory 로드 (user_id가 있을 때만)
    # ============================================================================
    if user_id:
        try:
            from app.services.long_term_memory_service import LongTermMemoryService

            memory_service = LongTermMemoryService()

            # 최근 대화 5개 로드
            loaded_memories = await memory_service.load_recent_memories(
                user_id=user_id,
                limit=5
            )

            # 사용자 선호도 로드
            user_preferences = await memory_service.get_user_preferences(user_id)

            # State에 저장
            state["loaded_memories"] = loaded_memories
            state["user_preferences"] = user_preferences
            state["memory_load_time"] = datetime.now().isoformat()

            logger.info(
                f"📚 Loaded {len(loaded_memories)} memories for user {user_id}"
            )

            # Progress callback
            if self._progress_callbacks.get(state.get("session_id")):
                callback = self._progress_callbacks[state["session_id"]]
                await callback("memory_loaded", {
                    "user_id": user_id,
                    "memory_count": len(loaded_memories),
                    "has_preferences": user_preferences is not None
                })

        except Exception as e:
            logger.error(f"Failed to load long-term memory: {e}")
            # Memory 로드 실패해도 계속 진행
            state["loaded_memories"] = []
            state["user_preferences"] = None
    else:
        logger.info("Anonymous user - skipping long-term memory loading")
        state["loaded_memories"] = []
        state["user_preferences"] = None

    # ============================================================================
    # 기존 Planning 로직 (그대로 유지)
    # ============================================================================
    intent_result = await self.planning_agent.analyze_intent(query)
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # ... (기존 코드 계속) ...

    return state
```

### Step 4-5: response_node 수정 (Memory 저장)

**수정 위치**: `response_node()` 또는 적절한 종료 지점

```python
async def response_node(self, state: MainSupervisorState):
    """
    최종 응답 생성 노드

    ✨ NEW: Long-term Memory 저장 추가
    """
    logger.info("[TeamSupervisor] Response generation phase")

    # ... (기존 응답 생성 로직) ...

    # ============================================================================
    # ✨ NEW: Long-term Memory 저장
    # ============================================================================
    user_id = state.get("user_id")
    if user_id:
        try:
            from app.services.long_term_memory_service import LongTermMemoryService

            memory_service = LongTermMemoryService()

            # 대화 정보 추출
            planning_state = state.get("planning_state", {})
            intent_info = planning_state.get("analyzed_intent", {})

            # 엔티티 추출 (간단한 예시)
            entities_mentioned = self._extract_entities(state)

            # 실행 시간 계산
            execution_time_ms = None
            if state.get("start_time") and state.get("end_time"):
                delta = state["end_time"] - state["start_time"]
                execution_time_ms = int(delta.total_seconds() * 1000)

            # 저장
            await memory_service.save_conversation(
                user_id=user_id,
                session_id=state.get("session_id"),
                user_query=state.get("query"),
                assistant_response_summary=self._summarize_response(state),
                conversation_summary=None,  # TODO: LLM으로 요약 생성
                intent_type=intent_info.get("intent_type"),
                intent_confidence=planning_state.get("intent_confidence"),
                teams_used=state.get("completed_teams", []),
                entities_mentioned=entities_mentioned,
                execution_time_ms=execution_time_ms
            )

            logger.info(f"💾 Saved conversation to long-term memory (user {user_id})")

        except Exception as e:
            logger.error(f"Failed to save long-term memory: {e}")
            # 저장 실패해도 응답은 계속 진행

    return state

def _extract_entities(self, state: MainSupervisorState) -> Dict[str, Any]:
    """대화에서 언급된 엔티티 추출 (간단한 구현)"""
    entities = {
        "regions": [],
        "properties": [],
        "agents": []
    }

    # TODO: 실제 엔티티 추출 로직 구현
    # 예시: state["team_results"]에서 real_estate_results 추출

    return entities

def _summarize_response(self, state: MainSupervisorState) -> str:
    """응답 요약 생성"""
    final_response = state.get("final_response", {})
    # TODO: 응답 요약 로직 구현
    return final_response.get("summary", "")[:500]  # 최대 500자
```

### Step 4-6: MainSupervisorState 확장

**파일**: `backend/app/service_agent/foundation/separated_states.py`

```python
class MainSupervisorState(TypedDict, total=False):
    """메인 Supervisor의 State"""
    # ... 기존 필드들 ...

    # ✨ NEW: Long-term Memory fields
    user_id: Optional[int]  # 사용자 ID (로그인 시)
    loaded_memories: Optional[List[Dict[str, Any]]]  # 로드된 과거 대화
    user_preferences: Optional[Dict[str, Any]]  # 사용자 선호도
    memory_load_time: Optional[str]  # 메모리 로드 시각
```

**예상 시간**: 3-4시간

---

## A-5. Frontend UI (Task 5)

### Step 5-1: Conversation History Component

**파일**: `frontend/src/components/ConversationHistory.tsx` (신규 생성)

```typescript
import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';

interface Conversation {
  id: string;
  user_query: string;
  conversation_summary: string;
  intent_type: string;
  created_at: string;
}

interface ConversationHistoryProps {
  userId: number;
  onSelectConversation?: (conversation: Conversation) => void;
}

export default function ConversationHistory({
  userId,
  onSelectConversation
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConversations();
  }, [userId]);

  const fetchConversations = async () => {
    try {
      const response = await fetch(`/api/v1/memory/conversations?user_id=${userId}&limit=10`);
      const data = await response.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to fetch conversation history:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading conversation history...</div>;
  }

  return (
    <div className="conversation-history">
      <h3>Past Conversations</h3>
      <div className="conversation-list">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className="conversation-item"
            onClick={() => onSelectConversation?.(conv)}
          >
            <div className="conversation-query">
              {conv.user_query.substring(0, 50)}...
            </div>
            <div className="conversation-meta">
              <span className="intent-badge">{conv.intent_type}</span>
              <span className="created-at">
                {format(new Date(conv.created_at), 'yyyy-MM-dd HH:mm')}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Step 5-2: Memory Loaded Indicator

**파일**: `frontend/src/components/MemoryLoadedIndicator.tsx` (신규 생성)

```typescript
import React from 'react';

interface MemoryLoadedIndicatorProps {
  memoryCount: number;
  hasPreferences: boolean;
}

export default function MemoryLoadedIndicator({
  memoryCount,
  hasPreferences
}: MemoryLoadedIndicatorProps) {
  if (memoryCount === 0 && !hasPreferences) {
    return null;
  }

  return (
    <div className="memory-loaded-indicator">
      <span className="icon">📚</span>
      <span className="text">
        {memoryCount > 0 && `${memoryCount} past conversations loaded`}
        {hasPreferences && ` • Preferences applied`}
      </span>
    </div>
  );
}
```

### Step 5-3: WebSocket Handler 수정

**파일**: WebSocket 메시지 처리 로직

```typescript
// WebSocket message handler에 추가
case 'memory_loaded':
  const { memory_count, has_preferences } = data;
  console.log(`📚 Loaded ${memory_count} memories`);

  // UI 업데이트
  setMemoryLoadedState({
    count: memory_count,
    hasPreferences: has_preferences
  });
  break;
```

### Step 5-4: Backend API Endpoints 추가

**파일**: `backend/app/api/memory_api.py` (신규 생성)

```python
"""
Long-term Memory API
사용자별 대화 기록 조회
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.long_term_memory_service import LongTermMemoryService

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

memory_service = LongTermMemoryService()


@router.get("/conversations")
async def get_user_conversations(
    user_id: int,
    limit: int = 10,
    intent_filter: Optional[str] = None
):
    """
    사용자 대화 기록 조회

    Query Parameters:
        user_id: 사용자 ID
        limit: 조회 개수 (기본 10)
        intent_filter: 의도 필터 (선택)

    Returns:
        {
            "conversations": [
                {
                    "id": uuid,
                    "user_query": str,
                    "conversation_summary": str,
                    "intent_type": str,
                    "created_at": str
                }
            ],
            "total": int
        }
    """
    memories = await memory_service.load_recent_memories(
        user_id=user_id,
        limit=limit,
        intent_filter=intent_filter
    )

    return {
        "conversations": memories,
        "total": len(memories)
    }


@router.get("/preferences")
async def get_user_preferences(user_id: int):
    """사용자 선호도 조회"""
    preferences = await memory_service.get_user_preferences(user_id)

    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return preferences


@router.get("/statistics")
async def get_user_statistics(user_id: int):
    """사용자 통계 조회"""
    stats = await memory_service.get_user_statistics(user_id)
    return stats


@router.get("/entities")
async def get_recent_entities(
    user_id: int,
    entity_type: Optional[str] = None,
    limit: int = 10
):
    """최근 언급된 엔티티 조회"""
    entities = await memory_service.get_recent_entities(
        user_id=user_id,
        entity_type=entity_type,
        limit=limit
    )

    return {
        "entities": entities,
        "total": len(entities)
    }
```

**예상 시간**: 4-5시간

---

## Part B: TODO Management 구현

---

## B-1. 현재 구현 상태 확인

### ✅ 이미 구현된 것들

1. **ExecutionStepState** (`separated_states.py:239-269`)
   - step_id, step_type, agent_name, team
   - task, description
   - status, progress_percentage
   - started_at, completed_at
   - result, error

2. **StateManager.update_step_status()** (`separated_states.py:353-405`)
   - 상태 업데이트
   - 시간 추적
   - 에러 기록

3. **PlanningState.execution_steps** (`separated_states.py:278`)
   - List[ExecutionStepState] 타입 명시

### ❌ 아직 구현되지 않은 것들

1. **사용자 개입 메커니즘**
   - modify_step_by_user()
   - add_step_by_user()
   - remove_step_by_user()
   - approve_plan()

2. **TODO API** (`api/todo_api.py`)
   - GET /todos/{session_id}
   - POST /todos/{session_id}/modify
   - POST /todos/{session_id}/approve

3. **Checkpoint 통합 강화**
   - list_checkpoints()
   - rollback_to_checkpoint()

---

## B-2. 사용자 개입 메커니즘 (Task 6)

### Step 6-1: StateManager에 사용자 수정 메서드 추가

**파일**: `backend/app/service_agent/foundation/separated_states.py`

**추가 위치**: `StateManager` 클래스 (Line ~344 이후)

```python
class StateManager:
    # ... 기존 메서드들 ...

    # ============================================================================
    # 사용자 개입 메서드 (NEW)
    # ============================================================================

    @staticmethod
    def modify_step_by_user(
        planning_state: PlanningState,
        step_id: str,
        modifications: Dict[str, Any],
        reason: Optional[str] = None
    ) -> PlanningState:
        """
        사용자에 의한 step 수정

        Args:
            planning_state: Planning State
            step_id: 수정할 step ID
            modifications: 수정할 필드들 {"field": new_value}
            reason: 수정 이유

        Returns:
            업데이트된 planning_state
        """
        for step in planning_state["execution_steps"]:
            if step["step_id"] == step_id:
                # 수정 적용
                for field, new_value in modifications.items():
                    if field in step:
                        old_value = step[field]
                        step[field] = new_value

                        logger.info(
                            f"User modified step {step_id}: "
                            f"{field} = {old_value} -> {new_value}"
                            f"{f' (reason: {reason})' if reason else ''}"
                        )
                break

        return planning_state

    @staticmethod
    def add_step_by_user(
        planning_state: PlanningState,
        new_step: ExecutionStepState,
        reason: Optional[str] = None
    ) -> PlanningState:
        """사용자가 새 TODO 추가"""
        planning_state["execution_steps"].append(new_step)

        logger.info(
            f"User added step {new_step['step_id']}: {new_step['task']}"
            f"{f' (reason: {reason})' if reason else ''}"
        )

        return planning_state

    @staticmethod
    def remove_step_by_user(
        planning_state: PlanningState,
        step_id: str,
        reason: Optional[str] = None
    ) -> PlanningState:
        """사용자가 TODO 제거"""
        removed_step = None
        for i, step in enumerate(planning_state["execution_steps"]):
            if step["step_id"] == step_id:
                removed_step = planning_state["execution_steps"].pop(i)
                break

        if removed_step:
            logger.info(
                f"User removed step {step_id}: {removed_step['task']}"
                f"{f' (reason: {reason})' if reason else ''}"
            )

        return planning_state

    @staticmethod
    def calculate_overall_progress(
        planning_state: PlanningState
    ) -> int:
        """
        전체 진행률 계산

        Returns:
            진행률 (0-100)
        """
        steps = planning_state["execution_steps"]
        total = len(steps)

        if total == 0:
            return 0

        completed = sum(1 for s in steps if s["status"] == "completed")
        in_progress_sum = sum(
            s.get("progress_percentage", 0)
            for s in steps
            if s["status"] == "in_progress"
        )

        # 전체 진행률 = (완료 100% + 진행중 부분%) / 전체
        overall = ((completed * 100) + in_progress_sum) / total

        return int(overall)
```

**예상 시간**: 1-2시간

---

## B-3. TODO API 구현 (Task 7)

### Step 7-1: API 파일 생성

**파일**: `backend/app/api/todo_api.py` (신규 생성)

```python
"""
TODO 관리 API
실시간 작업 진행 상황 조회 및 사용자 개입
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.service_agent.foundation.separated_states import (
    ExecutionStepState,
    StateManager
)
from app.service_agent.foundation.checkpointer import CheckpointerManager

router = APIRouter(prefix="/api/v1/todos", tags=["todos"])

checkpointer_mgr = CheckpointerManager()


# ============================================================================
# Request/Response Models
# ============================================================================

class StepModificationRequest(BaseModel):
    """Step 수정 요청"""
    step_id: str
    modifications: Dict[str, Any]
    reason: Optional[str] = None


class AddStepRequest(BaseModel):
    """Step 추가 요청"""
    step_type: str
    agent_name: str
    team: str
    task: str
    description: str
    reason: Optional[str] = None


class RemoveStepRequest(BaseModel):
    """Step 제거 요청"""
    step_id: str
    reason: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/{session_id}")
async def get_todos(session_id: str):
    """
    TODO 리스트 조회

    Returns:
        {
            "session_id": str,
            "execution_steps": List[ExecutionStepState],
            "overall_progress": int,
            "current_phase": str
        }
    """
    # Checkpoint에서 최신 state 로드
    state = await checkpointer_mgr.get_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    planning_state = state.get("planning_state")

    if not planning_state:
        raise HTTPException(status_code=404, detail="No planning state found")

    # 전체 진행률 계산
    overall_progress = StateManager.calculate_overall_progress(planning_state)

    return {
        "session_id": session_id,
        "execution_steps": planning_state["execution_steps"],
        "overall_progress": overall_progress,
        "current_phase": state.get("current_phase", "unknown")
    }


@router.get("/{session_id}/progress")
async def get_progress(session_id: str):
    """
    진행률만 간단히 조회

    Returns:
        {
            "overall_progress": int,
            "current_step": str,
            "completed_count": int,
            "total_count": int
        }
    """
    state = await checkpointer_mgr.get_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    planning_state = state.get("planning_state")
    steps = planning_state["execution_steps"]

    # 전체 진행률
    overall_progress = StateManager.calculate_overall_progress(planning_state)

    # 현재 실행 중인 step
    current_step = None
    for step in steps:
        if step["status"] == "in_progress":
            current_step = step["task"]
            break

    # 완료/총 개수
    completed_count = sum(1 for s in steps if s["status"] == "completed")
    total_count = len(steps)

    return {
        "overall_progress": overall_progress,
        "current_step": current_step,
        "completed_count": completed_count,
        "total_count": total_count
    }


@router.post("/{session_id}/modify")
async def modify_step(session_id: str, request: StepModificationRequest):
    """
    Step 수정

    Example:
        POST /api/v1/todos/session-123/modify
        {
            "step_id": "step_0",
            "modifications": {
                "task": "Updated task name",
                "description": "Updated description"
            },
            "reason": "사용자 요청"
        }
    """
    state = await checkpointer_mgr.get_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    planning_state = state.get("planning_state")

    # 수정 적용
    planning_state = StateManager.modify_step_by_user(
        planning_state,
        request.step_id,
        request.modifications,
        request.reason
    )

    state["planning_state"] = planning_state

    # State 저장
    await checkpointer_mgr.save_state(session_id, state)

    return {
        "success": True,
        "modified_step_id": request.step_id
    }


@router.post("/{session_id}/add")
async def add_step(session_id: str, request: AddStepRequest):
    """
    Step 추가

    Example:
        POST /api/v1/todos/session-123/add
        {
            "step_type": "analysis",
            "agent_name": "analysis_team",
            "team": "analysis",
            "task": "추가 분석 수행",
            "description": "사용자 요청에 따른 추가 분석",
            "reason": "더 상세한 분석 필요"
        }
    """
    state = await checkpointer_mgr.get_state(session_id)
    planning_state = state.get("planning_state")

    # 새 step 생성
    new_step_id = f"step_user_{len(planning_state['execution_steps'])}"
    new_step = ExecutionStepState(
        step_id=new_step_id,
        step_type=request.step_type,
        agent_name=request.agent_name,
        team=request.team,
        task=request.task,
        description=request.description,
        status="pending",
        progress_percentage=0,
        started_at=None,
        completed_at=None,
        result=None,
        error=None
    )

    # 추가
    planning_state = StateManager.add_step_by_user(
        planning_state,
        new_step,
        request.reason
    )

    state["planning_state"] = planning_state
    await checkpointer_mgr.save_state(session_id, state)

    return {
        "success": True,
        "new_step_id": new_step_id
    }


@router.delete("/{session_id}/{step_id}")
async def remove_step(
    session_id: str,
    step_id: str,
    reason: Optional[str] = None
):
    """
    Step 제거

    Example:
        DELETE /api/v1/todos/session-123/step_0?reason=불필요한+작업
    """
    state = await checkpointer_mgr.get_state(session_id)
    planning_state = state.get("planning_state")

    planning_state = StateManager.remove_step_by_user(
        planning_state,
        step_id,
        reason
    )

    state["planning_state"] = planning_state
    await checkpointer_mgr.save_state(session_id, state)

    return {
        "success": True,
        "removed_step_id": step_id
    }
```

**예상 시간**: 3-4시간

---

## B-4. Checkpoint 통합 강화 (Task 8)

### Step 8-1: CheckpointerManager 확장

**파일**: `backend/app/service_agent/foundation/checkpointer.py`

```python
class CheckpointerManager:
    # ... 기존 메서드들 ...

    async def get_state(
        self,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        State 조회

        Args:
            session_id: Session ID (thread_id)
            checkpoint_id: 특정 checkpoint ID (None이면 최신)

        Returns:
            복원된 state
        """
        checkpointer = await self.create_checkpointer()

        config = {"configurable": {"thread_id": session_id}}

        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id

        # LangGraph의 get_tuple() 사용
        state_snapshot = await checkpointer.aget_tuple(config)

        if state_snapshot:
            return state_snapshot.values  # State dict

        return None

    async def save_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ):
        """
        State 저장 (checkpoint)

        Args:
            session_id: Session ID
            state: 저장할 state
        """
        checkpointer = await self.create_checkpointer()

        config = {"configurable": {"thread_id": session_id}}

        # LangGraph의 put() 사용
        await checkpointer.aput(config, state, {})

        logger.info(f"Saved state for session {session_id}")

    async def list_checkpoints(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Session의 모든 checkpoint 목록

        Returns:
            [
                {
                    "checkpoint_id": str,
                    "parent_id": str,
                    "metadata": dict
                }
            ]
        """
        # PostgreSQL에서 조회
        from app.db.postgre_db import AsyncSessionLocal
        from sqlalchemy import select, text

        async with AsyncSessionLocal() as db:
            # checkpoints 테이블에서 조회
            query = text("""
                SELECT checkpoint_id, parent_checkpoint_id, metadata
                FROM checkpoints
                WHERE thread_id = :thread_id
                ORDER BY checkpoint_id DESC
            """)

            result = await db.execute(query, {"thread_id": session_id})
            rows = result.fetchall()

            checkpoints = []
            for row in rows:
                checkpoints.append({
                    "checkpoint_id": row[0],
                    "parent_id": row[1],
                    "metadata": row[2] or {}
                })

            return checkpoints
```

**예상 시간**: 2-3시간

---

## B-5. Frontend TODO UI (Task 9)

### Step 9-1: TODO List Component

**파일**: `frontend/src/components/TodoList.tsx` (신규 생성)

```typescript
import React, { useState, useEffect } from 'react';

interface TodoStep {
  step_id: string;
  step_type: string;
  task: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  progress_percentage: number;
}

interface TodoListProps {
  sessionId: string;
}

export default function TodoList({ sessionId }: TodoListProps) {
  const [steps, setSteps] = useState<TodoStep[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);

  useEffect(() => {
    fetchTodos();
    const interval = setInterval(fetchTodos, 2000); // 2초마다 업데이트

    return () => clearInterval(interval);
  }, [sessionId]);

  const fetchTodos = async () => {
    try {
      const response = await fetch(`/api/v1/todos/${sessionId}`);
      const data = await response.json();

      setSteps(data.execution_steps || []);
      setOverallProgress(data.overall_progress || 0);
    } catch (error) {
      console.error('Failed to fetch todos:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'in_progress': return '🔄';
      case 'failed': return '❌';
      case 'pending': return '⏳';
      case 'skipped': return '⏭️';
      default: return '❓';
    }
  };

  return (
    <div className="todo-list">
      <div className="overall-progress">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
        <span className="progress-text">{overallProgress}%</span>
      </div>

      <div className="todo-steps">
        {steps.map((step) => (
          <div key={step.step_id} className={`todo-item status-${step.status}`}>
            <span className="status-icon">{getStatusIcon(step.status)}</span>
            <div className="todo-content">
              <div className="todo-task">{step.task}</div>
              <div className="todo-description">{step.description}</div>
              {step.status === 'in_progress' && (
                <div className="step-progress">
                  <div
                    className="step-progress-fill"
                    style={{ width: `${step.progress_percentage}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**예상 시간**: 3-4시간

---

## 최종 요약

### 구현 순서 및 시간 배분

| Task | 내용 | 예상 시간 | 우선순위 |
|------|------|-----------|----------|
| **Task 1** | sessions.user_id 타입 수정 | 30분 | 🔴 최우선 |
| **Task 2** | Memory 모델 생성 | 2시간 | 🔴 최우선 |
| **Task 3** | LongTermMemoryService 구현 | 4-5시간 | 🔴 최우선 |
| **Task 4** | planning_node 통합 | 3-4시간 | 🔴 최우선 |
| **Task 5** | Frontend UI (Memory) | 4-5시간 | 🟡 중요 |
| **Task 6** | 사용자 개입 메커니즘 | 1-2시간 | 🟡 중요 |
| **Task 7** | TODO API 구현 | 3-4시간 | 🟡 중요 |
| **Task 8** | Checkpoint 통합 강화 | 2-3시간 | 🟢 보통 |
| **Task 9** | Frontend TODO UI | 3-4시간 | 🟢 보통 |

**총 예상 시간**: 23-30시간 (약 3-4 근무일)

### 체크리스트

#### Phase 1: Long-term Memory (Day 1-2)
- [ ] Task 1: sessions.user_id 타입 수정
  - [ ] models/session.py 수정
  - [ ] migrations/create_sessions_table.sql 수정
  - [ ] 데이터베이스 적용
  - [ ] SessionManager 테스트

- [ ] Task 2: Memory 모델 생성
  - [ ] models/memory.py 생성
  - [ ] ConversationMemory 모델
  - [ ] UserPreference 모델
  - [ ] EntityMemory 모델
  - [ ] User 모델에 relationship 추가
  - [ ] 테이블 생성 확인

- [ ] Task 3: LongTermMemoryService 구현
  - [ ] services/long_term_memory_service.py 생성
  - [ ] load_recent_memories() 구현
  - [ ] save_conversation() 구현
  - [ ] get_user_preferences() 구현
  - [ ] update_user_preferences() 구현

#### Phase 2: Workflow 통합 (Day 3)
- [ ] Task 4: planning_node 통합
  - [ ] chat_api.py user_id 추출
  - [ ] _process_query_async user_id 전달
  - [ ] process_query_streaming user_id 전달
  - [ ] planning_node Memory 로드
  - [ ] response_node Memory 저장
  - [ ] MainSupervisorState 확장

#### Phase 3: Frontend (Day 4)
- [ ] Task 5: Frontend UI (Memory)
  - [ ] ConversationHistory.tsx 생성
  - [ ] MemoryLoadedIndicator.tsx 생성
  - [ ] WebSocket handler 수정
  - [ ] memory_api.py 생성
  - [ ] API endpoints 추가

#### Phase 4: TODO Management (Day 5)
- [ ] Task 6: 사용자 개입 메커니즘
  - [ ] StateManager.modify_step_by_user() 구현
  - [ ] StateManager.add_step_by_user() 구현
  - [ ] StateManager.remove_step_by_user() 구현
  - [ ] StateManager.calculate_overall_progress() 구현

- [ ] Task 7: TODO API 구현
  - [ ] api/todo_api.py 생성
  - [ ] GET /todos/{session_id}
  - [ ] GET /todos/{session_id}/progress
  - [ ] POST /todos/{session_id}/modify
  - [ ] POST /todos/{session_id}/add
  - [ ] DELETE /todos/{session_id}/{step_id}

- [ ] Task 8: Checkpoint 통합 강화
  - [ ] CheckpointerManager.get_state() 구현
  - [ ] CheckpointerManager.save_state() 구현
  - [ ] CheckpointerManager.list_checkpoints() 구현

- [ ] Task 9: Frontend TODO UI
  - [ ] TodoList.tsx 생성
  - [ ] 실시간 업데이트 구현
  - [ ] Progress bar 구현

---

**Document End**

**Next Action**: Task 1 (sessions.user_id 타입 수정) 시작
