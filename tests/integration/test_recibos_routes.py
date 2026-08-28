"""Pruebas de integración para las rutas de recibos de sueldo y conciliación."""

from starlette.testclient import TestClient

from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoRecibo


def _crear_y_guardar_recibo_test() -> str:
    gateway = SQLReciboGateway()
    recibo = ReciboSueldo(
        id_recibo="recibo-test-integration-01",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="Docente Integración",
            numero_documento="36528392",
            cuil="20-36528392-4",
            mes_pago="2026-07",
        ),
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="016",
                periodo_liquidado="202607",
                fecha_pago="2026-08-07",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=250000.0,
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
                    carga_horaria=4.0,
                    periodo_liquidado="202607",
                ),
                liquido_calculado=250000.0,
            )
        ],
        totales=TotalesConsolidados(total_liquido=250000.0),
    )
    gateway.guardar(recibo)
    return "recibo-test-integration-01"


def test_recibos_crud_y_conciliacion_routes(client: TestClient) -> None:
    id_recibo = _crear_y_guardar_recibo_test()

    # 1. GET /recibos
    r_list = client.get("/api/v1/recibos?cuit=20365283924")
    assert r_list.status_code == 200
    assert r_list.json()["success"] is True
    assert len(r_list.json()["data"]) >= 1

    # 2. GET /recibos/{id}
    r_get = client.get(f"/api/v1/recibos/{id_recibo}")
    assert r_get.status_code == 200
    data = r_get.json()["data"]
    assert data["id_recibo"] == id_recibo
    assert data["agente"]["cuil"] == "20-36528392-4"

    # 3. GET /recibos/{id}/conciliacion
    r_conc = client.get(f"/api/v1/recibos/{id_recibo}/conciliacion")
    assert r_conc.status_code == 200
    reporte = r_conc.json()["data"]
    assert reporte["id_recibo"] == id_recibo
    assert reporte["total_liquidado_recibo"] == 250000.0
    assert "resumen_financiero" in reporte

    # 4. POST /recibos/{id}/crear-designaciones-huerfanas
    r_crear = client.post(f"/api/v1/recibos/{id_recibo}/crear-designaciones-huerfanas")
    assert r_crear.status_code == 200
    assert isinstance(r_crear.json()["data"], list)

    # 5. DELETE /recibos/{id}
    r_del = client.delete(f"/api/v1/recibos/{id_recibo}")
    assert r_del.status_code == 200
    assert r_del.json()["data"]["eliminado"] is True

    # 6. GET /recibos/{id} -> 404
    r_notfound = client.get(f"/api/v1/recibos/{id_recibo}")
    assert r_notfound.status_code == 404
    assert r_notfound.json()["success"] is False
    assert r_notfound.json()["error"]["code"] == "RECIBO_NOT_FOUND"
