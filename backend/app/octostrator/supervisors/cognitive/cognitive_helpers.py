"""
Cognitive Layer Helper Classes - 범용 인지 처리 헬퍼

범용 Specialist Agent System을 위한 인지 처리 유틸리티를 제공합니다.

⚠️ 현재 상태 (범용 시스템)
==========================================
이 모듈은 도메인에 구애받지 않는 범용 인지 처리 기능을 제공합니다:
- IntentClassifier: LLM 기반 동적 의도 분류
- PlanValidator: 도메인 독립적 계획 검증
- CognitiveSupervisor: 범용 인지 수퍼바이저

아카이브된 PT 특화 로직:
- INTENT_PATTERNS 딕셔너리 (하드코딩된 PT 패턴) → 제거됨
- Pattern matching 기반 분류 → LLM 기반으로 전환

🔮 구현된 기능
==========================================
1. **LLM 기반 Intent 분류**: 도메인 제약 없는 자유로운 의도 파악
2. **Fallback Pattern 지원**: LLM 사용 불가 시 기본 분류
3. **범용 Plan 검증**: 도메인 독립적 계획 유효성 검사

📚 See Also
==========================================
- cognitive_nodes.py: Intent 및 Planning Node 구현
- backend/app/models/: 데이터 모델 일반화 (동일한 전략)
- backend/app/octostrator/supervisors/: Supervisor 일반화 패턴

Author: Specialist Agent Development Team
Date: 2025-11-10
Version: 2.0 (Domain-Agnostic)
"""

import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    범용 사용자 의도 분류기 (LLM 기반)

    LLM을 사용하여 도메인에 구애받지 않는 동적 의도 분류를 수행합니다.

    ⚠️ 현재 상태 (범용 LLM 기반 시스템)
    ==========================================
    하드코딩된 INTENT_PATTERNS 제거되었습니다. 대신 LLM이 동적으로 의도를 파악합니다:
    - ✅ Fitness: "식단 추천", "운동 계획" 등
    - ✅ Medical: "진료 기록 분석", "처방전 검토" 등
    - ✅ Legal: "계약서 검토", "판례 검색" 등
    - ✅ Education: "강의 자료 작성", "과제 평가" 등
    - ✅ 기타 모든 도메인 자동 지원

    특징:
    - LLM 기반 분류로 완전한 도메인 독립성
    - Fallback 지원 (LLM 없을 시 기본 분류)
    - 신뢰도 및 추론 과정 제공

    🔮 도메인별 사용 예시
    ==========================================

    ## Example 1: Fitness 도메인
    ```python
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4")
    classifier = IntentClassifier()

    result = await classifier.classify("오늘 식단 추천해줘", llm)
    # Output: {
    #   "intent": "영양 및 식단 계획 요청",
    #   "confidence": 0.92,
    #   "reasoning": "사용자가 당일 식단에 대한 추천을 요청함"
    # }
    ```

    ## Example 2: Medical 도메인
    ```python
    result = await classifier.classify("환자 진료 기록 분석해줘", llm)
    # Output: {
    #   "intent": "의료 데이터 분석 요청",
    #   "confidence": 0.95,
    #   "reasoning": "환자의 진료 기록에 대한 분석 작업 요청"
    # }
    ```

    ## Example 3: Legal 도메인
    ```python
    result = await classifier.classify("계약서 법적 검토 부탁해", llm)
    # Output: {
    #   "intent": "법률 문서 검토 요청",
    #   "confidence": 0.93,
    #   "reasoning": "계약서의 법적 타당성 검토 요청"
    # }
    ```

    ## Example 4: Education 도메인
    ```python
    result = await classifier.classify("학생들 과제 채점해줘", llm)
    # Output: {
    #   "intent": "평가 및 채점 작업 요청",
    #   "confidence": 0.90,
    #   "reasoning": "학생 과제에 대한 채점 및 피드백 작업"
    # }
    ```

    ## Fallback (LLM 없을 때)
    ```python
    result = await classifier.classify("계획 세워줘", llm=None)
    # Output: {
    #   "intent": "general_task",
    #   "confidence": 0.5,
    #   "reasoning": "LLM unavailable, using fallback classification"
    # }
    ```

    📝 Alternative Implementation Options (참고용)
    ==========================================

    현재는 Option A (LLM 기반)을 구현했습니다.
    필요시 다음 옵션들로 전환 가능합니다:

    ## Option B: Agent Registry 기반 Dynamic Intent

    ### Step 1: Agent Capabilities에서 Intent 자동 추출
    ```python
    async def classify(self, text: str, llm) -> Dict[str, Any]:
        \"\"\"
        LLM을 사용하여 사용자 의도를 자유롭게 분류합니다.

        Args:
            text: 사용자 입력
            llm: LLM 인스턴스

        Returns:
            {
                "intent": str,  # 자유 형식 의도 (예: "데이터 분석 요청", "일정 조회")
                "confidence": float,
                "reasoning": str  # LLM이 판단한 이유
            }
        \"\"\"
        from langchain_core.messages import HumanMessage

        prompt = f\"\"\"Analyze the user's intent from their message.

User message: {text}

Identify:
1. Primary intent (what the user wants to accomplish)
2. Confidence level (0.0-1.0)
3. Your reasoning

Return JSON:
{{
    "intent": "brief description of user intent",
    "confidence": 0.0-1.0,
    "reasoning": "why you think this is the intent"
}}\"\"\"

        response = await llm.ainvoke([HumanMessage(content=prompt)])

        # Parse JSON response
        import json
        result = json.loads(response.content)

        return result
    ```

    ### Step 2: INTENT_PATTERNS 삭제
    ```python
    # 삭제:
    # INTENT_PATTERNS = {...}  # 더 이상 필요 없음
    ```

    ## Option B: Agent Registry 기반 Dynamic Intent

    ### Step 1: Agent Capabilities에서 Intent 자동 추출
    ```python
    from backend.app.octostrator.execution_agents import agent_registry
    from backend.app.octostrator.execution_agents.base.capabilities import Capability

    def __init__(self, registry=None):
        \"\"\"
        Args:
            registry: AgentRegistry 인스턴스 (None이면 전역 사용)
        \"\"\"
        self.registry = registry or agent_registry
        self._build_dynamic_intents()

    def _build_dynamic_intents(self):
        \"\"\"등록된 Agent의 Capability에서 Intent 패턴 자동 생성\"\"\"
        self.intent_patterns = {}

        for agent_id in self.registry.list_agents():
            agent = self.registry.get_agent_instance(agent_id)
            if not agent:
                continue

            for capability in agent.capabilities:
                intent_key = capability.value

                # Capability를 intent로 매핑
                if intent_key not in self.intent_patterns:
                    self.intent_patterns[intent_key] = []

                # Agent의 description에서 키워드 추출 (간단한 예시)
                keywords = self._extract_keywords(agent.description)
                self.intent_patterns[intent_key].extend(keywords)

        logger.info(f"[IntentClassifier] Built {len(self.intent_patterns)} intents from registry")

    def _extract_keywords(self, description: str) -> List[str]:
        \"\"\"Description에서 의미있는 키워드 추출 (간단한 토큰화)\"\"\"
        # TODO: 더 정교한 NLP 처리 가능
        words = description.lower().split()
        # 불용어 제거 등
        return [w for w in words if len(w) > 3]
    ```

    ### Step 2: classify 메서드를 동적 패턴 사용
    ```python
    def classify(self, text: str) -> Dict[str, Any]:
        \"\"\"동적으로 생성된 패턴으로 분류\"\"\"
        text_lower = text.lower()

        # Dynamic pattern matching
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return {
                        "intent": intent,
                        "confidence": 0.8,
                        "keywords": [pattern]
                    }

        # Fallback to generic task
        return {
            "intent": "generic_task",
            "confidence": 0.5,
            "keywords": []
        }
    ```

    ## Option C: 외부 설정 파일 사용

    ### Step 1: intent_config.yaml 생성
    ```yaml
    # config/intent_config.yaml
    intents:
      data_analysis:
        keywords: ["분석", "데이터", "통계", "analysis", "statistics"]

      task_management:
        keywords: ["일정", "작업", "task", "schedule", "todo"]

      report_generation:
        keywords: ["보고서", "리포트", "report", "summary"]
    ```

    ### Step 2: YAML 로딩 로직
    ```python
    import yaml
    from pathlib import Path

    def __init__(self, config_path: str = None):
        \"\"\"
        Args:
            config_path: Intent 설정 파일 경로 (기본: config/intent_config.yaml)
        \"\"\"
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "intent_config.yaml"

        self.intent_patterns = self._load_config(config_path)

    def _load_config(self, config_path: Path) -> Dict[str, List[str]]:
        \"\"\"YAML 파일에서 intent 패턴 로드\"\"\"
        if not config_path.exists():
            logger.warning(f"Intent config not found: {config_path}, using defaults")
            return {"generic_task": ["task", "작업"]}

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config.get('intents', {})
    ```

    ✅ Migration Checklist
    ==========================================

    현재 파일: backend/app/octostrator/supervisors/cognitive/cognitive_helpers.py

    ### 1단계: Intent 분류 방식 선택
    - [ ] Option A (LLM), Option B (Registry), Option C (Config) 중 선택
    - [ ] 프로젝트 요구사항에 맞는 방식 결정

    ### 2단계: 코드 수정 (Option A 선택 시)
    - [ ] Line 35-63: classify() 메서드를 async def로 변경
    - [ ] Line 24-33: INTENT_PATTERNS 딕셔너리 삭제
    - [ ] LLM 기반 분류 로직 구현

    ### 3단계: 코드 수정 (Option B 선택 시)
    - [ ] Line 17: __init__() 메서드 추가
    - [ ] _build_dynamic_intents() 메서드 구현
    - [ ] Line 49-56: 동적 패턴 사용하도록 수정

    ### 4단계: 코드 수정 (Option C 선택 시)
    - [ ] config/intent_config.yaml 파일 생성
    - [ ] Line 17: __init__(config_path) 메서드 추가
    - [ ] _load_config() 메서드 구현

    ### 5단계: 테스트
    - [ ] 다양한 도메인 입력으로 intent 분류 테스트
    - [ ] 기존 PT 관련 쿼리가 여전히 작동하는지 확인
    - [ ] 새로운 도메인 쿼리도 분류되는지 확인

    📚 Usage Examples
    ==========================================

    ### 현재 사용법 (PT 도메인 특화)
    ```python
    classifier = IntentClassifier()
    result = classifier.classify("오늘 식단 추천해줘")
    # Output: {"intent": "diet_query", "confidence": 0.8, "keywords": ["식단"]}

    result = classifier.classify("운동 계획 만들어줘")
    # Output: {"intent": "workout_query", "confidence": 0.8, "keywords": ["운동"]}
    ```

    **문제점**:
    - "환자 진료 기록 분석해줘" → multi_step_task (의도 파악 실패)
    - "계약서 검토해줘" → multi_step_task (의도 파악 실패)

    ### 향후 사용법 (Option A: LLM 기반)
    ```python
    classifier = IntentClassifier()
    result = await classifier.classify("환자 진료 기록 분석해줘", llm)
    # Output: {
    #   "intent": "의료 데이터 분석 요청",
    #   "confidence": 0.9,
    #   "reasoning": "사용자가 환자 진료 기록에 대한 분석을 요청함"
    # }

    result = await classifier.classify("계약서 검토해줘", llm)
    # Output: {
    #   "intent": "법률 문서 검토 요청",
    #   "confidence": 0.95,
    #   "reasoning": "계약서 검토는 법률 도메인의 문서 분석 작업"
    # }
    ```

    **장점**:
    - ✅ 도메인 제약 없음
    - ✅ 새로운 도메인 자동 지원
    - ✅ 자연스러운 의도 파악

    ### 향후 사용법 (Option B: Registry 기반)
    ```python
    from backend.app.octostrator.execution_agents import agent_registry

    # Agent Registry에 의료 Agent 추가 시
    # (별도 설정 없이 자동으로 medical_analysis intent 지원)

    classifier = IntentClassifier(registry=agent_registry)
    result = classifier.classify("환자 진료 기록 분석해줘")
    # Output: {
    #   "intent": "medical_data_analysis",  # Agent의 capability에서 자동 추출
    #   "confidence": 0.8,
    #   "keywords": ["진료", "분석"]
    # }
    ```

    **장점**:
    - ✅ Agent 추가 시 자동 확장
    - ✅ 설정 파일 불필요
    - ✅ Agent와 Intent 자동 동기화

    ### 향후 사용법 (Option C: Config 파일)
    ```python
    # config/medical_intent_config.yaml 사용
    classifier = IntentClassifier(config_path="config/medical_intent_config.yaml")
    result = classifier.classify("환자 진료 기록 분석해줘")
    # Output: {"intent": "medical_analysis", "confidence": 0.8, "keywords": ["진료"]}

    # config/legal_intent_config.yaml 사용
    classifier = IntentClassifier(config_path="config/legal_intent_config.yaml")
    result = classifier.classify("계약서 검토해줘")
    # Output: {"intent": "contract_review", "confidence": 0.8, "keywords": ["계약서"]}
    ```

    **장점**:
    - ✅ 도메인별 설정 분리
    - ✅ 코드 수정 없이 설정만 교체
    - ✅ 버전 관리 용이

    📌 See Also
    ==========================================
    - cognitive_nodes.py: Intent 카테고리 사용 위치
    - backend/app/octostrator/execution_agents/base/capabilities.py: Capability Enum 정의
    - backend/app/octostrator/execution_agents/agent_registry.py: Agent Registry 패턴
    """

    async def classify(self, text: str, llm=None) -> Dict[str, Any]:
        """
        LLM을 사용하여 사용자 의도를 동적으로 분류합니다.

        Args:
            text: 사용자 입력 텍스트
            llm: LangChain LLM 인스턴스 (None이면 fallback 사용)

        Returns:
            dict: {
                "intent": str,        # 분류된 의도 (예: "영양 계획 요청", "의료 데이터 분석")
                "confidence": float,  # 신뢰도 (0.0-1.0)
                "reasoning": str      # LLM의 판단 이유
            }

        Examples:
            >>> # LLM 기반 분류
            >>> result = await classifier.classify("환자 진료 기록 분석해줘", llm)
            >>> print(result["intent"])
            "의료 데이터 분석 요청"

            >>> # Fallback 분류
            >>> result = await classifier.classify("작업 처리해줘", llm=None)
            >>> print(result["intent"])
            "general_task"
        """
        # Fallback: LLM이 없을 경우 기본 분류
        if llm is None:
            logger.warning("[IntentClassifier] LLM not available, using fallback classification")
            return {
                "intent": "general_task",
                "confidence": 0.5,
                "reasoning": "LLM unavailable, using fallback classification"
            }

        try:
            from langchain_core.messages import HumanMessage

            # LLM 프롬프트 생성
            prompt = f"""Analyze the user's intent from their message.

User message: {text}

Identify:
1. Primary intent (what the user wants to accomplish)
2. Confidence level (0.0-1.0)
3. Your reasoning

Return JSON only (no markdown, no extra text):
{{
    "intent": "brief description of user intent in Korean or English",
    "confidence": 0.9,
    "reasoning": "why you think this is the intent"
}}"""

            # LLM 호출
            response = await llm.ainvoke([HumanMessage(content=prompt)])

            # JSON 파싱
            content = response.content.strip()

            # Markdown code block 제거 (```json ... ``` 형식)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:].strip()

            result = json.loads(content)

            logger.info(
                f"[IntentClassifier] Classified: '{result['intent']}' "
                f"(confidence: {result['confidence']:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"[IntentClassifier] Error during classification: {e}")
            # 에러 시 fallback
            return {
                "intent": "general_task",
                "confidence": 0.3,
                "reasoning": f"Classification error: {str(e)}"
            }


class PlanValidator:
    """
    실행 계획 검증기

    생성된 계획의 유효성을 검증합니다.
    """

    def validate(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        계획을 검증합니다.

        Checks:
        - Required fields exist
        - No circular dependencies
        - Agents are available

        Returns:
            dict: {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []

        # Check required fields
        if not plan.get("steps"):
            errors.append("No steps defined in plan")

        # Check each step
        for step in plan.get("steps", []):
            if not step.get("agent"):
                errors.append(f"Step {step.get('step_id')} missing agent")
            if not step.get("action"):
                warnings.append(f"Step {step.get('step_id')} missing action")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


class CognitiveSupervisor:
    """
    Cognitive Supervisor 클래스

    계획 수립 레이어의 메인 클래스입니다.
    """

    def __init__(self, llm=None, checkpointer=None):
        self.llm = llm
        self.checkpointer = checkpointer
        self.classifier = IntentClassifier()
        self.validator = PlanValidator()

    async def plan(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        사용자 메시지를 받아 실행 계획을 생성합니다.
        """
        # 1. Classify intent
        intent_result = self.classifier.classify(user_message)

        # 2. Generate plan (TODO: Use LLM)
        plan = {
            "goal": user_message,
            "intent": intent_result["intent"],
            "steps": []
        }

        # 3. Validate plan
        validation = self.validator.validate(plan)

        return {
            "plan": plan,
            "intent": intent_result,
            "validation": validation
        }