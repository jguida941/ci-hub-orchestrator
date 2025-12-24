#!/usr/bin/env python3
"""
Load repository configuration for dynamic GitHub Actions matrix.
Reads config/repositories.yaml and outputs JSON for matrix strategy.
"""

import argparse
import json
import sys
from pathlib import Path
import yaml


def load_repositories(config_file: str = "config/repositories.yaml") -> list:
    """Load repository configuration from YAML file."""
    config_path = Path(config_file)

    if not config_path.exists():
        print(f"ERROR: Configuration file not found: {config_file}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not config or 'repositories' not in config:
        print("ERROR: Invalid configuration - missing 'repositories' key", file=sys.stderr)
        sys.exit(1)

    return config['repositories']


def filter_enabled_repos(repositories: list) -> list:
    """Filter to only enabled repositories."""
    return [repo for repo in repositories if repo.get('enabled', False)]


def parse_timeout_minutes(timeout_str: str) -> int:
    """Parse timeout string (e.g. '30m', '1h') to minutes (whole numbers only)."""
    if not timeout_str:
        return 30  # default

    timeout_str = timeout_str.strip().lower()

    # Accept formats like "30", "30m", "1h"
    if not timeout_str or not timeout_str[0].isdigit():
        raise ValueError(f"Invalid timeout format '{timeout_str}'; expected e.g. '30m', '1h', or '30'")

    suffix = ''
    if timeout_str[-1] in {'m', 'h'}:
        suffix = timeout_str[-1]
        numeric_part = timeout_str[:-1]
    else:
        numeric_part = timeout_str

    if not numeric_part.isdigit():
        raise ValueError(f"Invalid timeout format '{timeout_str}'; value must be an integer number of minutes or hours")

    value = int(numeric_part)
    if value <= 0:
        raise ValueError(f"Timeout must be a positive integer, got: {value}")

    if suffix == 'h':
        value *= 60

    return value


def format_for_matrix(repositories: list, require_mutation: bool = False) -> dict:
    """Format repositories for GitHub Actions matrix strategy."""
    matrix_entries = []

    for repo in repositories:
        settings = repo.get('settings', {})
        if require_mutation and settings.get('enable_mutation') is False:
            continue
        # Parse timeout to minutes for GitHub Actions
        timeout_minutes = parse_timeout_minutes(settings.get('build_timeout', '30m'))

        entry = {
            'name': repo['name'],
            'repository': f"{repo['owner']}/{repo['name']}",
            'owner': repo['owner'],
            'path': settings.get('path', '.'),
            'package': settings.get('package', False),
            'timeout_minutes': timeout_minutes,
            'language': settings.get('language', ''),
            'build_cmd': settings.get('build_cmd', ''),
            'test_cmd': settings.get('test_cmd', ''),
            'pit_report': settings.get('pit_report', ''),
            'jdk_version': settings.get('jdk_version', '21'),
            'enable_mutation': settings.get('enable_mutation', True),
            'enable_codeql': settings.get('enable_codeql', False),
            'enable_depcheck': settings.get('enable_depcheck', False),
            'settings': settings
        }
        matrix_entries.append(entry)

    return {'include': matrix_entries}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load repository matrix")
    parser.add_argument(
        "--config",
        default="config/repositories.yaml",
        help="Path to repositories YAML (default: config/repositories.yaml)",
    )
    parser.add_argument(
        "--require-mutation",
        action="store_true",
        help="Filter to repositories with enable_mutation=true",
    )
    args = parser.parse_args()

    # Load repositories
    all_repos = load_repositories(args.config)

    # Filter to enabled only
    enabled_repos = filter_enabled_repos(all_repos)

    if not enabled_repos:
        print("WARNING: No enabled repositories found in configuration", file=sys.stderr)
        # Output empty matrix
        print(json.dumps({'include': []}))
        sys.exit(0)

    # Format for GitHub Actions matrix
    matrix = format_for_matrix(enabled_repos, require_mutation=args.require_mutation)

    # Output JSON for matrix
    print(json.dumps(matrix, indent=2))

    # Log summary to stderr
    print(f"Loaded {len(enabled_repos)} enabled repositories:", file=sys.stderr)
    for repo in enabled_repos:
        print(f"  - {repo['owner']}/{repo['name']}", file=sys.stderr)


if __name__ == '__main__':
    main()
