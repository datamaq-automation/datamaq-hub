"""Use case for deleting a calendar event."""

from src.domain.calendar.exceptions import EventNotFoundError
from src.domain.calendar.ports import CalendarRepositoryPort


class DeleteCalendarEventUseCase:
    """Use case to remove an event from the calendar."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(self, event_id: str, account: str) -> bool:
        existing = self.repository.get_event_by_id(event_id=event_id, account=account)
        if not existing:
            raise EventNotFoundError(event_id=event_id, account=account)

        return self.repository.delete_event(event_id=event_id, account=account)
