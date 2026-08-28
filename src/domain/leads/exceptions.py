"""Domain exceptions for leads bounded context."""


class LeadException(Exception):
    """Base domain exception for leads context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LeadValidationException(LeadException):
    """Raised when lead attributes fail validation rules."""
