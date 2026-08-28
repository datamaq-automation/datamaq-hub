"""Pruebas unitarias para SQLReciboGateway."""

from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


def _crear_recibo_dummy(
    cuit: str = "20-36528392-4", mes_pago: str = "2026-07"
) -> ReciboSueldo:
    return ReciboSueldo(
        id_recibo="recibo-test-01",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="Docente Test",
            numero_documento="36528392",
            cuil=cuit,
            mes_pago=mes_pago,
        ),
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="016",
                periodo_liquidado="202607",
                fecha_pago="2026-08-07",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=150000.0,
            )
        ],
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 IS 0199", nombre="ISFT 199"
                ),
                cargo=CargoDetalle(
                    secuencia="016",
                    situacion_revista="TITULAR",
                    cargo_real="Profesor",
                    carga_horaria=4.0,
                    periodo_liquidado="202607",
                ),
                conceptos=[
                    ConceptoItem(
                        codigo="1",
                        descripcion="Básico",
                        tipo=TipoConcepto.REMUNERATIVO,
                        haberes=160000.0,
                    ),
                    ConceptoItem(
                        codigo="10",
                        descripcion="IOMA",
                        tipo=TipoConcepto.DESCUENTO,
                        descuentos=10000.0,
                    ),
                ],
                subtotal_haberes=160000.0,
                subtotal_descuentos=10000.0,
                liquido_calculado=150000.0,
            )
        ],
        totales=TotalesConsolidados(
            total_haberes=160000.0,
            total_descuentos=10000.0,
            total_liquido=150000.0,
        ),
    )


def test_guardar_y_obtener_recibo() -> None:
    gateway = SQLReciboGateway(database_url="sqlite:///:memory:")
    recibo = _crear_recibo_dummy()

    guardado = gateway.guardar(recibo)
    assert guardado.id_recibo == "recibo-test-01"

    recuperado = gateway.obtener_por_id("recibo-test-01")
    assert recuperado is not None
    assert recuperado.agente.cuil == "20-36528392-4"
    assert recuperado.totales.total_liquido == 150000.0
    assert len(recuperado.resumen_liquidos) == 1
    assert len(recuperado.liquidaciones) == 1


def test_listar_y_eliminar_recibos() -> None:
    gateway = SQLReciboGateway(database_url="sqlite:///:memory:")
    r1 = _crear_recibo_dummy(cuit="20-36528392-4", mes_pago="2026-07")
    r1.id_recibo = "rec-1"
    r2 = _crear_recibo_dummy(cuit="20-36528392-4", mes_pago="2026-08")
    r2.id_recibo = "rec-2"

    gateway.guardar(r1)
    gateway.guardar(r2)

    lista = gateway.listar(cuit="20365283924")
    assert len(lista) == 2

    lista_julio = gateway.listar(mes_pago="2026-07")
    assert len(lista_julio) == 1
    assert lista_julio[0].id_recibo == "rec-1"

    eliminado = gateway.eliminar("rec-1")
    assert eliminado is True
    assert gateway.obtener_por_id("rec-1") is None
