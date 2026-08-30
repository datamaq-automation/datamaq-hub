"""Pruebas unitarias para el caso de uso ObtenerBriefingDiarioUseCase."""

from datetime import date, datetime, timezone

from src.adapters.gateways.sql_calendar_gateway import SQLCalendarGateway
from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.adapters.gateways.sql_tarea_gateway import SQLTareaGateway
from src.adapters.gateways.sql_tarjeta_gateway import SQLTarjetaGateway
from src.application.use_cases.obtener_briefing_diario import (
    ObtenerBriefingDiarioUseCase,
)
from src.domain.calendar.entities import CalendarEvent
from src.domain.horarios_docencia.entities import (
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
)
from src.domain.tareas.entities import Tarea
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    PrioridadTarea,
)
from src.domain.tarjetas.entities import ResumenTarjeta


def test_obtener_briefing_diario_completo() -> None:
    desig_repo = SQLDesignacionDocenteGateway(database_url="sqlite:///:memory:")
    tarea_repo = SQLTareaGateway(database_url="sqlite:///:memory:")
    cal_repo = SQLCalendarGateway(database_url="sqlite:///:memory:")

    cuit = "20-36528392-4"

    # 1. Crear designación docente para los VIERNES (ej. 28/08/2026 es viernes)
    # 2026-08-28 es viernes (weekday = 4)
    target_date = date(2026, 8, 28)

    d1 = DesignacionDocente(
        id_designacion="desig-isfdyt-199",
        docente_cuit="20365283924",
        establecimiento="ISFDyT N°199",
        distrito="TIGRE",
        cargo_asignatura="Ciencia de Datos",
        revista=SituacionRevista.PROVISIONAL,
        modulos=2,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None),
        horarios=(
            HorarioBloque(
                dia=DiaSemana.VIERNES,
                franja=FranjaHoraria(hora_inicio="07:30", hora_fin="09:30"),
                turno=Turno.MANANA,
            ),
        ),
    )
    d2 = DesignacionDocente(
        id_designacion="desig-eest-3",
        docente_cuit="20365283924",
        establecimiento="EEST N°3 Tigre",
        distrito="TIGRE",
        cargo_asignatura="Laboratorio de Sistemas Operativos",
        revista=SituacionRevista.SUPLENTE,
        modulos=2,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None),
        horarios=(
            HorarioBloque(
                dia=DiaSemana.VIERNES,
                franja=FranjaHoraria(hora_inicio="10:00", hora_fin="12:00"),
                turno=Turno.MANANA,
            ),
        ),
    )
    desig_repo.guardar(d1)
    desig_repo.guardar(d2)

    # 2. Crear tareas pendientes
    t1 = Tarea(
        id_tarea="tarea-urg-1",
        titulo="Reclamar liquidación: Tigre LEE",
        prioridad=PrioridadTarea.URGENTE,
        categoria=CategoriaTarea.RECIBOS,
        docente_cuit="20365283924",
        tipo_referencia="RECIBO",
        tags=("reclamo", "sueldo"),
    )
    t2 = Tarea(
        id_tarea="tarea-med-2",
        titulo="Subir notas de parciales al campus",
        prioridad=PrioridadTarea.MEDIA,
        categoria=CategoriaTarea.DOCENCIA,
        docente_cuit="20365283924",
        fecha_limite=date(2026, 8, 30),
    )
    tarea_repo.guardar(t1)
    tarea_repo.guardar(t2)

    # 3. Crear evento de calendario
    cal = cal_repo.get_or_create_default_calendar("20365283924@datamaq.com.ar")
    e1 = CalendarEvent(
        id_evento="evt-reunion-1",
        id_calendario=cal.id_calendario,
        titulo="Reunión de Departamento",
        inicio=datetime(2026, 8, 28, 14, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
        ubicacion="Google Meet",
    )
    cal_repo.create_event(e1, account="20365283924@datamaq.com.ar")

    # 4. Ejecutar Use Case
    use_case = ObtenerBriefingDiarioUseCase(
        designacion_repository=desig_repo,
        tarea_repository=tarea_repo,
        calendar_repository=cal_repo,
    )

    briefing = use_case.execute(docente_cuit=cuit, fecha=target_date)

    # Validar DTO
    assert briefing.fecha == target_date
    assert briefing.dia_semana == "VIERNES"
    assert briefing.docente_cuit == "20365283924"

    # Métricas
    assert briefing.metricas.total_horas_clase == 4.0
    assert briefing.metricas.cantidad_escuelas == 2
    assert briefing.metricas.total_tareas_pendientes == 2
    assert briefing.metricas.tareas_urgentes == 1
    assert briefing.metricas.total_reuniones == 1

    # Clases ordenadas
    assert len(briefing.clases_hoy) == 2
    assert briefing.clases_hoy[0].hora_inicio == "07:30"
    assert briefing.clases_hoy[0].establecimiento == "ISFDyT N°199"
    assert briefing.clases_hoy[1].hora_inicio == "10:00"
    assert briefing.clases_hoy[1].establecimiento == "EEST N°3 Tigre"

    # Tareas ordenadas (urgente primero)
    assert len(briefing.tareas_hoy) == 2
    assert briefing.tareas_hoy[0].id_tarea == "tarea-urg-1"
    assert briefing.tareas_hoy[0].es_urgente is True
    assert briefing.tareas_hoy[0].es_reclamo is True

    # Resumen Telegram generado
    assert "ISFDyT N°199" in briefing.resumen_telegram
    assert "EEST N°3 Tigre" in briefing.resumen_telegram
    assert "Reclamar liquidación: Tigre LEE" in briefing.resumen_telegram
    assert "Reunión de Departamento" in briefing.resumen_telegram


def test_obtener_briefing_diario_con_alertas_tarjetas() -> None:
    desig_repo = SQLDesignacionDocenteGateway(database_url="sqlite:///:memory:")
    tarea_repo = SQLTareaGateway(database_url="sqlite:///:memory:")
    cal_repo = SQLCalendarGateway(database_url="sqlite:///:memory:")
    tarjeta_repo = SQLTarjetaGateway("sqlite:///:memory:")

    cuit = "20-36528392-4"
    target_date = date(2026, 8, 28)

    # Resumen con vencimiento cercano (debe alertar)
    tarjeta_repo.guardar(
        ResumenTarjeta(
            id_resumen="bbva-visa",
            banco="BBVA",
            tarjeta_tipo="VISA",
            tarjeta_categoria="GOLD",
            numero_cuenta="1097452662",
            fecha_cierre=date(2026, 8, 27),
            fecha_vencimiento=date(2026, 9, 7),
            saldo_pesos=144565.27,
            saldo_dolares=0.0,
            pago_minimo=82120.0,
        )
    )
    # Resumen con vencimiento lejano (debe quedar filtrado)
    tarjeta_repo.guardar(
        ResumenTarjeta(
            id_resumen="bapro-visa",
            banco="BAPRO",
            tarjeta_tipo="VISA",
            tarjeta_categoria="CLASSIC",
            numero_cuenta="1151377322",
            fecha_cierre=date(2026, 8, 27),
            fecha_vencimiento=date(2026, 10, 1),
            saldo_pesos=277449.24,
            saldo_dolares=55.78,
            pago_minimo=65922.0,
        )
    )

    use_case = ObtenerBriefingDiarioUseCase(
        designacion_repository=desig_repo,
        tarea_repository=tarea_repo,
        calendar_repository=cal_repo,
        tarjeta_repository=tarjeta_repo,
    )

    briefing = use_case.execute(docente_cuit=cuit, fecha=target_date)

    # Solo el vencimiento dentro del umbral de 15 días debe alertar
    assert len(briefing.tarjetas_vencimiento) == 1
    alerta = briefing.tarjetas_vencimiento[0]
    assert alerta.banco == "BBVA"
    assert alerta.tarjeta_tipo == "VISA"
    assert alerta.tarjeta_categoria == "GOLD"
    assert alerta.fecha_vencimiento == date(2026, 9, 7)
    assert alerta.saldo_pesos == 144565.27
    assert alerta.pago_minimo == 82120.0

    # El texto de Telegram incluye la sección de alertas
    assert "Vencimientos de Tarjetas" in briefing.resumen_telegram
    assert "07/09/2026" in briefing.resumen_telegram
    assert "144,565.27" in briefing.resumen_telegram
    assert "82,120.00" in briefing.resumen_telegram
