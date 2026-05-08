"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check if the service is running."""
    return {
        "status": "healthy",
        "service": "안전귀가Navi API"
    }
