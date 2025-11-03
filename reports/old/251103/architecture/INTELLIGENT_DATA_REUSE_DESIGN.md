# Intelligent Data Reuse System 설계서

**작성일**: 2025-10-22
**버전**: 1.0
**시스템**: 부동산 AI 챗봇 (LangGraph 0.6)
**목표**: SearchTeam 건너뛰기를 통한 응답 시간 50% 단축

---

## 📋 목차

1. [문제 정의](#1-문제-정의)
2. [현재 시스템 분석](#2-현재-시스템-분석)
3. [설계 원칙](#3-설계-원칙)
4. [아키텍처 설계](#4-아키텍처-설계)
5. [구현 옵션 비교](#5-구현-옵션-비교)
6. [Phase별 구현 계획](#6-phase별-구현-계획)
7. [성능 예측](#7-성능-예측)
8. [리스크 분석](#8-리스크-분석)

---

## 1. 문제 정의

### 1.1 핵심 질문

> **"이전 대화에 충분한 정보가 있다면, SearchTeam을 건너뛰고 바로 AnalysisTeam을 실행할 수 있는가?"**

### 1.2 구체적 시나리오

```
대화 1: "강남구 아파트 시세 알려줘"
→ SearchTeam 실행 (MarketDataTool) → 8초 소요
→ 결과: 강남구 아파트 평균 시세 12억

대화 2: "강남구 아파트 위험도는?"
→ ❓ SearchTeam 다시 실행? (강남구 데이터 이미 있음)
→ ✅ 목표: SearchTeam 건너뛰기 → 4초로 단축

대화 3: "서초구 아파트 시세는?"
→ ✅ SearchTeam 실행 (지역이 다름)
```

### 1.3 문제의 복잡성

**단순해 보이지만 실제로는...**

1. **Intent가 다를 수 있음**
   - 대화1: `MARKET_INQUIRY` (시세)
   - 대화2: `RISK_ANALYSIS` (위험도)
   - → Intent가 달라도 같은 데이터 재사용 가능?

2. **파라미터가 미묘하게 다를 수 있음**
   - "강남구" vs "강남" → 같은가 다른가?
   - "5억 대출" vs "5.5억 대출" → 새로 검색? 재사용?

3. **데이터 신선도**
   - 시세 정보: 7일 지나면 낡은 데이터
   - 법률 정보: 30일은 괜찮음
   - → Intent별로 다른 기준 필요

---

## 2. 현재 시스템 분석

### 2.1 현재 흐름 (SYSTEM_FLOW_DIAGRAM.md 기반)

```mermaid
flowchart TD
    User([👤 사용자: "강남구 아파트 시세"])

    subgraph Planning["🧠 planning_node"]
        LoadMemory["🧠 Memory 로드<br/>(3-Tier Hybrid)"]
        ChatHistory["📜 Chat History 로드<br/>(최근 3쌍)"]
        IntentAnalysis["🤖 LLM #1: Intent 분석<br/>→ MARKET_INQUIRY"]
        CreatePlan["📋 실행 계획 생성<br/>→ [search_team, analysis_team]"]
    end

    subgraph Execute["⚙️ execute_teams_node"]
        SearchTeam["SearchTeam 실행<br/>🤖 LLM #4, #5<br/>⏱️ 8초"]
        AnalysisTeam["AnalysisTeam 실행<br/>🤖 LLM #6-#9<br/>⏱️ 7초"]
    end

    User --> Planning
    Planning --> Execute
    Execute --> Response["📝 응답 생성<br/>🤖 LLM #10"]

    style SearchTeam fill:#ffcdd2
    style AnalysisTeam fill:#c8e6c9
```

**총 소요 시간**: 약 15-20초

### 2.2 데이터 흐름 분석

#### 현재 저장되는 데이터

1. **Checkpointing (PostgreSQL)**
   - 위치: `checkpoints` 테이블 (thread_id = chat_session_id)
   - 저장 시점: 각 노드 완료 후 (planning, execute_teams, aggregate)
   - 저장 내용:
     ```python
     {
       "planning_state": {
         "analyzed_intent": {
           "intent_type": "market_inquiry",
           "confidence": 0.95,
           "keywords": ["강남구", "아파트", "시세"],
           "entities": {...}  # ⚠️ 현재는 간단한 형태만
         },
         "execution_steps": [...]
       },
       "team_results": {
         "search": {
           "market_data": [...],  # ✅ SearchTeam 결과 저장됨!
           "legal_data": [...]
         }
       },
       "end_time": "2025-10-22T10:00:00"
     }
     ```

2. **Long-term Memory (PostgreSQL)**
   - 위치: `chat_sessions.session_metadata`
   - 저장 시점: generate_response_node
   - 저장 내용:
     ```json
     {
       "summary": "강남구 아파트 시세 문의, 평균 12억",
       "intent": "market_inquiry",
       "timestamp": "2025-10-22T10:00:00"
     }
     ```

3. **Chat History (PostgreSQL)**
   - 위치: `chat_messages` 테이블
   - 저장 내용: 사용자 질문 + AI 응답 (텍스트만)

#### 현재 로딩되는 데이터

1. **planning_node에서**
   - Chat History (최근 3쌍) → Intent 분석에 사용 ✅
   - Long-term Memory (3-Tier) → 사용자 선호도 파악 ✅
   - ❌ **Checkpointing 데이터는 로드하지 않음!**

2. **execute_teams_node에서**
   - ❌ 이전 SearchTeam 결과 확인 안 함
   - ❌ 건너뛰기 로직 없음

### 2.3 핵심 발견

✅ **좋은 소식**:
- Checkpointing에 **이전 SearchTeam 결과**가 이미 저장됨!
- `checkpointer.aget(thread_id)` 로 이전 State 로드 가능
- Intent 분석 결과도 저장되어 있음

❌ **문제점**:
- 이전 데이터를 **로드만 하고 비교는 안 함**
- SearchTeam을 **무조건 실행** (건너뛰기 로직 없음)
- Entity 추출이 **부족** (Intent만 비교, 파라미터 비교 없음)

---

## 3. 설계 원칙

### 3.1 KISS (Keep It Simple, Stupid)

> **"복잡한 ML 알고리즘보다, 간단한 규칙 기반 로직으로 시작"**

**이유**:
- 80%의 케이스는 단순 규칙으로 처리 가능
- 빠른 구현 (1시간 vs 1주일)
- 디버깅 쉬움
- 예측 가능한 동작

### 3.2 Safety First

> **"잘못 건너뛰는 것보다, 불필요하게 검색하는 게 낫다"**

**False Positive (잘못 건너뛰기)** → **치명적**
- 사용자: "서초구 시세"
- 시스템: "강남구 데이터 재사용" → ❌ 잘못된 답변

**False Negative (불필요한 검색)** → **허용 가능**
- 사용자: "강남구 시세 다시 알려줘"
- 시스템: "SearchTeam 다시 실행" → ✅ 느리지만 정확함

**전략**: 엄격한 조건 설정
- 애매하면 → 검색 실행
- 확실할 때만 → 건너뛰기

### 3.3 Fail-Safe

> **"에러 발생 시 항상 안전한 경로로 복귀"**

```python
try:
    if can_skip_search():
        skip_search_team()
except Exception as e:
    logger.error(f"Skip check failed: {e}")
    # ✅ 안전하게 SearchTeam 실행
    execute_search_team()
```

### 3.4 Incremental Improvement

> **"한 번에 완벽하게 만들려 하지 말고, 점진적으로 개선"**

- **Phase 1**: 간단한 규칙 (70줄, 1시간) → 30% 개선
- **Phase 2**: 파라미터 유사도 매칭 → 50% 개선
- **Phase 3**: LLM 기반 판단 → 70% 개선
- **Phase 4**: Hybrid (규칙 + LLM) → 85% 개선

**각 Phase마다 실제 사용 데이터 수집 → 다음 Phase 설계에 반영**

---

## 4. 아키텍처 설계

### 4.1 구현 위치 분석

#### Option A: Supervisor 레벨 (planning_node)

```python
# team_supervisor.py - planning_node()

async def planning_node(self, state):
    # Intent 분석
    intent_result = await self.planning_agent.analyze_intent(query, context)

    # 🆕 건너뛰기 체크
    can_skip_search = await self._check_if_can_skip_search(
        current_intent=intent_result,
        chat_session_id=chat_session_id
    )

    if can_skip_search:
        state["search_skipped"] = True
        # SearchTeam을 execution_steps에서 제외
```

**장점**:
- ✅ 전체 흐름 제어 가능
- ✅ Checkpointing 접근 쉬움
- ✅ 모든 팀에 적용 확장 가능
- ✅ State 중앙 관리

**단점**:
- ❌ Supervisor가 복잡해짐
- ❌ SearchTeam 내부 로직과 분리됨

#### Option B: Executor 레벨 (search_executor.py)

```python
# search_executor.py - prepare_search_node()

async def prepare_search_node(self, state):
    # 🆕 건너뛰기 체크
    if self._can_reuse_previous_data(state):
        return state  # 검색 건너뛰기

    # 정상 검색 진행
    keywords = await self._extract_keywords(state)
    ...
```

**장점**:
- ✅ SearchTeam 로직과 통합
- ✅ Supervisor 단순 유지
- ✅ 팀별 독립적 최적화

**단점**:
- ❌ Checkpointing 접근 어려움 (Executor는 State만 받음)
- ❌ 전체 흐름 파악 어려움
- ❌ 다른 팀에 적용 시 중복 코드

#### Option C: Hybrid (Supervisor + Executor)

```python
# Supervisor: 건너뛰기 가능 여부 판단
async def planning_node(self, state):
    can_skip = await self._check_if_can_skip_search(...)
    state["search_skipped"] = can_skip

# Executor: 실제 건너뛰기 실행
async def prepare_search_node(self, state):
    if state.get("search_skipped"):
        return state  # 건너뛰기
```

**장점**:
- ✅ 책임 분리 (Supervisor: 판단, Executor: 실행)
- ✅ 확장성 좋음
- ✅ 테스트 쉬움

**단점**:
- ❌ 두 곳 수정 필요

### 4.2 선택: Option A (Supervisor 레벨)

**이유**:
1. Checkpointing 데이터 접근이 **필수적**
2. 전체 흐름 제어가 **중요** (SearchTeam뿐 아니라 다른 팀도 확장 가능)
3. State 중앙 관리로 **일관성** 유지
4. **Phase 1에서는 간단하게**, Phase 2에서 Executor 레벨 세부화 고려

---

### 4.3 데이터 흐름 설계

#### Phase 1: 간단한 규칙 기반

```mermaid
flowchart TD
    User([👤 대화2: "강남구 아파트 위험도"])

    subgraph Planning["🧠 planning_node"]
        ChatHistory["📜 Chat History 로드"]
        IntentAnalysis["🤖 LLM #1: Intent 분석<br/>→ RISK_ANALYSIS"]

        subgraph SkipCheck["🆕 _check_if_can_skip_search()"]
            LoadPrev["📦 이전 State 로드<br/>(checkpointer.aget)"]
            CompareIntent["1️⃣ Intent Type 비교<br/>prev: MARKET_INQUIRY<br/>curr: RISK_ANALYSIS<br/>→ ❌ 다름"]
            CompareEntities["2️⃣ Entity 비교<br/>(건너뜀)"]
            CheckFreshness["3️⃣ 신선도 체크<br/>(건너뜀)"]

            LoadPrev --> CompareIntent
            CompareIntent -->|다르면| Return_False["return False"]
        end

        CreatePlan["📋 실행 계획 생성<br/>→ [search, analysis]"]
    end

    subgraph Execute["⚙️ execute_teams_node"]
        CheckSkip{"search_skipped?"}
        SearchTeam["SearchTeam 실행"]
        SkipSearch["SearchTeam 건너뛰기"]
        AnalysisTeam["AnalysisTeam 실행"]
    end

    User --> Planning
    IntentAnalysis --> SkipCheck
    SkipCheck --> CreatePlan
    Planning --> Execute
    CheckSkip -->|False| SearchTeam
    CheckSkip -->|True| SkipSearch
    SearchTeam --> AnalysisTeam
    SkipSearch --> AnalysisTeam

    style SkipCheck fill:#e1f5fe
    style Return_False fill:#ffcdd2
    style SkipSearch fill:#c8e6c9
```

**이 케이스**: Intent가 다르므로 SearchTeam 실행 (안전)

---

#### Phase 2: 파라미터 매칭 추가

```mermaid
flowchart TD
    User([👤 대화2: "강남구 아파트 시세 다시"])

    subgraph SkipCheck["🆕 _check_if_can_skip_search()"]
        LoadPrev["📦 이전 State 로드"]
        CompareIntent["1️⃣ Intent Type 비교<br/>prev: MARKET_INQUIRY<br/>curr: MARKET_INQUIRY<br/>→ ✅ 같음"]
        CompareEntities["2️⃣ Entity 비교<br/>region: '강남구' == '강남구' ✅<br/>property_type: '아파트' == '아파트' ✅"]
        CheckFreshness["3️⃣ 신선도 체크<br/>prev_time: 2분 전<br/>max_age: 7일<br/>→ ✅ 신선함"]

        LoadPrev --> CompareIntent
        CompareIntent -->|같으면| CompareEntities
        CompareEntities -->|일치| CheckFreshness
        CheckFreshness -->|신선| Return_True["return True<br/>🎯 건너뛰기 가능!"]
    end

    style Return_True fill:#c8e6c9
```

**이 케이스**: 모든 조건 통과 → SearchTeam 건너뛰기 ✅

---

### 4.4 상태 관리 설계

#### State 확장

```python
# separated_states.py - MainSupervisorState

class MainSupervisorState(TypedDict, total=False):
    # 기존 필드들...
    query: str
    planning_state: Optional[PlanningState]
    team_results: Dict[str, Any]

    # 🆕 추가 필드
    search_skipped: bool  # SearchTeam 건너뛰기 여부
    reused_data_source: Optional[str]  # "checkpointing" or "memory"
    skip_reason: Optional[str]  # "same_intent_and_entities" or "recent_data"
```

#### PlanningState 확장 (entities 강화)

```python
# separated_states.py - PlanningState

class IntentAnalysisResult(TypedDict):
    intent_type: str
    confidence: float
    keywords: List[str]

    # 🆕 entities 강화
    entities: Dict[str, Any]  # {
    #   "region": "강남구",
    #   "property_type": "아파트",
    #   "amount": 500000000,
    #   "legal_topic": "전세금인상",
    #   "contract_type": "전세",
    #   "date": "2024년",
    #   "area": "84㎡"
    # }
```

---

## 5. 구현 옵션 비교

### 5.1 Intent Type 비교 전략

| 전략 | 설명 | 예시 | 장점 | 단점 |
|------|------|------|------|------|
| **엄격 일치** | Intent가 정확히 일치해야 재사용 | MARKET_INQUIRY만 재사용 | 안전함 | 재사용률 낮음 |
| **그룹 일치** | 관련 Intent 그룹 내에서 재사용 | MARKET_INQUIRY + RISK_ANALYSIS | 재사용률 높음 | 잘못된 데이터 위험 |
| **LLM 판단** | LLM에게 재사용 가능 여부 물어봄 | "이전 데이터 사용 가능?" | 정확함 | 느림 (LLM 호출) |

**Phase 1 선택**: 엄격 일치 (안전성 우선)

---

### 5.2 Entity 비교 전략

| 전략 | 설명 | "강남구" vs "강남" | "5억" vs "5.5억" |
|------|------|-------------------|------------------|
| **정확 일치** | 문자열 정확 비교 | ❌ 다름 | ❌ 다름 |
| **정규화 + 일치** | 정규화 후 비교 | ✅ 같음 ("강남구"로 정규화) | ❌ 다름 |
| **유사도 임계값** | 유사도 > 0.8이면 같음 | ✅ 같음 (0.9) | ⚠️ 애매 (0.7) |
| **Intent별 규칙** | Intent마다 다른 비교 규칙 | ✅ 지역: 정규화 일치 | ✅ 금액: ±20% 허용 |

**Phase 1 선택**: 정확 일치 (안전성)
**Phase 2 선택**: Intent별 규칙 (실용성)

---

### 5.3 신선도 기준

| Intent Type | 데이터 특성 | 권장 유효기간 | 이유 |
|-------------|------------|-------------|------|
| MARKET_INQUIRY | 시장 시세 | **7일** | 시세는 자주 변동 |
| LEGAL_CONSULT | 법률 정보 | **30일** | 법률은 비교적 안정적 |
| LOAN_CONSULT | 대출 금리 | **1일** | 금리는 매우 자주 변동 |
| CONTRACT_REVIEW | 계약서 검토 | **즉시** | 계약서는 매번 다름 → 재사용 불가 |
| RISK_ANALYSIS | 리스크 분석 | **7일** | 시장 데이터 기반 |

**구현**:
```python
FRESHNESS_LIMITS = {
    "market_inquiry": timedelta(days=7),
    "legal_consult": timedelta(days=30),
    "loan_consult": timedelta(days=1),
    "contract_review": timedelta(seconds=0),  # 항상 새로 검색
    "risk_analysis": timedelta(days=7),
}
```

---

## 6. Phase별 구현 계획

### Phase 1: 간단한 규칙 기반 (MVP) ⭐

**목표**: 가장 단순한 케이스만 처리 (Quick Win)

**구현 범위**:
1. Intent Type 정확 일치
2. Entity 정확 일치 (region, property_type만)
3. 간단한 신선도 체크 (시간 기반)

**코드**:
```python
# team_supervisor.py

async def _check_if_can_skip_search(
    self,
    current_intent: Dict[str, Any],
    chat_session_id: str
) -> bool:
    """Phase 1: 간단한 규칙 기반 건너뛰기 체크"""

    # Checkpointer 확인
    if not self.checkpointer or not chat_session_id:
        return False

    try:
        # 이전 State 로드
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if not prev_state or not prev_state.values:
            return False

        prev_intent = prev_state.values.get("planning_state", {}).get("analyzed_intent", {})

        # 1️⃣ Intent Type 비교 (정확 일치)
        if current_intent["intent_type"] != prev_intent.get("intent_type"):
            return False

        # 2️⃣ Entity 비교 (MARKET_INQUIRY만)
        if current_intent["intent_type"] == "market_inquiry":
            curr_entities = current_intent.get("entities", {})
            prev_entities = prev_intent.get("entities", {})

            # region 정확 일치
            if curr_entities.get("region") != prev_entities.get("region"):
                return False

            # property_type 정확 일치
            if curr_entities.get("property_type") != prev_entities.get("property_type"):
                return False

        # 3️⃣ 신선도 체크
        prev_time = prev_state.values.get("end_time")
        if prev_time:
            age = (datetime.now() - prev_time).total_seconds()
            max_age = 3600 * 24 * 7  # 7일
            if age > max_age:
                return False

        # ✅ 모든 조건 통과
        return True

    except Exception as e:
        logger.error(f"Skip check error: {e}")
        return False  # 에러 시 안전하게 검색
```

**수정 파일**:
1. `prompts/cognitive/intent_analysis.txt` (entities 추가, 10줄)
2. `team_supervisor.py` (_check_if_can_skip_search 추가, 60줄)
3. `team_supervisor.py` (planning_node 수정, 10줄)
4. `team_supervisor.py` (active_teams 필터링, 5줄)

**총 코드**: 85줄
**구현 시간**: 1시간
**예상 개선**: 30% 케이스에서 50% 시간 단축

---

### Phase 2: 파라미터 유사도 매칭

**목표**: 더 많은 케이스 처리 (실용성 향상)

**추가 구현**:
1. **정규화 매칭**
   ```python
   def normalize_region(region: str) -> str:
       """지역명 정규화"""
       # "강남" → "강남구"
       # "서초" → "서초구"
       return region.rstrip("시군구동읍면리")
   ```

2. **금액 범위 매칭**
   ```python
   def amount_within_range(curr_amt: int, prev_amt: int, threshold: float = 0.2) -> bool:
       """금액 ±20% 이내 매칭"""
       if prev_amt == 0:
           return False
       diff_ratio = abs(curr_amt - prev_amt) / prev_amt
       return diff_ratio <= threshold
   ```

3. **Intent 그룹 매칭**
   ```python
   INTENT_GROUPS = {
       "market": ["market_inquiry", "risk_analysis"],  # 같은 시장 데이터 사용
       "legal": ["legal_consult", "contract_review"],
       "loan": ["loan_consult"]
   }

   def intents_in_same_group(intent1: str, intent2: str) -> bool:
       for group in INTENT_GROUPS.values():
           if intent1 in group and intent2 in group:
               return True
       return False
   ```

**수정 파일**:
- `team_supervisor.py` (_check_if_can_skip_search 고도화, +50줄)
- `utils/entity_matcher.py` (신규 파일, 100줄)

**총 추가 코드**: 150줄
**구현 시간**: 3시간
**예상 개선**: 60% 케이스에서 50% 시간 단축

---

### Phase 3: LLM 기반 판단 (Hybrid)

**목표**: 애매한 케이스 LLM에게 물어보기

**추가 구현**:
1. **Rule-based 먼저 시도**
2. **애매하면 LLM 호출**

```python
async def _check_if_can_skip_search_advanced(
    self,
    current_intent: Dict,
    chat_session_id: str
) -> bool:
    # Phase 2 규칙 시도
    rule_result, confidence = await self._rule_based_check(current_intent, chat_session_id)

    # 확실하면 규칙 결과 사용
    if confidence > 0.9:
        return rule_result

    # 애매하면 LLM에게 물어보기
    llm_result = await self._llm_based_check(current_intent, prev_intent)
    return llm_result
```

**LLM 프롬프트**:
```
# prompts/cognitive/data_reuse_decision.txt

당신은 데이터 재사용 가능 여부를 판단하는 전문가입니다.

## 이전 질문
{prev_query}
Intent: {prev_intent}
Entities: {prev_entities}

## 현재 질문
{curr_query}
Intent: {curr_intent}
Entities: {curr_entities}

## 이전 검색 결과
{prev_search_results}

## 질문
현재 질문에 이전 검색 결과를 재사용할 수 있습니까?

**판단 기준**:
- Intent가 같은 종류인가?
- 핵심 파라미터 (지역, 금액, 주제)가 유사한가?
- 데이터가 여전히 유효한가?

**응답 형식**:
{
    "can_reuse": true/false,
    "confidence": 0.0~1.0,
    "reason": "이유 설명"
}
```

**수정 파일**:
- `team_supervisor.py` (+100줄)
- `prompts/cognitive/data_reuse_decision.txt` (신규 프롬프트)

**총 추가 코드**: 150줄
**구현 시간**: 4시간
**예상 개선**: 80% 케이스에서 50% 시간 단축
**주의**: LLM 호출 추가 (0.5초) → 여전히 이득 (8초 → 4.5초)

---

### Phase 4: 부분 재사용 (Executor 레벨)

**목표**: SearchTeam 내부 세분화

SearchTeam은 3개 도구로 구성:
- LegalSearchTool (법률 검색)
- MarketDataTool (시세 검색)
- LoanSearchTool (대출 검색)

**시나리오**:
```
대화1: "강남구 아파트 시세와 전세자금대출"
→ MarketDataTool + LoanSearchTool 실행

대화2: "강남구 아파트 법률 문제"
→ MarketDataTool 재사용, LegalSearchTool만 새로 실행
```

**구현**:
```python
# search_executor.py

async def prepare_search_node(self, state):
    # Phase 1~3: 전체 건너뛰기 체크
    if state.get("search_skipped"):
        return state

    # Phase 4: 부분 재사용 체크
    reuse_flags = await self._check_partial_reuse(state)
    # {
    #   "legal": False,  # 새로 검색
    #   "market": True,  # 재사용
    #   "loan": True     # 재사용
    # }

    # 필요한 것만 검색
    if not reuse_flags["legal"]:
        legal_results = await self.legal_tool.execute()
    else:
        legal_results = self._load_previous_legal_data()
```

**수정 파일**:
- `search_executor.py` (+150줄)
- `separated_states.py` (SearchTeamState 확장, +20줄)

**총 추가 코드**: 170줄
**구현 시간**: 6시간
**예상 개선**: 복합 질문에서 추가 20% 시간 단축

---

## 7. 성능 예측

### 7.1 케이스별 분석

| 케이스 | Phase 0 (현재) | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|--------------|---------|---------|---------|---------|
| 완전 동일 질문 | 15초 | **7초 (53%↓)** | 7초 | 7초 | 7초 |
| 같은 Intent + Entity | 15초 | **7초** | 7초 | 7초 | 7초 |
| 같은 Intent, 유사 Entity | 15초 | 15초 | **7초 (53%↓)** | 7초 | 7초 |
| 다른 Intent, 같은 데이터 | 15초 | 15초 | 15초 | **7초 (53%↓)** | 7초 |
| 복합 질문 (일부 재사용) | 15초 | 15초 | 15초 | 15초 | **11초 (27%↓)** |
| 완전 다른 질문 | 15초 | 15초 | 15초 | 15초 | 15초 |

### 7.2 실제 사용 패턴 예측

실제 부동산 상담 대화 패턴 분석:

| 패턴 | 비율 | 적용 Phase | 예상 효과 |
|------|------|-----------|----------|
| 같은 지역 반복 질문 | 40% | Phase 1 | 40% × 53% = **21% 전체 단축** |
| 유사 지역 질문 | 20% | Phase 2 | 20% × 53% = **11% 추가 단축** |
| 관련 Intent 질문 | 15% | Phase 3 | 15% × 53% = **8% 추가 단축** |
| 복합 질문 | 10% | Phase 4 | 10% × 27% = **3% 추가 단축** |
| 완전 새 질문 | 15% | - | 0% |

**총 예상 효과**:
- Phase 1: 평균 21% 시간 단축
- Phase 2: 평균 32% 시간 단축
- Phase 3: 평균 40% 시간 단축
- Phase 4: 평균 43% 시간 단축

### 7.3 비용 절감

**LLM 호출 비용** (GPT-4o-mini 기준):
- SearchTeam LLM 호출: LLM #4, #5 (2회)
- 건너뛰기 시 절감: 약 $0.001/query

**월간 절감** (10,000 queries 기준):
- Phase 1: 2,100 queries 건너뛰기 × $0.001 = **$2.1/month**
- Phase 2: 3,200 queries 건너뛰기 × $0.001 = **$3.2/month**

작은 금액이지만, 응답 시간 개선이 더 중요!

---

## 8. 리스크 분석

### 8.1 기술적 리스크

| 리스크 | 확률 | 영향 | 완화 전략 |
|--------|------|------|----------|
| **잘못된 데이터 재사용** | 중 | 🔴 높음 | - 엄격한 조건 설정<br/>- 로깅 강화<br/>- A/B 테스트 |
| **Checkpointing 실패** | 낮음 | 🟡 중간 | - Fail-safe (에러 시 검색)<br/>- try-catch 모든 곳 |
| **Entity 추출 실패** | 중 | 🟡 중간 | - LLM 프롬프트 개선<br/>- fallback (추출 실패 시 검색) |
| **신선도 기준 잘못 설정** | 중 | 🟡 중간 | - Intent별 기준 조정<br/>- 사용자 피드백 수집 |

### 8.2 사용자 경험 리스크

| 리스크 | 시나리오 | 해결책 |
|--------|---------|--------|
| **오래된 데이터** | 7일 전 시세 재사용 | - 신선도 표시: "2일 전 데이터 기반"<br/>- 재검색 옵션 제공 |
| **혼란스러운 답변** | "강남구" 물었는데 "서초구" 답변 | - 엄격한 Entity 매칭<br/>- 로그 모니터링 |
| **느린 응답 (LLM 판단)** | Phase 3에서 LLM 추가 호출 | - Rule 우선, LLM은 보조<br/>- 타임아웃 설정 |

### 8.3 모니터링 계획

**필수 로깅**:
```python
logger.info(f"🎯 SearchTeam skipped - reason: {skip_reason}")
logger.info(f"Skip check details: prev_intent={prev_intent}, curr_intent={curr_intent}")
logger.info(f"Entity match: region={region_match}, amount={amount_match}")
```

**메트릭 수집**:
- Skip 성공률 (skipped / total queries)
- False Positive 비율 (사용자 재질문 패턴 분석)
- 평균 응답 시간 (skipped vs non-skipped)

**알림 설정**:
- False Positive 의심 (같은 사용자 연속 재질문)
- Skip 비율 급변 (평소 30% → 갑자기 80%)

---

## 9. 구현 우선순위

### 권장 접근

```
Phase 1 (필수) → 사용자 피드백 수집 (2주) → Phase 2 (선택) → 평가 (1주) → Phase 3/4 결정
```

**Phase 1만 구현해도 충분할 수 있음!**
- 실제 데이터 수집 후 ROI 판단
- Phase 2~4는 필요성 검증 후 진행

### 구현 체크리스트

**Phase 1**:
- [ ] Intent Analysis 프롬프트에 entities 추가
- [ ] team_supervisor.py에 _check_if_can_skip_search() 추가
- [ ] planning_node()에 skip 로직 통합
- [ ] active_teams 필터링 추가
- [ ] 로깅 추가 (skip 여부, 이유)
- [ ] 테스트 (3개 시나리오)
- [ ] 문서화 (이 파일 업데이트)

**Phase 2** (선택적):
- [ ] entity_matcher.py 생성
- [ ] 정규화 함수 구현
- [ ] Intent 그룹 정의
- [ ] 통합 테스트 (10개 시나리오)

---

## 10. 결론

### 핵심 요약

1. **문제**: SearchTeam을 매번 실행하면 느림 (8초)
2. **해결책**: 이전 데이터 재사용 (Checkpointing 활용)
3. **접근**: 간단한 규칙부터 시작 (KISS 원칙)
4. **효과**: 평균 30%+ 케이스에서 50% 시간 단축

### 핵심 설계 결정

| 결정 사항 | 선택 | 이유 |
|----------|------|------|
| 구현 위치 | Supervisor 레벨 | Checkpointing 접근 필수 |
| Intent 비교 | Phase 1: 엄격 일치 | 안전성 우선 |
| Entity 비교 | Phase 1: 정확 일치 | 안전성 우선 |
| 신선도 기준 | Intent별 차등 | 데이터 특성 고려 |
| 에러 처리 | Fail-safe (검색 실행) | 정확성 우선 |

### Next Steps

1. ✅ **이 문서 리뷰** 받기
2. ⏩ **Phase 1 구현** (1시간)
3. 📊 **2주간 데이터 수집**
4. 📈 **효과 분석** (Skip 비율, 응답 시간, False Positive)
5. 🤔 **Phase 2 필요성 판단**

---

**작성**: Claude Code Assistant
**리뷰 필요**: ✅
**구현 시작 전 승인 필요**: ✅
