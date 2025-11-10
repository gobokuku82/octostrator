# AI PT Manager - 에이전트 예시 질문 & 복합 작동 구조

작성일: 2025-11-04
버전: Phase 1 (Tool 기반 리팩토링 완료)

## 목차

1. [복합 에이전트 작동 구조](#복합-에이전트-작동-구조)
2. [Mock 데이터 개요](#mock-데이터-개요)
3. [단일 에이전트 예시 질문](#단일-에이전트-예시-질문)
4. [복합 에이전트 예시 질문](#복합-에이전트-예시-질문)
5. [예상 응답 예시](#예상-응답-예시)

---

## 복합 에이전트 작동 구조

### 시스템 아키텍처: Supervisor Pattern

**AI PT Manager는 복합 에이전트 작동이 가능한 구조입니다.**

```
사용자 질문
    ↓
Intent Understanding (의도 파악)
    ↓
Planning (작업 분해)
    ↓
Executor (동적 라우팅)
    ↓
Agent 1 → Executor → Agent 2 → ... → Executor
    ↓
Aggregator (결과 종합)
    ↓
Output Router
    ↓
Generator (Chat/Graph/Report)
```

### 핵심 메커니즘

1. **Intent Understanding (의도 파악)**
   - 사용자 질문을 분석하여 7가지 카테고리로 분류
   - 카테고리: `diet_query`, `workout_query`, `schedule_query`, `member_report`, `coaching_search`, `multi_step_task`, `progress_comparison`

2. **Planning (작업 분해)**
   - 복잡한 요청을 여러 개의 `TaskStep`으로 분해
   - 각 TaskStep은 특정 Agent에 할당됨
   - 예: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘"
     - Step 1: MemberCareAgent - 회원 정보 조회
     - Step 2: WorkoutAgent - 운동 기록 조회
     - Step 3: DietAgent - 식단 기록 조회
     - Step 4: ScheduleAgent - PT 스케줄 생성

3. **Executor (동적 라우팅)**
   - Command 패턴으로 각 Agent를 순차 실행
   - 모든 Agent는 작업 완료 후 Executor로 복귀
   - Executor가 다음 TaskStep을 결정하여 다음 Agent 호출

4. **Aggregator (결과 종합)**
   - 모든 Agent의 실행 결과를 수집
   - 구조화된 데이터로 변환
   - 인사이트 생성 및 요약

### 복합 에이전트 작동 예시

**사용자 질문**: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘"

```python
# Planning 결과 (TaskStep 리스트)
plan = [
    {
        "step": 1,
        "description": "김철수 회원 정보 조회",
        "agent": "member_care",
        "status": "pending"
    },
    {
        "step": 2,
        "description": "김철수 운동 기록 조회",
        "agent": "workout",
        "status": "pending"
    },
    {
        "step": 3,
        "description": "김철수 식단 기록 조회",
        "agent": "diet",
        "status": "pending"
    },
    {
        "step": 4,
        "description": "김철수 PT 스케줄 생성",
        "agent": "schedule",
        "status": "pending"
    }
]

# Executor 실행 흐름
# Executor → MemberCareAgent → Executor (Step 1 완료)
# Executor → WorkoutAgent → Executor (Step 2 완료)
# Executor → DietAgent → Executor (Step 3 완료)
# Executor → ScheduleAgent → Executor (Step 4 완료)
# Executor → Aggregator (모든 Step 완료)
```

---

## Mock 데이터 개요

### 사용자 (Users)

| ID | 이름 | 이메일 | 목표 | 레벨 |
|----|------|--------|------|------|
| 1 | 김철수 | kim@example.com | muscle_gain | intermediate |
| 2 | 이영희 | lee@example.com | weight_loss | beginner |
| 3 | 박민수 | park@example.com | fitness | advanced |
| 100 | 트레이너_홍길동 | trainer@example.com | fitness | advanced |

### 식단 기록 (Meal Logs)

- **김철수** (user_id=1):
  - 아침: 계란 3개, 현미밥 1공기, 김치 50g (450kcal, 단백질 30g)
  - 점심: 닭가슴살 200g, 샐러드 1접시 (350kcal, 단백질 45g)
- **이영희** (user_id=2):
  - 아침: 오트밀 1컵, 바나나 1개 (280kcal, 단백질 8g)

### 운동 루틴 (Workout Routines)

- **김철수** (user_id=1):
  - 하체: 스쿼트 4세트 x 10회 (80kg), 런지 3세트 x 12회
- **박민수** (user_id=3):
  - 가슴: 벤치프레스 4세트 x 8회 (100kg)

### PT 스케줄 (Schedules)

- **김철수** (user_id=1):
  - 내일 오후 3시, 트레이너: 홍길동, 60분, 상태: confirmed, 메모: "하체 집중 PT"
- **이영희** (user_id=2):
  - 모레 오전 10시, 트레이너: 홍길동, 60분, 상태: confirmed, 메모: "유산소 + 다이어트 상담"

### 회원 진행률 (Member Progress)

- **김철수** (user_id=1):
  - 1주차 (7일 전): 체중 75.5kg, 체지방 18.5%, 근육량 60.2kg
  - 2주차 (오늘): 체중 76.0kg, 체지방 17.8%, 근육량 61.0kg
  - 변화: 체중 +0.5kg, 체지방 -0.7%, 근육량 +0.8kg
- **이영희** (user_id=2):
  - 1주차 (7일 전): 체중 65.0kg, 체지방 28.0%, 근육량 45.5kg

### 운동 데이터베이스 (Exercise DB)

- 스쿼트 (legs, beginner, barbell)
- 벤치프레스 (chest, intermediate, barbell)
- 데드리프트 (back, advanced, barbell)
- 런지 (legs, beginner, bodyweight)
- 풀업 (back, intermediate, bodyweight)

---

## 단일 에이전트 예시 질문

### 1. DietAgent (식단 관련)

#### Q1: "오늘 먹은 음식 보여줘"
**사용 Tool**: `get_meal_logs(user_id=1, limit=10)`

**Intent**: `diet_query`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "사용자의 최근 식단 기록 조회",
      "agent": "diet",
      "status": "pending"
    }
  ]
}
```

**예상 응답**:
```
[DietAgent] 사용자의 최근 식단 기록 조회

최근 식단 기록:

- breakfast (2025-11-04 08:30:00): 계란 3개, 현미밥 1공기, 김치 50g
  영양소: 450kcal, 단백질 30g

- lunch (2025-11-04 12:45:00): 닭가슴살 200g, 샐러드 1접시
  영양소: 350kcal, 단백질 45g


오늘의 총 섭취량:
- 칼로리: 800kcal
- 단백질: 75g
- 탄수화물: 65g
- 지방: 23g
(총 2끼)
```

---

#### Q2: "김철수 회원 식단 분석해줘"
**사용 Tool**: `get_meal_logs(user_id=1)`, `get_daily_nutrition_summary(user_id=1)`

**Intent**: `diet_query`

**예상 응답**:
```
[DietAgent] 김철수 회원 식단 분석

최근 식단 기록:
- breakfast (2025-11-04 08:30:00): 계란 3개, 현미밥 1공기, 김치 50g
  영양소: 450kcal, 단백질 30g

- lunch (2025-11-04 12:45:00): 닭가슴살 200g, 샐러드 1접시
  영양소: 350kcal, 단백질 45g

오늘의 총 섭취량:
- 칼로리: 800kcal
- 단백질: 75g
- 탄수화물: 65g
- 지방: 23g
(총 2끼)
```

---

### 2. WorkoutAgent (운동 루틴)

#### Q3: "최근 운동 기록 보여줘"
**사용 Tool**: `get_workout_history(user_id=1, limit=2)`, `search_exercises(limit=3)`

**Intent**: `workout_query`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "사용자의 최근 운동 기록 조회",
      "agent": "workout",
      "status": "pending"
    }
  ]
}
```

**예상 응답**:
```
[WorkoutAgent] 사용자의 최근 운동 기록 조회

최근 운동 루틴:

- legs (2025-11-04):
  • 스쿼트: 4세트 x 10회 (80kg)
  • 런지: 3세트 x 12회

추천 운동 (3개):
- 스쿼트 (legs, beginner)
- 벤치프레스 (chest, intermediate)
- 데드리프트 (back, advanced)
```

---

#### Q4: "하체 운동 추천해줘"
**사용 Tool**: `search_exercises(limit=5)`

**Intent**: `workout_query`

**예상 응답**:
```
[WorkoutAgent] 하체 운동 추천

추천 운동 (2개):
- 스쿼트 (legs, beginner)
  설명: 하체 전체를 강화하는 기본 운동
  장비: barbell
  영상: https://youtube.com/squat

- 런지 (legs, beginner)
  설명: 하체 균형과 근력 향상
  장비: bodyweight
  영상: https://youtube.com/lunge
```

---

### 3. ScheduleAgent (PT 스케줄)

#### Q5: "다음 PT 일정 알려줘"
**사용 Tool**: `get_schedules(start_date=datetime.now(), limit=5)`, `get_member_info(user_id)`

**Intent**: `schedule_query`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "사용자의 예정된 PT 스케줄 조회",
      "agent": "schedule",
      "status": "pending"
    }
  ]
}
```

**예상 응답**:
```
[ScheduleAgent] 사용자의 예정된 PT 스케줄 조회

예정된 PT 스케줄 (2개):

- 2025-11-05 15:00:00
  회원: 김철수
  트레이너: 트레이너_홍길동
  상태: confirmed
  메모: 하체 집중 PT

- 2025-11-06 10:00:00
  회원: 이영희
  트레이너: 트레이너_홍길동
  상태: confirmed
  메모: 유산소 + 다이어트 상담
```

---

### 4. MemberCareAgent (회원 관리)

#### Q6: "김철수 회원 진행률 보고해줘"
**사용 Tool**: `get_member_info(user_id=1)`, `get_member_progress(user_id=1)`, `get_progress_comparison(user_id=1)`

**Intent**: `member_report`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "김철수 회원의 진행률 및 변화 분석",
      "agent": "member_care",
      "status": "pending"
    }
  ]
}
```

**예상 응답**:
```
[MemberCareAgent] 김철수 회원의 진행률 및 변화 분석

회원 현황 (1명):

📊 김철수 (kim@example.com)
   목표: muscle_gain, 레벨: intermediate
   최근 측정: 2025-11-04
   - 체중: 76.0kg
   - 체지방률: 17.8%
   - 근육량: 61.0kg
   변화: 체중 +0.5kg, 체지방 -0.7%, 근육 +0.8kg
   메모: 2주차: 체지방 감소, 근육량 증가
```

---

#### Q7: "모든 회원 현황 보여줘"
**사용 Tool**: `get_all_members(limit=10)`, `get_member_progress(user_id)` (각 회원별)

**Intent**: `member_report`

**예상 응답**:
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

📊 이영희 (lee@example.com)
   목표: weight_loss, 레벨: beginner
   최근 측정: 2025-10-28
   - 체중: 65.0kg
   - 체지방률: 28.0%
   - 근육량: 45.5kg
   메모: 1주차: 다이어트 시작

📊 박민수 (park@example.com)
   목표: fitness, 레벨: advanced
   (측정 기록 없음)
```

---

### 5. CoachingAgent (자료 검색)

#### Q8: "운동 자세 영상 찾아줘"
**사용 Tool**: `search_materials(query="운동 자세", top_k=3)`, `get_bookmarks(user_id=1, limit=3)`

**Intent**: `coaching_search`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "운동 자세 관련 자료 검색",
      "agent": "coaching",
      "status": "pending"
    }
  ]
}
```

**예상 응답**:
```
[CoachingAgent] 운동 자세 관련 자료 검색

검색 결과 (3개):

1. 스쿼트 정확한 자세 가이드 (video)
   설명: 무릎과 허리를 보호하는 올바른 스쿼트 자세
   URL: https://youtube.com/squat_form
   유사도 점수: 0.892

2. 벤치프레스 어깨 부상 예방 (article)
   설명: 안전한 벤치프레스를 위한 자세 체크리스트
   URL: https://fitness.com/bench_safety
   유사도 점수: 0.854

3. 데드리프트 허리 보호 방법 (video)
   설명: 허리 부상 없이 데드리프트하는 법
   URL: https://youtube.com/deadlift_back
   유사도 점수: 0.821

저장된 북마크 (2개):
- 초보자를 위한 PT 가이드 (guide)
- 근육량 증가 식단 (article)
```

---

## 복합 에이전트 예시 질문

### 복합 예시 1: 회원 종합 분석 + PT 스케줄

#### Q9: "김철수 회원의 운동, 식단, 진행률 확인하고 다음 PT 예약해줘"

**Intent**: `multi_step_task`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "김철수 회원 정보 및 진행률 조회",
      "agent": "member_care",
      "status": "pending"
    },
    {
      "step": 2,
      "description": "김철수 운동 기록 조회",
      "agent": "workout",
      "status": "pending"
    },
    {
      "step": 3,
      "description": "김철수 식단 기록 조회",
      "agent": "diet",
      "status": "pending"
    },
    {
      "step": 4,
      "description": "김철수 PT 스케줄 확인",
      "agent": "schedule",
      "status": "pending"
    }
  ]
}
```

**Executor 실행 순서**:
```
Executor → MemberCareAgent (Step 1 완료) → Executor
       → WorkoutAgent (Step 2 완료) → Executor
       → DietAgent (Step 3 완료) → Executor
       → ScheduleAgent (Step 4 완료) → Executor
       → Aggregator (모든 결과 종합)
```

**예상 응답** (Aggregator가 종합한 결과):
```
[Aggregator] 김철수 회원 종합 분석 및 PT 스케줄 확인 완료

=== 회원 정보 ===
이름: 김철수 (kim@example.com)
목표: 근육 증가 (muscle_gain)
레벨: 중급 (intermediate)

=== 진행률 ===
최근 측정: 2025-11-04
- 체중: 76.0kg (+0.5kg)
- 체지방률: 17.8% (-0.7%)
- 근육량: 61.0kg (+0.8kg)

✓ 긍정적 변화: 체지방 감소와 근육량 증가가 동시에 진행 중입니다.

=== 운동 기록 ===
최근 운동 (2025-11-04):
- 스쿼트: 4세트 x 10회 (80kg)
- 런지: 3세트 x 12회

=== 식단 분석 ===
오늘 섭취량:
- 칼로리: 800kcal
- 단백질: 75g
- 탄수화물: 65g
- 지방: 23g

⚠️ 권장사항: 근육 증가 목표를 위해 칼로리 섭취를 늘려주세요. (목표: 2500-3000kcal)

=== PT 스케줄 ===
다음 예정된 PT: 2025-11-05 15:00:00
트레이너: 홍길동
메모: 하체 집중 PT

---

💡 종합 인사이트:
김철수 회원은 2주간 체지방 감소(-0.7%)와 근육량 증가(+0.8kg)라는
긍정적인 변화를 보이고 있습니다. 하지만 근육 증가 목표를 위해서는
칼로리 섭취를 늘려야 합니다. 다음 PT(내일 오후 3시)에서는 하체 집중
훈련이 예정되어 있으니, PT 전에 충분한 탄수화물 섭취를 권장합니다.
```

---

### 복합 예시 2: 회원별 맞춤 운동 추천

#### Q10: "이영희 회원의 진행률 보고 맞춤 운동 추천해줘"

**Intent**: `multi_step_task`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "이영희 회원 정보 및 진행률 조회",
      "agent": "member_care",
      "status": "pending"
    },
    {
      "step": 2,
      "description": "이영희 운동 기록 조회",
      "agent": "workout",
      "status": "pending"
    },
    {
      "step": 3,
      "description": "체중 감량에 적합한 운동 추천",
      "agent": "workout",
      "status": "pending"
    },
    {
      "step": 4,
      "description": "관련 운동 자료 검색",
      "agent": "coaching",
      "status": "pending"
    }
  ]
}
```

**Executor 실행 순서**:
```
Executor → MemberCareAgent (Step 1 완료) → Executor
       → WorkoutAgent (Step 2 완료) → Executor
       → WorkoutAgent (Step 3 완료) → Executor
       → CoachingAgent (Step 4 완료) → Executor
       → Aggregator (모든 결과 종합)
```

**예상 응답**:
```
[Aggregator] 이영희 회원 맞춤 운동 추천

=== 회원 정보 ===
이름: 이영희 (lee@example.com)
목표: 체중 감량 (weight_loss)
레벨: 초급 (beginner)

=== 진행률 ===
최근 측정: 2025-10-28 (1주차)
- 체중: 65.0kg
- 체지방률: 28.0%
- 근육량: 45.5kg

=== 운동 기록 ===
(아직 운동 기록이 없습니다.)

=== 추천 운동 ===
체중 감량에 효과적인 운동:
1. 런지 (legs, beginner, bodyweight)
   - 하체 근력과 균형 향상
   - 칼로리 소모에 효과적

2. 스쿼트 (legs, beginner, barbell)
   - 하체 전체 근육 활성화
   - 대사량 증가

3. 풀업 (back, intermediate, bodyweight)
   - 상체 근력 강화
   - 칼로리 소모 증대

=== 추천 자료 ===
검색 결과 (2개):
1. 초보자를 위한 체중 감량 운동 (video)
   URL: https://youtube.com/weight_loss_beginner
   유사도 점수: 0.912

2. 체지방 감소 식단 가이드 (article)
   URL: https://fitness.com/fat_loss_diet
   유사도 점수: 0.878

---

💡 종합 인사이트:
이영희 회원은 초급 레벨로 체중 감량을 목표로 하고 있습니다.
아직 운동 기록이 없으므로, 초보자에게 적합한 bodyweight 운동부터
시작하는 것을 추천합니다. 런지와 스쿼트를 3세트 x 10-12회로 시작하고,
체력이 향상되면 점차 강도를 높여나가세요. 다음 PT는 모레 오전 10시에
예정되어 있으니, 유산소 + 다이어트 상담을 진행할 예정입니다.
```

---

### 복합 예시 3: 전체 회원 현황 + 스케줄 관리

#### Q11: "오늘 예정된 PT 확인하고 각 회원 상태 보고해줘"

**Intent**: `multi_step_task`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "오늘 예정된 PT 스케줄 조회",
      "agent": "schedule",
      "status": "pending"
    },
    {
      "step": 2,
      "description": "각 회원의 진행률 및 상태 조회",
      "agent": "member_care",
      "status": "pending"
    },
    {
      "step": 3,
      "description": "각 회원의 최근 운동 기록 조회",
      "agent": "workout",
      "status": "pending"
    },
    {
      "step": 4,
      "description": "각 회원의 최근 식단 기록 조회",
      "agent": "diet",
      "status": "pending"
    }
  ]
}
```

**Executor 실행 순서**:
```
Executor → ScheduleAgent (Step 1 완료) → Executor
       → MemberCareAgent (Step 2 완료) → Executor
       → WorkoutAgent (Step 3 완료) → Executor
       → DietAgent (Step 4 완료) → Executor
       → Aggregator (모든 결과 종합)
```

---

### 복합 예시 4: 식단 분석 + 운동 추천

#### Q12: "내 식단 분석하고 부족한 영양소 채울 수 있는 운동 추천해줘"

**Intent**: `multi_step_task`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "사용자의 식단 기록 및 영양소 분석",
      "agent": "diet",
      "status": "pending"
    },
    {
      "step": 2,
      "description": "영양소 부족 보완을 위한 운동 추천",
      "agent": "workout",
      "status": "pending"
    },
    {
      "step": 3,
      "description": "식단 관련 자료 검색",
      "agent": "coaching",
      "status": "pending"
    }
  ]
}
```

**Executor 실행 순서**:
```
Executor → DietAgent (Step 1 완료) → Executor
       → WorkoutAgent (Step 2 완료) → Executor
       → CoachingAgent (Step 3 완료) → Executor
       → Aggregator (모든 결과 종합)
```

**예상 응답**:
```
[Aggregator] 식단 분석 및 운동 추천

=== 식단 분석 ===
오늘 섭취량:
- 칼로리: 800kcal
- 단백질: 75g ✓ (목표 대비 충분)
- 탄수화물: 65g ⚠️ (목표 대비 부족)
- 지방: 23g ✓ (적정 수준)

⚠️ 영양소 분석:
- 칼로리 부족: 근육 증가 목표(muscle_gain)를 위해 최소 2500kcal 필요
- 탄수화물 부족: 운동 에너지원이 부족합니다. 복합 탄수화물 섭취 권장

=== 추천 운동 ===
탄수화물 대사를 활성화하는 운동:
1. 스쿼트 (legs, beginner)
   - 하체 대근육 활성화로 대사량 증가
   - 추천: 4세트 x 10-12회

2. 데드리프트 (back, advanced)
   - 전신 근육 활성화
   - 추천: 3세트 x 8-10회

=== 추천 자료 ===
검색 결과:
- 근육량 증가를 위한 탄수화물 섭취 가이드 (article)
- 운동 전후 영양 섭취 타이밍 (video)

---

💡 종합 인사이트:
단백질 섭취는 충분하지만, 근육 증가를 위한 칼로리와 탄수화물이
부족합니다. 운동 1-2시간 전에 복합 탄수화물(현미, 고구마, 귀리 등)을
섭취하면 운동 효율이 향상됩니다. 하체와 등 운동으로 대근육을
활성화하면 대사량이 증가하여 영양소 흡수가 개선됩니다.
```

---

### 복합 예시 5: 진행률 비교 + 맞춤 계획

#### Q13: "지난주와 이번주 진행률 비교하고 다음주 운동/식단 계획 세워줘"

**Intent**: `progress_comparison`

**Planning**:
```json
{
  "steps": [
    {
      "step": 1,
      "description": "회원 진행률 조회 및 비교",
      "agent": "member_care",
      "status": "pending"
    },
    {
      "step": 2,
      "description": "최근 운동 기록 조회",
      "agent": "workout",
      "status": "pending"
    },
    {
      "step": 3,
      "description": "최근 식단 기록 조회",
      "agent": "diet",
      "status": "pending"
    },
    {
      "step": 4,
      "description": "다음주 PT 스케줄 확인",
      "agent": "schedule",
      "status": "pending"
    },
    {
      "step": 5,
      "description": "진행률 개선을 위한 자료 검색",
      "agent": "coaching",
      "status": "pending"
    }
  ]
}
```

**Executor 실행 순서**:
```
Executor → MemberCareAgent (Step 1 완료) → Executor
       → WorkoutAgent (Step 2 완료) → Executor
       → DietAgent (Step 3 완료) → Executor
       → ScheduleAgent (Step 4 완료) → Executor
       → CoachingAgent (Step 5 완료) → Executor
       → Aggregator (모든 결과 종합)
```

**예상 응답**:
```
[Aggregator] 진행률 비교 및 다음주 계획

=== 진행률 비교 ===
📊 1주차 (2025-10-28) vs 2주차 (2025-11-04)

| 항목 | 1주차 | 2주차 | 변화 | 평가 |
|------|-------|-------|------|------|
| 체중 | 75.5kg | 76.0kg | +0.5kg | ✓ 근육 증가 |
| 체지방률 | 18.5% | 17.8% | -0.7% | ✓ 체지방 감소 |
| 근육량 | 60.2kg | 61.0kg | +0.8kg | ✓ 목표 달성 |

✓ 전체 평가: 우수 (체지방 감소 + 근육 증가)

=== 운동 분석 ===
이번주 운동:
- 하체: 스쿼트 4세트 x 10회 (80kg), 런지 3세트 x 12회

권장사항:
- 상체 운동 추가 필요 (가슴, 등, 어깨)
- 스쿼트 중량 증가 고려 (85kg → 90kg)

=== 식단 분석 ===
이번주 평균 섭취량:
- 칼로리: 800kcal/일
- 단백질: 75g/일

⚠️ 개선 필요:
- 칼로리를 2500-3000kcal로 증가
- 탄수화물 섭취 증가 (현재 65g → 목표 300g)
- 식사 횟수 증가 (2끼 → 5-6끼)

=== 다음주 계획 ===
PT 스케줄:
- 2025-11-05 15:00: 하체 집중 PT
- (추가 스케줄 권장: 상체 PT)

운동 계획:
- 월: 하체 (스쿼트, 데드리프트, 런지)
- 화: 가슴 + 삼두 (벤치프레스, 딥스)
- 수: 휴식
- 목: 등 + 이두 (풀업, 바벨로우)
- 금: 어깨 (오버헤드프레스, 레터럴레이즈)
- 토: 전신 순환 운동
- 일: 휴식

식단 계획:
- 아침: 계란 4개 + 현미밥 2공기 + 과일 (650kcal)
- 간식1: 닭가슴살 샐러드 + 견과류 (400kcal)
- 점심: 소고기 200g + 고구마 2개 + 채소 (800kcal)
- 간식2: 프로틴 쉐이크 + 바나나 (350kcal)
- 저녁: 생선 150g + 현미밥 1공기 + 샐러드 (600kcal)
- 간식3: 그릭요거트 + 베리류 (200kcal)
- 총: 3000kcal, 단백질 180g

=== 추천 자료 ===
검색 결과:
- 근육량 증가를 위한 식단 구성법 (article)
- 하체 운동 강도 올리는 법 (video)
- 체지방 감소 유지 전략 (article)

---

💡 종합 인사이트:
2주간 우수한 성과를 보였습니다! 체지방은 감소(-0.7%)하고
근육량은 증가(+0.8kg)했으니, 현재 방향이 올바릅니다.
하지만 칼로리 섭취가 부족하여 근육 증가 속도가 제한될 수 있습니다.

다음주는 다음 3가지에 집중하세요:
1. 칼로리를 3000kcal까지 늘리기 (소량씩 자주 먹기)
2. 상체 운동 추가하여 균형잡힌 발달
3. 스쿼트 중량 5kg 증가 시도

다음 PT(내일 오후 3시)에서 트레이너와 상체 운동 스케줄을
추가로 잡는 것을 권장합니다.
```

---

## 예상 응답 예시

### Aggregator의 역할

모든 복합 에이전트 질문에서 **Aggregator**는 다음 역할을 수행합니다:

1. **결과 수집**: 모든 Agent의 실행 결과를 수집
2. **구조화**: 데이터를 섹션별로 정리 (회원 정보, 진행률, 운동, 식단 등)
3. **인사이트 생성**: LLM을 사용하여 종합 분석 및 권장사항 생성
4. **출력 포맷**: 사용자에게 보기 쉬운 형태로 변환

### Output Router의 역할

**Output Router**는 사용자 요청에 따라 적절한 Generator를 선택합니다:

- **ChatGenerator**: 일반적인 대화형 답변 (기본값)
- **GraphGenerator**: 시각화가 필요한 경우 (진행률 그래프, 영양소 차트 등)
- **ReportGenerator**: 상세한 Markdown 보고서가 필요한 경우

---

## 정리

### 단일 에이전트 작동

- 사용자 질문이 단순하고 명확한 경우
- 하나의 Agent만 호출되어 처리
- 예: "오늘 먹은 음식 보여줘" → DietAgent만 실행

### 복합 에이전트 작동

- 사용자 질문이 복잡하고 여러 도메인에 걸쳐있는 경우
- Planning 단계에서 여러 TaskStep으로 분해
- Executor가 순차적으로 여러 Agent를 호출
- Aggregator가 모든 결과를 종합하여 인사이트 생성
- 예: "김철수 회원의 운동과 식단을 확인하고 PT 예약해줘"
  - MemberCareAgent → WorkoutAgent → DietAgent → ScheduleAgent → Aggregator

### 복합 에이전트 작동의 장점

1. **유연성**: 사용자 요청에 따라 동적으로 Agent 조합 가능
2. **재사용성**: 각 Agent는 독립적이므로 다양한 조합으로 활용 가능
3. **확장성**: 새로운 Agent 추가 시 기존 시스템과 쉽게 통합
4. **일관성**: Supervisor Pattern으로 중앙 집중식 관리
5. **인사이트**: Aggregator가 개별 결과를 종합하여 더 깊은 분석 제공

---

## 향후 확장 계획

### Phase 2: LLM Tool Calling

- Agent가 LLM을 통해 동적으로 Tool 선택
- 더 복잡한 추론 및 의사결정 가능

### Phase 3: Real-time Collaboration

- 여러 Agent가 병렬로 실행 (현재는 순차 실행)
- Agent 간 실시간 데이터 공유

### Phase 4: Advanced Planning

- 사용자 피드백을 반영한 동적 계획 수정
- HITL (Human-in-the-Loop) 실제 대기 및 승인

---

**작성일**: 2025-11-04
**버전**: Phase 1 (Tool 기반 리팩토링 완료)
**문서 위치**: `C:\kdy\Projects\AI_PTmanager\beta_v001\reports\tools\agent_example_questions_251104.md`
