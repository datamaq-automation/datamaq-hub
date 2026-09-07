"""Gateway para exportar perfiles detallados a formato YAML en disco."""

from pathlib import Path
from typing import Any

import yaml

from src.domain.empleo.entities import PerfilCandidatoDetallado
from src.domain.empleo.ports import PerfilExportPort


class YamlPerfilExporterGateway(PerfilExportPort):
    """Implementa PerfilExportPort serializando entidades de perfil a archivos YAML."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            self._data_dir = Path("data/perfiles")
        else:
            self._data_dir = data_dir

    def exportar_yaml(self, perfil: PerfilCandidatoDetallado, destino: Path) -> None:
        """Serializa y guarda el perfil en el archivo destino en formato YAML."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        target = (
            destino
            if destino.is_absolute()
            else self._data_dir / f"{destino.stem}.yaml"
        )

        data: dict[str, Any] = {
            "contacto": {
                "nombre": perfil.contacto.nombre,
                "email": perfil.contacto.email,
                "telefono": perfil.contacto.telefono,
                "linkedin_url": perfil.contacto.linkedin_url,
                "ubicacion": perfil.contacto.ubicacion,
            },
            "titular": perfil.titular,
            "extracto": perfil.extracto,
            "aptitudes_principales": list(perfil.aptitudes_principales),
            "experiencias": [
                {
                    "empresa": exp.empresa,
                    "puesto": exp.puesto,
                    "periodo": exp.periodo,
                    "duracion": exp.duracion,
                    "ubicacion": exp.ubicacion,
                    "descripcion": exp.descripcion,
                    "es_actual": exp.es_actual,
                }
                for exp in perfil.experiencias
            ],
            "educacion": [
                {
                    "institucion": edu.institucion,
                    "titulo": edu.titulo,
                    "periodo": edu.periodo,
                }
                for edu in perfil.educacion
            ],
            "palabras_clave_detectadas": list(perfil.palabras_clave_detectadas),
            "anios_experiencia_estimados": perfil.anios_experiencia_estimados,
        }

        target.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
