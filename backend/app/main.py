"""
SLAYERS FastAPI application entry point.

CORS strategy:
  - Local dev: localhost:3000 always allowed
  - If FRONTEND_URL is set: those origins are explicitly allowed
  - All *.vercel.app previews are covered by allow_origin_regex
  - No wildcard '*' in production when FRONTEND_URL is provided
"""
from __future__ import annotations

import os
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import engine, Base
from app.core.logging import setup_logging
from app.api.router import api_router

# ── Bootstrap ─────────────────────────────────────────────────────────────────
setup_logging()
Base.metadata.create_all(bind=engine)

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "SLAYERS — AI-powered visual research and asset sourcing "
        "for video creators and editors."
    ),
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_always_allowed = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
]

_explicit_origins = list(_always_allowed)
if settings.FRONTEND_URL:
    for raw in settings.FRONTEND_URL.split(","):
        url = raw.strip().rstrip("/")
        if url and url not in _explicit_origins:
            _explicit_origins.append(url)

# Allow all vercel preview deployments via regex
_allow_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_explicit_origins,
    allow_origin_regex=_allow_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Global exception handlers ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    logging.getLogger("slayers.app").error(
        "Unhandled exception on %s %s: %s", request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred.", "type": type(exc).__name__},
    )

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_PREFIX)
# Mount health at root too so Render/Railway health checks work without prefix
from app.api.health import router as health_router  # noqa: E402
app.include_router(health_router)


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", str(settings.PORT)))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
