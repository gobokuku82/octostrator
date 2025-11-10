"""
Cognitive Layer Nodes - 범용 인지 레이어

도메인에 구애받지 않는 범용 Intent Understanding 및 Planning 노드를 제공합니다.

⚠️ 현재 상태 (범용 시스템)
==========================================
이 모듈의 노드들은 모든 도메인에서 사용할 수 있도록 설계되었습니다:

**Intent Understanding**:
- LLM 기반 동적 intent 분류
- 하드코딩된 카테고리 없음
- 도메인 독립적 처리

**Planning**:
- 동적 agent 선택 (향후 구현)
- LLM 기반 계획 생성 (향후 구현)
- Multi-step plan 지원 (향후 구현)

🔮 도메인별 사용 예시
==========================================

## Fitness 도메인
```python
state = {
    "user_query": "오늘 운동 루틴 추천해줘",
    "llm": llm_instance
}
result = await intent_understanding_node(state)
# Output: {
#   "user_intent": "운동 프로그램 추천 요청",
#   "intent_confidence": 0.92,
#   "intent_reasoning": "사용자가 오늘 수행할 운동 루틴에 대한 추천을 요청함"
# }
```

## Medical 도메인
```python
state = {
    "user_query": "환자 진료 기록 분석해줘",
    "llm": llm_instance
}
result = await intent_understanding_node(state)
# Output: {
#   "user_intent": "의료 데이터 분석 요청",
#   "intent_confidence": 0.95,
#   "intent_reasoning": "환자의 진료 기록에 대한 분석을 요청함"
# }
```

## Legal 도메인
```python
state = {
    "user_query": "계약서 검토해줘",
    "llm": llm_instance
}
result = await intent_understanding_node(state)
# Output: {
#   "user_intent": "법률 문서 검토 요청",
#   "intent_confidence": 0.88,
#   "intent_reasoning": "계약서에 대한 법률적 검토를 요청함"
# }
```

## Education 도메인
```python
state = {
    "user_query": "학생 과제 평가해줘",
    "llm": llm_instance
}
result = await intent_understanding_node(state)
# Output: {
#   "user_intent": "교육 콘텐츠 평가 요청",
#   "intent_confidence": 0.90,
#   "intent_reasoning": "학생이 제출한 과제에 대한 평가를 요청함"
# }
```

📚 See Also
==========================================
- cognitive_helpers.py: LLM 기반 IntentClassifier 구현
- planning_node: Intent를 기반으로 계획 수립
- backend/app/octostrator/execution_agents/base/: Base Agent 패턴

Author: Specialist Agent Development Team
Date: 2025-11-10
Version: 2.0 (Domain-Agnostic)
"""

import logging
from typing import Dict, Any, List, Literal

from langchain_core.messages import HumanMessage, AIMessage
from .cognitive_helpers import IntentClassifier

logger = logging.getLogger(__name__)


# ====================================
# COGNITIVE NODES
# ====================================

async def intent_understanding_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intent Understanding Node - LLM 기반 동적 의도 분류

    사용자의 의도를 LLM을 통해 동적으로 파악합니다.
    도메인 제약 없이 다양한 의도를 처리할 수 있습니다.

    ⚠️ 현재 상태 (범용 시스템)
    ==========================================
    - LLM 기반 동적 intent 분류
    - 하드코딩된 카테고리 없음
    - 모든 도메인 지원 (Fitness, Medical, Legal, Education 등)

    🔮 작동 방식
    ==========================================

    1. **LLM 사용 가능**: IntentClassifier의 LLM 기반 분류 사용
       - 사용자 쿼리를 LLM에 전달
       - JSON 형식으로 intent, confidence, reasoning 반환
       - 도메인 독립적 처리

    2. **LLM 사용 불가**: Fallback 분류 사용
       - 기본 intent 반환 ("general_task")
       - 낮은 confidence (0.5)
       - 시스템은 계속 작동

    📝 구현 세부사항
    ==========================================

    ## IntentClassifier 통합

    ```python
    from .cognitive_helpers import IntentClassifier

    classifier = IntentClassifier()
    intent_result = await classifier.classify(user_query, llm)
    ```

    ## State 요구사항

    **필수**:
    - `user_query` (str): 사용자 입력 쿼리

    **선택적**:
    - `llm`: LangChain LLM 인스턴스 (없으면 fallback 사용)
    - `messages` (list): 대화 히스토리 (현재 미사용, 향후 context 활용 가능)

    ## Return Value

    ```python
    {
        "user_intent": str,           # 분류된 의도 (예: "운동 프로그램 추천 요청")
        "intent_confidence": float,   # 신뢰도 (0.0-1.0)
        "intent_reasoning": str       # LLM의 판단 이유 (LLM 사용 시)
    }
    ```

    📚 도메인별 사용 예시
    ==========================================

    ## Fitness 도메인
    ```python
    state = {
        "user_query": "오늘 운동 루틴 추천해줘",
        "llm": llm_instance
    }

    result = await intent_understanding_node(state)
    # Output: {
    #   "user_intent": "운동 프로그램 추천 요청",
    #   "intent_confidence": 0.92,
    #   "intent_reasoning": "사용자가 오늘 수행할 운동 루틴에 대한 추천을 요청함"
    # }
    ```

    ## Medical 도메인
    ```python
    state = {
        "user_query": "환자 진료 기록 분석해줘",
        "llm": llm_instance
    }

    result = await intent_understanding_node(state)
    # Output: {
    #   "user_intent": "의료 데이터 분석 요청",
    #   "intent_confidence": 0.95,
    #   "intent_reasoning": "환자의 진료 기록에 대한 분석을 요청함"
    # }
    ```

    ## Legal 도메인
    ```python
    state = {
        "user_query": "계약서 검토해줘",
        "llm": llm_instance
    }

    result = await intent_understanding_node(state)
    # Output: {
    #   "user_intent": "법률 문서 검토 요청",
    #   "intent_confidence": 0.88,
    #   "intent_reasoning": "계약서에 대한 법률적 검토를 요청함"
    # }
    ```

    ## Education 도메인
    ```python
    state = {
        "user_query": "학생 과제 평가해줘",
        "llm": llm_instance
    }

    result = await intent_understanding_node(state)
    # Output: {
    #   "user_intent": "교육 콘텐츠 평가 요청",
    #   "intent_confidence": 0.90,
    #   "intent_reasoning": "학생이 제출한 과제에 대한 평가를 요청함"
    # }
    ```

    ## Fallback (LLM 없을 때)
    ```python
    state = {
        "user_query": "도와줘",
        # llm 없음
    }

    result = await intent_understanding_node(state)
    # Output: {
    #   "user_intent": "general_task",
    #   "intent_confidence": 0.5,
    #   "intent_reasoning": "LLM unavailable, using fallback classification"
    # }
    ```

    🔄 향후 확장 가능성
    ==========================================

    ### Option A: Registry 기반 분류 추가

    Agent Registry의 capabilities를 활용하여 분류:

    ```python
    from backend.app.octostrator.execution_agents import agent_registry

    # Registry 기반 분류기 사용
    classifier = IntentClassifier(registry=agent_registry)
    intent_result = await classifier.classify_with_registry(user_query)
    ```

    ### Option B: Conversation Context 활용

    대화 히스토리를 활용한 context-aware 분류:

    ```python
    messages = state.get("messages", [])

    # Context를 포함한 분류
    intent_result = await classifier.classify_with_context(
        user_query,
        llm,
        context=messages
    )
    ```

    ### Option C: Multi-Intent 지원

    하나의 쿼리에서 여러 의도 감지:

    ```python
    # "환자 진료 기록 분석하고 보고서 생성해줘"
    intent_result = await classifier.classify_multi_intent(user_query, llm)
    # Output: {
    #   "intents": [
    #       {"intent": "의료 데이터 분석", "confidence": 0.95},
    #       {"intent": "보고서 생성", "confidence": 0.92}
    #   ]
    # }
    ```

    ⚠️ Error Handling
    ==========================================

    - **LLM 없음**: Fallback으로 "general_task" 반환 (confidence 0.5)
    - **LLM 오류**: Exception 발생 시 fallback으로 처리
    - **JSON 파싱 오류**: IntentClassifier 내부에서 처리
    - **빈 쿼리**: 빈 문자열도 정상 처리 (LLM이 판단)

    📌 See Also
    ==========================================
    - cognitive_helpers.py: IntentClassifier 구현 (LLM 기반 분류 로직)
    - planning_node: Intent를 기반으로 실행 계획 수립
    - backend/app/octostrator/execution_agents/base/: Base Agent 패턴

    Args:
        state: LangGraph state dictionary
            - user_query (str): 사용자 입력 쿼리 (필수)
            - llm: LangChain LLM 인스턴스 (선택적)
            - messages (list): 대화 히스토리 (선택적)

    Returns:
        dict: Intent 분류 결과
            - user_intent (str): 분류된 의도
            - intent_confidence (float): 신뢰도 (0.0-1.0)
            - intent_reasoning (str): LLM의 판단 이유

    Raises:
        Exception: 치명적 오류 발생 시 (로깅 후 error 키 반환)
    """
    try:
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])

        # Context에서 LLM 가져오기
        llm = state.get("llm")  # LLM이 없으면 fallback 사용

        logger.info(f"[Intent] Analyzing: {user_query[:50]}...")

        # LLM 기반 IntentClassifier 사용
        classifier = IntentClassifier()
        intent_result = await classifier.classify(user_query, llm)

        logger.info(
            f"[Intent] Classified: '{intent_result['intent']}' "
            f"(confidence: {intent_result['confidence']:.2f})"
        )

        return {
            "user_intent": intent_result["intent"],
            "intent_confidence": intent_result["confidence"],
            "intent_reasoning": intent_result.get("reasoning", "")
        }

    except Exception as e:
        logger.error(f"[Intent] Error: {e}")
        return {"error": str(e)}


async def planning_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planning Node - LLM 기반 동적 계획 수립

    사용자 의도와 사용 가능한 Agent를 기반으로 실행 계획을 동적으로 생성합니다.

    ⚠️ 현재 상태 (범용 시스템)
    ==========================================
    - LLM 기반 동적 계획 수립
    - 하드코딩된 agent 없음 (이전의 "diet_agent" 제거됨)
    - 모든 도메인 지원 (Fitness, Medical, Legal, Education 등)

    🔮 작동 방식
    ==========================================

    **현재 구현** (Simple Fallback):
    1. LLM이 없거나 Agent Registry가 없는 경우
    2. 기본 계획 반환 (단일 step, general_agent)
    3. 시스템은 계속 작동

    **향후 구현** (LLM 기반 동적 계획):
    1. LLM을 사용하여 사용자 쿼리 분석
    2. 사용 가능한 Agent 목록 조회 (Agent Registry)
    3. LLM이 적합한 Agent 선택 및 계획 생성
    4. Multi-step 계획 지원 (복잡한 작업 분해)

    📝 구현 세부사항
    ==========================================

    ## State 요구사항

    **필수**:
    - `user_query` (str): 사용자 입력 쿼리
    - `user_intent` (str): Intent Understanding에서 분류된 의도

    **선택적**:
    - `llm`: LangChain LLM 인스턴스 (향후 구현에서 사용)

    ## Return Value

    ```python
    {
        "plan": {
            "goal": str,              # 사용자의 목표
            "intent": str,            # 분류된 의도
            "steps": [                # 실행 단계 목록
                {
                    "step_id": str,   # 단계 ID (step_1, step_2, ...)
                    "agent": str,     # 실행할 Agent ID
                    "action": str,    # Agent가 수행할 작업
                    "params": dict,   # 추가 파라미터
                    "dependencies": list  # 의존하는 이전 단계 ID
                }
            ]
        },
        "is_planning": bool           # 계획 수립 완료 여부
    }
    ```

    📚 도메인별 사용 예시 (향후 LLM 기반 구현)
    ==========================================

    ## Fitness 도메인
    ```python
    state = {
        "user_intent": "운동 프로그램 추천 요청",
        "user_query": "오늘 운동 루틴 추천해줘",
        "llm": llm_instance
    }

    result = await planning_node(state)
    # 향후 Output (LLM 기반):
    # {
    #   "plan": {
    #       "goal": "오늘 운동 루틴 추천해줘",
    #       "intent": "운동 프로그램 추천 요청",
    #       "steps": [
    #           {
    #               "step_id": "step_1",
    #               "agent": "fitness_program_agent",
    #               "action": "recommend_workout_routine",
    #               "params": {"timeframe": "today"},
    #               "dependencies": []
    #           }
    #       ]
    #   },
    #   "is_planning": False
    # }
    ```

    ## Medical 도메인
    ```python
    state = {
        "user_intent": "의료 데이터 분석 요청",
        "user_query": "환자 진료 기록 분석해줘",
        "llm": llm_instance
    }

    result = await planning_node(state)
    # 향후 Output (Multi-step):
    # {
    #   "plan": {
    #       "goal": "환자 진료 기록 분석해줘",
    #       "steps": [
    #           {
    #               "step_id": "step_1",
    #               "agent": "medical_data_agent",
    #               "action": "analyze_medical_records",
    #               "params": {"data_type": "진료기록"},
    #               "dependencies": []
    #           },
    #           {
    #               "step_id": "step_2",
    #               "agent": "report_generator_agent",
    #               "action": "generate_summary",
    #               "params": {},
    #               "dependencies": ["step_1"]
    #           }
    #       ]
    #   },
    #   "is_planning": False
    # }
    ```

    ## Legal 도메인
    ```python
    state = {
        "user_intent": "법률 문서 검토 요청",
        "user_query": "계약서 검토해줘",
        "llm": llm_instance
    }

    result = await planning_node(state)
    # 향후 Output:
    # {
    #   "plan": {
    #       "goal": "계약서 검토해줘",
    #       "steps": [
    #           {
    #               "step_id": "step_1",
    #               "agent": "legal_document_agent",
    #               "action": "review_contract",
    #               "params": {"query": "계약서 검토해줘"},
    #               "dependencies": []
    #           }
    #       ]
    #   },
    #   "is_planning": False
    # }
    ```

    ## Education 도메인
    ```python
    state = {
        "user_intent": "교육 콘텐츠 평가 요청",
        "user_query": "학생 과제 평가해줘",
        "llm": llm_instance
    }

    result = await planning_node(state)
    # 향후 Output:
    # {
    #   "plan": {
    #       "goal": "학생 과제 평가해줘",
    #       "steps": [
    #           {
    #               "step_id": "step_1",
    #               "agent": "education_assessment_agent",
    #               "action": "evaluate_assignment",
    #               "params": {},
    #               "dependencies": []
    #           }
    #       ]
    #   },
    #   "is_planning": False
    # }
    ```

    🔄 향후 구현 옵션
    ==========================================

    ### Option A: LLM 기반 동적 계획 생성

    ```python
    import json
    from langchain_core.messages import HumanMessage

    async def planning_node(state: Dict[str, Any]) -> Dict[str, Any]:
        llm = state.get("llm")
        user_intent = state.get("user_intent", "")
        user_query = state.get("user_query", "")

        # Agent Registry에서 사용 가능한 Agent 조회
        # available_agents = agent_registry.list_agents()
        # agents_info = [...]

        prompt = f\"\"\"Create an execution plan.

User Intent: {user_intent}
User Query: {user_query}

Available Agents: [agent1, agent2, ...]

Return JSON with goal, intent, and steps.\"\"\"

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        plan = json.loads(response.content)

        return {"plan": plan, "is_planning": False}
    ```

    ### Option B: Capability 기반 Agent 선택

    ```python
    from backend.app.octostrator.execution_agents.base.capabilities import CapabilityBasedRouter

    async def planning_node(state: Dict[str, Any]) -> Dict[str, Any]:
        router = CapabilityBasedRouter(agent_registry)

        # Intent를 Capability로 변환
        required_capability = intent_to_capability(state.get("user_intent"))

        # Capability에 맞는 Agent 선택
        selected_agent = router.find_best_agent(required_capability)

        plan = {
            "goal": state.get("user_query"),
            "steps": [{
                "step_id": "step_1",
                "agent": selected_agent,
                "action": "analyze_and_execute",
                "params": {},
                "dependencies": []
            }]
        }

        return {"plan": plan, "is_planning": False}
    ```

    ### Option C: 혼합 방식 (LLM + Capability)

    복잡한 작업은 LLM으로 분해하고, 각 단계마다 Capability 기반으로 Agent 선택.

    ⚠️ 현재 구현 (Fallback)
    ==========================================

    현재는 단순한 fallback 계획을 반환합니다:
    - Agent: "general_agent" (기본값)
    - Action: "analyze_and_execute"
    - Single-step plan

    향후 LLM 기반 또는 Capability 기반 구현으로 교체될 예정입니다.

    📌 See Also
    ==========================================
    - intent_understanding_node: Intent 분류 결과 활용
    - validator_node: 생성된 계획 검증 (향후 구현)
    - backend/app/octostrator/execution_agents/: Agent 구현

    Args:
        state: LangGraph state dictionary
            - user_intent (str): 분류된 의도 (필수)
            - user_query (str): 사용자 쿼리 (필수)
            - llm: LLM 인스턴스 (선택적, 향후 사용)

    Returns:
        dict: 실행 계획
            - plan (dict): 단계별 실행 계획
            - is_planning (bool): 계획 수립 완료 (항상 False)

    Raises:
        Exception: 치명적 오류 발생 시 (로깅 후 error 키 반환)
    """
    try:
        user_intent = state.get("user_intent", "")
        user_query = state.get("user_query", "")

        # 현재는 간단한 fallback plan 생성
        # 향후 LLM 기반 동적 계획 생성으로 교체 예정
        # TODO: Implement LLM-based planning with Agent Registry

        plan = {
            "goal": user_query,
            "intent": user_intent,
            "steps": [
                {
                    "step_id": "step_1",
                    "agent": "general_agent",  # 범용 agent (하드코딩된 "diet_agent" 제거됨)
                    "action": "analyze_and_execute",
                    "params": {"query": user_query},
                    "dependencies": []
                }
            ]
        }

        logger.info(f"[Planning] Generated plan with {len(plan['steps'])} step(s)")

        return {
            "plan": plan,
            "is_planning": False
        }

    except Exception as e:
        logger.error(f"[Planning] Error: {e}")
        return {"error": str(e)}


async def validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validator Node

    생성된 계획의 유효성을 검증합니다.

    Checks:
    - Agent availability
    - Dependency cycles
    - Resource constraints
    """
    try:
        plan = state.get("plan", {})

        # TODO: Implement validation logic
        # For now, always valid

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        logger.info(f"[Validator] Plan validation: {validation_result['valid']}")

        return {
            "validation_result": validation_result,
            "plan_valid": validation_result["valid"]
        }

    except Exception as e:
        logger.error(f"[Validator] Error: {e}")
        return {"error": str(e)}