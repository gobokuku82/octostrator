"""PostgreSQL 연결 테스트"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test_postgres_connection():
    """PostgreSQL 연결 테스트"""
    postgres_url = os.getenv("POSTGRES_URL")

    print(f"PostgreSQL URL: {postgres_url}")
    print("연결 시도 중...")

    try:
        # asyncpg로 연결 테스트
        conn = await asyncpg.connect(postgres_url)
        print("✓ PostgreSQL 연결 성공!")

        # 간단한 쿼리 실행
        version = await conn.fetchval("SELECT version()")
        print(f"✓ PostgreSQL 버전: {version[:50]}...")

        # 연결 종료
        await conn.close()
        print("✓ 연결 종료 완료")

        return True

    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        print("\n[해결 방법]")
        print("1. PostgreSQL이 실행 중인지 확인")
        print("2. .env 파일의 POSTGRES_URL 확인")
        print("3. 데이터베이스 'octo_chatbot'이 생성되어 있는지 확인")
        return False

if __name__ == "__main__":
    asyncio.run(test_postgres_connection())
