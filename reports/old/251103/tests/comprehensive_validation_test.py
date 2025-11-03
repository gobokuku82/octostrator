"""
종합 검증 테스트 - Analysis Team 실행 검증
핵심 문제가 해결되었는지 철저히 검증
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
import json
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.foundation.context import create_default_llm_context
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveValidationTest:
    """종합 검증 테스트 클래스"""

    def __init__(self):
        self.llm_context = create_default_llm_context()
        self.planning_agent = PlanningAgent(llm_context=self.llm_context)
        self.results = []

    # ===== 테스트 케이스 정의 =====

    CRITICAL_TEST_CASES = [
        {
            "id": "CRITICAL-001",
            "category": "COMPREHENSIVE Intent",
            "query": "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 해결방법 알려줘",
            "expected_intent": "COMPREHENSIVE",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "구체적 상황(3억→10억) + 해결방법 요청 = 분석 필수"
        },
        {
            "id": "CRITICAL-002",
            "category": "COMPREHENSIVE Intent",
            "query": "10년 살았는데 갑자기 전세금 7억 올려달래요. 어떻게 대응해야 해?",
            "expected_intent": "COMPREHENSIVE",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "상황 설명 + '어떻게 대응' = 해결책 필요"
        },
        {
            "id": "CRITICAL-003",
            "category": "LEGAL_CONSULT with Solution Request",
            "query": "보증금 반환 거절 당했어. 법적으로 어떻게 해야 해?",
            "expected_intent": "LEGAL_CONSULT",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "'어떻게 해야' = 단순 법률 조회 이상의 분석 필요"
        },
        {
            "id": "CRITICAL-004",
            "category": "LOAN_CONSULT",
            "query": "연봉 5000만원인데 LTV, DTI 한도 계산해줘",
            "expected_intent": "LOAN_CONSULT",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "계산 요청 = analysis_team 필수"
        },
        {
            "id": "CRITICAL-005",
            "category": "LOAN_CONSULT",
            "query": "전세자금대출 한도가 얼마나 되나요?",
            "expected_intent": "LOAN_CONSULT",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "대출 한도 = 계산 및 분석 필요"
        }
    ]

    NORMAL_TEST_CASES = [
        {
            "id": "NORMAL-001",
            "category": "Simple LEGAL_CONSULT",
            "query": "전세금 5% 인상 한도가 얼마야?",
            "expected_intent": "LEGAL_CONSULT",
            "expected_agents": ["search_team"],
            "must_include_analysis": False,
            "reason": "단순 사실 확인 = search만 필요"
        },
        {
            "id": "NORMAL-002",
            "category": "Simple MARKET_INQUIRY",
            "query": "강남구 아파트 전세 시세 알려줘",
            "expected_intent": "MARKET_INQUIRY",
            "expected_agents": ["search_team"],
            "must_include_analysis": False,
            "reason": "단순 시세 조회 = search만 필요"
        },
        {
            "id": "NORMAL-003",
            "category": "CONTRACT_CREATION",
            "query": "임대차계약서 작성해주세요",
            "expected_intent": "CONTRACT_CREATION",
            "expected_agents": ["document_team"],
            "must_include_analysis": False,
            "reason": "문서 생성 = document_team만 필요"
        }
    ]

    EDGE_CASES = [
        {
            "id": "EDGE-001",
            "category": "Ambiguous Query",
            "query": "전세금 인상",
            "expected_intent": "LEGAL_CONSULT",  # 또는 UNCLEAR
            "expected_agents": None,  # 어느쪽이든 허용
            "must_include_analysis": False,
            "reason": "모호한 질문 - 유연한 처리 필요"
        },
        {
            "id": "EDGE-002",
            "category": "Multiple Intents",
            "query": "강남 시세 알려주고, 대출 한도도 계산해줘",
            "expected_intent": "COMPREHENSIVE",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "복합 질문 = 분석 필요"
        },
        {
            "id": "EDGE-003",
            "category": "Emotional Language",
            "query": "집주인이 너무 짜증나요. 전세금 엄청 올리래요. 도와주세요.",
            "expected_intent": "COMPREHENSIVE",
            "expected_agents": ["search_team", "analysis_team"],
            "must_include_analysis": True,
            "reason": "감정적 표현 + 도움 요청 = 해결책 필요"
        }
    ]

    # ===== 테스트 실행 메서드 =====

    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """단일 테스트 케이스 실행"""
        test_id = test_case["id"]
        query = test_case["query"]

        logger.info(f"\n{'='*80}")
        logger.info(f"[{test_id}] Testing: {query}")
        logger.info(f"Category: {test_case['category']}")
        logger.info(f"Expected Intent: {test_case['expected_intent']}")
        logger.info(f"Expected Agents: {test_case['expected_agents']}")
        logger.info(f"Analysis Required: {test_case['must_include_analysis']}")
        logger.info(f"Reason: {test_case['reason']}")
        logger.info('='*80)

        result = {
            "test_id": test_id,
            "query": query,
            "category": test_case["category"],
            "timestamp": datetime.now().isoformat(),
            "passed": False,
            "details": {}
        }

        try:
            # Step 1: Intent 분석
            intent_result = await self.planning_agent.analyze_intent(query)

            result["details"]["intent"] = {
                "detected": intent_result.intent_type.value,
                "expected": test_case["expected_intent"],
                "confidence": intent_result.confidence,
                "keywords": intent_result.keywords
            }

            # Step 2: Agent 선택
            execution_plan = await self.planning_agent.create_execution_plan(intent_result)
            selected_agents = [step.agent_name for step in execution_plan.steps]

            result["details"]["agents"] = {
                "selected": selected_agents,
                "expected": test_case["expected_agents"],
                "strategy": execution_plan.strategy.value
            }

            # Step 3: 검증
            checks = self._validate_result(test_case, intent_result, selected_agents)
            result["checks"] = checks
            result["passed"] = all(check["passed"] for check in checks.values())

            # 결과 출력
            self._print_test_result(result)

        except Exception as e:
            result["error"] = str(e)
            result["passed"] = False
            logger.error(f"❌ Test {test_id} failed with error: {e}")

        return result

    def _validate_result(
        self,
        test_case: Dict,
        intent_result,
        selected_agents: List[str]
    ) -> Dict[str, Dict]:
        """테스트 결과 검증"""
        checks = {}

        # Check 1: Intent 일치
        expected_intent = test_case["expected_intent"]
        actual_intent = intent_result.intent_type.value

        # EDGE 케이스는 여러 intent 허용
        if test_case["id"].startswith("EDGE"):
            intent_match = actual_intent in ["LEGAL_CONSULT", "COMPREHENSIVE", "UNCLEAR"]
        else:
            intent_match = actual_intent == expected_intent

        checks["intent_match"] = {
            "passed": intent_match,
            "expected": expected_intent,
            "actual": actual_intent,
            "critical": True
        }

        # Check 2: Agent 선택 (EDGE 케이스 제외)
        if test_case["expected_agents"] is not None:
            agents_match = set(selected_agents) == set(test_case["expected_agents"])
            checks["agents_match"] = {
                "passed": agents_match,
                "expected": test_case["expected_agents"],
                "actual": selected_agents,
                "critical": True
            }
        else:
            # EDGE 케이스는 agent 선택을 검증하지 않음
            checks["agents_match"] = {
                "passed": True,
                "note": "Edge case - any agent selection allowed"
            }

        # Check 3: Analysis Team 포함 여부 (가장 중요!)
        if test_case["must_include_analysis"]:
            analysis_included = "analysis_team" in selected_agents
            checks["analysis_team_included"] = {
                "passed": analysis_included,
                "expected": True,
                "actual": analysis_included,
                "critical": True,
                "note": "★★★ CRITICAL: analysis_team must be included ★★★"
            }
        else:
            # analysis가 필수가 아닌 경우 - 포함되어도 되고 안되어도 됨
            checks["analysis_team_included"] = {
                "passed": True,
                "note": "Analysis not required for this query"
            }

        # Check 4: Confidence 검증
        checks["confidence"] = {
            "passed": intent_result.confidence >= 0.7,
            "value": intent_result.confidence,
            "threshold": 0.7,
            "critical": False
        }

        return checks

    def _print_test_result(self, result: Dict):
        """테스트 결과 출력"""
        if result["passed"]:
            logger.info("✅ TEST PASSED")
        else:
            logger.error("❌ TEST FAILED")

        logger.info("\n[Intent Analysis]")
        intent = result["details"]["intent"]
        logger.info(f"  Expected: {intent['expected']}")
        logger.info(f"  Detected: {intent['detected']}")
        logger.info(f"  Confidence: {intent['confidence']:.2f}")

        logger.info("\n[Agent Selection]")
        agents = result["details"]["agents"]
        logger.info(f"  Expected: {agents['expected']}")
        logger.info(f"  Selected: {agents['selected']}")
        logger.info(f"  Strategy: {agents['strategy']}")

        logger.info("\n[Validation Checks]")
        for check_name, check in result["checks"].items():
            status = "✅" if check["passed"] else "❌"
            critical = " [CRITICAL]" if check.get("critical", False) else ""
            logger.info(f"  {status} {check_name}{critical}")

            if "note" in check:
                logger.info(f"     Note: {check['note']}")

            if not check["passed"] and "expected" in check:
                logger.info(f"     Expected: {check['expected']}")
                logger.info(f"     Actual: {check['actual']}")

    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info("\n" + "="*80)
        logger.info("종합 검증 테스트 시작")
        logger.info("="*80 + "\n")

        all_tests = [
            ("CRITICAL", self.CRITICAL_TEST_CASES),
            ("NORMAL", self.NORMAL_TEST_CASES),
            ("EDGE", self.EDGE_CASES)
        ]

        total_passed = 0
        total_failed = 0
        critical_failed = []

        for category, test_cases in all_tests:
            logger.info(f"\n{'#'*80}")
            logger.info(f"# {category} TEST CASES ({len(test_cases)} tests)")
            logger.info(f"{'#'*80}\n")

            for test_case in test_cases:
                result = await self.run_single_test(test_case)
                self.results.append(result)

                if result["passed"]:
                    total_passed += 1
                else:
                    total_failed += 1
                    if category == "CRITICAL":
                        critical_failed.append(result)

        # 최종 결과 요약
        self._print_summary(total_passed, total_failed, critical_failed)

        # 결과 저장
        self._save_results()

    def _print_summary(self, total_passed: int, total_failed: int, critical_failed: List):
        """최종 결과 요약 출력"""
        logger.info("\n" + "="*80)
        logger.info("종합 결과 요약")
        logger.info("="*80 + "\n")

        total = total_passed + total_failed
        success_rate = (total_passed / total * 100) if total > 0 else 0

        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {total_passed} ({success_rate:.1f}%)")
        logger.info(f"❌ Failed: {total_failed} ({100-success_rate:.1f}%)")

        if critical_failed:
            logger.error(f"\n⚠️ CRITICAL FAILURES: {len(critical_failed)}")
            logger.error("다음 CRITICAL 테스트가 실패했습니다:")
            for result in critical_failed:
                logger.error(f"  - {result['test_id']}: {result['query']}")

                # 실패한 check 출력
                for check_name, check in result["checks"].items():
                    if not check["passed"] and check.get("critical", False):
                        logger.error(f"    ❌ {check_name}: {check.get('note', '')}")
        else:
            logger.info("\n🎉 모든 CRITICAL 테스트 통과!")

        # 카테고리별 통계
        logger.info("\n[카테고리별 통계]")
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0}

            if result["passed"]:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1

        for cat, stats in categories.items():
            total_cat = stats["passed"] + stats["failed"]
            rate = stats["passed"] / total_cat * 100 if total_cat > 0 else 0
            logger.info(f"  {cat}: {stats['passed']}/{total_cat} ({rate:.1f}%)")

    def _save_results(self):
        """결과 JSON 파일로 저장"""
        output_file = Path(__file__).parent / "comprehensive_validation_results.json"

        output_data = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r["passed"]),
                "failed": sum(1 for r in self.results if not r["passed"])
            },
            "results": self.results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"\n결과 저장 완료: {output_file}")


async def main():
    """메인 실행 함수"""
    tester = ComprehensiveValidationTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
