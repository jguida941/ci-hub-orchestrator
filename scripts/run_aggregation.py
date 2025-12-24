#!/usr/bin/env python3
"""
Hub Orchestrator Aggregation Script.

This script replaces the inline Python in hub-orchestrator.yml.
It downloads dispatch metadata, polls runs, fetches artifacts,
validates correlation IDs, and generates the hub report.

Usage:
    python scripts/run_aggregation.py \
        --dispatch-dir dispatch-artifacts \
        --output hub-report.json \
        --summary-file $GITHUB_STEP_SUMMARY \
        --defaults-file config/defaults.yaml

Environment:
    GITHUB_TOKEN: GitHub API token (required)
    HUB_RUN_ID: Hub orchestrator run ID
    HUB_EVENT: Trigger event name
    TOTAL_REPOS: Total repo count from matrix
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib import request

import yaml

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from correlation import find_run_by_correlation_id, validate_correlation_id


class GitHubAPI:
    """GitHub API client with retry logic."""

    def __init__(self, token: str):
        self.token = token

    def get(self, url: str, retries: int = 3, backoff: float = 2.0) -> dict:
        """Make GET request with retry logic."""
        attempt = 0
        while True:
            try:
                req = request.Request(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                with request.urlopen(req) as resp:
                    return json.loads(resp.read().decode())
            except Exception as exc:
                attempt += 1
                if attempt > retries:
                    raise
                sleep_for = backoff * attempt
                print(f"Retry {attempt}/{retries} for {url} after error: {exc} (sleep {sleep_for}s)")
                time.sleep(sleep_for)

    def download_artifact(self, archive_url: str, target_dir: Path) -> Path | None:
        """Download and extract artifact ZIP."""
        req = request.Request(
            archive_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with request.urlopen(req) as resp:
                data = resp.read()
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "artifact.zip"
            zip_path.write_bytes(data)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
            return target_dir
        except Exception as exc:
            print(f"Warning: failed to download artifact {archive_url}: {exc}")
            return None


def load_dispatch_metadata(dispatch_dir: Path) -> list[dict]:
    """Load all dispatch metadata JSON files."""
    entries = []
    for path in dispatch_dir.rglob("*.json"):
        try:
            data = json.loads(path.read_text())
            data["_source"] = str(path)
            entries.append(data)
        except Exception as exc:
            print(f"Warning: could not read {path}: {exc}")
    return entries


def create_run_status(entry: dict) -> dict:
    """Create initial run status structure from dispatch metadata."""
    repo = entry.get("repo", "unknown/unknown")
    run_id = entry.get("run_id")

    return {
        "config": entry.get("config", repo.split("/")[-1] if "/" in repo else repo),
        "repo": repo,
        "subdir": entry.get("subdir", ""),
        "language": entry.get("language"),
        "branch": entry.get("branch"),
        "workflow": entry.get("workflow"),
        "run_id": run_id or "",
        "correlation_id": entry.get("correlation_id", ""),
        "status": "missing_run_id" if not run_id else "unknown",
        "conclusion": "unknown",
        # Common quality metrics
        "coverage": None,
        "mutation_score": None,
        # Java-specific tools
        "checkstyle_issues": None,
        "spotbugs_issues": None,
        "pmd_violations": None,
        "owasp_critical": None,
        "owasp_high": None,
        "owasp_medium": None,
        # Python-specific tools
        "tests_passed": None,
        "tests_failed": None,
        "ruff_errors": None,
        "black_issues": None,
        "isort_issues": None,
        "mypy_errors": None,
        "bandit_high": None,
        "bandit_medium": None,
        "pip_audit_vulns": None,
        # Cross-language security tools
        "semgrep_findings": None,
        "trivy_critical": None,
        "trivy_high": None,
        # Track which tools ran
        "tools_ran": {},
    }


def poll_run_completion(
    api: GitHubAPI,
    owner: str,
    repo: str,
    run_id: str,
    timeout_sec: int = 1800,
) -> tuple[str, str]:
    """Poll run until completion or timeout. Returns (status, conclusion)."""
    pending_statuses = {"queued", "in_progress", "waiting", "pending"}
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    start_poll = time.time()
    delay = 10

    while True:
        try:
            run = api.get(url)
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion", "unknown")

            if status not in pending_statuses:
                return status, conclusion

            if time.time() - start_poll > timeout_sec:
                return "timed_out", "timed_out"

            time.sleep(delay)
            delay = min(delay * 1.5, 60)
        except Exception as exc:
            print(f"Warning: error polling run {run_id}: {exc}")
            return "fetch_failed", "unknown"


def extract_metrics_from_report(report_data: dict, run_status: dict) -> None:
    """Extract metrics from report.json into run_status (mutates run_status)."""
    results_data = report_data.get("results", {}) or {}
    tool_metrics = report_data.get("tool_metrics", {}) or {}

    # Common quality metrics
    run_status["coverage"] = results_data.get("coverage")
    run_status["mutation_score"] = results_data.get("mutation_score")

    # Java-specific tools
    run_status["checkstyle_issues"] = tool_metrics.get("checkstyle_issues")
    run_status["spotbugs_issues"] = tool_metrics.get("spotbugs_issues")
    run_status["pmd_violations"] = tool_metrics.get("pmd_violations")
    run_status["owasp_critical"] = tool_metrics.get("owasp_critical")
    run_status["owasp_high"] = tool_metrics.get("owasp_high")
    run_status["owasp_medium"] = tool_metrics.get("owasp_medium")

    # Python-specific tools
    run_status["tests_passed"] = results_data.get("tests_passed")
    run_status["tests_failed"] = results_data.get("tests_failed")
    run_status["ruff_errors"] = tool_metrics.get("ruff_errors")
    run_status["black_issues"] = tool_metrics.get("black_issues")
    run_status["isort_issues"] = tool_metrics.get("isort_issues")
    run_status["mypy_errors"] = tool_metrics.get("mypy_errors")
    run_status["bandit_high"] = tool_metrics.get("bandit_high")
    run_status["bandit_medium"] = tool_metrics.get("bandit_medium")
    run_status["pip_audit_vulns"] = tool_metrics.get("pip_audit_vulns")

    # Cross-language security tools
    run_status["semgrep_findings"] = tool_metrics.get("semgrep_findings")
    run_status["trivy_critical"] = tool_metrics.get("trivy_critical")
    run_status["trivy_high"] = tool_metrics.get("trivy_high")

    # Track which tools ran
    run_status["tools_ran"] = report_data.get("tools_ran", {})


def fetch_and_validate_artifact(
    api: GitHubAPI,
    owner: str,
    repo: str,
    run_id: str,
    expected_correlation_id: str,
    workflow: str,
    token: str,
) -> dict | None:
    """Fetch ci-report artifact and validate correlation ID.

    Returns report_data if valid, None otherwise.
    If correlation mismatch, attempts to find correct run.
    """
    try:
        artifacts = api.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        )
        ci_artifacts = artifacts.get("artifacts", [])

        # Prefer artifact ending with ci-report
        artifact = next(
            (a for a in ci_artifacts if a.get("name", "").endswith("ci-report")),
            None
        )
        if not artifact and ci_artifacts:
            artifact = next(
                (a for a in ci_artifacts if "report" in a.get("name", "")),
                ci_artifacts[0] if ci_artifacts else None
            )

        if not artifact:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            extracted = api.download_artifact(artifact["archive_download_url"], Path(tmpdir))
            if not extracted:
                return None

            report_file = next(iter(Path(extracted).rglob("report.json")), None)
            if not report_file or not report_file.exists():
                return None

            report_data = json.loads(report_file.read_text())
            report_corr = report_data.get("hub_correlation_id", "")

            # Validate correlation ID
            if not validate_correlation_id(expected_correlation_id, report_corr):
                print(
                    f"Correlation mismatch for {owner}/{repo} run {run_id} "
                    f"(expected {expected_correlation_id}, got {report_corr}); searching for correct run..."
                )

                # Try to find correct run by correlation ID
                correct_run_id = find_run_by_correlation_id(
                    owner, repo, workflow, expected_correlation_id, token,
                    gh_get=api.get
                )

                if correct_run_id and correct_run_id != run_id:
                    print(f"Found correct run {correct_run_id}, re-fetching artifacts...")
                    # Recursively fetch from correct run (with empty expected to skip re-validation)
                    return fetch_and_validate_artifact(
                        api, owner, repo, correct_run_id, "", workflow, token
                    )
                else:
                    print(f"Could not find correct run for {owner}/{repo}, skipping artifact.")
                    return None

            return report_data

    except Exception as exc:
        print(f"Warning: failed to fetch artifacts for run {run_id}: {exc}")
        return None


def aggregate_results(results: list[dict]) -> dict:
    """Aggregate metrics across all results."""

    def collect_values(key: str) -> list:
        return [r[key] for r in results if isinstance(r.get(key), (int, float))]

    # Quality metrics
    coverages = collect_values("coverage")
    mutations = collect_values("mutation_score")

    # Vulnerability metrics
    owasp_critical = collect_values("owasp_critical")
    owasp_high = collect_values("owasp_high")
    owasp_medium = collect_values("owasp_medium")
    bandit_high = collect_values("bandit_high")
    bandit_medium = collect_values("bandit_medium")
    pip_audit_vulns = collect_values("pip_audit_vulns")
    trivy_critical = collect_values("trivy_critical")
    trivy_high = collect_values("trivy_high")
    semgrep_findings = collect_values("semgrep_findings")

    # Code quality metrics
    checkstyle_issues = collect_values("checkstyle_issues")
    spotbugs_issues = collect_values("spotbugs_issues")
    pmd_violations = collect_values("pmd_violations")
    ruff_errors = collect_values("ruff_errors")
    black_issues = collect_values("black_issues")
    isort_issues = collect_values("isort_issues")
    mypy_errors = collect_values("mypy_errors")

    aggregated = {}

    if coverages:
        aggregated["coverage_average"] = round(sum(coverages) / len(coverages), 1)
    if mutations:
        aggregated["mutation_average"] = round(sum(mutations) / len(mutations), 1)

    aggregated["total_critical_vulns"] = sum(owasp_critical) + sum(trivy_critical)
    aggregated["total_high_vulns"] = sum(owasp_high) + sum(bandit_high) + sum(trivy_high)
    aggregated["total_medium_vulns"] = sum(owasp_medium) + sum(bandit_medium)
    aggregated["total_pip_audit_vulns"] = sum(pip_audit_vulns)
    aggregated["total_semgrep_findings"] = sum(semgrep_findings)
    aggregated["total_code_quality_issues"] = (
        sum(checkstyle_issues) + sum(spotbugs_issues) + sum(pmd_violations) +
        sum(ruff_errors) + sum(black_issues) + sum(isort_issues) + sum(mypy_errors)
    )

    return aggregated


def generate_summary_markdown(
    results: list[dict],
    report: dict,
    total_repos: int,
    dispatched: int,
    missing: int,
    missing_run_id: int,
) -> str:
    """Generate GitHub step summary markdown."""

    def fmt(val, suffix=""):
        return f"{val}{suffix}" if val is not None else "-"

    lines = [
        "# CI/CD Hub Report",
        "",
        f"**Run ID:** {report['hub_run_id']}",
        f"**Timestamp:** {report['timestamp']}",
        "",
        "## Dispatch Status",
        f"- Total configs: {total_repos}",
        f"- Successfully dispatched: {dispatched}",
        f"- Missing metadata: {missing}",
        f"- Missing run IDs: {missing_run_id}",
        "",
    ]

    # Separate by language
    java_results = [r for r in results if r.get("language") == "java"]
    python_results = [r for r in results if r.get("language") == "python"]

    # Java table
    if java_results:
        lines.extend([
            "## Java Repos",
            "",
            "| Config | Status | Cov | Mut | CS | SB | PMD | OWASP | Semgrep | Trivy |",
            "|--------|--------|-----|-----|----|----|-----|-------|---------|-------|",
        ])
        for entry in java_results:
            config = entry.get("config", "unknown")
            status = entry.get("conclusion", entry.get("status", "unknown"))
            status_label = "PASS" if status == "success" else "FAIL" if status in ("failure", "failed") else "PENDING"

            cov = fmt(entry.get("coverage"), "%")
            mut = fmt(entry.get("mutation_score"), "%")
            cs = fmt(entry.get("checkstyle_issues"))
            sb = fmt(entry.get("spotbugs_issues"))
            pmd = fmt(entry.get("pmd_violations"))

            oc, oh, om = entry.get("owasp_critical"), entry.get("owasp_high"), entry.get("owasp_medium")
            owasp = f"{oc or 0}/{oh or 0}/{om or 0}" if any(v is not None for v in [oc, oh, om]) else "-"

            sem = fmt(entry.get("semgrep_findings"))
            tc, th = entry.get("trivy_critical"), entry.get("trivy_high")
            trivy = f"{tc or 0}/{th or 0}" if any(v is not None for v in [tc, th]) else "-"

            lines.append(f"| {config} | {status_label} | {cov} | {mut} | {cs} | {sb} | {pmd} | {owasp} | {sem} | {trivy} |")
        lines.append("")

    # Python table
    if python_results:
        lines.extend([
            "## Python Repos",
            "",
            "| Config | Status | Cov | Mut | Tests | Ruff | Black | isort | mypy | Bandit | pip-audit | Semgrep | Trivy |",
            "|--------|--------|-----|-----|-------|------|-------|-------|------|--------|-----------|---------|-------|",
        ])
        for entry in python_results:
            config = entry.get("config", "unknown")
            status = entry.get("conclusion", entry.get("status", "unknown"))
            status_label = "PASS" if status == "success" else "FAIL" if status in ("failure", "failed") else "PENDING"

            cov = fmt(entry.get("coverage"), "%")
            mut = fmt(entry.get("mutation_score"), "%")

            tp, tf = entry.get("tests_passed"), entry.get("tests_failed")
            tests = f"{tp or 0} pass/{tf or 0} fail" if any(v is not None for v in [tp, tf]) else "-"

            ruff = fmt(entry.get("ruff_errors"))
            black = fmt(entry.get("black_issues"))
            isort = fmt(entry.get("isort_issues"))
            mypy = fmt(entry.get("mypy_errors"))

            bh, bm = entry.get("bandit_high"), entry.get("bandit_medium")
            bandit = f"{bh or 0}/{bm or 0}" if any(v is not None for v in [bh, bm]) else "-"

            pip = fmt(entry.get("pip_audit_vulns"))
            sem = fmt(entry.get("semgrep_findings"))

            tc, th = entry.get("trivy_critical"), entry.get("trivy_high")
            trivy = f"{tc or 0}/{th or 0}" if any(v is not None for v in [tc, th]) else "-"

            lines.append(f"| {config} | {status_label} | {cov} | {mut} | {tests} | {ruff} | {black} | {isort} | {mypy} | {bandit} | {pip} | {sem} | {trivy} |")
        lines.append("")

    # Aggregated metrics
    lines.extend([
        "## Aggregated Metrics",
        "",
        "### Quality",
    ])
    if "coverage_average" in report:
        lines.append(f"- **Average Coverage:** {report['coverage_average']}%")
    if "mutation_average" in report:
        lines.append(f"- **Average Mutation Score:** {report['mutation_average']}%")
    lines.append(f"- **Total Code Quality Issues:** {report['total_code_quality_issues']}")

    lines.extend([
        "",
        "### Security",
        f"- **Critical Vulnerabilities (OWASP+Trivy):** {report['total_critical_vulns']}",
        f"- **High Vulnerabilities (OWASP+Bandit+Trivy):** {report['total_high_vulns']}",
        f"- **Medium Vulnerabilities (OWASP+Bandit):** {report['total_medium_vulns']}",
        f"- **pip-audit Vulnerabilities:** {report['total_pip_audit_vulns']}",
        f"- **Semgrep Findings:** {report['total_semgrep_findings']}",
    ])

    return "\n".join(lines)


def load_thresholds(defaults_file: Path) -> tuple[int, int]:
    """Load vulnerability thresholds from defaults.yaml."""
    max_critical = 0
    max_high = 0

    if defaults_file.exists():
        try:
            defaults = yaml.safe_load(defaults_file.read_text())
            thresholds = defaults.get("thresholds", {})
            max_critical = thresholds.get("max_critical_vulns", 0)
            max_high = thresholds.get("max_high_vulns", 0)
        except Exception as exc:
            print(f"Warning: could not load thresholds from {defaults_file}: {exc}")

    return max_critical, max_high


def run_aggregation(
    dispatch_dir: Path,
    output_file: Path,
    summary_file: Path | None,
    defaults_file: Path,
    token: str,
    hub_run_id: str,
    hub_event: str,
    total_repos: int,
) -> int:
    """Main aggregation logic. Returns exit code (0=success, 1=failure)."""

    api = GitHubAPI(token)
    entries = load_dispatch_metadata(dispatch_dir)
    results = []

    for entry in entries:
        repo_full = entry.get("repo", "unknown/unknown")
        owner_repo = repo_full.split("/")
        if len(owner_repo) != 2:
            print(f"Invalid repo format in entry: {repo_full}")
            continue

        owner, repo = owner_repo
        run_id = entry.get("run_id")
        workflow = entry.get("workflow")
        expected_corr = entry.get("correlation_id", "")

        run_status = create_run_status(entry)

        # Try to find run by correlation ID if run_id is missing
        if not run_id and expected_corr and workflow:
            print(f"No run_id for {repo_full}, searching by correlation_id {expected_corr}...")
            found_run_id = find_run_by_correlation_id(
                owner, repo, workflow, expected_corr, token, gh_get=api.get
            )
            if found_run_id:
                run_id = found_run_id
                run_status["run_id"] = run_id
                run_status["status"] = "unknown"
                print(f"Found run_id {run_id} for {repo_full} via correlation_id")
            else:
                print(f"Could not find run by correlation_id for {repo_full}")

        if not run_id:
            results.append(run_status)
            continue

        # Poll for completion
        status, conclusion = poll_run_completion(api, owner, repo, run_id)
        run_status["status"] = status
        run_status["conclusion"] = conclusion

        if status == "fetch_failed":
            results.append(run_status)
            continue

        # Fetch and validate artifact
        if status == "completed" and conclusion == "success":
            report_data = fetch_and_validate_artifact(
                api, owner, repo, run_id, expected_corr, workflow, token
            )
            if report_data:
                run_status["correlation_id"] = report_data.get("hub_correlation_id", expected_corr)
                extract_metrics_from_report(report_data, run_status)

        results.append(run_status)

    # Build report
    dispatched = len(results)
    missing = max(total_repos - dispatched, 0)
    missing_run_id = len([e for e in results if not e.get("run_id")])

    report = {
        "hub_run_id": hub_run_id,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by": hub_event,
        "total_repos": total_repos,
        "dispatched_repos": dispatched,
        "missing_dispatch_metadata": missing,
        "runs": results,
    }

    # Add aggregated metrics
    aggregated = aggregate_results(results)
    report.update(aggregated)

    # Write report
    output_file.write_text(json.dumps(report, indent=2))
    print(f"Report written to {output_file}")

    # Write summary
    if summary_file:
        summary_md = generate_summary_markdown(
            results, report, total_repos, dispatched, missing, missing_run_id
        )
        summary_file.write_text(summary_md)

    # Check thresholds
    max_critical, max_high = load_thresholds(defaults_file)
    threshold_exceeded = False

    if report["total_critical_vulns"] > max_critical:
        print(f"THRESHOLD EXCEEDED: Critical vulnerabilities {report['total_critical_vulns']} > {max_critical}")
        threshold_exceeded = True
    if report["total_high_vulns"] > max_high:
        print(f"THRESHOLD EXCEEDED: High vulnerabilities {report['total_high_vulns']} > {max_high}")
        threshold_exceeded = True

    # Check for failures
    failed_runs = [
        r for r in results
        if r.get("status") in ("missing_run_id", "fetch_failed", "timed_out")
        or (r.get("status") == "completed" and r.get("conclusion") != "success")
        or r.get("status") not in ("completed",)
    ]

    if failed_runs or missing > 0 or threshold_exceeded:
        if failed_runs:
            print(f"Aggregation detected {len(failed_runs)} failed runs.")
        if missing > 0:
            print(f"Aggregation detected {missing} missing dispatch metadata.")
        if threshold_exceeded:
            print("Vulnerability thresholds exceeded.")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="Hub Orchestrator Aggregation")
    parser.add_argument("--dispatch-dir", type=Path, default=Path("dispatch-artifacts"))
    parser.add_argument("--output", type=Path, default=Path("hub-report.json"))
    parser.add_argument("--summary-file", type=Path, default=None)
    parser.add_argument("--defaults-file", type=Path, default=Path("config/defaults.yaml"))
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: Missing GITHUB_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)

    hub_run_id = os.environ.get("HUB_RUN_ID", "")
    hub_event = os.environ.get("HUB_EVENT", "")
    total_repos = int(os.environ.get("TOTAL_REPOS", 0))

    # Handle GITHUB_STEP_SUMMARY
    summary_file = args.summary_file
    if not summary_file:
        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env:
            summary_file = Path(summary_env)

    exit_code = run_aggregation(
        dispatch_dir=args.dispatch_dir,
        output_file=args.output,
        summary_file=summary_file,
        defaults_file=args.defaults_file,
        token=token,
        hub_run_id=hub_run_id,
        hub_event=hub_event,
        total_repos=total_repos,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
