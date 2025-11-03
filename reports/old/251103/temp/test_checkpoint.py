# -*- coding: utf-8 -*-
"""
Checkpoint 직렬화 테스트
_progress_callback이 State에서 제거되었는지 확인
"""
import asyncio
import sys
from app.service_agent.foundation.separated_states import MainSupervisorState
from datetime import datetime

# UTF-8 출력 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, 'strict')


async def test_checkpoint_serialization():
    """MainSupervisorState가 직렬화 가능한지 테스트"""

    # 테스트용 State 생성
    test_state = MainSupervisorState(
        query="테스트 쿼리",
        session_id="test-session-123",
        request_id="req_test",
        planning_state=None,
        execution_plan=None,
        search_team_state=None,
        document_team_state=None,
        analysis_team_state=None,
        current_phase="initialized",
        active_teams=[],
        completed_teams=[],
        failed_teams=[],
        team_results={},
        aggregated_results={},
        final_response=None,
        start_time=datetime.now(),
        end_time=None,
        total_execution_time=None,
        error_log=[],
        status="initialized"
    )

    print("✅ MainSupervisorState 생성 성공")
    print(f"   State keys: {list(test_state.keys())}")

    # _progress_callback이 State에 없는지 확인
    if "_progress_callback" in test_state:
        print("❌ 실패: _progress_callback이 State에 존재합니다!")
        return False
    else:
        print("✅ 성공: _progress_callback이 State에 없습니다")

    # msgpack 직렬화 테스트
    try:
        import ormsgpack
        serialized = ormsgpack.packb(test_state)
        print(f"✅ msgpack 직렬화 성공 (크기: {len(serialized)} bytes)")

        deserialized = ormsgpack.unpackb(serialized)
        print(f"✅ msgpack 역직렬화 성공")

        return True
    except Exception as e:
        print(f"❌ 직렬화 실패: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_checkpoint_serialization())
    if result:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n❌ 테스트 실패")
