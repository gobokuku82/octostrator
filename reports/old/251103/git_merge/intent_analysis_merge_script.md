# Intent Analysis 병합 실행 스크립트
## 작성일: 2025-10-23

---

## 🎯 병합 대상 파일
- **원본**: `backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt`
- **변경사항**: `backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis_LJM.txt`

---

## 📝 섹션별 상세 병합 내용

### 1️⃣ Section 1: 3단계 의도 결정 (Line 38-41)

**[기존 내용 삭제]**
```
### 3단계: 의도 결정
- **검색만**: 정보 확인형 + 저복잡도 → LEGAL_CONSULT, MARKET_INQUIRY, LOAN_CONSULT
- **검색+분석**: 평가/판단형 OR 중복잡도 → CONTRACT_REVIEW, RISK_ANALYSIS
- **종합처리**: 해결책 요청형 OR 고복잡도 → COMPREHENSIVE
```

**[새로운 내용 삽입]**
```
### 3단계: 의도 결정
- **검색만**: 정보 확인형 + 저복잡도 → TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY
- **검색+분석**: 평가/판단형 OR 중복잡도 → CONTRACT_PROCEDURE, LOAN_COMPARISON, INFRASTRUCTURE_ANALYSIS, MARKET_INQUIRY, PRICE_EVALUATION, PROPERTY_SEARCH, PROPERTY_RECOMMENDATION, CONTRACT_ANALYSIS, POLICY_INQUIRY, HOUSING_APPLICATION
- **분석 전용**: 계산/수치 분석 → ROI_CALCULATION
- **생성**: 문서 작성 → CONTRACT_CREATION
- **검색/추천**: 매물 관련 → PROPERTY_SEARCH, PROPERTY_RECOMMENDATION
```

---

### 2️⃣ Section 2: 의도 카테고리 제목 (Line 45)

**[기존]**
```
## 의도 카테고리 (9가지)
```

**[변경]**
```
## 의도 카테고리 (18가지)
**Flow 기반 기능 매핑**: 각 의도는 특정 Tool과 연결되어 있습니다.

### Tool 유형별 분류
- **Search (검색)**: TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY
- **Search → Analysis (검색+분석)**: CONTRACT_PROCEDURE, LOAN_COMPARISON, INFRASTRUCTURE_ANALYSIS, MARKET_INQUIRY, PRICE_EVALUATION, PROPERTY_SEARCH, PROPERTY_RECOMMENDATION, CONTRACT_ANALYSIS, POLICY_INQUIRY, HOUSING_APPLICATION
- **Analysis (분석)**: ROI_CALCULATION
- **Create Docs (문서생성)**: CONTRACT_CREATION
- **Multiple Tools (종합처리)**: COMPREHENSIVE
- **None (무관)**: IRRELEVANT

### 카테고리 구분 가이드
**중복되기 쉬운 카테고리 구분법**:
- **MARKET_INQUIRY vs PRICE_EVALUATION**:
  * 시세조회 = 단순 가격 확인 ("얼마야?", "시세 알려줘")
  * 가격평가 = 유사 매물 대비 가격 평가 ("이 가격 괜찮아?", "유사 매물보다 비싸?")

- **LOAN_SEARCH vs LOAN_COMPARISON**:
  * 대출상품검색 = 대출 상품 찾기 ("어떤 대출 상품 있어?")
  * 대출조건비교 = 여러 대출 조건 비교 분석 ("어느 은행 금리가 낮아?")

- **CONTRACT_PROCEDURE vs CONTRACT_ANALYSIS**:
  * 계약절차안내 = 계약 단계/순서 안내 ("계약할 때 순서가 어떻게 돼?")
  * 계약서분석 = 계약서 조항 검토/분석 ("이 특약 괜찮아?")

- **TERM_DEFINITION vs LEGAL_INQUIRY**:
  * 용어설명 = 단순 용어/개념 설명 ("LTV가 뭐야?", "임대차법이 뭐야?")
  * 법률해설 = 법률 적용/해석/권리의무 ("전세금 인상 가능해?")

- **PROPERTY_SEARCH vs PROPERTY_RECOMMENDATION**:
  * 매물검색 = 구체적 조건으로 검색 ("3억 이하 아파트 찾아줘")
  * 맞춤추천 = 추상적 선호도 기반 추천 ("나한테 맞는 집", "좋은 곳")

---
```

---

### 3️⃣ Section 3: 카테고리 상세 내용 (Line 47-112) - 전체 교체

**[기존 9개 카테고리 전체 삭제 후 18개 카테고리로 교체]**

```
### 1. TERM_DEFINITION (용어설명) 🔍
- **Tool**: legal_search_tool.py (Search)
- **설명**: 부동산 전문 용어, 개념의 단순 설명 요청
- **예시**:
  * "LTV가 뭐야? 대출받을 때 중요한 개념인가?"
  * "대항력이 뭔가요? 전세 계약할 때 필요한 건가요?"
  * "분양권과 입주권의 차이는? 어떤 걸 사야 하나요?"
  * "재건축과 재개발 차이 알려줘. 투자할 때 뭐가 유리해?"
  * "DSR이 뭔지 설명해주세요"
- **키워드**: 뭐야, 무엇, 의미, 설명, 개념, 정의, 차이, ~란

### 2. LEGAL_INQUIRY (법률해설) 📚
- **Tool**: legal_search_tool.py (Search)
- **설명**: 부동산 관련 법률 적용, 해석, 권리/의무 질문
- **예시**:
  * "집주인이 전세금 5% 이상 올리겠다는데 가능한가요?"
  * "2년 살았는데 임대인이 계약 갱신 거부할 수 있나요?"
  * "주택임대차보호법에서 전세금 인상 한도가 얼마로 정해져 있어요?"
  * "전월세 계약할 때 확정일자 꼭 받아야 하나요? 법적으로 어떤 효력이 있어요?"
  * "월세 계약 중인데 집주인이 갑자기 나가라는데 법적으로 가능한가요?"
- **키워드**: 법, 전세, 임대, 보증금, 계약, 권리, 의무, 갱신, 가능한가요

### 3. CONTRACT_PROCEDURE (계약절차안내) 📋
- **Tool**: contract_step_tool.py (Search → Analysis)
- **설명**: 부동산 계약 단계, 순서, 절차 안내
- **예시**:
  * "처음 전세 계약하는데 순서가 어떻게 되나요? 계약금부터 잔금까지 절차 알려주세요"
  * "매매 계약할 때 계약금은 언제 내고 중도금은 언제 내나요?"
  * "전세 계약서 작성하고 등기부등본 확인은 언제 해야 하나요?"
  * "임대차계약 체결 후 전입신고는 언제까지 해야 대항력 생기나요?"
- **키워드**: 절차, 순서, 단계, 프로세스, 과정, 언제, 타이밍

### 4. LOAN_SEARCH (대출상품검색) 💰
- **Tool**: loan_data_tool.py (Search)
- **설명**: 주택담보대출, 전세자금대출 등 대출 상품 검색
- **예시**:
  * "전세자금대출 상품 어떤 게 있어요? 은행별로 알려주세요"
  * "주택담보대출 상품 찾아줘. 4억 집 살 때 받을 수 있는 거"
  * "신생아 특례대출이 뭐예요? 조건이랑 금리 알려주세요"
  * "청년 전세대출 상품 있나요? 어떤 은행에서 취급하나요?"
- **키워드**: 대출, 상품, 찾다, 어떤 게

### 5. LOAN_COMPARISON (대출조건비교) 💳
- **Tool**: loan_simulator_tool.py (Search → Analysis)
- **설명**: 여러 대출 상품의 조건, 금리, 한도 비교 분석
- **예시**:
  * "KB국민, 신한, 우리은행 주택담보대출 금리 비교해줘. 어디가 제일 낮아?"
  * "연봉 5천만원인데 전세자금대출 얼마까지 받을 수 있어요? 은행별로 비교해주세요"
  * "DSR 40% 규제 적용받는데 어느 은행이 한도가 높아요?"
  * "보금자리론이랑 시중은행 대출 중 어떤 게 유리한가요? 조건 비교 부탁해요"
- **키워드**: 비교, 금리, 한도, 조건, 유리, 어느, 은행별

### 6. BUILDING_REGISTRY (건축물대장조회) 🏢
- **Tool**: building_registry_tool.py (Search)
- **설명**: 건축물대장 API 조회 요청
- **예시**:
  * "서울 강남구 테헤란로 123 건물 건축물대장 조회해줘"
  * "이 빌라 불법 증축 있는지 건축물대장으로 확인 가능해?"
  * "건물 준공일자가 언제인지 건축물대장에서 확인해주세요"
  * "주차장 면적이랑 세대수 건축물대장에 어떻게 나와있어요?"
- **키워드**: 건축물대장, 건물정보, 준공, 용도, 면적

### 7. INFRASTRUCTURE_ANALYSIS (인프라분석) 🏘️
- **Tool**: infrastructure_tool.py (Search → Analysis)
- **설명**: 주변 시설, 교통, 개발계획 등 입지 분석 요청
- **예시**:
  * "송파구 잠실 아파트 주변 지하철역 얼마나 가까워요? 교통 편리한가요?"
  * "아이 키우기 좋은 곳인지 근처 초등학교랑 학원가 분석해줘"
  * "이 동네 GTX 들어온다는데 개발계획 어떻게 돼요?"
  * "헬스장, 마트, 병원 주변에 뭐가 있는지 인프라 분석 부탁해요"
  * "강남구 대치동 학군 어때요? 초중고 배정 어떻게 되나요?"
- **키워드**: 교통, 지하철, 학교, 학군, 편의시설, 병원, 개발계획, 입지, 인프라

### 8. MARKET_INQUIRY (시세트렌드분석) 📈
- **Tool**: market_analysis_tool.py (Search → Analysis)
- **설명**: 지역별 시세 트렌드, 거래 동향 분석
- **예시**:
  * "강남구 아파트 전세 시세 최근 6개월 동안 얼마나 올랐나요?"
  * "서초동 래미안아파트 84㎡ 매매가 작년 대비 얼마나 변했어요?"
  * "송파구 거래량이 늘었다는데 전월 대비 몇 퍼센트 증가했나요?"
  * "요즘 서울 전세 시장 분위기 어때요? 가격 상승세인가요?"
  * "판교 아파트 시세 2024년부터 지금까지 추이 보여주세요"
- **키워드**: 시세, 추이, 트렌드, 거래 동향, 올랐나요, 떨어졌나요

### 9. PRICE_EVALUATION (가격평가) 💵
- **Tool**: market_analysis_tool.py (Search → Analysis)
- **설명**: 유사 매물 대비 가격 적정성 평가
- **예시**:
  * "강남구 대치동 은마아파트 84㎡ 매매가 15억인데 적정한가요?"
  * "같은 평수 비슷한 층 매물이랑 비교했을 때 이 가격 비싼가요?"
  * "주변 아파트 시세 대비 이 집 전세 3억이 합리적인지 평가해줘"
  * "유사 조건 매물보다 1억 높게 나왔는데 적정가인가요?"
- **키워드**: 적정가, 가격 평가, 괜찮아, 비싸, 저렴, 유사 매물

### 10. PROPERTY_SEARCH (매물검색) 🔎
- **Tool**: real_estate_search_tool.py (Search → Analysis)
- **설명**: 특정 조건의 부동산 매물 검색 요청
- **예시**:
  * "강남구 3억 이하 전세 아파트 찾아줘. 방 2개 이상 필요해"
  * "서울대입구역 도보 10분 거리에 월세 50만원 이하 원룸 있어?"
  * "판교 신도시 아파트 중에서 4억대 매매가 84㎡ 검색해줘"
  * "성수동 오피스텔 전세 2억 이하로 나온 매물 리스트 보여줘"
- **키워드**: 찾다, 검색, 구하다, 원하다, 방, 아파트, 오피스텔, 빌라

### 11. PROPERTY_RECOMMENDATION (맞춤추천) ⭐
- **Tool**: real_estate_search_tool.py (Search → Analysis)
- **설명**: 사용자 조건/선호도 기반 매물 추천 요청
- **예시**:
  * "나한테 맞는 집 추천해줘. 직장 강남이고 조용한 곳 좋아해"
  * "예산 4억으로 투자 수익 나올 만한 지역 어디가 좋아요?"
  * "신혼부부 둘이 살기 좋은 아파트 추천해주세요. 편의시설 중요해요"
  * "첫 집 마련하려는데 3억 전세로 직장 접근성 좋은 곳 어디가 좋을까요?"
  * "아이 학교 때문에 학군 좋은 곳으로 이사하려는데 추천 좀 해주세요"
- **키워드**: 추천, 제안, 적합, 좋은, 맞춤, 어디

### 12. ROI_CALCULATION (투자수익률계산) 📊
- **Tool**: roi_calculator_tool.py (Analysis)
- **설명**: 투자 수익률, ROI 계산 요청
- **예시**:
  * "5억 아파트 사서 월세 150만원 받으면 수익률이 얼마나 돼요?"
  * "매매가 3억인 오피스텔 전세 2억으로 놓으면 투자 수익률 계산해줘"
  * "5억짜리 집 매매할까 3억 전세 끼고 2억으로 투자할까? 어느 게 유리해요?"
  * "강남 아파트 월세 수익률이랑 판교 수익률 비교 계산해주세요"
- **키워드**: 투자, 수익률, ROI, 계산, 유리, 손익

### 13. CONTRACT_ANALYSIS (계약서조항분석) 📄
- **Tool**: contract_analysis_tool.py (Search → Analysis)
- **설명**: 기존 계약서 조항 검토/분석 요청
- **예시**:
  * "이 임대차계약서 검토해주세요. 불리한 조항 있는지 확인 부탁해요"
  * "특약사항에 '수리비는 임차인 부담'이라고 되어 있는데 문제없나요?"
  * "계약서 4조 이 조항 위험한 거 아니에요? 분석 좀 해주세요"
  * "전세계약서 받았는데 보증금 반환 관련 조항 확인해주세요"
- **키워드**: 검토, 확인, 점검, 리뷰, 분석, 조항

### 14. POLICY_INQUIRY (정부정책조회) 🏛️
- **Tool**: policy_matcher_tool.py (Search → Analysis)
- **설명**: 정부 지원 정책, 세제 혜택 관련 질문
- **예시**:
  * "생애최초 특별공급 자격 조건이 뭐예요? 소득 기준 있나요?"
  * "신혼부부 대상 정부 지원 정책 어떤 거 있어요? 대출이랑 청약 다 알려주세요"
  * "청년 전월세 대출 받을 수 있는 조건 뭐예요? 나이 제한 있나요?"
  * "다자녀 가구 혜택 어떤 게 있어요? 청약 가점이랑 세금 감면 알려주세요"
- **키워드**: 특별공급, 생애최초, 신혼부부, 청년, 지원, 정책, 혜택

### 15. HOUSING_APPLICATION (청약자격확인) 🎫
- **Tool**: housing_application_tool.py (Search → Analysis)
- **설명**: 청약 자격, 가점 확인 요청
- **예시**:
  * "무주택 3년차인데 이번 단지 청약 자격 있어요?"
  * "청약 가점 계산해줘. 무주택 5년, 부양가족 2명, 통장 3년차"
  * "특별공급 1순위 조건 뭐예요? 신혼부부인데 소득 기준 알려주세요"
  * "생애최초 청약하려는데 자격 되는지 확인 좀 해주세요"
- **키워드**: 청약, 자격, 가점, 1순위, 계산

### 16. CONTRACT_CREATION (계약서생성) 📝
- **Tool**: lease_contract_generator_tool.py (Create Docs)
- **설명**: 새로운 임대차계약서 작성 요청
- **예시**:
  * "전세 보증금 2억으로 임대차계약서 작성해주세요. 기간은 2년이요"
  * "월세 보증금 1천, 월세 60만원으로 계약서 만들어주세요"
  * "상가 임대차계약서 초안 생성 부탁해요. 월세 200만원 조건이에요"
  * "전세계약서 양식 필요한데 특약사항도 넣어서 만들어주세요"
- **키워드**: 작성, 만들, 생성, 초안, 계약서

### 17. COMPREHENSIVE (종합분석) 🔄
- **Tool**: Multiple Tools (Search → Analysis → Recommendation)
- **설명**: 여러 측면의 종합 분석이 필요하거나 복잡한 상황에 대한 해결책 요청
- **예시**:
  * "강남에서 자취방 구하는데 교통 좋고 안전한 곳 추천해줘. 대출도 받아야 하는데 어떻게 해야 해?"
  * "이 아파트 매매할까 전세 낄까 고민인데, 주변 시세도 보고 투자 가치도 분석해줘"
  * "전세 계약 만료인데 집주인이 보증금 2배 올려달래. 법적으로 문제없는지 확인하고 대응 방법 알려줘"
  * "신혼집 구하는데 예산 5억으로 어느 지역이 좋을까? 학군, 개발계획, 시세 상승 가능성 다 고려해줘"
- **키워드**: 종합, 전체, 모든, 복합적, 다각도, 어떻게 해야, 고민, 분석+추천
- **특징**: 3개 이상의 다른 Tool이 필요하거나, 복잡한 의사결정 지원이 필요한 경우

### 18. IRRELEVANT (무관) ❌
- **Tool**: None
- **설명**: 부동산과 전혀 관련 없는 질문
- **예시**:
  * 인사/작별: "안녕", "hi", "고마워", "bye"
  * 감정/반응: "ㅋㅋㅋ", "와", "좋아"
  * 테스트: "테스트", "test", "123"
  * 다른 분야: "주식 추천", "여행지 추천", "날씨 어때?"
- **처리**: 부동산 관련 질문 유도 메시지 표시
```

---

### 4️⃣ Section 4: 복합 질문 처리 예시 업데이트 (Line 119-136)

**[예시 1 수정]**
```
### 예시 1: "강남구 시세 확인하고 전세자금대출도 알려줘"
**분석**:
1. 유형: 정보 확인형 (두 가지)
2. 복잡도: 중 (두 독립 조회)
3. 의도: MARKET_INQUIRY (주), LOAN_SEARCH (부)  // LOAN_CONSULT → LOAN_SEARCH
```

**[예시 2 교체]**
```
### 예시 2: "이 아파트 가격 괜찮은지 보고 대출 조건도 비교해줘"
**분석**:
1. 유형: 평가/판단형
2. 복잡도: 중 (가격평가 + 대출비교)
3. 의도: PRICE_EVALUATION (주), LOAN_COMPARISON (부)
```

**[예시 3 수정]**
```
### 예시 3: "강남에서 자취방 구하려는데 교통 좋고 가격 적정한 곳 추천해줘"
**분석**:
1. 유형: 해결책 요청형
2. 복잡도: 중 (매물추천 + 인프라 + 가격평가)
3. 의도: PROPERTY_RECOMMENDATION (주), INFRASTRUCTURE_ANALYSIS (부), PRICE_EVALUATION (부)
```

---

### 5️⃣ Section 5: 실제 부동산 질문 예시 (Line 140-156) - 전체 교체

**[기존 3개 카테고리 예시 삭제 후 18개 카테고리 예시로 교체]**

각 카테고리별 3개씩, 총 54개 예시 추가 (상세 내용은 위 카테고리 섹션 참조)

---

### 6️⃣ Section 6: JSON 응답 형식 업데이트 (Line 162-179)

**[Line 163 수정]**
```json
{
    "intent": "LEGAL_INQUIRY",  // LEGAL_CONSULT → LEGAL_INQUIRY
    ...
```

**[Line 178 수정]**
```
    "reasoning": "1단계(유형): 정보 확인형. 2단계(복잡도): 저 - 단일 개념. 3단계(의도): 검색만으로 충분 → LEGAL_INQUIRY"
```

**[Line 183 수정]**
```
- intent: 18개 카테고리 중 하나 (대문자_언더스코어)
  * TERM_DEFINITION, LEGAL_INQUIRY, CONTRACT_PROCEDURE, LOAN_SEARCH, LOAN_COMPARISON,
  * BUILDING_REGISTRY, INFRASTRUCTURE_ANALYSIS, MARKET_INQUIRY, PRICE_EVALUATION,
  * PROPERTY_SEARCH, PROPERTY_RECOMMENDATION, ROI_CALCULATION, CONTRACT_ANALYSIS,
  * POLICY_INQUIRY, HOUSING_APPLICATION, CONTRACT_CREATION, COMPREHENSIVE, IRRELEVANT
```

---

### 7️⃣ Section 7: reasoning 작성 예시 업데이트 (Line 197-198)

**[좋은 예 수정]**
```
"1단계(유형): 해결책 요청형 - '추천해줘' 포함. 2단계(복잡도): 중 - 사용자 조건 기반 매물 추천. 3단계(의도): 검색/추천 필요 → PROPERTY_RECOMMENDATION"
```

**[나쁜 예 수정]**
```
"전세금 인상에 대한 법률 질문이므로 LEGAL_INQUIRY로 분류" (단계별 분석 누락)
```

---

## ✅ 실행 체크리스트

### 병합 전 준비
- [ ] 원본 파일 백업 (intent_analysis_backup_251023.txt)
- [ ] 변경사항 파일 확인 (intent_analysis_LJM.txt)
- [ ] 영향받는 시스템 컴포넌트 확인

### 병합 작업
- [ ] Section 1: 3단계 의도 결정 수정
- [ ] Section 2: 카테고리 제목 및 분류 체계 추가
- [ ] Section 3: 18개 카테고리 상세 내용 교체
- [ ] Section 4: 복합 질문 처리 예시 업데이트
- [ ] Section 5: 실제 질문 예시 확장 (18개)
- [ ] Section 6: JSON 응답 형식 업데이트
- [ ] Section 7: reasoning 예시 수정

### 병합 후 검증
- [ ] 파일 문법 오류 확인
- [ ] 카테고리 매핑 정확성 검증
- [ ] Tool 파일 연결 확인
- [ ] 테스트 케이스 실행
- [ ] 시스템 통합 테스트

---

## 💡 주의사항

1. **카테고리 이름 변경 주의**
   - LEGAL_CONSULT → LEGAL_INQUIRY로 변경됨
   - LOAN_CONSULT → LOAN_SEARCH로 세분화됨
   - 기존 코드에서 이 카테고리들을 참조하는 부분 확인 필요

2. **새로운 카테고리 추가**
   - 9개 → 18개로 2배 증가
   - 각 카테고리별 Tool 파일 존재 확인 필수

3. **Tool 매핑 확인**
   - 각 카테고리에 명시된 Tool 파일이 실제로 존재하는지 확인
   - Tool 파일 경로와 이름이 정확한지 검증

4. **하위 시스템 영향도**
   - 의도 분류 결과를 사용하는 모든 컴포넌트 확인
   - API 응답 형식 변경에 따른 프론트엔드 수정 필요 여부 확인