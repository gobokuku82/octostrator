# Agent 실행 흐름 상세 설명

작성일: 2025-11-04

---

## 질문에 대한 답변

### Q1. 에이전트 실행 순서는 어떻게 정해지나요?

**답변: Planning Node에서 LLM이 결정합니다.**

#### 상세 메커니즘

1. **Intent Understanding Node**
   - 사용자 질문을 7가지 카테고리로 분류
   - Complexity를 simple/medium/complex로 판단

2. **Planning Node**
   - **LLM이 PLANNING_SYSTEM_PROMPT를 기반으로 작업 계획 생성**
   - Structured Output을 사용하여 정확한 형식 강제

**Planning Prompt 핵심**:
```
Available agents:
- diet: 식단 기록/분석
- workout: 운동 루틴 추천
- schedule: 수업 예약/변경
- member_care: 회원 리포팅/알림
- coaching: 전문 자료 검색
- hitl: 사용자 승인 필요

Rules:
1. 같은 Agent를 여러 번 사용 가능
2. HITL은 중요한 결정 전에 배치
3. 각 Task는 명확한 description 필요
4. step_id는 1부터 시작

Complexity Guidelines:
- Simple (1-2 steps): 단순 조회/검색
- Medium (2-3 steps): 추천/분석
- Complex (4+ steps): 복합 작업 + HITL
```

#### 예시

**사용자 질문**: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘"

**LLM의 Planning 결과**:
```json
{
  "steps": [
    {
      "step_id": 1,
      "agent": "member_care",
      "description": "김철수 회원 정보 및 진행률 조회",
      "status": "pending"
    },
    {
      "step_id": 2,
      "agent": "workout",
      "description": "김철수 운동 기록 조회",
      "status": "pending"
    },
    {
      "step_id": 3,
      "agent": "diet",
      "description": "김철수 식단 기록 조회",
      "status": "pending"
    },
    {
      "step_id": 4,
      "agent": "schedule",
      "description": "PT 스케줄 확인 및 생성",
      "status": "pending"
    }
  ],
  "reasoning": "회원 정보를 먼저 조회하여 상태를 파악한 후, 운동과 식단을 확인합니다. 마지막으로 스케줄을 생성합니다."
}
```

**핵심**:
- **LLM이 자동으로 순서 결정**
- 논리적 흐름: 회원 정보 → 운동 → 식단 → 스케줄
- LLM의 추론(reasoning)도 함께 제공

#### LLM이 순서를 정하는 이유

1. **문맥 이해**: 자연어로 된 요청을 의미론적으로 분석
2. **도메인 지식**: Prompt에 각 Agent의 역할과 Guidelines 명시
3. **유연성**: 사용자 요청에 따라 다양한 조합 가능
4. **자동화**: 하드코딩 없이 동적으로 계획 생성

---

### Q2. 각 에이전트가 만든 정보를 다음 에이전트가 상속받나요?

**답변: 현재는 간접 공유, Phase 2에서 직접 참조 가능**

#### 현재 구조 (Phase 1)

**State 기반 간접 공유**:

```
State (모든 노드가 공유)
├── messages: [대화 히스토리]
├── plan: [
│     {"step_id": 1, "agent": "member_care", "result": "[MemberCare] 김철수..."},
│     {"step_id": 2, "agent": "workout", "result": "[Workout] ..."},
│     ...
│   ]
├── current_step: 2
└── ...
```

**각 Agent의 동작**:
```python
async def workout_agent_node(state: SupervisorState) -> Dict:
    plan = state["plan"]
    current_step = state["current_step"]

    # 이론적으로 이전 Agent 결과 참조 가능
    # previous_result = plan[current_step - 1]["result"]  # 가능하지만 현재 미사용

    # 현재는 독립적으로 Tool 호출
    user_id = state.get("user_id", 1)
    data = get_workout_history(user_id=user_id)

    # 결과 저장
    plan[current_step]["result"] = format_result(data)

    return {
        "plan": plan,
        "current_step": current_step + 1
    }
```

**현재 Phase 1의 특징**:
- ✅ 각 Agent는 State를 통해 이전 결과에 접근 **가능**
- ❌ 하지만 현재는 각 Agent가 독립적으로 Tool만 호출
- ❌ 이전 Agent 결과를 직접 파싱하지 않음
- ✅ **Aggregator에서 모든 결과를 종합**

#### Aggregator가 모든 결과 종합

```python
async def aggregator_node(state: SupervisorState, llm: ChatOpenAI) -> Dict:
    plan = state["plan"]

    # 모든 Agent 결과 수집
    all_results = ""
    for step in plan:
        all_results += f"[{step['agent']}] {step['result']}\n\n"

    # LLM으로 인사이트 생성
    insights = await llm.ainvoke([
        SystemMessage(content=AGGREGATOR_INSIGHT_PROMPT.format(
            user_intent=state["user_intent"],
            steps=all_results
        ))
    ])

    return {
        "aggregated_data": {
            "summary": "...",
            "sections": {
                "member_info": plan[0]["result"],
                "workout": plan[1]["result"],
                "diet": plan[2]["result"],
                "schedule": plan[3]["result"]
            },
            "insights": insights
        }
    }
```

**Aggregator의 역할**:
1. 모든 Agent 결과를 수집
2. 섹션별로 구조화
3. LLM으로 종합 분석 및 인사이트 생성
4. 최종 사용자 답변 생성

#### 향후 계획 (Phase 2: LLM Tool Calling)

**Phase 2에서는 Agent가 이전 결과를 직접 활용**:

```python
async def workout_agent_node(state: SupervisorState, llm: ChatOpenAI) -> Dict:
    plan = state["plan"]
    current_step = state["current_step"]

    # Phase 2: 이전 Agent 결과를 LLM에게 전달
    previous_results = "\n".join([
        step["result"] for step in plan[:current_step]
    ])

    # LLM이 Tool을 선택하고, 이전 결과를 고려하여 실행
    result = await llm_with_tools.ainvoke([
        SystemMessage(content=f"Previous results:\n{previous_results}"),
        HumanMessage(content=f"Task: {plan[current_step]['description']}")
    ])

    # LLM이 선택한 Tool 실행 및 결과 반환
    return {"plan": ..., "current_step": ...}
```

**Phase 2의 장점**:
- Agent가 이전 결과를 고려하여 더 정확한 Tool 선택
- 예: MemberCareAgent가 "김철수 회원은 근육 증가 목표"라고 했다면, WorkoutAgent가 근육 증가에 맞는 운동 추천

#### 요약

| 항목 | Phase 1 (현재) | Phase 2 (계획) |
|------|---------------|--------------|
| 결과 저장 | State.plan[step]["result"] | 동일 |
| Agent 간 공유 | State 통해 간접 공유 | LLM이 이전 결과 직접 참조 |
| Tool 선택 | Agent가 하드코딩 | LLM이 동적 선택 |
| 정보 활용 | Aggregator에서 종합 | Agent도 이전 결과 활용 |

**결론**:
- 현재는 "간접 공유" (State 통해 접근 가능하지만 미활용)
- Aggregator가 모든 결과를 종합하여 최종 인사이트 생성
- Phase 2에서 Agent가 이전 결과를 직접 활용 예정

---

### Q3. 에이전트가 병렬로 실행되나요?

**답변: 현재는 순차 실행만 지원, Phase 5에서 병렬 실행 계획**

#### 현재 구조 (순차 실행)

**Executor의 동작 방식**:

```python
async def executor_node(state: SupervisorState) -> Command:
    plan = state["plan"]
    current_step = state["current_step"]

    # 모든 단계 완료?
    if current_step >= len(plan):
        return Command(goto="aggregator")

    # 현재 단계 가져오기
    step = plan[current_step]
    agent_name = step["agent"]

    # Command로 다음 Agent 지정 (한 번에 하나만)
    return Command(goto=agent_name)
```

**Graph 구조 (main_graph.py)**:

```python
# 모든 Agent → executor로 복귀
workflow.add_edge("diet", "executor")
workflow.add_edge("workout", "executor")
workflow.add_edge("schedule", "executor")
workflow.add_edge("member_care", "executor")
workflow.add_edge("coaching", "executor")
```

**실행 흐름**:

```
Executor (Step 0)
  │
  ├─ Command(goto="member_care")
  │
  ▼
MemberCareAgent (실행)
  │
  ├─ return {"current_step": 1, ...}
  │
  ▼
Executor (Step 1)  ◀─── 복귀
  │
  ├─ Command(goto="workout")
  │
  ▼
WorkoutAgent (실행)
  │
  ├─ return {"current_step": 2, ...}
  │
  ▼
Executor (Step 2)  ◀─── 복귀
  │
  ├─ Command(goto="diet")
  │
  ▼
DietAgent (실행)
  │
  ...
```

**핵심**:
- **한 번에 하나의 Agent만 실행**
- 각 Agent가 완료되면 Executor로 복귀
- Executor가 다음 Agent를 결정하여 실행
- **순환 구조** (Executor ↔ Agent)

#### 왜 현재는 순차 실행인가?

1. **의존성 관리 용이**:
   - 일부 Agent는 이전 Agent 결과에 의존할 수 있음
   - 순차 실행으로 순서 보장

2. **State 안정성**:
   - 병렬 실행 시 State 충돌 가능성
   - 순차 실행으로 State 업데이트 안전성 보장

3. **디버깅 용이**:
   - 실행 순서가 명확하여 문제 추적 쉬움

4. **Phase 1의 목표**:
   - Tool 분리 및 기본 구조 완성
   - 병렬 실행은 최적화 단계 (Phase 5)

#### Phase 5: 병렬 실행 계획

**병렬 실행 가능한 경우**:

```
User: "김철수, 이영희, 박민수 회원의 진행률을 각각 조회해줘"

Planning 결과:
[
  {"step_id": 1, "agent": "member_care", "description": "김철수 진행률 조회", "parallel_group": 1},
  {"step_id": 2, "agent": "member_care", "description": "이영희 진행률 조회", "parallel_group": 1},
  {"step_id": 3, "agent": "member_care", "description": "박민수 진행률 조회", "parallel_group": 1}
]
```

**병렬 실행 흐름 (Phase 5)**:

```
Executor
  │
  ├─ 동일한 parallel_group 감지
  │
  ├─ 동시에 3개 Agent 실행
  │
  ├──┬──┬──┐
  │  │  │  │
  ▼  ▼  ▼  ▼
MemberCare (김철수)
MemberCare (이영희)
MemberCare (박민수)
  │  │  │  │
  └──┴──┴──┘
  │
  ▼
Executor (모든 결과 수집)
  │
  ▼
Aggregator
```

**병렬 실행의 장점**:
- **성능 향상**: 독립적인 작업을 동시 실행
- **응답 시간 단축**: 대량 조회 시 효과적
- **리소스 활용**: 비동기 I/O 최대 활용

**Phase 5 구현 예정 기능**:
1. `parallel_group` 필드 추가
2. Executor가 동일 group의 Agent를 동시 실행
3. 모든 Agent 완료 후 다음 단계 진행
4. State 동시성 제어 (Lock 또는 AsyncPostgresSaver 활용)

#### 요약

| 항목 | Phase 1-4 (현재) | Phase 5 (계획) |
|------|-----------------|---------------|
| 실행 방식 | 순차 실행 | 순차 + 병렬 |
| Agent 호출 | 한 번에 1개 | parallel_group별로 여러 개 |
| 의존성 관리 | 자동 보장 | Planning에서 명시 |
| 성능 | 일반적 | 독립 작업 시 향상 |
| 구현 복잡도 | 낮음 | 높음 (동시성 제어) |

**결론**:
- **현재는 순차 실행만 지원**
- Executor가 한 번에 하나의 Agent만 Command로 지정
- 각 Agent는 Executor로 복귀하여 다음 Agent 실행
- **Phase 5에서 병렬 실행 구현 예정** (독립 작업 동시 실행)

---

## 실행 흐름 전체 정리

### 단순 질문 (1개 Agent)

```
User: "오늘 식단 보여줘"

Intent Understanding
  ↓
  Category: diet_query
  Complexity: simple
  ↓
Planning
  ↓
  LLM이 계획 생성:
  [{"step_id": 1, "agent": "diet", "description": "최근 식단 기록 조회"}]
  ↓
Executor (Step 0)
  ↓
  Command(goto="diet")
  ↓
DietAgent
  ↓
  get_meal_logs(user_id=1)
  get_daily_nutrition_summary(user_id=1)
  result = "[DietAgent] 최근 식단 기록:\n..."
  ↓
  return {"current_step": 1, "plan": [...]}
  ↓
Executor (Step 1)
  ↓
  current_step >= len(plan) → 완료
  Command(goto="aggregator")
  ↓
Aggregator
  ↓
  모든 결과 종합
  LLM으로 인사이트 생성
  ↓
Output Router → Chat Generator
  ↓
final_result: "오늘의 식단은..."
```

### 복합 질문 (4개 Agent, 순차 실행)

```
User: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘"

Intent Understanding
  ↓
  Category: multi_step_task
  Complexity: complex
  ↓
Planning
  ↓
  LLM이 계획 생성:
  [
    {"step_id": 1, "agent": "member_care", "description": "회원 정보 조회"},
    {"step_id": 2, "agent": "workout", "description": "운동 기록 조회"},
    {"step_id": 3, "agent": "diet", "description": "식단 기록 조회"},
    {"step_id": 4, "agent": "schedule", "description": "PT 스케줄 확인"}
  ]
  ↓
Executor (Step 0) → Command(goto="member_care")
  ↓
MemberCareAgent (실행) → return {"current_step": 1, ...}
  ↓
Executor (Step 1) → Command(goto="workout")
  ↓
WorkoutAgent (실행) → return {"current_step": 2, ...}
  ↓
Executor (Step 2) → Command(goto="diet")
  ↓
DietAgent (실행) → return {"current_step": 3, ...}
  ↓
Executor (Step 3) → Command(goto="schedule")
  ↓
ScheduleAgent (실행) → return {"current_step": 4, ...}
  ↓
Executor (Step 4) → 모든 단계 완료 → Command(goto="aggregator")
  ↓
Aggregator
  ↓
  모든 Agent 결과 종합:
  - member_care 결과
  - workout 결과
  - diet 결과
  - schedule 결과
  ↓
  LLM으로 인사이트 생성:
  - "김철수 회원은 체지방 감소 중"
  - "운동 강도를 늘려야 함"
  - "다음 PT는 내일 오후 3시"
  ↓
Output Router → Chat Generator
  ↓
final_result: "김철수 회원의 종합 분석 결과..."
```

---

## 핵심 요약

### Q1. 에이전트 순서는 어떻게 정하나요?
✅ **Planning Node에서 LLM이 자동으로 결정**
- PLANNING_SYSTEM_PROMPT 기반
- 사용자 요청을 분석하여 논리적 순서 생성
- 유연하고 동적인 계획 수립

### Q2. 정보 상속은 되나요?
✅ **현재는 간접 공유, Aggregator가 종합**
- State를 통해 모든 Agent 결과 공유
- 현재 Phase 1: 각 Agent가 독립적으로 실행
- Aggregator에서 모든 결과를 종합하여 인사이트 생성
- Phase 2: Agent가 이전 결과를 직접 활용 예정

### Q3. 병렬 실행이 되나요?
❌ **현재는 순차 실행만 지원**
- Executor가 한 번에 하나의 Agent만 실행
- 각 Agent → Executor → 다음 Agent (순환)
- Phase 5에서 병렬 실행 구현 예정

---

**작성일**: 2025-11-04
**문서 위치**: `C:\kdy\Projects\AI_PTmanager\beta_v001\manual\agent_execution_flow.md`
