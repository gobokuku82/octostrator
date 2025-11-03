# Agent / Tool 추가 구현 가이드

**작성일**: 2025-10-22
**예상 구현 시간**: 2-3일 (Agent/Tool별)
**난이도**: 🟢 낮음 (패턴 복사)
**사용 기능**: 기본 LangGraph (Checkpointer 불필요)

---

## 구현 개요

새로운 Agent나 Tool을 추가하는 것은 **기존 패턴을 복사**하면 되므로 간단합니다.

### 추가 유형

1. **Tool 추가**: 새로운 데이터 소스나 기능 (예: 날씨 API, 뉴스 검색)
2. **Executor 추가**: 새로운 팀/작업 단위 (예: ReportingTeam, NotificationTeam)

---

## service_agent 폴더 구조

```
backend/app/service_agent/
├─ cognitive_agents/        # 계획/판단 Agent
│  ├─ planning_agent.py     # Intent 분석, Plan 생성
│  ├─ query_decomposer.py   # 쿼리 분해
│  └─ execution_orchestrator.py  # 실행 조율
│
├─ execution_agents/         # 실행 Executor (Team)
│  ├─ search_executor.py    # SearchTeam
│  ├─ document_executor.py  # DocumentTeam
│  └─ analysis_executor.py  # AnalysisTeam
│
├─ tools/                    # 실제 작업 Tool
│  ├─ hybrid_legal_search.py    # 법률 검색
│  ├─ market_data_tool.py       # 시세 조회
│  ├─ real_estate_search_tool.py  # 매물 검색
│  ├─ loan_data_tool.py         # 대출 정보
│  ├─ market_analysis_tool.py   # 시장 분석
│  ├─ roi_calculator_tool.py    # ROI 계산
│  └─ ... (더 추가 가능)
│
├─ supervisor/               # 최상위 조율자
│  └─ team_supervisor.py    # MainSupervisor
│
├─ foundation/               # 기반 클래스
│  ├─ agent_registry.py     # Agent 등록소
│  ├─ agent_adapter.py      # Agent 어댑터
│  ├─ checkpointer.py       # Checkpointer 설정
│  ├─ separated_states.py   # State 정의
│  └─ config.py             # 설정
│
└─ llm_manager/              # LLM 관리
   ├─ llm_service.py        # LLM 호출
   ├─ prompt_manager.py     # 프롬프트 관리
   └─ prompts/              # 프롬프트 파일
      ├─ cognitive/         # Planning용
      ├─ execution/         # Execution용
      └─ common/            # 공통
```

---

## 패턴 1: Tool 추가 (간단)

### 예시: 날씨 API Tool 추가

#### Step 1: Tool 클래스 생성 (15분)

**파일**: `backend/app/service_agent/tools/weather_tool.py` (신규)

```python
"""
날씨 정보 조회 Tool
"""
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class WeatherTool:
    """
    날씨 정보 조회 Tool
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: 날씨 API 키 (선택적)
        """
        self.api_key = api_key or "your_default_api_key"
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.name = "weather"

        logger.info("WeatherTool initialized")

    async def get_weather(
        self,
        location: str,
        days: int = 1
    ) -> Dict[str, Any]:
        """
        날씨 정보 조회

        Args:
            location: 지역명 (예: "서울", "Seoul")
            days: 예보 일수 (1~7일)

        Returns:
            날씨 정보 딕셔너리
        """
        try:
            logger.info(f"Fetching weather for {location}, {days} days")

            # API 호출
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "q": location,
                        "appid": self.api_key,
                        "units": "metric",  # 섭씨
                        "cnt": days * 8,  # 3시간 단위 → 8개/일
                        "lang": "kr"
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Weather API error: {response.status_code}")
                    return {
                        "status": "error",
                        "error": f"API returned {response.status_code}"
                    }

                data = response.json()

            # 결과 파싱
            forecasts = []
            for item in data.get("list", [])[:days * 8:8]:  # 하루에 1개씩
                forecasts.append({
                    "date": item["dt_txt"][:10],
                    "temp": item["main"]["temp"],
                    "temp_min": item["main"]["temp_min"],
                    "temp_max": item["main"]["temp_max"],
                    "description": item["weather"][0]["description"],
                    "humidity": item["main"]["humidity"],
                    "wind_speed": item["wind"]["speed"]
                })

            return {
                "status": "success",
                "location": location,
                "forecasts": forecasts,
                "count": len(forecasts)
            }

        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "location": location
            }

    async def search(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """
        통합 인터페이스 (다른 Tool과 동일한 인터페이스)

        Args:
            query: 검색 쿼리 (지역명 추출)
            params: 검색 파라미터

        Returns:
            날씨 정보
        """
        params = params or {}

        # 쿼리에서 지역명 추출 (간단한 패턴)
        location = params.get("location")
        if not location:
            # 쿼리에서 추출
            for city in ["서울", "부산", "대구", "인천", "광주", "대전", "울산"]:
                if city in query:
                    location = city
                    break

        if not location:
            location = "서울"  # 기본값

        days = params.get("days", 1)

        return await self.get_weather(location, days)
```

**코드 라인 수**: 120줄

---

#### Step 2: Executor에 Tool 등록 (10분)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`

**수정 위치**: `__init__()` 메서드 (Line 56-96)

```python
def __init__(self, llm_context=None):
    # ... 기존 코드 ...

    # 🆕 WeatherTool 초기화
    self.weather_tool = None

    try:
        from app.service_agent.tools.weather_tool import WeatherTool
        self.weather_tool = WeatherTool()
        logger.info("WeatherTool initialized successfully")
    except Exception as e:
        logger.warning(f"WeatherTool initialization failed: {e}")
```

**코드 라인 수**: 10줄

---

#### Step 3: Tool 선택 로직에 추가 (10분)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`

**수정 위치**: `_get_available_tools()` 메서드 (Line 246-308)

```python
def _get_available_tools(self) -> Dict[str, Any]:
    """사용 가능한 Tool 정보"""
    tools = {}

    # ... 기존 Tool들 ...

    # 🆕 WeatherTool 추가
    if self.weather_tool:
        tools["weather"] = {
            "name": "weather",
            "description": "날씨 정보 조회 (현재 날씨, 예보)",
            "capabilities": [
                "현재 날씨 조회",
                "7일 예보",
                "기온/습도/풍속",
                "지역별 날씨"
            ],
            "available": True
        }

    return tools
```

**코드 라인 수**: 15줄

---

#### Step 4: Tool 실행 로직 추가 (20분)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`

**수정 위치**: `execute_search_node()` 메서드 (Line 453-777)

```python
async def execute_search_node(self, state: SearchTeamState) -> SearchTeamState:
    # ... 기존 검색 로직들 (legal, market, loan) ...

    # 🆕 날씨 검색 추가
    if "weather" in selected_tools and self.weather_tool:
        try:
            logger.info("[SearchTeam] Executing weather search")

            # 날씨 검색 실행
            result = await self.weather_tool.search(query, {})

            if result.get("status") == "success":
                weather_data = result.get("forecasts", [])

                # 결과 저장
                state["weather_results"] = weather_data
                state["search_progress"]["weather_search"] = "completed"
                logger.info(f"[SearchTeam] Weather search completed: {len(weather_data)} days")
                execution_results["weather"] = {
                    "status": "success",
                    "result_count": len(weather_data)
                }
            else:
                state["search_progress"]["weather_search"] = "failed"
                execution_results["weather"] = {
                    "status": "failed",
                    "error": result.get('status')
                }

        except Exception as e:
            logger.error(f"Weather search failed: {e}")
            state["search_progress"]["weather_search"] = "failed"
            execution_results["weather"] = {
                "status": "error",
                "error": str(e)
            }

    return state
```

**코드 라인 수**: 35줄

---

#### Step 5: State 정의 확장 (5분)

**파일**: `backend/app/service_agent/foundation/separated_states.py`

**수정 위치**: `SearchTeamState` 클래스

```python
class SearchTeamState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # 🆕 날씨 검색 결과
    weather_results: List[Dict]
```

**코드 라인 수**: 3줄

---

#### Step 6: 테스트 (10분)

**파일**: `backend/tests/test_weather_tool.py` (신규)

```python
import pytest
from app.service_agent.tools.weather_tool import WeatherTool


@pytest.mark.asyncio
async def test_weather_tool():
    """WeatherTool 기본 테스트"""
    tool = WeatherTool(api_key="test_key")

    result = await tool.get_weather("서울", days=3)

    assert result["status"] in ["success", "error"]
    if result["status"] == "success":
        assert "forecasts" in result
        assert result["location"] == "서울"


@pytest.mark.asyncio
async def test_weather_search_interface():
    """통합 search 인터페이스 테스트"""
    tool = WeatherTool()

    result = await tool.search("서울 날씨 알려줘", {})

    assert result is not None
    assert "status" in result
```

**코드 라인 수**: 30줄

---

### Tool 추가 총 정리

| 단계 | 파일 | 코드 라인 | 시간 |
|------|------|-----------|------|
| 1. Tool 클래스 생성 | `tools/weather_tool.py` | 120줄 | 15분 |
| 2. Executor 등록 | `search_executor.py` (__init__) | 10줄 | 10분 |
| 3. Tool 선택 로직 | `search_executor.py` (_get_available_tools) | 15줄 | 10분 |
| 4. 실행 로직 추가 | `search_executor.py` (execute_search_node) | 35줄 | 20분 |
| 5. State 확장 | `separated_states.py` | 3줄 | 5분 |
| 6. 테스트 작성 | `tests/test_weather_tool.py` | 30줄 | 10분 |
| **합계** | **6개 파일** | **213줄** | **70분 (1.2시간)** |

---

## 패턴 2: Executor (Team) 추가 (중간)

### 예시: ReportingTeam 추가

#### Step 1: State 정의 (10분)

**파일**: `backend/app/service_agent/foundation/separated_states.py`

```python
class ReportingTeamState(TypedDict, total=False):
    """ReportingTeam 상태"""
    team_name: str
    status: str  # pending, in_progress, completed, failed
    shared_context: SharedState

    # 입력
    report_type: str  # "summary", "detailed", "comparison"
    data_sources: List[str]  # ["search", "analysis", "document"]

    # 처리
    collected_data: Dict[str, Any]
    report_sections: List[Dict]

    # 출력
    generated_report: Dict[str, Any]
    report_format: str  # "markdown", "json", "pdf"

    # 메타
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    report_time: float
    error: Optional[str]
```

**코드 라인 수**: 25줄

---

#### Step 2: Executor 클래스 생성 (2시간)

**파일**: `backend/app/service_agent/execution_agents/reporting_executor.py` (신규)

```python
"""
Reporting Executor - 보고서 생성 Agent
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

from app.service_agent.foundation.separated_states import ReportingTeamState, SharedState
from app.service_agent.llm_manager import LLMService

logger = logging.getLogger(__name__)


class ReportingExecutor:
    """
    보고서 생성 Executor
    """

    def __init__(self, llm_context=None):
        self.llm_context = llm_context
        self.llm_service = LLMService(llm_context=llm_context)
        self.team_name = "reporting"

        # 서브그래프 구성
        self.app = None
        self._build_subgraph()

    def _build_subgraph(self):
        """서브그래프 구성"""
        workflow = StateGraph(ReportingTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_node)
        workflow.add_node("collect", self.collect_data_node)
        workflow.add_node("generate", self.generate_report_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 구성
        workflow.add_edge(START, "prepare")
        workflow.add_edge("prepare", "collect")
        workflow.add_edge("collect", "generate")
        workflow.add_edge("generate", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("ReportingTeam subgraph built")

    async def prepare_node(self, state: ReportingTeamState) -> ReportingTeamState:
        """준비 노드"""
        logger.info("[ReportingTeam] Preparing")

        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()

        # 보고서 타입 기본값
        if not state.get("report_type"):
            state["report_type"] = "summary"

        # 데이터 소스 기본값
        if not state.get("data_sources"):
            state["data_sources"] = ["search", "analysis"]

        return state

    async def collect_data_node(self, state: ReportingTeamState) -> ReportingTeamState:
        """데이터 수집 노드"""
        logger.info("[ReportingTeam] Collecting data")

        collected = {}
        shared_context = state.get("shared_context", {})
        data_sources = state.get("data_sources", [])

        # SearchTeam 결과 수집
        if "search" in data_sources:
            search_state = shared_context.get("search_team_state", {})
            collected["search_results"] = {
                "legal": search_state.get("legal_results", []),
                "real_estate": search_state.get("real_estate_results", []),
                "loan": search_state.get("loan_results", [])
            }

        # AnalysisTeam 결과 수집
        if "analysis" in data_sources:
            analysis_state = shared_context.get("analysis_team_state", {})
            collected["analysis_results"] = analysis_state.get("insights", [])

        state["collected_data"] = collected
        logger.info(f"[ReportingTeam] Collected {len(collected)} data sources")

        return state

    async def generate_report_node(self, state: ReportingTeamState) -> ReportingTeamState:
        """보고서 생성 노드"""
        logger.info("[ReportingTeam] Generating report")

        report_type = state.get("report_type", "summary")
        collected_data = state.get("collected_data", {})

        # 보고서 섹션 구성
        sections = []

        # 1. 요약 섹션
        sections.append({
            "title": "요약",
            "content": self._generate_summary(collected_data)
        })

        # 2. 세부 섹션 (타입별)
        if report_type == "detailed":
            if "search_results" in collected_data:
                sections.append({
                    "title": "검색 결과",
                    "content": self._format_search_results(collected_data["search_results"])
                })

            if "analysis_results" in collected_data:
                sections.append({
                    "title": "분석 결과",
                    "content": self._format_analysis_results(collected_data["analysis_results"])
                })

        state["report_sections"] = sections

        # 최종 보고서 생성
        state["generated_report"] = {
            "title": f"{report_type.upper()} 보고서",
            "created_at": datetime.now().isoformat(),
            "sections": sections,
            "total_sections": len(sections)
        }

        logger.info(f"[ReportingTeam] Generated report with {len(sections)} sections")

        return state

    async def finalize_node(self, state: ReportingTeamState) -> ReportingTeamState:
        """최종화 노드"""
        logger.info("[ReportingTeam] Finalizing")

        state["end_time"] = datetime.now()

        if state.get("start_time"):
            elapsed = (state["end_time"] - state["start_time"]).total_seconds()
            state["report_time"] = elapsed

        state["status"] = "completed"

        return state

    def _generate_summary(self, data: Dict) -> str:
        """요약 생성 (간단한 버전)"""
        search_count = sum(len(v) for v in data.get("search_results", {}).values())
        analysis_count = len(data.get("analysis_results", []))

        return f"총 {search_count}개 검색 결과, {analysis_count}개 분석 결과를 수집했습니다."

    def _format_search_results(self, results: Dict) -> str:
        """검색 결과 포맷"""
        formatted = []

        for category, items in results.items():
            formatted.append(f"### {category.upper()}")
            formatted.append(f"- 결과 수: {len(items)}")

        return "\n".join(formatted)

    def _format_analysis_results(self, results: List) -> str:
        """분석 결과 포맷"""
        return f"총 {len(results)}개의 인사이트가 도출되었습니다."

    async def execute(
        self,
        shared_state: SharedState,
        report_type: str = "summary",
        data_sources: List[str] = None
    ) -> ReportingTeamState:
        """
        ReportingTeam 실행
        """
        initial_state = ReportingTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            report_type=report_type,
            data_sources=data_sources or ["search", "analysis"],
            collected_data={},
            report_sections=[],
            generated_report={},
            report_format="markdown",
            start_time=None,
            end_time=None,
            report_time=0.0,
            error=None
        )

        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"ReportingTeam execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["error"] = str(e)
            return initial_state
```

**코드 라인 수**: 230줄

---

#### Step 3: MainSupervisor 통합 (30분)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**수정 1: Executor 초기화 (10줄)**

```python
from app.service_agent.execution_agents.reporting_executor import ReportingExecutor

class TeamSupervisor:
    def __init__(self, ...):
        # ... 기존 Executor들 ...

        # 🆕 ReportingExecutor 초기화
        self.reporting_executor = ReportingExecutor(llm_context=llm_context)
```

**수정 2: Graph에 노드 추가 (20줄)**

```python
def build_graph(self):
    graph = StateGraph(MainSupervisorState)

    # 노드 추가
    graph.add_node("initialize", self.initialize_node)
    graph.add_node("planning", self.planning_node)
    graph.add_node("search_team", self.search_team_node)
    graph.add_node("analysis_team", self.analysis_team_node)
    graph.add_node("reporting_team", self.reporting_team_node)  # 🆕 추가
    graph.add_node("response", self.response_generation_node)

    # 엣지 추가
    graph.add_edge("analysis_team", "reporting_team")  # 🆕 추가
    graph.add_edge("reporting_team", "response")

    return graph.compile(checkpointer=self.checkpointer)
```

**수정 3: 실행 노드 추가 (40줄)**

```python
async def reporting_team_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """ReportingTeam 실행 노드"""
    logger.info("=" * 50)
    logger.info("📊 [ReportingTeam] Starting")
    logger.info("=" * 50)

    try:
        plan = state.get("execution_plan", {})
        report_type = plan.get("report_type", "summary")

        # ReportingExecutor 실행
        result = await self.reporting_executor.execute(
            shared_state=state,
            report_type=report_type,
            data_sources=["search", "analysis"]
        )

        # 결과 저장
        state["reporting_team_state"] = result

        logger.info(f"✅ ReportingTeam completed: {result.get('status')}")

        # WebSocket 알림
        await self._send_websocket_message({
            "type": "reporting_complete",
            "session_id": state.get("session_id"),
            "sections": result.get("report_sections", [])
        })

    except Exception as e:
        logger.error(f"❌ ReportingTeam error: {e}")
        state["reporting_team_state"] = {
            "status": "failed",
            "error": str(e)
        }

    return state
```

**총 코드 라인 수**: 70줄

---

#### Step 4: PlanningAgent 수정 (10분)

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

```python
async def generate_plan(...):
    # ... 기존 로직 ...

    # 🆕 보고서 생성 요청 시
    if intent_type == "report_request":
        return {
            "steps": [
                {"order": 1, "team": "search"},
                {"order": 2, "team": "analysis"},
                {"order": 3, "team": "reporting"}  # 🆕 추가
            ],
            "report_type": "detailed"  # or "summary"
        }
```

**코드 라인 수**: 15줄

---

### Executor 추가 총 정리

| 단계 | 파일 | 코드 라인 | 시간 |
|------|------|-----------|------|
| 1. State 정의 | `separated_states.py` | 25줄 | 10분 |
| 2. Executor 생성 | `reporting_executor.py` | 230줄 | 2시간 |
| 3. Supervisor 통합 | `team_supervisor.py` | 70줄 | 30분 |
| 4. Planning 수정 | `planning_agent.py` | 15줄 | 10분 |
| **합계** | **4개 파일** | **340줄** | **2.8시간** |

---

## 체크리스트

### ✅ Tool 추가 시

- [ ] `tools/{tool_name}_tool.py` 생성
- [ ] Tool 클래스 작성 (async search() 메서드 필수)
- [ ] Executor의 `__init__()`에 Tool 초기화
- [ ] `_get_available_tools()`에 Tool 정보 추가
- [ ] `execute_search_node()`에 실행 로직 추가
- [ ] `SearchTeamState`에 결과 필드 추가
- [ ] 테스트 코드 작성

### ✅ Executor 추가 시

- [ ] `separated_states.py`에 State 정의
- [ ] `execution_agents/{executor_name}.py` 생성
- [ ] Executor 클래스 작성 (서브그래프 구성)
- [ ] `team_supervisor.py`에 Executor 초기화
- [ ] Graph에 노드 추가
- [ ] Graph에 엣지 연결
- [ ] 실행 노드 작성
- [ ] `planning_agent.py`에 Plan 로직 추가
- [ ] 테스트 코드 작성

---

## 예시: 실제 추가된 Tool

### RealEstateSearchTool (이미 구현됨)

**위치**: `tools/real_estate_search_tool.py`

**Executor 등록**: `search_executor.py`
- Line 59: `self.real_estate_search_tool = None`
- Line 91-95: 초기화
- Line 279-293: `_get_available_tools()`에 추가
- Line 614-701: `execute_search_node()`에 실행 로직

**State 확장**: `separated_states.py`
- Line 887: `property_search_results: List[Dict]`

**코드 총량**: ~350줄

---

## 주의사항

### ⚠️ 공통 인터페이스

모든 Tool은 **동일한 인터페이스**를 제공해야 합니다:

```python
async def search(self, query: str, params: Dict = None) -> Dict[str, Any]:
    """
    Returns:
        {
            "status": "success" | "error",
            "data": [...],  # 결과 데이터
            "count": 10,    # 결과 수
            "error": "..."  # 에러 메시지 (실패 시)
        }
    """
```

### ⚠️ 에러 처리

Tool/Executor는 **절대 예외를 던지지 말고** 에러를 dict로 반환:

```python
try:
    # Tool 작업
    return {"status": "success", "data": results}
except Exception as e:
    logger.error(f"Tool failed: {e}")
    return {"status": "error", "error": str(e)}
```

### ⚠️ LLM Service 사용

LLM이 필요한 Tool은 `LLMService`를 주입받아 사용:

```python
from app.service_agent.llm_manager import LLMService

class MyTool:
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()
```

---

## 테스트 방법

### 1. 단위 테스트

```bash
cd backend
pytest tests/test_weather_tool.py -v
```

### 2. 통합 테스트

```python
# 직접 실행
from app.service_agent.execution_agents.search_executor import SearchExecutor

executor = SearchExecutor()
result = await executor.execute(
    shared_state={"query": "서울 날씨"},
    search_scope=["weather"]
)

print(result["weather_results"])
```

### 3. E2E 테스트 (WebSocket)

프론트엔드에서:
```
1. "서울 날씨 알려줘" → WeatherTool 실행 확인
2. 로그에서 "Weather search completed" 확인
3. 응답에 날씨 정보 포함 확인
```

---

## 추가 참고 사항

### 기존 Tool 참고

- **간단한 Tool**: `market_data_tool.py` (~200줄)
- **복잡한 Tool**: `market_analysis_tool.py` (~700줄)
- **DB 연동 Tool**: `real_estate_search_tool.py` (~400줄)

### 기존 Executor 참고

- **간단한 Executor**: `document_executor.py` (~300줄)
- **복잡한 Executor**: `search_executor.py` (~900줄)
- **분석 Executor**: `analysis_executor.py` (~500줄)

---

## 구현 통계 요약

| 추가 유형 | 파일 수 | 코드 라인 | 예상 시간 |
|-----------|---------|-----------|-----------|
| **Tool 추가** | 6개 | ~213줄 | 1-2시간 |
| **Executor 추가** | 4개 | ~340줄 | 2-3시간 |

---

## 다음 추가 추천 Tool/Executor

### 추천 Tool

1. **NewsSearchTool**: 부동산 뉴스 검색
2. **SchoolInfoTool**: 학군 정보 조회
3. **TransportationTool**: 교통 편의성 분석
4. **CrimeTool**: 치안 정보 조회
5. **PricePredictionTool**: ML 기반 가격 예측

### 추천 Executor

1. **ComparisonTeam**: 여러 매물 비교
2. **RecommendationTeam**: 추천 시스템
3. **NotificationTeam**: 알림 발송
4. **ReportingTeam**: 보고서 생성 (위 예시)

---

**마지막 업데이트**: 2025-10-22
**작성자**: Claude Code
**상태**: 📋 가이드 완료
**난이도**: 🟢 매우 쉬움 (패턴 복사)
