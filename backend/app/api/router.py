from fastapi import APIRouter
from app.api.projects import router as projects_router
from app.api.assets import router as assets_router
from app.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(assets_router)
