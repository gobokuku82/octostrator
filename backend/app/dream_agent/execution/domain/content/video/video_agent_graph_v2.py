"""Video Agent Graph V2 - LangGraph 기반 비디오 생성 통합 그래프

5단계 파이프라인:
1. 스토리보드 생성 (GPT-4o)
2. 이미지 프롬프트 생성 (GPT-4o)
3. 이미지 생성 (RunPod FLUX)
4. 비디오 변환 (RunPod Wan2.2)
5. 비디오 합성 (FFmpeg/MoviePy)
"""

import os
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# LLM 모듈
from .llm.translator import Translator
from .llm.storyboard_llm_generator import StoryboardLLMGenerator, StoryboardInput
from .llm.prompt_llm_generator import PromptLLMGenerator

# RunPod 모듈
from .runpod.flux_image_generator import FluxImageGenerator, ImageGenerateInput
from .runpod.wan22_video_generator import Wan22VideoGenerator, VideoGenerateInput

# Postprocess 모듈
from .postprocess.video_composer import VideoComposer, VideoClipInput, CompositionConfig


class VideoAgentPhase(str, Enum):
    """비디오 에이전트 단계"""
    INIT = "init"
    STORYBOARD = "storyboard"
    PROMPTS = "prompts"
    IMAGES = "images"
    VIDEOS = "videos"
    COMPOSE = "compose"
    COMPLETE = "complete"
    ERROR = "error"


class VideoAgentState(TypedDict):
    """비디오 에이전트 상태"""
    # 입력
    user_request: str
    brand: Optional[str]
    product: Optional[str]
    platform: str
    duration_sec: int
    style: str

    # 컨텍스트 (moaDREAM 연동)
    context: Dict[str, Any]

    # 단계별 결과
    phase: str
    storyboard: Optional[Dict[str, Any]]
    prompts: Optional[List[Dict[str, Any]]]
    images: Optional[List[Dict[str, Any]]]
    videos: Optional[List[Dict[str, Any]]]
    final_video: Optional[Dict[str, Any]]

    # 메타데이터
    errors: List[str]
    processing_times: Dict[str, int]
    started_at: Optional[str]
    completed_at: Optional[str]


def create_initial_state(
    user_request: str,
    brand: Optional[str] = None,
    product: Optional[str] = None,
    platform: str = "Instagram",
    duration_sec: int = 30,
    style: str = "modern",
    context: Optional[Dict[str, Any]] = None
) -> VideoAgentState:
    """초기 상태 생성"""
    return VideoAgentState(
        user_request=user_request,
        brand=brand,
        product=product,
        platform=platform,
        duration_sec=duration_sec,
        style=style,
        context=context or {},
        phase=VideoAgentPhase.INIT.value,
        storyboard=None,
        prompts=None,
        images=None,
        videos=None,
        final_video=None,
        errors=[],
        processing_times={},
        started_at=datetime.now().isoformat(),
        completed_at=None
    )


# ============================================================
# Node Functions
# ============================================================

async def storyboard_node(state: VideoAgentState) -> Dict[str, Any]:
    """
    Step 1: 스토리보드 생성

    GPT-4o를 사용하여 사용자 요청을 분석하고 상세 스토리보드를 생성합니다.
    """
    start_time = datetime.now()

    try:
        generator = StoryboardLLMGenerator()
        translator = Translator()

        # 한국어 → 영어 번역 (필요시)
        translated_request = await translator.translate_text(
            state["user_request"],
            context="storyboard"
        )

        # 스토리보드 생성
        input_data = StoryboardInput(
            user_request=translated_request,
            brand=state.get("brand"),
            product=state.get("product"),
            platform=state.get("platform", "Instagram"),
            duration_sec=state.get("duration_sec", 30),
            style=state.get("style", "modern"),
            reviews=state.get("context", {}).get("reviews"),
            insights=state.get("context", {}).get("insights", {}).get("insights")
        )

        result = await generator.generate(input_data)

        if not result.success:
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + [f"Storyboard generation failed: {result.error}"]
            }

        # 스토리보드 한영 번역 (프롬프트용)
        storyboard_dict = generator.to_dict(result.storyboard)
        translated_storyboard = await translator.translate_storyboard(
            storyboard_dict,
            preserve_terms=[state.get("brand", ""), state.get("product", "")]
        )

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "phase": VideoAgentPhase.STORYBOARD.value,
            "storyboard": translated_storyboard,
            "processing_times": {
                **state.get("processing_times", {}),
                "storyboard": processing_time
            }
        }

    except Exception as e:
        return {
            "phase": VideoAgentPhase.ERROR.value,
            "errors": state.get("errors", []) + [f"Storyboard node error: {str(e)}"]
        }


async def prompts_node(state: VideoAgentState) -> Dict[str, Any]:
    """
    Step 2: 이미지/모션 프롬프트 생성

    각 씬에 대해 FLUX와 Wan2.2에 최적화된 프롬프트를 생성합니다.
    """
    start_time = datetime.now()

    try:
        if not state.get("storyboard"):
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["No storyboard available for prompt generation"]
            }

        generator = PromptLLMGenerator()

        result = await generator.generate_from_storyboard(state["storyboard"])

        if not result.success:
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + [f"Prompt generation failed: {result.error}"]
            }

        prompts = [p.model_dump() for p in result.prompts]

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "phase": VideoAgentPhase.PROMPTS.value,
            "prompts": prompts,
            "processing_times": {
                **state.get("processing_times", {}),
                "prompts": processing_time
            }
        }

    except Exception as e:
        return {
            "phase": VideoAgentPhase.ERROR.value,
            "errors": state.get("errors", []) + [f"Prompts node error: {str(e)}"]
        }


async def images_node(state: VideoAgentState) -> Dict[str, Any]:
    """
    Step 3: 이미지 생성

    RunPod FLUX를 사용하여 각 씬의 이미지를 생성합니다.
    """
    start_time = datetime.now()

    try:
        if not state.get("prompts"):
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["No prompts available for image generation"]
            }

        generator = FluxImageGenerator()

        # 배치 이미지 생성
        inputs = []
        for prompt in state["prompts"]:
            inputs.append({
                "prompt": prompt["image_prompt"],
                "negative_prompt": prompt["negative_prompt"],
                "steps": prompt.get("recommended_steps", 30)
            })

        results = await generator.generate_batch(inputs)

        images = []
        for i, result in enumerate(results):
            images.append({
                "scene_number": i + 1,
                "success": result.success,
                "job_id": result.job_id,
                "image_data": result.image_data,
                "error": result.error
            })

        # 성공 여부 확인
        success_count = sum(1 for img in images if img["success"])
        if success_count == 0:
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["All image generations failed"]
            }

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "phase": VideoAgentPhase.IMAGES.value,
            "images": images,
            "processing_times": {
                **state.get("processing_times", {}),
                "images": processing_time
            }
        }

    except Exception as e:
        return {
            "phase": VideoAgentPhase.ERROR.value,
            "errors": state.get("errors", []) + [f"Images node error: {str(e)}"]
        }


async def videos_node(state: VideoAgentState) -> Dict[str, Any]:
    """
    Step 4: 비디오 변환

    RunPod Wan2.2를 사용하여 이미지를 비디오로 변환합니다.
    """
    start_time = datetime.now()

    try:
        if not state.get("images"):
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["No images available for video conversion"]
            }

        if not state.get("prompts"):
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["No prompts available for motion"]
            }

        generator = Wan22VideoGenerator()

        # 성공한 이미지만 비디오 변환
        inputs = []
        for i, image in enumerate(state["images"]):
            if image["success"] and image["image_data"]:
                motion_prompt = state["prompts"][i]["motion_prompt"] if i < len(state["prompts"]) else "gentle movement"
                duration = state["prompts"][i].get("recommended_duration", 5) if i < len(state["prompts"]) else 5

                inputs.append(VideoGenerateInput(
                    image_base64=image["image_data"],
                    prompt=motion_prompt,
                    negative_prompt=state["prompts"][i].get("motion_negative", "static, jerky"),
                    duration=duration
                ))

        # 순차 처리 (API 부하 고려)
        results = await generator.generate_batch([inp.model_dump() for inp in inputs], parallel=False)

        videos = []
        input_idx = 0
        for i, image in enumerate(state["images"]):
            if image["success"] and image["image_data"]:
                result = results[input_idx]
                videos.append({
                    "scene_number": i + 1,
                    "success": result.success,
                    "job_id": result.job_id,
                    "video_data": result.video_data,
                    "duration": result.duration,
                    "error": result.error
                })
                input_idx += 1
            else:
                videos.append({
                    "scene_number": i + 1,
                    "success": False,
                    "error": "Source image generation failed"
                })

        # 성공 여부 확인
        success_count = sum(1 for vid in videos if vid["success"])
        if success_count == 0:
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["All video conversions failed"]
            }

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "phase": VideoAgentPhase.VIDEOS.value,
            "videos": videos,
            "processing_times": {
                **state.get("processing_times", {}),
                "videos": processing_time
            }
        }

    except Exception as e:
        return {
            "phase": VideoAgentPhase.ERROR.value,
            "errors": state.get("errors", []) + [f"Videos node error: {str(e)}"]
        }


async def compose_node(state: VideoAgentState) -> Dict[str, Any]:
    """
    Step 5: 비디오 합성

    FFmpeg/MoviePy를 사용하여 모든 비디오 클립을 하나로 합성합니다.
    """
    start_time = datetime.now()

    try:
        if not state.get("videos"):
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["No videos available for composition"]
            }

        composer = VideoComposer()

        # 성공한 비디오 클립만 수집
        clips = []
        for video in state["videos"]:
            if video["success"] and video["video_data"]:
                clips.append(VideoClipInput(
                    video_data=video["video_data"],
                    duration=video.get("duration"),
                    transition_in="fade" if len(clips) > 0 else None,
                    transition_out="fade",
                    transition_duration=0.5
                ))

        if not clips:
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + ["No successful video clips to compose"]
            }

        # 플랫폼에 따른 설정
        platform = state.get("platform", "Instagram")
        config = CompositionConfig(
            resolution="1080p",
            fps=30,
            aspect_ratio="9:16" if platform in ["Instagram", "TikTok", "YouTube Shorts"] else "16:9"
        )

        result = await composer.compose(clips=clips, config=config)

        if not result.success:
            return {
                "phase": VideoAgentPhase.ERROR.value,
                "errors": state.get("errors", []) + [f"Video composition failed: {result.error}"]
            }

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return {
            "phase": VideoAgentPhase.COMPLETE.value,
            "final_video": {
                "success": True,
                "video_data": result.video_data,
                "output_path": result.output_path,
                "duration": result.duration,
                "file_size_mb": result.file_size_mb
            },
            "processing_times": {
                **state.get("processing_times", {}),
                "compose": processing_time
            },
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "phase": VideoAgentPhase.ERROR.value,
            "errors": state.get("errors", []) + [f"Compose node error: {str(e)}"]
        }


def should_continue(state: VideoAgentState) -> str:
    """라우팅 조건"""
    phase = state.get("phase", VideoAgentPhase.INIT.value)

    if phase == VideoAgentPhase.ERROR.value:
        return END

    if phase == VideoAgentPhase.INIT.value:
        return "storyboard"

    if phase == VideoAgentPhase.STORYBOARD.value:
        return "prompts"

    if phase == VideoAgentPhase.PROMPTS.value:
        return "images"

    if phase == VideoAgentPhase.IMAGES.value:
        return "videos"

    if phase == VideoAgentPhase.VIDEOS.value:
        return "compose"

    if phase == VideoAgentPhase.COMPLETE.value:
        return END

    return END


# ============================================================
# Graph Builder
# ============================================================

def build_video_agent_graph() -> StateGraph:
    """비디오 에이전트 그래프 빌드"""

    graph = StateGraph(VideoAgentState)

    # 노드 추가
    graph.add_node("storyboard", storyboard_node)
    graph.add_node("prompts", prompts_node)
    graph.add_node("images", images_node)
    graph.add_node("videos", videos_node)
    graph.add_node("compose", compose_node)

    # 엣지 추가
    graph.add_edge(START, "storyboard")
    graph.add_conditional_edges("storyboard", should_continue)
    graph.add_conditional_edges("prompts", should_continue)
    graph.add_conditional_edges("images", should_continue)
    graph.add_conditional_edges("videos", should_continue)
    graph.add_conditional_edges("compose", should_continue)

    return graph


# ============================================================
# Main Interface
# ============================================================

class VideoAgentGraphV2:
    """
    비디오 에이전트 V2

    LangGraph 기반 5단계 비디오 생성 파이프라인

    Usage:
        agent = VideoAgentGraphV2()

        result = await agent.run(
            user_request="라네즈 워터뱅크 크림 광고 만들어줘",
            brand="라네즈",
            product="워터뱅크 블루 히알루로닉 크림",
            platform="Instagram",
            duration_sec=30
        )

        if result["phase"] == "complete":
            video_data = result["final_video"]["video_data"]
    """

    def __init__(self):
        """VideoAgentGraphV2 초기화"""
        self.graph = build_video_agent_graph()
        self.compiled = self.graph.compile()

    async def run(
        self,
        user_request: str,
        brand: Optional[str] = None,
        product: Optional[str] = None,
        platform: str = "Instagram",
        duration_sec: int = 30,
        style: str = "modern",
        context: Optional[Dict[str, Any]] = None
    ) -> VideoAgentState:
        """
        비디오 생성 실행

        Args:
            user_request: 사용자 요청
            brand: 브랜드명
            product: 제품명
            platform: 플랫폼
            duration_sec: 목표 길이
            style: 스타일
            context: 추가 컨텍스트 (moaDREAM 연동)

        Returns:
            최종 상태
        """
        initial_state = create_initial_state(
            user_request=user_request,
            brand=brand,
            product=product,
            platform=platform,
            duration_sec=duration_sec,
            style=style,
            context=context
        )

        result = await self.compiled.ainvoke(initial_state)

        return result

    async def run_from_context(self, context: Dict[str, Any]) -> VideoAgentState:
        """
        moaDREAM 컨텍스트에서 실행

        Args:
            context: moaDREAM 시스템 컨텍스트

        Returns:
            최종 상태
        """
        brand_info = context.get("brand_info", {})

        return await self.run(
            user_request=context.get("user_input", "Create a product advertisement"),
            brand=brand_info.get("brand") or context.get("brand"),
            product=brand_info.get("product") or context.get("product"),
            platform=context.get("platform", "Instagram"),
            duration_sec=context.get("duration_sec", 30),
            style=context.get("style", "modern"),
            context=context
        )

    def get_phase_description(self, phase: str) -> str:
        """단계 설명 반환"""
        descriptions = {
            VideoAgentPhase.INIT.value: "초기화 중...",
            VideoAgentPhase.STORYBOARD.value: "스토리보드 생성 중...",
            VideoAgentPhase.PROMPTS.value: "이미지/모션 프롬프트 생성 중...",
            VideoAgentPhase.IMAGES.value: "이미지 생성 중 (RunPod FLUX)...",
            VideoAgentPhase.VIDEOS.value: "비디오 변환 중 (RunPod Wan2.2)...",
            VideoAgentPhase.COMPOSE.value: "비디오 합성 중...",
            VideoAgentPhase.COMPLETE.value: "완료!",
            VideoAgentPhase.ERROR.value: "오류 발생"
        }
        return descriptions.get(phase, "알 수 없는 상태")
