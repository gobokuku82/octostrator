# Agent Routing 문제 해결 - 집중 수정 계획

**작성일**: 2025-10-21
**목적**: 최소 수정으로 Agent Routing 문제 해결
**범위**: execute_teams_node, aggregate_results_node 개선

---

## 📋 현재 구조 정확한 이해

### 기존 아키텍처 (사용자 의도)

```
cognitive_agents/          → think / planning 담당 (이미 구현됨)
  ├─ planning_agent.py     → LLM #1-3: Intent Analysis + Agent Selection + Execution Plan
  ├─ query_decomposer.py   → 복합 질문 분해
  └─ execution_orchestrator.py → 실행 최적화 (미통합)

supervisor/                → execute / aggregate 담당 (수정 필요!)
  └─ team_supervisor.py
      ├─ initialize_node       → 초기화
      ├─ planning_node         → ✅ PlanningAgent 호출 (이미 완성)
      ├─ execute_teams_node    → ❌ 문제 발생 지점!
      ├─ aggregate_results_node → 🔧 개선 필요
      └─ generate_response_node → ✅ LLM #4 (완성)
```

### 현재 문제 요약

**문제 발생 위치**: `execute_teams_node` (Line 452-503)

**3가지 문제**:
1. ❌ **실행 순서 역전**: step_1 (analysis) → step_0 (search) 실행
2. ❌ **Priority 누락**: execution_steps에 priority 필드 없음
3. ❌ **순서 손실**: `set()` 사용으로 순서 보장 안 됨

**근본 원인**:
```python
# planning_node Line 267-274
active_teams = set()  # ❌ 순서 손실!
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)
state["active_teams"] = list(active_teams)  # ❌ 순서 보장 안 됨
```

---

## 🎯 수정 전략: 최소 변경 원칙

### 원칙
1. ✅ **cognitive_agents는 수정 안 함** (이미 완성됨)
2. ✅ **planning_node는 최소 수정** (priority 추가만)
3. 🔧 **execute_teams_node 집중 수정** (순서 보장)
4. 🔧 **aggregate_results_node 개선** (선택)

---

## 📝 수정 사항 (Phase 1: 긴급)

### 1. Priority 필드 추가 (separated_states.py)

**파일**: `backend/app/service_agent/foundation/separated_states.py`

**Before**:
```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str
    # ❌ priority 없음
    task: str
    ...
```

**After**:
```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str
    priority: int  # ✅ 추가!
    task: str
    ...
```

---

### 2. Planning Node 수정 (team_supervisor.py)

**파일**: `team_supervisor.py` Line 227-274

#### 수정 2-1: execution_steps에 priority 추가 (Line 227-259)

**Before**:
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "step_type": self._get_step_type_for_agent(step.agent_name),
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        # ❌ priority 없음!
        "task": self._get_task_name_for_agent(step.agent_name, intent_result),
        ...
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**After**:
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "step_type": self._get_step_type_for_agent(step.agent_name),
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        "priority": step.priority,  # ✅ 추가! (PlanningAgent가 이미 생성함)
        "task": self._get_task_name_for_agent(step.agent_name, intent_result),
        ...
    }
    for i, step in enumerate(execution_plan.steps)
]
```

#### 수정 2-2: active_teams 생성 시 순서 보장 (Line 267-274)

**Before**:
```python
# 활성화할 팀 결정
active_teams = set()  # ❌ 순서 손실!
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)  # ❌ 순서 보장 안 됨
```

**After Option A (중복 제거, 순서 보장)**:
```python
# 활성화할 팀 결정 (priority 순서 유지, 중복 제거)
active_teams = []
seen_teams = set()

# priority 순으로 정렬
sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)

state["active_teams"] = active_teams  # ✅ 순서 보장!

logger.info(f"[TeamSupervisor] Active teams (priority order): {active_teams}")
```

**After Option B (중복 허용, 더 나은 방법!)** ⭐ 권장:
```python
# 활성화할 실행 단계 저장 (중복 팀 허용, priority 순서 보장)
# execution_steps를 직접 사용하여 같은 팀이 여러 번 실행 가능
sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

state["active_steps"] = sorted_steps  # ✅ step 기반 실행

# 하위 호환성을 위한 active_teams (중복 제거)
active_teams = []
seen_teams = set()
for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)

state["active_teams"] = active_teams

logger.info(f"[TeamSupervisor] Active steps: {len(sorted_steps)}, Teams: {active_teams}")
```

---

### 3. Execute Teams Node 수정 (team_supervisor.py)

**파일**: `team_supervisor.py` Line 452-503

#### Option A: 최소 수정 (active_teams 사용)

**Before** (Line 492-497):
```python
# 팀별 실행
if execution_strategy == "parallel" and len(active_teams) > 1:
    results = await self._execute_teams_parallel(active_teams, shared_state, state)
else:
    results = await self._execute_teams_sequential(active_teams, shared_state, state)
```

**After**:
```python
# 팀별 실행 (이미 priority 순으로 정렬됨)
if execution_strategy == "parallel" and len(active_teams) > 1:
    results = await self._execute_teams_parallel(active_teams, shared_state, state)
else:
    # ✅ active_teams가 이미 priority 순이므로 그대로 사용
    results = await self._execute_teams_sequential(active_teams, shared_state, state)
```

**변경 없음! active_teams가 이미 priority 순으로 정렬되어 있으므로 execute_teams_node는 수정 불필요**

#### Option B: Step 기반 실행 (중복 팀 허용) ⭐ 권장

**파일**: `team_supervisor.py` Line 452-503

```python
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    팀 실행 노드
    계획에 따라 팀들을 실행 (Step 기반 실행으로 중복 팀 허용)
    """
    logger.info("[TeamSupervisor] Executing teams")

    state["current_phase"] = "executing"

    # WebSocket: 실행 시작 알림
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id) if session_id else None
    planning_state = state.get("planning_state")
    if progress_callback and planning_state:
        try:
            analyzed_intent = planning_state.get("analyzed_intent", {})
            await progress_callback("execution_start", {
                "message": "작업 실행을 시작합니다...",
                "execution_steps": planning_state.get("execution_steps", []),
                "intent": analyzed_intent.get("intent_type", "unknown"),
                "confidence": analyzed_intent.get("confidence", 0.0),
                "execution_strategy": planning_state.get("execution_strategy", "sequential"),
                "estimated_total_time": planning_state.get("estimated_total_time", 0),
                "keywords": analyzed_intent.get("keywords", [])
            })
            logger.info("[TeamSupervisor] Sent execution_start via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send execution_start: {e}")

    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")

    # ✅ active_steps 사용 (중복 팀 허용)
    active_steps = state.get("active_steps", [])

    # Fallback: active_steps 없으면 active_teams 사용 (하위 호환성)
    if not active_steps:
        active_teams = state.get("active_teams", [])
        # active_teams를 steps로 변환
        planning_state = state.get("planning_state", {})
        active_steps = [
            step for step in planning_state.get("execution_steps", [])
            if step.get("team") in active_teams
        ]
        active_steps = sorted(active_steps, key=lambda x: x.get("priority", 999))

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=state["query"],
        session_id=state["session_id"]
    )

    # Step 기반 실행
    if execution_strategy == "parallel" and len(active_steps) > 1:
        # 병렬 실행 (향후 구현)
        results = await self._execute_steps_parallel(active_steps, shared_state, state)
    else:
        # ✅ 순차 실행 (priority 순서 보장, 중복 팀 허용)
        results = await self._execute_steps_sequential(active_steps, shared_state, state)

    # 결과 저장 (step_id → team_name)
    for step_id, step_result in results.items():
        # step_id로 team_name 찾기
        team_name = None
        for step in active_steps:
            if step["step_id"] == step_id:
                team_name = step["team"]
                break

        if team_name:
            state = StateManager.merge_team_results(state, team_name, step_result)

    return state
```

---

### 4. _execute_steps_sequential 메서드 추가

**파일**: `team_supervisor.py` (새로운 메서드)

```python
async def _execute_steps_sequential(
    self,
    steps: List[Dict],  # ✅ ExecutionStepState 리스트
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """
    Step 순차 실행 (중복 팀 허용, priority 순서 보장)

    Args:
        steps: execution_steps (priority 순 정렬됨)
        shared_state: 공유 상태
        main_state: 메인 상태

    Returns:
        {step_id: result} 형태의 결과
    """
    logger.info(f"[TeamSupervisor] Executing {len(steps)} steps sequentially (priority order)")

    results = {}
    planning_state = main_state.get("planning_state")

    # ✅ steps는 이미 priority 순으로 정렬되어 있음
    for step in steps:
        step_id = step["step_id"]
        team_name = step["team"]
        priority = step.get("priority", 999)

        logger.info(f"[TeamSupervisor] Executing step '{step_id}' (team: {team_name}, priority: {priority})")

        if team_name in self.teams:
            try:
                # ✅ 실행 전: status = "in_progress"
                if planning_state:
                    planning_state = StateManager.update_step_status(
                        planning_state,
                        step_id,
                        "in_progress",
                        progress=0
                    )
                    main_state["planning_state"] = planning_state

                    # WebSocket: TODO 상태 변경 알림
                    session_id = main_state.get("session_id")
                    progress_callback = self._progress_callbacks.get(session_id)
                    if progress_callback:
                        try:
                            await progress_callback("todo_updated", {
                                "execution_steps": planning_state["execution_steps"]
                            })
                        except Exception as ws_error:
                            logger.error(f"[TeamSupervisor] Failed to send todo_updated (in_progress): {ws_error}")

                # 팀 실행
                result = await self._execute_single_team(team_name, shared_state, main_state)
                results[step_id] = result  # ✅ step_id를 키로 사용

                # ✅ 실행 성공: status = "completed"
                if planning_state:
                    planning_state = StateManager.update_step_status(
                        planning_state,
                        step_id,
                        "completed",
                        progress=100
                    )
                    # 결과 저장
                    for s in planning_state["execution_steps"]:
                        if s["step_id"] == step_id:
                            s["result"] = result
                            break
                    main_state["planning_state"] = planning_state

                    # WebSocket: TODO 상태 변경 알림
                    if progress_callback:
                        try:
                            await progress_callback("todo_updated", {
                                "execution_steps": planning_state["execution_steps"]
                            })
                        except Exception as ws_error:
                            logger.error(f"[TeamSupervisor] Failed to send todo_updated (completed): {ws_error}")

                logger.info(f"[TeamSupervisor] Step '{step_id}' ({team_name}) completed")

                # ✅ 데이터 전달 (step_id 기반)
                if "step_results" not in main_state:
                    main_state["step_results"] = {}
                main_state["step_results"][step_id] = self._extract_team_data(result, team_name)

            except Exception as e:
                # ✅ 실행 실패: status = "failed"
                logger.error(f"[TeamSupervisor] Step '{step_id}' ({team_name}) failed: {e}")

                if planning_state:
                    planning_state = StateManager.update_step_status(
                        planning_state,
                        step_id,
                        "failed",
                        error=str(e)
                    )
                    main_state["planning_state"] = planning_state

                    # WebSocket: TODO 상태 변경 알림
                    session_id = main_state.get("session_id")
                    progress_callback = self._progress_callbacks.get(session_id)
                    if progress_callback:
                        try:
                            await progress_callback("todo_updated", {
                                "execution_steps": planning_state["execution_steps"]
                            })
                        except Exception as ws_error:
                            logger.error(f"[TeamSupervisor] Failed to send todo_updated (failed): {ws_error}")

                results[step_id] = {"status": "failed", "error": str(e)}

    return results
```

---

### 5. PlanningAgent 키워드 필터 추가 (선택)

**파일**: `planning_agent.py` Line 297-361

**Before**:
```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    """LLM 기반 Agent 추천"""

    # === 1차: Primary LLM으로 Agent 선택 ===
    if self.llm_service:
        try:
            agents = await self._select_agents_with_llm(...)
            ...
```

**After**:
```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    """LLM 기반 Agent 추천 - 키워드 필터 추가"""

    # ✅ 추가: LEGAL_CONSULT 키워드 필터 (경계 케이스 해결)
    if intent_type == IntentType.LEGAL_CONSULT:
        # 분석이 필요한 키워드
        analysis_keywords = [
            "비교", "분석", "계산", "평가", "추천", "검토",
            "어떻게", "방법", "차이", "장단점", "괜찮아",
            "해야", "대응", "해결", "조치", "문제"
        ]

        needs_analysis = any(kw in query for kw in analysis_keywords)

        if not needs_analysis:
            logger.info(f"✅ LEGAL_CONSULT without analysis keywords → search_team only")
            return ["search_team"]
        else:
            logger.info(f"✅ LEGAL_CONSULT with analysis keywords → search + analysis")
            return ["search_team", "analysis_team"]

    # ✅ 추가: MARKET_INQUIRY 키워드 필터
    if intent_type == IntentType.MARKET_INQUIRY:
        analysis_keywords = ["비교", "분석", "평가", "추천", "차이", "장단점"]
        needs_analysis = any(kw in query for kw in analysis_keywords)

        if not needs_analysis:
            logger.info(f"✅ MARKET_INQUIRY without analysis keywords → search_team only")
            return ["search_team"]

    # === 1차: Primary LLM으로 Agent 선택 ===
    if self.llm_service:
        try:
            agents = await self._select_agents_with_llm(...)
            ...
```

---

## 🧪 테스트 케이스

### 테스트 1: 실행 순서 검증

**입력**: "강남구 아파트 시세 확인하고 투자 분석해줘"

**PlanningAgent 결과**:
```python
steps = [
    ExecutionStep(agent_name="search_team", priority=0),
    ExecutionStep(agent_name="analysis_team", priority=1)
]
```

**기대 동작**:
```
1. planning_node:
   execution_steps = [
     {step_id: "step_0", team: "search", priority: 0},
     {step_id: "step_1", team: "analysis", priority: 1}
   ]
   active_steps = sorted by priority → [step_0, step_1]

2. execute_teams_node:
   - step_0 (search, priority=0) 먼저 실행
   - step_1 (analysis, priority=1) 나중 실행

3. 로그:
   "Executing step 'step_0' (team: search, priority: 0)"
   "Step 'step_0' (search) completed"
   "Executing step 'step_1' (team: analysis, priority: 1)"
   "Step 'step_1' (analysis) completed"
```

### 테스트 2: LEGAL_CONSULT 키워드 필터

**입력 A**: "공인중개사 금지행위는?"
**기대**: search_team만

**입력 B**: "우리 계약서는 괜찮아?"
**기대**: search_team + analysis_team

### 테스트 3: 중복 팀 실행 (Option B)

**PlanningAgent 응답**:
```python
steps = [
    ExecutionStep(agent_name="search_team", priority=0),
    ExecutionStep(agent_name="analysis_team", priority=1),
    ExecutionStep(agent_name="search_team", priority=2)
]
```

**기대 동작**:
```
active_steps = [
  {step_id: "step_0", team: "search", priority: 0},
  {step_id: "step_1", team: "analysis", priority: 1},
  {step_id: "step_2", team: "search", priority: 2}
]

실행 순서:
1. step_0 (search, priority=0)
2. step_1 (analysis, priority=1)
3. step_2 (search, priority=2)  # ✅ 중복 허용!
```

---

## 📊 수정 파일 요약

### Phase 1: 긴급 수정 (2-3시간)

**1. separated_states.py**:
- ExecutionStepState에 `priority: int` 추가

**2. team_supervisor.py**:
- Line 227-259: execution_steps에 `"priority": step.priority` 추가
- Line 267-274: active_teams 생성 시 priority 순 정렬
- Line 452-503: execute_teams_node에 active_steps 사용 (Option B)
- 새로운 메서드: `_execute_steps_sequential()` 추가

**3. planning_agent.py** (선택):
- Line 297-361: `_suggest_agents()`에 키워드 필터 추가

---

## ✅ 성공 기준

1. ✅ **Priority 필드 존재**: execution_steps[i]["priority"] == i
2. ✅ **실행 순서 보장**: step_0 → step_1 → step_2 순서 실행
3. ✅ **로그 검증**: "Executing step 'step_X' (team: Y, priority: Z)" 출력
4. ✅ **LEGAL_CONSULT 정확도**: 단순 질문은 search만, 복잡한 질문은 search+analysis

---

## 🚀 구현 우선순위

### 우선순위 1: Priority 순서 보장 (필수) ⭐⭐⭐⭐⭐

**작업**:
1. separated_states.py에 priority 추가 (5분)
2. planning_node에 priority 복사 (10분)
3. active_teams priority 정렬 (15분)

**효과**: 실행 순서 문제 즉시 해결

### 우선순위 2: Step 기반 실행 (권장) ⭐⭐⭐⭐

**작업**:
1. active_steps 생성 (20분)
2. _execute_steps_sequential 구현 (1시간)
3. execute_teams_node 수정 (30분)

**효과**: 중복 팀 실행 가능 (Q1 요구사항)

### 우선순위 3: 키워드 필터 (선택) ⭐⭐⭐

**작업**:
1. planning_agent.py 수정 (30분)

**효과**: LEGAL_CONSULT 경계 케이스 해결

---

## 🎯 최종 구조 (Phase 1 완료 후)

```
START
  ↓
initialize_node
  ↓
planning_node (✅ 이미 완성, LLM 3회)
  ├─ PlanningAgent.analyze_intent()  # LLM #1
  ├─ PlanningAgent._suggest_agents()  # LLM #2 (+ 키워드 필터)
  ├─ PlanningAgent.create_execution_plan()  # LLM #3
  ├─ execution_steps에 priority 추가
  └─ active_steps = sorted(steps, key=priority)  # ✅ 순서 보장
  ↓
execute_teams_node (🔧 수정)
  ├─ _execute_steps_sequential(active_steps)  # ✅ priority 순서 실행
  └─ step_id 기반 결과 저장  # ✅ 중복 팀 대응
  ↓
aggregate_results_node
  ↓
generate_response_node (✅ 이미 완성, LLM #4)
  ↓
END
```

**LLM 호출 횟수**: 4회 (Planning 3회 + Response 1회) - 변경 없음

---

**작성 완료**: 2025-10-21
**예상 소요 시간**: 2-3시간 (우선순위 1+2)
**핵심 원칙**: 최소 수정으로 최대 효과
