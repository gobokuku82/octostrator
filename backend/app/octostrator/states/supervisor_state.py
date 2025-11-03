"""Supervisor State 정의

LangGraph 1.0의 TypedDict 기반 State 구조
"""
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SupervisorState(TypedDict):
    """Supervisor 기본 State (최소 버전)

    Attributes:
        messages: 대화 메시지 히스토리
            - Annotated[Sequence[BaseMessage], add_messages]로 정의하여
              LangGraph가 자동으로 메시지를 누적하도록 함
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
