"""WebSocket 엔드포인트

Phase 4.3: 실시간 스트리밍 구현
"""
import asyncio
import json
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import create_session, get_session_config


router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        """초기화"""
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """클라이언트 연결

        Args:
            session_id: 세션 ID
            websocket: WebSocket 객체
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"[WebSocket] Client connected: {session_id}")

    def disconnect(self, session_id: str):
        """클라이언트 연결 해제

        Args:
            session_id: 세션 ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"[WebSocket] Client disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """메시지 전송

        Args:
            session_id: 세션 ID
            message: 전송할 메시지 (dict)
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"[WebSocket] Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)


# 전역 ConnectionManager 인스턴스
manager = ConnectionManager()


async def create_progress_callback(session_id: str):
    """Progress callback 생성

    Args:
        session_id: 세션 ID

    Returns:
        async callback 함수
    """
    async def progress_callback(event_type: str, event_data: dict):
        """진행 상황 콜백

        Args:
            event_type: 이벤트 타입
            event_data: 이벤트 데이터
        """
        message = {
            "type": event_type,
            "data": event_data,
            "session_id": session_id
        }
        await manager.send_message(session_id, message)

    return progress_callback


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket 채팅 엔드포인트

    Phase 4.3: 실시간 스트리밍

    클라이언트는 다음 형식으로 메시지를 전송합니다:
    {
        "message": "사용자 메시지",
        "output_format": "chat"  # optional
    }

    서버는 다음 형식으로 이벤트를 전송합니다:
    {
        "type": "node_started" | "node_completed" | "hitl_waiting" | "final_result" | "error",
        "data": { ... },
        "session_id": "..."
    }

    Args:
        websocket: WebSocket 연결
        session_id: 세션 ID
    """
    # 연결 수락
    await manager.connect(session_id, websocket)

    # Checkpointer 및 Graph 초기화
    checkpointer = None
    graph = None

    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()
        print(f"[WebSocket] Checkpointer 생성 완료: {session_id}")

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)
        print(f"[WebSocket] Graph 빌드 완료: {session_id}")

        # 연결 성공 메시지
        await manager.send_message(session_id, {
            "type": "connected",
            "data": {"message": "WebSocket 연결 성공"},
            "session_id": session_id
        })

        # 메시지 수신 루프
        while True:
            # 클라이언트 메시지 대기
            data = await websocket.receive_json()

            # 메시지 검증
            if "message" not in data:
                await manager.send_message(session_id, {
                    "type": "error",
                    "data": {"error": "Message field is required"},
                    "session_id": session_id
                })
                continue

            user_message = data["message"]
            output_format = data.get("output_format", "chat")

            print(f"[WebSocket] Received message from {session_id}: {user_message[:50]}...")

            # Progress callback 생성
            progress_callback = await create_progress_callback(session_id)

            # thread_id로 config 생성
            config = get_session_config(session_id)

            # 그래프 실행
            try:
                # 실행 시작 알림
                await manager.send_message(session_id, {
                    "type": "execution_started",
                    "data": {"message": "처리 중..."},
                    "session_id": session_id
                })

                # 그래프 스트리밍 실행
                # astream_events()를 사용하여 실시간 이벤트 수신
                initial_input = {
                    "messages": [HumanMessage(content=user_message)],
                    "output_format": output_format
                }

                # 실시간 스트리밍
                async for event in graph.astream_events(initial_input, config=config, version="v2"):
                    # 이벤트 타입별 처리
                    event_type = event.get("event")
                    event_name = event.get("name")
                    event_data = event.get("data", {})

                    # 노드 시작
                    if event_type == "on_chain_start":
                        if event_name and not event_name.startswith("__"):
                            await manager.send_message(session_id, {
                                "type": "node_started",
                                "data": {
                                    "node": event_name,
                                    "run_id": event.get("run_id")
                                },
                                "session_id": session_id
                            })

                    # 노드 완료
                    elif event_type == "on_chain_end":
                        if event_name and not event_name.startswith("__"):
                            await manager.send_message(session_id, {
                                "type": "node_completed",
                                "data": {
                                    "node": event_name,
                                    "run_id": event.get("run_id")
                                },
                                "session_id": session_id
                            })

                    # HITL interrupt 감지
                    elif event_type == "on_chain_stream" and "is_waiting_human" in event_data.get("chunk", {}):
                        chunk = event_data["chunk"]
                        if chunk.get("is_waiting_human"):
                            await manager.send_message(session_id, {
                                "type": "hitl_waiting",
                                "data": {
                                    "question": chunk.get("hitl_question", "승인해주세요"),
                                    "plan": chunk.get("plan", []),
                                    "current_step": chunk.get("current_step", 0)
                                },
                                "session_id": session_id
                            })

                # 최종 결과 조회
                final_state = await graph.aget_state(config)

                if final_state.values:
                    final_result = final_state.values.get("final_result", "")
                    messages = final_state.values.get("messages", [])

                    await manager.send_message(session_id, {
                        "type": "final_result",
                        "data": {
                            "result": final_result,
                            "message_count": len(messages)
                        },
                        "session_id": session_id
                    })

                # 완료 알림
                await manager.send_message(session_id, {
                    "type": "execution_completed",
                    "data": {"message": "처리 완료"},
                    "session_id": session_id
                })

            except Exception as e:
                print(f"[WebSocket] Error during execution: {e}")
                import traceback
                traceback.print_exc()

                await manager.send_message(session_id, {
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "message": "처리 중 오류가 발생했습니다"
                    },
                    "session_id": session_id
                })

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: {session_id}")
        manager.disconnect(session_id)

    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        import traceback
        traceback.print_exc()

        try:
            await manager.send_message(session_id, {
                "type": "error",
                "data": {"error": str(e)},
                "session_id": session_id
            })
        except:
            pass

        manager.disconnect(session_id)

    finally:
        # 연결 정리
        manager.disconnect(session_id)
