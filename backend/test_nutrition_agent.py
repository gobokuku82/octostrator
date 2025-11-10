"""
Nutrition Agent Test Script

식단관리 에이전트 테스트 스크립트
"""

import asyncio
from datetime import datetime, date
from backend.app.octostrator.agents.nutrition.nutrition_agent import NutritionAgent
from backend.database.relation_db.session import init_db
from backend.database.relation_db.nutrition_seed_data import seed_food_database


async def test_nutrition_agent():
    """Nutrition Agent 기능 테스트"""
    print("=" * 60)
    print("Nutrition Agent Test")
    print("=" * 60)

    # Agent 초기화
    agent = NutritionAgent()
    print(f"\n✓ Agent 초기화 완료: {agent.agent_name}")
    print(f"  - Capabilities: {', '.join(agent.get_capabilities())}")

    # 테스트용 user_id
    test_user_id = 1

    # 1. 영양 목표 설정 테스트
    print("\n" + "=" * 60)
    print("1. 영양 목표 설정 테스트")
    print("=" * 60)

    goal_task = {
        "task_type": "set_goal",
        "user_id": test_user_id,
        "nutrition_goal": {
            "goal_type": "muscle_gain",
            "target_calories": 2500,
            "target_protein": 150.0,
            "target_carbs": 300.0,
            "target_fat": 70.0,
            "target_water": 3000,
            "start_date": datetime.now().isoformat()
        }
    }

    result = await agent.process_task(goal_task, {"session_id": "test_session_1"})
    print(f"결과: {result.get('status')}")
    if result.get("status") == "success":
        print(f"  - Goal Type: {result['result']['nutrition_goal'].get('goal_type')}")
        print(f"  - Goal ID: {result['result']['nutrition_goal'].get('goal_id')}")

    # 2. 음식 검색 테스트
    print("\n" + "=" * 60)
    print("2. 음식 검색 테스트")
    print("=" * 60)

    search_task = {
        "task_type": "search_food",
        "user_id": test_user_id,
        "food_search_keyword": "닭"
    }

    result = await agent.process_task(search_task, {"session_id": "test_session_2"})
    print(f"결과: {result.get('status')}")
    if result.get("status") == "success":
        foods = result['result'].get('foods', [])
        print(f"  - 검색된 음식 수: {len(foods)}")
        for food in foods[:3]:  # 상위 3개만 출력
            print(f"    • {food['name']}: {food['calories_per_serving']}kcal/{food['serving_size']}{food['serving_unit']}")

    # 3. 식사 기록 테스트
    print("\n" + "=" * 60)
    print("3. 식사 기록 테스트")
    print("=" * 60)

    meal_task = {
        "task_type": "log_meal",
        "user_id": test_user_id,
        "meal_data": {
            "date": datetime.now().isoformat(),
            "meal_type": "breakfast",
            "foods": [
                {"name": "닭가슴살", "quantity": 150, "unit": "g"},
                {"name": "고구마", "quantity": 200, "unit": "g"},
                {"name": "브로콜리", "quantity": 100, "unit": "g"}
            ],
            "notes": "운동 후 식사"
        }
    }

    result = await agent.process_task(meal_task, {"session_id": "test_session_3"})
    print(f"결과: {result.get('status')}")
    if result.get("status") == "success":
        meal_data = result['result'].get('meal_data', {})
        print(f"  - Meal ID: {meal_data.get('id')}")
        print(f"  - 칼로리: {meal_data.get('total_calories', 0):.1f}kcal")
        print(f"  - 단백질: {meal_data.get('total_protein', 0):.1f}g")
        print(f"  - 탄수화물: {meal_data.get('total_carbs', 0):.1f}g")
        print(f"  - 지방: {meal_data.get('total_fat', 0):.1f}g")

    # 4. 일일 영양 분석 테스트
    print("\n" + "=" * 60)
    print("4. 일일 영양 분석 테스트")
    print("=" * 60)

    analysis_task = {
        "task_type": "analyze_daily",
        "user_id": test_user_id,
        "target_date": date.today().isoformat()
    }

    result = await agent.process_task(analysis_task, {"session_id": "test_session_4"})
    print(f"결과: {result.get('status')}")
    if result.get("status") == "success":
        analysis = result['result'].get('analysis', {})
        print(f"  - 총 칼로리: {analysis.get('total_calories', 0):.1f}kcal")
        print(f"  - 총 단백질: {analysis.get('total_protein', 0):.1f}g")
        print(f"  - 식사 횟수: {analysis.get('meal_count', 0)}회")
        print(f"  - 목표 달성률: {analysis.get('goal_achievement_rate', 0):.1%}")
        print(f"  - 품질 점수: {analysis.get('quality_score', 0):.2f}/1.0")

    # 5. AI 피드백 생성 테스트
    print("\n" + "=" * 60)
    print("5. AI 피드백 생성 테스트")
    print("=" * 60)

    feedback_task = {
        "task_type": "get_daily_feedback",
        "user_id": test_user_id
    }

    result = await agent.process_task(feedback_task, {"session_id": "test_session_5"})
    print(f"결과: {result.get('status')}")
    if result.get("status") == "success":
        feedback = result['result'].get('feedback', '')
        print(f"\n[AI 피드백]")
        print(feedback[:500] + "..." if len(feedback) > 500 else feedback)

    # 6. 식단 추천 테스트
    print("\n" + "=" * 60)
    print("6. 식단 추천 테스트")
    print("=" * 60)

    recommend_task = {
        "task_type": "recommend_meal",
        "user_id": test_user_id,
        "meal_data": {
            "meal_type": "lunch"
        }
    }

    result = await agent.process_task(recommend_task, {"session_id": "test_session_6"})
    print(f"결과: {result.get('status')}")
    if result.get("status") == "success":
        recommendations = result['result'].get('recommendations', [])
        lacking = result['result'].get('lacking_nutrients', '')
        print(f"  - 부족한 영양소: {lacking}")
        if recommendations:
            print(f"\n[AI 추천]")
            print(recommendations[0].get('recommendation_text', '')[:500] + "...")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


async def main():
    """메인 함수"""
    print("\n데이터베이스 초기화 중...")

    # DB 초기화
    init_db()
    print("✓ 데이터베이스 초기화 완료")

    # 음식 시드 데이터 추가
    seed_food_database()

    # 테스트 실행
    await test_nutrition_agent()


if __name__ == "__main__":
    asyncio.run(main())
