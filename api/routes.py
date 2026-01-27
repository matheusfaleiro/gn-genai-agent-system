"""API route aggregation with version prefixes.

This module combines all versioned API routers into a single router
that can be included in the main application. New API versions can
be added here with their respective prefixes.
"""

from fastapi import APIRouter

from api.v1 import endpoints as v1_endpoints

router = APIRouter()

# Include V1 endpoints under /v1 prefix
router.include_router(v1_endpoints.router, prefix="/v1")
