"""
SessionManager PostgreSQL 마이그레이션 테스트 스크립트

마이그레이션 완료 후 기능 검증
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.api.session_manager import SessionManager
from app.db.postgre_db import AsyncSessionLocal
from sqlalchemy import text


async def test_postgres_connection():
    """PostgreSQL 연결 테스트"""
    print("\n[1/6] PostgreSQL 연결 테스트...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL 연결 성공!")
            print(f"   버전: {version[:50]}...")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        return False


async def test_sessions_table():
    """sessions 테이블 존재 확인"""
    print("\n[2/6] sessions 테이블 확인...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'sessions'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()

            if not columns:
                print("❌ sessions 테이블이 존재하지 않습니다!")
                return False

            print(f"✅ sessions 테이블 존재 확인!")
            print(f"   컬럼 수: {len(columns)}")
            for col_name, col_type in columns:
                print(f"   - {col_name}: {col_type}")
        return True
    except Exception as e:
        print(f"❌ 테이블 확인 실패: {e}")
        return False


async def test_create_session():
    """세션 생성 테스트"""
    print("\n[3/6] 세션 생성 테스트...")
    try:
        session_mgr = SessionManager(session_ttl_hours=24)
        session_id, expires_at = await session_mgr.create_session(
            user_id="test_user_001",
            metadata={"test": True, "migration_test": "v1.0"}
        )

        print(f"✅ 세션 생성 성공!")
        print(f"   session_id: {session_id}")
        print(f"   expires_at: {expires_at}")
        return session_id
    except Exception as e:
        print(f"❌ 세션 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_validate_session(session_id: str):
    """세션 검증 테스트"""
    print("\n[4/6] 세션 검증 테스트...")
    try:
        session_mgr = SessionManager()
        is_valid = await session_mgr.validate_session(session_id)

        if is_valid:
            print(f"✅ 세션 검증 성공!")
            print(f"   session_id: {session_id} - VALID")
        else:
            print(f"❌ 세션 검증 실패: 세션이 유효하지 않음")

        return is_valid
    except Exception as e:
        print(f"❌ 세션 검증 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_session(session_id: str):
    """세션 조회 테스트"""
    print("\n[5/6] 세션 조회 테스트...")
    try:
        session_mgr = SessionManager()
        session_data = await session_mgr.get_session(session_id)

        if session_data:
            print(f"✅ 세션 조회 성공!")
            print(f"   session_id: {session_data['session_id']}")
            print(f"   user_id: {session_data['user_id']}")
            print(f"   request_count: {session_data['request_count']}")
            print(f"   metadata: {session_data['metadata']}")
        else:
            print(f"❌ 세션 조회 실패: 세션을 찾을 수 없음")

        return session_data is not None
    except Exception as e:
        print(f"❌ 세션 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_active_session_count():
    """활성 세션 수 조회 테스트"""
    print("\n[6/6] 활성 세션 수 조회 테스트...")
    try:
        session_mgr = SessionManager()
        count = await session_mgr.get_active_session_count()

        print(f"✅ 활성 세션 수 조회 성공!")
        print(f"   활성 세션: {count}개")
        return True
    except Exception as e:
        print(f"❌ 활성 세션 수 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup_test_session(session_id: str):
    """테스트 세션 정리"""
    print("\n[Cleanup] 테스트 세션 정리...")
    try:
        session_mgr = SessionManager()
        success = await session_mgr.delete_session(session_id)

        if success:
            print(f"✅ 테스트 세션 삭제 완료: {session_id}")
        else:
            print(f"⚠️ 테스트 세션 삭제 실패 (이미 삭제되었을 수 있음)")
    except Exception as e:
        print(f"⚠️ 정리 중 오류: {e}")


async def main():
    """메인 테스트 함수"""
    print("=" * 70)
    print("SessionManager PostgreSQL 마이그레이션 테스트")
    print("=" * 70)

    results = []
    test_session_id = None

    # Test 1: PostgreSQL 연결
    results.append(await test_postgres_connection())

    if not results[0]:
        print("\n❌ PostgreSQL 연결 실패. 테스트를 중단합니다.")
        return

    # Test 2: 테이블 확인
    results.append(await test_sessions_table())

    if not results[1]:
        print("\n❌ sessions 테이블이 없습니다. 테스트를 중단합니다.")
        return

    # Test 3: 세션 생성
    test_session_id = await test_create_session()
    results.append(test_session_id is not None)

    if test_session_id:
        # Test 4: 세션 검증
        results.append(await test_validate_session(test_session_id))

        # Test 5: 세션 조회
        results.append(await test_get_session(test_session_id))

        # Test 6: 활성 세션 수
        results.append(await test_active_session_count())

        # Cleanup
        await cleanup_test_session(test_session_id)
    else:
        results.extend([False, False, False])

    # 결과 요약
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)

    test_names = [
        "PostgreSQL 연결",
        "sessions 테이블 확인",
        "세션 생성",
        "세션 검증",
        "세션 조회",
        "활성 세션 수 조회"
    ]

    passed = sum(results)
    total = len(results)

    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"[{i}/6] {name}: {status}")

    print("=" * 70)
    print(f"결과: {passed}/{total} 테스트 통과")

    if passed == total:
        print("🎉 모든 테스트 통과! 마이그레이션이 성공적으로 완료되었습니다!")
        return 0
    else:
        print(f"⚠️ {total - passed}개 테스트 실패. 로그를 확인해주세요.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
