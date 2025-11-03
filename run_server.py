"""서버 실행 스크립트

Windows psycopg 호환성을 위한 이벤트 루프 설정 포함
"""
import sys
import asyncio

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # reload는 event loop 설정을 무효화할 수 있음
    )
