"""Tests unitarios para servicios puros del dominio de analítica."""

import pytest

from src.domain.analytics.entities import (
    CampaignMetric,
    ConversionInsight,
    GeoTrafficInsight,
    MetricaFicha,
    ResenaFicha,
    SearchTermInsight,
    TrafficSourceInsight,
)
from src.domain.analytics.exceptions import (
    BudgetLimitViolationException,
    InvalidMarketingActionException,
    PublicacionFichaInvalidaException,
    RespuestaResenaInvalidaException,
)
from src.domain.analytics.services import (
    AnomalyDetectionService,
    BudgetPacingCalculatorService,
    FichaLocalAnalysisService,
    GeoAnalysisService,
    MarketingActionGuardrailService,
    MetricCalculatorService,
    SearchTermEvaluatorService,
    TrafficAttributionService,
)
from src.domain.analytics.value_objects import (
    AnomalySeverity,
    AnomalyType,
    CalculatedKpis,
    ChannelAttribution,
    MarketingActionType,
    PacingSeverity,
)


def test_budget_pacing_calculator_normal() -> None:
    """Verifica cálculo normal de pacing dentro de presupuesto."""
    pacing_pct, _projected, severity = BudgetPacingCalculatorService.calculate_pacing(
        spent_today_ars=500.0,
        budget_limit_ars=1500.0,
        current_hour_local=12,
    )
    assert pacing_pct == 33.33
    assert _projected > 0
    assert severity == PacingSeverity.NORMAL


def test_budget_pacing_calculator_exceeded() -> None:
    """Verifica detección de sobregasto."""
    pacing_pct, _projected, severity = BudgetPacingCalculatorService.calculate_pacing(
        spent_today_ars=1600.0,
        budget_limit_ars=1500.0,
        current_hour_local=14,
    )
    assert pacing_pct == 106.67
    assert severity == PacingSeverity.EXCEDIDO


def test_budget_pacing_calculator_sin_trafico() -> None:
    """Verifica estado sin tráfico a mitad de la jornada comercial."""
    pacing_pct, _projected, severity = BudgetPacingCalculatorService.calculate_pacing(
        spent_today_ars=0.0,
        budget_limit_ars=1500.0,
        current_hour_local=14,
    )
    assert pacing_pct == 0.0
    assert severity == PacingSeverity.SIN_TRAFICO


def test_budget_pacing_calculator_zero_budget() -> None:
    """Verifica manejo seguro de presupuesto cero."""
    pacing_pct, _projected, severity = BudgetPacingCalculatorService.calculate_pacing(
        spent_today_ars=100.0,
        budget_limit_ars=0.0,
        current_hour_local=12,
    )
    assert pacing_pct == 0.0
    assert severity == PacingSeverity.NORMAL


def test_metric_calculator_service() -> None:
    """Verifica cálculo de KPIs y protección contra división por cero."""
    # Caso con tráfico y conversiones
    kpis = MetricCalculatorService.calculate_kpis(
        impressions=1000,
        clicks=50,
        cost_ars=5000.0,
        conversions=5.0,
        spent_today_ars=800.0,
        budget_limit_ars=1500.0,
        current_hour_local=12,
    )
    assert kpis.ctr_percent == 5.0
    assert kpis.cpc_avg_ars == 100.0
    assert kpis.cpa_ars == 1000.0
    assert kpis.conversion_rate_percent == 10.0
    assert kpis.pacing_percent == 53.33

    # Caso con cero clics/impresiones (cero división)
    zero_kpis = MetricCalculatorService.calculate_kpis(
        impressions=0,
        clicks=0,
        cost_ars=0.0,
        conversions=0.0,
        spent_today_ars=0.0,
        budget_limit_ars=1500.0,
        current_hour_local=10,
    )
    assert zero_kpis.ctr_percent == 0.0
    assert zero_kpis.cpc_avg_ars == 0.0
    assert zero_kpis.cpa_ars == 0.0
    assert zero_kpis.conversion_rate_percent == 0.0


def test_search_term_evaluator_service() -> None:
    """Verifica clasificación heurística de palabras clave negativas."""
    raw_terms = [
        {
            "term": "telemetria industrial maquinas plc",
            "impressions": 100,
            "clicks": 5,
            "cost_ars": 200.0,
            "conversions": 1,
        },
        {
            "term": "curso gratis arduino plc",
            "impressions": 40,
            "clicks": 3,
            "cost_ars": 150.0,
            "conversions": 0,
        },
        {
            "term": "sueldo operario inyectora",
            "impressions": 10,
            "clicks": 4,
            "cost_ars": 180.0,
            "conversions": 0,
        },
        {
            "term": "servicio mantenimiento tableros",
            "impressions": 20,
            "clicks": 1,
            "cost_ars": 50.0,
            "conversions": 0,
        },
    ]

    insights = SearchTermEvaluatorService.evaluate_terms(raw_terms)
    assert len(insights) == 4
    # El primero es comercial B2B
    assert not insights[0].is_negative_candidate
    # El segundo tiene 'curso' y 'gratis'
    assert insights[1].is_negative_candidate
    # El tercero tiene 'sueldo'
    assert insights[2].is_negative_candidate
    # El cuarto es comercial con 1 clic (no alcanza umbral de desperdicio de 3 clics sin conv)
    assert not insights[3].is_negative_candidate


def test_anomaly_detection_service() -> None:
    """Verifica reglas de detección de anomalías."""
    kpis = CalculatedKpis(
        ctr_percent=2.5,
        cpc_avg_ars=120.0,
        cpa_ars=0.0,
        conversion_rate_percent=0.0,
        pacing_percent=95.0,
        budget_limit_ars=1500.0,
        spent_today_ars=1425.0,
        projected_daily_spend_ars=2000.0,
    )
    campaigns = [
        CampaignMetric(
            campaign_id="1",
            name="Retrofit IoT",
            status="ENABLED",
            impressions=0,
            clicks=0,
            cost_ars=0.0,
            conversions=0.0,
            cpc_avg_ars=0.0,
        )
    ]
    conversions = [
        ConversionInsight(event_name="whatsapp_click", event_count=2, total_users=2)
    ]
    search_terms = [
        SearchTermInsight(
            term="descargar pdf arduino",
            impressions=10,
            clicks=3,
            cost_ars=150.0,
            conversions=0.0,
            is_negative_candidate=True,
            reason="Coincide con patrón irrelevante 'pdf'",
        )
    ]

    anomalies = AnomalyDetectionService.detect_anomalies(
        kpis=kpis,
        campaigns=campaigns,
        conversions=conversions,
        search_terms=search_terms,
        current_hour_local=12,
    )

    types = [a.anomaly_type for a in anomalies]
    assert AnomalyType.GASTO_ACELERADO in types
    assert AnomalyType.SIN_IMPRESIONES in types
    assert AnomalyType.CONVERSION_DETECTADA in types
    assert AnomalyType.TERMINO_IRRELEVANTE in types


def test_marketing_action_guardrails() -> None:
    """Verifica cumplimiento de guardrails de post-procesamiento."""
    # 1. Presupuesto válido
    MarketingActionGuardrailService.validate_action(
        action_type=MarketingActionType.ADJUST_BUDGET,
        params={"new_budget_ars": 1200.0},
        max_daily_budget_ars=1500.0,
    )

    # 2. Presupuesto que excede límite
    with pytest.raises(BudgetLimitViolationException):
        MarketingActionGuardrailService.validate_action(
            action_type=MarketingActionType.ADJUST_BUDGET,
            params={"new_budget_ars": 2500.0},
            max_daily_budget_ars=1500.0,
        )

    # 3. CPC que excede límite de seguridad
    with pytest.raises(InvalidMarketingActionException):
        MarketingActionGuardrailService.validate_action(
            action_type=MarketingActionType.ADJUST_BID,
            params={"new_cpc_ars": 800.0},
            max_cpc_ars=500.0,
        )

    # 4. Palabra clave negativa vacía
    with pytest.raises(InvalidMarketingActionException):
        MarketingActionGuardrailService.validate_action(
            action_type=MarketingActionType.ADD_NEGATIVE_KEYWORD,
            params={"keyword": "   "},
        )


def test_traffic_attribution_100_percent_organic() -> None:
    """Verifica atribución de canal con 100% orgánico (SEO)."""
    sources = [
        TrafficSourceInsight(
            source="google",
            medium="organic",
            campaign="(not set)",
            sessions=50,
            active_users=45,
            conversions=2.0,
        )
    ]
    attr = TrafficAttributionService.calculate_attribution(sources)
    assert attr.organic_percent == 100.0
    assert attr.paid_percent == 0.0
    assert attr.direct_percent == 0.0
    assert attr.total_sessions == 50


def test_traffic_attribution_mixed_channels() -> None:
    """Verifica desglose porcentual de múltiples fuentes."""
    sources = [
        TrafficSourceInsight(
            source="google",
            medium="cpc",
            campaign="retrofit-iot",
            sessions=80,
            active_users=70,
            conversions=3.0,
        ),
        TrafficSourceInsight(
            source="google",
            medium="organic",
            campaign="(not set)",
            sessions=15,
            active_users=12,
            conversions=1.0,
        ),
        TrafficSourceInsight(
            source="(direct)",
            medium="(none)",
            campaign="(not set)",
            sessions=5,
            active_users=4,
            conversions=0.0,
        ),
    ]
    attr = TrafficAttributionService.calculate_attribution(sources)
    assert attr.total_sessions == 100
    assert attr.paid_percent == 80.0
    assert attr.organic_percent == 15.0
    assert attr.direct_percent == 5.0
    assert attr.referral_percent == 0.0


def test_traffic_attribution_empty() -> None:
    """Verifica manejo seguro de fuentes vacías sin división por cero."""
    attr = TrafficAttributionService.calculate_attribution([])
    assert attr.total_sessions == 0
    assert attr.organic_percent == 0.0
    assert attr.paid_percent == 0.0


def test_geo_analysis_target_zone() -> None:
    """Verifica clasificación geográfica en zona objetivo."""
    geos = [
        GeoTrafficInsight(
            city="Pilar",
            region="Buenos Aires",
            sessions=25,
            active_users=20,
            is_target_zone=True,
        ),
        GeoTrafficInsight(
            city="Garín",
            region="Buenos Aires",
            sessions=15,
            active_users=10,
            is_target_zone=True,
        ),
    ]
    in_z, out_z, pct_out = GeoAnalysisService.classify_geo(geos)
    assert in_z == 40
    assert out_z == 0
    assert pct_out == 0.0


def test_geo_analysis_mixed_zone() -> None:
    """Verifica porcentaje fuera de zona objetivo."""
    geos = [
        GeoTrafficInsight(
            city="Pilar",
            region="Buenos Aires",
            sessions=70,
            active_users=50,
            is_target_zone=True,
        ),
        GeoTrafficInsight(
            city="Córdoba",
            region="Córdoba",
            sessions=30,
            active_users=25,
            is_target_zone=False,
        ),
    ]
    in_z, out_z, pct_out = GeoAnalysisService.classify_geo(geos)
    assert in_z == 70
    assert out_z == 30
    assert pct_out == 30.0


def test_anomalies_seo_geo_and_sem_dependency() -> None:
    """Verifica detección de anomalías de SEO_BAJO, TRAFICO_FUERA_ZONA y DEPENDENCIA_SEM."""
    kpis = CalculatedKpis(
        ctr_percent=5.0,
        cpc_avg_ars=50.0,
        cpa_ars=500.0,
        conversion_rate_percent=10.0,
        pacing_percent=50.0,
        budget_limit_ars=1500.0,
        spent_today_ars=750.0,
        projected_daily_spend_ars=1200.0,
    )
    attribution = ChannelAttribution(
        organic_percent=5.0,
        paid_percent=85.0,
        direct_percent=10.0,
        referral_percent=0.0,
        other_percent=0.0,
        total_sessions=100,
    )

    anomalies = AnomalyDetectionService.detect_anomalies(
        kpis=kpis,
        campaigns=[],
        conversions=[],
        search_terms=[],
        current_hour_local=12,
        channel_attribution=attribution,
        geo_out_of_zone_percent=45.0,
    )

    types = [a.anomaly_type for a in anomalies]
    assert AnomalyType.DEPENDENCIA_SEM in types
    assert AnomalyType.SEO_BAJO in types
    assert AnomalyType.TRAFICO_FUERA_ZONA in types


def test_anomaly_sub_entrega_sem() -> None:
    """Verifica detección de sub-entrega crítica en campañas habilitadas con muy pocas impresiones."""
    kpis = CalculatedKpis(
        ctr_percent=0.0,
        cpc_avg_ars=0.0,
        cpa_ars=0.0,
        conversion_rate_percent=0.0,
        pacing_percent=0.0,
        budget_limit_ars=1500.0,
        spent_today_ars=0.0,
        projected_daily_spend_ars=0.0,
    )
    campaigns = [
        CampaignMetric(
            campaign_id="123",
            name="Calidad de Energia",
            status="ENABLED",
            impressions=2,
            clicks=0,
            cost_ars=0.0,
            conversions=0.0,
            cpc_avg_ars=0.0,
        )
    ]

    # Antes de las 13:00 no debe alertar sub-entrega
    anomalies_morning = AnomalyDetectionService.detect_anomalies(
        kpis=kpis,
        campaigns=campaigns,
        conversions=[],
        search_terms=[],
        current_hour_local=11,
    )
    types_morning = [a.anomaly_type for a in anomalies_morning]
    assert AnomalyType.SUB_ENTREGA_SEM not in types_morning

    # A partir de las 13:00 hs debe alertar SUB_ENTREGA_SEM
    anomalies_afternoon = AnomalyDetectionService.detect_anomalies(
        kpis=kpis,
        campaigns=campaigns,
        conversions=[],
        search_terms=[],
        current_hour_local=14,
    )
    types_afternoon = [a.anomaly_type for a in anomalies_afternoon]
    assert AnomalyType.SUB_ENTREGA_SEM in types_afternoon


def test_negative_pattern_capacitaciones() -> None:
    """Verifica que consultas de capacitacion y taller sean clasificadas como negativas."""
    raw_terms = [
        {
            "term": "capacitacion plc siemens",
            "impressions": 10,
            "clicks": 1,
            "cost_ars": 50.0,
            "conversions": 0,
        },
        {
            "term": "taller de electronica",
            "impressions": 5,
            "clicks": 1,
            "cost_ars": 40.0,
            "conversions": 0,
        },
        {
            "term": "banco de capacitores trifasico",
            "impressions": 20,
            "clicks": 2,
            "cost_ars": 100.0,
            "conversions": 1,
        },
    ]
    insights = SearchTermEvaluatorService.evaluate_terms(raw_terms)
    assert len(insights) == 3
    assert insights[0].is_negative_candidate is True
    assert "capacitacion" in insights[0].reason
    assert insights[1].is_negative_candidate is True
    assert "taller" in insights[1].reason
    assert insights[2].is_negative_candidate is False


# ==================== Ficha de Google Business Profile ====================


class TestFichaLocalAnalysisService:
    """Reglas de salud de la ficha derivadas de los §8 a §10 del plan de Fase 4."""

    @staticmethod
    def _metricas(valores: dict[str, int]) -> list[MetricaFicha]:
        return [
            MetricaFicha(fecha="2026-08-01", metrica=nombre, valor=valor)
            for nombre, valor in valores.items()
        ]

    def test_resumir_metricas_agrupa_por_eje(self) -> None:
        resumen = FichaLocalAnalysisService.resumir_metricas(
            metricas=self._metricas(
                {
                    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS": 10,
                    "BUSINESS_IMPRESSIONS_MOBILE_MAPS": 20,
                    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": 40,
                    "WEBSITE_CLICKS": 7,
                    "CALL_CLICKS": 3,
                }
            ),
            dias_analizados=28,
        )
        assert resumen.impresiones_maps == 30
        assert resumen.impresiones_search == 40
        assert resumen.impresiones_totales == 70
        assert resumen.clics_sitio == 7
        assert resumen.llamadas == 3
        # Sin período previo la variación es 0, no una división por cero.
        assert resumen.variacion_impresiones_percent == 0.0

    def test_variacion_contra_periodo_previo(self) -> None:
        resumen = FichaLocalAnalysisService.resumir_metricas(
            metricas=self._metricas({"BUSINESS_IMPRESSIONS_MOBILE_MAPS": 75}),
            dias_analizados=28,
            metricas_periodo_previo=self._metricas(
                {"BUSINESS_IMPRESSIONS_MOBILE_MAPS": 100}
            ),
        )
        assert resumen.impresiones_periodo_previo == 100
        assert resumen.variacion_impresiones_percent == -25.0

    def test_clasifica_terminos_de_marca_y_descubrimiento(self) -> None:
        terminos = FichaLocalAnalysisService.clasificar_terminos(
            [
                {"termino": "DataMaq Garín", "impresiones": 12},
                {
                    "termino": "medicion de energia parque industrial pilar",
                    "impresiones": 40,
                },
                {"termino": "", "impresiones": 5},
            ]
        )
        assert len(terminos) == 2
        assert terminos[0].es_de_marca is True
        assert terminos[1].es_de_marca is False

    def test_detecta_caida_de_impresiones(self) -> None:
        resumen = FichaLocalAnalysisService.resumir_metricas(
            metricas=self._metricas({"BUSINESS_IMPRESSIONS_MOBILE_MAPS": 50}),
            dias_analizados=28,
            metricas_periodo_previo=self._metricas(
                {"BUSINESS_IMPRESSIONS_MOBILE_MAPS": 100}
            ),
        )
        anomalias = FichaLocalAnalysisService.detectar_anomalias(
            resumen=resumen, resenas=[]
        )
        tipos = [a.anomaly_type for a in anomalias]
        assert AnomalyType.FICHA_IMPRESIONES_EN_CAIDA in tipos

    def test_detecta_resenas_sin_responder_y_pocas_resenas(self) -> None:
        resenas = [
            ResenaFicha(
                review_id="r1",
                autor="Planta A",
                estrellas=5,
                comentario="Muy bien",
                fecha_utc="2026-08-01T00:00:00Z",
                tiene_respuesta=False,
            )
        ]
        anomalias = FichaLocalAnalysisService.detectar_anomalias(
            resumen=None, resenas=resenas
        )
        tipos = [a.anomaly_type for a in anomalias]
        assert AnomalyType.FICHA_RESENA_SIN_RESPONDER in tipos
        assert AnomalyType.FICHA_POCAS_RESENAS in tipos

    def test_detecta_rating_bajo(self) -> None:
        resenas = [
            ResenaFicha(
                review_id=f"r{i}",
                autor="Planta",
                estrellas=2,
                comentario="",
                fecha_utc="2026-08-01T00:00:00Z",
                tiene_respuesta=True,
            )
            for i in range(6)
        ]
        anomalias = FichaLocalAnalysisService.detectar_anomalias(
            resumen=None, resenas=resenas
        )
        criticas = [a for a in anomalias if a.severity == AnomalySeverity.CRITICAL]
        assert any(a.anomaly_type == AnomalyType.FICHA_RATING_BAJO for a in criticas)

    def test_detecta_inactividad_de_publicaciones(self) -> None:
        anomalias = FichaLocalAnalysisService.detectar_anomalias(
            resumen=None, resenas=[], dias_desde_ultima_publicacion=30
        )
        assert [a.anomaly_type for a in anomalias] == [
            AnomalyType.FICHA_SIN_PUBLICACIONES
        ]

    def test_ficha_sana_no_genera_anomalias(self) -> None:
        resenas = [
            ResenaFicha(
                review_id=f"r{i}",
                autor="Planta",
                estrellas=5,
                comentario="",
                fecha_utc="2026-08-01T00:00:00Z",
                tiene_respuesta=True,
            )
            for i in range(6)
        ]
        anomalias = FichaLocalAnalysisService.detectar_anomalias(
            resumen=None, resenas=resenas, dias_desde_ultima_publicacion=3
        )
        assert anomalias == []


class TestGuardrailsFichaGoogle:
    """Guardrails de escritura sobre la ficha."""

    URL_OK = "https://datamaq.com.ar/guias/x?utm_source=google&utm_campaign=gbp"

    def test_publicacion_valida_no_lanza(self) -> None:
        MarketingActionGuardrailService.validate_action(
            action_type=MarketingActionType.GBP_CREATE_POST,
            params={"summary": "Nota técnica", "cta_url": self.URL_OK},
        )

    def test_publicacion_vacia_es_rechazada(self) -> None:
        with pytest.raises(PublicacionFichaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_CREATE_POST,
                params={"summary": "   ", "cta_url": self.URL_OK},
            )

    def test_publicacion_demasiado_larga_es_rechazada(self) -> None:
        with pytest.raises(PublicacionFichaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_CREATE_POST,
                params={"summary": "x" * 1501, "cta_url": self.URL_OK},
            )

    def test_publicacion_con_http_es_rechazada(self) -> None:
        with pytest.raises(PublicacionFichaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_CREATE_POST,
                params={
                    "summary": "Nota",
                    "cta_url": "http://datamaq.com.ar/x?utm_campaign=gbp",
                },
            )

    def test_publicacion_con_cta_invalido_es_rechazada(self) -> None:
        with pytest.raises(PublicacionFichaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_CREATE_POST,
                params={
                    "summary": "Nota",
                    "cta_url": self.URL_OK,
                    "cta_type": "COMPRAR_YA",
                },
            )

    def test_schedule_time_debe_ser_rfc3339(self) -> None:
        with pytest.raises(PublicacionFichaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_CREATE_POST,
                params={
                    "summary": "Nota",
                    "cta_url": self.URL_OK,
                    "schedule_time": "15/09/2026 09:00",
                },
            )

    def test_respuesta_a_resena_valida_no_lanza(self) -> None:
        MarketingActionGuardrailService.validate_action(
            action_type=MarketingActionType.GBP_REPLY_REVIEW,
            params={"review_id": "r1", "comment": "Gracias por el comentario."},
        )

    def test_respuesta_vacia_es_rechazada(self) -> None:
        with pytest.raises(RespuestaResenaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_REPLY_REVIEW,
                params={"review_id": "r1", "comment": ""},
            )

    def test_no_pisa_respuesta_existente_sin_overwrite(self) -> None:
        with pytest.raises(RespuestaResenaInvalidaException):
            MarketingActionGuardrailService.validate_action(
                action_type=MarketingActionType.GBP_REPLY_REVIEW,
                params={
                    "review_id": "r1",
                    "comment": "Gracias",
                    "tiene_respuesta": True,
                },
            )
