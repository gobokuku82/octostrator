"""Todo validation system"""

from typing import List, Dict, Any
from backend.app.dream_agent.states import TodoItem
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class TodoValidator:
    """Todo 검증 시스템"""

    @staticmethod
    def validate_todos(
        todos: List[TodoItem],
        intent: Dict[str, Any],
        user_input: str
    ) -> Dict[str, Any]:
        """
        Planning이 생성한 Todos를 검증

        Args:
            todos: Planning 노드가 생성한 todos
            intent: Cognitive 노드가 파악한 의도
            user_input: 사용자 입력

        Returns:
            검증 결과:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "suggestions": List[str]
            }
        """
        errors = []
        warnings = []
        suggestions = []

        # 1. 기본 검증: Todos가 존재하는가?
        if not todos:
            # Intent에 ML이나 Biz 작업이 필요한데 todos가 없으면 에러
            if intent.get("requires_ml") or intent.get("requires_biz"):
                errors.append("Planning did not create any todos despite requiring ML/Biz execution")
                suggestions.append("Planning should be re-run to generate appropriate todos")
            else:
                # 단순 질문이면 todos 없어도 OK
                logger.info("No todos created for simple question - this is expected")

        # 2. ML/Biz 요구사항 검증
        if intent.get("requires_ml"):
            ml_todos = [t for t in todos if t.layer == "ml_execution"]
            if not ml_todos:
                errors.append("Intent requires ML execution but no ML todos were created")
                suggestions.append("Add ML execution todos (collector, preprocessor, analyzer, insight)")

        if intent.get("requires_biz"):
            biz_todos = [t for t in todos if t.layer == "biz_execution"]
            if not biz_todos:
                errors.append("Intent requires Biz execution but no Biz todos were created")
                suggestions.append("Add Biz execution todos (report_agent, ad_creative_agent, etc.)")

        # 3. 데이터 소스 검증 (intent에서 추출된 소스와 todos의 소스가 일치하는지)
        extracted_entities = intent.get("extracted_entities", {})
        requested_sources = extracted_entities.get("data_sources", [])

        if requested_sources:
            # Collector todos 확인
            collector_todos = [
                t for t in todos
                if t.metadata and t.metadata.execution.tool == "collector"
            ]

            if collector_todos:
                todo_sources = [
                    t.metadata.execution.tool_params.get("source")
                    for t in collector_todos
                    if t.metadata.execution.tool_params.get("source")
                ]

                # 요청된 소스가 모두 포함되었는지 확인
                for source in requested_sources:
                    if source not in todo_sources:
                        warnings.append(f"Requested source '{source}' is missing from collector todos")
                        suggestions.append(f"Add collector todo for source: {source}")

                # 추가된 소스가 있는지 확인 (너무 많이 추가한 경우)
                for source in todo_sources:
                    if source not in requested_sources:
                        warnings.append(f"Unexpected source '{source}' added to collector todos")
            else:
                if requested_sources:
                    warnings.append("Data sources specified in intent but no collector todos created")

        # 4. ML 파이프라인 순서 검증
        ml_todos = [t for t in todos if t.layer == "ml_execution"]
        if len(ml_todos) > 1:
            # 일반적인 ML 파이프라인 순서: collect → preprocess → analyze → insight
            tool_order = [t.metadata.execution.tool if t.metadata else None for t in ml_todos]

            # Collector가 있으면 preprocessor가 있어야 함
            if "collector" in tool_order and "preprocessor" not in tool_order:
                warnings.append("Collector todo exists but no preprocessor todo found")
                suggestions.append("Add preprocessor todo after collector")

            # Preprocessor가 있으면 analyzer가 있어야 함
            if "preprocessor" in tool_order and "analyzer" not in tool_order:
                warnings.append("Preprocessor todo exists but no analyzer todo found")
                suggestions.append("Add analyzer todo after preprocessor")

            # Analyzer가 있으면 insight가 있어야 함
            if "analyzer" in tool_order and "insight" not in tool_order:
                warnings.append("Analyzer todo exists but no insight todo found")
                suggestions.append("Add insight todo after analyzer")

        # 5. 보고서 생성 요청 검증
        user_input_lower = user_input.lower()
        report_keywords = ["보고서", "report", "문서", "document", "만들어", "생성"]

        if any(keyword in user_input_lower for keyword in report_keywords):
            report_todos = [
                t for t in todos
                if t.metadata and t.metadata.execution.tool == "report_agent"
            ]
            if not report_todos:
                warnings.append("User requested report generation but no report_agent todo found")
                suggestions.append("Add biz_execution todo with tool: report_agent")

        # 6. Todo 우선순위 검증
        for idx, todo in enumerate(todos):
            if todo.priority is None or todo.priority < 0 or todo.priority > 10:
                warnings.append(f"Todo '{todo.task}' has invalid priority: {todo.priority}")

        # 결과 생성
        valid = len(errors) == 0

        result = {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "total_todos": len(todos),
            "ml_todos": len([t for t in todos if t.layer == "ml_execution"]),
            "biz_todos": len([t for t in todos if t.layer == "biz_execution"]),
        }

        # 로깅
        if not valid:
            logger.error(f"Todo validation failed: {errors}")
        elif warnings:
            logger.warning(f"Todo validation warnings: {warnings}")
        else:
            logger.info(f"Todo validation passed: {len(todos)} todos created")

        return result

    @staticmethod
    def get_fallback_todos(intent: Dict[str, Any], user_input: str) -> List[TodoItem]:
        """
        Planning 실패 시 fallback todos 생성 (조건부 실행 로직)

        Args:
            intent: Cognitive 노드가 파악한 의도
            user_input: 사용자 입력

        Returns:
            기본 todos 리스트

        플로우 규칙:
        - 수집 요청 시: Collector → Preprocessor(자동) → (분석 요청 시) 분석 파이프라인
        - 전처리만 요청: Preprocessor만 실행 (기존 데이터 재전처리)
        - 분석만 요청: Keyword → ABSA → Insight (DB의 전처리된 데이터 사용)
        """
        from .todo_creator import create_todo

        todos = []

        # Intent 플래그 추출
        requires_data_collection = intent.get("requires_data_collection", False)
        requires_preprocessing = intent.get("requires_preprocessing", False)
        requires_ml = intent.get("requires_ml", False)

        # 추출된 엔티티에서 정보 가져오기
        extracted_entities = intent.get("extracted_entities", {})
        brand = extracted_entities.get("brand", "laneige")
        platforms = extracted_entities.get("data_sources", ["youtube", "oliveyoung", "amazon"])

        # 키워드 추출: entities에서 가져오거나, user_input에서 추출
        keywords = extracted_entities.get("keywords", [])
        if keywords:
            keyword = keywords[0]  # 첫 번째 키워드 사용
        else:
            # user_input에서 키워드 추출 (간단한 휴리스틱)
            keyword = TodoValidator._extract_keyword_from_input(user_input, brand)

        logger.info(f"[TodoValidator] Creating fallback todos: "
                   f"requires_data_collection={requires_data_collection}, "
                   f"requires_preprocessing={requires_preprocessing}, "
                   f"requires_ml={requires_ml}")

        if requires_ml:
            priority_counter = 10

            # 1. 수집이 필요한 경우: Collector → Preprocessor 자동 연결
            if requires_data_collection:
                todos.append(create_todo(
                    task="데이터 수집",
                    layer="ml_execution",
                    priority=priority_counter,
                    tool="collector",
                    tool_params={"keyword": keyword, "platforms": platforms}
                ))
                logger.info(f"[TodoValidator] Created collector todo with keyword='{keyword}'")
                priority_counter -= 1

                # 수집 후 전처리는 자동 실행
                todos.append(create_todo(
                    task="데이터 전처리",
                    layer="ml_execution",
                    priority=priority_counter,
                    tool="preprocessor",
                    tool_params={"brand": brand},
                    depends_on=["collector"]  # 수집 완료 후 자동 실행
                ))
                priority_counter -= 1

            # 2. 전처리만 요청한 경우 (수집 없이 기존 데이터 재전처리)
            elif requires_preprocessing:
                todos.append(create_todo(
                    task="데이터 전처리",
                    layer="ml_execution",
                    priority=priority_counter,
                    tool="preprocessor",
                    tool_params={"brand": brand, "reprocess": True}
                ))
                priority_counter -= 1

            # 3. 분석 파이프라인 (항상 실행 - DB에서 조회)
            # 키워드 추출
            keyword_depends = ["preprocessor"] if (requires_data_collection or requires_preprocessing) else []
            todos.append(create_todo(
                task="키워드 추출",
                layer="ml_execution",
                priority=priority_counter,
                tool="keyword_extractor",
                tool_params={"brand": brand},
                depends_on=keyword_depends
            ))
            priority_counter -= 1

            # ABSA 감성 분석
            todos.append(create_todo(
                task="ABSA 감성 분석",
                layer="ml_execution",
                priority=priority_counter,
                tool="absa_analyzer",
                tool_params={"brand": brand},
                depends_on=["keyword_extractor"]
            ))
            priority_counter -= 1

            # 인사이트 도출 (트렌드/마케팅/글로벌 요청 시 K-Beauty RAG 사용)
            user_input_lower = user_input.lower() if user_input else ""
            trend_keywords = ["트렌드", "trend", "k-beauty", "kbeauty", "글로벌", "global", "마케팅", "marketing"]
            use_trend_insight = any(kw in user_input_lower for kw in trend_keywords)

            insight_tool = "insight_with_trends" if use_trend_insight else "insight_generator"
            insight_task = "K-Beauty 트렌드 인사이트 도출" if use_trend_insight else "인사이트 도출"

            if use_trend_insight:
                logger.info(f"[TodoValidator] Using insight_with_trends due to trend context in user request")

            todos.append(create_todo(
                task=insight_task,
                layer="ml_execution",
                priority=priority_counter,
                tool=insight_tool,
                tool_params={"brand": brand},
                depends_on=["absa_analyzer"]
            ))

        if intent.get("requires_biz"):
            # 기본 Biz 작업
            todos.append(create_todo(
                task="보고서 생성",
                layer="biz_execution",
                priority=5,
                tool="report_agent",
                tool_params={"report_type": "analysis"}
            ))

        logger.info(f"[TodoValidator] Generated {len(todos)} fallback todos: "
                   f"{[t.task for t in todos]}")
        return todos

    @staticmethod
    def _extract_keyword_from_input(user_input: str, default_brand: str = "laneige") -> str:
        """
        사용자 입력에서 검색 키워드 추출

        Args:
            user_input: 사용자 입력
            default_brand: 기본 브랜드명

        Returns:
            추출된 키워드
        """
        import re

        if not user_input:
            return default_brand

        # 일반적인 제품/키워드 패턴
        # "X 리뷰", "X 분석", "X 수집" 등에서 X 추출
        patterns = [
            r'([가-힣a-zA-Z0-9\s]+?)\s*리뷰',
            r'([가-힣a-zA-Z0-9\s]+?)\s*분석',
            r'([가-힣a-zA-Z0-9\s]+?)\s*수집',
            r'([가-힣a-zA-Z0-9\s]+?)\s*인사이트',
            r'([가-힣a-zA-Z0-9\s]+?)\s*데이터',
        ]

        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                keyword = match.group(1).strip()
                # 너무 짧거나 일반적인 단어 제외
                if len(keyword) >= 2 and keyword not in ['이', '그', '저', '해당', '관련']:
                    logger.info(f"[TodoValidator] Extracted keyword from user input: '{keyword}'")
                    return keyword

        # 패턴 매칭 실패 시 브랜드명 사용
        logger.info(f"[TodoValidator] Using default brand as keyword: '{default_brand}'")
        return default_brand
