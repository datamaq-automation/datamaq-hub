"""Use case for parsing salary receipt PDFs."""

from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.ports import (
    PDFExtractorPort,
    ReceiptParserRegistryPort,
    ReciboRepositoryPort,
)


class ParseReceiptUseCase:
    """Orchestrates PDF text extraction, parser detection, parsing, and DTO mapping."""

    def __init__(
        self,
        extractor: PDFExtractorPort,
        parser_registry: ReceiptParserRegistryPort,
        repository: ReciboRepositoryPort | None = None,
    ) -> None:
        self._extractor = extractor
        self._parser_registry = parser_registry
        self._repository = repository

    def execute_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "receipt.pdf",
        persistir: bool = False,
    ) -> ReceiptResponseDTO:
        """Parse raw PDF byte stream."""
        extracted_pdf = self._extractor.extract_from_bytes(pdf_bytes)
        parser = self._parser_registry.get_parser(extracted_pdf)
        receipt_entity = parser.parse(extracted_pdf)
        receipt_entity.metadata["filename"] = filename

        if persistir and self._repository is not None:
            receipt_entity = self._repository.guardar(receipt_entity)

        return ReceiptMapper.to_dto(receipt_entity)

    def execute_path(
        self,
        file_path: str,
        persistir: bool = False,
    ) -> ReceiptResponseDTO:
        """Parse PDF from filesystem path."""
        extracted_pdf = self._extractor.extract_from_path(file_path)
        parser = self._parser_registry.get_parser(extracted_pdf)
        receipt_entity = parser.parse(extracted_pdf)
        receipt_entity.metadata["filename"] = file_path

        if persistir and self._repository is not None:
            receipt_entity = self._repository.guardar(receipt_entity)

        return ReceiptMapper.to_dto(receipt_entity)
