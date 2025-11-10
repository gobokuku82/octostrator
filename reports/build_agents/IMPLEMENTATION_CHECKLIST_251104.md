# Agent 시스템 구현 체크리스트

**작성일**: 2025-11-04
**관련 문서**: AGENT_SYSTEM_DESIGN_251104.md

## Phase 1: Registry 및 Base 구조 구축

### 1.1 디렉토리 구조 생성
- [ ] `backend/app/octostrator/agents/` 하위 구조 생성
  - [ ] `base/` - Base Agent 클래스
  - [ ] `contract_agent/` - 계약서 분석 Agent
  - [ ] `law_agent/` - 법률 검색 Agent
  - [ ] `report_agent/` - 보고서 생성 Agent
  - [ ] `chat_agent/` - 대화형 Agent
  - [ ] `registry.py` - Agent Registry

- [ ] `backend/app/octostrator/sub_graphs/` 재구성
  - [ ] 기존 하위 폴더 제거 (평면 구조로 전환)
  - [ ] `registry.py` - SubGraph Registry
  - [ ] 각 SubGraph 파일들 (validation_graph.py, rag_graph.py 등)

- [ ] `backend/app/octostrator/tools/` 재구성
  - [ ] 기존 하위 폴더 제거 (평면 구조로 전환)
  - [ ] `registry.py` - Tool Registry
  - [ ] 각 Tool 파일들

### 1.2 Registry 구현
- [ ] `agents/registry.py` 작성
  - [ ] AgentRegistry 클래스 (싱글톤)
  - [ ] register() 메서드
  - [ ] get() 메서드 (Lazy Initialization)
  - [ ] list_agents() 메서드
  - [ ] Thread Safety (Lock 사용)

- [ ] `sub_graphs/registry.py` 작성
  - [ ] SubGraphRegistry 클래스 (싱글톤)
  - [ ] register() 메서드
  - [ ] get() 메서드 (캐싱)
  - [ ] list_subgraphs() 메서드

- [ ] `tools/registry.py` 작성
  - [ ] ToolRegistry 클래스 (싱글톤)
  - [ ] register() 메서드
  - [ ] get() 메서드
  - [ ] get_metadata() 메서드
  - [ ] list_tools() 메서드

### 1.3 Base Agent 구현
- [ ] `agents/base/agent_config.py` 작성
  - [ ] AgentConfig Pydantic 모델
  - [ ] 필드: name, description, llm_model, temperature, max_tokens, tools, subgraphs

- [ ] `agents/base/agent_base.py` 작성
  - [ ] BaseAgent 추상 클래스
  - [ ] @abstractmethod build_graph()
  - [ ] @abstractmethod get_state_schema()
  - [ ] compile() 메서드
  - [ ] invoke() 메서드
  - [ ] stream() 메서드
  - [ ] get_tools() 메서드
  - [ ] get_subgraphs() 메서드

### 1.4 공통 State 정의
- [ ] `states/common_state.py` 작성
  - [ ] BaseState TypedDict
  - [ ] 공통 필드 정의 (user_id, session_id, timestamp 등)

### 1.5 테스트
- [ ] Registry 단위 테스트
  - [ ] Singleton 패턴 검증
  - [ ] 등록/조회 기능 테스트
  - [ ] Thread Safety 테스트
- [ ] BaseAgent 단위 테스트

---

## Phase 2: 공유 리소스 구현

### 2.1 SubGraph 구현

#### Validation SubGraph
- [ ] `sub_graphs/validation_graph.py` 작성
  - [ ] ValidationState 정의
  - [ ] validate_schema() 노드
  - [ ] validate_business_rules() 노드
  - [ ] decide_validity() 조건부 라우팅
  - [ ] build_validation_graph() 함수
  - [ ] Registry 등록

#### RAG SubGraph
- [ ] `sub_graphs/rag_graph.py` 작성
  - [ ] RAGState 정의
  - [ ] retrieve_documents() 노드
  - [ ] build_context() 노드
  - [ ] generate_answer() 노드
  - [ ] build_rag_graph() 함수
  - [ ] Registry 등록

#### Search SubGraph
- [ ] `sub_graphs/search_graph.py` 작성
  - [ ] SearchState 정의
  - [ ] parse_query() 노드
  - [ ] execute_search() 노드
  - [ ] rank_results() 노드
  - [ ] build_search_graph() 함수
  - [ ] Registry 등록

#### Formatting SubGraph
- [ ] `sub_graphs/formatting_graph.py` 작성
  - [ ] FormattingState 정의
  - [ ] extract_structure() 노드
  - [ ] apply_template() 노드
  - [ ] build_formatting_graph() 함수
  - [ ] Registry 등록

#### HITL SubGraph
- [ ] `sub_graphs/hitl_graph.py` 작성
  - [ ] HITLState 정의
  - [ ] request_approval() 노드
  - [ ] wait_for_response() 노드 (인터럽트)
  - [ ] process_feedback() 노드
  - [ ] build_hitl_graph() 함수
  - [ ] Registry 등록

### 2.2 Tool 구현

#### Database Tool
- [ ] `tools/database_tool.py` 작성
  - [ ] query_database() 함수
  - [ ] insert_data() 함수
  - [ ] update_data() 함수
  - [ ] Registry 등록

#### Vector Search Tool
- [ ] `tools/vector_search_tool.py` 작성
  - [ ] vector_search_tool() 함수
  - [ ] 벡터 DB 연동 (Pinecone/Qdrant)
  - [ ] similarity_search() 로직
  - [ ] Registry 등록

#### LLM Tool
- [ ] `tools/llm_tool.py` 작성
  - [ ] llm_tool() 함수
  - [ ] ChatOpenAI 통합
  - [ ] 프롬프트 템플릿 처리
  - [ ] Registry 등록

#### Text Processing Tool
- [ ] `tools/text_processing_tool.py` 작성
  - [ ] clean_text() 함수
  - [ ] extract_keywords() 함수
  - [ ] tokenize() 함수
  - [ ] Registry 등록

#### PDF Tool
- [ ] `tools/pdf_tool.py` 작성
  - [ ] extract_text() 함수
  - [ ] parse_structure() 함수
  - [ ] PyPDF2/pdfplumber 통합
  - [ ] Registry 등록

#### Validation Tool
- [ ] `tools/validation_tool.py` 작성
  - [ ] validate_format() 함수
  - [ ] validate_content() 함수
  - [ ] check_completeness() 함수
  - [ ] Registry 등록

### 2.3 테스트
- [ ] 각 SubGraph 단위 테스트
- [ ] 각 Tool 단위 테스트
- [ ] Registry 통합 테스트

---

## Phase 3: Agent 구현

### 3.1 Contract Agent (계약서 분석)

#### State 정의
- [ ] `agents/contract_agent/state.py` 작성
  - [ ] ContractAgentState TypedDict
  - [ ] 필드: contract_text, clauses, risk_analysis, validation_result

#### Nodes 구현
- [ ] `agents/contract_agent/nodes/` 작성
  - [ ] `analyze.py` - analyze_contract() 함수
  - [ ] `validate.py` - validate_contract() 함수
  - [ ] `extract_clauses.py` - extract_clauses() 함수 (선택)

#### Prompts
- [ ] `agents/contract_agent/prompts.py` 작성
  - [ ] 계약서 분석 프롬프트
  - [ ] 조항 추출 프롬프트
  - [ ] 리스크 분석 프롬프트

#### Graph 구성
- [ ] `agents/contract_agent/graph.py` 작성 (또는 agent.py 내부)
  - [ ] build_graph() 메서드 구현
  - [ ] Nodes 추가
  - [ ] SubGraph 통합 (validation_graph, rag_graph)
  - [ ] Edges 정의

#### Agent 클래스
- [ ] `agents/contract_agent/agent.py` 작성
  - [ ] ContractAgent(BaseAgent) 클래스
  - [ ] __init__() - AgentConfig 설정
  - [ ] build_graph() 구현
  - [ ] get_state_schema() 구현

### 3.2 Law Agent (법률 검색)

#### State 정의
- [ ] `agents/law_agent/state.py` 작성
  - [ ] LawAgentState TypedDict
  - [ ] 필드: query, laws, summary, references

#### Nodes 구현
- [ ] `agents/law_agent/nodes/` 작성
  - [ ] `search.py` - search_laws() 함수
  - [ ] `summarize.py` - summarize_results() 함수
  - [ ] `filter.py` - filter_relevant_laws() 함수 (선택)

#### Prompts
- [ ] `agents/law_agent/prompts.py` 작성
  - [ ] 법률 검색 쿼리 프롬프트
  - [ ] 요약 프롬프트
  - [ ] 관련성 판단 프롬프트

#### Graph 구성
- [ ] `agents/law_agent/graph.py` (또는 agent.py 내부)
  - [ ] build_graph() 구현
  - [ ] SubGraph 통합 (search_graph, rag_graph)

#### Agent 클래스
- [ ] `agents/law_agent/agent.py` 작성
  - [ ] LawAgent(BaseAgent) 클래스

### 3.3 Report Agent (보고서 생성)

#### State 정의
- [ ] `agents/report_agent/state.py` 작성
  - [ ] ReportAgentState TypedDict
  - [ ] 필드: data, structure, formatted_report, template

#### Nodes 구현
- [ ] `agents/report_agent/nodes/` 작성
  - [ ] `structure.py` - create_structure() 함수
  - [ ] `format.py` - format_report() 함수
  - [ ] `export.py` - export_to_pdf() 함수 (선택)

#### Prompts
- [ ] `agents/report_agent/prompts.py` 작성
  - [ ] 보고서 구조 생성 프롬프트
  - [ ] 섹션별 작성 프롬프트

#### Graph 구성
- [ ] `agents/report_agent/graph.py`
  - [ ] SubGraph 통합 (formatting_graph)

#### Agent 클래스
- [ ] `agents/report_agent/agent.py` 작성
  - [ ] ReportAgent(BaseAgent) 클래스

### 3.4 Chat Agent (대화형)

#### State 정의
- [ ] `agents/chat_agent/state.py` 작성
  - [ ] ChatAgentState TypedDict
  - [ ] 필드: messages, context, response

#### Nodes 구현
- [ ] `agents/chat_agent/nodes/` 작성
  - [ ] `respond.py` - generate_response() 함수
  - [ ] `context_manager.py` - manage_context() 함수 (선택)

#### Prompts
- [ ] `agents/chat_agent/prompts.py` 작성
  - [ ] 대화 시스템 프롬프트
  - [ ] Few-shot 예시

#### Graph 구성
- [ ] `agents/chat_agent/graph.py`
  - [ ] 간단한 선형 그래프

#### Agent 클래스
- [ ] `agents/chat_agent/agent.py` 작성
  - [ ] ChatAgent(BaseAgent) 클래스

### 3.5 Agent 등록
- [ ] `agents/__init__.py` 수정
  - [ ] register_all_agents() 함수 작성
  - [ ] 모든 Agent import 및 등록

### 3.6 테스트
- [ ] 각 Agent 단위 테스트
  - [ ] Mock Tool/SubGraph 사용
  - [ ] Graph 실행 테스트
- [ ] Agent 통합 테스트

---

## Phase 4: Supervisor 통합

### 4.1 Router 수정
- [ ] `supervisor/nodes/router.py` 수정
  - [ ] route_to_agent() 함수 수정
  - [ ] AgentRegistry 사용
  - [ ] Intent → Agent 매핑 로직

### 4.2 Executor 수정
- [ ] `supervisor/nodes/executor.py` 수정
  - [ ] execute_agent() 함수 수정
  - [ ] AgentRegistry에서 Agent 가져오기
  - [ ] Agent.invoke() 호출
  - [ ] 결과 처리

### 4.3 Supervisor Graph 수정
- [ ] `supervisor/graph.py` 수정
  - [ ] Agent 실행 노드 추가
  - [ ] 조건부 라우팅 업데이트
  - [ ] SubGraph 통합 (HITL 등)

### 4.4 State 통합
- [ ] `states/supervisor_state.py` 수정
  - [ ] agent_results 필드 추가
  - [ ] selected_agent 필드 추가

### 4.5 테스트
- [ ] Supervisor → Agent 통합 테스트
- [ ] End-to-End 테스트
- [ ] 에러 시나리오 테스트

---

## Phase 5: 최적화 및 문서화

### 5.1 성능 최적화
- [ ] Agent 인스턴스 캐싱 검증
- [ ] SubGraph 재사용 검증
- [ ] 메모리 프로파일링
- [ ] 응답 시간 측정 및 최적화

### 5.2 에러 핸들링
- [ ] Agent 실패 시 Fallback
- [ ] Tool/SubGraph 에러 처리
- [ ] 사용자 친화적 에러 메시지

### 5.3 로깅 및 모니터링
- [ ] Agent 실행 로깅
- [ ] 성능 메트릭 수집 (Prometheus/Grafana)
- [ ] 에러 추적 (Sentry)

### 5.4 문서화
- [ ] Agent 개발 가이드
- [ ] Tool 개발 가이드
- [ ] SubGraph 개발 가이드
- [ ] API 문서 (Swagger/OpenAPI)
- [ ] 아키텍처 다이어그램

### 5.5 코드 품질
- [ ] 타입 힌팅 검증 (mypy)
- [ ] Linting (ruff/black)
- [ ] 테스트 커버리지 90% 이상
- [ ] 코드 리뷰

---

## 추가 고려사항

### 보안
- [ ] Agent 권한 관리
- [ ] Tool 접근 제어
- [ ] 입력 검증 및 Sanitization

### 확장성
- [ ] 새 Agent 추가 프로세스 문서화
- [ ] Agent 템플릿 생성
- [ ] CLI 도구 (Agent 스캐폴딩)

### 배포
- [ ] Docker 이미지 업데이트
- [ ] 환경 변수 설정
- [ ] 마이그레이션 스크립트 (필요 시)

---

## 마일스톤

| Phase | 완료 예정일 | 상태 |
|-------|------------|------|
| Phase 1: Registry & Base | Week 1 | ⬜ Pending |
| Phase 2: 공유 리소스 | Week 2 | ⬜ Pending |
| Phase 3: Agent 구현 | Week 3-4 | ⬜ Pending |
| Phase 4: Supervisor 통합 | Week 5 | ⬜ Pending |
| Phase 5: 최적화 | Week 6 | ⬜ Pending |

---

## 체크리스트 사용법

1. 각 항목 앞의 `[ ]`를 완료 시 `[x]`로 변경
2. 각 Phase 완료 후 팀 리뷰 진행
3. 이슈 발생 시 해당 항목에 코멘트 추가
4. 주간 진행 상황 업데이트

---

**문서 끝**
