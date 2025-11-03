"""octo_chatbot 데이터베이스 생성"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def create_octo_chatbot_database():
    """octo_chatbot 데이터베이스 생성"""
    # postgres 데이터베이스에 연결 (기본 DB)
    postgres_url = os.getenv("POSTGRES_URL").replace("/octo_chatbot", "/postgres")

    print("PostgreSQL 연결 중...")

    try:
        conn = await asyncpg.connect(postgres_url)
        print("✓ PostgreSQL 연결 성공!\n")

        # octo_chatbot 데이터베이스 생성
        print("octo_chatbot 데이터베이스 생성 중...")
        await conn.execute("CREATE DATABASE octo_chatbot")
        print("✓ octo_chatbot 데이터베이스 생성 완료!\n")

        await conn.close()

        # 생성된 데이터베이스에 연결 테스트
        print("생성된 데이터베이스 연결 테스트...")
        octo_url = os.getenv("POSTGRES_URL")
        octo_conn = await asyncpg.connect(octo_url)
        print("✓ octo_chatbot 데이터베이스 연결 성공!")

        version = await octo_conn.fetchval("SELECT version()")
        print(f"✓ PostgreSQL 버전: {version[:50]}...")

        await octo_conn.close()

        print("\n" + "=" * 50)
        print("✅ 모든 설정 완료! Phase 4.1 진행 가능")
        print("=" * 50)

        return True

    except asyncpg.exceptions.DuplicateDatabaseError:
        print("⚠️  octo_chatbot 데이터베이스가 이미 존재합니다.")
        return True
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_octo_chatbot_database())
