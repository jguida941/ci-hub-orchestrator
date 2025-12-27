"""Config loading for cihub ci commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cihub.cli import hub_root
from cihub.config.io import load_yaml_file
from cihub.config.merge import deep_merge

FALLBACK_DEFAULTS: dict[str, Any] = {
    "java": {
        "version": "21",
        "build_tool": "maven",
        "tools": {
            "jacoco": {"enabled": True, "min_coverage": 70},
            "checkstyle": {"enabled": True, "max_errors": 0},
            "spotbugs": {"enabled": True, "max_bugs": 0},
            "owasp": {"enabled": True, "fail_on_cvss": 7, "use_nvd_api_key": True},
            "pitest": {"enabled": True, "min_mutation_score": 70},
            "jqwik": {"enabled": False},
            "pmd": {"enabled": True, "max_violations": 0},
            "semgrep": {"enabled": False, "max_findings": 0},
            "trivy": {"enabled": False},
            "codeql": {"enabled": False},
            "docker": {
                "enabled": False,
                "compose_file": "docker-compose.yml",
                "health_endpoint": "/actuator/health",
            },
        },
    },
    "python": {
        "version": "3.12",
        "tools": {
            "pytest": {"enabled": True, "min_coverage": 70},
            "ruff": {"enabled": True, "max_errors": 0},
            "black": {"enabled": True, "max_issues": 0},
            "isort": {"enabled": True, "max_issues": 0},
            "bandit": {"enabled": True},
            "pip_audit": {"enabled": True},
            "mypy": {"enabled": False},
            "mutmut": {"enabled": True, "min_mutation_score": 70},
            "hypothesis": {"enabled": True},
            "semgrep": {"enabled": False, "max_findings": 0},
            "trivy": {"enabled": False, "fail_on_cvss": 7},
            "codeql": {"enabled": False},
            "docker": {"enabled": False},
        },
    },
    "thresholds": {
        "coverage_min": 70,
        "mutation_score_min": 70,
        "max_critical_vulns": 0,
        "max_high_vulns": 0,
    },
    "reports": {"retention_days": 30},
}


def load_ci_config(repo_path: Path) -> dict[str, Any]:
    defaults_path = hub_root() / "config" / "defaults.yaml"
    defaults = load_yaml_file(defaults_path) if defaults_path.exists() else {}
    if not defaults:
        defaults = FALLBACK_DEFAULTS
    local_path = repo_path / ".ci-hub.yml"
    if not local_path.exists():
        raise FileNotFoundError(f"Missing .ci-hub.yml in {repo_path}")
    local_config = load_yaml_file(local_path)
    merged = deep_merge(defaults, local_config)
    repo_info = merged.get("repo", {})
    if isinstance(repo_info, dict) and repo_info.get("language"):
        merged["language"] = repo_info["language"]
    return merged
