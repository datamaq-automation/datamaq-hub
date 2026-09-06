"""Unit tests for YamlPerfilGateway."""

from pathlib import Path

import pytest

from src.adapters.gateways.empleo.yaml_perfil_gateway import YamlPerfilGateway
from src.domain.empleo.exceptions import PerfilInvalidoError, PerfilNoEncontradoError
from src.domain.empleo.value_objects import ModalidadTrabajo


def test_yaml_perfil_gateway_carga_perfil_agustin_bustos() -> None:
    """Verifica que se pueda cargar el archivo real data/perfiles/agustin_bustos.yaml."""
    gateway = YamlPerfilGateway()
    perfil = gateway.obtener_perfil("agustin_bustos")

    assert (
        perfil.titulo_deseado
        == "Especialista en Confiabilidad Operacional y Desempeño de Activos"
    )
    assert "confiabilidad" in perfil.palabras_clave_prioritarias
    assert "13.2 kv" in perfil.palabras_clave_prioritarias
    assert "vfd" in perfil.palabras_clave_prioritarias
    assert "python" in perfil.palabras_clave_secundarias
    assert "añelo" in perfil.ubicaciones_preferidas
    assert ModalidadTrabajo.ROTACIONAL_YACIMIENTO in perfil.modalidades_admitidas


def test_yaml_perfil_gateway_usa_cache(tmp_path: Path) -> None:
    """Verifica que consultas sucesivas retornen la instancia cacheada sin releer."""
    profile_file = tmp_path / "test_user.yaml"
    profile_file.write_text(
        "titulo_deseado: Ingeniero Eléctrico\npalabras_clave_prioritarias: [potencia, mt]\n",
        encoding="utf-8",
    )

    gateway = YamlPerfilGateway(data_dir=tmp_path)
    p1 = gateway.obtener_perfil("test_user")
    p2 = gateway.obtener_perfil("test_user")

    assert p1 is p2
    assert p1.titulo_deseado == "Ingeniero Eléctrico"


def test_yaml_perfil_gateway_archivo_inexistente(tmp_path: Path) -> None:
    """Verifica que se lance PerfilNoEncontradoError si el archivo no existe."""
    gateway = YamlPerfilGateway(data_dir=tmp_path)
    with pytest.raises(PerfilNoEncontradoError):
        gateway.obtener_perfil("inexistente")


def test_yaml_perfil_gateway_sintaxis_invalida(tmp_path: Path) -> None:
    """Verifica que se lance PerfilInvalidoError si el archivo YAML está corrupto."""
    corrupt_file = tmp_path / "corrupto.yaml"
    corrupt_file.write_text("titulo_deseado: [abierto sin cerrar", encoding="utf-8")

    gateway = YamlPerfilGateway(data_dir=tmp_path)
    with pytest.raises(PerfilInvalidoError):
        gateway.obtener_perfil("corrupto")
