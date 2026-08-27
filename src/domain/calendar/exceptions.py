"""Domain exceptions for calendar and scheduling bounded context."""


class CalendarDomainException(Exception):
    """Base exception for all calendar domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EventNotFoundError(CalendarDomainException):
    """Raised when a calendar event is not found."""

    def __init__(self, event_id: str, account: str) -> None:
        super().__init__(
            f"No se encontró el evento '{event_id}' para la cuenta '{account}'."
        )
        self.event_id = event_id
        self.account = account


class CalendarNotFoundError(CalendarDomainException):
    """Raised when a calendar is not found."""

    def __init__(self, calendar_id: str, account: str) -> None:
        super().__init__(
            f"No se encontró el calendario '{calendar_id}' para la cuenta '{account}'."
        )
        self.calendar_id = calendar_id
        self.account = account


class InvalidEventDataError(CalendarDomainException):
    """Raised when event interval or parameters are invalid."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Datos de evento inválidos: {reason}")
        self.reason = reason


class ScheduleConflictError(CalendarDomainException):
    """Raised when an event conflicts with existing appointments."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Conflicto de agenda: {message}")
