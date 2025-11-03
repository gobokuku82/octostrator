"""
LLM Service 마이그레이션 최종 검증 테스트
모든 Agent의 LLM 호출을 상세하게 테스트하고 검증
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List

backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent, IntentType, IntentResult, ExecutionPlan
)
from app.service_agent.execution_agents import SearchExecutor, AnalysisExecutor
from app.service_agent.foundation.separated_states import SearchKeywords, AnalysisInsight
from app.service_agent.foundation.context import LLMContext
from app.service_agent.foundation.config import Config


class TestResult:
    """테스트 결과 추적"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def add_pass(self, test_name: str):
        self.total += 1
        self.passed += 1
        print(f"    [PASS] {test_name}")

    def add_fail(self, test_name: str, error: str):
        self.total += 1
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"    [FAIL] {test_name}")
        print(f"           Error: {error}")

    def summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"\nTotal Tests: {self.total}")
        print(f"Passed: {self.passed} ({self.passed/self.total*100:.1f}%)" if self.total > 0 else "Passed: 0")
        print(f"Failed: {self.failed}")

        if self.failed > 0:
            print("\nFailed Tests:")
            for error in self.errors:
                print(f"  - {error}")

        return self.failed == 0


async def test_planning_agent(llm_context: LLMContext, results: TestResult):
    """PlanningAgent 상세 테스트"""
    print("\n" + "="*80)
    print("TEST SUITE 1: PlanningAgent")
    print("="*80)

    planner = PlanningAgent(llm_context=llm_context)

    # Test 1-1: LLMService 초기화 확인
    try:
        assert planner.llm_service is not None, "LLMService not initialized"
        results.add_pass("PlanningAgent initialization")
    except AssertionError as e:
        results.add_fail("PlanningAgent initialization", str(e))
        return

    # Test 1-2: Intent Analysis - 시세조회
    try:
        intent: IntentResult = await planner.analyze_intent("강남구 아파트 전세 시세")

        assert isinstance(intent, IntentResult), f"Expected IntentResult, got {type(intent)}"
        assert isinstance(intent.intent_type, IntentType), "Intent type is not IntentType enum"
        assert intent.intent_type == IntentType.MARKET_INQUIRY, f"Expected MARKET_INQUIRY, got {intent.intent_type}"
        assert 0 <= intent.confidence <= 1.0, f"Confidence out of range: {intent.confidence}"
        assert isinstance(intent.keywords, list), "Keywords is not a list"
        assert not intent.fallback, "Should not use fallback with LLM"

        results.add_pass(f"Intent Analysis - Market (confidence: {intent.confidence:.2f})")
    except Exception as e:
        results.add_fail("Intent Analysis - Market", str(e))

    # Test 1-3: Intent Analysis - 법률상담
    try:
        intent: IntentResult = await planner.analyze_intent("전세금 5% 인상이 가능한가요?")

        assert isinstance(intent, IntentResult), f"Expected IntentResult, got {type(intent)}"
        assert intent.intent_type == IntentType.LEGAL_CONSULT, f"Expected LEGAL_CONSULT, got {intent.intent_type}"
        assert 0 <= intent.confidence <= 1.0, f"Confidence out of range: {intent.confidence}"
        assert not intent.fallback, "Should not use fallback with LLM"

        results.add_pass(f"Intent Analysis - Legal (confidence: {intent.confidence:.2f})")
    except Exception as e:
        results.add_fail("Intent Analysis - Legal", str(e))

    # Test 1-4: Intent Analysis - 대출상담
    try:
        intent: IntentResult = await planner.analyze_intent("전세자금대출 한도가 궁금해요")

        assert isinstance(intent, IntentResult), f"Expected IntentResult, got {type(intent)}"
        assert intent.intent_type == IntentType.LOAN_CONSULT, f"Expected LOAN_CONSULT, got {intent.intent_type}"
        assert 0 <= intent.confidence <= 1.0, f"Confidence out of range: {intent.confidence}"

        results.add_pass(f"Intent Analysis - Loan (confidence: {intent.confidence:.2f})")
    except Exception as e:
        results.add_fail("Intent Analysis - Loan", str(e))

    # Test 1-5: Execution Plan 생성
    try:
        intent = await planner.analyze_intent("강남구 아파트 시세 분석해주세요")
        plan: ExecutionPlan = await planner.create_execution_plan(intent)

        assert isinstance(plan, ExecutionPlan), f"Expected ExecutionPlan, got {type(plan)}"
        assert len(plan.steps) > 0, "No execution steps generated"
        assert plan.intent == intent, "Plan intent mismatch"

        results.add_pass(f"Execution Plan Generation ({len(plan.steps)} steps)")
    except Exception as e:
        results.add_fail("Execution Plan Generation", str(e))


async def test_search_executor(llm_context: LLMContext, results: TestResult):
    """SearchExecutor 상세 테스트"""
    print("\n" + "="*80)
    print("TEST SUITE 2: SearchExecutor")
    print("="*80)

    search_executor = SearchExecutor(llm_context=llm_context)

    # Test 2-1: LLMService 초기화 확인
    try:
        assert search_executor.llm_service is not None, "LLMService not initialized"
        results.add_pass("SearchExecutor initialization")
    except AssertionError as e:
        results.add_fail("SearchExecutor initialization", str(e))
        return

    # Test 2-2: Keyword Extraction - 법률
    try:
        keywords = search_executor._extract_keywords("전세금 5% 인상 가능한가요?")

        # SearchKeywords는 TypedDict이므로 dict로 체크
        assert isinstance(keywords, dict) or hasattr(keywords, 'legal'), f"Unexpected type: {type(keywords)}"

        # 속성 접근 확인
        legal = keywords.legal if hasattr(keywords, 'legal') else keywords.get('legal', [])
        assert isinstance(legal, list), f"legal is not a list: {type(legal)}"
        assert len(legal) > 0, "No legal keywords extracted"

        results.add_pass(f"Keyword Extraction - Legal ({len(legal)} legal keywords)")
    except Exception as e:
        results.add_fail("Keyword Extraction - Legal", str(e))

    # Test 2-3: Keyword Extraction - 부동산
    try:
        keywords = search_executor._extract_keywords("강남구 아파트 전세 시세")

        real_estate = keywords.real_estate if hasattr(keywords, 'real_estate') else keywords.get('real_estate', [])
        assert isinstance(real_estate, list), f"real_estate is not a list: {type(real_estate)}"
        assert len(real_estate) > 0, "No real_estate keywords extracted"

        results.add_pass(f"Keyword Extraction - Real Estate ({len(real_estate)} keywords)")
    except Exception as e:
        results.add_fail("Keyword Extraction - Real Estate", str(e))

    # Test 2-4: Keyword Extraction - 대출
    try:
        keywords = search_executor._extract_keywords("전세자금대출 금리와 한도")

        loan = keywords.loan if hasattr(keywords, 'loan') else keywords.get('loan', [])
        assert isinstance(loan, list), f"loan is not a list: {type(loan)}"
        assert len(loan) > 0, "No loan keywords extracted"

        results.add_pass(f"Keyword Extraction - Loan ({len(loan)} loan keywords)")
    except Exception as e:
        results.add_fail("Keyword Extraction - Loan", str(e))


async def test_analysis_executor(llm_context: LLMContext, results: TestResult):
    """AnalysisExecutor 상세 테스트"""
    print("\n" + "="*80)
    print("TEST SUITE 3: AnalysisExecutor")
    print("="*80)

    analysis_executor = AnalysisExecutor(llm_context=llm_context)

    # Test 3-1: LLMService 초기화 확인
    try:
        assert analysis_executor.llm_service is not None, "LLMService not initialized"
        results.add_pass("AnalysisExecutor initialization")
    except AssertionError as e:
        results.add_fail("AnalysisExecutor initialization", str(e))
        return

    # Test 3-2: Insight Generation - Market Analysis
    try:
        test_state = {
            "raw_analysis": {
                "market_trends": ["전세가 상승 추세", "매물 감소", "거래량 증가"],
                "price_data": ["평균 전세가 5억원", "전월 대비 3% 상승"],
                "regional_info": ["강남구 인기 지역", "교통 편리"]
            },
            "analysis_type": "market",
            "shared_context": {"query": "강남구 전세 시장 분석"}
        }

        insights = await analysis_executor._generate_insights_with_llm(test_state)

        assert isinstance(insights, list), f"Expected list, got {type(insights)}"
        assert len(insights) > 0, "No insights generated"

        # AnalysisInsight는 TypedDict이므로 dict나 객체 모두 지원
        for idx, insight in enumerate(insights):
            # 속성 확인 (dict 또는 객체)
            if isinstance(insight, dict):
                assert 'insight_type' in insight, f"Insight {idx} missing 'insight_type'"
                assert 'description' in insight, f"Insight {idx} missing 'description'"
                assert 'confidence' in insight, f"Insight {idx} missing 'confidence'"
                confidence = insight['confidence']
            else:
                assert hasattr(insight, 'insight_type'), f"Insight {idx} missing 'insight_type'"
                assert hasattr(insight, 'description'), f"Insight {idx} missing 'description'"
                assert hasattr(insight, 'confidence'), f"Insight {idx} missing 'confidence'"
                confidence = insight.confidence

            assert 0 <= confidence <= 1.0, f"Insight {idx} confidence out of range: {confidence}"

        # 평균 confidence 계산
        confidences = [i['confidence'] if isinstance(i, dict) else i.confidence for i in insights]
        avg_confidence = sum(confidences) / len(confidences)

        results.add_pass(f"Insight Generation - Market ({len(insights)} insights, avg confidence: {avg_confidence:.2f})")
    except Exception as e:
        results.add_fail("Insight Generation - Market", str(e))

    # Test 3-3: Insight Generation - Risk Analysis
    try:
        test_state = {
            "raw_analysis": {
                "risk_factors": ["금리 상승 가능성", "공급 과잉 우려"],
                "market_conditions": ["불확실성 증가"],
                "legal_issues": ["계약 조건 확인 필요"]
            },
            "analysis_type": "risk",
            "shared_context": {"query": "전세 계약 리스크 분석"}
        }

        insights: List[AnalysisInsight] = await analysis_executor._generate_insights_with_llm(test_state)

        assert isinstance(insights, list), f"Expected list, got {type(insights)}"
        assert len(insights) > 0, "No insights generated"

        results.add_pass(f"Insight Generation - Risk ({len(insights)} insights)")
    except Exception as e:
        results.add_fail("Insight Generation - Risk", str(e))


async def test_prompt_templates(results: TestResult):
    """프롬프트 템플릿 검증"""
    print("\n" + "="*80)
    print("TEST SUITE 4: Prompt Templates")
    print("="*80)

    from app.service_agent.llm_manager import PromptManager

    pm = PromptManager()

    # Test 4-1: Prompt 파일 존재 확인
    expected_prompts = {
        "cognitive": ["intent_analysis", "plan_generation"],
        "execution": ["keyword_extraction", "insight_generation", "response_synthesis"],
        "common": ["error_response"]
    }

    for category, prompt_names in expected_prompts.items():
        for prompt_name in prompt_names:
            try:
                # 각 프롬프트에 맞는 변수 제공
                test_vars = {
                    "query": "test query",
                    "analysis_type": "test",
                    "raw_analysis": "{}",
                    "intent_result": "{}",
                    "analysis_result": "{}",
                    "error_type": "test_error",
                    "error_message": "test message"
                }
                prompt = pm.get(prompt_name, test_vars)
                assert len(prompt) > 0, f"Empty prompt for {prompt_name}"
                assert "JSON" in prompt or "json" in prompt, f"Prompt {prompt_name} missing JSON keyword (required for json_mode)"
                results.add_pass(f"Prompt Template - {category}/{prompt_name}")
            except Exception as e:
                results.add_fail(f"Prompt Template - {category}/{prompt_name}", str(e))

    # Test 4-2: Prompt 목록 확인
    try:
        available_prompts = pm.list_prompts()
        total_prompts = sum(len(prompts) for prompts in available_prompts.values())
        assert total_prompts >= 6, f"Expected at least 6 prompts, found {total_prompts}"
        results.add_pass(f"Prompt Manager - List ({total_prompts} total prompts)")
    except Exception as e:
        results.add_fail("Prompt Manager - List", str(e))


async def test_model_configuration(results: TestResult):
    """모델 설정 검증"""
    print("\n" + "="*80)
    print("TEST SUITE 5: Model Configuration")
    print("="*80)

    # Test 5-1: 모델 매핑 확인
    expected_models = {
        "intent_analysis": "gpt-4o-mini",
        "plan_generation": "gpt-4o-mini",
        "keyword_extraction": "gpt-4o-mini",
        "insight_generation": "gpt-4o",
        "response_synthesis": "gpt-4o-mini",
        "error_response": "gpt-4o-mini"
    }

    for prompt_name, expected_model in expected_models.items():
        try:
            actual_model = Config.LLM_DEFAULTS["models"].get(prompt_name)
            assert actual_model == expected_model, f"Expected {expected_model}, got {actual_model}"
            results.add_pass(f"Model Config - {prompt_name} -> {actual_model}")
        except AssertionError as e:
            results.add_fail(f"Model Config - {prompt_name}", str(e))

    # Test 5-2: 기본 파라미터 확인
    try:
        defaults = Config.LLM_DEFAULTS["default_params"]
        assert "temperature" in defaults, "Missing temperature"
        assert "max_tokens" in defaults, "Missing max_tokens"
        assert "response_format" in defaults, "Missing response_format"
        results.add_pass(f"Default Parameters (temp={defaults['temperature']}, max_tokens={defaults['max_tokens']})")
    except AssertionError as e:
        results.add_fail("Default Parameters", str(e))


async def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("LLM SERVICE MIGRATION - COMPREHENSIVE VALIDATION")
    print("="*80)

    # API 키 확인
    api_key = Config.LLM_DEFAULTS.get("api_key")
    if not api_key:
        print("\n[ERROR] No OpenAI API key found")
        print("        Set OPENAI_API_KEY in .env")
        return False

    print(f"\n[INFO] API Key: {api_key[:10]}...")
    print(f"[INFO] Starting comprehensive tests...\n")

    llm_context = LLMContext(
        api_key=api_key,
        temperature=0.3,
        max_tokens=2000
    )

    results = TestResult()

    # 테스트 실행
    await test_planning_agent(llm_context, results)
    await test_search_executor(llm_context, results)
    await test_analysis_executor(llm_context, results)
    await test_prompt_templates(results)
    await test_model_configuration(results)

    # 결과 요약
    success = results.summary()

    if success:
        print("\n" + "="*80)
        print("[SUCCESS] ALL TESTS PASSED!")
        print("="*80)
        print("\n[VERIFIED]")
        print("  - All agents successfully migrated to LLMService")
        print("  - All LLM calls working correctly")
        print("  - All prompt templates loaded and validated")
        print("  - All model configurations verified")
        print("\n[READY] System is ready for production use")
    else:
        print("\n" + "="*80)
        print("[WARNING] SOME TESTS FAILED")
        print("="*80)
        print("\nPlease review failed tests above")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
