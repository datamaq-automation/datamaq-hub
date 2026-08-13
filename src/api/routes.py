"""API route handlers for receipt parsing and health checking."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.dependencies import get_parser_factory, get_settings
from src.config import Settings
from src.schemas.common import APIResponse, HealthResponse
from src.schemas.recibo import ReciboSueldoResponse
from src.services.base_parser import ReceiptParsingError
from src.services.parser_factory import ReceiptParserFactory

router = APIRouter(prefix="/api/v1", tags=["Recibos"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns service availability and metadata status.",
)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Check API operational health."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        service=settings.app_name,
    )


@router.post(
    "/recibos/parse",
    response_model=APIResponse[ReciboSueldoResponse],
    summary="Parse salary receipt PDF",
    description=(
        "Upload a salary receipt in PDF format (e.g. DGCyE PBA or standard salary receipt) "
        "and receive strongly-typed extracted structured data including agent, employer, "
        "consolidated liquid summaries, multi-sequence liquidations, and concept breakdowns."
    ),
    responses={
        200: {"description": "Receipt successfully parsed and validated"},
        400: {"description": "Invalid file format or unreadable PDF"},
        422: {"description": "Document failed domain schema validation"},
    },
)
async def parse_receipt_pdf(
    file: Annotated[UploadFile, File(description="PDF salary receipt file")],
    factory: Annotated[ReceiptParserFactory, Depends(get_parser_factory)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> APIResponse[ReciboSueldoResponse]:
    """Parse uploaded salary receipt PDF into structured JSON."""
    filename = file.filename or "receipt.pdf"

    if not filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file must be a PDF document.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {e!s}",
        ) from e

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF file is empty.",
        )

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_bytes // (1024 * 1024)}MB.",
        )

    try:
        parsed_data = factory.parse_pdf_bytes(content, filename=filename)
        return APIResponse(success=True, data=parsed_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ReceiptParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while parsing the receipt: {e!s}",
        ) from e
