import csv
import io
from datetime import date
from unittest.mock import MagicMock

from src.adapters.controllers.receipt_controller import ReceiptController
from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.application.use_cases.conciliar_recibo import ConciliarReciboUseCase
from src.application.use_cases.obtener_recibo import ObtenerReciboUseCase
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import PeriodoVigencia, SituacionRevista
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


def _mock_recibo() -> ReciboSueldo:
    return ReciboSueldo(
        id_recibo="recibo-test-desglose",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(
            organismo_o_empresa="DGCyE PBA",
            cuit="30655555551",
        ),
        agente=Agente(
            nombre_completo="DOCENTE TEST",
            numero_documento="36528392",
            cuil="20365283924",
            mes_pago="2026-08",
        ),
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(codigo="055IS0199"),
                cargo=CargoDetalle(
                    secuencia="001",
                    cargo_real="PR",
                    carga_horaria=4.5,
                    situacion_revista="TIT",
                ),
                conceptos=[],
                subtotal_haberes=100000.0,
                subtotal_descuentos=20000.0,
                liquido_calculado=80000.0,
            ),
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(codigo="055IS0199"),
                cargo=CargoDetalle(
                    secuencia="002",
                    cargo_real="PF",
                    carga_horaria=2.0,
                    situacion_revista="SUP",
                    periodo_liquidado="2026-06",
                ),
                conceptos=[],
                subtotal_haberes=25000.0,
                subtotal_descuentos=5000.0,
                liquido_calculado=20000.0,
            ),
        ],
        totales=TotalesConsolidados(
            total_haberes=125000.0,
            total_descuentos=25000.0,
            total_liquido=100000.0,
            total_declarado=100000.0,
            estado_cierre="VALIDO",
            diferencia_cierre=0.0,
        ),
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055IS0199",
                secuencia="001",
                periodo_liquidado="2026-08",
                fecha_pago="04/09/2026",
                orden_pago_codigo="00871",
                orden_pago_descripcion="SDOS PRO",
                liquido_pesos=50000.0,
                distrito="055",
                tipo_nivel="IS",
                escuela="0199",
                revista="TIT",
                orden_pago="00871",
                importe=50000.0,
                concepto_normalizado="sueldo",
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055IS0199",
                secuencia="002",
                periodo_liquidado="2026-06",
                fecha_pago="04/09/2026",
                orden_pago_codigo="00877",
                orden_pago_descripcion="SDOS SUP",
                liquido_pesos=20000.0,
                distrito="055",
                tipo_nivel="IS",
                escuela="0199",
                revista="SUP",
                orden_pago="00877",
                importe=20000.0,
                concepto_normalizado="retroactivo",
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055IS0199",
                secuencia="003",
                periodo_liquidado="2026-08",
                fecha_pago="04/09/2026",
                orden_pago_codigo="00871",
                orden_pago_descripcion="SAC",
                liquido_pesos=10000.0,
                distrito="055",
                tipo_nivel="IS",
                escuela="0199",
                revista="TIT",
                orden_pago="00871",
                importe=10000.0,
                concepto_normalizado="SAC",
            ),
        ],
    )


def test_controller_desglose_financiero() -> None:
    db_url = "sqlite:///:memory:"
    recibo_gw = SQLReciboGateway(db_url)
    recibo = _mock_recibo()
    recibo_gw.guardar(recibo)

    obtener_uc = ObtenerReciboUseCase(recibo_gw)
    controller = ReceiptController(
        parse_use_case=MagicMock(),
        obtener_use_case=obtener_uc,
    )

    response = controller.desglosar(recibo.id_recibo)
    assert response.success is True
    desglose = response.data
    assert desglose.mes_pago == "2026-08"
    assert desglose.total_liquido == 100000.0
    assert desglose.importe_periodo_nominal == 50000.0
    assert desglose.importe_retroactivos == 20000.0
    assert desglose.importe_sac == 10000.0
    assert desglose.importe_otros == 0.0


def test_controller_exportar_conciliacion_csv() -> None:
    db_url = "sqlite:///:memory:"
    recibo_gw = SQLReciboGateway(db_url)
    desig_gw = SQLDesignacionDocenteGateway(db_url)
    recibo = _mock_recibo()
    recibo_gw.guardar(recibo)

    desig_gw.guardar(
        DesignacionDocente(
            id_designacion="desig-001",
            docente_cuit=recibo.agente.cuil,
            establecimiento="055IS0199",
            distrito="055",
            cargo_asignatura="PR",
            secuencia=1,
            revista=SituacionRevista.TITULAR,
            modulos=4,
            vigencia=PeriodoVigencia(fecha_desde=date(2026, 1, 1)),
        )
    )
    desig_gw.guardar(
        DesignacionDocente(
            id_designacion="desig-no-cobrada",
            docente_cuit=recibo.agente.cuil,
            establecimiento="116MT0001",
            distrito="116",
            cargo_asignatura="PF",
            secuencia=5,
            revista=SituacionRevista.PROVISIONAL,
            modulos=2,
            vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1)),
        )
    )

    conciliar_uc = ConciliarReciboUseCase(recibo_gw, desig_gw)
    controller = ReceiptController(
        parse_use_case=MagicMock(),
        conciliar_use_case=conciliar_uc,
    )

    csv_content = controller.exportar_conciliacion_csv(recibo.id_recibo)
    reader = csv.reader(io.StringIO(csv_content), delimiter=";")
    filas = list(reader)

    assert filas[0] == [
        "tipo_linea",
        "secuencia",
        "escuela_codigo",
        "periodo_liquidado",
        "revista_recibo",
        "revista_designacion",
        "modulos_recibo",
        "modulos_designacion",
        "liquido_pesos",
        "estado",
        "es_retroactivo",
        "id_designacion",
        "observacion",
    ]

    tipos = [fila[0] for fila in filas[1:]]
    assert "CONCILIADA" in tipos
    assert "HUERFANA" in tipos
    assert "NO_COBRADA" in tipos
