"""FastAPI application entry point — JWT Auth Microservice."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import Base, engine
from src.routes import router as auth_router

logger = logging.getLogger("test_battle_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create database tables on startup."""
    # Warn if using the default insecure secret
    if settings.JWT_SECRET == "super-secret-key-change-me":
        logger.warning(
            "JWT_SECRET is set to the default insecure value! "
            "Change it before deploying to production."
        )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created. Application ready.")
    yield

    # Shutdown: dispose of the engine connection pool
    await engine.dispose()


app = FastAPI(
    title="JWT Auth Microservice",
    description=(
        "A standalone FastAPI microservice with JWT-based authentication. "
        "Five endpoints covering the full auth lifecycle: registration, login, "
        "profile retrieval, token refresh, and token verification."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth_router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
)
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "ok"}
