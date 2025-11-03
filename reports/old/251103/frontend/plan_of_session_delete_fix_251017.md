# Session 삭제 버튼 수정 계획서 - 2025-10-17

## 문제 요약 (Problem Summary)

### 현재 증상
1. **"최근 대화" 세션 삭제 버튼 클릭**
2. **제목이 `[삭제됨]`으로 변경되지만 목록에서 사라지지 않음**
3. **무한 중첩 가능**: `[삭제됨][삭제됨][삭제됨]...` 반복 생성

### 사용자 요구사항
- ✅ 삭제 버튼 클릭 시 세션이 **완전히 삭제**되고 **목록에서 즉시 사라져야 함**
- ✅ PostgreSQL에서 데이터 완전 제거 (hard delete)

---

## 근본 원인 분석 (Root Cause Analysis)

### 1. Backend의 Soft Delete 기본 동작

**파일**: `backend/app/api/chat_api.py`

**Line 452-522**: `delete_chat_session()` 함수

```python
@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    hard_delete: bool = False,  # ❌ 기본값이 False
    db: AsyncSession = Depends(get_async_db)
):
    if hard_delete:
        # 하드 삭제 (완전 삭제)
        await db.delete(session)
        # ...
    else:
        # ❌ 소프트 삭제 (기본 동작)
        session.title = f"[삭제됨] {session.title}"  # 제목만 변경
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
```

**문제점**:
- **기본값이 `hard_delete=False`** → Soft Delete 실행
- Soft Delete는 제목만 `[삭제됨]`으로 변경하고 **DB에서 삭제하지 않음**
- Frontend는 여전히 세션을 받아와서 표시함

---

### 2. Frontend의 hard_delete 파라미터 전달

**파일**: `frontend/hooks/use-chat-sessions.ts`

**Line 147-182**: `deleteSession()` 함수

```typescript
const deleteSession = useCallback(async (sessionId: string, hardDelete: boolean = false): Promise<boolean> => {
    try {
        const response = await fetch(
            `${API_BASE_URL}/sessions/${sessionId}?hard_delete=${hardDelete}`,  // ✅ hard_delete 전달
            { method: 'DELETE' }
        )

        // ...

        // ✅ 로컬 상태에서 세션 제거 (UI에서 사라짐)
        setSessions(prev => prev.filter(s => s.id !== sessionId))

        return true
    } catch (err) {
        // ...
    }
}, [currentSessionId, sessions])
```

**분석**:
- Frontend는 `hardDelete` 파라미터를 받을 수 있음
- 하지만 **기본값이 `false`**
- API 호출은 올바르게 구현됨
- 로컬 상태 업데이트도 올바름 (`setSessions` 필터링)

---

### 3. 호출 체인 분석

**호출 순서**:
```
[session-list.tsx]
  ↓ onClick
onSessionDelete(session.id)  // ❌ 파라미터 1개만 전달
  ↓
[page.tsx]
deleteSession(sessionId)  // ❌ hardDelete 전달 안 됨 (기본값 false 사용)
  ↓
[use-chat-sessions.ts]
deleteSession(sessionId, hardDelete=false)  // ❌ false로 실행
  ↓
[Backend API]
DELETE /sessions/{sessionId}?hard_delete=false  // ❌ Soft Delete 실행
  ↓
session.title = "[삭제됨] " + session.title  // ❌ 제목만 변경
```

---

## 문제 발생 이유 정리

### ❌ 왜 `[삭제됨]`만 표시되나?

1. **Backend**: `hard_delete=false`로 받아서 Soft Delete 실행
2. **Soft Delete**: 제목을 `[삭제됨] {원래 제목}`으로 변경
3. **Frontend**: API가 성공(200) 반환하면 로컬 상태에서 제거
4. **하지만**: 다음 새로고침 시 `/sessions` API에서 여전히 해당 세션 반환
5. **결과**: 다시 목록에 나타남 (제목은 `[삭제됨]`으로 변경된 채로)

### ❌ 왜 무한 중첩되나?

1. **첫 번째 삭제**: `"새 대화"` → `"[삭제됨] 새 대화"`
2. **두 번째 삭제**: `"[삭제됨] 새 대화"` → `"[삭제됨] [삭제됨] 새 대화"`
3. **세 번째 삭제**: `"[삭제됨] [삭제됨] 새 대화"` → `"[삭제됨] [삭제됨] [삭제됨] 새 대화"`
4. **반복...**

**원인**: Soft Delete 로직이 **현재 제목에 계속 `[삭제됨]` 추가**하기 때문

---

## 해결 방안 (Solution)

### Option 1: Frontend에서 hard_delete=true 전달 (추천 ⭐)

**장점**:
- ✅ Backend 수정 불필요
- ✅ 완전 삭제 보장
- ✅ PostgreSQL에서 데이터 완전 제거
- ✅ Cascade로 messages도 자동 삭제

**단점**:
- 복구 불가능 (영구 삭제)

**구현**:
```typescript
// frontend/hooks/use-chat-sessions.ts
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    const response = await fetch(
        `${API_BASE_URL}/sessions/${sessionId}?hard_delete=true`,  // ✅ true로 변경
        { method: 'DELETE' }
    )
    // ...
}, [currentSessionId, sessions])
```

---

### Option 2: Backend 기본값 변경

**장점**:
- Frontend 수정 불필요

**단점**:
- ❌ 복구 불가능 (기본 동작이 영구 삭제)
- ❌ 향후 Soft Delete가 필요한 경우 불편

**구현**:
```python
# backend/app/api/chat_api.py
@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    hard_delete: bool = True,  # ✅ 기본값을 True로 변경
    db: AsyncSession = Depends(get_async_db)
):
    # ...
```

---

### Option 3: Soft Delete 필터링 (권장하지 않음)

**아이디어**: `[삭제됨]`으로 시작하는 세션은 Frontend에서 필터링

**단점**:
- ❌ DB에 쓰레기 데이터 계속 쌓임
- ❌ 성능 저하 (조회는 하지만 표시 안 함)
- ❌ 근본적 해결 아님

---

## 권장 해결 방안 (Recommended Solution)

### ✅ Option 1 채택: Frontend에서 hard_delete=true 전달

**이유**:
1. **사용자 요구사항 충족**: "삭제하고 안보이면 좋겠어"
2. **Backend 로직 보존**: Soft Delete 기능은 나중에 필요할 수 있음
3. **명확한 의도**: 사용자가 삭제 버튼 누르면 = 완전 삭제 의도
4. **DB 정리**: 불필요한 데이터 누적 방지

---

## 상세 수정 계획 (Detailed Fix Plan)

### Step 1: use-chat-sessions.ts 수정

**파일**: `frontend/hooks/use-chat-sessions.ts`

**Before** (Line 147):
```typescript
const deleteSession = useCallback(async (sessionId: string, hardDelete: boolean = false): Promise<boolean> => {
    try {
        const response = await fetch(
            `${API_BASE_URL}/sessions/${sessionId}?hard_delete=${hardDelete}`,
            { method: 'DELETE' }
        )
        // ...
    }
}, [currentSessionId, sessions])
```

**After**:
```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
        // ✅ hard_delete=true로 고정 (완전 삭제)
        const response = await fetch(
            `${API_BASE_URL}/sessions/${sessionId}?hard_delete=true`,
            { method: 'DELETE' }
        )
        // ...
    }
}, [currentSessionId, sessions])
```

**변경사항**:
1. ❌ `hardDelete` 파라미터 제거 (불필요)
2. ✅ `hard_delete=true`로 고정
3. ✅ 함수 시그니처 단순화

---

### Step 2: 기존 Soft Deleted 세션 정리 (선택 사항)

**문제**: 이미 `[삭제됨]`으로 표시된 세션들이 DB에 남아있음

**해결책 1: SQL로 직접 삭제**
```sql
-- PostgreSQL 명령
DELETE FROM chat_sessions
WHERE title LIKE '[삭제됨]%';
```

**해결책 2: Backend에 정리 엔드포인트 추가** (추후)
```python
@router.post("/cleanup/soft-deleted")
async def cleanup_soft_deleted_sessions(db: AsyncSession = Depends(get_async_db)):
    """Soft Delete된 세션 완전 삭제"""
    result = await db.execute(
        "DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%'"
    )
    await db.commit()
    return {"deleted_count": result.rowcount}
```

---

## 테스트 계획 (Testing Plan)

### Test Case 1: 정상 삭제

**시나리오**:
1. 세션 목록에서 세션 선택
2. 삭제 버튼 클릭
3. 확인 다이얼로그에서 "확인"

**예상 결과**:
- ✅ 세션이 목록에서 즉시 사라짐
- ✅ F5 새로고침 해도 사라진 상태 유지
- ✅ PostgreSQL에서 세션 조회 시 404 반환

**검증 SQL**:
```sql
SELECT * FROM chat_sessions WHERE session_id = '{삭제된 session_id}';
-- 결과: 0 rows (삭제 확인)
```

---

### Test Case 2: 현재 세션 삭제

**시나리오**:
1. 현재 활성화된 세션 삭제
2. 확인

**예상 결과**:
- ✅ 세션 삭제됨
- ✅ 다른 세션으로 자동 전환 (use-chat-sessions.ts Line 165-171 로직)
- ✅ 세션이 없으면 `currentSessionId = null`

---

### Test Case 3: 마지막 세션 삭제

**시나리오**:
1. 세션이 1개만 있는 상태에서 삭제

**예상 결과**:
- ✅ 세션 삭제됨
- ✅ "세션이 없습니다. 새 채팅을 시작하세요." 메시지 표시
- ✅ `currentSessionId = null`

---

### Test Case 4: Cascade 삭제 확인

**시나리오**:
1. 메시지가 있는 세션 삭제

**예상 결과**:
- ✅ 세션 삭제됨
- ✅ 관련 메시지도 자동 삭제 (CASCADE)
- ✅ Checkpoints도 삭제 (Backend Line 481-493)

**검증 SQL**:
```sql
-- 세션 확인
SELECT * FROM chat_sessions WHERE session_id = '{삭제된 session_id}';
-- 결과: 0 rows

-- 메시지 확인 (CASCADE 동작)
SELECT * FROM chat_messages WHERE session_id = '{삭제된 session_id}';
-- 결과: 0 rows

-- Checkpoints 확인
SELECT * FROM checkpoints WHERE session_id = '{삭제된 session_id}';
-- 결과: 0 rows
```

---

## 보안 및 고려사항 (Security & Considerations)

### 1. PostgreSQL 권한

**확인 사항**:
- ✅ Backend DB User가 `DELETE` 권한 보유하는지 확인
- ✅ `CASCADE` 설정이 올바른지 확인

**검증 명령**:
```sql
-- 권한 확인
SELECT grantee, privilege_type
FROM information_schema.table_privileges
WHERE table_name = 'chat_sessions';

-- CASCADE 확인
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON tc.constraint_name = rc.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON rc.constraint_name = ccu.constraint_name
WHERE tc.table_name = 'chat_messages'
  AND tc.constraint_type = 'FOREIGN KEY';
```

---

### 2. 복구 불가능 경고

**현재 상태**:
- ✅ `window.confirm()` 다이얼로그로 확인 (Line 133)

**개선 방안** (추후):
```tsx
// 더 명확한 경고 메시지
if (window.confirm(
  `"${session.title}" 세션을 영구적으로 삭제하시겠습니까?\n\n` +
  `⚠️ 이 작업은 되돌릴 수 없으며, 모든 메시지가 삭제됩니다.`
)) {
  onSessionDelete(session.id)
}
```

---

### 3. 향후 개선 사항

**Option A: 휴지통 기능**
- Soft Delete된 세션을 별도 "휴지통" 탭에 표시
- 30일 후 자동 Hard Delete
- 복구 기능 제공

**Option B: Archive 기능**
- 삭제 대신 "보관" 기능
- 보관함에서 복원 가능
- DB에는 `is_archived` 플래그로 관리

---

## 코드 변경 요약 (Code Changes Summary)

| 파일 | 변경 내용 | 변경 줄 수 |
|------|----------|-----------|
| `frontend/hooks/use-chat-sessions.ts` | `hardDelete` 파라미터 제거, `hard_delete=true` 고정 | -1, +0 (수정) |
| **총합** | | **1줄 수정** |

---

## 위험도 평가 (Risk Assessment)

### 🟢 Low Risk

**이유**:
1. ✅ 변경 범위가 매우 작음 (1줄)
2. ✅ Backend 로직 수정 없음
3. ✅ 기존 Soft Delete 기능 보존
4. ✅ 사용자 확인 다이얼로그 있음
5. ✅ TypeScript 타입 오류 없음

**주의사항**:
- ⚠️ 한번 삭제하면 복구 불가
- ⚠️ 기존 `[삭제됨]` 세션은 수동 정리 필요 (SQL)

---

## 실행 순서 (Implementation Order)

### Phase 1: 코드 수정 (5분)
1. ✅ `use-chat-sessions.ts` 수정
2. ✅ 테스트 (Local)

### Phase 2: 기존 데이터 정리 (5분)
1. ✅ PostgreSQL에서 `[삭제됨]` 세션 삭제
   ```sql
   DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%';
   ```

### Phase 3: 통합 테스트 (10분)
1. ✅ Test Case 1-4 실행
2. ✅ PostgreSQL에서 삭제 확인
3. ✅ CASCADE 동작 확인

---

## 예상 효과 (Expected Benefits)

### Before (현재)
- ❌ 삭제 버튼 눌러도 `[삭제됨]`만 표시
- ❌ 새로고침하면 다시 나타남
- ❌ DB에 쓰레기 데이터 누적
- ❌ 무한 중첩 가능

### After (수정 후)
- ✅ 삭제 버튼 누르면 즉시 사라짐
- ✅ 새로고침해도 사라진 상태 유지
- ✅ PostgreSQL에서 완전 삭제
- ✅ DB 깔끔하게 유지

---

## 결론 (Conclusion)

### 근본 원인
- Backend의 `hard_delete=false` 기본값
- Frontend에서 `hard_delete=true` 전달 안 함
- 결과: Soft Delete 실행 → 제목만 `[삭제됨]`으로 변경

### 해결 방법
- ✅ **Frontend에서 `hard_delete=true`로 고정**
- ✅ 1줄 수정으로 해결
- ✅ Backend 수정 불필요
- ✅ 위험도 낮음

### 다음 단계
1. `use-chat-sessions.ts` 수정
2. 기존 `[삭제됨]` 세션 SQL로 정리
3. 테스트 실행
4. 완료 ✅

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0
**예상 작업 시간**: 20분
