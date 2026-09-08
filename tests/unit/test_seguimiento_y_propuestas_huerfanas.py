from datetime import date
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from src.adapters.controllers.receipt_controller import ReceiptController
from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.adapters.gateways.sql_seguimiento_no_liquidados_gateway import (
    SQLSeguimientoNoLiquidadosGateway,
)
from src.application.dtos.conciliacion_dto import (
    ConfirmarPropuestasDTO,
    PropuestaDesignacionDTO,
)
from src.application.use_cases.conciliar_recibo import ConciliarReciboUseCase
from src.application.use_cases.gestionar_propuestas_huerfanas import (
    GestionarPropuestasHuerfanasUseCase,
)
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


def _mock_recibo(id_recibo: str, mes_pago: str) -> ReciboSueldo:
    return ReciboSueldo(
        id_recibo=id_recibo,
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA", cuit="30655555551"),
        agente=Agente(
            nombre_completo="DOCENTE TEST",
            numero_documento="36528392",
            cuil="20365283924",
            mes_pago=mes_pago,
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
                    secuencia="099",
                    cargo_real="PF",
                    carga_horaria=2.0,
                    situacion_revista="SUP",
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
                periodo_liquidado=mes_pago,
                fecha_pago="04/09/2026",
                orden_pago_codigo="00871",
                orden_pago_descripcion="SDOS PRO",
                liquido_pesos=80000.0,
                distrito="055",
                tipo_nivel="IS",
                escuela="0199",
                revista="TIT",
                orden_pago="00871",
                importe=80000.0,
                concepto_normalizado="sueldo",
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055IS0199",
                secuencia="099",
                periodo_liquidado=mes_pago,
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
                concepto_normalizado="sueldo",
            ),
        ],
    )


def test_seguimiento_diferido_y_alerta_2_periodos() -> None:
    db_url = "sqlite:///:memory:"
    recibo_gw = SQLReciboGateway(db_url)
    desig_gw = SQLDesignacionDocenteGateway(db_url)
    seg_gw = SQLSeguimientoNoLiquidadosGateway(db_url)

    # Recibo 1 (mes 2026-08)
    r1 = _mock_recibo("recibo-1", "2026-08")
    recibo_gw.guardar(r1)

    # Designación en Secuencia 001 (cobrada) y Secuencia 005 (no cobrada)
    desig_gw.guardar(
        DesignacionDocente(
            id_designacion="desig-001",
            docente_cuit=r1.agente.cuil,
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
            id_designacion="desig-005",
            docente_cuit=r1.agente.cuil,
            establecimiento="116MT0001",
            distrito="116",
            cargo_asignatura="PF",
            secuencia=5,
            revista=SituacionRevista.PROVISIONAL,
            modulos=2,
            vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1)),
        )
    )

    conciliar_uc = ConciliarReciboUseCase(
        recibo_repository=recibo_gw,
        designacion_repository=desig_gw,
        seguimiento_repository=seg_gw,
    )

    # 1. Ejecutar conciliación mes 1 (2026-08)
    conciliar_uc.execute("recibo-1")
    pendientes_m1 = seg_gw.listar(docente_cuit="20365283924", solo_pendientes=True)
    assert len(pendientes_m1) == 1
    assert pendientes_m1[0].id_designacion == "desig-005"
    assert pendientes_m1[0].periodos_consecutivos == 1
    assert pendientes_m1[0].alerta_2_periodos is False

    # 2. Recibo 2 (mes 2026-09) donde desig-005 sigue sin cobrarse
    r2 = _mock_recibo("recibo-2", "2026-09")
    recibo_gw.guardar(r2)
    conciliar_uc.execute("recibo-2")

    pendientes_m2 = seg_gw.listar(docente_cuit="20365283924", solo_pendientes=True)
    assert len(pendientes_m2) == 2
    # El más reciente (de recibo-2) encadena 2 períodos y activa la alerta
    mas_reciente = pendientes_m2[0]
    assert mas_reciente.id_recibo == "recibo-2"
    assert mas_reciente.periodos_consecutivos == 2
    assert mas_reciente.alerta_2_periodos is True


def test_propuestas_huerfanas_y_alta_confirmada() -> None:
    db_url = "sqlite:///:memory:"
    recibo_gw = SQLReciboGateway(db_url)
    desig_gw = SQLDesignacionDocenteGateway(db_url)

    r1 = _mock_recibo("recibo-huerfano", "2026-08")
    recibo_gw.guardar(r1)

    propuestas_uc = GestionarPropuestasHuerfanasUseCase(
        recibo_repository=recibo_gw,
        designacion_repository=desig_gw,
    )

    controller = ReceiptController(
        parse_use_case=MagicMock(),
        gestionar_propuestas_use_case=propuestas_uc,
    )

    # GET propuestas huérfanas
    res_prop = controller.obtener_propuestas_huerfanas("recibo-huerfano")
    assert res_prop.success is True
    propuestas = res_prop.data
    assert len(propuestas) >= 1
    p = propuestas[0]
    assert p.secuencia in ["001", "099"]
    assert p.escuela_codigo == "055IS0199"

    # POST confirmar solo un subconjunto de propuestas
    solicitud = ConfirmarPropuestasDTO(
        propuestas=[
            PropuestaDesignacionDTO(
                secuencia="099",
                escuela_codigo="055IS0199",
                distrito="055",
                tipo_nivel="IS",
                escuela_numero="0199",
                cargo_codigo="DOCENTE",
                situacion_revista="TITULAR",
                modulos_horas=4.5,
                fecha_desde="2026-08-01",
                observaciones="Confirmado por test",
            )
        ]
    )

    res_conf = controller.confirmar_propuestas_huerfanas("recibo-huerfano", solicitud)
    assert res_conf.success is True
    creadas = res_conf.data
    assert len(creadas) == 1
    assert creadas[0].establecimiento == "055IS0199"

    # Verificar que el historial del docente en designaciones ahora incluye la nueva
    historial = desig_gw.obtener_historial("20365283924")
    assert len(historial) == 1
    assert historial[0].establecimiento == "055IS0199"


def test_parser_escuela_codigo_y_fecha_desde_retroactiva() -> None:
    from src.application.use_cases.gestionar_propuestas_huerfanas import (
        GestionarPropuestasHuerfanasUseCase,
        _parse_escuela_codigo,
    )

    # 1. Test unitario de _parse_escuela_codigo
    c1, d1, n1, e1 = _parse_escuela_codigo("11-ESCOBAR MT-0001")
    assert c1 == "011MT0001"
    assert d1 == "011"
    assert n1 == "MT"
    assert e1 == "0001"

    c2, d2, n2, e2 = _parse_escuela_codigo("055IS0199")
    assert c2 == "055IS0199"
    assert d2 == "055"
    assert n2 == "IS"
    assert e2 == "0199"

    # 2. Test de fecha_desde retroactiva y validación de solicitud vacía
    db_url = "sqlite:///:memory:"
    recibo_gw = SQLReciboGateway(db_url)
    desig_gw = SQLDesignacionDocenteGateway(db_url)

    r = _mock_recibo("recibo-retro", "2026-08")
    # Modificar una liquidación para que tenga periodo_liquidado retroactivo "2026-06"
    r.liquidaciones[0].cargo.periodo_liquidado = "2026-06"
    recibo_gw.guardar(r)

    use_case = GestionarPropuestasHuerfanasUseCase(
        recibo_repository=recibo_gw,
        designacion_repository=desig_gw,
    )

    propuestas = use_case.obtener_propuestas("recibo-retro")
    prop_retro = next(p for p in propuestas if p.secuencia == "001")
    assert prop_retro.fecha_desde == "2026-06-01"

    # Validaciones HTTP/DTO para propuesta vacía
    with pytest.raises(ValidationError):
        ConfirmarPropuestasDTO(propuestas=[])
