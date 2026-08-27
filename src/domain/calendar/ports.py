"""Port protocols for calendar repository and storage."""

from datetime import datetime
from typing import Protocol

from src.domain.calendar.entities import Calendar, CalendarEvent


class CalendarRepositoryPort(Protocol):
    """Abstract port for calendar and event persistence operations."""

    def get_or_create_default_calendar(self, account: str) -> Calendar:
        """Retrieves or creates the primary default calendar for an account."""
        ...

    def list_events(
        self,
        account: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[CalendarEvent]:
        """Lists events within a date range for a specific account."""
        ...

    def get_event_by_id(self, event_id: str, account: str) -> CalendarEvent | None:
        """Retrieves a single calendar event by identifier."""
        ...

    def create_event(self, event: CalendarEvent, account: str) -> CalendarEvent:
        """Persists a new calendar event returning entity with generated ID and UID."""
        ...

    def update_event(self, event: CalendarEvent, account: str) -> CalendarEvent:
        """Updates an existing calendar event."""
        ...

    def delete_event(self, event_id: str, account: str) -> bool:
        """Deletes a calendar event."""
        ...
