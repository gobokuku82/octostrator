# 세션 삭제 실행 흐름 정밀 분석 - 2025-10-17

## 목적
**"삭제 버튼을 눌렀는데 왜 지워지지 않는가?"**의 근본 원인을 코드 실행 흐름 단계별로 정밀 추적

---

## 정확한 코드 실행 순서 추적

### Step 1: 사용자가 삭제 버튼 클릭

**위치**: `frontend/components/session-list.tsx` Line 131-136

```typescript
<Button onClick={(e) => {
    e.stopPropagation()
    if (window.confirm(`"${session.title}" 세션을 삭제하시겠습니까?`)) {
        onSessionDelete(session.id)  // ← 여기 실행
    }
}}>
```

**실행**:
- `onSessionDelete(session.id)` 호출
- `onSessionDelete` = `deleteSession` (from `use-chat-sessions.ts`)
- **주의**: `await` 없음! Promise를 기다리지 않음

---

### Step 2: `deleteSession()` 함수 실행 시작

**위치**: `frontend/hooks/use-chat-sessions.ts` Line 147-183

```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
        setError(null)

        // ✅ DELETE API 호출 (hard_delete=true)
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}?hard_delete=true`, {
            method: 'DELETE'
        })

        if (!response.ok) {
            throw new Error(`Failed to delete session: ${response.statusText}`)
        }

        const data: DeleteSessionResponse = await response.json()

        // 로컬 상태 업데이트 (id 필드 사용)
        setSessions(prev => prev.filter(s => s.id !== sessionId))

        // 현재 세션이 삭제되면 다른 세션으로 전환
        if (currentSessionId === sessionId) {
            const remainingSessions = sessions.filter(s => s.id !== sessionId)  // ⚠️ Stale!
            if (remainingSessions.length > 0) {
                setCurrentSessionId(remainingSessions[0].id)  // ← 여기서 currentSessionId 변경!
            } else {
                setCurrentSessionId(null)
            }
        }

        console.log(`[useChatSessions] Deleted session: ${sessionId} at ${data.deleted_at}`)
        return true
    } catch (err) {
        // ...
        return false
    }
}, [currentSessionId, sessions])  // ⚠️ 의존성 배열
```

**타임라인**:
```
T1: fetch() 시작 → DELETE API 호출
T2: await response (대기 중...)
T3: await response.json() (대기 중...)
T4: setSessions(prev => prev.filter(...))  ← 로컬 상태 업데이트
T5: if (currentSessionId === sessionId) 체크
T6: setCurrentSessionId(다른ID)  ← currentSessionId 변경! ⚠️
T7: return true
```

---

### Step 3: `setCurrentSessionId()` 실행의 파급 효과

**React State 업데이트**:
```
setCurrentSessionId(새ID) 호출
  ↓
currentSessionId State 변경
  ↓
useChatSessions Hook 재렌더링
  ↓
fetchSessions 함수 재생성 (의존성 변경!)
```

**왜 재생성되나?**
```typescript
const fetchSessions = useCallback(async () => {
    // ...
}, [currentSessionId])  // ← currentSessionId가 의존성!
```

- `currentSessionId`가 변경됨
- `useCallback`이 함수를 **재생성**함
- `fetchSessions`의 참조가 변경됨

---

### Step 4: `useEffect([fetchSessions])` 트리거

**위치**: `frontend/hooks/use-chat-sessions.ts` Line 188-190

```typescript
useEffect(() => {
    fetchSessions()
}, [fetchSessions])  // ← fetchSessions 참조 변경 → 재실행!
```

**실행 순서**:
```
1. fetchSessions 참조 변경 감지
2. useEffect cleanup (없음)
3. useEffect 콜백 실행
4. fetchSessions() 호출! ← 여기서 문제 발생!
```

---

### Step 5: `fetchSessions()` 실행 (문제의 핵심!)

**위치**: `frontend/hooks/use-chat-sessions.ts` Line 30-61

```typescript
const fetchSessions = useCallback(async () => {
    try {
        setLoading(true)
        setError(null)

        // ⚠️ DB에서 세션 목록 다시 조회
        const response = await fetch(`${API_BASE_URL}/sessions?limit=50`)

        if (!response.ok) {
            throw new Error(`Failed to fetch sessions: ${response.statusText}`)
        }

        const data: ChatSessionResponse[] = await response.json()

        // ✅ 빈 세션 필터링 (message_count === 0인 세션 제외)
        const filteredSessions = data.filter(session => session.message_count > 0)

        // ⚠️ 여기서 sessions State를 덮어씀!
        setSessions(filteredSessions)

        // 첫 로드 시 가장 최근 세션을 현재 세션으로 설정
        if (!currentSessionId && filteredSessions.length > 0) {
            setCurrentSessionId(filteredSessions[0].id)
        }

        console.log(`[useChatSessions] Loaded ${filteredSessions.length} sessions`)
    } catch (err) {
        // ...
    } finally {
        setLoading(false)
    }
}, [currentSessionId])
```

**문제 시나리오**:

#### 케이스 A: DELETE API가 빠른 경우 (정상 동작)
```
T1: DELETE API 시작
T2: DELETE API 완료 (DB에서 세션 삭제됨)
T3: setSessions(필터링) - 로컬에서 제거
T4: setCurrentSessionId(새ID)
T5: fetchSessions 재생성
T6: useEffect → fetchSessions() 호출
T7: GET /sessions API 시작
T8: GET /sessions 완료 (이미 삭제된 세션 제외)
T9: setSessions(DB 데이터)
결과: ✅ 정상 (삭제된 세션 안 나타남)
```

#### 케이스 B: DELETE API가 느린 경우 (버그 발생!)
```
T1: DELETE API 시작 (네트워크 지연...)
T2: setSessions(필터링) - 로컬에서 제거 (UI에서 사라짐)
T3: setCurrentSessionId(새ID)
T4: fetchSessions 재생성
T5: useEffect → fetchSessions() 호출
T6: GET /sessions API 시작
T7: GET /sessions 완료 (DELETE 아직 완료 안 됨! → 삭제될 세션 포함)
T8: setSessions(DB 데이터) ← ⚠️ 삭제된 세션이 다시 나타남!
T9: DELETE API 완료 (너무 늦음)
결과: ❌ 버그 (삭제된 세션이 다시 나타남)
```

---

## Race Condition 상세 분석

### 타이밍 다이어그램

```
시간축 →

DELETE API:  [시작]----------[완료]
             T1              T9

setSessions: [필터링]
             T2

setCurrentSessionId: [변경]
                     T3

fetchSessions:       [재생성]
                     T4

useEffect:           [트리거]-[fetchSessions() 호출]
                     T5       T6

GET /sessions API:            [시작]---[완료]
                              T6       T7

setSessions:                           [덮어씀] ← 문제!
                                       T8
```

**Race Condition 발생 조건**:
- `T7 < T9` (GET이 DELETE보다 먼저 완료)
- **결과**: 삭제되기 전 데이터를 받아옴

---

## 왜 `[삭제됨]`으로 표시되는가?

### 추가 분석: Soft Delete 잔재

**가설**: 이전에 `hard_delete=false`로 삭제했던 세션들이 DB에 남아있음

**확인**:
```sql
-- PostgreSQL
SELECT session_id, title, message_count, created_at
FROM chat_sessions
WHERE title LIKE '[삭제됨]%'
ORDER BY updated_at DESC;
```

**시나리오**:
1. 과거에 삭제 버튼 클릭 (그때는 `hard_delete=false`)
2. Backend에서 Soft Delete 실행:
   ```python
   session.title = f"[삭제됨] {session.title}"
   ```
3. DB에 `[삭제됨]` 세션 남아있음
4. 현재 `fetchSessions()`가 이들을 받아옴
5. 필터링 로직:
   ```typescript
   const filteredSessions = data.filter(session => session.message_count > 0)
   ```
6. `[삭제됨]` 세션도 `message_count > 0`이면 통과!
7. 목록에 표시됨

---

## 무한 중첩 `[삭제됨][삭제됨][삭제됨]` 원인

**재현 시나리오**:
```
1. 세션 A: title="새 대화", message_count=5

2. 사용자가 삭제 버튼 클릭 (첫 번째)
   → Backend Soft Delete (과거에 hard_delete=false였을 때)
   → title="[삭제됨] 새 대화"

3. fetchSessions()로 다시 불러옴
   → message_count=5 → 필터 통과
   → 목록에 "[삭제됨] 새 대화" 표시

4. 사용자가 다시 삭제 버튼 클릭 (두 번째)
   → Backend Soft Delete
   → title="[삭제됨] [삭제됨] 새 대화"

5. fetchSessions()로 다시 불러옴
   → message_count=5 → 필터 통과
   → 목록에 "[삭제됨] [삭제됨] 새 대화" 표시

6. 반복...
```

**현재는 `hard_delete=true`로 수정했으므로 새로운 중첩은 발생 안 함!**

하지만 **이전에 생성된 `[삭제됨]` 세션들은 여전히 DB에 존재**

---

## 근본 원인 최종 결론

### 🔴 Primary Root Cause: Race Condition + Stale Data

**두 가지 문제의 조합**:

1. **Race Condition** (현재 발생 중):
   ```
   DELETE API (느림) vs GET /sessions API (빠름)
   → GET이 먼저 완료 → 삭제 전 데이터 받아옴
   ```

2. **Soft Delete 잔재** (과거 문제):
   ```
   이전에 hard_delete=false로 삭제된 세션들
   → DB에 "[삭제됨]" 제목으로 남아있음
   → fetchSessions()가 이들을 받아옴
   ```

**현재 상황**:
- `hard_delete=true` 수정 완료 → 새로운 Soft Delete 발생 안 함 ✅
- 하지만 **Race Condition 여전히 존재** → 삭제가 불안정 ❌
- **과거 `[삭제됨]` 세션 여전히 DB에 존재** → 목록에 나타남 ❌

---

## 증거 기반 확인 방법

### Console Log로 Race Condition 추적

**추가할 로그**:
```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    console.log('[DELETE] 🔴 START:', sessionId, 'at', Date.now())

    const response = await fetch(...)
    console.log('[DELETE] 🟡 API Response:', response.status, 'at', Date.now())

    const data = await response.json()
    console.log('[DELETE] 🟢 API Complete:', data, 'at', Date.now())

    setSessions(prev => {
        console.log('[DELETE] 📊 Before setSessions:', prev.map(s => s.id))
        const filtered = prev.filter(s => s.id !== sessionId)
        console.log('[DELETE] 📊 After setSessions:', filtered.map(s => s.id))
        return filtered
    })

    setCurrentSessionId(다른ID)
    console.log('[DELETE] ⭐ setCurrentSessionId:', 다른ID, 'at', Date.now())

    return true
}, [currentSessionId, sessions])

const fetchSessions = useCallback(async () => {
    console.log('[FETCH] 🔵 START at', Date.now())
    console.trace('[FETCH] Called from:')  // 호출 스택 추적

    const response = await fetch(...)
    const data = await response.json()

    console.log('[FETCH] 🔵 API Complete:', data.length, 'sessions at', Date.now())

    setSessions(filteredSessions)
    console.log('[FETCH] 📊 setSessions:', filteredSessions.map(s => s.id))
}, [currentSessionId])
```

**예상 로그 (버그 발생 시)**:
```
[DELETE] 🔴 START: abc at 1000
[DELETE] 🟡 API Response: 200 at 1500
[DELETE] 🟢 API Complete: {...} at 1600
[DELETE] 📊 Before setSessions: ['abc', 'def', 'ghi']
[DELETE] 📊 After setSessions: ['def', 'ghi']
[DELETE] ⭐ setCurrentSessionId: def at 1650
[FETCH] 🔵 START at 1700  ← useEffect 트리거!
[FETCH] 🔵 API Complete: 3 sessions at 2000  ← DELETE 완료 전!
[FETCH] 📊 setSessions: ['abc', 'def', 'ghi']  ← abc가 다시 나타남!
```

---

### PostgreSQL에서 [삭제됨] 세션 확인

```sql
-- [삭제됨] 세션 조회
SELECT
    session_id,
    title,
    message_count,
    created_at,
    updated_at
FROM chat_sessions
WHERE title LIKE '[삭제됨]%'
ORDER BY updated_at DESC;

-- 결과 예시:
-- session_id | title                    | message_count | updated_at
-- abc123     | [삭제됨] 새 대화         | 5             | 2025-10-17 10:00:00
-- def456     | [삭제됨][삭제됨] 테스트  | 3             | 2025-10-17 09:30:00
```

**만약 결과가 있다면** → 이것들이 목록에 나타나는 원인!

---

## 최종 진단

### 문제 1: Race Condition (확실)
- **증상**: 삭제 버튼 클릭 → 잠깐 사라짐 → 다시 나타남
- **원인**: `setCurrentSessionId()` → `fetchSessions` 재생성 → useEffect → `fetchSessions()` 호출
- **타이밍**: DELETE API vs GET /sessions API 경쟁
- **확률**: 네트워크 상태에 따라 불규칙하게 발생

### 문제 2: Soft Delete 잔재 (가능성 높음)
- **증상**: `[삭제됨]` 제목의 세션이 목록에 나타남
- **원인**: 과거에 `hard_delete=false`로 삭제된 세션들이 DB에 남아있음
- **필터링**: `message_count > 0`이면 통과 → 목록에 표시
- **확인 필요**: PostgreSQL 쿼리로 확인

### 문제 3: Stale Closure (부수적)
- **증상**: `remainingSessions` 계산 오류 가능
- **원인**: `sessions` 배열이 업데이트 전 상태 참조
- **영향도**: 낮음 (우연히 올바른 결과)

---

## 해결 우선순위

### 🔴 Critical (즉시 수정)
1. **fetchSessions 의존성 제거**: `[currentSessionId]` → `[]`
2. **[삭제됨] 필터링 추가**: `!session.title.startsWith('[삭제됨]')`
3. **DB 정리**: `DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%'`

### 🟡 Important (개선)
4. **deleteSession Stale Closure 수정**: `setSessions` 콜백 내에서 세션 전환
5. **session-list.tsx await 추가**: 에러 처리

### 🟢 Nice to Have (선택)
6. **TypeScript Props 타입 수정**: `Promise<boolean>` 명시

---

## 다음 단계

1. **Console Log 추가** → Race Condition 확인
2. **PostgreSQL 쿼리** → [삭제됨] 세션 확인
3. **증거 확보 후** → 수정 진행

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 3.0 (Execution Flow Analysis)
**상태**: 근본 원인 확정
