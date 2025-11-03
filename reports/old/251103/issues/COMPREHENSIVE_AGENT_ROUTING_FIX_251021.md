# 종합 Agent Routing 고도화 계획서

**작성일**: 2025-10-21
**목적**: Agent Routing 문제 해결 + Execute Node 고도화 (think-planning-execute 구조 완성)
**범위**: team_supervisor.py 전체 + execute 관련 노드 개선

---

## 📋 Executive Summary

### 현재 상황 파악

**원래 의도**: `think - planning - execute` 3단계 LLM 호출 구조
**현재 상태**: Planning 구현, Execute는 단순 실행, Think는 미구현 (혼재 상태)

**현재 노드 구조**:
```python
workflow.add_node("initialize", self.initialize_node)      # 초기화
workflow.add_node("planning", self.planning_node)          # ✅ LLM 3회 (완성)
workflow.add_node("execute_teams", self.execute_teams_node) # ❌ LLM 0회 (단순 실행)
workflow.add_node("aggregate", self.aggregate_results_node) # 집계 (LLM 불필요)
workflow.add_node("generate_response", self.generate_response_node) # ✅ LLM 1회
```

**발견된 문제**:
1. ❌ **Execute 단계 순서 역전**: analysis → search (step_1 → step_0)
2. ❌ **Intent vs Selection 모순**: LLM이 4초 만에 정반대 판단
3. ❌ **Priority 누락**: execution_steps에 priority 필드 없음
4. ❌ **순서 손실**: `set()` 사용으로 실행 순서 보장 안 됨
5. ❌ **중복 팀 불가**: Q1 요구사항 (search³-analysis) 미지원
6. ❌ **ExecutionOrchestrator 미통합**: 도구 중복 방지 기능 비활성화

### 해결 방안

**Phase 1: 긴급 수정** (2-3시간)
- Priority 필드 추가
- 실행 순서 보장
- LEGAL_CONSULT 키워드 필터

**Phase 2: Execute Node 고도화** (1일)
- Think Node 추가 (미구현 단계)
- Execute Node 세분화 (pre/loop/post)
- ExecutionOrchestrator 통합 (선택)

**Phase 3: 장기 개선** (선택)
- 2단계 분류 (Intent complexity)
- Few-Shot Learning
- 프롬프트 동기화

---

## 🎯 Phase 1: 긴급 수정 (2-3시간)

### 목표
현재 발견된 Agent Routing 문제 즉시 해결

### 1.1 Priority 필드 추가 ⭐⭐⭐⭐⭐

**파일**: `team_supervisor.py` Line 322-346

**Before**:
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "step_type": self._get_step_type_for_agent(step.agent_name),
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        # ❌ priority 없음!
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
        "priority": step.priority,  # ✅ 추가!
        ...
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**TypedDict 정의 추가**:

**파일**: `separated_states.py`

```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str
    priority: int  # ✅ 추가!
    task: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    progress_percentage: int
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
```

### 1.2 실행 순서 보장 ⭐⭐⭐⭐⭐

**파일**: `team_supervisor.py`

#### 수정 1: active_teams 생성 (Line 362-369)

**Before**:
```python
# 활성화할 팀 결정
active_teams = set()  # ❌ 순서 손실
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)  # ❌ 순서 보장 안 됨
```

**After (Option A - 순서 유지, 중복 제거)**:
```python
# 활성화할 팀 결정 (순서 유지, 중복 제거)
active_teams = []
seen_teams = set()

# priority 순으로 정렬 (중요!)
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

logger.info(f"[TeamSupervisor] Active teams (ordered by priority): {active_teams}")
```

**After (Option B - 중복 팀 허용, Q1 요구사항)**:
```python
# 활성화할 팀 결정 (중복 허용, priority 순서 유지)
# Q1 요구사항: 같은 팀 여러번 실행 가능 (search-analysis-search)

# execution_steps를 그대로 사용 (팀이 아닌 step 기반 실행)
state["active_steps"] = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

logger.info(f"[TeamSupervisor] Active steps: {len(state['active_steps'])} (allowing duplicate teams)")
```

**권장**: Option B (중복 팀 허용)

#### 수정 2: _execute_teams_sequential 변경 (Line 627-729)

**Before**:
```python
async def _execute_teams_sequential(
    self,
    teams: List[str],  # ❌ 팀 이름 리스트
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    results = {}
    planning_state = main_state.get("planning_state")

    for team_name in teams:  # ❌ 순서 보장 안 됨
        if team_name in self.teams:
            step_id = self._find_step_id_for_team(team_name, planning_state)  # ❌ 첫 번째만 반환
            ...
```

**After (Option A - 순서만 보장)**:
```python
async def _execute_teams_sequential(
    self,
    teams: List[str],  # ✅ 이미 priority 순으로 정렬됨
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    results = {}
    planning_state = main_state.get("planning_state")

    for team_name in teams:  # ✅ priority 순서대로 실행
        if team_name in self.teams:
            step_id = self._find_step_id_for_team(team_name, planning_state)

            logger.info(f"[TeamSupervisor] Executing {team_name} (step_id: {step_id})")
            ...
```

**After (Option B - 중복 팀 허용, 권장!)**:
```python
async def _execute_steps_sequential(  # ✅ 이름 변경: teams → steps
    self,
    steps: List[Dict],  # ✅ execution_steps 리스트
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """Step 순차 실행 (중복 팀 허용, priority 순서 보장)"""
    results = {}
    planning_state = main_state.get("planning_state")

    # ✅ 이미 priority 순으로 정렬된 steps
    for step in steps:
        step_id = step["step_id"]
        team_name = step["team"]
        priority = step.get("priority", 999)

        logger.info(f"[TeamSupervisor] Executing {team_name} (step_id: {step_id}, priority: {priority})")

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
                    await self._send_todo_update(main_state, "in_progress", step_id)

                # ✅ 팀 실행
                result = await self._execute_single_team(team_name, shared_state, main_state, step_id)

                # ✅ 결과 저장 (step_id를 키로 사용, 중복 팀 대응)
                results[step_id] = result

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
                    await self._send_todo_update(main_state, "completed", step_id)

                logger.info(f"[TeamSupervisor] Step '{step_id}' ({team_name}) completed")

                # ✅ 데이터 전달 (step_id 기반)
                main_state["step_results"] = main_state.get("step_results", {})
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
                    await self._send_todo_update(main_state, "failed", step_id)

                results[step_id] = {"status": "failed", "error": str(e)}

    return results

async def _send_todo_update(self, state: MainSupervisorState, status: str, step_id: str):
    """WebSocket TODO 업데이트 전송 (헬퍼 메서드)"""
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id)
    if progress_callback:
        try:
            await progress_callback("todo_updated", {
                "execution_steps": state["planning_state"]["execution_steps"]
            })
            logger.debug(f"[TeamSupervisor] Sent todo_updated ({status}) for {step_id}")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send todo_updated: {e}")
```

#### 수정 3: execute_teams_node 호출 변경 (Line 586-592)

**Before**:
```python
# 팀별 실행
if execution_strategy == "parallel" and len(active_teams) > 1:
    # 병렬 실행
    results = await self._execute_teams_parallel(active_teams, shared_state, state)
else:
    # 순차 실행
    results = await self._execute_teams_sequential(active_teams, shared_state, state)
```

**After (Option B)**:
```python
# Step 기반 실행 (중복 팀 허용)
active_steps = state.get("active_steps", [])

if execution_strategy == "parallel" and len(active_steps) > 1:
    # 병렬 실행 (향후 구현)
    results = await self._execute_steps_parallel(active_steps, shared_state, state)
else:
    # 순차 실행 (priority 순서 보장)
    results = await self._execute_steps_sequential(active_steps, shared_state, state)

# 결과 저장 (step_id → team_name 변환)
for step_id, step_result in results.items():
    # step_id로 팀 이름 찾기
    team_name = None
    for step in active_steps:
        if step["step_id"] == step_id:
            team_name = step["team"]
            break

    if team_name:
        state = StateManager.merge_team_results(state, team_name, step_result)
```

#### 수정 4: _execute_single_team 시그니처 변경

**Before**:
```python
async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
```

**After**:
```python
async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState,
    step_id: str  # ✅ 추가 (로깅 및 추적용)
) -> Any:
    """단일 팀 실행"""
    team = self.teams[team_name]

    logger.info(f"[TeamSupervisor] Executing team '{team_name}' for step '{step_id}'")

    # ... 기존 로직 ...
```

### 1.3 LEGAL_CONSULT 키워드 필터 ⭐⭐⭐⭐

**파일**: `planning_agent.py` Line 297-361

**Before**:
```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    """
    LLM 기반 Agent 추천
    """
    # === LLM 호출 ===
    result = await self.llm_service.complete_json_async(...)
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
    """
    LLM 기반 Agent 추천 - Intent 결과 고려
    """

    # ✅ 추가: LEGAL_CONSULT 키워드 필터
    if intent_type == IntentType.LEGAL_CONSULT:
        # 복잡한 분석이 필요한 키워드 체크
        analysis_needed_keywords = [
            "비교", "분석", "계산", "평가", "추천", "검토",
            "어떻게", "방법", "차이", "장단점", "괜찮아",
            "해야", "대응", "해결", "조치"
        ]

        needs_analysis = any(kw in query for kw in analysis_needed_keywords)

        if not needs_analysis:
            logger.info(f"✅ LEGAL_CONSULT without analysis keywords, using search_team only")
            return ["search_team"]
        else:
            logger.info(f"✅ LEGAL_CONSULT with analysis keywords ({[kw for kw in analysis_needed_keywords if kw in query]}), using search + analysis")
            return ["search_team", "analysis_team"]

    # ✅ 추가: MARKET_INQUIRY 키워드 필터
    if intent_type == IntentType.MARKET_INQUIRY:
        analysis_needed_keywords = ["비교", "분석", "평가", "추천", "차이"]
        needs_analysis = any(kw in query for kw in analysis_needed_keywords)

        if not needs_analysis:
            logger.info(f"✅ MARKET_INQUIRY without analysis keywords, using search_team only")
            return ["search_team"]

    # === 기존 LLM 기반 Agent 선택 로직 ===
    result = await self.llm_service.complete_json_async(
        prompt_name="planning/agent_selection",
        variables={
            "query": query,
            "intent_type": intent_type.value,
            "keywords": keywords,
            "available_agents": AgentRegistry.list_agents(enabled_only=True)
        },
        temperature=0.1,
        max_tokens=400
    )

    selected_agents = result.get("selected_agents", [])
    logger.info(f"LLM selected agents: {selected_agents}")

    return selected_agents
```

### 1.4 Few-Shot 예시 추가 ⭐⭐⭐

**파일**: `agent_selection.txt`

```text
# (기존 내용 유지)

### 예시 4: 경계 케이스 - 단순 법률 질문 ⭐ 중요!
질문: "공인중개사가 할 수 없는 금지행위에는 어떤 것들이 있나요?"
의도: LEGAL_CONSULT
키워드: ["공인중개사", "금지행위"]

**❌ 잘못된 판단**:
- "법률 정보이므로 분석 필요" → ["search_team", "analysis_team"]

**✅ 올바른 판단**:
- 단순 법률 조항 나열 요청
- 비교/평가/계산 불필요
- 검색만으로 충분

**CoT 분석**:
1. 질문 유형: "~에는 어떤 것들이 있나요?" → 나열 요청
2. 복잡도: 낮음 (법률 조항 확인)
3. 분석 키워드 없음: "비교", "분석", "계산", "평가" 등 없음
4. 결론: search_team만 필요

{
    "selected_agents": ["search_team"],
    "reasoning": "법률 조항 나열만 필요, 분석/평가 불요",
    "confidence": 0.9
}

### 예시 5: 경계 케이스 - 법률 + 적용 평가
질문: "우리 계약서의 전세금 인상 조항이 법적으로 문제없나요?"
의도: CONTRACT_REVIEW
키워드: ["계약서", "전세금", "인상", "법적", "문제"]

**❌ 잘못된 판단**:
- "법률 확인만 필요" → ["search_team"]

**✅ 올바른 판단**:
- 법률 확인 필요
- 계약서와 법률 비교 분석 필요
- "괜찮아" → 평가 요청

**CoT 분석**:
1. 질문 유형: "~괜찮나요?" → 평가 요청
2. 복잡도: 높음 (법률 + 계약서 비교)
3. 분석 키워드: "법적으로", "문제없나요" → 평가 필요
4. 결론: search + analysis 필요

{
    "selected_agents": ["search_team", "analysis_team"],
    "reasoning": "법률 확인 후 계약서 분석 및 평가 필요",
    "confidence": 0.85
}

### 예시 6: 경계 케이스 - 단순 시세 조회
질문: "강남구 아파트 전세 시세 알려줘"
의도: MARKET_INQUIRY
키워드: ["강남구", "아파트", "전세", "시세"]

**✅ 올바른 판단**:
- 시세 조회만 필요
- 비교/분석 요청 없음

{
    "selected_agents": ["search_team"],
    "reasoning": "단순 시세 조회",
    "confidence": 0.9
}

### 예시 7: 경계 케이스 - 시세 + 비교
질문: "강남구와 서초구 아파트 시세 비교해줘"
의도: MARKET_INQUIRY
키워드: ["강남구", "서초구", "아파트", "시세", "비교"]

**✅ 올바른 판단**:
- 시세 조회 필요
- "비교해줘" → 분석 필요

{
    "selected_agents": ["search_team", "analysis_team"],
    "reasoning": "시세 조회 후 지역 간 비교 분석 필요",
    "confidence": 0.85
}

## 경계 케이스 판단 원칙 (중요!) ⭐⭐⭐

### 🔍 Search만 필요한 경우
1. **나열 요청**: "~에는 어떤 것들이 있나요?"
2. **단일 정보**: "~가 얼마야?", "~이 뭐야?", "~알려줘"
3. **조항 확인**: "법률상 ~는 어떻게 돼?"
4. **단순 조회**: "시세 알려줘", "조건 알려줘"

### 🔍+📊 Search + Analysis 필요한 경우
1. **비교 요청**: "A와 B 비교", "차이는?"
2. **평가 요청**: "괜찮아?", "문제없어?", "적절해?"
3. **계산 요청**: "얼마나", "몇 %", "한도는"
4. **추천 요청**: "어떻게 해야", "방법은", "대응은"
5. **구체적 상황**: "우리 경우", "이 계약서", "내 상황"
6. **해결책 요청**: "어떻게 해야 해?", "조치는?", "대응 방법은?"

**키워드 체크리스트**:
```
분석 필요 키워드:
- 비교, 차이, 장단점
- 분석, 평가, 검토, 판단
- 계산, 금액, 얼마나, 몇 %
- 추천, 제안, 방법, 조치
- 어떻게, 대응, 해결, 해야
- 괜찮아, 문제없어, 적절해
```
```

---

## 🚀 Phase 2: Execute Node 고도화 (1일)

### 목표
`think - planning - execute` 3단계 구조 완성

### 2.1 현재 구조 vs 목표 구조

**현재**:
```
initialize → planning → execute_teams → aggregate → generate_response
              ↓ LLM 3회   ↓ LLM 0회                    ↓ LLM 1회
```

**목표 (원래 의도)**:
```
initialize → think → planning → execute → aggregate → generate_response
             ↓ LLM    ↓ LLM      ↓ LLM                 ↓ LLM
```

**ExecutionOrchestrator 참고 (reports/execute_node_implemention/)**:
```
pre_execution → team_execution_loop → post_execution
    ↓ LLM            ↓ LLM (각 팀)         ↓ LLM
```

### 2.2 Option A: Think Node 추가 (미구현 단계)

**think_node**: 쿼리 사전 분석 및 전략 수립

**역할**:
1. 쿼리 복잡도 평가
2. 필요한 정보 유형 파악
3. 실행 전략 힌트 제공
4. IRRELEVANT 조기 필터링

**구현**:

```python
async def think_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    Think 노드 - 쿼리 사전 분석
    Planning 전에 실행되어 전략적 힌트 제공
    """
    logger.info("[TeamSupervisor] Think phase")

    state["current_phase"] = "thinking"
    query = state.get("query", "")

    # WebSocket: Think 시작 알림
    await self._send_progress("think_start", {
        "message": "질문을 분석하고 있습니다..."
    }, state)

    # LLM 호출: 쿼리 사전 분석
    think_result = await self.planning_agent.llm_service.complete_json_async(
        prompt_name="thinking/query_analysis",
        variables={
            "query": query
        },
        temperature=0.1,
        max_tokens=300
    )

    # Think 결과 저장
    state["think_result"] = {
        "complexity": think_result.get("complexity", "medium"),  # simple/medium/complex
        "domain": think_result.get("domain", "general"),  # legal/market/loan/contract
        "info_needs": think_result.get("info_needs", []),  # ["법률조항", "시세데이터"]
        "strategy_hint": think_result.get("strategy_hint", "sequential"),
        "is_relevant": think_result.get("is_relevant", True)
    }

    # IRRELEVANT 조기 종료
    if not think_result.get("is_relevant", True):
        logger.info("⚡ Think phase detected IRRELEVANT, early return")
        state["planning_state"] = {
            "analyzed_intent": {
                "intent_type": "irrelevant",
                "confidence": 0.9
            },
            "execution_steps": []
        }
        state["active_teams"] = []
        return state

    logger.info(f"[TeamSupervisor] Think complete: complexity={state['think_result']['complexity']}, domain={state['think_result']['domain']}")

    return state
```

**프롬프트 파일**: `prompts/thinking/query_analysis.txt`

```text
# 역할
당신은 사용자 질문을 사전 분석하는 전략가입니다.

# 입력
사용자 질문: {{query}}

# 작업
다음을 분석하세요:
1. **복잡도** (complexity): simple / medium / complex
   - simple: 단일 정보 확인 ("~이 뭐야?")
   - medium: 여러 정보 조합 ("A와 B 비교")
   - complex: 구체적 상황 + 해결책 ("어떻게 해야 해?")

2. **도메인** (domain): legal / market / loan / contract / general
   - legal: 법률 관련
   - market: 시세/거래 관련
   - loan: 대출 관련
   - contract: 계약서 관련

3. **정보 필요** (info_needs): 필요한 정보 유형 리스트
   - 예: ["법률조항", "시세데이터", "대출금리"]

4. **전략 힌트** (strategy_hint): sequential / parallel
   - sequential: 순차 실행 (의존성 있음)
   - parallel: 병렬 실행 가능 (독립적)

5. **관련성** (is_relevant): true / false
   - false: 부동산과 무관한 질문

# 출력 (JSON)
{
  "complexity": "simple|medium|complex",
  "domain": "legal|market|loan|contract|general",
  "info_needs": ["정보유형1", "정보유형2"],
  "strategy_hint": "sequential|parallel",
  "is_relevant": true|false,
  "reasoning": "판단 근거"
}

# 예시
## 입력
질문: "공인중개사 금지행위는?"

## 출력
{
  "complexity": "simple",
  "domain": "legal",
  "info_needs": ["법률조항"],
  "strategy_hint": "sequential",
  "is_relevant": true,
  "reasoning": "단순 법률 조항 확인"
}
```

**workflow 수정**:
```python
def _build_graph(self):
    workflow = StateGraph(MainSupervisorState)

    # 노드 추가
    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("think", self.think_node)  # ✅ 추가
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("execute_teams", self.execute_teams_node)
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # 엣지 구성
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "think")  # ✅ 추가
    workflow.add_edge("think", "planning")    # ✅ 수정

    # 계획 후 라우팅 (기존과 동일)
    workflow.add_conditional_edges(...)
```

**Planning Node에서 think_result 활용**:
```python
async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    ...

    # Think 결과 활용
    think_result = state.get("think_result", {})
    complexity = think_result.get("complexity", "medium")

    # Intent 분석 시 think_result 전달
    context = {
        "chat_history": chat_history,
        "think_result": think_result  # ✅ 추가
    }

    intent_result = await self.planning_agent.analyze_intent(query, context)

    ...
```

### 2.3 Option B: Execute Node 세분화 (ExecutionOrchestrator 스타일)

**execute_teams_node 분해**:
```
execute_teams_node (현재)
   ↓
pre_execution_node + execute_loop_node + post_execution_node
```

**구현**:

```python
async def pre_execution_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    실행 전 준비 노드
    - 실행 전략 최적화
    - 도구 선택 조율
    """
    logger.info("[TeamSupervisor] Pre-execution phase")

    state["current_phase"] = "pre_execution"

    # ExecutionOrchestrator 통합 (선택)
    if os.getenv("ENABLE_EXECUTION_ORCHESTRATOR", "false") == "true":
        from app.service_agent.cognitive_agents.execution_orchestrator import ExecutionOrchestrator

        if not hasattr(self, 'execution_orchestrator'):
            self.execution_orchestrator = ExecutionOrchestrator(self.llm_context)

        # Orchestration 수행
        state = await self.execution_orchestrator.orchestrate_with_state(
            state,
            progress_callback=self._progress_callbacks.get(state.get("session_id"))
        )

        logger.info("[TeamSupervisor] ExecutionOrchestrator complete")

    return state

async def execute_loop_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    실행 루프 노드 (기존 execute_teams_node 로직)
    """
    logger.info("[TeamSupervisor] Execute loop phase")

    state["current_phase"] = "executing"

    # 기존 execute_teams_node 로직
    ...

    return state

async def post_execution_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    실행 후 검토 노드
    - 결과 품질 평가
    - 누락된 정보 체크
    """
    logger.info("[TeamSupervisor] Post-execution phase")

    state["current_phase"] = "post_execution"

    # LLM 호출: 결과 검토
    aggregated = state.get("aggregated_results", {})
    query = state.get("query", "")

    review_result = await self.planning_agent.llm_service.complete_json_async(
        prompt_name="execution/result_review",
        variables={
            "query": query,
            "results": aggregated
        },
        temperature=0.1,
        max_tokens=300
    )

    state["execution_review"] = {
        "quality_score": review_result.get("quality_score", 0.7),
        "missing_info": review_result.get("missing_info", []),
        "recommendations": review_result.get("recommendations", [])
    }

    logger.info(f"[TeamSupervisor] Execution review: quality={state['execution_review']['quality_score']}")

    return state
```

**workflow 수정**:
```python
def _build_graph(self):
    workflow = StateGraph(MainSupervisorState)

    # 노드 추가
    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("think", self.think_node)  # Option A
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("pre_execution", self.pre_execution_node)  # ✅ 새로운
    workflow.add_node("execute_loop", self.execute_loop_node)    # ✅ 새로운
    workflow.add_node("post_execution", self.post_execution_node) # ✅ 새로운
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # 엣지 구성
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "think")
    workflow.add_edge("think", "planning")

    # 계획 후 라우팅
    workflow.add_conditional_edges(
        "planning",
        self._route_after_planning,
        {
            "execute": "pre_execution",  # ✅ 수정
            "respond": "generate_response"
        }
    )

    # Execute 3단계
    workflow.add_edge("pre_execution", "execute_loop")
    workflow.add_edge("execute_loop", "post_execution")
    workflow.add_edge("post_execution", "aggregate")

    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)

    self.app = workflow.compile()
```

### 2.4 ExecutionOrchestrator 통합 (선택)

**통합 방법**:

1. **환경변수 설정**:
```bash
# .env
ENABLE_EXECUTION_ORCHESTRATOR=true
```

2. **프롬프트 파일 생성**:
```bash
mkdir -p backend/app/service_agent/llm_manager/prompts/orchestration
```

3. **prompts/orchestration/execution_strategy.txt**:
```text
# 역할
Multi-Agent 시스템의 실행 전략을 수립하는 전문가입니다.

# 입력
- 사용자 쿼리: {{query}}
- 실행 단계: {{execution_steps}}
- 이전 결과: {{previous_results}}
- 학습된 패턴: {{learned_patterns}}

# 작업
최적의 실행 전략을 결정하세요:
1. 실행 순서 (sequential/parallel/adaptive)
2. 우선순위 설정
3. 예상 시간

# 출력 (JSON)
{
  "strategy": "sequential|parallel|adaptive",
  "priorities": {"search": 1, "analysis": 2},
  "estimated_times": {"search": 5, "analysis": 10},
  "reasoning": "설명",
  "confidence": 0.8
}
```

4. **prompts/orchestration/tool_selection.txt**:
```text
# 역할
전체 시스템 관점에서 도구 사용을 최적화하는 오케스트레이터입니다.

# 입력
- 쿼리: {{query}}
- 팀: {{team}}
- 이미 선택된 도구: {{already_selected}}
- 도구 성공률: {{tool_success_rates}}

# 작업
1. 중복 방지: 이미 선택된 도구 제외
2. 최적 도구 선택: 성공률 기반
3. 비용-효과 고려

# 출력 (JSON)
{
  "selected_tools": ["legal_search", "market_data"],
  "avoided_duplicates": ["legal_search"],
  "reasoning": "설명"
}
```

5. **pre_execution_node에서 통합**:
```python
async def pre_execution_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """실행 전 준비 - ExecutionOrchestrator 통합"""

    if os.getenv("ENABLE_EXECUTION_ORCHESTRATOR", "false") == "true":
        logger.info("[TeamSupervisor] ExecutionOrchestrator enabled")

        from app.service_agent.cognitive_agents.execution_orchestrator import ExecutionOrchestrator

        if not hasattr(self, 'execution_orchestrator'):
            self.execution_orchestrator = ExecutionOrchestrator(self.llm_context)

        # Orchestration 수행
        state = await self.execution_orchestrator.orchestrate_with_state(
            state,
            progress_callback=self._progress_callbacks.get(state.get("session_id"))
        )

        # orchestration 메타데이터 활용
        orchestration_meta = state.get("orchestration_metadata", {})
        logger.info(f"[TeamSupervisor] Orchestration strategy: {orchestration_meta.get('strategy', {}).get('strategy')}")

    return state
```

---

## 🎯 Phase 3: 장기 개선 (선택)

### 3.1 2단계 분류 (Intent Complexity)

**intent_analysis.txt 수정**:
```text
# 출력 형식
{
  "intent_type": "LEGAL_CONSULT|MARKET_INQUIRY|...",
  "complexity": "simple|medium|complex",  # ✅ 추가
  "requires_analysis": true|false,        # ✅ 추가
  "confidence": 0.85,
  "keywords": ["키워드1", "키워드2"],
  "entities": {"entity_type": "value"},
  "reasoning": "판단 근거"
}

## Complexity 판단 기준

### Simple (단순)
- 단일 사실 확인
- "~이 뭐야?", "~얼마야?"
- 예: "전세금 인상 한도가 얼마야?"
- requires_analysis: false

### Medium (중간)
- 여러 정보 비교
- "A와 B 차이는?"
- 예: "전세와 월세 차이는?"
- requires_analysis: context에 따라

### Complex (복잡)
- 구체적 상황 + 해결책
- "어떻게 해야 해?"
- 예: "집주인이 10억 올려달래. 어떻게 해야 해?"
- requires_analysis: true
```

**agent_selection.txt에서 complexity 활용**:
```text
# 입력
- 의도 분석 결과: {{intent_result}}  # complexity 포함
- 쿼리: {{query}}

# 판단 로직
1. intent_result.requires_analysis가 false면 → search_team만
2. intent_result.complexity가 "simple"이면 → search_team만
3. intent_result.complexity가 "complex"이면 → search + analysis
4. 그 외: 키워드 체크
```

### 3.2 프롬프트 동기화

**intent_analysis.txt**:
```text
## LEGAL_CONSULT 판단 기준

다음 경우 LEGAL_CONSULT로 분류:
1. 법률 조항 확인 (예: "전세금 인상 한도는?")
   → complexity: simple, requires_analysis: false
2. 법률 적용 평가 (예: "우리 계약서는 괜찮아?")
   → complexity: medium, requires_analysis: true
3. 법률 해결책 (예: "법적으로 어떻게 해야 해?")
   → complexity: complex, requires_analysis: true
```

**agent_selection.txt**:
```text
## LEGAL_CONSULT Agent 선택

Intent Analysis에서 LEGAL_CONSULT로 분류된 경우:

1. **법률 조항 확인** (complexity: simple)
   - "~한도는?", "~이 뭐야?"
   → ["search_team"]

2. **법률 적용 평가** (complexity: medium)
   - "우리는~", "이 계약서는~"
   → ["search_team", "analysis_team"]

3. **법률 해결책** (complexity: complex)
   - "어떻게 해야~", "대응 방법은~"
   → ["search_team", "analysis_team"]
```

---

## 📊 구현 우선순위 및 로드맵

### Phase 1: 긴급 수정 (2-3시간) ⭐⭐⭐⭐⭐

**우선순위**: 최고
**시간**: 2-3시간
**효과**: 즉시 문제 해결

**작업**:
1. ✅ Priority 필드 추가 (30분)
2. ✅ 실행 순서 보장 (1시간)
3. ✅ LEGAL_CONSULT 키워드 필터 (30분)
4. ✅ Few-Shot 예시 추가 (30분)

**검증**:
```python
# 테스트 케이스
queries = [
    "공인중개사 금지행위는?",  # 기대: search만
    "우리 계약서는 괜찮아?",   # 기대: search + analysis
    "강남구 시세 알려줘",       # 기대: search만
    "강남구와 서초구 시세 비교"  # 기대: search + analysis
]
```

### Phase 2A: Think Node 추가 (4시간) ⭐⭐⭐⭐

**우선순위**: 높음
**시간**: 4시간
**효과**: 쿼리 사전 분석, IRRELEVANT 조기 필터링

**작업**:
1. think_node 구현 (2시간)
2. query_analysis.txt 프롬프트 작성 (1시간)
3. planning_node와 통합 (1시간)

### Phase 2B: Execute Node 세분화 (6시간) ⭐⭐⭐

**우선순위**: 중간
**시간**: 6시간
**효과**: Execute 단계 고도화, 결과 품질 향상

**작업**:
1. pre_execution_node 구현 (2시간)
2. execute_loop_node 리팩토링 (2시간)
3. post_execution_node 구현 (2시간)

### Phase 2C: ExecutionOrchestrator 통합 (4시간) ⭐⭐

**우선순위**: 낮음 (선택)
**시간**: 4시간
**효과**: 도구 중복 방지, 전역 최적화

**작업**:
1. 프롬프트 파일 생성 (1시간)
2. pre_execution_node 통합 (2시간)
3. 테스트 및 검증 (1시간)

### Phase 3: 장기 개선 (8시간) ⭐

**우선순위**: 낮음
**시간**: 8시간
**효과**: 장기적 정확도 향상

**작업**:
1. 2단계 분류 (4시간)
2. 프롬프트 동기화 (2시간)
3. 테스트 및 검증 (2시간)

---

## 🧪 테스트 계획

### 테스트 케이스 1: 실행 순서 검증

**입력**: "강남구 아파트 시세 확인하고 투자 분석해줘"

**기대 동작**:
```
1. Planning: steps = [
     {step_id: "step_0", team: "search", priority: 0},
     {step_id: "step_1", team: "analysis", priority: 1}
   ]
2. Execute:
   - step_0 (search, priority=0) 먼저 실행
   - step_1 (analysis, priority=1) 나중 실행
3. 로그:
   "Executing search (step_id: step_0, priority: 0)"
   "Executing analysis (step_id: step_1, priority: 1)"
```

**검증**:
```python
assert state["planning_state"]["execution_steps"][0]["priority"] == 0
assert state["planning_state"]["execution_steps"][1]["priority"] == 1
# 로그에서 실행 순서 확인
```

### 테스트 케이스 2: LEGAL_CONSULT 키워드 필터

**입력 A**: "공인중개사 금지행위는?"
**기대**: search_team만

**입력 B**: "우리 계약서는 괜찮아?"
**기대**: search_team + analysis_team

**검증**:
```python
# A
result_a = await supervisor.process_query_streaming("공인중개사 금지행위는?", ...)
assert result_a["planning_state"]["execution_steps"] == [
    {..., "team": "search"}
]

# B
result_b = await supervisor.process_query_streaming("우리 계약서는 괜찮아?", ...)
teams_b = [step["team"] for step in result_b["planning_state"]["execution_steps"]]
assert "search" in teams_b
assert "analysis" in teams_b
```

### 테스트 케이스 3: 중복 팀 실행 (Q1)

**입력**: "법률 검색 → 분석 → 추가 법률 검색"

**PlanningAgent 응답**:
```json
{
  "steps": [
    {"agent_name": "search_team", "priority": 0},
    {"agent_name": "analysis_team", "priority": 1},
    {"agent_name": "search_team", "priority": 2}
  ]
}
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

**검증**:
```python
assert len(state["active_steps"]) == 3
assert state["active_steps"][0]["team"] == "search"
assert state["active_steps"][1]["team"] == "analysis"
assert state["active_steps"][2]["team"] == "search"
```

---

## 📝 수정 파일 요약

### Phase 1: 긴급 수정

**1. team_supervisor.py**:
- Line 322-346: execution_steps에 priority 추가
- Line 362-369: active_teams → active_steps, priority 정렬
- Line 586-592: execute_teams_node 호출 변경
- Line 627-729: _execute_teams_sequential → _execute_steps_sequential

**2. separated_states.py**:
- ExecutionStepState에 priority 필드 추가

**3. planning_agent.py**:
- Line 297-361: _suggest_agents에 키워드 필터 추가

**4. prompts/planning/agent_selection.txt**:
- 경계 케이스 예시 7개 추가
- 판단 원칙 추가

### Phase 2A: Think Node

**1. team_supervisor.py**:
- think_node 메서드 추가
- _build_graph에 think 노드 추가

**2. prompts/thinking/query_analysis.txt** (신규):
- Think Node 프롬프트

### Phase 2B: Execute Node 세분화

**1. team_supervisor.py**:
- pre_execution_node 메서드 추가
- execute_loop_node 메서드 (기존 execute_teams_node 리팩토링)
- post_execution_node 메서드 추가
- _build_graph 수정

**2. prompts/execution/result_review.txt** (신규):
- Post-execution 프롬프트

### Phase 2C: ExecutionOrchestrator 통합

**1. prompts/orchestration/execution_strategy.txt** (신규)
**2. prompts/orchestration/tool_selection.txt** (신규)
**3. team_supervisor.py**:
- pre_execution_node에 ExecutionOrchestrator 통합

---

## 🎯 최종 구조 (Phase 2 완료 후)

```
START
  ↓
initialize_node
  ↓
think_node (LLM #1)
  ├─ 쿼리 복잡도 분석
  ├─ 도메인 파악
  ├─ IRRELEVANT 조기 필터링
  └─ 전략 힌트 제공
  ↓
planning_node (LLM #2-4)
  ├─ Intent Analysis (think_result 활용)
  ├─ Agent Selection (키워드 필터 + Few-Shot)
  └─ Execution Plan (priority 포함)
  ↓
pre_execution_node (LLM #5-N, 선택)
  ├─ ExecutionOrchestrator (선택)
  ├─ 실행 전략 최적화
  └─ 도구 선택 조율
  ↓
execute_loop_node (priority 순서 보장)
  ├─ active_steps 순회 (중복 팀 허용)
  ├─ priority 정렬
  └─ step_id 기반 추적
  ↓
post_execution_node (LLM #N+1)
  ├─ 결과 품질 평가
  ├─ 누락 정보 체크
  └─ 추가 작업 권장
  ↓
aggregate_results_node
  ↓
generate_response_node (LLM #N+2)
  ↓
END
```

**LLM 호출 횟수**:
- Think: 1회
- Planning: 3회 (Intent + Agent + Plan)
- Pre-execution: 0-3회 (ExecutionOrchestrator, 선택)
- Post-execution: 1회
- Response: 1회
- **총**: 6-9회 (기존 10-13회 대비 유사)

---

## ✅ 성공 기준

### Phase 1 성공 기준

1. ✅ **Priority 필드 존재**: execution_steps에 priority 필드 포함
2. ✅ **실행 순서 보장**: step_0 → step_1 → step_2 순서 보장
3. ✅ **LEGAL_CONSULT 정확도**: 단순 질문은 search만, 복잡한 질문은 search+analysis
4. ✅ **로그 검증**: "Executing {team} (step_id: {id}, priority: {p})" 출력

### Phase 2 성공 기준

1. ✅ **Think Node 동작**: think_result에 complexity, domain 포함
2. ✅ **Execute Node 세분화**: pre → loop → post 3단계 동작
3. ✅ **ExecutionOrchestrator 통합**: orchestration_metadata 포함 (선택)

### 전체 성공 기준

1. ✅ **Agent Routing 문제 해결**: Intent vs Selection 모순 소멸
2. ✅ **중복 팀 지원**: search-analysis-search 실행 가능
3. ✅ **응답 시간**: +10-30% 이내 (허용 범위)
4. ✅ **정확도 향상**: 경계 케이스 정확도 80% 이상

---

**작성 완료**: 2025-10-21
**다음 단계**: Phase 1 구현 시작
**예상 완료**: Phase 1 (2-3시간), Phase 2 (1일)
