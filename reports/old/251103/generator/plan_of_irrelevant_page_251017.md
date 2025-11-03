# Irrelevant Message Page 구현 계획서 - 2025-10-17

## 1. 개요 (Overview)

### 목적
사용자가 부동산과 관련 없는 질문(irrelevant) 또는 불명확한 질문(unclear)을 했을 때, 단순한 텍스트 메시지 대신 **시각적으로 꾸며진 안내 페이지**를 표시하여 사용자 경험을 개선합니다.

### 현재 상황
- Backend: `team_supervisor.py`의 `_generate_out_of_scope_response()` 함수가 단순 텍스트 메시지 반환
- Frontend: 일반 봇 메시지로 표시 (텍스트만)
- 문제점: 안내 메시지가 눈에 잘 띄지 않고, 기능 설명이 효과적으로 전달되지 않음

### 목표
- **Guidance Page** 컴포넌트 신규 개발
- Backend의 `type: "guidance"` 응답을 감지하여 전용 UI 표시
- 사용자에게 친근하고 명확한 안내 제공
- 기존 `ExecutionPlanPage`, `AnswerDisplay`와 유사한 디자인 통일성 유지

---

## 2. 현재 시스템 분석 (Current System Analysis)

### Backend 응답 구조 (team_supervisor.py)

**함수 위치**: `backend/app/service_agent/supervisor/team_supervisor.py:930-977`

```python
def _generate_out_of_scope_response(self, state: MainSupervisorState) -> Dict:
    """기능 외 질문에 대한 안내 응답 생성"""
    planning_state = state.get("planning_state", {})
    analyzed_intent = planning_state.get("analyzed_intent", {})
    intent_type = analyzed_intent.get("intent_type", "")
    query = state.get("query", "")

    # Intent 타입에 따른 메시지
    if intent_type == "irrelevant":
        message = """안녕하세요! 저는 부동산 전문 상담 AI입니다.

현재 질문은 부동산과 관련이 없는 것으로 보입니다.

**제가 도와드릴 수 있는 분야:**
- 전세/월세/매매 관련 법률 상담
- 부동산 시세 조회 및 시장 분석
- 주택담보대출 및 전세자금대출 상담
- 임대차 계약서 작성 및 검토
- 부동산 투자 리스크 분석

부동산과 관련된 질문을 해주시면 자세히 안내해드리겠습니다."""

    elif intent_type == "unclear":
        message = f"""질문의 의도를 명확히 파악하기 어렵습니다.

**더 구체적으로 질문해주시면 도움이 됩니다:**
- 어떤 상황인지 구체적으로 설명해주세요
- 무엇을 알고 싶으신지 명확히 해주세요
- 관련된 정보(지역, 금액, 계약 조건 등)를 포함해주세요

**예시:**
- "강남구 아파트 전세 시세 알려주세요"
- "전세금 5% 인상이 가능한가요?"
- "임대차 계약서 검토해주세요"

다시 한번 질문을 구체적으로 말씀해주시면 정확히 답변드리겠습니다."""

    else:
        message = "질문을 이해하는데 어려움이 있습니다. 부동산 관련 질문을 명확히 해주시면 도움을 드리겠습니다."

    return {
        "type": "guidance",  # ✅ 중요: 타입이 "guidance"
        "message": message,
        "original_query": query,
        "detected_intent": intent_type,
        "teams_used": [],
        "data": {}
    }
```

**응답 예시 (WebSocket final_response)**:
```json
{
  "type": "final_response",
  "response": {
    "type": "guidance",
    "message": "안녕하세요! 저는 부동산 전문 상담 AI입니다...",
    "original_query": "안녕? 날씨 어때?",
    "detected_intent": "irrelevant",
    "teams_used": [],
    "data": {}
  }
}
```

---

### Frontend 메시지 처리 흐름

**파일**: `frontend/components/chat-interface.tsx`

**현재 처리 방식** (Line 175-199):
```typescript
case 'final_response':
  // 최종 응답 수신
  // ✅ ExecutionPlan과 Progress 모두 제거
  setMessages((prev) => prev.filter(m =>
    m.type !== "execution-progress" && m.type !== "execution-plan"
  ))

  // 봇 응답 추가 (structured_data 포함)
  const botMessage: Message = {
    id: (Date.now() + 1).toString(),
    type: "bot",  // ⚠️ 모든 응답이 "bot" 타입으로 처리됨
    content: message.response?.answer || message.response?.content || message.response?.message || "응답을 받지 못했습니다.",
    structuredData: message.response?.structured_data,
    timestamp: new Date(),
  }
  setMessages((prev) => [...prev, botMessage])
```

**문제점**:
- `response.type === "guidance"` 체크 없음
- 모든 응답이 동일한 UI로 표시됨
- `guidance` 타입의 특별한 메시지 구조를 활용하지 못함

---

### 기존 페이지 컴포넌트 분석

#### 1. ExecutionPlanPage (실행 계획 페이지)

**파일**: `frontend/components/execution-plan-page.tsx`

**특징**:
- Card 기반 레이아웃
- 로딩 상태 UI (스켈레톤)
- Badge로 의도 표시
- 작업 리스트 번호 매김
- Icon 사용 (Target)

**디자인 요소**:
```tsx
- bg-card border
- bg-muted/50 (의도 정보 영역)
- Badge variant="secondary" (의도)
- Badge variant="outline" (키워드)
- Loader2 + animate-spin (로딩)
```

#### 2. AnswerDisplay (답변 표시 페이지)

**파일**: `frontend/components/answer-display.tsx`

**특징**:
- Card 기반 레이아웃
- Accordion으로 섹션 관리
- Icon 매핑 시스템
- 체크리스트, 경고, 텍스트 타입 구분
- 신뢰도 ProgressBar
- 참고 자료 Footer

**디자인 요소**:
```tsx
- Card with CardHeader, CardContent, CardFooter
- Badge variant="outline" (의도 타입)
- ProgressBar (신뢰도)
- Alert (경고 타입)
- Accordion (확장 가능 섹션)
- CheckCircle2 (체크리스트)
```

---

## 3. 설계 (Design)

### 3-1. Message 타입 확장

**파일**: `frontend/components/chat-interface.tsx`

**현재 Message 인터페이스** (Line 34-45):
```typescript
interface Message {
  id: string
  type: "user" | "bot" | "execution-plan" | "execution-progress"
  content: string
  timestamp: Date
  executionPlan?: ExecutionPlan
  executionSteps?: ExecutionStep[]
  structuredData?: {
    sections: AnswerSection[]
    metadata: AnswerMetadata
  }
}
```

**수정 후**:
```typescript
interface Message {
  id: string
  type: "user" | "bot" | "execution-plan" | "execution-progress" | "guidance"  // ✅ "guidance" 추가
  content: string
  timestamp: Date
  executionPlan?: ExecutionPlan
  executionSteps?: ExecutionStep[]
  structuredData?: {
    sections: AnswerSection[]
    metadata: AnswerMetadata
  }
  guidanceData?: GuidanceData  // ✅ 새로운 필드
}
```

**새로운 GuidanceData 인터페이스**:
```typescript
interface GuidanceData {
  detected_intent: "irrelevant" | "unclear" | "unknown"
  original_query: string
  message: string
  suggestions?: string[]  // 예시 질문 추출
}
```

---

### 3-2. GuidancePage 컴포넌트 설계

**파일**: `frontend/components/guidance-page.tsx` (신규 생성)

#### UI 구조

```
┌─ Card ─────────────────────────────────────────┐
│  ┌─ Header ──────────────────────────────────┐ │
│  │ [Icon] 제목                                │ │
│  │ 부제목                                     │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Intent Badge ───────────────────────────┐ │
│  │ [Badge] 기능 외 질문 / 명확화 필요        │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Message Section ────────────────────────┐ │
│  │ [Alert] 주요 안내 메시지                  │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Features Section (irrelevant만) ────────┐ │
│  │ [List] 제가 도와드릴 수 있는 분야:        │ │
│  │   - 항목 1                                │ │
│  │   - 항목 2                                │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Suggestions Section (unclear만) ────────┐ │
│  │ [List] 더 구체적으로 질문해주세요:        │ │
│  │   - 팁 1                                  │ │
│  │   - 팁 2                                  │ │
│  │                                            │ │
│  │ [Examples] 예시:                          │ │
│  │   - 예시 1                                │ │
│  │   - 예시 2                                │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  ┌─ Original Query (선택적) ────────────────┐ │
│  │ 질문: "..."                               │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### 컴포넌트 Props

```typescript
interface GuidancePageProps {
  guidance: GuidanceData
}
```

#### Intent별 UI 차별화

| Intent 타입 | 색상 테마 | 아이콘 | 제목 | Badge 색상 |
|------------|----------|-------|------|-----------|
| irrelevant | Orange/Amber | MessageCircleOff | "부동산 관련 질문이 아닙니다" | warning (노란색) |
| unclear | Blue | HelpCircle | "질문을 명확히 해주세요" | secondary (회색) |
| unknown | Gray | AlertCircle | "질문 이해 실패" | destructive (빨간색) |

---

### 3-3. Backend 응답 파싱 로직

**파일**: `frontend/components/chat-interface.tsx`

**수정 위치**: `handleWSMessage()` 함수의 `case 'final_response'` 블록

**현재 로직** (Line 175-199):
```typescript
case 'final_response':
  setMessages((prev) => prev.filter(m =>
    m.type !== "execution-progress" && m.type !== "execution-plan"
  ))

  const botMessage: Message = {
    id: (Date.now() + 1).toString(),
    type: "bot",
    content: message.response?.answer || message.response?.content || message.response?.message || "응답을 받지 못했습니다.",
    structuredData: message.response?.structured_data,
    timestamp: new Date(),
  }
  setMessages((prev) => [...prev, botMessage])
```

**수정 후**:
```typescript
case 'final_response':
  setMessages((prev) => prev.filter(m =>
    m.type !== "execution-progress" && m.type !== "execution-plan"
  ))

  // ✅ Guidance 응답 체크
  if (message.response?.type === "guidance") {
    const guidanceMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: "guidance",
      content: message.response.message,
      timestamp: new Date(),
      guidanceData: {
        detected_intent: message.response.detected_intent,
        original_query: message.response.original_query,
        message: message.response.message,
        suggestions: extractSuggestions(message.response.message)
      }
    }
    setMessages((prev) => [...prev, guidanceMessage])
  } else {
    // 기존 로직 (일반 답변)
    const botMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: "bot",
      content: message.response?.answer || message.response?.content || message.response?.message || "응답을 받지 못했습니다.",
      structuredData: message.response?.structured_data,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, botMessage])
  }
```

**Helper 함수**:
```typescript
// 메시지에서 예시 질문 추출
const extractSuggestions = (message: string): string[] => {
  const exampleRegex = /- "(.+?)"/g
  const matches = [...message.matchAll(exampleRegex)]
  return matches.map(match => match[1])
}
```

---

### 3-4. 렌더링 로직 수정

**파일**: `frontend/components/chat-interface.tsx`

**수정 위치**: 메시지 렌더링 부분 (Line 487-518)

**현재**:
```typescript
{messages.map((message) => (
  <div key={message.id} className="space-y-2">
    {message.type === "execution-plan" && message.executionPlan && (
      <ExecutionPlanPage plan={message.executionPlan} />
    )}
    {message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
      <ExecutionProgressPage
        steps={message.executionSteps}
        plan={message.executionPlan}
      />
    )}
    {(message.type === "user" || message.type === "bot") && (
      {/* ... */}
    )}
  </div>
))}
```

**수정 후**:
```typescript
{messages.map((message) => (
  <div key={message.id} className="space-y-2">
    {message.type === "execution-plan" && message.executionPlan && (
      <ExecutionPlanPage plan={message.executionPlan} />
    )}
    {message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
      <ExecutionProgressPage
        steps={message.executionSteps}
        plan={message.executionPlan}
      />
    )}
    {/* ✅ 새로운 Guidance 페이지 */}
    {message.type === "guidance" && message.guidanceData && (
      <GuidancePage guidance={message.guidanceData} />
    )}
    {(message.type === "user" || message.type === "bot") && (
      {/* ... */}
    )}
  </div>
))}
```

---

## 4. 구현 세부사항 (Implementation Details)

### 4-1. GuidancePage 컴포넌트 구조

**파일**: `frontend/components/guidance-page.tsx`

```typescript
"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  MessageCircleOff,
  HelpCircle,
  AlertCircle,
  CheckCircle2,
  Lightbulb
} from "lucide-react"

interface GuidanceData {
  detected_intent: "irrelevant" | "unclear" | "unknown"
  original_query: string
  message: string
  suggestions?: string[]
}

interface GuidancePageProps {
  guidance: GuidanceData
}

export function GuidancePage({ guidance }: GuidancePageProps) {
  // Intent별 설정
  const intentConfig = {
    irrelevant: {
      icon: MessageCircleOff,
      title: "부동산 관련 질문이 아닙니다",
      subtitle: "저는 부동산 전문 상담 AI입니다",
      badgeVariant: "warning" as const,
      badgeLabel: "기능 외 질문",
      iconColor: "text-orange-500"
    },
    unclear: {
      icon: HelpCircle,
      title: "질문을 명확히 해주세요",
      subtitle: "더 구체적인 정보가 필요합니다",
      badgeVariant: "secondary" as const,
      badgeLabel: "명확화 필요",
      iconColor: "text-blue-500"
    },
    unknown: {
      icon: AlertCircle,
      title: "질문 이해 실패",
      subtitle: "부동산 관련 질문을 명확히 해주세요",
      badgeVariant: "destructive" as const,
      badgeLabel: "분석 실패",
      iconColor: "text-gray-500"
    }
  }

  const config = intentConfig[guidance.detected_intent] || intentConfig.unknown
  const Icon = config.icon

  // 메시지 파싱
  const sections = parseMessage(guidance.message, guidance.detected_intent)

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <Card className="p-5 bg-card border flex-1">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-start gap-3">
              <Icon className={`w-6 h-6 ${config.iconColor} mt-1`} />
              <div>
                <h3 className="text-lg font-semibold">{config.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {config.subtitle}
                </p>
              </div>
            </div>
            <Badge variant={config.badgeVariant} className="ml-2">
              {config.badgeLabel}
            </Badge>
          </div>

          {/* Main Message */}
          {sections.mainMessage && (
            <Alert className="mb-4">
              <AlertDescription className="text-sm">
                {sections.mainMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* Features (irrelevant only) */}
          {guidance.detected_intent === "irrelevant" && sections.features && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <h4 className="text-sm font-semibold">제가 도와드릴 수 있는 분야</h4>
              </div>
              <ul className="space-y-2 ml-6">
                {sections.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-primary">•</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tips (unclear only) */}
          {guidance.detected_intent === "unclear" && sections.tips && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="w-4 h-4 text-yellow-500" />
                <h4 className="text-sm font-semibold">더 구체적으로 질문해주시면 도움이 됩니다</h4>
              </div>
              <ul className="space-y-2 ml-6">
                {sections.tips.map((tip, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-primary">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Example Questions */}
          {guidance.suggestions && guidance.suggestions.length > 0 && (
            <div className="mt-4 p-3 bg-muted/50 rounded-lg">
              <h4 className="text-sm font-semibold mb-2">예시 질문:</h4>
              <div className="space-y-2">
                {guidance.suggestions.map((suggestion, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-muted-foreground">{idx + 1}.</span>
                    <span className="text-primary font-medium">"{suggestion}"</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Original Query (Optional, 작게 표시) */}
          <div className="mt-4 pt-3 border-t text-xs text-muted-foreground">
            질문: "{guidance.original_query}"
          </div>
        </Card>
      </div>
    </div>
  )
}

// Helper: 메시지 파싱
function parseMessage(message: string, intent: string) {
  const sections: {
    mainMessage?: string
    features?: string[]
    tips?: string[]
  } = {}

  // 첫 번째 단락을 Main Message로 추출
  const paragraphs = message.split('\n\n')
  sections.mainMessage = paragraphs[0]

  if (intent === "irrelevant") {
    // "제가 도와드릴 수 있는 분야:" 섹션 추출
    const featuresMatch = message.match(/\*\*제가 도와드릴 수 있는 분야:\*\*\n((?:- .+\n?)+)/)
    if (featuresMatch) {
      sections.features = featuresMatch[1]
        .split('\n')
        .filter(line => line.startsWith('- '))
        .map(line => line.substring(2).trim())
    }
  }

  if (intent === "unclear") {
    // "더 구체적으로 질문해주시면..." 섹션 추출
    const tipsMatch = message.match(/\*\*더 구체적으로 질문해주시면 도움이 됩니다:\*\*\n((?:- .+\n?)+)/)
    if (tipsMatch) {
      sections.tips = tipsMatch[1]
        .split('\n')
        .filter(line => line.startsWith('- '))
        .map(line => line.substring(2).trim())
    }
  }

  return sections
}
```

---

### 4-2. 타입 정의 파일 추가

**파일**: `frontend/types/guidance.ts` (신규 생성)

```typescript
/**
 * Guidance 관련 타입 정의
 * 기능 외 질문 또는 불명확한 질문에 대한 안내 메시지
 */

export type GuidanceIntentType = "irrelevant" | "unclear" | "unknown"

export interface GuidanceData {
  /** 감지된 의도 타입 */
  detected_intent: GuidanceIntentType

  /** 사용자의 원본 질문 */
  original_query: string

  /** 안내 메시지 (백엔드에서 생성) */
  message: string

  /** 추출된 예시 질문 (옵션) */
  suggestions?: string[]
}

export interface GuidanceResponse {
  /** 응답 타입 */
  type: "guidance"

  /** 안내 메시지 */
  message: string

  /** 원본 질문 */
  original_query: string

  /** 감지된 의도 */
  detected_intent: GuidanceIntentType

  /** 사용된 팀 (항상 빈 배열) */
  teams_used: string[]

  /** 추가 데이터 (항상 빈 객체) */
  data: Record<string, never>
}
```

---

## 5. 구현 순서 (Implementation Steps)

### Step 1: 타입 정의 및 인터페이스 추가

1. **frontend/types/guidance.ts** 생성
   - `GuidanceIntentType`, `GuidanceData`, `GuidanceResponse` 정의

2. **frontend/components/chat-interface.tsx** 수정
   - `Message` 인터페이스에 `type: "guidance"` 추가
   - `guidanceData?: GuidanceData` 필드 추가

---

### Step 2: GuidancePage 컴포넌트 구현

1. **frontend/components/guidance-page.tsx** 생성
   - 기본 레이아웃 구현
   - Intent별 설정 객체 정의
   - Header, Badge, Icon 구현

2. **메시지 파싱 로직 구현**
   - `parseMessage()` 함수
   - Features 추출 (irrelevant)
   - Tips 추출 (unclear)

3. **섹션 렌더링**
   - Main Message (Alert)
   - Features List (CheckCircle2 아이콘)
   - Tips List (Lightbulb 아이콘)
   - Example Questions (bg-muted/50 박스)
   - Original Query (Footer)

---

### Step 3: WebSocket 메시지 핸들러 수정

**파일**: `frontend/components/chat-interface.tsx`

1. **`handleWSMessage()` 함수 수정**
   - `case 'final_response'` 블록에 guidance 체크 로직 추가
   - `extractSuggestions()` helper 함수 구현

2. **메시지 렌더링 수정**
   - `message.type === "guidance"` 조건 추가
   - `<GuidancePage guidance={message.guidanceData} />` 렌더링

---

### Step 4: 테스트

1. **Irrelevant 질문 테스트**
   - "안녕? 날씨 어때?"
   - "파이썬 코딩 도와줘"
   - 예상: Orange 테마, MessageCircleOff 아이콘, Features 리스트 표시

2. **Unclear 질문 테스트**
   - "계약서"
   - "알려줘"
   - 예상: Blue 테마, HelpCircle 아이콘, Tips 리스트 + 예시 표시

3. **정상 질문 테스트**
   - "전세금 5% 인상 가능한가요?"
   - 예상: 기존대로 ExecutionPlanPage → AnswerDisplay 표시

---

### Step 5: 스타일링 및 반응형 개선 (선택적)

1. **모바일 반응형**
   - `max-w-2xl` → `max-w-full sm:max-w-2xl`
   - 작은 화면에서 padding 조정

2. **애니메이션 추가**
   - `animate-in fade-in-50 duration-500`
   - Icon에 `animate-bounce` (선택적)

3. **접근성 개선**
   - ARIA labels 추가
   - 키보드 네비게이션 지원

---

## 6. Backend 수정 여부 (Backend Modifications)

### 현재 상태
Backend는 이미 `type: "guidance"` 응답을 생성하고 있으므로, **Backend 수정 불필요**.

### 선택적 개선 사항

만약 더 구조화된 데이터를 원한다면:

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**현재**:
```python
return {
    "type": "guidance",
    "message": message,
    "original_query": query,
    "detected_intent": intent_type,
    "teams_used": [],
    "data": {}
}
```

**개선 옵션**:
```python
return {
    "type": "guidance",
    "message": message,
    "original_query": query,
    "detected_intent": intent_type,
    "teams_used": [],
    "data": {
        "features": [  # irrelevant인 경우만
            "전세/월세/매매 관련 법률 상담",
            "부동산 시세 조회 및 시장 분석",
            # ...
        ] if intent_type == "irrelevant" else [],
        "tips": [  # unclear인 경우만
            "어떤 상황인지 구체적으로 설명해주세요",
            "무엇을 알고 싶으신지 명확히 해주세요",
            # ...
        ] if intent_type == "unclear" else [],
        "examples": [
            "강남구 아파트 전세 시세 알려주세요",
            "전세금 5% 인상이 가능한가요?",
            "임대차 계약서 검토해주세요"
        ] if intent_type == "unclear" else []
    }
}
```

**장점**:
- Frontend 파싱 로직 불필요
- Backend에서 완전히 제어
- 다국어 대응 쉬움

**단점**:
- Backend 수정 필요
- 현재 문자열 기반 메시지 형식 변경

**권장**: 현재는 Frontend 파싱으로 시작, 나중에 필요시 Backend 구조화

---

## 7. 코드 변경 요약 (Code Changes Summary)

### 신규 파일

1. **frontend/types/guidance.ts**
   - `GuidanceIntentType`, `GuidanceData`, `GuidanceResponse` 정의
   - ~30 줄

2. **frontend/components/guidance-page.tsx**
   - GuidancePage 컴포넌트
   - parseMessage() helper
   - ~200 줄

### 수정 파일

1. **frontend/components/chat-interface.tsx**
   - Message 인터페이스 수정 (Line 34)
     ```diff
     - type: "user" | "bot" | "execution-plan" | "execution-progress"
     + type: "user" | "bot" | "execution-plan" | "execution-progress" | "guidance"
     + guidanceData?: GuidanceData
     ```

   - handleWSMessage() 수정 (Line 175-199)
     ```diff
     case 'final_response':
     + if (message.response?.type === "guidance") {
     +   // Guidance 메시지 생성
     + } else {
         // 기존 로직
     + }
     ```

   - 렌더링 로직 수정 (Line 487-518)
     ```diff
     + {message.type === "guidance" && message.guidanceData && (
     +   <GuidancePage guidance={message.guidanceData} />
     + )}
     ```

---

## 8. 테스트 계획 (Testing Plan)

### 단위 테스트

1. **parseMessage() 함수 테스트**
   - Irrelevant 메시지 파싱
   - Unclear 메시지 파싱
   - Features 추출 정확도
   - Tips 추출 정확도

2. **extractSuggestions() 함수 테스트**
   - 예시 질문 추출
   - 없는 경우 빈 배열 반환

### 통합 테스트

1. **WebSocket 통신 테스트**
   - Backend guidance 응답 수신
   - Message 객체 생성 확인
   - guidanceData 구조 검증

2. **렌더링 테스트**
   - GuidancePage 컴포넌트 마운트
   - Intent별 UI 차이 확인
   - 섹션 표시 여부

### E2E 테스트

| 테스트 케이스 | 입력 | 예상 출력 |
|-------------|------|----------|
| Irrelevant #1 | "안녕? 날씨 어때?" | Orange 테마, Features 리스트 |
| Irrelevant #2 | "파이썬 코딩 도와줘" | Orange 테마, Features 리스트 |
| Unclear #1 | "계약서" | Blue 테마, Tips + 예시 |
| Unclear #2 | "알려줘" | Blue 테마, Tips + 예시 |
| 정상 질문 | "전세금 5% 인상 가능한가요?" | ExecutionPlanPage → AnswerDisplay |

---

## 9. 예상 결과 (Expected Results)

### Before (현재 상태)

```
┌─ User Message ───────────────────┐
│ 안녕? 날씨 어때?                  │
└───────────────────────────────────┘

┌─ Bot Message (일반 텍스트) ──────┐
│ 안녕하세요! 저는 부동산 전문      │
│ 상담 AI입니다.                    │
│                                    │
│ 현재 질문은 부동산과 관련이 없는   │
│ 것으로 보입니다.                  │
│                                    │
│ **제가 도와드릴 수 있는 분야:**    │
│ - 전세/월세/매매 관련 법률 상담    │
│ - 부동산 시세 조회 및 시장 분석    │
│ ...                                │
└───────────────────────────────────┘
```

**문제점**:
- 평범한 텍스트 메시지
- 시각적으로 눈에 띄지 않음
- 구조화되지 않음

---

### After (수정 후)

```
┌─ User Message ───────────────────┐
│ 안녕? 날씨 어때?                  │
└───────────────────────────────────┘

┌─ GuidancePage ─────────────────────────────────────┐
│ [MessageCircleOff Icon] 부동산 관련 질문이 아닙니다 │ [Badge: 기능 외 질문]
│ 저는 부동산 전문 상담 AI입니다                      │
│                                                      │
│ ┌─ Alert ──────────────────────────────────────┐   │
│ │ 안녕하세요! 저는 부동산 전문 상담 AI입니다.  │   │
│ │ 현재 질문은 부동산과 관련이 없는 것으로 보입니다. │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ [CheckCircle2] 제가 도와드릴 수 있는 분야           │
│   • 전세/월세/매매 관련 법률 상담                   │
│   • 부동산 시세 조회 및 시장 분석                   │
│   • 주택담보대출 및 전세자금대출 상담               │
│   • 임대차 계약서 작성 및 검토                      │
│   • 부동산 투자 리스크 분석                         │
│                                                      │
│ ─────────────────────────────────────────────────  │
│ 질문: "안녕? 날씨 어때?"                            │
└──────────────────────────────────────────────────────┘
```

**개선점**:
- 🎨 시각적으로 눈에 띄는 Card 레이아웃
- 🎯 Intent Badge로 상태 명확화
- 📋 구조화된 리스트 (Features/Tips)
- 🔍 원본 질문 표시

---

## 10. 추가 개선 사항 (Future Enhancements)

### 1. 인터랙티브 예시 버튼

**기능**: 예시 질문을 클릭하면 자동으로 입력창에 채워짐

```typescript
// GuidancePage.tsx에 추가
<Button
  variant="outline"
  size="sm"
  onClick={() => onExampleClick(suggestion)}
  className="text-xs"
>
  {suggestion}
</Button>
```

**필요한 변경**:
- GuidancePageProps에 `onExampleClick?: (text: string) => void` 추가
- chat-interface.tsx에서 콜백 전달

---

### 2. 다국어 지원

**구조**:
```typescript
const translations = {
  ko: {
    irrelevant: {
      title: "부동산 관련 질문이 아닙니다",
      // ...
    },
    en: {
      title: "Not a real estate question",
      // ...
    }
  }
}
```

---

### 3. 사용자 피드백 수집

**기능**: "도움이 되었나요?" 버튼

```typescript
<div className="flex gap-2 mt-4">
  <Button variant="ghost" size="sm" onClick={() => handleFeedback('helpful')}>
    👍 도움됨
  </Button>
  <Button variant="ghost" size="sm" onClick={() => handleFeedback('not_helpful')}>
    👎 도움 안됨
  </Button>
</div>
```

---

### 4. Analytics 추적

**메트릭**:
- Irrelevant 질문 빈도
- Unclear 질문 빈도
- 사용자가 예시 질문 클릭한 비율
- Guidance 페이지 표시 후 재질문 비율

---

## 11. 위험도 평가 (Risk Assessment)

### 낮은 위험 (Low Risk) - 권장 즉시 실행

- ✅ 신규 컴포넌트 추가 (기존 코드 영향 없음)
- ✅ Message 타입 확장 (하위 호환성 유지)
- ✅ WebSocket 메시지 핸들러 수정 (조건문 추가만)
- ✅ Backend 수정 불필요

### 중간 위험 (Medium Risk) - 테스트 필요

- ⚠️ 메시지 파싱 로직 (정규식 기반)
  - **대응**: 단위 테스트 작성
  - **대응**: Fallback 로직 구현

- ⚠️ TypeScript 타입 변경
  - **대응**: 컴파일 에러 체크
  - **대응**: 기존 코드 영향 확인

### 낮은 영향 (Low Impact)

- 기존 기능에 영향 없음
- Guidance 타입이 아니면 기존 로직 유지
- 렌더링 로직 추가만 (기존 조건문 영향 없음)

---

## 12. 결론 (Conclusion)

### 구현 난이도
⭐⭐ (중간)

### 예상 작업 시간
- **타입 정의**: 30분
- **GuidancePage 컴포넌트**: 2시간
- **WebSocket 핸들러 수정**: 1시간
- **테스트 및 디버깅**: 1시간
- **총 소요 시간**: **4.5시간**

### 주요 효과
1. **사용자 경험 향상** ✅
   - 명확한 안내 메시지
   - 시각적으로 눈에 띄는 UI
   - 구조화된 정보 전달

2. **코드 확장성** ✅
   - 신규 Intent 타입 추가 용이
   - Backend-Frontend 분리 유지
   - 재사용 가능한 컴포넌트

3. **디자인 일관성** ✅
   - 기존 ExecutionPlanPage, AnswerDisplay와 유사한 디자인
   - Card, Badge, Alert 등 동일한 UI 컴포넌트 사용

### 권장 사항
✅ **즉시 구현 권장**
- 낮은 위험도
- 높은 사용자 경험 개선
- Backend 수정 불필요
- 기존 시스템과 잘 통합됨

---

**작성일**: 2025-10-17
**작성자**: Claude Code Assistant
**문서 버전**: 1.0
