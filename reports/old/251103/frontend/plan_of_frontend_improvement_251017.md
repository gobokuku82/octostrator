# Frontend 기능 고도화 계획서 - 2025-10-17

## 목적 (Purpose)

Frontend에서 **인터페이스는 구현되었지만 기능이 미완성**인 부분들을 Backend와 연결하여 완전히 동작하도록 구현합니다.

---

## 재분석 결과 (Re-Analysis Result)

### ❌ 기존 분석 오류
**잘못된 판단**: "Dead Code이므로 삭제 필요"

**올바른 판단**: "**미완성 기능**이므로 구현 필요"

---

## 미완성 기능 목록 (Incomplete Features)

### ✅ Phase 1: 파일 삭제 - 올바른 판단
- `memory-history.tsx` - 실제로 Dead Code ✅ 삭제 완료

### ❌ Phase 2-5: 재검토 필요 - 미완성 기능들

| 항목 | 기존 판단 | 올바른 판단 | 상태 |
|------|----------|------------|------|
| **Split View** | Dead Code | 미완성 기능 | 구현 필요 |
| **todos State** | Unused | Backend 연동 필요 | 구현 필요 |
| **onRegisterMemoryLoader** | Dead Code | 장기 메모리 기능 (선택) | 보류 가능 |

---

## Feature 1: Split View 기능 (분할 화면)

### 현재 상태

**Frontend 구현 완료**:
- ✅ `page.tsx`에 Split View UI 구현됨
- ✅ `handleSplitView()` 함수 존재
- ✅ `renderSplitContent()` 함수 존재
- ✅ `isSplitView` state 관리
- ✅ Analysis, Verification, Consultation Agent 분할 표시 가능

**문제**:
- ❌ ChatInterface에서 `onSplitView`를 받지만 **호출하지 않음**
- ❌ 사용자가 Split View를 트리거할 방법이 없음

### Backend 지원 현황

**Backend에 Agent 기능 존재**:
```python
# backend/app/service_agent/cognitive_agents/
- property_analyzer.py     # 분석 에이전트
- fraud_detector.py         # 검증 에이전트
- consultation_advisor.py   # 상담 에이전트
```

**API 엔드포인트**:
- ✅ `/api/v1/chat/message` - 통합 엔드포인트 (모든 Agent 처리)

---

### 구현 방안

#### A. 사용자 트리거 추가

**방법 1: AnswerDisplay에 버튼 추가** (추천)

사용자가 답변을 받은 후, 관련 Agent를 Split View로 열 수 있도록 버튼 추가

**파일**: `frontend/components/answer-display.tsx`

**예시**:
```tsx
// 답변 하단에 Quick Action 버튼
<div className="mt-4 flex gap-2">
  {metadata.intent_type === "legal_consult" && (
    <Button onClick={() => onOpenSplitView?.("analysis")}>
      계약서 분석 상세보기
    </Button>
  )}
  {metadata.intent_type === "risk_analysis" && (
    <Button onClick={() => onOpenSplitView?.("verification")}>
      허위매물 검증하기
    </Button>
  )}
</div>
```

**방법 2: ExecutionPlanPage에 버튼 추가**

작업 계획이 표시될 때, 관련 Agent를 미리 열 수 있도록 버튼 추가

**파일**: `frontend/components/execution-plan-page.tsx`

---

#### B. 연결 작업

**1단계**: ChatInterface props 연결
```typescript
// chat-interface.tsx
export function ChatInterface({ onSplitView, currentSessionId }: ChatInterfaceProps) {
  // _onSplitView 제거, onSplitView 직접 사용
```

**2단계**: AnswerDisplay에 callback 전달
```typescript
// chat-interface.tsx
<AnswerDisplay
  sections={message.structuredData.sections}
  metadata={message.structuredData.metadata}
  onOpenSplitView={onSplitView}  // ✅ 추가
/>
```

**3단계**: AnswerDisplay props 추가
```typescript
// answer-display.tsx
interface AnswerDisplayProps {
  sections: AnswerSection[]
  metadata: AnswerMetadata
  onOpenSplitView?: (agentType: PageType) => void  // ✅ 추가
}
```

---

### 예상 사용 시나리오

```
1. 사용자: "강남구 아파트 계약서 검토해주세요"
   ↓
2. Backend: 법률 상담 답변 반환
   ↓
3. Frontend: AnswerDisplay 표시
   ↓
4. 사용자: "계약서 분석 상세보기" 버튼 클릭
   ↓
5. Split View 열림: 왼쪽=채팅, 오른쪽=AnalysisAgent
```

---

## Feature 2: Execution Steps (TODO) 실시간 표시

### 현재 상태

**Frontend**:
- ✅ `ExecutionProgressPage` 컴포넌트 존재
- ✅ `todos` state 선언됨
- ✅ WebSocket으로 `todo_created`, `todo_updated` 메시지 수신
- ❌ `todos` state를 업데이트는 하지만 **렌더링하지 않음**

**Backend**:
- ✅ `execution_steps` 생성 (`execution_orchestrator.py`)
- ✅ WebSocket으로 `todo_created`, `todo_updated` 전송
- ✅ `ExecutionStepState` 타입 정의

**문제**:
- ❌ Frontend에서 `ExecutionProgressPage`를 **렌더링하지 않음**
- ❌ `todos`가 업데이트되지만 UI에 표시 안 됨

---

### Backend의 execution_steps 구조

**파일**: `backend/app/service_agent/cognitive_agents/execution_orchestrator.py`

```python
execution_steps = [
    {
        "team": "search_team",
        "action": "법령 검색",
        "status": "pending",
        "estimated_time": 3,
        "result": None
    },
    {
        "team": "analysis_team",
        "action": "법률 분석",
        "status": "in_progress",
        "estimated_time": 5,
        "result": None
    }
]
```

**WebSocket 메시지**:
```json
{
  "type": "todo_created",
  "execution_steps": [...]
}
```

---

### 구현 방안

#### A. ExecutionProgressPage 렌더링 추가

**파일**: `frontend/components/chat-interface.tsx`

**현재**:
```typescript
const [todos, setTodos] = useState<ExecutionStepState[]>([])

// setTodos는 호출됨
case 'todo_created':
  setTodos(message.execution_steps || [])
  break

// 하지만 렌더링은 안 됨!
```

**수정 후**:
```typescript
// 1. ExecutionProgressPage용 메시지 생성
case 'todo_created':
  const progressMessage: Message = {
    id: `progress-${Date.now()}`,
    type: "execution-progress",
    content: "",
    timestamp: new Date(),
    executionSteps: message.execution_steps,
    executionPlan: getCurrentExecutionPlan()  // 현재 plan
  }
  setMessages(prev => [...prev, progressMessage])
  break

case 'todo_updated':
  // 기존 progress 메시지 업데이트
  setMessages(prev => prev.map(m =>
    m.type === "execution-progress"
      ? { ...m, executionSteps: message.execution_steps }
      : m
  ))
  break
```

---

#### B. ExecutionPlan 참조 유지

**문제**: `ExecutionProgressPage`는 `executionPlan`과 `executionSteps` 둘 다 필요

**해결**:
```typescript
// plan_ready에서 executionPlan 저장
const [currentPlan, setCurrentPlan] = useState<ExecutionPlan | null>(null)

case 'plan_ready':
  const plan = { intent, confidence, execution_steps, ... }
  setCurrentPlan(plan)  // ✅ 저장
  break

case 'todo_created':
  const progressMessage: Message = {
    executionPlan: currentPlan,  // ✅ 사용
    executionSteps: message.execution_steps
  }
  break
```

---

### 예상 UI 변화

**Before (현재)**:
```
[User] 강남구 아파트 시세 알려주세요
  ↓
[ExecutionPlanPage] 작업 계획 표시
  ↓
[Bot] 답변
```

**After (구현 후)**:
```
[User] 강남구 아파트 시세 알려주세요
  ↓
[ExecutionPlanPage] 작업 계획 표시
  ↓
[ExecutionProgressPage] 실시간 진행 상황 ✨ 새로 표시
  - ✅ 법령 검색 완료
  - 🔄 법률 분석 진행 중...
  - ⏳ 최종 답변 생성 대기
  ↓
[Bot] 답변
```

---

## Feature 3: 장기 메모리 (ConversationMemory) - 선택적

### 현재 상태

**Frontend**:
- ❌ `onRegisterMemoryLoader` prop chain
- ❌ `loadMemoryConversation` callback

**Backend**:
- ❌ `/api/v1/chat/memory/history` 엔드포인트 없음
- ✅ Chat History & State Endpoints로 대체됨

**판단**:
- 현재 Chat History로 충분히 동작
- 장기 메모리 기능은 **추후 개선**으로 보류
- **삭제 권장** (Dead Code 맞음)

---

## 구현 우선순위 (Priority)

### 🔴 High Priority

#### 1. Execution Steps 실시간 표시
- **이유**: Backend가 이미 데이터 전송 중
- **효과**: 사용자가 AI 작업 진행 상황을 실시간으로 확인 가능
- **난이도**: ⭐⭐ (중간)
- **작업 시간**: 2시간

#### 2. Split View 기능 완성
- **이유**: UI는 완성, 트리거만 추가하면 됨
- **효과**: 사용자가 채팅하면서 Agent 동시 사용 가능
- **난이도**: ⭐⭐⭐ (중상)
- **작업 시간**: 3시간

### 🟡 Low Priority

#### 3. 장기 메모리 Props 제거 ✅ 완료
- **이유**: 현재 시스템으로 충분
- **효과**: 코드 간소화
- **난이도**: ⭐ (쉬움)
- **작업 시간**: 30분
- **상태**: ✅ 완료 (2025-10-17)

---

## 상세 구현 계획

### Task 1: Execution Steps 실시간 표시

**목표**: Backend의 `execution_steps` 업데이트를 UI에 반영

#### Step 1-1: currentPlan State 추가 (chat-interface.tsx)

**Before**:
```typescript
const [messages, setMessages] = useState<Message[]>([...])
```

**After**:
```typescript
const [messages, setMessages] = useState<Message[]>([...])
const [currentPlan, setCurrentPlan] = useState<ExecutionPlan | null>(null)
```

---

#### Step 1-2: plan_ready에서 currentPlan 저장

**Before**:
```typescript
case 'plan_ready':
  if (message.intent && message.execution_steps) {
    setMessages((prev) =>
      prev.map(m =>
        m.type === "execution-plan" && m.executionPlan?.isLoading
          ? { ...m, executionPlan: plan }
          : m
      )
    )
  }
  break
```

**After**:
```typescript
case 'plan_ready':
  if (message.intent && message.execution_steps) {
    const plan = {
      intent: message.intent,
      confidence: message.confidence,
      execution_steps: message.execution_steps,
      execution_strategy: message.execution_strategy,
      estimated_total_time: message.estimated_total_time,
      keywords: message.keywords,
      isLoading: false
    }

    setCurrentPlan(plan)  // ✅ 추가

    setMessages((prev) =>
      prev.map(m =>
        m.type === "execution-plan" && m.executionPlan?.isLoading
          ? { ...m, executionPlan: plan }
          : m
      )
    )
  }
  break
```

---

#### Step 1-3: todo_created 처리 수정

**Before**:
```typescript
case 'todo_created':
  if (message.execution_steps) {
    setTodos(message.execution_steps)  // ❌ 렌더링 안 함
  }
  break
```

**After**:
```typescript
case 'todo_created':
  if (message.execution_steps && currentPlan) {
    // ExecutionProgressPage 메시지 생성
    const progressMessage: Message = {
      id: `progress-${Date.now()}`,
      type: "execution-progress",
      content: "",
      timestamp: new Date(),
      executionPlan: currentPlan,
      executionSteps: message.execution_steps
    }

    setMessages((prev) => [...prev, progressMessage])
  }
  break
```

---

#### Step 1-4: todo_updated 처리 수정

**Before**:
```typescript
case 'todo_updated':
  if (message.execution_steps) {
    setTodos(message.execution_steps)  // ❌ 렌더링 안 함
  }
  break
```

**After**:
```typescript
case 'todo_updated':
  if (message.execution_steps) {
    // 기존 progress 메시지 업데이트
    setMessages((prev) =>
      prev.map(m =>
        m.type === "execution-progress"
          ? { ...m, executionSteps: message.execution_steps }
          : m
      )
    )
  }
  break
```

---

#### Step 1-5: todos State 제거

**이유**: 이제 `messages` 배열로 관리하므로 불필요

**Before**:
```typescript
const [todos, setTodos] = useState<ExecutionStepState[]>([])
```

**After**: 삭제

**Before**:
```typescript
import type { ExecutionStepState } from "@/lib/types"
```

**After**: 삭제

---

### Task 2: Split View 기능 완성

**목표**: 사용자가 답변 후 Agent를 Split View로 열 수 있도록

#### Step 2-1: AnswerDisplay Props 추가

**파일**: `frontend/components/answer-display.tsx`

**Before**:
```typescript
interface AnswerDisplayProps {
  sections: AnswerSection[]
  metadata: AnswerMetadata
}
```

**After**:
```typescript
interface AnswerDisplayProps {
  sections: AnswerSection[]
  metadata: AnswerMetadata
  onOpenSplitView?: (agentType: PageType) => void
}
```

---

#### Step 2-2: Quick Action 버튼 추가

**파일**: `frontend/components/answer-display.tsx`

**위치**: CardFooter 내부 (Line ~140)

**추가 코드**:
```tsx
{/* Quick Actions */}
{onOpenSplitView && (
  <div className="mt-4 pt-4 border-t">
    <h4 className="text-xs font-semibold text-muted-foreground mb-2">
      관련 도구
    </h4>
    <div className="flex gap-2 flex-wrap">
      {metadata.intent_type === "legal_consult" && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onOpenSplitView("analysis")}
          className="text-xs"
        >
          📄 계약서 분석
        </Button>
      )}
      {metadata.intent_type === "market_inquiry" && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onOpenSplitView("map")}
          className="text-xs"
        >
          🗺️ 지도에서 보기
        </Button>
      )}
      {(metadata.intent_type === "risk_analysis" ||
        metadata.intent_type === "comprehensive") && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onOpenSplitView("verification")}
          className="text-xs"
        >
          🔍 허위매물 검증
        </Button>
      )}
      <Button
        variant="outline"
        size="sm"
        onClick={() => onOpenSplitView("consultation")}
        className="text-xs"
      >
        💬 상담 에이전트
      </Button>
    </div>
  </div>
)}
```

---

#### Step 2-3: ChatInterface에서 onSplitView 전달

**파일**: `frontend/components/chat-interface.tsx`

**Before** (Line 70):
```typescript
export function ChatInterface({ onSplitView: _onSplitView, onRegisterMemoryLoader, currentSessionId }: ChatInterfaceProps) {
```

**After**:
```typescript
export function ChatInterface({ onSplitView, onRegisterMemoryLoader, currentSessionId }: ChatInterfaceProps) {
```

**Before** (Line ~560):
```tsx
<AnswerDisplay
  sections={message.structuredData.sections}
  metadata={message.structuredData.metadata}
/>
```

**After**:
```tsx
<AnswerDisplay
  sections={message.structuredData.sections}
  metadata={message.structuredData.metadata}
  onOpenSplitView={onSplitView}
/>
```

---

### Task 3: 장기 메모리 Props 제거 ✅ 완료

**목표**: Dead Code 제거

**완료 사항**:
- ✅ `page.tsx`: `handleRegisterMemoryLoader`, `loadMemory` state 제거
- ✅ `page.tsx`: `onRegisterMemoryLoader`, `onLoadMemory` props 제거 (Sidebar, ChatInterface)
- ✅ `chat-interface.tsx`: `ConversationMemory` interface 제거
- ✅ `chat-interface.tsx`: `onRegisterMemoryLoader` prop 제거
- ✅ `chat-interface.tsx`: `loadMemoryConversation` callback 제거 (30줄)
- ✅ `sidebar.tsx`: `onLoadMemory` prop 제거
- ✅ `types/session.ts`: `ConversationMemory` interface 제거

**결과**:
- 총 제거된 코드: ~45줄
- Props drilling 3단계 제거
- 더 이상 사용되지 않는 ConversationMemory 시스템 완전 제거

---

## 코드 변경 요약 (Code Changes Summary)

### Task 1: Execution Steps 실시간 표시

| 파일 | 변경 내용 | 추가 줄 수 | 삭제 줄 수 |
|------|----------|-----------|-----------|
| `chat-interface.tsx` | currentPlan state 추가 | +1 | 0 |
| `chat-interface.tsx` | plan_ready 수정 | +3 | 0 |
| `chat-interface.tsx` | todo_created 수정 | +10 | -3 |
| `chat-interface.tsx` | todo_updated 수정 | +8 | -3 |
| `chat-interface.tsx` | todos state 삭제 | 0 | -1 |
| `chat-interface.tsx` | ExecutionStepState import 삭제 | 0 | -1 |
| **총합** | | **+22** | **-8** |

### Task 2: Split View 기능 완성

| 파일 | 변경 내용 | 추가 줄 수 |
|------|----------|-----------|
| `answer-display.tsx` | onOpenSplitView prop 추가 | +1 |
| `answer-display.tsx` | Quick Action 버튼 추가 | +40 |
| `chat-interface.tsx` | _onSplitView → onSplitView | 0 |
| `chat-interface.tsx` | AnswerDisplay에 prop 전달 | +1 |
| **총합** | | **+42** |

---

## 예상 효과 (Expected Benefits)

### 1. Execution Steps 실시간 표시

**Before**:
- 사용자: "AI가 뭐하는지 모르겠어요... 답변이 안 와요"

**After**:
- ✅ 실시간 진행 상황 표시
- ✅ 예상 소요 시간 표시
- ✅ 각 단계별 상태 (대기/진행/완료)
- ✅ 사용자 불안감 해소

---

### 2. Split View 기능

**Before**:
- 사용자: "계약서 분석하려면 새로 질문해야 하나요?"

**After**:
- ✅ 답변 보면서 바로 Agent 실행
- ✅ 채팅 내용 보존 (Split View)
- ✅ 워크플로우 개선

---

## 테스트 계획 (Testing Plan)

### Task 1 테스트

**시나리오**:
1. 사용자: "강남구 아파트 전세 시세 알려주세요"
2. 확인:
   - [ ] ExecutionPlanPage 표시
   - [ ] ExecutionProgressPage 표시 ✨ 새로 추가
   - [ ] 진행 상황 업데이트 (todo_updated)
   - [ ] 완료 후 AnswerDisplay 표시

**체크리스트**:
- [ ] 진행 상황이 실시간으로 업데이트됨
- [ ] 각 단계의 상태가 정확함 (pending/in_progress/completed)
- [ ] 예상 시간이 표시됨
- [ ] UI 깨짐 없음

---

### Task 2 테스트

**시나리오**:
1. 사용자: "강남구 아파트 계약서 검토해주세요"
2. 답변 수신
3. "📄 계약서 분석" 버튼 클릭
4. 확인:
   - [ ] Split View 열림
   - [ ] 왼쪽: 채팅 유지
   - [ ] 오른쪽: AnalysisAgent 표시

**체크리스트**:
- [ ] Intent별로 올바른 버튼 표시
- [ ] 버튼 클릭 시 Split View 동작
- [ ] 모바일/데스크톱 모두 동작
- [ ] 닫기 버튼 동작

---

## 결론 (Conclusion)

### 구현 난이도
- **Task 1**: ⭐⭐ (중간)
- **Task 2**: ⭐⭐⭐ (중상)

### 예상 작업 시간
- **Task 1**: 2시간
- **Task 2**: 3시간
- **테스트**: 1시간
- **총 소요 시간**: **6시간**

### 주요 효과
1. **UX 대폭 개선** ✅
   - 실시간 진행 상황 표시
   - Split View로 워크플로우 개선

2. **Backend 기능 활용** ✅
   - 이미 전송 중인 데이터 활용
   - Agent 시스템 완전 연동

3. **코드 완성도 향상** ✅
   - 미완성 기능 완성
   - 사용자 의도 반영

### 권장 사항
✅ **Task 1 우선 구현 권장**
- Backend 데이터 활용
- 사용자 경험 크게 개선
- 구현 난이도 적당

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0 (Cleanup에서 Improvement로 변경)
