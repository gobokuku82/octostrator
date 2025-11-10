# WorkoutAgent 구현 계획서

**작성일**: 2025-11-04
**버전**: 1.0 (간단 버전)
**Agent 역할**: 운동 루틴 추천 - 사용자의 목표/경험치를 기반으로 운동 루틴을 생성 및 제안

---

## 1. Agent 개요

### 1.1 목적
- 사용자의 운동 목표와 경험 수준을 분석하여 맞춤형 운동 루틴 생성
- 간단하고 실용적인 운동 계획 제공
- 초보자도 쉽게 따라할 수 있는 운동 추천

### 1.2 핵심 기능 (간단 버전)
1. **사용자 정보 분석**: 목표, 경험 수준, 운동 가능 시간 파악
2. **운동 루틴 생성**: 목표에 맞는 운동 종목 및 세트/반복 횟수 추천
3. **운동 설명 제공**: 각 운동의 수행 방법 간단 설명

---

## 2. Agent 구조 설계

### 2.1 State 정의

```python
# agents/workout_agent/state.py

from typing import TypedDict, Annotated, List, Dict, Optional
from operator import add

class WorkoutAgentState(TypedDict):
    """WorkoutAgent State Schema"""

    # ⭐ 입력 (사용자 정보)
    query: str                          # 사용자 요청 ("초보자를 위한 운동 추천해줘")
    user_id: Optional[int]              # ⭐ 사용자 ID (DB 조회용)
    user_profile: Dict[str, str]        # 사용자 프로필
    # {
    #   "goal": "weight_loss" | "muscle_gain" | "fitness",
    #   "level": "beginner" | "intermediate" | "advanced",
    #   "available_time": "30분" | "1시간" | "1시간 30분",
    #   "workout_location": "집" | "헬스장"
    # }

    # 중간 처리
    analyzed_goal: str                  # 분석된 목표
    workout_plan: Dict[str, any]        # 생성된 운동 계획
    # {
    #   "title": "초보자 체중 감량 루틴",
    #   "duration": "30분",
    #   "exercises": [
    #     {
    #       "name": "스쿼트",
    #       "sets": 3,
    #       "reps": 15,
    #       "rest": "30초",
    #       "description": "다리를 어깨 너비로 벌리고..."
    #     }
    #   ]
    # }

    # ⭐ 출력
    response: str                       # 최종 응답 메시지
    saved_routine_id: Optional[int]     # ⭐ 저장된 루틴 ID (DB 저장 시)

    # 에러
    errors: Annotated[List[str], add]   # 에러 목록
```

### 2.2 Agent Graph 구조

```
[START]
   ↓
[analyze_user] ─────────────> 사용자 정보 분석
   ↓                          (목표, 수준, 시간 파악)
   ↓
[generate_workout] ─────────> 운동 루틴 생성
   ↓                          (운동 종목, 세트, 반복 결정)
   ↓
[format_response] ──────────> 응답 포맷팅
   ↓                          (읽기 쉬운 형식으로 변환)
   ↓
[END]
```

---

## 3. 데이터베이스 연동 설계

### 3.1 데이터베이스 구조

**위치**: `C:\kdy\Projects\AI_PTmanager\beta_v001\backend\database`

```
database/
├── relation_db/          # 관계형 DB (SQLite)
│   ├── models.py         # DB 모델 정의
│   ├── session.py        # DB 세션 관리
│   └── mock_data.py      # Mock 데이터 생성 ⭐
├── vector_db/            # 벡터 DB
└── unstructured_db/      # 비구조화 DB
```

### 3.2 관련 테이블 (models.py)

#### 1) ExerciseDB (운동 데이터베이스) ⭐ 핵심 테이블
```python
class ExerciseDB(Base):
    __tablename__ = "exercise_db"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))              # 운동 이름 (예: "스쿼트")
    muscle_group = Column(String(50))       # 근육 그룹 (legs, chest, back, shoulders, arms)
    difficulty = Column(String(20))         # 난이도 (beginner, intermediate, advanced)
    equipment = Column(String(100))         # 장비 (barbell, dumbbell, bodyweight, machine)
    description = Column(Text)              # 운동 설명
    video_url = Column(String(500))         # 참고 영상 URL
```

**Mock 데이터 예시**:
- 스쿼트 (legs, beginner, barbell)
- 벤치프레스 (chest, intermediate, barbell)
- 데드리프트 (back, advanced, barbell)
- 런지 (legs, beginner, bodyweight)
- 풀업 (back, intermediate, bodyweight)

#### 2) WorkoutRoutine (운동 루틴 기록)
```python
class WorkoutRoutine(Base):
    __tablename__ = "workout_routines"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    muscle_group = Column(String(50))
    exercises = Column(Text)  # JSON: [{"name": "스쿼트", "sets": 4, "reps": 10, "weight": 80}]
```

#### 3) User (사용자 정보)
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    goal = Column(String(50))     # weight_loss, muscle_gain, fitness
    level = Column(String(20))    # beginner, intermediate, advanced
```

**Mock 사용자**:
- 김철수 (muscle_gain, intermediate)
- 이영희 (weight_loss, beginner)
- 박민수 (fitness, advanced)

#### 4) MemberProgress (진행률 추적)
```python
class MemberProgress(Base):
    __tablename__ = "member_progress"

    user_id = Column(Integer)
    weight = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass = Column(Float)
```

### 3.3 Database Tool 구현

WorkoutAgent가 DB와 연동하기 위한 Tool을 추가합니다.

```python
# tools/database_tool.py (기존 파일 확장)

from backend.database.relation_db.session import get_db
from backend.database.relation_db.models import ExerciseDB, WorkoutRoutine, User
import json

def get_exercises_by_criteria(
    muscle_group: str = None,
    difficulty: str = None,
    equipment: str = None
) -> list[dict]:
    """
    조건에 맞는 운동 목록 조회

    Args:
        muscle_group: 근육 그룹 (legs, chest, back 등)
        difficulty: 난이도 (beginner, intermediate, advanced)
        equipment: 장비 (bodyweight, barbell 등)

    Returns:
        운동 정보 리스트
    """
    with get_db() as db:
        query = db.query(ExerciseDB)

        if muscle_group:
            query = query.filter(ExerciseDB.muscle_group == muscle_group)
        if difficulty:
            query = query.filter(ExerciseDB.difficulty == difficulty)
        if equipment:
            query = query.filter(ExerciseDB.equipment == equipment)

        exercises = query.all()

        return [
            {
                "id": ex.id,
                "name": ex.name,
                "muscle_group": ex.muscle_group,
                "difficulty": ex.difficulty,
                "equipment": ex.equipment,
                "description": ex.description,
                "video_url": ex.video_url
            }
            for ex in exercises
        ]


def get_user_profile(user_id: int) -> dict:
    """사용자 프로필 조회"""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        return {
            "id": user.id,
            "name": user.name,
            "goal": user.goal,
            "level": user.level
        }


def save_workout_routine(user_id: int, muscle_group: str, exercises: list[dict]) -> int:
    """
    생성된 운동 루틴 DB에 저장

    Args:
        user_id: 사용자 ID
        muscle_group: 주요 근육 그룹
        exercises: 운동 리스트 [{"name": "스쿼트", "sets": 4, "reps": 10}]

    Returns:
        생성된 루틴 ID
    """
    from datetime import datetime

    with get_db() as db:
        routine = WorkoutRoutine(
            user_id=user_id,
            date=datetime.now(),
            muscle_group=muscle_group,
            exercises=json.dumps(exercises, ensure_ascii=False)
        )
        db.add(routine)
        db.commit()
        db.refresh(routine)

        return routine.id


# Tool Registry에 등록
from .registry import tool_registry

tool_registry.register(
    name="get_exercises_db",
    tool_func=get_exercises_by_criteria,
    description="DB에서 조건에 맞는 운동 목록 조회",
    parameters={
        "muscle_group": {"type": "string", "required": False},
        "difficulty": {"type": "string", "required": False},
        "equipment": {"type": "string", "required": False}
    }
)

tool_registry.register(
    name="get_user_profile",
    tool_func=get_user_profile,
    description="사용자 프로필 정보 조회",
    parameters={
        "user_id": {"type": "integer", "required": True}
    }
)

tool_registry.register(
    name="save_workout_routine",
    tool_func=save_workout_routine,
    description="생성된 운동 루틴 DB에 저장",
    parameters={
        "user_id": {"type": "integer", "required": True},
        "muscle_group": {"type": "string", "required": True},
        "exercises": {"type": "array", "required": True}
    }
)
```

### 3.4 WorkoutAgent에 DB Tool 추가

```python
# agents/workout_agent/agent.py

class WorkoutAgent(BaseAgent):
    def __init__(self):
        config = AgentConfig(
            name="workout_agent",
            description="운동 루틴 추천 - DB 기반 개인화 루틴 생성",
            llm_model="gpt-4",
            temperature=0.5,
            tools=[
                "llm_tool",
                "get_exercises_db",      # ⭐ DB 운동 조회
                "get_user_profile",      # ⭐ 사용자 정보 조회
                "save_workout_routine"   # ⭐ 루틴 저장
            ],
            subgraphs=[]
        )
        super().__init__(config)
```

### 3.5 Mock 데이터 활용 시나리오

#### 시나리오 1: 초보자 사용자 (이영희)
```python
# 입력
{
    "user_id": 2,  # 이영희 (weight_loss, beginner)
    "query": "집에서 할 수 있는 운동 알려줘"
}

# DB에서 가져올 데이터
user_profile = {"goal": "weight_loss", "level": "beginner"}
exercises = get_exercises_db(difficulty="beginner", equipment="bodyweight")
# → 런지, 풀업 등

# 생성된 루틴
{
    "title": "초보자 홈 트레이닝",
    "exercises": [
        {"name": "런지", "sets": 3, "reps": 12},
        # ExerciseDB에서 가져온 description, video_url 포함
    ]
}

# DB에 저장
routine_id = save_workout_routine(user_id=2, muscle_group="legs", exercises=[...])
```

#### 시나리오 2: 중급자 사용자 (김철수)
```python
# 입력
{
    "user_id": 1,  # 김철수 (muscle_gain, intermediate)
    "query": "하체 운동 루틴 만들어줘"
}

# DB 조회
exercises = get_exercises_db(muscle_group="legs", difficulty="intermediate")
# → 스쿼트 등

# 생성 및 저장
routine = {...}
save_workout_routine(user_id=1, muscle_group="legs", exercises=[...])
```

---

## 4. Node 구현 상세 (DB 연동 포함)

### 4.1 Node 1: analyze_user (사용자 분석 + DB 조회) ⭐ 업데이트

**역할**:
1. DB에서 사용자 프로필 조회
2. 사용자 요청 분석하여 운동 목표 파악

```python
# agents/workout_agent/nodes/analyze.py

from ..state import WorkoutAgentState
from ....tools.registry import tool_registry

def analyze_user(state: WorkoutAgentState) -> WorkoutAgentState:
    """
    사용자 정보 분석 (DB 연동)
    - DB에서 사용자 프로필 조회
    - 목표, 수준, 시간 분석
    """

    try:
        query = state["query"]
        user_id = state.get("user_id")  # ⭐ user_id 추가

        # ⭐ DB에서 사용자 프로필 조회
        if user_id:
            get_user_profile_tool = tool_registry.get("get_user_profile")
            db_profile = get_user_profile_tool(user_id=user_id)

            if db_profile:
                # DB 프로필을 state에 병합
                state["user_profile"] = {
                    "goal": db_profile.get("goal", "fitness"),
                    "level": db_profile.get("level", "beginner"),
                    "available_time": state.get("user_profile", {}).get("available_time", "30분"),
                    "workout_location": state.get("user_profile", {}).get("workout_location", "집")
                }
            else:
                # DB에 사용자 없으면 기본값 사용
                state["user_profile"] = state.get("user_profile", {
                    "goal": "fitness",
                    "level": "beginner",
                    "available_time": "30분",
                    "workout_location": "집"
                })

        profile = state["user_profile"]

        # LLM을 사용하여 목표 분석
        llm_tool = tool_registry.get("llm_tool")

        prompt = f"""
사용자 요청: {query}
사용자 프로필:
- 목표: {profile.get('goal')}
- 수준: {profile.get('level')}
- 가능 시간: {profile.get('available_time')}
- 운동 장소: {profile.get('workout_location')}

위 정보를 바탕으로 사용자의 주요 운동 목표를 한 줄로 명확하게 요약하세요.
예시: "30분 내 집에서 할 수 있는 초보자 체중 감량 운동"
"""

        analyzed_goal = llm_tool(
            prompt=prompt,
            model="gpt-4",
            temperature=0.3
        )

        state["analyzed_goal"] = analyzed_goal

        return state

    except Exception as e:
        state["errors"].append(f"분석 오류: {str(e)}")
        return state
```

### 4.2 Node 2: generate_workout (운동 루틴 생성 + DB 활용) ⭐ 업데이트

**역할**:
1. DB ExerciseDB에서 조건에 맞는 운동 조회
2. 조회된 운동을 기반으로 LLM이 루틴 생성
3. 생성된 루틴을 WorkoutRoutine 테이블에 저장

```python
# agents/workout_agent/nodes/generate.py

from ..state import WorkoutAgentState
from ....tools.registry import tool_registry
import json

def generate_workout(state: WorkoutAgentState) -> WorkoutAgentState:
    """
    운동 루틴 생성 (DB 연동)
    - ExerciseDB에서 운동 조회
    - LLM으로 루틴 구성
    - WorkoutRoutine에 저장
    """

    try:
        analyzed_goal = state["analyzed_goal"]
        profile = state.get("user_profile", {})
        user_id = state.get("user_id")

        # ⭐ 1. DB에서 적합한 운동 목록 조회
        get_exercises_tool = tool_registry.get("get_exercises_db")

        # 조건 설정
        difficulty = profile.get('level', 'beginner')
        equipment = "bodyweight" if profile.get('workout_location') == "집" else None

        # DB 조회
        available_exercises = get_exercises_tool(
            difficulty=difficulty,
            equipment=equipment
        )

        # 운동이 없으면 전체 조회
        if not available_exercises:
            available_exercises = get_exercises_tool()

        # ⭐ 2. LLM에게 DB의 운동 목록 제공하여 루틴 생성
        llm_tool = tool_registry.get("llm_tool")

        # DB 운동 목록을 텍스트로 변환
        exercises_text = "\n".join([
            f"- {ex['name']} ({ex['muscle_group']}, {ex['difficulty']}, {ex['equipment']})"
            for ex in available_exercises
        ])

        prompt = f"""
목표: {analyzed_goal}
수준: {profile.get('level', '초보자')}
시간: {profile.get('available_time', '30분')}
장소: {profile.get('workout_location', '집')}

**사용 가능한 운동 목록 (DB에서 조회):**
{exercises_text}

위의 DB에 있는 운동들 중에서 선택하여 효과적인 루틴을 JSON 형식으로 생성하세요.

형식:
{{
  "title": "운동 루틴 제목",
  "duration": "예상 소요 시간",
  "muscle_group": "주요 타겟 근육군",
  "exercises": [
    {{
      "name": "운동 이름 (DB 목록에서 선택)",
      "sets": 세트 수,
      "reps": 반복 횟수,
      "rest": "휴식 시간"
    }}
  ],
  "notes": "추가 주의사항"
}}

주의: 반드시 위의 DB 운동 목록에 있는 이름을 정확히 사용하세요.
"""

        workout_json = llm_tool(
            prompt=prompt,
            model="gpt-4",
            temperature=0.5
        )

        # JSON 파싱
        try:
            workout_plan = json.loads(workout_json)
        except:
            # JSON 파싱 실패 시 기본 템플릿
            workout_plan = _create_default_workout_from_db(available_exercises, profile)

        # ⭐ 3. DB의 운동 상세 정보 추가 (description, video_url)
        exercises_map = {ex['name']: ex for ex in available_exercises}

        for exercise in workout_plan.get('exercises', []):
            exercise_name = exercise['name']
            if exercise_name in exercises_map:
                db_exercise = exercises_map[exercise_name]
                exercise['description'] = db_exercise.get('description', '')
                exercise['video_url'] = db_exercise.get('video_url', '')
                exercise['muscle_group'] = db_exercise.get('muscle_group', '')

        state["workout_plan"] = workout_plan

        # ⭐ 4. DB에 루틴 저장 (user_id가 있는 경우)
        if user_id:
            try:
                save_routine_tool = tool_registry.get("save_workout_routine")
                routine_id = save_routine_tool(
                    user_id=user_id,
                    muscle_group=workout_plan.get('muscle_group', 'full_body'),
                    exercises=workout_plan.get('exercises', [])
                )
                state["saved_routine_id"] = routine_id
                print(f"✓ 루틴 저장 완료: ID {routine_id}")
            except Exception as save_error:
                print(f"⚠ 루틴 저장 실패: {save_error}")
                # 저장 실패해도 루틴은 반환

        return state

    except Exception as e:
        state["errors"].append(f"루틴 생성 오류: {str(e)}")
        return state


def _create_default_workout_from_db(exercises: list[dict], profile: dict) -> dict:
    """
    DB 운동 목록에서 기본 루틴 생성 (LLM 실패 시)
    """
    if not exercises:
        return {
            "title": "기본 루틴",
            "duration": "30분",
            "muscle_group": "full_body",
            "exercises": [],
            "notes": "운동 데이터를 불러올 수 없습니다."
        }

    # 간단한 로직으로 운동 선택 (예: 처음 5개)
    selected = exercises[:5]

    return {
        "title": f"{profile.get('level', '초보자')} 루틴",
        "duration": profile.get('available_time', '30분'),
        "muscle_group": selected[0].get('muscle_group', 'full_body'),
        "exercises": [
            {
                "name": ex['name'],
                "sets": 3,
                "reps": 12,
                "rest": "60초",
                "description": ex.get('description', ''),
                "video_url": ex.get('video_url', ''),
                "muscle_group": ex.get('muscle_group', '')
            }
            for ex in selected
        ],
        "notes": "운동 전후 스트레칭을 꼭 하세요."
    }
```

### 4.3 Node 3: format_response (응답 포맷팅 + DB 정보 포함) ⭐ 업데이트

**역할**:
1. 운동 루틴을 Markdown으로 변환
2. DB에서 가져온 설명과 영상 URL 포함
3. 저장된 루틴 ID 안내

```python
# agents/workout_agent/nodes/format.py

from ..state import WorkoutAgentState

def format_response(state: WorkoutAgentState) -> WorkoutAgentState:
    """
    응답 포맷팅 (DB 정보 포함)
    - Markdown 형식으로 변환
    - 운동 설명 및 영상 URL 포함
    - 저장된 루틴 ID 안내
    """

    try:
        workout_plan = state["workout_plan"]
        saved_routine_id = state.get("saved_routine_id")

        response = f"""
# {workout_plan['title']}

**예상 소요 시간**: {workout_plan['duration']}
**타겟 근육군**: {workout_plan.get('muscle_group', '전신')}
"""

        # ⭐ 저장된 루틴 ID 표시
        if saved_routine_id:
            response += f"**저장된 루틴 ID**: #{saved_routine_id}\n"

        response += "\n---\n\n## 운동 목록\n\n"

        # ⭐ DB 정보 포함하여 운동 표시
        for idx, exercise in enumerate(workout_plan['exercises'], 1):
            response += f"""
### {idx}. {exercise['name']}
- **타겟**: {exercise.get('muscle_group', '-')}
- **세트**: {exercise['sets']}세트
- **반복**: {exercise['reps']}회
- **휴식**: {exercise['rest']}
"""

            # ⭐ DB에서 가져온 설명 추가
            if exercise.get('description'):
                response += f"- **방법**: {exercise['description']}\n"

            # ⭐ 영상 URL 추가
            if exercise.get('video_url'):
                response += f"- **참고 영상**: {exercise['video_url']}\n"

            response += "\n"

        response += f"""
---

## 주의사항
{workout_plan.get('notes', '무리하지 말고 천천히 진행하세요.')}

---

💪 **화이팅! 꾸준히 하는 것이 중요합니다!**
"""

        state["response"] = response

        return state

    except Exception as e:
        state["errors"].append(f"포맷팅 오류: {str(e)}")
        state["response"] = "운동 루틴 생성 중 오류가 발생했습니다."
        return state
```

---

## 4. Agent 클래스 구현

```python
# agents/workout_agent/agent.py

from typing import Dict
from langgraph.graph import StateGraph, END
from ..base.agent_base import BaseAgent, AgentConfig
from .state import WorkoutAgentState
from .nodes.analyze import analyze_user
from .nodes.generate import generate_workout
from .nodes.format import format_response

class WorkoutAgent(BaseAgent):
    """
    운동 루틴 추천 Agent

    사용자의 목표/경험치를 기반으로 맞춤형 운동 루틴을 생성합니다.
    """

    def __init__(self):
        config = AgentConfig(
            name="workout_agent",
            description="운동 루틴 추천 - 사용자의 목표/경험치를 기반으로 운동 루틴 생성 및 제안",
            llm_model="gpt-4",
            temperature=0.5,
            tools=["llm_tool"],          # LLM만 사용 (간단 버전)
            subgraphs=[]                 # SubGraph 미사용 (간단 버전)
        )
        super().__init__(config)

    def get_state_schema(self) -> type:
        return WorkoutAgentState

    def build_graph(self) -> StateGraph:
        """WorkoutAgent Graph 구성"""

        graph = StateGraph(WorkoutAgentState)

        # Nodes 추가
        graph.add_node("analyze_user", analyze_user)
        graph.add_node("generate_workout", generate_workout)
        graph.add_node("format_response", format_response)

        # Edges 정의 (선형 구조)
        graph.set_entry_point("analyze_user")
        graph.add_edge("analyze_user", "generate_workout")
        graph.add_edge("generate_workout", "format_response")
        graph.add_edge("format_response", END)

        return graph
```

---

## 5. Prompts 정의

```python
# agents/workout_agent/prompts.py

# 운동 목표 분석 프롬프트
ANALYZE_GOAL_PROMPT = """
당신은 전문 피트니스 트레이너입니다.

사용자 요청: {query}
사용자 프로필:
- 목표: {goal}
- 수준: {level}
- 가능 시간: {available_time}
- 운동 장소: {workout_location}

위 정보를 바탕으로 사용자의 주요 운동 목표를 한 줄로 명확하게 요약하세요.
"""

# 운동 루틴 생성 프롬프트
GENERATE_WORKOUT_PROMPT = """
당신은 전문 피트니스 트레이너입니다.

목표: {analyzed_goal}
수준: {level}
시간: {available_time}
장소: {workout_location}

위 조건에 맞는 효과적인 운동 루틴을 생성하세요.

요구사항:
1. 초보자도 따라할 수 있는 기본 운동 위주
2. 5-7개의 운동으로 구성
3. 준비운동과 마무리 스트레칭 포함
4. 각 운동의 정확한 수행 방법 설명

JSON 형식으로 출력하세요:
{{
  "title": "운동 루틴 제목",
  "duration": "예상 소요 시간",
  "warm_up": "준비운동 방법",
  "exercises": [
    {{
      "name": "운동 이름",
      "target": "주요 타겟 부위",
      "sets": 세트 수,
      "reps": 반복 횟수 또는 시간,
      "rest": "세트 간 휴식 시간",
      "description": "자세한 수행 방법",
      "tips": "주의사항 및 팁"
    }}
  ],
  "cool_down": "마무리 스트레칭 방법",
  "notes": "전체적인 주의사항 및 팁"
}}
"""

# 운동 설명 프롬프트
EXERCISE_DESCRIPTION_PROMPT = """
운동 이름: {exercise_name}

위 운동의 정확한 수행 방법을 초보자도 이해할 수 있도록 단계별로 설명하세요.

포함 내용:
1. 시작 자세
2. 동작 수행 방법 (단계별)
3. 호흡 방법
4. 흔한 실수 및 주의사항
"""
```

---

## 6. 테스트 시나리오

### 6.1 기본 테스트

```python
# tests/test_agents/test_workout_agent.py

import pytest
from backend.app.octostrator.agents.workout_agent.agent import WorkoutAgent

@pytest.fixture
def agent():
    """WorkoutAgent fixture"""
    return WorkoutAgent()

@pytest.mark.asyncio
async def test_basic_workout_recommendation(agent):
    """기본 운동 추천 테스트"""

    input_data = {
        "query": "초보자를 위한 체중 감량 운동 추천해주세요",
        "user_profile": {
            "goal": "체중 감량",
            "level": "초보자",
            "available_time": "30분",
            "workout_location": "집"
        },
        "errors": []
    }

    result = await agent.invoke(input_data)

    # 검증
    assert result is not None
    assert "workout_plan" in result
    assert "response" in result
    assert len(result["errors"]) == 0
    assert "운동 목록" in result["response"]

@pytest.mark.asyncio
async def test_advanced_workout_recommendation(agent):
    """중급자 운동 추천 테스트"""

    input_data = {
        "query": "근력 향상을 위한 운동 루틴",
        "user_profile": {
            "goal": "근력 향상",
            "level": "중급자",
            "available_time": "1시간",
            "workout_location": "헬스장"
        },
        "errors": []
    }

    result = await agent.invoke(input_data)

    assert result is not None
    assert result["workout_plan"]["duration"] == "1시간"
    assert len(result["workout_plan"]["exercises"]) >= 5

@pytest.mark.asyncio
async def test_error_handling(agent):
    """에러 처리 테스트"""

    input_data = {
        "query": "",  # 빈 쿼리
        "user_profile": {},
        "errors": []
    }

    result = await agent.invoke(input_data)

    # 에러가 발생하더라도 기본 응답은 있어야 함
    assert "response" in result
```

### 6.2 통합 테스트

```python
@pytest.mark.asyncio
async def test_full_workflow():
    """전체 워크플로우 테스트"""

    from backend.app.octostrator.agents.registry import agent_registry

    # Agent 등록 확인
    assert agent_registry.is_registered("workout_agent")

    # Agent 가져오기
    agent = agent_registry.get("workout_agent")

    # 실행
    result = await agent.invoke({
        "query": "집에서 할 수 있는 운동 알려줘",
        "user_profile": {
            "goal": "체력 증진",
            "level": "초보자",
            "available_time": "30분",
            "workout_location": "집"
        },
        "errors": []
    })

    # 검증
    assert result["response"].startswith("#")  # Markdown 형식
    print("\n" + result["response"])  # 결과 출력
```

---

## 7. Mock 데이터 테스트 ⭐ 신규 추가

### 7.1 Mock 데이터 준비

**위치**: `backend/database/relation_db/mock_data.py`

현재 Mock 데이터가 생성 중이므로, 다음 명령으로 DB에 데이터를 삽입합니다:

```bash
# Mock 데이터 생성 스크립트 실행
cd backend/database/relation_db
python mock_data.py
```

**생성되는 데이터**:
- **사용자 3명**: 김철수(중급자), 이영희(초보자), 박민수(고급자)
- **운동 5개**: 스쿼트, 벤치프레스, 데드리프트, 런지, 풀업
- **기존 루틴 2개**: 김철수 하체, 박민수 가슴

### 7.2 Mock 사용자로 테스트

#### 테스트 1: 이영희 (초보자, 체중 감량) ⭐
```python
@pytest.mark.asyncio
async def test_with_mock_user_beginner():
    """Mock 사용자 - 이영희 (초보자)"""

    from backend.app.octostrator.agents.workout_agent.agent import WorkoutAgent

    agent = WorkoutAgent()

    # 이영희 user_id = 2
    result = await agent.invoke({
        "user_id": 2,  # ⭐ DB에서 프로필 자동 조회
        "query": "집에서 할 수 있는 운동 추천해주세요",
        "user_profile": {
            "available_time": "30분",
            "workout_location": "집"
        },
        "errors": []
    })

    # 검증
    assert result is not None
    assert result["user_profile"]["goal"] == "weight_loss"  # DB에서 조회됨
    assert result["user_profile"]["level"] == "beginner"    # DB에서 조회됨
    assert "saved_routine_id" in result  # DB에 저장됨
    assert "런지" in result["response"]  # beginner + bodyweight 운동 포함

    print("\n=== 이영희 운동 루틴 ===")
    print(result["response"])
```

#### 테스트 2: 김철수 (중급자, 근력 향상) ⭐
```python
@pytest.mark.asyncio
async def test_with_mock_user_intermediate():
    """Mock 사용자 - 김철수 (중급자)"""

    agent = WorkoutAgent()

    # 김철수 user_id = 1
    result = await agent.invoke({
        "user_id": 1,
        "query": "하체 운동 루틴 만들어줘",
        "user_profile": {
            "available_time": "1시간",
            "workout_location": "헬스장"
        },
        "errors": []
    })

    # 검증
    assert result["user_profile"]["goal"] == "muscle_gain"
    assert result["user_profile"]["level"] == "intermediate"
    assert "스쿼트" in result["response"]  # legs + intermediate 운동
    assert result.get("saved_routine_id") is not None

    print("\n=== 김철수 운동 루틴 ===")
    print(result["response"])
```

#### 테스트 3: 박민수 (고급자, 체력 증진) ⭐
```python
@pytest.mark.asyncio
async def test_with_mock_user_advanced():
    """Mock 사용자 - 박민수 (고급자)"""

    agent = WorkoutAgent()

    result = await agent.invoke({
        "user_id": 3,
        "query": "전신 운동 루틴",
        "user_profile": {
            "available_time": "1시간 30분",
            "workout_location": "헬스장"
        },
        "errors": []
    })

    # 검증
    assert result["user_profile"]["level"] == "advanced"
    assert len(result["workout_plan"]["exercises"]) >= 5
    # 고급자 운동 포함 (데드리프트 등)

    print("\n=== 박민수 운동 루틴 ===")
    print(result["response"])
```

### 7.3 DB 데이터 확인 테스트

```python
def test_exercise_db_query():
    """ExerciseDB 조회 테스트"""

    from backend.app.octostrator.tools.database_tool import get_exercises_by_criteria

    # 초보자 맨몸 운동 조회
    exercises = get_exercises_by_criteria(
        difficulty="beginner",
        equipment="bodyweight"
    )

    assert len(exercises) > 0
    assert exercises[0]["name"] == "런지"  # Mock 데이터 확인
    assert exercises[0]["description"] is not None
    assert exercises[0]["video_url"] is not None

    print("\n=== 초보자 맨몸 운동 목록 ===")
    for ex in exercises:
        print(f"- {ex['name']} ({ex['muscle_group']}, {ex['equipment']})")


def test_user_profile_query():
    """사용자 프로필 조회 테스트"""

    from backend.app.octostrator.tools.database_tool import get_user_profile

    # 이영희 조회
    user = get_user_profile(user_id=2)

    assert user is not None
    assert user["name"] == "이영희"
    assert user["goal"] == "weight_loss"
    assert user["level"] == "beginner"

    print("\n=== 이영희 프로필 ===")
    print(user)


def test_save_workout_routine():
    """운동 루틴 저장 테스트"""

    from backend.app.octostrator.tools.database_tool import save_workout_routine

    routine_id = save_workout_routine(
        user_id=2,
        muscle_group="legs",
        exercises=[
            {"name": "런지", "sets": 3, "reps": 12, "rest": "60초"},
            {"name": "스쿼트", "sets": 3, "reps": 15, "rest": "60초"}
        ]
    )

    assert routine_id is not None
    assert isinstance(routine_id, int)

    print(f"\n✓ 루틴 저장 완료: ID {routine_id}")
```

### 7.4 전체 플로우 테스트 (DB 포함)

```python
@pytest.mark.asyncio
async def test_full_workflow_with_database():
    """DB 연동 전체 워크플로우 테스트"""

    from backend.app.octostrator.agents.workout_agent.agent import WorkoutAgent
    from backend.database.relation_db.session import get_db
    from backend.database.relation_db.models import WorkoutRoutine

    agent = WorkoutAgent()

    # 1. Agent 실행 (DB 사용)
    result = await agent.invoke({
        "user_id": 2,  # 이영희
        "query": "30분 홈 트레이닝 추천",
        "user_profile": {
            "available_time": "30분",
            "workout_location": "집"
        },
        "errors": []
    })

    # 2. 응답 검증
    assert len(result["errors"]) == 0
    assert result["saved_routine_id"] is not None

    # 3. DB에 실제로 저장되었는지 확인
    routine_id = result["saved_routine_id"]

    with get_db() as db:
        saved_routine = db.query(WorkoutRoutine).filter(
            WorkoutRoutine.id == routine_id
        ).first()

        assert saved_routine is not None
        assert saved_routine.user_id == 2
        assert saved_routine.muscle_group is not None

        # exercises JSON 파싱
        import json
        exercises = json.loads(saved_routine.exercises)
        assert len(exercises) > 0

    print("\n✓ 전체 플로우 테스트 성공!")
    print(f"✓ 루틴 ID {routine_id}가 DB에 저장됨")
    print(f"✓ 운동 개수: {len(exercises)}개")
    print("\n" + result["response"])
```

### 7.5 예상 출력 (Mock 데이터 사용 시)

```
=== 이영희 운동 루틴 ===

# 초보자 홈 트레이닝

**예상 소요 시간**: 30분
**타겟 근육군**: legs
**저장된 루틴 ID**: #5

---

## 운동 목록

### 1. 런지
- **타겟**: legs
- **세트**: 3세트
- **반복**: 12회
- **휴식**: 60초
- **방법**: 하체 균형과 근력 향상
- **참고 영상**: https://youtube.com/lunge

### 2. 풀업
- **타겟**: back
- **세트**: 3세트
- **반복**: 8회
- **휴식**: 90초
- **방법**: 등 근육 발달
- **참고 영상**: https://youtube.com/pullup

---

## 주의사항
운동 전후 스트레칭을 꼭 하세요.

---

💪 **화이팅! 꾸준히 하는 것이 중요합니다!**
```

---

## 8. 구현 단계 (DB 연동 포함)

### Phase 1: DB Tool 구현 (1일) ⭐ 신규
- [ ] `tools/database_tool.py` 확장
- [ ] `get_exercises_by_criteria()` 함수 구현
- [ ] `get_user_profile()` 함수 구현
- [ ] `save_workout_routine()` 함수 구현
- [ ] Tool Registry에 등록
- [ ] ⭐ Mock 데이터 생성 스크립트 실행
- [ ] DB 연결 테스트

### Phase 2: 기본 구조 (1일)
- [ ] `agents/workout_agent/` 디렉토리 생성
- [ ] `state.py` 작성 (user_id, saved_routine_id 포함)
- [ ] `agent.py` 기본 구조 작성 (DB Tool 포함)
- [ ] Registry 등록

### Phase 3: Node 구현 (2일) ⭐ DB 연동
- [ ] `nodes/analyze.py` 구현 (DB 사용자 프로필 조회)
- [ ] `nodes/generate.py` 구현 (DB 운동 조회 + 루틴 저장)
- [ ] `nodes/format.py` 구현 (DB 정보 포함 포맷팅)
- [ ] 기본 템플릿 추가

### Phase 4: 프롬프트 최적화 (1일)
- [ ] `prompts.py` 작성
- [ ] LLM 프롬프트 튜닝 (DB 운동 목록 활용)
- [ ] 응답 품질 개선

### Phase 5: 테스트 (1.5일) ⭐ DB 테스트 추가
- [ ] DB Tool 단위 테스트
- [ ] Mock 사용자 테스트 (이영희, 김철수, 박민수)
- [ ] Agent 통합 테스트 (DB 저장 확인)
- [ ] 전체 워크플로우 테스트

### Phase 6: Supervisor 통합 (0.5일)
- [ ] Router에 "workout_recommendation" 매핑 추가
- [ ] End-to-End 테스트

**총 소요 예상 시간**: 7일 → **1주일** (DB 연동 포함)

---

## 8. 확장 계획 (향후)

### 8.1 단기 확장 (간단 → 중급)
- [ ] **운동 기록 기능**: DB에 사용자의 운동 기록 저장
- [ ] **진행도 추적**: 운동 완료 여부 체크
- [ ] **운동 영상 링크**: YouTube 등 참고 영상 제공

### 8.2 중기 확장 (중급 → 고급)
- [ ] **RAG SubGraph 통합**: 운동 DB에서 검색
- [ ] **개인화**: 사용자의 과거 기록 기반 추천
- [ ] **부상 방지**: 특정 부위 제외 옵션
- [ ] **운동 대체**: 장비가 없을 때 대체 운동 추천

### 8.3 장기 확장 (고급)
- [ ] **AI 피드백**: 운동 자세 분석 (이미지/비디오)
- [ ] **영양 연계**: DietAgent와 통합
- [ ] **스케줄링**: ScheduleAgent와 통합
- [ ] **커뮤니티**: 다른 사용자와 루틴 공유

---

## 9. 사용 예시

### 9.1 API 호출 예시

```python
# FastAPI 엔드포인트에서 호출
from backend.app.octostrator.agents.registry import agent_registry

@app.post("/api/workout/recommend")
async def recommend_workout(request: WorkoutRequest):
    """운동 루틴 추천 API"""

    # Agent 가져오기
    agent = agent_registry.get("workout_agent")

    # 입력 데이터 구성
    input_data = {
        "query": request.query,
        "user_profile": {
            "goal": request.goal,
            "level": request.level,
            "available_time": request.time,
            "workout_location": request.location
        },
        "errors": []
    }

    # Agent 실행
    result = await agent.invoke(input_data)

    return {
        "success": len(result["errors"]) == 0,
        "workout_plan": result["workout_plan"],
        "response": result["response"],
        "errors": result["errors"]
    }
```

### 9.2 사용자 시나리오

**시나리오 1: 초보자 홈 트레이닝**
```
사용자: "집에서 할 수 있는 30분 운동 알려줘. 나는 초보자야."

→ WorkoutAgent 응답:
# 초보자 홈 트레이닝 루틴

**예상 소요 시간**: 30분

## 운동 목록

### 1. 제자리 걷기 (워밍업)
- 세트: 1세트
- 반복: 5분
- 휴식: 1분
- 방법: 제자리에서 무릎을 들어 올리며 걷기

### 2. 스쿼트
- 세트: 3세트
- 반복: 15회
- 휴식: 30초
...
```

**시나리오 2: 헬스장 근력 운동**
```
사용자: "헬스장에서 1시간 근력 운동 루틴 짜줘. 중급자 수준이야."

→ WorkoutAgent 응답:
# 중급자 근력 향상 루틴

**예상 소요 시간**: 1시간

## 운동 목록

### 1. 벤치 프레스
- 세트: 4세트
- 반복: 10회
- 휴식: 90초
...
```

---

## 10. 파일 구조 요약

```
backend/app/octostrator/agents/workout_agent/
├── __init__.py
├── agent.py              # WorkoutAgent 클래스
├── state.py              # WorkoutAgentState 정의
├── prompts.py            # 프롬프트 템플릿
└── nodes/
    ├── __init__.py
    ├── analyze.py        # 사용자 분석 노드
    ├── generate.py       # 운동 루틴 생성 노드
    └── format.py         # 응답 포맷팅 노드
```

---

## 11. 다음 단계

1. **이 문서 검토** ✅
2. **Phase 1 시작**: 디렉토리 및 기본 구조 생성
3. **간단한 프로토타입 테스트**: 1개 운동만 추천하는 최소 버전
4. **점진적 개선**: 운동 개수 증가 및 품질 향상
5. **Supervisor 통합**: 전체 시스템과 연동

---

## 12. 데이터베이스 연동 요약 ⭐

### 12.1 주요 변경사항

| 항목 | 기존 (간단 버전) | 업데이트 (DB 연동) |
|------|-----------------|-------------------|
| **사용자 정보** | State에 직접 입력 | DB User 테이블에서 조회 |
| **운동 목록** | LLM이 임의 생성 | DB ExerciseDB에서 조회 |
| **운동 설명** | 간단한 텍스트 | DB의 description + video_url |
| **루틴 저장** | 미지원 | DB WorkoutRoutine에 자동 저장 |
| **개인화** | 제한적 | 사용자 프로필 기반 운동 추천 |

### 12.2 DB 활용 플로우

```
1. 사용자 요청 (user_id 포함)
   ↓
2. [analyze_user]
   → DB User 테이블 조회 (goal, level)
   ↓
3. [generate_workout]
   → DB ExerciseDB 조회 (difficulty, equipment 필터링)
   → LLM이 DB 운동 목록에서 선택하여 루틴 구성
   → DB WorkoutRoutine에 저장
   ↓
4. [format_response]
   → DB의 description, video_url 포함하여 응답 생성
   ↓
5. 사용자에게 루틴 반환 (저장된 routine_id 포함)
```

### 12.3 Mock 데이터 구조

**사용자 (User)**:
| ID | 이름 | 목표 | 수준 |
|----|------|------|------|
| 1 | 김철수 | muscle_gain | intermediate |
| 2 | 이영희 | weight_loss | beginner |
| 3 | 박민수 | fitness | advanced |

**운동 (ExerciseDB)**:
| 이름 | 근육군 | 난이도 | 장비 |
|------|--------|--------|------|
| 스쿼트 | legs | beginner | barbell |
| 벤치프레스 | chest | intermediate | barbell |
| 데드리프트 | back | advanced | barbell |
| 런지 | legs | beginner | bodyweight |
| 풀업 | back | intermediate | bodyweight |

### 12.4 핵심 장점

1. **데이터 일관성**: DB에 표준화된 운동 정보 저장
2. **재사용성**: 한 번 입력한 운동 정보를 모든 Agent가 활용
3. **이력 추적**: 사용자별 루틴 저장으로 진행도 파악 가능
4. **확장 가능성**: 향후 운동 추가 시 DB만 업데이트
5. **품질 보장**: LLM이 임의로 만드는 것이 아닌 검증된 운동 사용

### 12.5 다음 단계 (DB 확장)

- [ ] ExerciseDB에 더 많은 운동 추가 (현재 5개 → 50개+)
- [ ] 운동별 칼로리 소모량 추가
- [ ] 사용자의 과거 루틴 분석하여 개인화 강화
- [ ] MemberProgress와 연동하여 체성분 변화 고려
- [ ] 운동 완료 체크 기능 (WorkoutLog 테이블)

---

**참고 문서**:
- [AGENT_SYSTEM_DESIGN_251104.md](./AGENT_SYSTEM_DESIGN_251104.md) - 전체 Agent 시스템 설계
- [CODE_TEMPLATES_251104.md](./CODE_TEMPLATES_251104.md) - 코드 템플릿
- [IMPLEMENTATION_CHECKLIST_251104.md](./IMPLEMENTATION_CHECKLIST_251104.md) - 구현 체크리스트
- **Database Models**: `backend/database/relation_db/models.py`
- **Mock Data**: `backend/database/relation_db/mock_data.py`

---

**버전 히스토리**:
- v1.0 (2025-11-04): 초기 간단 버전 작성
- v1.1 (2025-11-04): ⭐ 데이터베이스 연동 추가 (ExerciseDB, User, WorkoutRoutine)

---

**문서 끝**
