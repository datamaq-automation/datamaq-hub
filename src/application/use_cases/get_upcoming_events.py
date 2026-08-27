"""Use case for retrieving upcoming events for the next N days."""

from datetime import datetime, timedelta, timezone

from src.application.dtos.calendar_dto import CalendarEventDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.ports import CalendarRepositoryPort


class GetUpcomingEventsUseCase:
    """Use case to fetch forthcoming events starting from now."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(
        self, account: str, days: int = 7, limit: int = 10
    ) -> list[CalendarEventDTO]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        end_date = now + timedelta(days=days)
        events = self.repository.list_events(
            account=account,
            start_date=now,
            end_date=end_date,
            limit=limit,
        )
        return [CalendarMapper.to_event_dto(e) for e in events]
