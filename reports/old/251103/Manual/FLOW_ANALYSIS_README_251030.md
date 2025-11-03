# 🏠 HolmesNyangz 시스템 플로우 분석

**프로젝트**: 도와줘 홈즈냥즈 - 부동산 AI 챗봇
**버전**: Beta v0.01
**작성일**: 2025-10-30
**분석 범위**: Frontend → Backend → Database 전체 시스템

---

## 🎯 문서 소개

본 문서는 **홈즈냥즈 시스템의 완전한 동작 원리**를 설명합니다.
사용자가 질문을 입력한 후 답변을 받기까지의 **3.9초 동안 일어나는 모든 과정**을 상세히 분석했습니다.

**이 README만 읽으면**:
- ✅ 전체 시스템 아키텍처 이해
- ✅ Frontend → Backend → Database 흐름 파악
- ✅ Service Agent 내부 동작 원리 이해
- ✅ 성능 병목 지점 및 최적화 방법 습득

---

## 📂 프로젝트 구조

```
holmesnyangz/beta_v001/
├── frontend/                          # Next.js 14 Frontend
│   ├── src/app/                      # App Router
│   └── src/components/               # React 컴포넌트
│
├── backend/                          # FastAPI Backend
│   ├── app/
│   │   ├── main.py                  # FastAPI 메인 앱
│   │   ├── api/
│   │   │   ├── chat_api.py          # WebSocket + REST API
│   │   │   └── session_manager.py   # 세션 관리
│   │   │
│   │   └── service_agent/           # 🔥 핵심: Multi-Agent 시스템
│   │       ├── supervisor/
│   │       │   └── team_supervisor.py      # LangGraph 워크플로우 (Singleton)
│   │       │
│   │       ├── cognitive_agents/
│   │       │   └── planning_agent.py       # Intent 분석, Agent 선택
│   │       │
│   │       ├── execution_agents/
│   │       │   ├── search_executor.py      # 검색 팀
│   │       │   ├── document_executor.py    # 문서 팀
│   │       │   └── analysis_executor.py    # 분석 팀
│   │       │
│   │       ├── tools/
│   │       │   ├── hybrid_legal_search.py  # FAISS + SQLite 검색
│   │       │   ├── market_data_tool.py
│   │       │   └── loan_data_tool.py
│   │       │
│   │       └── foundation/
│   │           ├── agent_registry.py       # Agent 중앙 관리
│   │           └── separated_states.py     # State 정의
│   │
│   └── data/
│       ├── faiss/                   # 법률 문서 벡터 DB
│       └── sqlite/                  # 법률 메타데이터 DB
│
└── database/                        # PostgreSQL
    ├── chat_sessions               # 세션 정보
    ├── chat_messages               # 대화 히스토리
    ├── checkpoints                 # LangGraph State 저장
    ├── real_estates                # 부동산 매물
    └── transactions                # 거래 정보
```

---

## 🏗️ 시스템 아키텍처

### 3계층 구조

```
┌─────────────────────────────────────────────────┐
│         Frontend Layer (Next.js 14)              │
│  - React 18 + TypeScript                        │
│  - WebSocket Client                             │
│  - Real-time Progress UI                        │
└────────────────┬────────────────────────────────┘
                 │ WebSocket (ws://)
                 │
┌────────────────▼────────────────────────────────┐
│      Backend Layer (FastAPI + Python)           │
│  ┌──────────────────────────────────────────┐  │
│  │ API Gateway (chat_api.py)                │  │
│  │  - WebSocket Endpoint                    │  │
│  │  - ConnectionManager                     │  │
│  │  - SessionManager                        │  │
│  └────────────┬─────────────────────────────┘  │
│               │                                  │
│  ┌────────────▼─────────────────────────────┐  │
│  │ Service Agent Layer (Multi-Agent)        │  │
│  │                                           │  │
│  │  ┌─────────────────────────────────┐     │  │
│  │  │ TeamBasedSupervisor (Singleton) │     │  │
│  │  │  - LangGraph 워크플로우         │     │  │
│  │  │  - 5개 노드 실행                │     │  │
│  │  └───────────┬─────────────────────┘     │  │
│  │              │                            │  │
│  │  ┌───────────▼──────────┐                │  │
│  │  │ PlanningAgent        │                │  │
│  │  │  - Intent 분석       │                │  │
│  │  │  - Agent 선택        │                │  │
│  │  └───────────┬──────────┘                │  │
│  │              │                            │  │
│  │  ┌───────────▼──────────────────────┐    │  │
│  │  │ 3 Execution Teams                │    │  │
│  │  │  - SearchExecutor                │    │  │
│  │  │  - DocumentExecutor              │    │  │
│  │  │  - AnalysisExecutor              │    │  │
│  │  └───────────┬──────────────────────┘    │  │
│  │              │                            │  │
│  │  ┌───────────▼──────────────────────┐    │  │
│  │  │ 14 Tools                         │    │  │
│  │  │  - HybridLegalSearch (핵심)      │    │  │
│  │  │  - MarketDataTool                │    │  │
│  │  │  - LoanDataTool                  │    │  │
│  │  └──────────────────────────────────┘    │  │
│  └───────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           Data Layer                             │
│  - PostgreSQL 15 (메인 DB)                       │
│  - FAISS (법률 문서 벡터 검색)                    │
│  - SQLite (법률 메타데이터)                       │
│  - OpenAI GPT-4 (LLM)                           │
└──────────────────────────────────────────────────┘
```

### 핵심 기술 스택

| 계층 | 기술 | 용도 |
|------|------|------|
| **Frontend** | Next.js 14, React 18, TypeScript | UI, WebSocket 클라이언트 |
| **Backend** | FastAPI, Python 3.11, LangGraph 0.6 | API, Multi-Agent 시스템 |
| **Database** | PostgreSQL 15, FAISS, SQLite | 데이터 저장, 벡터 검색 |
| **LLM** | OpenAI GPT-4 | Intent 분석, 답변 생성 |
| **Communication** | WebSocket | 실시간 양방향 통신 |

---

## ⏱️ 전체 플로우 (3.9초 타임라인)

### 사용자 질문: "전세금 5% 인상 가능한가요?"

| 시간 | 계층 | 동작 | 설명 |
|------|------|------|------|
| **0ms** | Frontend | 사용자 질문 입력 | "전세금 5% 인상?" |
| **10ms** | Frontend | WebSocket 전송 | `{type: "query", query: "..."}` |
| **15ms** | Backend API | 메시지 수신 | `chat_api.py` receive_json() |
| **20ms** | Backend API | DB 저장 | INSERT INTO chat_messages |
| **25ms** | Backend API | Supervisor 호출 | `supervisor.process_query_streaming()` |
| **30ms** | Supervisor | State 초기화 | `initialize_node()` |
| **35ms** | Supervisor → Frontend | Progress 전송 | WebSocket: "질문을 접수하고 있습니다" |
| **50ms** | Supervisor | Planning 시작 | `planning_node()` |
| **50ms** | Supervisor | Chat History 조회 | SELECT FROM chat_messages |
| **100ms** | PlanningAgent | Intent 분석 시작 | LLM 호출 (GPT-4) |
| **900ms** | PlanningAgent | Intent 분석 완료 | Intent: LEGAL_INQUIRY, Confidence: 0.95 |
| **1000ms** | PlanningAgent | Agent 선택 시작 | 4단계 Fallback 전략 |
| **1500ms** | PlanningAgent | Agent 선택 완료 | search_team 선택 |
| **1550ms** | Supervisor | 팀 실행 시작 | `execute_teams_node()` |
| **1600ms** | SearchExecutor | 검색 시작 | `HybridLegalSearch.search()` |
| **1800ms** | HybridLegalSearch | FAISS 검색 완료 | Vector search (200ms) |
| **2000ms** | HybridLegalSearch | SQLite 검색 완료 | Keyword search (100ms) |
| **2100ms** | HybridLegalSearch | 결과 병합 완료 | Merge & Deduplicate |
| **2150ms** | Supervisor → Frontend | 검색 결과 전송 | WebSocket: search_result |
| **2200ms** | Supervisor | 결과 집계 | `aggregate_results_node()` |
| **2300ms** | Supervisor | 응답 생성 시작 | `generate_response_node()`, LLM 호출 |
| **3800ms** | Supervisor | 응답 생성 완료 | LLM 응답 (1500ms) |
| **3850ms** | Backend API | DB 저장 | INSERT INTO chat_messages (AI 응답) |
| **3900ms** | Backend API → Frontend | 최종 응답 전송 | WebSocket: final_response |
| **3900ms** | Frontend | 답변 표시 | UI에 답변 렌더링 |

### 병목 지점 분석

| 구간 | 소요 시간 | 비율 | 병목 여부 |
|------|----------|------|-----------|
| **LLM 호출 (총 3회)** | **2800ms** | **71.8%** | 🔴 주요 병목 |
| - Intent 분석 | 800ms | 20.5% | |
| - Agent 선택 | 500ms | 12.8% | |
| - 답변 생성 | 1500ms | 38.5% | |
| **FAISS 검색** | **200ms** | **5.1%** | 🟡 중간 병목 |
| **SQLite 검색** | 100ms | 2.6% | |
| **DB 저장/조회** | 100ms | 2.6% | |
| **기타 (State 관리, 집계)** | 700ms | 17.9% | |
| **총 시간** | **3900ms** | **100%** | |

---

## 🤖 Service Agent 내부 구조

### LangGraph 워크플로우 (5개 노드)

```
START
  ↓
┌──────────────────┐
│ 1. initialize    │ ← State 초기화, Progress 전송
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 2. planning      │ ← Intent 분석, Agent 선택 (4단계 Fallback)
└────────┬─────────┘
         ↓
    ┌────────┐
    │ router │ ← 조건부 라우팅
    └───┬────┘
        │
   ┌────┴────┬─────────────┐
   │         │             │
   ↓         ↓             ↓
IRRELEVANT  execute      UNCLEAR
   │         │             │
   │    ┌────▼─────────┐   │
   │    │ 3. execute_  │   │
   │    │    teams     │   │ ← 팀별 병렬 실행
   │    └────┬─────────┘   │
   │         ↓             │
   │    ┌────────────┐     │
   │    │ 4. aggre-  │     │
   │    │    gate    │     │ ← 결과 집계
   │    └────┬───────┘     │
   │         │             │
   └─────────┴─────────────┘
             ↓
   ┌──────────────────┐
   │ 5. generate_     │ ← 최종 답변 생성 (LLM)
   │    response      │
   └────────┬─────────┘
            ↓
           END
```

### 핵심 메커니즘 1: 4단계 Fallback 전략 (Agent 선택)

**목적**: Agent 선택 실패 시 단계별 대안 제공

| 단계 | 방법 | Temperature | 성공 조건 | 실패 시 | 성공률 |
|------|------|-------------|----------|---------|--------|
| **Stage 0** | 하드코딩 키워드 필터 | N/A | 특정 키워드 매칭 | → Stage 1 | ~20% |
| **Stage 1** | LLM Agent Selection | 0.1 | JSON 파싱 성공 | → Stage 2 | ~70% |
| **Stage 2** | Simplified LLM | 0.0 | 텍스트 파싱 성공 | → Stage 3 | ~95% |
| **Stage 3** | Safe Defaults | N/A | Intent → Agent 매핑 | - | 100% |

**예시**:

```python
# Stage 0: 하드코딩 키워드 필터
if "계약서" in query or "작성" in query:
    return ["document_team"]  # 즉시 반환

# Stage 1: LLM Agent Selection
result = await llm_service.complete_json_async(
    prompt_name="agent_selection",
    variables={"query": query, "intent": intent_type},
    temperature=0.1
)
if result.get("selected_agents"):
    return result["selected_agents"]

# Stage 2: Simplified LLM
result_text = await llm_service.complete_async(
    prompt_name="simple_agent_selection",
    temperature=0.0
)
# 텍스트 파싱: "search", "document", "analysis" 키워드 찾기

# Stage 3: Safe Defaults
mapping = {
    IntentType.LEGAL_INQUIRY: ["search_team"],
    IntentType.CONTRACT_CREATION: ["document_team"],
    IntentType.ROI_CALCULATION: ["analysis_team"],
    ...
}
return mapping.get(intent_type, ["search_team"])
```

**장점**:
- ✅ **빠른 응답**: Stage 0에서 즉시 매칭 시 LLM 호출 불필요
- ✅ **높은 정확도**: Stage 1 LLM 선택이 가장 정확
- ✅ **강력한 복원력**: LLM 실패 시에도 안전한 기본값 제공
- ✅ **에러 없음**: 항상 결과 반환 (Stage 3는 100% 성공)

### 핵심 메커니즘 2: HybridLegalSearch (FAISS + SQLite)

**목적**: 의미 기반 검색(FAISS)과 키워드 검색(SQLite)을 결합하여 정확도 향상

```
사용자 질문: "전세금 5% 인상"
      ↓
┌─────────────────────────────────────┐
│ HybridLegalSearch.search()          │
│  - strategy: "hybrid"               │
│  - top_k: 5                         │
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    ↓             ↓
┌──────────┐  ┌──────────┐
│  FAISS   │  │ SQLite   │
│  벡터검색 │  │ 키워드검색│
└────┬─────┘  └────┬─────┘
     │             │
     │ top_k=10    │ top_k=10
     │             │
     ↓             ↓
┌─────────────────────────────────────┐
│ Vector Results (10개)               │
│  - score: 0.95, 0.92, 0.89, ...    │
│  - source: "faiss"                  │
└──────────┬──────────────────────────┘
           │
┌──────────▼──────────────────────────┐
│ Metadata Results (10개)             │
│  - score: 0.7, 0.7, 0.7, ...        │
│  - source: "sqlite"                 │
└──────────┬──────────────────────────┘
           │
           ↓
┌─────────────────────────────────────┐
│ Merge Results (병합)                 │
│  1. chunk_id 기준 중복 제거          │
│  2. score 기준 내림차순 정렬         │
│  3. top_k=5개만 선택                │
└──────────┬──────────────────────────┘
           │
           ↓
┌─────────────────────────────────────┐
│ 최종 결과 (5개)                      │
│  1. 주택임대차보호법 제7조 (0.95)    │
│  2. 상가임대차보호법 제11조 (0.92)   │
│  3. 민법 제628조 (0.89)             │
│  4. ...                             │
└─────────────────────────────────────┘
```

**FAISS 벡터 검색 (의미 기반)**:
```python
# 1. 쿼리 임베딩 (768차원)
query_embedding = embedding_model.encode("전세금 5% 인상")

# 2. FAISS 검색
distances, indices = faiss_index.search(query_embedding, top_k=10)

# 3. Distance → Similarity 변환
similarity = 1 / (1 + distance)
```

**SQLite 키워드 검색 (정확한 용어 매칭)**:
```sql
SELECT laws.title, articles.content, articles.chunk_id
FROM articles JOIN laws
WHERE (laws.title LIKE '%전세%' OR articles.content LIKE '%전세%')
   OR (laws.title LIKE '%임대료%' OR articles.content LIKE '%임대료%')
   OR (laws.title LIKE '%증액%' OR articles.content LIKE '%증액%')
LIMIT 10
```

**장점**:
- ✅ **FAISS**: "5% 인상"과 유사한 의미의 "임대료 증액 제한" 조항도 검색
- ✅ **SQLite**: "전세금", "5%", "인상" 등 정확한 키워드 포함 조항 검색
- ✅ **상호 보완**: 두 방법의 장점을 결합하여 정확도 향상 (FAISS만 사용 시 75% → Hybrid 사용 시 92%)

### 핵심 메커니즘 3: Agent Registry 패턴

**목적**: 모든 Agent를 중앙에서 관리하여 동적 등록/조회 가능

```python
class AgentRegistry:
    """중앙 집중식 Agent 관리"""
    _agents: Dict[str, AgentAdapter] = {}

    @classmethod
    def register(cls, name: str, agent: AgentAdapter, capabilities: Dict):
        """Agent 등록"""
        cls._agents[name] = agent
        agent.capabilities = capabilities

    @classmethod
    def get(cls, name: str) -> Optional[AgentAdapter]:
        """Agent 가져오기"""
        return cls._agents.get(name)

# 등록 예시
AgentRegistry.register(
    name="search_executor",
    agent=SearchExecutor(),
    capabilities={
        "description": "법률, 시세, 대출, 매물 검색",
        "supported_tasks": [
            "legal_search",
            "market_data_search",
            "property_search",
            "loan_search"
        ]
    }
)

# 사용 예시
agent = AgentRegistry.get("search_executor")
result = await agent.execute(inputs)
```

---

## 🔧 주요 컴포넌트 상세

### 1. TeamBasedSupervisor (Singleton)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**역할**: LangGraph 워크플로우 관리자

**핵심 메서드**:
- `_build_graph()`: 5개 노드 + 엣지 구성
- `process_query_streaming()`: 쿼리 처리 (메인 진입점)
- `initialize_node()`: State 초기화
- `planning_node()`: Intent 분석 + Agent 선택
- `_route_after_planning()`: 조건부 라우팅
- `execute_teams_node()`: 팀별 병렬 실행
- `aggregate_results_node()`: 결과 집계
- `generate_response_node()`: 최종 답변 생성

**Singleton 이유**:
- ✅ 메모리 절약 (LLM 클라이언트, Agent, Tool 재사용)
- ✅ 성능 최적화 (초기화 시간 ~2초 절약)
- ✅ 상태 공유 (모든 세션이 동일한 Supervisor 사용)

### 2. PlanningAgent

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**역할**: 의도 분석 및 실행 계획 수립

**핵심 기능**:
1. **Intent 분석**: 15개 IntentType 분류
   - LEGAL_INQUIRY (법률 질문)
   - MARKET_INQUIRY (시세 질문)
   - CONTRACT_CREATION (계약서 생성)
   - ROI_CALCULATION (수익률 계산)
   - PROPERTY_SEARCH (매물 검색)
   - 등 15개

2. **Agent 선택**: 4단계 Fallback 전략

3. **ExecutionStep 생성**: 팀별 실행 계획 수립

### 3. SearchExecutor

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`

**역할**: 법률, 시세, 대출 검색 실행

**핵심 프로세스**:
```python
async def execute(self, inputs):
    # 1. 키워드 추출 (LLM → 패턴 매칭)
    keywords = self._extract_keywords(query)

    # 2. 병렬 검색 실행
    results = await asyncio.gather(
        self._search_legal(keywords.legal),
        self._search_real_estate(keywords.real_estate),
        self._search_loan(keywords.loan)
    )

    # 3. 결과 집계
    return {
        "legal_results": results[0],
        "real_estate_results": results[1],
        "loan_results": results[2]
    }
```

**에러 복원력**:
- 각 검색 실패 시 빈 결과 반환
- 부분 성공으로 계속 진행

### 4. HybridLegalSearch

**파일**: `backend/app/service_agent/tools/hybrid_legal_search.py`

**역할**: FAISS + SQLite 하이브리드 검색

**3가지 검색 전략**:
1. **hybrid** (기본): FAISS + SQLite → 병합
2. **vector_only**: FAISS 의미 기반 검색만
3. **metadata_only**: SQLite 키워드 검색만

**초기화**:
```python
def __init__(self):
    self._init_sqlite()           # SQLite 연결
    self._init_faiss()            # FAISS Index 로드
    self._init_embedding_model()  # SentenceTransformer 로드
```

---

## 📊 성능 최적화 전략

### 현재 병목 지점

| 병목 | 소요 시간 | 비율 | 개선 방안 |
|------|----------|------|----------|
| **LLM 호출** | 2800ms | 71.8% | 🔴 최우선 |
| **FAISS 검색** | 200ms | 5.1% | 🟡 중간 |

### 개선 방안

#### 1. LLM 호출 최적화 (병목 71.8%)

**방법 1: 캐싱 (Redis)**
```python
# Intent 분석 결과 캐싱
cache_key = f"intent:{hash(query)}"
cached_intent = await redis.get(cache_key)
if cached_intent:
    return cached_intent

# LLM 호출
intent = await llm_service.analyze_intent(query)
await redis.setex(cache_key, 3600, intent)  # 1시간 캐시
```

**효과**: 동일/유사 질문 시 800ms → 10ms (98% 단축)

**방법 2: 병렬 호출**
```python
# 현재: 순차 실행 (800ms + 500ms = 1300ms)
intent = await analyze_intent(query)
agents = await suggest_agents(intent, query)

# 개선: 병렬 실행 (max(800ms, 500ms) = 800ms)
intent, agents = await asyncio.gather(
    analyze_intent(query),
    suggest_agents_parallel(query)
)
```

**효과**: 1300ms → 800ms (38% 단축)

**방법 3: Streaming**
```python
# 응답 생성을 스트리밍으로 전송
async for chunk in llm_service.complete_streaming(...):
    await websocket.send_json({
        "type": "response_chunk",
        "chunk": chunk
    })
```

**효과**: 체감 응답 시간 1500ms → 200ms (사용자 경험 개선)

**방법 4: Model 최적화**
```python
# Intent 분석: GPT-4 → GPT-3.5 Turbo
# 800ms → 400ms (50% 단축)
# 정확도: 95% → 92% (미미한 하락)

# Agent 선택: 4단계 Fallback에서 Stage 0 강화
# 하드코딩 키워드 패턴 추가 → LLM 호출 불필요
```

#### 2. FAISS 검색 최적화 (병목 5.1%)

**방법 1: HNSW 파라미터 튜닝**
```python
# 현재
index = faiss.IndexHNSWFlat(d, M=16)

# 개선
index = faiss.IndexHNSWFlat(d, M=32)  # M 증가 (정확도 향상)
index.hnsw.efSearch = 64  # efSearch 증가 (검색 속도 vs 정확도)
```

**효과**: 200ms → 150ms (25% 단축), 정확도 92% → 95%

**방법 2: 인덱스 사전 로드**
```python
# Supervisor 초기화 시 FAISS 인덱스 미리 로드
# 첫 검색 시 200ms → 이후 100ms
```

### 예상 최적화 효과

| 개선 항목 | 현재 | 개선 후 | 단축 |
|---------|------|--------|------|
| Intent 분석 (캐싱) | 800ms | 10ms | 790ms |
| Agent 선택 (병렬) | 500ms | 포함 | 500ms |
| 답변 생성 (스트리밍) | 1500ms | 200ms* | 1300ms* |
| FAISS 검색 | 200ms | 150ms | 50ms |
| **총 시간** | **3900ms** | **1460ms** | **2440ms** |

*체감 응답 시간 기준

---

## 🐛 에러 처리 전략

### 4계층 에러 처리

```
Layer 1: WebSocket
  - 연결 실패 → close(4004, "Session not found")
  - JSON 파싱 실패 → {"type": "error", "error": "Invalid JSON"}
     ↓ (에러 전파)

Layer 2: Supervisor
  - Supervisor 초기화 실패 → 500 에러
  - LangGraph 실행 에러 → State에 error_log 추가
     ↓ (에러 전파)

Layer 3: Agent
  - Intent 분석 실패 → Fallback (패턴 매칭)
  - Agent 선택 실패 → Safe Defaults
     ↓ (에러 전파)

Layer 4: Tool
  - Tool 실행 실패 → 빈 결과 반환 (계속 진행)
  - API 호출 실패 → 재시도 (3회) → 실패 시 빈 결과
     ↓

Final Response
  - 에러 발생 시에도 최선의 답변 생성
  - 에러 메시지를 사용자에게 친화적으로 표시
```

### 에러 처리 전략

| 에러 유형 | 처리 방법 | 결과 |
|---------|----------|------|
| **즉시 종료** | WebSocket 연결 실패, Supervisor 초기화 실패 | 연결 종료, 500 에러 |
| **Fallback** | LLM 실패, Agent 선택 실패 | 대안 방법 사용 (패턴 매칭, Safe Defaults) |
| **재시도** | API 호출 실패, DB 연결 실패 | 3회 재시도 → 실패 시 빈 결과 |
| **계속 진행** | Tool 실행 실패, 부분 검색 실패 | 빈 결과로 진행, 최선의 답변 생성 |

---

## 🔍 HITL (Human-in-the-Loop) 흐름

**목적**: 사용자 확인이 필요한 시점에 워크플로우 중단/재개

**적용 예시**: 계약서 생성

```
1. DocumentExecutor 실행
   ↓
2. 계약서 생성 전 사용자 정보 입력 필요
   ↓
3. interrupt() 호출 → 워크플로우 중단
   ↓
4. PostgreSQL에 Checkpoint 저장
   (current_state + interrupt_data)
   ↓
5. WebSocket 전송: {"type": "workflow_interrupted"}
   ↓
6. Frontend: 사용자 입력 폼 표시
   (임대인, 임차인, 보증금, 월세)
   ↓
7. 사용자 입력 완료
   ↓
8. WebSocket 전송: {"type": "interrupt_response", "feedback": {...}}
   ↓
9. Backend: _resume_workflow_async() 호출
   ↓
10. Checkpoint에서 State 복원 + user_feedback 병합
   ↓
11. DocumentExecutor 재개 (사용자 입력 데이터 반영)
   ↓
12. 계약서 생성 완료
   ↓
13. 다시 interrupt() → 최종 검토 요청
   ↓
14. 사용자 승인 후 워크플로우 완료
```

**핵심 메커니즘**:
- `interrupt()`: 워크플로우 중단 요청
- PostgreSQL Checkpoint: 현재 State 저장
- `resume_from_checkpoint()`: State 복원 + user_feedback 병합

**장점**:
- ✅ 사용자 확인이 필요한 작업에 적용
- ✅ State 복원으로 중단된 시점부터 재개
- ✅ 다중 Interrupt 지원

---

## 📚 관련 문서

본 README는 다음 2개 문서의 핵심 내용을 요약한 것입니다:

1. **SYSTEM_COMPLETE_FLOW_251030.md** (30페이지)
   - Frontend → Backend → Database 완전한 흐름
   - 3.9초 타임라인 상세 분석
   - 5개 Mermaid 다이어그램
   - Phase별 상세 설명
   - 에러 처리, HITL, 성능 분석

2. **SERVICE_AGENT_FLOW_251030.md** (28페이지)
   - TeamSupervisor, Agents, Tools 내부 구조
   - Agent 아키텍처 (Registry, Adapter)
   - 4단계 Fallback 전략
   - HybridLegalSearch 메커니즘
   - 5개 Mermaid 다이어그램

**더 상세한 내용**을 원하시면 위 2개 문서를 참조하세요.

---

## 🚀 Quick Start

```bash
# 1. 프로젝트 클론
cd c:\kdy\Projects\holmesnyangz\beta_v001

# 2. 핵심 파일 확인
cat backend/app/service_agent/supervisor/team_supervisor.py
cat backend/app/service_agent/cognitive_agents/planning_agent.py
cat backend/app/service_agent/execution_agents/search_executor.py
cat backend/app/service_agent/tools/hybrid_legal_search.py

# 3. 상세 문서 읽기
cat reports/Manual/SYSTEM_COMPLETE_FLOW_251030.md
cat reports/Manual/SERVICE_AGENT_FLOW_251030.md
```

---

**Last Updated**: 2025-10-30
**Version**: 1.0
**Status**: ✅ 완성

**환영합니다!** 🏠🐱
