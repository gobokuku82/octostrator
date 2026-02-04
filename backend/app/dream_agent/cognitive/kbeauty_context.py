"""K-Beauty Context Enricher - K-Beauty 도메인 컨텍스트

아모레퍼시픽 K-Beauty 도메인의 브랜드, 채널, 시장 정보를 관리합니다.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel, Field
import re


# ============================================================
# Brand Tier
# ============================================================

class BrandTier(str, Enum):
    """브랜드 티어"""
    LUXURY = "luxury"       # 럭셔리
    PREMIUM = "premium"     # 프리미엄
    MASS = "mass"           # 매스
    INDIE = "indie"         # 인디/신규


# ============================================================
# Market Region
# ============================================================

class MarketRegion(str, Enum):
    """글로벌 시장"""
    KOR = "KOR"     # 한국
    USA = "USA"     # 미국
    CHN = "CHN"     # 중국
    JPN = "JPN"     # 일본
    SEA = "SEA"     # 동남아시아
    EUR = "EUR"     # 유럽


# ============================================================
# Channel Type
# ============================================================

class ChannelType(str, Enum):
    """채널 유형"""
    BEAUTY_SPECIALTY = "beauty_specialty"  # 뷰티 전문점
    ECOMMERCE = "ecommerce"                # 이커머스
    DEPARTMENT = "department"              # 백화점
    DRUGSTORE = "drugstore"                # 드럭스토어
    SOCIAL = "social"                      # 소셜커머스
    DTC = "dtc"                            # Direct-to-Consumer


# ============================================================
# Brand Data
# ============================================================

class BrandInfo(BaseModel):
    """브랜드 정보"""
    name: str
    name_ko: str
    name_en: str
    tier: BrandTier
    parent_company: str = "아모레퍼시픽"
    categories: List[str] = Field(default_factory=list)
    key_products: List[str] = Field(default_factory=list)
    target_markets: List[MarketRegion] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class ChannelInfo(BaseModel):
    """채널 정보"""
    name: str
    name_ko: str
    name_en: str
    channel_type: ChannelType
    regions: List[MarketRegion] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    url_patterns: List[str] = Field(default_factory=list)


# ============================================================
# K-Beauty Knowledge Base
# ============================================================

# 아모레퍼시픽 브랜드 데이터
AMOREPACIFIC_BRANDS: Dict[str, BrandInfo] = {
    # Luxury
    "sulwhasoo": BrandInfo(
        name="sulwhasoo",
        name_ko="설화수",
        name_en="Sulwhasoo",
        tier=BrandTier.LUXURY,
        categories=["skincare", "anti-aging", "herbal"],
        key_products=["자음생크림", "윤조에센스", "진설크림"],
        target_markets=[MarketRegion.KOR, MarketRegion.CHN, MarketRegion.USA],
        keywords=["설화수", "sulwhasoo", "한방", "인삼", "자음생", "윤조"]
    ),
    "amorepacific": BrandInfo(
        name="amorepacific",
        name_ko="아모레퍼시픽",
        name_en="AMOREPACIFIC",
        tier=BrandTier.LUXURY,
        categories=["skincare", "premium"],
        key_products=["타임 레스폰스", "빈티지 싱글 익스트랙트"],
        target_markets=[MarketRegion.KOR, MarketRegion.USA, MarketRegion.EUR],
        keywords=["아모레퍼시픽", "amorepacific", "녹차", "제주"]
    ),

    # Premium
    "laneige": BrandInfo(
        name="laneige",
        name_ko="라네즈",
        name_en="LANEIGE",
        tier=BrandTier.PREMIUM,
        categories=["skincare", "makeup", "hydration"],
        key_products=["워터뱅크", "립슬리핑마스크", "네오쿠션"],
        target_markets=[MarketRegion.KOR, MarketRegion.USA, MarketRegion.CHN, MarketRegion.SEA],
        keywords=["라네즈", "laneige", "워터뱅크", "수분", "립슬리핑"]
    ),
    "hera": BrandInfo(
        name="hera",
        name_ko="헤라",
        name_en="HERA",
        tier=BrandTier.PREMIUM,
        categories=["makeup", "skincare"],
        key_products=["블랙쿠션", "센슈얼 파우더 매트"],
        target_markets=[MarketRegion.KOR, MarketRegion.CHN],
        keywords=["헤라", "hera", "블랙쿠션", "제니"]
    ),
    "iope": BrandInfo(
        name="iope",
        name_ko="아이오페",
        name_en="IOPE",
        tier=BrandTier.PREMIUM,
        categories=["skincare", "anti-aging"],
        key_products=["레티놀 엑스퍼트", "에어쿠션"],
        target_markets=[MarketRegion.KOR, MarketRegion.CHN],
        keywords=["아이오페", "iope", "레티놀", "바이오"]
    ),

    # Mass
    "innisfree": BrandInfo(
        name="innisfree",
        name_ko="이니스프리",
        name_en="innisfree",
        tier=BrandTier.MASS,
        categories=["skincare", "eco-friendly", "natural"],
        key_products=["그린티 씨드 세럼", "노세범 미네랄 파우더"],
        target_markets=[MarketRegion.KOR, MarketRegion.CHN, MarketRegion.SEA, MarketRegion.USA],
        keywords=["이니스프리", "innisfree", "그린티", "제주", "노세범"]
    ),
    "etude": BrandInfo(
        name="etude",
        name_ko="에뛰드",
        name_en="ETUDE",
        tier=BrandTier.MASS,
        categories=["makeup", "color cosmetics"],
        key_products=["플레이컬러 아이즈", "픽싱 틴트"],
        target_markets=[MarketRegion.KOR, MarketRegion.SEA, MarketRegion.JPN],
        keywords=["에뛰드", "etude", "플레이컬러", "하우스"]
    ),
    "mamonde": BrandInfo(
        name="mamonde",
        name_ko="마몽드",
        name_en="Mamonde",
        tier=BrandTier.MASS,
        categories=["skincare", "flower-based"],
        key_products=["로즈 워터 토너", "아쿠아 필 세럼"],
        target_markets=[MarketRegion.KOR, MarketRegion.CHN],
        keywords=["마몽드", "mamonde", "로즈", "꽃"]
    ),
    "espoir": BrandInfo(
        name="espoir",
        name_ko="에스쁘아",
        name_en="espoir",
        tier=BrandTier.PREMIUM,
        categories=["makeup", "professional"],
        key_products=["프로 테일러 비 커버리지 파운데이션", "노웨어 립스틱"],
        target_markets=[MarketRegion.KOR],
        keywords=["에스쁘아", "espoir", "프로테일러"]
    ),
    "primera": BrandInfo(
        name="primera",
        name_ko="프리메라",
        name_en="primera",
        tier=BrandTier.PREMIUM,
        categories=["skincare", "natural", "sensitive"],
        key_products=["알파인 베리 워터리 크림", "미라클 씨드 에센스"],
        target_markets=[MarketRegion.KOR],
        keywords=["프리메라", "primera", "알파인베리", "민감성"]
    ),
    "aestura": BrandInfo(
        name="aestura",
        name_ko="에스트라",
        name_en="AESTURA",
        tier=BrandTier.MASS,
        categories=["skincare", "derma", "sensitive"],
        key_products=["아토배리어 365 크림", "테라토콘 시카 크림"],
        target_markets=[MarketRegion.KOR],
        keywords=["에스트라", "aestura", "아토배리어", "시카"]
    ),
}

# 채널 데이터
CHANNELS: Dict[str, ChannelInfo] = {
    # 한국 채널
    "oliveyoung": ChannelInfo(
        name="oliveyoung",
        name_ko="올리브영",
        name_en="Olive Young",
        channel_type=ChannelType.BEAUTY_SPECIALTY,
        regions=[MarketRegion.KOR],
        keywords=["올리브영", "oliveyoung", "올영"],
        url_patterns=["oliveyoung.co.kr"]
    ),
    "coupang": ChannelInfo(
        name="coupang",
        name_ko="쿠팡",
        name_en="Coupang",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.KOR],
        keywords=["쿠팡", "coupang", "로켓배송"],
        url_patterns=["coupang.com"]
    ),
    "naver": ChannelInfo(
        name="naver",
        name_ko="네이버 쇼핑",
        name_en="Naver Shopping",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.KOR],
        keywords=["네이버", "naver", "스마트스토어"],
        url_patterns=["shopping.naver.com", "smartstore.naver.com"]
    ),
    "lotteon": ChannelInfo(
        name="lotteon",
        name_ko="롯데온",
        name_en="Lotte ON",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.KOR],
        keywords=["롯데온", "lotteon", "롯데"],
        url_patterns=["lotteon.com"]
    ),

    # 글로벌 채널
    "sephora": ChannelInfo(
        name="sephora",
        name_ko="세포라",
        name_en="Sephora",
        channel_type=ChannelType.BEAUTY_SPECIALTY,
        regions=[MarketRegion.USA, MarketRegion.EUR],
        keywords=["세포라", "sephora"],
        url_patterns=["sephora.com"]
    ),
    "amazon": ChannelInfo(
        name="amazon",
        name_ko="아마존",
        name_en="Amazon",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.USA, MarketRegion.EUR, MarketRegion.JPN],
        keywords=["아마존", "amazon"],
        url_patterns=["amazon.com", "amazon.co.jp"]
    ),
    "ulta": ChannelInfo(
        name="ulta",
        name_ko="얼타",
        name_en="Ulta Beauty",
        channel_type=ChannelType.BEAUTY_SPECIALTY,
        regions=[MarketRegion.USA],
        keywords=["얼타", "ulta"],
        url_patterns=["ulta.com"]
    ),
    "tmall": ChannelInfo(
        name="tmall",
        name_ko="티몰",
        name_en="Tmall",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.CHN],
        keywords=["티몰", "tmall", "天猫"],
        url_patterns=["tmall.com"]
    ),
    "rakuten": ChannelInfo(
        name="rakuten",
        name_ko="라쿠텐",
        name_en="Rakuten",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.JPN],
        keywords=["라쿠텐", "rakuten", "楽天"],
        url_patterns=["rakuten.co.jp"]
    ),
    "shopee": ChannelInfo(
        name="shopee",
        name_ko="쇼피",
        name_en="Shopee",
        channel_type=ChannelType.ECOMMERCE,
        regions=[MarketRegion.SEA],
        keywords=["쇼피", "shopee"],
        url_patterns=["shopee.com", "shopee.sg", "shopee.tw"]
    ),
}

# 트렌드 키워드
TREND_KEYWORDS: Dict[str, List[str]] = {
    "skincare": ["클린뷰티", "비건", "시카", "레티놀", "나이아신아마이드", "히알루론산",
                 "세라마이드", "펩타이드", "프로바이오틱스", "스킨배리어"],
    "makeup": ["글래스스킨", "글로우", "모노톤", "쿨톤", "웜톤", "블러", "톤업",
               "커버력", "지속력", "자연스러운"],
    "ingredients": ["녹차", "제주", "발효", "인삼", "한방", "센텔라", "티트리",
                   "로즈", "라벤더", "카밀레"],
    "concerns": ["민감성", "건성", "지성", "복합성", "트러블", "모공", "주름",
                 "미백", "수분", "탄력"],
}


# ============================================================
# K-Beauty Context Enricher
# ============================================================

class KBeautyContextEnricher:
    """
    K-Beauty 컨텍스트 강화기

    사용자 쿼리에서 K-Beauty 도메인 정보를 추출하고 강화합니다.
    """

    def __init__(self):
        self.brands = AMOREPACIFIC_BRANDS
        self.channels = CHANNELS
        self.trends = TREND_KEYWORDS
        self._build_keyword_maps()

    def _build_keyword_maps(self) -> None:
        """키워드 맵 구축"""
        self._brand_keywords: Dict[str, str] = {}
        self._channel_keywords: Dict[str, str] = {}

        for brand_id, brand in self.brands.items():
            for keyword in brand.keywords:
                self._brand_keywords[keyword.lower()] = brand_id

        for channel_id, channel in self.channels.items():
            for keyword in channel.keywords:
                self._channel_keywords[keyword.lower()] = channel_id

    def extract_brands(self, text: str) -> List[BrandInfo]:
        """텍스트에서 브랜드 추출"""
        text_lower = text.lower()
        found_brands = set()

        for keyword, brand_id in self._brand_keywords.items():
            if keyword in text_lower:
                found_brands.add(brand_id)

        return [self.brands[bid] for bid in found_brands]

    def extract_channels(self, text: str) -> List[ChannelInfo]:
        """텍스트에서 채널 추출"""
        text_lower = text.lower()
        found_channels = set()

        for keyword, channel_id in self._channel_keywords.items():
            if keyword in text_lower:
                found_channels.add(channel_id)

        return [self.channels[cid] for cid in found_channels]

    def extract_markets(self, text: str) -> List[MarketRegion]:
        """텍스트에서 시장 추출"""
        market_keywords = {
            MarketRegion.KOR: ["한국", "korea", "korean", "국내"],
            MarketRegion.USA: ["미국", "usa", "us", "america", "american"],
            MarketRegion.CHN: ["중국", "china", "chinese", "중화"],
            MarketRegion.JPN: ["일본", "japan", "japanese"],
            MarketRegion.SEA: ["동남아", "southeast asia", "sea", "싱가포르", "태국", "베트남"],
            MarketRegion.EUR: ["유럽", "europe", "european", "프랑스", "영국", "독일"],
        }

        text_lower = text.lower()
        found_markets = set()

        for market, keywords in market_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_markets.add(market)
                    break

        return list(found_markets)

    def extract_trends(self, text: str) -> Dict[str, List[str]]:
        """텍스트에서 트렌드 키워드 추출"""
        text_lower = text.lower()
        found_trends: Dict[str, List[str]] = {}

        for category, keywords in self.trends.items():
            matched = [kw for kw in keywords if kw.lower() in text_lower]
            if matched:
                found_trends[category] = matched

        return found_trends

    def enrich_context(self, text: str) -> Dict[str, Any]:
        """
        텍스트에서 K-Beauty 컨텍스트 추출

        Args:
            text: 사용자 쿼리 또는 문서

        Returns:
            {
                "brands": List[BrandInfo],
                "channels": List[ChannelInfo],
                "markets": List[MarketRegion],
                "trends": Dict[str, List[str]],
                "brand_tier": Optional[BrandTier],
                "entities": Dict[str, List[str]]
            }
        """
        brands = self.extract_brands(text)
        channels = self.extract_channels(text)
        markets = self.extract_markets(text)
        trends = self.extract_trends(text)

        # 대표 브랜드 티어 결정
        brand_tier = None
        if brands:
            tiers = [b.tier for b in brands]
            if BrandTier.LUXURY in tiers:
                brand_tier = BrandTier.LUXURY
            elif BrandTier.PREMIUM in tiers:
                brand_tier = BrandTier.PREMIUM
            else:
                brand_tier = BrandTier.MASS

        # 엔티티 정리
        entities = {
            "brand": [b.name_ko for b in brands],
            "channel": [c.name_ko for c in channels],
            "market": [m.value for m in markets],
        }

        return {
            "brands": brands,
            "channels": channels,
            "markets": markets,
            "trends": trends,
            "brand_tier": brand_tier,
            "entities": entities,
            "has_context": bool(brands or channels or markets or trends)
        }

    def get_brand_by_name(self, name: str) -> Optional[BrandInfo]:
        """브랜드 이름으로 조회"""
        name_lower = name.lower()

        # 정확한 매치
        if name_lower in self.brands:
            return self.brands[name_lower]

        # 키워드 매치
        if name_lower in self._brand_keywords:
            brand_id = self._brand_keywords[name_lower]
            return self.brands[brand_id]

        return None

    def get_channel_by_name(self, name: str) -> Optional[ChannelInfo]:
        """채널 이름으로 조회"""
        name_lower = name.lower()

        if name_lower in self.channels:
            return self.channels[name_lower]

        if name_lower in self._channel_keywords:
            channel_id = self._channel_keywords[name_lower]
            return self.channels[channel_id]

        return None

    def get_brands_by_tier(self, tier: BrandTier) -> List[BrandInfo]:
        """티어별 브랜드 목록"""
        return [b for b in self.brands.values() if b.tier == tier]

    def get_channels_by_region(self, region: MarketRegion) -> List[ChannelInfo]:
        """지역별 채널 목록"""
        return [c for c in self.channels.values() if region in c.regions]

    def normalize_brand_name(self, name: str) -> Optional[str]:
        """브랜드 이름 정규화"""
        brand = self.get_brand_by_name(name)
        return brand.name_en.upper() if brand else None

    def normalize_channel_name(self, name: str) -> Optional[str]:
        """채널 이름 정규화"""
        channel = self.get_channel_by_name(name)
        return channel.name_en.upper() if channel else None

    def to_llm_context(self) -> str:
        """LLM 컨텍스트용 문자열 생성"""
        lines = ["# K-Beauty Domain Context\n"]

        lines.append("## Amorepacific Brands")
        for tier in [BrandTier.LUXURY, BrandTier.PREMIUM, BrandTier.MASS]:
            tier_brands = self.get_brands_by_tier(tier)
            lines.append(f"\n### {tier.value.title()}")
            for b in tier_brands:
                lines.append(f"- {b.name_ko} ({b.name_en}): {', '.join(b.categories)}")

        lines.append("\n## Major Channels")
        for region in MarketRegion:
            region_channels = self.get_channels_by_region(region)
            if region_channels:
                lines.append(f"\n### {region.value}")
                for c in region_channels:
                    lines.append(f"- {c.name_ko} ({c.name_en})")

        return "\n".join(lines)


# ============================================================
# Global Instance
# ============================================================

_enricher: Optional[KBeautyContextEnricher] = None


def get_enricher() -> KBeautyContextEnricher:
    """전역 Enricher 인스턴스 반환"""
    global _enricher
    if _enricher is None:
        _enricher = KBeautyContextEnricher()
    return _enricher
