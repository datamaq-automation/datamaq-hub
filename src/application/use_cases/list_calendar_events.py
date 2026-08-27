"""Use case for listing calendar events by date range."""

from datetime import datetime

from src.application.dtos.calendar_dto import CalendarEventDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.ports import CalendarRepositoryPort


class ListCalendarEventsUseCase:
    """Use case to list events within an optional date range."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(
        self,
        account: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[CalendarEventDTO]:
        events = self.repository.list_events(
            account=account,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return [CalendarMapper.to_event_dto(e) for e in events]
