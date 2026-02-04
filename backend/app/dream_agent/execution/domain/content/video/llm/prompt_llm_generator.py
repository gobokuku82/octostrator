"""Prompt LLM Generator - GPT-4o 기반 이미지/비디오 프롬프트 생성

스토리보드의 각 씬에 대해 FLUX/Wan2.2에 최적화된 프롬프트를 생성합니다.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


class ScenePromptSpec(BaseModel):
    """씬 프롬프트 스펙"""
    scene_number: int = Field(..., description="씬 번호")

    # 이미지 생성 프롬프트
    image_prompt: str = Field(..., description="FLUX용 이미지 프롬프트")
    negative_prompt: str = Field(..., description="네거티브 프롬프트")

    # 비디오 변환 프롬프트
    motion_prompt: str = Field(..., description="Wan2.2용 모션 프롬프트")
    motion_negative: str = Field(..., description="모션 네거티브 프롬프트")

    # 생성 파라미터 권장값
    recommended_steps: int = Field(default=30, description="권장 스텝 수")
    recommended_cfg: float = Field(default=7.5, description="권장 CFG")
    recommended_duration: int = Field(default=5, description="권장 비디오 길이 (초)")


class PromptGenerationInput(BaseModel):
    """프롬프트 생성 입력"""
    scene_description: str = Field(..., description="씬 설명")
    visual_description: str = Field(..., description="비주얼 설명")
    camera_angle: str = Field(default="medium shot", description="카메라 앵글")
    camera_movement: str = Field(default="static", description="카메라 무브먼트")
    lighting: str = Field(default="soft", description="조명")
    style: str = Field(default="modern", description="스타일")
    mood: str = Field(default="professional", description="분위기")

    # 피사체 정보
    subject_type: str = Field(default="product", description="피사체 타입")
    product_name: Optional[str] = Field(default=None, description="제품명")
    brand_name: Optional[str] = Field(default=None, description="브랜드명")


class BatchPromptInput(BaseModel):
    """배치 프롬프트 생성 입력"""
    scenes: List[Dict[str, Any]] = Field(..., description="씬 목록")
    global_style: str = Field(default="modern professional", description="전체 스타일")
    brand_name: Optional[str] = Field(default=None, description="브랜드명")
    product_name: Optional[str] = Field(default=None, description="제품명")


class PromptGenerationOutput(BaseModel):
    """프롬프트 생성 출력"""
    success: bool
    prompt: Optional[ScenePromptSpec] = None
    error: Optional[str] = None


class BatchPromptOutput(BaseModel):
    """배치 프롬프트 출력"""
    success: bool
    prompts: List[ScenePromptSpec] = []
    error: Optional[str] = None


class PromptLLMGenerator:
    """
    GPT-4o 기반 이미지/비디오 프롬프트 생성기

    스토리보드의 각 씬에 대해 FLUX와 Wan2.2에 최적화된 프롬프트를 생성합니다.

    Features:
        - FLUX 이미지 생성 프롬프트 최적화
        - Wan2.2 모션 프롬프트 최적화
        - 네거티브 프롬프트 자동 생성
        - 씬별 최적 파라미터 추천

    Usage:
        generator = PromptLLMGenerator()

        # 단일 씬 프롬프트 생성
        result = await generator.generate(PromptGenerationInput(
            scene_description="제품 소개 씬",
            visual_description="화이트 배경에서 크림 제품 클로즈업",
            camera_angle="close-up",
            lighting="soft studio"
        ))

        # 배치 생성 (스토리보드 전체)
        results = await generator.generate_batch(BatchPromptInput(
            scenes=[scene1, scene2, ...],
            global_style="luxury cosmetic"
        ))
    """

    SYSTEM_PROMPT = """You are an expert prompt engineer specializing in AI image and video generation.
Create optimized prompts for FLUX (image generation) and Wan2.2 (image-to-video conversion).

FLUX Prompt Guidelines:
1. Start with the main subject and its characteristics
2. Include camera angle, lighting, and composition
3. Add style modifiers (photorealistic, cinematic, professional, etc.)
4. Include quality boosters (4k, high detail, sharp focus, etc.)
5. Be specific but not overly verbose (optimal: 50-100 words)
6. Use commas to separate concepts

FLUX Negative Prompt Guidelines:
1. Include common defects to avoid (blurry, low quality, distorted, etc.)
2. Add specific negatives based on subject (bad anatomy for humans, etc.)
3. Include style negatives if needed

Wan2.2 Motion Prompt Guidelines:
1. Describe the type of motion (gentle, dynamic, smooth, etc.)
2. Include camera movement (zoom in, pan left, tracking shot, etc.)
3. Specify motion direction and speed
4. Keep it concise (20-40 words)
5. Focus on natural, subtle movements for best results

Wan2.2 Motion Negative Guidelines:
1. Avoid jerky or unnatural movements
2. Include common video artifacts to avoid

Always respond in valid JSON format."""

    USER_PROMPT_TEMPLATE = """Generate optimized image and video prompts for the following scene:

Scene Description: {scene_description}
Visual Description: {visual_description}

Camera Settings:
- Angle: {camera_angle}
- Movement: {camera_movement}

Lighting: {lighting}
Style: {style}
Mood: {mood}

Subject:
- Type: {subject_type}
- Product: {product_name}
- Brand: {brand_name}

Scene Number: {scene_number}

Generate:
1. image_prompt: Optimized prompt for FLUX image generation
2. negative_prompt: Negative prompt for FLUX
3. motion_prompt: Optimized prompt for Wan2.2 video conversion
4. motion_negative: Negative prompt for motion
5. Recommended generation parameters

Respond in JSON format matching ScenePromptSpec schema."""

    BATCH_PROMPT_TEMPLATE = """Generate optimized image and video prompts for each scene in this storyboard:

Global Style: {global_style}
Brand: {brand_name}
Product: {product_name}

Scenes:
{scenes_json}

For each scene, generate:
1. image_prompt: Optimized for FLUX
2. negative_prompt: Negative prompt for FLUX
3. motion_prompt: Optimized for Wan2.2
4. motion_negative: Negative prompt for motion
5. Recommended parameters

Maintain visual consistency across all scenes while respecting individual scene characteristics.

Respond as a JSON array of ScenePromptSpec objects."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        api_key: Optional[str] = None
    ):
        """
        PromptLLMGenerator 초기화

        Args:
            model: OpenAI 모델 (기본: gpt-4o)
            temperature: 생성 온도
            api_key: OpenAI API 키
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=self.api_key
        )

        # 단일 프롬프트 체인
        self.single_prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", self.USER_PROMPT_TEMPLATE)
        ])
        self.single_parser = JsonOutputParser(pydantic_object=ScenePromptSpec)
        self.single_chain = self.single_prompt | self.llm | self.single_parser

        # 배치 프롬프트 체인
        self.batch_prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", self.BATCH_PROMPT_TEMPLATE)
        ])

    async def generate(
        self,
        input_data: PromptGenerationInput,
        scene_number: int = 1
    ) -> PromptGenerationOutput:
        """
        단일 씬 프롬프트 생성

        Args:
            input_data: 프롬프트 생성 입력
            scene_number: 씬 번호

        Returns:
            PromptGenerationOutput
        """
        try:
            result = await self.single_chain.ainvoke({
                "scene_description": input_data.scene_description,
                "visual_description": input_data.visual_description,
                "camera_angle": input_data.camera_angle,
                "camera_movement": input_data.camera_movement,
                "lighting": input_data.lighting,
                "style": input_data.style,
                "mood": input_data.mood,
                "subject_type": input_data.subject_type,
                "product_name": input_data.product_name or "product",
                "brand_name": input_data.brand_name or "brand",
                "scene_number": scene_number
            })

            if isinstance(result, dict):
                result["scene_number"] = scene_number
                prompt = ScenePromptSpec(**result)
            else:
                prompt = result

            return PromptGenerationOutput(
                success=True,
                prompt=prompt
            )

        except Exception as e:
            return PromptGenerationOutput(
                success=False,
                error=str(e)
            )

    async def generate_batch(self, input_data: BatchPromptInput) -> BatchPromptOutput:
        """
        배치 프롬프트 생성

        Args:
            input_data: 배치 프롬프트 입력

        Returns:
            BatchPromptOutput
        """
        try:
            import json

            # 씬 정보를 JSON 문자열로 변환
            scenes_json = json.dumps(input_data.scenes, ensure_ascii=False, indent=2)

            # LLM 호출
            response = await self.llm.ainvoke(
                self.batch_prompt.format_messages(
                    global_style=input_data.global_style,
                    brand_name=input_data.brand_name or "brand",
                    product_name=input_data.product_name or "product",
                    scenes_json=scenes_json
                )
            )

            # JSON 파싱
            content = response.content
            # JSON 배열 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            results = json.loads(content.strip())

            prompts = []
            for i, result in enumerate(results):
                if "scene_number" not in result:
                    result["scene_number"] = i + 1
                prompts.append(ScenePromptSpec(**result))

            return BatchPromptOutput(
                success=True,
                prompts=prompts
            )

        except Exception as e:
            return BatchPromptOutput(
                success=False,
                error=str(e)
            )

    async def generate_from_storyboard(
        self,
        storyboard: Dict[str, Any]
    ) -> BatchPromptOutput:
        """
        스토리보드에서 프롬프트 생성

        Args:
            storyboard: 스토리보드 딕셔너리

        Returns:
            BatchPromptOutput
        """
        scenes = storyboard.get("scenes", [])

        # 씬 정보 추출
        scene_inputs = []
        for scene in scenes:
            scene_inputs.append({
                "scene_number": scene.get("scene_number", len(scene_inputs) + 1),
                "description": scene.get("description", ""),
                "visual": scene.get("visual", ""),
                "camera_angle": scene.get("camera_angle", "medium shot"),
                "camera_movement": scene.get("camera_movement", "static"),
                "lighting": scene.get("lighting", "soft"),
                "lighting_mood": scene.get("lighting_mood", "neutral"),
                "subject_type": scene.get("subject_type", "product"),
                "style_reference": scene.get("style_reference", ""),
                "color_grade": scene.get("color_grade", ""),
            })

        # 브랜드 정보
        brand_info = storyboard.get("brand", {})
        if isinstance(brand_info, dict):
            brand_name = brand_info.get("brand", "")
            product_name = brand_info.get("product", "")
        else:
            brand_name = storyboard.get("brand", "")
            product_name = storyboard.get("product", "")

        return await self.generate_batch(BatchPromptInput(
            scenes=scene_inputs,
            global_style=storyboard.get("style", "modern professional"),
            brand_name=brand_name,
            product_name=product_name
        ))

    async def enhance_prompt(
        self,
        basic_prompt: str,
        style: str = "photorealistic",
        quality_level: str = "high"
    ) -> str:
        """
        기본 프롬프트 향상

        Args:
            basic_prompt: 기본 프롬프트
            style: 스타일
            quality_level: 품질 레벨 (low, medium, high, ultra)

        Returns:
            향상된 프롬프트
        """
        quality_boosters = {
            "low": "",
            "medium": ", high quality",
            "high": ", high quality, 4k, detailed, sharp focus",
            "ultra": ", masterpiece, best quality, 8k, ultra detailed, sharp focus, professional"
        }

        style_suffixes = {
            "photorealistic": ", photorealistic, realistic lighting",
            "cinematic": ", cinematic, film grain, dramatic lighting",
            "professional": ", professional photography, studio lighting",
            "artistic": ", artistic, creative, stylized",
            "minimal": ", minimalist, clean, simple"
        }

        enhanced = basic_prompt

        # 스타일 추가
        if style in style_suffixes:
            enhanced += style_suffixes[style]

        # 품질 부스터 추가
        if quality_level in quality_boosters:
            enhanced += quality_boosters[quality_level]

        return enhanced

    def get_default_negative_prompt(self, subject_type: str = "product") -> str:
        """
        기본 네거티브 프롬프트 반환

        Args:
            subject_type: 피사체 타입

        Returns:
            네거티브 프롬프트
        """
        base_negative = "low quality, blurry, distorted, noisy, grainy, jpeg artifacts, watermark, text, logo"

        subject_negatives = {
            "product": "damaged product, dirty, scratched, broken",
            "model": "bad anatomy, bad hands, missing fingers, extra limbs, disfigured, deformed",
            "both": "bad anatomy, bad hands, damaged product, dirty, scratched",
            "graphic": "pixelated, low resolution, compression artifacts"
        }

        negative = base_negative
        if subject_type in subject_negatives:
            negative += f", {subject_negatives[subject_type]}"

        return negative

    def get_default_motion_negative(self) -> str:
        """기본 모션 네거티브 프롬프트 반환"""
        return "jerky motion, static, frozen, glitchy, distorted, unnatural movement, sudden jumps"
