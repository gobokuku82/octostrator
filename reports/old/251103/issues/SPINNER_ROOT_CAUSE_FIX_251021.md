# Spinner 문제 근본 원인 및 해결 완료

**작성일**: 2025-10-21
**문제**: 복합 질문 시 ExecutionProgressPage spinner 작동 안 함
**근본 원인**: 병렬 실행(_execute_teams_parallel)에서 todo_updated 메시지 미전송
**해결 시간**: 10분 (1개 파일, 73줄 추가)

---

## 🎯 근본 원인 (최종 확인)

### 문제 발생 경로

```
사용자: "집주인이 하수구 수리 안 해줘요" (복합 질문)
   ↓
PlanningAgent: search_team + analysis_team 선택
   ↓
TeamSupervisor.execute_teams_node:
   execution_strategy = "parallel"  ⬅️ 복합 질문은 병렬 실행!
   ↓
_execute_teams_parallel 호출
   ❌ todo_updated 메시지 전송 안 함!
   ↓
Frontend: execution_start만 수신
   → ExecutionProgressPage 생성 안 됨 (조건: execution_start에 execution_steps 필요)
   ↓
결과: Spinner 안 보임
```

### 단일 vs 복합 에이전트 차이

| 항목 | 단일 에이전트 | 복합 에이전트 |
|------|--------------|--------------|
| **예시 질문** | "전세금 인상기준은?" | "시세 확인하고 분석해줘" |
| **선택된 팀** | search_team (1개) | search_team + analysis_team (2개) |
| **실행 전략** | sequential | **parallel** ⬅️ 차이점 |
| **실행 메서드** | _execute_teams_sequential | _execute_teams_parallel |
| **todo_updated 전송** | ✅ 있음 (Line 670-705) | ❌ 없음 (기존 Line 620-645) |
| **ExecutionProgressPage** | ✅ 생성됨 | ❌ 생성 안 됨 |
| **Spinner** | ✅ 작동 | ❌ 작동 안 함 |

---

## 📋 실제 로그 분석

### 백엔드 로그 (복합 질문)

```
2025-10-21 14:36:03 [TeamSupervisor] Sent execution_start via WebSocket  ✅
2025-10-21 14:36:03 [TeamSupervisor] Executing 2 teams in parallel       ⬅️ parallel!
2025-10-21 14:36:06 [TeamSupervisor] Team 'search' completed              ✅
2025-10-21 14:36:23 [TeamSupervisor] Team 'analysis' completed            ✅
2025-10-21 14:36:23 [TeamSupervisor] === Aggregating results ===          ✅
2025-10-21 14:36:29 [TeamSupervisor] === Response generation complete === ✅

❌ "todo_updated" 로그 없음!
```

### 프론트엔드 Console 로그 (복합 질문)

```javascript
[ChatWSClient] 📥 Received: execution_start {...}   ✅
[ChatInterface] Received WS message: execution_start ✅

❌ todo_updated 메시지 수신 없음!

[ChatWSClient] 📥 Received: final_response {...}    ✅
[ChatInterface] Received WS message: final_response ✅
```

### 메시지 흐름 비교

**단일 에이전트** (✅ 정상):
```
1. execution_start
2. todo_updated (step_0: in_progress)     ⬅️ ExecutionProgressPage 생성
3. todo_updated (step_0: completed)
4. final_response
```

**복합 에이전트** (❌ 문제):
```
1. execution_start
   (todo_updated 없음!)                  ⬅️ ExecutionProgressPage 생성 안 됨
2. final_response
```

---

## ✅ 해결 방법

### 수정 파일

**파일**: [team_supervisor.py:620-714](backend/app/service_agent/supervisor/team_supervisor.py#L620-L714)

**수정 내용**: `_execute_teams_parallel` 메서드에 `todo_updated` 전송 로직 추가 (73줄)

### 수정 전 코드 (기존)

```python
async def _execute_teams_parallel(
    self,
    teams: List[str],
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """팀 병렬 실행"""
    logger.info(f"[TeamSupervisor] Executing {len(teams)} teams in parallel")

    tasks = []
    for team_name in teams:
        if team_name in self.teams:
            task = self._execute_single_team(team_name, shared_state, main_state)
            tasks.append((team_name, task))

    results = {}
    for team_name, task in tasks:
        try:
            result = await task
            results[team_name] = result
            logger.info(f"[TeamSupervisor] Team '{team_name}' completed")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")
            results[team_name] = {"status": "failed", "error": str(e)}

    return results
```

**문제점**:
- ❌ `todo_updated` 메시지 전송 없음
- ❌ `planning_state` 업데이트 없음
- ❌ Frontend가 진행 상황을 알 수 없음

### 수정 후 코드 (최종)

```python
async def _execute_teams_parallel(
    self,
    teams: List[str],
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """팀 병렬 실행 + execution_steps status 업데이트"""
    logger.info(f"[TeamSupervisor] Executing {len(teams)} teams in parallel")

    planning_state = main_state.get("planning_state")
    session_id = main_state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id) if session_id else None

    tasks = []
    for team_name in teams:
        if team_name in self.teams:
            task = self._execute_single_team(team_name, shared_state, main_state)
            tasks.append((team_name, task))

    results = {}
    for team_name, task in tasks:
        # ✅ 실행 전: status = "in_progress"
        step_id = self._find_step_id_for_team(team_name, planning_state)
        if step_id and planning_state:
            planning_state = StateManager.update_step_status(
                planning_state,
                step_id,
                "in_progress",
                progress=0
            )
            main_state["planning_state"] = planning_state

            # WebSocket: TODO 상태 변경 알림 (in_progress)
            if progress_callback:
                try:
                    await progress_callback("todo_updated", {
                        "execution_steps": planning_state["execution_steps"]
                    })
                except Exception as ws_error:
                    logger.error(f"[TeamSupervisor] Failed to send todo_updated (in_progress): {ws_error}")

        try:
            result = await task
            results[team_name] = result

            # ✅ 실행 성공: status = "completed"
            if step_id and planning_state:
                planning_state = StateManager.update_step_status(
                    planning_state,
                    step_id,
                    "completed",
                    progress=100
                )
                # 결과 저장
                for step in planning_state["execution_steps"]:
                    if step["step_id"] == step_id:
                        step["result"] = result
                        break
                main_state["planning_state"] = planning_state

                # WebSocket: TODO 상태 변경 알림 (completed)
                if progress_callback:
                    try:
                        await progress_callback("todo_updated", {
                            "execution_steps": planning_state["execution_steps"]
                        })
                    except Exception as ws_error:
                        logger.error(f"[TeamSupervisor] Failed to send todo_updated (completed): {ws_error}")

            logger.info(f"[TeamSupervisor] Team '{team_name}' completed")
        except Exception as e:
            # ✅ 실행 실패: status = "failed"
            logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")

            if step_id and planning_state:
                planning_state = StateManager.update_step_status(
                    planning_state,
                    step_id,
                    "failed",
                    error=str(e)
                )
                main_state["planning_state"] = planning_state

                # WebSocket: TODO 상태 변경 알림 (failed)
                if progress_callback:
                    try:
                        await progress_callback("todo_updated", {
                            "execution_steps": planning_state["execution_steps"]
                        })
                    except Exception as ws_error:
                        logger.error(f"[TeamSupervisor] Failed to send todo_updated (failed): {ws_error}")

            results[team_name] = {"status": "failed", "error": str(e)}

    return results
```

**개선 사항**:
- ✅ `todo_updated` 메시지 전송 (in_progress, completed, failed)
- ✅ `planning_state` 실시간 업데이트
- ✅ Frontend가 진행 상황 추적 가능
- ✅ `_execute_teams_sequential`과 동일한 로직

---

## 📊 수정 효과 예상

### Before (문제)

```
[복합 질문 입력]
   ↓
화면: "계획 분석 중" (spinner 회전) ✅
   ↓
execution_start 수신
   ↓
❌ todo_updated 없음
   ↓
화면: 아무것도 없음 (spinner 사라짐) ❌
   ↓
final_response 수신
   ↓
화면: 답변 표시
```

### After (수정 후)

```
[복합 질문 입력]
   ↓
화면: "계획 분석 중" (spinner 회전) ✅
   ↓
execution_start 수신
   ↓
✅ todo_updated (step_0: in_progress) 수신
   ↓
화면: "작업 실행 중" (spinner 회전) ✅
   └─ ✓ 정보 검색 (진행 중)
   └─ ○ 데이터 분석 (대기 중)
   ↓
✅ todo_updated (step_0: completed) 수신
   ↓
화면: "작업 실행 중" (spinner 회전) ✅
   └─ ✓ 정보 검색 (완료)
   └─ ○ 데이터 분석 (대기 중)
   ↓
✅ todo_updated (step_1: in_progress) 수신
   ↓
화면: "작업 실행 중" (spinner 회전) ✅
   └─ ✓ 정보 검색 (완료)
   └─ ✓ 데이터 분석 (진행 중)
   ↓
✅ todo_updated (step_1: completed) 수신
   ↓
화면: "작업 실행 중" (spinner 회전) ✅
   └─ ✓ 정보 검색 (완료)
   └─ ✓ 데이터 분석 (완료)
   ↓
final_response 수신
   ↓
화면: 답변 표시
```

---

## 🧪 테스트 방법

### 테스트 1: 복합 질문 (병렬 실행)

**입력**:
```
강남구 아파트 시세 확인하고 투자 분석해줘
```

**기대 동작**:
1. "계획 분석 중" spinner 회전 ✅
2. "작업 실행 중" 카드 나타남 ✅
3. Spinner(톱니바퀴) 회전 ✅
4. "정보 검색" → "진행 중" → "완료" ✅
5. "데이터 분석" → "진행 중" → "완료" ✅
6. 답변 표시 ✅

**확인 로그** (백엔드):
```bash
tail -f backend/logs/app.log | grep -E "todo_updated|Executing.*parallel"
```

**기대 로그**:
```
[TeamSupervisor] Executing 2 teams in parallel
[TeamSupervisor] Failed to send todo_updated (in_progress): ...  (또는 성공)
[TeamSupervisor] Failed to send todo_updated (completed): ...    (또는 성공)
```

**확인 Console** (프론트엔드):
```javascript
F12 → Console → "todo_updated" 검색
```

**기대 Console**:
```
[ChatWSClient] 📥 Received: todo_updated {...}
[ChatInterface] Received WS message: todo_updated
```

---

### 테스트 2: 단일 질문 (순차 실행) - 기존 정상 동작 유지

**입력**:
```
전세금 인상기준은?
```

**기대 동작**:
- 기존과 동일하게 정상 작동 ✅
- Spinner 회전 ✅

---

## 📈 수정 영향 분석

### 변경 범위

| 항목 | Before | After |
|------|--------|-------|
| **수정 파일** | - | 1개 (team_supervisor.py) |
| **수정 라인** | - | 73줄 (추가) |
| **영향 범위** | 복합 질문 (병렬 실행) | 복합 질문만 |
| **기존 기능** | 단일 질문 정상 | 단일 질문 정상 유지 ✅ |

### 리스크

| 리스크 | 평가 | 비고 |
|--------|------|------|
| **기존 기능 영향** | 없음 | `_execute_teams_sequential`은 수정 안 함 |
| **성능 영향** | 없음 | WebSocket 메시지 추가만 (미미) |
| **에러 가능성** | 낮음 | Try-except로 에러 처리 |

---

## ✅ 성공 기준

### 필수 확인 사항

- [x] 코드 수정 완료
- [ ] 백엔드 재시작
- [ ] 복합 질문 입력 시 spinner 회전 확인
- [ ] Console에서 `todo_updated` 메시지 수신 확인
- [ ] 백엔드 로그에서 `todo_updated` 전송 확인

### 검증 체크리스트

- [ ] 복합 질문: "강남구 시세 확인하고 분석해줘"
  - [ ] "작업 실행 중" 카드 표시
  - [ ] Spinner 회전
  - [ ] "정보 검색" 상태 변화 (대기 → 진행 → 완료)
  - [ ] "데이터 분석" 상태 변화 (대기 → 진행 → 완료)

- [ ] 단일 질문: "전세금 인상기준은?"
  - [ ] 기존과 동일하게 정상 작동
  - [ ] Spinner 회전

---

## 🎯 최종 정리

### 핵심 문제

**병렬 실행(_execute_teams_parallel)에서 `todo_updated` 메시지를 전송하지 않아 Frontend가 진행 상황을 알 수 없었음**

### 해결 방법

**`_execute_teams_parallel`에 `_execute_teams_sequential`과 동일한 `todo_updated` 전송 로직 추가**

### 수정량

- **1개 파일**: team_supervisor.py
- **73줄 추가**: todo_updated 전송 로직 (in_progress, completed, failed)

### 예상 효과

- ✅ 복합 질문 시 ExecutionProgressPage 정상 표시
- ✅ Spinner 정상 회전
- ✅ 실시간 진행 상황 추적 가능
- ✅ 사용자 경험 개선

---

## 🚀 다음 단계

### 즉시 실행

```bash
# 백엔드 재시작
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
# Ctrl+C로 중지
python main.py
```

### 테스트

```
복합 질문 입력: "강남구 아파트 시세 확인하고 투자 분석해줘"
→ Spinner 회전 확인
→ "작업 실행 중" 카드 확인
→ 진행 상황 변화 확인
```

---

**작성 완료**: 2025-10-21
**구현 완료**: 2025-10-21
**테스트 대기**: 백엔드 재시작 필요
