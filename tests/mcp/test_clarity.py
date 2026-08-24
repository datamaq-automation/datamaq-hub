"""Tests unitarios para el servidor FastMCP de Microsoft Clarity (DataMaq)."""

from io import BytesIO
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from src.infrastructure.fastmcp.clarity import (
    _clarity_api_request,
    get_clarity_project_info,
    get_dashboard_insights,
    get_live_insights,
)


def test_clarity_project_info() -> None:
    info = get_clarity_project_info()
    assert info["project_id"] == "wx5hfvmv5y"
    assert "https://datamaq.com.ar" in info["site_url"]
    assert "clarity.microsoft.com" in info["dashboard_url"]
    assert "recordings" in info["recordings_url"]
    assert "heatmaps" in info["heatmaps_url"]


def test_clarity_missing_token_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.fastmcp.clarity.CLARITY_API_TOKEN", "")
    res = _clarity_api_request("test-endpoint")
    assert res["status"] == "missing_token"
    assert "CLARITY_API_TOKEN" in res["message"]


def test_clarity_tools_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.fastmcp.clarity.CLARITY_API_TOKEN", "")
    live = get_live_insights()
    assert live["status"] == "missing_token"

    dash = get_dashboard_insights(2)
    assert dash["status"] == "missing_token"


def test_clarity_api_request_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.fastmcp.clarity.CLARITY_API_TOKEN", "fake_token")

    fake_response = MagicMock()
    fake_response.read.return_value = b'{"metricName": "RageClickCount"}'
    fake_response.__enter__.return_value = fake_response

    def mock_urlopen_success(req: object, timeout: int = 15) -> MagicMock:
        return fake_response

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_success)

    res = get_dashboard_insights(3)
    assert res["status"] == "success"
    assert res["data"] == {"metricName": "RageClickCount"}


def test_clarity_api_request_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.fastmcp.clarity.CLARITY_API_TOKEN", "fake_token")

    def mock_urlopen_error(req: object, timeout: int = 15) -> object:
        raise HTTPError(
            url="http://fake",
            code=401,
            msg="Unauthorized",
            hdrs={},  # type: ignore
            fp=BytesIO(b'{"error": "Invalid token"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_error)

    res = get_live_insights()
    assert res["status"] == "error"
    assert res["code"] == 401
    assert "Invalid token" in res["message"]
