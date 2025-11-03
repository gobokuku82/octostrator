# Cognitive Agents 병합 계획서

**작성일**: 2025-10-29
**대상**: tests/cognitive → backend/app/service_agent 병합
**작성자**: Planning Agent Analysis

---

## 1. 개요

### 1.1 목적
- tests/cognitive 디렉토리의 개선된 planning_agent 및 프롬프트 파일을 기존 backend/app/service_agent에 통합
- 15개 세분화된 의도 카테고리 시스템을 도입하여 더 정확한 사용자 의도 분석 구현
- DB 기반 인프라 검색 기능 강화

### 1.2 파일 위치
- **소스**: `C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive`
- **대상**: `C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent`

---

## 2. 파일 구조 분석

### 2.1 Tests 디렉토리 구조
```
tests/cognitive/
├── cognitive_agents/
│   └── planning_agent.py                    # 15개 카테고리 버전
└── llm_manager/
    └── prompts/
        └── cognitive/
            ├── agent_selection.txt          # 15개 카테고리 대응
            └── intent_analysis.txt          # 상세 예시 포함
```

### 2.2 Backend 디렉토리 구조
```
backend/app/service_agent/
├── cognitive_agents/
│   ├── __init__.py
│   ├── planning_agent.py                    # 10개 카테고리 버전
│   └── query_decomposer.py
└── llm_manager/
    └── prompts/
        └── cognitive/
            ├── agent_selection.txt          # 10개 카테고리 대응
            ├── agent_selection_simple.txt
            ├── intent_analysis.txt          # chat_history 포함
            ├── intent_analysis_LJM.txt
            ├── plan_generation.txt
            └── query_decomposition.txt
```

---

## 3. 상세 차이점 분석

### 3.1 planning_agent.py 비교

#### A. 의도 카테고리 (IntentType Enum)

**Tests 버전 (15개 카테고리)**:
```python
class IntentType(Enum):
    TERM_DEFINITION = "용어설명"              # 추가
    LEGAL_INQUIRY = "법률해설"
    LOAN_SEARCH = "대출상품검색"             # 분리
    LOAN_COMPARISON = "대출조건비교"         # 분리
    BUILDING_REGISTRY = "건축물대장조회"     # 추가
    PROPERTY_INFRA_ANALYSIS = "매물인프라분석" # 추가
    PRICE_EVALUATION = "가격평가"            # 추가
    PROPERTY_SEARCH = "매물검색"             # 분리
    PROPERTY_RECOMMENDATION = "맞춤추천"     # 분리
    ROI_CALCULATION = "투자수익률계산"       # 추가
    POLICY_INQUIRY = "정부정책조회"          # 추가
    CONTRACT_CREATION = "계약서생성"
    MARKET_INQUIRY = "시세트렌드분석"
    COMPREHENSIVE = "종합분석"
    IRRELEVANT = "무관"
    UNCLEAR = "unclear"                      # 추가
    ERROR = "error"                          # 추가
```

**기존 버전 (10개 카테고리)**:
```python
class IntentType(Enum):
    LEGAL_CONSULT = "법률상담"
    MARKET_INQUIRY = "시세조회"
    LOAN_CONSULT = "대출상담"
    CONTRACT_CREATION = "계약서작성"
    CONTRACT_REVIEW = "계약서검토"           # 기존만 있음
    COMPREHENSIVE = "종합분석"
    RISK_ANALYSIS = "리스크분석"            # 기존만 있음
    UNCLEAR = "unclear"
    IRRELEVANT = "irrelevant"
    ERROR = "error"
```

#### B. 의도 패턴 (_initialize_intent_patterns)

**Tests 버전**: 15개 카테고리에 대한 상세한 키워드 매핑
- 매우 구체적인 키워드 세트
- 각 카테고리별 10-20개의 키워드
- 예: BUILDING_REGISTRY - "건축물대장", "건물정보", "준공", "용도", "면적", "불법 증축", "주차장", "세대수"

**기존 버전**: 더 일반적인 키워드 매핑
- 자연스러운 표현 추가 강조
- 예: "살다", "거주", "세입자", "집주인" 등

#### C. Agent 추천 로직 (_suggest_agents)

**Tests 버전**:
```python
safe_defaults = {
    IntentType.TERM_DEFINITION: ["search_team"],
    IntentType.LEGAL_INQUIRY: ["search_team"],
    IntentType.LOAN_SEARCH: ["search_team"],
    IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
    IntentType.BUILDING_REGISTRY: ["search_team"],
    IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
    IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
    IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
    IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
    IntentType.ROI_CALCULATION: ["analysis_team"],
    IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
    IntentType.CONTRACT_CREATION: ["document_team"],
    IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
    IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
    # ...
}
```

**기존 버전**:
```python
safe_defaults = {
    IntentType.LEGAL_CONSULT: ["search_team"],
    IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
    IntentType.LOAN_CONSULT: ["search_team", "analysis_team"],
    IntentType.CONTRACT_CREATION: ["document_team"],
    IntentType.CONTRACT_REVIEW: ["search_team", "analysis_team"],
    IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
    IntentType.RISK_ANALYSIS: ["search_team", "analysis_team"],
    # ...
}
```

#### D. 실행 전략 결정 (_determine_strategy)

**Tests 버전**:
```python
# 매우 구체적인 병렬 처리 의도 정의
parallel_intents = [
    IntentType.COMPREHENSIVE,
    IntentType.LOAN_COMPARISON,
    IntentType.PROPERTY_RECOMMENDATION,
    IntentType.PROPERTY_INFRA_ANALYSIS,
]

# 파이프라인 처리 의도
pipeline_intents = [
    IntentType.CONTRACT_CREATION,
    IntentType.ROI_CALCULATION,
]

# 조건부 처리 의도
conditional_intents = [
    IntentType.PRICE_EVALUATION,
    IntentType.PROPERTY_SEARCH,
]
```

**기존 버전**:
```python
# 더 간단한 로직
if intent.intent_type in [IntentType.COMPREHENSIVE, IntentType.RISK_ANALYSIS]:
    if len(steps) > 1:
        return ExecutionStrategy.PARALLEL

if "document_agent" in agent_names and "review_agent" in agent_names:
    return ExecutionStrategy.PIPELINE
```

#### E. 추가 기능

**기존 버전만 있는 기능**:
1. Chat History 지원:
   ```python
   chat_history = context.get("chat_history", []) if context else []
   ```

2. reuse_previous_data 기능:
   ```python
   reuse_previous_data = result.get("reuse_previous_data", False)
   if reuse_previous_data:
       entities["reuse_previous_data"] = reuse_previous_data
   ```

3. 키워드 기반 필터 (0차 필터):
   ```python
   if intent_type == IntentType.LEGAL_CONSULT:
       analysis_keywords = ["비교", "분석", "계산", "평가", ...]
       needs_analysis = any(kw in query for kw in analysis_keywords)
   ```

---

### 3.2 프롬프트 파일 비교

#### A. intent_analysis.txt

**Tests 버전 특징**:
- 15개 카테고리 상세 설명
- Tool 유형별 분류 (Search, Search→Analysis, Analysis, Create Docs, Multiple Tools)
- 각 카테고리별 3-5개의 구체적인 예시
- DB 기반 매물 인프라 분석 강조:
  ```
  ### 6. PROPERTY_INFRA_ANALYSIS (매물인프라분석)
  - **Tool**: infrastructure_tool.py (Search → Analysis)
  - **설명**: 특정 위치/아파트 주변의 지하철역, 마트, 병원, 약국,
             초중고 등 인프라 정보 조회 (DB 기반)
  ```

**기존 버전 특징**:
- 9개 카테고리 (더 통합된 분류)
- Chat History 섹션 포함:
  ```
  ## 🔹 최근 대화 기록 (Chat History)
  {chat_history}
  ```
- reuse_previous_data 판단 로직 포함
- 더 간결한 설명

#### B. agent_selection.txt

**Tests 버전 특징**:
- 15개 의도 카테고리 대응 매핑 테이블
- Tool별 상세 설명:
  ```
  - **도구**: realestate_terminology, legal_search, market_data,
             real_estate_search, loan_data, building_registry, policy_matcher
  ```
- 더 많은 few-shot 예시
- 각 의도별 use_cases 상세화

**기존 버전 특징**:
- 9개 의도 카테고리 대응
- 더 간소화된 도구 설명
- CoT 프로세스 강조

---

## 4. 병합 전략

### 4.1 병합 접근 방식

**권장 방식: 하이브리드 접근**

15개 카테고리의 상세함과 기존 버전의 고급 기능(chat_history, reuse_previous_data)을 결합

### 4.2 단계별 병합 전략

#### 단계 1: planning_agent.py 병합

**방식**: 통합 버전 생성 (15개 카테고리 + 기존 고급 기능)

**작업 내역**:
1. IntentType Enum을 15개 카테고리로 확장
2. 기존의 chat_history 지원 유지
3. reuse_previous_data 기능 유지
4. 키워드 기반 0차 필터 유지
5. Tests 버전의 상세한 의도 패턴 도입
6. Tests 버전의 구체적인 실행 전략 로직 도입

**병합 우선순위**:
- **Base**: Tests 버전의 15개 카테고리 체계
- **Add**: 기존 버전의 chat_history 처리
- **Add**: 기존 버전의 reuse_previous_data 처리
- **Add**: 기존 버전의 키워드 필터링
- **Merge**: safe_defaults 딕셔너리 통합

#### 단계 2: intent_analysis.txt 프롬프트 병합

**방식**: Tests 버전을 기반으로 기존 버전의 기능 추가

**작업 내역**:
1. Tests 버전의 15개 카테고리 상세 설명 사용
2. 기존 버전의 Chat History 섹션 추가:
   ```
   ## 🔹 최근 대화 기록 (Chat History)
   {chat_history}
   ```
3. 기존 버전의 reuse_previous_data 판단 로직 추가
4. DB 기반 인프라 분석 설명 유지

#### 단계 3: agent_selection.txt 프롬프트 병합

**방식**: Tests 버전을 기반으로 기존 버전의 CoT 프로세스 강화

**작업 내역**:
1. Tests 버전의 15개 카테고리 매핑 테이블 사용
2. 상세한 Tool 설명 유지
3. 기존 버전의 CoT 프로세스 보강
4. Few-shot 예시 통합

---

## 5. 세부 병합 계획

### 5.1 파일별 작업 내역

#### 파일 1: planning_agent.py

**경로**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**작업 순서**:

1. **백업 생성**
   ```
   경로: backend/app/service_agent/cognitive_agents/planning_agent_backup_251029.py
   ```

2. **IntentType Enum 확장** (Line 32-51)
   ```python
   # 기존 10개 → 15개로 확장
   # 추가 항목:
   - TERM_DEFINITION = "용어설명"
   - LOAN_SEARCH = "대출상품검색"
   - LOAN_COMPARISON = "대출조건비교"
   - BUILDING_REGISTRY = "건축물대장조회"
   - PROPERTY_INFRA_ANALYSIS = "매물인프라분석"
   - PRICE_EVALUATION = "가격평가"
   - PROPERTY_SEARCH = "매물검색"
   - PROPERTY_RECOMMENDATION = "맞춤추천"
   - ROI_CALCULATION = "투자수익률계산"
   - POLICY_INQUIRY = "정부정책조회"

   # 제거 또는 변경:
   - LEGAL_CONSULT → LEGAL_INQUIRY로 명칭 변경
   - MARKET_INQUIRY → 유지 (MARKET_INQUIRY로)
   - LOAN_CONSULT → LOAN_SEARCH/LOAN_COMPARISON으로 분리
   - CONTRACT_REVIEW → 삭제 (COMPREHENSIVE에 통합 가능)
   - RISK_ANALYSIS → 삭제 (COMPREHENSIVE에 통합 가능)
   ```

3. **_initialize_intent_patterns 메서드 확장** (Line 108-176)
   ```python
   # Tests 버전의 15개 카테고리 패턴 도입
   # 기존의 "자연스러운 표현" 키워드는 유지
   # 더 구체적인 키워드 추가
   ```

4. **_analyze_with_llm 메서드 유지** (Line 183-256)
   ```python
   # 기존의 chat_history 처리 로직 유지
   # reuse_previous_data 처리 로직 유지
   # Intent 파싱 로직은 15개 카테고리 대응하도록 수정
   ```

5. **_analyze_with_patterns 메서드 업데이트** (Line 258-303)
   ```python
   # intent_to_agent 딕셔너리를 15개 카테고리로 확장
   intent_to_agent = {
       IntentType.TERM_DEFINITION: ["search_team"],
       IntentType.LEGAL_INQUIRY: ["search_team"],
       IntentType.LOAN_SEARCH: ["search_team"],
       IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
       IntentType.BUILDING_REGISTRY: ["search_team"],
       IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
       IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
       IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
       IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
       IntentType.ROI_CALCULATION: ["analysis_team"],
       IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
       IntentType.CONTRACT_CREATION: ["document_team"],
       IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
       IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
       IntentType.UNCLEAR: ["search_team"],
   }
   ```

6. **_suggest_agents 메서드 업데이트** (Line 305-397)
   ```python
   # 키워드 기반 0차 필터 유지 (기존 버전)
   # 15개 카테고리에 대한 분기 추가

   # safe_defaults 딕셔너리 확장
   safe_defaults = {
       IntentType.TERM_DEFINITION: ["search_team"],
       IntentType.LEGAL_INQUIRY: ["search_team"],
       IntentType.LOAN_SEARCH: ["search_team"],
       IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
       IntentType.BUILDING_REGISTRY: ["search_team"],
       IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
       IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
       IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
       IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
       IntentType.ROI_CALCULATION: ["analysis_team"],
       IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
       IntentType.CONTRACT_CREATION: ["document_team"],
       IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
       IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
       IntentType.IRRELEVANT: ["search_team"],
       IntentType.UNCLEAR: ["search_team", "analysis_team"],
       IntentType.ERROR: ["search_team", "analysis_team"]
   }
   ```

7. **_select_agents_with_llm 메서드 업데이트** (Line 399-469)
   ```python
   # available_agents 딕셔너리를 15개 카테고리에 맞게 업데이트
   available_agents = {
       "search_team": {
           "name": "search_team",
           "capabilities": "법률 검색, 용어 설명, 부동산 시세 조회, 개별 매물 검색, 대출 상품 검색, 건축물대장 조회, 정부 정책 조회",
           "tools": ["realestate_terminology", "legal_search", "market_data",
                    "real_estate_search", "loan_data", "building_registry", "policy_matcher"],
           "use_cases": [
               "용어설명", "법률해설", "대출상품검색", "건축물대장조회",
               "정부정책조회", "매물검색"
           ]
       },
       # ... 나머지 팀 정보
   }
   ```

8. **_determine_strategy 메서드 업데이트** (Line 731-758)
   ```python
   # Tests 버전의 구체적인 전략 결정 로직 도입
   parallel_intents = [
       IntentType.COMPREHENSIVE,
       IntentType.LOAN_COMPARISON,
       IntentType.PROPERTY_RECOMMENDATION,
       IntentType.PROPERTY_INFRA_ANALYSIS,
   ]

   pipeline_intents = [
       IntentType.CONTRACT_CREATION,
       IntentType.ROI_CALCULATION,
   ]

   conditional_intents = [
       IntentType.PRICE_EVALUATION,
       IntentType.PROPERTY_SEARCH,
   ]
   ```

**예상 코드 라인 변경**:
- 추가: ~200 lines
- 수정: ~150 lines
- 삭제: ~50 lines
- 총 영향: ~400 lines

---

#### 파일 2: intent_analysis.txt

**경로**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**작업 순서**:

1. **백업 생성**
   ```
   경로: backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis_backup_251029.txt
   ```

2. **기존 파일 대체 전략**
   - 기존 파일을 `intent_analysis_old.txt`로 리네임
   - Tests 버전을 새로운 `intent_analysis.txt`로 복사

3. **기존 버전의 핵심 기능 추가**

   **3-1. Chat History 섹션 추가** (Line 205 이후 삽입)
   ```
   ---

   ## 🔹 최근 대화 기록 (Chat History)

   이전 대화 맥락을 참고하여 의도를 더 정확히 파악하세요.

   {chat_history}

   ---

   **현재 질문**: {query}

   **분석 지침**:
   1. 위 대화 기록을 참고하여 현재 질문의 맥락을 이해하세요
   2. "그럼", "그거", "그건", "아까" 등의 지시어가 있으면 이전 대화에서 언급된 내용을 찾으세요
   3. 이전 대화와 연결되는 질문이면 부동산 관련 질문으로 처리하세요

   **데이터 재사용 판단**:
   다음과 같은 경우 "reuse_previous_data": true로 설정하세요:
   - "방금", "위", "그", "이전", "아까" 등의 지시어로 이전 데이터를 참조하는 경우
   - "그 데이터로", "그 정보로", "그걸로 분석" 등 이전 정보 활용을 명시하는 경우
   - 문맥상 이전 대화의 검색 결과나 정보를 재사용하려는 의도가 명확한 경우

   ---
   ```

   **3-2. 응답 형식에 reuse_previous_data 필드 추가** (Line 356 수정)
   ```json
   {
       "intent": "LEGAL_INQUIRY",
       "confidence": 0.9,
       "keywords": ["전세금", "인상", "제한"],
       "sub_intents": [],
       "is_compound": false,
       "decomposed_tasks": [],
       "entities": {
           "location": "강남구",
           "price": "5억",
           "contract_type": "전세",
           "date": "2024년",
           "area": "84㎡",
           "action_verbs": ["확인", "검토"]
       },
       "reuse_previous_data": false,    // 추가
       "reasoning": "1단계(유형): 정보 확인형. 2단계(복잡도): 저 - 단일 개념. 3단계(의도): 검색만으로 충분 → LEGAL_INQUIRY"
   }
   ```

   **3-3. 응답 규칙에 reuse_previous_data 설명 추가** (Line 370)
   ```
   - reuse_previous_data: 이전 대화 데이터 재사용 여부 (true/false)
   ```

4. **15개 카테고리 설명 유지**
   - Tests 버전의 상세한 카테고리 설명 유지
   - Tool 유형별 분류 유지
   - Few-shot 예시 유지

**예상 변경**:
- 기존: 227 lines
- Tests: 385 lines
- 통합 후: ~420 lines (+Chat History 섹션)

---

#### 파일 3: agent_selection.txt

**경로**: `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt`

**작업 순서**:

1. **백업 생성**
   ```
   경로: backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection_backup_251029.txt
   ```

2. **기존 파일 대체 전략**
   - 기존 파일을 `agent_selection_old.txt`로 리네임
   - Tests 버전을 새로운 `agent_selection.txt`로 복사
   - 기존 버전의 내용 중 유지할 부분 확인

3. **변경 사항 없음 (Tests 버전이 더 포괄적)**
   - Tests 버전이 15개 카테고리를 모두 포함
   - CoT 프로세스가 더 상세
   - Few-shot 예시가 더 풍부
   - 기존 버전의 핵심 내용이 모두 포함됨

**예상 변경**:
- 기존: 189 lines
- Tests: 198 lines
- 통합 후: 198 lines (Tests 버전 그대로 사용)

---

### 5.2 의존성 파일 검토

병합 과정에서 영향을 받을 수 있는 파일들:

#### 영향 받는 파일들:

1. **backend/app/service_agent/supervisor/team_supervisor.py**
   - IntentType Enum 참조 가능성
   - planning_agent 호출 로직

2. **backend/app/service_agent/cognitive_agents/query_decomposer.py**
   - IntentType 참조 가능성
   - ExecutionMode와 ExecutionStrategy 연동

3. **backend/app/service_agent/llm_manager/prompt_manager.py**
   - 프롬프트 파일 로딩 로직
   - 변수 매핑 확인

4. **테스트 파일들**
   - `tests/test_supervisor_modern.py` (이미 삭제됨)
   - 새로운 테스트 필요

#### 검토 필요 사항:

1. **IntentType 참조 검색**
   ```bash
   grep -r "IntentType\." backend/app/service_agent/ --include="*.py"
   ```

2. **planning_agent import 검색**
   ```bash
   grep -r "from.*planning_agent import" backend/app/ --include="*.py"
   grep -r "import.*planning_agent" backend/app/ --include="*.py"
   ```

3. **프롬프트 이름 참조 검색**
   ```bash
   grep -r "intent_analysis" backend/app/service_agent/ --include="*.py"
   grep -r "agent_selection" backend/app/service_agent/ --include="*.py"
   ```

---

## 6. 단계별 실행 계획

### Phase 1: 준비 단계 (예상 소요: 30분)

#### Step 1.1: 백업 생성
```bash
# 1. planning_agent.py 백업
cp backend/app/service_agent/cognitive_agents/planning_agent.py \
   backend/app/service_agent/cognitive_agents/planning_agent_backup_251029.py

# 2. intent_analysis.txt 백업
cp backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt \
   backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis_backup_251029.txt

# 3. agent_selection.txt 백업
cp backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt \
   backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection_backup_251029.txt
```

#### Step 1.2: 의존성 파일 검토
```bash
# IntentType 참조 검색
grep -r "IntentType\." backend/app/service_agent/ --include="*.py" > reports/merge/intent_type_references.txt

# planning_agent import 검색
grep -r "planning_agent" backend/app/ --include="*.py" > reports/merge/planning_agent_imports.txt

# 프롬프트 참조 검색
grep -r "intent_analysis\|agent_selection" backend/app/service_agent/ --include="*.py" > reports/merge/prompt_references.txt
```

#### Step 1.3: Git 브랜치 생성
```bash
git checkout -b feature/cognitive-agents-merge-15-categories
git add -A
git commit -m "Backup: 병합 전 현재 상태 저장"
```

---

### Phase 2: planning_agent.py 병합 (예상 소요: 2시간)

#### Step 2.1: IntentType Enum 확장

**위치**: Line 32-51

**작업**:
```python
class IntentType(Enum):
    """의도 타입 정의 (15개 카테고리)"""
    # 검색 전용 (Search Only)
    TERM_DEFINITION = "용어설명"              # 신규
    LEGAL_INQUIRY = "법률해설"                # LEGAL_CONSULT에서 변경
    LOAN_SEARCH = "대출상품검색"              # LOAN_CONSULT에서 분리
    BUILDING_REGISTRY = "건축물대장조회"       # 신규

    # 검색 + 분석 (Search + Analysis)
    LOAN_COMPARISON = "대출조건비교"          # LOAN_CONSULT에서 분리
    PROPERTY_INFRA_ANALYSIS = "매물인프라분석" # 신규
    PRICE_EVALUATION = "가격평가"             # 신규
    PROPERTY_SEARCH = "매물검색"              # 신규
    PROPERTY_RECOMMENDATION = "맞춤추천"      # 신규
    POLICY_INQUIRY = "정부정책조회"           # 신규
    MARKET_INQUIRY = "시세트렌드분석"         # 기존

    # 분석 전용 (Analysis Only)
    ROI_CALCULATION = "투자수익률계산"        # 신규

    # 문서 생성 (Document Creation)
    CONTRACT_CREATION = "계약서생성"          # 기존

    # 종합 처리 (Comprehensive)
    COMPREHENSIVE = "종합분석"                # 기존

    # 기타 (Others)
    IRRELEVANT = "무관"                       # 기존
    UNCLEAR = "unclear"                       # 기존
    ERROR = "error"                           # 기존
```

**검증**:
```python
# 모든 IntentType이 올바르게 정의되었는지 확인
for intent in IntentType:
    print(f"{intent.name}: {intent.value}")
```

#### Step 2.2: _initialize_intent_patterns 메서드 확장

**위치**: Line 108-176

**작업**: Tests 버전의 15개 카테고리 패턴을 복사하고, 기존 버전의 "자연스러운 표현" 키워드 추가

```python
def _initialize_intent_patterns(self) -> Dict[IntentType, List[str]]:
    """의도 패턴 초기화 - 15개 카테고리"""
    return {
        IntentType.TERM_DEFINITION: [
            "뭐야", "무엇", "의미", "설명", "개념", "정의", "차이", "란",
            "LTV", "대항력", "분양권", "입주권", "재건축", "재개발", "DSR"
        ],
        IntentType.LEGAL_INQUIRY: [
            "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신", "가능한가요",
            # 기존 버전의 자연스러운 표현 추가
            "살다", "거주", "세입자", "집주인", "임차인", "임대인", "해지", "계약서",
            "주택임대차보호법", "확정일자", "대항력", "인상", "계약금", "위약금", "등기", "청약", "당첨"
        ],
        # ... (나머지 13개 카테고리)
    }
```

#### Step 2.3: _analyze_with_llm 메서드 유지

**위치**: Line 183-256

**작업**: 기존 버전의 chat_history 및 reuse_previous_data 로직 유지, Intent 파싱만 15개 카테고리로 수정

```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    """LLM을 사용한 의도 분석 (LLMService 사용)"""
    try:
        # Context에서 chat_history 추출 (기존 로직 유지)
        chat_history = context.get("chat_history", []) if context else []

        # Chat history를 문자열로 포맷팅 (기존 로직 유지)
        chat_history_text = ""
        if chat_history:
            formatted_history = []
            for msg in chat_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    formatted_history.append(f"사용자: {content}")
                elif role == "assistant":
                    formatted_history.append(f"AI: {content}")

            if formatted_history:
                chat_history_text = "\n".join(formatted_history)

        # LLMService를 통한 의도 분석
        result = await self.llm_service.complete_json_async(
            prompt_name="intent_analysis",
            variables={
                "query": query,
                "chat_history": chat_history_text  # 기존 로직 유지
            },
            temperature=0.0,
            max_tokens=500
        )

        logger.info(f"LLM Intent Analysis Result: {result}")

        # Intent 타입 파싱 (15개 카테고리 대응)
        intent_str = result.get("intent", "UNCLEAR").upper()
        try:
            intent_type = IntentType[intent_str]
        except KeyError:
            logger.warning(f"Unknown intent type from LLM: {intent_str}, using UNCLEAR")
            intent_type = IntentType.UNCLEAR

        # Agent 선택 (IRRELEVANT/UNCLEAR은 생략하여 성능 최적화)
        if intent_type in [IntentType.IRRELEVANT, IntentType.UNCLEAR]:
            suggested_agents = []
            logger.info(f"⚡ Skipping agent selection for {intent_type.value}")
        else:
            suggested_agents = await self._suggest_agents(
                intent_type=intent_type,
                query=query,
                keywords=result.get("keywords", [])
            )

        # reuse_previous_data를 entities에 추가 (기존 로직 유지)
        entities = result.get("entities", {})
        reuse_previous_data = result.get("reuse_previous_data", False)

        if reuse_previous_data:
            entities["reuse_previous_data"] = reuse_previous_data

        return IntentResult(
            intent_type=intent_type,
            confidence=result.get("confidence", 0.5),
            keywords=result.get("keywords", []),
            reasoning=result.get("reasoning", ""),
            entities=entities,
            suggested_agents=suggested_agents,
            fallback=False
        )

    except Exception as e:
        logger.error(f"LLM intent analysis failed: {e}")
        raise
```

#### Step 2.4: _analyze_with_patterns 메서드 업데이트

**위치**: Line 258-303

**작업**: intent_to_agent 딕셔너리를 15개 카테고리로 확장

```python
def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
    """패턴 매칭 기반 의도 분석"""
    detected_intents = {}
    found_keywords = []

    # 각 의도 타입별 점수 계산
    for intent_type, patterns in self.intent_patterns.items():
        score = 0
        for pattern in patterns:
            if pattern in query.lower():
                score += 1
                found_keywords.append(pattern)
        if score > 0:
            detected_intents[intent_type] = score

    # 가장 높은 점수의 의도 선택
    if detected_intents:
        best_intent = max(detected_intents.items(), key=lambda x: x[1])
        intent_type = best_intent[0]
        confidence = min(best_intent[1] * 0.3, 1.0)
    else:
        intent_type = IntentType.UNCLEAR
        confidence = 0.0

    # Agent 선택 (패턴 매칭 - fallback)
    intent_to_agent = {
        IntentType.TERM_DEFINITION: ["search_team"],
        IntentType.LEGAL_INQUIRY: ["search_team"],
        IntentType.LOAN_SEARCH: ["search_team"],
        IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
        IntentType.BUILDING_REGISTRY: ["search_team"],
        IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
        IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
        IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
        IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
        IntentType.ROI_CALCULATION: ["analysis_team"],
        IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
        IntentType.CONTRACT_CREATION: ["document_team"],
        IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
        IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
        IntentType.UNCLEAR: ["search_team"],
    }
    suggested_agents = intent_to_agent.get(intent_type, ["search_team"])

    return IntentResult(
        intent_type=intent_type,
        confidence=confidence,
        keywords=found_keywords,
        reasoning="Pattern-based analysis",
        suggested_agents=suggested_agents,
        fallback=True
    )
```

#### Step 2.5: _suggest_agents 메서드 업데이트

**위치**: Line 305-397

**작업**:
1. 기존 버전의 키워드 기반 0차 필터 유지
2. safe_defaults 딕셔너리를 15개 카테고리로 확장

```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    """
    LLM 기반 Agent 추천 - 다층 Fallback 전략 + 키워드 필터
    """

    # === 0차: 키워드 기반 필터 (경계 케이스 해결) - 기존 로직 유지 ===
    if intent_type == IntentType.LEGAL_INQUIRY:
        analysis_keywords = [
            "비교", "분석", "계산", "평가", "추천", "검토",
            "어떻게", "방법", "차이", "장단점", "괜찮아",
            "해야", "대응", "해결", "조치", "문제"
        ]
        needs_analysis = any(kw in query for kw in analysis_keywords)

        if not needs_analysis:
            logger.info(f"✅ LEGAL_INQUIRY without analysis keywords → search_team only")
            return ["search_team"]
        else:
            logger.info(f"✅ LEGAL_INQUIRY with analysis keywords → search + analysis")
            return ["search_team", "analysis_team"]

    if intent_type == IntentType.MARKET_INQUIRY:
        analysis_keywords = ["비교", "분석", "평가", "추천", "차이", "장단점"]
        needs_analysis = any(kw in query for kw in analysis_keywords)

        if not needs_analysis:
            logger.info(f"✅ MARKET_INQUIRY without analysis keywords → search_team only")
            return ["search_team"]

    # === 1차: Primary LLM으로 Agent 선택 ===
    if self.llm_service:
        try:
            agents = await self._select_agents_with_llm(
                intent_type=intent_type,
                query=query,
                keywords=keywords,
                attempt=1
            )
            if agents:
                logger.info(f"✅ Primary LLM selected agents: {agents}")
                return agents
        except Exception as e:
            logger.warning(f"⚠️ Primary LLM agent selection failed: {e}")

    # === 2차: Simplified prompt retry ===
    if self.llm_service:
        try:
            agents = await self._select_agents_with_llm_simple(
                intent_type=intent_type,
                query=query
            )
            if agents:
                logger.info(f"✅ Simplified LLM selected agents: {agents}")
                return agents
        except Exception as e:
            logger.warning(f"⚠️ Simplified LLM agent selection failed: {e}")

    # === 3차: Safe default agents (15개 카테고리 대응) ===
    logger.error("⚠️ All LLM attempts failed, using safe default agents")

    safe_defaults = {
        IntentType.TERM_DEFINITION: ["search_team"],
        IntentType.LEGAL_INQUIRY: ["search_team"],
        IntentType.LOAN_SEARCH: ["search_team"],
        IntentType.LOAN_COMPARISON: ["search_team", "analysis_team"],
        IntentType.BUILDING_REGISTRY: ["search_team"],
        IntentType.PROPERTY_INFRA_ANALYSIS: ["search_team", "analysis_team"],
        IntentType.PRICE_EVALUATION: ["search_team", "analysis_team"],
        IntentType.PROPERTY_SEARCH: ["search_team", "analysis_team"],
        IntentType.PROPERTY_RECOMMENDATION: ["search_team", "analysis_team"],
        IntentType.ROI_CALCULATION: ["analysis_team"],
        IntentType.POLICY_INQUIRY: ["search_team", "analysis_team"],
        IntentType.CONTRACT_CREATION: ["document_team"],
        IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
        IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
        IntentType.IRRELEVANT: ["search_team"],
        IntentType.UNCLEAR: ["search_team", "analysis_team"],
        IntentType.ERROR: ["search_team", "analysis_team"]
    }

    result = safe_defaults.get(intent_type, ["search_team", "analysis_team"])
    logger.info(f"Safe default agents for {intent_type.value}: {result}")
    return result
```

#### Step 2.6: _select_agents_with_llm 메서드 업데이트

**위치**: Line 399-469

**작업**: available_agents 딕셔너리를 15개 카테고리의 use_cases로 업데이트

```python
async def _select_agents_with_llm(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str],
    attempt: int = 1
) -> List[str]:
    """LLM을 사용한 Agent 선택 (상세 버전)"""

    # 사용 가능한 Agent 정보 수집 (15개 카테고리 대응)
    available_agents = {
        "search_team": {
            "name": "search_team",
            "capabilities": "법률 검색, 용어 설명, 부동산 시세 조회, 개별 매물 검색, 대출 상품 검색, 건축물대장 조회, 정부 정책 조회",
            "tools": ["realestate_terminology", "legal_search", "market_data", "real_estate_search", "loan_data", "building_registry", "policy_matcher"],
            "use_cases": [
                "용어설명", "법률해설", "대출상품검색", "건축물대장조회", "정부정책조회", "매물검색"
            ]
        },
        "analysis_team": {
            "name": "analysis_team",
            "capabilities": "데이터 분석, 가격 평가, 인프라 분석, 투자 수익률 계산, 리스크 평가, 추천",
            "tools": ["contract_analysis", "market_analysis", "roi_calculator", "infrastructure", "loan_simulator"],
            "use_cases": [
                "대출조건비교", "매물인프라분석", "가격평가", "매물검색",
                "맞춤추천", "투자수익률계산", "종합분석"
            ]
        },
        "document_team": {
            "name": "document_team",
            "capabilities": "계약서 작성, 문서 생성, 문서 검토",
            "tools": ["lease_contract_generator"],
            "use_cases": ["계약서생성"]
        }
    }

    try:
        result = await self.llm_service.complete_json_async(
            prompt_name="agent_selection",
            variables={
                "query": query,
                "intent_type": intent_type.value,
                "keywords": keywords,
                "available_agents": available_agents,
                "attempt": attempt
            },
            temperature=0.1 if attempt == 1 else 0.3
        )

        selected = result.get("selected_agents", [])
        reasoning = result.get("reasoning", "")

        logger.info(f"LLM agent selection reasoning: {reasoning}")

        # 유효성 검사
        valid_agents = [a for a in selected if a in available_agents]

        if not valid_agents:
            logger.warning("LLM returned no valid agents")
            return []

        return valid_agents

    except Exception as e:
        logger.error(f"LLM agent selection failed: {e}")
        raise
```

#### Step 2.7: _determine_strategy 메서드 업데이트

**위치**: Line 731-758

**작업**: Tests 버전의 구체적인 전략 결정 로직 도입

```python
def _determine_strategy(self, intent: IntentResult, steps: List[ExecutionStep]) -> ExecutionStrategy:
    """실행 전략 결정"""
    # 의존성이 있는 경우
    has_dependencies = any(step.dependencies for step in steps)
    if has_dependencies:
        return ExecutionStrategy.SEQUENTIAL

    # 병렬 처리: 여러 독립적인 데이터 소스 조회가 필요한 경우
    parallel_intents = [
        IntentType.COMPREHENSIVE,              # 종합분석 - 여러 관점에서 동시 분석
        IntentType.LOAN_COMPARISON,            # 대출비교 - 여러 은행 상품 동시 조회
        IntentType.PROPERTY_RECOMMENDATION,    # 맞춤추천 - 시세/인프라/법률 동시 분석
        IntentType.PROPERTY_INFRA_ANALYSIS,    # 매물인프라분석 - 지하철/마트/병원/학교 동시 조회
    ]
    if intent.intent_type in parallel_intents and len(steps) > 1:
        return ExecutionStrategy.PARALLEL

    # 파이프라인 처리: 순차적이지만 스트리밍 방식으로 처리 가능한 경우
    pipeline_intents = [
        IntentType.CONTRACT_CREATION,       # 계약서생성 - 생성 → 검토 파이프라인
        IntentType.ROI_CALCULATION,         # 투자수익률 - 데이터수집 → 계산 → 시뮬레이션
    ]
    agent_names = [step.agent_name for step in steps]
    if intent.intent_type in pipeline_intents:
        return ExecutionStrategy.PIPELINE
    # 레거시: document_agent + review_agent 조합도 파이프라인
    if "document_agent" in agent_names and "review_agent" in agent_names:
        return ExecutionStrategy.PIPELINE

    # 조건부 처리: 이전 결과에 따라 다음 단계가 달라지는 경우
    conditional_intents = [
        IntentType.PRICE_EVALUATION,        # 가격평가 - 시세 확인 후 추가 분석 필요 여부 판단
        IntentType.PROPERTY_SEARCH,         # 매물검색 - 검색 결과에 따라 추가 필터링 여부 결정
    ]
    if intent.intent_type in conditional_intents and len(steps) > 1:
        return ExecutionStrategy.CONDITIONAL

    # 순차 처리: 기본값 및 단순 조회
    # TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY, POLICY_INQUIRY 등
    return ExecutionStrategy.SEQUENTIAL
```

#### Step 2.8: 검증 및 테스트

```bash
# Python 구문 검사
python -m py_compile backend/app/service_agent/cognitive_agents/planning_agent.py

# Import 테스트
python -c "from backend.app.service_agent.cognitive_agents.planning_agent import PlanningAgent; print('Import successful')"
```

---

### Phase 3: 프롬프트 파일 병합 (예상 소요: 1시간)

#### Step 3.1: intent_analysis.txt 병합

**작업**:

1. 기존 파일 리네임
   ```bash
   mv backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt \
      backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis_old.txt
   ```

2. Tests 버전 복사
   ```bash
   cp tests/cognitive/llm_manager/prompts/cognitive/intent_analysis.txt \
      backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt
   ```

3. Chat History 섹션 추가

   **파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`
   **위치**: Line 384 (파일 끝에서 두 번째 줄, "분석할 질문: {query}" 앞)

   **추가 내용**:
   ```
   ---

   ## 🔹 최근 대화 기록 (Chat History)

   이전 대화 맥락을 참고하여 의도를 더 정확히 파악하세요.

   {chat_history}

   ---

   **현재 질문**: {query}

   **분석 지침**:
   1. 위 대화 기록을 참고하여 현재 질문의 맥락을 이해하세요
   2. "그럼", "그거", "그건", "아까" 등의 지시어가 있으면 이전 대화에서 언급된 내용을 찾으세요
   3. 이전 대화와 연결되는 질문이면 부동산 관련 질문으로 처리하세요

   **데이터 재사용 판단**:
   다음과 같은 경우 "reuse_previous_data": true로 설정하세요:
   - "방금", "위", "그", "이전", "아까" 등의 지시어로 이전 데이터를 참조하는 경우
   - "그 데이터로", "그 정보로", "그걸로 분석" 등 이전 정보 활용을 명시하는 경우
   - 문맥상 이전 대화의 검색 결과나 정보를 재사용하려는 의도가 명확한 경우

   ---

   분석할 질문: {query}
   ```

4. 응답 형식에 reuse_previous_data 추가

   **위치**: Line 356 부근 (응답 형식 예시)

   **수정**:
   ```json
   {
       "intent": "LEGAL_INQUIRY",
       "confidence": 0.9,
       "keywords": ["전세금", "인상", "제한"],
       "sub_intents": [],
       "is_compound": false,
       "decomposed_tasks": [],
       "entities": {
           "location": "강남구",
           "price": "5억",
           "contract_type": "전세",
           "date": "2024년",
           "area": "84㎡",
           "action_verbs": ["확인", "검토"]
       },
       "reuse_previous_data": false,
       "reasoning": "1단계(유형): 정보 확인형. 2단계(복잡도): 저 - 단일 개념. 3단계(의도): 검색만으로 충분 → LEGAL_INQUIRY"
   }
   ```

5. 응답 규칙에 reuse_previous_data 설명 추가

   **위치**: Line 370 부근

   **추가**:
   ```
   - reuse_previous_data: 이전 대화 데이터 재사용 여부 (true/false)
   ```

#### Step 3.2: agent_selection.txt 병합

**작업**:

1. 기존 파일 리네임
   ```bash
   mv backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt \
      backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection_old.txt
   ```

2. Tests 버전 복사 (수정 없이 그대로 사용)
   ```bash
   cp tests/cognitive/llm_manager/prompts/cognitive/agent_selection.txt \
      backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt
   ```

**이유**: Tests 버전이 15개 카테고리를 완전히 포괄하며, 기존 버전의 내용이 이미 포함되어 있음

---

### Phase 4: 의존성 파일 업데이트 (예상 소요: 1시간)

#### Step 4.1: team_supervisor.py 검토 및 수정

**경로**: `backend/app/service_agent/supervisor/team_supervisor.py`

**검토 사항**:
1. IntentType import 확인
2. planning_agent.analyze_intent() 호출 부분
3. intent.intent_type 사용 부분

**예상 수정**:
```python
# 기존 IntentType 참조가 있다면 15개 카테고리 대응하도록 수정
# 예:
# if intent.intent_type == IntentType.LEGAL_CONSULT:
# →
# if intent.intent_type == IntentType.LEGAL_INQUIRY:

# 또는 더 포괄적으로:
if intent.intent_type in [
    IntentType.TERM_DEFINITION,
    IntentType.LEGAL_INQUIRY,
    IntentType.LOAN_SEARCH
]:
    # 검색만 필요한 케이스
    pass
```

#### Step 4.2: query_decomposer.py 검토

**경로**: `backend/app/service_agent/cognitive_agents/query_decomposer.py`

**검토 사항**:
1. IntentType 참조 확인
2. intent_result 파라미터 처리

**예상 작업**:
- 대부분 변경 불필요 (intent_result를 딕셔너리로 받기 때문에 호환성 유지)

#### Step 4.3: prompt_manager.py 검토

**경로**: `backend/app/service_agent/llm_manager/prompt_manager.py`

**검토 사항**:
1. intent_analysis.txt 로딩 확인
2. agent_selection.txt 로딩 확인
3. 변수 매핑 확인 (특히 chat_history)

**예상 작업**:
- 프롬프트 파일 경로가 올바른지 확인
- 변수 매핑이 올바른지 확인

---

### Phase 5: 테스트 및 검증 (예상 소요: 2시간)

#### Step 5.1: 단위 테스트 작성

**파일 생성**: `tests/test_planning_agent_15_categories.py`

```python
import pytest
import asyncio
from backend.app.service_agent.cognitive_agents.planning_agent import (
    PlanningAgent,
    IntentType,
    IntentResult
)

class TestPlanningAgent15Categories:
    """15개 카테고리 Planning Agent 테스트"""

    @pytest.fixture
    def planner(self):
        return PlanningAgent()

    @pytest.mark.asyncio
    async def test_term_definition_intent(self, planner):
        """용어설명 의도 테스트"""
        query = "LTV가 뭐야?"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.TERM_DEFINITION
        assert intent.confidence > 0.5
        assert "search_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_legal_inquiry_intent(self, planner):
        """법률해설 의도 테스트"""
        query = "전세금 5% 인상이 가능한가요?"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.LEGAL_INQUIRY
        assert "search_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_loan_search_intent(self, planner):
        """대출상품검색 의도 테스트"""
        query = "전세자금대출 상품 어떤 게 있어요?"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.LOAN_SEARCH
        assert "search_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_loan_comparison_intent(self, planner):
        """대출조건비교 의도 테스트"""
        query = "KB국민, 신한은행 주택담보대출 금리 비교해줘"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.LOAN_COMPARISON
        assert "search_team" in intent.suggested_agents
        assert "analysis_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_property_infra_analysis_intent(self, planner):
        """매물인프라분석 의도 테스트"""
        query = "강남역 근처 대치초등학교가 있는 매물 확인해줘"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.PROPERTY_INFRA_ANALYSIS
        assert "search_team" in intent.suggested_agents
        assert "analysis_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_roi_calculation_intent(self, planner):
        """투자수익률계산 의도 테스트"""
        query = "5억 아파트 사서 월세 150만원 받으면 수익률이 얼마나 돼요?"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.ROI_CALCULATION
        assert "analysis_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_comprehensive_intent(self, planner):
        """종합분석 의도 테스트"""
        query = "10년 거주했는데 전세금 3억을 10억으로 올려달래. 어떻게 해야 해?"
        intent = await planner.analyze_intent(query)

        assert intent.intent_type == IntentType.COMPREHENSIVE
        assert "search_team" in intent.suggested_agents
        assert "analysis_team" in intent.suggested_agents

    @pytest.mark.asyncio
    async def test_execution_strategy_parallel(self, planner):
        """병렬 실행 전략 테스트"""
        query = "강남구 아파트 시세 확인하고 대출 가능 금액 계산해줘"
        plan = await planner.create_comprehensive_plan(query)

        # LOAN_COMPARISON이면 병렬 처리 가능
        assert plan.strategy in [
            ExecutionStrategy.PARALLEL,
            ExecutionStrategy.SEQUENTIAL
        ]

    @pytest.mark.asyncio
    async def test_chat_history_context(self, planner):
        """Chat History 컨텍스트 테스트"""
        context = {
            "chat_history": [
                {"role": "user", "content": "강남구 아파트 시세 알려줘"},
                {"role": "assistant", "content": "강남구 아파트 평균 시세는..."}
            ]
        }

        query = "그럼 대출은 얼마나 받을 수 있어?"
        intent = await planner.analyze_intent(query, context)

        # UNCLEAR가 아니라 LOAN_CONSULT 또는 LOAN_SEARCH여야 함
        assert intent.intent_type != IntentType.UNCLEAR
        assert intent.intent_type in [
            IntentType.LOAN_SEARCH,
            IntentType.LOAN_COMPARISON
        ]

    def test_all_intents_have_safe_defaults(self, planner):
        """모든 의도가 safe_defaults에 정의되었는지 확인"""
        for intent_type in IntentType:
            # _suggest_agents 내부의 safe_defaults 확인
            # (실제 구현에서는 _suggest_agents를 직접 호출하거나
            #  safe_defaults를 클래스 속성으로 추출해야 함)
            pass
```

#### Step 5.2: 통합 테스트

**파일**: `tests/integration/test_full_flow_15_categories.py`

```python
import pytest
import asyncio
from backend.app.service_agent.supervisor.team_supervisor import TeamSupervisor

class TestFullFlow15Categories:
    """15개 카테고리를 사용한 전체 플로우 통합 테스트"""

    @pytest.fixture
    def supervisor(self):
        return TeamSupervisor()

    @pytest.mark.asyncio
    async def test_term_definition_flow(self, supervisor):
        """용어설명 전체 플로우"""
        result = await supervisor.process_query("LTV가 뭐야?")

        assert result is not None
        assert "LTV" in result["response"]

    @pytest.mark.asyncio
    async def test_property_infra_analysis_flow(self, supervisor):
        """매물인프라분석 전체 플로우"""
        query = "강남역 근처 대치초등학교가 있는 매물 확인해줘"
        result = await supervisor.process_query(query)

        assert result is not None
        # DB 조회 결과 확인

    @pytest.mark.asyncio
    async def test_comprehensive_flow(self, supervisor):
        """종합분석 전체 플로우"""
        query = "10년 거주했는데 전세금 3억을 10억으로 올려달래. 어떻게 해야 해?"
        result = await supervisor.process_query(query)

        assert result is not None
        # 법률 검색 + 분석 결과 확인
```

#### Step 5.3: 수동 테스트

```bash
# 1. Python 인터프리터에서 직접 테스트
python

>>> from backend.app.service_agent.cognitive_agents.planning_agent import PlanningAgent, IntentType
>>> import asyncio
>>> planner = PlanningAgent()
>>>
>>> # 15개 카테고리 확인
>>> for intent in IntentType:
...     print(f"{intent.name}: {intent.value}")
>>>
>>> # 간단한 의도 분석 테스트
>>> async def test():
...     queries = [
...         "LTV가 뭐야?",
...         "전세금 5% 인상이 가능한가요?",
...         "전세자금대출 상품 어떤 게 있어요?",
...         "KB국민, 신한은행 금리 비교해줘"
...     ]
...     for q in queries:
...         intent = await planner.analyze_intent(q)
...         print(f"{q} → {intent.intent_type.value}")
>>>
>>> asyncio.run(test())
```

#### Step 5.4: 프롬프트 로딩 테스트

```bash
# LLM Manager가 새로운 프롬프트를 올바르게 로드하는지 확인
python

>>> from backend.app.service_agent.llm_manager import LLMService
>>> llm = LLMService()
>>>
>>> # intent_analysis 프롬프트 로딩 확인
>>> prompt = llm.prompt_manager.get_prompt("intent_analysis")
>>> print("Chat History 섹션 존재:", "{chat_history}" in prompt)
>>> print("15개 카테고리 존재:", "TERM_DEFINITION" in prompt)
>>> print("reuse_previous_data 존재:", "reuse_previous_data" in prompt)
>>>
>>> # agent_selection 프롬프트 로딩 확인
>>> prompt = llm.prompt_manager.get_prompt("agent_selection")
>>> print("15개 카테고리 매핑 존재:", "BUILDING_REGISTRY" in prompt)
```

---

### Phase 6: 배포 및 모니터링 (예상 소요: 30분)

#### Step 6.1: Git Commit

```bash
# 1. 변경사항 확인
git status
git diff backend/app/service_agent/cognitive_agents/planning_agent.py

# 2. 스테이징
git add backend/app/service_agent/cognitive_agents/planning_agent.py
git add backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt
git add backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt

# 3. 백업 파일도 추가
git add backend/app/service_agent/cognitive_agents/planning_agent_backup_251029.py
git add backend/app/service_agent/llm_manager/prompts/cognitive/*_old.txt
git add backend/app/service_agent/llm_manager/prompts/cognitive/*_backup_251029.txt

# 4. 테스트 파일 추가
git add tests/test_planning_agent_15_categories.py
git add tests/integration/test_full_flow_15_categories.py

# 5. 커밋
git commit -m "feat: Merge 15-category intent system from tests/cognitive

Merged features:
- 15개 의도 카테고리 시스템 도입 (기존 10개 → 15개)
- Tests 버전의 상세한 의도 패턴 및 Agent 매핑
- 기존 버전의 chat_history 및 reuse_previous_data 기능 유지
- DB 기반 매물 인프라 분석 강화
- 구체적인 실행 전략 로직 개선

New IntentTypes:
- TERM_DEFINITION (용어설명)
- LOAN_SEARCH (대출상품검색) - LOAN_CONSULT에서 분리
- LOAN_COMPARISON (대출조건비교) - LOAN_CONSULT에서 분리
- BUILDING_REGISTRY (건축물대장조회)
- PROPERTY_INFRA_ANALYSIS (매물인프라분석)
- PRICE_EVALUATION (가격평가)
- PROPERTY_SEARCH (매물검색)
- PROPERTY_RECOMMENDATION (맞춤추천)
- ROI_CALCULATION (투자수익률계산)
- POLICY_INQUIRY (정부정책조회)

Renamed IntentTypes:
- LEGAL_CONSULT → LEGAL_INQUIRY

Removed IntentTypes:
- CONTRACT_REVIEW (COMPREHENSIVE에 통합)
- RISK_ANALYSIS (COMPREHENSIVE에 통합)

Files changed:
- backend/app/service_agent/cognitive_agents/planning_agent.py
- backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt
- backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt

Tests added:
- tests/test_planning_agent_15_categories.py
- tests/integration/test_full_flow_15_categories.py"
```

#### Step 6.2: Pull Request 생성

**PR 제목**: `feat: Merge 15-category intent system from tests/cognitive`

**PR 설명**:
```markdown
## 개요
tests/cognitive의 개선된 15개 카테고리 의도 분석 시스템을 backend/app/service_agent에 병합합니다.

## 변경 사항

### 1. IntentType 확장 (10개 → 15개)

#### 추가된 카테고리
- `TERM_DEFINITION`: 부동산 용어 설명
- `LOAN_SEARCH`: 대출 상품 검색
- `LOAN_COMPARISON`: 대출 조건 비교
- `BUILDING_REGISTRY`: 건축물대장 조회
- `PROPERTY_INFRA_ANALYSIS`: 매물 인프라 분석 (DB 기반)
- `PRICE_EVALUATION`: 가격 평가
- `PROPERTY_SEARCH`: 매물 검색
- `PROPERTY_RECOMMENDATION`: 맞춤 추천
- `ROI_CALCULATION`: 투자 수익률 계산
- `POLICY_INQUIRY`: 정부 정책 조회

#### 변경된 카테고리
- `LEGAL_CONSULT` → `LEGAL_INQUIRY` (명칭 변경)

#### 삭제된 카테고리
- `CONTRACT_REVIEW` → `COMPREHENSIVE`에 통합
- `RISK_ANALYSIS` → `COMPREHENSIVE`에 통합

### 2. 주요 개선 사항

#### A. 더 정확한 의도 분석
- 15개의 세분화된 카테고리로 사용자 의도를 더 정확히 분류
- 각 카테고리별 상세한 키워드 패턴 정의

#### B. DB 기반 인프라 검색 강화
- `PROPERTY_INFRA_ANALYSIS` 카테고리 신설
- 지하철역, 초중고, 마트, 병원 등 인프라 정보 DB 조회 지원

#### C. 대출 관련 기능 세분화
- `LOAN_SEARCH`: 대출 상품 검색
- `LOAN_COMPARISON`: 대출 조건 비교 분석

#### D. 실행 전략 개선
- 병렬 처리: `LOAN_COMPARISON`, `PROPERTY_INFRA_ANALYSIS` 등
- 파이프라인 처리: `CONTRACT_CREATION`, `ROI_CALCULATION`
- 조건부 처리: `PRICE_EVALUATION`, `PROPERTY_SEARCH`

### 3. 기존 기능 유지

- ✅ Chat History 지원
- ✅ reuse_previous_data 기능
- ✅ 키워드 기반 0차 필터링
- ✅ 다층 Fallback 전략

### 4. 프롬프트 파일 업데이트

- `intent_analysis.txt`: 15개 카테고리 상세 설명, Chat History 섹션 추가
- `agent_selection.txt`: 15개 카테고리 대응 Agent 매핑

## 테스트

- ✅ 단위 테스트: 15개 카테고리별 의도 분석
- ✅ 통합 테스트: 전체 플로우 테스트
- ✅ 수동 테스트: Python 인터프리터 검증
- ✅ 프롬프트 로딩 테스트

## 체크리스트

- [x] 백업 파일 생성
- [x] IntentType Enum 확장
- [x] 의도 패턴 업데이트
- [x] Agent 추천 로직 업데이트
- [x] 실행 전략 로직 업데이트
- [x] 프롬프트 파일 병합
- [x] 테스트 작성 및 실행
- [x] Git 커밋

## Breaking Changes

⚠️ **주의**: 다음 IntentType이 변경되었습니다:
- `LEGAL_CONSULT` → `LEGAL_INQUIRY`
- `CONTRACT_REVIEW` → 삭제 (COMPREHENSIVE 사용)
- `RISK_ANALYSIS` → 삭제 (COMPREHENSIVE 사용)

기존 코드에서 이들을 직접 참조하는 경우 수정이 필요합니다.

## 마이그레이션 가이드

### 코드 수정 예시

**Before**:
```python
if intent.intent_type == IntentType.LEGAL_CONSULT:
    # ...
```

**After**:
```python
if intent.intent_type == IntentType.LEGAL_INQUIRY:
    # ...
```

**또는 더 포괄적으로**:
```python
# 검색만 필요한 케이스
if intent.intent_type in [
    IntentType.TERM_DEFINITION,
    IntentType.LEGAL_INQUIRY,
    IntentType.LOAN_SEARCH,
    IntentType.BUILDING_REGISTRY,
    IntentType.POLICY_INQUIRY
]:
    # 검색 팀만 사용
    pass

# 검색 + 분석이 필요한 케이스
elif intent.intent_type in [
    IntentType.LOAN_COMPARISON,
    IntentType.PROPERTY_INFRA_ANALYSIS,
    IntentType.PRICE_EVALUATION,
    IntentType.PROPERTY_SEARCH,
    IntentType.PROPERTY_RECOMMENDATION,
    IntentType.MARKET_INQUIRY,
    IntentType.COMPREHENSIVE
]:
    # 검색 팀 + 분석 팀 사용
    pass
```

## 관련 이슈

- Resolves #XXX (이슈 번호)

## 리뷰어에게

- [ ] IntentType 변경사항 확인
- [ ] 프롬프트 파일 변경사항 검토
- [ ] 테스트 결과 확인
- [ ] Breaking Changes 영향도 검토
```

#### Step 6.3: 모니터링 계획

**모니터링 지표**:

1. **의도 분석 정확도**
   - 각 의도 카테고리별 분류 정확도
   - UNCLEAR/IRRELEVANT 비율

2. **Agent 선택 정확도**
   - 선택된 Agent가 실제로 쿼리를 처리했는지
   - Fallback 발생 빈도

3. **실행 전략 효율성**
   - 병렬 처리 성공률
   - 평균 실행 시간

4. **Chat History 활용률**
   - reuse_previous_data가 true인 비율
   - 컨텍스트 기반 의도 분석 성공률

**로깅 추가**:
```python
# planning_agent.py에 추가
logger.info(f"Intent Analysis: {intent_type.value} (confidence: {confidence:.2f})")
logger.info(f"Selected Agents: {suggested_agents}")
logger.info(f"Execution Strategy: {strategy.value}")
logger.info(f"Chat History Used: {len(chat_history) > 0}")
logger.info(f"Reuse Previous Data: {reuse_previous_data}")
```

---

## 7. 롤백 계획

병합 후 문제가 발생할 경우를 대비한 롤백 계획

### 7.1 즉시 롤백 (< 10분)

```bash
# 1. Git revert
git revert HEAD

# 또는 브랜치 리셋
git reset --hard HEAD~1

# 2. 백업에서 복원
cp backend/app/service_agent/cognitive_agents/planning_agent_backup_251029.py \
   backend/app/service_agent/cognitive_agents/planning_agent.py

cp backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis_backup_251029.txt \
   backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt

cp backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection_backup_251029.txt \
   backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt

# 3. 서비스 재시작
# (서비스 재시작 명령어)
```

### 7.2 부분 롤백

특정 파일만 문제가 있는 경우:

```bash
# planning_agent.py만 롤백
git checkout HEAD~1 -- backend/app/service_agent/cognitive_agents/planning_agent.py

# 또는 백업에서 복원
cp backend/app/service_agent/cognitive_agents/planning_agent_backup_251029.py \
   backend/app/service_agent/cognitive_agents/planning_agent.py
```

---

## 8. 예상 이슈 및 대응 방안

### 8.1 IntentType 참조 오류

**증상**:
```python
KeyError: 'LEGAL_CONSULT'
AttributeError: type object 'IntentType' has no attribute 'LEGAL_CONSULT'
```

**원인**: 다른 파일에서 변경된 IntentType을 참조

**해결**:
```bash
# 참조 검색
grep -r "IntentType.LEGAL_CONSULT" backend/ --include="*.py"
grep -r "IntentType.CONTRACT_REVIEW" backend/ --include="*.py"
grep -r "IntentType.RISK_ANALYSIS" backend/ --include="*.py"

# 각 파일을 수정
# LEGAL_CONSULT → LEGAL_INQUIRY
# CONTRACT_REVIEW → COMPREHENSIVE
# RISK_ANALYSIS → COMPREHENSIVE
```

### 8.2 프롬프트 변수 오류

**증상**:
```
KeyError: 'chat_history'
```

**원인**: prompt_manager에서 chat_history 변수를 전달하지 않음

**해결**:
```python
# planning_agent.py의 _analyze_with_llm에서
# chat_history가 항상 전달되도록 확인

if context and "chat_history" in context:
    chat_history_text = format_chat_history(context["chat_history"])
else:
    chat_history_text = ""  # 빈 문자열로 기본값 설정
```

### 8.3 LLM 파싱 오류

**증상**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**원인**: LLM이 15개 카테고리를 인식하지 못하고 올바르지 않은 JSON 반환

**해결**:
```python
# planning_agent.py의 _analyze_with_llm에서
# 더 강력한 오류 처리
try:
    intent_type = IntentType[intent_str]
except KeyError:
    logger.warning(f"Unknown intent: {intent_str}, using fallback")
    # Fallback to pattern matching
    return self._analyze_with_patterns(query, context)
```

### 8.4 성능 저하

**증상**: 의도 분석 시간이 기존보다 증가

**원인**:
- 15개 카테고리로 인한 패턴 매칭 오버헤드
- LLM 프롬프트가 길어져서 토큰 수 증가

**해결**:
```python
# 1. 패턴 매칭 최적화
def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
    # 조기 종료 조건 추가
    query_lower = query.lower()

    # 빠른 필터링
    if len(query) < 5:
        return IntentResult(
            intent_type=IntentType.UNCLEAR,
            confidence=0.0,
            keywords=[],
            reasoning="Too short query",
            suggested_agents=["search_team"],
            fallback=True
        )

    # ... (기존 로직)

# 2. LLM 호출 최적화
result = await self.llm_service.complete_json_async(
    prompt_name="intent_analysis",
    variables={"query": query, "chat_history": chat_history_text},
    temperature=0.0,
    max_tokens=300  # 500 → 300으로 감소
)
```

---

## 9. 성공 기준

### 9.1 기능적 성공 기준

- [ ] 15개 모든 의도 카테고리가 올바르게 분류됨
- [ ] Chat History 기반 컨텍스트 분석이 작동함
- [ ] reuse_previous_data 기능이 정상 작동함
- [ ] Agent 선택이 각 의도에 맞게 이루어짐
- [ ] 실행 전략이 의도에 따라 올바르게 결정됨

### 9.2 품질 성공 기준

- [ ] 모든 단위 테스트 통과 (100%)
- [ ] 통합 테스트 통과 (100%)
- [ ] 의도 분석 정확도 > 85%
- [ ] UNCLEAR/IRRELEVANT 비율 < 10%
- [ ] 평균 실행 시간 < 2초

### 9.3 운영적 성공 기준

- [ ] 배포 후 24시간 동안 critical error 없음
- [ ] 롤백 없이 1주일 운영 가능
- [ ] 사용자 피드백 긍정적 (만족도 > 80%)

---

## 10. 타임라인

| Phase | 작업 | 예상 소요 시간 | 담당자 | 상태 |
|-------|------|---------------|--------|------|
| Phase 1 | 준비 단계 | 30분 | - | ⏳ Pending |
| Phase 2 | planning_agent.py 병합 | 2시간 | - | ⏳ Pending |
| Phase 3 | 프롬프트 파일 병합 | 1시간 | - | ⏳ Pending |
| Phase 4 | 의존성 파일 업데이트 | 1시간 | - | ⏳ Pending |
| Phase 5 | 테스트 및 검증 | 2시간 | - | ⏳ Pending |
| Phase 6 | 배포 및 모니터링 | 30분 | - | ⏳ Pending |
| **총계** | | **7시간** | | |

---

## 11. 참고 자료

### 11.1 관련 문서

- [기존 Planning Agent 설계 문서](../architecture/planning_agent_design.md)
- [Intent Analysis 프롬프트 가이드](../prompts/intent_analysis_guide.md)
- [Agent Selection 로직 설명](../architecture/agent_selection.md)

### 11.2 외부 참조

- [LangGraph Cognitive Architecture](https://python.langchain.com/docs/langgraph)
- [Intent Classification Best Practices](https://docs.anthropic.com/claude/docs/prompt-engineering#intent-classification)

---

## 12. 부록

### 12.1 15개 의도 카테고리 전체 매핑

| 번호 | 카테고리 | 한글명 | 주요 키워드 | 추천 Agent | 실행 전략 |
|------|----------|--------|------------|-----------|----------|
| 1 | TERM_DEFINITION | 용어설명 | 뭐야, 무엇, 의미, 설명, 개념 | search_team | Sequential |
| 2 | LEGAL_INQUIRY | 법률해설 | 법, 권리, 의무, 갱신, 가능한가요 | search_team | Sequential |
| 3 | LOAN_SEARCH | 대출상품검색 | 대출, 상품, 찾다, 어떤 게 | search_team | Sequential |
| 4 | LOAN_COMPARISON | 대출조건비교 | 비교, 금리, 한도, 조건, 유리 | search_team, analysis_team | Parallel |
| 5 | BUILDING_REGISTRY | 건축물대장조회 | 건축물대장, 준공, 용도, 면적 | search_team | Sequential |
| 6 | PROPERTY_INFRA_ANALYSIS | 매물인프라분석 | 지하철, 마트, 병원, 학교, 인프라 | search_team, analysis_team | Parallel |
| 7 | PRICE_EVALUATION | 가격평가 | 적정가, 가격 평가, 괜찮아, 비싸 | search_team, analysis_team | Conditional |
| 8 | PROPERTY_SEARCH | 매물검색 | 찾다, 검색, 구하다, 원하다, 매물 | search_team, analysis_team | Conditional |
| 9 | PROPERTY_RECOMMENDATION | 맞춤추천 | 추천, 제안, 적합, 좋은, 맞춤 | search_team, analysis_team | Parallel |
| 10 | ROI_CALCULATION | 투자수익률계산 | 투자, 수익률, ROI, 계산, 유리 | analysis_team | Pipeline |
| 11 | POLICY_INQUIRY | 정부정책조회 | 특별공급, 신혼부부, 청년, 지원 | search_team, analysis_team | Sequential |
| 12 | CONTRACT_CREATION | 계약서생성 | 작성, 만들, 생성, 초안, 계약서 | document_team | Pipeline |
| 13 | MARKET_INQUIRY | 시세트렌드분석 | 시세, 추이, 트렌드, 거래 동향 | search_team, analysis_team | Sequential |
| 14 | COMPREHENSIVE | 종합분석 | 종합, 어떻게, 방법, 해결, 조언 | search_team, analysis_team | Parallel |
| 15 | IRRELEVANT | 무관 | (기타) | - | - |

### 12.2 실행 전략 상세 설명

#### Sequential (순차)
- **설명**: Agent들이 순서대로 하나씩 실행
- **적용**: 의존성이 있거나 단순 조회 작업
- **예시**: search_team → analysis_team

#### Parallel (병렬)
- **설명**: 독립적인 Agent들이 동시에 실행
- **적용**: 여러 독립적인 데이터 소스 조회
- **예시**: search_team (시세) || search_team (인프라) → analysis_team

#### Pipeline (파이프라인)
- **설명**: 이전 결과를 다음 단계로 스트리밍
- **적용**: 생성 → 검토 같은 연속 작업
- **예시**: document_team → review_agent

#### Conditional (조건부)
- **설명**: 이전 결과에 따라 다음 단계 결정
- **적용**: 결과에 따라 추가 분석 필요 여부 판단
- **예시**: search_team → (조건 평가) → analysis_team (필요시)

---

## 결론

이 병합 계획서는 tests/cognitive의 15개 카테고리 시스템을 backend/app/service_agent에 통합하는 상세한 로드맵을 제공합니다.

**핵심 원칙**:
1. **점진적 병합**: 백업을 생성하고 단계별로 진행
2. **하이브리드 접근**: 두 버전의 장점을 모두 활용
3. **테스트 중심**: 각 단계마다 철저한 검증
4. **롤백 대비**: 문제 발생 시 즉시 복구 가능

**예상 효과**:
- 의도 분석 정확도 향상 (10개 → 15개 카테고리)
- DB 기반 인프라 검색 기능 강화
- 더 구체적인 Agent 선택 및 실행 전략
- Chat History 및 컨텍스트 기반 분석 유지

**다음 단계**: Phase 1 준비 단계 시작
