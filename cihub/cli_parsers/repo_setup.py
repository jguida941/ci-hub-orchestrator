"""Parser setup for repo initialization commands."""

from __future__ import annotations

import argparse
from typing import Callable

from cihub.cli_parsers.types import CommandHandlers


def add_repo_setup_commands(
    subparsers,
    add_json_flag: Callable[[argparse.ArgumentParser], None],
    handlers: CommandHandlers,
) -> None:
    new = subparsers.add_parser("new", help="Create hub-side repo config")
    add_json_flag(new)
    new.add_argument("name", help="Repo config name (config/repos/<name>.yaml)")
    new.add_argument("--owner", help="Repo owner (GitHub user/org)")
    new.add_argument(
        "--language",
        choices=["java", "python"],
        help="Repo language",
    )
    new.add_argument("--branch", help="Default branch (e.g., main)")
    new.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    new.add_argument("--profile", help="Apply a profile from templates/profiles")
    new.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive wizard (requires cihub[wizard])",
    )
    new.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    new.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    new.set_defaults(func=handlers.cmd_new)

    init = subparsers.add_parser("init", help="Generate .ci-hub.yml and hub-ci.yml")
    add_json_flag(init)
    init.add_argument("--repo", required=True, help="Path to repo")
    init.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    init.add_argument("--owner", help="Repo owner (GitHub user/org)")
    init.add_argument("--name", help="Repo name")
    init.add_argument("--branch", help="Default branch (e.g., main)")
    init.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    init.add_argument("--workdir", dest="subdir", help="Alias for --subdir")
    init.add_argument(
        "--fix-pom",
        action="store_true",
        help="Fix pom.xml for Java repos (adds missing plugins/dependencies)",
    )
    init.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: dry-run)",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="Override repo_side_execution guardrails",
    )
    init.add_argument(
        "--wizard",
        action="store_true",
        help="Run interactive wizard (requires cihub[wizard])",
    )
    init.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    init.set_defaults(func=handlers.cmd_init)

    update = subparsers.add_parser("update", help="Refresh hub-ci.yml and .ci-hub.yml")
    add_json_flag(update)
    update.add_argument("--repo", required=True, help="Path to repo")
    update.add_argument(
        "--language",
        choices=["java", "python"],
        help="Override detection",
    )
    update.add_argument("--owner", help="Repo owner (GitHub user/org)")
    update.add_argument("--name", help="Repo name")
    update.add_argument("--branch", help="Default branch (e.g., main)")
    update.add_argument("--subdir", help="Subdirectory for monorepos (repo.subdir)")
    update.add_argument("--workdir", dest="subdir", help="Alias for --subdir")
    update.add_argument(
        "--fix-pom",
        action="store_true",
        help="Fix pom.xml for Java repos (adds missing plugins/dependencies)",
    )
    update.add_argument(
        "--apply",
        action="store_true",
        help="Write files (default: dry-run)",
    )
    update.add_argument(
        "--force",
        action="store_true",
        help="Override repo_side_execution guardrails",
    )
    update.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output instead of writing",
    )
    update.set_defaults(func=handlers.cmd_update)

    validate = subparsers.add_parser(
        "validate",
        help="Validate .ci-hub.yml against schema",
    )
    add_json_flag(validate)
    validate.add_argument("--repo", required=True, help="Path to repo")
    validate.add_argument("--strict", action="store_true", help="Fail if pom.xml warnings are found")
    validate.set_defaults(func=handlers.cmd_validate)
