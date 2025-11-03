"""
홈즈냥즈 AI 에이전트 - 대화형 실행 프로그램
터미널에서 직접 쿼리를 입력하고 과정 및 답변을 확인할 수 있습니다.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import io

# Windows 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Path setup
backend_dir = Path(__file__).parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.separated_states import MainSupervisorState
from app.service_agent.foundation.context import create_default_llm_context


class Colors:
    """터미널 색상 코드"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """시작 배너 출력"""
    banner = f"""
{Colors.OKCYAN}{Colors.BOLD}
================================================================

         홈즈냥즈 AI 부동산 상담 에이전트

        법률 · 시장 · 대출 상담을 한 번에!

================================================================
{Colors.ENDC}
    """
    print(banner)


def print_section(title, color=Colors.OKBLUE):
    """섹션 헤더 출력"""
    print(f"\n{color}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{color}{Colors.BOLD}  {title}{Colors.ENDC}")
    print(f"{color}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_step(step_num, title, detail=""):
    """단계별 진행 상황 출력"""
    print(f"{Colors.OKGREEN}[{step_num}] {Colors.BOLD}{title}{Colors.ENDC}")
    if detail:
        print(f"    {Colors.OKCYAN}{detail}{Colors.ENDC}")


def print_info(label, value, indent=1):
    """정보 항목 출력"""
    indent_str = "  " * indent
    print(f"{indent_str}{Colors.BOLD}{label}:{Colors.ENDC} {value}")


def print_success(message):
    """성공 메시지 출력"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_warning(message):
    """경고 메시지 출력"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_error(message):
    """에러 메시지 출력"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


class HolmesNyangzCLI:
    """홈즈냥즈 CLI 인터페이스"""

    def __init__(self):
        self.supervisor = None
        self.llm_context = None
        self.session_count = 0

    async def initialize(self):
        """시스템 초기화"""
        print_step("1/2", "시스템 초기화 중...", "LLM Context 및 에이전트 로딩")

        try:
            # 로깅 설정
            logging.basicConfig(
                level=logging.WARNING,  # WARNING 이상만 출력
                format='%(name)s - %(levelname)s - %(message)s'
            )

            # LLM Context 초기화
            self.llm_context = create_default_llm_context()
            print_success("LLM Context 초기화 완료")

            # Supervisor 초기화
            self.supervisor = TeamBasedSupervisor(self.llm_context)
            print_success("팀 기반 Supervisor 초기화 완료")

            print_step("2/2", "시스템 준비 완료!", "이제 질문을 입력하실 수 있습니다.")

        except Exception as e:
            print_error(f"초기화 실패: {e}")
            raise

    async def process_query(self, query: str):
        """쿼리 처리"""
        self.session_count += 1
        session_id = f"session_{self.session_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print_section(f"질문 처리 중 (Session: {session_id})")

        print_info("질문", f'"{query}"')
        print()

        # 초기 상태 생성
        initial_state = MainSupervisorState(
            query=query,
            session_id=session_id,
            user_id=None,
            status="pending",
            current_phase="initialization",
            planning_state=None,
            execution_plan=None,
            active_teams=[],
            completed_teams=[],
            failed_teams=[],
            team_results={},
            aggregated_results={},
            final_response=None,
            error_log=[],
            start_time=None,
            end_time=None,
            total_execution_time=None,
            metadata={"cli_mode": True, "session": session_id}
        )

        start_time = datetime.now()

        try:
            # Phase 1: 초기화
            print_step("Phase 1/5", "초기화", "상태 준비 중...")

            # Phase 2-5: Supervisor 실행
            print_step("Phase 2/5", "Intent 분석", "질문의 의도를 파악하는 중...")

            final_state = await self.supervisor.app.ainvoke(initial_state)

            # 실행 시간 계산
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Phase 2: Planning 결과 출력
            print()
            planning_state = final_state.get('planning_state', {})
            if planning_state:
                analyzed_intent = planning_state.get('analyzed_intent', {})

                print_success("Intent 분석 완료")
                print_info("감지된 의도", analyzed_intent.get('intent_type', 'UNKNOWN'), indent=2)
                print_info("신뢰도", f"{analyzed_intent.get('confidence', 0):.0%}", indent=2)

                keywords = analyzed_intent.get('keywords', [])
                if keywords:
                    print_info("주요 키워드", ', '.join(keywords), indent=2)

                entities = analyzed_intent.get('entities', {})
                if entities:
                    filtered_entities = {k: v for k, v in entities.items() if v}
                    if filtered_entities:
                        print_info("추출된 정보", "", indent=2)
                        for key, value in filtered_entities.items():
                            print_info(f"  - {key}", value, indent=3)

            # Phase 3: Team 실행 결과
            print()
            print_step("Phase 3/5", "팀 실행", "관련 정보 검색 중...")

            completed_teams = final_state.get('completed_teams', [])
            failed_teams = final_state.get('failed_teams', [])
            team_results = final_state.get('team_results', {})

            if completed_teams:
                print_success(f"실행 완료: {', '.join(completed_teams)}")

                # 팀별 결과 상세
                for team_name, team_result in team_results.items():
                    if isinstance(team_result, dict):
                        status = team_result.get('status', 'unknown')

                        # 검색 결과 카운트
                        result_count = 0
                        data_sources = []

                        if 'legal_results' in team_result:
                            count = len(team_result.get('legal_results', []))
                            result_count += count
                            if count > 0:
                                data_sources.append(f"법률 DB ({count}건)")

                        if 'real_estate_results' in team_result:
                            count = len(team_result.get('real_estate_results', []))
                            result_count += count
                            if count > 0:
                                data_sources.append(f"부동산 DB ({count}건)")

                        if 'loan_results' in team_result:
                            count = len(team_result.get('loan_results', []))
                            result_count += count
                            if count > 0:
                                data_sources.append(f"대출 DB ({count}건)")

                        if data_sources:
                            print_info(f"{team_name} 팀", f"{', '.join(data_sources)}", indent=2)

            if failed_teams:
                print_warning(f"실패한 팀: {', '.join(failed_teams)}")

            # Phase 4: Aggregation
            print()
            print_step("Phase 4/5", "결과 통합", "검색 결과를 종합하는 중...")

            aggregated_results = final_state.get('aggregated_results', {})
            total_results = sum(len(v) if isinstance(v, list) else 0 for v in aggregated_results.values())
            if total_results > 0:
                print_success(f"총 {total_results}개의 관련 정보 수집 완료")

            # Phase 5: Response Generation
            print()
            print_step("Phase 5/5", "답변 생성", "AI가 답변을 작성하는 중...")

            final_response = final_state.get('final_response', {})
            if isinstance(final_response, dict):
                answer = final_response.get('answer', '')
            else:
                answer = str(final_response) if final_response else ''

            if answer:
                print_success("답변 생성 완료")
            else:
                print_warning("답변이 생성되지 않았습니다")

            # 최종 답변 출력
            print_section("📝 답변", Colors.OKGREEN)

            if answer:
                print(f"{Colors.BOLD}{answer}{Colors.ENDC}")
            else:
                print_warning("답변을 생성할 수 없습니다. 질문을 다시 입력해주세요.")

            # 실행 정보
            print()
            print_section("📊 실행 정보", Colors.OKCYAN)
            print_info("처리 시간", f"{execution_time:.2f}초")
            print_info("상태", final_state.get('status', 'unknown'))

            if final_state.get('error_log'):
                print_warning(f"경고/에러 {len(final_state['error_log'])}건")
                for error in final_state['error_log']:
                    print(f"  - {error}")

        except Exception as e:
            print_error(f"처리 중 오류 발생: {e}")
            import traceback
            print()
            print(f"{Colors.FAIL}상세 오류:{Colors.ENDC}")
            traceback.print_exc()

    async def run(self):
        """메인 실행 루프"""
        print_banner()

        # 초기화
        await self.initialize()

        print()
        print_section("💬 대화 시작", Colors.HEADER)
        print(f"{Colors.BOLD}사용법:{Colors.ENDC}")
        print("  - 질문을 입력하고 Enter를 누르세요")
        print("  - 'quit', 'exit', 'q'를 입력하면 종료됩니다")
        print("  - 'clear'를 입력하면 화면을 지웁니다")
        print("  - 'help'를 입력하면 예제 질문을 확인할 수 있습니다")
        print()

        # 메인 루프
        while True:
            try:
                # 사용자 입력
                print(f"{Colors.BOLD}{Colors.OKCYAN}질문 >{Colors.ENDC} ", end='')
                user_input = input().strip()

                # 명령어 처리
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print()
                    print_section("👋 종료", Colors.WARNING)
                    print_success("홈즈냥즈 AI 에이전트를 종료합니다.")
                    print(f"{Colors.OKCYAN}총 {self.session_count}개의 질문을 처리했습니다.{Colors.ENDC}")
                    break

                elif user_input.lower() == 'clear':
                    import os
                    os.system('cls' if sys.platform == 'win32' else 'clear')
                    print_banner()
                    continue

                elif user_input.lower() == 'help':
                    self.show_help()
                    continue

                elif not user_input:
                    print_warning("질문을 입력해주세요.")
                    continue

                # 쿼리 처리
                await self.process_query(user_input)

                print()

            except KeyboardInterrupt:
                print()
                print()
                print_section("👋 종료", Colors.WARNING)
                print_success("Ctrl+C로 종료합니다.")
                break

            except Exception as e:
                print_error(f"예상치 못한 오류: {e}")
                import traceback
                traceback.print_exc()

    def show_help(self):
        """도움말 및 예제 출력"""
        print()
        print_section("📚 도움말 및 예제 질문", Colors.HEADER)

        examples = {
            "법률 상담": [
                "전세금 5% 인상이 가능한가요?",
                "보증금 반환 안 받으면 어떻게 하나요?",
                "임대차보호법 적용 범위가 어떻게 되나요?",
                "계약금 돌려받을 수 있나요?"
            ],
            "시장 조회": [
                "강남구 아파트 시세 알려주세요",
                "서초구 전세 매물 있나요?",
                "송파구 아파트 값 어떻게 되나요?",
                "마포구 전세 시세는?"
            ],
            "대출 상담": [
                "주택담보대출 금리 비교해주세요",
                "전세자금대출 조건이 어떻게 되나요?",
                "신혼부부 대출 한도는?",
                "생애최초 주택 구매 대출 알려주세요"
            ],
            "복합 질문": [
                "강남 아파트 매매가와 대출 한도 알려주세요",
                "서초 전세 계약 시 법적 주의사항과 금리는?",
                "전세 사기 예방 방법과 관련 법률은?"
            ]
        }

        for category, questions in examples.items():
            print(f"{Colors.BOLD}{Colors.OKBLUE}▶ {category}{Colors.ENDC}")
            for q in questions:
                print(f"  {Colors.OKCYAN}•{Colors.ENDC} {q}")
            print()


async def main():
    """메인 함수"""
    cli = HolmesNyangzCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n종료되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
