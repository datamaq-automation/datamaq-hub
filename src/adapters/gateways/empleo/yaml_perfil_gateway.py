"""Gateway implementation for loading professional profiles from YAML files."""

from pathlib import Path
from typing import Any

import yaml

from src.domain.empleo.entities import PerfilProfesional
from src.domain.empleo.exceptions import PerfilInvalidoError, PerfilNoEncontradoError
from src.domain.empleo.ports import PerfilProfesionalRepositoryPort
from src.domain.empleo.value_objects import ModalidadTrabajo


class YamlPerfilGateway(PerfilProfesionalRepositoryPort):
    """Carga y parsea perfiles profesionales desde archivos YAML en data/perfiles/."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            # Default to data/perfiles relative to repo root
            self._data_dir = Path(__file__).resolve().parents[4] / "data" / "perfiles"
        else:
            self._data_dir = data_dir
        self._cache: dict[str, PerfilProfesional] = {}

    def obtener_perfil(self, nombre: str = "agustin_bustos") -> PerfilProfesional:
        """Carga y retorna una entidad PerfilProfesional a partir de su archivo YAML."""
        clean_name = nombre.strip().lower().removesuffix(".yaml").removesuffix(".yml")
        if clean_name in self._cache:
            return self._cache[clean_name]

        yaml_path = self._data_dir / f"{clean_name}.yaml"
        if not yaml_path.exists():
            # Probar alternativa .yml
            yaml_path = self._data_dir / f"{clean_name}.yml"

        if not yaml_path.exists():
            raise PerfilNoEncontradoError(
                f"No se encontró el archivo de perfil '{clean_name}.yaml' en {self._data_dir}"
            )

        try:
            content = yaml_path.read_text(encoding="utf-8")
            data: dict[str, Any] = yaml.safe_load(content) or {}
        except Exception as e:
            raise PerfilInvalidoError(
                f"Error de sintaxis al leer el archivo YAML de perfil {yaml_path}: {e}"
            ) from e

        titulo_deseado = str(data.get("titulo_deseado", "")).strip()

        list_prioritarias: list[object] = []
        raw_p = data.get("palabras_clave_prioritarias")
        if isinstance(raw_p, list):
            list_prioritarias.extend(raw_p)
        palabras_clave_prioritarias = tuple(
            str(k).strip().lower() for k in list_prioritarias if str(k).strip()
        )

        list_secundarias: list[object] = []
        raw_s = data.get("palabras_clave_secundarias")
        if isinstance(raw_s, list):
            list_secundarias.extend(raw_s)
        palabras_clave_secundarias = tuple(
            str(k).strip().lower() for k in list_secundarias if str(k).strip()
        )

        list_ubicaciones: list[object] = []
        raw_u = data.get("ubicaciones_preferidas")
        if isinstance(raw_u, list):
            list_ubicaciones.extend(raw_u)
        ubicaciones_preferidas = tuple(
            str(u).strip().lower() for u in list_ubicaciones if str(u).strip()
        )

        list_modalidades: list[object] = []
        raw_m = data.get("modalidades_admitidas")
        if isinstance(raw_m, list):
            list_modalidades.extend(raw_m)
        modalidades_admitidas_list: list[ModalidadTrabajo] = []
        for mod in list_modalidades:
            mod_str = str(mod).strip().upper()
            try:
                modalidades_admitidas_list.append(ModalidadTrabajo[mod_str])
            except KeyError:
                try:
                    modalidades_admitidas_list.append(ModalidadTrabajo(mod_str.lower()))
                except ValueError:
                    continue

        perfil = PerfilProfesional(
            titulo_deseado=titulo_deseado,
            palabras_clave_prioritarias=palabras_clave_prioritarias,
            palabras_clave_secundarias=palabras_clave_secundarias,
            ubicaciones_preferidas=ubicaciones_preferidas,
            modalidades_admitidas=tuple(modalidades_admitidas_list),
        )

        self._cache[clean_name] = perfil
        return perfil
