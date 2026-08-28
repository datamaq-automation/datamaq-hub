"""Excepciones de dominio para el contexto de analítica y telemetría."""


class AnalyticsDomainException(Exception):
    """Excepción base para errores en el dominio de analítica."""


class BudgetLimitViolationException(AnalyticsDomainException):
    """Lanzada cuando una acción o proyección viola los límites duros de presupuesto."""


class InvalidMarketingActionException(AnalyticsDomainException):
    """Lanzada cuando una acción de marketing propuesta por un agente es inválida o insegura."""


class AnomalyThresholdException(AnalyticsDomainException):
    """Lanzada cuando una métrica excede un umbral crítico de anomalía."""
