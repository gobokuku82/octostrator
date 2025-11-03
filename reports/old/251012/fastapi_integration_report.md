# FastAPI Integration Report

## 📋 Overview

**작성일**: 2025-10-08
**목적**: main.py와 service_agent 연결을 위한 FastAPI REST API 구현
**상태**: ✅ 완료 (테스트 대기)

---

## 🎯 구현 목표

1. **완전 비동기 아키텍처**: 높은 동시성 처리 능력
2. **서버 기반 세션 관리**: UUID 기반 세션 ID 서버 생성
3. **상세 응답 포맷**: 개발 단계에서 디버깅을 위한 상세 정보 포함 (추후 프로덕션용으로 간소화 예정)
4. **체크포인트 통합**: 기존 AsyncSqliteSaver와 완벽 연동
5. **에러 처리**: 중앙집중식 에러 핸들링

---

## 📁 생성된 파일 구조

```
backend/app/api/
├── __init__.py                 # 패키지 초기화
├── schemas.py                  # Pydantic 모델 정의
├── converters.py              # State → Response 변환
├── session_manager.py         # 세션 관리
├── chat_api.py               # API 라우터 (엔드포인트)
└── error_handlers.py         # 에러 핸들러
```

---

## 🔧 주요 컴포넌트

### 1. **schemas.py** - API 스키마 정의

#### Request Models
```python
# 세션 시작 요청
class SessionStartRequest(BaseModel):
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# 채팅 요청
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., description="세션 ID (필수)")
    enable_checkpointing: bool = Field(default=True)
    user_context: Optional[Dict[str, Any]] = Field(default={})
```

#### Response Models
```python
# 채팅 응답 (상세 버전 - Option B)
class ChatResponse(BaseModel):
    # 기본 정보
    session_id: str
    request_id: str
    status: str
    response: Dict[str, Any]  # final_response

    # 상세 정보 (개발용)
    planning_info: Optional[Dict[str, Any]] = None
    team_results: Optional[Dict[str, Any]] = None
    search_results: Optional[List[Dict]] = None
    analysis_metrics: Optional[Dict[str, Any]] = None

    # 메타데이터
    execution_time_ms: Optional[int] = None
    teams_executed: List[str] = []
    error: Optional[str] = None
```

#### Utility Models
- `SessionStartResponse`: 세션 생성 응답
- `SessionInfo`: 세션 정보 조회
- `DeleteSessionResponse`: 세션 삭제 응답
- `SessionStats`: 세션 통계

---

### 2. **converters.py** - State 변환 로직

```python
def state_to_chat_response(
    state: MainSupervisorState,
    execution_time_ms: int
) -> ChatResponse:
    """MainSupervisorState를 ChatResponse로 변환"""

    # 1. Planning 정보 추출
    planning_info = {
        "query_analysis": state.get("planning_state", {}).get("query_analysis"),
        "execution_steps": state.get("planning_state", {}).get("execution_steps"),
        "plan_status": state.get("planning_state", {}).get("status")
    }

    # 2. Team 실행 결과 추출
    team_results = {
        "search_team": state.get("search_team_state"),
        "document_team": state.get("document_team_state"),
        "analysis_team": state.get("analysis_team_state")
    }

    # 3. 검색 결과 추출
    search_results = state.get("search_team_state", {}).get("search_results", [])

    # 4. 분석 메트릭 추출
    analysis_metrics = state.get("analysis_team_state", {}).get("metrics")

    # 5. 실행된 팀 목록
    teams_executed = [
        team for team in ["search_team", "document_team", "analysis_team"]
        if state.get(f"{team}_state") is not None
    ]

    return ChatResponse(...)
```

**핵심 기능**:
- TypedDict (MainSupervisorState) → Pydantic (ChatResponse) 변환
- 중첩된 state 구조에서 필요한 정보만 추출
- 에러 상태 처리 및 fallback 응답

---

### 3. **session_manager.py** - 세션 관리

```python
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}  # 메모리 기반 (추후 Redis/DynamoDB)
        self.session_ttl = timedelta(hours=24)

    def create_session(self, user_id=None, metadata=None) -> Tuple[str, datetime]:
        """서버에서 UUID 기반 세션 ID 생성"""
        session_id = f"session-{uuid.uuid4()}"
        expires_at = datetime.now() + self.session_ttl

        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "expires_at": expires_at,
            "metadata": metadata or {}
        }

        return session_id, expires_at

    def validate_session(self, session_id: str) -> bool:
        """세션 유효성 검증 (만료 시간, 존재 여부)"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        if datetime.now() > session["expires_at"]:
            del self.sessions[session_id]
            return False

        session["last_activity"] = datetime.now()
        return True
```

**특징**:
- 서버 생성 UUID (보안 강화)
- 24시간 TTL
- 자동 만료 세션 정리
- 프로덕션에서는 Redis/DynamoDB로 교체 예정

---

### 4. **chat_api.py** - API 엔드포인트

```python
@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """새 세션 시작"""
    session_id, expires_at = session_manager.create_session(
        user_id=request.user_id,
        metadata=request.metadata
    )
    return SessionStartResponse(
        session_id=session_id,
        message="세션이 생성되었습니다",
        expires_at=expires_at
    )

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """채팅 메시지 처리 (메인 엔드포인트)"""

    # 1. 세션 검증
    if not session_manager.validate_session(request.session_id):
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # 2. Supervisor 인스턴스 생성
    supervisor = TeamBasedSupervisor()

    try:
        # 3. 쿼리 처리
        start_time = time.time()
        result_state = await supervisor.process_query(
            user_query=request.query,
            thread_id=request.session_id,
            enable_checkpointing=request.enable_checkpointing,
            user_context=request.user_context
        )
        execution_time_ms = int((time.time() - start_time) * 1000)

        # 4. State → Response 변환
        response = state_to_chat_response(result_state, execution_time_ms)
        response.session_id = request.session_id
        response.request_id = f"req-{uuid.uuid4()}"

        return response

    finally:
        # 5. Supervisor 정리 (백그라운드)
        background_tasks.add_task(supervisor.cleanup)
```

**처리 흐름**:
1. 세션 유효성 검증
2. TeamBasedSupervisor 인스턴스 생성
3. `process_query()` 실행 (LangGraph 실행)
4. State를 ChatResponse로 변환
5. 백그라운드에서 Supervisor 정리

---

### 5. **error_handlers.py** - 에러 처리

```python
async def validation_exception_handler(request, exc: RequestValidationError):
    """Pydantic 검증 에러 처리"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "body": exc.body
        }
    )

async def general_exception_handler(request, exc: Exception):
    """일반 예외 처리"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )

def register_error_handlers(app):
    """모든 에러 핸들러 등록"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(KeyError, key_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
```

---

## 🔌 main.py 연동

```python
# Import and include routers
from app.api.chat_api import router as chat_router
from app.api.error_handlers import register_error_handlers

# Include routers
app.include_router(chat_router)

# Register error handlers
register_error_handlers(app)
```

---

## 🌐 API 엔드포인트

### 1. **POST /api/v1/chat/start** - 세션 시작
```json
// Request
{
  "user_id": "user123",
  "metadata": {"device": "web"}
}

// Response
{
  "session_id": "session-a1b2c3d4-...",
  "message": "세션이 생성되었습니다",
  "expires_at": "2025-10-09T12:00:00"
}
```

### 2. **POST /api/v1/chat/** - 채팅 메시지
```json
// Request
{
  "query": "부동산 거래 시 주의사항은?",
  "session_id": "session-a1b2c3d4-...",
  "enable_checkpointing": true,
  "user_context": {}
}

// Response (상세 버전)
{
  "session_id": "session-a1b2c3d4-...",
  "request_id": "req-x7y8z9...",
  "status": "success",
  "response": {
    "answer": "부동산 거래 시 주의사항은...",
    "confidence": 0.95
  },
  "planning_info": {
    "query_analysis": {...},
    "execution_steps": [...],
    "plan_status": "completed"
  },
  "team_results": {
    "search_team": {...},
    "analysis_team": {...}
  },
  "search_results": [...],
  "analysis_metrics": {...},
  "execution_time_ms": 2456,
  "teams_executed": ["search_team", "analysis_team"]
}
```

### 3. **GET /api/v1/chat/{session_id}** - 세션 정보 조회
```json
{
  "session_id": "session-a1b2c3d4-...",
  "user_id": "user123",
  "created_at": "2025-10-08T12:00:00",
  "last_activity": "2025-10-08T14:30:00",
  "expires_at": "2025-10-09T12:00:00",
  "is_active": true,
  "metadata": {"device": "web"}
}
```

### 4. **DELETE /api/v1/chat/{session_id}** - 세션 삭제
```json
{
  "message": "세션이 삭제되었습니다",
  "session_id": "session-a1b2c3d4-..."
}
```

### 5. **GET /api/v1/chat/stats/sessions** - 세션 통계
```json
{
  "total_sessions": 42,
  "active_sessions": 15,
  "expired_sessions": 27
}
```

### 6. **POST /api/v1/chat/cleanup/sessions** - 만료 세션 정리
```json
{
  "message": "만료된 세션이 정리되었습니다",
  "cleaned_count": 27
}
```

---

## 🔄 데이터 흐름

```
Client Request
    ↓
FastAPI Router (/api/v1/chat/)
    ↓
Session Validation (session_manager)
    ↓
TeamBasedSupervisor Instance
    ↓
supervisor.process_query()
    ↓
    ├─→ PlanningAgent (계획 수립)
    ├─→ SearchTeam (검색 실행)
    ├─→ AnalysisTeam (분석 실행)
    └─→ DocumentTeam (문서 생성)
    ↓
MainSupervisorState (결과)
    ↓
state_to_chat_response() (변환)
    ↓
ChatResponse
    ↓
Client Response (JSON)
```

---

## ✅ 구현 완료 사항

1. ✅ **완전 비동기 아키텍처**
   - 모든 엔드포인트 `async def`
   - `await supervisor.process_query()`
   - `BackgroundTasks`로 cleanup 비동기 처리

2. ✅ **서버 기반 세션 관리**
   - UUID 기반 세션 ID (서버 생성)
   - 24시간 TTL
   - 자동 만료 세션 정리

3. ✅ **상세 응답 포맷 (Option B)**
   - planning_info, team_results 포함
   - search_results, analysis_metrics 포함
   - execution_time_ms, teams_executed 포함

4. ✅ **체크포인트 통합**
   - `enable_checkpointing` 파라미터
   - `thread_id=session_id`로 연결
   - 기존 AsyncSqliteSaver 활용

5. ✅ **에러 처리**
   - Pydantic validation 에러
   - ValueError, KeyError 처리
   - 일반 예외 처리

---

## 🚀 다음 단계

### 1. API 테스트
```bash
# 서버 실행
cd backend
uvicorn app.main:app --reload

# 테스트 (curl 또는 Swagger UI)
curl -X POST "http://localhost:8000/api/v1/chat/start" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

### 2. 프로덕션 최적화 (추후)
- [ ] SessionManager를 Redis/DynamoDB로 교체
- [ ] 응답 포맷 간소화 (Option A로 변경)
- [ ] Rate limiting 추가
- [ ] API 인증/인가 (JWT)
- [ ] 로깅 및 모니터링

### 3. TODO 관리 시스템 구현
- [ ] TODO 상태 추적 API
- [ ] 사용자 개입 API (TODO 수정)
- [ ] 체크포인트 롤백 API

---

## 📊 성능 고려사항

1. **동시성**: FastAPI의 비동기 처리로 높은 동시성 지원
2. **메모리**: 현재 세션은 메모리 저장 (프로덕션에서는 외부 저장소 필요)
3. **체크포인트**: SQLite 기반 (112개 체크포인트, 1936개 쓰기 검증됨)
4. **응답 크기**: 상세 응답으로 인한 페이로드 증가 (추후 최적화)

---

## 🔒 보안 고려사항

1. **세션 ID**: 서버 생성 UUID (예측 불가능)
2. **만료 처리**: 24시간 TTL, 자동 정리
3. **입력 검증**: Pydantic 모델로 모든 입력 검증
4. **CORS**: 현재 모든 origin 허용 (프로덕션에서 제한 필요)

---

## 📝 추가 참고사항

- **Supervisor 연동**: `TeamBasedSupervisor.process_query()` 완벽 통합
- **State 구조**: `MainSupervisorState` 기반 응답 생성
- **LangGraph**: 기존 체크포인트 시스템과 seamless 연동
- **확장성**: 추가 엔드포인트 쉽게 추가 가능 (router 구조)

---

**작성자**: Claude Code
**버전**: 1.0.0
**마지막 업데이트**: 2025-10-08
