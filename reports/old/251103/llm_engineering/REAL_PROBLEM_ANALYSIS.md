# 실제 문제 분석: SearchExecutor는 Agent인가 Tool인가?

**작성일**: 2025-10-14
**작성자**: Development Team

---

## 🤔 핵심 질문

> "SearchExecutor가 LLM을 호출하여 키워드 추출과 도구 선택을 하는 것이 문제인가?"

**답변**: 아니다. SearchExecutor는 **Agent**이므로 LLM을 호출하여 **생각하고 결정해야 한다**.

---

## ✅ 올바른 이해: Agent vs Tool

### Agent의 역할

```
Agent = LLM이 추론하고 결정하는 자율적 주체

역할:
1. 상황 분석 (Analyze)
2. 계획 수립 (Plan)
3. 도구 선택 (Choose tools)
4. 실행 결정 (Decide actions)
5. 결과 평가 (Evaluate)
6. 다음 단계 결정 (Next step)

핵심: "생각하고 결정한다"
```

### Tool의 역할

```
Tool = Agent가 사용하는 수동적 도구

역할:
1. Agent의 명령 받기
2. 명령대로 실행
3. 결과 반환

핵심: "시키는 대로 한다"
```

### 예시로 이해하기

```
인간 비유:
- Agent = 탐정 (생각하고 추론)
- Tool = 돋보기, 카메라, 검색엔진 (도구)

탐정(Agent)의 사고 과정:
1. "이 사건을 해결하려면..." (분석)
2. "먼저 현장을 조사하고..." (계획)
3. "돋보기와 카메라가 필요해" (도구 선택)
4. "여기를 자세히 봐야겠어" (실행 결정)
5. "이 증거는 중요해 보여" (평가)
6. "다음엔 증인을 찾아가자" (다음 단계)

돋보기(Tool):
- 탐정이 "여기 봐"라고 하면 → 확대해서 보여줌
- 스스로 "여기가 중요해 보여"라고 판단하지 않음
```

---

## 🔍 현재 시스템 재분석

### 현재 아키텍처 (올바른 이해)

```
┌─────────────────────────────────────────────────────────┐
│               TeamSupervisor (Meta-Agent)               │
│  역할: 전체 오케스트레이션, 팀 간 조율                    │
│  LLM 사용: ✅ (어떤 팀을 호출할지 결정)                  │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
┌───────▼──────────┐  ┌───────▼──────────┐
│ PlanningAgent    │  │ SearchExecutor   │
│ (Cognitive Agent)│  │ (Execution Agent)│
│                  │  │                  │
│ 역할: 계획 수립   │  │ 역할: 검색 실행  │
│ LLM: ✅ 사용     │  │ LLM: ✅ 사용     │
└──────────────────┘  └──────────────────┘
         │                     │
         │                     ├─ legal_search_tool (Tool)
         │                     ├─ market_data_tool (Tool)
         │                     ├─ loan_data_tool (Tool)
         │                     └─ real_estate_search_tool (Tool)
         │
         └─ query_decomposer (Sub-Agent)
```

### 역할 분담 (올바른 이해)

| Component | 유형 | LLM 사용 | 역할 | 예시 |
|-----------|------|----------|------|------|
| **TeamSupervisor** | Meta-Agent | ✅ Yes | 전체 조율, 팀 선택 | "검색팀과 분석팀이 필요해" |
| **PlanningAgent** | Cognitive Agent | ✅ Yes | 의도 분석, 계획 수립 | "법률 상담 의도야, 검색팀 호출해야겠어" |
| **SearchExecutor** | **Execution Agent** | **✅ Yes** | **검색 전략 결정, 도구 선택** | **"법률 검색이 필요해, legal_search_tool을 써야겠어"** |
| **AnalysisExecutor** | Execution Agent | ✅ Yes | 분석 전략 결정, 도구 선택 | "시장 분석이 필요해, market_analysis_tool을 써야겠어" |
| **legal_search_tool** | Tool | ❌ No | 법률 DB 검색 | (입력 받아서 검색만 함) |
| **market_data_tool** | Tool | ❌ No | 시세 API 호출 | (입력 받아서 호출만 함) |

---

## ❌ 이전 분석의 오류

### 잘못된 가정 1: "Execution Layer는 LLM 호출하면 안 된다"

**잘못됨!**

```
❌ 잘못된 생각:
Cognitive = LLM 사용 (분석, 계획)
Execution = Tool만 사용 (실행만)

✅ 올바른 이해:
Cognitive Agent = 전략적 계획 (What teams to use?)
Execution Agent = 전술적 실행 (How to execute? Which tools?)
Tool = 수동적 도구 (Just execute)

둘 다 Agent이므로 둘 다 LLM을 사용한다!
```

### 잘못된 가정 2: "키워드 추출은 Planning에서 해야 한다"

**잘못됨!**

```
❌ 잘못된 생각:
Planning: 키워드 추출, 도구 선택
Search: 도구 실행만

✅ 올바른 이해:
Planning: "검색이 필요한가?" (전략적 결정)
Search: "어떤 키워드로 어떤 도구를 쓸까?" (전술적 결정)

각 Agent는 자신의 도메인에서 자율적으로 결정한다!
```

### 잘못된 가정 3: "중복 분석이 문제다"

**재해석 필요!**

```
❌ 잘못된 생각:
Planning에서 키워드 추출 → Search에서 또 추출 → 중복!

✅ 올바른 이해:
Planning: 의도 분석용 키워드 (intent-level)
  예: "이 질문은 법률 상담이야" → keywords: ["법률", "상담"]

Search: 검색 실행용 키워드 (execution-level)
  예: "어떤 법률 조항을 검색할까?" → keywords: ["임대차보호법", "전세금", "5%"]

서로 다른 목적의 키워드 추출이다!
```

---

## 🎯 실제 문제는 무엇인가?

### 현재 코드 분석

```python
# search_executor.py (Line 187-207)
def _extract_keywords_with_llm(self, query: str) -> SearchKeywords:
    """LLM을 사용한 키워드 추출"""
    result = self.llm_service.complete_json(
        prompt_name="keyword_extraction",
        variables={"query": query},
        temperature=0.1
    )
    return SearchKeywords(
        legal=result.get("legal", []),
        real_estate=result.get("real_estate", []),
        loan=result.get("loan", []),
        general=result.get("general", [])
    )

# search_executor.py (Line 309-349)
async def _select_tools_with_llm(
    self,
    query: str,
    keywords: SearchKeywords = None
) -> Dict[str, Any]:
    """LLM을 사용한 tool 선택"""
    available_tools = self._get_available_tools()

    result = await self.llm_service.complete_json_async(
        prompt_name="tool_selection_search",
        variables={
            "query": query,
            "available_tools": json.dumps(available_tools, ...)
        },
        temperature=0.1
    )

    return {
        "selected_tools": result.get("selected_tools", []),
        "reasoning": result.get("reasoning", ""),
        "confidence": result.get("confidence", 0.0)
    }
```

### 코드는 이미 올바르다!

**SearchExecutor는 Agent이므로:**
- ✅ 키워드 추출 (자신의 검색 전략)
- ✅ 도구 선택 (어떤 도구를 쓸지 결정)
- ✅ LLM 호출 (추론하고 결정하기 위해)

**이것은 올바른 Agent 설계다!**

---

## 🤔 그렇다면 진짜 문제는?

### 문제 1: PlanningAgent와 SearchExecutor의 역할 구분이 모호

**현재 상황:**
```
PlanningAgent:
- analyze_intent() → "법률 상담"
- suggest_agents() → ["search_team"]

SearchExecutor:
- _extract_keywords_with_llm() → ["전세금", "인상"]
- _select_tools_with_llm() → ["legal_search"]
```

**문제점:**
- Planning이 "search_team이 필요해"라고만 하고 끝남
- Search가 모든 것을 다시 분석함
- **Planning의 분석 결과가 Search에 전달되지 않음**

**해결책:**
```
PlanningAgent:
- analyze_intent() → IntentResult {
    intent_type: "LEGAL_CONSULT",
    keywords: ["전세금", "인상", "5%"],  ← 이걸 전달!
    suggested_agents: ["search_team"]
  }

SearchExecutor:
- receive(intent_result)  ← Planning의 분석 받기
- refine_keywords() → 검색 전문화된 키워드로 정제
- select_tools(intent_result, refined_keywords) → 도구 선택
```

### 문제 2: 정보 흐름이 단절됨

**현재:**
```
Planning → "search_team 호출해"
           ↓ (정보 전달 없음)
Search ← query만 받음 → 처음부터 다시 분석
```

**개선:**
```
Planning → IntentResult {
             intent: "LEGAL_CONSULT",
             keywords: ["전세금", "인상"],
             confidence: 0.95
           }
           ↓ (정보 전달)
Search ← IntentResult + query → 컨텍스트를 활용한 정제
```

### 문제 3: Agent 간 협업 부족

**현재:**
```
각 Agent가 독립적으로 동작
→ 컨텍스트 공유 없음
→ 중복 분석
```

**개선:**
```
Agent들이 이전 Agent의 결과를 활용
→ 컨텍스트 전달
→ 점진적 정제
```

---

## ✅ 올바른 해결 방향

### 원칙 1: Agent는 LLM을 사용해야 한다

```
❌ "Execution Agent는 LLM 쓰면 안 돼"
✅ "Execution Agent도 Agent이므로 LLM으로 추론한다"

Agent의 정의:
- 자율적으로 결정하는 주체
- LLM을 사용하여 추론하고 계획
- Tool을 선택하고 사용
- 결과를 평가하고 다음 단계 결정
```

### 원칙 2: Agent 간 정보 전달을 강화

```python
# ✅ 올바른 방향
class SearchExecutor:
    async def execute(
        self,
        query: str,
        intent_result: IntentResult  # ← Planning의 분석 결과 받기
    ):
        # 1. Planning의 분석 활용
        base_keywords = intent_result.keywords
        intent_type = intent_result.intent_type

        # 2. 검색 도메인에 특화된 키워드로 정제
        refined_keywords = await self._refine_keywords_for_search(
            query=query,
            base_keywords=base_keywords,
            intent_type=intent_type
        )

        # 3. 정제된 키워드와 의도를 바탕으로 도구 선택
        selected_tools = await self._select_tools_with_llm(
            query=query,
            intent_type=intent_type,
            keywords=refined_keywords
        )

        # 4. 도구 실행
        results = await self._execute_tools(selected_tools, refined_keywords)

        return results
```

### 원칙 3: 각 Agent는 자신의 도메인에서 자율적으로 결정

```
PlanningAgent (전략적 레벨):
- "어떤 종류의 작업이 필요한가?" (What needs to be done?)
- "어떤 팀이 필요한가?" (Which teams?)
- "대략적인 키워드는?" (High-level keywords)

SearchExecutor (전술적 레벨):
- "어떻게 검색할 것인가?" (How to search?)
- "어떤 도구를 쓸 것인가?" (Which tools specifically?)
- "구체적인 검색어는?" (Specific search terms)
- "검색 순서는?" (Search order)

legal_search_tool (실행 레벨):
- "받은 키워드로 DB 검색" (Execute query)
- "결과 반환" (Return results)
```

---

## 📋 올바른 구현 계획

### Phase 1: State 구조 확장 (정보 전달 강화)

```python
@dataclass
class SearchTeamState:
    """SearchTeam 상태"""

    # ✅ NEW: Planning의 분석 결과 받기
    intent_result: Optional[IntentResult] = None

    # 기존 필드들...
    team_name: str = "search"
    keywords: SearchKeywords = None
    search_scope: List[str] = field(default_factory=list)
```

### Phase 2: SearchExecutor의 키워드 정제 (중복 제거)

```python
async def _refine_keywords_for_search(
    self,
    query: str,
    base_keywords: List[str],  # Planning에서 받은 키워드
    intent_type: str
) -> SearchKeywords:
    """
    Planning의 키워드를 검색 도메인에 특화된 키워드로 정제

    예:
    Input (from Planning):
      base_keywords: ["전세금", "인상"]
      intent_type: "LEGAL_CONSULT"

    Output (refined for search):
      SearchKeywords {
        legal: ["임대차보호법", "전세금 인상", "5% 상한"],
        entities: {"percentage": "5%"}
      }
    """
    result = await self.llm_service.complete_json_async(
        prompt_name="keyword_refinement_for_search",
        variables={
            "query": query,
            "base_keywords": ", ".join(base_keywords),
            "intent_type": intent_type
        }
    )
    return result
```

### Phase 3: Planning → Search 정보 전달

```python
# team_supervisor.py
async def execute_teams(self, state: MainSupervisorState):
    """팀 실행"""
    intent_result = state["planning_state"]["analyzed_intent"]

    # SearchExecutor에 IntentResult 전달
    search_result = await self.search_executor.execute(
        query=state["query"],
        intent_result=intent_result  # ← 정보 전달!
    )
```

### Phase 4: 프롬프트 개선 (정제에 집중)

```
# keyword_refinement_for_search.txt
당신은 검색 전문가입니다.
Planning Agent가 분석한 의도와 키워드를 받아서,
검색 실행에 최적화된 구체적인 키워드로 정제하세요.

## Planning의 분석
- 의도: {intent_type}
- 기본 키워드: {base_keywords}

## 사용자 질문
{query}

## 검색 키워드 정제 가이드
1. Planning의 키워드를 기반으로 함 (중복 분석 X)
2. 검색 도메인에 특화된 용어로 확장
3. 법률 검색: 법률명, 조항, 판례 용어
4. 시세 검색: 지역, 물건 유형, 가격대
5. 대출 검색: 대출 상품명, 금리 조건

JSON 출력:
{
  "legal": [...],
  "real_estate": [...],
  "loan": [...],
  "entities": {...}
}
```

---

## 🎯 핵심 요약

### ❌ 잘못된 이해

1. "Execution Agent는 LLM 호출하면 안 된다"
2. "키워드 추출은 Planning에서만 해야 한다"
3. "SearchExecutor는 Tool처럼 동작해야 한다"

### ✅ 올바른 이해

1. **Agent는 모두 LLM을 사용한다** (Cognitive든 Execution이든)
2. **각 Agent는 자신의 레벨에서 자율적으로 결정한다**
   - Planning: 전략적 결정 (What, Which team)
   - Execution: 전술적 결정 (How, Which tool, Specific keywords)
3. **Agent 간 정보 전달을 강화해야 한다** (중복 방지)

### 🚀 실제 해결책

1. **State 구조 확장**: Planning 결과를 Execution에 전달
2. **키워드 정제**: Planning 키워드를 Search 키워드로 정제 (새로 추출 X)
3. **프롬프트 개선**: "정제"에 집중 (분석 X)

---

## 📚 참고: LangGraph Agent 패턴

### Agent Hierarchy (LangGraph 표준)

```
Supervisor (Meta-Agent)
    ├─ Agent 1 (LLM + Tools)
    │   ├─ Tool A
    │   └─ Tool B
    ├─ Agent 2 (LLM + Tools)
    │   └─ Tool C
    └─ Agent 3 (LLM + Tools)
        ├─ Tool D
        └─ Sub-Agent (LLM + Tools)
```

### 각 레벨의 역할

- **Meta-Agent (Supervisor)**: 전체 조율, Agent 선택
- **Agent**: 자율적 실행, Tool 선택, 결과 평가
- **Tool**: 수동적 실행, 결과 반환

### 핵심 원칙

> **"Agent는 생각하고, Tool은 실행한다"**

- Agent = Thinker (LLM 사용)
- Tool = Executor (LLM 사용 안 함)

---

**결론**: 현재 SearchExecutor가 LLM을 사용하는 것은 **올바르다**. 문제는 **Planning과 Search 간 정보 전달 부족**이다.
