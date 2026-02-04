"""Cognitive - Layer 1: 의도 분석

Phase 1 고도화:
- IntentClassifier: 3-depth 계층적 Intent 분류
- EntityExtractor: 정교한 엔티티 추출
- DialogueManager: 멀티턴 대화 관리
"""

from .cognitive_node import cognitive_node

# Phase 1 components (optional imports)
try:
    from .intent_classifier import (
        IntentClassifier,
        HierarchicalIntent,
        IntentDomain,
        IntentCategory,
        IntentSubcategory,
    )
    from .entity_extractor import (
        EntityExtractor,
        EntityType,
        ExtractedEntity,
        format_entities_for_planning,
    )
    from .dialogue_manager import (
        DialogueManager,
        DialogueTurn,
        DialogueContext,
        ClarificationQuestion,
    )

    __all__ = [
        # Main node
        "cognitive_node",
        # Phase 1: Intent Classifier
        "IntentClassifier",
        "HierarchicalIntent",
        "IntentDomain",
        "IntentCategory",
        "IntentSubcategory",
        # Phase 1: Entity Extractor
        "EntityExtractor",
        "EntityType",
        "ExtractedEntity",
        "format_entities_for_planning",
        # Phase 1: Dialogue Manager
        "DialogueManager",
        "DialogueTurn",
        "DialogueContext",
        "ClarificationQuestion",
    ]

except ImportError:
    # Fallback to legacy exports only
    __all__ = ["cognitive_node"]
