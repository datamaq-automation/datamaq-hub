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


class CargoConciliadoDTO(BaseModel):
    """Representa la conciliación agrupada a nivel cargo (escuela + secuencia)."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str = Field(description="Secuencia del cargo")
    escuela_codigo: str = Field(description="Código de escuela o establecimiento")
    id_designacion: str | None = Field(
        default=None, description="UUID de la designación coincidente"
    )
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
    importe_total: float = Field(
        description="Suma de importes netos de todas las líneas del cargo"
    )
    cantidad_lineas: int = Field(
        description="Cantidad de líneas liquidadas para este cargo"
    )
    estado: EstadoLineaConciliacion = Field(
        description="Estado de la conciliación del cargo"
    )
    lineas_explicadas: list[LineaConciliadaDTO] = Field(
        default_factory=list[LineaConciliadaDTO],
        description="Líneas componentes del cargo explicadas",
    )
    observacion: str = Field(default="", description="Detalle de conciliación")


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
    cargos_conciliados: list[CargoConciliadoDTO] = Field(
        default_factory=list[CargoConciliadoDTO],
        description="Cargos consolidados conciliados (agrupados por escuela y secuencia)",
    )
    cargos_huerfanos_recibo: list[CargoConciliadoDTO] = Field(
        default_factory=list[CargoConciliadoDTO],
        description="Cargos del recibo sin designación registrada",
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


class DesignacionNoLiquidadaDTO(BaseModel):
    """Representación de una designación docente activa no liquidada para seguimiento diferido."""

    model_config = ConfigDict(extra="ignore")

    id_seguimiento: str = Field(
        description="Identificador único del registro de seguimiento"
    )
    id_recibo: str = Field(description="Recibo en el cual no se liquidó")
    id_designacion: str = Field(description="UUID de la designación docente activa")
    docente_cuit: str = Field(description="CUIT del docente")
    mes_pago: str = Field(description="Mes de pago del recibo auditado")
    secuencia: str | None = Field(
        default=None, description="Secuencia esperada del cargo"
    )
    escuela_codigo: str = Field(description="Establecimiento educativo")
    modulos: float = Field(description="Carga horaria o módulos del cargo")
    situacion_revista: str = Field(
        description="Situación de revista (TITULAR, PROVISIONAL, SUPLENTE)"
    )
    periodos_consecutivos: int = Field(
        default=1, description="Cantidad de períodos consecutivos sin cobrar"
    )
    alerta_2_periodos: bool = Field(
        default=False,
        description="True si encadena 2 o más períodos consecutivos sin liquidar",
    )
    estado: str = Field(
        default="PENDIENTE", description="Estado del seguimiento: PENDIENTE o RESUELTO"
    )
    id_recibo_resolucion: str | None = Field(
        default=None, description="Recibo donde finalmente se liquidó el cargo"
    )
    creado_en: str = Field(default="", description="Fecha y hora de registro isoformat")


class PropuestaDesignacionDTO(BaseModel):
    """Borrador estructurado precargado desde una línea huérfana de recibo para revisión y alta."""

    model_config = ConfigDict(extra="ignore")

    secuencia: str = Field(description="Secuencia del cargo en recibo")
    escuela_codigo: str = Field(
        description="Código de escuela extraído (ej. 055IS0199)"
    )
    distrito: str = Field(default="", description="Distrito escolar (ej. 055)")
    tipo_nivel: str = Field(default="", description="Tipo de nivel (ej. IS, MT)")
    escuela_numero: str = Field(default="", description="Número de escuela (ej. 0199)")
    cargo_codigo: str = Field(default="", description="Código de cargo o asignatura")
    situacion_revista: str = Field(
        default="TITULAR",
        description="Situación de revista propuesta (TITULAR, PROVISIONAL, SUPLENTE)",
    )
    modulos_horas: float = Field(default=0.0, description="Módulos u horas semanales")
    fecha_desde: str = Field(
        description="Fecha de inicio calculada/propuesta (YYYY-MM-DD)"
    )
    observaciones: str = Field(default="", description="Observaciones pre-completadas")


class ConfirmarPropuestasDTO(BaseModel):
    """Solicitud para la creación confirmada en bulk de designaciones huérfanas seleccionadas."""

    model_config = ConfigDict(extra="ignore")

    propuestas: list[PropuestaDesignacionDTO] = Field(
        ...,
        min_length=1,
        description="Lista de propuestas revisadas y aprobadas por el usuario para persistir",
    )
