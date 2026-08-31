#!/usr/bin/env bash
# Wrapper ejecutable para la réplica local de datos desde el VPS DonWeb (SSOT).
# Invoca scripts/sync_from_vps.py pasando todos los argumentos tal cual.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

PYTHON_BIN="python3"
if [ -x "${REPO_ROOT}/venv/bin/python" ]; then
    PYTHON_BIN="${REPO_ROOT}/venv/bin/python"
fi

"${PYTHON_BIN}" "${SCRIPT_DIR}/sync_from_vps.py" "$@"

# Sincronizar consumo de tokens locales hacia la VPS
HOST_ARG="vps"
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST_ARG="$2"
            shift; shift
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo "🔄 Sincronizando telemetría de tokens locales a la VPS..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/sync_usage_to_vps.py" --host "${HOST_ARG}"
