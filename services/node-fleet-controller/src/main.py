from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.api.router import router as api_router
from src.application.services.workflow_engine import WorkflowEngine
from src.config import Settings, get_settings
from src.infra.database.session import dispose_database, initialize_database
from src.infra.execution.opentofu_executor import OpenTofuExecutor
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter
from src.infra.secrets.openbao_manager import OpenBaoBootstrapManager
from src.observability import setup_sentry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    setup_sentry(settings)
    await initialize_database(settings)
    try:
        yield
    finally:
        await app.state.nats_adapter.close()
        await dispose_database(settings)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    logging.basicConfig(level=getattr(logging, runtime_settings.log_level.upper(), logging.INFO))
    app = FastAPI(
        title="CyberVPN Node Fleet Controller",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.nats_adapter = NatsJetStreamAdapter(runtime_settings)
    app.state.workflow_engine = WorkflowEngine()
    app.state.opentofu_executor = OpenTofuExecutor(runtime_settings)
    app.state.openbao_manager = OpenBaoBootstrapManager(runtime_settings)
    app.include_router(api_router)
    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
