from pathlib import Path

from src.application.dtos.empleo_dtos import PerfilCandidatoDetalladoDTO
from src.application.mappers.empleo_mapper import EmpleoMapper
from src.domain.empleo.ports import LinkedInProfileParserPort, PerfilExportPort


class ParsearPerfilLinkedInUseCase:
    """Caso de uso para parsear perfiles de LinkedIn en PDF y opcionalmente exportar a YAML."""

    def __init__(
        self,
        parser: LinkedInProfileParserPort,
        exporter: PerfilExportPort | None = None,
        perfiles_dir: Path | None = None,
    ) -> None:
        self._parser = parser
        self._exporter = exporter
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

        if guardar_como_yaml and self._exporter is not None:
            self._exporter.exportar_yaml(
                entidad, self._perfiles_dir / f"{nombre_yaml}.yaml"
            )

        return dto

    def execute_from_path(
        self,
        ruta_pdf: Path,
        guardar_como_yaml: bool = False,
        nombre_yaml: str = "agustin_bustos_parsed",
    ) -> PerfilCandidatoDetalladoDTO:
        entidad = self._parser.parsear_archivo(ruta_pdf)
        dto = EmpleoMapper.perfil_detallado_entidad_a_dto(entidad)

        if guardar_como_yaml and self._exporter is not None:
            self._exporter.exportar_yaml(
                entidad, self._perfiles_dir / f"{nombre_yaml}.yaml"
            )

        return dto
