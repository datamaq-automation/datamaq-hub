"""Salary receipt transfer models and DTOs."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


class AgenteDTO(BaseModel):
    """Employee data DTO."""

    model_config = ConfigDict(extra="ignore")

    nombre_completo: str = Field(description="Full name")
    tipo_documento: str = Field(description="Document type")
    numero_documento: str = Field(description="Document number")
    sexo: str | None = Field(default=None, description="Gender")
    cuil: str = Field(description="CUIL")
    mes_pago: str = Field(description="Payment period")


class EmpleadorDTO(BaseModel):
    """Employer data DTO."""

    model_config = ConfigDict(extra="ignore")

    organismo_o_empresa: str = Field(description="Organization name")
    dependencia: str | None = Field(default=None, description="Department")
    cuit: str | None = Field(default=None, description="Employer CUIT")


class ResumenLiquidoItemDTO(BaseModel):
    """Summary table row DTO."""

    model_config = ConfigDict(extra="ignore")

    establecimiento_codigo: str
    secuencia: str
    periodo_liquidado: str
    fecha_pago: str
    orden_pago_codigo: str
    orden_pago_descripcion: str
    liquido_pesos: float


class EstablecimientoDTO(BaseModel):
    """School / Establishment DTO."""

    model_config = ConfigDict(extra="ignore")

    codigo: str | None = None
    distrito: str | None = None
    categoria: str | None = None
    desfavorabilidad: int | None = 0
    secciones: int | None = 0
    es_carcel: bool | None = False
    doble_escolaridad: bool | None = False
    turnos: int | None = 1
    nombre: str | None = None


class CargoDTO(BaseModel):
    """Position attributes DTO."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str
    situacion_revista: str | None = None
    cargo_real: str | None = None
    carga_horaria: float | None = None
    antiguedad_anios: int | None = None
    dias_trabajados: float | None = 30.0
    inasistencias: float | None = 0.0
    periodo_liquidado: str | None = None
    orden_pago: str | None = None


class ConceptoItemDTO(BaseModel):
    """Concept line item DTO."""

    model_config = ConfigDict(extra="ignore")

    codigo: str
    descripcion: str
    haberes: float | None = None
    descuentos: float | None = None
    tipo: TipoConcepto


class LiquidacionSecuenciaDTO(BaseModel):
    """Sequence settlement DTO."""

    model_config = ConfigDict(extra="ignore")

    establecimiento: EstablecimientoDTO
    cargo: CargoDTO
    conceptos: list[ConceptoItemDTO]
    subtotal_haberes: float
    subtotal_descuentos: float
    liquido_calculado: float


class TotalesConsolidadosDTO(BaseModel):
    """Consolidated totals DTO."""

    model_config = ConfigDict(extra="ignore")

    total_haberes_remunerativos: float
    total_haberes_no_remunerativos: float
    total_haberes: float
    total_descuentos: float
    total_liquido: float


class ReceiptResponseDTO(BaseModel):
    """Top-level salary receipt response DTO."""

    model_config = ConfigDict(extra="ignore")

    tipo_recibo: TipoRecibo
    empleador: EmpleadorDTO
    agente: AgenteDTO
    id_recibo: str | None = Field(
        default=None, description="Identificador único del recibo persistido"
    )
    resumen_liquidos: list[ResumenLiquidoItemDTO] = Field(
        default_factory=list[ResumenLiquidoItemDTO]
    )
    liquidaciones: list[LiquidacionSecuenciaDTO] = Field(
        default_factory=list[LiquidacionSecuenciaDTO]
    )
    totales: TotalesConsolidadosDTO
    metadata: dict[str, Any] = Field(default_factory=dict[str, Any])
