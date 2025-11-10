# Fitness PT Manager - Agent Implementation Report

**작성일**: 2025-11-04
**버전**: 0.4.0
**상태**: Mock 데이터 기반 프로토타입 완료

---

## 1. 시스템 개요

Fitness PT Manager는 **LangGraph 1.0 Supervisor Pattern**을 사용한 멀티 에이전트 챗봇 시스템입니다.
PT 트레이너와 회원 간의 상호작용을 자동화하여 식단 관리, 운동 루틴 추천, 스케줄 관리, 회원 케어, 전문 자료 검색 등을 지원합니다.

### 주요 특징

- **LangGraph 1.0 기반**: StateGraph + TypedDict를 사용한 타입 안전성
- **Supervisor Pattern**: 중앙 Supervisor가 Intent → Planning → Execution을 조율
- **5개 전문 에이전트**: 각 도메인별 특화된 에이전트 (Diet, Workout, Schedule, MemberCare, Coaching)
- **Planning-Based Execution**: 복잡한 요청을 순차적 작업으로 분해
- **데이터베이스 통합**: SQLite (관계형) + FAISS (벡터 검색)
- **React 프론트엔드**: TypeScript 기반 간단한 챗봇 UI

---

## 2. 시스템 아키텍처

### 2.1 전체 플로우

```
사용자 입력
    ↓
Intent Understanding (의도 분석)
    ↓
Planning (작업 분해)
    ↓
Executor (동적 라우팅)
    ↓
Agents (순차 실행: diet, workout, schedule, member_care, coaching)
    ↓
Aggregator (결과 집계)
    ↓
Output Router (출력 형식 선택)
    ↓
Generator (Chat/Graph/Report)
    ↓
사용자에게 응답
```

### 2.2 핵심 컴포넌트

#### SupervisorState (TypedDict)

모든 노드 간 공유되는 상태 구조:

```python
class SupervisorState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_query: Optional[str]          # 사용자 입력 쿼리
    user_intent: Optional[str]         # 파악된 사용자 의도
    plan: List[dict]                   # 작업 계획 (TaskStep 리스트)
    current_step: int                  # 현재 실행 중인 단계
    is_planning: bool                  # 계획 수립 중인가?
    is_executing: bool                 # 실행 중인가?
    is_waiting_human: bool             # HITL 대기 중인가?
    aggregated_data: Optional[dict]    # 집계된 데이터
    output_format: str                 # 출력 형식 (chat/graph/report)
    final_result: Optional[str]        # 최종 결과
```

#### LangGraph 노드 구성

**파일**: `backend/app/octostrator/supervisor/graph.py:112-141`

| 노드 | 역할 | 파일 위치 |
|------|------|-----------|
| `intent` | 사용자 의도 분석 | `supervisor/nodes/intent_understanding.py` |
| `planning` | 작업 계획 생성 | `supervisor/nodes/planning.py` |
| `executor` | 동적 라우팅 (Command 패턴) | `supervisor/nodes/executor.py` |
| `diet` | 식단 관리 에이전트 | `agents/diet/agent.py` |
| `workout` | 운동 루틴 에이전트 | `agents/workout/agent.py` |
| `schedule` | 스케줄 관리 에이전트 | `agents/schedule/agent.py` |
| `member_care` | 회원 케어 에이전트 | `agents/member_care/agent.py` |
| `coaching` | 자료 검색 에이전트 | `agents/coaching/agent.py` |
| `hitl_handler` | 사용자 승인 처리 | `supervisor/nodes/hitl_handler.py` |
| `aggregator` | 결과 집계 | `supervisor/nodes/aggregator.py` |
| `output_router` | 출력 형식 선택 | `supervisor/nodes/router.py` |
| `chat_generator` | 대화형 답변 생성 | `supervisor/nodes/generators.py` |
| `graph_generator` | 시각화 데이터 생성 | `supervisor/nodes/generators.py` |
| `report_generator` | Markdown 보고서 생성 | `supervisor/nodes/generators.py` |

---

## 3. Intent Understanding (의도 분석)

**파일**: `backend/app/octostrator/supervisor/nodes/intent_understanding.py`

### 3.1 역할

사용자의 자연어 입력을 분석하여 **7개 카테고리**로 분류합니다.

### 3.2 카테고리

| 카테고리 | 설명 | 예시 |
|----------|------|------|
| `diet_query` | 식단 관련 조회/기록 | "오늘 식단 보여줘", "아침에 계란 2개 먹었어" |
| `workout_query` | 운동 루틴 조회/추천 | "오늘 운동 추천해줘", "하체 운동 알려줘" |
| `schedule_query` | PT 스케줄 조회/예약 | "내일 PT 예약", "이번 주 스케줄 확인" |
| `member_report` | 회원 상태/진행률 조회 | "김철수 회원 진행 상황", "최근 1주일 효과" |
| `coaching_search` | 운동/식단 자료 검색 | "스쿼트 자세 영상", "다이어트 식단표" |
| `multi_step_task` | 복합 작업 | "회원 상태 확인 후 PT 예약" |
| `progress_comparison` | 진행률 비교 | "지난주 대비 체중 변화", "이번 달 운동량" |

### 3.3 구현 세부사항

```python
# 사용자 쿼리 추출 (messages 또는 user_query에서)
user_request = ""
if messages:
    human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    if human_messages:
        user_request = human_messages[-1].content

if not user_request and user_query:
    user_request = user_query
```

**중요**: `user_query` 필드가 `SupervisorState`에 정의되어야 LangGraph가 유지합니다.
(`backend/app/octostrator/states/supervisor_state.py:62`)

### 3.4 출력 형식

```
Category: diet_query
Subject: 식단 기록
Expected Output: 식단 내역
Complexity: simple
Reasoning: 사용자가 최근 식단 기록을 조회하려는 단순 조회 요청
```

---

## 4. Planning (작업 계획 생성)

**파일**: `backend/app/octostrator/supervisor/nodes/planning.py`

### 4.1 역할

Intent Understanding에서 파악한 의도를 **순차적인 TaskStep 리스트**로 분해합니다.

### 4.2 TaskStep 구조

```python
class TaskStep(BaseModel):
    step_id: int                    # 단계 번호 (1부터 시작)
    agent: str                      # 실행할 에이전트 (diet, workout, etc.)
    description: str                # 작업 설명
    status: str = "pending"         # 상태 (pending/in_progress/completed)
    result: Optional[str] = None    # 실행 결과
    hitl_question: Optional[str] = None  # HITL 질문 (hitl 에이전트만)
```

### 4.3 복잡도별 계획 예시

#### Simple (1-2 steps): 단순 조회

**입력**: "최근 식단 기록 보여줘"

**Plan**:
```json
[
  {"step_id": 1, "agent": "diet", "description": "최근 식단 기록 조회"}
]
```

#### Medium (2-3 steps): 추천/분석

**입력**: "하체 운동 루틴 추천하고 자세 영상 찾아줘"

**Plan**:
```json
[
  {"step_id": 1, "agent": "workout", "description": "하체 운동 루틴 생성"},
  {"step_id": 2, "agent": "coaching", "description": "하체 운동 자세 영상 검색"}
]
```

#### Complex (4+ steps): 복합 작업 + HITL

**입력**: "회원 상태 확인하고 PT 스케줄 잡아줘. 확인 후 예약할게."

**Plan**:
```json
[
  {"step_id": 1, "agent": "member_care", "description": "회원 진행 상황 리포트 생성"},
  {"step_id": 2, "agent": "hitl", "description": "회원 상태 확인", "hitl_question": "회원 상태를 확인해주세요"},
  {"step_id": 3, "agent": "schedule", "description": "PT 스케줄 생성"},
  {"step_id": 4, "agent": "hitl", "description": "스케줄 최종 승인", "hitl_question": "스케줄을 확정하시겠습니까?"}
]
```

### 4.4 Structured Output 사용

LangGraph 1.0의 `with_structured_output()`을 사용하여 LLM 출력을 강제:

```python
class Plan(BaseModel):
    steps: List[TaskStep]
    reasoning: str

structured_llm = llm.with_structured_output(Plan)
plan_result = await structured_llm.ainvoke([planning_prompt, user_intent])
```

---

## 5. 5개 Fitness Agents

### 5.1 공통 특징

- **비동기 함수**: `async def {agent}_node(state: SupervisorState) -> Dict`
- **현재 구현**: Mock 데이터 조회 (SQLite, FAISS)
- **State 업데이트**:
  - `plan[current_step]["status"] = "completed"`
  - `plan[current_step]["result"] = result`
  - `current_step + 1`로 증가

---

### 5.2 DietAgent (식단 관리 에이전트)

**파일**: `backend/app/octostrator/agents/diet/agent.py`

#### 역할

- 사용자의 식단 입력을 분석
- 영양소 계산
- DB에 기록
- 일일 피드백 생성

#### 현재 구현 (Mock)

```python
# SQLite에서 최근 식단 기록 3개 조회
meal_logs = db.query(MealLog).order_by(MealLog.date.desc()).limit(3).all()

# 출력 예시:
# - 아침: 계란 2개, 식빵 2장
#   영양소: 350kcal, 단백질 18g
# - 점심: 닭가슴살 150g, 현미밥 200g
#   영양소: 450kcal, 단백질 35g
```

#### TODO (실제 구현)

1. 자연어 식단 입력 파싱 ("아침에 계란 2개 먹었어")
2. 영양소 계산 (API 또는 로컬 DB)
3. `meal_logs` 테이블에 저장
4. 일일 목표 대비 피드백 생성

#### 데이터베이스 모델

```python
class MealLog(Base):
    __tablename__ = "meal_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    meal_type = Column(String)  # 아침/점심/저녁/간식
    foods = Column(JSON)         # [{"name": "계란", "quantity": 2, "unit": "개"}]
    nutrition = Column(JSON)     # {"calories": 140, "protein": 12, ...}
```

---

### 5.3 WorkoutAgent (운동 루틴 에이전트)

**파일**: `backend/app/octostrator/agents/workout/agent.py`

#### 역할

- 사용자의 목표/경험치를 기반으로 운동 루틴 생성
- 개인화된 운동 프로그램 제안
- 운동 기록 관리

#### 현재 구현 (Mock)

```python
# 최근 운동 루틴 조회
routines = db.query(WorkoutRoutine).order_by(WorkoutRoutine.date.desc()).limit(2).all()

# 추천 운동 조회
exercises = db.query(ExerciseDB).limit(3).all()

# 출력 예시:
# 최근 운동 루틴:
# - 하체 (2025-11-03):
#   • 스쿼트: 3세트 x 10회 (60kg)
#   • 레그프레스: 3세트 x 12회 (100kg)
#
# 추천 운동 (3개):
# - 데드리프트 (전신, 중급)
# - 벤치프레스 (가슴, 초급)
```

#### TODO (실제 구현)

1. 사용자 프로필 분석 (목표, 레벨)
2. 운동 데이터베이스에서 적합한 운동 선택
3. 세트/반복 횟수/무게 계산
4. 개인화된 루틴 생성
5. `workout_routines` 테이블에 저장

#### 데이터베이스 모델

```python
class WorkoutRoutine(Base):
    __tablename__ = "workout_routines"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    muscle_group = Column(String)  # 하체/상체/전신
    exercises = Column(JSON)       # [{"name": "스쿼트", "sets": 3, "reps": 10, "weight": 60}]

class ExerciseDB(Base):
    __tablename__ = "exercise_db"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    muscle_group = Column(String)
    difficulty = Column(String)  # 초급/중급/고급
    instructions = Column(Text)
```

---

### 5.4 ScheduleAgent (PT 스케줄 관리 에이전트)

**파일**: `backend/app/octostrator/agents/schedule/agent.py`

#### 역할

- PT 수업 예약 생성/변경
- 스케줄 확인
- 회원에게 확정/리마인드 알림 발송

#### 현재 구현 (Mock)

```python
# 예정된 스케줄 조회 (현재 시간 이후)
schedules = db.query(Schedule).filter(
    Schedule.date >= datetime.now()
).order_by(Schedule.date).limit(5).all()

# 출력 예시:
# 예정된 PT 스케줄 (3개):
# - 2025-11-05 14:00
#   회원: 김철수
#   트레이너: 박트레이너
#   상태: confirmed
#   메모: 하체 집중 수업
```

#### TODO (실제 구현)

1. 자연어 스케줄 요청 파싱 ("A회원 3시 예약")
2. 트레이너/회원 가용 시간 확인
3. 스케줄 생성 또는 변경
4. `schedules` 테이블에 저장
5. 알림 발송 (이메일/SMS)

#### 데이터베이스 모델

```python
class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trainer_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    status = Column(String)  # pending/confirmed/cancelled
    notes = Column(Text)
```

---

### 5.5 MemberCareAgent (회원 케어 에이전트)

**파일**: `backend/app/octostrator/agents/member_care/agent.py`

#### 역할

- 회원 상태 리포트 생성 (예: A회원 최근 1주 효과)
- 주요 이벤트 알림 (재등록 7일 전, 출석률 저하 등)
- 트레이너에게 회원 관리 정보 제공

#### 현재 구현 (Mock)

```python
# 모든 회원 조회
users = db.query(User).filter(User.id < 100).all()

# 회원 진행률 조회
progress_records = db.query(MemberProgress).filter(
    MemberProgress.user_id == user.id
).order_by(MemberProgress.date.desc()).limit(2).all()

# 출력 예시:
# 회원 현황 (3명):
# 📊 김철수 (chulsoo@example.com)
#    목표: 체중감량, 레벨: 초급
#    최근 측정: 2025-11-03
#    - 체중: 75.0kg
#    - 체지방률: 20.5%
#    - 근육량: 35.0kg
#    변화: 체중 -1.5kg, 체지방 -2.0%, 근육 +0.5kg
#    메모: 식단 관리 잘하고 있음
```

#### TODO (실제 구현)

1. 회원 식별 (이름, ID 등)
2. 회원 데이터 수집 (식단, 운동, 스케줄, 진행률)
3. 상태 분석 (목표 대비 진행도, 추세 등)
4. 리포트 생성
5. 주요 이벤트 감지 (재등록 알림 등)
6. 트레이너에게 알림 발송

#### 데이터베이스 모델

```python
class MemberProgress(Base):
    __tablename__ = "member_progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    weight = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass = Column(Float)
    notes = Column(Text)
```

---

### 5.6 CoachingAgent (전문 자료 검색 에이전트)

**파일**: `backend/app/octostrator/agents/coaching/agent.py`

#### 역할

- 운동 자세 영상 검색
- 식단/운동 관련 논문 검색
- 전문 자료 요약 및 제공
- 북마크 관리

#### 현재 구현 (Mock)

```python
# FAISS 벡터 검색
manager = FAISSManager(index_path, dimension=384)

# Mock 쿼리 벡터 (실제로는 사용자 쿼리를 임베딩)
query_vector = np.random.rand(384).astype(np.float32)

# 유사도 검색
search_results = manager.search(query_vector, top_k=3)

# 출력 예시:
# 검색 결과 (3개):
# 1. 스쿼트 자세 완벽 가이드 (video)
#    설명: 정확한 스쿼트 자세 단계별 설명
#    URL: https://example.com/squat-guide
#    유사도 점수: 0.892
#
# 저장된 북마크 (2개):
# - 데드리프트 입문 가이드 (article)
# - 케토 다이어트 식단표 (diet)
```

#### TODO (실제 구현)

1. 자연어 쿼리 파싱 ("스쿼트 자세 영상")
2. 쿼리를 벡터로 임베딩 (OpenAI Embeddings)
3. FAISS에서 유사도 검색
4. 결과 순위 지정 및 필터링
5. 자료 요약 생성
6. 북마크 저장 옵션

#### 데이터베이스 모델

```python
class Bookmark(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    url = Column(String)
    category = Column(String)  # video/article/diet/workout
    faiss_id = Column(Integer)  # FAISS 인덱스 ID
```

**FAISS 인덱스**: `database/vector_db/exercise_index/`
- `index.faiss`: FAISS 벡터 인덱스
- `metadata.json`: 각 벡터의 메타데이터 (title, url, description, type)

---

## 6. 데이터베이스 구조

### 6.1 SQLite (관계형 데이터베이스)

**파일**: `backend/database/relation_db/models.py`

| 테이블 | 설명 | 주요 컬럼 |
|--------|------|-----------|
| `users` | 회원/트레이너 정보 | id, name, email, goal, level |
| `meal_logs` | 식단 기록 | user_id, date, meal_type, foods(JSON), nutrition(JSON) |
| `workout_routines` | 운동 루틴 | user_id, date, muscle_group, exercises(JSON) |
| `exercise_db` | 운동 데이터베이스 | name, muscle_group, difficulty, instructions |
| `schedules` | PT 스케줄 | user_id, trainer_id, date, status, notes |
| `member_progress` | 회원 진행률 | user_id, date, weight, body_fat_percentage, muscle_mass |
| `bookmarks` | 북마크 | user_id, title, url, category, faiss_id |

### 6.2 FAISS (벡터 검색)

**위치**: `database/vector_db/exercise_index/`

- **dimension**: 384 (OpenAI text-embedding-3-small)
- **인덱스 타입**: Flat (정확한 검색)
- **데이터**: 운동 자세 영상, 식단 자료, 논문 등

**메타데이터 구조**:
```json
{
  "title": "스쿼트 자세 완벽 가이드",
  "description": "정확한 스쿼트 자세 단계별 설명",
  "url": "https://example.com/squat-guide",
  "type": "video"
}
```

### 6.3 Mock 데이터 생성

**스크립트**: `backend/database/relation_db/seed.py`, `backend/database/vector_db/seed_faiss.py`

실행 방법:
```bash
# SQLite Mock 데이터 생성
python backend/database/relation_db/seed.py

# FAISS Mock 데이터 생성
python backend/database/vector_db/seed_faiss.py
```

---

## 7. 프론트엔드 (React)

**위치**: `frontend/`

### 7.1 기술 스택

- **Create React App** (TypeScript)
- **React 19.2.0**
- **개발 서버**: `npm start` (포트 3000)

### 7.2 주요 컴포넌트

**파일**: `frontend/src/App.tsx`

```typescript
interface Message {
  id: string;
  type: 'user' | 'bot';
  content: string;
  timestamp: Date;
}

const quickQuestions = [
  '최근 식단 기록 보여줘',
  '오늘 하체 운동 루틴 추천해줘',
  '예정된 PT 스케줄 확인',
  '스쿼트 자세 영상 찾아줘',
];
```

### 7.3 API 연동

```typescript
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: content,
  }),
});

const data = await response.json();
// data.response → 챗봇 응답
```

### 7.4 UI 특징

- **Gradient 디자인**: 보라색 그라데이션 배경
- **4개 퀵 버튼**: 각 에이전트를 테스트할 수 있는 샘플 질문
- **로딩 애니메이션**: 타이핑 점 애니메이션
- **에러 핸들링**: 서버 연결 실패 시 안내 메시지

---

## 8. 백엔드 API

**파일**: `backend/app/main.py`

### 8.1 FastAPI 엔드포인트

#### POST /chat

**Request**:
```json
{
  "message": "최근 식단 기록 보여줘"
}
```

**Response**:
```json
{
  "response": "[DietAgent] 최근 식단 기록 조회\n\n최근 식단 기록:\n- 아침: 계란 2개, 식빵 2장\n  영양소: 350kcal, 단백질 18g\n..."
}
```

**실행 흐름**:
```python
result = await supervisor_graph.ainvoke({
    "user_query": request.message,
    "messages": [],
    "plan": [],
    "current_step": 0,
    "is_planning": True,
    "is_executing": False,
    "is_waiting_human": False,
    "aggregated_data": {},
    "output_format": "chat"
})
```

### 8.2 CORS 설정

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경: 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.3 WebSocket 지원 (Phase 4.3)

**엔드포인트**: `/ws/{session_id}`

- **세션 관리**: PostgreSQL Checkpointer를 통한 영속화
- **실시간 스트리밍**: LangGraph의 `astream()` 사용

---

## 9. 실행 방법

### 9.1 환경 설정

**.env 파일 생성**:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 9.2 백엔드 실행

```bash
# 가상환경 활성화 (선택)
# python -m venv venv
# venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Mock 데이터 생성 (최초 1회)
python backend/database/relation_db/seed.py
python backend/database/vector_db/seed_faiss.py

# 서버 실행 (포트 8000)
python run_server.py
```

### 9.3 프론트엔드 실행

```bash
# frontend 폴더로 이동
cd frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행 (포트 3000)
npm start
```

### 9.4 테스트

브라우저에서 `http://localhost:3000` 접속 후 4개 퀵 버튼 클릭:

1. **"최근 식단 기록 보여줘"** → DietAgent 테스트
2. **"오늘 하체 운동 루틴 추천해줘"** → WorkoutAgent 테스트
3. **"예정된 PT 스케줄 확인"** → ScheduleAgent 테스트
4. **"스쿼트 자세 영상 찾아줘"** → CoachingAgent 테스트

---

## 10. 현재 상태 및 제약사항

### 10.1 구현 완료 항목

- ✅ LangGraph 1.0 Supervisor Pattern 구조
- ✅ Intent Understanding (7개 카테고리)
- ✅ Planning (TaskStep 생성)
- ✅ 5개 Fitness Agents (Mock 데이터 조회)
- ✅ SQLite + FAISS 데이터베이스 통합
- ✅ React 프론트엔드 (TypeScript)
- ✅ FastAPI 백엔드 (/chat 엔드포인트)
- ✅ CORS 설정
- ✅ Mock 데이터 생성 스크립트

### 10.2 현재 제약사항 (Mock 구현)

| 에이전트 | 현재 동작 | 실제 동작 (TODO) |
|----------|-----------|------------------|
| **DietAgent** | SQLite에서 최근 3개 식단 조회 | 자연어 식단 입력 파싱, 영양소 계산, DB 저장, 피드백 생성 |
| **WorkoutAgent** | 최근 루틴 2개 + 추천 운동 3개 조회 | 사용자 프로필 분석, 개인화된 루틴 생성, 진행도 추적 |
| **ScheduleAgent** | 예정된 스케줄 5개 조회 | 자연어 예약 파싱, 가용 시간 확인, 알림 발송 |
| **MemberCareAgent** | 모든 회원 진행률 조회 | 특정 회원 분석, 추세 분석, 이벤트 감지, 트레이너 알림 |
| **CoachingAgent** | FAISS 랜덤 검색 3개 + 북마크 조회 | 쿼리 임베딩, 유사도 검색, 자료 요약, 북마크 관리 |

### 10.3 미구현 기능

- ❌ **실제 식단 입력 파싱**: "아침에 계란 2개 먹었어" → 구조화된 데이터
- ❌ **영양소 API 연동**: 음식별 영양소 정보 (CalorieNinja, USDA 등)
- ❌ **개인화된 운동 루틴 생성**: 사용자 목표/레벨 기반 알고리즘
- ❌ **자연어 스케줄 파싱**: "A회원 내일 3시 예약" → 구조화된 예약 데이터
- ❌ **알림 발송**: 이메일/SMS 통합
- ❌ **HITL 실제 대기**: 현재 자동 승인, WebSocket으로 사용자 입력 대기 필요
- ❌ **Graph/Report Generator 실제 구현**: 현재 Mock 응답만 반환

---

## 11. 다음 단계 (Phase 5)

### 11.1 우선순위 1: 핵심 에이전트 로직 구현

1. **DietAgent 완성**
   - 자연어 식단 입력 파싱 (LLM + Few-shot Examples)
   - 영양소 API 연동 (CalorieNinja 또는 USDA FoodData Central)
   - 일일 목표 대비 피드백 생성

2. **WorkoutAgent 완성**
   - 사용자 프로필 기반 운동 루틴 생성 알고리즘
   - 진행도에 따른 점진적 과부하 (Progressive Overload) 적용
   - ExerciseDB에서 적합한 운동 선택 로직

3. **CoachingAgent 완성**
   - OpenAI Embeddings를 사용한 쿼리 벡터화
   - FAISS 유사도 검색 최적화
   - 검색 결과 요약 생성 (LLM)

### 11.2 우선순위 2: HITL 실제 구현

- WebSocket을 통한 사용자 입력 대기
- Frontend에서 승인/거부 UI 구현
- HITL Handler에서 실제 대기 로직 (현재 자동 승인)

### 11.3 우선순위 3: Graph & Report Generator

- **Graph Generator**:
  - 체중/체지방 추세 그래프 (Chart.js, D3.js)
  - 운동량 히트맵
  - 영양소 분포 파이 차트

- **Report Generator**:
  - Markdown 형식 주간/월간 리포트
  - PDF 변환 옵션 (WeasyPrint)

### 11.4 우선순위 4: 프로덕션 배포

- PostgreSQL Checkpointer를 통한 세션 영속화
- Docker 컨테이너화
- Nginx 리버스 프록시 설정
- HTTPS 적용
- 로깅 및 모니터링 (Sentry, Prometheus)

---

## 12. 기술 스택 요약

### 12.1 Backend

- **Framework**: FastAPI 0.115.5
- **LLM Orchestration**: LangGraph 1.0 (StateGraph)
- **LLM**: OpenAI GPT-4o-mini
- **Database (Relational)**: SQLite (SQLAlchemy)
- **Database (Vector)**: FAISS (384 dimension)
- **WebSocket**: FastAPI WebSocket support
- **Checkpointer**: PostgreSQL (AsyncPostgresSaver) - Phase 4.1

### 12.2 Frontend

- **Framework**: React 19.2.0
- **Language**: TypeScript 4.9.5
- **Build Tool**: react-scripts 5.0.1 (Create React App)
- **Styling**: CSS (Gradient 디자인)

### 12.3 DevOps

- **Package Manager (Python)**: pip
- **Package Manager (JavaScript)**: npm
- **Version Control**: Git
- **.gitignore**: `frontend/node_modules/` (모듈만 제외)

---

## 13. 파일 구조

```
AI_PTmanager/beta_v001/
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPI 엔드포인트
│   │   ├── config/
│   │   │   └── system.py                    # 환경 설정
│   │   └── octostrator/
│   │       ├── states/
│   │       │   └── supervisor_state.py      # SupervisorState 정의
│   │       ├── supervisor/
│   │       │   ├── __init__.py
│   │       │   ├── graph.py                 # LangGraph 그래프 정의
│   │       │   └── nodes/
│   │       │       ├── intent_understanding.py  # Intent 분석
│   │       │       ├── planning.py              # Planning 노드
│   │       │       ├── executor.py              # Executor 노드
│   │       │       ├── hitl_handler.py          # HITL Handler
│   │       │       ├── aggregator.py            # Aggregator
│   │       │       ├── router.py                # Output Router
│   │       │       └── generators.py            # Chat/Graph/Report Generator
│   │       └── agents/
│   │           ├── __init__.py
│   │           ├── diet/
│   │           │   └── agent.py             # DietAgent
│   │           ├── workout/
│   │           │   └── agent.py             # WorkoutAgent
│   │           ├── schedule/
│   │           │   └── agent.py             # ScheduleAgent
│   │           ├── member_care/
│   │           │   └── agent.py             # MemberCareAgent
│   │           └── coaching/
│   │               └── agent.py             # CoachingAgent
│   └── database/
│       ├── relation_db/
│       │   ├── models.py                    # SQLAlchemy Models
│       │   ├── session.py                   # DB 세션
│       │   └── seed.py                      # Mock 데이터 생성
│       └── vector_db/
│           ├── faiss_manager.py             # FAISS Manager
│           ├── seed_faiss.py                # FAISS Mock 데이터
│           └── exercise_index/
│               ├── index.faiss
│               └── metadata.json
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.tsx                          # 메인 컴포넌트
│   │   ├── App.css                          # 스타일
│   │   └── index.tsx
│   ├── package.json
│   └── tsconfig.json
├── reports/
│   └── fitness_agents_report.md             # 이 레포트
├── .env                                     # 환경 변수 (OPENAI_API_KEY)
├── .gitignore                               # frontend/node_modules/ 제외
├── requirements.txt                         # Python 의존성
└── run_server.py                            # 서버 실행 스크립트
```

---

## 14. 핵심 코드 참조

### 14.1 SupervisorState 정의

**파일**: `backend/app/octostrator/states/supervisor_state.py:62`

```python
user_query: Optional[str]  # ← LangGraph가 유지하도록 TypedDict에 추가
```

### 14.2 Intent Understanding 카테고리

**파일**: `backend/app/octostrator/supervisor/nodes/intent_understanding.py:59-66`

```python
Classify the request into one of these categories:
1. "diet_query" - 식단 관련 조회/기록
2. "workout_query" - 운동 루틴 조회/추천
3. "schedule_query" - PT 스케줄 조회/예약
4. "member_report" - 회원 상태/진행률 조회
5. "coaching_search" - 운동/식단 자료 검색
6. "multi_step_task" - 복합 작업
7. "progress_comparison" - 진행률 비교
```

### 14.3 LangGraph 노드 추가

**파일**: `backend/app/octostrator/supervisor/graph.py:124-141`

```python
# Fitness Agents
workflow.add_node("diet", diet_agent_node)
workflow.add_node("workout", workout_agent_node)
workflow.add_node("schedule", schedule_agent_node)
workflow.add_node("member_care", member_care_agent_node)
workflow.add_node("coaching", coaching_agent_node)
```

### 14.4 CORS 설정

**파일**: `backend/app/main.py:38-44`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경: 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 14.5 /chat 엔드포인트

**파일**: `backend/app/main.py:88-108`

```python
result = await supervisor_graph.ainvoke({
    "user_query": request.message,
    "messages": [],
    "plan": [],
    "current_step": 0,
    "is_planning": True,
    "is_executing": False,
    "is_waiting_human": False,
    "aggregated_data": {},
    "output_format": "chat"
})

if "final_result" in result and result["final_result"]:
    response_content = result["final_result"]
elif "messages" in result and result["messages"]:
    response_content = result["messages"][-1].content
else:
    response_content = "응답을 생성할 수 없습니다."
```

---

## 15. 트러블슈팅

### 15.1 "Please provide a user request for analysis" 에러

**원인**: `user_query` 필드가 `SupervisorState` TypedDict에 정의되지 않아 LangGraph가 Drop

**해결**: `backend/app/octostrator/states/supervisor_state.py:62`에 추가
```python
user_query: Optional[str]
```

### 15.2 CORS 에러

**원인**: FastAPI에 CORS 미들웨어 미설정

**해결**: `backend/app/main.py:38-44`에 CORS 미들웨어 추가

### 15.3 npm run dev 실패

**원인**: Create React App은 `dev` 스크립트가 없음

**해결**: `npm start` 사용 (개발 서버)

### 15.4 포트 8000 이미 사용 중

**원인**: 다른 서버가 8000 포트 사용

**해결**: 기존 서버 종료 또는 `backend/app/config/system.py`에서 포트 변경

---

## 16. 참고 자료

- **LangGraph 1.0 문서**: https://langchain-ai.github.io/langgraph/
- **FastAPI 문서**: https://fastapi.tiangolo.com/
- **SQLAlchemy 문서**: https://docs.sqlalchemy.org/
- **FAISS 문서**: https://github.com/facebookresearch/faiss
- **React 문서**: https://react.dev/

---

## 17. 라이센스 및 기여

이 프로젝트는 개인 프로젝트입니다.

---

**작성자**: Claude (AI Assistant)
**최종 업데이트**: 2025-11-04
