# 원래 설계 의도: LLM 기반 다단계 결정 구조

**작성일**: 2025-10-14
**버전**: Final v2.0
**상태**: 원래 설계 의도 복원

---

## 🎯 원래 설계 의도

### LLM 호출이 5단계에서 일어나야 함

```
1️⃣ LLM 호출: 의도 분석 (Planning)
   "사용자가 무엇을 원하는가?"

2️⃣ LLM 호출: 계획 수립 (Planning)
   "어떤 팀들을 어떤 순서로 실행할까?"

3️⃣ LLM 호출: 실행 조율 (Supervisor Execute)  ✨ 핵심!
   "지금까지 결과를 보고 다음 단계는?"
   "Agent들이 협업해야 하나?"
   "추가 검색이 필요한가?"

4️⃣ LLM 호출: Agent 도구 선택 (각 Agent)
   "내가 사용할 도구는?"

5️⃣ LLM 호출: 최종 메시지 출력 (Response)
   "사용자에게 어떻게 설명할까?"
```

---

## 🔍 현재 문제점

### 3️⃣번 LLM 호출이 누락됨!

**현재 코드** (team_supervisor.py Line 513-564):
```python
async def execute_teams_node(self, state: MainSupervisorState):
    """팀 실행 노드"""
    # ❌ 계획대로 무조건 실행
    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
    active_teams = state.get("active_teams", [])

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(...)

    # ❌ LLM 없이 그냥 실행
    if execution_strategy == "parallel":
        results = await self._execute_teams_parallel(active_teams, shared_state, state)
    else:
        results = await self._execute_teams_sequential(active_teams, shared_state, state)

    # 결과 저장
    for team_name, team_result in results.items():
        state = StateManager.merge_team_results(state, team_name, team_result)

    return state
```

**문제점**:
- Planning에서 만든 계획을 **무조건** 따라감
- 중간에 상황 변화를 감지하지 못함
- Agent 간 협업 여부를 동적으로 결정하지 못함
- Search 결과를 보고 Analysis가 필요한지 판단하지 못함

---

## ✅ 원래 의도대로 수정

### 1. 새로운 노드 추가: `orchestrate_execution_node`

**위치**: team_supervisor.py

**역할**: LLM이 실행 중간에 결정을 내림

```python
async def orchestrate_execution_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    🤖 LLM 기반 실행 오케스트레이션

    역할:
    1. 현재까지 수집된 정보 분석
    2. 다음 단계 결정 (계속/중단/Agent 추가)
    3. Agent 간 협업 필요 여부 판단
    4. 추가 정보 수집 필요 여부 판단
    """
    logger.info("[TeamSupervisor] 🤖 LLM Orchestration")

    # 현재까지의 결과 수집
    completed_teams = state.get("completed_teams", [])
    team_results = state.get("team_results", {})
    planning_state = state.get("planning_state", {})
    query = state.get("query", "")

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
        "reasoning": "Search 결과가 충분하지 않아 추가 검색이 필요함",
        "next_agent": "analysis_team",
        "collaboration_needed": {
            "primary_agent": "analysis_team",
            "supporting_agent": "search_team",
            "collaboration_type": "data_refinement"
        },
        "confidence": 0.85
    }
    """

    # 결정에 따라 실행 계획 수정
    action = orchestration_decision.get("action", "continue")

    if action == "add_agent":
        # Agent 추가
        new_agent = orchestration_decision.get("next_agent")
        if new_agent and new_agent not in state["active_teams"]:
            state["active_teams"].append(new_agent)
            logger.info(f"🤖 LLM decided to add agent: {new_agent}")

    elif action == "collaborate":
        # Agent 협업 필요
        collaboration = orchestration_decision.get("collaboration_needed", {})
        state["collaboration_plan"] = collaboration
        logger.info(f"🤖 LLM decided agents should collaborate: {collaboration}")

    elif action == "skip_remaining":
        # 나머지 단계 스킵
        logger.info(f"🤖 LLM decided to skip remaining steps")
        state["skip_remaining"] = True

    else:  # continue
        logger.info(f"🤖 LLM decided to continue as planned")

    # 결정 로깅
    state["orchestration_decisions"] = state.get("orchestration_decisions", [])
    state["orchestration_decisions"].append({
        "step": len(completed_teams),
        "decision": orchestration_decision,
        "timestamp": datetime.now().isoformat()
    })

    return state
```

### 2. LLM 호출 메서드: `_llm_orchestrate_execution`

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
            prompt_name="execution_orchestration",  # ✨ 새 프롬프트
            variables={
                "query": query,
                "intent_type": intent.get("intent_type", ""),
                "intent_confidence": f"{intent.get('confidence', 0):.0%}",
                "completed_teams": ", ".join(completed_teams),
                "situation_summary": situation_summary,
                "remaining_steps": json.dumps(remaining_steps, ensure_ascii=False)
            },
            temperature=0.2  # 낮은 temperature (일관된 결정)
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
        status = team_data.get("status", "unknown")

        if team_name == "search":
            total_results = team_data.get("data", {}).get("total_results", 0)
            summary_parts.append(f"- Search: {total_results}개 결과 발견 ({status})")

        elif team_name == "analysis":
            insights_count = len(team_data.get("data", {}).get("insights", []))
            summary_parts.append(f"- Analysis: {insights_count}개 인사이트 생성 ({status})")

        elif team_name == "document":
            doc_type = team_data.get("data", {}).get("document_type", "unknown")
            summary_parts.append(f"- Document: {doc_type} 생성 ({status})")

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

### 3. 워크플로우 수정

**기존 워크플로우**:
```
planning → execute_teams → aggregate → generate_response
```

**새 워크플로우**:
```
planning → orchestrate_execution → execute_teams →
  → orchestrate_execution (반복) → execute_teams (반복) →
  → aggregate → generate_response
```

**코드**:
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
            "orchestrate": "orchestrate",  # ✨ NEW
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

def _route_after_planning(self, state: MainSupervisorState) -> str:
    """계획 후 라우팅"""
    planning_state = state.get("planning_state")

    # IRRELEVANT/UNCLEAR는 바로 응답
    if planning_state:
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")

        if intent_type in ["irrelevant", "unclear"]:
            return "respond"

    # 정상적인 경우 오케스트레이션으로
    if planning_state and planning_state.get("execution_steps"):
        return "orchestrate"  # ✨ 오케스트레이션 시작

    return "respond"

def _route_after_execution(self, state: MainSupervisorState) -> str:
    """
    실행 후 라우팅

    LLM의 결정에 따라:
    - 추가 Agent 실행 필요 → orchestrate_again
    - 완료 → aggregate
    """
    # 스킵 플래그 확인
    if state.get("skip_remaining"):
        logger.info("🤖 Skipping remaining steps as decided by LLM")
        return "aggregate"

    # 남은 단계 확인
    remaining = self._get_remaining_steps(state)
    if remaining:
        logger.info(f"🤖 {len(remaining)} steps remaining, orchestrating again")
        return "orchestrate_again"

    # 모두 완료
    logger.info("🤖 All steps completed, proceeding to aggregation")
    return "aggregate"
```

---

## 📋 새 프롬프트: execution_orchestration.txt

**경로**: `prompts/cognitive/execution_orchestration.txt`

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
   - 추가 조치 불필요

2. **add_agent** (Agent 추가)
   - 현재 결과만으로 부족함
   - 추가 정보 수집 필요
   - 특정 Agent를 추가로 실행해야 함

   예시:
   - Search 결과가 너무 적음 → Search 재실행
   - 법률 정보만 있고 시세가 없음 → Search 추가
   - 분석이 필요함 → Analysis 추가

3. **skip_remaining** (나머지 생략)
   - 이미 충분한 정보를 얻음
   - 남은 단계가 불필요함
   - 사용자 질문에 이미 답할 수 있음

   예시:
   - Search만으로 충분한 답변 가능
   - Analysis 예정이었지만 필요 없음

4. **collaborate** (Agent 협업)
   - 2개 이상의 Agent가 협력해야 함
   - 데이터 정제/보완 필요
   - Agent 간 정보 교환 필요

   예시:
   - Analysis가 Search 결과를 더 상세히 분석
   - Document가 Search/Analysis 결과를 종합

## 결정 기준

### Search 결과 확인
- **결과 수 < 3개** → add_agent (추가 검색 필요)
- **결과 수 >= 5개** → continue (충분함)
- **관련도 낮음** → add_agent (다른 키워드로 재검색)

### Analysis 필요 여부
- **단순 정보 조회** → skip_remaining (Analysis 불필요)
- **복합 질문** → continue (Analysis 필요)
- **리스크 분석 요청** → continue (Analysis 필수)

### Document 필요 여부
- **계약서 작성 요청** → continue (Document 필수)
- **단순 상담** → skip_remaining (Document 불필요)

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
  "reasoning": "Search 결과가 2개뿐이라 추가 검색이 필요함. 다른 키워드로 재검색 필요",
  "confidence": 0.85
}
```

### 예시 3: 나머지 생략
```json
{
  "action": "skip_remaining",
  "reasoning": "Search 결과만으로 사용자 질문에 충분히 답할 수 있음. Analysis 단계는 불필요",
  "confidence": 0.95
}
```

### 예시 4: 협업 필요
```json
{
  "action": "collaborate",
  "collaboration_needed": {
    "primary_agent": "analysis_team",
    "supporting_agent": "search_team",
    "collaboration_type": "data_refinement"
  },
  "reasoning": "Analysis가 Search 결과를 더 상세히 분석하기 위해 협업 필요",
  "confidence": 0.8
}
```

## 중요 원칙

1. **효율성 우선**: 불필요한 단계는 과감히 생략
2. **품질 보장**: 정보가 부족하면 추가 수집
3. **사용자 의도**: 질문의 의도에 맞는 결정
4. **신뢰도 고려**: 낮은 품질의 결과는 보완 필요

현재 상황을 분석하고 다음 행동을 결정하세요.
```

---

## 🎯 예상 효과

### 1. 적응적 실행

**Before (고정 계획)**:
```
Query: "전세금 인상 가능한가요?"

Planning: Search → Analysis → Document 계획
Execute:  Search (5개 결과) → Analysis (불필요) → Document (불필요)
          ↑ 불필요한 단계도 무조건 실행
```

**After (적응적)**:
```
Query: "전세금 인상 가능한가요?"

Planning:      Search → Analysis → Document 계획
Orchestrate:   Search 실행 필요 → 실행
Execute:       Search (5개 결과)
Orchestrate:   🤖 "Search만으로 충분, 나머지 생략"
Skip:          Analysis, Document 생략
Response:      바로 응답 생성
```

### 2. 동적 Agent 추가

**Before (고정)**:
```
Query: "강남 아파트 시세"

Planning: Search만 계획
Execute:  Search (결과 2개, 부족!)
Response: 부족한 정보로 답변
```

**After (동적)**:
```
Query: "강남 아파트 시세"

Planning:      Search만 계획
Orchestrate:   Search 실행 필요 → 실행
Execute:       Search (결과 2개)
Orchestrate:   🤖 "결과 부족, Search 재실행"
Execute:       Search 재실행 (결과 7개)
Orchestrate:   🤖 "충분함, 완료"
Response:      풍부한 정보로 답변
```

### 3. Agent 협업

**Before (독립 실행)**:
```
Search → 결과 A
Analysis → 결과 A를 분석 (A를 받지 못함!)
```

**After (협업)**:
```
Search → 결과 A
Orchestrate: 🤖 "Analysis가 A를 정제해야 함"
Analysis → 결과 A를 받아서 상세 분석
```

---

## 📊 비교표

| 항목 | 기존 (고정 계획) | 개선 (적응적 실행) |
|------|------------------|-------------------|
| **LLM 호출** | 3회 (Planning 2회, Response 1회) | **5회** (Planning 2회, Orchestrate N회, Response 1회) |
| **실행 방식** | Planning 계획대로 무조건 실행 | **중간에 LLM이 판단하여 조정** |
| **불필요한 단계** | 실행됨 (비효율) | **생략 가능 (효율)** |
| **정보 부족 시** | 그대로 진행 (품질 저하) | **Agent 추가 실행 (품질 보장)** |
| **Agent 협업** | 불가능 | **가능** |
| **응답 시간** | 고정 (불필요한 단계도 실행) | **가변 (필요한 만큼만 실행)** |

---

## ✅ 구현 체크리스트

### Phase 1: 노드 추가
- [ ] `orchestrate_execution_node()` 메서드 추가
- [ ] `_llm_orchestrate_execution()` 메서드 추가
- [ ] `_summarize_current_situation()` 헬퍼 메서드 추가
- [ ] `_get_remaining_steps()` 헬퍼 메서드 추가

### Phase 2: 워크플로우 수정
- [ ] `_build_graph()` 수정 (orchestrate 노드 추가)
- [ ] `_route_after_planning()` 수정 (orchestrate로 라우팅)
- [ ] `_route_after_execution()` 추가 (반복 또는 완료 결정)

### Phase 3: State 확장
- [ ] `MainSupervisorState`에 `orchestration_decisions` 필드 추가
- [ ] `MainSupervisorState`에 `collaboration_plan` 필드 추가
- [ ] `MainSupervisorState`에 `skip_remaining` 필드 추가

### Phase 4: 프롬프트 추가
- [ ] `prompts/cognitive/execution_orchestration.txt` 생성
- [ ] 프롬프트 테스트 및 튜닝

### Phase 5: 테스트
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 (전체 흐름)
- [ ] 성능 테스트 (LLM 호출 횟수, 응답 시간)

---

## 📅 일정

| Phase | 작업 | 기간 | 담당 |
|-------|------|------|------|
| Phase 1 | 노드 및 메서드 추가 | 2일 | Dev |
| Phase 2 | 워크플로우 수정 | 1일 | Dev |
| Phase 3 | State 확장 | 1일 | Dev |
| Phase 4 | 프롬프트 추가 | 1일 | Dev |
| Phase 5 | 테스트 | 2일 | QA |
| **총** | | **7일** | |

---

## 🔄 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2025-10-14 | 2.0 | 원래 설계 의도 반영 (LLM 기반 실행 오케스트레이션 추가) | Dev Team |

---

**핵심**: TeamSupervisor의 execute 단계에서 **LLM이 중간 결과를 보고 다음 행동을 결정**하도록 수정!
