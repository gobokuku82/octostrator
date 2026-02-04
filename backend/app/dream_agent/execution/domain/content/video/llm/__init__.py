"""LLM Module - GPT 기반 텍스트 생성

번역, 스토리보드 생성, 프롬프트 생성을 담당합니다.
"""

from .translator import (
    Translator,
    TranslationInput,
    TranslationOutput,
    BatchTranslationOutput
)

from .storyboard_llm_generator import (
    StoryboardLLMGenerator,
    StoryboardInput,
    StoryboardOutput,
    StoryboardSpec,
    SceneSpec
)

from .prompt_llm_generator import (
    PromptLLMGenerator,
    PromptGenerationInput,
    PromptGenerationOutput,
    BatchPromptInput,
    BatchPromptOutput,
    ScenePromptSpec
)

__all__ = [
    # Translator
    "Translator",
    "TranslationInput",
    "TranslationOutput",
    "BatchTranslationOutput",

    # Storyboard Generator
    "StoryboardLLMGenerator",
    "StoryboardInput",
    "StoryboardOutput",
    "StoryboardSpec",
    "SceneSpec",

    # Prompt Generator
    "PromptLLMGenerator",
    "PromptGenerationInput",
    "PromptGenerationOutput",
    "BatchPromptInput",
    "BatchPromptOutput",
    "ScenePromptSpec",
]
