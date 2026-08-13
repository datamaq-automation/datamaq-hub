"""Domain entities for salary receipts domain."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


class Agente(BaseModel):
    """Employee / public agent identification entity."""

    model_config = ConfigDict(extra="ignore")

    nombre_completo: str = Field(description="Full employee name")
    tipo_documento: str = Field(default="DNI", description="Document type")
    numero_documento: str = Field(description="Document number")
    sexo: str | None = Field(default=None, description="Gender (M/F/X)")
    cuil: str = Field(description="CUIL formatted XX-XXXXXXXX-X")
    mes_pago: str = Field(description="Liquidated payment period")


class Empleador(BaseModel):
    """Employer entity."""

    model_config = ConfigDict(extra="ignore")

    organismo_o_empresa: str = Field(description="Organization or corporate name")
    dependencia: str | None = Field(
        default=None, description="Department or dependency"
    )
    cuit: str | None = Field(default=None, description="Employer CUIT")


class ConceptoItem(BaseModel):
    """Salary line item concept entity."""

    model_config = ConfigDict(extra="ignore")

    codigo: str = Field(description="Concept code")
    descripcion: str = Field(description="Concept description")
    haberes: float | None = Field(default=None, description="Earnings amount")
    descuentos: float | None = Field(default=None, description="Deduction amount")
    tipo: TipoConcepto = Field(description="Concept classification")


class EstablecimientoDetalle(BaseModel):
    """School / Establishment entity."""

    model_config = ConfigDict(extra="ignore")

    codigo: str | None = Field(default=None, description="Establishment code")
    distrito: str | None = Field(default=None, description="District name")
    categoria: str | None = Field(default=None, description="Category code")
    desfavorabilidad: int | None = Field(default=0, description="Hardship percentage")
    secciones: int | None = Field(default=0, description="Sections count")
    es_carcel: bool | None = Field(
        default=False, description="Is penitentiary facility"
    )
    doble_escolaridad: bool | None = Field(
        default=False, description="Double schooling"
    )
    turnos: int | None = Field(default=1, description="Shifts count")
    nombre: str | None = Field(default=None, description="Establishment name")


class CargoDetalle(BaseModel):
    """Position / Cargo attributes entity."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str = Field(description="Sequence number")
    situacion_revista: str | None = Field(default=None, description="Tenure status")
    cargo_real: str | None = Field(default=None, description="Job title / code")
    carga_horaria: float | None = Field(default=None, description="Assigned hours")
    antiguedad_anios: int | None = Field(default=None, description="Seniority years")
    dias_trabajados: float | None = Field(default=30.0, description="Days worked")
    inasistencias: float | None = Field(default=0.0, description="Absences")
    periodo_liquidado: str | None = Field(default=None, description="Liquidated period")
    orden_pago: str | None = Field(default=None, description="Payment order number")


class LiquidacionSecuencia(BaseModel):
    """Settlement per sequence / position."""

    model_config = ConfigDict(extra="ignore")

    establecimiento: EstablecimientoDetalle = Field(description="Establishment")
    cargo: CargoDetalle = Field(description="Position details")
    conceptos: list[ConceptoItem] = Field(
        default_factory=list, description="Concepts list"
    )
    subtotal_haberes: float = Field(default=0.0, description="Sum of earnings")
    subtotal_descuentos: float = Field(default=0.0, description="Sum of deductions")
    liquido_calculado: float = Field(default=0.0, description="Net calculated amount")


class ResumenLiquidoItem(BaseModel):
    """Summary table row entity."""

    model_config = ConfigDict(extra="ignore")

    establecimiento_codigo: str = Field(description="Establishment code")
    secuencia: str = Field(description="Sequence number")
    periodo_liquidado: str = Field(description="Liquidated period")
    fecha_pago: str = Field(description="Payment date")
    orden_pago_codigo: str = Field(description="Payment order code")
    orden_pago_descripcion: str = Field(description="Payment order description")
    liquido_pesos: float = Field(description="Net amount in ARS")


class TotalesConsolidados(BaseModel):
    """Consolidated totals entity."""

    model_config = ConfigDict(extra="ignore")

    total_haberes_remunerativos: float = Field(
        default=0.0, description="Taxable earnings"
    )
    total_haberes_no_remunerativos: float = Field(
        default=0.0, description="Non-taxable earnings"
    )
    total_haberes: float = Field(default=0.0, description="Total gross earnings")
    total_descuentos: float = Field(default=0.0, description="Total deductions")
    total_liquido: float = Field(default=0.0, description="Total net amount")


class ReciboSueldo(BaseModel):
    """Aggregate Root representing a parsed and validated salary receipt."""

    model_config = ConfigDict(extra="ignore")

    tipo_recibo: TipoRecibo = Field(description="Receipt type")
    empleador: Empleador = Field(description="Employer data")
    agente: Agente = Field(description="Employee data")
    resumen_liquidos: list[ResumenLiquidoItem] = Field(
        default_factory=list, description="Summary table rows"
    )
    liquidaciones: list[LiquidacionSecuencia] = Field(
        default_factory=list, description="Sequence breakdowns"
    )
    totales: TotalesConsolidados = Field(description="Consolidated totals")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
