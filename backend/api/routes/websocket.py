"""WebSocket Routes"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json

router = APIRouter()


class ConnectionManager:
    """WebSocket Connection Manager"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """새 연결 수락"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"[WS] Connected: {session_id}")

    def disconnect(self, session_id: str):
        """연결 해제"""
        self.active_connections.pop(session_id, None)
        print(f"[WS] Disconnected: {session_id}")

    async def send_update(self, session_id: str, message: dict):
        """특정 세션에 메시지 전송"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"[WS] Send error: {e}")
                self.disconnect(session_id)

    async def broadcast(self, message: dict):
        """모든 연결에 메시지 전송"""
        for session_id in list(self.active_connections.keys()):
            await self.send_update(session_id, message)


# 전역 ConnectionManager 인스턴스
manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 엔드포인트

    클라이언트와 실시간 통신:
    - 서버 → 클라이언트: todo_update, result, error, complete
    - 클라이언트 → 서버: stop, resume, input
    """
    await manager.connect(session_id, websocket)

    try:
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "ping":
                    # 핑퐁 (연결 유지)
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "stop":
                    # Agent 중지 요청
                    # TODO: Agent 중지 로직
                    await websocket.send_json({
                        "type": "status",
                        "data": {"status": "stopped"},
                    })

                elif msg_type == "resume":
                    # Agent 재개 요청
                    # TODO: Agent 재개 로직
                    await websocket.send_json({
                        "type": "status",
                        "data": {"status": "resumed"},
                    })

                elif msg_type == "input":
                    # HITL 사용자 입력
                    # TODO: 사용자 입력 처리
                    user_input = message.get("data", {}).get("input")
                    await websocket.send_json({
                        "type": "input_received",
                        "data": {"input": user_input},
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Invalid JSON"},
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
