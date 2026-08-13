"""PDF Extractor service using pdfplumber."""

import io
from dataclasses import dataclass

import pdfplumber


@dataclass
class PageData:
    """Extracted content and metadata for a single PDF page."""

    page_number: int
    width: float
    height: float
    text: str
    lines: list[str]


@dataclass
class ExtractedPDF:
    """Complete extracted document payload."""

    total_pages: int
    pages: list[PageData]
    raw_full_text: str
    metadata: dict


class PDFExtractorService:
    """Service to extract text, lines, and layout metadata from PDF bytes."""

    @staticmethod
    def extract_from_bytes(pdf_bytes: bytes) -> ExtractedPDF:
        """Extract text and metadata from PDF in-memory bytes."""
        if not pdf_bytes or len(pdf_bytes) < 10:
            raise ValueError("Invalid PDF: File is empty or too short.")

        if not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError(
                "Invalid PDF format: File header is missing %PDF- magic signature."
            )

        pages_data: list[PageData] = []
        full_text_list: list[str] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pdf_meta = pdf.metadata or {}
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text(layout=False) or ""
                lines = [line.strip() for line in page_text.split("\n") if line.strip()]
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

        full_text = "\n".join(full_text_list)
        return ExtractedPDF(
            total_pages=len(pages_data),
            pages=pages_data,
            raw_full_text=full_text,
            metadata=pdf_meta,
        )

    @classmethod
    def extract_from_path(cls, file_path: str) -> ExtractedPDF:
        """Extract text and metadata from a local PDF file path."""
        with open(file_path, "rb") as f:
            return cls.extract_from_bytes(f.read())
