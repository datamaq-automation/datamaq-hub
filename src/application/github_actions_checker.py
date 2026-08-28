"""Utility to check the status of the latest GitHub Actions workflow for the repository.

Requires the environment variable ``GITHUB_TOKEN`` with appropriate scopes.
"""

import json
import os
import urllib.request
from typing import Any, Literal

WorkflowResult = Literal[
    "success",
    "failure",
    "in_progress",
    "cancelled",
    "timed_out",
    "action_required",
    "unknown",
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
        # Sin token no podemos autenticar; devolvemos "unknown" para que el llamador lo maneje.
        return "unknown"
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


def format_run_report(run: dict[str, Any]) -> str:
    """Construye un reporte legible a partir del diccionario ``run``.

    Incluye conclusión, URL del run, timestamps y duración (si están disponibles).
    """
    url: Any = run.get("html_url", "N/A")
    conclusion: Any = run.get("conclusion", "N/A")
    status: Any = run.get("status", "N/A")
    started: Any = run.get("run_started_at", "N/A")
    completed: Any = run.get("updated_at", "N/A")
    duration = "N/A"
    if started != "N/A" and completed != "N/A":
        try:
            from datetime import datetime, timezone

            # Reemplazamos Z con +00:00 para asegurar compatibilidad de zona horaria
            dt_start = datetime.fromisoformat(
                str(started).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            dt_end = datetime.fromisoformat(
                str(completed).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            duration = str(dt_end - dt_start)
        except ValueError:
            pass
    return (
        f"GitHub Actions Run Report:\n"
        f"- URL: {url}\n"
        f"- Estado: {status}\n"
        f"- Conclusión: {conclusion}\n"
        f"- Iniciado: {started}\n"
        f"- Finalizado: {completed}\n"
        f"- Duración: {duration}\n"
    )
