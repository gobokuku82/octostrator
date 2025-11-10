# Phase 2 구현 계획서: Supervisor 구조 개편 + Context API 도입

**작성일**: 2025-11-05
**프로젝트**: AI PT Manager Beta v001
**Phase**: Phase 2 (Supervisor 최적화 + Context API)
**예상 기간**: 2주 (10 작업일)
**목표**: 시스템 안정성 향상 + 비용 50% 절감

---

## 📋 Executive Summary

### Phase 1 완료 현황 (2025-11-05)
- ✅ Tools Registry 구현 (11개 Tools 중앙 관리)
- ✅ LLM max_tokens 설정 (4096 전역, 2048 Planning)
- ✅ 전체 에이전트 테스트 성공률 100% (4/4)

### Phase 2 목표
1. **Supervisor 구조 개편**: 현재 8개 파일 → 4-Layer 구조 (nodes/helpers/prompts/graphs)
2. **Context API 도입**: 노드별 LLM 설정 관리 (max_tokens, temperature)
3. **프롬프트 최적화**: 109줄 → 30줄 압축 (70% 토큰 절감)

### 예상 효과
- 🎯 **토큰 사용량**: 30-40% 감소
- 💰 **비용**: 50% 이상 절감
- 🏗️ **유지보수성**: 파일 역할 명확화
- 🧪 **테스트 용이성**: 노드별 독립 테스트 가능

---

## 🎯 Phase 2 상세 목표

### 목표 1: Supervisor 구조 개편
**현재 문제**:
- `cognitive_supervisor.py`: 457줄 (그래프 + 노드 + 헬퍼 혼재)
- `execute_supervisor.py`: 520줄 (그래프 + 노드 + 헬퍼 혼재)
- 프롬프트 일부는 `.py`, 일부는 파일 내 하드코딩

**목표 구조**:
```
supervisor/
├── nodes/          # 순수 노드 함수만 (async def xxx_node)
│   ├── cognitive_nodes.py
│   ├── execute_nodes.py
│   └── response_nodes.py
│
├── helpers/        # 노드가 사용하는 헬퍼 클래스
│   ├── intent_classifier.py     # IntentClassifier
│   ├── agent_executor.py        # AgentExecutor
│   └── output_formatter.py
│
├── prompts/        # 모든 프롬프트 중앙 관리
│   ├── cognitive_prompts.py
│   ├── execute_prompts.py
│   └── response_prompts.py
│
└── graphs/         # 그래프 빌딩 로직만
    ├── cognitive_graph.py
    ├── execute_graph.py
    └── main_graph.py
```

### 목표 2: Context API 도입
**현재 문제**:
- LLM 설정이 하드코딩됨 (`temperature=0.7`, `max_tokens=4096`)
- 노드별 맞춤 설정 불가
- 환경별 분리 없음 (dev/prod 동일)

**목표**:
```python
# contexts/app_context.py
class LLMSettings(BaseModel):
    planning_temperature: float = 0.3
    planning_max_tokens: int = 2048
    chat_temperature: float = 0.7
    chat_max_tokens: int = 4096
    # ... 노드별 설정

# nodes/cognitive_nodes.py
async def planning_node(state, runtime: Runtime):
    settings = runtime.context.llm_settings
    llm = ChatOpenAI(
        temperature=settings.planning_temperature,
        max_tokens=settings.planning_max_tokens
    )
```

### 목표 3: 프롬프트 최적화
**현재 문제**:
- `PLANNING_SYSTEM_PROMPT`: 109줄 (1,323 tokens)
- 불필요한 설명, 예시 포함

**목표**:
- 핵심만 남기고 압축: 30줄 (400 tokens)
- 70% 토큰 절감

---

## 📅 상세 일정 (2주 / 10 작업일)

### Week 1: Supervisor 구조 개편 + Context API 기반

#### Day 1 (2025-11-06): Supervisor 구조 개편 - 폴더 생성 및 파일 분리
**작업 시간**: 6시간

**Task 1.1**: 폴더 구조 생성 (30분)
```bash
supervisor/
├── nodes/
├── helpers/
├── prompts/
└── graphs/
```

**Task 1.2**: helpers/ 분리 (2시간)
- `helpers/intent_classifier.py`: IntentClassifier 클래스 이동
- `helpers/agent_executor.py`: AgentExecutor 클래스 이동
- `helpers/__init__.py`: exports 정의

**Task 1.3**: prompts/ 통합 (1.5시간)
- 모든 프롬프트를 `prompts/`로 이동
- 하드코딩된 프롬프트도 추출
- `cognitive_supervisor.py` 내부 프롬프트 → `prompts/cognitive_prompts.py`

**Task 1.4**: nodes/ 분리 (2시간)
- `nodes/cognitive_nodes.py`: 노드 함수만 추출
- `nodes/execute_nodes.py`: 실행 노드 추출
- `nodes/response_nodes.py`: 응답 생성 노드 (기존 유지)

**Task 1.5**: Import 경로 수정 (30분)
- `from ..helpers.intent_classifier import IntentClassifier`
- `from ..prompts.cognitive_prompts import PLANNING_SYSTEM_PROMPT`

**검증**:
- [ ] 서버 시작 시 에러 없음
- [ ] 기존 테스트 통과 (4/4 성공 유지)

---

#### Day 2 (2025-11-07): graphs/ 분리 + Context API 준비
**작업 시간**: 6시간

**Task 2.1**: graphs/ 분리 (2.5시간)
- `graphs/cognitive_graph.py`: build_cognitive_supervisor() 이동
- `graphs/execute_graph.py`: build_execute_supervisor() 이동
- `graphs/main_graph.py`: build_supervisor_graph() 유지 + 정리

**Task 2.2**: AppContext 확장 (2시간)
- `contexts/app_context.py`: LLMSettings 클래스 추가
- Pydantic Field로 범위 검증 추가
- 노드별 설정 정의 (7개 노드)

**Task 2.3**: 환경별 설정 팩토리 생성 (1.5시간)
- `config/llm_settings.py` 신규 생성
- `get_llm_settings(environment)` 함수 구현
- production/development/testing 설정 정의

**검증**:
- [ ] AppContext import 에러 없음
- [ ] LLMSettings 범위 검증 동작 확인

---

#### Day 3 (2025-11-08): Cognitive Nodes에 Context API 적용
**작업 시간**: 6시간

**Task 3.1**: intent_understanding_node 수정 (1.5시간)
- 시그니처 변경: `(state, llm)` → `(state, runtime: Runtime)`
- Runtime Context에서 설정 가져오기
- LLM 생성 시 설정 적용

**Task 3.2**: planning_node 수정 (1.5시간)
- Runtime Context 사용
- planning 전용 설정 적용 (temperature=0.3, max_tokens=2048)

**Task 3.3**: aggregator_node 수정 (1.5시간)
- Runtime Context 사용
- aggregator 전용 설정 적용

**Task 3.4**: executor_node 검토 (1시간)
- Agent 실행은 Agent 내부 설정 사용
- Context 전달 확인

**Task 3.5**: 통합 테스트 (30분)
- Cognitive 노드들 개별 테스트
- 전체 플로우 테스트

**검증**:
- [ ] Cognitive Nodes 테스트 통과
- [ ] LLM 설정이 Runtime Context에서 올바르게 로드됨

---

#### Day 4 (2025-11-09): Response Nodes에 Context API 적용
**작업 시간**: 6시간

**Task 4.1**: chat_generator_node 수정 (1.5시간)
- Runtime Context 사용
- chat 전용 설정 적용 (temperature=0.7, max_tokens=4096)

**Task 4.2**: graph_generator_node 수정 (1.5시간)
- Runtime Context 사용
- graph 전용 설정 적용 (temperature=0.2, max_tokens=2048)

**Task 4.3**: report_generator_node 수정 (1.5시간)
- Runtime Context 사용
- report 전용 설정 적용 (temperature=0.5, max_tokens=8192)

**Task 4.4**: hitl_handler_node 검토 (30분)
- interrupt() 로직 유지
- Context 사용 여부 확인

**Task 4.5**: 통합 테스트 (1시간)
- Response Nodes 개별 테스트
- 전체 플로우 테스트

**검증**:
- [ ] Response Nodes 테스트 통과
- [ ] 각 노드별로 다른 LLM 설정 적용 확인

---

#### Day 5 (2025-11-10): Graph에 Context Schema 등록 + API 수정
**작업 시간**: 6시간

**Task 5.1**: main_graph.py에 context_schema 등록 (1.5시간)
```python
workflow = StateGraph(
    SupervisorState,
    context_schema=AppContext  # ⭐ 등록
)
```

**Task 5.2**: cognitive_graph.py에 context_schema 등록 (1시간)
- CognitiveSupervisor 그래프에도 적용

**Task 5.3**: execute_graph.py에 context_schema 등록 (1시간)
- ExecuteSupervisor 그래프에도 적용

**Task 5.4**: API에서 Context 전달 (1.5시간)
- `api/sessions.py`: AppContext 생성 및 전달
- `api/websocket.py`: AppContext 생성 및 전달
- 환경 설정 로드 (`config.environment`)

**Task 5.5**: 전체 통합 테스트 (1시간)
- API를 통한 호출 테스트
- Context가 모든 노드까지 전파되는지 확인

**검증**:
- [ ] Graph 컴파일 에러 없음
- [ ] API 호출 시 Context 정상 전달
- [ ] 전체 에이전트 테스트 100% 성공 유지

---

### Week 2: 프롬프트 최적화 + 테스트 + 문서화

#### Day 6 (2025-11-11): 프롬프트 최적화 (Cognitive)
**작업 시간**: 6시간

**Task 6.1**: PLANNING_SYSTEM_PROMPT 압축 (3시간)
- **현재**: 109줄, 1,323 tokens
- **목표**: 30줄, 400 tokens
- 불필요한 설명 제거
- 핵심 지침만 유지
- JSON 스키마 간소화

**Task 6.2**: INTENT_UNDERSTANDING_PROMPT 압축 (1.5시간)
- 현재 상태 분석
- 핵심만 추출

**Task 6.3**: AGGREGATOR_PROMPT 압축 (1.5시간)
- 결과 종합 로직 명확화
- 예시 제거, 지침만 유지

**검증**:
- [ ] 압축 전후 토큰 수 측정
- [ ] 압축 후에도 동일한 품질 출력 확인
- [ ] Planning 테스트 통과

---

#### Day 7 (2025-11-12): 프롬프트 최적화 (Response)
**작업 시간**: 6시간

**Task 7.1**: CHAT_GENERATION_PROMPT 최적화 (2시간)
- 자연스러운 대화 생성 핵심 지침
- 포맷 간소화

**Task 7.2**: GRAPH_GENERATION_PROMPT 최적화 (2시간)
- JSON 스키마 정확성 우선
- 예시 제거

**Task 7.3**: REPORT_GENERATION_PROMPT 최적화 (2시간)
- Markdown 구조 지침 간소화

**검증**:
- [ ] 모든 프롬프트 압축 완료
- [ ] 전체 토큰 절감율 측정 (목표: 50% 이상)
- [ ] Response 품질 유지 확인

---

#### Day 8 (2025-11-13): 단위 테스트 작성
**작업 시간**: 6시간

**Task 8.1**: LLMSettings 테스트 (2시간)
```python
# tests/test_llm_settings.py
def test_production_settings()
def test_development_settings()
def test_testing_settings()
def test_settings_validation()  # 범위 초과 시 에러
```

**Task 8.2**: Context 전파 테스트 (2시간)
```python
# tests/test_context_api.py
async def test_context_propagation()
async def test_node_llm_settings()
```

**Task 8.3**: Helper 클래스 테스트 (1시간)
```python
# tests/test_intent_classifier.py
def test_classify_diet()
def test_classify_workout()

# tests/test_agent_executor.py
async def test_execute_single_agent()
```

**Task 8.4**: 프롬프트 압축 효과 테스트 (1시간)
- 압축 전후 토큰 수 비교
- 출력 품질 비교

**검증**:
- [ ] 모든 단위 테스트 통과
- [ ] 커버리지 80% 이상

---

#### Day 9 (2025-11-14): 통합 테스트 + 성능 측정
**작업 시간**: 6시간

**Task 9.1**: 전체 에이전트 테스트 (2시간)
- test_agents_renewal.py 재실행
- 4/4 성공률 100% 확인
- 각 노드별 LLM 설정 확인

**Task 9.2**: 성능 측정 (2시간)
- **토큰 사용량 측정**:
  - Before: planning_tokens, chat_tokens 등
  - After: 압축 후 토큰 수
  - 절감율 계산

- **비용 측정**:
  - gpt-4o-mini 요금 기준 계산
  - 전후 비교

- **응답 시간 측정**:
  - 평균 응답 시간
  - 노드별 실행 시간

**Task 9.3**: 환경별 테스트 (1.5시간)
- production 설정으로 테스트
- development 설정으로 테스트
- testing 설정으로 테스트 (결정론적 출력 확인)

**Task 9.4**: 스트레스 테스트 (30분)
- 10회 연속 실행
- 메모리 누수 확인

**검증**:
- [ ] 전체 테스트 100% 통과
- [ ] 토큰 절감율 30% 이상 달성
- [ ] 비용 절감율 50% 이상 달성

---

#### Day 10 (2025-11-15): 문서화 + 배포 준비
**작업 시간**: 6시간

**Task 10.1**: 구조 변경 문서 작성 (2시간)
- `reports/supervisor/STRUCTURE_MIGRATION_GUIDE.md`
- Before/After 비교
- Import 경로 변경 가이드
- 폴더별 역할 설명

**Task 10.2**: Context API 사용 가이드 (1.5시간)
- `reports/contextAPI/USAGE_GUIDE.md`
- 노드에서 Runtime 사용법
- 환경별 설정 변경 방법
- 트러블슈팅

**Task 10.3**: 성능 측정 보고서 (1.5시간)
- `reports/system/PERFORMANCE_REPORT_PHASE2.md`
- 토큰 절감 상세 분석
- 비용 절감 효과
- 응답 시간 개선

**Task 10.4**: CHANGELOG 작성 (30분)
- Phase 2 변경사항 정리
- Breaking Changes 명시
- Migration Guide 링크

**Task 10.5**: README 업데이트 (30분)
- 새 구조 반영
- 빠른 시작 가이드 업데이트

**검증**:
- [ ] 모든 문서 완성
- [ ] 동료 리뷰 가능 상태

---

## 📊 성공 지표 (KPI)

### 필수 지표
- [x] **테스트 성공률**: 100% (4/4 에이전트)
- [ ] **토큰 절감율**: 30% 이상
- [ ] **비용 절감율**: 50% 이상
- [ ] **단위 테스트 커버리지**: 80% 이상

### 추가 지표
- [ ] **프롬프트 압축율**: 70% (109줄 → 30줄)
- [ ] **파일 구조 명확성**: 각 폴더 역할 100% 정의
- [ ] **응답 시간**: 2.0s → 1.5s 이하
- [ ] **메모리 사용량**: 증가 없음

---

## 🚨 리스크 관리

### 리스크 1: LangGraph 버전 호환성
**문제**: Context API가 v1.0+ 전용
**해결**:
- Day 1 시작 전 LangGraph 버전 확인
- 필요 시 업그레이드
- 하위 호환성 테스트

**대응 플랜**:
- v0.6 이하라면 먼저 업그레이드 (0.5일 소요)
- 업그레이드 불가 시 Context API 제외하고 구조 개편만 진행

---

### 리스크 2: Import 경로 변경으로 인한 버그
**문제**: 대규모 파일 이동으로 import 에러 발생 가능
**해결**:
- 각 Day마다 서버 시작 확인
- 기존 테스트 통과 확인
- 단계별 커밋 (롤백 가능)

**대응 플랜**:
- 에러 발생 시 즉시 롤백
- 한 폴더씩 점진적 이동

---

### 리스크 3: 프롬프트 압축 후 품질 저하
**문제**: 압축 시 중요한 지침 제거될 수 있음
**해결**:
- 압축 전후 A/B 테스트
- 10회 실행하여 출력 품질 비교
- 품질 저하 시 압축 조정

**대응 플랜**:
- 품질 저하 심하면 압축율 50%로 완화
- 핵심 지침만 압축, 예시는 제거

---

### 리스크 4: Context 전파 실패 (Subgraph)
**문제**: Subgraph에 Context 전달 안될 수 있음
**해결**:
- LangGraph 최신 버전 사용 (Issue #5700 해결됨)
- Subgraph 테스트 추가

**대응 플랜**:
- 전파 실패 시 Subgraph에 직접 전달 방식 사용

---

## 📦 산출물

### 코드
- [ ] `supervisor/nodes/` (3개 파일)
- [ ] `supervisor/helpers/` (3개 파일)
- [ ] `supervisor/prompts/` (3개 파일)
- [ ] `supervisor/graphs/` (3개 파일)
- [ ] `contexts/app_context.py` (LLMSettings 추가)
- [ ] `config/llm_settings.py` (환경별 팩토리)

### 테스트
- [ ] `tests/test_llm_settings.py`
- [ ] `tests/test_context_api.py`
- [ ] `tests/test_intent_classifier.py`
- [ ] `tests/test_agent_executor.py`
- [ ] `tests/test_prompt_compression.py`

### 문서
- [ ] `reports/supervisor/STRUCTURE_MIGRATION_GUIDE.md`
- [ ] `reports/contextAPI/USAGE_GUIDE.md`
- [ ] `reports/system/PERFORMANCE_REPORT_PHASE2.md`
- [ ] `CHANGELOG.md` (Phase 2 섹션)
- [ ] `README.md` (업데이트)

---

## 🔄 마이그레이션 가이드 (간략)

### Before (Phase 1)
```
supervisor/
├── cognitive_nodes.py
├── cognitive_prompts.py
├── cognitive_supervisor.py (457줄)
├── execute_supervisor.py (520줄)
└── main_graph.py

# 사용
async def planning_node(state, llm):
    llm = ChatOpenAI(temperature=0.7, max_tokens=4096)  # 하드코딩
```

### After (Phase 2)
```
supervisor/
├── nodes/
│   ├── cognitive_nodes.py
│   ├── execute_nodes.py
│   └── response_nodes.py
├── helpers/
│   ├── intent_classifier.py
│   └── agent_executor.py
├── prompts/
│   ├── cognitive_prompts.py (압축)
│   └── response_prompts.py
└── graphs/
    ├── cognitive_graph.py
    ├── execute_graph.py
    └── main_graph.py

# 사용
async def planning_node(state, runtime: Runtime):
    settings = runtime.context.llm_settings
    llm = ChatOpenAI(
        temperature=settings.planning_temperature,  # Context에서
        max_tokens=settings.planning_max_tokens
    )
```

---

## ✅ 완료 기준 (Definition of Done)

### 코드
- [ ] 모든 파일이 새 구조로 이동 완료
- [ ] Import 경로 모두 수정
- [ ] Context API 모든 노드에 적용
- [ ] 프롬프트 압축 70% 달성

### 테스트
- [ ] 전체 에이전트 테스트 100% 통과 (4/4)
- [ ] 단위 테스트 100% 통과
- [ ] 커버리지 80% 이상

### 성능
- [ ] 토큰 사용량 30% 감소 확인
- [ ] 비용 50% 절감 확인
- [ ] 응답 시간 25% 개선 확인

### 문서
- [ ] 모든 산출 문서 작성 완료
- [ ] CHANGELOG 업데이트
- [ ] README 업데이트

---

## 🎯 Phase 3 Preview

Phase 2 완료 후 다음 단계:

### Phase 3: LangGraph 성능 최적화 (2일)
- Streaming 활성화 (astream)
- Caching 적용 (LLM 응답 캐싱)
- 병렬 실행 최적화

### Phase 4: Monitoring & CI/CD (1일)
- 토큰 사용량 모니터링
- 에러 추적
- 자동 테스트 파이프라인

---

## 📞 연락처 및 지원

**문의사항**:
- 구조 개편 관련: `reports/supervisor/STRUCTURE_MIGRATION_GUIDE.md` 참조
- Context API 관련: `reports/contextAPI/USAGE_GUIDE.md` 참조
- 성능 관련: `reports/system/PERFORMANCE_REPORT_PHASE2.md` 참조

**긴급 이슈**:
- 테스트 실패 시 즉시 롤백
- 서버 시작 불가 시 이전 커밋으로 복구

---

**작성**: Claude (Anthropic)
**승인**: [승인자 이름]
**시작일**: 2025-11-06
**종료 예정일**: 2025-11-15
