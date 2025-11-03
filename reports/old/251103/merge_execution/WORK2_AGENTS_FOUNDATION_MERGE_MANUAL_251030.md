# 작업 2: Agents & Foundation 수동 병합 상세 가이드

**작성일**: 2025-10-30
**작성자**: Claude Code
**프로젝트**: beta_v001 (chatbot_improve)
**소스**: tests/backend/ (chatbot_execute 파일)
**우선순위**: **Backend 아키텍처 유지 + Tests 기능 추가**

---

## 🎯 작업 목표

### 총 4개 파일 병합

#### 🔥 Execution Agents (2개) - Critical
- `search_executor.py` (Backend 1021줄 vs Tests 1296줄)
- `analysis_executor.py` (Backend 1049줄 vs Tests 1023줄)

#### 📐 Foundation (2개) - Medium
- `agent_registry.py` (Backend 10,868 bytes vs Tests 10,993 bytes)
- `separated_states.py` (Backend 27,831 bytes vs Tests 26,398 bytes)

---

## ⚠️ 중요: 병합 원칙

### 핵심 원칙

**1. progress_callback 반드시 유지** 🔥
```python
# ✅ Backend (반드시 유지!)
def __init__(self, llm_context=None, progress_callback=None):
    self.progress_callback = progress_callback

# ❌ Tests (이 버전은 안 됨!)
def __init__(self, llm_context=None):
    # progress_callback 없음
```

**2. Backend 아키텍처 기준**
- WebSocket 실시간 진행률 기능 유지
- 기존 구조 보존

**3. Tests 신규 기능 추가**
- 신규 tool 속성 추가
- 신규 tool 초기화 코드 추가
- LegalSearch 사용

**4. Fallback 로직 추가**
- LegalSearch 실패 시 HybridLegalSearch
- Tool 초기화 실패 시 warning만 기록

---

## 🔍 Phase 1: search_executor.py 병합 (90분) 🔥

### 1.1 파일 비교 분석

**Backend (1021줄, 10월 29 16:28):**
```python
def __init__(self, llm_context=None, progress_callback=None):
    self.llm_context = llm_context
    self.progress_callback = progress_callback  # ✅ WebSocket 콜백

    # Tools
    self.legal_search_tool = None
    self.market_data_tool = None
    self.real_estate_search_tool = None
    self.loan_data_tool = None

    # Tool 초기화
    from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
    self.legal_search_tool = HybridLegalSearch()

    from app.service_agent.tools.market_data_tool import MarketDataTool
    self.market_data_tool = MarketDataTool()

    # ... 나머지 tools
```

**Tests (1296줄, +275줄, 10월 29 11:26):**
```python
def __init__(self, llm_context=None):  # ❌ progress_callback 없음!
    self.llm_context = llm_context

    # Tools
    self.legal_search_tool = None
    self.market_data_tool = None
    self.real_estate_search_tool = None
    self.loan_data_tool = None

    # ✅ 신규 tools 추가!
    self.transaction_price_tool = None
    self.building_registry_tool = None
    self.infrastructure_tool = None
    self.terminology_tool = None

    # Tool 초기화 (LegalSearch 사용)
    from app.service_agent.tools.legal_search_tool import LegalSearch
    self.legal_search_tool = LegalSearch()

    # ... 신규 tools 초기화
```

### 1.2 병합 전략 (Best-of-Both)

**목표:**
- ✅ Backend의 progress_callback 유지
- ✅ Backend의 WebSocket 진행률 코드 유지
- ✅ Tests의 신규 tool 속성 추가
- ✅ Tests의 신규 tool 초기화 추가
- ✅ LegalSearch 우선 사용 + HybridLegalSearch Fallback

### 1.3 병합 후 search_executor.py 구조

**__init__ 메서드 (최종 버전):**

```python
class SearchExecutor:
    """
    검색 실행 Agent
    법률, 부동산, 대출 검색 작업을 실행
    """

    def __init__(self, llm_context=None, progress_callback=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
            progress_callback: Optional callback for real-time progress updates
        """
        # ✅ Backend 유지
        self.llm_context = llm_context
        self.progress_callback = progress_callback  # 🔥 반드시 유지!

        # LLMService 초기화
        try:
            self.llm_service = LLMService(llm_context=llm_context)
            logger.info("✅ LLMService initialized successfully in SearchExecutor")
        except Exception as e:
            logger.error(f"❌ LLMService initialization failed: {e}", exc_info=True)
            self.llm_service = None

        self.team_name = "search"

        # Agent 초기화
        self.available_agents = self._initialize_agents()

        # ✅ 기존 tools (Backend)
        self.legal_search_tool = None
        self.market_data_tool = None
        self.real_estate_search_tool = None
        self.loan_data_tool = None

        # ✅ 신규 tools (Tests 추가)
        self.building_registry_tool = None
        self.infrastructure_tool = None
        self.terminology_tool = None
        # self.transaction_price_tool = None  # 선택 사항

        # Decision Logger 초기화
        try:
            self.decision_logger = DecisionLogger()
        except Exception as e:
            logger.warning(f"DecisionLogger initialization failed: {e}")
            self.decision_logger = None

        # =========================================================================
        # Tool 초기화 (LegalSearch 우선 + Fallback)
        # =========================================================================

        # Legal Search (LegalSearch 우선, HybridLegalSearch fallback)
        try:
            from app.service_agent.tools.legal_search_tool import LegalSearch
            self.legal_search_tool = LegalSearch()
            logger.info("LegalSearch initialized successfully")
        except Exception as e:
            logger.warning(f"LegalSearch initialization failed: {e}")
            # Fallback to HybridLegalSearch
            try:
                from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
                self.legal_search_tool = HybridLegalSearch()
                logger.info("Fallback to HybridLegalSearch successful")
            except Exception as e2:
                logger.error(f"Both LegalSearch attempts failed: {e2}")
                self.legal_search_tool = None

        # Market Data Tool
        try:
            from app.service_agent.tools.market_data_tool import MarketDataTool
            self.market_data_tool = MarketDataTool()
            logger.info("MarketDataTool initialized successfully")
        except Exception as e:
            logger.warning(f"MarketDataTool initialization failed: {e}")

        # Loan Data Tool
        try:
            from app.service_agent.tools.loan_data_tool import LoanDataTool
            self.loan_data_tool = LoanDataTool()
            logger.info("LoanDataTool initialized successfully")
        except Exception as e:
            logger.warning(f"LoanDataTool initialization failed: {e}")

        # Real Estate Search Tool
        try:
            from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool
            self.real_estate_search_tool = RealEstateSearchTool()
            logger.info("RealEstateSearchTool initialized successfully (PostgreSQL)")
        except Exception as e:
            logger.warning(f"RealEstateSearchTool initialization failed: {e}")

        # =========================================================================
        # 신규 Tools 초기화 (Tests에서 추가)
        # =========================================================================

        # Building Registry Tool
        try:
            from app.service_agent.tools.building_registry_tool import BuildingRegistryTool
            self.building_registry_tool = BuildingRegistryTool()
            logger.info("BuildingRegistryTool initialized successfully")
        except Exception as e:
            logger.warning(f"BuildingRegistryTool initialization failed: {e}")
            self.building_registry_tool = None

        # Infrastructure Tool
        try:
            from app.service_agent.tools.infrastructure_tool import InfrastructureTool
            self.infrastructure_tool = InfrastructureTool()
            logger.info("InfrastructureTool initialized successfully")
        except Exception as e:
            logger.warning(f"InfrastructureTool initialization failed: {e}")
            self.infrastructure_tool = None

        # Real Estate Terminology Tool
        try:
            from app.service_agent.tools.realestate_terminology import RealEstateTerminology
            self.terminology_tool = RealEstateTerminology()
            logger.info("RealEstateTerminology initialized successfully")
        except Exception as e:
            logger.warning(f"RealEstateTerminology initialization failed: {e}")
            self.terminology_tool = None

        # 서브그래프 구성
        self.app = None
        try:
            self.app = self._build_subgraph()
            logger.info("SearchExecutor subgraph built successfully")
        except Exception as e:
            logger.error(f"Failed to build SearchExecutor subgraph: {e}", exc_info=True)
```

### 1.4 _get_available_tools 메서드 업데이트

**기존 (Backend):**
```python
def _get_available_tools(self) -> Dict[str, Any]:
    """사용 가능한 도구 목록 반환"""
    return {
        "legal_search": self.legal_search_tool,
        "market_data": self.market_data_tool,
        "real_estate_search": self.real_estate_search_tool,
        "loan_data": self.loan_data_tool,
    }
```

**업데이트 (신규 tools 추가):**
```python
def _get_available_tools(self) -> Dict[str, Any]:
    """사용 가능한 도구 목록 반환"""
    tools = {
        "legal_search": self.legal_search_tool,
        "market_data": self.market_data_tool,
        "real_estate_search": self.real_estate_search_tool,
        "loan_data": self.loan_data_tool,
    }

    # ✅ 신규 tools 추가 (Tests에서)
    if self.building_registry_tool:
        tools["building_registry"] = self.building_registry_tool

    if self.infrastructure_tool:
        tools["infrastructure"] = self.infrastructure_tool

    if self.terminology_tool:
        tools["terminology"] = self.terminology_tool

    return tools
```

### 1.5 실행 방법

**옵션 A: 직접 수동 병합 (권장)**

```bash
# 1. Backend 파일 백업
cp backend/app/service_agent/execution_agents/search_executor.py \
   backend/app/service_agent/execution_agents/search_executor.py.backup

# 2. 편집기로 열기
code backend/app/service_agent/execution_agents/search_executor.py

# 3. 위 "병합 후 search_executor.py 구조" 대로 수정:
#    - __init__ 메서드 업데이트
#    - _get_available_tools 메서드 업데이트
```

**수정 가이드:**

1. **__init__ 메서드 찾기** (34행 근처)
2. **progress_callback 파라미터 확인** (있어야 함!)
3. **신규 tool 속성 추가** (62-65행 근처)
   ```python
   self.building_registry_tool = None
   self.infrastructure_tool = None
   self.terminology_tool = None
   ```

4. **LegalSearch 초기화 코드 교체** (72-76행)
   ```python
   # 기존 HybridLegalSearch를
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

5. **신규 tools 초기화 코드 추가** (98행 이후)
   - BuildingRegistryTool 초기화
   - InfrastructureTool 초기화
   - RealEstateTerminology 초기화

6. **_get_available_tools 메서드 업데이트** (200행 근처)

### 1.6 검증

**초기화 테스트:**
```bash
cd backend
python -c "
from app.service_agent.execution_agents.search_executor import SearchExecutor

# 초기화
executor = SearchExecutor(llm_context=None, progress_callback=None)

# progress_callback 확인
assert hasattr(executor, 'progress_callback'), 'progress_callback missing!'
print('✅ progress_callback exists')

# 신규 tools 확인
assert hasattr(executor, 'building_registry_tool'), 'building_registry_tool missing!'
assert hasattr(executor, 'infrastructure_tool'), 'infrastructure_tool missing!'
assert hasattr(executor, 'terminology_tool'), 'terminology_tool missing!'
print('✅ New tools attributes exist')

# Tool 초기화 확인
print(f'LegalSearch: {executor.legal_search_tool is not None}')
print(f'BuildingRegistry: {executor.building_registry_tool is not None}')
print(f'Infrastructure: {executor.infrastructure_tool is not None}')
print(f'Terminology: {executor.terminology_tool is not None}')

# Available tools 확인
tools = executor._get_available_tools()
print(f'✅ Available tools: {list(tools.keys())}')
"
```

**예상 출력:**
```
✅ progress_callback exists
✅ New tools attributes exist
LegalSearch: True
BuildingRegistry: True
Infrastructure: True
Terminology: True
✅ Available tools: ['legal_search', 'market_data', 'real_estate_search', 'loan_data', 'building_registry', 'infrastructure', 'terminology']
```

---

## 🔍 Phase 2: analysis_executor.py 병합 (45분)

### 2.1 파일 비교 분석

**Backend (1049줄, 10월 29 16:28):**
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool
)

def __init__(self, llm_context=None, progress_callback=None):
    self.llm_context = llm_context
    self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
    self.progress_callback = progress_callback  # ✅ 유지
    self.team_name = "analysis"

    # 분석 도구 초기화
    self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
    self.market_tool = MarketAnalysisTool(llm_service=self.llm_service)
    self.roi_tool = ROICalculatorTool()
    self.loan_tool = LoanSimulatorTool()
    self.policy_tool = PolicyMatcherTool()

    # ❌ LegalSearch 없음
```

**Tests (1023줄, 10월 29 11:26):**
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool,
    LegalSearch  # ✅ 추가!
)

def __init__(self, llm_context=None):  # ❌ progress_callback 없음
    self.llm_context = llm_context
    self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
    self.team_name = "analysis"

    # 분석 도구 초기화
    self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
    self.market_tool = MarketAnalysisTool(llm_service=self.llm_service)
    self.roi_tool = ROICalculatorTool()
    self.loan_tool = LoanSimulatorTool()
    self.policy_tool = PolicyMatcherTool()

    # ✅ LegalSearch 추가!
    self.legal_search_tool = LegalSearch()
```

### 2.2 병합 전략

**목표:**
- ✅ Backend의 progress_callback 유지
- ✅ Tests의 LegalSearch tool 추가

### 2.3 병합 후 analysis_executor.py 구조

**Import 문 업데이트:**
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool,
    LegalSearch  # ✅ 추가
)
```

**__init__ 메서드:**
```python
def __init__(self, llm_context=None, progress_callback=None):
    """
    초기화

    Args:
        llm_context: LLM 컨텍스트
        progress_callback: Optional callback for real-time progress updates
    """
    # ✅ Backend 유지
    self.llm_context = llm_context
    self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
    self.progress_callback = progress_callback  # 🔥 반드시 유지!
    self.team_name = "analysis"

    # 분석 도구 초기화 (기존)
    self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
    self.market_tool = MarketAnalysisTool(llm_service=self.llm_service)
    self.roi_tool = ROICalculatorTool()
    self.loan_tool = LoanSimulatorTool()
    self.policy_tool = PolicyMatcherTool()

    # ✅ 법률 검색 도구 추가 (Tests에서)
    try:
        self.legal_search_tool = LegalSearch()
        logger.info("LegalSearch initialized in AnalysisExecutor")
    except Exception as e:
        logger.warning(f"LegalSearch initialization failed in AnalysisExecutor: {e}")
        self.legal_search_tool = None

    # 서브그래프 구성
    self.app = None
    try:
        self.app = self._build_subgraph()
        logger.info("AnalysisExecutor subgraph built successfully")
    except Exception as e:
        logger.error(f"Failed to build AnalysisExecutor subgraph: {e}", exc_info=True)
```

### 2.4 실행 방법

```bash
# 1. Backend 파일 백업
cp backend/app/service_agent/execution_agents/analysis_executor.py \
   backend/app/service_agent/execution_agents/analysis_executor.py.backup

# 2. 편집기로 열기
code backend/app/service_agent/execution_agents/analysis_executor.py

# 3. 수정:
#    - Import 문에 LegalSearch 추가
#    - __init__ 메서드에 LegalSearch 초기화 추가
#    - progress_callback 파라미터 확인 (있어야 함!)
```

### 2.5 검증

```bash
cd backend
python -c "
from app.service_agent.execution_agents.analysis_executor import AnalysisExecutor

# 초기화
executor = AnalysisExecutor(llm_context=None, progress_callback=None)

# progress_callback 확인
assert hasattr(executor, 'progress_callback'), 'progress_callback missing!'
print('✅ progress_callback exists')

# LegalSearch 확인
assert hasattr(executor, 'legal_search_tool'), 'legal_search_tool missing!'
print(f'✅ LegalSearch: {executor.legal_search_tool is not None}')
"
```

---

## 🔍 Phase 3: agent_registry.py 검토 (15분)

### 3.1 파일 비교

**Diff 확인:**
```bash
diff -u backend/app/service_agent/foundation/agent_registry.py \
        tests/backend/app/service_agent/foundation/agent_registry.py
```

**결과:**
```diff
@@ -364,4 +364,6 @@
     agent = AgentRegistry.create_agent("test_agent", config={"test": True})
     if agent:
         result = agent.execute({"query": "test"})
-        print(f"Execution result: {result}")
+        # JSON 직렬화하여 출력 (object object 방지)
+        import json
+        print(f"Execution result: {json.dumps(result, ensure_ascii=False, indent=2)}")
```

**분석:**
- **Trivial 차이만** (테스트 코드 개선)
- JSON 출력 개선 (object object → 실제 내용)
- 기능 변경 없음

### 3.2 병합 전략

**옵션 A: Tests 버전 채택 (권장)**
- 더 나은 디버깅/로깅
- 위험 없음

**옵션 B: Backend 유지**
- 변경 최소화
- 동작에 영향 없음

**권장: Tests 버전 채택**

### 3.3 실행

```bash
cp tests/backend/app/service_agent/foundation/agent_registry.py \
   backend/app/service_agent/foundation/agent_registry.py
```

---

## 🔍 Phase 4: separated_states.py 검토 (30분)

### 4.1 파일 비교

**크기 차이:**
- Backend: 27,831 bytes (+1,433 bytes, 더 큼)
- Tests: 26,398 bytes

**분석:**
Backend가 더 최신이고 더 많은 내용 포함

### 4.2 Diff 확인

```bash
diff -u tests/backend/app/service_agent/foundation/separated_states.py \
        backend/app/service_agent/foundation/separated_states.py | head -100
```

**주요 차이점 확인:**
- State 필드 추가/삭제 여부
- TypedDict 정의 변경
- 새로운 State 클래스 추가

### 4.3 병합 전략

**원칙: Backend 우선**
- Backend가 더 최신 (10월 29 16:28)
- Backend가 더 많은 내용
- Tests는 오래됨 (10월 29 11:26)

**권장: Backend 유지**

### 4.4 실행

```bash
# Backend 유지 (아무 작업 안 함)
echo "✅ separated_states.py: Backend version kept (newer)"
```

**만약 Tests에 신규 State가 있다면:**
```bash
# Diff 확인 후 수동 병합
diff -u tests/backend/app/service_agent/foundation/separated_states.py \
        backend/app/service_agent/foundation/separated_states.py > states_diff.txt

# 검토 후 필요한 부분만 추가
```

---

## ✅ 작업 2 완료 체크리스트

### Phase 1: search_executor.py 병합
- [ ] Backend 파일 백업 완료
- [ ] progress_callback 파라미터 유지 확인
- [ ] 신규 tool 속성 추가 (3개)
- [ ] LegalSearch 초기화 + Fallback 추가
- [ ] 신규 tools 초기화 코드 추가 (3개)
- [ ] _get_available_tools 메서드 업데이트
- [ ] 초기화 테스트 성공

### Phase 2: analysis_executor.py 병합
- [ ] Backend 파일 백업 완료
- [ ] progress_callback 파라미터 유지 확인
- [ ] Import 문에 LegalSearch 추가
- [ ] LegalSearch 초기화 코드 추가
- [ ] 초기화 테스트 성공

### Phase 3: agent_registry.py 검토
- [ ] Diff 확인 완료
- [ ] Tests 버전 채택 (JSON 출력 개선)

### Phase 4: separated_states.py 검토
- [ ] Diff 확인 완료
- [ ] Backend 버전 유지 결정

### 최종 검증
- [ ] search_executor.py 초기화 성공
- [ ] analysis_executor.py 초기화 성공
- [ ] progress_callback 모두 유지
- [ ] 신규 tools 모두 초기화
- [ ] 에러 없음

---

## 🔍 Phase 5: 통합 검증 (45분)

### 5.1 Import 전체 테스트

```bash
cd backend
python -c "
# Tools import
from app.service_agent.tools import (
    LegalSearch,
    BuildingRegistryTool,
    InfrastructureTool,
    RealEstateTerminology,
    HybridLegalSearch
)
print('✅ Tools import successful')

# Agents import
from app.service_agent.execution_agents import SearchExecutor, AnalysisExecutor
print('✅ Agents import successful')

# Foundation import
from app.service_agent.foundation import AgentRegistry
from app.service_agent.foundation.separated_states import SearchTeamState
print('✅ Foundation import successful')
"
```

### 5.2 Execution Agents 초기화 테스트

```bash
cd backend
python -c "
from app.service_agent.execution_agents import SearchExecutor, AnalysisExecutor

# SearchExecutor
print('Testing SearchExecutor...')
search = SearchExecutor(llm_context=None, progress_callback=None)
assert search.progress_callback is None
assert hasattr(search, 'building_registry_tool')
assert hasattr(search, 'infrastructure_tool')
assert hasattr(search, 'terminology_tool')
print(f'  LegalSearch: {search.legal_search_tool is not None}')
print(f'  BuildingRegistry: {search.building_registry_tool is not None}')
print(f'  Infrastructure: {search.infrastructure_tool is not None}')
print(f'  Terminology: {search.terminology_tool is not None}')
print('✅ SearchExecutor OK')

# AnalysisExecutor
print('Testing AnalysisExecutor...')
analysis = AnalysisExecutor(llm_context=None, progress_callback=None)
assert analysis.progress_callback is None
assert hasattr(analysis, 'legal_search_tool')
print(f'  LegalSearch: {analysis.legal_search_tool is not None}')
print('✅ AnalysisExecutor OK')

print('\\n🎉 All tests passed!')
"
```

### 5.3 Progress Callback 동작 테스트

```bash
cd backend
python -c "
from app.service_agent.execution_agents import SearchExecutor

# Callback 함수 정의
async def test_callback(event_type, event_data):
    print(f'Callback: {event_type} - {event_data}')

# 초기화
search = SearchExecutor(llm_context=None, progress_callback=test_callback)
assert search.progress_callback == test_callback
print('✅ Progress callback assignment OK')
"
```

---

## 🎯 최종 상태

### 병합 완료 후 파일 구조

```
backend/app/service_agent/
├── execution_agents/
│   ├── search_executor.py       ✅ 병합 완료 (Best-of-Both)
│   ├── analysis_executor.py     ✅ 병합 완료 (Best-of-Both)
│   └── document_executor.py     (변경 없음)
│
├── foundation/
│   ├── agent_registry.py        ✅ Tests 버전 (JSON 출력 개선)
│   └── separated_states.py      ✅ Backend 유지 (더 최신)
│
└── tools/
    ├── __init__.py               ✅ 작업 1에서 완료
    ├── legal_search_tool.py      ✅ 작업 1에서 완료
    ├── building_registry_tool.py ✅ 작업 1에서 완료
    ├── infrastructure_tool.py    ✅ 작업 1에서 완료
    ├── real_estate_search_tool.py ✅ 작업 1에서 완료
    ├── realestate_terminology.py ✅ 작업 1에서 완료
    └── hybrid_legal_search.py    (유지, Fallback용)
```

### 핵심 달성 사항

#### ✅ SearchExecutor
- progress_callback 유지 (WebSocket 실시간 진행률)
- 신규 tools 3개 추가 (BuildingRegistry, Infrastructure, Terminology)
- LegalSearch 우선 사용 + HybridLegalSearch Fallback
- Backend 아키텍처 유지

#### ✅ AnalysisExecutor
- progress_callback 유지
- LegalSearch tool 추가
- Backend 아키텍처 유지

#### ✅ Foundation
- agent_registry.py: Tests 버전 (로깅 개선)
- separated_states.py: Backend 유지 (더 최신)

---

## 📊 예상 소요 시간

| Phase | 작업 | 시간 |
|-------|------|------|
| Phase 1 | search_executor.py 병합 | 90분 |
| Phase 2 | analysis_executor.py 병합 | 45분 |
| Phase 3 | agent_registry.py 검토 | 15분 |
| Phase 4 | separated_states.py 검토 | 30분 |
| Phase 5 | 통합 검증 | 45분 |
| **총계** | | **3시간 45분** |

---

## 🔧 문제 해결

### 문제 1: progress_callback이 None으로만 동작

**증상:**
```python
executor = SearchExecutor(llm_context=None, progress_callback=my_callback)
# 하지만 내부에서 callback 호출 안 됨
```

**해결:**
1. `_update_step_progress` 메서드 확인
2. `self.progress_callback` 호출 확인
3. Backend 버전의 progress 관련 코드 유지 확인

### 문제 2: LegalSearch import 실패

**증상:**
```python
ModuleNotFoundError: No module named 'app.service_agent.tools.legal_search_tool'
```

**해결:**
1. 작업 1 완료 확인 (legal_search_tool.py 복사 완료?)
2. __init__.py 업데이트 확인
3. 파일 경로 확인

### 문제 3: Tool 초기화 실패

**증상:**
```python
BuildingRegistryTool initialization failed: ...
```

**해결:**
1. Try-except로 감싸져 있어 warning만 출력
2. Tool이 None이어도 전체 동작은 정상
3. 필요 시 해당 tool의 의존성 확인

---

## 🎯 다음 단계

작업 2 완료 후:
→ **최종 문서화 & 커밋**

---

**문서 버전**: 1.0
**작성 완료일**: 2025-10-30
**이전 단계**: 작업 1 - Tools 병합
**다음 단계**: 최종 검증 & 문서화
