"""
Checkpoint Database Setup Script

PostgreSQL 데이터베이스 생성 및 LangGraph AsyncPostgresSaver 테이블 셋업.

사용법:
    python -m backend.scripts.setup_checkpointer

참고:
    - langgraph-checkpoint-postgres 3.0+ 기준
    - https://pypi.org/project/langgraph-checkpoint-postgres/
"""

import asyncio
import sys
import platform
from pathlib import Path

# Windows 호환성: SelectorEventLoop 사용 (psycopg async 요구사항)
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import psycopg
from psycopg import sql
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ========================================
# 설정
# ========================================
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "root1234"
DATABASE_NAME = "dream_agent"

# 연결 문자열
ADMIN_CONN_STRING = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/postgres"
CHECKPOINT_DB_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{DATABASE_NAME}"


def create_database():
    """
    dream_agent 데이터베이스 생성 (동기 작업).

    PostgreSQL에서 CREATE DATABASE는 트랜잭션 내에서 실행할 수 없으므로
    autocommit 모드로 실행해야 합니다.
    """
    print(f"[1/3] PostgreSQL에 연결 중... ({POSTGRES_HOST}:{POSTGRES_PORT})")

    try:
        # autocommit=True 필수 (CREATE DATABASE는 트랜잭션 내에서 실행 불가)
        with psycopg.connect(ADMIN_CONN_STRING, autocommit=True) as conn:
            with conn.cursor() as cur:
                # 데이터베이스 존재 여부 확인
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (DATABASE_NAME,)
                )
                exists = cur.fetchone()

                if exists:
                    print(f"      데이터베이스 '{DATABASE_NAME}'가 이미 존재합니다.")
                else:
                    # 데이터베이스 생성
                    cur.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(DATABASE_NAME)
                        )
                    )
                    print(f"      데이터베이스 '{DATABASE_NAME}' 생성 완료!")

    except psycopg.OperationalError as e:
        print(f"      오류: PostgreSQL 연결 실패 - {e}")
        print("      PostgreSQL 서버가 실행 중인지 확인하세요.")
        sys.exit(1)


async def setup_checkpoint_tables():
    """
    AsyncPostgresSaver에 필요한 체크포인트 테이블 생성.

    LangGraph checkpoint-postgres 3.0+에서는 .setup() 메서드를 호출하여
    필요한 테이블을 자동 생성합니다.

    Note: from_conn_string()을 사용하면 autocommit이 올바르게 설정되어
    CREATE INDEX CONCURRENTLY 문제를 피할 수 있습니다.
    """
    print(f"\n[2/3] 체크포인트 테이블 생성 중...")
    print(f"      연결: {DATABASE_NAME}@{POSTGRES_HOST}")

    try:
        # from_conn_string을 사용하여 autocommit 설정이 올바르게 적용되도록 함
        async with AsyncPostgresSaver.from_conn_string(CHECKPOINT_DB_URI) as checkpointer:
            # 테이블 생성 (.setup() 호출)
            await checkpointer.setup()

            print("      체크포인트 테이블 생성 완료!")
            print("      - checkpoint_migrations")
            print("      - checkpoints")
            print("      - checkpoint_blobs")
            print("      - checkpoint_writes")

    except Exception as e:
        print(f"      오류: 테이블 생성 실패 - {e}")
        raise


def print_env_config():
    """
    .env 파일에 추가할 설정 출력.
    """
    print(f"\n[3/3] .env 파일에 다음 설정을 추가하세요:")
    print("=" * 60)
    print(f"# Checkpoint Database (LangGraph AsyncPostgresSaver)")
    print(f"CHECKPOINT_DB_URI={CHECKPOINT_DB_URI}")
    print("=" * 60)


def verify_setup():
    """
    셋업 검증 - 테이블이 정상적으로 생성되었는지 확인 (동기 버전).
    """
    print(f"\n[검증] 테이블 확인 중...")

    with psycopg.connect(CHECKPOINT_DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cur.fetchall()

            if tables:
                print("      생성된 테이블:")
                for (table_name,) in tables:
                    print(f"        - {table_name}")
            else:
                print("      경고: 테이블이 생성되지 않았습니다.")


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("LangGraph Checkpoint Database Setup")
    print("=" * 60)

    # 1. 데이터베이스 생성
    create_database()

    # 2. 체크포인트 테이블 생성
    await setup_checkpoint_tables()

    # 3. 검증
    verify_setup()

    # 4. 환경 설정 안내
    print_env_config()

    print("\n✓ 셋업 완료!")


if __name__ == "__main__":
    asyncio.run(main())
