from pathlib import Path

import pytest

from src.adapters.gateways.empleo.pdf_linkedin_parser_gateway import (
    PdfplumberLinkedInParserGateway,
)
from src.domain.empleo.exceptions import LinkedInPDFParsingError

SAMPLE_PDF_PATH = Path("/home/agustin/Descargas/Profile.pdf")


def test_parsear_pdf_vacio_lanza_error() -> None:
    gateway = PdfplumberLinkedInParserGateway()
    with pytest.raises(LinkedInPDFParsingError, match="vacío"):
        gateway.parsear_pdf(b"")


def test_parsear_archivo_inexistente_lanza_error() -> None:
    gateway = PdfplumberLinkedInParserGateway()
    with pytest.raises(LinkedInPDFParsingError, match="no existe"):
        gateway.parsear_archivo(Path("/tmp/archivo_fantasma_inexistente.pdf"))


@pytest.mark.skipif(
    not SAMPLE_PDF_PATH.exists(),
    reason="Requiere el archivo local /home/agustin/Descargas/Profile.pdf",
)
def test_parsear_perfil_agustin_bustos_real() -> None:
    gateway = PdfplumberLinkedInParserGateway()
    perfil = gateway.parsear_archivo(SAMPLE_PDF_PATH)

    assert perfil.contacto.nombre == "Agustin Bustos"
    assert perfil.contacto.email == "agustin.mtto.madygraf@gmail.com"
    assert "1135162685" in perfil.contacto.telefono
    assert "linkedin.com/in/agustin-bustos" in perfil.contacto.linkedin_url

    assert "Impulsor de Tecnología" in perfil.titular
    assert "Madygraf" in perfil.titular
    assert "mantenimiento industrial" in perfil.extracto

    assert len(perfil.aptitudes_principales) >= 3
    assert any(
        "Automatización industrial" in apt for apt in perfil.aptitudes_principales
    )

    assert len(perfil.experiencias) >= 3
    empresas = [e.empresa for e in perfil.experiencias]
    assert "Madygraf" in empresas
    assert "Centro de Formación Laboral 402 Escobar" in empresas

    assert perfil.anios_experiencia_estimados >= 10.0
    assert "mantenimiento" in perfil.palabras_clave_detectadas
    assert "automatización" in perfil.palabras_clave_detectadas
    assert "electrotecnia" in perfil.palabras_clave_detectadas

    assert len(perfil.educacion) >= 1
    assert "Universidad Tecnológica Nacional" in perfil.educacion[0].institucion
