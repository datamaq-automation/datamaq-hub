"""Caso de uso para generar el Briefing Matutino Unificado."""

from collections.abc import Sequence
from datetime import date, datetime, timezone

from src.application.dtos.briefing_dtos import (
    BriefingDiarioResponseDTO,
    ClaseBriefingDTO,
    EventoBriefingDTO,
    ResumenMetricasDTO,
    TareaBriefingDTO,
    TarjetaVencimientoBriefingDTO,
)
from src.domain.calendar.exceptions import CalendarDomainException
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    normalizar_cuit,
)
from src.domain.tareas.ports import FiltrosTarea, TareaRepositoryPort
from src.domain.tareas.value_objects import EstadoTarea, PrioridadTarea
from src.domain.tarjetas.ports import TarjetaRepositoryPort

_DIAS_MAP = {
    0: DiaSemana.LUNES,
    1: DiaSemana.MARTES,
    2: DiaSemana.MIERCOLES,
    3: DiaSemana.JUEVES,
    4: DiaSemana.VIERNES,
    5: DiaSemana.SABADO,
}

_PRIORIDAD_ORDEN = {
    PrioridadTarea.URGENTE: 0,
    PrioridadTarea.ALTA: 1,
    PrioridadTarea.MEDIA: 2,
    PrioridadTarea.BAJA: 3,
}


class ObtenerBriefingDiarioUseCase:
    """Orquesta la obtención consolidada de docencia, tareas y eventos para el briefing."""

    def __init__(
        self,
        designacion_repository: DesignacionDocenteRepositoryPort,
        tarea_repository: TareaRepositoryPort,
        calendar_repository: CalendarRepositoryPort | None = None,
        logger: LoggerPort | None = None,
        tarjeta_repository: TarjetaRepositoryPort | None = None,
    ) -> None:
        self._desig_repo = designacion_repository
        self._tarea_repo = tarea_repository
        self._cal_repo = calendar_repository
        self._logger = logger or NullLogger()
        self._tarjeta_repo = tarjeta_repository

    def execute(
        self,
        docente_cuit: str,
        fecha: date | None = None,
    ) -> BriefingDiarioResponseDTO:
        target_date = fecha or datetime.now(timezone.utc).date()
        cuit_clean = normalizar_cuit(docente_cuit)
        weekday_idx = target_date.weekday()
        dia_semana_enum = _DIAS_MAP.get(weekday_idx)
        dia_semana_nombre = dia_semana_enum.value if dia_semana_enum else "DOMINGO"

        # 1. Clases de docencia del día
        clases_hoy: list[ClaseBriefingDTO] = []
        escuelas_set: set[str] = set()
        total_modulos_dia: float = 0.0

        if dia_semana_enum:
            vigentes = self._desig_repo.obtener_vigentes_en_fecha(
                cuit_clean, target_date
            )
            for desig in vigentes:
                for bloque in desig.horarios:
                    if bloque.dia == dia_semana_enum:
                        clase = ClaseBriefingDTO(
                            id_designacion=desig.id_designacion,
                            establecimiento=desig.establecimiento,
                            distrito=desig.distrito,
                            cargo_asignatura=desig.cargo_asignatura,
                            revista=desig.revista.value,
                            hora_inicio=bloque.franja.hora_inicio,
                            hora_fin=bloque.franja.hora_fin,
                            turno=bloque.turno.value,
                            modulos=desig.modulos,
                            escuela_numero=desig.escuela_numero,
                        )
                        clases_hoy.append(clase)
                        escuelas_set.add(desig.establecimiento)
                        total_modulos_dia += float(desig.modulos)

            # Ordenar cronológicamente por hora_inicio
            clases_hoy.sort(key=lambda c: c.hora_inicio)

        # 2. Tareas pendientes priorizadas
        todas_tareas = self._tarea_repo.listar(FiltrosTarea(docente_cuit=cuit_clean))
        tareas_pendientes = [
            t
            for t in todas_tareas
            if t.estado in (EstadoTarea.PENDIENTE, EstadoTarea.EN_PROGRESO)
        ]

        tareas_pendientes.sort(
            key=lambda t: (
                _PRIORIDAD_ORDEN.get(t.prioridad, 99),
                t.fecha_limite or date(9999, 12, 31),
            )
        )

        tareas_dto: list[TareaBriefingDTO] = []
        tareas_urgentes_count = 0
        for t in tareas_pendientes:
            es_urg = t.prioridad in (PrioridadTarea.URGENTE, PrioridadTarea.ALTA)
            if es_urg:
                tareas_urgentes_count += 1
            es_rec = t.tipo_referencia == "RECIBO" or "reclamo" in t.tags
            tareas_dto.append(
                TareaBriefingDTO(
                    id_tarea=t.id_tarea,
                    titulo=t.titulo,
                    prioridad=t.prioridad.value,
                    categoria=t.categoria.value,
                    fecha_limite=t.fecha_limite,
                    es_urgente=es_urg,
                    es_reclamo=es_rec,
                )
            )

        # 3. Eventos de calendario del día
        eventos_dto: list[EventoBriefingDTO] = []
        if self._cal_repo:
            try:
                start_dt = datetime.combine(
                    target_date, datetime.min.time(), tzinfo=timezone.utc
                )
                end_dt = datetime.combine(
                    target_date, datetime.max.time(), tzinfo=timezone.utc
                )
                evts = self._cal_repo.list_events(
                    account=f"{cuit_clean}@datamaq.com.ar",
                    start_date=start_dt,
                    end_date=end_dt,
                )
                for e in evts:
                    eventos_dto.append(
                        EventoBriefingDTO(
                            id_evento=e.id_evento,
                            titulo=e.titulo,
                            inicio=e.inicio,
                            fin=e.fin,
                            ubicacion=e.ubicacion,
                        )
                    )
            except CalendarDomainException as e:
                self._logger.error("Error al listar eventos de calendario: %s", e)
                # Continúa sin eventos si falla la obtención del calendario.

        # 3b. Alertas de vencimientos de tarjetas de crédito próximos
        tarjetas_vto_dto: list[TarjetaVencimientoBriefingDTO] = []
        if self._tarjeta_repo:
            resumenes = self._tarjeta_repo.obtener_resumenes_vencimiento_cercano(
                target_date
            )
            resumenes.sort(key=lambda r: (r.fecha_vencimiento, r.banco))
            for r in resumenes:
                dias_restantes = (r.fecha_vencimiento - target_date).days
                if -5 <= dias_restantes <= 15:
                    tarjetas_vto_dto.append(
                        TarjetaVencimientoBriefingDTO(
                            banco=r.banco,
                            tarjeta_tipo=r.tarjeta_tipo,
                            tarjeta_categoria=r.tarjeta_categoria,
                            fecha_vencimiento=r.fecha_vencimiento,
                            saldo_pesos=r.saldo_pesos,
                            saldo_dolares=r.saldo_dolares,
                            pago_minimo=r.pago_minimo,
                        )
                    )

        # 4. Métricas
        metricas = ResumenMetricasDTO(
            total_horas_clase=total_modulos_dia,
            cantidad_escuelas=len(escuelas_set),
            total_tareas_pendientes=len(tareas_pendientes),
            tareas_urgentes=tareas_urgentes_count,
            total_reuniones=len(eventos_dto),
            mensajes_no_leidos=0,
        )

        # 5. Generar texto formateado para Telegram
        resumen_telegram = self._formatear_telegram(
            fecha=target_date,
            dia_nombre=dia_semana_nombre,
            clases=clases_hoy,
            tareas=tareas_dto,
            eventos=eventos_dto,
            metricas=metricas,
            tarjetas=tarjetas_vto_dto,
        )

        return BriefingDiarioResponseDTO(
            fecha=target_date,
            dia_semana=dia_semana_nombre,
            docente_cuit=cuit_clean,
            metricas=metricas,
            clases_hoy=clases_hoy,
            tareas_hoy=tareas_dto,
            eventos_hoy=eventos_dto,
            tarjetas_vencimiento=tarjetas_vto_dto,
            resumen_telegram=resumen_telegram,
        )

    def _formatear_telegram(
        self,
        fecha: date,
        dia_nombre: str,
        clases: Sequence[ClaseBriefingDTO],
        tareas: Sequence[TareaBriefingDTO],
        eventos: Sequence[EventoBriefingDTO],
        metricas: ResumenMetricasDTO,
        tarjetas: Sequence[TarjetaVencimientoBriefingDTO] = (),
    ) -> str:
        fecha_str = fecha.strftime("%d/%m/%Y")
        dia_cap = dia_nombre.capitalize()
        lines = [f"🌅 *Buenos días. Tu briefing para hoy {dia_cap} ({fecha_str}):*", ""]

        # Sección Clases
        if clases:
            lines.append(
                f"🏫 *Clases de Hoy ({metricas.total_horas_clase:g} hs en {metricas.cantidad_escuelas} escuelas):*"
            )
            for c in clases:
                lines.append(
                    f"• `{c.hora_inicio} - {c.hora_fin}` | *{c.establecimiento}* — {c.cargo_asignatura} ({c.modulos} hs)"
                )
            lines.append("")
        else:
            lines.append("🏫 *Clases de Hoy:* Sin clases escolares programadas.")
            lines.append("")

        # Sección Tareas
        if tareas:
            top_tareas = tareas[:5]
            lines.append(
                f"📋 *Tareas Prioritarias ({metricas.tareas_urgentes} urgentes / {metricas.total_tareas_pendientes} total):*"
            )
            for t in top_tareas:
                icon = "🔴" if t.es_urgente else "🟡"
                reclam_tag = " `[RECLAMO]`" if t.es_reclamo else ""
                lines.append(f"{icon} *[{t.prioridad}]*{reclam_tag} {t.titulo}")
            if len(tareas) > 5:
                lines.append(f"  _...y {len(tareas) - 5} tareas más._")
            lines.append("")
        else:
            lines.append("📋 *Tareas:* ¡Al día! No tenés pendientes.")
            lines.append("")

        # Sección Eventos
        if eventos:
            lines.append("📅 *Reuniones y Eventos:*")
            for ev in eventos:
                h_ini = ev.inicio.strftime("%H:%M")
                h_fin = ev.fin.strftime("%H:%M")
                ub = f" ({ev.ubicacion})" if ev.ubicacion else ""
                lines.append(f"• `{h_ini} - {h_fin}` | {ev.titulo}{ub}")
            lines.append("")

        # Sección Tarjetas
        if tarjetas:
            grupos: dict[date, list[TarjetaVencimientoBriefingDTO]] = {}
            for t in tarjetas:
                grupos.setdefault(t.fecha_vencimiento, []).append(t)

            lines.append("💳 *Vencimientos de Tarjetas:*")
            for vto_date, list_t in sorted(grupos.items()):
                vto_str = vto_date.strftime("%d/%m/%Y")
                total_pesos = sum(t.saldo_pesos for t in list_t)
                total_usd = sum(t.saldo_dolares for t in list_t)
                total_min = sum(t.pago_minimo for t in list_t)

                usd_str = f" + U$S {total_usd:,.2f}" if total_usd > 0 else ""
                lines.append(
                    f"• ⚠️ *Alerta {vto_str}:* Total `${total_pesos:,.2f}`{usd_str} "
                    f"_(Pago Mínimo: `${total_min:,.2f}`)_"
                )
            lines.append("")

        return "\n".join(lines).strip()
