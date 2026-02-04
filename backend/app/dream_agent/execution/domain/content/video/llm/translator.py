"""Translator - GPT-4o-mini 기반 한영 번역

한국어 프롬프트를 영어로 번역합니다.
비디오/이미지 생성에 최적화된 번역을 수행합니다.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class TranslationInput(BaseModel):
    """번역 입력"""
    text: str = Field(..., description="번역할 텍스트")
    context: Optional[str] = Field(
        default=None,
        description="문맥 정보 (예: storyboard, image_prompt)"
    )
    preserve_terms: List[str] = Field(
        default_factory=list,
        description="보존할 용어 (브랜드명 등)"
    )


class TranslationOutput(BaseModel):
    """번역 출력"""
    success: bool
    original: str
    translated: Optional[str] = None
    error: Optional[str] = None


class BatchTranslationOutput(BaseModel):
    """배치 번역 출력"""
    success: bool
    results: List[TranslationOutput] = []
    error: Optional[str] = None


class Translator:
    """
    GPT-4o-mini 기반 한영 번역기

    비디오/이미지 생성 프롬프트에 최적화된 번역을 수행합니다.

    Features:
        - 한국어 → 영어 번역
        - 비디오/이미지 프롬프트 맥락 이해
        - 브랜드명 등 특정 용어 보존
        - 배치 번역 지원

    Usage:
        translator = Translator()

        # 단일 번역
        result = await translator.translate(TranslationInput(
            text="밝은 조명의 모던한 스튜디오",
            context="image_prompt"
        ))

        # 배치 번역
        results = await translator.translate_batch([
            TranslationInput(text="씬 1: 제품 소개"),
            TranslationInput(text="씬 2: 사용 방법"),
        ])
    """

    SYSTEM_PROMPT = """You are a professional translator specializing in video/image production prompts.
Translate Korean text to English, optimizing for AI image/video generation models.

Guidelines:
1. Translate naturally while preserving visual/cinematographic terminology
2. Keep brand names, product names, and technical terms in their original form if specified
3. Use descriptive, prompt-friendly English (suitable for Stable Diffusion, FLUX, etc.)
4. Maintain the visual mood and atmosphere of the original text
5. Be concise but descriptive

Preserve these terms without translation: {preserve_terms}

Context: {context}

Respond with ONLY the translated text, nothing else."""

    IMAGE_PROMPT_CONTEXT = """This is an image generation prompt. Focus on:
- Visual descriptions (colors, lighting, composition)
- Style and mood (cinematic, professional, modern, etc.)
- Subject details (model, product, scene)
- Camera settings (close-up, wide shot, etc.)"""

    STORYBOARD_CONTEXT = """This is a video storyboard. Focus on:
- Scene descriptions and transitions
- Action and motion descriptions
- Narrative flow
- Visual storytelling elements"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        api_key: Optional[str] = None
    ):
        """
        Translator 초기화

        Args:
            model: OpenAI 모델 (기본: gpt-4o-mini)
            temperature: 생성 온도 (기본: 0.3)
            api_key: OpenAI API 키 (기본: 환경변수)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=self.api_key
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{text}")
        ])

        self.chain = self.prompt | self.llm | StrOutputParser()

    def _get_context_description(self, context: Optional[str]) -> str:
        """맥락 설명 반환"""
        if context == "image_prompt":
            return self.IMAGE_PROMPT_CONTEXT
        elif context == "storyboard":
            return self.STORYBOARD_CONTEXT
        elif context:
            return context
        else:
            return "General video/image production context"

    async def translate(self, input_data: TranslationInput) -> TranslationOutput:
        """
        텍스트 번역

        Args:
            input_data: 번역 입력

        Returns:
            TranslationOutput
        """
        try:
            # 이미 영어인 경우 그대로 반환
            if self._is_english(input_data.text):
                return TranslationOutput(
                    success=True,
                    original=input_data.text,
                    translated=input_data.text
                )

            # 맥락 및 보존 용어 설정
            context_desc = self._get_context_description(input_data.context)
            preserve_terms = ", ".join(input_data.preserve_terms) if input_data.preserve_terms else "none"

            # 번역 실행
            translated = await self.chain.ainvoke({
                "text": input_data.text,
                "context": context_desc,
                "preserve_terms": preserve_terms
            })

            return TranslationOutput(
                success=True,
                original=input_data.text,
                translated=translated.strip()
            )

        except Exception as e:
            return TranslationOutput(
                success=False,
                original=input_data.text,
                error=str(e)
            )

    async def translate_batch(
        self,
        inputs: List[TranslationInput]
    ) -> BatchTranslationOutput:
        """
        배치 번역

        Args:
            inputs: 번역 입력 목록

        Returns:
            BatchTranslationOutput
        """
        try:
            import asyncio
            results = await asyncio.gather(
                *[self.translate(inp) for inp in inputs],
                return_exceptions=True
            )

            outputs = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    outputs.append(TranslationOutput(
                        success=False,
                        original=inputs[i].text,
                        error=str(result)
                    ))
                else:
                    outputs.append(result)

            return BatchTranslationOutput(
                success=all(r.success for r in outputs),
                results=outputs
            )

        except Exception as e:
            return BatchTranslationOutput(
                success=False,
                error=str(e)
            )

    async def translate_text(
        self,
        text: str,
        context: Optional[str] = None,
        preserve_terms: Optional[List[str]] = None
    ) -> str:
        """
        간단한 텍스트 번역 (편의 메서드)

        Args:
            text: 번역할 텍스트
            context: 맥락
            preserve_terms: 보존할 용어

        Returns:
            번역된 텍스트 (실패 시 원본 반환)
        """
        result = await self.translate(TranslationInput(
            text=text,
            context=context,
            preserve_terms=preserve_terms or []
        ))

        return result.translated if result.success else text

    async def translate_storyboard(
        self,
        storyboard: Dict[str, Any],
        preserve_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        스토리보드 전체 번역

        Args:
            storyboard: 스토리보드 딕셔너리
            preserve_terms: 보존할 용어 (브랜드명 등)

        Returns:
            번역된 스토리보드
        """
        preserve = preserve_terms or []

        # 브랜드/제품명 자동 추가
        if "brand" in storyboard:
            brand_info = storyboard["brand"]
            if isinstance(brand_info, dict):
                preserve.extend([
                    brand_info.get("brand", ""),
                    brand_info.get("product", "")
                ])
            preserve = [p for p in preserve if p]  # 빈 문자열 제거

        translated = storyboard.copy()

        # 씬 번역
        if "scenes" in translated:
            for scene in translated["scenes"]:
                # description 번역
                if "description" in scene:
                    scene["description"] = await self.translate_text(
                        scene["description"],
                        context="storyboard",
                        preserve_terms=preserve
                    )

                # visual 번역
                if "visual" in scene:
                    scene["visual"] = await self.translate_text(
                        scene["visual"],
                        context="image_prompt",
                        preserve_terms=preserve
                    )

                # text_overlay 번역
                if "text_overlay" in scene:
                    scene["text_overlay"] = await self.translate_text(
                        scene["text_overlay"],
                        context="storyboard",
                        preserve_terms=preserve
                    )

                # image_prompt 번역
                if "image_prompt" in scene:
                    scene["image_prompt"] = await self.translate_text(
                        scene["image_prompt"],
                        context="image_prompt",
                        preserve_terms=preserve
                    )

                # motion_prompt 추가 (비디오용)
                if "motion_prompt" in scene:
                    scene["motion_prompt"] = await self.translate_text(
                        scene["motion_prompt"],
                        context="image_prompt",
                        preserve_terms=preserve
                    )

        return translated

    def _is_english(self, text: str) -> bool:
        """
        텍스트가 영어인지 확인

        Args:
            text: 확인할 텍스트

        Returns:
            영어 여부
        """
        # 한글 문자 포함 여부 확인
        for char in text:
            if '\uac00' <= char <= '\ud7a3':  # 한글 음절 범위
                return False
            if '\u3131' <= char <= '\u3163':  # 한글 자모 범위
                return False
        return True
