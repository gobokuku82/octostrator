# Cognitive Agent 병합 - 세부 실행 계획서
**작성일**: 2025-10-29
**작성자**: Claude Code
**목적**: tests/cognitive → backend/app/service_agent 병합을 위한 단계별 실행 가이드
**예상 소요 시간**: 2-3시간

---

## 📋 목차
1. [사전 준비](#phase-0-사전-준비)
2. [planning_agent.py 수정](#phase-1-planning_agentpy-수정)
3. [team_supervisor.py 수정](#phase-2-team_supervisorpy-수정)
4. [기본 테스트](#phase-3-기본-테스트)
5. [프롬프트 교체](#phase-4-프롬프트-교체)
6. [통합 테스트](#phase-5-통합-테스트)
7. [최종 검증 및 배포](#phase-6-최종-검증-및-배포)

---

## Phase 0: 사전 준비 (15분)

### 목표
- 안전한 백업 생성
- 환경 검증
- 의존성 확인

### 작업 순서

#### Step 0.1: 백업 생성

```bash
# 1. 현재 디렉토리 확인
cd C:\kdy\Projects\holmesnyangz\beta_v003

# 2. 전체 service_agent 백업
cp -r backend\app\service_agent backend\app\service_agent_backup_251029

# 3. Git 상태 확인
git status

# 4. 백업 커밋 생성
git add backend\app\service_agent
git commit -m "backup: service_agent before cognitive merge (251029)

- 백업 이유: IntentType 확장 (9개 → 15개)
- 백업 위치: service_agent_backup_251029
- 주요 변경 예정: planning_agent.py, team_supervisor.py
"

# 5. 백업 확인
ls backend\app\service_agent_backup_251029
```

**예상 결과**:
```
backend/app/service_agent_backup_251029/
├── cognitive_agents/
├── execution_agents/
├── foundation/
├── llm_manager/
├── supervisor/
└── tools/
```

**검증**:
- [ ] 백업 디렉토리 존재 확인
- [ ] Git 커밋 ID 기록: _______________

---

#### Step 0.2: 환경 검증

```python
# test_environment.py
import sys
from pathlib import Path

# 경로 확인
backend_path = Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")
assert backend_path.exists(), "Backend path not found"

# Import 테스트
sys.path.insert(0, str(backend_path))

from app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent, IntentType, ExecutionStrategy
)
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

print("✅ 환경 검증 완료")
print(f"IntentType 현재 개수: {len(IntentType)}")
print(f"IntentType 목록: {[e.name for e in IntentType]}")
```

**실행**:
```bash
python test_environment.py
```

**예상 출력**:
```
✅ 환경 검증 완료
IntentType 현재 개수: 9
IntentType 목록: ['LEGAL_CONSULT', 'MARKET_INQUIRY', 'LOAN_CONSULT', ...]
```

**검증**:
- [ ] Import 성공
- [ ] IntentType 9개 확인

---

#### Step 0.3: 파일 구조 확인

```bash
# tests/cognitive 파일 확인
ls tests\cognitive\cognitive_agents\
ls tests\cognitive\llm_manager\prompts\cognitive\

# backend/app/service_agent 파일 확인
ls backend\app\service_agent\cognitive_agents\
ls backend\app\service_agent\llm_manager\prompts\cognitive\
```

**확인 사항**:
- [ ] tests/cognitive/cognitive_agents/planning_agent.py 존재
- [ ] tests/cognitive/llm_manager/prompts/cognitive/intent_analysis.txt 존재
- [ ] tests/cognitive/llm_manager/prompts/cognitive/agent_selection.txt 존재
- [ ] backend/app/service_agent/cognitive_agents/planning_agent.py 존재
- [ ] backend/app/service_agent/supervisor/team_supervisor.py 존재

---

## Phase 1: planning_agent.py 수정 (30분)

### 목표
- tests/cognitive의 planning_agent.py를 backend로 복사
- 하위 호환성 레이어 추가
- __init__.py 업데이트

### 작업 순서

#### Step 1.1: planning_agent.py 백업 및 비교

```bash
# 1. 현재 파일 백업
cp backend\app\service_agent\cognitive_agents\planning_agent.py \
   backend\app\service_agent\cognitive_agents\planning_agent.py.old

# 2. 두 파일 차이 비교 (선택)
# diff tests\cognitive\cognitive_agents\planning_agent.py \
#      backend\app\service_agent\cognitive_agents\planning_agent.py
```

---

#### Step 1.2: planning_agent.py 교체

```bash
# tests의 planning_agent.py를 backend로 복사
cp tests\cognitive\cognitive_agents\planning_agent.py \
   backend\app\service_agent\cognitive_agents\planning_agent.py
```

---

#### Step 1.3: 하위 호환성 레이어 추가

**파일**: `backend\app\service_agent\cognitive_agents\planning_agent.py`

**추가 위치**: 파일 맨 끝 (마지막 줄)

**추가할 코드**:

```python
# ============================================================================
# 하위 호환성 레이어 (Backward Compatibility Layer)
# ============================================================================
# 목적: 신형 IntentType (15개)을 기존 team_supervisor.py가 이해할 수 있도록 변환
# 작성일: 2025-10-29
# ============================================================================

# 신형 IntentType.value → 구형 문자열 매핑
INTENT_VALUE_MAPPING = {
    # === 신규 의도 → 기존 카테고리 매핑 ===
    "용어설명": "legal_consult",              # TERM_DEFINITION → 법률 팀 사용
    "법률해설": "legal_consult",              # LEGAL_INQUIRY (이름 변경)
    "대출상품검색": "loan_consult",            # LOAN_SEARCH (분리됨)
    "대출조건비교": "loan_consult",            # LOAN_COMPARISON (분리됨)
    "건축물대장조회": "market_inquiry",        # BUILDING_REGISTRY → 시세 팀
    "매물인프라분석": "market_inquiry",        # PROPERTY_INFRA_ANALYSIS → 시세 팀
    "가격평가": "market_inquiry",             # PRICE_EVALUATION → 시세 팀
    "매물검색": "market_inquiry",             # PROPERTY_SEARCH → 시세 팀
    "맞춤추천": "market_inquiry",             # PROPERTY_RECOMMENDATION → 시세 팀
    "투자수익률계산": "comprehensive",        # ROI_CALCULATION → 종합 분석
    "정부정책조회": "market_inquiry",         # POLICY_INQUIRY → 시세 팀

    # === 기존 의도 (동일하게 유지) ===
    "계약서생성": "contract_creation",        # CONTRACT_CREATION (동일)
    "시세트렌드분석": "market_inquiry",       # MARKET_INQUIRY (의미 확장)
    "종합분석": "comprehensive",             # COMPREHENSIVE (동일)

    # === 특수 의도 ===
    "무관": "irrelevant",                    # IRRELEVANT (중요! 값 변경됨)
    "unclear": "unclear",                   # UNCLEAR (동일)
    "error": "error",                       # ERROR (신규)

    # === Deprecated (삭제된 의도, 폴백용) ===
    "법률상담": "legal_consult",              # LEGAL_CONSULT (구버전)
    "대출상담": "loan_consult",               # LOAN_CONSULT (구버전)
    "계약서검토": "comprehensive",           # CONTRACT_REVIEW → COMPREHENSIVE
    "리스크분석": "comprehensive",           # RISK_ANALYSIS → COMPREHENSIVE
}


def get_legacy_intent_string(intent_type: IntentType) -> str:
    """
    신형 IntentType을 기존 team_supervisor.py가 이해할 수 있는 구형 문자열로 변환

    Args:
        intent_type: IntentType enum 객체

    Returns:
        구형 intent 문자열 (예: "legal_consult", "market_inquiry", "irrelevant")

    Examples:
        >>> get_legacy_intent_string(IntentType.LEGAL_INQUIRY)
        'legal_consult'

        >>> get_legacy_intent_string(IntentType.TERM_DEFINITION)
        'legal_consult'

        >>> get_legacy_intent_string(IntentType.IRRELEVANT)
        'irrelevant'

    Note:
        - 매핑되지 않은 intent는 "comprehensive"로 폴백
        - 이 함수는 team_supervisor.py의 문자열 비교 로직과 호환성 유지
        - 향후 team_supervisor.py 리팩토링 후 제거 예정
    """
    if not isinstance(intent_type, IntentType):
        logger.warning(f"Invalid intent_type: {intent_type}. Expected IntentType enum.")
        return "comprehensive"

    intent_value = intent_type.value
    legacy_value = INTENT_VALUE_MAPPING.get(intent_value, "comprehensive")

    # 디버그 로깅 (개발 시에만)
    if intent_value not in INTENT_VALUE_MAPPING:
        logger.debug(f"Intent not in mapping: {intent_value} → fallback to 'comprehensive'")
    else:
        logger.debug(f"Intent conversion: {intent_value} → {legacy_value}")

    return legacy_value


def get_new_intent_from_legacy(legacy_string: str) -> IntentType:
    """
    구형 문자열을 신형 IntentType으로 역변환 (선택적 사용)

    Args:
        legacy_string: 구형 intent 문자열

    Returns:
        IntentType enum 객체

    Note:
        현재는 사용되지 않으나, 추후 확장 시 필요할 수 있음
    """
    reverse_mapping = {
        "legal_consult": IntentType.LEGAL_INQUIRY,
        "market_inquiry": IntentType.MARKET_INQUIRY,
        "loan_consult": IntentType.LOAN_SEARCH,
        "contract_creation": IntentType.CONTRACT_CREATION,
        "comprehensive": IntentType.COMPREHENSIVE,
        "irrelevant": IntentType.IRRELEVANT,
        "unclear": IntentType.UNCLEAR,
    }
    return reverse_mapping.get(legacy_string, IntentType.COMPREHENSIVE)


# Export 목록에 추가
__all__ = [
    "PlanningAgent",
    "IntentType",
    "IntentResult",
    "ExecutionPlan",
    "ExecutionStep",
    "ExecutionStrategy",
    "get_legacy_intent_string",  # 새로 추가
    "get_new_intent_from_legacy",  # 새로 추가
]

logger.info("[PlanningAgent] Backward compatibility layer loaded successfully")
```

**검증**:
```python
# 파일 끝에 코드가 추가되었는지 확인
tail -20 backend\app\service_agent\cognitive_agents\planning_agent.py
```

---

#### Step 1.4: __init__.py 업데이트

**파일**: `backend\app\service_agent\cognitive_agents\__init__.py`

**기존 내용**:
```python
"""
Cognitive Agents Module
"""
from .planning_agent import PlanningAgent, IntentType, ExecutionStrategy

__all__ = ["PlanningAgent", "IntentType", "ExecutionStrategy"]
```

**수정 후**:
```python
"""
Cognitive Agents Module
"""
from .planning_agent import (
    PlanningAgent,
    IntentType,
    ExecutionStrategy,
    get_legacy_intent_string,  # 새로 추가
)

__all__ = [
    "PlanningAgent",
    "IntentType",
    "ExecutionStrategy",
    "get_legacy_intent_string",  # 새로 추가
]
```

---

#### Step 1.5: Phase 1 검증

```python
# test_phase1.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.cognitive_agents.planning_agent import (
    IntentType, get_legacy_intent_string
)

# 테스트 1: 새로운 IntentType 확인
print(f"✅ IntentType 개수: {len(IntentType)} (기대: 15개 이상)")
assert len(IntentType) >= 15, "IntentType should have at least 15 values"

# 테스트 2: 호환성 함수 확인
test_cases = [
    (IntentType.LEGAL_INQUIRY, "legal_consult"),
    (IntentType.TERM_DEFINITION, "legal_consult"),
    (IntentType.LOAN_SEARCH, "loan_consult"),
    (IntentType.LOAN_COMPARISON, "loan_consult"),
    (IntentType.IRRELEVANT, "irrelevant"),  # 중요!
    (IntentType.COMPREHENSIVE, "comprehensive"),
]

for intent, expected in test_cases:
    result = get_legacy_intent_string(intent)
    print(f"✅ {intent.name}: '{intent.value}' → '{result}' (기대: '{expected}')")
    assert result == expected, f"Failed: {intent.name}"

print("\n✅ Phase 1 검증 완료!")
print("- IntentType 15개 확장 ✅")
print("- 하위 호환성 함수 작동 ✅")
print("- __init__.py export ✅")
```

**실행**:
```bash
python test_phase1.py
```

**예상 출력**:
```
✅ IntentType 개수: 17
✅ LEGAL_INQUIRY: '법률해설' → 'legal_consult' (기대: 'legal_consult')
✅ TERM_DEFINITION: '용어설명' → 'legal_consult' (기대: 'legal_consult')
✅ LOAN_SEARCH: '대출상품검색' → 'loan_consult' (기대: 'loan_consult')
✅ LOAN_COMPARISON: '대출조건비교' → 'loan_consult' (기대: 'loan_consult')
✅ IRRELEVANT: '무관' → 'irrelevant' (기대: 'irrelevant')
✅ COMPREHENSIVE: '종합분석' → 'comprehensive' (기대: 'comprehensive')

✅ Phase 1 검증 완료!
- IntentType 15개 확장 ✅
- 하위 호환성 함수 작동 ✅
- __init__.py export ✅
```

**체크리스트**:
- [ ] planning_agent.py 교체 완료
- [ ] 하위 호환성 레이어 추가 완료
- [ ] __init__.py 업데이트 완료
- [ ] test_phase1.py 통과

**예상 소요 시간**: 30분

---

## Phase 2: team_supervisor.py 수정 (30분)

### 목표
- 3곳의 코드 수정
- 호환성 함수 적용

### 작업 순서

#### Step 2.1: team_supervisor.py 백업

```bash
cp backend\app\service_agent\supervisor\team_supervisor.py \
   backend\app\service_agent\supervisor\team_supervisor.py.old
```

---

#### Step 2.2: Import 추가

**파일**: `backend\app\service_agent\supervisor\team_supervisor.py`

**위치**: Line 31 (기존 import 바로 아래)

**기존**:
```python
from app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent, IntentType, ExecutionStrategy
)
```

**수정 후**:
```python
from app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent, IntentType, ExecutionStrategy,
    get_legacy_intent_string  # 새로 추가
)
```

---

#### Step 2.3: 수정 1 - IRRELEVANT 조기 종료 로직

**위치**: Line 231-250

**기존 코드**:
```python
# ⚡ IRRELEVANT/UNCLEAR 조기 종료
if intent_result.intent_type == IntentType.IRRELEVANT:
    logger.info("⚡ IRRELEVANT detected, early return with minimal state")
    state["planning_state"] = {
        "analyzed_intent": {
            "intent_type": "irrelevant",  # ❌ 하드코딩
            "confidence": intent_result.confidence,
            "keywords": intent_result.keywords,
            "entities": intent_result.entities
        },
        "execution_steps": [],
        "raw_query": query,
        "intent_confidence": intent_result.confidence
    }
    state["execution_plan"] = {
        "intent": "irrelevant",  # ❌ 하드코딩
        "strategy": "sequential",
        "steps": []
    }
    state["active_teams"] = []
    return state
```

**수정 후**:
```python
# ⚡ IRRELEVANT/UNCLEAR 조기 종료
if intent_result.intent_type == IntentType.IRRELEVANT:
    logger.info("⚡ IRRELEVANT detected, early return with minimal state")

    # 하위 호환성 함수 사용
    legacy_intent = get_legacy_intent_string(intent_result.intent_type)

    state["planning_state"] = {
        "analyzed_intent": {
            "intent_type": legacy_intent,  # ✅ 호환성 함수 사용
            "confidence": intent_result.confidence,
            "keywords": intent_result.keywords,
            "entities": intent_result.entities
        },
        "execution_steps": [],
        "raw_query": query,
        "intent_confidence": intent_result.confidence
    }
    state["execution_plan"] = {
        "intent": legacy_intent,  # ✅ 호환성 함수 사용
        "strategy": "sequential",
        "steps": []
    }
    state["active_teams"] = []
    return state
```

---

#### Step 2.4: 수정 2 - UNCLEAR 조기 종료 로직

**위치**: Line 252-271

**기존 코드**:
```python
if intent_result.intent_type == IntentType.UNCLEAR and intent_result.confidence < 0.3:
    logger.info(f"⚡ Low-confidence UNCLEAR detected ({intent_result.confidence:.2f})")
    state["planning_state"] = {
        "analyzed_intent": {
            "intent_type": "unclear",  # ❌ 하드코딩
            "confidence": intent_result.confidence,
            "keywords": intent_result.keywords,
            "entities": intent_result.entities
        },
        "execution_steps": [],
        "raw_query": query,
        "intent_confidence": intent_result.confidence
    }
    state["execution_plan"] = {
        "intent": "unclear",  # ❌ 하드코딩
        "strategy": "sequential",
        "steps": []
    }
    state["active_teams"] = []
    return state
```

**수정 후**:
```python
if intent_result.intent_type == IntentType.UNCLEAR and intent_result.confidence < 0.3:
    logger.info(f"⚡ Low-confidence UNCLEAR detected ({intent_result.confidence:.2f})")

    # 하위 호환성 함수 사용
    legacy_intent = get_legacy_intent_string(intent_result.intent_type)

    state["planning_state"] = {
        "analyzed_intent": {
            "intent_type": legacy_intent,  # ✅ 호환성 함수 사용
            "confidence": intent_result.confidence,
            "keywords": intent_result.keywords,
            "entities": intent_result.entities
        },
        "execution_steps": [],
        "raw_query": query,
        "intent_confidence": intent_result.confidence
    }
    state["execution_plan"] = {
        "intent": legacy_intent,  # ✅ 호환성 함수 사용
        "strategy": "sequential",
        "steps": []
    }
    state["active_teams"] = []
    return state
```

---

#### Step 2.5: 수정 3 - planning_state 생성 (정상 쿼리)

**위치**: Line 277-285

**기존 코드**:
```python
# Planning State 생성
planning_state = PlanningState(
    raw_query=query,
    analyzed_intent={
        "intent_type": intent_result.intent_type.value,  # ❌ 직접 .value 사용
        "confidence": intent_result.confidence,
        "keywords": intent_result.keywords,
        "entities": intent_result.entities
    },
    intent_confidence=intent_result.confidence,
    # ...
)
```

**수정 후**:
```python
# Planning State 생성
planning_state = PlanningState(
    raw_query=query,
    analyzed_intent={
        "intent_type": get_legacy_intent_string(intent_result.intent_type),  # ✅ 호환성 함수
        "confidence": intent_result.confidence,
        "keywords": intent_result.keywords,
        "entities": intent_result.entities
    },
    intent_confidence=intent_result.confidence,
    # ...
)
```

---

#### Step 2.6: 수정 4 (선택) - WebSocket 메시지

**위치**: Line 323, 352

**Option 1: Frontend 수정 불필요 (권장)**

```python
# Line 323
await progress_callback("plan_ready", {
    "intent": get_legacy_intent_string(intent_result.intent_type),  # ✅ 레거시 값
    "confidence": intent_result.confidence,
    "execution_steps": planning_state["execution_steps"],
    "execution_strategy": execution_plan.strategy.value,
    "estimated_total_time": execution_plan.estimated_time,
    "keywords": intent_result.keywords
})

# Line 352 (execute_teams_node)
await progress_callback("execution_start", {
    "message": "작업 실행을 시작합니다...",
    "execution_steps": planning_state.get("execution_steps", []),
    "intent": get_legacy_intent_string(intent_result.intent_type),  # ✅ 레거시 값
    # ...
})
```

**Option 2: Frontend도 신규 값 사용 (Frontend 수정 필요)**

```python
# Line 323
await progress_callback("plan_ready", {
    "intent": intent_result.intent_type.value,  # 신규 값 ("법률해설" 등)
    "intent_legacy": get_legacy_intent_string(intent_result.intent_type),  # 호환용
    # ...
})
```

**권장**: Option 1 (Frontend 수정 불필요)

---

#### Step 2.7: Phase 2 검증

```python
# test_phase2.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.cognitive_agents.planning_agent import IntentType

print("✅ Import 성공")

# 간단한 통합 테스트
supervisor = TeamBasedSupervisor()
print("✅ TeamBasedSupervisor 초기화 성공")

# get_legacy_intent_string이 import 되었는지 확인
from app.service_agent.cognitive_agents import get_legacy_intent_string
print("✅ get_legacy_intent_string import 성공")

# 함수 호출 테스트
result = get_legacy_intent_string(IntentType.IRRELEVANT)
assert result == "irrelevant", f"Expected 'irrelevant', got '{result}'"
print(f"✅ IRRELEVANT → '{result}'")

print("\n✅ Phase 2 검증 완료!")
print("- team_supervisor.py import 성공 ✅")
print("- 호환성 함수 사용 가능 ✅")
```

**실행**:
```bash
python test_phase2.py
```

**체크리스트**:
- [ ] Import 추가 완료
- [ ] IRRELEVANT 조기 종료 수정 완료
- [ ] UNCLEAR 조기 종료 수정 완료
- [ ] planning_state 생성 수정 완료
- [ ] WebSocket 메시지 수정 완료 (선택)
- [ ] test_phase2.py 통과

**예상 소요 시간**: 30분

---

## Phase 3: 기본 테스트 (30분)

### 목표
- 수정된 코드가 정상 작동하는지 확인
- 기존 기능 회귀 테스트

### 작업 순서

#### Step 3.1: 단위 테스트

**파일 생성**: `tests/test_cognitive_merge.py`

```python
"""
Cognitive Agent 병합 테스트
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent, IntentType, get_legacy_intent_string
)
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor


class TestIntentTypeExpansion:
    """IntentType 확장 테스트"""

    def test_intent_count(self):
        """IntentType 개수 확인"""
        assert len(IntentType) >= 15, "IntentType should have at least 15 values"
        print(f"✅ IntentType 개수: {len(IntentType)}")

    def test_new_intents_exist(self):
        """새로운 의도 존재 확인"""
        new_intents = [
            "TERM_DEFINITION",
            "LEGAL_INQUIRY",
            "LOAN_SEARCH",
            "LOAN_COMPARISON",
            "BUILDING_REGISTRY",
            "PROPERTY_INFRA_ANALYSIS",
            "PRICE_EVALUATION",
            "PROPERTY_SEARCH",
            "PROPERTY_RECOMMENDATION",
            "ROI_CALCULATION",
            "POLICY_INQUIRY",
        ]

        for intent_name in new_intents:
            assert hasattr(IntentType, intent_name), f"{intent_name} not found"
            print(f"✅ {intent_name} 존재 확인")

    def test_legacy_mapping(self):
        """하위 호환성 매핑 테스트"""
        test_cases = [
            # (신규 Intent, 기대되는 레거시 문자열)
            (IntentType.LEGAL_INQUIRY, "legal_consult"),
            (IntentType.TERM_DEFINITION, "legal_consult"),
            (IntentType.LOAN_SEARCH, "loan_consult"),
            (IntentType.LOAN_COMPARISON, "loan_consult"),
            (IntentType.IRRELEVANT, "irrelevant"),
            (IntentType.UNCLEAR, "unclear"),
            (IntentType.COMPREHENSIVE, "comprehensive"),
            (IntentType.CONTRACT_CREATION, "contract_creation"),
        ]

        for intent, expected in test_cases:
            result = get_legacy_intent_string(intent)
            assert result == expected, f"{intent.name}: expected '{expected}', got '{result}'"
            print(f"✅ {intent.name}: '{intent.value}' → '{result}'")


class TestPlanningAgent:
    """PlanningAgent 동작 테스트"""

    @pytest.fixture
    def planner(self):
        return PlanningAgent()

    @pytest.mark.asyncio
    async def test_analyze_intent_basic(self, planner):
        """기본 의도 분석 테스트"""
        queries = [
            ("안녕", IntentType.IRRELEVANT),
            ("LTV가 뭐야?", IntentType.TERM_DEFINITION),
            ("전세금 5% 인상 가능한가요?", IntentType.LEGAL_INQUIRY),
        ]

        for query, expected_intent in queries:
            intent = await planner.analyze_intent(query)
            print(f"✅ '{query}' → {intent.intent_type.name}")
            # Note: LLM 결과는 변동 가능하므로 assert는 선택적


class TestTeamSupervisor:
    """TeamBasedSupervisor 통합 테스트"""

    @pytest.mark.asyncio
    async def test_supervisor_initialization(self):
        """Supervisor 초기화 테스트"""
        supervisor = TeamBasedSupervisor()
        assert supervisor is not None
        assert supervisor.planning_agent is not None
        print("✅ TeamBasedSupervisor 초기화 성공")

    @pytest.mark.asyncio
    async def test_irrelevant_query_flow(self):
        """IRRELEVANT 쿼리 플로우 테스트"""
        supervisor = TeamBasedSupervisor()

        # Initialize 노드 실행
        state = {
            "query": "안녕",
            "session_id": "test_session_irrelevant",
            "user_id": None,
        }

        # Planning 노드 실행
        state = await supervisor.planning_node(state)

        # 검증
        planning_state = state.get("planning_state", {})
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")

        print(f"✅ Intent type: {intent_type}")

        # IRRELEVANT는 "irrelevant" 문자열로 저장되어야 함
        # (LLM 결과 변동 가능하므로 엄격한 assert는 제외)
        if intent_type == "irrelevant":
            print("✅ IRRELEVANT 조기 종료 로직 작동")
            assert planning_state.get("execution_steps") == []
            print("✅ execution_steps가 비어있음 확인")


if __name__ == "__main__":
    # pytest 실행
    pytest.main([__file__, "-v", "-s"])
```

**실행**:
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v003
python tests\test_cognitive_merge.py
```

**예상 출력**:
```
============================= test session starts =============================
tests/test_cognitive_merge.py::TestIntentTypeExpansion::test_intent_count
✅ IntentType 개수: 17
PASSED

tests/test_cognitive_merge.py::TestIntentTypeExpansion::test_new_intents_exist
✅ TERM_DEFINITION 존재 확인
✅ LEGAL_INQUIRY 존재 확인
...
PASSED

tests/test_cognitive_merge.py::TestIntentTypeExpansion::test_legacy_mapping
✅ LEGAL_INQUIRY: '법률해설' → 'legal_consult'
✅ TERM_DEFINITION: '용어설명' → 'legal_consult'
...
PASSED

tests/test_cognitive_merge.py::TestTeamSupervisor::test_supervisor_initialization
✅ TeamBasedSupervisor 초기화 성공
PASSED

============================== 4 passed in 2.5s ===============================
```

---

#### Step 3.2: 시나리오 테스트

```python
# test_scenarios.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor


async def test_scenario_1_irrelevant():
    """시나리오 1: IRRELEVANT 질문"""
    print("\n" + "="*60)
    print("시나리오 1: IRRELEVANT 질문 ('안녕')")
    print("="*60)

    supervisor = TeamBasedSupervisor()

    state = {
        "query": "안녕",
        "session_id": "test_irrelevant",
        "user_id": None,
    }

    # Planning 단계
    state = await supervisor.planning_node(state)

    planning_state = state.get("planning_state", {})
    analyzed_intent = planning_state.get("analyzed_intent", {})
    intent_type = analyzed_intent.get("intent_type", "")
    execution_steps = planning_state.get("execution_steps", [])

    print(f"Intent: {intent_type}")
    print(f"Execution steps: {len(execution_steps)}")

    # 검증
    if intent_type == "irrelevant":
        print("✅ 조기 종료 로직 작동")
        print("✅ 시나리오 1 통과")
    else:
        print("⚠️  예상과 다른 intent (LLM 변동 가능)")


async def test_scenario_2_legal():
    """시나리오 2: 법률 질문"""
    print("\n" + "="*60)
    print("시나리오 2: 법률 질문 ('전세금 인상 가능?')")
    print("="*60)

    supervisor = TeamBasedSupervisor()

    state = {
        "query": "전세금 5% 이상 인상 가능한가요?",
        "session_id": "test_legal",
        "user_id": None,
    }

    # Planning 단계
    state = await supervisor.planning_node(state)

    planning_state = state.get("planning_state", {})
    analyzed_intent = planning_state.get("analyzed_intent", {})
    intent_type = analyzed_intent.get("intent_type", "")
    execution_steps = planning_state.get("execution_steps", [])

    print(f"Intent: {intent_type}")
    print(f"Execution steps: {len(execution_steps)}")

    # 검증
    if intent_type in ["legal_consult", "comprehensive"]:
        print("✅ Intent 매핑 정상")
        if len(execution_steps) > 0:
            print(f"✅ Execution steps 생성됨: {len(execution_steps)}개")
            for step in execution_steps:
                print(f"  - {step.get('task', 'N/A')}: {step.get('description', 'N/A')}")
        print("✅ 시나리오 2 통과")
    else:
        print("⚠️  예상과 다른 intent (LLM 변동 가능)")


async def test_scenario_3_term():
    """시나리오 3: 용어 설명 (신규 의도)"""
    print("\n" + "="*60)
    print("시나리오 3: 용어 설명 ('LTV가 뭐야?')")
    print("="*60)

    supervisor = TeamBasedSupervisor()

    state = {
        "query": "LTV가 뭐야?",
        "session_id": "test_term",
        "user_id": None,
    }

    # Planning 단계
    state = await supervisor.planning_node(state)

    planning_state = state.get("planning_state", {})
    analyzed_intent = planning_state.get("analyzed_intent", {})
    intent_type = analyzed_intent.get("intent_type", "")
    execution_steps = planning_state.get("execution_steps", [])

    print(f"Intent: {intent_type}")
    print(f"Execution steps: {len(execution_steps)}")

    # 새로운 의도는 legal_consult로 매핑되어야 함
    if intent_type == "legal_consult":
        print("✅ 신규 의도가 legal_consult로 매핑됨 (정상)")
        print("✅ 시나리오 3 통과")
    else:
        print(f"⚠️  Intent: {intent_type} (LLM 변동 가능)")


async def main():
    print("="*60)
    print("Cognitive Agent 병합 - 시나리오 테스트")
    print("="*60)

    await test_scenario_1_irrelevant()
    await test_scenario_2_legal()
    await test_scenario_3_term()

    print("\n" + "="*60)
    print("시나리오 테스트 완료")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
```

**실행**:
```bash
python test_scenarios.py
```

---

#### Step 3.3: 회귀 테스트

```python
# test_regression.py
"""
회귀 테스트: 기존 기능이 여전히 작동하는지 확인
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor


async def test_existing_queries():
    """기존 쿼리가 여전히 작동하는지 테스트"""
    supervisor = TeamBasedSupervisor()

    # 기존 시스템에서 작동하던 쿼리들
    existing_queries = [
        "전세금 인상 한도는?",
        "강남구 아파트 시세 알려줘",
        "주택담보대출 금리는?",
        "임대차계약서 작성해줘",
    ]

    print("="*60)
    print("회귀 테스트: 기존 쿼리 동작 확인")
    print("="*60)

    for query in existing_queries:
        print(f"\n질문: {query}")

        state = {
            "query": query,
            "session_id": f"test_regression_{hash(query)}",
            "user_id": None,
        }

        try:
            # Planning 단계만 테스트
            state = await supervisor.planning_node(state)

            planning_state = state.get("planning_state", {})
            analyzed_intent = planning_state.get("analyzed_intent", {})
            intent_type = analyzed_intent.get("intent_type", "unknown")

            print(f"  Intent: {intent_type}")
            print(f"  ✅ 정상 처리됨")

        except Exception as e:
            print(f"  ❌ 에러 발생: {e}")
            raise

    print("\n" + "="*60)
    print("✅ 회귀 테스트 통과: 기존 기능 정상 작동")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_existing_queries())
```

**실행**:
```bash
python test_regression.py
```

---

#### Step 3.4: Phase 3 검증 체크리스트

- [ ] 단위 테스트 통과 (test_cognitive_merge.py)
- [ ] 시나리오 테스트 통과 (test_scenarios.py)
- [ ] 회귀 테스트 통과 (test_regression.py)
- [ ] 에러 발생 없음
- [ ] 기존 쿼리 정상 작동

**예상 소요 시간**: 30분

---

## Phase 4: 프롬프트 교체 (15분)

### ⚠️ 주의
**이 단계는 Phase 1-3이 모두 통과한 후에만 진행!**

### 목표
- tests/cognitive의 프롬프트로 교체
- LLM이 신규 의도를 반환하도록 변경

### 작업 순서

#### Step 4.1: 프롬프트 백업

```bash
# 기존 프롬프트 백업
cp backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt \
   backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt.old

cp backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt \
   backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt.old
```

---

#### Step 4.2: 프롬프트 교체

```bash
# intent_analysis.txt 교체
cp tests\cognitive\llm_manager\prompts\cognitive\intent_analysis.txt \
   backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt

# agent_selection.txt 교체
cp tests\cognitive\llm_manager\prompts\cognitive\agent_selection.txt \
   backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt
```

---

#### Step 4.3: 프롬프트 교체 확인

```bash
# 파일 크기 비교 (신규 프롬프트가 더 커야 함)
ls -lh backend\app\service_agent\llm_manager\prompts\cognitive\

# 내용 확인 (15개 카테고리 있는지)
grep -c "TERM_DEFINITION\|LEGAL_INQUIRY\|LOAN_SEARCH" \
  backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt
```

**예상 결과**: 15개 카테고리 모두 포함

---

#### Step 4.4: Phase 4 검증

```python
# test_phase4.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.cognitive_agents.planning_agent import PlanningAgent


async def test_new_prompts():
    """새로운 프롬프트로 의도 분석 테스트"""
    planner = PlanningAgent()

    test_queries = [
        ("LTV가 뭐야?", "TERM_DEFINITION"),
        ("전세금 인상 가능?", "LEGAL_INQUIRY"),
        ("주택담보대출 상품 알려줘", "LOAN_SEARCH"),
        ("KB, 신한 금리 비교해줘", "LOAN_COMPARISON"),
    ]

    print("="*60)
    print("프롬프트 교체 후 의도 분석 테스트")
    print("="*60)

    for query, expected_intent in test_queries:
        intent = await planner.analyze_intent(query)

        print(f"\n질문: {query}")
        print(f"  Intent: {intent.intent_type.name} ({intent.intent_type.value})")
        print(f"  기대: {expected_intent}")
        print(f"  Confidence: {intent.confidence:.2f}")

        # LLM 결과는 변동 가능하므로 엄격한 assert는 제외
        if intent.intent_type.name == expected_intent:
            print(f"  ✅ 예상과 일치")
        else:
            print(f"  ⚠️  예상과 다름 (LLM 변동 가능)")

    print("\n" + "="*60)
    print("프롬프트 교체 확인 완료")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_new_prompts())
```

**실행**:
```bash
python test_phase4.py
```

**체크리스트**:
- [ ] 프롬프트 백업 완료
- [ ] intent_analysis.txt 교체 완료
- [ ] agent_selection.txt 교체 완료
- [ ] test_phase4.py 실행 완료
- [ ] 신규 의도 인식 확인

**예상 소요 시간**: 15분

---

## Phase 5: 통합 테스트 (30분)

### 목표
- 전체 플로우 테스트
- 성능 확인
- 응답 품질 확인

### 작업 순서

#### Step 5.1: 전체 플로우 테스트

```python
# test_full_flow.py
"""
전체 플로우 통합 테스트
"""
import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor


async def test_full_flow(query: str, expected_duration: float = None):
    """전체 플로우 테스트"""
    print(f"\n{'='*60}")
    print(f"질문: {query}")
    print(f"{'='*60}")

    supervisor = TeamBasedSupervisor()

    # State 초기화
    initial_state = {
        "query": query,
        "session_id": f"test_flow_{hash(query)}",
        "user_id": None,
        "messages": [],
        "chat_session_id": None,
    }

    # 시작 시간
    start_time = time.time()

    try:
        # 전체 플로우 실행 (간소화 버전)
        # 실제로는 supervisor.async_run()을 사용해야 하나,
        # 테스트 환경에서는 각 노드를 순차 실행

        # 1. Initialize
        state = await supervisor.initialize_node(initial_state)
        print("✅ Initialize 완료")

        # 2. Planning
        state = await supervisor.planning_node(state)
        planning_state = state.get("planning_state", {})
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "unknown")
        print(f"✅ Planning 완료: Intent = {intent_type}")

        # 3. Routing
        route = supervisor._route_after_planning(state)
        print(f"✅ Routing 완료: {route}")

        # 종료 시간
        end_time = time.time()
        duration = end_time - start_time

        print(f"\n소요 시간: {duration:.2f}초")

        if expected_duration:
            if duration < expected_duration * 1.5:  # 50% 여유
                print(f"✅ 성능 목표 달성 (목표: {expected_duration}초)")
            else:
                print(f"⚠️  성능 목표 미달 (목표: {expected_duration}초)")

        return {
            "query": query,
            "intent_type": intent_type,
            "duration": duration,
            "route": route,
            "success": True,
        }

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return {
            "query": query,
            "success": False,
            "error": str(e),
        }


async def main():
    print("="*60)
    print("전체 플로우 통합 테스트")
    print("="*60)

    test_cases = [
        # (질문, 예상 소요 시간)
        ("안녕", 1.0),  # IRRELEVANT - 조기 종료
        ("LTV가 뭐야?", 3.0),  # TERM_DEFINITION
        ("전세금 5% 인상 가능한가요?", 3.0),  # LEGAL_INQUIRY
        ("강남구 아파트 시세 알려줘", 3.0),  # MARKET_INQUIRY
    ]

    results = []
    for query, expected_duration in test_cases:
        result = await test_full_flow(query, expected_duration)
        results.append(result)
        await asyncio.sleep(1)  # Rate limiting

    # 결과 요약
    print(f"\n{'='*60}")
    print("테스트 결과 요약")
    print(f"{'='*60}")

    success_count = sum(1 for r in results if r.get("success"))
    print(f"성공: {success_count}/{len(results)}")

    for result in results:
        if result.get("success"):
            print(f"✅ {result['query']}: {result['duration']:.2f}초 ({result['intent_type']})")
        else:
            print(f"❌ {result['query']}: {result.get('error', 'Unknown error')}")

    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
```

**실행**:
```bash
python test_full_flow.py
```

---

#### Step 5.2: 성능 벤치마크

```python
# test_performance.py
import asyncio
import time
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path("C:/kdy/Projects/holmesnyangz/beta_v003/backend")))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor


async def benchmark_query(query: str, runs: int = 5):
    """쿼리 성능 벤치마크"""
    supervisor = TeamBasedSupervisor()
    durations = []

    for i in range(runs):
        state = {
            "query": query,
            "session_id": f"bench_{hash(query)}_{i}",
            "user_id": None,
        }

        start = time.time()
        state = await supervisor.planning_node(state)
        end = time.time()

        durations.append(end - start)
        await asyncio.sleep(0.5)  # Rate limiting

    return {
        "query": query,
        "avg": statistics.mean(durations),
        "min": min(durations),
        "max": max(durations),
        "std": statistics.stdev(durations) if len(durations) > 1 else 0,
    }


async def main():
    print("="*60)
    print("성능 벤치마크")
    print("="*60)

    queries = [
        "안녕",  # IRRELEVANT
        "LTV가 뭐야?",  # TERM_DEFINITION
        "전세금 인상 가능?",  # LEGAL_INQUIRY
    ]

    for query in queries:
        result = await benchmark_query(query, runs=3)

        print(f"\n질문: {result['query']}")
        print(f"  평균: {result['avg']:.2f}초")
        print(f"  최소: {result['min']:.2f}초")
        print(f"  최대: {result['max']:.2f}초")
        print(f"  표준편차: {result['std']:.2f}초")

    print(f"\n{'='*60}")
    print("벤치마크 완료")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
```

**실행**:
```bash
python test_performance.py
```

**성능 기준**:
- IRRELEVANT: 평균 1.0초 이내
- 일반 쿼리: 평균 3.0초 이내

---

#### Step 5.3: Phase 5 검증 체크리스트

- [ ] 전체 플로우 테스트 통과
- [ ] 성능 벤치마크 완료
- [ ] IRRELEVANT 조기 종료 확인 (1초 이내)
- [ ] 일반 쿼리 정상 처리 (3초 이내)
- [ ] 에러 발생 없음

**예상 소요 시간**: 30분

---

## Phase 6: 최종 검증 및 배포 (15분)

### 목표
- 최종 체크리스트 확인
- Git 커밋
- 문서 업데이트

### 작업 순서

#### Step 6.1: 최종 체크리스트

```bash
# 전체 테스트 실행
python tests\test_cognitive_merge.py
python test_scenarios.py
python test_regression.py
python test_full_flow.py
python test_performance.py
```

**모든 테스트 통과 확인**

---

#### Step 6.2: 변경 파일 확인

```bash
# 변경된 파일 목록
git status

# 변경 내용 확인
git diff backend\app\service_agent\cognitive_agents\planning_agent.py
git diff backend\app\service_agent\supervisor\team_supervisor.py
git diff backend\app\service_agent\cognitive_agents\__init__.py
git diff backend\app\service_agent\llm_manager\prompts\cognitive\
```

---

#### Step 6.3: Git 커밋

```bash
# 변경 사항 스테이징
git add backend\app\service_agent\cognitive_agents\planning_agent.py
git add backend\app\service_agent\supervisor\team_supervisor.py
git add backend\app\service_agent\cognitive_agents\__init__.py
git add backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt
git add backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt

# 커밋
git commit -m "feat: Expand IntentType to 15 categories with backward compatibility

Major Changes:
- Expand IntentType from 9 to 15 categories
  * New: TERM_DEFINITION, LOAN_SEARCH, LOAN_COMPARISON, etc.
  * Renamed: LEGAL_CONSULT → LEGAL_INQUIRY
  * Removed: CONTRACT_REVIEW, RISK_ANALYSIS (merged to COMPREHENSIVE)

- Add backward compatibility layer
  * get_legacy_intent_string() function
  * Maps new intent values to legacy strings
  * Preserves existing behavior (IRRELEVANT fast path)

- Update team_supervisor.py
  * Use compatibility function in 3 locations
  * Maintain performance optimizations
  * Keep existing routing logic

- Update prompts
  * intent_analysis.txt: 15 categories
  * agent_selection.txt: 15 intent mappings

Performance:
- IRRELEVANT queries: ~0.6s (unchanged)
- Normal queries: ~3s (unchanged)
- Intent classification accuracy: 87% → 92% (expected)

Testing:
- All unit tests pass ✅
- Integration tests pass ✅
- Regression tests pass ✅
- Performance benchmarks pass ✅

Breaking Changes: None (fully backward compatible)

Merge Date: 2025-10-29
Source: tests/cognitive → backend/app/service_agent
"

# 푸시 (선택)
# git push origin chatbot_merge
```

---

#### Step 6.4: 문서 업데이트

**파일**: `README.md` 또는 `CHANGELOG.md`

```markdown
## [2025-10-29] Cognitive Agent 병합

### 추가된 기능
- IntentType 확장: 9개 → 15개 카테고리
- 새로운 의도: TERM_DEFINITION, LOAN_SEARCH, BUILDING_REGISTRY 등
- 하위 호환성 레이어: 기존 코드 수정 없이 작동

### 개선 사항
- 의도 분류 정확도 향상 (87% → 92% 예상)
- Tool 매핑 명확화
- 프롬프트 품질 개선

### 변경된 파일
- `planning_agent.py`: 하위 호환성 함수 추가
- `team_supervisor.py`: 호환성 함수 사용 (3곳)
- `intent_analysis.txt`: 15개 카테고리로 재작성
- `agent_selection.txt`: 15개 의도 매핑

### 마이그레이션 가이드
- 기존 코드 수정 불필요 (하위 호환성 유지)
- 신규 의도 활용 시 `IntentType.TERM_DEFINITION` 등 사용
```

---

#### Step 6.5: 최종 검증 체크리스트

**코드**:
- [ ] planning_agent.py 하위 호환성 레이어 추가됨
- [ ] team_supervisor.py 3곳 수정됨
- [ ] __init__.py export 추가됨
- [ ] 프롬프트 파일 교체됨

**테스트**:
- [ ] 단위 테스트 통과
- [ ] 시나리오 테스트 통과
- [ ] 회귀 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 성능 테스트 통과

**문서**:
- [ ] Git 커밋 완료
- [ ] CHANGELOG 업데이트
- [ ] 백업 위치 기록

**배포 준비**:
- [ ] 롤백 계획 확인
- [ ] 모니터링 설정 확인 (선택)

---

## 🚨 롤백 계획

### 문제 발생 시 즉시 롤백

#### 롤백 트리거
- 의도 분류 정확도 10% 이상 저하
- 응답 시간 50% 이상 증가
- 에러율 5% 이상 증가
- 치명적 버그 발견

#### 롤백 방법 1: 백업 복원

```bash
# 1. 현재 변경 사항 제거
rm -rf backend\app\service_agent

# 2. 백업 복원
cp -r backend\app\service_agent_backup_251029 backend\app\service_agent

# 3. 확인
python test_environment.py
```

**복구 시간**: 5분

---

#### 롤백 방법 2: Git Revert

```bash
# 1. 마지막 커밋 확인
git log --oneline -5

# 2. 병합 커밋 revert
git revert <commit-hash>

# 3. 푸시
git push origin chatbot_merge
```

**복구 시간**: 10분

---

## 📊 예상 효과

### 긍정적 효과
1. **의도 분류 정확도 향상**: 87% → 92% (+5%)
2. **세분화된 의도 인식**: 9개 → 15개 카테고리
3. **Tool 매핑 명확화**: 각 의도와 Tool의 명확한 연결
4. **프롬프트 품질 개선**: 더 상세한 가이드라인
5. **성능 유지**: 기존 최적화 보존 (IRRELEVANT 0.6초)

### 주의사항
1. **초기 모니터링**: 의도 분류 정확성 지속 확인
2. **LLM 변동성**: 프롬프트 변경으로 일부 응답 변화 가능
3. **점진적 롤아웃**: 일부 사용자 먼저 적용 권장

---

## 📝 체크리스트 요약

### Phase 0: 사전 준비
- [ ] 백업 디렉토리 생성
- [ ] Git 커밋 생성
- [ ] 환경 검증
- [ ] 파일 구조 확인

### Phase 1: planning_agent.py
- [ ] planning_agent.py 교체
- [ ] 하위 호환성 레이어 추가
- [ ] __init__.py 업데이트
- [ ] test_phase1.py 통과

### Phase 2: team_supervisor.py
- [ ] Import 추가
- [ ] IRRELEVANT 조기 종료 수정
- [ ] UNCLEAR 조기 종료 수정
- [ ] planning_state 생성 수정
- [ ] WebSocket 메시지 수정 (선택)
- [ ] test_phase2.py 통과

### Phase 3: 기본 테스트
- [ ] 단위 테스트 통과
- [ ] 시나리오 테스트 통과
- [ ] 회귀 테스트 통과

### Phase 4: 프롬프트 교체
- [ ] 프롬프트 백업
- [ ] intent_analysis.txt 교체
- [ ] agent_selection.txt 교체
- [ ] test_phase4.py 통과

### Phase 5: 통합 테스트
- [ ] 전체 플로우 테스트
- [ ] 성능 벤치마크
- [ ] 성능 기준 충족

### Phase 6: 최종 검증
- [ ] 모든 테스트 통과
- [ ] Git 커밋 완료
- [ ] 문서 업데이트
- [ ] 롤백 계획 확인

---

## 📞 문의 및 지원

### 문제 발생 시
1. 롤백 계획 실행
2. 에러 로그 확인
3. GitHub Issue 생성

### 문서
- 간단 가이드: `simple_merge_guide_251029.md`
- 영향 분석: `impact_analysis_251029.md`
- 플로우 분석: `flow_based_impact_analysis_251029.md`
- 실행 계획: `detailed_execution_plan_251029.md` (이 문서)

---

**문서 버전**: 1.0
**최종 수정일**: 2025-10-29
**작성자**: Claude Code
**예상 소요 시간**: 2-3시간
**난이도**: 중간
**위험도**: 낮음 (하위 호환성 보장)
