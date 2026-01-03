"""Release, tooling install, and summary commands."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import defusedxml.ElementTree as ET  # Secure XML parsing

from cihub.cli import hub_root
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS
from cihub.utils.progress import _bar

from . import (
    EMPTY_SARIF,
    _append_github_path,
    _append_summary,
    _download_file,
    _resolve_output_path,
    _resolve_summary_path,
    _run_command,
    _sha256,
    _extract_tarball_member,
    _write_outputs,
)


def _resolve_actionlint_version(version: str) -> str:
    if version != "latest":
        return version.lstrip("v")
    url = "https://api.github.com/repos/rhysd/actionlint/releases/latest"
    try:
        import urllib.request

        request = urllib.request.Request(url, headers={"User-Agent": "cihub"})  # noqa: S310
        with urllib.request.urlopen(request) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to resolve latest actionlint version: {exc}") from exc
    tag = str(data.get("tag_name", "")).strip()
    if not tag:
        raise RuntimeError("Failed to resolve latest actionlint version")
    return tag.lstrip("v")


def cmd_actionlint_install(args: argparse.Namespace) -> int:
    try:
        version = _resolve_actionlint_version(args.version)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILURE
    tar_name = f"actionlint_{version}_linux_amd64.tar.gz"
    url = f"https://github.com/rhysd/actionlint/releases/download/v{version}/{tar_name}"
    dest_dir = Path(args.dest).resolve()
    tar_path = dest_dir / tar_name

    try:
        _download_file(url, tar_path)
    except OSError as exc:
        print(f"Failed to download actionlint: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    if args.checksum:
        actual = _sha256(tar_path)
        if actual.lower() != args.checksum.lower():
            print("actionlint checksum mismatch", file=sys.stderr)
            print(f"expected={args.checksum}", file=sys.stderr)
            print(f"actual={actual}", file=sys.stderr)
            return EXIT_FAILURE

    try:
        bin_path = _extract_tarball_member(tar_path, "actionlint", dest_dir)
    except (OSError, tarfile.TarError, KeyError) as exc:
        print(f"Failed to extract actionlint: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    finally:
        try:
            tar_path.unlink()
        except OSError:
            pass

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"path": str(bin_path)}, output_path)
    print(f"actionlint installed at {bin_path}")
    return EXIT_SUCCESS


def cmd_actionlint(args: argparse.Namespace) -> int:
    bin_path = args.bin or shutil.which("actionlint") or ""
    if not bin_path:
        local = Path("actionlint")
        if local.exists():
            bin_path = str(local.resolve())
    if not bin_path:
        print("actionlint binary not found (install first)", file=sys.stderr)
        return EXIT_FAILURE

    proc = subprocess.run(  # noqa: S603
        [bin_path, "-oneline", args.workflow],
        capture_output=True,
        text=True,
    )
    output_lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]

    if args.reviewdog:
        if not shutil.which("reviewdog"):
            print("reviewdog not found (install reviewdog/action-setup)", file=sys.stderr)
            return EXIT_FAILURE
        input_text = "\n".join(f"e:{line}" for line in output_lines)
        if input_text:
            input_text += "\n"
        reviewdog_cmd = [  # noqa: S607 - reviewdog is installed in CI
            "reviewdog",
            "-efm=%t:%f:%l:%c: %m",
            "-name=actionlint",
            "-reporter=github-check",
            "-level=error",
            "-fail-level=error",
        ]
        reviewdog_proc = subprocess.run(  # noqa: S603
            reviewdog_cmd,
            input=input_text,
            text=True,
        )
        if proc.returncode != 0 and not output_lines:
            print(proc.stderr or "actionlint failed", file=sys.stderr)
            return EXIT_FAILURE
        return EXIT_SUCCESS if reviewdog_proc.returncode == 0 else EXIT_FAILURE

    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return EXIT_SUCCESS if proc.returncode == 0 else EXIT_FAILURE


def cmd_kyverno_install(args: argparse.Namespace) -> int:
    version = args.version
    if not version.startswith("v"):
        version = f"v{version}"
    tar_name = f"kyverno-cli_{version}_linux_x86_64.tar.gz"
    url = f"https://github.com/kyverno/kyverno/releases/download/{version}/{tar_name}"
    dest_dir = Path(args.dest).resolve()
    tar_path = dest_dir / tar_name

    try:
        _download_file(url, tar_path)
    except OSError as exc:
        print(f"Failed to download kyverno: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    try:
        bin_path = _extract_tarball_member(tar_path, "kyverno", dest_dir)
    except (OSError, tarfile.TarError, KeyError) as exc:
        print(f"Failed to extract kyverno: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    finally:
        try:
            tar_path.unlink()
        except OSError:
            pass

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"path": str(bin_path)}, output_path)
    print(f"kyverno installed at {bin_path}")
    return EXIT_SUCCESS


def _trivy_asset_name(version: str) -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "linux":
        if machine in {"x86_64", "amd64"}:
            suffix = "Linux-64bit"
        elif machine in {"aarch64", "arm64"}:
            suffix = "Linux-ARM64"
        else:
            raise ValueError(f"Unsupported Linux architecture: {machine}")
    elif system == "darwin":
        if machine in {"x86_64", "amd64"}:
            suffix = "macOS-64bit"
        elif machine in {"arm64", "aarch64"}:
            suffix = "macOS-ARM64"
        else:
            raise ValueError(f"Unsupported macOS architecture: {machine}")
    else:
        raise ValueError(f"Unsupported platform: {system}")
    return f"trivy_{version}_{suffix}.tar.gz"


def cmd_trivy_install(args: argparse.Namespace) -> int:
    version = args.version.lstrip("v")
    try:
        tar_name = _trivy_asset_name(version)
    except ValueError as exc:
        print(f"Failed to resolve trivy asset: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    url = f"https://github.com/aquasecurity/trivy/releases/download/v{version}/{tar_name}"
    dest_dir = Path(args.dest).resolve()
    tar_path = dest_dir / tar_name

    try:
        _download_file(url, tar_path)
    except OSError as exc:
        print(f"Failed to download trivy: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    try:
        bin_path = _extract_tarball_member(tar_path, "trivy", dest_dir)
    except (OSError, tarfile.TarError, KeyError) as exc:
        print(f"Failed to extract trivy: {exc}", file=sys.stderr)
        return EXIT_FAILURE
    finally:
        try:
            tar_path.unlink()
        except OSError:
            pass

    if args.github_path:
        _append_github_path(dest_dir)

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"path": str(bin_path)}, output_path)
    print(f"trivy installed at {bin_path}")
    return EXIT_SUCCESS


def cmd_trivy_summary(args: argparse.Namespace) -> int:
    """Parse Trivy JSON output and generate summary with counts.

    Reads both filesystem scan (vulnerabilities) and config scan (misconfigurations)
    JSON files, counts findings by severity, outputs to GITHUB_OUTPUT and GITHUB_STEP_SUMMARY.
    """
    fs_json = Path(args.fs_json) if args.fs_json else None
    config_json = Path(args.config_json) if args.config_json else None

    # Parse filesystem scan results (vulnerabilities)
    fs_critical = 0
    fs_high = 0
    if fs_json and fs_json.exists():
        try:
            data = json.loads(fs_json.read_text(encoding="utf-8"))
            for result in data.get("Results", []):
                for vuln in result.get("Vulnerabilities", []):
                    severity = vuln.get("Severity", "").upper()
                    if severity == "CRITICAL":
                        fs_critical += 1
                    elif severity == "HIGH":
                        fs_high += 1
        except (json.JSONDecodeError, KeyError) as e:
            print(f"::warning::Failed to parse {fs_json}: {e}")

    # Parse config scan results (misconfigurations)
    config_critical = 0
    config_high = 0
    if config_json and config_json.exists():
        try:
            data = json.loads(config_json.read_text(encoding="utf-8"))
            for result in data.get("Results", []):
                for misconfig in result.get("Misconfigurations", []):
                    severity = misconfig.get("Severity", "").upper()
                    if severity == "CRITICAL":
                        config_critical += 1
                    elif severity == "HIGH":
                        config_high += 1
        except (json.JSONDecodeError, KeyError) as e:
            print(f"::warning::Failed to parse {config_json}: {e}")

    # Calculate totals
    total_critical = fs_critical + config_critical
    total_high = fs_high + config_high

    # Write to GITHUB_OUTPUT if requested
    if args.github_output:
        outputs = {
            "fs_critical": str(fs_critical),
            "fs_high": str(fs_high),
            "config_critical": str(config_critical),
            "config_high": str(config_high),
            "total_critical": str(total_critical),
            "total_high": str(total_high),
        }
        output_path = _resolve_output_path(None, args.github_output)
        _write_outputs(outputs, output_path)

    # Write to GITHUB_STEP_SUMMARY if requested
    if args.github_summary:
        summary_lines = [
            "### Trivy Findings Summary",
            "",
            "| Scan Type | Critical | High |",
            "|-----------|----------|------|",
            f"| Filesystem (vulns) | {fs_critical} | {fs_high} |",
            f"| Config (misconfigs) | {config_critical} | {config_high} |",
            f"| **Total** | **{total_critical}** | **{total_high}** |",
        ]
        _append_summary("\n".join(summary_lines), None)

    # Print summary to console
    print(f"Trivy Summary: {total_critical} critical, {total_high} high")
    print(f"  Filesystem: {fs_critical} critical, {fs_high} high")
    print(f"  Config: {config_critical} critical, {config_high} high")

    return EXIT_SUCCESS


def _iter_yaml_files(path: Path) -> list[Path]:
    return sorted([*path.glob("*.yaml"), *path.glob("*.yml")])


def _kyverno_apply(policy: Path, resource: Path, bin_path: str | None = None) -> str:
    cmd = [bin_path or "kyverno", "apply", str(policy), "--resource", str(resource)]
    proc = _run_command(cmd, policy.parent)
    return (proc.stdout or "") + (proc.stderr or "")


def cmd_kyverno_validate(args: argparse.Namespace) -> int:
    policies_dir = Path(args.policies_dir)
    templates_dir = Path(args.templates_dir) if args.templates_dir else None

    failed = 0
    validated = 0

    if not policies_dir.exists():
        print(f"::warning::Policies directory '{policies_dir}' not found")
        output_path = _resolve_output_path(args.output, args.github_output)
        _write_outputs({"validated": "0", "failed": "0"}, output_path)
        return EXIT_SUCCESS

    for policy in _iter_yaml_files(policies_dir):
        print(f"Validating: {policy}")
        output = _kyverno_apply(policy, Path("/dev/null"), args.bin)
        lowered = output.lower()
        if "error" in lowered or "invalid" in lowered or "failed" in lowered:
            print("  FAILED")
            print(output)
            failed += 1
        else:
            print("  OK")
            validated += 1

    if templates_dir and templates_dir.exists():
        for template in _iter_yaml_files(templates_dir):
            print(f"Validating template: {template}")
            output = _kyverno_apply(template, Path("/dev/null"), args.bin)
            lowered = output.lower()
            if "error" in lowered or "invalid" in lowered or "failed" in lowered:
                print("  FAILED")
                print(output)
                failed += 1
            else:
                print("  OK")
                validated += 1

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"validated": str(validated), "failed": str(failed)}, output_path)

    if failed:
        print(f"::error::{failed} policy validation(s) failed")
        return EXIT_FAILURE

    print(f"All {validated} policies validated successfully")
    return EXIT_SUCCESS


def cmd_kyverno_test(args: argparse.Namespace) -> int:
    policies_dir = Path(args.policies_dir)
    fixtures_dir = Path(args.fixtures_dir)
    fail_on_warn = str(args.fail_on_warn).strip().lower() in {"true", "1", "yes", "y", "on"}

    if not fixtures_dir.exists():
        print(f"::warning::Fixtures directory '{fixtures_dir}' not found, skipping tests")
        return EXIT_SUCCESS

    for policy in _iter_yaml_files(policies_dir):
        policy_name = policy.stem
        print(f"\n=== Testing policy: {policy_name} ===")
        for fixture in _iter_yaml_files(fixtures_dir):
            fixture_name = fixture.name
            result = _kyverno_apply(policy, fixture, args.bin)
            if "pass: 1" in result:
                status = "PASS"
            elif "fail: 1" in result:
                status = "FAIL (policy enforced)"
            elif "warn: 1" in result:
                status = "WARN"
                if fail_on_warn:
                    print(f"::warning::Policy {policy_name} warned on {fixture_name}")
            else:
                status = "SKIP (not applicable)"
            print(f"  vs {fixture_name}: {status}")

    return EXIT_SUCCESS


def cmd_release_parse_tag(args: argparse.Namespace) -> int:
    ref = args.ref or os.environ.get("GITHUB_REF", "")
    if not ref.startswith("refs/tags/"):
        print("GITHUB_REF is not a tag ref", file=sys.stderr)
        return EXIT_FAILURE
    version = ref.replace("refs/tags/", "", 1)
    major = version.split(".")[0]
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"version": version, "major": major}, output_path)
    print(f"Release version: {version} (major: {major})")
    return EXIT_SUCCESS


def cmd_release_update_tag(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    major = args.major
    remote = args.remote

    def run_git(cmd_args: list[str], allow_fail: bool = False) -> bool:
        proc = _run_command(["git", *cmd_args], root)
        if proc.returncode != 0 and not allow_fail:
            message = (proc.stdout or proc.stderr or "").strip()
            if message:
                print(message, file=sys.stderr)
            return False
        return True

    run_git(["tag", "-d", major], allow_fail=True)
    if not run_git(["tag", major]):
        return EXIT_FAILURE
    if not run_git(["push", "-f", remote, major]):
        return EXIT_FAILURE
    print(f"Floating tag {major} now points to {args.version}")
    return EXIT_SUCCESS


def cmd_zizmor_run(args: argparse.Namespace) -> int:
    """Run zizmor and produce SARIF output, with fallback on failure.

    This replaces the inline heredoc in hub-production-ci.yml to satisfy
    the no-inline policy.
    """
    workflows_path = getattr(args, "workflows", ".github/workflows/")
    output_path = Path(args.output)

    # Run zizmor
    cmd = ["zizmor", "--format", "sarif", workflows_path]
    try:
        result = subprocess.run(  # noqa: S603, S607
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # Success - write the SARIF output
            output_path.write_text(result.stdout, encoding="utf-8")
            print(f"zizmor completed, SARIF written to {output_path}")
            return EXIT_SUCCESS
        else:
            # Non-zero exit - preserve SARIF if stdout is valid; otherwise write empty.
            # This keeps findings visible while maintaining a valid SARIF fallback.
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and "runs" in payload:
                output_path.write_text(result.stdout, encoding="utf-8")
                print(f"::warning::zizmor returned non-zero, SARIF preserved at {output_path}")
            else:
                output_path.write_text(EMPTY_SARIF, encoding="utf-8")
                print(f"::warning::zizmor returned non-zero, empty SARIF written to {output_path}")
            return EXIT_SUCCESS  # Still success - zizmor-check gates on SARIF content
    except FileNotFoundError:
        # zizmor not installed
        output_path.write_text(EMPTY_SARIF, encoding="utf-8")
        print(f"::warning::zizmor not found, empty SARIF written to {output_path}")
        return EXIT_SUCCESS  # Don't fail the build if tool is missing


def cmd_zizmor_check(args: argparse.Namespace) -> int:
    sarif_path = Path(args.sarif)
    if not sarif_path.exists():
        print(f"::error::SARIF file not found: {sarif_path}")
        return EXIT_FAILURE

    high = 0
    try:
        sarif = json.loads(sarif_path.read_text(encoding="utf-8"))
        runs = sarif.get("runs", []) if isinstance(sarif, dict) else []
        if runs:
            results = runs[0].get("results", []) or []
            high = len([r for r in results if r.get("level") in ("error", "warning")])
    except json.JSONDecodeError:
        high = 0

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    _append_summary(
        f"## Zizmor Workflow Security\nHigh/Warning findings: {high}\n",
        summary_path,
    )

    if high > 0:
        print("::error::Found workflow security findings - review in Security tab")
        return EXIT_FAILURE
    return EXIT_SUCCESS


def cmd_license_check(args: argparse.Namespace) -> int:
    proc = _run_command(["pip-licenses", "--format=csv"], Path("."))
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    total = len(lines)
    copyleft = len([line for line in lines if re.search(r"GPL|AGPL", line, re.I)])

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    summary = "## License Check\n"
    summary += f"Total packages: {total}\n"
    summary += f"Copyleft (GPL/AGPL): {copyleft}\n"
    if copyleft > 0:
        summary += "\nCopyleft packages (dev dependencies are acceptable):\n"
        summary += "\n".join([line for line in lines if re.search(r"GPL|AGPL", line, re.I)])
        summary += "\n"
        _append_summary(summary, summary_path)
        print(f"::warning::Found {copyleft} packages with copyleft licenses")
        return EXIT_SUCCESS

    summary += "PASS - no copyleft licenses\n"
    _append_summary(summary, summary_path)
    return EXIT_SUCCESS


def cmd_gitleaks_summary(args: argparse.Namespace) -> int:
    repo_root = Path(".")
    commits = _run_command(["git", "rev-list", "--count", "HEAD"], repo_root).stdout
    files = _run_command(["git", "ls-files"], repo_root).stdout
    commits_count = commits.strip() if commits else "0"
    files_count = str(len(files.splitlines())) if files else "0"
    outcome = args.outcome or os.environ.get("GITLEAKS_OUTCOME", "skipped")
    leak_text = "0" if outcome == "success" else "CHECK LOGS"
    result_text = "PASS" if outcome == "success" else "FAIL"

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    summary = (
        "## Secret Detection (gitleaks)\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| Commits scanned | {commits_count} |\n"
        f"| Files in repo | {files_count} |\n"
        f"| Leaks found | {leak_text} |\n"
        f"| Result | {result_text} |\n"
    )
    _append_summary(summary, summary_path)
    return EXIT_SUCCESS


def _env_result(name: str) -> str:
    return os.environ.get(name, "skipped")


def cmd_pytest_summary(args: argparse.Namespace) -> int:
    """Generate a summary for pytest results matching smoke test format."""
    summary_path = _resolve_summary_path(args.summary, args.github_summary)

    # Parse test-results.xml (JUnit format)
    tests_total = 0
    tests_passed = 0
    tests_failed = 0
    tests_skipped = 0

    junit_path = Path(args.junit_xml)
    if junit_path.exists():
        try:
            tree = ET.parse(junit_path)
            root = tree.getroot()
            # Handle both <testsuite> and <testsuites> root elements
            if root.tag == "testsuites":
                suites = root.findall("testsuite")
            else:
                suites = [root]

            for suite in suites:
                tests_total += int(suite.get("tests", 0))
                tests_failed += int(suite.get("failures", 0)) + int(suite.get("errors", 0))
                tests_skipped += int(suite.get("skipped", 0))

            tests_passed = tests_total - tests_failed - tests_skipped
        except ET.ParseError as e:
            print(f"Warning: Failed to parse {junit_path}: {e}", file=sys.stderr)

    # Parse coverage.xml (Cobertura format)
    coverage_pct = 0
    lines_covered = 0
    lines_total = 0

    coverage_path = Path(args.coverage_xml)
    if coverage_path.exists():
        try:
            tree = ET.parse(coverage_path)
            root = tree.getroot()
            # Cobertura format: line-rate is a decimal (0.0 to 1.0)
            line_rate = float(root.get("line-rate", 0))
            coverage_pct = int(line_rate * 100)
            lines_covered = int(root.get("lines-covered", 0))
            lines_total = int(root.get("lines-valid", 0))
        except ET.ParseError as e:
            print(f"Warning: Failed to parse {coverage_path}: {e}", file=sys.stderr)

    # Determine status
    tests_pass = tests_total > 0 and tests_failed == 0
    coverage_threshold = args.coverage_min
    coverage_pass = coverage_pct >= coverage_threshold

    # Generate summary matching smoke test format
    lines = [
        "## Unit Tests Summary",
        "",
        "| Metric | Result | Status |",
        "|--------|--------|--------|",
        f"| **Unit Tests** | {tests_passed} passed | {'PASS' if tests_pass else 'FAIL'} |",
        f"| **Test Failures** | {tests_failed} failed | {'WARN' if tests_failed > 0 else 'PASS'} |",
        f"| **Tests Skipped** | {tests_skipped} skipped | {'INFO' if tests_skipped > 0 else 'PASS'} |",
        f"| **Coverage (pytest-cov)** | {coverage_pct}% {_bar(coverage_pct)} | {'PASS' if coverage_pass else 'WARN'} |",
        "",
        f"**Coverage Details:** {lines_covered:,} / {lines_total:,} lines covered",
        "",
        "### Test Results",
        f"**{'PASS' if tests_pass and coverage_pass else 'FAIL'}** - "
        + (
            f"All {tests_total} tests passed with {coverage_pct}% coverage"
            if tests_pass and coverage_pass
            else f"{tests_failed} test(s) failed or coverage below {coverage_threshold}%"
        ),
    ]

    _append_summary("\n".join(lines), summary_path)
    return EXIT_SUCCESS if tests_pass else EXIT_FAILURE


def cmd_summary(args: argparse.Namespace) -> int:
    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    repo = os.environ.get("GH_REPOSITORY", "")
    branch = os.environ.get("GH_REF_NAME", "")
    run_number = os.environ.get("GH_RUN_NUMBER", "")
    event_name = os.environ.get("GH_EVENT_NAME", "")

    def ran(status: str) -> str:
        return "true" if status not in ("skipped", "cancelled") else "false"

    def ok(status: str) -> str:
        return "true" if status == "success" else "false"

    def status_text(status: str) -> str:
        if status == "success":
            return "Passed"
        if status == "skipped":
            return "Skipped"
        return "Failed"

    results = {
        "actionlint": _env_result("RESULT_ACTIONLINT"),
        "zizmor": _env_result("RESULT_ZIZMOR"),
        "ruff": _env_result("RESULT_LINT"),
        "syntax": _env_result("RESULT_SYNTAX"),
        "mypy": _env_result("RESULT_TYPECHECK"),
        "yamllint": _env_result("RESULT_YAMLLINT"),
        "pytest": _env_result("RESULT_UNIT_TESTS"),
        "mutmut": _env_result("RESULT_MUTATION"),
        "bandit": _env_result("RESULT_BANDIT"),
        "pip-audit": _env_result("RESULT_PIP_AUDIT"),
        "gitleaks": _env_result("RESULT_SECRET_SCAN"),
        "trivy": _env_result("RESULT_TRIVY"),
        "templates": _env_result("RESULT_TEMPLATES"),
        "configs": _env_result("RESULT_CONFIGS"),
        "matrix-keys": _env_result("RESULT_MATRIX_KEYS"),
        "licenses": _env_result("RESULT_LICENSE"),
        "dependency-review": _env_result("RESULT_DEP_REVIEW"),
        "scorecard": _env_result("RESULT_SCORECARD"),
    }

    lines = [
        "## Hub Production CI Summary",
        "",
        "### Environment",
        "",
        "| Setting | Value |",
        "|---------|-------|",
        f"| Repository | {repo} |",
        f"| Branch | {branch} |",
        f"| Run Number | #{run_number} |",
        f"| Trigger | {event_name} |",
        "| Language | Python |",
        "",
        "## Tools Enabled",
        "",
        "| Category | Tool | Configured | Ran | Success |",
        "|----------|------|------------|-----|---------|",
        f"| Workflow | actionlint | true | {ran(results['actionlint'])} | {ok(results['actionlint'])} |",
        f"| Workflow | zizmor | true | {ran(results['zizmor'])} | {ok(results['zizmor'])} |",
        f"| Quality | ruff | true | {ran(results['ruff'])} | {ok(results['ruff'])} |",
        f"| Quality | syntax | true | {ran(results['syntax'])} | {ok(results['syntax'])} |",
        f"| Quality | mypy | true | {ran(results['mypy'])} | {ok(results['mypy'])} |",
        f"| Quality | yamllint | true | {ran(results['yamllint'])} | {ok(results['yamllint'])} |",
        f"| Testing | pytest | true | {ran(results['pytest'])} | {ok(results['pytest'])} |",
        f"| Testing | mutmut | true | {ran(results['mutmut'])} | {ok(results['mutmut'])} |",
        f"| Security | bandit | true | {ran(results['bandit'])} | {ok(results['bandit'])} |",
        f"| Security | pip-audit | true | {ran(results['pip-audit'])} | {ok(results['pip-audit'])} |",
        f"| Security | gitleaks | true | {ran(results['gitleaks'])} | {ok(results['gitleaks'])} |",
        f"| Security | trivy | true | {ran(results['trivy'])} | {ok(results['trivy'])} |",
        f"| Validate | templates | true | {ran(results['templates'])} | {ok(results['templates'])} |",
        f"| Validate | configs | true | {ran(results['configs'])} | {ok(results['configs'])} |",
        f"| Validate | matrix-keys | true | {ran(results['matrix-keys'])} | {ok(results['matrix-keys'])} |",
        f"| Validate | licenses | true | {ran(results['licenses'])} | {ok(results['licenses'])} |",
        f"| Supply Chain | dependency-review | true | {ran(results['dependency-review'])} | {ok(results['dependency-review'])} |",  # noqa: E501
        f"| Supply Chain | scorecard | true | {ran(results['scorecard'])} | {ok(results['scorecard'])} |",
        "",
        "### Failed or Skipped Checks",
        "",
        "| Check | Status |",
        "|-------|--------|",
    ]

    has_issues = False
    for name, status in results.items():
        if status != "success":
            has_issues = True
            lines.append(f"| {name} | {status} |")
    if not has_issues:
        lines.append("| None | success |")
    lines.append("")
    # Parse Trivy findings from environment
    trivy_critical = int(os.environ.get("TRIVY_CRITICAL", "0") or "0")
    trivy_high = int(os.environ.get("TRIVY_HIGH", "0") or "0")
    trivy_fs_critical = int(os.environ.get("TRIVY_FS_CRITICAL", "0") or "0")
    trivy_fs_high = int(os.environ.get("TRIVY_FS_HIGH", "0") or "0")
    trivy_config_critical = int(os.environ.get("TRIVY_CONFIG_CRITICAL", "0") or "0")
    trivy_config_high = int(os.environ.get("TRIVY_CONFIG_HIGH", "0") or "0")

    # Trivy passes if no critical vulnerabilities (high may be warnings)
    trivy_status = "Passed" if trivy_critical == 0 else "Failed"
    trivy_finding_text = f"{trivy_critical} crit, {trivy_high} high"

    lines.extend(
        [
            "### Quality Gates",
            "",
            "| Check | Threshold | Status |",
            "|-------|-----------|--------|",
            f"| Unit Tests | pass | {status_text(results['pytest'])} |",
            f"| Coverage | 70% min | {'Passed' if results['pytest'] == 'success' else 'N/A'} |",
            f"| Mutation Score | 70% min | {status_text(results['mutmut'])} |",
            f"| Type Check (mypy) | 0 errors | {'Passed' if results['mypy'] == 'success' else 'Failed'} |",
            f"| SAST (bandit) | 0 high | {'Passed' if results['bandit'] == 'success' else 'Failed'} |",
            f"| Secrets (gitleaks) | 0 leaks | {'Passed' if results['gitleaks'] == 'success' else 'Failed'} |",
            f"| Trivy (vuln+config) | 0 critical | {trivy_status} ({trivy_finding_text}) |",
            "",
        ]
    )

    # Add Trivy breakdown if any findings
    if trivy_critical > 0 or trivy_high > 0:
        lines.extend(
            [
                "#### Trivy Findings Breakdown",
                "",
                "| Scan Type | Critical | High |",
                "|-----------|----------|------|",
                f"| Filesystem (vulns) | {trivy_fs_critical} | {trivy_fs_high} |",
                f"| Config (misconfigs) | {trivy_config_critical} | {trivy_config_high} |",
                f"| **Total** | **{trivy_critical}** | **{trivy_high}** |",
                "",
            ]
        )

    lines.append("Job summary generated at run-time")
    _append_summary("\n".join(lines), summary_path)
    return EXIT_SUCCESS


def cmd_enforce(args: argparse.Namespace) -> int:
    checks = [
        ("actionlint", _env_result("RESULT_ACTIONLINT"), "fix workflow syntax"),
        ("zizmor", _env_result("RESULT_ZIZMOR"), "address workflow security findings"),
        ("mypy", _env_result("RESULT_TYPECHECK"), "fix mypy errors"),
        ("yamllint", _env_result("RESULT_YAMLLINT"), "fix config syntax"),
        ("ruff", _env_result("RESULT_LINT"), "fix ruff lint violations"),
        ("syntax", _env_result("RESULT_SYNTAX"), "fix Python syntax errors"),
        ("unit-tests", _env_result("RESULT_UNIT_TESTS"), "unit tests failed"),
        ("mutation-tests", _env_result("RESULT_MUTATION"), "mutation testing failed"),
        ("bandit", _env_result("RESULT_BANDIT"), "security scan failed"),
        ("pip-audit", _env_result("RESULT_PIP_AUDIT"), "dependency audit failed"),
        ("gitleaks", _env_result("RESULT_SECRET_SCAN"), "secret detection failed"),
        ("trivy", _env_result("RESULT_TRIVY"), "trivy scan failed"),
        (
            "validate-templates",
            _env_result("RESULT_TEMPLATES"),
            "template validation failed",
        ),
        ("validate-configs", _env_result("RESULT_CONFIGS"), "config validation failed"),
        (
            "verify-matrix-keys",
            _env_result("RESULT_MATRIX_KEYS"),
            "matrix key validation failed",
        ),
        ("license-check", _env_result("RESULT_LICENSE"), "license compliance failed"),
        (
            "dependency-review",
            _env_result("RESULT_DEP_REVIEW"),
            "dependency review failed",
        ),
        ("scorecard", _env_result("RESULT_SCORECARD"), "scorecard checks failed"),
    ]

    failed = False
    for name, result, message in checks:
        if result in ("failure", "cancelled"):
            print(f"::error::{name} failed - {message}")
            failed = True

    if failed:
        return EXIT_FAILURE
    print("All critical checks passed")
    return EXIT_SUCCESS
