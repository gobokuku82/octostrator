"""Mock Data Generator for SQLite DB"""
from backend.database.relation_db.models import (
    User, MealLog, WorkoutRoutine, Schedule, MemberProgress, Bookmark, ExerciseDB,
    Lead, Inquiry, Appointment, InBodyData, PostureAnalysis, Program,
    Attendance, ChurnRisk, SocialMediaPost, Event, Revenue, TrainerSkill
)
from backend.database.relation_db.session import get_db, init_db
from datetime import datetime, timedelta
import json


def create_mock_users():
    """Mock 사용자 생성"""
    users = [
        User(id=1, name="김철수", email="kim@example.com", phone="010-1111-2222",
             goal="muscle_gain", level="intermediate"),
        User(id=2, name="이영희", email="lee@example.com", phone="010-3333-4444",
             goal="weight_loss", level="beginner"),
        User(id=3, name="박민수", email="park@example.com", phone="010-5555-6666",
             goal="fitness", level="advanced"),
        User(id=100, name="트레이너_홍길동", email="trainer@example.com", phone="010-7777-8888",
             goal="fitness", level="advanced"),  # 트레이너
    ]

    with get_db() as db:
        for user in users:
            existing = db.query(User).filter(User.id == user.id).first()
            if not existing:
                db.add(user)
        db.commit()

    print(f"✓ Mock Users 생성: {len(users)}개")


def create_mock_meal_logs():
    """Mock 식단 기록 생성"""
    meal_logs = [
        MealLog(
            user_id=1,
            date=datetime.now() - timedelta(days=0),
            meal_type="breakfast",
            foods=json.dumps([
                {"name": "계란", "quantity": 3, "unit": "개"},
                {"name": "현미밥", "quantity": 1, "unit": "공기"},
                {"name": "김치", "quantity": 50, "unit": "g"}
            ]),
            nutrition=json.dumps({
                "calories": 450, "protein": 30, "carbs": 45, "fat": 15
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
                "calories": 350, "protein": 45, "carbs": 20, "fat": 8
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


def create_mock_member_progress():
    """Mock 회원 진행률 생성"""
    progress_data = [
        MemberProgress(
            user_id=1,
            date=datetime.now() - timedelta(days=7),
            weight=75.5,
            body_fat_percentage=18.5,
            muscle_mass=60.2,
            notes="1주차: 근육량 증가 중"
        ),
        MemberProgress(
            user_id=1,
            date=datetime.now(),
            weight=76.0,
            body_fat_percentage=17.8,
            muscle_mass=61.0,
            notes="2주차: 체지방 감소, 근육량 증가"
        ),
        MemberProgress(
            user_id=2,
            date=datetime.now() - timedelta(days=7),
            weight=65.0,
            body_fat_percentage=28.0,
            muscle_mass=45.5,
            notes="1주차: 다이어트 시작"
        ),
    ]

    with get_db() as db:
        for progress in progress_data:
            db.add(progress)
        db.commit()

    print(f"✓ Mock Member Progress 생성: {len(progress_data)}개")


# ==================== New Agent Tables Mock Data ====================

def create_mock_leads():
    """Mock 리드 생성"""
    leads = [
        Lead(id=1, name="강지민", phone="010-1111-1111", email="jimin@example.com",
             source="website", interest="weight_loss", score=85, status="contacted",
             notes="온라인 문의, 3개월 PT 관심"),
        Lead(id=2, name="이서준", phone="010-2222-2222", email="seojun@example.com",
             source="walk_in", interest="muscle_gain", score=75, status="scheduled",
             notes="방문 상담, 헬스장 경험 1년"),
        Lead(id=3, name="박하늘", phone="010-3333-3333", email="haneul@example.com",
             source="referral", interest="fitness", score=90, status="new",
             notes="기존 회원 추천, 빠른 시일 내 시작 희망"),
        Lead(id=4, name="최민준", phone="010-4444-4444",
             source="phone", interest="weight_loss", score=60, status="lost",
             notes="가격 문의 후 연락 두절"),
    ]

    with get_db() as db:
        for lead in leads:
            existing = db.query(Lead).filter(Lead.id == lead.id).first()
            if not existing:
                db.add(lead)
        db.commit()

    print(f"✓ Mock Leads 생성: {len(leads)}개")


def create_mock_inquiries():
    """Mock 문의 생성"""
    inquiries = [
        Inquiry(lead_id=1, inquiry_text="3개월 PT 가격이 어떻게 되나요?",
                response_text="3개월 PT는 주 3회 기준 180만원입니다.", inquiry_type="pricing",
                handled_by="AI Agent"),
        Inquiry(lead_id=2, inquiry_text="평일 저녁 7시 이후 PT 가능한가요?",
                response_text="네, 평일 저녁 7시~9시 PT 가능합니다.", inquiry_type="schedule",
                handled_by="AI Agent"),
        Inquiry(lead_id=3, inquiry_text="다이어트 프로그램 어떤 게 있나요?",
                response_text="체계적인 다이어트 프로그램 제공합니다. 식단 관리 포함됩니다.",
                inquiry_type="program", handled_by="AI Agent"),
    ]

    with get_db() as db:
        for inquiry in inquiries:
            db.add(inquiry)
        db.commit()

    print(f"✓ Mock Inquiries 생성: {len(inquiries)}개")


def create_mock_appointments():
    """Mock 상담 예약 생성"""
    appointments = [
        Appointment(lead_id=2, appointment_date=datetime.now() + timedelta(days=2, hours=14),
                    appointment_type="consultation", status="scheduled",
                    notes="PT 프로그램 설명 및 체험 PT"),
        Appointment(lead_id=3, appointment_date=datetime.now() + timedelta(days=3, hours=16),
                    appointment_type="trial", status="scheduled",
                    notes="1회 체험 PT 진행"),
    ]

    with get_db() as db:
        for appointment in appointments:
            db.add(appointment)
        db.commit()

    print(f"✓ Mock Appointments 생성: {len(appointments)}개")


def create_mock_inbody_data():
    """Mock InBody 측정 데이터 생성"""
    inbody_list = [
        InBodyData(user_id=1, measurement_date=datetime.now() - timedelta(days=7),
                   weight=75.5, muscle_mass=32.5, body_fat_mass=15.2, body_fat_percentage=20.1,
                   bmr=1650, visceral_fat_level=8, body_water=45.2, protein=12.5, mineral=3.8),
        InBodyData(user_id=1, measurement_date=datetime.now(),
                   weight=74.8, muscle_mass=33.0, body_fat_mass=14.5, body_fat_percentage=19.4,
                   bmr=1680, visceral_fat_level=7, body_water=45.8, protein=12.8, mineral=3.9),
        InBodyData(user_id=2, measurement_date=datetime.now() - timedelta(days=14),
                   weight=68.0, muscle_mass=28.5, body_fat_mass=18.5, body_fat_percentage=27.2,
                   bmr=1420, visceral_fat_level=10, body_water=38.5, protein=10.5, mineral=3.2),
    ]

    with get_db() as db:
        for inbody in inbody_list:
            db.add(inbody)
        db.commit()

    print(f"✓ Mock InBody Data 생성: {len(inbody_list)}개")


def create_mock_posture_analysis():
    """Mock 자세 분석 생성"""
    posture_list = [
        PostureAnalysis(
            user_id=1, analysis_date=datetime.now() - timedelta(days=7),
            front_image_url="/images/posture/user1_front.jpg",
            side_image_url="/images/posture/user1_side.jpg",
            shoulder_alignment="right_high", hip_alignment="balanced",
            spine_curvature="normal",
            issues=json.dumps([
                {"area": "shoulder", "issue": "right_elevated", "severity": "moderate"},
                {"area": "neck", "issue": "forward_head", "severity": "mild"}
            ]),
            recommendations=json.dumps([
                {"exercise": "shoulder_shrugs", "sets": 3, "reps": 15},
                {"exercise": "chin_tucks", "sets": 3, "reps": 12}
            ])
        ),
    ]

    with get_db() as db:
        for posture in posture_list:
            db.add(posture)
        db.commit()

    print(f"✓ Mock Posture Analysis 생성: {len(posture_list)}개")


def create_mock_programs():
    """Mock 프로그램 생성"""
    programs = [
        Program(
            user_id=1, program_type="combined", goal="muscle_gain", duration_weeks=12,
            workout_plan=json.dumps({
                "frequency": "3x per week",
                "exercises": [
                    {"day": "Monday", "focus": "Chest/Triceps", "exercises": ["Bench Press", "Dips", "Cable Flyes"]},
                    {"day": "Wednesday", "focus": "Back/Biceps", "exercises": ["Pull-ups", "Rows", "Curls"]},
                    {"day": "Friday", "focus": "Legs/Shoulders", "exercises": ["Squats", "Lunges", "Shoulder Press"]}
                ]
            }),
            diet_plan=json.dumps({
                "calories": 2500,
                "protein": 180,
                "carbs": 300,
                "fat": 70,
                "meals": 5
            }),
            template_id="strength_gain_intermediate",
            customizations=json.dumps({"extra_protein": True, "no_dairy": False}),
            status="active"
        ),
    ]

    with get_db() as db:
        for program in programs:
            db.add(program)
        db.commit()

    print(f"✓ Mock Programs 생성: {len(programs)}개")


def create_mock_attendance():
    """Mock 출석 기록 생성"""
    attendance_list = [
        Attendance(user_id=1, check_in_time=datetime.now() - timedelta(days=1, hours=18),
                   check_out_time=datetime.now() - timedelta(days=1, hours=17),
                   workout_type="pt_session", trainer_id=100, notes="하체 집중 운동"),
        Attendance(user_id=1, check_in_time=datetime.now() - timedelta(days=3, hours=19),
                   check_out_time=datetime.now() - timedelta(days=3, hours=18),
                   workout_type="pt_session", trainer_id=100, notes="상체 운동"),
        Attendance(user_id=2, check_in_time=datetime.now() - timedelta(hours=2),
                   workout_type="self_workout", notes="유산소 30분"),
    ]

    with get_db() as db:
        for attendance in attendance_list:
            db.add(attendance)
        db.commit()

    print(f"✓ Mock Attendance 생성: {len(attendance_list)}개")


def create_mock_churn_risks():
    """Mock 이탈 위험도 생성"""
    churn_list = [
        ChurnRisk(
            user_id=2, risk_score=0.65, risk_level="high",
            factors=json.dumps([
                {"factor": "low_attendance", "weight": 0.4},
                {"factor": "expiring_membership", "weight": 0.25}
            ]),
            last_attendance=datetime.now() - timedelta(days=10),
            days_since_visit=10,
            membership_end_date=datetime.now() + timedelta(days=15),
            recommended_actions=json.dumps([
                "재등록 할인 제안", "개인 상담 스케줄", "동기부여 메시지 전송"
            ])
        ),
    ]

    with get_db() as db:
        for churn in churn_list:
            db.add(churn)
        db.commit()

    print(f"✓ Mock Churn Risks 생성: {len(churn_list)}개")


def create_mock_social_posts():
    """Mock SNS 게시물 생성"""
    posts = [
        SocialMediaPost(
            platform="instagram", content="💪 PT 성공 사례! 3개월 만에 체지방 5% 감소!\n#다이어트 #퍼스널트레이닝 #헬스",
            media_urls=json.dumps(["/images/posts/success1.jpg"]),
            hashtags="#다이어트 #PT #헬스 #운동",
            scheduled_time=datetime.now() + timedelta(hours=2),
            status="scheduled"
        ),
        SocialMediaPost(
            platform="facebook", content="신규 회원 환영 이벤트! 첫 달 20% 할인 🎉",
            posted_time=datetime.now() - timedelta(days=2),
            status="posted",
            engagement_metrics=json.dumps({"likes": 145, "comments": 23, "shares": 12})
        ),
    ]

    with get_db() as db:
        for post in posts:
            db.add(post)
        db.commit()

    print(f"✓ Mock Social Posts 생성: {len(posts)}개")


def create_mock_events():
    """Mock 이벤트 생성"""
    events = [
        Event(
            title="신규 회원 환영 이벤트", description="첫 달 PT 20% 할인",
            event_type="promotion",
            start_date=datetime.now() - timedelta(days=3),
            end_date=datetime.now() + timedelta(days=27),
            target_audience="new_members", budget=500000, revenue=1200000,
            status="active", participants=json.dumps([])
        ),
    ]

    with get_db() as db:
        for event in events:
            db.add(event)
        db.commit()

    print(f"✓ Mock Events 생성: {len(events)}개")


def create_mock_revenue():
    """Mock 매출 생성"""
    revenue_list = [
        Revenue(date=datetime.now() - timedelta(days=1), revenue_type="pt_session",
                amount=80000, user_id=1, trainer_id=100, description="PT 1회",
                payment_method="card"),
        Revenue(date=datetime.now() - timedelta(days=2), revenue_type="membership",
                amount=150000, user_id=2, description="1개월 회원권",
                payment_method="transfer"),
        Revenue(date=datetime.now() - timedelta(days=5), revenue_type="pt_session",
                amount=80000, user_id=3, trainer_id=100, description="PT 1회",
                payment_method="card"),
    ]

    with get_db() as db:
        for revenue in revenue_list:
            db.add(revenue)
        db.commit()

    print(f"✓ Mock Revenue 생성: {len(revenue_list)}개")


def create_mock_trainer_skills():
    """Mock 트레이너 스킬 생성"""
    skills = [
        TrainerSkill(trainer_id=100, skill_category="technique", skill_name="스쿼트 지도",
                     proficiency_level=5, assessment_date=datetime.now() - timedelta(days=30),
                     assessor="수석 트레이너", notes="완벽한 폼 교정 능력"),
        TrainerSkill(trainer_id=100, skill_category="communication", skill_name="회원 동기부여",
                     proficiency_level=4, assessment_date=datetime.now() - timedelta(days=30),
                     assessor="센터장", notes="긍정적인 커뮤니케이션"),
        TrainerSkill(trainer_id=100, skill_category="program_design", skill_name="다이어트 프로그램 설계",
                     proficiency_level=4, assessment_date=datetime.now() - timedelta(days=30),
                     assessor="수석 트레이너",
                     improvement_plan=json.dumps([
                         {"module_id": "nutrition_coaching", "priority": "high"}
                     ])),
    ]

    with get_db() as db:
        for skill in skills:
            db.add(skill)
        db.commit()

    print(f"✓ Mock Trainer Skills 생성: {len(skills)}개")


def create_all_mock_data():
    """모든 Mock 데이터 생성"""
    print("\n=== Mock 데이터 생성 시작 ===\n")

    # DB 초기화
    init_db()

    # 기존 Mock 데이터 생성
    create_mock_users()
    create_mock_exercises()
    create_mock_meal_logs()
    create_mock_workout_routines()
    create_mock_schedules()
    create_mock_member_progress()

    # 새로운 7개 에이전트 Mock 데이터 생성
    create_mock_leads()
    create_mock_inquiries()
    create_mock_appointments()
    create_mock_inbody_data()
    create_mock_posture_analysis()
    create_mock_programs()
    create_mock_attendance()
    create_mock_churn_risks()
    create_mock_social_posts()
    create_mock_events()
    create_mock_revenue()
    create_mock_trainer_skills()

    print("\n=== Mock 데이터 생성 완료 ===\n")


if __name__ == "__main__":
    create_all_mock_data()
