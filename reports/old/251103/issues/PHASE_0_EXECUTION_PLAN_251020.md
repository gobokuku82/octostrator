# Phase 0: 기준점 수립 - 단계별 검증 실행 계획

**작성일**: 2025-10-20
**원칙**: 작은 단계 + 매 단계 검증 + 사용자 확인
**목표**: DB 스키마를 단일 진실 공급원으로 확립

---

## 📋 전체 개요

```
Phase 0.1: DB 스키마 추출 (15분)
    ↓ 검증 & 확인
Phase 0.2: Models 검증 (20분)
    ↓ 검증 & 확인
Phase 0.3: 좀비 코드 탐지 (15분)
    ↓ 검증 & 확인
Phase 0.4: 불일치 항목 정리 (20분)
    ↓ 최종 검증
Phase 0 완료 → 사용자 승인 → Phase 1 시작
```

---

## 🎯 Phase 0.1: DB 스키마 추출

### 목표
실제 Production DB의 정확한 스냅샷 추출 및 검증

### 작업 단계

#### Step 1: Memory 관련 핵심 테이블 스키마 추출

**실행 명령어**:
```bash
# 1. chat_sessions 테이블
psql -U postgres -d real_estate -c "\d+ chat_sessions" > reports/schema/chat_sessions_251020.txt

# 2. chat_messages 테이블
psql -U postgres -d real_estate -c "\d+ chat_messages" > reports/schema/chat_messages_251020.txt

# 3. users 테이블
psql -U postgres -d real_estate -c "\d+ users" > reports/schema/users_251020.txt
```

**예상 소요 시간**: 2분

**검증 방법**:
```bash
# 파일 생성 확인
ls -lh reports/schema/*.txt

# 내용 확인 (각 파일 첫 10줄)
head -n 10 reports/schema/chat_sessions_251020.txt
head -n 10 reports/schema/chat_messages_251020.txt
head -n 10 reports/schema/users_251020.txt
```

**예상 출력**:
```
reports/schema/chat_sessions_251020.txt (약 30줄)
reports/schema/chat_messages_251020.txt (약 25줄)
reports/schema/users_251020.txt (약 20줄)
```

**사용자 확인 사항**:
- [ ] 3개 파일 모두 생성됨
- [ ] 각 파일에 테이블 구조 포함됨
- [ ] session_metadata, structured_data 컬럼 확인됨

---

#### Step 2: 전체 테이블 목록 추출

**실행 명령어**:
```bash
psql -U postgres -d real_estate -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    (SELECT COUNT(*)
     FROM information_schema.columns
     WHERE table_schema = schemaname
     AND table_name = tablename) AS columns
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
" > reports/schema/all_tables_251020.txt
```

**예상 소요 시간**: 1분

**검증 방법**:
```bash
# 테이블 개수 확인
grep -c "public" reports/schema/all_tables_251020.txt
```

**예상 결과**: 17개 테이블

**사용자 확인 사항**:
- [ ] 파일 생성됨
- [ ] 17개 테이블 목록 확인
- [ ] users, chat_sessions, chat_messages 포함 확인

---

#### Step 3: Memory 관련 테이블 존재 여부 확인

**실행 명령어**:
```bash
psql -U postgres -d real_estate -c "
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_memories')
        THEN '✅ EXISTS'
        ELSE '❌ NOT EXISTS'
    END AS conversation_memories,
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entity_memories')
        THEN '✅ EXISTS'
        ELSE '❌ NOT EXISTS'
    END AS entity_memories,
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_preferences')
        THEN '✅ EXISTS'
        ELSE '❌ NOT EXISTS'
    END AS user_preferences;
" > reports/schema/memory_tables_check_251020.txt
```

**예상 소요 시간**: 1분

**예상 출력**:
```
 conversation_memories | entity_memories | user_preferences
-----------------------+-----------------+------------------
 ❌ NOT EXISTS         | ❌ NOT EXISTS   | ❌ NOT EXISTS
```

**사용자 확인 사항**:
- [ ] 모두 "NOT EXISTS" 확인
- [ ] Phase 2에서 생성할 테이블임을 확인

---

#### Step 4: JSONB 컬럼 상세 확인

**실행 명령어**:
```bash
psql -U postgres -d real_estate -c "
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND data_type = 'jsonb'
ORDER BY table_name, ordinal_position;
" > reports/schema/jsonb_columns_251020.txt
```

**예상 소요 시간**: 1분

**예상 결과**:
```
      table_name       |   column_name    | data_type | is_nullable | column_default
-----------------------+------------------+-----------+-------------+---------------
 chat_messages         | structured_data  | jsonb     | YES         | NULL
 chat_sessions         | metadata         | jsonb     | YES         | NULL
```

**사용자 확인 사항**:
- [ ] chat_sessions.metadata (= session_metadata in code)
- [ ] chat_messages.structured_data
- [ ] 둘 다 nullable = YES

---

#### Step 5: Foreign Key 관계 확인

**실행 명령어**:
```bash
psql -U postgres -d real_estate -c "
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM
    information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('chat_sessions', 'chat_messages', 'users')
ORDER BY tc.table_name;
" > reports/schema/foreign_keys_251020.txt
```

**예상 소요 시간**: 1분

**예상 결과** (사용자님 상황에 따라 다를 수 있음):
```
  table_name   | column_name | foreign_table_name | foreign_column_name
---------------+-------------+--------------------+--------------------
 chat_sessions | user_id     | users              | id
(또는 FK 없을 수도 있음)
```

**사용자 확인 사항**:
- [ ] chat_sessions.user_id → users.id FK 여부 확인
- [ ] 없으면 Phase 1에서 추가 예정

---

### Phase 0.1 검증 체크리스트

```
✅ 완료 조건:
[ ] reports/schema/ 폴더에 6개 파일 생성
    - chat_sessions_251020.txt
    - chat_messages_251020.txt
    - users_251020.txt
    - all_tables_251020.txt
    - memory_tables_check_251020.txt
    - jsonb_columns_251020.txt
    - foreign_keys_251020.txt

[ ] 핵심 확인 사항:
    - chat_sessions.metadata (JSONB) 존재
    - chat_messages.structured_data (JSONB) 존재
    - conversation_memories, entity_memories, user_preferences 없음
    - 총 17개 테이블 확인

[ ] 사용자 승인: Phase 0.2로 진행 OK
```

---

## 🎯 Phase 0.2: SQLAlchemy Models 검증

### 목표
Models 파일이 실제 DB 스키마와 100% 일치하는지 검증

### 작업 단계

#### Step 1: Models 검증 스크립트 작성

**파일**: `backend/scripts/validate_models_251020.py`

```python
"""
Phase 0.2: SQLAlchemy Models vs DB Schema 검증
"""

import asyncio
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.postgre_db import Base
from app.models import *  # 모든 모델 import

async def validate_models():
    """Models와 DB 스키마 일치 여부 검증"""

    print("=" * 70)
    print("Phase 0.2: SQLAlchemy Models Validation")
    print("=" * 70)

    # DB 연결
    engine = create_async_engine(settings.sqlalchemy_url, echo=False)

    async with engine.begin() as conn:
        # 1. DB 테이블 목록
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        db_tables = {row[0] for row in result}

        print(f"\n📊 DB에 존재하는 테이블 ({len(db_tables)}):")
        for table in sorted(db_tables):
            print(f"   - {table}")

        # 2. SQLAlchemy Models 테이블 목록
        inspector = inspect(engine.sync_engine)
        model_tables = set(Base.metadata.tables.keys())

        print(f"\n🐍 Models에 정의된 테이블 ({len(model_tables)}):")
        for table in sorted(model_tables):
            print(f"   - {table}")

        # 3. 차이점 검출
        only_in_db = db_tables - model_tables
        only_in_models = model_tables - db_tables
        common = db_tables & model_tables

        print(f"\n" + "=" * 70)

        if only_in_db:
            print(f"⚠️  DB에만 있는 테이블 ({len(only_in_db)}):")
            for table in sorted(only_in_db):
                print(f"   - {table}")

        if only_in_models:
            print(f"⚠️  Models에만 있는 테이블 ({len(only_in_models)}):")
            for table in sorted(only_in_models):
                print(f"   - {table}")

        print(f"\n✅ 공통 테이블 ({len(common)}):")
        for table in sorted(common):
            print(f"   - {table}")

        # 4. Memory 관련 테이블 확인
        print(f"\n" + "=" * 70)
        print("Memory Service 관련 테이블 확인:")

        memory_tables = ['conversation_memories', 'entity_memories', 'user_preferences']
        for table in memory_tables:
            in_db = "✅ 존재" if table in db_tables else "❌ 없음"
            in_models = "✅ 정의됨" if table in model_tables else "❌ 미정의"
            print(f"   {table:25} DB: {in_db:10} Models: {in_models}")

        # 5. 핵심 JSONB 컬럼 확인
        print(f"\n" + "=" * 70)
        print("JSONB 컬럼 확인 (Memory 사용 예정):")

        for table_name in ['chat_sessions', 'chat_messages']:
            if table_name not in common:
                continue

            result = await conn.execute(text(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                AND data_type = 'jsonb'
            """))
            jsonb_cols = list(result)

            if jsonb_cols:
                print(f"\n   {table_name}:")
                for col_name, col_type in jsonb_cols:
                    print(f"      - {col_name} ({col_type})")

        print(f"\n" + "=" * 70)

        # 결과 판정
        if only_in_db or only_in_models:
            print("⚠️  Models와 DB 사이에 불일치 발견!")
            print("   → 위 목록 확인 필요")
            return False
        else:
            print("✅ Models와 DB 완벽 일치!")
            return True

    await engine.dispose()

if __name__ == "__main__":
    try:
        result = asyncio.run(validate_models())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ 검증 실패: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
```

**예상 소요 시간**: 5분 (스크립트 작성)

---

#### Step 2: 검증 스크립트 실행

**실행 명령어**:
```bash
cd backend
python scripts/validate_models_251020.py | tee ../reports/validation/models_validation_251020.txt
```

**예상 소요 시간**: 2분

**예상 출력**:
```
======================================================================
Phase 0.2: SQLAlchemy Models Validation
======================================================================

📊 DB에 존재하는 테이블 (17):
   - chat_messages
   - chat_sessions
   - users
   ... (14개 더)

🐍 Models에 정의된 테이블 (17):
   - chat_messages
   - chat_sessions
   - users
   ... (14개 더)

======================================================================

✅ 공통 테이블 (17):
   - chat_messages
   - chat_sessions
   ... (15개 더)

======================================================================
Memory Service 관련 테이블 확인:
   conversation_memories     DB: ❌ 없음     Models: ❌ 미정의
   entity_memories           DB: ❌ 없음     Models: ❌ 미정의
   user_preferences          DB: ❌ 없음     Models: ❌ 미정의

======================================================================
JSONB 컬럼 확인 (Memory 사용 예정):

   chat_sessions:
      - metadata (jsonb)

   chat_messages:
      - structured_data (jsonb)

======================================================================
✅ Models와 DB 완벽 일치!
```

**사용자 확인 사항**:
- [ ] "완벽 일치" 메시지 확인
- [ ] memory 테이블들이 DB/Models 모두 없음 확인
- [ ] JSONB 컬럼 존재 확인

---

#### Step 3: chat.py 모델 상세 확인

**실행 명령어**:
```bash
# ChatSession 모델의 session_metadata 정의 확인
grep -A 5 "session_metadata" backend/app/models/chat.py
```

**예상 출력**:
```python
session_metadata = Column(
    "metadata",  # DB에서는 "metadata"
    JSONB,
    comment="추가 메타데이터"
)
```

**사용자 확인 사항**:
- [ ] Column 이름: DB에서 "metadata", Python에서 "session_metadata"
- [ ] 타입: JSONB
- [ ] Nullable (기본값)

---

### Phase 0.2 검증 체크리스트

```
✅ 완료 조건:
[ ] scripts/validate_models_251020.py 작성 완료
[ ] 검증 스크립트 실행 성공
[ ] reports/validation/models_validation_251020.txt 생성

[ ] 핵심 확인 사항:
    - Models와 DB 100% 일치
    - memory 관련 테이블 없음 (예상대로)
    - chat_sessions.metadata (JSONB) 확인
    - chat_messages.structured_data (JSONB) 확인

[ ] 사용자 승인: Phase 0.3으로 진행 OK
```

---

## 🎯 Phase 0.3: 좀비 코드 탐지

### 목표
사용되지 않는 파일, 디렉토리, 코드 탐지 및 목록화

### 작업 단계

#### Step 1: 좀비 디렉토리 탐지

**실행 명령어**:
```bash
# *old*, *backup*, *archive* 등 패턴 찾기
find backend -type d \( -name "*old*" -o -name "*backup*" -o -name "*archive*" -o -name "*deprecated*" \) > reports/zombie/zombie_directories_251020.txt

# 결과 확인
cat reports/zombie/zombie_directories_251020.txt
```

**예상 소요 시간**: 1분

**예상 결과**:
```
backend/app/models/old
backend/migrations_old
backend/scripts_old
```

**사용자 확인 사항**:
- [ ] 발견된 디렉토리 목록 확인
- [ ] 실제로 사용 안 하는지 확인

---

#### Step 2: 좀비 Import 탐지

**실행 명령어**:
```bash
# memory.py에서 import하는 코드 찾기 (memory.py는 아직 없음)
grep -rn "from app.models.memory import" backend/app --include="*.py" > reports/zombie/zombie_imports_251020.txt 2>&1

# 결과 확인
cat reports/zombie/zombie_imports_251020.txt
```

**예상 결과**: 비어있거나 오류

**사용자 확인 사항**:
- [ ] 존재하지 않는 모델을 import하는 코드 있는지 확인
- [ ] 있다면 좀비 코드

---

#### Step 3: 미구현 메서드 탐지

**실행 명령어**:
```bash
# NotImplementedError, TODO, FIXME 찾기
grep -rn "NotImplementedError\|TODO\|FIXME\|raise NotImplemented" backend/app/service_agent --include="*.py" > reports/zombie/incomplete_code_251020.txt

# 결과 확인 (처음 20줄만)
head -n 20 reports/zombie/incomplete_code_251020.txt
```

**예상 소요 시간**: 2분

**사용자 확인 사항**:
- [ ] 미완성 메서드 목록 확인
- [ ] simple_memory_service.py에 있는지 확인

---

#### Step 4: 좀비 메서드 상세 분석 (simple_memory_service.py)

**실행 명령어**:
```bash
# simple_memory_service.py에서 entity/preference 관련 메서드 찾기
grep -n "def.*entity\|def.*preference" backend/app/service_agent/foundation/simple_memory_service.py
```

**예상 출력**:
```
97:async def save_entity_memory(...):
120:async def get_entity_memories(...):
145:async def update_user_preference(...):
```

**분석**:
- `entity_memories` 테이블 없는데 메서드 있음 → 좀비
- `user_preferences` 테이블 없는데 메서드 있음 → 좀비

**사용자 확인 사항**:
- [ ] 좀비 메서드 목록 확인
- [ ] Phase 1에서 제거 또는 주석 처리 예정

---

### Phase 0.3 검증 체크리스트

```
✅ 완료 조건:
[ ] reports/zombie/ 폴더에 3개 파일 생성
    - zombie_directories_251020.txt
    - zombie_imports_251020.txt
    - incomplete_code_251020.txt

[ ] 핵심 확인 사항:
    - old/ 디렉토리 발견
    - 좀비 import 여부 확인
    - 좀비 메서드 (entity_*, preference_*) 확인

[ ] 사용자 승인: Phase 0.4로 진행 OK
```

---

## 🎯 Phase 0.4: 불일치 항목 정리

### 목표
코드 간 불일치 (session_id 누락 등) 완전 목록화

### 작업 단계

#### Step 1: session_id 파라미터 불일치 확인

**실행 명령어**:
```bash
# team_supervisor.py에서 load_recent_memories 호출 찾기
grep -n "load_recent_memories" backend/app/service_agent/supervisor/team_supervisor.py

# simple_memory_service.py에서 정의 찾기
grep -n "def load_recent_memories" backend/app/service_agent/foundation/simple_memory_service.py
```

**분석**:
```
team_supervisor.py:211
→ load_recent_memories(user_id, limit, relevance_filter)
  ❌ session_id 없음

simple_memory_service.py:443
→ def load_recent_memories(self, user_id, limit, relevance_filter)
  ❌ session_id 파라미터 없음
```

**사용자 확인 사항**:
- [ ] session_id 누락 확인
- [ ] CRITICAL_FIX 문서와 일치 확인

---

#### Step 2: 메서드 시그니처 비교

**실행 명령어**:
```bash
# save_conversation 호출
grep -A 10 "save_conversation" backend/app/service_agent/supervisor/team_supervisor.py | head -n 15

# save_conversation 정의
grep -A 10 "def save_conversation" backend/app/service_agent/foundation/simple_memory_service.py | head -n 15
```

**분석**:
- 호출: session_id 전달 ✅
- 정의: session_id 파라미터 있음 ✅
- → 일치 OK

**사용자 확인 사항**:
- [ ] save_conversation은 일치 확인
- [ ] load_recent_memories만 불일치 확인

---

#### Step 3: 불일치 종합 리포트 작성

**파일**: `reports/mismatch/mismatch_report_251020.md`

```markdown
# 불일치 항목 종합 리포트

**작성일**: 2025-10-20
**Phase**: 0.4

---

## 1. 메서드 시그니처 불일치

### 1.1 load_recent_memories

**team_supervisor.py:211**:
```python
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
    # ❌ session_id 누락
)
```

**simple_memory_service.py:443**:
```python
async def load_recent_memories(
    self,
    user_id: int,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
    # ❌ session_id 파라미터 없음
) -> List[Dict[str, Any]]:
```

**문제**:
- 현재 세션 제외 로직 없음
- 불완전한 데이터 로드 가능성

**해결책**: CRITICAL_FIX_session_id_mismatch_251020.md 참조

---

## 2. 좀비 메서드

### 2.1 entity_memories 관련

- `save_entity_memory()` - entity_memories 테이블 없음
- `get_entity_memories()` - entity_memories 테이블 없음

### 2.2 user_preferences 관련

- `update_user_preference()` - user_preferences 테이블 없음

**해결책**: Phase 1에서 제거 또는 NotImplementedError

---

## 3. Type Hints 누락

대부분의 메서드에 타입 힌트 없음

**해결책**: Phase 1에서 추가

---
```

**예상 소요 시간**: 5분

**사용자 확인 사항**:
- [ ] 불일치 항목 완전 목록화
- [ ] 우선순위 확인 (session_id > 좀비 > type hints)

---

### Phase 0.4 검증 체크리스트

```
✅ 완료 조건:
[ ] reports/mismatch/mismatch_report_251020.md 작성
[ ] session_id 불일치 상세 문서화
[ ] 좀비 메서드 목록화
[ ] 우선순위 설정

[ ] 사용자 승인: Phase 0 완료, Phase 1 준비
```

---

## 📊 Phase 0 최종 검증

### 전체 체크리스트

```
Phase 0.1: DB 스키마 추출
[ ] reports/schema/ 에 7개 파일
[ ] chat_sessions.metadata 확인
[ ] chat_messages.structured_data 확인
[ ] memory 테이블 없음 확인

Phase 0.2: Models 검증
[ ] scripts/validate_models_251020.py 작성
[ ] 검증 실행 성공
[ ] Models와 DB 100% 일치

Phase 0.3: 좀비 코드 탐지
[ ] old/ 디렉토리 발견
[ ] 좀비 메서드 목록화
[ ] 미완성 코드 탐지

Phase 0.4: 불일치 정리
[ ] session_id 불일치 문서화
[ ] 우선순위 설정
[ ] 종합 리포트 작성
```

### 산출물

```
reports/
├── schema/
│   ├── chat_sessions_251020.txt
│   ├── chat_messages_251020.txt
│   ├── users_251020.txt
│   ├── all_tables_251020.txt
│   ├── memory_tables_check_251020.txt
│   ├── jsonb_columns_251020.txt
│   └── foreign_keys_251020.txt
├── validation/
│   └── models_validation_251020.txt
├── zombie/
│   ├── zombie_directories_251020.txt
│   ├── zombie_imports_251020.txt
│   └── incomplete_code_251020.txt
└── mismatch/
    └── mismatch_report_251020.md

scripts/
└── validate_models_251020.py
```

---

## 🚀 다음 단계

Phase 0 완료 후:

1. **사용자 검토**: 모든 리포트 확인
2. **우선순위 합의**: 어떤 것부터 수정?
3. **Phase 1 계획**: 클린업 상세 계획 작성
4. **실행 승인**: Phase 1 시작

---

**예상 총 소요 시간**: 1-2시간
**중간 체크포인트**: 각 Step 완료 시 사용자 확인
**실패 시 대응**: 즉시 중단 및 분석

