"""Domain services for decoding and sanitizing email headers and content."""

import re
from email.header import decode_header, make_header


class MailDecoderService:
    """Pure domain service for parsing and sanitizing MIME headers and text bodies."""

    @staticmethod
    def decode_header_str(raw_header: str | None) -> str:
        """Decodes RFC 2047 encoded email headers to clean Unicode string."""
        if not raw_header:
            return ""
        try:
            return str(make_header(decode_header(raw_header))).strip()
        except (LookupError, ValueError, TypeError, UnicodeDecodeError):
            return str(raw_header).strip()

    @staticmethod
    def clean_email_list(raw_header: str | None) -> list[str]:
        """Parses a comma-separated email header into clean email list."""
        if not raw_header:
            return []
        decoded = MailDecoderService.decode_header_str(raw_header)
        parts = [p.strip() for p in decoded.split(",") if p.strip()]
        return parts

    @staticmethod
    def sanitize_text(text: str | None) -> str:
        """Sanitizes text content removing null bytes and trailing whitespace."""
        if not text:
            return ""
        # Remove null bytes
        cleaned = text.replace("\x00", "")
        # Normalize multiple trailing line breaks
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
