"""FastAPI Application factory and server bootstrapping."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.adapters.gateways.api_cache_gateway import init_db
from src.adapters.presenters.error_presenter import ErrorPresenter
from src.domain.liquidacion.exceptions import LiquidacionDomainException
from src.domain.recibos.exceptions import DomainException
from src.infrastructure.fastapi.routes.health_routes import router as health_router
from src.infrastructure.fastapi.routes.receipt_routes import router as receipt_router
from src.infrastructure.fastapi.routes.simulation_routes import (
    router as simulation_router,
)
from src.infrastructure.pydantic.config import get_settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Inicializa el schema de caché en MySQL al arrancar el servidor."""
        init_db(settings.database_url)
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain exception handlers
    @app.exception_handler(DomainException)
    async def domain_exception_handler(
        _: Request, exc: DomainException
    ) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(LiquidacionDomainException)
    async def liquidacion_exception_handler(
        _: Request, exc: LiquidacionDomainException
    ) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    # Mount API routers under prefix /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(receipt_router, prefix="/api/v1")
    app.include_router(simulation_router, prefix="/api/v1")

    # Root redirect/info endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app
