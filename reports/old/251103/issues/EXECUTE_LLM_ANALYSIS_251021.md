# Execute 단계 LLM 호출 필요성 분석

**작성일**: 2025-10-21
**질문**: execute에서 LLM을 호출하는 것이 필요한가?

---

## 📋 현재 구조 분석

### 현재 LLM 호출 지점

```
initialize_node         (LLM 0회)
  ↓
planning_node           (LLM 3회) ✅ PlanningAgent
  ├─ analyze_intent()          # LLM #1
  ├─ _suggest_agents()          # LLM #2
  └─ create_execution_plan()   # LLM #3
  ↓
execute_teams_node      (LLM 0회) ❌ 단순 실행
  ├─ _execute_teams_sequential()
  └─ _execute_single_team()
      ├─ SearchExecutor.execute()     # LLM 2회 (내부)
      ├─ AnalysisExecutor.execute()   # LLM 3-5회 (내부)
      └─ DocumentExecutor.execute()   # LLM 1-2회 (내부)
  ↓
aggregate_results_node  (LLM 0회) ❌ 단순 집계
  ↓
generate_response_node  (LLM 1회) ✅
```

**총 LLM 호출**: 10-13회
- Planning: 3회
- Execute (내부 Executor): 6-9회
- Response: 1회

---

## 🤔 Execute에서 LLM을 호출해야 하는가?

### Option 1: 현재 방식 유지 (권장) ⭐⭐⭐⭐⭐

**현재**: execute_teams_node는 **단순 실행기 (Executor)**

```python
async def execute_teams_node(self, state):
    # 1. Planning이 만든 계획 읽기
    active_teams = state.get("active_teams", [])

    # 2. 순서대로 실행 (LLM 호출 없음)
    for team in active_teams:
        result = await self._execute_single_team(team, ...)

    # 3. 결과 저장
    return state
```

**장점**:
1. ✅ **단순함**: 계획-실행 분리 (SRP: Single Responsibility Principle)
2. ✅ **예측 가능**: Planning이 결정, Execute는 실행만
3. ✅ **디버깅 용이**: 문제 발생 시 Planning vs Execute 명확히 구분
4. ✅ **성능**: 불필요한 LLM 호출 최소화
5. ✅ **비용**: LLM 호출 줄여 비용 절감

**단점**:
1. ❌ **유연성 부족**: 실행 중 동적 조정 불가
2. ❌ **에러 대응 제한**: 팀 실패 시 대안 전략 없음

**적합한 경우**:
- ✅ Planning이 이미 충분히 정확함
- ✅ 실행 중 변화가 적음
- ✅ 비용/성능 중요

---

### Option 2: Execute에 LLM 추가 (고도화) ⭐⭐⭐⭐

**개선**: execute_teams_node가 **지능형 오케스트레이터**

#### 2-1. Pre-execution LLM (실행 전 검토)

**목적**: Planning 결과 검증 및 최적화

```python
async def execute_teams_node(self, state):
    # ✅ LLM 호출 #1: 실행 전 검토
    execution_review = await self._review_execution_plan(state)

    if execution_review["needs_adjustment"]:
        # Planning 계획 조정
        state = self._adjust_execution_plan(state, execution_review)

    # 실행
    for team in active_teams:
        result = await self._execute_single_team(team, ...)

    return state

async def _review_execution_plan(self, state):
    """실행 전 계획 검토 (LLM)"""
    plan = state["planning_state"]["execution_steps"]
    query = state["query"]

    result = await self.llm_service.complete_json_async(
        prompt_name="execution/pre_execution_review",
        variables={
            "query": query,
            "execution_plan": plan
        },
        temperature=0.1,
        max_tokens=300
    )

    return {
        "needs_adjustment": result.get("needs_adjustment", False),
        "adjustments": result.get("adjustments", []),
        "reasoning": result.get("reasoning", "")
    }
```

**Prompt**: `execution/pre_execution_review.txt`
```text
# 역할
실행 계획을 검토하고 문제를 찾는 검토자

# 입력
질문: {{query}}
계획: {{execution_plan}}

# 작업
다음을 체크하세요:
1. 실행 순서가 올바른가?
2. 필요한 팀이 빠졌는가?
3. 불필요한 팀이 있는가?

# 출력 (JSON)
{
  "needs_adjustment": true|false,
  "adjustments": [
    {"type": "reorder", "reason": "search가 analysis보다 먼저 실행되어야 함"},
    {"type": "add_team", "team": "document", "reason": "계약서 작성 필요"},
    {"type": "remove_team", "team": "analysis", "reason": "단순 조회로 충분"}
  ],
  "reasoning": "검토 결과 설명"
}
```

**장점**:
- ✅ Planning 오류 보정
- ✅ 실행 전 검증

**단점**:
- ❌ LLM 호출 +1회
- ❌ Planning과 역할 중복

**적합한 경우**:
- Planning의 정확도가 낮을 때
- 복잡한 쿼리가 많을 때

---

#### 2-2. Mid-execution LLM (실행 중 조정)

**목적**: 팀 실행 후 다음 단계 결정

```python
async def execute_teams_node(self, state):
    active_teams = state.get("active_teams", [])

    for i, team in enumerate(active_teams):
        # 팀 실행
        result = await self._execute_single_team(team, ...)

        # ✅ LLM 호출: 중간 결과 평가
        if i < len(active_teams) - 1:  # 마지막 팀 아니면
            evaluation = await self._evaluate_intermediate_result(
                team, result, remaining_teams=active_teams[i+1:]
            )

            if evaluation["should_skip_next"]:
                # 다음 팀 스킵 (예: search 결과가 충분하면 analysis 스킵)
                logger.info(f"Skipping {active_teams[i+1]} based on {team} result")
                continue

            if evaluation["should_add_team"]:
                # 새 팀 추가
                active_teams.insert(i+1, evaluation["team_to_add"])

    return state

async def _evaluate_intermediate_result(self, team, result, remaining_teams):
    """중간 결과 평가 (LLM)"""
    result_summary = self._summarize_result(result)

    llm_result = await self.llm_service.complete_json_async(
        prompt_name="execution/mid_execution_evaluation",
        variables={
            "completed_team": team,
            "result_summary": result_summary,
            "remaining_teams": remaining_teams
        },
        temperature=0.1,
        max_tokens=300
    )

    return {
        "should_skip_next": llm_result.get("should_skip_next", False),
        "should_add_team": llm_result.get("should_add_team", False),
        "team_to_add": llm_result.get("team_to_add"),
        "reasoning": llm_result.get("reasoning", "")
    }
```

**Prompt**: `execution/mid_execution_evaluation.txt`
```text
# 역할
팀 실행 결과를 평가하고 다음 단계를 결정하는 조율자

# 입력
완료된 팀: {{completed_team}}
결과 요약: {{result_summary}}
남은 팀: {{remaining_teams}}

# 작업
완료된 팀의 결과를 보고 판단하세요:
1. 결과가 충분한가? (다음 팀 스킵 가능?)
2. 추가 팀이 필요한가?
3. 다음 팀을 그대로 실행할 것인가?

# 예시
완료된 팀: search
결과 요약: 법률 조항 10건 검색 완료
남은 팀: [analysis]

판단: 검색 결과가 충분히 많고 명확함. 분석 불필요.

# 출력 (JSON)
{
  "should_skip_next": true,
  "should_add_team": false,
  "team_to_add": null,
  "reasoning": "검색 결과가 충분하여 분석 불필요"
}
```

**장점**:
- ✅ **동적 조정**: 실행 중 계획 변경
- ✅ **효율성**: 불필요한 팀 스킵 (비용 절감)
- ✅ **적응성**: 중간 결과 기반 결정

**단점**:
- ❌ LLM 호출 +N회 (팀 수만큼)
- ❌ 실행 시간 증가
- ❌ 복잡도 증가

**적합한 경우**:
- ✅ 질문이 복잡하고 예측 불가능
- ✅ 팀 간 의존성이 강함
- ✅ 비용보다 정확도가 중요

---

#### 2-3. Post-execution LLM (실행 후 검토)

**목적**: 결과 품질 평가 및 보완

```python
async def execute_teams_node(self, state):
    # 모든 팀 실행
    for team in active_teams:
        result = await self._execute_single_team(team, ...)

    # ✅ LLM 호출: 실행 완료 후 검토
    review = await self._post_execution_review(state)

    if review["quality_low"]:
        # 보완 작업
        if review["retry_team"]:
            # 특정 팀 재실행
            retry_result = await self._execute_single_team(review["retry_team"], ...)

        if review["add_team"]:
            # 새 팀 추가 실행
            new_result = await self._execute_single_team(review["add_team"], ...)

    state["execution_review"] = review
    return state

async def _post_execution_review(self, state):
    """실행 완료 후 검토 (LLM)"""
    query = state["query"]
    results = state["team_results"]

    llm_result = await self.llm_service.complete_json_async(
        prompt_name="execution/post_execution_review",
        variables={
            "query": query,
            "results": self._summarize_results(results)
        },
        temperature=0.1,
        max_tokens=400
    )

    return {
        "quality_low": llm_result.get("quality_score", 0.7) < 0.5,
        "quality_score": llm_result.get("quality_score", 0.7),
        "missing_info": llm_result.get("missing_info", []),
        "retry_team": llm_result.get("retry_team"),
        "add_team": llm_result.get("add_team"),
        "reasoning": llm_result.get("reasoning", "")
    }
```

**Prompt**: `execution/post_execution_review.txt`
```text
# 역할
모든 팀 실행 후 결과를 종합 검토하는 품질 관리자

# 입력
질문: {{query}}
실행 결과: {{results}}

# 작업
1. 질문에 답하기 충분한 정보가 모였는가?
2. 누락된 정보가 있는가?
3. 품질이 낮은 결과가 있는가?

# 출력 (JSON)
{
  "quality_score": 0.8,
  "missing_info": ["대출 금리 정보"],
  "retry_team": null,
  "add_team": "search",
  "reasoning": "법률 정보는 충분하나 대출 금리 정보 부족"
}
```

**장점**:
- ✅ **품질 보장**: 결과 검증
- ✅ **보완 기회**: 부족한 부분 재실행

**단점**:
- ❌ LLM 호출 +1회
- ❌ 실행 시간 증가 (재실행 시)

**적합한 경우**:
- ✅ 결과 품질이 중요
- ✅ 재실행 비용이 허용 가능

---

### Option 3: ExecutionOrchestrator 통합 (미구현 활용) ⭐⭐⭐

**방법**: 이미 구현된 `execution_orchestrator.py` 활용

```python
async def execute_teams_node(self, state):
    # ExecutionOrchestrator 사용
    from app.service_agent.cognitive_agents.execution_orchestrator import ExecutionOrchestrator

    if not hasattr(self, 'orchestrator'):
        self.orchestrator = ExecutionOrchestrator(self.llm_context)

    # ✅ Pre-execution: 실행 전 최적화
    state = await self.orchestrator.orchestrate_with_state(
        state,
        progress_callback=self._progress_callbacks.get(state["session_id"])
    )

    # 실행 (기존 로직)
    for team in active_teams:
        result = await self._execute_single_team(team, ...)

        # ✅ Mid-execution: 팀 실행 후 분석
        state = await self.orchestrator.analyze_team_result(
            state, team, result, progress_callback
        )

    return state
```

**장점**:
- ✅ **이미 구현됨**: 516줄 완성 코드
- ✅ **도구 중복 방지**: 전역 관점 최적화
- ✅ **학습 기능**: 사용자 패턴 Memory 저장

**단점**:
- ❌ LLM 호출 +2-3회
- ❌ 프롬프트 파일 작성 필요

---

## 📊 비교 분석

| 방식 | LLM 호출 | 복잡도 | 유연성 | 비용 | 품질 | 권장도 |
|-----|---------|--------|--------|------|------|--------|
| **Option 1: 현재 유지** | 0회 | 낮음 | 낮음 | 최저 | 중간 | ⭐⭐⭐⭐⭐ |
| **Option 2-1: Pre-execution** | +1회 | 중간 | 중간 | 낮음 | 높음 | ⭐⭐⭐⭐ |
| **Option 2-2: Mid-execution** | +N회 | 높음 | 높음 | 높음 | 최고 | ⭐⭐⭐ |
| **Option 2-3: Post-execution** | +1회 | 중간 | 중간 | 중간 | 높음 | ⭐⭐⭐⭐ |
| **Option 3: Orchestrator** | +2-3회 | 중간 | 높음 | 중간 | 높음 | ⭐⭐⭐⭐ |

---

## 🎯 상황별 권장 방안

### 현재 Agent Routing 문제에 집중 (긴급)

**권장**: **Option 1 (현재 유지)** ⭐⭐⭐⭐⭐

**이유**:
1. ✅ **문제의 원인이 Execute가 아님**
   - 현재 문제: Planning의 순서 손실 (`set()` 사용)
   - Execute는 Planning의 계획을 잘 실행하고 있음

2. ✅ **Priority 필드 추가만으로 해결 가능**
   ```python
   # Planning에서
   active_teams = sorted(steps, key=lambda x: x["priority"])  # 순서 보장

   # Execute는 그대로 사용
   for team in active_teams:  # ✅ 이미 순서대로 정렬됨
       result = await self._execute_single_team(team, ...)
   ```

3. ✅ **최소 수정 원칙**
   - 사용자 의도: "cognitive_agents는 완성, supervisor의 execute/aggregate만 수정"
   - Execute에 LLM 추가는 과도한 수정

**조치사항**:
- Planning의 priority 순서 보장 (30분)
- Execute는 수정 안 함 (0분)

---

### 장기 개선 (선택)

**권장**: **Option 2-3 (Post-execution)** + **Option 3 (Orchestrator)** ⭐⭐⭐⭐

**이유**:
1. ✅ **단계적 도입**
   - Phase 1: Priority 순서 보장 (현재 문제 해결)
   - Phase 2: Post-execution 검토 (품질 향상)
   - Phase 3: ExecutionOrchestrator 통합 (도구 최적화)

2. ✅ **실용성**
   - Post-execution: 결과 품질 보장
   - Orchestrator: 도구 중복 방지 (30% → 0%)

3. ✅ **비용 대비 효과**
   - LLM 호출: +1-2회 (허용 범위)
   - 효과: 품질 향상 + 도구 최적화

**구현 순서**:
```
Phase 1 (긴급):
  - Priority 순서 보장
  - 키워드 필터

Phase 2 (중기):
  - Post-execution 검토 LLM 추가
  - aggregate_results_node에 품질 평가 추가

Phase 3 (장기):
  - ExecutionOrchestrator 통합
  - 프롬프트 파일 작성
```

---

## 💡 최종 권장: Hybrid 접근

### Phase 1: 현재 문제 해결 (2-3시간)

**Execute에 LLM 추가 안 함!** ✅

```python
# planning_node: priority 순서 보장
active_teams = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

# execute_teams_node: 수정 없음 (그대로 실행)
for team in active_teams:  # ✅ 이미 순서대로
    result = await self._execute_single_team(team, ...)
```

---

### Phase 2: Aggregate에 LLM 추가 (선택, 4시간)

**aggregate_results_node 개선** ⭐⭐⭐⭐

**현재**:
```python
async def aggregate_results_node(self, state):
    # 단순 집계만
    aggregated = {}
    for team, data in team_results.items():
        aggregated[team] = {"status": "success", "data": data}
    return state
```

**개선**:
```python
async def aggregate_results_node(self, state):
    # 1. 기존 집계
    aggregated = {}
    for team, data in team_results.items():
        aggregated[team] = {"status": "success", "data": data}

    state["aggregated_results"] = aggregated

    # ✅ 2. LLM 추가: 결과 품질 평가
    quality_review = await self._evaluate_aggregated_quality(state)

    state["quality_review"] = quality_review

    # ✅ 3. 품질 낮으면 경고 (Response에서 활용)
    if quality_review["quality_score"] < 0.5:
        state["quality_warning"] = {
            "missing_info": quality_review["missing_info"],
            "recommendations": quality_review["recommendations"]
        }

    return state

async def _evaluate_aggregated_quality(self, state):
    """집계 결과 품질 평가 (LLM)"""
    query = state["query"]
    aggregated = state["aggregated_results"]

    result = await self.planning_agent.llm_service.complete_json_async(
        prompt_name="aggregation/quality_evaluation",
        variables={
            "query": query,
            "aggregated_results": self._summarize_aggregated(aggregated)
        },
        temperature=0.1,
        max_tokens=400
    )

    return {
        "quality_score": result.get("quality_score", 0.7),
        "missing_info": result.get("missing_info", []),
        "recommendations": result.get("recommendations", []),
        "reasoning": result.get("reasoning", "")
    }
```

**Prompt**: `aggregation/quality_evaluation.txt`
```text
# 역할
팀 실행 결과를 종합하여 품질을 평가하는 검토자

# 입력
질문: {{query}}
집계 결과: {{aggregated_results}}

# 작업
1. 질문에 답하기 충분한가?
2. 누락된 정보는?
3. 품질 점수 (0.0-1.0)

# 출력 (JSON)
{
  "quality_score": 0.8,
  "missing_info": ["대출 금리 세부 정보"],
  "recommendations": ["대출 상담 팀 추가 실행 권장"],
  "reasoning": "법률/시세 정보는 충분하나 대출 정보 부족"
}
```

**장점**:
- ✅ Execute는 수정 안 함 (단순 실행 유지)
- ✅ Aggregate에서 품질 평가 (책임 분리)
- ✅ Response에서 경고 메시지 활용 가능
- ✅ LLM 호출 +1회만

---

## 📝 결론

### 질문: "execute에서 LLM을 호출하는 건 어떤가?"

**답변**: **현재는 불필요하지만, 장기적으로 Aggregate에 추가하는 것이 좋습니다.**

### 이유

1. **현재 문제는 Execute가 아님**
   - 문제: Planning의 순서 손실
   - 해결: Priority 필드 추가 (Execute 수정 불필요)

2. **Execute는 이미 잘 작동 중**
   - Planning의 계획을 충실히 실행
   - 단순 실행기로서 역할 명확

3. **LLM 추가 시 적절한 위치는 Aggregate**
   - Execute: 실행만 담당
   - Aggregate: 결과 검토 및 품질 평가
   - 책임 분리 (SRP)

### 최종 권장 구조

```
planning_node (LLM 3회)
  ├─ Intent Analysis
  ├─ Agent Selection
  └─ Execution Plan (priority 포함) ✅
  ↓
execute_teams_node (LLM 0회) ✅ 단순 실행
  └─ priority 순서대로 실행 ✅
  ↓
aggregate_results_node (LLM 1회) ⭐ 개선 권장
  ├─ 결과 집계
  └─ 품질 평가 (LLM) ✅
  ↓
generate_response_node (LLM 1회)
  └─ 품질 경고 반영 ✅
```

**LLM 호출**: 10-13회 → 11-14회 (+1회만, Aggregate에서)

---

**작성 완료**: 2025-10-21
**권장**: Phase 1 (Execute 수정 안 함) + Phase 2 (Aggregate LLM 추가, 선택)
