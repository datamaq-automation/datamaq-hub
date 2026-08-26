"""Gateway para interactuar con la API de exportación de Microsoft Clarity."""

import json
import urllib.parse
import urllib.request
from typing import Any
from urllib.error import HTTPError

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.domain.cache.ports import ApiCachePort


def _clarity_api_request(
    clarity_id: str,
    clarity_api_token: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta una petición autenticada a la Clarity Export API."""
    if not clarity_api_token:
        return {
            "status": "missing_token",
            "message": "CLARITY_API_TOKEN no está configurado en .env. Podés generarlo en clarity.microsoft.com -> Settings -> API Tokens.",
            "project_id": clarity_id,
            "dashboard_url": f"https://clarity.microsoft.com/projects/view/{clarity_id}/dashboard",
        }

    base_url = f"https://www.clarity.ms/export-data/api/v1/{endpoint}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{base_url}?{query}"
    else:
        url = base_url

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {clarity_api_token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            return {"status": "success", "data": data}
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        return {"status": "error", "code": e.code, "message": error_body}
    except (OSError, ValueError) as e:
        return {"status": "error", "message": str(e)}


class ClarityGateway:
    """Encapsula llamadas I/O a Microsoft Clarity sin acoplamiento a infraestructura."""

    def __init__(
        self,
        clarity_id: str,
        clarity_api_token: str,
        cache: ApiCachePort | None = None,
    ):
        self.clarity_id = clarity_id.strip()
        self.clarity_api_token = clarity_api_token.strip()
        self._cache: ApiCachePort = cache if cache is not None else ApiCacheGateway()

    def get_project_info(self) -> dict[str, Any]:
        """Obtiene la información del proyecto Microsoft Clarity configurado para DataMaq."""
        return {
            "project_id": self.clarity_id,
            "site_url": "https://datamaq.com.ar",
            "has_api_token": bool(self.clarity_api_token),
            "dashboard_url": f"https://clarity.microsoft.com/projects/view/{self.clarity_id}/dashboard",
            "recordings_url": f"https://clarity.microsoft.com/projects/view/{self.clarity_id}/recordings",
            "heatmaps_url": f"https://clarity.microsoft.com/projects/view/{self.clarity_id}/heatmaps",
        }

    def get_live_insights(self) -> dict[str, Any]:
        """Consulta los usuarios activos y páginas vistas en tiempo real."""
        key = "clarity:live_insights"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = _clarity_api_request(
            self.clarity_id, self.clarity_api_token, "project-live-insights"
        )
        if result.get("status") == "success":
            self._cache.set(key, result)
        return result

    def get_dashboard_insights(self, num_of_days: int = 3) -> dict[str, Any]:
        """Obtiene las métricas agregadas de comportamiento de los últimos N días."""
        days = max(1, min(3, num_of_days))
        key = f"clarity:dashboard_insights:days_{days}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = _clarity_api_request(
            self.clarity_id,
            self.clarity_api_token,
            "project-live-insights",
            {"numOfDays": days},
        )
        if result.get("status") == "success":
            self._cache.set(key, result)
        return result
