# Session 삭제 버그 상세 분석 리포트 - 2025-10-17

## 🚨 핵심 문제 발견

### **중복된 DELETE 엔드포인트**가 문제의 근본 원인입니다!

---

## 문제 상세 분석

### 1. Backend에 DELETE 엔드포인트가 **2개** 존재

#### Endpoint 1: `/api/v1/chat/sessions/{session_id}` (Line 238-308)
```python
@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    hard_delete: bool = False,  # ✅ hard_delete 파라미터 지원
    db: AsyncSession = Depends(get_async_db)
):
    """Chat History & State Endpoints - DB 영속성 삭제"""
    if hard_delete:
        await db.delete(session)  # ✅ 하드 삭제
    else:
        session.title = f"[삭제됨] {session.title}"  # ❌ 소프트 삭제
```

**특징**:
- ✅ `hard_delete` 파라미터 지원
- ✅ PostgreSQL `chat_sessions` 테이블에서 삭제
- ✅ CASCADE로 `chat_messages`도 삭제
- ✅ Checkpoints 테이블도 정리

---

#### Endpoint 2: `/api/v1/chat/{session_id}` (Line 341-372)
```python
@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """Redis Session Manager - 인메모리 세션 삭제"""
    success = await session_mgr.delete_session(session_id)
    conn_mgr.cleanup_session(session_id)
```

**특징**:
- ❌ `hard_delete` 파라미터 **없음**
- ❌ PostgreSQL 테이블 건드리지 않음
- ✅ Redis 인메모리 세션만 삭제
- ✅ WebSocket 연결 정리

---

### 2. 라우팅 우선순위 문제

**FastAPI Route Matching 순서**:
```
1. `/api/v1/chat/sessions/{session_id}` (구체적)
2. `/api/v1/chat/{session_id}` (일반적)
```

**실제 호출 URL**:
```
DELETE http://localhost:8000/api/v1/chat/sessions/{session_id}?hard_delete=true
```

**매칭 결과**:
- ✅ **Endpoint 1과 매칭됨** (정확한 경로)
- ✅ `hard_delete=true` 파라미터 정상 전달
- ✅ PostgreSQL에서 삭제 실행

**결론**: 라우팅은 **정상 동작**하고 있습니다!

---

### 3. 실제 문제의 원인

#### 가설 1: Frontend에서 삭제 후 목록을 다시 fetch하는 경우 ❌

**코드 분석** (`use-chat-sessions.ts`):
```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}?hard_delete=true`, {
        method: 'DELETE'
    })

    // ✅ 로컬 상태에서 즉시 제거
    setSessions(prev => prev.filter(s => s.id !== sessionId))

    return true
}, [currentSessionId, sessions])
```

**분석**:
- ✅ 로컬 상태는 즉시 업데이트됨
- ✅ `fetchSessions()`를 다시 호출하지 않음
- ✅ UI에서 즉시 사라져야 함

**가설 1 결론**: 이것이 원인이 아님

---

#### 가설 2: useEffect가 fetchSessions를 재호출하는 경우 🎯

**코드 분석** (`use-chat-sessions.ts` Line 187-189):
```typescript
useEffect(() => {
    fetchSessions()
}, [fetchSessions])
```

**문제 분석**:
```typescript
const fetchSessions = useCallback(async () => {
    // ...
}, [currentSessionId])  // ⚠️ currentSessionId 의존성
```

**동작 순서**:
1. 사용자가 세션 A 삭제 버튼 클릭
2. `deleteSession()` 실행
3. API 호출: `DELETE /sessions/A?hard_delete=true`
4. **로컬 상태 업데이트**: `setSessions(prev => prev.filter(...))`
5. **세션 전환 로직 실행** (Line 165-172):
   ```typescript
   if (currentSessionId === sessionId) {
       const remainingSessions = sessions.filter(s => s.id !== sessionId)
       if (remainingSessions.length > 0) {
           setCurrentSessionId(remainingSessions[0].id)  // ⚠️ currentSessionId 변경!
       }
   }
   ```
6. **currentSessionId 변경** → `fetchSessions` 의존성 변경
7. **useEffect 재실행** → `fetchSessions()` 호출!
8. **DB에서 다시 조회** → 삭제된 세션 제외하고 받아옴
9. **기존 로컬 상태 덮어씌움**

**하지만 대기 중...**

**Race Condition 발생 가능**:
```
시간축:
T1: DELETE API 호출 시작
T2: setSessions() 실행 (로컬 상태 업데이트)
T3: setCurrentSessionId() 실행
T4: useEffect 트리거 → fetchSessions() 호출 시작
T5: DELETE API 완료 (DB에서 삭제)
T6: fetchSessions() 완료 (이미 삭제된 세션은 안 옴)

결과: 정상 동작
```

**하지만 만약...**
```
시간축:
T1: DELETE API 호출 시작
T2: setSessions() 실행 (로컬 상태 업데이트)
T3: setCurrentSessionId() 실행
T4: useEffect 트리거 → fetchSessions() 호출 시작
T5: fetchSessions() 완료 (DELETE 아직 완료 안 됨 → 삭제 전 세션 받아옴)
T6: DELETE API 완료 (DB에서 삭제되지만 이미 늦음)

결과: 삭제된 세션이 다시 나타남 ❌
```

**가설 2 결론**: **Race Condition이 원인일 가능성 높음!** 🎯

---

#### 가설 3: Soft Delete된 세션이 DB에 남아있는 경우 🎯

**확인 필요**:
- 이전에 `hard_delete=false`로 삭제했던 세션들이 DB에 남아있음
- 제목이 `[삭제됨]`으로 변경된 채로 존재
- `fetchSessions()`가 이들을 받아옴

**검증 SQL**:
```sql
SELECT session_id, title, message_count, updated_at
FROM chat_sessions
WHERE title LIKE '[삭제됨]%'
ORDER BY updated_at DESC;
```

---

### 4. 빈 세션 필터링 로직 확인

**코드** (`use-chat-sessions.ts` Line 44-46):
```typescript
// ✅ 빈 세션 필터링 (message_count === 0인 세션 제외)
const filteredSessions = data.filter(session => session.message_count > 0)
setSessions(filteredSessions)
```

**분석**:
- ✅ `message_count === 0`인 세션은 필터링됨
- ❌ `[삭제됨]` 세션은 메시지가 있으면 필터링 안 됨

**예시**:
```
세션 A: title="[삭제됨] 새 대화", message_count=5
→ 필터링 안 됨 → 목록에 표시됨 ❌
```

---

## 근본 원인 정리

### 🔴 Primary Issue: Race Condition + Stale Data

1. **Race Condition** (가설 2):
   - `deleteSession()` 실행
   - `setCurrentSessionId()` → `fetchSessions()` 재호출
   - `fetchSessions()`가 DELETE API보다 먼저 완료
   - 삭제되기 전 데이터를 받아옴

2. **Soft Delete 잔재** (가설 3):
   - 이전에 `hard_delete=false`로 삭제된 세션들이 DB에 남아있음
   - `[삭제됨]` 제목으로 변경되었지만 `message_count > 0`
   - 빈 세션 필터에 걸리지 않음

---

## 해결 방안

### Solution 1: deleteSession() 후 fetchSessions() 재호출 방지 ⭐

**문제**:
- `currentSessionId` 변경 → `fetchSessions` 재생성 → useEffect 재실행

**해결**:
- `fetchSessions`의 의존성에서 `currentSessionId` 제거
- 또는 `deleteSession` 성공 후 명시적으로 세션 전환

**수정**:
```typescript
const fetchSessions = useCallback(async () => {
    // ...
    const filteredSessions = data.filter(session => session.message_count > 0)
    setSessions(filteredSessions)

    // ✅ currentSessionId 의존성 제거
}, [])  // 빈 의존성 배열

// deleteSession에서 세션 전환
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    // ...
    await db.delete(session)  // API 호출

    // ✅ API 완료 후 로컬 상태 업데이트
    setSessions(prev => prev.filter(s => s.id !== sessionId))

    // ✅ 세션 전환 (fetchSessions 재호출 안 됨)
    if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId)
        setCurrentSessionId(remainingSessions[0]?.id || null)
    }

    return true
}, [currentSessionId, sessions])
```

---

### Solution 2: [삭제됨] 세션 필터링 ⭐

**문제**:
- `[삭제됨]` 세션이 `message_count > 0`이면 필터링 안 됨

**해결**:
```typescript
const fetchSessions = useCallback(async () => {
    // ...
    const data: ChatSessionResponse[] = await response.json()

    // ✅ 빈 세션 + [삭제됨] 세션 필터링
    const filteredSessions = data.filter(session =>
        session.message_count > 0 &&
        !session.title.startsWith('[삭제됨]')  // ✅ 추가
    )
    setSessions(filteredSessions)
}, [])
```

---

### Solution 3: 기존 [삭제됨] 세션 DB에서 정리

**SQL 실행**:
```sql
-- PostgreSQL에서 [삭제됨] 세션 완전 삭제
DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%';
```

**Git Bash 명령**:
```bash
PGPASSWORD=root1234 psql -U postgres -d real_estate -c "DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%';"
```

---

### Solution 4: deleteSession 성공 후 await 보장

**문제**:
- API 호출이 완료되기 전에 로컬 상태 업데이트

**해결**:
```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}?hard_delete=true`, {
            method: 'DELETE'
        })

        if (!response.ok) {
            throw new Error(`Failed to delete session: ${response.statusText}`)
        }

        await response.json()  // ✅ 응답 완료 대기

        // ✅ API 완료 후에만 로컬 상태 업데이트
        setSessions(prev => prev.filter(s => s.id !== sessionId))

        // 세션 전환
        if (currentSessionId === sessionId) {
            const remainingSessions = sessions.filter(s => s.id !== sessionId)
            setCurrentSessionId(remainingSessions[0]?.id || null)
        }

        return true
    } catch (err) {
        // ...
        return false
    }
}, [currentSessionId, sessions])
```

---

## 권장 해결 순서

### Phase 1: 긴급 수정 (5분)

1. ✅ **[삭제됨] 세션 필터링 추가**
   ```typescript
   const filteredSessions = data.filter(session =>
       session.message_count > 0 &&
       !session.title.startsWith('[삭제됨]')
   )
   ```

2. ✅ **기존 [삭제됨] 세션 DB 정리**
   ```bash
   PGPASSWORD=root1234 psql -U postgres -d real_estate -c "DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%';"
   ```

---

### Phase 2: 근본 수정 (10분)

3. ✅ **fetchSessions 의존성 배열 수정**
   ```typescript
   const fetchSessions = useCallback(async () => {
       // ...
   }, [])  // currentSessionId 제거
   ```

4. ✅ **deleteSession Race Condition 방지**
   ```typescript
   // await response.json() 추가
   // setSessions() 호출 시점 보장
   ```

---

## 테스트 계획

### Test 1: 삭제 후 목록 확인
1. 세션 삭제
2. **예상**: 즉시 사라짐
3. **확인**: `sessions` state 로그

### Test 2: F5 새로고침
1. 세션 삭제
2. F5 새로고침
3. **예상**: 삭제된 세션 안 나타남
4. **확인**: `/sessions` API 응답

### Test 3: 여러 세션 연속 삭제
1. 세션 A, B, C 삭제
2. **예상**: 모두 사라짐
3. **확인**: Race Condition 발생 안 함

### Test 4: DB 직접 확인
```sql
SELECT * FROM chat_sessions WHERE title LIKE '[삭제됨]%';
-- 예상: 0 rows
```

---

## 추가 디버깅 팁

### Console Log 추가
```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    console.log('[DELETE] Starting deletion:', sessionId)

    const response = await fetch(...)
    console.log('[DELETE] API response:', response.status)

    const data = await response.json()
    console.log('[DELETE] API data:', data)

    setSessions(prev => {
        const filtered = prev.filter(s => s.id !== sessionId)
        console.log('[DELETE] Sessions before:', prev.length)
        console.log('[DELETE] Sessions after:', filtered.length)
        return filtered
    })

    console.log('[DELETE] Deletion complete')
    return true
}, [currentSessionId, sessions])
```

### fetchSessions 호출 추적
```typescript
const fetchSessions = useCallback(async () => {
    console.log('[FETCH] fetchSessions called')
    console.trace('[FETCH] Call stack')  // 호출 위치 추적

    // ...
}, [currentSessionId])
```

---

## 결론

### 문제의 근본 원인
1. **Race Condition**: `deleteSession()` vs `fetchSessions()` 타이밍 이슈
2. **Soft Delete 잔재**: DB에 `[삭제됨]` 세션 남아있음
3. **필터링 부족**: `[삭제됨]` 세션을 필터링하지 않음

### 해결 방법
1. ✅ `[삭제됨]` 세션 필터링 추가
2. ✅ DB에서 기존 `[삭제됨]` 세션 삭제
3. ✅ `fetchSessions` 의존성 배열 수정
4. ✅ `deleteSession` Race Condition 방지

### 예상 효과
- ✅ 삭제 버튼 클릭 시 즉시 사라짐
- ✅ F5 새로고침해도 사라진 상태 유지
- ✅ Race Condition 해결
- ✅ DB 깔끔하게 유지

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0 (상세 디버깅 분석)
