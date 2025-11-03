# 🔍 근본 원인 분석: session_id 누락의 진실

**작성일**: 2025-10-20
**질문**: "이것도 문제의 시작이었는데, 자꾸 계획서를 수정하면서 누락이 된건가, 시작부터 누락되어서 잘못 계획한건가?"

---

## 📊 결론부터 (TL;DR)

**답변**: **시작부터 잘못 계획되었습니다!**

`session_id` 파라미터 누락은:
- ❌ 계획서 수정 중 누락된 것이 **아님**
- ✅ **원본 계획서(251019)부터 이미 잘못 설계됨**
- ✅ `team_supervisor.py`의 실제 호출 코드를 **정확히 분석하지 않았음**

---

## 🔎 증거 1: 원본 계획서 (251019) 분석

### plan_of_memory_service_error_fix_251019.md

**Line 44-50** (2.1 코드 불일치 섹션):

```python
# team_supervisor.py가 호출하는 메서드:
# planning_node (line 211-214)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
)
# ❌ 이미 여기서 session_id 누락!
```

**Line 53-62** (generate_response_node 호출):

```python
# generate_response_node (line 855)
await memory_service.save_conversation(
    user_id=user_id,
    query=state.get("query", ""),
    response_summary=response_summary,
    relevance="RELEVANT",
    session_id=chat_session_id,  # ✅ 여기는 있음
    intent_detected=intent_type,
    entities_mentioned=analyzed_intent.get("entities", {}),
    conversation_metadata={...}
)
```

### 문제점

**원본 계획서에서 이미**:
1. `load_recent_memories`에는 `session_id` 파라미터가 **없음**
2. `save_conversation`에는 `session_id` 파라미터가 **있음**
3. **두 메서드의 시그니처 불일치**를 인지하지 못함

---

## 🔎 증거 2: 실제 team_supervisor.py 코드

### 실제 코드 (Line 211-214):

```python
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
    # ❌ session_id 없음!
)
```

### 왜 누락되었나?

**추정 시나리오**:

1. **과거 어느 시점**:
   - 누군가 `team_supervisor.py`를 작성할 때
   - `load_recent_memories`는 "사용자 기반"으로만 생각
   - "현재 세션 제외" 로직을 고려하지 않음

2. **설계 불일치**:
   - `save_conversation`: 세션별 저장 → `session_id` 필수
   - `load_recent_memories`: 사용자별 로드 → `session_id` 선택적
   - **두 메서드의 책임이 다르다고 가정**

3. **문제 발견 시점**:
   - 원본 계획서(251019) 작성 시 이미 존재
   - 하지만 **문제로 인식하지 못함**

---

## 🔎 증거 3: 계획서 변화 추적

### 원본 (251019) → REVISED (251020) 변화

**plan_of_memory_service_error_fix_251019.md**:
```python
# Line 296-310 (Step 1: 긴급 패치)
async def load_recent_memories(
    self,
    user_id: str,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
) -> List[Dict[str, Any]]:
    """빈 리스트 반환"""
    return []
```
**→ session_id 파라미터 없음!**

**plan_of_memory_service_error_fix_251020_REVISED.md**:
```python
# Line 212-231 (Phase 1 구현)
async def load_recent_memories(
    self,
    user_id: int,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
) -> List[Dict[str, Any]]:
    # ... 구현
```
**→ REVISED에서도 session_id 파라미터 없음!**

### 결론

**계획서 수정 중 누락이 아니라**:
- ✅ 원본(251019)부터 잘못된 설계
- ✅ REVISED(251020)에서도 그대로 복사
- ✅ **오늘 사용자님이 지적하기 전까지 발견 못함**

---

## 🔎 증거 4: FINAL_IMPLEMENTATION_GUIDE도 동일

### FINAL_IMPLEMENTATION_GUIDE_251020.md

**Line 443-448**:

```python
async def load_recent_memories(
    self,
    user_id: int,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
) -> List[Dict[str, Any]]:
```

**→ session_id 파라미터 없음!**

### 왜 발견 못했나?

**분석 방법의 한계**:

1. **team_supervisor.py의 호출 코드만 봄**:
   ```python
   # Line 211
   loaded_memories = await memory_service.load_recent_memories(...)
   ```
   - 여기서 `session_id`가 없다는 걸 **"정상"**이라고 가정
   - "원래 이렇게 호출하는구나"라고 생각

2. **실행 흐름 분석 부족**:
   - planning_node → load (현재 대화 진행 중)
   - generate_response_node → save (현재 대화 완료 후)
   - **두 타이밍의 차이를 고려 안 함**

3. **"현재 세션 제외" 로직 필요성 간과**:
   - 세션 A에서 대화 중
   - 메모리 로드 시 세션 A는 아직 불완전
   - **세션 A를 제외해야 한다는 것을 생각 못함**

---

## 🧩 왜 이런 설계 오류가 발생했나?

### 근본 원인 (Root Cause)

#### 1. 불완전한 요구사항 분석

**잘못된 가정**:
```
load_recent_memories = 사용자의 과거 대화만 로드
→ user_id만 있으면 충분
```

**올바른 요구사항**:
```
load_recent_memories = 사용자의 과거 **완료된** 대화만 로드
→ 현재 진행 중인 세션은 제외
→ session_id 필요!
```

#### 2. 실행 타이밍 미고려

**실제 흐름**:
```
1. planning_node (대화 시작)
   ├─ load_recent_memories 호출
   ├─ 현재 세션은 막 시작, session_metadata 비어있음
   └─ 과거 세션만 로드해야 함 ← session_id 필요!

2. generate_response_node (대화 완료)
   ├─ save_conversation 호출
   └─ 현재 세션에 저장 ← session_id 필요!
```

#### 3. 코드 리뷰 부족

**원본 team_supervisor.py 작성 시**:
- `load_recent_memories`에 `session_id` 전달 안 함
- 이후 아무도 문제 발견 못함
- 계획서 작성 시에도 그대로 복사

---

## 🎯 교훈 (Lessons Learned)

### 1. 실행 흐름 분석 필수

**Before (잘못된 방식)**:
```
메서드 시그니처만 보고 설계
→ load_recent_memories(user_id, limit) ← 충분해 보임
```

**After (올바른 방식)**:
```
실행 타이밍 고려
→ planning_node에서 호출 시 현재 세션은 불완전
→ 현재 세션 제외 로직 필요
→ session_id 파라미터 필수!
```

### 2. 대칭성 확인

**대칭적 설계**:
```python
# 둘 다 session_id 필요!
save_conversation(..., session_id)  # 저장 시 세션 지정
load_recent_memories(..., session_id)  # 로드 시 현재 세션 제외
```

### 3. 엣지 케이스 고려

**엣지 케이스**:
- 세션 A에서 대화 중
- 세션 A의 session_metadata는 아직 불완전
- 로드하면 빈 데이터 또는 중복 데이터

**해결**:
- `session_id` 파라미터로 현재 세션 명시적 제외

---

## 📋 수정 이력

### Timeline

1. **2025-10-16 이전**:
   - `team_supervisor.py` 작성
   - `load_recent_memories` 호출 시 `session_id` 누락

2. **2025-10-19**:
   - `plan_of_memory_service_error_fix_251019.md` 작성
   - **session_id 누락 문제 발견 못함**

3. **2025-10-20 (오전)**:
   - `plan_of_memory_service_error_fix_251020_REVISED.md` 작성
   - **여전히 session_id 누락**

4. **2025-10-20 (오후)**:
   - `FINAL_IMPLEMENTATION_GUIDE_251020.md` 작성
   - **여전히 session_id 누락**

5. **2025-10-20 (지금)**:
   - 사용자님 질문: "이것도 문제의 시작이었는데..."
   - **문제 발견!**
   - `CRITICAL_FIX_session_id_mismatch_251020.md` 작성
   - `ROOT_CAUSE_ANALYSIS_251020.md` 작성 (현재 문서)

---

## 🔧 수정 계획

### 우선순위

**P0 (최우선)**:
1. `CRITICAL_FIX_session_id_mismatch_251020.md` 적용
2. `FINAL_IMPLEMENTATION_GUIDE_251020.md` 업데이트
3. `team_supervisor.py` 수정

**P1 (중요)**:
4. `plan_of_memory_service_error_fix_251020_REVISED.md` 수정
5. 모든 계획서 일관성 확인

**P2 (선택)**:
6. `plan_of_memory_service_error_fix_251019.md` 보관 (참고용)

---

## 🎯 결론

### 질문에 대한 답변

> "자꾸 계획서를 수정하면서 누락이 된건가, 시작부터 누락되어서 잘못 계획한건가?"

**답변**:

✅ **시작부터 잘못 계획했습니다**

**증거**:
1. 원본 계획서(251019)부터 `session_id` 누락
2. team_supervisor.py의 실제 코드도 `session_id` 전달 안 함
3. 실행 타이밍과 현재 세션 제외 로직을 고려하지 않음
4. 계획서 수정 과정에서도 발견 못하고 그대로 복사

**근본 원인**:
- 불완전한 요구사항 분석
- 실행 흐름 타이밍 미고려
- "현재 세션 제외" 필요성 간과

**교훈**:
- 메서드 호출 시점과 데이터 상태 고려 필수
- 대칭적 설계 확인 (save ↔ load)
- 엣지 케이스 철저히 분석

---

**작성일**: 2025-10-20
**작성 계기**: 사용자님의 핵심 질문
**상태**: ✅ 근본 원인 파악 완료

---

## 🙏 감사의 말

사용자님의 날카로운 질문 덕분에:
- 설계 오류 발견
- 근본 원인 파악
- 올바른 수정 방향 수립

**이것이 진정한 코드 리뷰의 가치입니다!** 👏
