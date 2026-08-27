"""Domain services for schedule availability checking and interval calculations."""

from datetime import date, datetime, time, timedelta

from src.domain.calendar.entities import CalendarEvent, TimeSlot
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import DiaSemana

_DIA_SEMANA_TO_WEEKDAY: dict[DiaSemana, int] = {
    DiaSemana.LUNES: 0,
    DiaSemana.MARTES: 1,
    DiaSemana.MIERCOLES: 2,
    DiaSemana.JUEVES: 3,
    DiaSemana.VIERNES: 4,
    DiaSemana.SABADO: 5,
}


class AvailabilityCheckerService:
    """Pure domain service for evaluating schedule availability and free time slots."""

    @staticmethod
    def calculate_free_slots(
        target_date: date,
        events: list[CalendarEvent],
        work_start_time: time = time(8, 0),
        work_end_time: time = time(18, 0),
        slot_duration_minutes: int = 30,
    ) -> list[TimeSlot]:
        """Calculates free and busy time slots for a given day within working hours."""
        slots: list[TimeSlot] = []

        day_start = datetime.combine(target_date, work_start_time)
        day_end = datetime.combine(target_date, work_end_time)
        step = timedelta(minutes=slot_duration_minutes)

        current_start = day_start
        while current_start + step <= day_end:
            current_end = current_start + step

            # Check overlap with any active event
            overlapping_event: CalendarEvent | None = None
            for ev in events:
                if ev.estado.upper() == "CANCELLED":
                    continue

                # Normalize naive/aware datetime comparisons
                ev_start = (
                    ev.inicio.replace(tzinfo=None)
                    if ev.inicio.tzinfo is not None
                    else ev.inicio
                )
                ev_end = (
                    ev.fin.replace(tzinfo=None) if ev.fin.tzinfo is not None else ev.fin
                )

                # Overlap condition: not (end <= ev_start or start >= ev_end)
                if not (current_end <= ev_start or current_start >= ev_end):
                    overlapping_event = ev
                    break

            if overlapping_event is not None:
                slots.append(
                    TimeSlot(
                        inicio=current_start,
                        fin=current_end,
                        disponible=False,
                        motivo=overlapping_event.titulo or "Ocupado",
                    )
                )
            else:
                slots.append(
                    TimeSlot(
                        inicio=current_start,
                        fin=current_end,
                        disponible=True,
                        motivo="Disponible",
                    )
                )

            current_start = current_end

        return slots


class DocenciaEventProjectorService:
    """Pure domain service for projecting teaching positions into calendar events."""

    @staticmethod
    def project_events(
        designaciones: list[DesignacionDocente],
        fecha_desde: date,
        fecha_hasta: date,
        calendar_id: str = "1",
        account: str = "",
    ) -> list[CalendarEvent]:
        """Generates concrete CalendarEvent instances for all active teaching blocks within range."""
        projected_events: list[CalendarEvent] = []

        if fecha_desde > fecha_hasta:
            return []

        # Iterate day by day in range
        current_date = fecha_desde
        one_day = timedelta(days=1)

        while current_date <= fecha_hasta:
            weekday = current_date.weekday()

            for desig in designaciones:
                # Check active validity period
                if not desig.vigencia.esta_vigente_en(current_date):
                    continue

                for bloque in desig.horarios:
                    mapped_weekday = _DIA_SEMANA_TO_WEEKDAY.get(bloque.dia)
                    if mapped_weekday == weekday:
                        try:
                            h_ini, m_ini = map(
                                int, bloque.franja.hora_inicio.split(":")
                            )
                            h_fin, m_fin = map(int, bloque.franja.hora_fin.split(":"))
                            t_ini = time(h_ini, m_ini)
                            t_fin = time(h_fin, m_fin)
                        except (ValueError, AttributeError):
                            continue

                        dt_inicio = datetime.combine(current_date, t_ini)
                        dt_fin = datetime.combine(current_date, t_fin)

                        clean_hora = bloque.franja.hora_inicio.replace(":", "")
                        uid = f"doc-{desig.id_designacion}-{current_date.isoformat()}-{clean_hora}"
                        titulo = (
                            f"Clase: {desig.cargo_asignatura} - {desig.establecimiento}"
                        )
                        descripcion = (
                            f"Designación: {desig.id_designacion} | Módulos: {desig.modulos} | "
                            f"Revista: {desig.revista.value} | Distrito: {desig.distrito} | "
                            f"Turno: {bloque.turno.value} | IGE: {desig.ige}"
                        )
                        ubicacion = f"{desig.establecimiento}, {desig.distrito}"

                        event = CalendarEvent(
                            id_evento="",
                            id_calendario=calendar_id,
                            uid=uid,
                            titulo=titulo,
                            inicio=dt_inicio,
                            fin=dt_fin,
                            descripcion=descripcion,
                            ubicacion=ubicacion,
                            todo_el_dia=False,
                            estado="CONFIRMED",
                            asistentes=[],
                            url="",
                            categorias="Docencia",
                            cuenta=account,
                        )
                        projected_events.append(event)

            current_date += one_day

        return projected_events
