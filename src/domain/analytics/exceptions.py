"""Excepciones de dominio para el contexto de analítica y telemetría."""


class AnalyticsDomainException(Exception):
    """Excepción base para errores en el dominio de analítica."""


class BudgetLimitViolationException(AnalyticsDomainException):
    """Lanzada cuando una acción o proyección viola los límites duros de presupuesto."""


class InvalidMarketingActionException(AnalyticsDomainException):
    """Lanzada cuando una acción de marketing propuesta por un agente es inválida o insegura."""


class AnomalyThresholdException(AnalyticsDomainException):
    """Lanzada cuando una métrica excede un umbral crítico de anomalía."""


class FichaGoogleException(AnalyticsDomainException):
    """Excepción base para errores sobre la ficha de Google Business Profile."""


class PublicacionFichaInvalidaException(FichaGoogleException):
    """Lanzada cuando una publicación propuesta para la ficha viola las políticas del negocio."""


class RespuestaResenaInvalidaException(FichaGoogleException):
    """Lanzada cuando la respuesta a una reseña es inválida o sobrescribiría una existente."""
