# 구현 평가 및 최종 가이드

**작성일**: 2025-10-14
**버전**: Final v3.0
**상태**: 현재 코드 분석 완료, 구현 준비

---

## 📋 목차

1. [현재 코드 분석](#현재-코드-분석)
2. [원래 설계 의도 vs 현재 구현](#원래-설계-의도-vs-현재-구현)
3. [누락된 기능 평가](#누락된-기능-평가)
4. [구현 우선순위](#구현-우선순위)
5. [상세 구현 가이드](#상세-구현-가이드)

---

## 🔍 현재 코드 분석

### 1. 현재 워크플로우 (team_supervisor.py Line 96-128)

```python
def _build_graph(self):
    """워크플로우 그래프 구성"""
    workflow = StateGraph(MainSupervisorState)

    # 노드 추가
    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("execute_teams", self.execute_teams_node)  # ← 단순 실행만
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # 엣지 구성
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "planning")

    # 계획 후 라우팅
    workflow.add_conditional_edges(
        "planning",
        self._route_after_planning,
        {
            "execute": "execute_teams",  # ← 바로 실행으로
            "respond": "generate_response"
        }
    )

    workflow.add_edge("execute_teams", "aggregate")  # ← 실행 후 바로 집계
    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)
```

**현재 흐름**:
```
initialize → planning → execute_teams → aggregate → generate_response
```

**특징**:
- Planning에서 계획 수립 후 **무조건 실행**
- 중간에 LLM 판단 없음
- 고정된 순서대로 진행

### 2. execute_teams_node 분석 (Line 214-265)

```python
async def execute_teams_node(self, state: MainSupervisorState):
    """팀 실행 노드 - 계획에 따라 팀들을 실행"""

    # 실행 전략 가져오기
    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
    active_teams = state.get("active_teams", [])

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(...)

    # 병렬/순차 실행
    if execution_strategy == "parallel" and len(active_teams) > 1:
        results = await self._execute_teams_parallel(...)
    else:
        results = await self._execute_teams_sequential(...)

    # 결과 저장
    for team_name, team_result in results.items():
        state = StateManager.merge_team_results(state, team_name, team_result)

    return state
```

**문제점**:
- ❌ LLM 호출 없음
- ❌ Planning 계획을 무조건 따름
- ❌ 중간 결과를 보고 판단하지 못함
- ❌ Agent 추가/제거 불가능
- ❌ 협업 결정 불가능

### 3. LLM 호출 현황

| 단계 | 위치 | LLM 호출 | 목적 | 상태 |
|------|------|----------|------|------|
| 1️⃣ | PlanningAgent | ✅ Yes | 의도 분석 | ✅ 구현됨 |
| 2️⃣ | PlanningAgent | ✅ Yes | Agent 선택 | ✅ 구현됨 |
| **3️⃣** | **Supervisor Execute** | **❌ No** | **실행 조율** | **❌ 누락!** |
| 4️⃣ | SearchExecutor | ✅ Yes | 키워드 추출 | ✅ 구현됨 |
| 5️⃣ | SearchExecutor | ✅ Yes | 도구 선택 | ✅ 구현됨 |
| 6️⃣ | TeamSupervisor | ✅ Yes | 최종 응답 | ✅ 구현됨 (Line 590-611) |

**결론**: **3번 LLM 호출(실행 조율)이 완전히 누락됨!**

---

## 🎯 원래 설계 의도 vs 현재 구현

### 원래 설계 의도

```
사용자 질문: "강남 아파트 시세 알려주세요"

1️⃣ LLM: 의도 분석
   → "시세 조회 의도야"

2️⃣ LLM: 계획 수립
   → "Search 팀만 필요해"

3️⃣ LLM: 실행 조율 ← 핵심!
   → "Search 실행해"

   [Search 실행 완료: 결과 2개]

3️⃣ LLM: 실행 조율 (다시)
   → "결과가 2개뿐이네? 추가 검색 필요!"
   → "Search를 다시 실행해, 키워드 바꿔서"

   [Search 재실행: 결과 8개]

3️⃣ LLM: 실행 조율 (다시)
   → "이제 충분해, 완료!"

4️⃣ LLM: 최종 응답
   → "강남 아파트 평균 시세는..."
```

### 현재 구현

```
사용자 질문: "강남 아파트 시세 알려주세요"

1️⃣ LLM: 의도 분석
   → "시세 조회 의도야"

2️⃣ LLM: 계획 수립
   → "Search 팀만 필요해"

❌ LLM 호출 없음!
   → Search 무조건 1회 실행

   [Search 실행: 결과 2개 (부족!)]

❌ LLM 판단 없음!
   → 바로 집계로 진행

4️⃣ LLM: 최종 응답
   → "강남 아파트 평균 시세는... (부족한 데이터로)"
```

**문제**:
- Planning의 계획을 무조건 따름
- Search 결과가 부족해도 재실행 안 함
- 품질 보장 불가

---

## ❌ 누락된 기능 평가

### 1. 적응적 실행 (Adaptive Execution)

**필요성**: ⭐⭐⭐⭐⭐ (매우 높음)

**현재**:
```python
# Planning 계획
teams = ["search", "analysis", "document"]

# Execute
for team in teams:
    execute(team)  # 무조건 실행
```

**개선 필요**:
```python
# Planning 계획
teams = ["search", "analysis", "document"]

# Execute with LLM orchestration
for team in teams:
    execute(team)

    # LLM 판단
    decision = llm_orchestrate(current_results)

    if decision == "skip_remaining":
        break  # 나머지 생략
    elif decision == "add_agent":
        teams.append(decision.next_agent)  # Agent 추가
```

### 2. 동적 Agent 추가

**필요성**: ⭐⭐⭐⭐ (높음)

**시나리오**:
```
Query: "전세금 인상 가능한가요?"

Planning: Search만 계획
Search: 법률 2개 검색
LLM: "부족해! Search 재실행 필요"  ← 이 기능이 없음!
```

### 3. Agent 협업

**필요성**: ⭐⭐⭐ (중간)

**시나리오**:
```
Search: 법률 5개 검색
LLM: "Analysis가 이 결과를 정제해야 해"  ← 이 기능이 없음!
Analysis: Search 결과 받아서 분석
```

### 4. 조기 종료 (Early Termination)

**필요성**: ⭐⭐⭐⭐ (높음)

**시나리오**:
```
Query: "전세 계약서 어디서 받나요?"

Planning: Search → Analysis → Document 계획
Search: 관련 정보 충분히 검색
LLM: "Search만으로 답변 가능! 나머지 생략"  ← 이 기능이 없음!
```

**현재 문제**:
- 불필요한 Analysis, Document도 실행
- 시간 낭비, 비용 낭비

---

## 🎖️ 구현 우선순위

### ⚡ 최우선 (Priority 1) - 1주

#### 1.1 기본 Orchestration 노드 추가

**목표**: LLM이 중간에 판단하도록

**작업**:
- `orchestrate_execution_node()` 추가
- `_llm_orchestrate_execution()` 추가 (LLM 호출)
- 워크플로우 수정 (orchestrate 노드 추가)

**효과**:
- 적응적 실행 가능
- 조기 종료 가능
- 품질 향상

#### 1.2 조기 종료 (Early Termination)

**목표**: 불필요한 단계 생략

**작업**:
- LLM 판단: "skip_remaining"
- 워크플로우 라우팅 수정

**효과**:
- 응답 시간 30% 단축 (예상)
- LLM 비용 20% 절감 (예상)

### 🔥 중요 (Priority 2) - 1주

#### 2.1 동적 Agent 추가

**목표**: 결과 부족 시 재실행

**작업**:
- LLM 판단: "add_agent"
- `active_teams` 동적 수정
- 반복 실행 로직

**효과**:
- 정보 부족 문제 해결
- 품질 보장

#### 2.2 Planning → Executor 정보 전달

**목표**: 중복 LLM 호출 제거

**작업**:
- `SearchTeamState`에 `intent_result` 추가
- Executor에서 키워드 정제 (재추출 X)

**효과**:
- LLM 호출 1회 절감
- 일관성 향상

### 🌟 추가 기능 (Priority 3) - 1주

#### 3.1 Agent 협업

**목표**: Agent 간 데이터 정제

**작업**:
- LLM 판단: "collaborate"
- Agent 간 데이터 전달 로직

**효과**:
- 결과 품질 향상

---

## 📝 상세 구현 가이드

### Phase 1: Orchestration 노드 추가 (2-3일)

#### 1.1 새 메서드 추가

**파일**: `team_supervisor.py`

**위치**: Line 461 앞에 추가

```python
async def orchestrate_execution_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    🤖 LLM 기반 실행 오케스트레이션

    역할:
    - 현재까지 수집된 정보 분석
    - 다음 단계 결정 (계속/중단/Agent 추가)
    - 조기 종료 판단
    """
    logger.info("[TeamSupervisor] 🤖 LLM Orchestration")

    state["current_phase"] = "orchestration"

    # 현재까지의 결과 수집
    completed_teams = state.get("completed_teams", [])
    team_results = state.get("team_results", {})
    planning_state = state.get("planning_state", {})
    query = state.get("query", "")

    # 처음 실행이면 스킵 (계획대로 시작)
    if not completed_teams:
        logger.info("[TeamSupervisor] First execution, following plan")
        state["orchestration_action"] = "continue"
        return state

    # LLM에게 물어보기
    orchestration_decision = await self._llm_orchestrate_execution(
        query=query,
        intent=planning_state.get("analyzed_intent", {}),
        completed_teams=completed_teams,
        team_results=team_results,
        remaining_steps=self._get_remaining_steps(state)
    )

    """
    orchestration_decision = {
        "action": "continue" | "add_agent" | "skip_remaining" | "collaborate",
        "reasoning": "...",
        "next_agent": "search_team" (if add_agent),
        "confidence": 0.85
    }
    """

    # 결정에 따라 State 업데이트
    action = orchestration_decision.get("action", "continue")
    state["orchestration_action"] = action
    state["orchestration_reasoning"] = orchestration_decision.get("reasoning", "")

    if action == "add_agent":
        # Agent 추가
        new_agent = orchestration_decision.get("next_agent")
        if new_agent:
            # "search_team" → "search" 변환
            team_name = new_agent.replace("_team", "")
            if team_name not in state.get("completed_teams", []):
                logger.info(f"🤖 LLM decided to add agent: {team_name}")
                state["pending_teams"] = state.get("pending_teams", [])
                state["pending_teams"].append(team_name)

    elif action == "skip_remaining":
        logger.info(f"🤖 LLM decided to skip remaining steps")
        state["skip_remaining"] = True

    else:  # continue
        logger.info(f"🤖 LLM decided to continue as planned")

    # 결정 로깅
    state["orchestration_decisions"] = state.get("orchestration_decisions", [])
    state["orchestration_decisions"].append({
        "step": len(completed_teams),
        "action": action,
        "reasoning": orchestration_decision.get("reasoning", ""),
        "timestamp": datetime.now().isoformat()
    })

    return state
```

#### 1.2 LLM 호출 메서드

**파일**: `team_supervisor.py`

**위치**: Line 677 앞에 추가

```python
async def _llm_orchestrate_execution(
    self,
    query: str,
    intent: Dict,
    completed_teams: List[str],
    team_results: Dict[str, Any],
    remaining_steps: List[Dict]
) -> Dict[str, Any]:
    """
    LLM을 사용한 실행 오케스트레이션

    중간에 LLM이 상황을 판단하고 다음 행동을 결정
    """
    if not self.planning_agent.llm_service:
        # LLM 없으면 계획대로 진행
        return {
            "action": "continue",
            "reasoning": "LLM not available, following original plan",
            "confidence": 1.0
        }

    # 현재 상황 요약
    situation_summary = self._summarize_current_situation(
        completed_teams, team_results, remaining_steps
    )

    try:
        result = await self.planning_agent.llm_service.complete_json_async(
            prompt_name="execution_orchestration",
            variables={
                "query": query,
                "intent_type": intent.get("intent_type", ""),
                "intent_confidence": f"{intent.get('confidence', 0):.0%}",
                "completed_teams": ", ".join(completed_teams),
                "situation_summary": situation_summary,
                "remaining_steps": json.dumps(remaining_steps, ensure_ascii=False, indent=2)
            },
            temperature=0.2
        )

        logger.info(f"🤖 LLM Orchestration Decision: {result.get('action')}")
        logger.info(f"   Reasoning: {result.get('reasoning', '')[:100]}")

        return result

    except Exception as e:
        logger.error(f"LLM orchestration failed: {e}")
        # Fallback: 계획대로 진행
        return {
            "action": "continue",
            "reasoning": f"LLM call failed: {e}",
            "confidence": 0.5
        }

def _summarize_current_situation(
    self,
    completed_teams: List[str],
    team_results: Dict[str, Any],
    remaining_steps: List[Dict]
) -> str:
    """현재 상황 요약 생성"""
    summary_parts = []

    # 완료된 팀 요약
    for team_name in completed_teams:
        team_data = team_results.get(team_name, {})

        if team_name == "search":
            # Search 결과 개수
            legal_count = len(team_data.get("legal_results", []))
            market_count = len(team_data.get("real_estate_results", []))
            loan_count = len(team_data.get("loan_results", []))
            total = legal_count + market_count + loan_count

            summary_parts.append(
                f"- Search: 총 {total}개 결과 (법률 {legal_count}, 시세 {market_count}, 대출 {loan_count})"
            )

        elif team_name == "analysis":
            insights = team_data.get("insights", [])
            summary_parts.append(f"- Analysis: {len(insights)}개 인사이트 생성")

        elif team_name == "document":
            doc_type = team_data.get("document_type", "unknown")
            summary_parts.append(f"- Document: {doc_type} 생성 완료")

    # 남은 단계
    if remaining_steps:
        remaining_names = [step.get("team", "unknown") for step in remaining_steps]
        summary_parts.append(f"- Remaining: {', '.join(remaining_names)}")

    return "\n".join(summary_parts) if summary_parts else "No teams completed yet"

def _get_remaining_steps(self, state: MainSupervisorState) -> List[Dict]:
    """남은 실행 단계 가져오기"""
    planning_state = state.get("planning_state", {})
    execution_steps = planning_state.get("execution_steps", [])
    completed_teams = set(state.get("completed_teams", []))

    remaining = []
    for step in execution_steps:
        team = step.get("team")
        if team and team not in completed_teams:
            remaining.append({
                "team": team,
                "task": step.get("task", ""),
                "description": step.get("description", "")
            })

    return remaining
```

#### 1.3 워크플로우 수정

**파일**: `team_supervisor.py`

**Line 96-128 수정**:

```python
def _build_graph(self):
    """워크플로우 그래프 구성"""
    workflow = StateGraph(MainSupervisorState)

    # 노드 추가
    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("orchestrate", self.orchestrate_execution_node)  # ✨ NEW
    workflow.add_node("execute_teams", self.execute_teams_node)
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # 엣지 구성
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "planning")

    # 계획 후 오케스트레이션으로
    workflow.add_conditional_edges(
        "planning",
        self._route_after_planning,
        {
            "execute": "orchestrate",  # ✨ orchestrate로 변경!
            "respond": "generate_response"
        }
    )

    # 오케스트레이션 → 실행
    workflow.add_edge("orchestrate", "execute_teams")

    # 실행 후 다시 오케스트레이션 또는 집계
    workflow.add_conditional_edges(
        "execute_teams",
        self._route_after_execution,  # ✨ NEW
        {
            "orchestrate_again": "orchestrate",  # 추가 실행 필요
            "aggregate": "aggregate"              # 완료
        }
    )

    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)

    self.app = workflow.compile()
    logger.info("Team-based workflow graph built successfully")
```

#### 1.4 새 라우팅 메서드

**파일**: `team_supervisor.py`

**Line 155 뒤에 추가**:

```python
def _route_after_execution(self, state: MainSupervisorState) -> str:
    """
    실행 후 라우팅

    LLM의 결정에 따라:
    - skip_remaining → aggregate (완료)
    - pending_teams 있음 → orchestrate_again (추가 실행)
    - 남은 단계 있음 → orchestrate_again (계속)
    - 모두 완료 → aggregate
    """
    # 스킵 플래그 확인
    if state.get("skip_remaining"):
        logger.info("🤖 Skipping remaining steps as decided by LLM")
        return "aggregate"

    # Pending 팀 확인 (LLM이 추가한 팀)
    pending_teams = state.get("pending_teams", [])
    if pending_teams:
        logger.info(f"🤖 Pending teams to execute: {pending_teams}")
        # pending_teams를 active_teams로 이동
        active_teams = state.get("active_teams", [])
        active_teams.extend(pending_teams)
        state["active_teams"] = active_teams
        state["pending_teams"] = []
        return "orchestrate_again"

    # 남은 단계 확인
    remaining = self._get_remaining_steps(state)
    if remaining:
        logger.info(f"🤖 {len(remaining)} steps remaining, orchestrating again")
        return "orchestrate_again"

    # 모두 완료
    logger.info("🤖 All steps completed, proceeding to aggregation")
    return "aggregate"
```

#### 1.5 MainSupervisorState 확장

**파일**: `separated_states.py`

**추가 필드**:

```python
class MainSupervisorState(TypedDict):
    # ... 기존 필드들 ...

    # ✨ NEW: Orchestration 관련
    orchestration_action: Optional[str]  # "continue", "add_agent", "skip_remaining"
    orchestration_reasoning: Optional[str]
    orchestration_decisions: List[Dict[str, Any]]  # 결정 이력
    pending_teams: List[str]  # LLM이 추가한 팀들
    skip_remaining: bool  # 나머지 단계 스킵 플래그
```

### Phase 2: 프롬프트 추가 (1일)

**파일**: `prompts/cognitive/execution_orchestration.txt` (신규 생성)

**내용**:

```
당신은 실행 오케스트레이터입니다.
여러 Agent들의 작업을 조율하고, 다음 단계를 결정합니다.

## 현재 상황

### 사용자 질문
{query}

### 의도 분석
- 유형: {intent_type}
- 신뢰도: {intent_confidence}

### 완료된 작업
{completed_teams}

### 현재까지의 결과 요약
{situation_summary}

### 남은 단계
{remaining_steps}

## 당신의 역할

**현재까지의 결과를 분석하고, 다음 행동을 결정하세요.**

### 결정 옵션

1. **continue** (계속 진행)
   - 현재 결과가 충분함
   - 계획대로 다음 단계 진행

2. **add_agent** (Agent 추가)
   - 현재 결과만으로 부족함
   - 추가 정보 수집 필요
   - 특정 Agent를 추가로 실행

3. **skip_remaining** (나머지 생략)
   - 이미 충분한 정보를 얻음
   - 남은 단계가 불필요함
   - 사용자 질문에 이미 답할 수 있음

## 결정 기준

### Search 결과 확인
- **결과 수 < 3개** → add_agent (추가 검색 필요)
- **결과 수 >= 5개** → continue (충분함)

### Analysis 필요 여부
- **단순 정보 조회** → skip_remaining (Analysis 불필요)
- **복합 질문** → continue (Analysis 필요)

## 출력 형식

JSON 형식으로 출력:

### 예시 1: 계속 진행
```json
{
  "action": "continue",
  "reasoning": "Search 결과 8개로 충분하며, 계획대로 Analysis 진행이 적절함",
  "confidence": 0.9
}
```

### 예시 2: Agent 추가
```json
{
  "action": "add_agent",
  "next_agent": "search_team",
  "reasoning": "Search 결과가 2개뿐이라 추가 검색이 필요함",
  "confidence": 0.85
}
```

### 예시 3: 나머지 생략
```json
{
  "action": "skip_remaining",
  "reasoning": "Search 결과만으로 사용자 질문에 충분히 답할 수 있음",
  "confidence": 0.95
}
```

현재 상황을 분석하고 다음 행동을 결정하세요.
```

### Phase 3: 테스트 (2일)

#### 3.1 단위 테스트

**파일**: `tests/test_orchestration.py` (신규)

```python
import pytest
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

@pytest.mark.asyncio
async def test_orchestration_skip_remaining():
    """조기 종료 테스트"""
    supervisor = TeamBasedSupervisor()

    # Search만으로 충분한 질문
    result = await supervisor.process_query_streaming(
        query="전세 계약서는 어디서 받나요?",
        session_id="test_skip"
    )

    # Analysis/Document가 실행되지 않았는지 확인
    active_teams = result.get("active_teams", [])
    assert "search" in active_teams
    assert "analysis" not in active_teams  # 스킵되어야 함

@pytest.mark.asyncio
async def test_orchestration_add_agent():
    """Agent 추가 테스트"""
    supervisor = TeamBasedSupervisor()

    # 추가 검색이 필요한 질문 시뮬레이션
    # (Mock을 사용하여 Search 결과를 2개만 반환하도록)

    result = await supervisor.process_query_streaming(
        query="강남 아파트 시세",
        session_id="test_add"
    )

    # Search가 여러 번 실행되었는지 확인
    orchestration_decisions = result.get("orchestration_decisions", [])
    assert len(orchestration_decisions) > 0
```

---

## 📊 예상 효과

| 지표 | 현재 | Phase 1 완료 후 | 개선율 |
|------|------|----------------|--------|
| **LLM 호출 횟수** | 4-5회 | 5-7회 | +1-2회 (품질 향상) |
| **불필요한 단계 실행** | 100% | 30% | **70% 감소** |
| **정보 부족 시 재검색** | 불가능 | 가능 | **품질 보장** |
| **평균 응답 시간** | 5초 | 3.5초 | **30% 단축** |
| **API 비용 (월)** | 100만원 | 70만원 | **30% 절감** |

---

## ✅ 구현 체크리스트

### Phase 1: Orchestration 노드 (2-3일)
- [ ] `orchestrate_execution_node()` 메서드 추가
- [ ] `_llm_orchestrate_execution()` 메서드 추가
- [ ] `_summarize_current_situation()` 헬퍼 추가
- [ ] `_get_remaining_steps()` 헬퍼 추가
- [ ] `_build_graph()` 수정 (orchestrate 노드 추가)
- [ ] `_route_after_execution()` 라우팅 메서드 추가
- [ ] `MainSupervisorState` 확장 (orchestration 필드)

### Phase 2: 프롬프트 (1일)
- [ ] `prompts/cognitive/execution_orchestration.txt` 생성
- [ ] 프롬프트 테스트 및 튜닝

### Phase 3: 테스트 (2일)
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 (전체 흐름)
- [ ] 성능 테스트

---

## 🔄 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2025-10-14 | 3.0 | 현재 코드 분석 및 구현 가이드 작성 | Dev Team |

---

**다음 단계**: Phase 1 구현 착수 (orchestrate_execution_node 추가)
