"""
Test: execution_steps Status 추적 검증
Phase 1-3 구현 검증용 테스트
"""

import asyncio
import sys
from pathlib import Path

# Path setup
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.context import create_default_llm_context


async def test_status_tracking():
    """execution_steps가 status를 올바르게 추적하는지 테스트"""

    print("=" * 80)
    print("TEST: execution_steps Status 추적 검증")
    print("=" * 80)

    # Supervisor 생성
    llm_context = create_default_llm_context()
    supervisor = TeamBasedSupervisor(
        llm_context=llm_context,
        enable_checkpointing=False  # 테스트는 checkpoint 비활성화
    )

    # 간단한 쿼리 실행
    test_query = "강남구 아파트 시세 알려줘"
    print(f"\n쿼리: {test_query}")
    print("\n실행 중...\n")

    result = await supervisor.process_query(
        query=test_query,
        session_id="test-status-tracking-001"
    )

    # Planning State 확인
    planning_state = result.get("planning_state")

    if not planning_state:
        print("[ERROR] planning_state가 없습니다!")
        return

    execution_steps = planning_state.get("execution_steps", [])

    if not execution_steps:
        print("[ERROR] execution_steps가 비어있습니다!")
        return

    print("=" * 80)
    print("[execution_steps 상태 확인]")
    print("=" * 80)

    # 각 step의 상태 출력
    for i, step in enumerate(execution_steps):
        print(f"\n[Step {i}]")
        print(f"  step_id:            {step.get('step_id')}")
        print(f"  agent_name:         {step.get('agent_name')}")
        print(f"  team:               {step.get('team')}")
        print(f"  description:        {step.get('description')}")
        print(f"  [OK] status:          {step.get('status')}")
        print(f"  [OK] progress:        {step.get('progress_percentage')}%")
        print(f"  started_at:         {step.get('started_at')}")
        print(f"  completed_at:       {step.get('completed_at')}")
        print(f"  execution_time_ms:  {step.get('execution_time_ms')}")

        if step.get('error'):
            print(f"  [ERROR] error:      {step.get('error')}")

    print("\n" + "=" * 80)
    print("[검증 항목]")
    print("=" * 80)

    # 검증
    all_have_status = all("status" in step for step in execution_steps)
    all_have_progress = all("progress_percentage" in step for step in execution_steps)
    any_completed = any(step.get("status") == "completed" for step in execution_steps)
    any_in_progress = any(step.get("status") == "in_progress" for step in execution_steps)

    print(f"1. 모든 step에 status 필드 존재:       {'[OK]' if all_have_status else '[FAIL]'}")
    print(f"2. 모든 step에 progress 필드 존재:     {'[OK]' if all_have_progress else '[FAIL]'}")
    print(f"3. 적어도 하나의 step이 completed:     {'[OK]' if any_completed else '[FAIL]'}")
    print(f"4. started_at 시간 기록:               {'[OK]' if execution_steps[0].get('started_at') else '[FAIL]'}")
    print(f"5. completed_at 시간 기록:             {'[OK]' if execution_steps[0].get('completed_at') else '[FAIL]'}")

    # 최종 결과
    print("\n" + "=" * 80)
    if all_have_status and all_have_progress and any_completed:
        print("[SUCCESS] Phase 1-3 구현이 올바르게 작동합니다!")
    else:
        print("[FAILED] 일부 검증 항목이 실패했습니다.")
    print("=" * 80)

    # Cleanup
    await supervisor.cleanup()


if __name__ == "__main__":
    asyncio.run(test_status_tracking())
