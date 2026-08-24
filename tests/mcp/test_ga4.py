"""Tests unitarios para el servidor FastMCP de Google Analytics 4 (DataMaq)."""

from typing import Any

import pytest

from src.infrastructure.fastmcp.ga4 import (
    _run_ga4_report,
    get_ga4_conversions,
    get_ga4_geo_traffic,
    get_ga4_status,
    get_ga4_top_pages,
    get_ga4_traffic_sources,
)


def test_ga4_status_structure() -> None:
    status = get_ga4_status()
    assert "status" in status
    assert "property_id" in status
    assert "credentials_path" in status
    assert status["site_url"] == "https://datamaq.com.ar"


def test_ga4_missing_credentials_graceful_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.fastmcp.ga4.GA4_PROPERTY_ID", "")
    monkeypatch.setattr("src.infrastructure.fastmcp.ga4.GOOGLE_APPLICATION_CREDENTIALS", "")

    status = get_ga4_status()
    assert status["status"] == "missing_credentials"

    report = _run_ga4_report(["pagePath"], ["screenPageViews"])
    assert report["status"] == "missing_credentials"
    assert "setup_guide" in report

    top = get_ga4_top_pages()
    assert top["status"] == "missing_credentials"

    sources = get_ga4_traffic_sources()
    assert sources["status"] == "missing_credentials"

    geo = get_ga4_geo_traffic()
    assert geo["status"] == "missing_credentials"

    conv = get_ga4_conversions()
    assert conv["status"] == "missing_credentials"


def test_ga4_top_pages_segmentation(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_data: dict[str, Any] = {
        "status": "success",
        "rows": [
            {"pagePath": "/", "pageTitle": "Home", "screenPageViews": "10"},
            {"pagePath": "/cursos/python", "pageTitle": "Curso Python", "screenPageViews": "8"},
            {"pagePath": "/contact", "pageTitle": "Contacto", "screenPageViews": "4"},
            {"pagePath": "/cursos/fastapi", "pageTitle": "Curso FastAPI", "screenPageViews": "3"},
        ],
    }

    def _mock_report(dimensions: list[str], metrics: list[str], days: int = 7, limit: int = 10) -> dict[str, Any]:
        return dict(mock_data)

    monkeypatch.setattr("src.infrastructure.fastmcp.ga4._run_ga4_report", _mock_report)

    all_res = get_ga4_top_pages(segment="all")
    assert all_res["total_rows"] == 4

    comm_res = get_ga4_top_pages(segment="commercial")
    assert comm_res["total_rows"] == 2
    assert all(not r["pagePath"].startswith("/cursos") for r in comm_res["rows"])

    acad_res = get_ga4_top_pages(segment="academic")
    assert acad_res["total_rows"] == 2
    assert all(r["pagePath"].startswith("/cursos") for r in acad_res["rows"])
