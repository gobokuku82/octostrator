"""Common response schemas"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """기본 응답 모델"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseResponse):
    """에러 응답 모델"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseResponse):
    """성공 응답 모델"""
    success: bool = True


class PaginatedResponse(BaseResponse):
    """페이지네이션 응답 모델"""
    success: bool = True
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool