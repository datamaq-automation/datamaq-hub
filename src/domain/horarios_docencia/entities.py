"""Entidades de dominio para el subdominio de horarios y compatibilidad de docencia."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    MotivoCese,
    NivelSeveridad,
    PeriodoVigencia,
    SituacionRevista,
    TipoConflicto,
    Turno,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class HorarioBloque:
    """Bloque de horario en un día específico de la semana."""

    dia: DiaSemana
    franja: FranjaHoraria
    turno: Turno


@dataclass(frozen=True)
class CargoDocente:
    """Cargo, espacio curricular o módulos declarados por el docente para una auditoría."""

    id_cargo: str
    establecimiento: str
    distrito: str
    cargo_asignatura: str
    revista: SituacionRevista
    ige: str = ""
    modulos: int = 0
    es_cargo_base: bool = False
    horarios: tuple[HorarioBloque, ...] = field(
        default_factory=tuple[HorarioBloque, ...]
    )
    cupof: str = ""
    secuencia: int | None = None
    observaciones: str = ""
    escuela_numero: str = ""


@dataclass(frozen=True)
class DesignacionDocente:
    """Entidad inmutable que representa una designación, titularidad o suplencia persistida en el tiempo."""

    id_designacion: str
    docente_cuit: str
    establecimiento: str
    distrito: str
    cargo_asignatura: str
    revista: SituacionRevista
    vigencia: PeriodoVigencia
    ige: str = ""
    modulos: int = 0
    es_cargo_base: bool = False
    horarios: tuple[HorarioBloque, ...] = field(
        default_factory=tuple[HorarioBloque, ...]
    )
    motivo_cese: MotivoCese | None = None
    observaciones: str = ""
    cupof: str = ""
    secuencia: int | None = None
    codigo_acto: str = ""
    escuela_numero: str = ""
    reemplaza_a: str = ""
    articulo_licencia: str = ""
    creado_en: datetime = field(default_factory=_now_utc)

    def to_cargo_docente(self) -> CargoDocente:
        """Convierte la designación histórica a un CargoDocente para validación."""
        return CargoDocente(
            id_cargo=self.id_designacion,
            establecimiento=self.establecimiento,
            distrito=self.distrito,
            cargo_asignatura=self.cargo_asignatura,
            revista=self.revista,
            ige=self.ige,
            modulos=self.modulos,
            es_cargo_base=self.es_cargo_base,
            horarios=self.horarios,
            cupof=self.cupof,
            secuencia=self.secuencia,
            observaciones=self.observaciones,
            escuela_numero=self.escuela_numero,
        )


@dataclass(frozen=True)
class DeclaracionHorariaDocente:
    """Declaración jurada horaria consolidada de un docente para auditoría."""

    docente_nombre: str
    cuit: str = ""
    dni: str = ""
    cargos: tuple[CargoDocente, ...] = field(default_factory=tuple[CargoDocente, ...])


@dataclass(frozen=True)
class ConflictoHorario:
    """Detalle de una incompatibilidad, superposición horaria o advertencia estatutaria."""

    tipo: TipoConflicto
    severidad: NivelSeveridad
    dia: DiaSemana | None
    cargos_involucrados: tuple[str, ...] = field(default_factory=tuple[str, ...])
    descripcion: str = ""
    minutos_solapamiento_o_traslado: int = 0


@dataclass(frozen=True)
class ItemGrillaDia:
    """Elemento visual ordenado de la grilla horaria diaria."""

    id_cargo: str
    establecimiento: str
    distrito: str
    cargo_asignatura: str
    revista: SituacionRevista
    franja: FranjaHoraria
    turno: Turno
    modulos: int
    ige: str = ""


@dataclass(frozen=True)
class ResultadoCompatibilidad:
    """Resultado formal del análisis de compatibilidad horaria docente."""

    es_compatible: bool
    total_cargos: int
    total_cargos_base: int
    total_modulos: int
    total_minutos_semanales: int
    cantidad_conflictos: int
    cantidad_incompatibilidades: int = 0
    cantidad_advertencias: int = 0
    tiene_advertencias: bool = False
    conflictos: tuple[ConflictoHorario, ...] = field(
        default_factory=tuple[ConflictoHorario, ...]
    )
    grilla_semanal: dict[str, list[ItemGrillaDia]] = field(
        default_factory=dict[str, list[ItemGrillaDia]]
    )
