# AI PT Manager - System & Agent Flow Diagrams (Mermaid)

**프로젝트**: AI PT Manager - Todo Manager & State Management System
**날짜**: 2025-11-06
**버전**: v0.5.0

---

## 목차

1. [System Flow - 시스템 흐름](#1-system-flow---시스템-흐름)
2. [Agent Flow - 에이전트 흐름](#2-agent-flow---에이전트-흐름)
3. [Data Flow - 데이터 흐름](#3-data-flow---데이터-흐름)

---

## 1. System Flow - 시스템 흐름

### 1.1 전체 시스템 아키텍처

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Frontend["Frontend<br/>React"]
        RestClient["REST Client<br/>Postman"]
        WSClient["WebSocket Client<br/>Real-time"]
    end

    subgraph API["API Gateway Layer - FastAPI v0.5.0"]
        Middleware["Middleware Stack<br/>CORS, Auth, Rate Limiting"]
        SessionAPI["Session API<br/>4 endpoints<br/>Phase 2"]
        TodoAPI["Todo API<br/>6 endpoints<br/>Phase 2"]
        AgentAPI["Agent API<br/>1 endpoint<br/>Phase 2"]
        WSAPI["WebSocket API<br/>streaming"]
    end

    subgraph Orchestration["Orchestration Layer - LangGraph Octostrator"]
        Start([START])
        Cognitive["Cognitive Layer<br/>cognitive_node<br/>🧠 Planning & Understanding"]
        CondEdge{"Conditional Edge<br/>should_use_todo_manager"}
        TodoLayer["Todo Layer<br/>todo_node<br/>📝 Todo Management"]
        ExecuteLayer["Execute Layer<br/>execute_node<br/>⚙️ Agent Execution"]
        ResponseLayer["Response Layer<br/>response_node<br/>📊 Response Generation"]
        End([END])
    end

    subgraph State["State Management Layer - Phase 1"]
        OctoState["OctostratorState TypedDict<br/>- Basic: user_query, session_id, plan, todos<br/>- Control Flags: plan_requires_todos, need_todo_update<br/>- History: action_history, plan_history, user_interactions"]
        Reducers["Custom Reducers<br/>1. add_with_timestamp_and_step<br/>2. merge_todos_smart<br/>3. track_plan_changes<br/>4. track_user_interactions"]
        Helpers["StateHelpers Utility<br/>- get_execution_summary<br/>- get_action_at_step<br/>- get_todo_status<br/>- 4 more methods"]
    end

    subgraph DB["Persistence Layer"]
        PostgreSQL["PostgreSQL Checkpointer<br/>- State Checkpointing<br/>- Resume Support<br/>- History Tracking"]
    end

    Frontend --> API
    RestClient --> API
    WSClient --> API

    API --> Middleware
    Middleware --> SessionAPI
    Middleware --> TodoAPI
    Middleware --> AgentAPI
    Middleware --> WSAPI

    SessionAPI --> Orchestration
    TodoAPI --> Orchestration
    AgentAPI --> Orchestration
    WSAPI --> Orchestration

    Start --> Cognitive
    Cognitive --> CondEdge
    CondEdge -->|Yes<br/>todos needed| TodoLayer
    CondEdge -->|No<br/>skip todos| ExecuteLayer
    TodoLayer --> ExecuteLayer
    ExecuteLayer --> ResponseLayer
    ResponseLayer --> End

    Orchestration --> State
    OctoState --> Reducers
    OctoState --> Helpers

    State --> DB
```

### 1.2 Conditional Todo Manager Flow - 조건부 실행

```mermaid
flowchart TD
    CogComplete["Cognitive Layer Complete"]
    CondFunc["should_use_todo_manager<br/>Conditional Edge Function"]

    Check1["Check 1<br/>plan_requires_todos<br/>== True"]
    Check2["Check 2<br/>user_requested_todo_update<br/>== True"]
    Check3["Check 3<br/>need_todo_update<br/>== True"]

    TodoNode["Todo Layer Node<br/>todo_manager"]
    ExecuteNode["Execute Layer<br/>실행"]
    ExecuteSkip["Execute Layer<br/>Todo Manager 건너뛰기"]

    CogComplete --> CondFunc
    CondFunc --> Check1
    CondFunc --> Check2
    CondFunc --> Check3

    Check1 -->|Yes| TodoNode
    Check2 -->|Yes| TodoNode
    Check3 -->|Yes| TodoNode

    Check1 -->|No| ExecuteSkip
    Check2 -->|No| ExecuteSkip
    Check3 -->|No| ExecuteSkip

    TodoNode --> ExecuteNode
```

**설명**:
- **Check 1**: Cognitive가 복잡한 계획 생성 시 (예: steps > 1)
- **Check 2**: 사용자가 API로 Todo 수정 요청 시
- **Check 3**: Execute 중 새로운 Todo 필요 시

### 1.3 API Request Flow - API 요청 흐름

```mermaid
flowchart TD
    ClientReq["Client Request"]
    Endpoint["FastAPI Endpoint<br/>sessions/todos/agents"]
    Checkpointer["1. create_checkpointer<br/>PostgreSQL 연결"]
    BuildGraph["2. build_graph<br/>Octostrator 빌드"]
    Config["3. get_session_config<br/>thread_id 설정"]
    GetState["4. graph.aget_state<br/>현재 State 조회"]
    BizLogic["5. Business Logic<br/>- Todo 추가/수정/삭제<br/>- State 조회/수정<br/>- 사용자 개입 처리"]
    UpdateState["6. graph.aupdate_state<br/>State 업데이트<br/>Reducer 자동 적용"]
    RecordInt["7. Record Interaction<br/>user_interactions 기록"]
    Response["8. Return Response<br/>Success/Error"]
    ClientResp["Response to Client"]

    ClientReq --> Endpoint
    Endpoint --> Checkpointer
    Checkpointer --> BuildGraph
    BuildGraph --> Config
    Config --> GetState
    GetState --> BizLogic
    BizLogic --> UpdateState
    UpdateState --> RecordInt
    RecordInt --> Response
    Response --> ClientResp
```

### 1.4 State Update Flow with Custom Reducers

```mermaid
flowchart LR
    APICall["API Call: Add Todo<br/>{todos: [{task: 'New Task'}]}"]
    UpdateState["graph.aupdate_state"]
    Reducer["merge_todos_smart Reducer<br/>Auto-applied<br/>1. Generate UUID<br/>2. Assign step number<br/>3. Set created_at<br/>4. Set updated_at<br/>5. Merge with existing"]
    Updated["Updated State<br/>{todos: [{<br/>id: 'uuid-123',<br/>step: 4,<br/>task: 'New Task',<br/>status: 'pending',<br/>created_at: '...',<br/>updated_at: '...'<br/>}, ...existing...]}"]

    APICall --> UpdateState
    UpdateState --> Reducer
    Reducer --> Updated
```

---

## 2. Agent Flow - 에이전트 흐름

### 2.1 Agent Hierarchy - 에이전트 계층 구조

```mermaid
flowchart TD
    Octo["Octostrator<br/>Main Supervisor"]

    Cog["Cognitive Supervisor<br/>Planning"]
    Todo["Todo Agent<br/>Todo Management"]
    Exec["Execute Supervisor<br/>Execution"]
    Resp["Response Graph<br/>Response Generation"]

    Diet["DietAgent<br/>식단 관리"]
    Workout["WorkoutAgent<br/>운동 계획"]
    Health["HealthAssessmentAgent<br/>건강 평가"]
    Report["ReportAgent<br/>보고서 생성"]

    Octo --> Cog
    Octo --> Todo
    Octo --> Exec
    Octo --> Resp

    Exec --> Diet
    Exec --> Workout
    Exec --> Health
    Exec --> Report
```

### 2.2 Cognitive Layer Agent Flow

```mermaid
flowchart TD
    Start["Cognitive Layer Node"]
    Init["1. Initialize<br/>CognitiveSupervisor<br/>- LLM setup<br/>- Checkpointer connection"]
    Analyze["2. Analyze User Query<br/>- Intent understanding<br/>- Goal extraction<br/>- Context analysis"]
    GenPlan["3. Generate Plan<br/>{goal: 'Create diet plan',<br/>steps: ['Analyze profile',<br/>'Calculate calories',<br/>'Generate meal plan']}"]
    Validate["4. Validate Plan<br/>- Check completeness<br/>- Validate steps<br/>- Set plan_valid = True"]
    Decide["5. Decide Todo Manager<br/>if len.steps > 1:<br/>plan_requires_todos = True<br/>else:<br/>plan_requires_todos = False"]
    Record["6. Record History<br/>action_history ← {<br/>action: 'cognitive_node',<br/>result: {plan: ...},<br/>duration_ms: 250<br/>}<br/>plan_history ← {...}"]
    Update["7. Update State<br/>- plan<br/>- plan_valid<br/>- plan_requires_todos<br/>- created_at, updated_at"]
    CondEdge["Conditional Edge"]

    Start --> Init
    Init --> Analyze
    Analyze --> GenPlan
    GenPlan --> Validate
    Validate --> Decide
    Decide --> Record
    Record --> Update
    Update --> CondEdge
```

### 2.3 Todo Layer Agent Flow

```mermaid
flowchart TD
    Start["Todo Layer Node"]
    Init["1. Initialize TodoAgent<br/>- LLM setup<br/>- Checkpointer connection"]
    GetPlan["2. Get Plan from State<br/>plan = {goal: '...',<br/>steps: [...]}"]
    Convert["3. Convert Plan to Todos<br/>For each step:<br/>- Analyze requirements<br/>- Determine agent<br/>- Set priority<br/>- Create todo item<br/><br/>todos = [{<br/>task: 'Analyze profile',<br/>agent: 'HealthAgent',<br/>priority: 1<br/>}, {...}]"]
    HITL["4. HITL Approval if needed<br/>if not auto_approve:<br/>requires_approval = True<br/>approval_data = {todos, plan_goal}"]
    StateUpdate["5. Update State<br/>merge_todos_smart applied<br/>- Generate UUIDs<br/>- Assign step numbers<br/>- Set timestamps"]
    Execute["Execute Layer"]

    Start --> Init
    Init --> GetPlan
    GetPlan --> Convert
    Convert --> HITL
    HITL --> StateUpdate
    StateUpdate --> Execute
```

### 2.4 Execute Layer Agent Flow

```mermaid
flowchart TD
    Start["Execute Layer Node"]
    Init["1. Initialize ExecuteSupervisor<br/>- Checkpointer connection<br/>- Agent registry load"]
    GetTodos["2. Get Todos<br/>Filter: status == 'pending'<br/>Sort by: step"]

    ExecLoop["3. Execute Each Todo<br/>For todo in todos:"]

    DetAgent["3.1 Determine Agent<br/>agent_name = todo.agent"]

    subgraph Agents["3.2 Execute Agent"]
        DietExec["DietAgent<br/>- meal_planning<br/>- calorie_calc<br/>- nutrition_analysis"]
        WorkoutExec["WorkoutAgent<br/>- workout_planning<br/>- exercise_recommend"]
        HealthExec["HealthAgent<br/>- health_check<br/>- risk_assessment"]
        ReportExec["ReportAgent<br/>- report_generation<br/>- data_visualization"]
    end

    HandleResult["3.3 Handle Result<br/>Success:<br/>- Store result<br/>- status: completed<br/>Failure:<br/>- Log error<br/>- status: failed<br/>- Store error message"]

    Aggregate["4. Aggregate Results<br/>- Count completed<br/>- Count failed<br/>- Calculate success_rate<br/>- Compile execution_results"]

    RecordHistory["5. Record History<br/>action_history ← {<br/>action: 'execute_node',<br/>result: {<br/>completed: 3,<br/>failed: 0,<br/>success_rate: 1.0<br/>}}"]

    ResponseLayer["Response Layer"]

    Start --> Init
    Init --> GetTodos
    GetTodos --> ExecLoop
    ExecLoop --> DetAgent
    DetAgent --> Agents

    Agents --> DietExec
    Agents --> WorkoutExec
    Agents --> HealthExec
    Agents --> ReportExec

    DietExec --> HandleResult
    WorkoutExec --> HandleResult
    HealthExec --> HandleResult
    ReportExec --> HandleResult

    HandleResult --> Aggregate
    Aggregate --> RecordHistory
    RecordHistory --> ResponseLayer
```

### 2.5 Response Layer Agent Flow

```mermaid
flowchart TD
    Start["Response Layer Node"]
    Build["1. Build Response Graph<br/>- Chat handler<br/>- Graph handler<br/>- Report handler"]
    Approval["2. HITL Final Approval<br/>if requires_approval:<br/>Wait for user confirmation"]
    Format["3. Select Output Format<br/>output_format = state.format"]

    Chat["Chat Format"]
    Graph["Graph Format"]
    Report["Report Format"]
    Custom["Custom Format"]

    Generate["4. Generate Response<br/>- Format execution_results<br/>- Include todo status<br/>- Add recommendations"]

    Record["5. Record History<br/>action_history ← {<br/>action: 'response_node',<br/>result: {format: 'chat'}}"]

    End([END])

    Start --> Build
    Build --> Approval
    Approval --> Format

    Format --> Chat
    Format --> Graph
    Format --> Report
    Format --> Custom

    Chat --> Generate
    Graph --> Generate
    Report --> Generate
    Custom --> Generate

    Generate --> Record
    Record --> End
```

### 2.6 Domain Agent Collaboration Flow

```mermaid
flowchart LR
    User["User Query<br/>'Create personalized<br/>health plan'"]

    subgraph Planning["Planning Phase"]
        Cognitive["Cognitive<br/>분석 & 계획"]
        TodoMgr["Todo Manager<br/>작업 분배"]
    end

    subgraph Execution["Execution Phase"]
        Health["HealthAgent<br/>건강 평가<br/>📊"]
        Diet["DietAgent<br/>식단 계획<br/>🥗"]
        Workout["WorkoutAgent<br/>운동 계획<br/>💪"]
        Report["ReportAgent<br/>보고서 생성<br/>📄"]
    end

    Response["Final Response<br/>통합 건강 계획"]

    User --> Planning
    Cognitive --> TodoMgr

    TodoMgr --> Health
    Health --> Diet
    Diet --> Workout
    Workout --> Report

    Report --> Response
```

---

## 3. Data Flow - 데이터 흐름

### 3.1 State Evolution Through Layers

```mermaid
flowchart TD
    Initial["Initial State START<br/>user_query: 'Create diet plan'<br/>session_id: 'session-123'<br/>output_format: 'chat'<br/>context: {auto_approve: true}"]

    AfterCog["After Cognitive Layer<br/>+ plan: {goal, steps}<br/>+ plan_valid: true<br/>+ plan_requires_todos: true<br/>+ action_history: [step:1, action:'cognitive', ...]<br/>+ plan_history: [...]<br/>+ created_at: '2025-11-06...'"]

    AfterTodo["After Todo Layer<br/>+ todos: [{<br/>id: 'uuid-1', step: 1,<br/>task: 'Analyze profile',<br/>agent: 'HealthAgent',<br/>status: 'pending',<br/>created_at: '...', updated_at: '...'<br/>}, {...}]<br/>+ action_history: [..., step:2, action:'todo', ...]"]

    AfterExec["After Execute Layer<br/>+ execution_results: {<br/>task_1: {status: 'completed', result: {...}},<br/>task_2: {...}<br/>}<br/>+ completed: 3, failed: 0<br/>+ success_rate: 1.0<br/>+ todos: [{..., status: 'completed'}]<br/>+ action_history: [..., step:3, action:'execute', ...]"]

    AfterResp["After Response Layer END<br/>+ final_response: '...'<br/>+ response_format: 'chat'<br/>+ action_history: [..., step:4, action:'response', ...]<br/>+ total_steps: 4<br/>+ updated_at: '2025-11-06...'"]

    Initial --> AfterCog
    AfterCog --> AfterTodo
    AfterTodo --> AfterExec
    AfterExec --> AfterResp
```

### 3.2 User Interaction Data Flow - 사용자 개입

```mermaid
flowchart TD
    UserAction["User Action API Call<br/>PUT /todos/{id}<br/>{status: 'completed'}"]

    GraphUpdate["graph.aupdate_state<br/>{todos: [{id: '...', status: '...'}]}"]

    ReducerApply["merge_todos_smart<br/>Auto-applied"]

    StateUpdate["State Updated<br/>todos[0].status = 'completed'<br/>todos[0].updated_at = now"]

    RecordInt["Record User Interaction<br/>graph.aupdate_state<br/>{user_interactions: [{<br/>type: 'modify_todo',<br/>details: {...}<br/>}]}"]

    IntReducer["track_user_interactions<br/>Auto-applied"]

    FinalState["State Updated<br/>user_interactions.append({<br/>type: 'modify_todo',<br/>timestamp: now,<br/>details: {...}<br/>})"]

    UserAction --> GraphUpdate
    GraphUpdate --> ReducerApply
    ReducerApply --> StateUpdate
    StateUpdate --> RecordInt
    RecordInt --> IntReducer
    IntReducer --> FinalState
```

### 3.3 History Tracking Data Flow - 히스토리 추적

```mermaid
flowchart TD
    NodeExec["Every Node Execution"]
    StartTime["start_time = now"]
    ExecLogic["Execute Node Logic"]
    EndTime["end_time = now<br/>duration_ms = end - start"]

    RecordAction["state['action_history'] = [{<br/>action: 'node_name',<br/>result: {...},<br/>duration_ms: duration<br/>}]"]

    AutoReducer["add_with_timestamp_and_step<br/>Auto-applied<br/><br/>Auto-added:<br/>- step: 1 or next step number<br/>- timestamp: '2025-11-06...'"]

    NodeExec --> StartTime
    StartTime --> ExecLogic
    ExecLogic --> EndTime
    EndTime --> RecordAction
    RecordAction --> AutoReducer
```

### 3.4 Complete Request-Response Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Graph
    participant State
    participant Reducers
    participant DB

    Client->>API: POST /chat<br/>{query: "Create diet plan"}
    API->>Graph: build_graph & config
    Graph->>State: Initialize state
    State->>DB: Load checkpoint

    Note over Graph: Cognitive Layer
    Graph->>State: Update plan, plan_requires_todos
    State->>Reducers: track_plan_changes
    Reducers->>State: Add version, timestamp
    State->>DB: Save checkpoint

    Note over Graph: Todo Layer
    Graph->>State: Update todos
    State->>Reducers: merge_todos_smart
    Reducers->>State: Add UUIDs, steps, timestamps
    State->>DB: Save checkpoint

    Note over Graph: Execute Layer
    Graph->>State: Update execution_results, todos
    State->>Reducers: merge_todos_smart
    Reducers->>State: Update status, updated_at
    State->>DB: Save checkpoint

    Note over Graph: Response Layer
    Graph->>State: Update final_response
    State->>Reducers: add_with_timestamp_and_step
    Reducers->>State: Add step, timestamp
    State->>DB: Save final checkpoint

    Graph->>API: Return response
    API->>Client: 200 OK<br/>{response: "..."}
```

### 3.5 Interrupt & Resume Flow - 중단 및 재개

```mermaid
flowchart TD
    Running["Session Running<br/>Execute Layer"]
    UserInt["User Action<br/>POST /interrupt<br/>{reason: 'need_modification'}"]

    SetFlag["Set State<br/>requires_approval = True<br/>user_interactions ← interrupt"]

    GraphPause["Graph Execution Paused<br/>Checkpoint Saved"]

    UserMod["User Modifies<br/>PUT /todos/{id}<br/>POST /todos<br/>DELETE /todos/{id}"]

    StateChange["State Updated<br/>Reducers Applied<br/>user_interactions ← modify"]

    Resume["User Resume<br/>POST /resume"]

    ClearFlag["Clear Flag<br/>requires_approval = False"]

    Continue["Graph Continues<br/>from last checkpoint"]

    Complete["Execution Completes"]

    Running --> UserInt
    UserInt --> SetFlag
    SetFlag --> GraphPause
    GraphPause --> UserMod
    UserMod --> StateChange
    StateChange --> Resume
    Resume --> ClearFlag
    ClearFlag --> Continue
    Continue --> Complete
```

---

## 요약

### System Flow 핵심 포인트

1. **Client → API Gateway → Octostrator → State → DB**
2. **Conditional Todo Manager**: 필요시에만 실행하여 성능 최적화
3. **Custom Reducers**: State 업데이트 시 자동 적용
4. **StateHelpers**: State 조회 간소화

### Agent Flow 핵심 포인트

1. **4-Layer Architecture**: Cognitive → Todo → Execute → Response
2. **Hierarchical Agent System**: Octostrator → Layer Supervisors → Domain Agents
3. **Dynamic Agent Selection**: Todo의 agent 필드로 동적 선택
4. **Agent Capabilities**: 각 Agent의 특화된 기능

### Data Flow 핵심 포인트

1. **State Evolution**: 각 Layer를 거치며 State가 점진적으로 완성
2. **History Tracking**: 모든 작업 내역 자동 기록
3. **User Interaction**: API를 통한 사용자 개입 추적
4. **Automatic Metadata**: 타임스탬프, step 번호 자동 관리

---

**작성자**: AI PT Manager Development Team
**최종 업데이트**: 2025-11-06
**버전**: v0.5.0
