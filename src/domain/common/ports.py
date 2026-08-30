"""Puertos comunes del dominio: abstracciones puras (Protocol) sin dependencias externas."""

from typing import Protocol


class LoggerPort(Protocol):
    """Contrato de logging puro para Clean Architecture.

    Las capas internas (Dominio, Aplicación, Adaptadores) reciben una instancia
    de este Protocol por Inyección de Dependencias, sin acoplarse a la librería
    concreta ``logging`` de la stdlib.
    """

    def debug(self, message: str, *args: object) -> None:
        """Registra un mensaje de depuración (nivel DEBUG)."""
        ...

    def info(self, message: str, *args: object) -> None:
        """Registra un mensaje informativo (nivel INFO)."""
        ...

    def warning(self, message: str, *args: object) -> None:
        """Registra una advertencia (nivel WARNING)."""
        ...

    def error(self, message: str, *args: object) -> None:
        """Registra un error (nivel ERROR)."""
        ...

    def exception(self, message: str, *args: object) -> None:
        """Registra una excepción con traceback (nivel ERROR)."""
        ...


class NullLogger:
    """Implementación no-op de :class:`LoggerPort` usada como fallback seguro.

    Permite instanciar gateways y use cases sin logger explícito (tests unitarios,
    composición mínima) sin efectos secundarios de registro.
    """

    def debug(self, message: str, *args: object) -> None:
        """No-op de depuración."""

    def info(self, message: str, *args: object) -> None:
        """No-op informativo."""

    def warning(self, message: str, *args: object) -> None:
        """No-op de advertencia."""

    def error(self, message: str, *args: object) -> None:
        """No-op de error."""

    def exception(self, message: str, *args: object) -> None:
        """No-op de excepción."""
