"""
SEO Analyzer — FastAPI Backend
================================
Main application entry point.

Run locally:
    uvicorn main:app --reload --port 8000

Production:
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from routers.analysis import router as analysis_router
from routers.billing import router as billing_router
from routers.admin import router as admin_router
from routers.writer import router as writer_router
from routers.compare import router as compare_router
from routers.audit import router as audit_router
from routers.keywords import router as keywords_router
from routers.export import router as export_router
from routers.editor import router as editor_router
from routers.aeo import router as aeo_router
from config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    print(f"✅ SEO Analyzer API starting — env: {settings.app_env}")
    print(f"✅ Allowed origins: {settings.origins_list}")
    yield
    print("👋 SEO Analyzer API shutting down")


app = FastAPI(
    title="SEO Analyzer API",
    description="AI-powered SEO analysis and optimization backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if True else None,   # disable in production if needed
    redoc_url="/redoc",
)

# ─── Middleware ────────────────────────────────────────────────────────────────

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(analysis_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(writer_router)
app.include_router(compare_router)
app.include_router(audit_router)
app.include_router(keywords_router)
app.include_router(export_router)
app.include_router(editor_router)
app.include_router(aeo_router)

# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "seo-analyzer-api",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {
        "message": "SEO Analyzer API",
        "docs": "/docs",
        "health": "/health"
    }
