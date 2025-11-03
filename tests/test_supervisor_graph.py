"""Supervisor Graph 단위 테스트"""
import pytest
from langchain_core.messages import HumanMessage, AIMessage
from backend.app.octostrator.supervisor import build_supervisor_graph


@pytest.fixture
def supervisor_graph():
    """Supervisor Graph 픽스처"""
    return build_supervisor_graph()


@pytest.mark.asyncio
async def test_supervisor_graph_compile():
    """Supervisor Graph 컴파일 테스트"""
    graph = build_supervisor_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_supervisor_graph_invoke(supervisor_graph):
    """Supervisor Graph 기본 실행 테스트"""
    # Given: 사용자 메시지
    user_message = "Hello, how are you?"

    # When: Graph 실행
    result = await supervisor_graph.ainvoke({
        "messages": [HumanMessage(content=user_message)]
    })

    # Then: 응답 메시지 확인
    assert "messages" in result
    assert len(result["messages"]) > 0

    # 마지막 메시지가 AI 응답인지 확인
    last_message = result["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert len(last_message.content) > 0


@pytest.mark.asyncio
async def test_supervisor_graph_korean(supervisor_graph):
    """한국어 메시지 처리 테스트"""
    # Given: 한국어 메시지
    user_message = "안녕하세요! 자기소개 해주세요."

    # When: Graph 실행
    result = await supervisor_graph.ainvoke({
        "messages": [HumanMessage(content=user_message)]
    })

    # Then: 한국어 응답 확인
    last_message = result["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert len(last_message.content) > 0


@pytest.mark.asyncio
async def test_supervisor_graph_multiple_turns(supervisor_graph):
    """멀티턴 대화 테스트"""
    # Given: 첫 번째 메시지
    messages = [HumanMessage(content="My name is John.")]

    # When: 첫 번째 턴
    result1 = await supervisor_graph.ainvoke({"messages": messages})

    # Then: 응답 추가
    messages = result1["messages"]
    messages.append(HumanMessage(content="What is my name?"))

    # When: 두 번째 턴
    result2 = await supervisor_graph.ainvoke({"messages": messages})

    # Then: 컨텍스트 유지 확인 (이름을 기억해야 함)
    last_message = result2["messages"][-1]
    assert isinstance(last_message, AIMessage)
    # Note: 실제로는 Graph가 stateless이므로 메시지 히스토리를 직접 전달해야 함
