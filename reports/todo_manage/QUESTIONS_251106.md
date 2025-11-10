# 사용자 확인 필요 사항

**작성일:** 2025-11-06
**버전:** 1.0

---

## 📋 목차

1. [필수 확인 사항](#필수-확인-사항)
2. [선택 확인 사항](#선택-확인-사항)
3. [기술적 결정 사항](#기술적-결정-사항)
4. [우선순위 결정](#우선순위-결정)

---

## ✅ 필수 확인 사항

### Q1: State History 보관 기간

**질문**: History 데이터를 얼마나 오래 보관할까요?

**옵션**:
- **A**: 세션 종료 시까지만 (세션 완료되면 삭제)
- **B**: 7일 보관 후 자동 삭제
- **C**: 30일 보관 후 자동 삭제
- **D**: 영구 보관 (수동 삭제만 가능)

**현재 제안**: 옵션 B (7일)

**이유**:
- PostgreSQL 부하 관리
- 대부분의 사용 케이스는 최근 내역만 필요
- 필요시 아카이빙으로 별도 보관 가능

**결정 필요**: [ ] 옵션 선택

---

### Q2: History 최대 항목 수

**질문**: 하나의 세션에서 History 항목을 최대 몇 개까지 저장할까요?

**옵션**:
- **A**: 100개 (초과 시 오래된 것 삭제)
- **B**: 500개
- **C**: 1000개
- **D**: 무제한 (제한 없음)

**현재 제안**: 옵션 C (1000개)

**이유**:
- 평균 세션은 20-50개 action
- 여유 있게 1000개면 대부분 케이스 커버
- 1000개 ≈ 500KB (PostgreSQL에 문제없음)

**결정 필요**: [ ] 옵션 선택

---

### Q3: API 인증 방식

**질문**: API 보안을 위한 인증을 추가할까요?

**옵션**:
- **A**: 지금 당장 추가 (JWT)
- **B**: 나중에 추가 (Phase 2 이후)
- **C**: 필요 없음 (내부 시스템만 사용)

**현재 제안**: 옵션 B (나중에)

**이유**:
- 현재는 기능 구현에 집중
- 내부 테스트 환경이면 인증 불필요
- 추후 프로덕션 배포 시 JWT 추가 가능

**결정 필요**: [ ] 옵션 선택

---

### Q4: WebSocket과의 연동

**질문**: 새 API들을 WebSocket으로도 사용 가능하게 만들까요?

**시나리오**:
```
WebSocket으로 접속 중
→ 사용자가 Todo 수정
→ WebSocket으로 수정 사항 실시간 전송
→ 클라이언트에서 즉시 반영
```

**옵션**:
- **A**: Phase 1에서 함께 구현
- **B**: Phase 2에서 별도 구현
- **C**: 필요 없음 (REST API만 사용)

**현재 제안**: 옵션 B (Phase 2)

**이유**:
- Phase 1은 REST API 안정화에 집중
- WebSocket 연동은 추가 복잡도 발생
- REST API가 안정된 후 WebSocket 추가가 안전

**결정 필요**: [ ] 옵션 선택

---

## 🔶 선택 확인 사항

### Q5: Todo 상태 관리

**질문**: Todo의 status 값을 어떻게 정의할까요?

**현재 제안**:
```python
TodoStatus = Literal[
    "pending",      # 대기 중
    "in_progress",  # 실행 중
    "completed",    # 완료
    "failed",       # 실패
    "skipped"       # 건너뜀
]
```

**추가 고려 사항**:
- `"paused"` - 일시정지
- `"cancelled"` - 취소됨
- `"waiting_dependency"` - 의존성 대기

**결정 필요**: [ ] 추가 status 필요 여부

---

### Q6: Plan 버전 관리 전략

**질문**: Plan이 수정될 때 어떻게 버전을 관리할까요?

**옵션**:
- **A**: 자동 버전 증가 (v1, v2, v3, ...)
- **B**: 의미있는 버전 (v1.0, v1.1, v2.0, ...)
- **C**: 타임스탬프만 (버전 번호 없음)

**현재 제안**: 옵션 A (자동 증가)

**이유**:
- 구현이 가장 간단
- 대부분의 사용 케이스에 충분
- 버전 번호로 순서 추적 쉬움

**결정 필요**: [ ] 옵션 선택

---

### Q7: Agent 변경 시 Todo 자동 재실행

**질문**: Agent를 변경하면 해당 Todo를 자동으로 재실행할까요?

**시나리오**:
```
Todo: "칼로리 계산" (DietAgent, status: completed)
→ Agent 변경: DietAgent → WorkoutAgent
→ ???
```

**옵션**:
- **A**: 자동 재실행 (status를 pending으로 변경)
- **B**: 수동 재실행 (사용자가 retry API 호출 필요)
- **C**: 상태 유지 (completed 그대로, 다음에 실행)

**현재 제안**: 옵션 B (수동)

**이유**:
- 예상치 못한 재실행 방지
- 사용자가 명시적으로 제어
- 비용/리소스 절약

**결정 필요**: [ ] 옵션 선택

---

### Q8: Error 발생 시 자동 재시도

**질문**: Todo 실행 중 에러가 발생하면 자동으로 재시도할까요?

**옵션**:
- **A**: 자동 재시도 (최대 3회)
- **B**: 자동 재시도 없음 (사용자가 수동 retry)
- **C**: 설정 가능 (Todo별로 retry_policy 설정)

**현재 제안**: 옵션 B (자동 재시도 없음)

**이유**:
- 일부 에러는 재시도해도 실패 (예: 잘못된 입력)
- LLM 비용 절약
- 사용자가 에러 원인 파악 후 수동 재시도

**결정 필요**: [ ] 옵션 선택

---

## 🔧 기술적 결정 사항

### Q9: Reducer 함수 위치

**질문**: Reducer 함수들을 어디에 위치시킬까요?

**옵션**:
- **A**: `backend/app/octostrator/states/reducers.py` (별도 파일)
- **B**: `backend/app/octostrator/states/octostrator_state.py` (같은 파일)
- **C**: `backend/app/octostrator/states/` 폴더 내 각 파일
  - `todo_reducers.py`
  - `plan_reducers.py`
  - `history_reducers.py`

**현재 제안**: 옵션 A (reducers.py)

**이유**:
- 한 곳에 모아서 관리 용이
- 재사용 쉬움
- 파일 수 최소화

**결정 필요**: [ ] 옵션 선택

---

### Q10: StateHelper 함수 형태

**질문**: StateHelper를 클래스로 만들까요, 개별 함수로 만들까요?

**옵션**:
- **A**: 클래스 (현재 제안)
  ```python
  StateHelpers.get_action_at_step(state, step)
  ```
- **B**: 개별 함수
  ```python
  get_action_at_step(state, step)
  ```
- **C**: State 메서드로 추가
  ```python
  state.get_action_at_step(step)  # (불가능 - dict임)
  ```

**현재 제안**: 옵션 A (클래스)

**이유**:
- 네임스페이스 정리
- 관련 함수들 그룹화
- Import 간단

**결정 필요**: [ ] 옵션 선택

---

### Q11: API 파일 구조

**질문**: 새 API들을 어떻게 구성할까요?

**옵션**:
- **A**: 기존 파일에 추가
  - `backend/app/api/sessions.py`에 모두 추가
- **B**: 새 파일 생성
  - `backend/app/api/todos.py` (Todo 관련)
  - `backend/app/api/agents.py` (Agent 관련)
  - `backend/app/api/sessions.py` (Session 관련)
- **C**: 세분화
  - `backend/app/api/sessions/state.py`
  - `backend/app/api/sessions/todos.py`
  - `backend/app/api/sessions/history.py`

**현재 제안**: 옵션 B (새 파일)

**이유**:
- 관심사 분리
- 파일 크기 적절
- 유지보수 용이

**결정 필요**: [ ] 옵션 선택

---

### Q12: PostgreSQL 인덱스 추가

**질문**: History 조회 성능을 위해 PostgreSQL 인덱스를 추가할까요?

**인덱스 대상**:
- `action_history.step`
- `action_history.timestamp`
- `plan_history.version`
- `user_interactions.type`

**옵션**:
- **A**: Phase 1에서 함께 추가
- **B**: Phase 3 (성능 테스트 후)
- **C**: 필요 없음

**현재 제안**: 옵션 B (테스트 후)

**이유**:
- 초기에는 데이터 적어서 인덱스 불필요
- 성능 병목 확인 후 추가가 효율적
- 불필요한 인덱스는 오히려 쓰기 성능 저하

**결정 필요**: [ ] 옵션 선택

---

## 🎯 우선순위 결정

### Q13: Phase 1에서 꼭 구현할 기능

**질문**: Phase 1에서 아래 기능 중 어디까지 구현할까요?

**체크리스트** (중요도 높은 순):
- [ ] **필수 1**: State History 기본 구조 (action_history, plan_history, user_interactions)
- [ ] **필수 2**: StateHelper 클래스 (get_summary, get_action_at_step 등)
- [ ] **필수 3**: GET /summary, GET /action/{step} API
- [ ] **중요 1**: PUT /state API (State 직접 수정)
- [ ] **중요 2**: POST/DELETE/PUT /todos API (Todo 관리)
- [ ] **중요 3**: POST /interrupt API (실행 중단)
- [ ] **옵션 1**: PUT /todos/reorder API (순서 변경)
- [ ] **옵션 2**: POST /retry/{todo_id} API (재시도)
- [ ] **옵션 3**: GET /agents, PUT /todos/{id}/agent API (Agent 관리)

**현재 제안**: 필수 + 중요 전부 (옵션은 Phase 2)

**결정 필요**: [ ] 체크리스트 확정

---

### Q14: 테스트 범위

**질문**: 테스트를 어디까지 작성할까요?

**옵션**:
- **A**: Unit Test만 (Reducer 함수, StateHelper)
- **B**: Unit + Integration Test (API 엔드포인트)
- **C**: Unit + Integration + E2E Test (전체 시나리오)

**현재 제안**: 옵션 B (Unit + Integration)

**이유**:
- Unit Test로 개별 함수 검증
- Integration Test로 API 동작 확인
- E2E는 시간 소요가 크고 Phase 3에서 가능

**결정 필요**: [ ] 옵션 선택

---

### Q15: 문서화 수준

**질문**: API 문서를 어떻게 작성할까요?

**옵션**:
- **A**: FastAPI 자동 생성 Swagger만
- **B**: Swagger + README 간단 예시
- **C**: Swagger + 상세 가이드 + 예시 코드

**현재 제안**: 옵션 B (Swagger + README)

**이유**:
- Swagger는 자동 생성되므로 비용 없음
- README에 핵심 사용 예시만 추가
- 상세 가이드는 Phase 4에서

**결정 필요**: [ ] 옵션 선택

---

## 📝 결정 사항 정리표

| 번호 | 질문 | 제안 | 결정 | 비고 |
|-----|------|------|------|------|
| Q1 | History 보관 기간 | 7일 | ✅ 영구보관 (설정 가능) | 추후 변경 가능하도록 구성 |
| Q2 | History 최대 항목 | 1000개 | ✅ 무제한 (설정 가능) | 설정으로 제한 가능하게 구현 |
| Q3 | API 인증 | Phase 2 이후 | ✅ 추후 | Phase 2 이후 추가 |
| Q4 | WebSocket 연동 | Phase 2 | ✅ Phase 1 필수 | WebSocket 연동 반드시 구현 |
| Q5 | Todo status | 5가지 | ⚠️ 고도화 필요 | 별도 설계 필요 (아래 참조) |
| Q6 | Plan 버전 관리 | 자동 증가 | ✅ 옵션 A | 자동 증가 (v1, v2, ...) |
| Q7 | Agent 변경 시 | 수동 재실행 | ✅ 자동 재실행 | 사용자 응답 시 자동 재실행 |
| Q8 | 자동 재시도 | 없음 | ✅ 옵션 A (설정 가능) | 재시도 기록 필수, 추후 변경 가능 |
| Q9 | Reducer 위치 | reducers.py | ✅ 옵션 A | reducers.py 별도 파일 |
| Q10 | StateHelper 형태 | 클래스 | ✅ 옵션 A | 클래스 형태 |
| Q11 | API 파일 구조 | 새 파일 | ✅ 옵션 B | todos.py, agents.py 분리 |
| Q12 | PostgreSQL 인덱스 | Phase 3 | ✅ 옵션 B | 성능 테스트 후 추가 |
| Q13 | Phase 1 범위 | 필수+중요 | ✅ 필수+중요 전부 | 옵션은 Phase 2 |
| Q14 | 테스트 범위 | Unit+Integration | ⏸️ 추후 고려 | Phase 3에서 결정 |
| Q15 | 문서화 수준 | Swagger+README | ✅ 옵션 B | Swagger + README |

---

## 🔍 추가 설계 필요 사항

### Q5 상세: Todo Status 고도화

**사용자 요구사항**:
> "todo의 status 관리는 state를 의미하는가? 이부분은 따로 더 고도화할 필요가 있다."

**명확화 필요**:

1. **"state"의 의미**:
   - LangGraph State (전체 시스템 상태)?
   - Todo의 status 필드 (pending, completed 등)?

2. **고도화 방향**:
   - 상태 전이 규칙 정의? (pending → in_progress → completed)
   - 의존성 관리? (Todo A 완료 후에만 Todo B 실행)
   - 병렬 실행? (여러 Todo 동시 실행)
   - 실패 처리? (실패 시 롤백, 스킵, 재시도)

**제안**:
별도 문서 `TODO_STATE_MACHINE_DESIGN.md` 작성 필요
- Todo 생명주기
- 상태 전이 다이어그램
- 의존성 그래프
- 병렬 실행 전략

---

### Q8 상세: 재시도 기록

**사용자 요구사항**:
> "일단 옵션A에서 추후 변경가능하게, 테스트상태에서는 재시도가 필요하고, 이부분도 기록해야 한다 (성능향상을 위해)"

**구현 방향**:

1. **재시도 기록 구조**:
```python
{
  "todo_id": "...",
  "attempt": 3,  # 3번째 시도
  "timestamp": "...",
  "error": "...",
  "retry_reason": "timeout",
  "success": false
}
```

2. **action_history에 기록**:
   - 각 재시도를 별도 step으로 기록
   - 재시도 사유 및 결과 저장

3. **설정 가능**:
```python
retry_policy = {
  "enabled": True,  # 재시도 활성화
  "max_attempts": 3,
  "retry_on": ["timeout", "rate_limit"],  # 재시도할 에러 타입
  "backoff": "exponential"  # 재시도 간격
}
```

4. **성능 분석 활용**:
   - "어떤 Todo가 자주 실패하는가?"
   - "몇 번째 시도에서 성공하는가?"
   - "어떤 에러가 재시도로 해결되는가?"

---

## ⚠️ 중요: History ≠ Memory

**사용자 확인 사항**:
사용자가 "history가 메모리를 의미하는가?"라고 질문하셨습니다.

**명확한 차이**:

### History (현재 계획서)
- **목적**: 작업 내역 추적
- **내용**: "9:30에 DietAgent 실행", "9:35에 사용자 중단"
- **저장 위치**: PostgreSQL Checkpointer
- **사용 예**: "4번 작업이 뭐였지?"

### Memory (별도 시스템)
- **목적**: LLM 컨텍스트 관리
- **내용**:
  - Long-term: 요약된 과거 대화
  - Short-term: 최근 대화 전체
  - Mid-term: 맥락만
- **저장 위치**: 별도 Memory Store
- **사용 예**: LLM에게 전달할 대화 맥락

**결론**:
- 현재 계획서는 **History(작업 내역)**만 다룹니다
- **Memory 시스템**은 별도 설계 및 구현이 필요합니다

---

## ✅ 다음 단계

1. ✅ 모든 질문 답변 완료
2. ⚠️ Q5 (Todo Status 고도화) 별도 설계 필요
3. ✅ 나머지 항목은 구현 가능
4. 다음 선택:
   - **Option A**: Q5 설계 먼저 (추천)
   - **Option B**: Q5 제외하고 구현 시작 (나중에 추가)

---

**참고 문서**:
- `PLAN_251106.md` - 전체 계획
- `THEORY_251106.md` - 이론 배경
- `STATE_DESIGN_251106.md` - State 설계
- `API_DESIGN_251106.md` - API 명세
