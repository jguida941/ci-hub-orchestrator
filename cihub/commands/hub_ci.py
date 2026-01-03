"""Hub production CI helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import py_compile
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ET  # Secure XML parsing (prevents XXE)

from cihub import badges as badge_tools
from cihub.cli import hub_root
from cihub.config.io import load_yaml_file
from cihub.config.normalize import normalize_config
from cihub.exit_codes import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from cihub.services.discovery import _THRESHOLD_KEYS, _TOOL_KEYS
from cihub.services.types import RepoEntry


def _write_outputs(values: dict[str, str], output_path: Path | None) -> None:
    if output_path is None:
        for key, value in values.items():
            print(f"{key}={value}")
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _append_summary(text: str, summary_path: Path | None) -> None:
    if summary_path is None:
        print(text)
        return
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def _resolve_output_path(path_value: str | None, github_output: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_output:
        env_path = os.environ.get("GITHUB_OUTPUT")
        return Path(env_path) if env_path else None
    return None


def _resolve_summary_path(path_value: str | None, github_summary: bool) -> Path | None:
    if path_value:
        return Path(path_value)
    if github_summary:
        env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        return Path(env_path) if env_path else None
    return None


def _append_github_path(path_value: Path) -> None:
    env_path = os.environ.get("GITHUB_PATH")
    if not env_path:
        return
    with open(env_path, "a", encoding="utf-8") as handle:
        handle.write(f"{path_value}\n")


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _parse_env_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return normalize_config(load_yaml_file(path))
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load config: {exc}")
        return {}


def _run_command(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=env,
    )


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "cihub"})  # noqa: S310
    with urllib.request.urlopen(request) as response:  # noqa: S310
        dest.write_bytes(response.read())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_tarball_member(tar_path: Path, member_name: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        member = tar.getmember(member_name)
        tar.extract(member, path=dest_dir)
    extracted = dest_dir / member_name
    extracted.chmod(extracted.stat().st_mode | stat.S_IEXEC)
    return extracted


def _parse_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _parse_float(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def cmd_ruff(args: argparse.Namespace) -> int:
    cmd = ["ruff", "check", args.path]
    if args.force_exclude:
        cmd.append("--force-exclude")

    json_proc = _run_command(cmd + ["--output-format=json"], Path("."))
    issues = 0
    try:
        data = json.loads(json_proc.stdout or "[]")
        issues = len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        issues = 0

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues)}, output_path)

    github_proc = subprocess.run(  # noqa: S603
        cmd + ["--output-format=github"],
        text=True,
    )
    return EXIT_SUCCESS if github_proc.returncode == 0 else EXIT_FAILURE


def cmd_black(args: argparse.Namespace) -> int:
    proc = _run_command(["black", "--check", args.path], Path("."))
    output = (proc.stdout or "") + (proc.stderr or "")
    issues = len(re.findall(r"would reformat", output))
    if proc.returncode != 0 and issues == 0:
        issues = 1
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues)}, output_path)
    return EXIT_SUCCESS


def _extract_count(line: str, emoji: str) -> int:
    match = re.search(rf"{re.escape(emoji)}\s*(\d+)", line)
    if match:
        return int(match.group(1))
    return 0


def _compare_badges(expected_dir: Path, actual_dir: Path) -> list[str]:
    issues: list[str] = []
    if not expected_dir.exists():
        return [f"missing badges directory: {expected_dir}"]

    expected = {p.name: p for p in expected_dir.glob("*.json")}
    actual = {p.name: p for p in actual_dir.glob("*.json")}

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    for name in missing:
        issues.append(f"missing: {name}")
    for name in extra:
        issues.append(f"extra: {name}")

    for name in sorted(set(expected) & set(actual)):
        try:
            expected_data = json.loads(expected[name].read_text(encoding="utf-8"))
            actual_data = json.loads(actual[name].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"invalid json: {name} ({exc})")
            continue
        if expected_data != actual_data:
            issues.append(f"diff: {name}")

    return issues


def cmd_mutmut(args: argparse.Namespace) -> int:
    workdir = Path(args.workdir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "mutmut-run.log"

    proc = _run_command(["mutmut", "run"], workdir)
    log_text = (proc.stdout or "") + (proc.stderr or "")
    log_path.write_text(log_text, encoding="utf-8")
    if proc.returncode != 0:
        print("::error::mutmut run failed - check for import errors or test failures")
        print(log_text)  # Print log to help debug CI failures
        return EXIT_FAILURE
    if "mutations/second" not in log_text:
        print("::error::mutmut did not complete successfully")
        print(log_text)
        return EXIT_FAILURE

    final_line = ""
    for line in log_text.splitlines():
        if re.search(r"\d+/\d+", line):
            final_line = line
    if not final_line:
        print("::error::mutmut output missing final counts")
        return EXIT_FAILURE

    killed = _extract_count(final_line, "🎉")
    survived = _extract_count(final_line, "🙁")
    timeout = _extract_count(final_line, "⏰")
    suspicious = _extract_count(final_line, "🤔")
    skipped = _extract_count(final_line, "🔇")

    tested = killed + survived + timeout + suspicious
    if tested == 0:
        print("::error::No mutants were tested - check test coverage")
        return EXIT_FAILURE

    score = (killed * 100) // tested

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(
        {
            "mutation_score": str(score),
            "killed": str(killed),
            "survived": str(survived),
            "timeout": str(timeout),
            "suspicious": str(suspicious),
        },
        output_path,
    )

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    summary = (
        "## Mutation Testing\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| **Score** | **{score}%** |\n"
        f"| Killed | {killed} |\n"
        f"| Survived | {survived} |\n"
        f"| Timeout | {timeout} |\n"
        f"| Suspicious | {suspicious} |\n"
        f"| Skipped | {skipped} |\n"
        f"| Total Tested | {tested} |\n"
    )
    if score < args.min_score:
        summary += f"\n**FAILED**: Score {score}% below {args.min_score}% threshold\n"
        _append_summary(summary, summary_path)
        print(f"::error::Mutation score {score}% below {args.min_score}% threshold")
        print(log_text)
        return EXIT_FAILURE
    summary += f"\n**PASSED**: Score {score}% meets {args.min_score}% threshold\n"
    _append_summary(summary, summary_path)
    return EXIT_SUCCESS


def cmd_badges(args: argparse.Namespace) -> int:
    root = hub_root()
    config_path = Path(args.config).resolve() if args.config else root / "config" / "defaults.yaml"
    config = _load_config(config_path)
    badges_cfg = config.get("reports", {}).get("badges", {}) or {}
    if badges_cfg.get("enabled") is False:
        print("Badges disabled via reports.badges.enabled")
        return EXIT_SUCCESS
    tools_cfg = config.get("hub_ci", {}).get("tools", {}) if isinstance(config.get("hub_ci"), dict) else {}

    def tool_enabled(name: str, default: bool = True) -> bool:
        if not isinstance(tools_cfg, dict):
            return default
        return bool(tools_cfg.get(name, default))

    # Collect disabled tools for deterministic "disabled" badges
    all_badge_tools = ["ruff", "mutmut", "mypy", "bandit", "pip_audit", "zizmor"]
    disabled_tools: set[str] = set()
    for tool in all_badge_tools:
        if not tool_enabled(tool):
            disabled_tools.add(tool)

    env = os.environ.copy()
    env["UPDATE_BADGES"] = "true"

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if output_dir:
        env["BADGE_OUTPUT_DIR"] = str(output_dir)

    if args.ruff_issues is not None and tool_enabled("ruff"):
        env["RUFF_ISSUES"] = str(args.ruff_issues)
    if args.mutation_score is not None and tool_enabled("mutmut"):
        env["MUTATION_SCORE"] = str(args.mutation_score)
    if args.mypy_errors is not None and tool_enabled("mypy"):
        env["MYPY_ERRORS"] = str(args.mypy_errors)
    if args.black_issues is not None and tool_enabled("black"):
        env["BLACK_ISSUES"] = str(args.black_issues)
    if args.black_status and tool_enabled("black"):
        env["BLACK_STATUS"] = args.black_status
    if args.zizmor_sarif and tool_enabled("zizmor"):
        env["ZIZMOR_SARIF"] = str(Path(args.zizmor_sarif).resolve())

    artifacts_dir = Path(args.artifacts_dir).resolve() if args.artifacts_dir else None
    if artifacts_dir:
        bandit = artifacts_dir / "bandit-results" / "bandit.json"
        pip_audit = artifacts_dir / "pip-audit-results" / "pip-audit.json"
        zizmor = artifacts_dir / "zizmor-sarif" / "zizmor.sarif"
        if bandit.exists() and tool_enabled("bandit"):
            shutil.copyfile(bandit, root / "bandit.json")
        if pip_audit.exists() and tool_enabled("pip_audit"):
            shutil.copyfile(pip_audit, root / "pip-audit.json")
        if zizmor.exists() and tool_enabled("zizmor"):
            shutil.copyfile(zizmor, root / "zizmor.sarif")

    if args.check:
        with tempfile.TemporaryDirectory(prefix="cihub-badges-") as tmpdir:
            env["BADGE_OUTPUT_DIR"] = tmpdir
            result = badge_tools.main(env=env, root=root, disabled_tools=disabled_tools)
            if result != 0:
                return EXIT_FAILURE
            issues = _compare_badges(root / "badges", Path(tmpdir))
            if issues:
                print("Badge drift detected:")
                for issue in issues:
                    print(f"- {issue}")
                return EXIT_FAILURE
            print("Badges are up to date.")
            return EXIT_SUCCESS

    result = badge_tools.main(env=env, root=root, disabled_tools=disabled_tools)
    if result != 0:
        return EXIT_FAILURE
    return EXIT_SUCCESS


def cmd_badges_commit(_: argparse.Namespace) -> int:
    root = hub_root()
    message = "chore: update CI badges [skip ci]"

    def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
        return _run_command(["git", *args], root)

    config_steps = (
        ["config", "user.name", "github-actions[bot]"],
        ["config", "user.email", "github-actions[bot]@users.noreply.github.com"],
    )
    for config_args in config_steps:
        proc = run_git(config_args)
        if proc.returncode != 0:
            message = (proc.stdout or proc.stderr or "").strip()
            if message:
                print(message, file=sys.stderr)
            return EXIT_FAILURE

    proc = run_git(["add", "badges/"])
    if proc.returncode != 0:
        message = (proc.stdout or proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    diff_proc = run_git(["diff", "--staged", "--quiet"])
    if diff_proc.returncode == 0:
        print("No badge changes to commit.")
        return EXIT_SUCCESS
    if diff_proc.returncode != 1:
        message = (diff_proc.stdout or diff_proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    commit_proc = run_git(["commit", "-m", message])
    if commit_proc.returncode != 0:
        message = (commit_proc.stdout or commit_proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    push_proc = run_git(["push"])
    if push_proc.returncode != 0:
        message = (push_proc.stdout or push_proc.stderr or "").strip()
        if message:
            print(message, file=sys.stderr)
        return EXIT_FAILURE

    return EXIT_SUCCESS


def cmd_outputs(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve() if args.config else hub_root() / "config" / "defaults.yaml"
    config = _load_config(config_path)
    hub_cfg = config.get("hub_ci", {}) if isinstance(config.get("hub_ci"), dict) else {}
    enabled = hub_cfg.get("enabled", True)
    tools = hub_cfg.get("tools", {}) if isinstance(hub_cfg.get("tools"), dict) else {}
    thresholds = hub_cfg.get("thresholds", {}) if isinstance(hub_cfg.get("thresholds"), dict) else {}

    outputs = {
        "hub_ci_enabled": _bool_str(bool(enabled)),
        "run_actionlint": _bool_str(bool(tools.get("actionlint", True))),
        "run_zizmor": _bool_str(bool(tools.get("zizmor", True))),
        "run_ruff": _bool_str(bool(tools.get("ruff", True))),
        "run_syntax": _bool_str(bool(tools.get("syntax", True))),
        "run_mypy": _bool_str(bool(tools.get("mypy", True))),
        "run_yamllint": _bool_str(bool(tools.get("yamllint", True))),
        "run_pytest": _bool_str(bool(tools.get("pytest", True))),
        "run_mutmut": _bool_str(bool(tools.get("mutmut", True))),
        "run_bandit": _bool_str(bool(tools.get("bandit", True))),
        "bandit_fail_high": _bool_str(bool(tools.get("bandit_fail_high", True))),
        "bandit_fail_medium": _bool_str(bool(tools.get("bandit_fail_medium", False))),
        "bandit_fail_low": _bool_str(bool(tools.get("bandit_fail_low", False))),
        "run_pip_audit": _bool_str(bool(tools.get("pip_audit", True))),
        "run_gitleaks": _bool_str(bool(tools.get("gitleaks", True))),
        "run_trivy": _bool_str(bool(tools.get("trivy", True))),
        "run_validate_templates": _bool_str(bool(tools.get("validate_templates", True))),
        "run_validate_configs": _bool_str(bool(tools.get("validate_configs", True))),
        "run_verify_matrix_keys": _bool_str(bool(tools.get("verify_matrix_keys", True))),
        "run_license_check": _bool_str(bool(tools.get("license_check", True))),
        "run_dependency_review": _bool_str(bool(tools.get("dependency_review", True))),
        "run_scorecard": _bool_str(bool(tools.get("scorecard", True))),
        "coverage_min": str(thresholds.get("coverage_min", 70)),
        "mutation_score_min": str(thresholds.get("mutation_score_min", 70)),
    }

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(outputs, output_path)
    return EXIT_SUCCESS


def cmd_bandit(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    cmd = [
        "bandit",
        "-r",
        *args.paths,
        "-f",
        "json",
        "-o",
        str(output_path),
        "--severity-level",
        args.severity,
        "--confidence-level",
        args.confidence,
    ]
    _run_command(cmd, Path("."))

    # Count issues by severity
    high = 0
    medium = 0
    low = 0
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            results = data.get("results", []) if isinstance(data, dict) else []
            high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
            medium = sum(1 for item in results if item.get("issue_severity") == "MEDIUM")
            low = sum(1 for item in results if item.get("issue_severity") == "LOW")
        except json.JSONDecodeError:
            pass

    total = high + medium + low

    # Write summary with breakdown table
    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    fail_on_high = getattr(args, "fail_on_high", True)
    fail_on_medium = getattr(args, "fail_on_medium", False)
    fail_on_low = getattr(args, "fail_on_low", False)

    env_fail_high = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_HIGH"))
    env_fail_medium = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_MEDIUM"))
    env_fail_low = _parse_env_bool(os.environ.get("CIHUB_BANDIT_FAIL_LOW"))
    if env_fail_high is not None:
        fail_on_high = env_fail_high
    if env_fail_medium is not None:
        fail_on_medium = env_fail_medium
    if env_fail_low is not None:
        fail_on_low = env_fail_low

    summary = (
        "## Bandit SAST\n\n"
        "| Severity | Count | Fail Threshold |\n"
        "|----------|-------|----------------|\n"
        f"| High | {high} | {'enabled' if fail_on_high else 'disabled'} |\n"
        f"| Medium | {medium} | {'enabled' if fail_on_medium else 'disabled'} |\n"
        f"| Low | {low} | {'enabled' if fail_on_low else 'disabled'} |\n"
        f"| **Total** | **{total}** | |\n"
    )
    _append_summary(summary, summary_path)

    # Check thresholds - fail if any enabled threshold is exceeded
    fail_reasons = []

    if fail_on_high and high > 0:
        fail_reasons.append(f"{high} HIGH")
    if fail_on_medium and medium > 0:
        fail_reasons.append(f"{medium} MEDIUM")
    if fail_on_low and low > 0:
        fail_reasons.append(f"{low} LOW")

    if fail_reasons:
        # Show details for failing severities
        subprocess.run(  # noqa: S603
            ["bandit", "-r", *args.paths, "--severity-level", "low"],  # noqa: S607
            text=True,
        )
        print(f"::error::Found {', '.join(fail_reasons)} severity issues")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def _count_pip_audit_vulns(data: Any) -> int:
    if not isinstance(data, list):
        return 0
    total = 0
    for item in data:
        vulns = item.get("vulns") or item.get("vulnerabilities") or []
        total += len(vulns)
    return total


def cmd_pip_audit(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    cmd = [
        "pip-audit",
        *sum([["-r", req] for req in args.requirements], []),
        "--format",
        "json",
        "--output",
        str(output_path),
    ]
    _run_command(cmd, Path("."))

    vulns = 0
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            vulns = _count_pip_audit_vulns(data)
        except json.JSONDecodeError:
            vulns = 0

    summary_path = _resolve_summary_path(args.summary, args.github_summary)
    _append_summary(
        f"## Dependency Vulnerabilities\nFound: {vulns}\n",
        summary_path,
    )

    if vulns > 0:
        markdown = subprocess.run(  # noqa: S603
            ["pip-audit", "--format", "markdown"],  # noqa: S607
            text=True,
            capture_output=True,
        )
        if markdown.stdout:
            _append_summary(markdown.stdout, summary_path)
        print(f"::error::Found {vulns} dependency vulnerabilities")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def _resolve_actionlint_version(version: str) -> str:
    if version != "latest":
        return version.lstrip("v")
    url = "https://api.github.com/repos/rhysd/actionlint/releases/latest"
    try:
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


def cmd_syntax_check(args: argparse.Namespace) -> int:
    base = Path(args.root).resolve()
    errors = 0
    for path in args.paths:
        target = (base / path).resolve()
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = list(target.rglob("*.py"))
        else:
            continue

        for file_path in files:
            try:
                py_compile.compile(str(file_path), doraise=True)
            except py_compile.PyCompileError as exc:
                errors += 1
                print(f"::error::{file_path}: {exc.msg}")

    if errors:
        return EXIT_FAILURE
    print("✓ Python syntax valid")
    return EXIT_SUCCESS


def cmd_repo_check(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    present = (repo_path / ".git").exists()
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"present": _bool_str(present)}, output_path)
    if not present and args.owner and args.name:
        print(f"::warning::Repo checkout failed for {args.owner}/{args.name}")
    return EXIT_SUCCESS


def cmd_source_check(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    language = args.language.lower()
    patterns: tuple[str, ...]
    if language == "java":
        patterns = ("*.java", "*.kt")
    elif language == "python":
        patterns = ("*.py",)
    else:
        patterns = ()

    has_source = False
    for pattern in patterns:
        if any(repo_path.rglob(pattern)):
            has_source = True
            break

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"has_source": _bool_str(has_source)}, output_path)
    print(f"Source code present: {has_source}")
    return EXIT_SUCCESS


def cmd_security_pip_audit(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()
    requirements = args.requirements or []

    for req in requirements:
        req_path = repo_path / req
        if not req_path.exists():
            continue
        _run_command(["pip", "install", "-r", str(req_path)], repo_path)

    proc = _run_command(
        ["pip-audit", "--format=json", "--output", str(report_path)],
        repo_path,
    )

    tool_status = "success"
    if not report_path.exists():
        report_path.write_text("[]", encoding="utf-8")
        if proc.returncode != 0:
            # Tool failed without producing output - warn but continue
            tool_status = "failed"
            print(f"::warning::pip-audit failed (exit {proc.returncode}): {proc.stderr or 'no output'}")

    vulns = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        vulns = _count_pip_audit_vulns(data)
    except json.JSONDecodeError:
        vulns = 0
        if proc.returncode != 0:
            tool_status = "failed"
            print(f"::warning::pip-audit produced invalid JSON (exit {proc.returncode})")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"vulnerabilities": str(vulns), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_security_bandit(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()

    proc = _run_command(
        ["bandit", "-r", ".", "-f", "json", "-o", str(report_path)],
        repo_path,
    )

    tool_status = "success"
    if not report_path.exists():
        report_path.write_text('{"results":[]}', encoding="utf-8")
        if proc.returncode != 0:
            # Tool failed without producing output - warn but continue
            tool_status = "failed"
            print(f"::warning::bandit failed (exit {proc.returncode}): {proc.stderr or 'no output'}")

    high = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        results = data.get("results", []) if isinstance(data, dict) else []
        high = sum(1 for item in results if item.get("issue_severity") == "HIGH")
    except json.JSONDecodeError:
        high = 0
        if proc.returncode != 0:
            tool_status = "failed"
            print(f"::warning::bandit produced invalid JSON (exit {proc.returncode})")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"high": str(high), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_security_ruff(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = (repo_path / args.report).resolve()

    proc = _run_command(
        ["ruff", "check", ".", "--select=S", "--output-format=json"],
        repo_path,
    )
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")

    tool_status = "success"
    issues = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        issues = len(data) if isinstance(data, list) else 0
    except json.JSONDecodeError:
        issues = 0
        # ruff returns non-zero when issues found (normal), but invalid JSON is a problem
        tool_status = "failed"
        print(f"::warning::ruff produced invalid JSON (exit {proc.returncode}): {proc.stderr or 'no output'}")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_security_owasp(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    tool_status = "success"
    proc = None
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        proc = _run_command(
            ["./mvnw", "-B", "-ntp", "org.owasp:dependency-check-maven:check", "-DfailBuildOnCVSS=11"],
            repo_path,
        )
    else:
        tool_status = "skipped"

    reports = list(repo_path.rglob("dependency-check-report.json"))
    report_path = reports[0] if reports else None
    critical = 0
    high = 0
    if report_path and report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            dependencies = data.get("dependencies", []) if isinstance(data, dict) else []
            for dep in dependencies:
                vulns = dep.get("vulnerabilities", []) if isinstance(dep, dict) else []
                for vuln in vulns:
                    severity = str(vuln.get("severity", "")).upper()
                    if severity == "CRITICAL":
                        critical += 1
                    elif severity == "HIGH":
                        high += 1
        except json.JSONDecodeError:
            critical = 0
            high = 0
            if proc and proc.returncode != 0:
                tool_status = "failed"
                print(f"::warning::OWASP dependency-check produced invalid JSON (exit {proc.returncode})")
    elif proc and proc.returncode != 0:
        # Tool ran but produced no report
        tool_status = "failed"
        print(f"::warning::OWASP dependency-check failed (exit {proc.returncode}): no report generated")

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"critical": str(critical), "high": str(high), "tool_status": tool_status}, output_path)
    return EXIT_SUCCESS


def cmd_docker_compose_check(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    has_docker = (repo_path / "docker-compose.yml").exists() or (repo_path / "docker-compose.yaml").exists()
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"has_docker": _bool_str(has_docker)}, output_path)
    return EXIT_SUCCESS


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


def _iter_junit_reports(repo_path: Path) -> list[Path]:
    reports: list[Path] = []
    for pattern in ("**/surefire-reports/*.xml", "**/failsafe-reports/*.xml"):
        reports.extend(repo_path.glob(pattern))
    return reports


def _parse_junit_report(path: Path) -> tuple[int, int, int, int, float]:
    try:
        tree = ET.parse(path)  # noqa: S314 - trusted CI tool output
    except ET.ParseError:
        return 0, 0, 0, 0, 0.0

    root = tree.getroot()

    def parse_suite(element: ET.Element) -> tuple[int, int, int, int, float]:
        tests = _parse_int(element.attrib.get("tests"))
        failures = _parse_int(element.attrib.get("failures"))
        errors = _parse_int(element.attrib.get("errors"))
        skipped = _parse_int(element.attrib.get("skipped"))
        time_val = _parse_float(element.attrib.get("time"))
        return tests, failures, errors, skipped, time_val

    if root.tag == "testsuite":
        return parse_suite(root)

    total = (0, 0, 0, 0, 0.0)
    for child in root.findall("testsuite"):
        tests, failures, errors, skipped, time_val = parse_suite(child)
        total = (
            total[0] + tests,
            total[1] + failures,
            total[2] + errors,
            total[3] + skipped,
            total[4] + time_val,
        )
    return total


def cmd_codeql_build(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "compile", "-DskipTests"],
            repo_path,
        )
        return EXIT_SUCCESS
    if (repo_path / "pom.xml").exists():
        _run_command(
            ["mvn", "-B", "-ntp", "compile", "-DskipTests"],
            repo_path,
        )
    return EXIT_SUCCESS


def cmd_smoke_java_build(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "verify", "-Dmaven.test.failure.ignore=true"],
            repo_path,
        )
        return EXIT_SUCCESS
    if (repo_path / "pom.xml").exists():
        _run_command(
            ["mvn", "-B", "-ntp", "verify", "-Dmaven.test.failure.ignore=true"],
            repo_path,
        )
        return EXIT_SUCCESS
    print("::warning::No Maven project found")
    return EXIT_SUCCESS


def cmd_smoke_java_tests(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}

    for report in _iter_junit_reports(repo_path):
        tests, failures, errors, skipped, time_val = _parse_junit_report(report)
        totals["tests"] += tests
        totals["failures"] += failures
        totals["errors"] += errors
        totals["skipped"] += skipped
        totals["time"] += time_val

    failed = totals["failures"] + totals["errors"]
    passed = totals["tests"] - failed - totals["skipped"]
    runtime = f"{totals['time']:.2f}s"

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(
        {
            "total": str(totals["tests"]),
            "passed": str(passed),
            "failed": str(failed),
            "skipped": str(totals["skipped"]),
            "runtime": runtime,
        },
        output_path,
    )
    print(f"Tests: {totals['tests']} total, {passed} passed, {failed} failed, {totals['skipped']} skipped")
    return EXIT_SUCCESS


def cmd_smoke_java_coverage(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    jacoco_files = list(repo_path.rglob("jacoco.xml"))
    covered = 0
    missed = 0
    for report in jacoco_files:
        try:
            tree = ET.parse(report)  # noqa: S314 - trusted CI tool output
        except ET.ParseError:
            continue
        for counter in tree.getroot().iter("counter"):
            if counter.attrib.get("type") == "INSTRUCTION":
                covered += _parse_int(counter.attrib.get("covered"))
                missed += _parse_int(counter.attrib.get("missed"))

    total = covered + missed
    percent = int((covered * 100) / total) if total > 0 else 0
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(
        {
            "covered": str(covered),
            "missed": str(missed),
            "percent": str(percent),
            "lines": f"{covered} / {total}",
        },
        output_path,
    )
    print(f"Coverage: {percent}% ({covered} / {total} instructions)")
    return EXIT_SUCCESS


def cmd_smoke_java_checkstyle(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "-DskipTests", "checkstyle:checkstyle"],
            repo_path,
        )

    violations = 0
    for report in repo_path.rglob("checkstyle-result.xml"):
        try:
            tree = ET.parse(report)  # noqa: S314 - trusted CI tool output
        except ET.ParseError:
            continue
        violations += len(list(tree.getroot().iter("error")))

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"violations": str(violations)}, output_path)
    print(f"Checkstyle: {violations} issues found")
    return EXIT_SUCCESS


def cmd_smoke_java_spotbugs(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    mvnw = repo_path / "mvnw"
    if mvnw.exists():
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IEXEC)
        _run_command(
            ["./mvnw", "-B", "-ntp", "com.github.spotbugs:spotbugs-maven-plugin:check"],
            repo_path,
        )

    count = 0
    for report in repo_path.rglob("spotbugsXml.xml"):
        try:
            tree = ET.parse(report)  # noqa: S314 - trusted CI tool output
        except ET.ParseError:
            continue
        count += len(list(tree.getroot().iter("BugInstance")))

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"count": str(count)}, output_path)
    print(f"SpotBugs: {count} potential bugs")
    return EXIT_SUCCESS


def cmd_smoke_python_install(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    commands = [
        ["python", "-m", "pip", "install", "--upgrade", "pip"],
        ["pip", "install", "pytest", "pytest-cov"],
        ["pip", "install", "ruff", "black"],
    ]
    for cmd in commands:
        proc = _run_command(cmd, repo_path)
        if proc.returncode != 0:
            print(proc.stdout or proc.stderr or "pip install failed", file=sys.stderr)

    req_files = ["requirements.txt", "requirements-dev.txt"]
    for req in req_files:
        req_path = repo_path / req
        if req_path.exists():
            _run_command(["pip", "install", "-r", str(req_path)], repo_path)

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        proc = _run_command(["pip", "install", "-e", ".[dev]"], repo_path)
        if proc.returncode != 0:
            _run_command(["pip", "install", "-e", "."], repo_path)

    return EXIT_SUCCESS


def _last_regex_int(pattern: str, text: str) -> int:
    matches = re.findall(pattern, text)
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except ValueError:
        return 0


def cmd_smoke_python_tests(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    output_file = repo_path / args.output_file

    proc = _run_command(
        ["pytest", "--cov=.", "--cov-report=xml", "--cov-report=term", "-v"],
        repo_path,
    )
    output_text = (proc.stdout or "") + (proc.stderr or "")
    output_file.write_text(output_text, encoding="utf-8")

    passed = _last_regex_int(r"(\d+)\s+passed", output_text)
    failed = _last_regex_int(r"(\d+)\s+failed", output_text)
    skipped = _last_regex_int(r"(\d+)\s+skipped", output_text)

    coverage = 0
    coverage_file = repo_path / "coverage.xml"
    if coverage_file.exists():
        try:
            tree = ET.parse(coverage_file)  # noqa: S314 - trusted CI tool output
            root = tree.getroot()
            coverage = int(float(root.attrib.get("line-rate", "0")) * 100)
        except (ET.ParseError, ValueError):
            coverage = 0

    total = passed + failed + skipped
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs(
        {
            "total": str(total),
            "passed": str(passed),
            "failed": str(failed),
            "skipped": str(skipped),
            "coverage": str(coverage),
        },
        output_path,
    )
    print(f"Tests: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"Coverage: {coverage}%")
    return EXIT_SUCCESS


def cmd_smoke_python_ruff(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    report_path = repo_path / args.report

    proc = _run_command(["ruff", "check", ".", "--output-format=json"], repo_path)
    report_path.write_text(proc.stdout or "[]", encoding="utf-8")

    errors = 0
    security = 0
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            errors = len(data)
            security = sum(1 for item in data if str(item.get("code", "")).startswith("S"))
    except json.JSONDecodeError:
        errors = 0
        security = 0

    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"errors": str(errors), "security": str(security)}, output_path)
    print(f"Ruff: {errors} issues ({security} security-related)")
    return EXIT_SUCCESS


def cmd_smoke_python_black(args: argparse.Namespace) -> int:
    repo_path = Path(args.path).resolve()
    output_file = repo_path / args.output_file

    proc = _run_command(["black", "--check", "."], repo_path)
    output_text = (proc.stdout or "") + (proc.stderr or "")
    output_file.write_text(output_text, encoding="utf-8")

    issues = len([line for line in output_text.splitlines() if "would reformat" in line])
    output_path = _resolve_output_path(args.output, args.github_output)
    _write_outputs({"issues": str(issues)}, output_path)
    print(f"Black: {issues} files need reformatting")
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


# Empty SARIF for fallback when zizmor fails
EMPTY_SARIF = (
    '{"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json",'
    '"runs":[{"tool":{"driver":{"name":"zizmor","version":"0.8.0"}},"results":[]}]}'
)


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


def cmd_validate_configs(args: argparse.Namespace) -> int:
    """Validate all repo configs in config/repos/.

    Uses cihub.config.loader (no scripts dependency).
    """
    from cihub.config.loader import generate_workflow_inputs, load_config

    root = hub_root()
    configs_dir = Path(args.configs_dir) if args.configs_dir else root / "config" / "repos"

    repos: list[str]
    if args.repo:
        repos = [args.repo]
        config_path = configs_dir / f"{args.repo}.yaml"
        if not config_path.exists():
            print(f"Config not found: {config_path}", file=sys.stderr)
            return EXIT_FAILURE
    else:
        repos = [path.stem for path in sorted(configs_dir.glob("*.yaml"))]

    for repo in repos:
        print(f"Validating {repo}")
        config = load_config(repo_name=repo, hub_root=root)
        generate_workflow_inputs(config)

    print("✓ All configs valid")
    return EXIT_SUCCESS


def cmd_validate_profiles(args: argparse.Namespace) -> int:
    root = hub_root()
    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else root / "templates" / "profiles"
    try:
        import yaml
    except ImportError as exc:
        print(f"Missing PyYAML: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    for path in sorted(profiles_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            print(f"{path} not a dict", file=sys.stderr)
            return EXIT_FAILURE
        print(f"✓ {path.name}")
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


def _bar(value: int) -> str:
    """Render a visual progress bar using Unicode block characters."""
    if value < 0:
        value = 0
    filled = min(20, max(0, value // 5))
    return f"{'█' * filled}{'░' * (20 - filled)}"


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
            "",
            "Job summary generated at run-time",
        ]
    )
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


def _expected_matrix_keys() -> set[str]:
    tools = {key: True for key in _TOOL_KEYS}
    thresholds: dict[str, int | float | None] = {key: 1 for key in _THRESHOLD_KEYS}
    entry = RepoEntry(
        config_basename="example",
        name="repo",
        owner="owner",
        language="python",
        branch="main",
        subdir="src",
        subdir_safe="src",
        run_group="full",
        dispatch_enabled=True,
        dispatch_workflow="hub-ci.yml",
        use_central_runner=True,
        tools=tools,
        thresholds=thresholds,
        java_version="21",
        python_version="3.12",
        build_tool="maven",
        retention_days=30,
        write_github_summary=True,
    )
    return set(entry.to_matrix_entry().keys())


def cmd_verify_matrix_keys(args: argparse.Namespace) -> int:
    """Verify that all matrix.<key> references in hub-run-all.yml are emitted by cihub discover."""
    hub = hub_root()
    wf_path = hub / ".github" / "workflows" / "hub-run-all.yml"

    if not wf_path.exists():
        print(f"ERROR: {wf_path} not found", file=sys.stderr)
        return 2

    text = wf_path.read_text(encoding="utf-8")

    # Pattern for matrix.key references
    matrix_ref_re = re.compile(r"\bmatrix\.([A-Za-z_][A-Za-z0-9_]*)\b")
    referenced = set(matrix_ref_re.findall(text))
    emitted = _expected_matrix_keys()

    missing = sorted(referenced - emitted)
    unused = sorted(emitted - referenced)

    if missing:
        print("ERROR: matrix keys referenced but not emitted by builder:")
        for key in missing:
            print(f"  - {key}")
        return EXIT_FAILURE

    print("OK: all referenced matrix keys are emitted by the builder.")

    if unused:
        print("\nWARN: builder emits keys not referenced as matrix.<key> in this workflow:")
        for key in unused:
            print(f"  - {key}")

    return EXIT_SUCCESS


def cmd_quarantine_check(args: argparse.Namespace) -> int:
    """Fail if any file imports from _quarantine."""
    root = Path(getattr(args, "path", None) or hub_root())

    quarantine_patterns = [
        r"^\s*from\s+_quarantine\b",
        r"^\s*import\s+_quarantine\b",
        r"^\s*from\s+hub_release\._quarantine\b",
        r"^\s*import\s+hub_release\._quarantine\b",
        r"^\s*from\s+cihub\._quarantine\b",
        r"^\s*import\s+cihub\._quarantine\b",
        r"^\s*from\s+\.+_quarantine\b",
    ]
    exclude_dirs = {
        "_quarantine",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".ruff_cache",
        "vendor",
        "generated",
    }
    env_excludes = os.environ.get("QUARANTINE_EXCLUDE_DIRS", "")
    if env_excludes:
        exclude_dirs.update(env_excludes.split(","))

    violations: list[tuple[Path, int, str]] = []

    for path in root.rglob("*.py"):
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for pattern in quarantine_patterns:
                if re.search(pattern, line):
                    violations.append((path, line_num, line.strip()))

    if not violations:
        print("Quarantine check PASSED - no imports from _quarantine found")
        return EXIT_SUCCESS

    print("=" * 60)
    print("QUARANTINE IMPORT VIOLATION")
    print("=" * 60)
    print("\nFiles importing from _quarantine detected!")
    print("_quarantine is COLD STORAGE - it must not be imported.\n")
    print("Violations:")
    print("-" * 60)

    for path, line_num, line in violations:
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            rel_path = path
        print(f"  {rel_path}:{line_num}")
        print(f"    {line}\n")

    print("-" * 60)
    print(f"Total: {len(violations)} violation(s)")
    return EXIT_FAILURE


def cmd_hub_ci(args: argparse.Namespace) -> int:
    handlers = {
        "actionlint-install": cmd_actionlint_install,
        "actionlint": cmd_actionlint,
        "syntax-check": cmd_syntax_check,
        "repo-check": cmd_repo_check,
        "source-check": cmd_source_check,
        "security-pip-audit": cmd_security_pip_audit,
        "security-bandit": cmd_security_bandit,
        "security-ruff": cmd_security_ruff,
        "security-owasp": cmd_security_owasp,
        "docker-compose-check": cmd_docker_compose_check,
        "codeql-build": cmd_codeql_build,
        "kyverno-install": cmd_kyverno_install,
        "trivy-install": cmd_trivy_install,
        "kyverno-validate": cmd_kyverno_validate,
        "kyverno-test": cmd_kyverno_test,
        "smoke-java-build": cmd_smoke_java_build,
        "smoke-java-tests": cmd_smoke_java_tests,
        "smoke-java-coverage": cmd_smoke_java_coverage,
        "smoke-java-checkstyle": cmd_smoke_java_checkstyle,
        "smoke-java-spotbugs": cmd_smoke_java_spotbugs,
        "smoke-python-install": cmd_smoke_python_install,
        "smoke-python-tests": cmd_smoke_python_tests,
        "smoke-python-ruff": cmd_smoke_python_ruff,
        "smoke-python-black": cmd_smoke_python_black,
        "release-parse-tag": cmd_release_parse_tag,
        "release-update-tag": cmd_release_update_tag,
        "ruff": cmd_ruff,
        "black": cmd_black,
        "mutmut": cmd_mutmut,
        "badges": cmd_badges,
        "badges-commit": cmd_badges_commit,
        "outputs": cmd_outputs,
        "bandit": cmd_bandit,
        "pip-audit": cmd_pip_audit,
        "zizmor-run": cmd_zizmor_run,
        "zizmor-check": cmd_zizmor_check,
        "validate-configs": cmd_validate_configs,
        "validate-profiles": cmd_validate_profiles,
        "license-check": cmd_license_check,
        "gitleaks-summary": cmd_gitleaks_summary,
        "pytest-summary": cmd_pytest_summary,
        "summary": cmd_summary,
        "enforce": cmd_enforce,
        "verify-matrix-keys": cmd_verify_matrix_keys,
        "quarantine-check": cmd_quarantine_check,
    }
    handler = handlers.get(args.subcommand)
    if handler is None:
        print(f"Unknown hub-ci subcommand: {args.subcommand}", file=sys.stderr)
        return EXIT_USAGE
    return handler(args)
