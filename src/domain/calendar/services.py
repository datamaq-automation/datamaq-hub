"""Domain services for schedule availability checking and interval calculations."""

from datetime import date, datetime, time, timedelta

from src.domain.calendar.entities import CalendarEvent, TimeSlot


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
