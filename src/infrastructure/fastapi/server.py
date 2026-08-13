"""FastAPI Application factory and server bootstrapping."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.adapters.controllers.http_health_controller import router as health_router
from src.adapters.controllers.http_receipt_controller import router as receipt_router
from src.adapters.presenters.error_presenter import ErrorPresenter
from src.domain.recibos.exceptions import DomainException
from src.infrastructure.pydantic.config import get_settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain exception handler
    @app.exception_handler(DomainException)
    async def domain_exception_handler(
        _: Request, exc: DomainException
    ) -> JSONResponse:
        return ErrorPresenter.format_domain_error(exc)

    # Mount API routers under prefix /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(receipt_router, prefix="/api/v1")

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
