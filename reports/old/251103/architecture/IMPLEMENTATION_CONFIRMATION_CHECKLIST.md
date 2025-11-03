# SearchTeam 건너뛰기 구현 전 확인사항

**작성일**: 2025-10-22
**목적**: 구현 전 사용자 확인 및 의사결정 사항 정리

---

## 🚨 필수 확인사항 (구현 전 반드시 답변 필요)

### 1. 기본 전제 확인

#### Q1. Checkpointer가 현재 정상 작동 중인가?

**확인 방법**:
```bash
# PostgreSQL 접속
psql -U postgres -d real_estate

# checkpoints 테이블 존재 확인
\dt checkpoints

# 최근 데이터 확인
SELECT thread_id,
       (checkpoint->'channel_values'->>'query') as query,
       metadata->>'ts' as timestamp
FROM checkpoints
ORDER BY metadata->>'ts' DESC
LIMIT 5;
```

**예상 결과**:
```
thread_id       | query              | timestamp
----------------|--------------------|--------------------------
session-abc123  | 강남구 아파트 시세    | 2025-10-22T10:00:00.123Z
...
```

**질문**:
- [ ] checkpoints 테이블이 존재하는가?
- [ ] 실제 대화 데이터가 저장되고 있는가?
- [ ] thread_id가 chat_session_id와 일치하는가?

**만약 No라면**: 먼저 Checkpointer 설정부터 확인 필요!

---

#### Q2. Intent 분석 시 entities가 제대로 추출되는가?

**확인 방법**:
```python
# 테스트 쿼리
"강남구 아파트 시세"

# 예상 Intent 결과
{
  "intent_type": "market_inquiry",
  "entities": {
    "region": "강남구",        # ✅ 있어야 함
    "property_type": "아파트"   # ✅ 있어야 함
  }
}
```

**현재 상태 확인**:
- [ ] entities 필드가 있는가?
- [ ] region이 추출되는가?
- [ ] property_type이 추출되는가?

**만약 entities가 없다면**:
```
Option A: intent_analysis.txt 프롬프트 수정 필요 (10줄 추가)
Option B: 당장은 Intent만 비교 (덜 정확하지만 작동 가능)
```

**질문**: 어느 옵션을 선택하시겠습니까?

---

### 2. 비즈니스 로직 확인

#### Q3. Intent별 신선도 기준이 적절한가?

**현재 설정**:
| Intent Type | 유효기간 | 이유 |
|-------------|---------|------|
| MARKET_INQUIRY | 7일 | 시세는 자주 변동 |
| LEGAL_CONSULT | 30일 | 법률은 안정적 |
| LOAN_CONSULT | 1일 | 금리는 매일 변동 |

**질문**:
- [ ] MARKET_INQUIRY 7일이 적절한가? (너무 길지 않은가?)
- [ ] LEGAL_CONSULT 30일이 적절한가?
- [ ] LOAN_CONSULT 1일이 적절한가?

**사용자 입력**:
- MARKET_INQUIRY: ___일
- LEGAL_CONSULT: ___일
- LOAN_CONSULT: ___일

**또는** "일단 제안된 기준대로 진행하고, 나중에 데이터 보고 조정" 선택?

---

#### Q4. 어떤 Intent부터 적용할 것인가?

**Option A: MARKET_INQUIRY만 (안전, 권장)**
```python
# Phase 1에서는 시장 시세 조회만
if intent_type == "market_inquiry":
    # 건너뛰기 체크
```
- 장점: 안전하게 시작
- 단점: 다른 Intent는 혜택 없음

**Option B: 모든 Intent (적극적)**
```python
# MARKET, LEGAL, LOAN 모두 적용
if intent_type in ["market_inquiry", "legal_consult", "loan_consult"]:
    # Intent별 다른 기준 적용
```
- 장점: 최대 효과
- 단점: 리스크 증가

**질문**: 어느 옵션을 선택하시겠습니까?
- [ ] Option A (MARKET_INQUIRY만)
- [ ] Option B (모든 Intent)
- [ ] Option C (직접 선택): _____________

---

#### Q5. Entity 매칭 기준은?

**현재 설정 (Phase 1)**:
```python
# 정확 일치만
region_match = (current["region"] == prev["region"])
property_match = (current["property_type"] == prev["property_type"])
```

**예시**:
- "강남구" == "강남구" → ✅ 일치
- "강남구" == "강남" → ❌ 불일치 (새로 검색)

**질문**:
- [ ] 정확 일치만 사용 (안전하지만 보수적)
- [ ] 유사도 허용 ("강남" = "강남구") → Phase 2 필요

**당장 유사도 필요한가?**
- [ ] Yes → Phase 1에 포함 (구현 시간 +20분)
- [ ] No → Phase 1은 정확 일치만, Phase 2에서 추가

---

### 3. 사용자 경험 관련

#### Q6. 사용자에게 "이전 데이터 재사용 중" 알림을 보여줄 것인가?

**Option A: 알림 표시**
```
프론트엔드 메시지:
"💡 최근 검색 결과를 재사용하여 빠르게 응답합니다 (2분 전 데이터)"
```
- 장점: 투명성, 사용자 이해 증가
- 단점: UI 수정 필요

**Option B: 조용히 처리**
```
로그만 남기고 사용자에게는 알리지 않음
```
- 장점: UI 수정 불필요
- 단점: 사용자가 왜 빠른지 모름

**질문**: 어느 옵션을 선택하시겠습니까?
- [ ] Option A (알림 표시) → WebSocket 메시지 추가 필요
- [ ] Option B (조용히 처리)

---

#### Q7. 오래된 데이터 재사용 시 사용자에게 확인받을 것인가?

**시나리오**:
```
대화1: "강남구 아파트" (6일 전)
대화2: "강남구 아파트" (오늘)
→ 7일 기준의 85% (애매한 경계선)
```

**Option A: 자동 판단**
```python
if age < 7_days:
    skip = True
else:
    skip = False
```

**Option B: 사용자 확인 (Human-in-the-Loop)**
```python
if 5_days < age < 7_days:
    # 프론트엔드에 물어봄
    user_choice = await ask_user("6일 전 데이터인데 사용할까요?")
    skip = user_choice
```

**질문**: 어느 옵션을 선택하시겠습니까?
- [ ] Option A (자동 판단) - Phase 1 권장
- [ ] Option B (사용자 확인) - Phase 3 고려

---

### 4. 기술적 고려사항

#### Q8. 에러 발생 시 fallback 동작은?

**현재 설정**:
```python
try:
    can_skip = check_skip_conditions()
except Exception as e:
    logger.error(f"Skip check failed: {e}")
    can_skip = False  # 🔄 안전하게 SearchTeam 실행
```

**질문**: 이 동작이 적절한가?
- [ ] Yes (에러 시 항상 SearchTeam 실행)
- [ ] No → 다른 동작: _____________

---

#### Q9. 로깅 레벨은?

**현재 설정**:
```python
logger.info("🎯 SearchTeam will be skipped - reusing previous data")
logger.info(f"Skip reason: same_intent_and_entities, age: 2.3 min")
```

**질문**: 로깅이 너무 많지 않은가?
- [ ] 현재 수준 유지 (DEBUG에 도움)
- [ ] WARNING 레벨만 남기기 (운영 환경)
- [ ] 로깅 레벨 설정 가능하게

---

#### Q10. 성능 모니터링을 어떻게 할 것인가?

**측정할 지표**:
1. **Skip 성공률**: skipped / total_queries
2. **평균 응답 시간**: avg(response_time)
3. **False Positive**: 사용자 재질문 패턴 분석

**질문**: 어떻게 측정할 것인가?
- [ ] Option A: 로그만 남기고 나중에 수동 분석
- [ ] Option B: PostgreSQL 별도 테이블에 통계 저장
- [ ] Option C: Prometheus/Grafana 연동
- [ ] Option D: 일단 구현하고 나중에 결정

---

### 5. 우선순위 및 일정

#### Q11. 언제까지 구현할 것인가?

**Phase 1 구현 시간**: 15분 (코드 작성)

**전체 일정**:
```
Day 0 (오늘): 의사결정 + 구현 (15분)
Day 0+10분: 간단 테스트 (3개 시나리오)
Day 1~14: 실사용 데이터 수집
Day 15: 효과 분석 + Phase 2 결정
```

**질문**: 이 일정이 적절한가?
- [ ] Yes, 오늘 바로 구현
- [ ] No, ___ 일 후 구현
- [ ] 일정 조정 필요: _____________

---

#### Q12. Phase 2/3 진행 기준은?

**Phase 2 (유사도 매칭) 진행 조건**:
```
IF (Phase 1 효과 > 15% AND False Positive < 5%)
THEN Phase 2 진행
```

**질문**: 이 기준이 적절한가?
- [ ] Yes
- [ ] No → 다른 기준: _____________

---

## 🎯 빠른 의사결정 템플릿

**바쁘신 분들을 위한 간단 체크**:

### 기본 설정 (권장 ⭐)
- [ ] Checkpointer 작동 확인만 하고 나머지는 기본값 사용
- [ ] MARKET_INQUIRY만 적용
- [ ] 7일 기준
- [ ] 정확 일치만
- [ ] 조용히 처리 (알림 없음)
- [ ] 오늘 바로 구현

→ **이 옵션 선택 시 15분 안에 구현 완료!**

---

## 📋 최종 확인 체크리스트

구현 시작 전 마지막 확인:

### 필수 (하나라도 No면 구현 불가)
- [ ] Checkpointer가 작동 중
- [ ] chat_session_id가 전달됨
- [ ] PostgreSQL 접근 가능

### 선택적 (추천하지만 필수 아님)
- [ ] entities 추출 작동
- [ ] Intent별 신선도 기준 확정
- [ ] 로깅 레벨 결정
- [ ] 사용자 알림 여부 결정

---

## 🚀 구현 GO/NO-GO 결정

**모든 필수 항목 확인 완료?**
- [ ] **GO** → 바로 구현 시작
- [ ] **NO-GO** → 부족한 부분: _____________

---

## 💬 추가 질문 사항

**구현 전 궁금한 점**:
1. _____________________________________________
2. _____________________________________________
3. _____________________________________________

---

**작성**: Claude Code
**다음 단계**: 사용자 답변 후 구현 시작 or 추가 분석
