# Cognitive-Execution Layer 분리 구현 계획

**작성일**: 2025-10-14
**작성자**: Development Team
**상태**: 계획 단계

---

## 📋 목차

1. [현황 분석](#현황-분석)
2. [문제점](#문제점)
3. [제안하는 아키텍처](#제안하는-아키텍처)
4. [구현 계획](#구현-계획)
5. [예상 효과](#예상-효과)
6. [리스크 관리](#리스크-관리)

---

## 🔍 현황 분석

### 현재 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Team Supervisor                           │
│  - 전체 오케스트레이션                                         │
│  - _generate_llm_response() ← LLM 호출 (최종 응답 생성)      │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
┌───────▼──────────┐  ┌───────▼──────────┐
│ Cognitive Layer  │  │ Execution Layer  │
│ (계획 수립)       │  │ (실행)           │
└──────────────────┘  └──────────────────┘
```

### LLM 호출 현황

| # | 파일 | 메서드 | 목적 | 레이어 | 상태 |
|---|------|--------|------|--------|------|
| 1 | `planning_agent.py` | `_analyze_with_llm()` | 의도 분석 | Cognitive | ✅ 적절 |
| 2 | `planning_agent.py` | `_select_agents_with_llm()` | Agent 선택 | Cognitive | ✅ 적절 |
| 3 | `query_decomposer.py` | `decompose()` | 복합 질문 분해 | Cognitive | ✅ 적절 |
| 4 | **`search_executor.py`** | **`_extract_keywords_with_llm()`** | 키워드 추출 | **Execution** | ⚠️ **문제** |
| 5 | **`search_executor.py`** | **`_select_tools_with_llm()`** | 도구 선택 | **Execution** | ⚠️ **문제** |
| 6 | `analysis_executor.py` | (도구 내부) | 시장 분석 | Execution | ⚠️ **문제** |
| 7 | `analysis_executor.py` | (도구 내부) | 계약서 분석 | Execution | ⚠️ **문제** |
| 8 | `team_supervisor.py` | `generate_final_response()` | 최종 응답 생성 | Supervisor | ✅ 적절 |

### 파일 구조

```
app/service_agent/
├── cognitive_agents/
│   ├── planning_agent.py          ✅ LLM 호출 (의도 분석, Agent 선택)
│   └── query_decomposer.py        ✅ LLM 호출 (질문 분해)
│
├── execution_agents/
│   ├── search_executor.py         ⚠️ LLM 호출 (키워드 추출, 도구 선택)
│   ├── analysis_executor.py       ⚠️ LLM 호출 (도구 내부)
│   └── document_executor.py       ⚠️ LLM 호출 가능성
│
├── llm_manager/
│   ├── llm_service.py             ✅ 중앙화된 LLM 서비스
│   └── prompts/                   ✅ 프롬프트 템플릿
│
└── supervisor/
    └── team_supervisor.py         ✅ LLM 호출 (최종 응답)
```

---

## ❌ 문제점

### 1. 책임 분리 위반 (SRP Violation)

**현재 상황:**
```python
# search_executor.py (Execution Layer)
async def _extract_keywords_with_llm(self, query: str):
    """⚠️ 실행 레이어에서 인지 작업(키워드 추출) 수행"""
    result = await self.llm_service.complete_json_async(
        prompt_name="keyword_extraction",
        variables={"query": query}
    )
    return result
```

**문제점:**
- Execution Layer가 Cognitive 작업(분석, 추론)을 수행
- 역할 혼재로 인한 코드 복잡도 증가
- 테스트 어려움 (Execution 테스트 시 LLM Mock 필요)

### 2. 중복 분석 (Redundant Processing)

**중복 발생 구조:**
```
PlanningAgent (Cognitive)           SearchExecutor (Execution)
     │                                      │
     ├─ analyze_intent(query)              │
     │  └─ intent: "LEGAL_CONSULT"         │
     │     keywords: ["전세", "인상"]       │
     │                                      │
     └─ suggest_agents()                   ├─ _extract_keywords_with_llm(query) ❌
        └─ ["search_team"]                 │  └─ keywords: ["전세", "인상"] (중복!)
                                            │
                                            └─ _select_tools_with_llm(query) ❌
                                               └─ tools: ["legal_search"]
```

**비효율성:**
- Planning에서 이미 추출한 키워드를 Search에서 다시 추출
- LLM 호출 2배 → 비용 증가, 응답 시간 증가
- 결과 불일치 가능성 (Planning의 키워드 ≠ Search의 키워드)

### 3. 데이터 흐름 비일관성

**현재 (AS-IS):**
```
┌──────────┐      ┌──────────┐      ┌──────────┐
│ Planning │ ───> │  Search  │ ───> │ LLM 호출 │
│ (분석함)  │      │(재분석함!)│      │ (중복)   │
└──────────┘      └──────────┘      └──────────┘
                       ↓
                  검색 실행
```

**기대 (TO-BE):**
```
┌──────────┐      ┌──────────┐      ┌──────────┐
│ Planning │ ───> │  Search  │ ───> │Tool 실행 │
│ (분석만)  │      │(실행만)   │      │ (검색)   │
└──────────┘      └──────────┘      └──────────┘
```

### 4. 구체적 문제 사례

#### 사례 1: 키워드 추출 중복
```python
# Step 1: PlanningAgent에서 분석
intent_result = await planning_agent.analyze_intent("전세금 5% 인상이 가능한가요?")
# 결과: keywords = ["전세금", "5%", "인상", "가능"]

# Step 2: SearchExecutor에서 다시 추출 (불필요!)
keywords = await search_executor._extract_keywords_with_llm("전세금 5% 인상이 가능한가요?")
# 결과: keywords = ["전세금", "인상", "법률"] (다를 수 있음!)
```

#### 사례 2: 도구 선택 중복
```python
# Step 1: PlanningAgent에서 Agent 선택
agents = await planning_agent.suggest_agents(intent_result)
# 결과: ["search_team"]

# Step 2: SearchExecutor에서 도구 선택 (중복!)
tools = await search_executor._select_tools_with_llm(query, keywords)
# 결과: ["legal_search", "market_data"]
# ⚠️ Planning에서 이미 어떤 도구가 필요한지 판단했어야 함!
```

### 5. 성능 및 비용 영향

| 항목 | 현재 | 예상 개선 |
|------|------|-----------|
| LLM 호출 횟수 (검색 요청당) | 4-6회 | 2-3회 (50% 감소) |
| 평균 응답 시간 | 5-8초 | 3-5초 (30% 단축) |
| LLM API 비용 | 100% | 50% (중복 제거) |
| 코드 복잡도 | 높음 | 낮음 |

---

## ✅ 제안하는 아키텍처

### 핵심 원칙

> **"Cognitive는 생각만, Execution은 행동만"**

### 새로운 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                    Team Supervisor                              │
│  - 오케스트레이션만                                              │
│  - LLM 호출: generate_final_response() (최종 응답 생성)         │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
┌───────▼──────────┐  ┌───────▼──────────┐
│ Cognitive Layer  │  │ Execution Layer  │
│  🧠 모든 LLM     │  │  🔧 도구만       │
└──────────────────┘  └──────────────────┘

===== ✅ NEW: Cognitive Layer (모든 분석 통합) =====
┌─────────────────────────────────────────────────────────────────┐
│              PlanningAgent (확장)                                │
│  🧠 LLM 호출 (모든 인지 작업):                                   │
│   1. analyze_intent()          - 의도 분석                       │
│   2. extract_keywords()        - 키워드 추출 ✨ NEW             │
│   3. select_agents()           - Agent 선택                      │
│   4. select_tools_for_agent()  - Tool 선택 ✨ NEW               │
│   5. decompose_query()         - 질문 분해 (QueryDecomposer)    │
│   6. build_execution_plan()    - 실행 계획 생성 ✨ ENHANCED     │
│                                                                  │
│  📤 Output (ExecutionPlan):                                      │
│   {                                                              │
│     "intent": {                                                  │
│       "intent_type": "LEGAL_CONSULT",                            │
│       "confidence": 0.95,                                        │
│       "keywords": ["전세금", "5%", "인상"],                       │
│       "entities": {"percentage": "5%", "type": "전세금"}         │
│     },                                                           │
│     "execution_steps": [                                         │
│       {                                                          │
│         "agent": "search_team",                                  │
│         "tools": ["legal_search", "market_data"],                │
│         "keywords": {                                            │
│           "legal": ["전세금", "인상", "임대차보호법"],            │
│           "market": ["전세", "시세", "지역"]                      │
│         },                                                       │
│         "params": {                                              │
│           "legal_search": {                                      │
│             "query": "전세금 인상 5% 제한",                       │
│             "filters": {"law_type": "임대차보호법"}              │
│           },                                                     │
│           "market_data": {                                       │
│             "region": "서울",                                    │
│             "property_type": "전세"                              │
│           }                                                      │
│         }                                                        │
│       }                                                          │
│     ]                                                            │
│   }                                                              │
└─────────────────────────────────────────────────────────────────┘

===== ✅ NEW: Execution Layer (도구 실행만) =====
┌─────────────────────────────────────────────────────────────────┐
│             SearchExecutor (간소화)                              │
│  🔧 Tool 실행만:                                                 │
│   - execute(execution_plan)                                     │
│   - _run_tool(tool_name, keywords, params)                      │
│                                                                  │
│  🔧 Tool 인스턴스:                                               │
│   - legal_search_tool.search(keywords, params)                  │
│   - market_data_tool.search(keywords, params)                   │
│   - real_estate_search_tool.search(keywords, params)            │
│   - loan_data_tool.search(keywords, params)                     │
│                                                                  │
│  ❌ LLM 호출 제거:                                               │
│   - _extract_keywords_with_llm() → 삭제                         │
│   - _select_tools_with_llm() → 삭제                             │
│                                                                  │
│  📥 Input (Planning에서 완성된 계획 받음):                       │
│   - execution_plan.steps[0].tools                               │
│   - execution_plan.steps[0].keywords                            │
│   - execution_plan.steps[0].params                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│          AnalysisExecutor (간소화)                               │
│  🔧 분석 도구 실행만:                                            │
│   - execute(execution_plan)                                     │
│   - _run_analysis_tool(tool_name, data, params)                 │
│                                                                  │
│  🔧 Tool 인스턴스:                                               │
│   - market_analysis_tool.analyze(data, params)                  │
│   - contract_analysis_tool.analyze(data, params)                │
│                                                                  │
│  ❌ LLM 호출 최소화:                                             │
│   - 도구 선택은 Planning에서 이미 완료                           │
│   - 분석 도구 내부에서만 필요 시 LLM 사용                        │
│     (단, 도구 선택이나 키워드 추출은 하지 않음)                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│         DocumentExecutor (간소화)                                │
│  🔧 문서 생성/검토 실행만:                                       │
│   - execute(execution_plan)                                     │
│   - _run_document_tool(tool_name, template, data, params)       │
│                                                                  │
│  ❌ LLM 호출 최소화:                                             │
│   - 템플릿 선택은 Planning에서                                   │
│   - 문서 생성은 도구에서 (LLM 사용 가능)                         │
└─────────────────────────────────────────────────────────────────┘
```

### 데이터 흐름 비교

#### AS-IS (현재)
```
Query: "전세금 5% 인상이 가능한가요?"
   ↓
┌─────────────────┐
│ PlanningAgent   │
│  🧠 LLM 호출    │ → intent: LEGAL_CONSULT
│                 │ → keywords: ["전세금", "인상"] (추출됨)
│                 │ → agents: ["search_team"]
└─────────────────┘
   ↓
┌─────────────────┐
│ SearchExecutor  │
│  🧠 LLM 호출 ❌ │ → keywords: ["전세금", "인상"] (다시 추출!)
│  🧠 LLM 호출 ❌ │ → tools: ["legal_search"] (다시 선택!)
│  🔧 Tool 실행   │ → legal_search.search()
└─────────────────┘
```

#### TO-BE (제안)
```
Query: "전세금 5% 인상이 가능한가요?"
   ↓
┌─────────────────────────────────┐
│ PlanningAgent                    │
│  🧠 LLM 호출 (1회, 통합 분석)   │
│   - intent: LEGAL_CONSULT        │
│   - keywords: ["전세금", "인상"] │
│   - agents: ["search_team"]      │
│   - tools: ["legal_search"]      │
│   - params: {법률 검색 조건}     │
└─────────────────────────────────┘
   ↓ (ExecutionPlan 전달)
┌─────────────────────────────────┐
│ SearchExecutor                   │
│  🔧 Tool 실행만                  │
│   - legal_search.search(         │
│       keywords,                  │
│       params                     │
│     )                            │
└─────────────────────────────────┘
```

---

## 🚀 구현 계획

### Phase 1: PlanningAgent 확장 (3-5일)

#### 1.1 키워드 추출 메서드 추가

**파일**: `planning_agent.py`

```python
async def extract_keywords_for_agent(
    self,
    query: str,
    intent_result: IntentResult,
    agent_name: str
) -> Dict[str, List[str]]:
    """
    Agent별 맞춤 키워드 추출

    Args:
        query: 사용자 질문
        intent_result: 의도 분석 결과
        agent_name: Agent 이름 (search_team, analysis_team, document_team)

    Returns:
        {
            "primary": ["전세금", "인상"],
            "legal": ["임대차보호법", "5%"],
            "entities": ["5%", "보증금"]
        }
    """
    result = await self.llm_service.complete_json_async(
        prompt_name="keyword_extraction_by_agent",
        variables={
            "query": query,
            "intent_type": intent_result.intent_type.value,
            "agent_name": agent_name,
            "base_keywords": ", ".join(intent_result.keywords)
        },
        temperature=0.3
    )
    return result
```

**프롬프트 파일**: `prompts/cognitive/keyword_extraction_by_agent.txt`

```
당신은 질의 분석 전문가입니다.
사용자 질문에서 {agent_name}가 사용할 키워드를 추출하세요.

## 사용자 질문
{query}

## 의도 분석 결과
- 의도 유형: {intent_type}
- 기본 키워드: {base_keywords}

## Agent별 키워드 추출 가이드

### search_team
- primary: 핵심 검색어
- legal: 법률 관련 키워드
- market: 시장 데이터 관련 키워드
- entities: 구체적 수치/지역/날짜

### analysis_team
- metrics: 분석할 지표
- dimensions: 분석 차원
- comparisons: 비교 대상

### document_team
- template_type: 필요한 문서 유형
- key_terms: 문서에 포함될 핵심 용어

JSON 형식으로 출력:
{
    "primary": [...],
    "legal": [...],
    "market": [...],
    "entities": {...}
}
```

#### 1.2 도구 선택 메서드 추가

**파일**: `planning_agent.py`

```python
async def select_tools_for_agent(
    self,
    query: str,
    intent_result: IntentResult,
    agent_name: str,
    keywords: Dict[str, List[str]]
) -> List[str]:
    """
    Agent에 필요한 도구 선택

    Args:
        query: 사용자 질문
        intent_result: 의도 분석 결과
        agent_name: Agent 이름
        keywords: 추출된 키워드

    Returns:
        선택된 도구 리스트
        예: ["legal_search", "market_data"]
    """
    # 사용 가능한 도구 목록
    available_tools = self._get_available_tools(agent_name)

    result = await self.llm_service.complete_json_async(
        prompt_name="tool_selection_by_agent",
        variables={
            "query": query,
            "intent_type": intent_result.intent_type.value,
            "agent_name": agent_name,
            "keywords": json.dumps(keywords, ensure_ascii=False),
            "available_tools": json.dumps(available_tools, ensure_ascii=False)
        },
        temperature=0.2
    )

    return result.get("selected_tools", [])

def _get_available_tools(self, agent_name: str) -> Dict[str, str]:
    """Agent별 사용 가능한 도구 반환"""
    tools_map = {
        "search_team": {
            "legal_search": "법률 조항 검색",
            "market_data": "시장 시세 데이터 조회",
            "real_estate_search": "부동산 정보 검색",
            "loan_data": "대출 상품 정보 조회"
        },
        "analysis_team": {
            "market_analysis": "시장 데이터 분석",
            "contract_analysis": "계약서 분석",
            "risk_analysis": "리스크 분석"
        },
        "document_team": {
            "contract_generator": "계약서 생성",
            "document_reviewer": "문서 검토"
        }
    }
    return tools_map.get(agent_name, {})
```

**프롬프트 파일**: `prompts/cognitive/tool_selection_by_agent.txt`

```
당신은 도구 선택 전문가입니다.
{agent_name}가 사용자 질문에 답하기 위해 필요한 도구를 선택하세요.

## 사용자 질문
{query}

## 의도 유형
{intent_type}

## 추출된 키워드
{keywords}

## 사용 가능한 도구
{available_tools}

## 선택 기준
1. 질문에 직접 답하기 위해 필요한 도구만 선택
2. 최소한의 도구로 최대 효과
3. 도구 간 의존성 고려

JSON 형식으로 출력:
{
    "selected_tools": ["tool1", "tool2"],
    "reasoning": "선택 이유"
}
```

#### 1.3 ExecutionPlan 구조 확장

**파일**: `planning_agent.py`

```python
@dataclass
class ExecutionStep:
    """실행 단계 (확장)"""
    agent_name: str
    priority: int

    # ✨ NEW: 도구 및 파라미터 정보 추가
    selected_tools: List[str] = field(default_factory=list)
    keywords: Dict[str, List[str]] = field(default_factory=dict)
    tool_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 기존 필드
    dependencies: List[str] = field(default_factory=list)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 1
    optional: bool = False
```

#### 1.4 통합 실행 계획 생성 메서드

**파일**: `planning_agent.py`

```python
async def build_execution_plan(
    self,
    query: str,
    intent_result: IntentResult
) -> ExecutionPlan:
    """
    완전한 실행 계획 생성 (키워드 추출 + 도구 선택 포함)

    Returns:
        ExecutionPlan with:
        - steps[].selected_tools
        - steps[].keywords
        - steps[].tool_params
    """
    steps = []

    for agent_name in intent_result.suggested_agents:
        # 1. Agent별 키워드 추출
        keywords = await self.extract_keywords_for_agent(
            query, intent_result, agent_name
        )

        # 2. Agent별 도구 선택
        selected_tools = await self.select_tools_for_agent(
            query, intent_result, agent_name, keywords
        )

        # 3. 도구별 파라미터 구성
        tool_params = self._build_tool_params(
            agent_name, selected_tools, keywords, intent_result
        )

        # 4. ExecutionStep 생성
        step = ExecutionStep(
            agent_name=agent_name,
            priority=self._get_priority(agent_name),
            selected_tools=selected_tools,
            keywords=keywords,
            tool_params=tool_params,
            timeout=30,
            retry_count=1
        )
        steps.append(step)

    # 5. ExecutionPlan 반환
    return ExecutionPlan(
        steps=steps,
        strategy=self._determine_strategy(steps),
        intent=intent_result,
        estimated_time=self._estimate_time(steps)
    )

def _build_tool_params(
    self,
    agent_name: str,
    selected_tools: List[str],
    keywords: Dict[str, List[str]],
    intent_result: IntentResult
) -> Dict[str, Dict[str, Any]]:
    """도구별 실행 파라미터 구성"""
    params = {}

    for tool_name in selected_tools:
        if agent_name == "search_team":
            if tool_name == "legal_search":
                params[tool_name] = {
                    "query": " ".join(keywords.get("legal", [])),
                    "filters": {"law_type": "임대차보호법"},
                    "max_results": 5
                }
            elif tool_name == "market_data":
                params[tool_name] = {
                    "keywords": keywords.get("market", []),
                    "region": intent_result.entities.get("region", "서울"),
                    "property_type": "전세"
                }
        # ... 다른 도구들

    return params
```

**테스트 케이스**:
```python
# tests/test_planning_agent_extended.py
async def test_build_execution_plan():
    planning_agent = PlanningAgent()

    query = "전세금 5% 인상이 가능한가요?"
    intent_result = await planning_agent.analyze_intent(query)

    plan = await planning_agent.build_execution_plan(query, intent_result)

    assert len(plan.steps) > 0
    assert plan.steps[0].selected_tools is not None
    assert plan.steps[0].keywords is not None
    assert "legal_search" in plan.steps[0].selected_tools
```

---

### Phase 2: SearchExecutor 간소화 (2-3일)

#### 2.1 LLM 호출 메서드 제거

**파일**: `search_executor.py`

**삭제할 메서드**:
```python
# ❌ 삭제
async def _extract_keywords_with_llm(self, query: str):
    """삭제 - Planning에서 처리"""
    pass

# ❌ 삭제
async def _select_tools_with_llm(self, query: str, keywords: List[str]):
    """삭제 - Planning에서 처리"""
    pass
```

#### 2.2 새로운 execute 메서드

**파일**: `search_executor.py`

```python
async def execute(self, execution_step: ExecutionStep) -> Dict[str, Any]:
    """
    검색 실행 (Planning에서 받은 계획대로 실행)

    Args:
        execution_step: Planning에서 생성한 실행 단계

    Returns:
        검색 결과
    """
    results = {}

    # Planning에서 선택된 도구들을 순차/병렬 실행
    for tool_name in execution_step.selected_tools:
        try:
            # 도구별 실행
            result = await self._run_tool(
                tool_name=tool_name,
                keywords=execution_step.keywords,
                params=execution_step.tool_params.get(tool_name, {})
            )
            results[tool_name] = {
                "status": "success",
                "data": result
            }

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            results[tool_name] = {
                "status": "error",
                "error": str(e)
            }

    return {
        "status": "completed",
        "tools_executed": list(results.keys()),
        "results": results
    }

async def _run_tool(
    self,
    tool_name: str,
    keywords: Dict[str, List[str]],
    params: Dict[str, Any]
) -> Any:
    """
    도구 실행 (LLM 호출 없음, 순수 검색만)

    Args:
        tool_name: 도구 이름
        keywords: Planning에서 추출한 키워드
        params: Planning에서 구성한 파라미터
    """
    if tool_name == "legal_search":
        if not self.legal_search_tool:
            raise ValueError("LegalSearchTool not initialized")
        return await self.legal_search_tool.search(
            query=params.get("query", ""),
            filters=params.get("filters", {}),
            max_results=params.get("max_results", 5)
        )

    elif tool_name == "market_data":
        if not self.market_data_tool:
            raise ValueError("MarketDataTool not initialized")
        return await self.market_data_tool.search(
            keywords=params.get("keywords", []),
            region=params.get("region", "서울"),
            property_type=params.get("property_type", "전세")
        )

    elif tool_name == "real_estate_search":
        if not self.real_estate_search_tool:
            raise ValueError("RealEstateSearchTool not initialized")
        return await self.real_estate_search_tool.search(
            keywords=keywords.get("primary", []),
            filters=params.get("filters", {})
        )

    elif tool_name == "loan_data":
        if not self.loan_data_tool:
            raise ValueError("LoanDataTool not initialized")
        return await self.loan_data_tool.search(
            keywords=keywords.get("primary", []),
            loan_type=params.get("loan_type", "전세자금대출")
        )

    else:
        raise ValueError(f"Unknown tool: {tool_name}")
```

#### 2.3 기존 메서드 수정

**파일**: `search_executor.py`

```python
# ✅ 기존 노드들을 새 execute 메서드로 리다이렉트
async def route_search_start(self, state: SearchTeamState) -> SearchTeamState:
    """
    검색 시작 노드 (간소화)
    """
    logger.info("=== Search Team Started ===")

    # Planning에서 받은 execution_step 확인
    execution_step = state.get("execution_step")
    if not execution_step:
        logger.error("No execution_step provided by Planning")
        state["status"] = "error"
        state["error_message"] = "No execution plan from Planning"
        return state

    # 실행 계획 로그
    logger.info(f"Executing with tools: {execution_step.selected_tools}")
    logger.info(f"Keywords: {execution_step.keywords}")

    state["status"] = "ready"
    return state

async def execute_search(self, state: SearchTeamState) -> SearchTeamState:
    """
    검색 실행 노드 (새 execute 메서드 사용)
    """
    execution_step = state.get("execution_step")

    # 새로운 execute 메서드 호출
    results = await self.execute(execution_step)

    state["search_results"] = results
    state["status"] = "completed"

    return state
```

**테스트 케이스**:
```python
# tests/test_search_executor_refactored.py
async def test_search_executor_no_llm():
    """SearchExecutor가 LLM 호출 없이 동작하는지 테스트"""

    # Mock LLMService (호출되면 안 됨)
    llm_service_mock = Mock()
    llm_service_mock.complete_json_async.side_effect = AssertionError("LLM should not be called!")

    search_executor = SearchExecutor()
    search_executor.llm_service = llm_service_mock

    # ExecutionStep 준비 (Planning에서 받는 것처럼)
    execution_step = ExecutionStep(
        agent_name="search_team",
        priority=1,
        selected_tools=["legal_search"],
        keywords={
            "legal": ["전세금", "인상", "5%"],
            "primary": ["전세금", "인상"]
        },
        tool_params={
            "legal_search": {
                "query": "전세금 인상 5% 제한",
                "filters": {"law_type": "임대차보호법"},
                "max_results": 5
            }
        }
    )

    # 실행
    results = await search_executor.execute(execution_step)

    # 검증
    assert results["status"] == "completed"
    assert "legal_search" in results["results"]
    # LLM이 호출되지 않았음을 확인 (Mock이 호출되면 AssertionError 발생)
```

---

### Phase 3: AnalysisExecutor & DocumentExecutor 간소화 (2-3일)

#### 3.1 AnalysisExecutor 간소화

**파일**: `analysis_executor.py`

```python
async def execute(self, execution_step: ExecutionStep) -> Dict[str, Any]:
    """
    분석 실행 (Planning에서 받은 계획대로 실행)
    """
    results = {}

    for tool_name in execution_step.selected_tools:
        try:
            result = await self._run_analysis_tool(
                tool_name=tool_name,
                data=execution_step.tool_params.get(tool_name, {}).get("data", {}),
                params=execution_step.tool_params.get(tool_name, {})
            )
            results[tool_name] = {
                "status": "success",
                "data": result
            }
        except Exception as e:
            logger.error(f"Analysis tool {tool_name} failed: {e}")
            results[tool_name] = {
                "status": "error",
                "error": str(e)
            }

    return {
        "status": "completed",
        "tools_executed": list(results.keys()),
        "results": results
    }

async def _run_analysis_tool(
    self,
    tool_name: str,
    data: Dict[str, Any],
    params: Dict[str, Any]
) -> Any:
    """분석 도구 실행"""
    if tool_name == "market_analysis":
        return await self.market_analysis_tool.analyze(data, params)
    elif tool_name == "contract_analysis":
        return await self.contract_analysis_tool.analyze(data, params)
    elif tool_name == "risk_analysis":
        return await self.risk_analysis_tool.analyze(data, params)
    else:
        raise ValueError(f"Unknown analysis tool: {tool_name}")
```

#### 3.2 DocumentExecutor 간소화

**파일**: `document_executor.py`

```python
async def execute(self, execution_step: ExecutionStep) -> Dict[str, Any]:
    """
    문서 생성/검토 실행
    """
    results = {}

    for tool_name in execution_step.selected_tools:
        try:
            result = await self._run_document_tool(
                tool_name=tool_name,
                template=execution_step.tool_params.get(tool_name, {}).get("template"),
                data=execution_step.tool_params.get(tool_name, {}).get("data", {}),
                params=execution_step.tool_params.get(tool_name, {})
            )
            results[tool_name] = {
                "status": "success",
                "data": result
            }
        except Exception as e:
            logger.error(f"Document tool {tool_name} failed: {e}")
            results[tool_name] = {
                "status": "error",
                "error": str(e)
            }

    return {
        "status": "completed",
        "tools_executed": list(results.keys()),
        "results": results
    }
```

---

### Phase 4: TeamSupervisor 통합 (1-2일)

#### 4.1 Supervisor 워크플로우 수정

**파일**: `team_supervisor.py`

```python
async def plan_execution(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    실행 계획 수립 (확장된 PlanningAgent 사용)
    """
    query = state.get("query", "")

    # 1. 의도 분석
    intent_result = await self.planning_agent.analyze_intent(query)

    # 2. 완전한 실행 계획 생성 (키워드 + 도구 선택 포함)
    execution_plan = await self.planning_agent.build_execution_plan(
        query, intent_result
    )

    # 3. State에 저장
    state["planning_state"] = {
        "analyzed_intent": intent_result.__dict__,
        "execution_plan": execution_plan,
        "steps": [step.__dict__ for step in execution_plan.steps]
    }

    logger.info(f"✅ Execution plan built with {len(execution_plan.steps)} steps")
    return state

async def execute_teams(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    팀 실행 (ExecutionPlan에 따라)
    """
    execution_plan = state["planning_state"]["execution_plan"]
    results = {}

    for step in execution_plan.steps:
        agent_name = step.agent_name

        # Executor 실행 (Planning에서 준비된 step 전달)
        if agent_name == "search_team":
            result = await self.search_executor.execute(step)
        elif agent_name == "analysis_team":
            result = await self.analysis_executor.execute(step)
        elif agent_name == "document_team":
            result = await self.document_executor.execute(step)

        results[agent_name] = result

    state["aggregated_results"] = results
    return state
```

---

### Phase 5: 프롬프트 파일 추가 (1일)

#### 5.1 새 프롬프트 파일 생성

**파일 목록**:
```
prompts/cognitive/
├── keyword_extraction_by_agent.txt    ✨ NEW
├── tool_selection_by_agent.txt        ✨ NEW
├── intent_analysis.txt                (기존)
├── agent_selection.txt                (기존)
└── query_decomposition.txt            (기존)
```

#### 5.2 keyword_extraction_by_agent.txt

**경로**: `app/service_agent/llm_manager/prompts/cognitive/keyword_extraction_by_agent.txt`

```
당신은 질의 분석 전문가입니다.
사용자 질문에서 {agent_name}가 사용할 키워드를 추출하세요.

## 사용자 질문
{query}

## 의도 분석 결과
- 의도 유형: {intent_type}
- 기본 키워드: {base_keywords}

## Agent별 키워드 추출 가이드

### search_team (검색팀)
- **primary**: 핵심 검색어 (가장 중요한 2-3개)
- **legal**: 법률 관련 키워드 (법률명, 조항, 법적 용어)
- **market**: 시장 데이터 관련 키워드 (지역, 가격, 시세)
- **entities**: 구체적 개체 (숫자, 날짜, 지역명, 금액)

예시:
```json
{
  "primary": ["전세금", "인상"],
  "legal": ["임대차보호법", "5%", "상한"],
  "market": ["전세", "시세", "서울"],
  "entities": {
    "percentage": "5%",
    "region": "서울",
    "type": "전세금"
  }
}
```

### analysis_team (분석팀)
- **metrics**: 분석할 지표 (가격 변동률, ROI 등)
- **dimensions**: 분석 차원 (지역별, 시간별, 유형별)
- **comparisons**: 비교 대상 (전년 대비, 타지역 대비)

예시:
```json
{
  "metrics": ["가격 변동률", "거래량"],
  "dimensions": ["지역별", "월별"],
  "comparisons": ["전년 대비", "전월 대비"]
}
```

### document_team (문서팀)
- **template_type**: 필요한 문서 유형 (계약서, 확인서, 신청서)
- **key_terms**: 문서에 포함될 핵심 용어
- **parties**: 문서 당사자 정보

예시:
```json
{
  "template_type": "전세계약서",
  "key_terms": ["전세금", "계약기간", "특약사항"],
  "parties": ["임대인", "임차인"]
}
```

## 출력 형식
반드시 JSON 형식으로 출력하세요.
Agent 이름에 따라 적절한 키워드 카테고리를 사용하세요.
```

#### 5.3 tool_selection_by_agent.txt

**경로**: `app/service_agent/llm_manager/prompts/cognitive/tool_selection_by_agent.txt`

```
당신은 도구 선택 전문가입니다.
{agent_name}가 사용자 질문에 답하기 위해 필요한 도구를 선택하세요.

## 사용자 질문
{query}

## 의도 유형
{intent_type}

## 추출된 키워드
{keywords}

## 사용 가능한 도구
{available_tools}

## 도구 선택 원칙

### 1. 최소 필요 원칙
- 질문에 직접 답하기 위해 **반드시 필요한 도구만** 선택
- 불필요한 도구는 선택하지 않음
- 1-3개 도구 권장

### 2. 의도-도구 매칭
- **LEGAL_CONSULT** → legal_search 필수
- **MARKET_INQUIRY** → market_data, real_estate_search
- **LOAN_CONSULT** → loan_data 필수
- **CONTRACT_CREATION** → contract_generator 필수
- **CONTRACT_REVIEW** → document_reviewer 필수
- **COMPREHENSIVE** → 여러 도구 조합

### 3. 도구 의존성 고려
- market_analysis는 market_data 또는 real_estate_search 선행 필요
- contract_analysis는 document_reviewer와 함께 사용

### 4. 키워드-도구 매칭
- 법률 키워드 많음 → legal_search
- 지역/시세 키워드 많음 → market_data, real_estate_search
- 대출 키워드 많음 → loan_data
- 계약서 키워드 많음 → contract_generator, document_reviewer

## 예시

### 예시 1: "전세금 5% 인상이 가능한가요?"
- 의도: LEGAL_CONSULT
- 키워드: ["전세금", "5%", "인상", "임대차보호법"]
- 선택: ["legal_search"]
- 이유: 법률 상담이므로 법률 검색만 필요

### 예시 2: "강남구 전세 시세는 얼마인가요?"
- 의도: MARKET_INQUIRY
- 키워드: ["강남구", "전세", "시세"]
- 선택: ["market_data", "real_estate_search"]
- 이유: 시세 조회이므로 시장 데이터 및 부동산 검색 필요

### 예시 3: "전세자금대출을 받을 수 있나요?"
- 의도: LOAN_CONSULT
- 키워드: ["전세자금대출", "조건", "금리"]
- 선택: ["loan_data"]
- 이유: 대출 상담이므로 대출 정보 조회만 필요

### 예시 4: "강남 전세 시세와 대출 한도를 알려주세요"
- 의도: COMPREHENSIVE
- 키워드: ["강남", "전세", "시세", "대출", "한도"]
- 선택: ["market_data", "real_estate_search", "loan_data"]
- 이유: 시세 + 대출 정보 모두 필요

## 출력 형식
JSON 형식으로 출력:
```json
{
  "selected_tools": ["tool1", "tool2"],
  "reasoning": "도구를 선택한 이유를 간결하게 설명"
}
```
```

---

### Phase 6: 통합 테스트 (2-3일)

#### 6.1 단위 테스트

```python
# tests/test_planning_agent_extended.py
async def test_extract_keywords_for_agent():
    """Agent별 키워드 추출 테스트"""
    planning_agent = PlanningAgent()

    query = "전세금 5% 인상이 가능한가요?"
    intent_result = await planning_agent.analyze_intent(query)

    keywords = await planning_agent.extract_keywords_for_agent(
        query, intent_result, "search_team"
    )

    assert "primary" in keywords
    assert "legal" in keywords
    assert len(keywords["primary"]) > 0

async def test_select_tools_for_agent():
    """Agent별 도구 선택 테스트"""
    planning_agent = PlanningAgent()

    query = "전세금 5% 인상이 가능한가요?"
    intent_result = await planning_agent.analyze_intent(query)
    keywords = await planning_agent.extract_keywords_for_agent(
        query, intent_result, "search_team"
    )

    tools = await planning_agent.select_tools_for_agent(
        query, intent_result, "search_team", keywords
    )

    assert "legal_search" in tools
    assert len(tools) <= 3  # 최소 필요 원칙

async def test_build_execution_plan_complete():
    """완전한 실행 계획 생성 테스트"""
    planning_agent = PlanningAgent()

    query = "전세금 5% 인상이 가능한가요?"
    intent_result = await planning_agent.analyze_intent(query)

    plan = await planning_agent.build_execution_plan(query, intent_result)

    assert len(plan.steps) > 0
    assert plan.steps[0].selected_tools is not None
    assert plan.steps[0].keywords is not None
    assert plan.steps[0].tool_params is not None
```

#### 6.2 통합 테스트

```python
# tests/test_cognitive_execution_integration.py
async def test_end_to_end_no_llm_in_execution():
    """Execution Layer에서 LLM 호출이 없는지 확인"""

    # Mock LLMService for Execution Layer
    execution_llm_mock = Mock()
    execution_llm_mock.complete_json_async.side_effect = \
        AssertionError("Execution Layer should NOT call LLM!")

    # Setup
    supervisor = TeamSupervisor()
    supervisor.search_executor.llm_service = execution_llm_mock

    # Execute
    query = "전세금 5% 인상이 가능한가요?"
    result = await supervisor.process(query)

    # Verify
    assert result["status"] == "success"
    # If execution called LLM, AssertionError would be raised

async def test_planning_provides_complete_plan():
    """Planning이 완전한 계획을 제공하는지 테스트"""

    planning_agent = PlanningAgent()
    query = "강남구 전세 시세를 알려주세요"

    intent_result = await planning_agent.analyze_intent(query)
    plan = await planning_agent.build_execution_plan(query, intent_result)

    # Verify plan completeness
    for step in plan.steps:
        assert len(step.selected_tools) > 0, "Tools must be selected"
        assert len(step.keywords) > 0, "Keywords must be extracted"
        assert len(step.tool_params) > 0, "Params must be provided"

        # Verify each selected tool has params
        for tool in step.selected_tools:
            assert tool in step.tool_params, f"No params for {tool}"
```

#### 6.3 성능 테스트

```python
# tests/test_performance_improvement.py
import time

async def test_llm_call_count():
    """LLM 호출 횟수 감소 확인"""

    # Mock LLM to count calls
    call_counter = {"count": 0}

    def count_and_return(*args, **kwargs):
        call_counter["count"] += 1
        return {"result": "mocked"}

    llm_service_mock = Mock()
    llm_service_mock.complete_json_async.side_effect = count_and_return

    supervisor = TeamSupervisor()
    supervisor.planning_agent.llm_service = llm_service_mock

    # Execute
    query = "전세금 5% 인상이 가능한가요?"
    await supervisor.process(query)

    # Verify: Should be 3-4 calls (intent + keywords + tools + final response)
    # NOT 6-8 calls (old architecture with redundant calls)
    assert call_counter["count"] <= 4, f"Too many LLM calls: {call_counter['count']}"

async def test_response_time_improvement():
    """응답 시간 개선 확인"""

    supervisor = TeamSupervisor()
    query = "강남구 전세 시세를 알려주세요"

    start = time.time()
    result = await supervisor.process(query)
    elapsed = time.time() - start

    # 기대: 5초 이내 (기존: 7-8초)
    assert elapsed < 5.0, f"Response too slow: {elapsed:.2f}s"
```

---

## 📊 예상 효과

### 1. 성능 개선

| 지표 | 현재 (AS-IS) | 목표 (TO-BE) | 개선율 |
|------|-------------|--------------|--------|
| LLM 호출 횟수 (검색 요청당) | 4-6회 | 2-3회 | **50% 감소** |
| 평균 응답 시간 | 5-8초 | 3-5초 | **30% 단축** |
| LLM API 비용 (월간) | 100만원 | 50만원 | **50% 절감** |

### 2. 코드 품질 개선

| 측면 | AS-IS | TO-BE |
|------|-------|-------|
| **책임 분리** | 혼재 (Execution이 분석도 함) | 명확 (Cognitive는 생각, Execution은 행동) |
| **코드 중복** | 높음 (키워드 추출 2회) | 없음 (1회만) |
| **테스트 용이성** | 어려움 (LLM Mock 필요) | 쉬움 (레이어 독립) |
| **유지보수성** | 낮음 (변경 영향 큼) | 높음 (레이어 분리) |
| **확장성** | 낮음 (새 도구 추가 복잡) | 높음 (Planning만 수정) |

### 3. 아키텍처 명확성

**AS-IS (혼재):**
```
Cognitive: 의도 분석
Execution: 키워드 추출 + 도구 선택 + 실행  ← 역할 혼재!
```

**TO-BE (명확):**
```
Cognitive: 의도 분석 + 키워드 추출 + 도구 선택  ← 모든 분석
Execution: 실행만                             ← 행동만
```

---

## ⚠️ 리스크 관리

### 1. 기존 코드 호환성

**리스크**: 기존 SearchExecutor를 사용하는 코드가 깨질 수 있음

**완화 방안**:
- Phase 2에서 임시로 기존 메서드를 deprecation warning과 함께 유지
- 점진적 마이그레이션 (새 코드는 새 방식, 기존 코드는 기존 방식)
- 충분한 테스트 커버리지 확보

```python
# search_executor.py - 임시 호환성 유지
async def _extract_keywords_with_llm(self, query: str):
    """
    @deprecated: Use PlanningAgent.extract_keywords_for_agent() instead
    """
    warnings.warn(
        "SearchExecutor._extract_keywords_with_llm is deprecated. "
        "Use PlanningAgent.extract_keywords_for_agent() instead.",
        DeprecationWarning
    )
    # 기존 로직 유지 (임시)
    ...
```

### 2. LLM 호출 증가 우려 (Planning에서)

**리스크**: Planning에서 키워드 추출 + 도구 선택을 추가하면 LLM 호출이 증가할 수 있음

**완화 방안**:
- **배치 처리**: 의도 분석, 키워드 추출, 도구 선택을 하나의 LLM 호출로 통합
- 단일 프롬프트에서 모든 정보를 한 번에 추출

```python
# 통합 프롬프트 예시
async def analyze_and_plan_all_in_one(self, query: str):
    """
    하나의 LLM 호출로 의도 분석 + 키워드 추출 + 도구 선택 수행
    """
    result = await self.llm_service.complete_json_async(
        prompt_name="comprehensive_planning",  # 통합 프롬프트
        variables={"query": query}
    )
    # 결과에서 intent, keywords, tools 모두 추출
    return result
```

### 3. ExecutionPlan 구조 복잡도

**리스크**: ExecutionPlan에 너무 많은 정보가 포함되어 복잡해질 수 있음

**완화 방안**:
- 명확한 데이터 클래스 정의 (typing)
- 문서화 강화
- 유효성 검증 추가

```python
@dataclass
class ExecutionStep:
    """실행 단계 (완전한 타입 힌트)"""
    agent_name: str
    priority: int
    selected_tools: List[str]
    keywords: Dict[str, List[str]]
    tool_params: Dict[str, Dict[str, Any]]

    def validate(self):
        """유효성 검증"""
        assert len(self.selected_tools) > 0, "No tools selected"
        for tool in self.selected_tools:
            assert tool in self.tool_params, f"Missing params for {tool}"
```

### 4. 마이그레이션 리소스

**리스크**: 전체 리팩토링에 2-3주 소요 예상

**완화 방안**:
- Phase별 점진적 구현
- 각 Phase 완료 후 통합 테스트
- 롤백 가능한 구조 (feature flag 사용)

```python
# config.py - Feature flag
USE_NEW_COGNITIVE_EXECUTION_ARCHITECTURE = os.getenv(
    "USE_NEW_ARCH", "false"
).lower() == "true"

# supervisor.py
if USE_NEW_COGNITIVE_EXECUTION_ARCHITECTURE:
    # 새 방식
    plan = await self.planning_agent.build_execution_plan(query, intent)
else:
    # 기존 방식
    plan = await self.planning_agent.suggest_agents(intent)
```

---

## 📅 일정 및 마일스톤

### 전체 일정: 2-3주

| Phase | 작업 | 기간 | 담당 | 완료 기준 |
|-------|------|------|------|-----------|
| **Phase 1** | PlanningAgent 확장 | 3-5일 | Dev Team | - `extract_keywords_for_agent()` 구현<br>- `select_tools_for_agent()` 구현<br>- `build_execution_plan()` 구현<br>- 프롬프트 파일 추가<br>- 단위 테스트 통과 |
| **Phase 2** | SearchExecutor 간소화 | 2-3일 | Dev Team | - LLM 호출 제거<br>- 새 `execute()` 메서드 구현<br>- 기존 메서드 deprecation<br>- 단위 테스트 통과 |
| **Phase 3** | Analysis/Document Executor 간소화 | 2-3일 | Dev Team | - 동일 패턴 적용<br>- 단위 테스트 통과 |
| **Phase 4** | TeamSupervisor 통합 | 1-2일 | Dev Team | - Supervisor 워크플로우 수정<br>- ExecutionPlan 전달 구현 |
| **Phase 5** | 프롬프트 파일 추가 | 1일 | Dev Team | - 2개 프롬프트 파일 작성<br>- 테스트 및 튜닝 |
| **Phase 6** | 통합 테스트 | 2-3일 | QA Team | - E2E 테스트 통과<br>- 성능 테스트 통과<br>- 회귀 테스트 통과 |

### 마일스톤

- **Week 1 완료**: Phase 1-2 완료, PlanningAgent 확장 및 SearchExecutor 간소화
- **Week 2 완료**: Phase 3-4 완료, 모든 Executor 간소화 및 Supervisor 통합
- **Week 3 완료**: Phase 5-6 완료, 프롬프트 추가 및 통합 테스트

---

## ✅ 체크리스트

### Phase 1: PlanningAgent 확장
- [ ] `extract_keywords_for_agent()` 메서드 구현
- [ ] `select_tools_for_agent()` 메서드 구현
- [ ] `build_execution_plan()` 메서드 구현
- [ ] `ExecutionStep` 데이터 클래스 확장
- [ ] `_get_available_tools()` 헬퍼 메서드 구현
- [ ] `_build_tool_params()` 헬퍼 메서드 구현
- [ ] 단위 테스트 작성 및 통과

### Phase 2: SearchExecutor 간소화
- [ ] `_extract_keywords_with_llm()` 삭제 (또는 deprecation)
- [ ] `_select_tools_with_llm()` 삭제 (또는 deprecation)
- [ ] 새 `execute(execution_step)` 메서드 구현
- [ ] `_run_tool()` 메서드 구현
- [ ] 기존 노드들을 새 메서드로 리다이렉트
- [ ] 단위 테스트 작성 및 통과
- [ ] LLM 호출이 없는지 검증

### Phase 3: Analysis/Document Executor 간소화
- [ ] AnalysisExecutor에 `execute()` 메서드 구현
- [ ] DocumentExecutor에 `execute()` 메서드 구현
- [ ] LLM 호출 최소화
- [ ] 단위 테스트 작성 및 통과

### Phase 4: TeamSupervisor 통합
- [ ] `plan_execution()` 메서드 수정 (ExecutionPlan 생성)
- [ ] `execute_teams()` 메서드 수정 (ExecutionPlan 전달)
- [ ] State 구조 업데이트
- [ ] 통합 테스트 작성 및 통과

### Phase 5: 프롬프트 파일 추가
- [ ] `keyword_extraction_by_agent.txt` 작성
- [ ] `tool_selection_by_agent.txt` 작성
- [ ] 프롬프트 테스트 및 튜닝

### Phase 6: 통합 테스트
- [ ] E2E 테스트 작성 및 통과
- [ ] 성능 테스트 (LLM 호출 횟수, 응답 시간)
- [ ] 회귀 테스트 (기존 기능 동작 확인)
- [ ] 문서화 업데이트

---

## 📚 참고 자료

### 관련 파일
- `app/service_agent/cognitive_agents/planning_agent.py`
- `app/service_agent/execution_agents/search_executor.py`
- `app/service_agent/execution_agents/analysis_executor.py`
- `app/service_agent/execution_agents/document_executor.py`
- `app/service_agent/supervisor/team_supervisor.py`
- `app/service_agent/llm_manager/llm_service.py`

### 관련 문서
- Architecture Design Document
- LLM Service Documentation
- Agent Registry Documentation

---

## 🔄 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2025-10-14 | 1.0 | 초안 작성 | Dev Team |

---

**다음 단계**: Phase 1 구현 착수
