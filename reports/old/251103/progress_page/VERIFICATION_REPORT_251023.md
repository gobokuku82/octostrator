# Data Reuse Visualization - Implementation Plan Verification Report

**작성일**: 2025년 10월 23일
**검증 대상**: DATA_REUSE_VISUALIZATION_PLAN_251023.md
**검증자**: Claude (AI Assistant)
**결론**: ⚠️ **수정 필요** - Variable timing issue identified

---

## 📋 Executive Summary

| 검증 항목 | 상태 | 비고 |
|---------|------|------|
| **백엔드 코드 위치** | ✅ 정확 | team_supervisor.py 파일 확인됨 |
| **WebSocket 신호 흐름** | ✅ 정확 | data_reuse_notification → plan_ready 순서 확인됨 |
| **사용자 의도 반영** | ✅ 정확 | 재사용된 팀 시각화 요구사항 정확히 반영됨 |
| **변수 접근 타이밍** | ⚠️ **문제 발견** | original_agents 변수가 notification 이후에 생성됨 |
| **타입 정의** | ✅ 정확 | Frontend 타입 구조 적절함 |

**종합 평가**: 계획서의 방향성과 사용자 의도는 정확하나, **백엔드 구현 시 variable timing 조정 필요**

---

## 🔍 Section 1: 백엔드 코드 검증

### 1.1 파일 위치 및 WebSocket 신호

**계획서 내용 (Line 139-141)**:
```python
# 파일: backend/app/service_agent/supervisor/team_supervisor.py
# 위치: 데이터 재사용 감지 로직 부분 (약 200-250번 줄 예상)
```

**실제 코드**:
- ✅ **파일 경로 정확**: `backend/app/service_agent/supervisor/team_supervisor.py`
- ✅ **위치 정확**: Line 263-269에 `data_reuse_notification` 존재

**현재 data_reuse_notification (Line 263-266)**:
```python
await progress_callback("data_reuse_notification", {
    "message": "이전 대화의 정보를 활용하여 분석 중입니다",
    "reused_from": f"{data_message_index}개 메시지 전"
})
```

**상태**: ✅ **위치 정확**

---

### 1.2 데이터 재사용 로직 흐름

**실제 코드 흐름 (team_supervisor.py)**:

```python
# Line 253-258: 데이터 재사용 감지
if has_search_data:
    logger.info(f"✅ [TeamSupervisor] Reusing data from {data_message_index} messages ago")
    state["data_reused"] = True
    state["reused_from_index"] = data_message_index

# Line 263-269: 🚨 data_reuse_notification 전송 (현재 위치)
if progress_callback:
    await progress_callback("data_reuse_notification", {
        "message": "이전 대화의 정보를 활용하여 분석 중입니다",
        "reused_from": f"{data_message_index}개 메시지 전"
    })

# Line 271-280: 이전 검색 결과를 team_results에 저장
for msg in recent_messages:
    if msg["role"] == "assistant" and self._has_reusable_data(msg):
        state["team_results"]["search"] = {
            "data": msg["content"],
            "reused": True,
            "from_message_index": data_message_index
        }
        break

# Line 288-296: 🚨 original_agents 변수 생성 (나중에 생성됨!)
if state.get("data_reused") and intent_result.suggested_agents:
    original_agents = intent_result.suggested_agents.copy()
    intent_result.suggested_agents = [
        agent for agent in intent_result.suggested_agents
        if agent != "search_team"
    ]
    logger.info(f"[TeamSupervisor] Removed search_team from suggested_agents due to data reuse")
    logger.info(f"[TeamSupervisor] Original agents: {original_agents} -> Modified: {intent_result.suggested_agents}")
```

**⚠️ 문제점 발견**:
- **Line 263**: `data_reuse_notification` 전송
- **Line 290**: `original_agents` 변수 생성 (27줄 뒤)
- 계획서는 notification에서 `original_agents` 변수 사용을 가정했으나, 실제로는 아직 생성되지 않음

---

### 1.3 WebSocket 신호 타이밍

**신호 전송 순서 (실제 코드 기준)**:

```
1. analysis_start      (Line 212) - ✅ Stage 2 시작
   ↓
2. intent 분석         (Line 221) - PlanningAgent.analyze_intent()
   ↓
3. data_reuse_notification (Line 263) - 🚨 문제: original_agents 없음
   ↓
4. original_agents 생성 (Line 290) - 🚨 늦게 생성됨
   ↓
5. plan_ready          (Line 252) - execution_steps 전송
   ↓
6. execution_start     (Line 480) - 팀 실행 시작
```

**상태**: ⚠️ **Variable timing issue** - notification이 너무 일찍 전송됨

---

## 🛠️ Section 2: 문제점 상세 분석

### 2.1 계획서 vs 실제 코드 Gap

**계획서 가정 (Line 150-165)**:
```python
# 데이터 재사용 감지 후
reused_teams_list = []
if "search_team" in original_agents and "search_team" not in modified_agents:
    reused_teams_list.append("search")

if reused_teams_list:
    await progress_callback("data_reuse_notification", {
        "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
        "reused_teams": reused_teams_list,
        "reused_from_message": message_index_to_reuse,
        "timestamp": datetime.now().isoformat()
    })
```

**실제 상황**:
- Line 263: Notification 시점에는 `original_agents` 변수가 존재하지 않음
- Line 290: `original_agents`는 27줄 뒤에 생성됨
- **결론**: 계획서의 코드를 그대로 적용하면 `NameError` 발생

---

### 2.2 원인 분석

**현재 코드 구조**:
1. Intent 분석 → `intent_result` 반환 (Line 221)
2. Data reuse 감지 (Line 253)
3. **즉시 notification 전송** (Line 263)
4. Team_results에 데이터 저장 (Line 271-280)
5. **나중에 agents 수정** (Line 288-296)

**문제의 근본 원인**:
- Notification 시점에는 "어떤 팀이 제거될지" 아직 모름
- Agent 수정 로직이 notification보다 뒤에 있음

---

## ✅ Section 3: 해결 방안 제시

### Option A: Notification 위치 이동 (권장)

**변경 전 (현재)**:
```python
# Line 263: Notification (너무 일찍)
await progress_callback("data_reuse_notification", {...})

# Line 288-296: Agents 수정 (나중에)
if state.get("data_reused") and intent_result.suggested_agents:
    original_agents = intent_result.suggested_agents.copy()
    ...
```

**변경 후 (권장)**:
```python
# Line 288-296: Agents 수정 먼저
if state.get("data_reused") and intent_result.suggested_agents:
    original_agents = intent_result.suggested_agents.copy()
    intent_result.suggested_agents = [
        agent for agent in intent_result.suggested_agents
        if agent != "search_team"
    ]
    logger.info(f"[TeamSupervisor] Removed search_team from suggested_agents due to data reuse")

    # 🆕 Notification 여기로 이동 (agents 정보 확보 후)
    reused_teams_list = []
    if "search_team" in original_agents and "search_team" not in intent_result.suggested_agents:
        reused_teams_list.append("search")

    if reused_teams_list and progress_callback:
        try:
            await progress_callback("data_reuse_notification", {
                "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
                "reused_teams": reused_teams_list,
                "reused_from_message": state.get("reused_from_index"),
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"[TeamSupervisor] Sent data_reuse_notification with teams: {reused_teams_list}")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send data_reuse_notification: {e}")
```

**장점**:
- ✅ `original_agents` 변수 접근 가능
- ✅ 제거된 팀 정보를 정확히 전송
- ✅ 코드 구조 변경 최소화

**단점**:
- ⚠️ Notification 타이밍이 약간 늦어짐 (하지만 plan_ready보다는 빠름)

---

### Option B: Early Agent Copy (Alternative)

**변경 방안**:
```python
# Line 253-258: 데이터 재사용 감지
if has_search_data:
    logger.info(f"✅ [TeamSupervisor] Reusing data from {data_message_index} messages ago")
    state["data_reused"] = True
    state["reused_from_index"] = data_message_index

    # 🆕 원본 agents 미리 저장 (intent_result에서)
    original_agents_early = intent_result.suggested_agents.copy() if intent_result.suggested_agents else []

# Line 263-269: Notification (수정)
if progress_callback:
    reused_teams_list = []
    if state.get("data_reused") and "search_team" in original_agents_early:
        reused_teams_list.append("search")

    if reused_teams_list:
        await progress_callback("data_reuse_notification", {
            "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
            "reused_teams": reused_teams_list,
            ...
        })
```

**장점**:
- ✅ Notification 타이밍 유지 (Line 263)
- ✅ Variable access 문제 해결

**단점**:
- ⚠️ 변수 중복 (`original_agents_early` vs `original_agents`)
- ⚠️ 코드 복잡도 증가

---

## 🎯 Section 4: 권장 구현 방안

### 4.1 최종 권장: **Option A (Notification 이동)**

**이유**:
1. **코드 구조가 깔끔함**: Agent 수정과 Notification이 한 블록에 있음
2. **유지보수 용이**: 로직이 한 곳에 집중됨
3. **타이밍 문제 없음**: plan_ready보다는 여전히 빨리 전송됨

**구현 위치**: `team_supervisor.py` Line 288-296 블록 내부

---

### 4.2 수정된 백엔드 코드 (Complete)

```python
# team_supervisor.py - Line 288-310 (수정 후)

# 🆕 데이터 재사용 시 suggested_agents에서 SearchTeam 제거
if state.get("data_reused") and intent_result.suggested_agents:
    original_agents = intent_result.suggested_agents.copy()
    intent_result.suggested_agents = [
        agent for agent in intent_result.suggested_agents
        if agent != "search_team"
    ]
    logger.info(f"[TeamSupervisor] Removed search_team from suggested_agents due to data reuse")
    logger.info(f"[TeamSupervisor] Original agents: {original_agents} -> Modified: {intent_result.suggested_agents}")

    # 🆕 재사용된 팀 리스트 생성
    reused_teams_list = []
    if "search_team" in original_agents and "search_team" not in intent_result.suggested_agents:
        reused_teams_list.append("search")

    # 🆕 WebSocket: data_reuse_notification 전송 (이동됨)
    if reused_teams_list and progress_callback:
        try:
            await progress_callback("data_reuse_notification", {
                "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
                "reused_teams": reused_teams_list,
                "reused_from_message": state.get("reused_from_index"),
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"[TeamSupervisor] Sent data_reuse_notification with teams: {reused_teams_list}")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send data_reuse_notification: {e}")
```

**변경 사항**:
- ❌ **삭제**: Line 263-269의 기존 notification 코드
- ✅ **추가**: Line 288-296 블록 내부에 notification 로직 통합

---

### 4.3 기존 notification 제거

**제거할 코드 (Line 260-269)**:
```python
# ❌ 삭제: 기존 notification (변수 접근 불가)
# 사용자에게 알림 (WebSocket)
if progress_callback:
    try:
        await progress_callback("data_reuse_notification", {
            "message": "이전 대화의 정보를 활용하여 분석 중입니다",
            "reused_from": f"{data_message_index}개 메시지 전"
        })
        logger.info("[TeamSupervisor] Sent data_reuse_notification via WebSocket")
    except Exception as e:
        logger.error(f"[TeamSupervisor] Failed to send data_reuse_notification: {e}")
```

---

## 📊 Section 5: Frontend 계획서 검증

### 5.1 Message 타입 정의

**계획서 (Line 205-218)**:
```tsx
progressData?: {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
  reusedTeams?: string[]  // 🆕 추가
}
```

**상태**: ✅ **적절함** - 타입 구조가 깔끔하고 확장 가능함

---

### 5.2 WebSocket Handler

**계획서 (Line 229-248)**:
```tsx
case 'data_reuse_notification':
  if (message.reused_teams && Array.isArray(message.reused_teams)) {
    setMessages((prev) =>
      prev.map(m =>
        m.type === "progress" && m.progressData
          ? {
              ...m,
              progressData: {
                ...m.progressData,
                reusedTeams: message.reused_teams
              }
            }
          : m
      )
    )
  }
  break
```

**상태**: ✅ **적절함** - React state 업데이트 로직 정확함

---

### 5.3 ExecutingContent 수정

**계획서 (Line 291-331)**:
```tsx
const reusedSteps: ExecutionStep[] = (reusedTeams || []).map(team => ({
  step_id: `reused-${team}`,
  task: team === 'search' ? '법률 검색' : `${team} 작업`,
  description: '이전 데이터 재사용',
  status: 'completed' as const,
  agent: `${team}_team`,
  progress: 100,
  isReused: true
}))

const allSteps = [...reusedSteps, ...steps]
```

**상태**: ✅ **적절함** - Virtual steps 생성 로직 명확함

---

### 5.4 AgentCard 재사용 배지

**계획서 (Line 496-501)**:
```tsx
{step.isReused && (
  <span className="ml-auto text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 ...">
    <span>♻️</span>
    <span>재사용</span>
  </span>
)}
```

**상태**: ✅ **적절함** - UI 디자인 일관성 유지

---

## 🔄 Section 6: WebSocket 신호 흐름 재검증

### 6.1 수정 후 신호 흐름

```
사용자 질문 입력
    ↓
1. handleSendMessage (frontend)
   → progress message 생성 (stage: "dispatch")
    ↓
2. analysis_start (backend, Line 212)
   → Frontend: stage = "analysis"
    ↓
3. intent 분석 (backend, Line 221)
   → PlanningAgent.analyze_intent()
    ↓
4. agents 수정 (backend, Line 288-296) 🆕
   → original_agents 생성
   → search_team 제거
   → 🆕 data_reuse_notification 전송
    ↓
5. data_reuse_notification 수신 (frontend) 🆕
   → progressData.reusedTeams = ["search"]
    ↓
6. plan_ready (backend, Line 252)
   → execution_steps 전송 (search 제외됨)
   → Frontend: progressData.plan 업데이트
    ↓
7. execution_start (backend, Line 480)
   → Frontend: stage = "executing"
   → ExecutingContent 렌더링
   → allSteps = [reusedSteps, actualSteps]
   → [✓ Search 재사용] [✓ Analysis 실행]
```

**상태**: ✅ **정확함** - 수정 후 신호 흐름이 올바름

---

### 6.2 타이밍 검증

| 신호 | 라인 번호 | 순서 | Frontend 동작 |
|-----|----------|------|---------------|
| analysis_start | 212 | 1 | stage → "analysis" |
| data_reuse_notification | 288-310 (수정 후) | 2 | reusedTeams 저장 |
| plan_ready | 252 | 3 | plan 저장 |
| execution_start | 480 | 4 | stage → "executing", steps 병합 |

**상태**: ✅ **타이밍 적절함** - reusedTeams가 plan_ready보다 먼저 도착함

---

## 🎨 Section 7: 사용자 의도 반영 검증

### 7.1 사용자 요구사항

**원본 요청**:
> "backend 로그를 보면 Search + Analysis 두 팀이 작동했는데 (Search는 데이터 재사용),
> 프론트엔드에는 Analysis 팀만 표시됨.
> Option C로 해결해줘."

**Option C 정의**:
- Backend에서 `data_reuse_notification`에 `reused_teams` 정보 추가
- Frontend에서 reused teams를 virtual steps로 병합
- "재사용" 배지로 시각적 구분

---

### 7.2 계획서의 의도 반영도

| 요구사항 | 계획서 반영 | 검증 결과 |
|---------|----------|----------|
| 재사용된 팀 표시 | ✅ reusedSteps 생성 | ✅ 정확 |
| "재사용" 배지 | ✅ AgentCard 수정 | ✅ 정확 |
| 전체 진행률 정확성 | ✅ allSteps 병합 | ✅ 정확 |
| Search + Analysis 모두 표시 | ✅ 2개 카드 렌더링 | ✅ 정확 |

**상태**: ✅ **사용자 의도 완벽히 반영됨**

---

## 📝 Section 8: 수정된 구현 계획

### 8.1 Phase 1: 백엔드 수정 (수정됨)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**Step 1.1: 기존 notification 제거**
- **위치**: Line 260-269
- **작업**: 전체 블록 삭제

**Step 1.2: Agents 수정 블록에 notification 통합**
- **위치**: Line 288-296 (기존) → Line 288-310 (수정 후)
- **작업**:
  1. `original_agents` 생성
  2. `search_team` 제거
  3. `reused_teams_list` 생성
  4. `data_reuse_notification` 전송 (추가)

**예상 라인 수 변화**:
- 삭제: -10줄 (기존 notification)
- 추가: +15줄 (통합 notification)
- **순증**: +5줄

---

### 8.2 Phase 2-4: Frontend 수정 (변경 없음)

**계획서 그대로 진행**:
- Phase 2: chat-interface.tsx 수정
- Phase 3: progress-container.tsx 수정
- Phase 4: AgentCard 배지 추가

**이유**: Frontend 계획은 정확하며 변경 불필요

---

## ✅ Section 9: 최종 검증 체크리스트

### 9.1 백엔드 검증

- [x] **파일 위치 정확**: team_supervisor.py
- [x] **WebSocket 신호 존재**: data_reuse_notification (Line 263)
- [x] **데이터 재사용 로직 존재**: Line 253-296
- [ ] **Variable timing 해결**: ⚠️ Notification 위치 이동 필요
- [x] **Intent 분석 흐름 정확**: Line 221

---

### 9.2 Frontend 검증

- [x] **Message 타입 적절**: progressData.reusedTeams
- [x] **WebSocket handler 적절**: data_reuse_notification case
- [x] **Steps 병합 로직 적절**: reusedSteps + actualSteps
- [x] **UI 배지 디자인 적절**: "♻️ 재사용"

---

### 9.3 통합 검증

- [x] **사용자 의도 반영**: 재사용 팀 시각화
- [x] **WebSocket 타이밍**: reusedTeams → plan_ready → execution_start
- [ ] **코드 구조 깔끔**: ⚠️ Backend notification 위치 조정 필요

---

## 🚀 Section 10: 구현 권장 사항

### 10.1 구현 순서 (수정됨)

**Phase 1: 백엔드 수정 (15분)**
1. Line 260-269 기존 notification 제거
2. Line 288-296 블록 수정 (notification 통합)
3. 로컬 테스트로 NameError 없는지 확인

**Phase 2: Frontend 타입 & 핸들러 (10분)**
- 계획서 그대로 진행

**Phase 3: Frontend UI 수정 (15분)**
- 계획서 그대로 진행

**Phase 4: AgentCard 배지 추가 (5분)**
- 계획서 그대로 진행

**Phase 5: 통합 테스트 (10분)**
- Scenario 1: 첫 번째 질문 (재사용 없음)
- Scenario 2: 두 번째 질문 (Search 재사용)
- Scenario 3: 로그 확인 (reused_teams 전송 여부)

**총 예상 시간**: 55분 (기존 50분 + 5분)

---

### 10.2 테스트 시나리오 (변경 없음)

**계획서의 테스트 시나리오 그대로 사용**:
- Scenario 1: 첫 번째 질문 (데이터 재사용 없음)
- Scenario 2: 두 번째 질문 (데이터 재사용 있음)
- Scenario 3: 여러 팀 재사용

---

## 📌 Section 11: 결론 및 조치사항

### 11.1 검증 결과 요약

| 항목 | 상태 | 설명 |
|-----|------|------|
| **계획서 방향성** | ✅ 정확 | 사용자 의도를 완벽히 반영함 |
| **Frontend 계획** | ✅ 정확 | 수정 없이 그대로 진행 가능 |
| **Backend 계획** | ⚠️ 수정 필요 | Variable timing 문제 해결 필요 |
| **WebSocket 흐름** | ✅ 정확 | 신호 순서 적절함 |
| **UI 디자인** | ✅ 정확 | 재사용 배지 디자인 적절함 |

---

### 11.2 필수 조치사항

**1. 백엔드 수정 (필수)**:
```python
# ❌ 제거: Line 260-269 (기존 notification)
# ✅ 추가: Line 288-310 (notification 통합)

if state.get("data_reused") and intent_result.suggested_agents:
    original_agents = intent_result.suggested_agents.copy()
    intent_result.suggested_agents = [
        agent for agent in intent_result.suggested_agents
        if agent != "search_team"
    ]

    # 🆕 재사용된 팀 리스트 생성
    reused_teams_list = []
    if "search_team" in original_agents and "search_team" not in intent_result.suggested_agents:
        reused_teams_list.append("search")

    # 🆕 WebSocket 전송 (이동됨)
    if reused_teams_list and progress_callback:
        await progress_callback("data_reuse_notification", {
            "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
            "reused_teams": reused_teams_list,
            "reused_from_message": state.get("reused_from_index"),
            "timestamp": datetime.now().isoformat()
        })
```

**2. Frontend 구현 (계획서 그대로)**:
- Phase 2-4 수정 없이 진행

---

### 11.3 구현 후 검증 포인트

**백엔드 로그 확인**:
```bash
grep "Sent data_reuse_notification with teams" backend/logs/app.log
# 예상 출력: [TeamSupervisor] Sent data_reuse_notification with teams: ['search']
```

**Frontend 콘솔 확인**:
```javascript
console.log('[DEBUG] data_reuse_notification received:', message.reused_teams)
// 예상 출력: ['search']
```

**UI 확인**:
```
[✓ Search 법률 검색 ♻️재사용]  [✓ Analysis 종합 분석]
```

---

## 📚 Section 12: 참고 자료

### 12.1 관련 파일

- **백엔드**: `backend/app/service_agent/supervisor/team_supervisor.py`
  - 수정 위치: Line 260-269 (삭제), Line 288-310 (추가)
- **프론트엔드**: `frontend/components/chat-interface.tsx`
  - 수정 위치: 계획서 참조
- **프론트엔드**: `frontend/components/progress-container.tsx`
  - 수정 위치: 계획서 참조

---

### 12.2 관련 문서

- **구현 계획서**: `DATA_REUSE_VISUALIZATION_PLAN_251023.md`
- **4-Stage 계획서**: `CLEAN_4STAGE_PLAN_251023.md`
- **Backend 데이터 재사용 로직**: Line 224-296

---

## ✅ 최종 승인 권장사항

**검증자 의견**:

✅ **계획서 승인 가능 (단, 백엔드 수정 반영 후)**

**조건**:
1. ✅ 백엔드 Line 260-269 삭제
2. ✅ 백엔드 Line 288-310 수정 (notification 통합)
3. ✅ Frontend는 계획서 그대로 진행

**예상 결과**:
- Search (재사용) + Analysis (실행) 모두 UI에 표시됨
- "♻️ 재사용" 배지로 명확한 구분
- 전체 진행률 2/2 정확히 표시

---

**검증 완료일**: 2025년 10월 23일
**다음 단계**: 백엔드 수정 반영 후 구현 시작

---

## Appendix A: 완전한 백엔드 수정 코드

### A.1 삭제할 코드 (Line 260-269)

```python
# ❌ 완전 삭제
# 사용자에게 알림 (WebSocket)
if progress_callback:
    try:
        await progress_callback("data_reuse_notification", {
            "message": "이전 대화의 정보를 활용하여 분석 중입니다",
            "reused_from": f"{data_message_index}개 메시지 전"
        })
        logger.info("[TeamSupervisor] Sent data_reuse_notification via WebSocket")
    except Exception as e:
        logger.error(f"[TeamSupervisor] Failed to send data_reuse_notification: {e}")
```

---

### A.2 수정할 코드 (Line 288-310, 완전 버전)

```python
# 🆕 데이터 재사용 시 suggested_agents에서 SearchTeam 제거
if state.get("data_reused") and intent_result.suggested_agents:
    original_agents = intent_result.suggested_agents.copy()
    intent_result.suggested_agents = [
        agent for agent in intent_result.suggested_agents
        if agent != "search_team"
    ]
    logger.info(f"[TeamSupervisor] Removed search_team from suggested_agents due to data reuse")
    logger.info(f"[TeamSupervisor] Original agents: {original_agents} -> Modified: {intent_result.suggested_agents}")

    # 🆕 재사용된 팀 리스트 생성
    reused_teams_list = []
    if "search_team" in original_agents and "search_team" not in intent_result.suggested_agents:
        reused_teams_list.append("search")

    # 🆕 다른 팀도 재사용되었다면 추가 (향후 확장 가능)
    # if "document_team" in original_agents and "document_team" not in intent_result.suggested_agents:
    #     reused_teams_list.append("document")
    # if "analysis_team" in original_agents and "analysis_team" not in intent_result.suggested_agents:
    #     reused_teams_list.append("analysis")

    # 🆕 WebSocket: data_reuse_notification 전송 (이동됨)
    if reused_teams_list:
        session_id = state.get("session_id")
        progress_callback = self._progress_callbacks.get(session_id) if session_id else None
        if progress_callback:
            try:
                await progress_callback("data_reuse_notification", {
                    "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
                    "reused_teams": reused_teams_list,
                    "reused_from_message": state.get("reused_from_index"),
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"[TeamSupervisor] Sent data_reuse_notification with teams: {reused_teams_list}")
            except Exception as e:
                logger.error(f"[TeamSupervisor] Failed to send data_reuse_notification: {e}")
```

---

## Appendix B: Frontend 수정 참조 (계획서 그대로)

### B.1 Message Interface (chat-interface.tsx)

```tsx
progressData?: {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
  reusedTeams?: string[]  // 🆕 추가
}
```

### B.2 WebSocket Handler (chat-interface.tsx)

```tsx
case 'data_reuse_notification':
  if (message.reused_teams && Array.isArray(message.reused_teams)) {
    console.log('[DEBUG] data_reuse_notification received:', message.reused_teams)
    setMessages((prev) =>
      prev.map(m =>
        m.type === "progress" && m.progressData
          ? {
              ...m,
              progressData: {
                ...m.progressData,
                reusedTeams: message.reused_teams
              }
            }
          : m
      )
    )
  }
  break
```

### B.3 ExecutingContent (progress-container.tsx)

```tsx
const reusedSteps: ExecutionStep[] = (reusedTeams || []).map(team => ({
  step_id: `reused-${team}`,
  task: team === 'search' ? '법률 검색' : `${team} 작업`,
  description: '이전 데이터 재사용',
  status: 'completed' as const,
  agent: `${team}_team`,
  progress: 100,
  isReused: true
}))

const allSteps = [...reusedSteps, ...steps]
```

### B.4 AgentCard Badge (progress-container.tsx)

```tsx
{step.isReused && (
  <span className="ml-auto text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-800 flex items-center gap-1">
    <span>♻️</span>
    <span>재사용</span>
  </span>
)}
```

---

**END OF VERIFICATION REPORT**
