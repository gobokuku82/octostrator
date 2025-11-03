# SearchTeam 건너뛰기 - 심층 분석 및 경우의 수 비교

**작성일**: 2025-10-22
**목적**: Checkpointer 기반 데이터 재사용 로직의 모든 경우의 수 분석

---

## 📊 목차

1. [Checkpointer의 실제 데이터 구조](#1-checkpointer의-실제-데이터-구조)
2. [현재 시스템의 데이터 흐름 상세 분석](#2-현재-시스템의-데이터-흐름-상세-분석)
3. [경우의 수 전체 비교](#3-경우의-수-전체-비교)
4. [구현 방법 상세 비교](#4-구현-방법-상세-비교)
5. [데이터 재사용 전략 비교](#5-데이터-재사용-전략-비교)
6. [최종 권장사항](#6-최종-권장사항)

---

## 1. Checkpointer의 실제 데이터 구조

### 1.1 Checkpointer 작동 방식 (현재 코드 기반)

```python
# team_supervisor.py Line 1300-1311
if self.checkpointer:
    thread_id = chat_session_id if chat_session_id else session_id
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await self.app.ainvoke(initial_state, config=config)
```

**핵심**: LangGraph가 **각 노드 실행 후 자동으로** State를 저장함

### 1.2 저장되는 데이터 (Checkpoint Values)

#### PostgreSQL 테이블 구조

```sql
-- checkpoints 테이블
CREATE TABLE checkpoints (
    thread_id TEXT,           -- chat_session_id (예: "session-abc123")
    checkpoint_id TEXT,       -- 고유 체크포인트 ID
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB,         -- 실제 State 데이터!
    metadata JSONB,           -- 타임스탬프 등
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

#### checkpoint JSONB 내용 (예상 구조)

```json
{
  "v": 1,
  "id": "1ef1234...",
  "ts": "2025-10-22T10:00:00.123Z",
  "channel_values": {
    // ✅ 바로 이것! MainSupervisorState가 여기에 저장됨
    "query": "강남구 아파트 시세",
    "session_id": "ws-abc",
    "chat_session_id": "session-abc123",
    "user_id": 1,
    "current_phase": "response_generation",
    "status": "completed",

    // ✅ planning_state - Intent + Entities 전부!
    "planning_state": {
      "raw_query": "강남구 아파트 시세",
      "analyzed_intent": {
        "intent_type": "market_inquiry",
        "confidence": 0.95,
        "keywords": ["강남구", "아파트", "시세"],
        "entities": {
          "region": "강남구",
          "property_type": "아파트",
          "amount": null,
          "contract_type": null,
          "legal_topic": null
        }
      },
      "execution_steps": [...]
    },

    // ✅ team_results - SearchTeam 결과 전부!
    "team_results": {
      "search": {
        "legal_search": [...],        // 법률 검색 결과
        "real_estate_search": [       // 부동산 검색 결과
          {
            "property_id": 1,
            "name": "강남 래미안",
            "price": 1200000000,
            "region": "강남구",
            "property_type": "아파트",
            "area": 84.5
          },
          // ... 10개 결과
        ],
        "loan_search": [...]          // 대출 정보
      }
    },

    // ✅ 시간 정보
    "start_time": "2025-10-22T10:00:00",
    "end_time": "2025-10-22T10:00:15",
    "total_execution_time": 15.2
  }
}
```

### 1.3 Checkpointer.aget() 로드 방법

```python
# planning_node()에서 이전 State 로드
prev_state = await self.checkpointer.aget(
    {"configurable": {"thread_id": chat_session_id}}
)

# prev_state 구조
{
  "values": {  # ← channel_values와 동일
    "query": "...",
    "planning_state": {...},
    "team_results": {...},
    "end_time": datetime(...)
  },
  "metadata": {
    "ts": "2025-10-22T10:00:00.123Z",
    "source": "update",
    "step": 5,
    "writes": {...}
  },
  "config": {
    "configurable": {
      "thread_id": "session-abc123",
      "checkpoint_id": "1ef1234..."
    }
  }
}
```

**핵심**: `prev_state.values`에 모든 정보 포함!

---

## 2. 현재 시스템의 데이터 흐름 상세 분석

### 2.1 대화 1: 첫 번째 질문

```
User: "강남구 아파트 시세"
```

#### 흐름

1. **initialize_node** → State 초기화
   ```python
   state = {
     "query": "강남구 아파트 시세",
     "chat_session_id": "session-abc123",
     "status": "initialized",
     ...
   }
   ```
   → Checkpoint 저장 ✅

2. **planning_node** → Intent 분석
   ```python
   intent_result = {
     "intent_type": "market_inquiry",
     "entities": {"region": "강남구", "property_type": "아파트"}
   }
   state["planning_state"] = {...}
   ```
   → Checkpoint 저장 ✅

3. **execute_teams_node** → SearchTeam 실행
   ```python
   search_results = await search_executor.execute()
   state["team_results"]["search"] = {
     "real_estate_search": [10개 아파트 데이터]
   }
   ```
   → Checkpoint 저장 ✅

4. **aggregate_results_node** → 결과 집계
   → Checkpoint 저장 ✅

5. **generate_response_node** → 응답 생성
   ```python
   state["end_time"] = datetime.now()
   state["final_response"] = {...}
   ```
   → Checkpoint 저장 ✅ (최종)

#### 최종 저장된 데이터

```python
# PostgreSQL checkpoints 테이블
{
  "thread_id": "session-abc123",
  "checkpoint": {
    "channel_values": {
      "query": "강남구 아파트 시세",
      "planning_state": {
        "analyzed_intent": {
          "intent_type": "market_inquiry",
          "entities": {"region": "강남구", "property_type": "아파트"}
        }
      },
      "team_results": {
        "search": {
          "real_estate_search": [10개 데이터]  # ✅ 여기에 저장됨!
        }
      },
      "end_time": "2025-10-22T10:00:15"
    }
  }
}
```

---

### 2.2 대화 2: 같은 질문 반복 (건너뛰기 대상)

```
User: "강남구 아파트 시세 다시 알려줘"
```

#### 흐름 (건너뛰기 로직 추가 시)

1. **initialize_node** → State 초기화

2. **planning_node** → Intent 분석
   ```python
   # Intent 분석
   intent_result = {
     "intent_type": "market_inquiry",
     "entities": {"region": "강남구", "property_type": "아파트"}
   }

   # 🆕 이전 State 로드
   prev_state = await self.checkpointer.aget(
       {"configurable": {"thread_id": "session-abc123"}}
   )

   # 🆕 비교
   prev_intent = prev_state.values["planning_state"]["analyzed_intent"]

   if (intent_result.intent_type == prev_intent["intent_type"] and
       intent_result.entities["region"] == prev_intent["entities"]["region"]):

       state["search_skipped"] = True  # 🎯 건너뛰기 플래그
   ```

3. **execute_teams_node** → active_teams 필터링
   ```python
   active_teams = ["search", "analysis"]

   # 🆕 search 제거
   if state.get("search_skipped"):
       active_teams.remove("search")  # ["analysis"]만 남음

   # 🆕 이전 SearchTeam 결과 재사용
   state["team_results"]["search"] = prev_state.values["team_results"]["search"]
   ```

4. **AnalysisTeam만 실행**
   - SearchTeam 건너뜀 (8초 절약)
   - AnalysisTeam만 실행 (7초)

**총 시간**: 15초 → **7초** (53% 단축!)

---

## 3. 경우의 수 전체 비교

### 3.1 Intent Type 비교

| Case | 대화1 | 대화2 | Intent 비교 | Entity 비교 | 건너뛰기? | 이유 |
|------|-------|-------|------------|------------|-----------|------|
| 1 | "강남구 아파트 시세" | "강남구 아파트 시세 다시" | ✅ 동일 (MARKET_INQUIRY) | ✅ 동일 | **Yes** | 완전 동일 |
| 2 | "강남구 아파트 시세" | "강남구 아파트 위험도" | ❌ 다름 (MARKET_INQUIRY vs RISK_ANALYSIS) | ✅ 동일 | **No** | Intent 다름 |
| 3 | "강남구 아파트 시세" | "서초구 아파트 시세" | ✅ 동일 | ❌ 다름 (region) | **No** | Entity 다름 |
| 4 | "강남구 아파트 시세" | "강남구 오피스텔 시세" | ✅ 동일 | ❌ 다름 (property_type) | **No** | Entity 다름 |
| 5 | "강남구 아파트" (7일 전) | "강남구 아파트" (오늘) | ✅ 동일 | ✅ 동일 | **No** | 오래된 데이터 |
| 6 | "강남구 시세" | "강남 시세" | ✅ 동일 | ⚠️ 유사 (강남구 vs 강남) | **Phase 1: No, Phase 2: Yes** | 정규화 필요 |
| 7 | "5억 대출" | "5.5억 대출" | ✅ 동일 (LOAN_CONSULT) | ⚠️ 유사 (10% 차이) | **Phase 1: No, Phase 2: Yes** | 범위 허용 |

---

### 3.2 시간 흐름에 따른 경우의 수

```
Timeline: [대화1] -------- 시간 경과 -------- [대화2]
```

| 시간 간격 | Intent 동일 | Entity 동일 | 건너뛰기? | Phase 1 | Phase 2 |
|----------|------------|------------|-----------|---------|---------|
| **2분** | ✅ | ✅ | ✅ Yes | Yes | Yes |
| **1시간** | ✅ | ✅ | ✅ Yes | Yes | Yes |
| **1일** (LOAN) | ✅ | ✅ | ❌ No | No (기준: 1일) | No |
| **3일** (MARKET) | ✅ | ✅ | ✅ Yes | Yes (기준: 7일) | Yes |
| **7일** (MARKET) | ✅ | ✅ | ❌ No | 경계선 | 경계선 |
| **10일** (MARKET) | ✅ | ✅ | ❌ No | No | No |
| **5일** (LEGAL) | ✅ | ✅ | ✅ Yes | Yes (기준: 30일) | Yes |

---

### 3.3 Entity 변형 경우의 수

| 대화1 | 대화2 | 정확 일치 | 정규화 일치 | 유사도 | Phase 1 | Phase 2 | Phase 3 (LLM) |
|-------|-------|---------|-----------|--------|---------|---------|--------------|
| "강남구" | "강남구" | ✅ | ✅ | 1.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| "강남구" | "강남" | ❌ | ✅ | 0.9 | ❌ No | ✅ Yes | ✅ Yes |
| "강남구" | "강남동" | ❌ | ❌ | 0.7 | ❌ No | ❌ No | ⚠️ Maybe |
| "강남구" | "서초구" | ❌ | ❌ | 0.3 | ❌ No | ❌ No | ❌ No |
| "5억" | "5억" | ✅ | ✅ | 1.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| "5억" | "5.5억" | ❌ | ❌ | - | ❌ No | ✅ Yes (±20%) | ✅ Yes |
| "5억" | "8억" | ❌ | ❌ | - | ❌ No | ❌ No (60%↑) | ⚠️ Maybe |

---

## 4. 구현 방법 상세 비교

### Option A: planning_node에서 직접 비교 (권장 ⭐)

#### 코드 위치
```python
# team_supervisor.py - planning_node() 내부
# Line 210 직후
```

#### 코드 (30줄)
```python
# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)

# 🆕 SearchTeam 건너뛰기 체크
can_skip_search = False

if self.checkpointer and chat_session_id:
    try:
        # 이전 State 로드
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if prev_state and prev_state.values:
            prev_planning = prev_state.values.get("planning_state", {})
            prev_intent_data = prev_planning.get("analyzed_intent", {})

            # 조건 1: Intent Type 동일
            if intent_result.intent_type.value == prev_intent_data.get("intent_type"):

                # 조건 2: Entity 동일 (MARKET_INQUIRY만)
                if intent_result.intent_type.value == "market_inquiry":
                    curr_entities = intent_result.entities or {}
                    prev_entities = prev_intent_data.get("entities", {})

                    region_match = curr_entities.get("region") == prev_entities.get("region")
                    property_match = curr_entities.get("property_type") == prev_entities.get("property_type")

                    if region_match and property_match:
                        # 조건 3: 신선도 (7일)
                        prev_time = prev_state.values.get("end_time")
                        if prev_time:
                            age_seconds = (datetime.now() - prev_time).total_seconds()
                            if age_seconds < (3600 * 24 * 7):
                                can_skip_search = True
                                logger.info("🎯 SearchTeam will be skipped - reusing previous data")

    except Exception as e:
        logger.error(f"Skip check error: {e}")
        can_skip_search = False

state["search_skipped"] = can_skip_search
```

#### 장점
- ✅ **간단**: 30줄만 추가
- ✅ **빠름**: checkpointer.aget() 0.1초 미만
- ✅ **안전**: try-catch로 에러 시 fallback
- ✅ **확장 가능**: 다른 Intent 쉽게 추가

#### 단점
- ❌ planning_node가 약간 길어짐 (200줄 → 230줄)

---

### Option B: 별도 메서드 분리

#### 코드
```python
# team_supervisor.py

async def _check_if_can_skip_search(
    self,
    current_intent: Dict,
    chat_session_id: str
) -> bool:
    """SearchTeam 건너뛰기 가능 여부 체크"""

    if not self.checkpointer or not chat_session_id:
        return False

    try:
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if not prev_state or not prev_state.values:
            return False

        # 비교 로직 (위와 동일)
        ...

        return True

    except Exception as e:
        logger.error(f"Skip check error: {e}")
        return False

# planning_node()에서 호출
can_skip = await self._check_if_can_skip_search(
    current_intent={
        "intent_type": intent_result.intent_type.value,
        "entities": intent_result.entities
    },
    chat_session_id=chat_session_id
)
```

#### 장점
- ✅ **깔끔**: planning_node가 간결해짐
- ✅ **재사용 가능**: 다른 곳에서도 호출 가능
- ✅ **테스트 쉬움**: 별도 메서드 단위 테스트

#### 단점
- ❌ 약간 더 복잡 (60줄)

---

### Option C: 별도 Agent 클래스 생성 (과도함 ❌)

```python
# 새 파일: cognitive_agents/data_reuse_checker.py

class DataReuseChecker:
    def __init__(self, checkpointer):
        self.checkpointer = checkpointer

    async def can_skip_search(self, ...):
        # 100줄
        ...

# team_supervisor.py
self.data_reuse_checker = DataReuseChecker(self.checkpointer)
can_skip = await self.data_reuse_checker.can_skip_search(...)
```

#### 장점
- ✅ 완전 분리

#### 단점
- ❌ **과도한 엔지니어링**: 간단한 로직에 클래스 불필요
- ❌ 새 파일 생성 (유지보수 증가)
- ❌ 복잡도 증가

**결론**: 사용 안 함!

---

## 5. 데이터 재사용 전략 비교

### 전략 1: Intent만 비교 (가장 간단)

```python
if current_intent == prev_intent:
    skip = True
```

| 장점 | 단점 | 재사용률 |
|------|------|---------|
| 코드 5줄 | 잘못된 재사용 위험 | 50% (높음) |
| 구현 1분 | "강남구" → "서초구" 잘못 재사용 | False Positive 높음 |

**결론**: ❌ 사용 안 함 (안전하지 않음)

---

### 전략 2: Intent + Entity 정확 일치 (권장 ⭐)

```python
if (current_intent == prev_intent and
    current_entities == prev_entities):
    skip = True
```

| 장점 | 단점 | 재사용률 |
|------|------|---------|
| 안전함 | "강남" vs "강남구" 재사용 못함 | 30% (중간) |
| 코드 30줄 | 약간 보수적 | False Positive 낮음 |

**결론**: ✅ **Phase 1 권장!**

---

### 전략 3: Intent + Entity 유사도 (Phase 2)

```python
def normalize_region(region):
    return region.rstrip("시군구동")

if (current_intent == prev_intent and
    normalize_region(current_region) == normalize_region(prev_region)):
    skip = True
```

| 장점 | 단점 | 재사용률 |
|------|------|---------|
| 실용적 | 코드 60줄 | 50% (높음) |
| "강남" = "강남구" | 정규화 규칙 필요 | False Positive 약간 증가 |

**결론**: ✅ Phase 2 고려

---

### 전략 4: LLM 판단 (Phase 3)

```python
llm_decision = await llm_service.analyze(
    "이전 검색 결과 재사용 가능한가?"
)
if llm_decision == "yes":
    skip = True
```

| 장점 | 단점 | 재사용률 |
|------|------|---------|
| 매우 정확 | LLM 호출 (+0.5초) | 80% (매우 높음) |
| 애매한 케이스 처리 | 비용 증가 | False Positive 거의 없음 |

**결론**: ✅ Phase 3 고려 (실제 필요성 검증 후)

---

## 6. 최종 권장사항

### 6.1 Phase 1 구현 (지금 바로)

**방법**: Option B (별도 메서드)

**코드**:
1. `_check_if_can_skip_search()` 메서드 추가 (60줄)
2. `planning_node()`에서 호출 (10줄)
3. `active_teams` 필터링 (5줄)

**총**: 75줄, 15분 구현

**효과**:
- 30% 케이스에서 건너뛰기
- 평균 응답 시간 16% 단축 (15초 → 12.6초)

**적용 대상**:
- MARKET_INQUIRY만 (안전)
- region + property_type 정확 일치
- 7일 이내 데이터

---

### 6.2 Phase 2 고려사항 (2주 후 결정)

**추가 내용**:
- 정규화 ("강남" → "강남구")
- 금액 범위 (±20%)
- Intent 그룹 (MARKET + RISK 묶음)

**추가 코드**: 50줄

**효과**:
- 50% 케이스에서 건너뛰기
- 평균 응답 시간 27% 단축

---

### 6.3 구현 체크리스트

**Phase 1**:
- [ ] `_check_if_can_skip_search()` 메서드 작성
- [ ] `planning_node()`에 호출 로직 추가
- [ ] `active_teams` 생성 시 필터링 추가
- [ ] 로깅 추가 (skip 여부, 이유)
- [ ] 간단한 테스트 (3개 시나리오)

**테스트 시나리오**:
1. 같은 질문 반복 → 건너뛰기 확인
2. 다른 지역 질문 → 새로 검색 확인
3. Checkpointer 없을 때 → 정상 작동 확인

---

### 6.4 예상 로그

**건너뛰기 성공**:
```
[TeamSupervisor] 🎯 SearchTeam will be skipped - reusing previous data
[TeamSupervisor] Skip reason: same_intent_and_entities, age: 2.3 min
[TeamSupervisor] Active teams: ['analysis']
```

**건너뛰기 실패 (지역 다름)**:
```
[TeamSupervisor] Cannot skip search - entity mismatch
[TeamSupervisor] Region changed: 강남구 → 서초구
[TeamSupervisor] Active teams: ['search', 'analysis']
```

**건너뛰기 실패 (오래된 데이터)**:
```
[TeamSupervisor] Cannot skip search - data too old
[TeamSupervisor] Data age: 8.2 days (max: 7 days)
[TeamSupervisor] Active teams: ['search', 'analysis']
```

---

## 7. 요약 표

### 구현 비교

| 옵션 | 코드 라인 | 구현 시간 | 복잡도 | 권장도 |
|------|----------|----------|--------|--------|
| **Option A (인라인)** | 30줄 | 10분 | 낮음 | ⭐⭐⭐ |
| **Option B (메서드)** | 75줄 | 15분 | 낮음 | ⭐⭐⭐⭐⭐ (권장) |
| **Option C (클래스)** | 200줄 | 1시간 | 높음 | ⭐ (비권장) |

### 전략 비교

| 전략 | 재사용률 | 안전성 | 구현 난이도 | 권장 Phase |
|------|---------|--------|------------|-----------|
| **Intent만** | 50% | 낮음 | 매우 쉬움 | ❌ |
| **Intent + Entity 정확** | 30% | 높음 | 쉬움 | ✅ Phase 1 |
| **Intent + Entity 유사** | 50% | 중간 | 중간 | ✅ Phase 2 |
| **LLM 판단** | 80% | 매우 높음 | 어려움 | ⚠️ Phase 3 |

### 경우의 수 요약

| 케이스 | 건너뛰기 (Phase 1) | 건너뛰기 (Phase 2) |
|--------|-------------------|-------------------|
| 완전 동일 질문 | ✅ Yes | ✅ Yes |
| 같은 Intent, 다른 Entity | ❌ No | ❌ No |
| 유사 Entity ("강남" vs "강남구") | ❌ No | ✅ Yes |
| 금액 범위 내 (±20%) | ❌ No | ✅ Yes |
| 오래된 데이터 (7일 초과) | ❌ No | ❌ No |
| 다른 Intent | ❌ No | ❌ No |

---

## 8. 다음 단계

1. **이 문서 검토** ✅
2. **Phase 1 구현 승인** 받기
3. **15분 구현**
4. **2주간 실제 사용 데이터 수집**
5. **효과 측정**:
   - Skip 성공률
   - 응답 시간 단축
   - False Positive 비율
6. **Phase 2 필요성 판단**

---

**작성**: Claude Code
**목적**: 모든 경우의 수 명확히 분석하여 의사결정 지원
**다음**: Phase 1 구현 여부 결정 필요
