"""Tests unitarios del adaptador StandardLogger de infraestructura."""

import logging

from src.infrastructure.logging.standard_logger import StandardLogger


class _ListHandler(logging.Handler):
    """Handler en memoria que acumula los LogRecord emitidos."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_standard_logger_delega_en_logging_get_logger() -> None:
    """SL-1: StandardLogger emite registros al logger stdlib del mismo nombre."""
    name = "test.standard_logger.unit"
    handler = _ListHandler()

    stdlib_logger = logging.getLogger(name)
    stdlib_logger.setLevel(logging.DEBUG)
    stdlib_logger.handlers.clear()
    stdlib_logger.addHandler(handler)

    try:
        logger = StandardLogger(name)
        logger.info("mensaje %s", "info")
        logger.error("mensaje %s", "error")

        assert len(handler.records) == 2
        assert handler.records[0].getMessage() == "mensaje info"
        assert handler.records[0].levelno == logging.INFO
        assert handler.records[1].getMessage() == "mensaje error"
        assert handler.records[1].levelno == logging.ERROR
    finally:
        stdlib_logger.handlers.clear()


def test_standard_logger_es_no_op_si_handler_sin_captura() -> None:
    """SL-1: las llamadas no levantan excepción aun sin handler explícito."""
    logger = StandardLogger("test.standard_logger.silent")
    logger.debug("debug")
    logger.warning("warning")
