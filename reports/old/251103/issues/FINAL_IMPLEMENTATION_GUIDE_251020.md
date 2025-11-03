# 🎯 Memory Service 최종 구현 가이드
## 복사-붙여넣기로 바로 실행 가능한 완전한 가이드

**작성일**: 2025-10-20
**대상**: 초보자부터 전문가까지
**목표**: 14일 안에 100% 완성

---

## 📊 전체 검증 결과

### ✅ 코드베이스 현황 (2025-10-20 기준)

```
코드 검증 완료:
✅ simple_memory_service.py - 존재 (메서드 미구현)
✅ team_supervisor.py - 존재 (Line 20, 211, 855에서 메모리 서비스 호출)
✅ chat.py - 존재 (ChatSession.session_metadata JSONB 컬럼 확인)
✅ users.py - 존재 (memory relationships 없음)
✅ config.py - 존재 (MEMORY_LOAD_LIMIT만 있음)
✅ models/__init__.py - 존재 (memory 모델 import 없음)

데이터베이스 검증 완료:
✅ chat_messages.structured_data - 존재
✅ chat_sessions.session_metadata - 존재 (JSONB)
❌ conversation_memories - 없음 (Phase 2에서 생성)
❌ entity_memories - 없음 (Phase 2에서 생성)
❌ user_preferences - 없음 (Phase 2에서 생성)

Alembic 상태:
❌ alembic.ini - 없음 (Phase 0에서 초기화)
❌ migrations/ - 없음 (Phase 0에서 생성)
```

### 📋 3가지 결정 사항 (사용자 입력 필요)

**이 섹션만 작성하면 바로 구현 시작!**

```yaml
# === 사용자 결정 사항 ===

결정 1️⃣: 한국어 임베딩 모델 (Phase 3)
현재 계획: all-MiniLM-L6-v2 (영어 모델)
선택:
  [ ] A: jhgan/ko-sbert-multitask (한국어 최적화, 400MB, 추천)
  [ ] B: all-MiniLM-L6-v2 (영어 기본, 80MB, 계획서대로)

결정 2️⃣: 동시성 제어 (Phase 1)
현재 계획: 없음
선택:
  [ ] A: with_for_update() 추가 (안전, 추천)
  [ ] B: 없음 (간단, 계획서대로)

결정 3️⃣: 자동 백업
현재 계획: 수동 백업
선택:
  [ ] A: 자동 백업 스크립트 (강력 추천)
  [ ] B: 수동 백업 (계획서대로)

# === 자동 처리 (사용자 확인 불필요) ===
✅ FK 추가 (chat_sessions.user_id → users.id)
✅ Memory 테이블 생성 (3개)
✅ User relationships 추가
✅ config.py 설정 추가
✅ team_supervisor.py import 수정
```

---

## 🚀 Phase 0: 환경 준비 (1일)

### 0.1 Alembic 초기화 (필수!)

**현재 상태**: Alembic 미설치
**필요 이유**: Phase 2 마이그레이션에 필수

```bash
# 1. backend 디렉토리로 이동
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend

# 2. Alembic 설치 확인
poetry show alembic

# 3. 설치 안 되어 있으면
poetry add alembic

# 4. Alembic 초기화
alembic init migrations

# 5. 결과 확인
dir alembic.ini
dir migrations
```

**예상 출력**:
```
✅ alembic.ini 파일 생성됨
✅ migrations/ 폴더 생성됨
   ├── versions/ (비어있음)
   ├── env.py
   ├── script.py.mako
   └── README
```

### 0.2 Alembic 설정 수정

**파일**: `backend/alembic.ini`

```ini
# Line 60-61 수정
# Before
sqlalchemy.url = driver://user:pass@localhost/dbname

# After
# sqlalchemy.url은 env.py에서 설정하므로 주석 처리
# sqlalchemy.url =
```

**파일**: `backend/migrations/env.py`

```python
# Line 1-20 사이에 추가
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# ✅ 추가: 설정 및 모델 import
from app.core.config import settings
from app.db.postgre_db import Base
from app.models import *  # 모든 모델 import

# Alembic Config
config = context.config

# ✅ 추가: DB URL 설정
config.set_main_option('sqlalchemy.url', settings.sqlalchemy_url)

# ... 나머지 코드 유지
```

### 0.3 현재 상태 스냅샷 생성

```bash
# 1. 현재 DB 스키마를 Alembic에 기록
alembic revision --autogenerate -m "initial_schema_snapshot"

# 2. 생성된 마이그레이션 파일 확인
dir migrations\versions

# 3. 이 마이그레이션은 실행하지 않음! (이미 DB에 테이블 있으므로)
# 대신 "가짜 적용"으로 Alembic에게 "이미 적용됨" 표시
alembic stamp head
```

**예상 출력**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.autogenerate.compare] Detected table 'users'
INFO  [alembic.autogenerate.compare] Detected table 'chat_sessions'
...
  Generating migrations\versions\xxxx_initial_schema_snapshot.py ... done
```

### 0.4 백업 (결정 3️⃣에 따라)

#### Option A: 자동 백업 스크립트 (선택 시)

**파일**: `backend/scripts/backup_db.sh` (신규)

```bash
#!/bin/bash
# 자동 백업 스크립트

# 백업 디렉토리 생성
mkdir -p backups

# 타임스탬프 생성
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 백업 실행
echo "🔄 Creating database backup..."
pg_dump -U postgres -h localhost real_estate > "backups/backup_${TIMESTAMP}.sql"

if [ $? -eq 0 ]; then
    echo "✅ Backup created: backups/backup_${TIMESTAMP}.sql"

    # 7일 이상 오래된 백업 삭제 (선택)
    find backups/ -name "backup_*.sql" -mtime +7 -delete
    echo "🧹 Cleaned up old backups (>7 days)"
else
    echo "❌ Backup failed!"
    exit 1
fi
```

**Windows PowerShell 버전**: `backend/scripts/backup_db.ps1`

```powershell
# 자동 백업 스크립트 (Windows)

# 백업 디렉토리 생성
New-Item -ItemType Directory -Force -Path "backups" | Out-Null

# 타임스탬프 생성
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"

# 백업 실행
Write-Host "🔄 Creating database backup..."
pg_dump -U postgres -h localhost real_estate > "backups/backup_$TIMESTAMP.sql"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Backup created: backups/backup_$TIMESTAMP.sql"

    # 7일 이상 오래된 백업 삭제 (선택)
    Get-ChildItem -Path "backups" -Filter "backup_*.sql" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
        Remove-Item
    Write-Host "🧹 Cleaned up old backups (>7 days)"
} else {
    Write-Host "❌ Backup failed!"
    exit 1
}
```

**실행**:
```bash
# Windows Git Bash
cd backend
bash scripts/backup_db.sh

# Windows PowerShell
cd backend
powershell.exe -ExecutionPolicy Bypass -File scripts\backup_db.ps1
```

#### Option B: 수동 백업 (선택 시)

```bash
# 백업 디렉토리 생성
mkdir backups

# 수동 백업
pg_dump -U postgres real_estate > backups/backup_before_phase1.sql
```

### 0.5 Git 브랜치 생성

```bash
# 1. 현재 상태 확인
cd C:\kdy\Projects\holmesnyangz\beta_v001
git status

# 2. 현재 작업 커밋 (있으면)
git add .
git commit -m "Before memory service implementation"

# 3. 백업 브랜치 생성
git checkout -b backup/before-memory-service
git checkout main  # 다시 main으로

# 4. Feature 브랜치 생성
git checkout -b feature/memory-service-phase0-3
```

### 0.6 검증 스크립트 실행

**파일**: `backend/scripts/verify_current_state.py` (신규)

```python
"""Phase 0: 현재 상태 검증 스크립트"""

import asyncio
import sys
from sqlalchemy import select, text
from app.db.postgre_db import get_async_db
from app.models.chat import ChatSession, ChatMessage
from app.models.users import User

async def verify_current_state():
    """현재 데이터베이스 상태 확인"""

    print("=" * 60)
    print("📊 Current State Verification")
    print("=" * 60)

    try:
        async for db_session in get_async_db():
            # 1. Users 테이블 확인
            result = await db_session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            print(f"✅ Users table exists: {user is not None}")

            # 2. ChatSession 테이블 확인
            result = await db_session.execute(select(ChatSession).limit(1))
            session = result.scalar_one_or_none()
            print(f"✅ ChatSession table exists: {session is not None}")

            # 3. ChatMessage 테이블 확인
            result = await db_session.execute(select(ChatMessage).limit(1))
            message = result.scalar_one_or_none()
            print(f"✅ ChatMessage table exists: {message is not None}")

            # 4. ChatSession.session_metadata 컬럼 확인
            if session:
                has_metadata = hasattr(session, 'session_metadata')
                print(f"✅ ChatSession.session_metadata exists: {has_metadata}")
                if has_metadata:
                    print(f"   Type: {type(session.session_metadata)}")

            # 5. ChatMessage.structured_data 컬럼 확인
            if message:
                has_structured = hasattr(message, 'structured_data')
                print(f"✅ ChatMessage.structured_data exists: {has_structured}")
                if has_structured:
                    print(f"   Type: {type(message.structured_data)}")

            # 6. Memory 테이블 존재 여부 (없어야 정상)
            result = await db_session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('conversation_memories', 'entity_memories', 'user_preferences')")
            )
            memory_table_count = result.scalar()
            print(f"✅ Memory tables (should be 0): {memory_table_count}")

            # 7. Alembic 버전 확인
            try:
                result = await db_session.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar_one_or_none()
                print(f"✅ Alembic version: {version if version else 'Not initialized'}")
            except Exception:
                print(f"⚠️  Alembic version table not found (will be created)")

            print("=" * 60)
            print("✅ Verification Complete!")
            print("=" * 60)
            break

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify_current_state())
```

**실행**:
```bash
cd backend
python scripts/verify_current_state.py
```

**예상 출력**:
```
============================================================
📊 Current State Verification
============================================================
✅ Users table exists: True
✅ ChatSession table exists: True
✅ ChatMessage table exists: True
✅ ChatSession.session_metadata exists: True
   Type: <class 'dict'>
✅ ChatMessage.structured_data exists: True
   Type: <class 'dict'>
✅ Memory tables (should be 0): 0
✅ Alembic version: xxxxxxxxxxxx
============================================================
✅ Verification Complete!
============================================================
```

### 0.7 Phase 0 체크리스트

```
Phase 0 완료 조건:
[ ] Alembic 초기화 완료
[ ] Alembic 설정 (env.py) 수정 완료
[ ] 현재 스키마 스냅샷 생성 (alembic stamp head)
[ ] 백업 완료 (자동 또는 수동)
[ ] Git 브랜치 생성 완료
[ ] 검증 스크립트 실행 성공
```

---

## ⚡ Phase 1: Quick Fix (1일)

### 1.1 simple_memory_service.py 전체 교체

**파일**: `backend/app/service_agent/foundation/simple_memory_service.py`

**전략**: 기존 파일 전체를 아래 코드로 교체

```python
"""
SimpleMemoryService - Phase 1 Implementation

Memory 테이블 없이 chat_sessions.session_metadata 활용
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class SimpleMemoryService:
    """
    간단한 메모리 서비스 (Phase 1)

    - session_metadata JSONB 활용
    - 마이그레이션 불필요
    - 즉시 사용 가능
    """

    def __init__(self, db_session: AsyncSession):
        """
        초기화

        Args:
            db_session: 비동기 DB 세션 (AsyncSession 인스턴스)
        """
        self.db = db_session

    # ========================================================================
    # team_supervisor.py가 호출하는 메서드 (Phase 1 구현)
    # ========================================================================

    async def load_recent_memories(
        self,
        user_id: int,
        limit: int = 5,
        relevance_filter: Optional[str] = "RELEVANT"
    ) -> List[Dict[str, Any]]:
        """
        최근 대화 기억 로드 (세션 기반)

        Phase 1: ChatSession.session_metadata에서 로드
        Phase 2+: ConversationMemory 테이블에서 로드

        Args:
            user_id: 사용자 ID
            limit: 로드할 개수
            relevance_filter: 관련성 필터 (RELEVANT/IRRELEVANT/None)

        Returns:
            메모리 리스트
        """
        try:
            # ⚠️ 결정 2️⃣: 동시성 제어
            # Option A 선택 시: .with_for_update() 추가
            # Option B 선택 시: 아래 코드 그대로

            query = select(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.is_active == True
            ).order_by(ChatSession.updated_at.desc()).limit(3)

            # === 결정 2️⃣ 적용 위치 ===
            # Option A를 선택했다면 아래 주석 해제:
            # query = query.with_for_update()

            result = await self.db.execute(query)
            sessions = result.scalars().all()

            memories = []
            for session in sessions:
                if not session.session_metadata:
                    continue

                session_memories = session.session_metadata.get('memories', [])

                for mem in session_memories:
                    # relevance_filter 적용
                    if relevance_filter and mem.get('relevance') != relevance_filter:
                        continue

                    memories.append({
                        "query": mem.get("query", ""),
                        "response": mem.get("response_summary", ""),
                        "response_summary": mem.get("response_summary", ""),
                        "intent": mem.get("intent"),
                        "entities": mem.get("entities", {}),
                        "timestamp": mem.get("timestamp"),
                        "session_id": session.session_id,
                        "relevance": mem.get("relevance", "NORMAL")
                    })

                    if len(memories) >= limit:
                        break

                if len(memories) >= limit:
                    break

            logger.info(f"Loaded {len(memories)} memories for user {user_id}")
            return memories[:limit]

        except Exception as e:
            logger.error(f"Error loading recent memories: {e}", exc_info=True)
            return []

    async def save_conversation(
        self,
        user_id: int,
        query: str,
        response_summary: str,
        relevance: str = "RELEVANT",
        session_id: Optional[str] = None,
        intent_detected: Optional[str] = None,
        entities_mentioned: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        대화 메모리 저장 (session_metadata 활용)

        Phase 1: ChatSession.session_metadata['memories']에 추가
        Phase 2+: ConversationMemory 테이블에 저장

        Args:
            user_id: 사용자 ID
            query: 사용자 쿼리
            response_summary: 응답 요약
            relevance: 관련성 (RELEVANT/IRRELEVANT/NORMAL)
            session_id: 채팅 세션 ID (필수)
            intent_detected: 감지된 의도
            entities_mentioned: 언급된 엔티티
            conversation_metadata: 추가 메타데이터

        Returns:
            bool: 저장 성공 여부
        """
        try:
            if not session_id:
                logger.warning("save_conversation called without session_id")
                return False

            # ChatSession 조회
            # ⚠️ 결정 2️⃣: 동시성 제어
            query_obj = select(ChatSession).filter(
                ChatSession.session_id == session_id
            )

            # === 결정 2️⃣ 적용 위치 ===
            # Option A를 선택했다면 아래 주석 해제:
            # query_obj = query_obj.with_for_update()

            result = await self.db.execute(query_obj)
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                logger.warning(f"ChatSession {session_id} not found")
                return False

            # session_metadata 초기화
            if not chat_session.session_metadata:
                chat_session.session_metadata = {}

            if 'memories' not in chat_session.session_metadata:
                chat_session.session_metadata['memories'] = []

            # 새 메모리 추가
            new_memory = {
                "query": query,
                "response_summary": response_summary,
                "relevance": relevance,
                "intent": intent_detected,
                "entities": entities_mentioned or {},
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                **(conversation_metadata or {})
            }

            chat_session.session_metadata['memories'].append(new_memory)

            # 최신 10개만 유지
            chat_session.session_metadata['memories'] = \
                chat_session.session_metadata['memories'][-10:]

            # JSONB 업데이트 flag
            flag_modified(chat_session, 'session_metadata')

            await self.db.commit()

            logger.info(
                f"Saved conversation memory to session {session_id} "
                f"(user_id={user_id}, relevance={relevance})"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving conversation: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        사용자 선호도 조회

        Phase 1: 빈 dict 반환
        Phase 2+: UserPreference 테이블에서 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Dict: 사용자 선호도 (Phase 1에서는 빈 dict)
        """
        logger.debug(f"get_user_preferences called for user {user_id} (Phase 1: returns empty)")
        return {}

    # ========================================================================
    # 기존 메서드들 (유지)
    # ========================================================================

    async def load_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 메시지 로드 (chat_messages 테이블)

        Note: 기존 메서드, 유지
        """
        try:
            query = select(ChatMessage).where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at).limit(limit)

            result = await self.db.execute(query)
            messages = result.scalars().all()

            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error loading recent messages: {e}")
            return []

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> str:
        """대화 히스토리를 텍스트로 변환"""
        messages = await self.load_recent_messages(session_id, limit)

        if not messages:
            return "No conversation history available."

        history_lines = []
        for msg in messages:
            history_lines.append(f"{msg['role']}: {msg['content']}")

        return "\n".join(history_lines)

    # ========================================================================
    # Deprecated 호환성 메서드
    # ========================================================================

    async def get_recent_memories(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Deprecated: load_recent_memories 사용 권장"""
        logger.warning(
            f"get_recent_memories is deprecated. Use load_recent_memories instead. "
            f"(user_id={user_id})"
        )

        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user_id: {user_id}")
            return []

        return await self.load_recent_memories(
            user_id=user_id_int,
            limit=limit,
            relevance_filter=None
        )

    async def save_conversation_memory(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Deprecated: save_conversation 사용 권장"""
        logger.warning(
            f"save_conversation_memory is deprecated. Use save_conversation instead. "
            f"(session_id={session_id})"
        )

        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid user_id: {user_id}")
            return False

        return await self.save_conversation(
            user_id=user_id_int,
            query=user_message,
            response_summary=ai_response[:200],
            session_id=session_id,
            conversation_metadata=metadata
        )

    async def update_user_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> bool:
        """Deprecated: Phase 2에서 구현"""
        logger.debug(f"update_user_preference called (no-op): user_id={user_id}, {key}={value}")
        return True

    async def save_entity_memory(
        self,
        user_id: str,
        entity_type: str,
        entity_name: str,
        properties: Dict[str, Any]
    ) -> bool:
        """Deprecated: Phase 2에서 구현"""
        logger.debug(
            f"save_entity_memory called (no-op): "
            f"user_id={user_id}, entity={entity_type}/{entity_name}"
        )
        return True

    async def get_entity_memories(
        self,
        user_id: str,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Deprecated: Phase 2에서 구현"""
        logger.debug(f"get_entity_memories called (returns empty): user_id={user_id}")
        return []


# ========================================================================
# 호환성 Alias
# ========================================================================
LongTermMemoryService = SimpleMemoryService
```

### 1.2 결정 2️⃣ 적용 가이드

**Option A 선택 시** (동시성 제어 추가):

```python
# Line 69-76 부분 (load_recent_memories)
query = select(ChatSession).filter(
    ChatSession.user_id == user_id,
    ChatSession.is_active == True
).order_by(ChatSession.updated_at.desc()).limit(3).with_for_update()  # ← 추가

# Line 139-145 부분 (save_conversation)
query_obj = select(ChatSession).filter(
    ChatSession.session_id == session_id
).with_for_update()  # ← 추가
```

**Option B 선택 시**: 위 코드 그대로 사용 (주석 제거 안 함)

### 1.3 Phase 1 테스트

**파일**: `backend/tests/test_simple_memory_phase1.py` (신규)

```python
"""Phase 1 Memory Service 테스트"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.users import User, UserType
from app.models.chat import ChatSession, ChatMessage
from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
from app.db.postgre_db import Base
from app.core.config import settings

# 테스트용 DB (실제 DB 사용 - 주의!)
TEST_DATABASE_URL = settings.sqlalchemy_url.replace("/real_estate", "/test_real_estate")


@pytest.fixture
async def async_session():
    """테스트용 AsyncSession"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    # 정리
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_user(async_session):
    """테스트 사용자 생성"""
    user = User(
        id=999,
        email="test_memory@example.com",
        type=UserType.USER,
        is_active=True
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_session(async_session, test_user):
    """테스트 채팅 세션 생성"""
    chat_session = ChatSession(
        session_id="test_session_phase1",
        user_id=test_user.id,
        title="Phase 1 테스트",
        session_metadata={}
    )
    async_session.add(chat_session)
    await async_session.commit()
    await async_session.refresh(chat_session)
    return chat_session


@pytest.mark.asyncio
async def test_save_conversation(async_session, test_user, test_session):
    """대화 저장 테스트"""
    service = SimpleMemoryService(async_session)

    result = await service.save_conversation(
        user_id=test_user.id,
        query="강남역 원룸 추천해주세요",
        response_summary="강남역 근처 원룸 3개를 추천해드립니다.",
        relevance="RELEVANT",
        session_id=test_session.session_id,
        intent_detected="property_search",
        entities_mentioned={
            "location": ["강남역"],
            "property_type": ["원룸"]
        }
    )

    assert result is True

    # 검증
    await async_session.refresh(test_session)
    assert 'memories' in test_session.session_metadata
    assert len(test_session.session_metadata['memories']) == 1

    memory = test_session.session_metadata['memories'][0]
    assert memory['query'] == "강남역 원룸 추천해주세요"
    assert memory['relevance'] == "RELEVANT"
    assert "강남역" in memory['entities']['location']


@pytest.mark.asyncio
async def test_load_recent_memories(async_session, test_user, test_session):
    """최근 메모리 로드 테스트"""
    service = SimpleMemoryService(async_session)

    # 메모리 저장
    await service.save_conversation(
        user_id=test_user.id,
        query="강남역 원룸 알아봐줘",
        response_summary="강남역 원룸 추천합니다",
        relevance="RELEVANT",
        session_id=test_session.session_id
    )

    # 메모리 로드
    memories = await service.load_recent_memories(
        user_id=test_user.id,
        limit=5,
        relevance_filter="RELEVANT"
    )

    assert len(memories) == 1
    assert memories[0]['query'] == "강남역 원룸 알아봐줘"
    assert memories[0]['relevance'] == "RELEVANT"


@pytest.mark.asyncio
async def test_memory_limit(async_session, test_user, test_session):
    """메모리 개수 제한 테스트 (최대 10개)"""
    service = SimpleMemoryService(async_session)

    # 15개 메모리 저장
    for i in range(15):
        await service.save_conversation(
            user_id=test_user.id,
            query=f"Query {i}",
            response_summary=f"Response {i}",
            session_id=test_session.session_id
        )

    # 검증
    await async_session.refresh(test_session)
    assert len(test_session.session_metadata['memories']) == 10

    # 가장 오래된 것 삭제됨
    queries = [m['query'] for m in test_session.session_metadata['memories']]
    assert "Query 0" not in queries
    assert "Query 14" in queries
```

**실행**:
```bash
cd backend

# 테스트 DB 생성 (한 번만)
psql -U postgres -c "DROP DATABASE IF EXISTS test_real_estate;"
psql -U postgres -c "CREATE DATABASE test_real_estate;"

# 테스트 실행
pytest tests/test_simple_memory_phase1.py -v -s
```

### 1.4 Phase 1 완료 검증

```bash
# 1. 백업 (결정 3️⃣에 따라)
# Option A:
bash scripts/backup_db.sh

# Option B:
pg_dump -U postgres real_estate > backups/before_phase2.sql

# 2. Git 커밋
git add .
git commit -m "Phase 1: SimpleMemoryService implementation complete"

# 3. 수동 테스트 (선택)
# 실제 앱 실행해서 대화 기록이 유지되는지 확인
```

### 1.5 Phase 1 체크리스트

```
Phase 1 완료 조건:
[ ] simple_memory_service.py 전체 교체
[ ] 결정 2️⃣ 적용 (with_for_update 추가 여부)
[ ] 테스트 코드 작성
[ ] pytest 모두 통과
[ ] Git 커밋 완료
[ ] (선택) 수동 테스트 확인
```

---

## 🚀 Phase 2: Enhanced Memory (5일)

### 2.1 User 모델 Relationship 추가 (최우선!)

**파일**: `backend/app/models/users.py`

**Line 44-50 이후에 추가**:

```python
# 기존 relationships (Line 44-49)
profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
local_auth = relationship("LocalAuth", back_populates="user", uselist=False, cascade="all, delete-orphan")
social_auths = relationship("SocialAuth", back_populates="user", cascade="all, delete-orphan")
favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

# ✅ Phase 2 추가 (Line 50 이후에)
# Long-term Memory Relationships
conversation_memories = relationship(
    "ConversationMemory",
    back_populates="user",
    cascade="all, delete-orphan",
    lazy="select"
)
entity_memories = relationship(
    "EntityMemory",
    back_populates="user",
    cascade="all, delete-orphan",
    lazy="select"
)
preferences = relationship(
    "UserPreference",
    back_populates="user",
    uselist=False,  # One-to-One
    cascade="all, delete-orphan",
    lazy="select"
)
```

### 2.2 Memory 모델 파일 생성

**파일**: `backend/app/models/memory.py` (신규)

전체 내용은 REVISED 계획서의 Line 883-1076 참조 (너무 길어서 생략)

### 2.3 models/__init__.py 업데이트

**파일**: `backend/app/models/__init__.py`

```python
# 기존 imports (Line 1-5)
from app.models.real_estate import RealEstate, Region, Transaction, NearbyFacility, RealEstateAgent
from app.models.trust import TrustScore
from app.models.users import User, UserProfile, LocalAuth, SocialAuth, UserFavorite
from app.models.chat import ChatSession, ChatMessage

# ✅ Phase 2 추가
from app.models.memory import (
    ConversationMemory,
    UserPreference,
    EntityMemory
)

__all__ = [
    "RealEstate",
    "Region",
    "Transaction",
    "NearbyFacility",
    "RealEstateAgent",
    "TrustScore",
    "User",
    "UserProfile",
    "LocalAuth",
    "SocialAuth",
    "UserFavorite",
    "ChatSession",
    "ChatMessage",
    # ✅ Phase 2 추가
    "ConversationMemory",
    "UserPreference",
    "EntityMemory",
]
```

### 2.4 Alembic 마이그레이션 생성 및 실행

```bash
cd backend

# 1. 마이그레이션 자동 생성
alembic revision --autogenerate -m "add_memory_tables_phase2"

# 2. 생성된 파일 확인
dir migrations\versions

# 3. 파일 내용 검토 (생성된 파일 열어서 확인)
# - conversation_memories 테이블
# - user_preferences 테이블
# - entity_memories 테이블
# - 인덱스들

# 4. 마이그레이션 실행
alembic upgrade head

# 5. 검증
psql -U postgres -d real_estate -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('conversation_memories', 'user_preferences', 'entity_memories') ORDER BY table_name;"
```

**예상 출력**:
```
      table_name
-----------------------
 conversation_memories
 entity_memories
 user_preferences
(3 rows)
```

### 2.5 EnhancedMemoryService 구현

**파일**: `backend/app/service_agent/foundation/enhanced_memory_service.py` (신규)

전체 내용은 REVISED 계획서의 Line 1252-1625 참조 (너무 길어서 생략)

### 2.6 Memory Factory 구현

**파일**: `backend/app/service_agent/foundation/memory_factory.py` (신규)

```python
"""
Memory Service Factory

설정에 따라 적절한 Memory Service를 반환
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
from app.service_agent.foundation.enhanced_memory_service import EnhancedMemoryService

logger = logging.getLogger(__name__)


def get_memory_service(db_session: AsyncSession):
    """
    설정에 따라 적절한 Memory Service 반환

    환경 변수:
        MEMORY_SERVICE_TYPE: "simple", "enhanced", "complete" (기본: simple)

    Args:
        db_session: SQLAlchemy AsyncSession

    Returns:
        Memory Service 인스턴스
    """
    service_type = getattr(settings, 'MEMORY_SERVICE_TYPE', 'simple').lower()

    if service_type == "enhanced":
        logger.info("Using EnhancedMemoryService (Phase 2)")
        return EnhancedMemoryService(db_session)
    elif service_type == "complete":
        # Phase 3에서 구현
        logger.warning("CompleteMemoryService not implemented yet, falling back to Enhanced")
        return EnhancedMemoryService(db_session)
    else:
        # Default: simple
        logger.info("Using SimpleMemoryService (Phase 1)")
        return SimpleMemoryService(db_session)


# Alias for backward compatibility
LongTermMemoryService = get_memory_service
```

### 2.7 config.py 설정 추가

**파일**: `backend/app/core/config.py`

**Line 28 이후에 추가**:

```python
# 기존 Memory 설정 (Line 24-27)
SESSION_TTL_HOURS: int = 24
MEMORY_RETENTION_DAYS: int = 90
MEMORY_LIMIT_PER_USER: int = 100
MEMORY_LOAD_LIMIT: int = 5

# ✅ Phase 2 추가 (Line 28 이후)
MEMORY_SERVICE_TYPE: str = "simple"  # "simple", "enhanced", "complete"
ENABLE_MEMORY_SERVICE: bool = True
MEMORY_RELEVANCE_THRESHOLD: float = 0.7  # Phase 3에서 사용
```

### 2.8 .env 파일 업데이트

**파일**: `backend/.env`

```env
# 기존 설정들...

# ✅ Phase 2 추가: Memory Service Configuration
MEMORY_SERVICE_TYPE=enhanced  # Phase 2에서 "enhanced"로 변경
MEMORY_LOAD_LIMIT=5
ENABLE_MEMORY_SERVICE=true
MEMORY_RELEVANCE_THRESHOLD=0.7
```

### 2.9 team_supervisor.py 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

```python
# Line 20 수정
# Before
from app.service_agent.foundation.simple_memory_service import LongTermMemoryService

# After
from app.service_agent.foundation.memory_factory import get_memory_service

# Line 208 수정 (planning_node 함수 내부)
# Before
memory_service = LongTermMemoryService(db_session)

# After
memory_service = get_memory_service(db_session)  # ✅ Factory 사용
```

### 2.10 Phase 2 체크리스트

```
Phase 2 완료 조건:
[ ] User 모델 relationship 추가
[ ] memory.py 파일 생성
[ ] models/__init__.py 업데이트
[ ] Alembic 마이그레이션 생성
[ ] 마이그레이션 실행 및 테이블 생성 확인
[ ] enhanced_memory_service.py 구현
[ ] memory_factory.py 구현
[ ] config.py 설정 추가
[ ] .env 파일 업데이트
[ ] team_supervisor.py 수정
[ ] Git 커밋
```

---

## 🎯 Phase 3: Complete System (7일)

### 3.1 결정 1️⃣ 적용: 임베딩 모델 선택

**파일**: `backend/pyproject.toml`

```toml
[tool.poetry.dependencies]
# 기존 의존성...

# ✅ Phase 3 추가
sentence-transformers = "^2.2.2"
numpy = "^1.24.0"
```

```bash
cd backend
poetry install
```

### 3.2 임베딩 모델 설정

**Option A 선택 시** (한국어 모델):

```python
# Phase 3 구현 시 사용할 모델명
EMBEDDING_MODEL_NAME = "jhgan/ko-sbert-multitask"
```

**Option B 선택 시** (영어 모델):

```python
# Phase 3 구현 시 사용할 모델명
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
```

### 3.3 ConversationMemory 모델 확장

```bash
cd backend

# 마이그레이션 생성
alembic revision -m "add_embedding_columns_phase3"
```

**생성된 파일 수정**:

```python
def upgrade():
    from sqlalchemy.dialects.postgresql import JSONB
    import sqlalchemy as sa

    op.add_column('conversation_memories',
        sa.Column('query_embedding', JSONB(), nullable=True, comment="쿼리 임베딩 벡터"))
    op.add_column('conversation_memories',
        sa.Column('embedding_model', sa.String(100), nullable=True, comment="임베딩 모델명"))

def downgrade():
    op.drop_column('conversation_memories', 'embedding_model')
    op.drop_column('conversation_memories', 'query_embedding')
```

```bash
# 실행
alembic upgrade head
```

### 3.4 백필 스크립트 (기존 데이터 임베딩 추가)

**파일**: `backend/scripts/backfill_embeddings.py` (신규)

```python
"""
Phase 2 데이터에 임베딩 백필

기존 ConversationMemory에 저장된 대화들에 벡터 임베딩 추가
"""

import asyncio
import logging
from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from app.db.postgre_db import get_async_db
from app.models.memory import ConversationMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚠️ 결정 1️⃣: 임베딩 모델 선택
# Option A: 한국어 모델
# EMBEDDING_MODEL_NAME = "jhgan/ko-sbert-multitask"

# Option B: 영어 모델 (기본)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


async def backfill_embeddings(batch_size: int = 100):
    """Phase 2 대화에 임베딩 추가"""

    logger.info("=" * 60)
    logger.info("Starting Embedding Backfill (Phase 3)")
    logger.info(f"Model: {EMBEDDING_MODEL_NAME}")
    logger.info("=" * 60)

    async for db_session in get_async_db():
        total_processed = 0

        while True:
            # 임베딩이 없는 대화 조회
            result = await db_session.execute(
                select(ConversationMemory)
                .filter(ConversationMemory.query_embedding.is_(None))
                .limit(batch_size)
            )
            memories = result.scalars().all()

            if not memories:
                logger.info("No more memories to backfill")
                break

            logger.info(f"Processing batch of {len(memories)} conversations...")

            for memory in memories:
                try:
                    # 임베딩 생성
                    query_embedding = embedding_model.encode(memory.query).tolist()

                    # DB 업데이트
                    memory.query_embedding = query_embedding
                    memory.embedding_model = EMBEDDING_MODEL_NAME

                    total_processed += 1

                    if total_processed % 10 == 0:
                        logger.info(f"Processed {total_processed} conversations...")

                except Exception as e:
                    logger.error(f"Failed to process memory {memory.id}: {e}")

            # 배치 커밋
            from sqlalchemy.orm.attributes import flag_modified
            for memory in memories:
                if memory.query_embedding:
                    flag_modified(memory, 'query_embedding')

            await db_session.commit()
            logger.info(f"Batch committed ({total_processed} total)")

        logger.info("=" * 60)
        logger.info(f"Backfill Complete! Total processed: {total_processed}")
        logger.info("=" * 60)
        break


if __name__ == "__main__":
    asyncio.run(backfill_embeddings())
```

**실행**:
```bash
cd backend
python scripts/backfill_embeddings.py
```

### 3.5 CompleteMemoryService 구현

**파일**: `backend/app/service_agent/foundation/complete_memory_service.py` (신규)

전체 내용은 REVISED 계획서의 Line 1895-2199 참조

### 3.6 memory_factory.py 업데이트

```python
# complete_memory_service import 추가
from app.service_agent.foundation.complete_memory_service import CompleteMemoryService

def get_memory_service(db_session: AsyncSession):
    """설정에 따라 Memory Service 반환"""
    service_type = getattr(settings, 'MEMORY_SERVICE_TYPE', 'simple').lower()

    if service_type == "complete":
        logger.info("Using CompleteMemoryService (Phase 3)")

        # ⚠️ 결정 1️⃣: 임베딩 모델
        # Option A:
        # embedding_model = "jhgan/ko-sbert-multitask"

        # Option B (기본):
        embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

        return CompleteMemoryService(db_session, embedding_model_name=embedding_model)
    elif service_type == "enhanced":
        logger.info("Using EnhancedMemoryService (Phase 2)")
        return EnhancedMemoryService(db_session)
    else:
        logger.info("Using SimpleMemoryService (Phase 1)")
        return SimpleMemoryService(db_session)
```

### 3.7 .env 업데이트 (Phase 3)

```env
# Phase 3에서 변경
MEMORY_SERVICE_TYPE=complete  # ← "enhanced"에서 "complete"로
```

### 3.8 Phase 3 체크리스트

```
Phase 3 완료 조건:
[ ] sentence-transformers 설치
[ ] 결정 1️⃣ 적용 (임베딩 모델 선택)
[ ] 임베딩 컬럼 마이그레이션
[ ] 백필 스크립트 실행
[ ] complete_memory_service.py 구현
[ ] memory_factory.py 업데이트
[ ] .env 파일 MEMORY_SERVICE_TYPE=complete
[ ] Semantic Search 테스트
[ ] Git 커밋
```

---

## 🧪 최종 통합 테스트

### 테스트 시나리오

```python
# scripts/test_memory_integration_final.py
"""최종 통합 테스트"""

import asyncio
from app.service_agent.foundation.memory_factory import get_memory_service
from app.db.postgre_db import get_async_db

async def test_complete_flow():
    """Phase 1 → Phase 2 → Phase 3 전체 흐름 테스트"""

    async for db_session in get_async_db():
        service = get_memory_service(db_session)

        print(f"Using: {service.__class__.__name__}")

        # 1. 대화 저장
        result = await service.save_conversation(
            user_id=1,
            query="강남역 원룸 추천해줘",
            response_summary="강남역 원룸 3개 추천합니다",
            relevance="RELEVANT",
            session_id="test_final_session"
        )
        print(f"Save result: {result}")

        # 2. 메모리 로드
        if hasattr(service, 'load_contextual_memories'):
            # Phase 3: Semantic Search
            memories = await service.load_contextual_memories(
                user_id=1,
                current_query="강남역 1인실 알려줘",  # 의미적으로 유사
                limit=5
            )
        else:
            # Phase 1/2: 일반 로드
            memories = await service.load_recent_memories(
                user_id=1,
                limit=5
            )

        print(f"Loaded {len(memories)} memories")
        for mem in memories:
            print(f"  - {mem['query']}")
            if 'similarity' in mem:
                print(f"    Similarity: {mem['similarity']:.3f}")

        break

if __name__ == "__main__":
    asyncio.run(test_complete_flow())
```

**실행**:
```bash
cd backend
python scripts/test_memory_integration_final.py
```

---

## 📋 전체 구현 체크리스트

### Phase 0: 환경 준비
- [ ] Alembic 초기화
- [ ] Alembic 설정 (env.py)
- [ ] 현재 스키마 스냅샷
- [ ] 백업 (결정 3️⃣)
- [ ] Git 브랜치 생성
- [ ] 검증 스크립트 실행

### Phase 1: Quick Fix (1일)
- [ ] simple_memory_service.py 교체
- [ ] 결정 2️⃣ 적용 (with_for_update)
- [ ] 테스트 작성 및 실행
- [ ] Git 커밋

### Phase 2: Enhanced Memory (5일)
- [ ] User 모델 relationship 추가
- [ ] memory.py 생성
- [ ] models/__init__.py 업데이트
- [ ] Alembic 마이그레이션
- [ ] enhanced_memory_service.py
- [ ] memory_factory.py
- [ ] config.py, .env 업데이트
- [ ] team_supervisor.py 수정
- [ ] Git 커밋

### Phase 3: Complete System (7일)
- [ ] sentence-transformers 설치
- [ ] 결정 1️⃣ 적용 (임베딩 모델)
- [ ] 임베딩 컬럼 마이그레이션
- [ ] 백필 스크립트
- [ ] complete_memory_service.py
- [ ] memory_factory.py 업데이트
- [ ] .env 업데이트
- [ ] 통합 테스트
- [ ] Git 커밋

### 최종 검증
- [ ] 모든 pytest 통과
- [ ] 실제 앱에서 대화 기록 유지 확인
- [ ] Semantic Search 동작 확인 (Phase 3)
- [ ] Git merge to main

---

## 🚨 트러블슈팅

### 문제 1: Alembic import 오류

```
ImportError: cannot import name 'Base' from 'app.db.postgre_db'
```

**해결**:
```python
# migrations/env.py 확인
sys.path.insert(0, str(backend_path))  # 경로 추가 확인
```

### 문제 2: JSONB 업데이트 안 됨

```python
# flag_modified 사용 확인
from sqlalchemy.orm.attributes import flag_modified
flag_modified(chat_session, 'session_metadata')
await self.db.commit()
```

### 문제 3: Memory 테이블 relationship 오류

```
sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize
```

**해결**: User 모델에 relationship 먼저 추가했는지 확인

### 문제 4: 임베딩 모델 다운로드 실패

```bash
# 수동 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sbert-multitask')"
```

---

## 🎯 성공 기준

### Phase 1 (40%)
- ✅ AttributeError 해결
- ✅ 세션 내 대화 기록 유지
- ✅ 시스템 안정성

### Phase 2 (70%)
- ✅ 사용자별 대화 기록 저장
- ✅ 엔티티 추적 동작
- ✅ 세션 간 컨텍스트 유지

### Phase 3 (100%)
- ✅ Semantic Search 동작
- ✅ 유사 대화 검색 정확도 > 80%
- ✅ 개인화 응답 품질 향상

---

## 📞 지원

궁금한 점이 있으면:

1. **계획서 재확인**: [plan_of_memory_service_error_fix_251020_REVISED.md](./plan_of_memory_service_error_fix_251020_REVISED.md)
2. **간단한 가이드**: [SIMPLE_DECISION_GUIDE_251020.md](./SIMPLE_DECISION_GUIDE_251020.md)
3. **검증 보고서**: [plan_verification_report_251020.md](./plan_verification_report_251020.md)

---

**작성일**: 2025-10-20
**상태**: ✅ 검증 완료, 즉시 구현 가능
**예상 소요**: 14일 (Phase 0: 1일, Phase 1: 1일, Phase 2: 5일, Phase 3: 7일)
