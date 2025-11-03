# Execution Agent 병합 계획서

**작성일**: 2025-10-29 (업데이트: 2025-10-30)
**작성자**: Claude Code
**프로젝트**: beta_v001 (LangGraph 0.6)
**목적**: tests/backend의 execution_agent와 tool 수정사항을 backend 코드베이스에 병합

---

## 🔄 업데이트 (2025-10-30)

### 🎯 최신: 3-Way Merge 분석 완료! (더 정확하고 빠름)

**중요한 발견:**
- ✅ **3개 파일은 충돌 없음!** (Execute만 수정)
- 🔀 **3개 파일만 3-way merge 필요**
- ⏱️ **예상 시간: 6시간 → 3시간 45분** (37% 단축!)

### 📄 최신 계획서 (3-Way Merge)

#### 🆕 [3-Way Merge 분석 보고서](3WAY_MERGE_ANALYSIS_251030.md) ⭐⭐⭐
- **original_base (분기 시점) 기반 정확한 분석**
- 충돌 없는 파일 3개 (단순 복사)
- 3-way merge 필요 파일 3개 (상세 가이드)
- **가장 정확하고 빠른 방법!**

#### 1️⃣ [작업 1: Tools 수동 병합](WORK1_TOOLS_MERGE_MANUAL_251030.md) ⭐
- 신규 Tools 3개 복사
- 중복 Tools 2개 → **충돌 없음! 단순 복사로 변경**
- __init__.py 업데이트
- **예상 시간: 30분** (간소화!)

#### 2️⃣ [작업 2: Agents & Foundation 병합](WORK2_AGENTS_FOUNDATION_MERGE_MANUAL_251030.md) ⭐
- search_executor.py 3-way merge (progress_callback 유지!)
- analysis_executor.py 3-way merge
- separated_states.py 3-way merge (+2줄만)
- agent_registry.py → **충돌 없음! 단순 복사**
- **예상 시간: 3시간 15분**

#### 📊 [Git Merge 분석 보고서](GIT_MERGE_ANALYSIS_REPORT_251030.md) (참고용)
- 초기 2-way 분석 (original_base 없을 때)
- Git merge 불가능 이유

### ✅ 권장 작업 순서 (3-Way 기반)

```
✅ 백업 생성 (완료)
✅ original_base/ 폴더 생성 (완료)

📁 Phase 1: 충돌 없는 파일 (30분)
   ├─ infrastructure_tool.py (Execute만 수정 → 단순 복사)
   ├─ real_estate_search_tool.py (Execute만 수정 → 단순 복사)
   └─ agent_registry.py (Execute만 수정 → 단순 복사)

📁 Phase 2: search_executor.py 3-Way Merge (90분)
   └─ Improve 아키텍처 + Execute 신규 tools

📁 Phase 3: analysis_executor.py 3-Way Merge (45분)
   └─ Improve 아키텍처 + Execute LegalSearch

📁 Phase 4: separated_states.py 3-Way Merge (30분)
   └─ Improve 기준 + Execute 2개 필드 추가

📁 Phase 5: 최종 검증 (30분)

⏱️ 총 예상 시간: 3시간 45분 (6시간에서 37% 단축!)
```

---

## 📌 아래는 원본 계획서 (참고용)

본 계획서는 초기 분석 버전입니다.
**실제 작업 시에는 위의 새로운 계획서를 사용하세요.**

---

## 1. 개요 (Executive Summary)

### 1.1 병합 범위
- **소스 디렉토리**: `C:\kdy\Projects\holmesnyangz\beta_v001\tests\backend`
- **타겟 디렉토리**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend`
- **주요 변경 영역**:
  - execution_agents (search_executor, analysis_executor)
  - tools (5개 신규/수정)
  - foundation (agent_registry, separated_states)

### 1.2 우선순위 정책
- **Tool 이름**: tests/backend 우선
- **코드 구조**: backend 우선 (최신 아키텍처)
- **기능**: 양쪽의 강점 통합

### 1.3 예상 작업 시간
- **준비 단계**: 30분 (백업 및 검증)
- **병합 작업**: 2-3시간
- **테스트 및 검증**: 1-2시간
- **총 소요 시간**: 4-6시간

---

## 2. 현황 분석 (Current State Analysis)

### 2.1 파일 구조 비교

#### backend (메인 코드베이스)
```
backend/app/service_agent/
├── execution_agents/
│   ├── search_executor.py       (progress_callback 지원, HybridLegalSearch 사용)
│   ├── analysis_executor.py     (progress_callback 지원)
│   └── document_executor.py
├── tools/
│   ├── hybrid_legal_search.py   (기존)
│   ├── real_estate_search_tool.py (PostgreSQL)
│   ├── market_data_tool.py
│   ├── loan_data_tool.py
│   ├── contract_analysis_tool.py
│   ├── market_analysis_tool.py
│   ├── roi_calculator_tool.py
│   ├── loan_simulator_tool.py
│   └── policy_matcher_tool.py
└── foundation/
    ├── agent_registry.py
    └── separated_states.py
```

#### tests/backend (수정 사항)
```
tests/backend/app/service_agent/
├── execution_agents/
│   ├── search_executor.py       (공공데이터 API 도구 추가, LegalSearch 사용)
│   └── analysis_executor.py     (LegalSearch tool 추가)
├── tools/
│   ├── legal_search_tool.py     (신규: SQLite+FAISS 하이브리드)
│   ├── building_registry_tool.py (신규: 건축물대장 API)
│   ├── infrastructure_tool.py   (신규: 공공인프라 API)
│   ├── realestate_terminology.py (신규: 부동산 용어 사전)
│   └── real_estate_search_tool.py (수정본)
└── foundation/
    ├── agent_registry.py        (수정본)
    └── separated_states.py      (수정본)
```

### 2.2 주요 차이점 상세 분석

#### 2.2.1 SearchExecutor

| 항목 | backend | tests/backend | 병합 방침 |
|------|---------|---------------|----------|
| progress_callback | ✅ 있음 | ❌ 없음 | backend 유지 |
| 공공데이터 API 도구 | ❌ 없음 | ✅ 있음 (3개) | tests 추가 |
| Legal Search | HybridLegalSearch | LegalSearch | tests 이름 채택, backend 코드 유지 |
| 부동산 용어 검색 | ❌ 없음 | ✅ 있음 | tests 추가 |

**세부 차이점**:

**backend (현재)**:
```python
def __init__(self, llm_context=None, progress_callback=None):
    self.progress_callback = progress_callback

    # Tools
    self.legal_search_tool = None
    self.market_data_tool = None
    self.real_estate_search_tool = None
    self.loan_data_tool = None

    # HybridLegalSearch 사용
    from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
    self.legal_search_tool = HybridLegalSearch()
```

**tests/backend**:
```python
def __init__(self, llm_context=None):
    # progress_callback 없음

    # Tools
    self.legal_search_tool = None
    self.market_data_tool = None
    self.real_estate_search_tool = None
    self.loan_data_tool = None

    # 공공데이터 API 도구 (NEW)
    self.transaction_price_tool = None
    self.building_registry_tool = None
    self.infrastructure_tool = None

    # 부동산 용어 검색 도구 (NEW)
    self.terminology_tool = None

    # LegalSearch 사용
    from app.service_agent.tools.legal_search_tool import LegalSearch
    self.legal_search_tool = LegalSearch()
```

#### 2.2.2 AnalysisExecutor

| 항목 | backend | tests/backend | 병합 방침 |
|------|---------|---------------|----------|
| progress_callback | ✅ 있음 | ❌ 없음 | backend 유지 |
| LegalSearch tool | ❌ 없음 | ✅ 있음 | tests 추가 |

**세부 차이점**:

**backend (현재)**:
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool
)

def __init__(self, llm_context=None, progress_callback=None):
    self.progress_callback = progress_callback
    self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
    # ... LegalSearch 없음
```

**tests/backend**:
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool,
    LegalSearch  # 추가
)

def __init__(self, llm_context=None):
    # progress_callback 없음
    self.legal_search_tool = LegalSearch()  # 추가
```

#### 2.2.3 신규 Tools (tests/backend)

| Tool 파일 | 설명 | 주요 기능 |
|----------|------|----------|
| **legal_search_tool.py** | SQLite + FAISS 하이브리드 법률 검색 | - 메타데이터 기반 필터링<br>- 시맨틱 벡터 검색<br>- KURE_v1 임베딩 |
| **building_registry_tool.py** | 건축물대장 API 연동 | - 건축물 정보 조회<br>- 용도/구조 확인 |
| **infrastructure_tool.py** | 공공인프라 API 연동 | - 교통/학교/병원 정보<br>- 지역 인프라 분석 |
| **realestate_terminology.py** | 부동산 용어 사전 | - 용어 검색/설명<br>- 관련 용어 추천 |
| **real_estate_search_tool.py** | 부동산 검색 (수정본) | - PostgreSQL 연동<br>- 고급 필터링 |

---

## 3. 병합 전략 (Merge Strategy)

### 3.1 병합 원칙

#### 원칙 1: 코드 아키텍처는 backend 유지
- **이유**: backend는 최신 progress_callback, WebSocket 통합 등을 포함
- **적용**: execution_agents의 기본 구조는 backend 기준

#### 원칙 2: Tool 이름은 tests/backend 우선
- **이유**: 사용자 요구사항에 명시됨
- **적용**:
  - `HybridLegalSearch` → `LegalSearch`로 이름 변경
  - 단, 기존 `hybrid_legal_search.py` 파일은 유지 (호환성)

#### 원칙 3: 신규 기능은 모두 통합
- **이유**: 양쪽의 강점을 모두 활용
- **적용**:
  - tests의 공공데이터 API 도구 추가
  - tests의 부동산 용어 사전 추가

#### 원칙 4: 점진적 병합 (Phase-by-Phase)
- **이유**: 안정성 확보, 롤백 가능성
- **적용**: 5단계로 나누어 진행

### 3.2 병합 방식

```
┌─────────────────────────────────────────────────┐
│  Phase 1: 백업 및 준비                           │
│  - backend 전체 백업                             │
│  - 의존성 확인                                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Phase 2: Tools 병합                             │
│  - 신규 tools 복사 (5개)                         │
│  - __init__.py 업데이트                          │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Phase 3: Foundation 병합                        │
│  - agent_registry.py 업데이트                    │
│  - separated_states.py 검토                      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Phase 4: Execution Agents 병합                  │
│  - SearchExecutor 도구 초기화 추가               │
│  - AnalysisExecutor 도구 추가                    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Phase 5: 테스트 및 검증                         │
│  - Import 검증                                   │
│  - 기본 실행 테스트                              │
│  - 롤백 준비                                     │
└─────────────────────────────────────────────────┘
```

---

## 4. 상세 병합 계획 (Detailed Merge Plan)

### Phase 1: 백업 및 준비 (30분)

#### 1.1 백업 생성
```powershell
# 전체 backend 백업
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Path "C:\kdy\Projects\holmesnyangz\beta_v001\backend" `
          -Destination "C:\kdy\Projects\holmesnyangz\beta_v001\backend_backup_$timestamp" `
          -Recurse

# 백업 확인
Write-Host "Backup created: backend_backup_$timestamp"
```

#### 1.2 Git 커밋 생성
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001
git add .
git commit -m "Pre-merge checkpoint: Before execution agent merge"
git branch merge-execution-agent-251029
```

#### 1.3 의존성 확인
- **확인 항목**:
  - SQLite3 설치 여부
  - FAISS 라이브러리 설치
  - sentence-transformers
  - 공공데이터 API 키 설정

```python
# 필요한 패키지 확인 스크립트
import sys
required_packages = [
    'sqlite3',
    'faiss',
    'sentence_transformers',
    'numpy'
]

for pkg in required_packages:
    try:
        __import__(pkg)
        print(f"✅ {pkg} installed")
    except ImportError:
        print(f"❌ {pkg} NOT installed - pip install {pkg}")
```

---

### Phase 2: Tools 병합 (60분)

#### 2.1 신규 Tools 복사

**작업 순서**:

1. **legal_search_tool.py 복사**
   ```powershell
   Copy-Item -Path "tests\backend\app\service_agent\tools\legal_search_tool.py" `
             -Destination "backend\app\service_agent\tools\legal_search_tool.py"
   ```
   - **검증**: SQLite DB 경로 확인
   - **검증**: FAISS 인덱스 경로 확인
   - **검증**: 임베딩 모델 경로 확인

2. **building_registry_tool.py 복사**
   ```powershell
   Copy-Item -Path "tests\backend\app\service_agent\tools\building_registry_tool.py" `
             -Destination "backend\app\service_agent\tools\building_registry_tool.py"
   ```
   - **검증**: API 키 설정 확인
   - **검증**: API 엔드포인트 확인

3. **infrastructure_tool.py 복사**
   ```powershell
   Copy-Item -Path "tests\backend\app\service_agent\tools\infrastructure_tool.py" `
             -Destination "backend\app\service_agent\tools\infrastructure_tool.py"
   ```
   - **검증**: API 키 설정 확인

4. **realestate_terminology.py 복사**
   ```powershell
   Copy-Item -Path "tests\backend\app\service_agent\tools\realestate_terminology.py" `
             -Destination "backend\app\service_agent\tools\realestate_terminology.py"
   ```
   - **검증**: 용어 데이터 파일 경로 확인

5. **real_estate_search_tool.py 비교 및 병합**
   - **방법**: diff 도구로 비교 후 수동 병합
   - **주의**: PostgreSQL 연결 설정 확인

#### 2.2 __init__.py 업데이트

**현재 (backend/app/service_agent/tools/__init__.py)**:
```python
from .hybrid_legal_search import HybridLegalSearch
from .market_data_tool import MarketDataTool
from .loan_data_tool import LoanDataTool
from .real_estate_search_tool import RealEstateSearchTool
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool

__all__ = [
    "HybridLegalSearch",
    "MarketDataTool",
    "LoanDataTool",
    "RealEstateSearchTool",
    "ContractAnalysisTool",
    "MarketAnalysisTool",
    "ROICalculatorTool",
    "LoanSimulatorTool",
    "PolicyMatcherTool"
]
```

**업데이트 (신규 tools 추가)**:
```python
# 기존 imports
from .hybrid_legal_search import HybridLegalSearch
from .market_data_tool import MarketDataTool
from .loan_data_tool import LoanDataTool
from .real_estate_search_tool import RealEstateSearchTool
from .contract_analysis_tool import ContractAnalysisTool
from .market_analysis_tool import MarketAnalysisTool
from .roi_calculator_tool import ROICalculatorTool
from .loan_simulator_tool import LoanSimulatorTool
from .policy_matcher_tool import PolicyMatcherTool

# 신규 imports (tests/backend에서 병합)
from .legal_search_tool import LegalSearch
from .building_registry_tool import BuildingRegistryTool
from .infrastructure_tool import InfrastructureTool
from .realestate_terminology import RealEstateTerminology

# Alias for backward compatibility
# Tool 이름 우선순위: tests/backend
LegalSearchTool = LegalSearch  # 기본 이름

__all__ = [
    # 기존
    "HybridLegalSearch",
    "MarketDataTool",
    "LoanDataTool",
    "RealEstateSearchTool",
    "ContractAnalysisTool",
    "MarketAnalysisTool",
    "ROICalculatorTool",
    "LoanSimulatorTool",
    "PolicyMatcherTool",
    # 신규
    "LegalSearch",
    "LegalSearchTool",  # Alias
    "BuildingRegistryTool",
    "InfrastructureTool",
    "RealEstateTerminology"
]
```

#### 2.3 Tool Import 검증

**검증 스크립트**:
```python
# test_tool_imports.py
import sys
sys.path.insert(0, "C:\\kdy\\Projects\\holmesnyangz\\beta_v001\\backend")

try:
    from app.service_agent.tools import (
        LegalSearch,
        BuildingRegistryTool,
        InfrastructureTool,
        RealEstateTerminology
    )
    print("✅ All new tools imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

---

### Phase 3: Foundation 병합 (30분)

#### 3.1 agent_registry.py 비교

**작업 방법**:
1. diff 도구로 비교
2. tests/backend의 신규 agent 등록 확인
3. 수동으로 병합

**예상 변경 사항**:
- 신규 tool 등록 (LegalSearch, BuildingRegistryTool 등)
- AgentRegistry.list_agents() 업데이트

#### 3.2 separated_states.py 비교

**작업 방법**:
1. diff 도구로 비교
2. 새로운 State 필드 확인
3. 필요 시 병합

**예상 변경 사항**:
- SearchTeamState에 새로운 필드 추가 가능
- 공공데이터 관련 State 추가 가능

**주의사항**:
- State 변경은 전체 시스템에 영향
- 변경 최소화
- 테스트 철저히

---

### Phase 4: Execution Agents 병합 (60분)

#### 4.1 SearchExecutor 병합

**병합 전략**: backend 코드를 기본으로, tests의 도구 초기화만 추가

**현재 (backend)**:
```python
def __init__(self, llm_context=None, progress_callback=None):
    self.llm_context = llm_context
    self.progress_callback = progress_callback  # 유지

    # 기존 tools
    self.legal_search_tool = None
    self.market_data_tool = None
    self.real_estate_search_tool = None
    self.loan_data_tool = None

    # 기존 초기화
    from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
    self.legal_search_tool = HybridLegalSearch()
```

**병합 후**:
```python
def __init__(self, llm_context=None, progress_callback=None):
    self.llm_context = llm_context
    self.progress_callback = progress_callback  # backend 유지

    # 기존 tools
    self.legal_search_tool = None
    self.market_data_tool = None
    self.real_estate_search_tool = None
    self.loan_data_tool = None

    # 신규 tools (tests/backend에서 추가)
    self.building_registry_tool = None
    self.infrastructure_tool = None
    self.terminology_tool = None

    # Legal Search 초기화 (tests 이름 채택, backend 코드 유지)
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
            logger.info("Fallback to HybridLegalSearch")
        except Exception as e2:
            logger.error(f"Both LegalSearch attempts failed: {e2}")

    # 기존 tools 초기화 (유지)
    try:
        from app.service_agent.tools.market_data_tool import MarketDataTool
        self.market_data_tool = MarketDataTool()
    except Exception as e:
        logger.warning(f"MarketDataTool initialization failed: {e}")

    try:
        from app.service_agent.tools.loan_data_tool import LoanDataTool
        self.loan_data_tool = LoanDataTool()
    except Exception as e:
        logger.warning(f"LoanDataTool initialization failed: {e}")

    try:
        from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool
        self.real_estate_search_tool = RealEstateSearchTool()
    except Exception as e:
        logger.warning(f"RealEstateSearchTool initialization failed: {e}")

    # 신규 tools 초기화 (tests/backend에서 추가)
    try:
        from app.service_agent.tools.building_registry_tool import BuildingRegistryTool
        self.building_registry_tool = BuildingRegistryTool()
        logger.info("BuildingRegistryTool initialized successfully")
    except Exception as e:
        logger.warning(f"BuildingRegistryTool initialization failed: {e}")

    try:
        from app.service_agent.tools.infrastructure_tool import InfrastructureTool
        self.infrastructure_tool = InfrastructureTool()
        logger.info("InfrastructureTool initialized successfully")
    except Exception as e:
        logger.warning(f"InfrastructureTool initialization failed: {e}")

    try:
        from app.service_agent.tools.realestate_terminology import RealEstateTerminology
        self.terminology_tool = RealEstateTerminology()
        logger.info("RealEstateTerminology initialized successfully")
    except Exception as e:
        logger.warning(f"RealEstateTerminology initialization failed: {e}")
```

**변경 요약**:
- ✅ progress_callback 유지 (backend)
- ✅ 신규 tool 속성 추가 (tests)
- ✅ LegalSearch 이름 채택, fallback 로직 추가
- ✅ 신규 tool 초기화 추가

#### 4.2 AnalysisExecutor 병합

**병합 전략**: backend 코드 유지, LegalSearch tool만 추가

**현재 (backend)**:
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
    self.progress_callback = progress_callback  # 유지
    self.team_name = "analysis"

    # 분석 도구 초기화
    self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
    self.market_tool = MarketAnalysisTool(llm_service=self.llm_service)
    self.roi_tool = ROICalculatorTool()
    self.loan_tool = LoanSimulatorTool()
    self.policy_tool = PolicyMatcherTool()
```

**병합 후**:
```python
from app.service_agent.tools import (
    ContractAnalysisTool,
    MarketAnalysisTool,
    ROICalculatorTool,
    LoanSimulatorTool,
    PolicyMatcherTool,
    LegalSearch  # 신규 추가
)

def __init__(self, llm_context=None, progress_callback=None):
    self.llm_context = llm_context
    self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
    self.progress_callback = progress_callback  # backend 유지
    self.team_name = "analysis"

    # 분석 도구 초기화 (기존)
    self.contract_tool = ContractAnalysisTool(llm_service=self.llm_service)
    self.market_tool = MarketAnalysisTool(llm_service=self.llm_service)
    self.roi_tool = ROICalculatorTool()
    self.loan_tool = LoanSimulatorTool()
    self.policy_tool = PolicyMatcherTool()

    # 법률 검색 도구 추가 (tests/backend에서)
    try:
        self.legal_search_tool = LegalSearch()
        logger.info("LegalSearch initialized in AnalysisExecutor")
    except Exception as e:
        logger.warning(f"LegalSearch initialization failed in AnalysisExecutor: {e}")
        self.legal_search_tool = None
```

**변경 요약**:
- ✅ progress_callback 유지 (backend)
- ✅ LegalSearch tool 추가 (tests)
- ✅ Import 문 업데이트

---

### Phase 5: 테스트 및 검증 (60-120분)

#### 5.1 Import 검증

**검증 스크립트 1: Tools**
```python
# verify_tools.py
import sys
sys.path.insert(0, "C:\\kdy\\Projects\\holmesnyangz\\beta_v001\\backend")

def verify_tools():
    """모든 tool import 검증"""
    tools_to_test = [
        ("LegalSearch", "app.service_agent.tools"),
        ("BuildingRegistryTool", "app.service_agent.tools"),
        ("InfrastructureTool", "app.service_agent.tools"),
        ("RealEstateTerminology", "app.service_agent.tools"),
        ("HybridLegalSearch", "app.service_agent.tools"),  # Backward compat
    ]

    results = []
    for tool_name, module_path in tools_to_test:
        try:
            module = __import__(module_path, fromlist=[tool_name])
            tool_class = getattr(module, tool_name)
            print(f"✅ {tool_name} import successful")
            results.append((tool_name, True, None))
        except Exception as e:
            print(f"❌ {tool_name} import failed: {e}")
            results.append((tool_name, False, str(e)))

    return results

if __name__ == "__main__":
    results = verify_tools()
    success_count = sum(1 for _, success, _ in results if success)
    print(f"\n{success_count}/{len(results)} tools imported successfully")
```

**검증 스크립트 2: Execution Agents**
```python
# verify_executors.py
import sys
sys.path.insert(0, "C:\\kdy\\Projects\\holmesnyangz\\beta_v001\\backend")

def verify_executors():
    """Execution agents import 및 초기화 검증"""
    try:
        from app.service_agent.execution_agents.search_executor import SearchExecutor
        print("✅ SearchExecutor import successful")

        # 초기화 테스트
        search_executor = SearchExecutor(llm_context=None, progress_callback=None)
        print(f"   - legal_search_tool: {search_executor.legal_search_tool is not None}")
        print(f"   - building_registry_tool: {search_executor.building_registry_tool is not None}")
        print(f"   - infrastructure_tool: {search_executor.infrastructure_tool is not None}")
        print(f"   - terminology_tool: {search_executor.terminology_tool is not None}")

    except Exception as e:
        print(f"❌ SearchExecutor failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        from app.service_agent.execution_agents.analysis_executor import AnalysisExecutor
        print("✅ AnalysisExecutor import successful")

        # 초기화 테스트
        analysis_executor = AnalysisExecutor(llm_context=None, progress_callback=None)
        print(f"   - legal_search_tool: {analysis_executor.legal_search_tool is not None}")

    except Exception as e:
        print(f"❌ AnalysisExecutor failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_executors()
```

#### 5.2 기본 실행 테스트

**테스트 1: LegalSearch 기본 동작**
```python
# test_legal_search.py
import sys
sys.path.insert(0, "C:\\kdy\\Projects\\holmesnyangz\\beta_v001\\backend")

from app.service_agent.tools import LegalSearch

def test_legal_search():
    """LegalSearch 기본 동작 테스트"""
    try:
        legal_search = LegalSearch()
        print("✅ LegalSearch initialized")

        # 간단한 검색 테스트
        result = legal_search.search(
            query="전세 계약",
            top_k=3
        )
        print(f"✅ Search returned {len(result.get('results', []))} results")

    except Exception as e:
        print(f"❌ LegalSearch test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_legal_search()
```

**테스트 2: SearchExecutor 통합 테스트**
```python
# test_search_executor_integration.py
import sys
import asyncio
sys.path.insert(0, "C:\\kdy\\Projects\\holmesnyangz\\beta_v001\\backend")

from app.service_agent.execution_agents.search_executor import SearchExecutor
from app.service_agent.foundation.separated_states import SharedState

async def test_search_executor():
    """SearchExecutor 통합 테스트"""
    try:
        # 초기화
        executor = SearchExecutor(llm_context=None, progress_callback=None)
        print("✅ SearchExecutor initialized")

        # State 생성
        shared_state = SharedState(
            query="서울 강남구 전세 매물",
            keywords=["전세", "강남구"],
            session_id="test_session",
            user_id=1
        )

        # 실행 테스트 (간단한 검색만)
        result = await executor.execute(shared_state)
        print(f"✅ SearchExecutor execute completed")
        print(f"   Result keys: {result.keys()}")

    except Exception as e:
        print(f"❌ SearchExecutor integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_executor())
```

#### 5.3 롤백 준비

**롤백 절차**:

1. **문제 발생 시 즉시 롤백**
   ```powershell
   # 백업에서 복원
   $backup = "backend_backup_YYYYMMDD_HHMMSS"  # 실제 백업 이름
   Remove-Item -Path "backend" -Recurse -Force
   Copy-Item -Path $backup -Destination "backend" -Recurse
   ```

2. **Git 롤백**
   ```bash
   git checkout .
   git clean -fd
   ```

3. **부분 롤백 (특정 파일만)**
   ```bash
   git checkout HEAD -- backend/app/service_agent/execution_agents/search_executor.py
   ```

---

## 5. 위험 관리 (Risk Management)

### 5.1 주요 위험 요소

| 위험 | 발생 가능성 | 영향도 | 완화 방안 |
|------|-----------|-------|----------|
| Import 오류 | 높음 | 높음 | - 단계별 import 검증<br>- Fallback 로직 추가 |
| API 키 누락 | 중간 | 중간 | - 환경 변수 체크리스트<br>- 에러 핸들링 강화 |
| DB 경로 오류 | 중간 | 높음 | - 경로 설정 검증<br>- 상대 경로 사용 |
| 성능 저하 | 낮음 | 중간 | - 프로파일링<br>- 캐싱 고려 |
| 호환성 문제 | 중간 | 높음 | - Backward compatibility<br>- Alias 사용 |

### 5.2 완화 전략

#### 전략 1: Import Fallback
```python
# 예시: SearchExecutor
try:
    from app.service_agent.tools.legal_search_tool import LegalSearch
    self.legal_search_tool = LegalSearch()
except Exception as e:
    logger.warning(f"LegalSearch failed, using HybridLegalSearch: {e}")
    try:
        from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch
        self.legal_search_tool = HybridLegalSearch()
    except Exception as e2:
        logger.error(f"Both LegalSearch attempts failed: {e2}")
        self.legal_search_tool = None
```

#### 전략 2: Tool 이름 Alias
```python
# tools/__init__.py
from .legal_search_tool import LegalSearch
from .hybrid_legal_search import HybridLegalSearch

# Backward compatibility
LegalSearchTool = LegalSearch  # 기본 이름
HybridLegalSearchTool = HybridLegalSearch  # 구 이름 유지
```

#### 전략 3: 환경 변수 체크
```python
# config 검증
import os
required_env_vars = [
    "SQLITE_DB_PATH",
    "FAISS_INDEX_PATH",
    "EMBEDDING_MODEL_PATH",
    "PUBLIC_API_KEY"  # 공공데이터 API
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.warning(f"Missing environment variables: {missing_vars}")
```

---

## 6. 테스트 체크리스트 (Test Checklist)

### 6.1 Unit Tests

- [ ] **LegalSearch**
  - [ ] 초기화 성공
  - [ ] 검색 기능 동작
  - [ ] SQLite 연결 확인
  - [ ] FAISS 인덱스 로딩 확인
  - [ ] 에러 핸들링 검증

- [ ] **BuildingRegistryTool**
  - [ ] 초기화 성공
  - [ ] API 호출 성공
  - [ ] 응답 파싱 정상
  - [ ] API 키 오류 핸들링

- [ ] **InfrastructureTool**
  - [ ] 초기화 성공
  - [ ] API 호출 성공
  - [ ] 데이터 변환 정상

- [ ] **RealEstateTerminology**
  - [ ] 초기화 성공
  - [ ] 용어 검색 동작
  - [ ] 관련 용어 추천 동작

### 6.2 Integration Tests

- [ ] **SearchExecutor**
  - [ ] 모든 tool 초기화 확인
  - [ ] progress_callback 동작 확인
  - [ ] 검색 workflow 실행 확인
  - [ ] 신규 tool 호출 확인

- [ ] **AnalysisExecutor**
  - [ ] LegalSearch tool 사용 확인
  - [ ] 기존 분석 로직 정상 동작
  - [ ] progress_callback 동작 확인

- [ ] **Supervisor Integration**
  - [ ] SearchExecutor 호출 정상
  - [ ] AnalysisExecutor 호출 정상
  - [ ] WebSocket 메시지 전송 정상

### 6.3 End-to-End Tests

- [ ] **전체 워크플로우**
  - [ ] 사용자 쿼리 입력
  - [ ] PlanningAgent 동작
  - [ ] SearchExecutor 실행 (신규 tools 포함)
  - [ ] AnalysisExecutor 실행 (LegalSearch 포함)
  - [ ] 최종 응답 생성
  - [ ] WebSocket 메시지 수신 확인

- [ ] **에러 시나리오**
  - [ ] Tool 초기화 실패 시 동작
  - [ ] API 호출 실패 시 동작
  - [ ] DB 연결 실패 시 동작

---

## 7. 후속 작업 (Follow-up Tasks)

### 7.1 문서화
- [ ] 신규 tools 사용법 문서 작성
- [ ] API 키 설정 가이드 작성
- [ ] 환경 변수 설정 가이드 업데이트
- [ ] 시스템 아키텍처 다이어그램 업데이트

### 7.2 최적화
- [ ] LegalSearch 성능 프로파일링
- [ ] 공공데이터 API 호출 캐싱
- [ ] FAISS 인덱스 최적화
- [ ] 메모리 사용량 모니터링

### 7.3 모니터링
- [ ] 신규 tool 사용률 추적
- [ ] 에러 로그 모니터링
- [ ] 성능 메트릭 수집
- [ ] 사용자 피드백 수집

---

## 8. 참고 자료 (References)

### 8.1 시스템 문서
- [COMPREHENSIVE_ANALYSIS_251029.md](../Manual/COMPREHENSIVE_ANALYSIS_251029.md) - 시스템 전체 분석

### 8.2 코드 위치
- **backend**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend`
- **tests/backend**: `C:\kdy\Projects\holmesnyangz\beta_v001\tests\backend`

### 8.3 주요 파일

| 파일 경로 | 설명 |
|----------|------|
| [backend/app/service_agent/execution_agents/search_executor.py](../../backend/app/service_agent/execution_agents/search_executor.py) | 메인 SearchExecutor |
| [backend/app/service_agent/execution_agents/analysis_executor.py](../../backend/app/service_agent/execution_agents/analysis_executor.py) | 메인 AnalysisExecutor |
| [tests/backend/app/service_agent/tools/legal_search_tool.py](../../tests/backend/app/service_agent/tools/legal_search_tool.py) | 신규 LegalSearch |
| [tests/backend/app/service_agent/tools/building_registry_tool.py](../../tests/backend/app/service_agent/tools/building_registry_tool.py) | 건축물대장 Tool |
| [tests/backend/app/service_agent/tools/infrastructure_tool.py](../../tests/backend/app/service_agent/tools/infrastructure_tool.py) | 인프라 Tool |

---

## 9. 승인 및 실행 (Approval & Execution)

### 9.1 실행 전 확인 사항
- [ ] 백업 완료 확인
- [ ] Git 커밋 생성 확인
- [ ] 의존성 설치 확인
- [ ] 환경 변수 설정 확인
- [ ] 테스트 환경 준비 완료

### 9.2 실행 담당자
- **병합 작업**: [담당자 이름]
- **코드 리뷰**: [리뷰어 이름]
- **테스트 검증**: [테스터 이름]

### 9.3 실행 일정
- **예정일**: 2025-10-29
- **예상 소요 시간**: 4-6시간
- **완료 목표**: 당일 종료

### 9.4 연락처
- **문의사항**: 사용자에게 확인
- **긴급 상황**: 즉시 롤백 실행

---

## 10. 결론 (Conclusion)

본 계획서는 `tests/backend`의 execution_agent와 tool 수정사항을 `backend` 코드베이스에 안전하게 병합하기 위한 상세 가이드입니다.

**핵심 원칙**:
1. ✅ **코드 우선순위**: backend 코드 구조 유지
2. ✅ **Tool 이름 우선순위**: tests/backend 이름 채택
3. ✅ **점진적 병합**: 5단계로 나누어 안전하게 진행
4. ✅ **롤백 준비**: 각 단계마다 백업 및 검증
5. ✅ **하위 호환성**: Alias 및 Fallback 로직으로 기존 코드 보호

**예상 결과**:
- 신규 공공데이터 API tools 통합
- 법률 검색 기능 강화 (LegalSearch)
- 부동산 용어 사전 기능 추가
- 기존 기능 정상 동작 유지

**사용자 확인 필요 사항**:
1. Tool 이름이 `LegalSearch`로 변경되는 것에 동의하시나요? (기존 HybridLegalSearch는 유지)
2. 공공데이터 API 키가 준비되어 있나요?
3. SQLite DB 및 FAISS 인덱스 파일이 준비되어 있나요?

---

**문서 버전**: 1.0
**작성 완료일**: 2025-10-29
**다음 단계**: 사용자 승인 후 Phase 1 실행
