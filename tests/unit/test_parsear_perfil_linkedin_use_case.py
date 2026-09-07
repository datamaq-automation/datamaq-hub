from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.adapters.gateways.empleo.yaml_perfil_exporter_gateway import (
    YamlPerfilExporterGateway,
)
from src.application.use_cases.empleo.parsear_perfil_linkedin_use_case import (
    ParsearPerfilLinkedInUseCase,
)
from src.domain.empleo.entities import (
    ContactoPerfil,
    EducacionPerfil,
    ExperienciaPerfil,
    PerfilCandidatoDetallado,
)


@pytest.fixture
def mock_perfil_detallado() -> PerfilCandidatoDetallado:
    return PerfilCandidatoDetallado(
        contacto=ContactoPerfil(
            nombre="Agustin Bustos",
            email="agustin@test.com",
            telefono="1135162637",
            linkedin_url="https://linkedin.com/in/agustin-bustos",
            ubicacion="Argentina",
        ),
        titular="Ingeniero de Automatización",
        extracto="Extracto de prueba",
        aptitudes_principales=("PLC", "SCADA"),
        experiencias=(
            ExperienciaPerfil(
                empresa="Madygraf",
                puesto="Coordinador de Proyectos",
                periodo="2020 - Actualidad",
                duracion="4 años",
                es_actual=True,
            ),
        ),
        educacion=(
            EducacionPerfil(
                institucion="UTN",
                titulo="Técnico Superior",
                periodo="2013 - 2019",
            ),
        ),
        palabras_clave_detectadas=("automatización", "mantenimiento"),
        anios_experiencia_estimados=12.0,
    )


def test_execute_from_bytes_success(
    mock_perfil_detallado: PerfilCandidatoDetallado, tmp_path: Path
) -> None:
    mock_parser = MagicMock()
    mock_parser.parsear_pdf.return_value = mock_perfil_detallado

    use_case = ParsearPerfilLinkedInUseCase(
        parser=mock_parser,
        exporter=YamlPerfilExporterGateway(data_dir=tmp_path),
        perfiles_dir=tmp_path,
    )
    dto = use_case.execute_from_bytes(
        b"%PDF-test", guardar_como_yaml=True, nombre_yaml="test_out"
    )

    assert dto.contacto.nombre == "Agustin Bustos"
    assert dto.contacto.email == "agustin@test.com"
    assert len(dto.experiencias) == 1
    assert dto.experiencias[0].empresa == "Madygraf"
    assert dto.anios_experiencia_estimados == 12.0

    # Verificar que se creó el YAML
    yaml_file = tmp_path / "test_out.yaml"
    assert yaml_file.exists()
    content = yaml_file.read_text(encoding="utf-8")
    assert "Agustin Bustos" in content


def test_execute_from_path_success(
    mock_perfil_detallado: PerfilCandidatoDetallado, tmp_path: Path
) -> None:
    mock_parser = MagicMock()
    mock_parser.parsear_archivo.return_value = mock_perfil_detallado

    use_case = ParsearPerfilLinkedInUseCase(
        parser=mock_parser,
        exporter=YamlPerfilExporterGateway(data_dir=tmp_path),
        perfiles_dir=tmp_path,
    )
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-dummy")

    dto = use_case.execute_from_path(
        pdf_file, guardar_como_yaml=True, nombre_yaml="test_out_path"
    )

    assert dto.contacto.nombre == "Agustin Bustos"
    yaml_file = tmp_path / "test_out_path.yaml"
    assert yaml_file.exists()
