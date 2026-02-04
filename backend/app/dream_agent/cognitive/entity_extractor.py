"""Entity Extractor - 고도화된 엔티티 추출기

Phase 1: Cognitive Layer 고도화
정교한 Entity 추출, Validation, Normalization 지원
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, validator

from backend.app.core.logging import get_logger, LogContext
from backend.app.dream_agent.llm_manager import get_llm_client

logger = get_logger(__name__)


# ============================================================
# Entity Types
# ============================================================

class EntityType(str, Enum):
    """추출 가능한 엔티티 타입"""

    # Data source entities
    DATA_SOURCE = "data_source"
    DATABASE = "database"
    API = "api"
    FILE = "file"

    # Temporal entities
    TIME_RANGE = "time_range"
    DATE = "date"
    PERIOD = "period"

    # Business entities
    BRAND = "brand"
    PRODUCT = "product"
    CATEGORY = "category"
    CHANNEL = "channel"
    MARKET = "market"
    REGION = "region"

    # Metric entities
    METRIC = "metric"
    KPI = "kpi"
    DIMENSION = "dimension"

    # Filter entities
    FILTER = "filter"
    CONDITION = "condition"

    # Output entities
    OUTPUT_FORMAT = "output_format"
    RECIPIENT = "recipient"
    DESTINATION = "destination"

    # Other
    KEYWORD = "keyword"
    TAG = "tag"


# ============================================================
# Entity Models
# ============================================================

class DataSourceEntity(BaseModel):
    """데이터 소스 엔티티"""
    type: str = "ecommerce"  # ecommerce, social, search, etc.
    name: str                 # amazon, coupang, naver, etc.
    region: Optional[str] = "kr"
    categories: List[str] = Field(default_factory=list)
    credentials: Optional[str] = None


class TimeRangeEntity(BaseModel):
    """시간 범위 엔티티"""
    start: Optional[str] = None  # ISO format or relative (e.g., "7 days ago")
    end: Optional[str] = None
    granularity: str = "daily"   # hourly, daily, weekly, monthly
    relative: bool = False        # Whether it's a relative time (e.g., "last week")

    @validator("start", "end")
    def validate_datetime(cls, v):
        """Validate datetime format"""
        if v and not cls._is_valid_datetime(v):
            # Try to parse relative time
            if "ago" in v or "last" in v or "this" in v:
                return v  # Will be resolved later
            raise ValueError(f"Invalid datetime format: {v}")
        return v

    @staticmethod
    def _is_valid_datetime(dt_str: str) -> bool:
        """Check if string is valid ISO datetime"""
        try:
            datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return True
        except:
            return False


class MetricEntity(BaseModel):
    """측정 지표 엔티티"""
    name: str
    aggregation: Optional[str] = "sum"  # sum, avg, count, min, max
    unit: Optional[str] = None           # USD, KRW, %, etc.


class FilterEntity(BaseModel):
    """필터 엔티티"""
    field: str
    operator: str  # ==, !=, >, <, >=, <=, in, not in, contains
    value: Any


class OutputEntity(BaseModel):
    """출력 설정 엔티티"""
    format: str = "json"  # json, csv, pdf, xlsx, dashboard
    destination: Optional[str] = None
    recipients: List[str] = Field(default_factory=list)
    template: Optional[str] = None


class ExtractedEntity(BaseModel):
    """추출된 엔티티 (통합)"""
    entity_type: EntityType
    raw_value: str                    # 원본 값
    normalized_value: Optional[Any] = None  # 정규화된 값
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Structured data (if applicable)
    structured_data: Optional[Any] = None


# ============================================================
# Entity Extractor
# ============================================================

class EntityExtractor:
    """고도화된 엔티티 추출기"""

    def __init__(self):
        self.llm_client = get_llm_client()
        self.log = LogContext(logger, node="EntityExtractor")

        # Predefined entity patterns (for quick extraction)
        self.patterns = {
            "date": [
                r'\d{4}-\d{2}-\d{2}',
                r'\d{4}/\d{2}/\d{2}',
                r'(오늘|어제|내일)',
                r'(이번|지난|다음)\s*(주|월|년)',
                r'\d+\s*(일|주|달|개월|년)\s*전',
            ],
            "brand": [
                r'(설화수|라네즈|헤라|이니스프리|에뛰드)',
                r'(SULWHASOO|LANEIGE|HERA|INNISFREE|ETUDE)',
            ],
            "channel": [
                r'(올리브영|쿠팡|네이버|아마존|G마켓)',
                r'(OLIVEYOUNG|COUPANG|NAVER|AMAZON|GMARKET)',
            ],
            "metric": [
                r'(매출|판매량|조회수|전환율|클릭율)',
                r'(sales|revenue|views|conversion|CTR)',
            ],
        }

    async def extract(
        self,
        user_input: str,
        intent: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[ExtractedEntity]]:
        """
        통합 엔티티 추출

        Args:
            user_input: 사용자 입력
            intent: 분류된 Intent (optional)
            context: 이전 대화 컨텍스트 (optional)

        Returns:
            엔티티 타입별 추출된 엔티티 목록
        """
        self.log.info(f"Extracting entities from: '{user_input[:50]}...'")

        entities: Dict[str, List[ExtractedEntity]] = {}

        try:
            # Step 1: Pattern-based quick extraction
            pattern_entities = self._extract_with_patterns(user_input)

            # Step 2: LLM-based comprehensive extraction
            llm_entities = await self._extract_with_llm(user_input, intent, context)

            # Step 3: Merge and deduplicate
            entities = self._merge_entities(pattern_entities, llm_entities)

            # Step 4: Validation
            entities = self._validate_entities(entities)

            # Step 5: Normalization
            entities = await self._normalize_entities(entities)

            self.log.info(
                f"Extracted {sum(len(v) for v in entities.values())} entities "
                f"across {len(entities)} types"
            )

        except Exception as e:
            self.log.error(f"Entity extraction error: {e}", exc_info=True)

        return entities

    def _extract_with_patterns(self, user_input: str) -> Dict[str, List[ExtractedEntity]]:
        """패턴 기반 빠른 추출"""

        entities: Dict[str, List[ExtractedEntity]] = {}

        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, user_input, re.IGNORECASE)
                for match in matches:
                    value = match.group(0)

                    entity = ExtractedEntity(
                        entity_type=self._pattern_to_entity_type(entity_type),
                        raw_value=value,
                        confidence=0.7,  # Pattern-based is less confident
                        metadata={"method": "pattern"}
                    )

                    if entity_type not in entities:
                        entities[entity_type] = []
                    entities[entity_type].append(entity)

        return entities

    async def _extract_with_llm(
        self,
        user_input: str,
        intent: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[ExtractedEntity]]:
        """LLM 기반 포괄적 추출"""

        system_prompt = """당신은 엔티티 추출 전문가입니다.
사용자 입력에서 다음 엔티티들을 추출하세요:

**Data Source**: 데이터 소스 (예: amazon, coupang, naver)
**Time Range**: 시간 범위 (예: 2026-01-01 ~ 2026-01-13, 지난주, 최근 30일)
**Brand**: 브랜드명
**Product**: 제품명
**Category**: 카테고리
**Channel**: 채널 (예: 올리브영, 쿠팡)
**Metric**: 측정 지표 (예: 매출, 조회수, 전환율)
**Filter**: 필터 조건 (예: 가격 > 10000, 평점 >= 4.0)
**Output Format**: 출력 형식 (예: PDF, Excel, Dashboard)

JSON 형식으로 응답하세요:
{
    "data_sources": [
        {
            "name": "amazon",
            "type": "ecommerce",
            "region": "kr",
            "confidence": 0.95
        }
    ],
    "time_range": {
        "start": "2026-01-01",
        "end": "2026-01-13",
        "granularity": "daily",
        "confidence": 0.9
    },
    "brands": [...],
    "metrics": [...],
    "filters": [...],
    "output_format": {...}
}

추출할 수 없는 엔티티는 빈 리스트 []로 반환하세요."""

        user_message = f"사용자 입력: {user_input}"
        if intent:
            user_message += f"\nIntent: {json.dumps(intent, ensure_ascii=False)}"
        if context:
            user_message += f"\n이전 컨텍스트: {json.dumps(context, ensure_ascii=False)}"

        try:
            response = await self.llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=800
            )
            result = json.loads(response)

            # Convert LLM result to ExtractedEntity objects
            return self._convert_llm_result(result)

        except Exception as e:
            self.log.warning(f"LLM extraction failed: {e}")
            return {}

    def _convert_llm_result(self, llm_result: Dict[str, Any]) -> Dict[str, List[ExtractedEntity]]:
        """LLM 결과를 ExtractedEntity 객체로 변환"""

        entities: Dict[str, List[ExtractedEntity]] = {}

        # Data sources
        if "data_sources" in llm_result:
            ds_entities = []
            for ds in llm_result["data_sources"]:
                try:
                    if isinstance(ds, dict):
                        raw_value = ds.get("name", "")
                        confidence = ds.get("confidence", 0.8)
                        structured = DataSourceEntity(**ds) if "name" in ds else None
                    elif isinstance(ds, str):
                        raw_value = ds
                        confidence = 0.8
                        structured = None
                    else:
                        raw_value = str(ds)
                        confidence = 0.6
                        structured = None

                    ds_entities.append(ExtractedEntity(
                        entity_type=EntityType.DATA_SOURCE,
                        raw_value=raw_value,
                        confidence=confidence,
                        metadata={"method": "llm"},
                        structured_data=structured
                    ))
                except Exception as e:
                    self.log.warning(f"Failed to parse data_source entity: {ds}, error: {e}")
            entities[EntityType.DATA_SOURCE] = ds_entities

        # Time range
        if "time_range" in llm_result and llm_result["time_range"]:
            tr = llm_result["time_range"]
            try:
                if isinstance(tr, dict):
                    raw_value = f"{tr.get('start', '')} ~ {tr.get('end', '')}"
                    confidence = tr.get("confidence", 0.8)
                    structured = TimeRangeEntity(**tr) if "start" in tr or "end" in tr else None
                elif isinstance(tr, list) and len(tr) > 0:
                    # LLM returned list instead of dict - take first item
                    first_item = tr[0]
                    if isinstance(first_item, dict):
                        raw_value = f"{first_item.get('start', '')} ~ {first_item.get('end', '')}"
                        confidence = first_item.get("confidence", 0.8)
                        structured = TimeRangeEntity(**first_item) if "start" in first_item or "end" in first_item else None
                    else:
                        raw_value = str(first_item)
                        confidence = 0.6
                        structured = None
                elif isinstance(tr, str):
                    raw_value = tr
                    confidence = 0.7
                    structured = None
                else:
                    raw_value = str(tr)
                    confidence = 0.6
                    structured = None

                entities[EntityType.TIME_RANGE] = [
                    ExtractedEntity(
                        entity_type=EntityType.TIME_RANGE,
                        raw_value=raw_value,
                        confidence=confidence,
                        metadata={"method": "llm"},
                        structured_data=structured
                    )
                ]
            except Exception as e:
                self.log.warning(f"Failed to parse time_range entity: {tr}, error: {e}")

        # Brands
        if "brands" in llm_result:
            brand_entities = []
            for brand in llm_result["brands"]:
                try:
                    if isinstance(brand, dict):
                        raw_value = brand.get("name", str(brand))
                        confidence = brand.get("confidence", 0.8)
                    elif isinstance(brand, str):
                        raw_value = brand
                        confidence = 0.8
                    else:
                        # Handle unexpected types (list, etc.)
                        raw_value = str(brand)
                        confidence = 0.6

                    brand_entities.append(ExtractedEntity(
                        entity_type=EntityType.BRAND,
                        raw_value=raw_value,
                        confidence=confidence,
                        metadata={"method": "llm"}
                    ))
                except Exception as e:
                    self.log.warning(f"Failed to parse brand entity: {brand}, error: {e}")
            entities[EntityType.BRAND] = brand_entities

        # Metrics
        if "metrics" in llm_result:
            metric_entities = []
            for metric in llm_result["metrics"]:
                try:
                    if isinstance(metric, dict):
                        raw_value = metric.get("name", str(metric))
                        confidence = metric.get("confidence", 0.8)
                        structured = MetricEntity(**metric) if "name" in metric else None
                    elif isinstance(metric, str):
                        raw_value = metric
                        confidence = 0.8
                        structured = None
                    else:
                        raw_value = str(metric)
                        confidence = 0.6
                        structured = None

                    metric_entities.append(ExtractedEntity(
                        entity_type=EntityType.METRIC,
                        raw_value=raw_value,
                        confidence=confidence,
                        metadata={"method": "llm"},
                        structured_data=structured
                    ))
                except Exception as e:
                    self.log.warning(f"Failed to parse metric entity: {metric}, error: {e}")
            entities[EntityType.METRIC] = metric_entities

        # Filters
        if "filters" in llm_result:
            filter_entities = []
            for f in llm_result["filters"]:
                try:
                    if isinstance(f, dict):
                        raw_value = f"{f.get('field', '')} {f.get('operator', '')} {f.get('value', '')}"
                        confidence = f.get("confidence", 0.8)
                        structured = FilterEntity(**f) if "field" in f else None
                    elif isinstance(f, str):
                        raw_value = f
                        confidence = 0.7
                        structured = None
                    else:
                        raw_value = str(f)
                        confidence = 0.6
                        structured = None

                    filter_entities.append(ExtractedEntity(
                        entity_type=EntityType.FILTER,
                        raw_value=raw_value,
                        confidence=confidence,
                        metadata={"method": "llm"},
                        structured_data=structured
                    ))
                except Exception as e:
                    self.log.warning(f"Failed to parse filter entity: {f}, error: {e}")
            entities[EntityType.FILTER] = filter_entities

        # Output format
        if "output_format" in llm_result and llm_result["output_format"]:
            of = llm_result["output_format"]
            try:
                if isinstance(of, dict):
                    raw_value = of.get("format", "json")
                    confidence = of.get("confidence", 0.8)
                    structured = OutputEntity(**of) if "format" in of else None
                elif isinstance(of, list) and len(of) > 0:
                    # LLM returned list instead of dict - take first item
                    first_item = of[0]
                    if isinstance(first_item, dict):
                        raw_value = first_item.get("format", "json")
                        confidence = first_item.get("confidence", 0.8)
                        structured = OutputEntity(**first_item) if "format" in first_item else None
                    else:
                        raw_value = str(first_item)
                        confidence = 0.6
                        structured = None
                elif isinstance(of, str):
                    raw_value = of
                    confidence = 0.8
                    structured = None
                else:
                    raw_value = str(of)
                    confidence = 0.6
                    structured = None

                entities[EntityType.OUTPUT_FORMAT] = [
                    ExtractedEntity(
                        entity_type=EntityType.OUTPUT_FORMAT,
                        raw_value=raw_value,
                        confidence=confidence,
                        metadata={"method": "llm"},
                        structured_data=structured
                    )
                ]
            except Exception as e:
                self.log.warning(f"Failed to parse output_format entity: {of}, error: {e}")

        return entities

    def _merge_entities(
        self,
        pattern_entities: Dict[str, List[ExtractedEntity]],
        llm_entities: Dict[str, List[ExtractedEntity]]
    ) -> Dict[str, List[ExtractedEntity]]:
        """패턴 기반 + LLM 기반 엔티티 병합 및 중복 제거"""

        merged: Dict[str, List[ExtractedEntity]] = {}

        all_types = set(pattern_entities.keys()) | set(llm_entities.keys())

        for entity_type in all_types:
            pattern_list = pattern_entities.get(entity_type, [])
            llm_list = llm_entities.get(entity_type, [])

            # LLM entities have higher priority
            # Use LLM if available, otherwise use pattern
            if llm_list:
                merged[entity_type] = llm_list
            else:
                merged[entity_type] = pattern_list

            # Deduplicate by raw_value
            seen = set()
            deduped = []
            for entity in merged[entity_type]:
                if entity.raw_value not in seen:
                    seen.add(entity.raw_value)
                    deduped.append(entity)

            merged[entity_type] = deduped

        return merged

    def _validate_entities(
        self,
        entities: Dict[str, List[ExtractedEntity]]
    ) -> Dict[str, List[ExtractedEntity]]:
        """엔티티 유효성 검증"""

        validated: Dict[str, List[ExtractedEntity]] = {}

        for entity_type, entity_list in entities.items():
            valid_entities = []

            for entity in entity_list:
                # Basic validation
                if not entity.raw_value or not entity.raw_value.strip():
                    continue

                # Type-specific validation
                if entity_type == EntityType.TIME_RANGE:
                    if entity.structured_data:
                        try:
                            TimeRangeEntity.model_validate(entity.structured_data.dict())
                            valid_entities.append(entity)
                        except:
                            self.log.debug(f"Invalid time range entity: {entity.raw_value}")
                    else:
                        valid_entities.append(entity)
                else:
                    valid_entities.append(entity)

            if valid_entities:
                validated[entity_type] = valid_entities

        return validated

    async def _normalize_entities(
        self,
        entities: Dict[str, List[ExtractedEntity]]
    ) -> Dict[str, List[ExtractedEntity]]:
        """엔티티 정규화"""

        normalized: Dict[str, List[ExtractedEntity]] = {}

        for entity_type, entity_list in entities.items():
            normalized_list = []

            for entity in entity_list:
                # Normalize based on type
                if entity_type == EntityType.BRAND:
                    entity.normalized_value = self._normalize_brand(entity.raw_value)
                elif entity_type == EntityType.CHANNEL:
                    entity.normalized_value = self._normalize_channel(entity.raw_value)
                elif entity_type == EntityType.DATA_SOURCE:
                    entity.normalized_value = self._normalize_data_source(entity.raw_value)
                elif entity_type == EntityType.TIME_RANGE:
                    entity.normalized_value = await self._normalize_time_range(entity)
                else:
                    entity.normalized_value = entity.raw_value

                normalized_list.append(entity)

            normalized[entity_type] = normalized_list

        return normalized

    def _normalize_brand(self, brand: str) -> str:
        """브랜드명 정규화"""
        brand_map = {
            "설화수": "SULWHASOO",
            "라네즈": "LANEIGE",
            "헤라": "HERA",
            "이니스프리": "INNISFREE",
            "에뛰드": "ETUDE",
        }
        return brand_map.get(brand, brand.upper())

    def _normalize_channel(self, channel: str) -> str:
        """채널명 정규화"""
        channel_map = {
            "올리브영": "OLIVEYOUNG",
            "쿠팡": "COUPANG",
            "네이버": "NAVER",
            "아마존": "AMAZON",
        }
        return channel_map.get(channel, channel.upper())

    def _normalize_data_source(self, source: str) -> str:
        """데이터 소스명 정규화"""
        return source.lower().replace(" ", "_")

    async def _normalize_time_range(self, entity: ExtractedEntity) -> Dict[str, str]:
        """시간 범위 정규화 (상대적 시간 → 절대적 시간)"""

        if not entity.structured_data:
            return {"start": None, "end": None}

        tr: TimeRangeEntity = entity.structured_data

        # If already absolute, return as-is
        if not tr.relative and tr.start and tr.end:
            return {"start": tr.start, "end": tr.end}

        # Convert relative time to absolute
        now = datetime.now()

        if "지난주" in entity.raw_value or "last week" in entity.raw_value.lower():
            start = now - timedelta(days=7)
            end = now
        elif "최근 30일" in entity.raw_value or "last 30 days" in entity.raw_value.lower():
            start = now - timedelta(days=30)
            end = now
        elif "어제" in entity.raw_value or "yesterday" in entity.raw_value.lower():
            start = now - timedelta(days=1)
            end = now
        else:
            # Default to last 7 days
            start = now - timedelta(days=7)
            end = now

        return {
            "start": start.isoformat(),
            "end": end.isoformat()
        }

    def _pattern_to_entity_type(self, pattern_name: str) -> EntityType:
        """패턴 이름을 EntityType으로 매핑"""
        mapping = {
            "date": EntityType.DATE,
            "brand": EntityType.BRAND,
            "channel": EntityType.CHANNEL,
            "metric": EntityType.METRIC,
        }
        return mapping.get(pattern_name, EntityType.KEYWORD)


# ============================================================
# Helper Functions
# ============================================================

def format_entities_for_planning(
    entities: Dict[str, List[ExtractedEntity]]
) -> Dict[str, Any]:
    """Planning Layer에서 사용할 수 있도록 엔티티 포맷팅"""

    formatted = {}

    for entity_type, entity_list in entities.items():
        if entity_type == EntityType.DATA_SOURCE:
            formatted["data_sources"] = [
                e.structured_data.dict() if e.structured_data else {"name": e.normalized_value}
                for e in entity_list
            ]
        elif entity_type == EntityType.TIME_RANGE:
            if entity_list:
                formatted["time_range"] = entity_list[0].normalized_value
        elif entity_type == EntityType.METRIC:
            formatted["metrics"] = [e.normalized_value for e in entity_list]
        elif entity_type == EntityType.FILTER:
            formatted["filters"] = [
                e.structured_data.dict() if e.structured_data else e.raw_value
                for e in entity_list
            ]
        elif entity_type == EntityType.OUTPUT_FORMAT:
            if entity_list:
                formatted["output_format"] = (
                    entity_list[0].structured_data.dict()
                    if entity_list[0].structured_data
                    else entity_list[0].normalized_value
                )
        elif entity_type == EntityType.KEYWORD:
            formatted["keywords"] = [
                e.normalized_value or e.raw_value for e in entity_list
            ]

    return formatted
