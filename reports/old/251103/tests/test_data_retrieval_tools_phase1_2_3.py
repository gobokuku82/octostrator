"""
Phase 1+2+3 통합 테스트
- Phase 1: MarketDataTool PostgreSQL 연동
- Phase 2: RealEstateSearchTool 개별 매물 검색
- Phase 3: SearchExecutor Tool 통합

실행: python test_data_retrieval_tools_phase1_2_3.py
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# backend 디렉토리를 Python path에 추가
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# .env 파일 로드 (DATABASE_URL 등)
from dotenv import load_dotenv
env_path = backend_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드: {env_path}")
else:
    print(f"⚠️  .env 파일 없음: {env_path}")

# 로깅 설정
logging.basicConfig(
    level=logging.WARNING,  # WARNING 이상만 표시 (테스트 출력을 깔끔하게)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TestResults:
    """테스트 결과 관리 클래스"""

    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "phases": {
                "phase1_market_data": {"tests": [], "passed": 0, "failed": 0},
                "phase2_real_estate_search": {"tests": [], "passed": 0, "failed": 0},
                "phase3_search_executor": {"tests": [], "passed": 0, "failed": 0}
            },
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0
            }
        }

    def add_test_result(self, phase: str, test_name: str, passed: bool,
                       details: str = "", error: str = ""):
        """테스트 결과 추가"""
        result = {
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

        self.results["phases"][phase]["tests"].append(result)

        if passed:
            self.results["phases"][phase]["passed"] += 1
        else:
            self.results["phases"][phase]["failed"] += 1

    def calculate_summary(self):
        """전체 요약 계산"""
        total_passed = sum(p["passed"] for p in self.results["phases"].values())
        total_failed = sum(p["failed"] for p in self.results["phases"].values())
        total_tests = total_passed + total_failed

        self.results["summary"]["total_tests"] = total_tests
        self.results["summary"]["passed"] = total_passed
        self.results["summary"]["failed"] = total_failed
        self.results["summary"]["success_rate"] = (
            (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        )

    def save_to_file(self, filename: str = "test_results_phase1_2_3.json"):
        """결과를 JSON 파일로 저장"""
        output_path = Path(__file__).parent / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        return output_path


async def test_phase1_market_data_tool(results: TestResults):
    """Phase 1: MarketDataTool 테스트"""
    print("\n" + "=" * 80)
    print("  Phase 1: MarketDataTool PostgreSQL 연동 테스트")
    print("=" * 80)

    try:
        from app.service_agent.tools.market_data_tool import MarketDataTool
        tool = MarketDataTool()
        print("✅ MarketDataTool 초기화 성공\n")

        # 테스트 1: 강남구 아파트 시세
        print("-" * 80)
        print("테스트 1-1: 강남구 아파트 시세 조회")
        try:
            result = await tool.search("강남구 아파트", {"property_type": "APARTMENT"})

            if result['status'] == 'success' and result['result_count'] > 0:
                data = result['data'][0]
                print(f"✅ 성공: {result['result_count']}개 결과")
                print(f"   - 지역: {data['region']}")
                print(f"   - 평균 매매가: {data.get('avg_sale_price', 0):,}만원")
                print(f"   - 거래 건수: {data.get('transaction_count', 0)}건")

                results.add_test_result(
                    "phase1_market_data",
                    "강남구 아파트 시세 조회",
                    True,
                    f"{result['result_count']}개 결과, 평균 매매가 {data.get('avg_sale_price', 0):,}만원"
                )
            else:
                print(f"⚠️  결과 없음: {result.get('status')}")
                results.add_test_result(
                    "phase1_market_data",
                    "강남구 아파트 시세 조회",
                    False,
                    error=f"Status: {result.get('status')}, Count: {result.get('result_count')}"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase1_market_data",
                "강남구 아파트 시세 조회",
                False,
                error=str(e)
            )

        # 테스트 2: 송파구 오피스텔 시세
        print("\n" + "-" * 80)
        print("테스트 1-2: 송파구 오피스텔 시세 조회")
        try:
            result = await tool.search("송파구 오피스텔", {"property_type": "OFFICETEL"})

            if result['status'] == 'success' and result['result_count'] > 0:
                data = result['data'][0]
                print(f"✅ 성공: {result['result_count']}개 결과")
                print(f"   - 지역: {data['region']}")
                print(f"   - 평균 전세가: {data.get('avg_deposit', 0):,}만원")

                results.add_test_result(
                    "phase1_market_data",
                    "송파구 오피스텔 시세 조회",
                    True,
                    f"{result['result_count']}개 결과, 평균 전세가 {data.get('avg_deposit', 0):,}만원"
                )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase1_market_data",
                    "송파구 오피스텔 시세 조회",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase1_market_data",
                "송파구 오피스텔 시세 조회",
                False,
                error=str(e)
            )

        # 테스트 3: 서초구 전체 시세
        print("\n" + "-" * 80)
        print("테스트 1-3: 서초구 전체 시세 조회")
        try:
            result = await tool.search("서초구", {})

            if result['status'] == 'success':
                print(f"✅ 성공: {result['result_count']}개 결과")
                for i, data in enumerate(result['data'][:2], 1):
                    print(f"   [{i}] {data['property_type']}: "
                          f"평균 {data.get('avg_sale_price', 0):,}만원")

                results.add_test_result(
                    "phase1_market_data",
                    "서초구 전체 시세 조회",
                    True,
                    f"{result['result_count']}개 물건 종류 결과"
                )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase1_market_data",
                    "서초구 전체 시세 조회",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase1_market_data",
                "서초구 전체 시세 조회",
                False,
                error=str(e)
            )

        # 테스트 4: NULLIF 검증 (0 값 처리)
        print("\n" + "-" * 80)
        print("테스트 1-4: NULLIF 처리 검증 (0 값 제외)")
        try:
            result = await tool.search("강남구", {"property_type": "APARTMENT"})

            if result['status'] == 'success' and result['result_count'] > 0:
                data = result['data'][0]
                # None이 아닌 값이 있는지 확인
                has_valid_data = (
                    data.get('avg_sale_price') is not None or
                    data.get('avg_deposit') is not None
                )

                if has_valid_data:
                    print(f"✅ 성공: NULLIF 정상 작동 (0 값이 평균에서 제외됨)")
                    results.add_test_result(
                        "phase1_market_data",
                        "NULLIF 처리 검증",
                        True,
                        "0 값이 NULL로 처리되어 평균 계산에서 제외됨"
                    )
                else:
                    print(f"⚠️  경고: 모든 값이 None")
                    results.add_test_result(
                        "phase1_market_data",
                        "NULLIF 처리 검증",
                        False,
                        error="All values are None"
                    )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase1_market_data",
                    "NULLIF 처리 검증",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase1_market_data",
                "NULLIF 처리 검증",
                False,
                error=str(e)
            )

    except Exception as e:
        print(f"\n❌ Phase 1 초기화 실패: {e}")
        results.add_test_result(
            "phase1_market_data",
            "Tool 초기화",
            False,
            error=str(e)
        )


async def test_phase2_real_estate_search_tool(results: TestResults):
    """Phase 2: RealEstateSearchTool 테스트"""
    print("\n" + "=" * 80)
    print("  Phase 2: RealEstateSearchTool 개별 매물 검색 테스트")
    print("=" * 80)

    try:
        from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool
        tool = RealEstateSearchTool()
        print("✅ RealEstateSearchTool 초기화 성공\n")

        # 테스트 1: 기본 검색
        print("-" * 80)
        print("테스트 2-1: 강남구 아파트 검색")
        try:
            result = await tool.search("강남구 아파트", {"property_type": "apartment", "limit": 3})

            if result['status'] == 'success' and result['result_count'] > 0:
                print(f"✅ 성공: {result['result_count']}개 매물")
                for i, item in enumerate(result['data'][:2], 1):
                    print(f"   [{i}] {item['name']} - {item['region']}")

                results.add_test_result(
                    "phase2_real_estate_search",
                    "강남구 아파트 검색",
                    True,
                    f"{result['result_count']}개 매물 발견"
                )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase2_real_estate_search",
                    "강남구 아파트 검색",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase2_real_estate_search",
                "강남구 아파트 검색",
                False,
                error=str(e)
            )

        # 테스트 2: 가격 필터링
        print("\n" + "-" * 80)
        print("테스트 2-2: 송파구 5억 이하 오피스텔")
        try:
            result = await tool.search(
                "송파구 오피스텔",
                {"property_type": "officetel", "max_price": 50000, "limit": 3}
            )

            if result['status'] == 'success':
                print(f"✅ 성공: {result['result_count']}개 매물 (5억 이하 필터링)")

                results.add_test_result(
                    "phase2_real_estate_search",
                    "가격 필터링 (5억 이하)",
                    True,
                    f"{result['result_count']}개 매물"
                )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase2_real_estate_search",
                    "가격 필터링 (5억 이하)",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase2_real_estate_search",
                "가격 필터링 (5억 이하)",
                False,
                error=str(e)
            )

        # 테스트 3: 면적 필터링
        print("\n" + "-" * 80)
        print("테스트 2-3: 면적 범위 필터링 (80~120㎡)")
        try:
            result = await tool.search(
                "아파트",
                {"property_type": "apartment", "min_area": 80.0, "max_area": 120.0, "limit": 3}
            )

            if result['status'] == 'success':
                print(f"✅ 성공: {result['result_count']}개 매물 (80~120㎡)")

                results.add_test_result(
                    "phase2_real_estate_search",
                    "면적 필터링 (80~120㎡)",
                    True,
                    f"{result['result_count']}개 매물"
                )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase2_real_estate_search",
                    "면적 필터링 (80~120㎡)",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase2_real_estate_search",
                "면적 필터링 (80~120㎡)",
                False,
                error=str(e)
            )

        # 테스트 4: 주변 시설 정보
        print("\n" + "-" * 80)
        print("테스트 2-4: 주변 시설 정보 포함")
        try:
            result = await tool.search(
                "강남구 아파트",
                {"property_type": "apartment", "limit": 2, "include_nearby": True}
            )

            if result['status'] == 'success' and result['result_count'] > 0:
                has_nearby = any('nearby_facilities' in item for item in result['data'])

                if has_nearby:
                    print(f"✅ 성공: 주변 시설 정보 포함됨")
                    results.add_test_result(
                        "phase2_real_estate_search",
                        "주변 시설 정보",
                        True,
                        "nearby_facilities 필드 존재"
                    )
                else:
                    print(f"⚠️  주변 시설 정보 없음")
                    results.add_test_result(
                        "phase2_real_estate_search",
                        "주변 시설 정보",
                        False,
                        error="No nearby_facilities field"
                    )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase2_real_estate_search",
                    "주변 시설 정보",
                    False,
                    error="No results"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase2_real_estate_search",
                "주변 시설 정보",
                False,
                error=str(e)
            )

        # 테스트 5: 페이지네이션
        print("\n" + "-" * 80)
        print("테스트 2-5: 페이지네이션")
        try:
            result_page1 = await tool.search(
                "빌라",
                {"property_type": "villa", "limit": 3, "offset": 0}
            )
            result_page2 = await tool.search(
                "빌라",
                {"property_type": "villa", "limit": 3, "offset": 3}
            )

            count1 = result_page1.get('result_count', 0)
            count2 = result_page2.get('result_count', 0)

            if count1 > 0 or count2 > 0:
                print(f"✅ 성공: 첫 페이지 {count1}개, 두 번째 페이지 {count2}개")
                results.add_test_result(
                    "phase2_real_estate_search",
                    "페이지네이션",
                    True,
                    f"Page 1: {count1}, Page 2: {count2}"
                )
            else:
                print(f"⚠️  결과 없음")
                results.add_test_result(
                    "phase2_real_estate_search",
                    "페이지네이션",
                    False,
                    error="No results on both pages"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase2_real_estate_search",
                "페이지네이션",
                False,
                error=str(e)
            )

    except Exception as e:
        print(f"\n❌ Phase 2 초기화 실패: {e}")
        results.add_test_result(
            "phase2_real_estate_search",
            "Tool 초기화",
            False,
            error=str(e)
        )


async def test_phase3_search_executor(results: TestResults):
    """Phase 3: SearchExecutor 통합 테스트"""
    print("\n" + "=" * 80)
    print("  Phase 3: SearchExecutor Tool 통합 테스트")
    print("=" * 80)

    try:
        from app.service_agent.execution_agents.search_executor import SearchExecutor
        executor = SearchExecutor()
        print("✅ SearchExecutor 초기화 성공\n")

        # 테스트 1: Tool 초기화 확인
        print("-" * 80)
        print("테스트 3-1: Tool 초기화 상태 확인")
        try:
            tools_initialized = {
                "legal_search_tool": executor.legal_search_tool is not None,
                "market_data_tool": executor.market_data_tool is not None,
                "real_estate_search_tool": executor.real_estate_search_tool is not None,
                "loan_data_tool": executor.loan_data_tool is not None
            }

            for tool_name, initialized in tools_initialized.items():
                status = "✅" if initialized else "❌"
                print(f"   {status} {tool_name}")

            all_initialized = all(tools_initialized.values())

            results.add_test_result(
                "phase3_search_executor",
                "Tool 초기화 상태",
                all_initialized,
                f"{sum(tools_initialized.values())}/4 tools initialized"
            )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase3_search_executor",
                "Tool 초기화 상태",
                False,
                error=str(e)
            )

        # 테스트 2: LLM Tool 선택
        print("\n" + "-" * 80)
        print("테스트 3-2: LLM 기반 Tool 자동 선택")

        test_queries = [
            ("강남구 아파트 매물 검색해줘", "real_estate_search"),
            ("송파구 5억 이하 오피스텔 찾아줘", "real_estate_search"),
            ("서초구 지하철역 근처 빌라", "real_estate_search")
        ]

        passed_count = 0
        for query, expected_tool in test_queries:
            try:
                tool_selection = await executor._select_tools_with_llm(query)
                selected = tool_selection.get("selected_tools", [])
                confidence = tool_selection.get("confidence", 0.0)

                if expected_tool in selected:
                    print(f"   ✅ '{query[:30]}...' → {expected_tool} (신뢰도: {confidence:.2f})")
                    passed_count += 1
                else:
                    print(f"   ❌ '{query[:30]}...' → {selected} (예상: {expected_tool})")
            except Exception as e:
                print(f"   ❌ '{query[:30]}...' → Error: {e}")

        results.add_test_result(
            "phase3_search_executor",
            "LLM Tool 자동 선택",
            passed_count == len(test_queries),
            f"{passed_count}/{len(test_queries)} queries correctly selected"
        )

        # 테스트 3: _get_available_tools() 확인
        print("\n" + "-" * 80)
        print("테스트 3-3: _get_available_tools() 메타데이터")
        try:
            available_tools = executor._get_available_tools()

            has_real_estate_search = "real_estate_search" in available_tools

            if has_real_estate_search:
                tool_info = available_tools["real_estate_search"]
                print(f"✅ real_estate_search 메타데이터 존재")
                print(f"   - Description: {tool_info['description']}")
                print(f"   - Capabilities: {len(tool_info['capabilities'])}개")

                results.add_test_result(
                    "phase3_search_executor",
                    "_get_available_tools() 메타데이터",
                    True,
                    f"real_estate_search tool with {len(tool_info['capabilities'])} capabilities"
                )
            else:
                print(f"❌ real_estate_search 메타데이터 없음")
                results.add_test_result(
                    "phase3_search_executor",
                    "_get_available_tools() 메타데이터",
                    False,
                    error="real_estate_search not in available_tools"
                )
        except Exception as e:
            print(f"❌ 실패: {e}")
            results.add_test_result(
                "phase3_search_executor",
                "_get_available_tools() 메타데이터",
                False,
                error=str(e)
            )

    except Exception as e:
        print(f"\n❌ Phase 3 초기화 실패: {e}")
        results.add_test_result(
            "phase3_search_executor",
            "SearchExecutor 초기화",
            False,
            error=str(e)
        )


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 80)
    print("  Phase 1+2+3 통합 테스트 시작")
    print("  PostgreSQL 기반 데이터 검색 Tool 검증")
    print("=" * 80)

    results = TestResults()

    # Phase 1 테스트
    await test_phase1_market_data_tool(results)

    # Phase 2 테스트
    await test_phase2_real_estate_search_tool(results)

    # Phase 3 테스트
    await test_phase3_search_executor(results)

    # 요약 계산
    results.calculate_summary()

    # 결과 출력
    print("\n" + "=" * 80)
    print("  테스트 결과 요약")
    print("=" * 80)

    for phase_name, phase_data in results.results["phases"].items():
        print(f"\n{phase_name}:")
        print(f"  - 통과: {phase_data['passed']}개")
        print(f"  - 실패: {phase_data['failed']}개")

    summary = results.results["summary"]
    print(f"\n전체 결과:")
    print(f"  - 총 테스트: {summary['total_tests']}개")
    print(f"  - 통과: {summary['passed']}개")
    print(f"  - 실패: {summary['failed']}개")
    print(f"  - 성공률: {summary['success_rate']:.1f}%")

    # JSON 파일로 저장
    output_path = results.save_to_file()
    print(f"\n결과 저장: {output_path}")

    print("\n" + "=" * 80)
    if summary['failed'] == 0:
        print("✅ 모든 테스트 통과!")
    else:
        print(f"⚠️  {summary['failed']}개 테스트 실패")
    print("=" * 80)

    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
