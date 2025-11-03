"""
Phase 1 Query Decomposition Test Runner
단일 질문 20개 + 복합 질문(2개 작업) 20개 테스트
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import traceback

# Path setup
import os
current_file = Path(__file__).resolve()
# Go up: tests -> reports -> service_agent -> app -> backend
backend_dir = current_file.parent.parent.parent.parent.parent
print(f"Backend dir: {backend_dir}")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
print(f"sys.path[0]: {sys.path[0]}")

from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.cognitive_agents.query_decomposer import QueryDecomposer
from app.service_agent.foundation.context import create_default_llm_context


class Phase1TestRunner:
    """Phase 1 테스트 실행기"""

    def __init__(self):
        self.test_data_path = Path(__file__).parent / "test_queries_phase1.json"
        self.results_path = Path(__file__).parent.parent / "phase1_test_results.json"
        self.log_path = Path(__file__).parent.parent / "phase1_test_log.txt"

        self.planning_agent = None
        self.query_decomposer = None
        self.test_results = []

        # 로그 설정
        self.setup_logging()

    def setup_logging(self):
        """로깅 설정"""
        # 파일 핸들러
        file_handler = logging.FileHandler(
            self.log_path,
            mode='w',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # 루트 로거 설정
        logging.basicConfig(
            level=logging.DEBUG,
            handlers=[file_handler, console_handler]
        )

        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """시스템 초기화"""
        self.logger.info("="*80)
        self.logger.info("Phase 1 Test Runner 초기화 중...")
        self.logger.info("="*80)

        try:
            # LLM Context 생성
            llm_context = create_default_llm_context()
            self.logger.info("✓ LLM Context 초기화 완료")

            # Planning Agent 초기화
            self.planning_agent = PlanningAgent(llm_context)
            self.logger.info("✓ Planning Agent 초기화 완료")

            # Query Decomposer 초기화
            from app.service_agent.llm_manager import LLMService
            llm_service = LLMService(llm_context=llm_context)
            self.query_decomposer = QueryDecomposer(llm_service)
            self.logger.info("✓ Query Decomposer 초기화 완료")

            self.logger.info("시스템 초기화 완료\n")

        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def load_test_data(self) -> Dict[str, Any]:
        """테스트 데이터 로드"""
        self.logger.info(f"테스트 데이터 로드: {self.test_data_path}")

        with open(self.test_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total = len(data['single_task_queries']) + len(data['dual_task_queries'])
        self.logger.info(f"총 {total}개 질문 로드 완료\n")

        return data

    async def test_single_query(self, test_case: Dict[str, Any], index: int) -> Dict[str, Any]:
        """단일 질문 테스트"""
        query_id = test_case['id']
        query = test_case['query']

        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"[{index}] 단일 질문 테스트: {query_id}")
        self.logger.info(f"질문: {query}")
        self.logger.info(f"{'='*80}")

        result = {
            "id": query_id,
            "query": query,
            "category": test_case['category'],
            "expected_intent": test_case['expected_intent'],
            "expected_agent": test_case['expected_agent'],
            "timestamp": datetime.now().isoformat()
        }

        try:
            start_time = datetime.now()

            # 1. Intent 분석
            self.logger.info("\n[Step 1] Intent 분석...")
            intent_result = await self.planning_agent.analyze_intent(query)

            result["intent_analysis"] = {
                "intent_type": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "keywords": intent_result.keywords,
                "suggested_agents": intent_result.suggested_agents,
                "reasoning": intent_result.reasoning,
                "fallback": intent_result.fallback
            }

            self.logger.info(f"  의도: {intent_result.intent_type.value}")
            self.logger.info(f"  신뢰도: {intent_result.confidence:.2f}")
            self.logger.info(f"  추천 Agent: {intent_result.suggested_agents}")

            # 2. Query Decomposition
            self.logger.info("\n[Step 2] Query Decomposition...")
            decomposed = await self.query_decomposer.decompose(
                query=query,
                intent_result={
                    "intent": intent_result.intent_type.value,
                    "confidence": intent_result.confidence,
                    "keywords": intent_result.keywords
                }
            )

            result["decomposition"] = {
                "is_compound": decomposed.is_compound,
                "num_tasks": len(decomposed.sub_tasks),
                "execution_mode": decomposed.execution_mode.value,
                "tasks": [
                    {
                        "description": task.description,
                        "type": task.task_type.value,
                        "agent_team": task.agent_team,
                        "dependencies": task.dependencies
                    }
                    for task in decomposed.sub_tasks
                ],
                "confidence": decomposed.confidence,
                "reasoning": decomposed.reasoning
            }

            self.logger.info(f"  복합 질문: {decomposed.is_compound}")
            self.logger.info(f"  작업 수: {len(decomposed.sub_tasks)}")
            self.logger.info(f"  실행 모드: {decomposed.execution_mode.value}")

            # 3. Execution Plan 생성
            self.logger.info("\n[Step 3] Execution Plan 생성...")
            plan = await self.planning_agent.create_execution_plan(intent_result)

            result["execution_plan"] = {
                "strategy": plan.strategy.value,
                "num_steps": len(plan.steps),
                "steps": [
                    {
                        "agent": step.agent_name,
                        "priority": step.priority,
                        "dependencies": step.dependencies
                    }
                    for step in plan.steps
                ],
                "estimated_time": plan.estimated_time
            }

            self.logger.info(f"  전략: {plan.strategy.value}")
            self.logger.info(f"  단계 수: {len(plan.steps)}")

            # 실행 시간 계산
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            result["execution_time"] = execution_time

            # 검증
            result["validation"] = self._validate_single_result(result, test_case)

            result["status"] = "success"
            self.logger.info(f"\n✓ 테스트 성공 (소요시간: {execution_time:.2f}초)")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            self.logger.error(f"\n✗ 테스트 실패: {e}")
            self.logger.error(traceback.format_exc())

        return result

    async def test_dual_query(self, test_case: Dict[str, Any], index: int) -> Dict[str, Any]:
        """복합 질문 (2개 작업) 테스트"""
        query_id = test_case['id']
        query = test_case['query']

        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"[{index}] 복합 질문 테스트: {query_id}")
        self.logger.info(f"질문: {query}")
        self.logger.info(f"{'='*80}")

        result = {
            "id": query_id,
            "query": query,
            "category": test_case['category'],
            "expected_intent": test_case['expected_intent'],
            "expected_agents": test_case['expected_agents'],
            "expected_decomposition": test_case['expected_decomposition'],
            "expected_tasks": test_case['expected_tasks'],
            "timestamp": datetime.now().isoformat()
        }

        try:
            start_time = datetime.now()

            # 1. Intent 분석
            self.logger.info("\n[Step 1] Intent 분석...")
            intent_result = await self.planning_agent.analyze_intent(query)

            result["intent_analysis"] = {
                "intent_type": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "keywords": intent_result.keywords,
                "suggested_agents": intent_result.suggested_agents,
                "reasoning": intent_result.reasoning
            }

            self.logger.info(f"  의도: {intent_result.intent_type.value}")
            self.logger.info(f"  신뢰도: {intent_result.confidence:.2f}")
            self.logger.info(f"  추천 Agent: {intent_result.suggested_agents}")

            # 2. Query Decomposition
            self.logger.info("\n[Step 2] Query Decomposition...")
            decomposed = await self.query_decomposer.decompose(
                query=query,
                intent_result={
                    "intent": intent_result.intent_type.value,
                    "confidence": intent_result.confidence,
                    "keywords": intent_result.keywords,
                    "is_compound": len(intent_result.suggested_agents) > 1
                }
            )

            result["decomposition"] = {
                "is_compound": decomposed.is_compound,
                "num_tasks": len(decomposed.sub_tasks),
                "execution_mode": decomposed.execution_mode.value,
                "parallel_groups": decomposed.parallel_groups,
                "tasks": [
                    {
                        "id": task.task_id,
                        "description": task.description,
                        "type": task.task_type.value,
                        "agent_team": task.agent_team,
                        "priority": task.priority,
                        "dependencies": task.dependencies,
                        "estimated_time": task.estimated_time
                    }
                    for task in decomposed.sub_tasks
                ],
                "total_estimated_time": decomposed.total_estimated_time,
                "confidence": decomposed.confidence,
                "reasoning": decomposed.reasoning
            }

            self.logger.info(f"  복합 질문: {decomposed.is_compound}")
            self.logger.info(f"  작업 수: {len(decomposed.sub_tasks)}")
            self.logger.info(f"  실행 모드: {decomposed.execution_mode.value}")
            for task in decomposed.sub_tasks:
                self.logger.info(f"    - {task.task_id}: {task.description} ({task.agent_team})")

            # 3. Comprehensive Plan 생성
            self.logger.info("\n[Step 3] Comprehensive Plan 생성...")
            plan = await self.planning_agent.create_comprehensive_plan(query)

            result["comprehensive_plan"] = {
                "strategy": plan.strategy.value,
                "num_steps": len(plan.steps),
                "steps": [
                    {
                        "agent": step.agent_name,
                        "priority": step.priority,
                        "dependencies": step.dependencies,
                        "timeout": step.timeout
                    }
                    for step in plan.steps
                ],
                "estimated_time": plan.estimated_time,
                "parallel_groups": plan.parallel_groups,
                "metadata": plan.metadata
            }

            self.logger.info(f"  전략: {plan.strategy.value}")
            self.logger.info(f"  단계 수: {len(plan.steps)}")

            # 실행 시간 계산
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            result["execution_time"] = execution_time

            # 검증
            result["validation"] = self._validate_dual_result(result, test_case)

            result["status"] = "success"
            self.logger.info(f"\n✓ 테스트 성공 (소요시간: {execution_time:.2f}초)")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            self.logger.error(f"\n✗ 테스트 실패: {e}")
            self.logger.error(traceback.format_exc())

        return result

    def _validate_single_result(self, result: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """단일 질문 결과 검증"""
        validation = {
            "intent_match": False,
            "agent_match": False,
            "decomposition_correct": False,
            "overall": False
        }

        # Intent 매칭
        if result["intent_analysis"]["intent_type"] == test_case["expected_intent"]:
            validation["intent_match"] = True

        # Agent 매칭
        suggested_agents = result["intent_analysis"]["suggested_agents"]
        if test_case["expected_agent"] in suggested_agents:
            validation["agent_match"] = True

        # Decomposition 검증 (단일 질문은 분해되지 않아야 함)
        if not result["decomposition"]["is_compound"] and result["decomposition"]["num_tasks"] == 1:
            validation["decomposition_correct"] = True

        # 전체 검증
        validation["overall"] = all([
            validation["intent_match"],
            validation["agent_match"],
            validation["decomposition_correct"]
        ])

        return validation

    def _validate_dual_result(self, result: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """복합 질문 결과 검증"""
        validation = {
            "intent_match": False,
            "decomposition_match": False,
            "task_count_match": False,
            "agents_match": False,
            "overall": False
        }

        # Intent 매칭
        if result["intent_analysis"]["intent_type"] == test_case["expected_intent"]:
            validation["intent_match"] = True

        # Decomposition 여부 매칭
        if result["decomposition"]["is_compound"] == test_case["expected_decomposition"]:
            validation["decomposition_match"] = True

        # Task 수 매칭
        if result["decomposition"]["num_tasks"] >= test_case["expected_tasks"]:
            validation["task_count_match"] = True

        # Agent 매칭
        decomposed_agents = [task["agent_team"] for task in result["decomposition"]["tasks"]]
        expected_agents = set(test_case["expected_agents"])
        actual_agents = set(decomposed_agents)

        if expected_agents.issubset(actual_agents):
            validation["agents_match"] = True

        # 전체 검증
        validation["overall"] = all([
            validation["intent_match"],
            validation["decomposition_match"],
            validation["task_count_match"]
        ])

        return validation

    async def run_tests(self):
        """전체 테스트 실행"""
        self.logger.info("\n\n" + "="*80)
        self.logger.info("Phase 1 테스트 시작")
        self.logger.info("="*80 + "\n")

        # 테스트 데이터 로드
        test_data = self.load_test_data()

        # 1. 단일 질문 테스트
        self.logger.info("\n" + "="*80)
        self.logger.info("PART 1: 단일 질문 테스트 (20개)")
        self.logger.info("="*80)

        single_results = []
        for idx, test_case in enumerate(test_data['single_task_queries'], 1):
            result = await self.test_single_query(test_case, idx)
            single_results.append(result)
            self.test_results.append(result)

            # 중간 저장
            if idx % 5 == 0:
                self.save_results()

        # 2. 복합 질문 테스트
        self.logger.info("\n\n" + "="*80)
        self.logger.info("PART 2: 복합 질문 테스트 (20개)")
        self.logger.info("="*80)

        dual_results = []
        for idx, test_case in enumerate(test_data['dual_task_queries'], 21):
            result = await self.test_dual_query(test_case, idx)
            dual_results.append(result)
            self.test_results.append(result)

            # 중간 저장
            if (idx - 20) % 5 == 0:
                self.save_results()

        # 최종 저장
        self.save_results()

        # 결과 요약
        self.print_summary(single_results, dual_results)

    def save_results(self):
        """결과 저장"""
        output = {
            "test_metadata": {
                "phase": "Phase 1 - Query Decomposition Test",
                "date": datetime.now().isoformat(),
                "total_tests": len(self.test_results)
            },
            "results": self.test_results
        }

        with open(self.results_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        self.logger.info(f"\n결과 저장: {self.results_path}")

    def print_summary(self, single_results: List[Dict], dual_results: List[Dict]):
        """결과 요약 출력"""
        self.logger.info("\n\n" + "="*80)
        self.logger.info("테스트 결과 요약")
        self.logger.info("="*80)

        # 단일 질문 요약
        self.logger.info("\n[단일 질문 테스트]")
        single_success = sum(1 for r in single_results if r.get("status") == "success")
        single_valid = sum(1 for r in single_results if r.get("validation", {}).get("overall", False))

        self.logger.info(f"  성공: {single_success}/{len(single_results)}")
        self.logger.info(f"  검증 통과: {single_valid}/{len(single_results)}")

        # 복합 질문 요약
        self.logger.info("\n[복합 질문 테스트]")
        dual_success = sum(1 for r in dual_results if r.get("status") == "success")
        dual_valid = sum(1 for r in dual_results if r.get("validation", {}).get("overall", False))

        self.logger.info(f"  성공: {dual_success}/{len(dual_results)}")
        self.logger.info(f"  검증 통과: {dual_valid}/{len(dual_results)}")

        # 평균 실행 시간
        all_times = [r.get("execution_time", 0) for r in self.test_results if "execution_time" in r]
        if all_times:
            avg_time = sum(all_times) / len(all_times)
            self.logger.info(f"\n평균 실행 시간: {avg_time:.2f}초")

        self.logger.info(f"\n결과 파일: {self.results_path}")
        self.logger.info(f"로그 파일: {self.log_path}")
        self.logger.info("\n" + "="*80)


async def main():
    """메인 함수"""
    runner = Phase1TestRunner()

    try:
        await runner.initialize()
        await runner.run_tests()

        print("\n테스트 완료!")
        print(f"결과: {runner.results_path}")
        print(f"로그: {runner.log_path}")

    except Exception as e:
        print(f"\n테스트 실행 중 오류: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())