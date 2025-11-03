# 현재 상황 명확한 분석

**작성일**: 2025-10-21
**목적**: 복잡한 분석 제거, 명확한 사실만 정리

---

## 1️⃣ 현재 코드 상태 (AS-IS)

### 실제 로그 (2025-10-21 11:09)

```log
11:09:33 - Intent Analysis Result:
  'reasoning': "검색만으로 충분 → LEGAL_CONSULT"

11:09:37 - Agent Selection reasoning:
  "단순 법률 검색만으로는 충분하지 않으며, 분석이 필요함"

11:09:37 - ✅ Primary LLM selected agents: ['search_team', 'analysis_team']

11:09:37 - [TeamSupervisor] Plan created: 2 steps, 2 teams

11:09:37 - [TeamSupervisor] Executing 2 teams sequentially

11:09:37 - Step step_1 status: pending -> in_progress    ← analysis 먼저
11:09:50 - Step step_1 status: in_progress -> completed

11:09:50 - Step step_0 status: pending -> in_progress    ← search 나중
11:09:53 - Step step_0 status: in_progress -> completed
```

---

## 2️⃣ 발견된 문제 (실제 로그 기준)

### 문제 1: Agent Selection이 Intent와 모순
- **Intent Analysis**: "검색만으로 충분"
- **Agent Selection**: "검색만으로 충분하지 않으며, 분석이 필요함"
- **결과**: analysis_team이 추가됨

### 문제 2: Step 실행 순서 역순
- **기대**: step_0 (search) → step_1 (analysis)
- **실제**: step_1 (analysis) → step_0 (search)

---

## 3️⃣ 현재 코드 확인

### execution_steps 생성 (team_supervisor.py Line 322-346)

```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        ...
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**질문**: execution_plan.steps에 priority가 있나?

### ExecutionStep 정의 (planning_agent.py Line 67-76)

```python
@dataclass
class ExecutionStep:
    agent_name: str
    priority: int  # ← priority 필드 존재!
    dependencies: List[str] = field(default_factory=list)
    ...
```

**답**: ✅ priority 필드 존재

### ExecutionStep 생성 (planning_agent.py Line 654-663)

```python
step = ExecutionStep(
    agent_name=agent_name,
    priority=i,  # ← 0, 1, 2, ...
    dependencies=dependencies,
    ...
)
```

**확인**: priority는 enumerate 순서 (0, 1, 2...)

---

## 4️⃣ active_teams 생성 (team_supervisor.py Line 362-369)

```python
active_teams = set()
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)
```

**문제**:
- set은 순서 보장 안 함
- execution_steps에서 추출한 팀 순서가 보장되지 않음

---

## 5️⃣ 팀 실행 (_execute_teams_sequential Line 627-639)

```python
for team_name in teams:  # teams = state["active_teams"]
    if team_name in self.teams:
        step_id = self._find_step_id_for_team(team_name, planning_state)
        ...
```

**확인**:
- teams 리스트를 순서대로 순회
- teams 리스트의 순서가 잘못되면 실행 순서도 잘못됨

---

## 6️⃣ execution_steps에 priority가 있는가?

### team_supervisor.py Line 322-346 재확인

```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "step_type": self._get_step_type_for_agent(step.agent_name),
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),

        "task": ...,
        "description": ...,

        "status": "pending",
        "progress_percentage": 0,

        "started_at": None,
        "completed_at": None,

        "result": None,
        "error": None
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**❌ priority 필드가 복사되지 않음!**

execution_plan.steps의 각 step은 ExecutionStep 객체이고 priority를 가지고 있지만,
execution_steps Dict를 만들 때 **priority를 복사하지 않았습니다**.

---

## 7️⃣ 근본 원인

### 원인 1: execution_steps에 priority 필드 누락
```python
# 현재 (❌)
execution_steps=[
    {
        "step_id": f"step_{i}",
        ...
        # priority 없음!
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**수정 필요**:
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "priority": step.priority,  # ← 추가!
        ...
    }
    for i, step in enumerate(execution_plan.steps)
]
```

### 원인 2: active_teams가 set 사용
```python
# 현재 (❌)
active_teams = set()  # 순서 없음
for step in planning_state["execution_steps"]:
    active_teams.add(step.get("team"))
state["active_teams"] = list(active_teams)  # 순서 미보장
```

**수정 필요**:
```python
# priority 순으로 정렬 후 중복 제거
sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

active_teams = []
seen = set()
for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen:
        active_teams.append(team)
        seen.add(team)

state["active_teams"] = active_teams
```

### 원인 3: Agent Selection이 Intent 무시
```python
# planning_agent.py Line 297
async def _suggest_agents(...) -> List[str]:
    # LEGAL_CONSULT에 대한 특별 처리 없음
    # 무조건 LLM에게 맡김
    if self.llm_service:
        agents = await self._select_agents_with_llm(...)
        return agents  # LLM이 잘못 판단하면 그대로 반환
```

**수정 필요**:
```python
if intent_type == IntentType.LEGAL_CONSULT:
    # 분석 키워드 체크
    if not any(kw in query for kw in ["분석", "어떻게", "방법", "해야"]):
        return ["search_team"]
```

---

## 8️⃣ 수정 방안

### 수정 1: execution_steps에 priority 추가

**파일**: team_supervisor.py
**위치**: Line 322-346

```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "step_type": self._get_step_type_for_agent(step.agent_name),
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        "priority": step.priority,  # ✅ 추가!

        "task": self._get_task_name_for_agent(step.agent_name, intent_result),
        "description": self._get_task_description_for_agent(step.agent_name, intent_result),

        "status": "pending",
        "progress_percentage": 0,

        "started_at": None,
        "completed_at": None,

        "result": None,
        "error": None
    }
    for i, step in enumerate(execution_plan.steps)
]
```

---

### 수정 2: active_teams 순서 보장

**파일**: team_supervisor.py
**위치**: Line 362-369

```python
# 현재 코드 삭제
# active_teams = set()
# for step in planning_state["execution_steps"]:
#     team = step.get("team")
#     if team:
#         active_teams.add(team)
# state["active_teams"] = list(active_teams)

# 새 코드
sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

active_teams = []
seen_teams = set()
for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)

state["active_teams"] = active_teams

logger.info(f"[TeamSupervisor] Active teams (priority order): {active_teams}")
```

---

### 수정 3: LEGAL_CONSULT 키워드 필터

**파일**: planning_agent.py
**위치**: Line 297 (함수 시작 부분)

```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    # ✅ 추가: LEGAL_CONSULT 단순 질문 필터
    if intent_type == IntentType.LEGAL_CONSULT:
        analysis_keywords = ["분석", "비교", "계산", "평가", "추천", "검토", "어떻게", "방법", "해야", "하면"]
        if not any(kw in query for kw in analysis_keywords):
            logger.info("✅ LEGAL_CONSULT simple query -> search_team only")
            return ["search_team"]

    # 기존 LLM 로직
    if self.llm_service:
        ...
```

---

## 9️⃣ 예상 결과

### 수정 전 (현재)
```log
Selected agents: ['search_team', 'analysis_team']
Step step_1 (analysis) -> in_progress
Step step_1 (analysis) -> completed
Step step_0 (search) -> in_progress
Step step_0 (search) -> completed
```

### 수정 후 (기대)
```log
Selected agents: ['search_team']  ← 키워드 필터
Active teams (priority order): ['search']
Step step_0 (search) -> in_progress
Step step_0 (search) -> completed
```

---

## 🔟 체크리스트

- [ ] **수정 1**: execution_steps에 `"priority": step.priority` 추가
- [ ] **수정 2**: active_teams 생성 시 priority 순 정렬 + 중복 제거
- [ ] **수정 3**: LEGAL_CONSULT 키워드 필터 추가
- [ ] **테스트**: 단순 법률 질문 → search만 실행 확인
- [ ] **테스트**: 복합 질문 → 올바른 순서 확인

---

**작성 완료**: 2025-10-21
**다음 단계**: 사용자 확인 후 3가지 수정 적용
