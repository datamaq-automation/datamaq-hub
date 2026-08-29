"""Tests RED de integración para compresión gzip de respuestas >1 KB (R-G1..R-G2)."""

from starlette.testclient import TestClient

from src.infrastructure.fastapi.server import create_app


def test_gzip_when_requested() -> None:
    """R-G1: ruta >1 KB con Accept-Encoding: gzip retorna Content-Encoding: gzip."""
    app = create_app()

    @app.get("/test/gzip")
    def big():
        return {"payload": "x" * 2000}

    client = TestClient(app)
    response = client.get("/test/gzip", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_no_gzip_without_request() -> None:
    """R-G2: sin header gzip (identity) no comprime."""
    app = create_app()

    @app.get("/test/gzip")
    def big():
        return {"payload": "x" * 2000}

    client = TestClient(app)
    response = client.get("/test/gzip", headers={"Accept-Encoding": "identity"})
    assert response.status_code == 200
    assert "content-encoding" not in response.headers
