"""FastAPI dependency injection providers."""

from functools import lru_cache

from src.config import Settings, get_settings
from src.services.parser_factory import ReceiptParserFactory


@lru_cache
def get_parser_factory() -> ReceiptParserFactory:
    """Provide singleton instance of ReceiptParserFactory."""
    return ReceiptParserFactory()


__all__ = ["Settings", "get_parser_factory", "get_settings"]
