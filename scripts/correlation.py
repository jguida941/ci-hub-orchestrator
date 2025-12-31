#!/usr/bin/env python3
"""
Deterministic correlation ID matching for hub orchestrator.

This module provides functions to match dispatched workflow runs
by hub_correlation_id embedded in artifacts, eliminating race conditions
from time-based matching.
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable
from urllib import request


def download_artifact(archive_url: str, target_dir: Path, token: str) -> Path | None:
    """Download and extract a GitHub artifact ZIP.

    Args:
        archive_url: GitHub artifact archive download URL
        target_dir: Directory to extract to
        token: GitHub API token

    Returns:
        Path to extraction directory if successful, None otherwise
    """
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


def extract_correlation_id_from_artifact(
    artifact_url: str,
    token: str,
) -> str | None:
    """Extract hub_correlation_id from a ci-report artifact.

    Args:
        artifact_url: GitHub artifact archive download URL
        token: GitHub API token

    Returns:
        The hub_correlation_id if found, None otherwise
    """
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
    """
    Deterministic run matching: search runs and match by hub_correlation_id.

    This eliminates race conditions from time-based matching by using the
    correlation ID embedded in the report.json artifact.

    Args:
        owner: Repository owner
        repo: Repository name
        workflow_id: Workflow file name (e.g., 'hub-python-ci.yml')
        correlation_id: Expected hub_correlation_id to match
        token: GitHub API token
        gh_get: Optional custom HTTP GET function for testing

    Returns:
        Run ID if found, None otherwise
    """
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
        # List recent workflow runs
        runs_url = (
            f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/"
            f"{workflow_id}/runs?per_page=20&event=workflow_dispatch"
        )
        runs_data = gh_get(runs_url)

        for run in runs_data.get("workflow_runs", []):
            run_id = run.get("id")
            if not run_id:
                continue

            # Check artifacts for this run
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

            except Exception as e:
                print(f"Warning: error checking run {run_id} artifacts: {e}")
                continue

    except Exception as e:
        print(f"Warning: error searching runs for correlation_id {correlation_id}: {e}")

    return None


def validate_correlation_id(
    expected: str,
    actual: str | None,
) -> bool:
    """Validate that actual correlation ID matches expected.

    Args:
        expected: Expected correlation ID from dispatch metadata
        actual: Actual correlation ID from report artifact

    Returns:
        True if IDs match or if expected is empty (no validation needed)
    """
    if not expected:
        return True  # No expected ID, skip validation
    if not actual:
        return False  # Expected ID but none found
    return expected == actual


def generate_correlation_id(
    hub_run_id: str | int,
    run_attempt: str | int,
    config_basename: str,
) -> str:
    """Generate a deterministic correlation ID.

    Format: {hub_run_id}-{run_attempt}-{config_basename}

    Args:
        hub_run_id: GitHub run ID of the hub orchestrator
        run_attempt: Run attempt number (for retries)
        config_basename: Config file basename (e.g., 'smoke-test-python')

    Returns:
        Formatted correlation ID string
    """
    return f"{hub_run_id}-{run_attempt}-{config_basename}"
