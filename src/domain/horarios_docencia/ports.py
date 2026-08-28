"""Puertos e interfaces abstractas para el subdominio de horarios de docencia."""

from datetime import date
from typing import Protocol

from src.domain.horarios_docencia.entities import (
    DeclaracionHorariaDocente,
    DesignacionDocente,
    ResultadoCompatibilidad,
)
from src.domain.horarios_docencia.value_objects import MotivoCese


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


class DesignacionDocenteRepositoryPort(Protocol):
    """Puerto de persistencia inmutable / temporal para designaciones y suplencias docentes."""

    def guardar(self, designacion: DesignacionDocente) -> DesignacionDocente:
        """Persiste una nueva designación o suplencia docente de forma inmutable."""
        ...

    def obtener_por_id(self, id_designacion: str) -> DesignacionDocente | None:
        """Busca una designación específica por su ID único."""
        ...

    def obtener_vigentes_en_fecha(
        self, docente_cuit: str, fecha: date
    ) -> tuple[DesignacionDocente, ...]:
        """Recupera todas las designaciones que estaban activas en una fecha determinada."""
        ...

    def obtener_historial(self, docente_cuit: str) -> tuple[DesignacionDocente, ...]:
        """Recupera la línea de tiempo histórica completa de todas las designaciones del docente."""
        ...

    def cerrar_vigencia(
        self, id_designacion: str, fecha_hasta: date, motivo: MotivoCese
    ) -> DesignacionDocente | None:
        """Sella la fecha de fin y el motivo de cese de una designación sin borrarla ni alterar su histórico."""
        ...

    def listar(
        self,
        docente_cuit: str | None = None,
        vigentes_al: date | None = None,
        establecimiento: str | None = None,
        distrito: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[DesignacionDocente, ...]:
        """Lista designaciones docentes con filtros opcionales y paginación."""
        ...

    def actualizar(self, designacion: DesignacionDocente) -> DesignacionDocente | None:
        """Actualiza una designación existente por su ID."""
        ...

    def eliminar(self, id_designacion: str) -> bool:
        """Elimina físicamente una designación por su ID (ej. registro accidental)."""
        ...
