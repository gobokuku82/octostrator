"""PostgreSQL 데이터베이스 목록 조회"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def list_databases():
    """모든 데이터베이스 목록 조회"""
    # postgres 데이터베이스에 연결 (기본 DB)
    postgres_url = os.getenv("POSTGRES_URL").replace("/octo_chatbot", "/postgres")

    print(f"PostgreSQL URL: {postgres_url}")
    print("연결 시도 중...\n")

    try:
        conn = await asyncpg.connect(postgres_url)
        print("✓ PostgreSQL 연결 성공!\n")

        # 데이터베이스 목록 조회
        databases = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false")

        print("📋 사용 가능한 데이터베이스 목록:")
        print("=" * 50)
        for db in databases:
            print(f"  - {db['datname']}")
        print("=" * 50)

        await conn.close()
        return [db['datname'] for db in databases]

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []

if __name__ == "__main__":
    asyncio.run(list_databases())
