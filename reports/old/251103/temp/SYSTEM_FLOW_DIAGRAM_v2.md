# 부동산 AI 시스템 흐름도 v2

**버전**: 2.0
**작성일**: 2025-10-09
**주요 변경사항**: WebSocket 실시간 통신, Progress Flow UI, Checkpointing 반영

---

## 전체 시스템 아키텍처

### 🔄 v1에서 v2로의 주요 변경점

| 항목 | v1 | v2 |
|------|----|----|
| **통신 방식** | HTTP POST | WebSocket (실시간) |
| **응답 방식** | 동기식 (완료 후 응답) | 스트리밍 (progress_callback) |
| **프론트엔드** | 단순 로딩 스피너 | ExecutionPlanPage + ExecutionProgressPage |
| **State 관리** | In-memory | LangGraph Checkpointing (SQLite) |
| **Todo 관리** | 없음 | 실시간 todo 업데이트 (pending → in_progress → completed) |

---

## 📡 WebSocket 기반 실시간 통신 플로우

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant Frontend as 🖥️ Frontend<br/>(ChatInterface)
    participant WS as 🔌 WebSocket<br/>(ConnectionManager)
    participant API as 📡 chat_api.py
    participant Supervisor as 🎯 TeamSupervisor<br/>(LangGraph)
    participant Planning as 🧠 PlanningAgent
    participant Executor as ⚙️ ExecutionAgents
    participant DB as 💾 AsyncSqliteSaver

    %% 연결 단계
    User->>Frontend: 1. 페이지 접속
    Frontend->>API: 2. POST /api/v1/chat/start
    API-->>Frontend: 3. session_id 반환
    Frontend->>WS: 4. WebSocket 연결<br/>/ws/{session_id}
    WS-->>Frontend: 5. connected 메시지

    %% 쿼리 전송
    User->>Frontend: 6. "전세금 인상기준은?" 입력
    Frontend->>Frontend: 7. processState.step = "planning"<br/>"계획 중..." 스피너 표시
    Frontend->>WS: 8. {"type": "query", "query": "..."}
    WS->>API: 9. 쿼리 수신
    API->>Supervisor: 10. process_query_streaming(query, session_id, progress_callback)

    %% Planning 단계
    Supervisor->>Planning: 11. planning_node 실행
    Planning-->>WS: 12. planning_start 이벤트
    WS-->>Frontend: 13. "계획을 수립하고 있습니다..."

    Planning->>Planning: 14. 🤖 LLM #1: intent_analysis
    Planning->>Planning: 15. 🤖 LLM #2: agent_selection
    Planning-->>WS: 16. plan_ready 이벤트<br/>{intent, execution_steps, estimated_time}
    WS-->>Frontend: 17. ExecutionPlanPage 생성
    Frontend->>Frontend: 18. 800ms 후<br/>ExecutionProgressPage 자동 생성<br/>스피너 제거

    %% 체크포인트 저장
    Supervisor->>DB: 19. 상태 저장 (planning 완료)

    %% Execution 단계
    Supervisor->>Executor: 20. execute_teams_node
    Executor->>Executor: 21. SearchTeam 실행 시작
    Executor-->>WS: 22. todo_updated<br/>{step[0]: "in_progress"}
    WS-->>Frontend: 23. StepItem 상태 업데이트<br/>(pending → in_progress)

    Executor->>Executor: 24. 🤖 LLM #4, #5: 검색
    Executor->>Executor: 25. SearchTeam 완료
    Executor-->>WS: 26. todo_updated<br/>{step[0]: "completed"}
    WS-->>Frontend: 27. StepItem 상태 업데이트<br/>(in_progress → completed)

    Executor->>Executor: 28. AnalysisTeam 실행
    Executor-->>WS: 29. todo_updated<br/>{step[1]: "in_progress"}
    WS-->>Frontend: 30. StepItem 상태 업데이트

    Executor->>Executor: 31. 🤖 LLM #6-#9: 분석
    Executor->>Executor: 32. AnalysisTeam 완료
    Executor-->>WS: 33. todo_updated<br/>{step[1]: "completed"}
    WS-->>Frontend: 34. StepItem 완료 표시

    %% 체크포인트 저장
    Supervisor->>DB: 35. 상태 저장 (execution 완료)

    %% Response 단계
    Supervisor->>Supervisor: 36. aggregate_results_node
    Supervisor->>Supervisor: 37. generate_response_node<br/>🤖 LLM #10
    Supervisor-->>WS: 38. final_response<br/>{type, content, data}
    WS-->>Frontend: 39. ExecutionPlanPage,<br/>ExecutionProgressPage 제거
    Frontend->>Frontend: 40. 봇 답변 메시지 추가<br/>processState.step = "idle"
    Frontend-->>User: 41. 답변 표시 ✅
```

---

## 🏗️ 백엔드 아키텍처 (LangGraph 기반)

```mermaid
flowchart TD
    User([👤 사용자])

    %% ============================================
    %% WebSocket Layer
    %% ============================================
    subgraph WSLayer["🔌 WebSocket Layer"]
        WSEndpoint["/ws/{session_id}"]
        ConnMgr["ConnectionManager<br/>- active_connections<br/>- message_queue"]
        SessMgr["SessionManager<br/>- session_id 생성<br/>- 세션 검증"]
    end

    User -->|WebSocket 연결| WSEndpoint
    WSEndpoint --> ConnMgr
    WSEndpoint --> SessMgr

    %% ============================================
    %% Supervisor (LangGraph)
    %% ============================================
    subgraph Supervisor["🎯 TeamBasedSupervisor (LangGraph)"]
        direction TB
        Init["initialize_node<br/>⚙️ 상태 초기화"]
        Plan["planning_node<br/>🧠 의도 분석 & 계획"]
        Route{"route_after_planning<br/>🔀 라우팅"}
        Exec["execute_teams_node<br/>⚙️ 팀 실행"]
        Agg["aggregate_results_node<br/>📊 결과 통합"]
        Resp["generate_response_node<br/>📝 응답 생성"]

        Init --> Plan
        Plan --> Route
        Route -->|execution_steps 있음| Exec
        Route -->|execution_steps 없음<br/>또는 IRRELEVANT/UNCLEAR| Resp
        Exec --> Agg
        Agg --> Resp
    end

    ConnMgr -->|query 수신| Init

    %% ============================================
    %% Checkpointing
    %% ============================================
    subgraph Checkpoint["💾 Checkpointing"]
        SQLite["AsyncSqliteSaver<br/>checkpoints.db"]
    end

    Plan -.->|상태 저장| SQLite
    Exec -.->|상태 저장| SQLite
    Agg -.->|상태 저장| SQLite

    %% ============================================
    %% Planning Agent
    %% ============================================
    subgraph PlanningAgent["🧠 PlanningAgent"]
        direction TB
        IntentAnalysis["analyze_intent<br/>🤖 LLM #1<br/>intent_analysis.txt"]
        IntentCheck{intent_type?}
        SkipAgent["⚡ Skip Agent Selection<br/>(IRRELEVANT/UNCLEAR)"]
        AgentSelection["suggest_agents<br/>🤖 LLM #2<br/>agent_selection.txt"]
        QueryDecomp["QueryDecomposer<br/>🤖 LLM #3<br/>query_decomposition.txt"]
        CreatePlan["create_execution_plan<br/>📋 실행 계획 생성"]

        IntentAnalysis --> IntentCheck
        IntentCheck -->|IRRELEVANT<br/>or UNCLEAR| SkipAgent
        IntentCheck -->|정상| AgentSelection
        SkipAgent --> CreatePlan
        AgentSelection --> QueryDecomp
        QueryDecomp --> CreatePlan
    end

    Plan --> IntentAnalysis

    %% ============================================
    %% Execution Agents
    %% ============================================
    subgraph Executors["⚙️ Execution Agents"]
        direction LR

        subgraph Search["SearchExecutor"]
            SearchKW["🤖 LLM #4<br/>keyword_extraction"]
            SearchTool["🤖 LLM #5<br/>tool_selection_search"]
            SearchTools["🔧 Tools<br/>Legal/Market/Loan"]
        end

        subgraph Analysis["AnalysisExecutor"]
            AnalysisTool["🤖 LLM #6<br/>tool_selection_analysis"]
            AnalysisTools["🔧 Tools<br/>Contract/Market"]
            AnalysisLLM["🤖 LLM #7-#9<br/>분석 & 종합"]
        end

        subgraph Document["DocumentExecutor"]
            DocGen["문서 생성"]
        end
    end

    Exec --> Search
    Exec --> Analysis
    Exec --> Document

    %% ============================================
    %% Progress Callback
    %% ============================================
    subgraph Callbacks["📡 Progress Callbacks"]
        CB1["planning_start<br/>'계획을 수립하고 있습니다...'"]
        CB2["plan_ready<br/>{intent, execution_steps,<br/>estimated_total_time}"]
        CB3["todo_updated<br/>{execution_steps<br/>with updated status}"]
        CB4["final_response<br/>{type, content, data}"]
    end

    IntentAnalysis -.->|callback| CB1
    CreatePlan -.->|callback| CB2
    Search -.->|callback| CB3
    Analysis -.->|callback| CB3
    Resp -.->|callback| CB4

    CB1 -.->|send_message| ConnMgr
    CB2 -.->|send_message| ConnMgr
    CB3 -.->|send_message| ConnMgr
    CB4 -.->|send_message| ConnMgr

    %% ============================================
    %% Response Generation
    %% ============================================
    RespCheck{intent_type?}
    Guidance["_generate_out_of_scope_response<br/>안내 메시지"]
    LLMResp["_generate_llm_response<br/>🤖 LLM #10<br/>response_synthesis.txt"]
    SimpleResp["_generate_simple_response<br/>단순 응답"]

    Resp --> RespCheck
    RespCheck -->|IRRELEVANT<br/>or UNCLEAR| Guidance
    RespCheck -->|결과 있음| LLMResp
    RespCheck -->|결과 없음| SimpleResp

    Guidance -.->|callback| CB4
    LLMResp -.->|callback| CB4
    SimpleResp -.->|callback| CB4

    %% ============================================
    %% Frontend
    %% ============================================
    ConnMgr -->|WebSocket 메시지| User

    %% ============================================
    %% Styling
    %% ============================================
    classDef llmNode fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef wsNode fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dbNode fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef skipNode fill:#ffebee,stroke:#c62828,stroke-width:2px

    class IntentAnalysis,AgentSelection,QueryDecomp,SearchKW,SearchTool,AnalysisTool,AnalysisLLM,LLMResp llmNode
    class WSEndpoint,ConnMgr,CB1,CB2,CB3,CB4 wsNode
    class SQLite dbNode
    class SkipAgent skipNode
```

---

## 🖥️ 프론트엔드 UI 플로우 (Progress Flow v3)

```mermaid
stateDiagram-v2
    [*] --> Idle: 페이지 로드

    Idle --> Planning: 질문 입력<br/>(query 전송)

    state Planning {
        [*] --> Spinner
        Spinner: 🔄 "계획을 수립하고 있습니다..."<br/>로딩 스피너 표시
    }

    Planning --> PlanReady: plan_ready 수신

    state PlanReady {
        [*] --> ExecutionPlanPage
        ExecutionPlanPage: 📋 ExecutionPlanPage<br/>- 감지된 의도<br/>- 예정 작업 리스트<br/>- 예상 소요 시간
        ExecutionPlanPage --> Wait800ms: 표시
        Wait800ms: ⏱️ 800ms 대기
    }

    PlanReady --> Executing: 800ms 경과

    state Executing {
        [*] --> ExecutionProgressPage
        ExecutionProgressPage: 📊 ExecutionProgressPage<br/>- Step 리스트 (StepItem)<br/>- 전체 진행률<br/>- 경과 시간<br/>- 스피너 제거 ✅

        ExecutionProgressPage --> UpdateSteps: todo_updated 수신
        UpdateSteps: 🔄 Step 상태 업데이트<br/>pending → in_progress → completed
        UpdateSteps --> ExecutionProgressPage: 계속 표시
    }

    Executing --> Completed: final_response 수신

    state Completed {
        [*] --> RemoveProgress
        RemoveProgress: 🗑️ ExecutionPlanPage,<br/>ExecutionProgressPage 제거
        RemoveProgress --> ShowAnswer
        ShowAnswer: 💬 봇 답변 표시
        ShowAnswer --> SetIdle
        SetIdle: ⚙️ processState.step = "idle"
    }

    Completed --> Idle: 입력 활성화

    note right of Planning
        WebSocket 메시지:
        - planning_start
    end note

    note right of PlanReady
        WebSocket 메시지:
        - plan_ready
        데이터:
        - intent
        - execution_steps
        - estimated_total_time
    end note

    note right of Executing
        WebSocket 메시지:
        - todo_updated (여러 번)
        실시간 업데이트:
        - Step 1: pending → in_progress
        - Step 1: in_progress → completed
        - Step 2: pending → in_progress
        - Step 2: in_progress → completed
    end note

    note right of Completed
        WebSocket 메시지:
        - final_response
        데이터:
        - type (guidance/summary)
        - content/message
        - data (팀 결과)
    end note
```

---

## 📊 WebSocket 메시지 프로토콜

### Client → Server

| 메시지 타입 | 필드 | 설명 |
|------------|------|------|
| `query` | `query`, `enable_checkpointing` | 사용자 쿼리 전송 |
| `interrupt_response` | `action`, `modified_todos` | Plan 승인/수정 (TODO) |
| `todo_skip` | `todo_id` | Todo 건너뛰기 (TODO) |

### Server → Client

| 메시지 타입 | 발생 시점 | 필드 | 프론트엔드 동작 |
|------------|----------|------|---------------|
| `connected` | WebSocket 연결 시 | - | 연결 확인 |
| `planning_start` | planning_node 시작 | `message` | 스피너 표시 |
| `plan_ready` | planning_node 완료 | `intent`, `confidence`, `execution_steps`, `estimated_total_time`, `keywords` | ExecutionPlanPage 생성<br/>800ms 후 ExecutionProgressPage 생성 |
| `todo_created` | 초기 todo 생성 | `execution_steps` | (미사용) |
| `todo_updated` | Step 상태 변경 | `execution_steps` | ExecutionProgressPage의 steps 업데이트 |
| `step_start` | Step 시작 | `agent`, `task` | (현재 미사용) |
| `step_progress` | Step 진행 중 | `progress_percentage` | (현재 미사용) |
| `step_complete` | Step 완료 | `result` | (현재 미사용) |
| `final_response` | generate_response_node 완료 | `response` (content/answer/message) | Progress 제거<br/>답변 표시<br/>idle 전환 |
| `error` | 에러 발생 | `error` | 에러 메시지 표시<br/>idle 전환 |

---

## 🤖 LLM 호출 지점 상세 정리

### LLM 호출 통계

| # | 호출 위치 | 프롬프트 파일 | 모델 | Temp | 방식 | 목적 |
|---|----------|-------------|------|------|------|------|
| 1 | PlanningAgent.analyze_intent | `intent_analysis.txt` | GPT-4o-mini | 0.0 | async | 사용자 의도 분석 |
| 2 | PlanningAgent.suggest_agents | `agent_selection.txt` | GPT-4o-mini | 0.0 | async | Agent 선택 (IRRELEVANT/UNCLEAR은 생략⚡) |
| 2b | PlanningAgent (fallback) | `agent_selection_simple.txt` | GPT-4o-mini | 0.0 | async | 단순 Agent 선택 |
| 3 | QueryDecomposer.decompose | `query_decomposition.txt` | GPT-4o-mini | 0.1 | async | 복합 질문 분해 |
| 4 | SearchExecutor | `keyword_extraction.txt` | GPT-4o-mini | 0.1 | **sync** | 검색 키워드 추출 |
| 5 | SearchExecutor | `tool_selection_search.txt` | GPT-4o-mini | 0.1 | async | 검색 도구 선택 |
| 6 | AnalysisExecutor | `tool_selection_analysis.txt` | GPT-4o-mini | 0.0 | async | 분석 도구 선택 |
| 7 | ContractAnalysisTool | ⚠️ 인라인 프롬프트 | GPT-4o-mini | 0.3 | async | 계약서 분석 |
| 8 | MarketAnalysisTool | `insight_generation.txt` | GPT-4o-mini | 0.3 | async | 시장 인사이트 생성 |
| 9 | AnalysisExecutor | `insight_generation.txt` | GPT-4o-mini | 0.3 | async | 분석 인사이트 종합 |
| 10 | TeamSupervisor.generate_response | `response_synthesis.txt` | GPT-4o-mini | 0.3 | async | 최종 응답 생성 |

---

## 🔄 주요 처리 흐름 (시나리오별)

### 1. IRRELEVANT 쿼리 (빠른 경로) ⚡

```
사용자: "안녕" 입력
   ↓
Frontend: WebSocket 연결 → query 전송
   ↓
Backend: planning_node
   ├─ 🤖 LLM #1: intent_analysis → IRRELEVANT
   ├─ ⚡ Skip LLM #2 (agent_selection)
   └─ create_execution_plan → Empty Plan (execution_steps: [])
   ↓
route_after_planning → "respond" (execute 건너뛰기)
   ↓
generate_response_node
   └─ _generate_out_of_scope_response → 안내 메시지
   ↓
final_response 전송 → Frontend
   ↓
Frontend: 안내 메시지 표시
```

**WebSocket 메시지**:
1. `planning_start` → 스피너 표시
2. `plan_ready` (execution_steps: []) → ExecutionPlanPage 생성 시도 (빈 배열)
3. `final_response` (type: "guidance") → 안내 메시지 표시

**LLM 호출**: 1회 (intent_analysis)
**소요 시간**: ~0.6초

---

### 2. 단순 부동산 질문 (일반 경로)

```
사용자: "전세금 인상기준은?" 입력
   ↓
Frontend: WebSocket 연결 → query 전송
   ↓
Backend: planning_node
   ├─ 🤖 LLM #1: intent_analysis → LEGAL_CONSULT
   ├─ 🤖 LLM #2: agent_selection → ["search_team"]
   └─ create_execution_plan → Simple Plan (1 step)
   ↓
route_after_planning → "execute"
   ↓
execute_teams_node
   ├─ SearchTeam 시작 → todo_updated (step 0: in_progress)
   ├─ 🤖 LLM #4: keyword_extraction
   ├─ 🤖 LLM #5: tool_selection_search
   ├─ Tools 실행 (LegalSearchTool)
   └─ SearchTeam 완료 → todo_updated (step 0: completed)
   ↓
aggregate_results_node
   ↓
generate_response_node
   └─ 🤖 LLM #10: response_synthesis
   ↓
final_response 전송 → Frontend
   ↓
Frontend: 답변 표시
```

**WebSocket 메시지**:
1. `planning_start`
2. `plan_ready` (execution_steps: [{ step_id, team: "search", status: "pending", ... }])
3. 800ms 후 Frontend가 ExecutionProgressPage 자동 생성
4. `todo_updated` (step 0: "in_progress")
5. `todo_updated` (step 0: "completed")
6. `final_response` (type: "summary", content: "...")

**LLM 호출**: 5회 (intent + agent + keyword + tool_sel + response)
**소요 시간**: ~5-7초

---

### 3. 복합 질문 + 분석 (전체 경로)

```
사용자: "강남구 아파트 전세 시세와 위험도 분석해줘" 입력
   ↓
Frontend: WebSocket 연결 → query 전송
   ↓
Backend: planning_node
   ├─ 🤖 LLM #1: intent_analysis → COMPREHENSIVE
   ├─ 🤖 LLM #2: agent_selection → ["search_team", "analysis_team"]
   ├─ 🤖 LLM #3: query_decomposition
   └─ create_execution_plan → Complex Plan (2 steps)
   ↓
route_after_planning → "execute"
   ↓
execute_teams_node (Sequential)
   │
   ├─ SearchTeam 시작 → todo_updated (step 0: in_progress)
   │  ├─ 🤖 LLM #4: keyword_extraction
   │  ├─ 🤖 LLM #5: tool_selection_search
   │  ├─ Tools 실행 (LegalSearchTool, MarketDataTool)
   │  └─ SearchTeam 완료 → todo_updated (step 0: completed)
   │
   └─ AnalysisTeam 시작 → todo_updated (step 1: in_progress)
      ├─ 🤖 LLM #6: tool_selection_analysis
      ├─ ContractAnalysisTool
      │  └─ 🤖 LLM #7: contract_analysis (인라인)
      ├─ MarketAnalysisTool
      │  └─ 🤖 LLM #8: insight_generation
      ├─ 🤖 LLM #9: insight_generation (종합)
      └─ AnalysisTeam 완료 → todo_updated (step 1: completed)
   ↓
aggregate_results_node
   ↓
generate_response_node
   └─ 🤖 LLM #10: response_synthesis
   ↓
final_response 전송 → Frontend
   ↓
Frontend: 답변 표시
```

**WebSocket 메시지**:
1. `planning_start`
2. `plan_ready` (execution_steps: [step0, step1])
3. 800ms 후 ExecutionProgressPage 자동 생성
4. `todo_updated` (step 0: "in_progress")
5. `todo_updated` (step 0: "completed", step 1: "pending")
6. `todo_updated` (step 1: "in_progress")
7. `todo_updated` (step 1: "completed")
8. `final_response`

**LLM 호출**: 최대 10회 (모든 LLM)
**소요 시간**: ~15-20초

---

## 🎯 최적화 포인트

### ✅ 이미 적용된 최적화

1. **IRRELEVANT/UNCLEAR 조기 종료** (LLM #2 생략)
   - 위치: `planning_agent.py:172-181`
   - 효과: ~5초 → ~0.6초 (약 90% 단축)

2. **WebSocket 실시간 통신**
   - HTTP POST (동기) → WebSocket (스트리밍)
   - 효과: 사용자 경험 개선, 진행 상황 실시간 확인

3. **Progress Flow UI** (v3)
   - ExecutionPlanPage + ExecutionProgressPage
   - 효과: 투명성 향상, 대기 시간 체감 감소

4. **Checkpointing (LangGraph)**
   - 대화 상태 저장
   - 효과: 재연결 시 복구 가능 (TODO)

5. **Intent Analysis 파라미터 최적화**
   - Temperature: 0.1 → 0.0
   - max_tokens: 500 추가
   - 효과: ~0.5초 단축

### 💡 추가 최적화 가능

1. **패턴 기반 빠른 감지** (LLM #1도 생략)
   - 간단한 인사말은 LLM 호출 없이 즉시 판단
   - 예상 효과: 0.6초 → 0.1초

2. **병렬 LLM 호출**
   - LLM #4, #5, #6 동시 호출 (현재는 순차)
   - 예상 효과: ~30% 시간 단축

3. **캐싱 전략**
   - 동일 쿼리 재요청 시 결과 재사용
   - Redis/Memcached 활용

4. **Frontend Skeleton UI**
   - ExecutionPlanPage 대신 Skeleton 표시
   - 더 빠른 시각적 피드백

---

## 📂 주요 파일 구조

### Backend

```
backend/
├── app/
│   ├── api/
│   │   ├── chat_api.py               ✅ WebSocket 엔드포인트
│   │   ├── ws_manager.py             ✅ ConnectionManager
│   │   ├── session_manager.py        ✅ SessionManager
│   │   └── schemas.py
│   │
│   └── service_agent/
│       ├── supervisor/
│       │   └── team_supervisor.py    ✅ TeamBasedSupervisor (LangGraph)
│       │
│       ├── cognitive_agents/
│       │   ├── planning_agent.py     ✅ PlanningAgent
│       │   └── query_decomposer.py   ✅ QueryDecomposer
│       │
│       ├── execution_agents/
│       │   ├── search_executor.py    ✅ SearchExecutor
│       │   ├── analysis_executor.py  ✅ AnalysisExecutor
│       │   └── document_executor.py  ✅ DocumentExecutor
│       │
│       └── llm_manager/
│           ├── llm_service.py        ✅ LLMService
│           ├── prompt_manager.py     ✅ PromptManager
│           └── prompts/
│               ├── cognitive/
│               │   ├── intent_analysis.txt
│               │   ├── agent_selection.txt
│               │   └── query_decomposition.txt
│               └── execution/
│                   ├── keyword_extraction.txt
│                   ├── tool_selection_search.txt
│                   ├── tool_selection_analysis.txt
│                   ├── insight_generation.txt
│                   └── response_synthesis.txt
```

### Frontend

```
frontend/
├── components/
│   ├── chat-interface.tsx            ✅ 메인 채팅 인터페이스
│   ├── execution-plan-page.tsx       ✅ 실행 계획 표시
│   ├── execution-progress-page.tsx   ✅ 실행 진행 상황 표시
│   ├── step-item.tsx                 ✅ 개별 Step UI
│   └── ui/
│       └── progress-bar.tsx          ✅ 진행률 바
│
├── lib/
│   ├── ws.ts                         ✅ WebSocket 클라이언트
│   └── types.ts
│
└── types/
    ├── process.ts                    ✅ ProcessState 타입
    └── execution.ts                  ✅ ExecutionStep, ExecutionPlan 타입
```

---

## 🔮 향후 개선 계획

### Phase 1: 성능 최적화
- [ ] 패턴 기반 인사말 감지 (LLM 호출 생략)
- [ ] LLM 호출 병렬화 (LLM #4, #5, #6)
- [ ] 결과 캐싱 (Redis)

### Phase 2: 기능 확장
- [ ] Human-in-the-Loop (Plan 수정)
- [ ] Step Skip 기능
- [ ] 재연결 시 State 복원 (Checkpointing 활용)

### Phase 3: UI/UX 개선
- [ ] Skeleton UI (로딩 상태)
- [ ] 애니메이션 추가 (전환 효과)
- [ ] 에러 처리 강화

### Phase 4: 모니터링
- [ ] LLM 호출 통계 대시보드
- [ ] 응답 시간 분석
- [ ] 에러 추적 (Sentry)

---

## 📚 참고 문서

- **v1 다이어그램**: `SYSTEM_FLOW_DIAGRAM.md` (HTTP 기반)
- **Progress Flow v3**: `plan_of_progress_flow_v3.md`
- **아키텍처 문서**: `backend/app/service_agent/reports/ARCHITECTURE_COMPLETE.md`

---

**생성일**: 2025-10-09
**버전**: 2.0
**마지막 업데이트**: WebSocket 실시간 통신, Progress Flow v3, Checkpointing 반영
