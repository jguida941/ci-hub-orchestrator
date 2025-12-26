"""Init command handlers."""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from cihub.cli import (
    CommandResult,
    apply_dependency_fixes,
    apply_pom_fixes,
    build_repo_config,
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    get_git_branch,
    get_git_remote,
    hub_root,
    load_effective_config,
    parse_repo_from_remote,
    render_caller_workflow,
    resolve_language,
    write_text,
)
from cihub.config.io import load_yaml_file, save_yaml_file
from cihub.config.paths import PathConfig
from cihub.exit_codes import (
    EXIT_FAILURE,
    EXIT_INTERRUPTED,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from cihub.wizard import HAS_WIZARD, WizardCancelled


def cmd_init(args: argparse.Namespace) -> int | CommandResult:
    repo_path = Path(args.repo).resolve()
    json_mode = getattr(args, "json", False)
    apply = getattr(args, "apply", False)
    force = getattr(args, "force", False)
    dry_run = args.dry_run or not apply

    if json_mode and args.wizard:
        message = "--wizard is not supported with --json"
        return CommandResult(
            exit_code=EXIT_USAGE,
            summary=message,
            problems=[{"severity": "error", "message": message}],
        )

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

    config_path = repo_path / ".ci-hub.yml"
    workflow_path = repo_path / ".github" / "workflows" / "hub-ci.yml"
    existing_config = config_path.exists()
    existing_workflow = workflow_path.exists()
    bootstrap = not existing_config or not existing_workflow
    repo_side_execution = False
    if existing_config:
        existing = load_yaml_file(config_path)
        repo_value = existing.get("repo")
        repo_block = repo_value if isinstance(repo_value, dict) else {}
        repo_side_execution = bool(repo_block.get("repo_side_execution", False))

    if apply and not repo_side_execution and not bootstrap and not force:
        message = (
            "repo_side_execution is false; re-run with --force or enable "
            "repo.repo_side_execution in .ci-hub.yml"
        )
        if json_mode:
            return CommandResult(
                exit_code=EXIT_USAGE,
                summary=message,
                problems=[
                    {
                        "severity": "error",
                        "message": message,
                        "code": "CIHUB-INIT-001",
                        "file": str(config_path),
                    }
                ],
            )
        print(message, file=sys.stderr)
        return EXIT_USAGE

    language, _ = resolve_language(repo_path, args.language)

    owner = args.owner or ""
    name = args.name or ""
    if not owner or not name:
        remote = get_git_remote(repo_path)
        if remote:
            git_owner, git_name = parse_repo_from_remote(remote)
            owner = owner or (git_owner or "")
            name = name or (git_name or "")

    if not name:
        name = repo_path.name
    owner_warnings: list[str] = []
    if not owner:
        owner = "unknown"
        owner_warnings.append(
            "Warning: could not detect repo owner; set repo.owner manually."
        )
        if not json_mode:
            print(owner_warnings[-1], file=sys.stderr)

    branch = args.branch or get_git_branch(repo_path) or "main"

    subdir = args.subdir or ""
    detected_config = build_repo_config(language, owner, name, branch, subdir=subdir)

    if args.wizard:
        if not HAS_WIZARD:
            print("Install wizard deps: pip install cihub[wizard]", file=sys.stderr)
            return EXIT_FAILURE
        from rich.console import Console

        from cihub.wizard.core import WizardRunner

        runner = WizardRunner(Console(), PathConfig(str(hub_root())))
        try:
            config = runner.run_init_wizard(detected_config)
        except WizardCancelled:
            print("Cancelled.", file=sys.stderr)
            return EXIT_INTERRUPTED
        language = config.get("language", language)
    else:
        config = detected_config
    config_path = repo_path / ".ci-hub.yml"
    if dry_run:
        if not json_mode:
            payload = yaml.safe_dump(
                config, sort_keys=False, default_flow_style=False, allow_unicode=True
            )
            print(f"# Would write: {config_path}")
            print(payload)
    else:
        save_yaml_file(config_path, config, dry_run=False)

    workflow_content = render_caller_workflow(language)
    write_text(workflow_path, workflow_content, dry_run, emit=not json_mode)

    pom_warning_problems: list[dict[str, str]] = []
    if language == "java" and not dry_run:
        effective = load_effective_config(repo_path)
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        pom_warning_list = pom_warnings + dep_warnings
        if pom_warning_list:
            if not json_mode:
                print("POM warnings:")
                for warning in pom_warning_list:
                    print(f"  - {warning}")
            else:
                pom_warning_problems = [
                    {
                        "severity": "warning",
                        "message": warning,
                        "code": "CIHUB-POM-001",
                        "file": str(repo_path / "pom.xml"),
                    }
                    for warning in pom_warning_list
                ]
            if args.fix_pom:
                if json_mode:
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        status = apply_pom_fixes(repo_path, effective, apply=True)
                        status = max(
                            status,
                            apply_dependency_fixes(repo_path, effective, apply=True),
                        )
                    problems = [
                        {
                            "severity": "warning",
                            "message": warning,
                            "code": "CIHUB-INIT-WARN",
                            "file": str(config_path),
                        }
                        for warning in owner_warnings
                    ]
                    problems.extend(pom_warning_problems)
                    root_path = repo_path / subdir if subdir else repo_path
                    pom_path = root_path / "pom.xml"
                    files_modified = [str(pom_path)] if pom_path.exists() else []
                    summary = "POM fixes applied" if status == 0 else "POM fixes failed"
                    if status != 0:
                        problems.append(
                            {
                                "severity": "error",
                                "message": "POM fixes failed",
                                "code": "CIHUB-POM-APPLY-001",
                                "file": str(pom_path),
                            }
                        )
                    return CommandResult(
                        exit_code=status,
                        summary=summary,
                        problems=problems,
                        files_generated=[str(config_path), str(workflow_path)],
                        files_modified=files_modified,
                        data={
                            "language": language,
                            "owner": owner,
                            "name": name,
                            "branch": branch,
                            "subdir": subdir,
                            "dry_run": dry_run,
                            "bootstrap": bootstrap,
                            "pom_fix_applied": True,
                            "pom_fix_status": status,
                        },
                    )
                status = apply_pom_fixes(repo_path, effective, apply=True)
                status = max(
                    status, apply_dependency_fixes(repo_path, effective, apply=True)
                )
                return status
            if not json_mode:
                print("Run: cihub fix-pom --repo . --apply")

    if json_mode:
        summary = "Dry run complete" if dry_run else "Initialization complete"
        problems = [
            {
                "severity": "warning",
                "message": warning,
                "code": "CIHUB-INIT-WARN",
                "file": str(config_path),
            }
            for warning in owner_warnings
        ]
        problems.extend(pom_warning_problems)
        return CommandResult(
            exit_code=EXIT_SUCCESS,
            summary=summary,
            problems=problems,
            files_generated=[str(config_path), str(workflow_path)],
            data={
                "language": language,
                "owner": owner,
                "name": name,
                "branch": branch,
                "subdir": subdir,
                "dry_run": dry_run,
                "bootstrap": bootstrap,
            },
        )
    return EXIT_SUCCESS
