"""Lógica de negocio para el servidor MCP de Microsoft Clarity (DataMaq)."""

import json
import os
import urllib.parse
import urllib.request
from typing import Any
from urllib.error import HTTPError

from dotenv import load_dotenv

load_dotenv()

CLARITY_ID: str = (os.getenv("CLARITY_ID") or "wx5hfvmv5y").strip()
CLARITY_API_TOKEN: str = (os.getenv("CLARITY_API_TOKEN") or "").strip()


def _clarity_api_request(
    endpoint: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Ejecuta una petición autenticada a la Clarity Export API."""
    if not CLARITY_API_TOKEN:
        return {
            "status": "missing_token",
            "message": "CLARITY_API_TOKEN no está configurado en .env. Podés generarlo en clarity.microsoft.com -> Settings -> API Tokens.",
            "project_id": CLARITY_ID,
            "dashboard_url": f"https://clarity.microsoft.com/projects/view/{CLARITY_ID}/dashboard",
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
            "Authorization": f"Bearer {CLARITY_API_TOKEN}",
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
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_clarity_project_info() -> dict[str, Any]:
    """Obtiene la información del proyecto Microsoft Clarity configurado para DataMaq."""
    return {
        "project_id": CLARITY_ID,
        "site_url": "https://datamaq.com.ar",
        "has_api_token": bool(CLARITY_API_TOKEN),
        "dashboard_url": f"https://clarity.microsoft.com/projects/view/{CLARITY_ID}/dashboard",
        "recordings_url": f"https://clarity.microsoft.com/projects/view/{CLARITY_ID}/recordings",
        "heatmaps_url": f"https://clarity.microsoft.com/projects/view/{CLARITY_ID}/heatmaps",
    }


def get_live_insights() -> dict[str, Any]:
    """Consulta los usuarios activos y páginas vistas en tiempo real en DataMaq."""
    return _clarity_api_request("project-live-insights")


def get_dashboard_insights(num_of_days: int = 3) -> dict[str, Any]:
    """Obtiene las métricas agregadas de comportamiento (sesiones, clics de frustración,
    scroll depth, clics muertos) de los últimos N días (1 a 3 según soporte de Clarity Export API).
    """
    days = max(1, min(3, num_of_days))
    return _clarity_api_request("project-live-insights", {"numOfDays": days})
