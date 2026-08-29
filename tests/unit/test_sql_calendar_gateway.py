"""Unit tests for SQLCalendarGateway using SQLite database."""

import uuid
from datetime import datetime, timezone

from src.adapters.gateways.sql_calendar_gateway import SQLCalendarGateway
from src.domain.calendar.entities import CalendarEvent


def test_sql_calendar_gateway_crud_flow(tmp_path) -> None:
    db_name = f"sqlite:///{tmp_path}/test_calendar_{uuid.uuid4().hex[:8]}.db"
    gateway = SQLCalendarGateway(database_url=db_name)
    account = "openclaw@datamaq.com.ar"

    # 1. Get or create calendar
    cal = gateway.get_or_create_default_calendar(account=account)
    assert cal.id_calendario != ""
    assert cal.nombre == "Principal"

    # 2. Create event
    start = datetime(2026, 8, 28, 14, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    end = datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    ev = CalendarEvent(
        id_evento="",
        id_calendario=cal.id_calendario,
        uid=str(uuid.uuid4()),
        titulo="Reunión Inicial",
        inicio=start,
        fin=end,
        descripcion="Kickoff del proyecto",
        ubicacion="Oficina Central",
        todo_el_dia=False,
        estado="CONFIRMED",
        asistentes=["agustin@datamaq.com.ar"],
        url="",
        categorias="Reunión",
        cuenta=account,
    )
    created = gateway.create_event(event=ev, account=account)
    assert created.id_evento != ""
    assert created.titulo == "Reunión Inicial"
    eid = created.id_evento

    # 3. Get event by ID
    fetched = gateway.get_event_by_id(event_id=eid, account=account)
    assert fetched is not None
    assert fetched.titulo == "Reunión Inicial"
    assert fetched.ubicacion == "Oficina Central"

    # 4. List events
    events = gateway.list_events(account=account, start_date=start, end_date=end)
    assert len(events) == 1
    assert events[0].id_evento == eid

    # 5. Update event
    updated_ev = CalendarEvent(
        id_evento=eid,
        id_calendario=cal.id_calendario,
        uid=fetched.uid,
        titulo="Reunión Inicial Reprogramada",
        inicio=start,
        fin=end,
        descripcion="Kickoff extendido",
        ubicacion="Sala Virtual",
        todo_el_dia=False,
        estado="CONFIRMED",
        asistentes=["agustin@datamaq.com.ar", "equipo@datamaq.com.ar"],
        url="https://meet.google.com/test",
        categorias="Reunión",
        cuenta=account,
    )
    updated = gateway.update_event(event=updated_ev, account=account)
    assert updated.titulo == "Reunión Inicial Reprogramada"
    assert updated.ubicacion == "Sala Virtual"

    # 6. Delete event
    deleted = gateway.delete_event(event_id=eid, account=account)
    assert deleted is True

    # 7. Verify deletion
    after_del = gateway.get_event_by_id(event_id=eid, account=account)
    assert after_del is None
