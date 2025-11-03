"""
Phase 4-5 검증: process_flow 필드 생성 테스트
StepMapper + API Extension이 올바르게 작동하는지 확인
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.api.converters import state_to_chat_response
from app.service_agent.foundation.config import Config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_process_flow_generation():
    """
    process_flow 필드 생성 테스트

    검증 항목:
    1. ChatResponse에 process_flow 필드가 존재하는가?
    2. process_flow가 None이 아닌가?
    3. process_flow에 최소 1개 이상의 step이 있는가?
    4. 각 step이 필수 필드를 포함하는가? (step, label, agent, status, progress)
    5. step 타입이 올바른가? (planning, searching, analyzing, generating 중 하나)
    """
    print("\n" + "="*80)
    print("Phase 4-5 검증: process_flow 필드 생성 테스트")
    print("="*80 + "\n")

    # 테스트 쿼리
    test_query = "강남구 아파트 시세 알려줘"
    print(f"[TEST] 쿼리: {test_query}\n")

    # Supervisor 초기화
    supervisor = TeamBasedSupervisor(
        enable_checkpointing=True
    )

    try:
        # 1. Supervisor 실행
        print("[STEP 1] Supervisor 실행 중...")
        import time
        start_time = time.time()
        result = await supervisor.process_query(test_query)
        execution_time_ms = int((time.time() - start_time) * 1000)
        print(f"[OK] Supervisor 실행 완료 (실행 시간: {execution_time_ms}ms)\n")

        # 2. API Response 변환
        print("[STEP 2] state_to_chat_response() 변환 중...")
        chat_response = state_to_chat_response(result, execution_time_ms)
        print(f"[OK] ChatResponse 변환 완료\n")

        # 3. process_flow 필드 검증
        print("[STEP 3] process_flow 필드 검증")
        print("-" * 80)

        # 검증 1: process_flow 필드 존재
        if not hasattr(chat_response, 'process_flow'):
            print("[FAIL] ChatResponse에 process_flow 필드가 없습니다!")
            return False
        print("[OK] process_flow 필드 존재")

        # 검증 2: process_flow가 None이 아님
        if chat_response.process_flow is None:
            print("[FAIL] process_flow가 None입니다!")
            print(f"     planning_info: {chat_response.planning_info}")
            return False
        print("[OK] process_flow가 None이 아님")

        # 검증 3: 최소 1개 이상의 step
        if len(chat_response.process_flow) == 0:
            print("[FAIL] process_flow에 step이 없습니다!")
            return False
        print(f"[OK] process_flow에 {len(chat_response.process_flow)}개의 step 존재")

        # 검증 4 & 5: 각 step의 필드 검증
        print("\n[STEP 4] 각 ProcessFlowStep 검증")
        print("-" * 80)

        valid_step_types = {"planning", "searching", "analyzing", "generating", "processing"}
        valid_statuses = {"pending", "in_progress", "completed", "failed", "skipped", "cancelled"}

        all_valid = True
        for i, step in enumerate(chat_response.process_flow):
            print(f"\n[Step {i}]")

            # step이 dict 또는 Pydantic 모델인지 확인
            if isinstance(step, dict):
                step_type = step.get("step")
                label = step.get("label")
                agent = step.get("agent")
                status = step.get("status")
                progress = step.get("progress")
            else:
                step_type = step.step
                label = step.label
                agent = step.agent
                status = step.status
                progress = step.progress

            print(f"  step:     {step_type}")
            print(f"  label:    {label}")
            print(f"  agent:    {agent}")
            print(f"  status:   {status}")
            print(f"  progress: {progress}%")

            # 필수 필드 존재 확인
            if not all([step_type, label, agent, status, progress is not None]):
                print(f"  [FAIL] 필수 필드가 누락되었습니다!")
                all_valid = False
                continue

            # step 타입 유효성 확인
            if step_type not in valid_step_types:
                print(f"  [FAIL] 잘못된 step 타입: {step_type}")
                all_valid = False
                continue

            # status 유효성 확인
            if status not in valid_statuses:
                print(f"  [FAIL] 잘못된 status: {status}")
                all_valid = False
                continue

            # progress 범위 확인
            if not (0 <= progress <= 100):
                print(f"  [FAIL] progress가 범위를 벗어남: {progress}")
                all_valid = False
                continue

            print(f"  [OK] Step {i} 검증 통과")

        print("\n" + "="*80)
        if all_valid:
            print("[SUCCESS] Phase 4-5 구현이 올바르게 작동합니다!")
            print("\n검증 항목:")
            print("1. process_flow 필드 존재:           [OK]")
            print("2. process_flow가 None이 아님:       [OK]")
            print(f"3. step 개수:                        [OK] {len(chat_response.process_flow)}개")
            print("4. 모든 step의 필드 검증:            [OK]")
            print("5. step 타입 및 status 유효성:       [OK]")

            # 실제 데이터 출력
            print("\n[생성된 process_flow 데이터]")
            print("-" * 80)
            for i, step in enumerate(chat_response.process_flow):
                if isinstance(step, dict):
                    print(f"{i+1}. {step['label']} ({step['step']}) - {step['status']} - {step['progress']}%")
                else:
                    print(f"{i+1}. {step.label} ({step.step}) - {step.status} - {step.progress}%")

            print("="*80 + "\n")
            return True
        else:
            print("[FAIL] 일부 검증 항목이 실패했습니다.")
            print("="*80 + "\n")
            return False

    except Exception as e:
        print(f"\n[ERROR] 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if hasattr(supervisor, 'checkpointer_manager'):
            await supervisor.checkpointer_manager.close_all()


if __name__ == "__main__":
    result = asyncio.run(test_process_flow_generation())
    sys.exit(0 if result else 1)
