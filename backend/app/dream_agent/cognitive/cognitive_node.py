"""Cognitive Layer - 의도 파악 노드

Phase 1 고도화:
- IntentClassifier: 3-depth 계층적 Intent 분류
- EntityExtractor: 정교한 엔티티 추출
- DialogueManager: 멀티턴 대화 관리
"""

import json
from typing import Dict, Any, Optional

from backend.app.core.logging import get_logger, LogContext
from backend.app.dream_agent.states.accessors import (
    get_user_input,
    get_current_context,
    get_session_id,
)
from backend.app.dream_agent.llm_manager import (
    get_llm_client,
    COGNITIVE_SYSTEM_PROMPT,
    format_cognitive_prompt,
    agent_config,
)

# Phase 1 components (optional - fallback to legacy if not available)
try:
    from .intent_classifier import IntentClassifier, HierarchicalIntent
    from .entity_extractor import EntityExtractor, format_entities_for_planning
    from .dialogue_manager import DialogueManager
    PHASE1_AVAILABLE = True
except ImportError:
    PHASE1_AVAILABLE = False

logger = get_logger(__name__)

# Feature flag for Phase 1 components
USE_PHASE1_COMPONENTS = PHASE1_AVAILABLE


def _get_config_based_intent(
    user_input: str,
    confidence: float,
    summary: str,
    error: str = None
) -> Dict[str, Any]:
    """
    Config 기반 fallback intent 생성

    LLM 호출 실패 시 키워드 기반으로 intent를 파악합니다.
    중복 코드 제거를 위한 공통 함수.

    Args:
        user_input: 사용자 입력 텍스트
        confidence: intent confidence (0.0~1.0)
        summary: intent summary 텍스트
        error: 에러 메시지 (optional)

    Returns:
        Intent dict
    """
    # Config 기반 키워드 의도 파악
    intent_result = agent_config.detect_intent_type(user_input, "ko")
    requires_ml = intent_result["requires_ml"]
    requires_biz = intent_result["requires_biz"]

    # 데이터 소스 추출 (Config 기반)
    data_sources = agent_config.detect_sources_from_text(user_input, "ko")

    # 소스가 명시되지 않았고 ML이 필요하면 기본 소스 사용
    if requires_ml and not data_sources:
        data_sources = agent_config.get_default_sources()

    intent = {
        "intent_type": intent_result["intent_type"],
        "confidence": confidence,
        "requires_ml": requires_ml,
        "requires_biz": requires_biz,
        "summary": summary,
        "extracted_entities": {
            "data_sources": data_sources
        }
    }

    if error:
        intent["error"] = error

    return intent


async def cognitive_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cognitive Layer - 의도 파악

    Phase 1 고도화:
    - 3-depth 계층적 Intent 분류 (Domain → Category → Subcategory)
    - 정교한 엔티티 추출 (validation + normalization)
    - 멀티턴 대화 컨텍스트 관리

    Args:
        state: AgentState

    Returns:
        Dict with 'intent', 'current_context', and optionally 'dialogue_context'
    """
    log = LogContext(logger, node="cognitive")
    user_input = get_user_input(state)
    current_context = get_current_context(state)
    session_id = get_session_id(state) or "default"

    log.info(f"Starting cognitive analysis for input: '{user_input[:50]}...'")

    # Use Phase 1 components if available
    if USE_PHASE1_COMPONENTS:
        log.info("Using Phase 1 enhanced components")
        return await _cognitive_node_v2(state, log)
    else:
        # Fallback to legacy implementation
        log.info("Using legacy cognitive implementation")
        return await _cognitive_node_legacy(state, log)


async def _cognitive_node_v2(state: Dict[str, Any], log: LogContext) -> Dict[str, Any]:
    """Phase 1 고도화 버전"""

    user_input = get_user_input(state)
    session_id = get_session_id(state) or "default"
    dialogue_context_dict = state.get("dialogue_context")  # No accessor available

    # Initialize or restore DialogueManager
    if dialogue_context_dict:
        dialogue_manager = DialogueManager(session_id=session_id)
        dialogue_manager.from_dict(dialogue_context_dict)
        log.debug("Restored DialogueManager from state")
    else:
        dialogue_manager = DialogueManager(session_id=session_id)
        log.debug("Created new DialogueManager")

    try:
        # Step 1: 3-depth Hierarchical Intent Classification
        log.debug("Classifying intent with 3-depth hierarchy")
        intent_classifier = IntentClassifier()

        # Get LLM context from dialogue history
        llm_context_str = dialogue_manager.get_context_for_llm()
        context_dict = {"dialogue_summary": llm_context_str} if llm_context_str else None

        hierarchical_intent: HierarchicalIntent = await intent_classifier.classify(
            user_input=user_input,
            context=context_dict
        )

        log.info(
            f"Intent classified: {hierarchical_intent.domain}.{hierarchical_intent.category}"
            f".{hierarchical_intent.subcategory} (confidence: {hierarchical_intent.overall_confidence:.2f})"
        )

        # Step 2: Enhanced Entity Extraction
        log.debug("Extracting entities")
        entity_extractor = EntityExtractor()

        intent_dict = {
            "domain": hierarchical_intent.domain.value,
            "category": hierarchical_intent.category.value,
            "subcategory": hierarchical_intent.subcategory.value if hierarchical_intent.subcategory else None,
            "confidence": hierarchical_intent.overall_confidence
        }

        extracted_entities = await entity_extractor.extract(
            user_input=user_input,
            intent=intent_dict,
            context=context_dict
        )

        log.info(f"Extracted {sum(len(v) for v in extracted_entities.values())} entities")

        # Format entities for planning
        formatted_entities = format_entities_for_planning(extracted_entities)

        # Step 3: Add turn to dialogue manager
        dialogue_manager.add_user_turn(
            user_input=user_input,
            intent=intent_dict,
            entities=formatted_entities
        )

        # Step 4: Check if clarification needed
        should_clarify = dialogue_manager.should_ask_for_clarification(
            hierarchical_intent.overall_confidence
        )

        if should_clarify:
            is_complete, missing_entities = dialogue_manager.check_intent_complete()
            if not is_complete and missing_entities:
                log.info(f"Need clarification for: {missing_entities}")

                # Generate clarification questions
                clarification_questions = dialogue_manager.generate_clarification_questions(
                    missing_entities
                )

                if clarification_questions:
                    # Add first clarification to dialogue
                    first_question = clarification_questions[0]
                    dialogue_manager.add_clarification_request(first_question)

                    log.info(f"Requesting clarification for: {first_question.entity_type}")

        # Step 5: Build legacy-compatible intent structure
        legacy_intent = _convert_to_legacy_intent(
            hierarchical_intent,
            formatted_entities
        )

        # Step 6: Generate context summary
        context_summary = dialogue_manager.get_conversation_summary()

        log.info("Phase 1 cognitive analysis completed")

        return {
            "intent": legacy_intent,
            "current_context": context_summary,
            "dialogue_context": dialogue_manager.to_dict(),
            "hierarchical_intent": hierarchical_intent.dict(),
            "extracted_entities": formatted_entities
        }

    except Exception as e:
        log.error(f"Phase 1 cognitive error: {e}", exc_info=True)

        # Fallback to legacy
        log.warning("Falling back to legacy implementation")
        return await _cognitive_node_legacy(state, log)


async def _cognitive_node_legacy(state: Dict[str, Any], log: LogContext) -> Dict[str, Any]:
    """레거시 구현 (기존 cognitive_node 로직)"""

    user_input = get_user_input(state)
    current_context = get_current_context(state)

    # LLM 호출
    llm_client = get_llm_client()
    prompt = format_cognitive_prompt(user_input, current_context)

    try:
        log.debug("Calling LLM for intent analysis (legacy)")
        response = await llm_client.chat_with_system(
            system_prompt=COGNITIVE_SYSTEM_PROMPT,
            user_message=prompt,
            max_tokens=500,
            response_format={"type": "json_object"}  # JSON 형식 강제
        )

        # JSON 파싱 시도
        intent = json.loads(response)
        log.info(
            f"Intent analysis completed: {intent.get('intent_type', 'unknown')} "
            f"(confidence: {intent.get('confidence', 0)})"
        )

    except json.JSONDecodeError as e:
        # JSON 파싱 실패 시 키워드 기반 fallback
        log.warning(f"Cognitive JSON parsing error: {e}. Using fallback intent.")

        intent = _get_config_based_intent(
            user_input=user_input,
            confidence=0.6,
            summary=f"Process: {user_input}"
        )
        log.info(
            f"Fallback intent: ML={intent['requires_ml']}, "
            f"Biz={intent['requires_biz']}, "
            f"sources={intent['extracted_entities']['data_sources']}"
        )
    except Exception as e:
        # 기타 에러 - 키워드 기반 fallback
        log.error(f"Cognitive node error: {e}", exc_info=True)

        intent = _get_config_based_intent(
            user_input=user_input,
            confidence=0.5,
            summary=f"Error processing: {user_input}",
            error=str(e)
        )
        log.info(
            f"Fallback intent (error): ML={intent['requires_ml']}, "
            f"Biz={intent['requires_biz']}, "
            f"sources={intent['extracted_entities']['data_sources']}"
        )

    return {
        "intent": intent,
        "current_context": intent.get("summary", "")
    }


def _convert_to_legacy_intent(
    hierarchical_intent: "HierarchicalIntent",
    extracted_entities: Dict[str, Any]
) -> Dict[str, Any]:
    """
    HierarchicalIntent를 레거시 intent 구조로 변환

    하위 호환성을 위해 기존 Planning/Execution Layer가 이해할 수 있는 형식으로 변환
    """

    # Map domain.category.subcategory to legacy intent_type
    intent_type = _map_hierarchical_to_legacy_type(hierarchical_intent)

    return {
        "intent_type": intent_type,
        "confidence": hierarchical_intent.overall_confidence,
        "requires_ml": hierarchical_intent.requires_ml,
        "requires_biz": hierarchical_intent.requires_biz,
        # CRITICAL: 명시적 수집/전처리 요청 플래그 추가
        "requires_data_collection": hierarchical_intent.requires_data_collection,
        "requires_preprocessing": hierarchical_intent.requires_preprocessing,
        "summary": (
            f"{hierarchical_intent.domain.value} - "
            f"{hierarchical_intent.category.value}"
            f"{f' - {hierarchical_intent.subcategory.value}' if hierarchical_intent.subcategory else ''}"
        ),
        "extracted_entities": extracted_entities,
        # Include hierarchical structure for future use
        "hierarchical": {
            "domain": hierarchical_intent.domain.value,
            "category": hierarchical_intent.category.value,
            "subcategory": hierarchical_intent.subcategory.value if hierarchical_intent.subcategory else None,
            "domain_confidence": hierarchical_intent.domain_confidence,
            "category_confidence": hierarchical_intent.category_confidence,
            "subcategory_confidence": hierarchical_intent.subcategory_confidence
        }
    }


def _map_hierarchical_to_legacy_type(hierarchical_intent: "HierarchicalIntent") -> str:
    """계층적 Intent를 레거시 intent_type으로 매핑"""

    domain = hierarchical_intent.domain.value
    category = hierarchical_intent.category.value
    subcategory = hierarchical_intent.subcategory.value if hierarchical_intent.subcategory else None

    # Map to existing legacy intent types
    if domain == "data_science":
        if category == "data_analysis":
            return "data_analysis"
        elif category == "data_visualization":
            return "data_visualization"
        return "data_collection"

    elif domain == "marketing":
        if "content_creation" in category:
            if subcategory == "video_generation":
                return "content_creation"
            return "content_creation"
        elif "campaign" in category:
            return "campaign_management"
        return "market_analysis"

    elif domain == "operations":
        if "reporting" in category:
            return "report_generation"
        return "automation"

    elif domain == "analytics":
        return "analysis"

    elif domain == "general":
        return "chat"

    # Default
    return "general"
