# 문서생성 에이전트 고도화 계획서

**작성일**: 2025-10-23
**버전**: 1.0
**대상 모듈**: `backend/app/service_agent/execution_agents/document_executor.py`

---

## 📊 현재 상태 분석

### 1. 현재 아키텍처 구조

#### 1.1 기본 구성
- **클래스명**: `DocumentExecutor`
- **위치**: Execution Agents 계층 (TeamBasedSupervisor 하위)
- **역할**: 문서 생성 및 검토 파이프라인 실행
- **State**: `DocumentTeamState` (TypedDict 기반)

#### 1.2 노드 구성 (LangGraph StateGraph)
```
START → prepare → generate → review_check → review → finalize → END
                                     ↓
                                  (skip)
```

#### 1.3 주요 기능
- **문서 템플릿 관리**: 3가지 하드코딩된 템플릿 (임대차, 매매, 대출)
- **문서 생성**: Tool 기반 (LeaseContractGeneratorTool) 또는 Agent 기반
- **문서 검토**: ReviewAgent 호출 (옵션)
- **최종 포맷팅**: Markdown 형식 출력

### 2. 현재 구현 상태 평가

#### 2.1 장점 ✅
- LangGraph StateGraph 기반 명확한 플로우
- State 기반 상태 관리 (DocumentTeamState)
- Tool과 Agent 둘 다 지원하는 유연한 구조
- 비동기 처리 지원 (async/await)
- 에러 핸들링 기본 구조 구현

#### 2.2 한계점 ❌
1. **템플릿 하드코딩**: 3가지 템플릿만 지원, 확장성 부족
2. **단순한 파라미터 추출**: 정규식 기반 간단한 추출만 구현
3. **제한적인 문서 타입**: 계약서 위주로만 구현
4. **Mock 함수 의존**: 실제 Agent 없을 때 모의 생성에 의존
5. **검토 프로세스 단순**: 단순 호출만 하고 피드백 반영 미구현
6. **LLM 활용 부족**: 문서 생성 자체에 LLM 활용 미흡
7. **버전 관리 없음**: 문서 버전/이력 관리 기능 없음
8. **협업 기능 없음**: 다중 사용자 편집/검토 미지원

### 3. 시스템 통합 상태

#### 3.1 상위 시스템과의 연계
- **TeamBasedSupervisor**: execute_teams_node에서 호출
- **SharedState**: 최소한의 공유 데이터만 전달받음
- **Priority**: 기본 우선순위 2 (search: 0, analysis: 1 다음)

#### 3.2 하위 컴포넌트 연계
- **Tools**: LeaseContractGeneratorTool만 연동
- **Agents**: DocumentAgent, ReviewAgent 연동 (옵션)
- **Templates**: 하드코딩된 3개 템플릿

#### 3.3 Memory 시스템 연계
- **현재**: Memory 시스템과 연동 없음
- **필요**: 이전 문서 참조, 사용자 선호 템플릿 저장 등

---

## 🎯 고도화 목표

### 1. 핵심 목표
1. **지능형 문서 생성**: LLM 기반 고품질 문서 자동 생성
2. **동적 템플릿 시스템**: 확장 가능한 템플릿 관리
3. **스마트 파라미터 추출**: NLP 기반 정확한 정보 추출
4. **반복적 개선 프로세스**: 검토-수정 사이클 구현
5. **다양한 문서 포맷**: PDF, DOCX, HTML 등 지원
6. **Memory 통합**: 이전 문서 참조 및 학습

### 2. 기대 효과
- 문서 생성 정확도 향상 (70% → 95%)
- 처리 가능 문서 타입 확대 (3개 → 20+개)
- 사용자 만족도 증가
- 법적 리스크 감소

---

## 🚀 고도화 계획

### Phase 1: 기반 강화 (1-2주)

#### 1.1 템플릿 시스템 개선
```python
# 현재: 하드코딩
templates = {
    "lease_contract": DocumentTemplate(...),
    "sales_contract": DocumentTemplate(...),
    "loan_application": DocumentTemplate(...)
}

# 개선: 동적 로딩 시스템
class TemplateManager:
    def __init__(self):
        self.template_dir = "templates/"
        self.template_db = TemplateDB()
        self.cache = {}

    async def load_template(self, template_id: str) -> DocumentTemplate:
        # 1. 캐시 확인
        # 2. DB 조회
        # 3. 파일 시스템 폴백
        # 4. LLM 생성 (없을 경우)
        pass

    async def create_template_from_llm(self, doc_type: str) -> DocumentTemplate:
        # LLM을 사용한 동적 템플릿 생성
        pass
```

#### 1.2 파라미터 추출 강화
```python
# 현재: 정규식 기반
def _extract_params_from_context(self, state):
    numbers = re.findall(r'\d+[억만원]?', query)

# 개선: NLP + LLM 기반
class ParameterExtractor:
    async def extract_parameters(self, query: str, template: DocumentTemplate) -> Dict:
        # 1. NER (Named Entity Recognition)
        entities = await self.extract_entities(query)

        # 2. LLM 기반 정보 추출
        prompt = self.create_extraction_prompt(query, template.required_fields)
        extracted = await self.llm.extract(prompt)

        # 3. 검증 및 정규화
        validated = self.validate_parameters(extracted, template)

        return validated
```

#### 1.3 노드 구조 개선
```python
# 개선된 노드 구조
workflow = StateGraph(DocumentTeamState)

# 준비 단계
workflow.add_node("prepare", self.prepare_document_node)
workflow.add_node("extract_params", self.extract_parameters_node)  # 신규

# 생성 단계
workflow.add_node("generate_draft", self.generate_draft_node)  # 개선
workflow.add_node("enhance_content", self.enhance_content_node)  # 신규

# 검토 단계
workflow.add_node("review", self.review_document_node)
workflow.add_node("apply_feedback", self.apply_feedback_node)  # 신규

# 최종화
workflow.add_node("format", self.format_document_node)  # 신규
workflow.add_node("finalize", self.finalize_node)

# 조건부 엣지 (반복 검토 지원)
workflow.add_conditional_edges(
    "review",
    self._needs_revision,
    {
        "revise": "apply_feedback",
        "approve": "format"
    }
)
```

### Phase 2: 지능형 기능 추가 (2-3주)

#### 2.1 LLM 기반 문서 생성
```python
class IntelligentDocumentGenerator:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.prompts = PromptManager()

    async def generate_document(
        self,
        template: DocumentTemplate,
        parameters: Dict,
        context: Dict
    ) -> DocumentContent:
        # 1. 섹션별 생성
        sections = []
        for section_template in template.sections:
            content = await self.generate_section(
                section_template,
                parameters,
                context
            )
            sections.append(content)

        # 2. 전체 문서 일관성 확보
        refined = await self.refine_document(sections, context)

        # 3. 법적 조항 검증
        validated = await self.validate_legal_clauses(refined)

        return DocumentContent(
            title=template.template_name,
            sections=validated,
            metadata=self.create_metadata(parameters)
        )

    async def generate_section(
        self,
        section_template: SectionTemplate,
        parameters: Dict,
        context: Dict
    ) -> Dict:
        prompt = self.prompts.get("section_generation")

        response = await self.llm.generate(
            prompt,
            section_template=section_template,
            parameters=parameters,
            context=context,
            temperature=0.3  # 낮은 temperature로 일관성 확보
        )

        return self.parse_section_response(response)
```

#### 2.2 반복적 개선 프로세스
```python
class IterativeRefinementEngine:
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.review_agent = ReviewAgent()
        self.refinement_llm = LLMService()

    async def refine_document(
        self,
        document: DocumentContent,
        review_criteria: List[str]
    ) -> DocumentContent:
        current_doc = document
        iteration = 0

        while iteration < self.max_iterations:
            # 1. 검토
            review_result = await self.review_agent.review(
                current_doc,
                criteria=review_criteria
            )

            # 2. 검토 통과 시 종료
            if review_result.score >= 0.9:
                break

            # 3. 피드백 적용
            current_doc = await self.apply_feedback(
                current_doc,
                review_result.feedback
            )

            iteration += 1

        return current_doc

    async def apply_feedback(
        self,
        document: DocumentContent,
        feedback: List[Dict]
    ) -> DocumentContent:
        # LLM을 사용한 피드백 적용
        prompt = self.create_refinement_prompt(document, feedback)
        refined = await self.refinement_llm.refine(prompt)
        return refined
```

#### 2.3 Memory 시스템 통합
```python
class DocumentMemoryIntegration:
    def __init__(self, memory_service: SimpleMemoryService):
        self.memory = memory_service

    async def load_relevant_documents(
        self,
        user_id: int,
        doc_type: str
    ) -> List[Dict]:
        # 1. 유사 문서 검색
        similar_docs = await self.memory.search_similar_documents(
            user_id=user_id,
            doc_type=doc_type,
            limit=5
        )

        # 2. 사용자 선호 템플릿
        preferences = await self.memory.get_user_preferences(
            user_id=user_id,
            preference_type="document_templates"
        )

        return {
            "similar_documents": similar_docs,
            "user_preferences": preferences
        }

    async def save_document_to_memory(
        self,
        user_id: int,
        document: DocumentContent,
        metadata: Dict
    ):
        # 1. 문서 저장
        await self.memory.save_document(
            user_id=user_id,
            document=document,
            metadata=metadata
        )

        # 2. 사용 패턴 학습
        await self.memory.update_user_preferences(
            user_id=user_id,
            preference_type="document_templates",
            data=self.extract_preferences(document)
        )
```

### Phase 3: 고급 기능 구현 (3-4주)

#### 3.1 다중 포맷 지원
```python
class DocumentFormatter:
    def __init__(self):
        self.formatters = {
            "markdown": MarkdownFormatter(),
            "pdf": PDFFormatter(),
            "docx": DOCXFormatter(),
            "html": HTMLFormatter()
        }

    async def format_document(
        self,
        document: DocumentContent,
        format_type: str,
        options: Dict = None
    ) -> Union[str, bytes]:
        formatter = self.formatters.get(format_type)
        if not formatter:
            raise ValueError(f"Unsupported format: {format_type}")

        return await formatter.format(document, options)

class PDFFormatter:
    async def format(
        self,
        document: DocumentContent,
        options: Dict
    ) -> bytes:
        # PDF 생성 로직
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph

        # ... PDF 생성 구현
        pass
```

#### 3.2 실시간 협업 지원
```python
class CollaborativeDocumentEditor:
    def __init__(self):
        self.active_sessions = {}
        self.change_history = []

    async def create_collaborative_session(
        self,
        document_id: str,
        users: List[str]
    ) -> str:
        session_id = generate_uuid()
        self.active_sessions[session_id] = {
            "document_id": document_id,
            "users": users,
            "changes": [],
            "locks": {}
        }
        return session_id

    async def apply_change(
        self,
        session_id: str,
        user_id: str,
        change: Dict
    ):
        # 1. 충돌 검사
        if self.has_conflict(session_id, change):
            return await self.resolve_conflict(session_id, change)

        # 2. 변경 적용
        await self.apply_to_document(session_id, change)

        # 3. 다른 사용자에게 브로드캐스트
        await self.broadcast_change(session_id, change, exclude=user_id)
```

#### 3.3 법적 준수성 검증
```python
class LegalComplianceValidator:
    def __init__(self):
        self.legal_db = LegalDatabase()
        self.compliance_llm = LLMService()

    async def validate_document(
        self,
        document: DocumentContent,
        jurisdiction: str = "KR"
    ) -> ValidationResult:
        # 1. 필수 조항 확인
        required_clauses = await self.legal_db.get_required_clauses(
            doc_type=document.type,
            jurisdiction=jurisdiction
        )

        missing = self.check_missing_clauses(document, required_clauses)

        # 2. 금지 조항 검사
        prohibited = await self.check_prohibited_terms(document, jurisdiction)

        # 3. LLM 기반 종합 검증
        llm_validation = await self.compliance_llm.validate_legal(
            document,
            jurisdiction=jurisdiction
        )

        return ValidationResult(
            is_valid=len(missing) == 0 and len(prohibited) == 0,
            missing_clauses=missing,
            prohibited_terms=prohibited,
            recommendations=llm_validation.recommendations,
            risk_score=llm_validation.risk_score
        )
```

### Phase 4: 최적화 및 모니터링 (4-5주)

#### 4.1 성능 최적화
```python
class OptimizedDocumentExecutor:
    def __init__(self):
        self.cache = DocumentCache()
        self.template_cache = {}
        self.parallel_executor = AsyncParallelExecutor()

    async def execute_optimized(self, state: DocumentTeamState):
        # 1. 캐시 확인
        cached = await self.cache.get(state.get("cache_key"))
        if cached:
            return cached

        # 2. 병렬 처리 가능한 작업 식별
        parallel_tasks = [
            self.extract_parameters(state),
            self.load_template(state),
            self.load_memory_context(state)
        ]

        results = await self.parallel_executor.execute_all(parallel_tasks)

        # 3. 순차 처리 필요한 작업
        document = await self.generate_with_results(results)

        # 4. 캐시 저장
        await self.cache.set(state.get("cache_key"), document)

        return document
```

#### 4.2 모니터링 및 분석
```python
class DocumentGenerationMonitor:
    def __init__(self):
        self.metrics = MetricsCollector()
        self.analytics = AnalyticsEngine()

    async def track_generation(self, state: DocumentTeamState):
        # 1. 성능 메트릭
        self.metrics.record("generation_time", state.get("generation_time"))
        self.metrics.record("template_type", state.get("document_type"))

        # 2. 품질 메트릭
        if state.get("review_result"):
            self.metrics.record("review_score", state["review_result"]["score"])
            self.metrics.record("risk_level", state["review_result"]["risk_level"])

        # 3. 사용 패턴 분석
        await self.analytics.analyze_usage_pattern(
            user_id=state.get("user_id"),
            document_type=state.get("document_type"),
            parameters=state.get("document_params")
        )

    async def generate_insights(self) -> Dict:
        return {
            "popular_templates": await self.analytics.get_popular_templates(),
            "average_generation_time": self.metrics.get_average("generation_time"),
            "quality_trends": await self.analytics.get_quality_trends(),
            "error_patterns": await self.analytics.get_error_patterns()
        }
```

---

## 📈 구현 우선순위

### 즉시 구현 (Week 1)
1. ✅ 템플릿 시스템 개선 - 동적 로딩 구조
2. ✅ 파라미터 추출 강화 - NLP 기반 추출
3. ✅ 노드 구조 개선 - 세분화된 처리 단계

### 단기 구현 (Week 2-3)
1. ⏳ LLM 기반 문서 생성 엔진
2. ⏳ 반복적 개선 프로세스
3. ⏳ Memory 시스템 통합

### 중기 구현 (Week 4-6)
1. ⏰ 다중 포맷 지원 (PDF, DOCX)
2. ⏰ 법적 준수성 검증
3. ⏰ 실시간 협업 기능

### 장기 구현 (Week 7+)
1. 📅 고급 템플릿 빌더 UI
2. 📅 AI 기반 문서 추천
3. 📅  다국어 지원

---

## 🔍 기술 스택 요구사항

### 신규 도입 필요
- **PDF 생성**: ReportLab 또는 WeasyPrint
- **DOCX 생성**: python-docx
- **NLP**: spaCy 또는 KoNLPy (한국어)
- **템플릿 엔진**: Jinja2
- **캐싱**: Redis
- **문서 DB**: MongoDB 또는 ElasticSearch

### 기존 활용
- **LLM**: GPT-4o-mini (현재 사용 중)
- **State 관리**: LangGraph StateGraph
- **비동기 처리**: asyncio
- **DB**: PostgreSQL

---

## 🎯 성공 지표 (KPI)

### 정량적 지표
| 지표 | 현재 | 목표 (3개월) | 측정 방법 |
|------|------|-------------|----------|
| 문서 생성 정확도 | 70% | 95% | 검토 통과율 |
| 평균 생성 시간 | 15초 | 5초 | 로그 분석 |
| 지원 문서 타입 | 3개 | 20개 | 템플릿 수 |
| 사용자 만족도 | - | 4.5/5.0 | 설문조사 |
| 에러율 | 10% | 2% | 에러 로그 |

### 정성적 지표
- 사용자 피드백 긍정률
- 법적 이슈 발생 건수
- 재작업 요청 빈도
- 시스템 안정성

---

## 🚧 리스크 및 대응 방안

### 기술적 리스크
| 리스크 | 영향도 | 확률 | 대응 방안 |
|--------|--------|------|----------|
| LLM 응답 불안정 | 높음 | 중간 | Fallback 메커니즘, 캐싱 |
| 템플릿 복잡도 증가 | 중간 | 높음 | 모듈화, 테스트 강화 |
| 성능 저하 | 높음 | 낮음 | 병렬 처리, 최적화 |

### 비즈니스 리스크
| 리스크 | 영향도 | 확률 | 대응 방안 |
|--------|--------|------|----------|
| 법적 준수성 | 매우 높음 | 낮음 | 전문가 검토, 검증 강화 |
| 사용자 저항 | 중간 | 중간 | 점진적 전환, 교육 |

---

## 📅 실행 로드맵

### Week 1-2: Foundation
- [ ] 템플릿 매니저 구현
- [ ] 파라미터 추출기 개선
- [ ] 노드 구조 리팩토링
- [ ] 단위 테스트 작성

### Week 3-4: Intelligence
- [ ] LLM 문서 생성기 구현
- [ ] 반복 개선 엔진 구현
- [ ] Memory 통합
- [ ] 통합 테스트

### Week 5-6: Advanced Features
- [ ] 포맷터 구현 (PDF, DOCX)
- [ ] 법적 검증기 구현
- [ ] 협업 기능 프로토타입
- [ ] 성능 테스트

### Week 7-8: Optimization
- [ ] 캐싱 구현
- [ ] 병렬 처리 최적화
- [ ] 모니터링 대시보드
- [ ] 배포 준비

---

## 📝 결론

문서생성 에이전트의 고도화는 단순한 템플릿 기반 생성에서 벗어나 **지능형 문서 생성 플랫폼**으로 진화하는 것을 목표로 합니다.

### 핵심 개선 방향
1. **지능화**: LLM 활용도 극대화
2. **확장성**: 동적 템플릿 시스템
3. **정확성**: NLP 기반 정보 추출
4. **품질**: 반복적 개선 프로세스
5. **통합**: Memory 시스템 연동

### 예상 임팩트
- 업무 효율성 300% 향상
- 문서 품질 대폭 개선
- 법적 리스크 최소화
- 사용자 만족도 향상

이 계획서를 기반으로 단계적이고 체계적인 고도화를 진행하여, 최종적으로는 **업계 최고 수준의 AI 문서 생성 시스템**을 구축할 수 있을 것으로 기대됩니다.

---

**작성자**: Claude Code
**검토 필요**: 개발팀 리드, 제품 관리자
**다음 단계**: 구현 우선순위 확정 후 Phase 1 개발 착수