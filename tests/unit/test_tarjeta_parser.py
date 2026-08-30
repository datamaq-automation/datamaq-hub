"""Tests unitarios de los helpers puros del parser de tarjetas de crédito."""

from datetime import date

import pytest

from src.adapters.gateways.pdf_tarjeta_parser_gateway import limpiar_monto, parse_fecha
from src.domain.tarjetas.exceptions import TarjetaParserException


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("27-Ago-26", date(2026, 8, 27)),
        ("07-Sep-26", date(2026, 9, 7)),
        ("27-Dic-25", date(2025, 12, 27)),
        ("07 Sep 26", date(2026, 9, 7)),
        ("27 Ago 26", date(2026, 8, 27)),
        ("07.08.26", date(2026, 8, 7)),
    ],
)
def test_parse_fecha_formatos_soportados(texto: str, esperado: date) -> None:
    assert parse_fecha(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    ["no-es-fecha", "32-Ago-26", "07-Mes-26", ""],
)
def test_parse_fecha_rechaza_formatos_invalidos(texto: str) -> None:
    with pytest.raises(TarjetaParserException):
        parse_fecha(texto)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("144.565,27", 144565.27),
        ("22.547,36", 22547.36),
        ("0,00", 0.0),
        ("55,78", 55.78),
        ("65.922,00", 65922.0),
        ("-,--", 0.0),
        ("702.405,15-", -702405.15),
        ("-189.470,00", -189470.0),
        ("2,12", 2.12),
        ("$ 1.714,21", 1714.21),
    ],
)
def test_limpiar_monto_convierte_importes(texto: str, esperado: float) -> None:
    assert limpiar_monto(texto) == esperado


def test_limpiar_monto_rechaza_importe_invalido() -> None:
    with pytest.raises(TarjetaParserException):
        limpiar_monto("abc")
