"""Gateway parser de resúmenes de tarjetas de crédito (BBVA y BAPRO) con pdfplumber."""

import re
from datetime import date
from typing import BinaryIO

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.tarjetas.entities import ResumenTarjeta
from src.domain.tarjetas.exceptions import TarjetaParserException
from src.domain.tarjetas.ports import TarjetaCreditoParserPort

_MESES: dict[str, int] = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

_RE_FECHA_GUION = re.compile(r"^(\d{1,2})-([A-Za-z]{3})-(\d{2,4})$")
_RE_FECHA_ESPACIO = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2,4})$")
_RE_FECHA_PUNTO = re.compile(r"^(\d{2})\.(\d{2})\.(\d{2,4})$")


def _resolver_anio(anio: str) -> int:
    """Normaliza un año de dos o cuatro dígitos a su valor entero."""
    valor = int(anio)
    if valor < 100:
        return 2000 + valor
    return valor


def parse_fecha(texto: str) -> date:
    """Parsea una fecha en formato DD-Mmm-YY, DD Mmm YY o DD.MM.YY."""
    texto = texto.strip()
    try:
        m = _RE_FECHA_GUION.match(texto) or _RE_FECHA_ESPACIO.match(texto)
        if m:
            dia = int(m.group(1))
            mes = _MESES[m.group(2).lower()]
            return date(_resolver_anio(m.group(3)), mes, dia)
        m = _RE_FECHA_PUNTO.match(texto)
        if m:
            return date(
                _resolver_anio(m.group(3)),
                int(m.group(2)),
                int(m.group(1)),
            )
    except (KeyError, ValueError) as exc:
        raise TarjetaParserException(
            f"Formato de fecha no reconocido: {texto!r}"
        ) from exc
    raise TarjetaParserException(f"Formato de fecha no reconocido: {texto!r}")


def limpiar_monto(texto: str) -> float:
    """Convierte un importe formateado argentino (p.ej. '144.565,27') a float."""
    texto = texto.strip()
    if texto in {"-,--", "-", "", "--", ",", "._,--"}:
        return 0.0
    negativo = texto.startswith("-") or texto.endswith("-")
    texto = texto.replace("$", "").replace("-", "").strip()
    if texto in {"", ",", "--"}:
        return 0.0
    texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = float(texto)
    except ValueError as exc:
        raise TarjetaParserException(f"Importe no válido: {texto!r}") from exc
    return -valor if negativo else valor


class PDFTarjetaParserGateway(TarjetaCreditoParserPort):
    """Parser de resúmenes de tarjetas de crédito BBVA y BAPRO."""

    def __init__(self, logger: LoggerPort | None = None) -> None:
        self._logger = logger or NullLogger()

    def parsear(self, archivo: BinaryIO) -> ResumenTarjeta:
        raise NotImplementedError
