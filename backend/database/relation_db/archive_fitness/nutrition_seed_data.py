"""
Nutrition Agent Seed Data

음식 데이터베이스 초기 시드 데이터
"""

from datetime import datetime
from .session import get_db
from .models import FoodDatabase
import logging

logger = logging.getLogger(__name__)


# 한국 음식 영양 데이터
KOREAN_FOOD_DATA = [
    # 단백질 (protein)
    {
        "name": "닭가슴살",
        "name_en": "Chicken Breast",
        "category": "protein",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 165,
        "protein": 31.0,
        "carbs": 0.0,
        "fat": 3.6,
        "fiber": 0.0,
        "sodium": 74,
        "sugar": 0.0,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "계란",
        "name_en": "Egg",
        "category": "protein",
        "serving_size": 50,
        "serving_unit": "개",
        "calories_per_serving": 72,
        "protein": 6.3,
        "carbs": 0.4,
        "fat": 4.8,
        "fiber": 0.0,
        "sodium": 71,
        "sugar": 0.4,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "두부",
        "name_en": "Tofu",
        "category": "protein",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 76,
        "protein": 8.1,
        "carbs": 1.9,
        "fat": 4.8,
        "fiber": 0.3,
        "sodium": 7,
        "sugar": 0.6,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "소고기",
        "name_en": "Beef",
        "category": "protein",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 250,
        "protein": 26.0,
        "carbs": 0.0,
        "fat": 15.0,
        "fiber": 0.0,
        "sodium": 72,
        "sugar": 0.0,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "연어",
        "name_en": "Salmon",
        "category": "protein",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 206,
        "protein": 22.0,
        "carbs": 0.0,
        "fat": 13.0,
        "fiber": 0.0,
        "sodium": 59,
        "sugar": 0.0,
        "is_verified": True,
        "source": "korean_fdc"
    },

    # 탄수화물 (carbs)
    {
        "name": "백미",
        "name_en": "White Rice",
        "category": "carbs",
        "serving_size": 210,
        "serving_unit": "공기",
        "calories_per_serving": 312,
        "protein": 5.4,
        "carbs": 68.5,
        "fat": 0.5,
        "fiber": 0.6,
        "sodium": 3,
        "sugar": 0.1,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "현미",
        "name_en": "Brown Rice",
        "category": "carbs",
        "serving_size": 210,
        "serving_unit": "공기",
        "calories_per_serving": 330,
        "protein": 6.7,
        "carbs": 69.8,
        "fat": 2.7,
        "fiber": 3.5,
        "sodium": 5,
        "sugar": 0.7,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "고구마",
        "name_en": "Sweet Potato",
        "category": "carbs",
        "serving_size": 200,
        "serving_unit": "g",
        "calories_per_serving": 172,
        "protein": 2.0,
        "carbs": 39.2,
        "fat": 0.2,
        "fiber": 3.0,
        "sodium": 110,
        "sugar": 12.5,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "감자",
        "name_en": "Potato",
        "category": "carbs",
        "serving_size": 150,
        "serving_unit": "g",
        "calories_per_serving": 114,
        "protein": 2.6,
        "carbs": 26.0,
        "fat": 0.1,
        "fiber": 2.4,
        "sodium": 9,
        "sugar": 1.2,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "귀리",
        "name_en": "Oats",
        "category": "carbs",
        "serving_size": 40,
        "serving_unit": "g",
        "calories_per_serving": 152,
        "protein": 5.4,
        "carbs": 27.3,
        "fat": 2.6,
        "fiber": 4.2,
        "sodium": 2,
        "sugar": 0.4,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "바나나",
        "name_en": "Banana",
        "category": "fruits",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 89,
        "protein": 1.1,
        "carbs": 22.8,
        "fat": 0.3,
        "fiber": 2.6,
        "sodium": 1,
        "sugar": 12.2,
        "is_verified": True,
        "source": "korean_fdc"
    },

    # 채소 (vegetables)
    {
        "name": "브로콜리",
        "name_en": "Broccoli",
        "category": "vegetables",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 34,
        "protein": 2.8,
        "carbs": 6.6,
        "fat": 0.4,
        "fiber": 2.6,
        "sodium": 33,
        "sugar": 1.7,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "시금치",
        "name_en": "Spinach",
        "category": "vegetables",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 23,
        "protein": 2.9,
        "carbs": 3.6,
        "fat": 0.4,
        "fiber": 2.2,
        "sodium": 79,
        "sugar": 0.4,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "양배추",
        "name_en": "Cabbage",
        "category": "vegetables",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 25,
        "protein": 1.3,
        "carbs": 5.8,
        "fat": 0.1,
        "fiber": 2.5,
        "sodium": 18,
        "sugar": 3.2,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "토마토",
        "name_en": "Tomato",
        "category": "vegetables",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 18,
        "protein": 0.9,
        "carbs": 3.9,
        "fat": 0.2,
        "fiber": 1.2,
        "sodium": 5,
        "sugar": 2.6,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "당근",
        "name_en": "Carrot",
        "category": "vegetables",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 41,
        "protein": 0.9,
        "carbs": 9.6,
        "fat": 0.2,
        "fiber": 2.8,
        "sodium": 69,
        "sugar": 4.7,
        "is_verified": True,
        "source": "korean_fdc"
    },

    # 과일 (fruits)
    {
        "name": "사과",
        "name_en": "Apple",
        "category": "fruits",
        "serving_size": 150,
        "serving_unit": "g",
        "calories_per_serving": 78,
        "protein": 0.4,
        "carbs": 20.8,
        "fat": 0.2,
        "fiber": 3.6,
        "sodium": 2,
        "sugar": 15.6,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "딸기",
        "name_en": "Strawberry",
        "category": "fruits",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 32,
        "protein": 0.7,
        "carbs": 7.7,
        "fat": 0.3,
        "fiber": 2.0,
        "sodium": 1,
        "sugar": 4.9,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "블루베리",
        "name_en": "Blueberry",
        "category": "fruits",
        "serving_size": 100,
        "serving_unit": "g",
        "calories_per_serving": 57,
        "protein": 0.7,
        "carbs": 14.5,
        "fat": 0.3,
        "fiber": 2.4,
        "sodium": 1,
        "sugar": 10.0,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "오렌지",
        "name_en": "Orange",
        "category": "fruits",
        "serving_size": 150,
        "serving_unit": "g",
        "calories_per_serving": 70,
        "protein": 1.4,
        "carbs": 17.6,
        "fat": 0.2,
        "fiber": 3.6,
        "sodium": 0,
        "sugar": 14.1,
        "is_verified": True,
        "source": "korean_fdc"
    },

    # 유제품 (dairy)
    {
        "name": "우유",
        "name_en": "Milk",
        "category": "dairy",
        "serving_size": 200,
        "serving_unit": "ml",
        "calories_per_serving": 122,
        "protein": 6.6,
        "carbs": 9.4,
        "fat": 6.4,
        "fiber": 0.0,
        "sodium": 90,
        "sugar": 9.4,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "그릭요거트",
        "name_en": "Greek Yogurt",
        "category": "dairy",
        "serving_size": 150,
        "serving_unit": "g",
        "calories_per_serving": 97,
        "protein": 10.0,
        "carbs": 3.6,
        "fat": 5.0,
        "fiber": 0.0,
        "sodium": 36,
        "sugar": 3.2,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "체다치즈",
        "name_en": "Cheddar Cheese",
        "category": "dairy",
        "serving_size": 30,
        "serving_unit": "g",
        "calories_per_serving": 120,
        "protein": 7.0,
        "carbs": 0.4,
        "fat": 9.9,
        "fiber": 0.0,
        "sodium": 198,
        "sugar": 0.2,
        "is_verified": True,
        "source": "korean_fdc"
    },

    # 견과류/건강 지방 (snacks)
    {
        "name": "아몬드",
        "name_en": "Almonds",
        "category": "snacks",
        "serving_size": 30,
        "serving_unit": "g",
        "calories_per_serving": 173,
        "protein": 6.0,
        "carbs": 6.1,
        "fat": 14.9,
        "fiber": 3.5,
        "sodium": 0,
        "sugar": 1.2,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "호두",
        "name_en": "Walnuts",
        "category": "snacks",
        "serving_size": 30,
        "serving_unit": "g",
        "calories_per_serving": 196,
        "protein": 4.6,
        "carbs": 4.1,
        "fat": 19.6,
        "fiber": 2.0,
        "sodium": 1,
        "sugar": 0.8,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "땅콩버터",
        "name_en": "Peanut Butter",
        "category": "snacks",
        "serving_size": 20,
        "serving_unit": "g",
        "calories_per_serving": 117,
        "protein": 4.6,
        "carbs": 4.0,
        "fat": 10.0,
        "fiber": 1.2,
        "sodium": 90,
        "sugar": 1.8,
        "is_verified": True,
        "source": "korean_fdc"
    },

    # 음료 (beverages)
    {
        "name": "물",
        "name_en": "Water",
        "category": "beverages",
        "serving_size": 250,
        "serving_unit": "ml",
        "calories_per_serving": 0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "fiber": 0.0,
        "sodium": 0,
        "sugar": 0.0,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "녹차",
        "name_en": "Green Tea",
        "category": "beverages",
        "serving_size": 250,
        "serving_unit": "ml",
        "calories_per_serving": 2,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "fiber": 0.0,
        "sodium": 2,
        "sugar": 0.0,
        "is_verified": True,
        "source": "korean_fdc"
    },
    {
        "name": "프로틴쉐이크",
        "name_en": "Protein Shake",
        "category": "beverages",
        "serving_size": 250,
        "serving_unit": "ml",
        "calories_per_serving": 120,
        "protein": 24.0,
        "carbs": 3.0,
        "fat": 1.5,
        "fiber": 0.0,
        "sodium": 150,
        "sugar": 2.0,
        "is_verified": True,
        "source": "korean_fdc"
    }
]


def seed_food_database():
    """음식 데이터베이스에 시드 데이터 추가"""
    try:
        with get_db() as db:
            # 기존 데이터 확인
            existing_count = db.query(FoodDatabase).count()

            if existing_count > 0:
                logger.info(f"[NutritionSeed] Food database already has {existing_count} items. Skipping seed.")
                return

            # 시드 데이터 추가
            for food_data in KOREAN_FOOD_DATA:
                food = FoodDatabase(
                    name=food_data["name"],
                    name_en=food_data["name_en"],
                    category=food_data["category"],
                    serving_size=food_data["serving_size"],
                    serving_unit=food_data["serving_unit"],
                    calories_per_serving=food_data["calories_per_serving"],
                    protein=food_data["protein"],
                    carbs=food_data["carbs"],
                    fat=food_data["fat"],
                    fiber=food_data["fiber"],
                    sodium=food_data["sodium"],
                    sugar=food_data["sugar"],
                    is_verified=food_data["is_verified"],
                    source=food_data["source"],
                    created_at=datetime.utcnow()
                )
                db.add(food)

            db.commit()

            logger.info(f"[NutritionSeed] Successfully added {len(KOREAN_FOOD_DATA)} foods to database")
            print(f"✓ 음식 데이터베이스에 {len(KOREAN_FOOD_DATA)}개 항목 추가 완료")

    except Exception as e:
        logger.error(f"[NutritionSeed] Failed to seed food database: {e}")
        print(f"✗ 음식 데이터베이스 시드 실패: {e}")


if __name__ == "__main__":
    # 직접 실행 시 시드 데이터 추가
    seed_food_database()
