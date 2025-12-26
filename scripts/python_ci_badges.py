#!/usr/bin/env python3
"""
Generate badge JSON files for Python CI metrics (shields.io endpoint format).

Parses outputs from: ruff, bandit, pip-audit, mypy, mutmut, zizmor
Writes badge JSON to badges/ directory for shields.io endpoint badges.

Usage:
    python scripts/python_ci_badges.py

Environment variables:
    UPDATE_BADGES=true      Enable badge generation
    BADGE_OUTPUT_DIR=path   Custom output directory (default: badges/)
    MUTATION_SCORE=XX       Mutation score percentage (from CI)
    RUFF_ISSUES=XX          Ruff issue count (from CI)
    MYPY_ERRORS=XX          Mypy error count (from CI)
    ZIZMOR_SARIF=path       Optional path to zizmor SARIF file
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
BADGES_DIR = ROOT / "badges"


def _badge_enabled() -> bool:
    return os.environ.get("UPDATE_BADGES", "").lower() in {"1", "true", "yes"}


def _badge_dir() -> Path:
    custom = os.environ.get("BADGE_OUTPUT_DIR")
    if custom:
        return Path(custom)
    return BADGES_DIR


def _percent_color(percent: float) -> str:
    """Color for percentage-based badges (higher is better)."""
    if percent >= 90:
        return "brightgreen"
    if percent >= 80:
        return "green"
    if percent >= 70:
        return "yellowgreen"
    if percent >= 60:
        return "yellow"
    if percent >= 50:
        return "orange"
    return "red"


def _count_color(count: int, thresholds: tuple = (0, 5, 10)) -> str:
    """Color for count-based badges (lower is better)."""
    zero, warn, error = thresholds
    if count <= zero:
        return "brightgreen"
    if count <= warn:
        return "yellow"
    if count <= error:
        return "orange"
    return "red"


def percent_badge(label: str, percent: float) -> dict:
    """Generate badge JSON for percentage metric."""
    safe = max(0.0, min(100.0, percent))
    return {
        "schemaVersion": 1,
        "label": label,
        "message": f"{safe:.0f}%",
        "color": _percent_color(safe),
    }


def count_badge(label: str, count: Optional[int], unit: str = "issues") -> dict:
    """Generate badge JSON for count metric."""
    if count is None:
        return {
            "schemaVersion": 1,
            "label": label,
            "message": "n/a",
            "color": "lightgrey",
        }
    if count == 0:
        return {
            "schemaVersion": 1,
            "label": label,
            "message": "clean",
            "color": "brightgreen",
        }
    return {
        "schemaVersion": 1,
        "label": label,
        "message": f"{count} {unit}",
        "color": _count_color(count),
    }


def status_badge(label: str, status: str, color: str) -> dict:
    """Generate badge JSON for pass/fail-style status."""
    return {
        "schemaVersion": 1,
        "label": label,
        "message": status,
        "color": color,
    }


def load_zizmor() -> Optional[int]:
    """Parse zizmor SARIF for high/warning findings."""
    report = ROOT / "zizmor.sarif"
    if not report.exists():
        return None
    try:
        sarif = json.loads(report.read_text())
        runs = sarif.get("runs", [])
        if not runs:
            return 0
        results = runs[0].get("results", [])
        findings = [r for r in results if r.get("level") in {"error", "warning"}]
        return len(findings)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def load_bandit() -> Optional[int]:
    """Parse bandit.json for high severity issue count."""
    report = ROOT / "bandit.json"
    if not report.exists():
        return None
    try:
        data = json.loads(report.read_text())
        results = data.get("results", [])
        high = sum(1 for r in results if r.get("issue_severity") == "HIGH")
        return high
    except (json.JSONDecodeError, KeyError):
        return None


def load_pip_audit() -> Optional[int]:
    """Parse pip-audit.json for vulnerability count."""
    report = ROOT / "pip-audit.json"
    if not report.exists():
        return None
    try:
        data = json.loads(report.read_text())
        if isinstance(data, list):
            return sum(
                len(pkg.get("vulns", [])) for pkg in data if isinstance(pkg, dict)
            )
        if isinstance(data, dict):
            deps = data.get("dependencies")
            if isinstance(deps, list):
                return sum(
                    len(pkg.get("vulns", [])) for pkg in deps if isinstance(pkg, dict)
                )
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def get_env_int(name: str) -> Optional[int]:
    """Get integer from environment variable."""
    val = os.environ.get(name)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return None


def get_env_float(name: str) -> Optional[float]:
    """Get float from environment variable."""
    val = os.environ.get(name)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return None


def main() -> int:
    if not _badge_enabled():
        print("[INFO] Badge generation disabled (set UPDATE_BADGES=true)")
        return 0

    badge_dir = _badge_dir()
    badge_dir.mkdir(parents=True, exist_ok=True)

    badges = {}

    # Mutation score (from env var set by CI)
    mutation_score = get_env_float("MUTATION_SCORE")
    if mutation_score is not None:
        badges["mutmut.json"] = percent_badge("mutmut", mutation_score)

    # Ruff issues (from env var set by CI)
    ruff_issues = get_env_int("RUFF_ISSUES")
    if ruff_issues is not None:
        badges["ruff.json"] = count_badge("ruff", ruff_issues)

    # Mypy errors (from env var set by CI)
    mypy_errors = get_env_int("MYPY_ERRORS")
    if mypy_errors is not None:
        badges["mypy.json"] = count_badge("mypy", mypy_errors, "errors")

    # Bandit high severity (from JSON file)
    bandit_high = load_bandit()
    if bandit_high is not None:
        badges["bandit.json"] = count_badge("bandit", bandit_high, "high")

    # pip-audit vulnerabilities (from JSON file)
    pip_vulns = load_pip_audit()
    if pip_vulns is not None:
        badges["pip-audit.json"] = count_badge("pip-audit", pip_vulns, "vulns")

    # zizmor workflow security (from SARIF)
    zizmor_findings = load_zizmor()
    if zizmor_findings is not None:
        if zizmor_findings > 0:
            badges["zizmor.json"] = status_badge("zizmor", "failed", "red")
        else:
            badges["zizmor.json"] = status_badge("zizmor", "clean", "brightgreen")

    if not badges:
        print("[WARN] No metrics found to generate badges")
        return 1

    for filename, payload in badges.items():
        path = badge_dir / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        print(f"[INFO] {filename}: {payload['message']}")

    print(f"[INFO] Updated {len(badges)} badges in {badge_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
