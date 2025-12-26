"""Validate command handler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cihub.cli import (
    collect_java_dependency_warnings,
    collect_java_pom_warnings,
    hub_root,
    load_effective_config,
)
from cihub.config.io import load_yaml_file
from cihub.config.paths import PathConfig
from cihub.config.schema import validate_config as validate_config_schema


def cmd_validate(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    config_path = repo_path / ".ci-hub.yml"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2
    config = load_yaml_file(config_path)
    paths = PathConfig(str(hub_root()))
    errors = validate_config_schema(config, paths)
    if errors:
        print("Validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Config OK")
    effective = load_effective_config(repo_path)
    if effective.get("language") == "java":
        pom_warnings, _ = collect_java_pom_warnings(repo_path, effective)
        dep_warnings, _ = collect_java_dependency_warnings(repo_path, effective)
        warnings = pom_warnings + dep_warnings
        if warnings:
            print("POM warnings:")
            for warning in warnings:
                print(f"  - {warning}")
            if args.strict:
                return 1
        else:
            print("POM OK")
    return 0
