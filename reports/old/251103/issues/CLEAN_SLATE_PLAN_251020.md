# 🎯 클린 슬레이트(Clean Slate) 재설계 계획서
## DB 스키마 기준 단일 진실 공급원(Single Source of Truth)

**작성일**: 2025-10-20
**목적**: 좀비 코드 제거 및 명확한 기준점 수립
**원칙**: DB 스키마가 모든 코드의 기준

---

## 📊 문제 진단

### 현재 상황

```
구현 중 → 변경 → 새 기능 추가 → 변경 → 오류 수정
     ↓         ↓              ↓        ↓          ↓
  좀비코드 | 불일치 | 미완성 코드 | 혼란 | 누락
```

**결과**:
- ❌ 계획서 ≠ 실제 코드
- ❌ 코드 A ≠ 코드 B (team_supervisor vs simple_memory_service)
- ❌ 설계 의도 불명확
- ❌ "무엇이 진실인가?" 불명확

---

## 🎯 해결 전략

### 원칙 1: Single Source of Truth (SSOT)

```
                    ┌─────────────────┐
                    │  DB Schema      │ ← 단일 진실
                    │  (Production)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │ Models  │   │  Code   │   │  Docs   │
         │ (.py)   │   │  Logic  │   │  Plans  │
         └─────────┘   └─────────┘   └─────────┘
              ▲              ▲              ▲
              └──────────────┴──────────────┘
                   모두 DB 스키마 기준
```

### 원칙 2: 역방향 설계 (Reverse Engineering)

**기존 방식 (Top-Down)** ❌:
```
계획서 작성 → 모델 설계 → DB 생성 → 코드 구현
  ↓
계획서 변경 시 모든 것 재작업
```

**새로운 방식 (Bottom-Up)** ✅:
```
현재 DB 스키마 추출 → 모델 검증 → 코드 정렬 → 계획서 작성
  ↓
DB가 변하지 않으면 모든 것 안정적
```

### 원칙 3: 3단계 검증

```
1️⃣ DB Schema (Production)
   └─ 검증: psql 직접 조회

2️⃣ SQLAlchemy Models
   └─ 검증: DB 스키마와 1:1 일치

3️⃣ Application Code
   └─ 검증: Models API만 사용
```

---

## 📋 Phase 0: 기준점 수립 (현재 상태의 진실 파악)

### Step 0.1: DB 스키마 완전 추출

**목표**: 실제 Production DB의 정확한 스냅샷

**작업**:

```bash
# 1. 전체 스키마 덤프
psql -U postgres -d real_estate -c "\d+" > reports/db_schema_snapshot_251020.txt

# 2. 테이블 목록
psql -U postgres -d real_estate -c "
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
ORDER BY table_name;
" > reports/db_tables_251020.txt

# 3. 각 테이블 상세 (Memory 관련만)
psql -U postgres -d real_estate -c "\d chat_sessions" > reports/schema_chat_sessions.txt
psql -U postgres -d real_estate -c "\d chat_messages" > reports/schema_chat_messages.txt
psql -U postgres -d real_estate -c "\d users" > reports/schema_users.txt

# 4. 존재하지 않는 테이블 확인
psql -U postgres -d real_estate -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('conversation_memories', 'entity_memories', 'user_preferences');
" > reports/missing_memory_tables.txt
```

**예상 결과** (사용자 제공 정보 기준):

```
✅ 존재하는 테이블 (17개):
   - users
   - chat_sessions (session_metadata JSONB 포함)
   - chat_messages (structured_data JSONB 포함)
   - real_estates
   - transactions
   - ... (총 17개)

❌ 존재하지 않는 테이블 (3개):
   - conversation_memories
   - entity_memories
   - user_preferences
```

### Step 0.2: SQLAlchemy Models 검증

**목표**: Models가 실제 DB 스키마와 100% 일치하는지 확인

**검증 스크립트**: `scripts/validate_models_vs_db.py`

```python
"""
DB Schema vs SQLAlchemy Models 일치 여부 검증
"""

import asyncio
from sqlalchemy import inspect, text
from app.db.postgre_db import get_async_db, engine
from app.models import *

async def validate_models_vs_db():
    """
    각 모델의 컬럼이 실제 DB 테이블과 일치하는지 검증
    """
    print("=" * 70)
    print("DB Schema vs SQLAlchemy Models Validation")
    print("=" * 70)

    async with engine.begin() as conn:
        # DB에서 실제 테이블 목록 가져오기
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        db_tables = {row[0] for row in result}

        print(f"\n📊 DB Tables ({len(db_tables)}): {sorted(db_tables)}\n")

        # SQLAlchemy Models 목록
        inspector = inspect(engine)
        model_tables = set(inspector.get_table_names())

        print(f"🐍 Model Tables ({len(model_tables)}): {sorted(model_tables)}\n")

        # 차이점 검출
        only_in_db = db_tables - model_tables
        only_in_models = model_tables - db_tables

        if only_in_db:
            print(f"⚠️  DB에만 있는 테이블 (Models 없음):")
            for table in sorted(only_in_db):
                print(f"   - {table}")
            print()

        if only_in_models:
            print(f"⚠️  Models에만 있는 테이블 (DB 없음):")
            for table in sorted(only_in_models):
                print(f"   - {table}")
            print()

        # 공통 테이블에 대해 컬럼 비교
        common_tables = db_tables & model_tables
        print(f"✅ 공통 테이블 ({len(common_tables)}):\n")

        mismatches = []

        for table_name in sorted(common_tables):
            # DB 컬럼
            result = await conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """))
            db_columns = {row[0]: (row[1], row[2]) for row in result}

            # Model 컬럼 (실제로는 inspector 사용)
            model_columns = {col['name']: (str(col['type']), col['nullable'])
                           for col in inspector.get_columns(table_name)}

            # 차이점
            only_in_db_cols = set(db_columns.keys()) - set(model_columns.keys())
            only_in_model_cols = set(model_columns.keys()) - set(db_columns.keys())

            if only_in_db_cols or only_in_model_cols:
                mismatches.append({
                    'table': table_name,
                    'only_db': only_in_db_cols,
                    'only_model': only_in_model_cols
                })
                print(f"   ⚠️  {table_name}:")
                if only_in_db_cols:
                    print(f"      DB에만: {only_in_db_cols}")
                if only_in_model_cols:
                    print(f"      Model에만: {only_in_model_cols}")
            else:
                print(f"   ✅ {table_name} - Perfect match")

        print("\n" + "=" * 70)
        if mismatches:
            print(f"❌ {len(mismatches)} 테이블에서 불일치 발견!")
            return False
        else:
            print("✅ 모든 테이블 완벽 일치!")
            return True

if __name__ == "__main__":
    result = asyncio.run(validate_models_vs_db())
    exit(0 if result else 1)
```

**실행**:
```bash
cd backend
python scripts/validate_models_vs_db.py
```

### Step 0.3: 좀비 코드 탐지

**목표**: 사용되지 않는 코드, 불일치 코드 찾기

**탐지 대상**:

1. **좀비 파일**:
   ```bash
   # old/, migrations_old/, scripts_old/ 폴더 확인
   find backend -type d -name "*old*" -o -name "*backup*"
   ```

2. **좀비 import**:
   ```bash
   # 실제 없는 모델 import
   grep -r "from app.models.memory import" backend/app --include="*.py"
   # → conversation_memories 없는데 import하면 좀비
   ```

3. **좀비 메서드**:
   ```python
   # simple_memory_service.py
   async def get_entity_memories(...):  # ← entity_memories 테이블 없는데 메서드 존재
       return []  # 좀비!
   ```

**좀비 코드 목록 작성**: `reports/zombie_code_report_251020.md`

### Step 0.4: 불일치 항목 목록화

**목표**: 코드 간 불일치 모두 찾기

**불일치 카테고리**:

1. **메서드 시그니처 불일치**:
   ```
   team_supervisor.py:211
   → load_recent_memories(user_id, limit, relevance_filter)

   simple_memory_service.py:443
   → load_recent_memories(user_id, limit, relevance_filter)

   ❌ session_id 파라미터 불일치!
   ```

2. **데이터 타입 불일치**:
   ```
   ChatSession.session_metadata: JSONB
   vs
   코드에서 dict로 가정 (맞음)
   ```

3. **Null 처리 불일치**:
   ```
   DB: session_metadata nullable
   코드: if not session.session_metadata: (체크함) ✅
   ```

**불일치 리포트**: `reports/mismatch_report_251020.md`

---

## 📋 Phase 1: 클린업 (좀비 제거 및 정렬)

### Step 1.1: 좀비 파일 제거

```bash
# 백업 후 삭제
git mv backend/app/models/old backend_archive/models_old_251020
git mv backend/migrations_old backend_archive/migrations_old_251020
git mv backend/scripts_old backend_archive/scripts_old_251020

git commit -m "Archive zombie directories"
```

### Step 1.2: 좀비 코드 제거

**simple_memory_service.py 정리**:

```python
# Before (좀비 메서드들)
async def save_entity_memory(...):  # ← entity_memories 테이블 없음
    return True  # 좀비!

async def get_entity_memories(...):  # ← entity_memories 테이블 없음
    return []  # 좀비!

# After (제거 또는 명확한 주석)
# Phase 2에서 entity_memories 테이블 생성 후 구현 예정
# async def save_entity_memory(...):
#     raise NotImplementedError("Phase 2에서 구현")
```

### Step 1.3: 불일치 수정

**우선순위 1: session_id 파라미터 추가** (CRITICAL_FIX 적용)

**우선순위 2: Type hints 추가**:
```python
from typing import Optional, List, Dict, Any

async def load_recent_memories(
    self,
    user_id: int,  # ✅ 명확한 타입
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT",
    session_id: Optional[str] = None  # ✅ 추가
) -> List[Dict[str, Any]]:  # ✅ 명확한 반환 타입
```

---

## 📋 Phase 2: 새 계획서 작성 (DB 스키마 기준)

### 원칙

**DB Schema → Models → Code → Plan** 순서로 작성

### 구조

```markdown
# Memory Service 구현 계획서 (DB Schema 기준)

## 1. 현재 상태 (Ground Truth)

### 1.1 DB 스키마 (Production)
```sql
-- 실제 DB에 존재하는 것만
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER,  -- FK 없음 (Phase 2에서 추가)
    session_metadata JSONB,  -- ✅ 이미 존재!
    ...
);
```

### 1.2 SQLAlchemy Models
```python
# 실제 models/chat.py
class ChatSession(Base):
    session_metadata = Column("metadata", JSONB)  # ✅ 일치
```

### 1.3 Application Code
```python
# 실제 team_supervisor.py:211
loaded_memories = await memory_service.load_recent_memories(...)
# ❌ session_id 누락 - 수정 필요
```

## 2. 목표 상태 (Phase별)

### Phase 1: 현재 DB 스키마 그대로 사용
- chat_sessions.session_metadata 활용
- 테이블 추가 없음
- 마이그레이션 없음

### Phase 2: Memory 전용 테이블 추가
- conversation_memories 생성
- entity_memories 생성
- user_preferences 생성

## 3. 구현 (DB 스키마 기준)

### Phase 1 구현
```python
# session_metadata JSONB 구조
{
    "memories": [
        {
            "query": "...",
            "response_summary": "...",
            "timestamp": "...",
            ...
        }
    ]
}
```
```

---

## 🎯 실행 계획

### 즉시 실행 (오늘)

```bash
# 1. DB 스키마 추출
cd backend
psql -U postgres -d real_estate -c "\d chat_sessions" > ../reports/schema_chat_sessions_251020.txt
psql -U postgres -d real_estate -c "\d chat_messages" > ../reports/schema_chat_messages_251020.txt
psql -U postgres -d real_estate -c "\d users" > ../reports/schema_users_251020.txt

# 2. Models 검증
python scripts/validate_models_vs_db.py > ../reports/models_validation_251020.txt

# 3. 좀비 코드 탐지
find . -type d -name "*old*" > ../reports/zombie_directories_251020.txt
grep -r "NotImplementedError\|TODO\|FIXME" app --include="*.py" > ../reports/incomplete_code_251020.txt
```

### 단계별 실행 (이번 주)

**Day 1 (오늘)**:
- [ ] DB 스키마 추출 완료
- [ ] Models 검증 완료
- [ ] 좀비 코드 목록 작성 완료
- [ ] 불일치 리포트 작성 완료

**Day 2**:
- [ ] 좀비 코드 제거 (git archive)
- [ ] session_id 불일치 수정
- [ ] Type hints 추가

**Day 3**:
- [ ] 새 계획서 작성 (DB 기준)
- [ ] 최종 검토

---

## ✅ 성공 기준

### Phase 0 완료 조건

```
✅ DB 스키마 완전 추출 (모든 테이블)
✅ Models vs DB 100% 일치 확인
✅ 좀비 코드 전체 목록화
✅ 불일치 항목 전체 목록화
✅ 기준점 명확화 (DB Schema = SSOT)
```

### Phase 1 완료 조건

```
✅ 좀비 디렉토리 archive
✅ 좀비 메서드 제거/주석 처리
✅ session_id 불일치 수정
✅ Type hints 완료
✅ 모든 코드 DB 스키마 기준 정렬
```

### Phase 2 완료 조건

```
✅ 새 계획서 작성 (DB 기준)
✅ 계획서 vs 코드 100% 일치
✅ 단일 진실 공급원 확립
✅ 향후 변경 시 절차 명문화
```

---

## 📝 질문에 대한 답변

> "처음부터 계획을 다시 수립하는게 안전한가?"

**답**: ✅ **예, 하지만 조건부**

**조건**:
1. ✅ DB 스키마를 기준점으로 확립
2. ✅ 현재 상태(좀비 코드 포함) 완전 파악
3. ✅ 단계적 정리 후 새 계획 작성

**방법**:
- Phase 0: 진실 파악 (DB 스키마 추출)
- Phase 1: 정리 (좀비 제거, 불일치 수정)
- Phase 2: 새 계획 (클린 상태 기준)

> "기준을 어떻게 잡지? DB schema를 기준으로 잡으면 될까?"

**답**: ✅ **완전히 맞습니다!**

**이유**:
1. DB Schema = Production Truth (실제 운영 데이터)
2. 코드는 바뀌어도 DB는 안정적
3. 데이터가 진실, 코드는 해석

**원칙**:
```
DB Schema (Production)
   ↓ 기준
SQLAlchemy Models
   ↓ 기준
Application Code
   ↓ 기준
Documentation
```

> "좀비코드와 지저분한 코드, 변경사항들이 섞인것 같아"

**답**: ✅ **정확한 진단!**

**해결책**:
1. 좀비 탐지 → 목록화
2. 불일치 탐지 → 목록화
3. 우선순위 정리 (Critical → Major → Minor)
4. 단계적 클린업
5. 클린 상태에서 새 계획

---

## 🎁 산출물

이 계획 완료 후:

1. **`reports/db_schema_snapshot_251020.txt`** - 완전한 DB 스키마
2. **`reports/models_validation_251020.txt`** - Models 검증 결과
3. **`reports/zombie_code_report_251020.md`** - 좀비 코드 목록
4. **`reports/mismatch_report_251020.md`** - 불일치 항목
5. **`CLEAN_SLATE_PLAN_FINAL_251020.md`** - 클린 상태 기준 최종 계획서

---

**작성일**: 2025-10-20
**상태**: ✅ 실행 준비 완료
**다음 단계**: 사용자 승인 후 Phase 0 시작

---

## 🚀 지금 바로 시작할까요?

**Option A**: Phase 0 즉시 시작
```bash
# DB 스키마 추출부터 시작
bash scripts/extract_db_schema.sh
```

**Option B**: 먼저 이 계획 검토 후 조정
```
사용자님의 피드백 반영 → 계획 수정 → 실행
```

어떤 방식을 선호하시나요?
