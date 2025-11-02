#!/usr/bin/env python3
"""
Load repository configuration for dynamic GitHub Actions matrix.
Reads config/repositories.yaml and outputs JSON for matrix strategy.
"""

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


def format_for_matrix(repositories: list) -> dict:
    """Format repositories for GitHub Actions matrix strategy."""
    matrix_entries = []

    for repo in repositories:
        entry = {
            'name': repo['name'],
            'repository': f"{repo['owner']}/{repo['name']}",
            'owner': repo['owner'],
            'path': repo.get('settings', {}).get('path', '.'),
            'package': repo.get('settings', {}).get('package', False),
            'settings': repo.get('settings', {})
        }
        matrix_entries.append(entry)

    return {'include': matrix_entries}


def main():
    """Main entry point."""
    # Load repositories
    all_repos = load_repositories()

    # Filter to enabled only
    enabled_repos = filter_enabled_repos(all_repos)

    if not enabled_repos:
        print("WARNING: No enabled repositories found in configuration", file=sys.stderr)
        # Output empty matrix
        print(json.dumps({'include': []}))
        sys.exit(0)

    # Format for GitHub Actions matrix
    matrix = format_for_matrix(enabled_repos)

    # Output JSON for matrix
    print(json.dumps(matrix, indent=2))

    # Log summary to stderr
    print(f"Loaded {len(enabled_repos)} enabled repositories:", file=sys.stderr)
    for repo in enabled_repos:
        print(f"  - {repo['owner']}/{repo['name']}", file=sys.stderr)


if __name__ == '__main__':
    main()
