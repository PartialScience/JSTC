"""
Health-check router.
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok"}
