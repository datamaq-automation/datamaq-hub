"""Pruebas unitarias para el motor de conciliación de recibos vs designaciones docentes."""

from datetime import date

from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.application.use_cases.conciliar_recibo import ConciliarReciboUseCase
from src.application.use_cases.crear_designaciones_desde_recibo import (
    CrearDesignacionesDesdeReciboUseCase,
)
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import PeriodoVigencia, SituacionRevista
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    Empleador,
    EstablecimientoDetalle,
    EstadoLineaConciliacion,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.services import ConciliadorReciboDocenteService
from src.domain.recibos.value_objects import TipoRecibo


def _crear_recibo_complejo() -> ReciboSueldo:
    """Crea un recibo de Julio 2026 con 4 líneas:
    1. ISFT 199 sec 016 (Activa, período 2026-07)
    2. MT 0001 sec 018 (Suplencia cesada en Junio, retroactivo 2026-05)
    3. MT 0001 sec 018 (Suplencia cesada en Junio, retroactivo 2026-06)
    4. Escobar 116 MT-0001 sec 022 (Huérfana, 4 modulos SUP, sin designación registrada)
    """
    return ReciboSueldo(
        id_recibo="recibo-julio-2026",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="Agustin Test",
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
                liquido_pesos=300000.0,
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055 MT 0001",
                secuencia="018",
                periodo_liquidado="202605",
                fecha_pago="2026-08-07",
                orden_pago_codigo="001",
                orden_pago_descripcion="RETROACTIVO",
                liquido_pesos=150000.0,
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055 MT 0001",
                secuencia="018",
                periodo_liquidado="202606",
                fecha_pago="2026-08-07",
                orden_pago_codigo="001",
                orden_pago_descripcion="RETROACTIVO",
                liquido_pesos=150000.0,
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="116 MT 0001",
                secuencia="022",
                periodo_liquidado="202607",
                fecha_pago="2026-08-07",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=232000.0,
            ),
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
                liquido_calculado=300000.0,
            ),
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 MT 0001", nombre="EEST 1 Tigre"
                ),
                cargo=CargoDetalle(
                    secuencia="018",
                    situacion_revista="SUPLENTE",
                    carga_horaria=2.0,
                    periodo_liquidado="202605",
                ),
                liquido_calculado=150000.0,
            ),
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 MT 0001", nombre="EEST 1 Tigre"
                ),
                cargo=CargoDetalle(
                    secuencia="018",
                    situacion_revista="SUPLENTE",
                    carga_horaria=2.0,
                    periodo_liquidado="202606",
                ),
                liquido_calculado=150000.0,
            ),
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="116 MT 0001", nombre="EEST 1 Escobar"
                ),
                cargo=CargoDetalle(
                    secuencia="022",
                    situacion_revista="SUPLENTE",
                    carga_horaria=4.0,
                    periodo_liquidado="202607",
                ),
                liquido_calculado=232000.0,
            ),
        ],
        totales=TotalesConsolidados(total_liquido=832000.0),
    )


def test_conciliacion_servicio_detecta_activas_retroactivos_y_huerfanas() -> None:
    recibo = _crear_recibo_complejo()

    # Designación 1: Activa en ISFT 199
    desig_activa = DesignacionDocente(
        id_designacion="desig-activa-01",
        docente_cuit="20365283924",
        establecimiento="ISFT N° 199 Tigre",
        distrito="Tigre",
        escuela_numero="0199",
        secuencia=16,
        cargo_asignatura="Automatización",
        revista=SituacionRevista.TITULAR,
        modulos=4,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None),
    )

    # Designación 2: Suplencia cesada en Junio (EEST 1 Tigre)
    desig_suplencia = DesignacionDocente(
        id_designacion="desig-suplente-02",
        docente_cuit="20365283924",
        establecimiento="EEST N° 1 Tigre",
        distrito="Tigre",
        escuela_numero="0001",
        secuencia=18,
        cargo_asignatura="Electrónica",
        revista=SituacionRevista.SUPLENTE,
        modulos=2,
        vigencia=PeriodoVigencia(
            fecha_desde=date(2026, 4, 1), fecha_hasta=date(2026, 6, 30)
        ),
        motivo_cese="FIN_LICENCIA",
    )

    # Designación 3: Activa en Pilar pero NO vino en el recibo (Designación No Cobrada)
    desig_no_cobrada = DesignacionDocente(
        id_designacion="desig-no-cobrada-03",
        docente_cuit="20365283924",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        escuela_numero="0001",
        secuencia=20,
        cargo_asignatura="Física",
        revista=SituacionRevista.PROVISIONAL,
        modulos=2,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None),
    )

    resultado = ConciliadorReciboDocenteService.conciliar(
        recibo=recibo,
        designaciones=[desig_activa, desig_suplencia, desig_no_cobrada],
    )

    # Verificaciones
    assert resultado.total_lineas_recibo == 4
    assert len(resultado.lineas_conciliadas) == 3
    assert len(resultado.lineas_huerfanas_recibo) == 1
    assert len(resultado.designaciones_no_cobradas) == 1

    # Línea activa
    linea_activa = next(l for l in resultado.lineas_conciliadas if l.secuencia == "016")
    assert linea_activa.estado == EstadoLineaConciliacion.CONCILIADO_EXACTO
    assert linea_activa.es_retroactivo is False

    # Líneas retroactivas
    lineas_retro = [l for l in resultado.lineas_conciliadas if l.secuencia == "018"]
    assert len(lineas_retro) == 2
    assert all(
        l.estado == EstadoLineaConciliacion.CONCILIADO_RETROACTIVO for l in lineas_retro
    )
    assert all(l.es_retroactivo is True for l in lineas_retro)

    # Línea huérfana (Escobar 116 MT 0001)
    linea_huerfana = resultado.lineas_huerfanas_recibo[0]
    assert linea_huerfana.secuencia == "022"
    assert linea_huerfana.liquido_pesos == 232000.0

    # Designación no cobrada (Pilar)
    no_cobrada = resultado.designaciones_no_cobradas[0]
    assert no_cobrada.id_designacion == "desig-no-cobrada-03"


def test_caso_de_uso_conciliar_y_crear_designaciones_huerfanas() -> None:
    recibo_repo = SQLReciboGateway(database_url="sqlite:///:memory:")
    desig_repo = SQLDesignacionDocenteGateway(database_url="sqlite:///:memory:")

    recibo = _crear_recibo_complejo()
    recibo_repo.guardar(recibo)

    conciliar_uc = ConciliarReciboUseCase(
        recibo_repository=recibo_repo,
        designacion_repository=desig_repo,
    )
    crear_uc = CrearDesignacionesDesdeReciboUseCase(
        recibo_repository=recibo_repo,
        designacion_repository=desig_repo,
    )

    # 1. Antes de crear, las 4 líneas son huérfanas porque no hay designaciones previas
    reporte_previo = conciliar_uc.execute("recibo-julio-2026")
    assert len(reporte_previo.lineas_huerfanas_recibo) == 4

    # 2. Auto-crear designaciones desde las huérfanas
    creadas = crear_uc.execute("recibo-julio-2026")
    assert len(creadas) == 4

    # 3. Conciliar nuevamente -> ahora todas están respaldadas
    reporte_post = conciliar_uc.execute("recibo-julio-2026")
    assert len(reporte_post.lineas_huerfanas_recibo) == 0
    assert len(reporte_post.lineas_conciliadas) == 4
    assert reporte_post.total_liquidado_conciliado == 832000.0


def test_normalizacion_periodos_y_fechas() -> None:
    # Formatos válidos con espacios, barras, guiones, 6 dígitos
    assert ConciliadorReciboDocenteService.extraer_anio_mes("07 / 2026") == (2026, 7)
    assert ConciliadorReciboDocenteService.extraer_anio_mes("2026-07") == (2026, 7)
    assert ConciliadorReciboDocenteService.extraer_anio_mes("07-2026") == (2026, 7)
    assert ConciliadorReciboDocenteService.extraer_anio_mes("202607") == (2026, 7)
    assert ConciliadorReciboDocenteService.extraer_anio_mes("072026") == (2026, 7)
    assert (
        ConciliadorReciboDocenteService.normalizar_periodo_a_iso("07 / 2026")
        == "2026-07"
    )


def test_matching_flexible_sin_secuencia_con_datos_reales() -> None:
    # Recibo con 3 líneas en ISFDyT 199 (7 mod, 4 mod, 4 mod) y 1 línea en EEST 3 (2 mod)
    recibo = ReciboSueldo(
        id_recibo="recibo-dgcye-real",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="Docente Real",
            numero_documento="36528392",
            cuil="20-36528392-4",
            mes_pago="07 / 2026",
        ),
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="016",
                periodo_liquidado="07 / 2026",
                fecha_pago="07/08/2026",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=450000.0,
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="017",
                periodo_liquidado="07 / 2026",
                fecha_pago="07/08/2026",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=250000.0,
            ),
            ResumenLiquidoItem(
                establecimiento_codigo="055 MT 0003",
                secuencia="018",
                periodo_liquidado="07 / 2026",
                fecha_pago="07/08/2026",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=150000.0,
            ),
        ],
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 IS 0199", nombre="ISFDyT N° 199"
                ),
                cargo=CargoDetalle(
                    secuencia="016",
                    situacion_revista="PROVISIONAL",
                    carga_horaria=7.0,
                    periodo_liquidado="07 / 2026",
                ),
                liquido_calculado=450000.0,
            ),
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 IS 0199", nombre="ISFDyT N° 199"
                ),
                cargo=CargoDetalle(
                    secuencia="017",
                    situacion_revista="PROVISIONAL",
                    carga_horaria=4.0,
                    periodo_liquidado="07 / 2026",
                ),
                liquido_calculado=250000.0,
            ),
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 MT 0003", nombre="EEST N°3"
                ),
                cargo=CargoDetalle(
                    secuencia="018",
                    situacion_revista="SUPLENTE",
                    carga_horaria=2.0,
                    periodo_liquidado="07 / 2026",
                ),
                liquido_calculado=150000.0,
            ),
        ],
        totales=TotalesConsolidados(total_liquido=850000.0),
    )

    # Designaciones SIN secuencia y con nombres de texto libre
    desig_199_7hs = DesignacionDocente(
        id_designacion="desig-199-7hs",
        docente_cuit="20365283924",
        establecimiento="ISFDyT N°199",
        distrito="TIGRE",
        escuela_numero="",
        secuencia=None,  # Sin secuencia
        cargo_asignatura="Tec. Sup. Ciencias de Datos 3er año",
        revista=SituacionRevista.PROVISIONAL,
        modulos=7,
        vigencia=PeriodoVigencia(fecha_desde=date(2025, 9, 4), fecha_hasta=None),
    )

    desig_199_4hs = DesignacionDocente(
        id_designacion="desig-199-4hs",
        docente_cuit="20365283924",
        establecimiento="ISFDyT N°199",
        distrito="TIGRE",
        escuela_numero="",
        secuencia=None,  # Sin secuencia
        cargo_asignatura="Practica Profesional Modelizado IA",
        revista=SituacionRevista.PROVISIONAL,
        modulos=4,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 4, 21), fecha_hasta=None),
    )

    desig_eest3 = DesignacionDocente(
        id_designacion="desig-eest3-2hs",
        docente_cuit="20365283924",
        establecimiento="Tigre (Marabotto y Benavidez) - EEST N°3",
        distrito="TIGRE",
        escuela_numero="",
        secuencia=None,  # Sin secuencia
        cargo_asignatura="Laboratorio de Sistemas Operativos",
        revista=SituacionRevista.SUPLENTE,
        modulos=2,
        vigencia=PeriodoVigencia(
            fecha_desde=date(2026, 7, 3), fecha_hasta=date(2026, 8, 1)
        ),
    )

    resultado = ConciliadorReciboDocenteService.conciliar(
        recibo=recibo,
        designaciones=[desig_199_7hs, desig_199_4hs, desig_eest3],
    )

    # Las 3 líneas deben quedar perfectamente conciliadas a pesar de no tener secuencia cargada
    assert resultado.total_lineas_recibo == 3
    assert len(resultado.lineas_conciliadas) == 3
    assert len(resultado.lineas_huerfanas_recibo) == 0
    assert resultado.total_liquidado_conciliado == 850000.0
    assert resultado.es_conciliacion_completa is True
