"""Adaptador de infraestructura que envuelve el logging estándar de Python."""

import logging

from src.domain.common.ports import LoggerPort


class StandardLogger(LoggerPort):
    """Implementa :class:`LoggerPort` delegando en ``logging.getLogger(name)``.

    Vive en la capa de infraestructura (única capa autorizada a conocer la
    librería concreta ``logging``), y se inyecta en gateways/use cases vía DIP.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, message: str, *args: object) -> None:
        self._logger.debug(message, *args)

    def info(self, message: str, *args: object) -> None:
        self._logger.info(message, *args)

    def warning(self, message: str, *args: object) -> None:
        self._logger.warning(message, *args)

    def error(self, message: str, *args: object) -> None:
        self._logger.error(message, *args)

    def exception(self, message: str, *args: object) -> None:
        self._logger.exception(message, *args)
