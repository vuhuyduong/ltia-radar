"""
LTIA Radar Backend — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alert_rules, articles, crawler, dashboard, keywords, sources
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
    # Startup
    logger.info("🚀 LTIA Radar Backend starting...")
    await MongoDB.connect()
    start_scheduler()
    logger.info("✅ LTIA Radar Backend ready")

    yield

    # Shutdown
    logger.info("🛑 LTIA Radar Backend shutting down...")
    stop_scheduler()
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


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LTIA Radar Backend",
        "version": "1.0.0",
    }
