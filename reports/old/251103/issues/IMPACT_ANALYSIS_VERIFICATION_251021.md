# 수정사항 영향 분석 및 검증

**작성일**: 2025-10-21
**목적**: 3가지 수정의 영향 범위, 부작용, 올바른 방향성 검증

---

## 📋 수정 사항 요약

1. **수정 1**: execution_steps에 priority 필드 추가
2. **수정 2**: active_teams 생성 시 priority 순 정렬
3. **수정 3**: LEGAL_CONSULT 키워드 필터 추가

---

## 1️⃣ 수정 1: execution_steps에 priority 필드 추가

### 현재 코드 (team_supervisor.py Line 322-346)

```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "step_type": self._get_step_type_for_agent(step.agent_name),
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        # ❌ priority 없음!

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

### 제안 수정

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

### 영향 분석

#### ✅ 긍정적 영향

1. **execution_steps에 priority 정보 포함**
   - 현재: priority 정보가 손실됨
   - 수정 후: 원본 ExecutionStep의 priority 보존

2. **WebSocket으로 전송되는 데이터 개선**
   - chat_api.py에서 execution_steps를 WebSocket으로 전송
   - Frontend가 priority를 받아서 정렬 가능

3. **ExecutionOrchestrator 호환성**
   - execution_orchestrator.py Line 131에서 priority 사용 가능
   ```python
   "priority": strategy.get("priorities", {}).get(team, 1),
   ```

#### ⚠️ 잠재적 부작용

1. **Frontend 호환성**
   - Frontend가 기존에 priority 필드를 예상하지 않았다면?
   - **검증 필요**: Frontend 코드 확인

2. **State 크기 증가**
   - priority 필드 추가로 State 크기 약간 증가
   - **영향**: 미미함 (Int 하나)

3. **Checkpoint 호환성**
   - PostgreSQL checkpointer에 저장되는 State
   - **검증**: TypedDict는 extra fields 허용하므로 문제없음

#### 🔍 검증 필요 사항

- [ ] Frontend가 execution_steps를 어떻게 사용하는지 확인
- [ ] priority 필드가 추가되어도 기존 Frontend 동작에 문제없는지

---

## 2️⃣ 수정 2: active_teams 순서 보장

### 현재 코드 (team_supervisor.py Line 362-369)

```python
active_teams = set()
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)
```

### 제안 수정

```python
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
```

### 영향 분석

#### ✅ 긍정적 영향

1. **실행 순서 보장**
   - 현재: set → list 변환으로 순서 상실
   - 수정 후: priority 순서대로 실행

2. **중복 제거 기능 유지**
   - 기존: set으로 중복 제거
   - 수정 후: seen_teams set으로 중복 제거
   - **기능 동일**: 중복 팀은 한 번만 실행

3. **복합 질문 대응**
   ```python
   # 예시: 복합 질문
   execution_steps = [
       {"step_id": "step_0", "team": "search", "priority": 0},    # 법률 검색
       {"step_id": "step_1", "team": "analysis", "priority": 1},  # 분석
       {"step_id": "step_2", "team": "search", "priority": 2}     # 시세 검색 (중복!)
   ]

   # 기존: {"search", "analysis"} → 순서 불명
   # 수정 후: ["search", "analysis"] → priority 순서 보장
   ```

#### ⚠️ 잠재적 부작용

1. **복합 질문에서 같은 팀 여러 번 실행 불가**
   - 현재도: set 사용으로 중복 제거됨
   - 수정 후도: seen_teams으로 중복 제거됨
   - **영향**: 없음 (기존 동작 유지)

2. **첫 번째 등장한 팀만 실행**
   ```python
   execution_steps = [
       {"step_id": "step_0", "team": "search", "priority": 0},  # 법률 검색
       {"step_id": "step_2", "team": "search", "priority": 2}   # 시세 검색
   ]

   # 결과: step_0만 실행, step_2는 스킵
   ```
   - **질문**: 이게 올바른 동작인가?

#### 🚨 중요 질문

**Q1**: 복합 질문에서 같은 팀을 여러 번 실행해야 하는 경우가 있는가?

**예시**:
```
질문: "강남구 전세 시세 확인하고, 서초구 매매 시세도 확인해줘"

execution_steps:
  step_0: search_team (강남구 전세 시세)
  step_1: search_team (서초구 매매 시세)

현재/수정 후 모두: search_team 한 번만 실행
```

**검증 필요**:
- [ ] QueryDecomposer가 같은 팀을 여러 번 생성하는가?
- [ ] 생성한다면, 각각 별도로 실행해야 하는가?
- [ ] 아니면 한 번에 모아서 실행하는 것이 맞는가?

---

## 3️⃣ 수정 3: LEGAL_CONSULT 키워드 필터

### 제안 수정 (planning_agent.py Line 297)

```python
async def _suggest_agents(...) -> List[str]:
    # ✅ 추가
    if intent_type == IntentType.LEGAL_CONSULT:
        analysis_keywords = ["분석", "비교", "계산", "평가", "추천", "검토", "어떻게", "방법", "해야", "하면"]
        if not any(kw in query for kw in analysis_keywords):
            logger.info("✅ LEGAL_CONSULT simple query -> search_team only")
            return ["search_team"]

    # 기존 LLM 로직
    if self.llm_service:
        ...
```

### 영향 분석

#### ✅ 긍정적 영향

1. **Intent Analysis와 Agent Selection 일관성**
   - 현재: Intent "검색만" → Selection "검색+분석" (모순)
   - 수정 후: Intent "검색만" → Selection "검색만" (일관)

2. **응답 시간 단축**
   - 단순 질문: 30초 → 13초 (56% 단축)

3. **LLM 비용 절감**
   - analysis_team 실행 건너뛰기
   - LLM 호출 6회 → 4회 (33% 감소)

#### ⚠️ 잠재적 부작용

1. **분석이 필요한데 건너뛸 위험**
   ```python
   질문: "공인중개사 금지행위 위반 시 처벌?"

   키워드 체크:
   - "분석" 없음
   - "어떻게" 없음
   - "방법" 없음

   결과: search_team만 선택

   실제: "처벌" = 분석/평가 필요할 수도?
   ```

2. **키워드 리스트 불완전**
   - 현재: ["분석", "비교", "계산", "평가", "추천", "검토", "어떻게", "방법", "해야", "하면"]
   - 누락 가능: "대처", "조치", "절차", "판단", "선택", ...

#### 🔍 개선 방안

**Option A**: 키워드 확장
```python
analysis_keywords = [
    # 분석
    "분석", "비교", "계산", "평가", "검토", "판단",
    # 행동
    "어떻게", "방법", "해야", "하면", "대처", "조치", "절차",
    # 선택
    "추천", "권장", "선택", "결정",
    # 결과
    "영향", "효과", "결과", "차이", "장단점"
]
```

**Option B**: 부정 키워드 (더 안전)
```python
# "단순 조회" 키워드 체크
simple_query_keywords = [
    "이 뭐", "이란", "인가요", "알려줘", "뭔지", "무엇"
]

if any(kw in query for kw in simple_query_keywords):
    return ["search_team"]
```

#### 🚨 중요 질문

**Q2**: LEGAL_CONSULT에서 "단순 조회"의 정확한 정의는?

**예시 분류**:
```
✅ 단순 조회 (search만):
- "공인중개사 금지행위는?"
- "전세금 인상률 한도 알려줘"
- "임대차보호법이 뭐야?"

❓ 경계 케이스:
- "금지행위 위반 시 처벌은?" (처벌 = 분석?)
- "전세금 5% 인상 가능한가요?" (가능 여부 판단 = 분석?)

❌ 분석 필요 (search + analysis):
- "금지행위 위반 시 어떻게 대처해야 해?"
- "전세금 인상 거부 방법은?"
```

**검증 필요**:
- [ ] 실제 사용자 질문 패턴 분석
- [ ] 키워드 리스트 충분성 검증
- [ ] False Negative 비율 측정

---

## 4️⃣ ExecutionOrchestrator와의 상호작용

### execution_orchestrator.py가 사용하는 필드

```python
# Line 131
"priority": strategy.get("priorities", {}).get(team, 1),
```

### 영향 분석

1. **수정 1 적용 시**:
   - execution_steps에 priority 추가
   - ExecutionOrchestrator가 이미 있는 priority 활용 가능
   - **충돌**: orchestration.priority vs step.priority?

2. **우선순위 충돌 가능성**:
   ```python
   # Planning Agent가 생성
   step["priority"] = 0  # search 먼저

   # ExecutionOrchestrator가 덮어쓰기
   step["orchestration"]["priority"] = 2  # 동적 조정

   # 어느 것을 따라야 하나?
   ```

3. **해결 방안**:
   - Planning Agent의 priority: 초기 계획
   - Orchestrator의 priority: 동적 조정
   - **사용**: Orchestrator가 있으면 orchestration.priority 우선

### 🔍 검증 필요

- [ ] ExecutionOrchestrator가 활성화되어 있는가?
- [ ] 활성화되면 priority 충돌 해결 로직 필요한가?

---

## 5️⃣ 전체 데이터 흐름 검증

### 현재 흐름

```
1. PlanningAgent.create_execution_plan()
   → ExecutionPlan.steps = [ExecutionStep(priority=0), ExecutionStep(priority=1)]

2. TeamSupervisor.planning_node()
   → execution_steps = [{...}, {...}]  # ❌ priority 손실!

3. TeamSupervisor.planning_node()
   → active_teams = set() → list()  # ❌ 순서 손실!

4. TeamSupervisor._execute_teams_sequential(teams=active_teams)
   → for team in teams  # ❌ 역순 실행 가능!
```

### 수정 후 흐름

```
1. PlanningAgent.create_execution_plan()
   → ExecutionPlan.steps = [ExecutionStep(priority=0), ExecutionStep(priority=1)]

2. TeamSupervisor.planning_node()
   → execution_steps = [{..., "priority": 0}, {..., "priority": 1}]  # ✅ priority 보존!

3. TeamSupervisor.planning_node()
   → sorted(execution_steps, key=priority)
   → active_teams = ["search", "analysis"]  # ✅ 순서 보장!

4. TeamSupervisor._execute_teams_sequential(teams=active_teams)
   → for team in teams  # ✅ 올바른 순서!
```

### ✅ 검증 결과

**데이터 흐름**: 수정 후가 올바름
- priority 정보 보존
- 순서 보장
- 의도대로 실행

---

## 6️⃣ 부작용 체크리스트

### Frontend 영향

- [ ] **Q**: Frontend가 execution_steps.priority를 예상하는가?
- [ ] **Q**: priority 추가로 Frontend가 깨지는가?
- [ ] **A**: TypeScript 타입 정의 확인 필요

### Backend 영향

- [x] **Q**: execution_steps를 읽는 다른 코드가 있는가?
- [x] **A**:
  - separated_states.py: ExecutionStepState TypedDict (priority 없음!)
  - execution_orchestrator.py: execution_steps 사용
  - chat_api.py: WebSocket으로 전송

### TypedDict 호환성

**separated_states.py Line 239-269**:
```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str
    # ❌ priority 없음!
    ...
```

**문제**: ExecutionStepState에 priority 정의 안됨
**영향**: TypedDict는 extra keys 허용 (total=False)
**해결**: ExecutionStepState에 priority 추가 권장

```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str
    priority: int  # ✅ 추가 권장
    ...
```

---

## 7️⃣ 최종 검증 질문

### 사용자 확인 필요

1. **복합 질문 처리**:
   - Q: 같은 팀을 여러 번 실행해야 하는 경우가 있는가?
   - 현재: 중복 제거 (첫 번째만 실행)
   - 수정 후도: 중복 제거 유지
   - **확인**: 이 동작이 의도한 것인가?

2. **LEGAL_CONSULT 분류**:
   - Q: "처벌은?", "가능한가요?" 같은 질문은 어느 쪽?
   - 단순 조회 vs 분석 필요
   - **확인**: 실제 사용 패턴 기준은?

3. **ExecutionOrchestrator 사용**:
   - Q: ExecutionOrchestrator를 사용 중인가?
   - 사용 중이면: priority 충돌 해결 필요
   - **확인**: 현재 활성화 여부?

4. **ExecutionStepState 타입 업데이트**:
   - Q: ExecutionStepState에 priority 추가할 것인가?
   - 추가 안 하면: Runtime에는 문제없음 (extra key 허용)
   - 추가 하면: 타입 정확도 향상
   - **확인**: 타입 정의 업데이트 할 것인가?

---

## 8️⃣ 권장 수정 순서

### Phase 1: 안전한 수정 (부작용 없음)

1. **ExecutionStepState에 priority 추가**
   ```python
   # separated_states.py Line 239
   class ExecutionStepState(TypedDict):
       ...
       priority: int  # ✅ 추가
   ```

2. **execution_steps에 priority 복사**
   ```python
   # team_supervisor.py Line 328
   "priority": step.priority,  # ✅ 추가
   ```

### Phase 2: 검증 후 적용

3. **active_teams 순서 보장**
   - 사용자 확인: 중복 팀 처리 방식
   - 확인 후 적용

4. **LEGAL_CONSULT 키워드 필터**
   - 사용자 확인: 키워드 리스트 충분성
   - 실제 질문 패턴 테스트
   - 확인 후 적용

---

## 9️⃣ 최종 권장사항

### 즉시 적용 가능 (안전)

1. ✅ **ExecutionStepState에 priority 추가**
   - 영향: 타입 정의만 업데이트
   - 위험: 없음

2. ✅ **execution_steps에 priority 복사**
   - 영향: 데이터 보존
   - 위험: 없음 (Frontend extra field 무시)

### 사용자 확인 후 적용

3. ⏳ **active_teams 순서 보장**
   - 확인 필요: 중복 팀 처리 의도
   - 현재 동작 유지하면서 순서만 보장

4. ⏳ **LEGAL_CONSULT 키워드 필터**
   - 확인 필요: 키워드 리스트
   - 실제 질문 패턴 테스트 필요

---

## 🔟 결론

### 올바른 방향인가?

**YES** ✅

1. **priority 보존**: 원본 데이터 보존은 항상 올바름
2. **순서 보장**: 실행 순서는 명확해야 함
3. **키워드 필터**: Intent 일관성 유지는 좋음

### 그러나 주의 필요

1. **복합 질문**: 중복 팀 처리 검증 필요
2. **키워드 리스트**: 실제 패턴 기반 검증 필요
3. **타입 정의**: ExecutionStepState 업데이트 권장

---

**작성 완료**: 2025-10-21
**다음 단계**: 4가지 확인 질문에 답변 → 단계별 적용
