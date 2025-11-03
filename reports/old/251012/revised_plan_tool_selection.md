# 수정된 Tool Selection 계획

## 🔴 기존 계획의 문제점

### 1. Agent별로 tool이 다른데 prompt는 1개
- SearchExecutor: 3개 tool (legal, market, loan)
- AnalysisExecutor: 5개 tool (contract, market, roi, loan, policy)
- DocumentExecutor: 문서 생성 tools
- **문제**: tool_selection.txt 1개만 있고 search_team 전용

### 2. 키워드 하드코딩
```python
# 여전히 하드코딩
variables={
    "legal_keywords": [...],
    "real_estate_keywords": [...],
    "loan_keywords": [...]
}
```
→ 키워드를 미리 분류하는 것 자체가 하드코딩!

---

## ✅ 올바른 접근 방식

### 핵심 원칙
1. **Agent별 prompt 분리**: 각 Agent가 사용하는 tool이 다르므로 prompt도 분리
2. **키워드 하드코딩 제거**: LLM에게 원본 쿼리만 주고 tool 선택하게 함
3. **동적 tool 정보 전달**: 실제 사용 가능한 tool을 런타임에 수집하여 전달

---

## 📦 수정된 구현 계획

### Step 1: Agent별 Tool Selection Prompt 생성

#### 1-1. Search Team Tool Selection
**파일**: `prompts/execution/tool_selection_search.txt`

```
당신은 Search Team의 Tool 선택 전문가입니다.

## 사용자 질문
{query}

## 사용 가능한 Tools
{available_tools}

## Tool 선택 기준
- 질문의 내용을 분석하여 필요한 tool만 선택
- 키워드가 아닌 질문의 의도를 파악
- 여러 tool이 필요하면 모두 선택

## 응답 형식 (JSON)
{
    "selected_tools": ["tool1", "tool2"],
    "reasoning": "선택 이유",
    "confidence": 0.9
}
```

#### 1-2. Analysis Team Tool Selection
**파일**: `prompts/execution/tool_selection_analysis.txt`

```
당신은 Analysis Team의 Tool 선택 전문가입니다.

## 사용자 질문
{query}

## 수집된 데이터
{collected_data_summary}

## 사용 가능한 Tools
{available_tools}

## Tool 선택 기준
- 수집된 데이터와 질문을 기반으로 필요한 분석 tool 선택
- 계약서 분석, 시장 분석, ROI 계산, 대출 시뮬레이션, 정책 매칭 중 선택

## 응답 형식 (JSON)
{
    "selected_tools": ["tool1", "tool2"],
    "reasoning": "선택 이유",
    "confidence": 0.9
}
```

---

### Step 2: 동적 Tool 정보 수집

각 Executor에서 실제 사용 가능한 tool 정보를 동적으로 수집:

```python
def _get_available_tools(self) -> Dict[str, Any]:
    """
    현재 Executor에서 사용 가능한 tool 정보를 동적으로 수집
    하드코딩 없이 실제 초기화된 tool만 반환
    """
    tools = {}

    # SearchExecutor 예시
    if self.legal_search_tool:
        tools["legal_search"] = {
            "name": "legal_search",
            "description": "법률 정보 검색 (전세법, 임대차보호법)",
            "capabilities": ["법률 조회", "판례 검색"],
            "available": True
        }

    if self.market_data_tool:
        tools["market_data"] = {
            "name": "market_data",
            "description": "부동산 시세 조회",
            "capabilities": ["매매가", "전세가", "월세"],
            "available": True
        }

    # 실제로 None이 아닌 tool만 반환
    return tools
```

---

### Step 3: LLM Tool 선택 수정

```python
async def _select_tools_with_llm(
    self,
    query: str
) -> Dict[str, Any]:
    """
    LLM을 사용한 tool 선택 (수정)

    변경사항:
    1. keywords 파라미터 제거 (하드코딩 제거)
    2. query만 전달
    3. available_tools를 동적으로 수집
    4. agent별 전용 prompt 사용
    """
    if not self.llm_service:
        return self._select_tools_with_fallback()

    try:
        # 동적으로 사용 가능한 tool 정보 수집
        available_tools = self._get_available_tools()

        # Agent별 전용 prompt 사용
        prompt_name = f"tool_selection_{self.team_name}"

        result = await self.llm_service.complete_json_async(
            prompt_name=prompt_name,
            variables={
                "query": query,  # 키워드 없이 원본 query만
                "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
            },
            temperature=0.1
        )

        return {
            "selected_tools": result.get("selected_tools", []),
            "reasoning": result.get("reasoning", ""),
            "confidence": result.get("confidence", 0.0)
        }

    except Exception as e:
        logger.error(f"LLM tool selection failed: {e}")
        return self._select_tools_with_fallback()
```

---

### Step 4: AnalysisExecutor에도 동일하게 적용

```python
# analysis_executor.py

async def _select_tools_with_llm(
    self,
    query: str,
    collected_data_summary: Dict = None
) -> Dict[str, Any]:
    """
    LLM을 사용한 분석 tool 선택
    """
    if not self.llm_service:
        return self._select_tools_with_fallback()

    try:
        # 동적으로 사용 가능한 분석 tool 정보 수집
        available_tools = self._get_available_analysis_tools()

        result = await self.llm_service.complete_json_async(
            prompt_name="tool_selection_analysis",
            variables={
                "query": query,
                "collected_data_summary": json.dumps(collected_data_summary or {}, ensure_ascii=False),
                "available_tools": json.dumps(available_tools, ensure_ascii=False, indent=2)
            },
            temperature=0.1
        )

        return {
            "selected_tools": result.get("selected_tools", []),
            "reasoning": result.get("reasoning", ""),
            "confidence": result.get("confidence", 0.0)
        }

    except Exception as e:
        logger.error(f"LLM analysis tool selection failed: {e}")
        return self._select_tools_with_fallback()

def _get_available_analysis_tools(self) -> Dict[str, Any]:
    """동적으로 분석 tool 정보 수집"""
    tools = {}

    if self.contract_tool:
        tools["contract_analysis"] = {
            "name": "contract_analysis",
            "description": "계약서 조항 분석 및 위험요소 탐지",
            "available": True
        }

    if self.market_tool:
        tools["market_analysis"] = {
            "name": "market_analysis",
            "description": "시장 동향 및 가격 적정성 분석",
            "available": True
        }

    if self.roi_tool:
        tools["roi_calculator"] = {
            "name": "roi_calculator",
            "description": "투자수익률 계산 및 현금흐름 분석",
            "available": True
        }

    if self.loan_tool:
        tools["loan_simulator"] = {
            "name": "loan_simulator",
            "description": "대출 한도 및 금리 시뮬레이션",
            "available": True
        }

    if self.policy_tool:
        tools["policy_matcher"] = {
            "name": "policy_matcher",
            "description": "정부 지원 정책 매칭 및 혜택 분석",
            "available": True
        }

    return tools
```

---

## 📁 수정된 파일 구조

```
llm_manager/prompts/execution/
├── tool_selection_search.txt       # Search Team 전용
├── tool_selection_analysis.txt     # Analysis Team 전용
└── tool_selection_document.txt     # Document Team 전용

execution_agents/
├── search_executor.py
│   ├── _get_available_tools()          # 동적 tool 정보 수집
│   └── _select_tools_with_llm(query)   # 키워드 제거
└── analysis_executor.py
    ├── _get_available_analysis_tools() # 동적 tool 정보 수집
    └── _select_tools_with_llm(query)   # 수집된 데이터 포함
```

---

## 🎯 개선 효과

### Before (잘못된 접근)
```
query → 키워드 추출 → 키워드 분류 → LLM(키워드로 tool 선택)
         ❌ 하드코딩    ❌ 하드코딩
```

### After (올바른 접근)
```
query → LLM(query + 동적 tool 정보 → tool 선택)
                     ✅ 런타임 수집
```

---

## 📝 핵심 변경사항 요약

1. **Prompt 분리**: Agent별로 3개 (search, analysis, document)
2. **키워드 제거**: query만 전달, 키워드 분류 로직 제거
3. **동적 tool 수집**: 하드코딩 대신 실제 초기화된 tool 정보만 전달
4. **Agent별 커스터마이징**: AnalysisExecutor는 수집된 데이터도 고려

---

이제 진짜 LLM이 "생각"해서 tool을 선택하게 됩니다!