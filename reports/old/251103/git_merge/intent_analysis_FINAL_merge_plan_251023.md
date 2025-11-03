# Intent Analysis 최종 병합 계획서 (Tool 분석 포함)
## 날짜: 2025-10-23

---

## 📋 개요
- **원본 파일**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt`
- **변경사항 파일**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis_LJM.txt`
- **목적**: LJM 파일의 개선사항을 원본 파일에 체계적으로 병합

---

## 🚨 중요: Tool 불일치 문제 (선행 해결 필요)

### Tool 파일 현황 분석 결과

#### 📊 요약
- **실제 존재하는 Tool**: 12개
- **LJM이 요구하는 Tool**: 13개 (고유)
- **일치율**: 68.75%
- **누락된 Tool**: 5개 카테고리 (4개 파일)

#### ❌ 누락된 Tool 파일
| 카테고리 | 요구 Tool | 대체 방안 |
|----------|-----------|----------|
| TERM_DEFINITION, LEGAL_INQUIRY | `legal_search_tool.py` | `hybrid_legal_search.py` 사용 |
| CONTRACT_PROCEDURE | `contract_step_tool.py` | **완전 누락** |
| BUILDING_REGISTRY | `building_registry_tool.py` | **완전 누락** |
| HOUSING_APPLICATION | `housing_application_tool.py` | **완전 누락** |

### 🔧 Tool 문제 해결 방안

#### **Option 1: LJM 파일 수정** (권장) ✅
```python
# intent_analysis_LJM.txt 수정 사항
1. legal_search_tool.py → hybrid_legal_search.py 변경
2. 누락된 Tool은 주석 처리 또는 대체 Tool 지정
```

#### **Option 2: Placeholder 생성**
```python
# placeholder_tools.py 생성
class ContractStepTool:
    def execute(self, **kwargs):
        return {"status": "not_implemented"}

class BuildingRegistryTool:
    def execute(self, **kwargs):
        return {"status": "not_implemented"}

class HousingApplicationTool:
    def execute(self, **kwargs):
        return {"status": "not_implemented"}
```

#### **Option 3: Tool 매핑 테이블 수정**
```python
TOOL_MAPPING = {
    "TERM_DEFINITION": "hybrid_legal_search",
    "LEGAL_INQUIRY": "hybrid_legal_search",
    "CONTRACT_PROCEDURE": None,  # TODO: 구현 필요
    "BUILDING_REGISTRY": None,   # TODO: 구현 필요
    "HOUSING_APPLICATION": None, # TODO: 구현 필요
    # ... 나머지는 정상 매핑
}
```

---

## 🔄 병합 실행 단계 (수정된 버전)

### Phase 0: Tool 문제 해결 (신규 추가) 🆕
**예상 시간**: 15분
**우선순위**: 최우선

1. **Tool 매핑 결정**
   - [ ] Option 1, 2, 3 중 선택
   - [ ] 선택한 방안 구현

2. **LJM 파일 수정** (Option 1 선택 시)
   - [ ] legal_search_tool → hybrid_legal_search 변경
   - [ ] 누락 Tool 카테고리 처리 방안 결정

3. **Placeholder 생성** (Option 2 선택 시)
   - [ ] placeholder_tools.py 파일 생성
   - [ ] __init__.py에 import 추가

### Phase 1: 파일 준비
**예상 시간**: 5분

1. **백업 생성**
   ```bash
   cp intent_analysis.txt intent_analysis_backup_251023.txt
   ```

2. **LJM 파일 사전 수정**
   - [ ] Line 40 중복 제거 (PROPERTY_SEARCH, PROPERTY_RECOMMENDATION)
   - [ ] Line 431 템플릿 변수 통일 ({query})
   - [ ] Tool 이름 수정 (Option 1 선택 시)

### Phase 2: 핵심 변경사항 적용
**예상 시간**: 15분

1. **3단계 의도 결정 로직 (Line 38-43)**
   - 기존 3줄 → 새로운 5줄로 교체
   - 분류 체계 확장 (검색, 검색+분석, 분석, 생성, 종합)

2. **의도 카테고리 확장 (Line 45-112)**
   - 제목: 9개 → 18개 카테고리
   - Tool 유형별 분류 추가
   - 카테고리 구분 가이드 추가
   - 각 카테고리별 상세 내용 교체

3. **카테고리 이름 변경 반영**
   - LEGAL_CONSULT → LEGAL_INQUIRY
   - LOAN_CONSULT → LOAN_SEARCH
   - CONTRACT_REVIEW → CONTRACT_ANALYSIS

### Phase 3: 예시 및 문서 업데이트
**예상 시간**: 10분

1. **복합 질문 처리 예시 (Line 119-136)**
   - 3개 예시 모두 업데이트
   - 새로운 카테고리 이름 반영

2. **실제 질문 예시 확장 (Line 140-156)**
   - 3개 카테고리 → 18개 카테고리
   - 각 카테고리별 3개 예시 (총 54개)

3. **JSON 응답 형식 (Line 162-183)**
   - intent 필드 예시 업데이트
   - 18개 카테고리 목록 명시
   - reasoning 예시 수정

### Phase 4: 기존 섹션 보존
**예상 시간**: 5분

1. **최근 대화 기록 섹션 유지 (Line 205-227)**
   - LJM에 없지만 반드시 유지
   - reuse_previous_data 기능 보존

2. **템플릿 변수 확인**
   - {chat_history} 유지
   - {query} 변수 통일

### Phase 5: 검증 및 테스트
**예상 시간**: 20분

1. **문법 검증**
   - [ ] JSON 파싱 테스트
   - [ ] 들여쓰기 확인
   - [ ] 특수문자 이스케이프 확인

2. **카테고리 분류 테스트**
   - [ ] 각 카테고리별 2-3개 테스트 질문
   - [ ] 경계 케이스 테스트
   - [ ] 복합 질문 처리 테스트

3. **Tool 연결 테스트**
   - [ ] 존재하는 Tool 정상 작동 확인
   - [ ] 누락 Tool 에러 처리 확인
   - [ ] Fallback 메커니즘 확인

---

## 📊 위험 평가 및 대응 계획

### 위험 요소
| 위험 | 수준 | 대응 방안 |
|------|------|----------|
| Tool 누락으로 인한 런타임 에러 | 🔴 높음 | Placeholder 또는 None 처리 |
| 카테고리 이름 변경으로 기존 코드 영향 | 🟡 중간 | 영향받는 코드 사전 확인 |
| JSON 파싱 오류 | 🟢 낮음 | 사전 검증 도구 활용 |
| 성능 저하 (18개 카테고리) | 🟢 낮음 | 캐싱 전략 검토 |

### Rollback 계획
1. **즉시 롤백 조건**
   - 시스템 다운
   - 모든 의도 분류 실패
   - Tool 로드 실패

2. **롤백 절차**
   ```bash
   # 1. 백업 파일로 복원
   cp intent_analysis_backup_251023.txt intent_analysis.txt

   # 2. 서비스 재시작
   python restart_service.py

   # 3. 로그 확인
   tail -f logs/intent_analysis.log
   ```

---

## ⚠️ 주의사항 (업데이트)

### Tool 관련 주의사항 🆕
1. **누락 Tool 처리**
   - 4개 Tool이 없으므로 해당 카테고리 사용 시 에러 발생 가능
   - 반드시 에러 처리 로직 추가 필요

2. **Tool 이름 불일치**
   - hybrid_legal_search vs legal_search_tool
   - 일관성 있는 이름 사용 필요

3. **Tool 초기화 확인**
   - __init__.py 파일 업데이트 필수
   - import 에러 방지

### 기존 주의사항
1. **호환성 유지**
   - JSON 구조 유지
   - 기존 API 인터페이스 유지

2. **테스트 우선순위**
   - 작동하는 11개 카테고리 우선 테스트
   - 누락 Tool 카테고리는 별도 처리

---

## 📋 최종 체크리스트

### 사전 준비
- [ ] Tool 문제 해결 방안 선택 및 구현
- [ ] 백업 파일 생성
- [ ] LJM 파일 사전 수정 (중복 제거, Tool 이름)
- [ ] 영향받는 코드 확인

### 병합 실행
- [ ] Phase 0: Tool 문제 해결
- [ ] Phase 1: 파일 준비
- [ ] Phase 2: 핵심 변경사항 적용
- [ ] Phase 3: 예시 및 문서 업데이트
- [ ] Phase 4: 기존 섹션 보존
- [ ] Phase 5: 검증 및 테스트

### 병합 후
- [ ] 시스템 정상 작동 확인
- [ ] 로그 모니터링 (최소 30분)
- [ ] 성능 메트릭 확인
- [ ] 사용자 피드백 수집

---

## 📊 예상 결과

### 성공 시나리오 (70% 확률)
- 11개 카테고리 정상 작동
- 5개 카테고리 Placeholder 처리
- 분류 정확도 향상

### 부분 성공 시나리오 (25% 확률)
- 일부 카테고리만 작동
- Tool 에러 발생하지만 시스템 유지
- 추가 디버깅 필요

### 실패 시나리오 (5% 확률)
- 시스템 다운
- 즉시 롤백 필요
- 근본적인 재설계 필요

---

## 🚀 실행 일정

### 권장 실행 시간
- **날짜**: 2025-10-23
- **시간**: 시스템 사용량이 적은 시간대
- **예상 소요시간**: 총 1시간 30분
  - Tool 문제 해결: 15분
  - 병합 작업: 35분
  - 테스트 및 검증: 20분
  - 버퍼 시간: 20분

### 담당자
- **실행**: 개발팀
- **검증**: QA팀
- **승인**: 프로젝트 매니저

---

## 📌 추가 권장사항

### 단계적 접근
1. **1단계**: Tool 문제 해결 및 테스트
2. **2단계**: 작동 확인된 카테고리만 먼저 적용
3. **3단계**: 누락 Tool 개발 후 전체 적용

### 문서화
- 변경 내역 상세 기록
- Tool 매핑 테이블 문서화
- 트러블슈팅 가이드 작성

### 후속 작업
1. **누락 Tool 개발 계획 수립**
   - contract_step_tool.py
   - building_registry_tool.py
   - housing_application_tool.py

2. **성능 최적화**
   - 18개 카테고리 분류 최적화
   - 캐싱 전략 구현

3. **모니터링 강화**
   - 카테고리별 사용 통계
   - Tool 에러율 추적
   - 분류 정확도 메트릭

---

## 🎯 최종 결론

### 병합 가능 여부: ⚠️ **조건부 가능**

**전제 조건**:
1. Tool 문제 해결 (Option 1, 2, 3 중 선택)
2. LJM 파일 사전 수정 완료
3. 에러 처리 로직 준비

**권장 사항**:
- Tool 문제를 먼저 해결한 후 병합 진행
- 단계적 적용으로 리스크 최소화
- 충분한 테스트 시간 확보

---

**작성자**: Claude Assistant
**최종 검토일**: 2025-10-23
**문서 버전**: 2.0 (Tool 분석 포함)
**상태**: 조건부 승인 대기 ⚠️