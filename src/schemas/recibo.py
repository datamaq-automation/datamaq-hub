"""Pydantic v2 schemas for salary receipt (Recibo de Sueldo) data extraction."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TipoConcepto(str, Enum):
    """Classification for receipt line items / concepts."""

    REMUNERATIVO = "remunerativo"
    NO_REMUNERATIVO = "no_remunerativo"
    DESCUENTO = "descuento"


class TipoRecibo(str, Enum):
    """Type / Origin format of receipt."""

    DGCYE_PBA = "DGCYE_PBA"
    GENERICO = "GENERICO"


class AgenteSchema(BaseModel):
    """Employee / Agent personal identification data."""

    model_config = ConfigDict(extra="ignore")

    nombre_completo: str = Field(description="Full name of employee / agent")
    tipo_documento: str = Field(
        default="DNI", description="Document type (DNI, LC, CI, etc.)"
    )
    numero_documento: str = Field(description="Document number (cleaned without dots)")
    sexo: str | None = Field(default=None, description="Gender indicator (M/F/X)")
    cuil: str = Field(description="CUIL / CUIT number formatted or raw")
    mes_pago: str = Field(description="Payment period / month (e.g. '07 / 2026')")


class EmpleadorSchema(BaseModel):
    """Employer / Organization details."""

    model_config = ConfigDict(extra="ignore")

    organismo_o_empresa: str = Field(
        description="Name of employer or governmental organism"
    )
    dependencia: str | None = Field(default=None, description="Branch or dependency")
    cuit: str | None = Field(default=None, description="Employer CUIT")


class ResumenLiquidoItem(BaseModel):
    """Line item in consolidated net salary summary table (e.g. DGCyE summary page)."""

    model_config = ConfigDict(extra="ignore")

    establecimiento_codigo: str = Field(description="Establishment code (e.g. '00199')")
    secuencia: str = Field(description="Sequence / position number (e.g. '016')")
    periodo_liquidado: str = Field(description="Settlement period (e.g. '07 / 2026')")
    fecha_pago: str = Field(description="Payment date (e.g. '06/08/2026')")
    orden_pago_codigo: str = Field(description="Payment order code (e.g. '1')")
    orden_pago_descripcion: str = Field(
        description="Payment order description (e.g. 'SUELDO')"
    )
    liquido_pesos: float = Field(description="Net amount paid in ARS")


class EstablecimientoDetalle(BaseModel):
    """School / Establishment details for a given position."""

    model_config = ConfigDict(extra="ignore")

    codigo: str | None = Field(default=None, description="Establishment code")
    distrito: str | None = Field(
        default=None, description="District name and code (e.g. '05-TIGRE')"
    )
    categoria: str | None = Field(default=None, description="Category (e.g. 'IS-0199')")
    desfavorabilidad: int | None = Field(
        default=0, description="Rurality/hardship percentage"
    )
    secciones: int | None = Field(default=0, description="Number of sections")
    es_carcel: bool | None = Field(
        default=False, description="Whether establishment is inside a prison"
    )
    doble_escolaridad: bool | None = Field(
        default=False, description="Full day / double schooling"
    )
    turnos: int | None = Field(default=1, description="Number of shifts")
    nombre: str | None = Field(
        default=None, description="Establishment descriptive name"
    )


class CargoDetalle(BaseModel):
    """Position / Cargo attributes."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str = Field(description="Sequence number of the position")
    situacion_revista: str | None = Field(
        default=None, description="Tenure status: TIT, PROV, SUP, etc."
    )
    cargo_real: str | None = Field(
        default=None, description="Job title / role (e.g. 'PROFESOR')"
    )
    carga_horaria: float | None = Field(
        default=None, description="Work hours / teaching hours"
    )
    antiguedad_anios: int | None = Field(default=None, description="Years of seniority")
    dias_trabajados: float | None = Field(
        default=30.0, description="Days worked in the period"
    )
    inasistencias: float | None = Field(default=0.0, description="Absences recorded")
    periodo_liquidado: str | None = Field(default=None, description="Liquidated period")
    orden_pago: str | None = Field(default=None, description="Payment order info")


class ConceptoItem(BaseModel):
    """Individual concept (earning or deduction) line."""

    model_config = ConfigDict(extra="ignore")

    codigo: str = Field(description="Concept code (e.g. '0510', '1060')")
    descripcion: str = Field(description="Concept title/description")
    haberes: float | None = Field(
        default=None, description="Earnings amount (positive)"
    )
    descuentos: float | None = Field(
        default=None, description="Deductions amount (positive)"
    )
    tipo: TipoConcepto = Field(
        description="remunerativo, no_remunerativo, or descuento"
    )


class LiquidacionSecuencia(BaseModel):
    """Detailed breakdown for a specific sequence/position."""

    model_config = ConfigDict(extra="ignore")

    establecimiento: EstablecimientoDetalle = Field(
        description="Associated establishment"
    )
    cargo: CargoDetalle = Field(description="Position details")
    conceptos: list[ConceptoItem] = Field(
        default_factory=list, description="List of earning and deduction concepts"
    )
    subtotal_haberes: float = Field(
        default=0.0, description="Sum of earnings for this sequence"
    )
    subtotal_descuentos: float = Field(
        default=0.0, description="Sum of deductions for this sequence"
    )
    liquido_calculado: float = Field(
        default=0.0, description="Calculated net (haberes - descuentos)"
    )


class TotalesConsolidados(BaseModel):
    """Global summary totals."""

    model_config = ConfigDict(extra="ignore")

    total_haberes_remunerativos: float = Field(
        default=0.0, description="Total taxable earnings"
    )
    total_haberes_no_remunerativos: float = Field(
        default=0.0, description="Total non-taxable earnings"
    )
    total_haberes: float = Field(default=0.0, description="Total gross earnings")
    total_descuentos: float = Field(default=0.0, description="Total deductions")
    total_liquido: float = Field(default=0.0, description="Total net salary in ARS")


class ReciboSueldoResponse(BaseModel):
    """Top-level normalized response for parsed salary receipts."""

    model_config = ConfigDict(extra="ignore")

    tipo_recibo: TipoRecibo = Field(description="Detected format of receipt")
    empleador: EmpleadorSchema = Field(description="Employer data")
    agente: AgenteSchema = Field(description="Employee data")
    resumen_liquidos: list[ResumenLiquidoItem] = Field(
        default_factory=list, description="Summary table items if available"
    )
    liquidaciones: list[LiquidacionSecuencia] = Field(
        default_factory=list, description="Breakdowns per position/sequence"
    )
    totales: TotalesConsolidados = Field(description="Global totals")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata such as pages, timing, filename"
    )
