"""Discover command handler - matrix generation for hub-run-all.yml."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from cihub.cli import CommandResult, hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS

# Safe character pattern for repo metadata (prevents shell injection)
SAFE_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def _sanitize_subdir(subdir: str) -> str:
    """Replace / with - in subdir to make it safe for artifact names."""
    return subdir.replace("/", "-")


def _load_repo_config(config_file: Path, hub: Path) -> dict[str, Any] | None:
    """Load a single repo config, returning None on validation failure."""
    # Import here to avoid circular imports
    from scripts.load_config import (
        ConfigValidationError,
        generate_workflow_inputs,
        load_config,
    )

    repo_basename = config_file.stem
    try:
        cfg = load_config(
            repo_name=repo_basename,
            hub_root=hub,
            exit_on_validation_error=False,
        )
    except ConfigValidationError as exc:
        print(f"::warning::Skipping {config_file}: validation failed ({exc})")
        return None
    except SystemExit:
        print(f"::warning::Skipping {config_file}: validation aborted")
        return None
    except Exception as exc:
        print(f"::warning::Skipping {config_file}: failed to load ({exc})")
        return None

    repo_info = cfg.get("repo", {})
    owner = repo_info.get("owner")
    name = repo_info.get("name") or repo_basename
    language = repo_info.get("language") or cfg.get("language")
    subdir = repo_info.get("subdir", "")
    branch = repo_info.get("default_branch", "main")

    if not (owner and name and language):
        print(f"::warning::Skipping {config_file}: missing repo.owner/name/language")
        return None

    # Validate all values are safe
    unsafe = [
        ("owner", owner),
        ("name", name),
        ("subdir", subdir),
        ("branch", branch),
        ("config", repo_basename),
    ]
    if any(not SAFE_RE.match(str(value)) for _, value in unsafe if value):
        print(f"::warning::Skipping {config_file}: unsafe repo metadata")
        return None

    inputs = generate_workflow_inputs(cfg)
    run_group = repo_info.get("run_group") or cfg.get("run_group") or "full"

    entry: dict[str, Any] = {
        "config_basename": repo_basename,
        "name": name,
        "owner": owner,
        "language": language,
        "branch": branch,
        "subdir": subdir,
        "subdir_safe": _sanitize_subdir(subdir) if subdir else "",
        "run_group": run_group,
    }

    # Tool flags and thresholds from inputs
    for key in (
        # Java tool flags
        "run_jacoco",
        "run_checkstyle",
        "run_spotbugs",
        "run_owasp",
        "use_nvd_api_key",
        "run_pitest",
        "run_jqwik",
        "run_pmd",
        "run_semgrep",
        "run_trivy",
        "run_codeql",
        "run_docker",
        # Python tool flags
        "run_pytest",
        "run_ruff",
        "run_bandit",
        "run_pip_audit",
        "run_mypy",
        "run_black",
        "run_isort",
        "run_mutmut",
        "run_hypothesis",
        # Environment settings
        "java_version",
        "python_version",
        "retention_days",
        "build_tool",
        # Thresholds
        "coverage_min",
        "mutation_score_min",
        "owasp_cvss_fail",
        "max_critical_vulns",
        "max_high_vulns",
        "max_semgrep_findings",
        "max_pmd_violations",
        "max_checkstyle_errors",
        "max_spotbugs_bugs",
        "max_ruff_errors",
        "max_black_issues",
        "max_isort_issues",
    ):
        if key in inputs:
            entry[key] = inputs[key]

    return entry


def cmd_discover(args: argparse.Namespace) -> int | CommandResult:
    """Generate matrix from config/repos/*.yaml for GitHub Actions."""
    hub = Path(args.hub_root).resolve() if args.hub_root else hub_root()
    repos_dir = hub / "config" / "repos"
    json_mode = getattr(args, "json", False)

    if not repos_dir.exists():
        message = f"Repos directory not found: {repos_dir}"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(f"Error: {message}")
        return EXIT_FAILURE

    # Parse filters
    run_group_filter = getattr(args, "run_group", "") or ""
    filter_groups = [g.strip() for g in run_group_filter.split(",") if g.strip()]

    repo_filter = getattr(args, "repos", "") or ""
    filter_repos = [r.strip() for r in repo_filter.split(",") if r.strip()]

    entries: list[dict[str, Any]] = []

    for config_file in sorted(repos_dir.glob("*.yaml")):
        entry = _load_repo_config(config_file, hub)
        if entry is None:
            continue

        # Apply repo filter
        if filter_repos:
            full_name = f"{entry['owner']}/{entry['name']}"
            if (
                entry["name"] not in filter_repos
                and full_name not in filter_repos
                and entry["config_basename"] not in filter_repos
            ):
                continue

        # Apply run_group filter
        if filter_groups and entry.get("run_group") not in filter_groups:
            continue

        entries.append(entry)

    matrix = {"include": entries}

    # Output to GITHUB_OUTPUT if requested
    if args.github_output:
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(f"matrix={json.dumps(matrix)}\n")
                handle.write(f"count={len(entries)}\n")
        else:
            print("Warning: --github-output specified but GITHUB_OUTPUT not set")

    # Print summary
    print(f"Found {len(entries)} repositories")
    for entry in entries:
        subdir_info = f" subdir={entry['subdir']}" if entry.get("subdir") else ""
        print(
            f"- {entry['owner']}/{entry['name']} ({entry['language']}) "
            f"run_group={entry.get('run_group', 'full')}{subdir_info}"
        )

    if not entries:
        message = "No repositories found after filtering."
        if json_mode:
            return CommandResult(
                exit_code=EXIT_FAILURE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(f"Error: {message}")
        return EXIT_FAILURE

    if json_mode:
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=f"Found {len(entries)} repositories",
            data={"matrix": matrix, "count": len(entries)},
        )

    if not args.github_output:
        # Print matrix as JSON if not writing to GITHUB_OUTPUT
        print(json.dumps(matrix, indent=2))

    return EXIT_SUCCESS
