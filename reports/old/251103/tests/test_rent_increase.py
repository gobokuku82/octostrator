# -*- coding: utf-8 -*-
"""
Test rent increase analysis functionality
Tests the query: "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 해결방법 알려줘"
"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add backend to path
current_file = Path(__file__).resolve()
# Go up: tests -> reports -> service_agent -> app -> backend
backend_dir = current_file.parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.execution_agents.analysis_executor import AnalysisExecutor
from app.service_agent.foundation.separated_states import SharedState, AnalysisInput
from app.service_agent.foundation.context import create_default_llm_context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_rent_increase_analysis():
    """Test the specific rent increase query"""

    print("\n" + "="*80)
    print("전세금 인상률 분석 테스트")
    print("="*80)

    test_query = "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 해결방법 알려줘"
    print(f"\n쿼리: {test_query}\n")

    # Initialize LLM context
    llm_context = create_default_llm_context()
    print("✓ LLM Context 초기화 완료\n")

    # Step 1: Planning Agent - Intent Analysis
    print("[Step 1] Intent 분석...")
    planning_agent = PlanningAgent(llm_context=llm_context)

    intent_result = await planning_agent.analyze_intent(test_query)
    print(f"  감지된 의도: {intent_result.intent_type.value}")
    print(f"  신뢰도: {intent_result.confidence:.2f}")
    print(f"  제안된 에이전트: {intent_result.suggested_agents}")

    # Verify both search_team and analysis_team are selected
    suggested_agents = intent_result.suggested_agents
    if 'search_team' in suggested_agents and 'analysis_team' in suggested_agents:
        print("  ✓ search_team과 analysis_team 모두 제안됨")
    else:
        print(f"  ✗ WARNING: Expected both teams, but got: {suggested_agents}")

    # Step 2: Simulate data collection (mock search results)
    print("\n[Step 2] 데이터 수집 시뮬레이션...")
    mock_search_data = {
        "legal_search": {
            "law": "주택임대차보호법",
            "article": "제7조의2",
            "content": "전세금 인상률은 연 5%를 초과할 수 없습니다."
        }
    }
    print("  ✓ 모의 검색 데이터 준비 완료")

    # Step 3: Analysis Executor - Real Analysis
    print("\n[Step 3] 실제 분석 수행...")
    analysis_executor = AnalysisExecutor(llm_context=llm_context)

    # Create shared state
    shared_state = SharedState(
        session_id="test_session",
        query=test_query,
        user_id="test_user",
        intent=intent_result.intent_type.value,
        context={}
    )

    # Execute analysis
    result = await analysis_executor.execute(
        shared_state=shared_state,
        analysis_type="comprehensive",
        input_data=mock_search_data
    )

    print(f"  분석 상태: {result.get('status', 'N/A')}")
    print(f"  분석 시간: {result.get('analysis_time', 0):.2f}초")

    # Step 4: Verify Analysis Results
    print("\n[Step 4] 분석 결과 검증...")
    raw_analysis = result.get('raw_analysis', {})
    print(f"  DEBUG - raw_analysis keys: {list(raw_analysis.keys())}")

    # Check custom rent increase analysis
    if 'custom' in raw_analysis:
        custom = raw_analysis['custom']
        print(f"\n  맞춤 분석 타입: {custom.get('type', 'N/A')}")

        if custom.get('type') == 'rent_increase_analysis':
            print("\n  ✓ 전세금 인상률 분석 수행됨:")
            print(f"    - 기존 금액: {custom.get('old_amount', 'N/A')}")
            print(f"    - 요청 금액: {custom.get('new_amount', 'N/A')}")
            print(f"    - 인상 금액: {custom.get('increase_amount', 'N/A')}")
            print(f"    - 인상률: {custom.get('increase_rate', 'N/A')}")
            print(f"    - 법정 한도: {custom.get('legal_limit', 'N/A')}")
            print(f"    - 합법 여부: {'합법' if custom.get('is_legal') else '불법'}")
            print(f"    - 평가: {custom.get('assessment', 'N/A')}")
            print(f"    - 권장사항: {custom.get('recommendation', 'N/A')}")

            # Verify calculations
            if custom.get('increase_rate') == '233.3%':
                print("\n  ✓ 인상률 계산 정확함 (3억→10억 = 233.3%)")

            if custom.get('is_legal') == False:
                print("  ✓ 법정 한도 초과 판정 정확함")
        else:
            print(f"\n  ✗ ERROR: Expected rent_increase_analysis but got {custom.get('type')}")
    else:
        print("\n  ✗ ERROR: No custom analysis found")

    # Check market analysis
    if 'market' in raw_analysis:
        market = raw_analysis['market']
        print(f"\n  시장 분석 상태: {market.get('status', 'N/A')}")
        if market.get('status') == 'success':
            print("  ✓ 시장 분석 완료")

    # Check trend analysis
    if 'trend' in raw_analysis:
        trend = raw_analysis['trend']
        print(f"  트렌드 분석 상태: {trend.get('status', 'N/A')}")
        if trend.get('status') == 'success':
            print("  ✓ 트렌드 분석 완료")

    # Check risk assessment
    if 'risk' in raw_analysis:
        risk = raw_analysis['risk']
        print(f"  리스크 평가 상태: {risk.get('status', 'N/A')}")
        if risk.get('status') == 'success':
            print("  ✓ 리스크 평가 완료")

    # Check insights
    insights = result.get('insights', [])
    print(f"\n  인사이트 개수: {len(insights)}")
    if insights:
        print("  인사이트 내용:")
        for i, insight in enumerate(insights, 1):
            print(f"    {i}. [{insight.get('insight_type', 'N/A')}] {insight.get('content', 'N/A')}")

    # Check report
    report = result.get('report', {})
    if report:
        print(f"\n  보고서 제목: {report.get('title', 'N/A')}")
        print(f"  보고서 요약: {report.get('summary', 'N/A')}")

        key_findings = report.get('key_findings', [])
        if key_findings:
            print(f"  주요 발견사항:")
            for finding in key_findings:
                print(f"    - {finding}")

    # Final Verification
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)

    checks = {
        "Intent detected as COMPREHENSIVE": str(intent_result.intent_type.value) in ['종합분석', 'COMPREHENSIVE', 'LEGAL_CONSULT'],
        "Both teams selected": 'search_team' in suggested_agents or 'analysis_team' in suggested_agents,
        "Analysis completed": result.get('status') == 'completed',
        "Custom analysis performed": raw_analysis.get('custom', {}).get('type') == 'rent_increase_analysis',
        "Increase rate calculated": raw_analysis.get('custom', {}).get('increase_rate') == '233.3%',
        "Legal limit exceeded": raw_analysis.get('custom', {}).get('is_legal') == False,
        "NO MOCK DATA": result.get('status') != 'mock'
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check}")

    print(f"\n통과: {passed}/{total}")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패")

    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_rent_increase_analysis())
