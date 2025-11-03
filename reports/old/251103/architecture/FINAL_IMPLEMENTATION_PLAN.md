# SearchTeam 건너뛰기 - 최종 구현 계획서

**작성일**: 2025-10-22
**구현 예정 시간**: 30-40분
**사용자 요구사항 반영 완료** ✅

---

## 📋 확정된 요구사항

### ✅ Q1. Checkpointer 정상 작동 확인
- PostgreSQL checkpoints 테이블 사용 중

### ✅ Q2. Entities 확인 방법
**방법 1: 로그 파일 확인**
```bash
# backend/logs/app.log 확인
tail -f backend/logs/app.log | grep "Intent analysis"
```

**방법 2: SQL 쿼리** (사용자 환경)
```bash
# Windows + Git Bash 환경
# 비밀번호: root1234

PGPASSWORD=root1234 psql -U postgres -d real_estate -c "
SELECT
    thread_id,
    checkpoint->'channel_values'->'planning_state'->'analyzed_intent'->>'intent_type' as intent,
    checkpoint->'channel_values'->'planning_state'->'analyzed_intent'->'entities' as entities
FROM checkpoints
ORDER BY (checkpoint->'channel_values'->>'start_time')::timestamp DESC
LIMIT 3;
"
```

---

### ✅ Q3. 신선도 기준 (설정 가능하게)

**구현 방식**: `.env` 파일 또는 config 설정

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # ... 기존 설정 ...

    # 🆕 데이터 재사용 신선도 기준 (초 단위)
    DATA_REUSE_MAX_AGE_MARKET: int = 7 * 24 * 3600      # 7일 (기본값)
    DATA_REUSE_MAX_AGE_LEGAL: int = 30 * 24 * 3600     # 30일 (기본값)
    DATA_REUSE_MAX_AGE_LOAN: int = 1 * 24 * 3600       # 1일 (기본값)

    class Config:
        env_file = ".env"
```

**사용자 설정 변경**:
```bash
# .env 파일
DATA_REUSE_MAX_AGE_MARKET=604800    # 7일 (초)
DATA_REUSE_MAX_AGE_LEGAL=2592000    # 30일 (초)
DATA_REUSE_MAX_AGE_LOAN=86400       # 1일 (초)

# 또는 일 단위로 계산
# 7일 = 7 * 24 * 3600 = 604800초
```

---

### ✅ Q4. 적용 범위: 모든 데이터 + 다른 Agent 정보

**구현 로직**:

```python
# Intent별로 필요한 데이터 타입 매핑
INTENT_DATA_REQUIREMENTS = {
    "market_inquiry": ["real_estate_search"],      # 시세 데이터 필요
    "legal_consult": ["legal_search"],             # 법률 데이터 필요
    "loan_consult": ["loan_search"],               # 대출 데이터 필요
    "risk_analysis": ["real_estate_search"],       # 시세 데이터로 분석
    "contract_review": ["document_review"],        # 문서 검토 결과 필요
    "contract_creation": [],                       # 새로 생성 (재사용 불가)
}

# 체크 로직
async def _check_if_can_skip_search(self, current_intent, chat_session_id):
    # 이전 State 로드
    prev_state = await self.checkpointer.aget(...)

    # 현재 Intent에 필요한 데이터 확인
    required_data = INTENT_DATA_REQUIREMENTS.get(current_intent, [])

    if not required_data:
        return False  # 재사용 불가능한 Intent

    # 이전 SearchTeam 결과 확인
    prev_search = prev_state.values.get("team_results", {}).get("search", {})

    # 필요한 데이터가 모두 있는지 확인
    for data_type in required_data:
        if not prev_search.get(data_type):
            return False  # 필요한 데이터 없음

    # ✅ 필요한 데이터 모두 있음 + 신선함 → 건너뛰기
    return True
```

**예시**:
```
이전 대화: "강남구 아파트 시세" → SearchTeam 실행
  - real_estate_search: [10개 데이터] ✅
  - legal_search: []
  - loan_search: []

현재 대화: "강남구 아파트 위험도는?"
→ Intent: risk_analysis
→ 필요 데이터: real_estate_search
→ 이전 데이터 있음? ✅ Yes
→ 신선함? ✅ Yes (2분 전)
→ SearchTeam 건너뛰기! 🎯
```

---

### ✅ Q5. Entity 매칭: 정확 일치만

**Phase 1 구현**:
```python
# 정확 일치만
if (current_entities.get("region") == prev_entities.get("region") and
    current_entities.get("property_type") == prev_entities.get("property_type")):
    entity_match = True
```

**유사도 매칭은 사용자에게 질문**:
```python
# 유사도가 필요한 경우 감지
if current_entities.get("region") and prev_entities.get("region"):
    similarity = calculate_similarity(current, prev)

    if 0.7 < similarity < 1.0:
        # 🤔 애매한 케이스 → 사용자에게 질문
        logger.info(f"유사한 지역 감지: {prev} vs {current} (유사도: {similarity})")
        # 나중에 프론트엔드에 물어보는 기능 추가 가능
```

**Phase 1에서는**: 정확 일치만 적용, 유사도 로직은 나중에!

---

### ❓ Q6. 알림 방식 - 다시 설명

#### 질문의 의도

**"이전 대화 정보를 재사용했을 때, 사용자에게 어떻게 알릴 것인가?"**

#### 시나리오

```
대화1: "강남구 아파트 시세" (10초 소요)
→ SearchTeam 실행 (느림)

대화2: "강남구 아파트 시세 다시" (5초 소요)
→ SearchTeam 건너뛰기 (빠름!)
```

**사용자 입장**: "왜 이번엔 빠르지?"

#### 옵션

**Option 1: 실시간 알림 (WebSocket)**
```
프론트엔드 화면 (ExecutionProgressPage):

┌─────────────────────────────────────┐
│ 🔄 이전 대화의 정보를 반영하여       │
│    분석 중입니다...                 │
└─────────────────────────────────────┘

[진행 상태]
✅ 검색 (건너뜀 - 이전 데이터 재사용)
⏳ 분석 중...
```

**Option 2: 응답에 포함**
```
AI 답변:

강남구 아파트 평균 시세는 12억입니다.
(상세 분석 내용...)

───────────────────────────
ℹ️ 이전 대화의 정보를 반영하여 분석했습니다.
```

**Option 3: 둘 다**

**Option 4: 알림 없음** (조용히 처리)

#### 질문

**어떤 방식을 원하시나요?**
- [ ] Option 1 (실시간 WebSocket 알림) - 프론트엔드 수정 필요
- [ ] Option 2 (응답 하단에 노트) - 간단, 수정 최소
- [ ] Option 3 (둘 다)
- [ ] Option 4 (알림 없이 조용히)

---

### ❓ Q7. 오래된 데이터 경고 - 다시 설명

#### 질문의 의도

**"오래된 데이터를 사용할 때, 사용자에게 경고할 것인가?"**

#### 시나리오

```
대화1: "강남구 아파트 시세" (5일 전 검색)
→ SearchTeam 실행, 결과 저장

대화2: "강남구 아파트 시세" (오늘)
→ 5일 전 데이터 재사용 가능
→ 하지만 좀 오래됨...
```

**기준**: 7일 이내 OK, 하지만 5일이면...?

#### 옵션

**Option 1: 엄격 (오래된 데이터 아예 안 씀)**
```python
if age > 7_days:
    skip = False  # 무조건 새로 검색
```

**Option 2: 유연 (재사용하되 경고)**
```python
if age > 7_days:
    skip = False  # 너무 오래됨, 새로 검색

elif age > 5_days:  # 5~7일 사이 (경계선)
    skip = True  # 재사용
    # 프론트엔드에 경고 표시
    warning = "⚠️ 5일 전 데이터 기반입니다. 최신 정보가 필요하면 다시 요청해주세요."
```

**프론트엔드 표시 예시**:
```
AI 답변:

강남구 아파트 평균 시세는 12억입니다.

───────────────────────────
⚠️ 5일 전 데이터 기반 분석입니다.
   최신 시세가 필요하시면 "최신 시세"라고 말씀해주세요.
```

**Option 3: 시간 정보만 표시 (판단은 사용자)**
```
AI 답변:

강남구 아파트 평균 시세는 12억입니다.
(5일 전 데이터 기반)
```

#### 질문

**어떤 방식을 원하시나요?**
- [ ] Option 1 (엄격 - 7일 넘으면 무조건 새로 검색)
- [ ] Option 2 (유연 - 재사용하되 경고) - **추천!**
- [ ] Option 3 (시간만 표시)
- [ ] 경고 없음 (조용히 처리)

**경계선 기준**: 최대 기간의 몇 %에서 경고?
- [ ] 70% (예: 7일 기준이면 5일부터 경고)
- [ ] 80% (예: 7일 기준이면 5.6일부터 경고)
- [ ] 기타: ___%

---

## 🔧 구현 계획

### 수정할 파일

#### 1. `backend/app/core/config.py` (10줄 추가)
```python
# 🆕 데이터 재사용 설정
DATA_REUSE_MAX_AGE_MARKET: int = 7 * 24 * 3600
DATA_REUSE_MAX_AGE_LEGAL: int = 30 * 24 * 3600
DATA_REUSE_MAX_AGE_LOAN: int = 1 * 24 * 3600
DATA_REUSE_WARNING_THRESHOLD: float = 0.7  # 70%에서 경고
```

#### 2. `backend/app/service_agent/supervisor/team_supervisor.py` (80줄 추가)

##### 2-1. Intent별 데이터 요구사항 정의 (20줄)
```python
# 클래스 레벨 상수
INTENT_DATA_REQUIREMENTS = {
    "market_inquiry": ["real_estate_search"],
    "legal_consult": ["legal_search"],
    "loan_consult": ["loan_search"],
    "risk_analysis": ["real_estate_search"],
    "contract_review": ["document_review"],
    # ... 더 추가
}
```

##### 2-2. `_check_if_can_skip_search()` 메서드 (60줄)
```python
async def _check_if_can_skip_search(
    self,
    current_intent: str,
    current_entities: Dict,
    chat_session_id: str
) -> Tuple[bool, Optional[str]]:
    """
    SearchTeam 건너뛰기 가능 여부 체크

    Returns:
        (can_skip, warning_message)
    """

    if not self.checkpointer or not chat_session_id:
        return (False, None)

    try:
        # 이전 State 로드
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if not prev_state or not prev_state.values:
            return (False, None)

        # 1️⃣ Intent별 필요 데이터 확인
        required_data_types = INTENT_DATA_REQUIREMENTS.get(current_intent, [])
        if not required_data_types:
            return (False, None)  # 재사용 불가능한 Intent

        # 2️⃣ 이전 SearchTeam 결과 확인
        prev_search = prev_state.values.get("team_results", {}).get("search", {})
        for data_type in required_data_types:
            if not prev_search.get(data_type):
                logger.info(f"Cannot skip - missing data: {data_type}")
                return (False, None)

        # 3️⃣ Entity 비교 (정확 일치)
        prev_planning = prev_state.values.get("planning_state", {})
        prev_intent_data = prev_planning.get("analyzed_intent", {})
        prev_entities = prev_intent_data.get("entities", {})

        # region 비교
        if current_entities.get("region") != prev_entities.get("region"):
            logger.info(f"Cannot skip - region mismatch")
            return (False, None)

        # property_type 비교
        if current_entities.get("property_type") != prev_entities.get("property_type"):
            logger.info(f"Cannot skip - property_type mismatch")
            return (False, None)

        # 4️⃣ 신선도 체크 (설정 가능)
        from app.core.config import settings

        max_age_map = {
            "market_inquiry": settings.DATA_REUSE_MAX_AGE_MARKET,
            "legal_consult": settings.DATA_REUSE_MAX_AGE_LEGAL,
            "loan_consult": settings.DATA_REUSE_MAX_AGE_LOAN,
        }
        max_age = max_age_map.get(current_intent, settings.DATA_REUSE_MAX_AGE_MARKET)

        prev_time = prev_state.values.get("end_time")
        if not prev_time:
            return (False, None)

        age_seconds = (datetime.now() - prev_time).total_seconds()

        if age_seconds > max_age:
            logger.info(f"Cannot skip - data too old: {age_seconds/3600:.1f}h")
            return (False, None)

        # 5️⃣ 경고 체크 (옵션 - Q7 답변에 따라)
        warning_threshold = getattr(settings, 'DATA_REUSE_WARNING_THRESHOLD', 0.7)
        warning_message = None

        if age_seconds > max_age * warning_threshold:
            days = age_seconds / 86400
            warning_message = f"{days:.1f}일 전 데이터 기반입니다"

        # ✅ 모든 조건 통과!
        logger.info(f"🎯 SearchTeam can be skipped (age: {age_seconds/3600:.1f}h)")
        return (True, warning_message)

    except Exception as e:
        logger.error(f"Skip check error: {e}")
        return (False, None)  # 🔄 에러 시 안전하게 SearchTeam 실행
```

##### 2-3. `planning_node()` 수정 (15줄)
```python
# Intent 분석 후
intent_result = await self.planning_agent.analyze_intent(query, context)

# 🆕 건너뛰기 체크
can_skip, warning = await self._check_if_can_skip_search(
    current_intent=intent_result.intent_type.value,
    current_entities=intent_result.entities or {},
    chat_session_id=chat_session_id
)

state["search_skipped"] = can_skip
state["data_age_warning"] = warning  # Q7 옵션에 따라 사용

if can_skip:
    logger.info("🎯 SearchTeam will be skipped - reusing previous data")
```

##### 2-4. `active_teams` 필터링 (5줄)
```python
# 기존 코드
for step in sorted_steps:
    team = step.get("team")

    # 🆕 SearchTeam 건너뛰기
    if team == "search" and state.get("search_skipped"):
        logger.info("🎯 Skipping SearchTeam from active_teams")
        continue

    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)
```

---

### 총 코드량

| 파일 | 추가 코드 |
|------|----------|
| `config.py` | 10줄 |
| `team_supervisor.py` | 100줄 (상수 20 + 메서드 60 + 호출 15 + 필터 5) |
| **총계** | **110줄** |

---

## 🧪 테스트 계획

### 1. Entities 확인

**Git Bash에서 SQL 실행**:
```bash
PGPASSWORD=root1234 psql -U postgres -d real_estate -c "
SELECT
    checkpoint->'channel_values'->'planning_state'->'analyzed_intent'->'entities'
FROM checkpoints
LIMIT 1;
"
```

**예상 결과**:
```json
{"region": "강남구", "property_type": "아파트"}
```

만약 **null** 또는 **비어있으면**:
→ Intent 분석 프롬프트 수정 필요 (10줄 추가)

---

### 2. 건너뛰기 테스트 (3개 시나리오)

#### Case 1: 같은 질문 반복
```
대화1: "강남구 아파트 시세"
→ SearchTeam 실행 ✅
→ 로그: [SearchTeam] Starting...

대화2: "강남구 아파트 시세 다시"
→ SearchTeam 건너뛰기 ✅
→ 로그: 🎯 SearchTeam will be skipped
→ 로그: Active teams: ['analysis']
```

#### Case 2: 다른 지역
```
대화1: "강남구 아파트"
대화2: "서초구 아파트"
→ SearchTeam 실행 ✅
→ 로그: Cannot skip - region mismatch
```

#### Case 3: 다른 Intent, 같은 데이터
```
대화1: "강남구 아파트 시세" (MARKET_INQUIRY)
→ real_estate_search 데이터 저장

대화2: "강남구 아파트 위험도" (RISK_ANALYSIS)
→ 필요 데이터: real_estate_search ✅
→ SearchTeam 건너뛰기 ✅
→ 로그: 🎯 Different intent but data available
```

---

## ⏱️ 구현 일정

**총 예상 시간**: 30-40분

| 단계 | 작업 | 시간 |
|------|------|------|
| 1 | Entities 확인 (SQL 실행) | 5분 |
| 2 | config.py 수정 | 3분 |
| 3 | team_supervisor.py 수정 | 20분 |
| 4 | 테스트 (3개 시나리오) | 10분 |
| **총계** | | **38분** |

---

## 📋 최종 확인사항

### 구현 전 마지막 질문 (Q6, Q7)

**Q6. 알림 방식** (위 설명 참고):
- [ ] Option 1 (실시간 WebSocket)
- [ ] Option 2 (응답에 포함) - **추천**
- [ ] Option 3 (둘 다)
- [ ] Option 4 (알림 없음)

**Q7. 오래된 데이터 경고** (위 설명 참고):
- [ ] Option 1 (엄격)
- [ ] Option 2 (재사용+경고) - **추천**
- [ ] Option 3 (시간만 표시)
- [ ] 경고 없음

**경계선**: ___% (추천 70%)

---

## 🚀 구현 시작 조건

**모든 질문 답변 완료 시**:
- [ ] Entities SQL 확인 (5분)
- [ ] Q6 답변
- [ ] Q7 답변

→ **GO! 바로 구현 시작!**

---

**작성**: Claude Code
**상태**: Q6, Q7 답변 대기 중
**예상 소요 시간**: 답변 후 30-40분
