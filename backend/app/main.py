import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import engine, Base
from app.core.logging import setup_logging
from app.api.router import api_router

setup_logging()

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# CORS configuration
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.FRONTEND_URL:
    for url in settings.FRONTEND_URL.split(","):
        cleaned = url.strip()
        if cleaned and cleaned not in allowed_origins:
            allowed_origins.append(cleaned)

# If no specific FRONTEND_URL provided, allow all origins
allow_all = len(allowed_origins) <= 2 and not settings.FRONTEND_URL

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app" if not allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(api_router) # also at root for convenience (e.g. GET /health)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
