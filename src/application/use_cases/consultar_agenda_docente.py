"""Use case for querying unified teaching and personal calendar schedule."""

from datetime import date, datetime, time

from src.application.dtos.calendar_dto import CalendarEventDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.ports import CalendarRepositoryPort


class ConsultarAgendaDocenteUseCase:
    """Use case to fetch unified schedule within date range."""

    def __init__(self, calendar_repo: CalendarRepositoryPort) -> None:
        self.calendar_repo = calendar_repo

    def execute(
        self,
        account: str,
        fecha_desde: date,
        fecha_hasta: date,
        solo_docencia: bool = False,
    ) -> list[CalendarEventDTO]:
        dt_from = datetime.combine(fecha_desde, time(0, 0))
        dt_to = datetime.combine(fecha_hasta, time(23, 59, 59))

        events = self.calendar_repo.list_events(
            account=account,
            start_date=dt_from,
            end_date=dt_to,
            limit=200,
        )

        if solo_docencia:
            events = [e for e in events if "docencia" in e.categorias.lower()]

        return [CalendarMapper.to_event_dto(e) for e in events]
