"""DTOs de aplicación para telemetría, digest de analítica y post-procesamiento."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CalculatedKpisDTO(BaseModel):
    """Métricas y KPIs calculados con exactitud determinística."""

    model_config = ConfigDict(frozen=True)

    ctr_percent: float = Field(description="Tasa de clics en porcentaje")
    cpc_avg_ars: float = Field(description="Costo por clic promedio en ARS")
    cpa_ars: float = Field(description="Costo por adquisición / conversión en ARS")
    conversion_rate_percent: float = Field(
        description="Tasa de conversión en porcentaje"
    )
    pacing_percent: float = Field(
        description="Porcentaje del presupuesto diario consumido"
    )
    budget_limit_ars: float = Field(description="Límite diario de presupuesto en ARS")
    spent_today_ars: float = Field(description="Gasto acumulado de hoy en ARS")
    projected_daily_spend_ars: float = Field(
        description="Proyección lineal de gasto para el día en ARS"
    )


class CampaignMetricDTO(BaseModel):
    """Métricas de rendimiento por campaña publicitaria."""

    model_config = ConfigDict(frozen=True)

    campaign_id: str = Field(
        description="Identificador único de la campaña en Google Ads"
    )
    name: str = Field(description="Nombre de la campaña")
    status: str = Field(description="Estado de la campaña (ENABLED, PAUSED, etc.)")
    impressions: int = Field(description="Cantidad de impresiones")
    clicks: int = Field(description="Cantidad de clics")
    cost_ars: float = Field(description="Costo total en ARS")
    conversions: float = Field(description="Cantidad de conversiones atribuidas")
    cpc_avg_ars: float = Field(description="Costo por clic medio en ARS")


class ConversionInsightDTO(BaseModel):
    """Evento de conversión registrado en GA4."""

    model_config = ConfigDict(frozen=True)

    event_name: str = Field(
        description="Nombre del evento de conversión (ej. whatsapp_click)"
    )
    event_count: int = Field(description="Cantidad de disparos del evento")
    total_users: int = Field(description="Cantidad de usuarios únicos que convirtieron")


class TrafficInsightDTO(BaseModel):
    """Página web con tráfico relevante en el período."""

    model_config = ConfigDict(frozen=True)

    page_path: str = Field(description="Ruta URL de la página")
    page_title: str = Field(description="Título de la página")
    screen_page_views: int = Field(description="Vistas de pantalla")
    active_users: int = Field(description="Usuarios activos")


class SearchTermInsightDTO(BaseModel):
    """Término de búsqueda real y su clasificación de relevancia."""

    model_config = ConfigDict(frozen=True)

    term: str = Field(description="Término de búsqueda consultado por el usuario")
    impressions: int = Field(description="Impresiones generadas")
    clicks: int = Field(description="Clics generados")
    cost_ars: float = Field(description="Costo consumido en ARS")
    conversions: float = Field(description="Conversiones logradas")
    is_negative_candidate: bool = Field(
        default=False,
        description="True si coincide con patrones irrelevantes o gasto infructuoso",
    )
    reason: str = Field(default="", description="Motivo de exclusión o recomendación")


class AnomalyDTO(BaseModel):
    """Alerta o anomalía detectada por reglas de negocio."""

    model_config = ConfigDict(frozen=True)

    anomaly_type: str = Field(description="Tipo de anomalía detectada")
    severity: str = Field(description="Severidad (info, warning, critical)")
    titulo: str = Field(description="Título breve de la alerta")
    descripcion: str = Field(description="Explicación detallada de la condición")
    metrica_observada: str = Field(description="Valor o métrica anómala")
    recomendacion: str = Field(description="Acción recomendada")


class AnalyticsDigestResponseDTO(BaseModel):
    """Resumen consolidado y pre-procesado listo para OpenClaw, Telegram y UI."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="success", description="Estado de la respuesta")
    timestamp_utc: str = Field(description="Marca temporal de generación")
    days_analyzed: int = Field(description="Período de días analizado")
    pacing_severity: str = Field(description="Severidad del consumo presupuestario")
    kpis: CalculatedKpisDTO = Field(description="KPIs calculados determinísticamente")
    campaigns: list[CampaignMetricDTO] = Field(
        default_factory=list[CampaignMetricDTO],
        description="Rendimiento de campañas",
    )
    conversions: list[ConversionInsightDTO] = Field(
        default_factory=list[ConversionInsightDTO],
        description="Eventos de conversión web",
    )
    top_pages: list[TrafficInsightDTO] = Field(
        default_factory=list[TrafficInsightDTO],
        description="Top páginas visitadas",
    )
    anomalies: list[AnomalyDTO] = Field(
        default_factory=list[AnomalyDTO],
        description="Anomalías y alertas detectadas",
    )
    search_terms: list[SearchTermInsightDTO] = Field(
        default_factory=list[SearchTermInsightDTO],
        description="Términos de búsqueda evaluados",
    )
    intent_recording_urls: dict[str, str] = Field(
        default_factory=dict[str, str],
        description="URLs directas a grabaciones en Clarity",
    )
    resumen_markdown: str = Field(
        default="",
        description="Resumen ejecutivo ultra-compacto formateado en Markdown para agentes o Telegram",
    )


class MarketingActionRequestDTO(BaseModel):
    """Petición de validación o ejecución de acción de marketing por parte de un agente."""

    model_config = ConfigDict(frozen=True)

    action_type: str = Field(
        description="Tipo de acción (pause_campaign, enable_campaign, add_negative_keyword, adjust_budget, adjust_bid)"
    )
    params: dict[str, Any] = Field(
        default_factory=dict[str, Any],
        description="Parámetros asociados a la acción",
    )


class MarketingActionValidationDTO(BaseModel):
    """Resultado de la validación determinística de guardrails de post-procesamiento."""

    model_config = ConfigDict(frozen=True)

    valid: bool = Field(
        description="True si la acción cumple con todos los guardrails de seguridad"
    )
    action_type: str = Field(description="Tipo de acción evaluada")
    message: str = Field(
        description="Mensaje explicativo o motivo de rechazo si no es válida"
    )
    params: dict[str, Any] = Field(
        default_factory=dict[str, Any],
        description="Parámetros normalizados",
    )
