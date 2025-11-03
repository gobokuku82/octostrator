# 로그 분석: 에이전트 라우팅 문제점

**작성일**: 2025-10-21
**분석 대상**: 서버 시작 ~ 답변 생성 (3개 질문)
**심각도**: MEDIUM

---

## 🔴 발견된 문제점

### 1. **에이전트 실행 순서 문제** ⚠️

#### 문제 상황
```
계획된 순서: ['search_team', 'analysis_team']
실제 실행 순서: analysis_team → search_team (역순!)
```

#### 로그 증거

**첫 번째 질문**: "공인중개사가 할 수 없는 금지행위에는 어떤 것들이 있나요?"

```log
11:09:37 - Selected agents/teams for execution: ['search_team', 'analysis_team']
11:09:37 - Executing 2 teams sequentially

# Step 1 (분석) 먼저 시작
11:09:37 - Step step_1 status: pending -> in_progress
11:09:37 - [AnalysisTeam] Preparing analysis
11:09:38 - LLM Analysis Tool Selection: contract_analysis
11:09:50 - [AnalysisTeam] Completed (13초 소요)

# Step 0 (검색) 나중에 시작
11:09:50 - Step step_0 status: pending -> in_progress
11:09:50 - [SearchTeam] Preparing search
11:09:53 - [SearchTeam] Completed (3초 소요)
```

**두 번째/세 번째 질문도 동일한 패턴**:
- 모두 `['search_team', 'analysis_team']` 순서로 계획
- 모두 `analysis → search` 순으로 실행

#### 왜 문제인가?
1. **비효율**: 분석 에이전트가 검색 결과 없이 먼저 실행
2. **의존성 무시**: 검색 결과를 바탕으로 분석해야 하는데 순서가 뒤바뀜
3. **시간 낭비**: 분석(13초) + 검색(3초) = 16초인데, 병렬이면 13초면 됨

---

### 2. **Intent vs Agent Selection 불일치** ⚠️

#### 문제 상황
```
Intent Analysis: "검색만으로 충분"
Agent Selection: "검색 + 분석 모두 필요"
→ 모순!
```

#### 로그 증거

**첫 번째 질문**:
```log
# Intent Analysis
11:09:33 - LLM Intent Analysis Result: {
    'intent': 'LEGAL_CONSULT',
    'confidence': 0.9,
    'reasoning': "검색만으로 충분 → LEGAL_CONSULT"
}

# Agent Selection (4초 후)
11:09:37 - LLM agent selection reasoning:
    "법률 정보 검색이 필요하고, 이를 바탕으로 추가적인 분석이 요구됨.
     단순 법률 검색만으로는 충분하지 않으며, 분석이 필요함."

11:09:37 - LLM selected agents: ['search_team', 'analysis_team']
```

**두 번째 질문**: "관리비의 부과 대상과 납부 의무자는 누구인가요?"
```log
# Intent Analysis
11:10:05 - reasoning: "검색만으로 충분 → LEGAL_CONSULT"

# Agent Selection
11:10:09 - reasoning: "단순 법률 검색만으로는 충분하지 않으며, 분석이 필수적임."
```

**세 번째 질문**: 동일한 패턴

#### 왜 문제인가?
1. **일관성 없음**: 같은 LLM이 4초 만에 정반대 결론
2. **비용 낭비**: 불필요한 analysis_team 실행 (LLM 호출 추가)
3. **응답 시간**: 검색만 하면 3초인데 분석 포함해서 16초+

---

### 3. **분석 에이전트의 불필요한 실행** ⚠️

#### 로그 증거

**모든 질문에서 동일**:
```log
11:09:38 - [AnalysisTeam] LLM selected tools: ['contract_analysis']
11:09:38 - [AnalysisTeam] Logged execution results: success=True

# 하지만 실제로 하는 일은?
- contract_analysis: 계약서 분석 도구
- 질문: "공인중개사의 금지행위는?"
- → 계약서 없는데 계약서 분석 도구 호출?
```

#### 분석 에이전트가 생성한 결과
```log
11:09:50 - LLM Insight Generation: 3 insights generated
11:09:50 - Aggregated analysis: 2649 bytes

# 하지만 검색 결과와 중복
11:09:53 - Aggregated search: 8988 bytes (이미 충분한 정보)
```

---

## 🔍 근본 원인 분석

### 원인 1: Step 번호와 실행 순서 불일치

**가설**:
```python
# planning_agent에서 생성한 순서
execution_plan = {
    "steps": [
        {"step_id": "step_0", "team": "search_team"},
        {"step_id": "step_1", "team": "analysis_team"}
    ]
}

# 하지만 team_supervisor에서 실행 시
# step_1이 먼저, step_0이 나중에?
```

**확인 필요**:
- `planning_agent.py`: 어떻게 step_id 할당?
- `team_supervisor.py`: 어떤 순서로 step 실행?

### 원인 2: Agent Selection 프롬프트 문제

**가설**:
```
Intent Analysis 프롬프트: "검색으로 충분한가?"
→ "충분함" 판단

Agent Selection 프롬프트: "어떤 에이전트 필요?"
→ "검색 + 분석" 선택

→ 두 프롬프트가 상충!
```

**확인 필요**:
- `intent_analysis.txt`: 어떤 가이드?
- `agent_selection.txt`: 어떤 기준?

---

## 📊 성능 영향

### 현재 상황 (3개 질문 평균)
```
Intent Analysis: 3초
Agent Selection: 4초
Analysis 실행: 13초
Search 실행: 3초
Response 생성: 7초
---
총 소요 시간: 30초
```

### 개선 시 (검색만 사용)
```
Intent Analysis: 3초
Search 실행: 3초
Response 생성: 7초
---
총 소요 시간: 13초 (17초 단축!)
```

**개선 효과**: 56% 시간 단축

---

## 🔧 해결 방안

### 해결책 1: Step 실행 순서 수정 (필수)

**위치**: `team_supervisor.py`

**현재 (추정)**:
```python
# 역순으로 실행?
for step in reversed(execution_plan["steps"]):
    execute_team(step["team"])
```

**수정**:
```python
# 정순으로 실행
for step in execution_plan["steps"]:
    execute_team(step["team"])
```

### 해결책 2: Agent Selection 로직 개선 (권장)

**위치**: `planning_agent.py`

**Option A: Intent 결과 반영**
```python
# Intent가 "검색만 충분"이면
if intent_result["reasoning"].contains("검색만으로 충분"):
    # Agent Selection 건너뛰고
    return ["search_team"]
```

**Option B: Agent Selection 프롬프트 수정**
```
Intent Analysis 결과를 고려하라:
- Intent reasoning: "{intent_reasoning}"
- Intent가 "검색 충분"이면 search_team만 선택
- Intent가 "분석 필요"이면 analysis_team 추가
```

### 해결책 3: Analysis 조건부 실행 (선택)

**조건**:
```python
# 분석 에이전트는 이런 경우만 실행
if any([
    "계약서" in query,
    "분석" in query,
    "비교" in query,
    "계산" in query,
    has_contract_data(state)
]):
    use_analysis_team = True
else:
    use_analysis_team = False
```

---

## 🎯 우선순위

| 해결책 | 우선순위 | 예상 시간 | 효과 |
|--------|---------|-----------|------|
| Step 순서 수정 | **HIGH** | 10분 | 의존성 해결 |
| Agent Selection 개선 | **HIGH** | 30분 | 56% 시간 단축 |
| Analysis 조건부 실행 | MEDIUM | 20분 | 추가 최적화 |

---

## 📋 확인 필요 사항

### 코드 확인
1. **planning_agent.py**
   - `create_execution_plan()` 메서드
   - step_id 할당 로직
   - Agent Selection 로직

2. **team_supervisor.py**
   - `execute_node()` 메서드
   - step 실행 순서
   - 왜 step_1이 먼저 실행되는지

### 프롬프트 확인
1. **intent_analysis.txt**
   - "검색만 충분" 판단 기준

2. **agent_selection.txt**
   - 에이전트 선택 기준
   - Intent 결과 반영 여부

---

## 🔍 삭제 오류 관련

**현재 로그**: 삭제 작업 로그가 포함되지 않음

**필요 정보**:
- 삭제 시도 시각
- 삭제 대상 (session_id)
- 오류 메시지
- Stack trace

삭제 관련 로그를 제공해주시면 분석하겠습니다.

---

**작성 완료**: 2025-10-21
**다음 단계**: planning_agent.py와 team_supervisor.py 코드 확인