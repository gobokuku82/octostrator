# 무한 루프 해결 및 다음 단계 가이드

**날짜**: 2025-10-16
**작성자**: Claude Code
**상태**: 완료 ✅
**문서 버전**: 1.0
**세션**: ScrollArea 및 useCallback 무한 루프 해결

---

## 📋 목차

1. [완료된 작업](#1-완료된-작업)
2. [현재 시스템 상태](#2-현재-시스템-상태)
3. [남은 작업](#3-남은-작업)
4. [수정된 파일 상세](#4-수정된-파일-상세)
5. [테스트 체크리스트](#5-테스트-체크리스트)
6. [다음 세션 시작 가이드](#6-다음-세션-시작-가이드)

---

## 1. 완료된 작업

### 1.1 ScrollArea 무한 루프 해결 ✅

**문제**:
```
Error: Maximum update depth exceeded
setScrollArea ..\src\scroll-area.tsx (85:66)
```

**원인**:
- Radix UI ScrollArea 컴포넌트의 내부 상태 관리 문제
- 페이지 전환 시 (지도 → 채팅) 무한 재렌더링 발생
- ScrollArea가 매 렌더링마다 부모 컴포넌트를 재렌더링 유발

**해결 방법**:
- ScrollArea를 plain `<div>`로 교체
- CSS `overflow-y-auto` 사용
- 스크롤 자동 이동 로직 단순화

**수정된 파일**: `frontend/components/chat-interface.tsx`

**수정 내용**:

1. **Import 제거** (Line 7)
```typescript
// 제거됨
import { ScrollArea } from "@/components/ui/scroll-area"
```

2. **JSX 변경** (Line 459)
```typescript
// Before
<ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
  <div className="space-y-4 max-w-3xl mx-auto">
    {messages.map((message) => (...))}
  </div>
</ScrollArea>

// After
<div ref={scrollAreaRef} className="flex-1 p-4 overflow-y-auto">
  <div className="space-y-4 max-w-3xl mx-auto">
    {messages.map((message) => (...))}
  </div>
</div>
```

3. **스크롤 로직 단순화** (Line 318-322)
```typescript
// Before: Radix UI 내부 구조 접근
useEffect(() => {
  if (scrollAreaRef.current) {
    const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight
    }
  }
}, [messages])

// After: 직접 DOM 조작
useEffect(() => {
  if (scrollAreaRef.current) {
    scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
  }
}, [messages])
```

**결과**:
- ✅ "Maximum update depth exceeded" 에러 완전 제거
- ✅ 페이지 전환 정상 작동 (지도 ↔ 채팅)
- ✅ 스크롤 자동 이동 정상 작동
- ✅ Git 커밋 완료 (사용자가 직접 커밋)

---

### 1.2 useCallback 무한 루프 해결 ✅

**문제**:
```
Warning: Maximum update depth exceeded
at page.tsx:42
onRegisterMemoryLoader @ page.tsx:42
```

**원인**:
- `page.tsx`에서 `onRegisterMemoryLoader` prop이 매 렌더링마다 새 함수로 생성됨
- `chat-interface.tsx`의 useEffect가 이 prop 변경을 감지하여 무한 실행
- page.tsx 재렌더링 → 새 함수 생성 → useEffect 실행 → setLoadMemory → 재렌더링 → 무한 루프

**해결 방법**:
- `page.tsx`에서 `useCallback`으로 함수 메모이제이션
- `chat-interface.tsx`의 의존성 배열 정확하게 설정

**수정된 파일**:
1. `frontend/app/page.tsx`
2. `frontend/components/chat-interface.tsx`

**수정 내용**:

**page.tsx** (Line 3, 39-41, 46, 56):
```typescript
// 1. useCallback import 추가
import { useState, useCallback } from "react"

// 2. 메모이제이션된 함수 생성
const handleRegisterMemoryLoader = useCallback((loader: (memory: any) => void) => {
  setLoadMemory(() => loader)
}, [])

// 3. JSX에서 사용 (2곳)
<ChatInterface
  onSplitView={handleSplitView}
  onRegisterMemoryLoader={handleRegisterMemoryLoader}  // ← 메모이제이션된 함수
/>
```

**chat-interface.tsx** (Line 349-354):
```typescript
// useEffect 의존성 배열 유지
useEffect(() => {
  if (onRegisterMemoryLoader) {
    onRegisterMemoryLoader(loadMemoryConversation)
  }
}, [onRegisterMemoryLoader, loadMemoryConversation])
```

**결과**:
- ✅ "Maximum update depth exceeded" 에러 제거
- ✅ 불필요한 재렌더링 방지
- ✅ 성능 향상

---

### 1.3 loadMemoryConversation 초기화 오류 해결 ✅

**문제**:
```
ReferenceError: Cannot access 'loadMemoryConversation' before initialization
```

**원인**:
- useEffect(Line 349)가 `loadMemoryConversation`을 의존성으로 참조
- `loadMemoryConversation` 함수가 나중에(Line 332) 정의됨
- JavaScript 호이스팅 문제

**해결 방법**:
- `loadMemoryConversation` 함수를 `useCallback`으로 감싸서 먼저 정의
- useEffect를 나중에 배치

**수정된 파일**: `frontend/components/chat-interface.tsx`

**수정 내용** (Line 324-354):
```typescript
// Before: useEffect가 먼저 → loadMemoryConversation이 나중 (에러!)
useEffect(() => { ... }, [loadMemoryConversation])
const loadMemoryConversation = (memory) => { ... }

// After: loadMemoryConversation이 먼저 → useEffect가 나중 (정상!)
const loadMemoryConversation = useCallback((memory: ConversationMemory) => {
  console.log('[ChatInterface] Loading memory conversation:', memory.id)

  const userMessage: Message = {
    id: `memory-user-${memory.id}`,
    type: "user",
    content: memory.query,
    timestamp: new Date(memory.created_at)
  }

  const botMessage: Message = {
    id: `memory-bot-${memory.id}`,
    type: "bot",
    content: memory.response_summary,
    timestamp: new Date(memory.created_at)
  }

  setMessages([userMessage, botMessage])
  console.log('[ChatInterface] Replaced messages with memory conversation')
}, [])  // 빈 의존성 배열

useEffect(() => {
  if (onRegisterMemoryLoader) {
    onRegisterMemoryLoader(loadMemoryConversation)
  }
}, [onRegisterMemoryLoader, loadMemoryConversation])
```

**결과**:
- ✅ 초기화 오류 완전 해결
- ✅ 함수 메모이제이션으로 성능 최적화
- ✅ React 권장 패턴 적용

---

## 2. 현재 시스템 상태

### 2.1 해결된 문제들 ✅

| 문제 | 상태 | 설명 |
|------|------|------|
| **ScrollArea 무한 루프** | ✅ **완전 해결** | 48번+ 에러 → 0번 에러 |
| **useCallback 무한 루프** | ✅ **완전 해결** | page.tsx 함수 메모이제이션 |
| **초기화 순서 에러** | ✅ **완전 해결** | loadMemoryConversation 순서 수정 |
| **페이지 전환** | ✅ **정상** | 지도 ↔ 채팅 에러 없음 |
| **WebSocket 연결** | ✅ **정상** | 재연결 로직 정상 작동 |
| **채팅 UI** | ✅ **정상** | 환영 메시지, 입력창 표시 |

### 2.2 브라우저 콘솔 로그 분석

**현재 접속 시 로그** (F5 후):
```
✅ New session created: session-1fe9b3d9...
✅ New session created: session-e1331417...  ← React Strict Mode (2번째)
[ChatWSClient] Connecting to ws://...
[ChatWSClient] Disconnecting...  ← 첫 번째 세션 정리
[ChatWSClient] Connecting to ws://...  ← 두 번째 세션 연결
[ChatWSClient] ✅ Connected
[ChatInterface] WebSocket connected
[ChatInterface] No messages in DB, keeping welcome message
[Fast Refresh] done in 57ms
```

**특징**:
- ⚠️ 세션 2개 생성 (React Strict Mode 개발 환경 전용)
- ✅ 최종적으로 1개 세션만 사용 (나머지는 정리됨)
- ✅ WebSocket 정상 연결
- ✅ 무한 루프 에러 없음

### 2.3 남아있는 개발 환경 이슈

#### React Strict Mode 세션 2개 생성 ⚠️

**현상**:
```typescript
// use-session.ts의 useEffect가 2번 실행됨
useEffect(() => {
  initSession()  // 1번째 실행: session-1fe9b3d9 생성
  // Strict Mode cleanup
  // 2번째 실행: session-e1331417 생성
}, [])
```

**이유**:
- React 18 Strict Mode가 개발 환경에서 useEffect를 의도적으로 2번 실행
- 예상치 못한 사이드 이펙트 탐지를 위한 React의 디버깅 기능
- **프로덕션 환경에서는 1번만 실행됨** (정상)

**영향**:
- ✅ 기능적으로 문제 없음 (최종 1개 세션만 사용)
- ⚠️ DB에 사용하지 않는 세션 1개 추가로 저장됨
- ⚠️ 개발 환경에서만 발생

**해결 옵션**:
1. **무시** - 프로덕션에서는 발생하지 않음
2. **Strict Mode 비활성화** - next.config.js 수정 (1분)
3. **cleanup 함수 추가** - use-session.ts에 isMounted 패턴 적용 (5분, 권장)
4. **sessionStorage 체크 강화** - 중복 실행 방지 로직 추가 (2분)

---

### 2.4 테스트 필요 항목 ⏳

| 테스트 항목 | 상태 | 우선순위 |
|-----------|------|---------|
| **메시지 전송** | ⏳ 미테스트 | 높음 |
| **응답 수신** | ⏳ 미테스트 | 높음 |
| **structured_data 표시** | ⏳ 미테스트 | 높음 |
| **F5 새로고침 복원** | ⏳ 미테스트 | 높음 |
| **DB 메시지 저장** | ⏳ 미테스트 | 중간 |
| **스크롤 자동 이동** | ⏳ 미테스트 | 낮음 |

---

## 3. 남은 작업

### 3.1 즉시 실행 가능 작업

#### Option A: 세션 2개 생성 문제 해결 (선택 사항)

**방법 1: React Strict Mode 비활성화** (가장 빠름)

**파일**: `frontend/next.config.js` 또는 `frontend/next.config.mjs`

**수정**:
```javascript
const nextConfig = {
  reactStrictMode: false,  // 개발 환경에서 비활성화
}

export default nextConfig
```

**장점**:
- 1줄 수정으로 즉시 해결
- 세션 1개만 생성됨

**단점**:
- React 18 미래 기능 대비 불가
- 잠재적 버그 탐지 기능 상실

---

**방법 2: useEffect cleanup 함수 추가** (권장)

**파일**: `frontend/hooks/use-session.ts`

**수정**:
```typescript
useEffect(() => {
  let isMounted = true  // cleanup 플래그

  const initSession = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY)

      if (storedSessionId) {
        console.log("✅ Using existing session:", storedSessionId)
        if (isMounted) {  // ← 마운트 상태 체크
          setSessionId(storedSessionId)
          setIsLoading(false)
        }
        return
      }

      console.log("🔄 Creating new session...")
      const response = await chatAPI.startSession({
        metadata: {
          device: "web_browser",
          user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
        },
      })

      if (isMounted) {  // ← 마운트 상태 체크
        console.log("✅ New session created:", response.session_id)
        setSessionId(response.session_id)
        sessionStorage.setItem(SESSION_STORAGE_KEY, response.session_id)
      }
    } catch (err) {
      if (isMounted) {  // ← 마운트 상태 체크
        console.error("❌ Session initialization failed:", err)
        setError(err instanceof Error ? err.message : "Failed to initialize session")
      }
    } finally {
      if (isMounted) {  // ← 마운트 상태 체크
        setIsLoading(false)
      }
    }
  }

  initSession()

  // Cleanup: 언마운트 시 플래그 변경
  return () => {
    isMounted = false
  }
}, [])
```

**장점**:
- Strict Mode 유지 (React 권장)
- 중복 세션 생성 방지
- 미래 대비

**단점**:
- 코드 복잡도 증가

---

**방법 3: sessionStorage 체크 강화** (가장 간단)

**파일**: `frontend/hooks/use-session.ts`

**수정**:
```typescript
useEffect(() => {
  // 이미 세션이 있으면 중복 실행 방지
  if (sessionId) return

  initSession()
}, [])  // sessionId를 의존성에 추가하지 않음
```

**장점**:
- 최소한의 수정 (1줄)

**단점**:
- 타이밍 이슈 가능성

---

#### Option B: 시스템 안정성 테스트 완료

**목표**: 현재 시스템이 완전히 정상 작동하는지 확인

**테스트 시나리오**:

1. **메시지 전송/수신 테스트**
   ```
   1. 채팅창에 질문 입력: "임대차계약이 뭐야?"
   2. 응답 수신 확인
   3. Backend 로그 확인:
      - "💾 Message saved: user → session-xxx"
      - "💾 Message saved: assistant → session-xxx"
   4. 콘솔 에러 없는지 확인
   ```

2. **F5 새로고침 테스트**
   ```
   1. 메시지 전송 후 응답 받기
   2. F5 새로고침
   3. 대화 내역 유지 확인
   4. 콘솔 로그:
      - "✅ Loaded N messages from DB"
   ```

3. **structured_data 표시 테스트**
   ```
   1. 법률 질문 입력 (구조화된 답변)
   2. AnswerDisplay 컴포넌트 정상 렌더링 확인
   3. sections 배열 정상 표시 확인
   ```

4. **DB 저장 확인**
   ```
   # PostgreSQL 쿼리 실행
   SELECT session_id, role, substring(content, 1, 50), structured_data IS NOT NULL
   FROM chat_messages
   ORDER BY created_at DESC
   LIMIT 5;
   ```

**예상 소요 시간**: 15-20분

---

### 3.2 다음 큰 작업: 세션 관리 기능 구현

**목표**: 사이드바에 채팅 세션 목록 표시 및 관리

**기능 요구사항**:
1. ✅ 사이드바에 세션 목록 표시 (SessionList 컴포넌트)
2. ✅ "새 채팅" 버튼으로 새 세션 생성
3. ✅ 과거 채팅 클릭해서 불러오기
4. ✅ 세션 제목 자동 생성 (첫 질문 기반)
5. ✅ 세션 삭제 기능

**예상 소요 시간**: 70분 (기존 계획서 참조)

**전제 조건**:
- ✅ ScrollArea 무한 루프 해결됨 (완료)
- ✅ useCallback 무한 루프 해결됨 (완료)
- ⏳ 시스템 안정성 테스트 완료 (권장)

**작업 단계**:
1. useChatSessions 훅 활성화 및 테스트
2. SessionList 컴포넌트 활성화
3. "새 채팅" 버튼 기능 연결
4. 세션 전환 기능 테스트
5. 세션 삭제 기능 테스트

---

## 4. 수정된 파일 상세

### 4.1 frontend/components/chat-interface.tsx

**수정 횟수**: 2회

**변경 사항 1: ScrollArea 제거**
- Line 7: `import { ScrollArea }` 제거
- Line 459: `<ScrollArea>` → `<div className="... overflow-y-auto">`
- Line 494: `</ScrollArea>` → `</div>`
- Line 318-322: 스크롤 로직 단순화

**변경 사항 2: loadMemoryConversation 메모이제이션**
- Line 324-347: `loadMemoryConversation` 함수를 useCallback으로 감쌈
- Line 349-354: useEffect를 loadMemoryConversation 아래로 이동

**Git 상태**:
- ScrollArea 변경: 사용자가 직접 커밋 완료
- loadMemoryConversation 변경: 커밋 필요

---

### 4.2 frontend/app/page.tsx

**수정 횟수**: 1회

**변경 사항**:
- Line 3: `import { useState, useCallback }` - useCallback 추가
- Line 39-41: `handleRegisterMemoryLoader` 함수 생성 (useCallback)
- Line 46: `onRegisterMemoryLoader={handleRegisterMemoryLoader}` 사용
- Line 56: 동일 (default case)

**Git 상태**: 커밋 필요

---

### 4.3 수정 요약

| 파일 | 변경 사항 | Git 상태 |
|------|---------|---------|
| `chat-interface.tsx` | ScrollArea 제거 + useCallback 추가 | 일부 커밋됨 |
| `page.tsx` | useCallback 추가 | 커밋 필요 |

**커밋 명령어**:
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001
git add frontend/app/page.tsx frontend/components/chat-interface.tsx
git commit -m "Fix: Resolve all infinite loop issues with useCallback memoization

- Add useCallback to page.tsx handleRegisterMemoryLoader
- Wrap loadMemoryConversation in useCallback
- Fix initialization order error
- Prevent unnecessary re-renders

Fixes #infinite-loop
"
```

---

## 5. 테스트 체크리스트

### 5.1 완료된 테스트 ✅

- [x] **ScrollArea 제거 후 페이지 전환**
  - 지도 → 채팅: 정상 ✅
  - 채팅 → 지도: 정상 ✅
  - 무한 루프 에러 없음 ✅

- [x] **useCallback 적용 후 콘솔 확인**
  - "Maximum update depth exceeded" 에러 사라짐 ✅
  - 렌더링 횟수 정상 ✅

- [x] **WebSocket 연결**
  - 세션 생성 후 자동 연결 ✅
  - 재연결 로직 정상 작동 ✅

### 5.2 미완료 테스트 ⏳

- [ ] **메시지 전송/수신**
  - [ ] 사용자 메시지 전송
  - [ ] AI 응답 수신
  - [ ] ExecutionPlan 표시
  - [ ] ExecutionProgress 표시
  - [ ] 최종 응답 표시

- [ ] **structured_data 표시**
  - [ ] AnswerDisplay 컴포넌트 렌더링
  - [ ] sections 배열 표시
  - [ ] metadata 표시

- [ ] **F5 새로고침**
  - [ ] 메시지 복원 (DB에서 로드)
  - [ ] 스크롤 위치 (맨 아래)
  - [ ] WebSocket 재연결

- [ ] **DB 저장 확인**
  - [ ] user 메시지 저장
  - [ ] assistant 메시지 저장
  - [ ] structured_data 저장 (JSONB)

- [ ] **세션 2개 생성 이슈 해결** (선택)
  - [ ] Strict Mode 비활성화 또는
  - [ ] cleanup 함수 추가

---

## 6. 다음 세션 시작 가이드

### 6.1 빠른 상황 파악 (1분)

```bash
# 1. Git 상태 확인
cd C:\kdy\Projects\holmesnyangz\beta_v001
git status

# 2. 수정된 파일 확인
git diff frontend/app/page.tsx
git diff frontend/components/chat-interface.tsx

# 3. 최근 커밋 확인
git log --oneline -5
```

**예상 결과**:
- `frontend/app/page.tsx` - Modified (useCallback 추가)
- `frontend/components/chat-interface.tsx` - Modified (일부는 커밋됨)

---

### 6.2 시작 옵션

#### 옵션 1: 시스템 안정성 테스트 완료 (추천)

**목표**: 현재 시스템이 완전히 정상 작동하는지 확인

**단계**:
1. 브라우저 열기: http://localhost:3000
2. 메시지 전송 테스트 실행 (위 체크리스트 참조)
3. F5 새로고침 테스트
4. DB 확인

**예상 시간**: 15-20분

**다음 단계**: 세션 관리 기능 구현

---

#### 옵션 2: 세션 2개 생성 문제 해결

**목표**: React Strict Mode 이슈 해결

**선택**:
- **A**: Strict Mode 비활성화 (빠름, 1분)
- **B**: cleanup 함수 추가 (권장, 5분)
- **C**: sessionStorage 체크 (간단, 2분)

**파일**: `frontend/hooks/use-session.ts` 또는 `next.config.js`

**다음 단계**: 시스템 안정성 테스트

---

#### 옵션 3: 세션 관리 기능 구현 (큰 작업)

**목표**: 사이드바에 채팅 세션 목록 표시

**전제 조건**:
- ✅ 무한 루프 완전 해결됨
- ⏳ 시스템 안정성 테스트 완료 (권장)

**단계**:
1. `CHAT_SYSTEM_STRUCTURE_AND_PLAN_251016.md` 읽기
2. Phase 1 시작: useChatSessions 훅 활성화
3. SessionList 컴포넌트 통합
4. "새 채팅" 버튼 연결
5. 테스트

**예상 시간**: 70분

---

### 6.3 관련 문서

**이 세션의 문서**:
- `SCROLLAREA_FIX_AND_ARCHITECTURE_ANALYSIS_251016.md` - 전체 아키텍처 분석
- `INFINITE_LOOP_FIX_AND_NEXT_STEPS_251016.md` - 이 문서

**이전 세션 문서**:
- `CHAT_SYSTEM_STRUCTURE_AND_PLAN_251016.md` - 채팅 시스템 전체 계획
- `PHASE0_STRUCTURE_ANALYSIS_251016.md` - Phase 0 분석
- `Fix_Plan_Chat_Message_Persistence_251016.md` - 메시지 저장 계획

---

### 6.4 핵심 코드 위치

**Frontend**:
- `frontend/app/page.tsx:39-41` - handleRegisterMemoryLoader (useCallback)
- `frontend/components/chat-interface.tsx:324-354` - loadMemoryConversation (useCallback)
- `frontend/components/chat-interface.tsx:459` - ScrollArea → div 변경
- `frontend/hooks/use-session.ts:13-15` - 세션 초기화 (세션 2개 생성 이슈)

**Backend**:
- `backend/app/api/chat_api.py:30` - _save_message_to_db()
- `backend/app/api/chat_api.py:243` - WebSocket 엔드포인트
- `backend/app/models/chat.py` - ChatSession, ChatMessage 모델

---

### 6.5 브라우저 확인 사항

**접속**: http://localhost:3000

**F12 콘솔에서 확인할 로그**:
```
✅ New session created: session-xxx  (1~2번)
[ChatWSClient] ✅ Connected
[ChatInterface] WebSocket connected
[ChatInterface] No messages in DB, keeping welcome message
```

**확인할 에러 (없어야 함)**:
```
❌ Maximum update depth exceeded  ← 이 에러가 없어야 정상
❌ Cannot access 'loadMemoryConversation' before initialization  ← 없어야 정상
```

---

## 7. 요약

### 7.1 이번 세션 성과

✅ **3개의 무한 루프 버그 완전 해결**:
1. ScrollArea 무한 루프 (Radix UI 문제)
2. useCallback 무한 루프 (page.tsx 함수 재생성)
3. 초기화 순서 에러 (loadMemoryConversation 순서 문제)

✅ **시스템 안정화**:
- 페이지 전환 정상 작동
- WebSocket 연결 안정화
- 코드 품질 향상 (React 권장 패턴 적용)

### 7.2 현재 상태

**정상 작동**:
- ✅ 채팅 UI 표시
- ✅ 페이지 전환 (지도 ↔ 채팅)
- ✅ WebSocket 연결
- ✅ 환영 메시지 표시

**테스트 필요**:
- ⏳ 메시지 전송/수신
- ⏳ F5 새로고침 복원
- ⏳ structured_data 표시
- ⏳ DB 저장 확인

**선택적 개선**:
- ⚠️ 세션 2개 생성 (React Strict Mode, 프로덕션에서는 정상)

### 7.3 다음 단계 권장 순서

1. **시스템 안정성 테스트** (15-20분) - 추천
2. **세션 2개 생성 해결** (1-5분) - 선택
3. **Git 커밋** (2분) - 필수
4. **세션 관리 기능 구현** (70분) - 다음 큰 작업

---

**문서 끝**

**다음 세션에서 시작할 때**: 이 문서의 섹션 6을 먼저 읽어주세요.
