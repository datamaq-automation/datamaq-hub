"""FastAPI Application factory and server bootstrapping."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.adapters.gateways.api_cache_gateway import init_db
from src.adapters.gateways.sql_designacion_docente_gateway import init_horarios_db
from src.adapters.presenters.error_presenter import ErrorPresenter
from src.domain.calendar.exceptions import CalendarDomainException
from src.domain.contacts.exceptions import ContactsDomainException
from src.domain.horarios_docencia.exceptions import (
    HorariosDocenciaDomainException,
)
from src.domain.leads.exceptions import LeadException
from src.domain.liquidacion.exceptions import LiquidacionDomainException
from src.domain.mail.exceptions import MailDomainException
from src.domain.recibos.exceptions import DomainException
from src.infrastructure.fastapi.routes.analytics_routes import (
    router as analytics_router,
)
from src.infrastructure.fastapi.routes.calendar_routes import (
    router as calendar_router,
)
from src.infrastructure.fastapi.routes.contacts_routes import (
    router as contacts_router,
)
from src.infrastructure.fastapi.routes.health_routes import router as health_router
from src.infrastructure.fastapi.routes.horarios_docencia_routes import (
    router as horarios_docencia_router,
)
from src.infrastructure.fastapi.routes.leads_routes import (
    router as leads_router,
)
from src.infrastructure.fastapi.routes.mail_routes import router as mail_router
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
        """Inicializa los schemas de BD (caché y horarios) al arrancar el servidor."""
        init_db(settings.database_url)
        init_horarios_db(settings.database_url)
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

    @app.exception_handler(HorariosDocenciaDomainException)
    async def horarios_docencia_exception_handler(
        _: Request, exc: HorariosDocenciaDomainException
    ) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(MailDomainException)
    async def mail_exception_handler(
        _: Request, exc: MailDomainException
    ) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(ContactsDomainException)
    async def contacts_exception_handler(
        _: Request, exc: ContactsDomainException
    ) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(CalendarDomainException)
    async def calendar_exception_handler(
        _: Request, exc: CalendarDomainException
    ) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(LeadException)
    async def lead_exception_handler(_: Request, exc: LeadException) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_domain_error(exc)
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    # Unified framework exception handlers (Standardizing all error shapes to {"success": false, "error": {...}})
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first_msg = (
            errors[0]["msg"] if errors else "Error de validación en la solicitud"
        )
        payload, status_code = ErrorPresenter.format_generic_error(
            message=first_msg,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"errors": errors},
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code_map = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
        }
        code_name = code_map.get(exc.status_code, "HTTP_ERROR")
        msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        payload, status_code = ErrorPresenter.format_generic_error(
            message=msg,
            code=code_name,
            status_code=exc.status_code,
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        payload, status_code = ErrorPresenter.format_generic_error(
            message=f"Error interno del servidor: {exc}",
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    # Mount API routers under prefix /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(receipt_router, prefix="/api/v1")
    app.include_router(simulation_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(horarios_docencia_router, prefix="/api/v1")
    app.include_router(mail_router, prefix="/api/v1")
    app.include_router(contacts_router, prefix="/api/v1")
    app.include_router(calendar_router, prefix="/api/v1")
    app.include_router(leads_router)

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
