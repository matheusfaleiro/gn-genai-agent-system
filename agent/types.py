"""Type definitions for the agent module."""

from __future__ import annotations

from typing import Any, TypedDict, Union


class SuccessResponse(TypedDict):
    """Response returned on successful API call."""

    success: bool  # Always True
    data: Any


class ErrorResponse(TypedDict):
    """Response returned on failed API call."""

    success: bool  # Always False
    status_code: int | None
    error: str


# Union type for all API responses
ApiResponse = Union[SuccessResponse, ErrorResponse]
