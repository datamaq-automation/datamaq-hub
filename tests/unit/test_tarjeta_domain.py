"""Tests unitarios del dominio de tarjetas de crédito."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.domain.tarjetas.entities import ResumenTarjeta, TransaccionTarjeta
from src.domain.tarjetas.exceptions import TarjetaException, TarjetaParserException


def test_transaccion_tarjeta_es_inmutable_y_default_cupon_vacio() -> None:
    transaccion = TransaccionTarjeta(
        fecha=date(2026, 8, 10),
        descripcion="Compra supermercado",
        monto_pesos=1500.0,
        monto_dolares=0.0,
    )
    assert transaccion.nro_cupon == ""
    assert transaccion.descripcion == "Compra supermercado"
    with pytest.raises(FrozenInstanceError):
        setattr(transaccion, "monto_pesos", 999.0)


def test_resumen_tarjeta_consolida_campos() -> None:
    consumo = TransaccionTarjeta(
        fecha=date(2026, 8, 10),
        descripcion="Compra",
        monto_pesos=100.0,
        monto_dolares=0.0,
    )
    resumen = ResumenTarjeta(
        id_resumen="res-1",
        banco="BBVA",
        tarjeta_tipo="VISA",
        tarjeta_categoria="GOLD",
        numero_cuenta="1234",
        fecha_cierre=date(2026, 8, 29),
        fecha_vencimiento=date(2026, 9, 7),
        saldo_pesos=144565.27,
        saldo_dolares=0.0,
        pago_minimo=10000.0,
        consumos=(consumo,),
    )
    assert resumen.id_resumen == "res-1"
    assert resumen.banco == "BBVA"
    assert resumen.saldo_pesos == 144565.27
    assert len(resumen.consumos) == 1
    assert resumen.consumos[0].descripcion == "Compra"


def test_resumen_tarjeta_consumos_default_vacio() -> None:
    resumen = ResumenTarjeta(
        id_resumen="res-2",
        banco="BAPRO",
        tarjeta_tipo="VISA",
        tarjeta_categoria="CLASSIC",
        numero_cuenta="5678",
        fecha_cierre=date(2026, 8, 27),
        fecha_vencimiento=date(2026, 9, 7),
        saldo_pesos=277449.24,
        saldo_dolares=55.78,
        pago_minimo=20000.0,
    )
    assert resumen.consumos == ()


def test_jerarquia_de_excepciones() -> None:
    assert issubclass(TarjetaParserException, TarjetaException)
    assert issubclass(TarjetaException, Exception)
    exc = TarjetaParserException("formato inválido", {"banco": "BBVA"})
    assert exc.message == "formato inválido"
    assert exc.details == {"banco": "BBVA"}
