-- Initialize Octostrator Database Schema
-- This script creates all necessary tables for the application

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables (for development)
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoints CASCADE;
DROP TABLE IF EXISTS streaming_events CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS execution_logs CASCADE;
DROP TABLE IF EXISTS performance_metrics CASCADE;
DROP TABLE IF EXISTS short_term_memory CASCADE;
DROP TABLE IF EXISTS interrupts CASCADE;
DROP TABLE IF EXISTS agent_executions CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS todo_history CASCADE;
DROP TABLE IF EXISTS todo_dependencies CASCADE;
DROP TABLE IF EXISTS todos CASCADE;
DROP TABLE IF EXISTS conversation_context CASCADE;
DROP TABLE IF EXISTS conversation_intents CASCADE;
DROP TABLE IF EXISTS threads CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    preferences JSONB
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_user_active ON sessions(user_id, is_active);

-- Threads table
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    parent_thread_id VARCHAR(255),
    graph_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_threads_thread_id ON threads(thread_id);
CREATE INDEX idx_threads_session_id ON threads(session_id);
CREATE INDEX idx_threads_parent ON threads(parent_thread_id);

-- TODOs table
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    parent_todo_id UUID REFERENCES todos(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(10) DEFAULT 'medium',
    assigned_agent VARCHAR(100),
    estimated_time_minutes INTEGER,
    actual_time_minutes INTEGER,
    order_index INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_todos_thread_id ON todos(thread_id);
CREATE INDEX idx_todos_parent ON todos(parent_todo_id);
CREATE INDEX idx_todos_status ON todos(status);
CREATE INDEX idx_todos_thread_status ON todos(thread_id, status);
CREATE INDEX idx_todos_thread_order ON todos(thread_id, order_index);

-- TODO Dependencies table
CREATE TABLE todo_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    todo_id UUID REFERENCES todos(id) ON DELETE CASCADE NOT NULL,
    depends_on_todo_id UUID REFERENCES todos(id) ON DELETE CASCADE NOT NULL,
    dependency_type VARCHAR(20) DEFAULT 'blocks',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_todo_deps_todo ON todo_dependencies(todo_id);
CREATE INDEX idx_todo_deps_depends ON todo_dependencies(depends_on_todo_id);
CREATE UNIQUE INDEX idx_todo_deps_unique ON todo_dependencies(todo_id, depends_on_todo_id);

-- Conversation Intents table
CREATE TABLE conversation_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    intent_type VARCHAR(50) NOT NULL,
    intent_subtype VARCHAR(50),
    confidence FLOAT NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    raw_input TEXT,
    parsed_intent JSONB,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_intents_thread ON conversation_intents(thread_id);
CREATE INDEX idx_intents_type ON conversation_intents(intent_type);
CREATE INDEX idx_intents_thread_active ON conversation_intents(thread_id, is_active);

-- Conversation Context table
CREATE TABLE conversation_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    context_key VARCHAR(100) NOT NULL,
    context_value JSONB NOT NULL,
    context_type VARCHAR(50),
    ttl_seconds INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_context_thread ON conversation_context(thread_id);
CREATE INDEX idx_context_key ON conversation_context(context_key);
CREATE INDEX idx_context_thread_type ON conversation_context(thread_id, context_type);

-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(100) UNIQUE NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    executor_subtype VARCHAR(50),
    capabilities JSONB,
    configuration JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX idx_agents_name ON agents(agent_name);
CREATE INDEX idx_agents_type ON agents(agent_type);

-- Agent Executions table
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE NOT NULL,
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    todo_id UUID REFERENCES todos(id),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    execution_time_ms INTEGER
);

CREATE INDEX idx_exec_agent ON agent_executions(agent_id);
CREATE INDEX idx_exec_thread ON agent_executions(thread_id);
CREATE INDEX idx_exec_todo ON agent_executions(todo_id);
CREATE INDEX idx_exec_status ON agent_executions(status);

-- Interrupts table
CREATE TABLE interrupts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    interrupt_type VARCHAR(50) NOT NULL,
    interrupt_reason TEXT,
    interrupt_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution_type VARCHAR(50),
    resolution_data JSONB
);

CREATE INDEX idx_interrupts_thread ON interrupts(thread_id);
CREATE INDEX idx_interrupts_type ON interrupts(interrupt_type);
CREATE INDEX idx_interrupts_created ON interrupts(created_at);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT,
    content_blocks JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_thread ON messages(thread_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_role ON messages(role);

-- LangGraph Checkpoints table
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id VARCHAR(255) NOT NULL,
    parent_checkpoint_id VARCHAR(255),
    checkpoint_data BYTEA NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_checkpoints_thread ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_checkpoint ON checkpoints(checkpoint_id);
CREATE UNIQUE INDEX idx_checkpoints_unique ON checkpoints(thread_id, checkpoint_id);

-- Checkpoint Writes table
CREATE TABLE checkpoint_writes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checkpoint_id UUID REFERENCES checkpoints(id) ON DELETE CASCADE NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    channel VARCHAR(255) NOT NULL,
    value JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_writes_checkpoint ON checkpoint_writes(checkpoint_id);
CREATE INDEX idx_writes_task ON checkpoint_writes(task_id);

-- Insert default agents
INSERT INTO agents (agent_name, agent_type, executor_subtype, capabilities, configuration) VALUES
('planner_agent', 'planner', NULL, '{"can_create_todos": true}', '{}'),
('router_agent', 'router', NULL, '{"can_route_tasks": true}', '{}'),
('validator_agent', 'validator', NULL, '{"can_validate": true}', '{}'),
('search_executor', 'executor', 'search', '{"search_types": ["web", "docs", "code"]}', '{}'),
('analysis_executor', 'executor', 'analysis', '{"analysis_types": ["statistical", "semantic"]}', '{}'),
('document_executor', 'executor', 'document', '{"document_types": ["report", "summary"]}', '{}'),
('api_executor', 'executor', 'api', '{"api_types": ["rest", "graphql"]}', '{}');

-- Create test user
INSERT INTO users (email, username, preferences) VALUES
('test@octostrator.com', 'testuser', '{"theme": "dark", "language": "ko"}');