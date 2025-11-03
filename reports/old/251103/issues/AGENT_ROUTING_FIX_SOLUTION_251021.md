# 에이전트 라우팅 문제 해결 방안

**작성일**: 2025-10-21
**심각도**: MEDIUM
**예상 소요 시간**: 1시간
**예상 효과**: 응답 시간 56% 단축 (30초 → 13초)

---

## 🔴 문제 요약

### 발견된 문제
1. **에이전트 실행 순서 역순**: `search → analysis` 계획이 `analysis → search`로 실행됨
2. **Intent vs Agent Selection 모순**: "검색만 충분" → "검색+분석 필요"
3. **불필요한 분석 에이전트 실행**: 단순 정보 검색에도 분석 에이전트 사용

### 영향
- **현재**: 30초 평균 응답 시간
- **개선 후**: 13초 (56% 단축)
- **비용**: 불필요한 LLM 호출 제거

---

## 🔧 해결 방안

### 해결책 1: Step 실행 순서 수정 (필수) ⭐⭐⭐

#### 원인 분석
```python
# planning_agent.py Line 645-663
for i, agent_name in enumerate(selected_agents):
    step = ExecutionStep(
        agent_name=agent_name,
        priority=i,  # ← 0, 1, 2, ...
        ...
    )
```

**문제**:
- `selected_agents = ['search_team', 'analysis_team']`
- priority: search_team=0, analysis_team=1
- 하지만 step_id는 자동 생성되어 순서가 뒤바뀜

#### 수정 방법

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치 찾기**:
```python
# "Executing 2 teams sequentially" 로그 근처
# state["execution_plan"]["steps"] 순회하는 부분
```

**현재 코드 (추정)**:
```python
# team_supervisor.py - execute_node
async def execute_node(state: MainSupervisorState):
    execution_plan = state.get("execution_plan", {})
    steps = execution_plan.get("steps", [])

    # ❌ 문제: reverse 또는 sorted(reverse=True) 사용?
    for step in reversed(steps):  # 또는 sorted(steps, reverse=True)
        team_name = step["agent_name"]
        await execute_team(team_name)
```

**수정 코드**:
```python
# team_supervisor.py - execute_node
async def execute_node(state: MainSupervisorState):
    execution_plan = state.get("execution_plan", {})
    steps = execution_plan.get("steps", [])

    # ✅ 수정: priority 순으로 정렬 (오름차순)
    sorted_steps = sorted(steps, key=lambda x: x.get("priority", 999))

    logger.info(f"[TeamSupervisor] Executing {len(sorted_steps)} teams sequentially")
    logger.debug(f"[TeamSupervisor] Execution order: {[s['agent_name'] for s in sorted_steps]}")

    for step in sorted_steps:
        team_name = step["agent_name"]
        logger.info(f"[TeamSupervisor] Starting team: {team_name} (priority: {step.get('priority')})")
        await execute_team(team_name)
```

**검증 로그**:
```log
# 수정 후 기대 로그
[TeamSupervisor] Execution order: ['search_team', 'analysis_team']
[TeamSupervisor] Starting team: search_team (priority: 0)
[SearchTeam] Completed
[TeamSupervisor] Starting team: analysis_team (priority: 1)
[AnalysisTeam] Completed
```

---

### 해결책 2: Agent Selection 로직 개선 (권장) ⭐⭐⭐

#### 원인 분석
```python
# Intent Analysis
reasoning: "검색만으로 충분 → LEGAL_CONSULT"

# 4초 후 Agent Selection
reasoning: "검색만으로 충분하지 않으며, 분석이 필요함"
```

**문제**: LLM이 Intent와 Agent Selection에서 상반된 판단

#### 수정 방법 A: Intent 결과 반영 (간단)

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**위치**: Line 297-361 `_suggest_agents` 메서드

**수정 코드**:
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
    if self.llm_service:
        try:
            agents = await self._select_agents_with_llm(
                intent_type=intent_type,
                query=query,
                keywords=keywords,
                attempt=1
            )
            if agents:
                logger.info(f"✅ Primary LLM selected agents: {agents}")
                return agents
        except Exception as e:
            logger.warning(f"⚠️ Primary LLM agent selection failed: {e}")

    # ... 나머지 코드 동일
```

**효과**:
- "공인중개사 금지행위?" → search_team만 (13초)
- "공인중개사 금지행위 분석해줘" → search_team + analysis_team (30초)

#### 수정 방법 B: Agent Selection 프롬프트 수정 (더 나음)

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt`

**현재 프롬프트 (추정)**:
```text
사용자 질문: {query}
의도: {intent_type}

어떤 에이전트가 필요한가?
- search_team: 정보 검색
- analysis_team: 데이터 분석
- document_team: 문서 작성

필요한 에이전트를 선택하라.
```

**수정 프롬프트**:
```text
사용자 질문: {query}
의도: {intent_type}
키워드: {keywords}

## 에이전트 선택 규칙

1. **단순 정보 검색 (search_team만)**:
   - 법률 조항 확인
   - 시세 조회
   - 매물 검색
   - "~이 뭐야?", "~는 어떻게?", "~알려줘" 등

2. **검색 + 분석 (search_team + analysis_team)**:
   - 비교 분석 필요
   - 계산/추천 필요
   - 리스크 평가 필요
   - "분석", "비교", "계산", "평가", "추천" 포함

3. **문서 작성 (document_team)**:
   - 계약서 작성/검토
   - "작성", "만들어", "검토" 포함

## 중요
- **최소한의 에이전트만 선택**하라
- 단순 질문에 분석 에이전트를 추가하지 마라

선택:
```

---

### 해결책 3: Safe Default 수정 (선택) ⭐

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**위치**: Line 346-361

**현재 코드**:
```python
safe_defaults = {
    IntentType.LEGAL_CONSULT: ["search_team"],
    IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],  # ❌ 분석 불필요
    # ...
}
```

**수정 코드**:
```python
safe_defaults = {
    IntentType.LEGAL_CONSULT: ["search_team"],  # ✅ 검색만
    IntentType.MARKET_INQUIRY: ["search_team"],  # ✅ 시세 조회도 검색만
    IntentType.LOAN_CONSULT: ["search_team"],   # ✅ 대출 정보도 검색만
    IntentType.CONTRACT_CREATION: ["document_team"],
    IntentType.CONTRACT_REVIEW: ["search_team", "document_team"],  # ✅ 분석 제거
    IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
    IntentType.RISK_ANALYSIS: ["analysis_team"],
    IntentType.UNCLEAR: ["search_team"],  # ✅ 불분명할 때는 검색만
    IntentType.IRRELEVANT: ["search_team"],
    IntentType.ERROR: ["search_team"]
}
```

---

## 📋 구현 단계

### Phase 1: 긴급 수정 (20분)

**우선순위 HIGH**:

1. **Step 실행 순서 수정**
   ```python
   # team_supervisor.py
   sorted_steps = sorted(steps, key=lambda x: x.get("priority", 999))
   for step in sorted_steps:
       ...
   ```

2. **LEGAL_CONSULT 기본 설정**
   ```python
   # planning_agent.py Line 347
   IntentType.LEGAL_CONSULT: ["search_team"],  # analysis 제거
   ```

### Phase 2: 근본 해결 (40분)

**우선순위 MEDIUM**:

3. **Agent Selection 로직 개선**
   ```python
   # planning_agent.py _suggest_agents 메서드
   # 분석 필요 키워드 체크 로직 추가
   ```

4. **프롬프트 수정**
   ```text
   # agent_selection.txt
   # "최소한의 에이전트만 선택" 규칙 추가
   ```

---

## 🧪 테스트 시나리오

### 테스트 1: 단순 법률 질문

**질문**: "공인중개사가 할 수 없는 금지행위에는 어떤 것들이 있나요?"

**기대 결과**:
```log
[TeamSupervisor] Selected agents: ['search_team']
[TeamSupervisor] Execution order: ['search_team']
[SearchTeam] Preparing search
[SearchTeam] Completed (3초)
총 소요 시간: 13초 (기존 30초)
```

### 테스트 2: 분석 필요한 질문

**질문**: "공인중개사 금지행위를 위반했을 때 어떤 처벌을 받는지 분석해줘"

**기대 결과**:
```log
[TeamSupervisor] Selected agents: ['search_team', 'analysis_team']
[TeamSupervisor] Execution order: ['search_team', 'analysis_team']
[SearchTeam] Preparing search
[SearchTeam] Completed (3초)
[AnalysisTeam] Preparing analysis
[AnalysisTeam] Completed (13초)
총 소요 시간: 26초
```

### 테스트 3: 시세 조회

**질문**: "강남구 아파트 시세 알려줘"

**기대 결과**:
```log
[TeamSupervisor] Selected agents: ['search_team']
총 소요 시간: 13초 (기존 30초)
```

---

## 📊 예상 효과

### 성능 개선

| 질문 유형 | 현재 | 개선 후 | 단축 |
|----------|------|---------|------|
| 단순 법률 질문 | 30초 | 13초 | 56% |
| 단순 시세 조회 | 30초 | 13초 | 56% |
| 분석 필요 질문 | 30초 | 26초 | 13% |

### 비용 절감

**LLM 호출 감소**:
- 현재: Intent(1) + Agent Selection(1) + Analysis Tool(1) + Analysis Insight(1) + Search Tool(1) + Response(1) = 6회
- 개선: Intent(1) + Agent Selection(1) + Search Tool(1) + Response(1) = 4회
- **33% 감소**

---

## ⚠️ 주의사항

### 수정 시 주의

1. **team_supervisor.py 수정 시**:
   - 기존 로그 구조 유지
   - priority 필드 없는 경우 대비 (기본값 999)

2. **planning_agent.py 수정 시**:
   - 기존 LLM 로직 보존
   - Fallback 동작 유지

3. **프롬프트 수정 시**:
   - 기존 출력 형식 유지 (JSON)
   - selected_agents 필드명 동일

### 롤백 계획

1. **코드 백업**:
   ```bash
   cp team_supervisor.py team_supervisor.py.backup
   cp planning_agent.py planning_agent.py.backup
   ```

2. **문제 발생 시**:
   - 백업 파일로 복원
   - 서버 재시작

---

## 📝 구현 체크리스트

### Phase 1 (긴급)
- [ ] team_supervisor.py - Step 순서 정렬 추가
- [ ] planning_agent.py - LEGAL_CONSULT safe default 수정
- [ ] 테스트: 단순 법률 질문 (응답 시간 확인)
- [ ] 테스트: 에이전트 실행 순서 로그 확인

### Phase 2 (근본 해결)
- [ ] planning_agent.py - _suggest_agents 로직 개선
- [ ] agent_selection.txt - 프롬프트 수정
- [ ] 테스트: 다양한 질문 유형
- [ ] 성능 측정: 응답 시간 비교

### Phase 3 (검증)
- [ ] 10개 질문으로 종합 테스트
- [ ] 로그 분석: 에이전트 선택 적절성
- [ ] 사용자 테스트: 답변 품질 확인

---

## 🎯 최종 권장

### 즉시 구현
1. ✅ **Step 순서 정렬** (team_supervisor.py)
2. ✅ **LEGAL_CONSULT 기본값 수정** (planning_agent.py)

**소요 시간**: 20분
**예상 효과**: 56% 응답 시간 단축

### 점진적 개선
3. ⏳ **Agent Selection 로직** (planning_agent.py)
4. ⏳ **프롬프트 수정** (agent_selection.txt)

**소요 시간**: 40분
**예상 효과**: 더 정확한 에이전트 선택

---

**작성 완료**: 2025-10-21
**다음 단계**: team_supervisor.py 코드 확인 및 수정