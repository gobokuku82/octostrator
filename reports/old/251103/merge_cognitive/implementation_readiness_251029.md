# Option B 구현 준비 완료 보고서

**작성일**: 2025-10-29
**상태**: ✅ 모든 계획 문서 완성
**다음 단계**: 사용자 승인 후 Checkpoint 1 실행 대기

---

## 📊 현재 상태 요약

### 1. 계획 문서 (완료)

| 문서명 | 상태 | 용도 |
|--------|------|------|
| `option_B_precise_execution_plan_251029.md` | ✅ 완료 | 메인 실행 계획서 (6 체크포인트) |
| `cognitive_merge_plan_251029.md` | ✅ 완료 | 초기 분석 문서 |
| `options_comparison_251029.md` | ✅ 완료 | Option A vs B 비교 |
| `option_A_safe_addition_plan_251029.md` | ✅ 완료 | 대안 계획 (미사용) |
| `cognitive_merge_extended_analysis_251029.md` | ✅ 완료 | 상세 분석 보고서 |

### 2. 소스 파일 분석 (완료)

#### 현재 백엔드 상태 (10 카테고리)
[backend/app/service_agent/cognitive_agents/planning_agent.py:32-43](backend/app/service_agent/cognitive_agents/planning_agent.py#L32-L43)
```python
class IntentType(Enum):
    """의도 타입 정의"""
    LEGAL_CONSULT = "법률상담"          # → LEGAL_INQUIRY로 변경 예정
    MARKET_INQUIRY = "시세조회"          # → 값 변경: "시세트렌드분석"
    LOAN_CONSULT = "대출상담"            # → LOAN_SEARCH + LOAN_COMPARISON으로 분할
    CONTRACT_CREATION = "계약서작성"     # → 값 변경: "계약서생성"
    CONTRACT_REVIEW = "계약서검토"       # ❌ 삭제 예정
    COMPREHENSIVE = "종합분석"           # ✅ 유지
    RISK_ANALYSIS = "리스크분석"         # ❌ 삭제 예정
    UNCLEAR = "unclear"                  # ✅ 유지
    IRRELEVANT = "irrelevant"            # → 값 변경: "무관"
    ERROR = "error"                      # ✅ 유지
```

#### 목표 상태 (15 카테고리)
[tests/cognitive/cognitive_agents/planning_agent.py:32-50](tests/cognitive/cognitive_agents/planning_agent.py#L32-L50)
```python
class IntentType(Enum):
    """의도 타입 정의 (15개 카테고리)"""
    TERM_DEFINITION = "용어설명"              # 🆕 NEW
    LEGAL_INQUIRY = "법률해설"                # 🔄 RENAMED
    LOAN_SEARCH = "대출상품검색"              # 🔀 SPLIT
    LOAN_COMPARISON = "대출조건비교"          # 🔀 SPLIT
    BUILDING_REGISTRY = "건축물대장조회"      # 🆕 NEW
    PROPERTY_INFRA_ANALYSIS = "매물인프라분석" # 🆕 NEW
    PRICE_EVALUATION = "가격평가"             # 🆕 NEW
    PROPERTY_SEARCH = "매물검색"              # 🆕 NEW
    PROPERTY_RECOMMENDATION = "맞춤추천"      # 🆕 NEW
    ROI_CALCULATION = "투자수익률계산"        # 🆕 NEW
    POLICY_INQUIRY = "정부정책조회"           # 🆕 NEW
    CONTRACT_CREATION = "계약서생성"          # 🔄 VALUE CHANGED
    MARKET_INQUIRY = "시세트렌드분석"         # 🔄 VALUE CHANGED
    COMPREHENSIVE = "종합분석"                # ✅ UNCHANGED
    IRRELEVANT = "무관"                       # 🔄 VALUE CHANGED
    UNCLEAR = "unclear"                       # ✅ UNCHANGED
    ERROR = "error"                           # ✅ UNCHANGED
```

### 3. 변경 영향 범위 (검증 완료)

#### 파일 수정 계획

| 파일 | 라인 범위 | 변경 유형 | 예상 시간 |
|------|----------|----------|----------|
| [planning_agent.py](backend/app/service_agent/cognitive_agents/planning_agent.py) | 32-51 | IntentType Enum 재구성 | 30분 |
| [planning_agent.py](backend/app/service_agent/cognitive_agents/planning_agent.py) | 108-176 | 패턴 초기화 확장 | 30분 |
| [planning_agent.py](backend/app/service_agent/cognitive_agents/planning_agent.py) | 258-303 | intent_to_agent 매핑 | 30분 |
| [planning_agent.py](backend/app/service_agent/cognitive_agents/planning_agent.py) | 305-397 | safe_defaults 업데이트 | 30분 |
| [team_supervisor.py](backend/app/service_agent/supervisor/team_supervisor.py) | 877-960 | 문자열 비교 15곳 수정 | 1시간 |
| [intent_analysis.txt](backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt) | 전체 | 15-category 프롬프트 병합 | 30분 |
| [agent_selection.txt](backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt) | 전체 | 15-category 매핑 병합 | 30분 |

#### Breaking Changes 요약

```python
# 1. 이름 변경 (코드 전체 영향)
LEGAL_CONSULT → LEGAL_INQUIRY

# 2. 값 변경 (문자열 비교 영향)
"법률상담" → "법률해설"
"시세조회" → "시세트렌드분석"
"계약서작성" → "계약서생성"
"irrelevant" → "무관"

# 3. 분할 (로직 영향)
LOAN_CONSULT → LOAN_SEARCH + LOAN_COMPARISON

# 4. 삭제 (참조 제거 필요)
CONTRACT_REVIEW (사용처: team_supervisor.py 2곳)
RISK_ANALYSIS (사용처: team_supervisor.py 2곳)

# 5. 신규 (패턴/매핑 추가 필요)
TERM_DEFINITION, BUILDING_REGISTRY, PROPERTY_INFRA_ANALYSIS,
PRICE_EVALUATION, PROPERTY_SEARCH, PROPERTY_RECOMMENDATION,
ROI_CALCULATION, POLICY_INQUIRY
```

---

## 🎯 구현 체크포인트 (6단계)

### Checkpoint 1: 백업 및 환경 설정 (30분)
**목표**: 안전한 작업 환경 구축
**작업**:
- Git 브랜치 생성: `feature/cognitive-merge-option-b-15-categories`
- 파일 백업: `backups/merge_251029/`
- 환경 검증: Python 3.8+, pytest 설치 확인

**완료 기준**:
```bash
✅ git branch --show-current  # feature/cognitive-merge-option-b-15-categories
✅ ls backups/merge_251029/   # planning_agent.py.bak 등 존재
✅ pytest --version            # 정상 출력
```

---

### Checkpoint 2: planning_agent.py 수정 (2시간)
**목표**: IntentType Enum 및 패턴 로직 업데이트
**작업**:
1. IntentType Enum 재구성 (32-51줄)
2. `_initialize_intent_patterns` 확장 (108-176줄)
3. `_analyze_with_patterns` 업데이트 (258-303줄)
4. `_suggest_agents` safe_defaults (305-397줄)
5. `_select_agents_with_llm` available_agents (399-469줄)
6. `_determine_strategy` 병렬/파이프라인 로직 (731-758줄)

**검증 스크립트**:
```python
# verify_checkpoint2.py
from backend.app.service_agent.cognitive_agents.planning_agent import IntentType

# 1. Enum 검증
assert hasattr(IntentType, 'LEGAL_INQUIRY'), "LEGAL_INQUIRY 없음"
assert hasattr(IntentType, 'LOAN_SEARCH'), "LOAN_SEARCH 없음"
assert hasattr(IntentType, 'LOAN_COMPARISON'), "LOAN_COMPARISON 없음"
assert not hasattr(IntentType, 'LEGAL_CONSULT'), "LEGAL_CONSULT 아직 존재"
assert not hasattr(IntentType, 'CONTRACT_REVIEW'), "CONTRACT_REVIEW 아직 존재"

# 2. 값 검증
assert IntentType.LEGAL_INQUIRY.value == "법률해설", f"값 오류: {IntentType.LEGAL_INQUIRY.value}"
assert IntentType.MARKET_INQUIRY.value == "시세트렌드분석", f"값 오류: {IntentType.MARKET_INQUIRY.value}"

# 3. 총 개수 검증
intent_count = len([m for m in dir(IntentType) if not m.startswith('_')])
assert intent_count == 17, f"IntentType 개수: {intent_count} (예상: 17)"

print("✅ Checkpoint 2 검증 완료")
```

**롤백 방법**:
```bash
git checkout backend/app/service_agent/cognitive_agents/planning_agent.py
# 또는
cp backups/merge_251029/planning_agent.py.bak backend/app/service_agent/cognitive_agents/planning_agent.py
```

---

### Checkpoint 3: team_supervisor.py 수정 (1시간)
**목표**: 문자열 비교 로직을 15-category 체계로 업데이트
**영향 범위**: [team_supervisor.py:877-960](backend/app/service_agent/supervisor/team_supervisor.py#L877-L960)

**수정 필요 위치 (15곳)**:
```python
# _get_task_name_for_agent (877-912줄)
- "legal_consult" → "법률해설"
- "loan_consult" → "대출상품검색" / "대출조건비교"
- "contract_review" → 삭제
+ "용어설명", "건축물대장조회", ... (8개 추가)

# _get_task_description_for_agent (914-960줄)
- 동일한 15개 문자열 매칭 수정
```

**검증 스크립트**:
```python
# verify_checkpoint3.py
from backend.app.service_agent.supervisor.team_supervisor import TeamSupervisor

supervisor = TeamSupervisor()

# 1. 새로운 intent 처리 검증
new_intents = [
    "용어설명", "법률해설", "대출상품검색", "대출조건비교",
    "건축물대장조회", "매물인프라분석", "가격평가", "매물검색",
    "맞춤추천", "투자수익률계산", "정부정책조회"
]

for intent in new_intents:
    task_name = supervisor._get_task_name_for_agent(intent, "search_team")
    assert task_name is not None, f"{intent} 처리 실패"
    print(f"✓ {intent}: {task_name}")

# 2. 삭제된 intent 처리 검증 (fallback 동작)
old_intents = ["contract_review", "risk_analysis"]
for intent in old_intents:
    task_name = supervisor._get_task_name_for_agent(intent, "search_team")
    print(f"⚠ {intent}: {task_name} (fallback)")

print("✅ Checkpoint 3 검증 완료")
```

---

### Checkpoint 4: 프롬프트 파일 병합 (1시간)
**목표**: LLM 프롬프트를 15-category 체계로 업데이트

**파일 1**: [intent_analysis.txt](backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt)
- **변경**: `tests/cognitive` 버전으로 대체
- **주요 차이**:
  - 15-category 의도 정의
  - Chat History 섹션 추가 (line 205-226)
  - `reuse_previous_data` 필드 추가

**파일 2**: [agent_selection.txt](backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt)
- **변경**: `tests/cognitive` 버전으로 대체
- **주요 차이**:
  - 15-category 매핑 테이블
  - Tool 유형별 분류 추가
  - search_team 도구 목록 확장

**검증 스크립트**:
```python
# verify_checkpoint4.py
from pathlib import Path

prompt_dir = Path("backend/app/service_agent/llm_manager/prompts/cognitive")

# 1. 파일 존재 확인
assert (prompt_dir / "intent_analysis.txt").exists()
assert (prompt_dir / "agent_selection.txt").exists()

# 2. 필수 키워드 검증
intent_prompt = (prompt_dir / "intent_analysis.txt").read_text(encoding='utf-8')
assert "TERM_DEFINITION" in intent_prompt, "TERM_DEFINITION 누락"
assert "LEGAL_INQUIRY" in intent_prompt, "LEGAL_INQUIRY 누락"
assert "reuse_previous_data" in intent_prompt, "reuse_previous_data 필드 누락"
assert "chat_history" in intent_prompt.lower(), "chat_history 변수 누락"

agent_prompt = (prompt_dir / "agent_selection.txt").read_text(encoding='utf-8')
assert "LOAN_SEARCH" in agent_prompt, "LOAN_SEARCH 누락"
assert "LOAN_COMPARISON" in agent_prompt, "LOAN_COMPARISON 누락"
assert "realestate_terminology" in agent_prompt, "새 도구 누락"

print("✅ Checkpoint 4 검증 완료")
```

---

### Checkpoint 5: 검증 및 테스트 (1.5시간)
**목표**: 통합 테스트 및 회귀 테스트

**테스트 시나리오**:
```python
# test_option_b_integration.py
import pytest
from backend.app.service_agent.cognitive_agents.planning_agent import PlanningAgent, IntentType

class TestOptionBIntegration:

    @pytest.fixture
    def planning_agent(self):
        return PlanningAgent()

    def test_intent_enum_structure(self):
        """IntentType Enum 구조 검증"""
        # 1. 총 개수 확인 (17개)
        all_intents = [m for m in dir(IntentType) if not m.startswith('_')]
        assert len(all_intents) == 17

        # 2. 필수 항목 존재 확인
        required = ['LEGAL_INQUIRY', 'LOAN_SEARCH', 'LOAN_COMPARISON',
                   'TERM_DEFINITION', 'ROI_CALCULATION']
        for intent in required:
            assert hasattr(IntentType, intent)

        # 3. 삭제된 항목 부재 확인
        deleted = ['LEGAL_CONSULT', 'CONTRACT_REVIEW', 'RISK_ANALYSIS']
        for intent in deleted:
            assert not hasattr(IntentType, intent)

    def test_intent_values(self):
        """IntentType 값 검증"""
        assert IntentType.LEGAL_INQUIRY.value == "법률해설"
        assert IntentType.LOAN_SEARCH.value == "대출상품검색"
        assert IntentType.MARKET_INQUIRY.value == "시세트렌드분석"
        assert IntentType.IRRELEVANT.value == "무관"

    @pytest.mark.asyncio
    async def test_new_intents_pattern_matching(self, planning_agent):
        """새로운 의도 패턴 매칭 테스트"""
        test_cases = [
            ("전세금이란 무엇인가요?", IntentType.TERM_DEFINITION),
            ("건축물대장 어떻게 확인하나요?", IntentType.BUILDING_REGISTRY),
            ("이 지역 학교 거리 알려줘", IntentType.PROPERTY_INFRA_ANALYSIS),
            ("이 집 적정 가격이야?", IntentType.PRICE_EVALUATION),
            ("강남 2억 아파트 찾아줘", IntentType.PROPERTY_SEARCH),
            ("내 조건에 맞는 집 추천해줘", IntentType.PROPERTY_RECOMMENDATION),
            ("투자 수익률 계산해줘", IntentType.ROI_CALCULATION),
            ("청년 주거 지원 정책 있어?", IntentType.POLICY_INQUIRY),
        ]

        for query, expected_intent in test_cases:
            result = await planning_agent.analyze_intent(query)
            assert result.intent == expected_intent, \
                f"Query: '{query}' | Expected: {expected_intent} | Got: {result.intent}"

    @pytest.mark.asyncio
    async def test_loan_consult_split(self, planning_agent):
        """LOAN_CONSULT 분할 검증"""
        # 대출 상품 검색
        result1 = await planning_agent.analyze_intent("전세대출 상품 알려줘")
        assert result1.intent == IntentType.LOAN_SEARCH

        # 대출 조건 비교
        result2 = await planning_agent.analyze_intent("A은행 vs B은행 대출 금리 비교")
        assert result2.intent == IntentType.LOAN_COMPARISON

    @pytest.mark.asyncio
    async def test_agent_suggestions(self, planning_agent):
        """Agent 제안 로직 테스트"""
        result = await planning_agent.analyze_intent("전세금이란?")
        assert "search_team" in result.suggested_agents

        result2 = await planning_agent.analyze_intent("투자 수익률 계산")
        assert "analysis_team" in result2.suggested_agents

    def test_backward_compatibility(self):
        """하위 호환성 테스트 (유지된 항목)"""
        kept_intents = [
            (IntentType.COMPREHENSIVE, "종합분석"),
            (IntentType.CONTRACT_CREATION, "계약서생성"),
            (IntentType.UNCLEAR, "unclear"),
            (IntentType.ERROR, "error"),
        ]

        for intent, expected_value in kept_intents:
            assert intent.value == expected_value
```

**실행**:
```bash
# 1. 단위 테스트
pytest tests/test_option_b_integration.py -v

# 2. 기존 테스트 회귀 검증
pytest tests/ -k "cognitive" -v

# 3. 커버리지 확인
pytest tests/test_option_b_integration.py --cov=backend/app/service_agent/cognitive_agents
```

---

### Checkpoint 6: 배포 및 모니터링 (1시간)
**목표**: 프로덕션 배포 및 초기 모니터링

**배포 절차**:
```bash
# 1. 최종 커밋
git add .
git commit -m "feat: Implement Option B - 15-category intent system

Breaking Changes:
- LEGAL_CONSULT → LEGAL_INQUIRY
- LOAN_CONSULT → LOAN_SEARCH + LOAN_COMPARISON
- Remove CONTRACT_REVIEW, RISK_ANALYSIS
- Add 8 new intent categories

Features:
- Term definition intent (TERM_DEFINITION)
- Building registry lookup (BUILDING_REGISTRY)
- Property infrastructure analysis (PROPERTY_INFRA_ANALYSIS)
- Price evaluation (PRICE_EVALUATION)
- Property search/recommendation (PROPERTY_SEARCH, PROPERTY_RECOMMENDATION)
- ROI calculation (ROI_CALCULATION)
- Policy inquiry (POLICY_INQUIRY)

Updated:
- planning_agent.py: IntentType Enum, pattern matching
- team_supervisor.py: String comparisons (15 locations)
- intent_analysis.txt: 15-category prompt
- agent_selection.txt: 15-category mappings

Tests: All passing (pytest tests/test_option_b_integration.py)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 2. 메인 브랜치 병합
git checkout main
git merge feature/cognitive-merge-option-b-15-categories

# 3. 태그 생성
git tag -a v1.0.0-intent-15-categories -m "Option B: 15-category intent system"

# 4. 원격 푸시 (선택적)
# git push origin main
# git push origin v1.0.0-intent-15-categories
```

**모니터링 체크리스트**:
```markdown
□ 로그 확인: intent 분류가 새 카테고리로 정상 동작하는지
□ 에러 모니터링: AttributeError (IntentType) 발생 여부
□ 성능 확인: 응답 시간 변화 (LLM 호출 증가 예상)
□ 사용자 피드백: 의도 분류 정확도 개선 확인
```

---

## 🔥 긴급 롤백 매뉴얼

### 전체 롤백 (Checkpoint 6 이후)
```bash
# 1. Git 되돌리기
git revert HEAD
git push origin main

# 2. 또는 브랜치 삭제 후 재시작
git checkout main
git branch -D feature/cognitive-merge-option-b-15-categories
git checkout -b feature/cognitive-merge-option-b-15-categories
```

### 부분 롤백 (특정 파일만)
```bash
# planning_agent.py만 되돌리기
git checkout HEAD~1 -- backend/app/service_agent/cognitive_agents/planning_agent.py
git commit -m "revert: Rollback planning_agent.py changes"

# 프롬프트 파일만 되돌리기
git checkout HEAD~1 -- backend/app/service_agent/llm_manager/prompts/cognitive/
git commit -m "revert: Rollback prompt files"
```

### 백업 파일 복원
```bash
# 백업에서 복원
cp backups/merge_251029/planning_agent.py.bak \
   backend/app/service_agent/cognitive_agents/planning_agent.py

cp backups/merge_251029/team_supervisor.py.bak \
   backend/app/service_agent/supervisor/team_supervisor.py

git add .
git commit -m "fix: Restore from backup files"
```

---

## 📈 예상 결과

### 긍정적 영향
1. **의도 분류 정밀도 향상**: 10 → 15 카테고리로 세분화
2. **도구 매핑 최적화**: 각 의도별 전용 도구 연결
3. **사용자 경험 개선**: 더 정확한 응답 제공
4. **확장성 확보**: 새 기능 추가 용이

### 주의 사항
1. **LLM 호출 증가**: 패턴 매칭 실패 시 LLM 의존도 증가 → 비용 상승 가능
2. **프롬프트 엔지니어링**: 15-category 구분을 LLM이 정확히 이해하도록 지속 개선 필요
3. **초기 모니터링 필수**: 의도 분류 오류 발생 시 즉시 조정

---

## ✅ 구현 준비 완료 체크리스트

- [x] Option B 정밀 실행 계획서 작성
- [x] IntentType 변경 내역 상세 분석
- [x] team_supervisor.py 수정 위치 15곳 특정
- [x] 프롬프트 파일 차이 분석 완료
- [x] 검증 스크립트 6개 작성
- [x] 롤백 절차 문서화
- [x] Git 커밋 메시지 준비
- [x] 테스트 시나리오 작성

---

## 🚀 다음 단계

**사용자 결정 대기 중**

Option B 구현을 시작하려면 다음 명령을 확인하세요:

```bash
# Checkpoint 1 시작
git checkout -b feature/cognitive-merge-option-b-15-categories
mkdir -p backups/merge_251029
cp backend/app/service_agent/cognitive_agents/planning_agent.py backups/merge_251029/planning_agent.py.bak
cp backend/app/service_agent/supervisor/team_supervisor.py backups/merge_251029/team_supervisor.py.bak
```

**예상 총 소요 시간**: 7시간
**권장 실행 시간대**: 업무 외 시간 (테스트 충분히 확보)
**필수 인원**: 개발자 1명 + QA 1명 (검증용)

---

**문서 작성**: Claude Code
**참조 문서**: [option_B_precise_execution_plan_251029.md](reports/merge/option_B_precise_execution_plan_251029.md)
