# 문서생성 에이전트 고도화 작업계획서

**날짜**: 2025-10-28
**버전**: Beta v0.01 - Document Executor Enhancement
**타입**: 고도화 계획서
**작성자**: Development Team
**대상 파일**: `backend/app/service_agent/execution_agents/document_executor.py`

---

## 📋 목차

1. [개요](#개요)
2. [현재 상태 분석](#현재-상태-분석)
3. [고도화 목표](#고도화-목표)
4. [세부 구현 계획](#세부-구현-계획)
5. [단계별 작업 내역](#단계별-작업-내역)
6. [기술 스택](#기술-스택)
7. [테스트 계획](#테스트-계획)
8. [일정 및 리소스](#일정-및-리소스)
9. [리스크 관리](#리스크-관리)
10. [성공 지표](#성공-지표)

---

## 개요

### 목적
현재 Mock 데이터로 구현된 문서생성 에이전트(Document Executor)를 실제 프로덕션 환경에서 사용 가능한 수준으로 고도화

### 범위
- **대상 파일**: `backend/app/service_agent/execution_agents/document_executor.py`
- **핵심 기능**: 사용자 요청에 따라 법률 문서(임대차 계약서 등) 자동 생성
- **현재 상태**: LangGraph 0.6 HITL 패턴은 완성, 내부 로직은 Mock 구현
- **목표 상태**: 실제 LLM, 검색 도구, 문서 템플릿을 활용한 완전한 문서 생성 워크플로우

### 기대효과
1. 사용자 요청에 따른 실제 계약서 자동 생성
2. 법률 데이터베이스 및 부동산 정보 실시간 검색 통합
3. DOCX 템플릿 기반 전문적인 문서 포맷 생성
4. 에러 처리 및 예외 상황 대응 강화
5. 실제 서비스 배포 가능한 코드 품질 확보

---

## 현재 상태 분석

### ✅ 완성된 부분

#### 1. LangGraph 0.6 HITL 워크플로우
```
Planning → Aggregate (⏸️ HITL Interrupt) → Generate → END
```
- `interrupt()` 함수를 통한 사용자 승인 대기
- `Command(resume=...)` 패턴으로 워크플로우 재개
- PostgreSQL checkpoint 기반 상태 저장
- WebSocket 기반 실시간 UI 통신

#### 2. 프로그레스 추적
- 6단계 진행률 업데이트 (WebSocket으로 프론트엔드 전송)
- 각 노드별 시작/완료 상태 관리

#### 3. Parent Graph 통합
- `team_results`를 통한 상위 그래프 연동
- 통계 로그 및 결과 집계

### ❌ Mock 구현 현황 (고도화 필요)

#### 1. **planning_node** (Lines 94-142)
**현재**:
```python
def _extract_keywords(self, query: str) -> List[str]:
    # Simple extraction: take first 5 words
    keywords = query.split()[:5]
    return keywords
```

**문제점**:
- 단순 문자열 split으로 키워드 추출
- 문서 타입 판별 없음 (항상 "general")
- 필요한 정보 파악 미흡

**필요 기능**:
- LLM 기반 의도 분석
- 문서 타입 자동 분류 (임대차 계약서, 법률 자문서 등)
- 필수 정보 항목 식별
- 검색 전략 수립

---

#### 2. **aggregate_node** (Lines 144-245)
**현재**:
```python
def _mock_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
    search_results = []
    for keyword in keywords:
        result = {
            "keyword": keyword,
            "source": "mock_database",
            "content": f"Mock search result for: {keyword}",
            "relevance_score": 0.85,
        }
        search_results.append(result)
    return search_results

def _aggregate_results(self, search_results: List[Dict[str, Any]]) -> str:
    aggregated = "\n\n".join([
        f"- {result.get('keyword', 'Unknown')}: {result.get('content', 'No content')}"
        for result in search_results
    ])
    return f"Aggregated Content:\n{aggregated}"
```

**문제점**:
- Mock 검색 결과만 반환
- 실제 법률 데이터베이스 미연동
- 간단한 문자열 조합만 수행
- 정보 검증 및 필터링 없음

**필요 기능**:
- 실제 검색 도구 호출 (legal search, real estate DB)
- LLM 기반 정보 집계 및 정제
- 중복 제거 및 관련성 순위화
- 법률 규정 검증

---

#### 3. **generate_node** (Lines 247-326)
**현재**:
```python
def _format_document(self, content: str, planning: Dict, feedback: Dict) -> str:
    doc_type = planning.get("document_type", "general")
    sections = planning.get("sections", [])

    document = f"""
# Document: {doc_type.upper()}

## Generated Content

{content}

## Metadata
- Document Type: {doc_type}
- Sections: {', '.join(sections)}
...
"""
    return document.strip()
```

**문제점**:
- 단순 텍스트 템플릿만 사용
- DOCX 템플릿 미활용
- 법률 문서 형식 미준수
- PDF 생성 불가

**필요 기능**:
- `LeaseContractGeneratorTool` 통합
- DOCX 템플릿 기반 문서 생성
- 법률 문서 포맷 준수
- 메타데이터 및 서명란 포함

---

#### 4. **기타 Helper 메서드**
**현재**:
```python
def _apply_user_feedback(self, content: str, feedback: Dict) -> str:
    modifications = feedback.get("modifications", "")
    if modifications:
        # Simple append for now
        return f"{content}\n\n[User Feedback Applied]\n{modifications}"
    return content
```

**문제점**:
- 사용자 피드백을 단순 추가만 수행
- LLM 기반 지능형 병합 없음

**필요 기능**:
- LLM으로 피드백 분석 및 문맥 병합
- 문서 구조 유지하면서 수정사항 반영

---

### 🔧 사용 가능한 기존 도구

#### 1. **LLMService** (`app/service_agent/llm_manager/llm_service.py`)
- OpenAI LLM 호출 관리
- 동기/비동기 호출 지원
- JSON 응답 모드
- 재시도 로직 내장
- 프롬프트 기반 호출

**사용 예시**:
```python
from app.service_agent.llm_manager.llm_service import LLMService

llm_service = LLMService(llm_context)
result = await llm_service.complete_json_async(
    prompt_name="document_planning",
    variables={"query": "임대차 계약서 작성해줘"},
    temperature=0.3
)
```

---

#### 2. **LeaseContractGeneratorTool** (`app/service_agent/tools/lease_contract_generator_tool.py`)
- DOCX 템플릿 기반 계약서 생성
- Placeholder 자동 치환 (`{{address_road}}` 등)
- Markdown 변환 지원
- 생성된 DOCX 파일 저장

**사용 예시**:
```python
from app.service_agent.tools.lease_contract_generator_tool import LeaseContractGeneratorTool

tool = LeaseContractGeneratorTool()
result = await tool.execute(
    address_road="서울특별시 강남구 테헤란로 123",
    deposit="500,000,000",
    start_date="2024년 1월 1일",
    end_date="2026년 1월 1일",
    lessor_name="홍길동",
    lessee_name="김철수"
)

# result: {
#   "status": "success",
#   "content": "# 주택임대차 표준계약서\n...",
#   "docx_path": "/path/to/generated/계약서_20241028.docx",
#   "sections": [...]
# }
```

---

#### 3. **PromptManager** (`app/service_agent/llm_manager/prompt_manager.py`)
- 프롬프트 템플릿 관리
- 변수 치환 (코드 블록 보호)
- 캐싱 지원

**필요한 프롬프트 템플릿** (신규 작성 필요):
- `document_planning.txt` - 문서 계획 수립
- `document_aggregation.txt` - 정보 집계 및 정제
- `document_feedback_merge.txt` - 피드백 병합

---

#### 4. **검색 도구들** (`app/service_agent/tools/`)
- `hybrid_legal_search.py` - 법률 검색 (FAISS + 키워드)
- `real_estate_search_tool.py` - 부동산 검색
- `market_data_tool.py` - 시장 데이터 조회

---

### 📁 템플릿 파일 위치
- **DOCX 템플릿**: `backend/data/storage/documents/lease_contract_template_with_placeholders.docx`
- Placeholder 포함된 표준 계약서 템플릿
- `LeaseContractGeneratorTool`이 사용

---

## 고도화 목표

### 주요 목표

#### 1. Mock 제거 및 실제 구현
- [ ] 모든 Mock 로직을 실제 LLM 호출로 대체
- [ ] 실제 검색 도구 통합
- [ ] DOCX 템플릿 기반 문서 생성

#### 2. 지능형 문서 생성
- [ ] LLM 기반 의도 분석
- [ ] 문서 타입 자동 분류
- [ ] 맥락 기반 정보 집계
- [ ] 사용자 피드백 지능형 병합

#### 3. 프로덕션 품질
- [ ] 에러 처리 강화
- [ ] 로깅 및 모니터링
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성

---

### 구체적 성능 목표

| 항목 | 현재 | 목표 |
|------|------|------|
| 문서 생성 성공률 | N/A (Mock) | 95% |
| 평균 응답 시간 | 17s (Mock) | 25s 이내 |
| 사용자 만족도 | N/A | 4.0/5.0 이상 |
| 정보 정확도 | N/A | 90% 이상 |
| 템플릿 적용률 | 0% | 100% |

---

## 세부 구현 계획

### Phase 1: planning_node 고도화

#### 1.1 프롬프트 템플릿 작성
**파일**: `backend/app/service_agent/llm_manager/prompts/execution/document_planning.txt`

**내용**:
```
당신은 법률 문서 생성 전문가입니다.
사용자의 요청을 분석하여 문서 생성 계획을 수립하세요.

사용자 요청: {query}

다음 JSON 형식으로 응답하세요:
{{
  "document_type": "lease_contract | legal_advice | contract_review | other",
  "confidence": 0.95,
  "sections": ["섹션1", "섹션2", ...],
  "required_information": {{
    "필드명": "설명"
  }},
  "search_strategy": {{
    "keywords": ["키워드1", "키워드2"],
    "sources": ["legal_db", "real_estate_db"],
    "priority": "high | medium | low"
  }},
  "estimated_complexity": "simple | medium | complex",
  "reasoning": "계획 수립 근거"
}}

분석 시 고려사항:
1. 문서 타입이 "lease_contract"인 경우 임대차 계약서 표준 양식 사용
2. 필수 정보는 법률적으로 반드시 포함되어야 하는 항목
3. 검색 전략은 정보 수집의 우선순위와 방법 결정
4. 복잡도는 향후 작업 시간 예측에 사용
```

---

#### 1.2 planning_node 구현
**위치**: `document_executor.py` Lines 94-142

**구현 내용**:
```python
async def planning_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    """
    Planning Node: 사용자 요청 분석 및 문서 생성 계획 수립

    Improvements:
    - LLM 기반 의도 분석
    - 문서 타입 자동 분류
    - 필수 정보 식별
    - 검색 전략 수립
    """
    logger.info("📋 Planning node: Analyzing document requirements")

    await self._update_step_progress(state, step_index=0, status="in_progress", progress=0)

    query = state.get("query", "")

    # LLM으로 계획 수립
    from app.service_agent.llm_manager.llm_service import LLMService

    llm_service = LLMService(self.llm_context)

    try:
        planning_result = await llm_service.complete_json_async(
            prompt_name="document_planning",
            variables={"query": query},
            temperature=0.3,
            max_tokens=1000
        )

        logger.info(
            f"Planning complete: {planning_result.get('document_type')} "
            f"(confidence: {planning_result.get('confidence', 0):.2%})"
        )

    except Exception as e:
        logger.error(f"LLM planning failed, using fallback: {e}")
        # Fallback to simple extraction
        planning_result = self._fallback_planning(query)

    await self._update_step_progress(state, step_index=0, status="completed", progress=100)

    return {
        "planning_result": planning_result,
        "workflow_status": "running"
    }

def _fallback_planning(self, query: str) -> Dict[str, Any]:
    """Fallback 계획 (LLM 실패 시)"""
    return {
        "document_type": "general",
        "confidence": 0.5,
        "sections": ["introduction", "main_content", "conclusion"],
        "required_information": {},
        "search_strategy": {
            "keywords": query.split()[:5],
            "sources": ["general"],
            "priority": "medium"
        },
        "estimated_complexity": "simple",
        "reasoning": "Fallback planning due to LLM error"
    }
```

**삭제할 메서드**:
- `_extract_keywords()` - LLM이 대체

---

### Phase 2: aggregate_node 고도화

#### 2.1 프롬프트 템플릿 작성
**파일**: `backend/app/service_agent/llm_manager/prompts/execution/document_aggregation.txt`

**내용**:
```
당신은 법률 정보 분석 전문가입니다.
검색 결과를 분석하여 문서 생성에 필요한 정보를 체계적으로 정리하세요.

문서 타입: {document_type}
필수 정보: {required_information}
검색 결과: {search_results}

다음 JSON 형식으로 응답하세요:
{{
  "aggregated_fields": {{
    "필드명": "추출된 값"
  }},
  "additional_context": "추가 설명 또는 맥락",
  "missing_fields": ["누락된 필드1", "누락된 필드2"],
  "confidence": 0.85,
  "sources": ["source1", "source2"],
  "warnings": ["주의사항1", "주의사항2"]
}}

집계 시 고려사항:
1. 법률적으로 정확한 정보만 추출
2. 중복 정보는 가장 신뢰도 높은 것 선택
3. 누락된 필수 정보는 명확히 표시
4. 출처를 명확히 기록
```

---

#### 2.2 aggregate_node 구현
**위치**: `document_executor.py` Lines 144-245

**구현 내용**:
```python
async def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    """
    Aggregate Node: 정보 검색 및 집계 + HITL

    Improvements:
    - 실제 검색 도구 호출
    - LLM 기반 정보 집계
    - 중복 제거 및 검증
    - 지능형 정보 정제
    """
    logger.info("📊 Aggregate node: Consolidating search results")

    await self._update_step_progress(state, step_index=1, status="in_progress", progress=0)

    planning_result = state.get("planning_result", {})
    search_strategy = planning_result.get("search_strategy", {})

    # Step 1: 실제 검색 수행
    search_results = await self._perform_search(search_strategy)

    # Step 2: LLM으로 정보 집계
    aggregated_data = await self._aggregate_with_llm(
        planning_result=planning_result,
        search_results=search_results
    )

    logger.info(f"Aggregation complete: {len(aggregated_data.get('aggregated_fields', {}))} fields extracted")

    await self._update_step_progress(state, step_index=1, status="completed", progress=100)
    await self._update_step_progress(state, step_index=2, status="in_progress", progress=0)

    # Step 3: HITL - 사용자 승인 요청
    logger.info("⏸️  Requesting human approval via interrupt()")

    interrupt_value = {
        "aggregated_data": aggregated_data,
        "search_results_count": len(search_results),
        "missing_fields": aggregated_data.get("missing_fields", []),
        "warnings": aggregated_data.get("warnings", []),
        "message": "수집된 정보를 검토해주세요. 필요한 경우 수정사항을 입력하세요.",
        "options": {
            "approve": "정보가 정확합니다. 문서 생성을 계속하세요.",
            "modify": "일부 정보를 수정하겠습니다.",
            "reject": "문서 생성을 취소합니다."
        },
        "_metadata": {
            "interrupted_by": "aggregate",
            "interrupt_type": "approval",
            "node_name": "document_team.aggregate"
        }
    }

    state["aggregated_content"] = self._format_aggregated_content(aggregated_data)
    state["aggregated_data"] = aggregated_data  # 구조화된 데이터 저장
    state["workflow_status"] = "interrupted"

    # LangGraph 0.6 HITL Pattern
    user_feedback = interrupt(interrupt_value)

    logger.info("▶️  Workflow resumed with user feedback")

    await self._update_step_progress(state, step_index=2, status="completed", progress=100)
    await self._update_step_progress(state, step_index=3, status="in_progress", progress=0)

    # Step 4: 사용자 피드백 처리
    if user_feedback and user_feedback.get("action") == "modify":
        logger.info("Applying user modifications with LLM")
        aggregated_data = await self._apply_user_feedback_with_llm(
            aggregated_data=aggregated_data,
            user_feedback=user_feedback
        )

    await self._update_step_progress(state, step_index=3, status="completed", progress=100)

    return {
        "aggregated_content": self._format_aggregated_content(aggregated_data),
        "aggregated_data": aggregated_data,
        "collaboration_result": user_feedback,
        "workflow_status": "running",
        "interrupted_by": "aggregate",
        "interrupt_type": "approval"
    }


async def _perform_search(self, search_strategy: Dict) -> List[Dict[str, Any]]:
    """
    실제 검색 도구 호출

    Args:
        search_strategy: 검색 전략 (keywords, sources, priority)

    Returns:
        검색 결과 리스트
    """
    keywords = search_strategy.get("keywords", [])
    sources = search_strategy.get("sources", [])

    search_results = []

    # Legal DB 검색
    if "legal_db" in sources:
        try:
            from app.service_agent.tools.hybrid_legal_search import HybridLegalSearch

            legal_tool = HybridLegalSearch()
            for keyword in keywords[:3]:  # 최대 3개 키워드
                result = await legal_tool.execute(query=keyword, top_k=3)
                if result.get("status") == "success":
                    search_results.extend(result.get("results", []))
        except Exception as e:
            logger.warning(f"Legal search failed: {e}")

    # Real Estate DB 검색
    if "real_estate_db" in sources:
        try:
            from app.service_agent.tools.real_estate_search_tool import RealEstateSearchTool

            realestate_tool = RealEstateSearchTool()
            result = await realestate_tool.execute(query=" ".join(keywords))
            if result.get("status") == "success":
                search_results.extend(result.get("properties", []))
        except Exception as e:
            logger.warning(f"Real estate search failed: {e}")

    # Fallback: Mock 데이터 (검색 실패 시)
    if not search_results:
        logger.warning("All searches failed, using mock data")
        search_results = self._mock_search(keywords)

    return search_results


async def _aggregate_with_llm(
    self,
    planning_result: Dict,
    search_results: List[Dict]
) -> Dict[str, Any]:
    """
    LLM으로 검색 결과 집계 및 정제

    Args:
        planning_result: 계획 결과
        search_results: 검색 결과

    Returns:
        집계된 데이터
    """
    from app.service_agent.llm_manager.llm_service import LLMService
    import json

    llm_service = LLMService(self.llm_context)

    try:
        # 검색 결과를 JSON으로 변환 (최대 3000자)
        search_results_json = json.dumps(search_results, ensure_ascii=False)[:3000]

        variables = {
            "document_type": planning_result.get("document_type", "general"),
            "required_information": json.dumps(
                planning_result.get("required_information", {}),
                ensure_ascii=False
            ),
            "search_results": search_results_json
        }

        aggregated_data = await llm_service.complete_json_async(
            prompt_name="document_aggregation",
            variables=variables,
            temperature=0.2,
            max_tokens=1500
        )

        return aggregated_data

    except Exception as e:
        logger.error(f"LLM aggregation failed: {e}")
        # Fallback
        return {
            "aggregated_fields": {},
            "additional_context": "LLM aggregation failed",
            "missing_fields": [],
            "confidence": 0.3,
            "sources": [],
            "warnings": ["LLM aggregation failed, using fallback"]
        }


def _format_aggregated_content(self, aggregated_data: Dict) -> str:
    """
    집계된 데이터를 사용자 친화적 텍스트로 변환

    Args:
        aggregated_data: 집계된 데이터

    Returns:
        포맷된 텍스트
    """
    lines = ["# 수집된 정보\n"]

    # 필드 정보
    fields = aggregated_data.get("aggregated_fields", {})
    if fields:
        lines.append("## 추출된 정보")
        for key, value in fields.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    # 추가 맥락
    context = aggregated_data.get("additional_context", "")
    if context:
        lines.append("## 추가 정보")
        lines.append(context)
        lines.append("")

    # 누락 필드
    missing = aggregated_data.get("missing_fields", [])
    if missing:
        lines.append("## ⚠️ 누락된 필수 정보")
        for field in missing:
            lines.append(f"- {field}")
        lines.append("")

    # 경고
    warnings = aggregated_data.get("warnings", [])
    if warnings:
        lines.append("## ⚠️ 주의사항")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)


async def _apply_user_feedback_with_llm(
    self,
    aggregated_data: Dict,
    user_feedback: Dict
) -> Dict[str, Any]:
    """
    LLM으로 사용자 피드백 지능형 병합

    Args:
        aggregated_data: 원본 집계 데이터
        user_feedback: 사용자 피드백

    Returns:
        수정된 집계 데이터
    """
    from app.service_agent.llm_manager.llm_service import LLMService
    import json

    modifications = user_feedback.get("modifications", "")
    if not modifications:
        return aggregated_data

    llm_service = LLMService(self.llm_context)

    try:
        # 프롬프트 작성
        prompt_content = f"""
당신은 문서 정보 편집 전문가입니다.
사용자의 피드백을 반영하여 집계된 정보를 수정하세요.

현재 정보:
{json.dumps(aggregated_data, ensure_ascii=False, indent=2)}

사용자 피드백:
{modifications}

수정된 정보를 원본과 같은 JSON 형식으로 출력하세요.
필드 구조는 유지하되, 사용자가 요청한 내용만 수정하세요.
"""

        # LLM 호출 (임시로 직접 호출)
        response = await llm_service.complete_async(
            prompt_name="common_instruction",  # 간단한 프롬프트 사용
            variables={"instruction": prompt_content},
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )

        modified_data = json.loads(response)
        logger.info("User feedback applied successfully with LLM")
        return modified_data

    except Exception as e:
        logger.error(f"LLM feedback merge failed: {e}")
        # Fallback: 단순 추가
        aggregated_data["additional_context"] += f"\n\n[사용자 수정사항]\n{modifications}"
        return aggregated_data
```

**삭제할 메서드**:
- `_mock_search()` - 실제 검색으로 대체 (fallback으로만 유지)
- `_aggregate_results()` - LLM 집계로 대체
- `_apply_user_feedback()` - LLM 병합으로 대체

---

### Phase 3: generate_node 고도화

#### 3.1 generate_node 구현
**위치**: `document_executor.py` Lines 247-326

**구현 내용**:
```python
async def generate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
    """
    Generate Node: 최종 문서 생성

    Improvements:
    - LeaseContractGeneratorTool 통합
    - DOCX 템플릿 사용
    - 법률 문서 포맷 준수
    - 메타데이터 및 출처 포함
    """
    logger.info("📝 Generate node: Creating final document")

    await self._update_step_progress(state, step_index=4, status="in_progress", progress=0)

    planning_result = state.get("planning_result", {})
    aggregated_data = state.get("aggregated_data", {})
    collaboration_result = state.get("collaboration_result", {})

    document_type = planning_result.get("document_type", "general")

    # 문서 타입에 따른 생성 전략
    if document_type == "lease_contract":
        final_response = await self._generate_lease_contract(
            aggregated_data=aggregated_data,
            planning_result=planning_result,
            collaboration_result=collaboration_result
        )
    else:
        # 일반 문서 (텍스트 기반)
        final_response = await self._generate_general_document(
            aggregated_data=aggregated_data,
            planning_result=planning_result,
            collaboration_result=collaboration_result
        )

    await self._update_step_progress(state, step_index=4, status="completed", progress=100)
    await self._update_step_progress(state, step_index=5, status="in_progress", progress=0)

    # 최종 검토 (자동 승인)
    logger.info("✅ Document generated successfully")

    await self._update_step_progress(state, step_index=5, status="completed", progress=100)

    # team_results 구성
    team_results = {
        "document": {
            "status": "success",
            "data": final_response
        }
    }

    return {
        "final_document": final_response.get("answer", ""),
        "final_response": final_response,
        "workflow_status": "completed",
        "team_results": team_results
    }


async def _generate_lease_contract(
    self,
    aggregated_data: Dict,
    planning_result: Dict,
    collaboration_result: Dict
) -> Dict[str, Any]:
    """
    임대차 계약서 생성 (DOCX 템플릿 사용)

    Args:
        aggregated_data: 집계된 데이터
        planning_result: 계획 결과
        collaboration_result: 사용자 피드백

    Returns:
        final_response 딕셔너리
    """
    from app.service_agent.tools.lease_contract_generator_tool import LeaseContractGeneratorTool

    # 집계된 필드 추출
    fields = aggregated_data.get("aggregated_fields", {})

    # LeaseContractGeneratorTool 파라미터 매핑
    params = self._map_fields_to_contract_params(fields)

    # 도구 실행
    tool = LeaseContractGeneratorTool()

    try:
        result = await tool.execute(**params)

        if result.get("status") == "success":
            logger.info(f"Contract generated: {result.get('docx_path')}")

            return {
                "answer": result.get("content", ""),
                "document_type": "lease_contract",
                "docx_path": result.get("docx_path"),
                "sections": result.get("sections", []),
                "user_approved": collaboration_result.get("action") == "approve",
                "user_action": collaboration_result.get("action", "unknown"),
                "metadata": result.get("metadata", {}),
                "type": "document"
            }
        else:
            # 도구 실패 시 Fallback
            logger.error(f"Contract generation failed: {result.get('error')}")
            return self._generate_fallback_document(
                aggregated_data=aggregated_data,
                document_type="lease_contract",
                error=result.get("error")
            )

    except Exception as e:
        logger.error(f"Contract generation exception: {e}", exc_info=True)
        return self._generate_fallback_document(
            aggregated_data=aggregated_data,
            document_type="lease_contract",
            error=str(e)
        )


def _map_fields_to_contract_params(self, fields: Dict) -> Dict:
    """
    집계된 필드를 LeaseContractGeneratorTool 파라미터로 매핑

    Args:
        fields: 집계된 필드 딕셔너리

    Returns:
        도구 파라미터 딕셔너리
    """
    # 필드명 매핑 (집계 필드 → 도구 파라미터)
    field_mapping = {
        "주소": "address_road",
        "상세주소": "address_detail",
        "임차면적": "rental_area",
        "보증금": "deposit",
        "보증금_한글": "deposit_hangeul",
        "계약금": "contract_payment",
        "월세": "monthly_rent",
        "월세_납부일": "monthly_rent_day",
        "관리비": "management_fee",
        "시작일": "start_date",
        "종료일": "end_date",
        "임대인_성명": "lessor_name",
        "임대인_주소": "lessor_address",
        "임대인_연락처": "lessor_phone",
        "임차인_성명": "lessee_name",
        "임차인_주소": "lessee_address",
        "임차인_연락처": "lessee_phone",
        "특약사항": "special_terms"
    }

    params = {}
    for korean_name, param_name in field_mapping.items():
        if korean_name in fields:
            params[param_name] = fields[korean_name]

    return params


async def _generate_general_document(
    self,
    aggregated_data: Dict,
    planning_result: Dict,
    collaboration_result: Dict
) -> Dict[str, Any]:
    """
    일반 문서 생성 (텍스트 기반)

    Args:
        aggregated_data: 집계된 데이터
        planning_result: 계획 결과
        collaboration_result: 사용자 피드백

    Returns:
        final_response 딕셔너리
    """
    from app.service_agent.llm_manager.llm_service import LLMService
    import json

    llm_service = LLMService(self.llm_context)

    try:
        # LLM으로 문서 생성
        prompt_content = f"""
당신은 전문 문서 작성가입니다.
수집된 정보를 바탕으로 전문적인 문서를 작성하세요.

문서 타입: {planning_result.get('document_type')}
필요 섹션: {', '.join(planning_result.get('sections', []))}

수집된 정보:
{json.dumps(aggregated_data, ensure_ascii=False, indent=2)}

사용자 피드백:
{collaboration_result.get('modifications', '없음')}

다음 형식으로 문서를 작성하세요:
# 문서 제목

## 섹션1
내용...

## 섹션2
내용...
"""

        document_content = await llm_service.complete_async(
            prompt_name="common_instruction",
            variables={"instruction": prompt_content},
            temperature=0.5,
            max_tokens=2000
        )

        return {
            "answer": document_content,
            "document_type": planning_result.get("document_type"),
            "user_approved": collaboration_result.get("action") == "approve",
            "user_action": collaboration_result.get("action", "unknown"),
            "type": "document",
            "metadata": {
                "confidence": aggregated_data.get("confidence", 0.7),
                "sources": aggregated_data.get("sources", [])
            }
        }

    except Exception as e:
        logger.error(f"General document generation failed: {e}")
        return self._generate_fallback_document(
            aggregated_data=aggregated_data,
            document_type=planning_result.get("document_type", "general"),
            error=str(e)
        )


def _generate_fallback_document(
    self,
    aggregated_data: Dict,
    document_type: str,
    error: str
) -> Dict[str, Any]:
    """
    Fallback 문서 생성 (에러 시)

    Args:
        aggregated_data: 집계된 데이터
        document_type: 문서 타입
        error: 에러 메시지

    Returns:
        final_response 딕셔너리
    """
    content = f"""
# 문서 생성 결과

문서 타입: {document_type}

## 수집된 정보

"""

    fields = aggregated_data.get("aggregated_fields", {})
    for key, value in fields.items():
        content += f"- **{key}**: {value}\n"

    content += f"\n\n## 주의\n문서 생성 중 오류가 발생했습니다: {error}\n"
    content += "위 정보를 참고하여 수동으로 문서를 작성하세요.\n"

    return {
        "answer": content,
        "document_type": document_type,
        "type": "document",
        "status": "partial",
        "error": error,
        "metadata": {
            "fallback": True
        }
    }
```

**삭제할 메서드**:
- `_format_document()` - DOCX 생성 또는 LLM 생성으로 대체

---

### Phase 4: 프롬프트 템플릿 작성

#### 4.1 필요한 프롬프트 파일

**디렉토리**: `backend/app/service_agent/llm_manager/prompts/execution/`

1. **document_planning.txt** (이미 Phase 1에 작성됨)
2. **document_aggregation.txt** (이미 Phase 2에 작성됨)
3. **common_instruction.txt** (범용 프롬프트)

**파일**: `common_instruction.txt`
**위치**: `backend/app/service_agent/llm_manager/prompts/common/`

**내용**:
```
{instruction}
```

(단순 변수 전달용 범용 프롬프트)

---

### Phase 5: 에러 처리 및 로깅 강화

#### 5.1 에러 처리 개선

**추가할 예외 처리**:
1. LLM 호출 실패 → Fallback 로직
2. 검색 도구 실패 → Mock 데이터 사용
3. DOCX 생성 실패 → 텍스트 문서 생성
4. 타임아웃 처리 → 진행 상황 저장 및 재개

**구현 예시**:
```python
try:
    result = await llm_service.complete_json_async(...)
except TimeoutError as e:
    logger.error(f"LLM timeout: {e}")
    return fallback_result
except Exception as e:
    logger.error(f"LLM error: {e}", exc_info=True)
    return fallback_result
```

---

#### 5.2 로깅 강화

**추가할 로그**:
1. 각 단계 시작/완료 시간 기록
2. LLM 토큰 사용량 기록
3. 검색 결과 개수 및 품질 지표
4. 사용자 피드백 내용 기록

**구현 예시**:
```python
import time

start_time = time.time()
logger.info(f"[{node_name}] Starting...")

# ... 작업 수행 ...

elapsed = time.time() - start_time
logger.info(f"[{node_name}] Completed in {elapsed:.2f}s")
```

---

### Phase 6: 단위 테스트 작성

#### 6.1 테스트 파일 구조
**위치**: `backend/tests/service_agent/execution_agents/`

**파일**:
- `test_document_executor_planning.py` - planning_node 테스트
- `test_document_executor_aggregate.py` - aggregate_node 테스트
- `test_document_executor_generate.py` - generate_node 테스트
- `test_document_executor_integration.py` - 통합 테스트

---

#### 6.2 테스트 케이스 예시

**파일**: `test_document_executor_planning.py`

```python
import pytest
from app.service_agent.execution_agents.document_executor import DocumentExecutor
from app.service_agent.foundation.separated_states import MainSupervisorState

@pytest.mark.asyncio
async def test_planning_node_lease_contract():
    """임대차 계약서 요청 시 planning_node 테스트"""
    executor = DocumentExecutor()

    state = MainSupervisorState(
        query="임대차 계약서 작성해줘. 보증금 5억, 월세 200만원"
    )

    result = await executor.planning_node(state)

    assert result["planning_result"]["document_type"] == "lease_contract"
    assert result["planning_result"]["confidence"] > 0.8
    assert "보증금" in result["planning_result"]["required_information"]
    assert "월세" in result["planning_result"]["required_information"]


@pytest.mark.asyncio
async def test_planning_node_fallback():
    """LLM 실패 시 fallback 테스트"""
    executor = DocumentExecutor()
    executor.llm_context = None  # LLM 비활성화

    state = MainSupervisorState(query="계약서 작성")

    result = await executor.planning_node(state)

    assert result["planning_result"]["document_type"] == "general"
    assert result["planning_result"]["confidence"] < 0.7
```

---

## 단계별 작업 내역

### Phase 1: planning_node 고도화 (예상 소요: 2일)

#### Day 1
- [ ] `document_planning.txt` 프롬프트 작성
- [ ] `planning_node` 구현
- [ ] `_fallback_planning` 구현
- [ ] `_extract_keywords` 제거
- [ ] 단위 테스트 작성 (test_planning_node)

#### Day 2
- [ ] LLM 호출 테스트
- [ ] Fallback 로직 테스트
- [ ] 다양한 쿼리 테스트 (임대차, 법률자문 등)
- [ ] 로깅 검증
- [ ] 코드 리뷰 및 수정

**완료 기준**:
- [ ] 80% 이상의 쿼리에서 올바른 document_type 분류
- [ ] LLM 실패 시 fallback 정상 작동
- [ ] 단위 테스트 pass
- [ ] 로그에 의도 분석 결과 명확히 표시

---

### Phase 2: aggregate_node 고도화 (예상 소요: 4일)

#### Day 3-4
- [ ] `document_aggregation.txt` 프롬프트 작성
- [ ] `_perform_search` 구현 (legal, real estate 검색)
- [ ] `_aggregate_with_llm` 구현
- [ ] `_format_aggregated_content` 구현

#### Day 5-6
- [ ] `_apply_user_feedback_with_llm` 구현
- [ ] 검색 도구 통합 테스트
- [ ] LLM 집계 테스트
- [ ] HITL 흐름 테스트
- [ ] 단위 테스트 작성
- [ ] 코드 리뷰 및 수정

**완료 기준**:
- [ ] 실제 검색 도구 정상 작동
- [ ] LLM 집계 정확도 80% 이상
- [ ] 사용자 피드백 반영 정상 작동
- [ ] HITL interrupt/resume 정상 작동
- [ ] 단위 테스트 pass

---

### Phase 3: generate_node 고도화 (예상 소요: 3일)

#### Day 7-8
- [ ] `_generate_lease_contract` 구현
- [ ] `_map_fields_to_contract_params` 구현
- [ ] `LeaseContractGeneratorTool` 통합
- [ ] DOCX 생성 테스트

#### Day 9
- [ ] `_generate_general_document` 구현
- [ ] `_generate_fallback_document` 구현
- [ ] 다양한 문서 타입 테스트
- [ ] 에러 처리 테스트
- [ ] 단위 테스트 작성
- [ ] 코드 리뷰 및 수정

**완료 기준**:
- [ ] 임대차 계약서 DOCX 생성 성공
- [ ] 일반 문서 텍스트 생성 성공
- [ ] Fallback 문서 생성 정상 작동
- [ ] 생성된 문서 법률 형식 준수
- [ ] 단위 테스트 pass

---

### Phase 4: 프롬프트 및 에러 처리 (예상 소요: 1일)

#### Day 10
- [ ] `common_instruction.txt` 작성
- [ ] 프롬프트 디렉토리 정리
- [ ] 에러 처리 로직 추가
- [ ] 로깅 강화
- [ ] 타임아웃 처리 추가

**완료 기준**:
- [ ] 모든 프롬프트 파일 작성 완료
- [ ] 모든 예외 상황 처리
- [ ] 로그에 충분한 정보 기록
- [ ] 타임아웃 시 안전하게 종료

---

### Phase 5: 통합 테스트 및 검증 (예상 소요: 2일)

#### Day 11
- [ ] 통합 테스트 작성 (end-to-end)
- [ ] 다양한 시나리오 테스트
  - [ ] 임대차 계약서 생성
  - [ ] 법률 자문서 생성
  - [ ] 사용자 수정 후 재생성
  - [ ] 에러 발생 시 복구
- [ ] 성능 테스트 (응답 시간, 토큰 사용량)

#### Day 12
- [ ] 버그 수정
- [ ] 코드 최적화
- [ ] 문서화 업데이트
- [ ] 최종 검토

**완료 기준**:
- [ ] 모든 통합 테스트 pass
- [ ] 평균 응답 시간 25초 이내
- [ ] 문서 생성 성공률 95% 이상
- [ ] 코드 커버리지 80% 이상

---

### Phase 6: 배포 준비 (예상 소요: 1일)

#### Day 13
- [ ] Production 환경 설정 검토
- [ ] 환경 변수 설정 가이드 작성
- [ ] 배포 체크리스트 작성
- [ ] 롤백 계획 수립
- [ ] 모니터링 대시보드 설정

**완료 기준**:
- [ ] 배포 가이드 문서 작성
- [ ] 환경 설정 검증 완료
- [ ] 롤백 절차 문서화

---

## 기술 스택

### 핵심 라이브러리

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| LangGraph | 0.6.x | 워크플로우 오케스트레이션, HITL |
| OpenAI Python | 1.x | LLM 호출 |
| python-docx | 0.8.x | DOCX 문서 생성 |
| PostgreSQL | 16+ | Checkpoint 저장 |
| pytest | 8.x | 단위 테스트 |

### 프로젝트 내 의존성

| 모듈 | 경로 | 용도 |
|------|------|------|
| LLMService | `llm_manager/llm_service.py` | LLM 호출 관리 |
| PromptManager | `llm_manager/prompt_manager.py` | 프롬프트 관리 |
| LeaseContractGeneratorTool | `tools/lease_contract_generator_tool.py` | 계약서 생성 |
| HybridLegalSearch | `tools/hybrid_legal_search.py` | 법률 검색 |
| RealEstateSearchTool | `tools/real_estate_search_tool.py` | 부동산 검색 |

---

## 테스트 계획

### 단위 테스트

#### 1. planning_node 테스트
**파일**: `test_document_executor_planning.py`

**테스트 케이스**:
- [ ] 임대차 계약서 요청 분류
- [ ] 법률 자문서 요청 분류
- [ ] 애매한 요청 처리
- [ ] LLM 실패 시 fallback
- [ ] 필수 정보 식별
- [ ] 검색 전략 수립

---

#### 2. aggregate_node 테스트
**파일**: `test_document_executor_aggregate.py`

**테스트 케이스**:
- [ ] Legal DB 검색 성공
- [ ] Real Estate DB 검색 성공
- [ ] 검색 실패 시 fallback
- [ ] LLM 집계 정상 작동
- [ ] 중복 정보 제거
- [ ] 누락 필드 탐지
- [ ] 사용자 피드백 병합

---

#### 3. generate_node 테스트
**파일**: `test_document_executor_generate.py`

**테스트 케이스**:
- [ ] 임대차 계약서 DOCX 생성
- [ ] 필드 매핑 정확성
- [ ] 일반 문서 텍스트 생성
- [ ] DOCX 생성 실패 시 fallback
- [ ] 메타데이터 포함 검증
- [ ] team_results 구성 검증

---

### 통합 테스트

#### End-to-End 시나리오
**파일**: `test_document_executor_integration.py`

**시나리오 1: 임대차 계약서 생성 (승인)**
```
입력: "강남구 아파트 임대차 계약서 작성해줘. 보증금 5억, 월세 200만원"
→ planning: lease_contract 분류
→ aggregate: 검색 및 집계 → HITL interrupt
→ 사용자: "승인" 버튼
→ generate: DOCX 생성
→ 출력: 계약서 DOCX + Markdown

검증:
- DOCX 파일 생성 확인
- 보증금, 월세 필드 정확히 채워짐
- 법률 형식 준수
```

**시나리오 2: 사용자 수정 후 생성**
```
입력: "임대차 계약서 작성"
→ aggregate: HITL interrupt
→ 사용자: "월세를 250만원으로 수정" 입력 + "수정" 버튼
→ LLM으로 피드백 병합
→ generate: 수정된 값으로 DOCX 생성

검증:
- 월세 250만원으로 반영
- 다른 필드는 유지
```

**시나리오 3: 검색 실패 시 복구**
```
입력: "계약서 작성"
→ planning: 성공
→ aggregate: 검색 도구 모두 실패 → Mock 데이터 사용
→ generate: Fallback 문서 생성

검증:
- 에러 없이 완료
- Fallback 경고 포함
- 사용자에게 안내 메시지
```

---

### 성능 테스트

**측정 지표**:
1. **응답 시간**
   - Planning: < 3초
   - Aggregate: < 10초
   - Generate: < 12초
   - 전체: < 25초

2. **토큰 사용량**
   - Planning: ~1,000 토큰
   - Aggregate: ~2,000 토큰
   - Generate: ~2,500 토큰
   - 전체: ~5,500 토큰

3. **성공률**
   - 정상 케이스: 95% 이상
   - 에러 복구: 100% (fallback)

---

## 일정 및 리소스

### 전체 일정

| Phase | 기간 | 담당자 | 상태 |
|-------|------|--------|------|
| Phase 1: planning_node | 2일 (Day 1-2) | 개발자 1명 | 예정 |
| Phase 2: aggregate_node | 4일 (Day 3-6) | 개발자 1명 | 예정 |
| Phase 3: generate_node | 3일 (Day 7-9) | 개발자 1명 | 예정 |
| Phase 4: 프롬프트/에러 처리 | 1일 (Day 10) | 개발자 1명 | 예정 |
| Phase 5: 통합 테스트 | 2일 (Day 11-12) | 개발자 1명 + QA | 예정 |
| Phase 6: 배포 준비 | 1일 (Day 13) | 개발자 1명 + DevOps | 예정 |
| **총 기간** | **13일** | - | - |

### 추가 버퍼
- 예상치 못한 이슈: +3일
- 코드 리뷰 및 수정: +2일
- **최종 예상 기간**: **18일 (약 3-4주)**

---

### 필요 리소스

#### 인력
- **백엔드 개발자** 1명 (Full-time)
- **QA 엔지니어** 0.5명 (테스트 기간)
- **코드 리뷰어** 1명 (Part-time)

#### 인프라
- **PostgreSQL 서버** (Checkpoint 저장)
- **OpenAI API 크레딧** (테스트용 ~$50)
- **개발 환경** (Python 3.11+)

#### 외부 의존성
- OpenAI API 안정성
- PostgreSQL 가용성
- DOCX 템플릿 파일 준비

---

## 리스크 관리

### 주요 리스크

#### 1. LLM 응답 품질 불안정 🔴 High
**리스크**:
- LLM이 JSON 형식 미준수
- 잘못된 정보 추출
- 신뢰도 낮은 응답

**완화 방안**:
- JSON 모드 강제 사용 (`response_format: json_object`)
- 응답 검증 로직 추가 (JSON schema validation)
- Fallback 로직 구현 (잘못된 응답 시)
- Temperature 낮게 설정 (0.2-0.3)

**비상 계획**:
- Few-shot 예시 추가
- 프롬프트 개선 반복
- GPT-4 모델 사용 검토

---

#### 2. 검색 도구 실패 🟡 Medium
**리스크**:
- Legal DB 또는 Real Estate DB 다운
- 검색 결과 없음
- API 타임아웃

**완화 방안**:
- 각 검색 도구에 try-except 적용
- Mock 데이터 fallback 유지
- 타임아웃 설정 (10초)
- 에러 로깅 강화

**비상 계획**:
- Mock 데이터로만 작동
- 사용자에게 "제한된 정보" 안내

---

#### 3. DOCX 생성 실패 🟡 Medium
**리스크**:
- `python-docx` 라이브러리 버그
- 템플릿 파일 손상
- 필드 매핑 오류

**완화 방안**:
- 템플릿 파일 백업
- 필드 매핑 검증 로직
- Fallback: 텍스트 문서 생성
- DOCX 파일 검증 (생성 후)

**비상 계획**:
- 텍스트 또는 Markdown으로 생성
- 사용자에게 수동 작성 가이드 제공

---

#### 4. 프롬프트 최적화 시간 초과 🟢 Low
**리스크**:
- 프롬프트 튜닝에 예상보다 많은 시간 소요

**완화 방안**:
- 초기 프롬프트는 단순하게 시작
- 점진적으로 개선
- A/B 테스트로 효과 검증

**비상 계획**:
- 기본 프롬프트로 배포 후 점진적 개선

---

#### 5. 통합 테스트 복잡도 🟡 Medium
**리스크**:
- HITL 워크플로우 테스트 어려움
- Checkpoint 상태 검증 복잡
- WebSocket 통합 테스트

**완화 방안**:
- Mock WebSocket 클라이언트 작성
- Checkpoint 검증 헬퍼 함수
- 단계별 테스트 분리

**비상 계획**:
- 수동 테스트로 대체
- 프로덕션에서 모니터링 강화

---

## 성공 지표

### 정량적 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| **문서 생성 성공률** | 95% 이상 | (성공 건수 / 전체 요청) × 100 |
| **평균 응답 시간** | 25초 이내 | 전체 워크플로우 완료 시간 |
| **LLM 정확도** | 80% 이상 | 수동 검증 (샘플 100건) |
| **DOCX 생성 성공률** | 90% 이상 | (DOCX 성공 / 임대차 요청) × 100 |
| **테스트 커버리지** | 80% 이상 | pytest-cov 리포트 |
| **토큰 사용량** | 6,000 이내 | OpenAI API 로그 |

---

### 정성적 지표

| 지표 | 평가 기준 |
|------|----------|
| **코드 품질** | - 함수 분리 명확<br>- 주석 충분<br>- 네이밍 일관성 |
| **에러 처리** | - 모든 예외 상황 처리<br>- 사용자 친화적 메시지<br>- 로그 충분 |
| **유지보수성** | - 모듈화 잘 됨<br>- 확장 가능한 구조<br>- 문서화 완료 |
| **사용자 경험** | - 진행 상황 명확<br>- 에러 메시지 이해 가능<br>- HITL 흐름 직관적 |

---

### 검증 방법

#### 1. 자동 테스트
```bash
# 단위 테스트
pytest backend/tests/service_agent/execution_agents/ -v --cov

# 통합 테스트
pytest backend/tests/integration/test_document_executor_e2e.py -v
```

#### 2. 수동 테스트
- 임대차 계약서 생성 (10건)
- 법률 자문서 생성 (5건)
- 에러 시나리오 (5건)
- 사용자 수정 시나리오 (5건)

#### 3. 코드 리뷰
- [ ] 모든 TODO 제거
- [ ] Mock 코드 제거 (fallback 제외)
- [ ] 에러 처리 완료
- [ ] 로깅 충분
- [ ] 주석 명확

---

## 부록

### A. 파일 변경 요약

| 파일 | 변경 타입 | 주요 변경 내용 |
|------|----------|----------------|
| `execution_agents/document_executor.py` | Modified | planning_node, aggregate_node, generate_node 고도화 |
| `llm_manager/prompts/execution/document_planning.txt` | New | 문서 계획 프롬프트 |
| `llm_manager/prompts/execution/document_aggregation.txt` | New | 정보 집계 프롬프트 |
| `llm_manager/prompts/common/common_instruction.txt` | New | 범용 프롬프트 |
| `tests/service_agent/execution_agents/test_document_executor_*.py` | New | 단위 테스트 |
| `tests/integration/test_document_executor_e2e.py` | New | 통합 테스트 |

---

### B. 주요 의존성

```python
# requirements.txt에 추가 (이미 있을 수 있음)
openai>=1.0.0
python-docx>=0.8.11
langgraph>=0.6.0
psycopg>=3.1.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
```

---

### C. 환경 변수

```bash
# .env 파일
OPENAI_API_KEY=sk-...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=real_estate
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root1234
```

---

### D. 참고 문서

#### 내부 문서
- `reports/PatchNote/251026_Document_executor_HITL.md` - HITL 구현 내역
- `backend/app/service_agent/tools/lease_contract_generator_tool.py` - 계약서 생성 도구
- `backend/app/service_agent/llm_manager/llm_service.py` - LLM 서비스

#### 외부 문서
- [LangGraph 0.6 HITL](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [OpenAI API Docs](https://platform.openai.com/docs/api-reference)
- [python-docx Documentation](https://python-docx.readthedocs.io/)

---

## 다음 단계

### 즉시 시작 가능한 작업
1. [ ] Phase 1 시작: `document_planning.txt` 프롬프트 작성
2. [ ] 개발 환경 설정 확인 (OpenAI API 키, PostgreSQL)
3. [ ] Git 브랜치 생성: `feature/document-executor-enhancement`

### 승인 후 진행
- [ ] 작업 계획서 검토 및 승인
- [ ] 일정 확정
- [ ] 리소스 할당
- [ ] Kickoff 미팅

---

**End of Implementation Plan**

**작성**: 2025-10-28
**검토**: Pending
**승인**: Pending
**문의**: Development Team
