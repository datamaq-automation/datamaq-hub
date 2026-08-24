"""Tests unitarios para el servidor FastMCP de Google Analytics 4 (DataMaq)."""

from typing import Any

import pytest

import src.infrastructure.fastmcp.ga4 as ga4_mcp
from src.adapters.gateways.ga4_gateway import (
    GA4Gateway,
    _run_ga4_report,
)


def test_ga4_status_structure() -> None:
    status = ga4_mcp.get_ga4_status()
    assert "status" in status
    assert "property_id" in status
    assert "credentials_path" in status
    assert status["site_url"] == "https://datamaq.com.ar"


def test_ga4_missing_credentials_graceful_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_gateway = GA4Gateway(ga4_property_id="", google_application_credentials="")
    monkeypatch.setattr(ga4_mcp, "_gateway", mock_gateway)

    status = ga4_mcp.get_ga4_status()
    assert status["status"] == "missing_credentials"

    report = _run_ga4_report("", "", ["pagePath"], ["screenPageViews"])
    assert report["status"] == "missing_credentials"
    assert "setup_guide" in report

    top = ga4_mcp.get_ga4_top_pages()
    assert top["status"] == "missing_credentials"

    sources = ga4_mcp.get_ga4_traffic_sources()
    assert sources["status"] == "missing_credentials"

    geo = ga4_mcp.get_ga4_geo_traffic()
    assert geo["status"] == "missing_credentials"

    conv = ga4_mcp.get_ga4_conversions()
    assert conv["status"] == "missing_credentials"


def test_ga4_top_pages_segmentation(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_data: dict[str, Any] = {
        "status": "success",
        "rows": [
            {"pagePath": "/", "pageTitle": "Home", "screenPageViews": "10"},
            {
                "pagePath": "/cursos/python",
                "pageTitle": "Curso Python",
                "screenPageViews": "8",
            },
            {"pagePath": "/contact", "pageTitle": "Contacto", "screenPageViews": "4"},
            {
                "pagePath": "/cursos/fastapi",
                "pageTitle": "Curso FastAPI",
                "screenPageViews": "3",
            },
        ],
    }

    def _mock_report(
        prop_id: str,
        creds: str,
        dimensions: list[str],
        metrics: list[str],
        days: int = 7,
        limit: int = 10,
    ) -> dict[str, Any]:
        return dict(mock_data)

    mock_gateway = GA4Gateway(
        ga4_property_id="123456789", google_application_credentials="fake_path"
    )
    monkeypatch.setattr(ga4_mcp, "_gateway", mock_gateway)
    monkeypatch.setattr(
        "src.adapters.gateways.ga4_gateway._run_ga4_report", _mock_report
    )

    all_res = ga4_mcp.get_ga4_top_pages(segment="all")
    assert all_res["total_rows"] == 4

    comm_res = ga4_mcp.get_ga4_top_pages(segment="commercial")
    assert comm_res["total_rows"] == 2
    assert all(not r["pagePath"].startswith("/cursos") for r in comm_res["rows"])

    acad_res = ga4_mcp.get_ga4_top_pages(segment="academic")
    assert acad_res["total_rows"] == 2
    assert all(r["pagePath"].startswith("/cursos") for r in acad_res["rows"])
