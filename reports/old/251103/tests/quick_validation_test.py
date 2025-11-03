#!/usr/bin/env python
"""Quick validation test - 3 queries to verify fixes"""

import asyncio
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
backend_dir = project_root
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
print(f"Backend dir: {backend_dir}")
print(f"sys.path[0]: {sys.path[0]}\n")

from app.service_agent.llm_manager.llm_service import LLMService
from app.service_agent.foundation.context import create_default_llm_context
from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.cognitive_agents.query_decomposer import QueryDecomposer


async def main():
    print("="*80)
    print("Quick Validation Test - Verifying Phase 1 Fixes")
    print("="*80)

    # Initialize
    llm_context = create_default_llm_context()
    planning_agent = PlanningAgent(llm_context)
    llm_service = LLMService(llm_context=llm_context)
    decomposer = QueryDecomposer(llm_service)

    test_queries = [
        "전세금 5% 인상 제한이 법적으로 가능한가요?",  # Single - Legal
        "강남구 아파트 시세 확인하고 대출 가능 금액 계산해줘",  # Dual - Market + Loan
        "이 계약서 검토하고 위험 요소 분석해줘"  # Dual - Review + Risk
    ]

    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}] Query: {query}")
        print("-" * 80)

        try:
            # Intent analysis
            intent = await planning_agent.analyze_intent(query)
            print(f"[OK] Intent: {intent.intent_type.value} (confidence: {intent.confidence:.2f})")
            print(f"  Suggested agents: {intent.suggested_agents}")

            # Query decomposition
            decomposed = await decomposer.decompose(
                query=query,
                intent_result={
                    "intent": intent.intent_type.value,
                    "confidence": intent.confidence,
                    "keywords": intent.keywords
                }
            )
            print(f"[OK] Decomposition: is_compound={decomposed.is_compound}, tasks={len(decomposed.sub_tasks)}")

            # Execution plan
            plan = await planning_agent.create_execution_plan(intent)
            print(f"[OK] Plan: strategy={plan.strategy.value}, steps={len(plan.steps)}")

            results.append({"success": True, "query": query})
            print("[PASSED] Test succeeded")

        except Exception as e:
            print(f"[FAILED] Test error: {e}")
            results.append({"success": False, "query": query, "error": str(e)})

    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    passed = sum(1 for r in results if r["success"])
    print(f"Total: {len(results)}")
    print(f"Passed: {passed}/{len(results)} ({100*passed/len(results):.0f}%)")

    if passed == len(results):
        print("\n[SUCCESS] All fixes verified successfully!")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
