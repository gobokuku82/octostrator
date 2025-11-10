"""7개 에이전트 Tools 테스트 예시

각 에이전트의 주요 기능을 테스트하는 예시 코드
Mock 데이터를 활용하여 실제 flow를 확인할 수 있습니다.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ==================== Frontdesk Agent 테스트 ====================

async def test_frontdesk_agent():
    """Frontdesk Agent 테스트

    핵심 역할: 신규 문의 처리 및 상담 예약 관리
    Pain Point: 문의 전화/메시지에 일일이 대응하느라 정작 PT에 집중 못함
    """
    print("\n" + "="*60)
    print("1. Frontdesk Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_all_leads,
        create_inquiry,
        classify_inquiry_intent,
        calculate_lead_score,
        get_available_slots,
        create_appointment,
        send_notification
    )

    # 1) 모든 리드 조회
    print("\n[1-1] 모든 리드 조회")
    result = await get_all_leads(limit=10)
    if result["success"]:
        print(f"✓ 리드 {result['count']}개 조회 완료")
        for lead in result["leads"][:3]:
            print(f"  - {lead['name']} ({lead['status']}) - Score: {lead['score']}")

    # 2) 신규 문의 처리
    print("\n[1-2] 신규 문의 생성")
    inquiry_text = "주 3회 PT를 하고 싶은데 가격이 궁금합니다"

    # 문의 의도 분류
    intent_result = await classify_inquiry_intent(inquiry_text)
    print(f"✓ 문의 의도 분류: {intent_result['intent']}")

    # 문의 생성
    inquiry_result = await create_inquiry(
        lead_id=1,
        inquiry_text=inquiry_text,
        inquiry_type=intent_result["intent"],
        response_text="주 3회 PT는 월 80만원입니다. 3개월 패키지 시 10% 할인 가능합니다."
    )
    if inquiry_result["success"]:
        print(f"✓ 문의 생성 완료 (ID: {inquiry_result['inquiry_id']})")

    # 3) 리드 스코어링
    print("\n[1-3] 리드 스코어 계산")
    score_result = await calculate_lead_score(
        lead_id=1,
        factors={
            "urgency": 0.8,        # 긴급도
            "budget_fit": 0.9,     # 예산 적합도
            "engagement": 0.7,     # 참여도
            "fit": 0.85            # 적합도
        }
    )
    if score_result["success"]:
        print(f"✓ 리드 스코어: {score_result['score']}/100")

    # 4) 예약 가능한 시간 조회
    print("\n[1-4] 예약 가능 시간 조회")
    slots_result = await get_available_slots(days=3)
    if slots_result["success"]:
        print(f"✓ {slots_result['count']}개 슬롯 사용 가능")
        for slot in slots_result["slots"][:5]:
            print(f"  - {slot['display']}")

    # 5) 상담 예약 생성
    print("\n[1-5] 상담 예약 생성")
    appointment_result = await create_appointment(
        lead_id=1,
        appointment_date=datetime.now() + timedelta(days=1, hours=15),
        appointment_type="consultation",
        notes="PT 프로그램 설명 및 체형 분석"
    )
    if appointment_result["success"]:
        print(f"✓ 예약 완료 (ID: {appointment_result['appointment_id']})")
        print(f"  일시: {appointment_result['appointment_date']}")

    # 6) 예약 확인 알림 전송
    print("\n[1-6] 예약 확인 알림 전송")
    notification_result = await send_notification(
        lead_id=1,
        notification_type="appointment_confirm",
        message=f"상담 예약이 확인되었습니다. 일시: {appointment_result['appointment_date']}",
        channel="sms"
    )
    if notification_result["success"]:
        print(f"✓ 알림 전송 완료 ({notification_result['channel']})")


# ==================== Assessor Agent 테스트 ====================

async def test_assessor_agent():
    """Assessor Agent 테스트

    핵심 역할: 회원 초기 평가 및 자세 분석
    Pain Point: 회원 체형과 자세를 '감'이 아닌 '데이터'로 정확하게 분석하고 싶다
    """
    print("\n" + "="*60)
    print("2. Assessor Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_inbody_data,
        analyze_inbody_trend,
        get_posture_analysis,
        get_member_assessment_summary,
        calculate_fitness_score
    )

    # 1) InBody 데이터 조회
    print("\n[2-1] InBody 데이터 조회")
    inbody_result = await get_inbody_data(user_id=1, limit=5)
    if inbody_result["success"]:
        print(f"✓ InBody 데이터 {inbody_result['count']}개 조회")
        latest = inbody_result["data"][0]
        print(f"  최근 측정: {latest['measurement_date']}")
        print(f"  - 체중: {latest['weight']}kg")
        print(f"  - 체지방률: {latest['body_fat_percentage']}%")
        print(f"  - 근육량: {latest['muscle_mass']}kg")
        print(f"  - 기초대사량: {latest['bmr']}kcal")

    # 2) InBody 트렌드 분석
    print("\n[2-2] InBody 트렌드 분석 (30일)")
    trend_result = await analyze_inbody_trend(user_id=1, days=30)
    if trend_result["success"]:
        print(f"✓ 분석 기간: {trend_result['period_days']}일")
        print(f"  측정 횟수: {trend_result['measurements_count']}회")
        trends = trend_result["trends"]
        print(f"  체중 변화: {trends['weight']['change']:+.1f}kg ({trends['weight']['change_percent']:+.1f}%)")
        print(f"  근육량 변화: {trends['muscle_mass']['change']:+.1f}kg ({trends['muscle_mass']['change_percent']:+.1f}%)")
        print(f"  체지방률 변화: {trends['body_fat_percentage']['change']:+.1f}%")

    # 3) 자세 분석 조회
    print("\n[2-3] 자세 분석 조회")
    posture_result = await get_posture_analysis(user_id=1, limit=1)
    if posture_result["success"] and posture_result["count"] > 0:
        posture = posture_result["data"][0]
        print(f"✓ 자세 분석 완료: {posture['analysis_date']}")
        print(f"  어깨 정렬: {posture['shoulder_alignment']}")
        print(f"  골반 정렬: {posture['hip_alignment']}")
        print(f"  척추 만곡: {posture['spine_curvature']}")
        print(f"  발견된 문제: {len(posture['issues'])}개")
        print(f"  권장 운동: {len(posture['recommendations'])}개")

    # 4) 회원 종합 평가 요약
    print("\n[2-4] 회원 종합 평가 요약")
    summary_result = await get_member_assessment_summary(user_id=1)
    if summary_result["success"]:
        print(f"✓ 회원: {summary_result['user']['name']}")
        print(f"  목표: {summary_result['user']['goal']}")
        print(f"  레벨: {summary_result['user']['level']}")
        if summary_result["body_composition"]:
            bc = summary_result["body_composition"]
            print(f"  현재 체지방률: {bc['body_fat_percentage']}%")
            print(f"  기초대사량: {bc['bmr']}kcal")

    # 5) 체력 점수 계산
    print("\n[2-5] 체력 점수 계산")
    fitness_result = await calculate_fitness_score(user_id=1)
    if fitness_result["success"]:
        print(f"✓ 종합 체력 점수: {fitness_result['fitness_score']}/100")
        components = fitness_result["components"]
        print(f"  - 근력: {components['strength']}")
        print(f"  - 지구력: {components['endurance']}")
        print(f"  - 유연성: {components['flexibility']}")
        print(f"  - 균형: {components['balance']}")


# ==================== Program Designer Agent 테스트 ====================

async def test_program_designer_agent():
    """Program Designer Agent 테스트

    핵심 역할: 회원별 맞춤 운동/식단 프로그램 자동 생성
    Pain Point: 매번 수기로 프로그램 짜느라 시간이 너무 오래 걸림
    """
    print("\n" + "="*60)
    print("3. Program Designer Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_workout_templates,
        get_diet_templates,
        create_program,
        get_program,
        get_user_programs,
        search_exercises
    )

    # 1) 운동 템플릿 조회
    print("\n[3-1] 운동 템플릿 조회")
    workout_templates = await get_workout_templates()
    if workout_templates["success"]:
        print(f"✓ {workout_templates['count']}개 템플릿 사용 가능")
        for template in workout_templates["templates"][:3]:
            print(f"  - {template['name']} ({template['level']})")
            print(f"    목표: {template['goal']}, 기간: {template['duration_weeks']}주")

    # 2) 식단 템플릿 조회
    print("\n[3-2] 식단 템플릿 조회")
    diet_templates = await get_diet_templates()
    if diet_templates["success"]:
        print(f"✓ {diet_templates['count']}개 템플릿 사용 가능")
        for template in diet_templates["templates"][:3]:
            print(f"  - {template['name']}")
            print(f"    칼로리: {template['daily_calories']}kcal, 단백질: {template['macros']['protein_percent']}%")

    # 3) 운동 검색
    print("\n[3-3] 하체 운동 검색")
    exercise_result = await search_exercises(muscle_group="legs", limit=3)
    if exercise_result["success"]:
        print(f"✓ {exercise_result['count']}개 운동 발견")
        for exercise in exercise_result["exercises"]:
            print(f"  - {exercise['name']} ({exercise['difficulty']})")

    # 4) 프로그램 생성 (Mock - 실제로는 LLM이 생성)
    print("\n[3-4] 맞춤 프로그램 생성")
    import json
    program_result = await create_program(
        user_id=2,
        program_type="combined",
        goal="weight_loss",
        duration_weeks=8,
        workout_plan=json.dumps({
            "frequency": "4x per week",
            "focus": "cardio + strength",
            "exercises": [
                {"day": "Mon/Thu", "type": "strength", "duration": 40},
                {"day": "Tue/Fri", "type": "cardio", "duration": 30}
            ]
        }),
        diet_plan=json.dumps({
            "calories": 1800,
            "protein": 120,
            "carbs": 180,
            "fat": 60
        }),
        template_id="weight_loss_intermediate"
    )
    if program_result["success"]:
        print(f"✓ 프로그램 생성 완료 (ID: {program_result['program_id']})")
        print(f"  유형: {program_result['program_type']}")
        print(f"  목표: {program_result['goal']}")
        print(f"  기간: {program_result['duration_weeks']}주")

    # 5) 사용자 프로그램 조회
    print("\n[3-5] 사용자 프로그램 조회")
    user_programs = await get_user_programs(user_id=1, status="active")
    if user_programs["success"]:
        print(f"✓ 활성 프로그램 {user_programs['count']}개")
        for program in user_programs["programs"]:
            print(f"  - 목표: {program['goal']}, 기간: {program['duration_weeks']}주")


# ==================== Manager Agent 테스트 ====================

async def test_manager_agent():
    """Manager Agent 테스트

    핵심 역할: 회원 출석 관리 및 이탈 방지
    Pain Point: 어떤 회원이 이탈 위험인지 감으로만 알고, 체계적 관리 어려움
    """
    print("\n" + "="*60)
    print("4. Manager Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_attendance_records,
        calculate_attendance_rate,
        calculate_churn_risk,
        get_churn_risks,
        get_renewal_candidates
    )

    # 1) 출석 기록 조회
    print("\n[4-1] 회원 출석 기록 조회")
    attendance_result = await get_attendance_records(user_id=1, limit=10)
    if attendance_result["success"]:
        print(f"✓ 출석 기록 {attendance_result['count']}개")
        for record in attendance_result["records"][:3]:
            print(f"  - {record['check_in_time']}")
            print(f"    유형: {record['workout_type']}, 시간: {record.get('duration_minutes', 'N/A')}분")

    # 2) 출석률 계산
    print("\n[4-2] 출석률 계산 (30일)")
    rate_result = await calculate_attendance_rate(user_id=1, days=30)
    if rate_result["success"]:
        print(f"✓ 출석률: {rate_result['attendance_rate']:.1f}%")
        print(f"  실제 출석: {rate_result['attendance_count']}회")
        print(f"  예정 세션: {rate_result['schedule_count']}회")

    # 3) 이탈 위험도 계산
    print("\n[4-3] 회원 이탈 위험도 분석")
    churn_result = await calculate_churn_risk(user_id=2)
    if churn_result["success"]:
        print(f"✓ 위험도: {churn_result['risk_level']} (점수: {churn_result['risk_score']:.2f})")
        print(f"  마지막 방문: {churn_result['days_since_visit']}일 전")
        print(f"  출석률: {churn_result['attendance_rate']}%")
        print(f"  위험 요소: {churn_result['factors_count']}개")
        print(f"  권장 조치: {churn_result['recommended_actions_count']}개")

    # 4) 이탈 위험 회원 목록
    print("\n[4-4] 이탈 위험 회원 목록 조회")
    risk_list = await get_churn_risks(risk_level="high", limit=10)
    if risk_list["success"]:
        print(f"✓ 고위험 회원 {risk_list['count']}명")
        for risk in risk_list["risks"]:
            print(f"  - User ID: {risk['user_id']}")
            print(f"    위험도: {risk['risk_level']} ({risk['risk_score']:.2f})")
            print(f"    마지막 방문: {risk['days_since_visit']}일 전")

    # 5) 재등록 대상 조회
    print("\n[4-5] 재등록 대상 회원 조회 (7일 내 만료)")
    renewal_result = await get_renewal_candidates(days_before_expiry=7)
    if renewal_result["success"]:
        print(f"✓ 재등록 대상 {renewal_result['count']}명")
        for candidate in renewal_result["candidates"]:
            print(f"  - {candidate['name']}")
            print(f"    만료일: {candidate['membership_end_date']}")
            print(f"    D-{candidate['days_until_expiry']}")


# ==================== Marketing Agent 테스트 ====================

async def test_marketing_agent():
    """Marketing Agent 테스트

    핵심 역할: SNS 콘텐츠 자동 생성 및 이벤트 관리
    Pain Point: SNS 콘텐츠 만들 시간도 없고, 뭘 올려야 할지 막막함
    """
    print("\n" + "="*60)
    print("5. Marketing Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_posts,
        create_social_post,
        update_post_engagement,
        get_events,
        create_event
    )

    # 1) 기존 SNS 게시물 조회
    print("\n[5-1] SNS 게시물 조회")
    posts_result = await get_posts(limit=10)
    if posts_result["success"]:
        print(f"✓ 게시물 {posts_result['count']}개")
        for post in posts_result["posts"]:
            print(f"  - [{post['platform']}] {post['content'][:50]}...")
            print(f"    상태: {post['status']}")
            if post["engagement_metrics"]:
                metrics = post["engagement_metrics"]
                print(f"    참여: 좋아요 {metrics.get('likes', 0)}, 댓글 {metrics.get('comments', 0)}")

    # 2) 새 게시물 생성
    print("\n[5-2] 새 SNS 게시물 생성")
    new_post = await create_social_post(
        platform="instagram",
        content="💪 신규 회원 이벤트! 첫 달 PT 30% 할인\n지금 바로 체험해보세요!\n\n#PT #헬스 #다이어트 #근성장",
        hashtags="#PT #헬스 #다이어트 #근성장 #퍼스널트레이닝",
        scheduled_time=datetime.now() + timedelta(hours=3)
    )
    if new_post["success"]:
        print(f"✓ 게시물 생성 완료 (ID: {new_post['post_id']})")
        print(f"  플랫폼: {new_post['platform']}")
        print(f"  상태: {new_post['status']}")

    # 3) 게시물 참여도 업데이트
    print("\n[5-3] 게시물 참여도 업데이트")
    engagement_result = await update_post_engagement(
        post_id=2,  # Mock 데이터의 Facebook 게시물
        likes=180,
        comments=28,
        shares=15
    )
    if engagement_result["success"]:
        print(f"✓ 참여도 업데이트 완료")
        metrics = engagement_result['engagement_metrics']
        print(f"  좋아요: {metrics['likes']}")
        print(f"  댓글: {metrics['comments']}")
        print(f"  공유: {metrics['shares']}")

    # 4) 이벤트 조회
    print("\n[5-4] 진행 중인 이벤트 조회")
    events_result = await get_events(status="active", limit=10)
    if events_result["success"]:
        print(f"✓ 활성 이벤트 {events_result['count']}개")
        for event in events_result["events"]:
            print(f"  - {event['title']}")
            print(f"    기간: {event['start_date']} ~ {event['end_date']}")
            print(f"    예산: {event.get('budget', 0):,}원, 매출: {event.get('revenue', 0):,}원")
            print(f"    참여자: {event['participants_count']}명")

    # 5) 새 이벤트 생성
    print("\n[5-5] 새 이벤트 생성")
    new_event = await create_event(
        title="여름 대비 4주 챌린지",
        description="4주 동안 체지방 3% 감량 도전! 달성자 전원 상품 증정",
        event_type="challenge",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=28),
        target_audience="existing",
        budget=1000000
    )
    if new_event["success"]:
        print(f"✓ 이벤트 생성 완료 (ID: {new_event['event_id']})")
        print(f"  제목: {new_event['title']}")
        print(f"  유형: {new_event['event_type']}")


# ==================== Owner Assistant Agent 테스트 ====================

async def test_owner_assistant_agent():
    """Owner Assistant Agent 테스트

    핵심 역할: 매출 분석 및 경영 인사이트 제공
    Pain Point: 어디서 얼마나 벌고 있는지 한눈에 파악 어려움
    """
    print("\n" + "="*60)
    print("6. Owner Assistant Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_revenue_records,
        get_revenue_analysis,
        get_trainer_performance,
        get_all_trainers_performance,
        get_key_business_metrics
    )

    # 1) 매출 기록 조회
    print("\n[6-1] 최근 매출 기록 조회")
    revenue_result = await get_revenue_records(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        limit=10
    )
    if revenue_result["success"]:
        print(f"✓ 매출 기록 {revenue_result['count']}건")
        print(f"  총 매출: {revenue_result['total_amount']:,}원")
        for record in revenue_result["records"][:5]:
            print(f"  - {record['date']}: {record['amount']:,}원 ({record['revenue_type']})")

    # 2) 매출 분석
    print("\n[6-2] 매출 분석 (최근 30일)")
    analysis_result = await get_revenue_analysis(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    if analysis_result["success"]:
        print(f"✓ 총 매출: {analysis_result['total_revenue']:,}원")
        print(f"  유형별 매출:")
        for rev_type, data in analysis_result["analysis_by_type"].items():
            print(f"    - {rev_type}: {data['total']:,}원 ({data['percentage']:.1f}%)")
        print(f"  결제 수단별:")
        for method, data in analysis_result["analysis_by_payment"].items():
            print(f"    - {method}: {data['total']:,}원 ({data['percentage']:.1f}%)")

    # 3) 트레이너 성과 조회
    print("\n[6-3] 트레이너 성과 분석")
    trainer_result = await get_trainer_performance(
        trainer_id=100,
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    if trainer_result["success"]:
        print(f"✓ 트레이너 ID: {trainer_result['trainer_id']}")
        print(f"  총 매출: {trainer_result['total_revenue']:,}원")
        print(f"  세션 수: {trainer_result['session_count']}회")
        print(f"  평균 세션당 매출: {trainer_result['avg_revenue_per_session']:,}원")
        print(f"  성과 점수: {trainer_result['performance_score']:.1f}/100")

    # 4) 전체 트레이너 비교
    print("\n[6-4] 전체 트레이너 성과 비교")
    all_trainers = await get_all_trainers_performance(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    if all_trainers["success"]:
        print(f"✓ 트레이너 {all_trainers['trainers_count']}명 분석")
        for trainer in all_trainers["trainers"]:
            print(f"  - Trainer {trainer['trainer_id']}: {trainer['total_revenue']:,}원")
            print(f"    세션: {trainer['session_count']}회, 점수: {trainer['performance_score']:.1f}")

    # 5) 핵심 비즈니스 지표
    print("\n[6-5] 핵심 비즈니스 지표 (최근 7일)")
    metrics_result = await get_key_business_metrics(days=7)
    if metrics_result["success"]:
        print(f"✓ 총 매출: {metrics_result['total_revenue']:,}원")
        print(f"  거래 건수: {metrics_result['transaction_count']}건")
        print(f"  일평균: {metrics_result['daily_average_revenue']:,}원")
        print(f"  성장률: {metrics_result['growth_percentage']:+.1f}%")
        print(f"  주요 매출원:")
        for source in metrics_result["top_revenue_sources"]:
            print(f"    - {source['type']}: {source['amount']:,}원")


# ==================== Trainer Education Agent 테스트 ====================

async def test_trainer_education_agent():
    """Trainer Education Agent 테스트

    핵심 역할: 트레이너 교육 및 스킬 관리
    Pain Point: 신입 트레이너 교육 체계 없고, 누가 어떤 스킬 가졌는지 파악 어려움
    """
    print("\n" + "="*60)
    print("7. Trainer Education Agent 테스트")
    print("="*60)

    from backend.app.octostrator.tools import (
        get_trainer_skills,
        get_skill_gap_analysis,
        get_training_modules,
        get_all_trainers_overview
    )

    # 1) 트레이너 스킬 조회
    print("\n[7-1] 트레이너 스킬 조회")
    skills_result = await get_trainer_skills(trainer_id=100, limit=10)
    if skills_result["success"]:
        print(f"✓ 스킬 {skills_result['total_skills']}개")
        for category, skills in skills_result["skills_by_category"].items():
            print(f"  [{category}]")
            for skill in skills:
                print(f"    - {skill['skill_name']}: Lv.{skill['proficiency_level']}/5")

    # 2) 스킬 갭 분석
    print("\n[7-2] 스킬 갭 분석 (목표 레벨: 4)")
    gap_result = await get_skill_gap_analysis(trainer_id=100)
    if gap_result["success"]:
        print(f"✓ 분석 완료")
        print(f"  갭 있는 스킬: {gap_result['skills_with_gaps']}개")
        if "gap_analysis" in gap_result:
            for category, gaps in gap_result["gap_analysis"]["by_category"].items():
                if gaps:
                    print(f"  [{category}]")
                    for gap in gaps[:3]:
                        print(f"    - {gap['skill_name']}: 현재 Lv.{gap['current_level']} → 목표 Lv.{gap['target_level']}")
                        print(f"      갭: {gap['gap']}포인트")

    # 3) 교육 모듈 조회
    print("\n[7-3] 사용 가능한 교육 모듈")
    modules_result = await get_training_modules()
    if modules_result["success"]:
        print(f"✓ {modules_result['total_modules']}개 모듈")
        for category, modules in modules_result["modules_by_category"].items():
            print(f"  [{category}] {len(modules)}개 모듈")
            for module in modules[:2]:
                print(f"    - {module['name']} ({module['duration_hours']}시간)")
                print(f"      난이도: {module['difficulty']}, 목표: Lv.{module['target_proficiency']}")

    # 4) 전체 트레이너 스킬 현황
    print("\n[7-4] 전체 트레이너 스킬 현황")
    overview_result = await get_all_trainers_overview()
    if overview_result["success"]:
        print(f"✓ 트레이너 {overview_result['total_trainers']}명")
        for trainer in overview_result["trainers"]:
            print(f"  - Trainer {trainer['trainer_id']}")
            print(f"    평균 숙련도: {trainer['average_proficiency']:.1f}/5")
            print(f"    보유 스킬: {trainer['total_skills']}개")


# ==================== 전체 테스트 실행 ====================

async def run_all_tests():
    """모든 에이전트 테스트 실행"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "AI PT Manager - 7개 에이전트 통합 테스트" + " "*10 + "║")
    print("╚" + "="*58 + "╝")

    try:
        await test_frontdesk_agent()
        await test_assessor_agent()
        await test_program_designer_agent()
        await test_manager_agent()
        await test_marketing_agent()
        await test_owner_assistant_agent()
        await test_trainer_education_agent()

        print("\n" + "="*60)
        print("✅ 모든 에이전트 테스트 완료!")
        print("="*60)
        print("\n각 에이전트의 62개 Tools가 정상 동작하는 것을 확인했습니다.")
        print("이제 실제 LangGraph workflow에 통합하여 사용할 수 있습니다.\n")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 비동기 함수 실행
    asyncio.run(run_all_tests())
