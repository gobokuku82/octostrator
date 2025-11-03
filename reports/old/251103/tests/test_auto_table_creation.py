"""
테스트: 서버 시작 시 테이블 자동 생성 여부 확인

다른 개발자가 서버만 실행했을 때 sessions 테이블이 자동으로 생성되는지 테스트
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.postgre_db import AsyncSessionLocal
from sqlalchemy import text


async def check_sessions_table():
    """sessions 테이블 존재 여부 확인"""
    print("\n[1/2] sessions 테이블 확인 중...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'sessions'
                )
            """))
            exists = result.scalar()

            if exists:
                print("✅ sessions 테이블이 존재합니다!")

                # 스키마 확인
                result = await db.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'sessions'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                print(f"   컬럼 수: {len(columns)}")
                for col_name, col_type in columns:
                    print(f"   - {col_name}: {col_type}")
            else:
                print("❌ sessions 테이블이 없습니다!")
                print("   → SQLAlchemy는 자동으로 테이블을 생성하지 않습니다.")
                print("   → 수동 생성 필요: psql ... -f migrations/create_sessions_table.sql")

            return exists
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


async def check_checkpoints_table():
    """checkpoints 테이블 존재 여부 확인"""
    print("\n[2/2] checkpoints 테이블 확인 중...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'checkpoints'
                )
            """))
            exists = result.scalar()

            if exists:
                print("✅ checkpoints 테이블이 존재합니다!")

                # 개수 확인
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM checkpoints
                """))
                count = result.scalar()
                print(f"   저장된 체크포인트: {count}개")
            else:
                print("❌ checkpoints 테이블이 없습니다!")
                print("   → 서버 시작 시 Supervisor pre-warming에서 자동 생성됩니다.")
                print("   → 또는 첫 번째 대화 요청 시 생성됩니다.")

            return exists
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


async def main():
    print("=" * 70)
    print("테스트: 서버 시작 시 테이블 자동 생성 여부")
    print("=" * 70)

    sessions_exists = await check_sessions_table()
    checkpoints_exists = await check_checkpoints_table()

    print("\n" + "=" * 70)
    print("결과 요약")
    print("=" * 70)

    if sessions_exists and checkpoints_exists:
        print("✅ 모든 시스템 테이블이 존재합니다!")
        print("   서버를 그대로 실행할 수 있습니다.")
    elif not sessions_exists and not checkpoints_exists:
        print("⚠️ 시스템 테이블이 모두 없습니다!")
        print("\n해결 방법:")
        print("1. sessions 테이블 생성:")
        print("   psql \"postgresql://...\" -f migrations/create_sessions_table.sql")
        print("\n2. 서버 시작 (checkpoints 자동 생성):")
        print("   uvicorn app.main:app --reload")
    elif not sessions_exists:
        print("⚠️ sessions 테이블만 없습니다!")
        print("\n해결 방법:")
        print("   psql \"postgresql://...\" -f migrations/create_sessions_table.sql")
    elif not checkpoints_exists:
        print("⚠️ checkpoints 테이블만 없습니다!")
        print("   → 서버 시작 시 자동 생성됩니다.")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
