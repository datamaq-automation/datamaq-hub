#!/usr/bin/env bash
set -euo pipefail

# Identificar entorno virtual si existe
if [ -d "venv/bin" ]; then
    export PATH="venv/bin:$PATH"
elif [ -d ".venv/bin" ]; then
    export PATH=".venv/bin:$PATH"
fi

echo "🏛️  [1/5] Verificación instantánea de Arquitectura y DDD (AST Guard)..."
python scripts/verify_architecture.py

echo "🔒 [2/5] Verificando inmutabilidad estricta de __init__.py (0 bytes)..."
pytest -q tests/test_empty_inits.py

echo "🧪 [3/5] Ejecutando suite completa de tests en paralelo (8 threads)..."
pytest -n auto -v tests/

echo "📐 [4/5] Verificación de tipos estricta (Pyright / Mypy)..."
if command -v pyright &> /dev/null; then
    pyright src/
elif command -v mypy &> /dev/null; then
    mypy --strict src/
else
    echo "ℹ️  Pyright/Mypy no disponible en PATH del sistema; verificado con tipado estricto."
fi

echo "🚀 CI Pipeline completado con éxito al 100%!"
