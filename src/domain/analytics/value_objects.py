"""Value Objects inmutables para el contexto de analítica y telemetría."""

from dataclasses import dataclass
from enum import Enum


class PacingSeverity(str, Enum):
    """Nivel de consumo del presupuesto diario respecto al límite fijado."""

    NORMAL = "normal"
    PRECAUCION = "precaucion"
    EXCEDIDO = "excedido"
    SIN_TRAFICO = "sin_trafico"


class AnomalyType(str, Enum):
    """Tipología de anomalías detectadas determinísticamente."""

    GASTO_ACELERADO = "gasto_acelerado"
    SIN_IMPRESIONES = "sin_impresiones"
    ALTA_FRICCION_UX = "alta_friccion_ux"
    CONVERSION_DETECTADA = "conversion_detectada"
    TERMINO_IRRELEVANTE = "termino_irrelevante"
    SEO_BAJO = "seo_bajo"
    TRAFICO_FUERA_ZONA = "trafico_fuera_zona"
    DEPENDENCIA_SEM = "dependencia_sem"
    SUB_ENTREGA_SEM = "sub_entrega_sem"
    FICHA_IMPRESIONES_EN_CAIDA = "ficha_impresiones_en_caida"
    FICHA_RESENA_SIN_RESPONDER = "ficha_resena_sin_responder"
    FICHA_SIN_PUBLICACIONES = "ficha_sin_publicaciones"
    FICHA_RATING_BAJO = "ficha_rating_bajo"
    FICHA_POCAS_RESENAS = "ficha_pocas_resenas"


class AnomalySeverity(str, Enum):
    """Severidad de la anomalía o evento para alerting."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MarketingActionType(str, Enum):
    """Tipos de acciones o mutaciones permitidas para evaluación en post-procesamiento."""

    PAUSE_CAMPAIGN = "pause_campaign"
    ENABLE_CAMPAIGN = "enable_campaign"
    ADD_NEGATIVE_KEYWORD = "add_negative_keyword"
    ADJUST_BUDGET = "adjust_budget"
    ADJUST_BID = "adjust_bid"
    GBP_CREATE_POST = "gbp_create_post"
    GBP_REPLY_REVIEW = "gbp_reply_review"


@dataclass(frozen=True)
class CalculatedKpis:
    """Métricas y KPIs calculados con exactitud matemática determinística."""

    ctr_percent: float
    cpc_avg_ars: float
    cpa_ars: float
    conversion_rate_percent: float
    pacing_percent: float
    budget_limit_ars: float
    spent_today_ars: float
    projected_daily_spend_ars: float


@dataclass(frozen=True)
class ResumenFicha:
    """Totales agregados de la ficha de Google Business Profile en el período analizado."""

    dias_analizados: int
    impresiones_maps: int
    impresiones_search: int
    impresiones_totales: int
    clics_sitio: int
    llamadas: int
    solicitudes_indicaciones: int
    conversaciones: int
    impresiones_periodo_previo: int
    variacion_impresiones_percent: float


@dataclass(frozen=True)
class ChannelAttribution:
    """Distribución porcentual del tráfico por canal."""

    organic_percent: float
    paid_percent: float
    direct_percent: float
    referral_percent: float
    other_percent: float
    total_sessions: int
