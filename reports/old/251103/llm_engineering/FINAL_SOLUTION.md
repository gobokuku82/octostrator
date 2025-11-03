# 최종 해결책: Agent 간 정보 전달 강화

**작성일**: 2025-10-14
**버전**: Final v1.0
**상태**: 구현 준비 완료

---

## 📋 목차

1. [문제 재정의](#문제-재정의)
2. [현재 코드 분석](#현재-코드-분석)
3. [핵심 문제점](#핵심-문제점)
4. [해결 방안](#해결-방안)
5. [구현 계획](#구현-계획)
6. [예상 효과](#예상-효과)

---

## 🎯 문제 재정의

### ✅ 올바른 이해

1. **SearchExecutor는 Agent다**
   - LLM을 사용하여 **자율적으로 결정**해야 함
   - 키워드 추출, 도구 선택은 Agent의 **정당한 역할**

2. **Agent vs Tool**
   ```
   Agent = 생각하고 결정하는 주체 (LLM 사용)
   Tool  = 시키는 대로 실행하는 도구 (LLM 사용 안 함)

   SearchExecutor = Agent ✅
   legal_search_tool = Tool ✅
   ```

3. **실제 문제**
   - SearchExecutor가 LLM을 사용하는 것은 **올바름** ✅
   - 문제는 **PlanningAgent의 분석 결과가 SearchExecutor에 전달되지 않음** ❌
   - 결과: **중복 분석** (Planning 분석 → Search 재분석)

---

## 🔍 현재 코드 분석

### 1. PlanningAgent의 의도 분석

**파일**: `planning_agent.py`

**Line 183-223**: `_analyze_with_llm()`
```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    """LLM을 사용한 의도 분석"""
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={"query": query},
        temperature=0.0,
        max_tokens=500
    )

    # ✅ 키워드 추출됨
    return IntentResult(
        intent_type=intent_type,
        confidence=result.get("confidence", 0.5),
        keywords=result.get("keywords", []),  # ← 이미 추출됨!
        reasoning=result.get("reasoning", ""),
        entities=result.get("entities", {}),   # ← 엔티티도 추출됨!
        suggested_agents=suggested_agents,
        fallback=False
    )
```

**출력 예시**:
```python
IntentResult {
    intent_type: "LEGAL_CONSULT",
    confidence: 0.95,
    keywords: ["전세금", "인상", "5%", "가능"],  # ← Planning이 추출
    entities: {"percentage": "5%", "type": "전세금"},
    suggested_agents: ["search_team"]
}
```

### 2. SearchExecutor의 키워드 추출

**파일**: `search_executor.py`

**Line 150-173**: `prepare_search_node()`
```python
async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
    """검색 준비 노드"""
    # ❌ 키워드가 없으면 쿼리에서 추출
    if not state.get("keywords"):
        query = state.get("shared_context", {}).get("query", "")
        state["keywords"] = self._extract_keywords(query)  # ← 다시 추출!
```

**Line 187-207**: `_extract_keywords_with_llm()`
```python
def _extract_keywords_with_llm(self, query: str) -> SearchKeywords:
    """LLM을 사용한 키워드 추출"""
    result = self.llm_service.complete_json(
        prompt_name="keyword_extraction",  # ← 또 LLM 호출!
        variables={"query": query},
        temperature=0.1
    )

    return SearchKeywords(
        legal=result.get("legal", []),
        real_estate=result.get("real_estate", []),
        loan=result.get("loan", []),
        general=result.get("general", [])
    )
```

### 3. 정보 흐름 단절

**현재 흐름**:
```
1. PlanningAgent.analyze_intent(query)
   → IntentResult {
       keywords: ["전세금", "인상", "5%"],
       entities: {"percentage": "5%"}
     }

2. TeamSupervisor.execute_teams()
   → SearchExecutor.execute()

3. SearchExecutor.prepare_search_node()
   → state.get("keywords") == None  ← Planning 결과가 없음!
   → _extract_keywords_with_llm(query)  ← 다시 추출!
```

**문제**: Planning의 `IntentResult`가 Search로 전달되지 않음!

---

## ❌ 핵심 문제점

### 문제 1: State 구조에 IntentResult가 없음

**현재 `SearchTeamState`**:
```python
class SearchTeamState(TypedDict):
    # ...
    shared_context: Dict[str, Any]  # ← 여기에 query만 있음
    keywords: Optional[SearchKeywords]  # ← Planning에서 전달되지 않음
    # ...
```

**`shared_context`에 무엇이 들어있나?**
```python
{
    "query": "전세금 5% 인상이 가능한가요?",
    "session_id": "...",
    # IntentResult는 없음!
}
```

### 문제 2: TeamSupervisor가 IntentResult를 전달하지 않음

**현재 코드** (`team_supervisor.py` 추정):
```python
async def execute_teams(self, state: MainSupervisorState):
    """팀 실행"""
    # Planning 결과
    intent_result = state["planning_state"]["analyzed_intent"]

    # SearchExecutor 호출
    search_result = await self.search_executor.execute(
        shared_state=state["shared_context"],
        search_scope=["legal", "real_estate"],
        keywords=None  # ← intent_result의 키워드를 전달하지 않음!
    )
```

### 문제 3: 중복 LLM 호출

```
Planning:  LLM 호출 1회 (의도 분석 + 키워드 추출)
Search:    LLM 호출 1회 (키워드 재추출)
           LLM 호출 1회 (도구 선택)

총 3회 → 2회는 중복 가능성!
```

---

## ✅ 해결 방안

### 핵심 원칙

> **"Planning의 분석 결과를 Search에 전달하여, Search는 정제만 한다"**

1. **Planning**: 고수준 키워드 추출 (의도 파악용)
2. **Search**: Planning 키워드를 **검색 도메인에 특화된 키워드로 정제**
3. **중복 제거**: 동일한 작업을 2번 하지 않음

### 데이터 흐름 (개선)

```
1. PlanningAgent.analyze_intent(query)
   → IntentResult {
       intent_type: "LEGAL_CONSULT",
       keywords: ["전세금", "인상", "5%"],
       entities: {"percentage": "5%"}
     }

2. TeamSupervisor.execute_teams()
   → SearchExecutor.execute(
       shared_state=...,
       intent_result=IntentResult  ← 전달!
     )

3. SearchExecutor.prepare_search_node()
   → state.get("intent_result") != None  ← 있음!
   → _refine_keywords(  ← 새로 추출 X, 정제 O
       base_keywords=intent_result.keywords,
       query=query
     )
```

---

## 🚀 구현 계획

### Phase 1: State 구조 확장 (1일)

#### 1.1 SearchTeamState에 intent_result 추가

**파일**: `separated_states.py`

**수정**:
```python
class SearchTeamState(TypedDict):
    """검색 팀 전용 State"""
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # ✨ NEW: Planning의 의도 분석 결과
    intent_result: Optional[Dict[str, Any]]  # IntentResult를 Dict로 전달

    # Search specific
    keywords: Optional[SearchKeywords]
    search_scope: List[str]
    # ...
```

#### 1.2 TeamSupervisor에서 intent_result 전달

**파일**: `team_supervisor.py`

**수정**:
```python
async def execute_teams(self, state: MainSupervisorState):
    """팀 실행"""
    # Planning 결과 가져오기
    planning_state = state.get("planning_state", {})
    intent_result = planning_state.get("analyzed_intent", {})

    # Search 팀 실행
    if "search_team" in selected_teams:
        search_result = await self.search_executor.execute(
            shared_state=shared_context,
            search_scope=search_scope,
            keywords=None,  # 키워드는 intent_result에 포함
            intent_result=intent_result  # ✨ NEW: 전달!
        )
```

#### 1.3 SearchExecutor.execute()에 intent_result 파라미터 추가

**파일**: `search_executor.py`

**Line 460-509**: `execute()` 메서드 수정

**현재**:
```python
async def execute(
    self,
    shared_state: SharedState,
    search_scope: Optional[List[str]] = None,
    keywords: Optional[Dict] = None
) -> SearchTeamState:
```

**수정**:
```python
async def execute(
    self,
    shared_state: SharedState,
    search_scope: Optional[List[str]] = None,
    keywords: Optional[Dict] = None,
    intent_result: Optional[Dict[str, Any]] = None  # ✨ NEW
) -> SearchTeamState:
    """
    SearchTeam 실행

    Args:
        shared_state: 공유 상태
        search_scope: 검색 범위
        keywords: 검색 키워드
        intent_result: Planning의 의도 분석 결과 ✨ NEW

    Returns:
        검색 팀 상태
    """
    # 초기 상태 생성
    initial_state = SearchTeamState(
        team_name=self.team_name,
        status="pending",
        shared_context=shared_state,
        intent_result=intent_result,  # ✨ NEW: State에 포함
        keywords=keywords or SearchKeywords(...),
        # ...
    )

    # 서브그래프 실행
    final_state = await self.app.ainvoke(initial_state)
    return final_state
```

---

### Phase 2: 키워드 정제 로직 구현 (1-2일)

#### 2.1 prepare_search_node() 수정

**파일**: `search_executor.py`

**Line 150-173**: 기존 `prepare_search_node()`

**수정**:
```python
async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
    """
    검색 준비 노드
    키워드 정제 및 검색 범위 설정
    """
    logger.info("[SearchTeam] Preparing search")

    # 초기화
    state["team_name"] = self.team_name
    state["status"] = "in_progress"
    state["start_time"] = datetime.now()
    state["search_progress"] = {}

    # ✨ NEW: Intent 결과 확인
    intent_result = state.get("intent_result")

    # 키워드 처리
    if not state.get("keywords"):
        query = state.get("shared_context", {}).get("query", "")

        if intent_result and intent_result.get("keywords"):
            # ✅ Planning의 키워드가 있으면 정제
            logger.info(f"[SearchTeam] Refining keywords from Planning: {intent_result['keywords']}")
            state["keywords"] = await self._refine_keywords_from_intent(
                query=query,
                intent_result=intent_result
            )
        else:
            # ⚠️ Planning 키워드가 없으면 추출 (fallback)
            logger.warning("[SearchTeam] No keywords from Planning, extracting from query")
            state["keywords"] = self._extract_keywords(query)

    # 검색 범위 결정
    if not state.get("search_scope"):
        state["search_scope"] = self._determine_search_scope(state["keywords"])

    logger.info(f"[SearchTeam] Search scope: {state['search_scope']}")
    return state
```

#### 2.2 새 메서드 추가: _refine_keywords_from_intent()

**파일**: `search_executor.py`

**새로 추가**:
```python
async def _refine_keywords_from_intent(
    self,
    query: str,
    intent_result: Dict[str, Any]
) -> SearchKeywords:
    """
    Planning의 키워드를 검색 도메인에 특화된 키워드로 정제

    ✅ 핵심: 새로 추출하지 않고, 기존 키워드를 검색용으로 변환

    Args:
        query: 원본 질문
        intent_result: Planning의 의도 분석 결과
            {
                "intent_type": "LEGAL_CONSULT",
                "keywords": ["전세금", "인상", "5%"],
                "entities": {"percentage": "5%", "type": "전세금"},
                "confidence": 0.95
            }

    Returns:
        SearchKeywords {
            legal: ["임대차보호법", "전세금 인상", "5% 상한", "제7조"],
            real_estate: [],
            loan: [],
            general: ["5%"]
        }
    """
    if not self.llm_service:
        logger.warning("LLM service not available, using simple mapping")
        return self._simple_keyword_mapping(intent_result)

    try:
        base_keywords = intent_result.get("keywords", [])
        intent_type = intent_result.get("intent_type", "UNCLEAR")
        entities = intent_result.get("entities", {})

        # LLM 호출: 키워드 정제 (추출 X)
        result = await self.llm_service.complete_json_async(
            prompt_name="keyword_refinement_for_search",  # ✨ 새 프롬프트
            variables={
                "query": query,
                "base_keywords": ", ".join(base_keywords),
                "intent_type": intent_type,
                "entities": json.dumps(entities, ensure_ascii=False)
            },
            temperature=0.1
        )

        logger.info(f"[SearchTeam] Keywords refined: {result}")

        return SearchKeywords(
            legal=result.get("legal", []),
            real_estate=result.get("real_estate", []),
            loan=result.get("loan", []),
            general=result.get("general", [])
        )

    except Exception as e:
        logger.error(f"Keyword refinement failed: {e}")
        # Fallback: 간단한 매핑
        return self._simple_keyword_mapping(intent_result)

def _simple_keyword_mapping(self, intent_result: Dict[str, Any]) -> SearchKeywords:
    """
    간단한 규칙 기반 키워드 매핑 (LLM 실패 시 fallback)
    """
    base_keywords = intent_result.get("keywords", [])
    intent_type = intent_result.get("intent_type", "UNCLEAR")

    legal_keywords = []
    real_estate_keywords = []
    loan_keywords = []
    general_keywords = base_keywords.copy()

    # Intent 기반 분류
    if intent_type == "LEGAL_CONSULT":
        legal_keywords = base_keywords
    elif intent_type == "MARKET_INQUIRY":
        real_estate_keywords = base_keywords
    elif intent_type == "LOAN_CONSULT":
        loan_keywords = base_keywords
    else:
        # COMPREHENSIVE나 UNCLEAR: 모두에 포함
        legal_keywords = base_keywords
        real_estate_keywords = base_keywords
        loan_keywords = base_keywords

    return SearchKeywords(
        legal=legal_keywords,
        real_estate=real_estate_keywords,
        loan=loan_keywords,
        general=general_keywords
    )
```

---

### Phase 3: 새 프롬프트 추가 (1일)

#### 3.1 keyword_refinement_for_search.txt 생성

**경로**: `prompts/execution/keyword_refinement_for_search.txt`

**내용**:
```
당신은 검색 키워드 정제 전문가입니다.
Planning Agent가 추출한 고수준 키워드를 받아서,
검색 실행에 최적화된 구체적인 키워드로 변환하세요.

## 입력 정보

### 원본 질문
{query}

### Planning Agent의 분석 결과
- 의도: {intent_type}
- 기본 키워드: {base_keywords}
- 엔티티: {entities}

## 키워드 정제 가이드

### 1. 정제의 목적
- **새로 추출하지 않습니다** (Planning이 이미 추출함)
- Planning의 키워드를 **검색 도메인에 특화된 용어로 확장/변환**
- 검색 효율을 높이기 위한 **관련 용어 추가**

### 2. Intent별 정제 전략

#### LEGAL_CONSULT (법률 상담)
- 기본 키워드 → 법률 용어로 변환
- 예: "전세금 인상" → ["임대차보호법", "전세금 인상", "5% 상한", "제7조", "차임증감청구권"]
- 관련 법률명, 조항, 법적 용어 추가

#### MARKET_INQUIRY (시세 조회)
- 기본 키워드 → 부동산 시장 용어로 변환
- 예: "강남 아파트" → ["강남구", "아파트", "매매가", "전세가", "시세", "실거래가"]
- 지역명, 물건 유형, 가격 관련 용어 추가

#### LOAN_CONSULT (대출 상담)
- 기본 키워드 → 대출 상품 용어로 변환
- 예: "주택 대출" → ["주택담보대출", "전세자금대출", "금리", "LTV", "DTI", "한도"]
- 대출 상품명, 조건, 규제 용어 추가

### 3. 출력 형식

**카테고리별 분류**:
- `legal`: 법률 검색용 키워드
- `real_estate`: 부동산 시세/매물 검색용 키워드
- `loan`: 대출 상품 검색용 키워드
- `general`: 일반 키워드 (숫자, 날짜 등)

## 예시

### 예시 1
**입력**:
- 질문: "전세금 5% 인상이 가능한가요?"
- Intent: LEGAL_CONSULT
- 기본 키워드: ["전세금", "인상", "5%", "가능"]
- 엔티티: {"percentage": "5%", "type": "전세금"}

**출력**:
```json
{
  "legal": [
    "임대차보호법",
    "전세금 인상",
    "5% 상한",
    "제7조",
    "차임 증감청구권",
    "보증금 증액"
  ],
  "real_estate": [],
  "loan": [],
  "general": ["5%"]
}
```

### 예시 2
**입력**:
- 질문: "강남구 아파트 시세는 얼마인가요?"
- Intent: MARKET_INQUIRY
- 기본 키워드: ["강남구", "아파트", "시세"]
- 엔티티: {"region": "강남구", "property_type": "아파트"}

**출력**:
```json
{
  "legal": [],
  "real_estate": [
    "강남구",
    "아파트",
    "시세",
    "매매가",
    "전세가",
    "실거래가",
    "평균 가격",
    "가격 동향"
  ],
  "loan": [],
  "general": ["강남구", "아파트"]
}
```

### 예시 3
**입력**:
- 질문: "서초동 전세가 확인하고 법적으로 문제없는지도 봐줘"
- Intent: COMPREHENSIVE
- 기본 키워드: ["서초동", "전세가", "법적", "문제"]
- 엔티티: {"region": "서초동", "type": "전세"}

**출력**:
```json
{
  "legal": [
    "임대차보호법",
    "전세 계약",
    "법적 권리",
    "대항력",
    "확정일자",
    "우선변제권"
  ],
  "real_estate": [
    "서초동",
    "전세",
    "전세가",
    "시세",
    "전세 시장"
  ],
  "loan": [],
  "general": ["서초동", "전세"]
}
```

## 중요 원칙

1. **기본 키워드를 반드시 포함**: Planning이 추출한 키워드를 제거하지 마세요
2. **Intent에 맞게 분류**: 각 카테고리에 적절한 키워드만 배치
3. **검색 효율성 우선**: 너무 많은 키워드는 오히려 역효과
4. **도메인 용어 사용**: 일반 용어를 전문 용어로 변환

JSON 형식으로 출력하세요.
```

---

### Phase 4: 도구 선택 개선 (1일)

#### 4.1 _select_tools_with_llm() 수정

**파일**: `search_executor.py`

**Line 309-376**: 기존 `_select_tools_with_llm()`

**수정**:
```python
async def _select_tools_with_llm(
    self,
    query: str,
    keywords: SearchKeywords = None,
    intent_result: Optional[Dict[str, Any]] = None  # ✨ NEW
) -> Dict[str, Any]:
    """
    LLM을 사용한 tool 선택

    Args:
        query: 사용자 쿼리
        keywords: 정제된 키워드
        intent_result: Planning의 의도 분석 결과 ✨ NEW

    Returns:
        {
            "selected_tools": ["legal_search", "market_data"],
            "reasoning": "...",
            "confidence": 0.9
        }
    """
    if not self.llm_service:
        logger.warning("LLM service not available, using fallback")
        return self._select_tools_with_fallback(keywords=keywords, query=query)

    try:
        # 사용 가능한 도구 정보 수집
        available_tools = self._get_available_tools()

        # ✨ NEW: Intent 정보 포함
        intent_type = intent_result.get("intent_type", "UNCLEAR") if intent_result else "UNCLEAR"
        intent_confidence = intent_result.get("confidence", 0.0) if intent_result else 0.0

        result = await self.llm_service.complete_json_async(
            prompt_name="tool_selection_search",
            variables={
                "query": query,
                "intent_type": intent_type,  # ✨ NEW
                "intent_confidence": f"{intent_confidence:.0%}",  # ✨ NEW
                "keywords": json.dumps(keywords, ensure_ascii=False) if keywords else "{}",  # ✨ NEW
                "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
            },
            temperature=0.1
        )

        logger.info(f"LLM Tool Selection: {result}")

        selected_tools = result.get("selected_tools", [])
        reasoning = result.get("reasoning", "")
        confidence = result.get("confidence", 0.0)

        # Decision Logger에 기록
        decision_id = None
        if self.decision_logger:
            try:
                decision_id = self.decision_logger.log_tool_decision(
                    agent_type="search",
                    query=query,
                    available_tools=available_tools,
                    selected_tools=selected_tools,
                    reasoning=reasoning,
                    confidence=confidence,
                    intent_info=intent_result  # ✨ NEW: Intent 정보도 로깅
                )
            except Exception as e:
                logger.warning(f"Failed to log tool decision: {e}")

        return {
            "selected_tools": selected_tools,
            "reasoning": reasoning,
            "confidence": confidence,
            "decision_id": decision_id
        }

    except Exception as e:
        logger.error(f"LLM tool selection failed: {e}")
        return self._select_tools_with_fallback(keywords=keywords, query=query)
```

#### 4.2 execute_search_node() 수정

**파일**: `search_executor.py`

**Line 453-509**: `execute_search_node()`

**수정**:
```python
async def execute_search_node(self, state: SearchTeamState) -> SearchTeamState:
    """검색 실행 노드"""
    logger.info("[SearchTeam] Executing searches")

    import time
    start_time = time.time()

    search_scope = state.get("search_scope", [])
    keywords = state.get("keywords", {})
    shared_context = state.get("shared_context", {})
    query = shared_context.get("user_query", "") or shared_context.get("query", "")
    intent_result = state.get("intent_result")  # ✨ NEW

    # LLM 기반 도구 선택 (Intent 정보 포함)
    tool_selection = await self._select_tools_with_llm(
        query=query,
        keywords=keywords,
        intent_result=intent_result  # ✨ NEW
    )
    selected_tools = tool_selection.get("selected_tools", [])
    decision_id = tool_selection.get("decision_id")

    logger.info(
        f"[SearchTeam] LLM selected tools: {selected_tools}, "
        f"confidence: {tool_selection.get('confidence')}, "
        f"intent: {intent_result.get('intent_type') if intent_result else 'N/A'}"  # ✨ NEW
    )

    # ... 나머지 도구 실행 로직은 동일 ...
```

---

### Phase 5: 프롬프트 개선 (1일)

#### 5.1 tool_selection_search.txt 업데이트

**경로**: `prompts/execution/tool_selection_search.txt`

**기존 내용에 Intent 정보 추가**:
```
당신은 검색 도구 선택 전문가입니다.
사용자 질문에 답하기 위해 필요한 검색 도구를 선택하세요.

## 입력 정보

### 사용자 질문
{query}

### Planning Agent의 분석
- 의도: {intent_type}
- 신뢰도: {intent_confidence}

### 정제된 키워드
{keywords}

### 사용 가능한 도구
{available_tools}

## 도구 선택 전략

### 1. Intent 기반 우선 선택
- **LEGAL_CONSULT** → legal_search 필수
- **MARKET_INQUIRY** → market_data, real_estate_search
- **LOAN_CONSULT** → loan_data 필수
- **COMPREHENSIVE** → 여러 도구 조합

### 2. 키워드 기반 보조 선택
- `legal` 카테고리에 키워드 많음 → legal_search 추가
- `real_estate` 카테고리에 키워드 많음 → market_data, real_estate_search 추가
- `loan` 카테고리에 키워드 많음 → loan_data 추가

### 3. 최소 필요 원칙
- 질문에 직접 답하기 위해 **반드시 필요한 도구만** 선택
- 1-3개 도구 권장
- 불필요한 도구는 선택하지 않음

## 예시

### 예시 1
**입력**:
- 질문: "전세금 5% 인상이 가능한가요?"
- Intent: LEGAL_CONSULT (신뢰도: 95%)
- 키워드: {"legal": ["임대차보호법", "전세금 인상", "5% 상한"]}

**출력**:
```json
{
  "selected_tools": ["legal_search"],
  "reasoning": "법률 상담 의도이며 법률 키워드가 명확하므로 legal_search만 필요",
  "confidence": 0.95
}
```

### 예시 2
**입력**:
- 질문: "강남구 아파트 시세와 대출 한도를 알려주세요"
- Intent: COMPREHENSIVE (신뢰도: 90%)
- 키워드: {
    "real_estate": ["강남구", "아파트", "시세"],
    "loan": ["대출", "한도"]
  }

**출력**:
```json
{
  "selected_tools": ["market_data", "real_estate_search", "loan_data"],
  "reasoning": "시세 조회와 대출 정보 모두 필요하므로 3개 도구 선택",
  "confidence": 0.90
}
```

JSON 형식으로 출력하세요.
```

---

### Phase 6: 테스트 및 검증 (2일)

#### 6.1 단위 테스트

**파일**: `tests/test_search_executor_with_intent.py` (신규 생성)

```python
import pytest
import asyncio
from app.service_agent.execution_agents.search_executor import SearchExecutor
from app.service_agent.foundation.separated_states import SearchTeamState, SharedState

@pytest.mark.asyncio
async def test_keyword_refinement_with_intent():
    """Intent 정보를 받아 키워드 정제하는지 테스트"""

    executor = SearchExecutor()

    # Planning의 Intent 결과
    intent_result = {
        "intent_type": "LEGAL_CONSULT",
        "keywords": ["전세금", "인상", "5%"],
        "entities": {"percentage": "5%", "type": "전세금"},
        "confidence": 0.95
    }

    # 키워드 정제
    refined_keywords = await executor._refine_keywords_from_intent(
        query="전세금 5% 인상이 가능한가요?",
        intent_result=intent_result
    )

    # 검증
    assert "legal" in refined_keywords
    assert len(refined_keywords["legal"]) > 0
    assert any("임대차보호법" in kw or "전세금" in kw for kw in refined_keywords["legal"])

    print(f"✅ Refined keywords: {refined_keywords}")

@pytest.mark.asyncio
async def test_no_duplicate_llm_calls():
    """중복 LLM 호출이 없는지 테스트"""

    from unittest.mock import Mock, AsyncMock

    executor = SearchExecutor()

    # LLM Mock (호출 횟수 추적)
    llm_mock = Mock()
    llm_mock.complete_json_async = AsyncMock(return_value={
        "legal": ["임대차보호법", "전세금"],
        "real_estate": [],
        "loan": [],
        "general": ["5%"]
    })
    executor.llm_service = llm_mock

    # Intent 결과가 있을 때
    intent_result = {
        "intent_type": "LEGAL_CONSULT",
        "keywords": ["전세금", "인상"],
        "confidence": 0.95
    }

    # 키워드 정제 실행
    await executor._refine_keywords_from_intent(
        query="전세금 5% 인상이 가능한가요?",
        intent_result=intent_result
    )

    # LLM 호출 횟수 확인 (1회만 호출되어야 함)
    assert llm_mock.complete_json_async.call_count == 1

    # 호출된 프롬프트 확인
    call_args = llm_mock.complete_json_async.call_args
    assert call_args[1]["prompt_name"] == "keyword_refinement_for_search"

    print(f"✅ LLM called {llm_mock.complete_json_async.call_count} time(s)")

@pytest.mark.asyncio
async def test_full_flow_with_intent():
    """전체 흐름 테스트 (Planning → Search)"""

    executor = SearchExecutor()

    # Planning 결과 시뮬레이션
    intent_result = {
        "intent_type": "LEGAL_CONSULT",
        "keywords": ["전세금", "인상", "5%"],
        "entities": {"percentage": "5%"},
        "confidence": 0.95
    }

    # Shared state 생성
    shared_state = {
        "query": "전세금 5% 인상이 가능한가요?",
        "session_id": "test_session",
        "user_id": None,
        "timestamp": "2025-10-14T10:00:00",
        "language": "ko",
        "status": "processing",
        "error_message": None
    }

    # SearchExecutor 실행 (Intent 포함)
    result = await executor.execute(
        shared_state=shared_state,
        search_scope=["legal"],
        keywords=None,  # Planning이 제공한 키워드 사용
        intent_result=intent_result  # ✨ Intent 전달
    )

    # 검증
    assert result["status"] in ["completed", "success"]
    assert result.get("intent_result") is not None
    assert result.get("keywords") is not None

    print(f"✅ Full flow completed: {result['status']}")
    print(f"   Keywords used: {result.get('keywords')}")
```

#### 6.2 통합 테스트

**파일**: `tests/test_planning_to_search_integration.py` (신규 생성)

```python
import pytest
import asyncio
from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.execution_agents.search_executor import SearchExecutor

@pytest.mark.asyncio
async def test_planning_to_search_information_flow():
    """Planning → Search 정보 전달 통합 테스트"""

    # 1. PlanningAgent로 의도 분석
    planning_agent = PlanningAgent()
    query = "전세금 5% 인상이 가능한가요?"

    intent_result = await planning_agent.analyze_intent(query)

    print(f"\n=== Planning 결과 ===")
    print(f"Intent: {intent_result.intent_type.value}")
    print(f"Confidence: {intent_result.confidence}")
    print(f"Keywords: {intent_result.keywords}")
    print(f"Entities: {intent_result.entities}")

    # 2. SearchExecutor로 Intent 전달
    search_executor = SearchExecutor()

    shared_state = {
        "query": query,
        "session_id": "test_integration",
        "user_id": None,
        "timestamp": "2025-10-14T10:00:00",
        "language": "ko",
        "status": "processing",
        "error_message": None
    }

    # Intent 결과를 Dict로 변환
    intent_dict = {
        "intent_type": intent_result.intent_type.value,
        "keywords": intent_result.keywords,
        "entities": intent_result.entities,
        "confidence": intent_result.confidence
    }

    search_result = await search_executor.execute(
        shared_state=shared_state,
        intent_result=intent_dict  # ✨ 전달!
    )

    print(f"\n=== Search 결과 ===")
    print(f"Status: {search_result['status']}")
    print(f"Keywords refined: {search_result.get('keywords')}")
    print(f"Tools used: {search_result.get('sources_used')}")

    # 검증
    assert intent_result.keywords is not None
    assert len(intent_result.keywords) > 0
    assert search_result["status"] in ["completed", "success"]
    assert search_result.get("keywords") is not None

    print(f"\n✅ Information flow verified!")
```

---

## 📊 예상 효과

### 1. LLM 호출 감소

| 시나리오 | 현재 (AS-IS) | 개선 (TO-BE) | 감소율 |
|----------|-------------|--------------|--------|
| 단순 검색 (법률만) | 3회 | 2회 | **33%** |
| 복합 검색 (법률+시세) | 4회 | 3회 | **25%** |
| 종합 분석 | 5회 | 3회 | **40%** |

**절감 비용 (월간 예상)**:
- 현재: 1,000건 × 4회 = 4,000 LLM calls
- 개선: 1,000건 × 2.5회 = 2,500 LLM calls
- **절감: 1,500 calls (37.5%)**

### 2. 응답 시간 단축

| 작업 | 현재 | 개선 | 단축 |
|------|------|------|------|
| Planning 의도 분석 | 0.5초 | 0.5초 | - |
| Search 키워드 추출 | 0.5초 | **0.2초** (정제만) | 0.3초 |
| Search 도구 선택 | 0.5초 | 0.5초 | - |
| **합계** | **1.5초** | **1.2초** | **0.3초 (20%)** |

### 3. 코드 품질 개선

| 측면 | AS-IS | TO-BE |
|------|-------|-------|
| **정보 흐름** | 단절 (Planning 결과 버려짐) | 연결 (Planning → Search 전달) |
| **중복 작업** | 키워드 2번 추출 | 1번 추출 + 1번 정제 |
| **Agent 역할** | 모호 (Search가 Planning 작업 재수행) | 명확 (각자 역할 분담) |
| **컨텍스트 활용** | 없음 | Planning의 컨텍스트 활용 |

### 4. 검색 품질 향상

**개선 전**:
```
Query: "전세금 5% 인상이 가능한가요?"

Planning 키워드: ["전세금", "인상", "5%"] (버려짐)
Search 키워드:   ["전세", "임대", "보증금"] (새로 추출, 다를 수 있음)
→ Planning의 분석과 다른 키워드로 검색 가능성
```

**개선 후**:
```
Query: "전세금 5% 인상이 가능한가요?"

Planning 키워드: ["전세금", "인상", "5%"]
Search 키워드:   ["임대차보호법", "전세금 인상", "5% 상한", "제7조"]
                 (Planning 키워드 기반 정제)
→ Planning의 의도를 반영한 일관된 검색
```

---

## ✅ 체크리스트

### Phase 1: State 구조 확장
- [ ] `separated_states.py`: SearchTeamState에 `intent_result` 필드 추가
- [ ] `team_supervisor.py`: `execute_teams()`에서 intent_result 전달
- [ ] `search_executor.py`: `execute()` 메서드에 intent_result 파라미터 추가
- [ ] 단위 테스트: State 구조 변경 검증

### Phase 2: 키워드 정제 로직
- [ ] `search_executor.py`: `prepare_search_node()` 수정 (정제 로직 추가)
- [ ] `search_executor.py`: `_refine_keywords_from_intent()` 메서드 추가
- [ ] `search_executor.py`: `_simple_keyword_mapping()` 메서드 추가 (fallback)
- [ ] 단위 테스트: 키워드 정제 검증

### Phase 3: 새 프롬프트 추가
- [ ] `prompts/execution/keyword_refinement_for_search.txt` 생성
- [ ] 프롬프트 테스트 및 튜닝
- [ ] 예시 케이스 추가

### Phase 4: 도구 선택 개선
- [ ] `search_executor.py`: `_select_tools_with_llm()` 수정 (intent_result 활용)
- [ ] `search_executor.py`: `execute_search_node()` 수정 (intent_result 전달)
- [ ] 단위 테스트: 도구 선택 검증

### Phase 5: 프롬프트 개선
- [ ] `prompts/execution/tool_selection_search.txt` 업데이트
- [ ] Intent 정보 반영
- [ ] 예시 케이스 추가

### Phase 6: 테스트 및 검증
- [ ] 단위 테스트 작성 및 실행
- [ ] 통합 테스트 작성 및 실행
- [ ] E2E 테스트 (Planning → Search → Response)
- [ ] 성능 측정 (LLM 호출 횟수, 응답 시간)
- [ ] 품질 검증 (검색 결과 일관성)

---

## 📅 일정

| Phase | 작업 | 기간 | 담당 |
|-------|------|------|------|
| Phase 1 | State 구조 확장 | 1일 | Dev |
| Phase 2 | 키워드 정제 로직 | 1-2일 | Dev |
| Phase 3 | 프롬프트 추가 | 1일 | Dev |
| Phase 4 | 도구 선택 개선 | 1일 | Dev |
| Phase 5 | 프롬프트 개선 | 1일 | Dev |
| Phase 6 | 테스트 및 검증 | 2일 | QA |
| **총** | | **7-8일** | |

---

## 🔄 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2025-10-14 | 1.0 | 최종 해결책 문서 작성 | Dev Team |

---

**다음 단계**: Phase 1 구현 착수
