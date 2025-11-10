# AI PT Manager - System & Agent Flow Diagrams

**프로젝트**: AI PT Manager - Todo Manager & State Management System
**날짜**: 2025-11-06
**버전**: v0.5.0

---

## 목차

1. [System Flow (시스템 흐름)](#1-system-flow-시스템-흐름)
2. [Agent Flow (에이전트 흐름)](#2-agent-flow-에이전트-흐름)
3. [Data Flow (데이터 흐름)](#3-data-flow-데이터-흐름)

---

## 1. System Flow (시스템 흐름)

### 1.1 전체 시스템 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│                          Client Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │   Frontend   │  │  REST Client │  │  WebSocket Client  │   │
│  │   (React)    │  │   (Postman)  │  │  (Real-time)       │   │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘   │
└─────────┼──────────────────┼────────────────────┼──────────────┘
          │                  │                    │
          └──────────────────┴────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                    API Gateway Layer (FastAPI)                  │
│                          Version 0.5.0                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Middleware Stack                                        │  │
│  │  - CORS                                                  │  │
│  │  - Authentication (Future)                               │  │
│  │  - Rate Limiting (Future)                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────┬─────────────┬─────────────┬────────────────┐ │
│  │ Session API │  Todo API   │ Agent API   │ WebSocket API  │ │
│  │ 4 endpoints │ 6 endpoints │ 1 endpoint  │  (streaming)   │ │
│  │  (Phase 2)  │  (Phase 2)  │  (Phase 2)  │   (기존)        │ │
│  └─────────────┴─────────────┴─────────────┴────────────────┘ │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│               Orchestration Layer (LangGraph)                   │
│                    Octostrator Supervisor                       │
│                                                                 │
│    START                                                        │
│      ↓                                                          │
│    ┌────────────────────┐                                      │
│    │ Cognitive Layer    │  🧠 Planning & Understanding         │
│    │ (cognitive_node)   │                                      │
│    └─────────┬──────────┘                                      │
│              │                                                  │
│              ▼                                                  │
│      [Conditional Edge]                                         │
│    should_use_todo_manager()                                    │
│              │                                                  │
│      ┌───────┴───────┐                                         │
│     Yes              No                                         │
│      │               │                                          │
│      ▼               │                                          │
│  ┌─────────────┐     │                                          │
│  │ Todo Layer  │     │  📝 Todo Management                      │
│  │ (todo_node) │     │                                          │
│  └──────┬──────┘     │                                          │
│         │            │                                          │
│         └────────────┘                                          │
│              │                                                  │
│              ▼                                                  │
│    ┌────────────────────┐                                      │
│    │  Execute Layer     │  ⚙️ Agent Execution                  │
│    │  (execute_node)    │                                      │
│    └─────────┬──────────┘                                      │
│              │                                                  │
│              ▼                                                  │
│    ┌────────────────────┐                                      │
│    │  Response Layer    │  📊 Response Generation              │
│    │  (response_node)   │                                      │
│    └─────────┬──────────┘                                      │
│              │                                                  │
│              ▼                                                  │
│            END                                                  │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│              State Management Layer (Phase 1)                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              OctostratorState (TypedDict)                │ │
│  │                                                          │ │
│  │  Basic:                                                  │ │
│  │  - user_query, session_id, output_format               │ │
│  │  - plan, todos, execution_results                       │ │
│  │                                                          │ │
│  │  Control Flags (Phase 1):                               │ │
│  │  - plan_requires_todos                                  │ │
│  │  - need_todo_update                                     │ │
│  │  - user_requested_todo_update                           │ │
│  │                                                          │ │
│  │  History Tracking (Phase 1):                            │ │
│  │  - action_history (Annotated: add_with_timestamp)       │ │
│  │  - plan_history (Annotated: track_plan_changes)         │ │
│  │  - user_interactions (Annotated: track_interactions)    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         Custom Reducer Functions (Phase 1)               │ │
│  │  1. add_with_timestamp_and_step                          │ │
│  │  2. merge_todos_smart                                    │ │
│  │  3. track_plan_changes                                   │ │
│  │  4. track_user_interactions                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         StateHelpers Utility (Phase 1)                   │ │
│  │  - get_execution_summary()                               │ │
│  │  - get_action_at_step()                                  │ │
│  │  - get_todo_status()                                     │ │
│  │  - 4 more methods...                                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│         Persistence Layer (PostgreSQL Checkpointer)             │
│  - State Checkpointing                                          │
│  - Resume Support                                               │
│  - History Tracking                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Conditional Todo Manager Flow (Phase 1 핵심)

```
                    Cognitive Layer Complete
                              │
                              ▼
              ┌───────────────────────────────┐
              │  should_use_todo_manager()    │
              │  (Conditional Edge Function)  │
              └────────────┬──────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐     ┌─────────┐
    │ Check 1 │      │ Check 2 │     │ Check 3 │
    └────┬────┘      └────┬────┘     └────┬────┘
         │                │                │
         │                │                │
    plan_requires    user_requested    need_todo
    _todos == True   _todo_update      _update
         │           == True            == True
         │                │                │
         │                │                │
         └────────────────┼────────────────┘
                          │
                         Yes
                          │
                          ▼
              ┌───────────────────────┐
              │    Todo Layer Node    │
              │   (todo_manager)      │
              └──────────┬────────────┘
                         │
                         ▼
                   Execute Layer


                         No
                          │
                          ▼
                   Execute Layer
                   (Todo Manager 건너뛰기)
```

**설명**:
- **Check 1**: Cognitive가 복잡한 계획 생성 시 (예: steps > 1)
- **Check 2**: 사용자가 API로 Todo 수정 요청 시
- **Check 3**: Execute 중 새로운 Todo 필요 시

### 1.3 API Request Flow (Phase 2)

```
           Client Request
                 │
                 ▼
    ┌────────────────────────────┐
    │  FastAPI Endpoint          │
    │  (sessions/todos/agents)   │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  1. create_checkpointer()  │
    │     - PostgreSQL 연결      │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  2. build_graph()          │
    │     - Octostrator 빌드     │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  3. get_session_config()   │
    │     - thread_id 설정       │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  4. graph.aget_state()     │
    │     - 현재 State 조회       │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  5. Business Logic         │
    │     - Todo 추가/수정/삭제  │
    │     - State 조회/수정      │
    │     - 사용자 개입 처리      │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  6. graph.aupdate_state()  │
    │     - State 업데이트       │
    │     - Reducer 자동 적용    │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  7. Record Interaction     │
    │     - user_interactions    │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────────┐
    │  8. Return Response        │
    │     - Success/Error        │
    └────────────────────────────┘
             │
             ▼
        Response to Client
```

### 1.4 State Update Flow with Custom Reducers

```
    API Call: Add Todo
         │
         ▼
    ┌───────────────────────────────┐
    │  graph.aupdate_state()        │
    │  {                            │
    │    "todos": [{                │
    │      "task": "New Task"       │
    │    }]                         │
    │  }                            │
    └───────────┬───────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │  merge_todos_smart Reducer    │
    │  (Auto-applied)               │
    │                               │
    │  1. Generate UUID             │
    │  2. Assign step number        │
    │  3. Set created_at            │
    │  4. Set updated_at            │
    │  5. Merge with existing       │
    └───────────┬───────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │  Updated State                │
    │  {                            │
    │    "todos": [                 │
    │      {                        │
    │        "id": "uuid-123",      │
    │        "step": 4,             │
    │        "task": "New Task",    │
    │        "status": "pending",   │
    │        "created_at": "...",   │
    │        "updated_at": "..."    │
    │      },                       │
    │      ...existing todos...     │
    │    ]                          │
    │  }                            │
    └───────────────────────────────┘
```

---

## 2. Agent Flow (에이전트 흐름)

### 2.1 Agent Hierarchy

```
                    ┌──────────────────┐
                    │   Octostrator    │
                    │ (Main Supervisor)│
                    └────────┬─────────┘
                             │
           ┌─────────────────┼─────────────────┬─────────────┐
           │                 │                 │             │
           ▼                 ▼                 ▼             ▼
    ┌────────────┐    ┌──────────┐    ┌──────────┐   ┌──────────┐
    │ Cognitive  │    │   Todo   │    │ Execute  │   │ Response │
    │ Supervisor │    │  Agent   │    │Supervisor│   │  Graph   │
    └────────────┘    └──────────┘    └────┬─────┘   └──────────┘
                                            │
                          ┌─────────────────┼─────────────────┬────────┐
                          │                 │                 │        │
                          ▼                 ▼                 ▼        ▼
                   ┌──────────┐      ┌──────────┐     ┌──────────┐ ┌──────────┐
                   │  Diet    │      │ Workout  │     │  Health  │ │  Report  │
                   │  Agent   │      │  Agent   │     │  Agent   │ │  Agent   │
                   └──────────┘      └──────────┘     └──────────┘ └──────────┘
```

### 2.2 Cognitive Layer Agent Flow

```
    Cognitive Layer Node
            │
            ▼
    ┌─────────────────────────────────────┐
    │  1. Initialize                      │
    │     CognitiveSupervisor             │
    │     - LLM setup                     │
    │     - Checkpointer connection       │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  2. Analyze User Query              │
    │     - Intent understanding          │
    │     - Goal extraction               │
    │     - Context analysis              │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  3. Generate Plan                   │
    │     {                               │
    │       "goal": "Create diet plan",   │
    │       "steps": [                    │
    │         "Analyze profile",          │
    │         "Calculate calories",       │
    │         "Generate meal plan"        │
    │       ]                             │
    │     }                               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  4. Validate Plan                   │
    │     - Check completeness            │
    │     - Validate steps                │
    │     - Set plan_valid = True         │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  5. Decide Todo Manager             │
    │     if len(steps) > 1:              │
    │       plan_requires_todos = True    │
    │     else:                           │
    │       plan_requires_todos = False   │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  6. Record History                  │
    │     action_history ← {              │
    │       "action": "cognitive_node",   │
    │       "result": {"plan": ...},      │
    │       "duration_ms": 250            │
    │     }                               │
    │     plan_history ← {                │
    │       "plan": ...,                  │
    │       "reason": "initial",          │
    │       "modified_by": "system"       │
    │     }                               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  7. Update State                    │
    │     - plan                          │
    │     - plan_valid                    │
    │     - plan_requires_todos           │
    │     - created_at, updated_at        │
    └──────────────┬──────────────────────┘
                   │
                   ▼
          Conditional Edge
```

### 2.3 Todo Layer Agent Flow

```
    Todo Layer Node
            │
            ▼
    ┌─────────────────────────────────────┐
    │  1. Initialize TodoAgent            │
    │     - LLM setup                     │
    │     - Checkpointer connection       │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  2. Get Plan from State             │
    │     plan = {                        │
    │       "goal": "...",                │
    │       "steps": [...]                │
    │     }                               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  3. Convert Plan to Todos           │
    │     For each step:                  │
    │     ┌─────────────────────────────┐ │
    │     │  Analyze requirements       │ │
    │     │  Determine agent            │ │
    │     │  Set priority               │ │
    │     │  Create todo item           │ │
    │     └─────────────────────────────┘ │
    │                                     │
    │     todos = [                       │
    │       {                             │
    │         "task": "Analyze profile",  │
    │         "agent": "HealthAgent",     │
    │         "priority": 1               │
    │       },                            │
    │       {                             │
    │         "task": "Create meal plan", │
    │         "agent": "DietAgent",       │
    │         "priority": 2               │
    │       }                             │
    │     ]                               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  4. HITL Approval (if needed)       │
    │     if not auto_approve:            │
    │       requires_approval = True      │
    │       approval_data = {             │
    │         "todos": todos,             │
    │         "plan_goal": "..."          │
    │       }                             │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  5. Update State                    │
    │     (merge_todos_smart applied)     │
    │     - Generate UUIDs                │
    │     - Assign step numbers           │
    │     - Set timestamps                │
    └──────────────┬──────────────────────┘
                   │
                   ▼
          Execute Layer
```

### 2.4 Execute Layer Agent Flow

```
    Execute Layer Node
            │
            ▼
    ┌─────────────────────────────────────┐
    │  1. Initialize ExecuteSupervisor    │
    │     - Checkpointer connection       │
    │     - Agent registry load           │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  2. Get Todos                       │
    │     Filter: status == "pending"     │
    │     Sort by: step                   │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  3. Execute Each Todo               │
    │                                     │
    │  For todo in todos:                 │
    │    ┌──────────────────────────────┐ │
    │    │ 3.1 Determine Agent          │ │
    │    │     agent_name = todo.agent  │ │
    │    └──────────────────────────────┘ │
    │    ┌──────────────────────────────┐ │
    │    │ 3.2 Execute Agent            │ │
    │    │                              │ │
    │    │  ┌────────────────────────┐  │ │
    │    │  │ if agent == "DietAgent"│  │ │
    │    │  │   - meal_planning      │  │ │
    │    │  │   - calorie_calc       │  │ │
    │    │  │   - nutrition_analysis │  │ │
    │    │  └────────────────────────┘  │ │
    │    │  ┌────────────────────────┐  │ │
    │    │  │if agent=="WorkoutAgent"│  │ │
    │    │  │   - workout_planning   │  │ │
    │    │  │   - exercise_recommend │  │ │
    │    │  └────────────────────────┘  │ │
    │    │  ┌────────────────────────┐  │ │
    │    │  │if agent=="HealthAgent" │  │ │
    │    │  │   - health_check       │  │ │
    │    │  │   - risk_assessment    │  │ │
    │    │  └────────────────────────┘  │ │
    │    │  ┌────────────────────────┐  │ │
    │    │  │if agent=="ReportAgent" │  │ │
    │    │  │   - report_generation  │  │ │
    │    │  │   - data_visualization │  │ │
    │    │  └────────────────────────┘  │ │
    │    └──────────────────────────────┘ │
    │    ┌──────────────────────────────┐ │
    │    │ 3.3 Handle Result            │ │
    │    │   Success:                   │ │
    │    │     - Store result           │ │
    │    │     - Update status:completed│ │
    │    │   Failure:                   │ │
    │    │     - Log error              │ │
    │    │     - Update status: failed  │ │
    │    │     - Store error message    │ │
    │    └──────────────────────────────┘ │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  4. Aggregate Results               │
    │     - Count completed               │
    │     - Count failed                  │
    │     - Calculate success_rate        │
    │     - Compile execution_results     │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  5. Record History                  │
    │     action_history ← {              │
    │       "action": "execute_node",     │
    │       "result": {                   │
    │         "completed": 3,             │
    │         "failed": 0,                │
    │         "success_rate": 1.0         │
    │       }                             │
    │     }                               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
          Response Layer
```

### 2.5 Response Layer Agent Flow

```
    Response Layer Node
            │
            ▼
    ┌─────────────────────────────────────┐
    │  1. Build Response Graph            │
    │     - Chat handler                  │
    │     - Graph handler                 │
    │     - Report handler                │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  2. HITL Final Approval (if needed) │
    │     if requires_approval:           │
    │       Wait for user confirmation    │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  3. Select Output Format            │
    │     output_format = state.format    │
    └──────────────┬──────────────────────┘
                   │
        ┌──────────┼──────────┬──────────┐
        │          │          │          │
        ▼          ▼          ▼          ▼
    ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
    │ Chat │  │Graph │  │Report│  │Custom│
    └───┬──┘  └───┬──┘  └───┬──┘  └───┬──┘
        │         │         │         │
        └─────────┴─────────┴─────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  4. Generate Response               │
    │     - Format execution_results      │
    │     - Include todo status           │
    │     - Add recommendations           │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  5. Record History                  │
    │     action_history ← {              │
    │       "action": "response_node",    │
    │       "result": {                   │
    │         "format": "chat"            │
    │       }                             │
    │     }                               │
    └──────────────┬──────────────────────┘
                   │
                   ▼
                  END
```

### 2.6 Agent Capabilities Matrix

```
┌──────────────────┬───────────────┬───────────────┬───────────────┬───────────────┐
│                  │  DietAgent    │ WorkoutAgent  │ HealthAgent   │ ReportAgent   │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Primary Task     │ 식단 관리      │ 운동 계획      │ 건강 평가      │ 보고서 생성    │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Capability 1     │ meal_planning │ workout_plan  │ health_check  │ report_gen    │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Capability 2     │ calorie_calc  │ exercise_rec  │ risk_assess   │ data_viz      │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Capability 3     │ nutrition_    │ fitness_      │ medical_      │ summary_      │
│                  │   analysis    │   assessment  │   history     │   creation    │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Capability 4     │ allergy_check │ progress_     │ -             │ -             │
│                  │               │   tracking    │               │               │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Input Type       │ User profile, │ Fitness level,│ Medical hist, │ Execution     │
│                  │ Dietary prefs │ Goals         │ Health status │ Results       │
├──────────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ Output Type      │ Meal plan     │ Workout plan  │ Health report │ Final report  │
│                  │ with nutrition│ with exercises│ with risks    │ with viz      │
└──────────────────┴───────────────┴───────────────┴───────────────┴───────────────┘
```

---

## 3. Data Flow (데이터 흐름)

### 3.1 State Evolution Through Layers

```
Initial State (START)
┌─────────────────────────────────┐
│ user_query: "Create diet plan"  │
│ session_id: "session-123"       │
│ output_format: "chat"           │
│ context: {"auto_approve": true} │
└────────────┬────────────────────┘
             │
             ▼
After Cognitive Layer
┌──────────────────────────────────┐
│ + plan: {                        │
│     "goal": "Create diet plan",  │
│     "steps": [...]               │
│   }                              │
│ + plan_valid: true               │
│ + plan_requires_todos: true      │
│ + action_history: [              │
│     {                            │
│       "step": 1,                 │
│       "action": "cognitive",     │
│       "timestamp": "...",        │
│       "duration_ms": 250         │
│     }                            │
│   ]                              │
│ + plan_history: [...]            │
│ + created_at: "2025-11-06..."    │
└────────────┬─────────────────────┘
             │
             ▼
After Todo Layer
┌──────────────────────────────────┐
│ + todos: [                       │
│     {                            │
│       "id": "uuid-1",            │
│       "step": 1,                 │
│       "task": "Analyze profile", │
│       "agent": "HealthAgent",    │
│       "status": "pending",       │
│       "created_at": "...",       │
│       "updated_at": "..."        │
│     },                           │
│     {...}                        │
│   ]                              │
│ + action_history: [              │
│     ...,                         │
│     {                            │
│       "step": 2,                 │
│       "action": "todo",          │
│       "result": {                │
│         "todos_count": 3         │
│       }                          │
│     }                            │
│   ]                              │
└────────────┬─────────────────────┘
             │
             ▼
After Execute Layer
┌──────────────────────────────────┐
│ + execution_results: {           │
│     "task_1": {                  │
│       "status": "completed",     │
│       "result": {...}            │
│     },                           │
│     "task_2": {...}              │
│   }                              │
│ + completed: 3                   │
│ + failed: 0                      │
│ + success_rate: 1.0              │
│ + todos: [                       │
│     {                            │
│       ...,                       │
│       "status": "completed"      │
│     }                            │
│   ]                              │
│ + action_history: [              │
│     ...,                         │
│     {                            │
│       "step": 3,                 │
│       "action": "execute",       │
│       "result": {                │
│         "completed": 3,          │
│         "success_rate": 1.0      │
│       }                          │
│     }                            │
│   ]                              │
└────────────┬─────────────────────┘
             │
             ▼
After Response Layer (END)
┌──────────────────────────────────┐
│ + final_response: "..."          │
│ + response_format: "chat"        │
│ + action_history: [              │
│     ...,                         │
│     {                            │
│       "step": 4,                 │
│       "action": "response",      │
│       "result": {                │
│         "format": "chat"         │
│       }                          │
│     }                            │
│   ]                              │
│ + total_steps: 4                 │
│ + updated_at: "2025-11-06..."    │
└──────────────────────────────────┘
```

### 3.2 User Interaction Data Flow (Phase 2)

```
    User Action (API Call)
            │
            ▼
    ┌───────────────────────────┐
    │  PUT /todos/{id}          │
    │  {"status": "completed"}  │
    └───────────┬───────────────┘
                │
                ▼
    ┌───────────────────────────────────┐
    │  graph.aupdate_state()            │
    │  {"todos": [{"id": "...",         │
    │              "status": "..."}]}   │
    └───────────┬───────────────────────┘
                │
                ▼  (merge_todos_smart)
    ┌───────────────────────────────────┐
    │  State Updated                    │
    │  todos[0].status = "completed"    │
    │  todos[0].updated_at = now()      │
    └───────────┬───────────────────────┘
                │
                ▼
    ┌───────────────────────────────────┐
    │  Record User Interaction          │
    │  graph.aupdate_state()            │
    │  {"user_interactions": [{         │
    │    "type": "modify_todo",         │
    │    "details": {...}               │
    │  }]}                              │
    └───────────┬───────────────────────┘
                │
                ▼  (track_user_interactions)
    ┌───────────────────────────────────┐
    │  State Updated                    │
    │  user_interactions.append({       │
    │    "type": "modify_todo",         │
    │    "timestamp": now(),            │
    │    "details": {...}               │
    │  })                               │
    └───────────────────────────────────┘
```

### 3.3 History Tracking Data Flow

```
    Every Node Execution
            │
            ▼
    ┌─────────────────────────────┐
    │  start_time = now()         │
    └─────────────┬───────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │  Execute Node Logic         │
    └─────────────┬───────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │  end_time = now()           │
    │  duration_ms = (end - start)│
    └─────────────┬───────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────┐
    │  state["action_history"] = [{       │
    │    "action": "node_name",           │
    │    "result": {...},                 │
    │    "duration_ms": duration          │
    │  }]                                 │
    └─────────────┬───────────────────────┘
                  │
                  ▼  (add_with_timestamp_and_step)
    ┌─────────────────────────────────────┐
    │  Auto-added:                        │
    │  - step: 1 (or next step number)    │
    │  - timestamp: "2025-11-06..."       │
    └─────────────────────────────────────┘
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
