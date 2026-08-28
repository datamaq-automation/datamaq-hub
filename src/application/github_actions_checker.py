"""Utility to check the status of the latest GitHub Actions workflow for the repository.

Requires the environment variable ``GITHUB_TOKEN`` with appropriate scopes.
"""

import json
import os
import urllib.request
from typing import Literal

WorkflowResult = Literal[
    "success", "failure", "in_progress", "cancelled", "timed_out", "action_required"
]


def get_latest_workflow_status(repo: str, branch: str = "main") -> WorkflowResult:
    """Return the conclusion or status of the most recent workflow run on the given branch.

    Args:
        repo: GitHub repository in the form 'owner/name'.
        branch: Branch name to filter runs.
    Returns:
        A string indicating the workflow result.
    Raises:
        RuntimeError: If the token is missing or no runs are found.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable not set")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/repos/{repo}/actions/runs?branch={branch}&per_page=1"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.load(response)
    runs = data.get("workflow_runs", [])
    if not runs:
        raise RuntimeError("No workflow runs found for branch")
    run = runs[0]
    # Prefer conclusion if the run is completed, otherwise use status
    return run.get("conclusion") or run.get("status")  # type: ignore[return-value]
