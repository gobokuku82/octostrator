"""API Routes Package"""
from .agent import router as agent_router
from .websocket import router as websocket_router
from .health import router as health_router

__all__ = ["agent_router", "websocket_router", "health_router"]
