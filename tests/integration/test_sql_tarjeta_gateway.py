"""Tests de integración del gateway SQLAlchemy de tarjetas de crédito."""

from datetime import date

from src.adapters.gateways.sql_tarjeta_gateway import SQLTarjetaGateway
from src.domain.tarjetas.entities import ResumenTarjeta, TransaccionTarjeta


def _crear_resumen(
    id_resumen: str, fecha_vencimiento: date, con_consumos: bool = True
) -> ResumenTarjeta:
    consumos: tuple[TransaccionTarjeta, ...] = ()
    if con_consumos:
        consumos = (
            TransaccionTarjeta(
                fecha=date(2026, 8, 10),
                descripcion="Compra supermercado",
                monto_pesos=1500.0,
                monto_dolares=0.0,
            ),
        )
    return ResumenTarjeta(
        id_resumen=id_resumen,
        banco="BBVA",
        tarjeta_tipo="VISA",
        tarjeta_categoria="GOLD",
        numero_cuenta="1234",
        fecha_cierre=date(2026, 8, 29),
        fecha_vencimiento=fecha_vencimiento,
        saldo_pesos=144565.27,
        saldo_dolares=55.78,
        pago_minimo=10000.0,
        consumos=consumos,
    )


def test_guardar_y_obtener_por_id() -> None:
    gateway = SQLTarjetaGateway("sqlite:///:memory:")
    gateway.guardar(_crear_resumen("res-1", date(2026, 9, 7)))
    obtenido = gateway.obtener_por_id("res-1")
    assert obtenido is not None
    assert obtenido.banco == "BBVA"
    assert obtenido.saldo_pesos == 144565.27
    assert obtenido.fecha_vencimiento == date(2026, 9, 7)
    assert len(obtenido.consumos) == 1
    assert obtenido.consumos[0].descripcion == "Compra supermercado"


def test_obtener_por_id_inexistente_retorna_none() -> None:
    gateway = SQLTarjetaGateway("sqlite:///:memory:")
    assert gateway.obtener_por_id("no-existe") is None


def test_obtener_resumenes_vencimiento_cercano() -> None:
    gateway = SQLTarjetaGateway("sqlite:///:memory:")
    gateway.guardar(_crear_resumen("res-1", date(2026, 9, 7)))
    gateway.guardar(_crear_resumen("res-2", date(2026, 10, 1)))
    gateway.guardar(_crear_resumen("res-3", date(2026, 8, 15), con_consumos=False))
    cercanos = gateway.obtener_resumenes_vencimiento_cercano(date(2026, 9, 1))
    ids = {resumen.id_resumen for resumen in cercanos}
    assert ids == {"res-1", "res-2"}
