# DB Schema vs LangGraph State 연동 가이드

## 목차
1. [개요](#개요)
2. [DB Schema 분석](#db-schema-분석)
3. [LangGraph State 설계](#langgraph-state-설계)
4. [연동 패턴](#연동-패턴)
5. [구현 예시](#구현-예시)
6. [베스트 프랙티스](#베스트-프랙티스)

---

## 개요

본 문서는 공유 데이터베이스를 사용하는 FastAPI + LangGraph 시스템에서 DB Schema (Pydantic)와 LangGraph State (TypedDict)를 어떻게 연동할지 설명합니다.

### 핵심 원칙
1. **DB Schema**: 영속성 계층 (저장할 데이터)
2. **LangGraph State**: 실행 계층 (작업 중 데이터)
3. **Service Layer**: 두 계층의 변환 담당

---

## DB Schema 분석

### 현재 DB 테이블 구조

```
사용자 관련:
- users
- local_auths
- social_auths
- user_profiles

부동산 관련:
- regions
- real_estates
- transactions
- trust_scores
- user_favorites

채팅 관련:
- chat_sessions
- chat_messages
```

### LangGraph에서 필요한 DB 데이터

| 테이블 | LangGraph 사용 | 사용 목적 |
|--------|---------------|-----------|
| `users` | ✅ 필요 | 사용자 권한 확인, 개인화 |
| `chat_sessions` | ✅ 필수 | 세션 컨텍스트 |
| `chat_messages` | ✅ 필수 | 대화 이력 |
| `real_estates` | ✅ 필요 | 부동산 분석 데이터 |
| `transactions` | ✅ 필요 | 시장 분석 데이터 |
| `regions` | ✅ 필요 | 지역 정보 |
| `trust_scores` | ✅ 필요 | 신뢰도 분석 |
| `user_favorites` | ⚠️ 선택 | 추천 시스템 |
| `local_auths` | ❌ 불필요 | 인증만 사용 |
| `social_auths` | ❌ 불필요 | 인증만 사용 |
| `user_profiles` | ⚠️ 선택 | 개인화 응답 |

---

## LangGraph State 설계

### 1. MainSupervisorState - 전체 실행 상태

```python
# backend/app/service_agent/foundation/separated_states.py

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime

class MainSupervisorState(TypedDict):
    """메인 슈퍼바이저 상태"""

    # ============================================
    # DB에서 가져오는 데이터 (READ)
    # ============================================
    session_id: str  # chat_sessions.id
    user_id: int  # users.id
    user_query: str  # chat_messages.content (최신)

    # 대화 이력 (chat_messages에서 조회)
    conversation_history: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]

    # 사용자 정보 (users, user_profiles에서 조회)
    user_type: str  # users.type
    user_preferences: Optional[Dict[str, Any]]  # 개인화 설정

    # ============================================
    # LangGraph 실행 중 생성되는 데이터 (TEMPORARY)
    # ============================================
    current_team: str  # "search_team" | "analysis_team" | "document_team"
    next_team: Optional[str]

    # 팀별 작업 상태
    team_results: Dict[str, Any]  # {"search_team": {...}, "analysis_team": {...}}
    team_status: Dict[str, str]  # {"search_team": "completed", ...}

    # 처리 과정 추적 (로깅용, DB 저장 안함)
    processing_steps: List[Dict[str, Any]]
    error_logs: List[str]

    # ============================================
    # DB에 저장될 최종 결과 (WRITE)
    # ============================================
    final_answer: str  # chat_messages.content로 저장
    confidence_score: Optional[float]
    sources_used: List[str]

    # 메타데이터
    timestamp: str
    status: str  # "pending" | "processing" | "completed" | "error"
    error_message: Optional[str]
```

### 2. SearchTeamState - 검색 팀 상태

```python
class SearchTeamState(TypedDict):
    """검색 팀 전용 상태"""

    # ============================================
    # DB 참조 데이터
    # ============================================
    user_query: str
    session_id: str

    # 지역 정보 (regions 테이블에서 조회)
    target_regions: Optional[List[Dict[str, Any]]]  # [{"id": 1, "name": "강남구"}]

    # ============================================
    # 검색 작업 데이터 (TEMPORARY)
    # ============================================
    keywords: Optional[Dict[str, List[str]]]
    search_scope: List[str]  # ["legal", "real_estate", "loan"]

    # 검색 결과 (임시, DB 저장 안함)
    legal_results: List[Dict[str, Any]]
    real_estate_results: List[Dict[str, Any]]  # real_estates 테이블 검색 결과
    transaction_results: List[Dict[str, Any]]  # transactions 테이블 검색 결과

    # 집계 결과
    aggregated_results: Dict[str, Any]
    total_results: int
    search_time: float

    # ============================================
    # 메타데이터
    # ============================================
    search_progress: Dict[str, str]
    status: str
```

### 3. AnalysisTeamState - 분석 팀 상태

```python
class AnalysisTeamState(TypedDict):
    """분석 팀 전용 상태"""

    # ============================================
    # DB 참조 데이터
    # ============================================
    session_id: str
    user_id: int

    # 부동산 분석 대상 (real_estates 테이블)
    target_real_estate_ids: Optional[List[int]]

    # 부동산 상세 정보 (DB에서 조회한 데이터 스냅샷)
    property_data: Optional[List[Dict[str, Any]]]  # real_estates 조인 데이터

    # 거래 데이터 (transactions 테이블)
    transaction_data: Optional[List[Dict[str, Any]]]

    # 신뢰도 정보 (trust_scores 테이블)
    trust_scores: Optional[Dict[int, float]]  # {real_estate_id: score}

    # ============================================
    # 분석 작업 데이터 (TEMPORARY)
    # ============================================
    analysis_type: str  # "market" | "contract" | "investment" | "legal"

    # 전처리 데이터
    preprocessing_done: bool
    preprocessed_data: Optional[Dict[str, Any]]

    # 분석 결과 (임시)
    raw_analysis: Optional[Dict[str, Any]]
    market_analysis: Optional[Dict[str, Any]]
    contract_analysis: Optional[Dict[str, Any]]
    roi_analysis: Optional[Dict[str, Any]]

    # 인사이트
    insights: List[str]
    recommendations: List[str]
    confidence_score: float

    # ============================================
    # 최종 결과 (DB 저장 가능)
    # ============================================
    final_report: Optional[str]  # chat_messages로 저장되거나 별도 테이블

    # 메타데이터
    analysis_progress: Dict[str, str]
    status: str
```

---

## 연동 패턴

### 패턴 1: DB 데이터 → State (읽기)

```python
# Service Layer에서 DB → State 변환

from sqlalchemy.orm import Session
from app.models import ChatSession, ChatMessage, RealEstate, Transaction

async def create_initial_state(
    db: Session,
    session_id: str,
    user_message: str
) -> MainSupervisorState:
    """DB에서 데이터를 읽어 State 생성"""

    # 1. 세션 정보 조회
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise ValueError("Session not found")

    # 2. 대화 이력 조회 (최근 10개)
    messages = db.query(ChatMessage).filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()

    conversation_history = [
        {
            "role": msg.sender_type,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat()
        }
        for msg in reversed(messages)
    ]

    # 3. State 생성
    state: MainSupervisorState = {
        # DB 데이터
        "session_id": session_id,
        "user_id": session.user_id,
        "user_query": user_message,
        "conversation_history": conversation_history,
        "user_type": "user",  # users 테이블에서 조회 가능
        "user_preferences": None,

        # 작업 필드 (초기값)
        "current_team": "",
        "next_team": None,
        "team_results": {},
        "team_status": {},
        "processing_steps": [],
        "error_logs": [],

        # 결과 필드 (초기값)
        "final_answer": "",
        "confidence_score": None,
        "sources_used": [],

        # 메타데이터
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "error_message": None
    }

    return state
```

### 패턴 2: State → DB (쓰기)

```python
async def save_final_result(
    db: Session,
    state: MainSupervisorState
) -> ChatMessage:
    """State의 최종 결과를 DB에 저장"""

    # 1. 응답 메시지 저장
    assistant_message = ChatMessage(
        id=str(uuid4()),
        session_id=state["session_id"],
        sender_type="assistant",
        content=state["final_answer"],
        created_at=datetime.now()
    )
    db.add(assistant_message)

    # 2. 추가 분석 결과 저장 (선택적)
    # 예: analysis_results 테이블 생성 후 저장
    if state.get("team_results", {}).get("analysis_team"):
        analysis_result = AnalysisResult(
            id=str(uuid4()),
            session_id=state["session_id"],
            message_id=assistant_message.id,
            analysis_data=state["team_results"]["analysis_team"],
            confidence_score=state.get("confidence_score", 0.0),
            created_at=datetime.now()
        )
        db.add(analysis_result)

    db.commit()
    db.refresh(assistant_message)

    return assistant_message
```

### 패턴 3: 노드에서 DB 조회 (필요시)

```python
# AnalysisExecutor의 노드에서 DB 직접 조회

async def analyze_property_node(
    self,
    state: AnalysisTeamState
) -> AnalysisTeamState:
    """부동산 분석 노드"""

    # State에 real_estate_id가 있으면 DB에서 상세 정보 조회
    if state.get("target_real_estate_ids"):
        property_ids = state["target_real_estate_ids"]

        # DB 조회
        properties = self.db.query(RealEstate).filter(
            RealEstate.id.in_(property_ids)
        ).all()

        # State에 데이터 추가
        state["property_data"] = [
            {
                "id": prop.id,
                "name": prop.name,
                "address": prop.address,
                "property_type": prop.property_type,
                "completion_date": prop.completion_date
            }
            for prop in properties
        ]

        # 거래 데이터 조회
        transactions = self.db.query(Transaction).filter(
            Transaction.real_estate_id.in_(property_ids)
        ).order_by(Transaction.transaction_date.desc()).limit(50).all()

        state["transaction_data"] = [
            {
                "id": t.id,
                "real_estate_id": t.real_estate_id,
                "transaction_type": t.transaction_type,
                "price": t.price,
                "transaction_date": t.transaction_date.isoformat(),
                "exclusive_area": t.exclusive_area
            }
            for t in transactions
        ]

        # 신뢰도 조회
        trust_scores = self.db.query(TrustScore).filter(
            TrustScore.real_estate_id.in_(property_ids)
        ).all()

        state["trust_scores"] = {
            score.real_estate_id: float(score.score)
            for score in trust_scores
        }

    # 분석 수행
    state["raw_analysis"] = self._perform_analysis(state)
    state["status"] = "completed"

    return state
```

---

## 구현 예시

### 전체 플로우 구현

```python
# backend/app/service_agent/services/chat_service.py

from typing import Dict, Any
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from app.models import ChatSession, ChatMessage, User
from app.service_agent.supervisor.team_supervisor import TeamSupervisor
from app.service_agent.foundation.separated_states import MainSupervisorState

class ChatService:
    """채팅 서비스 - DB와 LangGraph 연동"""

    def __init__(self, db: Session):
        self.db = db
        self.supervisor = TeamSupervisor(db=db)  # DB 전달

    async def process_message(
        self,
        session_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """메시지 처리 전체 플로우"""

        # ============================================
        # 1. DB 검증 및 사전 작업
        # ============================================

        # 세션 확인
        session = self.db.query(ChatSession).filter_by(
            id=session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # 사용자 메시지 저장
        user_msg = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            sender_type="user",
            content=user_message,
            created_at=datetime.now()
        )
        self.db.add(user_msg)
        self.db.commit()

        # ============================================
        # 2. DB → State 변환
        # ============================================

        # 대화 이력 조회
        previous_messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()

        conversation_history = [
            {
                "role": msg.sender_type,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in reversed(previous_messages)
        ]

        # 사용자 정보 조회
        user = self.db.query(User).filter_by(
            id=session.user_id
        ).first()

        # State 생성
        initial_state: MainSupervisorState = {
            # DB 데이터
            "session_id": session_id,
            "user_id": session.user_id,
            "user_query": user_message,
            "conversation_history": conversation_history,
            "user_type": user.type if user else "user",
            "user_preferences": {},

            # 작업 필드
            "current_team": "",
            "next_team": None,
            "team_results": {},
            "team_status": {},
            "processing_steps": [],
            "error_logs": [],

            # 결과 필드
            "final_answer": "",
            "confidence_score": None,
            "sources_used": [],

            # 메타데이터
            "timestamp": datetime.now().isoformat(),
            "status": "processing",
            "error_message": None
        }

        # ============================================
        # 3. LangGraph 실행
        # ============================================

        try:
            result_state = await self.supervisor.invoke(initial_state)
        except Exception as e:
            # 에러 처리
            result_state = initial_state.copy()
            result_state["status"] = "error"
            result_state["error_message"] = str(e)
            result_state["final_answer"] = "죄송합니다. 처리 중 오류가 발생했습니다."

        # ============================================
        # 4. State → DB 저장
        # ============================================

        # 응답 메시지 저장
        assistant_msg = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            sender_type="assistant",
            content=result_state["final_answer"],
            created_at=datetime.now()
        )
        self.db.add(assistant_msg)

        # 세션 업데이트
        session.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(assistant_msg)

        # ============================================
        # 5. 응답 반환
        # ============================================

        return {
            "message_id": assistant_msg.id,
            "session_id": session_id,
            "content": assistant_msg.content,
            "confidence_score": result_state.get("confidence_score"),
            "sources": result_state.get("sources_used", []),
            "timestamp": assistant_msg.created_at.isoformat(),
            "status": result_state["status"]
        }
```

### SearchExecutor에서 DB 사용

```python
# backend/app/service_agent/execution_agents/search_executor.py

from sqlalchemy.orm import Session
from app.models import RealEstate, Transaction, Region

class SearchExecutor:
    """검색 실행 에이전트"""

    def __init__(self, db: Session = None):
        self.db = db
        # ... 기타 초기화

    async def execute_real_estate_search_node(
        self,
        state: SearchTeamState
    ) -> SearchTeamState:
        """부동산 검색 노드"""

        if not self.db:
            logger.warning("DB not available for real estate search")
            return state

        keywords = state.get("keywords", {})
        real_estate_keywords = keywords.get("real_estate", [])

        if not real_estate_keywords:
            return state

        # ============================================
        # DB에서 부동산 검색
        # ============================================

        # 지역명 추출
        region_names = [kw for kw in real_estate_keywords if "구" in kw or "동" in kw]

        results = []

        if region_names:
            # regions 테이블에서 지역 ID 찾기
            regions = self.db.query(Region).filter(
                Region.name.in_(region_names)
            ).all()

            region_ids = [r.id for r in regions]

            if region_ids:
                # real_estates 테이블에서 검색
                estates = self.db.query(RealEstate).filter(
                    RealEstate.region_id.in_(region_ids)
                ).limit(50).all()

                # 거래 데이터도 함께 조회
                for estate in estates:
                    # 최근 거래 3건
                    recent_transactions = self.db.query(Transaction).filter(
                        Transaction.real_estate_id == estate.id
                    ).order_by(
                        Transaction.transaction_date.desc()
                    ).limit(3).all()

                    # State에 저장할 형태로 변환
                    results.append({
                        "id": estate.id,
                        "name": estate.name,
                        "address": estate.address,
                        "property_type": estate.property_type,
                        "completion_date": estate.completion_date,
                        "recent_transactions": [
                            {
                                "type": t.transaction_type,
                                "price": t.price,
                                "date": t.transaction_date.isoformat(),
                                "area": t.exclusive_area
                            }
                            for t in recent_transactions
                        ]
                    })

        # State 업데이트
        state["real_estate_results"] = results
        state["search_progress"]["real_estate_search"] = "completed"

        return state
```

---

## 베스트 프랙티스

### 1. DB 데이터는 필요할 때만 조회

```python
# ✅ GOOD: 조건부 조회
async def analyze_node(state: AnalysisTeamState):
    if state.get("target_real_estate_ids"):
        # 필요할 때만 DB 조회
        properties = db.query(RealEstate).filter(...).all()
        state["property_data"] = [p.to_dict() for p in properties]

# ❌ BAD: 항상 조회
async def analyze_node(state: AnalysisTeamState):
    # 사용 여부와 관계없이 무조건 조회
    properties = db.query(RealEstate).all()
```

### 2. State에는 ID만, 노드에서 조회

```python
# ✅ GOOD: ID 참조
class AnalysisTeamState(TypedDict):
    target_real_estate_ids: Optional[List[int]]  # ID만 저장
    property_data: Optional[List[Dict]]  # 조회 후 스냅샷

async def node(state):
    if state["target_real_estate_ids"]:
        # 노드에서 조회
        data = db.query(...).filter(id.in_(state["target_real_estate_ids"])).all()
        state["property_data"] = [d.to_dict() for d in data]

# ❌ BAD: ORM 객체 직접 저장
class AnalysisTeamState(TypedDict):
    properties: List[RealEstate]  # ORM 객체 (직렬화 문제!)
```

### 3. 중간 결과는 State에만, 최종 결과만 DB에

```python
# ✅ GOOD: 명확한 분리
state = {
    # 중간 결과 (메모리에만)
    "search_results": [...],
    "preprocessing_done": True,
    "raw_analysis": {...},

    # 최종 결과 (DB 저장)
    "final_answer": "답변입니다",
    "confidence_score": 0.85
}

# 최종 결과만 DB 저장
db.add(ChatMessage(content=state["final_answer"]))

# ❌ BAD: 모든 것을 DB에 저장
db.add(IntermediateResult(search_results=state["search_results"]))  # 불필요
```

### 4. DB Session 관리

```python
# ✅ GOOD: Dependency Injection
class SearchExecutor:
    def __init__(self, db: Session = None):
        self.db = db

# Service에서 전달
service = ChatService(db=db_session)
supervisor = TeamSupervisor(db=db_session)

# ❌ BAD: 글로벌 DB 접근
class SearchExecutor:
    def search(self):
        from app.db import get_db  # 안티패턴
        db = get_db()
```

### 5. 트랜잭션 관리

```python
# ✅ GOOD: 명확한 트랜잭션
async def process_message(db: Session, ...):
    try:
        # 1. 사용자 메시지 저장
        db.add(user_msg)
        db.commit()

        # 2. LangGraph 실행 (DB 읽기만)
        result = await supervisor.invoke(state)

        # 3. 응답 저장
        db.add(assistant_msg)
        db.commit()

    except Exception as e:
        db.rollback()
        raise

# ❌ BAD: 노드 내부에서 commit
async def node(state):
    db.add(something)
    db.commit()  # 다른 노드 실패 시 롤백 불가!
```

---

## 요약

### DB Schema (Pydantic)
- **역할**: 영속성 계층
- **테이블**: users, chat_sessions, chat_messages, real_estates, transactions 등
- **용도**: API 입출력, 데이터 저장

### LangGraph State (TypedDict)
- **역할**: 실행 계층
- **구성**: DB 참조 데이터 + 임시 작업 데이터
- **용도**: 팀 간 데이터 전달, 중간 결과 보관

### 연동 패턴
1. **DB → State**: Service Layer에서 조회 후 변환
2. **State 실행**: LangGraph 노드들이 State 처리
3. **노드 내 DB 조회**: 필요시 추가 데이터 조회
4. **State → DB**: 최종 결과만 DB에 저장

### 핵심 원칙
✅ State는 DB 데이터를 **읽어서** 사용
✅ 중간 결과는 State에만 (메모리)
✅ 최종 결과만 DB에 **저장**
✅ ID 참조 방식으로 느슨한 결합 유지

---

*작성일: 2025-10-06*
*버전: 1.0*
