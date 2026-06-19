"""
LTIA Radar Backend — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    alert_rules,
    articles,
    crawler,
    dashboard,
    keywords,
    sources,
    llm_configs,
    general,
    llm_prompts,
)
from app.config import settings
from app.infrastructure.database.mongodb import MongoDB
from app.scheduler.jobs import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    import os
    port = os.environ.get("PORT", "8000")
    logger.info(f"🚀 LTIA Radar Backend starting on port {port}...")

    # Connect to MongoDB — non-fatal: app stays up even if connection is slow
    try:
        await MongoDB.connect()
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed at startup: {e}")
        logger.warning("⚠️  App will continue — retrying on first request")

    # Start scheduler — non-fatal: scheduler may fail if DB not ready yet
    try:
        await start_scheduler()
        logger.info("✅ Scheduler started")
    except Exception as e:
        logger.error(f"❌ Scheduler startup failed: {e}")
        logger.warning("⚠️  App will continue without scheduler")

    logger.info("✅ LTIA Radar Backend ready")

    yield

    # Shutdown
    logger.info("🛑 LTIA Radar Backend shutting down...")
    try:
        stop_scheduler()
    except Exception:
        pass
    await MongoDB.disconnect()



# Create FastAPI app
app = FastAPI(
    title="LTIA Radar — Early Warning System API",
    description=(
        "Hệ thống Radar Cảnh báo sớm & Quản trị khủng hoảng "
        "Sân bay Long Thành (LTIA Early Warning System)"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(sources.router)
app.include_router(keywords.router)
app.include_router(articles.router)
app.include_router(dashboard.router)
app.include_router(alert_rules.router)
app.include_router(crawler.router)
app.include_router(llm_configs.router)
app.include_router(general.router)
app.include_router(llm_prompts.router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LTIA Radar Backend",
        "version": "1.0.0",
    }
