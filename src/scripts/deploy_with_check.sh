#!/usr/bin/env bash
set -euo pipefail

# Deploy the latest code to the VPS and verify GitHub Actions workflow status.
# Usage: ./src/scripts/deploy_with_check.sh [branch]
# If no branch is provided, defaults to 'main'.

BRANCH="${1:-main}"
VPS_USER="vps"  # assuming SSH config for host 'vps'
VPS_PATH="/var/www/datamaq-hub"

# Pull and restart service on the VPS
ssh "$VPS_USER" "cd $VPS_PATH && git pull origin $BRANCH && sudo systemctl restart datamaq-hub"

# After restart, run the workflow check on the VPS (the script is part of the repo)
ssh "$VPS_USER" "cd $VPS_PATH && $VPS_PATH/src/scripts/check_github_actions.sh $BRANCH"

echo "✅ Deployment and GitHub Actions verification completed successfully"
