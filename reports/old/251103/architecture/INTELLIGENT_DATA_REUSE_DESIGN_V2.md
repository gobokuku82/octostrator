# Intelligent Data Reuse System 설계서 V2

**작성일**: 2025-10-22
**버전**: 2.0 (Checkpointer 활용 간소화 버전)
**핵심 발견**: Checkpointer가 이미 모든 데이터를 저장하고 있음! **단순 비교만 하면 됨**

---

## 🎯 핵심 인사이트

> **"Checkpointer에 이전 State가 이미 다 있는데, 왜 복잡하게 하나?"**

### 현재 시스템이 이미 가지고 있는 것

```python
# planning_node()에서 Checkpointer 로드 (Line 1295-1311)
config = {"configurable": {"thread_id": chat_session_id}}
prev_state = await self.checkpointer.aget(config)

# prev_state.values에 이미 다 있음!
{
  "planning_state": {
    "analyzed_intent": {
      "intent_type": "market_inquiry",
      "confidence": 0.95,
      "keywords": ["강남구", "아파트"],
      "entities": {"region": "강남구", "property_type": "아파트"}  # ✅ 이미 있음!
    }
  },
  "team_results": {
    "search": {  # ✅ SearchTeam 결과도 이미 저장되어 있음!
      "real_estate_results": [...],
      "legal_results": [...]
    }
  },
  "end_time": "2025-10-22T10:00:00"  # ✅ 신선도 체크용
}
```

### 우리가 해야 할 일

❌ **복잡한 작업 (필요 없음)**:
- 새로운 Agent 만들기
- 새로운 Node 추가하기
- 복잡한 유사도 알고리즘

✅ **간단한 작업 (실제 필요한 것)**:
```python
# planning_node()에 20줄만 추가
prev_state = await self.checkpointer.aget(config)  # 이미 있는 코드 활용!
current_intent = intent_result.intent_type.value
prev_intent = prev_state.values["planning_state"]["analyzed_intent"]["intent_type"]

if current_intent == prev_intent:  # 간단한 비교!
    state["search_skipped"] = True
```

---

## 📊 현재 코드 분석

### 1. Checkpointer 이미 작동 중

**파일**: `team_supervisor.py`

#### Line 1182-1186: Checkpointer 초기화
```python
self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
self.checkpointer = await self._checkpoint_cm.__aenter__()
await self.checkpointer.setup()
```
✅ **이미 작동 중!** PostgreSQL에 State 저장됨

#### Line 1295-1311: Checkpointer 사용
```python
if self.checkpointer:
    thread_id = chat_session_id if chat_session_id else session_id
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await self.app.ainvoke(initial_state, config=config)
```
✅ **이미 thread_id로 State 저장/로드 중!**

---

### 2. 이전 State 로드 방법 (매우 간단!)

```python
# planning_node() 어디든지 추가 가능
async def planning_node(self, state: MainSupervisorState):
    chat_session_id = state.get("chat_session_id")

    # 🆕 이전 State 로드 (단 3줄!)
    if self.checkpointer and chat_session_id:
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if prev_state and prev_state.values:
            # ✅ 이전 데이터 전부 사용 가능!
            prev_intent = prev_state.values.get("planning_state", {}).get("analyzed_intent", {})
            prev_search_results = prev_state.values.get("team_results", {}).get("search", {})
            prev_time = prev_state.values.get("end_time")
```

**이게 끝!** 복잡한 HistoryRetrievalAgent 필요 없음!

---

## 🔧 실제 구현 (Phase 1 - 초간단 버전)

### 수정할 파일: 단 1개!

**파일**: `team_supervisor.py`

### 수정 위치: `planning_node()` 내부

**기존 코드** (Line 210):
```python
# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)

# 🔻 여기에 20줄 추가! 🔻

# ============================================================================
# Long-term Memory 로딩 (조기 단계 - 모든 쿼리)
# ============================================================================
```

**추가할 코드** (20줄):
```python
# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)

# 🆕 ========================================================================
# SearchTeam 건너뛰기 체크 (Checkpointer 활용)
# ==========================================================================
can_skip_search = False
if self.checkpointer and chat_session_id:
    try:
        # 이전 State 로드
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if prev_state and prev_state.values:
            prev_planning = prev_state.values.get("planning_state", {})
            prev_intent = prev_planning.get("analyzed_intent", {})

            # 1️⃣ Intent Type 비교 (정확 일치)
            if intent_result.intent_type.value == prev_intent.get("intent_type"):

                # 2️⃣ 핵심 Entity 비교 (MARKET_INQUIRY만)
                if intent_result.intent_type.value == "market_inquiry":
                    curr_entities = intent_result.entities or {}
                    prev_entities = prev_intent.get("entities", {})

                    # region + property_type 일치
                    if (curr_entities.get("region") == prev_entities.get("region") and
                        curr_entities.get("property_type") == prev_entities.get("property_type")):

                        # 3️⃣ 신선도 체크 (7일 이내)
                        prev_time = prev_state.values.get("end_time")
                        if prev_time:
                            age = (datetime.now() - prev_time).total_seconds()
                            if age < (3600 * 24 * 7):  # 7일
                                can_skip_search = True
                                logger.info("🎯 SearchTeam will be skipped - reusing previous data")

                # 다른 Intent도 쉽게 추가 가능
                elif intent_result.intent_type.value == "legal_consult":
                    # LEGAL_CONSULT 로직...
                    pass

    except Exception as e:
        logger.error(f"Skip check error: {e}")
        can_skip_search = False  # 에러 시 안전하게 검색

state["search_skipped"] = can_skip_search
# 🆕 ========================================================================

# ============================================================================
# Long-term Memory 로딩 (조기 단계 - 모든 쿼리)
# ============================================================================
```

**그게 끝!**

---

### active_teams 필터링 수정 (5줄)

**기존 코드** (Line 382-388):
```python
for step in sorted_steps:
    team = step.get("team")
    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)
```

**수정 코드**:
```python
for step in sorted_steps:
    team = step.get("team")

    # 🆕 SearchTeam 건너뛰기 체크
    if team == "search" and state.get("search_skipped", False):
        logger.info("🎯 Skipping SearchTeam - using previous data")
        continue

    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)
```

---

## 📋 전체 수정 통계

| 항목 | 값 |
|------|------|
| **수정 파일** | 1개 (`team_supervisor.py`) |
| **추가 코드** | 25줄 (20줄 + 5줄) |
| **새 함수/클래스** | 0개 |
| **새 파일** | 0개 |
| **프롬프트 수정** | 0줄 (entities는 이미 있음!) |
| **구현 시간** | **10분** |

**비교**:
- V1 (이전 설계): 445줄, 7개 파일, 1주일
- V2 (현재 설계): **25줄, 1개 파일, 10분** ✅

---

## 🧪 테스트 시나리오

### Case 1: 완전 동일한 질문
```
대화1: "강남구 아파트 시세"
→ Intent: MARKET_INQUIRY
→ Entities: {region: "강남구", property_type: "아파트"}
→ SearchTeam 실행 ✅

대화2: "강남구 아파트 시세 다시"
→ Intent: MARKET_INQUIRY (같음!)
→ Entities: {region: "강남구", property_type: "아파트"} (같음!)
→ 시간: 2분 전 (신선함!)
→ SearchTeam 건너뛰기 🎯
```

### Case 2: Intent 같지만 Entity 다름
```
대화1: "강남구 아파트 시세"
대화2: "서초구 아파트 시세"
→ Intent: MARKET_INQUIRY (같음)
→ Entities: region 다름 ("강남구" ≠ "서초구")
→ SearchTeam 실행 ✅ (안전)
```

### Case 3: Intent 다름
```
대화1: "강남구 아파트 시세"
대화2: "강남구 아파트 위험도"
→ Intent 다름 (MARKET_INQUIRY ≠ RISK_ANALYSIS)
→ SearchTeam 실행 ✅ (안전)
```

### Case 4: 오래된 데이터
```
대화1: "강남구 아파트 시세" (7일 전)
대화2: "강남구 아파트 시세" (오늘)
→ 모든 조건 일치하지만, 시간 초과 (7일)
→ SearchTeam 실행 ✅ (신선한 데이터 필요)
```

---

## 🔍 왜 이렇게 간단한가?

### V1 설계의 문제 (과도한 복잡도)

```
1. HistoryRetrievalAgent 클래스 생성 (200줄)
   → ❌ 필요 없음! checkpointer.aget() 3줄이면 됨

2. 새로운 Node 추가 (history_retrieval_node)
   → ❌ 필요 없음! planning_node에서 바로 체크

3. Intent 분석 프롬프트 수정 (entities 추가)
   → ❌ 필요 없음! entities는 이미 있음!

4. Graph 구조 변경 (conditional edges 추가)
   → ❌ 필요 없음! active_teams만 필터링하면 됨
```

### V2 설계의 핵심 (Keep It Simple)

```python
# 이미 있는 것 활용:
prev_state = await self.checkpointer.aget(config)  # ← 이미 작동 중!
prev_intent = prev_state.values["planning_state"]["analyzed_intent"]

# 간단한 비교:
if current == prev:  # ← 3줄이면 끝!
    skip = True
```

---

## 📈 예상 효과

### 성능 개선

| 시나리오 | 기존 | Phase 1 | 개선율 |
|----------|------|---------|--------|
| 완전 동일 질문 (30%) | 15초 | **7초** | 53%↓ |
| 같은 Intent+Entity (20%) | 15초 | **7초** | 53%↓ |
| 다른 질문 (50%) | 15초 | 15초 | 0% |

**평균 효과**: 30% × 53% + 20% × 53% = **27% 전체 응답 시간 단축**

### 구현 리스크

| 리스크 | 확률 | 영향 | 완화 |
|--------|------|------|------|
| 잘못된 건너뛰기 | 낮음 | 높음 | 엄격한 조건 (Intent + Entity + Time) |
| Checkpointer 실패 | 낮음 | 낮음 | try-catch + fallback (검색 실행) |
| Entity 추출 실패 | 중간 | 낮음 | entities 없으면 검색 실행 |

---

## 🚀 구현 순서

### Step 1: 코드 추가 (5분)
1. `planning_node()`에 20줄 추가
2. `active_teams` 생성 부분에 5줄 추가

### Step 2: 로깅 확인 (2분)
```python
logger.info("🎯 SearchTeam will be skipped - reusing previous data")
logger.info("🎯 Skipping SearchTeam - using previous data")
```

### Step 3: 테스트 (3분)
```bash
# WebSocket으로 테스트
대화1: "강남구 아파트 시세"
대화2: "강남구 아파트 시세 다시"

# 로그 확인:
[TeamSupervisor] 🎯 SearchTeam will be skipped
[TeamSupervisor] Active teams: ['analysis']  # search 없음!
```

**총 소요 시간**: **10분**

---

## 🎨 Phase 2 (선택적 고도화)

### 현재 제한사항

1. **Intent Type 엄격 일치**
   - MARKET_INQUIRY만 MARKET_INQUIRY에 재사용
   - 개선: "MARKET_INQUIRY + RISK_ANALYSIS 묶음"

2. **Entity 정확 일치**
   - "강남구" ≠ "강남"
   - 개선: 정규화 ("강남" → "강남구")

3. **MARKET_INQUIRY만 지원**
   - 개선: LEGAL_CONSULT, LOAN_CONSULT 추가

### Phase 2 추가 코드 (50줄)

```python
# Intent 그룹 정의
INTENT_GROUPS = {
    "market": ["market_inquiry", "risk_analysis"],  # 같은 데이터 사용
    "legal": ["legal_consult", "contract_review"]
}

def intents_in_same_group(intent1, intent2):
    for group in INTENT_GROUPS.values():
        if intent1 in group and intent2 in group:
            return True
    return False

# Entity 정규화
def normalize_region(region: str) -> str:
    """강남 → 강남구"""
    if not region:
        return region
    return region.rstrip("시군구동읍면리") + "구"

# planning_node()에서 사용
if intents_in_same_group(current_intent, prev_intent):
    curr_region = normalize_region(curr_entities.get("region"))
    prev_region = normalize_region(prev_entities.get("region"))

    if curr_region == prev_region:
        can_skip = True
```

**추가 시간**: 30분
**추가 효과**: 50% 케이스에서 건너뛰기 (vs 30%)

---

## 💡 핵심 교훈

### ❌ 이전 설계 (V1)의 실수

```
"새로운 기능 = 새로운 Agent + 새로운 Node"
→ 445줄, 7개 파일, 1주일
→ 과도한 엔지니어링
```

### ✅ 올바른 설계 (V2)

```
"이미 있는 것 활용 = Checkpointer.aget()"
→ 25줄, 1개 파일, 10분
→ Keep It Simple, Stupid!
```

### 설계 원칙

1. **기존 인프라 먼저 확인**
   - Checkpointer가 이미 State 저장 중
   - 굳이 새로 만들 필요 없음

2. **최소 수정 원칙**
   - 새 파일/클래스 만들지 않기
   - 기존 함수에 10-20줄만 추가

3. **Fail-Safe 우선**
   - 에러 시 항상 안전한 경로 (검색 실행)
   - try-catch 필수

4. **점진적 개선**
   - Phase 1: 30% 효과, 10분 구현
   - Phase 2: 50% 효과, 40분 추가

---

## 📝 최종 체크리스트

**구현 전 확인**:
- [ ] Checkpointer 작동 중? (Line 1182-1186)
- [ ] chat_session_id 전달됨? (process_query_streaming)
- [ ] Intent 분석 시 entities 추출됨? (planning_agent.py)

**구현 시**:
- [ ] `planning_node()`에 20줄 추가
- [ ] `active_teams` 필터링에 5줄 추가
- [ ] 로깅 추가 (skip 여부)
- [ ] try-catch로 감싸기

**테스트**:
- [ ] 같은 질문 반복 → 건너뛰기 확인
- [ ] 다른 지역 질문 → 검색 실행 확인
- [ ] Checkpointer 없을 때 → 정상 작동 확인

---

## 🎯 결론

**V1 vs V2 비교**:

| 항목 | V1 (과도한 설계) | V2 (간소화 설계) |
|------|----------------|----------------|
| 수정 파일 | 7개 | **1개** ✅ |
| 코드 라인 | 445줄 | **25줄** ✅ |
| 구현 시간 | 1주일 | **10분** ✅ |
| 새 클래스 | HistoryRetrievalAgent | **0개** ✅ |
| 새 Node | history_retrieval_node | **0개** ✅ |
| 복잡도 | 높음 | **매우 낮음** ✅ |

**핵심 메시지**:
> **"Checkpointer가 이미 다 가지고 있다. 단순 비교만 하면 된다!"**

**Next Step**:
1. ✅ 이 설계 승인 받기
2. ⏩ 10분 구현
3. 📊 2주간 데이터 수집
4. 📈 효과 분석 후 Phase 2 결정

---

**작성**: Claude Code (Simplified Version)
**리뷰 필요**: ✅
**구현 시작 전 승인 필요**: ✅
