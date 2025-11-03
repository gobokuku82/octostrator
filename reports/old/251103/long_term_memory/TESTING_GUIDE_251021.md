# 3-Tier Hybrid Memory 테스트 가이드

**Date:** 2025-10-21

---

## 1. 로그로 확인하는 방법 (가장 간단)

### 1-1. 로그 파일 위치

```bash
backend/logs/app.log
```

### 1-2. 확인할 로그 메시지들

구현된 코드에서 다음과 같은 로그가 자동으로 기록됩니다:

#### ✅ 메모리 로딩 시 (planning_node)
```
[TeamSupervisor] Loading Long-term Memory for user {user_id}
[TeamSupervisor] 3-Tier memories loaded - Short(N), Mid(N), Long(N)
```

**예시:**
```
2025-10-21 14:30:15 INFO [TeamSupervisor] Loading Long-term Memory for user 1
2025-10-21 14:30:15 INFO [TeamSupervisor] 3-Tier memories loaded - Short(3), Mid(4), Long(8)
```

**해석:**
- Short(3): 최근 1-3번째 세션, 전체 메시지 로드
- Mid(4): 4-7번째 세션, 요약만 로드
- Long(8): 8-15번째 세션, 요약만 로드

#### ✅ 백그라운드 요약 시작 시 (generate_response_node)
```
[TeamSupervisor] Background summary started for session: {session_id}
```

**예시:**
```
2025-10-21 14:30:25 INFO [TeamSupervisor] Background summary started for session: session-abc123
```

#### ✅ 백그라운드 요약 진행 중 (simple_memory_service.py)
```
Background summary task created for session: {session_id}
```

**예시:**
```
2025-10-21 14:30:25 INFO Background summary task created for session: session-abc123
```

#### ✅ 요약 저장 완료 시
```
Summary saved to metadata for session {session_id}
```

### 1-3. 실시간 로그 모니터링

**Windows PowerShell:**
```powershell
Get-Content "C:\kdy\Projects\holmesnyangz\beta_v001\backend\logs\app.log" -Wait -Tail 50 | Select-String "3-Tier|Background summary|Summary saved"
```

**필터링된 로그만 보기:**
```powershell
Get-Content "C:\kdy\Projects\holmesnyangz\beta_v001\backend\logs\app.log" | Select-String "3-Tier|Background summary" | Select-Object -Last 20
```

---

## 2. 데이터베이스로 확인하는 방법

### 2-1. 요약이 저장되었는지 확인

```sql
-- 특정 세션의 요약 확인
SELECT
    session_id,
    session_metadata->>'summary' as summary,
    session_metadata->>'summary_generated_at' as generated_at,
    created_at,
    updated_at
FROM chat_sessions
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 10;
```

**예상 결과:**
```
session_id       | summary                          | generated_at
-----------------+----------------------------------+-------------------------
session-abc123   | 강남구 아파트 전세 시세 문의...    | 2025-10-21T14:30:25Z
session-def456   | 대출 조건 비교 및 금리 문의...     | 2025-10-21T13:15:10Z
```

### 2-2. 세션 메시지 개수 확인

```sql
-- 세션별 메시지 개수
SELECT
    cs.session_id,
    COUNT(cm.id) as message_count,
    cs.session_metadata->>'summary' IS NOT NULL as has_summary,
    cs.created_at
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
WHERE cs.user_id = 1
GROUP BY cs.session_id, cs.session_metadata, cs.created_at
ORDER BY cs.created_at DESC
LIMIT 10;
```

---

## 3. 실제 테스트 시나리오

### 테스트 시나리오 1: 신규 사용자 (세션 5개 미만)

**상황:** 사용자가 처음 3개 대화만 했을 때

**기대 동작:**
```
[TeamSupervisor] 3-Tier memories loaded - Short(3), Mid(0), Long(0)
```

**확인 방법:**
1. 로그에서 `Short(3), Mid(0), Long(0)` 확인
2. 모든 세션의 전체 메시지가 로드됨

### 테스트 시나리오 2: 일반 사용자 (세션 6-10개)

**상황:** 사용자가 7개 대화를 했을 때

**기대 동작:**
```
[TeamSupervisor] 3-Tier memories loaded - Short(5), Mid(2), Long(0)
```

**확인 방법:**
1. 최근 5개: 전체 메시지
2. 6-7번째: 요약만 (DB에서 확인)
3. 로그에서 백그라운드 요약 시작 메시지 확인

### 테스트 시나리오 3: 파워유저 (세션 15개 이상)

**상황:** 사용자가 15개 대화를 했을 때

**기대 동작:**
```
[TeamSupervisor] 3-Tier memories loaded - Short(5), Mid(5), Long(5)
```

**확인 방법:**
1. 최근 1-5번째: 전체 메시지
2. 6-10번째: 요약만
3. 11-15번째: 요약만
4. DB에서 15개 세션 모두 요약 생성 확인

---

## 4. 간단한 테스트 스크립트

### Python 스크립트로 테스트

```python
# test_3tier_memory.py
import asyncio
from app.db.postgre_db import get_async_db
from app.service_agent.foundation.simple_memory_service import LongTermMemoryService

async def test_3tier_loading():
    """3-Tier 메모리 로딩 테스트"""
    print("="*80)
    print("3-Tier Hybrid Memory Loading Test")
    print("="*80)

    user_id = 1  # 테스트할 user_id

    async for db_session in get_async_db():
        memory_service = LongTermMemoryService(db_session)

        # 3-Tier 메모리 로드
        tiered_memories = await memory_service.load_tiered_memories(
            user_id=user_id,
            current_session_id=None
        )

        # 결과 출력
        print(f"\n✅ User ID: {user_id}")
        print(f"Short-term: {len(tiered_memories.get('shortterm', []))} sessions")
        print(f"Mid-term: {len(tiered_memories.get('midterm', []))} sessions")
        print(f"Long-term: {len(tiered_memories.get('longterm', []))} sessions")

        # Short-term 상세 정보
        print("\n📋 Short-term memories (full messages):")
        for session in tiered_memories.get('shortterm', []):
            session_id = session['session_id']
            message_count = len(session.get('messages', []))
            print(f"  - {session_id}: {message_count} messages")

        # Mid-term 상세 정보
        print("\n📋 Mid-term memories (summaries only):")
        for session in tiered_memories.get('midterm', []):
            session_id = session['session_id']
            summary = session.get('summary', 'No summary')[:50]
            print(f"  - {session_id}: {summary}...")

        # Long-term 상세 정보
        print("\n📋 Long-term memories (summaries only):")
        for session in tiered_memories.get('longterm', []):
            session_id = session['session_id']
            summary = session.get('summary', 'No summary')[:50]
            print(f"  - {session_id}: {summary}...")

        break

if __name__ == "__main__":
    asyncio.run(test_3tier_loading())
```

**실행:**
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
python test_3tier_memory.py
```

---

## 5. 문제 해결 (Troubleshooting)

### 문제 1: 로그에 3-Tier 메시지가 안 보임

**원인:**
- user_id가 None
- 또는 메모리 로딩 자체가 실패

**해결:**
1. user_id가 제대로 전달되는지 확인
2. 로그에서 에러 메시지 찾기: `Failed to load Long-term Memory`

### 문제 2: 백그라운드 요약이 안 생김

**원인:**
- LLM API 키 없음
- LLM 호출 실패

**해결:**
1. .env에서 `OPENAI_API_KEY` 확인
2. 로그에서 LLM 관련 에러 찾기
3. `session_metadata` JSONB 필드에 summary가 null인지 확인

### 문제 3: 요약이 생성되었는데 로딩 안 됨

**원인:**
- 요약 생성은 됐지만 로딩 로직 오류

**해결:**
1. DB에서 `session_metadata->>'summary'` 직접 조회
2. `_get_or_create_summary()` 메서드 로그 확인

---

## 6. 성공 기준

### ✅ 모든 테스트가 성공하면:

1. **로그 확인**
   ```
   [TeamSupervisor] 3-Tier memories loaded - Short(5), Mid(5), Long(10)
   [TeamSupervisor] Background summary started for session: ...
   Background summary task created for session: ...
   ```

2. **DB 확인**
   - 모든 세션에 `session_metadata->>'summary'` 존재
   - `summary_generated_at` 타임스탬프 기록됨

3. **동작 확인**
   - 1-5번째 세션: messages 배열에 데이터 있음
   - 6-20번째 세션: summary만 있음, messages는 빈 배열

---

## 7. 성능 확인

### 토큰 절약 효과 측정

**이전 (모든 세션 전체 메시지):**
```
20개 세션 × 평균 10개 메시지 × 평균 100 토큰 = 20,000 토큰
```

**현재 (3-Tier 적용):**
```
5개 세션 × 10개 메시지 × 100 토큰 = 5,000 토큰 (Short)
15개 세션 × 1개 요약 × 50 토큰 = 750 토큰 (Mid + Long)
총합: 5,750 토큰
```

**절약률:** 71% 토큰 절약!

---

**테스트 성공하면 이 가이드에 체크 표시하세요:**

- [ ] 로그에서 3-Tier 메시지 확인됨
- [ ] 백그라운드 요약 시작 메시지 확인됨
- [ ] DB에서 요약 저장 확인됨
- [ ] 테스트 스크립트 실행 성공
- [ ] 토큰 절약 효과 확인됨

---

**Created:** 2025-10-21
**Status:** Ready for Testing ✅
