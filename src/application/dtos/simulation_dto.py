"""Salary projection and simulation transfer models."""

from pydantic import BaseModel, ConfigDict, Field

from src.domain.liquidacion.value_objects import (
    NivelCargo,
    SituacionRevista,
    TipoConceptoLiquidacion,
)


class DesignacionInputDTO(BaseModel):
    """Input teaching appointment / position to simulate."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str = Field(description="Sequence identifier, e.g. '016'")
    escuela_codigo: str = Field(description="School identifier code, e.g. 'IS-0199'")
    escuela_nombre: str = Field(description="School name, e.g. 'ISFDyT 199'")
    cargo_nivel: NivelCargo = Field(description="Cargo level: SM or PM")
    carga_horaria: float = Field(gt=0, description="Number of modules/hours, e.g. 4.0")
    situacion_revista: SituacionRevista = Field(
        description="Employment status (PROV., SUP., TIT.)"
    )
    dias_trabajados: float = Field(
        default=30.0, ge=0, le=30, description="Days to liquidate in the month"
    )
    inasistencias_paro: float = Field(
        default=0.0, ge=0, le=30, description="Strike days deducted"
    )
    aplica_suteba: bool = Field(
        default=False, description="Whether union deductions apply"
    )
    aplica_bonificaciones_plenas: bool = Field(
        default=True, description="Whether full bonuses apply"
    )
    periodo_liquidado: str | None = Field(
        default=None,
        pattern=r"^\d{4}(0[1-9]|1[0-2])$",
        description="Period to liquidate YYYYMM (defaults to request projected period)",
        examples=["202608"],
    )
    es_retroactivo: bool = Field(
        default=False,
        description="True if this is a retroactive payment from past months",
    )


class SimulacionSueldoRequestDTO(BaseModel):
    """Payload to request salary projection."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "anios_antiguedad": 4,
                "periodo_proyectado": "202608",
                "tope_bonificaciones_modulos": None,
                "designaciones": [
                    {
                        "secuencia": "016",
                        "escuela_codigo": "IS-0199",
                        "escuela_nombre": "ISFDyT 199",
                        "cargo_nivel": "SM",
                        "carga_horaria": 7.0,
                        "situacion_revista": "PROV.",
                        "dias_trabajados": 30.0,
                        "inasistencias_paro": 0.0,
                        "aplica_suteba": True,
                        "aplica_bonificaciones_plenas": True,
                        "es_retroactivo": False,
                    }
                ],
            }
        },
    )

    anios_antiguedad: int = Field(
        ge=0, le=50, description="Years of teaching seniority", examples=[4]
    )
    periodo_proyectado: str = Field(
        pattern=r"^\d{4}(0[1-9]|1[0-2])$",
        description="Projected period (YYYYMM)",
        examples=["202608"],
    )
    tope_bonificaciones_modulos: float | None = Field(
        default=None,
        ge=0,
        description="Optional override for maximum bonus quota in modules",
        examples=[None],
    )
    designaciones: list[DesignacionInputDTO] = Field(
        min_length=1, description="List of active or retroactive teaching positions"
    )


class ConceptoLiquidadoDTO(BaseModel):
    """Settled salary line item."""

    model_config = ConfigDict(extra="ignore")

    codigo: str
    descripcion: str
    tipo: TipoConceptoLiquidacion
    haberes: float | None = None
    descuentos: float | None = None


class CargoLiquidadoDTO(BaseModel):
    """Settled position outcome."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str
    escuela_codigo: str
    escuela_nombre: str
    cargo_nivel: NivelCargo
    carga_horaria: float
    situacion_revista: SituacionRevista
    periodo_liquidado: str
    dias_trabajados: float
    es_retroactivo: bool
    conceptos: list[ConceptoLiquidadoDTO]
    subtotal_haberes: float
    subtotal_descuentos: float
    liquido: float


class SimulacionSueldoResponseDTO(BaseModel):
    """Consolidated salary simulation response."""

    model_config = ConfigDict(extra="ignore")

    periodo_proyectado: str
    anios_antiguedad: int
    cargos_liquidados: list[CargoLiquidadoDTO]
    total_haberes_remunerativos: float
    total_haberes_no_remunerativos: float
    total_haberes: float
    total_descuentos: float
    total_liquido: float
    total_liquido_regular: float
    total_liquido_retroactivos: float


class ProyeccionEscenarioDTO(BaseModel):
    """Scenario details containing totals."""

    model_config = ConfigDict(extra="ignore")

    total_haberes: float
    total_descuentos: float
    total_liquido: float


class SimulacionSueldoCuitResponseDTO(BaseModel):
    """Consolidated response for CUIT salary projection with regular vs devengado scenarios."""

    model_config = ConfigDict(extra="ignore")

    cuit: str
    docente_nombre: str
    periodo_proyectado: str
    anios_antiguedad: int
    modulos_totales: float
    escenario_base_asegurado: ProyeccionEscenarioDTO
    escenario_devengado_total: ProyeccionEscenarioDTO
    retroactivo_estimado: float
    cargos_liquidados: list[CargoLiquidadoDTO]

