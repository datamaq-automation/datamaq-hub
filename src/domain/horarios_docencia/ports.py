"""Puertos e interfaces abstractas para el subdominio de horarios de docencia."""

from typing import Protocol

from src.domain.horarios_docencia.entities import (
    DeclaracionHorariaDocente,
    ResultadoCompatibilidad,
)


class HorariosDocenciaValidatorPort(Protocol):
    """Puerto para servicios de validación de compatibilidad horaria."""

    def validar(
        self,
        declaracion: DeclaracionHorariaDocente,
        margen_traslado_minutos: int = 20,
        tope_modulos_semanales: int = 30,
        tope_cargos_base: int = 2,
    ) -> ResultadoCompatibilidad:
        """Audita una declaración horaria docente y retorna el resultado de compatibilidad."""
        ...
