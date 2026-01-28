"""API authentication module.

This module provides API key authentication for securing endpoints.
"""

from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_HEADER_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


@lru_cache(maxsize=1)
def get_api_key() -> str | None:
    """Get the API key from environment, cached at first call."""
    return os.getenv("API_KEY")


def clear_api_key_cache() -> None:
    """Clear the API key cache. Useful for testing."""
    get_api_key.cache_clear()


async def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),  # noqa: UP045
) -> str:
    """Verify the API key from request header.

    Args:
        api_key: The API key from the X-API-Key header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: 500 if API_KEY environment variable is not configured.
        HTTPException: 401 if API key is missing or invalid.
    """
    expected_key = get_api_key()

    if not expected_key:
        logger.error("API_KEY environment variable is not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include 'X-API-Key' header.",
        )

    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key
