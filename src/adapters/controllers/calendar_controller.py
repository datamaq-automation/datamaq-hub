"""Controller for calendar and scheduling operations agnostics of transport layer."""

from datetime import date, datetime

from src.application.dtos.calendar_dto import (
    AvailabilityResponseDTO,
    CalendarEventDTO,
    CreateEventDTO,
    UpdateEventDTO,
)
from src.application.use_cases.check_availability import CheckAvailabilityUseCase
from src.application.use_cases.create_calendar_event import (
    CreateCalendarEventUseCase,
)
from src.application.use_cases.delete_calendar_event import (
    DeleteCalendarEventUseCase,
)
from src.application.use_cases.get_event_detail import GetEventDetailUseCase
from src.application.use_cases.get_upcoming_events import (
    GetUpcomingEventsUseCase,
)
from src.application.use_cases.list_calendar_events import (
    ListCalendarEventsUseCase,
)
from src.application.use_cases.update_calendar_event import (
    UpdateCalendarEventUseCase,
)


class CalendarController:
    """Agnostic controller orchestrating calendar and appointment use cases."""

    def __init__(
        self,
        list_events_use_case: ListCalendarEventsUseCase,
        get_upcoming_events_use_case: GetUpcomingEventsUseCase,
        get_event_detail_use_case: GetEventDetailUseCase,
        create_event_use_case: CreateCalendarEventUseCase,
        update_event_use_case: UpdateCalendarEventUseCase,
        delete_event_use_case: DeleteCalendarEventUseCase,
        check_availability_use_case: CheckAvailabilityUseCase,
    ) -> None:
        self._list_events = list_events_use_case
        self._get_upcoming = get_upcoming_events_use_case
        self._get_event = get_event_detail_use_case
        self._create_event = create_event_use_case
        self._update_event = update_event_use_case
        self._delete_event = delete_event_use_case
        self._check_availability = check_availability_use_case

    def list_events(
        self,
        account: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[CalendarEventDTO]:
        return self._list_events.execute(
            account=account,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def get_upcoming_events(
        self, account: str, days: int = 7, limit: int = 10
    ) -> list[CalendarEventDTO]:
        return self._get_upcoming.execute(account=account, days=days, limit=limit)

    def get_event_detail(self, event_id: str, account: str) -> CalendarEventDTO:
        return self._get_event.execute(event_id=event_id, account=account)

    def create_event(self, dto: CreateEventDTO, account: str) -> CalendarEventDTO:
        return self._create_event.execute(dto=dto, account=account)

    def update_event(
        self, event_id: str, dto: UpdateEventDTO, account: str
    ) -> CalendarEventDTO:
        return self._update_event.execute(event_id=event_id, dto=dto, account=account)

    def delete_event(self, event_id: str, account: str) -> bool:
        return self._delete_event.execute(event_id=event_id, account=account)

    def check_availability(
        self, account: str, target_date: date, slot_duration_minutes: int = 30
    ) -> AvailabilityResponseDTO:
        return self._check_availability.execute(
            account=account,
            target_date=target_date,
            slot_duration_minutes=slot_duration_minutes,
        )
