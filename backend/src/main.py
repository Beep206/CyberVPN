import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.presentation.api.v1.router import api_router
from src.presentation.middleware.auth import AuthMiddleware
from src.presentation.middleware.logging import LoggingMiddleware

logger = logging.getLogger("cybervpn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("CyberVPN Backend starting up...")
    try:
        from src.infrastructure.database.session import check_db_connection
        db_ok = await check_db_connection()
        logger.info(f"Database connection: {'OK' if db_ok else 'FAILED'}")
    except Exception as e:
        logger.warning(f"Database check skipped: {e}")

    try:
        from src.infrastructure.cache.redis_client import check_redis_connection
        redis_ok, _ = await check_redis_connection()
        logger.info(f"Redis connection: {'OK' if redis_ok else 'FAILED'}")
    except Exception as e:
        logger.warning(f"Redis check skipped: {e}")

    yield

    # Shutdown
    logger.info("CyberVPN Backend shutting down...")
    try:
        from src.infrastructure.remnawave.client import remnawave_client
        await remnawave_client.close()
    except Exception:
        pass

    try:
        from src.infrastructure.cache.redis_client import close_redis_pool
        await close_redis_pool()
    except Exception:
        pass

    from src.infrastructure.messaging.websocket_manager import ws_manager
    logger.info(f"Closed {ws_manager.active_connections} WebSocket connections")


app = FastAPI(
    title="CyberVPN Backend API",
    version="0.1.0",
    description="Backend API for CyberVPN admin dashboard",
    lifespan=lifespan,
)

# Middleware (order matters - last added = first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggingMiddleware)

# Exception handlers
from src.presentation.exception_handlers import validation_exception_handler

app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routes
app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "cybervpn-backend"}
