"""Storyboard Agent Tool - 광고 스토리보드 생성

마케팅/광고 콘텐츠의 스토리보드를 JSON/Markdown 형식으로 생성합니다.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.app.dream_agent.biz_execution.base_tool import (
    BaseBizTool,
    BizResult,
    BizResultStatus,
    BizResultMetadata,
    ApprovalType,
    ValidationResult
)
from backend.app.dream_agent.biz_execution.tool_registry import register_tool
from backend.app.dream_agent.models.todo import TodoItem


# ============================================================
# Storyboard Templates
# ============================================================

STORYBOARD_TEMPLATES = {
    "instagram": {
        "name": "Instagram Reel/Story",
        "duration_sec": 30,
        "aspect_ratio": "9:16",
        "scenes": 5,
        "scene_duration": 6
    },
    "youtube": {
        "name": "YouTube Short",
        "duration_sec": 60,
        "aspect_ratio": "9:16",
        "scenes": 8,
        "scene_duration": 7.5
    },
    "tiktok": {
        "name": "TikTok Video",
        "duration_sec": 30,
        "aspect_ratio": "9:16",
        "scenes": 6,
        "scene_duration": 5
    },
    "tv_ad": {
        "name": "TV Commercial",
        "duration_sec": 15,
        "aspect_ratio": "16:9",
        "scenes": 4,
        "scene_duration": 3.75
    }
}

STYLE_PROMPTS = {
    "modern": "미니멀하고 세련된 현대적 스타일, 깔끔한 라인, 밝은 조명",
    "classic": "클래식하고 우아한 스타일, 부드러운 톤, 고급스러운 분위기",
    "playful": "밝고 활기찬 스타일, 비비드한 컬러, 다이나믹한 움직임",
    "luxury": "럭셔리하고 프리미엄한 스타일, 골드 액센트, 고급 질감"
}


@register_tool
class StoryboardAgentTool(BaseBizTool):
    """
    스토리보드 생성 도구

    광고/마케팅 콘텐츠의 스토리보드를 생성합니다.
    """

    name = "storyboard_agent"
    description = "광고/마케팅 콘텐츠 스토리보드 생성"
    version = "1.0.0"

    requires_approval = True
    approval_type = ApprovalType.PREVIEW

    is_async = False
    estimated_duration_sec = 60

    required_input_types = []
    output_type = "storyboard"

    has_cost = False

    def __init__(self):
        super().__init__()
        self.content_types = list(STORYBOARD_TEMPLATES.keys())
        self.styles = list(STYLE_PROMPTS.keys())

    def validate_input(self, todo: TodoItem, context: Dict[str, Any]) -> ValidationResult:
        """입력 검증"""
        errors = []
        warnings = []

        params = todo.metadata.execution.tool_params
        content_type = params.get("content_type", "instagram")
        style = params.get("style", "modern")

        if content_type not in self.content_types:
            errors.append(f"Unknown content_type: {content_type}. Supported: {self.content_types}")

        if style not in self.styles:
            warnings.append(f"Unknown style '{style}', using 'modern'")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    async def execute(
        self,
        todo: TodoItem,
        context: Dict[str, Any],
        log: Any
    ) -> BizResult:
        """스토리보드 생성 실행"""
        start_time = datetime.now()

        try:
            params = todo.metadata.execution.tool_params
            content_type = params.get("content_type", "instagram")
            duration_sec = params.get("duration_sec", STORYBOARD_TEMPLATES[content_type]["duration_sec"])
            style = params.get("style", "modern")

            # 컨텍스트에서 브랜드/인사이트 정보 추출
            brand_info = self._extract_brand_info(context)
            insights = context.get("insights", {}).get("insights", [])

            # 스토리보드 생성
            storyboard = self._generate_storyboard(
                content_type=content_type,
                duration_sec=duration_sec,
                style=style,
                brand_info=brand_info,
                insights=insights
            )

            # JSON 저장
            json_path = self._save_storyboard_json(storyboard)

            # Markdown 저장
            md_content = self._generate_storyboard_markdown(storyboard)
            md_path = self._save_storyboard_markdown(md_content)

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return self.create_result(
                todo=todo,
                status=BizResultStatus.SUCCESS,
                result_type="storyboard",
                output_path=str(json_path),
                output_data={
                    "storyboard": storyboard,
                    "markdown_path": str(md_path)
                },
                summary=f"스토리보드 생성 완료 ({content_type}, {duration_sec}초)",
                preview=md_content[:800] + "..." if len(md_content) > 800 else md_content,
                metadata=BizResultMetadata(
                    processing_time_ms=processing_time
                )
            )

        except Exception as e:
            return self.create_error_result(
                todo=todo,
                error_message=str(e),
                error_code="STORYBOARD_GENERATION_ERROR"
            )

    def _extract_brand_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """브랜드 정보 추출"""
        return {
            "brand": context.get("brand", "라네즈"),
            "product": context.get("product", "워터뱅크 블루 히알루로닉 크림"),
            "key_benefit": context.get("key_benefit", "72시간 수분 지속"),
            "target_audience": context.get("target_audience", "2030 여성"),
            "channel": context.get("source", "올리브영")
        }

    def _generate_storyboard(
        self,
        content_type: str,
        duration_sec: int,
        style: str,
        brand_info: Dict[str, Any],
        insights: List[str]
    ) -> Dict[str, Any]:
        """스토리보드 생성"""
        template = STORYBOARD_TEMPLATES[content_type]
        style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["modern"])

        # 씬 수 계산
        num_scenes = template["scenes"]
        scene_duration = duration_sec / num_scenes

        # 씬 생성
        scenes = self._generate_scenes(
            num_scenes=num_scenes,
            scene_duration=scene_duration,
            brand_info=brand_info,
            insights=insights,
            style_prompt=style_prompt
        )

        return {
            "id": f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "content_type": content_type,
            "platform": template["name"],
            "duration_sec": duration_sec,
            "aspect_ratio": template["aspect_ratio"],
            "style": style,
            "style_description": style_prompt,
            "brand": brand_info,
            "created_at": datetime.now().isoformat(),
            "scenes": scenes,
            "audio": self._generate_audio_spec(duration_sec, brand_info),
            "metadata": {
                "version": "1.0",
                "generator": "moaDREAM StoryboardAgent"
            }
        }

    def _generate_scenes(
        self,
        num_scenes: int,
        scene_duration: float,
        brand_info: Dict[str, Any],
        insights: List[str],
        style_prompt: str
    ) -> List[Dict[str, Any]]:
        """씬 생성"""
        brand = brand_info["brand"]
        product = brand_info["product"]
        benefit = brand_info["key_benefit"]

        # 기본 씬 템플릿
        scene_templates = [
            {
                "type": "hook",
                "description": f"문제 제기: 건조한 피부로 고민하는 모습",
                "visual": "클로즈업, 건조한 피부 질감",
                "text_overlay": "피부가 당기고 건조하다면?",
                "transition": "fade"
            },
            {
                "type": "problem",
                "description": f"일상에서 느끼는 불편함",
                "visual": "일상 장면, 거울을 보는 모습",
                "text_overlay": "하루 종일 촉촉함이 필요해",
                "transition": "slide"
            },
            {
                "type": "solution_intro",
                "description": f"{brand} {product} 소개",
                "visual": f"제품 히어로 샷, {style_prompt}",
                "text_overlay": f"NEW {product}",
                "transition": "zoom"
            },
            {
                "type": "benefit",
                "description": f"핵심 베네핏: {benefit}",
                "visual": "제품 사용 장면, 수분감 표현",
                "text_overlay": benefit,
                "transition": "slide"
            },
            {
                "type": "usage",
                "description": "제품 사용법 시연",
                "visual": "적용 과정, 텍스처 클로즈업",
                "text_overlay": "부드럽게 발라주세요",
                "transition": "fade"
            },
            {
                "type": "result",
                "description": "사용 후 결과",
                "visual": "광채나는 피부, 만족스러운 표정",
                "text_overlay": "촉촉하게 빛나는 피부",
                "transition": "slide"
            },
            {
                "type": "social_proof",
                "description": "고객 반응/리뷰",
                "visual": "리뷰 하이라이트, 별점",
                "text_overlay": insights[0] if insights else "⭐ 4.8점 만족도",
                "transition": "fade"
            },
            {
                "type": "cta",
                "description": "콜투액션",
                "visual": f"제품 팩샷, {brand} 로고",
                "text_overlay": f"{brand} 공식몰에서 만나보세요",
                "transition": "fade"
            }
        ]

        # 필요한 씬 수만큼 선택
        selected_scenes = scene_templates[:num_scenes]

        scenes = []
        current_time = 0

        for i, template in enumerate(selected_scenes):
            scenes.append({
                "scene_number": i + 1,
                "start_time": round(current_time, 2),
                "end_time": round(current_time + scene_duration, 2),
                "duration": round(scene_duration, 2),
                **template,
                "camera": self._get_camera_direction(template["type"]),
                "image_prompt": f"{template['visual']}, {style_prompt}, {brand} 브랜드 스타일"
            })
            current_time += scene_duration

        return scenes

    def _get_camera_direction(self, scene_type: str) -> str:
        """씬 타입별 카메라 디렉션"""
        directions = {
            "hook": "클로즈업, 슬로우 모션",
            "problem": "미디엄 샷, 자연스러운 움직임",
            "solution_intro": "와이드 to 클로즈업, 다이나믹 줌",
            "benefit": "클로즈업, 텍스처 강조",
            "usage": "오버헤드 샷, 핸드 모델",
            "result": "미디엄 클로즈업, 소프트 라이팅",
            "social_proof": "모션 그래픽, 텍스트 애니메이션",
            "cta": "풀 샷, 브랜드 그리드"
        }
        return directions.get(scene_type, "미디엄 샷")

    def _generate_audio_spec(self, duration_sec: int, brand_info: Dict[str, Any]) -> Dict[str, Any]:
        """오디오 스펙 생성"""
        return {
            "background_music": {
                "mood": "uplifting, modern, fresh",
                "tempo": "medium (100-120 BPM)",
                "duration": duration_sec
            },
            "voiceover": {
                "tone": "친근하고 신뢰감 있는",
                "language": "ko",
                "script_outline": f"{brand_info['brand']} {brand_info['product']}로 {brand_info['key_benefit']}을 경험하세요"
            },
            "sound_effects": [
                {"time": 0, "effect": "soft intro"},
                {"time": duration_sec - 3, "effect": "logo reveal"}
            ]
        }

    def _generate_storyboard_markdown(self, storyboard: Dict[str, Any]) -> str:
        """Markdown 형식 스토리보드 생성"""
        lines = [
            f"# 🎬 스토리보드: {storyboard['brand']['brand']} {storyboard['brand']['product']}",
            "",
            "## 📋 개요",
            f"- **플랫폼**: {storyboard['platform']}",
            f"- **총 길이**: {storyboard['duration_sec']}초",
            f"- **화면 비율**: {storyboard['aspect_ratio']}",
            f"- **스타일**: {storyboard['style']} - {storyboard['style_description']}",
            "",
            "---",
            "",
            "## 🎞️ 씬 구성",
            ""
        ]

        for scene in storyboard["scenes"]:
            lines.extend([
                f"### Scene {scene['scene_number']}: {scene['type'].upper()}",
                f"**시간**: {scene['start_time']}s - {scene['end_time']}s ({scene['duration']}s)",
                "",
                f"📷 **비주얼**: {scene['visual']}",
                "",
                f"🎥 **카메라**: {scene['camera']}",
                "",
                f"💬 **텍스트 오버레이**: \"{scene['text_overlay']}\"",
                "",
                f"➡️ **전환**: {scene['transition']}",
                "",
                f"🎨 **이미지 프롬프트**:",
                f"> {scene['image_prompt']}",
                "",
                "---",
                ""
            ])

        lines.extend([
            "## 🎵 오디오",
            f"- **배경음악**: {storyboard['audio']['background_music']['mood']}",
            f"- **템포**: {storyboard['audio']['background_music']['tempo']}",
            f"- **보이스오버**: {storyboard['audio']['voiceover']['script_outline']}",
            "",
            "---",
            f"*Generated by moaDREAM StoryboardAgent | {storyboard['created_at']}*"
        ])

        return "\n".join(lines)

    def _save_storyboard_json(self, storyboard: Dict[str, Any]) -> Path:
        """JSON 저장"""
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        output_dir = project_root / "data/output/storyboards"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{storyboard['id']}.json"
        output_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

        return output_path

    def _save_storyboard_markdown(self, content: str) -> Path:
        """Markdown 저장"""
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        output_dir = project_root / "data/output/storyboards"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"storyboard_{timestamp}.md"
        output_path.write_text(content, encoding="utf-8")

        return output_path
