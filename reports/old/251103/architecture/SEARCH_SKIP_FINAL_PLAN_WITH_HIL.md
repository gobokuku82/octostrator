# SearchTeam 건너뛰기 최종 구현 계획서 (Human-in-the-Loop 준비)

**작성일**: 2025-10-22
**버전**: Final v1.0
**구현 예정 시간**: 40-50분
**Human-in-the-Loop 준비**: 고려됨 ✅

---

## 🎯 확정된 요구사항

### ✅ 사용자 선택 사항

| 질문 | 선택 | 비고 |
|------|------|------|
| **Q1** | Checkpointer 작동 확인 | ✅ 확인됨 |
| **Q2** | Entities 확인 방법 | 로그 + SQL (Git Bash) |  |
| **Q3** | 신선도 기준 | 권장대로 (7일/30일/1일), **설정 가능** | `.env` 파일 |
| **Q4** | 적용 범위 | **모든 Intent + 다른 Agent 데이터** | SearchTeam, DocumentTeam 등 |
| **Q5** | Entity 매칭 | **정확 일치만** | 유사도는 Phase 2 |
| **Q6** | 알림 방식 | **Option 1: 실시간 WebSocket** | Todo Management 준비 |
| **Q7** | 오래된 데이터 | **Option 2: 유연 + 경고 (70%)** | |

---

## 🚀 구현 계획

### Phase 1: Backend Core (30분)

#### 1.1 설정 추가 (5분)

**파일**: `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # 🆕 데이터 재사용 신선도 기준 (초 단위)
    DATA_REUSE_MAX_AGE_MARKET: int = Field(
        default=7 * 24 * 3600,
        description="시세 데이터 최대 유효기간 (초)"
    )
    DATA_REUSE_MAX_AGE_LEGAL: int = Field(
        default=30 * 24 * 3600,
        description="법률 데이터 최대 유효기간 (초)"
    )
    DATA_REUSE_MAX_AGE_LOAN: int = Field(
        default=1 * 24 * 3600,
        description="대출 데이터 최대 유효기간 (초)"
    )
    DATA_REUSE_WARNING_THRESHOLD: float = Field(
        default=0.7,
        description="경고 표시 임계값 (70% 지점)"
    )

    class Config:
        env_file = ".env"
```

**사용자 설정 변경 가능** (`.env` 파일):
```bash
# 시세 데이터 유효기간 (기본 7일)
DATA_REUSE_MAX_AGE_MARKET=604800

# 법률 데이터 유효기간 (기본 30일)
DATA_REUSE_MAX_AGE_LEGAL=2592000

# 대출 데이터 유효기간 (기본 1일)
DATA_REUSE_MAX_AGE_LOAN=86400

# 경고 임계값 (기본 70%)
DATA_REUSE_WARNING_THRESHOLD=0.7
```

---

#### 1.2 Intent별 데이터 요구사항 정의 (10분)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**클래스 레벨 상수 추가** (Line 40 근처):

```python
# Intent별 필요 데이터 매핑
# Q4 요구사항: 모든 Intent + 다른 Agent 데이터 확인
INTENT_DATA_REQUIREMENTS = {
    # SearchTeam 데이터
    "market_inquiry": {
        "team": "search",
        "data_types": ["real_estate_search"],
        "entities_required": ["region", "property_type"]
    },
    "legal_consult": {
        "team": "search",
        "data_types": ["legal_search"],
        "entities_required": []  # 법률은 지역 무관
    },
    "loan_consult": {
        "team": "search",
        "data_types": ["loan_search"],
        "entities_required": []  # 대출은 금액만
    },
    "risk_analysis": {
        "team": "search",
        "data_types": ["real_estate_search"],  # 시세 데이터로 분석
        "entities_required": ["region"]
    },

    # DocumentTeam 데이터
    "contract_review": {
        "team": "document",
        "data_types": ["review_result"],
        "entities_required": []
    },

    # AnalysisTeam 데이터
    "comprehensive": {
        "team": "analysis",
        "data_types": ["analysis_result"],
        "entities_required": []
    },

    # 재사용 불가 Intent
    "contract_creation": {
        "team": None,  # 항상 새로 생성
        "data_types": [],
        "entities_required": []
    },
    "irrelevant": {
        "team": None,
        "data_types": [],
        "entities_required": []
    },
    "unclear": {
        "team": None,
        "data_types": [],
        "entities_required": []
    },
}
```

---

#### 1.3 `_check_if_can_skip_team()` 메서드 (15분)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치**: Line 174 근처 (initialize_node 이후)

```python
async def _check_if_can_skip_team(
    self,
    current_intent: str,
    current_entities: Dict[str, Any],
    chat_session_id: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    팀 실행 건너뛰기 가능 여부 체크 (SearchTeam, DocumentTeam 등)

    Args:
        current_intent: 현재 Intent Type
        current_entities: 현재 추출된 Entities
        chat_session_id: 채팅 세션 ID

    Returns:
        (can_skip, warning_message, skip_team_name)
        - can_skip: 건너뛰기 가능 여부
        - warning_message: 경고 메시지 (오래된 데이터)
        - skip_team_name: 건너뛸 팀 이름 ("search", "document", etc.)

    Example:
        >>> can_skip, warning, team = await self._check_if_can_skip_team(
        ...     "market_inquiry",
        ...     {"region": "강남구"},
        ...     "session-123"
        ... )
        >>> if can_skip:
        ...     logger.info(f"Skipping {team} team")
    """

    # Checkpointer 확인
    if not self.checkpointer or not chat_session_id:
        return (False, None, None)

    # Intent 데이터 요구사항 확인
    requirements = INTENT_DATA_REQUIREMENTS.get(current_intent)
    if not requirements or not requirements.get("team"):
        # 재사용 불가능한 Intent (contract_creation 등)
        return (False, None, None)

    target_team = requirements["team"]
    required_data_types = requirements["data_types"]
    required_entities = requirements.get("entities_required", [])

    try:
        # 1️⃣ 이전 State 로드
        prev_state = await self.checkpointer.aget(
            {"configurable": {"thread_id": chat_session_id}}
        )

        if not prev_state or not prev_state.values:
            return (False, None, None)

        # 2️⃣ 이전 팀 결과 확인
        prev_team_results = prev_state.values.get("team_results", {})
        prev_team_data = prev_team_results.get(target_team, {})

        # 필요한 데이터 타입이 모두 있는지 확인
        for data_type in required_data_types:
            if not prev_team_data.get(data_type):
                logger.info(f"Cannot skip - missing data: {data_type}")
                return (False, None, None)

        # 3️⃣ Entity 비교 (정확 일치만 - Q5)
        if required_entities:
            prev_planning = prev_state.values.get("planning_state", {})
            prev_intent_data = prev_planning.get("analyzed_intent", {})
            prev_entities = prev_intent_data.get("entities", {})

            for entity_key in required_entities:
                curr_value = current_entities.get(entity_key)
                prev_value = prev_entities.get(entity_key)

                if curr_value != prev_value:
                    logger.info(f"Cannot skip - entity mismatch: {entity_key}")
                    return (False, None, None)

        # 4️⃣ 신선도 체크 (Q3 - 설정 가능)
        from app.core.config import settings

        # Intent별 최대 유효기간
        max_age_map = {
            "market_inquiry": settings.DATA_REUSE_MAX_AGE_MARKET,
            "legal_consult": settings.DATA_REUSE_MAX_AGE_LEGAL,
            "loan_consult": settings.DATA_REUSE_MAX_AGE_LOAN,
            "risk_analysis": settings.DATA_REUSE_MAX_AGE_MARKET,  # 시세 기준
        }
        max_age = max_age_map.get(current_intent, settings.DATA_REUSE_MAX_AGE_MARKET)

        prev_time = prev_state.values.get("end_time")
        if not prev_time:
            return (False, None, None)

        age_seconds = (datetime.now() - prev_time).total_seconds()

        # 너무 오래됨
        if age_seconds > max_age:
            logger.info(f"Cannot skip - data too old: {age_seconds/3600:.1f}h (max: {max_age/3600:.1f}h)")
            return (False, None, None)

        # 5️⃣ 경고 메시지 생성 (Q7 - 유연 + 경고)
        warning_threshold = settings.DATA_REUSE_WARNING_THRESHOLD
        warning_message = None

        if age_seconds > max_age * warning_threshold:
            days = age_seconds / 86400
            warning_message = f"{days:.1f}일 전 데이터 기반 분석입니다"
            logger.info(f"⚠️ Old data warning: {warning_message}")

        # ✅ 모든 조건 통과!
        logger.info(f"🎯 {target_team.capitalize()}Team can be skipped (age: {age_seconds/3600:.1f}h)")
        return (True, warning_message, target_team)

    except Exception as e:
        logger.error(f"Skip check error: {e}")
        return (False, None, None)  # 🔄 에러 시 안전하게 실행
```

---

#### 1.4 `planning_node()` 수정 (10분)

**위치**: Line 308 근처 (Intent 분석 직후)

```python
# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)

# 🆕 팀 건너뛰기 체크 (Q4: 모든 Intent)
can_skip, data_age_warning, skip_team_name = await self._check_if_can_skip_team(
    current_intent=intent_result.intent_type.value,
    current_entities=intent_result.entities or {},
    chat_session_id=chat_session_id
)

# State 저장
state["team_skip_requested"] = can_skip
state["skip_team_name"] = skip_team_name  # "search", "document", etc.
state["data_age_warning"] = data_age_warning

# 🆕 Q6: 실시간 WebSocket 알림 (Todo Management 준비)
if can_skip and skip_team_name:
    logger.info(f"🎯 {skip_team_name.capitalize()}Team will be skipped - reusing previous data")

    # WebSocket 메시지 전송
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id) if session_id else None

    if progress_callback:
        try:
            await progress_callback("team_skip_notification", {
                "message": "이전 대화의 정보를 반영하여 분석 중입니다",
                "skipped_team": skip_team_name,
                "data_age": f"{(datetime.now() - prev_time).total_seconds() / 60:.1f}분 전",
                "warning": data_age_warning
            })
            logger.info(f"[TeamSupervisor] Sent team_skip_notification via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send skip notification: {e}")
```

**주요 변경점**:
- `search_skipped` → `team_skip_requested` (더 일반적)
- `skip_team_name` 추가 (어떤 팀을 건너뛸지 명시)
- **WebSocket 실시간 알림** 추가 (Q6)

---

#### 1.5 `active_teams` 필터링 수정 (5분)

**위치**: Line 497 근처

```python
# 활성화할 팀 결정 (priority 순서 보장)
active_teams = []
seen_teams = set()
skip_team_name = state.get("skip_team_name")  # 🆕

# ✅ priority 순으로 정렬
sorted_steps = sorted(
    planning_state["execution_steps"],
    key=lambda x: x.get("priority", 999)
)

for step in sorted_steps:
    team = step.get("team")

    # 🆕 팀 건너뛰기 체크 (SearchTeam, DocumentTeam 등)
    if team == skip_team_name and state.get("team_skip_requested", False):
        logger.info(f"🎯 Skipping {team.capitalize()}Team from active_teams - reusing previous data")
        continue

    if team and team not in seen_teams:
        active_teams.append(team)
        seen_teams.add(team)
```

---

### Phase 2: WebSocket 프로토콜 확장 (10분)

#### 2.1 WebSocket 메시지 타입 추가

**문서**: `backend/app/api/chat_api.py` (docstring)

**추가할 메시지 타입**:
```python
"""
Server → Client:
    ...
    - {"type": "team_skip_notification", "message": "...", "skipped_team": "search", "data_age": "2분 전", "warning": "5일 전 데이터"}  # 🆕 Q6
    ...
"""
```

**프론트엔드에서 수신 처리**:
```typescript
// frontend/components/chat-interface.tsx

ws.onmessage = (event) => {
  const message = JSON.parse(event.data)

  if (message.type === 'team_skip_notification') {
    // 🆕 Todo Management UI에 표시 준비
    console.log('🔄 팀 건너뛰기:', message.message)
    console.log('⚠️ 경고:', message.warning)

    // 나중에 Todo UI에 표시
    // setSkipNotification(message)
  }
}
```

---

### Phase 3: 응답 생성 시 경고 포함 (5분)

#### 3.1 `generate_response_node()` 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치**: Line 914 근처

```python
async def generate_response_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """응답 생성 노드"""
    logger.info("[TeamSupervisor] === Generating response ===")

    state["current_phase"] = "response_generation"

    # ... 기존 응답 생성 코드 ...

    # 🆕 Q7: 오래된 데이터 경고 포함
    data_age_warning = state.get("data_age_warning")
    if data_age_warning:
        response["warnings"] = [data_age_warning]
        logger.info(f"⚠️ Added data age warning to response: {data_age_warning}")

    state["final_response"] = response
    state["status"] = "completed"

    # ... 기존 코드 ...

    return state
```

---

## 🧪 테스트 계획

### 1. Entities 확인 (5분)

**Git Bash에서 SQL 실행**:
```bash
PGPASSWORD=root1234 psql -U postgres -d real_estate -c "
SELECT
    checkpoint->'channel_values'->'planning_state'->'analyzed_intent'->'entities' as entities
FROM checkpoints
ORDER BY (checkpoint->'channel_values'->>'start_time')::timestamp DESC
LIMIT 1;
"
```

**예상 결과**:
```json
{"region": "강남구", "property_type": "아파트"}
```

**만약 null이면**: Intent 분석 프롬프트 수정 필요!

---

### 2. 건너뛰기 테스트 (10분)

#### Case 1: 같은 질문 반복
```
대화1: "강남구 아파트 시세"
→ SearchTeam 실행 ✅
→ 로그: [SearchTeam] Starting...

대화2: "강남구 아파트 시세 다시"
→ SearchTeam 건너뛰기 ✅
→ 로그: 🎯 SearchTeam can be skipped (age: 2.3h)
→ 로그: Active teams: ['analysis']
→ WebSocket: {"type": "team_skip_notification", "message": "이전 대화의 정보를 반영하여 분석 중입니다"}
```

#### Case 2: 다른 Intent, 같은 데이터
```
대화1: "강남구 아파트 시세" (MARKET_INQUIRY)
→ real_estate_search 저장

대화2: "강남구 아파트 위험도" (RISK_ANALYSIS)
→ 필요 데이터: real_estate_search ✅
→ SearchTeam 건너뛰기 ✅
→ 로그: 🎯 Different intent but same data available
```

#### Case 3: 오래된 데이터 경고
```
대화1: "강남구 아파트 시세" (5일 전)
대화2: "강남구 아파트 시세" (오늘)
→ SearchTeam 건너뛰기 ✅ (7일 이내)
→ 경고: "5.2일 전 데이터 기반 분석입니다"
→ WebSocket: {"type": "team_skip_notification", "warning": "5.2일 전 데이터..."}
```

---

## 🎯 지금 구현 vs 나중 구현 (명확한 구분)

### ✅ 지금 구현 (HITL 없이 작동)

**핵심 동작**: 조건만 맞으면 **자동으로 팀 건너뛰기**, 사용자에게 **알림만 전송**

**구현 내용**:
1. **자동 skip 판단** (조건: 데이터 존재 + Entity 일치 + 신선도 OK)
2. **WebSocket 알림** (사용자에게 "이전 대화 정보 사용 중" 표시)
3. **경고 메시지** (70% 지점 이상이면 "N일 전 데이터" 경고)

**사용자 개입**: ❌ **없음** (자동으로 진행)

```python
# 지금 구현할 코드
async def _check_if_can_skip_team(...):
    # 1️⃣ 데이터 확인
    # 2️⃣ Entity 비교
    # 3️⃣ 신선도 체크

    # ✅ 조건 만족 → 자동 skip
    if all_conditions_met:
        # WebSocket 알림만 전송 (확인 요청 X)
        await progress_callback("team_skip_notification", {
            "message": "이전 대화의 정보를 반영하여 분석 중입니다",
            "warning": "5일 전 데이터" if old else None
        })

        return (True, warning, team_name)  # 자동 skip

    # ❌ 조건 불만족 → 새로 검색
    return (False, None, None)
```

**동작 예시**:
```
사용자: "강남구 아파트 시세"
→ SearchTeam 실행 ✅

사용자: "강남구 아파트 다시 알려줘"
→ [자동] SearchTeam skip ✅
→ [알림] "이전 대화의 정보를 반영하여 분석 중입니다"
→ [경고] "2.3시간 전 데이터 기반 분석입니다" (70% 넘으면)
→ 사용자는 그냥 결과 받음 (선택권 없음)
```

---

### 🔮 나중 구현 (HITL 기능 추가 시)

**핵심 동작**: 애매한 경우 **사용자에게 확인 요청**, 사용자가 **선택**

**추가 내용**:
1. **사용자 확인 요청** (오래된 데이터인 경우)
2. **사용자 선택** ("사용" or "새로 검색")
3. **Interrupt 처리** (LangGraph `interrupt()` 사용)

**사용자 개입**: ✅ **있음** (선택해야 진행)

```python
# 🔮 HITL 구현 시 추가할 코드 (Phase 4)

async def _check_if_can_skip_team(...):
    # ... 기존 로직 ...

    # 🆕 HITL: 오래된 데이터는 사용자에게 물어봄
    if age_seconds > max_age * warning_threshold:
        from langgraph.types import interrupt

        # ⏸️ 그래프 일시 중단, 사용자 확인 요청
        user_choice = interrupt({
            "type": "data_reuse_confirmation",
            "message": f"{days:.1f}일 전 데이터를 사용할까요?",
            "options": ["사용", "새로 검색"],
            "data_age": f"{days:.1f}일"
        })

        # 사용자 선택에 따라 처리
        if user_choice == "새로 검색":
            return (False, None, None)  # skip 안 함

        # "사용" 선택 시 계속

    return (True, warning, team_name)
```

**프론트엔드 모달** (Todo Management UI 통합):
```typescript
// 🔮 HITL 구현 시 추가할 프론트엔드 코드

if (message.type === 'interrupt') {
  // 사용자 확인 모달 표시
  showModal({
    title: "데이터 재사용 확인",
    message: "5.2일 전 데이터를 사용할까요?",
    buttons: [
      {text: "사용", value: "사용"},
      {text: "새로 검색", value: "새로 검색"}
    ],
    onConfirm: (choice) => {
      ws.send({type: "interrupt_response", choice})
    }
  })
}
```

**동작 예시**:
```
사용자: "강남구 아파트 시세" (5일 전)
→ SearchTeam 실행 ✅

사용자: "강남구 아파트 다시 알려줘" (오늘)
→ [체크] 5일 전 데이터 발견 (70% 넘음)
→ [모달] "5일 전 데이터를 사용할까요?"
   ┌─────────────────────┐
   │ 사용  │  새로 검색   │
   └─────────────────────┘
→ 사용자 선택에 따라 진행
```

---

### 📊 비교표

| 항목 | 지금 구현 (Phase 1) | HITL 구현 (Phase 4) |
|------|---------------------|---------------------|
| **사용자 확인** | ❌ 없음 (자동) | ✅ 있음 (선택) |
| **WebSocket** | 알림만 | 알림 + Interrupt |
| **오래된 데이터** | 자동 사용 + 경고 | 사용자 선택 |
| **LangGraph** | 일반 실행 | `interrupt()` 사용 |
| **프론트엔드** | 알림 표시만 | 모달 + 버튼 |
| **구현 난이도** | 쉬움 (45분) | 중간 (3-4시간) |
| **필요 기능** | 없음 | HITL 전체 구조 필요 |

---

### 🚨 핵심 정리

**지금 구현 (45분)**:
- ✅ 자동 skip 판단
- ✅ WebSocket 알림
- ✅ 경고 메시지
- ❌ **사용자 확인 요청 없음** (자동 진행)

**HITL 구현 시 추가 (나중)**:
- ✅ 사용자 확인 요청 (모달)
- ✅ `interrupt()` 사용
- ✅ 사용자 선택 처리
- ⚠️ **HITL 전체 구조 필요**

**결론**:
- 지금 구현해도 **완전히 작동** ✅
- HITL은 **선택적 업그레이드** (필수 아님)
- WebSocket 구조 덕분에 **나중에 쉽게 추가** 가능

---

## 📊 구현 체크리스트

### Backend Core (30분)
- [ ] config.py: 신선도 설정 추가 (5분)
- [ ] team_supervisor.py: INTENT_DATA_REQUIREMENTS 정의 (10분)
- [ ] team_supervisor.py: _check_if_can_skip_team() 추가 (15분)
- [ ] planning_node(): 호출 로직 + WebSocket 알림 (10분)
- [ ] active_teams 필터링 (5분)

### WebSocket (10분)
- [ ] 메시지 타입 문서화 (5분)
- [ ] 프론트엔드 수신 처리 준비 (5분)

### Response (5분)
- [ ] generate_response_node(): 경고 메시지 포함 (5분)

### 테스트 (10분)
- [ ] Entities SQL 확인 (5분)
- [ ] 건너뛰기 테스트 3개 시나리오 (10분)

**총 예상 시간**: **45분**

---

## 🔮 향후 확장 계획

### Phase 2 (2주 후)
- Entity 유사도 매칭 ("강남" = "강남구")
- 금액 범위 허용 (±20%)

### Phase 3 (HIL 구현 시)
- 오래된 데이터 사용자 확인
- Todo Management UI와 통합
- Rollback 기능과 통합

### Phase 4 (고급 기능)
- 여러 Checkpoint 병합
- 스마트 캐싱 (Redis)
- LLM 기반 재사용 판단

---

## 📚 관련 문서

- **Human-in-the-Loop 구현**: `../todo_management/IMPLEMENTATION_GAP_ANALYSIS_251022.md`
- **Checkpointer 가이드**: `../human_in_the_loop/CHECKPOINTER_COMPLETE_GUIDE.md`
- **System Flow**: `../Manual/SYSTEM_FLOW_DIAGRAM.md`

---

## 🚀 구현 시작

**Q6, Q7 답변 반영 완료!**

**확인 사항**:
- [x] Q6: WebSocket 실시간 알림 (Todo Management 준비)
- [x] Q7: 유연 + 경고 (70% 경계선)
- [x] Human-in-the-Loop 확장 준비

**다음 단계**:
1. Entities SQL 확인 (5분)
2. 코드 구현 (40분)
3. 테스트 (10분)

**총 55분 예상**

---

**작성**: Claude Code
**상태**: 최종 승인 대기
**Human-in-the-Loop 준비**: ✅ 완료
