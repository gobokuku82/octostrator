# Database Schema Specification
**Version**: 2.0 | **Date**: 2026-02-05 | **Status**: Draft

## 1. Overview

기업용 에이전트 시스템의 데이터베이스 스키마 정의서입니다. PostgreSQL을 기본 RDBMS로 사용하며, LangGraph 체크포인트 및 비즈니스 데이터를 관리합니다.

## 2. Database Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL (Primary)                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  LangGraph       │  │   Business       │  │   Analytics   │  │
│  │  Checkpoint      │  │   Data           │  │   Data        │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        Redis (Cache)                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  Session Cache   │  │  Execution Cache │  │  Rate Limit   │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Vector DB (FAISS/Chroma)                     │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  Document Store  │  │   Embeddings     │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Core Tables

### 3.1 Sessions Table

세션 관리를 위한 테이블입니다.

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    language VARCHAR(10) DEFAULT 'KOR',

    -- Context
    initial_input TEXT,
    current_context JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('active', 'completed', 'expired', 'error'))
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
```

### 3.2 Plans Table

플랜 관리 테이블입니다.

```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    current_version INTEGER DEFAULT 1,

    -- Intent (Cognitive Layer Output)
    intent JSONB,

    -- Metadata
    total_todos INTEGER DEFAULT 0,
    completed_todos INTEGER DEFAULT 0,
    failed_todos INTEGER DEFAULT 0,

    -- Cost Estimation
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    estimated_duration_seconds INTEGER,
    actual_duration_seconds INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_plan_status CHECK (status IN (
        'draft', 'approved', 'executing', 'paused',
        'waiting', 'completed', 'failed', 'cancelled'
    ))
);

CREATE INDEX idx_plans_session_id ON plans(session_id);
CREATE INDEX idx_plans_status ON plans(status);
```

### 3.3 Plan Versions Table

플랜 버전 히스토리 테이블입니다.

```sql
CREATE TABLE plan_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,

    -- Snapshot
    todos_snapshot JSONB NOT NULL,  -- 해당 버전의 전체 Todo 목록

    -- Change Info
    change_type VARCHAR(20) NOT NULL,
    change_reason TEXT,
    changed_by VARCHAR(50),  -- 'user' | 'system' | user_id

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_change_type CHECK (change_type IN (
        'create', 'replan', 'user_edit', 'auto_adjust'
    )),
    UNIQUE (plan_id, version)
);

CREATE INDEX idx_plan_versions_plan_id ON plan_versions(plan_id);
```

### 3.4 Todos Table

Todo 아이템 테이블입니다.

```sql
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,

    -- Basic Info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 0 AND 10),

    -- Layer & Tool
    layer VARCHAR(50) NOT NULL,  -- 'ml', 'biz', 'data', etc.
    tool_name VARCHAR(100),
    tool_params JSONB DEFAULT '{}',

    -- Dependencies
    depends_on UUID[] DEFAULT '{}',  -- 의존하는 Todo ID들
    blocks UUID[] DEFAULT '{}',       -- 이 Todo가 블로킹하는 ID들

    -- Execution Config
    timeout_seconds INTEGER DEFAULT 300,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,

    -- Progress
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
    error_message TEXT,

    -- Approval
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Data
    input_data JSONB,
    output_path TEXT,
    result_data JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Order
    execution_order INTEGER,

    CONSTRAINT valid_todo_status CHECK (status IN (
        'pending', 'in_progress', 'completed', 'failed',
        'blocked', 'skipped', 'needs_approval', 'cancelled'
    ))
);

CREATE INDEX idx_todos_plan_id ON todos(plan_id);
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_layer ON todos(layer);
CREATE INDEX idx_todos_execution_order ON todos(plan_id, execution_order);
```

### 3.5 Execution Results Table

실행 결과 저장 테이블입니다.

```sql
CREATE TABLE execution_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    todo_id UUID NOT NULL REFERENCES todos(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Result
    success BOOLEAN NOT NULL,
    result_data JSONB,
    error_message TEXT,
    error_stack TEXT,

    -- Timing
    execution_time_ms INTEGER NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Tool Info
    tool_name VARCHAR(100),
    tool_version VARCHAR(20),

    -- Resource Usage
    tokens_used INTEGER,
    api_calls_count INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_execution_results_todo_id ON execution_results(todo_id);
CREATE INDEX idx_execution_results_plan_id ON execution_results(plan_id);
CREATE INDEX idx_execution_results_session_id ON execution_results(session_id);
CREATE INDEX idx_execution_results_success ON execution_results(success);
```

### 3.6 HITL Events Table

Human-in-the-Loop 이벤트 로깅 테이블입니다.

```sql
CREATE TABLE hitl_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES plans(id) ON DELETE SET NULL,
    todo_id UUID REFERENCES todos(id) ON DELETE SET NULL,

    -- Event Info
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',

    -- User Interaction
    user_id UUID REFERENCES users(id),
    user_input TEXT,
    user_decision VARCHAR(50),

    -- Timing
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    timeout_at TIMESTAMP WITH TIME ZONE,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',

    CONSTRAINT valid_event_type CHECK (event_type IN (
        'plan_review', 'approval_request', 'input_request',
        'pause', 'resume', 'cancel', 'edit', 'replan'
    )),
    CONSTRAINT valid_event_status CHECK (status IN (
        'pending', 'completed', 'timeout', 'cancelled'
    ))
);

CREATE INDEX idx_hitl_events_session_id ON hitl_events(session_id);
CREATE INDEX idx_hitl_events_event_type ON hitl_events(event_type);
CREATE INDEX idx_hitl_events_status ON hitl_events(status);
```

## 4. Tool Management Tables

### 4.1 Tools Registry Table

도구 정의 테이블입니다.

```sql
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,

    -- Classification
    type VARCHAR(20) NOT NULL,
    layer VARCHAR(50) NOT NULL,

    -- Schema
    parameters_schema JSONB NOT NULL DEFAULT '[]',
    output_schema JSONB,

    -- Execution
    executor_class VARCHAR(255) NOT NULL,
    timeout_seconds INTEGER DEFAULT 300,

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    version VARCHAR(20) DEFAULT '1.0.0',
    dependencies TEXT[] DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_tool_type CHECK (type IN ('data', 'analysis', 'content', 'business'))
);

CREATE INDEX idx_tools_name ON tools(name);
CREATE INDEX idx_tools_type ON tools(type);
CREATE INDEX idx_tools_layer ON tools(layer);
CREATE INDEX idx_tools_is_active ON tools(is_active);
```

### 4.2 Tool Executions Log Table

도구 실행 로그 테이블입니다.

```sql
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES tools(id),
    tool_name VARCHAR(100) NOT NULL,
    session_id UUID REFERENCES sessions(id),
    todo_id UUID REFERENCES todos(id),

    -- Input/Output
    input_params JSONB,
    output_data JSONB,

    -- Status
    success BOOLEAN NOT NULL,
    error_message TEXT,

    -- Timing
    execution_time_ms INTEGER,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Resource
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tool_executions_tool_id ON tool_executions(tool_id);
CREATE INDEX idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX idx_tool_executions_created_at ON tool_executions(created_at);
```

## 5. User Management Tables

### 5.1 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),

    -- Authentication
    password_hash VARCHAR(255),
    api_key_hash VARCHAR(255) UNIQUE,

    -- Organization
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(50) DEFAULT 'user',

    -- Settings
    preferences JSONB DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'KOR',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_role CHECK (role IN ('admin', 'manager', 'user', 'viewer'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization_id ON users(organization_id);
```

### 5.2 Organizations Table

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE,

    -- Settings
    settings JSONB DEFAULT '{}',

    -- Limits
    max_users INTEGER DEFAULT 10,
    max_daily_requests INTEGER DEFAULT 1000,
    max_monthly_tokens INTEGER DEFAULT 1000000,

    -- Usage
    current_month_tokens INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 6. Analytics Tables

### 6.1 Usage Metrics Table

```sql
CREATE TABLE usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    session_id UUID REFERENCES sessions(id),

    -- Metrics
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(15, 4),
    metric_data JSONB,

    -- Period
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_metric_type CHECK (metric_type IN (
        'token_usage', 'api_calls', 'execution_time',
        'plan_count', 'todo_count', 'success_rate'
    ))
);

CREATE INDEX idx_usage_metrics_org_id ON usage_metrics(organization_id);
CREATE INDEX idx_usage_metrics_user_id ON usage_metrics(user_id);
CREATE INDEX idx_usage_metrics_recorded_at ON usage_metrics(recorded_at);
CREATE INDEX idx_usage_metrics_type ON usage_metrics(metric_type);
```

### 6.2 Feedback Table

```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    plan_id UUID REFERENCES plans(id),
    user_id UUID REFERENCES users(id),

    -- Feedback
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type VARCHAR(50),
    comment TEXT,

    -- Context
    context_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_feedback_session_id ON feedback(session_id);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
```

## 7. LangGraph Checkpoint Tables

LangGraph에서 자동 생성하는 체크포인트 테이블입니다.

```sql
-- langgraph-checkpoint-postgres에서 자동 생성
-- Reference: https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-postgres

CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',

    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,

    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,

    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

## 8. Redis Cache Structures

### 8.1 Session Cache

```
Key: session:{session_id}
Type: Hash
Fields:
  - user_id: string
  - status: string
  - language: string
  - current_context: JSON string
  - created_at: timestamp
TTL: 24 hours
```

### 8.2 Execution Cache

```
Key: exec_cache:{tool_name}:{input_hash}
Type: String (JSON)
Value: ExecutionResult JSON
TTL: 1 hour (configurable per tool)
```

### 8.3 Rate Limit

```
Key: rate_limit:{user_id}:{minute}
Type: Integer (counter)
TTL: 60 seconds
```

## 9. Indexes & Performance

### 9.1 Composite Indexes

```sql
-- 자주 사용되는 쿼리 패턴을 위한 복합 인덱스
CREATE INDEX idx_todos_plan_status ON todos(plan_id, status);
CREATE INDEX idx_todos_plan_layer ON todos(plan_id, layer);
CREATE INDEX idx_execution_results_plan_success ON execution_results(plan_id, success);
CREATE INDEX idx_hitl_events_session_status ON hitl_events(session_id, status);
```

### 9.2 Partial Indexes

```sql
-- 활성 세션만 조회하는 경우
CREATE INDEX idx_sessions_active ON sessions(user_id, created_at)
    WHERE status = 'active';

-- 실행 대기 중인 Todo만 조회하는 경우
CREATE INDEX idx_todos_pending ON todos(plan_id, execution_order)
    WHERE status = 'pending';
```

## 10. Migration Strategy

### 10.1 Alembic Configuration

```python
# alembic/env.py
from app.core.config import settings
from sqlalchemy import engine_from_config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

### 10.2 Migration Commands

```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add new table"

# 마이그레이션 실행
alembic upgrade head

# 롤백
alembic downgrade -1
```

---

## Related Documents
- [DATA_MODELS_260205.md](DATA_MODELS_260205.md) - Pydantic models
- [ARCHITECTURE_260205.md](ARCHITECTURE_260205.md) - System architecture
