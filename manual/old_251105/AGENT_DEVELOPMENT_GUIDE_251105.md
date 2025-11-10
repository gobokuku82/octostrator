# Agent 개발 가이드

**작성일**: 2025-11-05
**버전**: 2.0
**대상**: Agent 개발자

---

## 목차

1. [Agent 개발 개요](#1-agent-개발-개요)
2. [BaseAgent 상속](#2-baseagent-상속)
3. [LangGraph Workflow 구현](#3-langgraph-workflow-구현)
4. [Capability 정의](#4-capability-정의)
5. [State 관리](#5-state-관리)
6. [노드 구현](#6-노드-구현)
7. [Checkpoint 활용](#7-checkpoint-활용)
8. [테스트 및 디버깅](#8-테스트-및-디버깅)
9. [실전 예제](#9-실전-예제)

---

## 1. Agent 개발 개요

### 1.1 Agent란?

Agent는 특정 도메인의 작업을 수행하는 독립적인 실행 단위입니다:
- **LangGraph 기반**: StateGraph로 워크플로우 정의
- **BaseAgent 상속**: 표준 인터페이스 구현
- **Capability 제공**: 특정 능력 제공
- **Checkpoint 지원**: 상태 저장/복원 가능

### 1.2 개발 단계

```
1. 요구사항 분석 → 어떤 작업을 수행할 것인가?
2. State 정의 → 어떤 데이터가 필요한가?
3. Workflow 설계 → 작업 흐름은 어떻게 되는가?
4. 노드 구현 → 각 단계별 로직 구현
5. 테스트 → 단위 테스트 및 통합 테스트
6. 등록 → Agent Registry에 등록
```

---

## 2. BaseAgent 상속

### 2.1 기본 구조

```python
from backend.app.octostrator.agents.base.base_agent import BaseAgent, BaseAgentState
from backend.app.octostrator.agents.base.agent_registry import register_agent
from backend.app.octostrator.agents.base.capabilities import Capability

@register_agent("my_agent")  # 데코레이터로 자동 등록
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="my_agent",
            agent_name="My Custom Agent",
            description="Custom agent for specific tasks",
            enable_checkpoint=True,  # Checkpoint 사용 여부
            priority=AgentPriority.NORMAL,
            dependencies=[],  # 다른 Agent 의존성
            metadata={
                "version": "1.0",
                "author": "developer"
            }
        )

        # Agent capabilities 정의
        self.capabilities = [
            Capability.DATA_ANALYSIS.value,
            Capability.REPORT_GENERATION.value
        ]

        self.primary_capabilities = [
            Capability.DATA_ANALYSIS.value
        ]

    def build_graph(self, llm=None) -> StateGraph:
        """LangGraph workflow 구축 (필수 구현)"""
        pass

    async def process_task(self, task: Dict, context: Dict) -> Dict:
        """작업 처리 (필수 구현)"""
        pass
```

### 2.2 필수 메서드

| 메서드 | 설명 | 필수 |
|--------|------|------|
| `__init__()` | Agent 초기화 | ✅ |
| `build_graph()` | LangGraph 워크플로우 구축 | ✅ |
| `process_task()` | 작업 처리 로직 | ✅ |
| `get_info()` | Agent 정보 반환 | ❌ (BaseAgent 제공) |
| `validate_dependencies()` | 의존성 검증 | ❌ (BaseAgent 제공) |

---

## 3. LangGraph Workflow 구현

### 3.1 Graph 구축

```python
def build_graph(self, llm=None) -> StateGraph:
    """Agent의 LangGraph workflow 구축"""

    # LLM 설정
    self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    # StateGraph 생성
    workflow = StateGraph(MyAgentState)

    # 노드 추가
    workflow.add_node("validate_input", self.validate_input_node)
    workflow.add_node("process_data", self.process_data_node)
    workflow.add_node("generate_output", self.generate_output_node)

    # 엣지 추가 (흐름 정의)
    workflow.add_edge(START, "validate_input")
    workflow.add_edge("validate_input", "process_data")
    workflow.add_edge("process_data", "generate_output")
    workflow.add_edge("generate_output", END)

    # 조건부 엣지 (선택적)
    workflow.add_conditional_edges(
        "process_data",
        self.check_processing_result,
        {
            "success": "generate_output",
            "retry": "process_data",
            "error": END
        }
    )

    return workflow
```

### 3.2 Workflow 패턴

#### Sequential Pattern (순차)
```python
START → Node1 → Node2 → Node3 → END
```

#### Conditional Pattern (조건부)
```python
START → Check → {
    condition1: → NodeA → END
    condition2: → NodeB → END
    default: → NodeC → END
}
```

#### Loop Pattern (반복)
```python
START → Process → Check → {
    continue: → Process (loop)
    complete: → END
}
```

#### Parallel Pattern (병렬)
```python
START → Fork → {
    → NodeA →
    → NodeB →  } → Join → END
    → NodeC →
}
```

---

## 4. Capability 정의

### 4.1 표준 Capabilities

```python
from backend.app.octostrator.agents.base.capabilities import Capability

# 사용 가능한 표준 Capabilities
capabilities = [
    Capability.MEAL_PLANNING,      # 식단 계획
    Capability.NUTRITION_ANALYSIS, # 영양 분석
    Capability.EXERCISE_PLANNING,  # 운동 계획
    Capability.HEALTH_TRACKING,    # 건강 추적
    Capability.SCHEDULING,         # 일정 관리
    Capability.DATA_ANALYSIS,      # 데이터 분석
    Capability.REPORT_GENERATION,  # 보고서 생성
    # ... 더 많은 capabilities
]
```

### 4.2 Custom Capability

```python
# 커스텀 capability 정의
custom_capability = extend_capability(
    base_capability=Capability.DATA_ANALYSIS,
    extension="medical"
)
# 결과: "data_analysis_medical"

# Agent에서 사용
self.capabilities = [
    Capability.DATA_ANALYSIS.value,
    "data_analysis_medical"  # 커스텀
]
```

### 4.3 Capability 기반 라우팅

```python
# Execute Supervisor가 capability로 Agent 선택
router = CapabilityBasedRouter(agent_registry)

# 특정 capability를 가진 Agent 찾기
agent_id = router.find_best_agent("meal_planning", context)

# 대체 Agent 찾기
alternatives = router.find_alternative_agents("diet_agent", "meal_planning")
```

---

## 5. State 관리

### 5.1 State 정의

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class MyAgentState(BaseAgentState):
    """Agent의 State 정의"""

    # BaseAgentState에서 상속받는 기본 필드
    # - agent_id, agent_name, task, user_context, messages
    # - status, started_at, completed_at, error, result

    # Agent 고유 필드 추가
    input_data: Optional[Dict[str, Any]] = None
    processed_data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, bool]] = None
    output_format: str = "json"
    retry_count: int = 0
    max_retries: int = 3
```

### 5.2 State 업데이트

```python
async def process_node(self, state: MyAgentState) -> Dict[str, Any]:
    """노드에서 State 업데이트"""

    # 현재 state 읽기
    input_data = state.input_data

    # 처리
    processed = self.process_logic(input_data)

    # State 업데이트 반환
    return {
        "processed_data": processed,
        "status": "processing",
        "metadata": {
            **state.metadata,
            "processing_time": datetime.now().isoformat()
        }
    }
```

### 5.3 State 검증

```python
def validate_state(state: MyAgentState) -> bool:
    """State 유효성 검증"""

    # 필수 필드 확인
    if not state.task:
        return False

    # 비즈니스 로직 검증
    if state.retry_count > state.max_retries:
        return False

    return True
```

---

## 6. 노드 구현

### 6.1 노드 기본 구조

```python
async def node_name(self, state: MyAgentState) -> Dict[str, Any]:
    """노드 구현 기본 구조

    Args:
        state: 현재 Agent State

    Returns:
        State 업데이트 딕셔너리
    """
    try:
        # 1. State에서 필요한 데이터 추출
        input_data = state.input_data

        # 2. 비즈니스 로직 실행
        result = await self.business_logic(input_data)

        # 3. State 업데이트 반환
        return {
            "processed_data": result,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Node failed: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }
```

### 6.2 LLM 사용 노드

```python
async def generate_with_llm_node(self, state: MyAgentState) -> Dict[str, Any]:
    """LLM을 사용하는 노드"""

    # 프롬프트 생성
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="당신은 전문가입니다."),
        HumanMessage(content=f"다음을 분석하세요: {state.input_data}")
    ])

    # LLM 호출
    response = await self.llm.ainvoke(prompt.format_messages())

    # 결과 파싱
    try:
        result = json.loads(response.content)
    except:
        result = {"text": response.content}

    return {"processed_data": result}
```

### 6.3 외부 API 호출 노드

```python
async def fetch_external_data_node(self, state: MyAgentState) -> Dict[str, Any]:
    """외부 API 호출 노드"""

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.example.com/data",
            params={"id": state.task["params"]["id"]}
        ) as response:
            data = await response.json()

    return {"external_data": data}
```

### 6.4 조건부 노드

```python
def check_condition(self, state: MyAgentState) -> Literal["path1", "path2", "error"]:
    """조건 검사 함수"""

    if state.processed_data.get("score", 0) > 0.8:
        return "path1"
    elif state.processed_data.get("score", 0) > 0.5:
        return "path2"
    else:
        return "error"

# Graph에서 사용
workflow.add_conditional_edges(
    "process_node",
    self.check_condition,
    {
        "path1": "success_node",
        "path2": "retry_node",
        "error": "error_handler"
    }
)
```

---

## 7. Checkpoint 활용

### 7.1 Checkpoint 설정

```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="my_agent",
            enable_checkpoint=True  # Checkpoint 활성화
        )

# Agent 초기화 시 checkpointer 전달
agent = MyAgent()
await agent.initialize(
    llm=llm,
    checkpointer=AsyncPostgresSaver.from_conn_string(db_url)
)
```

### 7.2 Checkpoint 저장 시점

자동 저장 시점:
- 각 노드 실행 후
- 조건부 분기 전
- 에러 발생 시

### 7.3 Checkpoint 복원

```python
# 이전 상태에서 재개
config = {
    "configurable": {
        "thread_id": "session_123_my_agent"
    }
}

# 중단된 지점부터 재개
result = await agent.execute(task, context, thread_id="session_123")
```

### 7.4 Stateless vs Stateful

```python
# Stateless Agent (빠름, 단순)
class StatelessAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            enable_checkpoint=False  # Checkpoint 비활성화
        )

# Stateful Agent (복잡, 재개 가능)
class StatefulAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            enable_checkpoint=True  # Checkpoint 활성화
        )
```

---

## 8. 테스트 및 디버깅

### 8.1 단위 테스트

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_agent_initialization():
    """Agent 초기화 테스트"""
    agent = MyAgent()
    assert agent.agent_id == "my_agent"
    assert agent.enable_checkpoint == True

@pytest.mark.asyncio
async def test_node_execution():
    """노드 실행 테스트"""
    agent = MyAgent()
    state = MyAgentState(
        agent_id="my_agent",
        task={"type": "test"},
        input_data={"value": 10}
    )

    result = await agent.process_node(state)
    assert "processed_data" in result
    assert result["status"] == "success"
```

### 8.2 통합 테스트

```python
@pytest.mark.asyncio
async def test_full_workflow():
    """전체 워크플로우 테스트"""

    # Agent 초기화
    agent = MyAgent()
    await agent.initialize()

    # 실행
    result = await agent.execute(
        task={"type": "analyze", "params": {"data": [1, 2, 3]}},
        context={"session_id": "test_123"}
    )

    # 검증
    assert result["status"] == "completed"
    assert "result" in result
```

### 8.3 디버깅 도구

```python
# 로깅 레벨 설정
import logging
logging.basicConfig(level=logging.DEBUG)

# State 추적
async def debug_node(self, state: MyAgentState) -> Dict:
    logger.debug(f"=== Node: {self.__name__} ===")
    logger.debug(f"Input State: {state.dict()}")

    result = await self.actual_logic(state)

    logger.debug(f"Output: {result}")
    return result

# Graph 시각화
from langgraph.graph import visualize
graph_image = visualize(workflow)
```

### 8.4 성능 모니터링

```python
import time
from functools import wraps

def monitor_performance(func):
    """성능 모니터링 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()

        result = await func(*args, **kwargs)

        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")

        return result
    return wrapper

# 사용
@monitor_performance
async def heavy_processing_node(self, state):
    # 무거운 처리
    pass
```

---

## 9. 실전 예제

### 9.1 완전한 Agent 구현

```python
"""My Custom Agent - 실전 예제"""

import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.app.octostrator.agents.base.base_agent import (
    BaseAgent, BaseAgentState, AgentStatus, AgentPriority
)
from backend.app.octostrator.agents.base.agent_registry import register_agent
from backend.app.octostrator.agents.base.capabilities import Capability

logger = logging.getLogger(__name__)


# ====================================
# State Definition
# ====================================

class DataAnalysisState(BaseAgentState):
    """데이터 분석 Agent State"""
    raw_data: Optional[List[Dict]] = None
    cleaned_data: Optional[List[Dict]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    report: Optional[str] = None
    confidence_score: float = 0.0


# ====================================
# Agent Implementation
# ====================================

@register_agent("data_analysis_agent")
class DataAnalysisAgent(BaseAgent):
    """데이터 분석 및 리포트 생성 Agent"""

    def __init__(self):
        super().__init__(
            agent_id="data_analysis_agent",
            agent_name="Data Analysis Agent",
            description="Analyzes data and generates comprehensive reports",
            enable_checkpoint=True,
            priority=AgentPriority.HIGH,
            metadata={
                "version": "1.0",
                "max_data_size": 10000
            }
        )

        self.capabilities = [
            Capability.DATA_ANALYSIS.value,
            Capability.REPORT_GENERATION.value,
            Capability.TREND_ANALYSIS.value
        ]

        self.primary_capabilities = [
            Capability.DATA_ANALYSIS.value
        ]

        self.llm = None

    def build_graph(self, llm=None) -> StateGraph:
        """데이터 분석 워크플로우 구축"""

        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

        workflow = StateGraph(DataAnalysisState)

        # 노드 추가
        workflow.add_node("validate_data", self.validate_data_node)
        workflow.add_node("clean_data", self.clean_data_node)
        workflow.add_node("analyze_data", self.analyze_data_node)
        workflow.add_node("generate_insights", self.generate_insights_node)
        workflow.add_node("create_report", self.create_report_node)
        workflow.add_node("quality_check", self.quality_check_node)

        # 기본 흐름
        workflow.add_edge(START, "validate_data")
        workflow.add_edge("validate_data", "clean_data")
        workflow.add_edge("clean_data", "analyze_data")
        workflow.add_edge("analyze_data", "generate_insights")
        workflow.add_edge("generate_insights", "create_report")
        workflow.add_edge("create_report", "quality_check")

        # 조건부 엣지
        workflow.add_conditional_edges(
            "quality_check",
            self.check_quality,
            {
                "pass": END,
                "retry": "analyze_data",
                "fail": END
            }
        )

        return workflow

    async def process_task(self, task: Dict, context: Dict) -> Dict:
        # execute()에서 처리됨
        pass

    # ====================================
    # Node Implementations
    # ====================================

    async def validate_data_node(self, state: DataAnalysisState) -> Dict:
        """데이터 유효성 검증"""
        try:
            raw_data = state.task.get("params", {}).get("data", [])

            if not raw_data:
                return {"error": "No data provided"}

            if len(raw_data) > self.metadata["max_data_size"]:
                return {"error": f"Data exceeds maximum size"}

            logger.info(f"Validated {len(raw_data)} data points")

            return {
                "raw_data": raw_data,
                "metadata": {
                    **state.metadata,
                    "data_count": len(raw_data)
                }
            }

        except Exception as e:
            return {"error": str(e)}

    async def clean_data_node(self, state: DataAnalysisState) -> Dict:
        """데이터 정제"""
        raw_data = state.raw_data
        cleaned = []

        for item in raw_data:
            # 결측값 처리
            if self._is_valid_item(item):
                cleaned_item = self._clean_item(item)
                cleaned.append(cleaned_item)

        logger.info(f"Cleaned {len(cleaned)}/{len(raw_data)} items")

        return {"cleaned_data": cleaned}

    async def analyze_data_node(self, state: DataAnalysisState) -> Dict:
        """데이터 분석"""
        data = state.cleaned_data

        # 기본 통계 분석
        analysis = {
            "count": len(data),
            "summary": self._calculate_summary(data),
            "trends": self._identify_trends(data),
            "anomalies": self._detect_anomalies(data)
        }

        # LLM을 사용한 심층 분석
        if self.llm:
            deep_analysis = await self._deep_analyze_with_llm(data)
            analysis["insights"] = deep_analysis

        return {"analysis_result": analysis}

    async def generate_insights_node(self, state: DataAnalysisState) -> Dict:
        """인사이트 생성"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""당신은 데이터 분석 전문가입니다.
분석 결과를 바탕으로 핵심 인사이트를 도출하세요."""),
            HumanMessage(content=f"""
분석 결과:
{json.dumps(state.analysis_result, ensure_ascii=False, indent=2)}

다음 형식으로 인사이트를 제공하세요:
1. 핵심 발견사항 (3개)
2. 추천 액션 (2개)
3. 주의사항 (1개)
""")
        ])

        response = await self.llm.ainvoke(prompt.format_messages())

        return {
            "analysis_result": {
                **state.analysis_result,
                "insights": response.content
            }
        }

    async def create_report_node(self, state: DataAnalysisState) -> Dict:
        """리포트 생성"""
        report = f"""
# 데이터 분석 리포트

**생성일**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**데이터 수**: {state.analysis_result["count"]}

## 요약
{state.analysis_result.get("summary", "N/A")}

## 트렌드
{state.analysis_result.get("trends", "N/A")}

## 인사이트
{state.analysis_result.get("insights", "N/A")}

## 신뢰도
{self._calculate_confidence(state)}%
"""
        return {
            "report": report,
            "confidence_score": self._calculate_confidence(state) / 100
        }

    async def quality_check_node(self, state: DataAnalysisState) -> Dict:
        """품질 검증"""
        score = state.confidence_score

        if score < 0.3:
            logger.warning(f"Low confidence score: {score}")

        return {"confidence_score": score}

    # ====================================
    # Conditional Functions
    # ====================================

    def check_quality(self, state: DataAnalysisState) -> Literal["pass", "retry", "fail"]:
        """품질 검사"""
        if state.confidence_score >= 0.7:
            return "pass"
        elif state.confidence_score >= 0.4 and state.retry_count < 2:
            return "retry"
        else:
            return "fail"

    # ====================================
    # Helper Methods
    # ====================================

    def _is_valid_item(self, item: Dict) -> bool:
        return item is not None and len(item) > 0

    def _clean_item(self, item: Dict) -> Dict:
        # 데이터 정제 로직
        return {k: v for k, v in item.items() if v is not None}

    def _calculate_summary(self, data: List[Dict]) -> Dict:
        # 요약 통계 계산
        return {
            "total": len(data),
            "unique_keys": len(set(k for d in data for k in d.keys()))
        }

    def _identify_trends(self, data: List[Dict]) -> List[str]:
        # 트렌드 식별 로직
        return ["상승 트렌드", "계절적 패턴"]

    def _detect_anomalies(self, data: List[Dict]) -> List[Dict]:
        # 이상치 탐지 로직
        return []

    async def _deep_analyze_with_llm(self, data: List[Dict]) -> str:
        # LLM을 사용한 심층 분석
        sample = data[:5] if len(data) > 5 else data
        prompt = f"다음 데이터를 분석하세요: {sample}"

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content

    def _calculate_confidence(self, state: DataAnalysisState) -> float:
        # 신뢰도 점수 계산
        base_score = 50.0

        if state.cleaned_data and len(state.cleaned_data) > 10:
            base_score += 20

        if state.analysis_result and "insights" in state.analysis_result:
            base_score += 20

        if not state.error:
            base_score += 10

        return min(base_score, 100.0)
```

### 9.2 Agent 사용 방법

```python
# 1. Agent 등록 및 초기화
from backend.app.octostrator.agents.base.agent_registry import agent_registry

# 자동 발견
agent_registry.discover_agents()

# 또는 수동 등록
from my_agents import DataAnalysisAgent
agent_registry.register(DataAnalysisAgent, "data_analysis_agent")

# 2. Agent 인스턴스 생성
agent = agent_registry.create_agent("data_analysis_agent")
await agent.initialize(llm=llm, checkpointer=checkpointer)

# 3. Agent 실행
result = await agent.execute(
    task={
        "type": "analyze",
        "params": {
            "data": [
                {"date": "2024-01-01", "value": 100},
                {"date": "2024-01-02", "value": 120},
                # ...
            ]
        }
    },
    context={
        "session_id": "session_123",
        "user_id": "user_456"
    },
    thread_id="session_123"  # Checkpoint용
)

# 4. 결과 확인
print(result["result"]["report"])
print(f"Confidence: {result['result']['confidence_score']}")
```

### 9.3 Agent 통합

Execute Supervisor에서 자동으로 Agent를 찾아 실행:

```python
# TODO에서 capability 지정
todo = {
    "id": "todo_001",
    "agent": "data_analysis_agent",  # 또는 None (자동 선택)
    "task": "analyze",
    "capability": "data_analysis",  # 이 capability로 Agent 선택
    "params": {"data": [...]}
}

# Execute Supervisor가 자동으로:
# 1. Agent Registry에서 검색
# 2. Capability 매칭
# 3. 최적 Agent 선택
# 4. 실행 및 결과 수집
```

---

## 부록

### A. Agent 체크리스트

- [ ] BaseAgent 상속
- [ ] agent_id 설정
- [ ] capabilities 정의
- [ ] State 클래스 정의
- [ ] build_graph() 구현
- [ ] 모든 노드 구현
- [ ] 조건부 로직 구현
- [ ] 에러 처리
- [ ] 테스트 작성
- [ ] 문서화
- [ ] Registry 등록

### B. 베스트 프랙티스

1. **Single Responsibility**: 하나의 Agent는 하나의 도메인만
2. **Stateless 우선**: 가능한 Stateless로 구현
3. **명확한 Capability**: 제공하는 능력을 명확히 정의
4. **에러 처리**: 모든 노드에 try-except
5. **로깅**: 충분한 로그로 디버깅 용이하게
6. **테스트**: 단위 테스트 + 통합 테스트
7. **문서화**: 코드 내 주석 + README

### C. 자주 하는 실수

1. ❌ State 직접 수정 → ✅ 업데이트 딕셔너리 반환
2. ❌ 동기 함수 사용 → ✅ async/await 사용
3. ❌ 하드코딩 → ✅ 설정값 사용
4. ❌ 에러 무시 → ✅ 명시적 에러 처리
5. ❌ 거대한 노드 → ✅ 작은 단위로 분할

---

**작성 완료일**: 2025-11-05
**다음 문서**: [API Reference](./API_REFERENCE_251105.md)