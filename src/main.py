"""Main FastAPI application entrypoint."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router as api_router
from src.config import get_settings
from src.schemas.common import ErrorDetail, ErrorResponse
from src.services.base_parser import InvalidPDFError, ReceiptParsingError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ReceiptParsingError)
async def receipt_parsing_error_handler(
    _: Request, exc: ReceiptParsingError
) -> JSONResponse:
    """Handle domain parsing errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="RECEIPT_PARSING_ERROR",
                message=exc.message,
                details=exc.details,
            ),
        ).model_dump(),
    )


@app.exception_handler(InvalidPDFError)
async def invalid_pdf_error_handler(_: Request, exc: InvalidPDFError) -> JSONResponse:
    """Handle invalid PDF errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INVALID_PDF_ERROR",
                message=exc.message,
                details=exc.details,
            ),
        ).model_dump(),
    )


# Include API routes
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to docs."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
