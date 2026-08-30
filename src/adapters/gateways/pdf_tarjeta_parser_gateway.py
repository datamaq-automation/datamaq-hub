"""Gateway parser de resúmenes de tarjetas de crédito (BBVA y BAPRO) con pdfplumber."""

import io
import re
from datetime import date
from typing import BinaryIO

import pdfplumber

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.tarjetas.entities import ResumenTarjeta, TransaccionTarjeta
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

_RE_CUENTA_BBVA = re.compile(r"cuenta\s+(\d+)")
_RE_TARJETA_BBVA = re.compile(
    r"(Visa|Mastercard)\s+"
    r"(Gold|Platinum|Black|Signature|Regional|Internacional|Nacional)"
    r"\s+CONSOLIDADO",
    re.IGNORECASE,
)
_RE_CABECERA_BBVA = re.compile(
    r"(\d{1,2}-[A-Za-z]{3}-\d{2})\s+"
    r"(\d{1,2}-[A-Za-z]{3}-\d{2})\s+"
    r"([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
)
_RE_CONSUMO_BBVA = re.compile(r"^(\d{1,2}-[A-Za-z]{3}-\d{2})\s+(.*?)\s+([\d.,]+)$")

_RE_CUENTA_BAPRO = re.compile(r"N DE CUENTA:\s*(\d+)")
_RE_CIERRE_BAPRO = re.compile(r"CIERRE ACTUAL:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})")
_RE_TARJETA_BAPRO = re.compile(
    r"^(VISA|MASTERCARD|AMEX)\s+"
    r"(CLASSIC|GOLD|PLATINUM|NACIONAL|INTERNACIONAL)",
    re.IGNORECASE | re.MULTILINE,
)
_RE_DATOS_BAPRO = re.compile(
    r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})\s+"
    r"([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
)


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
        datos = archivo.read()
        if not datos or len(datos) < 10:
            raise TarjetaParserException("Archivo PDF vacío o demasiado corto.")
        texto = self._extraer_texto(datos)
        texto_mayus = texto.upper()
        if "CONSOLIDADO" in texto_mayus:
            return self._parsear_bbva(texto)
        if "N DE CUENTA" in texto_mayus or "VISA CLASSIC" in texto_mayus:
            return self._parsear_bapro(texto)
        raise TarjetaParserException("Formato de resumen de tarjeta no reconocido.")

    @staticmethod
    def _extraer_texto(datos: bytes) -> str:
        try:
            with pdfplumber.open(io.BytesIO(datos)) as pdf:
                paginas = [page.extract_text() or "" for page in pdf.pages]
        except Exception as exc:
            raise TarjetaParserException(f"Error al leer el PDF: {exc!s}") from exc
        return "\n".join(paginas)

    def _parsear_bbva(self, texto: str) -> ResumenTarjeta:
        m_tarjeta = _RE_TARJETA_BBVA.search(texto)
        if not m_tarjeta:
            raise TarjetaParserException(
                "No se pudo determinar el tipo de tarjeta BBVA."
            )
        m_cuenta = _RE_CUENTA_BBVA.search(texto)
        if not m_cuenta:
            raise TarjetaParserException("No se encontró el número de cuenta (BBVA).")
        m_datos = _RE_CABECERA_BBVA.search(texto)
        if not m_datos:
            raise TarjetaParserException(
                "No se encontraron los datos del resumen (BBVA)."
            )
        fecha_cierre = parse_fecha(m_datos.group(1))
        fecha_vencimiento = parse_fecha(m_datos.group(2))
        return ResumenTarjeta(
            id_resumen=f"{m_cuenta.group(1)}-{fecha_cierre.isoformat()}",
            banco="BBVA",
            tarjeta_tipo=m_tarjeta.group(1).upper(),
            tarjeta_categoria=m_tarjeta.group(2).upper(),
            numero_cuenta=m_cuenta.group(1),
            fecha_cierre=fecha_cierre,
            fecha_vencimiento=fecha_vencimiento,
            saldo_pesos=limpiar_monto(m_datos.group(3)),
            saldo_dolares=limpiar_monto(m_datos.group(4)),
            pago_minimo=limpiar_monto(m_datos.group(5)),
            consumos=self._extraer_consumos_bbva(texto),
        )

    def _extraer_consumos_bbva(self, texto: str) -> tuple[TransaccionTarjeta, ...]:
        consumos: list[TransaccionTarjeta] = []
        en_seccion = False
        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue
            if linea.upper().startswith("CONSUMOS"):
                en_seccion = True
                continue
            if not en_seccion:
                continue
            if linea.upper().startswith("TOTAL CONSUMOS"):
                break
            m = _RE_CONSUMO_BBVA.match(linea)
            if not m:
                continue
            consumos.append(
                TransaccionTarjeta(
                    fecha=parse_fecha(m.group(1)),
                    descripcion=m.group(2).strip(),
                    monto_pesos=limpiar_monto(m.group(3)),
                    monto_dolares=0.0,
                )
            )
        return tuple(consumos)

    def _parsear_bapro(self, texto: str) -> ResumenTarjeta:
        m_tarjeta = _RE_TARJETA_BAPRO.search(texto)
        if not m_tarjeta:
            raise TarjetaParserException(
                "No se pudo determinar el tipo de tarjeta BAPRO."
            )
        m_cuenta = _RE_CUENTA_BAPRO.search(texto)
        if not m_cuenta:
            raise TarjetaParserException("No se encontró el número de cuenta (BAPRO).")
        m_cierre = _RE_CIERRE_BAPRO.search(texto)
        if not m_cierre:
            raise TarjetaParserException("No se encontró la fecha de cierre (BAPRO).")
        m_datos = _RE_DATOS_BAPRO.search(texto)
        if not m_datos:
            raise TarjetaParserException(
                "No se encontraron los datos del resumen (BAPRO)."
            )
        fecha_cierre = parse_fecha(m_cierre.group(1))
        return ResumenTarjeta(
            id_resumen=f"{m_cuenta.group(1)}-{fecha_cierre.isoformat()}",
            banco="BAPRO",
            tarjeta_tipo=m_tarjeta.group(1).upper(),
            tarjeta_categoria=m_tarjeta.group(2).upper(),
            numero_cuenta=m_cuenta.group(1),
            fecha_cierre=fecha_cierre,
            fecha_vencimiento=parse_fecha(m_datos.group(1)),
            saldo_pesos=limpiar_monto(m_datos.group(2)),
            saldo_dolares=limpiar_monto(m_datos.group(3)),
            pago_minimo=limpiar_monto(m_datos.group(4)),
            consumos=(),
        )
