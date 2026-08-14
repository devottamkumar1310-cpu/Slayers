from fastapi import APIRouter
from app.core.config import settings
from app.core.db import check_database

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    db_ok = check_database()
    return {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_provider": settings.AI_PROVIDER,
        "database": "connected" if db_ok else "unreachable",
        "providers_configured": {
            "pexels": bool(settings.PEXELS_API_KEY),
            "unsplash": bool(settings.UNSPLASH_ACCESS_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "wikimedia": True,
            "web_brand": True,
        },
    }
