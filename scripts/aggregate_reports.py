#!/usr/bin/env python3
"""
CI/CD Hub - Report Aggregator

Aggregates CI reports from all connected repositories into a single dashboard.

Usage:
    python aggregate_reports.py --output dashboard.html
    python aggregate_reports.py --output report.json --format json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_reports(reports_dir: Path) -> list[dict]:
    """Load all report JSON files from the reports directory."""
    reports = []

    if not reports_dir.exists():
        return reports

    for report_file in reports_dir.glob("**/report.json"):
        try:
            with open(report_file) as f:
                report = json.load(f)
                report["_source_file"] = str(report_file)
                reports.append(report)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load {report_file}: {e}")

    return reports


def generate_summary(reports: list[dict]) -> dict:
    """Generate a summary from all reports."""
    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_repos": len(reports),
        "languages": {},
        "coverage": {"total": 0, "count": 0, "average": 0},
        "mutation": {"total": 0, "count": 0, "average": 0},
        "repos": [],
    }

    for report in reports:
        repo_name = report.get("repository", "unknown")
        results = report.get("results", {})

        # Track languages
        lang = report.get("java_version") and "java" or "python"
        summary["languages"][lang] = summary["languages"].get(lang, 0) + 1

        # Coverage
        coverage = results.get("coverage", 0)
        if coverage:
            summary["coverage"]["total"] += coverage
            summary["coverage"]["count"] += 1

        # Mutation score
        mutation = results.get("mutation_score", 0)
        if mutation:
            summary["mutation"]["total"] += mutation
            summary["mutation"]["count"] += 1

        # Repo details
        summary["repos"].append(
            {
                "name": repo_name,
                "branch": report.get("branch", "unknown"),
                "status": results.get("build", "unknown"),
                "coverage": coverage,
                "mutation_score": mutation,
                "timestamp": report.get("timestamp", "unknown"),
            }
        )

    # Calculate averages
    if summary["coverage"]["count"] > 0:
        summary["coverage"]["average"] = round(
            summary["coverage"]["total"] / summary["coverage"]["count"], 1
        )

    if summary["mutation"]["count"] > 0:
        summary["mutation"]["average"] = round(
            summary["mutation"]["total"] / summary["mutation"]["count"], 1
        )

    return summary


def generate_html_dashboard(summary: dict) -> str:
    """Generate an HTML dashboard from the summary."""
    repos_html = ""
    for repo in summary["repos"]:
        status_class = "success" if repo["status"] == "success" else "failure"
        repos_html += f"""
        <tr>
            <td>{repo['name']}</td>
            <td>{repo['branch']}</td>
            <td class="{status_class}">{repo['status']}</td>
            <td>{repo['coverage']}%</td>
            <td>{repo['mutation_score']}%</td>
            <td>{repo['timestamp']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI/CD Hub Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
            <div class="card-value">{summary['total_repos']}</div>
            <div class="card-label">Total Repositories</div>
        </div>
        <div class="card">
            <div class="card-value">{summary['coverage']['average']}%</div>
            <div class="card-label">Average Coverage</div>
        </div>
        <div class="card">
            <div class="card-value">{summary['mutation']['average']}%</div>
            <div class="card-label">Average Mutation Score</div>
        </div>
        <div class="card">
            <div class="card-value">{len(summary['languages'])}</div>
            <div class="card-label">Languages</div>
        </div>
    </div>

    <h2>Repository Status</h2>
    <table>
        <thead>
            <tr>
                <th>Repository</th>
                <th>Branch</th>
                <th>Status</th>
                <th>Coverage</th>
                <th>Mutation</th>
                <th>Last Run</th>
            </tr>
        </thead>
        <tbody>
            {repos_html}
        </tbody>
    </table>

    <p class="timestamp">Generated: {summary['generated_at']}</p>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Aggregate CI/CD Hub reports")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path(__file__).parent.parent / "reports",
        help="Directory containing report JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output file path",
    )
    parser.add_argument(
        "--format",
        choices=["json", "html"],
        default="html",
        help="Output format",
    )

    args = parser.parse_args()

    # Load reports
    reports = load_reports(args.reports_dir)
    print(f"Loaded {len(reports)} reports")

    # Generate summary
    summary = generate_summary(reports)

    # Output
    if args.format == "json":
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
    else:
        html = generate_html_dashboard(summary)
        with open(args.output, "w") as f:
            f.write(html)

    print(f"Generated {args.format} report: {args.output}")


if __name__ == "__main__":
    main()
