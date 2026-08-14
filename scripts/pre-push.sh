#!/usr/bin/env bash
set -euo pipefail

# Identificar entorno virtual si existe
if [ -d "venv/bin" ]; then
    export PATH="venv/bin:$PATH"
elif [ -d ".venv/bin" ]; then
    export PATH=".venv/bin:$PATH"
fi

echo "🏛️  [1/5] Verificación instantánea de Arquitectura y DDD (< 30ms)..."
python scripts/verify_architecture.py

echo "🛠️  [2/5] Auto-reparación rápida en local (ruff check --fix & format)..."
ruff check --fix . || true
ruff format . || true

echo "🔍 [3/5] Verificando linter (ruff check) y formato..."
ruff check .
ruff format --check .

echo "🔒 [4/5] Verificando inmutabilidad estricta de __init__.py (0 bytes)..."
pytest -q tests/test_empty_inits.py

echo "🧪 [5/5] Ejecutando suite de tests en paralelo (8 threads)..."
pytest -n auto -q tests/unit/ tests/test_architecture_boundaries.py

echo "✅ Pre-push verification exitosa!"
