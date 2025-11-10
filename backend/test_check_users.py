"""Quick test to check if users exist in database"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from database.session import get_db
from sqlalchemy import select, text


async def check_users():
    async with await get_db() as session:
        # Check if users table exists and has data
        result = await session.execute(text("SELECT id, name, email FROM users LIMIT 5"))
        users = result.fetchall()

        if users:
            print("Found users:")
            for user in users:
                print(f"  ID: {user[0]}, Name: {user[1]}, Email: {user[2]}")
        else:
            print("No users found in database")

            # Try to create a test user
            print("\nCreating test user...")
            from backend.app.models.core import User
            test_user = User(
                name="테스트 회원",
                email="test@example.com",
                phone="010-1234-5678",
                goal="fitness",
                level="beginner"
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            print(f"  ✓ Created test user ID={test_user.id}")

if __name__ == "__main__":
    asyncio.run(check_users())
