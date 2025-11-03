# Intent Analysis 파일 병합 계획서
## 날짜: 2025-10-23

---

## 📋 개요
- **원본 파일**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt`
- **변경사항 파일**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis_LJM.txt`
- **목적**: LJM 파일의 개선사항을 원본 파일에 체계적으로 병합

---

## 🔄 주요 변경사항 요약

### 1. 의도 카테고리 확장
- **기존**: 9개 카테고리
- **변경**: 18개 카테고리
- **신규 추가 카테고리**:
  1. TERM_DEFINITION (용어설명)
  2. LEGAL_INQUIRY (법률해설) - LEGAL_CONSULT 세분화
  3. CONTRACT_PROCEDURE (계약절차안내)
  4. LOAN_SEARCH (대출상품검색) - LOAN_CONSULT 세분화
  5. LOAN_COMPARISON (대출조건비교)
  6. BUILDING_REGISTRY (건축물대장조회)
  7. INFRASTRUCTURE_ANALYSIS (인프라분석)
  8. PRICE_EVALUATION (가격평가)
  9. PROPERTY_SEARCH (매물검색)
  10. PROPERTY_RECOMMENDATION (맞춤추천)
  11. ROI_CALCULATION (투자수익률계산)
  12. CONTRACT_ANALYSIS (계약서조항분석)
  13. POLICY_INQUIRY (정부정책조회)
  14. HOUSING_APPLICATION (청약자격확인)

### 2. Tool 유형별 분류 체계 도입
- **Search (검색)**: 단순 정보 조회
- **Search → Analysis (검색+분석)**: 정보 조회 후 분석
- **Analysis (분석)**: 수치/데이터 분석
- **Create Docs (문서생성)**: 새 문서 작성
- **Multiple Tools (종합처리)**: 다중 도구 활용
- **None (무관)**: 부동산 무관 질문

### 3. 카테고리 구분 가이드 추가
중복되기 쉬운 카테고리들의 명확한 구분법 제시:
- TERM_DEFINITION vs LEGAL_INQUIRY
- LOAN_SEARCH vs LOAN_COMPARISON
- PROPERTY_SEARCH vs PROPERTY_RECOMMENDATION
- CONTRACT_PROCEDURE vs CONTRACT_ANALYSIS
- MARKET_INQUIRY vs PRICE_EVALUATION

### 4. 상세한 예시 추가
각 카테고리별로 3-5개의 구체적인 실제 질문 예시와 Tool 매핑 정보 추가

---

## 📝 병합 전략

### Phase 1: 기존 구조 유지 항목
다음 섹션은 변경 없이 유지:
- 분석 원칙
- 부동산 관련 질문 판단 기준
- Chain-of-Thought 분석 (1단계, 2단계)
- 복합 질문 처리 로직
- 응답 형식 (JSON 구조)
- reasoning 작성 예시
- 최근 대화 기록 처리

### Phase 2: 수정이 필요한 항목

#### 2.1 3단계 의도 결정 로직 업데이트
**기존**:
```
- 검색만: LEGAL_CONSULT, MARKET_INQUIRY, LOAN_CONSULT
- 검색+분석: CONTRACT_REVIEW, RISK_ANALYSIS
- 종합처리: COMPREHENSIVE
```

**변경**:
```
- 검색만: TERM_DEFINITION, LEGAL_INQUIRY, LOAN_SEARCH, BUILDING_REGISTRY
- 검색+분석: CONTRACT_PROCEDURE, LOAN_COMPARISON, INFRASTRUCTURE_ANALYSIS, MARKET_INQUIRY, PRICE_EVALUATION, PROPERTY_SEARCH, PROPERTY_RECOMMENDATION, CONTRACT_ANALYSIS, POLICY_INQUIRY, HOUSING_APPLICATION
- 분석 전용: ROI_CALCULATION
- 생성: CONTRACT_CREATION
- 검색/추천: PROPERTY_SEARCH, PROPERTY_RECOMMENDATION
```

#### 2.2 의도 카테고리 섹션 전면 교체
- 9개 카테고리 → 18개 카테고리
- 각 카테고리별 Tool 정보 추가
- 더 상세한 예시와 키워드 제공

#### 2.3 예시 섹션 업데이트
- 복합 질문 처리 예시 업데이트
- 실제 부동산 질문 예시를 18개 카테고리로 확장
- 각 카테고리별 3개씩 구체적 예시 제공

#### 2.4 JSON 응답 규칙 수정
- intent 필드: 9개 → 18개 카테고리 명시

---

## 🔧 구체적 병합 작업

### Step 1: 백업
```bash
# 원본 파일 백업
cp intent_analysis.txt intent_analysis_backup_251023.txt
```

### Step 2: 섹션별 교체 작업

#### A. 3단계 의도 결정 (Line 38-41)
```
# 기존 내용 삭제 후 새 내용으로 교체
```

#### B. 의도 카테고리 섹션 (Line 45-112)
```
# 전체 섹션을 18개 카테고리로 교체
# Tool 정보와 상세 예시 추가
```

#### C. 복합 질문 처리 예시 (Line 119-136)
```
# 예시 업데이트
- LOAN_CONSULT → LOAN_SEARCH
- CONTRACT_REVIEW 예시 → PRICE_EVALUATION 예시로 변경
- LEGAL_CONSULT → LEGAL_INQUIRY
```

#### D. 실제 부동산 질문 예시 섹션 (Line 140-156)
```
# 9개 카테고리 예시 → 18개 카테고리 예시로 확장
# 각 카테고리별 3개 예시 제공
```

#### E. JSON 응답 규칙 (Line 183)
```
# intent 필드 설명 업데이트
# 18개 카테고리 목록 명시
```

### Step 3: 검증
- 모든 카테고리가 올바르게 매핑되었는지 확인
- Tool 정보가 정확한지 검증
- 예시들이 적절한 카테고리에 배치되었는지 확인

### Step 4: 테스트
- 각 카테고리별 테스트 질문으로 분류 정확도 확인
- 복합 질문 처리 로직 테스트
- JSON 응답 형식 검증

---

## ⚠️ 주의사항

1. **호환성 유지**
   - 기존 시스템과의 호환성을 위해 JSON 구조는 유지
   - 새 카테고리 추가로 인한 영향도 분석 필요

2. **세분화된 카테고리 처리**
   - LEGAL_CONSULT → LEGAL_INQUIRY, TERM_DEFINITION 분리
   - LOAN_CONSULT → LOAN_SEARCH, LOAN_COMPARISON 분리
   - 기존 카테고리를 참조하는 코드 수정 필요

3. **Tool 매핑 확인**
   - 각 카테고리별 Tool 파일 존재 여부 확인
   - Tool 파일명과 실제 구현 일치 확인

4. **테스트 케이스 업데이트**
   - 18개 카테고리에 대한 테스트 케이스 작성
   - 카테고리 간 경계 테스트 강화

---

## 📊 예상 효과

1. **분류 정확도 향상**: 세분화된 카테고리로 더 정확한 의도 파악
2. **Tool 연결 최적화**: 각 의도에 맞는 특화 Tool 직접 연결
3. **처리 속도 개선**: 명확한 분류로 불필요한 처리 감소
4. **유지보수 용이성**: 카테고리별 독립적 관리 가능

---

## 🚀 실행 계획

### 즉시 실행 (Phase 1)
1. 백업 파일 생성
2. 3단계 의도 결정 로직 업데이트
3. 의도 카테고리 섹션 교체

### 순차 실행 (Phase 2)
1. 예시 섹션 업데이트
2. JSON 응답 규칙 수정
3. 테스트 및 검증

### 후속 작업 (Phase 3)
1. 관련 코드 수정 (카테고리 참조 부분)
2. Tool 파일 확인 및 연결
3. 전체 시스템 통합 테스트

---

## 📌 체크리스트

- [ ] 원본 파일 백업 완료
- [ ] 3단계 의도 결정 로직 수정
- [ ] 18개 카테고리 섹션 교체
- [ ] 카테고리 구분 가이드 추가
- [ ] 복합 질문 예시 업데이트
- [ ] 실제 질문 예시 확장 (18개)
- [ ] JSON 응답 규칙 수정
- [ ] reasoning 예시 업데이트
- [ ] 테스트 케이스 실행
- [ ] 최종 검증 완료

---

## 📎 참고 문서
- 원본 파일: `intent_analysis.txt`
- 변경사항 파일: `intent_analysis_LJM.txt`
- 백업 파일: `intent_analysis_backup_251023.txt` (생성 예정)