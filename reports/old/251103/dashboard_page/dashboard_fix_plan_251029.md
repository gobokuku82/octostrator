# 대시보드 작동 문제 분석 및 수정 계획서

**작성일**: 2025-10-29
**문서 타입**: 문제 분석 및 수정 계획
**우선순위**: 높음

---

## 🔍 현재 상황 분석

### 1. 구현된 구조

#### Cognitive Dashboard
- **위치**: `frontend/components/dashboards/cognitive-dashboard.tsx`
- **독립 WebSocket 연결**: 자체 `useSession()` 및 `createWSClient()` 사용
- **처리 메시지**: `analysis_start`, `plan_ready`, `data_reuse_notification`, `execution_start`

#### Execution Dashboard
- **위치**: `frontend/components/dashboards/execution-dashboard.tsx`
- **독립 WebSocket 연결**: 자체 `useSession()` 및 `createWSClient()` 사용
- **처리 메시지**: `execution_start`, `agent_steps_initialized`, `agent_step_progress`, `todo_updated`, `response_generating_start/progress`, `final_response`

#### 백엔드 메시지 전송
- **팀 Supervisor**: `team_supervisor.py`
  - ✅ `plan_ready` (line 589)
  - ✅ `agent_steps_initialized` (line 610)
  - ✅ `agent_step_progress` (line 627)
  - ✅ `execution_start` (line 1014)

---

## ❌ 문제점 분석

### 문제 1: WebSocket 메시지 타입 불일치

**현상**:
- `ws.ts`의 `WSMessageType`에 대시보드가 필요로 하는 메시지 타입이 정의되어 있지 않음

**누락된 타입**:
```typescript
// ws.ts (현재 - 11개 타입만 정의)
export type WSMessageType =
  | 'connected'
  | 'planning_start'
  | 'plan_ready'
  | 'execution_start'
  | 'todo_created'
  | 'todo_updated'
  | 'step_start'
  | 'step_progress'
  | 'step_complete'
  | 'final_response'
  | 'error';

// 누락된 타입들 (대시보드가 기대하는 메시지)
  | 'analysis_start'                 // Cognitive Dashboard
  | 'data_reuse_notification'        // Cognitive Dashboard
  | 'agent_steps_initialized'        // Execution Dashboard
  | 'agent_step_progress'            // Execution Dashboard
  | 'response_generating_start'      // Execution Dashboard
  | 'response_generating_progress'   // Execution Dashboard
  | 'supervisor_phase_change'        // 3-Layer Progress
  | 'workflow_interrupted'           // HITL
```

**영향**:
- TypeScript 타입 체크 실패 가능
- 메시지가 전송되어도 타입 미정의로 처리 안 될 수 있음

---

### 문제 2: 독립 세션으로 인한 메시지 격리 ⭐ 핵심 문제

**현상**:
- 각 대시보드가 `useSession()`을 호출하여 **별도의 세션 ID**를 생성
- 각 대시보드가 **독립적인 WebSocket 연결**을 생성

**문제 시나리오**:
```
1. 사용자가 ChatInterface 열기
   → useSession() 호출 → Session A 생성
   → WebSocket A 연결 (ws://localhost:8000/.../Session_A)

2. 사용자가 Cognitive Dashboard 열기
   → useSession() 호출 → Session B 생성
   → WebSocket B 연결 (ws://localhost:8000/.../Session_B)

3. 사용자가 ChatInterface에서 질문 입력
   → Session A로 메시지 전송
   → 백엔드가 Session A로 응답 전송
   → Cognitive Dashboard는 Session B를 듣고 있음
   → ❌ 메시지 수신 불가
```

**근본 원인**:
- 대시보드가 **질문을 직접 입력받는 독립 모드**로 설계됨
- 세션 공유 메커니즘이 없음
- 각 컴포넌트가 독립적으로 세션 생성

---

### 문제 3: WebSocket 싱글톤 충돌

**현상**:
```typescript
// ws.ts
export function createWSClient(config: WSClientConfig): ChatWSClient {
  if (wsClientInstance) {
    wsClientInstance.disconnect();  // ❌ 이전 연결 끊김
  }
  wsClientInstance = new ChatWSClient(config);
  return wsClientInstance;
}
```

**문제점**:
- WebSocket 싱글톤 패턴이 **하나의 연결만 유지**
- 새로운 페이지를 열면 → 이전 페이지의 연결이 끊김
- ChatInterface ↔ Dashboard 전환 시 연결 끊김 반복

---

### 문제 4: 메시지 브로드캐스팅 부재

**현상**:
- 백엔드는 하나의 세션에만 메시지 전송
- 같은 메시지를 여러 컴포넌트가 받을 방법 없음

**필요한 것**:
- 하나의 WebSocket 연결을 여러 컴포넌트가 구독하는 패턴
- 메시지 브로드캐스팅 메커니즘

---

## 🎯 수정 방안

### 방안 A: 통합 WebSocket + React Context (추천 ⭐⭐⭐⭐⭐)

**개념**:
- 하나의 WebSocket 연결을 애플리케이션 전체에서 공유
- React Context로 메시지 브로드캐스팅
- 여러 컴포넌트가 동일 메시지 수신

**아키텍처**:
```
HomePage (App Root)
  ↓
WebSocketProvider (Context)
  ├─ sessionId: 하나의 세션 ID 공유
  ├─ WebSocket: 단일 연결
  └─ messageSubscribers: 구독자 관리
       ↓ (메시지 브로드캐스트)
       ├─ ChatInterface
       ├─ Cognitive Dashboard
       └─ Execution Dashboard
```

**코드 구조**:
```typescript
// context/WebSocketContext.tsx
export const WebSocketProvider = ({ children, sessionId }) => {
  const [wsClient, setWsClient] = useState<ChatWSClient | null>(null)
  const subscribers = useRef<Map<string, (msg: WSMessage) => void>>(new Map())

  // 메시지 수신 시 모든 구독자에게 브로드캐스트
  const handleMessage = (message: WSMessage) => {
    subscribers.current.forEach(callback => callback(message))
  }

  // 구독 API
  const subscribe = (id: string, callback: (msg: WSMessage) => void) => {
    subscribers.current.set(id, callback)
    return () => subscribers.current.delete(id)
  }

  return (
    <WebSocketContext.Provider value={{ wsClient, subscribe, send }}>
      {children}
    </WebSocketContext.Provider>
  )
}

// 컴포넌트에서 사용
const CognitiveDashboard = () => {
  const { subscribe } = useWebSocket()

  useEffect(() => {
    return subscribe('cognitive-dashboard', (message) => {
      if (message.type === 'plan_ready') {
        // 처리
      }
    })
  }, [])
}
```

**장점**:
- ✅ 세션 공유 자동 해결
- ✅ 중복 연결 제거
- ✅ 모든 컴포넌트가 동일 메시지 수신
- ✅ React 패턴에 적합
- ✅ 대시보드가 독립적으로 테스트 가능

**단점**:
- 구조 변경 필요 (중간 규모)
- 기존 코드 리팩토링 필요

**구현 시간**: 3시간

---

### 방안 B: 모니터링 전용 모드 (빠른 해결 ⭐⭐⭐⭐)

**개념**:
- 대시보드를 **독립 입력 모드**가 아닌 **ChatInterface 모니터링 모드**로 변경
- ChatInterface가 메시지를 받아서 → 전역 상태로 공유 → 대시보드가 읽기
- 대시보드는 입력 기능 제거, 읽기 전용

**아키텍처**:
```
ChatInterface (WebSocket 소유)
  ↓ (메시지 수신)
  ↓ (Zustand Store 업데이트)
  ↓
Cognitive Dashboard (Store 구독)
Execution Dashboard (Store 구독)
```

**코드 구조**:
```typescript
// lib/store/dashboard-store.ts
export const useDashboardStore = create((set) => ({
  cognitiveState: { phase: 'idle' },
  executionState: { status: 'idle', active_teams: [] },

  updateCognitive: (data) => set({ cognitiveState: data }),
  updateExecution: (data) => set({ executionState: data }),
}))

// ChatInterface에서
const handleWSMessage = (message: WSMessage) => {
  // 기존 처리...

  // 대시보드용 업데이트 추가
  if (message.type === 'plan_ready') {
    useDashboardStore.getState().updateCognitive({
      intent_analysis: { ... },
      execution_plan: { ... }
    })
  }
}

// Cognitive Dashboard에서
const CognitiveDashboard = () => {
  const cognitiveState = useDashboardStore(state => state.cognitiveState)

  return (
    <div>
      <p>ChatInterface에서 질문하세요 👉</p>
      {cognitiveState.intent_analysis && (
        <IntentAnalysisCard data={cognitiveState.intent_analysis} />
      )}
    </div>
  )
}
```

**장점**:
- ✅ 빠른 구현 (2시간)
- ✅ 기존 구조 최소 변경
- ✅ WebSocket 연결 중복 없음
- ✅ 즉시 작동

**단점**:
- ❌ 대시보드가 독립적으로 테스트 불가능
- ❌ 항상 ChatInterface를 거쳐야 함
- ❌ 입력 기능 제거

**구현 시간**: 2시간

---

### 방안 C: 백엔드 메시지 복제 (장기 솔루션 ⭐⭐)

**개념**:
- 백엔드에 "세션 그룹" 또는 "메시지 브로드캐스트" 기능 추가
- 여러 WebSocket 연결이 같은 메시지를 받도록 설정

**아키텍처**:
```
Backend ConnectionManager
  ↓ (세션 그룹 관리)
  ├─ Group A (같은 사용자)
  │   ├─ WebSocket 1 (ChatInterface)
  │   ├─ WebSocket 2 (Cognitive Dashboard)
  │   └─ WebSocket 3 (Execution Dashboard)
  └─ 메시지 브로드캐스트 → 그룹 내 모든 연결
```

**장점**:
- ✅ 대시보드가 완전 독립 작동
- ✅ 프론트엔드 구조 변경 최소

**단점**:
- ❌ 백엔드 수정 필요 (복잡도 높음)
- ❌ 세션 관리 로직 대폭 변경
- ❌ 구현 시간 오래 걸림

**구현 시간**: 5시간+

---

## 📊 의사결정 매트릭스

| 방안 | 구현 시간 | 복잡도 | 독립 테스트 | 유지보수 | 즉시 작동 | 추천도 |
|------|----------|--------|-------------|----------|-----------|--------|
| **방안 A** (통합 WebSocket) | 3시간 | 중간 | ✅ | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ |
| **방안 B** (모니터링 모드) | 2시간 | 낮음 | ❌ | ⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ |
| **방안 C** (백엔드 확장) | 5시간+ | 높음 | ✅ | ⭐⭐⭐⭐ | ❌ | ⭐⭐ |

---

## 🎯 최종 추천: 방안 A (통합 WebSocket + React Context)

### 선택 이유

1. **중장기 관점**:
   - 깔끔한 아키텍처
   - 확장성 우수
   - 다른 대시보드 추가 시 재사용 가능

2. **사용자 경험**:
   - 대시보드가 독립적으로 작동
   - 실시간 테스트 가능
   - 입력 기능 유지

3. **유지보수**:
   - React 표준 패턴
   - 코드 가독성 높음
   - 버그 추적 용이

4. **구현 시간**:
   - 3시간 (합리적)
   - 한 번 구현하면 영구적 해결

---

## 📋 구현 계획 (방안 A)

### Phase 1: WebSocket 타입 확장 (15분)

**파일**: `frontend/lib/ws.ts`

**수정 내용**:
```typescript
export type WSMessageType =
  | 'connected'
  | 'planning_start'
  | 'analysis_start'              // 추가
  | 'plan_ready'
  | 'execution_start'
  | 'todo_created'
  | 'todo_updated'
  | 'step_start'
  | 'step_progress'
  | 'step_complete'
  | 'agent_steps_initialized'     // 추가
  | 'agent_step_progress'         // 추가
  | 'data_reuse_notification'     // 추가
  | 'response_generating_start'   // 추가
  | 'response_generating_progress' // 추가
  | 'supervisor_phase_change'     // 추가
  | 'workflow_interrupted'        // 추가
  | 'final_response'
  | 'error';
```

---

### Phase 2: WebSocketContext 생성 (1시간)

**파일**: `frontend/context/WebSocketContext.tsx` (새로 생성)

**구조**:
```typescript
import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { createWSClient, ChatWSClient, type WSMessage } from '@/lib/ws'

interface WebSocketContextValue {
  wsClient: ChatWSClient | null
  isConnected: boolean
  subscribe: (id: string, callback: (message: WSMessage) => void) => () => void
  send: (message: any) => void
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null)

export function WebSocketProvider({
  children,
  sessionId
}: {
  children: React.ReactNode
  sessionId: string
}) {
  const [wsClient, setWsClient] = useState<ChatWSClient | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const subscribersRef = useRef<Map<string, (msg: WSMessage) => void>>(new Map())

  useEffect(() => {
    if (!sessionId) return

    const client = createWSClient({
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
      sessionId,
      onMessage: (message) => {
        // 모든 구독자에게 브로드캐스트
        subscribersRef.current.forEach(callback => {
          callback(message)
        })
      },
      onConnected: () => setIsConnected(true),
      onDisconnected: () => setIsConnected(false),
    })

    client.connect()
    setWsClient(client)

    return () => {
      client.disconnect()
      subscribersRef.current.clear()
    }
  }, [sessionId])

  const subscribe = (id: string, callback: (message: WSMessage) => void) => {
    subscribersRef.current.set(id, callback)
    return () => subscribersRef.current.delete(id)
  }

  const send = (message: any) => {
    wsClient?.send(message)
  }

  return (
    <WebSocketContext.Provider value={{ wsClient, isConnected, subscribe, send }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider')
  }
  return context
}
```

---

### Phase 3: HomePage에 Provider 추가 (15분)

**파일**: `frontend/app/page.tsx`

**수정**:
```typescript
export default function HomePage() {
  const { currentSessionId } = useChatSessions()

  return (
    <WebSocketProvider sessionId={currentSessionId || ''}>
      <div className="flex h-screen bg-background">
        {/* 기존 코드 */}
      </div>
    </WebSocketProvider>
  )
}
```

---

### Phase 4: ChatInterface 리팩토링 (30분)

**파일**: `frontend/components/chat-interface.tsx`

**수정**:
```typescript
export function ChatInterface({ onSplitView, currentSessionId }: ChatInterfaceProps) {
  const { subscribe, send, isConnected } = useWebSocket()
  // WebSocket 관련 코드 제거 (wsClientRef, createWSClient 등)

  useEffect(() => {
    const unsubscribe = subscribe('chat-interface', handleWSMessage)
    return unsubscribe
  }, [subscribe, handleWSMessage])

  const handleSendMessage = () => {
    send({
      type: 'query',
      query: inputValue,
      enable_checkpointing: true
    })
  }
}
```

---

### Phase 5: Cognitive Dashboard 리팩토링 (30분)

**파일**: `frontend/components/dashboards/cognitive-dashboard.tsx`

**수정**:
```typescript
export function CognitiveDashboard() {
  const { subscribe, send, isConnected } = useWebSocket()
  // useSession, createWSClient 제거

  useEffect(() => {
    const unsubscribe = subscribe('cognitive-dashboard', handleWSMessage)
    return unsubscribe
  }, [subscribe, handleWSMessage])
}
```

---

### Phase 6: Execution Dashboard 리팩토링 (30분)

**파일**: `frontend/components/dashboards/execution-dashboard.tsx`

**수정**:
```typescript
export function ExecutionDashboard() {
  const { subscribe, send, isConnected } = useWebSocket()
  // useSession, createWSClient 제거

  useEffect(() => {
    const unsubscribe = subscribe('execution-dashboard', handleWSMessage)
    return unsubscribe
  }, [subscribe, handleWSMessage])
}
```

---

### Phase 7: 테스트 (30분)

**테스트 시나리오**:
1. ChatInterface에서 질문 입력
2. Cognitive Dashboard에서 Intent Analysis 실시간 업데이트 확인
3. Execution Dashboard에서 팀 실행 상황 실시간 업데이트 확인
4. 모든 탭 동시 열기 테스트
5. WebSocket 재연결 테스트

---

## 📝 구현 체크리스트

### Phase 1: 준비 (15분)
- [ ] `ws.ts` 타입 확장
- [ ] TypeScript 빌드 확인

### Phase 2: Context 생성 (1시간)
- [ ] `context/WebSocketContext.tsx` 생성
- [ ] `useWebSocket` 훅 구현
- [ ] 메시지 브로드캐스팅 로직 구현
- [ ] 구독 패턴 구현

### Phase 3: 통합 (30분)
- [ ] `HomePage`에 Provider 추가
- [ ] sessionId 전달 확인

### Phase 4: 리팩토링 (1.5시간)
- [ ] `ChatInterface` 리팩토링
- [ ] `CognitiveDashboard` 리팩토링
- [ ] `ExecutionDashboard` 리팩토링
- [ ] WebSocket 중복 연결 코드 제거

### Phase 5: 테스트 (30분)
- [ ] 기본 기능 테스트
- [ ] 실시간 업데이트 테스트
- [ ] 다중 탭 테스트
- [ ] 재연결 테스트

**총 예상 시간**: 3시간

---

## 🚨 주의사항

### 1. sessionId 전달
- `currentSessionId`가 null일 때 처리 필요
- 초기 로딩 시 빈 세션 처리

### 2. 메모리 누수 방지
- 구독 해제(`unsubscribe`) 반드시 호출
- useEffect cleanup 함수 활용

### 3. 메시지 필터링
- 각 컴포넌트가 필요한 메시지만 처리
- 불필요한 리렌더링 방지

---

## 🎉 기대 효과

1. **즉시 작동**: 모든 대시보드가 정상 작동
2. **독립 테스트**: 각 대시보드를 독립적으로 테스트 가능
3. **확장성**: 새로운 대시보드 추가 시 재사용 가능
4. **유지보수**: 깔끔한 아키텍처로 버그 수정 용이
5. **성능**: 단일 WebSocket 연결로 리소스 절약

---

**작성자**: Claude Code
**문서 버전**: 1.0
**최종 수정일**: 2025-10-29
