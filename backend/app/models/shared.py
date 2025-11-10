"""
Shared Generic Models - 범용 공유 모델

도메인에 구애받지 않는 범용 공유 모델을 제공합니다.

⚠️ 현재 상태 (범용 시스템)
==========================================
Bookmark 모델은 모든 도메인에서 사용할 수 있는 범용 북마크 기능을 제공합니다:
- URL 기반 자료 저장
- 카테고리별 분류
- 요약 정보 저장

아카이브된 모델:
- ❌ ExerciseDB: PT 특화 모델 → backend/app/models/archive/fitness/ 이동
  (muscle_group, equipment 등 fitness 도메인 전용 필드 포함)

🔮 도메인별 확장 예시
==========================================

## Fitness 도메인: 운동 데이터베이스

```python
# backend/app/models/fitness_models.py
class ExerciseDB(Base):
    \"\"\"Fitness 도메인 운동 데이터베이스\"\"\"
    __tablename__ = "fitness_exercise_db"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    muscle_group = Column(String(50))  # legs, chest, back, shoulders, arms
    difficulty = Column(String(20))  # beginner, intermediate, advanced
    equipment = Column(String(100))  # barbell, dumbbell, bodyweight, machine
    description = Column(Text)
    video_url = Column(String(500))
```

## Medical 도메인: 의료 자료 데이터베이스

```python
# backend/app/models/medical_models.py
class MedicalReferenceDB(Base):
    \"\"\"Medical 도메인 의료 참고 자료\"\"\"
    __tablename__ = "medical_reference_db"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    medical_category = Column(String(100))  # cardiology, neurology, etc.
    icd_code = Column(String(20))  # ICD-10 code
    description = Column(Text)
    reference_url = Column(String(500))
```

## Legal 도메인: 법률 판례 데이터베이스

```python
# backend/app/models/legal_models.py
class LegalPrecedentDB(Base):
    \"\"\"Legal 도메인 법률 판례 데이터베이스\"\"\"
    __tablename__ = "legal_precedent_db"

    id = Column(Integer, primary_key=True)
    case_name = Column(String(300), nullable=False)
    court_name = Column(String(200))
    decision_date = Column(Date)
    case_number = Column(String(100))
    legal_area = Column(String(100))  # civil, criminal, administrative
    summary = Column(Text)
    full_text_url = Column(String(500))
```

📚 See Also
==========================================
- DOMAIN_MODELS_GUIDE.md: 도메인별 모델 추가 가이드
- backend/app/models/archive/fitness/: PT 도메인 참고 자료
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from .base import Base


class Bookmark(Base):
    """
    범용 북마크 모델

    모든 도메인에서 사용할 수 있는 URL 기반 자료 북마크 기능을 제공합니다.
    사용자가 중요한 웹 자료(비디오, 기사, 연구 논문 등)를 저장하고 분류할 수 있습니다.

    Attributes:
        id: 북마크 고유 ID (Primary Key)
        user_id: 사용자 ID (Foreign Key to users.id)
        title: 북마크 제목
        url: 자료 URL
        category: 카테고리 (예: "video", "article", "research", "documentation")
        summary: 자료 요약 (선택적)
        tags: 태그 (JSON 형식, 선택적)
        created_at: 북마크 생성 시각
        updated_at: 최종 수정 시각

    Examples:
        >>> # Fitness 도메인: 운동 영상 북마크
        >>> bookmark = Bookmark(
        ...     user_id=1,
        ...     title="스쿼트 자세 교정 영상",
        ...     url="https://youtube.com/watch?v=...",
        ...     category="video",
        ...     summary="올바른 스쿼트 자세에 대한 설명"
        ... )

        >>> # Medical 도메인: 의학 논문 북마크
        >>> bookmark = Bookmark(
        ...     user_id=2,
        ...     title="COVID-19 Treatment Guidelines",
        ...     url="https://pubmed.ncbi.nlm.nih.gov/...",
        ...     category="research",
        ...     summary="코로나19 치료 가이드라인"
        ... )

        >>> # Legal 도메인: 판례 북마크
        >>> bookmark = Bookmark(
        ...     user_id=3,
        ...     title="대법원 2023다12345 판결",
        ...     url="https://www.scourt.go.kr/...",
        ...     category="case_law",
        ...     summary="계약 해제 관련 중요 판례"
        ... )
    """
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    category = Column(String(50))  # video, article, research, documentation, case_law 등
    summary = Column(Text)
    tags = Column(Text)  # JSON 형식의 태그 리스트 (선택적)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
