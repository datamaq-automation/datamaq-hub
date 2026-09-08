"""Domain ports and DTOs for salary receipts domain."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.domain.recibos.entities import DesignacionNoLiquidada, ReciboSueldo


@dataclass
class PageData:
    """Extracted text and dimensions for a single PDF page."""

    page_number: int
    width: float
    height: float
    text: str
    lines: list[str]


@dataclass
class ExtractedPDF:
    """Extracted PDF payload."""

    total_pages: int
    pages: list[PageData]
    raw_full_text: str
    metadata: dict[str, Any]


class PDFExtractorPort(ABC):
    """Abstract port for PDF extraction."""

    @abstractmethod
    def extract_from_bytes(self, pdf_bytes: bytes) -> ExtractedPDF: ...

    @abstractmethod
    def extract_from_path(self, file_path: str) -> ExtractedPDF: ...


class ReceiptParserPort(ABC):
    """Abstract port for receipt parsers."""

    @abstractmethod
    def can_handle(self, extracted_pdf: ExtractedPDF) -> bool: ...

    @abstractmethod
    def parse(self, extracted_pdf: ExtractedPDF) -> ReciboSueldo: ...


class ReceiptParserRegistryPort(ABC):
    """Abstract port for resolving receipt parsers."""

    @abstractmethod
    def get_parser(self, extracted_pdf: ExtractedPDF) -> ReceiptParserPort: ...


class ReciboRepositoryPort(ABC):
    """Abstract port for persisting and querying salary receipts."""

    @abstractmethod
    def guardar(self, recibo: ReciboSueldo) -> ReciboSueldo: ...

    @abstractmethod
    def obtener_por_id(self, id_recibo: str) -> ReciboSueldo | None: ...

    @abstractmethod
    def listar(
        self,
        cuit: str | None = None,
        mes_pago: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReciboSueldo]: ...

    @abstractmethod
    def eliminar(self, id_recibo: str) -> bool: ...

    @abstractmethod
    def obtener_por_hash(self, pdf_hash: str) -> ReciboSueldo | None: ...


class SeguimientoNoLiquidadosRepositoryPort(ABC):
    """Puerto para persistir y auditar designaciones docentes activas no liquidadas."""

    @abstractmethod
    def guardar(self, item: DesignacionNoLiquidada) -> DesignacionNoLiquidada: ...

    @abstractmethod
    def guardar_batch(self, items: list[DesignacionNoLiquidada]) -> None: ...

    @abstractmethod
    def obtener_por_recibo(self, id_recibo: str) -> list[DesignacionNoLiquidada]: ...

    @abstractmethod
    def listar(
        self,
        docente_cuit: str | None = None,
        solo_pendientes: bool = False,
        solo_alertas: bool = False,
    ) -> list[DesignacionNoLiquidada]: ...

    @abstractmethod
    def obtener_ultimas_pendientes(
        self, docente_cuit: str
    ) -> list[DesignacionNoLiquidada]: ...

    @abstractmethod
    def resolver_designaciones(
        self, docente_cuit: str, ids_designacion: list[str], id_recibo_resolucion: str
    ) -> None: ...
