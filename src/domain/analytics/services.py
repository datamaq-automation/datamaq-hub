"""Servicios de dominio puros para cálculo de métricas, anomalías y guardrails."""

import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.domain.analytics.entities import (
    AnomalyAlert,
    CampaignMetric,
    ConversionInsight,
    GeoTrafficInsight,
    MetricaFicha,
    ResenaFicha,
    SearchTermInsight,
    TerminoBusquedaFicha,
    TrafficSourceInsight,
)
from src.domain.analytics.exceptions import (
    BudgetLimitViolationException,
    InvalidMarketingActionException,
    PublicacionFichaInvalidaException,
    RespuestaResenaInvalidaException,
)
from src.domain.analytics.value_objects import (
    AnomalySeverity,
    AnomalyType,
    CalculatedKpis,
    ChannelAttribution,
    MarketingActionType,
    PacingSeverity,
    ResumenFicha,
)

DEFAULT_NEGATIVE_PATTERNS: tuple[str, ...] = (
    "curso",
    "cursos",
    "tutorial",
    "pdf",
    "gratis",
    "free",
    "arduino",
    "raspberry",
    "tesis",
    "universidad",
    "empleo",
    "sueldo",
    "curriculum",
    "manual",
    "descargar",
    "login",
    "portal",
    "capacitacion",
    "capacitaciones",
    "taller",
    "facultad",
    "estudiante",
)

# Ciudades dentro de la zona objetivo de DataMaq (GBA Norte + AMBA)
TARGET_CITIES: frozenset[str] = frozenset(
    {
        "pilar",
        "garín",
        "garin",
        "tigre",
        "campana",
        "san martín",
        "san martin",
        "vicente lópez",
        "vicente lopez",
        "san fernando",
        "malvinas argentinas",
        "escobar",
        "san isidro",
        "olivos",
        "martínez",
        "martinez",
        "del viso",
        "los polvorines",
        "grand bourg",
        "buenos aires",
    }
)


# Métricas diarias de la Business Profile Performance API agrupadas por eje de lectura
FICHA_METRICAS_MAPS: tuple[str, ...] = (
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
)
FICHA_METRICAS_SEARCH: tuple[str, ...] = (
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
)
FICHA_METRICA_CLICS_SITIO = "WEBSITE_CLICKS"
FICHA_METRICA_LLAMADAS = "CALL_CLICKS"
FICHA_METRICA_INDICACIONES = "BUSINESS_DIRECTION_REQUESTS"
FICHA_METRICA_CONVERSACIONES = "BUSINESS_CONVERSATIONS"

# Tokens que identifican una búsqueda de marca frente a una de descubrimiento.
# La API ya no expone el corte marca/descubrimiento (murió con la Insights API v4),
# por lo que se aproxima sobre el texto del término.
FICHA_TOKENS_DE_MARCA: tuple[str, ...] = ("datamaq", "data maq")

# Límites duros impuestos por la API de Google, no política de negocio.
FICHA_MAX_CHARS_PUBLICACION = 1500
FICHA_MAX_CHARS_RESPUESTA = 4096
FICHA_CTA_TYPES_VALIDOS: frozenset[str] = frozenset(
    {"BOOK", "ORDER", "SHOP", "LEARN_MORE", "SIGN_UP", "CALL"}
)

# El §7 del plan de Fase 4 exige que el enlace de la ficha apunte al sitio con UTM propio.
FICHA_HOSTS_PERMITIDOS: frozenset[str] = frozenset(
    {"datamaq.com.ar", "www.datamaq.com.ar"}
)
FICHA_UTM_CAMPAIGN_ESPERADA = "gbp"

RFC3339_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


class BudgetPacingCalculatorService:
    """Calcula determinísticamente el ritmo de consumo del presupuesto publicitario."""

    @staticmethod
    def calculate_pacing(
        spent_today_ars: float,
        budget_limit_ars: float,
        current_hour_local: int = 12,
    ) -> tuple[float, float, PacingSeverity]:
        """Calcula el porcentaje gastado, proyección de gasto del día y severidad."""
        if budget_limit_ars <= 0:
            return 0.0, spent_today_ars, PacingSeverity.NORMAL

        pacing_percent = round((spent_today_ars / budget_limit_ars) * 100.0, 2)

        # Proyección horaria en ventana comercial (07:30 a 18:30 = ~11 horas)
        if 7 <= current_hour_local <= 19:
            elapsed_fraction = max(0.1, min(1.0, (current_hour_local - 7) / 11.0))
            projected_daily_spend = round(spent_today_ars / elapsed_fraction, 2)
        else:
            projected_daily_spend = round(spent_today_ars, 2)

        if spent_today_ars > budget_limit_ars:
            severity = PacingSeverity.EXCEDIDO
        elif pacing_percent >= 85.0 or (
            projected_daily_spend > budget_limit_ars * 1.15 and current_hour_local < 16
        ):
            severity = PacingSeverity.PRECAUCION
        elif spent_today_ars == 0.0 and current_hour_local >= 12:
            severity = PacingSeverity.SIN_TRAFICO
        else:
            severity = PacingSeverity.NORMAL

        return pacing_percent, projected_daily_spend, severity


class MetricCalculatorService:
    """Calcula KPIs agregados y ratios matemáticos sin riesgo de división por cero."""

    @staticmethod
    def calculate_kpis(
        impressions: int,
        clicks: int,
        cost_ars: float,
        conversions: float,
        spent_today_ars: float,
        budget_limit_ars: float,
        current_hour_local: int = 12,
    ) -> CalculatedKpis:
        """Genera el objeto inmutable CalculatedKpis consolidado."""
        ctr = round((clicks / impressions * 100.0), 2) if impressions > 0 else 0.0
        cpc = round((cost_ars / clicks), 2) if clicks > 0 else 0.0
        cpa = round((cost_ars / conversions), 2) if conversions > 0 else 0.0
        conv_rate = round((conversions / clicks * 100.0), 2) if clicks > 0 else 0.0

        pacing_pct, projected_spend, _ = BudgetPacingCalculatorService.calculate_pacing(
            spent_today_ars=spent_today_ars,
            budget_limit_ars=budget_limit_ars,
            current_hour_local=current_hour_local,
        )

        return CalculatedKpis(
            ctr_percent=ctr,
            cpc_avg_ars=cpc,
            cpa_ars=cpa,
            conversion_rate_percent=conv_rate,
            pacing_percent=pacing_pct,
            budget_limit_ars=round(budget_limit_ars, 2),
            spent_today_ars=round(spent_today_ars, 2),
            projected_daily_spend_ars=projected_spend,
        )


class SearchTermEvaluatorService:
    """Evalúa términos de búsqueda reales para detectar oportunidades y palabras negativas."""

    @staticmethod
    def evaluate_terms(
        raw_terms: Sequence[dict[str, Any]],
        custom_negative_patterns: Sequence[str] | None = None,
    ) -> list[SearchTermInsight]:
        """Clasifica los términos identificando consultas no comerciales o derrochadoras."""
        patterns = (
            tuple(custom_negative_patterns)
            if custom_negative_patterns is not None
            else DEFAULT_NEGATIVE_PATTERNS
        )
        insights: list[SearchTermInsight] = []

        for item in raw_terms:
            term = str(item.get("term", item.get("search_term", ""))).strip()
            if not term:
                continue

            impressions = int(item.get("impressions", 0))
            clicks = int(item.get("clicks", 0))
            cost_ars = float(item.get("cost_ars", 0.0))
            conversions = float(item.get("conversions", 0.0))

            term_lower = term.lower()
            is_neg = False
            reason = ""

            for pat in patterns:
                if pat in term_lower:
                    is_neg = True
                    reason = f"Coincide con patrón irrelevante '{pat}'"
                    break

            if not is_neg and clicks >= 3 and conversions == 0 and cost_ars > 0:
                is_neg = True
                reason = "Gasto reiterado con 0 conversiones"

            insights.append(
                SearchTermInsight(
                    term=term,
                    impressions=impressions,
                    clicks=clicks,
                    cost_ars=cost_ars,
                    conversions=conversions,
                    is_negative_candidate=is_neg,
                    reason=reason,
                )
            )

        return insights


class AnomalyDetectionService:
    """Detección determinística de anomalías mediante reglas de negocio auditables."""

    @staticmethod
    def detect_anomalies(
        kpis: CalculatedKpis,
        campaigns: Sequence[CampaignMetric],
        conversions: Sequence[ConversionInsight],
        search_terms: Sequence[SearchTermInsight],
        current_hour_local: int = 12,
        channel_attribution: ChannelAttribution | None = None,
        geo_out_of_zone_percent: float | None = None,
    ) -> list[AnomalyAlert]:
        """Evalúa las reglas y retorna la lista de anomalías encontradas."""
        anomalies: list[AnomalyAlert] = []

        # 1. Regla de presupuesto / sobregasto
        if kpis.spent_today_ars > kpis.budget_limit_ars:
            anomalies.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.GASTO_ACELERADO,
                    severity=AnomalySeverity.CRITICAL,
                    titulo="Límite Diario Excedido",
                    descripcion=(
                        f"Gasto actual de ${kpis.spent_today_ars:,.2f} ARS superó el "
                        f"límite fijado de ${kpis.budget_limit_ars:,.2f} ARS."
                    ),
                    metrica_observada=f"Pacing: {kpis.pacing_percent:.1f}%",
                    recomendacion="Pausar o revisar campañas de inmediato.",
                )
            )
        elif kpis.pacing_percent >= 85.0 and current_hour_local < 15:
            anomalies.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.GASTO_ACELERADO,
                    severity=AnomalySeverity.WARNING,
                    titulo="Consumo Rápido de Presupuesto",
                    descripcion=(
                        f"Se ha consumido el {kpis.pacing_percent:.1f}% del presupuesto antes "
                        f"de las 15:00 hs (gasto: ${kpis.spent_today_ars:,.2f} ARS)."
                    ),
                    metrica_observada=f"Pacing: {kpis.pacing_percent:.1f}%",
                    recomendacion="Monitorear ritmo de clics en las próximas horas.",
                )
            )

        # 2. Regla de campañas activas sin tráfico
        for camp in campaigns:
            if (
                camp.status == "ENABLED"
                and camp.impressions == 0
                and current_hour_local >= 11
            ):
                anomalies.append(
                    AnomalyAlert(
                        anomaly_type=AnomalyType.SIN_IMPRESIONES,
                        severity=AnomalySeverity.WARNING,
                        titulo=f"Campaña '{camp.name}' sin impresiones",
                        descripcion="La campaña está habilitada pero no ha registrado impresiones hoy.",
                        metrica_observada="0 impresiones",
                        recomendacion="Verificar aprobación de anuncios, pujas y saldo en Google Ads.",
                    )
                )
            elif (
                camp.status == "ENABLED"
                and 0 < camp.impressions < 3
                and current_hour_local >= 13
            ):
                anomalies.append(
                    AnomalyAlert(
                        anomaly_type=AnomalyType.SUB_ENTREGA_SEM,
                        severity=AnomalySeverity.WARNING,
                        titulo=f"Sub-entrega Crítica en '{camp.name}'",
                        descripcion=(
                            f"La campaña lleva solo {camp.impressions} impresiones pasadas las "
                            f"{current_hour_local}:00 hs. Posible puja insuficiente o palabras clave con bajo volumen."
                        ),
                        metrica_observada=f"{camp.impressions} impresiones a las {current_hour_local}:00 hs",
                        recomendacion="Revisar concordancias en campaigns.yaml, ampliar términos o verificar Quality Score.",
                    )
                )

        # 3. Regla de conversiones detectadas
        total_conv_events = sum(c.event_count for c in conversions)
        if total_conv_events > 0:
            anomalies.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.CONVERSION_DETECTADA,
                    severity=AnomalySeverity.INFO,
                    titulo="Conversiones Web Registradas",
                    descripcion=f"Se registraron {total_conv_events} eventos de conversión en el sitio.",
                    metrica_observada=f"{total_conv_events} conversiones",
                    recomendacion="Revisar grabaciones de intención en Clarity o contactar al prospecto.",
                )
            )

        # 4. Regla de términos negativos a excluir
        for term in search_terms:
            if term.is_negative_candidate:
                anomalies.append(
                    AnomalyAlert(
                        anomaly_type=AnomalyType.TERMINO_IRRELEVANTE,
                        severity=AnomalySeverity.WARNING,
                        titulo=f"Palabra Irrelevante: '{term.term}'",
                        descripcion=f"Término que consumió presupuesto sin intención B2B: {term.reason}.",
                        metrica_observada=f"Costo: ${term.cost_ars:,.2f} ARS, {term.clicks} clics",
                        recomendacion=f"Agregar '{term.term}' como palabra clave negativa compartida.",
                    )
                )

        # 5. Regla de dependencia excesiva en SEM (>80% tráfico pago)
        if channel_attribution is not None:
            if (
                channel_attribution.paid_percent > 80.0
                and channel_attribution.total_sessions >= 10
            ):
                anomalies.append(
                    AnomalyAlert(
                        anomaly_type=AnomalyType.DEPENDENCIA_SEM,
                        severity=AnomalySeverity.WARNING,
                        titulo="Dependencia Excesiva de Google Ads",
                        descripcion=(
                            f"El {channel_attribution.paid_percent:.1f}% del tráfico proviene de SEM. "
                            f"Solo {channel_attribution.organic_percent:.1f}% es orgánico."
                        ),
                        metrica_observada=(
                            f"SEM: {channel_attribution.paid_percent:.1f}% | "
                            f"SEO: {channel_attribution.organic_percent:.1f}%"
                        ),
                        recomendacion="Invertir en contenido SEO (blog técnico B2B) para reducir dependencia de Ads.",
                    )
                )

            # 6. Regla de SEO bajo (orgánico < 10% con al menos 20 sesiones totales)
            if (
                channel_attribution.organic_percent < 10.0
                and channel_attribution.total_sessions >= 20
            ):
                anomalies.append(
                    AnomalyAlert(
                        anomaly_type=AnomalyType.SEO_BAJO,
                        severity=AnomalySeverity.WARNING,
                        titulo="Tráfico Orgánico Muy Bajo",
                        descripcion=(
                            f"Solo el {channel_attribution.organic_percent:.1f}% del tráfico es orgánico "
                            f"({channel_attribution.total_sessions} sesiones totales)."
                        ),
                        metrica_observada=f"Orgánico: {channel_attribution.organic_percent:.1f}%",
                        recomendacion="Activar Google Search Console, crear landing pages con keywords long-tail B2B.",
                    )
                )

        # 7. Regla de tráfico fuera de zona objetivo (>30%)
        if geo_out_of_zone_percent is not None and geo_out_of_zone_percent > 30.0:
            anomalies.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.TRAFICO_FUERA_ZONA,
                    severity=AnomalySeverity.WARNING,
                    titulo="Tráfico Fuera de Zona Objetivo",
                    descripcion=(
                        f"El {geo_out_of_zone_percent:.1f}% del tráfico proviene de ciudades "
                        f"fuera de GBA Norte / AMBA."
                    ),
                    metrica_observada=f"Fuera de zona: {geo_out_of_zone_percent:.1f}%",
                    recomendacion="Revisar segmentación geográfica en Google Ads y ajustar exclusiones.",
                )
            )

        return anomalies


class TrafficAttributionService:
    """Calcula la distribución de tráfico por canal (SEO/SEM/Directo/Referral)."""

    @staticmethod
    def calculate_attribution(
        sources: Sequence[TrafficSourceInsight],
    ) -> ChannelAttribution:
        """Clasifica las fuentes en canales y calcula porcentajes."""
        total = sum(s.sessions for s in sources)
        if total == 0:
            return ChannelAttribution(
                organic_percent=0.0,
                paid_percent=0.0,
                direct_percent=0.0,
                referral_percent=0.0,
                other_percent=0.0,
                total_sessions=0,
            )

        organic = sum(s.sessions for s in sources if s.medium == "organic")
        paid = sum(s.sessions for s in sources if s.medium in ("cpc", "ppc", "paid"))
        direct = sum(
            s.sessions
            for s in sources
            if s.medium in ("(none)", "(not set)")
            and s.source in ("(direct)", "direct")
        )
        referral = sum(s.sessions for s in sources if s.medium == "referral")
        other = total - organic - paid - direct - referral

        return ChannelAttribution(
            organic_percent=round(organic / total * 100, 1),
            paid_percent=round(paid / total * 100, 1),
            direct_percent=round(direct / total * 100, 1),
            referral_percent=round(referral / total * 100, 1),
            other_percent=round(other / total * 100, 1),
            total_sessions=total,
        )


class GeoAnalysisService:
    """Analiza la distribución geográfica del tráfico contra la zona objetivo."""

    @staticmethod
    def classify_geo(
        geo_rows: Sequence[GeoTrafficInsight],
    ) -> tuple[int, int, float]:
        """Retorna (sesiones_en_zona, sesiones_fuera, porcentaje_fuera)."""
        in_zone = sum(g.sessions for g in geo_rows if g.is_target_zone)
        out_zone = sum(g.sessions for g in geo_rows if not g.is_target_zone)
        total = in_zone + out_zone
        pct_out = round(out_zone / total * 100, 1) if total > 0 else 0.0
        return in_zone, out_zone, pct_out


class FichaLocalAnalysisService:
    """Análisis determinístico de la ficha de Google Business Profile (paquete local de Maps)."""

    @staticmethod
    def resumir_metricas(
        metricas: Sequence[MetricaFicha],
        dias_analizados: int,
        metricas_periodo_previo: Sequence[MetricaFicha] = (),
    ) -> ResumenFicha:
        """Agrega las series diarias en totales por eje y calcula la variación contra el período previo."""

        def _total(serie: Sequence[MetricaFicha], nombres: Sequence[str]) -> int:
            return sum(m.valor for m in serie if m.metrica in nombres)

        impresiones_maps = _total(metricas, FICHA_METRICAS_MAPS)
        impresiones_search = _total(metricas, FICHA_METRICAS_SEARCH)
        impresiones_totales = impresiones_maps + impresiones_search

        previas = _total(
            metricas_periodo_previo, FICHA_METRICAS_MAPS + FICHA_METRICAS_SEARCH
        )
        if previas > 0:
            variacion = round((impresiones_totales - previas) / previas * 100.0, 1)
        else:
            variacion = 0.0

        return ResumenFicha(
            dias_analizados=dias_analizados,
            impresiones_maps=impresiones_maps,
            impresiones_search=impresiones_search,
            impresiones_totales=impresiones_totales,
            clics_sitio=_total(metricas, (FICHA_METRICA_CLICS_SITIO,)),
            llamadas=_total(metricas, (FICHA_METRICA_LLAMADAS,)),
            solicitudes_indicaciones=_total(metricas, (FICHA_METRICA_INDICACIONES,)),
            conversaciones=_total(metricas, (FICHA_METRICA_CONVERSACIONES,)),
            impresiones_periodo_previo=previas,
            variacion_impresiones_percent=variacion,
        )

    @staticmethod
    def clasificar_terminos(
        raw_terms: Sequence[dict[str, Any]],
    ) -> list[TerminoBusquedaFicha]:
        """Separa términos de marca de términos de descubrimiento, que son los que traen clientes nuevos."""
        terminos: list[TerminoBusquedaFicha] = []
        for item in raw_terms:
            termino = str(item.get("termino", item.get("searchKeyword", ""))).strip()
            if not termino:
                continue
            termino_lower = termino.lower()
            terminos.append(
                TerminoBusquedaFicha(
                    termino=termino,
                    impresiones=int(item.get("impresiones", 0)),
                    es_de_marca=any(
                        token in termino_lower for token in FICHA_TOKENS_DE_MARCA
                    ),
                )
            )
        return terminos

    @staticmethod
    def detectar_anomalias(
        resumen: ResumenFicha | None,
        resenas: Sequence[ResenaFicha],
        dias_desde_ultima_publicacion: int | None = None,
        umbral_caida_impresiones_percent: float = -25.0,
        min_resenas_competitivo: int = 5,
        umbral_rating_bajo: float = 4.0,
        max_dias_sin_publicar: int = 14,
    ) -> list[AnomalyAlert]:
        """Aplica las reglas de salud de la ficha derivadas de los §8 a §10 del plan de Fase 4."""
        anomalias: list[AnomalyAlert] = []

        # 1. Caída de impresiones respecto del período previo
        if (
            resumen is not None
            and resumen.impresiones_periodo_previo > 0
            and resumen.variacion_impresiones_percent
            <= umbral_caida_impresiones_percent
        ):
            anomalias.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.FICHA_IMPRESIONES_EN_CAIDA,
                    severity=AnomalySeverity.WARNING,
                    titulo="Caída de Impresiones en la Ficha de Google",
                    descripcion=(
                        f"Las impresiones cayeron {abs(resumen.variacion_impresiones_percent):.1f}% "
                        f"respecto del período previo ({resumen.impresiones_totales} contra "
                        f"{resumen.impresiones_periodo_previo})."
                    ),
                    metrica_observada=(
                        f"Impresiones: {resumen.impresiones_totales} "
                        f"({resumen.variacion_impresiones_percent:+.1f}%)"
                    ),
                    recomendacion="Verificar que la ficha siga activa y publicar contenido nuevo.",
                )
            )

        # 2. Reseñas sin responder — la tasa de respuesta es en sí misma señal de ranking (§8)
        sin_responder = [r for r in resenas if not r.tiene_respuesta]
        if sin_responder:
            anomalias.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.FICHA_RESENA_SIN_RESPONDER,
                    severity=AnomalySeverity.WARNING,
                    titulo=f"{len(sin_responder)} reseña(s) sin responder",
                    descripcion=(
                        "Hay reseñas sin respuesta en la ficha. Contestar todas, incluidas las "
                        "negativas, en tono técnico y sin defensividad."
                    ),
                    metrica_observada=f"{len(sin_responder)} de {len(resenas)} sin responder",
                    recomendacion="Responder con reply_to_gbp_review antes del próximo ciclo semanal.",
                )
            )

        # 3. Volumen de reseñas por debajo del piso competitivo del paquete local (§8)
        if resenas and len(resenas) < min_resenas_competitivo:
            anomalias.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.FICHA_POCAS_RESENAS,
                    severity=AnomalySeverity.INFO,
                    titulo="Volumen de Reseñas Insuficiente",
                    descripcion=(
                        f"La ficha tiene {len(resenas)} reseñas. Por debajo de "
                        f"{min_resenas_competitivo} compite en desventaja en el paquete local."
                    ),
                    metrica_observada=f"{len(resenas)} reseñas",
                    recomendacion="Pedir reseña al cierre de obra, cuando el ahorro ya se ve en la factura.",
                )
            )

        # 4. Rating promedio bajo
        if resenas:
            promedio = round(sum(r.estrellas for r in resenas) / len(resenas), 2)
            if promedio < umbral_rating_bajo:
                anomalias.append(
                    AnomalyAlert(
                        anomaly_type=AnomalyType.FICHA_RATING_BAJO,
                        severity=AnomalySeverity.CRITICAL,
                        titulo="Rating Promedio Bajo",
                        descripcion=(
                            f"El promedio de la ficha es {promedio} estrellas sobre "
                            f"{len(resenas)} reseñas."
                        ),
                        metrica_observada=f"{promedio} estrellas",
                        recomendacion="Revisar las reseñas negativas y responderlas en tono técnico.",
                    )
                )

        # 5. Inactividad: las publicaciones caducan y la inactividad es señal negativa (§10)
        if (
            dias_desde_ultima_publicacion is not None
            and dias_desde_ultima_publicacion > max_dias_sin_publicar
        ):
            anomalias.append(
                AnomalyAlert(
                    anomaly_type=AnomalyType.FICHA_SIN_PUBLICACIONES,
                    severity=AnomalySeverity.WARNING,
                    titulo="Ficha sin Publicaciones Recientes",
                    descripcion=(
                        f"Pasaron {dias_desde_ultima_publicacion} días desde la última publicación. "
                        f"Las publicaciones caducan y la inactividad es una señal negativa."
                    ),
                    metrica_observada=f"{dias_desde_ultima_publicacion} días sin publicar",
                    recomendacion="Publicar la siguiente guía del calendario semanal de la Fase 3.",
                )
            )

        return anomalias


class MarketingActionGuardrailService:
    """Guardrails determinísticos de post-procesamiento para validar acciones de agentes."""

    @staticmethod
    def validate_action(
        action_type: MarketingActionType,
        params: dict[str, Any],
        max_daily_budget_ars: float = 1500.0,
        max_cpc_ars: float = 500.0,
    ) -> None:
        """Valida que la acción cumpla las políticas duras del negocio."""
        if action_type == MarketingActionType.ADJUST_BUDGET:
            new_budget = float(params.get("new_budget_ars", 0.0))
            if new_budget <= 0:
                raise InvalidMarketingActionException(
                    "El nuevo presupuesto debe ser mayor a 0."
                )
            if new_budget > max_daily_budget_ars:
                raise BudgetLimitViolationException(
                    f"El presupuesto solicitado (${new_budget:,.2f} ARS) supera el límite "
                    f"máximo permitido de ${max_daily_budget_ars:,.2f} ARS."
                )

        elif action_type == MarketingActionType.ADJUST_BID:
            new_cpc = float(params.get("new_cpc_ars", 0.0))
            if new_cpc <= 0:
                raise InvalidMarketingActionException(
                    "El CPC máximo debe ser mayor a 0."
                )
            if new_cpc > max_cpc_ars:
                raise InvalidMarketingActionException(
                    f"El CPC propuesto (${new_cpc:,.2f} ARS) supera el límite máximo "
                    f"de seguridad de ${max_cpc_ars:,.2f} ARS."
                )

        elif action_type == MarketingActionType.ADD_NEGATIVE_KEYWORD:
            keyword = str(params.get("keyword", "")).strip()
            if not keyword:
                raise InvalidMarketingActionException(
                    "La palabra clave negativa no puede estar vacía."
                )

        elif action_type in (
            MarketingActionType.PAUSE_CAMPAIGN,
            MarketingActionType.ENABLE_CAMPAIGN,
        ):
            campaign_id = str(params.get("campaign_id", "")).strip()
            if not campaign_id:
                raise InvalidMarketingActionException(
                    "El ID de campaña es obligatorio."
                )

        elif action_type == MarketingActionType.GBP_CREATE_POST:
            MarketingActionGuardrailService._validar_publicacion_ficha(params)

        elif action_type == MarketingActionType.GBP_REPLY_REVIEW:
            MarketingActionGuardrailService._validar_respuesta_resena(params)

    @staticmethod
    def _validar_publicacion_ficha(params: dict[str, Any]) -> None:
        """Valida una publicación propuesta para la ficha contra los límites de la API y del §7."""
        summary = str(params.get("summary", "")).strip()
        if not summary:
            raise PublicacionFichaInvalidaException(
                "El texto de la publicación no puede estar vacío."
            )
        if len(summary) > FICHA_MAX_CHARS_PUBLICACION:
            raise PublicacionFichaInvalidaException(
                f"La publicación tiene {len(summary)} caracteres y el máximo es "
                f"{FICHA_MAX_CHARS_PUBLICACION}."
            )

        cta_type = str(params.get("cta_type", "LEARN_MORE")).strip().upper()
        if cta_type not in FICHA_CTA_TYPES_VALIDOS:
            raise PublicacionFichaInvalidaException(
                f"El tipo de llamada a la acción '{cta_type}' no es válido. "
                f"Válidos: {', '.join(sorted(FICHA_CTA_TYPES_VALIDOS))}."
            )

        cta_url = str(params.get("cta_url", "")).strip()
        if not cta_url:
            raise PublicacionFichaInvalidaException(
                "La publicación debe enlazar al sitio; cta_url es obligatoria."
            )

        parsed = urlparse(cta_url)
        if parsed.scheme != "https":
            raise PublicacionFichaInvalidaException(
                f"El enlace debe usar https, no '{parsed.scheme or 'ninguno'}'."
            )
        if parsed.hostname not in FICHA_HOSTS_PERMITIDOS:
            raise PublicacionFichaInvalidaException(
                f"El enlace apunta a '{parsed.hostname}'. Solo se permite enlazar a "
                f"{', '.join(sorted(FICHA_HOSTS_PERMITIDOS))}."
            )

        utm_campaign = parse_qs(parsed.query).get("utm_campaign", [])
        if FICHA_UTM_CAMPAIGN_ESPERADA not in utm_campaign:
            raise PublicacionFichaInvalidaException(
                f"El enlace debe llevar utm_campaign={FICHA_UTM_CAMPAIGN_ESPERADA} para que "
                f"el tráfico desde Maps se pueda atribuir en GA4."
            )

        schedule_time = params.get("schedule_time")
        if schedule_time is not None and not RFC3339_REGEX.match(str(schedule_time)):
            raise PublicacionFichaInvalidaException(
                f"schedule_time debe estar en formato RFC3339 (ej. 2026-09-15T09:00:00Z), "
                f"se recibió '{schedule_time}'."
            )

    @staticmethod
    def _validar_respuesta_resena(params: dict[str, Any]) -> None:
        """Valida la respuesta a una reseña y protege contra sobrescrituras accidentales."""
        review_id = str(params.get("review_id", "")).strip()
        if not review_id:
            raise RespuestaResenaInvalidaException(
                "El identificador de la reseña es obligatorio."
            )

        comment = str(params.get("comment", "")).strip()
        if not comment:
            raise RespuestaResenaInvalidaException(
                "La respuesta a la reseña no puede estar vacía."
            )
        if len(comment) > FICHA_MAX_CHARS_RESPUESTA:
            raise RespuestaResenaInvalidaException(
                f"La respuesta tiene {len(comment)} caracteres y el máximo es "
                f"{FICHA_MAX_CHARS_RESPUESTA}."
            )

        if bool(params.get("tiene_respuesta", False)) and not bool(
            params.get("overwrite", False)
        ):
            raise RespuestaResenaInvalidaException(
                f"La reseña '{review_id}' ya tiene una respuesta publicada. "
                f"Pasá overwrite=True si realmente querés reemplazarla."
            )
