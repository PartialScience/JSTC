"""
Health router for JSTC API

This module contains health check and system status endpoints.
"""

from fastapi import APIRouter
from datetime import datetime

from ..models.common import HealthResponse
from ..core.config import get_settings

# Get settings
settings = get_settings()

# Create router instance
router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("", response_model=HealthResponse, summary="Health check")
async def health_check():
    """
    Check the health status of the API.
    
    Returns the current status, timestamp, and version information.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=settings.api.version
    )


@router.get("/ping", summary="Simple ping endpoint")
async def ping():
    """
    Simple ping endpoint for basic connectivity testing.
    """
    return {"message": "pong"}
