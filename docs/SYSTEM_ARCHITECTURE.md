# Dream Agent 시스템 아키텍처

> **문서 상태 범례**
> - ✅ 구현 완료
> - ⚠️ 부분 구현 / 검토 필요
> - ❌ 미구현
> - 🔧 사용자 결정 필요

> **참고**: 상세 레이어 문서는 [README/03_AGENT_LAYERS.md](../README/03_AGENT_LAYERS.md) 참조

---

## 1. 개요

Dream Agent는 **4-Layer Hand-off 아키텍처** 기반의 K-Beauty 글로벌 트렌드 분석 AI 에이전트입니다.
LangGraph StateGraph를 활용하여 각 레이어 간 상태 전이를 관리합니다.

---

## 2. 시스템 구조 ✅

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard (HTML/CSS/JS)                       │
│              FastAPI StaticFiles로 서빙 (Flask 아님!)            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│            api/main.py → uvicorn 실행                            │
│            WebSocket 실시간 통신 포함                             │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  Tool System  │      │   Executors   │      │   LLM Layer   │
│  (YAML 기반)  │      │ (Domain별)    │      │ (gpt-4o-mini) │
└───────────────┘      └───────────────┘      └───────────────┘
```

---

## 3. 4-Layer Hand-off 아키텍처 ✅

### 3.1 레이어 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                 Layer 1: COGNITIVE (의도 파악)                   │
│  - IntentClassifier: 의도 분류 (Domain/Category/Subcategory)    │
│  - EntityExtractor: 엔티티 추출                                  │
│  - DialogueManager: 대화 컨텍스트 관리                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ Intent, Entities
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Layer 2: PLANNING (작업 계획)                    │
│  - LLM 기반 계획 생성                                            │
│  - Todo 자동 생성 및 의존성 관리 (Topological Sort)              │
│  - 실행 그래프 (Mermaid)                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ Plan, TodoItems
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Layer 3: EXECUTION (실행)                        │
│  - ExecutionSupervisor: Todo 라우팅                              │
│  - DataExecutor: 데이터 수집/처리                                │
│  - InsightExecutor: 분석/인사이트                                │
│  - ContentExecutor: 콘텐츠 생성                                  │
│  - OpsExecutor: 운영 작업                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ ExecutionResults
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Layer 4: RESPONSE (응답 생성)                    │
│  - 결과 요약                                                     │
│  - 마크다운 포맷팅                                               │
│  - 보고서 저장                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 TodoItem.layer 값

| layer | 설명 | Executor |
|-------|------|----------|
| `cognitive` | 인지 레이어 | - |
| `planning` | 계획 레이어 | - |
| `ml_execution` | ML 분석 실행 | DataExecutor, InsightExecutor |
| `biz_execution` | 비즈니스 로직 | ContentExecutor, OpsExecutor |
| `response` | 응답 생성 | - |

### 3.3 Executor 매핑 ✅

```python
TOOL_TO_EXECUTOR = {
    # DataExecutor
    "collector": "data_executor",
    "preprocessor": "data_executor",
    "google_trends": "data_executor",

    # InsightExecutor
    "sentiment_analyzer": "insight_executor",
    "keyword_extractor": "insight_executor",
    "hashtag_analyzer": "insight_executor",
    "problem_classifier": "insight_executor",
    "competitor_analyzer": "insight_executor",
    "insight_generator": "insight_executor",

    # ContentExecutor
    "video_agent": "content_executor",
    "ad_creative_agent": "content_executor",
    "storyboard_agent": "content_executor",
    "report_generator": "content_executor",

    # OpsExecutor
    "dashboard_agent": "ops_executor",
    "sales_agent": "ops_executor",
    "inventory_agent": "ops_executor",
}
```

---

## 4. 핵심 컴포넌트

### 4.1 LangGraph Orchestrator ✅

> 위치: `orchestrator/`

```python
# orchestrator/builder.py
workflow = StateGraph(AgentState)

workflow.add_node("cognitive", cognitive_node)
workflow.add_node("planning", planning_node)
workflow.add_node("execution", execution_node)
workflow.add_node("response", response_node)
```

### 4.2 데이터 구조 주의사항 ⚠️

#### 4.2.1 이중 Intent 시스템

시스템 내 두 가지 Intent 표현 방식이 공존합니다:

| 구분 | 레거시 (Dict) | 신규 (Pydantic) |
|------|--------------|--------------------|
| 위치 | cognitive_node.py 출력 | models/intent.py |
| 키/필드 | `intent_type` (문자열) | `domain` (IntentDomain Enum) |
| 사용처 | AgentState, planning_node | schemas/planning.py |

**현재 동작**:
- `cognitive_node`는 항상 레거시 dict 형식(`intent_type` 키)을 반환
- `AgentState["intent"]`는 `dict` 타입으로 정의됨
- Planning/Execution 레이어에서 `intent.get("intent_type")` 방식으로 접근

```python
# AgentState에서의 intent 정의 (states/base.py)
class AgentState(TypedDict, total=False):
    intent: dict  # ← dict, NOT Intent Pydantic model
```

#### 4.2.2 스키마 사용 현황

`schemas/` 디렉토리의 I/O 스키마는 **문서화/명세 목적**으로 정의되어 있으며,
실제 노드 코드에서는 사용되지 않습니다. 런타임 검증은 각 노드에서 직접 수행됩니다.

| 스키마 | 정의 위치 | 실제 사용 | 상태 |
|--------|----------|----------|------|
| CognitiveInput/Output | schemas/cognitive.py | 노드에서 미사용 | 📝 문서용 |
| PlanningInput/Output | schemas/planning.py | 노드에서 미사용 | 📝 문서용 |
| ExecutionInput/Output | schemas/execution.py | 노드에서 미사용 | 📝 문서용 |
| ResponseInput/Output | schemas/response.py | 노드에서 미사용 | 📝 문서용 |

#### 4.2.3 ExecutionResult 클래스

두 개의 ExecutionResult 클래스가 존재합니다:

| 위치 | 타입 | 용도 |
|------|------|------|
| `models/execution.py` | Pydantic BaseModel | API/스키마 표준 |
| `execution/core/base_executor.py` | Plain Python class | Executor 내부 사용 |

> ⚠️ 동일 이름으로 인한 import 혼동 가능성 있음

---

### 4.3 Tool System (Phase 0-3) ✅

| Phase | 기능 | 파일 |
|-------|------|------|
| Phase 0 | YAML 기반 Tool Discovery | `discovery.py`, `loader.py` |
| Phase 1 | ToolSpec ↔ BaseTool 호환 | `compat.py` |
| Phase 2 | Hot Reload | `hot_reload.py` |
| Phase 3 | Validator | `validator.py` |

### 4.3 Workflow Manager ✅

```
workflow_manager/
├── planning_manager/         # 계획 관리
│   ├── plan_manager.py
│   ├── execution_graph_builder.py
│   ├── resource_planner.py
│   └── sync_manager.py
├── todo_manager/             # Todo 관리
│   ├── todo_manager.py
│   ├── todo_creator.py
│   ├── todo_updater.py
│   ├── todo_store.py
│   ├── todo_validator.py
│   ├── todo_queries.py
│   └── todo_failure_recovery.py
├── hitl_manager/             # Human-in-the-Loop
│   ├── decision_manager.py
│   ├── input_requester.py
│   ├── pause_controller.py
│   ├── plan_editor.py
│   ├── nl_plan_modifier.py
│   └── replan_manager.py
├── feedback_manager/         # 피드백 관리
│   ├── feedback_manager.py
│   ├── plan_edit_logger.py
│   ├── query_logger.py
│   └── result_evaluator.py
├── approval_manager.py
├── base_manager.py
├── manager_registry.py
└── todo_failure_recovery.py
```

---

## 5. 디렉토리 구조 (전체) ✅

```
beta_v001/
├── backend/
│   ├── api/                          # FastAPI 애플리케이션
│   │   ├── main.py                   # ✅ 엔트리포인트
│   │   ├── routes/
│   │   │   ├── agent.py              # /api/agent/*
│   │   │   ├── websocket.py          # /ws/*
│   │   │   └── health.py             # /health
│   │   ├── schemas/
│   │   │   ├── agent.py
│   │   │   └── websocket.py
│   │   └── middleware/
│   │
│   ├── app/
│   │   ├── core/                     # 코어 설정
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── file_storage.py
│   │   │
│   │   └── dream_agent/
│   │       ├── cognitive/            # Layer 1
│   │       │   ├── cognitive_node.py
│   │       │   ├── intent_classifier.py
│   │       │   ├── entity_extractor.py  # ← 누락되어있었음
│   │       │   ├── dialogue_manager.py
│   │       │   ├── intent_types.py
│   │       │   ├── language_detector.py
│   │       │   └── kbeauty_context.py
│   │       │
│   │       ├── planning/             # Layer 2
│   │       │   ├── planning_node.py
│   │       │   ├── dependency_calculator.py
│   │       │   ├── intent_mapper.py
│   │       │   └── tool_catalog.py
│   │       │
│   │       ├── execution/            # Layer 3
│   │       │   ├── execution_node.py
│   │       │   ├── supervisor.py
│   │       │   ├── data_executor.py
│   │       │   ├── insight_executor.py
│   │       │   ├── content_executor.py
│   │       │   ├── ops_executor.py
│   │       │   ├── core/
│   │       │   │   ├── base_executor.py
│   │       │   │   ├── executor_registry.py
│   │       │   │   └── execution_cache.py
│   │       │   └── domain/           # (아래 참조)
│   │       │
│   │       ├── response/             # Layer 4
│   │       │   └── response_node.py
│   │       │
│   │       ├── orchestrator/         # LangGraph
│   │       │   ├── builder.py
│   │       │   ├── router.py
│   │       │   └── checkpointer.py
│   │       │
│   │       ├── tools/
│   │       │   ├── definitions/      # YAML (18개)
│   │       │   ├── discovery.py
│   │       │   ├── loader.py
│   │       │   ├── compat.py
│   │       │   ├── hot_reload.py
│   │       │   ├── validator.py
│   │       │   ├── base_tool.py
│   │       │   ├── tool_registry.py
│   │       │   ├── analysis/         # 도구 클래스
│   │       │   ├── business/
│   │       │   ├── content/
│   │       │   ├── data/
│   │       │   └── utils/
│   │       │
│   │       ├── models/
│   │       │   ├── intent.py
│   │       │   ├── todo.py
│   │       │   ├── plan.py
│   │       │   ├── execution.py
│   │       │   ├── execution_graph.py
│   │       │   ├── results.py
│   │       │   ├── resource.py
│   │       │   └── tool.py
│   │       │
│   │       ├── schemas/
│   │       │   ├── cognitive.py
│   │       │   ├── planning.py
│   │       │   ├── execution.py
│   │       │   ├── response.py
│   │       │   └── tool_io/
│   │       │
│   │       ├── states/
│   │       │   ├── base.py
│   │       │   ├── reducers.py
│   │       │   └── accessors.py
│   │       │
│   │       ├── llm_manager/
│   │       │   ├── client.py
│   │       │   ├── config_loader.py
│   │       │   ├── prompts.py
│   │       │   └── configs/          # YAML 설정
│   │       │       ├── data_sources.yaml
│   │       │       ├── intent_keywords.yaml
│   │       │       ├── tool_settings.yaml
│   │       │       └── prompts/
│   │       │
│   │       ├── callbacks/
│   │       └── workflow_manager/     # (위 참조)
│   │
│   └── scripts/
│       └── setup_checkpointer.py
│
├── dashboard/                        # HTML 대시보드 (FastAPI 서빙)
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
│
├── tests/                            # 테스트
│   ├── unit/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── tools/
│   ├── integration/
│   └── e2e/
│
├── data/                             # 데이터 저장소
├── docs/                             # 이 문서들
├── README/                           # 상세 개발 문서 (기존)
├── frontend/                         # (비어있음)
└── reports_mind_dream/               # 생성된 보고서
```

---

## 6. Domain Agents 구조 ✅

```
execution/domain/
├── base_agent.py                     # BaseDomainAgent

├── collection/
│   ├── collector/collector_agent.py           # ✅
│   └── preprocessor/preprocessor_agent.py     # ✅

├── analysis/
│   ├── sentiment/sentiment_analyzer_agent.py  # ✅
│   ├── keyword/keyword_extractor_agent.py     # ✅
│   ├── hashtag/hashtag_analyzer_agent.py      # ✅
│   ├── classifier/problem_classifier_agent.py # ✅
│   ├── competitor/competitor_analyzer_agent.py# ✅
│   └── trends/google_trends_agent.py          # ✅

├── insight/
│   └── insight_generator/insight_generator_agent.py  # ✅

├── content/
│   ├── video/
│   │   ├── video_agent_graph.py               # ✅
│   │   ├── video_agent_graph_v2.py            # ✅
│   │   ├── llm/                               # LLM 생성기
│   │   ├── postprocess/                       # 후처리
│   │   └── runpod/                            # RunPod 연동
│   ├── ad_creative/
│   │   ├── ad_creative_agent_tool.py          # ✅ (16KB)
│   │   └── ad_creative_generator.py
│   └── storyboard/
│       ├── storyboard_agent_tool.py           # ✅ (15KB)
│       └── video_agent_tool.py

├── report/
│   ├── report_agent.py
│   ├── report_agent_tool.py
│   └── report_agent/
│       └── report_agent_graph.py              # ✅

├── ops/
│   ├── dashboard/dashboard_agent_tool.py      # ✅ (14KB)
│   ├── sales/sales_material_generator.py      # ⚠️ 이름 다름
│   └── inventory/__init__.py                  # ❌ 미구현

└── toolkit/                                   # 공용 유틸리티
```

---

## 7. 기술 스택 ✅

| 영역 | 기술 | 상태 |
|------|------|------|
| Backend | FastAPI | ✅ |
| Entry Point | `uvicorn api.main:app` | ✅ |
| Workflow | LangGraph (StateGraph) | ✅ |
| LLM | OpenAI (gpt-4o-mini) | ✅ |
| Validation | Pydantic v2 | ✅ |
| Dashboard | FastAPI StaticFiles | ✅ |
| 실시간 통신 | WebSocket | ✅ |
| 설정 관리 | YAML | ✅ |
| 테스트 | pytest | ✅ |
| Database | PostgreSQL (Checkpoint) | ⚠️ |
| Cache | Redis | ❌ Phase 2 |

---

## 8. 서버 실행 ✅

```bash
# 1. 환경 변수 설정
cp .env.example .env

# 2. 서버 실행
cd backend
uvicorn api.main:app --reload --port 8000

# 3. 대시보드 접속
# http://localhost:8000
```

---

## 🔧 사용자 결정 필요 사항

| 항목 | 현재 | 옵션 |
|------|------|------|
| 세션 저장소 | In-memory | Redis / PostgreSQL |
| inventory_agent | 미구현 | 구현 / YAML 제거 |
| sales_agent 이름 | 불일치 | 통일 필요 |
| frontend/ | 비어있음 | React 개발 / 제거 |
