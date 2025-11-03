"""
AsyncSqliteSaver Checkpoint와 LLM Tool Selection Decision Logging 통합 테스트
"""

import asyncio
import logging
import json
import sqlite3
from pathlib import Path
from datetime import datetime

import sys
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.config import Config
from app.service_agent.foundation.decision_logger import DecisionLogger

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CheckpointAndLoggingTester:
    """Checkpoint와 Decision Logging 통합 테스터"""

    def __init__(self):
        self.checkpoint_db = Config.CHECKPOINT_DIR / "default_checkpoint.db"
        self.decision_db = Config.AGENT_LOGGING_DIR / "decisions.db"
        self.test_results = []

    def _print_section(self, title: str):
        """섹션 헤더 출력"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def _print_result(self, test_name: str, passed: bool, details: str = ""):
        """테스트 결과 출력"""
        status = "[PASS]" if passed else "[FAILED]"
        print(f"{status} {test_name}")
        if details:
            print(f"       {details}")
        self.test_results.append({"test": test_name, "passed": passed, "details": details})

    async def test_checkpoint_save(self) -> bool:
        """Checkpoint 저장 테스트"""
        self._print_section("Test 1: Checkpoint Save")

        try:
            # TeamSupervisor 초기화 (checkpointing 활성화)
            supervisor = TeamBasedSupervisor(enable_checkpointing=True)

            # 테스트 쿼리 실행
            test_query = "전세금 5% 인상 한도가 얼마인가요?"
            session_id = "test_session_001"

            logger.info(f"Running query with session_id: {session_id}")
            result = await supervisor.process_query(query=test_query, session_id=session_id)

            # Cleanup to flush checkpoint data
            await supervisor.cleanup()

            # 결과 확인
            has_response = bool(result.get("final_response"))
            self._print_result(
                "Query execution",
                has_response,
                f"Response type: {result.get('final_response', {}).get('type')}"
            )

            # Checkpoint DB 파일 확인
            checkpoint_exists = self.checkpoint_db.exists()
            self._print_result(
                "Checkpoint DB file created",
                checkpoint_exists,
                f"Path: {self.checkpoint_db}"
            )

            # Checkpoint DB 내용 확인
            if checkpoint_exists:
                conn = sqlite3.connect(str(self.checkpoint_db))
                cursor = conn.cursor()

                # 테이블 확인
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                has_checkpoint_table = 'checkpoints' in tables or 'checkpoint_writes' in tables

                self._print_result(
                    "Checkpoint tables exist",
                    has_checkpoint_table,
                    f"Tables: {', '.join(tables)}"
                )

                # Checkpoint 데이터 확인
                if 'checkpoints' in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (session_id,))
                    checkpoint_count = cursor.fetchone()[0]
                    self._print_result(
                        "Checkpoint data saved",
                        checkpoint_count > 0,
                        f"Checkpoint count for {session_id}: {checkpoint_count}"
                    )

                conn.close()

            return has_response and checkpoint_exists

        except Exception as e:
            logger.error(f"Checkpoint save test failed: {e}", exc_info=True)
            self._print_result("Checkpoint save test", False, f"Error: {str(e)}")
            return False

    async def test_checkpoint_load(self) -> bool:
        """Checkpoint 로드 테스트"""
        self._print_section("Test 2: Checkpoint Load")

        try:
            # 같은 session_id로 재실행
            supervisor = TeamBasedSupervisor(enable_checkpointing=True)
            session_id = "test_session_001"

            # 이전 checkpoint 확인
            if self.checkpoint_db.exists():
                conn = sqlite3.connect(str(self.checkpoint_db))
                cursor = conn.cursor()

                # Checkpoint 조회
                if 'checkpoints' in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
                    cursor.execute(f"SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (session_id,))
                    checkpoint_count = cursor.fetchone()[0]
                    self._print_result(
                        "Previous checkpoints found",
                        checkpoint_count > 0,
                        f"Found {checkpoint_count} checkpoints for {session_id}"
                    )

                conn.close()

            # 새로운 쿼리로 같은 세션 계속
            test_query = "그럼 현재 강남구 아파트 시세는 얼마인가요?"
            logger.info(f"Continuing session: {session_id}")
            result = await supervisor.process_query(query=test_query, session_id=session_id)

            # Cleanup to flush checkpoint data
            await supervisor.cleanup()

            has_response = bool(result.get("final_response"))
            self._print_result(
                "Continue session query",
                has_response,
                f"Response type: {result.get('final_response', {}).get('type')}"
            )

            return has_response

        except Exception as e:
            logger.error(f"Checkpoint load test failed: {e}", exc_info=True)
            self._print_result("Checkpoint load test", False, f"Error: {str(e)}")
            return False

    async def test_llm_tool_selection(self) -> bool:
        """LLM Tool Selection 테스트"""
        self._print_section("Test 3: LLM Tool Selection")

        try:
            supervisor = TeamBasedSupervisor(enable_checkpointing=False)

            # 다양한 질문 유형 테스트
            test_cases = [
                ("전세금 인상률 한도가 얼마인가요?", ["legal_search"]),
                ("강남구 아파트 시세 알려주세요", ["market_data"]),
                ("전세 계약할 때 시세와 법률 확인해주세요", ["legal_search", "market_data"])
            ]

            all_passed = True
            for query, expected_tools in test_cases:
                result = await supervisor.process_query(query=query, session_id=f"tool_test_{hash(query)}")

                # 응답 확인
                has_response = bool(result.get("final_response"))
                if not has_response:
                    all_passed = False

                self._print_result(
                    f"Tool selection: {query[:40]}...",
                    has_response,
                    f"Expected: {expected_tools}"
                )

            return all_passed

        except Exception as e:
            logger.error(f"LLM tool selection test failed: {e}", exc_info=True)
            self._print_result("LLM tool selection test", False, f"Error: {str(e)}")
            return False

    async def test_decision_logging(self) -> bool:
        """Decision Logging 저장 테스트"""
        self._print_section("Test 4: Decision Logging")

        try:
            supervisor = TeamBasedSupervisor(enable_checkpointing=False)

            # Decision Logger 직접 확인
            decision_logger = DecisionLogger()

            # 테스트 쿼리 실행
            test_query = "전세금 인상 가능한가요?"
            result = await supervisor.process_query(query=test_query, session_id="decision_log_test")

            # Decision DB 확인
            decision_db_exists = self.decision_db.exists()
            self._print_result(
                "Decision DB file created",
                decision_db_exists,
                f"Path: {self.decision_db}"
            )

            if decision_db_exists:
                conn = sqlite3.connect(str(self.decision_db))
                cursor = conn.cursor()

                # tool_decisions 테이블 확인
                cursor.execute("SELECT COUNT(*) FROM tool_decisions")
                tool_decision_count = cursor.fetchone()[0]
                self._print_result(
                    "Tool decisions logged",
                    tool_decision_count > 0,
                    f"Total tool decisions: {tool_decision_count}"
                )

                # 최근 decision 조회
                cursor.execute("""
                    SELECT agent_type, query, selected_tools, confidence
                    FROM tool_decisions
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    agent_type, query, selected_tools, confidence = row
                    self._print_result(
                        "Decision details",
                        True,
                        f"Agent: {agent_type}, Tools: {selected_tools}, Confidence: {confidence}"
                    )

                conn.close()

            # Decision Logger API로 통계 조회
            stats = decision_logger.get_tool_usage_stats(agent_type="search")
            self._print_result(
                "Tool usage statistics",
                stats['total_decisions'] > 0,
                f"Total: {stats['total_decisions']}, Success rate: {stats['success_rate']:.2f}"
            )

            return decision_db_exists and tool_decision_count > 0

        except Exception as e:
            logger.error(f"Decision logging test failed: {e}", exc_info=True)
            self._print_result("Decision logging test", False, f"Error: {str(e)}")
            return False

    async def test_integrated(self) -> bool:
        """통합 테스트: Checkpoint + Tool Selection + Decision Logging"""
        self._print_section("Test 5: Integrated Test")

        try:
            supervisor = TeamBasedSupervisor(enable_checkpointing=True)
            session_id = "integrated_test_session"

            # Step 1: 첫 번째 질문 (법률 검색)
            query1 = "전세금 인상률 한도를 알려주세요"
            result1 = await supervisor.process_query(query=query1, session_id=session_id)
            step1_ok = bool(result1.get("final_response"))
            self._print_result("Step 1: Legal query", step1_ok)

            # Step 2: 두 번째 질문 (시세 검색)
            query2 = "강남구 아파트 시세도 확인해주세요"
            result2 = await supervisor.process_query(query=query2, session_id=session_id)
            step2_ok = bool(result2.get("final_response"))
            self._print_result("Step 2: Market query", step2_ok)

            # Cleanup to flush checkpoint data
            await supervisor.cleanup()

            # Step 3: Checkpoint 확인
            checkpoint_ok = False
            if self.checkpoint_db.exists():
                conn = sqlite3.connect(str(self.checkpoint_db))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (session_id,))
                checkpoint_count = cursor.fetchone()[0]
                checkpoint_ok = checkpoint_count > 0
                conn.close()
            self._print_result("Step 3: Checkpoints saved", checkpoint_ok, f"Count: {checkpoint_count}")

            # Step 4: Decision Log 확인
            decision_ok = False
            if self.decision_db.exists():
                conn = sqlite3.connect(str(self.decision_db))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tool_decisions")
                decision_count = cursor.fetchone()[0]
                decision_ok = decision_count >= 2  # 최소 2개 (각 query당 1개)
                conn.close()
            self._print_result("Step 4: Decisions logged", decision_ok, f"Count: {decision_count}")

            return step1_ok and step2_ok and checkpoint_ok and decision_ok

        except Exception as e:
            logger.error(f"Integrated test failed: {e}", exc_info=True)
            self._print_result("Integrated test", False, f"Error: {str(e)}")
            return False

    def print_summary(self):
        """테스트 결과 요약 출력"""
        self._print_section("Test Summary")

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed}")

        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")

        print("\n" + "=" * 80)

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "=" * 80)
        print("  AsyncSqliteSaver Checkpoint + LLM Tool Selection Test Suite")
        print("=" * 80)

        # Test 1: Checkpoint 저장
        await self.test_checkpoint_save()

        # Test 2: Checkpoint 로드
        await self.test_checkpoint_load()

        # Test 3: LLM Tool Selection
        await self.test_llm_tool_selection()

        # Test 4: Decision Logging
        await self.test_decision_logging()

        # Test 5: 통합 테스트
        await self.test_integrated()

        # 결과 요약
        self.print_summary()


async def main():
    """메인 테스트 실행"""
    tester = CheckpointAndLoggingTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
