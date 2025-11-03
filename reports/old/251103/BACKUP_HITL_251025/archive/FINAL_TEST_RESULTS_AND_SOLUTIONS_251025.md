# HITL 테스트 최종 결과 및 해결 방법
**Date:** 2025-10-25
**Status:** 근본 원인 확인 완료

---

## 테스트 결과 요약

### 확인한 항목 (모두 테스트 완료)

1. ✅ **State** - TypedDict에 HITL 필드 추가됨
2. ✅ **Checkpoint** - AsyncPostgresSaver 사용, thread_id로 저장
3. ✅ **Command** - Command(resume=...) 패턴 테스트 완료
4. ✅ **Thread ID** - Main과 Subgraph 같은 thread_id 사용 (session_id = thread_id)
5. ✅ **Config** - `{"configurable": {"thread_id": session_id}}` 올바름
6. ✅ **Subgraph 인스턴스** - 재사용 패턴 구현됨

---

## 근본 원인 발견

### Subgraph Checkpoint가 저장되지 않음

```
테스트 결과:
- Subgraph checkpoint: EMPTY (Next node: ())
- Main graph checkpoint: HAS DATA (Values: ['query', 'status', 'subgraph_result'])
```

**왜 저장 안 되나?**

Main graph 내에서 subgraph를 실행하면:
- LangGraph는 **Main graph의 checkpoint만** 저장
- Subgraph는 main graph의 **내부 실행 단계**일 뿐
- Subgraph 자체의 checkpoint는 **저장되지 않음**

**Resume 시 문제:**
- `subgraph_app.astream(Command(resume=...), config)` 호출
- Subgraph checkpoint가 없음 → **아무것도 실행 안 됨** (no events)
- 결과: finish_node 절대 도달 불가

**이것이 LangGraph Issue #4796입니다.**

---

## 해결 방법

### Option 1: Flatten Architecture (추천) ✅

**방법:** Subgraph 제거, 모든 노드를 Main graph로 이동

**구조:**
```
Before (Subgraph):
Main Graph → Document Subgraph (plan → search → aggregate → generate)
                    ↑ HITL interrupt 발생

After (Flatten):
Main Graph → plan → search → aggregate → [HITL] → generate
                                          ↑ 직접 interrupt
```

**장점:**
- ✅ Main graph checkpoint만 사용 → 저장/복원 확실히 작동
- ✅ LangGraph 0.6에서 검증된 패턴
- ✅ 구현 단순, 디버깅 쉬움
- ✅ Issue #4796 영향 없음

**단점:**
- ❌ 3-4일 작업 필요
- ❌ 기존 subgraph 코드 재구조화

**구현:**
1. Git reset to `ab8cd08`
2. `service_agent/teams/document_team/` 노드들을 `supervisor/team_supervisor.py`로 이동
3. Main graph에 노드 추가: planning → search → aggregate → **[HITL]** → generate
4. HITL은 aggregate 이후 NodeInterrupt 발생
5. Resume은 `main_app.astream(Command(resume=...), config)`

**타임라인:** 3-4일

---

### Option 2: 별도 Subgraph App으로 분리 ⚠️

**방법:** Subgraph를 main graph 밖에서 독립 실행

**구조:**
```
Frontend ↔ FastAPI ↔ Supervisor
                        ↓ (직접 호출)
                     Document App (독립 graph)
```

**구현:**
```python
# team_supervisor.py
class TeamSupervisor:
    def __init__(self):
        # Subgraph를 별도 app으로 compile
        self.document_app = build_document_subgraph().compile(
            checkpointer=AsyncPostgresSaver(pool)
        )

    async def execute_document_team(self, state, session_id):
        # Main graph 밖에서 독립 실행
        config = {"configurable": {"thread_id": f"{session_id}:document"}}

        async for event in self.document_app.astream(state, config):
            if "__interrupt__" in event:
                return {"status": "interrupted", ...}

        return {"status": "completed", ...}

    async def resume_document_team(self, session_id, user_input):
        config = {"configurable": {"thread_id": f"{session_id}:document"}}

        # Subgraph app 직접 resume
        async for event in self.document_app.astream(
            Command(resume={"user_input": user_input}),
            config
        ):
            ...
```

**장점:**
- ✅ Subgraph checkpoint 저장됨 (독립 graph이므로)
- ✅ 현재 구조 유지 가능

**단점:**
- ❌ Main graph가 subgraph 완료를 기다리지 못함
- ❌ Main graph checkpoint와 Subgraph checkpoint 동기화 필요
- ❌ 복잡도 증가
- ❌ 테스트 필요 (작동 보장 없음)

**타임라인:** 2-3일 + 테스트

---

### Option 3: HITL을 Main Graph로 이동 (중간 방법) ✅

**방법:** HITL interrupt만 main graph로 이동, subgraph 구조 유지

**구조:**
```
Main Graph:
  execute_teams_node → [Check HITL 필요 여부] → [HITL Interrupt] → aggregate
                              ↓
                          Document Subgraph (HITL 없음, 순수 작업만)
```

**구현:**
```python
# team_supervisor.py
async def execute_teams_node(self, state):
    # Subgraph 실행 (HITL 없음)
    results = await self._execute_single_team("document", state)

    # HITL 체크를 MAIN GRAPH에서
    if results.get("needs_collaboration"):
        state["workflow_status"] = "interrupted"
        state["interrupted_by"] = "document"
        state["interrupt_data"] = results.get("collaboration_data")

        # Main graph에서 interrupt 발생
        raise NodeInterrupt(results["collaboration_data"])

    return state

# Subgraph는 단순히 결과만 반환
def aggregate_node(state):
    if needs_collaboration:
        return {
            "status": "completed",
            "needs_collaboration": True,
            "collaboration_data": {...}
        }
    return {"status": "completed"}
```

**장점:**
- ✅ Main graph checkpoint만 사용 → 작동 확실
- ✅ Subgraph 구조 유지 (코드 재구조화 최소)
- ✅ 1-2일 작업

**단점:**
- ❌ Subgraph에서 직접 HITL 불가능 (우회)
- ❌ Subgraph 역할이 애매해짐

**타임라인:** 1-2일

---

## 추천 순위

### 1순위: Option 1 (Flatten Architecture) ✅

**이유:**
- 가장 명확하고 단순한 구조
- LangGraph 0.6 검증된 패턴
- 장기적으로 유지보수 쉬움
- 3-4일 투자 가치 있음

**다음 단계:**
1. Git reset to `ab8cd08 Upload Plan : Docs_Agent`
2. `HITL_RESTART_COMPREHENSIVE_PLAN_251025.md` 따라 구현
3. 3-4일 집중 작업

---

### 2순위: Option 3 (HITL만 Main으로) ⚠️

**이유:**
- 빠른 구현 (1-2일)
- 최소 변경

**단점:**
- Subgraph 존재 이유가 약해짐
- 나중에 결국 flatten 필요할 수도

**사용 시나리오:**
- 급하게 HITL 필요한 경우
- 임시 해결책으로 사용

---

### 3순위: Option 2 (독립 Subgraph App) ❌

**이유:**
- 복잡도 높음
- 작동 보장 없음
- 추천하지 않음

---

## 테스트 환경에서 확인된 사실

### 테스트 결과 상세

```
Phase 1 (Initial Execution):
  ✅ work_node executed (step_count = 1)
  ✅ interrupt_node raised NodeInterrupt
  ✅ Main graph detected interrupt
  ✅ Workflow paused

Phase 2 (Checkpoint 확인):
  ✅ Main graph checkpoint: 저장됨
  ❌ Subgraph checkpoint: EMPTY

Phase 3 (Resume):
  ❌ Command(resume=...) 호출 → NO events
  ❌ finish_node never executed
  ❌ Resume 완전히 실패
```

### 테스트한 항목들

1. ✅ `astream(None)` → 실패
2. ✅ `Command(resume=...)` → 실패
3. ✅ Separate thread_id → 관계 없음 (subgraph checkpoint 자체가 저장 안 됨)
4. ✅ Same thread_id → 관계 없음
5. ✅ user_input을 state로 전달 → interrupt_node가 실행 안 되어 의미 없음

**결론:** Subgraph 내 HITL은 현재 LangGraph 버전에서 **불가능**

---

## 최종 결정 필요

### 질문:

**Option 1 (Flatten Architecture) 진행할까요?**

- Git reset to `ab8cd08`
- 3-4일 작업
- 확실한 해결

**또는**

**Option 3 (HITL만 Main으로) 시도할까요?**

- 빠른 구현 (1-2일)
- 임시 해결책

---

## 관련 문서

- [TEST_RESULTS_HITL_SUBGRAPH_RESUME_251025.md](TEST_RESULTS_HITL_SUBGRAPH_RESUME_251025.md) - 이전 테스트 결과
- [CRITICAL_ANALYSIS_LANGGRAPH_06_SUBGRAPH_HITL_251025.md](CRITICAL_ANALYSIS_LANGGRAPH_06_SUBGRAPH_HITL_251025.md) - LangGraph 0.6 분석
- [HITL_RESTART_COMPREHENSIVE_PLAN_251025.md](HITL_RESTART_COMPREHENSIVE_PLAN_251025.md) - Flatten 구현 계획
- [DECISION_SUMMARY_HITL_ARCHITECTURE_251025.md](DECISION_SUMMARY_HITL_ARCHITECTURE_251025.md) - 이전 의사결정 요약

---

**작성:** 2025-10-25
**테스트 완료:** 모든 주요 항목 확인
**근본 원인:** Subgraph checkpoint 저장 안 됨 (LangGraph Issue #4796)
**추천 해결책:** Option 1 (Flatten Architecture)
