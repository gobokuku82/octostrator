"""Storyboard LLM Generator - GPT-4o 기반 스토리보드 생성

사용자 의도를 분석하여 상세한 스토리보드를 생성합니다.
카메라 앵글, 조명, 모델 사용 등 세부 연출 정보를 포함합니다.
"""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


class SceneSpec(BaseModel):
    """씬 스펙"""
    scene_number: int = Field(..., description="씬 번호")
    scene_type: str = Field(..., description="씬 타입 (hook, problem, solution, benefit, cta 등)")
    duration: float = Field(..., description="씬 길이 (초)")

    # 비주얼 설명
    description: str = Field(..., description="씬 설명")
    visual: str = Field(..., description="비주얼 상세 설명")

    # 카메라 설정
    camera_angle: str = Field(..., description="카메라 앵글 (close-up, medium shot, wide shot, etc.)")
    camera_movement: str = Field(..., description="카메라 무브먼트 (static, pan, zoom, tracking, etc.)")

    # 조명
    lighting: str = Field(..., description="조명 설정 (soft, dramatic, natural, studio, etc.)")
    lighting_mood: str = Field(..., description="조명 분위기 (warm, cool, neutral, etc.)")

    # 모델/피사체
    subject_type: str = Field(..., description="피사체 타입 (product, model, both, graphic)")
    model_direction: Optional[str] = Field(default=None, description="모델 연출 (표정, 포즈 등)")
    product_placement: Optional[str] = Field(default=None, description="제품 배치")

    # 스타일
    color_grade: str = Field(..., description="컬러 그레이딩")
    style_reference: Optional[str] = Field(default=None, description="스타일 레퍼런스")

    # 텍스트/오버레이
    text_overlay: Optional[str] = Field(default=None, description="텍스트 오버레이")
    text_position: str = Field(default="center", description="텍스트 위치")

    # 전환
    transition_in: str = Field(default="cut", description="입장 전환")
    transition_out: str = Field(default="cut", description="퇴장 전환")

    # 프롬프트 (생성용)
    image_prompt: Optional[str] = Field(default=None, description="이미지 생성 프롬프트")
    motion_prompt: Optional[str] = Field(default=None, description="모션 프롬프트 (비디오 변환용)")


class StoryboardSpec(BaseModel):
    """스토리보드 스펙"""
    id: str = Field(..., description="스토리보드 ID")
    title: str = Field(..., description="스토리보드 제목")

    # 메타 정보
    platform: str = Field(..., description="플랫폼 (Instagram, YouTube, TikTok, etc.)")
    aspect_ratio: str = Field(..., description="화면 비율")
    total_duration: float = Field(..., description="총 길이 (초)")
    style: str = Field(..., description="전체 스타일")

    # 브랜드 정보
    brand: str = Field(..., description="브랜드명")
    product: str = Field(..., description="제품명")
    key_message: str = Field(..., description="핵심 메시지")
    target_audience: str = Field(..., description="타겟 오디언스")

    # 씬 목록
    scenes: List[SceneSpec] = Field(..., description="씬 목록")

    # 오디오
    background_music_mood: str = Field(..., description="배경음악 분위기")
    voiceover_tone: Optional[str] = Field(default=None, description="보이스오버 톤")

    # 메타데이터
    created_at: str = Field(..., description="생성 시간")


class StoryboardInput(BaseModel):
    """스토리보드 생성 입력"""
    user_request: str = Field(..., description="사용자 요청")

    # 브랜드/제품 정보
    brand: Optional[str] = Field(default=None, description="브랜드명")
    product: Optional[str] = Field(default=None, description="제품명")
    key_benefit: Optional[str] = Field(default=None, description="핵심 베네핏")

    # 플랫폼 설정
    platform: str = Field(default="Instagram", description="플랫폼")
    duration_sec: int = Field(default=30, description="목표 길이 (초)")
    aspect_ratio: str = Field(default="9:16", description="화면 비율")

    # 스타일 설정
    style: str = Field(default="modern", description="스타일")
    mood: str = Field(default="professional", description="분위기")

    # 타겟
    target_audience: Optional[str] = Field(default=None, description="타겟 오디언스")

    # 추가 지시사항
    additional_instructions: Optional[str] = Field(default=None, description="추가 지시사항")

    # 리뷰/인사이트 정보
    reviews: Optional[List[str]] = Field(default=None, description="고객 리뷰")
    insights: Optional[List[str]] = Field(default=None, description="분석 인사이트")


class StoryboardOutput(BaseModel):
    """스토리보드 생성 출력"""
    success: bool
    storyboard: Optional[StoryboardSpec] = None
    error: Optional[str] = None


class StoryboardLLMGenerator:
    """
    GPT-4o 기반 스토리보드 생성기

    사용자 의도를 분석하여 상세한 스토리보드를 생성합니다.

    Features:
        - 사용자 요청 분석
        - 플랫폼별 최적화 (Instagram, YouTube, TikTok 등)
        - 상세 연출 정보 (카메라, 조명, 모델 등)
        - 이미지/비디오 생성 프롬프트 자동 생성

    Usage:
        generator = StoryboardLLMGenerator()

        result = await generator.generate(StoryboardInput(
            user_request="라네즈 워터뱅크 크림 광고 만들어줘",
            brand="라네즈",
            product="워터뱅크 블루 히알루로닉 크림",
            platform="Instagram",
            duration_sec=30
        ))

        if result.success:
            storyboard = result.storyboard
    """

    SYSTEM_PROMPT = """You are an expert video director and storyboard artist specializing in commercial advertising.
Create detailed storyboards for video advertisements based on user requests.

Your storyboards should include:
1. Scene breakdown with precise timing
2. Camera angles and movements (close-up, wide shot, pan, zoom, tracking, etc.)
3. Lighting setup (soft, dramatic, natural, studio, rim light, etc.)
4. Subject/model direction (expressions, poses, actions)
5. Product placement and highlighting
6. Color grading and visual style
7. Text overlays and transitions
8. Image generation prompts optimized for FLUX/Stable Diffusion
9. Motion prompts for image-to-video conversion

Platform specifications:
- Instagram Reels: 9:16 aspect ratio, 15-60 seconds, engaging hook in first 3 seconds
- YouTube Shorts: 9:16 aspect ratio, up to 60 seconds, educational or entertaining
- TikTok: 9:16 aspect ratio, 15-60 seconds, trend-aware, dynamic
- YouTube: 16:9 aspect ratio, variable length, cinematic quality
- TV Commercial: 16:9 aspect ratio, 15-30 seconds, broadcast quality

Scene types to consider:
- hook: Attention-grabbing opening (problem or intrigue)
- problem: Relatable pain point
- solution_intro: Product reveal
- benefit: Key benefits demonstration
- usage: How-to/application
- result: Transformation/outcome
- social_proof: Reviews/testimonials
- cta: Call to action

Always respond in valid JSON format matching the StoryboardSpec schema."""

    USER_PROMPT_TEMPLATE = """Create a detailed storyboard for the following request:

User Request: {user_request}

Brand Information:
- Brand: {brand}
- Product: {product}
- Key Benefit: {key_benefit}
- Target Audience: {target_audience}

Platform Settings:
- Platform: {platform}
- Duration: {duration_sec} seconds
- Aspect Ratio: {aspect_ratio}

Style:
- Style: {style}
- Mood: {mood}

{additional_context}

Generate a complete storyboard with {num_scenes} scenes.
Each scene should have detailed camera, lighting, and subject directions.
Include optimized image_prompt and motion_prompt for each scene."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        api_key: Optional[str] = None
    ):
        """
        StoryboardLLMGenerator 초기화

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

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", self.USER_PROMPT_TEMPLATE)
        ])

        self.parser = JsonOutputParser(pydantic_object=StoryboardSpec)
        self.chain = self.prompt | self.llm | self.parser

    def _calculate_num_scenes(self, duration_sec: int, platform: str) -> int:
        """플랫폼과 길이에 따른 씬 수 계산"""
        # 평균 씬 길이 (초)
        avg_scene_duration = {
            "Instagram": 5,
            "TikTok": 4,
            "YouTube Shorts": 6,
            "YouTube": 8,
            "TV Commercial": 4
        }

        avg_duration = avg_scene_duration.get(platform, 5)
        num_scenes = max(3, min(10, int(duration_sec / avg_duration)))

        return num_scenes

    def _build_additional_context(self, input_data: StoryboardInput) -> str:
        """추가 맥락 구성"""
        parts = []

        if input_data.reviews:
            parts.append("Customer Reviews:")
            for review in input_data.reviews[:3]:
                parts.append(f"- {review}")

        if input_data.insights:
            parts.append("\nMarket Insights:")
            for insight in input_data.insights[:3]:
                parts.append(f"- {insight}")

        if input_data.additional_instructions:
            parts.append(f"\nAdditional Instructions:\n{input_data.additional_instructions}")

        return "\n".join(parts) if parts else "No additional context provided."

    async def generate(self, input_data: StoryboardInput) -> StoryboardOutput:
        """
        스토리보드 생성

        Args:
            input_data: 스토리보드 생성 입력

        Returns:
            StoryboardOutput
        """
        try:
            num_scenes = self._calculate_num_scenes(
                input_data.duration_sec,
                input_data.platform
            )

            additional_context = self._build_additional_context(input_data)

            # LLM 호출
            result = await self.chain.ainvoke({
                "user_request": input_data.user_request,
                "brand": input_data.brand or "Unknown",
                "product": input_data.product or "Unknown",
                "key_benefit": input_data.key_benefit or "Not specified",
                "target_audience": input_data.target_audience or "General audience",
                "platform": input_data.platform,
                "duration_sec": input_data.duration_sec,
                "aspect_ratio": input_data.aspect_ratio,
                "style": input_data.style,
                "mood": input_data.mood,
                "additional_context": additional_context,
                "num_scenes": num_scenes
            })

            # ID와 생성시간 추가
            if isinstance(result, dict):
                result["id"] = f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                result["created_at"] = datetime.now().isoformat()

                # StoryboardSpec으로 변환
                storyboard = StoryboardSpec(**result)
            else:
                storyboard = result

            return StoryboardOutput(
                success=True,
                storyboard=storyboard
            )

        except Exception as e:
            return StoryboardOutput(
                success=False,
                error=str(e)
            )

    async def generate_from_context(
        self,
        context: Dict[str, Any],
        user_request: Optional[str] = None
    ) -> StoryboardOutput:
        """
        컨텍스트에서 스토리보드 생성

        moaDREAM 시스템의 context를 직접 사용

        Args:
            context: 시스템 컨텍스트
            user_request: 사용자 요청 (없으면 컨텍스트에서 추출)

        Returns:
            StoryboardOutput
        """
        # 컨텍스트에서 정보 추출
        brand_info = context.get("brand_info", {})
        insights = context.get("insights", {}).get("insights", [])
        reviews = context.get("reviews", [])

        input_data = StoryboardInput(
            user_request=user_request or context.get("user_input", "Create a product advertisement"),
            brand=brand_info.get("brand") or context.get("brand"),
            product=brand_info.get("product") or context.get("product"),
            key_benefit=brand_info.get("key_benefit") or context.get("key_benefit"),
            target_audience=brand_info.get("target_audience") or context.get("target_audience"),
            platform=context.get("platform", "Instagram"),
            duration_sec=context.get("duration_sec", 30),
            aspect_ratio=context.get("aspect_ratio", "9:16"),
            style=context.get("style", "modern"),
            mood=context.get("mood", "professional"),
            reviews=reviews if isinstance(reviews, list) else None,
            insights=insights if isinstance(insights, list) else None,
            additional_instructions=context.get("additional_instructions")
        )

        return await self.generate(input_data)

    def to_dict(self, storyboard: StoryboardSpec) -> Dict[str, Any]:
        """스토리보드를 딕셔너리로 변환"""
        return storyboard.model_dump()

    def to_json(self, storyboard: StoryboardSpec, indent: int = 2) -> str:
        """스토리보드를 JSON 문자열로 변환"""
        return json.dumps(self.to_dict(storyboard), ensure_ascii=False, indent=indent)
