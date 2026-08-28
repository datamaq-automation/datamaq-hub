"""Excepciones de dominio para el subdominio de horarios y cargos de docencia."""


class HorariosDocenciaDomainException(Exception):
    """Excepción base del dominio de horarios y compatibilidad docente."""


class FranjaHorariaInvalidaException(HorariosDocenciaDomainException):
    """Lanzada cuando un horario no cumple el formato HH:MM o hora_inicio >= hora_fin."""


class HorarioDocenciaInvalidoException(HorariosDocenciaDomainException):
    """Lanzada cuando los datos de un cargo u horario son inválidos."""


class IncompatibilidadHorariaCriticaException(HorariosDocenciaDomainException):
    """Lanzada cuando se intenta registrar un cargo con superposición horaria crítica sin forzar."""

    def __init__(self, mensaje: str, conflictos: tuple[object, ...] = ()) -> None:
        super().__init__(mensaje)
        self.conflictos = conflictos
