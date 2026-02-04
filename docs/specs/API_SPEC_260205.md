# API Specification
**Version**: 2.0 | **Date**: 2026-02-05 | **Status**: Draft

## 1. Overview

기업용 에이전트 시스템의 REST API 및 WebSocket 명세입니다.

### 1.1 Base URL

```
Production: https://api.octostrator.com/v2
Development: http://localhost:8000/api
```

### 1.2 Authentication (To Be Implemented)

```
Authorization: Bearer <jwt_token>
X-API-Key: <api_key>
```

---

## 2. Agent Endpoints

### 2.1 Run Agent (Synchronous)

동기 방식으로 에이전트를 실행하고 완료까지 대기합니다.

```
POST /api/agent/run
```

**Request:**
```json
{
  "user_input": "라네즈 리뷰 분석해서 인사이트 뽑아줘",
  "language": "KOR",
  "session_id": "optional_session_id",
  "options": {
    "skip_plan_review": false,
    "auto_approve": false,
    "max_execution_time": 300
  }
}
```

**Response (200 OK):**
```json
{
  "session_id": "sess_abc123",
  "status": "completed",
  "response": "라네즈 리뷰 분석 결과입니다...",
  "todos": [
    {
      "id": "todo_001",
      "title": "데이터 수집",
      "status": "completed",
      "tool_name": "data_collector",
      "completed_at": "2026-02-05T10:05:00Z"
    },
    {
      "id": "todo_002",
      "title": "감성 분석",
      "status": "completed",
      "tool_name": "sentiment_analyzer",
      "completed_at": "2026-02-05T10:07:00Z"
    }
  ],
  "plan_id": "plan_xyz789",
  "execution_time_ms": 45000,
  "report_path": "/reports/sess_abc123/trend_report.json"
}
```

**Error Response (4xx/5xx):**
```json
{
  "error": {
    "code": "EXECUTION_FAILED",
    "message": "Todo execution failed",
    "details": {
      "todo_id": "todo_002",
      "error": "API rate limit exceeded"által
    }
  },
  "session_id": "sess_abc123"
}
```

### 2.2 Run Agent (Asynchronous)

비동기 방식으로 에이전트를 실행하고 즉시 반환합니다. 진행상황은 WebSocket으로 수신합니다.

```
POST /api/agent/run-async
```

**Request:**
```json
{
  "user_input": "라네즈 리뷰 분석해서 인사이트 뽑아줘",
  "language": "KOR",
  "session_id": "optional_session_id",
  "options": {
    "skip_plan_review": false,
    "auto_approve": false
  }
}
```

**Response (202 Accepted):**
```json
{
  "session_id": "sess_abc123",
  "status": "running",
  "websocket_url": "ws://localhost:8000/ws/sess_abc123",
  "message": "Agent started. Connect to WebSocket for updates."
}
```

### 2.3 Get Agent Status

에이전트 실행 상태를 조회합니다.

```
GET /api/agent/status/{session_id}
```

**Response (200 OK):**
```json
{
  "session_id": "sess_abc123",
  "status": "executing",
  "progress": {
    "total_todos": 5,
    "completed_todos": 2,
    "current_todo": {
      "id": "todo_003",
      "title": "키워드 분석",
      "progress_percentage": 45
    }
  },
  "hitl_mode": "running",
  "started_at": "2026-02-05T10:00:00Z",
  "estimated_completion": "2026-02-05T10:10:00Z"
}
```

### 2.4 Stop Agent

실행 중인 에이전트를 중지합니다.

```
POST /api/agent/stop/{session_id}
```

**Request:**
```json
{
  "reason": "User requested cancellation"
}
```

**Response (200 OK):**
```json
{
  "message": "Agent stopped",
  "session_id": "sess_abc123",
  "stopped_at": "2026-02-05T10:05:30Z",
  "completed_todos": ["todo_001", "todo_002"],
  "cancelled_todos": ["todo_003", "todo_004", "todo_005"]
}
```

---

## 3. Plan Endpoints

### 3.1 Get Plan

플랜 정보를 조회합니다.

```
GET /api/plan/{plan_id}
```

**Response (200 OK):**
```json
{
  "id": "plan_xyz789",
  "session_id": "sess_abc123",
  "status": "executing",
  "current_version": 2,
  "todos": [...],
  "execution_graph": {
    "nodes": {...},
    "groups": [...],
    "critical_path": ["todo_001", "todo_002", "todo_003"]
  },
  "statistics": {
    "total": 5,
    "pending": 2,
    "in_progress": 1,
    "completed": 2,
    "failed": 0
  },
  "created_at": "2026-02-05T10:00:00Z",
  "updated_at": "2026-02-05T10:05:00Z"
}
```

### 3.2 Approve Plan

플랜을 승인합니다.

```
POST /api/plan/{plan_id}/approve
```

**Request:**
```json
{
  "approved_by": "user_123",
  "comment": "Looks good, proceed."
}
```

**Response (200 OK):**
```json
{
  "message": "Plan approved",
  "plan_id": "plan_xyz789",
  "new_status": "approved",
  "execution_will_start": true
}
```

### 3.3 Edit Plan

플랜을 수정합니다.

```
PATCH /api/plan/{plan_id}
```

**Request:**
```json
{
  "edits": [
    {
      "edit_type": "add_todo",
      "params": {
        "title": "경쟁사 분석",
        "tool_name": "competitor_analyzer",
        "layer": "ml",
        "insert_after": "todo_002"
      }
    },
    {
      "edit_type": "remove_todo",
      "target_id": "todo_005"
    },
    {
      "edit_type": "change_priority",
      "target_id": "todo_003",
      "params": {
        "priority": 9
      }
    }
  ],
  "edited_by": "user_123",
  "reason": "Added competitor analysis, removed unnecessary step"
}
```

**Response (200 OK):**
```json
{
  "message": "Plan updated",
  "plan_id": "plan_xyz789",
  "new_version": 3,
  "updated_todos": [...],
  "changes_applied": [
    "Added todo: 경쟁사 분석",
    "Removed todo: todo_005",
    "Changed priority of todo_003 to 9"
  ]
}
```

### 3.4 Edit Plan with Natural Language

자연어로 플랜을 수정합니다.

```
POST /api/plan/{plan_id}/nl-edit
```

**Request:**
```json
{
  "instruction": "리뷰 수집 다음에 경쟁사 분석도 추가해주고, 영상 생성은 빼줘",
  "edited_by": "user_123"
}
```

**Response (200 OK):**
```json
{
  "message": "Plan updated via natural language",
  "plan_id": "plan_xyz789",
  "new_version": 3,
  "interpreted_edits": [
    {
      "edit_type": "add_todo",
      "description": "경쟁사 분석 Todo를 '리뷰 수집' 다음에 추가"
    },
    {
      "edit_type": "remove_todo",
      "description": "영상 생성 Todo 제거"
    }
  ],
  "updated_todos": [...]
}
```

### 3.5 Get Plan History

플랜 변경 이력을 조회합니다.

```
GET /api/plan/{plan_id}/history
```

**Response (200 OK):**
```json
{
  "plan_id": "plan_xyz789",
  "versions": [
    {
      "version": 1,
      "change_type": "create",
      "changed_by": "system",
      "created_at": "2026-02-05T10:00:00Z",
      "todo_count": 5
    },
    {
      "version": 2,
      "change_type": "user_edit",
      "changed_by": "user_123",
      "created_at": "2026-02-05T10:02:00Z",
      "change_reason": "Added competitor analysis",
      "todo_count": 6
    }
  ]
}
```

---

## 4. Todo Endpoints

### 4.1 Get Todo

개별 Todo를 조회합니다.

```
GET /api/todo/{todo_id}
```

**Response (200 OK):**
```json
{
  "id": "todo_001",
  "plan_id": "plan_xyz789",
  "title": "데이터 수집",
  "description": "올리브영에서 라네즈 리뷰 수집",
  "status": "completed",
  "priority": 10,
  "layer": "data",
  "tool_name": "data_collector",
  "tool_params": {
    "brand": "라네즈",
    "platform": "oliveyoung",
    "limit": 1000
  },
  "depends_on": [],
  "blocks": ["todo_002", "todo_003"],
  "progress_percentage": 100,
  "result_data": {
    "collected_count": 987,
    "platforms": ["oliveyoung"],
    "date_range": "2025-11-05 ~ 2026-02-05"
  },
  "started_at": "2026-02-05T10:01:00Z",
  "completed_at": "2026-02-05T10:03:00Z"
}
```

### 4.2 Update Todo

Todo를 수정합니다.

```
PATCH /api/todo/{todo_id}
```

**Request:**
```json
{
  "title": "데이터 수집 (확장)",
  "priority": 10,
  "tool_params": {
    "brand": "라네즈",
    "platform": ["oliveyoung", "coupang"],
    "limit": 2000
  }
}
```

**Response (200 OK):**
```json
{
  "message": "Todo updated",
  "todo": {...}
}
```

### 4.3 Approve Todo

승인 대기 중인 Todo를 승인합니다.

```
POST /api/todo/{todo_id}/approve
```

**Request:**
```json
{
  "approved_by": "user_123",
  "comment": "Approved for execution"
}
```

**Response (200 OK):**
```json
{
  "message": "Todo approved",
  "todo_id": "todo_003",
  "new_status": "pending"
}
```

### 4.4 Reject Todo

승인 대기 중인 Todo를 거부합니다.

```
POST /api/todo/{todo_id}/reject
```

**Request:**
```json
{
  "rejected_by": "user_123",
  "reason": "Not needed for this analysis"
}
```

**Response (200 OK):**
```json
{
  "message": "Todo rejected",
  "todo_id": "todo_003",
  "new_status": "cancelled"
}
```

### 4.5 Retry Todo

실패한 Todo를 재시도합니다.

```
POST /api/todo/{todo_id}/retry
```

**Response (200 OK):**
```json
{
  "message": "Todo queued for retry",
  "todo_id": "todo_003",
  "new_status": "pending",
  "retry_count": 2
}
```

---

## 5. HITL Endpoints

### 5.1 Pause Execution

실행을 일시정지합니다.

```
POST /api/hitl/{session_id}/pause
```

**Request:**
```json
{
  "reason": "Need to review intermediate results"
}
```

**Response (200 OK):**
```json
{
  "message": "Execution paused",
  "session_id": "sess_abc123",
  "hitl_mode": "paused",
  "current_todo": "todo_003"
}
```

### 5.2 Resume Execution

실행을 재개합니다.

```
POST /api/hitl/{session_id}/resume
```

**Response (200 OK):**
```json
{
  "message": "Execution resumed",
  "session_id": "sess_abc123",
  "hitl_mode": "running"
}
```

### 5.3 Submit Input

요청된 입력을 제출합니다.

```
POST /api/hitl/{session_id}/input
```

**Request:**
```json
{
  "request_id": "input_req_001",
  "value": "2024년 1분기"
}
```

**Response (200 OK):**
```json
{
  "message": "Input received",
  "session_id": "sess_abc123",
  "hitl_mode": "running"
}
```

### 5.4 Get Pending Actions

대기 중인 HITL 액션을 조회합니다.

```
GET /api/hitl/{session_id}/pending
```

**Response (200 OK):**
```json
{
  "session_id": "sess_abc123",
  "pending_actions": [
    {
      "type": "approval_request",
      "todo_id": "todo_005",
      "message": "영상 생성을 시작하려면 승인이 필요합니다.",
      "timeout_at": "2026-02-05T11:00:00Z"
    }
  ]
}
```

---

## 6. WebSocket API

### 6.1 Connection

```
WS /ws/{session_id}
```

### 6.2 Server → Client Messages

#### Todo Update
```json
{
  "type": "todo_update",
  "session_id": "sess_abc123",
  "todo": {
    "id": "todo_002",
    "title": "감성 분석",
    "status": "in_progress",
    "progress_percentage": 45
  },
  "timestamp": "2026-02-05T10:05:30Z"
}
```

#### Todo Completed
```json
{
  "type": "todo_completed",
  "session_id": "sess_abc123",
  "todo": {
    "id": "todo_002",
    "title": "감성 분석",
    "status": "completed",
    "result_summary": {
      "positive": 65,
      "negative": 20,
      "neutral": 15
    }
  },
  "timestamp": "2026-02-05T10:06:00Z"
}
```

#### Plan Review Request
```json
{
  "type": "hitl_plan_review",
  "session_id": "sess_abc123",
  "plan_id": "plan_xyz789",
  "plan": {
    "todos": [...],
    "estimated_time_seconds": 300,
    "estimated_cost": 0.05
  },
  "message": "실행 계획을 검토해주세요.",
  "timestamp": "2026-02-05T10:00:30Z"
}
```

#### Approval Request
```json
{
  "type": "hitl_approval_request",
  "session_id": "sess_abc123",
  "todo_id": "todo_005",
  "todo": {...},
  "message": "영상 생성을 시작하려면 승인이 필요합니다.",
  "timeout_at": "2026-02-05T11:00:00Z",
  "timestamp": "2026-02-05T10:08:00Z"
}
```

#### Input Request
```json
{
  "type": "hitl_input_request",
  "session_id": "sess_abc123",
  "request_id": "input_req_001",
  "question": "분석할 기간을 지정해주세요.",
  "input_type": "choice",
  "options": ["최근 1개월", "최근 3개월", "최근 6개월", "직접 입력"],
  "required": true,
  "timestamp": "2026-02-05T10:02:00Z"
}
```

#### Execution Complete
```json
{
  "type": "complete",
  "session_id": "sess_abc123",
  "response": "라네즈 리뷰 분석 결과입니다...",
  "statistics": {
    "total_todos": 5,
    "completed": 5,
    "execution_time_ms": 45000
  },
  "report_path": "/reports/sess_abc123/trend_report.json",
  "timestamp": "2026-02-05T10:10:00Z"
}
```

#### Error
```json
{
  "type": "error",
  "session_id": "sess_abc123",
  "error": {
    "code": "TODO_EXECUTION_FAILED",
    "message": "감성 분석 실행 중 오류가 발생했습니다.",
    "todo_id": "todo_002",
    "recoverable": true
  },
  "timestamp": "2026-02-05T10:05:00Z"
}
```

### 6.3 Client → Server Messages

#### Plan Response
```json
{
  "type": "hitl_plan_response",
  "session_id": "sess_abc123",
  "plan_id": "plan_xyz789",
  "action": "approve"
}
```

#### Approval Response
```json
{
  "type": "hitl_approval_response",
  "session_id": "sess_abc123",
  "todo_id": "todo_005",
  "action": "approve",
  "comment": "승인합니다"
}
```

#### Input Response
```json
{
  "type": "hitl_input_response",
  "session_id": "sess_abc123",
  "request_id": "input_req_001",
  "value": "최근 3개월"
}
```

#### Control Command
```json
{
  "type": "hitl_control",
  "session_id": "sess_abc123",
  "command": "pause",
  "reason": "결과 확인 필요"
}
```

---

## 7. Health & Info Endpoints

### 7.1 Health Check

```
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 86400,
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm_provider": "connected"
  }
}
```

### 7.2 Available Tools

```
GET /api/tools
```

**Response (200 OK):**
```json
{
  "tools": [
    {
      "name": "data_collector",
      "display_name": "데이터 수집기",
      "type": "data",
      "layer": "data",
      "description": "다양한 플랫폼에서 리뷰 데이터를 수집합니다."
    },
    {
      "name": "sentiment_analyzer",
      "display_name": "감성 분석기",
      "type": "analysis",
      "layer": "ml",
      "description": "텍스트의 감성을 분석합니다."
    }
  ],
  "total": 15
}
```

---

## 8. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | 잘못된 입력 |
| `SESSION_NOT_FOUND` | 404 | 세션을 찾을 수 없음 |
| `PLAN_NOT_FOUND` | 404 | 플랜을 찾을 수 없음 |
| `TODO_NOT_FOUND` | 404 | Todo를 찾을 수 없음 |
| `EXECUTION_FAILED` | 500 | 실행 실패 |
| `TODO_EXECUTION_FAILED` | 500 | Todo 실행 실패 |
| `TIMEOUT` | 504 | 타임아웃 |
| `LLM_ERROR` | 502 | LLM 서비스 오류 |
| `UNAUTHORIZED` | 401 | 인증 필요 |
| `FORBIDDEN` | 403 | 권한 없음 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 한도 초과 |

---

## 9. Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/api/agent/run` | 10 req/min |
| `/api/agent/run-async` | 20 req/min |
| `/api/plan/*` | 60 req/min |
| `/api/todo/*` | 60 req/min |
| `/api/hitl/*` | 120 req/min |
| WebSocket | 100 msg/min |

---

## Related Documents
- [ARCHITECTURE_260205.md](ARCHITECTURE_260205.md) - System architecture
- [TODO_SYSTEM_260205.md](TODO_SYSTEM_260205.md) - Todo & HITL system
- [DATA_MODELS_260205.md](DATA_MODELS_260205.md) - Data models
