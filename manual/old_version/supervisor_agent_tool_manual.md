# AI PT Manager - Supervisor, Agent, Tool 메뉴얼

작성일: 2025-11-04
버전: Phase 4.3 (Cognitive Nodes + Response Nodes 구조)

---

## 목차

1. [시스템 개요](#시스템-개요)
2. [Supervisor (슈퍼바이저)](#supervisor-슈퍼바이저)
3. [Agents (에이전트)](#agents-에이전트)
4. [Tools (툴)](#tools-툴)
5. [실행 흐름](#실행-흐름)
6. [State 관리](#state-관리)
7. [다이어그램](#다이어그램)

---

## 시스템 개요

### 아키텍처 패턴

**AI PT Manager**는 **Supervisor Pattern**을 사용한 **Multi-Agent System**입니다.

```
┌────────────────────────────────────────────────┐
│           Supervisor (오케스트레이터)            │
│  - 의도 파악                                    │
│  - 작업 계획 수립                               │
│  - Agent 동적 라우팅                            │
│  - 결과 종합 및 인사이트 생성                    │
└────────────────┬───────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
    ┌───▼────┐      ┌────▼────┐
    │ Agents │      │  Tools  │
    │        │─────▶│         │
    └────────┘      └─────────┘
```

### 핵심 개념

1. **Supervisor (슈퍼바이저)**
   - 중앙 제어 시스템으로 모든 Agent를 조율
   - LangGraph StateGraph 기반
   - 사용자 요청 → Agent 실행 → 결과 종합까지 전체 플로우 관리

2. **Agents (에이전트)**
   - 특정 도메인 작업을 수행하는 전문가
   - 각 Agent는 독립적이며 재사용 가능
   - 5개의 Fitness Agent: Diet, Workout, Schedule, MemberCare, Coaching

3. **Tools (툴)**
   - Agent가 사용하는 실제 비즈니스 로직
   - Database CRUD, 벡터 검색, 계산 로직 등
   - Agent와 Database 사이의 추상화 계층

### 기술 스택

- **Framework**: LangGraph 1.0 (TypedDict, Command 패턴)
- **LLM**: OpenAI GPT-4o-mini
- **Database**: SQLite (Mock), FAISS (Vector DB)
- **Backend**: FastAPI + WebSocket
- **State Management**: PostgreSQL Checkpointer (Phase 4.1+)

---

## Supervisor (슈퍼바이저)

### 목적

**Supervisor**는 사용자의 자연어 요청을 이해하고, 적절한 Agent들을 조합하여 실행하며, 결과를 종합하여 최종 응답을 생성하는 **중앙 오케스트레이터**입니다.

### 그래프 구조

LangGraph StateGraph로 구성된 **유향 비순환 그래프 (DAG)**:

```
START
  │
  ▼
Intent Understanding (의도 파악)
  │
  ▼
Planning (작업 계획 수립)
  │
  ▼
Executor (동적 라우팅) ◀────┐
  │                        │
  ├─▶ Diet Agent ─────────┤
  ├─▶ Workout Agent ──────┤
  ├─▶ Schedule Agent ─────┤
  ├─▶ MemberCare Agent ───┤
  ├─▶ Coaching Agent ─────┤
  ├─▶ HITL Handler ───────┤
  │                        │
  ▼                        │
Aggregator (결과 종합) ─────┘
  │
  ▼
Output Router (출력 형식 선택)
  │
  ├─▶ Chat Generator ─▶ END
  ├─▶ Graph Generator ─▶ END
  └─▶ Report Generator ─▶ END
```

### 노드 (Nodes)

Supervisor는 **Cognitive Nodes**와 **Response Nodes**로 구성됩니다.

#### 1. Cognitive Nodes (인지/분석 노드)

##### 1.1 Intent Understanding Node
- **목적**: 사용자 요청의 의도를 파악
- **입력**: 사용자 자연어 쿼리
- **출력**: 7가지 카테고리로 분류된 의도
  - `diet_query`: 식단 관련 질문
  - `workout_query`: 운동 루틴 질문
  - `schedule_query`: PT 스케줄 질문
  - `member_report`: 회원 상태 보고
  - `coaching_search`: 자료 검색
  - `multi_step_task`: 복합 작업 (여러 Agent 필요)
  - `progress_comparison`: 진행률 비교
- **기능**:
  - LLM을 사용하여 사용자 의도 분석
  - 단순 질문인지, 복합 작업인지 구분
  - Planning Node로 전환

##### 1.2 Planning Node
- **목적**: 사용자 요청을 실행 가능한 작업 단계로 분해
- **입력**: 사용자 의도 (Intent Understanding 결과)
- **출력**: TaskStep 리스트 (실행 계획)
- **기능**:
  - 복잡한 요청을 여러 개의 TaskStep으로 분해
  - 각 TaskStep에 적절한 Agent 할당
  - 실행 순서 결정
  - Executor Node로 전환

**TaskStep 구조**:
```
{
  "step_id": 1,
  "agent": "member_care",
  "description": "김철수 회원 정보 조회",
  "status": "pending",
  "tool": None,
  "result": None
}
```

##### 1.3 Executor Node
- **목적**: Plan에 따라 Agent를 순차적으로 실행
- **입력**: Plan (TaskStep 리스트), current_step (현재 단계)
- **출력**: Command (다음 Agent 지정)
- **기능**:
  - Command 패턴으로 동적 라우팅
  - 각 Agent 실행 후 Executor로 복귀
  - 모든 TaskStep 완료 시 Aggregator로 전환
  - 에러 처리 및 상태 관리

**동작 방식**:
```
1. current_step 확인
2. plan[current_step] 가져오기
3. TaskStep.agent에 따라 Command 반환
   - "diet" → Command(goto="diet")
   - "workout" → Command(goto="workout")
   - ...
4. Agent 실행 완료 후 Executor로 복귀
5. current_step += 1
6. 반복
7. 모든 TaskStep 완료 시 Command(goto="aggregator")
```

##### 1.4 Aggregator Node
- **목적**: 모든 Agent 결과를 종합하여 구조화된 데이터 생성
- **입력**: Plan (모든 TaskStep의 result 포함)
- **출력**: aggregated_data (구조화된 데이터), output_format (출력 형식)
- **기능**:
  - 각 Agent 결과를 섹션별로 정리
  - LLM을 사용하여 인사이트 생성
  - 권장사항 및 요약 제공
  - Output Router로 전환

**Aggregated Data 예시**:
```json
{
  "summary": "김철수 회원은 2주간 체지방 감소와 근육량 증가...",
  "sections": {
    "member_info": {...},
    "workout_analysis": {...},
    "diet_analysis": {...},
    "schedule_info": {...}
  },
  "insights": [
    "체지방 감소와 근육 증가가 동시에 진행 중",
    "칼로리 섭취를 늘려야 함"
  ],
  "recommendations": [
    "다음 PT에서 하체 집중 훈련",
    "식사 횟수 증가 (2끼 → 5-6끼)"
  ]
}
```

#### 2. Response Nodes (응답 생성 노드)

##### 2.1 HITL Handler Node
- **목적**: Human-in-the-Loop, 사용자 승인 대기
- **입력**: hitl_question (승인 요청 질문)
- **출력**: hitl_response (사용자 응답)
- **기능**:
  - LangGraph interrupt()를 사용하여 실제 대기
  - Checkpointer에 State 저장
  - 사용자 응답 수신 후 재개
  - Executor로 복귀하여 다음 TaskStep 실행

**사용 예시**:
```
User: "김철수 회원에게 PT 예약 확인 메시지 보내줘"
  → Planning: [Step 1: 스케줄 조회, Step 2: HITL (승인), Step 3: 메시지 발송]
  → Executor → Schedule Agent (Step 1) → Executor
  → HITL Handler: "다음 메시지를 발송할까요? [메시지 내용]"
  → (사용자 승인 대기)
  → User: "네, 발송해주세요"
  → HITL Handler → Executor
  → Message Agent (Step 3) → Executor → Aggregator
```

##### 2.2 Output Router Node
- **목적**: 출력 형식에 따라 적절한 Generator 선택
- **입력**: output_format ("chat", "graph", "report")
- **출력**: Command (다음 Generator 지정)
- **기능**:
  - Chat Generator: 일반 대화형 답변 (기본값)
  - Graph Generator: 시각화 데이터 (D3.js, Cytoscape)
  - Report Generator: 상세 Markdown 보고서

##### 2.3 Chat Generator Node
- **목적**: 자연스러운 대화형 답변 생성
- **입력**: aggregated_data
- **출력**: final_result (자연어 답변)
- **기능**:
  - LLM을 사용하여 친근한 톤으로 재작성
  - 사용자 친화적인 형식으로 변환
  - 이모지 및 포맷팅 추가

##### 2.4 Graph Generator Node
- **목적**: 시각화를 위한 그래프 데이터 생성
- **입력**: aggregated_data
- **출력**: final_result (JSON 그래프 데이터)
- **기능**:
  - D3.js 또는 Cytoscape.js 포맷으로 변환
  - 노드와 엣지 생성
  - 진행률 그래프, 영양소 차트 등

**Graph Data 예시**:
```json
{
  "type": "line_chart",
  "title": "체중 변화 추이",
  "data": [
    {"date": "2025-10-28", "weight": 75.5},
    {"date": "2025-11-04", "weight": 76.0}
  ],
  "xAxis": "date",
  "yAxis": "weight"
}
```

##### 2.5 Report Generator Node
- **목적**: 상세한 Markdown 보고서 생성
- **입력**: aggregated_data
- **출력**: final_result (Markdown 보고서)
- **기능**:
  - 구조화된 Markdown 문서 생성
  - 표, 차트, 섹션 구분
  - 파일로 저장 가능

### State (SupervisorState)

**SupervisorState**는 전체 그래프의 상태를 관리하는 TypedDict입니다.

#### State 필드

| 필드 | 타입 | 목적 | 업데이트 시점 |
|------|------|------|--------------|
| `messages` | Sequence[BaseMessage] | 대화 히스토리 | 모든 노드에서 메시지 추가 |
| `user_query` | Optional[str] | 사용자 입력 쿼리 | 초기 입력 시 |
| `user_intent` | Optional[str] | 파악된 의도 | Intent Understanding 완료 시 |
| `plan` | List[dict] | 작업 계획 (TaskStep 리스트) | Planning 완료 시, Agent 실행 시 |
| `current_step` | int | 현재 실행 중인 단계 | Executor에서 증가 |
| `is_planning` | bool | 계획 수립 중인가? | Intent Understanding → Planning |
| `is_executing` | bool | 실행 중인가? | Planning → Executor |
| `is_waiting_human` | bool | HITL 대기 중인가? | HITL Handler 진입/탈출 시 |
| `aggregated_data` | Optional[dict] | 구조화된 결과 데이터 | Aggregator 완료 시 |
| `output_format` | str | 출력 형식 | Aggregator 결정 시 |
| `final_result` | Optional[str] | 최종 결과 | Generator 완료 시 |

#### State 업데이트 흐름

```
초기 State:
{
  "messages": [HumanMessage("김철수 회원 운동 기록 보여줘")],
  "user_query": "김철수 회원 운동 기록 보여줘",
  "plan": [],
  "current_step": 0
}

Intent Understanding 후:
{
  "user_intent": "workout_query - 특정 회원의 운동 기록 조회",
  "is_planning": True
}

Planning 후:
{
  "plan": [
    {"step_id": 1, "agent": "workout", "description": "김철수 운동 기록 조회", "status": "pending"}
  ],
  "current_step": 0,
  "is_executing": True
}

Agent 실행 후:
{
  "plan": [
    {"step_id": 1, "agent": "workout", "status": "completed", "result": "[WorkoutAgent] ..."}
  ],
  "current_step": 1
}

Aggregator 후:
{
  "aggregated_data": {"summary": "...", "sections": {...}},
  "output_format": "chat"
}

Generator 후:
{
  "final_result": "김철수 회원의 최근 운동 기록은 다음과 같습니다..."
}
```

### 기능

#### 1. 동적 Multi-Agent 조합

- 사용자 요청에 따라 필요한 Agent만 실행
- Agent 순서는 Planning Node가 자동 결정
- 단일 Agent 또는 복수 Agent 조합 가능

**예시**:
- 단순 질문: "오늘 먹은 음식 보여줘" → DietAgent만 실행
- 복합 질문: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘" → MemberCare + Workout + Diet + Schedule Agent 순차 실행

#### 2. Command 패턴 기반 동적 라우팅

- Executor가 Command 객체를 반환하여 다음 노드 지정
- 각 Agent는 Executor로 복귀하여 다음 TaskStep 실행
- 순환 구조로 모든 TaskStep을 순차 처리

#### 3. State 영속화 (Checkpointer)

- PostgreSQL Checkpointer 사용 (Phase 4.1+)
- thread_id 기반 세션 관리
- HITL 대기 중에도 State 유지
- 재개 시 이전 상태에서 계속 실행

#### 4. 인사이트 생성

- Aggregator가 LLM을 사용하여 인사이트 생성
- 단순 결과 나열이 아닌 의미 있는 분석 제공
- 권장사항 및 다음 액션 제안

#### 5. 유연한 출력 형식

- Chat: 대화형 답변
- Graph: 시각화 데이터 (프론트엔드 차트)
- Report: Markdown 보고서 (파일 저장 가능)

---

## Agents (에이전트)

### 목적

**Agent**는 특정 도메인의 작업을 수행하는 전문가입니다. 각 Agent는 독립적이며, Tool을 사용하여 실제 비즈니스 로직을 실행합니다.

### Agent 구조

모든 Agent는 동일한 구조를 따릅니다:

```
async def {agent_name}_agent_node(state: SupervisorState) -> Dict:
    """Agent 노드 (Tool 기반)

    1. State에서 plan, current_step 추출
    2. Tool 호출하여 데이터 조회/처리
    3. 결과 포맷팅
    4. State 업데이트 (status: completed, result 저장)
    5. current_step 증가
    6. Executor로 복귀
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    try:
        # Tool 호출
        data = some_tool(...)

        # 결과 포맷팅
        result = f"[{AgentName}] {step['description']}\n\n{data}"

    except Exception as e:
        result = f"[{AgentName}] Error: {str(e)}"

    # State 업데이트
    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
```

### 5개의 Fitness Agents

#### 1. DietAgent (식단 에이전트)

**노드**: `diet_agent_node`

**목적**: 식단 기록 및 영양소 분석

**기능**:
- 식단 기록 조회
- 일일 영양소 집계 (칼로리, 단백질, 탄수화물, 지방)
- 영양소 분석 및 피드백

**사용 Tools**:
- `get_meal_logs(user_id, limit)`: 식단 기록 조회
- `get_daily_nutrition_summary(user_id)`: 일일 영양소 집계

**입력**:
- `state["user_id"]`: 사용자 ID (Mock: 1)

**출력**:
```
[DietAgent] 사용자의 최근 식단 기록 조회

최근 식단 기록:
- breakfast (2025-11-04 08:30:00): 계란 3개, 현미밥 1공기, 김치 50g
  영양소: 450kcal, 단백질 30g

오늘의 총 섭취량:
- 칼로리: 800kcal
- 단백질: 75g
...
```

---

#### 2. WorkoutAgent (운동 에이전트)

**노드**: `workout_agent_node`

**목적**: 운동 루틴 추천 및 기록 관리

**기능**:
- 운동 기록 조회
- 운동 데이터베이스 검색
- 개인화된 운동 프로그램 제안

**사용 Tools**:
- `get_workout_history(user_id, limit)`: 운동 기록 조회
- `search_exercises(limit)`: 운동 데이터베이스 검색

**입력**:
- `state["user_id"]`: 사용자 ID

**출력**:
```
[WorkoutAgent] 사용자의 최근 운동 기록 조회

최근 운동 루틴:
- legs (2025-11-04):
  • 스쿼트: 4세트 x 10회 (80kg)
  • 런지: 3세트 x 12회

추천 운동 (3개):
- 스쿼트 (legs, beginner)
...
```

---

#### 3. ScheduleAgent (스케줄 에이전트)

**노드**: `schedule_agent_node`

**목적**: PT 스케줄 관리

**기능**:
- PT 스케줄 조회
- 예약 생성/변경
- 회원 및 트레이너 정보 조회

**사용 Tools**:
- `get_schedules(start_date, limit)`: 스케줄 조회
- `get_member_info(user_id)`: 회원 정보 조회

**입력**:
- `start_date`: 조회 시작 날짜 (기본: 오늘)

**출력**:
```
[ScheduleAgent] 예정된 PT 스케줄 조회

예정된 PT 스케줄 (2개):
- 2025-11-05 15:00:00
  회원: 김철수
  트레이너: 트레이너_홍길동
  상태: confirmed
  메모: 하체 집중 PT
...
```

---

#### 4. MemberCareAgent (회원 관리 에이전트)

**노드**: `member_care_agent_node`

**목적**: 회원 상태 리포팅 및 진행률 분석

**기능**:
- 전체 회원 목록 조회
- 회원 진행률 조회 (체중, 체지방률, 근육량)
- 진행률 비교 및 변화 분석

**사용 Tools**:
- `get_all_members(limit)`: 전체 회원 조회
- `get_member_progress(user_id, limit)`: 진행률 조회
- `get_progress_comparison(user_id)`: 진행률 비교

**입력**:
- `limit`: 조회할 회원 수 (기본: 10)

**출력**:
```
[MemberCareAgent] 전체 회원 현황 조회

회원 현황 (3명):

📊 김철수 (kim@example.com)
   목표: muscle_gain, 레벨: intermediate
   최근 측정: 2025-11-04
   - 체중: 76.0kg
   - 체지방률: 17.8%
   - 근육량: 61.0kg
   변화: 체중 +0.5kg, 체지방 -0.7%, 근육 +0.8kg
...
```

---

#### 5. CoachingAgent (코칭 에이전트)

**노드**: `coaching_agent_node`

**목적**: 전문 자료 검색 및 북마크 관리

**기능**:
- FAISS 벡터 검색으로 운동 자세 영상, 논문 검색
- 북마크 조회 및 관리
- 자료 요약 및 제공

**사용 Tools**:
- `search_materials(query, top_k)`: FAISS 벡터 검색
- `get_bookmarks(user_id, limit)`: 북마크 조회

**입력**:
- `state["user_query"]`: 검색 쿼리 (예: "운동 자세")

**출력**:
```
[CoachingAgent] 운동 자세 관련 자료 검색

검색 결과 (3개):
1. 스쿼트 정확한 자세 가이드 (video)
   설명: 무릎과 허리를 보호하는 올바른 스쿼트 자세
   URL: https://youtube.com/squat_form
   유사도 점수: 0.892

저장된 북마크 (2개):
- 초보자를 위한 PT 가이드 (guide)
...
```

---

### Agent 특징

#### 1. 독립성
- 각 Agent는 독립적으로 실행 가능
- 다른 Agent에 의존하지 않음
- 재사용 및 조합 가능

#### 2. Tool 기반
- Agent는 직접 Database에 접근하지 않음
- Tool을 통해 비즈니스 로직 실행
- Agent는 오케스트레이션과 포맷팅에만 집중

#### 3. 비동기 실행
- 모든 Agent는 async 함수
- 비동기 I/O로 성능 향상

#### 4. 에러 처리
- Try-except로 모든 에러 캐치
- 에러 발생 시에도 State 업데이트
- 에러 메시지를 result에 저장

#### 5. 상태 관리
- 각 Agent는 TaskStep의 status를 "completed"로 변경
- result 필드에 실행 결과 저장
- current_step 증가하여 Executor로 복귀

---

## Tools (툴)

### 목적

**Tool**은 Agent가 사용하는 실제 비즈니스 로직입니다. Database CRUD, 계산, 외부 API 호출 등을 담당합니다.

### Tool 설계 원칙

1. **단일 책임 원칙**: 하나의 Tool은 하나의 명확한 작업만 수행
2. **순수 함수**: 입력에 대해 예측 가능한 출력 반환
3. **에러 처리**: 모든 Tool은 명확한 에러 메시지 제공
4. **타입 안정성**: 입력/출력 타입 명시
5. **독립성**: Tool 간 의존성 최소화

### Tool 구조

```python
def tool_name(param1: Type1, param2: Type2) -> ReturnType:
    """Tool 설명

    Args:
        param1: 파라미터 설명
        param2: 파라미터 설명

    Returns:
        ReturnType: 반환값 설명

    Raises:
        Exception: 에러 상황 설명
    """
    try:
        # 1. 입력 검증
        if not param1:
            raise ValueError("param1 is required")

        # 2. 비즈니스 로직 실행
        with get_db() as db:
            data = db.query(...).filter(...).all()

        # 3. 결과 포맷팅
        result = [{"field": item.field} for item in data]

        return result

    except Exception as e:
        raise Exception(f"Tool 실패: {str(e)}")
```

### Tool 카테고리

#### 1. Diet Tools (식단 툴)

**파일**: `backend/app/octostrator/tools/diet_tools.py`

##### 1.1 get_meal_logs
- **목적**: 식단 기록 조회
- **파라미터**: `user_id`, `limit`, `date_range`
- **반환**: List[Dict] (식단 기록 리스트)
- **기능**: SQLite에서 MealLog 테이블 조회

##### 1.2 save_meal_log
- **목적**: 식단 기록 저장
- **파라미터**: `user_id`, `meal_type`, `foods`, `nutrition`
- **반환**: Dict (저장된 기록)
- **기능**: MealLog 테이블에 INSERT

##### 1.3 get_daily_nutrition_summary
- **목적**: 일일 영양소 집계
- **파라미터**: `user_id`, `date`
- **반환**: Dict (총 칼로리, 단백질, 탄수화물, 지방)
- **기능**: 오늘 날짜의 모든 식단 기록을 집계

---

#### 2. Workout Tools (운동 툴)

**파일**: `backend/app/octostrator/tools/workout_tools.py`

##### 2.1 get_workout_history
- **목적**: 운동 기록 조회
- **파라미터**: `user_id`, `limit`, `date_range`
- **반환**: List[Dict] (운동 루틴 리스트)
- **기능**: WorkoutRoutine 테이블 조회

##### 2.2 save_workout_routine
- **목적**: 운동 루틴 저장
- **파라미터**: `user_id`, `muscle_group`, `exercises`
- **반환**: Dict (저장된 루틴)
- **기능**: WorkoutRoutine 테이블에 INSERT

##### 2.3 search_exercises
- **목적**: 운동 데이터베이스 검색
- **파라미터**: `muscle_group`, `difficulty`, `limit`
- **반환**: List[Dict] (운동 리스트)
- **기능**: ExerciseDB 테이블에서 필터링 조회

##### 2.4 get_exercise_by_name
- **목적**: 특정 운동 정보 조회
- **파라미터**: `name`
- **반환**: Dict (운동 정보)
- **기능**: ExerciseDB 테이블에서 이름으로 조회

---

#### 3. Schedule Tools (스케줄 툴)

**파일**: `backend/app/octostrator/tools/schedule_tools.py`

##### 3.1 get_schedules
- **목적**: PT 스케줄 조회
- **파라미터**: `start_date`, `end_date`, `user_id`, `trainer_id`, `limit`
- **반환**: List[Dict] (스케줄 리스트)
- **기능**: Schedule 테이블에서 날짜 범위 조회

##### 3.2 create_schedule
- **목적**: PT 스케줄 생성
- **파라미터**: `user_id`, `trainer_id`, `date`, `duration_minutes`, `notes`
- **반환**: Dict (생성된 스케줄)
- **기능**: Schedule 테이블에 INSERT

##### 3.3 update_schedule
- **목적**: 스케줄 변경
- **파라미터**: `schedule_id`, `date`, `status`, `notes`
- **반환**: Dict (변경된 스케줄)
- **기능**: Schedule 테이블 UPDATE

##### 3.4 delete_schedule
- **목적**: 스케줄 삭제
- **파라미터**: `schedule_id`
- **반환**: bool (성공 여부)
- **기능**: Schedule 테이블 DELETE

---

#### 4. MemberCare Tools (회원 관리 툴)

**파일**: `backend/app/octostrator/tools/member_care_tools.py`

##### 4.1 get_member_info
- **목적**: 회원 정보 조회
- **파라미터**: `user_id`
- **반환**: Dict (회원 정보)
- **기능**: User 테이블 조회

##### 4.2 get_all_members
- **목적**: 전체 회원 목록 조회
- **파라미터**: `limit`, `goal`, `level`
- **반환**: List[Dict] (회원 리스트)
- **기능**: User 테이블 조회 (필터링 가능)

##### 4.3 get_member_progress
- **목적**: 회원 진행률 조회
- **파라미터**: `user_id`, `limit`, `date_range`
- **반환**: List[Dict] (진행률 기록)
- **기능**: MemberProgress 테이블 조회

##### 4.4 save_member_progress
- **목적**: 진행률 기록 저장
- **파라미터**: `user_id`, `weight`, `body_fat_percentage`, `muscle_mass`, `notes`
- **반환**: Dict (저장된 기록)
- **기능**: MemberProgress 테이블에 INSERT

##### 4.5 get_progress_comparison
- **목적**: 진행률 비교
- **파라미터**: `user_id`
- **반환**: Dict (최신 vs 이전 기록 비교)
- **기능**: 최신 2개 기록을 비교하여 변화량 계산

---

#### 5. Coaching Tools (코칭 툴)

**파일**: `backend/app/octostrator/tools/coaching_tools.py`

##### 5.1 search_materials
- **목적**: FAISS 벡터 검색
- **파라미터**: `query`, `top_k`
- **반환**: List[Dict] (검색 결과)
- **기능**: 쿼리를 임베딩하여 FAISS에서 유사도 검색

##### 5.2 get_bookmarks
- **목적**: 북마크 조회
- **파라미터**: `user_id`, `category`, `limit`
- **반환**: List[Dict] (북마크 리스트)
- **기능**: Bookmark 테이블 조회

##### 5.3 save_bookmark
- **목적**: 북마크 저장
- **파라미터**: `user_id`, `title`, `url`, `category`, `description`
- **반환**: Dict (저장된 북마크)
- **기능**: Bookmark 테이블에 INSERT

##### 5.4 delete_bookmark
- **목적**: 북마크 삭제
- **파라미터**: `bookmark_id`
- **반환**: bool (성공 여부)
- **기능**: Bookmark 테이블 DELETE

##### 5.5 embed_query
- **목적**: 쿼리 임베딩 생성
- **파라미터**: `text`
- **반환**: List[float] (임베딩 벡터)
- **기능**: OpenAI Embedding API 호출

---

#### 6. Common Tools (공통 툴)

**파일**: `backend/app/octostrator/tools/common_tools.py`

##### 6.1 format_date
- **목적**: 날짜 포맷팅
- **파라미터**: `date`, `format_string`
- **반환**: str (포맷된 날짜)
- **기능**: datetime을 문자열로 변환

##### 6.2 calculate_bmi
- **목적**: BMI 계산
- **파라미터**: `weight`, `height`
- **반환**: float (BMI)
- **기능**: 체중(kg) / 신장(m)^2

##### 6.3 calculate_calories
- **목적**: 칼로리 계산
- **파라미터**: `foods` (음식 리스트)
- **반환**: int (총 칼로리)
- **기능**: 각 음식의 칼로리를 합산

---

### Tool 특징

#### 1. Database 추상화
- Agent는 Database 구조를 몰라도 됨
- Tool이 SQL 쿼리 및 ORM 처리
- Database 변경 시 Tool만 수정

#### 2. 재사용성
- 여러 Agent가 동일한 Tool 사용 가능
- 예: `get_member_info`는 ScheduleAgent와 MemberCareAgent가 모두 사용

#### 3. 테스트 용이성
- Tool은 순수 함수로 단위 테스트 가능
- Mock Database로 테스트 가능

#### 4. Phase 2 준비 (LLM Tool Calling)
- 현재는 Agent가 Tool을 직접 호출 (Phase 1)
- Phase 2에서는 LLM이 Tool을 동적으로 선택하여 호출
- Tool 시그니처와 Docstring이 LLM의 판단 기준

---

## 실행 흐름

### 전체 실행 흐름

```
1. 사용자 입력
   User: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘"

2. Intent Understanding
   → 의도 파악: multi_step_task
   → 복합 작업 (여러 Agent 필요)

3. Planning
   → TaskStep 리스트 생성:
     Step 1: member_care - 김철수 회원 정보 조회
     Step 2: workout - 김철수 운동 기록 조회
     Step 3: diet - 김철수 식단 기록 조회
     Step 4: schedule - PT 스케줄 확인

4. Executor (Step 1)
   → Command(goto="member_care")
   → MemberCareAgent 실행
     - get_member_info(user_id=1)
     - get_member_progress(user_id=1)
   → State 업데이트: plan[0]["status"] = "completed", current_step = 1
   → Executor로 복귀

5. Executor (Step 2)
   → Command(goto="workout")
   → WorkoutAgent 실행
     - get_workout_history(user_id=1)
   → State 업데이트: plan[1]["status"] = "completed", current_step = 2
   → Executor로 복귀

6. Executor (Step 3)
   → Command(goto="diet")
   → DietAgent 실행
     - get_meal_logs(user_id=1)
     - get_daily_nutrition_summary(user_id=1)
   → State 업데이트: plan[2]["status"] = "completed", current_step = 3
   → Executor로 복귀

7. Executor (Step 4)
   → Command(goto="schedule")
   → ScheduleAgent 실행
     - get_schedules(start_date=today)
   → State 업데이트: plan[3]["status"] = "completed", current_step = 4
   → Executor로 복귀

8. Executor (모든 TaskStep 완료)
   → Command(goto="aggregator")

9. Aggregator
   → 모든 Agent 결과 수집
   → LLM으로 인사이트 생성
   → aggregated_data 생성
   → output_format 결정 (chat)
   → Output Router로 전환

10. Output Router
    → output_format = "chat"
    → Command(goto="chat_generator")

11. Chat Generator
    → aggregated_data를 자연어로 변환
    → final_result 생성
    → END

12. 사용자에게 응답
    → final_result 반환
```

### 단일 Agent 실행 흐름

```
User: "오늘 먹은 음식 보여줘"

1. Intent Understanding
   → 의도: diet_query

2. Planning
   → TaskStep 1개:
     Step 1: diet - 사용자의 최근 식단 기록 조회

3. Executor
   → Command(goto="diet")

4. DietAgent
   → get_meal_logs(user_id=1)
   → get_daily_nutrition_summary(user_id=1)
   → result 생성

5. Executor
   → 모든 TaskStep 완료
   → Command(goto="aggregator")

6. Aggregator → Output Router → Chat Generator → END
```

### HITL 포함 실행 흐름

```
User: "김철수 회원에게 PT 변경 메시지 보내줘"

1-3. Intent → Planning → Executor
   → TaskStep:
     Step 1: schedule - 스케줄 조회
     Step 2: hitl - 메시지 승인
     Step 3: message - 메시지 발송

4. Executor → ScheduleAgent → Executor

5. Executor (Step 2)
   → Command(goto="hitl_handler")

6. HITL Handler
   → interrupt("다음 메시지를 발송할까요? [메시지 내용]")
   → State 저장 (Checkpointer)
   → 대기...

7. 사용자 응답
   User: "네, 발송해주세요"
   → graph.ainvoke({"messages": [HumanMessage("네")]}, config)

8. HITL Handler 재개
   → hitl_response 저장
   → Executor로 복귀

9. Executor → MessageAgent → Executor → Aggregator → END
```

---

## State 관리

### State 업데이트 규칙

#### 1. messages 필드
- **타입**: `Annotated[Sequence[BaseMessage], add_messages]`
- **특징**: add_messages로 자동 병합
- **업데이트**:
  ```python
  return {"messages": [AIMessage(content="...")]}
  # 기존 messages에 추가됨 (덮어쓰지 않음)
  ```

#### 2. plan 필드
- **타입**: `List[dict]`
- **특징**: 전체 plan을 복사하여 수정 후 반환
- **업데이트**:
  ```python
  plan = state["plan"]  # 복사
  plan[current_step]["status"] = "completed"
  plan[current_step]["result"] = "..."
  return {"plan": plan}  # 전체 plan 업데이트
  ```

#### 3. current_step 필드
- **타입**: `int`
- **특징**: Executor와 Agent가 증가
- **업데이트**:
  ```python
  return {"current_step": current_step + 1}
  ```

#### 4. 기타 필드
- **덮어쓰기 방식**: 새 값으로 완전히 대체
- 예: `user_intent`, `aggregated_data`, `final_result`

### State 영속화 (Checkpointer)

#### PostgreSQL Checkpointer

**Phase 4.1+**에서는 AsyncPostgresSaver를 사용하여 State를 영속화합니다.

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Checkpointer 생성
checkpointer = AsyncPostgresSaver.from_conn_string(
    conn_string="postgresql://user:pass@localhost/db"
)

# Graph 컴파일
graph = build_supervisor_graph(context, checkpointer=checkpointer)

# 실행 (thread_id로 세션 관리)
config = {"configurable": {"thread_id": "user_123_session_1"}}
result = await graph.ainvoke(initial_state, config)
```

#### Thread ID 기반 세션 관리

- 각 사용자 세션은 고유한 `thread_id`를 가짐
- 동일한 `thread_id`로 재실행 시 이전 State에서 계속
- HITL 대기 중에도 State 유지

#### State 재개

```python
# 1. HITL 대기 중 State 저장됨
# 2. 사용자 응답 준비
# 3. 동일한 thread_id로 재개
config = {"configurable": {"thread_id": "user_123_session_1"}}
result = await graph.ainvoke(None, config)  # 자동 승인
# 또는
result = await graph.ainvoke(
    {"messages": [HumanMessage("네, 발송해주세요")]},
    config
)
```

---

## 다이어그램

### 1. 전체 시스템 아키텍처

```
┌────────────────────────────────────────────────────────────┐
│                        Frontend                            │
│                    (React + TypeScript)                    │
└──────────────────────────┬─────────────────────────────────┘
                           │ WebSocket
                           ▼
┌────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                       │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │               Supervisor Graph                       │ │
│  │                                                      │ │
│  │  START → Intent → Planning → Executor → Agents     │ │
│  │                                 ↓                    │ │
│  │                            Aggregator → Router      │ │
│  │                                          ↓           │ │
│  │                                      Generators      │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                │
│  ┌────────────────────────┴─────────────────────────────┐ │
│  │                      Tools                           │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                      Database Layer                        │
│                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐│
│  │  SQLite (Mock) │  │  FAISS Vector  │  │  PostgreSQL  ││
│  │  Relational DB │  │  Search Index  │  │  Checkpointer││
│  └────────────────┘  └────────────────┘  └──────────────┘│
└────────────────────────────────────────────────────────────┘
```

### 2. Supervisor Graph 상세

```
                         START
                           │
                           ▼
                    ┌──────────────┐
                    │    Intent    │
                    │ Understanding│
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Planning   │
                    └──────┬───────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │                                      │
        │           Executor (Loop)            │
        │                                      │
        └─┬──────────────────────────────────┬─┘
          │                                  │
          │ Command(goto="agent_name")       │
          │                                  │
    ┌─────┼─────┬─────┬─────┬──────┬────────┼────┐
    │     │     │     │     │      │        │    │
    ▼     ▼     ▼     ▼     ▼      ▼        ▼    ▼
  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐  ┌───┐  ┌────┐
  │Diet│Workout│Sche│Memb│Coach│  │HITL│  │END │
  │   │ │   │ │dule│er  │ing │  │    │  │(error)
  │   │ │   │ │    │Care│    │  │    │  │    │
  └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘  └─┬─┘  └────┘
    │     │     │     │     │      │
    └─────┼─────┴─────┴─────┴──────┘
          │ return to Executor
          │
          ▼
        Executor (current_step++)
          │
          │ All steps completed?
          ▼
    ┌──────────────┐
    │  Aggregator  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │Output Router │
    └──────┬───────┘
           │
     ┌─────┼─────┐
     │     │     │
     ▼     ▼     ▼
  ┌────┐┌────┐┌────┐
  │Chat││Graph││Report│
  │Gen ││Gen ││Gen  │
  └─┬──┘└─┬──┘└─┬──┘
    │     │     │
    └─────┼─────┘
          │
          ▼
         END
```

### 3. Agent - Tool - Database 관계

```
┌──────────────────────────────────────────────────────────┐
│                         Agent                            │
│                                                          │
│  async def agent_node(state):                           │
│      # 1. State에서 정보 추출                            │
│      plan = state["plan"]                               │
│      current_step = state["current_step"]               │
│                                                          │
│      # 2. Tool 호출                                      │
│      data = tool_function(params)                       │
│                                                          │
│      # 3. 결과 포맷팅                                    │
│      result = format_result(data)                       │
│                                                          │
│      # 4. State 업데이트                                 │
│      return {"plan": ..., "current_step": ...}          │
└───────────────────────┬──────────────────────────────────┘
                        │ Tool 호출
                        ▼
┌──────────────────────────────────────────────────────────┐
│                         Tool                             │
│                                                          │
│  def tool_function(param1, param2):                     │
│      # 1. 입력 검증                                      │
│      validate(param1, param2)                           │
│                                                          │
│      # 2. Database 접근                                  │
│      with get_db() as db:                               │
│          data = db.query(Model).filter(...).all()       │
│                                                          │
│      # 3. 결과 가공                                      │
│      result = process(data)                             │
│                                                          │
│      return result                                      │
└───────────────────────┬──────────────────────────────────┘
                        │ Database 쿼리
                        ▼
┌──────────────────────────────────────────────────────────┐
│                       Database                           │
│                                                          │
│  ┌────────────────┐  ┌────────────────┐                │
│  │  SQLite Tables │  │  FAISS Index   │                │
│  │  - User        │  │  - Embeddings  │                │
│  │  - MealLog     │  │  - Materials   │                │
│  │  - Workout     │  │                │                │
│  │  - Schedule    │  │                │                │
│  │  - Progress    │  │                │                │
│  └────────────────┘  └────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

### 4. State 변화 흐름

```
Initial State:
┌────────────────────────────────────┐
│ messages: [HumanMessage("...")]   │
│ user_query: "..."                 │
│ plan: []                          │
│ current_step: 0                   │
└────────────────────────────────────┘
           │
           ▼ Intent Understanding
┌────────────────────────────────────┐
│ user_intent: "multi_step_task"    │
│ is_planning: True                 │
└────────────────────────────────────┘
           │
           ▼ Planning
┌────────────────────────────────────┐
│ plan: [                           │
│   {step: 1, agent: "diet", ...},  │
│   {step: 2, agent: "workout",...} │
│ ]                                 │
│ current_step: 0                   │
│ is_executing: True                │
└────────────────────────────────────┘
           │
           ▼ Executor → Agent 1
┌────────────────────────────────────┐
│ plan: [                           │
│   {step: 1, status: "completed",  │
│    result: "[DietAgent] ..."},    │
│   {step: 2, status: "pending"}    │
│ ]                                 │
│ current_step: 1                   │
└────────────────────────────────────┘
           │
           ▼ Executor → Agent 2
┌────────────────────────────────────┐
│ plan: [                           │
│   {step: 1, status: "completed"}, │
│   {step: 2, status: "completed",  │
│    result: "[WorkoutAgent] ..."}  │
│ ]                                 │
│ current_step: 2                   │
└────────────────────────────────────┘
           │
           ▼ Aggregator
┌────────────────────────────────────┐
│ aggregated_data: {                │
│   summary: "...",                 │
│   sections: {...},                │
│   insights: [...]                 │
│ }                                 │
│ output_format: "chat"             │
└────────────────────────────────────┘
           │
           ▼ Chat Generator
┌────────────────────────────────────┐
│ final_result: "김철수 회원의..."  │
└────────────────────────────────────┘
```

### 5. Tool 호출 시퀀스

```
Agent                Tool               Database
  │                   │                    │
  │  call tool()      │                    │
  ├──────────────────▶│                    │
  │                   │  query DB          │
  │                   ├───────────────────▶│
  │                   │                    │
  │                   │  return rows       │
  │                   │◀───────────────────┤
  │                   │                    │
  │                   │  process data      │
  │                   │                    │
  │  return result    │                    │
  │◀──────────────────┤                    │
  │                   │                    │
  │  format result    │                    │
  │                   │                    │
  │  update State     │                    │
  │                   │                    │
```

---

## 부록

### Phase 진행 현황

| Phase | 상태 | 설명 |
|-------|------|------|
| Phase 1 | ✅ 완료 | Tool 기반 리팩토링 (Agent와 Database 분리) |
| Phase 2 | 🔄 진행 중 | LLM Tool Calling (Agent가 동적으로 Tool 선택) |
| Phase 3 | ✅ 완료 | Executor + Agents (Command 패턴) |
| Phase 3.5 | ✅ 완료 | Aggregator + Generator 추가 |
| Phase 3.6 | ✅ 완료 | Graph & Report Generator 추가 |
| Phase 4.1 | ✅ 완료 | PostgreSQL Checkpointer 통합 |
| Phase 4.2 | ✅ 완료 | HITL interrupt() 구현 |
| Phase 4.3 | ✅ 완료 | Cognitive/Response Nodes 구조 개선 |

### 향후 개발 계획

#### Phase 2 완료 (LLM Tool Calling)
- Agent가 LLM을 통해 Tool을 동적으로 선택
- Structured Output으로 Tool 호출 결정
- 더 복잡한 추론 및 의사결정

#### Phase 5 (병렬 실행)
- 여러 Agent를 병렬로 실행
- 성능 향상 및 응답 시간 단축

#### Phase 6 (Advanced Planning)
- 사용자 피드백을 반영한 동적 계획 수정
- Re-planning 기능

### 참고 문서

- LangGraph 공식 문서: https://langchain-ai.github.io/langgraph/
- Supervisor Pattern: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/
- Command 패턴: https://langchain-ai.github.io/langgraph/how-tos/command/

---

**작성일**: 2025-11-04
**문서 위치**: `C:\kdy\Projects\AI_PTmanager\beta_v001\manual\supervisor_agent_tool_manual.md`
**버전**: Phase 4.3
