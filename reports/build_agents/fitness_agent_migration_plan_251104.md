# 운동용 챗봇 에이전트 변경 계획서

**작성일**: 2025-11-04
**버전**: 1.0
**프로젝트**: Fitness PT Manager - 운동/식단/회원 관리 챗봇

---

## 목차

1. [변경 개요](#변경-개요)
2. [에이전트 설계](#에이전트-설계)
3. [Phase 1: 기존 에이전트 제거 및 구조 정리](#phase-1-기존-에이전트-제거-및-구조-정리)
4. [Phase 2: 새 에이전트 기본 구조 구현](#phase-2-새-에이전트-기본-구조-구현)
5. [Phase 3: DietAgent 구현](#phase-3-dietagent-구현)
6. [Phase 4: WorkoutAgent 구현](#phase-4-workoutagent-구현)
7. [Phase 5: ScheduleAgent 구현](#phase-5-scheduleagent-구현)
8. [Phase 6: MemberCareAgent 구현](#phase-6-membercareagent-구현)
9. [Phase 7: CoachingAgent 구현](#phase-7-coachingagent-구현)
10. [Phase 8: DB 스키마 및 통합](#phase-8-db-스키마-및-통합)
11. [Phase 9: 테스트 및 검증](#phase-9-테스트-및-검증)
12. [타임라인](#타임라인)

---

## 변경 개요

### 현재 에이전트 (범용)

| 에이전트 | 역할 |
|---------|------|
| search | 정보 검색 |
| validation | 데이터 검증 |
| analysis | 데이터 분석 |
| comparison | 비교 분석 |
| document | 문서 생성 |

### 새 에이전트 (운동용)

| 에이전트 | 역할 |
|---------|------|
| DietAgent | 식단 기록/분석, 사용자의 식단 입력을 분석, 영양소 계산, DB에 기록하고 일일 피드백 생성 |
| WorkoutAgent | 운동 루틴 추천, 사용자의 목표/경험치를 기반으로 운동 루틴(예: "오늘의 하체")을 생성 및 제안 |
| ScheduleAgent | 수업 예약/변경, A회원 3시 예약처럼 PT 스케줄을 생성/변경하고, 회원에게 확정/리마인드 알림 발송 |
| MemberCareAgent | 회원 리포팅/알림, 회원 상태(A회원 최근 1주 효과)를 리포트, "재등록 7일 전" 등 주요 이벤트를 트레이너에게 알림 |
| CoachingAgent | 전문 자료 검색, "스쿼트 자세 영상", "척신 다이어트 논문" 등 단일 정보를 검색하고 요약 |

### 변경 범위

```
변경 필요 파일:
1. backend/app/octostrator/supervisor/graph.py
2. backend/app/octostrator/agents/placeholder_agents.py → 완전 삭제 후 재구성
3. backend/app/octostrator/supervisor/nodes/planning.py
4. 새 디렉토리 구조:
   backend/app/octostrator/agents/
   ├── diet/
   ├── workout/
   ├── schedule/
   ├── member_care/
   └── coaching/
```

---

## 에이전트 설계

### 1. DietAgent (식단 에이전트)

#### 역할
사용자의 식단 입력을 분석하고, 영양소를 계산하며, DB에 기록하고 일일 피드백을 생성합니다.

#### 주요 기능
1. **식단 입력 파싱**
   - 자연어 입력: "아침에 계란 2개, 현미밥 1공기, 김치"
   - 구조화된 데이터로 변환

2. **영양소 계산**
   - 칼로리, 단백질, 탄수화물, 지방 계산
   - 영양 DB 또는 API 연동 (예: USDA FoodData Central)

3. **DB 기록**
   - meal_logs 테이블에 저장
   - user_id, date, meal_type, foods, nutrition

4. **피드백 생성**
   - 일일 목표 대비 섭취량 비교
   - 조언 생성 (예: "단백질 30g 더 필요합니다")

#### 내부 워크플로우 (SubGraph)

```
START → parse_food → calculate_nutrition → validate_nutrition → save_to_db → generate_feedback → END
```

#### State 구조

```python
class DietAgentState(TypedDict, total=False):
    user_input: str                    # "아침에 계란 2개..."
    parsed_foods: List[dict]           # [{"name": "계란", "quantity": 2, "unit": "개"}]
    nutrition_data: dict               # {"calories": 300, "protein": 24, ...}
    validation_result: dict            # {"is_valid": True, "warnings": []}
    db_record_id: Optional[int]        # 저장된 레코드 ID
    feedback: str                      # "오늘 단백질 섭취량: 80g (목표: 100g)"
```

#### 필요한 툴

1. **food_parser_tool**: 자연어 → 식품 리스트
2. **nutrition_calculator_tool**: 식품 → 영양소
3. **nutrition_validator_tool**: 영양소 검증
4. **db_meal_logger_tool**: DB 저장

#### 필요한 서브에이전트

1. **food_recognizer**: 식품명 인식 및 정규화
2. **portion_estimator**: 양 추정 (1공기 → 200g)

---

### 2. WorkoutAgent (운동 루틴 에이전트)

#### 역할
사용자의 목표와 경험치를 기반으로 맞춤형 운동 루틴을 생성하고 제안합니다.

#### 주요 기능

1. **사용자 프로필 분석**
   - 목표: 체중 감량, 근육 증가, 체력 향상
   - 경험치: 초급, 중급, 고급
   - 제약사항: 부상, 사용 가능한 장비

2. **운동 루틴 생성**
   - 부위별 운동 선택 (예: 하체 - 스쿼트, 런지, 레그프레스)
   - 세트/횟수/무게 설정
   - 템플릿 기반 또는 LLM 생성

3. **루틴 저장 및 추천**
   - workout_routines 테이블에 저장
   - 이전 운동 기록 기반 난이도 조정

4. **진행률 트래킹**
   - 완료 여부 체크
   - 다음 운동 추천

#### 내부 워크플로우

```
START → analyze_profile → select_exercises → calculate_volume → personalize_routine → save_routine → generate_recommendation → END
```

#### State 구조

```python
class WorkoutAgentState(TypedDict, total=False):
    user_id: str
    user_profile: dict                 # {"goal": "muscle_gain", "level": "intermediate"}
    target_muscle_group: str           # "legs", "chest", "back", ...
    selected_exercises: List[dict]     # [{"name": "스쿼트", "sets": 4, "reps": 10}]
    workout_routine: dict              # 전체 루틴
    routine_id: Optional[int]          # 저장된 루틴 ID
    recommendation: str                # "오늘의 하체 운동: 스쿼트 4세트..."
```

#### 필요한 툴

1. **exercise_db_tool**: 운동 DB 조회 (부위, 난이도별)
2. **volume_calculator_tool**: 운동량 계산 (1RM 기반)
3. **routine_template_tool**: 템플릿 기반 루틴 생성
4. **db_routine_saver_tool**: DB 저장

#### 필요한 서브에이전트

1. **exercise_selector**: 사용자에게 맞는 운동 선택
2. **progression_planner**: 점진적 과부하 계획

---

### 3. ScheduleAgent (스케줄 에이전트)

#### 역할
PT 스케줄을 생성/변경하고, 회원에게 확정/리마인드 알림을 발송합니다.

#### 주요 기능

1. **스케줄 생성**
   - "A회원 내일 오후 3시 PT 예약"
   - 트레이너 가용 시간 확인
   - 충돌 검사

2. **스케줄 변경**
   - 기존 예약 취소/변경
   - 재스케줄링

3. **알림 발송**
   - 예약 확정 알림 (카카오톡, 이메일, SMS)
   - 리마인드 알림 (예약 1시간 전)

4. **캘린더 관리**
   - 트레이너별 스케줄 조회
   - 회원별 스케줄 조회

#### 내부 워크플로우

```
START → parse_schedule_request → check_availability → validate_schedule → create_or_update → send_notification → END
```

#### State 구조

```python
class ScheduleAgentState(TypedDict, total=False):
    user_input: str                    # "A회원 3시 예약"
    parsed_request: dict               # {"member": "A", "date": "2025-11-05", "time": "15:00"}
    trainer_availability: List[dict]   # 가용 시간대
    conflicts: List[dict]              # 충돌 목록
    schedule_action: Literal["create", "update", "cancel"]
    schedule_id: Optional[int]
    notification_result: dict          # {"sent": True, "channel": "kakao"}
    confirmation: str                  # "A회원님 11/5 15:00 예약 완료"
```

#### 필요한 툴

1. **schedule_parser_tool**: 자연어 → 스케줄 정보
2. **availability_checker_tool**: 가용 시간 확인
3. **schedule_validator_tool**: 충돌 검사
4. **notification_sender_tool**: 알림 발송 (카카오톡/이메일/SMS)
5. **db_schedule_tool**: DB 저장/조회

#### 필요한 서브에이전트

1. **time_parser**: 시간 표현 파싱 ("내일 오후 3시" → datetime)
2. **conflict_resolver**: 충돌 해결 제안

---

### 4. MemberCareAgent (회원 관리 에이전트)

#### 역할
회원 상태를 리포트하고, 주요 이벤트를 트레이너에게 알립니다.

#### 주요 기능

1. **회원 상태 리포팅**
   - "A회원 최근 1주 효과"
   - 운동 출석률, 식단 기록률, 체중 변화
   - 목표 달성률

2. **이벤트 알림**
   - 재등록 7일 전 알림
   - 장기 미출석 회원 (30일 이상)
   - 생일 축하 알림

3. **회원 분석**
   - 회원 세그멘테이션 (활성/휴면/위험)
   - 이탈 위험 회원 예측

4. **리포트 생성**
   - 주간/월간 회원 리포트
   - 트레이너별 담당 회원 현황

#### 내부 워크플로우

```
START → identify_member → fetch_member_data → analyze_status → generate_report → check_events → send_alerts → END
```

#### State 구조

```python
class MemberCareAgentState(TypedDict, total=False):
    member_id: str
    query_type: Literal["status", "report", "alert"]
    date_range: dict                   # {"start": "2025-10-28", "end": "2025-11-04"}
    member_data: dict                  # 운동/식단/체중 데이터
    analysis_result: dict              # {"attendance_rate": 0.85, "weight_change": -2.3}
    events: List[dict]                 # [{"type": "renewal_due", "days_left": 7}]
    report: str                        # 마크다운 리포트
    alerts_sent: List[dict]            # 발송된 알림 목록
```

#### 필요한 툴

1. **member_data_fetcher_tool**: 회원 데이터 조회
2. **attendance_analyzer_tool**: 출석 분석
3. **progress_tracker_tool**: 진행률 계산
4. **event_detector_tool**: 이벤트 감지
5. **report_generator_tool**: 리포트 생성
6. **alert_sender_tool**: 알림 발송

#### 필요한 서브에이전트

1. **churn_predictor**: 이탈 위험 예측
2. **segmentation_engine**: 회원 세그멘테이션

---

### 5. CoachingAgent (코칭 자료 검색 에이전트)

#### 역할
운동 자세, 영양 논문, 트레이닝 팁 등 전문 자료를 검색하고 요약합니다.

#### 주요 기능

1. **자료 검색**
   - "스쿼트 자세 영상"
   - "척신 다이어트 논문"
   - "HIIT 트레이닝 가이드"

2. **멀티 소스 검색**
   - YouTube (운동 영상)
   - PubMed (논문)
   - 피트니스 블로그/포럼

3. **요약 생성**
   - 긴 논문 → 핵심 요약
   - 영상 → 주요 포인트 추출

4. **북마크 관리**
   - 유용한 자료 저장
   - 카테고리별 분류

#### 내부 워크플로우

```
START → parse_query → determine_source → search_resources → rank_results → summarize_top → save_bookmark → END
```

#### State 구조

```python
class CoachingAgentState(TypedDict, total=False):
    query: str                         # "스쿼트 자세 영상"
    search_category: Literal["video", "article", "research", "general"]
    search_sources: List[str]          # ["youtube", "pubmed", "google"]
    raw_results: List[dict]            # 검색 결과
    ranked_results: List[dict]         # 랭킹된 결과
    top_result: dict                   # 최상위 결과
    summary: str                       # 요약
    bookmark_id: Optional[int]         # 저장된 북마크 ID
```

#### 필요한 툴

1. **youtube_search_tool**: YouTube 검색
2. **pubmed_search_tool**: PubMed 검색
3. **web_search_tool**: 일반 웹 검색
4. **content_summarizer_tool**: 콘텐츠 요약
5. **db_bookmark_tool**: 북마크 저장

#### 필요한 서브에이전트

1. **query_classifier**: 쿼리 분류 (영상/논문/일반)
2. **result_ranker**: 결과 순위 매기기 (관련성 기준)

---

## Phase 1: 기존 에이전트 제거 및 구조 정리

### 목표
기존 범용 에이전트를 제거하고 새 구조를 준비합니다.

### 1.1 파일 삭제

```bash
# 기존 placeholder_agents.py 삭제
del backend\app\octostrator\agents\placeholder_agents.py
```

### 1.2 새 디렉토리 구조 생성

```bash
mkdir backend\app\octostrator\agents\diet
mkdir backend\app\octostrator\agents\workout
mkdir backend\app\octostrator\agents\schedule
mkdir backend\app\octostrator\agents\member_care
mkdir backend\app\octostrator\agents\coaching

# 각 디렉토리에 __init__.py 생성
type nul > backend\app\octostrator\agents\diet\__init__.py
type nul > backend\app\octostrator\agents\workout\__init__.py
type nul > backend\app\octostrator\agents\schedule\__init__.py
type nul > backend\app\octostrator\agents\member_care\__init__.py
type nul > backend\app\octostrator\agents\coaching\__init__.py
```

### 1.3 graph.py 수정

**파일**: `backend/app/octostrator/supervisor/graph.py`

**변경 전 (28-34번 줄)**:
```python
from backend.app.octostrator.agents import (
    search_agent_node,
    validation_agent_node,
    analysis_agent_node,
    comparison_agent_node,
    document_agent_node,
)
```

**변경 후**:
```python
from backend.app.octostrator.agents.diet import diet_agent_node
from backend.app.octostrator.agents.workout import workout_agent_node
from backend.app.octostrator.agents.schedule import schedule_agent_node
from backend.app.octostrator.agents.member_care import member_care_agent_node
from backend.app.octostrator.agents.coaching import coaching_agent_node
```

**변경 전 (124-129번 줄)**:
```python
# 3. Agents (교체 가능)
workflow.add_node("search", search_agent_node)
workflow.add_node("validation", validation_agent_node)
workflow.add_node("analysis", analysis_agent_node)
workflow.add_node("comparison", comparison_agent_node)
workflow.add_node("document", document_agent_node)
```

**변경 후**:
```python
# 3. Fitness Agents
workflow.add_node("diet", diet_agent_node)
workflow.add_node("workout", workout_agent_node)
workflow.add_node("schedule", schedule_agent_node)
workflow.add_node("member_care", member_care_agent_node)
workflow.add_node("coaching", coaching_agent_node)
```

**변경 전 (120-122번 줄)**:
```python
workflow.add_node("executor", executor_node, ends=[
    "search", "validation", "analysis", "comparison", "document", "hitl_handler", "aggregator"
])
```

**변경 후**:
```python
workflow.add_node("executor", executor_node, ends=[
    "diet", "workout", "schedule", "member_care", "coaching", "hitl_handler", "aggregator"
])
```

**변경 전 (151-155번 줄)**:
```python
workflow.add_edge("search", "executor")
workflow.add_edge("validation", "executor")
workflow.add_edge("analysis", "executor")
workflow.add_edge("comparison", "executor")
workflow.add_edge("document", "executor")
```

**변경 후**:
```python
workflow.add_edge("diet", "executor")
workflow.add_edge("workout", "executor")
workflow.add_edge("schedule", "executor")
workflow.add_edge("member_care", "executor")
workflow.add_edge("coaching", "executor")
```

### 1.4 planning.py 수정

**파일**: `backend/app/octostrator/supervisor/nodes/planning.py`

**변경 전 (54-60번 줄)**:
```python
Available agents:
- search: 데이터 검색 (벡터DB, SQL, 웹 검색 등)
- validation: 데이터 검증 (완전성, 정확성 확인)
- analysis: 데이터 분석 (트렌드, 패턴 등)
- comparison: 비교 분석 (전년 대비, 기간별 비교 등)
- document: 문서 생성 (보고서, 요약 등)
- hitl: 사용자 승인 필요 (중요한 결정 전)
```

**변경 후**:
```python
Available agents:
- diet: 식단 기록/분석 (식단 입력, 영양소 계산, DB 저장, 피드백 생성)
- workout: 운동 루틴 추천 (목표/경험치 기반 맞춤 루틴 생성 및 제안)
- schedule: 스케줄 관리 (PT 예약/변경, 알림 발송)
- member_care: 회원 관리 (회원 상태 리포트, 이벤트 알림)
- coaching: 전문 자료 검색 (운동 영상, 논문, 트레이닝 팁 검색 및 요약)
- hitl: 사용자 승인 필요 (중요한 결정 전)
```

**프롬프트 예시 변경 (80-100번 줄)** - 피트니스 도메인에 맞게:

```python
Example Plans:

1. Simple Request: "오늘 먹은 음식 기록해줘: 아침에 계란 2개, 현미밥"
Plan:
[
  {"step_id": 1, "agent": "diet", "description": "식단 입력 파싱 및 영양소 계산"},
  {"step_id": 2, "agent": "diet", "description": "DB에 식단 기록 저장"},
  {"step_id": 3, "agent": "diet", "description": "일일 피드백 생성"}
]

2. Medium Request: "오늘 하체 운동 루틴 추천해줘"
Plan:
[
  {"step_id": 1, "agent": "workout", "description": "사용자 프로필 및 목표 분석"},
  {"step_id": 2, "agent": "workout", "description": "하체 운동 선택 및 세트/횟수 계산"},
  {"step_id": 3, "agent": "workout", "description": "맞춤 루틴 생성 및 추천"}
]

3. Complex Request: "A회원 내일 오후 3시 PT 예약하고, 이번 주 운동 기록 리포트 보여줘"
Plan:
[
  {"step_id": 1, "agent": "schedule", "description": "A회원 내일 15:00 PT 스케줄 생성"},
  {"step_id": 2, "agent": "schedule", "description": "예약 확정 알림 발송"},
  {"step_id": 3, "agent": "member_care", "description": "A회원 이번 주 운동 데이터 조회"},
  {"step_id": 4, "agent": "member_care", "description": "주간 운동 리포트 생성"}
]

4. Coaching Request: "스쿼트 올바른 자세 영상 찾아줘"
Plan:
[
  {"step_id": 1, "agent": "coaching", "description": "스쿼트 자세 영상 검색"},
  {"step_id": 2, "agent": "coaching", "description": "상위 결과 요약 및 제공"}
]
```

### 소요 시간: 0.5일

---

## Phase 2: 새 에이전트 기본 구조 구현

### 목표
5개 에이전트의 Placeholder 버전을 먼저 구현하여 그래프가 동작하도록 합니다.

### 2.1 Base Agent 클래스 (Phase 1 계획서와 동일)

**파일**: `backend/app/octostrator/agents/base_agent.py`

```python
"""Base Agent for Fitness PT Manager

모든 Fitness Agent의 부모 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from langgraph.graph import StateGraph, CompiledGraph
from backend.app.octostrator.states.supervisor_state import SupervisorState


class BaseFitnessAgent(ABC):
    """기본 Fitness Agent 클래스"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._graph: CompiledGraph = None

    @abstractmethod
    def build_graph(self) -> CompiledGraph:
        """Agent SubGraph 빌드"""
        pass

    def get_graph(self) -> CompiledGraph:
        """빌드된 그래프 반환"""
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    async def execute(self, state: SupervisorState) -> Dict[str, Any]:
        """Agent 실행 (Supervisor에서 호출)"""
        graph = self.get_graph()
        agent_input = self.prepare_input(state)
        result = await graph.ainvoke(agent_input)
        return self.prepare_output(state, result)

    @abstractmethod
    def prepare_input(self, supervisor_state: SupervisorState) -> Dict[str, Any]:
        """Supervisor State → Agent State 변환"""
        pass

    @abstractmethod
    def prepare_output(
        self,
        supervisor_state: SupervisorState,
        agent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent 결과 → Supervisor State 변환"""
        pass
```

### 2.2 Placeholder 에이전트 구현

각 에이전트를 간단한 Placeholder로 먼저 구현합니다.

#### DietAgent Placeholder

**파일**: `backend/app/octostrator/agents/diet/__init__.py`

```python
"""DietAgent - 식단 기록 및 분석 에이전트

Placeholder 구현
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def diet_agent_node(state: SupervisorState) -> Dict:
    """Diet Agent Placeholder

    TODO: Phase 3에서 SubGraph로 교체
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    # Placeholder 응답
    result = f"[DietAgent Placeholder] {step['description']}\n\n" \
             f"식단 입력을 파싱하고, 영양소를 계산하여 DB에 저장합니다.\n" \
             f"일일 피드백: 칼로리 1800kcal, 단백질 80g 섭취 완료"

    # State 업데이트
    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
```

#### WorkoutAgent Placeholder

**파일**: `backend/app/octostrator/agents/workout/__init__.py`

```python
"""WorkoutAgent - 운동 루틴 추천 에이전트

Placeholder 구현
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def workout_agent_node(state: SupervisorState) -> Dict:
    """Workout Agent Placeholder

    TODO: Phase 4에서 SubGraph로 교체
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    result = f"[WorkoutAgent Placeholder] {step['description']}\n\n" \
             f"오늘의 하체 운동 루틴:\n" \
             f"1. 스쿼트 4세트 x 10회\n" \
             f"2. 런지 3세트 x 12회\n" \
             f"3. 레그프레스 4세트 x 12회"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
```

#### ScheduleAgent Placeholder

**파일**: `backend/app/octostrator/agents/schedule/__init__.py`

```python
"""ScheduleAgent - PT 스케줄 관리 에이전트

Placeholder 구현
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def schedule_agent_node(state: SupervisorState) -> Dict:
    """Schedule Agent Placeholder

    TODO: Phase 5에서 SubGraph로 교체
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    result = f"[ScheduleAgent Placeholder] {step['description']}\n\n" \
             f"A회원님 11/5 15:00 PT 예약이 완료되었습니다.\n" \
             f"카카오톡으로 예약 확정 알림을 발송했습니다."

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
```

#### MemberCareAgent Placeholder

**파일**: `backend/app/octostrator/agents/member_care/__init__.py`

```python
"""MemberCareAgent - 회원 관리 및 리포팅 에이전트

Placeholder 구현
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def member_care_agent_node(state: SupervisorState) -> Dict:
    """MemberCare Agent Placeholder

    TODO: Phase 6에서 SubGraph로 교체
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    result = f"[MemberCareAgent Placeholder] {step['description']}\n\n" \
             f"A회원 최근 1주 현황:\n" \
             f"- 출석률: 85% (주 5회 목표 중 4회 달성)\n" \
             f"- 체중 변화: -1.2kg\n" \
             f"- 재등록일: 7일 남음 (알림 발송 완료)"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
```

#### CoachingAgent Placeholder

**파일**: `backend/app/octostrator/agents/coaching/__init__.py`

```python
"""CoachingAgent - 전문 자료 검색 에이전트

Placeholder 구현
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def coaching_agent_node(state: SupervisorState) -> Dict:
    """Coaching Agent Placeholder

    TODO: Phase 7에서 SubGraph로 교체
    """
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    result = f"[CoachingAgent Placeholder] {step['description']}\n\n" \
             f"스쿼트 자세 관련 상위 검색 결과:\n" \
             f"1. [YouTube] 스쿼트 완벽 가이드 - 올바른 자세와 흔한 실수\n" \
             f"2. [PubMed] Effects of Squat Depth on Performance (2023)\n" \
             f"요약: 무릎이 발끝을 넘지 않도록, 허리는 중립 유지"

    plan[current_step]["status"] = "completed"
    plan[current_step]["result"] = result

    return {
        "plan": plan,
        "current_step": current_step + 1,
        "messages": [AIMessage(content=result)]
    }
```

### 2.3 통합 테스트

**파일**: `tests/test_fitness_agents_placeholder.py`

```python
"""Fitness Agents Placeholder 테스트"""
import asyncio
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import get_session_config


async def test_all_fitness_agents():
    """5개 Fitness Agent Placeholder 테스트"""

    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config("test_fitness_agents_001")

    # 복합 요청: 모든 Agent 사용
    user_input = """
    1. 오늘 먹은 음식: 아침 - 계란 2개, 현미밥, 김치
    2. 하체 운동 루틴 추천해줘
    3. A회원 내일 오후 3시 PT 예약
    4. A회원 최근 1주 운동 현황 리포트
    5. 스쿼트 올바른 자세 영상 찾아줘
    """

    result = await graph.ainvoke({
        "messages": [HumanMessage(content=user_input)],
        "output_format": "chat"
    }, config=config)

    print("\n=== 최종 결과 ===")
    print(result.get("final_result", ""))

    # Plan 확인
    plan = result.get("plan", [])
    print(f"\n=== 실행된 단계: {len(plan)}개 ===")
    for step in plan:
        print(f"Step {step['step_id']}: {step['agent']} - {step['status']}")


if __name__ == "__main__":
    asyncio.run(test_all_fitness_agents())
```

### 소요 시간: 1일

---

## Phase 3: DietAgent 구현

### 목표
식단 기록/분석 기능을 완전히 구현합니다.

### 3.1 State 정의

**파일**: `backend/app/octostrator/agents/diet/state.py`

```python
"""DietAgent State"""
from typing import TypedDict, Optional, List


class DietAgentState(TypedDict, total=False):
    """Diet Agent 내부 State"""
    user_id: str
    user_input: str                    # "아침에 계란 2개, 현미밥 1공기"
    parsed_foods: List[dict]           # [{"name": "계란", "quantity": 2, "unit": "개"}]
    nutrition_data: dict               # {"calories": 300, "protein": 24, "carbs": 30, "fat": 10}
    validation_result: dict            # {"is_valid": True, "warnings": []}
    db_record_id: Optional[int]        # 저장된 레코드 ID
    feedback: str                      # "오늘 단백질 섭취량: 80g (목표: 100g)"
```

### 3.2 노드 구현

#### parse_food_node

**파일**: `backend/app/octostrator/agents/diet/nodes/parse_food_node.py`

```python
"""식품 파싱 노드"""
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.octostrator.agents.diet.state import DietAgentState
from backend.app.config.system import config


async def parse_food_node(state: DietAgentState) -> Dict:
    """자연어 식단 입력 → 구조화된 식품 리스트

    "아침에 계란 2개, 현미밥 1공기" → [{"name": "계란", "quantity": 2, "unit": "개"}, ...]
    """
    user_input = state["user_input"]

    # LLM으로 파싱
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=config.openai_api_key)

    prompt = SystemMessage(content="""
    You are a food parsing expert. Parse the user's meal input into structured data.

    Output format (JSON):
    [
        {"name": "식품명", "quantity": 수량, "unit": "단위"},
        ...
    ]

    Examples:
    - "계란 2개, 현미밥 1공기" → [{"name": "계란", "quantity": 2, "unit": "개"}, {"name": "현미밥", "quantity": 1, "unit": "공기"}]
    - "닭가슴살 200g" → [{"name": "닭가슴살", "quantity": 200, "unit": "g"}]
    """)

    response = await llm.ainvoke([prompt, HumanMessage(content=user_input)])

    # JSON 파싱 (간단히 eval 사용, 실제론 json.loads)
    import json
    try:
        parsed_foods = json.loads(response.content)
    except:
        # 파싱 실패 시 기본값
        parsed_foods = [{"name": user_input, "quantity": 1, "unit": "serving"}]

    return {
        "parsed_foods": parsed_foods
    }
```

#### calculate_nutrition_node

**파일**: `backend/app/octostrator/agents/diet/nodes/calculate_nutrition_node.py`

```python
"""영양소 계산 노드"""
from typing import Dict
from backend.app.octostrator.agents.diet.state import DietAgentState


# 간단한 영양소 DB (실제론 외부 API 또는 DB 사용)
NUTRITION_DB = {
    "계란": {"calories": 70, "protein": 6, "carbs": 0.5, "fat": 5},  # 1개 기준
    "현미밥": {"calories": 200, "protein": 4, "carbs": 44, "fat": 1},  # 1공기 기준
    "닭가슴살": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},  # 100g 기준
    "김치": {"calories": 15, "protein": 1, "carbs": 3, "fat": 0},  # 100g 기준
}


async def calculate_nutrition_node(state: DietAgentState) -> Dict:
    """식품 리스트 → 영양소 계산"""
    parsed_foods = state["parsed_foods"]

    total_nutrition = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0
    }

    for food in parsed_foods:
        food_name = food["name"]
        quantity = food["quantity"]
        unit = food["unit"]

        # DB에서 영양소 조회
        base_nutrition = NUTRITION_DB.get(food_name)

        if base_nutrition:
            # 단위 변환 (간단히 처리, 실제론 복잡한 변환 필요)
            multiplier = quantity
            if unit == "g":
                multiplier = quantity / 100  # 100g 기준

            # 영양소 누적
            for key in total_nutrition:
                total_nutrition[key] += base_nutrition[key] * multiplier

    return {
        "nutrition_data": total_nutrition
    }
```

#### validate_nutrition_node

**파일**: `backend/app/octostrator/agents/diet/nodes/validate_nutrition_node.py`

```python
"""영양소 검증 노드"""
from typing import Dict
from backend.app.octostrator.agents.diet.state import DietAgentState


async def validate_nutrition_node(state: DietAgentState) -> Dict:
    """영양소 검증 및 경고 생성"""
    nutrition = state["nutrition_data"]

    warnings = []
    is_valid = True

    # 칼로리 범위 체크 (하루 1500-2500kcal)
    if nutrition["calories"] > 2500:
        warnings.append("칼로리가 목표치를 초과했습니다.")
    elif nutrition["calories"] < 1500:
        warnings.append("칼로리가 목표치에 미달합니다.")

    # 단백질 체크 (하루 최소 80g)
    if nutrition["protein"] < 80:
        warnings.append(f"단백질 부족: {80 - nutrition['protein']:.1f}g 더 필요합니다.")

    return {
        "validation_result": {
            "is_valid": is_valid,
            "warnings": warnings
        }
    }
```

#### save_to_db_node

**파일**: `backend/app/octostrator/agents/diet/nodes/save_to_db_node.py`

```python
"""DB 저장 노드"""
from typing import Dict
from backend.app.octostrator.agents.diet.state import DietAgentState


async def save_to_db_node(state: DietAgentState) -> Dict:
    """식단 기록을 DB에 저장

    TODO: 실제 DB 연동 (SQLAlchemy, Alembic 사용)
    """
    user_id = state["user_id"]
    parsed_foods = state["parsed_foods"]
    nutrition = state["nutrition_data"]

    # TODO: DB INSERT
    # db.execute("INSERT INTO meal_logs (user_id, foods, nutrition, date) VALUES ...")

    # Placeholder: 임의의 레코드 ID 반환
    record_id = 12345

    print(f"[DB] 식단 기록 저장 완료: user_id={user_id}, record_id={record_id}")

    return {
        "db_record_id": record_id
    }
```

#### generate_feedback_node

**파일**: `backend/app/octostrator/agents/diet/nodes/generate_feedback_node.py`

```python
"""피드백 생성 노드"""
from typing import Dict
from backend.app.octostrator.agents.diet.state import DietAgentState


async def generate_feedback_node(state: DietAgentState) -> Dict:
    """일일 피드백 생성"""
    nutrition = state["nutrition_data"]
    validation = state["validation_result"]

    # 피드백 메시지 생성
    feedback = f"""
📊 오늘의 식단 분석

총 섭취량:
- 칼로리: {nutrition['calories']:.0f} kcal
- 단백질: {nutrition['protein']:.1f}g
- 탄수화물: {nutrition['carbs']:.1f}g
- 지방: {nutrition['fat']:.1f}g

목표 대비:
- 칼로리: {"✅ 적정" if 1500 <= nutrition['calories'] <= 2500 else "⚠️ 조정 필요"}
- 단백질: {"✅ 충분" if nutrition['protein'] >= 80 else f"⚠️ {80 - nutrition['protein']:.1f}g 부족"}
"""

    if validation["warnings"]:
        feedback += f"\n⚠️ 주의사항:\n"
        for warning in validation["warnings"]:
            feedback += f"- {warning}\n"

    return {
        "feedback": feedback.strip()
    }
```

### 3.3 SubGraph 빌드

**파일**: `backend/app/octostrator/agents/diet/graph.py`

```python
"""DietAgent SubGraph"""
from langgraph.graph import StateGraph, START, END
from backend.app.octostrator.agents.base_agent import BaseFitnessAgent
from backend.app.octostrator.agents.diet.state import DietAgentState
from backend.app.octostrator.agents.diet.nodes import (
    parse_food_node,
    calculate_nutrition_node,
    validate_nutrition_node,
    save_to_db_node,
    generate_feedback_node,
)


class DietAgent(BaseFitnessAgent):
    """Diet Agent SubGraph"""

    def __init__(self):
        super().__init__("diet")

    def build_graph(self):
        """SubGraph 빌드"""
        workflow = StateGraph(DietAgentState)

        # 노드 추가
        workflow.add_node("parse_food", parse_food_node)
        workflow.add_node("calculate_nutrition", calculate_nutrition_node)
        workflow.add_node("validate_nutrition", validate_nutrition_node)
        workflow.add_node("save_to_db", save_to_db_node)
        workflow.add_node("generate_feedback", generate_feedback_node)

        # 엣지 추가
        workflow.add_edge(START, "parse_food")
        workflow.add_edge("parse_food", "calculate_nutrition")
        workflow.add_edge("calculate_nutrition", "validate_nutrition")
        workflow.add_edge("validate_nutrition", "save_to_db")
        workflow.add_edge("save_to_db", "generate_feedback")
        workflow.add_edge("generate_feedback", END)

        return workflow.compile()

    def prepare_input(self, supervisor_state):
        """Supervisor State → Diet State"""
        plan = supervisor_state["plan"]
        current_step = supervisor_state["current_step"]
        task = plan[current_step]

        return {
            "user_id": "user_123",  # TODO: Context에서 가져오기
            "user_input": task["description"]
        }

    def prepare_output(self, supervisor_state, agent_result):
        """Diet 결과 → Supervisor State"""
        plan = supervisor_state["plan"]
        current_step = supervisor_state["current_step"]

        plan[current_step]["status"] = "completed"
        plan[current_step]["result"] = agent_result.get("feedback", "")

        from langchain_core.messages import AIMessage

        return {
            "plan": plan,
            "current_step": current_step + 1,
            "messages": [AIMessage(content=agent_result["feedback"])]
        }
```

### 3.4 __init__.py 업데이트

**파일**: `backend/app/octostrator/agents/diet/__init__.py`

```python
"""DietAgent - 식단 기록 및 분석 에이전트"""
from backend.app.octostrator.agents.diet.graph import DietAgent


# Agent 인스턴스 생성
_diet_agent = DietAgent()


async def diet_agent_node(state):
    """Diet Agent 노드 (Supervisor에서 호출)"""
    return await _diet_agent.execute(state)
```

### 3.5 노드 패키지

**파일**: `backend/app/octostrator/agents/diet/nodes/__init__.py`

```python
"""DietAgent Nodes"""
from backend.app.octostrator.agents.diet.nodes.parse_food_node import parse_food_node
from backend.app.octostrator.agents.diet.nodes.calculate_nutrition_node import calculate_nutrition_node
from backend.app.octostrator.agents.diet.nodes.validate_nutrition_node import validate_nutrition_node
from backend.app.octostrator.agents.diet.nodes.save_to_db_node import save_to_db_node
from backend.app.octostrator.agents.diet.nodes.generate_feedback_node import generate_feedback_node

__all__ = [
    "parse_food_node",
    "calculate_nutrition_node",
    "validate_nutrition_node",
    "save_to_db_node",
    "generate_feedback_node",
]
```

### 3.6 테스트

**파일**: `tests/test_diet_agent.py`

```python
"""DietAgent 테스트"""
import asyncio
from backend.app.octostrator.agents.diet.graph import DietAgent


async def test_diet_agent():
    """DietAgent SubGraph 테스트"""
    agent = DietAgent()
    graph = agent.get_graph()

    # 입력
    input_data = {
        "user_id": "user_123",
        "user_input": "아침에 계란 2개, 현미밥 1공기, 김치"
    }

    # 실행
    result = await graph.ainvoke(input_data)

    print("\n=== DietAgent 실행 결과 ===")
    print(f"파싱된 식품: {result['parsed_foods']}")
    print(f"영양소: {result['nutrition_data']}")
    print(f"DB 레코드 ID: {result['db_record_id']}")
    print(f"\n{result['feedback']}")


if __name__ == "__main__":
    asyncio.run(test_diet_agent())
```

### 소요 시간: 2일

---

## Phase 4: WorkoutAgent 구현

### 목표
운동 루틴 추천 기능을 완전히 구현합니다.

### 구조 (DietAgent와 유사)

```
backend/app/octostrator/agents/workout/
├── __init__.py
├── graph.py
├── state.py
└── nodes/
    ├── __init__.py
    ├── analyze_profile_node.py
    ├── select_exercises_node.py
    ├── calculate_volume_node.py
    ├── personalize_routine_node.py
    ├── save_routine_node.py
    └── generate_recommendation_node.py
```

### 워크플로우

```
START → analyze_profile → select_exercises → calculate_volume → personalize_routine → save_routine → generate_recommendation → END
```

### State

```python
class WorkoutAgentState(TypedDict, total=False):
    user_id: str
    user_profile: dict                 # {"goal": "muscle_gain", "level": "intermediate"}
    target_muscle_group: str           # "legs", "chest", "back", ...
    selected_exercises: List[dict]     # [{"name": "스쿼트", "type": "compound"}]
    workout_routine: dict              # 전체 루틴 (세트/횟수/무게)
    routine_id: Optional[int]
    recommendation: str
```

### 핵심 노드

1. **analyze_profile_node**: 사용자 목표/경험치 분석
2. **select_exercises_node**: 운동 DB에서 적합한 운동 선택
3. **calculate_volume_node**: 1RM 기반 세트/횟수/무게 계산
4. **personalize_routine_node**: 사용자 맞춤 조정
5. **save_routine_node**: DB 저장
6. **generate_recommendation_node**: 추천 메시지 생성

### 소요 시간: 2일

---

## Phase 5: ScheduleAgent 구현

### 목표
PT 스케줄 관리 및 알림 발송 기능을 구현합니다.

### 구조

```
backend/app/octostrator/agents/schedule/
├── __init__.py
├── graph.py
├── state.py
└── nodes/
    ├── __init__.py
    ├── parse_schedule_node.py
    ├── check_availability_node.py
    ├── validate_schedule_node.py
    ├── create_or_update_node.py
    └── send_notification_node.py
```

### 워크플로우

```
START → parse_schedule → check_availability → validate_schedule → create_or_update → send_notification → END
```

### State

```python
class ScheduleAgentState(TypedDict, total=False):
    user_input: str
    parsed_request: dict               # {"member": "A", "date": "2025-11-05", "time": "15:00"}
    trainer_availability: List[dict]
    conflicts: List[dict]
    schedule_action: Literal["create", "update", "cancel"]
    schedule_id: Optional[int]
    notification_result: dict
    confirmation: str
```

### 핵심 노드

1. **parse_schedule_node**: 자연어 → 스케줄 정보
2. **check_availability_node**: 트레이너 가용 시간 확인
3. **validate_schedule_node**: 충돌 검사
4. **create_or_update_node**: DB에 스케줄 생성/변경
5. **send_notification_node**: 카카오톡/이메일/SMS 알림 발송

### 소요 시간: 2일

---

## Phase 6: MemberCareAgent 구현

### 목표
회원 관리 및 리포팅 기능을 구현합니다.

### 구조

```
backend/app/octostrator/agents/member_care/
├── __init__.py
├── graph.py
├── state.py
└── nodes/
    ├── __init__.py
    ├── identify_member_node.py
    ├── fetch_member_data_node.py
    ├── analyze_status_node.py
    ├── generate_report_node.py
    ├── check_events_node.py
    └── send_alerts_node.py
```

### 워크플로우

```
START → identify_member → fetch_member_data → analyze_status → generate_report → check_events → send_alerts → END
```

### State

```python
class MemberCareAgentState(TypedDict, total=False):
    member_id: str
    query_type: Literal["status", "report", "alert"]
    date_range: dict
    member_data: dict
    analysis_result: dict
    events: List[dict]
    report: str
    alerts_sent: List[dict]
```

### 핵심 노드

1. **identify_member_node**: 회원 식별
2. **fetch_member_data_node**: 운동/식단/체중 데이터 조회
3. **analyze_status_node**: 출석률, 진행률 분석
4. **generate_report_node**: 마크다운 리포트 생성
5. **check_events_node**: 재등록, 생일 등 이벤트 감지
6. **send_alerts_node**: 트레이너에게 알림 발송

### 소요 시간: 2일

---

## Phase 7: CoachingAgent 구현

### 목표
전문 자료 검색 및 요약 기능을 구현합니다.

### 구조

```
backend/app/octostrator/agents/coaching/
├── __init__.py
├── graph.py
├── state.py
└── nodes/
    ├── __init__.py
    ├── parse_query_node.py
    ├── determine_source_node.py
    ├── search_resources_node.py
    ├── rank_results_node.py
    ├── summarize_top_node.py
    └── save_bookmark_node.py
```

### 워크플로우

```
START → parse_query → determine_source → search_resources → rank_results → summarize_top → save_bookmark → END
```

### State

```python
class CoachingAgentState(TypedDict, total=False):
    query: str
    search_category: Literal["video", "article", "research", "general"]
    search_sources: List[str]
    raw_results: List[dict]
    ranked_results: List[dict]
    top_result: dict
    summary: str
    bookmark_id: Optional[int]
```

### 핵심 노드

1. **parse_query_node**: 쿼리 분석
2. **determine_source_node**: 검색 소스 결정 (YouTube/PubMed/Web)
3. **search_resources_node**: 멀티 소스 검색
4. **rank_results_node**: 관련성 기반 순위
5. **summarize_top_node**: 최상위 결과 요약
6. **save_bookmark_node**: 북마크 저장

### 소요 시간: 2일

---

## Phase 8: 데이터베이스 스키마 및 통합

### 목표
3종류의 데이터베이스 (SQLite, FAISS, 비정형)를 설계하고 모든 Agent와 통합합니다.

### 데이터베이스 구조

```
backend/database/
├── relation_db/          # SQLite - 정형 데이터
│   ├── fitness.db        # SQLite DB 파일
│   ├── models.py         # SQLAlchemy 모델
│   ├── session.py        # DB 세션 관리
│   └── mock_data.py      # Mock 데이터 생성
├── vector_db/            # FAISS - 벡터 데이터
│   ├── exercise_index/   # 운동 자료 벡터
│   ├── member_index/     # 회원 유사도 벡터
│   ├── faiss_manager.py  # FAISS 관리자
│   └── mock_vectors.py   # Mock 벡터 데이터
└── unstructured_db/      # 파일 기반 - 비정형 데이터
    ├── videos/           # 운동 영상
    ├── documents/        # 논문 PDF
    ├── images/           # 운동 자세 이미지
    └── mock_files.py     # Mock 파일 생성
```

### 8.1 정형 DB - SQLite

#### DB 용도
- 회원 정보 (users)
- 식단 기록 (meal_logs)
- 운동 기록 (workout_routines)
- PT 스케줄 (schedules)
- 회원 진행률 (member_progress)
- 북마크 (bookmarks)

#### models.py

**파일**: `backend/database/relation_db/models.py`

```python
"""SQLite Database Models for Fitness PT Manager"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """사용자/회원 테이블"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    goal = Column(String(50))  # weight_loss, muscle_gain, fitness
    level = Column(String(20))  # beginner, intermediate, advanced
    created_at = Column(DateTime, default=datetime.utcnow)


class MealLog(Base):
    """식단 기록 테이블"""
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    meal_type = Column(String(20))  # breakfast, lunch, dinner, snack
    foods = Column(Text)  # JSON 문자열: [{"name": "계란", "quantity": 2, "unit": "개"}]
    nutrition = Column(Text)  # JSON 문자열: {"calories": 300, "protein": 24, ...}
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkoutRoutine(Base):
    """운동 루틴 테이블"""
    __tablename__ = "workout_routines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    muscle_group = Column(String(50))  # legs, chest, back, shoulders, arms
    exercises = Column(Text)  # JSON 문자열: [{"name": "스쿼트", "sets": 4, "reps": 10, ...}]
    created_at = Column(DateTime, default=datetime.utcnow)


class Schedule(Base):
    """PT 스케줄 테이블"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trainer_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(String(20))  # confirmed, cancelled, completed
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class MemberProgress(Base):
    """회원 진행률 테이블"""
    __tablename__ = "member_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    weight = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass = Column(Float)
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class Bookmark(Base):
    """자료 북마크 테이블"""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    url = Column(String(500))
    category = Column(String(50))  # video, article, research
    summary = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)


class ExerciseDB(Base):
    """운동 데이터베이스 테이블"""
    __tablename__ = "exercise_db"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    muscle_group = Column(String(50))  # legs, chest, back, shoulders, arms
    difficulty = Column(String(20))  # beginner, intermediate, advanced
    equipment = Column(String(100))  # barbell, dumbbell, bodyweight, machine
    description = Column(Text)
    video_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### session.py

**파일**: `backend/database/relation_db/session.py`

```python
"""SQLite Database Session Management"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

# SQLite 연결 문자열
DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Engine 생성
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """DB 세션 가져오기 (Context Manager)

    사용 예:
        with get_db() as db:
            user = db.query(User).filter(User.id == 1).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    from backend.database.relation_db.models import Base

    Base.metadata.create_all(bind=engine)
    print(f"✓ SQLite 데이터베이스 초기화 완료: {DB_PATH}")
```

#### mock_data.py

**파일**: `backend/database/relation_db/mock_data.py`

```python
"""Mock Data Generator for SQLite DB"""
from backend.database.relation_db.models import (
    User, MealLog, WorkoutRoutine, Schedule, MemberProgress, Bookmark, ExerciseDB
)
from backend.database.relation_db.session import get_db, init_db
from datetime import datetime, timedelta
import json


def create_mock_users():
    """Mock 사용자 생성"""
    users = [
        User(id=1, name="김철수", email="chulsoo@example.com", phone="010-1234-5678",
             goal="muscle_gain", level="intermediate"),
        User(id=2, name="이영희", email="younghee@example.com", phone="010-2345-6789",
             goal="weight_loss", level="beginner"),
        User(id=3, name="박민수", email="minsoo@example.com", phone="010-3456-7890",
             goal="fitness", level="advanced"),
        User(id=100, name="트레이너A", email="trainer_a@example.com", phone="010-9999-0001",
             goal="trainer", level="expert"),
    ]

    with get_db() as db:
        for user in users:
            existing = db.query(User).filter(User.email == user.email).first()
            if not existing:
                db.add(user)
        db.commit()

    print(f"✓ Mock Users 생성: {len(users)}명")


def create_mock_meal_logs():
    """Mock 식단 기록 생성"""
    meal_logs = [
        MealLog(
            user_id=1,
            date=datetime.now() - timedelta(days=0),
            meal_type="breakfast",
            foods=json.dumps([
                {"name": "계란", "quantity": 2, "unit": "개"},
                {"name": "현미밥", "quantity": 1, "unit": "공기"}
            ]),
            nutrition=json.dumps({
                "calories": 340, "protein": 18, "carbs": 45, "fat": 11
            })
        ),
        MealLog(
            user_id=1,
            date=datetime.now() - timedelta(days=0),
            meal_type="lunch",
            foods=json.dumps([
                {"name": "닭가슴살", "quantity": 200, "unit": "g"},
                {"name": "샐러드", "quantity": 1, "unit": "접시"}
            ]),
            nutrition=json.dumps({
                "calories": 250, "protein": 50, "carbs": 10, "fat": 5
            })
        ),
        MealLog(
            user_id=2,
            date=datetime.now() - timedelta(days=0),
            meal_type="breakfast",
            foods=json.dumps([
                {"name": "오트밀", "quantity": 1, "unit": "컵"},
                {"name": "바나나", "quantity": 1, "unit": "개"}
            ]),
            nutrition=json.dumps({
                "calories": 280, "protein": 8, "carbs": 55, "fat": 4
            })
        ),
    ]

    with get_db() as db:
        for log in meal_logs:
            db.add(log)
        db.commit()

    print(f"✓ Mock Meal Logs 생성: {len(meal_logs)}개")


def create_mock_exercises():
    """Mock 운동 데이터베이스 생성"""
    exercises = [
        ExerciseDB(name="스쿼트", muscle_group="legs", difficulty="beginner",
                   equipment="barbell", description="하체 전체를 강화하는 기본 운동",
                   video_url="https://youtube.com/squat"),
        ExerciseDB(name="벤치프레스", muscle_group="chest", difficulty="intermediate",
                   equipment="barbell", description="가슴 근육을 발달시키는 운동",
                   video_url="https://youtube.com/bench_press"),
        ExerciseDB(name="데드리프트", muscle_group="back", difficulty="advanced",
                   equipment="barbell", description="등과 하체 전반을 강화",
                   video_url="https://youtube.com/deadlift"),
        ExerciseDB(name="런지", muscle_group="legs", difficulty="beginner",
                   equipment="bodyweight", description="하체 균형과 근력 향상",
                   video_url="https://youtube.com/lunge"),
        ExerciseDB(name="풀업", muscle_group="back", difficulty="intermediate",
                   equipment="bodyweight", description="등 근육 발달",
                   video_url="https://youtube.com/pullup"),
    ]

    with get_db() as db:
        for exercise in exercises:
            existing = db.query(ExerciseDB).filter(ExerciseDB.name == exercise.name).first()
            if not existing:
                db.add(exercise)
        db.commit()

    print(f"✓ Mock Exercises 생성: {len(exercises)}개")


def create_mock_workout_routines():
    """Mock 운동 루틴 생성"""
    routines = [
        WorkoutRoutine(
            user_id=1,
            date=datetime.now() - timedelta(days=0),
            muscle_group="legs",
            exercises=json.dumps([
                {"name": "스쿼트", "sets": 4, "reps": 10, "weight": 80},
                {"name": "런지", "sets": 3, "reps": 12, "weight": 0},
            ])
        ),
        WorkoutRoutine(
            user_id=3,
            date=datetime.now() - timedelta(days=1),
            muscle_group="chest",
            exercises=json.dumps([
                {"name": "벤치프레스", "sets": 4, "reps": 8, "weight": 100},
            ])
        ),
    ]

    with get_db() as db:
        for routine in routines:
            db.add(routine)
        db.commit()

    print(f"✓ Mock Workout Routines 생성: {len(routines)}개")


def create_mock_schedules():
    """Mock PT 스케줄 생성"""
    schedules = [
        Schedule(
            user_id=1,
            trainer_id=100,
            date=datetime.now() + timedelta(days=1, hours=15),  # 내일 오후 3시
            duration_minutes=60,
            status="confirmed",
            notes="하체 집중 PT"
        ),
        Schedule(
            user_id=2,
            trainer_id=100,
            date=datetime.now() + timedelta(days=2, hours=10),  # 모레 오전 10시
            duration_minutes=60,
            status="confirmed",
            notes="유산소 + 다이어트 상담"
        ),
    ]

    with get_db() as db:
        for schedule in schedules:
            db.add(schedule)
        db.commit()

    print(f"✓ Mock Schedules 생성: {len(schedules)}개")


def create_all_mock_data():
    """모든 Mock 데이터 생성"""
    print("\n=== Mock 데이터 생성 시작 ===\n")

    # DB 초기화
    init_db()

    # Mock 데이터 생성
    create_mock_users()
    create_mock_exercises()
    create_mock_meal_logs()
    create_mock_workout_routines()
    create_mock_schedules()

    print("\n=== Mock 데이터 생성 완료 ===\n")


if __name__ == "__main__":
    create_all_mock_data()
```

### 8.2 벡터 DB - FAISS

#### DB 용도
- 운동 자료 벡터 검색 (CoachingAgent)
- 유사 회원 검색 (MemberCareAgent)
- 운동 추천 (WorkoutAgent)

#### faiss_manager.py

**파일**: `backend/database/vector_db/faiss_manager.py`

```python
"""FAISS Vector Database Manager"""
import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple


class FAISSManager:
    """FAISS 벡터 DB 관리자"""

    def __init__(self, index_path: str, dimension: int = 384):
        """초기화

        Args:
            index_path: FAISS 인덱스 저장 경로
            dimension: 벡터 차원 (기본: 384, sentence-transformers 기본)
        """
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.metadata = []  # 벡터에 대응하는 메타데이터

    def create_index(self):
        """새 FAISS 인덱스 생성"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        print(f"✓ FAISS 인덱스 생성 완료 (dimension={self.dimension})")

    def add_vectors(self, vectors: np.ndarray, metadata: List[dict]):
        """벡터 추가

        Args:
            vectors: (N, dimension) numpy array
            metadata: 각 벡터에 대응하는 메타데이터 리스트
        """
        if self.index is None:
            self.create_index()

        self.index.add(vectors.astype('float32'))
        self.metadata.extend(metadata)
        print(f"✓ {len(vectors)}개 벡터 추가 완료 (총: {self.index.ntotal}개)")

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[dict, float]]:
        """벡터 검색

        Args:
            query_vector: (dimension,) numpy array
            top_k: 상위 K개 결과

        Returns:
            [(metadata, distance), ...] 리스트
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vector = query_vector.reshape(1, -1).astype('float32')
        distances, indices = self.index.search(query_vector, top_k)

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                results.append((self.metadata[idx], float(distance)))

        return results

    def save(self):
        """인덱스 저장"""
        if self.index is None:
            return

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # FAISS 인덱스 저장
        faiss.write_index(self.index, f"{self.index_path}.index")

        # 메타데이터 저장
        with open(f"{self.index_path}.meta", "wb") as f:
            pickle.dump(self.metadata, f)

        print(f"✓ FAISS 인덱스 저장 완료: {self.index_path}")

    def load(self):
        """인덱스 로드"""
        if not os.path.exists(f"{self.index_path}.index"):
            print(f"⚠ FAISS 인덱스 파일 없음: {self.index_path}.index")
            self.create_index()
            return

        self.index = faiss.read_index(f"{self.index_path}.index")

        with open(f"{self.index_path}.meta", "rb") as f:
            self.metadata = pickle.load(f)

        print(f"✓ FAISS 인덱스 로드 완료: {self.index.ntotal}개 벡터")
```

#### mock_vectors.py

**파일**: `backend/database/vector_db/mock_vectors.py`

```python
"""Mock Vector Data Generator"""
from backend.database.vector_db.faiss_manager import FAISSManager
import numpy as np
import os


def create_mock_exercise_vectors():
    """운동 자료 벡터 Mock 데이터 생성"""

    # 운동 자료 메타데이터
    exercises = [
        {"title": "스쿼트 완벽 가이드", "type": "video", "url": "https://youtube.com/squat", "description": "올바른 스쿼트 자세"},
        {"title": "벤치프레스 팁", "type": "video", "url": "https://youtube.com/bench", "description": "가슴 운동 핵심"},
        {"title": "데드리프트 논문", "type": "research", "url": "https://pubmed.com/deadlift", "description": "등 근육 발달 연구"},
        {"title": "HIIT 트레이닝", "type": "article", "url": "https://blog.com/hiit", "description": "고강도 인터벌"},
        {"title": "다이어트 식단", "type": "article", "url": "https://blog.com/diet", "description": "체중 감량 식단"},
    ]

    # Mock 벡터 생성 (실제로는 Sentence Transformer 사용)
    vectors = np.random.rand(len(exercises), 384)  # 384차원

    # FAISS Manager 초기화
    index_path = os.path.join(os.path.dirname(__file__), "exercise_index")
    manager = FAISSManager(index_path, dimension=384)

    # 벡터 추가
    manager.add_vectors(vectors, exercises)

    # 저장
    manager.save()

    print(f"✓ Mock 운동 자료 벡터 생성: {len(exercises)}개")


def create_mock_member_vectors():
    """회원 유사도 벡터 Mock 데이터 생성"""

    members = [
        {"user_id": 1, "name": "김철수", "goal": "muscle_gain", "level": "intermediate"},
        {"user_id": 2, "name": "이영희", "goal": "weight_loss", "level": "beginner"},
        {"user_id": 3, "name": "박민수", "goal": "fitness", "level": "advanced"},
    ]

    vectors = np.random.rand(len(members), 384)

    index_path = os.path.join(os.path.dirname(__file__), "member_index")
    manager = FAISSManager(index_path, dimension=384)

    manager.add_vectors(vectors, members)
    manager.save()

    print(f"✓ Mock 회원 벡터 생성: {len(members)}개")


def create_all_mock_vectors():
    """모든 Mock 벡터 데이터 생성"""
    print("\n=== Mock 벡터 데이터 생성 시작 ===\n")

    create_mock_exercise_vectors()
    create_mock_member_vectors()

    print("\n=== Mock 벡터 데이터 생성 완료 ===\n")


if __name__ == "__main__":
    create_all_mock_vectors()
```

### 8.3 비정형 DB - 파일 기반

#### DB 용도
- 운동 영상 파일
- 논문 PDF
- 운동 자세 이미지

#### mock_files.py

**파일**: `backend/database/unstructured_db/mock_files.py`

```python
"""Mock Unstructured Files Generator"""
import os


def create_mock_directories():
    """디렉토리 생성"""
    base_path = os.path.dirname(__file__)

    directories = [
        os.path.join(base_path, "videos"),
        os.path.join(base_path, "documents"),
        os.path.join(base_path, "images"),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    print(f"✓ 디렉토리 생성 완료: {len(directories)}개")


def create_mock_video_links():
    """Mock 영상 링크 파일 생성"""
    base_path = os.path.join(os.path.dirname(__file__), "videos")

    videos = {
        "squat_guide.txt": "https://www.youtube.com/watch?v=squat_example\n스쿼트 완벽 가이드 - 올바른 자세와 흔한 실수",
        "bench_press.txt": "https://www.youtube.com/watch?v=bench_example\n벤치프레스 마스터하기",
        "deadlift.txt": "https://www.youtube.com/watch?v=deadlift_example\n데드리프트 기초부터 고급까지",
    }

    for filename, content in videos.items():
        filepath = os.path.join(base_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"✓ Mock 영상 링크 생성: {len(videos)}개")


def create_mock_documents():
    """Mock 문서 파일 생성"""
    base_path = os.path.join(os.path.dirname(__file__), "documents")

    documents = {
        "hiit_training.md": """# HIIT 트레이닝 가이드

## 개요
고강도 인터벌 트레이닝 (HIIT)는 짧은 시간에 최대 효과를 내는 운동입니다.

## 효과
- 체지방 감소
- 심폐 기능 향상
- 근육 유지

## 추천 루틴
1. 워밍업 5분
2. 고강도 30초 - 휴식 30초 (8회 반복)
3. 쿨다운 5분
""",
        "diet_plan.md": """# 다이어트 식단 가이드

## 기본 원칙
- 칼로리 적정량 유지
- 단백질 충분히 섭취
- 가공식품 최소화

## 추천 식단
- 아침: 계란 2개, 현미밥, 김치
- 점심: 닭가슴살 200g, 샐러드
- 저녁: 생선구이, 채소
""",
    }

    for filename, content in documents.items():
        filepath = os.path.join(base_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"✓ Mock 문서 생성: {len(documents)}개")


def create_mock_image_placeholders():
    """Mock 이미지 placeholder 생성"""
    base_path = os.path.join(os.path.dirname(__file__), "images")

    images = [
        "squat_form.txt",  # placeholder: 실제로는 .jpg
        "bench_press_form.txt",
        "deadlift_form.txt",
    ]

    for filename in images:
        filepath = os.path.join(base_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"[이미지 Placeholder] {filename.replace('.txt', '.jpg')}")

    print(f"✓ Mock 이미지 placeholder 생성: {len(images)}개")


def create_all_mock_files():
    """모든 Mock 파일 생성"""
    print("\n=== Mock 비정형 파일 생성 시작 ===\n")

    create_mock_directories()
    create_mock_video_links()
    create_mock_documents()
    create_mock_image_placeholders()

    print("\n=== Mock 비정형 파일 생성 완료 ===\n")


if __name__ == "__main__":
    create_all_mock_files()
```

### 8.4 Agent에서 DB 사용

각 Agent의 DB 사용 예시:

#### DietAgent - SQLite 사용

```python
# backend/app/octostrator/agents/diet/nodes/save_to_db_node.py

from backend.database.relation_db.models import MealLog
from backend.database.relation_db.session import get_db
from datetime import datetime
import json


async def save_to_db_node(state: DietAgentState) -> Dict:
    """식단 기록을 SQLite에 저장"""
    user_id = state["user_id"]
    parsed_foods = state["parsed_foods"]
    nutrition = state["nutrition_data"]

    with get_db() as db:
        meal_log = MealLog(
            user_id=int(user_id.replace("user_", "")),
            date=datetime.utcnow(),
            meal_type="breakfast",
            foods=json.dumps(parsed_foods),
            nutrition=json.dumps(nutrition)
        )

        db.add(meal_log)
        db.commit()
        db.refresh(meal_log)

        record_id = meal_log.id

    print(f"[SQLite] 식단 기록 저장: user_id={user_id}, record_id={record_id}")

    return {
        "db_record_id": record_id
    }
```

#### CoachingAgent - FAISS 사용

```python
# backend/app/octostrator/agents/coaching/nodes/search_resources_node.py

from backend.database.vector_db.faiss_manager import FAISSManager
import numpy as np
import os


async def search_resources_node(state: CoachingAgentState) -> Dict:
    """벡터 검색으로 자료 찾기"""
    query = state["query"]

    # FAISS Manager 로드
    index_path = os.path.join("backend", "database", "vector_db", "exercise_index")
    manager = FAISSManager(index_path)
    manager.load()

    # 쿼리 벡터 생성 (실제로는 Sentence Transformer 사용)
    query_vector = np.random.rand(384)

    # 검색
    results = manager.search(query_vector, top_k=5)

    # 메타데이터 추출
    raw_results = [metadata for metadata, distance in results]

    print(f"[FAISS] 검색 완료: {len(raw_results)}개 결과")

    return {
        "raw_results": raw_results
    }
```

### 소요 시간: 2일

---

## Phase 9: 테스트 및 검증

### 목표
전체 시스템 통합 테스트 및 검증

### 9.1 단위 테스트

각 Agent의 노드별 단위 테스트:

```python
# tests/agents/test_diet_nodes.py
async def test_parse_food_node():
    state = {"user_input": "계란 2개, 현미밥 1공기"}
    result = await parse_food_node(state)
    assert len(result["parsed_foods"]) == 2
    assert result["parsed_foods"][0]["name"] == "계란"
```

### 9.2 통합 테스트

Agent별 SubGraph 통합 테스트:

```python
# tests/agents/test_diet_agent_integration.py
async def test_diet_agent_full_workflow():
    agent = DietAgent()
    result = await agent.get_graph().ainvoke({
        "user_id": "user_123",
        "user_input": "아침 계란 2개"
    })
    assert result["db_record_id"] is not None
    assert "칼로리" in result["feedback"]
```

### 9.3 E2E 테스트

Supervisor → 모든 Agent 실행:

```python
# tests/test_e2e_fitness_chatbot.py
async def test_full_chatbot_workflow():
    graph = build_supervisor_graph(checkpointer=checkpointer)

    # 복합 요청
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="""
            1. 오늘 식단: 아침 계란 2개, 현미밥
            2. 하체 운동 추천
            3. A회원 내일 3시 예약
            4. A회원 최근 1주 리포트
            5. 스쿼트 자세 영상 찾기
        """)],
        "output_format": "chat"
    }, config=config)

    # 검증
    assert result["final_result"] is not None
    plan = result["plan"]
    assert all(step["status"] == "completed" for step in plan)
```

### 9.4 성능 테스트

응답 시간 측정:

```python
import time

async def test_performance():
    start = time.time()
    result = await graph.ainvoke(input_data)
    elapsed = time.time() - start

    assert elapsed < 10  # 10초 이내
    print(f"응답 시간: {elapsed:.2f}초")
```

### 소요 시간: 2일

---

## 타임라인

### 총 예상 기간: 약 15일 (3주)

| Phase | 작업 | 소요 시간 | 누적 |
|-------|------|-----------|------|
| Phase 1 | 기존 에이전트 제거 및 구조 정리 | 0.5일 | 0.5일 |
| Phase 2 | 새 에이전트 Placeholder 구현 | 1일 | 1.5일 |
| Phase 3 | DietAgent 구현 | 2일 | 3.5일 |
| Phase 4 | WorkoutAgent 구현 | 2일 | 5.5일 |
| Phase 5 | ScheduleAgent 구현 | 2일 | 7.5일 |
| Phase 6 | MemberCareAgent 구현 | 2일 | 9.5일 |
| Phase 7 | CoachingAgent 구현 | 2일 | 11.5일 |
| Phase 8 | DB 스키마 및 통합 | 2일 | 13.5일 |
| Phase 9 | 테스트 및 검증 | 2일 | 15.5일 |

### 주차별 마일스톤

**Week 1 (Day 1-5)**
- ✅ Phase 1-2: 구조 정리 및 Placeholder
- ✅ Phase 3: DietAgent 완성
- ✅ Phase 4: WorkoutAgent 시작

**Week 2 (Day 6-10)**
- ✅ Phase 4: WorkoutAgent 완성
- ✅ Phase 5: ScheduleAgent 완성
- ✅ Phase 6: MemberCareAgent 완성

**Week 3 (Day 11-15)**
- ✅ Phase 7: CoachingAgent 완성
- ✅ Phase 8: DB 통합
- ✅ Phase 9: 전체 테스트

---

## 검증 체크리스트

### Phase 1-2 완료 기준
- [ ] graph.py에서 5개 새 에이전트 import 성공
- [ ] planning.py 프롬프트 업데이트 완료
- [ ] Placeholder 에이전트가 모두 동작
- [ ] 통합 테스트 통과

### Phase 3 (DietAgent) 완료 기준
- [ ] 식품 파싱 정확도 > 90%
- [ ] 영양소 계산 정확도 > 95%
- [ ] DB 저장 성공
- [ ] 피드백 생성 완료

### Phase 4 (WorkoutAgent) 완료 기준
- [ ] 사용자 프로필 분석 완료
- [ ] 운동 선택 알고리즘 동작
- [ ] 세트/횟수/무게 계산 정확
- [ ] 루틴 저장 성공

### Phase 5 (ScheduleAgent) 완료 기준
- [ ] 스케줄 파싱 정확도 > 90%
- [ ] 충돌 검사 동작
- [ ] DB 저장 성공
- [ ] 알림 발송 성공 (카카오톡/이메일)

### Phase 6 (MemberCareAgent) 완료 기준
- [ ] 회원 데이터 조회 성공
- [ ] 출석률/진행률 분석 정확
- [ ] 리포트 생성 완료
- [ ] 이벤트 감지 동작

### Phase 7 (CoachingAgent) 완료 기준
- [ ] YouTube 검색 동작
- [ ] PubMed 검색 동작
- [ ] 결과 순위 매기기 정확
- [ ] 요약 생성 완료

### Phase 8 (DB 통합) 완료 기준
- [ ] 모든 테이블 생성 완료
- [ ] Migration 성공
- [ ] 모든 Agent가 DB 연동 동작
- [ ] 데이터 무결성 검증

### Phase 9 (테스트) 완료 기준
- [ ] 단위 테스트 커버리지 > 80%
- [ ] 통합 테스트 100% 통과
- [ ] E2E 테스트 통과
- [ ] 성능 테스트 통과 (응답 시간 < 10초)

---

## 위험 요소 및 대응

### 기술적 위험

1. **영양소 DB 부족**
   - 위험: 한국 음식 영양소 데이터 부족
   - 대응: 식품의약품안전처 API 연동 또는 수동 DB 구축

2. **운동 추천 정확도**
   - 위험: 부상 위험이 있는 잘못된 추천
   - 대응: 전문가 검증, 보수적인 추천

3. **알림 발송 실패**
   - 위험: 카카오톡 API 연동 문제
   - 대응: 이메일 백업, 재시도 로직

### 비즈니스 위험

1. **사용자 데이터 부족**
   - 위험: 초기 사용자 프로필 데이터 부족
   - 대응: 기본값 제공, 점진적 학습

2. **DB 마이그레이션 복잡도**
   - 위험: 기존 데이터 마이그레이션 실패
   - 대응: 철저한 백업, 단계별 마이그레이션

---

## 참고 문서

- [시스템 아키텍처 명세서](../../manual/시스템_아키텍처_명세서_251103.md)
- [DB 스키마](../../manual/DB_스키마_251103.dbml)
- [Phase 1 계획서](./implementation_plan2_251104.md)

---

## 다음 단계

승인 후:
1. Phase 1부터 순차적으로 시작
2. 매 Phase마다 검증 체크리스트 확인
3. 완료 후 다음 Phase 진행

**준비 완료!**
