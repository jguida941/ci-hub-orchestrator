"""Dashboard generation commands (HTML/JSON)."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_dashboard_reports(
    reports_dir: Path, schema_mode: str = "warn"
) -> tuple[list[dict[str, Any]], int, list[str]]:
    """Load all report JSON files from the reports directory.

    Args:
        reports_dir: Directory containing report.json files
        schema_mode: "warn" to warn on non-2.0 schema, "strict" to skip them

    Returns:
        Tuple of (reports list, skipped count, warnings)
    """
    reports: list[dict[str, Any]] = []
    skipped = 0
    warnings: list[str] = []

    if not reports_dir.exists():
        return reports, skipped, warnings

    for report_file in reports_dir.glob("**/report.json"):
        try:
            with report_file.open(encoding="utf-8") as f:
                report = json.load(f)
                report["_source_file"] = str(report_file)

                # Validate schema version
                schema_version = report.get("schema_version")
                if schema_version != "2.0":
                    if schema_mode == "strict":
                        warnings.append(f"Skipping {report_file}: schema_version={schema_version}, expected '2.0'")
                        skipped += 1
                        continue
                    else:
                        warnings.append(f"{report_file} has schema_version={schema_version}, expected '2.0'")

                reports.append(report)
        except (json.JSONDecodeError, OSError) as e:
            warnings.append(f"Could not load {report_file}: {e}")

    return reports, skipped, warnings


def _detect_language(report: dict[str, Any]) -> str:
    """Detect language from report fields."""
    if report.get("java_version"):
        return "java"
    if report.get("python_version"):
        return "python"
    # Fallback to tools_ran inspection
    tools_ran = report.get("tools_ran", {})
    if tools_ran.get("jacoco") or tools_ran.get("checkstyle") or tools_ran.get("spotbugs"):
        return "java"
    if tools_ran.get("pytest") or tools_ran.get("ruff") or tools_ran.get("bandit"):
        return "python"
    return "unknown"


def _get_report_status(report: dict[str, Any]) -> str:
    """Get build/test status from report (handles both Java and Python)."""
    results = report.get("results", {})
    # Python uses 'test', Java uses 'build'
    status = results.get("test") or results.get("build") or "unknown"
    return status


def _generate_dashboard_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary from all reports."""
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "2.0",
        "total_repos": len(reports),
        "languages": {},
        "coverage": {"total": 0, "count": 0, "average": 0},
        "mutation": {"total": 0, "count": 0, "average": 0},
        "tests": {"total_passed": 0, "total_failed": 0},
        "repos": [],
    }

    # Aggregate tool statistics across all repos
    tool_stats: dict[str, dict[str, int]] = {}

    for report in reports:
        repo_name = report.get("repository", "unknown")
        results = report.get("results", {})
        tool_metrics = report.get("tool_metrics", {})
        tools_ran = report.get("tools_ran", {})
        tools_configured = report.get("tools_configured", {})
        tools_success = report.get("tools_success", {})

        # Track languages using helper
        lang = _detect_language(report)
        summary["languages"][lang] = summary["languages"].get(lang, 0) + 1

        # Coverage - include zeros in average (only skip if key is missing)
        coverage = results.get("coverage")
        if coverage is not None:
            summary["coverage"]["total"] += coverage
            summary["coverage"]["count"] += 1
        else:
            coverage = 0  # Default for repo_detail below

        # Mutation score - include zeros in average (only skip if key is missing)
        mutation = results.get("mutation_score")
        if mutation is not None:
            summary["mutation"]["total"] += mutation
            summary["mutation"]["count"] += 1
        else:
            mutation = 0  # Default for repo_detail below

        # Test counts
        tests_passed = results.get("tests_passed", 0)
        tests_failed = results.get("tests_failed", 0)
        summary["tests"]["total_passed"] += tests_passed
        summary["tests"]["total_failed"] += tests_failed

        # Repo details with schema 2.0 fields
        repo_detail: dict[str, Any] = {
            "name": repo_name,
            "branch": report.get("branch", "unknown"),
            "language": lang,
            "status": _get_report_status(report),
            "coverage": coverage,
            "mutation_score": mutation,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "timestamp": report.get("timestamp", "unknown"),
            "schema_version": report.get("schema_version", "unknown"),
        }

        # Include tool_metrics if present
        if tool_metrics:
            repo_detail["tool_metrics"] = tool_metrics

        # Include tools_ran if present
        if tools_ran:
            repo_detail["tools_ran"] = tools_ran

        # Include tools_configured and tools_success if present
        if tools_configured:
            repo_detail["tools_configured"] = tools_configured
        if tools_success:
            repo_detail["tools_success"] = tools_success

        summary["repos"].append(repo_detail)

        # Aggregate tool stats across all repos
        for tool, configured in tools_configured.items():
            if tool not in tool_stats:
                tool_stats[tool] = {"configured": 0, "ran": 0, "passed": 0, "failed": 0}
            if configured:
                tool_stats[tool]["configured"] += 1
            if tools_ran.get(tool):
                tool_stats[tool]["ran"] += 1
            if tools_success.get(tool):
                tool_stats[tool]["passed"] += 1
            elif tools_ran.get(tool):
                tool_stats[tool]["failed"] += 1

    # Calculate averages
    if summary["coverage"]["count"] > 0:
        summary["coverage"]["average"] = round(summary["coverage"]["total"] / summary["coverage"]["count"], 1)

    if summary["mutation"]["count"] > 0:
        summary["mutation"]["average"] = round(summary["mutation"]["total"] / summary["mutation"]["count"], 1)

    # Add tool stats to summary
    if tool_stats:
        summary["tool_stats"] = tool_stats

    return summary


def _generate_html_dashboard(summary: dict[str, Any]) -> str:
    """Generate an HTML dashboard from the summary."""
    total_tests = summary["tests"]["total_passed"] + summary["tests"]["total_failed"]
    repos_html = ""
    for repo in summary["repos"]:
        status_class = "success" if repo["status"] == "success" else "failure"
        tests_passed = repo.get("tests_passed", 0)
        tests_failed = repo.get("tests_failed", 0)
        tests_class = "success" if tests_failed == 0 else "failure"
        # Escape user-controlled values to prevent XSS
        name = html.escape(str(repo["name"]))
        language = html.escape(str(repo.get("language", "unknown")))
        branch = html.escape(str(repo["branch"]))
        status = html.escape(str(repo["status"]))
        timestamp = html.escape(str(repo["timestamp"]))
        repos_html += f"""
        <tr>
            <td>{name}</td>
            <td>{language}</td>
            <td>{branch}</td>
            <td class="{status_class}">{status}</td>
            <td>{repo["coverage"]}%</td>
            <td class="{tests_class}">{tests_passed}/{tests_passed + tests_failed}</td>
            <td>{repo["mutation_score"]}%</td>
            <td>{timestamp}</td>
        </tr>
        """

    html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI/CD Hub Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 2rem;
        }}
        h1 {{ color: #58a6ff; margin-bottom: 1rem; }}
        h2 {{ color: #8b949e; margin: 1.5rem 0 1rem; font-size: 1.2rem; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 1.5rem;
        }}
        .card-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #58a6ff;
        }}
        .card-label {{
            color: #8b949e;
            font-size: 0.9rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }}
        th {{ background: #21262d; color: #8b949e; font-weight: 600; }}
        .success {{ color: #3fb950; }}
        .failure {{ color: #f85149; }}
        .timestamp {{ color: #8b949e; font-size: 0.8rem; margin-top: 2rem; }}
    </style>
</head>
<body>
    <h1>CI/CD Hub Dashboard</h1>

    <div class="summary">
        <div class="card">
            <div class="card-value">{summary["total_repos"]}</div>
            <div class="card-label">Total Repositories</div>
        </div>
        <div class="card">
            <div class="card-value">{summary["coverage"]["average"]}%</div>
            <div class="card-label">Average Coverage</div>
        </div>
        <div class="card">
            <div class="card-value">{summary["mutation"]["average"]}%</div>
            <div class="card-label">Average Mutation Score</div>
        </div>
        <div class="card">
            <div class="card-value">{len(summary["languages"])}</div>
            <div class="card-label">Languages</div>
        </div>
        <div class="card">
            <div class="card-value">
                {summary["tests"]["total_passed"]}/{total_tests}
            </div>
            <div class="card-label">Tests Passed</div>
        </div>
    </div>

    <h2>Repository Status</h2>
    <table>
        <thead>
            <tr>
                <th>Repository</th>
                <th>Language</th>
                <th>Branch</th>
                <th>Status</th>
                <th>Coverage</th>
                <th>Tests</th>
                <th>Mutation</th>
                <th>Last Run</th>
            </tr>
        </thead>
        <tbody>
            {repos_html}
        </tbody>
    </table>

    <p class="timestamp">Generated: {summary["generated_at"]}</p>
</body>
</html>
"""
    return html_output
