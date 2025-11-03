# 💡 Memory Service 구현을 위한 간단한 선택 가이드
## 초보자를 위한 쉬운 설명

**작성일**: 2025-10-20
**대상**: 개발 초보자
**목적**: 3가지만 결정하면 바로 구현 시작!

---

## ✅ 현재 DB 상태 확인 완료!

사용자님이 제공한 정보로 확인된 사실:

```
✅ chat_messages에 structured_data 컬럼 있음!
✅ Memory 테이블 3개 없음! (conversation_memories, entity_memories, user_preferences)
✅ 총 17개 테이블 존재
```

**좋은 소식**: 계획서대로 진행 가능합니다! 🎉

---

## 🎯 꼭 결정해야 할 3가지 (5분이면 충분!)

### 결정 1️⃣: 한국어 검색 품질을 높일까요? (Phase 3)

**상황 설명**:
- 나중에 Phase 3에서 "비슷한 대화 찾기" 기능을 만들 예정입니다
- 예: 사용자가 "강남역 원룸"이라고 물었던 걸 나중에 "강남역 1인실"로 물어도 기억

**현재 계획**:
- 영어로 만들어진 AI 모델 사용 (all-MiniLM-L6-v2)
- 한국어도 작동하긴 하지만 정확도가 좀 떨어질 수 있음

**선택지**:

**A. 한국어 전용 모델 사용 (추천!)**
```
장점:
- 한국어 검색이 훨씬 정확함
- "강남역 원룸" ≈ "강남역 1인실" 매칭 잘 됨
- 사용자 경험 좋음

단점:
- 다운로드 크기가 좀 큼 (약 400MB)
- 초기 로딩이 몇 초 더 걸림

사용 모델: jhgan/ko-sbert-multitask
```

**B. 영어 모델 그대로 (계획서대로)**
```
장점:
- 가볍고 빠름 (약 80MB)
- 로딩 빠름

단점:
- 한국어 검색 정확도 낮을 수 있음
- "강남역" vs "강남역 근처" 같은 유사어 매칭 약함

사용 모델: all-MiniLM-L6-v2
```

**초보자 추천**: **A (한국어 모델)**
- 부동산 서비스는 한국어가 주력이니까요!
- 크기 차이는 실제로 크게 문제 안 됩니다

```
👉 선택: [ A - 한국어 모델 / B - 영어 모델 ]
```

---

### 결정 2️⃣: 여러 사용자가 동시에 채팅할 때 안전장치를 추가할까요? (Phase 1)

**상황 설명**:
- Phase 1에서는 대화를 `session_metadata`라는 곳에 임시 저장합니다
- 만약 같은 세션에서 2명이 **정확히 같은 순간**에 메시지를 보내면?
  - 한 사람의 메시지가 사라질 수 있음 (아주 드물지만)

**예시**:
```
사용자 A: "강남역 원룸 알아봐줘" (1초)
사용자 B: "홍대 원룸은?" (1초)

← 동시에 저장하려고 하면 한쪽이 덮어써질 수 있음
```

**선택지**:

**A. 안전장치 추가 (권장)**
```python
# 코드에 이 한 줄 추가
query = select(ChatSession).where(...).with_for_update()

의미:
- "지금 이 데이터를 수정 중이니 다른 사람은 잠깐 기다려!"
- 데이터 손실 방지

단점:
- 코드 한 줄 더 씁니다 (그게 다입니다)
```

**B. 안전장치 없이 (계획서대로)**
```
장점:
- 코드가 간단

단점:
- 아주 드물게 데이터 손실 가능
- 웹소켓은 보통 순차적이라 괜찮긴 함

상황:
- 1명만 사용 → 문제 없음
- 여러 명 동시 사용 → 아주 가끔 문제
```

**초보자 추천**: **A (안전장치 추가)**
- 코드 한 줄 차이인데 안전성이 높아집니다
- "혹시 모를 버그"를 미리 방지

```
👉 선택: [ A - 안전장치 추가 / B - 안전장치 없이 ]
```

---

### 결정 3️⃣: 백업을 자동으로 만들까요?

**상황 설명**:
- 이제부터 데이터베이스를 수정합니다 (Phase 2, 3)
- 혹시 실수하면 되돌릴 수 있게 백업이 필요합니다

**선택지**:

**A. 자동 백업 스크립트 사용 (강력 추천!)**
```bash
# Phase 시작할 때마다 자동으로 백업 생성
백업 파일: backup_20251020_140530.sql
         (날짜_시간.sql)

장점:
- 안심하고 개발 가능
- 문제 생기면 바로 복구
- 스크립트 한 번만 실행하면 됨

단점:
- 디스크 공간 약간 사용 (텍스트 파일이라 작음)
```

**B. 백업 안 함 (위험!)**
```
장점:
- 편함?

단점:
- 실수하면 데이터 날아감
- 되돌릴 방법 없음
- 다시 처음부터...
```

**초보자 추천**: **무조건 A (자동 백업)**
- 백업은 개발자의 생명줄입니다!
- 1분 투자로 큰 사고 방지

```
👉 선택: [ A - 자동 백업 / B - 백업 안 함 ]
```

---

## 📋 나머지는 자동으로 처리됩니다!

### 자동 처리 항목 (사용자가 신경 쓸 필요 없음)

#### ✅ chat_sessions.user_id FK 추가
**자동 처리**: Phase 2 마이그레이션에 포함
```sql
ALTER TABLE chat_sessions
ADD CONSTRAINT fk_chat_sessions_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```
**이유**: 데이터 무결성을 위해 필수입니다.

#### ✅ Memory 테이블 생성
**자동 처리**: Phase 2에서 Alembic이 자동 생성
```
- conversation_memories (대화 기억)
- entity_memories (장소/건물 기억)
- user_preferences (사용자 선호도)
```
**이유**: 계획서대로 진행합니다.

#### ✅ config.py 설정 추가
**자동 처리**: Phase 2 구현 시 자동 추가
```python
MEMORY_SERVICE_TYPE: str = "simple"  # Phase별 자동 전환
ENABLE_MEMORY_SERVICE: bool = True
```

#### ✅ users.py relationship 추가
**자동 처리**: Phase 2 첫 단계에서 추가
```python
conversation_memories = relationship("ConversationMemory", ...)
entity_memories = relationship("EntityMemory", ...)
preferences = relationship("UserPreference", ...)
```

#### ✅ team_supervisor.py 수정
**자동 처리**: Phase 2에서 import 경로만 변경
```python
# 기존
from app.service_agent.foundation.simple_memory_service import LongTermMemoryService

# 변경
from app.service_agent.foundation.memory_factory import get_memory_service
```

---

## 🎯 빠른 결정 템플릿 (복사해서 답변해주세요)

```
=== Memory Service 구현 결정 ===

결정 1️⃣ 한국어 모델 사용:
선택: [ A - 한국어 모델 (추천) ]

결정 2️⃣ 동시성 안전장치:
선택: [ A - 안전장치 추가 (추천) ]

결정 3️⃣ 자동 백업:
선택: [ A - 자동 백업 (강력 추천) ]

=== 추가 의견 (선택사항) ===


```

---

## 💡 각 결정이 코드에 미치는 영향

### 결정 1️⃣에 따른 변화

**A 선택 시 (한국어 모델)**:
```python
# Phase 3: complete_memory_service.py
embedding_model_name = "jhgan/ko-sbert-multitask"  # 한국어 모델
```

**B 선택 시 (영어 모델)**:
```python
# Phase 3: complete_memory_service.py
embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"  # 영어 모델
```

### 결정 2️⃣에 따른 변화

**A 선택 시 (안전장치)**:
```python
# Phase 1: simple_memory_service.py
async def save_conversation(...):
    # ✅ 이 한 줄 추가
    query_obj = select(ChatSession).where(...).with_for_update()

    result = await self.db.execute(query_obj)
    # ... 나머지 코드
```

**B 선택 시 (안전장치 없음)**:
```python
# Phase 1: simple_memory_service.py
async def save_conversation(...):
    # with_for_update() 없음
    query_obj = select(ChatSession).where(...)

    result = await self.db.execute(query_obj)
    # ... 나머지 코드
```

### 결정 3️⃣에 따른 변화

**A 선택 시 (자동 백업)**:
```bash
# Phase 0, Phase 2, Phase 3 시작 시 자동 실행
./scripts/backup_db.sh

# 백업 파일 생성됨
backups/backup_20251020_140530.sql
backups/backup_20251022_093045.sql
backups/backup_20251025_151200.sql
```

**B 선택 시**:
```
(백업 없음 - 추천하지 않음!)
```

---

## 🚀 결정 후 다음 단계

### 즉시 진행 사항:

1. **위 3가지 결정만 알려주세요**
   - 복사-붙여넣기로 답변하시면 됩니다

2. **최종 계획서 자동 생성**
   - 사용자의 결정을 반영한 맞춤형 계획서
   - 복사-붙여넣기만 하면 되는 실행 가능한 코드

3. **Phase 0 시작**
   - 백업 스크립트 실행 (선택한 경우)
   - 현재 상태 검증
   - 개발 브랜치 생성

4. **Phase 1 구현 (1일)**
   - 즉시 작동하는 메모리 기능
   - 테스트 통과 확인

5. **Phase 2 구현 (5일)**
   - 전용 메모리 테이블 생성
   - 사용자별 메모리 저장

6. **Phase 3 구현 (7일)**
   - AI 기반 유사 대화 찾기
   - 선택한 모델로 작동

---

## ❓ 궁금하실 만한 것들

### Q: "결정 1은 나중에 바꿀 수 있나요?"
**A**: 네! Phase 3 구현할 때 언제든지 모델만 바꾸면 됩니다.

### Q: "결정 2는 꼭 필요한가요?"
**A**: 1명만 사용하면 불필요하지만, 코드 한 줄이라 추가하는 걸 추천합니다.

### Q: "백업은 어떻게 복구하나요?"
**A**:
```bash
# 이 명령어 한 줄이면 복구됩니다
psql -U postgres -d real_estate < backups/backup_20251020_140530.sql
```

### Q: "다 모르겠어요. 추천대로 하면 되나요?"
**A**: 네! 그냥 이렇게 답변하세요:
```
결정 1️⃣: A
결정 2️⃣: A
결정 3️⃣: A
```

### Q: "실수하면 어떻게 되나요?"
**A**:
- 백업 있으면 → 복구하면 됩니다 (1분)
- Git 있으면 → 코드 되돌리면 됩니다
- Phase별로 진행 → 작은 단위로 검증하니 안전합니다

---

## 🎁 보너스: 자동으로 만들어질 것들

결정만 해주시면 자동으로 생성:

1. ✅ **맞춤형 최종 계획서**
   - 3가지 결정 반영
   - 실행 가능한 전체 코드
   - 단계별 체크리스트

2. ✅ **Phase별 마이그레이션 스크립트**
   - SQL 파일 자동 생성
   - 롤백 스크립트 포함

3. ✅ **테스트 코드**
   - Phase별 검증 스크립트
   - 자동 테스트

4. ✅ **실행 가이드**
   - 복사-붙여넣기 명령어
   - 각 단계 설명

---

## 📝 지금 해야 할 일

**1개만 하시면 됩니다**:

위의 "빠른 결정 템플릿"을 복사해서 선택만 표시해주세요!

```
결정 1️⃣: A 또는 B
결정 2️⃣: A 또는 B
결정 3️⃣: A 또는 B
```

**그러면**:
- 최종 계획서 즉시 생성
- 바로 구현 시작 가능
- 14일 후 100% 완성!

---

**작성일**: 2025-10-20
**난이도**: ⭐ (초보자도 OK!)
**소요 시간**: 결정 5분 + 구현 14일

---

*혹시 이해 안 되는 부분이 있으면 언제든지 물어보세요!*
*"추천대로 하겠습니다"라고만 하셔도 됩니다 😊*