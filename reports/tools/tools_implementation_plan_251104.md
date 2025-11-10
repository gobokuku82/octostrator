# Fitness PT Manager - Tool 구현 계획서

**작성일**: 2025-11-04
**버전**: 1.0.0
**상태**: 계획 단계

---

## 1. 개요

### 1.1 목적

현재 각 에이전트가 직접 데이터베이스를 쿼리하고 비즈니스 로직을 수행하고 있습니다. 이를 **재사용 가능한 Tool 모듈로 분리**하여:

1. **코드 재사용성 향상**: 여러 에이전트가 동일한 Tool 공유
2. **유지보수성 향상**: 비즈니스 로직을 Tool에서 중앙 관리
3. **테스트 용이성**: Tool 단위로 독립적인 테스트 가능
4. **LangChain 패턴 준수**: Tool 기반 아키텍처로 확장성 확보

### 1.2 현재 상태

**에이전트가 직접 수행하는 작업**:

| 에이전트 | 현재 구현 | 문제점 |
|----------|-----------|--------|
| **DietAgent** | 직접 `MealLog` 테이블 쿼리 | DB 로직이 에이전트에 하드코딩 |
| **WorkoutAgent** | 직접 `WorkoutRoutine`, `ExerciseDB` 쿼리 | 운동 선택 로직이 에이전트에 하드코딩 |
| **ScheduleAgent** | 직접 `Schedule` 테이블 쿼리 | 스케줄 생성 로직이 에이전트에 하드코딩 |
| **MemberCareAgent** | 직접 `User`, `MemberProgress` 쿼리 | 분석 로직이 에이전트에 하드코딩 |
| **CoachingAgent** | 직접 FAISS 검색 수행 | 벡터 검색 로직이 에이전트에 하드코딩 |

**예시** (diet/agent.py:44-66):
```python
# 현재: 에이전트가 직접 DB 쿼리
with get_db() as db:
    meal_logs = db.query(MealLog).order_by(MealLog.date.desc()).limit(3).all()
    # ... 결과 가공 로직 ...
```

### 1.3 목표 구조

**Tool로 분리 후**:
```python
# 에이전트는 Tool을 호출만 수행
from backend.app.octostrator.tools.diet_tools import get_meal_logs_tool

result = await get_meal_logs_tool.ainvoke({"user_id": 1, "limit": 3})
```

**장점**:
- ✅ 에이전트는 "언제 어떤 Tool을 호출할지"만 결정 (Orchestration)
- ✅ Tool은 "어떻게 수행할지"를 담당 (Business Logic)
- ✅ 다른 에이전트도 동일한 Tool 재사용 가능

---

## 2. Tool 분류 및 우선순위

### 2.1 Tool 카테고리

| 카테고리 | 파일 위치 | 설명 |
|----------|-----------|------|
| **Diet Tools** | `backend/app/octostrator/tools/diet_tools.py` | 식단 관련 CRUD 및 분석 |
| **Workout Tools** | `backend/app/octostrator/tools/workout_tools.py` | 운동 루틴 생성 및 관리 |
| **Schedule Tools** | `backend/app/octostrator/tools/schedule_tools.py` | PT 스케줄 관리 |
| **Member Care Tools** | `backend/app/octostrator/tools/member_care_tools.py` | 회원 관리 및 분석 |
| **Coaching Tools** | `backend/app/octostrator/tools/coaching_tools.py` | 자료 검색 및 북마크 |
| **Common Tools** | `backend/app/octostrator/tools/common_tools.py` | 공통 유틸리티 (날짜 파싱 등) |

### 2.2 구현 우선순위

**Phase 1 (우선순위: 높음)** - 기본 CRUD Tools
1. Diet Tools: 식단 조회/저장
2. Workout Tools: 운동 조회/저장
3. Schedule Tools: 스케줄 조회/생성
4. Member Care Tools: 회원 정보 조회

**Phase 2 (우선순위: 중간)** - 분석 & 생성 Tools
1. Diet Tools: 영양소 계산, 피드백 생성
2. Workout Tools: 개인화된 루틴 생성
3. Member Care Tools: 진행률 분석
4. Coaching Tools: 벡터 검색

**Phase 3 (우선순위: 낮음)** - 고급 기능 Tools
1. 자연어 파싱 Tools (식단 입력, 스케줄 요청)
2. 알림 발송 Tools
3. 북마크 관리 Tools
4. 리포트 생성 Tools

---

## 3. 세부 Tool 설계

### 3.1 Diet Tools

**파일**: `backend/app/octostrator/tools/diet_tools.py`

#### Tool 목록

| Tool 이름 | 설명 | 우선순위 | 입력 | 출력 |
|-----------|------|----------|------|------|
| `get_meal_logs_tool` | 식단 기록 조회 | P1 | `user_id`, `limit`, `date_range` | `List[MealLog]` |
| `save_meal_log_tool` | 식단 기록 저장 | P1 | `user_id`, `meal_type`, `foods`, `nutrition` | `MealLog` |
| `parse_meal_input_tool` | 자연어 식단 파싱 | P3 | `user_input` (예: "아침에 계란 2개") | `{"meal_type": "아침", "foods": [...]}` |
| `calculate_nutrition_tool` | 영양소 계산 | P2 | `foods` 리스트 | `{"calories": 350, "protein": 18, ...}` |
| `generate_diet_feedback_tool` | 일일 피드백 생성 | P2 | `user_id`, `date` | `str` (피드백 텍스트) |

#### 구현 예시: `get_meal_logs_tool`

```python
from langchain.tools import Tool
from backend.database.relation_db.models import MealLog
from backend.database.relation_db.session import get_db
from typing import List, Optional
from datetime import datetime
import json


def get_meal_logs(
    user_id: int,
    limit: int = 10,
    date_range: Optional[tuple] = None
) -> List[dict]:
    """식단 기록 조회

    Args:
        user_id: 회원 ID
        limit: 조회 개수 (기본 10개)
        date_range: 날짜 범위 (start_date, end_date)

    Returns:
        List[dict]: 식단 기록 리스트
    """
    try:
        with get_db() as db:
            query = db.query(MealLog).filter(MealLog.user_id == user_id)

            if date_range:
                start_date, end_date = date_range
                query = query.filter(
                    MealLog.date >= start_date,
                    MealLog.date <= end_date
                )

            meal_logs = query.order_by(MealLog.date.desc()).limit(limit).all()

            result = []
            for log in meal_logs:
                result.append({
                    "id": log.id,
                    "date": log.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "meal_type": log.meal_type,
                    "foods": json.loads(log.foods),
                    "nutrition": json.loads(log.nutrition)
                })

            return result
    except Exception as e:
        raise Exception(f"식단 조회 실패: {str(e)}")


# LangChain Tool로 래핑
get_meal_logs_tool = Tool(
    name="get_meal_logs",
    description="사용자의 식단 기록을 조회합니다.",
    func=lambda user_id, limit=10, date_range=None: get_meal_logs(user_id, limit, date_range)
)
```

---

### 3.2 Workout Tools

**파일**: `backend/app/octostrator/tools/workout_tools.py`

#### Tool 목록

| Tool 이름 | 설명 | 우선순위 | 입력 | 출력 |
|-----------|------|----------|------|------|
| `get_workout_history_tool` | 운동 기록 조회 | P1 | `user_id`, `limit`, `muscle_group` | `List[WorkoutRoutine]` |
| `save_workout_routine_tool` | 운동 루틴 저장 | P1 | `user_id`, `muscle_group`, `exercises` | `WorkoutRoutine` |
| `search_exercises_tool` | 운동 데이터베이스 검색 | P1 | `muscle_group`, `difficulty`, `limit` | `List[ExerciseDB]` |
| `generate_workout_routine_tool` | 개인화된 루틴 생성 | P2 | `user_id`, `goal`, `muscle_group` | `List[Exercise]` |
| `analyze_user_profile_tool` | 사용자 프로필 분석 | P2 | `user_id` | `{"level": "초급", "goal": "체중감량", ...}` |

---

### 3.3 Schedule Tools

**파일**: `backend/app/octostrator/tools/schedule_tools.py`

#### Tool 목록

| Tool 이름 | 설명 | 우선순위 | 입력 | 출력 |
|-----------|------|----------|------|------|
| `get_schedules_tool` | 스케줄 조회 | P1 | `user_id`, `start_date`, `end_date` | `List[Schedule]` |
| `create_schedule_tool` | 스케줄 생성 | P1 | `user_id`, `trainer_id`, `date`, `notes` | `Schedule` |
| `update_schedule_tool` | 스케줄 수정 | P1 | `schedule_id`, `status`, `notes` | `Schedule` |
| `check_availability_tool` | 가용 시간 확인 | P2 | `trainer_id`, `date_range` | `List[datetime]` |

---

### 3.4 Member Care Tools

**파일**: `backend/app/octostrator/tools/member_care_tools.py`

#### Tool 목록

| Tool 이름 | 설명 | 우선순위 | 입력 | 출력 |
|-----------|------|----------|------|------|
| `get_member_info_tool` | 회원 정보 조회 | P1 | `user_id` 또는 `name` | `User` |
| `get_member_progress_tool` | 진행률 조회 | P1 | `user_id`, `limit` | `List[MemberProgress]` |
| `analyze_member_progress_tool` | 진행률 분석 | P2 | `user_id`, `date_range` | `{"trend": "상승", "changes": {...}}` |
| `detect_events_tool` | 이벤트 감지 | P2 | `user_id` | `List[Event]` (재등록 알림 등) |

---

### 3.5 Coaching Tools

**파일**: `backend/app/octostrator/tools/coaching_tools.py`

#### Tool 목록

| Tool 이름 | 설명 | 우선순위 | 입력 | 출력 |
|-----------|------|----------|------|------|
| `search_materials_tool` | FAISS 벡터 검색 | P2 | `query`, `top_k`, `filter` | `List[Material]` |
| `embed_query_tool` | 쿼리 임베딩 | P2 | `query` | `np.array` (384 dim) |
| `rank_results_tool` | 검색 결과 순위화 | P2 | `results`, `criteria` | `List[Material]` |
| `save_bookmark_tool` | 북마크 저장 | P3 | `user_id`, `material_id`, `title`, `url` | `Bookmark` |

---

### 3.6 Common Tools

**파일**: `backend/app/octostrator/tools/common_tools.py`

#### Tool 목록

| Tool 이름 | 설명 | 우선순위 | 입력 | 출력 |
|-----------|------|----------|------|------|
| `parse_date_tool` | 자연어 날짜 파싱 | P2 | `date_str` (예: "내일", "다음 주 월요일") | `datetime` |
| `format_date_tool` | 날짜 포맷팅 | P2 | `datetime`, `format` | `str` |
| `send_notification_tool` | 알림 발송 | P3 | `user_id`, `message`, `channel` | `bool` |

---

## 4. 에이전트 리팩토링 계획

### 4.1 현재 구조 (Before)

**파일**: `backend/app/octostrator/agents/diet/agent.py:44-66`

```python
# 에이전트가 직접 DB 쿼리
async def diet_agent_node(state: SupervisorState) -> Dict:
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    try:
        with get_db() as db:
            meal_logs = db.query(MealLog).order_by(MealLog.date.desc()).limit(3).all()
            # 결과 가공 로직...
    except Exception as e:
        result = f"Error: {str(e)}"

    return {"plan": plan, "current_step": current_step + 1}
```

**문제점**:
- ❌ DB 쿼리 로직이 에이전트에 하드코딩
- ❌ 다른 에이전트가 식단 조회 필요 시 코드 중복

### 4.2 목표 구조 (After)

```python
from backend.app.octostrator.tools.diet_tools import get_meal_logs_tool

async def diet_agent_node(state: SupervisorState) -> Dict:
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    try:
        # Tool 호출로 간소화
        user_id = state.get("user_id", 1)
        meal_logs = await get_meal_logs_tool.ainvoke({
            "user_id": user_id,
            "limit": 3
        })

        # 결과 포맷팅만 담당
        result_text = format_meal_logs(meal_logs)
    except Exception as e:
        result = f"[DietAgent] Error: {str(e)}"

    return {"plan": plan, "current_step": current_step + 1}
```

**장점**:
- ✅ 에이전트는 Tool 호출과 결과 표현만 담당
- ✅ DB 쿼리 로직은 Tool에서 중앙 관리
- ✅ 다른 에이전트도 재사용 가능

---

## 5. 구현 로드맵

### Phase 1: 기본 CRUD Tools (2-3일)

**작업 항목**:

1. **Tool 모듈 생성**
   - [ ] `backend/app/octostrator/tools/__init__.py` 생성
   - [ ] `backend/app/octostrator/tools/diet_tools.py` 생성
   - [ ] `backend/app/octostrator/tools/workout_tools.py` 생성
   - [ ] `backend/app/octostrator/tools/schedule_tools.py` 생성
   - [ ] `backend/app/octostrator/tools/member_care_tools.py` 생성

2. **Diet Tools 구현**
   - [ ] `get_meal_logs_tool`: 식단 기록 조회
   - [ ] `save_meal_log_tool`: 식단 기록 저장

3. **Workout Tools 구현**
   - [ ] `get_workout_history_tool`: 운동 기록 조회
   - [ ] `search_exercises_tool`: 운동 DB 검색

4. **에이전트 리팩토링**
   - [ ] `diet/agent.py` 리팩토링 (Tool 사용)
   - [ ] `workout/agent.py` 리팩토링
   - [ ] `schedule/agent.py` 리팩토링
   - [ ] `member_care/agent.py` 리팩토링

### Phase 2: 분석 & 생성 Tools (3-4일)

1. **Diet Tools 고급 기능**
   - [ ] `calculate_nutrition_tool`: 영양소 계산 (API 연동)
   - [ ] `generate_diet_feedback_tool`: 피드백 생성

2. **Workout Tools 고급 기능**
   - [ ] `generate_workout_routine_tool`: 개인화된 루틴 생성

3. **Coaching Tools 구현**
   - [ ] `embed_query_tool`: 쿼리 임베딩 (OpenAI API)
   - [ ] `search_materials_tool`: FAISS 벡터 검색
   - [ ] `coaching/agent.py` 리팩토링

### Phase 3: 고급 기능 Tools (4-5일)

1. **자연어 파싱 Tools**
   - [ ] `parse_meal_input_tool`: 식단 입력 파싱
   - [ ] `parse_schedule_request_tool`: 스케줄 요청 파싱

2. **알림 발송 Tools**
   - [ ] `send_notification_tool`: 이메일/SMS 발송

---

## 6. 디렉토리 구조

```
AI_PTmanager/beta_v001/
├── backend/
│   ├── app/
│   │   └── octostrator/
│   │       ├── tools/                          # ← 새로 추가
│   │       │   ├── __init__.py
│   │       │   ├── diet_tools.py
│   │       │   ├── workout_tools.py
│   │       │   ├── schedule_tools.py
│   │       │   ├── member_care_tools.py
│   │       │   ├── coaching_tools.py
│   │       │   └── common_tools.py
│   │       └── agents/
│   │           ├── diet/agent.py               # Tool 사용으로 리팩토링
│   │           ├── workout/agent.py
│   │           ├── schedule/agent.py
│   │           ├── member_care/agent.py
│   │           └── coaching/agent.py
│   └── database/
└── tests/                                       # ← 테스트 추가
    └── tools/
        ├── test_diet_tools.py
        ├── test_workout_tools.py
        └── test_coaching_tools.py
```

---

## 7. 주의사항

### 7.1 데이터베이스 세션 관리

```python
# 좋은 예: context manager 사용
with get_db() as db:
    meal_logs = db.query(MealLog).all()

# 나쁜 예: 세션을 닫지 않음 → 메모리 누수
db = SessionLocal()
meal_logs = db.query(MealLog).all()
```

### 7.2 에러 핸들링

```python
try:
    result = get_meal_logs(user_id=1)
except Exception as e:
    # 명확한 에러 메시지 필수
    raise Exception(f"식단 조회 실패 (user_id={user_id}): {str(e)}")
```

### 7.3 Tool 버전 관리

```python
# 하위 호환성 유지: 새 파라미터는 기본값 제공
def get_meal_logs(user_id: int, limit: int = 10, include_deleted: bool = False):
    ...
```

---

## 8. 성공 기준

### Phase 1 완료 기준
- ✅ 모든 CRUD Tool 구현 완료
- ✅ 모든 에이전트 리팩토링 완료
- ✅ Frontend에서 기존 기능 정상 동작

### Phase 2 완료 기준
- ✅ 분석 & 생성 Tool 구현 완료
- ✅ FAISS 벡터 검색 Tool 구현 완료

### Phase 3 완료 기준
- ✅ 자연어 파싱 Tool 구현 완료
- ✅ 알림 발송 Tool 구현 완료

---

## 9. 결론

### 9.1 Tool 분리의 이점

1. **재사용성**: 여러 에이전트가 동일한 Tool 공유
2. **유지보수성**: 비즈니스 로직을 Tool에서 중앙 관리
3. **테스트 용이성**: Tool 단위로 독립적인 테스트 가능
4. **확장성**: LangChain Tool Calling으로 자동 Tool 선택 가능

### 9.2 구현 순서

**Phase 1 (2-3일)** → **Phase 2 (3-4일)** → **Phase 3 (4-5일)**

총 **9-12일** 예상

### 9.3 다음 단계

1. **Phase 1 착수**: 기본 CRUD Tools 구현
2. **에이전트 리팩토링**: Tool 사용으로 전환
3. **회귀 테스트**: Frontend에서 기존 기능 동작 확인

---

**작성자**: Claude (AI Assistant)
**최종 업데이트**: 2025-11-04
**버전**: 1.0.0
