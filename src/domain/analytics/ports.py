"""Puertos e interfaces de dominio para fuentes de datos de analítica."""

from typing import Any, Protocol


class GoogleAdsDataSourcePort(Protocol):
    """Puerto para consultas a la API de Google Ads."""

    def get_status(self) -> dict[str, Any]: ...

    def get_campaign_performance(self, days: int = 7) -> dict[str, Any]: ...

    def get_search_terms_report(
        self, days: int = 7, limit: int = 20
    ) -> dict[str, Any]: ...

    def get_daily_budget_pacing(self) -> dict[str, Any]: ...


class GA4DataSourcePort(Protocol):
    """Puerto para consultas a la API de Google Analytics 4."""

    def get_status(self) -> dict[str, Any]: ...

    def get_top_pages(
        self, days: int = 7, limit: int = 10, segment: str = "all"
    ) -> dict[str, Any]: ...

    def get_traffic_sources(self, days: int = 7, limit: int = 10) -> dict[str, Any]: ...

    def get_geo_traffic(self, days: int = 7, limit: int = 15) -> dict[str, Any]: ...

    def get_conversions(self, days: int = 7) -> dict[str, Any]: ...


class ClarityDataSourcePort(Protocol):
    """Puerto para consultas a Microsoft Clarity."""

    def get_project_info(self) -> dict[str, Any]: ...

    def get_intent_recording_urls(self) -> dict[str, str]: ...

    def get_live_insights(self) -> dict[str, Any]: ...

    def get_dashboard_insights(self, num_of_days: int = 3) -> dict[str, Any]: ...


class GoogleBusinessProfileDataSourcePort(Protocol):
    """Puerto para consultas y publicaciones sobre la ficha de Google Business Profile."""

    def get_status(self) -> dict[str, Any]: ...

    def get_location_info(self) -> dict[str, Any]: ...

    def get_performance(self, days: int = 30) -> dict[str, Any]: ...

    def get_search_keywords(
        self, months: int = 1, limit: int = 25
    ) -> dict[str, Any]: ...

    def get_reviews(self, limit: int = 20) -> dict[str, Any]: ...

    def create_post(
        self,
        summary: str,
        cta_url: str,
        cta_type: str = "LEARN_MORE",
        schedule_time: str | None = None,
    ) -> dict[str, Any]: ...

    def reply_to_review(
        self, review_id: str, comment: str, overwrite: bool = False
    ) -> dict[str, Any]: ...


class APIUsagePort(Protocol):
    """Puerto para la obtención de métricas y saldos de APIs de LLMs."""

    def obtener_usage_consolidado(self) -> dict[str, Any]: ...

    def guardar_usage_local(
        self, input_tokens: int, output_tokens: int, cached_tokens: int
    ) -> None: ...
