# HITL Progress 지속 표시 테스트 가이드

**작성일**: 2025-10-28
**버전**: 1.0
**목적**: Document Executor HITL 워크플로우 Progress 표시 개선 테스트

---

## 📋 변경 사항 요약

### 수정된 파일

1. **`frontend/components/lease_contract/lease_contract_page.tsx`**
   - Props에 `onClosePopup` 추가 (Progress 유지)
   - `handleApprove`, `handleModify`, `handleReject`에서 `onClosePopup()` 호출
   - X 버튼은 기존 `onClose` 유지 (Progress 삭제)

2. **`frontend/components/chat-interface.tsx`**
   - `onClosePopup` 핸들러 추가 (팝업만 닫기, Progress 유지)
   - `onClose` 핸들러 유지 (X 버튼용, Progress 삭제)

### 핵심 변경 로직

**변경 전:**
```typescript
// LeaseContractPage
const handleApprove = () => {
  onApprove()
  onClose()  // ❌ Progress 삭제
}

// ChatInterface
onClose={() => {
  setShowLeaseContract(false)
  setLeaseContractData(null)
  setMessages(prev => prev.filter(m => m.type !== "progress"))  // ❌ 삭제
}}
```

**변경 후:**
```typescript
// LeaseContractPage
const handleApprove = () => {
  onApprove()
  onClosePopup()  // ✅ Progress 유지
}

// ChatInterface
onClosePopup={() => {
  setShowLeaseContract(false)
  setLeaseContractData(null)
  // Progress는 삭제하지 않음! ✅
}}

onClose={() => {
  // X 버튼용
  setShowLeaseContract(false)
  setLeaseContractData(null)
  setMessages(prev => prev.filter(m => m.type !== "progress"))  // ❌ 삭제
}}
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 정상 승인 플로우 (핵심) ⭐⭐⭐

**목적**: "승인" 후 Progress가 유지되고 최종 답변까지 표시되는지 확인

**테스트 케이스:** "임대차 계약서 작성해줘"

**예상 동작:**

```
1. 사용자 입력: "임대차 계약서 작성해줘"
   ✅ Progress 표시 시작
      - 접수 (5%)
      - 분석 (10%)
      - 작업 계획 표시
      - 실행 (30%)

2. Interrupt 발생 (약 5초 후)
   ✅ 팝업 표시: "계약서 작성을 위해 승인이 필요합니다"
   ✅ Progress는 배경에 유지됨 (가려져 있지만 존재)

3. 사용자 "승인" 버튼 클릭
   ✅ 팝업 닫힘
   ✅ Progress 다시 표시됨 (핵심!)
   ✅ Progress 업데이트:
      - "결과를 정리하고 있습니다" (75%)
      - "최종 답변을 생성하고 있습니다" (85%)
      - "답변 내용을 작성하고 있습니다" (87%)
      [약 7초 소요 - LLM 작업]
      - "답변을 검증하고 있습니다" (90%)
      - "답변 생성 완료" (95%)

4. 최종 답변 수신
   ✅ Progress 제거
   ✅ 답변 표시
```

**체크 포인트:**

- [ ] Progress가 "승인" 후에도 계속 표시됨
- [ ] Progress가 75% → 85% → 87% → 90% → 95%로 업데이트됨
- [ ] 사용자가 7초간 진행 상황을 볼 수 있음
- [ ] final_response 수신 시 Progress가 자동으로 제거됨

**콘솔 로그 확인:**

```
[LeaseContractPage] Approve - keeping progress visible
[ChatInterface] Sending approve response
[ChatInterface] Closing popup only (keeping progress visible)
```

---

### 시나리오 2: X 버튼으로 강제 종료 ⭐⭐

**목적**: X 버튼으로 닫을 때 Progress가 제거되는지 확인

**테스트 케이스:** "임대차 계약서 작성해줘" → Interrupt → X 버튼 클릭

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시

2. Interrupt 발생
   ✅ 팝업 표시

3. 사용자 X 버튼 클릭 (우측 상단)
   ✅ 팝업 닫힘
   ✅ Progress 제거됨 (의도적)
   ⚠️  Backend는 계속 실행되지만 UI에서는 표시 안 함

4. 최종 답변 수신
   ✅ 답변 표시 (Progress 없이)
```

**체크 포인트:**

- [ ] X 버튼 클릭 시 팝업이 닫힘
- [ ] Progress가 즉시 제거됨
- [ ] final_response 수신 시 답변이 표시됨

**콘솔 로그 확인:**

```
[ChatInterface] Force closing popup (removing progress)
```

---

### 시나리오 3: "수정" 요청 ⭐⭐

**목적**: "수정" 후 Progress가 유지되는지 확인

**테스트 케이스:** "임대차 계약서 작성해줘" → Interrupt → "수정" → 수정 사항 입력 → "수정 제출"

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시

2. Interrupt 발생
   ✅ 팝업 표시

3. 사용자 "수정" 버튼 클릭
   ✅ 수정 입력창 표시 (팝업 하단)

4. 수정 사항 입력
   예: "임대료를 월 100만원으로 조정해주세요"

5. "수정 제출" 버튼 클릭
   ✅ 팝업 닫힘
   ✅ Progress 유지됨 (핵심!)
   ✅ Progress 업데이트 (승인과 동일)

6. 최종 답변 수신 (수정 반영됨)
   ✅ Progress 제거
   ✅ 답변 표시 (수정 내용 반영)
```

**체크 포인트:**

- [ ] "수정" 버튼 클릭 시 입력창 표시
- [ ] 수정 사항 입력 가능
- [ ] "수정 제출" 후 팝업 닫힘
- [ ] Progress 유지됨
- [ ] Progress 업데이트됨 (75% → 95%)
- [ ] 최종 답변에 수정 내용 반영됨

**콘솔 로그 확인:**

```
[LeaseContractPage] Modify - keeping progress visible
[ChatInterface] Sending modify response: 임대료를 월 100만원으로...
[ChatInterface] Closing popup only (keeping progress visible)
```

---

### 시나리오 4: "거부" ⭐

**목적**: "거부" 후 Progress가 유지되고 에러 응답이 표시되는지 확인

**테스트 케이스:** "임대차 계약서 작성해줘" → Interrupt → "거부"

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시

2. Interrupt 발생
   ✅ 팝업 표시

3. 사용자 "거부" 버튼 클릭
   ✅ 팝업 닫힘
   ✅ Progress 유지됨 (Backend 처리 중)

4. Backend에서 reject 처리
   ✅ 에러 응답 또는 안내 메시지 반환

5. 응답 수신
   ✅ Progress 제거
   ✅ 에러 메시지 또는 안내 메시지 표시
```

**체크 포인트:**

- [ ] "거부" 클릭 시 팝업 닫힘
- [ ] Progress 유지됨
- [ ] Backend 응답 수신 시 Progress 제거
- [ ] 적절한 메시지 표시

**콘솔 로그 확인:**

```
[LeaseContractPage] Reject - keeping progress visible
[ChatInterface] Sending reject response
[ChatInterface] Closing popup only (keeping progress visible)
```

---

## 🔍 디버깅 가이드

### 콘솔 로그 확인

**정상 승인 플로우:**

```
[ChatInterface] Received WS message: workflow_interrupted
[ChatInterface] Workflow interrupted: {...}
[사용자가 승인 버튼 클릭]
[LeaseContractPage] Approve - keeping progress visible
[ChatInterface] Sending approve response
[ChatInterface] Closing popup only (keeping progress visible)
[ChatInterface] Received WS message: supervisor_phase_change
[ChatInterface] Received WS message: supervisor_phase_change
[ChatInterface] Received WS message: supervisor_phase_change
[ChatInterface] Received WS message: final_response
```

### Progress 상태 확인

**React DevTools 사용:**

1. React DevTools 열기 (F12 → Components 탭)
2. ChatInterface 컴포넌트 찾기
3. State 확인:
   - `messages` 배열에 `type: "progress"` 메시지 존재 확인
   - `showLeaseContract`: false (팝업 닫힌 후)
   - `threeLayerProgress`: 업데이트되는지 확인

### Backend 로그 확인

**승인 후 Backend 로그:**

```
INFO:app.api.chat_api:📥 Interrupt response received: approve
INFO:app.api.chat_api:🔄 Resuming workflow for session-...
INFO:app.service_agent.execution_agents.document_executor:📊 Aggregate node
INFO:app.service_agent.execution_agents.document_executor:📝 Generate node
INFO:app.service_agent.supervisor.team_supervisor:[TeamSupervisor] === Aggregating results ===
INFO:app.service_agent.supervisor.team_supervisor:[TeamSupervisor] === Generating response ===
INFO:app.service_agent.llm_manager.llm_service:LLM Call: response_synthesis | ...
```

### WebSocket 메시지 확인

**Network 탭에서 WebSocket 확인:**

1. F12 → Network 탭
2. WS 필터 클릭
3. WebSocket 연결 클릭
4. Messages 탭에서 메시지 확인:

```json
// 승인 후 전송되는 Progress 메시지들
{"type": "supervisor_phase_change", "supervisorPhase": "finalizing", "supervisorProgress": 75, ...}
{"type": "supervisor_phase_change", "supervisorPhase": "finalizing", "supervisorProgress": 85, ...}
{"type": "supervisor_phase_change", "supervisorPhase": "finalizing", "supervisorProgress": 87, ...}
{"type": "supervisor_phase_change", "supervisorPhase": "finalizing", "supervisorProgress": 90, ...}
{"type": "supervisor_phase_change", "supervisorPhase": "finalizing", "supervisorProgress": 95, ...}
{"type": "final_response", "response": {...}}
```

---

## ⚠️ 알려진 이슈 및 확인 사항

### 1. Progress 메시지가 이미 삭제된 경우

**문제:**
- 다른 로직에서 Progress 메시지가 삭제되었을 수 있음
- Interrupt 재개 시 업데이트할 대상이 없음

**대응:**
- 현재는 `supervisor_phase_change` 메시지를 수신하면 `threeLayerProgress` state만 업데이트
- `messages` 배열에 Progress 메시지가 없어도 `threeLayerProgress`가 있으면 일부 UI는 표시 가능
- 필요 시 Phase 4 (Progress 자동 재생성) 구현 고려

**확인 방법:**
```javascript
// React DevTools에서 확인
messages.filter(m => m.type === "progress")  // 비어있으면 문제
threeLayerProgress  // null이 아니면 일부 표시 가능
```

### 2. final_response가 오지 않는 경우

**문제:**
- Backend 에러로 인해 final_response가 전송되지 않음
- Progress가 계속 표시됨 (멈춘 상태)

**대응:**
- Backend 에러 로그 확인
- 타임아웃 처리 고려 (추후 구현)

**확인 방법:**
- Backend 로그에서 에러 확인
- 30초 이상 Progress가 95%에서 멈춰있으면 문제

### 3. Progress 업데이트가 너무 빠른 경우

**문제:**
- LLM 호출이 빠르게 완료되면 Progress 업데이트가 너무 빨라서 보이지 않을 수 있음

**대응:**
- 정상 동작 (문제 아님)
- LLM 호출이 빠르면 사용자 경험이 더 좋음

---

## 📊 성능 확인

### 타이밍 측정

**예상 타이밍:**

| 단계 | 시간 | Progress |
|-----|------|----------|
| 입력 → Interrupt | 약 5초 | 0% → 30% |
| 사용자 승인 대기 | 가변 | 30% (유지) |
| 승인 → Aggregate | 0.1초 | 75% |
| Aggregate → Generate | 0.1초 | 85% |
| Generate → LLM 시작 | 0.1초 | 87% |
| LLM 작업 | 약 7초 | 87% (유지) |
| LLM 완료 → 검증 | 0.1초 | 90% |
| 검증 → 완료 | 0.1초 | 95% |
| 완료 → 답변 표시 | 0.1초 | 100% |

**총 소요 시간:**
- 변경 전: 5초 (Progress) + 사용자 대기 + 7초 (Progress 없음) = 12초 + 사용자 대기
- 변경 후: 5초 (Progress) + 사용자 대기 + 7초 (Progress 있음) = 12초 + 사용자 대기
- **UX 개선:** 7초간 피드백 제공 ✅

---

## ✅ 테스트 체크리스트

### 기능 테스트

- [ ] 시나리오 1: 정상 승인 플로우 (핵심)
- [ ] 시나리오 2: X 버튼으로 강제 종료
- [ ] 시나리오 3: "수정" 요청
- [ ] 시나리오 4: "거부"

### UI/UX 테스트

- [ ] Progress가 자연스럽게 업데이트됨
- [ ] Progress Bar 애니메이션이 부드러움
- [ ] 팝업 닫힘/열림 애니메이션이 자연스러움
- [ ] 메시지 표시가 명확함

### 브라우저 호환성

- [ ] Chrome (권장)
- [ ] Firefox
- [ ] Edge
- [ ] Safari (macOS)

### 디바이스 테스트

- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (iPad)
- [ ] Mobile (iPhone)

---

## 🐛 버그 리포트 템플릿

**버그 발견 시 아래 정보를 수집하여 보고:**

```
### 버그 설명
[간단한 설명]

### 재현 단계
1. ...
2. ...
3. ...

### 예상 동작
[...]

### 실제 동작
[...]

### 콘솔 로그
```
[로그 복사]
```

### 스크린샷/비디오
[첨부]

### 환경
- 브라우저: Chrome 120.0
- OS: Windows 11
- 날짜/시간: 2025-10-28 10:00

### 추가 정보
[...]
```

---

## 🎯 성공 기준

### 필수 (Must Have)

- ✅ "승인" 후 Progress가 유지됨
- ✅ Progress가 75% → 95%로 업데이트됨
- ✅ final_response 수신 시 Progress가 제거됨
- ✅ X 버튼으로 닫을 때 Progress가 제거됨

### 권장 (Should Have)

- ✅ 콘솔 로그가 명확함
- ✅ Progress 업데이트가 부드러움
- ✅ 사용자가 진행 상황을 명확히 인지

### 선택 (Nice to Have)

- 💡 Progress 자동 재생성 (삭제된 경우)
- 💡 타임아웃 처리 (30초 이상 멈춘 경우)
- 💡 에러 메시지 개선

---

**끝.**
