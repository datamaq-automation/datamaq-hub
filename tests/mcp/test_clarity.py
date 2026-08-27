"""Tests unitarios para el servidor FastMCP de Microsoft Clarity (DataMaq)."""

from io import BytesIO
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

import src.infrastructure.fastmcp.clarity as clarity_mcp
from src.adapters.gateways.clarity_gateway import (
    ClarityGateway,
    _clarity_api_request,
)
from src.infrastructure.pydantic.config import Settings


def test_clarity_project_info() -> None:
    gateway = ClarityGateway(clarity_id="wx5hfvmv5y", clarity_api_token="fake")
    info = gateway.get_project_info()
    assert info["project_id"] == "wx5hfvmv5y"
    assert "https://datamaq.com.ar" in info["site_url"]
    assert "clarity.microsoft.com" in info["dashboard_url"]
    assert "recordings" in info["recordings_url"]
    assert "heatmaps" in info["heatmaps_url"]


def test_clarity_missing_token_handling() -> None:
    res = _clarity_api_request(
        clarity_id="wx5hfvmv5y", clarity_api_token="", endpoint="test-endpoint"
    )
    assert res["status"] == "missing_token"
    assert "CLARITY_API_TOKEN" in res["message"]


def test_clarity_tools_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = Settings(clarity_api_token="", clarity_id="wx5hfvmv5y")

    # Inyectar gateway sin token en el módulo del servidor MCP
    monkeypatch.setattr(
        clarity_mcp,
        "_gateway",
        ClarityGateway(
            clarity_id=mock_settings.clarity_id,
            clarity_api_token=mock_settings.clarity_api_token,
        ),
    )

    live = clarity_mcp.get_live_insights()
    assert live["status"] == "missing_token"

    dash = clarity_mcp.get_dashboard_insights(2)
    assert dash["status"] == "missing_token"


def test_clarity_api_request_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gateway = ClarityGateway(
        clarity_id="wx5hfvmv5y", clarity_api_token="fake_token"
    )
    monkeypatch.setattr(clarity_mcp, "_gateway", mock_gateway)

    fake_response = MagicMock()
    fake_response.read.return_value = b'{"metricName": "RageClickCount"}'
    fake_response.__enter__.return_value = fake_response

    def mock_urlopen_success(req: object, timeout: int = 15) -> MagicMock:
        return fake_response

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_success)

    res = clarity_mcp.get_dashboard_insights(3)
    assert res["status"] == "success"
    assert res["data"] == {"metricName": "RageClickCount"}


def test_clarity_api_request_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gateway = ClarityGateway(
        clarity_id="wx5hfvmv5y", clarity_api_token="fake_token"
    )
    monkeypatch.setattr(clarity_mcp, "_gateway", mock_gateway)

    def mock_urlopen_error(req: object, timeout: int = 15) -> object:
        raise HTTPError(
            url="http://fake",
            code=401,
            msg="Unauthorized",
            hdrs={},  # type: ignore
            fp=BytesIO(b'{"error": "Invalid token"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_error)

    res = clarity_mcp.get_live_insights()
    assert res["status"] == "error"
    assert res["code"] == 401
    assert "Invalid token" in res["message"]


def test_clarity_intent_recording_urls() -> None:
    gateway = ClarityGateway(clarity_id="wx5hfvmv5y", clarity_api_token="fake")
    urls = gateway.get_intent_recording_urls()
    assert "email_click" in urls
    assert "lead_intent%3Aemail_click" in urls["email_click"]
    assert "whatsapp_click" in urls
    assert "lead_intent%3Awhatsapp_click" in urls["whatsapp_click"]
    assert "form_submit" in urls
    assert "lead_intent%3Aform_submit" in urls["form_submit"]


def test_clarity_get_recording_url_custom() -> None:
    gateway = ClarityGateway(clarity_id="wx5hfvmv5y", clarity_api_token="fake")
    # Base sin filtro
    assert (
        gateway.get_recording_url()
        == "https://clarity.microsoft.com/projects/view/wx5hfvmv5y/recordings"
    )
    # Con alias conocido
    assert "filter=lead_intent%3Aemail_click" in gateway.get_recording_url(
        "email_click"
    )
    # Con filtro ad-hoc
    assert "filter=custom_tag%3Avalue" in gateway.get_recording_url("custom_tag:value")


def test_clarity_project_info_contains_intent_urls() -> None:
    gateway = ClarityGateway(clarity_id="wx5hfvmv5y", clarity_api_token="fake")
    info = gateway.get_project_info()
    assert "intent_recording_urls" in info
    assert "email_click" in info["intent_recording_urls"]


def test_clarity_mcp_recording_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gateway = ClarityGateway(clarity_id="wx5hfvmv5y", clarity_api_token="fake")
    monkeypatch.setattr(clarity_mcp, "_gateway", mock_gateway)

    urls = clarity_mcp.get_intent_recording_urls()
    assert isinstance(urls, dict)
    assert "email_click" in urls

    url = clarity_mcp.get_recording_url("email_click")
    assert "lead_intent%3Aemail_click" in url
