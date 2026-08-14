"""Gateway adapter implementing PDFExtractorPort using pdfplumber."""

import io
from typing import Any

import pdfplumber

from src.domain.recibos.exceptions import InvalidPDFError
from src.domain.recibos.ports import ExtractedPDF, PageData, PDFExtractorPort


class PdfPlumberExtractorGateway(PDFExtractorPort):
    """PDF extraction gateway using pdfplumber."""

    def extract_from_bytes(self, pdf_bytes: bytes) -> ExtractedPDF:
        if not pdf_bytes or len(pdf_bytes) < 10:
            raise InvalidPDFError("PDF file is empty or too short.")

        if not pdf_bytes.startswith(b"%PDF-"):
            raise InvalidPDFError(
                "File is not a valid PDF document (missing %PDF- signature)."
            )

        pages_data: list[PageData] = []
        full_text_list: list[str] = []

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pdf_meta: dict[str, Any] = dict(pdf.metadata or {})
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text(layout=False) or ""
                    lines = [
                        line.strip() for line in page_text.split("\n") if line.strip()
                    ]
                    pages_data.append(
                        PageData(
                            page_number=i + 1,
                            width=float(page.width),
                            height=float(page.height),
                            text=page_text,
                            lines=lines,
                        )
                    )
                    full_text_list.append(page_text)
        except Exception as e:
            if isinstance(e, InvalidPDFError):
                raise
            raise InvalidPDFError(f"Failed to read and parse PDF stream: {e!s}") from e

        return ExtractedPDF(
            total_pages=len(pages_data),
            pages=pages_data,
            raw_full_text="\n".join(full_text_list),
            metadata=pdf_meta,
        )

    def extract_from_path(self, file_path: str) -> ExtractedPDF:
        try:
            with open(file_path, "rb") as f:
                return self.extract_from_bytes(f.read())
        except FileNotFoundError as e:
            raise InvalidPDFError(f"PDF file not found at path: '{file_path}'") from e
        except Exception as e:
            if isinstance(e, InvalidPDFError):
                raise
            raise InvalidPDFError(f"Error opening PDF file '{file_path}': {e!s}") from e
