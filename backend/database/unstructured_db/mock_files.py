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
        "lunge_tutorial.txt": "https://www.youtube.com/watch?v=lunge_example\n런지로 하체 균형 잡기",
        "pullup_progression.txt": "https://www.youtube.com/watch?v=pullup_example\n풀업 단계별 훈련법",
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

## 주의사항
- 초보자는 주 2-3회 시작
- 충분한 휴식 필요
- 부상 방지를 위한 올바른 자세 중요
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

## 영양소 비율
- 단백질: 30%
- 탄수화물: 40%
- 지방: 30%

## 팁
- 하루 6끼 소량 식사
- 충분한 수분 섭취 (2L 이상)
- 식사 일지 기록
""",
        "muscle_gain_guide.md": """# 근육 증가 가이드

## 핵심 원칙
1. 점진적 과부하 (Progressive Overload)
2. 충분한 단백질 섭취 (체중 1kg당 2g)
3. 충분한 수면 (7-8시간)

## 운동 프로그램
### 주 4일 분할 프로그램
- 월요일: 가슴 + 삼두
- 화요일: 등 + 이두
- 목요일: 어깨 + 복근
- 금요일: 하체

## 영양 섭취
- 칼로리 잉여 (TDEE + 300-500kcal)
- 단백질: 체중 1kg당 2g
- 운동 후 탄수화물 섭취

## 보충제
- 단백질 파우더
- 크레아틴
- 멀티 비타민
""",
        "stretching_routine.md": """# 스트레칭 루틴

## 운동 전 동적 스트레칭
1. 팔 돌리기 - 10회
2. 다리 스윙 - 각 10회
3. 몸통 비틀기 - 10회
4. 무릎 들기 - 10회

## 운동 후 정적 스트레칭
1. 햄스트링 스트레칭 - 30초
2. 대퇴사두근 스트레칭 - 30초
3. 가슴 스트레칭 - 30초
4. 어깨 스트레칭 - 30초
5. 척추 스트레칭 - 30초

## 효과
- 부상 예방
- 유연성 향상
- 근육 회복 촉진
- 혈액 순환 개선
""",
    }

    for filename, content in documents.items():
        filepath = os.path.join(base_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"✓ Mock 문서 생성: {len(documents)}개")


def create_mock_image_placeholders():
    """Mock 이미지 파일 placeholder 생성"""
    base_path = os.path.join(os.path.dirname(__file__), "images")

    # 실제 이미지 대신 텍스트 파일로 placeholder 생성
    images = {
        "squat_form.txt": "[이미지 placeholder] 스쿼트 올바른 자세 - 사용자가 실제 이미지로 교체",
        "bench_press_form.txt": "[이미지 placeholder] 벤치프레스 올바른 자세 - 사용자가 실제 이미지로 교체",
        "deadlift_form.txt": "[이미지 placeholder] 데드리프트 올바른 자세 - 사용자가 실제 이미지로 교체",
        "lunge_form.txt": "[이미지 placeholder] 런지 올바른 자세 - 사용자가 실제 이미지로 교체",
        "pullup_form.txt": "[이미지 placeholder] 풀업 올바른 자세 - 사용자가 실제 이미지로 교체",
    }

    for filename, content in images.items():
        filepath = os.path.join(base_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

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
