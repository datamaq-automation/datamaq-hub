"""Entidades de dominio para el subdominio de horarios y compatibilidad de docencia."""

from dataclasses import dataclass, field

from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    NivelSeveridad,
    SituacionRevista,
    TipoConflicto,
    Turno,
)


@dataclass(frozen=True)
class HorarioBloque:
    """Bloque de horario en un día específico de la semana."""

    dia: DiaSemana
    franja: FranjaHoraria
    turno: Turno


@dataclass(frozen=True)
class CargoDocente:
    """Cargo, espacio curricular o módulos declarados por el docente."""

    id_cargo: str
    establecimiento: str
    distrito: str
    cargo_asignatura: str
    revista: SituacionRevista
    modulos: int = 0
    es_cargo_base: bool = False
    horarios: tuple[HorarioBloque, ...] = field(
        default_factory=tuple[HorarioBloque, ...]
    )


@dataclass(frozen=True)
class DeclaracionHorariaDocente:
    """Declaración jurada horaria consolidada de un docente."""

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


@dataclass(frozen=True)
class ResultadoCompatibilidad:
    """Resultado formal del análisis de compatibilidad horaria docente."""

    es_compatible: bool
    total_cargos: int
    total_cargos_base: int
    total_modulos: int
    total_minutos_semanales: int
    cantidad_conflictos: int
    conflictos: tuple[ConflictoHorario, ...] = field(
        default_factory=tuple[ConflictoHorario, ...]
    )
    grilla_semanal: dict[str, list[ItemGrillaDia]] = field(
        default_factory=dict[str, list[ItemGrillaDia]]
    )
