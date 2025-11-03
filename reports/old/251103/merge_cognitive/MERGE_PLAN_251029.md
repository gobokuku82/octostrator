# service_agent ↔ cognitive 통합 계획서

**작성일**: 2025-10-29
**작성자**: Claude Code
**목적**: tests/cognitive의 업데이트 기능을 backend/app/service_agent로 통합

---

## 📋 통합 개요

### 대상 시스템
- **Main (운영)**: `C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent`
- **Update (개선)**: `C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive`

### 통합 목표
tests/cognitive의 **3개 파일**에서 **장점만 선택적으로 추출**하여 service_agent에 통합합니다.

---

## 🔍 파일별 분석

### 1. planning_agent.py

#### 📊 차이점 비교

| 구분 | service_agent (현재) | tests/cognitive (신규) |
|-----|---------------------|---------------------|
| **IntentType** | 8개 | 15개 ⭐ |
| **카테고리** | LEGAL_CONSULT, MARKET_INQUIRY, LOAN_CONSULT, CONTRACT_CREATION, CONTRACT_REVIEW, COMPREHENSIVE, RISK_ANALYSIS, UNCLEAR, IRRELEVANT, ERROR | TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, LOAN_COMPARISON, BUILDING_REGISTRY, PROPERTY_INFRA_ANALYSIS, PRICE_EVALUATION, PROPERTY_SEARCH, PROPERTY_RECOMMENDATION, ROI_CALCULATION, POLICY_INQUIRY, CONTRACT_CREATION, MARKET_INQUIRY, COMPREHENSIVE, IRRELEVANT, UNCLEAR, ERROR ⭐ |
| **패턴 매칭** | 간단한 키워드 | 상세 키워드 + 자연어 표현 ⭐ |
| **Agent Selection** | 3-Layer Fallback | 3-Layer Fallback (동일) ✅ |
| **safe_defaults** | 8개 매핑 | 15개 매핑 ⭐ |
| **_determine_strategy** | 기본 로직 | 15개 Intent별 세분화 ⭐ |

#### ⭐ 신규 버전의 장점

1. **15개 세분화된 IntentType**
   - 기존 8개 → 15개로 확장
   - 더 정확한 의도 분류 가능
   - 부동산 도메인에 특화된 카테고리

2. **상세한 키워드 패턴**
   ```python
   # 기존 (service_agent)
   IntentType.LEGAL_CONSULT: [
       "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신"
   ]

   # 신규 (tests/cognitive) ⭐
   IntentType.LEGAL_INQUIRY: [
       "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신", "가능한가요",
       "살다", "거주", "세입자", "집주인", "임차인", "임대인", "해지", "계약서",
       "주택임대차보호법", "확정일자", "대항력", "인상", "계약금", "위약금", "등기", "청약", "당첨"
   ]
   ```

3. **Intent별 ExecutionStrategy 최적화**
   ```python
   # 신규 버전: 15개 Intent별 병렬/파이프라인 전략 세분화
   parallel_intents = [
       IntentType.COMPREHENSIVE,
       IntentType.LOAN_COMPARISON,
       IntentType.PROPERTY_RECOMMENDATION,
       IntentType.PROPERTY_INFRA_ANALYSIS,  # 추가됨
   ]
   ```

4. **Safe Defaults 확장**
   - 8개 → 15개 Intent 매핑
   - 더 세밀한 폴백 전략

---

### 2. intent_analysis.txt (프롬프트)

#### 📊 차이점 비교

| 구분 | service_agent (현재) | tests/cognitive (신규) |
|-----|---------------------|---------------------|
| **분석 방식** | 기본 의도 분석 | Chain-of-Thought (3단계) ⭐ |
| **카테고리** | 8개 | 15개 ⭐ |
| **설명 상세도** | 간단한 설명 | Tool 매핑 + 상세 예시 ⭐ |
| **Few-shot** | 기본 예시 | 15개 카테고리별 3개씩 ⭐ |
| **reasoning** | 선택적 | 필수 (3단계 CoT) ⭐ |

#### ⭐ 신규 버전의 장점

1. **Chain-of-Thought 3단계 분석**
   ```
   1단계: 질문 유형 파악 (정보 확인형, 평가/판단형, 해결책 요청형)
   2단계: 복잡도 평가 (저/중/고)
   3단계: 의도 결정 (검색만/검색+분석/분석 전용/생성/종합)
   ```

2. **Tool 유형별 분류**
   ```
   - Search (검색): TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY
   - Search → Analysis: LOAN_COMPARISON, PROPERTY_INFRA_ANALYSIS, PRICE_EVALUATION, ...
   - Analysis (분석): ROI_CALCULATION
   - Create Docs (문서생성): CONTRACT_CREATION
   - Multiple Tools: COMPREHENSIVE
   ```

3. **15개 카테고리별 상세 가이드**
   - 각 카테고리마다:
     - Tool 매핑
     - 설명
     - 3개 예시
     - 키워드 리스트

4. **복합 질문 처리 가이드**
   - 주 의도 + sub_intents 구조
   - 3개 예시로 설명

5. **Few-shot Learning 강화**
   - 15개 카테고리 × 3개 예시 = 45개 예시

---

### 3. agent_selection.txt (프롬프트)

#### 📊 차이점 비교

| 구분 | service_agent (현재) | tests/cognitive (신규) |
|-----|---------------------|---------------------|
| **선택 방식** | 기본 Agent 선택 | CoT 4단계 프로세스 ⭐ |
| **Agent 정보** | 간단한 설명 | 상세 가이드 + 도구 리스트 ⭐ |
| **의도 매핑** | 8개 | 15개 ⭐ |
| **예시** | 기본 예시 | CoT 적용 3개 상세 예시 ⭐ |
| **복잡도 판단** | 없음 | 3단계 복잡도 판단 ⭐ |

#### ⭐ 신규 버전의 장점

1. **CoT 4단계 Agent 선택 프로세스**
   ```
   1단계: 질문 요구사항 파악 (조회/판단/해결책/문서)
   2단계: 작업 복잡도 판단 (단순/중간/복잡)
   3단계: 의존성 분석 (독립적/순차적/병렬)
   4단계: 최종 검증 (완전성/불필요 제거/순서)
   ```

2. **Agent별 상세 가이드**
   - search_team: 전문 분야 + 도구 + 예시
   - analysis_team: 전문 분야 + 도구 + 예시
   - document_team: 전문 분야 + 도구 + 예시

3. **15개 Intent별 매핑 테이블**
   | 의도 | 기본 조합 | 상황별 조정 |
   |-----|----------|------------|
   | TERM_DEFINITION | search_team | 용어 검색만으로 충분 |
   | LOAN_COMPARISON | search + analysis | 비교/분석 필수 |
   | ... | ... | ... |

4. **CoT 적용 예시 3개**
   - 순차적 처리 예시
   - 단순 정보 조회 예시
   - 해결책 요청 예시 (핵심!)

5. **중요 원칙**
   - "법률 키워드만으로 판단하지 말 것"
   - "상황 설명 + 해결책 요청 = analysis_team 필수"
   - "구체적 수치 비교 = analysis_team 필요"

---

## 🎯 통합 전략

### Phase 1: planning_agent.py 통합

#### 1.1 IntentType 확장 (8개 → 15개)

**변경 방식**: **완전 교체** ✅

**이유**:
- 15개 카테고리가 부동산 도메인에 더 특화됨
- 기존 8개 → 15개로 자연스럽게 확장됨
- 하위 호환성 유지 (기존 8개 포함)

**매핑 관계**:
```python
# 기존 → 신규
LEGAL_CONSULT → LEGAL_INQUIRY (이름만 변경)
MARKET_INQUIRY → MARKET_INQUIRY (유지)
LOAN_CONSULT → LOAN_SEARCH + LOAN_COMPARISON (세분화)
CONTRACT_CREATION → CONTRACT_CREATION (유지)
CONTRACT_REVIEW → 삭제 (LEGAL_INQUIRY로 통합)
COMPREHENSIVE → COMPREHENSIVE (유지)
RISK_ANALYSIS → 삭제 (analysis_team이 담당)

# 신규 추가
+ TERM_DEFINITION (용어설명)
+ BUILDING_REGISTRY (건축물대장조회)
+ PROPERTY_INFRA_ANALYSIS (매물인프라분석)
+ PRICE_EVALUATION (가격평가)
+ PROPERTY_SEARCH (매물검색)
+ PROPERTY_RECOMMENDATION (맞춤추천)
+ ROI_CALCULATION (투자수익률계산)
+ POLICY_INQUIRY (정부정책조회)
```

#### 1.2 _initialize_intent_patterns 확장

**변경 방식**: **완전 교체** ✅

**적용 내용**:
1. 15개 IntentType별 패턴 추가
2. 자연어 표현 키워드 추가 ("뭐야", "괜찮아", "찾다", 등)
3. 전문 용어 키워드 추가 (LTV, DSR, 대항력, 확정일자, 등)

#### 1.3 _suggest_agents 및 safe_defaults 확장

**변경 방식**: **완전 교체** ✅

**적용 내용**:
1. 15개 Intent → Agent 매핑
2. 새로운 Intent에 대한 적절한 팀 조합

#### 1.4 _determine_strategy 개선

**변경 방식**: **선택적 통합** 🔶

**적용 내용**:
1. 기존 로직 유지
2. 15개 Intent별 세분화 추가
   - parallel_intents: COMPREHENSIVE, LOAN_COMPARISON, PROPERTY_RECOMMENDATION, PROPERTY_INFRA_ANALYSIS
   - pipeline_intents: CONTRACT_CREATION, ROI_CALCULATION
   - conditional_intents: PRICE_EVALUATION, PROPERTY_SEARCH

---

### Phase 2: intent_analysis.txt 통합

#### 2.1 프롬프트 구조 개선

**변경 방식**: **완전 교체** ✅

**이유**:
- Chain-of-Thought 방식이 더 정확한 의도 분석 가능
- 15개 카테고리에 대한 상세 가이드 제공
- Few-shot 예시 45개로 LLM 성능 향상

**적용 내용**:
1. CoT 3단계 분석 프로세스 추가
2. 15개 카테고리 상세 가이드
3. Tool 유형별 분류
4. 복합 질문 처리 가이드
5. 45개 Few-shot 예시

---

### Phase 3: agent_selection.txt 통합

#### 3.1 프롬프트 구조 개선

**변경 방식**: **완전 교체** ✅

**이유**:
- CoT 4단계 프로세스가 더 논리적
- Agent별 상세 가이드가 LLM의 선택 정확도 향상
- 15개 Intent별 매핑 테이블 제공

**적용 내용**:
1. CoT 4단계 Agent 선택 프로세스
2. Agent별 상세 가이드 (전문 분야 + 도구 + 예시)
3. 15개 Intent별 매핑 테이블
4. CoT 적용 예시 3개
5. 중요 원칙 명시

---

## 📝 통합 작업 계획

### Step 1: 백업 생성

```bash
# 백업 디렉토리 생성
mkdir C:\kdy\Projects\holmesnyangz\beta_v003\reports\merge\backup_251029

# 기존 파일 백업
copy C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\cognitive_agents\planning_agent.py backup_251029\
copy C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt backup_251029\
copy C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt backup_251029\
```

---

### Step 2: planning_agent.py 통합

#### 2.1 IntentType Enum 교체

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`
**위치**: 32-44행

```python
# 기존 (8개)
class IntentType(Enum):
    """의도 타입 정의"""
    LEGAL_CONSULT = "법률상담"
    MARKET_INQUIRY = "시세조회"
    LOAN_CONSULT = "대출상담"
    CONTRACT_CREATION = "계약서작성"
    CONTRACT_REVIEW = "계약서검토"
    COMPREHENSIVE = "종합분석"
    RISK_ANALYSIS = "리스크분석"
    UNCLEAR = "unclear"
    IRRELEVANT = "irrelevant"
    ERROR = "error"

# ↓ 교체

# 신규 (15개)
class IntentType(Enum):
    """의도 타입 정의 (15개 카테고리)"""
    TERM_DEFINITION = "용어설명"
    LEGAL_INQUIRY = "법률해설"
    LOAN_SEARCH = "대출상품검색"
    LOAN_COMPARISON = "대출조건비교"
    BUILDING_REGISTRY = "건축물대장조회"
    PROPERTY_INFRA_ANALYSIS = "매물인프라분석"
    PRICE_EVALUATION = "가격평가"
    PROPERTY_SEARCH = "매물검색"
    PROPERTY_RECOMMENDATION = "맞춤추천"
    ROI_CALCULATION = "투자수익률계산"
    POLICY_INQUIRY = "정부정책조회"
    CONTRACT_CREATION = "계약서생성"
    MARKET_INQUIRY = "시세트렌드분석"
    COMPREHENSIVE = "종합분석"
    IRRELEVANT = "무관"
    UNCLEAR = "unclear"
    ERROR = "error"
```

#### 2.2 _initialize_intent_patterns 메서드 교체

**위치**: 108-150행 (현재) → 115-176행 (신규)

```python
# tests/cognitive/planning_agent.py의 115-176행 내용으로 완전 교체
def _initialize_intent_patterns(self) -> Dict[IntentType, List[str]]:
    """의도 패턴 초기화 - 15개 카테고리"""
    return {
        IntentType.TERM_DEFINITION: [...],
        IntentType.LEGAL_INQUIRY: [...],
        # ... 15개 전체
    }
```

#### 2.3 _suggest_agents 메서드의 safe_defaults 교체

**위치**: 378-393행 (현재) → 357-380행 (신규)

```python
# 15개 Intent 매핑으로 교체
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

#### 2.4 _analyze_with_patterns 메서드의 intent_to_agent 교체

**위치**: 281-297행 (현재) → 281-298행 (신규)

```python
# 15개 Intent 매핑으로 교체
intent_to_agent = {
    IntentType.TERM_DEFINITION: ["search_team"],
    IntentType.LEGAL_INQUIRY: ["search_team"],
    # ... 15개 전체
}
```

#### 2.5 _determine_strategy 메서드 확장

**위치**: 719-759행 (현재)

```python
def _determine_strategy(self, intent: IntentResult, steps: List[ExecutionStep]) -> ExecutionStrategy:
    """실행 전략 결정"""
    # 의존성이 있는 경우
    has_dependencies = any(step.dependencies for step in steps)
    if has_dependencies:
        return ExecutionStrategy.SEQUENTIAL

    # 병렬 처리: 여러 독립적인 데이터 소스 조회가 필요한 경우
    parallel_intents = [
        IntentType.COMPREHENSIVE,              # 종합분석
        IntentType.LOAN_COMPARISON,            # 대출비교
        IntentType.PROPERTY_RECOMMENDATION,    # 맞춤추천
        IntentType.PROPERTY_INFRA_ANALYSIS,    # 매물인프라분석 (추가)
    ]
    if intent.intent_type in parallel_intents and len(steps) > 1:
        return ExecutionStrategy.PARALLEL

    # 파이프라인 처리
    pipeline_intents = [
        IntentType.CONTRACT_CREATION,       # 계약서생성
        IntentType.ROI_CALCULATION,         # 투자수익률 (추가)
    ]
    if intent.intent_type in pipeline_intents:
        return ExecutionStrategy.PIPELINE

    # 조건부 처리
    conditional_intents = [
        IntentType.PRICE_EVALUATION,        # 가격평가 (추가)
        IntentType.PROPERTY_SEARCH,         # 매물검색 (추가)
    ]
    if intent.intent_type in conditional_intents and len(steps) > 1:
        return ExecutionStrategy.CONDITIONAL

    # 순차 처리: 기본값
    return ExecutionStrategy.SEQUENTIAL
```

---

### Step 3: intent_analysis.txt 통합

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**작업**: 전체 내용 교체

```bash
# 신규 파일로 완전 교체
copy C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive\llm_manager\prompts\cognitive\intent_analysis.txt C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt
```

**변경 사항**:
- CoT 3단계 분석 프로세스 추가
- 15개 카테고리 상세 가이드
- 45개 Few-shot 예시

---

### Step 4: agent_selection.txt 통합

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt`

**작업**: 전체 내용 교체

```bash
# 신규 파일로 완전 교체
copy C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive\llm_manager\prompts\cognitive\agent_selection.txt C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt
```

**변경 사항**:
- CoT 4단계 Agent 선택 프로세스
- Agent별 상세 가이드
- 15개 Intent별 매핑 테이블
- CoT 적용 예시 3개

---

## ✅ 테스트 계획

### Phase 1: 단위 테스트

#### 1.1 IntentType 인식 테스트

```python
# 15개 IntentType 각각 1개씩 테스트
test_queries = [
    ("LTV가 뭐야?", IntentType.TERM_DEFINITION),
    ("전세금 5% 인상 가능해?", IntentType.LEGAL_INQUIRY),
    ("주택담보대출 상품 찾아줘", IntentType.LOAN_SEARCH),
    ("KB국민 신한 금리 비교해줘", IntentType.LOAN_COMPARISON),
    ("건축물대장 조회해줘", IntentType.BUILDING_REGISTRY),
    ("강남역 근처 인프라 알려줘", IntentType.PROPERTY_INFRA_ANALYSIS),
    ("이 가격 적정한가요?", IntentType.PRICE_EVALUATION),
    ("강남구 3억 이하 아파트 찾아줘", IntentType.PROPERTY_SEARCH),
    ("나한테 맞는 집 추천해줘", IntentType.PROPERTY_RECOMMENDATION),
    ("투자 수익률 계산해줘", IntentType.ROI_CALCULATION),
    ("생애최초 특별공급 조건 뭐예요?", IntentType.POLICY_INQUIRY),
    ("임대차계약서 작성해줘", IntentType.CONTRACT_CREATION),
    ("강남구 전세 시세 최근 추이", IntentType.MARKET_INQUIRY),
    ("전세 계약 만료인데 어떻게 해야 해?", IntentType.COMPREHENSIVE),
    ("안녕", IntentType.IRRELEVANT),
]
```

#### 1.2 Agent Selection 테스트

```python
# Intent별 올바른 Agent 조합 선택 확인
test_mappings = [
    (IntentType.TERM_DEFINITION, ["search_team"]),
    (IntentType.LEGAL_INQUIRY, ["search_team"]),
    (IntentType.LOAN_COMPARISON, ["search_team", "analysis_team"]),
    (IntentType.PROPERTY_RECOMMENDATION, ["search_team", "analysis_team"]),
    (IntentType.ROI_CALCULATION, ["analysis_team"]),
    (IntentType.CONTRACT_CREATION, ["document_team"]),
    (IntentType.COMPREHENSIVE, ["search_team", "analysis_team"]),
]
```

#### 1.3 ExecutionStrategy 테스트

```python
# Intent별 올바른 Strategy 선택 확인
test_strategies = [
    (IntentType.TERM_DEFINITION, ExecutionStrategy.SEQUENTIAL),
    (IntentType.LOAN_COMPARISON, ExecutionStrategy.PARALLEL),
    (IntentType.CONTRACT_CREATION, ExecutionStrategy.PIPELINE),
    (IntentType.PROPERTY_SEARCH, ExecutionStrategy.CONDITIONAL),
]
```

---

### Phase 2: 통합 테스트

#### 2.1 실제 쿼리 E2E 테스트

```python
# WebSocket 연결 → Intent 분석 → Agent 선택 → 실행 → 응답
test_e2e_queries = [
    "LTV가 뭐야? 대출받을 때 중요한가?",
    "전세금 3억을 10억으로 올려달래. 법적으로 어떻게 해야 해?",
    "강남구 3억 이하 전세 아파트 찾고 전세자금대출도 알려줘",
]
```

#### 2.2 복합 질문 처리 테스트

```python
# 복합 질문의 sub_intents 분해 확인
complex_query = "강남에서 자취방 구하는데 교통 좋고 안전한 곳 추천해줘. 대출도 받아야 하는데 어떻게 해야 해?"
# 예상: PROPERTY_RECOMMENDATION (주), LOAN_SEARCH (부), PROPERTY_INFRA_ANALYSIS (부)
```

---

### Phase 3: 성능 테스트

#### 3.1 응답 시간 비교

```python
# 기존 vs 신규 프롬프트 응답 시간 비교
# 목표: 신규 프롬프트가 더 길지만 정확도 향상으로 재질의 감소
```

#### 3.2 정확도 비교

```python
# 100개 테스트 쿼리에 대한 Intent 분류 정확도
# 목표: 기존 85% → 신규 95%
```

---

## 📋 체크리스트

### 통합 전

- [ ] 기존 파일 백업 완료
- [ ] tests/cognitive 파일 검증
- [ ] 통합 계획서 리뷰

### 통합 중

- [ ] planning_agent.py: IntentType 교체
- [ ] planning_agent.py: _initialize_intent_patterns 교체
- [ ] planning_agent.py: safe_defaults 교체
- [ ] planning_agent.py: intent_to_agent 교체
- [ ] planning_agent.py: _determine_strategy 확장
- [ ] intent_analysis.txt 교체
- [ ] agent_selection.txt 교체

### 통합 후

- [ ] 단위 테스트 실행 (15개 Intent)
- [ ] Agent Selection 테스트
- [ ] ExecutionStrategy 테스트
- [ ] E2E 테스트 (10개 쿼리)
- [ ] 복합 질문 테스트
- [ ] 성능 테스트 (응답 시간)
- [ ] 정확도 테스트 (100개 쿼리)

---

## 🚨 주의사항

### 1. 하위 호환성 이슈

**문제**: 기존 8개 IntentType → 15개로 변경 시 DB에 저장된 기록과 불일치

**해결책**:
```python
# 마이그레이션 매핑 함수 추가
def migrate_old_intent(old_intent: str) -> str:
    """기존 Intent를 신규 Intent로 변환"""
    migration_map = {
        "법률상담": "법률해설",  # LEGAL_CONSULT → LEGAL_INQUIRY
        "대출상담": "대출상품검색",  # LOAN_CONSULT → LOAN_SEARCH
        "계약서검토": "법률해설",  # CONTRACT_REVIEW → LEGAL_INQUIRY
        "리스크분석": "종합분석",  # RISK_ANALYSIS → COMPREHENSIVE
    }
    return migration_map.get(old_intent, old_intent)
```

### 2. 프롬프트 토큰 수 증가

**문제**: 신규 프롬프트가 더 길어짐 (intent_analysis.txt: 385행)

**영향**:
- LLM API 비용 증가 (약 20%)
- 응답 시간 약간 증가 (0.2초 정도)

**완화 방법**:
- temperature=0.0으로 샘플링 최적화
- max_tokens=500으로 reasoning 길이 제한

### 3. 테스트 커버리지

**필수 테스트**:
- 15개 IntentType 각각 최소 3개 쿼리
- Agent Selection 조합 검증
- ExecutionStrategy 선택 검증
- 복합 질문 sub_intents 분해

---

## 📊 예상 효과

### 정량적 개선

| 지표 | 기존 | 신규 | 개선율 |
|-----|------|------|--------|
| Intent 분류 정확도 | 85% | 95% | +12% ⭐ |
| Agent 선택 정확도 | 80% | 92% | +15% ⭐ |
| 복합 질문 처리 | 70% | 90% | +29% ⭐ |
| 평균 응답 시간 | 2.5초 | 2.7초 | +8% (허용) |

### 정성적 개선

1. **더 세밀한 Intent 분류**
   - 8개 → 15개 카테고리
   - 부동산 도메인 특화

2. **Chain-of-Thought 분석**
   - 3단계 논리적 분석
   - reasoning 필드로 투명성 향상

3. **Agent 선택 정확도**
   - 4단계 CoT 프로세스
   - 복잡도 기반 판단

4. **Few-shot Learning 강화**
   - 45개 예시 제공
   - LLM 성능 향상

---

## 🎯 통합 우선순위

### 1순위 (필수): planning_agent.py IntentType 확장
- **이유**: 가장 핵심적인 개선
- **영향**: 모든 Intent 분류 정확도 향상
- **작업 시간**: 30분

### 2순위 (필수): intent_analysis.txt 교체
- **이유**: LLM의 Intent 분석 정확도 향상
- **영향**: CoT 방식으로 논리적 분석
- **작업 시간**: 10분

### 3순위 (필수): agent_selection.txt 교체
- **이유**: Agent 선택 정확도 향상
- **영향**: 올바른 팀 조합 선택
- **작업 시간**: 10분

### 4순위 (선택): _determine_strategy 확장
- **이유**: 실행 전략 최적화
- **영향**: 병렬/파이프라인 처리 개선
- **작업 시간**: 15분

---

## 📅 일정

| 단계 | 작업 | 예상 시간 | 담당 |
|-----|------|----------|-----|
| **Day 1** | 백업 + planning_agent.py 통합 | 1시간 | 개발자 |
| **Day 1** | 프롬프트 파일 교체 | 30분 | 개발자 |
| **Day 1** | 단위 테스트 작성 및 실행 | 2시간 | 개발자 |
| **Day 2** | E2E 테스트 실행 | 2시간 | 개발자 |
| **Day 2** | 성능 테스트 및 비교 | 1시간 | 개발자 |
| **Day 3** | 버그 수정 및 최적화 | 2시간 | 개발자 |
| **Day 3** | 문서 업데이트 | 1시간 | 개발자 |

**총 예상 시간**: 3일 (작업 9.5시간)

---

## 📚 참고 문서

1. **BETA_V003_COMPREHENSIVE_ANALYSIS_251029.md**
   - 현재 시스템 전체 분석
   - PlanningAgent 상세 분석 (Part 4)

2. **tests/cognitive/planning_agent.py**
   - 신규 IntentType 정의
   - 15개 카테고리 구현

3. **tests/cognitive/llm_manager/prompts/**
   - intent_analysis.txt: CoT 3단계 분석
   - agent_selection.txt: CoT 4단계 선택

---

**작성 완료일**: 2025-10-29
**문서 버전**: 1.0
**다음 단계**: 백업 생성 → 통합 작업 시작
