# Service Agent 시스템 - LangGraph 0.6 기반 멀티 에이전트 챗봇

## 📋 개요

LangGraph 0.6를 기반으로 구축된 부동산 전문 AI 상담 챗봇 시스템입니다. 팀 기반 아키텍처를 통해 법률 검색, 시세 조회, 대출 상담, 계약서 작성 등의 복합적인 작업을 처리합니다.

### 주요 특징

- **LangGraph 0.6** 기반 상태 관리 및 워크플로우
- **팀 기반 아키텍처**: Search, Analysis, Document 팀의 독립적 운영
- **실시간 WebSocket 지원**: 작업 진행상황 실시간 전송
- **LLM 기반 동적 의사결정**: 도구 선택 및 에이전트 라우팅
- **AsyncSqliteSaver**: 체크포인트 기반 대화 상태 영속화

---

## 🏗️ 디렉토리 구조

```
backend/app/service_agent/
├── supervisor/                # 메인 그래프 - 팀 조율 및 워크플로우 관리
│   ├── __init__.py
│   └── team_supervisor.py    # [핵심] 메인 Supervisor - 3개 팀 오케스트레이션
│
├── cognitive_agents/          # 분석 및 계획 수립
│   ├── __init__.py
│   ├── planning_agent.py      # [핵심] 의도 분석 및 실행 계획 생성
│   └── query_decomposer.py    # 복합 질문 분해 (Phase 1 Enhancement)
│
├── execution_agents/          # 실행 에이전트 (3개 팀)
│   ├── __init__.py
│   ├── search_executor.py     # [핵심] SearchTeam - 법률/부동산/대출 검색
│   ├── analysis_executor.py   # [핵심] AnalysisTeam - 데이터 분석 및 인사이트
│   └── document_executor.py   # [핵심] DocumentTeam - 문서 생성 및 검토
│
├── foundation/                # 설정 및 공통 인프라
│   ├── __init__.py
│   ├── config.py              # [핵심] 시스템 설정 (DB 경로, 모델, 타임아웃)
│   ├── separated_states.py    # [핵심] 팀별 State 정의 (TypedDict)
│   ├── context.py             # [핵심] LLMContext, AgentContext 정의
│   ├── agent_registry.py      # [핵심] 중앙화된 Agent 등록 및 관리
│   ├── agent_adapter.py       # [핵심] 팀/에이전트 동적 실행 어댑터
│   ├── checkpointer.py        # [핵심] AsyncSqliteSaver 체크포인터 관리
│   └── decision_logger.py     # [핵심] LLM 의사결정 로깅 (SQLite)
│
├── llm_manager/               # LLM 관리
│   ├── __init__.py
│   ├── llm_service.py         # [핵심] 중앙화된 LLM 호출 관리
│   ├── prompt_manager.py      # [핵심] 프롬프트 템플릿 로드 및 변수 치환
│   ├── prompt_manager_old.py  # [미사용] 구버전 프롬프트 매니저
│   └── prompts/               # 프롬프트 템플릿 디렉토리 (TXT/YAML)
│       ├── cognitive/         # 의도 분석, 계획 수립
│       ├── execution/         # 키워드 추출, 인사이트 생성
│       └── common/            # 공통 프롬프트
│
├── tools/                     # 도구들 - 실제 작업 수행
│   ├── __init__.py
│   ├── hybrid_legal_search.py        # [핵심] 법률 검색 (ChromaDB + SQLite)
│   ├── market_data_tool.py           # [핵심] 부동산 시세 조회
│   ├── loan_data_tool.py             # [핵심] 대출 상품 검색
│   ├── analysis_tools.py             # [사용 중] 분석 도구 베이스 클래스
│   ├── contract_analysis_tool.py     # [핵심] 계약서 위험 분석
│   ├── market_analysis_tool.py       # [핵심] 시장 동향 분석
│   ├── roi_calculator_tool.py        # [핵심] 투자수익률 계산
│   ├── loan_simulator_tool.py        # [핵심] 대출 한도 시뮬레이션
│   ├── policy_matcher_tool.py        # [핵심] 정부 정책 매칭
│   └── lease_contract_generator_tool.py  # [핵심] 임대차계약서 생성
│
├── tests/                     # 단위 테스트
│   ├── test_process_flow_api.py      # ProcessFlow API 테스트
│   └── test_status_tracking.py       # 상태 추적 테스트
│
└── reports/                   # 보고서 및 문서 (제외 요청됨)
    └── tests/                 # 검증 테스트 스크립트

```

---

## 🔑 핵심 파일 상세 설명

### 1. **supervisor/team_supervisor.py** - 메인 Supervisor

**역할**: 전체 시스템의 두뇌. 3개 팀(Search, Analysis, Document)을 조율하고 워크플로우를 관리합니다.

**핵심 기능**:
- **Planning**: PlanningAgent를 통한 의도 분석 및 실행 계획 수립
- **Team Orchestration**: 팀별 실행 조율 (순차/병렬)
- **WebSocket 실시간 통신**: `_progress_callbacks`로 진행상황 전송
- **Response Generation**: LLM 기반 최종 응답 생성
- **Checkpoint 관리**: AsyncSqliteSaver로 대화 상태 영속화

**주요 메서드**:
```python
async def process_query_streaming(query, session_id, progress_callback)
async def planning_node(state)  # 계획 수립
async def execute_teams_node(state)  # 팀 실행
async def generate_response_node(state)  # 응답 생성
```

**상태 흐름**:
```
START → initialize → planning → [execute_teams → aggregate] → generate_response → END
```

---

### 2. **cognitive_agents/planning_agent.py** - 의도 분석 및 계획 수립

**역할**: 사용자 쿼리를 분석하고 어떤 팀을 어떤 순서로 실행할지 결정합니다.

**핵심 기능**:
- **Intent Analysis**: LLM 기반 의도 분석 (9가지 의도 타입)
  - `LEGAL_CONSULT`, `MARKET_INQUIRY`, `LOAN_CONSULT`, `CONTRACT_CREATION`, etc.
- **Agent Selection**: 다층 Fallback 전략으로 안전한 에이전트 선택
  - Primary LLM → Simplified LLM → Safe Defaults
- **Execution Plan**: 실행 계획 생성 (순차/병렬 전략 결정)
- **Query Decomposition**: 복합 질문 분해 (QueryDecomposer 통합)

**의도 타입**:
```python
class IntentType(Enum):
    LEGAL_CONSULT = "법률상담"
    MARKET_INQUIRY = "시세조회"
    LOAN_CONSULT = "대출상담"
    CONTRACT_CREATION = "계약서작성"
    CONTRACT_REVIEW = "계약서검토"
    COMPREHENSIVE = "종합분석"
    RISK_ANALYSIS = "리스크분석"
    UNCLEAR = "unclear"
    IRRELEVANT = "irrelevant"
```

**LLM 기반 동적 결정**:
- 프롬프트: `intent_analysis`, `agent_selection`, `agent_selection_simple`
- Fallback: 패턴 매칭 → 기본 에이전트

---

### 3. **execution_agents/search_executor.py** - SearchTeam

**역할**: 법률, 부동산, 대출 정보를 검색하는 팀입니다.

**핵심 기능**:
- **LLM Tool Selection**: 사용자 쿼리 기반으로 필요한 도구만 선택
  - `legal_search`, `market_data`, `loan_data`
- **Hybrid Legal Search**: ChromaDB (벡터 검색) + SQLite (메타데이터)
- **Parallel Execution**: 독립적인 검색 작업 병렬 실행
- **Decision Logging**: 도구 선택 근거 및 실행 결과 로깅

**워크플로우**:
```
prepare → route → search → aggregate → finalize
```

**도구**:
- `HybridLegalSearch`: 주택임대차보호법 등 법률 조항 검색
- `MarketDataTool`: 지역별 부동산 시세 조회
- `LoanDataTool`: 대출 상품 정보 검색

---

### 4. **execution_agents/analysis_executor.py** - AnalysisTeam

**역할**: 수집된 데이터를 분석하여 인사이트와 추천사항을 생성합니다.

**핵심 기능**:
- **LLM Tool Selection**: 수집된 데이터 기반으로 분석 도구 선택
- **5가지 분석 도구**:
  - `ContractAnalysisTool`: 계약서 위험 조항 탐지
  - `MarketAnalysisTool`: 시장 동향 및 가격 적정성 분석
  - `ROICalculatorTool`: 투자수익률 계산
  - `LoanSimulatorTool`: 대출 한도 시뮬레이션 (LTV/DTI/DSR)
  - `PolicyMatcherTool`: 정부 지원 정책 매칭
- **Custom Analysis**: 전세금 인상률 등 특정 시나리오 분석
- **LLM Insight Generation**: 분석 결과를 사용자 친화적 인사이트로 변환

**워크플로우**:
```
prepare → preprocess → analyze → generate_insights → create_report → finalize
```

---

### 5. **execution_agents/document_executor.py** - DocumentTeam

**역할**: 부동산 관련 법률 문서를 생성하고 검토합니다.

**핵심 기능**:
- **템플릿 기반 문서 생성**: 주택임대차계약서, 매매계약서 등
- **LeaseContractGeneratorTool**: HWP 템플릿 기반 계약서 생성
- **Document Review**: 생성된 문서의 법적 위험 요소 검토
- **Pipeline Architecture**: 생성 → 검토 파이프라인

**워크플로우**:
```
prepare → generate → review_check → [review] → finalize
```

---

### 6. **foundation/separated_states.py** - State 정의

**역할**: LangGraph State 정의. 팀별 독립적인 State로 State pollution 방지.

**핵심 State 타입**:
- `SharedState`: 모든 팀이 공유하는 최소 상태
- `SearchTeamState`: 검색 팀 전용
- `AnalysisTeamState`: 분석 팀 전용
- `DocumentTeamState`: 문서 팀 전용
- `MainSupervisorState`: Supervisor 상태
- `PlanningState`: 계획 수립 상태 (execution_steps 포함)

**ExecutionStepState** (TODO 아이템):
```python
class ExecutionStepState(TypedDict):
    step_id: str                    # "step_0", "step_1"
    step_type: str                  # "search", "analysis", "document"
    agent_name: str                 # "search_team"
    team: str                       # "search"
    task: str                       # "법률 정보 검색"
    description: str                # 상세 설명
    status: Literal["pending", "in_progress", "completed", "failed"]
    progress_percentage: int        # 0-100
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict]
    error: Optional[str]
```

**유틸리티 클래스**:
- `StateManager`: State 변환 및 관리
- `StateValidator`: State 유효성 검증
- `StateTransition`: State 전환 헬퍼

---

### 7. **foundation/agent_registry.py** - Agent 등록 시스템

**역할**: 중앙화된 Agent 관리. 팀과 에이전트를 동적으로 등록하고 조회합니다.

**핵심 기능**:
- **동적 등록**: `register()` 메서드로 Agent 등록
- **Capability 기반 검색**: 입출력 타입, 필요한 도구로 Agent 검색
- **팀별 관리**: 팀 단위 Agent 그룹화
- **싱글톤 패턴**: 전역 레지스트리

**사용 예**:
```python
AgentRegistry.register(
    name="search_team",
    agent_class=SearchTeamPlaceholder,
    team="search",
    capabilities=capabilities,
    enabled=True
)
```

---

### 8. **foundation/checkpointer.py** - Checkpoint 관리

**역할**: AsyncSqliteSaver 기반 체크포인트 관리. 대화 상태 영속화.

**핵심 기능**:
- **AsyncSqliteSaver 관리**: 비동기 컨텍스트 매니저 생명주기 관리
- **세션별 체크포인트**: `session_id` 기반 상태 저장
- **자동 재시작**: 중단된 대화 재개 지원

**사용 예**:
```python
checkpointer = await create_checkpointer()
config = {"configurable": {"thread_id": session_id}}
result = await app.ainvoke(state, config=config)
```

---

### 9. **llm_manager/llm_service.py** - LLM 호출 관리

**역할**: 모든 LLM 호출을 중앙화하여 일관성과 에러 핸들링 제공.

**핵심 기능**:
- **OpenAI 클라이언트 관리**: 동기/비동기 클라이언트 싱글톤
- **프롬프트 기반 호출**: PromptManager 통합
- **JSON 응답 파싱**: `complete_json()`, `complete_json_async()`
- **Retry 로직**: 에러 발생 시 재시도
- **모델 선택**: 프롬프트별 최적 모델 자동 선택

**주요 메서드**:
```python
async def complete_async(prompt_name, variables, temperature, max_tokens)
async def complete_json_async(prompt_name, variables, ...)  # JSON 응답 전용
```

---

### 10. **llm_manager/prompt_manager.py** - 프롬프트 관리

**역할**: 프롬프트 템플릿 로드 및 변수 치환.

**핵심 기능**:
- **파일 기반 프롬프트**: TXT/YAML 파일 로드
- **안전한 변수 치환**: 코드 블록 보호 (f-string 대신 regex)
- **프롬프트 캐싱**: 성능 최적화
- **카테고리 자동 탐색**: cognitive/execution/common

**디렉토리 구조**:
```
llm_manager/prompts/
├── cognitive/
│   ├── intent_analysis.txt
│   ├── agent_selection.txt
│   └── agent_selection_simple.txt
├── execution/
│   ├── keyword_extraction.txt
│   ├── tool_selection_search.txt
│   ├── tool_selection_analysis.txt
│   └── insight_generation.txt
└── common/
    ├── response_synthesis.txt
    └── error_response.txt
```

---

### 11. **tools/** - 도구 모음

#### **검색 도구**:
- **hybrid_legal_search.py**: 법률 조항 하이브리드 검색 (ChromaDB + SQLite)
- **market_data_tool.py**: 부동산 시세 조회 (Mock 데이터)
- **loan_data_tool.py**: 대출 상품 검색 (Mock 데이터)

#### **분석 도구**:
- **contract_analysis_tool.py**: 계약서 위험 조항 탐지
- **market_analysis_tool.py**: 시장 동향 분석
- **roi_calculator_tool.py**: 투자수익률 계산
- **loan_simulator_tool.py**: 대출 한도 시뮬레이션 (LTV/DTI/DSR)
- **policy_matcher_tool.py**: 정부 정책 매칭

#### **문서 도구**:
- **lease_contract_generator_tool.py**: HWP 템플릿 기반 계약서 생성

---

## 🚫 미사용 파일

### **llm_manager/prompt_manager_old.py** - [미사용]

**이유**: 구버전 프롬프트 매니저입니다. 현재는 `prompt_manager.py`를 사용합니다.

**추천 조치**: 삭제 가능. 백업이 필요하면 Git 히스토리에서 복원 가능.

---

## 📊 시스템 아키텍처

### 전체 흐름도

```
User Query
    ↓
TeamBasedSupervisor
    ↓
    ├─→ PlanningAgent (의도 분석 + 계획 수립)
    ↓
    ├─→ SearchExecutor (법률/시세/대출 검색)
    │       ↓
    │       ├─→ LLM Tool Selection
    │       ├─→ HybridLegalSearch
    │       ├─→ MarketDataTool
    │       └─→ LoanDataTool
    ↓
    ├─→ AnalysisExecutor (데이터 분석)
    │       ↓
    │       ├─→ LLM Tool Selection
    │       ├─→ ContractAnalysisTool
    │       ├─→ MarketAnalysisTool
    │       ├─→ ROICalculatorTool
    │       ├─→ LoanSimulatorTool
    │       └─→ PolicyMatcherTool
    ↓
    ├─→ DocumentExecutor (문서 생성/검토)
    │       ↓
    │       └─→ LeaseContractGeneratorTool
    ↓
    └─→ Response Generation (LLM 기반 최종 응답)
```

### State 관리

```
MainSupervisorState
    ├─ planning_state (PlanningState)
    ├─ search_team_state (SearchTeamState)
    ├─ analysis_team_state (AnalysisTeamState)
    ├─ document_team_state (DocumentTeamState)
    └─ final_response
```

### LLM 의사결정 포인트

1. **Intent Analysis** (planning_agent.py)
   - 프롬프트: `intent_analysis`
   - 출력: 의도 타입, 키워드, 엔티티, Confidence

2. **Agent Selection** (planning_agent.py)
   - 프롬프트: `agent_selection`, `agent_selection_simple`
   - 출력: 선택된 에이전트 목록, Reasoning

3. **Tool Selection - Search** (search_executor.py)
   - 프롬프트: `tool_selection_search`
   - 출력: 선택된 검색 도구 목록 (`legal_search`, `market_data`, `loan_data`)

4. **Tool Selection - Analysis** (analysis_executor.py)
   - 프롬프트: `tool_selection_analysis`
   - 출력: 선택된 분석 도구 목록 (`contract_analysis`, `market_analysis`, ...)

5. **Insight Generation** (analysis_executor.py)
   - 프롬프트: `insight_generation`
   - 출력: 사용자 친화적 인사이트

6. **Response Synthesis** (team_supervisor.py)
   - 프롬프트: `response_synthesis`
   - 출력: 최종 응답 (JSON 형식)

---

## 🔧 설정 파일

### **foundation/config.py**

시스템 전역 설정을 관리합니다.

**주요 설정**:
- **DB 경로**: `DATABASES`, `LEGAL_PATHS`
- **모델 설정**: `LLM_DEFAULTS` - 프롬프트별 모델 매핑
- **타임아웃**: `TIMEOUTS` - Agent, LLM 타임아웃
- **Feature Flags**: `FEATURES` - LLM Planning 활성화 등

**프롬프트별 모델 매핑**:
```python
"models": {
    "intent_analysis": "gpt-4o-mini",
    "plan_generation": "gpt-4o-mini",
    "keyword_extraction": "gpt-4o-mini",
    "insight_generation": "gpt-4o",
    "response_synthesis": "gpt-4o-mini",
}
```

---

## 🚀 실행 방법

### 1. Supervisor 인스턴스 생성

```python
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.context import create_default_llm_context

llm_context = create_default_llm_context()
supervisor = TeamBasedSupervisor(llm_context=llm_context, enable_checkpointing=True)
```

### 2. 쿼리 처리 (WebSocket 실시간 통신)

```python
async def progress_callback(event_type: str, event_data: dict):
    """WebSocket으로 진행상황 전송"""
    await websocket.send_json({
        "type": event_type,
        "data": event_data
    })

result = await supervisor.process_query_streaming(
    query="전세금 5% 인상이 가능한가요?",
    session_id="session_abc123",
    progress_callback=progress_callback
)
```

### 3. 응답 확인

```python
print(result["final_response"])
# {
#   "type": "answer",
#   "answer": "네, 전세금 5% 인상은 법정 한도 내에서 가능합니다...",
#   "teams_used": ["search", "analysis"],
#   "data": {...}
# }
```

---

## 📝 로깅 및 디버깅

### Decision Logger

**foundation/decision_logger.py**가 모든 LLM 의사결정을 SQLite에 기록합니다.

**DB 경로**: `backend/data/system/agent_logging/decisions.db`

**테이블**:
- `agent_decisions`: 에이전트 선택 결정
- `tool_decisions`: 도구 선택 결정

**쿼리 예시**:
```sql
SELECT * FROM tool_decisions
WHERE agent_type = 'search'
ORDER BY timestamp DESC LIMIT 10;
```

---

## 🔄 확장 가이드

### 새로운 팀 추가

1. **Executor 생성**: `execution_agents/new_team_executor.py`
2. **State 정의**: `separated_states.py`에 `NewTeamState` 추가
3. **Registry 등록**: `agent_adapter.py`에서 팀 등록
4. **Supervisor 통합**: `team_supervisor.py`에서 팀 초기화

### 새로운 도구 추가

1. **도구 클래스 생성**: `tools/new_tool.py`
2. **Executor 통합**: 해당 Executor의 `_initialize_tools()`에 추가
3. **LLM Tool Selection**: `_get_available_tools()`에 메타데이터 추가

---

## 📚 참고 자료

- **LangGraph 0.6 문서**: https://langchain-ai.github.io/langgraph/
- **AsyncSqliteSaver**: https://langchain-ai.github.io/langgraph/reference/checkpoints/
- **OpenAI API**: https://platform.openai.com/docs/

---

## 👥 팀 구성원 및 역할

| 팀 | 역할 | 주요 도구 |
|---|---|---|
| **SearchTeam** | 법률/부동산/대출 정보 검색 | HybridLegalSearch, MarketDataTool, LoanDataTool |
| **AnalysisTeam** | 데이터 분석 및 인사이트 도출 | ContractAnalysisTool, MarketAnalysisTool, ROICalculatorTool, LoanSimulatorTool, PolicyMatcherTool |
| **DocumentTeam** | 계약서 생성 및 검토 | LeaseContractGeneratorTool |

---

## 🎯 핵심 개념 정리

### 1. **LangGraph State**
- TypedDict 기반 강타입 State 정의
- 팀별 독립적인 State로 State pollution 방지
- `MainSupervisorState` → `SearchTeamState`, `AnalysisTeamState`, `DocumentTeamState`

### 2. **LLM 기반 동적 의사결정**
- **Agent Selection**: 의도에 따라 실행할 팀 선택
- **Tool Selection**: 팀 내에서 필요한 도구만 선택
- **Insight Generation**: 분석 결과를 사용자 친화적으로 변환

### 3. **Checkpoint 영속화**
- AsyncSqliteSaver로 대화 상태 저장
- `session_id` (thread_id)로 세션 관리
- 중단된 대화 재개 지원

### 4. **WebSocket 실시간 통신**
- `_progress_callbacks`로 진행상황 전송
- `execution_steps` (TODO 아이템) 상태 업데이트
- Frontend ProcessFlow UI와 동기화

---

## ⚠️ 주의사항

1. **Callable은 State에 포함하지 마세요**
   - LangGraph Checkpoint가 msgpack으로 직렬화할 때 에러 발생
   - `_progress_callbacks`는 Supervisor 인스턴스에서 별도 관리

2. **LLM API Key 필수**
   - `OPENAI_API_KEY` 환경변수 설정 필요
   - `backend/.env` 파일에 정의

3. **ChromaDB 경로**
   - 법률 검색을 위해 ChromaDB 데이터 필요
   - 경로: `data/storage/legal_info/chroma_db`

4. **HWP 템플릿**
   - 계약서 생성을 위해 HWP 템플릿 필요
   - 경로: `data/storage/templates/lease_contract_template.hwp`

---

## 📊 3개 파일 사용 현황 분석
1. agent_registry.py - ✅ 현재 사용 중
사용 위치:
team_supervisor.py (3곳)
planning_agent.py (4곳)
search_executor.py (2곳)
document_executor.py (2곳)
사용 방식:
team_supervisor.py:
# 1. 초기화 시 Agent 시스템 등록
from app.service_agent.foundation.agent_adapter import initialize_agent_system
initialize_agent_system(auto_register=True)  # → AgentRegistry에 팀 등록

# 2. Planning 시 사용 가능한 에이전트 조회
available_agents=AgentRegistry.list_agents(enabled_only=True)

# 3. Agent 의존성 정보 조회
dependencies = AgentAdapter.get_agent_dependencies(agent_name)
planning_agent.py:
# 1. Agent 능력 정보 로드
for agent_name in AgentRegistry.list_agents():
    agent_caps = AgentRegistry.get_capabilities(agent_name)

# 2. 사용 가능한 Agent 확인
available_agents = AgentRegistry.list_agents(enabled_only=True)

# 3. Agent 검증
if not AgentRegistry.get_agent(step.agent_name):
    errors.append(f"Agent '{step.agent_name}' not found in registry")
search_executor.py:
# 사용 가능한 Agent 확인
available[agent_name] = agent_name in AgentRegistry.list_agents(enabled_only=True)
핵심 역할:
팀(search_team, analysis_team, document_team)을 중앙 레지스트리에 등록
Planning 시 실행 가능한 팀 목록 제공
Agent 메타데이터(capabilities) 조회
2. agent_adapter.py - ✅ 현재 사용 중
사용 위치:
team_supervisor.py (2곳)
planning_agent.py (1곳)
search_executor.py (1곳)
document_executor.py (1곳)
사용 방식:
team_supervisor.py:
# 1. 초기화 - Agent 시스템 등록
from app.service_agent.foundation.agent_adapter import initialize_agent_system
initialize_agent_system(auto_register=True)

# 2. Agent 의존성 정보 조회 (팀 매핑)
from app.service_agent.foundation.agent_adapter import AgentAdapter
dependencies = AgentAdapter.get_agent_dependencies(agent_name)
return dependencies.get("team", "search")
search_executor.py:
# SearchAgent 동적 실행 (fallback)
result = await AgentAdapter.execute_agent_dynamic(
    "search_agent",
    search_input,
    self.llm_context
)
핵심 역할:
initialize_agent_system(): AgentRegistry에 3개 팀 자동 등록
get_agent_dependencies(): Agent → Team 매핑 정보 제공
execute_agent_dynamic(): Agent 동적 실행 (현재는 거의 사용 안 함)
3. query_decomposer.py - ⚠️ 부분적으로 사용 중
사용 위치:
planning_agent.py (핵심)
reports/tests/ (테스트 코드 3개)
사용 방식:
planning_agent.py:
# 1. 초기화
from app.service_agent.cognitive_agents.query_decomposer import (
    QueryDecomposer,
    DecomposedQuery,
    ExecutionMode as DecomposerExecutionMode
)

# PlanningAgent 생성자
self.query_decomposer = QueryDecomposer(self.llm_service)

# 2. 복합 질문 분해 (create_comprehensive_plan 메서드)
async def create_comprehensive_plan(self, query, context):
    # 의도 분석
    intent = await self.analyze_intent(query, context)
    
    # ⭐ 복합 질문 분해
    decomposed = await self.query_decomposer.decompose(
        query=query,
        context=context,
        intent_result={
            "intent": intent.intent_type.value,
            "confidence": intent.confidence,
            "keywords": intent.keywords,
            "entities": intent.entities,
            "is_compound": len(intent.suggested_agents) > 1
        }
    )
    
    # 분해된 작업을 기반으로 실행 계획 생성
    if decomposed.is_compound:
        steps = []
        for task in decomposed.sub_tasks:
            step = ExecutionStep(
                agent_name=task.agent_team,
                priority=task.priority,
                dependencies=task.dependencies,
                ...
            )
문제점:
create_comprehensive_plan() 메서드는 정의되어 있지만 실제로 호출되지 않음
현재는 create_execution_plan()만 사용됨
QueryDecomposer는 초기화만 되고 실행되지 않음
결론: Phase 1 Enhancement로 준비했지만 아직 활성화되지 않음
📝 요약
파일	사용 여부	사용 빈도	주요 역할
agent_registry.py	✅ 활발히 사용	11곳	팀 등록, 조회, 메타데이터 관리
agent_adapter.py	✅ 사용 중	5곳	팀 자동 등록, 의존성 조회, 동적 실행
query_decomposer.py	⚠️ 준비됨, 미활성화	1곳 (초기화만)	복합 질문 분해 (Phase 1 Enhancement)
🔍 상세 분석
agent_registry.py - 핵심 인프라
왜 필요한가?
3개 팀(search_team, analysis_team, document_team)을 중앙에서 관리
Planning Agent가 실행 가능한 팀 목록을 조회할 때 사용
팀별 capabilities (입출력 타입, 도구) 정보 제공
삭제 시 영향:
Planning Agent가 팀 목록을 조회할 수 없음
시스템 초기화 실패
삭제 불가
agent_adapter.py - 초기화 및 브릿지
왜 필요한가?
initialize_agent_system(): AgentRegistry에 팀 자동 등록
get_agent_dependencies(): Agent 이름 → Team 매핑 (예: "search_agent" → "search")
execute_agent_dynamic(): 동적 실행 (현재는 SearchAgent fallback에만 사용)
삭제 시 영향:
팀이 AgentRegistry에 등록되지 않음
Agent → Team 매핑 정보 손실
삭제 불가
query_decomposer.py - 미래 준비
왜 만들었는가?
Phase 1 Enhancement: 복합 질문 처리 강화
"강남구 아파트 시세 확인하고 대출 가능 금액 계산해줘" 같은 복합 질문을 개별 작업으로 분해
왜 사용하지 않는가?
create_comprehensive_plan()이 호출되지 않음
현재는 create_execution_plan()만 사용
Planning Agent가 이미 복합 질문을 처리 가능
삭제 가능한가?
코드는 완성되어 있고 테스트도 있음
향후 활성화 가능성이 있음
보존 권장 (미래 확장용)
💡 결론 및 권장사항
agent_registry.py: ✅ 핵심 인프라, 삭제 불가
agent_adapter.py: ✅ 초기화 필수, 삭제 불가
query_decomposer.py: ⚠️ Phase 1 준비 완료, 미활성화 상태
삭제하지 말고 보존
향후 복합 질문 처리 강화 시 활성화 가능
create_comprehensive_plan() 호출 로직만 추가하면 바로 사용 가능
