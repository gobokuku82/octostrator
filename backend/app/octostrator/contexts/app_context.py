"""Application Context - 런타임 불변 정보

LangGraph 0.6+ Context API 사용
- Context는 State와 별도로 관리되는 불변 런타임 정보
- Checkpoint에 저장되지 않음
- 모든 노드에서 접근 가능

참고: reports/context_management/langgraph_context_analysis.md
"""
from dataclasses import dataclass
from typing import Optional
from langchain_openai import ChatOpenAI


@dataclass
class AppContext:
    """Application 런타임 Context

    불변 정보만 포함:
    - user_id: 사용자 ID
    - session_id: 세션 ID
    - llm: LLM 인스턴스 (노드 간 공유)
    - db_conn: DB 연결 (Phase 5에서 추가 예정)
    """

    # 사용자 정보
    user_id: str
    session_id: str

    # LLM 설정
    llm: ChatOpenAI

    # DB 연결 (Phase 5에서 활성화)
    db_conn: Optional[str] = None

    # 디버그 모드
    debug: bool = False
