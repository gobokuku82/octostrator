# 파일별 장단점 비교 분석 (Best-of-Both 통합 전략)

**작성일**: 2025-10-29
**비교 대상**: tests/cognitive vs backend/app/service_agent
**목표**: 양쪽 파일의 장점을 살려서 최적의 통합본 생성

---

## 📊 비교 파일 목록

### 1. planning_agent.py
- **Backend**: `C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\cognitive_agents\planning_agent.py`
- **Tests**: `C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive\cognitive_agents\planning_agent.py`

### 2. intent_analysis.txt
- **Backend**: `C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt`
- **Tests**: `C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive\llm_manager\prompts\cognitive\intent_analysis.txt`

### 3. agent_selection.txt
- **Backend**: `C:\kdy\Projects\holmesnyangz\beta_v003\backend\app\service_agent\llm_manager\prompts\cognitive\agent_selection.txt`
- **Tests**: `C:\kdy\Projects\holmesnyangz\beta_v003\tests\cognitive\llm_manager\prompts\cognitive\agent_selection.txt`

---

## 🔍 파일 1: planning_agent.py 비교

### 📈 Backend 버전의 장점 (유지해야 할 기능)

#### ✅ 1. Chat History 처리 기능 (Line 186-202)
```python
# Context에서 chat_history 추출
chat_history = context.get("chat_history", []) if context else []

# Chat history를 문자열로 포맷팅
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
```

**왜 중요한가?**
- 이전 대화 맥락을 활용하여 더 정확한 의도 분석
- "그거", "아까", "그럼" 같은 지시어 처리 가능
- 연속된 대화에서 사용자 의도 파악 개선

**통합 결정**: ✅ **반드시 유지**

---

#### ✅ 2. reuse_previous_data 기능 (Line 236-242)
```python
# 🆕 reuse_previous_data를 entities에 추가
entities = result.get("entities", {})
reuse_previous_data = result.get("reuse_previous_data", False)

# entities에 reuse_previous_data 추가 (team_supervisor에서 사용하기 위해)
if reuse_previous_data:
    entities["reuse_previous_data"] = reuse_previous_data
```

**왜 중요한가?**
- 이전 대화에서 수집한 데이터 재사용 가능
- API 호출 최소화 → 비용 절감, 응답 속도 향상
- "그 데이터로 분석해줘" 같은 요청 처리

**통합 결정**: ✅ **반드시 유지**

---

#### ✅ 3. 키워드 기반 필터 (Line 322-349)
```python
# === 0차: 키워드 기반 필터 (경계 케이스 해결) ===
# LEGAL_CONSULT: 단순 질문은 search만, 복잡한 질문은 search + analysis
if intent_type == IntentType.LEGAL_CONSULT:
    # 분석이 필요한 키워드
    analysis_keywords = [
        "비교", "분석", "계산", "평가", "추천", "검토",
        "어떻게", "방법", "차이", "장단점", "괜찮아",
        "해야", "대응", "해결", "조치", "문제"
    ]

    needs_analysis = any(kw in query for kw in analysis_keywords)

    if not needs_analysis:
        logger.info(f"✅ LEGAL_CONSULT without analysis keywords → search_team only")
        return ["search_team"]
    else:
        logger.info(f"✅ LEGAL_CONSULT with analysis keywords → search + analysis")
        return ["search_team", "analysis_team"]
```

**왜 중요한가?**
- LLM 호출 전 빠른 규칙 기반 필터링
- "전세금 5% 인상 가능해?" (단순) vs "3억을 10억으로 올려달래, 어떻게?" (복잡) 구분
- 성능 최적화 + Agent 비용 절감

**통합 결정**: ✅ **유지하되 15-category로 확장**

---

#### ✅ 4. 자연스러운 표현 패턴 (Line 111-148)
```python
IntentType.LEGAL_CONSULT: [
    # 기존 키워드
    "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신",
    # 자연스러운 표현 추가
    "살다", "거주", "세입자", "집주인", "임차인", "임대인", "해지", "계약서",
    "대항력", "확정일자", "우선변제", "임차권"
],
```

**왜 중요한가?**
- 사용자가 전문 용어 대신 일상 언어로 질문하는 경우 처리
- "집주인이 나가라고 해요" → LEGAL_CONSULT 인식
- 패턴 매칭 정확도 향상

**통합 결정**: ✅ **유지하되 15-category 패턴에 병합**

---

### 📈 Tests 버전의 장점 (추가해야 할 기능)

#### ✅ 1. 15-Category 시스템 (Line 32-50)
```python
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

**왜 중요한가?**
- 더 세분화된 의도 분류 → 정확한 Agent 매칭
- 사용자 요구사항에 더 구체적으로 대응
- Tool 매핑이 더 명확해짐

**통합 결정**: ✅ **Backend에 추가**

---

#### ✅ 2. 상세한 패턴 정의 (Line 115-175)
```python
IntentType.TERM_DEFINITION: [
    "뭐야", "무엇", "의미", "설명", "개념", "정의", "차이", "란",
    "LTV", "대항력", "분양권", "입주권", "재건축", "재개발", "DSR"
],
IntentType.BUILDING_REGISTRY: [
    "건축물대장", "건물정보", "준공", "용도", "면적", "조회",
    "불법 증축", "주차장", "세대수"
],
IntentType.PROPERTY_INFRA_ANALYSIS: [
    "지하철", "마트", "병원", "약국", "초등학교", "중학교", "고등학교",
    "학군", "인프라", "근처", "주변", "도보권", "거리", "교통", "편의시설"
],
```

**왜 중요한가?**
- 새로운 8개 카테고리에 대한 구체적인 키워드
- 패턴 매칭 fallback 성능 향상
- LLM 호출 실패 시에도 정확한 의도 파악

**통합 결정**: ✅ **Backend 패턴에 병합**

---

#### ✅ 3. _determine_strategy 로직 강화 (Line 719-758)
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
    if intent.intent_type in pipeline_intents:
        return ExecutionStrategy.PIPELINE

    # 조건부 처리: 이전 결과에 따라 다음 단계가 달라지는 경우
    conditional_intents = [
        IntentType.PRICE_EVALUATION,        # 가격평가 - 시세 확인 후 추가 분석 필요 여부 판단
        IntentType.PROPERTY_SEARCH,         # 매물검색 - 검색 결과에 따라 추가 필터링 여부 결정
    ]
    if intent.intent_type in conditional_intents and len(steps) > 1:
        return ExecutionStrategy.CONDITIONAL

    return ExecutionStrategy.SEQUENTIAL
```

**왜 중요한가?**
- 각 의도별로 최적화된 실행 전략
- 병렬 처리로 응답 속도 향상 (예: 인프라 분석 시 지하철/마트/병원 동시 조회)
- 파이프라인 처리로 단계별 피드백 가능

**통합 결정**: ✅ **Backend의 기존 로직 대체**

---

#### ✅ 4. available_agents 정의 강화 (Line 402-426)
```python
available_agents = {
    "search_team": {
        "name": "search_team",
        "capabilities": "법률 검색, 용어 설명, 부동산 시세 조회, 개별 매물 검색, 대출 상품 검색, 건축물대장 조회, 정부 정책 조회",
        "tools": ["realestate_terminology", "legal_search", "market_data", "real_estate_search",
                  "loan_data", "building_registry", "policy_matcher"],
        "use_cases": [
            "용어설명", "법률해설", "대출상품검색", "건축물대장조회", "정부정책조회", "매물검색"
        ]
    },
    "analysis_team": {
        "name": "analysis_team",
        "capabilities": "데이터 분석, 가격 평가, 인프라 분석, 투자 수익률 계산, 리스크 평가, 추천",
        "tools": ["contract_analysis", "market_analysis", "roi_calculator",
                  "infrastructure", "loan_simulator"],
        "use_cases": [
            "대출조건비교", "매물인프라분석", "가격평가", "매물검색",
            "맞춤추천", "투자수익률계산", "종합분석"
        ]
    },
}
```

**왜 중요한가?**
- 15-category 각각에 맞는 Tool 매핑 명시
- LLM이 Agent 선택 시 더 정확한 판단 가능
- `realestate_terminology`, `building_registry` 등 새 도구 추가

**통합 결정**: ✅ **Backend 버전 업데이트**

---

### 📊 planning_agent.py 통합 전략

| 항목 | Backend | Tests | 통합 결정 |
|------|---------|-------|----------|
| **IntentType Enum** | 10개 카테고리 | 15개 카테고리 | ✅ Tests 15-category 채택 |
| **Chat History** | ✅ 있음 (line 186-202) | ❌ 없음 | ✅ Backend 유지 |
| **reuse_previous_data** | ✅ 있음 (line 236-242) | ❌ 없음 | ✅ Backend 유지 |
| **키워드 필터** | ✅ 있음 (line 322-349) | ❌ 없음 | ✅ Backend 유지 + 15-category 확장 |
| **패턴 정의** | 자연스러운 표현 강조 | 구체적 키워드 강조 | ✅ 양쪽 병합 |
| **_analyze_with_patterns** | 10-category 매핑 | 15-category 매핑 | ✅ Tests 로직 채택 |
| **_suggest_agents (safe_defaults)** | 10-category | 15-category | ✅ Tests 15-category 채택 |
| **_determine_strategy** | 기본 로직 | 상세 로직 (parallel/pipeline/conditional) | ✅ Tests 로직 채택 |
| **available_agents (use_cases)** | 10-category 매핑 | 15-category 매핑 | ✅ Tests 상세 정의 채택 |

---

## 🔍 파일 2: intent_analysis.txt 비교

### 📈 Backend 버전의 장점 (유지해야 할 기능)

#### ✅ 1. Chat History 섹션 (Line 205-226)
```markdown
## 🔹 최근 대화 기록 (Chat History)

이전 대화 맥락을 참고하여 의도를 더 정확히 파악하세요.

{chat_history}

**분석 지침**:
1. 위 대화 기록을 참고하여 현재 질문의 맥락을 이해하세요
2. "그럼", "그거", "그건", "아까" 등의 지시어가 있으면 이전 대화에서 언급된 내용을 찾으세요
3. 이전 대화와 연결되는 질문이면 부동산 관련 질문으로 처리하세요

**데이터 재사용 판단**:
다음과 같은 경우 "reuse_previous_data": true로 설정하세요:
- "방금", "위", "그", "이전", "아까" 등의 지시어로 이전 데이터를 참조하는 경우
- "그 데이터로", "그 정보로", "그걸로 분석" 등 이전 정보 활용을 명시하는 경우
- 문맥상 이전 대화의 검색 결과나 정보를 재사용하려는 의도가 명확한 경우
```

**왜 중요한가?**
- 대화의 연속성 유지
- 지시어 처리 가이드라인
- reuse_previous_data 판단 기준 명시

**통합 결정**: ✅ **반드시 유지**

---

#### ✅ 2. Chain-of-Thought 분석 (Line 26-42)
```markdown
## Chain-of-Thought 분석 (3단계)

### 1단계: 질문 유형 파악
- 정보 확인형: "~이 뭐야?", "~알려줘" → 검색만으로 충분
- 평가/판단형: "괜찮아?", "문제있어?" → 검색 + 분석 필요
- 해결책 요청형: "어떻게?", "방법?" → 검색 + 분석 + 제안 필요

### 2단계: 복잡도 평가
- **저**: 단일 개념/사실 확인 (예: "전세금 인상률 한도?")
- **중**: 특정 상황 + 판단 (예: "3억을 5억으로 올려달래. 가능해?")
- **고**: 복잡한 상황 + 여러 조건 + 해결책 (예: "10년 거주, 3억→10억 요구. 어떻게?")

### 3단계: 의도 결정
- **검색만**: 정보 확인형 + 저복잡도
- **검색+분석**: 평가/판단형 OR 중복잡도
- **종합처리**: 해결책 요청형 OR 고복잡도
```

**왜 중요한가?**
- LLM에게 명확한 사고 프로세스 제공
- 의도 분류 정확도 향상
- reasoning 필드 작성 가이드

**통합 결정**: ✅ **유지하되 15-category 매핑으로 업데이트**

---

#### ✅ 3. reasoning 작성 예시 (Line 195-201)
```markdown
## reasoning 작성 예시

**좋은 예**:
"1단계(유형): 해결책 요청형 - '어떻게 해야 해?' 포함. 2단계(복잡도): 고 - 구체적 상황(10년 거주, 3억→10억) + 법률 + 대응방안. 3단계(의도): 종합 분석 필요 → COMPREHENSIVE"

**나쁜 예**:
"전세금 인상에 대한 법률 질문이므로 LEGAL_CONSULT로 분류" (단계별 분석 누락)
```

**왜 중요한가?**
- LLM 응답 품질 향상
- 디버깅 및 개선 시 추론 과정 추적 가능

**통합 결정**: ✅ **유지**

---

### 📈 Tests 버전의 장점 (추가해야 할 기능)

#### ✅ 1. 15-Category 정의 (전체 구조)
```markdown
## 의도 카테고리 (15가지)
**Flow 기반 기능 매핑**: 각 의도는 특정 Tool과 연결되어 있습니다.

### Tool 유형별 분류

#### 🔍 검색 전용 (Search-Only)
1. **TERM_DEFINITION** (용어설명)
   - 설명: 부동산 전문 용어의 정의와 개념 설명
   - 예시:
     * "LTV가 뭐야?"
     * "대항력이란?"
     * "재건축과 재개발의 차이는?"
   - 키워드: 뭐야, 무엇, 의미, 설명, 개념, 정의, 차이, 란

2. **LEGAL_INQUIRY** (법률해설)
   - 설명: 부동산 관련 법률, 권리, 의무 질문
   - 예시:
     * "전세금 5% 인상이 가능한가요?"
     * "임대차계약 갱신 거부할 수 있나요?"
   - 키워드: 법, 전세, 임대, 보증금, 계약, 권리, 의무, 갱신, 가능한가요

... (15개 모두 상세히 정의)
```

**왜 중요한가?**
- 각 카테고리별로 명확한 예시와 키워드
- Tool 유형별 분류로 Agent 매핑 명확화
- LLM이 15개 카테고리를 정확히 구분 가능

**통합 결정**: ✅ **Backend 9개 카테고리 대체**

---

#### ✅ 2. Tool 유형별 분류 (Tests 고유)
```markdown
### Tool 유형별 분류

#### 🔍 검색 전용 (Search-Only)
- TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY, POLICY_INQUIRY

#### 🔍 + 📊 검색 + 분석 (Search + Analysis)
- LOAN_COMPARISON, PROPERTY_INFRA_ANALYSIS, PRICE_EVALUATION,
  PROPERTY_SEARCH, PROPERTY_RECOMMENDATION, MARKET_INQUIRY

#### 📊 분석 전용 (Analysis-Only)
- ROI_CALCULATION

#### 📝 문서 생성 (Document)
- CONTRACT_CREATION

#### 🔄 종합 처리 (Comprehensive)
- COMPREHENSIVE
```

**왜 중요한가?**
- Agent 매핑 논리가 명확해짐
- LLM이 어떤 팀을 호출해야 하는지 직관적으로 이해
- 프롬프트 구조가 체계적

**통합 결정**: ✅ **Backend에 추가**

---

### 📊 intent_analysis.txt 통합 전략

| 항목 | Backend | Tests | 통합 결정 |
|------|---------|-------|----------|
| **카테고리 수** | 9개 | 15개 | ✅ Tests 15-category 채택 |
| **Chat History 섹션** | ✅ 있음 (line 205-226) | ❌ 없음 | ✅ Backend 유지 |
| **reuse_previous_data 가이드** | ✅ 있음 (line 220-224) | ❌ 없음 | ✅ Backend 유지 |
| **CoT 분석 (3단계)** | ✅ 명확함 (line 26-42) | ✅ 있음 | ✅ Backend 유지 + 15-category 매핑 업데이트 |
| **Tool 유형별 분류** | ❌ 없음 | ✅ 있음 | ✅ Tests 추가 |
| **각 카테고리별 예시** | 9개 상세 | 15개 상세 | ✅ Tests 15개 예시 채택 |
| **reasoning 예시** | ✅ 상세함 (line 195-201) | ✅ 있음 | ✅ Backend 유지 |
| **복합 질문 처리** | ✅ 상세함 (line 115-137) | ✅ 있음 | ✅ Backend 유지 |

---

## 🔍 파일 3: agent_selection.txt 비교

### 📈 Backend 버전의 장점 (유지해야 할 기능)

#### ✅ 1. Chain-of-Thought 프로세스 (Line 62-90)
```markdown
## Chain-of-Thought Agent 선택 프로세스

다음 단계를 **순서대로** 따라 최적의 Agent 조합을 선택하세요:

### 1단계: 질문 요구사항 파악
- 단순 정보 조회인가? → search_team만 필요
- 판단/평가가 필요한가? → search + analysis 필요
- 해결책 제시가 필요한가? → search + analysis 필요
- 문서 생성이 필요한가? → document_team 추가

### 2단계: 작업 복잡도 판단
- **단순** (검색만): "~이 뭐야?", "~알려줘" → search_team
- **중간** (검색+판단): "~괜찮아?", "~적절해?" → search + analysis
- **복잡** (종합 해결): 구체적 상황 + "어떻게 해야 해?" → search + analysis

### 3단계: 의존성 분석
- 독립적 작업: 단일 팀으로 처리 가능
- 순차적 의존: 이전 결과 필요 → 여러 팀 순서대로
- 병렬 가능: 동시 조회 가능 → coordination: "parallel"

### 4단계: 최종 검증
- 선택한 팀들로 질문에 완전히 답변 가능한가?
- 불필요한 팀이 포함되지 않았는가?
- 순서가 논리적인가? (데이터 흐름 고려)
```

**왜 중요한가?**
- LLM에게 구조화된 의사결정 프로세스 제공
- Agent 선택 오류 최소화
- 복잡한 질문에서도 논리적 선택 가능

**통합 결정**: ✅ **반드시 유지**

---

#### ✅ 2. 핵심 원칙 강조 (Line 87-90)
```markdown
### 중요 원칙:
- **법률 키워드만으로 판단하지 말 것**: "법적으로 어떻게 해야 해?" = 법률 검색 + 분석 필요
- **상황 설명 + 해결책 요청** = 반드시 analysis_team 포함
- **구체적 수치 비교** (3억→10억 같은) = analysis_team 필요
```

**왜 중요한가?**
- 흔한 실수 방지 (법률 키워드만 보고 search_team만 선택)
- Edge case 명시
- Agent 선택 정확도 향상

**통합 결정**: ✅ **유지하되 15-category 예시 추가**

---

#### ✅ 3. 해결책 요청 예시 (Line 142-158)
```markdown
### 예시 3: 해결책 요청 (핵심 예시!)
질문: "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 어떻게 해야 해?"
의도: COMPREHENSIVE
**CoT 분석**:
1. 요구사항: 상황 설명 + 해결책 요청
2. 복잡도: 높음 (구체적 상황 + 수치 비교)
3. 의존성: 법률 확인 → 상황 분석 → 해결책 제시
4. 검증: "법적으로"만 보고 search만 선택하면 불충분! 해결책 제시 필요

```json
{
    "selected_agents": ["search_team", "analysis_team"],
    "reasoning": "1단계: 법률 + 상황 분석 + 해결책 필요. 2단계: 고복잡도(3억→10억 비정상). 3단계: 순차(법률 확인 후 타당성 분석). 4단계: '어떻게 해야' = 단순 법률 조회 아님, 분석 필수",
    "coordination": "sequential",
    "confidence": 0.95
}
```
```

**왜 중요한가?**
- 가장 실수하기 쉬운 케이스를 명시적으로 가르침
- "법적으로"라는 키워드에 속지 않도록 경고
- 실제 사용자 질문 패턴 반영

**통합 결정**: ✅ **반드시 유지**

---

### 📈 Tests 버전의 장점 (추가해야 할 기능)

#### ✅ 1. 15-Category Agent 매핑 (Tests 고유)
```markdown
## Agent 역할 및 상세 가이드

### 1. search_team (검색 팀)
- **도구**: realestate_terminology, legal_search_tool, market_data_tool,
           real_estate_search_tool, loan_data_tool, building_registry_tool,
           policy_matcher_tool
- **적합한 의도**:
  * TERM_DEFINITION (용어설명)
  * LEGAL_INQUIRY (법률해설)
  * LOAN_SEARCH (대출상품검색)
  * BUILDING_REGISTRY (건축물대장조회)
  * POLICY_INQUIRY (정부정책조회)

### 2. analysis_team (분석 팀)
- **도구**: contract_analysis_tool, market_analysis_tool, roi_calculator_tool,
           loan_simulator_tool, infrastructure_tool
- **적합한 의도**:
  * LOAN_COMPARISON (대출조건비교)
  * PROPERTY_INFRA_ANALYSIS (매물인프라분석)
  * PRICE_EVALUATION (가격평가)
  * PROPERTY_SEARCH (매물검색)
  * PROPERTY_RECOMMENDATION (맞춤추천)
  * ROI_CALCULATION (투자수익률계산)
```

**왜 중요한가?**
- 15-category 각각에 대한 명확한 팀 매핑
- 새 도구 (`building_registry_tool`, `infrastructure_tool` 등) 명시
- LLM이 적절한 팀 선택 가능

**통합 결정**: ✅ **Backend 매핑 테이블 업데이트**

---

#### ✅ 2. 도구 목록 확장 (Tests 버전)
```markdown
- **도구**:
  * realestate_terminology (용어 사전) 🆕
  * legal_search_tool (법률 검색)
  * market_data_tool (시세 조회)
  * real_estate_search_tool (매물 검색)
  * loan_data_tool (대출 상품 검색)
  * building_registry_tool (건축물대장 조회) 🆕
  * policy_matcher_tool (정부 정책 매칭) 🆕
  * infrastructure_tool (인프라 분석) 🆕
  * roi_calculator_tool (ROI 계산) 🆕
```

**왜 중요한가?**
- 새로운 8개 카테고리를 지원하는 도구 명시
- Agent가 어떤 도구를 사용할 수 있는지 명확
- 프롬프트와 실제 구현 간 일관성

**통합 결정**: ✅ **Backend에 추가**

---

### 📊 agent_selection.txt 통합 전략

| 항목 | Backend | Tests | 통합 결정 |
|------|---------|-------|----------|
| **CoT 프로세스 (4단계)** | ✅ 매우 상세 (line 62-90) | ❌ 간단함 | ✅ Backend 유지 |
| **중요 원칙 강조** | ✅ 있음 (line 87-90) | ❌ 없음 | ✅ Backend 유지 |
| **해결책 요청 예시** | ✅ 핵심 예시 (line 142-158) | ❌ 없음 | ✅ Backend 유지 |
| **Agent 도구 목록** | 기본 도구 3개 | 확장 도구 9개 🆕 | ✅ Tests 도구 채택 |
| **의도별 Agent 매핑** | 9개 카테고리 | 15개 카테고리 | ✅ Tests 15-category 매핑 채택 |
| **Tool 유형별 분류** | ❌ 없음 | ✅ 있음 | ✅ Tests 추가 |

---

## 🎯 최종 통합 전략 요약

### Backend를 메인으로 유지하며 Tests의 장점 추가

#### 1️⃣ planning_agent.py 통합 계획

**유지할 Backend 기능**:
- ✅ Chat History 처리 (line 186-202)
- ✅ reuse_previous_data 기능 (line 236-242)
- ✅ 키워드 기반 필터 (line 322-349)
- ✅ 자연스러운 표현 패턴

**추가할 Tests 기능**:
- ✅ IntentType Enum: 10개 → 17개 (15 고유 카테고리)
- ✅ _initialize_intent_patterns: 15-category 패턴 추가
- ✅ _analyze_with_patterns: 15-category 매핑
- ✅ _suggest_agents (safe_defaults): 15-category 기본값
- ✅ _determine_strategy: parallel/pipeline/conditional 상세 로직
- ✅ available_agents: 15-category use_cases + 확장 도구

**통합 방법**:
```python
# 1. IntentType Enum 확장
class IntentType(Enum):
    # Tests의 15-category 채택
    TERM_DEFINITION = "용어설명"
    LEGAL_INQUIRY = "법률해설"  # LEGAL_CONSULT에서 변경
    # ... (15개 정의)

    # Backend의 시스템 카테고리 유지
    UNCLEAR = "unclear"
    IRRELEVANT = "무관"  # "irrelevant"에서 변경
    ERROR = "error"

# 2. _initialize_intent_patterns: Backend + Tests 패턴 병합
def _initialize_intent_patterns(self):
    return {
        IntentType.LEGAL_INQUIRY: [
            # Tests 패턴
            "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신", "가능한가요",
            # Backend 자연스러운 표현
            "살다", "거주", "세입자", "집주인", "임차인", "임대인", "해지", "계약서",
            # 병합
            "주택임대차보호법", "확정일자", "대항력", "인상", "계약금", "위약금"
        ],
        # ... (15개 모두 병합)
    }

# 3. _suggest_agents: Backend 키워드 필터 + Tests 15-category 매핑
async def _suggest_agents(self, intent_type, query, keywords):
    # Backend: 0차 키워드 필터 (유지 + 확장)
    if intent_type == IntentType.LEGAL_INQUIRY:  # 이름 변경
        analysis_keywords = ["비교", "분석", "계산", ...]
        if not any(kw in query for kw in analysis_keywords):
            return ["search_team"]

    # 새로운 카테고리에 대한 필터 추가
    if intent_type == IntentType.TERM_DEFINITION:
        return ["search_team"]  # 용어설명은 항상 search만

    if intent_type == IntentType.ROI_CALCULATION:
        return ["analysis_team"]  # ROI 계산은 항상 analysis만

    # 기존 LLM 선택 로직 (1차, 2차) 유지
    ...

    # 3차: Tests의 15-category safe_defaults
    safe_defaults = {
        IntentType.TERM_DEFINITION: ["search_team"],
        IntentType.LEGAL_INQUIRY: ["search_team"],
        IntentType.LOAN_SEARCH: ["search_team"],
        # ... (15개 정의)
    }

# 4. _determine_strategy: Tests 로직으로 대체
def _determine_strategy(self, intent, steps):
    # Tests의 상세 로직 채택
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
    # ... (상세 로직)
```

---

#### 2️⃣ intent_analysis.txt 통합 계획

**유지할 Backend 섹션**:
- ✅ Chat History 섹션 (line 205-226)
- ✅ reuse_previous_data 가이드 (line 220-224)
- ✅ CoT 분석 3단계 (line 26-42)
- ✅ reasoning 작성 예시 (line 195-201)
- ✅ 복합 질문 처리 (line 115-137)

**추가/대체할 Tests 섹션**:
- ✅ 9개 카테고리 → 15개 카테고리로 대체
- ✅ Tool 유형별 분류 추가
- ✅ 각 카테고리별 상세 예시 (15개)

**통합 방법**:
```markdown
# Backend의 구조 유지하되 카테고리 부분만 대체

## 분석 원칙
[Backend 유지]

## Chain-of-Thought 분석 (3단계)
[Backend 유지 + 15-category 매핑으로 업데이트]

### 3단계: 의도 결정
- **검색만**: TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY, POLICY_INQUIRY
- **검색+분석**: LOAN_COMPARISON, PROPERTY_INFRA_ANALYSIS, PRICE_EVALUATION, ...
- **분석 전용**: ROI_CALCULATION
- **문서 생성**: CONTRACT_CREATION
- **종합처리**: COMPREHENSIVE

## 의도 카테고리 (15가지)
[Tests 15-category 전체 채택]
**Flow 기반 기능 매핑**: 각 의도는 특정 Tool과 연결되어 있습니다.

### Tool 유형별 분류
[Tests 분류 채택]

## 복합 질문 처리
[Backend 유지]

## reasoning 작성 예시
[Backend 유지]

## 🔹 최근 대화 기록 (Chat History)
[Backend 유지]

**데이터 재사용 판단**:
[Backend 유지]
```

---

#### 3️⃣ agent_selection.txt 통합 계획

**유지할 Backend 섹션**:
- ✅ CoT Agent 선택 프로세스 (line 62-90)
- ✅ 중요 원칙 강조 (line 87-90)
- ✅ 해결책 요청 예시 (line 142-158)
- ✅ 복합 질문 처리 예시 (line 108-159)

**추가/대체할 Tests 섹션**:
- ✅ Agent 도구 목록 확장 (9개 도구)
- ✅ 15-category Agent 매핑 테이블
- ✅ 적합한 의도 매핑 (15개)

**통합 방법**:
```markdown
# Backend 구조 유지하되 도구/매핑 부분 업데이트

## Agent 역할 및 상세 가이드

### 1. search_team (검색 팀)
- **도구**: [Tests의 확장 도구 목록 채택]
  * realestate_terminology 🆕
  * legal_search_tool
  * market_data_tool
  * real_estate_search_tool
  * loan_data_tool
  * building_registry_tool 🆕
  * policy_matcher_tool 🆕

- **적합한 의도**: [15-category 매핑]
  * TERM_DEFINITION (용어설명)
  * LEGAL_INQUIRY (법률해설)
  * LOAN_SEARCH (대출상품검색)
  * BUILDING_REGISTRY (건축물대장조회)
  * POLICY_INQUIRY (정부정책조회)

### 2. analysis_team (분석 팀)
- **도구**: [Tests의 확장 도구 목록]
  * contract_analysis_tool
  * market_analysis_tool
  * roi_calculator_tool 🆕
  * loan_simulator_tool
  * infrastructure_tool 🆕

- **적합한 의도**: [15-category 매핑]
  * LOAN_COMPARISON (대출조건비교)
  * PROPERTY_INFRA_ANALYSIS (매물인프라분석)
  * PRICE_EVALUATION (가격평가)
  * PROPERTY_SEARCH (매물검색)
  * PROPERTY_RECOMMENDATION (맞춤추천)
  * ROI_CALCULATION (투자수익률계산)

## Chain-of-Thought Agent 선택 프로세스
[Backend 유지]

### 중요 원칙:
[Backend 유지 + 15-category 예시 추가]

## 의도별 Agent 매핑 가이드
[9개 → 15개로 업데이트]

| 의도 (Intent) | 기본 조합 | 상황별 조정 |
|--------------|-----------|-------------|
| TERM_DEFINITION | ["search_team"] | 항상 search만 |
| LEGAL_INQUIRY | ["search_team"] | 해결책 요청시 → + analysis |
| LOAN_SEARCH | ["search_team"] | 단순 검색 |
| LOAN_COMPARISON | ["search_team", "analysis_team"] | 비교 분석 필수 |
| ... (15개) |

## 복합 질문 처리 예시
[Backend 유지]
```

---

## 📋 통합 작업 체크리스트

### Phase 1: planning_agent.py 통합 (2시간)

- [ ] **1.1 IntentType Enum 수정**
  - [ ] 15개 카테고리 정의 (TERM_DEFINITION, LEGAL_INQUIRY, ...)
  - [ ] LEGAL_CONSULT → LEGAL_INQUIRY 이름 변경
  - [ ] 값 변경 (계약서작성 → 계약서생성, irrelevant → 무관)
  - [ ] CONTRACT_REVIEW, RISK_ANALYSIS 삭제

- [ ] **1.2 _initialize_intent_patterns 병합**
  - [ ] Tests의 15-category 패턴 추가
  - [ ] Backend의 자연스러운 표현 유지
  - [ ] 양쪽 키워드 병합

- [ ] **1.3 Chat History 기능 유지** (Backend)
  - [ ] Line 186-202 그대로 유지
  - [ ] chat_history 포맷팅 로직

- [ ] **1.4 reuse_previous_data 기능 유지** (Backend)
  - [ ] Line 236-242 그대로 유지
  - [ ] entities에 추가하는 로직

- [ ] **1.5 _analyze_with_patterns 업데이트**
  - [ ] intent_to_agent 매핑 15-category로 확장
  - [ ] Tests 매핑 로직 채택

- [ ] **1.6 _suggest_agents 업데이트**
  - [ ] Backend 키워드 필터 유지 (line 322-349)
  - [ ] 15-category로 확장
  - [ ] safe_defaults 15-category로 업데이트

- [ ] **1.7 _select_agents_with_llm 업데이트**
  - [ ] available_agents 15-category use_cases 추가
  - [ ] Tests 도구 목록 채택

- [ ] **1.8 _determine_strategy 대체**
  - [ ] Tests 로직으로 완전 대체
  - [ ] parallel_intents, pipeline_intents, conditional_intents 정의

---

### Phase 2: intent_analysis.txt 통합 (30분)

- [ ] **2.1 파일 구조 유지** (Backend)
  - [ ] Backend 전체 구조 베이스로 사용

- [ ] **2.2 CoT 분석 업데이트**
  - [ ] 3단계 의도 결정 부분 15-category 매핑

- [ ] **2.3 의도 카테고리 대체**
  - [ ] 9개 카테고리 삭제
  - [ ] Tests 15개 카테고리 전체 복사
  - [ ] Tool 유형별 분류 추가

- [ ] **2.4 Chat History 섹션 유지** (Backend)
  - [ ] Line 205-226 그대로 유지
  - [ ] reuse_previous_data 가이드 유지

- [ ] **2.5 reasoning 예시 유지** (Backend)
  - [ ] Line 195-201 그대로 유지

---

### Phase 3: agent_selection.txt 통합 (30분)

- [ ] **3.1 Agent 도구 목록 업데이트**
  - [ ] search_team: 7개 도구로 확장
  - [ ] analysis_team: 5개 도구로 확장
  - [ ] 각 도구 설명 추가

- [ ] **3.2 적합한 의도 매핑 업데이트**
  - [ ] 15-category 매핑 테이블 작성
  - [ ] 각 팀별 적합한 의도 목록

- [ ] **3.3 CoT 프로세스 유지** (Backend)
  - [ ] Line 62-90 그대로 유지
  - [ ] 4단계 선택 로직 유지

- [ ] **3.4 중요 원칙 업데이트** (Backend)
  - [ ] Line 87-90 유지
  - [ ] 15-category 예시 추가

- [ ] **3.5 의도별 Agent 매핑 테이블 확장**
  - [ ] 9개 → 15개로 확장
  - [ ] 각 의도별 기본 조합 + 상황별 조정

---

### Phase 4: team_supervisor.py 업데이트 (1시간)

- [ ] **4.1 문자열 비교 업데이트**
  - [ ] _get_task_name_for_agent: 15개 의도 처리
  - [ ] _get_task_description_for_agent: 15개 의도 처리
  - [ ] 값 변경 반영 (법률상담 → 법률해설 등)

---

### Phase 5: 검증 및 테스트 (1시간)

- [ ] **5.1 IntentType Enum 검증**
  - [ ] 17개 멤버 확인
  - [ ] 값 정확도 확인

- [ ] **5.2 패턴 매칭 테스트**
  - [ ] 15-category 각각에 대한 테스트 쿼리
  - [ ] fallback 동작 확인

- [ ] **5.3 Agent 선택 테스트**
  - [ ] LLM 기반 선택 테스트
  - [ ] safe_defaults 동작 확인

- [ ] **5.4 Chat History 테스트**
  - [ ] reuse_previous_data 동작 확인
  - [ ] 지시어 처리 테스트

---

## 🎯 통합 후 예상 효과

### 긍정적 영향

1. **의도 분류 정밀도 향상**
   - 10 → 15 카테고리로 세분화
   - 사용자 요청에 더 정확한 대응

2. **Backend 고유 기능 유지**
   - Chat History + reuse_previous_data 유지
   - 대화 맥락 이해 및 데이터 재사용

3. **Agent 매핑 최적화**
   - 15-category 각각에 최적화된 팀 조합
   - 새 도구 지원 (building_registry, infrastructure 등)

4. **실행 전략 고도화**
   - parallel/pipeline/conditional 전략 명확화
   - 응답 속도 향상 (병렬 처리)

5. **프롬프트 품질 향상**
   - CoT 프로세스 유지 + 15-category 예시
   - LLM 응답 품질 향상

### 주의 사항

1. **Breaking Changes 관리**
   - LEGAL_CONSULT → LEGAL_INQUIRY 이름 변경
   - 문자열 값 변경 (법률상담 → 법률해설)
   - team_supervisor.py 동기화 필수

2. **테스트 필수**
   - 15-category 각각에 대한 통합 테스트
   - Chat History + reuse_previous_data 회귀 테스트

3. **문서 업데이트**
   - API 문서, 사용자 가이드 업데이트
   - 15-category 설명 추가

---

## 📊 최종 요약

### Backend를 메인으로 Tests의 장점 추가

| 구분 | Backend 장점 (유지) | Tests 장점 (추가) |
|------|-------------------|------------------|
| **planning_agent.py** | • Chat History<br>• reuse_previous_data<br>• 키워드 필터<br>• 자연스러운 표현 | • 15-category Enum<br>• 상세 패턴<br>• 고도화된 실행 전략<br>• 확장 도구 목록 |
| **intent_analysis.txt** | • CoT 3단계<br>• Chat History 섹션<br>• reuse_previous_data 가이드<br>• reasoning 예시 | • 15-category 정의<br>• Tool 유형별 분류<br>• 상세 예시 (15개) |
| **agent_selection.txt** | • CoT 4단계 프로세스<br>• 중요 원칙 강조<br>• 해결책 요청 예시<br>• 복합 질문 처리 | • 확장 도구 목록 (9개)<br>• 15-category 매핑<br>• 적합한 의도 명시 |

### 통합 작업 예상 시간: **5시간**
- Phase 1: planning_agent.py (2시간)
- Phase 2: intent_analysis.txt (30분)
- Phase 3: agent_selection.txt (30분)
- Phase 4: team_supervisor.py (1시간)
- Phase 5: 검증 및 테스트 (1시간)

---

**문서 작성**: Claude Code
**다음 단계**: 통합 실행 계획서 작성 대기 중
