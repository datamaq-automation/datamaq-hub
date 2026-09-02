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


class TrafficSourceInsightDTO(BaseModel):
    """Fuente de tráfico desglosada por canal."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="Fuente de tráfico (google, direct, etc.)")
    medium: str = Field(description="Medio de tráfico (organic, cpc, referral, etc.)")
    campaign: str = Field(description="Nombre de campaña UTM")
    sessions: int = Field(description="Cantidad de sesiones")
    active_users: int = Field(description="Usuarios activos")
    conversions: float = Field(description="Conversiones atribuidas")


class GeoTrafficInsightDTO(BaseModel):
    """Distribución geográfica del tráfico."""

    model_config = ConfigDict(frozen=True)

    city: str = Field(description="Ciudad de origen")
    region: str = Field(description="Región o provincia")
    sessions: int = Field(description="Cantidad de sesiones")
    active_users: int = Field(description="Usuarios activos")
    is_target_zone: bool = Field(
        description="True si pertenece a la zona objetivo GBA Norte/AMBA"
    )


class ChannelAttributionDTO(BaseModel):
    """Distribución porcentual del tráfico por canal."""

    model_config = ConfigDict(frozen=True)

    organic_percent: float = Field(description="% tráfico orgánico (SEO)")
    paid_percent: float = Field(description="% tráfico pago (SEM/Ads)")
    direct_percent: float = Field(description="% tráfico directo")
    referral_percent: float = Field(description="% tráfico referral")
    other_percent: float = Field(description="% otros canales")
    total_sessions: int = Field(description="Total de sesiones en el período")


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
    traffic_sources: list[TrafficSourceInsightDTO] = Field(
        default_factory=list[TrafficSourceInsightDTO],
        description="Desglose de tráfico por fuente/medio/campaña (SEO vs SEM vs Directo)",
    )
    geo_traffic: list[GeoTrafficInsightDTO] = Field(
        default_factory=list[GeoTrafficInsightDTO],
        description="Distribución geográfica del tráfico con clasificación de zona",
    )
    channel_attribution: ChannelAttributionDTO | None = Field(
        default=None,
        description="Atribución porcentual de canales (SEO/SEM/Directo/Referral)",
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


class TokenUsageDTO(BaseModel):
    """Consumo acumulado de tokens de un proveedor de LLM."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(description="Total de tokens de entrada consumidos")
    output_tokens: int = Field(description="Total de tokens de salida consumidos")
    cached_tokens: int = Field(description="Total de tokens de caché consumidos")


class DeepSeekUsageDTO(BaseModel):
    """Balance y disponibilidad de la API de DeepSeek."""

    model_config = ConfigDict(frozen=True)

    is_available: bool = Field(
        description="Indica si la API de DeepSeek está disponible y configurada"
    )
    balance: float = Field(description="Saldo disponible en la cuenta")
    currency: str = Field(description="Moneda del saldo (usualmente USD)")


class UsageResponseDTO(BaseModel):
    """Respuesta consolidada de consumo y balance de APIs de LLM."""

    model_config = ConfigDict(frozen=True)

    deepseek: DeepSeekUsageDTO = Field(description="Uso y balance de DeepSeek API")
    agy: TokenUsageDTO = Field(
        description="Consumo acumulado de tokens de Antigravity CLI"
    )


class LocalUsageRequestDTO(BaseModel):
    """Petición para sincronizar el uso acumulado local de tokens AGY."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(ge=0, description="Tokens de entrada acumulados")
    output_tokens: int = Field(ge=0, description="Tokens de salida acumulados")
    cached_tokens: int = Field(ge=0, description="Tokens de caché acumulados")
