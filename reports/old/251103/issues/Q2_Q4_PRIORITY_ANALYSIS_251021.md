# Q2 & Q4 답변: LEGAL_CONSULT 분류 및 Priority 필드 분석

**작성일**: 2025-10-21
**목적**: Q2 (LEGAL_CONSULT 경계 케이스 분류 아이디어)와 Q4 (priority 필드 목적) 답변

---

## Q4: Priority 필드의 목적

### 질문
> "priority 필드를 execution_steps에 추가하면 어떤점이 좋은가? 순서를 만드는건가? 우선순위를 만드는건가?"

### 답변

#### 현재 코드 분석

**planning_agent.py Line 654-663**:
```python
for i, agent_name in enumerate(selected_agents):
    step = ExecutionStep(
        agent_name=agent_name,
        priority=i,  # ← 0, 1, 2, ...
        dependencies=dependencies,
        ...
    )
```

**의미**:
- `priority = 0`: search_team (첫 번째)
- `priority = 1`: analysis_team (두 번째)
- `priority = 2`: document_team (세 번째)

#### Priority는 "순서"인가 "우선순위"인가?

**→ 둘 다!**

##### 1. 순서 (Order)

**목적**: 실행 순서 결정

```python
# sorted by priority (ascending)
sorted_steps = sorted(steps, key=lambda x: x.get("priority", 999))

for step in sorted_steps:
    execute(step)
```

**효과**:
- `priority=0` → 먼저 실행
- `priority=1` → 나중 실행

**이것이 바로 현재 문제 해결책!**
- 현재: `set()`으로 순서 손실
- 해결: `sorted(steps, key=priority)` 사용

##### 2. 우선순위 (Priority)

**목적**: 병렬 실행 시 중요도 결정

```python
# 병렬 실행 시
async def execute_parallel(steps):
    # priority 낮은 것(중요한 것) 먼저 시작
    sorted_steps = sorted(steps, key=lambda x: x["priority"])

    tasks = []
    for step in sorted_steps:
        task = asyncio.create_task(execute(step))
        tasks.append(task)

    # priority 0인 작업이 먼저 시작됨 (조금이라도 빨리)
    await asyncio.gather(*tasks)
```

**효과**:
- 중요한 작업(priority=0)이 먼저 스케줄링됨
- CPU/메모리 자원 경쟁 시 우선권

#### 현재 시스템에서 Priority의 역할

**1. PlanningAgent (생성)**:
```python
# Line 654
for i, agent_name in enumerate(selected_agents):
    step = ExecutionStep(
        agent_name=agent_name,
        priority=i,  # 순서 부여
        ...
    )
```

**2. ExecutionStepState (저장 안 됨!) ❌**:
```python
# separated_states.py
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str
    # priority: int  # ← 정의 안 됨!
```

**3. team_supervisor.py (사용 안 됨!) ❌**:
```python
# Line 362-369
active_teams = set()  # priority 무시
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)  # 순서 손실!
```

#### Priority를 추가하면 좋은 점

##### ✅ 1. 실행 순서 보장

**현재 문제**:
```
PlanningAgent: [search_team, analysis_team] → priority=[0, 1]
   ↓ (ExecutionStepState에 priority 없음)
team_supervisor: set() 사용 → 순서 손실
   ↓
실행 순서: [analysis_team, search_team] ← 역순!
```

**해결 후**:
```
PlanningAgent: [search_team, analysis_team] → priority=[0, 1]
   ↓ (execution_steps에 priority 추가)
team_supervisor: sorted(steps, key=priority)
   ↓
실행 순서: [search_team, analysis_team] ← 정상!
```

##### ✅ 2. 중복 팀 처리 가능

**Q1 요구사항**: "같은팀을 여러번 실행하거나 한번만 실행하거나"

**Priority 활용**:
```python
# search → analysis → search 계획
steps = [
    {"step_id": "step_0", "team": "search", "priority": 0, "task": "법률 검색"},
    {"step_id": "step_1", "team": "analysis", "priority": 1, "task": "분석"},
    {"step_id": "step_2", "team": "search", "priority": 2, "task": "추가 검색"}
]

# sorted by priority
for step in sorted(steps, key=lambda x: x["priority"]):
    execute(step)

# 결과: search → analysis → search (정확한 순서!)
```

**현재 문제**:
```python
# set()으로 중복 제거
active_teams = set(["search", "analysis", "search"])
# → ["search", "analysis"]  ← 마지막 search 사라짐!
```

##### ✅ 3. 병렬 실행 최적화

**병렬 실행 가능한 경우**:
```python
steps = [
    {"team": "search", "priority": 0, "dependencies": []},
    {"team": "analysis", "priority": 1, "dependencies": []}  # search 의존 없음
]

# priority로 중요도 판단
async def execute_parallel(steps):
    # priority 낮은 것부터 먼저 시작 (더 중요)
    sorted_steps = sorted(steps, key=lambda x: x["priority"])

    tasks = [execute(step) for step in sorted_steps]
    await asyncio.gather(*tasks)
```

##### ✅ 4. 동적 재정렬

**ExecutionOrchestrator 사용 시**:
```python
# 초기 계획
steps = [
    {"team": "search", "priority": 0},
    {"team": "analysis", "priority": 1}
]

# Orchestrator가 전략 변경
if orchestrator.strategy == "analysis_first":
    # priority 재할당
    steps[0]["priority"] = 1  # search 나중에
    steps[1]["priority"] = 0  # analysis 먼저
```

#### 추가하면 어떻게 되나?

**Before** (현재):
```python
# team_supervisor.py Line 322-346
execution_steps=[
    {
        "step_id": f"step_{i}",
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        # priority 없음!
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**After** (추가):
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        "priority": step.priority,  # ✅ 추가
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**사용**:
```python
# team_supervisor.py Line 639 (_execute_teams_sequential)
async def _execute_teams_sequential(...):
    # ✅ priority 순으로 정렬
    sorted_steps = sorted(
        planning_state["execution_steps"],
        key=lambda x: x.get("priority", 999)
    )

    for step in sorted_steps:
        team_name = step["team"]
        logger.info(f"Executing {team_name} (priority: {step['priority']})")
        await self._execute_team(team_name, ...)
```

---

## Q2: LEGAL_CONSULT 경계 케이스 분류 아이디어

### 질문
> "Q2는 경계케이스 분류에 대한 아이디어를 말해줘"

### 문제 상황

**Intent Analysis**:
```json
{
  "intent_type": "LEGAL_CONSULT",
  "reasoning": "법률 정보만 검색하면 충분"
}
```

**Agent Selection** (4초 후):
```json
{
  "selected_agents": ["search_team", "analysis_team"],
  "reasoning": "검색만으로 충분하지 않으며, 분석이 필요함"
}
```

**모순**: 같은 LLM이 4초 만에 정반대 판단!

### 경계 케이스 정의

**경계 케이스 = Intent는 단순하지만 실제로는 복잡한 질문**

#### 예시 1: "공인중개사 금지행위?"

**표면**: 법률 조항 확인 → LEGAL_CONSULT → search_team만
**실제**: 사용자는 구체적 상황에 적용 원함 → 분석 필요

#### 예시 2: "전세금 5% 인상 가능한가요?"

**표면**: 법률 한도 확인 → search_team만
**실제**: 현재 계약서와 비교 필요 → 분석 필요

#### 예시 3: "강남구 아파트 시세"

**표면**: 시세 조회 → search_team만
**실제**: 여러 매물 비교 → 분석 필요할 수도

### 분류 아이디어

---

## 아이디어 1: Intent 세분화 ⭐⭐⭐

**현재 문제**: LEGAL_CONSULT가 너무 포괄적

**개선**:
```python
class IntentType(str, Enum):
    # 현재
    LEGAL_CONSULT = "법률 상담"

    # 세분화
    LEGAL_FACT_CHECK = "법률 사실 확인"      # "전세금 한도가 얼마야?"
    LEGAL_APPLICATION = "법률 적용 상담"    # "우리 계약서는 괜찮아?"
    LEGAL_COMPREHENSIVE = "법률 종합 상담"  # "법적으로 어떻게 해야 해?"
```

**Agent 매핑**:
```python
safe_defaults = {
    IntentType.LEGAL_FACT_CHECK: ["search_team"],  # 검색만
    IntentType.LEGAL_APPLICATION: ["search_team", "analysis_team"],  # 검색+분석
    IntentType.LEGAL_COMPREHENSIVE: ["search_team", "analysis_team"],  # 검색+분석

    IntentType.MARKET_FACT_CHECK: ["search_team"],  # 시세만
    IntentType.MARKET_COMPARISON: ["search_team", "analysis_team"],  # 시세+비교
}
```

**Intent Analysis 프롬프트 수정**:
```text
## 법률 관련 의도 세분화

1. **LEGAL_FACT_CHECK**: 단순 사실 확인
   - "~이 뭐야?", "~가 얼마야?", "~는 어떻게 돼?"
   - 예: "전세금 인상 한도가 얼마야?"

2. **LEGAL_APPLICATION**: 구체적 상황 적용
   - "우리 경우는~", "이 계약서는~", "이런 상황에서는~"
   - 예: "우리 계약서는 전세금 인상 조항이 문제없나요?"

3. **LEGAL_COMPREHENSIVE**: 종합 판단 및 해결책
   - "어떻게 해야 해?", "대응 방법은?", "법적으로 괜찮아?"
   - 예: "집주인이 10억 올려달래. 법적으로 어떻게 해야 해?"
```

**장점**:
- ✅ Intent 단계에서 복잡도 파악
- ✅ Agent Selection과 모순 감소
- ✅ 명확한 기준

**단점**:
- ❌ Intent 타입 증가 (관리 복잡)
- ❌ Intent Analysis 프롬프트 복잡해짐

---

## 아이디어 2: 키워드 기반 필터 ⭐⭐⭐⭐

**현재 제안** (AGENT_ROUTING_FIX_SOLUTION Line 129-140):

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
    # ✅ 추가: LEGAL_CONSULT는 기본적으로 검색만
    if intent_type == IntentType.LEGAL_CONSULT:
        # 복잡한 분석이 필요한 키워드 체크
        analysis_needed_keywords = [
            "분석", "비교", "계산", "평가", "추천", "검토",
            "어떻게", "방법", "차이", "장단점"
        ]

        needs_analysis = any(kw in query for kw in analysis_needed_keywords)

        if not needs_analysis:
            logger.info(f"✅ LEGAL_CONSULT without analysis keywords, using search_team only")
            return ["search_team"]

    # === 기존 LLM 기반 Agent 선택 로직 ===
    ...
```

**개선 버전**:

```python
# 키워드 분류 체계
KEYWORD_PATTERNS = {
    "fact_check": {
        "keywords": ["뭐야", "얼마야", "어떻게 돼", "알려줘", "확인", "조회"],
        "agents": ["search_team"]
    },
    "comparison": {
        "keywords": ["비교", "차이", "장단점", "어느게", "뭐가 좋아"],
        "agents": ["search_team", "analysis_team"]
    },
    "calculation": {
        "keywords": ["계산", "금액", "얼마나", "몇 %", "한도"],
        "agents": ["search_team", "analysis_team"]
    },
    "recommendation": {
        "keywords": ["추천", "제안", "방법", "어떻게 해야"],
        "agents": ["search_team", "analysis_team"]
    },
    "evaluation": {
        "keywords": ["평가", "검토", "분석", "판단", "괜찮아"],
        "agents": ["search_team", "analysis_team"]
    },
    "problem_solving": {
        "keywords": ["어떻게", "대응", "해결", "조치"],
        "agents": ["search_team", "analysis_team"]
    }
}

async def _suggest_agents(self, intent_type, query, keywords):
    # 1. 키워드 패턴 매칭
    matched_pattern = None
    for pattern_name, pattern_info in KEYWORD_PATTERNS.items():
        if any(kw in query for kw in pattern_info["keywords"]):
            matched_pattern = pattern_name
            break

    # 2. LEGAL_CONSULT + fact_check → search만
    if intent_type == IntentType.LEGAL_CONSULT:
        if matched_pattern == "fact_check":
            logger.info(f"✅ LEGAL_CONSULT + fact_check pattern → search_team only")
            return ["search_team"]
        elif matched_pattern in ["comparison", "calculation", "recommendation", "evaluation", "problem_solving"]:
            logger.info(f"✅ LEGAL_CONSULT + {matched_pattern} pattern → search + analysis")
            return ["search_team", "analysis_team"]

    # 3. MARKET_INQUIRY도 동일 로직
    if intent_type == IntentType.MARKET_INQUIRY:
        if matched_pattern == "fact_check":
            return ["search_team"]
        elif matched_pattern in ["comparison", "recommendation", "evaluation"]:
            return ["search_team", "analysis_team"]

    # 4. 패턴 매칭 실패 시 LLM 사용
    return await self._select_agents_with_llm(...)
```

**장점**:
- ✅ 빠름 (LLM 호출 안 함)
- ✅ 명확한 기준
- ✅ 쉽게 조정 가능

**단점**:
- ❌ 키워드 누락 시 오판
- ❌ 복잡한 질문 처리 어려움

---

## 아이디어 3: 2단계 분류 ⭐⭐⭐⭐⭐

**핵심 아이디어**: Intent Analysis와 Agent Selection을 **협업**시킴

### 현재 문제

```
Intent Analysis (독립)
  ↓
  LEGAL_CONSULT, "검색만 충분"
  ↓
Agent Selection (독립)
  ↓
  search + analysis, "분석 필요"  ← 모순!
```

### 해결 방법

```
Intent Analysis (1단계)
  ↓
  intent_type, intent_complexity (신규!)
  ↓
Agent Selection (2단계: Intent 결과 참고)
  ↓
  if intent_complexity == "simple" → search만
  elif intent_complexity == "complex" → search + analysis
```

### 구현

**Step 1: Intent Analysis 출력 확장**

**현재**:
```json
{
  "intent_type": "LEGAL_CONSULT",
  "reasoning": "법률 정보 검색"
}
```

**개선**:
```json
{
  "intent_type": "LEGAL_CONSULT",
  "complexity": "simple",  // ← 추가
  "reasoning": "단순 법률 조항 확인",
  "requires_analysis": false  // ← 추가
}
```

**Step 2: Agent Selection에서 Intent 결과 참고**

```python
async def _suggest_agents(self, intent_type, query, keywords, intent_result):
    """
    intent_result: Intent Analysis의 전체 결과
    """
    # 1. Intent Analysis가 이미 판단한 경우
    if intent_result.get("requires_analysis") == False:
        logger.info(f"✅ Intent Analysis says no analysis needed")
        return ["search_team"]

    # 2. Intent complexity 기반
    complexity = intent_result.get("complexity", "medium")

    if complexity == "simple":
        return ["search_team"]
    elif complexity == "medium":
        # 키워드 추가 체크
        if any(kw in query for kw in ["비교", "분석", "계산"]):
            return ["search_team", "analysis_team"]
        else:
            return ["search_team"]
    elif complexity == "complex":
        return ["search_team", "analysis_team"]

    # 3. Fallback: LLM
    return await self._select_agents_with_llm(...)
```

**Step 3: Intent Analysis 프롬프트 수정**

```text
# intent_analysis.txt

## 출력 형식

{
  "intent_type": "LEGAL_CONSULT|MARKET_INQUIRY|...",
  "complexity": "simple|medium|complex",
  "requires_analysis": true|false,
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

**장점**:
- ✅ Intent와 Selection이 일관성 유지
- ✅ LLM이 두 번 판단 (더 신뢰)
- ✅ Fallback 체계적

**단점**:
- ❌ Intent Analysis 복잡해짐
- ❌ LLM 호출 1회 유지 (비용 동일)

---

## 아이디어 4: Few-Shot Learning ⭐⭐⭐⭐

**핵심**: Agent Selection 프롬프트에 **경계 케이스 예시** 추가

### 현재 프롬프트 (agent_selection.txt Line 142-158)

```text
### 예시 3: 해결책 요청 (핵심 예시!)
질문: "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 어떻게 해야 해?"
의도: COMPREHENSIVE
**CoT 분석**:
1. 요구사항: 상황 설명 + 해결책 요청
2. 복잡도: 높음 (구체적 상황 + 수치 비교)
3. 의존성: 법률 확인 → 상황 분석 → 해결책 제시
4. 검증: "법적으로"만 보고 search만 선택하면 불충분! 해결책 제시 필요

{
    "selected_agents": ["search_team", "analysis_team"],
    ...
}
```

### 개선: 경계 케이스 예시 대폭 추가

```text
### 예시 4: 경계 케이스 - 단순 법률 질문
질문: "공인중개사가 할 수 없는 금지행위에는 어떤 것들이 있나요?"
의도: LEGAL_CONSULT

**❌ 잘못된 판단**:
- "법률 정보이므로 분석 필요" → ["search_team", "analysis_team"]

**✅ 올바른 판단**:
- 단순 법률 조항 나열
- 분석/평가/비교 불필요
- 검색만으로 충분

{
    "selected_agents": ["search_team"],
    "reasoning": "법률 조항 나열만 필요, 분석 불요",
    "confidence": 0.9
}

### 예시 5: 경계 케이스 - 법률 + 적용
질문: "우리 계약서의 전세금 인상 조항이 법적으로 문제없나요?"
의도: CONTRACT_REVIEW

**❌ 잘못된 판단**:
- "법률 확인만 필요" → ["search_team"]

**✅ 올바른 판단**:
- 법률 확인 필요
- 계약서와 비교 분석 필요
- 법적 타당성 평가 필요

{
    "selected_agents": ["search_team", "analysis_team"],
    "reasoning": "법률 확인 후 계약서 분석 필요",
    "confidence": 0.85
}

### 예시 6: 경계 케이스 - 시세 조회
질문: "강남구 아파트 전세 시세 알려줘"
의도: MARKET_INQUIRY

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

**✅ 올바른 판단**:
- 시세 조회 필요
- 지역 간 비교 분석 필요

{
    "selected_agents": ["search_team", "analysis_team"],
    "reasoning": "시세 조회 후 비교 분석 필요",
    "confidence": 0.85
}

## 경계 케이스 판단 원칙

### 🔍 Search만 필요한 경우
1. 단순 사실 나열: "~에는 어떤 것들이 있나요?"
2. 단일 정보 조회: "~가 얼마야?", "~이 뭐야?"
3. 법률 조항 확인: "~는 어떻게 돼?"
4. 시세 단순 조회: "~시세 알려줘"

### 🔍+📊 Search + Analysis 필요한 경우
1. 비교 요청: "A와 B 비교", "차이는?"
2. 평가 요청: "괜찮아?", "문제없어?", "적절해?"
3. 계산 요청: "얼마나", "몇 %"
4. 추천 요청: "어떻게 해야", "방법은", "대응은"
5. 구체적 상황: "우리 경우", "이 계약서"
6. 해결책 요청: "어떻게 해야 해?", "조치는?"
```

**장점**:
- ✅ LLM이 패턴 학습
- ✅ 경계 케이스 정확도 향상
- ✅ 설명 가능 (예시로 이해)

**단점**:
- ❌ 프롬프트 길어짐 (토큰 증가)
- ❌ 예시 관리 필요

---

## 아이디어 5: Intent와 Agent 프롬프트 동기화 ⭐⭐⭐

**문제**: Intent와 Agent Selection 프롬프트가 **다른 기준** 사용

### 현재 상황

**intent_analysis.txt**:
```text
LEGAL_CONSULT: 법률 정보가 필요한 경우
```

**agent_selection.txt**:
```text
LEGAL_CONSULT: 기본적으로 search_team
```

**→ 모순 발생 가능!**

### 해결: 프롬프트 동기화

**intent_analysis.txt 수정**:
```text
## LEGAL_CONSULT 판단 기준

다음 경우 LEGAL_CONSULT로 분류:
1. 법률 조항 확인 (예: "전세금 인상 한도는?")
2. 법률 적용 평가 (예: "우리 계약서는 괜찮아?")
3. 법률 해결책 (예: "법적으로 어떻게 해야 해?")

**중요**: LEGAL_CONSULT로 분류했다면, 다음 단계에서:
- 1번 유형 → search_team만
- 2,3번 유형 → search_team + analysis_team
```

**agent_selection.txt 수정**:
```text
## LEGAL_CONSULT Agent 선택

Intent Analysis에서 LEGAL_CONSULT로 분류된 경우:

1. **법률 조항 확인** ("~한도는?", "~이 뭐야?")
   → ["search_team"]

2. **법률 적용 평가** ("우리는~", "이 계약서는~")
   → ["search_team", "analysis_team"]

3. **법률 해결책** ("어떻게 해야~", "대응 방법은~")
   → ["search_team", "analysis_team"]
```

**장점**:
- ✅ 프롬프트 간 일관성
- ✅ LLM 혼란 감소
- ✅ 유지보수 용이

**단점**:
- ❌ 두 프롬프트 동시 수정 필요

---

## 📊 아이디어 비교

| 아이디어 | 구현 난이도 | 효과 | 비용 | 유지보수 | 추천 |
|---------|-----------|------|------|---------|------|
| 1. Intent 세분화 | 중 | 높음 | 중 | 중 | ⭐⭐⭐ |
| 2. 키워드 필터 | 낮음 | 중 | 낮음 | 쉬움 | ⭐⭐⭐⭐ |
| 3. 2단계 분류 | 중 | 매우 높음 | 동일 | 중 | ⭐⭐⭐⭐⭐ |
| 4. Few-Shot | 낮음 | 높음 | 중 (토큰↑) | 쉬움 | ⭐⭐⭐⭐ |
| 5. 프롬프트 동기화 | 낮음 | 중 | 낮음 | 쉬움 | ⭐⭐⭐ |

---

## 🎯 최종 권장: 복합 전략

**Phase 1: 즉시 적용** (1시간)

1. **키워드 필터** (아이디어 2)
   ```python
   # planning_agent.py _suggest_agents
   if intent_type == IntentType.LEGAL_CONSULT:
       if any(kw in query for kw in ["비교", "분석", "계산", "평가", "추천", "어떻게"]):
           return ["search_team", "analysis_team"]
       else:
           return ["search_team"]
   ```

2. **Few-Shot 예시 추가** (아이디어 4)
   ```text
   # agent_selection.txt
   # 경계 케이스 예시 7개 추가
   ```

**Phase 2: 중기 개선** (2-3시간)

3. **2단계 분류** (아이디어 3)
   ```python
   # Intent Analysis 출력에 complexity 추가
   # Agent Selection에서 complexity 참고
   ```

4. **프롬프트 동기화** (아이디어 5)
   ```text
   # intent_analysis.txt와 agent_selection.txt 기준 통일
   ```

**Phase 3: 장기 개선** (선택)

5. **Intent 세분화** (아이디어 1)
   ```python
   # LEGAL_CONSULT → LEGAL_FACT_CHECK / LEGAL_APPLICATION / LEGAL_COMPREHENSIVE
   ```

---

## 💡 Q2 & Q4 종합 답변

### Q4: Priority 필드 목적

**→ 순서(Order) + 우선순위(Priority) 둘 다!**

1. **순서**: 실행 순서 결정 (sequential)
2. **우선순위**: 병렬 실행 시 중요도
3. **중복 지원**: Q1 요구사항 (같은 팀 여러번)
4. **동적 조정**: ExecutionOrchestrator 활용

**추가하면 좋은 점**:
- ✅ 실행 순서 보장
- ✅ 중복 팀 처리
- ✅ 병렬 최적화
- ✅ 동적 재정렬

### Q2: LEGAL_CONSULT 경계 케이스

**추천 전략**: 키워드 필터 + Few-Shot

```python
# 1. 키워드 필터 (즉시)
if intent_type == IntentType.LEGAL_CONSULT:
    analysis_keywords = ["비교", "분석", "계산", "평가", "추천", "어떻게", "방법", "괜찮아"]
    if not any(kw in query for kw in analysis_keywords):
        return ["search_team"]
```

```text
# 2. Few-Shot 예시 (agent_selection.txt)
### 예시: 단순 법률 질문
질문: "공인중개사 금지행위는?"
→ ["search_team"]

### 예시: 법률 적용 평가
질문: "우리 계약서는 괜찮아?"
→ ["search_team", "analysis_team"]
```

---

**작성 완료**: 2025-10-21
**다음 단계**: 종합 수정 방안 작성
