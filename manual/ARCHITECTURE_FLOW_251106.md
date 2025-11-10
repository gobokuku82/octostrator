# AI PT Manager - System Architecture Flow

**Version:** 1.0
**Date:** 2025-11-05
**Author:** AI PT Manager Development Team

---

## 📋 Table of Contents

1. [Overall System Architecture](#overall-system-architecture)
2. [Octostrator Main Flow](#octostrator-main-flow)
3. [Layer Details](#layer-details)
4. [API Request Flow](#api-request-flow)
5. [Folder Structure](#folder-structure)

---

## 🏗️ Overall System Architecture

```mermaid
graph TB
    subgraph "API Layer"
        REST[REST API<br/>main.py]
        WS[WebSocket API<br/>websocket.py]
        SESSION[Session API<br/>sessions.py]
    end

    subgraph "Orchestrator"
        OCTO[Octostrator Supervisor<br/>supervisors/octostrator/]
    end

    subgraph "Supervisor Layers"
        COG[Cognitive Layer<br/>Planning & Intent]
        TODO[Todo Layer<br/>Task Management]
        EXEC[Execute Layer<br/>Agent Execution]
        RESP[Response Layer<br/>Output Generation]
    end

    subgraph "Agents"
        DIET[DietAgent]
        MORE[Other Agents<br/>Future]
    end

    subgraph "Infrastructure"
        STATE[States<br/>Central State Mgmt]
        TOOLS[Tools<br/>Shared Utilities]
        CHECKPOINT[Checkpointer<br/>PostgreSQL]
    end

    REST --> OCTO
    WS --> OCTO
    SESSION --> OCTO

    OCTO --> COG
    COG -.->|conditional| TODO
    COG --> EXEC
    TODO --> EXEC
    EXEC --> RESP

    EXEC -.-> DIET
    DIET -.-> EXEC
    EXEC -.-> MORE
    MORE -.-> EXEC

    COG --> STATE
    TODO --> STATE
    EXEC --> STATE
    RESP --> STATE

    OCTO --> CHECKPOINT
    STATE --> CHECKPOINT
```

---

## 🔄 Octostrator Main Flow

**핵심 변경**: Todo Manager는 **필요시에만** 조건부로 실행됩니다.

```mermaid
graph TB
    START([User Request]) --> OCTO[Octostrator Supervisor]

    OCTO --> L1[Cognitive Layer<br/>cognitive_layer_node]

    L1 --> COND{Todo Manager<br/>필요?}

    COND -->|YES<br/>plan_requires_todos=True| L2[Todo Layer<br/>todo_layer_node]
    COND -->|NO<br/>기본 경로| L3[Execute Layer<br/>execute_layer_node]

    L2 --> L3

    L3 --> L4[Response Layer<br/>response_layer_node]

    L4 --> END([Final Response])

    style OCTO fill:#e1f5ff
    style L1 fill:#fff3e0
    style COND fill:#ffeb3b
    style L2 fill:#e8f5e9
    style L3 fill:#f3e5f5
    style L4 fill:#fce4ec
```

### Todo Manager 호출 조건

Todo Manager는 다음 경우에만 실행됩니다:

1. **Cognitive Layer 요청**: `plan_requires_todos = True`
   - 복잡한 계획 → Todo 분할 필요
2. **Execute Layer 요청**: `need_todo_update = True`
   - 실행 중 추가 작업 발견
3. **사용자 API 요청**: `user_requested_todo_update = True`
   - 사용자가 직접 Todo 수정

### 중요 특징

- ✅ `state["todos"]`는 항상 존재 (초기값: `[]`)
- ✅ Todo Manager 노드 실행은 **선택적**
- ✅ 사용자는 API로 언제든 todos 수정 가능

### Octostrator Components

```
supervisors/octostrator/
├── octostrator_graph.py      # Main workflow graph
├── octostrator_nodes.py       # Layer execution nodes
├── octostrator_helpers.py     # OctostratorSupervisor class
└── __init__.py
```

---

## 📊 Layer Details

### Layer 1: Cognitive Layer

**Location:** `supervisors/cognitive/`

```mermaid
graph LR
    START([User Query]) --> INTENT[Intent Understanding<br/>intent_understanding_node]

    INTENT --> PLAN[Planning<br/>planning_node]

    PLAN --> VALID[Validation<br/>validator_node]

    VALID --> END([Plan Output])

    style INTENT fill:#fff3e0
    style PLAN fill:#fff3e0
    style VALID fill:#fff3e0
```

**Purpose:**
- Understand user intent
- Generate execution plan
- Validate plan feasibility

**State:** `CognitiveState`
```python
{
    "user_query": str,
    "user_intent": str,
    "plan": dict,
    "plan_valid": bool
}
```

---

### Layer 2: Todo Layer

**Location:** `supervisors/todo/`

```mermaid
graph LR
    START([Plan]) --> CONVERT[Plan to Todos<br/>TodoAgent]

    CONVERT --> HITL{HITL<br/>Required?}

    HITL -->|No| BATCH[Create Batches]
    HITL -->|Yes| WAIT[Wait Approval]

    WAIT --> BATCH
    BATCH --> END([Todo List])

    style CONVERT fill:#e8f5e9
    style HITL fill:#fff9c4
    style BATCH fill:#e8f5e9
```

**Purpose:**
- Convert plan to actionable todos
- Handle Human-in-the-Loop (HITL) approval
- Organize todos into execution batches

**State:** `TodoAgentState`
```python
{
    "plan": dict,
    "todos": list,
    "current_batch": dict,
    "requires_approval": bool
}
```

---

### Layer 3: Execute Layer

**Location:** `supervisors/execute/`

```mermaid
graph TB
    START([Todo List]) --> EXECUTOR[Executor Node<br/>executor_node]

    EXECUTOR --> RESOLVE[Resolve Dependencies<br/>DependencyResolver]

    RESOLVE --> AGENTS{Route to<br/>Agents}

    AGENTS -->|diet| DIET[DietAgent]
    AGENTS -->|workout| WORKOUT[WorkoutAgent]
    AGENTS -->|more| MORE[Other Agents]

    DIET --> AGG[Aggregator<br/>aggregator_node]
    WORKOUT --> AGG
    MORE --> AGG

    AGG --> ERROR{Errors?}

    ERROR -->|Yes| HANDLER[Error Handler<br/>error_handler_node]
    ERROR -->|No| END([Results])

    HANDLER --> END

    style EXECUTOR fill:#f3e5f5
    style AGENTS fill:#fff9c4
    style AGG fill:#f3e5f5
    style ERROR fill:#fff9c4
```

**Purpose:**
- Execute todos through specialized agents
- Resolve dependencies between tasks
- Aggregate results
- Handle errors

**State:** `ExecuteState`
```python
{
    "todos": list,
    "execution_tasks": list,
    "execution_results": dict,
    "completed": int,
    "failed": int,
    "success_rate": float
}
```

---

### Layer 4: Response Layer

**Location:** `supervisors/response/`

```mermaid
graph LR
    START([Execution Results]) --> HITL[HITL Handler<br/>hitl_handler_node]

    HITL --> ROUTER[Output Router<br/>output_router_node]

    ROUTER --> FORMAT{Output<br/>Format?}

    FORMAT -->|chat| CHAT[Chat Generator<br/>chat_generator_node]
    FORMAT -->|graph| GRAPH[Graph Generator<br/>graph_generator_node]
    FORMAT -->|report| REPORT[Report Generator<br/>report_generator_node]

    CHAT --> END([Final Response])
    GRAPH --> END
    REPORT --> END

    style HITL fill:#fce4ec
    style ROUTER fill:#fce4ec
    style FORMAT fill:#fff9c4
    style CHAT fill:#fce4ec
    style GRAPH fill:#fce4ec
    style REPORT fill:#fce4ec
```

**Purpose:**
- Handle final HITL approval
- Route to appropriate output format
- Generate formatted response

**State:** `ResponseState`
```python
{
    "execution_results": dict,
    "output_format": str,  # "chat" | "graph" | "report"
    "final_response": str,
    "requires_approval": bool
}
```

---

## 🌐 API Request Flow

### REST API Flow

```mermaid
sequenceDiagram
    participant Client
    participant REST as main.py
    participant Octo as Octostrator
    participant Layers as 4 Layers
    participant State as State Store

    Client->>REST: POST /chat
    REST->>Octo: ainvoke(initial_state)

    Octo->>Layers: Execute Layer 1 (Cognitive)
    Layers->>State: Save cognitive state

    Octo->>Layers: Execute Layer 2 (Todo)
    Layers->>State: Save todo state

    Octo->>Layers: Execute Layer 3 (Execute)
    Layers->>State: Save execution state

    Octo->>Layers: Execute Layer 4 (Response)
    Layers->>State: Save response state

    Layers-->>Octo: final_state
    Octo-->>REST: result
    REST-->>Client: ChatResponse
```

### WebSocket API Flow

```mermaid
sequenceDiagram
    participant Client
    participant WS as websocket.py
    participant Octo as Octostrator Graph
    participant Layers as 4 Layers

    Client->>WS: Connect /ws/chat/{session_id}
    WS-->>Client: connected

    Client->>WS: {"message": "..."}
    WS->>Octo: astream_events(initial_input)

    loop For each layer
        Octo->>Layers: Execute layer node
        Layers-->>WS: node_started event
        WS-->>Client: node_started

        Layers-->>WS: node_completed event
        WS-->>Client: node_completed

        alt Layer specific updates
            WS-->>Client: plan_update (Layer 1)
            WS-->>Client: todos_update (Layer 2)
            WS-->>Client: execution_update (Layer 3)
        end
    end

    Octo-->>WS: final_state
    WS-->>Client: final_result
    WS-->>Client: execution_completed
```

### Session Management Flow

```mermaid
sequenceDiagram
    participant Client
    participant Session as sessions.py
    participant Octo as Octostrator Graph
    participant Checkpoint as PostgreSQL

    Client->>Session: GET /api/sessions/{thread_id}
    Session->>Octo: aget_state(config)
    Octo->>Checkpoint: Load state
    Checkpoint-->>Octo: state
    Octo-->>Session: state
    Session-->>Client: SessionStateResponse

    Note over Client,Session: HITL Resume Flow

    Client->>Session: POST /api/sessions/{thread_id}/resume
    Session->>Octo: ainvoke(None/Command, config)
    Octo->>Checkpoint: Load from checkpoint
    Checkpoint-->>Octo: previous state
    Octo->>Octo: Resume execution
    Octo-->>Session: result
    Session-->>Client: ResumeResponse
```

---

## 📁 Folder Structure

```
backend/app/octostrator/
│
├── supervisors/
│   ├── octostrator/              # Main Orchestrator
│   │   ├── octostrator_graph.py
│   │   ├── octostrator_nodes.py
│   │   ├── octostrator_helpers.py
│   │   └── __init__.py
│   │
│   ├── cognitive/                # Layer 1: Planning
│   │   ├── cognitive_graph.py
│   │   ├── cognitive_nodes.py
│   │   ├── cognitive_helpers.py
│   │   ├── cognitive_prompts.py
│   │   └── __init__.py
│   │
│   ├── todo/                     # Layer 2: Task Management
│   │   ├── todo_manager.py
│   │   └── __init__.py
│   │
│   ├── execute/                  # Layer 3: Execution
│   │   ├── execute_graph.py
│   │   ├── execute_nodes.py
│   │   ├── execute_helpers.py
│   │   ├── execute_prompts.py
│   │   └── __init__.py
│   │
│   └── response/                 # Layer 4: Output
│       ├── response_graph.py
│       ├── response_nodes.py
│       ├── response_helpers.py
│       ├── response_prompts.py
│       └── __init__.py
│
├── agents/                       # Domain Agents
│   ├── base/
│   │   ├── base_agent.py
│   │   ├── agent_registry.py
│   │   └── capabilities.py
│   ├── diet/
│   │   └── diet_agent.py
│   └── [other agents...]
│
├── states/                       # Central State Management
│   ├── cognitive_state.py
│   ├── todo_state.py
│   ├── execute_state.py
│   ├── response_state.py
│   ├── diet_state.py
│   └── __init__.py
│
├── tools/                        # Shared Tools
│   └── [tool implementations...]
│
├── checkpointer.py               # PostgreSQL Checkpointer
├── session.py                    # Session Management
└── test_octostrator.py           # Tests
```

---

## 🔑 Key Design Principles

### 1. **Separation of Concerns**
- Each layer has a specific responsibility
- Supervisors orchestrate, agents execute
- States are centrally managed

### 2. **Sequential Flow**
```
Cognitive → Todo → Execute → Response
```
- Each layer depends on the previous layer's output
- Clear data flow through state updates

### 3. **Modularity**
- Each supervisor is self-contained
- Can be tested independently
- Easy to add new agents or layers

### 4. **Checkpointing & Resume**
- Every state change is checkpointed
- Can resume from any point
- Supports HITL (Human-in-the-Loop)

### 5. **Consistent Naming**
- All files prefixed with folder name
- Example: `cognitive_graph.py`, `cognitive_nodes.py`
- Easy to identify which layer a file belongs to

---

## 📝 State Flow Example

### Complete Request Flow

```mermaid
stateDiagram-v2
    [*] --> UserRequest

    UserRequest --> CognitiveLayer
    state CognitiveLayer {
        [*] --> IntentUnderstanding
        IntentUnderstanding --> Planning
        Planning --> Validation
        Validation --> [*]
    }

    CognitiveLayer --> TodoLayer
    state TodoLayer {
        [*] --> PlanConversion
        PlanConversion --> HITLCheck
        HITLCheck --> TodoBatching
        TodoBatching --> [*]
    }

    TodoLayer --> ExecuteLayer
    state ExecuteLayer {
        [*] --> DependencyResolution
        DependencyResolution --> AgentExecution
        AgentExecution --> ResultAggregation
        ResultAggregation --> ErrorHandling
        ErrorHandling --> [*]
    }

    ExecuteLayer --> ResponseLayer
    state ResponseLayer {
        [*] --> HITLHandler
        HITLHandler --> OutputRouting
        OutputRouting --> ResponseGeneration
        ResponseGeneration --> [*]
    }

    ResponseLayer --> [*]
```

### State Transitions

| Layer | Input State | Output State |
|-------|-------------|--------------|
| **Cognitive** | `user_query` | `plan`, `user_intent` |
| **Todo** | `plan` | `todos`, `current_batch` |
| **Execute** | `todos` | `execution_results`, `completed`, `failed` |
| **Response** | `execution_results` | `final_response` |

---

## 🚀 Execution Example

### Simple Request

```python
# User Request
request = {
    "message": "오늘 점심 식단 추천해줘"
}

# Octostrator processes through all layers
result = await octostrator_graph.ainvoke({
    "user_query": "오늘 점심 식단 추천해줘",
    "session_id": "user123",
    "output_format": "chat",
    # ... other initial state
})

# Layer 1: Cognitive
# → Intent: diet_recommendation
# → Plan: { goal: "점심 식단 추천", steps: [...] }

# Layer 2: Todo
# → Todos: [
#     { agent: "diet", task: "점심 메뉴 생성" },
#     { agent: "diet", task: "영양 정보 계산" }
#   ]

# Layer 3: Execute
# → DietAgent 실행
# → Results: { menu: "...", nutrition: "..." }

# Layer 4: Response
# → Format: chat
# → Final Response: "오늘 점심으로 ..."
```

---

## 📌 Summary

### Architecture Highlights

1. **4-Layer Sequential Architecture**
   - Clear separation of responsibilities
   - Predictable data flow
   - Easy to debug and test

2. **Main Orchestrator (Octostrator)**
   - Single entry point for all requests
   - Coordinates all 4 layers
   - Manages state transitions

3. **Centralized State Management**
   - All states in `states/` folder
   - Checkpointed in PostgreSQL
   - Supports resume and HITL

4. **Modular Agent System**
   - Agents are called by Execute Layer
   - Easy to add new agents
   - Registry-based discovery

5. **Multiple API Interfaces**
   - REST API for simple requests
   - WebSocket for real-time streaming
   - Session API for state management

---

**Last Updated:** 2025-11-05
**Version:** 1.0
**Maintainer:** AI PT Manager Development Team
