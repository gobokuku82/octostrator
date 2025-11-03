# 3-Tier Hybrid Memory 기준점 설정 및 사용자 확인 사항

**작성일**: 2025-10-20
**목적**: 구현 전 모든 기준점 확립 및 사용자 확인 필요 사항 정리

---

## 🎯 구현 기준점 (Baseline)

### 1. 데이터베이스 구조 기준

#### 1-1. PostgreSQL 테이블 구조
```sql
-- chat_sessions 테이블
- session_id: VARCHAR(100) PRIMARY KEY  -- String 타입
- user_id: INTEGER (Foreign Key)        -- Integer 타입 ⚠️
- metadata: JSONB                       -- session_metadata로 매핑
- updated_at: TIMESTAMP WITH TIMEZONE
- created_at: TIMESTAMP WITH TIMEZONE

-- chat_messages 테이블
- id: INTEGER PRIMARY KEY
- session_id: VARCHAR(100) (Foreign Key)
- role: VARCHAR(20)
- content: TEXT
- structured_data: JSONB
- created_at: TIMESTAMP WITH TIMEZONE

-- 인덱스
- idx_chat_sessions_user_id
- idx_chat_sessions_updated_at
- idx_chat_sessions_user_updated (복합 인덱스)
```

#### 1-2. JSONB metadata 필드 구조
```json
{
  "conversation_summary": "string",      // 대화 요약
  "summary_method": "llm|simple",       // 요약 방식
  "summary_updated_at": "ISO datetime", // 요약 업데이트 시간
  "last_updated": "ISO datetime",       // 마지막 업데이트
  "message_count": number,              // 메시지 개수
  "relevance": "RELEVANT|IRRELEVANT"    // 관련성
}
```

---

### 2. State 관리 기준

#### 2-1. MainSupervisorState 구조
```python
MainSupervisorState = {
    # Core fields
    "query": str,
    "session_id": str,                    # LangGraph session
    "chat_session_id": Optional[str],     # DB chat_sessions.session_id
    "user_id": Optional[int],             # Integer 타입

    # Long-term Memory Fields (현재)
    "loaded_memories": Optional[List[Dict]],  # 하위 호환성 유지
    "user_preferences": Optional[Dict],       # 빈 dict (미구현)
    "memory_load_time": Optional[str],

    # 새로 추가될 필드
    "tiered_memories": Optional[Dict[str, List[Dict]]]  # 3-Tier 구조
}
```

#### 2-2. Checkpoint 시스템
```python
# AsyncPostgresSaver 사용 (PostgreSQL)
- checkpoints 테이블
- checkpoint_blobs 테이블
- checkpoint_writes 테이블

# 연결: settings.DATABASE_URL
# 형식: postgresql+psycopg://...
```

---

### 3. 메모리 서비스 기준

#### 3-1. 클래스 구조
```python
# simple_memory_service.py
class SimpleMemoryService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session  # ⚠️ self.db_session 아님!

    # 현재 메서드
    async def load_recent_memories(...)  # 다른 세션 로드
    async def save_conversation(...)      # 요약 저장
    async def get_user_preferences(...)   # 빈 dict 반환

    # 추가될 메서드
    async def load_tiered_memories(...)   # 3-Tier 로드
    async def summarize_with_llm(...)     # LLM 요약
    async def summarize_conversation_background(...)  # 백그라운드

# Alias
LongTermMemoryService = SimpleMemoryService  # Line 392
```

#### 3-2. 메서드 시그니처
```python
async def load_recent_memories(
    user_id: str,  # ⚠️ String인데 DB는 Integer
    limit: int = 5,
    relevance_filter: str = "ALL",
    session_id: Optional[str] = None
) -> List[Dict[str, Any]]
```

---

### 4. LLM 서비스 기준

#### 4-1. 프롬프트 관리
```python
# PromptManager 디렉토리 구조
prompts/
├── cognitive/     # 탐색됨
├── execution/     # 탐색됨
├── common/        # 탐색됨
└── memory/        # ❌ 탐색 안 됨!

# 카테고리 탐색 순서 (prompt_manager.py Line 226)
for cat in ["cognitive", "execution", "common"]:  # memory 없음
```

#### 4-2. 메서드 시그니처
```python
async def complete_async(
    prompt_name: str,      # "/" 경로 지원 안 됨
    variables: Dict[str, Any] = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    **kwargs
) -> str
```

---

### 5. 설정 관리 기준

#### 5-1. 현재 설정
```bash
# .env
MEMORY_LOAD_LIMIT=5  # 현재 유일한 메모리 설정
DATABASE_URL=postgresql+psycopg://...
```

#### 5-2. Pydantic Settings
```python
# config.py
from typing import List
from pydantic_settings import BaseSettings
# ❌ from pydantic import Field 없음!

class Settings(BaseSettings):
    MEMORY_LOAD_LIMIT: int = 5  # Field 없이
```

---

## ❓ 사용자 확인 필요 사항

### 🔴 Critical - 즉시 확인 필요

#### 1. **user_id 타입 불일치**
```
현재 상황:
- DB 스키마: user_id INTEGER
- 메서드 파라미터: user_id: str
- State: user_id: Optional[int]

질문: 어떤 타입을 표준으로 할까요?
  A. DB 기준 (Integer) - 타입 변환 추가
  B. 코드 기준 (String) - DB 마이그레이션
  C. 혼용 허용 - 자동 변환 로직
```

#### 2. **프롬프트 파일 위치**
```
현재 상황:
- 카테고리 탐색: ["cognitive", "execution", "common"]
- memory 카테고리 미지원
- "/" 경로 분리 미지원

질문: 새 프롬프트 파일 어디에?
  A. prompts/common/conversation_summary.txt (추천)
  B. prompts/memory/ 생성 + 코드 수정
  C. prompts/cognitive/ 활용
```

#### 3. **3-Tier 메모리 범위 최종 확인**
```
현재 계획:
- Short-term: 1-5 세션 (전체 메시지)
- Mid-term: 6-10 세션 (LLM 요약)
- Long-term: 11-20 세션 (LLM 요약)

질문: 이 범위가 맞나요?
설정값 확인:
- SHORTTERM_MEMORY_LIMIT=5
- MIDTERM_MEMORY_LIMIT=5
- LONGTERM_MEMORY_LIMIT=10
```

---

### ⚠️ High - 구현 방식 결정

#### 4. **백그라운드 요약 에러 처리**
```
현재 계획:
- asyncio.create_task() 사용 (fire-and-forget)
- 실패 시 조용히 실패

질문: 에러 처리 방식?
  A. 로깅만 (현재 계획)
  B. 재시도 로직 추가
  C. 에러 큐 관리
  D. 상태 모니터링 추가
```

#### 5. **JSONB 동시성 처리**
```
잠재적 문제:
- 백그라운드 요약 중 동일 세션 업데이트
- Race condition 가능

질문: 동시성 처리?
  A. 현재대로 (PostgreSQL MVCC 의존)
  B. Optimistic locking (version 체크)
  C. SELECT FOR UPDATE 사용
  D. 백그라운드 요약 비활성화
```

#### 6. **메모리 로드 성능**
```
현재 계획:
- Short-term: 5세션 × 전체 메시지
- 예상: 세션당 20메시지 = 100메시지
- 토큰: ~12,500 토큰

질문: 성능/비용 허용 범위?
  A. 현재대로 진행
  B. 메시지 수 제한 추가
  C. 요약 강제 (전체 메시지 X)
```

---

### 💡 Medium - 옵션 선택

#### 7. **기존 loaded_memories 호환성**
```
현재:
state["loaded_memories"] = List[Dict]

계획:
state["loaded_memories"] = short + mid + long  # 호환성
state["tiered_memories"] = {"shortterm": [...], ...}  # 신규

질문: 호환성 유지 방식?
  A. 위 계획대로 (병합 + 별도)
  B. loaded_memories 제거
  C. 점진적 마이그레이션
```

#### 8. **요약 길이 설정**
```
계획:
- Mid-term: 200자
- Long-term: 200자 (동일)

질문: 차등 적용?
  A. 동일 (200자)
  B. Mid-term 200자, Long-term 100자
  C. 설정 가능하게 (현재 계획)
```

#### 9. **ChatSession vs LangGraph Session**
```
현재:
- chat_session_id: DB의 chat_sessions.session_id
- session_id: LangGraph checkpoint session

질문: 명확한 구분 필요?
  A. 현재 이름 유지
  B. db_session_id vs lg_session_id
  C. 문서화로만 구분
```

---

### 📌 Low - 향후 고려사항

#### 10. **메모리 캐싱**
```
질문: 메모리 캐싱 필요?
  A. 불필요 (매번 DB 조회)
  B. Redis 캐싱 추가
  C. 인메모리 캐싱
```

#### 11. **메모리 압축**
```
질문: Long-term 압축?
  A. 텍스트 그대로
  B. gzip 압축
  C. 임베딩 변환
```

---

## 📋 구현 전 체크리스트

### 필수 확인 (Must Have)
- [ ] user_id 타입 결정 (Integer vs String)
- [ ] 프롬프트 파일 위치 결정
- [ ] 3-Tier 범위 최종 확인
- [ ] self.db vs self.db_session 확인

### 중요 결정 (Should Have)
- [ ] 백그라운드 에러 처리 방식
- [ ] JSONB 동시성 처리 방식
- [ ] 성능/비용 허용 범위

### 선택 사항 (Nice to Have)
- [ ] 호환성 유지 방식
- [ ] 요약 길이 차등
- [ ] 세션 명명 규칙

---

## 🔧 수정 필요 항목 매핑

### 사용자 결정에 따른 수정 사항

#### user_id 타입 = Integer 선택 시
```python
# 모든 메서드에 추가
if isinstance(user_id, str):
    user_id = int(user_id)
```

#### 프롬프트 = common 선택 시
```python
# 변경
prompt_name="conversation_summary"  # not "memory/..."
# 파일 위치
prompts/common/conversation_summary.txt
```

#### 백그라운드 에러 = 재시도 선택 시
```python
# 추가 구현 필요
async def _retry_with_backoff(func, *args, **kwargs):
    for attempt in range(3):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)
```

---

## 🚀 구현 준비 상태

### 확정된 사항
1. ✅ SimpleMemoryService에 메서드 추가 (새 클래스 X)
2. ✅ self.db 사용 (self.db_session X)
3. ✅ get_user_preferences() 사용 (load_ X)
4. ✅ AsyncPostgresSaver checkpoint 시스템
5. ✅ JSONB metadata 필드 구조

### 미확정 사항 (사용자 응답 필요)
1. ❓ user_id 타입
2. ❓ 프롬프트 위치
3. ❓ 백그라운드 에러 처리
4. ❓ JSONB 동시성
5. ❓ 성능/비용 한계

---

## 📊 리스크 평가

| 항목 | 리스크 레벨 | 영향도 | 완화 방안 |
|------|------------|--------|----------|
| user_id 타입 불일치 | 🔴 High | 런타임 에러 | 타입 변환 로직 |
| 프롬프트 로딩 실패 | 🔴 High | 요약 불가 | common 사용 |
| 백그라운드 실패 | 🟡 Medium | 요약 누락 | 로깅 강화 |
| JSONB 충돌 | 🟡 Medium | 데이터 손실 | Version 체크 |
| 토큰 초과 | 🟡 Medium | 비용 증가 | 제한 설정 |
| 성능 저하 | 🟢 Low | 응답 지연 | 캐싱 고려 |

---

## 💬 권장 사항

### 우선순위 1: 안정성
```
1. user_id: Integer로 통일 (DB 기준)
2. 프롬프트: common 디렉토리 사용
3. 에러 처리: 로깅만 (복잡도 최소화)
```

### 우선순위 2: 성능
```
1. JSONB: PostgreSQL MVCC 의존
2. 백그라운드: 활성화 (비동기 처리)
3. 캐싱: 향후 고려
```

### 우선순위 3: 확장성
```
1. 설정 가능한 범위
2. 호환성 유지
3. 점진적 마이그레이션
```

---

**작성 완료**: 2025-10-20
**다음 단계**: 사용자 응답 후 최종 구현 계획 수정