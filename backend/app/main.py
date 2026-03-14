"""
DiaIntel — FastAPI Application Entry Point

Main application with:
- CORS middleware
- Router registration
- WebSocket endpoint
- Startup/shutdown events
- Health check endpoint
"""

import os
import time
import logging
from contextlib import asynccontextmanager

# CRITICAL: Set before any HuggingFace import
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from app.api.routes import drugs, compare, analyze, graph, dashboard, misinfo
from app.api.websocket import router as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("diaintel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    logger.info("=" * 60)
    logger.info("DiaIntel — Starting up...")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    logger.info(f"Model cache: {settings.MODEL_CACHE_DIR}")
    logger.info(f"Data directory: {settings.PUSHSHIFT_DATA_DIR}")

    # Initialize scheduler for data ingestion (Step 2)
    try:
        from app.ingestion.scheduler import start_scheduler
        start_scheduler()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.warning(f"Scheduler not yet implemented: {e}")

    yield

    # Shutdown
    logger.info("DiaIntel — Shutting down...")
    try:
        from app.ingestion.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title="DiaIntel",
    description="Pharmacovigilance Intelligence Platform for Type 2 Diabetes",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # ms
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response


# Register routers
app.include_router(drugs.router, prefix="/api/v1", tags=["Drugs"])
app.include_router(compare.router, prefix="/api/v1", tags=["Compare"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analyze"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(misinfo.router, prefix="/api/v1", tags=["Misinformation"])
app.include_router(ws_router, tags=["WebSocket"])


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "diaintel-backend",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "DiaIntel API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
