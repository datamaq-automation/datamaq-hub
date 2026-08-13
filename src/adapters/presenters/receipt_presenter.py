"""Presenter for formatting receipt output responses."""

from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.receipt_dto import ReceiptResponseDTO


class ReceiptPresenter:
    """Formats Receipt DTOs into standardized API envelopes."""

    @staticmethod
    def present(dto: ReceiptResponseDTO) -> APIResponseDTO[ReceiptResponseDTO]:
        """Wrap receipt DTO into API response envelope."""
        return APIResponseDTO(
            success=True,
            data=dto,
        )
