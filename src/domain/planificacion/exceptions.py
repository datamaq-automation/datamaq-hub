"""Domain exceptions for planificacion bounded context."""


class PlanificacionDomainException(Exception):
    """Base exception for planificacion domain."""


class TareaPlanNoEncontradaError(PlanificacionDomainException):
    """Raised when a planning task is not found."""


class PlanNoEncontradoError(PlanificacionDomainException):
    """Raised when a planning file or project plan is not found."""


class CicloEnGrafoPertError(PlanificacionDomainException):
    """Raised when a cycle is detected in the PERT dependency network."""


class TareaPlanInvalidaError(PlanificacionDomainException):
    """Raised when a task definition has invalid parameters."""
