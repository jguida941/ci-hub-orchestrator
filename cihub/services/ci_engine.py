"""CI execution engine for the services layer."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import smtplib
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Mapping

from cihub.ci_config import load_ci_config, load_hub_config
from cihub.ci_report import (
    RunContext,
    build_java_report,
    build_python_report,
    resolve_thresholds,
)
from cihub.ci_runner import (
    ToolResult,
    run_bandit,
    run_black,
    run_checkstyle,
    run_isort,
    run_jacoco,
    run_java_build,
    run_mutmut,
    run_mypy,
    run_owasp,
    run_pip_audit,
    run_pitest,
    run_pmd,
    run_pytest,
    run_ruff,
    run_sbom,
    run_semgrep,
    run_spotbugs,
    run_trivy,
)
from cihub.cli import (
    get_git_branch,
    get_git_remote,
    parse_repo_from_remote,
    resolve_executable,
    validate_subdir,
)
from cihub.exit_codes import EXIT_FAILURE, EXIT_INTERNAL_ERROR, EXIT_SUCCESS
from cihub.reporting import render_summary
from cihub.services.types import ServiceResult


@dataclass
class CiRunResult(ServiceResult):
    """Result of running cihub ci via the services layer."""

    exit_code: int = 0
    report_path: Path | None = None
    summary_path: Path | None = None
    report: dict[str, Any] = field(default_factory=dict)
    summary_text: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    problems: list[dict[str, Any]] = field(default_factory=list)


PYTHON_TOOLS = [
    "pytest",
    "ruff",
    "black",
    "isort",
    "mypy",
    "bandit",
    "pip_audit",
    "sbom",
    "semgrep",
    "trivy",
    "codeql",
    "docker",
    "hypothesis",
    "mutmut",
]

JAVA_TOOLS = [
    "jacoco",
    "pitest",
    "jqwik",
    "checkstyle",
    "spotbugs",
    "pmd",
    "owasp",
    "semgrep",
    "trivy",
    "codeql",
    "sbom",
    "docker",
]

RESERVED_FEATURES: list[tuple[str, str]] = [
    ("chaos", "Chaos testing"),
    ("dr_drill", "Disaster recovery drills"),
    ("cache_sentinel", "Cache sentinel"),
    ("runner_isolation", "Runner isolation"),
    ("supply_chain", "Supply chain security"),
    ("egress_control", "Egress control"),
    ("canary", "Canary deployments"),
    ("telemetry", "Telemetry"),
    ("kyverno", "Kyverno policies"),
]

PYTHON_RUNNERS = {
    "pytest": run_pytest,
    "ruff": run_ruff,
    "black": run_black,
    "isort": run_isort,
    "mypy": run_mypy,
    "bandit": run_bandit,
    "pip_audit": run_pip_audit,
    "mutmut": run_mutmut,
    "sbom": run_sbom,
    "semgrep": run_semgrep,
    "trivy": run_trivy,
}

JAVA_RUNNERS = {
    "jacoco": run_jacoco,
    "pitest": run_pitest,
    "checkstyle": run_checkstyle,
    "spotbugs": run_spotbugs,
    "pmd": run_pmd,
    "owasp": run_owasp,
    "semgrep": run_semgrep,
    "trivy": run_trivy,
    "sbom": run_sbom,
}


def _get_repo_name(config: dict[str, Any], repo_path: Path) -> str:
    repo_env = os.environ.get("GITHUB_REPOSITORY")
    if repo_env:
        return repo_env
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    owner = repo_info.get("owner")
    name = repo_info.get("name")
    if owner and name:
        return f"{owner}/{name}"
    remote = get_git_remote(repo_path)
    if remote:
        parsed = parse_repo_from_remote(remote)
        if parsed[0] and parsed[1]:
            return f"{parsed[0]}/{parsed[1]}"
    return ""


def _get_git_commit(repo_path: Path) -> str:
    try:
        git_bin = resolve_executable("git")
        output = subprocess.check_output(  # noqa: S603
            [git_bin, "-C", str(repo_path), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return output.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _resolve_workdir(
    repo_path: Path,
    config: dict[str, Any],
    override: str | None,
) -> str:
    if override:
        validate_subdir(override)
        return override
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    subdir = repo_info.get("subdir")
    if isinstance(subdir, str) and subdir:
        validate_subdir(subdir)
        return subdir
    return "."


def _detect_java_project_type(workdir: Path) -> str:
    pom = workdir / "pom.xml"
    if pom.exists():
        try:
            content = pom.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "<modules>" in content:
            modules = len(re.findall(r"<module>.*?</module>", content))
            return f"Multi-module ({modules} modules)" if modules else "Multi-module"
        return "Single module"

    settings_gradle = workdir / "settings.gradle"
    settings_kts = workdir / "settings.gradle.kts"
    if settings_gradle.exists() or settings_kts.exists():
        return "Multi-module"
    if (workdir / "build.gradle").exists() or (workdir / "build.gradle.kts").exists():
        return "Single module"
    return "Unknown"


def _tool_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    tools = config.get(language, {}).get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if isinstance(entry, bool):
        return entry
    if isinstance(entry, dict):
        return bool(entry.get("enabled", False))
    return False


def _tool_gate_enabled(config: dict[str, Any], tool: str, language: str) -> bool:
    tools = config.get(language, {}).get("tools", {}) or {}
    entry = tools.get(tool, {}) if isinstance(tools, dict) else {}
    if not isinstance(entry, dict):
        return True

    if language == "python":
        if tool == "ruff":
            return bool(entry.get("fail_on_error", True))
        if tool == "black":
            return bool(entry.get("fail_on_format_issues", True))
        if tool == "isort":
            return bool(entry.get("fail_on_issues", True))
        if tool == "bandit":
            return bool(entry.get("fail_on_high", True))
        if tool == "pip_audit":
            return bool(entry.get("fail_on_vuln", True))
        if tool == "semgrep":
            return bool(entry.get("fail_on_findings", True))
        if tool == "trivy":
            return bool(entry.get("fail_on_critical", True) or entry.get("fail_on_high", True))

    if language == "java":
        if tool == "checkstyle":
            return bool(entry.get("fail_on_violation", True))
        if tool == "spotbugs":
            return bool(entry.get("fail_on_error", True))
        if tool == "pmd":
            return bool(entry.get("fail_on_violation", True))
        if tool == "semgrep":
            return bool(entry.get("fail_on_findings", True))
        if tool == "trivy":
            return bool(entry.get("fail_on_critical", True) or entry.get("fail_on_high", True))

    return True


def _parse_env_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _get_env_name(config: dict[str, Any], key: str, default: str) -> str:
    value = config.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _get_env_value(
    env: Mapping[str, str],
    name: str | None,
    fallbacks: list[str] | None = None,
) -> str | None:
    if name:
        value = env.get(name)
        if value:
            return value
    if fallbacks:
        for fallback in fallbacks:
            value = env.get(fallback)
            if value:
                return value
    return None


def _warn_reserved_features(config: dict[str, Any], problems: list[dict[str, Any]]) -> None:
    for key, label in RESERVED_FEATURES:
        entry = config.get(key, {})
        enabled = False
        if isinstance(entry, dict):
            enabled = bool(entry.get("enabled", False))
        elif isinstance(entry, bool):
            enabled = entry
        if enabled:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"{label} is enabled but not implemented yet (toggle reserved).",
                    "code": "CIHUB-CI-RESERVED-FEATURE",
                }
            )


def _set_tool_enabled(
    config: dict[str, Any],
    language: str,
    tool: str,
    enabled: bool,
) -> None:
    lang_cfg = config.setdefault(language, {})
    tools = lang_cfg.setdefault("tools", {})
    entry = tools.get(tool)
    if isinstance(entry, dict):
        entry["enabled"] = enabled
    else:
        tools[tool] = {"enabled": enabled}


def _apply_env_overrides(
    config: dict[str, Any],
    language: str,
    env: dict[str, str],
    problems: list[dict[str, Any]],
) -> None:
    tool_env = {
        "python": {
            "pytest": "CIHUB_RUN_PYTEST",
            "ruff": "CIHUB_RUN_RUFF",
            "bandit": "CIHUB_RUN_BANDIT",
            "pip_audit": "CIHUB_RUN_PIP_AUDIT",
            "mypy": "CIHUB_RUN_MYPY",
            "black": "CIHUB_RUN_BLACK",
            "isort": "CIHUB_RUN_ISORT",
            "mutmut": "CIHUB_RUN_MUTMUT",
            "hypothesis": "CIHUB_RUN_HYPOTHESIS",
            "sbom": "CIHUB_RUN_SBOM",
            "semgrep": "CIHUB_RUN_SEMGREP",
            "trivy": "CIHUB_RUN_TRIVY",
            "codeql": "CIHUB_RUN_CODEQL",
            "docker": "CIHUB_RUN_DOCKER",
        },
        "java": {
            "jacoco": "CIHUB_RUN_JACOCO",
            "checkstyle": "CIHUB_RUN_CHECKSTYLE",
            "spotbugs": "CIHUB_RUN_SPOTBUGS",
            "owasp": "CIHUB_RUN_OWASP",
            "pitest": "CIHUB_RUN_PITEST",
            "jqwik": "CIHUB_RUN_JQWIK",
            "pmd": "CIHUB_RUN_PMD",
            "semgrep": "CIHUB_RUN_SEMGREP",
            "trivy": "CIHUB_RUN_TRIVY",
            "codeql": "CIHUB_RUN_CODEQL",
            "sbom": "CIHUB_RUN_SBOM",
            "docker": "CIHUB_RUN_DOCKER",
        },
    }
    overrides = tool_env.get(language, {})
    for tool, var in overrides.items():
        raw = env.get(var)
        if raw is None:
            continue
        parsed = _parse_env_bool(raw)
        if parsed is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Invalid boolean for {var}: {raw!r}",
                    "code": "CIHUB-CI-ENV-BOOL",
                }
            )
            continue
        _set_tool_enabled(config, language, tool, parsed)

    summary_override = _parse_env_bool(env.get("CIHUB_WRITE_GITHUB_SUMMARY"))
    if summary_override is not None:
        reports = config.setdefault("reports", {})
        github_summary = reports.setdefault("github_summary", {})
        github_summary["enabled"] = summary_override


def _apply_force_all_tools(config: dict[str, Any], language: str) -> None:
    repo_cfg = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    if not repo_cfg.get("force_all_tools", False):
        return
    tool_list = PYTHON_TOOLS if language == "python" else JAVA_TOOLS
    for tool in tool_list:
        _set_tool_enabled(config, language, tool, True)


def _collect_codecov_files(
    language: str,
    output_dir: Path,
    tool_outputs: dict[str, dict[str, Any]],
) -> list[Path]:
    files: list[Path] = []
    if language == "python":
        coverage_path = tool_outputs.get("pytest", {}).get("artifacts", {}).get("coverage")
        if coverage_path:
            files.append(Path(coverage_path))
        else:
            files.append(output_dir / "coverage.xml")
    elif language == "java":
        jacoco_path = tool_outputs.get("jacoco", {}).get("artifacts", {}).get("report")
        if jacoco_path:
            files.append(Path(jacoco_path))
    return [path for path in files if path and path.exists()]


def _run_codecov_upload(
    files: list[Path],
    fail_ci_on_error: bool,
    problems: list[dict[str, Any]],
) -> None:
    if not files:
        problems.append(
            {
                "severity": "warning",
                "message": "Codecov enabled but no coverage files were found",
                "code": "CIHUB-CI-CODECOV-NO-FILES",
            }
        )
        return
    codecov_bin = shutil.which("codecov")
    if not codecov_bin:
        problems.append(
            {
                "severity": "error" if fail_ci_on_error else "warning",
                "message": "Codecov enabled but uploader not found in PATH",
                "code": "CIHUB-CI-CODECOV-MISSING",
            }
        )
        return
    cmd = [codecov_bin]
    for path in files:
        cmd.extend(["-f", str(path)])
    proc = subprocess.run(  # noqa: S603
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        problems.append(
            {
                "severity": "error" if fail_ci_on_error else "warning",
                "message": f"Codecov upload failed: {proc.stderr.strip() or proc.stdout.strip()}",
                "code": "CIHUB-CI-CODECOV-FAILED",
            }
        )


def _send_slack(
    webhook_url: str,
    message: str,
    problems: list[dict[str, Any]],
) -> None:
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            if resp.status >= 400:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Slack notification failed with status {resp.status}",
                        "code": "CIHUB-CI-SLACK-FAILED",
                    }
                )
    except Exception as exc:  # pragma: no cover - network dependent
        problems.append(
            {
                "severity": "warning",
                "message": f"Slack notification failed: {exc}",
                "code": "CIHUB-CI-SLACK-FAILED",
            }
        )


def _send_email(
    subject: str,
    body: str,
    problems: list[dict[str, Any]],
    email_cfg: dict[str, Any],
    env: Mapping[str, str],
) -> None:
    host_name = _get_env_name(email_cfg, "smtp_host_env", "SMTP_HOST")
    host = _get_env_value(env, host_name)
    if not host:
        problems.append(
            {
                "severity": "warning",
                "message": f"Email notifications enabled but {host_name} is not set",
                "code": "CIHUB-CI-EMAIL-MISSING",
            }
        )
        return
    port_name = _get_env_name(email_cfg, "smtp_port_env", "SMTP_PORT")
    port_value = _get_env_value(env, port_name)
    port = 25
    if port_value:
        try:
            port = int(port_value)
        except ValueError:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Email notifications enabled but {port_name} is not a valid port",
                    "code": "CIHUB-CI-EMAIL-MISSING",
                }
            )
            port = 25

    username = _get_env_value(env, _get_env_name(email_cfg, "smtp_user_env", "SMTP_USER"))
    password = _get_env_value(env, _get_env_name(email_cfg, "smtp_password_env", "SMTP_PASSWORD"))
    starttls_value = _get_env_value(
        env,
        _get_env_name(email_cfg, "smtp_starttls_env", "SMTP_STARTTLS"),
    )
    use_starttls = _parse_env_bool(starttls_value) or False
    sender = _get_env_value(env, _get_env_name(email_cfg, "smtp_from_env", "SMTP_FROM")) or "cihub@localhost"
    recipients_name = _get_env_name(email_cfg, "recipients_env", "CIHUB_EMAIL_TO")
    recipients = _get_env_value(env, recipients_name, ["SMTP_TO", "EMAIL_TO"])
    if not recipients:
        problems.append(
            {
                "severity": "warning",
                "message": (f"Email notifications enabled but no recipients set ({recipients_name}/SMTP_TO/EMAIL_TO)"),
                "code": "CIHUB-CI-EMAIL-MISSING",
            }
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipients
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as client:
            if use_starttls:
                client.starttls()
            if username and password:
                client.login(username, password)
            client.send_message(msg)
    except Exception as exc:  # pragma: no cover - network dependent
        problems.append(
            {
                "severity": "warning",
                "message": f"Email notification failed: {exc}",
                "code": "CIHUB-CI-EMAIL-FAILED",
            }
        )


def _notify(
    success: bool,
    config: dict[str, Any],
    report: dict[str, Any],
    problems: list[dict[str, Any]],
    env: Mapping[str, str],
) -> None:
    notifications = config.get("notifications", {}) or {}
    slack_cfg = notifications.get("slack", {}) or {}
    email_cfg = notifications.get("email", {}) or {}

    repo = report.get("repository", "") or report.get("repo", "") or "unknown"
    branch = report.get("branch", "") or "unknown"
    status = "SUCCESS" if success else "FAILURE"

    if slack_cfg.get("enabled", False):
        on_success = bool(slack_cfg.get("on_success", False))
        on_failure = bool(slack_cfg.get("on_failure", True))
        if (success and on_success) or (not success and on_failure):
            webhook_name = _get_env_name(slack_cfg, "webhook_env", "CIHUB_SLACK_WEBHOOK_URL")
            webhook = _get_env_value(env, webhook_name, ["SLACK_WEBHOOK_URL", "SLACK_WEBHOOK"])
            if not webhook:
                problems.append(
                    {
                        "severity": "warning",
                        "message": f"Slack notifications enabled but {webhook_name} is not set",
                        "code": "CIHUB-CI-SLACK-MISSING",
                    }
                )
            else:
                _send_slack(webhook, f"CIHUB {status}: {repo} ({branch})", problems)

    if email_cfg.get("enabled", False):
        _send_email(
            f"CIHUB {status}: {repo}",
            f"Repository: {repo}\nBranch: {branch}\nStatus: {status}\n",
            problems,
            email_cfg,
            env,
        )


def _run_dep_command(
    cmd: list[str],
    workdir: Path,
    label: str,
    problems: list[dict[str, Any]],
) -> bool:
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=workdir,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return True
    message = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
    problems.append(
        {
            "severity": "error",
            "message": f"{label} failed: {message}",
            "code": "CIHUB-CI-DEPS",
        }
    )
    return False


def _install_python_dependencies(
    config: dict[str, Any],
    workdir: Path,
    problems: list[dict[str, Any]],
) -> None:
    deps_cfg = config.get("python", {}).get("dependencies", {}) or {}
    if isinstance(deps_cfg, dict):
        if deps_cfg.get("install") is False:
            return
        commands = deps_cfg.get("commands")
    else:
        commands = None

    python_bin = sys.executable or resolve_executable("python")
    if commands:
        for cmd in commands:
            if not cmd:
                continue
            if isinstance(cmd, list):
                parts = [str(part) for part in cmd if str(part)]
            else:
                cmd_str = str(cmd).strip()
                if not cmd_str:
                    continue
                parts = shlex.split(cmd_str)
            if not parts:
                continue
            _run_dep_command(parts, workdir, " ".join(parts), problems)
        return

    if (workdir / "requirements.txt").exists():
        _run_dep_command(
            [python_bin, "-m", "pip", "install", "-r", "requirements.txt"],
            workdir,
            "requirements.txt",
            problems,
        )
    if (workdir / "requirements-dev.txt").exists():
        _run_dep_command(
            [python_bin, "-m", "pip", "install", "-r", "requirements-dev.txt"],
            workdir,
            "requirements-dev.txt",
            problems,
        )
    if (workdir / "pyproject.toml").exists():
        ok = _run_dep_command(
            [python_bin, "-m", "pip", "install", "-e", ".[dev]"],
            workdir,
            "pyproject.toml [dev]",
            problems,
        )
        if not ok:
            _run_dep_command(
                [python_bin, "-m", "pip", "install", "-e", "."],
                workdir,
                "pyproject.toml",
                problems,
            )


def _run_python_tools(
    config: dict[str, Any],
    repo_path: Path,
    workdir: str,
    output_dir: Path,
    problems: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        raise FileNotFoundError(f"Workdir not found: {workdir_path}")

    mutants_dir = workdir_path / "mutants"
    if mutants_dir.exists():
        try:
            shutil.rmtree(mutants_dir)
        except OSError as exc:
            problems.append(
                {
                    "severity": "warning",
                    "message": f"Failed to remove mutmut artifacts: {exc}",
                    "code": "CIHUB-CI-MUTMUT-CLEANUP",
                }
            )

    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {tool: False for tool in PYTHON_TOOLS}
    tools_success: dict[str, bool] = {tool: False for tool in PYTHON_TOOLS}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    for tool in PYTHON_TOOLS:
        if tool == "hypothesis":
            continue
        enabled = _tool_enabled(config, tool, "python")
        if not enabled:
            continue
        runner = PYTHON_RUNNERS.get(tool)
        if runner is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": (f"Tool '{tool}' is enabled but is not supported by cihub; run it via a workflow step."),
                    "code": "CIHUB-CI-UNSUPPORTED",
                }
            )
            ToolResult(tool=tool, ran=False, success=False).write_json(tool_output_dir / f"{tool}.json")
            continue
        try:
            if tool == "pytest":
                pytest_cfg = config.get("python", {}).get("tools", {}).get("pytest", {}) or {}
                fail_fast = bool(pytest_cfg.get("fail_fast", False))
                result = runner(workdir_path, output_dir, fail_fast)  # type: ignore[operator]
            elif tool == "mutmut":
                timeout = config.get("python", {}).get("tools", {}).get("mutmut", {}).get("timeout_minutes", 15)
                result = runner(workdir_path, output_dir, int(timeout) * 60)  # type: ignore[operator]
            elif tool == "sbom":
                sbom_cfg = config.get("python", {}).get("tools", {}).get("sbom", {})
                if not isinstance(sbom_cfg, dict):
                    sbom_cfg = {}
                sbom_format = sbom_cfg.get("format", "cyclonedx")
                result = runner(workdir_path, output_dir, sbom_format)  # type: ignore[operator]
            else:
                result = runner(workdir_path, output_dir)  # type: ignore[operator]
        except FileNotFoundError as exc:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found: {exc}",
                    "code": "CIHUB-CI-MISSING-TOOL",
                }
            )
            result = ToolResult(tool=tool, ran=False, success=False)
        tool_outputs[tool] = result.to_payload()
        tools_ran[tool] = result.ran
        tools_success[tool] = result.success
        result.write_json(tool_output_dir / f"{tool}.json")

    if _tool_enabled(config, "hypothesis", "python"):
        tools_ran["hypothesis"] = tools_ran.get("pytest", False)
        tools_success["hypothesis"] = tools_success.get("pytest", False)

    return tool_outputs, tools_ran, tools_success


def _run_java_tools(
    config: dict[str, Any],
    repo_path: Path,
    workdir: str,
    output_dir: Path,
    build_tool: str,
    problems: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, bool], dict[str, bool]]:
    workdir_path = repo_path / workdir
    if not workdir_path.exists():
        raise FileNotFoundError(f"Workdir not found: {workdir_path}")

    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {tool: False for tool in JAVA_TOOLS}
    tools_success: dict[str, bool] = {tool: False for tool in JAVA_TOOLS}

    tool_output_dir = output_dir / "tool-outputs"
    tool_output_dir.mkdir(parents=True, exist_ok=True)

    jacoco_enabled = _tool_enabled(config, "jacoco", "java")
    build_result = run_java_build(workdir_path, output_dir, build_tool, jacoco_enabled)
    tool_outputs["build"] = build_result.to_payload()
    build_result.write_json(tool_output_dir / "build.json")

    use_nvd_api_key = bool(config.get("java", {}).get("tools", {}).get("owasp", {}).get("use_nvd_api_key", True))

    for tool in JAVA_TOOLS:
        if tool == "jqwik":
            continue
        enabled = _tool_enabled(config, tool, "java")
        if not enabled:
            continue
        runner = JAVA_RUNNERS.get(tool)
        if runner is None:
            problems.append(
                {
                    "severity": "warning",
                    "message": (f"Tool '{tool}' is enabled but is not supported by cihub; run it via a workflow step."),
                    "code": "CIHUB-CI-UNSUPPORTED",
                }
            )
            ToolResult(tool=tool, ran=False, success=False).write_json(tool_output_dir / f"{tool}.json")
            continue
        try:
            if tool == "pitest":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "checkstyle":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "spotbugs":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "pmd":
                result = runner(workdir_path, output_dir, build_tool)  # type: ignore[operator]
            elif tool == "owasp":
                result = runner(workdir_path, output_dir, build_tool, use_nvd_api_key)  # type: ignore[operator]
            elif tool == "sbom":
                sbom_cfg = config.get("java", {}).get("tools", {}).get("sbom", {})
                if not isinstance(sbom_cfg, dict):
                    sbom_cfg = {}
                sbom_format = sbom_cfg.get("format", "cyclonedx")
                result = runner(workdir_path, output_dir, sbom_format)  # type: ignore[operator]
            else:
                result = runner(workdir_path, output_dir)  # type: ignore[operator]
        except FileNotFoundError as exc:
            problems.append(
                {
                    "severity": "error",
                    "message": f"Tool '{tool}' not found: {exc}",
                    "code": "CIHUB-CI-MISSING-TOOL",
                }
            )
            result = ToolResult(tool=tool, ran=False, success=False)

        tool_outputs[tool] = result.to_payload()
        tools_ran[tool] = result.ran
        tools_success[tool] = result.success
        result.write_json(tool_output_dir / f"{tool}.json")

    if _tool_enabled(config, "jqwik", "java"):
        tests_failed = int(build_result.metrics.get("tests_failed", 0))
        tools_ran["jqwik"] = True
        tools_success["jqwik"] = build_result.success and tests_failed == 0

    return tool_outputs, tools_ran, tools_success


def _build_context(
    repo_path: Path,
    config: dict[str, Any],
    workdir: str,
    correlation_id: str | None,
    build_tool: str | None = None,
    project_type: str | None = None,
    docker_compose_file: str | None = None,
    docker_health_endpoint: str | None = None,
) -> RunContext:
    repo_info = config.get("repo", {}) if isinstance(config.get("repo"), dict) else {}
    branch = os.environ.get("GITHUB_REF_NAME") or repo_info.get("default_branch")
    branch = branch or get_git_branch(repo_path) or ""
    return RunContext(
        repository=_get_repo_name(config, repo_path),
        branch=branch,
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_number=os.environ.get("GITHUB_RUN_NUMBER"),
        commit=os.environ.get("GITHUB_SHA") or _get_git_commit(repo_path),
        correlation_id=correlation_id,
        workflow_ref=os.environ.get("GITHUB_WORKFLOW_REF"),
        workdir=workdir,
        build_tool=build_tool,
        retention_days=config.get("reports", {}).get("retention_days"),
        project_type=project_type,
        docker_compose_file=docker_compose_file,
        docker_health_endpoint=docker_health_endpoint,
    )


def _evaluate_python_gates(
    report: dict[str, Any],
    thresholds: dict[str, Any],
    tools_configured: dict[str, bool],
    config: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    results = report.get("results", {}) or {}
    metrics = report.get("tool_metrics", {}) or {}

    tests_failed = int(results.get("tests_failed", 0))
    if tools_configured.get("pytest") and tests_failed > 0:
        failures.append("pytest failures detected")

    coverage_min = int(thresholds.get("coverage_min", 0) or 0)
    coverage = int(results.get("coverage", 0))
    if tools_configured.get("pytest") and coverage < coverage_min:
        failures.append(f"coverage {coverage}% < {coverage_min}%")

    mut_min = int(thresholds.get("mutation_score_min", 0) or 0)
    mut_score = int(results.get("mutation_score", 0))
    if tools_configured.get("mutmut") and mut_score < mut_min:
        failures.append(f"mutation score {mut_score}% < {mut_min}%")

    max_ruff = int(thresholds.get("max_ruff_errors", 0) or 0)
    ruff_errors = int(metrics.get("ruff_errors", 0))
    if tools_configured.get("ruff") and _tool_gate_enabled(config, "ruff", "python") and ruff_errors > max_ruff:
        failures.append(f"ruff errors {ruff_errors} > {max_ruff}")

    max_black = int(thresholds.get("max_black_issues", 0) or 0)
    black_issues = int(metrics.get("black_issues", 0))
    if tools_configured.get("black") and _tool_gate_enabled(config, "black", "python") and black_issues > max_black:
        failures.append(f"black issues {black_issues} > {max_black}")

    max_isort = int(thresholds.get("max_isort_issues", 0) or 0)
    isort_issues = int(metrics.get("isort_issues", 0))
    if tools_configured.get("isort") and _tool_gate_enabled(config, "isort", "python") and isort_issues > max_isort:
        failures.append(f"isort issues {isort_issues} > {max_isort}")

    mypy_errors = int(metrics.get("mypy_errors", 0))
    if tools_configured.get("mypy") and mypy_errors > 0:
        failures.append(f"mypy errors {mypy_errors} > 0")

    max_high = int(thresholds.get("max_high_vulns", 0) or 0)
    bandit_high = int(metrics.get("bandit_high", 0))
    if tools_configured.get("bandit") and _tool_gate_enabled(config, "bandit", "python") and bandit_high > max_high:
        failures.append(f"bandit high {bandit_high} > {max_high}")

    pip_vulns = int(metrics.get("pip_audit_vulns", 0))
    max_pip = int(thresholds.get("max_pip_audit_vulns", max_high) or 0)
    if tools_configured.get("pip_audit") and _tool_gate_enabled(config, "pip_audit", "python") and pip_vulns > max_pip:
        failures.append(f"pip-audit vulns {pip_vulns} > {max_pip}")

    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
    semgrep_findings = int(metrics.get("semgrep_findings", 0))
    if (
        tools_configured.get("semgrep")
        and _tool_gate_enabled(config, "semgrep", "python")
        and semgrep_findings > max_semgrep
    ):
        failures.append(f"semgrep findings {semgrep_findings} > {max_semgrep}")

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    trivy_critical = int(metrics.get("trivy_critical", 0))
    if (
        tools_configured.get("trivy")
        and bool(config.get("python", {}).get("tools", {}).get("trivy", {}).get("fail_on_critical", True))
        and trivy_critical > max_critical
    ):
        failures.append(f"trivy critical {trivy_critical} > {max_critical}")

    trivy_high = int(metrics.get("trivy_high", 0))
    if (
        tools_configured.get("trivy")
        and bool(config.get("python", {}).get("tools", {}).get("trivy", {}).get("fail_on_high", True))
        and trivy_high > max_high
    ):
        failures.append(f"trivy high {trivy_high} > {max_high}")

    return failures


def _evaluate_java_gates(
    report: dict[str, Any],
    thresholds: dict[str, Any],
    tools_configured: dict[str, bool],
    config: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    results = report.get("results", {}) or {}
    metrics = report.get("tool_metrics", {}) or {}

    tests_failed = int(results.get("tests_failed", 0))
    if tests_failed > 0:
        failures.append("test failures detected")

    coverage_min = int(thresholds.get("coverage_min", 0) or 0)
    coverage = int(results.get("coverage", 0))
    if tools_configured.get("jacoco") and coverage < coverage_min:
        failures.append(f"coverage {coverage}% < {coverage_min}%")

    mut_min = int(thresholds.get("mutation_score_min", 0) or 0)
    mut_score = int(results.get("mutation_score", 0))
    if tools_configured.get("pitest") and mut_score < mut_min:
        failures.append(f"mutation score {mut_score}% < {mut_min}%")

    max_checkstyle = int(thresholds.get("max_checkstyle_errors", 0) or 0)
    checkstyle_issues = int(metrics.get("checkstyle_issues", 0))
    if (
        tools_configured.get("checkstyle")
        and _tool_gate_enabled(config, "checkstyle", "java")
        and checkstyle_issues > max_checkstyle
    ):
        failures.append(f"checkstyle issues {checkstyle_issues} > {max_checkstyle}")

    max_spotbugs = int(thresholds.get("max_spotbugs_bugs", 0) or 0)
    spotbugs_issues = int(metrics.get("spotbugs_issues", 0))
    if (
        tools_configured.get("spotbugs")
        and _tool_gate_enabled(config, "spotbugs", "java")
        and spotbugs_issues > max_spotbugs
    ):
        failures.append(f"spotbugs issues {spotbugs_issues} > {max_spotbugs}")

    max_pmd = int(thresholds.get("max_pmd_violations", 0) or 0)
    pmd_issues = int(metrics.get("pmd_violations", 0))
    if tools_configured.get("pmd") and _tool_gate_enabled(config, "pmd", "java") and pmd_issues > max_pmd:
        failures.append(f"pmd violations {pmd_issues} > {max_pmd}")

    max_critical = int(thresholds.get("max_critical_vulns", 0) or 0)
    max_high = int(thresholds.get("max_high_vulns", 0) or 0)

    owasp_critical = int(metrics.get("owasp_critical", 0))
    owasp_high = int(metrics.get("owasp_high", 0))
    if tools_configured.get("owasp") and (owasp_critical > max_critical or owasp_high > max_high):
        failures.append(f"owasp critical/high {owasp_critical}/{owasp_high} > {max_critical}/{max_high}")

    trivy_critical = int(metrics.get("trivy_critical", 0))
    trivy_high = int(metrics.get("trivy_high", 0))
    trivy_cfg = config.get("java", {}).get("tools", {}).get("trivy", {}) or {}
    trivy_crit_gate = bool(trivy_cfg.get("fail_on_critical", True))
    trivy_high_gate = bool(trivy_cfg.get("fail_on_high", True))
    if tools_configured.get("trivy") and (
        (trivy_crit_gate and trivy_critical > max_critical) or (trivy_high_gate and trivy_high > max_high)
    ):
        failures.append(f"trivy critical/high {trivy_critical}/{trivy_high} > {max_critical}/{max_high}")

    max_semgrep = int(thresholds.get("max_semgrep_findings", 0) or 0)
    semgrep_findings = int(metrics.get("semgrep_findings", 0))
    if (
        tools_configured.get("semgrep")
        and _tool_gate_enabled(config, "semgrep", "java")
        and semgrep_findings > max_semgrep
    ):
        failures.append(f"semgrep findings {semgrep_findings} > {max_semgrep}")

    return failures


def _split_problems(problems: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    errors = [p.get("message", "") for p in problems if p.get("severity") == "error"]
    warnings = [p.get("message", "") for p in problems if p.get("severity") == "warning"]
    return [e for e in errors if e], [w for w in warnings if w]


def run_ci(
    repo_path: Path,
    *,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    summary_path: Path | None = None,
    workdir: str | None = None,
    install_deps: bool = False,
    correlation_id: str | None = None,
    no_summary: bool = False,
    write_github_summary: bool | None = None,
    config_from_hub: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CiRunResult:
    repo_path = repo_path.resolve()
    output_dir = Path(output_dir or ".cihub")
    if not output_dir.is_absolute():
        output_dir = repo_path / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    env_map = dict(env) if env is not None else dict(os.environ)

    try:
        if config_from_hub:
            config = load_hub_config(config_from_hub, repo_path)
        else:
            config = load_ci_config(repo_path)
    except Exception as exc:
        message = f"Failed to load config: {exc}"
        config_problems = [{"severity": "error", "message": message, "code": "CIHUB-CI-CONFIG"}]
        errors, warnings = _split_problems(config_problems)
        return CiRunResult(
            success=False,
            errors=errors,
            warnings=warnings,
            exit_code=EXIT_FAILURE,
            problems=config_problems,
        )

    language = config.get("language") or ""
    run_workdir = _resolve_workdir(repo_path, config, workdir)
    problems: list[dict[str, Any]] = []
    _apply_force_all_tools(config, language)
    _apply_env_overrides(config, language, env_map, problems)
    _warn_reserved_features(config, problems)

    report: dict[str, Any] = {}
    tool_outputs: dict[str, dict[str, Any]] = {}
    tools_ran: dict[str, bool] = {}
    tools_success: dict[str, bool] = {}
    gate_failures: list[str] = []

    if language == "python":
        if install_deps:
            _install_python_dependencies(config, repo_path / run_workdir, problems)
        try:
            tool_outputs, tools_ran, tools_success = _run_python_tools(
                config,
                repo_path,
                run_workdir,
                output_dir,
                problems,
            )
        except Exception as exc:
            message = f"Tool execution failed: {exc}"
            problems.append(
                {
                    "severity": "error",
                    "message": message,
                    "code": "CIHUB-CI-TOOL-FAILURE",
                }
            )
            errors, warnings = _split_problems(problems)
            return CiRunResult(
                success=False,
                errors=errors,
                warnings=warnings,
                exit_code=EXIT_INTERNAL_ERROR,
                problems=problems,
            )

        tools_configured = {tool: _tool_enabled(config, tool, "python") for tool in PYTHON_TOOLS}
        thresholds = resolve_thresholds(config, "python")
        context = _build_context(repo_path, config, run_workdir, correlation_id)
        report = build_python_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
        gate_failures = _evaluate_python_gates(report, thresholds, tools_configured, config)

    elif language == "java":
        build_tool = config.get("java", {}).get("build_tool", "maven").strip().lower() or "maven"
        if build_tool not in {"maven", "gradle"}:
            build_tool = "maven"
        project_type = _detect_java_project_type(repo_path / run_workdir)
        docker_cfg = config.get("java", {}).get("tools", {}).get("docker", {}) or {}
        docker_compose = docker_cfg.get("compose_file")
        docker_health = docker_cfg.get("health_endpoint")

        try:
            tool_outputs, tools_ran, tools_success = _run_java_tools(
                config, repo_path, run_workdir, output_dir, build_tool, problems
            )
        except Exception as exc:
            message = f"Tool execution failed: {exc}"
            problems.append(
                {
                    "severity": "error",
                    "message": message,
                    "code": "CIHUB-CI-TOOL-FAILURE",
                }
            )
            errors, warnings = _split_problems(problems)
            return CiRunResult(
                success=False,
                errors=errors,
                warnings=warnings,
                exit_code=EXIT_INTERNAL_ERROR,
                problems=problems,
            )

        tools_configured = {tool: _tool_enabled(config, tool, "java") for tool in JAVA_TOOLS}
        thresholds = resolve_thresholds(config, "java")
        context = _build_context(
            repo_path,
            config,
            run_workdir,
            correlation_id,
            build_tool=build_tool,
            project_type=project_type,
            docker_compose_file=docker_compose,
            docker_health_endpoint=docker_health,
        )
        report = build_java_report(
            config,
            tool_outputs,
            tools_configured,
            tools_ran,
            tools_success,
            thresholds,
            context,
        )
        gate_failures = _evaluate_java_gates(report, thresholds, tools_configured, config)

    else:
        message = f"cihub ci supports python or java (got '{language}')"
        problems = [{"severity": "error", "message": message, "code": "CIHUB-CI-LANGUAGE"}]
        errors, warnings = _split_problems(problems)
        return CiRunResult(
            success=False,
            errors=errors,
            warnings=warnings,
            exit_code=EXIT_FAILURE,
            problems=problems,
        )

    resolved_report_path = report_path or output_dir / "report.json"
    if not resolved_report_path.is_absolute():
        resolved_report_path = repo_path / resolved_report_path
    resolved_report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    github_summary_cfg = config.get("reports", {}).get("github_summary", {}) or {}
    include_metrics = bool(github_summary_cfg.get("include_metrics", True))
    summary_text = render_summary(report, include_metrics=include_metrics)
    if write_github_summary is None:
        write_summary = bool(github_summary_cfg.get("enabled", True))
    else:
        write_summary = bool(write_github_summary)

    resolved_summary_path: Path | None = None
    if not no_summary:
        resolved_summary_path = summary_path or output_dir / "summary.md"
        if not resolved_summary_path.is_absolute():
            resolved_summary_path = repo_path / resolved_summary_path
        resolved_summary_path.write_text(summary_text, encoding="utf-8")

    github_summary_env = env_map.get("GITHUB_STEP_SUMMARY")
    if write_summary and github_summary_env:
        Path(github_summary_env).write_text(summary_text, encoding="utf-8")

    codecov_cfg = config.get("reports", {}).get("codecov", {}) or {}
    if codecov_cfg.get("enabled", True):
        files = _collect_codecov_files(language, output_dir, tool_outputs)
        _run_codecov_upload(
            files,
            bool(codecov_cfg.get("fail_ci_on_error", False)),
            problems,
        )

    if gate_failures:
        problems.extend(
            [
                {
                    "severity": "error",
                    "message": failure,
                    "code": "CIHUB-CI-GATE",
                }
                for failure in gate_failures
            ]
        )

    has_errors = any(p.get("severity") == "error" for p in problems)
    _notify(not has_errors, config, report, problems, env_map)
    exit_code = EXIT_FAILURE if has_errors else EXIT_SUCCESS
    errors, warnings = _split_problems(problems)

    artifacts: dict[str, str] = {"report": str(resolved_report_path)}
    data: dict[str, str] = {"report_path": str(resolved_report_path)}
    if resolved_summary_path:
        artifacts["summary"] = str(resolved_summary_path)
        data["summary_path"] = str(resolved_summary_path)

    return CiRunResult(
        success=exit_code == EXIT_SUCCESS,
        errors=errors,
        warnings=warnings,
        exit_code=exit_code,
        report_path=resolved_report_path,
        summary_path=resolved_summary_path,
        report=report,
        summary_text=summary_text,
        artifacts=artifacts,
        data=data,
        problems=problems,
    )
