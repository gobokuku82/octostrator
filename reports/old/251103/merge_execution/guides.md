
7 files changed
+563
-49
lines changed
Search within code
 
‎backend/app/service_agent/cognitive_agents/planning_agent.py‎
+3
-1
Lines changed: 3 additions & 1 deletion
Original file line number	Diff line number	Diff line change
@@ -191,7 +191,9 @@ async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> Intent
                max_tokens=500    # 불필요하게 긴 reasoning 방지
            )

            logger.info(f"LLM Intent Analysis Result: {result}")
            # JSON 직렬화하여 로깅 (object object 출력 방지)
            import json
            logger.info(f"LLM Intent Analysis Result: {json.dumps(result, ensure_ascii=False)}")

            # Intent 타입 파싱
            intent_str = result.get("intent", "UNCLEAR").upper()
‎backend/app/service_agent/execution_agents/analysis_executor.py‎
+52
-2
Lines changed: 52 additions & 2 deletions
Original file line number	Diff line number	Diff line change
@@ -33,7 +33,8 @@
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool
    PolicyMatcherTool,
    LegalSearch
)

logger = logging.getLogger(__name__)
@@ -57,6 +58,7 @@ def __init__(self, llm_context=None):
        self.roi_tool = ROICalculatorTool()
        self.loan_tool = LoanSimulatorTool()
        self.policy_tool = PolicyMatcherTool()
        self.legal_search_tool = LegalSearch()

        # Decision Logger 초기화
        try:
@@ -153,6 +155,19 @@ def _get_available_analysis_tools(self) -> Dict[str, Any]:
                "available": True
            }

        if self.legal_search_tool:
            tools["legal_search"] = {
                "name": "legal_search",
                "description": "법률 및 시행령 검색, 법률 조항 분석",
                "capabilities": [
                    "법률 조문 검색",
                    "시행령 검색",
                    "부동산 관련 법률 조회",
                    "법률 해석 및 적용"
                ],
                "available": True
            }
        return tools

    async def _select_tools_with_llm(
@@ -196,7 +211,9 @@ async def _select_tools_with_llm(
                temperature=0.1
            )

            logger.info(f"LLM Analysis Tool Selection: {result}")
            # JSON 직렬화하여 로깅 (object object 출력 방지)
            import json
            logger.info(f"LLM Analysis Tool Selection: {json.dumps(result, ensure_ascii=False)}")

            selected_tools = result.get("selected_tools", [])
            reasoning = result.get("reasoning", "")
@@ -480,6 +497,39 @@ async def analyze_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState
                        "error": str(e)
                    }

            if "legal_search" in selected_tools:
                try:
                    legal_data = preprocessed_data.get("legal_search")
                    if legal_data:
                        # LegalSearch는 이미 검색 결과를 legal_data에 가지고 있으므로
                        # 해당 결과를 분석하여 인사이트 생성
                        results["legal"] = await self.legal_search_tool.search(
                            query=query,
                            params={"mode": "hybrid", "limit": 5}
                        )
                        logger.info("[AnalysisTools] Legal search analysis completed")
                        execution_results["legal_search"] = {
                            "status": "success",
                            "has_result": bool(results["legal"])
                        }
                    else:
                        # 데이터가 없어도 직접 검색 수행
                        results["legal"] = await self.legal_search_tool.search(
                            query=query,
                            params={"mode": "hybrid", "limit": 5}
                        )
                        logger.info("[AnalysisTools] Legal search performed directly")
                        execution_results["legal_search"] = {
                            "status": "success",
                            "has_result": bool(results["legal"])
                        }
                except Exception as e:
                    logger.error(f"Legal search analysis failed: {e}")
                    execution_results["legal_search"] = {
                        "status": "error",
                        "error": str(e)
                    }
            # 맞춤 분석 (전세금 인상률 등)
            results["custom"] = self._perform_custom_analysis(query, preprocessed_data)
            if results["custom"]["type"] != "general":
‎backend/app/service_agent/execution_agents/search_executor.py‎
+359
-11
Lines changed: 359 additions & 11 deletions
Large diffs are not rendered by default.
‎backend/app/service_agent/foundation/agent_registry.py‎
+3
-1
Lines changed: 3 additions & 1 deletion
Original file line number	Diff line number	Diff line change
@@ -364,4 +364,6 @@ def execute(self, input_data):
    agent = AgentRegistry.create_agent("test_agent", config={"test": True})
    if agent:
        result = agent.execute({"query": "test"})
        print(f"Execution result: {result}")
        # JSON 직렬화하여 출력 (object object 방지)
        import json
        print(f"Execution result: {json.dumps(result, ensure_ascii=False, indent=2)}")
‎backend/app/service_agent/foundation/decision_logger.py‎
+46
-33
Lines changed: 46 additions & 33 deletions
Original file line number	Diff line number	Diff line change
@@ -330,40 +330,53 @@ def get_tool_usage_stats(
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # 조건 설정
            where_clause = ""
            params = []
            # SQL Injection 방지: where_clause를 안전하게 구성
            # agent_type이 있으면 parameterized query 사용
            if agent_type:
                where_clause = "WHERE agent_type = ?"
                params.append(agent_type)
            # 전체 결정 수
            cursor.execute(f"""
                SELECT COUNT(*) FROM tool_decisions {where_clause}
            """, params)
            total_decisions = cursor.fetchone()[0]
            # 도구별 빈도
            cursor.execute(f"""
                SELECT selected_tools FROM tool_decisions {where_clause}
            """, params)
            tool_frequency = {}
            for row in cursor.fetchall():
                tools = json.loads(row[0])
                for tool in tools:
                    tool_frequency[tool] = tool_frequency.get(tool, 0) + 1
            # 평균 confidence
            cursor.execute(f"""
                SELECT AVG(confidence) FROM tool_decisions {where_clause}
            """, params)
            avg_confidence = cursor.fetchone()[0] or 0.0
            # 성공률
            cursor.execute(f"""
                SELECT AVG(success) FROM tool_decisions {where_clause}
            """, params)
            success_rate = cursor.fetchone()[0] or 0.0
                # 전체 결정 수
                cursor.execute("""
                    SELECT COUNT(*) FROM tool_decisions WHERE agent_type = ?
                """, (agent_type,))
                total_decisions = cursor.fetchone()[0]
                # 도구별 빈도
                cursor.execute("""
                    SELECT selected_tools FROM tool_decisions WHERE agent_type = ?
                """, (agent_type,))
                tool_frequency = {}
                for row in cursor.fetchall():
                    tools = json.loads(row[0])
                    for tool in tools:
                        tool_frequency[tool] = tool_frequency.get(tool, 0) + 1
                # 평균 confidence
                cursor.execute("""
                    SELECT AVG(confidence) FROM tool_decisions WHERE agent_type = ?
                """, (agent_type,))
                avg_confidence = cursor.fetchone()[0] or 0.0
                # 성공률
                cursor.execute("""
                    SELECT AVG(success) FROM tool_decisions WHERE agent_type = ?
                """, (agent_type,))
                success_rate = cursor.fetchone()[0] or 0.0
            else:
                # agent_type이 없으면 전체 조회
                cursor.execute("SELECT COUNT(*) FROM tool_decisions")
                total_decisions = cursor.fetchone()[0]
                cursor.execute("SELECT selected_tools FROM tool_decisions")
                tool_frequency = {}
                for row in cursor.fetchall():
                    tools = json.loads(row[0])
                    for tool in tools:
                        tool_frequency[tool] = tool_frequency.get(tool, 0) + 1
                cursor.execute("SELECT AVG(confidence) FROM tool_decisions")
                avg_confidence = cursor.fetchone()[0] or 0.0
                cursor.execute("SELECT AVG(success) FROM tool_decisions")
                success_rate = cursor.fetchone()[0] or 0.0

            conn.close()

‎backend/app/service_agent/foundation/separated_states.py‎
+2
Lines changed: 2 additions & 0 deletions
Original file line number	Diff line number	Diff line change
@@ -93,6 +93,8 @@ class SearchTeamState(TypedDict):
    real_estate_results: List[Dict[str, Any]]
    loan_results: List[Dict[str, Any]]
    property_search_results: List[Dict[str, Any]]  # 개별 매물 검색 결과 (RealEstateSearchTool)
    infrastructure_results: Optional[Dict[str, Any]]  # 주변 인프라 검색 결과 (InfrastructureTool)
    building_registry_results: List[Dict[str, Any]]  # 건축물 대장 검색 결과 (BuildingRegistryTool)
    aggregated_results: Dict[str, Any]

    # Metadata
‎backend/app/service_agent/llm_manager/prompts/execution/tool_selection_search.txt‎
+98
-1
Lines changed: 98 additions & 1 deletion
Original file line number	Diff line number	Diff line change
@@ -15,6 +15,13 @@
- 키워드가 아닌 문맥 이해

### 2. Tool 선택 기준
- **부동산 용어 정의가 필요한가?** → realestate_terminology
  * 용도: 부동산/대출 관련 **용어의 의미와 정의** 검색
  * 예: "DSR이 뭐야", "LTV란?", "가계약금이 뭐야", "임차권등기란", "분양권 의미"
  * 제공: 용어명, 카테고리, 정의, 법률 용어 여부
  * 키워드: "~이 뭐야", "~란?", "~의 뜻", "~의 의미", "용어 설명"
  * **중요**: 용어의 정의를 묻는 질문은 **반드시** 이 도구를 선택!
- **법률 정보가 필요한가?** → legal_search
  * 예: "전세금 인상률", "임차인 권리", "계약 조건", "법적 효력"

@@ -31,6 +38,19 @@
- **대출 정보가 필요한가?** → loan_data
  * 예: "대출 가능 금액", "금리", "LTV", "DTI"

- **주변 인프라 정보가 필요한가?** → infrastructure
  * 용도: 부동산 주변 지하철역, 학교, 편의시설 등 **인프라 정보**
  * 예: "에버그린 주변 지하철역", "역삼동 주변 학교", "강남구 아파트 근처 마트"
  * 제공: 지하철역, 초/중/고등학교, 마트, 병원, 약국, 거리 정보
  * 키워드: "주변", "근처", "인근", "지하철", "역", "학교", "마트", "편의시설", "인프라"
- **건축물 상세 정보가 필요한가?** → building_registry
  * 용도: 특정 주소의 **건축물 대장 정보** (건물 스펙)
  * 예: "서울시 강남구 역삼동 123-45 건축물 정보", "이 건물 면적", "층수 정보"
  * 제공: 건축물 면적, 지상/지하 층수, 준공년도, 건물 구조, 용도, 사용승인일
  * 키워드: "건축물", "건물 정보", "면적", "층수", "준공년도", "건물 구조", "용도"
  * **필수**: 주소 정보가 있어야 검색 가능 (시군구 + 읍면동 + 번지)
### 3. 복합 질문 처리
- 여러 종류의 정보가 필요하면 여러 tool 선택
- 예: "전세금 인상이 법적으로 가능한지, 시세는 얼마인지"
@@ -119,7 +139,29 @@
}
```

### 예시 8: 전체 종합
### 예시 8: 주변 인프라 검색
**질문**: "에버그린 주변 인프라 검색해줘"
**분석**: 특정 부동산의 주변 인프라 정보 필요
```json
{
    "selected_tools": ["infrastructure"],
    "reasoning": "에버그린 주변 인프라 정보 필요. infrastructure로 지하철역, 학교, 편의시설 검색",
    "confidence": 0.95
}
```
### 예시 9: 매물 + 인프라
**질문**: "강남구 아파트 중에 지하철역 가까운 곳 찾아줘"
**분석**: 매물 검색 + 인프라 정보 필요
```json
{
    "selected_tools": ["real_estate_search", "infrastructure"],
    "reasoning": "1) real_estate_search로 강남구 아파트 검색 2) infrastructure로 지하철역 근접성 확인",
    "confidence": 0.9
}
```
### 예시 10: 전체 종합
**질문**: "전세 계약 갱신할 건데 법적으로 어떻게 해야 하고, 시세는 어떻고, 대출도 가능한지 알려줘"
**분석**: 법률 + 시세 + 대출 모두 필요
```json
@@ -130,6 +172,61 @@
}
```

### 예시 11: 건축물 대장 검색
**질문**: "서울시 강남구 역삼동 123-45 건축물 정보 알려줘"
**분석**: 특정 주소의 건축물 대장 정보 필요
```json
{
    "selected_tools": ["building_registry"],
    "reasoning": "주소가 명확히 제공됨. building_registry로 건축물 면적, 층수, 준공년도 등 상세 스펙 조회",
    "confidence": 0.95
}
```
### 예시 12: 매물 + 건축물 정보
**질문**: "강남구 역삼동 아파트 찾고 건물 정보도 알려줘"
**분석**: 매물 검색 + 건축물 상세 정보 필요
```json
{
    "selected_tools": ["real_estate_search", "building_registry"],
    "reasoning": "1) real_estate_search로 역삼동 아파트 매물 검색 2) building_registry로 해당 건물의 상세 스펙 확인",
    "confidence": 0.9
}
```
### 예시 13: 용어 정의 검색
**질문**: "DSR이 뭐야?"
**분석**: 부동산/대출 용어의 정의를 묻는 질문
```json
{
    "selected_tools": ["realestate_terminology"],
    "reasoning": "DSR(부채상환비율)은 대출 관련 용어. '~이 뭐야' 패턴으로 용어 정의를 묻고 있으므로 realestate_terminology 선택",
    "confidence": 0.95
}
```
### 예시 14: 용어 + 실제 데이터
**질문**: "LTV가 뭔지 알려주고 내 경우는 어떤지 계산해줘"
**분석**: 용어 정의 + 대출 계산 필요
```json
{
    "selected_tools": ["realestate_terminology", "loan_data"],
    "reasoning": "1) realestate_terminology로 LTV 용어 설명 2) loan_data로 실제 LTV 계산 및 대출 가능 금액 조회",
    "confidence": 0.9
}
```
### 예시 15: 복합 용어 질문
**질문**: "임차권등기랑 전세권설정 차이가 뭐야?"
**분석**: 두 용어의 정의 및 비교 필요
```json
{
    "selected_tools": ["realestate_terminology"],
    "reasoning": "두 가지 임대차 관련 용어의 정의를 비교하는 질문. realestate_terminology로 두 용어 모두 검색 가능",
    "confidence": 0.95
}
```
## 응답 형식 (JSON)

반드시 아래 형식으로 응답하세요:
