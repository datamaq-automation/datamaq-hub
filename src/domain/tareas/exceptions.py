"""Excepciones de dominio para el subdominio de tareas."""


class TareaDomainException(Exception):
    """Excepción base del dominio de tareas."""


class TareaNoEncontradaException(TareaDomainException):
    """Lanzada cuando una tarea solicitada no existe."""


class TareaInvalidaException(TareaDomainException):
    """Lanzada cuando los datos de una tarea no son válidos."""
