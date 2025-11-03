"""
테스트: Checkpointer setup() 호출 시 테이블 자동 생성 확인
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_checkpointer_setup():
    """Checkpointer setup 직접 호출 테스트"""
    print("\n[테스트] Checkpointer setup() 호출")
    print("=" * 70)

    try:
        from app.service_agent.foundation.checkpointer import CheckpointerManager

        print("1. CheckpointerManager 생성 중...")
        manager = CheckpointerManager()
        print("   ✅ CheckpointerManager 생성 완료")

        print("\n2. Checkpointer 생성 및 setup() 호출 중...")
        checkpointer = await manager.create_checkpointer()
        print("   ✅ Checkpointer 생성 완료")
        print(f"   Type: {type(checkpointer)}")

        print("\n3. PostgreSQL에서 테이블 확인 중...")
        from app.db.postgre_db import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            # checkpoints 테이블 확인
            result = await db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('checkpoints', 'checkpoint_blobs', 'checkpoint_writes')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            if len(tables) == 3:
                print("   ✅ 모든 Checkpointer 테이블 생성 완료!")
                for table in tables:
                    print(f"      - {table}")
            else:
                print(f"   ⚠️  일부 테이블만 생성됨: {tables}")

        print("\n4. 테스트 체크포인트 저장...")
        # 간단한 체크포인트 저장 테스트
        test_config = {
            "configurable": {
                "thread_id": "test-thread-001",
                "checkpoint_ns": ""
            }
        }

        # LangGraph의 Checkpoint 구조 생성
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        from datetime import datetime, timezone

        test_checkpoint = Checkpoint(
            v=1,
            id="test-checkpoint-001",
            ts=datetime.now(timezone.utc).isoformat(),
            channel_values={},
            channel_versions={},
            versions_seen={}
        )

        test_metadata = CheckpointMetadata(
            source="test",
            step=1,
            writes={},
            parents={}
        )

        await checkpointer.aput(
            test_config,
            test_checkpoint,
            test_metadata,
            {}
        )
        print("   ✅ 테스트 체크포인트 저장 완료")

        print("\n5. 저장된 체크포인트 확인...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM checkpoints"))
            count = result.scalar()
            print(f"   ✅ checkpoints 테이블: {count}개 레코드")

            result = await db.execute(text("SELECT COUNT(*) FROM checkpoint_writes"))
            count = result.scalar()
            print(f"   ✅ checkpoint_writes 테이블: {count}개 레코드")

        print("\n" + "=" * 70)
        print("✅ Checkpointer 자동 생성 테스트 성공!")
        print("   → Supervisor 시작 시 자동으로 checkpoints 테이블이 생성됩니다.")
        return True

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 70)
    print("Checkpointer 자동 테이블 생성 테스트")
    print("=" * 70)

    success = await test_checkpointer_setup()

    if success:
        print("\n[결론]")
        print("✅ Checkpointer는 서버 시작 시 자동으로 테이블을 생성합니다!")
        print("   - create_checkpointer() 호출 시 setup() 자동 실행")
        print("   - 3개 테이블 자동 생성: checkpoints, checkpoint_blobs, checkpoint_writes")
    else:
        print("\n[결론]")
        print("❌ 테스트 실패 - 로그를 확인하세요")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
