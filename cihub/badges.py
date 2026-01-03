"""Badge generation helpers for CI metrics."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping, Optional

ROOT = Path(__file__).resolve().parents[1]
BADGES_DIR = ROOT / "badges"


def _badge_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    return env.get("UPDATE_BADGES", "").lower() in {"1", "true", "yes"}


def _badge_dir(env: Mapping[str, str] | None = None, root: Path | None = None) -> Path:
    env = env or os.environ
    base = root or ROOT
    custom = env.get("BADGE_OUTPUT_DIR")
    if custom:
        return Path(custom)
    return base / "badges"


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


def disabled_badge(label: str) -> dict:
    """Generate badge JSON for disabled tool (light grey, deterministic)."""
    return {
        "schemaVersion": 1,
        "label": label,
        "message": "disabled",
        "color": "lightgrey",
    }


def load_zizmor(env: Mapping[str, str] | None = None, root: Path | None = None) -> Optional[int]:
    """Parse zizmor SARIF for high/warning findings."""
    env = env or os.environ
    base = root or ROOT
    report_path = env.get("ZIZMOR_SARIF")
    report = Path(report_path) if report_path else base / "zizmor.sarif"
    if not report.exists():
        return None
    try:
        sarif = json.loads(report.read_text(encoding="utf-8"))
        runs = sarif.get("runs", [])
        if not runs:
            return 0
        results = runs[0].get("results", [])
        findings = [r for r in results if r.get("level") in {"error", "warning"}]
        return len(findings)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def load_bandit(root: Path | None = None) -> Optional[int]:
    """Parse bandit.json for high severity issue count."""
    base = root or ROOT
    report = base / "bandit.json"
    if not report.exists():
        return None
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        results = data.get("results", [])
        high = sum(1 for r in results if r.get("issue_severity") == "HIGH")
        return high
    except (json.JSONDecodeError, KeyError):
        return None


def load_pip_audit(root: Path | None = None) -> Optional[int]:
    """Parse pip-audit.json for vulnerability count."""
    base = root or ROOT
    report = base / "pip-audit.json"
    if not report.exists():
        return None
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return sum(len(pkg.get("vulns", [])) for pkg in data if isinstance(pkg, dict))
        if isinstance(data, dict):
            deps = data.get("dependencies")
            if isinstance(deps, list):
                return sum(len(pkg.get("vulns", [])) for pkg in deps if isinstance(pkg, dict))
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def get_env_int(name: str, env: Mapping[str, str] | None = None) -> Optional[int]:
    """Get integer from environment variable."""
    env = env or os.environ
    val = env.get(name)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return None


def get_env_float(name: str, env: Mapping[str, str] | None = None) -> Optional[float]:
    """Get float from environment variable."""
    env = env or os.environ
    val = env.get(name)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return None


def build_badges(
    env: Mapping[str, str] | None = None,
    root: Path | None = None,
    disabled_tools: set[str] | None = None,
) -> dict[str, dict]:
    """Build badge payloads from environment and files.

    Args:
        env: Environment variables (defaults to os.environ)
        root: Project root path
        disabled_tools: Set of tool names that are disabled (will get "disabled" badges)
    """
    env = env or os.environ
    base = root or ROOT
    badges: dict[str, dict] = {}
    disabled_tools = disabled_tools or set()

    # Map tool names to badge filenames
    tool_badge_files = {
        "mutmut": "mutmut.json",
        "ruff": "ruff.json",
        "mypy": "mypy.json",
        "bandit": "bandit.json",
        "pip_audit": "pip-audit.json",
        "pip-audit": "pip-audit.json",
        "zizmor": "zizmor.json",
    }

    # Generate disabled badges first (these are final - metrics won't override)
    for tool in disabled_tools:
        badge_file = tool_badge_files.get(tool)
        if badge_file:
            badges[badge_file] = disabled_badge(tool.replace("_", "-"))

    # Only load metrics for enabled tools (skip if tool is disabled)
    if "mutmut" not in disabled_tools:
        mutation_score = get_env_float("MUTATION_SCORE", env)
        if mutation_score is not None:
            badges["mutmut.json"] = percent_badge("mutmut", mutation_score)

    if "ruff" not in disabled_tools:
        ruff_issues = get_env_int("RUFF_ISSUES", env)
        if ruff_issues is not None:
            badges["ruff.json"] = count_badge("ruff", ruff_issues)

    if "mypy" not in disabled_tools:
        mypy_errors = get_env_int("MYPY_ERRORS", env)
        if mypy_errors is not None:
            badges["mypy.json"] = count_badge("mypy", mypy_errors, "errors")

    if "bandit" not in disabled_tools:
        bandit_high = load_bandit(base)
        if bandit_high is not None:
            badges["bandit.json"] = count_badge("bandit", bandit_high, "high")

    if "pip_audit" not in disabled_tools and "pip-audit" not in disabled_tools:
        pip_vulns = load_pip_audit(base)
        if pip_vulns is not None:
            badges["pip-audit.json"] = count_badge("pip-audit", pip_vulns, "vulns")

    if "zizmor" not in disabled_tools:
        zizmor_findings = load_zizmor(env, base)
        if zizmor_findings is not None:
            badges["zizmor.json"] = count_badge("zizmor", zizmor_findings)

    # Note: Black badge removed - we use ruff format, not black.
    # The ruff badge already covers lint. Format check is a separate CI step.

    return badges


def main(
    env: Mapping[str, str] | None = None,
    root: Path | None = None,
    disabled_tools: set[str] | None = None,
) -> int:
    """Generate badge JSON files.

    Args:
        env: Environment variables (defaults to os.environ)
        root: Project root path
        disabled_tools: Set of tool names that are disabled (will get "disabled" badges)
    """
    env = env or os.environ
    base = root or ROOT

    if not _badge_enabled(env):
        print("[INFO] Badge generation disabled (set UPDATE_BADGES=true)")
        return 0

    badge_dir = _badge_dir(env, base)
    badge_dir.mkdir(parents=True, exist_ok=True)
    badges = build_badges(env, base, disabled_tools)

    if not badges:
        print("[WARN] No metrics found to generate badges")
        return 1

    for filename, payload in badges.items():
        path = badge_dir / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        print(f"[INFO] {filename}: {payload['message']}")

    print(f"[INFO] Updated {len(badges)} badges in {badge_dir}")
    return 0
