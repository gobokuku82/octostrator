# Progress Page 레이아웃 개선 계획서

**작성일**: 2025-10-28
**목표**: Progress Page를 일반 챗봇 답변 페이지와 동일한 레이아웃으로 변경하여 일체감 향상

---

## 1. 문제 상황 분석

### 1.1 현재 문제점

#### 문제 1: 챗봇 아이콘 미표시
- **현상**: Progress page 작동 중에는 챗봇 캐릭터 이미지가 보이지 않음
- **원인**: `chat-interface.tsx` Line 819-837에서 progress 메시지는 아이콘 없이 바로 `<ProgressContainer>` 렌더링
- **영향**: 사용자가 "누가 말하는지" 인지하기 어려움

#### 문제 2: 레이아웃 불일치
- **현상**: Progress page가 챗봇 내부 영역을 벗어나서 화면 너비를 가득 채움
- **원인**:
  - Progress: `max-w-5xl` (1280px) 사용 (progress-container.tsx Line 137)
  - Bot 답변: `max-w-[80%]` 사용 (chat-interface.tsx Line 844)
- **영향**: 일반 답변과 시각적 일관성 부족, UI가 불안정해 보임

#### 문제 3: 아이콘 영역 부재
- **현상**: Progress page는 왼쪽 여백 없이 바로 시작
- **원인**: Bot 메시지와 달리 아이콘을 위한 `flex gap-2` 구조가 없음
- **영향**: 왼쪽 정렬이 일반 답변과 다름

---

## 2. 코드 세부 분석

### 2.1 현재 Progress 렌더링 구조

**파일**: `frontend/components/chat-interface.tsx`

#### Line 819-837: Progress 메시지 렌더링 (❌ 문제 코드)

```tsx
{message.type === "progress" && (
  threeLayerProgress ? (
    <ProgressContainer
      mode="three-layer"
      progressData={{
        ...threeLayerProgress,
        supervisorProgress: animatedSupervisorProgress
      }}
    />
  ) : message.progressData ? (
    <ProgressContainer
      mode="legacy"
      stage={message.progressData.stage}
      plan={message.progressData.plan}
      steps={message.progressData.steps}
      responsePhase={message.progressData.responsePhase}
      reusedTeams={message.progressData.reusedTeams}
    />
  ) : null
)}
```

**문제점**:
- 아이콘 없이 바로 `<ProgressContainer>` 렌더링
- 레이아웃 구조가 일반 메시지와 완전히 다름
- `max-w-*` 제한 없음

---

### 2.2 현재 Bot 답변 렌더링 구조

#### Line 842-873: Bot 메시지 렌더링 (✅ 올바른 구조)

```tsx
{(message.type === "user" || message.type === "bot") && (
  <div className="flex justify-start">
    <div className="flex gap-2 max-w-[80%]">
      {/* 1. 챗봇 아이콘 (128x128px) */}
      <div className="flex-shrink-0 w-32 h-32">
        <Image
          src="/images/holmesnyangz.png"
          alt="Holmes Nyangz"
          width={128}
          height={128}
          className="rounded-full object-cover"
          priority
        />
      </div>

      {/* 2. 답변 내용 */}
      {message.type === "bot" && message.structuredData ? (
        <AnswerDisplay
          sections={message.structuredData.sections}
          metadata={message.structuredData.metadata}
        />
      ) : (
        <Card className="p-3">
          <p className="text-sm">{message.content}</p>
        </Card>
      )}
    </div>
  </div>
)}
```

**좋은 점**:
- ✅ 챗봇 아이콘 포함 (`w-32 h-32`)
- ✅ `flex gap-2` 구조로 아이콘과 내용 분리
- ✅ `max-w-[80%]`로 너비 제한
- ✅ `justify-start`로 왼쪽 정렬

---

### 2.3 ProgressContainer 내부 구조

**파일**: `frontend/components/progress-container.tsx`

#### Line 136-159: ThreeLayerProgress 컴포넌트

```tsx
function ThreeLayerProgress({ progressData }: { progressData: ThreeLayerProgressData }) {
  return (
    <div className="flex justify-start mb-2">
      <div className="flex items-start gap-3 max-w-5xl w-full">
        <Card className="p-3 bg-card border flex-1">
          {/* Layer 1: Supervisor Progress Bar */}
          <SupervisorProgressBar ... />

          {/* Layer 2: Agent Steps */}
          {activeAgents && activeAgents.length > 0 && (
            <div className="mt-3 space-y-2">
              {activeAgents.map(agent => (
                <AgentStepsCard key={agent.agentName} agentProgress={agent} />
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
```

**문제점**:
- ❌ `max-w-5xl` (1280px) - 너무 넓음
- ❌ 아이콘을 위한 공간 없음
- ❌ Bot 메시지와 다른 외부 래퍼 구조

---

## 3. 해결 방안

### 3.1 Option A: chat-interface.tsx 수정 (✅ 추천)

**장점**:
- Progress만 수정하면 되므로 영향 범위 최소화
- ProgressContainer는 그대로 재사용 가능
- Legacy 모드도 동시에 수정 가능

**단점**:
- chat-interface.tsx가 약간 복잡해짐

**구현 방법**:
```tsx
{message.type === "progress" && (
  // 🆕 Bot 메시지와 동일한 구조 적용
  <div className="flex justify-start">
    <div className="flex gap-2 max-w-[80%]">
      {/* 1. 챗봇 아이콘 */}
      <div className="flex-shrink-0 w-32 h-32">
        <Image
          src="/images/holmesnyangz.png"
          alt="Holmes Nyangz"
          width={128}
          height={128}
          className="rounded-full object-cover"
          priority
        />
      </div>

      {/* 2. Progress Container */}
      <div className="flex-1">
        {threeLayerProgress ? (
          <ProgressContainer mode="three-layer" progressData={{...}} />
        ) : message.progressData ? (
          <ProgressContainer mode="legacy" ... />
        ) : null}
      </div>
    </div>
  </div>
)}
```

---

### 3.2 Option B: progress-container.tsx 수정

**장점**:
- ProgressContainer가 자체적으로 완전한 레이아웃 포함
- 다른 곳에서 재사용 시에도 일관된 레이아웃

**단점**:
- ProgressContainer에 아이콘 로직 추가 필요
- 다른 컨텍스트에서 사용 시 아이콘이 불필요할 수 있음
- 영향 범위가 더 넓음

**구현 방법**:
```tsx
function ThreeLayerProgress({ progressData, showBotIcon = true }: { ... }) {
  return (
    <div className="flex justify-start mb-2">
      <div className="flex gap-2 max-w-[80%]">
        {/* 🆕 챗봇 아이콘 추가 */}
        {showBotIcon && (
          <div className="flex-shrink-0 w-32 h-32">
            <Image src="/images/holmesnyangz.png" ... />
          </div>
        )}

        {/* Progress 내용 */}
        <div className="flex-1">
          <Card className="p-3 bg-card border">
            <SupervisorProgressBar ... />
            {/* ... */}
          </Card>
        </div>
      </div>
    </div>
  )
}
```

---

## 4. 최종 권장 방안: Option A

**선택 이유**:
1. **관심사 분리**: ProgressContainer는 progress 표시만 담당, 레이아웃은 chat-interface가 담당
2. **일관성**: Bot 메시지와 동일한 레이아웃 구조 재사용
3. **유연성**: 다른 곳에서 ProgressContainer를 아이콘 없이 사용 가능
4. **영향 범위**: chat-interface.tsx만 수정하면 됨

---

## 5. 구현 계획

### Phase 1: chat-interface.tsx 수정

#### Step 1: Progress 메시지 레이아웃 변경

**파일**: `frontend/components/chat-interface.tsx`
**위치**: Line 819-837

**변경 전**:
```tsx
{message.type === "progress" && (
  threeLayerProgress ? (
    <ProgressContainer mode="three-layer" progressData={{...}} />
  ) : ...
)}
```

**변경 후**:
```tsx
{message.type === "progress" && (
  <div className="flex justify-start">
    <div className="flex gap-2 max-w-[80%]">
      {/* 챗봇 아이콘 */}
      <div className="flex-shrink-0 w-32 h-32">
        <Image
          src="/images/holmesnyangz.png"
          alt="Holmes Nyangz"
          width={128}
          height={128}
          className="rounded-full object-cover"
          priority
        />
      </div>

      {/* Progress Container */}
      <div className="flex-1">
        {threeLayerProgress ? (
          <ProgressContainer
            mode="three-layer"
            progressData={{
              ...threeLayerProgress,
              supervisorProgress: animatedSupervisorProgress
            }}
          />
        ) : message.progressData ? (
          <ProgressContainer
            mode="legacy"
            stage={message.progressData.stage}
            plan={message.progressData.plan}
            steps={message.progressData.steps}
            responsePhase={message.progressData.responsePhase}
            reusedTeams={message.progressData.reusedTeams}
          />
        ) : null}
      </div>
    </div>
  </div>
)}
```

**예상 소요 시간**: 5분

---

### Phase 2: progress-container.tsx 내부 너비 조정

#### Step 2: ThreeLayerProgress max-width 제거

**파일**: `frontend/components/progress-container.tsx`
**위치**: Line 136-159

**변경 전**:
```tsx
<div className="flex justify-start mb-2">
  <div className="flex items-start gap-3 max-w-5xl w-full">
    <Card className="p-3 bg-card border flex-1">
```

**변경 후**:
```tsx
<div className="w-full">
  <Card className="p-3 bg-card border">
```

**이유**:
- 외부에서 `max-w-[80%]`로 제한하므로 내부에서는 `w-full`만 있으면 됨
- `justify-start`도 외부에서 처리하므로 불필요
- `flex items-start gap-3`도 내부에 아이콘이 없으므로 불필요

**예상 소요 시간**: 2분

---

#### Step 3: LegacyProgress max-width 제거

**파일**: `frontend/components/progress-container.tsx`
**위치**: Line 401-403

**변경 전**:
```tsx
<div className="flex justify-start mb-2">
  <div className="flex items-start gap-3 max-w-5xl w-full">
    <Card className="p-3 bg-card border flex-1">
```

**변경 후**:
```tsx
<div className="w-full">
  <Card className="p-3 bg-card border">
```

**예상 소요 시간**: 2분

---

### Phase 3: 테스트

#### Test Case 1: 3-Layer Progress 표시 확인
- [ ] 질문 전송 시 챗봇 아이콘 표시됨
- [ ] Progress bar가 아이콘 오른쪽에 표시됨
- [ ] 너비가 일반 답변과 동일 (화면의 80% 이내)
- [ ] 왼쪽 정렬이 일반 답변과 동일

#### Test Case 2: Legacy Progress 표시 확인
- [ ] 이전 메시지 로딩 시 챗봇 아이콘 표시됨
- [ ] Legacy progress가 올바르게 표시됨

#### Test Case 3: 반응형 확인
- [ ] 모바일 화면에서도 레이아웃 유지
- [ ] 태블릿 화면에서도 레이아웃 유지

**예상 소요 시간**: 10분

---

## 6. Before & After 비교

### Before (현재)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  [전체 진행률 85%]  ← 챗봇 아이콘 없음, 화면 가득 채움     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │
│  [접수] [분석] [실행] [완료]                               │
│                                                             │
│  🔍 검색 에이전트                                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━                                │
│  ✓ 쿼리 생성                                               │
│  ● 데이터 검색                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**문제점**:
- ❌ 챗봇 아이콘 없음
- ❌ 화면 너비를 가득 채움 (max-w-5xl = 1280px)
- ❌ 일반 답변과 다른 레이아웃

---

### After (개선 후)

```
┌─────────────────────────────────────────────┐
│                                             │
│  🐱     [전체 진행률 85%]  ← 아이콘 추가    │
│  탐정    ━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│  고양이   [접수] [분석] [실행] [완료]       │
│ (128px)                                     │
│         🔍 검색 에이전트                    │
│         ━━━━━━━━━━━━━━━━━                │
│         ✓ 쿼리 생성                         │
│         ● 데이터 검색                       │
│                                             │
└─────────────────────────────────────────────┘
          ↑ 화면의 80% 이내 (max-w-[80%])
```

**개선점**:
- ✅ 챗봇 아이콘 표시 (128x128px)
- ✅ 화면 너비의 80% 이내로 제한
- ✅ 일반 답변과 동일한 레이아웃 구조

---

## 7. 예상 효과

### 7.1 사용자 경험 개선
- **일관성**: Progress와 답변이 동일한 레이아웃으로 일체감 향상
- **명확성**: 챗봇 아이콘으로 "누가 말하는지" 명확히 인지
- **안정감**: 화면 너비 제한으로 UI가 안정적으로 보임

### 7.2 개발 측면
- **유지보수성**: 레이아웃 구조가 통일되어 수정 용이
- **확장성**: 향후 다른 메시지 타입 추가 시 동일한 패턴 적용 가능
- **코드 품질**: 관심사 분리 (chat-interface = 레이아웃, progress-container = 내용)

---

## 8. 리스크 및 대응

### 리스크 1: 모바일에서 아이콘이 너무 큼 (128px)
**대응**: CSS media query로 모바일에서는 64px로 축소
```tsx
<div className="flex-shrink-0 w-32 h-32 md:w-16 md:h-16">
```

### 리스크 2: Progress 너비가 너무 좁아질 수 있음
**대응**: `max-w-[80%]` 대신 `max-w-[85%]` 또는 `max-w-4xl` 사용 가능

### 리스크 3: 기존 progress 데이터가 손상될 수 있음
**대응**: 변경은 렌더링 부분만이므로 데이터 구조는 영향 없음

---

## 9. 체크리스트

### 구현 전
- [ ] 현재 progress 레이아웃 스크린샷 저장
- [ ] bot 답변 레이아웃 스크린샷 저장
- [ ] 비교 분석 완료

### 구현 중
- [ ] chat-interface.tsx Line 819-837 수정
- [ ] progress-container.tsx Line 136-159 수정 (ThreeLayerProgress)
- [ ] progress-container.tsx Line 401-403 수정 (LegacyProgress)
- [ ] 코드 리뷰

### 구현 후
- [ ] Desktop 테스트
- [ ] Tablet 테스트
- [ ] Mobile 테스트
- [ ] Before/After 스크린샷 비교
- [ ] 문서 업데이트 (CHATBOT_COMPLETE_FLOW_MANUAL.md)
- [ ] 패치 노트 작성 (251028_progress_layout_fix_v1.3.md)

---

## 10. 총 예상 소요 시간

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| Phase 1 | chat-interface.tsx 수정 | 5분 |
| Phase 2 | progress-container.tsx 수정 (2곳) | 4분 |
| Phase 3 | 테스트 및 확인 | 10분 |
| **총계** | | **19분** |

---

## 11. 참고 파일

- `frontend/components/chat-interface.tsx` - 메시지 렌더링 로직
- `frontend/components/progress-container.tsx` - Progress UI 컴포넌트
- `frontend/public/images/holmesnyangz.png` - 챗봇 캐릭터 이미지
- `reports/Manual/CHATBOT_COMPLETE_FLOW_MANUAL.md` - 시스템 매뉴얼

---

**계획서 작성 완료**: 2025-10-28
**다음 단계**: 사용자 승인 후 구현 시작
