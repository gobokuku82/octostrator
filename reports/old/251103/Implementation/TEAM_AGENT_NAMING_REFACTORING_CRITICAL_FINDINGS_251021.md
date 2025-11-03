# Team/Agent 네이밍 리팩토링 - 추가 발견 사항 및 수정 권장사항

**작성일**: 2025-10-21
**검증자**: Claude Code (기존 보고서 교차 검증)
**상태**: ✅ 검증 완료

---

## 🎯 Executive Summary

기존 리팩토링 계획 보고서(TEAM_AGENT_NAMING_REFACTORING_PLAN_251021.md)를 작성한 후,
다음 문서들과 교차 검증하여 **4가지 중요한 누락 사항**을 발견했습니다:

1. ✅ **ARCHITECTURE_OVERVIEW.md** - 시스템 전체 아키텍처
2. ✅ **EXECUTION_AGENTS_GUIDE.md** - Executor 상세 가이드
3. ✅ **STATE_MANAGEMENT_GUIDE.md** - State 관리 가이드
4. ✅ **COMPLETE_ROOT_CAUSE_ANALYSIS_251021.md** - 근본 원인 분석 (agent selection 문제)

---

## 📋 발견된 누락 사항 (4가지)

### 1. ⚠️ ExecutionStepState.team 필드의 핵심 역할

#### 발견 내용
**근본 원인 분석 보고서 (COMPLETE_ROOT_CAUSE_ANALYSIS_251021.md)**에서 확인:

```python
# team_supervisor.py Line 523-545
def _find_step_id_for_team(self, team_name: str, planning_state) -> Optional[str]:
    """team_name으로 step_id를 찾는 핵심 메서드"""
    for step in planning_state.get("execution_steps", []):
        if step.get("team") == team_name:  # ← team 필드 사용!
            return step.get("step_id")
    return None
```

**문제점**:
- 기존 리팩토링 계획에서 `ExecutionStepState.team` → `executor`로 단순 변경 제안
- 하지만 **이 필드는 현재 실행 흐름의 핵심**
- `active_teams` 생성 시 `set()` 사용으로 순서가 역전되는 문제와 직결

**영향도**: 🔴 **Critical** - 실행 순서 결정에 직접 관여

#### 권장 수정 방안

**Phase 1: 병행 사용 (하위 호환성 유지)**
```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str  # ⚠️ DEPRECATED (하위 호환성 유지)
    executor: str  # 새로운 표준 필드
```

**Phase 2: team 제거 (3개월 후)**
```python
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    executor: str  # team 완전 제거
```

**마이그레이션 로직**:
```python
def _find_step_id_for_executor(self, executor_name: str, planning_state):
    """하위 호환성을 고려한 step_id 검색"""
    for step in planning_state.get("execution_steps", []):
        # 1. 새 필드 우선
        if step.get("executor") == executor_name:
            return step.get("step_id")
        # 2. 구 필드 폴백
        if step.get("team") == executor_name:
            logger.warning(f"Using deprecated 'team' field for {executor_name}")
            return step.get("step_id")
    return None
```

---

### 2. 🟡 PlanningAgent의 "team" 용어 사용

#### 발견 내용
**planning_agent.py Line 276-286**에서 fallback 로직에 "team" 용어 사용:

```python
def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
    """패턴 매칭 기반 의도 분석"""
    # ...
    intent_to_agent = {
        IntentType.LEGAL_CONSULT: ["search_team"],  # ← "team" suffix
        IntentType.MARKET_INQUIRY: ["search_team"],
        IntentType.LOAN_CONSULT: ["search_team"],
        IntentType.CONTRACT_CREATION: ["document_team"],
        IntentType.CONTRACT_REVIEW: ["search_team", "analysis_team"],
        # ...
    }
    suggested_agents = intent_to_agent.get(intent_type, ["search_team"])
```

**문제점**:
- PlanningAgent는 "search_team", "document_team", "analysis_team" 이름으로 Executor 참조
- 기존 리팩토링 계획에서 이 부분 누락

**영향도**: 🟡 **Medium** - PlanningAgent와 TeamSupervisor 간 인터페이스

#### 권장 수정 방안

```python
# planning_agent.py
def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
    intent_to_agent = {
        IntentType.LEGAL_CONSULT: ["search_executor"],  # ← "executor" suffix
        IntentType.MARKET_INQUIRY: ["search_executor"],
        IntentType.LOAN_CONSULT: ["search_executor"],
        IntentType.CONTRACT_CREATION: ["document_executor"],
        IntentType.CONTRACT_REVIEW: ["search_executor", "analysis_executor"],
        # ...
    }
```

**단, 주의사항**:
- AgentRegistry에 등록된 이름도 함께 변경 필요
- `agent_adapter.py`의 `register_existing_agents()` 메서드 동시 수정

---

### 3. 🟡 LLM 프롬프트 파일 내 "team" 용어

#### 발견 내용
**agent_selection.txt** 프롬프트에서 "team" 용어 사용:

```
| LEGAL_CONSULT | ["search_team"] | 해결책 요청시 → + analysis_team |
```

**문제점**:
- LLM이 "search_team", "analysis_team" 이름으로 Agent 선택
- 기존 리팩토링 계획에서 프롬프트 파일 변경 누락

**영향도**: 🟡 **Medium** - LLM Agent 선택 로직

#### 권장 수정 방안

**agent_selection.txt 전체 용어 통일**:
```
# Before
| LEGAL_CONSULT | ["search_team"] | 해결책 요청시 → + analysis_team |

# After
| LEGAL_CONSULT | ["search_executor"] | 해결책 요청시 → + analysis_executor |
```

**변경 파일**:
- `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt`
- `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection_simple.txt`

---

### 4. 🟢 문서 파일 내 "Team" 용어 (매뉴얼 업데이트 필요)

#### 발견 내용
**3개 주요 매뉴얼 문서**에서 "team" 용어 광범위 사용:

1. **ARCHITECTURE_OVERVIEW.md**:
   ```
   팀 기반 워크플로우: Search, Analysis, Document 팀이 협업하여 작업 수행
   ```

2. **EXECUTION_AGENTS_GUIDE.md**:
   ```
   각 Agent는 독립적인 서브그래프로 구성
   SearchTeam, AnalysisTeam, DocumentTeam
   ```

3. **STATE_MANAGEMENT_GUIDE.md**:
   ```
   SearchTeamState, AnalysisTeamState, DocumentTeamState
   ```

**문제점**:
- 매뉴얼 문서가 코드와 불일치하면 개발자 혼란 가중
- 기존 리팩토링 계획에서 문서 업데이트 우선순위 낮음 (Priority 3)

**영향도**: 🟢 **Low** - 코드 동작에는 영향 없음, 문서 정합성 문제

#### 권장 수정 방안

**문서 업데이트 우선순위 상향 조정**:
- Priority 3 (Low) → Priority 2 (Medium)
- 이유: 코드 변경 직후 문서 즉시 업데이트하여 일관성 유지

**변경 대상 문서**:
1. `reports/Manual/ARCHITECTURE_OVERVIEW.md`
2. `reports/Manual/EXECUTION_AGENTS_GUIDE.md`
3. `reports/Manual/STATE_MANAGEMENT_GUIDE.md`
4. `reports/Manual/DATABASE_GUIDE.md`
5. `reports/Manual/SYSTEM_FLOW_DIAGRAM.md`

**변경 내용**:
- "팀" → "Executor"
- "SearchTeam" → "SearchExecutor"
- "TeamBasedSupervisor" → "ExecutionSupervisor"
- "team_results" → "executor_results"

---

## 📊 업데이트된 리팩토링 우선순위

### 기존 계획
```
Priority 1 (High): 파일명/클래스명
Priority 2 (Medium): 변수명/메서드명
Priority 3 (Low): 주석/로그/문서
```

### 수정된 계획
```
Priority 0 (Critical): ExecutionStepState.team 필드 병행 전략
  - team + executor 병행 사용
  - 하위 호환성 유지 로직
  - _find_step_id_for_executor() 마이그레이션

Priority 1 (High): 파일명/클래스명
  - team_supervisor.py → execution_supervisor.py
  - TeamBasedSupervisor → ExecutionSupervisor
  - State 클래스명 변경

Priority 2 (Medium): 변수명/메서드명 + PlanningAgent + 프롬프트
  - self.teams → self.executors
  - active_teams → active_executors
  - PlanningAgent 내 "team" suffix 제거
  - LLM 프롬프트 파일 업데이트

Priority 3 (Medium): 문서 업데이트 (우선순위 상향)
  - 5개 매뉴얼 문서 즉시 업데이트
  - 코드 변경과 동시 반영

Priority 4 (Low): 주석/로그 메시지
  - "팀 기반" → "Executor 조율"
  - 로그 메시지 정리
```

---

## 🛠️ 업데이트된 Phase별 실행 계획

### Phase 0: ExecutionStepState 병행 전략 (신규 추가, 1일)

**목표**: team 필드를 유지하면서 executor 필드 추가

```python
# separated_states.py
class ExecutionStepState(TypedDict):
    step_id: str
    step_type: str
    agent_name: str
    team: str  # DEPRECATED (하위 호환성)
    executor: str  # 새 표준 필드
```

**변경 파일**:
1. `backend/app/service_agent/foundation/separated_states.py`
   - ExecutionStepState에 executor 필드 추가
   - team 필드는 DEPRECATED 주석 추가

2. `backend/app/service_agent/supervisor/team_supervisor.py`
   - `_get_team_for_agent()` → `_get_executor_for_agent()` 메서드 추가
   - `_find_step_id_for_team()` → `_find_step_id_for_executor()` 메서드 추가
   - 두 메서드 모두 하위 호환성 로직 포함

3. `backend/app/service_agent/cognitive_agents/planning_agent.py`
   - execution_steps 생성 시 team과 executor 동시 설정
   ```python
   for i, step in enumerate(execution_plan.steps):
       execution_step = {
           "step_id": f"step_{i}",
           "agent_name": step.agent_name,
           "team": self._get_team_for_agent(step.agent_name),  # DEPRECATED
           "executor": self._get_team_for_agent(step.agent_name),  # 새 필드
       }
   ```

---

### Phase 1: 파일명/클래스명 변경 (기존 계획, 1일)

**변경 사항 동일**, 단 추가:
- import 구문 업데이트 시 PlanningAgent도 포함

---

### Phase 2: 변수명/메서드명 + PlanningAgent + 프롬프트 (수정, 2일)

**기존 계획에 추가**:

1. **PlanningAgent 수정**
   ```python
   # planning_agent.py Line 276-286
   intent_to_agent = {
       IntentType.LEGAL_CONSULT: ["search_executor"],  # ← 변경
       IntentType.MARKET_INQUIRY: ["search_executor"],
       # ...
   }
   ```

2. **agent_adapter.py 수정**
   ```python
   def register_existing_agents():
       """Executor 기반 아키텍처..."""  # ← 주석 변경

       AgentRegistry.register(
           name="search_executor",  # ← 변경
           agent_class=SearchExecutorPlaceholder,
           executor="search",  # ← 변경
       )
   ```

3. **LLM 프롬프트 파일 수정**
   - `agent_selection.txt`: "search_team" → "search_executor"
   - `agent_selection_simple.txt`: 동일 변경

---

### Phase 3: 문서 업데이트 (우선순위 상향, 1일)

**기존 Priority 3 → Priority 3 (Medium)으로 변경**

**변경 대상 문서 (5개)**:
1. `reports/Manual/ARCHITECTURE_OVERVIEW.md`
2. `reports/Manual/EXECUTION_AGENTS_GUIDE.md`
3. `reports/Manual/STATE_MANAGEMENT_GUIDE.md`
4. `reports/Manual/DATABASE_GUIDE.md`
5. `reports/Manual/SYSTEM_FLOW_DIAGRAM.md`

**변경 내용**:
- 전체 "팀" → "Executor" 용어 통일
- Mermaid 다이어그램 업데이트
- 코드 예시 블록 업데이트

---

### Phase 4: team 필드 완전 제거 (신규 추가, 3개월 후)

**조건**: Phase 0~3 완료 후 3개월 경과

**제거 대상**:
1. `ExecutionStepState.team` 필드
2. `_find_step_id_for_team()` 메서드 (하위 호환성 로직)
3. MainSupervisorState의 DEPRECATED 필드들
   - `active_teams`
   - `team_results`

**검증**:
- 3개월 간 프로덕션 로그에서 "Using deprecated 'team' field" 경고 발생 빈도 확인
- 0건이면 안전하게 제거

---

## ✅ 업데이트된 체크리스트

### Phase 0 체크리스트 (신규)
- [ ] ExecutionStepState에 executor 필드 추가
- [ ] team 필드에 DEPRECATED 주석 추가
- [ ] _get_executor_for_agent() 메서드 추가 (하위 호환성 포함)
- [ ] _find_step_id_for_executor() 메서드 추가 (하위 호환성 포함)
- [ ] PlanningAgent에서 team/executor 동시 설정
- [ ] 단위 테스트: 두 필드 모두 정상 동작 확인

### Phase 2 추가 체크리스트
- [ ] PlanningAgent 내 "team" suffix 제거
- [ ] agent_adapter.py "team" → "executor" 변경
- [ ] agent_selection.txt 프롬프트 업데이트
- [ ] agent_selection_simple.txt 프롬프트 업데이트
- [ ] AgentRegistry 등록 이름 변경 확인

### Phase 3 추가 체크리스트 (우선순위 상향)
- [ ] ARCHITECTURE_OVERVIEW.md 업데이트
- [ ] EXECUTION_AGENTS_GUIDE.md 업데이트
- [ ] STATE_MANAGEMENT_GUIDE.md 업데이트
- [ ] DATABASE_GUIDE.md 업데이트
- [ ] SYSTEM_FLOW_DIAGRAM.md 업데이트
- [ ] Mermaid 다이어그램 "Team" → "Executor" 변경
- [ ] 코드 예시 블록 전체 검증

### Phase 4 체크리스트 (신규, 3개월 후)
- [ ] 프로덕션 로그 분석 (deprecated 경고 빈도)
- [ ] ExecutionStepState.team 필드 제거
- [ ] _find_step_id_for_team() 메서드 제거
- [ ] MainSupervisorState DEPRECATED 필드 제거
- [ ] 회귀 테스트 전체 실행
- [ ] 프로덕션 배포 후 1주일 모니터링

---

## 📊 예상 작업 기간 업데이트

### 기존 계획
- 총 8일 (준비 1일 + 변경 5일 + 테스트 2일)

### 수정된 계획
- **Phase 0**: 1일 (ExecutionStepState 병행 전략)
- **Phase 1**: 1일 (파일명/클래스명)
- **Phase 2**: 2일 (변수명/메서드명 + PlanningAgent + 프롬프트)
- **Phase 3**: 1일 (문서 업데이트, 우선순위 상향)
- **테스트**: 2일 (단위 + 통합 + 회귀)
- **Phase 4**: 1일 (3개월 후 team 필드 완전 제거)

**총 작업 기간**: 7일 (즉시 실행) + 1일 (3개월 후)

---

## 🎯 최종 권장사항

### 즉시 적용 (Priority 0)
1. ✅ **ExecutionStepState 병행 전략 적용** (Phase 0)
   - **이유**: team 필드는 현재 핵심 역할 수행, 급격한 변경은 위험
   - **방법**: executor 필드 추가, team 유지 (DEPRECATED)
   - **소요**: 1일
   - **위험**: 낮음 (하위 호환성 완벽 유지)

### 순차 적용 (Priority 1-3)
2. ✅ **파일명/클래스명 변경** (Phase 1)
3. ✅ **변수명/메서드명 + PlanningAgent + 프롬프트** (Phase 2)
4. ✅ **문서 즉시 업데이트** (Phase 3, 우선순위 상향)

### 장기 적용 (Priority 4)
5. ⏳ **team 필드 완전 제거** (Phase 4, 3개월 후)
   - **조건**: 프로덕션 로그에서 deprecated 경고 0건
   - **방법**: 점진적 제거, 충분한 검증 기간

---

## 📝 변경 이력

| 날짜 | 변경 사항 | 작성자 |
|------|----------|--------|
| 2025-10-21 | 초기 보고서 작성 (TEAM_AGENT_NAMING_REFACTORING_PLAN_251021.md) | Claude Code |
| 2025-10-21 | 교차 검증 후 4가지 누락 사항 발견 및 보고서 작성 | Claude Code |
| 2025-10-21 | Phase 0 추가, 우선순위 재조정, 체크리스트 업데이트 | Claude Code |

---

**작성 완료**: 2025-10-21
**다음 단계**: 사용자 승인 후 Phase 0부터 순차 구현
