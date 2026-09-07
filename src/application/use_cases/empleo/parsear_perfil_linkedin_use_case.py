from pathlib import Path
from typing import Any

import yaml

from src.application.dtos.empleo_dtos import PerfilCandidatoDetalladoDTO
from src.application.mappers.empleo_mapper import EmpleoMapper
from src.domain.empleo.ports import LinkedInProfileParserPort


class ParsearPerfilLinkedInUseCase:
    """Caso de uso para parsear perfiles de LinkedIn en PDF y opcionalmente exportar a YAML."""

    def __init__(
        self,
        parser: LinkedInProfileParserPort,
        perfiles_dir: Path | None = None,
    ) -> None:
        self._parser = parser
        if perfiles_dir is None:
            self._perfiles_dir = (
                Path(__file__).resolve().parents[4] / "data" / "perfiles"
            )
        else:
            self._perfiles_dir = perfiles_dir

    def execute_from_bytes(
        self,
        contenido_pdf: bytes,
        guardar_como_yaml: bool = False,
        nombre_yaml: str = "agustin_bustos_parsed",
    ) -> PerfilCandidatoDetalladoDTO:
        entidad = self._parser.parsear_pdf(contenido_pdf)
        dto = EmpleoMapper.perfil_detallado_entidad_a_dto(entidad)

        if guardar_como_yaml:
            self._guardar_perfil_yaml(dto, nombre_yaml)

        return dto

    def execute_from_path(
        self,
        ruta_pdf: Path,
        guardar_como_yaml: bool = False,
        nombre_yaml: str = "agustin_bustos_parsed",
    ) -> PerfilCandidatoDetalladoDTO:
        entidad = self._parser.parsear_archivo(ruta_pdf)
        dto = EmpleoMapper.perfil_detallado_entidad_a_dto(entidad)

        if guardar_como_yaml:
            self._guardar_perfil_yaml(dto, nombre_yaml)

        return dto

    def _guardar_perfil_yaml(
        self, dto: PerfilCandidatoDetalladoDTO, nombre_yaml: str
    ) -> Path:
        self._perfiles_dir.mkdir(parents=True, exist_ok=True)
        clean_name = nombre_yaml.removesuffix(".yaml").removesuffix(".yml")
        target_file = self._perfiles_dir / f"{clean_name}.yaml"

        data: dict[str, Any] = dto.model_dump()
        target_file.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return target_file
