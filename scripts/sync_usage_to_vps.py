#!/usr/bin/env python3
"""Sincroniza el consumo acumulado de tokens de Antigravity (AGY) local hacia la VPS.

Analiza los logs de Antigravity en la máquina local de desarrollo y los envía
a la base de datos de producción mediante un túnel SSH / ejecución remota.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

_AGY_LOG_PATTERNS = (
    os.path.join(os.path.expanduser("~"), ".gemini/antigravity-cli/log/*.log"),
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


def calcular_uso_local() -> dict[str, int]:
    """Suma los tokens acumulados parseando los logs locales de Antigravity CLI."""
    agy_data = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    parsed_files: set[str] = set()
    for pattern in _AGY_LOG_PATTERNS:
        for path in glob.glob(pattern):
            if path in parsed_files:
                continue
            parsed_files.add(path)
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
    return agy_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sincroniza tokens AGY locales a la VPS."
    )
    parser.add_argument(
        "--host",
        default="vps",
        help="Alias SSH de la VPS destino (default: vps)",
    )
    args = parser.parse_args()

    print("🔍 Calculando consumo local de tokens de Antigravity...")
    uso = calcular_uso_local()
    print(
        f"   Input: {uso['input_tokens']:,} | Output: {uso['output_tokens']:,} | Cached: {uso['cached_tokens']:,}"
    )

    if uso["input_tokens"] == 0 and uso["output_tokens"] == 0:
        print("⚠️ No se detectó consumo local de tokens. Abortando sincronización.")
        return

    payload = json.dumps(uso)
    # Ejecutar curl en la VPS mediante SSH para registrar el uso local
    ssh_cmd: list[str] = [
        "ssh",
        args.host,
        f"curl -sS -X POST -H 'Content-Type: application/json' -d {payload!r} http://127.0.0.1:8013/api/v1/analytics/usage/local",
    ]

    print(f"📤 Sincronizando consumo en la VPS ({args.host})...")
    try:
        res = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        print(f"✅ Respuesta VPS: {res.stdout.strip()}")
    except subprocess.TimeoutExpired:
        print("❌ ERROR: Tiempo de espera agotado al conectar a la VPS.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR al sincronizar consumo via SSH: {e.stderr.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
