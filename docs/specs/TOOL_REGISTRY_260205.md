# Tool Registry Specification
**Version**: 2.0 | **Date**: 2026-02-05 | **Status**: Draft

## 1. Overview

기업용 에이전트의 도구(Tool) 정의 및 등록 시스템 명세입니다.

### 1.1 Design Principles

1. **선언적 정의**: YAML 기반 도구 정의
2. **동적 발견**: 런타임 도구 자동 탐색
3. **Hot Reload**: 재시작 없이 도구 업데이트
4. **Type Safety**: Pydantic 스키마 기반 검증

---

## 2. Tool Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Tool Registry System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
│  │   YAML Files    │───▶│  ToolDiscovery  │───▶│  ToolRegistry  │  │
│  │  (definitions/) │    │   (Singleton)   │    │   (Singleton)  │  │
│  └─────────────────┘    └─────────────────┘    └────────────────┘  │
│                                │                        │           │
│                                ▼                        ▼           │
│                    ┌─────────────────────┐    ┌────────────────┐   │
│                    │   ToolSpec Models   │    │ Executor Mapping│   │
│                    └─────────────────────┘    └────────────────┘   │
│                                                        │           │
│                                                        ▼           │
│                                              ┌────────────────┐    │
│                                              │   BaseTool     │    │
│                                              │ Implementation │    │
│                                              └────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tool Definition (YAML)

### 3.1 Tool Definition Structure

```yaml
# tools/definitions/sentiment_analyzer.yaml

name: sentiment_analyzer
display_name: 감성 분석기
version: 1.2.0
description: |
  텍스트 데이터의 감성을 분석합니다.
  긍정/부정/중립 분류와 세부 감정 점수를 제공합니다.

# Classification
type: analysis          # data | analysis | content | business
layer: ml              # 실행 레이어

# Parameters
parameters:
  - name: text_data
    type: array
    required: true
    description: 분석할 텍스트 데이터 배열
    item_type: string

  - name: model
    type: string
    required: false
    default: "gpt-4o-mini"
    description: 사용할 LLM 모델
    enum: ["gpt-4o-mini", "gpt-4o", "claude-3-sonnet"]

  - name: batch_size
    type: integer
    required: false
    default: 10
    description: 배치 처리 크기
    min: 1
    max: 100

  - name: include_reasoning
    type: boolean
    required: false
    default: false
    description: 분석 근거 포함 여부

# Output
output_schema:
  type: object
  properties:
    overall_sentiment:
      type: string
      enum: ["positive", "negative", "neutral", "mixed"]
    sentiment_distribution:
      type: object
      properties:
        positive: { type: number }
        negative: { type: number }
        neutral: { type: number }
    top_positive_aspects:
      type: array
      items: { type: string }
    top_negative_aspects:
      type: array
      items: { type: string }
    confidence_score:
      type: number

# Executor
executor: app.dream_agent.tools.analysis.sentiment.SentimentTool

# Execution Config
timeout: 300
max_retries: 3

# Dependencies
dependencies:
  - preprocessor    # 전처리된 데이터 필요

# Metadata
tags:
  - sentiment
  - nlp
  - analysis
  - kbeauty

# Cost Estimation
cost:
  base_cost: 0.001    # USD per execution
  per_item_cost: 0.0001  # USD per text item
```

### 3.2 Parameter Types

```yaml
# String Parameter
- name: brand_name
  type: string
  required: true
  description: 브랜드명
  pattern: "^[가-힣a-zA-Z0-9\\s]+$"  # 정규식 패턴
  max_length: 50

# Integer Parameter
- name: limit
  type: integer
  required: false
  default: 100
  min: 1
  max: 10000

# Float Parameter
- name: threshold
  type: float
  required: false
  default: 0.5
  min: 0.0
  max: 1.0

# Boolean Parameter
- name: include_metadata
  type: boolean
  required: false
  default: false

# Array Parameter
- name: platforms
  type: array
  required: true
  item_type: string
  enum: ["oliveyoung", "coupang", "naver", "hwahae"]
  min_items: 1
  max_items: 5

# Object Parameter
- name: filters
  type: object
  required: false
  properties:
    start_date:
      type: string
      format: date
    end_date:
      type: string
      format: date
    rating_min:
      type: integer
      min: 1
      max: 5

# Enum Parameter
- name: analysis_type
  type: string
  required: true
  enum: ["basic", "detailed", "comprehensive"]
  default: "basic"
```

---

## 4. Tool Registry

### 4.1 ToolDiscovery

```python
class ToolDiscovery:
    """도구 자동 발견 (Singleton)"""

    _instance: Optional["ToolDiscovery"] = None
    _tools: Dict[str, ToolSpec] = {}

    @classmethod
    def get_instance(cls) -> "ToolDiscovery":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_all_tools()
        return cls._instance

    def _load_all_tools(self) -> None:
        """definitions/ 폴더의 모든 YAML 로드"""
        definitions_path = Path(__file__).parent / "definitions"
        for yaml_file in definitions_path.glob("*.yaml"):
            tool_spec = self._load_tool(yaml_file)
            self._tools[tool_spec.name] = tool_spec

    def _load_tool(self, path: Path) -> ToolSpec:
        """단일 YAML 파일 로드 및 검증"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return ToolSpec(**data)

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        """도구 조회"""
        return self._tools.get(name)

    def get_tools_by_type(self, tool_type: str) -> List[ToolSpec]:
        """타입별 도구 조회"""
        return [t for t in self._tools.values() if t.type == tool_type]

    def get_tools_by_layer(self, layer: str) -> List[ToolSpec]:
        """레이어별 도구 조회"""
        return [t for t in self._tools.values() if t.layer == layer]

    def get_tools_by_tags(self, tags: List[str]) -> List[ToolSpec]:
        """태그로 도구 검색"""
        return [
            t for t in self._tools.values()
            if any(tag in t.tags for tag in tags)
        ]

    def reload_tool(self, name: str) -> Optional[ToolSpec]:
        """Hot reload: 특정 도구 재로드"""
        # Implementation

    def validate_params(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> ValidationResult:
        """파라미터 검증"""
        # Implementation
```

### 4.2 ToolRegistry

```python
class ToolRegistry:
    """도구 실행기 레지스트리 (Singleton)"""

    _instance: Optional["ToolRegistry"] = None
    _executors: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, name: str, executor: Type[BaseTool]) -> None:
        """실행기 등록"""
        cls._executors[name] = executor

    @classmethod
    def get_executor(cls, name: str) -> Optional[Type[BaseTool]]:
        """실행기 조회"""
        return cls._executors.get(name)

    @classmethod
    def execute(
        cls,
        name: str,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """도구 실행"""
        executor_class = cls.get_executor(name)
        if not executor_class:
            raise ToolNotFoundError(f"Tool '{name}' not found")

        executor = executor_class()
        return executor.execute(params, context)
```

### 4.3 Executor Registration

```python
# 데코레이터 방식
@register_tool("sentiment_analyzer")
class SentimentTool(BaseTool):
    """감성 분석 도구"""

    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        # Implementation
        pass

# 수동 등록 방식
ToolRegistry.register("sentiment_analyzer", SentimentTool)
```

---

## 5. BaseTool Interface

### 5.1 Abstract Base Class

```python
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """도구 기본 클래스"""

    # Class attributes from YAML
    name: str
    display_name: str
    description: str
    type: ToolType
    layer: str

    def __init__(self):
        self._spec: Optional[ToolSpec] = None

    @property
    def spec(self) -> ToolSpec:
        """도구 사양 반환"""
        if self._spec is None:
            discovery = ToolDiscovery.get_instance()
            self._spec = discovery.get_tool(self.name)
        return self._spec

    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        도구 실행 (추상 메서드)

        Args:
            params: 입력 파라미터 (YAML에 정의된 스키마)
            context: 실행 컨텍스트

        Returns:
            ExecutionResult: 실행 결과
        """
        pass

    async def validate(self, params: Dict[str, Any]) -> ValidationResult:
        """파라미터 검증"""
        discovery = ToolDiscovery.get_instance()
        return discovery.validate_params(self.name, params)

    async def pre_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """실행 전 처리 (오버라이드 가능)"""
        return params

    async def post_execute(self, result: ExecutionResult) -> ExecutionResult:
        """실행 후 처리 (오버라이드 가능)"""
        return result

    def get_dependencies(self) -> List[str]:
        """의존 도구 목록"""
        return self.spec.dependencies if self.spec else []
```

### 5.2 Tool Implementation Example

```python
from app.dream_agent.tools.base_tool import BaseTool, register_tool
from app.dream_agent.models.execution import ExecutionResult, ExecutionContext

@register_tool("sentiment_analyzer")
class SentimentTool(BaseTool):
    """감성 분석 도구"""

    name = "sentiment_analyzer"
    display_name = "감성 분석기"
    type = ToolType.ANALYSIS
    layer = "ml"

    async def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        try:
            # 1. 파라미터 추출
            text_data = params["text_data"]
            model = params.get("model", "gpt-4o-mini")
            batch_size = params.get("batch_size", 10)

            # 2. 배치 처리
            results = []
            for i in range(0, len(text_data), batch_size):
                batch = text_data[i:i + batch_size]
                batch_result = await self._analyze_batch(batch, model)
                results.extend(batch_result)

            # 3. 결과 집계
            aggregated = self._aggregate_results(results)

            return ExecutionResult(
                success=True,
                data=aggregated,
                execution_time_ms=self._get_elapsed_time()
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=self._get_elapsed_time()
            )

    async def _analyze_batch(
        self,
        texts: List[str],
        model: str
    ) -> List[Dict]:
        """배치 분석 (내부 메서드)"""
        # LLM 호출 로직
        pass

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """결과 집계"""
        # 집계 로직
        pass
```

---

## 6. Tool Categories

### 6.1 Data Tools

```yaml
# 데이터 수집/처리 도구

data_collector:
  type: data
  layer: data
  description: 플랫폼에서 리뷰 데이터 수집

preprocessor:
  type: data
  layer: data
  description: 텍스트 전처리 (클리닝, 정규화)

google_trends:
  type: data
  layer: data
  description: Google Trends 데이터 수집
```

### 6.2 Analysis Tools

```yaml
# 분석 도구

sentiment_analyzer:
  type: analysis
  layer: ml
  description: 감성 분석

keyword_extractor:
  type: analysis
  layer: ml
  description: 키워드 추출

hashtag_analyzer:
  type: analysis
  layer: ml
  description: 해시태그 분석

competitor_analyzer:
  type: analysis
  layer: ml
  description: 경쟁사 분석

problem_classifier:
  type: analysis
  layer: ml
  description: 문제점 분류

insight_generator:
  type: analysis
  layer: ml
  description: 인사이트 생성
```

### 6.3 Content Tools

```yaml
# 콘텐츠 생성 도구

report_generator:
  type: content
  layer: biz
  description: 리포트 생성

video_generator:
  type: content
  layer: biz
  description: 영상 생성

ad_creative_generator:
  type: content
  layer: biz
  description: 광고 크리에이티브 생성

storyboard_generator:
  type: content
  layer: biz
  description: 스토리보드 생성
```

### 6.4 Business Tools

```yaml
# 비즈니스 운영 도구

sales_material_generator:
  type: business
  layer: biz
  description: 영업 자료 생성

inventory_manager:
  type: business
  layer: biz
  description: 재고 관리

dashboard_generator:
  type: business
  layer: biz
  description: 대시보드 생성
```

---

## 7. Tool Discovery Flow

### 7.1 Intent to Tool Mapping

```python
class IntentToolMapper:
    """의도에서 도구로 매핑"""

    INTENT_TOOL_MAP = {
        ("analysis", "sentiment"): ["preprocessor", "sentiment_analyzer"],
        ("analysis", "keyword"): ["preprocessor", "keyword_extractor"],
        ("analysis", "competitor"): ["data_collector", "competitor_analyzer"],
        ("content", "report"): ["insight_generator", "report_generator"],
        ("content", "video"): ["storyboard_generator", "video_generator"],
    }

    def map_intent_to_tools(
        self,
        intent: IntentClassificationResult
    ) -> List[str]:
        """의도를 도구 목록으로 변환"""
        key = (intent.domain, intent.category)
        return self.INTENT_TOOL_MAP.get(key, [])

    def infer_tool_chain(
        self,
        target_tool: str
    ) -> List[str]:
        """도구 체인 추론 (의존성 포함)"""
        discovery = ToolDiscovery.get_instance()
        tool_spec = discovery.get_tool(target_tool)

        if not tool_spec:
            return [target_tool]

        chain = []
        for dep in tool_spec.dependencies:
            chain.extend(self.infer_tool_chain(dep))
        chain.append(target_tool)

        return list(dict.fromkeys(chain))  # 중복 제거
```

### 7.2 Automatic Tool Selection

```python
async def select_tools_for_intent(
    intent: IntentClassificationResult,
    entities: List[Entity]
) -> List[ToolSpec]:
    """의도와 엔티티 기반 도구 자동 선택"""

    discovery = ToolDiscovery.get_instance()
    mapper = IntentToolMapper()

    # 1. 기본 도구 매핑
    base_tools = mapper.map_intent_to_tools(intent)

    # 2. 엔티티 기반 추가 도구
    for entity in entities:
        if entity.type == "competitor":
            base_tools.append("competitor_analyzer")
        if entity.type == "trend":
            base_tools.append("google_trends")

    # 3. 의존성 해결
    all_tools = []
    for tool_name in base_tools:
        chain = mapper.infer_tool_chain(tool_name)
        all_tools.extend(chain)

    # 4. 중복 제거 및 순서 유지
    seen = set()
    ordered_tools = []
    for tool_name in all_tools:
        if tool_name not in seen:
            seen.add(tool_name)
            tool_spec = discovery.get_tool(tool_name)
            if tool_spec:
                ordered_tools.append(tool_spec)

    return ordered_tools
```

---

## 8. Tool Validation

### 8.1 Parameter Validation

```python
class ToolValidator:
    """도구 파라미터 검증기"""

    def validate_params(
        self,
        tool_spec: ToolSpec,
        params: Dict[str, Any]
    ) -> ValidationResult:
        """파라미터 검증"""
        errors = []

        for param_spec in tool_spec.parameters:
            value = params.get(param_spec.name)

            # Required check
            if param_spec.required and value is None:
                errors.append(f"Missing required parameter: {param_spec.name}")
                continue

            if value is None:
                continue

            # Type check
            if not self._check_type(value, param_spec.type):
                errors.append(
                    f"Invalid type for {param_spec.name}: "
                    f"expected {param_spec.type}, got {type(value).__name__}"
                )

            # Range check (for numbers)
            if param_spec.type in ["integer", "float"]:
                if param_spec.min is not None and value < param_spec.min:
                    errors.append(f"{param_spec.name} must be >= {param_spec.min}")
                if param_spec.max is not None and value > param_spec.max:
                    errors.append(f"{param_spec.name} must be <= {param_spec.max}")

            # Enum check
            if param_spec.enum and value not in param_spec.enum:
                errors.append(
                    f"{param_spec.name} must be one of: {param_spec.enum}"
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """타입 체크"""
        type_map = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        return isinstance(value, expected) if expected else True
```

### 8.2 Output Validation

```python
def validate_output(
    tool_spec: ToolSpec,
    output: Dict[str, Any]
) -> ValidationResult:
    """출력 스키마 검증"""
    if not tool_spec.output_schema:
        return ValidationResult(valid=True)

    # JSON Schema 기반 검증
    from jsonschema import validate, ValidationError

    try:
        validate(instance=output, schema=tool_spec.output_schema)
        return ValidationResult(valid=True)
    except ValidationError as e:
        return ValidationResult(valid=False, errors=[str(e)])
```

---

## 9. Hot Reload

### 9.1 File Watcher

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ToolFileWatcher(FileSystemEventHandler):
    """도구 정의 파일 감시"""

    def __init__(self, discovery: ToolDiscovery):
        self.discovery = discovery

    def on_modified(self, event):
        if event.src_path.endswith(".yaml"):
            tool_name = Path(event.src_path).stem
            print(f"Reloading tool: {tool_name}")
            self.discovery.reload_tool(tool_name)

def start_tool_watcher():
    """파일 감시 시작"""
    discovery = ToolDiscovery.get_instance()
    handler = ToolFileWatcher(discovery)

    observer = Observer()
    observer.schedule(
        handler,
        path="app/dream_agent/tools/definitions",
        recursive=False
    )
    observer.start()
```

---

## 10. Tool Metadata

### 10.1 Cost Estimation

```python
class ToolCostEstimator:
    """도구 비용 추정"""

    def estimate_cost(
        self,
        tool_spec: ToolSpec,
        params: Dict[str, Any]
    ) -> float:
        """실행 비용 추정"""
        if not tool_spec.cost:
            return 0.0

        base_cost = tool_spec.cost.get("base_cost", 0.0)
        per_item_cost = tool_spec.cost.get("per_item_cost", 0.0)

        # 아이템 수 계산
        item_count = 1
        for param_spec in tool_spec.parameters:
            if param_spec.type == "array" and param_spec.name in params:
                item_count = len(params[param_spec.name])
                break

        return base_cost + (per_item_cost * item_count)

    def estimate_plan_cost(
        self,
        todos: List[TodoItem]
    ) -> float:
        """전체 플랜 비용 추정"""
        discovery = ToolDiscovery.get_instance()
        total_cost = 0.0

        for todo in todos:
            tool_spec = discovery.get_tool(todo.tool_name)
            if tool_spec:
                total_cost += self.estimate_cost(tool_spec, todo.tool_params)

        return total_cost
```

---

## 11. Available Tools Summary

| Tool Name | Type | Layer | Description |
|-----------|------|-------|-------------|
| `data_collector` | data | data | 플랫폼 리뷰 데이터 수집 |
| `preprocessor` | data | data | 텍스트 전처리 |
| `google_trends` | data | data | Google Trends 수집 |
| `sentiment_analyzer` | analysis | ml | 감성 분석 |
| `keyword_extractor` | analysis | ml | 키워드 추출 |
| `hashtag_analyzer` | analysis | ml | 해시태그 분석 |
| `competitor_analyzer` | analysis | ml | 경쟁사 분석 |
| `problem_classifier` | analysis | ml | 문제점 분류 |
| `insight_generator` | analysis | ml | 인사이트 생성 |
| `report_generator` | content | biz | 리포트 생성 |
| `video_generator` | content | biz | 영상 생성 |
| `ad_creative_generator` | content | biz | 광고 크리에이티브 생성 |
| `storyboard_generator` | content | biz | 스토리보드 생성 |
| `sales_material_generator` | business | biz | 영업 자료 생성 |
| `inventory_manager` | business | biz | 재고 관리 |
| `dashboard_generator` | business | biz | 대시보드 생성 |

---

## Related Documents
- [DATA_MODELS_260205.md](DATA_MODELS_260205.md) - ToolSpec model definition
- [LAYER_SPEC_260205.md](LAYER_SPEC_260205.md) - Execution layer tools
- [ARCHITECTURE_260205.md](ARCHITECTURE_260205.md) - System architecture
