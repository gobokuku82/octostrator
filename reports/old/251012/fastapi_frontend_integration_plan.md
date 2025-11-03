# Frontend-Backend 통합 계획서

## 📋 개요

**작성일**: 2025-10-08
**목적**: Next.js Frontend와 FastAPI Backend 연결
**기술 스택**: Next.js 14, React 18, TypeScript, FastAPI

---

## 🔍 현재 Frontend 구조 분석

### 1. **프로젝트 구조**
```
frontend/
├── app/
│   ├── page.tsx                    # 메인 페이지 (HomePage)
│   ├── layout.tsx                  # 루트 레이아웃
│   └── globals.css
├── components/
│   ├── chat-interface.tsx          # ⭐ 주요 수정 대상
│   ├── chat-interface-alt.tsx
│   ├── sidebar.tsx
│   ├── map-interface.tsx
│   └── agents/
│       ├── analysis-agent.tsx
│       ├── verification-agent.tsx
│       ├── consultation-agent.tsx
│       ├── contract-analysis.tsx
│       └── property-documents.tsx
├── lib/
│   ├── utils.ts
│   ├── district-coordinates.ts
│   └── clustering.ts
├── hooks/
│   ├── use-toast.ts
│   └── use-mobile.ts
└── package.json
```

### 2. **현재 ChatInterface 분석**

**위치**: `frontend/components/chat-interface.tsx`

**현재 상태**:
- ✅ 메시지 UI 구현됨
- ✅ 사용자 입력 처리
- ✅ Agent 타입 감지 로직 (`detectAgentType`)
- ❌ **Mock 데이터 사용 중** (setTimeout으로 가짜 응답)
- ❌ **Backend API 연결 없음**

**주요 기능**:
- 메시지 송수신 UI
- Agent 팝업 표시
- 예시 질문 버튼
- 처리 중 로딩 애니메이션 (Agent별 동영상)

**데이터 구조**:
```typescript
interface Message {
  id: string
  type: "user" | "bot" | "agent-popup"
  content: string
  timestamp: Date
  agentType?: PageType
  isProcessing?: boolean
}
```

### 3. **기술 스택 확인**

- **Next.js**: 14.2.16 (App Router 사용)
- **React**: 18
- **TypeScript**: 5
- **UI 라이브러리**: Radix UI + shadcn/ui
- **상태 관리**: useState (로컬 상태만 사용)
- **HTTP 클라이언트**: 없음 (추가 필요)

---

## 🎯 통합 목표

### 1. **API 연동**
- FastAPI Backend (`http://localhost:8000/api/v1/chat`)와 통신
- 세션 관리 (서버 생성 `session_id` 사용)
- 실시간 메시지 송수신

### 2. **세션 관리**
- 페이지 로드 시 세션 자동 생성
- `sessionStorage`에 session_id 저장
- 세션 만료 처리

### 3. **응답 처리**
- Backend의 상세 응답 파싱
- `planning_info`, `team_results`, `search_results` 표시
- 에러 핸들링

### 4. **UX 개선**
- 실제 Backend 처리 시간 반영
- 에러 메시지 표시
- 재시도 로직

---

## 📝 구현 계획

### Phase 1: 기본 구조 설정 (30분)

#### 1.1 타입 정의 파일 생성
**파일**: `frontend/types/chat.ts`

```typescript
// API 요청/응답 타입 (FastAPI Pydantic 모델과 일치)
export interface SessionStartRequest {
  user_id?: string
  metadata?: Record<string, any>
}

export interface SessionStartResponse {
  session_id: string
  message: string
  expires_at: string
}

export interface ChatRequest {
  query: string
  session_id: string
  enable_checkpointing?: boolean
  user_context?: Record<string, any>
}

export interface ChatResponse {
  session_id: string
  request_id: string
  status: string
  response: {
    answer: string
    confidence?: number
    sources?: Array<{
      law_name: string
      article: string
      relevance: number
    }>
  }
  planning_info?: {
    query_analysis?: any
    execution_steps?: any[]
    plan_status?: string
  }
  team_results?: Record<string, any>
  search_results?: any[]
  analysis_metrics?: any
  execution_time_ms?: number
  teams_executed: string[]
  error?: string
}

export interface SessionInfo {
  session_id: string
  user_id?: string
  created_at: string
  last_activity: string
  expires_at: string
  is_active: boolean
  metadata?: Record<string, any>
}
```

#### 1.2 API 서비스 레이어 생성
**파일**: `frontend/lib/api.ts`

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const API_PREFIX = "/api/v1/chat"

class ChatAPIService {
  private baseUrl: string

  constructor() {
    this.baseUrl = `${API_BASE_URL}${API_PREFIX}`
  }

  // 세션 시작
  async startSession(
    request: SessionStartRequest = {}
  ): Promise<SessionStartResponse> {
    const response = await fetch(`${this.baseUrl}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`)
    }

    return response.json()
  }

  // 채팅 메시지 전송
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `Failed to send message: ${response.statusText}`)
    }

    return response.json()
  }

  // 세션 정보 조회
  async getSessionInfo(sessionId: string): Promise<SessionInfo> {
    const response = await fetch(`${this.baseUrl}/${sessionId}`)

    if (!response.ok) {
      throw new Error(`Failed to get session info: ${response.statusText}`)
    }

    return response.json()
  }

  // 세션 삭제
  async deleteSession(sessionId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${sessionId}`, {
      method: "DELETE",
    })

    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.statusText}`)
    }
  }
}

export const chatAPI = new ChatAPIService()
```

#### 1.3 환경 변수 설정
**파일**: `frontend/.env.local`

```bash
# FastAPI Backend URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### Phase 2: 세션 관리 Hook (30분)

#### 2.1 세션 관리 커스텀 Hook
**파일**: `frontend/hooks/use-session.ts`

```typescript
import { useState, useEffect } from "react"
import { chatAPI } from "@/lib/api"
import type { SessionStartResponse } from "@/types/chat"

const SESSION_STORAGE_KEY = "holmes_session_id"

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 세션 초기화
  useEffect(() => {
    initSession()
  }, [])

  const initSession = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // 1. sessionStorage에서 기존 세션 확인
      const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY)

      if (storedSessionId) {
        // 2. 세션 유효성 검증
        try {
          await chatAPI.getSessionInfo(storedSessionId)
          setSessionId(storedSessionId)
          setIsLoading(false)
          return
        } catch {
          // 만료된 세션 - 삭제하고 새로 생성
          sessionStorage.removeItem(SESSION_STORAGE_KEY)
        }
      }

      // 3. 새 세션 생성
      const response = await chatAPI.startSession({
        metadata: {
          device: "web_browser",
          user_agent: navigator.userAgent,
        },
      })

      setSessionId(response.session_id)
      sessionStorage.setItem(SESSION_STORAGE_KEY, response.session_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to initialize session")
    } finally {
      setIsLoading(false)
    }
  }

  // 세션 재생성
  const resetSession = async () => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
    await initSession()
  }

  return {
    sessionId,
    isLoading,
    error,
    resetSession,
  }
}
```

---

### Phase 3: ChatInterface 수정 (1시간)

#### 3.1 ChatInterface 컴포넌트 수정
**파일**: `frontend/components/chat-interface.tsx`

**주요 변경사항**:

1. **세션 관리 통합**
```typescript
import { useSession } from "@/hooks/use-session"

export function ChatInterface({ onSplitView }: ChatInterfaceProps) {
  const { sessionId, isLoading: sessionLoading, error: sessionError } = useSession()
  // ...
}
```

2. **실제 API 호출로 변경**
```typescript
const handleSendMessage = async (content: string) => {
  if (!content.trim() || !sessionId) return

  const userMessage: Message = {
    id: Date.now().toString(),
    type: "user",
    content,
    timestamp: new Date(),
  }

  setMessages((prev) => [...prev, userMessage])
  setInputValue("")
  setIsProcessing(true)

  try {
    // 🔥 실제 API 호출
    const response = await chatAPI.sendMessage({
      query: content,
      session_id: sessionId,
      enable_checkpointing: true,
    })

    // Agent 타입 감지 (응답의 teams_executed 기반)
    const agentType = detectAgentTypeFromResponse(response)

    // 봇 응답 추가
    const botMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: "bot",
      content: response.response.answer,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, botMessage])

    // Agent 팝업 표시 (필요시)
    if (agentType && response.teams_executed.length > 0) {
      const agentPopup: Message = {
        id: (Date.now() + 2).toString(),
        type: "agent-popup",
        content: getAgentResponseFromAPI(agentType, response),
        timestamp: new Date(),
        agentType,
      }
      setMessages((prev) => [...prev, agentPopup])
    }

  } catch (error) {
    // 에러 메시지 표시
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: "bot",
      content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}`,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, errorMessage])
  } finally {
    setIsProcessing(false)
  }
}
```

3. **응답 기반 Agent 타입 감지**
```typescript
const detectAgentTypeFromResponse = (response: ChatResponse): PageType | null => {
  const teams = response.teams_executed

  if (teams.includes("analysis_team")) return "analysis"
  if (teams.includes("search_team")) return "verification"
  // 기본 agent 로직 유지
  return null
}

const getAgentResponseFromAPI = (agentType: PageType, response: ChatResponse): string => {
  const executionTime = response.execution_time_ms || 0
  const teamCount = response.teams_executed.length

  switch (agentType) {
    case "analysis":
      return `분석 에이전트가 ${teamCount}개 팀을 사용하여 ${executionTime}ms 동안 처리했습니다.`
    case "verification":
      return `검증 에이전트가 처리를 완료했습니다. ${response.search_results?.length || 0}개의 결과를 찾았습니다.`
    default:
      return `처리가 완료되었습니다.`
  }
}
```

4. **로딩 및 에러 상태 처리**
```typescript
// 세션 로딩 중
if (sessionLoading) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-muted-foreground">세션을 초기화하는 중...</p>
      </div>
    </div>
  )
}

// 세션 에러
if (sessionError) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <p className="text-sm text-destructive mb-4">{sessionError}</p>
        <Button onClick={resetSession}>다시 시도</Button>
      </div>
    </div>
  )
}
```

---

### Phase 4: 응답 데이터 시각화 (선택 사항, 1시간)

#### 4.1 상세 정보 표시 컴포넌트
**파일**: `frontend/components/chat-response-detail.tsx`

```typescript
interface ChatResponseDetailProps {
  response: ChatResponse
}

export function ChatResponseDetail({ response }: ChatResponseDetailProps) {
  return (
    <div className="mt-4 space-y-4">
      {/* Planning Info */}
      {response.planning_info && (
        <Card className="p-4">
          <h4 className="font-semibold mb-2">계획 정보</h4>
          <div className="text-sm text-muted-foreground">
            <p>상태: {response.planning_info.plan_status}</p>
            <p>실행 단계: {response.planning_info.execution_steps?.length || 0}개</p>
          </div>
        </Card>
      )}

      {/* Search Results */}
      {response.search_results && response.search_results.length > 0 && (
        <Card className="p-4">
          <h4 className="font-semibold mb-2">검색 결과 ({response.search_results.length}개)</h4>
          <div className="space-y-2">
            {response.search_results.slice(0, 3).map((result, idx) => (
              <div key={idx} className="text-sm border-l-2 border-primary pl-3">
                <p className="font-medium">{result.law_name}</p>
                <p className="text-muted-foreground">관련도: {(result.relevance * 100).toFixed(1)}%</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Execution Metrics */}
      {response.execution_time_ms && (
        <div className="text-xs text-muted-foreground">
          처리 시간: {response.execution_time_ms}ms |
          실행된 팀: {response.teams_executed.join(", ")}
        </div>
      )}
    </div>
  )
}
```

---

## 📊 데이터 플로우

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │
       │ 1. 페이지 로드
       ↓
┌─────────────────────┐
│  useSession Hook    │
│ (세션 초기화)       │
└──────┬──────────────┘
       │
       │ 2. POST /api/v1/chat/start
       ↓
┌─────────────────────┐
│  FastAPI Backend    │
│  (세션 생성)        │
└──────┬──────────────┘
       │
       │ 3. session_id 반환
       ↓
┌─────────────────────┐
│  sessionStorage     │
│  (session_id 저장) │
└─────────────────────┘

사용자 메시지 전송 시:
┌─────────────┐
│ ChatInterface│
└──────┬───────┘
       │
       │ 4. handleSendMessage()
       ↓
┌─────────────────────┐
│  chatAPI.sendMessage│
│  (POST /api/v1/chat)│
└──────┬──────────────┘
       │
       │ 5. ChatRequest
       ↓
┌─────────────────────┐
│  TeamBasedSupervisor│
│  (LangGraph 실행)   │
└──────┬──────────────┘
       │
       │ 6. ChatResponse (상세)
       ↓
┌─────────────────────┐
│  Message 배열 업데이트│
│  (UI 렌더링)        │
└─────────────────────┘
```

---

## ✅ 체크리스트

### 기본 기능
- [ ] 타입 정의 파일 생성 (`types/chat.ts`)
- [ ] API 서비스 레이어 생성 (`lib/api.ts`)
- [ ] 환경 변수 설정 (`.env.local`)
- [ ] 세션 관리 Hook 생성 (`hooks/use-session.ts`)
- [ ] ChatInterface 수정 (API 연동)

### 고급 기능 (선택)
- [ ] 응답 상세 정보 표시 컴포넌트
- [ ] 재시도 로직
- [ ] 오프라인 감지
- [ ] 타이핑 인디케이터
- [ ] 메시지 히스토리 persist

### 테스트
- [ ] 세션 생성 테스트
- [ ] 메시지 송수신 테스트
- [ ] 에러 핸들링 테스트
- [ ] 세션 만료 처리 테스트

---

## 🚀 실행 순서

### 1. Backend 실행
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Frontend 패키지 설치 (없는 경우)
```bash
cd frontend
npm install
```

### 3. 환경 변수 설정
```bash
# frontend/.env.local 생성
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 4. Frontend 실행
```bash
npm run dev
```

### 5. 브라우저 접속
```
http://localhost:3000
```

---

## 🧪 테스트 시나리오

### Scenario 1: 기본 대화
1. 페이지 로드 → 세션 자동 생성 확인
2. "부동산 매매 계약 시 주의사항은?" 입력
3. Backend 응답 확인
4. Agent 팝업 표시 확인

### Scenario 2: 세션 유지
1. 페이지 새로고침
2. 기존 세션 ID 유지 확인 (sessionStorage)
3. 대화 이어가기

### Scenario 3: 에러 처리
1. Backend 중단
2. 메시지 전송 시도
3. 에러 메시지 표시 확인

---

## 📈 성능 최적화 (추후)

### 1. API 응답 캐싱
- React Query 또는 SWR 도입
- 동일 질문 재사용

### 2. 낙관적 업데이트
- 사용자 메시지 즉시 표시
- Backend 응답 대기 중에도 UI 반응성 유지

### 3. Streaming 응답
- Server-Sent Events (SSE)
- 긴 응답을 실시간으로 표시

---

## 🔒 보안 고려사항

### 1. XSS 방지
- 사용자 입력 sanitization
- React의 기본 escaping 활용

### 2. CORS 설정
- Backend의 `allow_origins` 프로덕션 설정
- 현재: `["*"]` (개발용)
- 프로덕션: 특정 도메인만 허용

### 3. API 키 관리
- `.env.local` 사용
- Git에 커밋하지 않음 (`.gitignore`)

---

## 📝 구현 우선순위

### 필수 (Week 1)
1. ✅ 타입 정의
2. ✅ API 서비스 레이어
3. ✅ 세션 관리 Hook
4. ✅ ChatInterface API 연동

### 선택 (Week 2)
5. 응답 상세 정보 표시
6. 에러 재시도 로직
7. 메시지 히스토리 저장

### 최적화 (Week 3+)
8. React Query 도입
9. Streaming 응답
10. 성능 모니터링

---

**작성자**: Claude Code
**버전**: 1.0.0
**마지막 업데이트**: 2025-10-08
