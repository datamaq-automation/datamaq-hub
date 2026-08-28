#!/usr/bin/env bash
set -euo pipefail

# Repository in the form owner/name
REPO="datamaq-automation/datamaq-hub"
BRANCH="${1:-main}"

# Use the Python utility to get the workflow status
STATUS=$(python - <<'PY'
import sys
sys.path.append('src')
from application.github_actions_checker import get_latest_workflow_status
print(get_latest_workflow_status('$REPO', '$BRANCH'))
PY
)

if [[ "$STATUS" != "success" ]]; then
  echo "⚠️ GitHub Actions workflow did not succeed (status: $STATUS)"
  exit 1
fi

echo "✅ GitHub Actions workflow succeeded"
