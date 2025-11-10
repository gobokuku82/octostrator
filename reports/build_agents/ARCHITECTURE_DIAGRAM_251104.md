# Agent 시스템 아키텍처 다이어그램

**작성일**: 2025-11-04
**버전**: 1.0

---

## 1. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                             │
│                         (WebSocket / REST API)                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Supervisor Graph                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │   │
│  │  │  Intent  │→ │ Planning │→ │  Router  │→ │ Executor │         │   │
│  │  │  Under   │  │          │  │          │  │          │         │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘         │   │
│  │                                                  │               │   │
│  │  ┌──────────┐  ┌──────────┐                     │               │   │
│  │  │   HITL   │← │Aggregator│←────────────────────┘               │   │
│  │  │  Handler │  │          │                                     │   │
│  │  └──────────┘  └──────────┘                                     │   │
│  │                                                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │   │
│  │  │   Chat   │  │  Report  │  │  Graph   │                       │   │
│  │  │Generator │  │Generator │  │Generator │                       │   │
│  │  └──────────┘  └──────────┘  └──────────┘                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENT LAYER                                    │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │ Contract Agent │  │   Law Agent    │  │  Report Agent  │            │
│  │ ┌────────────┐ │  │ ┌────────────┐ │  │ ┌────────────┐ │            │
│  │ │   Analyze  │ │  │ │   Search   │ │  │ │ Structure  │ │            │
│  │ │   ↓        │ │  │ │   ↓        │ │  │ │   ↓        │ │            │
│  │ │  Validate  │ │  │ │ Summarize  │ │  │ │   Format   │ │            │
│  │ │   ↓        │ │  │ │   ↓        │ │  │ │   ↓        │ │            │
│  │ │   Report   │ │  │ │  Respond   │ │  │ │   Export   │ │            │
│  │ └────────────┘ │  │ └────────────┘ │  │ └────────────┘ │            │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘            │
│           │                   │                   │                     │
│  ┌────────────────┐           │                   │                     │
│  │   Chat Agent   │           │                   │                     │
│  │ ┌────────────┐ │           │                   │                     │
│  │ │  Respond   │ │           │                   │                     │
│  │ └────────────┘ │           │                   │                     │
│  └────────┬───────┘           │                   │                     │
│           │                   │                   │                     │
└───────────┼───────────────────┼───────────────────┼─────────────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SUB-GRAPH LAYER (공유)                                │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │ Validation  │  │     RAG     │  │   Search    │  │  Formatting │   │
│  │  SubGraph   │  │  SubGraph   │  │  SubGraph   │  │  SubGraph   │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                          │
│  ┌─────────────┐                                                        │
│  │    HITL     │                                                        │
│  │  SubGraph   │                                                        │
│  └─────────────┘                                                        │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TOOL LAYER (공유)                                │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Database │  │  Vector  │  │   LLM    │  │   Text   │               │
│  │   Tool   │  │  Search  │  │   Tool   │  │Processing│               │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │
│                                                                          │
│  ┌──────────┐  ┌──────────┐                                            │
│  │   PDF    │  │Validation│                                            │
│  │   Tool   │  │   Tool   │                                            │
│  └──────────┘  └──────────┘                                            │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│    Vector Database       │    │   PostgreSQL Database    │
│   (Pinecone/Qdrant)      │    │  (State + Checkpointing) │
└──────────────────────────┘    └──────────────────────────┘
```

---

## 2. Registry 시스템 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Registry System                               │
│                       (Singleton Pattern)                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Agent Registry                              │ │
│  │                                                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │  Contract    │  │     Law      │  │    Report    │        │ │
│  │  │    Agent     │  │    Agent     │  │    Agent     │        │ │
│  │  │   Class      │  │    Class     │  │    Class     │        │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │ │
│  │          ▲                 ▲                 ▲                 │ │
│  │          │                 │                 │                 │ │
│  │          └─────────────────┴─────────────────┘                 │ │
│  │                            │                                   │ │
│  │                   [Lazy Instantiation]                         │ │
│  │                            │                                   │ │
│  │          ┌─────────────────┴─────────────────┐                 │ │
│  │          ▼                 ▼                 ▼                 │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │  Contract    │  │     Law      │  │    Report    │        │ │
│  │  │   Agent      │  │    Agent     │  │    Agent     │        │ │
│  │  │  Instance    │  │   Instance   │  │   Instance   │        │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  SubGraph Registry                             │ │
│  │                                                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │  Validation  │  │     RAG      │  │    Search    │        │ │
│  │  │   Builder    │  │   Builder    │  │   Builder    │        │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │ │
│  │          │                 │                 │                 │ │
│  │          └─────────────────┴─────────────────┘                 │ │
│  │                            │                                   │ │
│  │                      [Build & Cache]                           │ │
│  │                            │                                   │ │
│  │          ┌─────────────────┴─────────────────┐                 │ │
│  │          ▼                 ▼                 ▼                 │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │  Validation  │  │     RAG      │  │    Search    │        │ │
│  │  │   SubGraph   │  │   SubGraph   │  │   SubGraph   │        │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Tool Registry                              │ │
│  │                                                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │ │
│  │  │   Database   │  │    Vector    │  │     LLM      │        │ │
│  │  │     Tool     │  │    Search    │  │     Tool     │        │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │ │
│  │         +                +                  +                  │ │
│  │     Metadata         Metadata           Metadata               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent 실행 플로우

```
                    [사용자 요청]
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Supervisor: Intent Understanding           │
│                   "계약서를 분석해주세요"                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Supervisor: Planning                       │
│            Intent Type: "contract_analysis"                  │
│            Required Tools: [pdf_tool, llm_tool]             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Supervisor: Router                         │
│         Agent Mapping: "contract_analysis"                   │
│                   → "contract_agent"                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Agent Registry: Get Agent                    │
│        agent_registry.get("contract_agent")                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Contract Agent: Execute                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Node: Analyze Contract                             │    │
│  │    └─> Tool: pdf_tool (계약서 파싱)                  │    │
│  │    └─> Tool: llm_tool (조항 추출)                    │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  SubGraph: RAG Graph                                │    │
│  │    └─> Tool: vector_search_tool (유사 계약서 검색)   │    │
│  │    └─> Tool: llm_tool (컨텍스트 기반 분석)           │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Node: Validate Contract                            │    │
│  │    └─> Tool: validation_tool                        │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        ▼                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  SubGraph: Validation Graph                         │    │
│  │    └─> Schema Validation                            │    │
│  │    └─> Business Rules Validation                    │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        ▼                                     │
│                  [Agent Result]                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Supervisor: Aggregator                       │
│           Agent Results + Context → Final Response          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             Supervisor: Response Generator                   │
│                  Output Format: Chat/Report                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  [사용자에게 응답]
```

---

## 4. 디렉토리 구조 (상세)

```
backend/app/octostrator/
│
├── supervisor/                          # Supervisor 레이어
│   ├── __init__.py
│   ├── graph.py                        # Supervisor 그래프
│   ├── prompts.py                      # Supervisor 프롬프트
│   └── nodes/                          # Supervisor 노드
│       ├── __init__.py
│       ├── intent_understanding.py     # Intent 파악
│       ├── planning.py                 # 계획 수립
│       ├── router.py                   # Agent 라우팅 ★
│       ├── executor.py                 # Agent 실행 ★
│       ├── aggregator.py               # 결과 집계
│       ├── hitl_handler.py             # HITL 처리
│       └── generators/                 # 응답 생성기
│           ├── __init__.py
│           ├── chat_generator.py
│           ├── report_generator.py
│           └── graph_generator.py
│
├── agents/                              # Agent 레이어 ★
│   ├── __init__.py                     # Agent 자동 등록 ★
│   ├── registry.py                     # Agent Registry ★
│   │
│   ├── base/                           # Base Agent ★
│   │   ├── __init__.py
│   │   ├── agent_base.py               # BaseAgent 추상 클래스
│   │   └── agent_config.py             # AgentConfig 스키마
│   │
│   ├── contract_agent/                 # 계약서 분석 Agent ★
│   │   ├── __init__.py
│   │   ├── agent.py                    # ContractAgent 클래스
│   │   ├── state.py                    # ContractAgentState
│   │   ├── prompts.py                  # Agent 프롬프트
│   │   └── nodes/                      # Agent 노드
│   │       ├── __init__.py
│   │       ├── analyze.py
│   │       └── validate.py
│   │
│   ├── law_agent/                      # 법률 검색 Agent ★
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── state.py
│   │   ├── prompts.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── search.py
│   │       └── summarize.py
│   │
│   ├── report_agent/                   # 보고서 생성 Agent ★
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── state.py
│   │   ├── prompts.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── structure.py
│   │       └── format.py
│   │
│   └── chat_agent/                     # 대화형 Agent ★
│       ├── __init__.py
│       ├── agent.py
│       ├── state.py
│       ├── prompts.py
│       └── nodes/
│           ├── __init__.py
│           └── respond.py
│
├── sub_graphs/                          # 공유 SubGraph ★
│   ├── __init__.py
│   ├── registry.py                     # SubGraph Registry ★
│   ├── validation_graph.py             # 검증 서브그래프 ★
│   ├── rag_graph.py                    # RAG 서브그래프 ★
│   ├── search_graph.py                 # 검색 서브그래프 ★
│   ├── formatting_graph.py             # 포맷팅 서브그래프 ★
│   └── hitl_graph.py                   # HITL 서브그래프 ★
│
├── tools/                               # 공유 Tool ★
│   ├── __init__.py
│   ├── registry.py                     # Tool Registry ★
│   ├── database_tool.py                # DB 도구 ★
│   ├── vector_search_tool.py           # 벡터 검색 도구 ★
│   ├── llm_tool.py                     # LLM 도구 ★
│   ├── text_processing_tool.py         # 텍스트 처리 도구 ★
│   ├── pdf_tool.py                     # PDF 도구 ★
│   └── validation_tool.py              # 검증 도구 ★
│
├── states/                              # State 정의
│   ├── __init__.py
│   ├── supervisor_state.py             # Supervisor State
│   └── common_state.py                 # 공통 State
│
├── contexts/                            # Context 관리
│   ├── __init__.py
│   └── app_context.py
│
├── session/                             # 세션 관리
│   ├── __init__.py
│   └── session_manager.py
│
├── checkpointer/                        # Checkpointing
│   ├── __init__.py
│   └── postgres_checkpointer.py
│
└── __init__.py

★ = 새로 구현 또는 수정이 필요한 파일
```

---

## 5. 데이터 플로우

### 5.1 State 전달 흐름

```
┌──────────────────────────────────────────────────┐
│           Supervisor State                       │
│  {                                               │
│    "query": "계약서 분석 요청",                   │
│    "intent": {                                   │
│      "type": "contract_analysis"                 │
│    },                                            │
│    "selected_agent": "contract_agent",           │
│    "agent_results": [],                          │
│    "errors": []                                  │
│  }                                               │
└───────────────────┬──────────────────────────────┘
                    │
                    │ Supervisor → Agent
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│          Contract Agent State                    │
│  {                                               │
│    "query": "계약서 분석 요청",                   │
│    "contract_text": "",                          │
│    "clauses": [],                                │
│    "risk_analysis": {},                          │
│    "validation_result": {},                      │
│    "errors": []                                  │
│  }                                               │
└───────────────────┬──────────────────────────────┘
                    │
                    │ Agent → SubGraph
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│            RAG SubGraph State                    │
│  {                                               │
│    "query": "계약서 유사 사례 검색",              │
│    "documents": [],                              │
│    "context": "",                                │
│    "answer": ""                                  │
│  }                                               │
└──────────────────────────────────────────────────┘
```

### 5.2 Tool 호출 흐름

```
Agent Node → Tool Registry → Tool Function → External Resource
     │            │               │                  │
     │            └─get("tool")───┘                  │
     │                            └─execute()────────┘
     │                                    │
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │ Vector Database  │
     │                           │   PostgreSQL     │
     │                           │   LLM API        │
     └───result────────────────  └──────────────────┘
```

---

## 6. 확장 포인트

### 6.1 새 Agent 추가

```
1. agents/<new_agent>/ 폴더 생성
2. agent.py, state.py, nodes/ 구현
3. agents/__init__.py에 등록 추가
4. Supervisor router.py에 매핑 추가
```

### 6.2 새 SubGraph 추가

```
1. sub_graphs/<new_graph>.py 생성
2. build_<new_graph>_graph() 함수 구현
3. Registry에 등록
4. Agent에서 config.subgraphs에 추가
```

### 6.3 새 Tool 추가

```
1. tools/<new_tool>_tool.py 생성
2. Tool 함수 구현
3. Registry에 등록
4. Agent에서 config.tools에 추가
```

---

## 7. 주요 설계 원칙

### 7.1 SOLID 원칙
- **Single Responsibility**: 각 Agent는 단일 책임
- **Open/Closed**: Registry를 통한 확장 개방
- **Liskov Substitution**: BaseAgent 상속
- **Interface Segregation**: 필요한 Tool/SubGraph만 사용
- **Dependency Inversion**: Registry에 의존

### 7.2 Design Patterns
- **Singleton**: Registry 시스템
- **Factory**: Agent/SubGraph 생성
- **Strategy**: Agent 선택 및 실행
- **Template Method**: BaseAgent.build_graph()

---

## 8. 성능 고려사항

### 8.1 최적화 전략
- Agent 인스턴스 재사용 (Singleton Registry)
- SubGraph 캐싱
- 비동기 처리 (asyncio)
- Lazy Initialization

### 8.2 확장성
- Horizontal Scaling: Agent별 독립 배포 가능
- Vertical Scaling: Tool 성능 개선
- Caching: Redis 캐시 레이어 추가 가능

---

**문서 끝**
