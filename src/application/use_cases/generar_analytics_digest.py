"""Caso de uso para generar el Digest Pre-procesado de Analítica Comercial."""

from datetime import datetime, timezone
from typing import Any

from src.application.dtos.analytics_dtos import (
    AnalyticsDigestResponseDTO,
    AnomalyDTO,
    CalculatedKpisDTO,
    CampaignMetricDTO,
    ConversionInsightDTO,
    SearchTermInsightDTO,
    TrafficInsightDTO,
)
from src.domain.analytics.entities import (
    CampaignMetric,
    ConversionInsight,
    TrafficInsight,
)
from src.domain.analytics.ports import (
    ClarityDataSourcePort,
    GA4DataSourcePort,
    GoogleAdsDataSourcePort,
)
from src.domain.analytics.services import (
    AnomalyDetectionService,
    BudgetPacingCalculatorService,
    MetricCalculatorService,
    SearchTermEvaluatorService,
)

DEFAULT_BUDGET_LIMIT_ARS = 1500.0


class GenerarAnalyticsDigestUseCase:
    """Orquesta la ingesta multi-fuente, agregación determinística y detección de anomalías."""

    def __init__(
        self,
        google_ads_port: GoogleAdsDataSourcePort,
        ga4_port: GA4DataSourcePort,
        clarity_port: ClarityDataSourcePort,
        budget_limit_ars: float = DEFAULT_BUDGET_LIMIT_ARS,
    ) -> None:
        self._ads_port = google_ads_port
        self._ga4_port = ga4_port
        self._clarity_port = clarity_port
        self._budget_limit_ars = budget_limit_ars

    def execute(
        self,
        days: int = 1,
        current_hour_local: int | None = None,
    ) -> AnalyticsDigestResponseDTO:
        """Genera el snapshot y digest de analítica consolidado."""
        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        if current_hour_local is None:
            # Horario local Argentina (UTC-3)
            current_hour_local = (now_utc.hour - 3) % 24

        # 1. Ingesta desde puertos (con caché transparente de los gateways)
        ads_pacing = self._ads_port.get_daily_budget_pacing()
        ads_perf = self._ads_port.get_campaign_performance(days=days)
        ads_terms = self._ads_port.get_search_terms_report(days=days, limit=20)
        ga4_convs = self._ga4_port.get_conversions(days=days)
        ga4_pages = self._ga4_port.get_top_pages(days=days, limit=5, segment="all")
        clarity_urls = self._clarity_port.get_intent_recording_urls()

        # 2. Mapeo a entidades de dominio
        campaigns_entities: list[CampaignMetric] = []
        raw_camps: list[dict[str, Any]] = ads_perf.get("campaigns", [])
        for c in raw_camps:
            cost_val = float(c.get("cost_ars", c.get("cost", 0.0)))
            clicks_val = int(c.get("clicks", 0))
            cpc_val = (
                float(c.get("cpc_ars", c.get("cpc_avg_ars", 0.0)))
                if clicks_val > 0
                else 0.0
            )
            campaigns_entities.append(
                CampaignMetric(
                    campaign_id=str(c.get("id", c.get("campaign_id", ""))),
                    name=str(c.get("name", "Campaña")),
                    status=str(c.get("status", "ENABLED")),
                    impressions=int(c.get("impressions", 0)),
                    clicks=clicks_val,
                    cost_ars=cost_val,
                    conversions=float(c.get("conversions", 0.0)),
                    cpc_avg_ars=cpc_val,
                )
            )

        conversions_entities: list[ConversionInsight] = []
        raw_convs: list[dict[str, Any]] = ga4_convs.get("rows", [])
        for cv in raw_convs:
            conversions_entities.append(
                ConversionInsight(
                    event_name=str(cv.get("eventName", "")),
                    event_count=int(cv.get("eventCount", 0)),
                    total_users=int(cv.get("totalUsers", 0)),
                )
            )

        pages_entities: list[TrafficInsight] = []
        raw_pages: list[dict[str, Any]] = ga4_pages.get("rows", [])
        for pg in raw_pages:
            pages_entities.append(
                TrafficInsight(
                    page_path=str(pg.get("pagePath", "")),
                    page_title=str(pg.get("pageTitle", "")),
                    screen_page_views=int(pg.get("screenPageViews", 0)),
                    active_users=int(pg.get("activeUsers", 0)),
                )
            )

        # 3. Evaluación de términos de búsqueda
        raw_terms_list = ads_terms.get("terms", ads_terms.get("search_terms", []))
        search_terms_entities = SearchTermEvaluatorService.evaluate_terms(
            raw_terms=raw_terms_list
        )

        # 4. Agregación matemática de métricas
        total_impressions = sum(c.impressions for c in campaigns_entities)
        total_clicks = sum(c.clicks for c in campaigns_entities)
        total_cost = sum(c.cost_ars for c in campaigns_entities)
        total_conversions = sum(c.conversions for c in campaigns_entities)

        spent_today_raw = ads_pacing.get("spent_ars", ads_pacing.get("spent_today_ars"))
        spent_today = (
            float(spent_today_raw)
            if spent_today_raw is not None
            else (total_cost if days == 1 else 0.0)
        )

        kpis = MetricCalculatorService.calculate_kpis(
            impressions=total_impressions,
            clicks=total_clicks,
            cost_ars=total_cost,
            conversions=total_conversions,
            spent_today_ars=spent_today,
            budget_limit_ars=self._budget_limit_ars,
            current_hour_local=current_hour_local,
        )

        _, _, pacing_severity = BudgetPacingCalculatorService.calculate_pacing(
            spent_today_ars=spent_today,
            budget_limit_ars=self._budget_limit_ars,
            current_hour_local=current_hour_local,
        )

        # 5. Detección determinística de anomalías
        anomalies_entities = AnomalyDetectionService.detect_anomalies(
            kpis=kpis,
            campaigns=campaigns_entities,
            conversions=conversions_entities,
            search_terms=search_terms_entities,
            current_hour_local=current_hour_local,
        )

        # 6. Formateo de resumen Markdown optimizado para OpenClaw / Telegram
        resumen_md = self._build_markdown_summary(
            timestamp=timestamp_str,
            days=days,
            kpis=kpis,
            pacing_severity=pacing_severity.value,
            campaigns=campaigns_entities,
            conversions=conversions_entities,
            anomalies=anomalies_entities,
            intent_urls=clarity_urls,
        )

        # 7. Construcción de DTOs de salida
        return AnalyticsDigestResponseDTO(
            status="success",
            timestamp_utc=timestamp_str,
            days_analyzed=days,
            pacing_severity=pacing_severity.value,
            kpis=CalculatedKpisDTO(
                ctr_percent=kpis.ctr_percent,
                cpc_avg_ars=kpis.cpc_avg_ars,
                cpa_ars=kpis.cpa_ars,
                conversion_rate_percent=kpis.conversion_rate_percent,
                pacing_percent=kpis.pacing_percent,
                budget_limit_ars=kpis.budget_limit_ars,
                spent_today_ars=kpis.spent_today_ars,
                projected_daily_spend_ars=kpis.projected_daily_spend_ars,
            ),
            campaigns=[
                CampaignMetricDTO(
                    campaign_id=c.campaign_id,
                    name=c.name,
                    status=c.status,
                    impressions=c.impressions,
                    clicks=c.clicks,
                    cost_ars=c.cost_ars,
                    conversions=c.conversions,
                    cpc_avg_ars=c.cpc_avg_ars,
                )
                for c in campaigns_entities
            ],
            conversions=[
                ConversionInsightDTO(
                    event_name=cv.event_name,
                    event_count=cv.event_count,
                    total_users=cv.total_users,
                )
                for cv in conversions_entities
            ],
            top_pages=[
                TrafficInsightDTO(
                    page_path=pg.page_path,
                    page_title=pg.page_title,
                    screen_page_views=pg.screen_page_views,
                    active_users=pg.active_users,
                )
                for pg in pages_entities
            ],
            anomalies=[
                AnomalyDTO(
                    anomaly_type=a.anomaly_type.value,
                    severity=a.severity.value,
                    titulo=a.titulo,
                    descripcion=a.descripcion,
                    metrica_observada=a.metrica_observada,
                    recomendacion=a.recomendacion,
                )
                for a in anomalies_entities
            ],
            search_terms=[
                SearchTermInsightDTO(
                    term=t.term,
                    impressions=t.impressions,
                    clicks=t.clicks,
                    cost_ars=t.cost_ars,
                    conversions=t.conversions,
                    is_negative_candidate=t.is_negative_candidate,
                    reason=t.reason,
                )
                for t in search_terms_entities
            ],
            intent_recording_urls=clarity_urls,
            resumen_markdown=resumen_md,
        )

    def _build_markdown_summary(
        self,
        timestamp: str,
        days: int,
        kpis: Any,
        pacing_severity: str,
        campaigns: list[CampaignMetric],
        conversions: list[ConversionInsight],
        anomalies: list[Any],
        intent_urls: dict[str, str],
    ) -> str:
        """Construye un resumen Markdown ultra-compacto listo para consumo."""
        lines: list[str] = [
            f"📊 *DataMaq Analytics Digest ({timestamp})* [Período: {days}d]",
            "",
            f"💰 *Gasto Hoy:* ${kpis.spent_today_ars:,.2f} / ${kpis.budget_limit_ars:,.2f} ARS ({kpis.pacing_percent:.1f}%) — Estado: `{pacing_severity.upper()}`",
            f"📈 *KPIs:* CTR: {kpis.ctr_percent:.2f}% | CPC Medio: ${kpis.cpc_avg_ars:,.2f} | Conv. Rate: {kpis.conversion_rate_percent:.2f}%",
        ]

        if conversions:
            conv_summary = ", ".join(
                f"`{c.event_name}`: {c.event_count}" for c in conversions[:3]
            )
            lines.append(f"🎯 *Conversiones:* {conv_summary}")
        else:
            lines.append("🎯 *Conversiones:* Sin eventos en el período.")

        if anomalies:
            lines.append("\n⚠️ *Alertas & Anomalías:*")
            for a in anomalies:
                icon = "🔴" if a.severity.value == "critical" else "🟡"
                lines.append(f"  {icon} *{a.titulo}:* {a.descripcion}")

        if intent_urls:
            lines.append("\n🎥 *Grabaciones Clarity con Intención:*")
            for k in ("whatsapp_click", "email_click", "form_submit"):
                if k in intent_urls:
                    lines.append(f"  • [{k}]({intent_urls[k]})")

        return "\n".join(lines)
