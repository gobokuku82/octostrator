# 프로젝트 구조 - Octostrator

**Octostrator**: Octopus + Orchestrator
문어발처럼 여러 에이전트를 자동으로 오케스트레이션하는 시스템

---

## 최종 폴더 구조

```
backend/app/
├── main.py                        # FastAPI 엔트리포인트
│
├── config/                        # 시스템 설정 (환경 변수)
│   ├── __init__.py
│   └── system.py                 # SystemConfig
│
├── octostrator/                   # 🐙 Octostrator (메인 시스템)
│   ├── __init__.py
│   │
│   ├── contexts/                 # Runtime Context (불변)
│   │   └── __init__.py           # Phase 1.5 이후 추가 예정
│   │
│   ├── states/                   # State (변경 가능)
│   │   ├── __init__.py
│   │   └── supervisor_state.py  # SupervisorState
│   │
│   ├── supervisor/               # Supervisor Agent (메인 오케스트레이터)
│   │   ├── __init__.py
│   │   ├── graph.py             # build_supervisor_graph()
│   │   ├── nodes.py             # 노드 함수들
│   │   └── prompts.py           # 프롬프트 템플릿
│   │
│   ├── agents/                   # Worker Agents
│   │   ├── __init__.py
│   │   ├── search/              # Phase 2: 검색 에이전트
│   │   ├── rag/                 # Phase 6: RAG 에이전트
│   │   └── base/                # Phase 6: 기본 대화 에이전트
│   │
│   ├── sub_agents/              # 공유 하위 에이전트 (평면 구조)
│   │   ├── __init__.py
│   │   ├── retriever.py         # Phase 7: 문서 검색
│   │   ├── reranker.py          # Phase 7: 재정렬
│   │   └── validator.py         # Phase 7: 검증
│   │
│   └── tools/                   # 공유 툴 (평면 구조)
│       ├── __init__.py
│       ├── search_tool.py       # Phase 2: 검색 툴
│       ├── document_tool.py     # Phase 6: 문서 툴
│       └── web_tool.py          # Phase 2: 웹 툴
│
├── api/                          # FastAPI 라우터 (향후)
│   └── __init__.py
│
└── db/                           # DB & Checkpointer (Phase 5)
    └── __init__.py
```

---

## 설계 원칙

### 1. Octostrator - 모든 것을 포함하는 시스템
- **contexts/**: 런타임 불변 정보 (user_id, session_id, db_conn)
- **states/**: 변경 가능한 상태 (messages, next 등)
- **supervisor/**: 메인 오케스트레이터
- **agents/**: 전문 에이전트들
- **sub_agents/**: 모든 에이전트가 공유하는 하위 에이전트 (평면 구조)
- **tools/**: 모든 에이전트가 공유하는 툴 (평면 구조)

### 2. 공유 리소스는 평면 구조
- `sub_agents/`, `tools/` 폴더는 **세부 폴더 없이** 평면 구조
- 모든 에이전트가 접근 가능
- 파일명으로 구분 (예: `search_tool.py`, `retriever.py`)

### 3. State vs Context 분리
- **State** (변경 가능): `states/` 폴더
- **Context** (불변): `contexts/` 폴더

---

## 현재 상태 (Phase 1 완료)

### 구현된 파일
```
octostrator/
├── states/
│   └── supervisor_state.py      ✅ SupervisorState
└── supervisor/
    ├── graph.py                 ✅ build_supervisor_graph()
    ├── nodes.py                 ⏸️ 향후 분리 예정
    └── prompts.py               ⏸️ Phase 2에서 사용
```

### 준비된 폴더 (비어있음)
```
octostrator/
├── contexts/                    ⏸️ Phase 1.5에서 추가
├── agents/                      ⏸️ Phase 2에서 추가
├── sub_agents/                  ⏸️ Phase 7에서 추가
└── tools/                       ⏸️ Phase 2에서 추가
```

---

## Import 예시

### 현재 (Phase 1)
```python
# Supervisor 사용
from backend.app.octostrator.supervisor import build_supervisor_graph

# State 사용
from backend.app.octostrator.states.supervisor_state import SupervisorState
```

### 향후 (Phase 2+)
```python
# Search Agent
from backend.app.octostrator.agents.search import search_agent_node

# 공유 툴
from backend.app.octostrator.tools.search_tool import web_search

# Context (Phase 1.5+)
from backend.app.octostrator.contexts.app_context import AppContext
```

---

## 폴더별 역할

### octostrator/contexts/
- **용도**: 런타임 불변 정보
- **예시**: user_id, session_id, db_conn, LLM 설정
- **특징**: Checkpoint에 저장 안 됨
- **파일명**: `app_context.py`, `agent_context.py`

### octostrator/states/
- **용도**: 노드 간 전달되는 변경 가능한 상태
- **예시**: messages, next, intermediate_results
- **특징**: Checkpoint에 저장됨
- **파일명**: `supervisor_state.py`, `agent_state.py`

### octostrator/supervisor/
- **용도**: 메인 오케스트레이터
- **역할**: 사용자 요청 분석 및 에이전트 선택
- **파일**: graph.py, nodes.py, prompts.py

### octostrator/agents/
- **용도**: 전문 Worker 에이전트들
- **구조**: 각 에이전트별 폴더 (search/, rag/, base/)
- **파일**: graph.py, nodes.py, prompts.py 등

### octostrator/sub_agents/
- **용도**: 모든 에이전트가 공유하는 하위 에이전트
- **구조**: 평면 (세부 폴더 없음)
- **예시**: retriever.py, reranker.py, validator.py

### octostrator/tools/
- **용도**: 모든 에이전트가 공유하는 툴
- **구조**: 평면 (세부 폴더 없음)
- **예시**: search_tool.py, document_tool.py, web_tool.py

---

## 왜 octostrator인가?

### Octopus (문어) + Orchestrator (오케스트레이터)
- **문어발**: 여러 에이전트를 동시에 제어
- **자동화**: 사용자 요청에 따라 자동으로 적절한 에이전트 선택
- **유연성**: 에이전트 추가/제거가 용이한 구조

### 특징
1. **중앙 집중**: 모든 에이전트 관련 코드가 한 곳에
2. **공유 리소스**: sub_agents, tools를 모든 에이전트가 사용
3. **명확한 분리**: Context(불변) vs State(변경)
4. **확장성**: 새 에이전트 추가 시 폴더만 생성

---

## 테스트 결과

```bash
✅ 11 passed in 13.81s

- test_root_endpoint ✅
- test_health_endpoint ✅
- test_chat_endpoint ✅
- test_chat_endpoint_korean ✅
- test_supervisor_graph_compile ✅
- test_supervisor_graph_invoke ✅
- test_supervisor_graph_korean ✅
- test_supervisor_graph_multiple_turns ✅
```

모든 테스트 통과!
