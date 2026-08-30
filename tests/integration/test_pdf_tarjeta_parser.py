"""Tests de integración del parser de tarjetas de crédito con PDFs reales."""

from datetime import date
from pathlib import Path

import pytest

from src.adapters.gateways.pdf_tarjeta_parser_gateway import PDFTarjetaParserGateway
from src.domain.tarjetas.entities import ResumenTarjeta

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "tarjeta_credito"


def _parsear_archivo(nombre: str) -> ResumenTarjeta:
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        pytest.skip(f"PDF de tarjeta no encontrado: {ruta}")
    with ruta.open("rb") as archivo:
        return PDFTarjetaParserGateway().parsear(archivo)


def test_parsear_bbva_visa_gold() -> None:
    resumen = _parsear_archivo("20260829_visa.pdf")
    assert resumen.banco == "BBVA"
    assert resumen.tarjeta_tipo == "VISA"
    assert resumen.tarjeta_categoria == "GOLD"
    assert resumen.numero_cuenta == "1097452662"
    assert resumen.fecha_cierre == date(2026, 8, 27)
    assert resumen.fecha_vencimiento == date(2026, 9, 7)
    assert resumen.saldo_pesos == 144565.27
    assert resumen.saldo_dolares == 0.0
    assert resumen.pago_minimo == 82120.0
    assert resumen.id_resumen == "1097452662-2026-08-27"
    assert len(resumen.consumos) == 3
    assert resumen.consumos[0].descripcion == "MIRGOR SACIFIA C.08/09 000014"


def test_parsear_bbva_mastercard_gold() -> None:
    resumen = _parsear_archivo("20260829_mastercard.pdf")
    assert resumen.banco == "BBVA"
    assert resumen.tarjeta_tipo == "MASTERCARD"
    assert resumen.tarjeta_categoria == "GOLD"
    assert resumen.numero_cuenta == "1267475185"
    assert resumen.fecha_cierre == date(2026, 8, 27)
    assert resumen.fecha_vencimiento == date(2026, 9, 7)
    assert resumen.saldo_pesos == 22547.36
    assert resumen.saldo_dolares == 0.0
    assert resumen.pago_minimo == 1382.0
    assert len(resumen.consumos) == 1
    assert resumen.consumos[0].descripcion == "ENERSE SA 001831"


def test_parsear_bapro_visa_classic() -> None:
    resumen = _parsear_archivo("1151377322.01.27-08-26.pdf")
    assert resumen.banco == "BAPRO"
    assert resumen.tarjeta_tipo == "VISA"
    assert resumen.tarjeta_categoria == "CLASSIC"
    assert resumen.numero_cuenta == "1151377322"
    assert resumen.fecha_cierre == date(2026, 8, 27)
    assert resumen.fecha_vencimiento == date(2026, 9, 7)
    assert resumen.saldo_pesos == 277449.24
    assert resumen.saldo_dolares == 55.78
    assert resumen.pago_minimo == 65922.0
    assert resumen.consumos == ()
