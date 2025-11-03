# 🚨 세션 삭제 치명적 버그 분석 - 2025-10-17

## 진짜 문제 발견! 3개의 치명적 버그

---

## Bug 1: `fetchSessions`의 `currentSessionId` 의존성 ⚠️⚠️⚠️

### 코드 위치
**파일**: `frontend/hooks/use-chat-sessions.ts` Line 30-61

```typescript
const fetchSessions = useCallback(async () => {
    // ... 세션 목록 조회 ...
}, [currentSessionId])  // ❌ currentSessionId 의존성
```

### 문제점

**무한 루프 가능성**:
```
1. deleteSession() 호출
   ↓
2. setCurrentSessionId() 실행 (다른 세션으로 전환)
   ↓
3. currentSessionId 변경
   ↓
4. fetchSessions 재생성 (의존성 변경)
   ↓
5. useEffect 재실행 (Line 161-163)
   ↓
6. fetchSessions() 호출
   ↓
7. DB에서 세션 목록 다시 가져옴
   ↓
8. setSessions() 호출
   ↓
9. 삭제한 세션이 다시 나타날 수 있음!
```

### Race Condition 시나리오

**타임라인**:
```
T1: DELETE API 시작 (http://localhost:8000/api/v1/chat/sessions/abc?hard_delete=true)
T2: setSessions(prev => prev.filter(...))  // 로컬에서 제거
T3: setCurrentSessionId(다른세션ID)  // currentSessionId 변경
T4: fetchSessions 재생성 (의존성 변경)
T5: useEffect → fetchSessions() 호출
T6: GET /sessions API 시작
T7: GET /sessions 완료 (아직 DELETE 완료 안 됨! → 삭제 전 세션 포함)
T8: setSessions(data)  // ❌ 삭제된 세션이 다시 나타남!
T9: DELETE API 완료 (너무 늦음)
```

**결과**: 삭제 버튼 누름 → 잠깐 사라짐 → 다시 나타남 ❌

---

## Bug 2: `deleteSession`의 Stale Closure ⚠️⚠️

### 코드 위치
**파일**: `frontend/hooks/use-chat-sessions.ts` Line 139-145

```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    // ...

    // 현재 세션이 삭제되면 다른 세션으로 전환
    if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId)  // ❌ 문제!
        if (remainingSessions.length > 0) {
            setCurrentSessionId(remainingSessions[0].id)
        } else {
            setCurrentSessionId(null)
        }
    }

    return true
}, [currentSessionId, sessions])  // ❌ sessions 의존성
```

### 문제점

**Stale Closure**:
- `sessions` 배열은 **이전 상태**를 참조
- `setSessions(prev => prev.filter(...))`는 **즉시 반영되지 않음**
- `const remainingSessions = sessions.filter(...)`는 **오래된 sessions 사용**

**시나리오**:
```typescript
// 현재 sessions = [A, B, C]
// currentSessionId = A

// 사용자가 A 삭제
deleteSession('A')
  ↓
setSessions(prev => prev.filter(s => s.id !== 'A'))  // [B, C]로 업데이트
  ↓
const remainingSessions = sessions.filter(s => s.id !== 'A')
// ❌ sessions는 여전히 [A, B, C] (오래된 상태)
// remainingSessions = [B, C] (우연히 맞음)
  ↓
setCurrentSessionId(remainingSessions[0].id)  // B로 전환
```

**문제**:
- 우연히 동작하는 것처럼 보이지만
- `sessions` state 업데이트 타이밍에 따라 버그 발생 가능
- **의존성 배열에 `sessions`가 있어서 매번 재생성됨** → 성능 저하

---

## Bug 3: `session-list.tsx`의 async/await 누락 ⚠️

### 코드 위치
**파일**: `frontend/components/session-list.tsx` Line 131-136

```typescript
<Button
  onClick={(e) => {
    e.stopPropagation()
    if (window.confirm(`"${session.title}" 세션을 삭제하시겠습니까?`)) {
      onSessionDelete(session.id)  // ❌ await 없음!
    }
  }}
>
```

### 문제점

**Promise를 기다리지 않음**:
```typescript
// onSessionDelete = deleteSession (async 함수)
// deleteSession은 Promise<boolean>을 반환

onSessionDelete(session.id)  // ❌ Promise를 무시
// 실패해도 모름
// 성공해도 확인 못 함
```

**결과**:
- 삭제 실패해도 에러 표시 안 됨
- 로딩 상태 없음
- 사용자는 삭제되는지 모름

---

## Bug 4: TypeScript 타입 불일치 (발견됨)

### session-list.tsx Props

```typescript
interface SessionListProps {
  onSessionDelete: (sessionId: string) => void  // ❌ void 반환
}
```

### use-chat-sessions.ts 실제 타입

```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    // ...
}, [currentSessionId, sessions])

// 반환 타입: Promise<boolean>
```

### 문제점

**타입 불일치**:
- `onSessionDelete`는 `void` 반환 기대
- `deleteSession`은 `Promise<boolean>` 반환
- TypeScript가 경고해야 하지만 **`void`는 모든 것을 받아들임**

**수정 필요**:
```typescript
interface SessionListProps {
  onSessionDelete: (sessionId: string) => Promise<void> | void  // ✅ async 지원
}
```

---

## 근본 원인 정리

### 🔴 Primary Root Cause

**`fetchSessions`의 `currentSessionId` 의존성**이 모든 문제의 근원입니다!

1. **의존성 변경** → fetchSessions 재생성
2. **useEffect 재실행** → fetchSessions() 호출
3. **Race Condition** → DELETE 전 데이터 받아옴
4. **삭제된 세션 다시 나타남**

---

## 완벽한 해결 방법

### Fix 1: `fetchSessions` 의존성 제거 ⭐⭐⭐

```typescript
const fetchSessions = useCallback(async () => {
    try {
        setLoading(true)
        setError(null)

        const response = await fetch(`${API_BASE_URL}/sessions?limit=50`)

        if (!response.ok) {
            throw new Error(`Failed to fetch sessions: ${response.statusText}`)
        }

        const data: ChatSessionResponse[] = await response.json()

        // ✅ [삭제됨] 세션 필터링 추가
        const filteredSessions = data.filter(session =>
            session.message_count > 0 &&
            !session.title.startsWith('[삭제됨]')
        )
        setSessions(filteredSessions)

        // ✅ currentSessionId를 의존성에서 제거
        // 첫 로드 시에만 세션 설정 (다른 곳에서 관리)
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(message)
        console.error('[useChatSessions] Failed to fetch sessions:', err)
    } finally {
        setLoading(false)
    }
}, [])  // ✅ 빈 의존성 배열
```

---

### Fix 2: `deleteSession` Stale Closure 해결 ⭐⭐⭐

```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
        setError(null)

        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}?hard_delete=true`, {
            method: 'DELETE'
        })

        if (!response.ok) {
            throw new Error(`Failed to delete session: ${response.statusText}`)
        }

        const data: DeleteSessionResponse = await response.json()

        // ✅ setSessions 콜백 내에서 세션 전환 처리
        setSessions(prev => {
            const filteredSessions = prev.filter(s => s.id !== sessionId)

            // ✅ 현재 세션이 삭제되면 다른 세션으로 전환
            if (currentSessionId === sessionId) {
                if (filteredSessions.length > 0) {
                    setCurrentSessionId(filteredSessions[0].id)
                } else {
                    setCurrentSessionId(null)
                }
            }

            return filteredSessions
        })

        console.log(`[useChatSessions] Deleted session: ${sessionId} at ${data.deleted_at}`)
        return true
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(message)
        console.error('[useChatSessions] Failed to delete session:', err)
        return false
    }
}, [currentSessionId])  // ✅ sessions 의존성 제거
```

---

### Fix 3: `session-list.tsx` async 처리 ⭐⭐

```typescript
<Button
  onClick={async (e) => {  // ✅ async 추가
    e.stopPropagation()
    if (window.confirm(`"${session.title}" 세션을 삭제하시겠습니까?`)) {
      const success = await onSessionDelete(session.id)  // ✅ await 추가
      if (!success) {
        alert('세션 삭제에 실패했습니다.')
      }
    }
  }}
>
  <Trash2 className="h-3 w-3 text-destructive" />
</Button>
```

---

### Fix 4: TypeScript Props 타입 수정 ⭐

```typescript
interface SessionListProps {
  sessions: SessionListItem[]
  currentSessionId: string | null
  onSessionClick: (sessionId: string) => void
  onSessionDelete: (sessionId: string) => Promise<boolean>  // ✅ Promise<boolean>
  isCollapsed?: boolean
}
```

---

### Fix 5: 초기 세션 설정 로직 개선 ⭐

```typescript
// fetchSessions에서 currentSessionId 설정을 제거했으므로
// useEffect로 분리
useEffect(() => {
    fetchSessions()
}, [])  // ✅ 한 번만 실행

// 첫 로드 시 세션 설정
useEffect(() => {
    if (!currentSessionId && sessions.length > 0) {
        setCurrentSessionId(sessions[0].id)
    }
}, [sessions, currentSessionId])
```

---

## 추가 개선: DB 정리

### SQL로 [삭제됨] 세션 제거

```bash
# Git Bash
PGPASSWORD=root1234 psql -U postgres -d real_estate -c "DELETE FROM chat_sessions WHERE title LIKE '[삭제됨]%';"
```

---

## 테스트 시나리오

### Test 1: 단일 세션 삭제
1. 세션 3개 (A, B, C) 있는 상태
2. 현재 세션 A
3. A 삭제
4. **예상**: 즉시 사라짐, B로 전환
5. **확인**: `fetchSessions()` 재호출 안 됨

### Test 2: F5 새로고침
1. 세션 삭제
2. F5 새로고침
3. **예상**: 삭제된 세션 안 나타남
4. **확인**: DB에서 세션 사라짐

### Test 3: 연속 삭제
1. A, B, C 순서로 빠르게 삭제
2. **예상**: 모두 즉시 사라짐
3. **확인**: Race Condition 없음

### Test 4: 마지막 세션 삭제
1. 세션 1개만 있을 때 삭제
2. **예상**: "세션이 없습니다" 메시지
3. **확인**: `currentSessionId = null`

---

## Console Log로 디버깅

### fetchSessions 호출 추적

```typescript
const fetchSessions = useCallback(async () => {
    console.log('[FETCH] fetchSessions called')
    console.trace('[FETCH] Call stack')  // ✅ 호출 위치 추적

    // ...
}, [])
```

### deleteSession 실행 추적

```typescript
const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    console.log('[DELETE] Starting:', sessionId)
    console.log('[DELETE] Current sessions:', sessions.map(s => s.id))

    const response = await fetch(...)
    console.log('[DELETE] API response:', response.status)

    setSessions(prev => {
        console.log('[DELETE] Before:', prev.map(s => s.id))
        const filtered = prev.filter(s => s.id !== sessionId)
        console.log('[DELETE] After:', filtered.map(s => s.id))
        return filtered
    })

    console.log('[DELETE] Complete')
    return true
}, [currentSessionId])
```

---

## 왜 지금까지 발견 못 했나?

### 1. TypeScript의 허점
- `void` 반환 타입은 모든 것을 받아들임
- `Promise<boolean>`을 `void`에 할당해도 에러 없음
- **타입 안전성 무시됨**

### 2. Race Condition의 타이밍
- DELETE API와 GET /sessions API의 타이밍 차이
- 대부분의 경우 DELETE가 먼저 완료됨
- **가끔 GET이 먼저 완료** → 버그 발생
- **일관성 없는 재현** → 디버깅 어려움

### 3. Stale Closure의 우연한 동작
- `sessions` 배열이 오래되었지만
- 우연히 올바른 결과 반환
- **겉보기엔 정상** → 실제론 버그

---

## 최종 수정 체크리스트

### Phase 1: 긴급 수정 (10분)
- [ ] `fetchSessions` 의존성 배열 `[]`로 변경
- [ ] `[삭제됨]` 세션 필터링 추가
- [ ] DB에서 `[삭제됨]` 세션 삭제

### Phase 2: 근본 수정 (15분)
- [ ] `deleteSession` Stale Closure 해결
- [ ] `session-list.tsx` async/await 추가
- [ ] TypeScript Props 타입 수정
- [ ] 초기 세션 설정 로직 분리

### Phase 3: 테스트 (10분)
- [ ] Test 1-4 실행
- [ ] Console Log 확인
- [ ] Race Condition 재현 안 됨 확인

---

## 예상 효과

### Before (현재)
- ❌ 삭제 버튼 → 잠깐 사라짐 → 다시 나타남
- ❌ Race Condition 발생
- ❌ Stale Closure 버그
- ❌ 에러 처리 없음

### After (수정 후)
- ✅ 삭제 버튼 → 즉시 사라짐 (영구)
- ✅ Race Condition 해결
- ✅ Stale Closure 해결
- ✅ 에러 처리 추가
- ✅ TypeScript 타입 안전성 확보

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 2.0 (Critical Bug Analysis)
**심각도**: 🚨 Critical
