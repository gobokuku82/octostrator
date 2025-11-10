# PT Manager User & Agent DB Schema

**작성일**: 2025-11-10
**데이터베이스**: PostgreSQL
**ORM**: SQLAlchemy (Async)
**모델 위치**: `C:\kdy\Projects\AI_PTmanager\beta_v001\backend\database\relation_db\models.py`

---

## 개요

PT 관리 시스템의 핵심 데이터베이스 스키마입니다.
- **User 중심 설계**: users 테이블을 중심으로 모든 데이터 연결
- **Agent별 테이블**: 8개 Agent의 전용 테이블 포함
- **관계형 구조**: ForeignKey로 데이터 무결성 보장

---

## DB Diagram (dbdiagram.io)

아래 코드를 [dbdiagram.io](https://dbdiagram.io)에 붙여넣으면 ER Diagram을 볼 수 있습니다.

```dbml
// ==================== Core Tables ====================

Table users {
  id INTEGER [pk, increment, note: 'Primary key']
  name VARCHAR(100) [not null, note: '사용자/회원 이름']
  email VARCHAR(255) [unique, note: '이메일 (고유)']
  phone VARCHAR(20) [note: '전화번호']
  goal VARCHAR(50) [note: 'weight_loss, muscle_gain, fitness']
  level VARCHAR(20) [note: 'beginner, intermediate, advanced']
  created_at DATETIME [default: `now()`, note: '생성 시간']

  Note: '사용자/회원 마스터 테이블 - 모든 관계의 중심'
}

// ==================== Workout & Health Tables ====================

Table meal_logs {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id, note: 'FK: users']
  date DATETIME [not null, note: '식사 날짜/시간']
  meal_type VARCHAR(20) [note: 'breakfast, lunch, dinner, snack, pre_workout, post_workout']
  foods TEXT [note: 'JSON: [{"name": "계란", "quantity": 2, "unit": "개"}]']
  nutrition TEXT [note: 'JSON: {"calories": 300, "protein": 24, ...}']
  total_calories FLOAT [note: '총 칼로리']
  total_protein FLOAT [note: '총 단백질 (g)']
  total_carbs FLOAT [note: '총 탄수화물 (g)']
  total_fat FLOAT [note: '총 지방 (g)']
  meal_photo_url VARCHAR(500) [note: '식사 사진 URL']
  notes TEXT [note: '메모']
  feedback TEXT [note: 'AI 피드백']
  quality_score FLOAT [note: '식단 품질 점수 (0.0 ~ 1.0)']
  created_at DATETIME [default: `now()`]

  Note: '식단 기록 테이블 (Nutrition Agent)'
}

Table workout_routines {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  date DATETIME [not null]
  muscle_group VARCHAR(50) [note: 'legs, chest, back, shoulders, arms']
  exercises TEXT [note: 'JSON: [{"name": "스쿼트", "sets": 4, "reps": 10, ...}]']
  created_at DATETIME [default: `now()`]

  Note: '운동 루틴 테이블 (Program Designer Agent)'
}

Table schedules {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  trainer_id INTEGER [ref: > users.id, note: 'FK: users (trainer)']
  date DATETIME [not null]
  duration_minutes INTEGER [default: 60]
  status VARCHAR(20) [note: 'confirmed, cancelled, completed']
  notes VARCHAR(500)
  created_at DATETIME [default: `now()`]

  Note: 'PT 스케줄 테이블 (Manager Agent)'
}

Table member_progress {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  date DATETIME [not null]
  weight FLOAT [note: '체중 (kg)']
  body_fat_percentage FLOAT [note: '체지방률 (%)']
  muscle_mass FLOAT [note: '근육량 (kg)']
  notes VARCHAR(500)
  created_at DATETIME [default: `now()`]

  Note: '회원 진행률 테이블 (Assessor Agent)'
}

Table bookmarks {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  title VARCHAR(255)
  url VARCHAR(500)
  category VARCHAR(50) [note: 'video, article, research']
  summary VARCHAR(1000)
  created_at DATETIME [default: `now()`]

  Note: '자료 북마크 테이블 (Trainer Education Agent)'
}

Table exercise_db {
  id INTEGER [pk, increment]
  name VARCHAR(100) [not null, note: '운동 이름']
  muscle_group VARCHAR(50) [note: 'legs, chest, back, shoulders, arms']
  difficulty VARCHAR(20) [note: 'beginner, intermediate, advanced']
  equipment VARCHAR(100) [note: 'barbell, dumbbell, bodyweight, machine']
  description TEXT
  video_url VARCHAR(500)
  created_at DATETIME [default: `now()`]

  Note: '운동 데이터베이스 테이블 (마스터 데이터)'
}

// ==================== Frontdesk Agent Tables ====================

Table leads {
  id INTEGER [pk, increment]
  name VARCHAR(100) [not null]
  phone VARCHAR(20)
  email VARCHAR(255)
  source VARCHAR(50) [note: 'website, phone, walk_in, referral']
  interest VARCHAR(100) [note: 'weight_loss, muscle_gain, fitness']
  score INTEGER [default: 0, note: 'Lead scoring: 0-100']
  status VARCHAR(20) [default: 'new', note: 'new, contacted, scheduled, converted, lost']
  notes TEXT
  created_at DATETIME [default: `now()`]

  Note: '리드 정보 테이블 (Frontdesk Agent) - 잠재 고객'
}

Table inquiries {
  id INTEGER [pk, increment]
  lead_id INTEGER [ref: > leads.id]
  inquiry_text TEXT [not null]
  response_text TEXT
  inquiry_type VARCHAR(50) [note: 'pricing, schedule, program, facility']
  handled_by VARCHAR(100) [note: 'staff name or "AI Agent"']
  created_at DATETIME [default: `now()`]

  Note: '문의 내역 테이블 (Frontdesk Agent)'
}

Table appointments {
  id INTEGER [pk, increment]
  lead_id INTEGER [ref: > leads.id]
  appointment_date DATETIME [not null]
  appointment_type VARCHAR(50) [note: 'consultation, trial, assessment']
  status VARCHAR(20) [default: 'scheduled', note: 'scheduled, completed, cancelled, no_show']
  notes TEXT
  created_at DATETIME [default: `now()`]

  Note: '상담 예약 테이블 (Frontdesk Agent)'
}

// ==================== Assessor Agent Tables ====================

Table inbody_data {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  measurement_date DATETIME [not null]
  weight FLOAT
  muscle_mass FLOAT
  body_fat_mass FLOAT
  body_fat_percentage FLOAT
  bmr INTEGER [note: 'Basal Metabolic Rate (기초대사량)']
  visceral_fat_level INTEGER [note: '내장지방 레벨']
  body_water FLOAT
  protein FLOAT
  mineral FLOAT
  created_at DATETIME [default: `now()`]

  Note: 'InBody 측정 데이터 테이블 (Assessor Agent)'
}

Table posture_analysis {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  analysis_date DATETIME [not null]
  front_image_url VARCHAR(500)
  side_image_url VARCHAR(500)
  back_image_url VARCHAR(500)
  shoulder_alignment VARCHAR(50) [note: 'balanced, left_high, right_high']
  hip_alignment VARCHAR(50) [note: 'balanced, left_high, right_high']
  spine_curvature VARCHAR(50) [note: 'normal, kyphosis, lordosis, scoliosis']
  issues TEXT [note: 'JSON: [{"area": "shoulder", "issue": "rounded", "severity": "moderate"}]']
  recommendations TEXT [note: 'JSON: [{"exercise": "wall_angels", "sets": 3, "reps": 10}]']
  created_at DATETIME [default: `now()`]

  Note: '자세 분석 테이블 (Assessor Agent)'
}

// ==================== Program Designer Agent Tables ====================

Table programs {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  program_type VARCHAR(20) [note: 'workout, diet, combined']
  goal VARCHAR(100) [note: 'weight_loss, muscle_gain, strength, endurance']
  duration_weeks INTEGER
  workout_plan TEXT [note: 'JSON: workout routine details']
  diet_plan TEXT [note: 'JSON: meal plan details']
  template_id VARCHAR(50) [note: 'Reference to template used']
  customizations TEXT [note: 'JSON: custom modifications']
  status VARCHAR(20) [default: 'active', note: 'active, completed, paused']
  created_at DATETIME [default: `now()`]

  Note: '운동/식단 프로그램 테이블 (Program Designer Agent)'
}

// ==================== Manager Agent Tables ====================

Table attendance {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  check_in_time DATETIME [not null]
  check_out_time DATETIME
  workout_type VARCHAR(50) [note: 'pt_session, group_class, self_workout']
  trainer_id INTEGER [ref: > users.id]
  notes VARCHAR(500)
  created_at DATETIME [default: `now()`]

  Note: '출석 기록 테이블 (Manager Agent)'
}

Table churn_risks {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  risk_score FLOAT [note: '이탈 위험 점수 (0.0 - 1.0)']
  risk_level VARCHAR(20) [note: 'low, medium, high, critical']
  factors TEXT [note: 'JSON: [{"factor": "low_attendance", "weight": 0.3}]']
  last_attendance DATETIME
  days_since_visit INTEGER
  membership_end_date DATETIME
  recommended_actions TEXT [note: 'JSON: suggested retention strategies']
  created_at DATETIME [default: `now()`]

  Note: '이탈 위험도 테이블 (Manager Agent)'
}

// ==================== Marketing Agent Tables ====================

Table social_media_posts {
  id INTEGER [pk, increment]
  platform VARCHAR(50) [note: 'instagram, facebook, blog, youtube']
  content TEXT [not null]
  media_urls TEXT [note: 'JSON: ["url1", "url2"]']
  hashtags VARCHAR(500)
  scheduled_time DATETIME
  posted_time DATETIME
  status VARCHAR(20) [default: 'draft', note: 'draft, scheduled, posted, failed']
  engagement_metrics TEXT [note: 'JSON: {"likes": 120, "comments": 15, "shares": 8}']
  created_at DATETIME [default: `now()`]

  Note: 'SNS 게시물 테이블 (Marketing Agent)'
}

Table events {
  id INTEGER [pk, increment]
  title VARCHAR(200) [not null]
  description TEXT
  event_type VARCHAR(50) [note: 'promotion, challenge, workshop, open_house']
  start_date DATETIME [not null]
  end_date DATETIME [not null]
  target_audience VARCHAR(100) [note: 'new_members, existing, prospects']
  participants TEXT [note: 'JSON: [user_ids]']
  budget FLOAT
  revenue FLOAT
  status VARCHAR(20) [default: 'planned', note: 'planned, active, completed, cancelled']
  created_at DATETIME [default: `now()`]

  Note: '이벤트 테이블 (Marketing Agent)'
}

// ==================== Owner Assistant Agent Tables ====================

Table revenue {
  id INTEGER [pk, increment]
  date DATETIME [not null]
  revenue_type VARCHAR(50) [note: 'membership, pt_session, product, event']
  amount FLOAT [not null]
  user_id INTEGER [ref: > users.id]
  trainer_id INTEGER [ref: > users.id]
  description VARCHAR(500)
  payment_method VARCHAR(50) [note: 'card, cash, transfer']
  created_at DATETIME [default: `now()`]

  Note: '매출 데이터 테이블 (Owner Assistant Agent)'
}

// ==================== Trainer Education Agent Tables ====================

Table trainer_skills {
  id INTEGER [pk, increment]
  trainer_id INTEGER [not null, ref: > users.id]
  skill_category VARCHAR(50) [note: 'technique, communication, program_design, sales']
  skill_name VARCHAR(100) [not null]
  proficiency_level INTEGER [note: '1-5']
  assessment_date DATETIME [not null]
  assessor VARCHAR(100) [note: 'Who assessed the skill']
  notes TEXT
  improvement_plan TEXT [note: 'JSON: training recommendations']
  created_at DATETIME [default: `now()`]

  Note: '트레이너 스킬 테이블 (Trainer Education Agent)'
}

// ==================== Nutrition Agent Tables ====================

Table nutrition_goals {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  goal_type VARCHAR(50) [note: 'weight_loss, muscle_gain, maintenance, health']
  target_calories INTEGER
  target_protein FLOAT [note: 'grams']
  target_carbs FLOAT [note: 'grams']
  target_fat FLOAT [note: 'grams']
  target_water INTEGER [note: 'ml']
  start_date DATETIME [not null]
  end_date DATETIME
  status VARCHAR(20) [default: 'active', note: 'active, completed, paused']
  notes TEXT
  created_at DATETIME [default: `now()`]

  Note: '영양 목표 테이블 (Nutrition Agent)'
}

Table food_database {
  id INTEGER [pk, increment]
  name VARCHAR(200) [not null]
  name_en VARCHAR(200)
  category VARCHAR(50) [note: 'protein, carbs, vegetables, fruits, dairy, snacks, beverages']
  serving_size FLOAT [note: '1회 제공량']
  serving_unit VARCHAR(20) [note: 'g, ml, 개, 공기']
  calories_per_serving FLOAT
  protein FLOAT [note: 'grams']
  carbs FLOAT [note: 'grams']
  fat FLOAT [note: 'grams']
  fiber FLOAT [note: 'grams']
  sodium FLOAT [note: 'mg']
  sugar FLOAT [note: 'grams']
  is_verified BOOLEAN [default: false]
  source VARCHAR(50) [note: 'user_input, korean_fdc, usda']
  created_at DATETIME [default: `now()`]

  Note: '음식 영양 정보 DB (Nutrition Agent) - 마스터 데이터'
}

Table daily_nutrition_summary {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  date DATE [not null]
  total_calories FLOAT
  total_protein FLOAT
  total_carbs FLOAT
  total_fat FLOAT
  water_intake INTEGER [note: 'ml']
  meal_count INTEGER
  goal_achievement_rate FLOAT [note: '0.0 ~ 1.0']
  quality_score FLOAT [note: '0.0 ~ 1.0']
  ai_feedback TEXT
  created_at DATETIME [default: `now()`]

  Note: '일별 영양 요약 테이블 (Nutrition Agent)'
}

Table nutrition_feedback {
  id INTEGER [pk, increment]
  user_id INTEGER [not null, ref: > users.id]
  meal_log_id INTEGER [ref: > meal_logs.id]
  feedback_date DATETIME [not null]
  feedback_type VARCHAR(50) [note: 'daily_summary, meal_specific, weekly_review']
  feedback_text TEXT [not null]
  recommendations TEXT [note: 'JSON array']
  created_by VARCHAR(100) [note: 'AI_Agent, Trainer_Name']
  sentiment VARCHAR(20) [note: 'positive, neutral, constructive']
  created_at DATETIME [default: `now()`]

  Note: '영양 피드백 테이블 (Nutrition Agent)'
}
```

---

## 테이블 그룹별 설명

### 1. Core Tables (핵심 테이블)
- **users**: 모든 관계의 중심이 되는 사용자/회원 마스터 테이블

### 2. Workout & Health Tables (운동 & 건강 테이블)
- **meal_logs**: 식단 기록
- **workout_routines**: 운동 루틴
- **schedules**: PT 스케줄
- **member_progress**: 회원 진행률
- **bookmarks**: 자료 북마크
- **exercise_db**: 운동 데이터베이스 (마스터)

### 3. Agent별 전용 테이블

#### Frontdesk Agent (3개 테이블)
- **leads**: 잠재 고객 정보
- **inquiries**: 문의 내역
- **appointments**: 상담 예약

#### Assessor Agent (2개 테이블)
- **inbody_data**: InBody 측정 데이터
- **posture_analysis**: 자세 분석

#### Program Designer Agent (1개 테이블)
- **programs**: 운동/식단 프로그램

#### Manager Agent (2개 테이블)
- **attendance**: 출석 기록
- **churn_risks**: 이탈 위험도

#### Marketing Agent (2개 테이블)
- **social_media_posts**: SNS 게시물
- **events**: 이벤트

#### Owner Assistant Agent (1개 테이블)
- **revenue**: 매출 데이터

#### Trainer Education Agent (1개 테이블)
- **trainer_skills**: 트레이너 스킬

#### Nutrition Agent (4개 테이블)
- **nutrition_goals**: 영양 목표
- **food_database**: 음식 영양 정보 DB
- **daily_nutrition_summary**: 일별 영양 요약
- **nutrition_feedback**: 영양 피드백

---

## 주요 관계 (Foreign Keys)

### users 테이블 중심 관계
```
users (1) ──── (N) meal_logs
users (1) ──── (N) workout_routines
users (1) ──── (N) schedules (as member)
users (1) ──── (N) schedules (as trainer)
users (1) ──── (N) member_progress
users (1) ──── (N) bookmarks
users (1) ──── (N) inbody_data
users (1) ──── (N) posture_analysis
users (1) ──── (N) programs
users (1) ──── (N) attendance (as member)
users (1) ──── (N) attendance (as trainer)
users (1) ──── (N) churn_risks
users (1) ──── (N) revenue (as customer)
users (1) ──── (N) revenue (as trainer)
users (1) ──── (N) trainer_skills
users (1) ──── (N) nutrition_goals
users (1) ──── (N) daily_nutrition_summary
users (1) ──── (N) nutrition_feedback
```

### leads 테이블 중심 관계
```
leads (1) ──── (N) inquiries
leads (1) ──── (N) appointments
```

### meal_logs 테이블 관계
```
meal_logs (1) ──── (N) nutrition_feedback
```

---

## 연결 정보

**PostgreSQL URL**:
```
postgresql://postgres:root1234@localhost:5432/octo_chatbot
```

**Async PostgreSQL URL**:
```
postgresql+asyncpg://postgres:root1234@localhost:5432/octo_chatbot
```

**SQLAlchemy Session**:
```python
# backend/database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(ASYNC_POSTGRES_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 데이터 타입 매핑

| SQLAlchemy Type | PostgreSQL Type | 설명 |
|----------------|-----------------|------|
| `Integer` | `INTEGER` | 정수 |
| `String(N)` | `VARCHAR(N)` | 가변 길이 문자열 |
| `Text` | `TEXT` | 무제한 텍스트 |
| `Float` | `REAL` | 부동소수점 |
| `DateTime` | `TIMESTAMP` | 날짜/시간 |
| `Date` | `DATE` | 날짜만 |
| `Boolean` | `BOOLEAN` | 참/거짓 |

---

## JSON 필드 사용 패턴

많은 테이블에서 JSON 문자열을 `TEXT` 타입으로 저장합니다:

### 예시: meal_logs.foods
```json
[
  {"name": "계란", "quantity": 2, "unit": "개"},
  {"name": "현미밥", "quantity": 1, "unit": "공기"},
  {"name": "닭가슴살", "quantity": 150, "unit": "g"}
]
```

### 예시: programs.workout_plan
```json
{
  "weeks": [
    {
      "week": 1,
      "days": [
        {
          "day": "Monday",
          "exercises": [
            {"name": "스쿼트", "sets": 4, "reps": 10, "weight": 60}
          ]
        }
      ]
    }
  ]
}
```

**⚠️ 향후 개선 제안**: PostgreSQL의 `JSONB` 타입으로 마이그레이션하면 쿼리 성능 향상 가능

---

## 인덱스 제안

현재 명시적 인덱스 없음. 성능 최적화를 위한 권장 인덱스:

```sql
-- users 테이블
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- meal_logs 테이블
CREATE INDEX idx_meal_logs_user_date ON meal_logs(user_id, date);

-- attendance 테이블
CREATE INDEX idx_attendance_user_date ON attendance(user_id, check_in_time);

-- leads 테이블
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_email ON leads(email);

-- schedules 테이블
CREATE INDEX idx_schedules_date ON schedules(date);
CREATE INDEX idx_schedules_user_trainer ON schedules(user_id, trainer_id);
```

---

## Agent별 테이블 요약

| Agent | 테이블 수 | 주요 테이블 |
|-------|---------|-----------|
| Frontdesk | 3 | leads, inquiries, appointments |
| Assessor | 2 | inbody_data, posture_analysis |
| Program Designer | 1 | programs |
| Manager | 2 | attendance, churn_risks |
| Marketing | 2 | social_media_posts, events |
| Owner Assistant | 1 | revenue |
| Trainer Education | 1 | trainer_skills |
| Nutrition | 4 | nutrition_goals, food_database, daily_nutrition_summary, nutrition_feedback |

**총 테이블 수**: 23개 (Core 7개 + Agent 16개)

---

## 참고 자료

- [SQLAlchemy 공식 문서](https://docs.sqlalchemy.org/)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [dbdiagram.io 공식 사이트](https://dbdiagram.io)

---

## 결론

✅ **User 중심의 관계형 설계**
- users 테이블을 중심으로 모든 데이터 연결
- ForeignKey로 데이터 무결성 보장

✅ **Agent별 전용 테이블 분리**
- 각 Agent의 책임에 맞는 테이블 설계
- 명확한 도메인 분리

✅ **JSON 필드로 유연성 확보**
- 복잡한 데이터 구조를 TEXT/JSON으로 저장
- 향후 JSONB로 마이그레이션 권장

✅ **dbdiagram.io 형식으로 문서화 완료**
- 시각적 ER Diagram 생성 가능
- 관계 파악 용이
