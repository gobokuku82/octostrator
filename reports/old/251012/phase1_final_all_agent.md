🔄 Service Agent 작업 순서 및 데이터 흐름
1️⃣ 전체 아키텍처 개요
사용자 쿼리
    ↓
[PlanningAgent] ← LLM 호출 #1: Intent 분석
    ↓
    ├─ Intent 결정 (COMPREHENSIVE, LEGAL_CONSULT 등)
    ├─ Confidence (0.0~1.0)
    └─ Suggested Agents 선택
         ↓
[QueryDecomposer] ← LLM 호출 #2: 복합 질문 분해 (선택적)
    ↓
[ExecutionPlan 생성] → 실행할 팀과 순서 결정
    ↓
    ├─ search_team (순차 실행)
    ├─ analysis_team
    └─ document_team
         ↓
각 팀의 LangGraph 실행
    ↓
최종 결과 통합
2️⃣ 단계별 상세 흐름
Phase 1: 의도 분석 및 계획 수립
1.1 PlanningAgent.analyze_intent()
📍 위치: backend/app/service_agent/cognitive_agents/planning_agent.py:95-184
async def analyze_intent(query: str) -> IntentResult:
    """
    LLM이 판단하는 것:
    - intent: COMPREHENSIVE, LEGAL_CONSULT, MARKET_INQUIRY 등
    - confidence: 0.0~1.0
    - keywords: ['전세금', '인상', '법적']
    - entities: {'price': '3억→10억', 'contract_type': '전세'}
    - suggested_agents: ['search_team', 'analysis_team']
    """
LLM 호출 내용:
프롬프트: "intent_analysis"
입력 데이터:
  - query: "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 해결방법 알려줘"
  - available_intents: [COMPREHENSIVE, LEGAL_CONSULT, ...]
  
LLM 반환:
{
  "intent": "COMPREHENSIVE",
  "confidence": 0.95,
  "keywords": ["전세금", "인상", "법적"],
  "entities": {"price": "3억→10억"},
  "reasoning": "법률 검색 + 상황 분석 필요 → COMPREHENSIVE"
}
데이터 저장 위치:
❌ SQLite에 저장 안됨
✅ Python 메모리: IntentResult 객체
✅ 다음 단계로 전달
1.2 Agent 선택 (3단계 Fallback)
📍 위치: planning_agent.py:240-304
1차 시도: Primary LLM (상세 버전)
   ↓ 실패시
2차 시도: Simplified LLM (간소화 버전)
   ↓ 실패시
3차 Fallback: 하드코딩된 기본값
LLM 호출 #2: agent_selection
프롬프트: "agent_selection"
입력:
  - query: 원본 쿼리
  - intent_type: "COMPREHENSIVE"
  - available_agents: {
      "search_team": {"capabilities": "법률 검색, 시세 조회"},
      "analysis_team": {"capabilities": "데이터 분석, 리스크 평가"},
      "document_team": {"capabilities": "계약서 작성"}
    }

LLM 반환:
{
  "selected_agents": ["search_team", "analysis_team"],
  "reasoning": "법률 정보 검색 후 상황 분석 필요"
}
Fallback 기본값:
safe_defaults = {
    IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
    IntentType.LEGAL_CONSULT: ["search_team"],
    IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
}
1.3 Query Decomposition (복합 질문 분해)
📍 위치: backend/app/service_agent/cognitive_agents/query_decomposer.py LLM 호출 #3: query_decomposition (조건부)
# 단순 질문은 스킵, 복합 질문만 분해
if is_compound:
    LLM 호출:
      프롬프트: "query_decomposition"
      입력:
        - query: "강남 시세 확인하고 대출 한도 계산해줘"
      
      반환:
      {
        "is_compound": true,
        "sub_tasks": [
          {"description": "강남 아파트 시세 조회", "agent": "search_team"},
          {"description": "대출 한도 계산", "agent": "analysis_team"}
        ],
        "execution_order": "sequential"
      }
Phase 2: 팀별 실행 (LangGraph)
2.1 AnalysisTeam 예시
📍 위치: backend/app/service_agent/execution_agents/analysis_executor.py
# LangGraph 노드 구조
workflow = StateGraph(AnalysisTeamState)

workflow.add_node("prepare", prepare_node)         # 데이터 준비
workflow.add_node("preprocess", preprocess_node)   # 전처리
workflow.add_node("analyze", analyze_data_node)    # 🔥 핵심 분석
workflow.add_node("generate_insights", insights_node)  # LLM 인사이트
workflow.add_node("create_report", report_node)    # 보고서 생성
workflow.add_node("finalize", finalize_node)       # 완료

# 순차 실행
workflow.set_entry_point("prepare")
workflow.add_edge("prepare", "preprocess")
workflow.add_edge("preprocess", "analyze")
workflow.add_edge("analyze", "generate_insights")
workflow.add_edge("generate_insights", "create_report")
workflow.add_edge("create_report", "finalize")
2.2 analyze_data_node (실제 분석)
📍 위치: analysis_executor.py:113-164
async def analyze_data_node(state: AnalysisTeamState):
    """
    실제 분석 수행 - NO MOCK!
    """
    from analysis_tools import MarketAnalyzer, TrendAnalyzer, RiskAssessor
    
    results = {}
    
    # 1. 시장 분석
    market_analyzer = MarketAnalyzer()
    results["market"] = await market_analyzer.execute(preprocessed_data)
    
    # 2. 트렌드 분석
    trend_analyzer = TrendAnalyzer()
    results["trend"] = await trend_analyzer.execute(preprocessed_data)
    
    # 3. 리스크 평가
    risk_assessor = RiskAssessor()
    results["risk"] = await risk_assessor.execute(preprocessed_data)
    
    # 4. 맞춤 분석 (전세금 인상률)
    results["custom"] = _perform_custom_analysis(query, preprocessed_data)
    # 👆 여기서 정규식으로 "3억", "10억" 추출 → 233.3% 계산
    
    # State에 저장
    state["raw_analysis"] = results  # 🔥 이 데이터가 최종 결과에 포함
    state["analysis_status"] = "completed"
    
    return state
2.3 generate_insights_node (LLM 인사이트 생성)
📍 위치: analysis_executor.py:243-316 LLM 호출 #4: insight_generation
프롬프트: "insight_generation"
입력:
  - raw_analysis: {
      "market": {"status": "success", "avg_price": 5억},
      "trend": {"price_change_3m": 5.2%},
      "risk": {"risk_score": 63},
      "custom": {
        "type": "rent_increase_analysis",
        "increase_rate": "233.3%",
        "is_legal": false
      }
    }
  - query: 원본 쿼리

LLM 반환:
{
  "insights": [
    {
      "type": "key_finding",
      "content": "인상률 233.3%는 법정 한도 5%를 초과합니다",
      "confidence": 0.95
    },
    {
      "type": "trend",
      "content": "최근 3개월간 부동산 가격 5.2% 상승"
    }
  ]
}
3️⃣ 데이터 저장 및 관리
저장소별 역할
저장소	저장 내용	용도	지속성
Python 메모리	IntentResult, 중간 계산 결과	실행 중 임시 데이터	❌ 휘발성
State (TypedDict)	각 팀의 작업 상태 및 결과	팀 내부 상태 관리	✅ LangGraph 실행 중 유지
SharedState	팀 간 공유 데이터	팀 간 통신	✅ 전체 실행 동안 유지
SQLite (LangGraph Checkpointer)	LangGraph 체크포인트	재시작/디버깅	✅ 영구 저장 (선택적)
최종 결과 (return)	통합된 최종 응답	사용자에게 반환	✅ API 응답
State 구조 상세
AnalysisTeamState
📍 위치: backend/app/service_agent/foundation/separated_states.py:199-229
class AnalysisTeamState(TypedDict):
    # 팀 식별
    team_name: str
    status: str  # "pending", "analyzing", "completed"
    
    # 공유 컨텍스트
    shared_context: Dict[str, Any]  # 🔥 SharedState가 여기 들어감
    
    # 분석 입력
    analysis_type: str  # "comprehensive", "market", "risk"
    input_data: Dict[str, Any]  # search_team 결과 등
    
    # 🔥 분석 결과 (핵심!)
    raw_analysis: Dict[str, Any]  # analysis_tools 실행 결과
    metrics: Dict[str, float]
    insights: List[str]  # LLM 생성 인사이트
    report: Dict[str, Any]
    
    # 진행 상태
    analysis_progress: Dict[str, str]
    
    # 타이밍
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    analysis_time: Optional[float]
데이터 흐름:
1. 초기 상태 생성 (execute 메서드)
   ↓
2. LangGraph 노드들이 state 수정
   - analyze_data_node: state["raw_analysis"] = {...}
   - insights_node: state["insights"] = [...]
   - report_node: state["report"] = {...}
   ↓
3. 최종 state 반환
   ↓
4. API 응답에 포함
SharedContext (팀 간 데이터 공유)
shared_context = {
    "query": "집주인이 전세금 3억을...",
    "session_id": "abc123",
    "intent": "COMPREHENSIVE",
    "user_id": "user001"
}

# search_team 실행 후
shared_context["search_results"] = {...}

# analysis_team이 search 결과 사용
analysis_input = shared_context["search_results"]
4️⃣ LLM 호출 요약
순서	호출 위치	프롬프트 이름	입력	출력	목적
1	PlanningAgent	intent_analysis	query	intent, confidence, keywords	의도 파악
2	PlanningAgent	agent_selection	intent, query, available_agents	selected_agents	팀 선택
3	QueryDecomposer	query_decomposition	query, intent	sub_tasks, execution_order	질문 분해 (조건부)
4	AnalysisTeam	insight_generation	raw_analysis, query	insights[]	인사이트 생성
5️⃣ 실제 예시: "전세금 3억을 10억으로"
[사용자 쿼리]
"집주인이 전세금 3억을 10억으로 올려달래. 법적으로 해결방법 알려줘"

↓ LLM #1: Intent 분석

{intent: "COMPREHENSIVE", confidence: 0.95}

↓ LLM #2: Agent 선택

["search_team", "analysis_team"]

↓ QueryDecomposer (스킵 - 단순 질문)

↓ search_team 실행 (가정)

{
  "legal_results": [{"law": "주택임대차보호법", "limit": "5%"}]
}
→ shared_context["search_results"]에 저장

↓ analysis_team 실행

[prepare_node]
input_data = shared_context["search_results"]

↓

[analyze_data_node]
# 정규식 추출
amounts = ["3", "10"]  
increase_rate = ((10-3)/3)*100 = 233.3%

state["raw_analysis"] = {
  "market": {...},
  "trend": {...},
  "risk": {...},
  "custom": {
    "type": "rent_increase_analysis",
    "increase_rate": "233.3%",
    "is_legal": false,
    "assessment": "법정 한도 5%를 초과합니다"
  }
}

↓ LLM #4: Insight 생성

state["insights"] = [
  "인상률 233.3%는 법정 한도 5% 초과",
  "거부 가능"
]

↓

[최종 결과]
{
  "status": "completed",
  "raw_analysis": {...},
  "insights": [...],
  "report": {...}
}
6️⃣ 핵심 정리
LLM이 하는 일:
✅ Intent 분석 (COMPREHENSIVE인지, LEGAL_CONSULT인지 판단)
✅ Agent 선택 (어떤 팀을 실행할지 결정)
✅ 복합 질문 분해 (2개 이상 작업으로 나누기)
✅ Insight 생성 (분석 결과를 사람이 읽을 수 있게 설명)
LLM이 안 하는 일 (코드로 처리):
❌ 전세금 인상률 계산 (정규식 + 수식)
❌ 시장/트렌드/리스크 분석 (analysis_tools의 로직)
❌ State 관리 (LangGraph)
데이터 저장:
실행 중: Python 메모리 + State (TypedDict)
팀 간 공유: SharedContext
영구 저장: SQLite Checkpointer (선택적)
최종 반환: API 응답 JSON
NO MOCK 보장:
✅ _mock_analysis() 완전 삭제
✅ analysis_tools 실제 실행
✅ 정규식으로 실제 계산 (233.3%)