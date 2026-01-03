"""Validation commands for syntax, repos, configs, and quarantine checks."""

from __future__ import annotations

import argparse
import os
import py_compile
import re
from pathlib import Path

from cihub.cli import hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.services.discovery import _THRESHOLD_KEYS, _TOOL_KEYS
from cihub.services.types import RepoEntry

from . import (
    _bool_str,
    _resolve_output_path,
    _write_outputs,
)


def cmd_syntax_check(args: argparse.Namespace) -> int:
    base = Path(args.root).resolve()
    errors = 0
    for path in args.paths:
        target = (base / path).resolve()
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = list(target.rglob("*.py"))
        else:
            continue

        for file_path in files:
            try:
                py_compile.compile(str(file_path), doraise=True)
            except py_compile.PyCompileError as exc:
                errors += 1
                print(f"::error::{file_path}: {exc.msg}")

    if errors:
        return EXIT_FAILURE
    print("\u2713 Python syntax valid")
    return EXIT_SUCCESS


def cmd_repo_check(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    present = (repo_path / ".git").exists()
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"present": _bool_str(present)}, output_path)
    if not present and args.owner and args.name:
        print(f"::warning::Repo checkout failed for {args.owner}/{args.name}")
    return EXIT_SUCCESS


def cmd_source_check(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    language = args.language.lower()
    patterns: tuple[str, ...]
    if language == "java":
        patterns = ("*.java", "*.kt")
    elif language == "python":
        patterns = ("*.py",)
    else:
        patterns = ()

    has_source = False
    for pattern in patterns:
        if any(repo_path.rglob(pattern)):
            has_source = True
            break

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"has_source": _bool_str(has_source)}, output_path)
    print(f"Source code present: {has_source}")
    return EXIT_SUCCESS


def cmd_docker_compose_check(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    has_docker = (repo_path / "docker-compose.yml").exists() or (repo_path / "docker-compose.yaml").exists()
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"has_docker": _bool_str(has_docker)}, output_path)
    return EXIT_SUCCESS


def cmd_validate_configs(args: argparse.Namespace) -> int:
    """Validate all repo configs in config/repos/.

    Uses cihub.config.loader (no scripts dependency).
    """
    from cihub.config.loader import generate_workflow_inputs, load_config

    root = hub_root()
    configs_dir = Path(args.configs_dir) if args.configs_dir else root / "config" / "repos"

    repos: list[str]
    if args.repo:
        repos = [args.repo]
        config_path = configs_dir / f"{args.repo}.yaml"
        if not config_path.exists():
            print(f"Config not found: {config_path}", file=__import__("sys").stderr)
            return EXIT_FAILURE
    else:
        repos = [path.stem for path in sorted(configs_dir.glob("*.yaml"))]

    for repo in repos:
        print(f"Validating {repo}")
        config = load_config(repo_name=repo, hub_root=root)
        generate_workflow_inputs(config)

    print("\u2713 All configs valid")
    return EXIT_SUCCESS


def cmd_validate_profiles(args: argparse.Namespace) -> int:
    import sys

    root = hub_root()
    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else root / "templates" / "profiles"
    try:
        import yaml
    except ImportError as exc:
        print(f"Missing PyYAML: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    for path in sorted(profiles_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            print(f"{path} not a dict", file=sys.stderr)
            return EXIT_FAILURE
        print(f"\u2713 {path.name}")
    return EXIT_SUCCESS


def _expected_matrix_keys() -> set[str]:
    tools = {key: True for key in _TOOL_KEYS}
    thresholds: dict[str, int | float | None] = {key: 1 for key in _THRESHOLD_KEYS}
    entry = RepoEntry(
        config_basename="example",
        name="repo",
        owner="owner",
        language="python",
        branch="main",
        subdir="src",
        subdir_safe="src",
        run_group="full",
        dispatch_enabled=True,
        dispatch_workflow="hub-ci.yml",
        use_central_runner=True,
        tools=tools,
        thresholds=thresholds,
        java_version="21",
        python_version="3.12",
        build_tool="maven",
        retention_days=30,
        write_github_summary=True,
    )
    return set(entry.to_matrix_entry().keys())


def cmd_verify_matrix_keys(args: argparse.Namespace) -> int:
    """Verify that all matrix.<key> references in hub-run-all.yml are emitted by cihub discover."""
    import sys

    hub = hub_root()
    wf_path = hub / ".github" / "workflows" / "hub-run-all.yml"

    if not wf_path.exists():
        print(f"ERROR: {wf_path} not found", file=sys.stderr)
        return 2

    text = wf_path.read_text(encoding="utf-8")

    # Pattern for matrix.key references
    matrix_ref_re = re.compile(r"\bmatrix\.([A-Za-z_][A-Za-z0-9_]*)\b")
    referenced = set(matrix_ref_re.findall(text))
    emitted = _expected_matrix_keys()

    missing = sorted(referenced - emitted)
    unused = sorted(emitted - referenced)

    if missing:
        print("ERROR: matrix keys referenced but not emitted by builder:")
        for key in missing:
            print(f"  - {key}")
        return EXIT_FAILURE

    print("OK: all referenced matrix keys are emitted by the builder.")

    if unused:
        print("\nWARN: builder emits keys not referenced as matrix.<key> in this workflow:")
        for key in unused:
            print(f"  - {key}")

    return EXIT_SUCCESS


def cmd_quarantine_check(args: argparse.Namespace) -> int:
    """Fail if any file imports from _quarantine."""
    root = Path(getattr(args, "path", None) or hub_root())

    quarantine_patterns = [
        r"^\s*from\s+_quarantine\b",
        r"^\s*import\s+_quarantine\b",
        r"^\s*from\s+hub_release\._quarantine\b",
        r"^\s*import\s+hub_release\._quarantine\b",
        r"^\s*from\s+cihub\._quarantine\b",
        r"^\s*import\s+cihub\._quarantine\b",
        r"^\s*from\s+\.+_quarantine\b",
    ]
    exclude_dirs = {
        "_quarantine",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".ruff_cache",
        "vendor",
        "generated",
    }
    env_excludes = os.environ.get("QUARANTINE_EXCLUDE_DIRS", "")
    if env_excludes:
        exclude_dirs.update(env_excludes.split(","))

    violations: list[tuple[Path, int, str]] = []

    for path in root.rglob("*.py"):
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for pattern in quarantine_patterns:
                if re.search(pattern, line):
                    violations.append((path, line_num, line.strip()))

    if not violations:
        print("Quarantine check PASSED - no imports from _quarantine found")
        return EXIT_SUCCESS

    print("=" * 60)
    print("QUARANTINE IMPORT VIOLATION")
    print("=" * 60)
    print("\nFiles importing from _quarantine detected!")
    print("_quarantine is COLD STORAGE - it must not be imported.\n")
    print("Violations:")
    print("-" * 60)

    for path, line_num, line in violations:
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            rel_path = path
        print(f"  {rel_path}:{line_num}")
        print(f"    {line}\n")

    print("-" * 60)
    print(f"Total: {len(violations)} violation(s)")
    return EXIT_FAILURE
