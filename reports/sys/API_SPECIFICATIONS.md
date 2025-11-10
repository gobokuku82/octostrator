# API 명세서 (API Specifications)

**작성일**: 2025-11-06
**목적**: 전체 시스템의 API 엔드포인트 명세
**버전**: 0.5.0
**Base URL**: http://localhost:8000

---

## 📑 목차 (Table of Contents)

1. [개요 (Overview)](#개요-overview)
2. [인증 (Authentication)](#인증-authentication)
3. [공통 응답 형식](#공통-응답-형식)
4. [WebSocket API](#websocket-api)
5. [REST API](#rest-api)
6. [에러 코드](#에러-코드)
7. [사용 예시](#사용-예시)

---

## 개요 (Overview)

### API 아키텍처

AI PT Manager는 다음 API를 제공합니다:

```
APIs
├── WebSocket API              # 실시간 스트리밍 (Phase 4.3)
│   └── /ws/chat/{session_id}  # 채팅 + 실시간 업데이트
│
└── REST API
    ├── Health & Info
    │   ├── GET  /              # Root endpoint
    │   └── GET  /health        # Health check
    │
    ├── Chat
    │   └── POST /chat          # 일반 채팅 (비스트리밍)
    │
    ├── Session Management (Phase 4.4)
    │   ├── POST /sessions      # 세션 생성
    │   ├── GET  /sessions/{id} # 세션 조회
    │   └── GET  /sessions/{id}/history  # 세션 히스토리
    │
    ├── Todo Management (Phase 2)
    │   ├── GET  /todos         # Todo 목록
    │   ├── POST /todos         # Todo 생성
    │   └── PUT  /todos/{id}    # Todo 업데이트
    │
    └── Agent Management (Phase 2)
        ├── GET  /agents        # Agent 목록
        └── GET  /agents/{id}   # Agent 상세
```

### 기술 스택

- **Framework**: FastAPI
- **WebSocket**: fastapi.WebSocket
- **실시간 스트리밍**: LangGraph astream_events v2
- **Checkpoint**: AsyncPostgresSaver (PostgreSQL)
- **CORS**: 모든 origin 허용 (개발 환경)

---

## 인증 (Authentication)

**현재 상태**: 인증 없음 (개발 환경)

**Phase 3 UserTier 시스템**:
- WebSocket 메시지의 `user_id` 필드로 사용자 등급 식별
- `premium_*` → PREMIUM (gpt-4o, 높은 토큰)
- `trial_*` → TRIAL (gpt-4o-mini, 낮은 토큰)
- 기타 → STANDARD (균형)

**Future**: JWT 기반 인증 예정 (Phase 5)

---

## 공통 응답 형식

### 성공 응답

```json
{
  "status": "success",
  "data": { ... }
}
```

### 에러 응답

```json
{
  "status": "error",
  "detail": "Error message"
}
```

### WebSocket 이벤트 형식

```json
{
  "type": "event_type",
  "data": { ... },
  "session_id": "session_xxx"
}
```

---

## WebSocket API

### `/ws/chat/{session_id}`

실시간 채팅 및 스트리밍 엔드포인트 (Phase 4.3)

#### Connection

**URL**: `ws://localhost:8000/ws/chat/{session_id}`

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `session_id` | string | ✅ | 세션 ID (고유) |

**Connection Flow**:
1. 클라이언트 → 서버: WebSocket 연결 요청
2. 서버 → 클라이언트: `connected` 이벤트
3. 양방향 메시지 송수신
4. 연결 종료

#### Client → Server Message Format

클라이언트가 서버로 전송하는 메시지 형식:

```json
{
  "message": "사용자 질의 내용",
  "output_format": "chat",
  "debug": false,
  "trace_id": "optional_trace_id",
  "user_id": "premium_user123"
}
```

**필드 명세**:

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `message` | string | ✅ | - | 사용자 질의 |
| `output_format` | string | ❌ | "chat" | 출력 형식: "chat", "report", "graph" |
| `debug` | boolean | ❌ | false | 디버그 모드 (Phase 3) |
| `trace_id` | string | ❌ | (auto) | 분산 추적 ID (Phase 3) |
| `user_id` | string | ❌ | `user_{session_id}` | 사용자 ID (Phase 3, Tier 추출용) |

**user_id 예시**:
- `"premium_user123"` → UserTier.PREMIUM (gpt-4o)
- `"trial_user456"` → UserTier.TRIAL (gpt-4o-mini, 낮은 토큰)
- `"regular_user789"` → UserTier.STANDARD (균형)

#### Server → Client Events

서버가 클라이언트로 전송하는 이벤트:

##### 1. `connected`
연결 성공 이벤트

```json
{
  "type": "connected",
  "data": {
    "message": "WebSocket 연결 성공"
  },
  "session_id": "session_001"
}
```

##### 2. `execution_started`
그래프 실행 시작

```json
{
  "type": "execution_started",
  "data": {
    "message": "처리 중..."
  },
  "session_id": "session_001"
}
```

##### 3. `node_started`
노드 실행 시작 (Cognitive, Todo, Execute, Response)

```json
{
  "type": "node_started",
  "data": {
    "node": "cognitive",
    "run_id": "uuid"
  },
  "session_id": "session_001"
}
```

##### 4. `node_completed`
노드 실행 완료

```json
{
  "type": "node_completed",
  "data": {
    "node": "cognitive",
    "run_id": "uuid"
  },
  "session_id": "session_001"
}
```

##### 5. `plan_update`
Cognitive Layer 완료 후 계획 업데이트

```json
{
  "type": "plan_update",
  "data": {
    "plan": {
      "goal": "회원 프로그램 설계",
      "steps": [...]
    },
    "plan_valid": true
  },
  "session_id": "session_001"
}
```

##### 6. `todos_update`
Todo Layer 완료 후 Todo 목록 업데이트

```json
{
  "type": "todos_update",
  "data": {
    "todos": [
      {
        "id": "todo_1",
        "title": "회원 평가",
        "status": "pending"
      }
    ],
    "total_todos": 3
  },
  "session_id": "session_001"
}
```

##### 7. `execution_update`
Execute Layer 완료 후 실행 결과 업데이트

```json
{
  "type": "execution_update",
  "data": {
    "completed": 2,
    "failed": 0,
    "success_rate": 100
  },
  "session_id": "session_001"
}
```

##### 8. `final_result`
최종 응답

```json
{
  "type": "final_result",
  "data": {
    "result": "최종 응답 내용...",
    "completed": 3,
    "total_todos": 3,
    "success_rate": 100
  },
  "session_id": "session_001"
}
```

##### 9. `execution_completed`
실행 완료

```json
{
  "type": "execution_completed",
  "data": {
    "message": "처리 완료"
  },
  "session_id": "session_001"
}
```

##### 10. `error`
에러 발생

```json
{
  "type": "error",
  "data": {
    "error": "Error message",
    "message": "처리 중 오류가 발생했습니다"
  },
  "session_id": "session_001"
}
```

#### Event Flow Diagram

```
Client                           Server
  |                                 |
  |--- WebSocket Connect ---------->|
  |<-- connected -------------------|
  |                                 |
  |--- {message: "..."} ----------->|
  |<-- execution_started -----------|
  |<-- node_started (cognitive) ----|
  |<-- node_completed (cognitive) --|
  |<-- plan_update -----------------|
  |<-- node_started (todo) ---------|
  |<-- node_completed (todo) -------|
  |<-- todos_update -----------------|
  |<-- node_started (execute) ------|
  |<-- node_completed (execute) ----|
  |<-- execution_update ------------|
  |<-- node_started (response) -----|
  |<-- node_completed (response) ---|
  |<-- final_result -----------------|
  |<-- execution_completed ----------|
  |                                 |
  |--- {message: "..."} ----------->| (다음 질의)
  |                                 |
```

#### Example

**JavaScript (Browser)**:

```javascript
const sessionId = "session_" + Date.now();
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`);

// 이벤트 핸들러
ws.onopen = () => {
  console.log("WebSocket Connected");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Event:", data.type, data.data);

  switch(data.type) {
    case "connected":
      console.log("✅ 연결 성공");
      break;

    case "plan_update":
      console.log("📋 계획:", data.data.plan);
      break;

    case "todos_update":
      console.log("✓ Todos:", data.data.todos);
      break;

    case "final_result":
      console.log("💬 응답:", data.data.result);
      break;

    case "error":
      console.error("❌ 에러:", data.data.error);
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket Error:", error);
};

ws.onclose = () => {
  console.log("WebSocket Disconnected");
};

// 메시지 전송
function sendMessage(message) {
  ws.send(JSON.stringify({
    message: message,
    output_format: "chat",
    debug: true,
    user_id: "premium_user123"  // Premium 사용자
  }));
}

// 사용
sendMessage("회원 홍길동의 운동 프로그램 설계해줘");
```

**Python**:

```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:8000/ws/chat/session_001"

    async with websockets.connect(uri) as websocket:
        # 연결 이벤트 수신
        response = await websocket.recv()
        print(f"연결: {json.loads(response)}")

        # 메시지 전송
        await websocket.send(json.dumps({
            "message": "안녕하세요",
            "output_format": "chat",
            "debug": True,
            "user_id": "premium_user123"
        }))

        # 이벤트 수신
        while True:
            try:
                response = await websocket.recv()
                event = json.loads(response)
                print(f"이벤트: {event['type']} - {event['data']}")

                if event['type'] == 'execution_completed':
                    break

            except websockets.exceptions.ConnectionClosed:
                print("연결 종료")
                break

asyncio.run(chat())
```

---

## REST API

### Health & Info

#### `GET /`

Root 엔드포인트 (API 정보)

**Request**: None

**Response**:
```json
{
  "message": "LangGraph Chatbot API",
  "version": "0.5.0",
  "status": "running"
}
```

**Status Code**: 200

---

#### `GET /health`

Health check 엔드포인트

**Request**: None

**Response**:
```json
{
  "status": "healthy"
}
```

**Status Code**: 200

---

### Chat

#### `POST /chat`

일반 채팅 엔드포인트 (비스트리밍)

**Request Body**:
```json
{
  "message": "사용자 질의"
}
```

**Response**:
```json
{
  "response": "AI 응답 내용"
}
```

**Status Codes**:
- `200`: 성공
- `500`: 서버 에러

**Example**:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요"
  }'
```

**Response**:
```json
{
  "response": "안녕하세요! 무엇을 도와드릴까요?"
}
```

**Note**: WebSocket API 사용 권장 (실시간 업데이트)

---

### Session Management (Phase 4.4)

#### `POST /sessions`

새 세션 생성

**Request Body**:
```json
{
  "user_id": "premium_user123"
}
```

**Response**:
```json
{
  "session_id": "session_abc123",
  "user_id": "premium_user123",
  "created_at": "2025-11-06T10:00:00Z"
}
```

---

#### `GET /sessions/{session_id}`

세션 정보 조회

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `session_id` | string | ✅ | 세션 ID |

**Response**:
```json
{
  "session_id": "session_abc123",
  "user_id": "premium_user123",
  "created_at": "2025-11-06T10:00:00Z",
  "last_activity": "2025-11-06T10:30:00Z"
}
```

---

#### `GET /sessions/{session_id}/history`

세션 히스토리 조회

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `session_id` | string | ✅ | 세션 ID |

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `limit` | int | ❌ | 10 | 최대 항목 수 |

**Response**:
```json
{
  "session_id": "session_abc123",
  "history": [
    {
      "timestamp": "2025-11-06T10:00:00Z",
      "user_query": "안녕하세요",
      "response": "안녕하세요! ..."
    },
    {
      "timestamp": "2025-11-06T10:05:00Z",
      "user_query": "회원 프로그램 설계",
      "response": "프로그램 설계를 시작하겠습니다..."
    }
  ],
  "total": 2
}
```

---

### Todo Management (Phase 2)

#### `GET /todos`

Todo 목록 조회

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `session_id` | string | ❌ | - | 특정 세션의 Todo만 |
| `status` | string | ❌ | - | 상태 필터: pending, completed, failed |

**Response**:
```json
{
  "todos": [
    {
      "id": "todo_1",
      "title": "회원 초기 평가",
      "description": "인바디 측정 및 자세 분석",
      "status": "completed",
      "agent_id": "assessor_agent",
      "created_at": "2025-11-06T10:00:00Z",
      "updated_at": "2025-11-06T10:05:00Z"
    }
  ],
  "total": 1
}
```

---

#### `POST /todos`

Todo 생성

**Request Body**:
```json
{
  "title": "새 Todo",
  "description": "설명",
  "agent_id": "assessor_agent",
  "session_id": "session_001"
}
```

**Response**:
```json
{
  "id": "todo_new",
  "title": "새 Todo",
  "description": "설명",
  "status": "pending",
  "agent_id": "assessor_agent",
  "created_at": "2025-11-06T10:00:00Z"
}
```

---

#### `PUT /todos/{todo_id}`

Todo 업데이트

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `todo_id` | string | ✅ | Todo ID |

**Request Body**:
```json
{
  "status": "completed",
  "result": "완료 결과"
}
```

**Response**:
```json
{
  "id": "todo_1",
  "title": "회원 초기 평가",
  "status": "completed",
  "result": "완료 결과",
  "updated_at": "2025-11-06T10:10:00Z"
}
```

---

### Agent Management (Phase 2)

#### `GET /agents`

Agent 목록 조회

**Response**:
```json
{
  "agents": [
    {
      "agent_id": "frontdesk_agent",
      "agent_name": "AI Frontdesk Agent",
      "description": "신규 회원 응대 및 리드 관리",
      "capabilities": ["lead_management", "appointment_scheduling"],
      "status": "active"
    },
    {
      "agent_id": "assessor_agent",
      "agent_name": "AI Assessor Agent",
      "description": "회원 초기 평가 및 자세 분석",
      "capabilities": ["inbody_analysis", "posture_evaluation"],
      "status": "active"
    }
  ],
  "total": 7
}
```

---

#### `GET /agents/{agent_id}`

Agent 상세 조회

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `agent_id` | string | ✅ | Agent ID |

**Response**:
```json
{
  "agent_id": "frontdesk_agent",
  "agent_name": "AI Frontdesk Agent",
  "description": "신규 회원 응대 및 리드 관리",
  "capabilities": [
    "lead_management",
    "appointment_scheduling",
    "lead_scoring"
  ],
  "supported_channels": ["web", "phone", "sns"],
  "status": "active",
  "version": "1.0.0"
}
```

---

## 에러 코드

### HTTP Status Codes

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 |
| 404 | Not Found | 리소스 없음 |
| 500 | Internal Server Error | 서버 에러 |

### WebSocket Close Codes

| 코드 | 의미 | 설명 |
|------|------|------|
| 1000 | Normal Closure | 정상 종료 |
| 1001 | Going Away | 클라이언트 떠남 |
| 1006 | Abnormal Closure | 비정상 종료 |

### Application Error Codes

WebSocket `error` 이벤트의 `data.error` 필드:

| 에러 메시지 | 원인 | 해결 |
|-------------|------|------|
| "Message field is required" | message 필드 누락 | 메시지에 message 필드 포함 |
| "Error processing chat: ..." | 그래프 실행 에러 | 서버 로그 확인 |
| "Type is not msgpack serializable" | State 직렬화 실패 | State 정의 확인 (Phase 3 원칙) |

---

## 사용 예시

### Example 1: 기본 채팅

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/session_001');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "안녕하세요"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'final_result') {
    console.log("응답:", data.data.result);
  }
};
```

### Example 2: Premium 사용자 (Phase 3)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/premium_session_001');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "회원 평가 및 프로그램 설계",
    user_id: "premium_user123",  // gpt-4o 사용
    debug: true  // 상세 로깅
  }));
};
```

### Example 3: 실시간 진행 상황 표시

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/session_001');
let progress = {};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'node_started':
      console.log(`🔄 ${data.data.node} 시작`);
      break;

    case 'plan_update':
      console.log("📋 계획 생성됨");
      progress.plan = data.data.plan;
      break;

    case 'todos_update':
      console.log(`✓ Todo 생성: ${data.data.total_todos}개`);
      progress.todos = data.data.todos;
      break;

    case 'execution_update':
      console.log(`⚙️ 실행 중: ${data.data.completed}/${data.data.total_todos}`);
      break;

    case 'final_result':
      console.log("✅ 완료:", data.data.result);
      break;
  }
};
```

---

## 부록

### CORS 설정

현재 개발 환경에서는 모든 origin 허용:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production**: 특정 도메인만 허용하도록 변경 필요

### Rate Limiting

**현재 상태**: 없음

**Future**: API Gateway 또는 Redis 기반 Rate Limiting 추가 예정

---

**작성자**: Claude Code Agent
**검토자**: -
**버전**: 1.0
**마지막 업데이트**: 2025-11-06
**관련 문서**:
- [MASTER_CHECKLIST.md](MASTER_CHECKLIST.md)
- [SCHEMA_SPECIFICATIONS.md](SCHEMA_SPECIFICATIONS.md)
- [FEATURE_SPECIFICATIONS.md](FEATURE_SPECIFICATIONS.md)
