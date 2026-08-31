"""Gateway para la obtención de consumo y balance de APIs de LLM (DeepSeek y AGY)."""

import glob
import json
import os
import re
import urllib.request
from typing import Any

from src.domain.analytics.ports import APIUsagePort
from src.domain.common.ports import LoggerPort, NullLogger

_AGY_LOG_PATTERNS = (
    os.path.join(os.path.expanduser("~"), ".gemini/antigravity-cli/log/*.log"),
    "/root/.gemini/antigravity-cli/log/*.log",
    "/home/agustin/.gemini/antigravity-cli/log/*.log",
)

_USAGE_RE = re.compile(
    r"Usage:\s*([0-9.]+[km]?)\s*in\s*/\s*([0-9.]+[km]?)\s*out"
    r"\s*·\s*cache\s*([0-9.]+[km]?)\s*cached"
)


def parse_tokens(token_str: str) -> int:
    """Convierte una cadena de tokens (ej. ``72k``, ``1.5m``, ``848``) a entero."""
    t_str = token_str.lower().strip()
    try:
        if t_str.endswith("k"):
            return int(float(t_str[:-1]) * 1000)
        if t_str.endswith("m"):
            return int(float(t_str[:-1]) * 1000000)
        return int(float(t_str))
    except ValueError:
        return 0


class APIUsageGateway(APIUsagePort):
    """Implementación del puerto de métricas y saldos de APIs de LLMs."""

    def __init__(
        self,
        deepseek_api_key: str | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._deepseek_api_key = deepseek_api_key
        self._logger = logger or NullLogger()

    def obtener_usage_consolidado(self) -> dict[str, Any]:
        """Consolida el balance de DeepSeek y el consumo acumulado de AGY."""
        return {
            "deepseek": self._obtener_balance_deepseek(),
            "agy": self._obtener_uso_agy(),
        }

    def _obtener_balance_deepseek(self) -> dict[str, Any]:
        """Consulta el endpoint oficial ``/user/balance`` de DeepSeek."""
        deepseek_data: dict[str, Any] = {
            "is_available": False,
            "balance": 0.0,
            "currency": "USD",
        }
        if not self._deepseek_api_key:
            return deepseek_data

        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/user/balance",
                headers={"Authorization": f"Bearer {self._deepseek_api_key}"},
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read().decode())
            if data.get("is_available") and data.get("balance_infos"):
                info = data["balance_infos"][0]
                deepseek_data["is_available"] = True
                deepseek_data["balance"] = float(info.get("total_balance", 0.0))
                deepseek_data["currency"] = info.get("currency", "USD")
        except (OSError, TypeError, ValueError) as e:
            self._logger.warning("No se pudo obtener el balance de DeepSeek: %s", e)

        return deepseek_data

    def _obtener_uso_agy(self) -> dict[str, int]:
        """Suma los tokens acumulados parseando los logs locales de Antigravity CLI."""
        agy_data: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }
        parsed_files: set[str] = set()
        for pattern in _AGY_LOG_PATTERNS:
            for path in glob.glob(pattern):
                if path in parsed_files:
                    continue
                parsed_files.add(path)
                self._sumar_uso_log(path, agy_data)
        return agy_data

    @staticmethod
    def _sumar_uso_log(path: str, agy_data: dict[str, int]) -> None:
        """Acumula los tokens de un archivo de log en ``agy_data``."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = _USAGE_RE.search(line)
                    if m:
                        agy_data["input_tokens"] += parse_tokens(m.group(1))
                        agy_data["output_tokens"] += parse_tokens(m.group(2))
                        agy_data["cached_tokens"] += parse_tokens(m.group(3))
        except OSError:
            pass
