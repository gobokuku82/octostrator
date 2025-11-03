# Execute Node Enhancement - 구현 계획 문서

**프로젝트**: 홈즈냥즈 Beta v001
**목표**: Execute Node에 LLM 기반 동적 오케스트레이션 추가
**아키텍처**: LangGraph 0.6 Multi-Agent System
**작성일**: 2025-10-15

---

## 📚 문서 개요

이 디렉토리는 **Supervisor의 execute_teams_node를 "단순 실행자"에서 "지능형 오케스트레이터"로 전환**하기 위한 전체 설계 및 구현 계획을 포함합니다.

---

## 📄 문서 목록

### 1. [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) ⭐ **필독**

**전체 구현 계획서 (가장 중요한 문서)**

**내용**:
- 📊 현황 분석: 현재 시스템 구조 및 문제점
- 🎯 개선 목표: 동적 조율, 통합 도구 관리, 지능형 에러 처리
- 🏗️ 아키텍처 설계: 새로운 실행 흐름 (4단계 노드)
- 📝 구현 계획: Phase 1-5 상세 단계 (4-5일 예상)
- 🆕 새로운 LLM 호출 4회:
  - LLM #4: execution_strategy.txt
  - LLM #5: tool_orchestration.txt
  - LLM #6: result_analysis.txt
  - LLM #7: execution_review.txt
- 🛠️ 도구 관리 전략: Global Tool Registry
- 🧪 테스트 계획: 3가지 시나리오
- ⚡ 성능 고려사항: LLM 호출 증가 대응

**페이지**: ~50페이지
**코드 예시**: 15+
**다이어그램**: 2개 (Mermaid)

**대상 독자**: 백엔드 개발자, 시스템 아키텍트, 프로젝트 매니저

---

### 2. [AGENT_TOOL_STRATEGY.md](./AGENT_TOOL_STRATEGY.md)

**에이전트별 LLM 호출 및 도구 관리 상세 전략**

**내용**:
- 🔍 SearchExecutor 전략:
  - LLM 호출 재구성 (2회 → 0-1회)
  - execute_with_orchestration 메서드
  - 도구별 세부 전략 (legal_search, market_data, real_estate_search, loan_data)
  - 파라미터 최적화
- 📊 AnalysisExecutor 전략:
  - LLM 호출 재구성 (4-6회 → 3-5회)
  - execute_with_context 메서드
  - 이전 팀 결과 활용 패턴
- 📄 DocumentExecutor 전략:
  - LLM 불필요 (템플릿 기반 유지)
  - 법률 검색 결과 활용
- 🔄 도구 간 협업 패턴:
  - 검색 → 분석 파이프라인
  - 검색 → 문서 생성
  - 병렬 검색 + 순차 분석
- 🎨 LLM 프롬프트 최적화:
  - 토큰 절감 (10,000 → 500 토큰)
  - max_tokens 제한
  - Temperature 조정

**페이지**: ~30페이지
**코드 예시**: 12+
**다이어그램**: 3개 (Mermaid)

**대상 독자**: 백엔드 개발자, LLM 엔지니어

---

### 3. [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)

**시각적 아키텍처 다이어그램 모음**

**내용**:
- 🌊 전체 시스템 흐름: Before vs After
- 🏗️ Execute Node 상세 구조: 4단계 실행 흐름
- 🔗 LLM 호출 맵: 14회 호출 전체 시퀀스
- 🛠️ 도구 오케스트레이션: Global Tool Registry, 도구 선택 로직
- 🔄 에러 복구 흐름: 팀 실패 시 대응, 에러 유형별 전략
- 🔀 상태 전이 다이어그램: ExecutionContext, 팀 실행 상태
- 📊 비교 요약: 기존 vs 개선

**다이어그램**: 12개 (Mermaid)
**비교 테이블**: 3개

**대상 독자**: 시스템 아키텍트, 기술 리더, 프로젝트 매니저, 디자이너

---

## 🎯 핵심 개선 사항

### 1. Execute Node를 4단계로 분해

```
기존: execute_teams_node (단순 팀 실행)

개선:
  ↓
pre_execution_node (LLM #4: 실행 전략 수립)
  ↓
team_execution_loop
  ├─ before_team_execution (LLM #5: 도구 오케스트레이션)
  ├─ 팀 실행 (SearchExecutor/AnalysisExecutor)
  └─ after_team_execution (LLM #6: 결과 분석)
  ↓
post_execution_node (LLM #7: 실행 종합 검토)
```

### 2. LLM 호출 재구성

| 단계 | 기존 | 개선 | 변화 |
|------|------|------|------|
| Planning | 3회 | 3회 | 유지 |
| **Execute** | **0회** | **4회** | **+4회** |
| SearchExecutor | 2회 | 0-1회 | -1-2회 |
| AnalysisExecutor | 4-6회 | 3-5회 | -1회 |
| Response | 1회 | 1회 | 유지 |
| **총합** | **10회** | **14회** | **+4회** |

### 3. 전역 도구 관리

**Global Tool Registry**:
- 모든 도구를 중앙에서 추적
- 도구 중복 사용 방지 (30% → 0%)
- 도구 간 의존성 자동 관리
- 비용-효과 분석 기반 선택

### 4. 동적 실행 조율

- 중간 결과 품질 분석
- 실행 중 계획 조정 (팀 스킵, 파라미터 변경)
- 조기 종료 판단
- 에러 복구 전략 수립

---

## 📖 읽는 순서 (권장)

### 신규 개발자 / 이해 우선

```
1. README.md (이 파일) - 전체 개요
   ↓
2. ARCHITECTURE_DIAGRAM.md - 시각적 이해
   ↓
3. IMPLEMENTATION_PLAN.md - 상세 계획
   ↓
4. AGENT_TOOL_STRATEGY.md - 에이전트별 전략
```

### 구현 담당자 / 코드 작성

```
1. IMPLEMENTATION_PLAN.md - 전체 계획 숙지
   ↓
2. AGENT_TOOL_STRATEGY.md - 에이전트별 구현 상세
   ↓
3. ARCHITECTURE_DIAGRAM.md - 흐름 확인
   ↓
4. 코드 작성 시작 (Phase 1부터)
```

### 리뷰어 / 의사결정자

```
1. README.md - 핵심 요약
   ↓
2. IMPLEMENTATION_PLAN.md (섹션별)
   - 개선 목표
   - 아키텍처 설계
   - 성능 고려사항
   ↓
3. ARCHITECTURE_DIAGRAM.md - 비교 요약
```

---

## ⏱️ 구현 일정

### Phase 1: 기반 작업 (1일)

- [ ] ExecutionContext 클래스 구현
- [ ] 4개 프롬프트 파일 작성
- [ ] Global Tool Registry 구축
- [ ] 헬퍼 함수 작성

### Phase 2: Execute Node 리팩토링 (1.5일)

- [ ] execute_teams_node 분해 (4단계)
- [ ] pre_execution_node 구현 + LLM 연동
- [ ] team_execution_loop 구현
- [ ] before_team_execution 구현 + LLM 연동
- [ ] after_team_execution 구현 + LLM 연동
- [ ] post_execution_node 구현 + LLM 연동

### Phase 3: Executor 강화 (1일)

- [ ] SearchExecutor.execute_with_orchestration
- [ ] AnalysisExecutor.execute_with_context
- [ ] DocumentExecutor 검토

### Phase 4: 통합 테스트 (0.5일)

- [ ] 단순 질문 테스트
- [ ] 복합 질문 테스트
- [ ] 에러 시나리오 테스트
- [ ] 성능 테스트

### Phase 5: 문서화 및 배포 (0.5일)

- [ ] 코드 주석 추가
- [ ] 실행 흐름 다이어그램 업데이트
- [ ] 테스트 보고서 작성
- [ ] 배포

**총 예상 기간**: 4-5일

---

## 📊 기대 효과

### 정량적 개선

| 메트릭 | 기존 | 목표 | 개선율 |
|-------|------|------|--------|
| 도구 중복 사용 | 30% | 0% | -100% |
| 에러 복구율 | 0% | 70% | +70% |
| 결과 일관성 | 70% | 90% | +29% |
| 응답 시간 (단순) | 5-7초 | 7-9초 | +20-30% |
| 응답 시간 (복합) | 15-20초 | 18-22초 | +10-15% |

### 정성적 개선

✅ **장점**:
- 전체 시스템 관점에서 도구 관리
- 실행 중 동적 계획 조정 가능
- 에러 발생 시 자동 복구 전략
- 사용자에게 투명한 진행 상황
- 중간 결과 품질 보장

⚠️ **단점**:
- LLM 호출 40% 증가 (10회 → 14회)
- 응답 시간 10-30% 증가
- 구현 복잡도 증가
- 유지보수 비용 증가

💡 **완화책**:
- IRRELEVANT 쿼리는 LLM 최소화
- 병렬 LLM 호출
- 결과 캐싱 (Redis)
- 프롬프트 최적화 (max_tokens)

---

## 🔍 주요 코드 위치

### 수정 대상 파일

1. **TeamSupervisor**
   - 파일: `backend/app/service_agent/supervisor/team_supervisor.py`
   - 라인: 513-695 (execute_teams_node)
   - 변경: 4단계 노드로 분해

2. **SearchExecutor**
   - 파일: `backend/app/service_agent/execution_agents/search_executor.py`
   - 라인: 28-909
   - 변경: execute_with_orchestration 메서드 추가

3. **AnalysisExecutor**
   - 파일: `backend/app/service_agent/execution_agents/analysis_executor.py`
   - 변경: execute_with_context 메서드 추가

### 신규 파일

1. **ExecutionContext**
   - 파일: `backend/app/service_agent/foundation/execution_context.py` (신규)
   - 내용: 실행 컨텍스트 관리

2. **프롬프트 파일** (4개)
   - `backend/app/service_agent/llm_manager/prompts/execution/execution_strategy.txt`
   - `backend/app/service_agent/llm_manager/prompts/execution/tool_orchestration.txt`
   - `backend/app/service_agent/llm_manager/prompts/execution/result_analysis.txt`
   - `backend/app/service_agent/llm_manager/prompts/execution/execution_review.txt`

---

## 🧪 테스트 시나리오

### 시나리오 1: 단순 법률 질문

**입력**: "전세금 5% 인상 가능한가요?"

**예상 LLM 호출**: 10회
- Planning: 3회
- Execute Pre: 1회
- Execute Before: 1회 (search_team)
- SearchExecutor: 1회 (keyword_extraction)
- Execute After: 1회 (search_team)
- Execute Post: 1회
- Response: 1회

**예상 시간**: 7-9초 (기존 5-7초)

### 시나리오 2: 복합 질문

**입력**: "강남구 아파트 시세 확인하고 대출 가능 금액도 알려줘"

**예상 LLM 호출**: 15회
- Planning: 3회
- Execute Pre: 1회
- Execute Before: 2회 (search_team, analysis_team)
- SearchExecutor: 1회
- AnalysisExecutor: 3-5회
- Execute After: 2회
- Execute Post: 1회
- Response: 1회

**예상 시간**: 18-22초 (기존 15-20초)

### 시나리오 3: 에러 복구

**입력**: "서초구 매물 검색하고 리스크 분석해줘"

**시뮬레이션**: search_team의 real_estate_search 도구 실패

**예상 동작**:
1. Execute Before: legal_search + real_estate_search 선택
2. real_estate_search 실패
3. Execute After: 품질 0.3 (낮음), next_action="adjust"
4. 계획 조정: analysis_team 스킵 또는 다른 도구 시도
5. Execute Post: 부분 달성, 사용자 안내

**예상 시간**: 8-10초

---

## 🔗 관련 문서 링크

### 프로젝트 문서

- [시스템 흐름도](../Manual/SYSTEM_FLOW_DIAGRAM.md)
- [아키텍처 개요](../Manual/ARCHITECTURE_OVERVIEW.md)
- [데이터베이스 가이드](../Manual/DATABASE_GUIDE.md)

### 코드 레퍼런스

- [TeamSupervisor](../../../service_agent/supervisor/team_supervisor.py)
- [SearchExecutor](../../../service_agent/execution_agents/search_executor.py)
- [AnalysisExecutor](../../../service_agent/execution_agents/analysis_executor.py)
- [PlanningAgent](../../../service_agent/cognitive_agents/planning_agent.py)

---

## 📞 문의 및 피드백

### 구현 관련 질문

- **담당자**: 백엔드 팀
- **Slack**: #holmesnyangz-backend
- **Issues**: GitHub Issues 탭

### 설계 검토 요청

- **담당자**: 시스템 아키텍트
- **이메일**: architect@holmesnyangz.com
- **회의 일정**: 매주 화요일 14:00

---

## 📝 버전 이력

| 버전 | 날짜 | 변경 사항 | 작성자 |
|------|------|----------|--------|
| 1.0 | 2025-10-15 | 초기 설계 문서 작성 | Claude |

---

## ✅ 체크리스트

### 설계 단계
- [x] 현황 분석 완료
- [x] 개선 목표 확정
- [x] 아키텍처 설계 완료
- [x] 프롬프트 파일 작성 완료
- [x] 테스트 계획 수립

### 구현 단계 (예정)
- [ ] Phase 1: 기반 작업
- [ ] Phase 2: Execute Node 리팩토링
- [ ] Phase 3: Executor 강화
- [ ] Phase 4: 통합 테스트
- [ ] Phase 5: 문서화 및 배포

### 검토 단계 (예정)
- [ ] 코드 리뷰 (백엔드 팀)
- [ ] 아키텍처 리뷰 (시스템 아키텍트)
- [ ] 성능 테스트 (QA 팀)
- [ ] 배포 승인 (프로젝트 매니저)

---

**마지막 업데이트**: 2025-10-15
**상태**: ✅ 설계 완료, 구현 대기
**우선순위**: 중간 (Phase 2 Long-term Memory 완료 후 진행)
**예상 공수**: 4-5일
**리스크**: 중간 (LLM 호출 증가, 복잡도 증가)

---

**홈즈냥즈 팀** 🏠🐱
