# 에이전트 라우팅 수정안 심층 분석 보고서

**작성일**: 2025-10-21
**분석 대상**: AGENT_ROUTING_FIX_SOLUTION_251021.md
**분석 결과**: ⚠️ **CRITICAL - 근본 원인 오진단 발견**

---

## 📋 Executive Summary

기존 솔루션 문서를 실제 코드와 대조 분석한 결과, **제안된 해결책이 실제 문제를 해결하지 못함**을 확인했습니다.

### 주요 발견사항
1. ❌ **문제 1번 진단 오류**: Step 실행 순서 역순 문제의 근본 원인을 잘못 파악함
2. ✅ **문제 2번 진단 정확**: Intent vs Agent Selection 모순은 정확히 진단됨
3. ⚠️ **구현 위치 오류**: 제안된 수정 위치가 실제 코드 구조와 불일치

---

## 🔍 심층 분석

### 1️⃣ 문제 1: Step 실행 순서 역순 (근본 원인 재분석)

#### 솔루션 문서의 진단 (❌ 오류)
```
원인: team_supervisor.py가 reversed(steps) 또는 sorted(reverse=True) 사용
해결책: sorted(steps, key=lambda x: x.get("priority", 999)) 추가
```

#### 실제 코드 분석 (✅ 진실)

**team_supervisor.py Line 627-639** (`_execute_teams_sequential`)
```python
async def _execute_teams_sequential(
    self,
    teams: List[str],  # ← 이미 팀 이름 리스트로 전달받음!
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """팀 순차 실행 + execution_steps status 업데이트"""
    logger.info(f"[TeamSupervisor] Executing {len(teams)} teams sequentially")

    results = {}
    planning_state = main_state.get("planning_state")

    for team_name in teams:  # ← teams 리스트를 그대로 순회
        if team_name in self.teams:
            # Step ID 찾기
            step_id = self._find_step_id_for_team(team_name, planning_state)
            ...
```

**핵심 발견**:
- `_execute_teams_sequential`은 **`teams` 리스트를 받아서 그대로 순회**함
- reversed()나 sorted(reverse=True)를 사용하지 **않음**
- 문제는 이 함수가 아니라 **`teams` 리스트를 생성하는 곳**에 있음!

#### 진짜 문제 위치 추적

**Step 1**: `teams` 리스트는 어디서 오는가?

team_supervisor.py Line 577-592:
```python
execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
active_teams = state.get("active_teams", [])  # ← 여기서 가져옴!

# 공유 상태 생성
shared_state = StateManager.create_shared_state(...)

# 팀별 실행
if execution_strategy == "parallel" and len(active_teams) > 1:
    results = await self._execute_teams_parallel(active_teams, ...)
else:
    results = await self._execute_teams_sequential(active_teams, ...)  # ← active_teams 전달
```

**Step 2**: `active_teams`는 어디서 생성되는가?

team_supervisor.py Line 362-369:
```python
# 활성화할 팀 결정
active_teams = set()
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)  # ← set을 list로 변환!
```

**🔴 근본 원인 발견!**
```
set → list 변환 시 순서가 보장되지 않음!
Python의 set은 순서가 없는 자료구조입니다.
```

#### 실제 실행 흐름 예시

```python
# planning_state["execution_steps"]에서 추출
execution_steps = [
    {"step_id": "step_0", "agent_name": "search_team", "team": "search", "priority": 0},
    {"step_id": "step_1", "agent_name": "analysis_team", "team": "analysis", "priority": 1}
]

# Line 362-369 실행
active_teams = set()  # {}
for step in execution_steps:
    active_teams.add(step["team"])
    # 1차: active_teams = {"search"}
    # 2차: active_teams = {"search", "analysis"}  ← set은 순서 없음!

state["active_teams"] = list(active_teams)
# 결과: ["analysis", "search"] 또는 ["search", "analysis"] (비결정적!)
# Python 3.7+에서는 insertion order 보장되지만 set → list는 예외
```

#### 올바른 해결책

**위치**: team_supervisor.py Line 362-369

**현재 코드 (❌ 문제)**:
```python
# 활성화할 팀 결정
active_teams = set()
for step in planning_state["execution_steps"]:
    team = step.get("team")
    if team:
        active_teams.add(team)

state["active_teams"] = list(active_teams)  # ← set → list (순서 상실!)
```

**수정 코드 (✅ 해결)**:
```python
# 활성화할 팀 결정 (priority 순서 보장)
# Step 1: execution_steps를 priority 순으로 정렬
sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

# Step 2: 정렬된 순서대로 팀 추출 (중복 제거하되 순서 유지)
active_teams = []
seen_teams = set()
for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)

state["active_teams"] = active_teams  # ← 이미 리스트, 순서 보장됨
logger.info(f"[TeamSupervisor] Active teams in priority order: {active_teams}")
```

---

### 2️⃣ 문제 2: Intent vs Agent Selection 모순 (진단 정확 ✅)

#### 솔루션 문서의 진단 (✅ 정확)
```
원인: LLM이 Intent와 Agent Selection에서 상반된 판단
예시:
  Intent: "검색만으로 충분 → LEGAL_CONSULT"
  Agent Selection (4초 후): "검색만으로 충분하지 않으며, 분석이 필요함"
```

#### 실제 코드 확인

**planning_agent.py Line 297-361** (`_suggest_agents` 메서드):
```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    """
    LLM 기반 Agent 추천 - 다층 Fallback 전략
    """
    # === 1차: Primary LLM으로 Agent 선택 ===
    if self.llm_service:
        try:
            agents = await self._select_agents_with_llm(...)  # ← LLM 호출
            if agents:
                logger.info(f"✅ Primary LLM selected agents: {agents}")
                return agents
        except Exception as e:
            logger.warning(f"⚠️ Primary LLM agent selection failed: {e}")

    # === 2차: Simplified prompt retry ===
    # === 3차: Safe default agents ===
    safe_defaults = {
        IntentType.LEGAL_CONSULT: ["search_team"],  # ← 기본값: search만
        IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],  # ← 기본값: search+analysis
        ...
    }
```

**문제 확인**:
1. ✅ LEGAL_CONSULT의 safe_default는 ["search_team"]으로 올바름
2. ❌ LLM이 안내 프롬프트를 무시하고 analysis_team 추가함
3. ❌ Intent Analysis에서 "검색만 충분"이라고 판단해도 Agent Selection이 무시함

#### agent_selection.txt 프롬프트 분석

**Line 96** (의도별 매핑 가이드):
```
| LEGAL_CONSULT | ["search_team"] | 해결책 요청시 → + analysis_team |
```

**Line 142-158** (예시 3 - 핵심!):
```
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
    "reasoning": "...'어떻게 해야' = 단순 법률 조회 아님, 분석 필수",
    ...
}
```

**문제 분석**:
- 프롬프트는 "해결책 요청" 시 analysis_team 추가를 권장함
- "공인중개사 금지행위?" ← 단순 정보 조회
- "법적으로 어떻게 해야 해?" ← 해결책 요청
- LLM이 "금지행위"라는 법률 키워드를 보고 "법적으로" 패턴과 매칭시켜 해결책 요청으로 오판할 가능성 있음

#### 올바른 해결책

**방법 A**: planning_agent.py에 키워드 필터 추가 (솔루션 문서 제안 - ✅ 유효)

**위치**: planning_agent.py Line 297-313

**추가 코드**:
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
            "어떻게", "방법", "차이", "장단점", "해야", "하면"
        ]

        needs_analysis = any(kw in query for kw in analysis_needed_keywords)

        if not needs_analysis:
            logger.info(f"✅ LEGAL_CONSULT without analysis keywords, using search_team only")
            return ["search_team"]

    # === 기존 LLM 기반 Agent 선택 로직 ===
    if self.llm_service:
        ...
```

**방법 B**: agent_selection.txt 프롬프트 수정 (더 명확한 가이드)

**추가할 섹션** (Line 92 다음):
```
## ⚠️ LEGAL_CONSULT 특별 규칙

**단순 법률 조회** (search_team만):
- "~이 뭐야?", "~란?", "~인가요?", "~알려줘"
- 법률 조항, 규정, 제도 설명 요청
- **예시**: "공인중개사 금지행위는?", "전세금 인상률 한도는?"

**법률 + 해결책** (search_team + analysis_team):
- "~해야 해?", "~하면 어떻게?", "~방법은?", "~대처법은?"
- 구체적 상황 + 판단/조언 요청
- **예시**: "집주인이 5% 넘게 올려달래. 어떻게 해야 해?"

**핵심**: "법적으로"라는 단어만으로 분석 팀을 추가하지 마세요!
질문이 **사실 확인**인지 **해결책 요청**인지 구분하세요.
```

---

### 3️⃣ 문제 3: Safe Default 수정 (부분 정확 ⚠️)

#### 솔루션 문서의 제안
```python
safe_defaults = {
    IntentType.LEGAL_CONSULT: ["search_team"],  # ✅ 검색만
    IntentType.MARKET_INQUIRY: ["search_team"],  # ✅ 시세 조회도 검색만
    IntentType.LOAN_CONSULT: ["search_team"],   # ✅ 대출 정보도 검색만
    ...
}
```

#### 실제 코드 (planning_agent.py Line 346-361)
```python
safe_defaults = {
    IntentType.LEGAL_CONSULT: ["search_team"],
    IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],  # ← 현재
    IntentType.LOAN_CONSULT: ["search_team", "analysis_team"],    # ← 현재
    IntentType.CONTRACT_CREATION: ["document_team"],
    IntentType.CONTRACT_REVIEW: ["search_team", "analysis_team"],
    IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
    IntentType.RISK_ANALYSIS: ["search_team", "analysis_team"],
    IntentType.UNCLEAR: ["search_team", "analysis_team"],
    IntentType.IRRELEVANT: ["search_team"],
    IntentType.ERROR: ["search_team", "analysis_team"]
}
```

#### ⚠️ 사용자 확인 필요!

**질문 1**: MARKET_INQUIRY (시세 조회)에 analysis_team이 필요한가?
- **예시**: "강남구 아파트 시세 알려줘" → search만으로 충분?
- **현재**: search + analysis (시장 분석 포함)
- **제안**: search만 (단순 조회)

**질문 2**: LOAN_CONSULT (대출 상담)에 analysis_team이 필요한가?
- **예시**: "전세자금대출 금리 얼마?" → search만으로 충분?
- **예시**: "내 상황에 맞는 대출 추천해줘" → search + analysis 필요
- **현재**: search + analysis (계산 포함)
- **제안**: search만? 아니면 유지?

**📋 사용자 결정 필요**:
```
1. 시세 조회 질문에 시장 분석을 기본 제공할 것인가?
   - YES → MARKET_INQUIRY: ["search_team", "analysis_team"] 유지
   - NO → MARKET_INQUIRY: ["search_team"] 변경

2. 대출 상담 질문에 대출 계산을 기본 제공할 것인가?
   - YES → LOAN_CONSULT: ["search_team", "analysis_team"] 유지
   - NO → LOAN_CONSULT: ["search_team"] 변경
```

---

## 🎯 수정 우선순위 및 영향도

### Priority 1: CRITICAL (즉시 수정 필요)

#### 1-1. Step 실행 순서 보장 (team_supervisor.py Line 362-369)

**현재 문제**:
```python
active_teams = set()  # ← 순서 없음
for step in planning_state["execution_steps"]:
    active_teams.add(step.get("team"))
state["active_teams"] = list(active_teams)  # ← 순서 보장 안됨
```

**수정 후**:
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
logger.info(f"[TeamSupervisor] Active teams in priority order: {active_teams}")
```

**영향**:
- ✅ Step 실행 순서 문제 **완전 해결**
- ✅ 로그에서 `["search_team", "analysis_team"]` 순서 보장
- ✅ search → analysis 순차 실행 보장

**소요 시간**: 5분

---

### Priority 2: HIGH (권장 수정)

#### 2-1. LEGAL_CONSULT 키워드 필터 (planning_agent.py Line 297)

**추가 코드**:
```python
async def _suggest_agents(...) -> List[str]:
    # ✅ LEGAL_CONSULT 사전 필터링
    if intent_type == IntentType.LEGAL_CONSULT:
        analysis_needed_keywords = [
            "분석", "비교", "계산", "평가", "추천", "검토",
            "어떻게", "방법", "차이", "장단점", "해야", "하면"
        ]
        needs_analysis = any(kw in query for kw in analysis_needed_keywords)
        if not needs_analysis:
            logger.info(f"✅ LEGAL_CONSULT simple query, using search_team only")
            return ["search_team"]

    # 기존 LLM 로직
    if self.llm_service:
        ...
```

**영향**:
- ✅ "공인중개사 금지행위?" → search만 (13초)
- ✅ "금지행위 위반시 처벌은 어떻게?" → search + analysis (26초)
- ✅ 응답 시간 56% 단축 (단순 질문)

**소요 시간**: 10분

---

### Priority 3: MEDIUM (선택적 개선)

#### 3-1. agent_selection.txt 프롬프트 개선

**추가할 섹션** (Line 92 다음):
```
## ⚠️ LEGAL_CONSULT 특별 규칙

**단순 법률 조회** (search_team만):
- 패턴: "~이 뭐야?", "~란?", "~인가요?", "~알려줘"
- 예시: "공인중개사 금지행위는?", "전세금 인상률 한도는?"

**법률 + 해결책** (search_team + analysis_team):
- 패턴: "~해야 해?", "~하면 어떻게?", "~방법은?"
- 예시: "집주인이 5% 넘게 올려달래. 어떻게 해야 해?"

**핵심**: "법적으로"라는 단어만으로 분석 팀을 추가하지 마세요!
```

**영향**:
- ✅ LLM의 Agent 선택 정확도 향상
- ✅ Intent와 Agent Selection 모순 감소

**소요 시간**: 15분

---

#### 3-2. Safe Default 조정 (사용자 확인 필요)

**현재**:
```python
IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
IntentType.LOAN_CONSULT: ["search_team", "analysis_team"],
```

**제안 (보수적)**:
```python
IntentType.MARKET_INQUIRY: ["search_team"],  # 단순 시세 조회
IntentType.LOAN_CONSULT: ["search_team"],    # 단순 대출 정보
```

**영향**:
- ⚠️ **사용자 경험 변화**: 시세/대출 질문에 분석이 기본 제공되지 않음
- ✅ **응답 속도 개선**: 13초 (기존 26-30초)
- ❌ **분석 필요 시**: 사용자가 명시적으로 "분석해줘" 요청 필요

**📋 사용자 확인 필요!**

---

## 🚨 솔루션 문서의 오류 정리

### 오류 1: 문제 위치 오진단

**문서 주장**:
```
team_supervisor.py의 execute_node 또는 _execute_teams_sequential에서
reversed(steps) 또는 sorted(steps, reverse=True) 사용
```

**실제**:
```
해당 함수들은 reversed()를 사용하지 않음.
문제는 active_teams를 set → list 변환할 때 순서가 상실되는 것.
```

**영향**:
- ❌ 제안된 수정 위치가 잘못됨
- ❌ 제안된 코드를 추가해도 문제 해결 안됨

---

### 오류 2: 코드 예시 불일치

**문서의 "현재 코드 (추정)"**:
```python
# team_supervisor.py - execute_node
async def execute_node(state: MainSupervisorState):
    execution_plan = state.get("execution_plan", {})
    steps = execution_plan.get("steps", [])

    # ❌ 문제: reverse 또는 sorted(reverse=True) 사용?
    for step in reversed(steps):  # ← 실제로 존재하지 않음!
        team_name = step["agent_name"]
        await execute_team(team_name)
```

**실제 코드**:
```python
# execute_node라는 함수는 존재하지 않음!
# 실제는 execute_teams_node → _execute_teams_sequential
async def _execute_teams_sequential(
    self,
    teams: List[str],  # ← 이미 팀 이름 리스트
    shared_state: SharedState,
    main_state: MainSupervisorState
):
    for team_name in teams:  # ← reversed() 없음!
        ...
```

---

### 오류 3: 검증 로그 예시 부정확

**문서의 기대 로그**:
```log
[TeamSupervisor] Execution order: ['search_team', 'analysis_team']
[TeamSupervisor] Starting team: search_team (priority: 0)
[SearchTeam] Completed
[TeamSupervisor] Starting team: analysis_team (priority: 1)
```

**실제 로그 형식** (team_supervisor.py Line 634):
```python
logger.info(f"[TeamSupervisor] Executing {len(teams)} teams sequentially")
# "Execution order" 로그는 없음!
# "Starting team" 로그도 없음!
```

---

## ✅ 올바른 수정 계획

### Phase 1: 긴급 수정 (10분)

#### 수정 1: Step 실행 순서 보장
- **파일**: `team_supervisor.py`
- **위치**: Line 362-369
- **변경**: set → 순서 보장 리스트

```python
# 기존 (❌)
active_teams = set()
for step in planning_state["execution_steps"]:
    active_teams.add(step.get("team"))
state["active_teams"] = list(active_teams)

# 수정 (✅)
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
logger.info(f"[TeamSupervisor] Active teams in priority order: {active_teams}")
```

---

#### 수정 2: LEGAL_CONSULT 키워드 필터
- **파일**: `planning_agent.py`
- **위치**: Line 297 (async def _suggest_agents 시작 부분)
- **변경**: 키워드 기반 사전 필터링 추가

```python
async def _suggest_agents(...) -> List[str]:
    # ✅ 추가: LEGAL_CONSULT 사전 필터링
    if intent_type == IntentType.LEGAL_CONSULT:
        analysis_needed_keywords = [
            "분석", "비교", "계산", "평가", "추천", "검토",
            "어떻게", "방법", "차이", "장단점", "해야", "하면"
        ]
        needs_analysis = any(kw in query for kw in analysis_needed_keywords)
        if not needs_analysis:
            logger.info(f"✅ LEGAL_CONSULT simple query, using search_team only")
            return ["search_team"]

    # === 기존 LLM 기반 Agent 선택 로직 ===
    if self.llm_service:
        ...
```

---

### Phase 2: 선택적 개선 (25분)

#### 개선 1: agent_selection.txt 프롬프트 개선
- **파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt`
- **위치**: Line 92 다음 (의도별 매핑 가이드 전)
- **변경**: LEGAL_CONSULT 특별 규칙 섹션 추가

#### 개선 2: Safe Default 조정 (📋 사용자 확인 필요)
- **파일**: `planning_agent.py`
- **위치**: Line 346-361
- **변경**: MARKET_INQUIRY, LOAN_CONSULT 기본값 조정

---

## 📊 예상 효과 (수정 후)

### 시나리오 1: 단순 법률 질문
**질문**: "공인중개사 금지행위는?"

**현재 (❌)**:
```
1. Intent: LEGAL_CONSULT
2. Agent Selection: ["search_team", "analysis_team"]  ← LLM이 analysis 추가
3. 실행 순서: ["analysis_team", "search_team"]  ← set 때문에 역순
4. 소요 시간: 30초
```

**수정 후 (✅)**:
```
1. Intent: LEGAL_CONSULT
2. Keyword Filter: "분석/어떻게" 없음 → ["search_team"]
3. 실행 순서: ["search_team"]  ← 단일 팀
4. 소요 시간: 13초 (56% 단축)
```

---

### 시나리오 2: 해결책 요청
**질문**: "집주인이 전세금 10억으로 올려달래. 법적으로 어떻게 해야 해?"

**현재 (❌)**:
```
1. Intent: COMPREHENSIVE
2. Agent Selection: ["search_team", "analysis_team"]
3. 실행 순서: ["analysis_team", "search_team"]  ← 역순!
4. 결과: analysis가 search 데이터 없이 먼저 실행 → 오류 가능성
```

**수정 후 (✅)**:
```
1. Intent: COMPREHENSIVE
2. Agent Selection: ["search_team", "analysis_team"]
3. 실행 순서: ["search_team", "analysis_team"]  ← 올바른 순서!
4. 결과: search → analysis 순차 실행 → 정상
```

---

## 🔧 구현 체크리스트

### Phase 1: 긴급 수정 (필수)
- [ ] **team_supervisor.py Line 362-369**: set → 순서 보장 리스트 변경
- [ ] **planning_agent.py Line 297**: LEGAL_CONSULT 키워드 필터 추가
- [ ] **테스트 1**: "공인중개사 금지행위?" → search만 실행 확인
- [ ] **테스트 2**: "강남구 시세 확인하고 투자 분석" → search → analysis 순서 확인

### Phase 2: 선택적 개선
- [ ] **agent_selection.txt Line 92**: LEGAL_CONSULT 특별 규칙 섹션 추가
- [ ] **📋 사용자 확인**: MARKET_INQUIRY, LOAN_CONSULT safe default 변경 여부
- [ ] **planning_agent.py Line 346-361**: safe_defaults 조정 (사용자 결정 후)
- [ ] **테스트 3**: 다양한 시세/대출 질문으로 검증

---

## 📋 사용자 확인 필요 사항

### 질문 1: 시세 조회 기본 동작
**시나리오**: "강남구 아파트 시세 알려줘"

**옵션 A** (현재):
- Agents: search_team + analysis_team
- 결과: 시세 데이터 + 시장 분석
- 시간: 26초

**옵션 B** (제안):
- Agents: search_team만
- 결과: 시세 데이터만
- 시간: 13초
- 분석 필요 시: "강남구 아파트 시세 분석해줘" 명시 필요

**선택**: A / B ?

---

### 질문 2: 대출 상담 기본 동작
**시나리오**: "전세자금대출 금리 얼마?"

**옵션 A** (현재):
- Agents: search_team + analysis_team
- 결과: 대출 정보 + 한도 계산
- 시간: 26초

**옵션 B** (제안):
- Agents: search_team만
- 결과: 대출 정보만
- 시간: 13초
- 계산 필요 시: "내 상황에 맞는 대출 추천해줘" 명시 필요

**선택**: A / B ?

---

### 질문 3: 프롬프트 개선 방향
**agent_selection.txt에 LEGAL_CONSULT 특별 규칙 추가**

**추가할 내용**:
```
## ⚠️ LEGAL_CONSULT 특별 규칙

단순 법률 조회: search_team만
법률 + 해결책: search_team + analysis_team

**핵심**: "법적으로"라는 단어만으로 분석 팀을 추가하지 마세요!
```

**적용**: YES / NO ?

---

## 🎯 최종 권장사항

### 즉시 적용 (Phase 1)
1. ✅ **team_supervisor.py Line 362-369**: set → 순서 보장 리스트
   - **영향**: Step 실행 순서 문제 **완전 해결**
   - **소요**: 5분
   - **위험**: 낮음 (순서만 보장)

2. ✅ **planning_agent.py Line 297**: LEGAL_CONSULT 키워드 필터
   - **영향**: 단순 법률 질문 56% 속도 개선
   - **소요**: 5분
   - **위험**: 낮음 (fallback 있음)

**총 소요 시간**: 10분
**예상 효과**: 응답 시간 56% 단축 (단순 질문), 실행 순서 100% 보장

---

### 사용자 확인 후 적용 (Phase 2)
3. ⏳ **agent_selection.txt**: LEGAL_CONSULT 규칙 추가
   - **영향**: LLM 선택 정확도 향상
   - **소요**: 15분
   - **위험**: 낮음 (가이드 추가)

4. ⏳ **planning_agent.py Line 346-361**: safe_defaults 조정
   - **영향**: 시세/대출 질문 기본 동작 변경
   - **소요**: 5분
   - **위험**: 중간 (사용자 경험 변화)
   - **📋 사용자 확인 필수!**

---

## 📝 결론

### 기존 솔루션 문서의 문제점
1. ❌ Step 실행 순서 문제의 근본 원인 오진단
2. ❌ 존재하지 않는 함수(`execute_node`)에 대한 수정 제안
3. ❌ 실제 코드와 불일치하는 예시 코드
4. ✅ Intent vs Agent Selection 모순은 정확히 진단

### 올바른 해결책
1. ✅ **team_supervisor.py Line 362-369**: set → 순서 보장 리스트 (근본 원인)
2. ✅ **planning_agent.py Line 297**: LEGAL_CONSULT 키워드 필터 (정확)
3. ⏳ **agent_selection.txt**: 프롬프트 개선 (선택)
4. ⏳ **safe_defaults**: 사용자 확인 후 조정 (선택)

### 구현 전 확인 필요
- 📋 질문 1: 시세 조회에 분석 기본 제공? (YES/NO)
- 📋 질문 2: 대출 상담에 계산 기본 제공? (YES/NO)
- 📋 질문 3: 프롬프트 개선 적용? (YES/NO)

---

**작성 완료**: 2025-10-21
**다음 단계**: 사용자 확인 후 Phase 1 구현 시작
