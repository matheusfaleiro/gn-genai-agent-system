"""FastAPI application entry point.

This module creates the FastAPI application and includes all API routes.
The health check endpoint is defined here as it's version-independent.
"""

import config  # noqa: F401 - Load .env before other imports

from fastapi import FastAPI

from api.routes import router as api_router

app = FastAPI(
    title="Ticketing API",
    description="A mock ticketing API for GenAI agent integration",
    version="1.0.0",
)


@app.get("/")
async def health_check():
    """Check if the API is running.

    Returns:
        A dictionary with status and service name.
    """
    return {"status": "healthy", "service": "ticketing-api"}


# Include all API routes
app.include_router(api_router)
