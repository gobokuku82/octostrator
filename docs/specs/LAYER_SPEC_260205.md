# 4-Layer Architecture Specification
**Version**: 2.0 | **Date**: 2026-02-05 | **Status**: Draft

## 1. Overview

기업용 에이전트의 4-Layer 아키텍처 상세 명세입니다.

```
┌────────────────────────────────────────────────────────────────────┐
│                         User Input                                  │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 1: COGNITIVE                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Intent     │  │   Entity     │  │      Dialogue            │  │
│  │  Classifier  │→ │  Extractor   │→ │      Manager             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  Output: IntentClassificationResult {domain, category, entities}   │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 2: PLANNING                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │    Todo      │  │  Dependency  │  │     Resource             │  │
│  │  Generator   │→ │  Calculator  │→ │     Planner              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  Output: Plan {todos[], execution_graph, resource_plan}            │
└────────────────────────────────────────────────────────────────────┘
                                │
                           ◆ HITL Gate ◆
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 3: EXECUTION                                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Execution Supervisor                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│           │              │              │              │            │
│           ▼              ▼              ▼              ▼            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐  │
│  │    Data      │ │   Insight    │ │   Content    │ │   Ops    │  │
│  │   Executor   │ │   Executor   │ │   Executor   │ │ Executor │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘  │
│                                                                     │
│  Output: ExecutionResult {success, data, execution_time}           │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 4: RESPONSE                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Result     │  │    Smart     │  │      Response            │  │
│  │  Aggregator  │→ │  Summarizer  │→ │      Generator           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  Output: Natural Language Response + Structured Report             │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Cognitive Layer

### 2.1 Purpose
사용자 입력을 분석하여 의도(Intent)를 파악하고, 필요한 엔티티를 추출합니다.

### 2.2 Components

#### 2.2.1 Intent Classifier

```python
class IntentClassifier:
    """3-depth 계층적 의도 분류기"""

    async def classify(self, user_input: str, context: Dict) -> Intent:
        """
        Input:
            user_input: 사용자 입력 텍스트
            context: 이전 대화 컨텍스트

        Output:
            Intent:
                domain: IntentDomain (ANALYSIS, CONTENT, OPERATION, INQUIRY)
                category: IntentCategory (SENTIMENT, KEYWORD, REPORT, etc.)
                subcategory: Optional[str]
                confidence: float (0.0 ~ 1.0)

        Classification Hierarchy:
            Level 1 (Domain): 분석 / 콘텐츠 / 운영 / 조회
            Level 2 (Category): 감성분석 / 키워드 / 리포트 / 영상 ...
            Level 3 (Subcategory): 리뷰분석 / 경쟁사비교 ...
        """
```

**분류 체계:**

| Domain | Category | Subcategory Examples |
|--------|----------|---------------------|
| ANALYSIS | SENTIMENT | review_analysis, brand_perception |
| ANALYSIS | KEYWORD | keyword_extraction, topic_modeling |
| ANALYSIS | TREND | google_trends, market_trends |
| ANALYSIS | COMPETITOR | competitor_comparison, market_share |
| CONTENT | REPORT | trend_report, analysis_report |
| CONTENT | VIDEO | promotional_video, tutorial |
| CONTENT | AD | social_ad, display_ad |
| OPERATION | SALES | sales_material, proposal |
| OPERATION | INVENTORY | stock_check, reorder |
| OPERATION | DASHBOARD | kpi_dashboard, real_time |
| INQUIRY | GENERAL | faq, how_to |

#### 2.2.2 Entity Extractor

```python
class EntityExtractor:
    """엔티티 추출기"""

    async def extract(self, user_input: str, intent: Intent) -> List[Entity]:
        """
        Entity Types:
            - brand: 브랜드명 (라네즈, 설화수, ...)
            - product: 제품명
            - date_range: 기간 (최근 3개월, 2024년 1분기)
            - platform: 플랫폼 (네이버, 올리브영, ...)
            - metric: 지표 (매출, 리뷰수, ...)
            - competitor: 경쟁사
            - category: 제품 카테고리
        """
```

#### 2.2.3 Dialogue Manager

```python
class DialogueManager:
    """멀티턴 대화 관리자"""

    def update_context(self, turn: DialogueTurn) -> None:
        """대화 턴 추가"""

    def get_context_summary(self) -> str:
        """컨텍스트 요약"""

    def check_completeness(self, intent: Intent, entities: List[Entity]) -> bool:
        """의도 완성도 확인"""

    def generate_clarification(self) -> str:
        """명확화 질문 생성"""
```

### 2.3 Input/Output Schema

```python
# Input
class CognitiveInput(BaseModel):
    user_input: str
    language: str = "KOR"
    session_id: Optional[str]
    previous_context: Optional[Dict]

# Output
class CognitiveOutput(BaseModel):
    intent: IntentClassificationResult
    requires_clarification: bool
    clarification_question: Optional[str]
    processing_time_ms: float
```

### 2.4 LLM Prompt Template

```yaml
# configs/prompts/cognitive.yaml
system_prompt: |
  당신은 사용자 의도를 분석하는 전문가입니다.
  다음 분류 체계에 따라 의도를 분류하세요.

  분류 체계:
  1. Domain: {domains}
  2. Category: {categories}
  3. Subcategory: (자유 형식)

  응답 형식:
  {
    "domain": "...",
    "category": "...",
    "subcategory": "...",
    "confidence": 0.0-1.0,
    "entities": [...]
  }
```

---

## 3. Layer 2: Planning Layer

### 3.1 Purpose
분류된 의도를 기반으로 실행 가능한 Todo 목록을 생성하고, 의존성과 리소스를 계획합니다.

### 3.2 Components

#### 3.2.1 Todo Generator

```python
class TodoGenerator:
    """Todo 생성기"""

    async def generate(
        self,
        intent: IntentClassificationResult,
        available_tools: List[ToolSpec]
    ) -> List[TodoItem]:
        """
        Process:
            1. Intent에서 필요 작업 식별
            2. ToolDiscovery로 적합한 도구 매핑
            3. 세분화된 TodoItem 생성
            4. 기본 의존성 설정

        Generation Strategy:
            - 데이터 수집 → 전처리 → 분석 → 콘텐츠 생성
            - 각 단계를 독립적인 Todo로 분리
            - 재사용 가능한 단위로 설계
        """
```

**Todo 생성 템플릿:**

```yaml
# 감성 분석 요청 시 생성되는 Todo 목록
intent: analysis.sentiment
todos:
  - title: "데이터 수집"
    tool: data_collector
    layer: data
    priority: 10

  - title: "데이터 전처리"
    tool: preprocessor
    layer: data
    depends_on: ["데이터 수집"]
    priority: 9

  - title: "감성 분석"
    tool: sentiment_analyzer
    layer: ml
    depends_on: ["데이터 전처리"]
    priority: 8

  - title: "키워드 추출"
    tool: keyword_extractor
    layer: ml
    depends_on: ["데이터 전처리"]
    priority: 7

  - title: "인사이트 생성"
    tool: insight_generator
    layer: ml
    depends_on: ["감성 분석", "키워드 추출"]
    priority: 6
```

#### 3.2.2 Dependency Calculator

```python
class DependencyCalculator:
    """의존성 계산기"""

    def calculate_dependencies(self, todos: List[TodoItem]) -> List[TodoItem]:
        """
        기능:
            1. 명시적 의존성 검증
            2. 암시적 의존성 추론 (데이터 흐름 기반)
            3. 순환 의존성 탐지
            4. 위상 정렬 (Topological Sort)
        """

    def detect_cycles(self, todos: List[TodoItem]) -> List[List[str]]:
        """순환 의존성 탐지"""

    def topological_sort(self, todos: List[TodoItem]) -> List[TodoItem]:
        """위상 정렬"""
```

#### 3.2.3 Execution Graph Builder

```python
class ExecutionGraphBuilder:
    """실행 그래프 생성기"""

    def build(self, todos: List[TodoItem]) -> ExecutionGraph:
        """
        Output:
            ExecutionGraph:
                nodes: Dict[str, ExecutionNode]
                groups: List[ExecutionGroup]  # 병렬 실행 그룹
                critical_path: List[str]       # 크리티컬 패스

        Features:
            - 병렬 실행 가능 Todo 그룹화
            - 크리티컬 패스 계산
            - Mermaid 다이어그램 생성
        """
```

#### 3.2.4 Resource Planner

```python
class ResourcePlanner:
    """리소스 계획기"""

    async def plan(
        self,
        todos: List[TodoItem],
        constraints: ResourceConstraints
    ) -> ResourcePlan:
        """
        기능:
            1. Todo별 적합 에이전트 선정
            2. 비용 추정
            3. 시간 추정
            4. 병렬화 최적화

        Constraints:
            - max_parallel_tasks: 최대 병렬 작업 수
            - max_cost: 최대 비용
            - max_time: 최대 소요 시간
        """
```

### 3.3 Input/Output Schema

```python
# Input
class PlanningInput(BaseModel):
    intent: IntentClassificationResult
    session_id: str
    user_preferences: Optional[Dict]

# Output
class PlanningOutput(BaseModel):
    plan: Plan
    todos: List[TodoItem]
    execution_graph: ExecutionGraph
    resource_plan: ResourcePlan
    cost_estimate: CostEstimate
    requires_approval: bool
```

### 3.4 LLM Prompt Template

```yaml
# configs/prompts/planning.yaml
system_prompt: |
  당신은 작업 계획을 수립하는 전문가입니다.
  주어진 의도와 사용 가능한 도구를 기반으로 실행 계획을 생성하세요.

  사용 가능한 도구:
  {available_tools}

  규칙:
  1. 각 Todo는 하나의 도구만 사용
  2. 의존성을 명확히 지정
  3. 병렬 실행 가능한 작업은 의존성 없이 분리

  응답 형식:
  {
    "todos": [
      {
        "title": "...",
        "description": "...",
        "tool": "tool_name",
        "layer": "ml|biz|data",
        "depends_on": ["todo_id_1", ...],
        "priority": 0-10,
        "params": {...}
      }
    ]
  }
```

---

## 4. Layer 3: Execution Layer

### 4.1 Purpose
Planning Layer에서 생성된 Todo를 실제로 실행하고, 결과를 수집합니다.

### 4.2 Architecture

```
                    ┌─────────────────────┐
                    │   Execution Node    │
                    │  (Single Todo/Cycle)│
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Execution Supervisor│
                    └─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Data Executor │   │Insight Executor│   │Content Executor│
├───────────────┤   ├───────────────┤   ├───────────────┤
│ - collector   │   │ - sentiment   │   │ - report      │
│ - preprocessor│   │ - keyword     │   │ - video       │
│ - trends      │   │ - hashtag     │   │ - ad_creative │
└───────────────┘   │ - competitor  │   └───────────────┘
                    │ - insight     │
                    └───────────────┘
```

### 4.3 Components

#### 4.3.1 Execution Supervisor

```python
class ExecutionSupervisor:
    """실행 관리자 (Singleton)"""

    def __init__(self):
        self.executors = {
            "data": DataExecutor(),
            "insight": InsightExecutor(),
            "content": ContentExecutor(),
            "ops": OpsExecutor(),
        }

    async def execute(
        self,
        todo: TodoItem,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Process:
            1. Todo의 layer/tool로 적합한 Executor 선택
            2. Executor에 실행 위임
            3. 결과 수집 및 표준화
            4. 캐시 저장 (선택적)
        """

    def get_executor(self, todo: TodoItem) -> BaseExecutor:
        """Todo에 맞는 Executor 반환"""
```

#### 4.3.2 Base Executor

```python
class BaseExecutor(ABC):
    """실행기 기본 클래스"""

    @abstractmethod
    async def execute(
        self,
        todo: TodoItem,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Todo 실행"""

    async def pre_execute(self, todo: TodoItem) -> None:
        """실행 전 준비"""

    async def post_execute(self, result: ExecutionResult) -> None:
        """실행 후 정리"""

    def validate_input(self, todo: TodoItem) -> bool:
        """입력 검증"""
```

#### 4.3.3 Domain Executors

```python
# Data Executor
class DataExecutor(BaseExecutor):
    """데이터 수집/처리 실행기"""

    tools = {
        "collector": CollectorTool,
        "preprocessor": PreprocessorTool,
        "google_trends": TrendsTool,
    }

# Insight Executor
class InsightExecutor(BaseExecutor):
    """분석/인사이트 실행기"""

    tools = {
        "sentiment_analyzer": SentimentTool,
        "keyword_extractor": KeywordTool,
        "hashtag_analyzer": HashtagTool,
        "competitor_analyzer": CompetitorTool,
        "insight_generator": InsightTool,
    }

# Content Executor
class ContentExecutor(BaseExecutor):
    """콘텐츠 생성 실행기"""

    tools = {
        "report_generator": ReportTool,
        "video_generator": VideoTool,
        "ad_creative_generator": AdCreativeTool,
    }

# Ops Executor
class OpsExecutor(BaseExecutor):
    """운영 작업 실행기"""

    tools = {
        "sales_material": SalesTool,
        "inventory_manager": InventoryTool,
        "dashboard_generator": DashboardTool,
    }
```

### 4.4 Execution Flow

```python
async def execute_single_todo(state: AgentState) -> AgentState:
    """단일 Todo 실행 (Cycle당 1개)"""

    # 1. 실행 가능한 Todo 찾기
    ready_todo = find_ready_todo(state.todos)
    if not ready_todo:
        return state  # 모든 Todo 완료

    # 2. 상태 업데이트 (in_progress)
    ready_todo.status = TodoStatus.IN_PROGRESS
    ready_todo.metadata.progress.started_at = datetime.utcnow()

    # 3. Supervisor를 통한 실행
    supervisor = ExecutionSupervisor()
    context = ExecutionContext(
        session_id=state.session_id,
        language=state.language,
        previous_results=state.ml_result | state.biz_result,
    )

    result = await supervisor.execute(ready_todo, context)

    # 4. 결과 처리
    if result.success:
        ready_todo.status = TodoStatus.COMPLETED
        ready_todo.result_data = result.data
    else:
        ready_todo.status = TodoStatus.FAILED
        ready_todo.metadata.progress.error_message = result.error

    # 5. State 업데이트
    if ready_todo.layer == "ml":
        state.ml_result[ready_todo.id] = result.data
    else:
        state.biz_result[ready_todo.id] = result.data

    # 6. WebSocket 이벤트 발송
    await send_websocket_update(state.session_id, ready_todo, result)

    return state
```

### 4.5 Input/Output Schema

```python
# Input
class ExecutionInput(BaseModel):
    todo: TodoItem
    context: ExecutionContext

# Output
class ExecutionOutput(BaseModel):
    todo_id: str
    result: ExecutionResult
    updated_state: Dict
```

---

## 5. Layer 4: Response Layer

### 5.1 Purpose
실행 결과를 종합하여 사용자에게 전달할 자연어 응답을 생성합니다.

### 5.2 Components

#### 5.2.1 Result Aggregator

```python
class ResultAggregator:
    """결과 집계기"""

    def aggregate(
        self,
        ml_results: Dict,
        biz_results: Dict
    ) -> Dict:
        """
        기능:
            1. 중복 데이터 제거
            2. 결과 정규화
            3. 핵심 인사이트 추출
        """
```

#### 5.2.2 Smart Summarizer

```python
class SmartSummarizer:
    """스마트 요약기"""

    def summarize(self, results: Dict, max_length: int = 2000) -> Dict:
        """
        기능:
            1. Raw 데이터 제외 (preprocessed_reviews, collected_data)
            2. 핵심 통계만 추출
            3. 토큰 수 제한 준수
            4. 구조화된 요약 생성

        제외 항목:
            - preprocessed_reviews
            - collected_reviews
            - raw_data
            - embedding_vectors
        """
```

#### 5.2.3 Response Generator

```python
class ResponseGenerator:
    """응답 생성기"""

    async def generate(
        self,
        summarized_results: Dict,
        intent: Intent,
        language: str
    ) -> str:
        """
        템플릿 선택:
            - with_ml_only: ML 결과만 있을 때
            - with_biz_only: 비즈니스 결과만 있을 때
            - with_both: 둘 다 있을 때
            - base: 기본 응답

        응답 구조:
            1. 요약 (1-2문장)
            2. 핵심 발견 (bullet points)
            3. 상세 결과 (필요시)
            4. 추천 액션 (선택적)
        """
```

### 5.3 Input/Output Schema

```python
# Input
class ResponseInput(BaseModel):
    ml_result: Dict
    biz_result: Dict
    intent: IntentClassificationResult
    language: str = "KOR"

# Output
class ResponseOutput(BaseModel):
    response: str
    structured_report: Optional[Dict]
    report_path: Optional[str]
```

### 5.4 LLM Prompt Template

```yaml
# configs/prompts/response.yaml
templates:
  with_ml_only:
    system: |
      분석 결과를 바탕으로 사용자에게 인사이트를 전달하세요.

      응답 구조:
      1. 핵심 요약 (1-2문장)
      2. 주요 발견 (3-5개 bullet points)
      3. 추천 액션 (선택적)

      분석 결과:
      {ml_result}

  with_both:
    system: |
      분석 및 비즈니스 결과를 종합하여 응답하세요.

      분석 결과: {ml_result}
      비즈니스 결과: {biz_result}
```

---

## 6. Layer Orchestration

### 6.1 LangGraph Configuration

```python
# orchestrator/builder.py

def build_unified_graph() -> StateGraph:
    """통합 에이전트 그래프 구성"""

    graph = StateGraph(AgentState)

    # 노드 추가
    graph.add_node("cognitive", cognitive_node)
    graph.add_node("planning", planning_node)
    graph.add_node("execution", execution_node)
    graph.add_node("response", response_node)

    # 엣지 정의
    graph.add_edge(START, "cognitive")
    graph.add_edge("cognitive", "planning")
    graph.add_conditional_edges(
        "planning",
        route_to_execution,
        {
            "execute": "execution",
            "hitl_wait": END,  # HITL 대기
        }
    )
    graph.add_conditional_edges(
        "execution",
        route_after_execution,
        {
            "continue": "execution",  # 다음 Todo
            "response": "response",    # 완료
            "hitl_wait": END,          # HITL 대기
        }
    )
    graph.add_edge("response", END)

    return graph.compile(checkpointer=PostgresCheckpointer())
```

### 6.2 Routing Logic

```python
def route_to_execution(state: AgentState) -> str:
    """Planning → Execution 라우팅"""
    if state.get("requires_hitl"):
        return "hitl_wait"
    return "execute"

def route_after_execution(state: AgentState) -> str:
    """Execution 후 라우팅"""
    # HITL 체크
    if state.get("hitl_mode") == "approval_wait":
        return "hitl_wait"

    # 남은 Todo 체크
    pending_todos = [t for t in state.todos if t.status == "pending"]
    if pending_todos:
        return "continue"

    return "response"
```

---

## 7. Cross-Layer Communication

### 7.1 State Reducers

```python
def todo_reducer(
    existing: List[TodoItem],
    updates: List[TodoItem]
) -> List[TodoItem]:
    """Todo 목록 병합"""
    existing_map = {t.id: t for t in existing}
    for update in updates:
        existing_map[update.id] = update
    return list(existing_map.values())

def ml_result_reducer(existing: Dict, new: Dict) -> Dict:
    """ML 결과 병합"""
    return {**existing, **new}

def biz_result_reducer(existing: Dict, new: Dict) -> Dict:
    """비즈니스 결과 병합"""
    return {**existing, **new}
```

### 7.2 Context Passing

```python
# Layer 간 컨텍스트 전달
class LayerContext:
    """레이어 간 공유 컨텍스트"""

    def __init__(self, state: AgentState):
        self.session_id = state.get("session_id")
        self.language = state.get("language", "KOR")
        self.intent = state.get("intent")
        self.collected_data = state.get("ml_result", {}).get("collected_data")
        self.preprocessed = state.get("ml_result", {}).get("preprocessed")
```

---

## Related Documents
- [ARCHITECTURE_260205.md](ARCHITECTURE_260205.md) - System architecture
- [DATA_MODELS_260205.md](DATA_MODELS_260205.md) - Data models
- [TODO_SYSTEM_260205.md](TODO_SYSTEM_260205.md) - Todo & HITL system
