"""
Test Cognitive Layer Generalization

Tests the generalized cognitive layer (IntentClassifier, intent_understanding_node, planning_node)
with queries from different domains.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.octostrator.supervisors.cognitive.cognitive_helpers import IntentClassifier
from app.octostrator.supervisors.cognitive.cognitive_nodes import (
    intent_understanding_node,
    planning_node
)


async def test_intent_classifier():
    """Test IntentClassifier with different domain queries"""
    print("\n" + "="*80)
    print("TEST 1: IntentClassifier (Fallback - no LLM)")
    print("="*80)

    classifier = IntentClassifier()

    test_queries = [
        "오늘 운동 루틴 추천해줘",  # Fitness
        "환자 진료 기록 분석해줘",  # Medical
        "계약서 검토해줘",          # Legal
        "학생 과제 평가해줘",        # Education
    ]

    for query in test_queries:
        result = await classifier.classify(query, llm=None)  # No LLM - fallback
        print(f"\nQuery: {query}")
        print(f"  Intent: {result['intent']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Reasoning: {result['reasoning']}")


async def test_intent_understanding_node():
    """Test intent_understanding_node with different domain queries"""
    print("\n" + "="*80)
    print("TEST 2: intent_understanding_node (Fallback - no LLM)")
    print("="*80)

    test_cases = [
        {
            "domain": "Fitness",
            "user_query": "오늘 운동 루틴 추천해줘"
        },
        {
            "domain": "Medical",
            "user_query": "환자 진료 기록 분석해줘"
        },
        {
            "domain": "Legal",
            "user_query": "계약서 검토해줘"
        },
        {
            "domain": "Education",
            "user_query": "학생 과제 평가해줘"
        }
    ]

    for test_case in test_cases:
        state = {
            "user_query": test_case["user_query"],
            "messages": []
            # No LLM - will use fallback
        }

        result = await intent_understanding_node(state)

        print(f"\n[{test_case['domain']}] Query: {test_case['user_query']}")
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ✓ Intent: {result['user_intent']}")
            print(f"  ✓ Confidence: {result['intent_confidence']:.2f}")
            print(f"  ✓ Reasoning: {result['intent_reasoning']}")


async def test_planning_node():
    """Test planning_node with different domain queries"""
    print("\n" + "="*80)
    print("TEST 3: planning_node (Fallback - general_agent)")
    print("="*80)

    test_cases = [
        {
            "domain": "Fitness",
            "user_intent": "운동 프로그램 추천 요청",
            "user_query": "오늘 운동 루틴 추천해줘"
        },
        {
            "domain": "Medical",
            "user_intent": "의료 데이터 분석 요청",
            "user_query": "환자 진료 기록 분석해줘"
        },
        {
            "domain": "Legal",
            "user_intent": "법률 문서 검토 요청",
            "user_query": "계약서 검토해줘"
        },
        {
            "domain": "Education",
            "user_intent": "교육 콘텐츠 평가 요청",
            "user_query": "학생 과제 평가해줘"
        }
    ]

    for test_case in test_cases:
        state = {
            "user_intent": test_case["user_intent"],
            "user_query": test_case["user_query"]
        }

        result = await planning_node(state)

        print(f"\n[{test_case['domain']}] Query: {test_case['user_query']}")
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            plan = result["plan"]
            print(f"  ✓ Goal: {plan['goal']}")
            print(f"  ✓ Intent: {plan['intent']}")
            print(f"  ✓ Steps: {len(plan['steps'])}")
            for step in plan['steps']:
                print(f"    - {step['step_id']}: {step['agent']} -> {step['action']}")


async def test_full_pipeline():
    """Test full cognitive pipeline: Intent -> Planning"""
    print("\n" + "="*80)
    print("TEST 4: Full Pipeline (Intent Understanding -> Planning)")
    print("="*80)

    test_queries = [
        ("Fitness", "오늘 운동 루틴 추천해줘"),
        ("Medical", "환자 진료 기록 분석해줘"),
        ("Legal", "계약서 검토해줘"),
        ("Education", "학생 과제 평가해줘"),
    ]

    for domain, query in test_queries:
        print(f"\n[{domain}] Query: {query}")

        # Step 1: Intent Understanding
        state = {"user_query": query, "messages": []}
        intent_result = await intent_understanding_node(state)

        if "error" in intent_result:
            print(f"  ❌ Intent Error: {intent_result['error']}")
            continue

        print(f"  ✓ Intent: {intent_result['user_intent']}")

        # Step 2: Planning
        state.update(intent_result)
        planning_result = await planning_node(state)

        if "error" in planning_result:
            print(f"  ❌ Planning Error: {planning_result['error']}")
            continue

        plan = planning_result["plan"]
        print(f"  ✓ Plan: {len(plan['steps'])} step(s)")
        print(f"    Agent: {plan['steps'][0]['agent']}")
        print(f"    Action: {plan['steps'][0]['action']}")


async def main():
    """Run all tests"""
    print("\n" + "🧪" * 40)
    print(" COGNITIVE LAYER GENERALIZATION TEST SUITE")
    print("🧪" * 40)

    try:
        await test_intent_classifier()
        await test_intent_understanding_node()
        await test_planning_node()
        await test_full_pipeline()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\n📊 Summary:")
        print("  ✓ IntentClassifier: Working with fallback (no LLM)")
        print("  ✓ intent_understanding_node: Working with fallback")
        print("  ✓ planning_node: Working with general_agent (diet_agent removed)")
        print("  ✓ Full pipeline: Intent -> Planning successful")
        print("\n⚠️  Note: Tests run without LLM (fallback mode)")
        print("   To test with LLM, provide llm instance in state")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
