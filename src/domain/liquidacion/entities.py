"""Domain entities for salary settlement and projection domain."""

from dataclasses import dataclass, field

from src.domain.liquidacion.value_objects import (
    NivelCargo,
    SituacionRevista,
    TipoConceptoLiquidacion,
)


@dataclass(frozen=True)
class ConceptoLiquidado:
    """Individual line item concept in a salary settlement."""

    codigo: str
    descripcion: str
    tipo: TipoConceptoLiquidacion
    haberes: float | None = None
    descuentos: float | None = None


@dataclass(frozen=True)
class DesignacionDocente:
    """Teaching position assignment / appointment details."""

    secuencia: str
    escuela_codigo: str
    escuela_nombre: str
    cargo_nivel: NivelCargo
    carga_horaria: float
    situacion_revista: SituacionRevista
    dias_trabajados: float
    periodo_liquidado: str
    inasistencias_paro: float = 0.0
    aplica_suteba: bool = False
    aplica_bonificaciones_plenas: bool = True
    es_retroactivo: bool = False
    fecha_inicio: str | None = None
    fecha_fin: str | None = None


@dataclass(frozen=True)
class LiquidacionCargoResultado:
    """Settlement outcome for a single teaching position sequence."""

    secuencia: str
    escuela_codigo: str
    escuela_nombre: str
    cargo_nivel: NivelCargo
    carga_horaria: float
    situacion_revista: SituacionRevista
    periodo_liquidado: str
    dias_trabajados: float
    es_retroactivo: bool
    conceptos: tuple[ConceptoLiquidado, ...] = field(
        default_factory=tuple[ConceptoLiquidado, ...]
    )
    subtotal_haberes: float = 0.0
    subtotal_descuentos: float = 0.0
    liquido: float = 0.0


@dataclass(frozen=True)
class LiquidacionConsolidadaResultado:
    """Consolidated salary projection result."""

    periodo_proyectado: str
    anios_antiguedad: int
    cargos_liquidados: tuple[LiquidacionCargoResultado, ...] = field(
        default_factory=tuple[LiquidacionCargoResultado, ...]
    )
    total_haberes_remunerativos: float = 0.0
    total_haberes_no_remunerativos: float = 0.0
    total_haberes: float = 0.0
    total_descuentos: float = 0.0
    total_liquido: float = 0.0
    total_liquido_regular: float = 0.0
    total_liquido_retroactivos: float = 0.0
