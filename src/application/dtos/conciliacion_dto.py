"""DTOs para el reporte y resultado de conciliación entre recibo y designaciones."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.domain.recibos.entities import EstadoLineaConciliacion


class LineaConciliadaDTO(BaseModel):
    """Representación DTO de una línea cruzada entre recibo y designación."""

    model_config = ConfigDict(extra="ignore")

    id_designacion: str | None = Field(
        default=None,
        description="UUID de la designación coincidente (o None si es huérfana)",
    )
    secuencia: str = Field(description="Secuencia liquidada en el recibo")
    escuela_codigo: str = Field(description="Código o número de establecimiento")
    periodo_liquidado: str = Field(description="Período devengado (YYYY-MM)")
    revista_recibo: str = Field(
        default="", description="Situación de revista en recibo"
    )
    revista_designacion: str | None = Field(
        default=None, description="Situación de revista en designación"
    )
    modulos_recibo: float = Field(default=0.0, description="Módulos en recibo")
    modulos_designacion: float | None = Field(
        default=None, description="Módulos en designación"
    )
    liquido_pesos: float = Field(description="Importe neto liquidado")
    estado: EstadoLineaConciliacion = Field(description="Estado de la conciliación")
    es_retroactivo: bool = Field(
        description="True si corresponde a un período anterior al mes de pago"
    )
    observacion: str = Field(description="Detalle o justificación de la conciliación")


class ConciliacionResponseDTO(BaseModel):
    """Reporte completo de conciliación mensual: liquidado vs esperado."""

    model_config = ConfigDict(extra="ignore")

    id_recibo: str = Field(description="Identificador del recibo auditado")
    mes_pago: str = Field(description="Mes de pago del recibo (YYYY-MM)")
    docente_cuit: str = Field(description="CUIT del docente")
    total_lineas_recibo: int = Field(
        description="Cantidad de líneas liquidadas en el recibo"
    )
    total_designaciones_evaluadas: int = Field(
        description="Cantidad de designaciones históricas evaluadas"
    )
    lineas_conciliadas: list[LineaConciliadaDTO] = Field(
        default_factory=list[LineaConciliadaDTO],
        description="Líneas que matchearon con designaciones activas o suplencias cesadas",
    )
    lineas_huerfanas_recibo: list[LineaConciliadaDTO] = Field(
        default_factory=list[LineaConciliadaDTO],
        description="Líneas percibidas en recibo sin designación en el sistema",
    )
    designaciones_no_cobradas: list[LineaConciliadaDTO] = Field(
        default_factory=list[LineaConciliadaDTO],
        description="Designaciones vigentes que no fueron liquidadas en este recibo",
    )
    total_liquidado_recibo: float = Field(
        description="Total neto percibido según recibo"
    )
    total_liquidado_conciliado: float = Field(
        description="Total neto que cuenta con designación respaldatoria"
    )
    total_liquidado_huerfano: float = Field(
        description="Total neto percibido sin designación registrada"
    )
    es_conciliacion_completa: bool = Field(
        description="True si el 100% de las líneas del recibo y designaciones vigentes concilian sin huérfanas"
    )
    resumen_financiero: dict[str, Any] = Field(
        default_factory=dict[str, Any],
        description="Resumen consolidado de haberes y desvíos",
    )
