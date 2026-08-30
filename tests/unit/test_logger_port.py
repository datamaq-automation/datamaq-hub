"""Tests unitarios del contrato de logging puro del dominio (LoggerPort y NullLogger)."""

from src.domain.common.ports import LoggerPort, NullLogger


def test_null_logger_implementa_logger_port_estructuralmente() -> None:
    """LP-2: NullLogger satisface el Protocol LoggerPort con sus 5 métodos."""
    null_logger = NullLogger()
    assert hasattr(null_logger, "debug")
    assert hasattr(null_logger, "info")
    assert hasattr(null_logger, "warning")
    assert hasattr(null_logger, "error")
    assert hasattr(null_logger, "exception")


def test_null_logger_es_no_op_silencioso() -> None:
    """LP-1: las llamadas a todos los métodos de NullLogger no levantan excepción."""
    null_logger = NullLogger()
    null_logger.debug("debug %s", "arg")
    null_logger.info("info %s", "arg")
    null_logger.warning("warning %s", "arg")
    null_logger.error("error %s", "arg")
    null_logger.exception("exception %s", "arg")


def test_logger_port_es_protocol() -> None:
    """LP-2: LoggerPort es un Protocol tipado importable desde dominio."""
    assert isinstance(LoggerPort, type)
