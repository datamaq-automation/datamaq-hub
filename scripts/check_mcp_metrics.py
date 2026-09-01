#!/usr/bin/env python3
"""Verificación manual de métricas de los 3 servidores MCP (DataMaq).

Consulta Google Ads, GA4 y Microsoft Clarity usando las credenciales de ``.env``
(pydantic-settings). Sin ``DATABASE_URL`` configurado, las llamadas van directas
a las APIs externas (sin caché).

Uso (desde la raíz del repo, venv activado):
    PYTHONPATH=. ./venv/bin/python scripts/check_mcp_metrics.py

Exit code: 0 si todos los servicios responden sin ``status == "error"``;
1 si alguno reporta un error real de conexión/API.
"""

import json
import os
import sys
from typing import Any, cast

from src.infrastructure.fastmcp import clarity, ga4, google_ads
from src.infrastructure.pydantic.config import get_settings


def _ads_snapshot() -> dict[str, Any]:
    status = google_ads.get_google_ads_status()
    snapshot: dict[str, Any] = dict(status)
    if status.get("status") == "ready":
        snapshot["campaign_performance"] = google_ads.get_campaign_performance(7)
        snapshot["search_terms_report"] = google_ads.get_search_terms_report(7)
        snapshot["daily_budget_pacing"] = google_ads.get_daily_budget_pacing()
    return snapshot


def _ga4_snapshot() -> dict[str, Any]:
    status = ga4.get_ga4_status()
    snapshot: dict[str, Any] = dict(status)
    if status.get("status") == "configured":
        snapshot["top_pages"] = ga4.get_ga4_top_pages(7)
        snapshot["traffic_sources"] = ga4.get_ga4_traffic_sources(7)
        snapshot["geo_traffic"] = ga4.get_ga4_geo_traffic(7)
        snapshot["conversions"] = ga4.get_ga4_conversions(7)
    return snapshot


def _clarity_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = dict(clarity.get_clarity_project_info())
    snapshot["live_insights"] = clarity.get_live_insights()
    snapshot["dashboard_insights"] = clarity.get_dashboard_insights(3)
    return snapshot


def _has_error(payload: Any, depth: int = 0) -> bool:
    """Detecta recursivamente un ``status == "error"`` dentro del payload."""
    if depth > 3:
        return False
    if isinstance(payload, dict):
        if payload.get("status") == "error":
            return True
        values = cast(dict[str, Any], payload).values()
        return any(_has_error(value, depth + 1) for value in values)
    if isinstance(payload, list):
        items = cast(list[Any], payload)
        return any(_has_error(item, depth + 1) for item in items)
    return False


def main() -> int:
    settings = get_settings()
    # google-auth ADC: el cliente de GA4 resuelve credenciales vía esta variable.
    if settings.google_application_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
            settings.google_application_credentials
        )

    report: dict[str, Any] = {
        "google_ads": _ads_snapshot(),
        "ga4": _ga4_snapshot(),
        "clarity": _clarity_snapshot(),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    errored = [name for name, snap in report.items() if _has_error(snap)]
    if errored:
        print(
            f"\n[ERROR] Servicios con error real: {errored}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
