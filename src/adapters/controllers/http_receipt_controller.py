"""HTTP controller for receipt parsing."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.adapters.controllers.dependencies import get_parse_receipt_use_case
from src.adapters.presenters.receipt_presenter import ReceiptPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.use_cases.parse_receipt import ParseReceiptUseCase

router = APIRouter(prefix="/recibos", tags=["Recibos"])


@router.post(
    "/parse",
    response_model=APIResponseDTO[ReceiptResponseDTO],
    summary="Parse salary receipt PDF",
    description=(
        "Upload a salary receipt in PDF format (e.g. DGCyE PBA or standard salary receipt) "
        "and receive strongly-typed extracted structured data."
    ),
    responses={
        200: {"description": "Receipt successfully parsed and validated"},
        400: {"description": "Invalid file format or unreadable PDF"},
        422: {"description": "Document failed domain schema validation"},
    },
)
async def parse_receipt(
    file: Annotated[UploadFile, File(description="PDF salary receipt file")],
    use_case: Annotated[ParseReceiptUseCase, Depends(get_parse_receipt_use_case)],
) -> APIResponseDTO[ReceiptResponseDTO]:
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

    # Execute application use case
    receipt_dto = use_case.execute_bytes(content, filename=filename)

    # Present formatted output
    return ReceiptPresenter.present(receipt_dto)
