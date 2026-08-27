"""Pytest test configuration and shared fixtures."""

from collections.abc import Generator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.adapters.controllers.dependencies import (
    get_designacion_docente_repository_gateway,
)
from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.main import app

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_PDF_PATH = DATA_DIR / "36528392-2026-08-13-17_12_03_336.pdf"


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture con base de datos en memoria aislada."""
    mem_gateway = SQLDesignacionDocenteGateway("sqlite:///:memory:")
    app.dependency_overrides[get_designacion_docente_repository_gateway] = lambda: (
        mem_gateway
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_path() -> Path:
    """Path to the real sample DGCyE PDF receipt."""
    return SAMPLE_PDF_PATH


@pytest.fixture
def sample_pdf_bytes(sample_pdf_path: Path) -> bytes:
    """Bytes of the real sample DGCyE PDF receipt."""
    if not sample_pdf_path.exists():
        pytest.skip("Sample PDF file not found in data/ directory")
    return sample_pdf_path.read_bytes()
