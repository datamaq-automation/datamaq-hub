#!/usr/bin/env bash
set -euo pipefail

# Repository in the form owner/name
REPO="datamaq-automation/datamaq-hub"
BRANCH="${1:-main}"

# Export variables for the Python subprocess
export REPO
export BRANCH

# Use venv python with PYTHONPATH pointing to src
PY_OUTPUT=$(PYTHONPATH=src ./venv/bin/python - <<'PY'
import os, json, urllib.request
from application.github_actions_checker import get_latest_workflow_status, format_run_report
repo = os.getenv('REPO')
branch = os.getenv('BRANCH', 'main')
status = get_latest_workflow_status(repo, branch)
if status == 'unknown':
    print('UNKNOWN')
else:
    token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github+json'}
    url = f'https://api.github.com/repos/{repo}/actions/runs?branch={branch}&per_page=1'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    run = data.get('workflow_runs', [{}])[0]
    print(format_run_report(run))
PY
)

# Check if the Python utility reported UNKNOWN (missing token)
if [[ "$PY_OUTPUT" == "UNKNOWN" ]]; then
  echo "⚠️  No GITHUB_TOKEN provided; cannot verify workflow status."
  exit 1
fi

# Print the formatted report (contains status, conclusion, etc.)
echo "$PY_OUTPUT"

# Exit with status 0 (success) if the report indicates a successful workflow
if echo "$PY_OUTPUT" | grep -q "Conclusions?: success" || echo "$PY_OUTPUT" | grep -q "Conclusión: success"; then
  exit 0
else
  exit 1
fi
