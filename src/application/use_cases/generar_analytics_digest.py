"""Caso de uso para generar el Digest Pre-procesado de Analítica Comercial."""

from datetime import datetime, timezone
from typing import Any

from src.application.dtos.analytics_dtos import (
    AnalyticsDigestResponseDTO,
    AnomalyDTO,
    CalculatedKpisDTO,
    CampaignMetricDTO,
    ChannelAttributionDTO,
    ConversionInsightDTO,
    GeoTrafficInsightDTO,
    ResenaFichaDTO,
    ResumenFichaDTO,
    SearchTermInsightDTO,
    TerminoBusquedaFichaDTO,
    TrafficInsightDTO,
    TrafficSourceInsightDTO,
)
from src.domain.analytics.entities import (
    AnomalyAlert,
    CampaignMetric,
    ConversionInsight,
    GeoTrafficInsight,
    MetricaFicha,
    ResenaFicha,
    TerminoBusquedaFicha,
    TrafficInsight,
    TrafficSourceInsight,
)
from src.domain.analytics.ports import (
    ClarityDataSourcePort,
    GA4DataSourcePort,
    GoogleAdsDataSourcePort,
    GoogleBusinessProfileDataSourcePort,
)
from src.domain.analytics.services import (
    TARGET_CITIES,
    AnomalyDetectionService,
    BudgetPacingCalculatorService,
    FichaLocalAnalysisService,
    GeoAnalysisService,
    MetricCalculatorService,
    SearchTermEvaluatorService,
    TrafficAttributionService,
)
from src.domain.analytics.value_objects import ResumenFicha

DEFAULT_BUDGET_LIMIT_ARS = 1500.0

# La Business Profile API entrega la serie diaria con retraso y el digest suele
# pedirse con days=1, así que la ficha se lee siempre sobre una ventana mensual.
FICHA_DIAS_MINIMOS = 28


class GenerarAnalyticsDigestUseCase:
    """Orquesta la ingesta multi-fuente, agregación determinística y detección de anomalías."""

    def __init__(
        self,
        google_ads_port: GoogleAdsDataSourcePort,
        ga4_port: GA4DataSourcePort,
        clarity_port: ClarityDataSourcePort,
        budget_limit_ars: float = DEFAULT_BUDGET_LIMIT_ARS,
        gbp_port: GoogleBusinessProfileDataSourcePort | None = None,
    ) -> None:
        self._ads_port = google_ads_port
        self._ga4_port = ga4_port
        self._clarity_port = clarity_port
        self._budget_limit_ars = budget_limit_ars
        # Opcional: el digest sigue funcionando sin ficha configurada.
        self._gbp_port = gbp_port

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

        # 3b. Ingesta de fuentes de tráfico (SEO/SEM/Directo)
        ga4_traffic = self._ga4_port.get_traffic_sources(days=days, limit=15)
        traffic_source_entities: list[TrafficSourceInsight] = []
        for row in ga4_traffic.get("rows", []):
            traffic_source_entities.append(
                TrafficSourceInsight(
                    source=str(row.get("sessionSource", "")),
                    medium=str(row.get("sessionMedium", "")),
                    campaign=str(row.get("sessionCampaignName", "")),
                    sessions=int(row.get("sessions", 0)),
                    active_users=int(row.get("activeUsers", 0)),
                    conversions=float(row.get("conversions", 0.0)),
                )
            )

        # 3c. Ingesta de tráfico geográfico
        ga4_geo = self._ga4_port.get_geo_traffic(days=days, limit=15)
        geo_entities: list[GeoTrafficInsight] = []
        for row in ga4_geo.get("rows", []):
            city = str(row.get("city", ""))
            geo_entities.append(
                GeoTrafficInsight(
                    city=city,
                    region=str(row.get("region", "")),
                    sessions=int(row.get("sessions", 0)),
                    active_users=int(row.get("activeUsers", 0)),
                    is_target_zone=city.lower().strip() in TARGET_CITIES,
                )
            )

        # 3d. Cálculo de atribución de canales
        channel_attribution = TrafficAttributionService.calculate_attribution(
            traffic_source_entities
        )

        # 3e. Análisis geográfico
        _, _, geo_out_pct = GeoAnalysisService.classify_geo(geo_entities)

        # 3f. Ingesta de la ficha de Google Business Profile (paquete local de Maps)
        (
            ficha_resumen,
            ficha_resenas_entities,
            ficha_terminos_entities,
            ficha_anomalies,
        ) = self._ingestar_ficha(days=days)

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
            channel_attribution=channel_attribution,
            geo_out_of_zone_percent=geo_out_pct,
        )

        # 6. Formateo de resumen Markdown optimizado para OpenClaw / Telegram
        resumen_md = self._build_markdown_summary(
            timestamp=timestamp_str,
            days=days,
            kpis=kpis,
            pacing_severity=pacing_severity.value,
            campaigns=campaigns_entities,
            conversions=conversions_entities,
            anomalies=[*anomalies_entities, *ficha_anomalies],
            intent_urls=clarity_urls,
            channel_attribution=channel_attribution,
            geo_insights=geo_entities,
            geo_out_of_zone_percent=geo_out_pct,
            ficha_resumen=ficha_resumen,
            ficha_terminos=ficha_terminos_entities,
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
                for a in [*anomalies_entities, *ficha_anomalies]
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
            traffic_sources=[
                TrafficSourceInsightDTO(
                    source=ts.source,
                    medium=ts.medium,
                    campaign=ts.campaign,
                    sessions=ts.sessions,
                    active_users=ts.active_users,
                    conversions=ts.conversions,
                )
                for ts in traffic_source_entities
            ],
            geo_traffic=[
                GeoTrafficInsightDTO(
                    city=g.city,
                    region=g.region,
                    sessions=g.sessions,
                    active_users=g.active_users,
                    is_target_zone=g.is_target_zone,
                )
                for g in geo_entities
            ],
            channel_attribution=ChannelAttributionDTO(
                organic_percent=channel_attribution.organic_percent,
                paid_percent=channel_attribution.paid_percent,
                direct_percent=channel_attribution.direct_percent,
                referral_percent=channel_attribution.referral_percent,
                other_percent=channel_attribution.other_percent,
                total_sessions=channel_attribution.total_sessions,
            ),
            ficha_resumen=(
                ResumenFichaDTO(
                    dias_analizados=ficha_resumen.dias_analizados,
                    impresiones_maps=ficha_resumen.impresiones_maps,
                    impresiones_search=ficha_resumen.impresiones_search,
                    impresiones_totales=ficha_resumen.impresiones_totales,
                    clics_sitio=ficha_resumen.clics_sitio,
                    llamadas=ficha_resumen.llamadas,
                    solicitudes_indicaciones=ficha_resumen.solicitudes_indicaciones,
                    conversaciones=ficha_resumen.conversaciones,
                    impresiones_periodo_previo=ficha_resumen.impresiones_periodo_previo,
                    variacion_impresiones_percent=ficha_resumen.variacion_impresiones_percent,
                )
                if ficha_resumen is not None
                else None
            ),
            ficha_resenas=[
                ResenaFichaDTO(
                    review_id=r.review_id,
                    autor=r.autor,
                    estrellas=r.estrellas,
                    comentario=r.comentario,
                    fecha_utc=r.fecha_utc,
                    tiene_respuesta=r.tiene_respuesta,
                )
                for r in ficha_resenas_entities
            ],
            ficha_terminos=[
                TerminoBusquedaFichaDTO(
                    termino=t.termino,
                    impresiones=t.impresiones,
                    es_de_marca=t.es_de_marca,
                )
                for t in ficha_terminos_entities
            ],
            resumen_markdown=resumen_md,
        )

    def _ingestar_ficha(
        self, days: int
    ) -> tuple[
        ResumenFicha | None,
        list[ResenaFicha],
        list[TerminoBusquedaFicha],
        list[AnomalyAlert],
    ]:
        """Lee la ficha de Google, la mapea a dominio y detecta sus anomalías.

        Degrada a vacío ante cualquier estado que no sea ``success``: sin
        credenciales, sin ficha configurada o con la API todavía sin aprobar.
        """
        if self._gbp_port is None:
            return None, [], [], []

        dias_ficha = max(days, FICHA_DIAS_MINIMOS)
        perf = self._gbp_port.get_performance(days=dias_ficha)
        reviews = self._gbp_port.get_reviews(limit=20)
        keywords = self._gbp_port.get_search_keywords(months=1, limit=25)

        resumen: ResumenFicha | None = None
        if perf.get("status") == "success":
            metricas = [
                MetricaFicha(
                    fecha=str(m.get("fecha", "")),
                    metrica=str(m.get("metrica", "")),
                    valor=int(m.get("valor", 0)),
                )
                for m in perf.get("metricas", [])
            ]
            metricas_previas = [
                MetricaFicha(
                    fecha=str(m.get("fecha", "")),
                    metrica=str(m.get("metrica", "")),
                    valor=int(m.get("valor", 0)),
                )
                for m in perf.get("metricas_periodo_previo", [])
            ]
            resumen = FichaLocalAnalysisService.resumir_metricas(
                metricas=metricas,
                dias_analizados=int(perf.get("dias_analizados", dias_ficha)),
                metricas_periodo_previo=metricas_previas,
            )

        resenas: list[ResenaFicha] = []
        if reviews.get("status") == "success":
            resenas = [
                ResenaFicha(
                    review_id=str(r.get("review_id", "")),
                    autor=str(r.get("autor", "")),
                    estrellas=int(r.get("estrellas", 0)),
                    comentario=str(r.get("comentario", "")),
                    fecha_utc=str(r.get("fecha_utc", "")),
                    tiene_respuesta=bool(r.get("tiene_respuesta", False)),
                )
                for r in reviews.get("resenas", [])
            ]

        terminos: list[TerminoBusquedaFicha] = []
        if keywords.get("status") == "success":
            terminos = FichaLocalAnalysisService.clasificar_terminos(
                keywords.get("terminos", [])
            )

        anomalias = FichaLocalAnalysisService.detectar_anomalias(
            resumen=resumen,
            resenas=resenas,
        )

        return resumen, resenas, terminos, anomalias

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
        channel_attribution: Any | None = None,
        geo_insights: list[GeoTrafficInsight] | None = None,
        geo_out_of_zone_percent: float = 0.0,
        ficha_resumen: ResumenFicha | None = None,
        ficha_terminos: list[TerminoBusquedaFicha] | None = None,
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

        # Sección SEO vs SEM (Atribución de Canales)
        if channel_attribution is not None and channel_attribution.total_sessions > 0:
            lines.append("")
            lines.append("📡 *Canales de Tráfico:*")
            lines.append(
                f"  🔍 SEO: {channel_attribution.organic_percent:.1f}% "
                f"| 💰 SEM: {channel_attribution.paid_percent:.1f}% "
                f"| 🔗 Directo: {channel_attribution.direct_percent:.1f}% "
                f"| 🌐 Referral: {channel_attribution.referral_percent:.1f}%"
            )
            lines.append(f"  Total sesiones: {channel_attribution.total_sessions}")

        # Sección GEO
        if geo_insights:
            top_cities = sorted(geo_insights, key=lambda g: g.sessions, reverse=True)[
                :5
            ]
            lines.append("")
            lines.append("📍 *Top Ciudades:*")
            for g in top_cities:
                zone_icon = "✅" if g.is_target_zone else "⚠️"
                lines.append(f"  {zone_icon} {g.city}: {g.sessions} sesiones")
            if geo_out_of_zone_percent > 0:
                lines.append(
                    f"  Fuera de zona objetivo: {geo_out_of_zone_percent:.1f}%"
                )

        # Sección de la ficha de Google (paquete local de Maps)
        if ficha_resumen is not None and ficha_resumen.impresiones_totales > 0:
            lines.append("")
            lines.append(
                f"🗺️ *Ficha de Google ({ficha_resumen.dias_analizados}d):* "
                f"{ficha_resumen.impresiones_totales} impresiones "
                f"({ficha_resumen.variacion_impresiones_percent:+.1f}% vs. período previo)"
            )
            lines.append(
                f"  Maps: {ficha_resumen.impresiones_maps} "
                f"| Search: {ficha_resumen.impresiones_search} "
                f"| Clics al sitio: {ficha_resumen.clics_sitio} "
                f"| Llamadas: {ficha_resumen.llamadas} "
                f"| Indicaciones: {ficha_resumen.solicitudes_indicaciones}"
            )

            if ficha_terminos:
                descubrimiento = [t for t in ficha_terminos if not t.es_de_marca]
                impresiones_marca = sum(
                    t.impresiones for t in ficha_terminos if t.es_de_marca
                )
                impresiones_desc = sum(t.impresiones for t in descubrimiento)
                total_terminos = impresiones_marca + impresiones_desc
                if total_terminos > 0:
                    pct_desc = round(impresiones_desc / total_terminos * 100, 1)
                    lines.append(
                        f"  Descubrimiento: {pct_desc:.1f}% | Marca: {100 - pct_desc:.1f}%"
                    )
                top_desc = sorted(
                    descubrimiento, key=lambda t: t.impresiones, reverse=True
                )[:3]
                if top_desc:
                    detalle = ", ".join(
                        f"`{t.termino}` ({t.impresiones})" for t in top_desc
                    )
                    lines.append(f"  Top descubrimiento: {detalle}")

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
