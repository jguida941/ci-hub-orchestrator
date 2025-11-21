#!/usr/bin/env python3
"""Enforce per-workflow concurrency budgets using the GitHub Actions API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

API_ROOT = "https://api.github.com"


def _github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("[concurrency-budget] GITHUB_TOKEN (or GH_TOKEN) is required")
    return token


def _github_repo() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("[concurrency-budget] GITHUB_REPOSITORY environment variable missing")
    return repo


def _github_run_id() -> int:
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not run_id:
        raise SystemExit("[concurrency-budget] GITHUB_RUN_ID environment variable missing")
    try:
        return int(run_id)
    except ValueError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"[concurrency-budget] invalid GITHUB_RUN_ID: {run_id}") from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SystemExit(f"[concurrency-budget] {path} invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"[concurrency-budget] {path} must be a mapping")
    return data


ALLOWED_GITHUB_HOSTS = {"api.github.com"}


def _http_get(url: str, token: str) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else None)
    if parsed.scheme.lower() != "https":
        raise SystemExit(f"[concurrency-budget] refusing to fetch non-HTTPS URL: {url}")
    if host not in ALLOWED_GITHUB_HOSTS or port not in (None, 443):
        raise SystemExit(f"[concurrency-budget] refusing to contact unknown host: {parsed.netloc}")

    request = urllib.request.Request(  # noqa: S310 - HTTPS + host validated above
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ci-intel-concurrency-budget/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - HTTPS and host validated above
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(
            f"[concurrency-budget] GitHub API request failed ({exc.code}): {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"[concurrency-budget] failed to reach GitHub API: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[concurrency-budget] invalid JSON from GitHub API: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("[concurrency-budget] unexpected JSON payload from GitHub API")
    return data


def _list_in_progress_runs(repo: str, workflow: str, token: str) -> list[dict[str, Any]]:
    per_page = 100
    all_runs: list[dict[str, Any]] = []
    page = 1
    total_expected: int | None = None
    while True:
        url = (
            f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}"
            f"/runs?status=in_progress&per_page={per_page}&page={page}"
        )
        data = _http_get(url, token)
        runs = data.get("workflow_runs")
        if not isinstance(runs, list):
            raise SystemExit("[concurrency-budget] workflow_runs missing from GitHub response")
        if total_expected is None:
            total_count = data.get("total_count")
            if isinstance(total_count, int) and total_count >= 0:
                total_expected = total_count
        if not runs:
            break
        all_runs.extend(runs)
        if total_expected is not None and len(all_runs) >= total_expected:
            break
        if len(runs) < per_page:
            break
        page += 1
        if page > 1000:
            raise SystemExit("[concurrency-budget] pagination exceeded safe limit (1000 pages)")
    return all_runs


def enforce_budget(config: dict[str, Any], workflow: str, budget: int) -> None:
    repo = _github_repo()
    token = _github_token()
    current_run = _github_run_id()
    runs = _list_in_progress_runs(repo, workflow, token)
    count = 0
    for run in runs:
        run_id = run.get("id")
        if run_id == current_run:
            continue
        # GitHub can return ints or strings; normalize to int comparison.
        try:
            run_id_int = int(run_id)
        except (TypeError, ValueError):
            run_id_int = None
        if run_id_int == current_run:
            continue
        count += 1
    if count >= budget:
        raise SystemExit(
            f"[concurrency-budget] workflow '{workflow}' already has {count} runs in progress "
            f"(budget={budget}); aborting to avoid runner starvation"
        )
    print(
        f"[concurrency-budget] workflow '{workflow}' currently has {count} other in-progress runs "
        f"(budget={budget})"
    )


def get_budget(config: dict[str, Any], workflow: str) -> int | None:
    workflows = config.get("workflows")
    if not isinstance(workflows, dict):
        return None
    entry = workflows.get(workflow)
    if not isinstance(entry, dict):
        return None
    budget = entry.get("max_in_progress")
    if budget is None:
        return None
    if not isinstance(budget, int) or budget < 1:
        raise SystemExit(
            f"[concurrency-budget] invalid max_in_progress value for {workflow}: {budget}"
        )
    return budget


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ensure GitHub workflow concurrency budgets are respected"
    )
    parser.add_argument(
        "--workflow",
        required=True,
        help="Workflow filename (e.g., release.yml)",
    )
    parser.add_argument(
        "--config",
        default="config/runner-isolation.yaml",
        help="Runner isolation configuration (default: config/runner-isolation.yaml)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.is_file():
        raise SystemExit(f"[concurrency-budget] config file not found: {config_path}")
    config = _load_yaml(config_path)
    budget = get_budget(config, args.workflow)
    if budget is None:
        print(f"[concurrency-budget] no budget defined for {args.workflow}; skipping")
        return 0
    enforce_budget(config, args.workflow, budget)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
