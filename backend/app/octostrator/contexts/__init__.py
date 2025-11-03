"""Runtime Context 관리

불변 런타임 정보 (user_id, session_id, db_conn 등)
"""
from backend.app.octostrator.contexts.app_context import AppContext

__all__ = ["AppContext"]
