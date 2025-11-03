# 3-Way Merge 상세 분석 보고서

**분석일**: 2025-10-30
**분석자**: Claude Code
**프로젝트**: beta_v001
**분기 시점**: original_base/

---

## 🎯 역사 (History)

```
original_base/ (분기 시작점)
    ├─→ Branch 1: backend/ (improve팀, chatbot_improve)
    │   └─ 버그 수정 + 기능 개선
    │
    └─→ Branch 2: tests/backend/ (execute팀, chatbot_execute)
        └─ 신규 tools 추가 + 기능 확장

→ Merge: backend/ ← (Branch 1 + Branch 2)
```

---

## 📊 파일별 변경사항 분석

### ✅ 충돌 없음 (3개) - Execute만 수정

| 파일 | Base | Improve | Execute | 결론 |
|------|------|---------|---------|------|
| **infrastructure_tool.py** | 438줄 | 438줄 (변경 없음) | 530줄 (+92줄) | ✅ tests 채택 |
| **real_estate_search_tool.py** | 352줄 | 352줄 (변경 없음) | 411줄 (+59줄) | ✅ tests 채택 |
| **agent_registry.py** | - | - (변경 없음) | JSON 출력 개선 | ✅ tests 채택 |

**병합 방법:**
```bash
# 충돌 없으니 그냥 복사!
cp tests/backend/app/service_agent/tools/infrastructure_tool.py \
   backend/app/service_agent/tools/

cp tests/backend/app/service_agent/tools/real_estate_search_tool.py \
   backend/app/service_agent/tools/

cp tests/backend/app/service_agent/foundation/agent_registry.py \
   backend/app/service_agent/foundation/
```

---

### 🔀 3-Way Merge 필요 (3개) - 양쪽 모두 수정

#### 1️⃣ search_executor.py (Critical) 🔥

| 버전 | 줄 수 | 변경량 |
|------|-------|--------|
| **original_base** | 948줄 | (기준) |
| **backend (improve)** | 1021줄 | **+73줄** ⭐ |
| **tests (execute)** | 1296줄 | **+348줄** ⭐ |

**Improve팀 변경사항 (+73줄):**
- ✅ `progress_callback` 파라미터 추가 (WebSocket 실시간 진행률)
- ✅ `_update_step_progress` 메서드 추가
- ✅ Progress 관련 로직 강화

**Execute팀 변경사항 (+348줄):**
- ✅ 신규 tool 속성 3개 추가
  - `self.building_registry_tool`
  - `self.infrastructure_tool`
  - `self.terminology_tool`
- ✅ 신규 tool 초기화 코드 (대규모)
- ✅ LegalSearch 사용 (HybridLegalSearch 대체)
- ✅ `_get_available_tools` 확장

**병합 전략:**
```python
# ✅ 최종 목표: Improve 아키텍처 + Execute 신규 tools

def __init__(self, llm_context=None, progress_callback=None):  # ← Improve 유지
    self.progress_callback = progress_callback  # ← Improve 유지

    # 기존 tools
    self.legal_search_tool = None
    # ... 기존 tools

    # ← Execute 추가
    self.building_registry_tool = None
    self.infrastructure_tool = None
    self.terminology_tool = None

    # LegalSearch 초기화 (Execute 방식) + Fallback (Improve 방식)
    try:
        from app.service_agent.tools.legal_search_tool import LegalSearch
        self.legal_search_tool = LegalSearch()
    except Exception as e:
        # Fallback to HybridLegalSearch
        from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
        self.legal_search_tool = HybridLegalSearch()
```

**난이도:** 🔴 **높음** (양쪽 대규모 수정)

---

#### 2️⃣ analysis_executor.py (Medium)

| 버전 | 줄 수 | 변경량 |
|------|-------|--------|
| **original_base** | 973줄 | (기준) |
| **backend (improve)** | 1049줄 | **+76줄** ⭐ |
| **tests (execute)** | 1023줄 | **+50줄** ⭐ |

**Improve팀 변경사항 (+76줄):**
- ✅ `progress_callback` 파라미터 추가
- ✅ Progress 관련 로직 추가
- ✅ 기타 버그 수정 및 개선

**Execute팀 변경사항 (+50줄):**
- ✅ LegalSearch tool 추가
- ✅ `_get_available_analysis_tools`에 legal_search 추가
- ✅ `analyze_data_node`에서 LegalSearch 사용 로직 추가

**병합 전략:**
```python
# ✅ 최종 목표: Improve 아키텍처 + Execute LegalSearch

from app.service_agent.tools import (
    # ... 기존 imports
    LegalSearch  # ← Execute 추가
)

def __init__(self, llm_context=None, progress_callback=None):  # ← Improve 유지
    self.progress_callback = progress_callback  # ← Improve 유지

    # 기존 tools
    self.contract_tool = ContractAnalysisTool(...)
    # ... 기존 tools

    # ← Execute 추가
    self.legal_search_tool = LegalSearch()
```

**난이도:** 🟡 **중간** (비교적 명확한 변경)

---

#### 3️⃣ separated_states.py (Low)

| 버전 | 줄 수 | 변경량 |
|------|-------|--------|
| **original_base** | 760줄 | (기준) |
| **backend (improve)** | 785줄 | **+25줄** ⭐ |
| **tests (execute)** | 762줄 | **+2줄** (신규 필드만) |

**Improve팀 변경사항 (+25줄):**
- 다양한 State 개선
- 필드 추가/수정
- 타입 정의 개선

**Execute팀 변경사항 (+2줄):**
```python
# guides.md에서 확인된 내용
infrastructure_results: Optional[Dict[str, Any]]  # 신규
building_registry_results: List[Dict[str, Any]]   # 신규
```

**병합 전략:**
```python
# ✅ 최종 목표: Improve 기준 + Execute 2개 필드 추가

class SearchTeamState(TypedDict):
    # ... Improve의 모든 필드 유지

    # ← Execute 추가 (2줄)
    infrastructure_results: Optional[Dict[str, Any]]
    building_registry_results: List[Dict[str, Any]]
```

**난이도:** 🟢 **낮음** (단순 필드 추가)

---

## 🎯 3-Way Merge 상세 전략

### Phase 1: 충돌 없는 파일 (30분)

**단순 복사만 하면 됨!**

```bash
# 1. infrastructure_tool.py (Execute가 +92줄, Improve 변경 없음)
cp tests/backend/app/service_agent/tools/infrastructure_tool.py \
   backend/app/service_agent/tools/

# 2. real_estate_search_tool.py (Execute가 +59줄, Improve 변경 없음)
cp tests/backend/app/service_agent/tools/real_estate_search_tool.py \
   backend/app/service_agent/tools/

# 3. agent_registry.py (Execute가 JSON 출력 개선, Improve 변경 없음)
cp tests/backend/app/service_agent/foundation/agent_registry.py \
   backend/app/service_agent/foundation/
```

**검증:**
```bash
diff original_base/backend/app/service_agent/tools/infrastructure_tool.py \
     backend/app/service_agent/tools/infrastructure_tool.py
# 출력: Files differ (정상 - Execute 변경사항 반영됨)
```

---

### Phase 2: search_executor.py 3-Way Merge (90분) 🔥

#### Step 1: Improve 변경사항 파악

```bash
# Improve가 무엇을 변경했는지 확인
diff -u original_base/backend/app/service_agent/execution_agents/search_executor.py \
        backend/app/service_agent/execution_agents/search_executor.py > improve_changes.diff
```

**예상 변경사항:**
- `__init__` 메서드에 `progress_callback` 파라미터 추가
- `_update_step_progress` 메서드 추가
- Progress 콜백 호출 코드 추가

#### Step 2: Execute 변경사항 파악

```bash
# Execute가 무엇을 변경했는지 확인
diff -u original_base/backend/app/service_agent/execution_agents/search_executor.py \
        tests/backend/app/service_agent/execution_agents/search_executor.py > execute_changes.diff
```

**예상 변경사항:**
- 신규 tool 속성 3개 추가
- 신규 tool 초기화 코드 추가
- LegalSearch 사용
- `_get_available_tools` 확장

#### Step 3: 수동 병합

**병합 기준:**
```python
# Backend (Improve) 기준 파일 사용
cp backend/app/service_agent/execution_agents/search_executor.py \
   backend/app/service_agent/execution_agents/search_executor.py.merge_working

# 편집기로 열기
code backend/app/service_agent/execution_agents/search_executor.py.merge_working
```

**추가할 내용 (Execute에서):**

1. **신규 tool 속성 추가** (62-65행 근처)
```python
# ✅ Execute 추가
self.building_registry_tool = None
self.infrastructure_tool = None
self.terminology_tool = None
```

2. **LegalSearch 초기화 교체** (72-98행 근처)
```python
# ✅ Execute 방식 + Improve Fallback
try:
    from app.service_agent.tools.legal_search_tool import LegalSearch
    self.legal_search_tool = LegalSearch()
    logger.info("LegalSearch initialized successfully")
except Exception as e:
    logger.warning(f"LegalSearch initialization failed: {e}")
    # Fallback
    try:
        from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
        self.legal_search_tool = HybridLegalSearch()
        logger.info("Fallback to HybridLegalSearch successful")
    except Exception as e2:
        logger.error(f"Both LegalSearch attempts failed: {e2}")
```

3. **신규 tools 초기화** (기존 tools 초기화 후)
```python
# ✅ Execute 추가
try:
    from app.service_agent.tools.building_registry_tool import BuildingRegistryTool
    self.building_registry_tool = BuildingRegistryTool()
    logger.info("BuildingRegistryTool initialized successfully")
except Exception as e:
    logger.warning(f"BuildingRegistryTool initialization failed: {e}")

# Infrastructure Tool
try:
    from app.service_agent.tools.infrastructure_tool import InfrastructureTool
    self.infrastructure_tool = InfrastructureTool()
    logger.info("InfrastructureTool initialized successfully")
except Exception as e:
    logger.warning(f"InfrastructureTool initialization failed: {e}")

# Terminology Tool
try:
    from app.service_agent.tools.realestate_terminology import RealEstateTerminology
    self.terminology_tool = RealEstateTerminology()
    logger.info("RealEstateTerminology initialized successfully")
except Exception as e:
    logger.warning(f"RealEstateTerminology initialization failed: {e}")
```

4. **_get_available_tools 메서드 확장** (200행 근처)
```python
def _get_available_tools(self) -> Dict[str, Any]:
    tools = {
        "legal_search": self.legal_search_tool,
        "market_data": self.market_data_tool,
        "real_estate_search": self.real_estate_search_tool,
        "loan_data": self.loan_data_tool,
    }

    # ✅ Execute 추가
    if self.building_registry_tool:
        tools["building_registry"] = self.building_registry_tool

    if self.infrastructure_tool:
        tools["infrastructure"] = self.infrastructure_tool

    if self.terminology_tool:
        tools["terminology"] = self.terminology_tool

    return tools
```

#### Step 4: 검증 후 교체

```bash
# 병합 파일 테스트
python -c "
from backend.app.service_agent.execution_agents.search_executor import SearchExecutor
executor = SearchExecutor(llm_context=None, progress_callback=None)
assert hasattr(executor, 'progress_callback')
assert hasattr(executor, 'building_registry_tool')
print('✅ Merge successful')
"

# 테스트 통과하면 원본 교체
mv backend/app/service_agent/execution_agents/search_executor.py.merge_working \
   backend/app/service_agent/execution_agents/search_executor.py
```

---

### Phase 3: analysis_executor.py 3-Way Merge (45분)

#### Step 1: Improve 변경사항 확인

```bash
diff -u original_base/backend/app/service_agent/execution_agents/analysis_executor.py \
        backend/app/service_agent/execution_agents/analysis_executor.py
```

#### Step 2: Execute 변경사항 확인

```bash
diff -u original_base/backend/app/service_agent/execution_agents/analysis_executor.py \
        tests/backend/app/service_agent/execution_agents/analysis_executor.py
```

#### Step 3: 수동 병합

**병합 기준:**
```python
# Backend (Improve) 기준 파일 사용
cp backend/app/service_agent/execution_agents/analysis_executor.py \
   backend/app/service_agent/execution_agents/analysis_executor.py.merge_working
```

**추가할 내용 (Execute에서):**

1. **Import 문에 LegalSearch 추가**
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool,
    LegalSearch  # ✅ Execute 추가
)
```

2. **LegalSearch 초기화 추가**
```python
def __init__(self, llm_context=None, progress_callback=None):  # Improve 유지
    # ... 기존 초기화

    # ✅ Execute 추가
    try:
        self.legal_search_tool = LegalSearch()
        logger.info("LegalSearch initialized in AnalysisExecutor")
    except Exception as e:
        logger.warning(f"LegalSearch initialization failed: {e}")
        self.legal_search_tool = None
```

3. **_get_available_analysis_tools 확장** (Execute의 guides.md 참고)
```python
if self.legal_search_tool:
    tools["legal_search"] = {
        "name": "legal_search",
        "description": "법률 및 시행령 검색, 법률 조항 분석",
        "capabilities": [
            "법률 조문 검색",
            "시행령 검색",
            "부동산 관련 법률 조회",
            "법률 해석 및 적용"
        ],
        "available": True
    }
```

4. **analyze_data_node에 LegalSearch 로직 추가** (guides.md 참고)

---

### Phase 4: separated_states.py 3-Way Merge (30분)

#### Step 1: Improve 변경사항 확인

```bash
diff -u original_base/backend/app/service_agent/foundation/separated_states.py \
        backend/app/service_agent/foundation/separated_states.py
```

#### Step 2: Execute 변경사항 확인 (2줄만!)

```bash
diff -u original_base/backend/app/service_agent/foundation/separated_states.py \
        tests/backend/app/service_agent/foundation/separated_states.py
```

**Execute 변경사항 (guides.md 확인):**
```python
infrastructure_results: Optional[Dict[str, Any]]
building_registry_results: List[Dict[str, Any]]
```

#### Step 3: 수동 병합

**병합 기준:**
```python
# Backend (Improve) 기준 파일 사용
cp backend/app/service_agent/foundation/separated_states.py \
   backend/app/service_agent/foundation/separated_states.py.merge_working

# 편집기로 열기
code backend/app/service_agent/foundation/separated_states.py.merge_working
```

**추가할 내용:**

SearchTeamState 클래스에 2줄 추가:
```python
class SearchTeamState(TypedDict):
    # ... Improve의 모든 기존 필드

    property_search_results: List[Dict[str, Any]]

    # ✅ Execute 추가 (2줄)
    infrastructure_results: Optional[Dict[str, Any]]      # 주변 인프라 검색 결과
    building_registry_results: List[Dict[str, Any]]       # 건축물 대장 검색 결과

    aggregated_results: Dict[str, Any]
    # ... 나머지 필드
```

---

## ✅ 최종 체크리스트

### Phase 1: 충돌 없는 파일 (30분)
- [ ] infrastructure_tool.py 복사 완료 (530줄)
- [ ] real_estate_search_tool.py 복사 완료 (411줄)
- [ ] agent_registry.py 복사 완료
- [ ] 3개 파일 검증 완료

### Phase 2: search_executor.py 3-Way Merge (90분)
- [ ] improve_changes.diff 생성
- [ ] execute_changes.diff 생성
- [ ] progress_callback 유지 확인
- [ ] 신규 tool 속성 3개 추가
- [ ] LegalSearch + Fallback 추가
- [ ] 신규 tools 초기화 추가
- [ ] _get_available_tools 확장
- [ ] 초기화 테스트 통과

### Phase 3: analysis_executor.py 3-Way Merge (45분)
- [ ] Import 문 LegalSearch 추가
- [ ] progress_callback 유지 확인
- [ ] LegalSearch 초기화 추가
- [ ] _get_available_analysis_tools 확장
- [ ] analyze_data_node 로직 추가
- [ ] 초기화 테스트 통과

### Phase 4: separated_states.py 3-Way Merge (30분)
- [ ] Improve 변경사항 유지
- [ ] Execute 2개 필드 추가
- [ ] Import 테스트 통과

### 최종 검증
- [ ] 전체 import 테스트
- [ ] Executor 초기화 테스트
- [ ] Progress callback 동작 확인
- [ ] 모든 신규 tools 초기화 확인

---

## 📊 예상 소요 시간

| Phase | 작업 | 시간 |
|-------|------|------|
| Phase 1 | 충돌 없는 파일 복사 | 30분 |
| Phase 2 | search_executor 3-way merge | 90분 |
| Phase 3 | analysis_executor 3-way merge | 45분 |
| Phase 4 | separated_states 3-way merge | 30분 |
| 최종 검증 | 통합 테스트 | 30분 |
| **총계** | | **3시간 45분** |

---

## 🎉 핵심 개선 사항

### 기존 2-Way 분석 대비 개선

**이전 (2-Way):**
- 6개 파일 모두 충돌 예상 🔴
- 누가 무엇을 바꿨는지 불명확
- 추측으로 병합

**현재 (3-Way):**
- **3개 파일은 충돌 없음!** ✅
- **3개 파일만 3-way merge** 🟡
- 각자의 변경사항 명확히 파악
- 정확한 병합 전략

**시간 절약:**
- 예상: 6시간 → **실제: 3시간 45분** (37% 단축!)

---

**문서 버전**: 1.0
**작성 완료일**: 2025-10-30
**다음 단계**: Phase 1부터 순차 진행
