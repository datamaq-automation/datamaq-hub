"""Domain exceptions for empleo bounded context."""


class EmpleoDomainException(Exception):
    """Base exception for empleo domain."""


class PortalEmpleoError(EmpleoDomainException):
    """Raised when an external employment portal fails or is unreachable."""


class PerfilInvalidoError(EmpleoDomainException):
    """Raised when a professional profile is malformed or invalid."""


class OfertaNoEncontradaError(EmpleoDomainException):
    """Raised when an employment offer is not found."""
