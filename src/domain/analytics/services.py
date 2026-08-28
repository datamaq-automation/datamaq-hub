"""Servicios de dominio puros para cálculo de métricas, anomalías y guardrails."""

from collections.abc import Sequence
from typing import Any

from src.domain.analytics.entities import (
    AnomalyAlert,
    CampaignMetric,
    ConversionInsight,
    SearchTermInsight,
)
from src.domain.analytics.exceptions import (
    BudgetLimitViolationException,
    InvalidMarketingActionException,
)
from src.domain.analytics.value_objects import (
    AnomalySeverity,
    AnomalyType,
    CalculatedKpis,
    MarketingActionType,
    PacingSeverity,
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

        return anomalies


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
