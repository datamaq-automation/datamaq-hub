"""Unit tests for calendar use cases."""

from datetime import date, datetime, timezone

import pytest

from src.application.dtos.calendar_dto import CreateEventDTO, UpdateEventDTO
from src.application.use_cases.check_availability import CheckAvailabilityUseCase
from src.application.use_cases.create_calendar_event import (
    CreateCalendarEventUseCase,
)
from src.application.use_cases.delete_calendar_event import (
    DeleteCalendarEventUseCase,
)
from src.application.use_cases.get_event_detail import GetEventDetailUseCase
from src.application.use_cases.list_calendar_events import (
    ListCalendarEventsUseCase,
)
from src.application.use_cases.update_calendar_event import (
    UpdateCalendarEventUseCase,
)
from src.domain.calendar.entities import Calendar, CalendarEvent
from src.domain.calendar.exceptions import EventNotFoundError
from src.domain.calendar.ports import CalendarRepositoryPort


class FakeCalendarRepository(CalendarRepositoryPort):
    """In-memory mock repository implementing CalendarRepositoryPort."""

    def __init__(self) -> None:
        self.events: dict[str, CalendarEvent] = {
            "1": CalendarEvent(
                id_evento="1",
                id_calendario="1",
                uid="uid-1",
                titulo="Reunión de Planificación",
                inicio=datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc),
                fin=datetime(2026, 8, 28, 11, 0, tzinfo=timezone.utc),
                descripcion="Plan mensual",
                ubicacion="Sala Principal",
                todo_el_dia=False,
                estado="CONFIRMED",
                asistentes=["agustin@datamaq.com.ar"],
                url="",
                categorias="Plan",
                cuenta="openclaw@datamaq.com.ar",
            )
        }
        self.next_id = 2

    def get_or_create_default_calendar(self, account: str) -> Calendar:
        return Calendar(
            id_calendario="1",
            nombre="Principal",
            color="#0288D1",
            cuenta=account,
        )

    def list_events(
        self,
        account: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[CalendarEvent]:
        def _to_naive(dt: datetime | None) -> datetime | None:
            if dt is None:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

        res = [e for e in self.events.values() if e.cuenta == account]
        s_date = _to_naive(start_date)
        e_date = _to_naive(end_date)
        if s_date is not None:
            res = [e for e in res if _to_naive(e.fin) >= s_date]
        if e_date is not None:
            res = [e for e in res if _to_naive(e.inicio) <= e_date]
        return sorted(res, key=lambda x: _to_naive(x.inicio))[:limit]

    def get_event_by_id(self, event_id: str, account: str) -> CalendarEvent | None:
        e = self.events.get(event_id)
        if e and e.cuenta == account:
            return e
        return None

    def create_event(self, event: CalendarEvent, account: str) -> CalendarEvent:
        eid = str(self.next_id)
        self.next_id += 1
        new_event = CalendarEvent(
            id_evento=eid,
            id_calendario=event.id_calendario,
            uid=event.uid or f"uid-{eid}",
            titulo=event.titulo,
            inicio=event.inicio,
            fin=event.fin,
            descripcion=event.descripcion,
            ubicacion=event.ubicacion,
            todo_el_dia=event.todo_el_dia,
            estado=event.estado,
            asistentes=event.asistentes,
            url=event.url,
            categorias=event.categorias,
            cuenta=account,
        )
        self.events[eid] = new_event
        return new_event

    def update_event(self, event: CalendarEvent, account: str) -> CalendarEvent:
        self.events[event.id_evento] = event
        return event

    def delete_event(self, event_id: str, account: str) -> bool:
        if event_id in self.events and self.events[event_id].cuenta == account:
            del self.events[event_id]
            return True
        return False


def test_calendar_use_cases_crud_and_availability():
    repo = FakeCalendarRepository()
    account = "openclaw@datamaq.com.ar"

    # 1. List events
    list_uc = ListCalendarEventsUseCase(repository=repo)
    events = list_uc.execute(account=account)
    assert len(events) == 1
    assert events[0].titulo == "Reunión de Planificación"

    # 2. Get event detail
    detail_uc = GetEventDetailUseCase(repository=repo)
    detail = detail_uc.execute(event_id="1", account=account)
    assert detail.id_evento == "1"
    assert detail.ubicacion == "Sala Principal"

    # 3. Create event
    create_uc = CreateCalendarEventUseCase(repository=repo)
    new_dto = CreateEventDTO(
        titulo="Demo Telemetría",
        inicio=datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 8, 28, 16, 0, tzinfo=timezone.utc),
        descripcion="Demo con cliente",
        ubicacion="Google Meet",
        asistentes=["cliente@empresa.com"],
    )
    created = create_uc.execute(dto=new_dto, account=account)
    assert created.id_evento == "2"
    assert created.titulo == "Demo Telemetría"

    # 4. Check availability
    avail_uc = CheckAvailabilityUseCase(repository=repo)
    avail = avail_uc.execute(
        account=account, target_date=date(2026, 8, 28), slot_duration_minutes=60
    )
    assert avail.fecha == "2026-08-28"
    assert len(avail.bloques) > 0

    # 5. Update event
    update_uc = UpdateCalendarEventUseCase(repository=repo)
    upd_dto = UpdateEventDTO(
        titulo="Demo Telemetría Extendida",
        ubicacion="Meet y Presencial",
    )
    updated = update_uc.execute(event_id="2", dto=upd_dto, account=account)
    assert updated.titulo == "Demo Telemetría Extendida"
    assert updated.ubicacion == "Meet y Presencial"

    # 6. Delete event
    delete_uc = DeleteCalendarEventUseCase(repository=repo)
    deleted = delete_uc.execute(event_id="2", account=account)
    assert deleted is True

    with pytest.raises(EventNotFoundError):
        detail_uc.execute(event_id="2", account=account)
