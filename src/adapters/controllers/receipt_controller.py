"""Pure transport-agnostic controller for receipt parsing."""

from src.adapters.presenters.receipt_presenter import ReceiptPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.use_cases.parse_receipt import ParseReceiptUseCase


class ReceiptController:
    """Handles receipt parsing operations independently of web transport."""

    def __init__(self, parse_use_case: ParseReceiptUseCase) -> None:
        self._parse_use_case = parse_use_case

    def parse_bytes(
        self, content: bytes, filename: str = "receipt.pdf"
    ) -> APIResponseDTO[ReceiptResponseDTO]:
        """Execute receipt parsing on byte stream and present envelope."""
        receipt_dto = self._parse_use_case.execute_bytes(content, filename=filename)
        return ReceiptPresenter.present(receipt_dto)
