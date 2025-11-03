# 🐛 데이터 재사용 기능 문제 분석 보고서

**작성일**: 2025-10-22
**문제**: SearchTeam이 계속 실행되며 데이터 재사용이 작동하지 않음

---

## 🔍 1. 로그 분석

### 관찰된 현상
```
2025-10-22 15:40:04 - LLM Intent Analysis Result: {'intent': 'LEGAL_CONSULT', ..., 'reuse_previous_data': True}
2025-10-22 15:40:04 - ✅ LEGAL_CONSULT without analysis keywords → search_team only
2025-10-22 15:40:04 - [SearchTeam] Preparing search (실행됨!)
```

### 문제점
1. ✅ LLM이 `reuse_previous_data: True`로 정확히 반환
2. ❌ 데이터 재사용 로직이 실행되지 않음
3. ❌ SearchTeam이 계속 실행됨

---

## 🎯 2. 근본 원인 분석

### 코드 실행 순서 문제

**현재 구조** (team_supervisor.py):
```python
Line 210: intent_result = await self.planning_agent.analyze_intent(query, context)
Line 216-276: # 데이터 재사용 로직 (실행됨)
Line 338-361: # IRRELEVANT/UNCLEAR 조기 종료
Line 382: execution_plan = await self.planning_agent.create_execution_plan(intent_result)
Line 447-456: # SearchTeam 스킵 로직 (너무 늦음!)
```

### 핵심 문제
**데이터 재사용 판단은 Line 216-276에서 하지만, SearchTeam 스킵은 Line 447-456에서 함**
- Line 382에서 `create_execution_plan()`이 이미 SearchTeam을 포함한 계획 생성
- Line 447에서 스킵하려 해도 이미 늦음

---

## 💡 3. 해결 방안

### Option A: 실행 순서 조정 (권장)
```python
# 1. Intent 분석
intent_result = await self.planning_agent.analyze_intent(query, context)

# 2. 데이터 재사용 체크 (먼저!)
if intent_result.entities.get("reuse_previous_data"):
    # 데이터 체크 및 state["data_reused"] 설정

# 3. 실행 계획 생성 (data_reused를 고려)
if state.get("data_reused"):
    # SearchTeam을 제외한 agents로 계획 생성
    intent_result.suggested_agents = [a for a in intent_result.suggested_agents if a != "search_team"]

execution_plan = await self.planning_agent.create_execution_plan(intent_result)
```

### Option B: planning_agent에 data_reused 전달
```python
execution_plan = await self.planning_agent.create_execution_plan(
    intent_result,
    skip_search=state.get("data_reused", False)
)
```

---

## 🔧 4. 즉시 수정 방안

### 간단한 Fix: suggested_agents 수정
```python
# team_supervisor.py Line 276 이후 추가
if state.get("data_reused") and intent_result.suggested_agents:
    # SearchTeam 제거
    intent_result.suggested_agents = [
        agent for agent in intent_result.suggested_agents
        if agent != "search_team"
    ]
    logger.info(f"[TeamSupervisor] Removed search_team from suggested_agents due to data reuse")
```

---

## 📊 5. 영향 분석

### 현재 버그의 영향
- **성능**: SearchTeam이 불필요하게 실행 (3초 낭비)
- **사용자 경험**: "이전 데이터 활용" 알림이 나와도 새로 검색
- **데이터 일관성**: 이전 데이터와 새 검색 결과 혼재 가능

### 수정 후 예상 효과
- ✅ SearchTeam 스킵으로 3초 단축
- ✅ 일관된 데이터 재사용
- ✅ 서버 부하 감소

---

## 🚀 6. 구현 계획

### Step 1: 즉시 수정 (5분)
- suggested_agents에서 search_team 제거

### Step 2: 테스트 (10분)
- "방금 데이터로 분석해줘" 테스트
- 로그 확인

### Step 3: 고도화 (선택)
- planning_agent와 통합
- skip_teams 파라미터 추가

---

## 📌 7. 결론

**문제**: 실행 순서 오류로 데이터 재사용 판단이 실행 계획 생성 후에 적용됨
**해결**: suggested_agents 수정으로 SearchTeam 제외
**시간**: 15분 내 해결 가능