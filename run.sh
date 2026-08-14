#!/usr/bin/env bash
set -euo pipefail

# Identificar entorno virtual si existe
if [ -d "venv/bin" ]; then
    export PATH="venv/bin:$PATH"
elif [ -d ".venv/bin" ]; then
    export PATH=".venv/bin:$PATH"
fi

export PYTHONPATH="src:$PYTHONPATH"
echo "🌟 Levantando servidor de desarrollo FastAPI..."
exec uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
