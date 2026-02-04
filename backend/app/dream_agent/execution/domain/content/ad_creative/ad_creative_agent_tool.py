"""Ad Creative Agent Tool - 광고 크리에이티브 생성

광고 카피, 해시태그, 캡션을 다양한 플랫폼에 맞게 생성합니다.
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
# Platform-specific Configurations
# ============================================================

PLATFORM_CONFIGS = {
    "instagram": {
        "name": "Instagram",
        "max_caption_length": 2200,
        "max_hashtags": 30,
        "optimal_hashtags": 11,
        "caption_style": "engaging, emoji-friendly, story-telling"
    },
    "facebook": {
        "name": "Facebook",
        "max_caption_length": 63206,
        "max_hashtags": 10,
        "optimal_hashtags": 5,
        "caption_style": "informative, conversational, community-focused"
    },
    "tiktok": {
        "name": "TikTok",
        "max_caption_length": 300,
        "max_hashtags": 10,
        "optimal_hashtags": 5,
        "caption_style": "trendy, casual, viral-potential"
    },
    "youtube": {
        "name": "YouTube",
        "max_caption_length": 5000,
        "max_hashtags": 15,
        "optimal_hashtags": 5,
        "caption_style": "SEO-optimized, descriptive, clickable"
    },
    "naver": {
        "name": "Naver Blog/Post",
        "max_caption_length": 10000,
        "max_hashtags": 30,
        "optimal_hashtags": 10,
        "caption_style": "informative, detailed, keyword-rich"
    }
}

TONE_CONFIGS = {
    "professional": {
        "adjectives": ["프리미엄", "전문적인", "신뢰할 수 있는", "검증된"],
        "style": "격식체, 전문 용어 사용",
        "emoji_level": "minimal"
    },
    "casual": {
        "adjectives": ["편안한", "친근한", "자연스러운", "일상적인"],
        "style": "반말체, 친근한 표현",
        "emoji_level": "moderate"
    },
    "playful": {
        "adjectives": ["재미있는", "신나는", "특별한", "트렌디한"],
        "style": "밈, 유행어 사용",
        "emoji_level": "heavy"
    },
    "luxury": {
        "adjectives": ["럭셔리한", "프레스티지", "고급스러운", "특별한"],
        "style": "격식체, 고급 어휘",
        "emoji_level": "minimal"
    }
}

# K-Beauty 해시태그 데이터베이스
HASHTAG_DATABASE = {
    "general": [
        "#뷰티", "#스킨케어", "#화장품", "#코스메틱", "#데일리뷰티",
        "#beauty", "#skincare", "#kbeauty", "#koreanbeauty", "#cosmetics"
    ],
    "skincare": [
        "#스킨케어루틴", "#피부관리", "#수분케어", "#보습", "#피부고민",
        "#skincareroutine", "#skincaretips", "#glowingskin", "#healthyskin"
    ],
    "makeup": [
        "#메이크업", "#데일리메이크업", "#립스틱", "#쿠션팩트", "#아이메이크업",
        "#makeup", "#makeuptutorial", "#koreanmakeup", "#dailymakeup"
    ],
    "brand": {
        "laneige": ["#라네즈", "#워터뱅크", "#립슬리핑마스크", "#laneige"],
        "sulwhasoo": ["#설화수", "#자음생", "#윤조에센스", "#sulwhasoo"],
        "innisfree": ["#이니스프리", "#그린티", "#제주", "#innisfree"],
        "hera": ["#헤라", "#블랙쿠션", "#hera"],
        "etude": ["#에뛰드", "#플레이컬러", "#etude"]
    },
    "trending": [
        "#뷰티인사이드", "#화장품추천", "#스킨케어추천", "#피부맛집",
        "#오늘의뷰티", "#뷰티꿀팁", "#뷰티스타그램", "#화장품스타그램"
    ]
}


@register_tool
class AdCreativeAgentTool(BaseBizTool):
    """
    광고 크리에이티브 생성 도구

    플랫폼별 최적화된 광고 카피와 해시태그를 생성합니다.
    """

    name = "ad_creative_agent"
    description = "광고 카피, 해시태그, 캡션 생성"
    version = "1.0.0"

    requires_approval = True
    approval_type = ApprovalType.RESULT  # 결과 검토 후 승인

    is_async = False
    estimated_duration_sec = 30

    required_input_types = []
    output_type = "ad_creative"

    has_cost = False

    def __init__(self):
        super().__init__()
        self.platforms = list(PLATFORM_CONFIGS.keys())
        self.tones = list(TONE_CONFIGS.keys())

    def validate_input(self, todo: TodoItem, context: Dict[str, Any]) -> ValidationResult:
        """입력 검증"""
        errors = []
        warnings = []

        params = todo.metadata.execution.tool_params
        platform = params.get("platform", "instagram")
        tone = params.get("tone", "professional")
        language = params.get("language", "ko")

        if platform not in self.platforms:
            errors.append(f"Unknown platform: {platform}. Supported: {self.platforms}")

        if tone not in self.tones:
            warnings.append(f"Unknown tone '{tone}', using 'professional'")

        if language not in ["ko", "en", "ja", "zh"]:
            warnings.append(f"Unsupported language '{language}', using 'ko'")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    async def execute(
        self,
        todo: TodoItem,
        context: Dict[str, Any],
        log: Any
    ) -> BizResult:
        """광고 크리에이티브 생성 실행"""
        start_time = datetime.now()

        try:
            params = todo.metadata.execution.tool_params
            platform = params.get("platform", "instagram")
            tone = params.get("tone", "professional")
            language = params.get("language", "ko")

            # 컨텍스트에서 브랜드/인사이트 정보 추출
            brand_info = self._extract_brand_info(context)
            insights = context.get("insights", {}).get("insights", [])

            # 크리에이티브 생성
            creative = self._generate_creative(
                platform=platform,
                tone=tone,
                language=language,
                brand_info=brand_info,
                insights=insights
            )

            # 파일 저장
            output_path = self._save_creative(creative)

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return self.create_result(
                todo=todo,
                status=BizResultStatus.SUCCESS,
                result_type="ad_creative",
                output_path=str(output_path),
                output_data=creative,
                summary=f"광고 크리에이티브 생성 완료 ({platform}, {tone})",
                preview=self._format_preview(creative),
                metadata=BizResultMetadata(
                    processing_time_ms=processing_time
                )
            )

        except Exception as e:
            return self.create_error_result(
                todo=todo,
                error_message=str(e),
                error_code="AD_CREATIVE_GENERATION_ERROR"
            )

    def _extract_brand_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """브랜드 정보 추출"""
        return {
            "brand": context.get("brand", "라네즈"),
            "product": context.get("product", "워터뱅크 블루 히알루로닉 크림"),
            "key_benefit": context.get("key_benefit", "72시간 수분 지속"),
            "target_audience": context.get("target_audience", "2030 여성"),
            "category": context.get("category", "skincare")
        }

    def _generate_creative(
        self,
        platform: str,
        tone: str,
        language: str,
        brand_info: Dict[str, Any],
        insights: List[str]
    ) -> Dict[str, Any]:
        """크리에이티브 생성"""
        platform_config = PLATFORM_CONFIGS[platform]
        tone_config = TONE_CONFIGS.get(tone, TONE_CONFIGS["professional"])

        # 헤드라인 생성
        headlines = self._generate_headlines(brand_info, tone_config)

        # 본문 카피 생성
        body_copy = self._generate_body_copy(
            brand_info, insights, platform_config, tone_config
        )

        # 해시태그 생성
        hashtags = self._generate_hashtags(
            brand_info, platform_config["optimal_hashtags"]
        )

        # CTA 생성
        cta = self._generate_cta(platform, tone)

        return {
            "id": f"creative_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "platform": platform,
            "platform_name": platform_config["name"],
            "tone": tone,
            "language": language,
            "brand": brand_info["brand"],
            "product": brand_info["product"],
            "created_at": datetime.now().isoformat(),
            "content": {
                "headlines": headlines,
                "body_copy": body_copy,
                "cta": cta,
                "hashtags": hashtags
            },
            "full_caption": self._compose_full_caption(
                headlines[0], body_copy, cta, hashtags
            ),
            "variations": self._generate_variations(brand_info, tone_config),
            "metadata": {
                "char_count": len(body_copy),
                "hashtag_count": len(hashtags),
                "platform_optimized": True
            }
        }

    def _generate_headlines(
        self,
        brand_info: Dict[str, Any],
        tone_config: Dict[str, Any]
    ) -> List[str]:
        """헤드라인 생성"""
        brand = brand_info["brand"]
        product = brand_info["product"]
        benefit = brand_info["key_benefit"]

        templates = [
            f"✨ {product}로 {benefit}을 경험하세요",
            f"💧 {brand}가 선사하는 {benefit}",
            f"🌟 {benefit}의 비밀, {product}",
            f"💎 {brand} NEW! {product}",
            f"🔥 지금 핫한 {product}"
        ]

        # 톤에 따라 조정
        if tone_config.get("emoji_level") == "minimal":
            templates = [t.replace("✨ ", "").replace("💧 ", "").replace("🌟 ", "").replace("💎 ", "").replace("🔥 ", "") for t in templates]

        return templates[:3]

    def _generate_body_copy(
        self,
        brand_info: Dict[str, Any],
        insights: List[str],
        platform_config: Dict[str, Any],
        tone_config: Dict[str, Any]
    ) -> str:
        """본문 카피 생성"""
        brand = brand_info["brand"]
        product = brand_info["product"]
        benefit = brand_info["key_benefit"]
        target = brand_info["target_audience"]

        # 인사이트 활용
        insight_text = ""
        if insights:
            insight_text = f"\n\n📊 {insights[0]}"

        copy = f"""
{brand}의 {product}을 소개합니다!

💧 {benefit}으로 하루 종일 촉촉한 피부를 유지하세요.

✅ 수분 충전
✅ 피부 장벽 강화
✅ 산뜻한 마무리

{target}을 위한 완벽한 선택!{insight_text}
        """.strip()

        # 플랫폼 길이 제한 적용
        max_length = platform_config["max_caption_length"]
        if len(copy) > max_length:
            copy = copy[:max_length - 3] + "..."

        return copy

    def _generate_hashtags(
        self,
        brand_info: Dict[str, Any],
        num_hashtags: int
    ) -> List[str]:
        """해시태그 생성"""
        hashtags = []

        # 브랜드 해시태그
        brand_lower = brand_info["brand"].lower().replace(" ", "")
        brand_tags = HASHTAG_DATABASE["brand"].get(brand_lower, [f"#{brand_info['brand']}"])
        hashtags.extend(brand_tags[:2])

        # 카테고리 해시태그
        category = brand_info.get("category", "skincare")
        if category in HASHTAG_DATABASE:
            hashtags.extend(HASHTAG_DATABASE[category][:3])

        # 일반 뷰티 해시태그
        hashtags.extend(HASHTAG_DATABASE["general"][:3])

        # 트렌딩 해시태그
        hashtags.extend(HASHTAG_DATABASE["trending"][:2])

        # 중복 제거 및 개수 제한
        unique_hashtags = list(dict.fromkeys(hashtags))
        return unique_hashtags[:num_hashtags]

    def _generate_cta(self, platform: str, tone: str) -> str:
        """CTA 생성"""
        ctas = {
            "instagram": {
                "professional": "프로필 링크에서 자세히 알아보세요 👆",
                "casual": "링크 타고 구경하러 가요! 🏃‍♀️",
                "playful": "지금 바로 GET 하러 가자! 🛒✨",
                "luxury": "공식 부티크에서 만나보세요"
            },
            "facebook": {
                "professional": "더 알아보기 버튼을 클릭하세요",
                "casual": "궁금하면 클릭!",
                "playful": "지금 바로 확인해보세요! 👀",
                "luxury": "자세한 내용을 확인하세요"
            },
            "tiktok": {
                "professional": "bio 링크 확인! 🔗",
                "casual": "링크 고고! 🏃",
                "playful": "안 보면 후회함 ㄹㅇ 👀",
                "luxury": "bio에서 만나요 ✨"
            },
            "youtube": {
                "professional": "설명란 링크를 확인해주세요",
                "casual": "설명란에 링크 있어요!",
                "playful": "구독! 좋아요! 알림설정! 🔔",
                "luxury": "더 많은 정보는 설명란에서"
            },
            "naver": {
                "professional": "자세한 정보는 아래 링크를 참조하세요",
                "casual": "더 궁금하면 링크 클릭!",
                "playful": "꿀팁 더 보러 가기 👇",
                "luxury": "공식 사이트에서 확인하세요"
            }
        }

        return ctas.get(platform, {}).get(tone, "자세히 알아보기")

    def _compose_full_caption(
        self,
        headline: str,
        body: str,
        cta: str,
        hashtags: List[str]
    ) -> str:
        """전체 캡션 조합"""
        hashtag_str = " ".join(hashtags)

        return f"""{headline}

{body}

{cta}

.
.
.
{hashtag_str}"""

    def _generate_variations(
        self,
        brand_info: Dict[str, Any],
        tone_config: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """A/B 테스트용 변형 생성"""
        brand = brand_info["brand"]
        product = brand_info["product"]
        benefit = brand_info["key_benefit"]

        return [
            {
                "name": "Variation A - 질문형",
                "headline": f"피부가 건조해서 고민이신가요? {product}로 해결하세요!",
                "hook": "문제 제기 → 솔루션 제시"
            },
            {
                "name": "Variation B - 후기형",
                "headline": f"⭐4.8점! {product} 써본 후기",
                "hook": "소셜 프루프 강조"
            },
            {
                "name": "Variation C - 혜택형",
                "headline": f"🎁 {brand} {product} 특별 할인 진행 중!",
                "hook": "프로모션/할인 강조"
            }
        ]

    def _format_preview(self, creative: Dict[str, Any]) -> str:
        """미리보기 포맷팅"""
        content = creative["content"]
        return f"""
📝 헤드라인: {content['headlines'][0]}

📄 본문:
{content['body_copy'][:200]}...

🏷️ 해시태그: {' '.join(content['hashtags'][:5])}...

🔗 CTA: {content['cta']}
        """.strip()

    def _save_creative(self, creative: Dict[str, Any]) -> Path:
        """크리에이티브 저장"""
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        output_dir = project_root / "data/output/ad_creatives"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{creative['id']}.json"
        output_path.write_text(
            json.dumps(creative, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return output_path
