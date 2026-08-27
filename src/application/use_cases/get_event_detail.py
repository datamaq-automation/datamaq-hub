"""Use case for retrieving a calendar event by identifier."""

from src.application.dtos.calendar_dto import CalendarEventDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.exceptions import EventNotFoundError
from src.domain.calendar.ports import CalendarRepositoryPort


class GetEventDetailUseCase:
    """Use case to fetch complete details of a calendar event."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(self, event_id: str, account: str) -> CalendarEventDTO:
        event = self.repository.get_event_by_id(event_id=event_id, account=account)
        if not event:
            raise EventNotFoundError(event_id=event_id, account=account)
        return CalendarMapper.to_event_dto(event)
