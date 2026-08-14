"""Gateway implementation for paritary parameters using JSON files."""

import json
from pathlib import Path

from src.domain.liquidacion.exceptions import ParitariaNoEncontradaException
from src.domain.liquidacion.ports import ParitariaRepositoryPort
from src.domain.liquidacion.value_objects import ParametrosParitaria


class ParitariaJsonGateway(ParitariaRepositoryPort):
    """Loads paritary configuration from versioned JSON files in data/paritarias/."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            # Default to data/paritarias relative to repo root
            self._data_dir = Path(__file__).resolve().parents[3] / "data" / "paritarias"
        else:
            self._data_dir = data_dir
        self._cache: dict[str, ParametrosParitaria] = {}

    def obtener_por_periodo(self, periodo: str) -> ParametrosParitaria:
        """Load and return paritary parameters for period YYYYMM."""
        clean_period = periodo.replace(" ", "").replace("/", "")
        if clean_period in self._cache:
            return self._cache[clean_period]

        json_path = self._data_dir / f"{clean_period}.json"

        if not json_path.exists():
            raise ParitariaNoEncontradaException(
                f"No se encontraron parámetros paritarios para el período '{periodo}' en {self._data_dir}"
            )

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            parametros = ParametrosParitaria(
                periodo=str(data["periodo"]),
                basico_por_modulo_sm=float(data["basico_por_modulo_sm"]),
                basico_por_modulo_pm=float(data["basico_por_modulo_pm"]),
                bonif_0455_sm=float(data["bonif_0455_sm"]),
                bonif_0455_pm=float(data["bonif_0455_pm"]),
                bonif_0667_sm=float(data["bonif_0667_sm"]),
                bonif_0667_pm=float(data["bonif_0667_pm"]),
                bonif_2575_sm=float(data["bonif_2575_sm"]),
                bonif_2575_pm=float(data["bonif_2575_pm"]),
                alicuota_ips=float(data["alicuota_ips"]),
                alicuota_ioma=float(data["alicuota_ioma"]),
                alicuota_suteba_sindicato=float(data["alicuota_suteba_sindicato"]),
                alicuota_suteba_os=float(data["alicuota_suteba_os"]),
                tope_bonificaciones_modulos=float(data["tope_bonificaciones_modulos"]),
            )
            self._cache[clean_period] = parametros
            return parametros
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise ParitariaNoEncontradaException(
                f"Error al leer parámetros paritarios de {json_path}: {e}"
            ) from e
