"""Correlation helpers for hub orchestration."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable
from urllib import request


def download_artifact(archive_url: str, target_dir: Path, token: str) -> Path | None:
    """Download and extract a GitHub artifact ZIP."""
    req = request.Request(  # noqa: S310
        archive_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with request.urlopen(req) as resp:  # noqa: S310
            data = resp.read()
        target_dir.mkdir(parents=True, exist_ok=True)
        zip_path = target_dir / "artifact.zip"
        zip_path.write_bytes(data)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
        return target_dir
    except Exception as exc:
        print(f"Warning: failed to download artifact {archive_url}: {exc}")
        return None


def extract_correlation_id_from_artifact(artifact_url: str, token: str) -> str | None:
    """Extract hub_correlation_id from a ci-report artifact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        extracted = download_artifact(artifact_url, Path(tmpdir), token)
        if not extracted:
            return None
        report_file = next(iter(Path(extracted).rglob("report.json")), None)
        if report_file and report_file.exists():
            try:
                report_data = json.loads(report_file.read_text())
                if not isinstance(report_data, dict):
                    return None
                corr = report_data.get("hub_correlation_id")
                return corr if isinstance(corr, str) else None
            except (json.JSONDecodeError, OSError):
                return None
    return None


def find_run_by_correlation_id(
    owner: str,
    repo: str,
    workflow_id: str,
    correlation_id: str,
    token: str,
    gh_get: Callable[[str], dict[str, Any]] | None = None,
) -> str | None:
    """Find a workflow run by matching hub_correlation_id in artifacts."""
    if not correlation_id:
        return None

    if gh_get is None:

        def gh_get(url: str) -> dict[str, Any]:
            req = request.Request(  # noqa: S310
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with request.urlopen(req) as resp:  # noqa: S310
                data = json.loads(resp.read().decode())
                return data if isinstance(data, dict) else {}

    try:
        runs_url = (
            f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/"
            f"{workflow_id}/runs?per_page=20&event=workflow_dispatch"
        )
        runs_data = gh_get(runs_url)

        for run in runs_data.get("workflow_runs", []):
            run_id = run.get("id")
            if not run_id:
                continue

            try:
                artifacts_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
                artifacts = gh_get(artifacts_url)
                ci_artifact = next(
                    (a for a in artifacts.get("artifacts", []) if a.get("name", "").endswith("ci-report")),
                    None,
                )

                if ci_artifact:
                    artifact_corr = extract_correlation_id_from_artifact(ci_artifact["archive_download_url"], token)
                    if artifact_corr == correlation_id:
                        print(f"Found matching run {run_id} for {correlation_id}")
                        return str(run_id)

            except Exception as exc:
                print(f"Warning: error checking run {run_id} artifacts: {exc}")
                continue

    except Exception as exc:
        print(f"Warning: error searching runs for correlation_id {correlation_id}: {exc}")

    return None


def validate_correlation_id(expected: str, actual: str | None) -> bool:
    """Validate that actual correlation ID matches expected."""
    if not expected:
        return True
    if not actual:
        return False
    return expected == actual


def generate_correlation_id(hub_run_id: str | int, run_attempt: str | int, config_basename: str) -> str:
    """Generate a deterministic correlation ID."""
    return f"{hub_run_id}-{run_attempt}-{config_basename}"
