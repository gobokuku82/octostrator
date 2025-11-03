# Phase 2 Test Plan: 복잡한 복합 질문 처리 테스트

**작성일**: 2025년 10월 5일
**Phase 1 결과 기반**: 40개 질문 테스트 완료
**실행 예정**: Phase 1 수정 완료 후

---

## 📋 테스트 개요

### 목적
Phase 1에서 발견된 문제점을 수정한 후, **더 복잡한 복합 질문**에 대한 시스템 처리 능력을 검증합니다.

### 테스트 범위
1. **3개 이상 작업 복합 질문**: 30개
2. **고난이도 복합 질문**: 30개
3. **총 테스트 케이스**: 60개

### 성공 기준
- Query Decomposition 성공률 > 80%
- Task 분해 정확도 > 85%
- Agent 선택 정확도 > 90%
- Parallel/Sequential 판단 정확도 > 85%
- E2E 실행 성공률 > 90%

---

## 1. 3개 이상 작업 복합 질문 (30개)

### 1.1 카테고리: 검색 → 분석 → 문서 (10개)

#### T3-001
**질문**: "강남구 아파트 시세 조회하고 대출 한도 계산한 후 계약서 작성해줘"
**기대 분해**:
1. 강남구 아파트 시세 조회 (search_team)
2. 대출 한도 계산 (analysis_team, depends_on: task_0)
3. 계약서 작성 (document_team, depends_on: task_1)
**실행 모드**: sequential
**난이도**: ⭐⭐⭐

#### T3-002
**질문**: "서초 전세 시세 확인하고 법적 주의사항 찾고 종합 보고서 만들어줘"
**기대 분해**:
1. 서초 전세 시세 확인 (search_team)
2. 법적 주의사항 검색 (search_team, parallel with task_0)
3. 종합 보고서 작성 (document_team, depends_on: task_0, task_1)
**실행 모드**: mixed (병렬 + 순차)
**난이도**: ⭐⭐⭐⭐

#### T3-003
**질문**: "송파 아파트 시세 분석하고 투자 가치 평가한 후 리스크 리포트 작성해줘"
**기대 분해**:
1. 송파 아파트 시세 조회 (search_team)
2. 투자 가치 평가 (analysis_team, depends_on: task_0)
3. 리스크 리포트 작성 (document_team, depends_on: task_1)
**실행 모드**: sequential
**난이도**: ⭐⭐⭐

#### T3-004
**질문**: "마포 월세 시세 찾고 주택담보대출 조건 확인하고 비교 표 만들어줘"
**기대 분해**:
1. 마포 월세 시세 조회 (search_team)
2. 주택담보대출 조건 검색 (search_team, parallel)
3. 비교 표 생성 (analysis_team, depends_on: task_0, task_1)
**실행 모드**: mixed
**난이도**: ⭐⭐⭐

#### T3-005
**질문**: "용산 재개발 지역 법규 확인하고 시세 동향 분석하고 투자 의견서 작성해줘"
**기대 분해**:
1. 재개발 법규 확인 (search_team)
2. 시세 동향 분석 (search_team → analysis_team, parallel start)
3. 투자 의견서 작성 (document_team, depends_on: all)
**실행 모드**: mixed
**난이도**: ⭐⭐⭐⭐

#### T3-006
**질문**: "전세 사기 예방 법률 찾고 계약서 검토하고 안전 체크리스트 만들어줘"
**기대 분해**:
1. 전세 사기 예방 법률 검색 (search_team)
2. 계약서 법적 검토 (search_team → analysis_team)
3. 안전 체크리스트 생성 (document_team, depends_on: all)
**실행 모드**: sequential
**난이도**: ⭐⭐⭐⭐

#### T3-007
**질문**: "강남 vs 서초 아파트 시세 비교하고 투자 수익률 계산하고 추천서 작성해줘"
**기대 분해**:
1. 강남 아파트 시세 조회 (search_team)
2. 서초 아파트 시세 조회 (search_team, parallel)
3. 시세 비교 및 수익률 계산 (analysis_team, depends_on: task_0, task_1)
4. 투자 추천서 작성 (document_team, depends_on: task_2)
**실행 모드**: mixed
**난이도**: ⭐⭐⭐⭐⭐

#### T3-008
**질문**: "LTV, DTI 규제 확인하고 대출 가능액 계산하고 금융 계획서 만들어줘"
**기대 분해**:
1. LTV, DTI 규제 검색 (search_team)
2. 대출 가능액 계산 (analysis_team, depends_on: task_0)
3. 금융 계획서 작성 (document_team, depends_on: task_1)
**실행 모드**: sequential
**난이도**: ⭐⭐⭐

#### T3-009
**질문**: "임대차보호법 적용 범위 확인하고 계약서 리뷰하고 수정안 제시해줘"
**기대 분해**:
1. 임대차보호법 적용 범위 검색 (search_team)
2. 계약서 법적 리뷰 (analysis_team, depends_on: task_0)
3. 계약서 수정안 작성 (document_team, depends_on: task_1)
**실행 모드**: sequential
**난이도**: ⭐⭐⭐⭐

#### T3-010
**질문**: "성동구 빌라 시세 조회하고 전세 전환 계산하고 손익 분석 보고서 작성해줘"
**기대 분해**:
1. 성동구 빌라 시세 조회 (search_team)
2. 전세 전환 계산 (analysis_team, depends_on: task_0)
3. 손익 분석 보고서 작성 (document_team, depends_on: task_1)
**실행 모드**: sequential
**난이도**: ⭐⭐⭐⭐

### 1.2 카테고리: 병렬 검색 → 통합 분석 (10개)

#### T3-011
**질문**: "강남, 서초, 송파 전세 시세 모두 조회하고 지역별 비교 분석해줘"
**기대 분해**:
1. 강남 전세 시세 (search_team)
2. 서초 전세 시세 (search_team, parallel)
3. 송파 전세 시세 (search_team, parallel)
4. 지역별 비교 분석 (analysis_team, depends_on: all)
**실행 모드**: mixed (3-way parallel → analysis)
**난이도**: ⭐⭐⭐⭐

#### T3-012
**질문**: "전세, 월세, 매매 시세 동시에 찾고 가격 비교 그래프 만들어줘"
**기대 분해**:
1. 전세 시세 조회 (search_team)
2. 월세 시세 조회 (search_team, parallel)
3. 매매 시세 조회 (search_team, parallel)
4. 비교 그래프 생성 (analysis_team, depends_on: all)
**실행 모드**: parallel → sequential
**난이도**: ⭐⭐⭐⭐

#### T3-013
**질문**: "KB, 신한, 우리은행 주택대출 상품 찾고 금리 비교 분석해줘"
**기대 분해**:
1. KB 주택대출 상품 조회 (search_team)
2. 신한 주택대출 상품 조회 (search_team, parallel)
3. 우리은행 주택대출 상품 조회 (search_team, parallel)
4. 금리 비교 분석 (analysis_team, depends_on: all)
**실행 모드**: parallel → analysis
**난이도**: ⭐⭐⭐⭐

#### T3-014
**질문**: "법률 DB, 시세 DB, 대출 DB 모두 검색하고 종합 리포트 작성해줘"
**기대 분해**:
1. 법률 정보 검색 (search_team)
2. 시세 정보 검색 (search_team, parallel)
3. 대출 정보 검색 (search_team, parallel)
4. 종합 리포트 작성 (analysis_team → document_team, depends_on: all)
**실행 모드**: parallel → sequential
**난이도**: ⭐⭐⭐⭐⭐

#### T3-015
**질문**: "아파트, 빌라, 오피스텔 전세 시세 비교하고 투자 추천해줘"
**기대 분해**:
1. 아파트 전세 시세 (search_team)
2. 빌라 전세 시세 (search_team, parallel)
3. 오피스텔 전세 시세 (search_team, parallel)
4. 시세 비교 및 투자 추천 (analysis_team, depends_on: all)
**실행 모드**: parallel → analysis
**난이도**: ⭐⭐⭐⭐

#### T3-016-020
*(유사 패턴으로 5개 더 생성)*

### 1.3 카테고리: 조건부 실행 (10개)

#### T3-021
**질문**: "강남 아파트 시세 조회하고 적정가면 대출 상담, 비싸면 다른 지역 추천해줘"
**기대 분해**:
1. 강남 아파트 시세 조회 (search_team)
2. 가격 적정성 평가 (analysis_team, depends_on: task_0)
3a. (조건: 적정) 대출 상담 (search_team, conditional)
3b. (조건: 비쌈) 대안 지역 추천 (analysis_team, conditional)
**실행 모드**: conditional
**난이도**: ⭐⭐⭐⭐⭐

#### T3-022-030
*(조건부 실행 패턴 9개 더)*

---

## 2. 고난이도 복합 질문 (30개)

### 2.1 카테고리: 시계열 분석 + 예측 (10개)

#### TC-001
**질문**: "강남 아파트 3년치 시세 동향 분석하고 향후 1년 예측하고 투자 의견서 작성해줘"
**기대 분해**:
1. 3년치 시세 데이터 수집 (search_team)
2. 시계열 동향 분석 (analysis_team, depends_on: task_0)
3. 향후 1년 가격 예측 (analysis_team, depends_on: task_1)
4. 투자 의견서 작성 (document_team, depends_on: task_2)
**실행 모드**: sequential (4단계)
**특이사항**: 시계열 데이터 처리, 예측 모델 필요
**난이도**: ⭐⭐⭐⭐⭐

#### TC-002
**질문**: "서초 전세가율 5년 추이 분석하고 매매 대비 전세 선택 시 손익 계산하고 세금까지 고려한 종합 의견 줘"
**기대 분해**:
1. 5년치 전세가율 데이터 수집 (search_team)
2. 전세가율 추이 분석 (analysis_team)
3. 매매 vs 전세 손익 계산 (analysis_team)
4. 세금 영향 분석 (search_team → analysis_team)
5. 종합 의견서 작성 (document_team)
**실행 모드**: complex sequential
**특이사항**: 다단계 재무 계산, 세금 DB 조회
**난이도**: ⭐⭐⭐⭐⭐

#### TC-003-010
*(유사 시계열 분석 8개 더)*

### 2.2 카테고리: 다중 조건 최적화 (10개)

#### TC-011
**질문**: "예산 5억, 출퇴근 30분 이내, 학군 좋은 곳, 전세가율 70% 이하 조건으로 최적 물건 찾고 대출 계획 세우고 계약서 초안 만들어줘"
**기대 분해**:
1. 조건 분석 및 검색 쿼리 생성 (analysis_team)
2. 다중 조건 부동산 검색 (search_team, depends_on: task_0)
3. 검색 결과 최적화 (analysis_team, depends_on: task_1)
4. 대출 계획 수립 (search_team → analysis_team)
5. 계약서 초안 작성 (document_team)
**실행 모드**: complex sequential + parallel
**특이사항**: 다중 조건 최적화, 의사결정 필요
**난이도**: ⭐⭐⭐⭐⭐

#### TC-012-020
*(유사 최적화 문제 9개 더)*

### 2.3 카테고리: 시나리오 비교 분석 (10개)

#### TC-021
**질문**: "A: 강남 전세 vs B: 서초 매매 두 시나리오 각각 5년 후 자산 가치 예측하고, 대출 이자 포함한 총비용 계산하고, 리스크 평가해서 추천해줘"
**기대 분해**:
1. 시나리오 A - 강남 전세 정보 수집 (search_team)
2. 시나리오 B - 서초 매매 정보 수집 (search_team, parallel)
3. 시나리오 A - 5년 후 예측 (analysis_team)
4. 시나리오 B - 5년 후 예측 (analysis_team, parallel)
5. 시나리오 A - 총비용 계산 (analysis_team)
6. 시나리오 B - 총비용 계산 (analysis_team, parallel)
7. 두 시나리오 비교 분석 (analysis_team)
8. 리스크 평가 (analysis_team)
9. 최종 추천 보고서 (document_team)
**실행 모드**: complex parallel + sequential
**특이사항**: 9단계 복합 작업, 병렬/순차 혼합
**난이도**: ⭐⭐⭐⭐⭐

#### TC-022-030
*(유사 시나리오 비교 9개 더)*

---

## 3. 테스트 실행 계획

### 3.1 전제 조건
- [ ] Phase 1 발견 이슈 모두 수정 완료
- [ ] Prompt 파일 정리 (변수, JSON 형식)
- [ ] Available agents 연동 완료
- [ ] Validation 로직 수정 완료
- [ ] Query decomposition LLM 호출 정상화

### 3.2 테스트 환경 준비
```bash
# 1. 테스트 데이터 생성
backend/app/service_agent/reports/tests/test_queries_phase2.json

# 2. 실행 스크립트 작성
backend/app/service_agent/reports/tests/run_phase2_test.py

# 3. 검증 기준 강화
- Decomposition 정확도
- Dependency 순서
- Parallel group 구성
- Agent selection 정확도
```

### 3.3 실행 순서
1. **3개 작업 복합 질문 (30개)**:
   - 순차 실행: 10개
   - 병렬 실행: 10개
   - 조건부 실행: 10개

2. **고난이도 복합 질문 (30개)**:
   - 시계열 분석: 10개
   - 다중 조건 최적화: 10개
   - 시나리오 비교: 10개

3. **결과 분석 및 보고서**:
   - 자동 결과 집계
   - 실패 케이스 분석
   - 개선 방향 도출

### 3.4 성공 기준 상세

#### Decomposition 정확도 (> 80%)
```python
# 검증 항목
- 작업 수 일치 (expected_tasks vs actual_tasks)
- 작업 설명 적절성 (semantic similarity)
- Agent 할당 정확성 (team selection)
```

#### Dependency 정확도 (> 90%)
```python
# 검증 항목
- Dependency 관계 올바름
- Circular dependency 없음
- Parallel group 구성 적절
```

#### Execution Mode 정확도 (> 85%)
```python
# 검증 항목
- Sequential/Parallel/Conditional 판단
- Parallel opportunities 활용
- Execution strategy 최적화
```

---

## 4. 예상 어려움 및 대응 방안

### 4.1 예상 문제점

#### 문제 1: 복잡한 의존성 처리
**증상**: 4단계 이상 sequential 작업에서 dependency 오류
**대응**:
- Dependency graph validation 강화
- Topological sort 적용
- Circular dependency 사전 감지

#### 문제 2: 조건부 실행 미지원
**증상**: Conditional execution mode 구현 안됨
**대응**:
- Phase 2에서는 조건부 케이스 skip
- 또는 manual intervention point 추가
- Phase 3에서 HITL 통합 시 구현

#### 문제 3: LLM Token Limit
**증상**: 복잡한 질문 처리 시 context 초과
**대응**:
- Prompt compression
- Multi-turn decomposition
- Hierarchical planning

### 4.2 Fallback 전략

#### Level 1: LLM Decomposition 실패
→ Pattern-based decomposition (keyword 기반)

#### Level 2: Execution Plan 생성 실패
→ Default sequential plan 생성

#### Level 3: Agent 실행 실패
→ Alternative agent 선택

---

## 5. 기대 효과 및 학습 목표

### 5.1 기술적 검증
- [ ] 복잡한 질문 분해 능력 확인
- [ ] 다단계 작업 오케스트레이션
- [ ] 병렬/순차 실행 최적화
- [ ] Agent 간 데이터 전달 안정성

### 5.2 품질 목표
- [ ] E2E 성공률 > 90%
- [ ] 평균 실행 시간 < 10초
- [ ] Decomposition 정확도 > 80%
- [ ] 사용자 의도 보존률 > 95%

### 5.3 학습 내용
- LLM의 복잡한 reasoning 능력 평가
- Prompt engineering 고도화
- System design trade-offs 이해
- Error recovery 전략 최적화

---

## 6. Timeline

### Week 1
- [ ] Phase 1 이슈 수정
- [ ] Phase 2 테스트 데이터 작성 (60개)
- [ ] 실행 스크립트 준비

### Week 2
- [ ] 3개 작업 복합 질문 테스트 (30개)
- [ ] 결과 분석 및 1차 보고서

### Week 3
- [ ] 이슈 수정 (발견 시)
- [ ] 고난이도 복합 질문 테스트 (30개)
- [ ] 최종 보고서 작성

### Week 4
- [ ] Phase 3 준비 (Checkpoint, Memory)
- [ ] Production deployment 검토

---

## 7. 체크리스트

### 시작 전
- [ ] Phase 1 모든 이슈 해결됨
- [ ] 단위 테스트 통과
- [ ] Prompt 파일 검증
- [ ] Agent Registry 연동 확인

### 실행 중
- [ ] 실시간 모니터링
- [ ] 에러 로그 수집
- [ ] 중간 결과 저장
- [ ] 성능 메트릭 추적

### 완료 후
- [ ] 결과 분석 완료
- [ ] 보고서 작성
- [ ] 개선 사항 정리
- [ ] Phase 3 계획 수립

---

**작성자**: AI Development Team
**실행 시작 예정**: Phase 1 수정 완료 후
**예상 소요 시간**: 3-4주