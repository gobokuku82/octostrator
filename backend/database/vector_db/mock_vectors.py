"""Mock Vector Data Generator for FAISS"""
import numpy as np
import os
from backend.database.vector_db.faiss_manager import FAISSManager


def create_mock_exercise_vectors():
    """운동 자료 벡터 Mock 데이터 생성"""

    # 운동 자료 메타데이터
    exercises = [
        {"title": "스쿼트 완벽 가이드", "type": "video", "url": "https://youtube.com/squat", "description": "올바른 스쿼트 자세"},
        {"title": "벤치프레스 팁", "type": "video", "url": "https://youtube.com/bench", "description": "가슴 운동 핵심"},
        {"title": "데드리프트 논문", "type": "research", "url": "https://pubmed.com/deadlift", "description": "등 근육 발달 연구"},
        {"title": "HIIT 트레이닝", "type": "article", "url": "https://blog.com/hiit", "description": "고강도 인터벌"},
        {"title": "다이어트 식단", "type": "article", "url": "https://blog.com/diet", "description": "체중 감량 식단"},
        {"title": "요가 스트레칭", "type": "video", "url": "https://youtube.com/yoga", "description": "유연성 향상"},
        {"title": "달리기 폼 교정", "type": "video", "url": "https://youtube.com/running", "description": "올바른 러닝 자세"},
        {"title": "단백질 섭취 가이드", "type": "article", "url": "https://blog.com/protein", "description": "근육 성장을 위한 단백질"},
    ]

    # Mock 벡터 생성 (실제로는 Sentence Transformer 사용)
    # 여기서는 랜덤 벡터 사용 (사용자가 나중에 실제 임베딩으로 교체)
    vectors = np.random.rand(len(exercises), 384).astype(np.float32)

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
        {"user_id": 4, "name": "최수영", "goal": "weight_loss", "level": "beginner"},
        {"user_id": 5, "name": "정대한", "goal": "muscle_gain", "level": "intermediate"},
    ]

    # Mock 벡터 생성
    vectors = np.random.rand(len(members), 384).astype(np.float32)

    # FAISS Manager 초기화
    index_path = os.path.join(os.path.dirname(__file__), "member_index")
    manager = FAISSManager(index_path, dimension=384)

    # 벡터 추가
    manager.add_vectors(vectors, members)

    # 저장
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
