# Human-in-the-Loop Documentation

**Created:** 2025-10-22
**Status:** 📋 Planning Phase Complete
**Priority:** 🔴 P0 (Next Major Feature)

---

## Overview

이 폴더는 HolmesNyangz 챗봇에 Human-in-the-Loop (HITL) 기능을 구현하기 위한 계획서와 기반 개념 문서들을 담고 있습니다.

**Human-in-the-Loop란?**
- LLM이 중요한 작업을 실행하기 전에 사용자 승인을 요청하는 기능
- 예: 부동산 매물 예약, 상담 신청, 중요 결정 등
- LangGraph의 Checkpointer 기반으로 구현

---

## Quick Start

### 빠른 구현 가이드 (바로 시작하고 싶다면)

1. **[HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md](HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md)** 읽기
2. Phase 1부터 순서대로 구현
3. 3주 소요 예상

### 개념 이해부터 하고 싶다면

1. **[LANGGRAPH_CHECKPOINTER_HISTORY.md](LANGGRAPH_CHECKPOINTER_HISTORY.md)** - Checkpointer의 역사와 버전별 변화
2. **[CHECKPOINTER_COMPLETE_GUIDE.md](CHECKPOINTER_COMPLETE_GUIDE.md)** - Checkpointer의 모든 기능 (7가지)
3. **[HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md](HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md)** - 실제 구현 계획

---

## 📚 Document Index

### 1. HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md

**용도:** HITL 구현을 위한 완전한 가이드

**포함 내용:**
- LangGraph 0.6+ 기능 (interrupt, Command)
- 아키텍처 설계 (Mermaid 다이어그램)
- 백엔드 구현 (ApprovalNode, API endpoints, WebSocket)
- 프론트엔드 구현 (ApprovalModal, useApproval hook)
- 테스트 전략 (Unit, Integration, E2E)
- 배포 계획
- 3주 타임라인

**누가 읽어야 하나:**
- HITL을 구현할 개발자 (필독)
- 프로젝트 매니저 (타임라인 확인)
- QA 엔지니어 (테스트 전략)

**키워드:** `interrupt()`, `Command`, `ApprovalNode`, WebSocket, React Modal

---

### 2. CHECKPOINTER_COMPLETE_GUIDE.md

**용도:** LangGraph Checkpointer의 모든 기능을 이해하기 위한 종합 가이드

**포함 내용:**

#### Checkpointer의 7가지 주요 기능:

1. **Human-in-the-Loop (HITL)**
   - `interrupt()` - 워크플로우 일시정지
   - `Command` - 사용자 입력으로 재개

2. **Memory (대화 기록)**
   - `thread_id`를 통한 세션 기억
   - 이전 대화 기록 로드

3. **State Time Travel (상태 시간 여행)**
   - 과거 체크포인트로 되돌아가기
   - 상태 수정 후 다시 실행

4. **Replay (재실행 최적화)**
   - 이미 실행된 노드 건너뛰기
   - 실패한 부분만 재시도

5. **Debugging (디버깅)**
   - 단계별 상태 검사
   - 그래프 실행 흐름 추적

6. **Fault Tolerance (장애 복구)**
   - 실패 시 마지막 성공 지점부터 재개
   - 부분 실패 복구

7. **Streaming (실시간 모니터링)**
   - 그래프 실행 중 상태 변화 스트리밍
   - 진행 상황 실시간 추적

**Database Schema:**
- `checkpoints` - 메인 상태 저장
- `checkpoint_writes` - 장애 복구용 pending writes
- `checkpoint_blobs` - 대용량 데이터
- `checkpoint_migrations` - 스키마 버전 관리

**실용 예제:**
- HITL + Time Travel 조합 (거부 → 되돌아가기 → 수정 → 재시도)
- 디버깅 워크플로우 (에러 발견 → 되돌아가기 → 수정 → 재개)
- 장애 복구 (부분 실패 → 실패한 노드만 재시도)

**누가 읽어야 하나:**
- LangGraph를 처음 사용하는 개발자
- Checkpointer 개념을 깊이 이해하고 싶은 사람
- 고급 기능 (Time Travel, Replay 등) 활용을 고려하는 개발자

**키워드:** `AsyncPostgresSaver`, `thread_id`, `checkpoint_id`, `get_state_history()`, `update_state()`

---

### 3. LANGGRAPH_CHECKPOINTER_HISTORY.md

**용도:** Checkpointer가 언제, 왜 도입되었는지 이해

**포함 내용:**
- LangGraph 버전별 Checkpointer 기능 변화
- v0.1.x (2023 mid): InMemorySaver만 존재
- v0.2.0 (Aug 2024): Major Checkpointer ecosystem release
  - Breaking changes: `thread_ts` → `checkpoint_id`
  - PostgreSQL, SQLite Checkpointer 패키지 분리
- v0.6.x (Oct 2024): Command primitive, interrupt() 개선
- v1.0.0 (Oct 17, 2024): Production-ready

**왜 교재에 없나:**
- 대부분 교재는 2024년 중반 이전 출간
- v0.2.0 (Aug 2024) 이전 버전 기준
- Checkpointer는 비교적 최신 기능

**Breaking Changes:**
- v0.2.0: API 변경 (thread_ts → checkpoint_id)
- 기존 코드 마이그레이션 가이드 포함

**누가 읽어야 하나:**
- 교재와 실제 코드의 차이를 이해하고 싶은 사람
- 버전 업그레이드 계획 중인 개발자
- LangGraph의 발전 과정이 궁금한 사람

**키워드:** `v0.1`, `v0.2`, `v0.6`, `v1.0`, Breaking Changes, Migration

---

## 🎯 개념 계층 구조

```
LangGraph Framework (최상위)
    │
    ├─ Checkpointing / Persistence (기반 인프라) ← 모든 고급 기능의 전제조건
    │   ├─ AsyncPostgresSaver (Production)
    │   ├─ SQLiteSaver (Local Development)
    │   └─ InMemorySaver (Testing)
    │
    ├─ Advanced Features (Checkpointer 기반)
    │   ├─ Human-in-the-Loop (HITL) ← 우리가 구현할 기능
    │   ├─ Memory (대화 기록)
    │   ├─ State Time Travel (상태 수정)
    │   ├─ Replay (재실행 최적화)
    │   ├─ Debugging (디버깅)
    │   ├─ Fault Tolerance (장애 복구)
    │   └─ Streaming (실시간 모니터링)
    │
    └─ Implementation Primitives (구현 도구)
        ├─ interrupt() (일시정지)
        └─ Command (재개/제어)
```

**핵심 이해:**
- **Checkpointer = 필수 기반 인프라** (없으면 HITL 불가능)
- **HITL = Checkpointer 위에 구축된 기능**
- **interrupt/Command = HITL을 구현하는 도구**

---

## 🚀 Implementation Status

### ✅ Completed (기반 완료)
- AsyncPostgresSaver 설정 완료 (`backend/app/api/chat_api.py`)
- Checkpoint 테이블 자동 생성 (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`)
- thread_id 기반 세션 관리
- 3-Tier Hybrid Memory 구현 (93% 토큰 절약)

### 📋 Planned (계획 완료)
- Human-in-the-Loop 상세 구현 계획 (3주)
- Backend: ApprovalNode, API endpoints, WebSocket
- Frontend: ApprovalModal, useApproval hook
- Testing: Unit, Integration, E2E
- Deployment: Blue-Green, Rollback plan

### ⏳ Not Started (미착수)
- HITL 실제 코드 구현
- 승인 UI 개발
- 통합 테스트

---

## 🎓 Recommended Reading Path

### Path 1: 빠른 구현 (개념 이해 후 바로 구현)
**소요 시간:** 1시간

1. **CHECKPOINTER_COMPLETE_GUIDE.md** - Section 1 (HITL만 읽기) (15분)
2. **HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md** (45분)
3. 구현 시작!

---

### Path 2: 깊은 이해 (모든 개념 완전 이해)
**소요 시간:** 2-3시간

1. **LANGGRAPH_CHECKPOINTER_HISTORY.md** (30분)
   - Checkpointer의 역사 이해

2. **CHECKPOINTER_COMPLETE_GUIDE.md** (90분)
   - 7가지 기능 모두 이해
   - Database schema 확인
   - 실전 예제 학습

3. **HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md** (45분)
   - 실제 구현 계획 숙지

4. 구현 시작!

---

### Path 3: 선택적 학습 (필요한 부분만)
**소요 시간:** 30분-1시간

**HITL만 구현하고 싶다면:**
- CHECKPOINTER_COMPLETE_GUIDE.md - Section 1 (HITL)
- HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md

**Time Travel도 활용하고 싶다면:**
- CHECKPOINTER_COMPLETE_GUIDE.md - Section 1, 3
- HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN_251021.md

**디버깅 능력 향상하고 싶다면:**
- CHECKPOINTER_COMPLETE_GUIDE.md - Section 5
- `get_state_history()` 사용법

**장애 복구 강화하고 싶다면:**
- CHECKPOINTER_COMPLETE_GUIDE.md - Section 6
- Fault tolerance 패턴

---

## 📊 Feature Comparison

### LangGraph 버전별 HITL 지원

| 기능 | v0.1.x | v0.2.0 | v0.6.x | v1.0.0 |
|------|--------|--------|--------|--------|
| InMemorySaver | ✅ | ✅ | ✅ | ✅ |
| PostgresSaver | ❌ | ✅ | ✅ | ✅ |
| interrupt() | 기초적 | 기초적 | ✅ 개선 | ✅ 안정 |
| Command | ❌ | ❌ | ✅ 신규 | ✅ 안정 |
| Time Travel | ❌ | ✅ | ✅ | ✅ |
| Production Ready | ❌ | ⚠️ Beta | ⚠️ RC | ✅ |

**우리 프로젝트:** LangGraph 0.6+ / 1.0.0 사용 예정

---

## 🔗 Related Documentation

### Internal Documentation
- **[../database/README_SESSION_DELETE_FIX_251021.md](../database/README_SESSION_DELETE_FIX_251021.md)** - Session deletion bug fix (thread_id 이슈)
- **[../Implementation/SYSTEM_ENHANCEMENT_ROADMAP_251021.md](../Implementation/SYSTEM_ENHANCEMENT_ROADMAP_251021.md)** - 전체 시스템 고도화 로드맵
- **[../long_term_memory/IMPLEMENTATION_COMPLETE_251021.md](../long_term_memory/IMPLEMENTATION_COMPLETE_251021.md)** - 3-Tier Hybrid Memory 구현 완료 보고서
- **[../../Manual/MEMORY_CONFIGURATION_GUIDE.md](../../Manual/MEMORY_CONFIGURATION_GUIDE.md)** - Memory 설정 가이드 (v2.0.0)

### External References
- [LangGraph Documentation - Human-in-the-Loop](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [LangGraph API Reference - interrupt()](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.types.interrupt)
- [LangGraph API Reference - Command](https://langchain-ai.github.io/langgraph/reference/types/#command)
- [LangGraph Checkpointer Packages](https://github.com/langchain-ai/langgraph/tree/main/libs)

---

## 💡 Key Insights

### 1. Checkpointer는 선택이 아닌 필수
- HITL, Memory, Time Travel 등 모든 고급 기능의 전제조건
- 없으면 단순 stateless 그래프만 가능
- HolmesNyangz는 이미 AsyncPostgresSaver 설정 완료 ✅

### 2. interrupt()와 Command의 관계
```python
# interrupt() - 워크플로우 일시정지, 데이터 반환
user_decision = interrupt({"action": "approve", "data": {...}})

# Command - 사용자 입력으로 재개
result = graph.invoke(
    Command(resume={"approved": True}),
    config={"configurable": {"thread_id": session_id}}
)
```
- `interrupt()` = 질문하기 (그래프 → 사용자)
- `Command` = 답변하기 (사용자 → 그래프)

### 3. thread_id의 중요성
- Checkpointer의 핵심 식별자
- 같은 thread_id = 같은 대화 세션 = 같은 상태 기억
- HolmesNyangz: `session_id` 값을 `thread_id`로 전달
  ```python
  config = {"configurable": {"thread_id": session_id}}
  ```

### 4. Database vs. In-Memory
- **InMemorySaver:** 테스트용, 서버 재시작 시 데이터 소실
- **AsyncPostgresSaver:** 프로덕션용, 영구 저장, 분산 시스템 지원
- HolmesNyangz: AsyncPostgresSaver 사용 (이미 설정 완료)

---

## 🛠️ Implementation Checklist

### Before You Start
- [ ] LangGraph 0.6+ 설치 확인
- [ ] AsyncPostgresSaver 설정 확인 (✅ 이미 완료)
- [ ] Checkpoint 테이블 존재 확인 (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`)
- [ ] 문서 읽기 완료 (최소 HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN)

### Phase 1: Backend Core (Week 1)
- [ ] `ApprovalNode` 클래스 구현
- [ ] `ApprovalConfig` 승인 규칙 정의
- [ ] `team_supervisor.py`에 ApprovalNode 통합
- [ ] Unit tests 작성

### Phase 2: API & WebSocket (Week 2)
- [ ] `/approve`, `/reject`, `/pending-approval` 엔드포인트 구현
- [ ] WebSocket `approval_request` 이벤트 추가
- [ ] Integration tests 작성

### Phase 3: Frontend (Week 2-3)
- [ ] `ApprovalModal.tsx` 컴포넌트 개발
- [ ] `useApproval.ts` 커스텀 훅 개발
- [ ] ChatInterface에 통합
- [ ] E2E tests 작성

### Phase 4: Testing & Deployment (Week 3)
- [ ] 전체 통합 테스트
- [ ] 성능 테스트
- [ ] Blue-Green 배포
- [ ] 모니터링 설정

---

## ⚠️ Known Issues & Solutions

### Issue 1: session_id vs thread_id
**Problem:** LangGraph checkpoint tables use `thread_id`, but our code uses `session_id`

**Status:** ✅ FIXED (2025-10-21)

**Solution:**
- DELETE queries updated to use `thread_id` column
- Value still uses `session_id` variable: `{"thread_id": session_id}`
- Files modified: `chat_api.py`, `postgres_session_manager.py`

**Reference:** [SESSION_DELETE_FIX_RESULT_251021.md](../database/SESSION_DELETE_FIX_RESULT_251021.md)

---

### Issue 2: Windows AsyncIO Event Loop
**Problem:** `Psycopg cannot use the 'ProactorEventLoop' to run in async mode`

**Solution:**
```python
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**Reference:** [IMPLEMENTATION_COMPLETE_251021.md](../long_term_memory/IMPLEMENTATION_COMPLETE_251021.md) - Issue 3

---

## 📞 Support & Questions

### Documentation Issues
- 문서 오류 발견 시: 이슈 생성 또는 직접 수정
- 추가 설명 필요 시: Claude Code에 요청

### Implementation Questions
- HITL 구현 중 막힌 부분: HUMAN_IN_THE_LOOP_IMPLEMENTATION_PLAN의 troubleshooting 섹션 참고
- Checkpointer 관련 질문: CHECKPOINTER_COMPLETE_GUIDE 재확인
- LangGraph 버전 이슈: LANGGRAPH_CHECKPOINTER_HISTORY의 breaking changes 확인

### External Resources
- LangGraph Discord: [https://discord.gg/langchain](https://discord.gg/langchain)
- LangGraph GitHub Issues: [https://github.com/langchain-ai/langgraph/issues](https://github.com/langchain-ai/langgraph/issues)

---

## 🎯 Success Criteria

### Documentation Complete ✅
- [x] Checkpointer 역사 문서화
- [x] Checkpointer 7가지 기능 문서화
- [x] HITL 상세 구현 계획 작성
- [x] README 인덱스 문서 작성

### Implementation Ready ✅
- [x] LangGraph 0.6+ 기능 조사 완료
- [x] 아키텍처 설계 완료
- [x] Backend/Frontend 구현 계획 완료
- [x] 테스트 전략 수립 완료
- [x] 배포 계획 수립 완료

### Next Phase (Waiting for Approval)
- [ ] User approval to start implementation
- [ ] Resource allocation (2-3 developers, 3 weeks)
- [ ] Sprint planning
- [ ] Development environment setup

---

**Created by:** Claude Code
**Date:** 2025-10-22
**Status:** 📋 Planning Complete - Ready for Implementation
**Estimated Implementation Time:** 3 weeks
**Priority:** P0 (Critical - Last major feature before launch)

---

## Version History

- **v1.0.0** (2025-10-22): Initial documentation index created
  - 3 comprehensive guides completed
  - Concept hierarchy clarified
  - Implementation roadmap ready
  - Waiting for user approval to proceed
