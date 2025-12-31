"""Update command handler."""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

from cihub.cli import (
    CommandResult,
    apply_dependency_fixes,
    apply_pom_fixes,
    build_repo_config,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    load_effective_config,
    render_caller_workflow,
    resolve_language,
    write_text,
)
from cihub.config.io import load_yaml_file, save_yaml_file
from cihub.config.merge import deep_merge
from cihub.exit_codes import EXIT_SUCCESS, EXIT_USAGE


def cmd_update(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    json_mode = getattr(args, "json", False)
    apply = getattr(args, "apply", False)
    force = getattr(args, "force", False)
    dry_run = args.dry_run or not apply
    pom_fix_status: int | None = None

    if force and not apply:
        message = "--force requires --apply"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[{"severity": "error", "message": message}],
            )
        print(message, file=sys.stderr)
        return EXIT_USAGE

    workflow_path = repo_path / ".github" / "workflows" / "hub-ci.yml"
    existing_config = config_path.exists()
    existing_workflow = workflow_path.exists()
    bootstrap = not existing_config or not existing_workflow
    repo_side_execution = False
    if existing_config:
        existing_cfg = load_yaml_file(config_path)
        repo_block = existing_cfg.get("repo", {}) if isinstance(existing_cfg.get("repo"), dict) else {}
        repo_side_execution = bool(repo_block.get("repo_side_execution", False))

    if apply and not repo_side_execution and not bootstrap and not force:
        message = "repo_side_execution is false; re-run with --force or enable repo.repo_side_execution in .ci-hub.yml"
        if json_mode:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[
                    {
                        "severity": "error",
                        "message": message,
                        "code": "CIHUB-UPDATE-001",
                        "file": str(config_path),
                    }
                ],
            )
        print(message, file=sys.stderr)
        return EXIT_USAGE

    existing = load_yaml_file(config_path) if config_path.exists() else {}

    language = args.language or existing.get("language")
    if not language:
        language, _ = resolve_language(repo_path, None)

    owner = args.owner or existing.get("repo", {}).get("owner", "")
    name = args.name or existing.get("repo", {}).get("name", "")
    repo_existing = existing.get("repo", {}) if isinstance(existing.get("repo"), dict) else {}
    branch = args.branch or repo_existing.get("default_branch", "main")
    subdir = args.subdir or repo_existing.get("subdir")

    if not name:
        name = repo_path.name
    owner_warnings: list[str] = []
    if not owner:
        owner = "unknown"
        owner_warnings.append("Warning: could not detect repo owner; set repo.owner manually.")
        if not json_mode:
            print(owner_warnings[-1], file=sys.stderr)

    base = build_repo_config(language, owner, name, branch, subdir=subdir)
    merged = deep_merge(base, existing)
    if dry_run:
        if not json_mode:
            payload = yaml.safe_dump(merged, sort_keys=False, default_flow_style=False, allow_unicode=True)
            print(f"# Would write: {config_path}")
            print(payload)
    else:
        save_yaml_file(config_path, merged, dry_run=False)

    workflow_content = render_caller_workflow(language)
    write_text(workflow_path, workflow_content, dry_run, emit=not json_mode)

    pom_warning_problems: list[dict[str, str]] = []
    if language == "java" and not dry_run:
        effective = load_effective_config(repo_path)
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            if not json_mode:
                print("POM warnings:")
                for warning in warnings:
                    print(f"  - {warning}")
            else:
                pom_warning_problems = [
                    {
                        "severity": "warning",
                        "message": warning,
                        "code": "CIHUB-POM-001",
                        "file": str(repo_path / "pom.xml"),
                    }
                    for warning in warnings
                ]
            if args.fix_pom:
                if json_mode:
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        status = apply_pom_fixes(repo_path, effective, apply=True)
                        status = max(
                            status,
                            apply_dependency_fixes(repo_path, effective, apply=True),
                        )
                    pom_fix_status = status
                else:
                    apply_pom_fixes(repo_path, effective, apply=True)
                    apply_dependency_fixes(repo_path, effective, apply=True)
            else:
                if not json_mode:
                    print("Run: cihub fix-pom --repo . --apply")
    if json_mode:
        summary = "Dry run complete" if dry_run else "Update complete"
        problems = [
            {
                "severity": "warning",
                "message": warning,
                "code": "CIHUB-UPDATE-WARN",
                "file": str(config_path),
            }
            for warning in owner_warnings
        ]
        problems.extend(pom_warning_problems)
        exit_code = 0
        files_modified = [str(config_path), str(workflow_path)]
        data = {
            "language": language,
            "owner": owner,
            "name": name,
            "branch": branch,
            "subdir": subdir or "",
            "dry_run": dry_run,
            "bootstrap": bootstrap,
        }
        if pom_fix_status is not None:
            exit_code = max(exit_code, pom_fix_status)
            data["pom_fix_applied"] = True
            data["pom_fix_status"] = pom_fix_status
            if not dry_run:
                summary = (
                    "Update complete; POM fixes applied" if pom_fix_status == 0 else "Update complete; POM fixes failed"
                )
            root_path = repo_path / subdir if subdir else repo_path
            pom_path = root_path / "pom.xml"
            if pom_path.exists():
                files_modified.append(str(pom_path))
            if pom_fix_status != 0:
                problems.append(
                    {
                        "severity": "error",
                        "message": "POM fixes failed",
                        "code": "CIHUB-POM-APPLY-001",
                        "file": str(pom_path),
                    }
                )
        return CommandResult(
            exit_code=exit_code,
            summary=summary,
            problems=problems,
            files_modified=files_modified,
            data=data,
        )
    return EXIT_SUCCESS
