#!/usr/bin/env bash
set -euo pipefail

# Identificar entorno virtual si existe
if [ -d "venv/bin" ]; then
    export PATH="venv/bin:$PATH"
elif [ -d ".venv/bin" ]; then
    export PATH=".venv/bin:$PATH"
fi

echo "🔍 [1/3] Ejecutando linter (ruff check)..."
ruff check .

echo "🎨 [2/3] Verificando formato (ruff format)..."
ruff format --check .

echo "🧪 [3/3] Ejecutando tests unitarios en paralelo (8 threads) y __init__.py..."
pytest -n auto -q tests/unit/ tests/test_empty_inits.py

echo "✅ Pre-push verification exitosa!"

