"""Puertos del dominio de tarjetas de crédito."""

from abc import ABC, abstractmethod
from datetime import date
from typing import BinaryIO

from src.domain.tarjetas.entities import ResumenTarjeta


class TarjetaCreditoParserPort(ABC):
    """Contrato para parsear PDFs de resúmenes de tarjetas de crédito."""

    @abstractmethod
    def parsear(self, archivo: BinaryIO) -> ResumenTarjeta:
        """Parsea un PDF y devuelve el resumen de tarjeta extraído."""


class TarjetaRepositoryPort(ABC):
    """Contrato para persistir y consultar resúmenes de tarjetas de crédito."""

    @abstractmethod
    def guardar(self, resumen: ResumenTarjeta) -> None:
        """Persiste un resumen de tarjeta."""

    @abstractmethod
    def obtener_por_id(self, id_resumen: str) -> ResumenTarjeta | None:
        """Recupera un resumen por su identificador."""

    @abstractmethod
    def obtener_resumenes_vencimiento_cercano(
        self, fecha_limite: date
    ) -> list[ResumenTarjeta]:
        """Lista resúmenes cuyo vencimiento es igual o posterior a la fecha límite."""
