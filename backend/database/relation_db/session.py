"""SQLite Database Session Management"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

# SQLite 연결 문자열
DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Engine 생성
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Session:
    """DB 세션 가져오기 (Context Manager)

    사용 예:
        with get_db() as db:
            user = db.query(User).filter(User.id == 1).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    from backend.database.relation_db.models import Base

    Base.metadata.create_all(bind=engine)
    print(f"✓ SQLite 데이터베이스 초기화 완료: {DB_PATH}")
