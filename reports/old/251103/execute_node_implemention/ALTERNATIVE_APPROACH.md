# Execute Node Enhancement - 대안 접근법: 새 에이전트 파일 추가

**작성일**: 2025-10-15
**관련 문서**: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

---

## 🤔 질문 정리

> **기존 supervisor의 graph는 놔두고 execute 부분을 실행할 수 있는 에이전트 파일을 더 만들면 어떤가?**
> **위치는 cognitive가 맞는가?**

---

## 📊 현재 구조 분석

### 디렉토리 구조

```
backend/app/service_agent/
├── cognitive_agents/           # 인지/계획 담당
│   ├── planning_agent.py       # 의도 분석, 실행 계획 수립
│   └── query_decomposer.py     # 복합 질문 분해
│
├── execution_agents/           # 실행 담당
│   ├── search_executor.py      # 검색 실행
│   ├── analysis_executor.py    # 분석 실행
│   └── document_executor.py    # 문서 생성
│
├── supervisor/                 # 조정 담당
│   └── team_supervisor.py      # 전체 오케스트레이션
│
├── foundation/                 # 기반 시스템
│   ├── agent_registry.py
│   ├── separated_states.py
│   └── ...
│
├── llm_manager/               # LLM 관리
│   └── prompts/
│       ├── cognitive/         # 인지 프롬프트
│       └── execution/         # 실행 프롬프트
│
└── tools/                     # 도구들
    ├── legal_search.py
    ├── market_data_tool.py
    └── ...
```

### 역할 구분

| 레이어 | 역할 | 현재 파일 | LLM 호출 |
|--------|------|----------|---------|
| **Cognitive** | 계획 수립 | `planning_agent.py`, `query_decomposer.py` | 3회 (Intent, Agent Selection, Decomposition) |
| **Execution** | 작업 실행 | `search_executor.py`, `analysis_executor.py`, `document_executor.py` | 6-9회 (Tool Selection, Analysis) |
| **Supervisor** | 전체 조율 | `team_supervisor.py` | 1회 (Response Synthesis) |

---

## ✅ 추천: 새 에이전트 파일 추가 방식

### Option A: `ExecutionOrchestrator` 추가 (권장)

**위치**: `backend/app/service_agent/cognitive_agents/execution_orchestrator.py` ✅

**이유**:
1. **인지적 역할**: 실행 중 "어떻게 조율할지" 결정 → Cognitive
2. **계획 연장선**: PlanningAgent가 사전 계획, ExecutionOrchestrator가 실행 중 조정
3. **일관성**: 다른 cognitive_agents와 역할이 유사

**파일 구조**:
```python
# backend/app/service_agent/cognitive_agents/execution_orchestrator.py

"""
Execution Orchestrator - 실행 중 동적 조율 전담
TeamSupervisor의 execute_teams_node를 지원하는 독립 에이전트
"""

from typing import Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationDecision:
    """오케스트레이션 결정"""
    phase: str  # "pre", "before_team", "after_team", "post"
    decision: Dict[str, Any]
    reasoning: str
    llm_call_number: int


class ExecutionOrchestrator:
    """
    실행 중 동적 조율을 담당하는 Cognitive Agent

    역할:
    - 실행 전 전략 수립 (pre_execution)
    - 팀별 도구 오케스트레이션 (before_team)
    - 중간 결과 분석 (after_team)
    - 실행 후 종합 검토 (post_execution)

    Supervisor의 execute_teams_node와 협업:
    - Supervisor: 팀 실행 루프 관리
    - Orchestrator: 각 단계에서 LLM 기반 의사결정 제공
    """

    def __init__(self, llm_context=None):
        """초기화"""
        from app.service_agent.llm_manager import LLMService
        self.llm_service = LLMService(llm_context=llm_context)
        self.decision_history: List[OrchestrationDecision] = []
        self.llm_call_count = 0

    async def decide_execution_strategy(
        self,
        query: str,
        intent_type: str,
        confidence: float,
        planned_teams: List[Dict[str, Any]],
        intermediate_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        실행 전 전략 결정

        LLM 호출: execution_strategy.txt

        Returns:
            {
                "strategy": "sequential|parallel|adaptive",
                "execution_order": [...],
                "parallel_groups": [...],
                "total_estimated_time": float,
                "reasoning": str
            }
        """
        logger.info("[ExecutionOrchestrator] Deciding execution strategy")

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="execution_strategy",
                variables={
                    "query": query,
                    "intent_type": intent_type,
                    "confidence": confidence,
                    "planned_teams": planned_teams,
                    "estimated_times": {t["team"]: t.get("estimated_time", 10.0) for t in planned_teams},
                    "intermediate_results": intermediate_results or {}
                },
                temperature=0.1,
                max_tokens=600
            )

            # 결정 기록
            self._log_decision("pre_execution", result)

            return result

        except Exception as e:
            logger.error(f"Strategy decision failed: {e}")
            # Fallback
            return {
                "strategy": "sequential",
                "execution_order": planned_teams,
                "reasoning": "Fallback: LLM failed"
            }

    async def orchestrate_tools(
        self,
        team_name: str,
        query: str,
        used_tools: List[str],
        available_tools: List[str],
        tool_registry: Dict[str, Any],
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        팀별 도구 오케스트레이션

        LLM 호출: tool_orchestration.txt

        Returns:
            {
                "selected_tools": [
                    {
                        "tool_name": str,
                        "priority": int,
                        "parameters": dict,
                        "reason": str
                    }
                ],
                "skipped_tools": [...],
                "optimization_notes": str
            }
        """
        logger.info(f"[ExecutionOrchestrator] Orchestrating tools for {team_name}")

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="tool_orchestration",
                variables={
                    "current_team": team_name,
                    "query": query,
                    "used_tools": used_tools,
                    "available_tools": available_tools,
                    "tool_registry": tool_registry,
                    "previous_results": self._summarize_results(previous_results),
                    "quality_scores": {k: v.get("quality", 0.0) for k, v in previous_results.items()}
                },
                temperature=0.1,
                max_tokens=800
            )

            # 결정 기록
            self._log_decision(f"before_{team_name}", result)

            return result

        except Exception as e:
            logger.error(f"Tool orchestration failed: {e}")
            # Fallback: 모든 도구 허용
            return {
                "selected_tools": [],
                "skipped_tools": [],
                "optimization_notes": "Fallback: all tools available"
            }

    async def analyze_team_result(
        self,
        team_name: str,
        team_result: Any,
        tools_used: List[str],
        execution_time: float,
        query: str,
        original_plan: Dict[str, Any],
        remaining_teams: List[str],
        intermediate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        팀 실행 후 결과 분석

        LLM 호출: result_analysis.txt

        Returns:
            {
                "quality_score": float,
                "next_action": "continue|adjust|early_exit",
                "plan_adjustments": [...],
                "data_to_pass": {...},
                "early_exit_possible": bool
            }
        """
        logger.info(f"[ExecutionOrchestrator] Analyzing result from {team_name}")

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="result_analysis",
                variables={
                    "completed_team": team_name,
                    "team_result": self._summarize_result(team_result),
                    "tools_used": tools_used,
                    "execution_time": execution_time,
                    "error": team_result.get("error") if isinstance(team_result, dict) else None,
                    "query": query,
                    "original_plan": original_plan,
                    "remaining_teams": remaining_teams,
                    "intermediate_results": self._summarize_results(intermediate_results)
                },
                temperature=0.2,
                max_tokens=700
            )

            # 결정 기록
            self._log_decision(f"after_{team_name}", result)

            return result

        except Exception as e:
            logger.error(f"Result analysis failed: {e}")
            # Fallback: 계속 진행
            return {
                "quality_score": 0.7,
                "next_action": "continue",
                "reasoning": "Fallback: continue execution"
            }

    async def review_execution(
        self,
        query: str,
        original_plan: Dict[str, Any],
        executed_teams: List[str],
        team_results: Dict[str, Any],
        quality_scores: Dict[str, float],
        strategy_adjustments: List[str],
        total_execution_time: float
    ) -> Dict[str, Any]:
        """
        실행 후 종합 검토

        LLM 호출: execution_review.txt

        Returns:
            {
                "goal_achievement": float,
                "overall_quality": float,
                "missing_information": [...],
                "proceed_to_aggregation": bool,
                "confidence_in_results": float
            }
        """
        logger.info("[ExecutionOrchestrator] Reviewing overall execution")

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="execution_review",
                variables={
                    "query": query,
                    "original_plan": original_plan,
                    "executed_teams": executed_teams,
                    "team_results": self._summarize_results(team_results),
                    "quality_scores": quality_scores,
                    "strategy_adjustments": strategy_adjustments,
                    "total_execution_time": total_execution_time
                },
                temperature=0.2,
                max_tokens=900
            )

            # 결정 기록
            self._log_decision("post_execution", result)

            return result

        except Exception as e:
            logger.error(f"Execution review failed: {e}")
            # Fallback: 진행 승인
            return {
                "goal_achievement": 0.7,
                "overall_quality": 0.7,
                "proceed_to_aggregation": True
            }

    def _log_decision(self, phase: str, decision: Dict[str, Any]):
        """결정 기록"""
        self.llm_call_count += 1
        self.decision_history.append(
            OrchestrationDecision(
                phase=phase,
                decision=decision,
                reasoning=decision.get("reasoning", ""),
                llm_call_number=self.llm_call_count
            )
        )
        logger.info(
            f"[ExecutionOrchestrator] Decision logged: {phase}, "
            f"LLM call #{self.llm_call_count}"
        )

    def _summarize_result(self, result: Any) -> Dict[str, Any]:
        """단일 결과 요약"""
        if not isinstance(result, dict):
            return {"data": str(result)[:200]}

        return {
            "count": len(result.get("data", [])) if "data" in result else 0,
            "status": result.get("status", "unknown"),
            "summary": str(result)[:200]
        }

    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """여러 결과 요약"""
        return {
            team: self._summarize_result(result)
            for team, result in results.items()
        }

    def get_orchestration_summary(self) -> str:
        """오케스트레이션 요약"""
        return f"Total LLM calls: {self.llm_call_count}, Decisions: {len(self.decision_history)}"
```

---

### Supervisor에서 사용 방법

**team_supervisor.py 수정 (최소 변경)**:

```python
# team_supervisor.py

from app.service_agent.cognitive_agents.execution_orchestrator import ExecutionOrchestrator

class TeamBasedSupervisor:

    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        # ... 기존 코드 ...

        # 새로 추가: Execution Orchestrator
        self.execution_orchestrator = ExecutionOrchestrator(llm_context=llm_context)

    async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        향상된 팀 실행 노드 (Orchestrator 활용)
        """
        logger.info("[TeamSupervisor] === Enhanced Execute Teams Node ===")

        state["current_phase"] = "executing"

        # 계획 정보 추출
        planning_state = state.get("planning_state", {})
        execution_steps = planning_state.get("execution_steps", [])

        if not execution_steps:
            logger.warning("No execution steps, skipping")
            return state

        # ========================================
        # Phase 1: Pre-Execution (새로 추가)
        # ========================================
        strategy_decision = await self.execution_orchestrator.decide_execution_strategy(
            query=state.get("query", ""),
            intent_type=planning_state.get("analyzed_intent", {}).get("intent_type", ""),
            confidence=planning_state.get("intent_confidence", 0.0),
            planned_teams=[
                {"team": step["team"], "estimated_time": step.get("estimated_time", 10.0)}
                for step in execution_steps
            ]
        )

        # 전략 적용
        execution_strategy = strategy_decision.get("strategy", "sequential")
        logger.info(f"[TeamSupervisor] Orchestrator decided strategy: {execution_strategy}")

        # ========================================
        # Phase 2: Team Execution Loop (수정)
        # ========================================
        active_teams = state.get("active_teams", [])

        for team_name in active_teams:
            logger.info(f"[TeamSupervisor] ======= Processing team: {team_name} =======")

            # Before Team: 도구 오케스트레이션 (새로 추가)
            tool_selection = await self.execution_orchestrator.orchestrate_tools(
                team_name=team_name,
                query=state.get("query", ""),
                used_tools=[],  # 추적 필요
                available_tools=list(self._get_tool_registry().keys()),
                tool_registry=self._get_tool_registry(),
                previous_results=state.get("team_results", {})
            )

            # Team 실행 (도구 선택 전달)
            team_result = await self._execute_single_team_with_orchestration(
                team_name=team_name,
                state=state,
                tool_selection=tool_selection
            )

            state["team_results"][team_name] = team_result

            # After Team: 결과 분석 (새로 추가)
            analysis = await self.execution_orchestrator.analyze_team_result(
                team_name=team_name,
                team_result=team_result,
                tools_used=team_result.get("sources_used", []),
                execution_time=team_result.get("execution_time", 0.0),
                query=state.get("query", ""),
                original_plan=state.get("execution_plan", {}),
                remaining_teams=[t for t in active_teams if t != team_name],
                intermediate_results=state.get("team_results", {})
            )

            # 조기 종료 판단
            if analysis.get("next_action") == "early_exit":
                logger.info(f"[TeamSupervisor] Early exit: {analysis.get('reasoning')}")
                break

        # ========================================
        # Phase 3: Post-Execution (새로 추가)
        # ========================================
        review = await self.execution_orchestrator.review_execution(
            query=state.get("query", ""),
            original_plan=state.get("execution_plan", {}),
            executed_teams=list(state.get("team_results", {}).keys()),
            team_results=state.get("team_results", {}),
            quality_scores={},  # Orchestrator가 추적
            strategy_adjustments=[],
            total_execution_time=0.0  # 계산 필요
        )

        # 검토 결과 저장
        state["execution_review"] = review

        logger.info(f"[TeamSupervisor] Orchestration summary: {self.execution_orchestrator.get_orchestration_summary()}")

        return state

    async def _execute_single_team_with_orchestration(
        self,
        team_name: str,
        state: MainSupervisorState,
        tool_selection: Dict[str, Any]
    ) -> Any:
        """도구 오케스트레이션을 반영한 팀 실행"""
        team = self.teams[team_name]
        shared_state = StateManager.create_shared_state(
            query=state["query"],
            session_id=state["session_id"]
        )

        if team_name == "search":
            # SearchExecutor에 도구 선택 전달
            return await team.execute_with_orchestration(shared_state, tool_selection)

        elif team_name == "analysis":
            # AnalysisExecutor에 이전 결과 + 도구 선택 전달
            return await team.execute_with_context(
                shared_state,
                tool_selection,
                state.get("team_results", {})
            )

        elif team_name == "document":
            return await team.execute(shared_state)

        return {"status": "skipped"}

    def _get_tool_registry(self) -> Dict[str, Any]:
        """전역 도구 레지스트리 구축"""
        return {
            "legal_search": {
                "team": "search",
                "cost": "medium",
                "avg_time": 2.5,
                "quality": 0.9
            },
            "market_data": {
                "team": "search",
                "cost": "low",
                "avg_time": 1.5,
                "quality": 0.85
            },
            # ... 나머지 도구들
        }
```

---

## 📊 Option 비교

### Option A: ExecutionOrchestrator (cognitive_agents) ✅ **권장**

**장점**:
- ✅ 역할 명확: "어떻게 조율할지" 결정 → Cognitive
- ✅ 기존 구조 최대 보존: Supervisor는 루프만 관리
- ✅ 테스트 용이: 독립 에이전트로 단위 테스트 가능
- ✅ 재사용 가능: 다른 Supervisor도 활용 가능
- ✅ 계획-실행 분리 명확: Planning → Orchestration → Execution

**단점**:
- ⚠️ 파일 1개 추가 (cognitive_agents/execution_orchestrator.py)
- ⚠️ Supervisor와의 통신 오버헤드 (미미함)

### Option B: Supervisor 내부에 메서드 추가

**장점**:
- ✅ 파일 추가 없음
- ✅ Supervisor 내부에서 모든 처리

**단점**:
- ❌ Supervisor 파일 비대화 (1,200줄 → 1,800줄+)
- ❌ 역할 혼재: Supervisor가 조율 + 의사결정 둘 다
- ❌ 테스트 어려움: Supervisor 전체를 테스트해야 함
- ❌ 재사용 불가: 다른 곳에서 활용 못함

### Option C: execution_agents에 추가

**장점**:
- ✅ execution 폴더에 있어 직관적

**단점**:
- ❌ 역할 불일치: execution_agents는 "실행"만, Orchestrator는 "결정"
- ❌ 계층 구조 혼란: Executor들과 동급이 아님 (상위 조율자)

---

## 🎯 최종 권장 사항

### ✅ ExecutionOrchestrator를 cognitive_agents에 추가

**파일 위치**:
```
backend/app/service_agent/cognitive_agents/execution_orchestrator.py
```

**이유**:
1. **역할의 본질**: 실행 전략 "결정" → Cognitive 영역
2. **아키텍처 일관성**: Planning (사전 계획) ↔ Orchestration (실행 중 조정)
3. **독립성**: Supervisor와 분리하여 테스트 및 재사용 용이
4. **확장성**: 향후 다른 Supervisor나 시스템에서도 활용 가능

### 구현 단계

1. **Phase 1**: `execution_orchestrator.py` 생성
   - 4개 메서드 구현 (decide_strategy, orchestrate_tools, analyze_result, review)
   - 프롬프트 파일 4개 추가 (execution/)

2. **Phase 2**: `team_supervisor.py` 수정 (최소 변경)
   - Orchestrator 초기화
   - `execute_teams_node`에서 Orchestrator 호출
   - 기존 로직 유지

3. **Phase 3**: Executor 강화
   - `execute_with_orchestration` 메서드 추가
   - 도구 선택 반영

---

## 📈 예상 효과

### 코드 변경 최소화

| 파일 | 변경 유형 | 변경 라인 수 |
|------|----------|-------------|
| `execution_orchestrator.py` | **신규 추가** | ~400줄 |
| `team_supervisor.py` | 수정 (Orchestrator 호출) | +50줄 |
| `search_executor.py` | 메서드 추가 | +80줄 |
| `analysis_executor.py` | 메서드 추가 | +60줄 |
| **총계** | | ~590줄 |

vs. Supervisor 내부 구현:
- `team_supervisor.py` 수정: +600줄 (기존 1,200줄 → 1,800줄)

### 유지보수성 향상

- ✅ 각 컴포넌트 독립 테스트 가능
- ✅ Orchestrator만 수정으로 로직 변경
- ✅ Supervisor는 루프 관리에만 집중

---

## 📝 결론

**ExecutionOrchestrator를 `cognitive_agents/`에 추가하는 것을 강력히 권장합니다.**

이 방식은:
- 기존 아키텍처를 최대한 보존하면서
- 새로운 기능을 독립적으로 추가하고
- 테스트 및 유지보수가 용이하며
- 향후 확장성도 보장합니다.

**다음 단계**: ExecutionOrchestrator 파일 구현 시작?

---

**작성자**: Claude
**검토 필요**: 백엔드 개발자, 시스템 아키텍트
**우선순위**: 높음
**상태**: 대안 분석 완료, 구현 대기
