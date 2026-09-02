"""Entidades de dominio para el contexto de analítica y telemetría."""

from dataclasses import dataclass, field

from src.domain.analytics.value_objects import (
    AnomalySeverity,
    AnomalyType,
    CalculatedKpis,
    PacingSeverity,
)


@dataclass(frozen=True)
class CampaignMetric:
    """Métricas consolidadas de una campaña publicitaria individual."""

    campaign_id: str
    name: str
    status: str
    impressions: int
    clicks: int
    cost_ars: float
    conversions: float
    cpc_avg_ars: float


@dataclass(frozen=True)
class ConversionInsight:
    """Evento de conversión web consolidado desde GA4 / CRM."""

    event_name: str
    event_count: int
    total_users: int


@dataclass(frozen=True)
class TrafficInsight:
    """Tráfico consolidado de una página web relevante."""

    page_path: str
    page_title: str
    screen_page_views: int
    active_users: int


@dataclass(frozen=True)
class SearchTermInsight:
    """Término de búsqueda real con evaluación heurística de intencionalidad."""

    term: str
    impressions: int
    clicks: int
    cost_ars: float
    conversions: float
    is_negative_candidate: bool = False
    reason: str = ""


@dataclass(frozen=True)
class AnomalyAlert:
    """Anomalía detectada por reglas determinísticas de negocio."""

    anomaly_type: AnomalyType
    severity: AnomalySeverity
    titulo: str
    descripcion: str
    metrica_observada: str
    recomendacion: str


@dataclass(frozen=True)
class MarketingSnapshot:
    """Agregado inmutable que consolida el estado global de telemetría y marketing."""

    timestamp_utc: str
    days_analyzed: int
    pacing_severity: PacingSeverity
    kpis: CalculatedKpis
    campaigns: list[CampaignMetric] = field(default_factory=list[CampaignMetric])
    conversions: list[ConversionInsight] = field(
        default_factory=list[ConversionInsight]
    )
    top_pages: list[TrafficInsight] = field(default_factory=list[TrafficInsight])
    anomalies: list[AnomalyAlert] = field(default_factory=list[AnomalyAlert])
    search_terms: list[SearchTermInsight] = field(
        default_factory=list[SearchTermInsight]
    )
    intent_recording_urls: dict[str, str] = field(default_factory=dict[str, str])


@dataclass(frozen=True)
class TrafficSourceInsight:
    """Fuente de tráfico consolidada (SEO, SEM, Directo, Referral)."""

    source: str
    medium: str
    campaign: str
    sessions: int
    active_users: int
    conversions: float


@dataclass(frozen=True)
class GeoTrafficInsight:
    """Tráfico por ubicación geográfica del usuario."""

    city: str
    region: str
    sessions: int
    active_users: int
    is_target_zone: bool
