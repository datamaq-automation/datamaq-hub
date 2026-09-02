"""Gateway para interactuar con la Google Ads API."""

from typing import Any

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.domain.cache.ports import ApiCachePort

try:
    from google.ads.googleads.errors import GoogleAdsException  # type: ignore
except ImportError:
    # google-ads ausente en entornos de test/CI sin dependencias de Google
    GoogleAdsException = Exception

import os

# Límite diario de gasto en ARS (se lee de la variable de entorno o se usa 1500 por defecto)
DAILY_BUDGET_LIMIT_ARS: float = float(
    os.getenv("GOOGLE_ADS_DAILY_BUDGET_LIMIT_ARS", "1500")
)


def _get_google_ads_client(
    developer_token: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> Any:
    """Inicializa y retorna un cliente de la Google Ads API."""
    if not (developer_token and client_id and client_secret and refresh_token):
        return None

    try:
        from google.ads.googleads.client import GoogleAdsClient  # type: ignore

        credentials: dict[str, Any] = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(credentials)
    except (ImportError, ValueError):
        return None


def _resolve_gaql_date_range(days: int) -> str:
    """Mapea una cantidad de días a un literal válido de fecha en Google Ads Query Language (GAQL)."""
    if days <= 1:
        return "TODAY"
    elif days <= 7:
        return "LAST_7_DAYS"
    elif days <= 14:
        return "LAST_14_DAYS"
    elif days <= 30:
        return "LAST_30_DAYS"
    return "LAST_30_DAYS"


class GoogleAdsGateway:
    """Encapsula llamadas I/O a Google Ads API sin acoplamiento a infraestructura."""

    def __init__(
        self,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        customer_id: str,
        cache: ApiCachePort | None = None,
    ):
        self.developer_token = developer_token.strip()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.refresh_token = refresh_token.strip()
        # La API exige el ID sin guiones (ej. "4057778237"); el .env puede usar "405-777-8237".
        self.customer_id = customer_id.strip().replace("-", "")
        self._cache: ApiCachePort = cache if cache is not None else ApiCacheGateway()

    def get_status(self) -> dict[str, Any]:
        """Retorna el estado de las credenciales y configuración de la Google Ads API."""
        is_ready = bool(
            self.developer_token
            and self.client_id
            and self.client_secret
            and self.refresh_token
            and self.customer_id
        )

        accessible_accounts: list[str] = []
        token_level = "unknown"
        if is_ready:
            try:
                client = _get_google_ads_client(
                    self.developer_token,
                    self.client_id,
                    self.client_secret,
                    self.refresh_token,
                )
                if client:
                    customer_service = client.get_service("CustomerService")
                    resp = customer_service.list_accessible_customers()
                    accessible_accounts = [
                        r.replace("customers/", "") for r in resp.resource_names
                    ]
                    token_level = "test_or_basic_active"
            except GoogleAdsException as e:
                if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
                    token_level = "test_access_only (requiere solicitar Acceso Básico en Google Ads API Center)"
                else:
                    token_level = f"error: {str(e)[:100]}"

        return {
            "status": "ready" if is_ready else "pending_credentials",
            "has_developer_token": bool(self.developer_token),
            "has_client_id": bool(self.client_id),
            "has_client_secret": bool(self.client_secret),
            "has_refresh_token": bool(self.refresh_token),
            "customer_id": self.customer_id or "No configurado",
            "accessible_accounts": accessible_accounts,
            "developer_token_level": token_level,
            "daily_budget_limit_ars": DAILY_BUDGET_LIMIT_ARS,
            "message": (
                "Google Ads API conectada con éxito."
                if is_ready
                else "Falta completar GOOGLE_ADS_REFRESH_TOKEN o GOOGLE_ADS_LOGIN_CUSTOMER_ID en .env."
            ),
        }

    def get_campaign_performance(self, days: int = 7) -> dict[str, Any]:
        """Obtiene el rendimiento por campaña (impresiones, clics, costo ARS, conversiones, CPC promedio)."""
        key = f"google_ads:campaign_performance:days_{days}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        status = self.get_status()
        if status["status"] != "ready":
            return {
                "status": "missing_credentials",
                "details": status,
                "instructions": "Correr 'scripts/auth_google_ads.py' para generar el Refresh Token.",
            }

        client = _get_google_ads_client(
            self.developer_token,
            self.client_id,
            self.client_secret,
            self.refresh_token,
        )
        if not client:
            return {
                "status": "error",
                "message": "No se pudo inicializar GoogleAdsClient.",
            }

        ga_service = client.get_service("GoogleAdsService")
        date_range = _resolve_gaql_date_range(days)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.average_cpc
            FROM campaign
            WHERE segments.date DURING {date_range}
            ORDER BY metrics.clicks DESC
        """

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            campaigns: list[dict[str, Any]] = []
            total_cost_ars = 0.0

            for row in response:
                cost_ars = (row.metrics.cost_micros or 0) / 1_000_000.0
                avg_cpc_ars = (row.metrics.average_cpc or 0) / 1_000_000.0
                total_cost_ars += cost_ars
                campaigns.append(
                    {
                        "id": str(row.campaign.id),
                        "name": row.campaign.name,
                        "status": str(row.campaign.status.name),
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost_ars": round(cost_ars, 2),
                        "avg_cpc_ars": round(avg_cpc_ars, 2),
                        "conversions": row.metrics.conversions,
                    }
                )

            result: dict[str, Any] = {
                "status": "success",
                "customer_id": self.customer_id,
                "period_days": days,
                "total_campaigns": len(campaigns),
                "total_cost_ars": round(total_cost_ars, 2),
                "campaigns": campaigns,
            }
            self._cache.set(key, result)
            return result
        except GoogleAdsException as e:
            if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
                return {
                    "status": "developer_token_test_access",
                    "message": "El Developer Token actual está en nivel 'Test Access'. Para leer cuentas reales de producción, solicitar 'Acceso Básico' en Google Ads -> Herramientas -> Centro de la API.",
                    "customer_id": self.customer_id,
                }
            return {"status": "error", "message": str(e)}

    def get_search_terms_report(self, days: int = 7, limit: int = 20) -> dict[str, Any]:
        """Obtiene los términos de búsqueda reales que dispararon los anuncios para identificar negativas."""
        key = f"google_ads:search_terms_report:days_{days}:limit_{limit}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        status = self.get_status()
        if status["status"] != "ready":
            return {"status": "missing_credentials", "details": status}

        client = _get_google_ads_client(
            self.developer_token,
            self.client_id,
            self.client_secret,
            self.refresh_token,
        )
        if not client:
            return {
                "status": "error",
                "message": "No se pudo inicializar GoogleAdsClient.",
            }

        ga_service = client.get_service("GoogleAdsService")
        date_range = _resolve_gaql_date_range(days)
        query = f"""
            SELECT
                search_term_view.search_term,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM search_term_view
            WHERE segments.date DURING {date_range}
            ORDER BY metrics.clicks DESC
            LIMIT {limit}
        """

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            terms: list[dict[str, Any]] = []
            for row in response:
                terms.append(
                    {
                        "search_term": row.search_term_view.search_term,
                        "campaign": row.campaign.name,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost_ars": round(
                            (row.metrics.cost_micros or 0) / 1_000_000.0, 2
                        ),
                        "conversions": row.metrics.conversions,
                    }
                )
            search_result: dict[str, Any] = {"status": "success", "terms": terms}
            self._cache.set(key, search_result)
            return search_result
        except GoogleAdsException as e:
            if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
                return {
                    "status": "developer_token_test_access",
                    "message": "El Developer Token actual está en nivel 'Test Access'. Solicitar 'Acceso Básico' en Centro de la API de Google Ads.",
                }
            return {"status": "error", "message": str(e)}

    def get_daily_budget_pacing(self) -> dict[str, Any]:
        """Audita el gasto acumulado de hoy contra el presupuesto máximo permitido de $1.500 ARS/día."""
        key = "google_ads:daily_budget_pacing"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        status = self.get_status()
        if status["status"] != "ready":
            return {
                "status": "missing_credentials",
                "daily_limit_ars": DAILY_BUDGET_LIMIT_ARS,
                "rule": "Límite máximo de gasto: $1.500 ARS/día",
            }

        client = _get_google_ads_client(
            self.developer_token,
            self.client_id,
            self.client_secret,
            self.refresh_token,
        )
        if not client:
            return {
                "status": "error",
                "message": "No se pudo inicializar GoogleAdsClient.",
            }

        ga_service = client.get_service("GoogleAdsService")
        query = """
            SELECT
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions
            FROM customer
            WHERE segments.date DURING TODAY
        """

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            today_cost_ars = 0.0
            today_clicks = 0
            for row in response:
                today_cost_ars += (row.metrics.cost_micros or 0) / 1_000_000.0
                today_clicks += row.metrics.clicks or 0

            pacing_percentage = (today_cost_ars / DAILY_BUDGET_LIMIT_ARS) * 100.0
            is_safe = today_cost_ars <= DAILY_BUDGET_LIMIT_ARS

            pacing_result: dict[str, Any] = {
                "status": "success",
                "date": "TODAY",
                "spent_ars": round(today_cost_ars, 2),
                "daily_budget_limit_ars": DAILY_BUDGET_LIMIT_ARS,
                "pacing_percentage": f"{round(pacing_percentage, 1)}%",
                "is_within_budget": is_safe,
                "clicks_today": today_clicks,
                "alert": "Presupuesto OK"
                if is_safe
                else "ALERTA: Presupuesto diario excedido",
            }
            self._cache.set(key, pacing_result)
            return pacing_result
        except GoogleAdsException as e:
            if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
                return {
                    "status": "developer_token_test_access",
                    "message": "Developer Token en Test Access. Límite configurado: $1.500 ARS/día.",
                    "daily_budget_limit_ars": DAILY_BUDGET_LIMIT_ARS,
                }
            return {"status": "error", "message": str(e)}
