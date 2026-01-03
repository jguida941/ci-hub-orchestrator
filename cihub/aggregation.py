"""Hub orchestration aggregation helpers."""

from __future__ import annotations

import json
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

import yaml

from cihub.correlation import find_run_by_correlation_id, validate_correlation_id
from cihub.reporting import detect_language, render_summary


class GitHubAPI:
    """GitHub API client with retry logic."""

    def __init__(self, token: str):
        self.token = token

    def get(self, url: str, retries: int = 3, backoff: float = 2.0, timeout: int = 30) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                req = request.Request(  # noqa: S310
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                    data = json.loads(resp.read().decode())
                    return data if isinstance(data, dict) else {}
            except Exception as exc:
                attempt += 1
                if attempt > retries:
                    raise
                sleep_for = backoff * attempt
                print(f"Retry {attempt}/{retries} for {url}: {exc} (sleep {sleep_for}s)")
                time.sleep(sleep_for)

    def download_artifact(self, archive_url: str, target_dir: Path) -> Path | None:
        """Download an artifact from GitHub.

        GitHub's artifact download API returns a 302 redirect to Azure Blob Storage.
        We must NOT send the Authorization header to Azure (it causes 401 errors).
        Instead, we manually handle the redirect: first get the redirect URL with auth,
        then download from Azure without auth.
        """
        print("   Downloading artifact...")

        # Step 1: Request the artifact URL with auth to get the redirect location
        # We use a custom opener that does NOT follow redirects automatically
        class NoRedirectHandler(request.HTTPRedirectHandler):
            def redirect_request(
                self,
                req: request.Request,
                fp: Any,
                code: int,
                msg: str,
                headers: Any,
                newurl: str,
            ) -> None:
                return None  # Don't follow redirects

        opener = request.build_opener(NoRedirectHandler)

        req = request.Request(  # noqa: S310
            archive_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            opener.open(req, timeout=60)  # noqa: S310
            # If we get here without redirect, something is wrong
            print("   WARNING: No redirect received from GitHub API")
            return None
        except request.HTTPError as e:
            if e.code == 302:
                # This is expected - GitHub redirects to Azure Blob Storage
                redirect_url = e.headers.get("Location")
                if not redirect_url:
                    print("   WARNING: 302 redirect but no Location header")
                    return None
            else:
                print(f"   Failed to get artifact redirect: HTTP {e.code}")
                return None
        except Exception as exc:
            print(f"   Failed to get artifact redirect: {exc}")
            return None

        # Step 2: Download from Azure Blob Storage WITHOUT auth headers
        try:
            req_azure = request.Request(redirect_url)  # noqa: S310
            with request.urlopen(req_azure, timeout=120) as resp:  # noqa: S310
                data = resp.read()
            target_dir.mkdir(parents=True, exist_ok=True)
            zip_path = target_dir / "artifact.zip"
            zip_path.write_bytes(data)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
            print(f"   Artifact extracted to {target_dir}")
            return target_dir
        except Exception as exc:
            print(f"   Failed to download artifact from storage: {exc}")
            return None


def load_dispatch_metadata(dispatch_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in dispatch_dir.rglob("*.json"):
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                print(f"Warning: skipping non-object JSON in {path}")
                continue
            data["_source"] = str(path)
            entries.append(data)
        except Exception as exc:
            print(f"Warning: could not read {path}: {exc}")
    return entries


def create_run_status(entry: dict[str, Any]) -> dict[str, Any]:
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
        "tools_configured": {},
        "tools_success": {},
    }


def _artifact_name_from_report(report_path: Path, reports_dir: Path) -> str:
    try:
        relative = report_path.relative_to(reports_dir)
    except ValueError:
        relative = report_path

    if relative.parts:
        return relative.parts[0]
    return report_path.parent.name or report_path.stem


def _config_from_artifact_name(artifact_name: str) -> str:
    suffix = "-ci-report"
    if artifact_name.endswith(suffix):
        return artifact_name[: -len(suffix)]
    return artifact_name


def _status_from_report(report_data: dict[str, Any]) -> tuple[str, str]:
    results = report_data.get("results", {}) or {}
    status = results.get("build") or results.get("test") or "unknown"
    if status in {"success", "failure", "skipped"}:
        return "completed", status

    tests_failed = results.get("tests_failed")
    if isinstance(tests_failed, int):
        return "completed", "failure" if tests_failed > 0 else "success"
    return "completed", "unknown"


def _run_status_from_report(
    report_data: dict[str, Any],
    report_path: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    artifact_name = _artifact_name_from_report(report_path, reports_dir)
    config_name = _config_from_artifact_name(artifact_name)
    repo = report_data.get("repository") or config_name
    branch = report_data.get("branch") or ""
    workflow_ref = report_data.get("metadata", {}).get("workflow_ref", "")
    correlation = report_data.get("hub_correlation_id", "") or ""
    run_id = report_data.get("run_id", "") or ""
    workdir = report_data.get("environment", {}).get("workdir") or ""
    language = detect_language(report_data)

    entry = {
        "config": config_name,
        "repo": repo,
        "subdir": workdir if workdir not in ("", ".") else "",
        "language": language,
        "branch": branch,
        "workflow": workflow_ref,
        "run_id": run_id,
        "correlation_id": correlation,
    }
    run_status = create_run_status(entry)
    status, conclusion = _status_from_report(report_data)
    run_status["status"] = status
    run_status["conclusion"] = conclusion
    return run_status


def _run_status_for_invalid_report(report_path: Path, reports_dir: Path, reason: str) -> dict[str, Any]:
    artifact_name = _artifact_name_from_report(report_path, reports_dir)
    config_name = _config_from_artifact_name(artifact_name)
    entry = {
        "config": config_name,
        "repo": config_name,
        "subdir": "",
        "language": "unknown",
        "branch": "",
        "workflow": "",
        "run_id": "",
        "correlation_id": "",
    }
    run_status = create_run_status(entry)
    run_status["status"] = reason
    run_status["conclusion"] = "failure"
    return run_status


def poll_run_completion(
    api: GitHubAPI,
    owner: str,
    repo: str,
    run_id: str,
    timeout_sec: int = 1800,
) -> tuple[str, str]:
    pending_statuses = {"queued", "in_progress", "waiting", "pending"}
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    run_url = f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"
    start_poll = time.time()
    delay: float = 10.0

    print(f"Polling {owner}/{repo} run {run_id}...")
    print(f"   View: {run_url}")

    while True:
        try:
            elapsed = int(time.time() - start_poll)
            elapsed_min = elapsed // 60
            elapsed_sec = elapsed % 60

            run = api.get(url)
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion", "unknown")

            print(f"   [{elapsed_min:02d}:{elapsed_sec:02d}] {owner}/{repo}: status={status}, conclusion={conclusion}")

            if status not in pending_statuses:
                print(f"Completed {owner}/{repo}: {conclusion}")
                return status, conclusion

            if time.time() - start_poll > timeout_sec:
                print(f"TIMEOUT: {owner}/{repo} after {timeout_sec}s")
                return "timed_out", "timed_out"

            print(f"   Waiting {int(delay)}s before next poll...")
            time.sleep(delay)
            delay = min(delay * 1.5, 60)
        except Exception as exc:
            print(f"ERROR polling {owner}/{repo} run {run_id}: {exc}")
            return "fetch_failed", "unknown"


def extract_metrics_from_report(report_data: dict[str, Any], run_status: dict[str, Any]) -> None:
    results_data = report_data.get("results", {}) or {}
    tool_metrics = report_data.get("tool_metrics", {}) or {}

    run_status["coverage"] = results_data.get("coverage")
    run_status["mutation_score"] = results_data.get("mutation_score")

    run_status["checkstyle_issues"] = tool_metrics.get("checkstyle_issues")
    run_status["spotbugs_issues"] = tool_metrics.get("spotbugs_issues")
    run_status["pmd_violations"] = tool_metrics.get("pmd_violations")
    run_status["owasp_critical"] = tool_metrics.get("owasp_critical")
    run_status["owasp_high"] = tool_metrics.get("owasp_high")
    run_status["owasp_medium"] = tool_metrics.get("owasp_medium")

    run_status["tests_passed"] = results_data.get("tests_passed")
    run_status["tests_failed"] = results_data.get("tests_failed")
    run_status["ruff_errors"] = tool_metrics.get("ruff_errors")
    run_status["black_issues"] = tool_metrics.get("black_issues")
    run_status["isort_issues"] = tool_metrics.get("isort_issues")
    run_status["mypy_errors"] = tool_metrics.get("mypy_errors")
    run_status["bandit_high"] = tool_metrics.get("bandit_high")
    run_status["bandit_medium"] = tool_metrics.get("bandit_medium")
    run_status["pip_audit_vulns"] = tool_metrics.get("pip_audit_vulns")

    run_status["semgrep_findings"] = tool_metrics.get("semgrep_findings")
    run_status["trivy_critical"] = tool_metrics.get("trivy_critical")
    run_status["trivy_high"] = tool_metrics.get("trivy_high")

    run_status["tools_ran"] = report_data.get("tools_ran", {})
    run_status["tools_configured"] = report_data.get("tools_configured", {})
    run_status["tools_success"] = report_data.get("tools_success", {})


def fetch_and_validate_artifact(
    api: GitHubAPI,
    owner: str,
    repo: str,
    run_id: str,
    expected_correlation_id: str,
    workflow: str,
    token: str,
) -> dict[str, Any] | None:
    try:
        print(f"   Fetching artifacts for run {run_id}...")
        artifacts = api.get(f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts")
        ci_artifacts = artifacts.get("artifacts", [])
        print(f"   Found {len(ci_artifacts)} artifact(s)")

        artifact = next((a for a in ci_artifacts if a.get("name", "").endswith("ci-report")), None)
        if not artifact and ci_artifacts:
            artifact = next(
                (a for a in ci_artifacts if "report" in a.get("name", "")),
                ci_artifacts[0] if ci_artifacts else None,
            )

        if not artifact:
            print(f"   WARNING: No ci-report artifact found for {owner}/{repo}")
            if ci_artifacts:
                names = [a.get("name", "?") for a in ci_artifacts]
                print(f"   Available artifacts: {names}")
            return None

        print(f"   Using artifact: {artifact.get('name')}")

        with tempfile.TemporaryDirectory() as tmpdir:
            dl_url = artifact["archive_download_url"]
            extracted = api.download_artifact(dl_url, Path(tmpdir))
            if not extracted:
                return None

            report_file = next(iter(Path(extracted).rglob("report.json")), None)
            if not report_file or not report_file.exists():
                print("   WARNING: No report.json found in artifact")
                return None

            report_data = json.loads(report_file.read_text())
            if not isinstance(report_data, dict):
                print("   WARNING: report.json is not a JSON object")
                return None
            report_corr_value = report_data.get("hub_correlation_id", "")
            report_corr = report_corr_value if isinstance(report_corr_value, str) else ""

            if expected_correlation_id:
                print(f"   Validating correlation: expected={expected_correlation_id}, got={report_corr or '(none)'}")
            if not validate_correlation_id(expected_correlation_id, report_corr):
                print(
                    f"Correlation mismatch for {owner}/{repo} run {run_id} "
                    f"(expected {expected_correlation_id}, got {report_corr})"
                )

                correct_run_id = find_run_by_correlation_id(
                    owner,
                    repo,
                    workflow,
                    expected_correlation_id,
                    token,
                    gh_get=api.get,
                )

                if correct_run_id and correct_run_id != run_id:
                    print(f"Found correct run {correct_run_id}, re-fetching...")
                    return fetch_and_validate_artifact(api, owner, repo, correct_run_id, "", workflow, token)
                print(f"Could not find correct run for {owner}/{repo}")
                return None

            print("   Correlation OK, extracting metrics...")
            return report_data

    except Exception as exc:
        print(f"Warning: failed to fetch artifacts for run {run_id}: {exc}")
        return None


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    def collect_values(key: str) -> list[float]:
        return [r[key] for r in results if isinstance(r.get(key), (int, float))]

    coverages = collect_values("coverage")
    mutations = collect_values("mutation_score")

    owasp_critical = collect_values("owasp_critical")
    owasp_high = collect_values("owasp_high")
    owasp_medium = collect_values("owasp_medium")
    bandit_high = collect_values("bandit_high")
    bandit_medium = collect_values("bandit_medium")
    pip_audit_vulns = collect_values("pip_audit_vulns")
    trivy_critical = collect_values("trivy_critical")
    trivy_high = collect_values("trivy_high")
    semgrep_findings = collect_values("semgrep_findings")

    checkstyle_issues = collect_values("checkstyle_issues")
    spotbugs_issues = collect_values("spotbugs_issues")
    pmd_violations = collect_values("pmd_violations")
    ruff_errors = collect_values("ruff_errors")
    black_issues = collect_values("black_issues")
    isort_issues = collect_values("isort_issues")
    mypy_errors = collect_values("mypy_errors")

    aggregated: dict[str, Any] = {}

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
        sum(checkstyle_issues)
        + sum(spotbugs_issues)
        + sum(pmd_violations)
        + sum(ruff_errors)
        + sum(black_issues)
        + sum(isort_issues)
        + sum(mypy_errors)
    )

    return aggregated


def generate_details_markdown(results: list[dict[str, Any]]) -> str:
    lines = ["# Per-Repo Details", ""]
    for entry in results:
        config = entry.get("config", "unknown")
        report_data = entry.get("_report_data")
        status = entry.get("status", "unknown")
        conclusion = entry.get("conclusion", "unknown")
        lines.append(f"<details><summary><strong>{config}</strong></summary>")
        lines.append("")
        if report_data:
            try:
                detailed_summary = render_summary(report_data, include_metrics=True)
                lines.append(detailed_summary)
            except Exception as exc:
                lines.append(f"*Error rendering summary: {exc}*")
        else:
            lines.append(f"*No report.json available (status: {status}, conclusion: {conclusion}).*")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines)


def generate_summary_markdown(
    results: list[dict[str, Any]],
    report: dict[str, Any],
    total_repos: int,
    dispatched: int,
    missing: int,
    missing_run_id: int,
    *,
    dispatched_label: str = "Successfully dispatched",
    missing_label: str = "Missing metadata",
    include_details: bool = False,
    details_md: str | None = None,
) -> str:
    def fmt(val, suffix=""):
        return f"{val}{suffix}" if val is not None else "-"

    def status_label_for(entry: dict[str, Any]) -> str:
        status = entry.get("status", "unknown")
        conclusion = entry.get("conclusion", status)
        if status in {"missing_run_id", "fetch_failed", "timed_out", "missing_report"}:
            return "MISSING"
        if conclusion == "success":
            return "PASS"
        if conclusion in {"failure", "failed", "cancelled", "timed_out"}:
            return "FAIL"
        if status == "completed" and isinstance(conclusion, str) and conclusion:
            return conclusion.upper()
        return "PENDING"

    failed_runs = len([r for r in results if status_label_for(r) == "FAIL"])
    missing_runs = len([r for r in results if status_label_for(r) == "MISSING"])
    pending_runs = len([r for r in results if status_label_for(r) == "PENDING"])

    lines = [
        "# CI/CD Hub Report",
        "",
        f"**Run ID:** {report['hub_run_id']}",
        f"**Timestamp:** {report['timestamp']}",
        "",
        "## Dispatch Status",
        f"- Total configs: {total_repos}",
        f"- {dispatched_label}: {dispatched}",
        f"- {missing_label}: {missing}",
        f"- Missing run IDs: {missing_run_id}",
        f"- Failed runs: {failed_runs}",
        f"- Missing reports: {missing_runs}",
        f"- Pending runs: {pending_runs}",
        "",
    ]

    java_results = [r for r in results if r.get("language") == "java"]
    python_results = [r for r in results if r.get("language") == "python"]

    if java_results:
        lines.extend(
            [
                "## Java Repos",
                "",
                "| Config | Status | Coverage | Mutation | Checkstyle | SpotBugs | PMD | OWASP | Semgrep | Trivy |",
                "|--------|--------|----------|----------|------------|----------|-----|-------|---------|-------|",
            ]
        )
        for entry in java_results:
            config = entry.get("config", "unknown")
            status_label = status_label_for(entry)

            cov = fmt(entry.get("coverage"), "%")
            mut = fmt(entry.get("mutation_score"), "%")
            cs = fmt(entry.get("checkstyle_issues"))
            sb = fmt(entry.get("spotbugs_issues"))
            pmd = fmt(entry.get("pmd_violations"))

            oc = entry.get("owasp_critical")
            oh = entry.get("owasp_high")
            om = entry.get("owasp_medium")
            if any(v is not None for v in [oc, oh, om]):
                owasp = f"{oc or 0}/{oh or 0}/{om or 0}"
            else:
                owasp = "-"

            sem = fmt(entry.get("semgrep_findings"))
            tc, th = entry.get("trivy_critical"), entry.get("trivy_high")
            if any(v is not None for v in [tc, th]):
                trivy = f"{tc or 0}/{th or 0}"
            else:
                trivy = "-"

            lines.append(
                f"| {config} | {status_label} | {cov} | {mut} | {cs} | {sb} | {pmd} | {owasp} | {sem} | {trivy} |"
            )
        lines.append("")

    if python_results:
        hdr = "| Config | Status | Coverage | Mutation | Tests | Ruff | Black "
        hdr += "| isort | mypy | Bandit | pip-audit | Semgrep | Trivy |"
        sep = "|--------|--------|----------|----------|-------|------|-------"
        sep += "|-------|------|--------|-----------|---------|-------|"
        lines.extend(["## Python Repos", "", hdr, sep])
        for entry in python_results:
            config = entry.get("config", "unknown")
            status_label = status_label_for(entry)

            cov = fmt(entry.get("coverage"), "%")
            mut = fmt(entry.get("mutation_score"), "%")

            tp, tf = entry.get("tests_passed"), entry.get("tests_failed")
            if any(v is not None for v in [tp, tf]):
                tests = f"{tp or 0}/{tf or 0}"
            else:
                tests = "-"

            ruff = fmt(entry.get("ruff_errors"))
            black = fmt(entry.get("black_issues"))
            isort = fmt(entry.get("isort_issues"))
            mypy = fmt(entry.get("mypy_errors"))

            bh, bm = entry.get("bandit_high"), entry.get("bandit_medium")
            if any(v is not None for v in [bh, bm]):
                bandit = f"{bh or 0}/{bm or 0}"
            else:
                bandit = "-"

            pip = fmt(entry.get("pip_audit_vulns"))
            sem = fmt(entry.get("semgrep_findings"))

            tc, th = entry.get("trivy_critical"), entry.get("trivy_high")
            if any(v is not None for v in [tc, th]):
                trivy = f"{tc or 0}/{th or 0}"
            else:
                trivy = "-"

            lines.append(
                f"| {config} | {status_label} | {cov} | {mut} | {tests} "
                f"| {ruff} | {black} | {isort} | {mypy} | {bandit} "
                f"| {pip} | {sem} | {trivy} |"
            )
        lines.append("")

    lines.extend(["## Aggregated Metrics", "", "### Quality"])
    if "coverage_average" in report:
        lines.append(f"- **Average Coverage:** {report['coverage_average']}%")
    if "mutation_average" in report:
        lines.append(f"- **Average Mutation Score:** {report['mutation_average']}%")
    total_issues = report["total_code_quality_issues"]
    lines.append(f"- **Total Code Quality Issues:** {total_issues}")

    crit = report["total_critical_vulns"]
    high = report["total_high_vulns"]
    med = report["total_medium_vulns"]
    pip_v = report["total_pip_audit_vulns"]
    sem_f = report["total_semgrep_findings"]
    lines.extend(
        [
            "",
            "### Security",
            f"- **Critical Vulnerabilities (OWASP+Trivy):** {crit}",
            f"- **High Vulnerabilities (OWASP+Bandit+Trivy):** {high}",
            f"- **Medium Vulnerabilities (OWASP+Bandit):** {med}",
            f"- **pip-audit Vulnerabilities:** {pip_v}",
            f"- **Semgrep Findings:** {sem_f}",
        ]
    )

    if include_details:
        if details_md is None:
            details_md = generate_details_markdown(results)
        lines.extend(["", "---", ""])
        lines.extend(details_md.splitlines())

    return "\n".join(lines)


def load_thresholds(defaults_file: Path) -> tuple[int, int]:
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
    *,
    strict: bool = False,
    timeout_sec: int = 1800,
    details_file: Path | None = None,
    include_details: bool = False,
) -> int:
    api = GitHubAPI(token)
    entries = load_dispatch_metadata(dispatch_dir)
    results: list[dict[str, Any]] = []

    if total_repos <= 0:
        total_repos = len(entries)

    print(f"\n{'=' * 60}")
    print(f"Starting aggregation for {len(entries)} dispatched repos")
    print(f"   Hub Run ID: {hub_run_id}")
    print(f"   Total expected repos: {total_repos}")
    print(f"{'=' * 60}\n")

    for idx, entry in enumerate(entries, 1):
        repo_full = entry.get("repo", "unknown/unknown")
        owner_repo = repo_full.split("/")
        if len(owner_repo) != 2:
            print(f"Invalid repo format in entry: {repo_full}")
            continue

        owner, repo = owner_repo
        run_id_value = entry.get("run_id")
        run_id = str(run_id_value) if run_id_value else None
        workflow_value = entry.get("workflow")
        workflow = workflow_value if isinstance(workflow_value, str) else ""
        expected_corr_value = entry.get("correlation_id", "")
        expected_corr = expected_corr_value if isinstance(expected_corr_value, str) else ""

        print(f"\n[{idx}/{len(entries)}] Processing {repo_full}...")
        run_status = create_run_status(entry)

        if not run_id and expected_corr and workflow:
            print(f"No run_id for {repo_full}, searching by {expected_corr}...")
            found_run_id = find_run_by_correlation_id(owner, repo, workflow, expected_corr, token, gh_get=api.get)
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

        status, conclusion = poll_run_completion(api, owner, repo, run_id, timeout_sec=timeout_sec)
        run_status["status"] = status
        run_status["conclusion"] = conclusion

        if status == "fetch_failed":
            results.append(run_status)
            continue

        if status == "completed":
            report_data = fetch_and_validate_artifact(api, owner, repo, run_id, expected_corr, workflow, token)
            if report_data:
                corr = report_data.get("hub_correlation_id", expected_corr)
                run_status["correlation_id"] = corr
                extract_metrics_from_report(report_data, run_status)
                # Store full report for detailed summary generation
                run_status["_report_data"] = report_data
            else:
                run_status["status"] = "missing_report"
                run_status["conclusion"] = "failure"

        results.append(run_status)

    dispatched = len(results)
    missing = max(total_repos - dispatched, 0)
    missing_run_id = len([e for e in results if not e.get("run_id")])

    # Strip _report_data from runs for JSON output (too large), but keep for summary
    runs_for_json = [{k: v for k, v in r.items() if k != "_report_data"} for r in results]

    report: dict[str, Any] = {
        "hub_run_id": hub_run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by": hub_event,
        "total_repos": total_repos,
        "dispatched_repos": dispatched,
        "missing_dispatch_metadata": missing,
        "runs": runs_for_json,
    }

    aggregated = aggregate_results(results)
    report.update(aggregated)

    output_file.write_text(json.dumps(report, indent=2))
    print(f"Report written to {output_file}")

    details_md = None
    if include_details or details_file:
        details_md = generate_details_markdown(results)

    if summary_file:
        summary_md = generate_summary_markdown(
            results,
            report,
            total_repos,
            dispatched,
            missing,
            missing_run_id,
            include_details=include_details,
            details_md=details_md,
        )
        summary_file.write_text(summary_md)

    if details_file and details_md is not None:
        details_file.parent.mkdir(parents=True, exist_ok=True)
        details_file.write_text(details_md)

    max_critical, max_high = load_thresholds(defaults_file)
    total_critical = int(report.get("total_critical_vulns", 0) or 0)
    total_high = int(report.get("total_high_vulns", 0) or 0)
    threshold_exceeded = False

    if total_critical > max_critical:
        print(f"THRESHOLD EXCEEDED: Critical vulns {total_critical} > {max_critical}")
        threshold_exceeded = True
    if total_high > max_high:
        print(f"THRESHOLD EXCEEDED: High vulns {total_high} > {max_high}")
        threshold_exceeded = True

    failed_runs = [
        r
        for r in results
        if r.get("status") in ("missing_run_id", "fetch_failed", "timed_out")
        or (r.get("status") == "completed" and r.get("conclusion") != "success")
        or r.get("status") not in ("completed",)
    ]

    passed_runs = [r for r in results if r.get("status") == "completed" and r.get("conclusion") == "success"]

    print(f"\n{'=' * 60}")
    print("AGGREGATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total dispatched: {dispatched}")
    print(f"Passed: {len(passed_runs)}")
    print(f"Failed: {len(failed_runs)}")
    if missing > 0:
        print(f"Missing metadata: {missing}")
    if missing_run_id > 0:
        print(f"Missing run IDs: {missing_run_id}")

    if failed_runs:
        print("\nFailed runs:")
        for r in failed_runs:
            repo = r.get("repo", "unknown")
            status = r.get("status", "unknown")
            conclusion = r.get("conclusion", "unknown")
            run_id = r.get("run_id", "none")
            if status == "missing_run_id":
                print(f"  - {repo}: no run_id (dispatch may have failed)")
            elif status == "timed_out":
                print(f"  - {repo}: timed out waiting for run {run_id}")
            elif status == "fetch_failed":
                print(f"  - {repo}: failed to fetch run {run_id}")
            else:
                print(f"  - {repo}: {status}/{conclusion} (run {run_id})")

    if threshold_exceeded:
        print("\nThreshold violations:")
        if total_critical > max_critical:
            print(f"  - Critical vulns: {total_critical} (max: {max_critical})")
        if total_high > max_high:
            print(f"  - High vulns: {total_high} (max: {max_high})")

    print(f"{'=' * 60}\n")

    if strict and (failed_runs or missing > 0 or threshold_exceeded):
        return 1
    return 0


def run_reports_aggregation(
    reports_dir: Path,
    output_file: Path,
    summary_file: Path | None,
    defaults_file: Path,
    hub_run_id: str,
    hub_event: str,
    total_repos: int,
    *,
    strict: bool = False,
    details_file: Path | None = None,
    include_details: bool = False,
) -> int:
    reports_dir = reports_dir.resolve()
    report_paths = sorted(reports_dir.rglob("report.json"))
    results: list[dict[str, Any]] = []
    invalid_reports = 0

    if total_repos <= 0:
        total_repos = len(report_paths)

    print(f"\n{'=' * 60}")
    print(f"Starting aggregation from reports dir: {reports_dir}")
    print(f"   Hub Run ID: {hub_run_id}")
    print(f"   Total expected repos: {total_repos}")
    print(f"{'=' * 60}\n")

    for report_path in report_paths:
        try:
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(report_data, dict):
                raise ValueError("report.json is not a JSON object")
        except Exception as exc:
            invalid_reports += 1
            print(f"Warning: invalid report {report_path}: {exc}")
            results.append(_run_status_for_invalid_report(report_path, reports_dir, "invalid_report"))
            continue

        run_status = _run_status_from_report(report_data, report_path, reports_dir)
        extract_metrics_from_report(report_data, run_status)
        # Store full report for detailed summary generation
        run_status["_report_data"] = report_data
        results.append(run_status)

    processed = len(results)
    missing = max(total_repos - processed, 0)
    missing_run_id = len([e for e in results if not e.get("run_id")])

    # Strip _report_data from runs for JSON output (too large), but keep for summary
    runs_for_json = [{k: v for k, v in r.items() if k != "_report_data"} for r in results]

    report: dict[str, Any] = {
        "hub_run_id": hub_run_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by": hub_event,
        "total_repos": total_repos,
        "dispatched_repos": processed,
        "missing_dispatch_metadata": missing,
        "runs": runs_for_json,
    }

    aggregated = aggregate_results(results)
    report.update(aggregated)

    output_file.write_text(json.dumps(report, indent=2))
    print(f"Report written to {output_file}")

    details_md = None
    if include_details or details_file:
        details_md = generate_details_markdown(results)

    if summary_file:
        summary_md = generate_summary_markdown(
            results,
            report,
            total_repos,
            processed,
            missing,
            missing_run_id,
            dispatched_label="Reports processed",
            missing_label="Missing reports",
            include_details=include_details,
            details_md=details_md,
        )
        summary_file.write_text(summary_md)

    if details_file and details_md is not None:
        details_file.parent.mkdir(parents=True, exist_ok=True)
        details_file.write_text(details_md)

    max_critical, max_high = load_thresholds(defaults_file)
    total_critical = int(report.get("total_critical_vulns", 0) or 0)
    total_high = int(report.get("total_high_vulns", 0) or 0)
    threshold_exceeded = False

    if total_critical > max_critical:
        print(f"THRESHOLD EXCEEDED: Critical vulns {total_critical} > {max_critical}")
        threshold_exceeded = True
    if total_high > max_high:
        print(f"THRESHOLD EXCEEDED: High vulns {total_high} > {max_high}")
        threshold_exceeded = True

    failed_runs = [
        r
        for r in results
        if r.get("status") in ("invalid_report", "missing_run_id")
        or (r.get("status") == "completed" and r.get("conclusion") != "success")
        or r.get("status") not in ("completed",)
    ]

    passed_runs = [r for r in results if r.get("status") == "completed" and r.get("conclusion") == "success"]

    print(f"\n{'=' * 60}")
    print("AGGREGATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Reports processed: {processed}")
    print(f"Passed: {len(passed_runs)}")
    print(f"Failed: {len(failed_runs)}")
    if invalid_reports:
        print(f"Invalid reports: {invalid_reports}")
    if missing > 0:
        print(f"Missing reports: {missing}")
    if missing_run_id > 0:
        print(f"Missing run IDs: {missing_run_id}")

    if failed_runs:
        print("\nFailed runs:")
        for r in failed_runs:
            repo = r.get("repo", "unknown")
            status = r.get("status", "unknown")
            conclusion = r.get("conclusion", "unknown")
            run_id = r.get("run_id", "none")
            if status == "missing_run_id":
                print(f"  - {repo}: no run_id")
            elif status == "invalid_report":
                print(f"  - {repo}: invalid report.json")
            else:
                print(f"  - {repo}: {status}/{conclusion} (run {run_id})")

    if threshold_exceeded:
        print("\nThreshold violations:")
        if total_critical > max_critical:
            print(f"  - Critical vulns: {total_critical} (max: {max_critical})")
        if total_high > max_high:
            print(f"  - High vulns: {total_high} (max: {max_high})")

    print(f"{'=' * 60}\n")

    if strict and (failed_runs or missing > 0 or threshold_exceeded):
        return 1
    return 0
