"""
Lumi DICOM — FastAPI Server
Copyright © 2026 Lumi DICOM. All rights reserved.

Creates and configures the Lumi DICOM FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from lumi_dicom.api.inbound import router as inbound_router
from lumi_dicom.api.routes import router
from lumi_dicom.dashboard import create_dashboard_router
from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.docs import create_docs_router

logger = logging.getLogger("lumi-dicom")


def get_db_dependency():
    """Return the FastAPI dependency from routes.py.

    The actual dependency is defined in routes.get_db which reads
    DatabaseManager from app.state.
    """
    from lumi_dicom.api.routes import get_db
    return get_db


def create_app(db_manager: DatabaseManager, config: dict) -> FastAPI:
    """Create and configure Lumi DICOM FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Lumi DICOM API starting up")
        yield
        logger.info("Lumi DICOM API shutting down")

    app = FastAPI(
        title="Lumi DICOM Orchestrator",
        description="DICOM Modality Worklist orchestrator for radiology workflows",
        version=config.get("version", "0.1.0"),
        lifespan=lifespan,
        docs_url=None,  # Disable built-in Swagger UI — use custom /docs instead
        redoc_url=None,
    )

    # Store db_manager in app.state for dependency injection
    app.state.db_manager = db_manager

    # Store API keys in app.state for auth dependency
    api_cfg = config.get("api", {})
    app.state.api_keys = api_cfg.get("api_keys", ["lumi-dicom-dev-key"])

    # CORS
    cors_origins = api_cfg.get("cors_origins", ["http://localhost:3000"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include existing routes (worklist, modalities, audit, health)
    app.include_router(router)

    # Include inbound routes (HL7, FHIR, inbound health)
    app.include_router(inbound_router)

    # Auth middleware: enforce API key on all /api/v1/* paths
    # (but NOT /health or / dashboard)
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class LumiAPIKeyMiddleware(BaseHTTPMiddleware):
        """Lumi DICOM API key middleware."""

        async def dispatch(self, request: Request, call_next):
            if request.url.path.startswith("/api/v1/"):
                api_keys = getattr(request.app.state, "api_keys", [])
                x_api_key = request.headers.get("X-API-Key")
                if not x_api_key:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Missing X-API-Key header"},
                        headers={"WWW-Authenticate": "ApiKey"},
                    )
                if x_api_key not in api_keys:
                    logger.warning("Lumi DICOM: invalid API key attempt")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid API key"},
                        headers={"WWW-Authenticate": "ApiKey"},
                    )
            return await call_next(request)

    app.add_middleware(LumiAPIKeyMiddleware)

    # Dashboard
    dashboard_router = create_dashboard_router()
    app.include_router(dashboard_router)

    # Documentation
    docs_router = create_docs_router()
    app.include_router(docs_router)

    return app
