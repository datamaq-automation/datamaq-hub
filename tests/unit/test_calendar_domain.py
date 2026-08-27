"""Unit tests for calendar domain entities, value objects, and services."""

from datetime import date, datetime, time, timezone

import pytest

from src.domain.calendar.entities import CalendarEvent
from src.domain.calendar.exceptions import (
    CalendarDomainException,
    CalendarNotFoundError,
    EventNotFoundError,
    InvalidEventDataError,
)
from src.domain.calendar.services import AvailabilityCheckerService
from src.domain.calendar.value_objects import (
    EventDateTimeInterval,
    EventId,
    EventStatus,
)


def test_event_id_validation():
    eid = EventId("42")
    assert eid.value == "42"

    with pytest.raises(InvalidEventDataError):
        EventId("")


def test_event_date_time_interval_validation():
    start = datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 28, 11, 0, tzinfo=timezone.utc)
    interval = EventDateTimeInterval(inicio=start, fin=end)
    assert interval.duracion_minutos == 60.0
    assert interval.duracion_segundos == 3600.0

    # Invalid interval where end < start
    with pytest.raises(InvalidEventDataError):
        EventDateTimeInterval(inicio=end, fin=start)


def test_calendar_event_immutability():
    start = datetime(2026, 8, 28, 14, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc)
    ev = CalendarEvent(
        id_evento="1",
        id_calendario="1",
        uid="abc-123",
        titulo="Reunión de Avance",
        inicio=start,
        fin=end,
        descripcion="Seguimiento semanal",
        ubicacion="Google Meet",
        todo_el_dia=False,
        estado=EventStatus.CONFIRMED.value,
        asistentes=["agustin@datamaq.com.ar", "cliente@empresa.com"],
        url="https://meet.google.com/xyz",
        categorias="Reunión",
        cuenta="openclaw@datamaq.com.ar",
    )
    assert ev.titulo == "Reunión de Avance"
    assert len(ev.asistentes) == 2
    assert ev.estado == "CONFIRMED"


def test_availability_checker_service():
    target_date = date(2026, 8, 28)
    # Event from 10:00 to 11:00 (tz-naive in service)
    ev = CalendarEvent(
        id_evento="1",
        id_calendario="1",
        uid="ev-1",
        titulo="Llamada con Proveedor",
        inicio=datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc).replace(tzinfo=None),
        fin=datetime(2026, 8, 28, 11, 0, tzinfo=timezone.utc).replace(tzinfo=None),
        estado="CONFIRMED",
        cuenta="openclaw@datamaq.com.ar",
    )

    slots = AvailabilityCheckerService.calculate_free_slots(
        target_date=target_date,
        events=[ev],
        work_start_time=time(9, 0),
        work_end_time=time(12, 0),
        slot_duration_minutes=30,
    )

    # From 09:00 to 12:00 (3 hours = 6 slots of 30 min)
    assert len(slots) == 6

    # 09:00 - 09:30 -> True
    assert slots[0].disponible is True
    # 09:30 - 10:00 -> True
    assert slots[1].disponible is True
    # 10:00 - 10:30 -> False (Overlap with ev)
    assert slots[2].disponible is False
    assert slots[2].motivo == "Llamada con Proveedor"
    # 10:30 - 11:00 -> False (Overlap with ev)
    assert slots[3].disponible is False
    # 11:00 - 11:30 -> True
    assert slots[4].disponible is True
    # 11:30 - 12:00 -> True
    assert slots[5].disponible is True


def test_calendar_exceptions():
    exc = EventNotFoundError("501", "openclaw@datamaq.com.ar")
    assert "501" in exc.message

    exc2 = CalendarNotFoundError("1", "openclaw@datamaq.com.ar")
    assert "1" in exc2.message

    exc3 = CalendarDomainException("Error general")
    assert str(exc3) == "Error general"
