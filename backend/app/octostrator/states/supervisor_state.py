"""Supervisor State 정의

LangGraph 1.0의 TypedDict 기반 State 구조
Phase 2: Planning-Based Execution을 위한 State 확장
"""
from typing import TypedDict, Annotated, Sequence, Optional, List, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class TaskStep(BaseModel):
    """개별 작업 단계

    Planning Agent가 생성하는 Task의 구조

    Attributes:
        step_id: 단계 ID
        agent: 실행할 Agent 이름 ("search", "analysis", "document", "hitl" 등)
        status: 현재 상태
        tool: 사용할 Tool (선택적)
        description: 작업 설명
        result: 실행 결과 (완료 후 저장)
        error: 에러 메시지 (실패 시 저장)
        hitl_question: HITL 질문 (agent가 "hitl"인 경우)
        hitl_response: 사용자 응답 (HITL 완료 후 저장)
    """
    step_id: int
    agent: str
    status: Literal["pending", "running", "completed", "failed", "waiting_human"] = "pending"
    tool: Optional[str] = None
    description: str
    result: Optional[str] = None
    error: Optional[str] = None
    hitl_question: Optional[str] = None
    hitl_response: Optional[str] = None


class SupervisorState(TypedDict, total=False):
    """Supervisor State with Plan Management

    Phase 2: Planning-Based Multi-Agent Execution을 위한 확장된 State
    Phase 3.5: Aggregator + Generator를 위한 State 확장

    Attributes:
        messages: 대화 메시지 히스토리
        user_intent: 파악된 사용자 의도 (Intent Understanding Node 결과)
        plan: 전체 작업 계획 (TaskStep 리스트를 dict로 변환)
        current_step: 현재 실행 중인 단계 인덱스
        is_planning: 계획 수립 중인가?
        is_executing: 실행 중인가?
        is_waiting_human: HITL 대기 중인가?
        aggregated_data: Aggregator가 생성한 구조화된 데이터 (Phase 3.5)
        output_format: 출력 형식 ("chat", "graph", "report") (Phase 3.5)
        final_result: 최종 결과 (모든 작업 완료 후)
    """
    # 필수 필드
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Planning 관련 (선택적)
    user_intent: Optional[str]
    plan: List[dict]
    current_step: int

    # Execution Flags (선택적)
    is_planning: bool
    is_executing: bool
    is_waiting_human: bool

    # Phase 3.5: Aggregation & Generation (선택적)
    aggregated_data: Optional[dict]
    output_format: str

    # Results (선택적)
    final_result: Optional[str]
