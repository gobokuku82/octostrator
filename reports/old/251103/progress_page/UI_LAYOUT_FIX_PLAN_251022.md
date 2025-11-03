# UI 레이아웃 수정 계획서 (v2)

**작성일**: 2025-10-22
**목적**: 비율 기반 레이아웃으로 전환 - 스피너 30% : 콘텐츠 70%
**업데이트**: 사용자 스크린샷 분석 반영

---

## 🎯 사용자 요구사항 (스크린샷 분석)

### 이미지 분석 결과

```
┌─────────────────────────────────────────────────┐ ← 노란색 박스 (전체 Card)
│ [제목: AI 응답 생성 중]                         │
│ [설명: 최종 답변을 생성하고 있습니다...]        │
│                                                 │
│ ┌───────────┐ ┌─────────────────────────────┐  │
│ │           │ │ ✓ 데이터 수집 완료          │  │
│ │  Spinner  │ │ ✓ 정보 정리 중              │  │
│ │  (GIF)    │ │ ○ 최종 답변 생성 중         │  │
│ │           │ │                             │  │
│ │   30%     │ │         70%                 │  │
│ │           │ │      (콘텐츠 영역)           │  │
│ └───────────┘ └─────────────────────────────┘  │
└─────────────────────────────────────────────────┘
  ↑ 빨간색       ↑ 파란색
```

**핵심 요구사항**:
1. ✅ **비율**: 스피너 30% : 콘텐츠 70%
2. ✅ **정렬**: 양쪽 모두 상단 정렬 (items-start)
3. ✅ **여백**: 하단 여백 없음 (노란색 박스가 콘텐츠에 딱 맞게)
4. ✅ **간격**: 스피너와 콘텐츠 사이 적절한 gap

---

## 🔍 현재 문제 분석

### 근본 원인: 잘못된 레이아웃 전략

**현재 코드 (문제)**:
```tsx
// 고정 픽셀 크기 + flex-1 조합
<div className="flex items-start">
  <div className="flex-shrink-0 pl-2">
    <img className="w-[360px] h-[360px]" />  // ❌ 고정 360px
  </div>
  <div className="flex-1 pl-4 pr-6 pb-6">   // ❌ flex-1 (나머지 전부 차지)
    {/* 콘텐츠 */}
  </div>
</div>
```

**문제점**:
1. 고정 픽셀 크기로는 반응형 비율 구현 불가
2. `flex-1`은 "나머지 전부"를 의미 (70% 고정 불가)
3. `pb-6` 패딩이 불필요한 하단 공백 생성
4. 화면 크기 변경 시 30:70 비율 유지 불가

**증거**:
- ExecutionPlanPage line 42-48
- ExecutionProgressPage line 58-64
- ResponseGeneratingPage line 49-55

---

### 해결 방향: 비율 기반 레이아웃

**목표 코드**:
```tsx
// 퍼센트 비율 기반
<div className="flex items-start gap-4">
  <div className="w-[30%] flex-shrink-0">   // ✅ 정확히 30%
    <img className="w-full h-auto" />        // ✅ 부모 너비에 맞춤
  </div>
  <div className="w-[70%] flex-shrink-0">   // ✅ 정확히 70%
    {/* 콘텐츠 */}
  </div>
</div>
```

**장점**:
1. 정확한 30:70 비율 보장
2. 반응형 대응 (max-w-5xl 범위 내에서)
3. 하단 패딩 제거로 깔끔한 마무리
4. gap으로 간격 일관성 유지

---

## ✅ 제안된 해결책 (비율 기반 레이아웃)

### 핵심 변경사항

**1단계: 제목 영역 패딩 조정**
```tsx
// Before
<div className="px-6 pt-6 pb-4">

// After
<div className="px-6 pt-6 pb-3">  // 16px → 12px (약간 축소)
```

**2단계: GIF+콘텐츠 영역 비율 기반으로 전환**
```tsx
// Before (고정 픽셀 + flex-1)
<div className="flex items-start">
  <div className="flex-shrink-0 pl-2">
    <img
      src="/animation/spinner/3response-generating_spinner.gif"
      alt="generating response"
      className="w-[360px] h-[360px] object-contain"
    />
  </div>
  <div className="flex-1 pl-4 pr-6 pb-6">
    {/* 콘텐츠 */}
  </div>
</div>

// After (30:70 비율)
<div className="flex items-start gap-4 px-6 pb-6">
  <div className="w-[30%] flex-shrink-0">
    <img
      src="/animation/spinner/3response-generating_spinner.gif"
      alt="generating response"
      className="w-full h-auto object-contain"
    />
  </div>
  <div className="w-[70%] flex-shrink-0">
    {/* 콘텐츠 */}
  </div>
</div>
```

### 상세 변경 포인트

**A. 스피너 영역 (30%)**
- ❌ `flex-shrink-0 pl-2` → ✅ `w-[30%] flex-shrink-0`
- ❌ `w-[360px] h-[360px]` → ✅ `w-full h-auto`
- 이유: 부모 너비의 30%를 정확히 차지, GIF는 부모에 맞춰 자동 크기 조정

**B. 콘텐츠 영역 (70%)**
- ❌ `flex-1 pl-4 pr-6 pb-6` → ✅ `w-[70%] flex-shrink-0`
- 이유: 정확히 70% 차지, 패딩은 부모 컨테이너로 이동

**C. 부모 컨테이너 패딩**
- ✅ `gap-4`: 스피너-콘텐츠 간 16px 간격
- ✅ `px-6 pb-6`: 좌우 및 하단 패딩을 부모로 이동
- 이유: 일관된 여백 관리

**D. 상단 정렬**
- ✅ `items-start` 유지: 양쪽 모두 상단 정렬

---

## 📋 구현 계획

### Step 1: execution-plan-page.tsx 수정

**파일**: `frontend/components/execution-plan-page.tsx`

**변경 1: 제목 영역 패딩**
```tsx
// Line 29
- <div className="px-6 pt-6 pb-4">
+ <div className="px-6 pt-6 pb-3">
```

**변경 2: GIF+콘텐츠 영역 구조**
```tsx
// Line 42-48 (전체 교체)
- <div className="flex items-start">
-   <div className="flex-shrink-0 pl-2">
-     <img
-       src="/animation/spinner/1_execution-plan_spinner.gif"
-       alt="planning"
-       className="w-[360px] h-[360px] object-contain"
-     />
-   </div>
-   <div className="flex-1 pl-4 pr-6 pb-6">

+ <div className="flex items-start gap-4 px-6 pb-6">
+   <div className="w-[30%] flex-shrink-0">
+     <img
+       src="/animation/spinner/1_execution-plan_spinner.gif"
+       alt="planning"
+       className="w-full h-auto object-contain"
+     />
+   </div>
+   <div className="w-[70%] flex-shrink-0">
```

---

### Step 2: execution-progress-page.tsx 수정

**파일**: `frontend/components/execution-progress-page.tsx`

**변경 1: 제목 영역 패딩**
```tsx
// Line 38
- <div className="px-6 pt-6 pb-4">
+ <div className="px-6 pt-6 pb-3">
```

**변경 2: GIF+콘텐츠 영역 구조**
```tsx
// Line 58-64 (전체 교체)
- <div className="flex items-start">
-   <div className="flex-shrink-0 pl-2">
-     <img
-       src="/animation/spinner/2_execution-progress_spinner.gif"
-       alt="executing"
-       className="w-[360px] h-[360px] object-contain"
-     />
-   </div>
-   <div className="flex-1 pl-4 pr-6 pb-6">

+ <div className="flex items-start gap-4 px-6 pb-6">
+   <div className="w-[30%] flex-shrink-0">
+     <img
+       src="/animation/spinner/2_execution-progress_spinner.gif"
+       alt="executing"
+       className="w-full h-auto object-contain"
+     />
+   </div>
+   <div className="w-[70%] flex-shrink-0">
```

---

### Step 3: response-generating-page.tsx 수정

**파일**: `frontend/components/response-generating-page.tsx`

**변경 1: 제목 영역 패딩**
```tsx
// Line 38
- <div className="px-6 pt-6 pb-4">
+ <div className="px-6 pt-6 pb-3">
```

**변경 2: GIF+콘텐츠 영역 구조**
```tsx
// Line 49-55 (전체 교체)
- <div className="flex items-start">
-   <div className="flex-shrink-0 pl-2">
-     <img
-       src="/animation/spinner/3response-generating_spinner.gif"
-       alt="generating response"
-       className="w-[360px] h-[360px] object-contain"
-     />
-   </div>
-   <div className="flex-1 pl-4 pr-6 pb-6">

+ <div className="flex items-start gap-4 px-6 pb-6">
+   <div className="w-[30%] flex-shrink-0">
+     <img
+       src="/animation/spinner/3response-generating_spinner.gif"
+       alt="generating response"
+       className="w-full h-auto object-contain"
+     />
+   </div>
+   <div className="w-[70%] flex-shrink-0">
```

---

### Step 4: 빌드 및 최종 검증

**빌드 명령**:
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\frontend
npm run build
```

**검증 체크리스트**:
- [ ] TypeScript 컴파일 에러 없음
- [ ] 3개 파일 모두 정상 빌드
- [ ] 브라우저 하드 리프레시 (Ctrl+Shift+R)
- [ ] 30:70 비율 정확히 적용
- [ ] 양쪽 상단 정렬 확인
- [ ] 하단 공백 제거 확인
- [ ] 스피너-콘텐츠 간격 적절

---

## 🔄 Before / After 비교

### Before (현재 - 고정 픽셀 기반)

```
Card (max-w-5xl = 1024px)
┌─────────────────────────────────────────────┐
│ [제목]                         px-6, pt-6   │
│ [설명]                         pb-4 (16px)  │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐  [콘텐츠 영역]                │
│  │          │  flex-1 (나머지 전부)          │
│  │   GIF    │  pl-4, pr-6                   │
│  │  360px   │  pb-6 (24px) ← 문제!          │
│  │  고정    │                               │
│  └──────────┘                               │
│               ↑ 비율 고정 불가               │
│               ↑ 불필요한 하단 공백           │
└─────────────────────────────────────────────┘
   ↑ pl-2로 왼쪽에 약간 여백
```

**문제점**:
- GIF 360px 고정 → 반응형 비율 불가
- flex-1로 나머지 전부 차지 → 70% 고정 불가
- pb-6 하단 패딩 → 불필요한 공백 발생

---

### After (수정 후 - 30:70 비율 기반)

```
Card (max-w-5xl = 1024px)
┌─────────────────────────────────────────────┐
│ [제목]                         px-6, pt-6   │
│ [설명]                         pb-3 (12px)  │
├─────────────────────────────────────────────┤
│ ┌─ px-6, pb-6 (전체 패딩) ─────────────────┐│
│ │                                           ││
│ │ ┌─────────┐ ← gap-4 → ┌─────────────┐   ││
│ │ │         │            │             │   ││
│ │ │  GIF    │            │  콘텐츠     │   ││
│ │ │  30%    │            │  70%        │   ││
│ │ │ w-full  │            │             │   ││
│ │ │ h-auto  │            │             │   ││
│ │ └─────────┘            └─────────────┘   ││
│ │                                           ││
│ └───────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
   ↑ 정확한 30:70 비율
   ↑ 상단 정렬 (items-start)
   ↑ 하단 공백 최소화
```

**개선점**:
- ✅ 정확한 30:70 비율 보장
- ✅ 반응형 대응 (w-[30%], w-[70%])
- ✅ 깔끔한 패딩 구조 (부모에서 일괄 관리)
- ✅ gap-4로 일관된 간격 유지
- ✅ 하단 공백 최소화 (pb-6만 적용)

**수치 비교**:
- 제목 하단: pb-4 (16px) → pb-3 (12px)
- GIF 영역: 360px 고정 → 30% 비율 (약 307px @ 1024px)
- 콘텐츠 영역: flex-1 (불확정) → 70% 비율 (약 717px @ 1024px)
- 간격: pl-4 (16px) → gap-4 (16px) 유지

---

## 🚨 위험 요소 및 대응책

### 위험 1: GIF 비율 왜곡

**원인**: `w-full h-auto`로 변경 시 GIF가 찌그러질 수 있음

**대응책**:
- `object-contain` 유지로 aspect ratio 보존
- GIF 파일들이 정사각형(1:1)이므로 자동으로 30% 너비 내에서 최대 크기로 조정됨
- 30% 영역 내에서 중앙 정렬 필요 시 부모에 `flex items-center justify-center` 추가 가능

**검증 방법**:
- 실제 브라우저에서 GIF가 찌그러지지 않는지 확인
- 필요시 `aspect-square` 클래스 추가

---

### 위험 2: 작은 화면에서 30% 영역이 너무 좁아질 수 있음

**원인**: max-w-5xl (1024px) 미만 화면에서 30%가 매우 좁아짐

**현황**:
- 1024px 화면: 30% = 약 307px ✅ 충분
- 768px 화면: 30% = 약 230px ⚠️ 작아짐
- 640px 화면: 30% = 약 192px ❌ 너무 작음

**대응책** (Phase 2에서 고려):
```tsx
// 필요 시 반응형 비율 조정
<div className="w-[30%] md:w-[30%] sm:w-[35%] flex-shrink-0">
```
- 현재는 고정 30%로 진행
- 사용자 피드백에 따라 반응형 조정

---

### 위험 3: 페이지별 콘텐츠 높이 차이

**현황**:
- ExecutionPlanPage: 스켈레톤 2-3줄 (낮음)
- ExecutionProgressPage: ProgressBar + StepItem 리스트 (가변, 높을 수 있음)
- ResponseGeneratingPage: 3단계 진행 표시 (중간)

**대응책**:
- `items-start` 사용으로 양쪽 모두 상단 정렬
- 콘텐츠가 GIF보다 길면 자연스럽게 Card가 늘어남
- GIF는 h-auto로 비율 유지하며 30% 너비에 맞춤
- 최소/최대 높이 제한 없이 자연스럽게 조정

---

### 위험 4: 간격(gap) 너비 부족

**원인**: gap-4 (16px)가 너무 좁을 수 있음

**대응책**:
- 우선 gap-4 (16px)로 시작
- 시각적으로 답답하면 `gap-6` (24px)로 조정
- 사용자 스크린샷 기준으로 판단

---

## ✅ 구현 체크리스트

### 파일 수정
- [ ] execution-plan-page.tsx line 29: `pb-4` → `pb-3`
- [ ] execution-plan-page.tsx line 42-48: 비율 기반 레이아웃으로 전체 교체
- [ ] execution-progress-page.tsx line 38: `pb-4` → `pb-3`
- [ ] execution-progress-page.tsx line 58-64: 비율 기반 레이아웃으로 전체 교체
- [ ] response-generating-page.tsx line 38: `pb-4` → `pb-3`
- [ ] response-generating-page.tsx line 49-55: 비율 기반 레이아웃으로 전체 교체

### 빌드 검증
- [ ] `npm run build` 성공
- [ ] TypeScript 컴파일 에러 없음
- [ ] 브라우저 하드 리프레시 (Ctrl+Shift+R)

### 시각적 검증
- [ ] 스피너 30% : 콘텐츠 70% 비율 정확히 적용
- [ ] 양쪽 모두 상단 정렬 (items-start) 확인
- [ ] 하단 공백 최소화 확인
- [ ] GIF 비율 왜곡 없음 (object-contain 작동)
- [ ] 스피너-콘텐츠 간격 적절 (gap-4)
- [ ] 3개 페이지 일관성 유지

### 추가 조정 (필요시)
- [ ] gap-4 → gap-6 변경 필요 여부 (간격 부족 시)
- [ ] pb-3 → pb-2 변경 필요 여부 (제목-GIF 간격 조정)
- [ ] GIF 중앙 정렬 필요 여부 (30% 영역 내)

---

## 📊 예상 결과

### 정량적 개선
- **비율**: 정확히 30:70 유지 (반응형)
- **제목 하단**: pb-4 (16px) → pb-3 (12px) - 4px 감소
- **GIF 크기**: 360px 고정 → 30% 비율 (약 307px @ 1024px)
- **콘텐츠 영역**: flex-1 → 70% 비율 (약 717px @ 1024px)
- **간격**: gap-4 (16px) 일관성 유지

### 정성적 개선
- ✅ 사용자 요구사항 정확히 반영 (스크린샷 기준)
- ✅ 반응형 대응 (화면 크기에 따라 비율 유지)
- ✅ 깔끔한 코드 구조 (부모에서 패딩 일괄 관리)
- ✅ 하단 공백 최소화 (pb-6만 적용)
- ✅ 3개 페이지 완벽한 일관성

### 위험도
- 전체: ⭐⭐ 낮음-중간
- 레이아웃 구조 변경이지만 안전한 접근
- TypeScript 타입 변경 없음
- 즉시 롤백 가능 (Git)

---

## 🎯 결론

**핵심 전략**: 고정 픽셀 → 비율 기반 레이아웃 전환

**기대 효과**:
1. ✅ 정확한 30:70 비율 보장
2. ✅ 사용자 스크린샷과 일치하는 레이아웃
3. ✅ 반응형 대응 (max-w-5xl 범위 내)
4. ✅ 깔끔한 코드 구조

**예상 소요 시간**: 10-15분
**성공 확률**: 90% 이상 (비율 기반 접근이 정확)

---

## 📝 최종 요약

**변경 핵심**:
```tsx
// From: 고정 픽셀 + flex-1
<div className="flex items-start">
  <div className="flex-shrink-0 pl-2">
    <img className="w-[360px] h-[360px]" />
  </div>
  <div className="flex-1 pl-4 pr-6 pb-6">

// To: 30:70 비율 + 부모 패딩
<div className="flex items-start gap-4 px-6 pb-6">
  <div className="w-[30%] flex-shrink-0">
    <img className="w-full h-auto object-contain" />
  </div>
  <div className="w-[70%] flex-shrink-0">
```

**사용자 요구사항 충족**:
- [x] 스피너 30% : 콘텐츠 70% 비율
- [x] 양쪽 상단 정렬 (items-start)
- [x] 하단 공백 최소화
- [x] 적절한 간격 (gap-4)

---

**다음 단계**: 사용자 승인 후 즉시 구현 시작
