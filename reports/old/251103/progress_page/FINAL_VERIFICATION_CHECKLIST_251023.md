# 최종 검증 체크리스트 - 4-Stage 구현 전 점검

**작성일**: 2025-10-23
**목적**: 사용자 의견 반영 확인 + 코드 수정 가능 여부 검증

---

## 1️⃣ 사용자 의견 반영 확인

### ✅ 확인된 사용자 요구사항

| 번호 | 요구사항 | 계획서 반영 | 비고 |
|------|----------|------------|------|
| 1 | 기존 3개 파일 완전 삭제 + 새로운 1개 파일 | ✅ 반영 | _old 폴더 백업 |
| 2 | 기존 방식과 혼용 금지 (완전히 새롭게) | ✅ 반영 | 기존 타입 완전 제거 |
| 3 | 4개 스피너 수평 배치 (상단) | ✅ 반영 | 이미지 기준 |
| 4 | 하단에 에이전트 카드들 (동적 1~N개) | ✅ 반영 | Stage 3에서 표시 |
| 5 | 스피너 파일 1~4번 사용 | ✅ 반영 | 1_execution-plan_spinner.gif 등 |
| 6 | 비활성 스피너: 작고 회색 / 활성: 크고 컬러 | ✅ 반영 | 60px/100px, grayscale |
| 7 | 전환 속도 0.15초 (시각 효과) | ✅ 반영 | CSS transition |

### ❌ 놓칠 뻔한 부분 (재확인 필요)

1. **"기존 방식과 혼용 금지"의 정확한 의미**
   - ❓ Message 타입에서 기존 필드(`executionPlan`, `executionSteps`, `responseGenerating`) 완전 제거?
   - ❓ 아니면 새로운 필드만 추가하고 기존 필드는 사용하지 않기만 하면 됨?

2. **WebSocket 핸들러의 기존 로직**
   - ❓ 기존 `plan_ready`, `execution_start` 핸들러를 완전히 삭제하고 새로 작성?
   - ❓ 아니면 기존 핸들러 내부 로직만 수정?

3. **렌더링 조건문**
   - ❓ 기존 3개 조건문(`execution-plan`, `execution-progress`, `response-generating`) 완전 삭제?
   - ❓ 아니면 주석 처리?

---

## 2️⃣ 현재 코드 분석

### 삭제해야 할 코드 (Line 번호 포함)

#### chat-interface.tsx

**Import (Line 12-14)**: ❌ 완전 삭제
```typescript
import { ExecutionPlanPage } from "@/components/execution-plan-page"
import { ExecutionProgressPage } from "@/components/execution-progress-page"
import { ResponseGeneratingPage } from "@/components/response-generating-page"
```

**Message 타입 (Line 44)**: ❌ 완전 삭제
```typescript
type: "execution-plan" | "execution-progress" | "response-generating"
```

**Message 필드 (Line 47-52)**: ❌ 완전 삭제
```typescript
executionPlan?: ExecutionPlan
executionSteps?: ExecutionStep[]
responseGenerating?: {
  message?: string
  phase?: "aggregation" | "response_generation"
}
```

**WebSocket 핸들러 (Line 67-210)**: ❌ 완전 삭제
```typescript
case 'plan_ready': { ... }           // Line 67-97
case 'execution_start': { ... }      // Line 99-135
case 'todo_updated': { ... }         // Line 137-157
case 'response_generating_start': { ... }    // Line 167-192
case 'response_generating_progress': { ... } // Line 194-210
```

**handleSendMessage (Line 428-442)**: ❌ 완전 삭제
```typescript
const planMessage: Message = {
  type: "execution-plan",
  executionPlan: { ... }
}
```

**final_response (Line 215-219)**: ❌ 부분 수정
```typescript
// 현재: 3개 타입 필터링
.filter(m =>
  m.type !== "execution-progress" &&
  m.type !== "execution-plan" &&
  m.type !== "response-generating"
)

// 수정: 1개 타입만 필터링
.filter(m => m.type !== "progress")
```

**렌더링 (Line 521-535)**: ❌ 완전 삭제
```typescript
{message.type === "execution-plan" && message.executionPlan && (
  <ExecutionPlanPage plan={message.executionPlan} />
)}
{message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
  <ExecutionProgressPage ... />
)}
{message.type === "response-generating" && message.responseGenerating && (
  <ResponseGeneratingPage ... />
)}
```

---

## 3️⃣ 추가할 새로운 코드 (Line 위치 포함)

#### chat-interface.tsx

**Import (Line 12 교체)**:
```typescript
// ❌ 기존 3줄 삭제
// ✅ 새로운 1줄 추가
import { ProgressContainer, type ProgressStage } from "@/components/progress-container"
```

**Message 타입 (Line 44 수정)**:
```typescript
// ❌ 기존 삭제
type: "execution-plan" | "execution-progress" | "response-generating"

// ✅ 새로 작성
type: "progress"
```

**Message 필드 (Line 47-52 교체)**:
```typescript
// ❌ 기존 3개 필드 삭제
// ✅ 새로운 1개 필드 추가
progressData?: {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
}
```

**WebSocket 핸들러 (Line 67-210 교체)**:
```typescript
// ✅ 새로운 핸들러 (완전히 새로 작성)
case 'analysis_start': { ... }           // 신규
case 'plan_ready': { ... }               // 완전 새로 작성
case 'execution_start': { ... }          // 완전 새로 작성
case 'todo_updated': { ... }             // 완전 새로 작성
case 'response_generating_start': { ... }    // 완전 새로 작성
case 'response_generating_progress': { ... } // 완전 새로 작성
```

**handleSendMessage (Line 428-442 교체)**:
```typescript
// ✅ 새로운 progress 생성
const progressMessage: Message = {
  type: "progress",
  progressData: {
    stage: "dispatch",
    plan: { ... }
  }
}
```

**렌더링 (Line 521-535 교체)**:
```typescript
// ✅ 새로운 1개 조건문
{message.type === "progress" && message.progressData && (
  <ProgressContainer
    stage={message.progressData.stage}
    plan={message.progressData.plan}
    steps={message.progressData.steps}
    responsePhase={message.progressData.responsePhase}
  />
)}
```

---

## 4️⃣ 코드 수정 가능 여부 검증

### ✅ 수정 가능한 부분

| 항목 | 현재 상태 | 수정 방법 | 난이도 |
|------|----------|----------|--------|
| Import 교체 | 3줄 → 1줄 | Edit tool로 교체 | ⭐ 쉬움 |
| Message 타입 수정 | 6개 → 4개 | Edit tool로 교체 | ⭐ 쉬움 |
| Message 필드 수정 | 3개 → 1개 | Edit tool로 교체 | ⭐⭐ 보통 |
| WebSocket 핸들러 | 기존 로직 → 새 로직 | Edit tool로 교체 (여러 번) | ⭐⭐⭐ 복잡 |
| handleSendMessage | ExecutionPlan → Progress | Edit tool로 교체 | ⭐⭐ 보통 |
| 렌더링 | 3개 조건문 → 1개 | Edit tool로 교체 | ⭐⭐ 보통 |

### ⚠️ 주의해야 할 부분

1. **WebSocket 핸들러 수정**
   - 기존 핸들러가 Line 67-210 (약 143줄)
   - 새로운 핸들러도 비슷한 길이
   - 한 번에 교체하기 어려움 → **case별로 나눠서 수정 필요**

2. **Line 번호 변동**
   - 중간에 코드를 삭제/추가하면 Line 번호가 변경됨
   - 순서대로 수정해야 함: Import → 타입 → 핸들러 → handleSendMessage → 렌더링

3. **TypeScript 컴파일 에러**
   - Message 타입을 바꾸면 기존 코드에서 컴파일 에러 발생
   - 모든 수정이 완료될 때까지 빌드 실패 가능

---

## 5️⃣ 구현 순서 (에러 최소화)

### Phase 1: 새 파일 생성 (기존 코드 영향 없음)
1. ✅ `progress-container.tsx` 생성
2. ✅ 기존 3개 파일 `_old/` 백업

### Phase 2: Import 추가 (기존 유지)
1. ✅ `ProgressContainer` import 추가
2. ❌ 기존 3개 import는 **아직 유지** (에러 방지)

### Phase 3: Message 타입 확장 (기존 유지)
1. ✅ `type`에 `"progress"` 추가 (기존 타입 유지)
2. ✅ `progressData` 필드 추가 (기존 필드 유지)

### Phase 4: 새로운 핸들러 추가 (기존 유지)
1. ✅ `analysis_start` 핸들러 추가
2. ✅ 새로운 `plan_ready` 핸들러 추가 (기존 핸들러 주석 처리)
3. ✅ 새로운 `execution_start` 핸들러 추가 (기존 핸들러 주석 처리)
4. ✅ 새로운 `todo_updated` 핸들러 추가 (기존 핸들러 주석 처리)
5. ✅ 새로운 `response_generating_*` 핸들러 추가 (기존 핸들러 주석 처리)

### Phase 5: 렌더링 추가 (기존 유지)
1. ✅ `progress` 타입 렌더링 추가
2. ❌ 기존 3개 렌더링은 **아직 유지**

### Phase 6: 테스트
1. ✅ `npm run build` 성공 확인
2. ✅ 브라우저에서 4-stage 동작 확인

### Phase 7: 기존 코드 제거 (동작 확인 후)
1. ❌ 기존 3개 import 삭제
2. ❌ 기존 Message 타입 삭제
3. ❌ 기존 핸들러 삭제
4. ❌ 기존 렌더링 삭제
5. ✅ 최종 빌드 테스트

---

## 6️⃣ 잠재적 문제점

### 문제 1: 기존 타입과 새 타입 동시 존재 시

**시나리오**:
```typescript
type: "execution-plan" | "progress"  // 둘 다 존재
executionPlan?: ExecutionPlan        // 기존 필드
progressData?: ProgressData          // 새 필드
```

**문제**:
- 기존 핸들러가 `execution-plan` 메시지 생성
- 새 핸들러가 `progress` 메시지 생성
- **둘 다 화면에 표시됨** (중복)

**해결**:
- Phase 4에서 기존 핸들러를 **주석 처리**하지 말고 **완전 삭제**
- 또는 기존 핸들러 로직을 즉시 수정

### 문제 2: WebSocket 메시지 타입 불일치

**Backend는 계속 동일한 신호 전송**:
- `plan_ready`
- `execution_start`
- `todo_updated`
- `response_generating_start`

**Frontend 핸들러를 바꿔도 Backend는 그대로**:
- Backend 신호는 변경 없음
- Frontend 핸들러만 새로 작성

**결론**: 문제 없음 (Backend 호환)

### 문제 3: DB에 저장된 메시지 복원

**현재 코드 (Line 326-332)**:
```typescript
const formattedMessages = dbMessages.map((msg: any) => ({
  type: msg.role === 'user' ? 'user' : 'bot',
  content: msg.content,
  structuredData: msg.structured_data,
  timestamp: new Date(msg.created_at)
}))
```

**문제**:
- DB에는 `progress` 타입 메시지가 **저장되지 않음**
- `execution-plan`, `execution-progress`, `response-generating`도 DB에 없음
- **영향 없음** (Progress는 실시간만 표시)

**결론**: 문제 없음

---

## 7️⃣ 최종 질문 (사용자 확인 필요)

### ❓ 질문 1: 기존 코드 제거 시점

**Option A**: 새 코드 추가 후 즉시 삭제
```
1. 새 코드 작성
2. 기존 코드 즉시 삭제
3. 빌드 테스트
```
- 장점: 깔끔함
- 단점: 중간에 에러 나면 복구 어려움

**Option B**: 새 코드 테스트 후 삭제
```
1. 새 코드 작성 (기존 코드 유지)
2. 빌드 테스트 + 동작 확인
3. 기존 코드 삭제
4. 최종 빌드 테스트
```
- 장점: 안전함
- 단점: 중간에 코드 혼용

**사용자 선택**: A? B?

---

### ❓ 질문 2: 기존 핸들러 처리

**Option A**: 기존 핸들러 로직 수정
```typescript
case 'plan_ready':
  // ❌ 기존 로직 전부 삭제
  // ✅ 새 로직 작성
  setMessages(prev => prev.map(...))  // progress 업데이트
  break
```

**Option B**: 기존 핸들러 삭제 + 새 핸들러 추가
```typescript
// ❌ case 'plan_ready': { ... } 전부 삭제

// ✅ 완전히 새로 작성
case 'plan_ready':
  setMessages(prev => prev.map(...))
  break
```

**사용자 선택**: A? B?

---

### ❓ 질문 3: Message 타입 필드

**Option A**: 기존 필드 유지 (하위 호환)
```typescript
interface Message {
  type: "user" | "bot" | "progress" | "guidance"

  // 새 필드
  progressData?: { ... }

  // 기존 필드 (사용하지 않지만 유지)
  executionPlan?: ExecutionPlan
  executionSteps?: ExecutionStep[]
  responseGenerating?: { ... }
}
```

**Option B**: 기존 필드 완전 삭제
```typescript
interface Message {
  type: "user" | "bot" | "progress" | "guidance"

  // 새 필드만
  progressData?: { ... }

  // 기존 필드 완전 삭제
}
```

**사용자 선택**: A? B?

---

## 8️⃣ 구현 준비 완료 체크리스트

구현 시작 전 최종 확인:

- [ ] **사용자 의견 반영 확인 완료**
- [ ] **현재 코드 분석 완료** (삭제할 Line 파악)
- [ ] **새 코드 작성 방법 확인 완료**
- [ ] **구현 순서 확정** (Phase 1-7)
- [ ] **질문 1-3 답변 받음**

---

## 9️⃣ 사용자님께

**이 체크리스트를 검토해주시고 다음 사항을 확인 부탁드립니다**:

1. **질문 1**: 기존 코드 제거 시점 - Option A vs B?
2. **질문 2**: 기존 핸들러 처리 - Option A vs B?
3. **질문 3**: Message 타입 필드 - Option A vs B?

**확인해주시면 즉시 구현 시작하겠습니다!**

아니면 "그냥 가장 깔끔한 방식으로 해줘"라고 하시면 제가 판단해서 진행하겠습니다.
