"""Domain entities for salary receipts domain."""

from dataclasses import dataclass, field
from typing import Any

from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


@dataclass
class Agente:
    """Employee / public agent identification entity."""

    nombre_completo: str
    numero_documento: str
    cuil: str
    mes_pago: str
    tipo_documento: str = "DNI"
    sexo: str | None = None


@dataclass
class Empleador:
    """Employer entity."""

    organismo_o_empresa: str
    dependencia: str | None = None
    cuit: str | None = None


@dataclass
class ConceptoItem:
    """Salary line item concept entity."""

    codigo: str
    descripcion: str
    tipo: TipoConcepto
    haberes: float | None = None
    descuentos: float | None = None


@dataclass
class EstablecimientoDetalle:
    """School / Establishment entity."""

    codigo: str | None = None
    distrito: str | None = None
    categoria: str | None = None
    desfavorabilidad: int | None = 0
    secciones: int | None = 0
    es_carcel: bool | None = False
    doble_escolaridad: bool | None = False
    turnos: int | None = 1
    nombre: str | None = None


@dataclass
class CargoDetalle:
    """Position / Cargo attributes entity."""

    secuencia: str
    situacion_revista: str | None = None
    cargo_real: str | None = None
    carga_horaria: float | None = None
    antiguedad_anios: int | None = None
    dias_trabajados: float | None = None
    inasistencias: float | None = 0.0
    periodo_liquidado: str | None = None
    orden_pago: str | None = None


@dataclass
class LiquidacionSecuencia:
    """Settlement per sequence / position."""

    establecimiento: EstablecimientoDetalle
    cargo: CargoDetalle
    conceptos: list[ConceptoItem] = field(default_factory=list[ConceptoItem])
    subtotal_haberes: float = 0.0
    subtotal_descuentos: float = 0.0
    liquido_calculado: float = 0.0


@dataclass
class ResumenLiquidoItem:
    """Summary table row entity."""

    establecimiento_codigo: str
    secuencia: str
    periodo_liquidado: str
    fecha_pago: str
    orden_pago_codigo: str
    orden_pago_descripcion: str
    liquido_pesos: float


@dataclass
class TotalesConsolidados:
    """Consolidated totals entity."""

    total_haberes_remunerativos: float = 0.0
    total_haberes_no_remunerativos: float = 0.0
    total_haberes: float = 0.0
    total_descuentos: float = 0.0
    total_liquido: float = 0.0


@dataclass
class ReciboSueldo:
    """Aggregate Root representing a parsed and validated salary receipt."""

    tipo_recibo: TipoRecibo
    empleador: Empleador
    agente: Agente
    resumen_liquidos: list[ResumenLiquidoItem] = field(
        default_factory=list[ResumenLiquidoItem]
    )
    liquidaciones: list[LiquidacionSecuencia] = field(
        default_factory=list[LiquidacionSecuencia]
    )
    totales: TotalesConsolidados = field(default_factory=TotalesConsolidados)
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])
