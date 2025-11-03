# Phase 4 Planning: Checkpointer + Real HITL Implementation

**작성일**: 2025-11-03
**대상 프로젝트**: Octostrator Planning-Based Multi-Agent System
**현재 상태**: Phase 3.6 완료 (Aggregator + 3 Generators)
**Phase 4 목표**: Checkpointer를 통한 State 영속화 + 실제 HITL 구현

---

## 📋 Executive Summary

Phase 4에서는 현재 메모리 기반으로만 동작하는 Octostrator를 **영속성 있는 시스템**으로 전환합니다. 이를 통해:

1. **세션 관리**: 사용자별 독립적인 실행 컨텍스트 유지
2. **실제 HITL**: 사용자 승인 대기 중 State 저장 및 복원
3. **Plan 수정 가능**: 실행 중 Plan 동적 변경 지원
4. **재시작 가능**: 서버 재시작 후에도 실행 재개
5. **디버깅 향상**: State 히스토리 추적 가능

**참고 구현**: beta_v003의 LangGraph 0.6 + AsyncPostgresSaver 패턴을 **LangGraph 1.0** 스타일로 적용

---

## 🎯 Phase 4 목표

### 1. Checkpointer 통합
- AsyncPostgresSaver 사용 (PostgreSQL 기반)
- thread_id 기반 세션 관리
- State 자동 저장/복원

### 2. 실제 HITL 구현
- Phase 3의 자동 승인 제거
- `interrupt()` 패턴으로 실행 중단
- API를 통한 사용자 응답 수신 및 재개

### 3. Plan 동적 수정
- HITL 시점에서 Plan 수정 가능
- 새 Task 추가/삭제/순서 변경
- Re-planning 트리거 지원

### 4. 세션 API
- 새 세션 생성
- 기존 세션 조회/재개
- 세션 종료 및 정리

---

## 🏗️ 아키텍처 변경 사항

### 현재 Phase 3.6 구조

```
START → intent → planning → executor → (agents) → aggregator → router → (generators) → END
                                ↓
                           hitl_handler (자동 승인)
```

### Phase 4 구조

```
START → intent → planning → executor → (agents) → aggregator → router → (generators) → END
                                ↓
                    hitl_handler (interrupt + 대기)
                           ↓ (State 저장)
                    [PostgreSQL Checkpointer]
                           ↓ (사용자 응답 대기)
                    API Call: resume_session(thread_id, response)
                           ↓ (State 복원)
                    executor (실행 재개)
```

---

## 🔧 기술 스택 및 의존성

### LangGraph 버전
- **현재 Phase 3.6**: LangGraph 1.0 패턴 사용 (Command, START/END, add_edge)
- **Phase 4**: LangGraph 1.0 유지하되, Checkpointer 통합

### Checkpointer 선택
- **AsyncPostgresSaver** (참고: beta_v003)
  - 프로덕션 환경에 적합
  - 멀티 프로세스 지원
  - 트랜잭션 보장
  - 히스토리 관리 용이

### 필요 패키지
```python
# requirements.txt에 추가
langgraph>=1.0.0
langgraph-checkpoint-postgres>=1.0.0
asyncpg>=0.29.0
psycopg>=3.1.0
```

### PostgreSQL 설정
```sql
-- Checkpointer용 테이블 자동 생성
-- langgraph-checkpoint-postgres가 자동으로 생성하지만, 수동 생성도 가능
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx ON checkpoints (thread_id);
```

---

## 📝 Phase 4 구현 단계

### Phase 4.1: Checkpointer 기본 통합

**목표**: AsyncPostgresSaver 설정 및 기본 State 저장/복원

#### 구현 내역

1. **Checkpointer 초기화 모듈**
   - 파일: `backend/app/octostrator/checkpointer/postgres_checkpointer.py`
   - AsyncPostgresSaver 초기화 함수
   - PostgreSQL 연결 풀 관리
   - 환경 변수 설정 (DATABASE_URL)

2. **Graph 컴파일 시 Checkpointer 연결**
   - 파일: `backend/app/octostrator/supervisor/graph.py`
   - `build_supervisor_graph()` 함수 수정
   - `workflow.compile(checkpointer=checkpointer)` 추가

3. **Session Manager 구현**
   - 파일: `backend/app/octostrator/session/session_manager.py`
   - thread_id 생성/관리
   - 세션 조회/삭제 API

4. **테스트**
   - State가 PostgreSQL에 저장되는지 확인
   - 동일 thread_id로 재실행 시 이전 State 복원 확인

#### 참고 코드 (beta_v003 기반)

```python
# checkpointer 초기화
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def create_checkpointer() -> AsyncPostgresSaver:
    """AsyncPostgresSaver 초기화"""
    db_uri = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/octostrator")

    checkpointer = AsyncPostgresSaver.from_conn_string(db_uri)
    await checkpointer.setup()  # 테이블 생성

    return checkpointer

# Graph 컴파일
checkpointer = await create_checkpointer()
compiled_graph = workflow.compile(checkpointer=checkpointer)
```

#### 예상 문제점

1. **PostgreSQL 연결 실패**: DATABASE_URL 설정 누락 → 환경 변수 검증 로직 필요
2. **비동기 초기화 타이밍**: FastAPI 시작 시점에 checkpointer 초기화 필요
3. **연결 풀 관리**: 과도한 연결 방지 → 싱글톤 패턴 고려

---

### Phase 4.2: HITL Interrupt 구현

**목표**: HITL 시점에서 실행 중단 및 사용자 응답 대기

#### 구현 내역

1. **HITL Handler 수정**
   - 파일: `backend/app/octostrator/nodes/hitl_handler.py`
   - 자동 승인 로직 제거
   - `interrupt()` 호출 추가

2. **Interrupt Value 구조 정의**
   ```python
   interrupt_value = {
       "type": "hitl_request",
       "step_id": current_step,
       "question": step["hitl_question"],
       "plan_snapshot": plan,
       "allow_plan_modification": True,
       "metadata": {...}
   }
   ```

3. **State 조회 API**
   - 파일: `backend/app/api/routes/session.py`
   - `GET /sessions/{thread_id}/state` - 현재 State 및 Interrupt 정보 조회
   - 참고: beta_v003의 `app.aget_state(config)` 패턴

4. **세션 재개 API**
   - `POST /sessions/{thread_id}/resume` - 사용자 응답 전달 및 실행 재개
   - Body: `{"hitl_response": "user approval text", "modified_plan": [...]}`

5. **테스트**
   - HITL 도달 시 실행이 실제로 중단되는지 확인
   - 사용자 응답 후 executor로 정상 복귀 확인

#### 참고 코드 (beta_v003 기반)

```python
# hitl_handler.py
from langgraph.types import interrupt

async def hitl_handler_node(state: SupervisorState) -> Dict:
    """HITL 핸들러 - Phase 4: 실제 interrupt"""
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    question = step.get("hitl_question", "승인이 필요합니다.")

    # Interrupt 발생 (실행 중단)
    interrupt_value = interrupt({
        "type": "hitl_request",
        "step_id": current_step,
        "question": question,
        "plan_snapshot": plan.copy(),
        "allow_plan_modification": True
    })

    # 사용자 응답이 interrupt_value에 포함됨
    hitl_response = interrupt_value.get("response", "")
    modified_plan = interrupt_value.get("modified_plan", None)

    # Plan 수정이 있으면 적용
    if modified_plan:
        plan = modified_plan

    # Step 완료 처리
    plan[current_step]["status"] = "completed"
    plan[current_step]["hitl_response"] = hitl_response
    plan[current_step]["result"] = f"HITL: {question}\n사용자 응답: {hitl_response}"

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "is_waiting_human": False,
        "messages": [AIMessage(content=f"[HITL] 사용자 승인 완료: {hitl_response}")]
    }

# API route
@router.get("/sessions/{thread_id}/state")
async def get_session_state(thread_id: str):
    """현재 세션의 State 및 Interrupt 정보 조회"""
    config = {"configurable": {"thread_id": thread_id}}

    state_snapshot = await app.aget_state(config)

    interrupt_data = None
    if state_snapshot.tasks:
        for task in state_snapshot.tasks:
            if hasattr(task, 'interrupts') and task.interrupts:
                interrupt_data = task.interrupts[0].value
                break

    return {
        "thread_id": thread_id,
        "state": state_snapshot.values,
        "interrupt": interrupt_data,
        "next_node": state_snapshot.next
    }

@router.post("/sessions/{thread_id}/resume")
async def resume_session(thread_id: str, body: dict):
    """사용자 응답을 반영하여 세션 재개"""
    config = {"configurable": {"thread_id": thread_id}}

    # 사용자 응답을 Command로 전달
    result = await app.ainvoke(
        Command(resume=body),
        config=config
    )

    return {
        "thread_id": thread_id,
        "resumed": True,
        "result": result
    }
```

#### 예상 문제점

1. **Interrupt Value 전달 방식**: LangGraph 1.0에서 interrupt()의 정확한 API 확인 필요
2. **Resume 시 Command 구조**: `Command(resume=...)` 형식이 맞는지 확인 필요
3. **Frontend 대기 처리**: WebSocket 또는 Polling 방식 결정 필요

---

### Phase 4.3: Plan 동적 수정 지원

**목표**: HITL 시점에서 사용자가 Plan을 수정할 수 있도록 지원

#### 구현 내역

1. **Plan 수정 모드**
   - HITL Interrupt 시 `allow_plan_modification: true` 플래그
   - 사용자가 Plan을 수정하여 resume 요청

2. **수정 가능한 작업**
   - 새 Task 추가
   - 기존 Task 삭제
   - Task 순서 변경
   - Agent/Tool 변경

3. **Plan 검증 로직**
   - 파일: `backend/app/octostrator/utils/plan_validator.py`
   - 수정된 Plan의 유효성 검증
   - Agent 존재 여부 확인
   - 순환 참조 방지

4. **HITL Handler에서 수정된 Plan 적용**
   ```python
   if modified_plan:
       # 검증
       validation_result = validate_plan(modified_plan)
       if not validation_result.is_valid:
           raise ValueError(f"Invalid plan: {validation_result.errors}")

       # 적용
       plan = modified_plan
   ```

5. **Re-planning 트리거**
   - 사용자가 "전체 재계획" 요청 시
   - Planning Node로 다시 라우팅

6. **테스트**
   - HITL에서 Task 추가/삭제/순서 변경 테스트
   - 잘못된 Plan 수정 시 에러 처리 확인

#### API 예시

```python
POST /sessions/{thread_id}/resume
{
    "response": "승인합니다",
    "modified_plan": [
        {
            "step_id": 1,
            "agent": "search",
            "description": "검색 작업",
            "status": "completed"
        },
        {
            "step_id": 2,
            "agent": "analysis",  // 원래 validation이었는데 변경
            "description": "분석 작업",
            "status": "pending"
        },
        {
            "step_id": 3,  // 새로 추가된 Task
            "agent": "document",
            "description": "문서 생성",
            "status": "pending"
        }
    ]
}
```

#### 예상 문제점

1. **step_id 충돌**: 새 Task 추가 시 step_id 재할당 필요
2. **실행 중인 Task 수정**: 이미 completed된 Task는 수정 불가 처리
3. **Frontend UI**: Plan 수정 UI가 복잡할 수 있음

---

### Phase 4.4: 세션 관리 API

**목표**: 세션 생성, 조회, 재개, 종료 API 제공

#### 구현 내역

1. **세션 생성 API**
   ```python
   POST /sessions
   {
       "user_id": "user123",
       "initial_message": "데이터를 검색하고 분석해줘"
   }

   Response:
   {
       "thread_id": "thread_abc123",
       "created_at": "2025-11-03T10:00:00Z"
   }
   ```

2. **세션 목록 조회 API**
   ```python
   GET /sessions?user_id=user123

   Response:
   {
       "sessions": [
           {
               "thread_id": "thread_abc123",
               "created_at": "2025-11-03T10:00:00Z",
               "status": "waiting_human",
               "last_node": "hitl_handler"
           }
       ]
   }
   ```

3. **세션 상세 조회 API**
   ```python
   GET /sessions/{thread_id}

   Response:
   {
       "thread_id": "thread_abc123",
       "state": {...},
       "interrupt": {...},
       "history": [...]
   }
   ```

4. **세션 종료 API**
   ```python
   DELETE /sessions/{thread_id}
   ```

5. **테스트**
   - 여러 세션 동시 생성 및 독립 실행 확인
   - 세션 조회 API 정상 동작 확인

---

### Phase 4.5: 히스토리 및 디버깅

**목표**: State 변경 이력 조회 및 디버깅 지원

#### 구현 내역

1. **State 히스토리 조회 API**
   ```python
   GET /sessions/{thread_id}/history

   Response:
   {
       "history": [
           {
               "checkpoint_id": "...",
               "node": "intent",
               "timestamp": "2025-11-03T10:00:01Z",
               "state": {...}
           },
           {
               "checkpoint_id": "...",
               "node": "planning",
               "timestamp": "2025-11-03T10:00:05Z",
               "state": {...}
           }
       ]
   }
   ```

2. **Time-travel 디버깅**
   - 특정 checkpoint로 State 복원
   - 디버깅 목적으로만 사용 (프로덕션 X)

3. **로깅 개선**
   - 각 노드 실행 시 로그 기록
   - Checkpointer 저장/복원 로그

---

## 🔍 참고 구현 비교 (beta_v003 vs beta_v002)

| 기능 | beta_v003 (참고) | beta_v002 Phase 4 (목표) |
|------|------------------|--------------------------|
| LangGraph 버전 | 0.6 | 1.0 |
| Checkpointer | AsyncPostgresSaver | AsyncPostgresSaver |
| HITL 패턴 | `interrupt()` | `interrupt()` (동일) |
| State 구조 | BaseState → SupervisorState | SupervisorState (기존 유지) |
| 그래프 구조 | 3-tier (Supervisor → Teams → Executors) | 1-tier (Supervisor → Agents) |
| 메모리 시스템 | 3-tier Memory | Phase 4에서는 미구현 (Phase 5 고려) |
| WebSocket | 실시간 진행 상황 스트리밍 | Phase 4에서는 HTTP API만 (Phase 5 고려) |
| Thread ID | 사용자가 생성 | 시스템이 자동 생성 |

---

## ⚠️ 잠재적 문제점 및 해결 방안

### 1. LangGraph 1.0 Checkpointer 호환성
**문제**: LangGraph 1.0에서 AsyncPostgresSaver의 정확한 API 확인 필요

**해결 방안**:
- LangGraph 1.0 공식 문서 확인
- 테스트 코드 작성하여 검증
- 필요 시 beta_v003의 0.6 패턴을 1.0 스타일로 마이그레이션

### 2. Interrupt 복원 메커니즘
**문제**: `interrupt()` 호출 후 resume 시 정확한 값 전달 방식 불명확

**해결 방안**:
- `Command(resume=...)` 패턴 검증
- LangGraph 예제 코드 참고
- 필요 시 Custom Interrupt Node 구현

### 3. PostgreSQL 의존성
**문제**: 개발 환경에 PostgreSQL 필요

**해결 방안**:
- Docker Compose로 PostgreSQL 컨테이너 제공
- 개발용 SQLite Checkpointer 옵션 제공 (langgraph-checkpoint-sqlite)
- 환경 변수로 Checkpointer 선택 가능하게 구성

### 4. Plan 수정 시 State 일관성
**문제**: 사용자가 Plan을 수정할 때 이미 실행된 Agent 결과와 충돌 가능

**해결 방안**:
- completed 상태의 Task는 수정 불가 처리
- 수정된 Plan의 step_id 재할당
- Plan 검증 로직 강화

### 5. 멀티 프로세스 환경
**문제**: FastAPI worker가 여러 개일 때 Checkpointer 공유 필요

**해결 방안**:
- AsyncPostgresSaver는 멀티 프로세스 지원
- 단, 같은 thread_id에 대한 동시 실행 방지 필요 (락 메커니즘)
- PostgreSQL의 트랜잭션 활용

---

## 🧪 테스트 계획

### Phase 4.1 테스트
- [ ] Checkpointer 초기화 성공
- [ ] State가 PostgreSQL에 저장되는지 확인
- [ ] 동일 thread_id로 재실행 시 State 복원 확인

### Phase 4.2 테스트
- [ ] HITL 도달 시 실행 중단 확인
- [ ] State 조회 API로 Interrupt 정보 확인
- [ ] resume API로 실행 재개 확인

### Phase 4.3 테스트
- [ ] HITL에서 Plan 수정 (Task 추가/삭제/순서 변경)
- [ ] 잘못된 Plan 수정 시 에러 처리 확인
- [ ] Re-planning 트리거 동작 확인

### Phase 4.4 테스트
- [ ] 여러 세션 동시 생성 및 독립 실행
- [ ] 세션 조회 API 정상 동작
- [ ] 세션 종료 API 정상 동작

### Phase 4.5 테스트
- [ ] State 히스토리 조회 API
- [ ] Time-travel 디버깅 (옵션)

---

## 📦 필요한 파일 및 모듈

### 새로 작성할 파일

1. `backend/app/octostrator/checkpointer/postgres_checkpointer.py`
   - AsyncPostgresSaver 초기화 함수

2. `backend/app/octostrator/session/session_manager.py`
   - thread_id 생성/관리
   - 세션 조회/삭제

3. `backend/app/octostrator/utils/plan_validator.py`
   - Plan 검증 로직

4. `backend/app/api/routes/session.py`
   - 세션 관리 API 엔드포인트

5. `tests/test_phase4_1.py`, `test_phase4_2.py`, ...
   - Phase 4 각 단계별 테스트

### 수정할 파일

1. `backend/app/octostrator/supervisor/graph.py`
   - `build_supervisor_graph()` 함수에 checkpointer 매개변수 추가
   - `workflow.compile(checkpointer=checkpointer)` 적용

2. `backend/app/octostrator/nodes/hitl_handler.py`
   - 자동 승인 로직 제거
   - `interrupt()` 호출 추가

3. `backend/app/config/system.py`
   - DATABASE_URL 환경 변수 추가

4. `backend/app/main.py`
   - FastAPI 시작 시 Checkpointer 초기화

5. `requirements.txt`
   - `langgraph-checkpoint-postgres` 추가
   - `asyncpg` 추가

---

## 📚 참고 자료

1. **LangGraph 1.0 공식 문서**
   - Checkpointer 사용법
   - interrupt() API
   - AsyncPostgresSaver 설정

2. **beta_v003 참고 코드**
   - `COMPREHENSIVE_ANALYSIS_251029.md`
   - Checkpointer 초기화 패턴 (lines 446-464)
   - interrupt() 사용 패턴 (lines 356-405)
   - State 조회 패턴 (lines 509-521)

3. **PostgreSQL 공식 문서**
   - JSONB 타입 사용법
   - 인덱싱 전략

---

## 🤔 사용자 질문 사항

Phase 4 구현을 시작하기 전에 다음 사항들을 확인하고 싶습니다:

### 1. PostgreSQL 환경
- PostgreSQL이 이미 설치되어 있나요?
- 개발 환경에서 Docker를 사용하나요? (Docker Compose로 PostgreSQL 제공 가능)
- 아니면 SQLite Checkpointer로 시작할까요? (개발용으로 더 간단)

### 2. LangGraph 버전
- LangGraph 1.0을 계속 사용할 것이 맞나요?
- 아니면 beta_v003처럼 0.6을 사용할까요? (참고 코드가 0.6 기반이라 0.6이 더 안전할 수 있음)

### 3. API 스타일
- 세션 관리 API를 REST API로 구현할까요?
- 아니면 WebSocket도 함께 구현할까요? (실시간 진행 상황 스트리밍)

### 4. Phase 4 세부 단계
- Phase 4.1부터 4.5까지 순차적으로 진행하는 것이 좋을까요?
- 아니면 특정 단계를 먼저 우선 구현할까요?

### 5. 기타
- Plan 수정 기능이 Phase 4에서 꼭 필요한가요? (Phase 5로 미룰 수도 있음)
- HITL은 모든 Agent에서 발생 가능하게 할까요? 아니면 특정 시점에만 발생하게 할까요?

---

## ✅ 다음 단계

계획 문서 검토 후 다음 단계를 진행합니다:

1. **사용자 질문 답변 받기**
2. **Phase 4.1 구현 시작**: Checkpointer 기본 통합
3. **각 Phase별 테스트 및 검증**
4. **다음 Phase로 진행**

---

**문서 작성자**: Claude (Octostrator Assistant)
**검토 필요**: Phase 4 구현 전 사용자 확인 필요
