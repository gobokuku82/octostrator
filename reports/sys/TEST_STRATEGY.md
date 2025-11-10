# 테스트 전략 (Test Strategy)

**작성일**: 2025-11-06
**목적**: 전체 시스템의 테스트 전략 및 체크리스트
**대상**: QA Engineer, Backend Developer

---

## 📑 목차 (Table of Contents)

1. [개요 (Overview)](#개요-overview)
2. [테스트 피라미드](#테스트-피라미드)
3. [단위 테스트 (Unit Tests)](#단위-테스트-unit-tests)
4. [통합 테스트 (Integration Tests)](#통합-테스트-integration-tests)
5. [E2E 테스트 (End-to-End Tests)](#e2e-테스트-end-to-end-tests)
6. [수동 테스트 (Manual Tests)](#수동-테스트-manual-tests)
7. [성능 테스트 (Performance Tests)](#성능-테스트-performance-tests)
8. [테스트 환경 (Test Environments)](#테스트-환경-test-environments)
9. [CI/CD 통합](#cicd-통합)
10. [테스트 커버리지 목표](#테스트-커버리지-목표)

---

## 개요 (Overview)

### 테스트 목표

1. **품질 보장**: 버그 최소화, 기능 정확성 확보
2. **리그레션 방지**: 기존 기능 보호
3. **자신감 있는 배포**: 안전한 릴리스
4. **빠른 피드백**: 문제 조기 발견

### 현재 상태 (2025-11-06)

| 테스트 타입 | 상태 | 커버리지 | 비고 |
|-------------|------|----------|------|
| **Unit Tests** | 🟡 | ~10% | Phase 3 일부만 |
| **Integration Tests** | 🔴 | 0% | 미작성 |
| **E2E Tests** | 🔴 | 0% | 미작성 |
| **Manual Tests** | 🟢 | N/A | 기본 동작 확인 |
| **Performance Tests** | 🔴 | 0% | 미작성 |

**목표**: 단위 테스트 >80%, 통합 테스트 핵심 Flow, E2E 주요 시나리오

---

## 테스트 피라미드

```
       /\
      /  \     E2E Tests (느림, 소수)
     /____\    ↑ 주요 사용자 시나리오
    /      \
   /  통합   \   Integration Tests (중간, 중간)
  /  테스트  \  ↑ 핵심 Flow
 /___________\
/             \
/   단위 테스트  \  Unit Tests (빠름, 다수)
/_____________\ ↑ 개별 함수/클래스
```

### 각 레벨 비율 (권장)

- **Unit Tests**: 70%
- **Integration Tests**: 20%
- **E2E Tests**: 10%

---

## 단위 테스트 (Unit Tests)

### 목표

개별 함수/클래스/모듈의 정확성 검증

### 도구

- **Framework**: pytest
- **Mocking**: unittest.mock, pytest-mock
- **Fixture**: pytest fixtures
- **Coverage**: pytest-cov

### 테스트 대상

#### 1. Context API (Phase 3)

**파일**: `tests/test_app_context.py` ✅ 완료

**테스트 케이스** (26개):
- [x] AppContext 생성
- [x] LLMSettings Pydantic 검증
- [x] UserTier Enum
- [x] get_user_tier() 함수
- [x] create_app_context() Factory
- [x] LLM Settings Presets (PREMIUM/STANDARD/TRIAL)
- [x] Debug 모드
- [x] Trace ID 자동 생성

**Example**:
```python
def test_create_app_context_with_premium_user():
    """Premium 사용자 Context 생성 테스트"""
    settings = get_llm_settings_for_user(UserTier.PREMIUM)
    context = create_app_context(
        user_id="premium_user123",
        session_id="session_001",
        llm_settings=settings
    )

    assert context.user_tier == UserTier.PREMIUM
    assert context.llm_settings.agent_model == "gpt-4o"
    assert context.llm_settings.agent_max_tokens == 8000
```

---

#### 2. State Serialization

**파일**: `tests/test_state_serialization.py` 🔴 미작성

**테스트 케이스**:
- [ ] OctostratorState msgpack 직렬화/역직렬화
- [ ] CognitiveState 직렬화
- [ ] TodoState 직렬화
- [ ] ExecuteState 직렬화
- [ ] ResponseState 직렬화
- [ ] 직렬화 불가능 객체 에러 테스트

**Example**:
```python
import msgpack

def test_octostrator_state_serialization():
    """OctostratorState 직렬화 테스트"""
    state = {
        "user_query": "안녕하세요",
        "plan": {"goal": "테스트"},
        "todos": [{"id": "todo_1"}]
    }

    # 직렬화
    serialized = msgpack.packb(state)

    # 역직렬화
    deserialized = msgpack.unpackb(serialized, raw=False)

    assert deserialized == state
```

---

#### 3. Custom Reducers

**파일**: `tests/test_reducers.py` 🔴 미작성

**테스트 케이스**:
- [ ] merge_todos_smart (ID 기반 병합)
- [ ] add_with_timestamp_and_step (타임스탬프 추가)
- [ ] track_plan_changes (계획 추적)
- [ ] track_user_interactions (상호작용 추적)

**Example**:
```python
from backend.app.octostrator.states.octostrator_state import merge_todos_smart

def test_merge_todos_smart():
    """Todos 병합 테스트"""
    existing = [
        {"id": "todo_1", "status": "pending"},
        {"id": "todo_2", "status": "completed"}
    ]

    new = [
        {"id": "todo_1", "status": "completed"},  # 업데이트
        {"id": "todo_3", "status": "pending"}     # 새 Todo
    ]

    result = merge_todos_smart(existing, new)

    assert len(result) == 3
    assert result[0]["status"] == "completed"  # todo_1 업데이트됨
    assert any(todo["id"] == "todo_3" for todo in result)  # todo_3 추가됨
```

---

#### 4. Supervisor Nodes

**파일**: `tests/test_*_supervisor.py` 🔴 미작성

**테스트 대상**:
- [ ] Cognitive Supervisor
  - [ ] 의도 파악
  - [ ] 계획 생성
  - [ ] 계획 검증
- [ ] Todo Manager
  - [ ] Plan → Todo 변환
  - [ ] 의존성 관리
  - [ ] HITL 처리
- [ ] Execute Supervisor
  - [ ] Agent 실행
  - [ ] 의존성 해결
  - [ ] 결과 집계
- [ ] Response Supervisor
  - [ ] 응답 생성
  - [ ] 포매팅

**Example**:
```python
import pytest
from backend.app.octostrator.supervisors.cognitive.cognitive_supervisor import CognitiveSupervisor

@pytest.mark.asyncio
async def test_cognitive_planning():
    """Cognitive 계획 생성 테스트"""
    supervisor = CognitiveSupervisor()
    user_message = "회원 홍길동의 운동 프로그램 설계해줘"

    plan = await supervisor.plan(user_message, context={})

    assert plan is not None
    assert "goal" in plan
    assert "steps" in plan
    assert len(plan["steps"]) > 0
```

---

#### 5. Worker Agents

**파일**: `tests/test_*_agent.py` 🔴 미작성

**테스트 대상**:
- [ ] FrontdeskAgent
  - [ ] 리드 스코어링
  - [ ] 상담 일정 추천
  - [ ] 입력 유효성 검증
- [ ] AssessorAgent (향후)
- [ ] ProgramDesignerAgent (향후)
- [ ] 기타 Agents (향후)

**Example**:
```python
import pytest
from backend.app.octostrator.agents.frontdesk.frontdesk_agent import FrontdeskAgent

@pytest.mark.asyncio
async def test_frontdesk_lead_scoring():
    """Frontdesk 리드 스코어링 테스트"""
    agent = FrontdeskAgent()
    task = {
        "inquiry_text": "3개월 PT 등록하고 싶어요",
        "inquiry_type": "membership"
    }

    result = await agent.process_task(task, context={})

    assert result["status"] == "completed"
    assert "lead_info" in result
    assert 0.0 <= result["lead_info"]["lead_score"] <= 1.0
```

---

### 단위 테스트 체크리스트

#### Context API
- [x] AppContext 생성 (26개 테스트)
- [x] LLMSettings 검증
- [x] UserTier 추출
- [x] Factory 함수

#### State
- [ ] OctostratorState 직렬화
- [ ] Supervisor States 직렬화
- [ ] Worker Agent States 직렬화
- [ ] Custom Reducers

#### Supervisors
- [ ] Cognitive Supervisor
- [ ] Todo Manager
- [ ] Execute Supervisor
- [ ] Response Supervisor

#### Worker Agents
- [ ] FrontdeskAgent
- [ ] AssessorAgent (향후)
- [ ] ProgramDesignerAgent (향후)
- [ ] 기타 Agents (향후)

---

## 통합 테스트 (Integration Tests)

### 목표

여러 컴포넌트 간 상호작용 검증

### 도구

- **Framework**: pytest
- **Database**: PostgreSQL test DB
- **Fixtures**: pytest-asyncio, pytest-postgresql

### 테스트 시나리오

#### I-001: Cognitive → Execute Flow

**파일**: `tests/integration/test_cognitive_execute_flow.py` 🔴 미작성

**시나리오**:
1. 사용자 질의 입력
2. Cognitive Layer 계획 생성
3. (Todo Manager 건너뜀)
4. Execute Layer Agent 실행
5. 결과 검증

**Example**:
```python
import pytest
from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph

@pytest.mark.asyncio
async def test_cognitive_execute_flow():
    """Cognitive → Execute 통합 테스트"""
    graph = build_octostrator_graph()

    state = {
        "user_query": "회원 상담 일정 예약",
        "session_id": "test_session",
        "output_format": "chat",
        "plan": {},
        "todos": [],
        "execution_results": {},
        "final_response": "",
        "plan_valid": False
    }

    result = await graph.ainvoke(state)

    # 검증
    assert result["plan_valid"] is True
    assert result["final_response"] != ""
    assert len(result.get("execution_results", {})) > 0
```

---

#### I-002: Cognitive → Todo → Execute Flow

**파일**: `tests/integration/test_full_flow_with_todo.py` 🔴 미작성

**시나리오**:
1. 복잡한 질의 (Todo Manager 필요)
2. Cognitive Layer 계획 생성
3. Todo Manager Todo 생성
4. Execute Layer Todo 실행
5. Response Layer 응답 생성

---

#### I-003: Context API 전체 흐름

**파일**: `tests/integration/test_context_api_flow.py` 🔴 미작성

**시나리오**:
1. AppContext 생성 (UserTier=PREMIUM)
2. Graph 실행 with context
3. 노드에서 runtime.context 접근 확인
4. UserTier별 LLM 사용 확인

---

#### I-004: WebSocket 연결 테스트

**파일**: `tests/integration/test_websocket_connection.py` 🔴 미작성

**시나리오**:
1. WebSocket 연결
2. 메시지 전송
3. 이벤트 수신 (connected, execution_started 등)
4. 최종 결과 확인
5. 연결 종료

**Example**:
```python
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def test_websocket_connection():
    """WebSocket 연결 테스트"""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat/test_session") as websocket:
            # 연결 이벤트 수신
            data = websocket.receive_json()
            assert data["type"] == "connected"

            # 메시지 전송
            websocket.send_json({
                "message": "안녕하세요"
            })

            # 이벤트 수신
            events = []
            for _ in range(10):  # 최대 10개 이벤트
                event = websocket.receive_json()
                events.append(event)
                if event["type"] == "execution_completed":
                    break

            # 검증
            assert any(e["type"] == "final_result" for e in events)
```

---

#### I-005: PostgreSQL Checkpointer 테스트

**파일**: `tests/integration/test_checkpointer.py` 🔴 미작성

**시나리오**:
1. Checkpointer 생성
2. Graph 실행 (thread_id 지정)
3. State 저장 확인
4. 같은 thread_id로 재실행
5. 이전 State 복원 확인

---

### 통합 테스트 체크리스트

- [ ] Cognitive → Execute Flow
- [ ] Cognitive → Todo → Execute Flow
- [ ] Execute → Response Flow
- [ ] Context API 전체 흐름
- [ ] WebSocket 연결
- [ ] PostgreSQL Checkpointer
- [ ] Agent Registry 통합
- [ ] Session Management

---

## E2E 테스트 (End-to-End Tests)

### 목표

실제 사용자 시나리오 검증 (Frontend + Backend + DB)

### 도구

- **Framework**: Playwright 또는 Selenium
- **API Testing**: requests 또는 httpx

### 테스트 시나리오

#### E-001: 기본 사용자 질의 처리

**시나리오**:
1. Frontend 로드
2. WebSocket 연결
3. "안녕하세요" 입력
4. 실시간 이벤트 수신 확인
5. 최종 응답 표시 확인

**Expected**:
- 연결 성공 메시지
- 응답 수신
- UI 업데이트

---

#### E-002: 복잡한 계획 생성

**시나리오**:
1. "회원 홍길동의 운동 프로그램 설계해줘" 입력
2. Cognitive Layer 이벤트 확인
3. Plan 업데이트 이벤트 확인
4. Todo 생성 확인
5. Agent 실행 확인
6. 최종 프로그램 표시 확인

**Expected**:
- Plan에 steps 포함
- Todo 목록 생성
- 실행 진행 상황 표시
- 최종 프로그램 문서 생성

---

#### E-003: UserTier별 LLM 차별화

**시나리오**:
1. Premium 사용자로 질의 (user_id="premium_user123")
2. LLM 모델 확인 (gpt-4o)
3. 상세한 응답 확인

4. Trial 사용자로 질의 (user_id="trial_user456")
5. LLM 모델 확인 (gpt-4o-mini)
6. 간결한 응답 확인

**Expected**:
- Premium: 더 상세하고 긴 응답
- Trial: 간결한 응답

---

#### E-004: 세션 복원

**시나리오**:
1. 질의 1 전송
2. 응답 확인
3. 연결 종료
4. 같은 session_id로 재연결
5. 질의 2 전송 (이전 대화 참조)
6. Context 유지 확인

**Expected**:
- 이전 대화 기억
- Context 기반 응답

---

### E2E 테스트 체크리스트

- [ ] 기본 사용자 질의 처리
- [ ] 복잡한 계획 생성
- [ ] UserTier별 LLM 차별화
- [ ] HITL Approval Flow
- [ ] 세션 복원
- [ ] Frontend-Backend 통신
- [ ] 에러 핸들링 (연결 끊김, 타임아웃 등)

---

## 수동 테스트 (Manual Tests)

### 목표

자동화하기 어려운 시나리오 및 사용자 경험 검증

### 테스트 체크리스트

#### 서버 시작/중지
- [x] uvicorn 서버 시작
- [x] Health check (/health)
- [x] WebSocket 연결 확인
- [x] 서버 종료 (Ctrl+C)

#### 기본 동작
- [x] REST API /chat 엔드포인트
- [x] WebSocket 연결
- [x] 실시간 이벤트 수신
- [x] 최종 응답 확인

#### Context API (Phase 3)
- [x] user_id로 UserTier 추출
- [x] Debug 모드 로깅
- [ ] Metrics 수집 확인

#### 에러 처리
- [ ] 잘못된 JSON 전송
- [ ] message 필드 누락
- [ ] 연결 끊김 처리
- [ ] 타임아웃 처리
- [ ] LLM API 에러

#### 성능
- [ ] 긴 응답 처리 (10초 이상)
- [ ] 동시 연결 (10개)
- [ ] 메모리 사용량
- [ ] CPU 사용량

---

## 성능 테스트 (Performance Tests)

### 목표

시스템 성능 및 확장성 검증

### 도구

- **Load Testing**: Locust 또는 k6
- **Profiling**: cProfile, memory_profiler

### 테스트 시나리오

#### P-001: LLM 호출 최적화

**목표**: LLM API 호출 횟수 최소화

**측정**:
- 요청당 LLM 호출 횟수
- Token 사용량
- 비용 추정

**목표 값**:
- Cognitive: 1-2회
- Todo: 0-1회
- Execute: Agent 수만큼
- Response: 1회

---

#### P-002: WebSocket 연결 제한

**목표**: 동시 연결 최대 수 확인

**테스트**:
1. 점진적으로 동시 연결 수 증가
2. 응답 시간 측정
3. 에러율 측정

**목표 값**:
- 100개 동시 연결 처리
- 평균 응답 시간 <5초
- 에러율 <1%

---

#### P-003: 데이터베이스 쿼리 성능

**목표**: Checkpoint 저장/로드 성능

**측정**:
- 저장 시간
- 로드 시간
- State 크기

**목표 값**:
- 저장 <100ms
- 로드 <50ms
- State 크기 <1MB

---

### 성능 테스트 체크리스트

- [ ] LLM 호출 최적화
- [ ] WebSocket 연결 제한
- [ ] 데이터베이스 쿼리 성능
- [ ] 메모리 사용량 (장시간 실행)
- [ ] CPU 사용량 (높은 부하)

---

## 테스트 환경 (Test Environments)

### 환경 구성

| 환경 | 목적 | DB | LLM 모델 |
|------|------|----|----|
| **Development** | 개발 | Local PostgreSQL | gpt-4o-mini |
| **Testing** | CI/CD | Test DB | Mock / gpt-4o-mini |
| **Staging** | Pre-production | Staging DB | gpt-4o-mini |
| **Production** | 운영 | Production DB | UserTier별 |

### 환경 변수

**Testing 환경** (.env.test):
```env
SYSTEM_ENV=testing
OPENAI_API_KEY=test_key
POSTGRES_URL=postgresql://test:test@localhost:5432/test_db
SYSTEM_DEBUG=true
```

---

## CI/CD 통합

### GitHub Actions (예시)

**파일**: `.github/workflows/test.yml` 🔴 미작성

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        env:
          POSTGRES_URL: postgresql://postgres:test@localhost:5432/test_db
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/ --cov=backend --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 테스트 커버리지 목표

### 단기 목표 (1개월)

| 카테고리 | 현재 | 목표 |
|----------|------|------|
| **Unit Tests** | ~10% | >50% |
| **Integration Tests** | 0% | 핵심 Flow |
| **E2E Tests** | 0% | 주요 시나리오 1개 |

### 중기 목표 (3개월)

| 카테고리 | 목표 |
|----------|------|
| **Unit Tests** | >80% |
| **Integration Tests** | 핵심 + 주요 Flow |
| **E2E Tests** | 주요 시나리오 3개 |

### 장기 목표 (6개월)

- Unit Tests >90%
- Integration Tests 전체 Flow
- E2E Tests 전체 시나리오
- Performance Tests 정기 실행
- CI/CD 완전 자동화

---

## 부록: 테스트 명령어

### 단위 테스트 실행

```bash
# 전체 테스트
pytest tests/

# 특정 파일
pytest tests/test_app_context.py

# 커버리지 포함
pytest tests/ --cov=backend --cov-report=html

# Verbose 모드
pytest tests/ -v
```

### 통합 테스트 실행

```bash
# 통합 테스트만
pytest tests/integration/

# 특정 테스트
pytest tests/integration/test_cognitive_execute_flow.py
```

### E2E 테스트 실행

```bash
# E2E 테스트 (서버 실행 필요)
pytest tests/e2e/

# Playwright
pytest tests/e2e/ --headed  # 브라우저 표시
```

---

**작성자**: Claude Code Agent
**검토자**: -
**버전**: 1.0
**마지막 업데이트**: 2025-11-06
**관련 문서**:
- [MASTER_CHECKLIST.md](MASTER_CHECKLIST.md)
- [FEATURE_SPECIFICATIONS.md](FEATURE_SPECIFICATIONS.md)
